"""Jede Seite jeder Beispielreise startet ohne Fehler (frieda-reist#387).

Anlass: Eine Startanweisung der Vorlage rief über mehrere Funktionen eine const auf, die weiter unten angelegt wird; der Fehler
trat nur bei einem Aufenthalt ohne Tag an einem Ort ohne eigenen Abschnitt auf, den keine Beispielreise hatte. Die Seite blieb leer.
Dieser Test lädt die gebaute Seite jeder Beispielreise (Start und jedes Ziel: Tage, Orte, Aufenthalte, Strecken, Unterkünfte,
Wahlstellen, Abschnitte, Reiter) und wird bei jedem Seitenfehler und jedem console.error rot. Erfundene Testdaten."""
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
from playwright_pfad import PLAYWRIGHT  # noqa: E402

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"


def lade_alle_seiten(tmp_path, reise):
    bauen.bauen(BEISPIELE / reise, tmp_path / "web" / "r")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_start.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/r/"],
                             capture_output=True, text=True, timeout=900, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_jede_seite_startet_ohne_fehler(tmp_path, reise):
    e = lade_alle_seiten(tmp_path, reise)
    assert e["fehler"] == [], sorted({x.split(": ", 1)[1] for x in e["fehler"]})[:8]
    # nicht nur kein Fehler: die Startseite hat Titel und Inhalt (eine leere Seite meldet manchmal nichts)
    assert e["seiten"][""]["inhalt"] > 0 and e["seiten"][""]["titel"], e["seiten"][""]
    assert len(e["seiten"]) > 30 if reise == "beispielreise" else len(e["seiten"]) > 10, len(e["seiten"])


def test_beispielreise_hat_den_fall_aus_387(tmp_path):
    """Voraussetzung des Tests oben: A-32 steht an keinem Tag, und sein Ort O-02 hat keinen eigenen Abschnitt."""
    d = bauen.bauen(BEISPIELE / "beispielreise", tmp_path / "web" / "b")
    a = d["route"]["aufenthalte"]["A-32"]
    assert a["ohne_tag"] and not a.get("tage") and a["ort"] == "O-02"
