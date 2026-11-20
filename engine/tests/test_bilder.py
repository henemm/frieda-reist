"""Tests für Bilder Stufe 1, Paket P1 (#455, #581; Spec docs/specs/oberflaeche/bilder-455-stufe1.md): Liste plan/bilder.yaml mit
Kennung BI-NN, Abruf aus Wikimedia Commons und Wikidata, Lizenz lesen und einordnen (#613, Spec
docs/specs/oberflaeche/bilder-lizenzhinweis-613.md: keine Positivliste mehr, Hinweis statt Ablehnung), zwei WebP-Fassungen,
Rechte, Werkzeuge, Hotlink-Sperre, bilder_nachziehen und BI- im Text. Kein Test geht ins Netz: urllib.request.urlopen wird ersetzt, Commons- und
Wikidata-Antworten sind Fixtures in dieser Datei, das Testbild entsteht mit Pillow.

Was diese Tests als Schnittstelle festlegen (über die Spec hinaus):
  bilder.Abgelehnt(schluessel, **werte)         Ablehnung des Moduls; .schluessel ist bild.abgelehnt.*
  bilder.lizenz_lesen(extmetadata) -> dict       {"lizenz", "lizenz_url", "gemeinfrei"}; wirft nie wegen der Lizenz (#613)
  bilder.einschraenkungen(lizenz) -> list[str]   Codes aus nc, nd, gfdl, fehlt, andere; leer bei freier Lizenz (#613)
  bilder.urheber_saeubern(html) -> str           reiner Text
  bilder.abrufen(commons=None, wikidata=None) -> dict   Netzabruf (Metadaten und Bytes der 1600er-Fassung):
                                                 {"datei", "urheber", "lizenz", "lizenz_url", "seite", "gemeinfrei", "inhalt"}
  bilder.ZEITLIMIT = 20, bilder.MAX_META = 1 MB, bilder.MAX_BILD = 15 MB, bilder.PAUSE (Wartezeit vor der Wiederholung)
  bilder.FASSUNGEN = {"klein": 480, "gross": 1600}
  sb.bild_hinzufuegen(reise_dir, wer, args) / sb.bild_aendern(reise_dir, wer, args) -> (Titel, Text); Titel beginnt mit BI-NN
  sb.bild_vorab(s, reise, anfrage, vorab)       Abruf vor der Sperre; der Unterprozess liest das Ergebnis über FR_BILD_VORAB
  Antwort des Schreibwegs an den Konnektor: Feld "vorschau" (Base64 der kleinen Fassung) -> MitBild an Claude
  neu.bilder_nachziehen(reise_dir, schreiben=True) -> Meldungen; läuft in neu.nachziehen
  Baufehler: pruefung.bauen.bild_fremd (fremde Bildadresse), pruefung.bauen.bild_unbekannt (BI- ohne Eintrag)
"""
import base64
import io
import json
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import neu  # noqa: E402
import reise as rg  # noqa: E402
import routen  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402
from test_konnektor import dienst, schreibweg, seiten  # noqa: E402,F401  (Fixtures)
from test_schreiben import repo  # noqa: E402,F401  (Fixture)

WURZEL = Path(__file__).resolve().parent.parent.parent
WANDERUNG = WURZEL / "beispiel" / "reisen" / "beispielreise"
STADT = WURZEL / "beispiel" / "reisen" / "stadtwochenende"
IDA = {"name": "Ida", "rolle": "organisator"}
KARL = {"name": "Karl", "rolle": "mitwirkend"}


def bilder_modul():
    import bilder
    return bilder


# ---------- Fixtures: Commons, Wikidata, Testbild ----------

def bild_bytes(breite=2000, hoehe=1250, art="JPEG"):
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", (breite, hoehe), (120, 140, 90)).save(puffer, art)
    return puffer.getvalue()


def meta(lizenz="CC BY-SA 4.0", url="https://creativecommons.org/licenses/by-sa/4.0", artist='<a href="//commons.wikimedia.org/wiki/User:Max">Max Muster</a>'):
    m = {"Artist": {"value": artist}}
    if lizenz is not None:
        m["LicenseShortName"] = {"value": lizenz}
    if url is not None:
        m["LicenseUrl"] = {"value": url}
    return m


def commons_antwort(datei="Basteibruecke.jpg", extmetadata=None, mime="image/jpeg", fehlt=False):
    if fehlt:
        return {"query": {"pages": {"-1": {"title": f"File:{datei}", "missing": ""}}}}
    return {"query": {"pages": {"42": {"title": f"File:{datei}", "imageinfo": [{
        "thumburl": f"https://upload.wikimedia.org/thumb/{datei}/1600px-{datei}", "thumbwidth": 1600, "thumbheight": 1000,
        "url": f"https://upload.wikimedia.org/{datei}", "descriptionurl": f"https://commons.wikimedia.org/wiki/File:{datei}",
        "mime": mime, "extmetadata": extmetadata if extmetadata is not None else meta()}]}}}}


