"""Tagesseite und Ortsseite bei gewähltem Plan (frieda-reist#144): Nummer und Datum kommen aus dem gewählten Plan."""
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

# Erfundene Zusatzpläne (Beispielwert): V-04 fügt in Hohnstein eine Nacht ein, V-05 lässt den Tag nach Altendorf weg.
# Der gewählte Plan A nimmt weder die Nacht noch lässt er den Tag aus.
NACHT = """  - id: P-X
    kurz: Plan X
    titel: "Eine Nacht mehr in Hohnstein (erfunden, Beispiel)"
    farbe: a
    auswahl: [V-04.a, V-05.a, V-01.a, V-03.a]
"""
OHNE_TAG = """  - id: P-Y
    kurz: Plan Y
    titel: "Ohne den Tag nach Altendorf (erfunden, Beispiel)"
    farbe: b
    auswahl: [V-04.b, V-05.b, V-01.a, V-03.a]
"""
WAHLSTELLEN = """  V-04:
    titel: "Hohnstein: eine Nacht mehr (erfunden, Beispiel)"
    art: planung
    optionen:
      - {id: V-04.a, titel: "Eine Nacht mehr", folge: [T-07]}
      - id: V-04.b
        titel: "Weiter wie geplant"
        verlauf:
          - {datum: 2026-10-24, status: gewaehlt, wer: Ida, grund: "Test"}
  V-05:
    titel: "Altendorf: Tag auslassen (erfunden, Beispiel)"
    art: planung
    optionen:
      - id: V-05.a
        titel: "Über Brand nach Altendorf"
        folge: [T-03]
        verlauf:
          - {datum: 2026-10-24, status: gewaehlt, wer: Ida, grund: "Test"}
      - {id: V-05.b, titel: "Ohne diesen Tag"}

"""


