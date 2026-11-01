"""B2 auf Reise, Ortsseite, Wissen und Vergleich (frieda-reist#58, Entscheidung des Product Owners 1.11.2026) im Browser."""
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
from test_tagesseite import WURZEL, plan_fest  # noqa: E402


def nacht_offen(quelle):
    """Plan A wählt nur den letzten Tag; die Nacht in Hohnstein (V-03) ist wieder offen (erfunden, nur für den Test)."""
    r = quelle / "plan" / "routen.yaml"
    text = r.read_text(encoding="utf-8")
    for alt, neu in (("auswahl: [V-01.a, V-03.a]", "auswahl: [V-01.a]"),
                     ('status: gewaehlt, wer: Ida, grund: "liegt am Weg', 'status: vorgeschlagen, wer: Ida, grund: "liegt am Weg'),
                     ('status: verworfen, wer: Ida, grund: "Anstieg am Morgen"', 'status: vorgeschlagen, wer: Ida, grund: "Anstieg am Morgen"')):
        assert alt in text, alt
        text = text.replace(alt, neu)
    r.write_text(text, encoding="utf-8")


@pytest.fixture(scope="module")
def basis(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("b2")
    for name, aendern in (("fest", None), ("offen", nacht_offen)):
        q = tmp / ("quelle-" + name)
        shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", q)
        plan_fest(q)
        if aendern:
            aendern(q)
        bauen.bauen(q, tmp / "web" / name)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}/"
    s.shutdown()


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_b2_auf_reise_ort_wissen_vergleich(basis, browser):
    aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_b2.mjs"), str(PLAYWRIGHT), basis],
                         capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    for breite, a in e["aus"].items():
        rechner = int(breite) >= 1100
        # P1: An- und Abreise als Zeile wie die Zeitachse, kein Kasten
        assert a["reise"] == {"anab": [False, False], "kaesten": 0}, (breite, a["reise"])
        # O1: Abschnitte eines Orts als Lesetext, alle offen, Sprechblase im Kopf; kein Kasten, nichts steht über
        o = a["ort"]
        assert o["bloecke"] == 0 and o["kaesten"] == 0 and not o["ueber"], (breite, o)
        assert [x[0] for x in o["lesen"]] == ["Frauenkirche", "Abend an der Elbe"] and all(x[1] for x in o["lesen"]), (breite, o)
        # W1: Weitere Wege in der Wegtabelle mit Kennzahlen und Variante, keine Kacheln und keine Kästen; Kopf nur am Rechner
        w = a["wissen"]
        assert w["kacheln"] == 0 and w["bloecke"] == 0 and w["kaesten"] == 0, (breite, w)
        assert [x[0] for x in w["wege"]] == ["#E-04"], (breite, w)
        assert "6,6 km" in w["wege"][0][1] and "190 m" in w["wege"][0][1] and "Variante" in w["wege"][0][1], (breite, w)
        assert w["kopf"] == rechner, (breite, w)
        # V1–V4: Wahlstelle ohne Rahmen, im Vergleich kein Knopf am Wert, die Herkunft einmal je Möglichkeit
        # (Herkunftszeile, #58); Tabelle nur am Rechner, Frage mit Namen
        v = a["vergleich"]
        assert not v["rahmen"] and v["kaesten"] == [] and v["i"] == 0 and v["werte"] == 0 and v["herkunft"] > 0, (breite, v)
        assert v["tabelle"] == rechner and v["karten"] == (not rechner), (breite, v)
        assert v["umschalter"] == (int(breite) < 700), (breite, v)     # Karten oder Tabelle wählt nur das Handy
        assert v["einzeln"] == (not rechner), (breite, v)              # ohne Tabelle die Einzelheiten zum Aufklappen
        assert not v["kennung"] and v["frage"].startswith("Zu klären: „Unterkunft in Hohnstein wählen"), (breite, v)
        assert not v["ueber"], (breite, v)
        # Außerhalb des Vergleichs steht die Herkunft hinter dem Wert selbst
        assert v["tippen"][:2] == ["true", True] and "Quelle" in v["tippen"][2], (breite, v)
        assert v["tippenText"].startswith("85 €") or v["tippenText"].startswith("70 €"), (breite, v)
        if rechner:
            assert v["hover"], (breite, v)