class Antwort:
    def __init__(self, inhalt, status=200):
        self.inhalt, self.status, self.headers = inhalt, status, {"Content-Length": str(len(inhalt))}

    def read(self, n=-1):
        return self.inhalt if n is None or n < 0 else self.inhalt[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Netz:
    """Ersetzt urllib.request.urlopen: Commons-API (prop=imageinfo), Wikidata (wbgetclaims) und die Bilddatei.
    fehler: Liste von Ausnahmen oder HTTP-Codes, die nacheinander vor der echten Antwort geworfen werden."""

    def __init__(self, monkeypatch, commons=None, wikidata=None, bild=None, fehler=()):
        self.commons = commons if commons is not None else commons_antwort()
        self.wikidata = wikidata if wikidata is not None else {"claims": {"P18": [{"mainsnak": {"datavalue": {"value": "Basteibruecke.jpg"}}}]}}
        self.bild = bild if bild is not None else bild_bytes()
        self.fehler = list(fehler)
        self.aufrufe = []      # (url, user_agent, timeout)
        monkeypatch.setattr(urllib.request, "urlopen", self.urlopen)
        monkeypatch.setattr(bilder_modul().time, "sleep", lambda s: None)

    def urlopen(self, req, timeout=None, **kw):
        url = req.full_url if isinstance(req, urllib.request.Request) else req
        ua = req.get_header("User-agent") if isinstance(req, urllib.request.Request) else None
        self.aufrufe.append((url, ua, timeout))
        if self.fehler:
            f = self.fehler.pop(0)
            if isinstance(f, int):
                raise urllib.error.HTTPError(url, f, "Fehler", {}, None)
            raise f
        if "wbgetclaims" in url:
            return Antwort(json.dumps(self.wikidata).encode())
        if "imageinfo" in url:
            return Antwort(json.dumps(self.commons).encode() if isinstance(self.commons, dict) else self.commons)
        return Antwort(self.bild)


@pytest.fixture
def wanderung(tmp_path):
    ziel = tmp_path / "beispielreise"
    shutil.copytree(WANDERUNG, ziel)
    return ziel


@pytest.fixture
def stadt(tmp_path):
    ziel = tmp_path / "stadtwochenende"
    shutil.copytree(STADT, ziel)
    return ziel


def liste(ordner):
    p = ordner / "plan" / "bilder.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("bilder") or [] if p.exists() else []


def eintrag(ordner, bid):
    return next(b for b in liste(ordner) if b["id"] == bid)


def neu_hinzu(ordner, wer=IDA, **args):
    titel, text = sb.bild_hinzufuegen(ordner, wer, {"commons": "Basteibruecke.jpg", "zu": "E-01", **args})
    return titel.split()[0], text


# ---------- Lizenz lesen und einordnen (#613, ersetzt V8; V9) ----------

@pytest.mark.parametrize("lizenz, url", [("CC0", "https://creativecommons.org/publicdomain/zero/1.0"), ("Public domain", None),
                                         ("PD", None), ("CC BY 3.0", "https://creativecommons.org/licenses/by/3.0"),
                                         ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0"),
                                         ("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0"),
                                         ("CC BY-ND 4.0", None), ("GFDL", None), ("Free Art License", None),
                                         ("Copyrighted", None), ("", None), (None, None)])
def test_lizenz_lesen_wirft_nie(lizenz, url):
    r = bilder_modul().lizenz_lesen(meta(lizenz, url))
    assert set(r) == {"lizenz", "lizenz_url", "gemeinfrei"}
    assert r["lizenz"] == (lizenz or "")
    assert r["gemeinfrei"] == (lizenz in ("CC0", "Public domain", "PD"))
    assert r["lizenz_url"] == url


def test_lizenz_lesen_nimmt_nur_https_links():
    assert bilder_modul().lizenz_lesen(meta("CC BY-NC 4.0", "javascript:alert(1)"))["lizenz_url"] is None


def test_positivliste_und_pruefung_entfallen():
    b = bilder_modul()
    assert not hasattr(b, "lizenz_pruefen") and not hasattr(b, "FREI")


EINORDNUNG = [("CC0", []), ("Public domain", []), ("PD-old", []), ("CC BY 4.0", []), ("CC BY-SA 3.0", []), ("CC BY-SA", []),
              ("CC BY", []), ("CC BY 4.0 de", []), ("cc by-sa 2.5", []),
              ("CC BY-NC 4.0", ["nc"]), ("CC BY-NC-SA 3.0", ["nc"]), ("CC BY-NC-ND 4.0", ["nc", "nd"]), ("CC BY-ND 2.0", ["nd"]),
              ("cc by-nc-nd 4.0", ["nc", "nd"]), ("GFDL", ["gfdl"]), ("GFDL 1.2", ["gfdl"]),
              ("Free Art License", ["andere"]), ("FAL", ["andere"]), ("Copyrighted", ["andere"]), ("Attribution", ["andere"]),
              ("", ["fehlt"]), ("   ", ["fehlt"]), (None, ["fehlt"])]


@pytest.mark.parametrize("lizenz, codes", EINORDNUNG)
def test_einschraenkungen_nach_der_tabelle(lizenz, codes):
    assert bilder_modul().einschraenkungen(lizenz) == codes


def test_einschraenkung_nur_als_eigenes_wort():
    """NC, ND und GFDL zählen nur als eigenes Wort: „Grand“ oder „Unclear“ sind keine Einschränkung, sondern „andere“."""
    assert bilder_modul().einschraenkungen("Grand Unclear License") == ["andere"]


def test_urheber_wird_zu_text_gesaeubert():
    t = bilder_modul().urheber_saeubern('<a href="//x">Max <b>Muster</b></a><script>alert(1)</script><img src=x onerror=y>')
    assert t == "Max Muster" and "<" not in t and "alert" not in t


# ---------- Abruf (V7, AC-5) ----------

def test_abruf_mit_user_agent_zeitlimit_und_ohne_original(monkeypatch):
    import instanz
    b = bilder_modul()
    netz = Netz(monkeypatch)
    r = b.abrufen(commons="Basteibruecke.jpg")
    assert r["datei"] == "Basteibruecke.jpg" and r["urheber"] == "Max Muster" and r["lizenz"] == "CC BY-SA 4.0"
    assert r["seite"] == "https://commons.wikimedia.org/wiki/File:Basteibruecke.jpg" and r["inhalt"] == netz.bild
    assert b.ZEITLIMIT == 20
    assert all(ua == instanz.kennung() and t == 20 for _, ua, t in netz.aufrufe), netz.aufrufe
    api = urllib.parse.parse_qs(urllib.parse.urlsplit(netz.aufrufe[0][0]).query)
    assert api["iiurlwidth"] == ["1600"] and "extmetadata" in api["iiprop"][0]
    assert netz.aufrufe[-1][0].startswith("https://upload.wikimedia.org/thumb/")      # die 1600er-Fassung, nie das Original


def test_abruf_wiederholt_einmal_nach_429(monkeypatch):
    netz = Netz(monkeypatch, fehler=[429])
    assert bilder_modul().abrufen(commons="Basteibruecke.jpg")["lizenz"] == "CC BY-SA 4.0"
    assert len(netz.aufrufe) == 3


@pytest.mark.parametrize("fehler", [[503, 503], [502, 500], [TimeoutError(), TimeoutError()],
                                    [urllib.error.URLError("weg"), urllib.error.URLError("weg")]])
def test_abruf_dauerhaft_gestoert_lehnt_ab(monkeypatch, fehler):
    b = bilder_modul()
    Netz(monkeypatch, fehler=fehler)
    with pytest.raises(b.Abgelehnt) as e:
        b.abrufen(commons="Basteibruecke.jpg")
    assert e.value.schluessel == "bild.abgelehnt.netz"


def test_abruf_wikidata_liest_p18(monkeypatch):
    netz = Netz(monkeypatch)
    r = bilder_modul().abrufen(wikidata="Q12345")
    assert r["datei"] == "Basteibruecke.jpg"
    assert "wbgetclaims" in netz.aufrufe[0][0] and "Q12345" in netz.aufrufe[0][0] and "P18" in netz.aufrufe[0][0]


@pytest.mark.parametrize("fall, schluessel", [
    ("ohne_p18", "bild.abgelehnt.nicht_gefunden"),
    ("fehlt", "bild.abgelehnt.nicht_gefunden"),
    ("svg", "bild.abgelehnt.kein_rasterbild"),
    ("pdf", "bild.abgelehnt.kein_rasterbild"),
    ("kaputt", "bild.abgelehnt.kein_rasterbild"),
    ("meta_gross", "bild.abgelehnt.zu_gross"),
])
def test_abruf_lehnt_ab(monkeypatch, fall, schluessel):
    b = bilder_modul()
    kw = {"ohne_p18": {"wikidata": {"claims": {}}}, "fehlt": {"commons": commons_antwort(fehlt=True)},
          "svg": {"commons": commons_antwort("X.svg", mime="image/svg+xml"), "bild": b'<svg xmlns="http://www.w3.org/2000/svg"/>'},
          "pdf": {"commons": commons_antwort("X.pdf", mime="application/pdf"), "bild": b"%PDF-1.4\n"},
          "kaputt": {"bild": b"\xff\xd8\xff\xe0kaputt"},
          "meta_gross": {"commons": b"{" + b" " * (b.MAX_META + 10) + b"}"}}[fall]
    Netz(monkeypatch, **kw)
    with pytest.raises(b.Abgelehnt) as e:
        b.abrufen(**({"wikidata": "Q1"} if fall == "ohne_p18" else {"commons": "X.jpg"}))
    assert e.value.schluessel == schluessel


def test_bilddatei_ueber_15_mb_wird_vor_der_verkleinerung_abgelehnt(monkeypatch):
    b = bilder_modul()
    assert b.MAX_BILD == 15 * 1024 * 1024
    Netz(monkeypatch, bild=b"\xff\xd8" + b"0" * (b.MAX_BILD + 1))
    with pytest.raises(b.Abgelehnt) as e:
        b.abrufen(commons="Basteibruecke.jpg")
    assert e.value.schluessel == "bild.abgelehnt.zu_gross"


# ---------- Hinzufügen (V1, V4, AC-1, AC-2) ----------

def test_bild_hinzufuegen_legt_eintrag_mit_herkunft_und_zwei_webp_fassungen_an(wanderung, monkeypatch):
    from PIL import Image
    Netz(monkeypatch)
    vorher = {b["id"] for b in liste(wanderung)}
    bid, text = neu_hinzu(wanderung, bildunterschrift="Die Basteibrücke", alt="Steinbrücke über einer Schlucht")
    assert bid.startswith("BI-") and bid not in vorher
    b = eintrag(wanderung, bid)
    assert b["zu"] == "E-01" and b["quelle"] == {"commons": "Basteibruecke.jpg"}
    assert b["urheber"] == "Max Muster" and b["lizenz"] == "CC BY-SA 4.0"
    assert b["lizenz_url"].startswith("https://creativecommons.org/") and b["seite"].startswith("https://commons.wikimedia.org/")
    assert b["bildunterschrift"] == "Die Basteibrücke" and b["alt"] == "Steinbrücke über einer Schlucht"
    assert b["status"] == "aktiv" and not b.get("titelbild")
    assert b["hinzugefuegt"]["wer"] == "Ida" and b["hinzugefuegt"]["datum"]
    for fassung, breite in (("klein", 480), ("gross", 1600)):
        pfad = wanderung / b["dateien"][fassung]
        assert b["dateien"][fassung].startswith("medien/bilder/") and pfad.suffix == ".webp"
        with Image.open(pfad) as im:
            assert im.format == "WEBP" and im.width == breite
    assert b["breite"] == 1600 and b["hoehe"] == 1000
    assert "Max Muster" in text and "CC BY-SA 4.0" in text


def test_bild_aus_wikidata(wanderung, monkeypatch):
    Netz(monkeypatch)
    bid = sb.bild_hinzufuegen(wanderung, IDA, {"wikidata": "Q12345", "zu": "O-01"})[0].split()[0]
    assert eintrag(wanderung, bid)["quelle"] == {"wikidata": "Q12345", "commons": "Basteibruecke.jpg"}


@pytest.mark.parametrize("args, schluessel", [
    ({"commons": "X.jpg", "wikidata": "Q1", "zu": "E-01"}, "bild.abgelehnt.quelle"),
    ({"zu": "E-01"}, "bild.abgelehnt.quelle"),
    ({"commons": "X.jpg", "zu": "E-99"}, "bild.abgelehnt.ziel"),
    ({"commons": "X.jpg", "zu": "Quatsch"}, "bild.abgelehnt.ziel"),
])
def test_bild_hinzufuegen_lehnt_ab_ohne_eintrag(wanderung, monkeypatch, args, schluessel):
    netz = Netz(monkeypatch)
    vorher = liste(wanderung)
    with pytest.raises(sb.Ablehnung) as e:
        sb.bild_hinzufuegen(wanderung, IDA, args)
    assert e.value.schluessel == schluessel
    assert liste(wanderung) == vorher and netz.aufrufe == []       # Prüfung der Anfrage vor dem Netz


EINGESCHRAENKT = [("CC BY-NC 4.0", ["nc"]), ("CC BY-ND 4.0", ["nd"]), ("CC BY-NC-ND 4.0", ["nc", "nd"]), ("GFDL", ["gfdl"]),
                  ("Free Art License", ["andere"]), ("Copyrighted", ["andere"]), (None, ["fehlt"])]
CODES = ("nc", "nd", "gfdl", "fehlt", "andere")


def einschraenkung(code):
    return f"schreiben.antwort.bild.einschraenkung.{code}"


@pytest.mark.parametrize("reise", ["wanderung", "stadt"])
@pytest.mark.parametrize("lizenz, codes", EINGESCHRAENKT)
def test_bild_mit_eingeschraenkter_lizenz_wird_angenommen_mit_hinweis(request, monkeypatch, reise, lizenz, codes):
    """AC-1, AC-2, AC-5: jedes Commons-Bild kommt in die Reise, an der Wanderung wie am Stadtwochenende; die Antwort nennt
    Urheber, Lizenz, die Verantwortung der Person und je Einschränkung genau ihren Satz."""
    from PIL import Image
    ordner = request.getfixturevalue(reise)
    Netz(monkeypatch, commons=commons_antwort(extmetadata=meta(lizenz, None)))
    bid, text = neu_hinzu(ordner)
    b = eintrag(ordner, bid)
    assert b["lizenz"] == (lizenz or "") and b["status"] == "aktiv"
    for fassung in ("klein", "gross"):
        with Image.open(ordner / b["dateien"][fassung]) as im:
            assert im.format == "WEBP"
    assert "Max Muster" in text and (lizenz is None or lizenz in text)
    assert meldet(text, "schreiben.antwort.bild.neu") and meldet(text, "schreiben.antwort.bild.rechte")
    for code in CODES:
        assert meldet(text, einschraenkung(code)) == (code in codes), (code, text)


@pytest.mark.parametrize("lizenz", ["CC BY 4.0", "CC0", "CC BY-SA"])
def test_freie_lizenz_nur_mit_rechtehinweis(wanderung, monkeypatch, lizenz):
    """AC-4: freie Lizenz, auch ohne Version: Urheber, Lizenz, Verantwortung, kein Einschränkungssatz."""
    Netz(monkeypatch, commons=commons_antwort(extmetadata=meta(lizenz, None)))
    _, text = neu_hinzu(wanderung)
    assert "Max Muster" in text and lizenz in text and meldet(text, "schreiben.antwort.bild.rechte")
    assert [c for c in CODES if meldet(text, einschraenkung(c))] == []


def test_reihenfolge_der_saetze_in_der_antwort(wanderung, monkeypatch):
    """Aufbau: bild.neu, dann bild.rechte, dann die Einschränkungen in der Reihenfolge nc, nd; getrennt durch ein Leerzeichen."""
    import texte
    de = texte.sprache("de").TEXTE
    Netz(monkeypatch, commons=commons_antwort(extmetadata=meta("CC BY-NC-ND 4.0", None)))
    _, text = neu_hinzu(wanderung)
    assert text.endswith(" ".join([de["schreiben.antwort.bild.rechte"], de[einschraenkung("nc")], de[einschraenkung("nd")]]))


@pytest.mark.parametrize("artist, lizenz, ersatz", [("", "CC BY 4.0", "schreiben.antwort.bild.ohne_urheber"),
                                                     ('<a href="//x">Max Muster</a>', None, "schreiben.antwort.bild.ohne_lizenz"),
                                                     ("", "", "schreiben.antwort.bild.ohne_lizenz")])
def test_leerer_urheber_oder_lizenz_bekommt_ersatzwort(wanderung, monkeypatch, artist, lizenz, ersatz):
    """AC-6: keine leeren Stellen in der Antwort; gespeichert bleibt der leere Wert."""
    Netz(monkeypatch, commons=commons_antwort(extmetadata=meta(lizenz, None, artist=artist)))
    bid, text = neu_hinzu(wanderung)
    assert meldet(text, ersatz)
    assert ": ," not in text and ", ." not in text and " ." not in text and "  " not in text, text
    b = eintrag(wanderung, bid)
    assert b["lizenz"] == (lizenz or "")
    if not artist:
        assert not b.get("urheber")


@pytest.mark.parametrize("reise", ["wanderung", "stadt"])
def test_eingeschraenkte_bilder_ohne_neues_feld_und_nachziehen_aendert_nichts(request, monkeypatch, reise):
    """AC-8: kein neues Feld in plan/bilder.yaml, kein Formatwechsel; nachziehen meldet für die Bilder nichts."""
    ordner = request.getfixturevalue(reise)
    Netz(monkeypatch)
    frei, _ = neu_hinzu(ordner)
    felder = set(eintrag(ordner, frei))
    for lizenz in ("CC BY-NC-ND 4.0", None):
        Netz(monkeypatch, commons=commons_antwort(extmetadata=meta(lizenz, None)))
        bid, _ = neu_hinzu(ordner)
        assert set(eintrag(ordner, bid)) == felder, (lizenz, set(eintrag(ordner, bid)) ^ felder)
    stand = (ordner / "plan" / "bilder.yaml").read_bytes()
    assert neu.bilder_nachziehen(ordner, schreiben=False) == []
    neu.nachziehen(ordner, schreiben=False)
    assert (ordner / "plan" / "bilder.yaml").read_bytes() == stand


def test_nc_bild_wird_mit_namensnennung_gebaut(wanderung, monkeypatch, tmp_path):
    """AC-3: ein angenommenes NC-Bild steht mit Urheber und Lizenz-Link unter dem Bild, der Bau gelingt."""
    Netz(monkeypatch, commons=commons_antwort(extmetadata=meta("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0")))
    bid, _ = neu_hinzu(wanderung)
    text_anhaengen(wanderung, f"![Die Brücke]({bid})")
    bauen.bauen(wanderung, tmp_path / "dist")
    seite = (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    assert "Max Muster" in seite and "CC BY-NC 4.0" in seite and "https://creativecommons.org/licenses/by-nc/4.0" in seite


NEUE_LIZENZTEXTE = ("schreiben.antwort.bild.rechte", "schreiben.antwort.bild.ohne_urheber", "schreiben.antwort.bild.ohne_lizenz",
                    *(f"schreiben.antwort.bild.einschraenkung.{c}" for c in CODES))


def test_lizenztexte_in_allen_sprachen_und_ablehnung_entfaellt():
    """AC-7: bild.abgelehnt.lizenz in keiner Sprache, die neuen Schlüssel in jeder; der Code wirft die Ablehnung nirgends mehr."""
    import texte
    for kuerzel in texte.SPRACHEN:
        katalog = texte.sprache(kuerzel).TEXTE
        assert "bild.abgelehnt.lizenz" not in katalog, kuerzel
        fehlt = [k for k in NEUE_LIZENZTEXTE if k not in katalog]
        assert fehlt == [], (kuerzel, fehlt)
    for datei in (WURZEL / "engine").glob("*.py"):
        assert "bild.abgelehnt.lizenz" not in datei.read_text(encoding="utf-8"), datei.name


def test_werkzeugbeschreibung_und_doku_ohne_positivliste():
    """AC-10: keine Positivliste mehr; Verantwortung der Person und Hinweis in der Antwort."""
    import texte
    for kuerzel in ("de", "en"):
        beschreibung = texte.sprache(kuerzel).TEXTE["konnektor.werkzeug.bild_hinzufuegen"]
        assert "CC BY-SA" not in beschreibung and "CC0" not in beschreibung, kuerzel
    de = texte.sprache("de").TEXTE["konnektor.werkzeug.bild_hinzufuegen"]
    assert "verantwortlich" in de and "Hinweis" in de, de
    en = texte.sprache("en").TEXTE["konnektor.werkzeug.bild_hinzufuegen"]
    assert "responsib" in en, en
    zeile = next(z for z in (WURZEL / "docs" / "konnektor.md").read_text(encoding="utf-8").splitlines()
                 if z.startswith("| `bild_hinzufuegen`"))
    assert "CC BY-SA" not in zeile and "CC0" not in zeile and "verantwortlich" in zeile, zeile


def test_zu_reise_ist_erlaubt(wanderung, monkeypatch):
    Netz(monkeypatch)
    bid, _ = neu_hinzu(wanderung, zu="reise")
    assert eintrag(wanderung, bid)["zu"] == "reise"


# ---------- Rechte, Titelbild, Zurückziehen (V2, V5, V6, AC-3, AC-4) ----------

def test_rechte_in_reise_und_schreibweg():
    alle = rg.BAUSTEINE
    for w in ("bild_hinzufuegen", "bild_aendern"):
        assert w in sb.WERKZEUGE and w in sb.AKTIONEN and sb.AKTIONEN[w] in rg.AKTIONEN
    aktion = sb.AKTIONEN["bild_hinzufuegen"]
    assert rg.erlaubt(aktion, "mitwirkend", "planung", alle)[0]
    assert not rg.erlaubt(aktion, "gast", "planung", alle)[0]
    assert "titelbild" in rg.AKTIONEN and rg.AKTIONEN["titelbild"]["rolle"] == "organisator"
    assert not rg.erlaubt("titelbild", "mitwirkend", "planung", alle)[0] and rg.erlaubt("titelbild", "organisator", "planung", alle)[0]


def test_titelbild_nur_organisator_und_hoechstens_eines(wanderung, monkeypatch):
    Netz(monkeypatch)
    with pytest.raises(sb.Ablehnung) as e:
        neu_hinzu(wanderung, KARL, titelbild=True)
    assert e.value.schluessel == "bild.abgelehnt.rolle"
    a, _ = neu_hinzu(wanderung, KARL)                                  # ohne Titelbild darf Karl hinzufügen
    with pytest.raises(sb.Ablehnung) as e:
        sb.bild_aendern(wanderung, KARL, {"ziel": a, "titelbild": True})
    assert e.value.schluessel == "bild.abgelehnt.rolle"
    sb.bild_aendern(wanderung, IDA, {"ziel": a, "titelbild": True})
    b, _ = neu_hinzu(wanderung, IDA, titelbild=True)                  # ein neues Titelbild löst das bisherige ab
    titel = [x["id"] for x in liste(wanderung) if x.get("titelbild")]
    assert titel == [b]


def test_mitwirkend_aendert_zieht_zurueck_und_stellt_wieder_her(wanderung, monkeypatch):
    Netz(monkeypatch)
    bid, _ = neu_hinzu(wanderung, KARL)
    sb.bild_aendern(wanderung, KARL, {"ziel": bid, "bildunterschrift": "Neu", "alt": "Brücke", "zu": "O-01"})
    b = eintrag(wanderung, bid)
    assert (b["bildunterschrift"], b["alt"], b["zu"]) == ("Neu", "Brücke", "O-01")
    with pytest.raises(sb.Ablehnung) as e:
        sb.bild_aendern(wanderung, KARL, {"ziel": bid, "zu": "U-99"})
    assert e.value.schluessel == "bild.abgelehnt.ziel"
    sb.bild_aendern(wanderung, KARL, {"ziel": bid, "zurueckziehen": True})
    b = eintrag(wanderung, bid)
    assert b["status"] == "zurueckgezogen" and all((wanderung / f).exists() for f in b["dateien"].values())
    sb.bild_aendern(wanderung, KARL, {"ziel": bid, "wiederherstellen": True})
    assert eintrag(wanderung, bid)["status"] == "aktiv"


def test_grenze_je_reise(wanderung, monkeypatch):
    Netz(monkeypatch)
    vorhanden = len([b for b in liste(wanderung) if b["status"] == "aktiv"])
    p = wanderung / "reise.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8"))
    roh["bilder"] = {"max_anzahl": vorhanden + 1, "offline_mb": 25}
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    neu_hinzu(wanderung)
    with pytest.raises(sb.Ablehnung) as e:
        neu_hinzu(wanderung)
    assert e.value.schluessel == "bild.abgelehnt.grenze"
    roh["bilder"]["max_anzahl"] = vorhanden + 2
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    neu_hinzu(wanderung)


