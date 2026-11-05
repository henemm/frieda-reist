"""„Zu tun“ mit erledigten Buchungen (frieda-reist#314): Offenes steht oben, Gebuchtes zugeklappt; ist alles gebucht, steht
„Zu buchen“ zugeklappt am Ende. Grundlage: Beispielreise mit Plan A fest (Kopie im Test), Buchungsstände erfunden."""
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
from test_tagesseite import PLAYWRIGHT, WURZEL, plan_fest  # noqa: E402


def _seite(tmp_path, alle_gebucht):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    plan_fest(quelle)
    if alle_gebucht:
        r = quelle / "plan" / "routen.yaml"
        d = yaml.safe_load(r.read_text(encoding="utf-8"))
        for bu in d.get("buchungen", {}).values():
            bu["status"] = "gebucht"
        mit = {x for bu in d.get("buchungen", {}).values() for x in bu.get("fuer") or []}
        n = len(d.get("buchungen", {}))
        for gruppe in ("unterkuenfte", "strecken", "aufenthalte"):   # Beispielwert: alles gebucht, je Ding eine Buchung B-… (#215)
            for did, x in d.get(gruppe, {}).items():
                if isinstance(x, dict) and did not in mit:
                    n += 1
                    d.setdefault("buchungen", {})[f"B-{n:02d}"] = {"fuer": [did], "status": "gebucht", "quelle": "Beispielwert (Test)"}
        r.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    bauen.bauen(quelle, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_zu_tun.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    return e


OHNE_BROWSER = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")


@OHNE_BROWSER
def test_alles_gebucht_steht_zugeklappt_am_ende_314(tmp_path):
    e = _seite(tmp_path, alle_gebucht=True)
    assert "zu-buchen" in e["reihe"] and e["reihe"][-1] == "zu-buchen", e["reihe"]
    assert e["vorher"] == {"da": True, "offen": 0, "gebucht": 0}, e["vorher"]
    assert e["nachher"]["gebucht"] > 0 and e["nachher"]["offen"] == 0, e["nachher"]
    assert e["link"]["gebucht"] > 0, e["link"]   # ein Link auf #zu-buchen zeigt ihn aufgeklappt


@OHNE_BROWSER
def test_teils_gebucht_offenes_oben_gebuchtes_zugeklappt_314(tmp_path):
    e = _seite(tmp_path, alle_gebucht=False)
    assert e["reihe"].index("zu-buchen") < e["reihe"].index("aufgaben"), e["reihe"]
    assert e["vorher"]["offen"] > 0 and e["vorher"]["gebucht"] == 0, e["vorher"]
    assert e["nachher"]["gebucht"] > 0, e["nachher"]
