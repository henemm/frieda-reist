"""Nachweistests für die Anmeldecode-Mail mit Mail-Rahmen (#532, Spec docs/specs/betrieb/anmeldecode-mail-532.md).

Mails kommen aus FR_MAIL_DATEI oder einem SMTP-Spion; Texte werden über ihre Schlüssel im Katalog geprüft (meldet, text),
nie über kopierte Sätze. Alle Adressen, Namen und Anschriften sind erfunden (Domain beispiel.invalid)."""
import email
import email.policy
import html
import json
import re
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
sys.path.insert(0, str(ENGINE))
import konten  # noqa: E402
import texte  # noqa: E402
from conftest import meldet, text  # noqa: E402

IDA, KARL = "ida@beispiel.invalid", "karl@beispiel.invalid"
BASIS = "https://frieda.beispiel.invalid"
BETREIBER_NAME = "Erfundene Reisewerkstatt"
BETREIBER_ANSCHRIFT = "Beispielweg 1\n12345 Musterstadt"
SPRACHEN = ("de", "en")
ZWECKE = ("anmelden", "adresse")

NEUE_SCHLUESSEL = (
    "mail.code.betreff_anmelden", "mail.code.betreff_adresse", "mail.code.zeile_code", "mail.code.zeile_eingabe",
    "mail.code.zeile_link", "mail.code.titel_anmelden", "mail.code.titel_adresse", "mail.code.vorschau",
    "mail.code.sicher_titel", "mail.code.sicher_text", "mail.fuss.grund", "mail.fuss.impressum",
    "mail.fuss.datenschutz",
)
VERBOTEN_IM_HTML = ("<img", "<link", "<script", "<iframe", "<form", "url(", "@import", "@font-face")


# ---------------------------------------------------------------- Hilfen

@pytest.fixture(autouse=True)
def umgebung(tmp_path, monkeypatch):
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    monkeypatch.setenv("FR_BASIS", BASIS)
    monkeypatch.setenv("FR_BETREIBER_NAME", BETREIBER_NAME)
    monkeypatch.setenv("FR_BETREIBER_ANSCHRIFT", BETREIBER_ANSCHRIFT)
    uhr = {"t": 1_800_000_000.0}
    monkeypatch.setattr(konten, "_jetzt", lambda: uhr["t"])
    return {"tmp": tmp_path, "uhr": uhr}


def mails(umgebung, an=None):
    p = umgebung["tmp"] / "mails.jsonl"
    alle = [json.loads(z) for z in p.read_text(encoding="utf-8").splitlines() if z.strip()] if p.exists() else []
    return [m for m in alle if an is None or m["an"] == an]


def konto_neu(kid, mail, name="Ida", sprache="de", rechte=""):
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, rechte, gesperrt, angelegt, sprache) VALUES (?,?,?,?,?,?,?)",
                  (kid, mail, name, rechte, 0, "2026-11-19", sprache))
    return konten.konto(kid)


def code_mail(umgebung, sprache="de", zweck="anmelden", an=IDA):
    """Fordert einen Code an und liefert die geschriebene Mailzeile (Zweck „adresse“ über ein Konto von Karl)."""
    if zweck == "adresse":
        konto_neu("k-karl", KARL, "Karl", sprache)
        konten.code_anfordern(an, zweck="adresse", konto="k-karl", sprache=sprache)
    else:
        konten.code_anfordern(an, sprache=sprache)
    alle = mails(umgebung, an)
    assert len(alle) == 1, alle
    return alle[0]


def code_aus(m):
    """Der Code steht als sechs zusammenhängende Ziffern vorn im Betreff."""
    treffer = re.match(r"(\d{6})(?!\d)", m["betreff"])
    assert treffer, f"Betreff beginnt nicht mit dem Code: {m['betreff']!r}"
    return treffer.group(1)


def adressen(s):
    return re.findall(r"https?://[^\s\"'<>]+", s)


def hrefs(h):
    return re.findall(r'href="([^"]*)"', h)


class Spion:
    gesendet = []

    def __init__(self, *a, **kw):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, *a):
        pass

    def send_message(self, m):
        Spion.gesendet.append(m)


