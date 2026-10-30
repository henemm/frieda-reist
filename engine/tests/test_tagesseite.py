"""Tagesseite in Ebenen (B2 „Freundlich“, frieda-reist#52/#53) und Kennung als Sprechblase (#56) im Browser."""
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


def plan_fest(quelle):
    """Plan A fest wählen (V-01.a gewählt, erfunden): dann hat jeder Tag seine Tagesseite mit der ganzen Etappe."""
    r = quelle / "plan" / "routen.yaml"
    alt = '          - {datum: 2026-10-20, status: vorgeschlagen, wer: Claude, grund: "kürzeste Verbindung zum Bahnhof"}\n'
    text = r.read_text(encoding="utf-8")
    assert alt in text
    r.write_text(text.replace(alt, alt + '          - {datum: 2026-10-24, status: gewaehlt, wer: Ida, grund: "Test"}\n'), encoding="utf-8")


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_tagesseite_in_ebenen(tmp_path, browser):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    plan_fest(quelle)
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
    for breite, a in e["aus"].items():
        assert a["breit"] == [] and not a["breitNachTabelle"], (breite, a["breit"])
        assert a["kaesten"] == 1 and a["flaeche"], breite                       # ein Kasten: der Tageskasten
        assert a["planChips"] == [], a["planChips"]                             # Plan gewählt: der Tag nennt keine Pläne
        assert a["aufenthalte"] == [["Burg Hohnstein", "nicht gebucht"]], a["aufenthalte"]   # Aufenthalt ohne Nacht am Ziel (O-5)
        assert a["reiter"] == ["Eckdaten", "Wegpunkte", "Unterkünfte"], a["reiter"]
        assert a["offen"] == ["E-01.eckdaten"] and a["kennungImKopf"] == ["E-01.eckdaten"]
        assert a["nachKlick"] == ["E-01.unterkuenfte-liste"] and a["kennungNachKlick"] == ["E-01.unterkuenfte-liste"]
        assert a["nachPfeil"] == ["E-01.eckdaten"] and a["gemerkt"] == ["E-01.unterkuenfte-liste"]
        # Ein Wert steht einmal: Gehzeit, Auf-, Abstieg und Länge zeigt die Kennzahlenleiste, nicht die Merkmalliste
        assert a["merkmale"] == ["Höchster Punkt", "Markierung", "Herkunft"], a["merkmale"]
        assert a["textInEtappe"] == 0                                           # Kennung der Etappe steht bei „Der Weg“
        # Kennung: nur Sprechblase mit Tooltip, kein „i“; das Fenster nennt die Kennung und kann sie kopieren
        assert a["info"] == 0 and a["knoepfe"] and all(t in ("Anmerken",) and l.startswith("Anmerken zu ") for t, l in a["knoepfe"])
        assert a["fenster"] == {"offen": True, "kennung": "E-01", "kopieren": True}
        assert all(a["tiefe"].values()) and len(a["tiefe"]) == 3, a["tiefe"]
        # Hintergrund als Kapitel: zu, immer nur eines offen; der umschaltende Bereich ist getönt; Der Weg mit „Weiterlesen“
        assert a["kapitel"][0] >= 2 and a["kapitel"][1] == 0 and len(a["kapitelOffen"]) == 1, (a["kapitel"], a["kapitelOffen"])
        assert a["getoent"] and a["weiterlesen"] == 1 and a["nachWeiterlesen"] == 0, a
        # Anmerken erst nach dem Lesen: unterwegs ohne Sprechblase in Vorschauen, am Rechner mit
        assert a["vorschauen"] > 0 and a["sichtbarVorschau"] == (0 if breite == "390" else a["vorschauen"] + a["zugeklappt"]), a
        lage = {n: (o, l) for n, o, l in a["ebenen"]}
        if breite == "390":   # unterwegs: Weg, Nachschlagen, Orte, Hintergrund, Quellen untereinander
            assert [n for n, o, _ in sorted(a["ebenen"], key=lambda x: x[1])] == ["weg", "unterwegs", "orte", "hintergrund", "quellen"]
            # WebKit gibt content: attr() ": " als '"Typ" ": "' aus, Chromium als '"Typ: "'
            assert a["tabelle"]["display"] == "block" and a["tabelle"]["vor"].replace('" "', "") == '"Typ: "'
        else:                 # Rechner: links lesen, rechts nachschlagen
            assert lage["unterwegs"][1] > lage["weg"][1] and lage["orte"][1] == lage["unterwegs"][1]
            assert lage["hintergrund"][1] == lage["weg"][1] and lage["unterwegs"][0] == lage["weg"][0]
            assert a["tabelle"]["display"] == "block"   # rechte Spalte ist schmal: auch am Rechner gestapelt
