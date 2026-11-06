"""Orte (O-…) als Möglichkeiten einer Wahlstelle (#353, Schritt 2, Spec docs/specs/routen/orte-als-moeglichkeit-353.md).
Product Owner, 6.11.2026: Alternativen kann jedes Ding sein, nur der Tag nicht. Ein gewählter Ort ist ein Ziel ohne
Rechenbedeutung (Entscheidung des Tech Leads): er steht am Tag, im Vergleich und auf der Karte; Anschluss, Anfang und Ende der
Tage und der Ort der Nacht ändern sich nicht. Testdaten: erfundene Abwandlungen der beiden Beispielreisen.

Die Abwandlungen ändern plan/routen.yaml und plan/arten.yaml als Daten (yaml laden, ändern, schreiben), nicht über Textanker:
so bleiben sie gültig, wenn die Beispielreise selbst eine Wahlstelle mit Orten bekommt (AC-14)."""
import copy
import datetime
import functools
import http.server
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import kalender  # noqa: E402
import karte  # noqa: E402
import konnektor as kn  # noqa: E402
import neu  # noqa: E402
import schreiben as sb  # noqa: E402
import texte  # noqa: E402
from conftest import meldet  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_schreiben import KARL, repo, routen_auf_main, schreiber  # noqa: E402,F401

REISEN = pathlib.Path(__file__).resolve().parents[2] / "beispiel" / "reisen"
HEUTE = datetime.date(2026, 11, 1)
B = "erfunden (Beispiel)"
WERT = lambda w: {"wert": w, "quelle": B, "geprueft": HEUTE}   # noqa: E731

# Erfundenes Merkmal der Art „Ort am Weg“ (Beispielwert): Pflicht, damit sich zeigt, wer es mahnt
EINKEHR = {"name": "Einkehr im Ort", "typ": "auswahl", "werte": ["ja", "nein", "unklar"], "stufe": "pflicht"}
# Erfundener Ort mit eigener Lage, der in keiner Strecke vorkommt (nur in einer Möglichkeit)
O90 = {"name": "Aussichtsturm am Hang (erfunden)", "quelle": B,
       "merkmale": {"koordinaten": {"typ": "koordinaten", "wert": [50.95, 14.20], "quelle": B, "geprueft": HEUTE}}}
O91 = {"name": "Unbenutzte Lichtung (erfunden)", "quelle": B,
       "merkmale": {"koordinaten": {"typ": "koordinaten", "wert": [50.96, 14.21], "quelle": B, "geprueft": HEUTE}}}


def option(oid, titel, **felder):
    return {"id": oid, "titel": titel, "quelle": B, **felder,
            "verlauf": felder.pop("verlauf", None) or [{"datum": HEUTE, "status": "vorgeschlagen", "wer": "Claude"}]}


def wahlstelle(vid, *optionen, wann="unterwegs", **felder):
    return vid, {"titel": f"{vid}: erfundenes Beispiel", "wann": wann, **felder, "optionen": list(optionen)}