@pytest.fixture
def smtp(monkeypatch):
    Spion.gesendet = []
    monkeypatch.delenv("FR_MAIL_DATEI", raising=False)
    monkeypatch.setenv("FR_SMTP_HOST", "smtp.beispiel.invalid")
    monkeypatch.setenv("FR_ABSENDER", "frieda@beispiel.invalid")
    monkeypatch.setattr(konten.smtplib, "SMTP", Spion)
    return Spion.gesendet


# ---------------------------------------------------------------- Versandweg (AC-1 bis AC-4)

def test_mehrteiler_text_und_html_smtp(smtp):
    konten.mail_senden(IDA, "Betreff", "Nur Text", html="<p>Mit HTML</p>")
    konten.mail_senden(IDA, "Betreff", "Nur Text")
    m, ohne = smtp
    assert m.get_content_type() == "multipart/alternative"
    teile = list(m.iter_parts())
    assert [t.get_content_type() for t in teile] == ["text/plain", "text/html"]
    assert teile[0].get_content().strip() == "Nur Text"
    assert teile[1].get_content().strip() == "<p>Mit HTML</p>"
    assert not ohne.is_multipart() and ohne.get_content_type() == "text/plain"
    assert ohne.get_content().strip() == "Nur Text"


@pytest.mark.parametrize("absender", ["frieda@beispiel.invalid", "Andere Person <frieda@beispiel.invalid>",
                                      "Frieda <frieda@beispiel.invalid>"])
def test_absender_anzeigename_frieda(smtp, monkeypatch, absender):
    monkeypatch.setenv("FR_ABSENDER", absender)
    konten.mail_senden(IDA, "Betreff", "Text")
    von = smtp[0]["From"]
    assert str(von) == "Frieda <frieda@beispiel.invalid>"
    assert str(von).count("Frieda") == 1 and "Andere" not in str(von)


@pytest.mark.parametrize("absender", ["a@b.invalid\nBcc: x@y.invalid", "a@b.invalid\r\nBcc: x@y.invalid",
                                      "keine-adresse", "Frieda <ohne-at>"])
def test_absender_ohne_header_injektion(smtp, monkeypatch, absender):
    monkeypatch.setenv("FR_ABSENDER", absender)
    with pytest.raises(konten.KontoFehler) as f:
        konten.mail_senden(IDA, "Betreff", "Text")
    assert f.value.schluessel == "konto.fehler.mail_nicht_eingerichtet"
    assert smtp == []
    assert all(m["Bcc"] is None for m in smtp)


def test_absender_ohne_header_injektion_code_bleibt(smtp, monkeypatch):
    """Ein ungültiger Absender sperrt nicht still: die Code-Anforderung meldet „nicht eingerichtet“, nichts geht hinaus."""
    monkeypatch.setenv("FR_ABSENDER", "a@b.invalid\nBcc: x@y.invalid")
    with pytest.raises(konten.KontoFehler) as f:
        konten.code_anfordern(IDA)
    assert f.value.schluessel == "konto.fehler.mail_nicht_eingerichtet"
    assert smtp == []


def test_dateizeile_ohne_html_unveraendert(umgebung):
    datei = umgebung["tmp"] / "mails.jsonl"
    konten.mail_senden(IDA, "B", "T")
    konten.mail_senden(IDA, "B", "T", antwort_an=KARL)
    a, b = datei.read_text(encoding="utf-8").splitlines()
    assert a == json.dumps({"an": IDA, "betreff": "B", "text": "T"}, ensure_ascii=False)
    assert b == json.dumps({"an": IDA, "betreff": "B", "text": "T", "antwort_an": KARL}, ensure_ascii=False)


def test_dateizeile_mit_html(umgebung):
    datei = umgebung["tmp"] / "mails.jsonl"
    konten.mail_senden(IDA, "B", "T", html="<p>H</p>")
    konten.mail_senden(IDA, "B", "T", antwort_an=KARL, html="<p>H</p>")
    a, b = datei.read_text(encoding="utf-8").splitlines()
    assert json.loads(a) == {"an": IDA, "betreff": "B", "text": "T", "html": "<p>H</p>"}
    assert list(json.loads(b)) == ["an", "betreff", "text", "html", "antwort_an"]
    assert json.loads(b)["antwort_an"] == KARL and "von" not in json.loads(b)


