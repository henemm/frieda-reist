"""Automatische Karte auf der Seite (Epic #225): Reiter „Karte“ ohne Baustein Varianten (#231), Punkte mit Farbe der Art und
Alternativen (#234), Kartenansichten (#236), Aufenthalte ohne Tag (#235), Tageskarte (#237). Grundlage: Beispielreise ohne
plan/karte.yaml, dazu erfundene Koordinaten (Beispielwerte)."""
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
from test_karte_auto import mit_lagen, punkt  # noqa: E402
from test_tagesseite import PLAYWRIGHT, WURZEL, plan_fest  # noqa: E402


def seite(tmp_path, browser, fest=False, bausteine="[karte, tagesseiten, rueckmeldungen, fragen, aufgaben]", fall=None):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    if fest:
        plan_fest(quelle)
    cfg = json.loads((quelle / "reise.json").read_text(encoding="utf-8"))
    del cfg["routen"]["karte"]
    (quelle / "reise.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    (quelle / "plan" / "karte.yaml").unlink()
    y = quelle / "reise.yaml"
    y.write_text(y.read_text(encoding="utf-8").replace("bausteine: [varianten, karte, tagesseiten, rueckmeldungen, fragen, aufgaben, wuensche]",
                                                       f"bausteine: {bausteine}"), encoding="utf-8")
    r = quelle / "plan" / "routen.yaml"
    d = yaml.safe_load(r.read_text(encoding="utf-8"))
    mit_lagen(d)
    d["unterkuenfte"]["U-02"]["punkt"] = punkt([50.9792, 14.1128])
    d["unterkuenfte"]["U-03"]["punkt"] = punkt([50.9700, 14.1000])
    d["aufenthalte"]["A-01"]["punkt"] = punkt([50.9785, 14.1140])
    # Wochenmarkt: ohne Tag, sein Ort (erfunden, ohne Ortsseite) hat keine Seite, also „noch ohne Platz“ am Ende der Reise (#432);
    # Bäckerei: ohne Tag, aber mit Heimat auf der Seite ihres Orts (Dresden), steht in der Reise gar nicht
    d["orte"]["O-90"] = {"name": "Nachbardorf", "an": "O-07", "quelle": "erfunden (Test)"}
    d["aufenthalte"]["A-02"] = {"name": "Wochenmarkt", "ort": "O-90", "art": "besichtigung", "quelle": "erfunden (Test)",
                                "punkt": punkt([51.050, 13.740])}
    d["aufenthalte"]["A-90"] = {"name": "Bäckerei am Markt", "ort": "O-01", "art": "besichtigung", "quelle": "erfunden (Test)"}
    d["aufenthalte"].pop("A-32", None)   # Fischbrötchen (ohne Tag, #387) gehört nicht zu diesem Fall
    d["karten_ansichten"] = [{"titel": "Hohnstein", "tage": ["T-02"]}, {"titel": "Vor Ort", "arten": ["besichtigung"]}]
    r.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    bauen.bauen(quelle, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_karte.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", fall or ("fest" if fest else "offen")],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    return e["aus"]


ohne_browser = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")


@ohne_browser
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_karte_unter_reise_ohne_varianten_mit_ansichten_und_ohne_tag(tmp_path, browser):
    for breite, a in seite(tmp_path, browser).items():
        # Baustein Karte allein bringt den Reiter „Karte“ (K10); keine Pläne nebeneinander
        assert "Karte" not in a["reiter"], a["reiter"]   # kein eigener Reiter mehr: die Karte steht unter Reise (#425)
        assert a["vergroessert"]["gross"] and a["vergroessert"]["hoehe"] > a["klein"]["hoehe"] and not a["klein"]["gross"], a
        assert a["vergroessert"]["hoehe"] >= a["vergroessert"]["fenster"] * 0.5 and not a["zu"]["gross"] and a["knopfSchliesst"], a
        assert a["kartenboxen"] == 1 and a["steckbriefe"] == 0, a
        # Übersicht: alle Punkte mit Lage (U-02, U-03 als Alternative, A-01, A-02), Farbe der Art, Alternative als Umriss
        assert a["punkte"]["uebersicht"] == {"gefuellt": 3, "umriss": 1}, a["punkte"]
        assert {"Pension", "Gasthof", "Besichtigung", "Alternative", "schematisch (ohne GPX-Track)"} <= set(a["legende"]), a["legende"]
        assert a["gestrichelt"] > 0, a
        # Ansichten zur Auswahl; „Vor Ort“ zeigt nur Besichtigungen, „Hohnstein“ nur Tag 2 mit seinen Alternativen
        assert a["ansichten"] == ["Übersicht", "Hohnstein", "Vor Ort"], a["ansichten"]
        assert a["punkte"]["Vor Ort"] == {"gefuellt": 2, "umriss": 0} and a["punkte"]["Hohnstein"] == {"gefuellt": 2, "umriss": 1}, a["punkte"]
        # Aufenthalt ohne Tag (#432): nur wer keine Seite anderswo hat, steht am Ende der Reise, zugeklappt; ein Sprung dorthin klappt auf
        assert a["ohneTag"] == ["Wochenmarkt"] and not a["imTagesplan"], a
        assert a["ohneTagBlock"] == {"titel": "Noch ohne Platz (1)", "offen": False}, a["ohneTagBlock"]
        assert "Bäckerei am Markt" not in a["reiseText"] and a["sprungOffen"], a
        assert not a["breit"], a


@ohne_browser
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_tageskarte_am_tag_mit_strecke(tmp_path, browser):
    for breite, a in seite(tmp_path, browser, fest=True, bausteine="[varianten, karte, tagesseiten, fragen]").items():
        assert a["reiter"][0] == "Reise" and a["kartenboxen"] == 1, a
        # Tag 2 hat Strecken: ein Ausschnitt mit den Punkten des Tags (Pension Burgblick, Gasthof als Alternative, Burg)
        assert a["tag2"] == {"karten": 1, "gefuellt": 2, "umriss": 1, "schematisch": True}, a["tag2"]
        # Tag 1 hat keine Strecke: keine Karte, kein leerer Rahmen
        assert a["tag1"] == {"karten": 0, "gefuellt": 0, "umriss": 0, "schematisch": False}, a["tag1"]


@ohne_browser
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_zwei_plaene_erscheinen_auf_der_automatischen_karte_in_zwei_farben(tmp_path, browser):
    """K16 (#234): Mit Baustein Varianten und zwei offenen Plänen zeichnet die automatische Karte auf dem Reiter „Varianten“ die Strecken in den Planfarben
    der Pläne (Plan A = a, Plan B = b); Strecken beider Pläne einmal neutral. Die Beispielwerte kommen aus der Beispielreise."""
    for breite, a in seite(tmp_path, browser, bausteine="[varianten, karte, tagesseiten, fragen]", fall="plaene").items():
        assert a["auto"], "die Karte muss die automatische sein (ohne plan/karte.yaml)"
        assert {"Plan A", "Plan B"} <= set(a["planLegende"]), a["planLegende"]
        assert {"rh-plan-a", "rh-plan-b"} <= set(a["planKlassen"]), a["planKlassen"]
        assert a["planFarben"]["rh-plan-a"] != a["planFarben"]["rh-plan-b"], a["planFarben"]
