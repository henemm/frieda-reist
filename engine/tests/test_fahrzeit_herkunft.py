"""#508: Fahrzeit als eigene Kennzahl einer Fahrt, Herkunft je Wert statt Überschreiben der Herkunft der Strecke,
Hinweis auf Doppelte in der Packliste. Nur erfundene Daten: die Beispielreise."""
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import neu  # noqa: E402
import routen  # noqa: E402
import schreiben as sb  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"
IDA = {"name": "Ida", "rolle": "organisator"}
QUELLE_E21 = "Beispiel; Fahrplan nicht geprüft"


@pytest.fixture
def reise(tmp_path):
    ziel = tmp_path / "beispielreise"
    shutil.copytree(BEISPIEL, ziel)
    return ziel


def strecke(r, sid):
    return yaml.safe_load((r / "plan/routen.yaml").read_text(encoding="utf-8"))["strecken"][sid]


def route(r):
    with tempfile.TemporaryDirectory() as t:
        return bauen.Bauer(r, t).daten()["route"]


def test_kennzahl_mit_quelle_ueberschreibt_die_herkunft_der_strecke_nicht(reise):
    """Der gemeldete Fall: Kennzahlen in merkmale, quelle oben. Die Herkunft der Strecke bleibt, der Wert trägt seine eigene."""
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "merkmale": {"kennzahlen": {"fahrzeit": "0:45"}}, "quelle": "Fahrplanauskunft (Beispiel)",
                                 "geprueft": "2026-11-11"})
    s = strecke(reise, "E-21")
    assert s["quelle"] == QUELLE_E21
    assert s["kennzahlen"]["fahrzeit"]["wert"] == "0:45"
    assert s["kennzahlen"]["fahrzeit"]["quelle"] == "Fahrplanauskunft (Beispiel)"
    assert str(s["kennzahlen"]["fahrzeit"]["geprueft"]) == "2026-11-11"
    r = route(reise)["strecken"]["E-21"]
    assert r["kennzahlen"] == {"fahrzeit": "0:45"}
    assert r["kennzahlen_herkunft"]["fahrzeit"] == {"quelle": "Fahrplanauskunft (Beispiel)", "geprueft": "2026-11-11"}


def test_kennzahlen_oben_mit_quelle_ebenso(reise):
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "kennzahlen": {"laenge": 38}, "quelle": "Karte (Beispiel)"})
    s = strecke(reise, "E-21")
    assert s["quelle"] == QUELLE_E21 and s["kennzahlen"]["laenge"] == {"wert": 38, "quelle": "Karte (Beispiel)"}


def test_quelle_allein_aendert_die_herkunft_des_dings(reise):
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "quelle": "neu geprüft (Beispiel)"})
    assert strecke(reise, "E-21")["quelle"] == "neu geprüft (Beispiel)"


def test_abfahrt_traegt_die_neue_herkunft(reise):
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "ab": "09:15", "quelle": "Fahrplan (Beispiel)"})
    s = strecke(reise, "E-21")
    assert s["quelle"] == QUELLE_E21
    assert any(isinstance(v, dict) and v.get("wert") == "09:15" and v.get("quelle") == "Fahrplan (Beispiel)"
               for v in (s.get("merkmale") or {}).values())


def test_gehzeit_einer_fahrt_wird_fahrzeit(reise):
    """Bahn ist nicht summiert: eine angegebene Gehzeit (auch „Dauer“) ist dort die Fahrzeit."""
    sb.ding_aendern(reise, IDA, {"ziel": "E-23", "kennzahlen": {"walking_time": "1:05"}})
    assert strecke(reise, "E-23")["kennzahlen"] == {"fahrzeit": "1:05"}
    sb.ding_aendern(reise, IDA, {"ziel": "E-23", "kennzahlen": {"driving_time": "1:10"}})
    assert strecke(reise, "E-23")["kennzahlen"] == {"fahrzeit": "1:10"}


def test_wanderung_behaelt_gehzeit_und_summe_ohne_fahrzeit(reise):
    vorher = route(reise)["summe"]["min"] if "summe" in route(reise) else None
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "kennzahlen": {"fahrzeit": "0:45"}})
    sb.ding_aendern(reise, IDA, {"ziel": "E-01", "kennzahlen": {"gehzeit": {"wert": "ca. 3:40 h", "quelle": "Dossier (Beispiel)"}}})
    s = strecke(reise, "E-01")["kennzahlen"]
    assert s["gehzeit"]["wert"] == "ca. 3:40 h" and routen.kennwerte(s)["min"] == 220
    if vorher is not None:
        assert route(reise)["summe"]["min"] == vorher