# ---------------------------------------------------------------- Code-Mail (AC-5 bis AC-8, AC-16)

@pytest.mark.parametrize("sprache", SPRACHEN)
@pytest.mark.parametrize("zweck", ZWECKE)
def test_betreff_code_vorn_ohne_leerzeichen(umgebung, sprache, zweck):
    m = code_mail(umgebung, sprache, zweck)
    code = code_aus(m)
    assert "\n" not in m["betreff"] and "\r" not in m["betreff"]
    assert meldet(m["betreff"], f"mail.code.betreff_{zweck}", sprache)
    assert code in m["text"] and code in m["html"]
    assert f"{code[:3]} {code[3:]}" not in m["text"] and f"{code[:3]} {code[3:]}" not in m["html"]
    # der Code der Mail ist der gültige Code
    if zweck == "anmelden":
        konto_neu("k-ida", IDA, "Ida", sprache)
        token, k = konten.anmelden(IDA, code)
        assert k["id"] == "k-ida"


@pytest.mark.parametrize("sprache", SPRACHEN)
@pytest.mark.parametrize("zweck", ZWECKE)
def test_code_nie_in_einem_link(umgebung, sprache, zweck):
    m = code_mail(umgebung, sprache, zweck)
    code = code_aus(m)
    links = adressen(m["text"]) + adressen(m["html"]) + hrefs(m["html"])
    assert links, "die Mail enthält mindestens die Links des Fußes"
    for link in links:
        assert code not in link, link
        assert not re.search(r"\d{6}", link), link
    if zweck == "anmelden":
        anmelde = [l for l in links if "/anmelden?" in l]
        assert anmelde and all("schritt=code" in l and "email=" in l for l in anmelde)


@pytest.mark.parametrize("sprache", SPRACHEN)
def test_link_nur_bei_anmelden_mit_basis(umgebung, monkeypatch, sprache):
    m = code_mail(umgebung, sprache, "anmelden")
    assert meldet(m["text"], "mail.code.zeile_link", sprache)
    assert f"{BASIS}/anmelden?schritt=code&email=" in m["text"]
    assert any(h.startswith(f"{BASIS}/anmelden?") for h in map(html.unescape, hrefs(m["html"])))


@pytest.mark.parametrize("sprache", SPRACHEN)
def test_link_nicht_bei_neuer_adresse(umgebung, sprache):
    m = code_mail(umgebung, sprache, "adresse", an=IDA)
    assert not meldet(m["text"], "mail.code.zeile_link", sprache)
    assert "/anmelden" not in m["text"]
    assert not any("/anmelden" in h for h in hrefs(m["html"]))


@pytest.mark.parametrize("basis", [None, "", "javascript:alert(1)", "ftp://frieda.beispiel.invalid",
                                   "frieda.beispiel.invalid"])
@pytest.mark.parametrize("sprache", SPRACHEN)
def test_link_nicht_ohne_gueltige_basis(umgebung, monkeypatch, basis, sprache):
    if basis is None:
        monkeypatch.delenv("FR_BASIS", raising=False)
    else:
        monkeypatch.setenv("FR_BASIS", basis)
    m = code_mail(umgebung, sprache, "anmelden")
    assert hrefs(m["html"]) == [], "ohne gültige Basis gibt es keinen einzigen Link"
    assert not meldet(m["text"], "mail.code.zeile_link", sprache)
    assert "/anmelden" not in m["text"] and "javascript:" not in m["text"] + m["html"]
    assert "/impressum" not in m["text"] and "/datenschutz" not in m["text"]
    # Impressum und Datenschutz bleiben als Wörter stehen
    for teil in (m["text"], m["html"]):
        assert meldet(teil, "mail.fuss.impressum", sprache) and meldet(teil, "mail.fuss.datenschutz", sprache)


