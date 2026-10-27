"""Tagesseite in drei Ansichten (Fluss, Reiter, Magazin) und Kennung ohne „i“ im Browser."""
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

WURZEL = Path(__file__).resolve().parent.parent.parent
PLAYWRIGHT = Path(os.environ.get("PLAYWRIGHT_MODUL") or Path.home() / "playwright-tool/node_modules/playwright/index.mjs")


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_tagesseite_in_drei_ansichten(tmp_path, browser):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    y = yaml.safe_load((quelle / "reise.yaml").read_text(encoding="utf-8"))
    y.setdefault("darstellung", {})["tiefe"] = True   # Tagesseiten mit Plan-Baum, wie bei den echten Reisen
    (quelle / "reise.yaml").write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
    bauen.bauen(quelle, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_tagesseite.mjs"), str(PLAYWRIGHT), f"http://127.0.0.1:{s.server_address[1]}/beispiel/"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    for breite, ansichten in e["aus"].items():
        for a in ("fluss", "reiter", "magazin"):
            x = ansichten[a]
            assert x["gedrueckt"] == a and not x["breit"], (breite, a, x)     # Schalter wirkt, nichts steht seitlich über
            assert x["knoepfe"] > 0 and x["info"] == 0, (breite, a, x)         # Kennung ohne „i“ und ohne eingebautes Feld
        assert ansichten["reiter"]["reiter"] >= 2
        assert ansichten["reiterWechsel"].count(True) == 1 and ansichten["reiterWechsel"][1] is True
        assert all(ansichten["tiefenlink"].values()) and set(ansichten["tiefenlink"]) == {"reiter", "magazin", "fluss"}, ansichten["tiefenlink"]
        assert ansichten["fenster"]["offen"] and ansichten["fenster"]["kopieren"] and ansichten["fenster"]["kennung"]
    # Seitenindex: am Rechner an der Seite, am Handy als Aufklappzeile
    assert e["aus"]["1300"]["magazin"]["index"] and not e["aus"]["1300"]["magazin"]["indexKlein"]
    assert e["aus"]["390"]["magazin"]["indexKlein"] and not e["aus"]["390"]["magazin"]["index"]
