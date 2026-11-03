#!/usr/bin/env python3
"""Koordinaten für die Karten in der Recherche (Wissens-Punkte) aus OpenStreetMap (Nominatim, ODbL).

Seit ADR-0007 (Schritt d) sind Punkte der Recherche Dinge (Aufenthalte A-… mit an: <Abschnitt des Wissens>, Art mit gruppe wissen) in
plan/routen.yaml. Die Punkte-Datei der Reise (reise.json -> wissen_punkte) hält die Arbeitsliste: unter bloecke stehen Punkte, die noch
keine Lage haben oder bewusst keine bekommen (ohne_karte: "Grund"), je mit name, kat (Art der Reise), gebiet und suche (Suchbegriffe,
der beste zuerst); dazu gebiete (mitte und radius_km) und grundkarten. Für Punkte ohne lage fragt das Skript Nominatim, je Begriff
eingegrenzt auf das Gebiet, legt bei einem Treffer das Ding an (Lage, Quelle mit OSM-Objekt, Suchbegriff und Datum) und nimmt den Punkt
aus der Liste. Was nicht gefunden wird, bleibt in der Liste und wird am Ende aufgelistet: keine geschätzten Koordinaten. ohne_karte
markiert Orte, die sich nicht sicher verorten lassen; sie werden nicht gesucht. Vorhandene Dinge bleiben unverändert (auch von Hand
korrigierte).

Aufruf (in der Wurzel des Reisen-Repos):  engine/.venv/bin/python frieda/werkzeuge/wissen_punkte_holen.py <reise> [--neu] [--rahmen]
         --neu: Dinge, deren Lage dieses Werkzeug gesetzt hat (Quelle „via Nominatim“), mit ihrem Namen neu suchen, im nächsten Gebiet
         --rahmen: je Grundkarte den Ausschnitt vorschlagen, der alle Punkte ihres Gebiets enthält
         Sprachen der Namen: FR_SPRACHEN (Vorgabe de,en; z. B. de,en,ja)
Braucht Internet. Nominatim erlaubt eine Anfrage pro Sekunde. Kennung: FR_KENNUNG der Instanz (engine/instanz.py).
"""
import datetime
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import instanz  # noqa: E402
import schreiben  # noqa: E402

WURZEL = instanz.wurzel()
NOMINATIM = "https://nominatim.openstreetmap.org/search"
KENNUNG = instanz.kennung()
SPRACHEN = instanz.wert("FR_SPRACHEN", "de,en")


def suchen(begriff, mitte, radius_km):
    dy = radius_km / 111.0
    dx = radius_km / (111.0 * math.cos(math.radians(mitte[0])))
    q = urllib.parse.urlencode({"q": begriff, "format": "jsonv2", "limit": 1, "bounded": 1,
                                "viewbox": f"{mitte[1] - dx},{mitte[0] + dy},{mitte[1] + dx},{mitte[0] - dy}",
                                "accept-language": SPRACHEN})
    req = urllib.request.Request(f"{NOMINATIM}?{q}", headers={"User-Agent": KENNUNG})
    time.sleep(1.1)
    with urllib.request.urlopen(req, timeout=30) as r:
        treffer = json.load(r)
    return treffer[0] if treffer else None


AUFRUF = """Usage (in the root of the trips repository):
  engine/.venv/bin/python frieda/werkzeuge/wissen_punkte_holen.py <trip> [--neu] [--rahmen]
  --neu      search again the things whose position this tool set (source "via Nominatim"), by their name, in the nearest area
  --rahmen   propose the extract per base map that contains all points of its area
Names in languages: FR_SPRACHEN (default de,en; e.g. de,en,ja)"""


