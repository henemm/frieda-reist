#!/usr/bin/env python3
"""Lage der Unterkünfte aus OpenStreetMap vorfüllen (ADR-0004): Adresse und Koordinaten mit Quelle und Prüfdatum.

Für jede Unterkunft in plan/routen.yaml ohne Adresse:
  1. Hat plan/punkte.yaml einen Punkt mit ihrer ID (id: U-…) und einem OSM-Objekt als Quelle („OSM way/123“), schlägt
     Nominatim dieses Objekt nach (/lookup); aus Straße (oder Platz), Hausnummer, Postleitzahl und Ort wird die Adresse.
  2. Sonst (nur mit --suchen) fragt das Skript Nominatim nach „Name, Ort“, begrenzt auf 3 km um den Ort aus plan/karte.yaml.
     Übernommen wird nur ein Treffer, der eine Unterkunft ist (tourism=hotel, guest_house, hostel, alpine_hut, apartment …)
     und eine Straße hat; dann auch die Koordinaten, wenn die Unterkunft noch keine hat.
Was nichts liefert, bleibt ohne Adresse und wird am Ende aufgelistet: keine geschätzten Adressen. Vorhandene Adressen bleiben.
Das Ergebnis ist ein Vorschlag mit Quelle; die Datei durchsehen, dann einchecken (Rest im Gespräch mit Frieda: lage_eintragen).

Aufruf (in der Wurzel des Reisen-Repos):
  engine/.venv/bin/python frieda/werkzeuge/adressen_holen.py <reise> [--suchen] [--trocken]
  --suchen  zusätzlich Nominatim-Suche nach Name und Ort für Unterkünfte ohne OSM-Punkt
  --trocken nur anzeigen, nichts schreiben
Braucht Internet. Nominatim erlaubt eine Anfrage pro Sekunde. Kennung: FR_KENNUNG der Instanz (engine/instanz.py).
"""
import datetime
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import instanz  # noqa: E402
import schreiben  # noqa: E402  (routen.yaml formerhaltend lesen und schreiben)

NOMINATIM = "https://nominatim.openstreetmap.org/search"
NACHSCHLAGEN = "https://nominatim.openstreetmap.org/lookup"
UNTERKUNFT = {"hotel", "guest_house", "hostel", "alpine_hut", "apartment", "motel", "chalet", "wilderness_hut"}
OSM_MUSTER = re.compile(r"OSM (node|way|relation)/(\d+)")
SUCHRADIUS_KM = 3


def holen(url, daten=None, versuche=6):
    """GET oder POST -> JSON (Kennung der Instanz, eine Anfrage pro Sekunde; bei 429 „zu viele Anfragen“ mit wachsender Pause
    erneut, etwa wenn sich mehrere Rechner eine Adresse teilen)."""
    req = urllib.request.Request(url, data=urllib.parse.urlencode(daten).encode() if daten else None,
                                 headers={"User-Agent": instanz.kennung()})
    for n in range(versuche):
        time.sleep(1.1 if n == 0 else 5 * 2 ** (n - 1))
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or n == versuche - 1:
                raise