def test_fahrzeit_als_zahl_wird_abgelehnt(reise):
    with pytest.raises(sb.Ablehnung):
        sb.ding_aendern(reise, IDA, {"ziel": "E-21", "kennzahlen": {"fahrzeit": 45}})


def test_nachziehen_macht_aus_gehzeit_einer_fahrt_fahrzeit(reise):
    p = reise / "plan/routen.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('art: bus, quelle: "erfunden (Beispiel)"',
                                                        'art: bus, kennzahlen: {gehzeit: "1:05"}, quelle: "erfunden (Beispiel)"'), encoding="utf-8")
    neu.nachziehen(reise)
    assert strecke(reise, "E-23")["kennzahlen"] == {"fahrzeit": "1:05"}
    assert strecke(reise, "E-01")["kennzahlen"]["gehzeit"] == "ca. 3:40 h"   # Wanderung bleibt
    davor = p.read_bytes()
    neu.nachziehen(reise)
    assert p.read_bytes() == davor


def test_packliste_meldet_doppelte(reise):
    _, text = sb.gegenstand_anlegen(reise, IDA, {"art": "kleidung", "titel": "Wandersocke"})
    assert "G-03" in text and "Wandersocken" in text
    _, text = sb.gegenstand_anlegen(reise, IDA, {"art": "kleidung", "titel": "Mütze"})
    assert "G-03" not in text


def test_aehnlich_auch_bei_zusammengesetzten_woertern():
    gs = [{"id": "G-01", "titel": "Kotbeutel"}, {"id": "G-02", "titel": "Socken", "status": "entfaellt"}]
    assert [g["id"] for g in sb.gegenstaende_aehnlich(gs, "Hundekotbeutel")] == ["G-01"]
    assert [g["id"] for g in sb.gegenstaende_aehnlich(gs, "Kotbeutel (Hund)")] == ["G-01"]
    assert sb.gegenstaende_aehnlich(gs, "Socken") == []   # entfallene zählen nicht
    assert sb.gegenstaende_aehnlich(gs, "Regenjacke") == []


# Zwischenstopps (#509): S-Bahn Bad Schandau → Dresden der Beispielreise, erfundene Halte in Stadt Wehlen (O-02) und Hohnstein (O-03)
ABSCHNITTE = [{"nach": "O-02", "kennzahlen": {"fahrzeit": "0:20", "laenge": 12}, "halt": {"zweck": "Pause", "dauer": "0:30"}},
              {"nach": "O-03", "kennzahlen": {"fahrzeit": "0:15", "laenge": 9}, "halt": {"zweck": "Umsteigen", "dauer": "0:10"}},
              {"kennzahlen": {"fahrzeit": "0:40", "laenge": 30}}]


def test_zwischenstopps_eintragen_und_summen(reise):
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "merkmale": {"abschnitte": ABSCHNITTE}, "quelle": "Fahrplan (Beispiel)"})
    s = strecke(reise, "E-21")
    assert s["quelle"] == QUELLE_E21
    assert [a["nach"] for a in s["abschnitte"]] == ["O-02", "O-03", "O-01"]
    assert s["abschnitte"][0]["kennzahlen"]["fahrzeit"] == {"wert": "0:20", "quelle": "Fahrplan (Beispiel)"}
    assert "halt" not in s["abschnitte"][-1]
    r = route(reise)["strecken"]["E-21"]
    assert r["kennzahlen"]["fahrzeit"] == "1:15 h" and r["kennzahlen"]["laenge"] == 51
    assert r["halte"] == 2 and r["pausen"] == 40 and r["mit_pausen"] == "1:55 h"
    assert r["abschnitte"][1]["halt"] == {"zweck": "Umsteigen", "dauer": "0:10"}
    assert r["abschnitte"][0]["kennzahlen_herkunft"]["fahrzeit"]["quelle"] == "Fahrplan (Beispiel)"


def test_zwischenstopps_gehzeit_wird_fahrzeit_und_eigene_summe_gilt(reise):
    ab = [{"nach": "O-02", "kennzahlen": {"gehzeit": "0:20"}}, {"kennzahlen": {"gehzeit": "0:40"}}]
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "abschnitte": ab, "kennzahlen": {"fahrzeit": "1:30"}})
    s = strecke(reise, "E-21")
    assert s["abschnitte"][0]["kennzahlen"] == {"fahrzeit": "0:20"}
    assert route(reise)["strecken"]["E-21"]["kennzahlen"]["fahrzeit"] == "1:30"   # die eigene Angabe der Strecke gilt