def test_vorgabe_der_grenze_ist_60():
    assert rg.VORGABEN_BILDER == {"max_anzahl": 60, "offline_mb": 25}


# ---------- Kennung BI- neben B- (V1, AC-9) ----------

def test_bi_und_b_werden_nicht_verwechselt(wanderung):
    assert "BI" in neu.ARTEN and "B" in neu.ARTEN
    (wanderung / "plan" / "notiz.md").write_text("BI-07 und B-03\n", encoding="utf-8")
    assert neu._nummern(wanderung, "BI") >= 7
    assert neu._nummern(wanderung, "B") < 7
    import re
    assert re.fullmatch(routen.MUSTER["bild"], "BI-03") and not re.fullmatch(routen.MUSTER["bild"], "B-03")
    assert not re.fullmatch(routen.MUSTER["buchung"], "BI-03")
    assert sb.ID_MUSTER.match("BI-03") and sb.ID_MUSTER.match("B-03")


def test_modul_steht_in_der_deploy_liste():
    import re
    text = (WURZEL / "betrieb" / "deploy.sh").read_text(encoding="utf-8")
    for liste_ in ("KN_MODULE", "SB_MODULE"):
        m = re.search(rf"{liste_}=\"?\(?([^\n)]*)", text)
        assert m and "bilder.py" in m.group(1), liste_


