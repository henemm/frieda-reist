"""werkzeuge/punkte_holen.py und wissen_punkte_holen.py legen Dinge an statt plan/punkte.yaml zu schreiben (ADR-0007, Schritt d,
frieda-reist#297). Ohne Netz: Overpass und Nominatim sind durch erfundene Antworten ersetzt. Gegen die Beispielreise (Wanderung) und
gegen das Städtewochenende (ohne Tracks und ohne Punkte der Recherche: beide Werkzeuge sagen es und brechen sauber ab)."""
import datetime
import shutil
import sys
from pathlib import Path

import pytest
import yaml

WURZEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WURZEL / "werkzeuge"))
sys.path.insert(0, str(WURZEL / "engine"))
import bauen  # noqa: E402
import punkte_holen as ph  # noqa: E402
import wissen_punkte_holen as wph  # noqa: E402

HEUTE = datetime.date(2026, 11, 3)


def kopie(tmp_path, quelle="beispielreise"):
    ziel = tmp_path / "reisen" / quelle
    shutil.copytree(WURZEL / "beispiel/reisen" / quelle, ziel)
    return ziel


def dinge(reise):
    return yaml.safe_load((reise / "plan/routen.yaml").read_text(encoding="utf-8"))["aufenthalte"]


# ---------- punkte_holen ----------
def osm_antwort():
    """Erfundene Antwort von Overpass: zwei Trinkwasserstellen und eine Haltestelle entlang des Tracks von E-01 (50.9585, 14.0325 …)."""
    return {"osm3s": {"timestamp_osm_base": "2026-11-01T00:00:00Z"}, "elements": [
        {"type": "node", "id": 111, "lat": 50.96250, "lon": 14.07600, "tags": {"amenity": "drinking_water", "opening_hours": "24/7"}},
        {"type": "node", "id": 222, "lat": 50.96400, "lon": 14.08500, "tags": {"man_made": "water_tap", "drinking_water": "yes"}},
        {"type": "node", "id": 333, "lat": 50.95900, "lon": 14.03400, "tags": {"highway": "bus_stop", "name": "Wehlen Markt"}}]}


def test_punkte_holen_legt_dinge_an_und_aendert_nichts_beim_zweiten_lauf(tmp_path, monkeypatch, capsys):
    reise = kopie(tmp_path)
    monkeypatch.setattr(ph, "WURZEL", tmp_path)
    monkeypatch.setattr(ph, "abfrage", lambda rahmen: osm_antwort())
    vorher = set(dinge(reise))
    ph.main("beispielreise")
    aus = capsys.readouterr().out
    assert "new" in aus
    neu = {k: v for k, v in dinge(reise).items() if k not in vorher}
    assert neu, aus
    # Dinge statt Altform: keine Datei punkte.yaml, jedes Ding mit Art, an: <Strecke>, Quelle und Koordinaten
    assert not (reise / "plan/punkte.yaml").exists()
    for v in neu.values():
        assert v["an"].startswith("E-") and v["art"] in ("wasser", "notfall") and v["quelle"].startswith("OSM ")
        assert any(m.get("typ") == "koordinaten" for m in v["merkmale"].values())
    assert sorted(v["name"] for v in neu.values()) == ["Wasser", "Wasser", "Wehlen Markt"]   # ohne Namen in OSM: der Name der Art
    # Öffnungszeiten und OSM-Bezug stehen als Merkmale, der Bau nimmt alles an und führt die Punkte auf der Karte der Etappe
    d = bauen.bauen(reise, tmp_path / "web" / "x")
    assert any(p.get("offen") == "24/7" for p in d["route"]["punkte"]["E-01"])
    # zweiter Lauf: nichts wird verdoppelt
    ph.main("beispielreise")
    assert set(dinge(reise)) == vorher | set(neu)


