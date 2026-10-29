"""Tests für werkzeuge/wasser_pruefen.py: Einstufung der OSM-Wasserpunkte nach Datenlage (ohne Netz)."""
import datetime
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WURZEL / "werkzeuge"))
import wasser_pruefen as wp  # noqa: E402

HEUTE = datetime.date(2026, 10, 26)


def stufe(tags):
    return wp.bewerte(tags, HEUTE)[0]


def test_trinkwasser_mit_frischem_pruefdatum_ist_gut_belegt():
    assert stufe({"amenity": "drinking_water", "check_date": "2025-06-01"}) == "gut belegt"


def test_trinkwasser_ohne_pruefdatum_hat_vorbehalt():
    assert stufe({"amenity": "drinking_water"}) == "mit Vorbehalt"


def test_altes_pruefdatum_hat_vorbehalt():
    assert stufe({"amenity": "drinking_water", "survey:date": "2019-04"}) == "mit Vorbehalt"


def test_quelle_ohne_trinkbarkeit_ist_unsicher():
    assert stufe({"natural": "spring", "check_date": "2026-01-01"}) == "unsicher"


def test_saisonal_und_zeitweise_sind_unsicher():
    assert stufe({"amenity": "drinking_water", "seasonal": "summer", "check_date": "2026-01-01"}) == "unsicher"
    assert stufe({"amenity": "drinking_water", "intermittent": "yes", "check_date": "2026-01-01"}) == "unsicher"


def test_kein_trinkwasser_und_eingeschraenkter_zugang_sind_unsicher():
    assert stufe({"natural": "spring", "drinking_water": "no"}) == "unsicher"
    assert stufe({"amenity": "drinking_water", "access": "customers"}) == "unsicher"


def test_warnhinweis_im_notiztext_wird_erkannt():
    s, gruende = wp.bewerte({"amenity": "drinking_water", "note": "fuente seca en verano"}, HEUTE)
    assert s == "unsicher" and any("seca" in g for g in gruende)


def test_pruefdatum_nimmt_jüngstes_und_teilweise_daten():
    assert wp.pruefdatum({"check_date": "2024", "survey:date": "2025-03"}) == datetime.date(2025, 3, 1)
    assert wp.pruefdatum({"check_date": "kürzlich"}) is None


def test_osm_ids_nur_wasserpunkte_mit_osm_quelle():
    punkte = [{"kat": "wasser", "quelle": "OSM node/12, Stand 2026-10-25"},
              {"kat": "wasser", "quelle": "Ida, 2026-10-01"},
              {"kat": "einkehr", "quelle": "OSM node/99, Stand 2026-10-25"},
              {"kat": "wasser", "quelle": "OSM way/7, Stand 2026-10-25"}]
    assert wp.osm_ids(punkte) == {"node": [12], "way": [7]}


def test_werkzeuge_ohne_werte_einer_instanz():
    """Kennung und Ordner kommen aus engine/instanz.py; kein Name, keine Adresse einer echten Installation."""
    import re
    for p in (WURZEL / "werkzeuge").iterdir():
        if p.suffix in (".py", ".sh"):
            text = p.read_text(encoding="utf-8")
            assert "ops/" not in text and not re.search(r"/home/\w+|/srv/\w+|private Reiseplanung", text), p.name


def test_werkzeuge_finden_die_wurzel_des_reisen_repos(tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv("FR_WURZEL", str(tmp_path))
    monkeypatch.setenv("FR_KENNUNG", "Probe/1 (ida@example.org)")
    for name in ("punkte_holen", "wissen_punkte_holen"):
        m = importlib.reload(importlib.import_module(name))
        assert m.WURZEL == tmp_path and m.KENNUNG == "Probe/1 (ida@example.org)"
    m = importlib.reload(wp)
    assert m.WURZEL == tmp_path


# ---------- werkzeuge/adressen_holen.py: Lage der Unterkünfte aus OSM (ADR-0004), ohne Netz ----------
import adressen_holen as ah  # noqa: E402


def test_adresse_aus_osm_tags():
    assert ah.adresse_aus({"addr:street": "Carrer de sa Lluna", "addr:housenumber": "21", "addr:postcode": "07100",
                           "addr:city": "Sóller"}) == "Carrer de sa Lluna 21, 07100 Sóller"
    assert ah.adresse_aus({"addr:place": "Biniaraix", "addr:postcode": "07100"}) == "Biniaraix, 07100"
    assert ah.adresse_aus({"addr:city": "Sóller"}) is None   # ohne Straße keine Adresse


def test_vorschlaege_aus_osm_bezug_und_suche():
    """Erfundene Testdaten: U-1 mit OSM-Punkt (Overpass liefert eine Adresse), U-2 ohne Punkt (Nominatim findet ein Hotel),
    U-3 hat schon eine Adresse, U-4 findet nichts."""
    roh = {"orte": {"O-1": {"name": "Musterort"}},
           "unterkuenfte": {"U-1": {"name": "Haus A", "ort": "O-1"}, "U-2": {"name": "Haus B", "ort": "O-1"},
                            "U-3": {"name": "Haus C", "ort": "O-1", "adresse": {"wert": "x", "quelle": "y"}},
                            "U-4": {"name": "Haus D", "ort": "O-1"}}}
    punkte = {"strecken": {"E-1": [{"name": "Haus A", "id": "U-1", "lage": [50.0, 14.0], "quelle": "OSM way/11, Stand 2026-10-25"}]}}
    karte = {"orte": {"O-1": {"lage": [50.0, 14.0]}}}

    def abfragen(url, daten=None):
        if url == ah.OVERPASS:
            assert "way(id:11);" in daten["data"]
            return {"elements": [{"type": "way", "id": 11, "tags": {"addr:street": "Hauptstraße", "addr:housenumber": "1",
                                                                     "addr:postcode": "12345", "addr:city": "Musterort"}}]}
        if "Haus+B" in url:
            return [{"category": "amenity", "type": "restaurant"},
                    {"category": "tourism", "type": "hotel", "osm_type": "node", "osm_id": 22, "lat": "50.001", "lon": "14.002",
                     "address": {"road": "Nebenweg", "house_number": "2", "postcode": "12345", "village": "Musterort"}}]
        return []
    heute = datetime.date(2026, 10, 29)
    neu, fehlt = ah.vorschlaege(roh, punkte, karte, suchen=True, heute=heute, abfragen=abfragen)
    assert neu["U-1"] == {"adresse": {"wert": "Hauptstraße 1, 12345 Musterort", "quelle": "OSM way/11, Stand 2026-10-29", "geprueft": heute}}
    assert neu["U-2"]["adresse"]["wert"] == "Nebenweg 2, 12345 Musterort" and neu["U-2"]["punkt"]["wert"] == [50.001, 14.002]
    assert "U-3" not in neu and [f[0] for f in fehlt] == ["U-4"]
    # ohne --suchen: nur der OSM-Bezug, der Rest steht in der Liste
    neu, fehlt = ah.vorschlaege(roh, punkte, karte, suchen=False, heute=heute, abfragen=abfragen)
    assert list(neu) == ["U-1"] and [f[0] for f in fehlt] == ["U-2", "U-4"]