def kopie(tmp, reise="beispielreise", wahl=(), tag="T-03", orte=None, aufenthalte=None, ort_merkmal=True,
          routen=None, arten=None, ohne_karte=False):
    """Beispielreise kopieren und als Daten abwandeln.
    wahl: Paare (V-…, Wahlstelle), an den Tag tag gehängt (wahl: am Tag); orte/aufenthalte: Einträge dazu oder ersetzen;
    ort_merkmal: Art ort_am_weg bekommt das Merkmal einkehr, Altendorf (O-04) den Wert ja;
    routen/arten: Funktionen, die die geladenen Daten weiter ändern; ohne_karte: automatische Karte (ohne plan/karte.yaml)."""
    q = tmp / "quelle"
    shutil.copytree(REISEN / reise, q)
    rp, ap = q / "plan" / "routen.yaml", q / "plan" / "arten.yaml"
    r = yaml.safe_load(rp.read_text(encoding="utf-8"))
    a = yaml.safe_load(ap.read_text(encoding="utf-8")) if ap.exists() else None
    for oid, o in (orte or {}).items():
        r["orte"][oid] = o
    for aid, x in (aufenthalte or {}).items():
        r["aufenthalte"][aid] = x
    if wahl:
        r.setdefault("wahlstellen", {})
        t = r["tage"][tag]
        for vid, w in wahl:
            r["wahlstellen"][vid] = w
            if not w.get("an") and vid not in (t.get("wahl") or []):
                t["wahl"] = list(t.get("wahl") or []) + [vid]
    if ort_merkmal and a and "ort_am_weg" in a["arten"]:
        a["arten"]["ort_am_weg"].setdefault("merkmale", {})["einkehr"] = EINKEHR
        r["orte"]["O-04"].setdefault("merkmale", {})["einkehr"] = WERT("ja")
    if routen:
        routen(r)
    if arten and a:
        arten(a)
    rp.write_text(yaml.safe_dump(r, allow_unicode=True, sort_keys=False), encoding="utf-8")
    if a is not None:
        ap.write_text(yaml.safe_dump(a, allow_unicode=True, sort_keys=False), encoding="utf-8")
    if ohne_karte:
        cfg = json.loads((q / "reise.json").read_text(encoding="utf-8"))
        (cfg.get("routen") or {}).pop("karte", None)
        (q / "reise.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        (q / "plan" / "karte.yaml").unlink(missing_ok=True)
    return q


def gebaut(tmp, **abwandlung):
    q = kopie(tmp, **abwandlung)
    return bauen.bauen(q, tmp / "web" / "b")


def wahl_von(d, vid):
    return next(x for x in d["route"]["wahlstellen"] if x["id"] == vid)


def warnungen_zu(d, *bezuege):
    return [w for w in d["route"].get("warnungen") or [] if w.get("bezug") in bezuege or any(b in str(w.get("text")) for b in bezuege)]


# Altendorf (Ort mit Art) oder Lichtenhainer Wasserfall (Ort ohne Art), am Nachmittag von Tag 3 (erfunden)
V91 = wahlstelle("V-91",
                 option("V-91.a", "Nachmittag in Altendorf (Beispiel)", orte=["O-04"]),
                 option("V-91.b", "Zum Lichtenhainer Wasserfall (Beispiel)", orte=["O-06"], plus=["kühl bei Hitze (Beispiel)"]))


def test_ort_als_option_wird_gelesen_und_verglichen(tmp_path):
    """AC-1: orte steht in der Ausgabe der Option, die Merkmale der Art des Orts stehen im Vergleich."""
    d = gebaut(tmp_path, wahl=[V91])
    w = wahl_von(d, "V-91")
    a, _ = w["optionen"]
    assert a.get("orte") == ["O-04"], a.keys()
    assert "einkehr" in {k["id"] for k in w["kriterien"]}, "Merkmal der Art „Ort am Weg“ steht im Vergleich"
    assert a["merkmale"]["einkehr"]["wert"] == "ja", "der Wert kommt vom Ort"


def test_ort_ohne_art_ist_erlaubt_und_vergleicht_nur_text(tmp_path):
    """AC-2: Ort ohne Art (O-06) ist erlaubt, ohne Fehler und Warnung; nur Text, Plus, Minus, keine Ortsmerkmale."""
    d = gebaut(tmp_path, wahl=[V91])
    _, b = wahl_von(d, "V-91")["optionen"]
    assert b.get("orte") == ["O-06"]
    assert "einkehr" not in b["merkmale"] and "einkehr" not in b["fehlt"], "ein Ort ohne Art hat keine Merkmale und mahnt keine"
    assert b["plus"] == ["kühl bei Hitze (Beispiel)"]
    assert not warnungen_zu(d, "V-91", "V-91.a", "V-91.b", "O-06")


def test_unbekannter_ort_in_option_ist_ein_fehler(tmp_path):
    """AC-3: orte: [O-99] ist genau ein Prüffehler option_ort mit Wahlstelle, Möglichkeit und Ort."""
    falsch = wahlstelle("V-91", option("V-91.a", "Nirgendwo (Beispiel)", orte=["O-99"]), option("V-91.b", "Wasserfall", orte=["O-06"]))
    with pytest.raises(bauen.BauFehler) as e:
        gebaut(tmp_path, wahl=[falsch])
    meldungen = e.value.args[0] if isinstance(e.value.args[0], (list, tuple)) else str(e.value.args[0]).splitlines()
    treffer = [m for m in meldungen if "O-99" in str(m)]
    assert len(treffer) == 1, meldungen
    assert meldet(treffer, "pruefung.routen.option_ort") and "V-91" in str(treffer[0]) and "V-91.a" in str(treffer[0])


@pytest.mark.parametrize("inhalt, gueltig", [
    ({"orte": ["O-04"]}, True),
    ({"orte": ["O-04"], "aufenthalte": ["A-01"]}, True),
    ({"orte": ["O-04"], "strecken": ["E-04"]}, True),
    ({"orte": ["O-04"], "aufenthalte": ["A-01"], "strecken": ["E-04"]}, True),
    ({"strecken": ["E-04"], "aufenthalte": ["A-01"]}, True),
    ({"unterkuenfte": ["U-02"]}, True),
    ({"folge": ["T-04"]}, True),
    ({"orte": ["O-04"], "unterkuenfte": ["U-02"]}, False),
    ({"orte": ["O-04"], "folge": ["T-04"]}, False),
    ({"unterkuenfte": ["U-02"], "strecken": ["E-04"]}, False),
    ({"unterkuenfte": ["U-02"], "aufenthalte": ["A-01"]}, False),
    ({"folge": ["T-04"], "strecken": ["E-04"]}, False),
])
def test_sortenregel_orte_mit_aufenthalten_und_strecken(inhalt, gueltig):
    """AC-4: orte allein oder mit aufenthalte und/oder strecken; unterkuenfte und folge nur allein."""
    neu_ = {k: inhalt.get(k, []) for k in ("unterkuenfte", "strecken", "folge", "aufenthalte", "orte")}
    assert sb.option_inhalt_ok(neu_) is gueltig


def test_schreibweg_nimmt_orte_in_optionen(repo):
    """AC-5: wahlstelle_anlegen, option_anlegen und option_aendern (setzen, ersetzen, leeren) schreiben orte als Liste von O-IDs."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "wahlstelle_anlegen", {**KARL, "args": {
        "titel": "Nachmittag: Ort oder Wasserfall (Beispiel)", "wann": "unterwegs", "an": ["T-03"],
        "optionen": [{"titel": "Altendorf (Beispiel)", "orte": ["O-04"], "quelle": B},
                     {"titel": "Wasserfall (Beispiel)", "orte": ["O-06"], "quelle": B}]}})
    assert a["ok"]
    r, text = routen_auf_main(origin)
    vid, w = next((k, v) for k, v in r["wahlstellen"].items() if v["titel"].startswith("Nachmittag: Ort oder Wasserfall"))
    assert [o.get("orte") for o in w["optionen"]] == [["O-04"], ["O-06"]]
    assert "orte: [O-04]" in text, "Listenwerte ohne Anführungszeichen, wie aufenthalte"
    s.vorbereiten()
    a = s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-02", "titel": "Rast in Hohnstein (Beispiel)",
                                                                         "orte": ["O-03"], "aufenthalte": ["A-01"], "quelle": B}})
    assert "V-02.c" in a["text"]
    o = lambda r: next(o for o in r["wahlstellen"]["V-02"]["optionen"] if o["id"] == "V-02.c")   # noqa: E731
    r, _ = routen_auf_main(origin)
    assert o(r)["orte"] == ["O-03"] and o(r)["aufenthalte"] == ["A-01"]
    vorher = len(o(r).get("verlauf") or [])
    s.vorbereiten()
    a = s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-02.c", "orte": ["O-06"]}})   # nur orte: eine Änderung
    assert a["ok"] and not meldet(a["text"], "schreiben.option_aendern.8")
    r, _ = routen_auf_main(origin)
    assert o(r)["orte"] == ["O-06"] and o(r)["aufenthalte"] == ["A-01"], "ersetzt, der Rest bleibt"
    assert len(o(r).get("verlauf") or []) >= vorher, "der Verlauf wird nicht überschrieben"
    s.vorbereiten()
    s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-02.c", "orte": []}})
    r, _ = routen_auf_main(origin)
    assert not o(r).get("orte") and o(r)["aufenthalte"] == ["A-01"], "geleert"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="O-77"):
        s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-02", "titel": "X", "orte": ["O-77"], "quelle": "x"}})
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-03.a", "orte": ["O-03"]}})   # Unterkunft und Ort
    assert e.value.schluessel == "schreiben.option_aendern.5"


def test_konnektor_schema_und_show_kennen_orte(tmp_path):
    """AC-6: OPTION_FELDER hat orte (Liste von Strings, Beschreibung aus dem Katalog); show nennt die Orte mit Namen."""
    f = kn.OPTION_FELDER.get("orte")
    assert f and f["type"] == "array" and f["items"]["type"] == "string"
    assert f["description"] == "@konnektor.feld.option_felder.orte"
    h = kn.Handbuch(gebaut(tmp_path, wahl=[V91]))
    t, fehler = h.zeige("V-91.b")
    assert not fehler and "Lichtenhainer Wasserfall" in t, t
    assert any(meldet(t, "konnektor.ausgabe.option_text.orte", sp) for sp in texte.SPRACHEN), t


A90 = {"name": "Burg Hohnstein (Beispiel)", "ort": "O-03", "art": "besichtigung", "quelle": B,
       "merkmale": {"geoeffnet": WERT("ja"), "eintritt": WERT("8 €")}}


def test_gemischter_vergleich_ort_und_aufenthalt(tmp_path):
    """AC-7: Ort (ort_am_weg) und Aufenthalt (besichtigung): der Vergleich hat die Merkmale beider Arten,
    jede Möglichkeit mahnt nur die Pflichtmerkmale ihrer eigenen Art."""
    v92 = wahlstelle("V-92", option("V-92.a", "Altendorf (Beispiel)", orte=["O-04"]),
                     option("V-92.b", "Burg (Beispiel)", aufenthalte=["A-90"]))
    d = gebaut(tmp_path, wahl=[v92], aufenthalte={"A-90": A90})
    w = wahl_von(d, "V-92")
    a, b = w["optionen"]
    assert a.get("orte") == ["O-04"]
    assert {"einkehr", "geoeffnet", "eintritt"} <= {k["id"] for k in w["kriterien"]}
    assert a["merkmale"]["einkehr"]["wert"] == "ja" and "eintritt" not in a["merkmale"]
    assert "geoeffnet" not in a["fehlt"], "der Ort braucht kein „Geöffnet am Reisedatum“ der Besichtigung"
    assert "einkehr" not in b["fehlt"] and b["merkmale"]["eintritt"]["wert"] == "8 €"


def test_art_der_wahlstelle_aus_erstem_ort_mit_art(tmp_path):
    """AC-8: ohne art: kommt die Art aus dem ersten Ort mit Art; haben alle Orte keine Art: allgemein, ohne Fehler."""
    v93 = wahlstelle("V-93", option("V-93.a", "Wasserfall (Beispiel)", orte=["O-06"]),
                     option("V-93.b", "Altendorf (Beispiel)", orte=["O-04"]))
    v94 = wahlstelle("V-94", option("V-94.a", "Wasserfall (Beispiel)", orte=["O-06"]),
                     option("V-94.b", "Turm (Beispiel)", orte=["O-90"]))
    d = gebaut(tmp_path, wahl=[v93, v94], orte={"O-90": O90})
    assert wahl_von(d, "V-93")["optionen"][1].get("orte") == ["O-04"]
    assert wahl_von(d, "V-93")["art"] == "ort_am_weg"
    assert wahl_von(d, "V-94")["art"] == "allgemein"


def test_ort_der_moeglichkeit_bekommt_punkt_auf_uebersicht(tmp_path):
    """AC-9: ein Ort nur in einer Möglichkeit am Tag hat einen Punkt; Stand plan für die aktive, alternative für die andere;
    ein Ort ohne Verwendung bleibt ohne Punkt (#335)."""
    v91 = wahlstelle("V-91", option("V-91.a", "Turm (Beispiel)", orte=["O-90"]),
                     option("V-91.b", "Wasserfall (Beispiel)", orte=["O-06"]))
    d = gebaut(tmp_path, wahl=[v91], orte={"O-90": O90, "O-91": O91}, ohne_karte=True)
    route = d["route"]
    opts = wahl_von(d, "V-91")["optionen"]
    aktiv = next(o for o in opts if o.get("aktiv"))
    andere = next(o for o in opts if not o.get("aktiv"))
    assert aktiv.get("orte") and andere.get("orte"), "orte fehlt in der Ausgabe der Optionen"
    stand, tage = karte.dinge_bezug(route)
    assert stand.get(aktiv["orte"][0]) == "plan" and "T-03" in tage.get(aktiv["orte"][0], [])
    if andere["orte"][0] == "O-90":
        assert stand.get("O-90") == "alternative"
    k = route["karte"]
    assert k["orte"]["O-90"].get("punkt") is not False, "Ort der Möglichkeit steht auf der Übersicht"
    assert k["orte"]["O-91"].get("punkt") is False, "Ort ohne Verwendung bleibt ohne Punkt"


def test_nacht_nur_mit_orten_warnt_und_aendert_nichts(tmp_path):
    """AC-10: nacht: V-…, deren Möglichkeiten nur orte haben: Warnung nacht_nur_orte, kein Fehler, Ort der Nacht None."""
    v95 = wahlstelle("V-95", option("V-95.a", "Altendorf (Beispiel)", orte=["O-04"]),
                     option("V-95.b", "Wasserfall (Beispiel)", orte=["O-06"]), wann="planung", an=["T-03"], frage="F-01")   # offene Planungswahl braucht eine Frage (pruefung.routen.97)

    def nacht(r):
        r["tage"]["T-03"]["nacht"] = "V-95"
    d = gebaut(tmp_path, wahl=[v95], routen=nacht)
    assert wahl_von(d, "V-95")["optionen"][0].get("orte") == ["O-04"]
    texte_ = [w["text"] for w in d["route"]["warnungen"]]
    assert meldet(texte_, "pruefung.routen.nacht_nur_orte"), texte_
    t3 = next(t for t in d["route"]["tage"] if t["id"] == "T-03")
    assert t3["nacht"]["ort"] is None and t3["nacht"]["wahl"] == "V-95"


def tageslauf(d):
    return [(t["id"], t.get("start_ort"), t.get("end_ort"), json.dumps(t.get("nacht"), sort_keys=True, default=str),
             json.dumps(t.get("anschluss"), sort_keys=True, default=str)) for t in d["route"]["tage"]]


def test_orte_in_option_aendern_nachtort_und_anschluss_nicht(tmp_path):
    """AC-11: mit und ohne orte: in einer Wahlstelle am Tag sind Anfang, Ende, Nacht und Anschluss aller Tage gleich."""
    mit = gebaut(tmp_path / "mit", wahl=[V91])
    _, w = V91
    ohne_orte = ("V-91", {**w, "optionen": [{k: v for k, v in o.items() if k != "orte"} for o in w["optionen"]]})
    ohne = gebaut(tmp_path / "ohne", wahl=[ohne_orte])
    assert wahl_von(mit, "V-91")["optionen"][0].get("orte") == ["O-04"]
    assert tageslauf(mit) == tageslauf(ohne)


def test_kalender_hat_keinen_eintrag_fuer_orte(tmp_path):
    """AC-12: ein Ort als entschiedene Möglichkeit bringt keinen Kalendereintrag; die übrigen Einträge bleiben gleich."""
    _, w = V91
    entschieden = copy.deepcopy(w)
    entschieden["optionen"][0]["verlauf"].append({"datum": HEUTE, "status": "gewaehlt", "wer": "Ida", "grund": "Test"})
    ohne_orte = copy.deepcopy(entschieden)
    for o in ohne_orte["optionen"]:
        o.pop("orte")
    mit = gebaut(tmp_path / "mit", wahl=[("V-91", entschieden)])
    ohne = gebaut(tmp_path / "ohne", wahl=[("V-91", ohne_orte)])
    assert wahl_von(mit, "V-91")["optionen"][0].get("orte") == ["O-04"]
    e_mit, e_ohne = kalender.eintraege(mit), kalender.eintraege(ohne)
    assert not [e for e in e_mit if str(e.get("id", "")).startswith("O-")]
    assert sorted(e["uid"] for e in e_mit) == sorted(e["uid"] for e in e_ohne)


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_seite_zeigt_ort_der_option(tmp_path, browser):
    """AC-13: die Option zeigt eine Ortszeile mit Namen und Link #O-… zur Ortsseite (optionBlock und optionEinzelheiten),
    der Vergleich die Merkmale des Orts mit Art, keine Seitenfehler."""
    gebaut(tmp_path, wahl=[V91])
    seiten = tmp_path / "web"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(seiten)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(pathlib.Path(__file__).parent / "seiten_option_ort.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/b/"],
                             capture_output=True, text=True, timeout=120, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert not e["fehler"], e["fehler"]
    assert e["wahl"] and "Nachmittag in Altendorf (Beispiel)" in e["wahl"] and "Einkehr im Ort" in e["wahl"], e["wahl"]
    assert "#O-04" in e["links_block"] and "#O-06" in e["links_block"], e["links_block"]
    assert "#O-04" in e["links_einzelheiten"] or "#O-06" in e["links_einzelheiten"], e["links_einzelheiten"]


def test_beispielreise_hat_wahlstelle_mit_orten(tmp_path):
    """AC-14: die Wanderung hat eine Wahlstelle mit zwei Orten (einer mit Art, O-06 ohne), als Beispiel markiert, an einem Tag;
    Summen der Reise und der Pläne sind unverändert."""
    d = bauen.bauen(REISEN / "beispielreise", tmp_path / "web" / "b")
    r = d["route"]
    mit_orten = [w for w in r["wahlstellen"] if any(o.get("orte") for o in w["optionen"])]
    assert mit_orten, "keine Wahlstelle mit Orten in der Beispielreise"
    w = mit_orten[0]
    orte = [x for o in w["optionen"] for x in o.get("orte") or []]
    assert "O-06" in orte and any(r["orte"][x].get("art") for x in orte if x != "O-06")
    assert "Beispiel" in w["titel"] and all("Beispiel" in (o.get("quelle") or "") for o in w["optionen"])
    assert any(w["id"] in (t.get("wahlstellen") or []) for t in r["tage"]), "die Wahlstelle hängt an einem Tag (wahl:)"
    s = r["summe"]
    assert (s["min"], s["km"], s["auf"], s["ab"]) == (595, 25.4, 1075, 1025)
    assert {p["id"]: p["summe"]["min"] for p in r["plaene"]} == {"P-A": 610, "P-B": 595}


def test_stadtwochenende_baut_unveraendert(tmp_path):
    """AC-15: das Stadtwochenende (keine Wahlstelle, Orte ohne Art) baut ohne Fehler und Warnung; eine erfundene Wahlstelle mit
    seinen Orten (ohne Art) baut ebenso, ohne Merkmale und ohne Warnung."""
    d = bauen.bauen(REISEN / "stadtwochenende", tmp_path / "web" / "a")
    assert d["route"].get("warnungen") == [] and not d["route"].get("wahlstellen")
    v90 = wahlstelle("V-90", option("V-90.a", "In Beispielstadt bleiben (Beispiel)", orte=["O-02"]),
                     option("V-90.b", "Zurück nach Heimatstadt (Beispiel)", orte=["O-01"]))
    d2 = gebaut(tmp_path / "zwei", reise="stadtwochenende", wahl=[v90], tag="T-02", ort_merkmal=False)
    a, b = wahl_von(d2, "V-90")["optionen"]
    assert a.get("orte") == ["O-02"] and b.get("orte") == ["O-01"]
    assert wahl_von(d2, "V-90")["art"] == "allgemein" and not a["merkmale"] and not b["fehlt"]
    assert d2["route"].get("warnungen") == []


def test_bestand_ohne_orte_bleibt_gleich(tmp_path):
    """AC-16: Optionen ohne orte: tragen orte als None (wie aufenthalte); die übrigen Felder sind gleich."""
    d = bauen.bauen(REISEN / "beispielreise", tmp_path / "web" / "b")
    for vid in ("V-01", "V-02", "V-03"):
        for o in wahl_von(d, vid)["optionen"]:
            assert "orte" in o and o["orte"] is None, (o["id"], o.keys())
    v03 = wahl_von(d, "V-03")["optionen"]
    assert [o["unterkuenfte"] for o in v03] == [["U-02"], ["U-03"]] and [o["aufenthalte"] for o in v03] == [None, None]


def test_arten_ableiten_kennt_orte_in_optionen(tmp_path):
    """AC-18: arten_ableiten nimmt die Art der Wahlstelle aus dem ersten Ort mit Art, wenn diese Art abgeleitet wird
    (erreichbar nur, wenn der Schlüssel auch an einem anderen Ding vorkommt, hier die Art pension einer Unterkunft);
    eine nicht abgeleitete Ortsart verdrängt die Art einer Unterkunft nicht; ein Ort ohne Art ergibt keine Art und keinen Fehler."""
    o92 = {"name": "Ort mit Pensionsart (erfunden)", "art": "pension", "quelle": B}
    v96 = wahlstelle("V-96", option("V-96.a", "Ort (Beispiel)", orte=["O-92"], merkmale={"ausblick": WERT("ja")}),
                     option("V-96.b", "Wasserfall (Beispiel)", orte=["O-06"]))
    v97 = wahlstelle("V-97", option("V-97.a", "Altendorf (Beispiel)", orte=["O-04"]),
                     option("V-97.b", "Gasthof (Beispiel)", unterkuenfte=["U-03"], merkmale={"hausschuhe": WERT("ja")}))
    v98 = wahlstelle("V-98", option("V-98.a", "Wasserfall (Beispiel)", orte=["O-06"], merkmale={"nur_text": WERT("ja")}))
    q = kopie(tmp_path, wahl=[v96, v97, v98], orte={"O-92": o92}, ort_merkmal=False)
    gasthof = yaml.safe_load(q.joinpath("plan/routen.yaml").read_text(encoding="utf-8"))["unterkuenfte"]["U-03"].get("art")
    a = yaml.safe_load(neu.arten_ableiten(q, schreiben=False))["arten"]
    assert "ausblick" in (a["pension"].get("merkmale") or {}), "Merkmal der Möglichkeit landet an der Art des ersten Orts mit Art"
    assert "hausschuhe" in (a[gasthof].get("merkmale") or {}), "die Art der Unterkunft bleibt die Art der Wahlstelle"
    assert "ort_am_weg" not in a and not any("nur_text" in (x.get("merkmale") or {}) for x in a.values())
