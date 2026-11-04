"""Punkte der automatischen Karte (frieda-reist#310): Tipp oder Klick öffnet ein Popup am Punkt mit Name, Art, den Merkmalen der
Stufen „nötig“ und „gut zu wissen“ und dem Link zum Eintrag; am Rechner zeigt das Überfahren einen Kurztext; eine Ansicht nur
aus Arten öffnet auf ihren Punkten. Grundlage: Beispielreise ohne plan/karte.yaml, erfundene Koordinaten (Beispielwerte)."""
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
from test_karte_auto import LAGEN, punkt  # noqa: E402
from test_tagesseite import PLAYWRIGHT, WURZEL  # noqa: E402


def _seite(tmp_path, browser):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    cfg = json.loads((quelle / "reise.json").read_text(encoding="utf-8"))
    del cfg["routen"]["karte"]
    (quelle / "reise.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    (quelle / "plan" / "karte.yaml").unlink()
    y = quelle / "reise.yaml"
    y.write_text(y.read_text(encoding="utf-8").replace("bausteine: [varianten, karte, tagesseiten, rueckmeldungen, fragen, aufgaben, wuensche]",
                                                       "bausteine: [karte, tagesseiten, rueckmeldungen, fragen, aufgaben]"), encoding="utf-8")
    r = quelle / "plan" / "routen.yaml"
    d = yaml.safe_load(r.read_text(encoding="utf-8"))
    for oid, lage in LAGEN.items():
        d["orte"][oid]["punkt"] = punkt(lage)
    a01 = d["aufenthalte"]["A-01"]
    a01["punkt"] = punkt([50.9785, 14.1140])
    a01["merkmale"]["eintritt"] = {"wert": "6 €", "quelle": "erfunden (Test)"}         # Stufe „gut zu wissen“ (Vorgabe)
    a01["merkmale"]["dauer"] = {"wert": "zwei Stunden (Test)", "quelle": "erfunden (Test)"}   # Stufe „zusätzlich“: nicht im Popup
    # Zweite Besichtigung 300 m daneben, ohne Tag (Beispielwert): die Ansicht „Burg“ hat nur diese beiden eng liegenden Punkte
    d["aufenthalte"]["A-03"] = {"name": "Aussicht am Burgweg", "ort": "O-03", "art": "besichtigung", "quelle": "erfunden (Test)",
                                "punkt": punkt([50.9810, 14.1160])}
    d["karten_ansichten"] = [{"titel": "Burg", "arten": ["besichtigung"]}]
    r.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    bauen.bauen(quelle, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_karte_popup.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", "A-01", "Burg"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    return e["aus"]


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_punkt_mit_popup_kurztext_und_ausschnitt_310(tmp_path, browser):
    aus = _seite(tmp_path, browser)
    handy, rechner = aus["390"], aus["1300"]
    p = handy["popup"]
    assert p, "kein Popup am Punkt"
    assert p["imBild"], p
    for teil in ("Burg Hohnstein", "Besichtigung", "Geöffnet am Reisedatum", "Eintritt", "6 €"):
        assert teil in p["text"], (teil, p["text"])
    assert "zwei Stunden" not in p["text"], p["text"]
    assert "#A-01" in p["links"], p["links"]
    assert any("Burg Hohnstein" in t and "Besichtigung" in t for t in rechner["kurztext"]), rechner["kurztext"]
    for a in (handy["ansicht"], rechner["ansicht"]):   # Ansicht nur aus Arten: Ausschnitt auf ihre zwei Punkte, nicht die Reise
        assert a["punkte"] == 2 and a["alle"], a
        assert a["spanne"][0] < 0.05 and a["spanne"][1] < 0.05, a