def test_punkte_holen_nennt_arten_die_die_reise_nicht_kennt(tmp_path, monkeypatch, capsys):
    reise = kopie(tmp_path)
    a = yaml.safe_load((reise / "plan/arten.yaml").read_text(encoding="utf-8"))
    del a["arten"]["notfall"]
    (reise / "plan/arten.yaml").write_text(yaml.safe_dump(a, allow_unicode=True, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(ph, "WURZEL", tmp_path)
    monkeypatch.setattr(ph, "abfrage", lambda rahmen: osm_antwort())
    vorher = set(dinge(reise))
    ph.main("beispielreise")
    aus = capsys.readouterr().out
    assert "notfall" in aus and "kind_define" in aus
    assert all(v["art"] != "notfall" for k, v in dinge(reise).items() if k not in vorher)   # nichts wird in eine unbekannte Art gelegt


# ---------- wissen_punkte_holen ----------
def wissen_arbeitsliste(reise):
    """Die Arbeitsliste der Beispielreise: ein Punkt ohne Lage (wird gefunden), einer ohne Treffer, einer ohne Karte."""
    pfad = reise / "inhalt/wissen-punkte.yaml"
    d = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    block = next(v["an"] for v in dinge(reise).values() if str(v.get("an", "")).startswith("W-"))   # ein Abschnitt des Wissens mit Punkten
    d["gebiete"] = {"elbe": {"mitte": [50.96, 14.08], "radius_km": 20}}
    d["bloecke"] = {block: [
        {"name": "Gesuchter Ort", "kat": "sehenswert", "gebiet": "elbe", "suche": ["Gesuchter Ort"]},
        {"name": "Unauffindbar", "kat": "sehenswert", "gebiet": "elbe", "suche": ["Unauffindbar"]},
        {"name": "Ohne Karte", "kat": "sehenswert", "gebiet": "elbe", "ohne_karte": "nicht sicher verortet"}]}
    pfad.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return block, pfad


def test_wissen_punkte_holen_legt_gefundene_dinge_an_und_laesst_den_rest_in_der_liste(tmp_path, monkeypatch, capsys):
    reise = kopie(tmp_path)
    block, pfad = wissen_arbeitsliste(reise)
    monkeypatch.setattr(wph, "WURZEL", tmp_path)
    monkeypatch.setattr(wph, "suchen", lambda begriff, mitte, radius: (
        {"lat": "50.9700", "lon": "14.0900", "osm_type": "node", "osm_id": 4711, "display_name": "Gesuchter Ort, Test"} if begriff == "Gesuchter Ort" else None))
    vorher = set(dinge(reise))
    assert wph.main(["x", "beispielreise"]) == 0
    aus = capsys.readouterr().out
    neu = {k: v for k, v in dinge(reise).items() if k not in vorher}
    assert len(neu) == 1
    (aid, v), = neu.items()
    assert v["name"] == "Gesuchter Ort" and v["an"] == block and v["art"] == "sehenswert"
    k = next(m for m in v["merkmale"].values() if m.get("typ") == "koordinaten")
    assert k["wert"] == [50.97, 14.09] and "via Nominatim" in k["quelle"] and "node/4711" in k["quelle"] and k["geprueft"]
    # der Rest bleibt in der Liste (Unauffindbar mit Suchbegriffen, ohne_karte mit Grund), der gefundene ist heraus
    rest = yaml.safe_load(pfad.read_text(encoding="utf-8"))["bloecke"][block]
    assert [p["name"] for p in rest] == ["Unauffindbar", "Ohne Karte"] and rest[0]["suche"] == ["Unauffindbar"] and rest[1]["ohne_karte"]
    assert "Unauffindbar" in aus
    bauen.bauen(reise, tmp_path / "web" / "x")
    # zweiter Lauf: nichts Neues
    wph.main(["x", "beispielreise"])
    assert set(dinge(reise)) == vorher | {aid}


def test_wissen_punkte_holen_neu_sucht_nur_was_das_werkzeug_gesetzt_hat(tmp_path, monkeypatch):
    reise = kopie(tmp_path)
    block, pfad = wissen_arbeitsliste(reise)
    monkeypatch.setattr(wph, "WURZEL", tmp_path)
    treffer = {"Gesuchter Ort": {"lat": "50.9700", "lon": "14.0900", "osm_type": "node", "osm_id": 4711, "display_name": "x"}}
    monkeypatch.setattr(wph, "suchen", lambda b, m, r: treffer.get(b))
    wph.main(["x", "beispielreise"])
    # eine zweite Antwort für denselben Namen, dazu ein von Hand gesetztes Ding im Wissen (Quelle ohne „via Nominatim“)
    treffer["Gesuchter Ort"] = {"lat": "50.9800", "lon": "14.1000", "osm_type": "node", "osm_id": 4712, "display_name": "y"}
    wph.main(["x", "beispielreise", "--neu"])
    koordinaten = {v["name"]: next(m for m in v["merkmale"].values() if m.get("typ") == "koordinaten")
                   for v in dinge(reise).values() if str(v.get("an", "")).startswith("W-") and v.get("merkmale")}
    assert koordinaten["Gesuchter Ort"]["wert"] == [50.98, 14.1] and "node/4712" in koordinaten["Gesuchter Ort"]["quelle"]
    von_hand = [v for v in dinge(reise).values() if str(v.get("an", "")).startswith("W-") and v["name"] != "Gesuchter Ort" and v.get("merkmale")]
    assert von_hand and all("via Nominatim" not in next(m for m in v["merkmale"].values() if m.get("typ") == "koordinaten")["quelle"] for v in von_hand)


def test_werkzeuge_sagen_bei_einer_reise_ohne_tracks_und_ohne_wissenspunkte_was_fehlt(tmp_path, monkeypatch, capsys):
    kopie(tmp_path, "stadtwochenende")
    monkeypatch.setattr(ph, "WURZEL", tmp_path)
    monkeypatch.setattr(wph, "WURZEL", tmp_path)
    assert ph.main("stadtwochenende") == 1 and "map_points_fetch" in capsys.readouterr().err
    assert wph.main(["x", "stadtwochenende"]) == 1 and "wissen_punkte" in capsys.readouterr().out
