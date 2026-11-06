"""Eine Lage je Stelle und Karte als Regel (ADR-0008, Schritt b, frieda-reist #335): Ein Aufenthalt mit bezug auf einen Ort liegt beim
Ort; die Übersicht zeigt nur Orte des Plans; ein Ort mit Unterorten (Region) ist kein Punkt. Erfundene Testdaten der beiden
Beispielreisen."""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import karte  # noqa: E402
import routen  # noqa: E402
from conftest import meldet  # noqa: E402
from test_karte_auto import LAGEN, daten, mit_lagen, punkt, reise  # noqa: E402,F401

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"


def kopie(tmp_path, name="beispielreise"):
    q = tmp_path / name
    shutil.copytree(BEISPIELE / name, q)
    return q


def routen_aendern(r, fn):
    p = r / "plan" / "routen.yaml"
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    fn(d)
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_wegpunkt_mit_bezug_liegt_beim_ort(tmp_path):
    d = bauen.Bauer(kopie(tmp_path), tmp_path / "web").daten()["route"]
    ort = d["orte"]["O-03"]["punkt"]
    for aid in ("A-08", "A-10"):   # Hohnstein als Wegpunkt an E-01 und E-02, ohne eigene Koordinaten
        p = d["aufenthalte"][aid]["punkt"]
        assert p["wert"] == ort["wert"] and p["von"] == "O-03" and p["quelle"] == ort["quelle"]
    je_strecke, _ = routen.kartenpunkte_aus_dingen(d)
    hohnstein = [p for p in je_strecke["E-01"] if p["name"] == "Hohnstein"]
    assert hohnstein and hohnstein[0]["lage"] == ort["wert"] and hohnstein[0]["id"] == "O-03"


def test_eigene_koordinaten_gehen_vor(tmp_path):
    q = kopie(tmp_path)
    routen_aendern(q, lambda d: d["aufenthalte"]["A-08"]["merkmale"].update(
        koordinaten={"typ": "koordinaten", "wert": [50.98, 14.11], "quelle": "Test"}))
    d = bauen.Bauer(q, tmp_path / "web").daten()["route"]
    assert d["aufenthalte"]["A-08"]["punkt"]["wert"] == [50.98, 14.11] and "von" not in d["aufenthalte"]["A-08"]["punkt"]
    assert d["aufenthalte"]["A-10"]["punkt"]["von"] == "O-03"


def test_ort_ohne_eigene_lage_vererbt_die_lage_seiner_unterkunft():
    route = {"orte": {"O-1": {"name": "Dorf"}}, "eltern": {},
             "unterkuenfte": {"U-1": {"name": "Haus", "ort": "O-1", "punkt": punkt([3.0, 4.0])}},
             "aufenthalte": {"A-1": {"name": "Dorf", "art": "wp", "merkmale": {"st": {"wert": "O-1"}}}},
             "merkmale": {"wp": [{"id": "st", "rolle": "bezug"}]}}
    routen.lage_ueber_bezug(route)
    assert route["aufenthalte"]["A-1"]["punkt"]["wert"] == [3.0, 4.0]


def test_bezug_auf_unbekannten_ort(tmp_path):
    q = kopie(tmp_path)
    routen_aendern(q, lambda d: d["aufenthalte"]["A-08"]["merkmale"]["station"].update(wert="O-99"))
    with pytest.raises(bauen.BauFehler) as e:
        bauen.Bauer(q, tmp_path / "web").daten()
    assert meldet(e.value.args[0], "pruefung.routen.bezug_ort")


def test_uebersicht_nur_mit_orten_des_plans_und_ohne_region(reise, tmp_path):
    def aendere(d):
        mit_lagen(d)
        d["orte"]["O-07"] = {"name": "Sächsische Schweiz (Beispiel)", "quelle": "Test", "punkt": punkt([50.95, 14.15])}
        d["orte"]["O-08"] = {"name": "Pirna (ohne Verwendung, Beispiel)", "quelle": "Test", "punkt": punkt([50.96, 13.94])}
        for oid in ("O-02", "O-03", "O-04", "O-05", "O-06"):
            d["orte"][oid]["an"] = "O-07"
    routen_aendern(reise, aendere)
    d, _ = daten(reise, tmp_path)
    k, st = d["route"]["karte"], d["route"]["karte_status"]
    assert k["orte"]["O-07"]["punkt"] is False and k["orte"]["O-08"]["punkt"] is False
    assert all("punkt" not in k["orte"][oid] for oid in LAGEN)
    # Die Linien der Strecken bleiben, der Kartenstatus mahnt die Region und den unbenutzten Ort nicht an
    assert not {"Sächsische Schweiz (Beispiel)", "Pirna (ohne Verwendung, Beispiel)"} & set(st["ohne_lage"])


def test_region_ohne_punkt_ohne_lage_wird_nicht_angemahnt(reise, tmp_path):
    def aendere(d):
        mit_lagen(d)
        d["orte"]["O-07"] = {"name": "Region ohne Lage (Beispiel)", "quelle": "Test"}
        d["orte"]["O-02"]["an"] = "O-07"
    routen_aendern(reise, aendere)
    d, _ = daten(reise, tmp_path)
    assert "Region ohne Lage (Beispiel)" not in d["route"]["karte_status"]["ohne_lage"]


def test_stadtwochenende_heimatregion_ist_kein_punkt():
    route = {"orte": {"O-01": {"name": "Heimatstadt", "punkt": punkt([52.0, 7.6])},
                      "O-02": {"name": "Beispielstadt", "punkt": punkt([51.4, 6.8])},
                      "O-03": {"name": "Heimatregion", "punkt": punkt([51.7, 7.2])}},
             "eltern": {"O-01": "O-03", "O-02": "O-03"},
             "strecken": {"E-01": {"von": "O-01", "nach": "O-02"}, "E-02": {"von": "O-02", "nach": "O-01"}},
             "tage": [], "unterkuenfte": {}, "aufenthalte": {}}
    k, st = karte.auto(route)
    assert st["gebaut"] and st["punkte"] == 2
    assert k["orte"]["O-03"]["punkt"] is False and "punkt" not in k["orte"]["O-01"]
