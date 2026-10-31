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


def rundgang(tmp_path, browser, aendern=None):
    """Beispielreise mit Plan A bauen (aendern: Text von routen.yaml anpassen) und Tag 2 bei 390 und 1300 px prüfen."""
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    plan_fest(quelle)
    if aendern:
        r = quelle / "plan" / "routen.yaml"
        r.write_text(aendern(r.read_text(encoding="utf-8")), encoding="utf-8")
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
    return json.loads(aus.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_tagesseite_in_ebenen(tmp_path, browser):
    e = rundgang(tmp_path, browser)
    assert e["fehler"] == []
    for breite, a in e["aus"].items():
        # Die Nacht kommt zuletzt: nach dem Hintergrund, vor den Quellen (Product Owner 31.10.2026), auf beiden Geräten
        n = a["nacht"]
        assert not n["voll"] and n["hintergrund"] < n["oben"] < n["quellen"], n
        # Stand-Leiter: nicht gebucht (Pension Burgblick) sind die Einzelheiten offen
        assert n["einzelheiten"] == [True], n
        # gebucht (Hotel am Elbufer, B-01): Einzelheiten von Unterkunft und Buchung zu; oben Nummer, Preis, Zahlung (#166) und die
        # laufende Stornofrist; der Stand steht einmal (die Buchung trägt ihn, kein Chip an der Karte); im Tageskasten „gebucht“
        g = a["gebucht"]
        assert g["karte"] == [False] and g["buchung"] == [False], g
        assert g["oben"] == ["Nummer", "Preis", "Zahlung", "Storno"] and g["storno"] == "Storno: bis 11.5.", g
        assert g["chipsKarte"] == 0 and g["tageskasten"] == ["gebucht"], g
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


# Erfunden: Gasthof Polenztal (V-03.b) ist nicht verworfen, sondern nur vorgeschlagen; so hat die Nacht von Tag 2 zwei gültige
# Möglichkeiten. Mit der gewählten Pension Burgblick ist sie entschieden, ohne die Wahl offen; damit Plan A trotzdem fest
# ist (sonst keine Tagesseiten), hängt er dann nur an V-01.a.
VERWORFEN = '          - {datum: 2026-10-20, status: verworfen, wer: Ida, grund: "Anstieg am Morgen"}\n'
GEWAEHLT = '          - {datum: 2026-10-20, status: gewaehlt, wer: Ida, grund: "liegt am Weg, kein Anstieg am Morgen"}\n'


def zwei_moeglichkeiten(text, offen=False):
    assert VERWORFEN in text and GEWAEHLT in text
    text = text.replace(VERWORFEN, "")
    if offen:
        text = text.replace(GEWAEHLT, "").replace("auswahl: [V-01.a, V-03.a]", "auswahl: [V-01.a]")
    return text


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("offen", [False, True])
def test_nacht_volle_breite_nur_bei_offener_wahl(tmp_path, offen):
    """Am Rechner steht die Nacht nur bei offener Wahl über die volle Breite unter dem Tageskasten (Product Owner 29.10.2026).
    Eine entschiedene Nacht mit weiteren Möglichkeiten (zugeklappt, mit Vergleich) bleibt in der Lesespalte (31.10.2026)."""
    e = rundgang(tmp_path, "chromium", lambda t: zwei_moeglichkeiten(t, offen))
    assert e["fehler"] == []
    n = e["aus"]["1300"]["nacht"]
    assert (n["voll"], n["inLesen"]) == (offen, not offen), n
