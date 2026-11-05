"""Browser-Rundgang durch die Beispielreise (Designsystem, frieda-reist#18): jede Ansicht ohne Skriptfehler und nicht leer."""
import datetime
import functools
import http.server
import json
import re
import time
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
from conftest import meldet  # noqa: E402


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
    assert e["schrift"] == {}        # jeder Text hat eine Stufe der Schriftleiter (Größe -> Ansicht und Element)
    assert e["ohneArt"] == []        # jede Kennung gehört einer Art der Ontologie mit Bausteinen an
    # Behälter statt Fenster (#332, Schritt D): bei 320, 700, 900, 1100 und 1300 px kein seitlicher Überstand; in einer schmalen
    # Spalte (340 px) am Rechner (1300 px) zeigen Vergleich und Kennzahlen die schmale Darstellung
    assert e["behaelter"]["ueberstand"] == []
    sp = e["behaelter"]["spalte"]
    assert sp["vergleich"]["breite"] == 340 and not sp["vergleich"]["ueberstand"], sp
    assert sp["vergleich"]["karten"] <= 2 and sp["vergleich"]["tabelle"] == "none" and sp["vergleich"]["umschalter"] != "none", sp
    assert sp["kennzahlen"]["spaltenNach"] == 2 and sp["kennzahlen"]["kacheln"] > 2, sp
    # Wahl-Modul: öffnet an der Stelle, zeigt mindestens 2 Möglichkeiten (Handy als Karten, höchstens 2; Rechner als Tabelle
    # mit allen gültigen, sortierbar, Zeile klappt auf; Alternativen D1, 29.10.2026)
    for breite, v in e["vergleich"].items():
        assert v["sichtbar"] and v["offen"] == "true", (breite, v)
        assert 2 <= v["spalten"] and (int(breite) >= 700 or v["spalten"] <= 2), (breite, v)
        if int(breite) >= 700:
            assert v["sortiert"] == 1 and v["aufgeklappt"] == 1 and v["falscheSpalten"] == [], (breite, v)
            ez = v["einzelheiten"]
            assert ez["doppelt"] == 0 and not ez["fehlertext"] and not ez["nummern"] and not ez["springt"], (breite, ez)
            assert ez["kursiv"] == "normal" and ez["ohneNummern"] == "|zu teuer" and ez.get("herkunft", True), (breite, ez)
            assert ez["iKnoepfe"] == 0, (breite, ez)      # Herkunft hinter dem Wert, kein „i“ (#58)
    assert set(e["vergleich"]) == {"390", "1200"}
    # Leiste als App: bleibt unten, wenn iOS die Höhe nach der Tastatur vergisst (800 statt 500 px), mit Tastatur über
    # ihr; im Browser ändert sich nichts (Abstand unten 12 px)
    a, w = e["leiste"]["app"], e["leiste"]["browser"]
    assert a["start"] == a["klein"] == a["zu"] == a["voll"] == 788, a
    assert a["tippt"] == 488, a
    assert w == {"start": 788, "klein": 488, "tippt": 488, "zu": 488, "voll": 788}, w
    dom = json.loads((tmp_path / "dom.json").read_text(encoding="utf-8"))
    # Wert je Datum: die Unterkunft zeigt beide Einträge; Herkunft steht hinter dem Wert (#58), nicht im Text
    u01 = dom["1200#U-01"]
    assert "15.5.: " in u01 and "sonst: " in u01 and "140 €" in u01
    assert 'class="mk-w"' in u01 and 'class="mk-i"' not in u01 and '<span class="mk-q" role="tooltip" hidden="">Beispielwert, erfunden' in u01
    # Regeln und Anschluss (Paket 4): an der Wahlstelle stehen „Setzt voraus“ und die berechnete Lücke der erfundenen V-01.c
    v01 = dom["1200#V-01"]
    assert meldet(v01, "seite.vergleich.setzt_voraus_label") and meldet(v01, "seite.vergleich.schliesst_aus_label") and "(im Plan)" in v01
    # die Lücke fällt auf; im Vergleich ohne Knopf (Herkunft dort einmal je Möglichkeit, #58), sonst hinter dem Wert
    assert re.search(r'class="(mk-w )?mk-luecke"[^>]*>Lücke am Anfang: Altendorf → Bad Schandau<', v01)
    # Bausteinseite: alle Ebenen, keine Sprungziele (die echten Stellen bleiben eindeutig), kein „null“
    b = dom["1200#bausteine"]
    for teil in ("Atom · Zustand", "Atom · Wert", "Molekül · Listenzeile", "Molekül · Frage als Zeile", "Molekül · Rückmeldung", "Molekül · Aufgabe", "Molekül · Wunschkarte", "Molekül · Kennzahlenleiste", "Organismus · Wahl-Modul", "Organismus · Tageskasten",
                 "Ontologie · Grundform → Bausteine", "Atom · Etikett", "Molekül · Reisetext: Tabellen", "Molekül · Reiter", "Organismus · Tageskasten der Tagesseite", "Vorlage · Tageskachel", "Molekül · Kapitel", "Organismus · Karte der Reise",
                 "Molekül · Stornierte Buchungen"):
        assert teil in b, teil
    assert ' id="' not in b.split(">", 1)[1]
    assert "null" not in re.sub(r"<[^>]+>", " ", b)
    assert b.count('class="zid hat-rm"') >= 1 and b.count('class="zid hat-ag"') == 1 and 'class="zid hat-rm hat-ag"' in b
    assert 'class="textmerkmale"' in b and 'class="tabelle stapel"' in b and 'role="tablist"' in b