@pytest.mark.parametrize("ab", [
    [{"nach": "O-02"}],                                                    # nur ein Abschnitt
    [{"nach": "O-02"}, {"nach": "O-03"}],                                  # endet nicht am Ziel
    [{"nach": "O-99"}, {}],                                                # Ort fehlt
    [{"nach": "O-02", "halt": {"dauer": "eine halbe Stunde"}}, {}],        # Dauer nicht h:mm
    [{"nach": "O-02"}, {"halt": {"zweck": "Pause"}}],                      # Halt am Ziel
])
def test_zwischenstopps_unstimmig_wird_abgelehnt(reise, ab):
    with pytest.raises(sb.Ablehnung):
        sb.ding_aendern(reise, IDA, {"ziel": "E-21", "abschnitte": ab})


def test_zwischenstopps_entfernen(reise):
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "abschnitte": ABSCHNITTE})
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "abschnitte": []})
    assert "abschnitte" not in strecke(reise, "E-21")


def test_zwischenstopps_unveraenderte_werte_behalten_ihre_herkunft(reise):
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "abschnitte": ABSCHNITTE, "quelle": "Fahrplan (Beispiel)"})
    neu_ab = [dict(a) for a in ABSCHNITTE]
    neu_ab[2] = {"kennzahlen": {"fahrzeit": "0:45", "laenge": 30}}
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "abschnitte": neu_ab, "quelle": "Routenplaner (Beispiel)"})
    s = strecke(reise, "E-21")
    assert s["abschnitte"][0]["kennzahlen"]["fahrzeit"]["quelle"] == "Fahrplan (Beispiel)"
    assert s["abschnitte"][2]["kennzahlen"]["fahrzeit"]["quelle"] == "Routenplaner (Beispiel)"


def test_routen_prueft_abschnitte_in_der_datei(reise):
    p = reise / "plan/routen.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('art: bus, quelle: "erfunden (Beispiel)"',
                                                        'art: bus, abschnitte: [{nach: O-02, halt: {zweck: Pause}}, {nach: O-03}], quelle: "erfunden (Beispiel)"'),
                 encoding="utf-8")
    with pytest.raises(bauen.BauFehler, match="E-23"):
        route(reise)


def test_karte_fuehrt_ueber_die_halte(reise):
    import karte
    sb.ding_aendern(reise, IDA, {"ziel": "E-21", "abschnitte": ABSCHNITTE})
    r = route(reise)
    orte = karte.ort_lagen(r)
    wege = karte.schematische_wege(r, orte)
    if "E-21" in wege:
        assert orte["O-02"] in wege["E-21"] and orte["O-03"] in wege["E-21"]


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_seite_zeigt_zwischenstopps_fahrzeit_und_herkunft(tmp_path, browser):
    """#508, #509: Die S-Bahn E-20 an ihrer Heimat mit einem erfundenen Halt: Kachel Fahrzeit mit Zeit mit Pausen, Kachel Halte,
    die Zeitleiste mit Abschnitten und die Herkunft je Wert."""
    from test_seite import seite_der_variante
    ersetzen = [('    art: bahn\n    quelle: "Beispiel; Fahrplan nicht geprüft"\n    merkmale:\n',
                 '    art: bahn\n    quelle: "Beispiel; Fahrplan nicht geprüft"\n'
                 '    kennzahlen: {fahrzeit: {wert: "0:28", quelle: "Fahrplanauskunft (Beispiel)", geprueft: 2026-11-11}}\n'
                 '    abschnitte:\n'
                 '      - {nach: O-06, kennzahlen: {fahrzeit: "0:12", laenge: 9}, halt: {zweck: "Umsteigen (Beispiel)", dauer: "0:10"}}\n'
                 '      - {nach: O-02, kennzahlen: {fahrzeit: "0:16", laenge: 11}}\n'
                 '    merkmale:\n')]
    e = seite_der_variante(tmp_path, browser, skript="seiten_strecke_heimat.mjs", routen_ersetzen=ersetzen)
    t = e["heimat"]["text"]
    for teil in ("Fahrzeit", "0:28", "mit Pausen 0:38 h", "Halte", "zusammen 10 min", "Umsteigen (Beispiel) · 10 min",
                 "20 km", "Herkunft", "Fahrplanauskunft (Beispiel)"):
        assert teil in t, (teil, t)
