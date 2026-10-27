"""Browser-Rundgang durch die Beispielreise (Designsystem, frieda-reist#18): jede Ansicht ohne Skriptfehler und nicht leer."""
import datetime
import functools
import http.server
import json
import re
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
PLAYWRIGHT = Path(os.environ.get("PLAYWRIGHT_MODUL") or Path.home() / "playwright-tool/node_modules/playwright/index.mjs")


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])   # webkit = Safari auf iPhone und iPad
def test_alle_ansichten_der_beispielreise(tmp_path, browser):
    ziel = tmp_path / "web" / "beispiel"
    if os.environ.get("RH_BILDER"):   # Bilder der Bausteinseite zur Durchsicht (in GitHub Actions als Artefakt)
        Path(os.environ["RH_BILDER"]).mkdir(parents=True, exist_ok=True)
    bauen.bauen(WURZEL / "beispiel/reisen/beispielreise", ziel)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_browser.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", str(tmp_path / "dom.json")],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["routen"] > 100
    assert e["fehler"] == []
    assert e["leer"] == []
    assert e["breit"] == []          # keine Ansicht steht auf dem Handy seitlich über
    # Wahl-Modul: öffnet an der Stelle, zeigt mindestens 2 Möglichkeiten (Handy höchstens 2, Rechner höchstens 4, ab 1100 px höchstens 5)
    for breite, v in e["vergleich"].items():
        assert v["sichtbar"] and v["offen"] == "true", (breite, v)
        assert 2 <= v["spalten"] <= (2 if int(breite) < 700 else 4 if int(breite) < 1100 else 5), (breite, v)
    assert set(e["vergleich"]) == {"390", "1200"}
    # Leiste als App: bleibt unten, wenn iOS die Höhe nach der Tastatur vergisst (800 statt 500 px), mit Tastatur über
    # ihr; im Browser ändert sich nichts (Abstand unten 12 px)
    a, w = e["leiste"]["app"], e["leiste"]["browser"]
    assert a["start"] == a["klein"] == a["zu"] == a["voll"] == 788, a
    assert a["tippt"] == 488, a
    assert w == {"start": 788, "klein": 488, "tippt": 488, "zu": 488, "voll": 788}, w
    dom = json.loads((tmp_path / "dom.json").read_text(encoding="utf-8"))
    # Wert je Datum: die Unterkunft zeigt beide Einträge; Herkunft steht hinter dem i, nicht im Text
    u01 = dom["1200#U-01"]
    assert "15.5.: " in u01 and "sonst: " in u01 and "140 €" in u01
    assert 'class="mk-i"' in u01 and '<span class="mk-q" hidden="">Beispielwert, erfunden' in u01
    # Regeln und Anschluss (Paket 4): an der Wahlstelle stehen „Setzt voraus“ und die berechnete Lücke der erfundenen V-01.c
    v01 = dom["1200#V-01"]
    assert "Setzt voraus: " in v01 and "Schließt aus: " in v01 and "(im Plan)" in v01
    assert '<span class="mk-luecke">Lücke am Anfang: Altendorf → Bad Schandau</span>' in v01
    # Bausteinseite: alle Ebenen, keine Sprungziele (die echten Stellen bleiben eindeutig), kein „null“
    b = dom["1200#bausteine"]
    for teil in ("Atom · Zustand", "Atom · Wert", "Molekül · Listenzeile", "Molekül · Fragenkarte", "Molekül · Rückmeldung", "Molekül · Aufgabe", "Molekül · Wunschkarte", "Molekül · Kennzahlenleiste", "Organismus · Wahl-Modul", "Vorlage · Tag"):
        assert teil in b, teil
    assert ' id="' not in b.split(">", 1)[1]
    assert "null" not in re.sub(r"<[^>]+>", " ", b)


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_neue_reise_aus_der_vorlage(tmp_path, browser):
    """Paket H: Eine frisch angelegte Reise (Status idee, ohne Plan) zeigt jede Ansicht ohne Fehler und ohne Leere."""
    import neu
    r = neu.anlegen(tmp_path / "reisen", "Skiurlaub im Tal", datetime.date(2027, 2, 6), datetime.date(2027, 2, 13),
                    {"ida": {"name": "Ida", "rolle": "bestimmer"}, "karl": {"name": "Karl", "rolle": "einbringer"}},
                    "Ida", ziel="Oberstdorf")
    bauen.bauen(r, tmp_path / "web" / r.name)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_browser.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/{r.name}/", str(tmp_path / "dom.json")],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["routen"] > 20 and e["fehler"] == [] and e["leer"] == [] and e["breit"] == []
    dom = json.loads((tmp_path / "dom.json").read_text(encoding="utf-8"))
    assert "6.–13. Februar 2027" in dom["390#"] and "Offene Fragen: 1" in dom["390#"]


