"""Buchungen mit Zeitraum und Check-in-Ansicht (#463, Product Owner 9.11.2026): Eine Buchung gilt mit anreise/abreise nur für
ihre Nächte; die Seite zeigt an jeder Nacht nur die Buchung, die sie enthält, und an der Anreise einer weiteren Buchung derselben
Unterkunft die Karte noch einmal (neuer Check-in). Gebucht stehen oben Nummer, Check-in, Check-out, vor Ort zu zahlen;
Preis, Zahlungsweg und Stornoregel in den Einzelheiten; die Herkunft der Adresse (ⓘ) entfällt."""
import datetime
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
import routen  # noqa: E402
import schnittstelle  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_heimat_unterkunft import zwei_naechte_im_gewaehlten_plan  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
D = datetime.date


def test_buchung_gilt_am():
    b = {"anreise": D(2027, 3, 5), "abreise": D(2027, 3, 7)}
    assert [routen.buchung_gilt_am(b, D(2027, 3, x), True) for x in (4, 5, 6, 7)] == [False, True, True, False]
    assert [routen.buchung_gilt_am(b, D(2027, 3, x), False) for x in (4, 5, 6, 7)] == [False, True, True, True]
    assert routen.buchung_gilt_am({}, D(2027, 3, 1), True)                       # ohne Zeitraum: immer
    nur_an = {"anreise": "2027-02-25"}
    assert routen.buchung_gilt_am(nur_an, "2027-02-25", True) and not routen.buchung_gilt_am(nur_an, "2027-02-26", True)
    eins = {"anreise": D(2027, 2, 25), "abreise": D(2027, 2, 26)}
    assert not routen.zeitraeume_ueberschneiden(eins, b) and routen.zeitraeume_ueberschneiden(eins, {})
    assert routen.zeitraeume_ueberschneiden(b, {"anreise": D(2027, 3, 6)})


def test_zeitpunkt_mit_uhrzeit():
    """frist und ab einer Buchung mit Uhrzeit (#472): Prüfung, Textform und Wächter-Tag."""
    import texte
    assert routen.DATUM_UHR.match("2027-02-22T17:55") and routen.tag_von("2027-02-22T17:55") == D(2027, 2, 22)
    assert texte.datum_uhr("2027-02-22T17:55", "de") == "22.2.2027, 17:55" and texte.datum_uhr(D(2027, 2, 22), "de") == "22.2.2027"


def test_parameter_englisch():
    """arrival/departure heißen nur bei Buchungen Anreise/Abreise; bei Strecken bleiben sie Abfahrt und Ankunft."""
    assert schnittstelle.parameter_zu_intern("buchung_anlegen")["arrival"] == "anreise"
    assert schnittstelle.parameter_zu_intern("buchung_aendern")["departure"] == "abreise"
    assert schnittstelle.parameter_zu_intern("buchung_anlegen")["checkin_from"] == "anreise_ab"
    assert schnittstelle.parameter_zu_intern("ding_anlegen")["arrival"] == "an"


def zwei_buchungen(quelle):
    """U-01 an T-01 (13.5.) und T-07 (14.5.), je Nacht eine eigene Buchung: B-01 (13.–14.5.) und neu B-04 (ab 14.5.)."""
    zwei_naechte_im_gewaehlten_plan(quelle)
    r = quelle / "plan" / "routen.yaml"
    t = r.read_text(encoding="utf-8")
    t = t.replace("\ntage:\n", '''  B-04:
    fuer: [U-01]
    status: gebucht
    nummer: "HE-2027-0999"
    preis: "130 € für eine Nacht (Beispielwert)"
    zahlung: bezahlt
    anreise: 2027-05-14
    abreise: 2027-05-15
    anreise_ab: "14:00"
    ab: "2027-05-13T08:00"   # Zeitpunkt mit Uhrzeit (#472)
    ab_was: "Online-Check-in"
    gebucht_am: 2026-11-09
    wer: Ida
    quelle: "erfunden (Beispiel)"

tage:
''', 1)
    r.write_text(t, encoding="utf-8")


def test_bau_ohne_warnung_bei_getrennten_zeitraeumen(tmp_path):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    zwei_buchungen(quelle)
    d = bauen.bauen(quelle, tmp_path / "web" / "beispiel")
    b = d["route"]["buchungen"]
    assert b["B-04"]["anreise"] == "2027-05-14" and b["B-04"]["anreise_ab"] == "14:00" and b["B-01"]["vor_ort_zahlen"]
    assert not any("B-04" in str(w) and "B-01" in str(w) for w in d["route"].get("warnungen") or [])


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_jede_nacht_nur_ihre_buchung(tmp_path):
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    zwei_buchungen(quelle)
    bauen.bauen(quelle, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_buchung_zeitraum.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    t1, t7 = e["tage"]["T-01"], e["tage"]["T-07"]
    # Jede Nacht nur ihre Buchung, die Karte der Unterkunft an beiden (zwei Anreisen)
    assert t1["buchungen"] == ["B-01"] and t1["karte"], t1
    assert t7["buchungen"] == ["B-04"] and t7["karte"], t7
    # Check-in-Ansicht: Nummer, Check-in und vor Ort zu zahlen oben; Preis und Stornoregel zugeklappt; kein ⓘ an der Adresse
    assert "HE-2027-0415" in t1["oben"] and "Check-in" in t1["oben"] and "15:00" in t1["oben"] and "Check-out" in t1["oben"], t1
    assert "Vor Ort zu zahlen" in t1["oben"] and "Preis" not in t1["oben"] and "Storno" not in t1["oben"], t1
    assert t1["einzelheiten_zu"] and not t1["herkunft_adresse"], t1
    assert "bezahlt" in t7["marken"], t7
    assert "Ab: Do 13.5., 08:00 · Online-Check-in" in t7["oben"], t7   # Uhrzeit im Feld, nicht im Text (#472)
    # Ein Link auf die zweite Buchung führt zum Tag ihrer Anreise
    assert e["ziel_b04"]["block"] and "14.5." in e["ziel_b04"]["kopf"], e["ziel_b04"]
    # Die Nacht des 14.5. ist gebucht, im Stand der Vorbereitung zählen beide Nächte als gebucht
    assert e["zeilen"]["T-07"] == "gebucht", e
