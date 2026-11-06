"""Automatische Karte aus dem Plan (Epic #225): Karte ohne plan/karte.yaml, Kartenstatus, Legende aus der Art, Ansichten,
Aufenthalte ohne Tag, GPX an der Strecke, Grundkarte nach Fläche. Grundlage ist die erfundene Beispielreise."""
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import karte  # noqa: E402

BEISPIEL = Path(__file__).resolve().parents[2] / "beispiel" / "reisen" / "beispielreise"
# Koordinaten der Orte der Beispielreise (Beispielwerte, aus plan/karte.yaml übernommen)
LAGEN = {"O-01": [51.040, 13.732], "O-02": [50.9585, 14.0325], "O-03": [50.979, 14.1125], "O-04": [50.9275, 14.187],
         "O-05": [50.918, 14.155], "O-06": [50.9335, 14.234]}


def punkt(lage):
    return {"wert": lage, "quelle": "Beispielwert (Test)"}


@pytest.fixture
def reise(tmp_path):
    """Beispielreise ohne handgepflegte Karte (reise.json ohne routen.karte, ohne plan/karte.yaml)."""
    r = tmp_path / "beispielreise"
    shutil.copytree(BEISPIEL, r)
    cfg = json.loads((r / "reise.json").read_text(encoding="utf-8"))
    del cfg["routen"]["karte"]
    (r / "reise.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    (r / "plan" / "karte.yaml").unlink()
    return r


def routen(r, aendere):
    p = r / "plan" / "routen.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    aendere(d)
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")


def daten(r, tmp_path):
    b = bauen.Bauer(r, tmp_path / "dist")
    return b.daten(), b


def mit_lagen(d, orte=LAGEN):
    for oid, lage in orte.items():
        (d["orte"][oid].get("merkmale") or {}).pop("koordinaten", None)   # eigene Lage des Orts (ADR-0008) ersetzt der Test
        d["orte"][oid]["punkt"] = punkt(lage)


def test_ohne_karte_yaml_entsteht_die_karte_aus_den_orten(reise, tmp_path):
    routen(reise, mit_lagen)
    d, _ = daten(reise, tmp_path)
    k, st = d["route"]["karte"], d["route"]["karte_status"]
    assert k and k["auto"] and st["gebaut"] and st["art"] == "auto"
    assert set(k["orte"]) == set(LAGEN)
    r = k["rahmen"]
    assert all(r["sued"] < l[0] < r["nord"] and r["west"] < l[1] < r["ost"] for l in LAGEN.values())
    # Ohne GPX: schematische Linien zwischen den Orten, in der Legende „schematisch“
    assert k["wege"]["E-20"] == [LAGEN["O-01"], LAGEN["O-02"]] and "E-20" in k["schematisch"]
    # Unterkünfte und Aufenthalte ohne Koordinaten stehen mit Namen im Kartenstatus (K3)
    assert "Hotel am Elbufer" in st["ohne_lage"] and "Burg Hohnstein" in st["ohne_lage"]
    assert "Dresden" not in st["ohne_lage"]


def test_nur_ein_punkt_keine_karte_mit_grund(reise, tmp_path):
    routen(reise, lambda d: (d["orte"]["O-03"].pop("merkmale"), mit_lagen(d, {"O-01": LAGEN["O-01"]})))   # Hohnstein ohne eigene Lage
    d, _ = daten(reise, tmp_path)
    st = d["route"]["karte_status"]
    assert d["route"]["karte"] is None and not st["gebaut"] and st["grund"] == "zu_wenig_punkte" and st["punkte"] == 1


def test_ohne_baustein_karte_keine_automatische_karte(reise, tmp_path):
    routen(reise, mit_lagen)
    y = reise / "reise.yaml"
    y.write_text(y.read_text(encoding="utf-8").replace("bausteine: [varianten, karte,", "bausteine: [varianten,"), encoding="utf-8")
    d, _ = daten(reise, tmp_path)
    assert d["route"]["karte"] is None and d["route"]["karte_status"]["grund"] == "baustein_aus"


def test_fehlerhafte_kartendaten_lassen_den_bau_nicht_scheitern(tmp_path):
    r = tmp_path / "beispielreise"
    shutil.copytree(BEISPIEL, r)
    k = r / "plan" / "karte.yaml"
    k.write_text(k.read_text(encoding="utf-8").replace("  nord: 51.08\n", ""), encoding="utf-8")
    d, b = daten(r, tmp_path)
    st = d["route"]["karte_status"]
    assert d["route"]["karte"] is None and st["grund"] == "fehler" and any("rahmen" in m for m in st["meldungen"])
    assert any("rahmen" in str(h) for h in b.hinweise)
    assert d["abschnitte"]   # der Rest der Seite ist da


def test_handgepflegte_karte_bleibt_wie_sie_ist(tmp_path):
    d, _ = daten(BEISPIEL, tmp_path)
    k, st = d["route"]["karte"], d["route"]["karte_status"]
    assert st == {"gebaut": True, "art": "hand", "punkte": 8, "ohne_lage": []}
    assert "auto" not in k and "dinge" not in k and "schematisch" not in k and set(k["gpx"]) == {"E-01", "E-02", "E-03", "E-04"}


def test_unterkuenfte_und_aufenthalte_mit_lage_sind_punkte_mit_art_und_stand(reise, tmp_path):
    def aendere(d):
        mit_lagen(d)
        d["unterkuenfte"]["U-02"]["punkt"] = punkt([50.9792, 14.1128])   # gewählt (V-03.a)
        d["unterkuenfte"]["U-03"]["punkt"] = punkt([50.9700, 14.1000])   # verworfen: Alternative
        d["aufenthalte"]["A-01"]["punkt"] = punkt([50.9785, 14.1140])    # an Tag 2
        d["aufenthalte"]["A-02"] = {"name": "Wochenmarkt", "ort": "O-01", "art": "besichtigung", "quelle": "erfunden (Test)",
                                    "punkt": punkt([51.050, 13.740])}  # an keinem Tag
    routen(reise, aendere)
    d, _ = daten(reise, tmp_path)
    dinge = {x["id"]: x for x in d["route"]["karte"]["dinge"]}
    assert dinge["U-02"]["stand"] == "plan" and dinge["U-02"]["art"] == "pension" and "T-02" in dinge["U-02"]["tage"]
    assert dinge["U-03"]["stand"] == "alternative" and "T-02" in dinge["U-03"]["tage"]
    assert dinge["A-01"]["stand"] == "plan" and dinge["A-01"]["tage"] == ["T-02"]
    assert dinge["A-02"]["stand"] == "frei" and dinge["A-02"]["tage"] == []
    # Aufenthalt ohne Tag (K7): erlaubt, als solcher markiert (Heimat: Reiter mit der Karte)
    assert d["route"]["aufenthalte"]["A-02"]["ohne_tag"] and not d["route"]["aufenthalte"]["A-01"]["ohne_tag"]
    # Legende aus der Art (K4): Name und Farbe der Reise
    leg = d["route"]["karte"]["legende"]
    assert (leg["pension"]["name"], leg["pension"]["farbe"]) == ("Pension", "braun") and leg["gasthof"]["farbe"] == "braun"
    assert leg["besichtigung"] == {"name": "Besichtigung", "farbe": "lila", "symbol": "museum"}


def test_kategorie_ueberschreibt_farbe_und_name_einer_art(reise, tmp_path):
    def aendere(d):
        mit_lagen(d)
        d["unterkuenfte"]["U-02"]["punkt"] = punkt([50.9792, 14.1128])
    routen(reise, aendere)
    # alte Form (plan/kategorien.yaml) wird weiter gelesen; eine Art gleichen Schlüssels mit gruppe (neue Form) gilt zuerst
    k = reise / "plan" / "kategorien.yaml"
    k.write_text("kategorien:\n  pension:\n    gruppe: punkt\n    name: Kleine Häuser\n    farbe: rosa\n", encoding="utf-8")
    d, _ = daten(reise, tmp_path)
    leg = d["route"]["karte"]["legende"]["pension"]
    assert (leg["name"], leg["farbe"]) == ("Kleine Häuser", "rosa")


def test_aufenthalte_des_tags_liegen_auf_der_schematischen_linie(reise, tmp_path):
    def aendere(d):
        mit_lagen(d)
        d["aufenthalte"]["A-01"]["punkt"] = punkt([50.97, 14.09])
        d["tage"]["T-03"]["aufenthalte"] = ["A-01"]   # Tag mit genau einer Strecke (E-02)
        d["tage"]["T-02"]["aufenthalte"] = []
    routen(reise, aendere)
    d, _ = daten(reise, tmp_path)
    assert d["route"]["karte"]["wege"]["E-02"] == [LAGEN["O-03"], [50.97, 14.09], LAGEN["O-04"]]


def test_gpx_an_der_strecke_ersetzt_die_schematische_linie_und_bringt_wegpunkte(reise, tmp_path):
    (reise / "medien" / "gpx" / "fahrt.gpx").write_text(
        '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">'
        '<wpt lat="50.99" lon="13.9"><name>Pillnitz</name></wpt><wpt lat="50.97" lon="13.95"></wpt>'
        '<trk><trkseg><trkpt lat="51.04" lon="13.732"/><trkpt lat="50.99" lon="13.9"/><trkpt lat="50.9585" lon="14.0325"/></trkseg></trk></gpx>',
        encoding="utf-8")
    def aendere(d):
        mit_lagen(d)
        d["strecken"]["E-20"]["gpx"] = "medien/gpx/fahrt.gpx"
    routen(reise, aendere)
    d, _ = daten(reise, tmp_path)
    k = d["route"]["karte"]
    assert k["wege"]["E-20"] == [[51.04, 13.732], [50.99, 13.9], [50.9585, 14.0325]] and "E-20" not in k["schematisch"]
    p = d["route"]["punkte"]["E-20"]
    assert p == [{"name": "Pillnitz", "nr": 1, "lage": [50.99, 13.9], "quelle": "GPX fahrt.gpx", "gpx": True}]


def test_gpx_pfad_ausserhalb_von_medien_wird_abgelehnt(reise, tmp_path):
    routen(reise, lambda d: d["strecken"]["E-20"].update(gpx="../geheim.gpx"))
    with pytest.raises(bauen.BauFehler) as e:
        daten(reise, tmp_path)
    assert any("E-20" in m and "gpx" in m for m in e.value.meldungen)


def test_kartenansichten_werden_geprueft_und_ausgegeben(reise, tmp_path):
    def aendere(d):
        mit_lagen(d)
        d["karten_ansichten"] = [{"titel": "Anfahrt", "tage": ["T-02"], "arten": ["pension", "gasthof"]},
                                 {"titel": "Vor Ort", "arten": ["besichtigung"]}]
    routen(reise, aendere)
    d, _ = daten(reise, tmp_path)
    assert d["route"]["karten_ansichten"] == [
        {"titel": "Anfahrt", "tage": ["T-02"], "strecken": [], "arten": ["pension", "gasthof"]},
        {"titel": "Vor Ort", "tage": [], "strecken": [], "arten": ["besichtigung"]}]
    routen(reise, lambda d: d["karten_ansichten"].append({"titel": "Falsch", "tage": ["T-99"]}))
    with pytest.raises(bauen.BauFehler) as e:
        daten(reise, tmp_path)
    assert any("T-99" in m for m in e.value.meldungen)


def test_ort_mit_adresse_wird_abgelehnt(reise, tmp_path):
    routen(reise, lambda d: d["orte"]["O-01"].update(adresse={"wert": "Markt 1", "quelle": "Test"}))
    with pytest.raises(bauen.BauFehler) as e:
        daten(reise, tmp_path)
    assert any("O-01" in m and "Adresse" in m for m in e.value.meldungen)


def test_ort_ohne_eigenen_punkt_liegt_bei_seiner_unterkunft():
    route = {"orte": {"O-1": {"name": "A"}, "O-2": {"name": "B", "punkt": punkt([1.0, 2.0])}},
             "unterkuenfte": {"U-1": {"name": "Haus", "ort": "O-1", "punkt": punkt([3.0, 4.0])}}, "aufenthalte": {}}
    assert karte.ort_lagen(route) == {"O-1": [3.0, 4.0], "O-2": [1.0, 2.0]}


def test_zoom_nach_flaeche_kompakt_und_lange_fahrt():
    kompakt = karte.rahmen_aus([[50.92, 14.03], [50.98, 14.23]])
    assert karte.zoom_fuer(kompakt) == 15 and karte.grundkarten_plan(kompakt, [])["details"] == []
    # Lange Fahrt (Hamburg – München, erfundene Stationen): gröbere Übersicht, Detailkarten der Gebiete in Zoom 15
    punkte = [[53.55, 9.99], [53.56, 10.01], [50.11, 8.68], [48.14, 11.58], [48.15, 11.57]]
    lang = karte.rahmen_aus(punkte)
    plan = karte.grundkarten_plan(lang, punkte)
    assert plan["zoom"] < 12 and len(plan["details"]) == 3 and all(d["zoom"] == 15 for d in plan["details"])
    assert all(karte.kacheln(d["rahmen"], d["zoom"]) <= karte.KACHELN_MAX for d in plan["details"])


def test_grundkarte_wird_nur_bei_neuem_rahmen_geholt(reise, tmp_path):
    """#239: Die Grundkarte entsteht beim Veröffentlichen, wenn sich der Rahmen geändert hat; sonst bleibt die vorhandene.
    Ohne Netz (Holen scheitert) endet das Skript mit 1, die Seite wird trotzdem gebaut."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "werkzeuge"))
    import grundkarte_auto
    routen(reise, mit_lagen)
    geholt = []
    def holen(reise_dir, name, rahmen, zoom):
        geholt.append((name, zoom))
        (reise_dir / "medien" / "karte").mkdir(parents=True, exist_ok=True)
        (reise_dir / "medien" / "karte" / f"{name}.pmtiles").write_bytes(b"PMTiles")
        return True
    assert grundkarte_auto.main(reise, holen) == 0 and geholt == [("grundkarte", 15)]
    assert grundkarte_auto.main(reise, holen) == 0 and len(geholt) == 1          # unverändert: nichts geholt
    routen(reise, lambda d: d["orte"]["O-06"].update(punkt=punkt([51.30, 14.50])))
    assert grundkarte_auto.main(reise, lambda *a: False) == 1                     # ohne Netz: Hinweis, kein Abbruch
    d, b = daten(reise, tmp_path)
    assert d["route"]["karte"]["grundkarte"]["url"] == "grundkarte.pmtiles" and b.grundkarte.name == "grundkarte.pmtiles"
    # Handgepflegte Karte: nichts zu holen
    assert grundkarte_auto.main(BEISPIEL, holen) == 0 and len(geholt) == 1
