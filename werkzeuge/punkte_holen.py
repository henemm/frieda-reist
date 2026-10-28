#!/usr/bin/env python3
"""Punkte für die Etappen-Karten: Wegpunkte der GPX-Tracks, Unterkünfte, Einkehr, Wasser, Bus/Notfall.

Erzeugt reisen/<reise>/plan/punkte.yaml einmalig; die Datei wird geprüft und eingecheckt.
Der Bau (engine/bauen.py) liest nur diese Datei und holt nichts aus dem Netz.

Quellen, in dieser Reihenfolge:
  1. GPX-Wegpunkte (<wpt>) der Tracks aus plan/karte.yaml -> gpx; Name „04_Steinbruch (6)“,
     die Nummer verbindet sie mit der Kurzliste im Etappen-Dossier („**Steinbruch (6)**“).
  2. Eine Overpass-Abfrage (OpenStreetMap, ODbL) über den Kartenrahmen; danach wird je Etappe
     lokal nach Abstand zum Track gefiltert.
Namen aus dem Dossier (fett in der Wegpunkt-Kurzliste, erste Spalte der Unterkunftstabellen), die
weder als GPX-Wegpunkt noch in OSM gefunden werden, listet das Skript am Ende auf: keine
geschätzten Koordinaten.

Aufruf (in der Wurzel des Reisen-Repos):  engine/.venv/bin/python frieda/werkzeuge/punkte_holen.py <reise>
Braucht Internet. Kennung gegenüber OpenStreetMap: FR_KENNUNG der Instanz (engine/instanz.py).
"""
import datetime
import json
import math
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import gpx  # noqa: E402
import instanz  # noqa: E402

WURZEL = instanz.wurzel()

OVERPASS = "https://overpass-api.de/api/interpreter"
KENNUNG = instanz.kennung()
NAH_M = 150        # Einkehr, Wasser, Bus: höchstens so weit vom Track
NAH_GENANNT_M = 1500
ORT_M = 700        # so nah an einem Ort aus karte.yaml gilt ein Punkt als „im Ort“  # im Dossier genannte Orte dürfen weiter weg liegen (Abstecher, Ortsmitte)

# OSM-Tags -> (Kategorie, Art)
def einordnen(t):
    a, n, to, hw, mm = t.get("amenity"), t.get("natural"), t.get("tourism"), t.get("highway"), t.get("man_made")
    if a in ("restaurant", "cafe", "bar", "pub", "fast_food", "biergarten"):
        return "einkehr", a
    if a == "drinking_water" or (mm == "water_tap" and t.get("drinking_water") == "yes"):
        return "wasser", "trinkwasser"
    if n == "spring" or a == "fountain" or mm == "water_well":
        return "wasser", "quelle"
    if hw == "bus_stop" or t.get("public_transport") == "platform" and t.get("bus") == "yes":
        return "notfall", "bus"
    if a in ("pharmacy", "clinic", "hospital", "doctors"):
        return "notfall", a
    if a == "taxi":
        return "notfall", "taxi"
    if to in ("hotel", "hostel", "guest_house", "alpine_hut", "wilderness_hut", "apartment", "chalet"):
        return "unterkunft", to
    if a == "shelter":
        return "unterkunft", "schutzhuette"
    return None


