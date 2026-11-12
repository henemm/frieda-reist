"""Zwei sichtbare Änderungen aus dem Rundgang vom 12.11.2026 (frieda-reist#546, vom Product Owner am Entwurf freigegeben):
1. Tagesseite am Rechner: Hat der Tag keine Karte, steht die rechte Spalte neben dem Tageskasten statt einer leeren Hälfte.
2. Kartenpunkte (Dinge einer Art mit gruppe) stehen auf der Seite ihrer Strecke als Zeilen „Punkte am Weg“, nicht als Karten."""
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
from conftest import text  # noqa: E402
from test_tagesseite import PLAYWRIGHT, WURZEL  # noqa: E402


def rundgang(tmp_path, reise, etappe=""):
    daten = bauen.bauen(WURZEL / "beispiel/reisen" / reise, tmp_path / "web" / reise)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_rundgang_546.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/{reise}/", etappe],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    return daten, e


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_tagesseite_ohne_karte_hat_keine_leere_haelfte(tmp_path, reise):
    _, e = rundgang(tmp_path, reise)
    geprueft = 0
    for t in e["tage"]:
        if t["karte"] or not t["spalte"]:
            continue   # mit Karte bleibt der Tageskasten neben der Karte; ohne rechte Spalte gibt es nichts zu rücken
        geprueft += 1
        oben, spalte = t["oben"], t["spalte"]
        assert abs(spalte["o"] - oben["o"]) <= 2, t        # die rechte Spalte beginnt auf der Höhe des Tageskastens
        assert spalte["l"] >= oben["r"], t                  # rechts neben ihm, nichts überlappt
        assert oben["r"] - oben["l"] > t["breite"] * 0.55, t   # der Kasten füllt die linke Spalte
        if t["voll"]:
            assert t["voll"]["o"] >= max(oben["u"], spalte["u"]), t   # Wahl oder Nacht über die volle Breite steht darunter
    assert geprueft, "kein Tag ohne Karte mit rechter Spalte in der Beispielreise"


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_kartenpunkte_stehen_als_zeilen_punkte_am_weg(tmp_path):
    daten, e = rundgang(tmp_path, "beispielreise", "E-03")
    punkte = daten["route"]["punkte"]["E-03"]
    assert all(p.get("ding", "").startswith("A-") for p in punkte)   # der Punkt nennt sein Ding (routen.kartenpunkte_aus_dingen)
    p = e["punkte"]
    assert p["titel"] == [text("seite.karte.punkte_am_weg")]            # kein „Aufenthalte hier“ für Kartenpunkte
    assert [z["id"] for z in p["zeilen"]] == [x["ding"] for x in punkte]
    assert [z["name"] for z in p["zeilen"]] == [x["name"] for x in punkte]
    assert all(z["unter"] for z in p["zeilen"])                        # die Art des Punkts steht darunter
    assert p["karten"] == 0                                            # keine Karte mit Koordinaten und Einzelheiten je Punkt
    assert p["sprung"] is True                                         # ein Link auf den Punkt landet bei seiner Zeile