@pytest.mark.parametrize("sprache", SPRACHEN)
@pytest.mark.parametrize("minuten", [10, 17])
def test_text_teil_vollstaendig(umgebung, monkeypatch, sprache, minuten):
    if minuten != 10:
        monkeypatch.setattr(konten, "CODE_MINUTEN", minuten)
    else:
        assert konten.CODE_MINUTEN == 10
    m = code_mail(umgebung, sprache, "anmelden")
    t = m["text"]
    assert code_aus(m) in t
    assert text("mail.code.zeile_eingabe", sprache, minuten=minuten) in t
    assert meldet(t, "mail.code.titel_anmelden", sprache)
    assert meldet(t, "mail.code.zeile_code", sprache)
    assert meldet(t, "mail.code.sicher_titel", sprache) and meldet(t, "mail.code.sicher_text", sprache)
    assert meldet(t, "mail.fuss.grund", sprache)
    assert meldet(t, "mail.fuss.impressum", sprache) and meldet(t, "mail.fuss.datenschutz", sprache)
    assert f"{BASIS}/impressum" in t and f"{BASIS}/datenschutz" in t
    assert "<" not in t and ">" not in t and "{" not in t and "}" not in t
    assert "None" not in t


@pytest.mark.parametrize("sprache", SPRACHEN)
def test_titel_der_neuen_adresse(umgebung, sprache):
    m = code_mail(umgebung, sprache, "adresse")
    assert meldet(m["text"], "mail.code.titel_adresse", sprache)
    assert meldet(m["html"], "mail.code.titel_adresse", sprache)


def test_eine_mail_je_anforderung_und_still(umgebung, monkeypatch):
    assert konten.code_anfordern(IDA) is None
    alle = mails(umgebung)
    assert len(alle) == 1 and alle[0]["an"] == IDA and "html" in alle[0]
    # Tagesgrenze für Adressen ohne Konto erreicht: keine Mail, gleiche Antwort
    monkeypatch.setattr(konten.instanz, "grenze_codes_tag", lambda: 1)
    assert konten.code_anfordern(KARL) is None
    assert mails(umgebung, KARL) == []
    assert len(mails(umgebung)) == 1


# ---------------------------------------------------------------- HTML und Fuß (AC-9 bis AC-12)

@pytest.mark.parametrize("sprache", SPRACHEN)
def test_html_geruest_dunkelmodus_inline_stile(umgebung, sprache):
    m = code_mail(umgebung, sprache)
    h, code = m["html"], code_aus(m)
    assert h.lstrip().lower().startswith("<!doctype html")
    assert re.search(rf'<html[^>]*\blang="{sprache}"', h)
    assert '<meta charset="utf-8">' in h.lower()
    assert re.search(r'<meta name="color-scheme" content="light dark"', h)
    assert re.search(r'<meta name="supported-color-schemes" content="light dark"', h)
    assert "<table" in h
    stile = re.findall(r"<style[^>]*>(.*?)</style>", h, flags=re.S)
    assert len(stile) == 1, "genau ein Stilblock"
    block = stile[0].strip()
    assert block.startswith("@media (prefers-color-scheme: dark)")
    # außerhalb von @media steht keine Regel: der Block endet mit der schließenden Klammer des @media
    tiefe, ende = 0, None
    for i, z in enumerate(block):
        if z == "{":
            tiefe += 1
        elif z == "}":
            tiefe -= 1
            if tiefe == 0:
                ende = i
                break
    assert ende is not None and block[ende + 1:].strip() == ""
    assert 'style="' in h
    # Der Code steht groß und in Festbreitenschrift in einer eigenen Zelle
    zelle = re.search(rf"<td[^>]*style=\"([^\"]*)\"[^>]*>\s*{code}\s*</td>", h)
    assert zelle, "Code in einer eigenen Zelle, ohne Leerzeichen"
    assert "monospace" in zelle.group(1) and re.search(r"font-size:\s*(2[8-9]|3\d|4\d)px", zelle.group(1))
    # Vorschautext versteckt am Anfang des Bodys
    body = h[h.lower().index("<body"):]
    vorschau = html.escape(text("mail.code.vorschau", sprache))
    assert vorschau in body[:1500] and "display:none" in body[:1500].replace(" ", "")


@pytest.mark.parametrize("sprache", SPRACHEN)
@pytest.mark.parametrize("zweck", ZWECKE)
def test_html_ohne_bild_pixel_externe_ressourcen(umgebung, sprache, zweck):
    h = code_mail(umgebung, sprache, zweck)["html"]
    klein = h.lower()
    for marker in VERBOTEN_IM_HTML:
        assert marker not in klein, marker
    for a in hrefs(h):
        assert html.unescape(a).startswith(BASIS + "/"), a
    ohne_href = re.sub(r'href="[^"]*"', "", h)
    assert "http" not in ohne_href.lower()