def seite_der_variante(tmp_path, browser, datum="2027-05-13", **variante):
    """Beispielreise mit anderem Status oder anderen Bausteinen bauen (wie test_regeln) und im Browser ansehen."""
    from test_regeln import reise_bauen
    seiten = reise_bauen(tmp_path, **variante)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(seiten)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_variante.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispielreise/", datum],
                             capture_output=True, text=True, timeout=120, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    return e


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_seite_je_status_und_baustein(tmp_path, browser):
    """Paket B auf der Seite: unterwegs beginnt mit Heute und der Karte; ausgeschaltete Bausteine verschwinden."""
    planung = seite_der_variante(tmp_path / "planung", browser)
    assert planung["heute"] is None
    assert {"wuensche", "offen"} <= set(planung["reiter"]) and planung["knoepfe"] > 0
    unterwegs = seite_der_variante(tmp_path / "unterwegs", browser, status="unterwegs")
    assert unterwegs["aktiv"] == "varianten" and unterwegs["heute"].startswith("Heute · Tag 1: "), unterwegs
    kein_tag = seite_der_variante(tmp_path / "kein_tag", browser, datum="2027-06-30", status="unterwegs")
    assert kein_tag["heute"] == "Heute"
    wenig = seite_der_variante(tmp_path / "wenig", browser, bausteine=["varianten"])
    assert "wuensche" not in wenig["reiter"] and "offen" not in wenig["reiter"], wenig
    assert wenig["knoepfe"] == 0 and wenig["kennungen"] > 0   # IDs stehen da, aber ohne Rückmeldeknopf


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_wunsch_brett(tmp_path, monkeypatch, browser):
    """Paket G auf der Seite, unterwegs, mit dem echten Rückmeldedienst: Spalten, Punkte nur auf eigene Wünsche, abhaken
    (auch fremde), ohne Netz abhaken und nachreichen, Bilanz; nichts steht am Handy über, am Rechner Spalten nebeneinander."""
    from test_regeln import reise_bauen, starten
    import rueckmeldungen as rm
    seiten = reise_bauen(tmp_path, status="unterwegs")
    o = tmp_path / "ablage" / "beispielreise"
    o.mkdir(parents=True)
    wuensche = [("R-20261021-091500-a1b2", "Karl", "Einmal mit der Kirnitzschtalbahn fahren", "uebernommen"),
                ("R-20261022-100000-0001", "Ida", "Abends in Hohnstein essen", "neu"),
                ("R-20261023-100000-0002", "Karl", "Baden in der Elbe", "verworfen")]
    (o / "eingang.jsonl").write_text("".join(json.dumps({"id": i, "name": n, "art": "Wunsch", "ziel": "wuensche", "text": t,
                                                         "quelle": "", "erstellt": f"2026-10-2{k}T10:00:00+00:00"}) + "\n"
                                             for k, (i, n, t, _) in enumerate(wuensche)), encoding="utf-8")
    (o / "status.json").write_text(json.dumps({i: {"status": s, "kommentar": "Test"} for i, _, _, s in wuensche if s != "neu"}),
                                   encoding="utf-8")
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    rm._zeiten.clear()
    dienst, durl = starten(rm.Dienst)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(seiten)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_brett.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispielreise/", durl, "Karl"],
                             capture_output=True, text=True, timeout=180, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
        dienst.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    bahn, essen, baden = (t for _, _, t, _ in wuensche)
    assert e["start"]["spalten"] == {bahn: "geprueft", essen: "eingebracht", baden: "passt_nicht"}
    assert any(z.startswith("Karl") and "1 Wunsch" not in z for z in e["start"]["bilanz"])
    assert e["punkte"] == "1" and e["fremdePunkte"] == 0               # Punkte nur auf eigene Wünsche
    assert e["erlebt"]["spalten"][essen] == "erlebt"                   # fremden Wunsch abgehakt
    assert e["offline"]["spalten"][bahn] == "erlebt" and e["offline"]["ausgang"] == 1 and e["offline"]["nachreichen"] >= 1
    assert e["offline"]["zuruecknehmen"][essen] == "erlebt"            # ohne Netz kein Zurücknehmen fremder Haken
    assert e["nach429"] == 1                                           # „zu viele“: Haken bleibt im Ausgang
    assert e["nachgereicht"]["spalten"][bahn] == "erlebt" and e["nachgereicht"]["nachreichen"] == 0
    assert any(z.startswith("Karl") and "9 von 10 Punkten frei" in z for z in e["nachgereicht"]["bilanz"]), e["nachgereicht"]
    assert not any(x["breit"] for x in (e["start"], e["erlebt"], e["offline"], e["nachgereicht"]))
    assert e["breit"] >= 2                                             # am Rechner Spalten nebeneinander
    b = json.loads((o / "brett.json").read_text(encoding="utf-8"))
    assert b[bahn_id := wuensche[0][0]]["erlebt"]["wer"] == "Karl" and b[bahn_id]["punkte"] == 1
    assert b[wuensche[1][0]]["erlebt"]["wer"] == "Karl"
