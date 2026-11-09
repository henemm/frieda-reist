"""Eine Seitenordnung für alle Reisen (frieda-reist#214, ADR-0003): Zeitachse in einer Spalte, je Tag eine Tagesseite, jedes
Ding genau einmal vollständig, keine doppelte ID, „Zu tun“ mit „Zu entscheiden“ und „Zu buchen“, Wahlen an ihrem Element.

Geprüft in vier Fällen, alle aus der Beispielreise abgeleitet (Kopie im Test, die Demo bleibt unverändert):
  (a) ohne_plaene   keine Pläne, keine Wahlstellen, Bausteine nur [karte] (wie ein Familienbesuch)
  (b) plaene_offen  Pläne P-A und P-B, keiner gewählt
  (c) plan_fest     Plan A gewählt (heute schon die Zielordnung; hier Regressionsschutz)
  (d) tiefe         Pläne offen, darstellung.tiefe und plan_reiter, ohne Baustein tagesseiten (wie eine Rundreise)
In allen Fällen hat das Hotel am Elbufer (U-01) mehrere Nächte mit einer Buchung (B-01) und die Burg Hohnstein (A-01) steht an
zwei Tagen. Alle Ergänzungen sind erfunden (Beispielwerte)."""
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
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIEL = WURZEL / "beispiel/reisen/beispielreise"
from playwright_pfad import PLAYWRIGHT  # noqa: E402

FAELLE = ["ohne_plaene", "plaene_offen", "plan_fest", "tiefe"]
OHNE_BROWSER = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")

# Woran die vollständige Form eines Dings zu erkennen ist (nur sie trägt diese Angabe; Zeilen und Chips nicht):
# Buchung B-01 ihre Nummer, das Hotel am Elbufer U-01 seine Adresse, die Burg Hohnstein A-01 ihr Eintritt (Merkmal).
VOLL = {"B-01": "HE-2027-0415", "U-01": "Terrassenufer 1, 01067 Dresden", "A-01": "6 €"}


