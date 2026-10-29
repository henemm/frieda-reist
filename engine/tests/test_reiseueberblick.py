"""Reiseüberblick im ersten Reiter, sobald ein Plan gewählt ist (28.10.2026, docs/design.md): kein Planname, Kopf mit
Zähler, An- und Abreise, Kennzahlen mit Kosten, Mitreisende, Stand der Vorbereitung, feste Termine und die Tage als Zeilen
mit dem Stand der Nacht."""
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


def ueberblick(tmp_path, browser, datum, status=None):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    plan_fest(quelle)
    if status:
        y = yaml.safe_load((quelle / "reise.yaml").read_text(encoding="utf-8"))
        y["status"]["verlauf"].append({"datum": y["status"]["verlauf"][-1]["datum"], "wert": status, "wer": "Ida", "grund": "Test"})
        y["status"]["wert"] = status
        (quelle / "reise.yaml").write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
    bauen.bauen(quelle, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_reise.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", datum],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    return e["aus"]


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_reiseueberblick(tmp_path, browser):
    for breite, a in ueberblick(tmp_path, browser, "2026-10-28").items():
        # Seitenordnung (28.10.2026): Reise · Zu tun · Wissen · Wünsche, kein Reiter „Plan“
        assert a["reiter"] == ["Reise", "Zu tun", "Wissen", "Wünsche"] and a["aktiv"] == "Reise", a["reiter"]
        assert not a["planname"] and a["steckbriefe"] == 0                      # kein Planname, keine anderen Pläne
        assert a["kopf"] == ["Reise", "noch 197 Tage"], a["kopf"]
        assert a["kennzahlen"] == ["Tage", "Gehzeit", "Strecke", "Höhenmeter", "Übernachtungen"], a["kennzahlen"]
        # 120 € (U-01) + 85 € (U-02), Beispielwerte; „35 € pro Person“ (U-04) zählt nicht, der Preis gilt für die Nacht
        assert a["kosten"] == "205 €" and a["kostenHinweis"].startswith("Übernachtungen: Preis bekannt für 2 von 3 Nächten"), a
        # Anreise oben, Abreise unten; Abreise nennt nur die Fahrt, nicht die Wanderetappe des Tages
        assert a["reihenfolge"] == ["Anreise", "Karte", "Tage", "Abreise"], a["reihenfolge"]
        assert a["anab"] == [["Anreise · Do 13.5.", "#T-01", ["Ankunft mit dem Zug in Dresden (Beispiel)"]],
                             ["Abreise · So 16.5.", "#T-04", ["S-Bahn Bad Schandau → Dresden"]]], a["anab"]
        assert a["mitreisende"] == "Mitreisende Ida, Karl ab 14.5.", a["mitreisende"]
        assert a["termine"] == ["Abendessen in Altendorf, Tisch um 19 Uhr reserviert (Beispiel)"], a["termine"]
        # gebucht ist nur U-01 (Beispielwert); dazu zählen die Bahnfahrten (Art bahn buchbar) und die Burg (Aufenthalt ohne Nacht),
        # Paket O-5; der Stand führt nach „Zu tun · Zu buchen“
        assert a["stand"] == [["Gebucht", "1 von 6", "#zu-buchen"], ["Offene Fragen", "2", "#fragen"]], a["stand"]
        assert a["inZeile"] == 0, a["inZeile"]
        assert a["karte"] and a["karte"]["breite"] == a["karte"]["kasten"] and a["karte"]["wege"] > 100, a["karte"]
        assert a["zurueck"]["tag"] == "T-03" and a["zurueck"]["sichtbar"], a["zurueck"]
        karte = a["unterkunft"].pop("karte")
        assert a["unterkunft"] == {"inNacht": True, "reiter": "Reise", "web": "https://example.org/pension-burgblick", "selbst": 0}, a["unterkunft"]
        # Google Maps immer, Apple Karten nur auf Apple-Geräten (WebKit meldet sich als Macintosh)
        assert karte[0] == "https://www.google.com/maps/search/?api=1&query=50.9792%2C14.1128", karte
        assert karte[1:] in ([], ["https://maps.apple.com/?q=Pension%20Burgblick&ll=50.9792,14.1128"]), karte
        # je Tag: Nacht, dann Bewegungen und Aufenthalte mit Buchungsstand; Bewegung und Aufenthalt führen zum Tag
        assert [x[1] for x in a["buchen"]] == ["gebucht"] + ["nicht gebucht"] * 5, a["buchen"]
        assert [x[0] for x in a["buchen"]][1:4] == ["#U-02", "#T-02", "#T-02"], a["buchen"]
        assert a["ueberPlan"] > 0
        assert [x[0] for x in a["tage"]] == ["#T-01", "#T-02", "#T-03", "#T-04"]
        assert [x[2] for x in a["tage"]] == ["gebucht", "nicht gebucht", "nicht gebucht", None], a["tage"]
        assert not a["breit"], breite
        assert a["planZiel"] and a["nachKlick"] == "#T-01", a
        # Lesetext: „(F-03)“ wird zum Link mit den ersten Worten der Frage, „R-…“ entfällt
        assert "F-03" not in a["lesetext"]["text"] and "R-2026" not in a["lesetext"]["text"], a["lesetext"]
        assert a["lesetext"]["link"] and a["lesetext"]["link"][0].startswith("„Fahrplan"), a["lesetext"]
        assert "(Herkunft: Rückmeldung von Karl" in a["lesetext"]["text"], a["lesetext"]
        # Offene Fragen sprechen ohne Kennungen: „(V-01.a)“ wird zur Pille mit dem Namen der Möglichkeit
        assert a["fragen"]["kennungen"] == [] and a["fragen"]["gruppen"] == ["Zu klären", "Geklärt"], a["fragen"]
        assert len(a["fragen"]["pillen"]) == 2 and all(a["fragen"]["pillen"]), a["fragen"]


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_reiseueberblick_unterwegs(tmp_path):
    """Unterwegs zählt der Tag, nicht die Vorbereitung: Zähler „Tag x von n“, kein Stand der Vorbereitung."""
    for a in ueberblick(tmp_path, "chromium", "2027-05-14", status="unterwegs").values():
        assert a["kopf"] == ["Reise", "Tag 2 von 4"] and a["stand"] == [], a
