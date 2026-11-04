"""Leere Rubriken „Tagesplan“ und „Unterkünfte“ unter Wissen (frieda-reist#276): Abschnitte, die nur aus reise.json routen.tagesplan
und routen.unterkuenfte stammen und keinen eigenen Text haben, stehen nicht unter „Über diesen Plan“; ihr Aufruf führt zum Plan.
Mit eigenem Plantext bleiben sie, wie sie sind. Die Kopie im Test lässt die Beispielreise unverändert."""
import functools
import http.server
import json
import os
import re
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

OHNE_BROWSER = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")


def _seite(tmp_path, ohne_plantext):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    if ohne_plantext:   # Tagesplan und Unterkünfte ohne eigenen Text: nur noch die Einträge in reise.json
        p = quelle / "plan/plan.md"
        t = p.read_text(encoding="utf-8")
        p.write_text(re.split(r"\n## Tagesplan\n", t)[0], encoding="utf-8")
        rj = quelle / "reise.json"
        cfg = json.loads(rj.read_text(encoding="utf-8"))
        for titel in ("Tagesplan", "Unterkünfte"):
            del cfg["abschnitte"]["plan/plan.md"][titel]
        rj.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    d = bauen.bauen(quelle, tmp_path / "web" / "beispiel")
    return d


def _browser(tmp_path, *ids):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_plan_rubriken.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", *ids],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


@OHNE_BROWSER
def test_leere_plan_rubriken_nicht_unter_wissen_276(tmp_path):
    d = _seite(tmp_path, ohne_plantext=True)
    leer = {a["id"]: a for a in d["abschnitte"] if a.get("route_ansicht")}
    assert set(leer) == {"W-03", "W-04"} and not any(a["intro"] or a["bloecke"] for a in leer.values())   # Vorbedingung
    e = _browser(tmp_path, "W-03", "W-04")
    assert e["fehler"] == []
    assert "W-02" in e["zeilen"] and "W-03" not in e["zeilen"] and "W-04" not in e["zeilen"], e["zeilen"]
    for wid in ("W-03", "W-04"):   # vorhandene Links führen zum Plan (Reiter Reise mit der Zeitachse), nicht ins Leere
        z = e["ziele"][wid]
        assert z["reiter"] == "varianten" and z["achse"] and not z["leer"], (wid, z)


@OHNE_BROWSER
def test_plan_rubriken_mit_eigenem_text_bleiben_276(tmp_path):
    _seite(tmp_path, ohne_plantext=False)
    e = _browser(tmp_path)
    assert e["fehler"] == []
    assert {"W-02", "W-03", "W-04"} <= set(e["zeilen"]), e["zeilen"]
