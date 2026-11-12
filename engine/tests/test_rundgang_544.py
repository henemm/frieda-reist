"""Rundgang vom 12.11.2026 (frieda-reist#544, #545): Jede Kennung beider Beispielreisen führt als Adresse zu einem sichtbaren Ziel
(ADR-0003: ein Link führt zur Heimat, das Ding steht dort), am Handy und am Rechner. Gefunden waren: Elternbezug auf einen Block
eines Abschnitts, Strecke an einem Tag außerhalb des gezeigten Plans, nicht gewählte Unterkunft im zugeklappten Block, Möglichkeit
im Vergleich am Handy (Ziel war die verborgene Tabellenzeile), Kartenpunkt an einer Strecke. Dazu die Kleinigkeiten aus #545:
kein „undefined“ (Tag ohne Nummer in einer Möglichkeit), kein Komma nach „Wahl unterwegs:“, Tippfläche des Kopier-Knopfs."""
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
from test_tagesseite import PLAYWRIGHT, WURZEL  # noqa: E402


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_jede_kennung_fuehrt_zu_einem_sichtbaren_ziel(tmp_path, reise):
    bauen.bauen(WURZEL / "beispiel/reisen" / reise, tmp_path / "web" / reise)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_rundgang_544.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/{reise}/"],
                             capture_output=True, text=True, timeout=600, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    assert e["geprueft"] > 40, e["geprueft"]
    assert e["ohneZiel"] == [], e["ohneZiel"]   # #544
    assert e["roh"] == [], e["roh"]             # #545: Tag ohne Nummer zeigte „undefined“
    assert e["komma"] == [], e["komma"]         # #545: „Wahl unterwegs: , Nachmittag …“
    assert e["klein"] == [], e["klein"]         # #545: Tippfläche des Kopier-Knopfs


def test_tagnummer_im_titel_einer_wahlstelle_faellt_auch_mit_komma_weg():
    """#545: Die Regel, die „Tag 3: “ vor dem Titel einer Wahlstelle wegnimmt, nimmt auch „Tag 3, “ weg."""
    vorlage = (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")
    zeile = next(z for z in vorlage.splitlines() if z.strip().startswith("tagNr: new RegExp("))
    assert '\\\\s*[:,;–-]?\\\\s*"' in zeile, zeile