def abfrage(rf):
    bbox = f"{rf['sued']},{rf['west']},{rf['nord']},{rf['ost']}"
    q = f"""[out:json][timeout:120];
(
  nwr["amenity"~"^(restaurant|cafe|bar|pub|fast_food|biergarten|drinking_water|fountain|pharmacy|clinic|hospital|doctors|taxi|shelter)$"]({bbox});
  nwr["natural"="spring"]({bbox});
  nwr["man_made"~"^(water_tap|water_well)$"]({bbox});
  node["highway"="bus_stop"]({bbox});
  nwr["tourism"~"^(hotel|hostel|guest_house|alpine_hut|wilderness_hut|apartment|chalet)$"]({bbox});
);
out center tags;"""
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(),
                                 headers={"User-Agent": KENNUNG})
    for versuch in range(4):  # Overpass ist öfter kurz überlastet (502/504)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504) or versuch == 3:
                raise
            print(f"Overpass {e.code}, neuer Versuch in {30 * (versuch + 1)} s …", file=sys.stderr)
            time.sleep(30 * (versuch + 1))


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower().replace("ø", "o").replace("æ", "ae"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[’'`´.,()\"«»]", " ", s)
    s = re.sub(r"\b(restaurant|restaurante|bar|cafe|caf|hotel|hostal|hostel|pension|refugi|refugio|de|del|des|d|s|sa|es|el|la|l|the|y|i|a)\b", " ", s)
    return " ".join(s.split())


def passt(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    k, g = sorted((a, b), key=len)  # enthalten nur bei mindestens zwei Wörtern, sonst passt „Petit“ auf jedes Petit-Hotel
    return len(k.split()) >= 2 and re.search(rf"\b{re.escape(k)}\b", g) is not None


def abstand_linie_m(p, linie):
    """Kleinster Abstand eines Punkts zu einer Polylinie (flache Näherung)."""
    b0 = p[0]
    px, py = gpx._xy(p, b0)
    best = math.inf
    xy = [gpx._xy(q, b0) for q in linie]
    for (ax, ay), (bx, by) in zip(xy, xy[1:]):
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        t = 0 if not l2 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / l2))
        best = min(best, math.hypot(px - ax - t * dx, py - ay - t * dy))
    return best


def wegpunkte(pfad):
    out = []
    for w in ET.parse(pfad).getroot().iter():
        if w.tag.rsplit("}", 1)[-1] != "wpt":
            continue
        name = next((c.text for c in w if c.tag.rsplit("}", 1)[-1] == "name"), "") or ""
        m = re.match(r"^\w+?_(.*?)\s*\((\d+)\)\s*$", name)
        if m:
            out.append({"name": m.group(1).strip(), "nr": int(m.group(2)),
                        "lage": [round(float(w.get("lat")), 6), round(float(w.get("lon")), 6)]})
    return out


def dossier_namen(text):
    """Etappe-ID -> [(Name, Quelle im Dossier)] aus Wegpunkt-Kurzliste (fett) und Unterkunftstabellen."""
    teile = re.split(r"^## Etappe (\S+?):.*$", text, flags=re.M)
    out = {}
    for i in range(1, len(teile), 2):
        nr, body = teile[i], teile[i + 1]
        eid = "E-" + (nr.zfill(3) if nr[-1].isalpha() else nr.zfill(2))
        namen = []
        for m in re.finditer(r"\*\*([^*]+?)\*\*", body):
            n = re.sub(r"\s*\(\d+\)\s*$", "", m.group(1)).strip()
            if 3 <= len(n) <= 60:
                namen.append(n)
        for zeile in body.splitlines():
            if zeile.startswith("|") and not re.match(r"^\|\s*(-+|Name)\s*\|", zeile):
                n = zeile.split("|")[1].strip().strip("*")
                if 3 <= len(n) <= 60:
                    namen.append(n)
        out[eid] = list(dict.fromkeys(namen))
    return out


def main(reise):
    rd = WURZEL / "reisen" / reise
    karte = yaml.safe_load((rd / "plan/karte.yaml").read_text(encoding="utf-8"))
    route = yaml.safe_load((rd / "plan/routen.yaml").read_text(encoding="utf-8"))
    cfg = json.loads((rd / "reise.json").read_text(encoding="utf-8"))
    text = "\n".join((rd / cfg[k]).read_text(encoding="utf-8") for k in ("etappen_dossier", "unterkuenfte_dossier") if cfg.get(k))
    genannt = {}
    for eid, n in dossier_namen(text).items():
        genannt.setdefault(eid, []).extend(x for x in n if x not in genannt.get(eid, []))
    heute = datetime.date.today().isoformat()

    print("Frage OpenStreetMap ab …", file=sys.stderr)
    osm = abfrage(karte["rahmen"])
    stand = osm.get("osm3s", {}).get("timestamp_osm_base", heute)[:10]
    elemente = []
    for e in osm["elements"]:
        t = e.get("tags", {})
        k = einordnen(t)
        lat, lon = (e.get("lat"), e.get("lon")) if "lat" in e else (e.get("center", {}).get("lat"), e.get("center", {}).get("lon"))
        if k and lat is not None:
            elemente.append({"osm": f"{e['type']}/{e['id']}", "kat": k[0], "art": k[1], "name": t.get("name", ""),
                             "lage": [round(lat, 6), round(lon, 6)], "tags": t})

    datei = rd / "plan/punkte.yaml"
    alt = (yaml.safe_load(datei.read_text(encoding="utf-8")) or {}).get("strecken", {}) if datei.exists() else {}
    unterkuenfte = route.get("unterkuenfte") or {}
    ortschaften = [o["lage"] for o in (karte.get("orte") or {}).values() if o.get("lage")] + \
        [p["lage"] for p in karte.get("punkte") or [] if p.get("lage")]
    ausgabe, fehlt = {}, {}
    for eid, rel in (karte.get("gpx") or {}).items():
        linie = gpx.vereinfachen(gpx.lesen(rd / rel))
        punkte, gefunden = [], set()
        for w in wegpunkte(rd / rel):
            p = {"name": w["name"], "kat": "wegpunkt", "nr": w["nr"], "lage": w["lage"], "quelle": "Rother-GPX"}
            uid = next((u for u, x in unterkuenfte.items() if passt(x.get("name", ""), w["name"])), None)
            if uid:
                p["id"] = uid
            punkte.append(p)
            gefunden.add(norm(w["name"]))
        for e in elemente:
            d = abstand_linie_m(e["lage"], linie)
            if d > NAH_GENANNT_M:
                continue
            nennung = next((n for n in genannt.get(eid, []) if e["name"] and passt(n, e["name"])), None)
            uid = next((u for u, x in unterkuenfte.items() if e["name"] and passt(x.get("name", ""), e["name"])), None)
            if e["kat"] == "unterkunft" and not (nennung or uid):
                continue  # Hotels nur, wenn genannt oder im Plan: sonst ganze Orte voller Betten
            if not (nennung or uid) and d > NAH_M:
                continue
            # Ungenanntes in den Orten (Einkehr, Brunnen, Haltestellen) nur ausgedünnt: dort findet man es ohnehin
            im_ort = min(gpx.abstand_m(e["lage"], o) for o in ortschaften) < ORT_M
            if not (nennung or uid) and e["kat"] == "einkehr" and im_ort:
                continue
            if not (nennung or uid) and e["kat"] in ("wasser", "notfall") and any(
                    q["kat"] == e["kat"] and q.get("art") == e["art"] and gpx.abstand_m(q["lage"], e["lage"]) < (400 if im_ort else 150)
                    for q in punkte):
                continue
            if any(norm(p["name"]) == norm(e["name"]) and p["kat"] == "wegpunkt" for p in punkte if e["name"]):
                continue  # schon als GPX-Wegpunkt da
            p = {"name": e["name"],  # leer: die Seite zeigt dann die Art (Quelle, Bushaltestelle …)
                 "kat": e["kat"], "art": e["art"], "lage": e["lage"], "quelle": f"OSM {e['osm']}, Stand {stand}"}
            if uid:
                p["id"] = uid
            if nennung and nennung != p["name"]:  # auch bei anderem Akzent oder Großschreibung: der Text verlinkt wörtlich
                p["auch"] = [nennung]
            t = e["tags"]
            if t.get("opening_hours"):
                p["offen"] = t["opening_hours"]
            if e["art"] == "quelle" and t.get("drinking_water"):
                p["trinkbar"] = t["drinking_water"]
            punkte.append(p)
            if nennung:
                gefunden.add(norm(nennung))
        # Von Hand ergänzte Punkte (von_hand: true) bleiben beim Auffrischen erhalten; ihr OSM-Eintrag nicht doppelt
        for h in alt.get(eid, []):
            if h.get("von_hand"):
                punkte = [p for p in punkte if p.get("quelle", "").split(",")[0] != h.get("quelle", "").split(",")[0]]
                punkte.append(h)
        # Reihenfolge entlang des Tracks
        def lauf(p):
            b0 = p["lage"][0]
            return min(range(len(linie)), key=lambda i: gpx.abstand_m(p["lage"], linie[i]))
        punkte.sort(key=lauf)
        ausgabe[eid] = punkte
        fehlt[eid] = [n for n in genannt.get(eid, []) if norm(n) not in gefunden
                      and not any(passt(n, x) for p in punkte for x in [p["name"], *(p.get("auch") or [])])]

    kopf = (f"# Punkte der Etappen-Karten, erzeugt mit frieda/werkzeuge/punkte_holen.py {reise} am {heute}.\n"
            f"# Quellen: Rother-GPX (nur privat, siehe medien/gpx/README.md) und OpenStreetMap (ODbL), Stand {stand}.\n"
            "# kat: wegpunkt | unterkunft | einkehr | wasser | notfall; bei wasser art trinkwasser (laut OSM) oder quelle\n"
            "# (Trinkbarkeit ungeprüft). Von Hand ergänzte Punkte: von_hand: true, quelle mit Prüfdatum; sie bleiben beim Auffrischen.\n")
    zeilen = [f"stand: {stand}", "strecken:"]
    for eid, punkte in ausgabe.items():  # ein Punkt je Zeile: gut zu prüfen und zu ändern
        zeilen.append(f"  {eid}:")
        zeilen += ["  - " + yaml.safe_dump(p, allow_unicode=True, default_flow_style=True, sort_keys=False, width=10000).strip()
                   for p in punkte]
    (rd / "plan/punkte.yaml").write_text(kopf + "\n".join(zeilen) + "\n", encoding="utf-8")
    for eid, p in ausgabe.items():
        z = {}
        for x in p:
            z[x["kat"]] = z.get(x["kat"], 0) + 1
        print(f"{eid}: {z}" + (f"  · im Dossier genannt, nicht gefunden: {', '.join(fehlt[eid])}" if fehlt[eid] else ""))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: engine/.venv/bin/python frieda/werkzeuge/punkte_holen.py <reise>")
    main(sys.argv[1])
