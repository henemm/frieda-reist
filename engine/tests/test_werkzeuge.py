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
