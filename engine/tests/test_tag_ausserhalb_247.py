"""Tag außerhalb der Zeitachse (frieda-reist#247, F005, F006 aus der Gegenprüfung zu #214). Ein Tag, den nur ein anderer Plan
enthält, zählt in diesem Plan; seine Blätterlinks führen aber auf Tagesseiten, die in der Zeitachse zählen. Sie tragen deshalb
keine Nummer, die dort nicht stimmt. Dazu: Eine Wahlstelle, die nur über an: an einer Unterkunft hängt, wohnt an der Nacht dieser
Unterkunft. Grundlage: Kopie der Beispielreise mit dem erfundenen Plan X aus test_tagesplan (Beispielwerte)."""
import datetime
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
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
from test_tagesseite import PLAYWRIGHT, WURZEL  # noqa: E402
from test_tagesplan import fest_mit_abweichenden_plaenen  # noqa: E402


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_blaetterlinks_ohne_fremde_nummer_und_heimat_ueber_an_247(tmp_path):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    fest_mit_abweichenden_plaenen(quelle, "nacht")   # Plan X zählt anders als die Zeitachse (eine Nacht mehr), wie in test_tagesplan
    r = quelle / "plan" / "routen.yaml"
    t = r.read_text(encoding="utf-8")
    gewaehlt = '          - {datum: 2026-10-24, status: gewaehlt, wer: Ida, grund: "Test"}\n'
    i = t.index(gewaehlt, t.index("kürzeste Verbindung zum Bahnhof"))
    r.write_text(t[:i] + t[i + len(gewaehlt):], encoding="utf-8")   # V-01 wieder offen: kein Plan ist vollständig gewählt
    d = yaml.safe_load(r.read_text(encoding="utf-8"))
    # F006: eine Wahlstelle, die nur über an: an der Unterkunft in Dresden hängt (keine Tage, kein wahl: an einem Tag)
    d["wahlstellen"]["V-09"] = {"titel": "Abendessen in Dresden (erfunden)", "wann": "unterwegs", "an": ["U-01"], "optionen": [
        {"id": "V-09.a", "titel": "Im Hotel", "quelle": "erfunden (Test)"},
        {"id": "V-09.b", "titel": "Am Elbufer", "quelle": "erfunden (Test)", "ausloeser": "bei schönem Wetter"}]}
    r.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    daten = bauen.bauen(quelle, tmp_path / "web" / "beispiel")
    px = next(p for p in daten["route"]["plaene"] if p["id"] == "P-X")
    assert "T-07" in [t["id"] for t in px["tage"]]   # Vorbedingung: T-07 gibt es nur in Plan X

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_tag_ausserhalb.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", "T-07", "V-09", "P-X"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    assert len(e["links"]) == 2, e["links"]
    for l in e["links"]:   # keine Nummer im Link, die auf der Zielseite nicht steht
        n = re.search(r"\d+", l["text"])
        assert not n or n.group(0) in l["kopf"], l
    assert e["heimat"] == {"tagseite": True, "tag": "T-01", "da": True}, e["heimat"]
