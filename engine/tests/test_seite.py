"""Browser-Rundgang durch die Beispielreise (Designsystem, frieda-reist#18): jede Ansicht ohne Skriptfehler und nicht leer."""
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
    # Wahl-Modul: öffnet an der Stelle, zeigt mindestens 2 Möglichkeiten (Handy höchstens 2, Rechner höchstens 4)
    for breite, v in e["vergleich"].items():
        assert v["sichtbar"] and v["offen"] == "true", (breite, v)
        assert 2 <= v["spalten"] <= (2 if int(breite) < 700 else 4), (breite, v)
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
    for teil in ("Atom · Zustand", "Atom · Wert", "Molekül · Listenzeile", "Molekül · Fragenkarte", "Molekül · Rückmeldung", "Molekül · Aufgabe", "Molekül · Kennzahlenleiste", "Organismus · Wahl-Modul", "Vorlage · Tag"):
        assert teil in b, teil
    assert ' id="' not in b.split(">", 1)[1]
    assert "null" not in re.sub(r"<[^>]+>", " ", b)


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