def adresse_aus(tags):
    """OSM-Tags -> „Straße Nr., PLZ Ort“ oder None (ohne Straße oder Platz keine Adresse)."""
    strasse = tags.get("addr:street") or tags.get("addr:place")
    if not strasse:
        return None
    teil1 = f"{strasse} {tags['addr:housenumber']}" if tags.get("addr:housenumber") else strasse
    ort = " ".join(x for x in (tags.get("addr:postcode"), tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village")) if x)
    return f"{teil1}, {ort}" if ort else teil1


def osm_bezuege(punkte):
    """plan/punkte.yaml -> {U-…: (typ, nummer, [Breite, Länge])} aus Punkten mit id und OSM-Quelle."""
    aus = {}
    for liste in (punkte.get("strecken") or {}).values():
        for p in liste or []:
            m = OSM_MUSTER.search(str(p.get("quelle") or ""))
            if p.get("id") and m and p["id"] not in aus:
                aus[p["id"]] = (m.group(1), int(m.group(2)), p.get("lage"))
    return aus


def nachschlagen(bezuege, abfragen=holen):
    """{U-…: (typ, nummer, lage)} -> {(typ, nummer): Nominatim-Treffer}, je Anfrage bis zu 50 Objekte."""
    ids = sorted({f"{t[0].upper()}{n}" for t, n, _ in bezuege.values()})
    aus = {}
    for i in range(0, len(ids), 50):
        q = urllib.parse.urlencode({"osm_ids": ",".join(ids[i:i + 50]), "format": "jsonv2", "addressdetails": 1})
        for t in abfragen(f"{NACHSCHLAGEN}?{q}") or []:
            aus[(t.get("osm_type"), int(t.get("osm_id")))] = t
    return aus


def nominatim_suchen(name, ort_name, mitte, abfragen=holen):
    """Unterkunft nach Name und Ort suchen, begrenzt auf SUCHRADIUS_KM um die Ortsmitte -> Treffer oder None."""
    dy = SUCHRADIUS_KM / 111.0
    dx = SUCHRADIUS_KM / (111.0 * math.cos(math.radians(mitte[0])))
    q = urllib.parse.urlencode({"q": f"{name}, {ort_name}", "format": "jsonv2", "limit": 3, "bounded": 1, "addressdetails": 1,
                                "extratags": 1, "viewbox": f"{mitte[1] - dx},{mitte[0] + dy},{mitte[1] + dx},{mitte[0] - dy}"})
    for t in abfragen(f"{NOMINATIM}?{q}") or []:
        if t.get("category") == "tourism" and t.get("type") in UNTERKUNFT:
            return t
    return None


def adresse_aus_nominatim(t):
    a = t.get("address") or {}
    tags = {"addr:street": a.get("road") or a.get("pedestrian") or a.get("square"), "addr:housenumber": a.get("house_number"),
            "addr:postcode": a.get("postcode"), "addr:city": a.get("town") or a.get("city") or a.get("village")}
    return adresse_aus({k: v for k, v in tags.items() if v})


def vorschlaege(roh, punkte, karte, suchen=False, heute=None, abfragen=holen):
    """-> (neu {U-…: {adresse?, punkt?}}, fehlt [(U-…, Name, Grund)])."""
    heute = heute or datetime.date.today()
    stand = f"Stand {heute.isoformat()}"
    unterkuenfte = roh.get("unterkuenfte") or {}
    offen = {uid: u for uid, u in unterkuenfte.items() if not u.get("adresse")}
    bezuege = {uid: b for uid, b in osm_bezuege(punkte).items() if uid in offen}
    treffer = nachschlagen(bezuege, abfragen)
    neu, fehlt = {}, []
    for uid, u in offen.items():
        if uid in bezuege:
            typ, nr, _ = bezuege[uid]
            a = adresse_aus_nominatim(treffer.get((typ, nr)) or {})
            if a:
                neu[uid] = {"adresse": {"wert": a, "quelle": f"OSM {typ}/{nr}, {stand}", "geprueft": heute}}
                continue
            if not suchen:
                fehlt.append((uid, u.get("name"), f"OSM {typ}/{nr} hat keine Adresse"))
                continue
        if not suchen:
            fehlt.append((uid, u.get("name"), "kein OSM-Punkt in plan/punkte.yaml (--suchen versucht Nominatim)"))
            continue
        ort = (roh.get("orte") or {}).get(u.get("ort")) or {}
        mitte = ((karte.get("orte") or {}).get(u.get("ort")) or {}).get("lage")
        if not mitte:
            fehlt.append((uid, u.get("name"), f"Ort {u.get('ort')} hat keine Lage in plan/karte.yaml"))
            continue
        t = nominatim_suchen(u.get("name"), ort.get("name") or u.get("ort"), mitte, abfragen)
        a = t and adresse_aus_nominatim(t)
        if not a:
            fehlt.append((uid, u.get("name"), "bei Nominatim keine Unterkunft mit Straße gefunden"))
            continue
        quelle = f"OSM {t.get('osm_type')}/{t.get('osm_id')} (Nominatim, Suche „{u.get('name')}“), {stand}"
        neu[uid] = {"adresse": {"wert": a, "quelle": quelle, "geprueft": heute}}
        if not u.get("punkt") and uid not in bezuege:
            neu[uid]["punkt"] = {"wert": [round(float(t["lat"]), 6), round(float(t["lon"]), 6)], "quelle": quelle, "geprueft": heute}
    return neu, fehlt


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    reise = instanz.wurzel() / "reisen" / argv[1]
    roh = schreiben.routen_laden(reise)
    lies = lambda name: yaml.safe_load((reise / "plan" / name).read_text(encoding="utf-8")) if (reise / "plan" / name).exists() else {}
    neu, fehlt = vorschlaege(roh, lies("punkte.yaml") or {}, lies("karte.yaml") or {}, suchen="--suchen" in argv)
    for uid, felder in neu.items():
        print(f"{uid} {roh['unterkuenfte'][uid].get('name')}: {felder['adresse']['wert']}  ({felder['adresse']['quelle']})")
        if "--trocken" not in argv:
            for feld, v in felder.items():
                roh["unterkuenfte"][uid][feld] = schreiben.fliess_map(v)
    if neu and "--trocken" not in argv:
        schreiben.routen_speichern(reise, roh)
    print(f"\n{len(neu)} Adressen {'gefunden' if '--trocken' in argv else 'eingetragen'}; ohne Adresse {len(fehlt)}:")
    for uid, name, grund in fehlt:
        print(f"  {uid} {name}: {grund}")
    print("Den Rest im Gespräch mit Frieda eintragen (lage_eintragen).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