def test_zweite_beispielreise_ohne_wanderung_baut_sauber(tmp_path):
    """Stadtwochenende (#266): eine Reise ohne Etappen, Varianten und Tagesseiten baut ohne Fehler und Warnungen; die
    Software kennt nur Grundformen (ADR-0001, Frage 1)."""
    ziel = tmp_path / "web" / "stadt"
    bauen.bauen(WURZEL / "beispiel/reisen/stadtwochenende", ziel)
    d = json.loads((ziel / "daten.json").read_text(encoding="utf-8"))
    assert not [a for a in d["abschnitte"] if a["typ"] == "strecke"]
    r = d["route"]
    assert [t["titel"] for t in r["tage"]] == ["Anreise und Ankommen bei Tante Anna", "Samstag in Beispielstadt", "Museum und Rückfahrt"]
    assert r["wahlstellen"] == [] and r["plaene"] == [] and r["warnungen"] == []
    assert set(r["arten"]) == {"gastzimmer", "essen", "museum", "bahn"}


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_alle_ansichten_der_zweiten_beispielreise(tmp_path, browser):
    """Derselbe Rundgang wie bei der Wanderung, jetzt an einer Reise anderen Typs (#266, ADR-0001 Frage 1)."""
    bauen.bauen(WURZEL / "beispiel/reisen/stadtwochenende", tmp_path / "web" / "stadt")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_browser.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/stadt/"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["routen"] > 20
    assert e["fehler"] == [] and e["leer"] == [] and e["breit"] == [] and e["schrift"] == {} and e["ohneArt"] == []


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_neue_reise_aus_der_vorlage(tmp_path, browser):
    """Paket H: Eine frisch angelegte Reise (Status idee, ohne Plan) zeigt jede Ansicht ohne Fehler und ohne Leere. Ohne Tage
    beginnt sie mit „Wissen“: die Eckdaten unter „Über diesen Plan“, die offene Frage in „Zu tun“ (#214: kein Reiter „Plan“)."""
    import neu
    r = neu.anlegen(tmp_path / "reisen", "Skiurlaub im Tal", datetime.date(2027, 2, 6), datetime.date(2027, 2, 13),
                    {"ida": {"name": "Ida", "rolle": "organisator"}, "karl": {"name": "Karl", "rolle": "mitwirkend"}},
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
    assert 'id="ueber-plan"' in dom["390#"] and "6.–13. Februar 2027" in dom["390#W-01"]
    assert 'id="fragen"' in dom["390#offen"] and "Offene Fragen" in dom["390#offen"]
    # die eine Frage der Vorlage (F-01) steht mit ihrem Text in „Zu tun“, nicht nur die Überschrift
    f01 = next(z for z in (r / "offene-fragen.md").read_text(encoding="utf-8").splitlines() if z.startswith("| F-01 "))
    assert f01.split("|")[2].strip().split("?")[0] in dom["390#offen"], f01


# Erste Einträge einer neuen Reise, wie sie über den Konnektor entstehen (erfunden, Beispielwerte): ein Ort, eine Ferienwohnung
# über drei Nächte mit einer Buchung, vier Tage ohne Pläne und ohne Wahlstellen
ERSTE_EINTRAEGE = {
    "start": {"datum": datetime.date(2027, 2, 6), "ort": "O-01"},
    "ende": {"datum": datetime.date(2027, 2, 9), "ort": "O-01"},
    "orte": {"O-01": {"name": "Talort (erfunden)", "quelle": "erfunden (Beispiel)"}},
    "unterkuenfte": {"U-01": {"name": "Ferienwohnung am Hang (erfunden)", "ort": "O-01", "art": "ferienwohnung",
                              "adresse": {"wert": "Hangweg 2 (Beispielwert)", "quelle": "erfunden (Beispiel)"},
                              "quelle": "erfunden (Beispiel)"}},
    "buchungen": {"B-01": {"fuer": ["U-01"], "status": "gebucht", "nummer": "FW-0001", "quelle": "erfunden (Beispiel)"}},
    "tage": {"T-01": {"titel": "Anreise (erfunden)", "nacht": "U-01"}, "T-02": {"titel": "Im Tal (erfunden)", "nacht": "U-01"},
             "T-03": {"titel": "Am Berg (erfunden)", "nacht": "U-01"}, "T-04": {"titel": "Abreise (erfunden)"}},
    "route": ["T-01", "T-02", "T-03", "T-04"],
}


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
def test_neue_reise_aus_der_vorlage_im_browser(tmp_path):
    """#214 (K6): Eine frisch aus engine/reisevorlage angelegte Reise mit ihren ersten Tagen sieht im Browser aus wie die
    Beispielreise: Zeitachse, Tagesseiten, „Zu tun“, kein Reiter „Plan“, die Buchung genau einmal vollständig."""
    import neu
    import yaml
    from test_eine_seitenordnung import messen
    r = neu.anlegen(tmp_path / "reisen", "Skiurlaub im Tal", datetime.date(2027, 2, 6), datetime.date(2027, 2, 9),
                    {"ida": {"name": "Ida", "rolle": "organisator"}, "karl": {"name": "Karl", "rolle": "mitwirkend"}},
                    "Ida", ziel="Oberstdorf")
    (r / "plan").mkdir(exist_ok=True)
    (r / "plan" / "routen.yaml").write_text(yaml.safe_dump(ERSTE_EINTRAEGE, allow_unicode=True, sort_keys=False), encoding="utf-8")
    import schreiben
    neu.arten_ableiten(r)             # Art der Ferienwohnung (Grundform aufenthalt)
    schreiben.plan_sicherstellen(r)   # wie der Schreibweg: den Plan in reise.json eintragen
    web = tmp_path / "web"
    bauen.bauen(r, web / r.name)
    d = json.loads((web / r.name / "daten.json").read_text(encoding="utf-8"))
    assert d["route"]["plaene"] == [] and [t["id"] for t in d["route"]["tage"]] == ["T-01", "T-02", "T-03", "T-04"]
    e = messen(web, d, voll={"B-01": "FW-0001"}, pfad=r.name)
    assert "plan" not in e["reiter"] and "offen" in e["reiter"], e["reiter"]
    assert e["start"]["achse"] and e["start"]["zeilen"] == ["T-01", "T-02", "T-03", "T-04"] and e["start"]["tageskaesten"] == 0, e["start"]
    assert all(v["tagseite"] for v in e["tagesseiten"].values()), {t: v["tagseite"] for t, v in e["tagesseiten"].items()}
    gesehen, voll = set(), 0
    for a in e["ansichten"]:
        if a["schluessel"] not in gesehen:
            gesehen.add(a["schluessel"])
            voll += a["voll"]["B-01"]
    assert voll == 1, [(a["schluessel"], a["voll"]) for a in e["ansichten"]]
    assert e["zuTun"] and e["zuTun"]["zuBuchen"], e["zuTun"]


def seite_der_variante(tmp_path, browser, datum="2027-05-13", skript="seiten_variante.mjs", **variante):
    """Beispielreise mit anderem Status oder anderen Bausteinen bauen (wie test_regeln) und im Browser ansehen."""
    from test_regeln import reise_bauen
    seiten = reise_bauen(tmp_path, **variante)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(seiten)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / skript), str(PLAYWRIGHT),
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
    # „Zu tun“ mit „Zu entscheiden“ und „Zu buchen“ gibt es in jeder Reise mit Tagen (#214), Wünsche nur mit ihrem Baustein
    assert "wuensche" not in wenig["reiter"] and "offen" in wenig["reiter"], wenig
    assert wenig["knoepfe"] == 0 and wenig["kennungen"] > 0   # IDs stehen da, aber ohne Rückmeldeknopf


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_buchung_genau_einmal_vollstaendig(tmp_path, browser):
    """Eine Buchung (B-…, #76) wohnt bei ihrem Ding (ADR-0003): in der Unterkunftskarte des Abschnitts „Nacht“ der Tagesseite,
    genau einmal vollständig, in jeder Reise (#214: mit offenem Plan, mit festem Plan, mit darstellung.tiefe wie bei einer
    Rundreise; einen Reiter „Plan“ gibt es nicht mehr). #B-01 führt in jedem Fall hin."""
    for name, variante in (("offen", {}), ("fest", {"fest": True}), ("tiefe", {"darstellung": {"tiefe": True}})):
        e = seite_der_variante(tmp_path / name, browser, **variante)
        b = e["buchung"]
        assert b and b["sichtbar"] and b["nummer"] == "HE-2027-0415", (name, e)
        assert b["zahlung"] == "angezahlt · Anzahlung 30 €, Rest vor Ort (Beispielwert)", (name, b)   # Zahlstand in Worten (#166)
        assert b["reiter"] == "varianten", (name, b)          # Reise, nicht ein Reiter „Plan“
        assert len(e["stornoB01"]["b01"]) == 1, (name, e["stornoB01"]["b01"])   # genau ein Ding zeigt sie voll


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_stornierte_buchung_eingeklappt_am_ding(tmp_path, browser):
    """#146: Eine stornierte Buchung (B-03 an U-01) steht nicht mehr voll da, sondern an ihrem Ding im zugeklappten Block
    „Storniert (1)“ mit Hinweis zum Zurückholen; die geltende B-01 steht voll da. #B-03 öffnet den Block. Geprüft mit offenem
    Plan, mit festem Plan und mit darstellung.tiefe. Seit #214 steht B-01 an genau einem Ding voll (seiner Heimat), die übrigen
    Dinge zeigen den Chip."""
    for name, variante in (("plan", {}), ("fest", {"fest": True}), ("tiefe", {"darstellung": {"tiefe": True}})):
        e = seite_der_variante(tmp_path / name, browser, **variante)
        # AC-1, AC-2: am Ding mit B-01 steht B-01 voll, B-03 nur im zugeklappten Block „Storniert (1)“, unsichtbar
        s = e["stornoB01"]
        assert len(s["b01"]) == 1, (name, s["b01"])   # #214: genau ein Ding mit vollem Block
        for o in s["b01"]:
            assert o["sichtbar"] and not o["imBlock"], (name, o)
            assert len(o["bloecke"]) == 1 and o["b03Draussen"] == 0, (name, o)
            blk = o["bloecke"][0]
            assert blk["summary"] == "Storniert (1)" and blk["offen"] is False, (name, o)
            # AC-4: Hinweis und die Buchung unverändert (Chip „storniert“, Nummer, Verlauf mit Grund)
            assert blk["hinweis"] == "Zurückholen: im Gespräch mit Frieda.", (name, o)
            i = blk["b03"]
            assert i and "storniert" in i["chip"] and i["nummer"] == "Nummer: HE-2027-0388", (name, o)
            assert i["verlauf"] == "Verlauf (2)" and i["grund"], (name, o)
        assert s["b03"] >= 1 and s["b03Draussen"] == 0 and not s["b03Sichtbar"], (name, s)
        # AC-8: kein Chip führt zur stornierten Buchung; der Chip der Unterkunft zeigt „gebucht“ aus B-01
        assert s["chipZuB03"] == 0 and "gebucht" in s["chipZuB01"], (name, s)
        # AC-3: ein Ding ohne stornierte Buchung (E-20 mit B-02) hat keinen Block und keinen Hinweis
        s = e["stornoB02"]
        assert s["b02"], (name, s)
        for o in s["b02"]:
            assert o["bloecke"] == [] and not o["zurueckholen"], (name, o)
        # AC-5: #B-03 öffnet den Block, die Buchung ist sichtbar und steht bei U-01 neben der geltenden B-01
        s = e["stornoB03"]
        assert s["b03Sichtbar"] and s["b03Draussen"] == 0, (name, s)
        assert any(blk["offen"] and blk["b03"] for blk in s["bloecke"]), (name, s)
        assert any(o["sichtbar"] and len(o["bloecke"]) == 1 for o in s["b01"]), (name, s)
        if name == "fest":
            # AC-7: Tagesseite T-02, Nacht in Hohnstein: V-03 hat eine gültige Option und eine verworfene (V-03.b). Die Zeile
            # zählt nur die gültige, steht aber da, damit die verworfene im Block „Verworfen (1)“ und #V-03.b erreichbar bleiben
            m = e["moeglichkeiten"]
            assert m["nacht"], (name, m)
            assert [z for z in m["zeilen"] if z.startswith("Alle Möglichkeiten (")] == ["Alle Möglichkeiten (1)"], (name, m)
            assert "Verworfen (1)" in m["zeilen"] and m["verworfenSichtbar"], (name, m)


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_b2_wissen_orte_vergleich(tmp_path, browser):
    """#58 (Entscheidung PO 1.11.2026), Plan A fest: Weitere Wege am Rechner als Tabelle, am Handy und Tablet als Einträge mit
    einer Zeile Kennzahlen, nie als Kacheln; Ortsseite als Ebenen ohne Kasten in einer Lesespalte; Vergleich ohne „i“, die
    Herkunft einmal je Möglichkeit (Karte unten, Tabelle als Zeile darunter), Tabelle nur am Rechner."""
    # Erfundene Abwandlung: der Gasthof in Hohnstein (V-03.b) ist nicht verworfen, damit die Nacht zwei gültige Möglichkeiten
    # mit Quellen hat; V-03.a bleibt gewählt, der Plan bleibt fest (sonst gäbe es keine „Weiteren Wege“)
    offen = [('- {datum: 2026-10-20, status: verworfen, wer: Ida, grund: "Anstieg am Morgen"}',
              '- {datum: 2026-10-20, status: vorgeschlagen, wer: Ida, grund: "Abendessen im Haus"}')]
    e = seite_der_variante(tmp_path, browser, datum="2026-11-01", skript="b2_browser.mjs", fest=True, routen_ersetzen=offen)   # vor der Reise
    for breite in ("390", "820", "1300"):
        w, o, v = e[breite]["wege"], e[breite]["ort"], e[breite]["vergleich"]
        assert w and w["zeilen"] >= 1 and w["kacheln"] == 0 and not w["ueberlauf"] and w["links"] == w["zeilen"], (breite, w)
        assert w["kopf"] == (breite == "1300"), (breite, w)   # Tabellenkopf nur am Rechner
        assert w["zahlen"] and all(z.strip() for z in w["zahlen"]), (breite, w)
        assert o["spalte"] and o["abschnitte"] == 2 and o["kaesten"] == 0 and o["allesSichtbar"], (breite, o)
        assert v and v["iImVergleich"] == 0 and not v["ueberlauf"], (breite, v)
        assert v["herkunftZeilen"] >= 1 and v["herkunftOhneAufklappen"] and v["quellenDa"], (breite, v)
        assert v["herkunftText"].startswith("Quellen: "), (breite, v)
        if breite == "1300":
            assert v["tabelle"] and v["karten"] == 0 and v["nachSortieren"], (breite, v)   # im breiten Behälter (1100 px) die Tabelle
            # Behälter statt Fenster (#332, Schritt D): in der Spalte der Tagesseite (unter 960 px) am Rechner Karten, keine Tabelle
            assert v["inSpalte"]["breite"] < 960 and not v["inSpalte"]["tabelle"] and v["inSpalte"]["karten"] >= 2, (breite, v)
            assert v["aufgeklappt"]["mehr"] == 1 and v["aufgeklappt"]["iImKasten"] == 0, (breite, v)
        else:
            assert not v["tabelle"] and v["karten"] >= 2 and v["herkunftKarten"] >= 1, (breite, v)
    assert e["1300"]["ort"]["breite"] <= 44 * 17 + 1   # Lesebreite --lese (44rem bei 106,25 % Schrift), nicht die volle Breite
    # Zweiter Pfad der Ortsseite: Reisen mit darstellung.tiefe zeigen den Ort über ansichtOrt, dort gilt dasselbe
    t = seite_der_variante(tmp_path / "tiefe", browser, datum="2026-11-01", skript="b2_browser.mjs", darstellung={"tiefe": True})
    for breite in ("390", "1300"):
        o = t[breite]["ort"]
        assert o["spalte"] and o["abschnitte"] == 2 and o["kaesten"] == 0 and o["allesSichtbar"], (breite, o)


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_buchung_und_anschluss_mit_namen(tmp_path, browser):
    """#189: In den Einzelheiten einer Buchung für zwei Strecken stehen ihre Namen als Link zur Heimat, keine Kennungen; die
    Anschlusswarnung nennt die Strecken beim Namen und die Zeiten wie sonst auf der Seite (ohne Jahr und Zeitzone).
    Erfundene Abwandlung der Beispielreise: B-02 gilt für zwei Bahnfahrten, und der Weg ab Stadt Wehlen beginnt vor der Ankunft."""
    reise = tmp_path / "quelle" / "beispielreise"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", reise)
    datei = reise / "plan/routen.yaml"
    text = datei.read_text(encoding="utf-8")
    for alt, neu in (('wert: "08:40", quelle', 'wert: "2027-05-13T08:40+02:00", quelle'),
                     ("von: O-02, nach: O-03, art: wandern,", 'von: O-02, nach: O-03, art: wandern, ab: "08:30",'),   # altes Feld wird weiter gelesen
                     ("    fuer: [E-20]\n    status: gebucht\n", '    fuer: [E-20, E-21]\n    preise: {E-20: "12 €", E-21: "8 €"}\n    status: angefragt\n')):
        assert alt in text, alt
        text = text.replace(alt, neu)
    datei.write_text(text, encoding="utf-8")
    bauen.bauen(reise, tmp_path / "web" / "beispiel")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "namen_browser.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/"],
                             capture_output=True, text=True, timeout=120, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    b = e["buchung"]
    assert b and not re.search(r"\bE-\d", b["text"]), b
    hin, zurueck = "S-Bahn Dresden → Stadt Wehlen, Fähre über die Elbe", "S-Bahn Bad Schandau → Dresden"
    assert b["links"] == [["#E-20", hin], ["#E-21", zurueck], ["#E-20", hin], ["#E-21", zurueck]], b   # Für, Preise
    assert f"{hin}: 12 €" in b["text"] and f"{zurueck}: 8 €" in b["text"], b
    assert e["warnungen"], e
    for w in e["warnungen"]:
        assert not re.search(r"\b[ET]-\d", w) and "+02:00" not in w and "2027" not in w, w
        assert f"{hin} kommt um 13.5. 8:40 an" in w and "fährt schon um 8:30 ab" in w, w