def _laden(p):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _schreiben(p, y):
    p.write_text(yaml.safe_dump(y, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _gestreckt(r, tage_dresden):
    """U-01 über mehrere Nächte (weitere Tage in Dresden direkt nach T-01) und A-01 an zwei Tagen (T-02 und T-03)."""
    neu = {}
    for i in range(tage_dresden):
        neu[f"T-{7 + i:02d}"] = {"titel": f"Weiterer Tag in Dresden {i + 1} (erfunden, Beispielwert)", "nacht": "U-01"}
    r["tage"].update(neu)
    r["tage"]["T-03"]["aufenthalte"] = ["A-01"]   # Beispielwert: die Burg auch am Morgen des dritten Tags
    i = r["route"].index("T-01") + 1
    r["route"][i:i] = list(neu)
    r["ende"]["datum"] = r["ende"]["datum"] + datetime.timedelta(days=tage_dresden)
    return list(neu)


def fall_bauen(tmp, fall, an=None, wahl_offen=False, v03_offen=False):
    """Testreise des Falls ableiten und bauen -> (Seitenordner, daten.json als dict).
    an: zusätzliches „an:“ für V-02 (Wahl an einem Element, erfunden); wahl_offen: ohne Pläne, aber V-03 als offene Wahl."""
    quelle = tmp / "quelle"
    shutil.copytree(BEISPIEL, quelle)
    ry = quelle / "reise.yaml"
    rp = quelle / "plan" / "routen.yaml"
    reise, r = _laden(ry), _laden(rp)
    if fall == "ohne_plaene":
        _gestreckt(r, 2)   # U-01: drei Nächte (T-01, T-07, T-08), eine Buchung
        r.pop("plaene")
        v03 = r["wahlstellen"]["V-03"]
        r.pop("wahlstellen")
        r["tage"]["T-02"].pop("wahl")
        r["tage"]["T-03"].pop("wahl", None)   # V-06: Orte als Möglichkeit (#353, Schritt 2)
        r["tage"]["T-02"]["nacht"] = "U-02"
        for t in ("T-05", "T-06"):   # nur über V-01 erreichbar
            r["tage"].pop(t)
        (quelle / "plan" / "wuensche.yaml").unlink()   # Wünsche nennen V-01; der Baustein ist ohnehin aus
        r["route"] = [x for x in r["route"] if x != "V-01"] + ["T-04"]
        r["ende"]["datum"] = r["start"]["datum"] + datetime.timedelta(days=len(r["route"]) - 1)
        if wahl_offen:   # eine offene Wahl ohne Pläne: beide Unterkünfte in Hohnstein noch möglich (Beispielwert)
            for o in v03["optionen"]:
                o["verlauf"] = [{"datum": datetime.date(2026, 10, 20), "status": "vorgeschlagen", "wer": "Ida"}]
            r["wahlstellen"] = {"V-03": v03}
            r["tage"]["T-02"]["nacht"] = "V-03"
        reise["bausteine"] = ["karte"]   # wie eine Reise ohne Alternativen: kein varianten, tagesseiten, aufgaben, fragen
    else:
        _gestreckt(r, 1)   # U-01: zwei Nächte (T-01, T-07)
        if fall == "plan_fest":
            r["wahlstellen"]["V-01"]["optionen"][0]["verlauf"].append(
                {"datum": datetime.date(2026, 10, 25), "status": "gewaehlt", "wer": "Ida", "grund": "Test"})
        if fall == "tiefe":
            reise["bausteine"] = [b for b in reise["bausteine"] if b != "tagesseiten"]
            reise.setdefault("darstellung", {}).update({"tiefe": True, "plan_reiter": ["W-02"]})   # Eckdaten im Reiter „Plan“
        if an:
            r["wahlstellen"]["V-02"]["an"] = [an]
        if v03_offen:   # Unterkunft in Hohnstein noch offen und zugleich als Wahl des Tags genannt: Nacht und Wahl an T-02
            # sind dieselbe Kennung V-03 (Beispielwert)
            for o in r["wahlstellen"]["V-03"]["optionen"]:
                o["verlauf"] = [{"datum": datetime.date(2026, 10, 20), "status": "vorgeschlagen", "wer": "Ida"}]
            r["tage"]["T-02"]["wahl"] = ["V-02", "V-03"]
    _schreiben(ry, reise)
    _schreiben(rp, r)
    seiten = tmp / "seiten"
    d = bauen.bauen(quelle, seiten / "beispielreise")
    return seiten, json.loads((seiten / "beispielreise" / "daten.json").read_text(encoding="utf-8"))


def vorbedingung(fall, d):
    """Die abgeleitete Reise hat wirklich die Form ihres Falls (sonst prüft der Test etwas anderes)."""
    r = d["route"]
    assert r["buchungen"]["B-01"]["fuer"] == ["U-01"]
    assert len(r["unterkuenfte"]["U-01"]["naechte"]) == (3 if fall == "ohne_plaene" else 2), r["unterkuenfte"]["U-01"]["naechte"]
    assert [t["id"] for t in r["tage"] if "A-01" in (t.get("aufenthalte") or [])] == ["T-02", "T-03"]
    if fall == "ohne_plaene":
        assert r["plaene"] == []
    else:
        assert [p["id"] for p in r["plaene"]] == ["P-A", "P-B"]


def im_browser(seiten, skript, *args, timeout=300, pfad="beispielreise"):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(seiten)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / skript), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/{pfad}/", *args],
                             capture_output=True, text=True, timeout=timeout, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


def messen(seiten, d, extra=(), voll=VOLL, pfad="beispielreise"):
    """Startseite, jeden Reiter, jede Tagesseite und die Sprungziele der Dinge (und extra) im Browser messen."""
    tage = [t["id"] for t in d["route"]["tage"]]
    wahlen = [w["id"] for w in d["route"]["wahlstellen"]]
    e = im_browser(seiten, "seiten_eine_seitenordnung.mjs",
                   json.dumps({"tage": tage, "voll": voll, "wahlen": wahlen, "extra": list(extra)}), pfad=pfad)
    assert e["fehler"] == [], e["fehler"]
    return e


def rundgang(tmp, fall, extra=(), **kw):
    """Fall bauen, Vorbedingung prüfen und messen."""
    seiten, d = fall_bauen(tmp, fall, **kw)
    vorbedingung(fall, d)
    return messen(seiten, d, extra), d


def _ansichten(e):
    """Startseite, Reiter und Tagesseiten; jede Ansicht genau einmal (der Startreiter ist die Startseite)."""
    gesehen, aus = set(), []
    for a in e["ansichten"]:
        if a["schluessel"] in gesehen:
            continue
        gesehen.add(a["schluessel"])
        aus.append(a)
    return aus


# K1: Zeitachse in einer Spalte, je Tag eine Zeile mit genau einem Link (Fall a)
@OHNE_BROWSER
def test_ohne_plaene_zeitachse_eine_spalte_ein_link(tmp_path):
    e, d = rundgang(tmp_path, "ohne_plaene")
    tage = [t["id"] for t in d["route"]["tage"]]
    s = e["start"]
    assert s["achse"], s                                     # die Zeitachse steht auf der Startseite
    assert s["spalten"] == 1, s                              # eine Spalte: alle Tageszeilen am selben linken Rand
    assert s["zeilen"] == tage, s                            # je Tag eine Zeile, in Reihenfolge
    assert all(z == ["#" + t] for z, t in zip(s["zeilenLinks"], tage)), s   # je Zeile genau ein Link: zu ihrer Tagesseite
    assert s["tageskaesten"] == 0, s                         # keine Tageskästen der alten Plan-Seite
    for t in tage:                                           # jede Tagesseite gibt es
        assert e["tagesseiten"][t]["tagseite"], (t, e["tagesseiten"][t])


# K2: genau einmal vollständig, überall sonst Zeile oder Chip mit Link
@OHNE_BROWSER
@pytest.mark.parametrize("fall", FAELLE)
def test_genau_einmal_vollstaendig(tmp_path, fall):
    e, d = rundgang(tmp_path, fall)
    ans = _ansichten(e)
    for ding in VOLL:
        wo = [a["schluessel"] for a in ans for _ in range(a["voll"][ding])]
        assert len(wo) == 1, (fall, ding, wo)
    for w in d["route"]["wahlstellen"]:
        if sum(1 for o in w["optionen"] if o["status"] not in ("verworfen", "ersetzt")) < 2:
            continue
        if fall == "plan_fest" and w["id"] == "V-01":   # entschiedener Reiseteil: kein Vergleich mehr, Heimat „Entschieden“ (#450)
            continue
        wo = [a["schluessel"] for a in ans for _ in range(a["vergleiche"].get(w["id"], 0))]
        assert len(wo) == 1, (fall, w["id"], wo)
    # Der Link zu einem Ding führt an seine Heimat: dort steht es vollständig
    for ding in VOLL:   # (sprung enthält auch O-03 und Extras; deren Heimat ist kein Tag)
        z = e["sprung"][ding]
        assert z["voll"] and z["tagseite"], (fall, ding, z)


# K3: keine doppelte ID im DOM, in jeder Ansicht
@OHNE_BROWSER
@pytest.mark.parametrize("fall", FAELLE)
def test_keine_doppelte_id(tmp_path, fall):
    e, _ = rundgang(tmp_path, fall)
    doppelt = {a["schluessel"]: a["doppelt"] for a in _ansichten(e) if a["doppelt"]}
    assert doppelt == {}, (fall, doppelt)


# K3, Test 4: Nacht und Wahl an derselben Kennung (T-02, Nacht V-03): nur die Heimat trägt die ID
@OHNE_BROWSER
@pytest.mark.parametrize("fall", ["plaene_offen", "tiefe"])
def test_nachtzeile_und_wahlzeile_teilen_keine_id(tmp_path, fall):
    e, d = rundgang(tmp_path, fall, v03_offen=True)
    assert [w["offen"] for w in d["route"]["wahlstellen"] if w["id"] == "V-03"] == [True]
    for a in _ansichten(e):
        for vid in ("V-02", "V-03"):
            n = a["ids"].get(vid, 0)
            assert n <= 1, (fall, a["schluessel"], vid, n)
    # Die Heimat von V-03 (Unterkunft in Hohnstein) ist die Tagesseite seiner Nacht
    assert e["tagesseiten"]["T-02"]["ids"].get("V-03") == 1, (fall, e["tagesseiten"]["T-02"])


# K4: „Zu tun“ mit „Zu buchen“ ohne Pläne, und „Zu entscheiden“, sobald es ohne Pläne etwas zu entscheiden gibt
@OHNE_BROWSER
def test_zu_tun_auch_ohne_plaene(tmp_path):
    e, _ = rundgang(tmp_path / "a", "ohne_plaene")
    assert "zu-tun" in e["reiter"], e["reiter"]
    tun = e["zuTun"]
    assert tun and tun["zuBuchen"], tun
    assert not tun["zuEntscheiden"], tun   # keine Wahlstelle: nichts zu entscheiden
    e2, _ = rundgang(tmp_path / "a2", "ohne_plaene", wahl_offen=True)
    assert "zu-tun" in e2["reiter"] and e2["zuTun"] and e2["zuTun"]["zuEntscheiden"] and e2["zuTun"]["zuBuchen"], e2["zuTun"]


# K5: Wahlen erscheinen an ihrem Element, in allen Fällen mit Wahlstellen (V-02 am Tag T-02, dazu an: O-03 erfunden)
@OHNE_BROWSER
@pytest.mark.parametrize("an", ["O-03", "E-02", "U-01", "W-05"])   # Ort, Strecke (anderer Tag als V-02), Unterkunft, Wissen
@pytest.mark.parametrize("fall", ["plaene_offen", "plan_fest", "tiefe"])
def test_wahl_mit_an_steht_am_element(tmp_path, fall, an):
    e, d = rundgang(tmp_path, fall, extra=[an] if an != "O-03" else [], an=an)
    assert d["route"]["wahlstellen"][[w["id"] for w in d["route"]["wahlstellen"]].index("V-02")]["an_ids"] == [an]
    t02 = e["tagesseiten"]["T-02"]
    assert t02["tagseite"] and t02["vergleiche"].get("V-02") == 1, (fall, an, t02)   # die Wahl mit Vergleich an ihrem Tag
    ziel = e["sprung"].get(an)
    assert ziel and ziel["ziel"], (fall, an, ziel)
    if an in ("E-02", "U-01"):   # Strecke, Unterkunft: Heimat ist die Tagesseite, die Wahl steht dort am Tageskasten
        assert ziel["tagseite"] and "#V-02" in ziel["wahlLinksSeite"], (fall, an, ziel)
    else:                        # Ort, Abschnitt des Wissens: Abschnitt „Zur Wahl“ am Element mit Zeile oder Vergleich
        assert ziel["wahlLinks"].count("#V-02") >= 1, (fall, an, ziel)


@OHNE_BROWSER
def test_ohne_plaene_keine_marke_und_kein_vergleich(tmp_path):
    """K5, Fall (a): ohne Wahlstellen erscheint weder eine Marke „offen“ noch ein Vergleich."""
    e, _ = rundgang(tmp_path, "ohne_plaene")
    for a in _ansichten(e):
        assert a["vergleiche"] == {} and a["wahlen"] == 0, a["schluessel"]


# Entscheidung 5 (PO 2.11.2026): Etappen richten sich nach dem Plan der Zeitachse; bei offenen Plänen wie bei festem Plan
@OHNE_BROWSER
def test_etappen_bei_offenen_plaenen_wie_bei_festem_plan(tmp_path):
    offen, _ = rundgang(tmp_path / "b", "plaene_offen")
    fest, _ = rundgang(tmp_path / "c", "plan_fest")
    assert ("etappen" in offen["reiter"]) == ("etappen" in fest["reiter"]), (offen["reiter"], fest["reiter"])
    o, f = offen["tagesseiten"]["T-02"], fest["tagesseiten"]["T-02"]
    assert o["tagseite"] and o["etappe"] == f["etappe"] and f["etappe"], (o, f)   # ganze Etappe E-01 mit Karte am Tag


# #450 (PO 9.11.2026): Eine entschiedene Wahlstelle über einen Reiseteil steht nicht mehr unter „Zur Wahl“ am Tag, sondern
# zugeklappt unter „Entschieden“ am Ende der Reise; Links auf sie und ihre Optionen führen dorthin. Offen bleibt sie am Tag.
@OHNE_BROWSER
def test_entschiedene_wahl_steht_unter_entschieden(tmp_path):
    seiten, d = fall_bauen(tmp_path / "fest", "plan_fest")
    tage = [t["id"] for t in d["route"]["tage"]]
    e = im_browser(seiten, "seiten_entschieden.mjs", json.dumps({"tage": tage, "sprung": ["V-01", "V-01.a", "V-01.b"]}))
    assert e["fehler"] == [], e["fehler"]
    assert not e["tag"]["v01"] and not e["tag"]["zurWahl"], e["tag"]       # an keinem Tag „Zur Wahl“ oder V-01
    r = e["reise"]
    assert r["entschieden"] == 1 and r["zu"], r                                # ein Eintrag, zugeklappt
    assert r["zeile"].startswith("Letzter Tag: Weg zum Zug") and "Abstieg nach Bad Schandau" in r["zeile"], r
    assert r["nichtGewaehlt"] == 2, r                                          # die zwei übrigen Möglichkeiten, aufgeklappt
    for id_, z in e["sprung"].items():                                         # der Link führt in die Reise und klappt auf
        assert z["reiter"] == "varianten" and z["offen"] and z["imBlock"], (id_, z)
    seiten_o, d_o = fall_bauen(tmp_path / "offen", "plaene_offen")
    offen = im_browser(seiten_o, "seiten_entschieden.mjs", json.dumps({"tage": [t["id"] for t in d_o["route"]["tage"]], "sprung": []}))
    assert offen["tag"]["v01"] and offen["tag"]["zurWahl"] and offen["reise"]["entschieden"] == 0, offen   # offen: am Tag