def test_html_alles_escaped(umgebung, monkeypatch):
    boese = '<script>alert(1)</script> & "x"'
    monkeypatch.setenv("FR_BETREIBER_NAME", boese)
    monkeypatch.setenv("FR_BETREIBER_ANSCHRIFT", f"{boese}\nZweite <b>Zeile</b>")
    m = code_mail(umgebung, "de", "anmelden", an="a+<b>@beispiel.invalid")
    h, t = m["html"], m["text"]
    assert "<script" not in h.lower() and "<b>" not in h
    assert html.escape(boese, quote=True) in h
    assert "&lt;script&gt;" in h and "&amp;" in h and "&quot;" in h
    assert f"{html.escape(boese, quote=True)}<br>Zweite &lt;b&gt;Zeile&lt;/b&gt;" in h.replace("<br/>", "<br>").replace("<br />", "<br>")
    assert boese in t and "Zweite <b>Zeile</b>" in t
    assert "a+<b>@" not in h


@pytest.mark.parametrize("sprache", SPRACHEN)
def test_fuss_mit_betreiberwerten_und_links(umgebung, sprache):
    m = code_mail(umgebung, sprache)
    for teil in (m["text"], m["html"]):
        assert meldet(teil, "mail.fuss.grund", sprache)
        assert BETREIBER_NAME in teil
        assert "Beispielweg 1" in teil and "12345 Musterstadt" in teil
    assert f"{BASIS}/impressum" in m["text"] and f"{BASIS}/datenschutz" in m["text"]
    assert f"{BASIS}/impressum" in hrefs(m["html"]) and f"{BASIS}/datenschutz" in hrefs(m["html"])
    assert meldet(m["html"], "mail.fuss.impressum", sprache) and meldet(m["html"], "mail.fuss.datenschutz", sprache)


@pytest.mark.parametrize("name, anschrift", [(None, None), (BETREIBER_NAME, None), (None, BETREIBER_ANSCHRIFT),
                                             ("   ", " \n "), ("", "")])
@pytest.mark.parametrize("sprache", SPRACHEN)
def test_fuss_ohne_betreiberwerte(umgebung, monkeypatch, name, anschrift, sprache):
    for schluessel, wert in (("FR_BETREIBER_NAME", name), ("FR_BETREIBER_ANSCHRIFT", anschrift)):
        if wert is None:
            monkeypatch.delenv(schluessel, raising=False)
        else:
            monkeypatch.setenv(schluessel, wert)
    m = code_mail(umgebung, sprache)
    for teil in (m["text"], m["html"]):
        assert meldet(teil, "mail.fuss.grund", sprache)
        assert meldet(teil, "mail.fuss.impressum", sprache) and meldet(teil, "mail.fuss.datenschutz", sprache)
        assert "None" not in teil and "{" not in re.sub(r"<style.*?</style>", "", teil, flags=re.S)
        assert (BETREIBER_NAME in teil) == (name == BETREIBER_NAME)
        assert ("Beispielweg 1" in teil) == (anschrift == BETREIBER_ANSCHRIFT)
    assert "\n\n\n" not in m["text"], "keine leere Zeile, wo eine Angabe fehlt"
    assert "<br><br>" not in m["html"].replace(" ", "")


# ---------------------------------------------------------------- Texte, Module, Deploy, Doku (AC-13 bis AC-18)

def test_mail_texte_vollstaendig_de_en():
    def platzhalter(s):
        return sorted(re.findall(r"\{(\w+)\}", s))
    for schluessel in NEUE_SCHLUESSEL:
        de, en = (texte.t(s, schluessel) for s in SPRACHEN)
        assert de != schluessel and en != schluessel, f"{schluessel} fehlt im Katalog"
        assert platzhalter(de) == platzhalter(en), schluessel
    for s in SPRACHEN:
        for zweck in ZWECKE:
            vorlage = texte.t(s, f"mail.code.betreff_{zweck}")
            assert vorlage.startswith("{code}"), f"Betreff {zweck}/{s} beginnt nicht mit dem Code"
        assert texte.t(s, "mail.code.zeile_loeschen") == "mail.code.zeile_loeschen", "alter Schlüssel ist weg"