def _funktion(quelle, name):
    """Rumpf einer Funktion der Vorlage (vom Kopf bis zur schließenden Klammer am Zeilenanfang)."""
    m = re.search(rf"^function {name}\(.*?^\}}", quelle, re.S | re.M)
    assert m, name
    return m.group(0)


def test_stornierte_buchungen_ein_helfer_an_jeder_heimat():
    """#146, AC-6: Strecke, Aufenthalt und Unterkunft hängen stornierte Buchungen über denselben Helfer an (keine Kopien);
    buchungenBei liefert nur geltende, stornierteBei nur stornierte, jeweils an der Heimat (ADR-0003). Der Tageskasten ist seit
    #214 nirgends mehr Heimat einer Buchung (die vierte Stelle, der Tageskasten im Plan ohne Tagesseiten, ist entfallen)."""
    q = (WURZEL / "engine" / "vorlage.html").read_text(encoding="utf-8")
    assert re.search(r"^function stornierteBuchungen\(|^const stornierteBuchungen = ", q, re.M)
    assert re.search(r"^const stornierteBei = ", q, re.M) or re.search(r"^function stornierteBei\(", q, re.M)
    for name in ("streckeZeile", "aufenthaltZeile", "dingKarte"):
        f = _funktion(q, name)
        assert "stornierteBuchungen(stornierteBei(" in f, name
    # Stornierte nie über buchungenBei voll gezeichnet: der Helfer trennt nach Status
    bei = re.search(r"^const buchungenBei = .*$", q, re.M)
    assert bei and "storniert" in bei.group(0), bei and bei.group(0)
    assert 'T("seite.buchung.zurueckholen")' in q and 'T("seite.buchung.storniert_n"' in q   # die Texte stehen im Katalog (ADR-0006)
    de = (WURZEL / "engine/texte_de.py").read_text(encoding="utf-8")
    assert '"seite.buchung.zurueckholen": "Zurückholen: im Gespräch mit Frieda."' in de and '"seite.buchung.storniert_n": "Storniert ({n})"' in de


