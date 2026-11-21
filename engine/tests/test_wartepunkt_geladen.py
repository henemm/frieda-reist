"""Wartepunkt „Live-Daten geladen“ (#568): Nach dem Laden der Live-Daten zeichnet die Seite die Ansicht mit route(true) neu und ersetzt
dabei den Inhalt von #main. Browsertests, die vorher zugreifen, greifen auf Elemente, die gleich verschwinden. Die Seite setzt darum nach
diesem Neuzeichnen html[data-geladen]; die Messskripte warten darauf (#369, #457, #550: auf den Zielzustand warten)."""
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
from test_karte_legende import gebaut  # noqa: E402
from test_tagesseite import PLAYWRIGHT, WURZEL  # noqa: E402

ohne_browser = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
TESTS = Path(__file__).parent


def sonde(tmp_path, reise, anker, browser="chromium"):
    """Baut eine Beispielreise, öffnet sie mit abgebrochenem api/** und liefert die Messung von seiten_geladen.mjs. Die Wanderung bekommt
    wie in test_karte_legende.py Attrappen der Grundkarte, sonst gibt es keine Etappenkarte (.ekarte)."""
    if reise == "beispielreise":
        gebaut(tmp_path)
        pfad = "beispiel"
    else:
        quelle = tmp_path / "quelle"
        shutil.copytree(WURZEL / "beispiel/reisen" / reise, quelle)
        bauen.bauen(quelle, tmp_path / "web" / "r")
        pfad = "r"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(TESTS / "seiten_geladen.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/{pfad}/", anker],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    return e["aus"]


REISEN = [("beispielreise", "E-01"), ("stadtwochenende", "")]


@ohne_browser
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
@pytest.mark.parametrize("reise,anker", REISEN)
def test_signal_ohne_dienst(tmp_path, browser, reise, anker):
    """AC-1: Auch wenn alle Lader scheitern (api/** abgebrochen), setzt die Seite html[data-geladen] nach dem Neuzeichnen."""
    a = sonde(tmp_path, reise, anker, browser)
    assert a["geladen"] and a["signal"] == "1", a
    assert a["gesamt"] >= 2, ("Erstaufbau und Neuzeichnen nach den Live-Daten erwartet", a)


@ohne_browser
@pytest.mark.parametrize("reise,anker", REISEN)
def test_kein_neuzeichnen_nach_signal(tmp_path, reise, anker):
    """AC-2: Nach dem Signal ersetzt der Erstaufbau #main nicht mehr; die Etappenkarte bleibt dasselbe Element."""
    a = sonde(tmp_path, reise, anker)
    assert a["geladen"], a
    assert a["nachSignal"] == 0, a
    if reise == "beispielreise":
        assert a["hatKarte"] and a["karteGleich"] is True, a


@pytest.mark.parametrize("skript", ["seiten_karte_legende.mjs", "seiten_bilder_csp.mjs"])
def test_skripte_warten_auf_signal(skript):
    """AC-4: Vor dem ersten Zugriff auf .ekarte warten die Messskripte auf html[data-geladen]."""
    quelle = (TESTS / skript).read_text(encoding="utf-8")
    karte = quelle.index('waitForSelector(".ekarte"')
    assert "html[data-geladen]" in quelle[:karte], f"{skript}: kein Wartepunkt auf das Signal vor .ekarte"


def test_vorlage_setzt_signal_nach_neuzeichnen():
    """AC-1 statisch: Das Signal steht im then-Zweig nach route(true), nicht davor."""
    v = (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")
    start = v.index("Promise.all([ichLaden()")
    zweig = v[start:v.index("\n\n", start)]
    assert "route(true)" in zweig and "dataset.geladen" in zweig, zweig
    assert zweig.index("route(true)") < zweig.index("dataset.geladen"), zweig


def test_doku_nennt_wartepunkt():
    """AC-5: docs/design.md nennt data-geladen als Wartepunkt für Browsertests."""
    d = (WURZEL / "docs/design.md").read_text(encoding="utf-8")
    assert "data-geladen" in d, "docs/design.md nennt das Signal nicht"
