"""Legende der Karten nach Arten am Telefon (ADR-0007 Schritt d, frieda-reist#296): Die Etappenkarte bietet je Art eine Ebene mit Zähler,
die Karte eines Wissensabschnitts zeigt je Art einen Legendeneintrag; beide mit dem Namen der Art, im Fenster, ohne waagerechtes Scrollen,
bei 390 px und am Rechner. Die Beispielreise hat keine Grundkarte (PMTiles): der Test legt Attrappen an, die Kacheln fehlen, Karte,
Punkte und Bedienung funktionieren."""
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
from test_tagesseite import PLAYWRIGHT, WURZEL  # noqa: E402

ohne_browser = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")


def gebaut(tmp_path):
    """Beispielreise mit Attrappen der Grundkarten: eine für die Etappenkarten, eine Region für die Karten des Wissens."""
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    karte = quelle / "medien" / "karte"
    karte.mkdir(parents=True, exist_ok=True)
    for name in ("attrappe.pmtiles", "region.pmtiles"):
        (karte / name).write_bytes(b"PMTiles")
    k = yaml.safe_load((quelle / "plan/karte.yaml").read_text(encoding="utf-8"))
    k["grundkarte"] = {"datei": "medien/karte/attrappe.pmtiles", "namensnennung": "erfunden (Attrappe)"}
    (quelle / "plan/karte.yaml").write_text(yaml.safe_dump(k, allow_unicode=True, sort_keys=False), encoding="utf-8")
    w = yaml.safe_load((quelle / "inhalt/wissen-punkte.yaml").read_text(encoding="utf-8")) or {}
    w["grundkarten"] = {"region": {"titel": "Elbsandstein", "rahmen": {"nord": 51.3, "sued": 50.7, "west": 13.4, "ost": 14.6}}}
    kopf = "".join(z for z in (quelle / "inhalt/wissen-punkte.yaml").read_text(encoding="utf-8").splitlines(keepends=True) if z.startswith("#"))
    (quelle / "inhalt/wissen-punkte.yaml").write_text(kopf + yaml.safe_dump(w, allow_unicode=True, sort_keys=False), encoding="utf-8")
    daten = bauen.bauen(quelle, tmp_path / "web" / "beispiel")
    return daten


def messen(tmp_path, browser, breite):
    daten = gebaut(tmp_path)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_karte_legende.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", str(breite)],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == [], e["fehler"]
    return daten, e["aus"]


@ohne_browser
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
@pytest.mark.parametrize("breite", [390, 1300])
def test_legende_nach_arten(tmp_path, browser, breite):
    daten, a = messen(tmp_path, browser, breite)
    arten = daten["route"]["arten"]
    # Etappenkarte: eine Ebene je Art mit Punkten an der Strecke, Name der Art mit Zähler, im Fenster, Schalter blendet Punkte aus und ein
    e = a["etappe"]
    assert e["schalter"] and all(x["innen"] for x in e["schalter"]), e["schalter"]
    namen = {arten[k]["name"] for k, d in arten.items() if d.get("gruppe") == "punkt"}
    ebenen = [x["text"].rsplit(" (", 1)[0] for x in e["ebenen"]]
    assert ebenen and set(ebenen) <= namen and len(ebenen) == len(set(ebenen)), (ebenen, namen)
    assert all(x["innen"] for x in e["ebenen"]), e["ebenen"]
    if breite < 600:   # am Telefon Tippflächen von mindestens 44 px (docs/design.md)
        assert all(x["breit"] >= 44 and x["hoch"] >= 44 for x in e["schalter"]) and all(x["hoch"] >= 44 for x in e["ebenen"]), (e["schalter"], e["ebenen"])
    assert e["markenAus"] < e["markenVorher"] and e["markenWieder"] == e["markenVorher"], e
    assert not e["waagerecht"]
    # Karte des Wissensabschnitts: je Art mit Punkten ein Eintrag mit dem Einzahl-Namen oder Namen der Art
    assert a["bloecke"], "die Beispielreise hat Punkte an Wissensabschnitten"
    w = a["wissen"]
    erlaubt = {arten[k].get("einzahl") or arten[k]["name"] for k, d in arten.items() if d.get("gruppe") == "wissen"}
    assert w["legende"] and {x["text"] for x in w["legende"]} <= erlaubt, (w["legende"], erlaubt)
    assert all(x["innen"] for x in w["legende"]) and not w["waagerecht"], w
