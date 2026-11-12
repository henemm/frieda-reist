"""Tests für Datenschutz, Impressum und Alpha-Hinweis (#383, Meilenstein M5a, Spec docs/specs/betrieb/rechtliches-383.md).
Alle Angaben sind erfunden; die Betreiberangaben kommen über die Umgebung der Instanz (instanz.wert)."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anmeldung  # noqa: E402
import konten  # noqa: E402
import texte  # noqa: E402
from conftest import meldet  # noqa: E402
from test_anmeldung import IDA, KARL, abruf, anmelden, welt  # noqa: E402,F401  (welt: Fixture)

NAME, ANSCHRIFT, KONTAKT = "Beispiel-Betreiber", "Musterweg 1, 12345 Beispielstadt", "kontakt@example.org"
SEITEN = ("/datenschutz", "/impressum", "/alpha")
REPO = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def betreiber(tmp_path, monkeypatch):
    """Erfundene Betreiberangaben; die Einstellungsdatei der Instanz zeigt ins Leere."""
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(tmp_path / "keine-einstellungen.env"))
    monkeypatch.setenv("FR_BETREIBER_NAME", NAME)
    monkeypatch.setenv("FR_BETREIBER_ANSCHRIFT", ANSCHRIFT)
    monkeypatch.setenv("FR_BETREIBER_KONTAKT", KONTAKT)


def hole(u, pfad, **kw):
    return abruf(f"{u.kurl}{pfad}", **kw)


def hat_links(html_text, ausser=None):
    return all(f'href="{p}"' in html_text for p in SEITEN if p != ausser)


# ---------------------------------------------------------------- Seiten (AC-1)

@pytest.mark.parametrize("pfad", SEITEN)
def test_seiten_ohne_anmeldung_in_beiden_sprachen(welt, betreiber, pfad):
    u = welt()
    for sprache in ("de", "en"):
        s, _, t = hole(u, pfad, kopf={"Accept-Language": sprache})
        assert s == 200 and f'lang="{sprache}"' in t and 'name="robots" content="noindex"' in t
        assert meldet(t, f"recht.{pfad[1:]}.titel", sprache), (pfad, sprache)


def test_kontosprache_geht_vor_dem_browser(welt, betreiber):
    u = welt()
    token, _ = anmelden(u, IDA, name="Ida")
    konten.sprache_setzen(konten.sitzung(token)["id"], "en")
    s, _, t = hole(u, "/datenschutz", cookie=token, kopf={"Accept-Language": "de"})
    assert s == 200 and meldet(t, "recht.datenschutz.titel", "en")


@pytest.mark.parametrize("pfad", SEITEN)
def test_nur_get_post_wird_abgelehnt(welt, betreiber, pfad):
    u = welt()
    s, _, t = hole(u, pfad, methode="POST", felder={"x": "y"})
    assert s != 200 and not meldet(t, f"recht.{pfad[1:]}.titel")


def test_nur_die_drei_exakten_pfade_gehoeren_dem_dienst():
    for p in SEITEN:
        assert anmeldung.ist_unsere(p) and anmeldung.ist_unsere(p + "?x=1")
    for p in ("/impressum/x", "/impressum.html", "/datenschutz/", "/alpha/x", "/alphabet", "/datenschutzerklaerung"):
        assert not anmeldung.ist_unsere(p), p


@pytest.mark.parametrize("pfad", SEITEN)
def test_jede_seite_traegt_die_linkzeile_und_einen_weg_zurueck(welt, betreiber, pfad):
    u = welt()
    _, _, t = hole(u, pfad)
    assert hat_links(t, ausser=pfad) and 'class="fuss"' in t
    assert 'href="/warteliste"' in t or 'href="/anmelden"' in t


# ---------------------------------------------------------------- Impressum (AC-2, AC-3)

def test_impressum_zeigt_die_drei_angaben_maskiert(welt, betreiber, monkeypatch):
    u = welt()
    _, _, t = hole(u, "/impressum")
    assert NAME in t and ANSCHRIFT in t and KONTAKT in t
    monkeypatch.setenv("FR_BETREIBER_NAME", "<b>Bösewicht</b>")
    monkeypatch.setenv("FR_BETREIBER_ANSCHRIFT", "Musterweg 1\n12345 Beispielstadt")
    _, _, t = hole(u, "/impressum")
    assert "<b>Bösewicht</b>" not in t and "&lt;b&gt;" in t
    assert re.search(r"Musterweg 1(<br\s*/?>|\n)\s*12345 Beispielstadt", t)


@pytest.mark.parametrize("fehlt", ["FR_BETREIBER_NAME", "FR_BETREIBER_ANSCHRIFT", "FR_BETREIBER_KONTAKT"])
@pytest.mark.parametrize("leer", [False, True])
def test_leerfall_meldet_nicht_eingerichtet(welt, betreiber, monkeypatch, fehlt, leer):
    u = welt()
    if leer:
        monkeypatch.setenv(fehlt, "")
    else:
        monkeypatch.delenv(fehlt)
    s, _, t = hole(u, "/impressum")
    assert s == 200 and meldet(t, "recht.impressum.nicht_eingerichtet")
    assert not any(a in t for a in (NAME, ANSCHRIFT, KONTAKT))      # keine halb gefüllten Felder
    assert hole(u, "/warteliste")[0] == 200 and hole(u, "/anmelden")[0] == 200   # AC-3: nichts blockiert


@pytest.mark.parametrize("fehlt", ["FR_BETREIBER_NAME", "FR_BETREIBER_ANSCHRIFT", "FR_BETREIBER_KONTAKT"])
def test_leerraum_zaehlt_als_nicht_gesetzt(welt, betreiber, monkeypatch, fehlt):
    u = welt()
    monkeypatch.setenv(fehlt, "   ")
    s, _, t = hole(u, "/impressum")
    assert s == 200 and meldet(t, "recht.impressum.nicht_eingerichtet")
    assert not any(a in t for a in (NAME, ANSCHRIFT, KONTAKT))
    for feld in ("name", "anschrift", "kontakt"):                                 # keine Felder, auch kein leeres
        assert f"<strong>{texte.t('de', 'recht.impressum.' + feld)}</strong>" not in t, feld


@pytest.mark.parametrize("pfad", ("/datenschutz", "/alpha", "/warteliste", "/anmelden"))
def test_betreiberangaben_stehen_nur_im_impressum(welt, betreiber, pfad):
    u = welt()
    _, _, t = hole(u, pfad)
    # /alpha nennt seit #530 den Kontakt als Weg für Meldungen ohne Claude-App (Spec betreiber-meldung-530, AC-15); Name und
    # Anschrift bleiben nur im Impressum
    angaben = (NAME, ANSCHRIFT) if pfad == "/alpha" else (NAME, ANSCHRIFT, KONTAKT)
    assert not any(a in t for a in angaben)


def test_betreiberangaben_stehen_nicht_im_katalog():
    for sp in texte.sprachen():
        katalog = json.dumps(vars(texte.sprache(sp)), default=str, ensure_ascii=False)
        assert "Musterweg" not in katalog and "@example.org" not in katalog


# ---------------------------------------------------------------- Datenschutz (AC-6) und Alpha

def test_datenschutz_sagt_nur_zu_was_es_gibt(welt, betreiber):
    u = welt()
    for sprache in ("de", "en"):
        _, _, t = hole(u, "/datenschutz", kopf={"Accept-Language": sprache})
        assert meldet(t, "recht.datenschutz.konto_loeschen", sprache)        # vorhanden: Konto selbst löschen
        assert meldet(t, "recht.datenschutz.folgt", sprache)                 # Warteliste löschen/Export, Reisedaten-Export
        assert 'href="/impressum"' in t                                      # Rechte: Verweis aufs Impressum
    folgt = texte.t("de", "recht.datenschutz.folgt").lower()
    assert "folgt" in folgt and "löschen" in folgt and "export" in folgt


def test_alpha_seite_nennt_die_vorbehalte(welt, betreiber):
    u = welt()
    for sprache in ("de", "en"):
        _, _, t = hole(u, "/alpha", kopf={"Accept-Language": sprache})
        for schluessel in ("fehler", "datenverlust", "aenderungen", "claude_konto"):
            assert meldet(t, f"recht.alpha.{schluessel}", sprache), (sprache, schluessel)


# ---------------------------------------------------------------- Verlinkung (AC-4)

def test_linkzeile_auf_warteliste_anmeldeseiten_einladung_und_konto(welt, betreiber):
    u = welt()
    assert hat_links(hole(u, "/warteliste")[2])
    assert hat_links(hole(u, "/anmelden")[2])
    s, _, t = abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "adresse", "email": IDA})
    assert hat_links(t)                                                      # Code-Seite
    token, _ = anmelden(u, IDA, name="Ida")
    assert hat_links(hole(u, "/konto", cookie=token)[2])
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida", titel="Malerweg")
    link = re.search(r"/einladung/(\S+)", json.loads(u.mails.read_text().splitlines()[-1])["text"]).group(1)
    assert hat_links(hole(u, f"/einladung/{link}")[2])
    s, _, t = hole(u, "/einladung/gibt-es-nicht")                            # unbekannt oder abgelaufen
    assert s == 404 and hat_links(t)
    assert hat_links(hole(u, "/konto?loeschen=1", cookie=token)[2])          # Rückfrage vor dem Löschen
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "loeschen", "sicher": "ja"}, cookie=token)
    assert s == 200 and meldet(t, "konto.seite.geloescht") and hat_links(t)  # Konto gelöscht


def test_wartelistensatz_verlinkt_auf_alpha_und_datenschutzsatz_auf_die_erklaerung(welt, betreiber):
    u = welt()
    _, _, t = hole(u, "/warteliste")
    assert meldet(t, "warteliste.alpha") and 'href="/alpha"' in t
    _, _, t = hole(u, "/anmelden")
    assert meldet(t, "konto.datenschutz") and 'href="/datenschutz"' in t


# ---------------------------------------------------------------- Vorlage (AC-5)

def test_vorlage_hat_die_rechtszeile_mit_katalogschluesseln():
    v = (REPO / "engine" / "vorlage.html").read_text(encoding="utf-8")
    fuss = re.search(r'<footer[^>]*id="fuss"[^>]*>.*?</footer>', v, re.S).group(0)
    assert " hidden" not in fuss.split(">", 1)[0]                            # nicht mehr von Anfang an versteckt
    for pfad in SEITEN:
        a = re.search(rf'<a[^>]*href="{pfad}"[^>]*>', fuss)
        assert a, pfad
        schluessel = re.search(r'data-t="([^"]+)"', a.group(0))
        assert schluessel, pfad
        for sp in texte.sprachen():
            assert texte.t(sp, schluessel.group(1)) != schluessel.group(1), (sp, schluessel.group(1))
    zeigen = re.search(r"function fussZeigen\(\)\s*\{(.*?)\}", v, re.S).group(1)
    assert '$("#release").hidden' not in zeigen and '$("#sprachen").hidden' not in zeigen


def test_baustein_rechtszeile_ist_dokumentiert():
    v = (REPO / "engine" / "vorlage.html").read_text(encoding="utf-8")
    assert "Rechtszeile" in v.split("<body", 1)[0]
    assert "Rechtszeile" in (REPO / "docs" / "design.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- Texte (AC-7)

NEUE_SCHLUESSEL = ["recht.link.datenschutz", "recht.link.impressum", "recht.link.alpha", "recht.datenschutz.titel",
                   "recht.impressum.titel", "recht.alpha.titel", "recht.impressum.nicht_eingerichtet",
                   "recht.datenschutz.konto_loeschen", "recht.datenschutz.folgt", "recht.alpha.fehler",
                   "recht.alpha.datenverlust", "recht.alpha.aenderungen", "recht.alpha.claude_konto"]


def test_neue_schluessel_in_allen_sprachen():
    for sp in texte.sprachen():
        for s in NEUE_SCHLUESSEL:
            assert texte.t(sp, s) != s, (sp, s)


# ---------------------------------------------------------------- nginx und Einstellungen (AC-8)

def test_nginx_orte_fuer_die_drei_seiten():
    conf = (REPO / "betrieb" / "vorlagen" / "nginx-konnektor-orte.inc").read_text(encoding="utf-8")
    for p in SEITEN:
        i = conf.index(f"location = {p} ")
        assert "zone=__ZONE_KONTO__" in conf[i:conf.index("}", i)], p


def test_einstellungen_beispiel_nennt_die_betreiberangaben():
    b = (REPO / "betrieb" / "einstellungen.beispiel").read_text(encoding="utf-8")
    for n in ("FR_BETREIBER_NAME", "FR_BETREIBER_ANSCHRIFT", "FR_BETREIBER_KONTAKT"):
        assert re.search(rf"^#?\s*{n}=", b, re.M), n