def test_mailrahmen_importiert_anmeldung_nicht():
    quelle = (ENGINE / "mailrahmen.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(anmeldung|konten)\b", quelle, flags=re.M)
    probe = ("import sys; sys.path.insert(0, sys.argv[1]); import mailrahmen; "
             "print('anmeldung' in sys.modules, 'konten' in sys.modules)")
    aus = subprocess.run([sys.executable, "-I", "-c", probe, str(ENGINE)], capture_output=True, text=True, check=True)
    assert aus.stdout.split() == ["False", "False"]


def test_andere_mails_unveraendert(umgebung):
    """Warteliste, Freigabe, Einladung und Betreiber-Meldung bleiben Textmails ohne Feld html (Regressionsschutz)."""
    konten.warteliste_eintragen(KARL)
    wort = re.search(r"/warteliste/bestaetigen/(\S+)", mails(umgebung, KARL)[-1]["text"]).group(1)
    konten.warteliste_bestaetigen(wort)
    konten.freigeben(KARL)
    konten.einladen("beispielreise", "ida", "lea@beispiel.invalid", "gast", "Lea", "Ida", titel="Beispielreise")
    konto_neu("k-betr", "betrieb@beispiel.invalid", "Betrieb", "de", "betreiber")
    ida = konto_neu("k-ida", IDA, "Ida")
    konten.an_betreiber_melden(ida, "Frage", "Eine erfundene Frage")
    erwartet = {"mail.warteliste.betreff", "mail.freigabe.betreff", "mail.einladung.betreff",
                "konto.betreiber_meldung.mail_betreff"}
    gefunden = set()
    for m in mails(umgebung):
        assert "html" not in m and set(m) <= {"an", "betreff", "text", "antwort_an"}, m
        gefunden |= {s for s in erwartet if meldet(m["betreff"], s)}
    assert gefunden == erwartet
    # Reise löschen (anmeldung.py) und alle übrigen Aufrufer: nur code_anfordern übergibt html
    for datei in ("konten.py", "anmeldung.py"):
        quelle = (ENGINE / datei).read_text(encoding="utf-8")
        for aufruf in re.finditer(r"(?<!def )mail_senden\((?:[^()]|\([^()]*\))*\)", quelle):
            if "html" in aufruf.group(0):
                anfang = quelle.rfind("\ndef ", 0, aufruf.start())
                assert quelle[anfang:].startswith("\ndef code_anfordern"), aufruf.group(0)


def _deploy_liste(name):
    zeile = re.search(rf'^{name}="([^"]*)"', (WURZEL / "betrieb" / "deploy.sh").read_text(encoding="utf-8"), re.M)
    return set(zeile.group(1).split())


@pytest.mark.parametrize("liste", ["RM_MODULE", "KN_MODULE", "SB_MODULE", "PS_MODULE"])
def test_deploy_listen_enthalten_mailrahmen(liste):
    module = _deploy_liste(liste)
    assert "konten.py" in module and "mailrahmen.py" in module


def test_doku_mailrahmen_und_mail_datei():
    design = (WURZEL / "docs" / "design.md").read_text(encoding="utf-8")
    assert re.search(r"^#+ .*Mail-Rahmen", design, flags=re.M), "eigener Abschnitt „Mail-Rahmen“"
    tabelle_von = design.index("| Ebene | Bausteine")
    tabelle_bis = design.index("## Ontologie und Bausteine")
    assert "Mail-Rahmen" not in design[tabelle_von:tabelle_bis], "nicht in der Ebenen-Tabelle"
    assert "Mail-Rahmen" not in (ENGINE / "vorlage.html").read_text(encoding="utf-8")
    betrieb = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    abschnitt = betrieb[betrieb.index("FR_MAIL_DATEI"):]
    for feld in ("`an`", "`betreff`", "`text`", "`html`", "`antwort_an`"):
        assert feld in abschnitt[:3000], f"FR_MAIL_DATEI-Format nennt {feld} nicht"
