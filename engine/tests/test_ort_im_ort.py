"""Ortsseite mit „liegt in“, den Orten darin und der Karte des Orts (ADR-0008, Schritt d, frieda-reist #335). Beispielreise:
die Orte am Weg liegen in der Region Sächsische Schweiz (O-07, ohne eigenen Text); Städtewochenende ohne „liegt in“.
Erfundene Testdaten der beiden Beispielreisen."""
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
import karte  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"


def test_region_ist_kein_punkt_und_keine_station(tmp_path):
    d = bauen.bauen(BEISPIELE / "beispielreise", tmp_path / "web" / "b")
    r = d["route"]
    assert all(r["eltern"][o] == "O-07" for o in ("O-02", "O-03", "O-04", "O-05", "O-06"))
    assert "O-07" not in r["eltern"] and "O-01" not in r["eltern"]
    # keine Strecke, keine Nacht in der Region: sie ist keine Station
    assert all("O-07" not in (s.get("von"), s.get("nach")) for s in r["strecken"].values())
    assert "O-07" in karte.regionen(r)


def seiten(tmp_path, reise, *orte):
    bauen.bauen(BEISPIELE / reise, tmp_path / "web" / "r")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_ort_im_ort.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/r/", *orte],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    return e


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_ortsseite_liegt_in_orte_darin_und_karte(tmp_path):
    e = seiten(tmp_path, "beispielreise", "O-03", "O-07", "O-02", "O-01")
    # Hohnstein: liegt in der Region (Link auf ihre Seite), Karte mit dem Ort und seiner Unterkunft mit Lage
    h = e["O-03"]
    assert h["titel"].startswith("Hohnstein") and h["liegtIn"].endswith("Sächsische Schweiz") and h["liegtInLink"] == "#O-07", h
    assert h["darin"] == [] and h["karte"] and h["hier"] == 1 and h["dinge"] >= 1, h
    # Die Region hat keinen Text und trotzdem eine Seite: die Orte darin als Zeilen, auf der Karte, sie selbst kein Punkt
    r = e["O-07"]
    assert r["titel"].startswith("Sächsische Schweiz") and r["liegtIn"] is None, r
    assert [z["href"] for z in r["darin"]] == ["#O-04", "#O-05", "#O-03", "#O-06", "#O-02"], r   # nach Namen
    assert r["karte"] and r["hier"] == 0 and r["darinMarken"] == 5, r
    # Ein Ort ohne eigene Seite ist auf der Seite der Region zu Hause: sein Link führt dorthin, zu seiner Zeile
    w = e["O-02"]
    assert w["titel"].startswith("Sächsische Schweiz") and {z["href"]: z["id"] for z in w["darin"]}["#O-02"] == "O-02", w
    assert {z["href"]: z["id"] for z in r["darin"]}["#O-03"] is None   # Hohnstein hat eine eigene Seite
    # Dresden liegt in keinem Ort: kein „liegt in“, keine Orte darin, Karte wie bisher
    d = e["O-01"]
    assert d["liegtIn"] is None and d["darin"] == [] and d["karte"] and d["hier"] == 1, d


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_stadtwochenende_ortsseite_wie_bisher(tmp_path):
    e = seiten(tmp_path, "stadtwochenende", "O-02")
    assert e["O-02"]["liegtIn"] is None and e["O-02"]["darin"] == [], e