def abstand_km(a, b):
    """Luftlinie in km zwischen zwei Punkten [Breite, Länge] (Haversine)."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def naechstes_gebiet(lage, gebiete):
    """Name des Gebiets, dessen Mitte der Lage am nächsten liegt (None ohne Gebiete)."""
    return min(gebiete, key=lambda n: abstand_km(lage, gebiete[n]["mitte"]), default=None)


def wissen_dinge(reise):
    """Dinge an Abschnitten des Wissens (an: W-…), deren Art die gruppe wissen hat -> [(ID, Knoten)]; Quelle: plan/routen.yaml."""
    arten = schreiben.arten_laden(reise)
    roh = schreiben.routen_laden(reise)
    return [(aid, k) for aid, k in (roh.get("aufenthalte") or {}).items()
            if isinstance(k, dict) and str(k.get("an", "")).startswith("W-") and (arten.get(k.get("art")) or {}).get("gruppe") == "wissen"]


def lage_von(knoten):
    k = next((v for v in (knoten.get("merkmale") or {}).values() if isinstance(v, dict) and v.get("typ") == "koordinaten"), None)
    return (list(k["wert"]), str(k.get("quelle") or "")) if k and k.get("wert") else (None, "")


def main(argv):
    if len(argv) < 2:
        print(AUFRUF)
        return 1
    reise = WURZEL / "reisen" / argv[1]
    rel = json.loads((reise / "reise.json").read_text(encoding="utf-8")).get("wissen_punkte")
    if not rel:
        print("reise.json has no entry wissen_punkte.")
        return 1
    pfad = reise / rel
    text = pfad.read_text(encoding="utf-8")
    kopf = "".join(z + "\n" for z in text.splitlines() if z.startswith("#"))  # Kommentarkopf bleibt
    d = yaml.safe_load(text) or {}
    gebiete = d.get("gebiete") or {}

    if "--rahmen" in argv:
        lagen = [(lage_von(k)[0], naechstes_gebiet(lage_von(k)[0], gebiete)) for _, k in wissen_dinge(reise) if lage_von(k)[0]]
        lagen += [(p["lage"], p.get("gebiet")) for liste in (d.get("bloecke") or {}).values() for p in liste if p.get("lage")]
        for name, g in (d.get("grundkarten") or {}).items():
            pk = [lage for lage, gebiet in lagen if gebiet in g.get("gebiete", [name])]
            if pk:
                s, n = min(p[0] for p in pk), max(p[0] for p in pk)
                w, o = min(p[1] for p in pk), max(p[1] for p in pk)
                print(f"{name}: {{nord: {n + 0.02:.3f}, sued: {s - 0.02:.3f}, west: {w - 0.02:.3f}, ost: {o + 0.02:.3f}}}  ({len(pk)} points)")
        return 0

    heute = datetime.date.today()
    wer = {"name": f"Tool wissen_punkte_holen {heute.isoformat()}"}
    neu, fehlt, unbekannt, angelegt = "--neu" in argv, [], set(), 0
    for bid, liste in list((d.get("bloecke") or {}).items()):
        bleibt = []
        for p in liste or []:
            if p.get("ohne_karte"):
                bleibt.append(p)
                continue
            if not p.get("lage"):
                g = gebiete.get(p.get("gebiet"))
                if not g:
                    fehlt.append(f"{bid}: {p['name']} (area {p.get('gebiet')} missing under gebiete)")
                    bleibt.append(p)
                    continue
                for begriff in p.get("suche") or [p["name"]]:
                    t = suchen(begriff, g["mitte"], g.get("radius_km", 30))
                    if t:
                        p["lage"] = [round(float(t["lat"]), 6), round(float(t["lon"]), 6)]
                        p["quelle"] = f"OSM {t['osm_type']}/{t['osm_id']} via Nominatim (“{begriff}”), as of {heute.isoformat()}"
                        print(f"  {p['name']}: {t.get('display_name', '')[:90]}")
                        break
                else:
                    fehlt.append(f"{bid}: {p['name']}")
                    bleibt.append(p)
                    continue
            res = schreiben.kartenpunkte_ablegen(reise, wer, bid, [{k: v for k, v in p.items() if k not in ("gebiet", "suche", "von_hand")}], heute=heute)
            if res["unbekannt"]:
                unbekannt.update(res["unbekannt"])
                bleibt.append(p)
            else:
                angelegt += 1
        if bleibt:
            d["bloecke"][bid] = bleibt
        else:
            d["bloecke"].pop(bid)
    if "bloecke" in d and not d["bloecke"]:
        d.pop("bloecke")

    neu_gesucht = 0
    if neu:   # Dinge, deren Lage dieses Werkzeug gesetzt hat, erneut suchen (von Hand gesetzte tragen eine andere Quelle und bleiben)
        roh = schreiben.routen_laden(reise)
        for aid, k in wissen_dinge(reise):
            lage, quelle = lage_von(k)
            if not lage or "via Nominatim" not in quelle:
                continue
            gebiet = naechstes_gebiet(lage, gebiete)
            if gebiet is None:
                continue
            t = suchen(k["name"], gebiete[gebiet]["mitte"], gebiete[gebiet].get("radius_km", 30))
            if t:
                knoten = roh["aufenthalte"][aid]
                quelle_neu = f"OSM {t['osm_type']}/{t['osm_id']} via Nominatim (“{k['name']}”), as of {heute.isoformat()}"
                schreiben.lage_merkmal_schreiben(knoten, "koordinaten", [round(float(t["lat"]), 6), round(float(t["lon"]), 6)], quelle_neu, heute)
                neu_gesucht += 1
                print(f"  {aid} {k['name']}: {t.get('display_name', '')[:90]}")
            else:
                fehlt.append(f"{aid}: {k['name']} (unchanged)")
        schreiben.routen_speichern(reise, roh)
    d["stand"] = heute.isoformat()
    pfad.write_text(kopf + yaml.dump(d, allow_unicode=True, sort_keys=False, width=200, default_flow_style=None),
                    encoding="utf-8")
    print(f"Written: {pfad} · things created {angelegt}" + (f", searched again {neu_gesucht}" if neu else ""))
    if unbekannt:
        print("Kinds missing in the trip (create them with kind_define, group wissen), their points stay in the list: " + ", ".join(sorted(unbekannt)))
    if fehlt:
        print(f"Not found ({len(fehlt)}), please check by hand:")
        print("\n".join("  " + f for f in fehlt))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