def test_stornierte_buchung_bleibt_in_den_daten(tmp_path):
    """#146, AC-13 und AC-8: Nichts wird gelöscht. B-03 steht nach dem Bauen mit Status und beiden Verlaufseinträgen in den Daten;
    der Buchungsstand von U-01 kommt aus der geltenden B-01."""
    ziel = tmp_path / "web"
    bauen.bauen(WURZEL / "beispiel/reisen/beispielreise", ziel)
    r = json.loads((ziel / "daten.json").read_text(encoding="utf-8"))["route"]
    b = r["buchungen"]["B-03"]
    assert b["status"] == "storniert" and b["fuer"] == ["U-01"] and b["nummer"] == "HE-2027-0388"
    assert [v["was"] for v in b["verlauf"]] == ["angelegt", "Status"] and "Zimmer doppelt gebucht" in b["verlauf"][1]["grund"]
    assert r["unterkuenfte"]["U-01"]["buchung"] == "gebucht" and r["unterkuenfte"]["U-01"]["buchung_id"] == "B-01"


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


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_anmeldung_auf_der_seite(tmp_path, monkeypatch, browser):
    """Paket J2: ohne Konto „Anmelden“ und Namensfeld (Übergang: eingetippter Name geht), angemeldet der eigene Name
    oben rechts, kein Namensfeld, die Rückmeldung trägt den Namen aus dem Konto."""
    from test_regeln import reise_bauen, starten
    import konten
    import rueckmeldungen as rm
    seiten = reise_bauen(tmp_path)
    (tmp_path / "ablage" / "beispielreise").mkdir(parents=True)
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    rm._zeiten.clear()
    dienst, durl = starten(rm.Dienst)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(seiten)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    basis = f"http://127.0.0.1:{s.server_address[1]}"
    monkeypatch.setenv("FR_BASIS", basis)          # die Seite liegt auf Friedas Adresse
    konten.einladen("beispielreise", "karl", "karl@beispiel.invalid", "mitwirkend", "Karl", "Ida")
    konten.code_anfordern("karl@beispiel.invalid")
    code = re.search(r"(\d{3}) (\d{3})", json.loads((tmp_path / "mails.jsonl").read_text().splitlines()[-1])["text"])
    token, karl = konten.anmelden("karl@beispiel.invalid", code.expand(r"\1\2"))
    konten.sprache_setzen(karl["id"], "de")   # angemeldet folgt die Seite der Sprache des Kontos (#188)
    rm.meldung_anlegen(tmp_path / "ablage" / "beispielreise", ["Karl"], "hinweis", "allgemein", "Treffpunkt ist jetzt 8:40 Uhr.")
    import push
    push.schluessel()                          # Push-Dienst eingerichtet: die Seite bietet Benachrichtigungen an

    def lauf(sitzung):
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_konto.mjs"), str(PLAYWRIGHT),
                              f"{basis}/beispielreise/", durl, sitzung],
                             capture_output=True, text=True, timeout=120, env={**os.environ, "RH_BROWSER": browser})
        assert aus.returncode == 0, aus.stderr[-2000:]
        return json.loads(aus.stdout.strip().splitlines()[-1])
    try:
        ohne, mit = lauf("-"), lauf(token)
    finally:
        s.shutdown()
        dienst.shutdown()
    assert ohne["fehler"] == [] and mit["fehler"] == []
    assert ohne["knopf"]["text"] == "Anmelden" and ohne["knopf"]["ziel"].startswith("/anmelden?zurueck=%2Fbeispielreise%2F")
    assert ohne["nameFeld"] == "text" and any("anmelden" in h for h in ohne["hinweis"])
    assert mit["knopf"] == {"text": "Karl", "ziel": "/konto"}
    # Benachrichtigungen haben ihre Heimat auf Mein Konto (#21, Entscheidung A): angemeldet nur ein Verweis dorthin
    assert ohne["push"] is None and mit["push"] == {"text": "Benachrichtigungen: unter „Mein Konto“", "ziel": "/konto#push"}
    assert mit["nameFeld"] == "hidden" and "Du schreibst als Karl." in mit["hinweis"]
    assert "Danke" in ohne["meldung"] and "Danke" in mit["meldung"]
    # Meldungen an die Person (#21): angemeldet als Hinweis, ohne Netz aus dem Speicher, nach „Gelesen“ weg
    assert ohne["fuerDich"]["hidden"] and ohne["fuerDichOffline"]["hidden"]
    assert not mit["fuerDich"]["hidden"] and mit["fuerDich"]["text"].startswith("Für dich") and "8:40 Uhr" in mit["fuerDich"]["text"]
    assert mit["fuerDichOffline"] == mit["fuerDich"]
    assert mit["fuerDichGelesen"]["hidden"] and mit["fuerDichDanach"]["hidden"]
    namen = [json.loads(z)["name"] for z in (tmp_path / "ablage/beispielreise/eingang.jsonl").read_text().splitlines()]
    assert namen == ["Hanna", "Karl"]


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_anmeldeseiten_im_browser(tmp_path, monkeypatch, browser):
    """Paket J2: Formulare so abschicken, wie ein Browser es tut (er setzt Origin selbst). Fängt Einstellungen ab, bei
    denen Browser „Origin: null“ schicken und die Herkunftsprüfung jede Anmeldung ablehnen würde."""
    from test_regeln import starten
    import konnektor as kn
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    monkeypatch.setenv("KN_SEITEN", str(tmp_path / "seiten"))
    monkeypatch.setenv("KN_ZUGAENGE", str(tmp_path / "zugaenge.json"))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    k, kurl = starten(kn.Dienst)
    monkeypatch.setenv("FR_BASIS", kurl)
    email = "neu@beispiel.invalid"
    try:
        proc = subprocess.Popen(["node", str(Path(__file__).parent / "seiten_anmelden.mjs"), str(PLAYWRIGHT), kurl, email],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env={**os.environ, "RH_BROWSER": browser})
        assert json.loads(proc.stdout.readline()) == {"bereit": True}, proc.stderr.read()[-2000:]
        # Die Seite zeigt „Code eingeben“, bevor der Dienst die Mail abgelegt hat: auf die Datei warten statt sie einmal zu
        # lesen (unter Last fehlte sie sonst, #204)
        mails = tmp_path / "mails.jsonl"
        for _ in range(150):
            if mails.exists() and mails.read_text().strip():
                break
            time.sleep(0.1)
        code = re.search(r"(\d{3}) (\d{3})", json.loads(mails.read_text().splitlines()[-1])["text"])
        out, err = proc.communicate(code.expand(r"\1\2") + "\n", timeout=60)
    finally:
        k.shutdown()
    assert proc.returncode == 0, err[-2000:]
    e = json.loads(out.strip().splitlines()[-1])
    assert e["nachAdresse"] == "Code eingeben", e
    assert e["antworten"][0] == 200 and e["nachCode"] == "Code eingeben", e   # neues Konto: jetzt fragt sie den Namen


def test_schriftleiter_ohne_freie_groessen():
    """Schriftleiter (docs/design.md): Jede Schriftgröße im Stil der Vorlage ist eine der fünf Stufen (var(--t-…)).
    Ausnahmen: Wurzel (html, %), Leiste unten (nav, Suche), Ziffer der Tagesnummer, Karte (px, Leaflet) und Hochzahlen (em)."""
    html = (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")
    css = html[html.index("<style>"):html.index("</style>")]
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    frei = []
    for regel in re.findall(r"([^{}]*)\{([^{}]*)\}", css):
        sel, inhalt = regel
        for wert in re.findall(r"font(?:-size)?:\s*([^;]+)", inhalt):
            if "var(--t-" in wert or wert.strip() in ("inherit",) or not re.search(r"\d(?:rem|px|em|%)", wert):
                continue
            if re.search(r"^\s*(html|.*\b(nav a|#suchKnopf|tagnr|leaflet|rh-|sup\.fn)\b)", sel.strip()) or "leaflet" in sel or ".rh-" in sel:
                continue
            frei.append(f"{sel.strip()[-60:]}: {wert}")
    assert frei == [], frei