def fest_mit_abweichenden_plaenen(quelle, zuerst):
    """Plan A fest (V-01.a, V-03.a, V-04.b, V-05.a gewählt); davor steht ein verworfener Plan mit anderer Zählung."""
    r = quelle / "plan" / "routen.yaml"
    t = r.read_text(encoding="utf-8")
    alt = '          - {datum: 2026-10-20, status: vorgeschlagen, wer: Claude, grund: "kürzeste Verbindung zum Bahnhof"}\n'
    assert alt in t
    t = t.replace(alt, alt + '          - {datum: 2026-10-24, status: gewaehlt, wer: Ida, grund: "Test"}\n')
    t = t.replace("  T-06: {", '  T-07: {titel: "Ruhetag in Hohnstein (erfunden, Beispiel)"}\n  T-06: {', 1)
    t = t.replace("route: [T-01, T-02, T-03, V-01]", "route: [T-01, T-02, V-04, V-05, V-01]")
    t = t.replace("wahlstellen:\n", "wahlstellen:\n" + WAHLSTELLEN, 1)
    t = t.replace("    auswahl: [V-01.a, V-03.a]", "    auswahl: [V-04.b, V-05.a, V-01.a, V-03.a]")
    t = t.replace("    auswahl: [V-01.b, V-03.a]", "    auswahl: [V-04.b, V-05.a, V-01.b, V-03.a]")
    vor = {"nacht": NACHT, "tag": OHNE_TAG}[zuerst]
    nach = {"nacht": OHNE_TAG, "tag": NACHT}[zuerst]
    t = t.replace("  - id: P-A\n", vor + "  - id: P-A\n", 1)
    t = t.replace("  - id: P-B\n", nach + "  - id: P-B\n", 1)
    r.write_text(t, encoding="utf-8")


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("tiefe", [False, True])
@pytest.mark.parametrize("zuerst", ["nacht", "tag"])
def test_tagesseite_zaehlt_im_gewaehlten_plan(tmp_path, zuerst, tiefe):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    fest_mit_abweichenden_plaenen(quelle, zuerst)
    if tiefe:  # Ortsseiten mit „Kommt vor in“ (ansichtOrt) gibt es nur im Tiefe-Modus
        eck = quelle / "reise.yaml"
        eck.write_text(eck.read_text(encoding="utf-8").replace("darstellung:\n", "darstellung:\n  tiefe: true\n", 1), encoding="utf-8")
    bauen.bauen(quelle, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_tagesplan.mjs"), str(PLAYWRIGHT), f"http://127.0.0.1:{s.server_address[1]}/beispiel/"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    assert len(e["tage"]) >= 4, e["tage"]
    # 1./2./3.: jede Tagesseite zeigt Nummer und Datum der Übersicht, keine zwei Seiten mit gleichem Kopf
    for t in e["tage"]:
        assert t["kopf"] == t["erwartet"], t
    assert len({t["kopf"] for t in e["tage"]}) == len(e["tage"]), [t["kopf"] for t in e["tage"]]
    # 4.: Blättern bleibt im gewählten Plan (Nummer des Nachbarn = Nummer in der Übersicht)
    nr = {t["id"]: t["erwartet"].split(" · ")[0] for t in e["tage"]}
    for t in e["tage"]:
        for href, text in t["blaettern"]:
            assert nr[href.lstrip("#")] in text, (t["id"], t["blaettern"])
    # 7.: Ortsseite: „Kommt vor in“ nennt nur den gewählten Plan
    if tiefe:
        assert e["ort"]["chips"] and all(c.startswith("Plan A:") for c in e["ort"]["chips"]), e["ort"]
        assert e["ort"]["zurueck"] == "#P-A", e["ort"]


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("tiefe", [False, True])
def test_tagesseite_zaehlt_wie_die_zeitachse_bei_offenen_plaenen(tmp_path, tiefe):
    """#214, Entscheidung 3: tiefe steuert die Tagesseiten nicht mehr. Bei offenen Plänen zeigt jede Tagesseite Nummer und
    Datum ihrer Zeile auf der Zeitachse, auch nachdem ein anderer Plan (Plan X, eine Nacht mehr, zählt anders) offen war."""
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    fest_mit_abweichenden_plaenen(quelle, "nacht")
    r = quelle / "plan" / "routen.yaml"
    t = r.read_text(encoding="utf-8")
    gewaehlt = '          - {datum: 2026-10-24, status: gewaehlt, wer: Ida, grund: "Test"}\n'
    i = t.index(gewaehlt, t.index("kürzeste Verbindung zum Bahnhof"))
    r.write_text(t[:i] + t[i + len(gewaehlt):], encoding="utf-8")   # V-01 wieder offen: kein Plan ist vollständig gewählt
    if tiefe:
        eck = quelle / "reise.yaml"
        eck.write_text(eck.read_text(encoding="utf-8").replace("darstellung:\n", "darstellung:\n  tiefe: true\n", 1), encoding="utf-8")
    bauen.bauen(quelle, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_tagesplan.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", "P-X"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    auf_achse = [t for t in e["tage"] if t["achse"]]
    assert len(auf_achse) >= 4, e["tage"]
    for t in auf_achse:
        assert t["kopf"] == t["achse"], (tiefe, t)


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_tiefe_nur_noch_plan_baum(tmp_path):
    """#214, Entscheidung 3 (K11): darstellung.tiefe steuert nur noch den Plan-Baum im Reiter „Pläne“. Die Startseite ist die
    Zeitachse, die Tage haben Tagesseiten, der Plan P-A öffnet weiter seinen Baum unter „Pläne“."""
    from test_eine_seitenordnung import rundgang
    e, d = rundgang(tmp_path, "tiefe", extra=["P-A"])
    assert e["start"]["achse"] and e["start"]["tageskaesten"] == 0, e["start"]
    assert "plan" not in e["reiter"], e["reiter"]
    seiten = {t: v["tagseite"] for t, v in e["tagesseiten"].items()}
    assert all(seiten.values()), seiten
    p = e["sprung"]["P-A"]
    assert p["ziel"] and p["reiter"] == "varianten" and not p["tagseite"], p
