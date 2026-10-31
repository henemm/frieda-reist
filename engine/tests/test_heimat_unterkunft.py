"""Heimat einer Unterkunft über mehrere Nächte im Browser (ADR-0003, frieda-reist#157, Prüfbericht 4.10): vollständig an
der ersten Nacht, an jeder weiteren nur als Zeile mit Link dorthin."""
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

WURZEL = Path(__file__).resolve().parent.parent.parent
from playwright_pfad import PLAYWRIGHT  # noqa: E402

# Erfundener zweiter Tag in Dresden (Beispielwert): Das Hotel am Elbufer (U-01) hat damit zwei Nächte, T-01 und T-07.
# Die Kopie im Test lässt die Beispielreise unverändert (deren feste Zahlen prüfen andere Tests).
ZWEITER_TAG = '  T-07: {titel: "Zweiter Tag in Dresden (erfunden, Beispiel)", nacht: U-01}\n'


def zwei_naechte_im_gewaehlten_plan(quelle):
    """Plan A fest (V-01.a gewählt, V-03.a ist es schon), damit es Tagesseiten gibt; U-01 an T-01 und T-07."""
    r = quelle / "plan" / "routen.yaml"
    t = r.read_text(encoding="utf-8")
    alt = '          - {datum: 2026-10-20, status: vorgeschlagen, wer: Claude, grund: "kürzeste Verbindung zum Bahnhof"}\n'
    route = "route: [T-01, T-02, T-03, V-01]"
    assert alt in t and route in t and "  T-06: {" in t
    t = t.replace(alt, alt + '          - {datum: 2026-10-24, status: gewaehlt, wer: Ida, grund: "Test"}\n')
    t = t.replace("  T-06: {", ZWEITER_TAG + "  T-06: {", 1)
    t = t.replace(route, "route: [T-01, T-07, T-02, T-03, V-01]")
    r.write_text(t, encoding="utf-8")


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_unterkunft_vollstaendig_nur_an_der_ersten_nacht(tmp_path):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    zwei_naechte_im_gewaehlten_plan(quelle)
    d = bauen.bauen(quelle, tmp_path / "web" / "beispiel")
    assert d["route"]["unterkuenfte"]["U-01"]["naechte"] == ["T-01", "T-07"]   # die Vorbedingung steht wirklich

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_heimat_unterkunft.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", "U-01", "T-01", "T-07"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    erste, zweite = e["naechte"]
    # Erste Nacht: die Unterkunft vollständig (ihre Karte), kein Verweis auf eine andere Nacht
    assert erste["da"] and erste["karten"] == 1 and erste["links"] == [], erste
    # Weitere Nacht: nur die Zeile, keine Karte, und ein Link zur Unterkunft an ihrer ersten Nacht
    assert zweite["da"] and zweite["karten"] == 0, zweite
    assert zweite["links"] == ["#U-01"], zweite
    # Der Link führt auf die Tagesseite der ersten Nacht, dort steht die Karte
    z = e["ziel"]
    assert z and z["tagseite"] and z["karte"] and z["kopf"] == erste["kopf"], (z, erste)
