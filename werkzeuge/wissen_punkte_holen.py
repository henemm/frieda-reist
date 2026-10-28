#!/usr/bin/env python3
"""Koordinaten für die Karten in der Recherche (Wissens-Punkte) aus OpenStreetMap (Nominatim, ODbL).

Liest die Punkte-Datei der Reise (reise.json -> wissen_punkte). Jeder Punkt nennt name, kat, gebiet und
suche (Suchbegriffe, der beste zuerst). Für Punkte ohne lage fragt das Skript Nominatim, je Begriff
eingegrenzt auf das Gebiet (gebiete: mitte und radius_km), und trägt lage und quelle (OSM-Objekt,
Suchbegriff, Datum) ein. Was nicht gefunden wird, bleibt ohne lage und wird am Ende aufgelistet: keine
geschätzten Koordinaten. Punkte mit lage bleiben unverändert (auch von Hand korrigierte); ohne_karte: "Grund"
markiert Orte, die sich nicht sicher verorten lassen (keine Filiale genannt, nicht in OSM), sie werden nicht gesucht.

Aufruf (in der Wurzel des Reisen-Repos):  engine/.venv/bin/python frieda/werkzeuge/wissen_punkte_holen.py <reise> [--neu]
         --neu: auch Punkte mit lage neu suchen (außer von_hand: true)
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


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    reise = WURZEL / "reisen" / argv[1]
    rel = json.loads((reise / "reise.json").read_text(encoding="utf-8")).get("wissen_punkte")
    if not rel:
        print("reise.json hat keinen Eintrag wissen_punkte.")
        return 1
    pfad = reise / rel
    text = pfad.read_text(encoding="utf-8")
    kopf = "".join(z + "\n" for z in text.splitlines() if z.startswith("#"))  # Kommentarkopf bleibt
    d = yaml.safe_load(text) or {}
    gebiete = d.get("gebiete") or {}

    if "--rahmen" in argv:
        for name, g in (d.get("grundkarten") or {}).items():
            pk = [p["lage"] for l in d["bloecke"].values() for p in l if p.get("lage") and p.get("gebiet") in g.get("gebiete", [name])]
            if pk:
                s, n = min(p[0] for p in pk), max(p[0] for p in pk)
                w, o = min(p[1] for p in pk), max(p[1] for p in pk)
                print(f"{name}: {{nord: {n + 0.02:.3f}, sued: {s - 0.02:.3f}, west: {w - 0.02:.3f}, ost: {o + 0.02:.3f}}}  ({len(pk)} Punkte)")
        return 0

    heute = datetime.date.today().isoformat()
    neu, fehlt = "--neu" in argv, []
    for bid, liste in (d.get("bloecke") or {}).items():
        for p in liste:
            if p.get("ohne_karte") or p.get("lage") and (not neu or p.get("von_hand")):
                continue
            g = gebiete.get(p.get("gebiet"))
            if not g:
                fehlt.append(f"{bid}: {p['name']} (Gebiet {p.get('gebiet')} fehlt unter gebiete)")
                continue
            for begriff in p.get("suche") or [p["name"]]:
                t = suchen(begriff, g["mitte"], g.get("radius_km", 30))
                if t:
                    p["lage"] = [round(float(t["lat"]), 6), round(float(t["lon"]), 6)]
                    p["quelle"] = f"OSM {t['osm_type']}/{t['osm_id']} über Nominatim („{begriff}“), Stand {heute}"
                    print(f"  {p['name']}: {t.get('display_name', '')[:90]}")
                    break
            else:
                p.pop("lage", None)
                p.pop("quelle", None)
                fehlt.append(f"{bid}: {p['name']}")
    d["stand"] = heute
    pfad.write_text(kopf + yaml.dump(d, allow_unicode=True, sort_keys=False, width=200, default_flow_style=None),
                    encoding="utf-8")
    print(f"Geschrieben: {pfad}")
    if fehlt:
        print(f"Nicht gefunden ({len(fehlt)}), bitte von Hand prüfen:")
        print("\n".join("  " + f for f in fehlt))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