# ---------- Vorab-Abruf vor der Sperre (V7, AC-5) ----------

def test_abruf_laeuft_vor_der_sperre_und_der_unterprozess_geht_nicht_ins_netz(monkeypatch, request):
    from test_schreiben import IDA as IDA_S, env_mitschneiden, sperre_frei
    wurzel, _, arbeit, _ = request.getfixturevalue("repo")
    b = bilder_modul()
    aufrufe = []
    original = b.abrufen

    def abrufen(**kw):
        aufrufe.append(sperre_frei("beispielreise"))
        Netz(monkeypatch)
        return original(**kw)
    monkeypatch.setattr(b, "abrufen", abrufen)
    monkeypatch.setenv("FR_COMMONS_API", "http://127.0.0.1:9/")      # der Unterprozess fände dort nichts
    monkeypatch.setenv("FR_WIKIDATA_API", "http://127.0.0.1:9/")
    umgebungen = env_mitschneiden(monkeypatch)
    code, a = sb.anwenden_extern(sb.Schreiber(wurzel, arbeit), "beispielreise", "bild_hinzufuegen",
                                 {**IDA_S, "args": {"commons": "Basteibruecke.jpg", "zu": "E-01"}})
    assert code == 200 and a["ok"], a
    assert aufrufe == [True]
    assert len(umgebungen) == 1 and umgebungen[0].get("FR_BILD_VORAB"), umgebungen
    assert a.get("vorschau") and base64.b64decode(a["vorschau"])[:4] == b"RIFF"


# ---------- Konnektor (V4, V6) ----------

def test_werkzeuge_englisch_mit_deutschem_alias():
    import konnektor as kn
    import schnittstelle
    assert schnittstelle.NAMEN["image_add"] == "bild_hinzufuegen" and schnittstelle.NAMEN["image_update"] == "bild_aendern"
    tab = schnittstelle.parameter_zu_englisch("bild_hinzufuegen")
    assert tab["zu"] == "belongs_to" and tab["bildunterschrift"] == "caption" and tab["alt"] == "alt_text"
    assert tab["titelbild"] == "title_image" and tab.get("commons", "commons") == "commons"
    aendern = schnittstelle.parameter_zu_englisch("bild_aendern")
    assert aendern["zurueckziehen"] == "withdraw" and aendern["wiederherstellen"] == "restore"
    for w in ("bild_hinzufuegen", "bild_aendern"):
        assert w in kn.ONTOLOGIE_WERKZEUGE and kn.ONTOLOGIE_AKTION[w] == sb.AKTIONEN[w]


def test_konnektor_gibt_vorschau_als_bild_an_claude(request, monkeypatch):
    from test_konnektor import ALT_ORGANISATOR, GAST, KARL as KARL_TOKEN, Schreibweg, rpc
    basis, _ = request.getfixturevalue("schreibweg")
    namen = lambda token: {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}
    assert {"bild_hinzufuegen", "bild_aendern"} <= namen(KARL_TOKEN) and not {"bild_hinzufuegen", "bild_aendern"} & namen(GAST)
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", (480, 300), "green").save(puffer, "WEBP")
    monkeypatch.setattr(Schreibweg, "antwort", (200, {"ok": True, "text": "Bild BI-01 angelegt.",
                                                      "vorschau": base64.b64encode(puffer.getvalue()).decode()}))
    r = rpc(basis, ALT_ORGANISATOR, "tools/call", {"name": "image_add", "arguments": {
        "commons": "Basteibruecke.jpg", "belongs_to": "E-01", "caption": "Brücke", "title_image": True}})
    assert not r["isError"] and any(c["type"] == "image" for c in r["content"]), r
    pfad, _, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/bild_hinzufuegen"
    assert body["args"] == {"commons": "Basteibruecke.jpg", "zu": "E-01", "bildunterschrift": "Brücke", "titelbild": True}


def test_werkzeugliste_der_doku_nennt_die_bildwerkzeuge():
    text = (WURZEL / "docs" / "konnektor.md").read_text(encoding="utf-8")
    assert "image_add" in text and "image_update" in text


# ---------- Hotlink-Sperre (V10, AC-6, #581) ----------

def bau_meldungen(ordner):
    with tempfile.TemporaryDirectory() as t:
        with pytest.raises(bauen.BauFehler) as e:
            bauen.Bauer(ordner, t).daten()
    return e.value.meldungen


def text_anhaengen(ordner, zeile):
    p = ordner / "inhalt" / "wissen.md"
    p.write_text(p.read_text(encoding="utf-8").replace("### Der Hockstein\n", f"### Der Hockstein\n{zeile}\n\n", 1), encoding="utf-8")


@pytest.mark.parametrize("ziel", ["https://example.org/bild.jpg", "http://example.org/bild.png", "//example.org/bild.jpg"])
def test_fremdes_bild_im_text_ist_ein_baufehler(wanderung, ziel):
    text_anhaengen(wanderung, f"![Fremd]({ziel})")
    assert meldet(bau_meldungen(wanderung), "pruefung.bauen.bild_fremd")


