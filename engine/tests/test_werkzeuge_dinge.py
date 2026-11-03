"""werkzeuge/adressen_holen.py und wasser_pruefen.py lesen kartenpunkte als Dinge (ADR-0007, Schritt d, frieda-reist#304) und weiter die
Altform plan/punkte.yaml, solange es sie gibt. Ohne Netz: Nominatim und Overpass sind durch erfundene Antworten ersetzt. Gegen die
Beispielreise (Wanderung) und das Städtewochenende (ohne Punkte). Gelesen wird nach Rolle, nie nach dem Namen der Art."""
import datetime
import shutil
import sys
from pathlib import Path

import pytest
import yaml

WURZEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WURZEL / "werkzeuge"))
sys.path.insert(0, str(WURZEL / "engine"))
import adressen_holen as ah  # noqa: E402
import punkte_holen as ph  # noqa: E402
import schreiben  # noqa: E402
import wasser_pruefen as wp  # noqa: E402

HEUTE = datetime.date(2026, 11, 3)
WER = {"name": "Test"}


def kopie(tmp_path, quelle="beispielreise"):
    ziel = tmp_path / "reisen" / quelle
    shutil.copytree(WURZEL / "beispiel/reisen" / quelle, ziel)
    return ziel


def punkt(kat, name, lage, **felder):
    return {"kat": kat, "name": name, "lage": lage, "quelle": "erfunden (Beispielwert)", **felder}


def mit_dingen(reise):
    """Dinge an E-01: zwei Wasserpunkte (Sorten trinkwasser und quelle), einer ohne OSM-Bezug, eine Einkehr mit OSM-Bezug und die
    Unterkunft U-02 mit OSM-Bezug und ihrer ID (Rolle bezug)."""
    return schreiben.kartenpunkte_ablegen(reise, WER, "E-01", [
        punkt("wasser", "Quelle A", [50.9618, 14.0938], osm="node/111", art="trinkwasser"),
        punkt("wasser", "Quelle B", [50.9640, 14.0850], osm="node/222", art="quelle"),
        punkt("wasser", "Quelle C", [50.9650, 14.0860], art="quelle"),
        punkt("einkehr", "Gasthof", [50.9600, 14.0400], osm="node/333", art="restaurant"),
        punkt("unterkunft", "Pension Burgblick", [50.9792, 14.1128], osm="way/11", id="U-02", art="guest_house")], heute=HEUTE)


def test_kartenpunkte_lesen_nach_rolle(tmp_path):
    reise = kopie(tmp_path)
    mit_dingen(reise)
    gelesen = {p["name"]: p for p in schreiben.kartenpunkte_lesen(reise)}
    assert gelesen["Quelle A"]["osm"] == "node/111" and gelesen["Quelle A"]["sorte"] == "trinkwasser" and gelesen["Quelle A"]["an"] == "E-01"
    assert gelesen["Quelle A"]["lage"] == [50.9618, 14.0938] and gelesen["Quelle A"]["gruppe"] == "punkt"
    assert gelesen["Quelle C"]["osm"] is None
    assert [p["bezug"] for p in gelesen.values() if p["bezug"] and p["osm"]] == ["U-02"]
    # kein Ding ohne Art mit gruppe und ohne Elternbezug: die Besichtigung A-01 hängt an keiner Strecke und hat keine Gruppe
    assert "Burg Hohnstein" not in gelesen


# ---------- wasser_pruefen ----------
def test_wasserpunkte_nach_sorte_und_rolle_nicht_nach_dem_namen_der_art(tmp_path):
    reise = kopie(tmp_path)
    mit_dingen(reise)
    pw = wp.wasserpunkte(schreiben.kartenpunkte_lesen(reise))
    assert sorted(p["osm"] for p in pw) == ["node/111", "node/222"]      # nicht die Einkehr, nicht die Quelle C ohne OSM-Bezug
    assert wp.osm_ids(pw) == {"node": [111, 222]}
    # eine Reise, deren Art anders heißt, wird genauso gelesen: der Schlüssel der Art zählt nicht
    a = yaml.safe_load((reise / "plan/arten.yaml").read_text(encoding="utf-8"))
    a["arten"]["trinkstelle"] = a["arten"].pop("wasser")
    (reise / "plan/arten.yaml").write_text(yaml.safe_dump(a, allow_unicode=True, sort_keys=False), encoding="utf-8")
    r = yaml.safe_load((reise / "plan/routen.yaml").read_text(encoding="utf-8"))
    for d in r["aufenthalte"].values():
        if d.get("art") == "wasser":
            d["art"] = "trinkstelle"
    (reise / "plan/routen.yaml").write_text(yaml.safe_dump(r, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert sorted(p["osm"] for p in wp.wasserpunkte(schreiben.kartenpunkte_lesen(reise))) == ["node/111", "node/222"]


def test_wasserpunkte_liest_die_altform_mit_und_zaehlt_doppelte_einmal():
    alt = {"strecken": {"E-02": [{"name": "Alt", "kat": "wasser", "art": "quelle", "lage": [1.0, 2.0], "quelle": "OSM node/222, Stand x"},
                                  {"name": "Alt2", "kat": "wasser", "art": "quelle", "lage": [1.0, 2.0], "quelle": "OSM way/9, Stand x"},
                                  {"name": "Café", "kat": "einkehr", "lage": [1.0, 2.0], "quelle": "OSM node/5, Stand x"}]}}
    dinge = [{"gruppe": "punkt", "osm": "node/222", "sorte": "quelle", "an": "E-01", "lage": [3.0, 4.0], "name": "Neu", "art": "wasser"}]
    pw = wp.wasserpunkte(dinge, alt)
    assert [(p["osm"], p["etappe"]) for p in pw] == [("node/222", "E-01"), ("way/9", "E-02")]


def test_wasser_pruefen_main_mit_dingen_schreibt_den_bericht(tmp_path, monkeypatch, capsys):
    reise = kopie(tmp_path)
    mit_dingen(reise)
    monkeypatch.setattr(wp, "WURZEL", tmp_path)
    gefragt = []

    def antwort(ids):
        gefragt.append(ids)
        return {"elements": [{"type": "node", "id": 111, "timestamp": "2026-05-01T00:00:00Z",
                              "tags": {"amenity": "drinking_water", "check_date": "2026-06-01"}}]}   # 222 gibt es in OSM nicht mehr
    monkeypatch.setattr(wp, "abfragen", antwort)
    wp.main("beispielreise")
    assert gefragt == [{"node": [111, 222]}]
    text = (reise / "inhalt/recherche/wasserstellen-osm.md").read_text(encoding="utf-8")
    assert "Quelle A" in text and "well documented" in text and "node/222" in text and "nicht mehr vorhanden" in text
    assert "Gasthof" not in text
    assert "1 well documented" in capsys.readouterr().out


def test_wasser_pruefen_ohne_wasserpunkte_sagt_es(tmp_path, monkeypatch):
    kopie(tmp_path, "stadtwochenende")
    monkeypatch.setattr(wp, "WURZEL", tmp_path)
    with pytest.raises(SystemExit) as e:
        wp.main("stadtwochenende")
    assert "No OSM water points" in str(e.value)


def test_wasser_sorten_decken_alles_ab_was_punkte_holen_fuer_wasser_vergibt():
    tags = [{"amenity": "drinking_water"}, {"man_made": "water_tap", "drinking_water": "yes"}, {"natural": "spring"},
            {"amenity": "fountain"}, {"man_made": "water_well"}]
    arten = {ph.einordnen(t) for t in tags}
    assert {k for k, _ in arten} == {"wasser"} and {a for _, a in arten} <= set(wp.WASSER_SORTEN)


# ---------- adressen_holen ----------
def test_osm_bezuege_aus_dingen_und_altform():
    dinge = [{"bezug": "U-1", "osm": "way/11", "lage": [50.0, 14.0], "quelle": "x"},
             {"bezug": "U-2", "osm": None, "quelle": "OSM node/22, Stand 2026-11-03", "lage": None},   # Bezug nur in der Quelle der Koordinaten
             {"bezug": None, "osm": "node/5", "quelle": "x"},                                           # kein Bezug zu einer Unterkunft
             {"bezug": "U-4", "osm": None, "quelle": "von Hand"}]                                      # kein OSM-Objekt
    alt = {"strecken": {"E-1": [{"id": "U-1", "quelle": "OSM way/99, Stand x"}, {"id": "U-3", "quelle": "OSM node/33, Stand x"}]}}
    assert ah.osm_bezuege(alt, dinge) == {"U-1": ("way", 11, [50.0, 14.0]), "U-2": ("node", 22, None), "U-3": ("node", 33, None)}


def test_adressen_holen_main_liest_den_osm_bezug_aus_dem_ding(tmp_path, monkeypatch, capsys):
    reise = kopie(tmp_path)
    mit_dingen(reise)
    monkeypatch.setattr(ah.instanz, "wurzel", lambda: tmp_path)

    def abfragen(url, daten=None):
        assert url.startswith(ah.NACHSCHLAGEN) and "osm_ids=W11&" in url
        return [{"osm_type": "way", "osm_id": 11, "address": {"road": "Burgstraße", "house_number": "3", "postcode": "01848", "town": "Hohnstein"}}]
    monkeypatch.setattr(ah, "holen", abfragen)
    roh = schreiben.routen_laden(reise)
    karte = {}
    neu, fehlt = ah.vorschlaege(roh, {}, karte, heute=HEUTE, abfragen=abfragen, dinge=schreiben.kartenpunkte_lesen(reise))
    assert neu["U-02"]["adresse"]["wert"] == "Burgstraße 3, 01848 Hohnstein" and neu["U-02"]["adresse"]["quelle"] == "OSM way/11, Stand 2026-11-03"
    assert "U-02" not in [f[0] for f in fehlt]
    # ohne das Ding bleibt die Unterkunft in der Liste, ohne Absturz
    ohne = kopie(tmp_path / "x")
    neu, fehlt = ah.vorschlaege(schreiben.routen_laden(ohne), {}, karte, heute=HEUTE, abfragen=abfragen, dinge=schreiben.kartenpunkte_lesen(ohne))
    assert "U-02" not in neu and "U-02" in [f[0] for f in fehlt]
    # der Lauf von der Kommandozeile schreibt die Adresse als Merkmal in die Unterkunft
    assert ah.main(["x", "beispielreise"]) == 0
    u = yaml.safe_load((reise / "plan/routen.yaml").read_text(encoding="utf-8"))["unterkuenfte"]["U-02"]
    assert any(m.get("typ") == "adresse" and m["wert"] == "Burgstraße 3, 01848 Hohnstein" for m in u["merkmale"].values())
    assert "U-02" in capsys.readouterr().out


def test_adressen_holen_staedtewochenende_ohne_punkte(tmp_path):
    reise = kopie(tmp_path, "stadtwochenende")
    assert schreiben.kartenpunkte_lesen(reise) == []
    neu, fehlt = ah.vorschlaege(schreiben.routen_laden(reise), {}, {}, heute=HEUTE, abfragen=lambda *a, **k: [], dinge=[])
    assert neu == {}