def test_link_bleibt_erlaubt_und_csp_begrenzt_bilder(wanderung, tmp_path):
    text_anhaengen(wanderung, "[Fahrplan](https://example.org/fahrplan) und [anderswo](//example.org/x)")
    bauen.bauen(wanderung, tmp_path / "dist")
    seite = (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    import re
    regel = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', seite).group(1)
    assert "img-src 'self' data:" in regel


@pytest.mark.parametrize("ziel", ["https://example.org/x.jpg", "//example.org/x.jpg"])
def test_schreibweg_lehnt_fremdes_bild_im_text_ab(request, ziel):
    from test_schreiben import IDA as IDA_S, deutsch
    wurzel, _, arbeit, _ = request.getfixturevalue("repo")
    code, a = sb.anwenden_extern(sb.Schreiber(wurzel, arbeit), "beispielreise", "wissen_schreiben",
                                 {**IDA_S, "args": {"titel": "Testbild", "text": f"Ein Bild: ![x]({ziel})", "gruppe": "wissen",
                                                    "quelle": "eigene Beobachtung"}})
    assert code == 422 and not a["ok"], a
    assert meldet(deutsch(a), "pruefung.bauen.bild_fremd"), a
    from test_schreiben import auf_main
    assert "example.org" not in auf_main("beispielreise", "inhalt/wissen.md")


# ---------- BI- im Text (V10a, V16, AC-8) ----------

def bild_eintragen(ordner, bid="BI-01", zu="E-01", status="aktiv", quelle=None, lizenz="CC BY-SA 4.0", urheber="Max Muster"):
    from PIL import Image
    (ordner / "medien" / "bilder").mkdir(parents=True, exist_ok=True)
    dateien = {}
    for fassung, breite in (("klein", 480), ("gross", 1600)):
        rel = f"medien/bilder/{bid}-{breite}.webp"
        Image.new("RGB", (breite, breite * 10 // 16), "blue").save(ordner / rel, "WEBP")
        dateien[fassung] = rel
    b = {"id": bid, "zu": zu, "quelle": quelle or {"commons": "Basteibruecke.jpg"}, "status": status,
         "dateien": dateien, "breite": 1600, "hoehe": 1000, "hinzugefuegt": {"datum": "2026-11-15", "wer": "Ida"}}
    if quelle != "reise":
        b.update({"urheber": urheber, "lizenz": lizenz, "lizenz_url": "https://creativecommons.org/licenses/by-sa/4.0",
                  "seite": "https://commons.wikimedia.org/wiki/File:Basteibruecke.jpg"})
    p = ordner / "plan" / "bilder.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    roh = roh or {}
    roh["bilder"] = [x for x in (roh.get("bilder") or []) if x["id"] != bid] + [b]
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return b


def test_bi_im_text_zeigt_grosse_fassung_mit_nennung_und_im_precache(wanderung, tmp_path):
    b = bild_eintragen(wanderung, "BI-50")
    text_anhaengen(wanderung, "![Die Brücke](BI-50)")
    ziel = tmp_path / "dist"
    bauen.bauen(wanderung, ziel)
    seite = (ziel / "index.html").read_text(encoding="utf-8")
    assert b["dateien"]["gross"] in seite and (ziel / b["dateien"]["gross"]).exists()
    assert "Max Muster" in seite and "CC BY-SA 4.0" in seite and "commons.wikimedia.org/wiki/File:Basteibruecke.jpg" in seite
    import re
    dateien = json.loads(re.search(r"const DATEIEN = (\[.*\]);", (ziel / "sw.js").read_text(encoding="utf-8")).group(1))
    assert b["dateien"]["gross"] in dateien


def test_nennung_gemeinfrei_nur_urheber_und_aus_der_reise_ohne(wanderung, tmp_path):
    bild_eintragen(wanderung, "BI-51", lizenz="CC0", urheber="Erika Frei")
    bild_eintragen(wanderung, "BI-52", quelle="reise")
    text_anhaengen(wanderung, "![Frei](BI-51)\n\n![Eigen](BI-52)")
    bauen.bauen(wanderung, tmp_path / "dist")
    seite = (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    assert "Erika Frei" in seite and "creativecommons.org/publicdomain" not in seite
    assert "medien/bilder/BI-52-1600.webp" in seite


def test_zurueckgezogenes_bild_entfaellt_ohne_fehler_unbekanntes_ist_baufehler(wanderung, tmp_path):
    b = bild_eintragen(wanderung, "BI-53", status="zurueckgezogen")
    text_anhaengen(wanderung, "![Weg](BI-53)")
    bauen.bauen(wanderung, tmp_path / "dist")
    assert b["dateien"]["gross"] not in (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    text_anhaengen(wanderung, "![Gibts nicht](BI-98)")
    assert meldet(bau_meldungen(wanderung), "pruefung.bauen.bild_unbekannt")


# ---------- bilder_nachziehen (V11, AC-7) ----------

def test_nachziehen_stellt_altbestand_um_und_ist_idempotent(wanderung, tmp_path):
    p = wanderung / "inhalt" / "etappen.md"
    # die Beispielreise im Repo ist schon umgestellt (V24): für den Test den Altbestand wiederherstellen
    p.write_text(p.read_text(encoding="utf-8").replace(
        "![Skizze: Felsnadeln, Brücke und Fluss](BI-01)", "![Skizze: Felsnadeln, Brücke und Fluss](../medien/skizze-felsen.png)").replace(
        "![Skizze: Felsnadeln, Brücke und Fluss](../medien/skizze-felsen.png)",
        "![Skizze: Felsnadeln, Brücke und Fluss](../medien/skizze-felsen.png)\n\n![Fremd](https://example.org/f.jpg)"), encoding="utf-8")
    w = wanderung / "inhalt" / "wissen.md"     # ohne Liste auch ohne die Commons-Bilder der Beispielreise im Text
    w.write_text(re.sub(r"\n!\[[^\]]*\]\(BI-\d+\)\n", "\n", w.read_text(encoding="utf-8")), encoding="utf-8")
    shutil.rmtree(wanderung / "medien" / "bilder", ignore_errors=True)
    (wanderung / "plan" / "bilder.yaml").unlink(missing_ok=True)
    neu.nachziehen(wanderung)
    text = p.read_text(encoding="utf-8")
    assert "medien/skizze-felsen.png" not in text and "](https://example.org/f.jpg)" in text and "![Fremd]" not in text
    alt = [b for b in liste(wanderung) if b["quelle"] == "reise"]
    assert len(alt) == 1 and f"]({alt[0]['id']})" in text and alt[0]["zu"].startswith("E-")
    assert "lizenz" not in alt[0] and "urheber" not in alt[0]
    assert all((wanderung / f).suffix == ".webp" and (wanderung / f).exists() for f in alt[0]["dateien"].values())
    assert (wanderung / "medien" / "skizze-felsen.png").exists()                 # das Original bleibt in der Ablage
    stand = {f: f.read_bytes() for f in wanderung.rglob("*") if f.is_file()}
    neu.nachziehen(wanderung)
    assert {f: f.read_bytes() for f in wanderung.rglob("*") if f.is_file()} == stand
    bauen.bauen(wanderung, tmp_path / "dist")
    assert alt[0]["dateien"]["gross"] in (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")


def test_nachziehen_aendert_stadtwochenende_nicht(stadt):
    stand = {f: f.read_bytes() for f in stadt.rglob("*") if f.is_file()}
    neu.nachziehen(stadt)
    assert {f: f.read_bytes() for f in stadt.rglob("*") if f.is_file()} == stand


def test_nachziehen_aendert_die_beispielreise_nicht_mehr(wanderung):
    """Die Beispielreise im Repo ist schon umgestellt (V24): Altbestand steht als BI-, ein Bild mit Commons-Herkunft und ein Titelbild."""
    # nur die Dateien, die bilder_nachziehen berührt; volle Idempotenz der Beispielreise: #584
    def dateien():
        muster = ("plan/bilder.yaml", "ids.yaml", "inhalt/*.md", "medien/bilder/*")
        return {f: f.read_bytes() for m in muster for f in wanderung.glob(m) if f.is_file()}
    stand = dateien()
    neu.nachziehen(wanderung)
    assert dateien() == stand
    bilder = liste(wanderung)
    assert any("commons" in (b["quelle"] if isinstance(b["quelle"], dict) else {}) for b in bilder)
    assert sum(1 for b in bilder if b.get("titelbild")) == 1
    assert not (STADT / "plan" / "bilder.yaml").exists()


def test_beispielbilder_stehen_in_third_party():
    text = (WURZEL / "THIRD_PARTY.md").read_text(encoding="utf-8")
    for b in liste(WANDERUNG):
        if isinstance(b["quelle"], dict) and "commons" in b["quelle"]:
            assert b["quelle"]["commons"] in text and b["lizenz"] in text


# ---------- Export und Löschen nehmen die Bilddateien mit ----------

def test_bilddateien_werden_ausgelagert_und_exportiert(wanderung, tmp_path, monkeypatch):
    import reisespeicher as rs
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "_speicher"))
    b = bild_eintragen(wanderung, "BI-54")
    rs.importieren(wanderung, "beispielreise", wer="Ida", grund="Test")
    ziel = tmp_path / "wieder"
    rs.materialisieren("beispielreise", ziel)
    assert (ziel / b["dateien"]["klein"]).read_bytes() == (wanderung / b["dateien"]["klein"]).read_bytes()


# ---------- Seitentest unter der neuen CSP (V10, AC-6) ----------

@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_seite_unter_der_csp_ohne_meldung(tmp_path, browser):
    """Gebaute Beispielreise (Grundkarten als Attrappe wie test_karte_legende): Etappenkarte mit Kacheln und Ebenen-Symbol, Belege,
    App-Symbol und ein Bild ![…](BI-NN) mit Nennung, in Chromium und WebKit ohne CSP-Meldung in der Konsole und ohne Seitenfehler."""
    import functools
    import http.server
    import os
    import subprocess
    import threading
    from test_karte_legende import gebaut
    from test_tagesseite import PLAYWRIGHT
    if not PLAYWRIGHT.exists() or not shutil.which("node"):
        pytest.skip("Playwright fehlt")
    gebaut(tmp_path)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_bilder_csp.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    a = e["aus"]
    assert a["karte"]["marken"] and a["karte"]["kacheln"] and a["karte"]["ebenenSymbol"], a["karte"]
    assert a["symbol"] and all(a["symbol"]), a["symbol"]
    assert a["beleg"] == 1, a
    assert a["bild"] and all(x["breite"] > 0 for x in a["bild"]), a["bild"]
    assert any("CC BY-SA 4.0" in x["nennung"] for x in a["bild"]), a["bild"]


# ---------- Befunde der Gegenprüfung (F001 bis F007) ----------

def reise_yaml_bilder(ordner, wert):
    p = ordner / "reise.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8"))
    roh["bilder"] = wert
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")


def probebau(ordner):
    with tempfile.TemporaryDirectory() as t:
        return bauen.Bauer(ordner, t).daten()


def test_f001_bilder_in_reise_yaml_baut_und_hebt_die_grenze(wanderung, monkeypatch):
    Netz(monkeypatch)
    vorhanden = liste(wanderung)
    platzhalter = [{"id": f"BI-{n}", "zu": "reise", "quelle": "reise", "status": "aktiv"} for n in range(100, 160 - len(vorhanden))]
    p = wanderung / "plan" / "bilder.yaml"
    p.write_text(yaml.safe_dump({"bilder": vorhanden + platzhalter}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert len([b for b in liste(wanderung) if b["status"] == "aktiv"]) == 60
    with pytest.raises(sb.Ablehnung):
        neu_hinzu(wanderung)
    reise_yaml_bilder(wanderung, {"max_anzahl": 100, "offline_mb": 25})
    probebau(wanderung)                                                  # der Bau kennt den Schlüssel bilder
    bid, _ = neu_hinzu(wanderung)                                        # das 61. Bild wird angenommen
    assert eintrag(wanderung, bid)["status"] == "aktiv"


@pytest.mark.parametrize("wert", [{"max_anzahl": 0}, {"offline_mb": "viel"}, {"unbekannt": 1}, "60"])
def test_f001_falscher_bilder_block_ist_ein_baufehler(wanderung, wert):
    reise_yaml_bilder(wanderung, wert)
    assert meldet(bau_meldungen(wanderung), "pruefung.reise.bilder")


def test_f002_kaputtes_altbild_bleibt_und_der_rest_wird_umgestellt(wanderung):
    w = wanderung / "inhalt" / "wissen.md"
    w.write_text(re.sub(r"\n!\[[^\]]*\]\(BI-\d+\)\n", "\n", w.read_text(encoding="utf-8")), encoding="utf-8")
    (wanderung / "medien" / "kaputt.png").write_bytes(b"\x89PNG kaputt")
    text_anhaengen(wanderung, "![Kaputt](../medien/kaputt.png)")
    p = wanderung / "inhalt" / "etappen.md"
    p.write_text(p.read_text(encoding="utf-8").replace("(BI-01)", "(../medien/skizze-felsen.png)"), encoding="utf-8")
    shutil.rmtree(wanderung / "medien" / "bilder")
    (wanderung / "plan" / "bilder.yaml").unlink()
    meldungen = neu.nachziehen(wanderung, betrieb=False)
    assert any("kaputt.png" in m for m in meldungen), meldungen
    assert "](../medien/kaputt.png)" in w.read_text(encoding="utf-8")
    neu_ids = [b["id"] for b in liste(wanderung)]
    assert len(neu_ids) == 1 and f"]({neu_ids[0]})" in p.read_text(encoding="utf-8")
    assert all((wanderung / f).exists() for f in eintrag(wanderung, neu_ids[0])["dateien"].values())
    probebau(wanderung)
    stand = {f: f.read_bytes() for f in wanderung.rglob("*") if f.is_file()}
    neu.nachziehen(wanderung, betrieb=False)
    assert {f: f.read_bytes() for f in wanderung.rglob("*") if f.is_file()} == stand


def test_f003_titelbild_false_entfernt_nur_die_eigene_marke(wanderung, monkeypatch):
    Netz(monkeypatch)
    a, _ = neu_hinzu(wanderung, titelbild=True)
    b, _ = neu_hinzu(wanderung)
    sb.bild_aendern(wanderung, IDA, {"ziel": b, "titelbild": False})
    assert [x["id"] for x in liste(wanderung) if x.get("titelbild")] == [a]
    sb.bild_aendern(wanderung, IDA, {"ziel": a, "titelbild": False})
    assert [x["id"] for x in liste(wanderung) if x.get("titelbild")] == []


def test_f004_zurueckgezogenes_bild_ist_nie_titelbild(wanderung, monkeypatch):
    Netz(monkeypatch)
    a, _ = neu_hinzu(wanderung, titelbild=True)
    sb.bild_aendern(wanderung, KARL, {"ziel": a, "zurueckziehen": True})
    assert not eintrag(wanderung, a).get("titelbild")
    with pytest.raises(sb.Ablehnung) as e:
        sb.bild_aendern(wanderung, IDA, {"ziel": a, "titelbild": True})
    assert e.value.schluessel == "bild.abgelehnt.zurueckgezogen"


@pytest.mark.parametrize("schreibweise", ['BI-50 "Titel"', "bi-50", "BI-50 'Titel'"])
def test_f005_kennung_mit_titel_oder_klein_wird_aufgeloest(wanderung, tmp_path, schreibweise):
    b = bild_eintragen(wanderung, "BI-50")
    text_anhaengen(wanderung, f"![Die Brücke]({schreibweise})")
    bauen.bauen(wanderung, tmp_path / "dist")
    seite = (tmp_path / "dist" / "index.html").read_text(encoding="utf-8")
    assert b["dateien"]["gross"] in seite and 'src=\\"BI-50' not in seite and 'src=\\"bi-50' not in seite


def test_f005_unbekannte_kennung_klein_ist_baufehler(wanderung):
    text_anhaengen(wanderung, "![x](bi-97)")
    assert meldet(bau_meldungen(wanderung), "pruefung.bauen.bild_unbekannt")


@pytest.mark.parametrize("ziel", ["https://example.org/x.jpg", "//example.org/x.jpg", "/\\example.org/x.jpg", "/a.png",
                                  "data:image/png;base64,AAAA", "javascript:alert(1)", " https://example.org/y.jpg"])
def test_f007_nach_nachziehen_baut_jede_abgelehnte_bildquelle(wanderung, ziel):
    text_anhaengen(wanderung, f"![Alt]({ziel})")
    assert meldet(bau_meldungen(wanderung), "pruefung.bauen.bild_fremd") or bau_meldungen(wanderung)
    neu.nachziehen(wanderung, betrieb=False)
    probebau(wanderung)
    assert "![Alt](" not in (wanderung / "inhalt" / "wissen.md").read_text(encoding="utf-8")


def test_f007_trockenlauf_nennt_eindeutige_kennungen(wanderung):
    p = wanderung / "inhalt" / "etappen.md"
    p.write_text(p.read_text(encoding="utf-8").replace("(BI-01)", "(../medien/skizze-felsen.png)\n\n![Zwei](../medien/icon.svg)"),
                 encoding="utf-8")
    shutil.copy(wanderung / "medien" / "skizze-felsen.png", wanderung / "medien" / "zwei.png")
    p.write_text(p.read_text(encoding="utf-8").replace("../medien/icon.svg", "../medien/zwei.png"), encoding="utf-8")
    meldungen = neu.bilder_nachziehen(wanderung, schreiben=False)
    kennungen = re.findall(r"→ (BI-\d+)", " ".join(meldungen))
    assert len(kennungen) == 2 and len(set(kennungen)) == 2, meldungen


# ---------- P2: Daten an die Seite, Bild im Text, Offline in zwei Stufen, Beispielbilder (#455, Spec bilder-455-p2) ----------

def felder_setzen(ordner, bid, **felder):
    p = ordner / "plan" / "bilder.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8"))
    for b in roh["bilder"]:
        if b["id"] == bid:
            b.update(felder)
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")


def zeichenketten(x):
    """Alle Zeichenketten in den Seitendaten (die Texte der Abschnitte stehen als HTML darin)."""
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from zeichenketten(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from zeichenketten(v)


def figur(daten, bid):
    """Das <figure> mit data-bild="bid" aus den Texten der Seite, sonst None."""
    for s in zeichenketten(daten):
        for m in re.finditer(r"<figure\b[^>]*>.*?</figure>", s, flags=re.S):
            if f'data-bild="{bid}"' in m.group(0):
                return m.group(0)
    return None


def aktive_gruppen(bilder):
    """{zu: [aktive Bilder in der Reihenfolge der Liste]}; das erste je Ding ist sein Kopfbild."""
    gruppen = {}
    for b in bilder:
        if b.get("status", "aktiv") == "aktiv":
            gruppen.setdefault(b["zu"], []).append(b)
    return gruppen


def test_p2_daten_enthalten_nur_aktive_bilder_mit_nennung_als_daten(wanderung):
    """V12: daten()["bilder"] je aktivem Bild id, zu, klein, gross, alt, bildunterschrift, titel, nennung; Nennung als Daten
    (kein HTML), bei quelle: reise null, gemeinfrei nur der Urheber; zurückgezogene fehlen; Reihenfolge der Liste."""
    bild_eintragen(wanderung, "BI-60", zu="O-01", status="zurueckgezogen")
    bild_eintragen(wanderung, "BI-61", zu="O-01", lizenz="CC0", urheber="Erika Frei")
    felder_setzen(wanderung, "BI-61", alt="Ein Felsen", bildunterschrift="Der Felsen")
    d = probebau(wanderung)
    assert "bilder" in d, "daten() liefert keinen Schlüssel bilder"
    erwartet = [b for b in liste(wanderung) if b.get("status", "aktiv") == "aktiv"]
    assert [x["id"] for x in d["bilder"]] == [b["id"] for b in erwartet]
    assert "BI-60" not in [x["id"] for x in d["bilder"]]
    for x, b in zip(d["bilder"], erwartet):
        assert {"id", "zu", "klein", "gross", "alt", "bildunterschrift", "titel", "nennung"} <= set(x), x
        assert x["zu"] == b["zu"] and x["klein"] == b["dateien"]["klein"] and x["gross"] == b["dateien"]["gross"]
        assert x["klein"].startswith("medien/bilder/") and x["gross"].startswith("medien/bilder/")
        assert x["titel"] is bool(b.get("titelbild"))
        if b["quelle"] == "reise":
            assert x["nennung"] is None, x
        else:
            assert isinstance(x["nennung"], dict) and set(x["nennung"]) <= {"urheber", "lizenz", "lizenz_url", "seite"}, x
            assert not any("<" in str(v) for v in x["nennung"].values()), x["nennung"]
            assert x["nennung"]["urheber"] == b["urheber"]
    frei = next(x for x in d["bilder"] if x["id"] == "BI-61")
    assert {k: v for k, v in frei["nennung"].items() if v} == {"urheber": "Erika Frei"}, frei["nennung"]
    assert frei["alt"] == "Ein Felsen" and frei["bildunterschrift"] == "Der Felsen"
    cc = next(x for x in d["bilder"] if x["id"] == "BI-03")
    assert cc["nennung"]["lizenz"] == "CC BY-SA 4.0" and cc["nennung"]["seite"].startswith("https://commons.wikimedia.org/")


def test_p2_stadtwochenende_ohne_bilddaten_und_ohne_bilddateien(stadt, tmp_path):
    """AC-3 (AC-12): ohne aktive Bilder fehlt der Schlüssel bilder ganz, und es gibt keine Bilddateien (Schutz gegen Rückschritt)."""
    ziel = tmp_path / "dist"
    bauen.bauen(stadt, ziel)
    roh = (ziel / "daten.json").read_text(encoding="utf-8")
    assert "bilder" not in json.loads(roh)
    assert not (ziel / "medien" / "bilder").exists() or not any((ziel / "medien" / "bilder").iterdir())
    assert 'data-bild=' not in roh


def test_p2_nur_zurueckgezogene_bilder_heisst_keine_bilddaten(wanderung):
    """AC-3: eine Reise, deren Bilder alle zurückgezogen sind, trägt keinen Schlüssel bilder (wie eine ohne Bilder)."""
    (wanderung / "plan" / "bilder.yaml").unlink()
    for name in ("wissen.md", "etappen.md"):
        p = wanderung / "inhalt" / name
        p.write_text(re.sub(r"!?\[[^\]]*\]\(BI-\d+\)", "", p.read_text(encoding="utf-8")), encoding="utf-8")
    bild_eintragen(wanderung, "BI-01", zu="E-01", status="zurueckgezogen")
    assert "bilder" not in probebau(wanderung)


def test_p2_bild_im_text_ist_ein_figure_mit_bildtext_und_nennung(wanderung):
    """V15: ![…](BI-NN) wird im Bau zu <figure> mit button.bild.text[data-bild] und figcaption mit .bildtext und .nennung (V16);
    die P1-Zeile <br><small class="nennung"> gibt es nicht mehr."""
    bild_eintragen(wanderung, "BI-50")
    felder_setzen(wanderung, "BI-50", bildunterschrift="Die Brücke am Morgen", alt="Steinbrücke")
    bild_eintragen(wanderung, "BI-51", lizenz="CC0", urheber="Erika Frei")
    bild_eintragen(wanderung, "BI-52", quelle="reise")
    text_anhaengen(wanderung, "![Die Brücke](BI-50)\n\n![Frei](BI-51)\n\n![Eigen](BI-52)")
    d = probebau(wanderung)
    f = figur(d, "BI-50")
    assert f, 'kein <figure> mit data-bild="BI-50"'
    knopf = re.search(r"<button\b[^>]*>", f).group(0)
    assert 'class="bild text"' in knopf and 'data-bild="BI-50"' in knopf and "aria-label=" in knopf, knopf
    assert "<img" in f and "medien/bilder/BI-50-1600.webp" in f and "<figcaption" in f
    assert re.search(r'class="bildtext"[^>]*>[^<]*Die Brücke am Morgen', f), f
    assert re.search(r'class="nennung"', f) and "Max Muster" in f and "CC BY-SA 4.0" in f, f
    assert "creativecommons.org/licenses/by-sa/4.0" in f and "commons.wikimedia.org/wiki/File:Basteibruecke.jpg" in f
    frei = figur(d, "BI-51")
    assert frei and "Erika Frei" in frei and "creativecommons.org" not in frei and "commons.wikimedia.org" not in frei, frei
    eigen = figur(d, "BI-52")
    assert eigen and 'class="nennung"' not in eigen, eigen
    assert not any('<small class="nennung">' in s for s in zeichenketten(d))


def test_p2_bildlink_im_satz_wird_als_bild_gezeigt(wanderung):
    """V12: [Text](BI-NN) im Satz: der Linktext bleibt im Satz, nach dem Absatz folgt dasselbe figure wie bei ![…](BI-NN);
    zurückgezogen: reiner Text ohne Fehler; unbekannt: Baufehler."""
    bild_eintragen(wanderung, "BI-55")
    bild_eintragen(wanderung, "BI-56", status="zurueckgezogen")
    text_anhaengen(wanderung, "Vom Hockstein sieht man [die alte Brücke](BI-55) gut. Früher stand dort [ein Turm](BI-56).")
    d = probebau(wanderung)
    absatz = next(s for s in zeichenketten(d) if "Vom Hockstein sieht man" in s)
    assert "die alte Brücke" in absatz and 'href="BI-55"' not in absatz, absatz
    f = figur(d, "BI-55")
    assert f and 'class="bild text"' in f and "medien/bilder/BI-55-1600.webp" in f, f
    assert f in absatz and absatz.index("die alte Brücke") < absatz.index(f), "figure folgt nicht nach dem Absatz"
    assert "ein Turm" in absatz and 'data-bild="BI-56"' not in absatz and 'href="BI-56"' not in absatz
    text_anhaengen(wanderung, "Und [das hier](BI-97) gibt es nicht.")
    assert meldet(bau_meldungen(wanderung), "pruefung.bauen.bild_unbekannt")


def test_p2_jedes_bild_im_text_genau_einmal_verpackt(wanderung):
    """F001 (Gegenprüfung): je Bild im Text und je Bildlink genau ein figure mit genau einem button[data-bild], darin genau ein
    img, und genau ein figcaption; nie ein figure im figure oder im Knopf (auch die Bilder der Beispielreise, BI-01 und BI-03)."""
    bild_eintragen(wanderung, "BI-57")
    felder_setzen(wanderung, "BI-57", bildunterschrift="Unterschrift")
    bild_eintragen(wanderung, "BI-58")
    text_anhaengen(wanderung, "![Brücke](BI-57)\n\nVom Hockstein sieht man [die Brücke](BI-58) gut.")
    html = "".join(zeichenketten(probebau(wanderung)))
    for bid in ("BI-01", "BI-03", "BI-57", "BI-58"):
        knoepfe = re.findall(rf'<button\b[^>]*data-bild="{bid}"[^>]*>(.*?)</button>', html, flags=re.S)
        assert len(knoepfe) == 1, (bid, knoepfe)
        assert knoepfe[0].count("<img") == 1 and "<figure" not in knoepfe[0] and "<button" not in knoepfe[0], (bid, knoepfe[0])
        f = figur({"x": html}, bid)
        assert f.count("<figure") == 1 and f.count("<figcaption") <= 1, (bid, f)
    assert html.count("<figure") == html.count("</figure>")
    assert not re.search(r"<figure\b(?:(?!</figure>).)*<figure\b", html, flags=re.S), "figure im figure"
    assert sum(html.count(f'data-bild="{b}"') for b in ("BI-57", "BI-58")) == 2
    assert figur({"x": html}, "BI-57").count("<figcaption") == 1


def sw_dateien(ziel):
    return json.loads(re.search(r"const DATEIEN = (\[.*\]);", (ziel / "sw.js").read_text(encoding="utf-8")).group(1))


def test_p2_precache_kleine_alle_grosse_nur_titel_kopf_und_text(wanderung, tmp_path):
    """V20, AC-5 (AC-14): __DATEIEN__ enthält alle kleinen Fassungen und die großen von Titel- und Kopfbildern (erstes Bild je
    Ding) und von Bildern im Text, übrige große nicht; kopiert werden alle Fassungen."""
    bild_eintragen(wanderung, "BI-62", zu="O-02")
    bild_eintragen(wanderung, "BI-63", zu="O-02")
    ziel = tmp_path / "dist"
    bauen.bauen(wanderung, ziel)
    dateien = set(sw_dateien(ziel))
    gruppen = aktive_gruppen(liste(wanderung))
    alle = [b for g in gruppen.values() for b in g]
    assert {b["dateien"]["klein"] for b in alle} <= dateien, {b["dateien"]["klein"] for b in alle} - dateien
    kopf = {g[0]["dateien"]["gross"] for g in gruppen.values()} | {b["dateien"]["gross"] for b in alle if b.get("titelbild")}
    assert kopf <= dateien, kopf - dateien
    im_text = set(re.findall(r"\]\((BI-\d+)\)", "".join(f.read_text(encoding="utf-8") for f in (wanderung / "inhalt").glob("*.md"))))
    uebrige = {b["dateien"]["gross"] for b in alle if b["dateien"]["gross"] not in kopf and b["id"] not in im_text}
    assert "medien/bilder/BI-63-1600.webp" in uebrige
    assert uebrige.isdisjoint(dateien), uebrige & dateien
    for b in alle:
        assert (ziel / b["dateien"]["klein"]).exists() and (ziel / b["dateien"]["gross"]).exists(), b["id"]


def test_p2_jpeg_pipeline_unter_medien_bleibt_und_alles_wird_aufgeraeumt(wanderung, tmp_path):
    """AC-5: ein Bild aus medien/ (nicht der Bilderliste) wird wie vorher verkleinert, ausgeliefert und vorab geladen;
    nicht mehr gebrauchte Dateien in der Ablage der Seite werden entfernt (Schutz gegen Rückschritt)."""
    from PIL import Image
    Image.new("RGB", (2400, 1600), "green").save(wanderung / "medien" / "foto-p2.jpg", "JPEG")
    text_anhaengen(wanderung, "![Foto](../medien/foto-p2.jpg)")
    ziel = tmp_path / "dist"
    (ziel / "medien" / "bilder").mkdir(parents=True)
    (ziel / "medien" / "bilder" / "BI-99-480.webp").write_bytes(b"alt")
    bauen.bauen(wanderung, ziel)
    assert "medien/foto-p2.jpg" in sw_dateien(ziel)
    with Image.open(ziel / "medien" / "foto-p2.jpg") as im:
        assert im.width == 1600
    assert not (ziel / "medien" / "bilder" / "BI-99-480.webp").exists()


def test_p2_warnung_ueber_offline_grenze_und_der_bau_gelingt(wanderung, tmp_path):
    """V3, AC-6 (AC-14): Summe der Vorab-Bilddateien über bilder.offline_mb -> Warnung mit Katalogtext
    (pruefung.bauen.bilder_offline), der Bau gelingt; unter der Grenze keine Warnung."""
    import os
    b = bild_eintragen(wanderung, "BI-64", zu="O-03")
    (wanderung / b["dateien"]["klein"]).write_bytes(os.urandom(1_500_000))
    reise_yaml_bilder(wanderung, {"offline_mb": 1})
    bau = bauen.Bauer(wanderung, tmp_path / "dist")
    bau.schreiben(bau.daten())
    assert (tmp_path / "dist" / "index.html").exists()
    assert meldet(bau.hinweise, "pruefung.bauen.bilder_offline"), bau.hinweise
    reise_yaml_bilder(wanderung, {"offline_mb": 25})
    bau = bauen.Bauer(wanderung, tmp_path / "dist2")
    bau.schreiben(bau.daten())
    assert not meldet(bau.hinweise, "pruefung.bauen.bilder_offline"), bau.hinweise


def test_p2_beispielbilder_frei_mit_third_party_titelbild_und_gruppe():
    """AC-8 (V24): echte freie Bilder (CC0, CC BY, CC BY-SA, gemeinfrei) mit je genau einer Zeile in THIRD_PARTY.md (Datei,
    Urheber, Lizenz, Seite); ein Titelbild, ein Ort mit 3 Bildern, Kopfbilder aus Commons an Tag, Etappe und Unterkunft."""
    bilder = liste(WANDERUNG)
    zeilen = (WURZEL / "THIRD_PARTY.md").read_text(encoding="utf-8").splitlines()
    for b in bilder:
        if b["quelle"] == "reise":
            continue
        assert re.fullmatch(r"CC0( 1\.0)?|CC BY(-SA)? \d\.\d( [a-z]{2,})?", b["lizenz"]) or bilder_modul().gemeinfrei(b["lizenz"]), \
            (b["id"], b["lizenz"])
        treffer = [z for z in zeilen if re.match(rf"\|\s*{b['id']}\b", z)]
        assert len(treffer) == 1, (b["id"], treffer)
        z = treffer[0]
        assert b["quelle"]["commons"] in z and b["urheber"] in z and b["lizenz"] in z and b["seite"] in z, z
        for f in b["dateien"].values():
            assert (WANDERUNG / f).is_file(), f
    gruppen = aktive_gruppen(bilder)
    assert sum(1 for b in bilder if b.get("titelbild")) == 1
    assert any(z.startswith("O-") and len(g) >= 3 for z, g in gruppen.items()), sorted(gruppen)
    for vorsilbe in ("T-", "E-", "U-"):
        assert any(z.startswith(vorsilbe) and g[0]["quelle"] != "reise" for z, g in gruppen.items()), (vorsilbe, sorted(gruppen))


# ---------- P2: Texte und Bausteine (AC-7) ----------

NEUE_TEXTE = ("seite.bild.anzahl", "seite.bild.schliessen", "seite.bild.grossansicht", "seite.bild.vorheriges",
              "seite.bild.naechstes", "seite.bild.zaehler", "pruefung.bauen.bilder_offline")


def test_p2_neue_texte_in_allen_sprachen():
    import texte
    for kuerzel in texte.SPRACHEN:
        katalog = texte.sprache(kuerzel).TEXTE
        fehlt = [k for k in NEUE_TEXTE if k not in katalog]
        assert fehlt == [], (kuerzel, fehlt)
    de = texte.sprache("de").TEXTE
    assert "{n}" in de["seite.bild.anzahl"], de["seite.bild.anzahl"]
    assert {"{ding}", "{i}", "{n}"} <= set(re.findall(r"\{\w+\}", de["seite.bild.zaehler"])), de["seite.bild.zaehler"]


def test_p2_bausteine_an_allen_vier_stellen():
    """V19: neue Bausteine im Kopfkommentar (damit prüft test_design Bausteinseite und docs/design.md), Stile mit den Maßen des
    Entwurfs, Token --r-gross statt --radius-gross; der Kopfkommentar des Service Workers sagt nicht mehr, alle Bilder würden
    bei der Installation vorab gespeichert."""
    from test_design import DESIGN, VORLAGE, bausteine
    namen = {n for l in bausteine().values() for n in l}
    fehlt = [n for n in ("bildEl", "miniEl", "galerieEl", "kopfBild") if n not in namen]
    assert fehlt == [], fehlt
    for klasse in (".bild", ".bild.titel", ".bild.kopf", ".bild.text", ".nennung", ".bildtext", ".mini", ".galerie", "#gross"):
        assert re.search(re.escape(klasse) + r"\s*[{,]", VORLAGE), klasse
    assert "--radius-gross" not in VORLAGE
    assert "Großansicht" in DESIGN
    assert not re.search(r"alle Bilder werden[^.]*vorab", (WURZEL / "engine" / "sw.vorlage.js").read_text(encoding="utf-8"))
