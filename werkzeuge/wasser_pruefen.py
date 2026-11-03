#!/usr/bin/env python3
"""Wasserstellen prüfen: wie belastbar sind die OSM-Angaben zu den Wasserpunkten einer Reise?

Organic Maps zeigt OpenStreetMap-Daten; es gibt dort keine eigene Wasserdatenbank. Dieses Skript nimmt
die Wasserpunkte der Reise (ADR-0007, Schritt d: Dinge, Aufenthalte A-… mit an: <Strecke>, deren Art eine gruppe hat, mit einem
Merkmal der Rolle osm und einer Sorte, die Wasser ist: Merkmal der Rolle sorte mit „trinkwasser“ oder „quelle“, den Sorten, die
punkte_holen.py für Wasser vergibt; gelesen nach Rolle, nie nach dem Namen der Art), holt sie mit allen Tags
und Bearbeitungsdaten noch einmal von Overpass (OpenStreetMap, ODbL) und stuft sie nach der Datenlage ein.
Die Einstufung sagt, wie gut belegt ein Eintrag ist, nicht, ob die Quelle zur Reisezeit wirklich läuft.

Die Altform (Punkte mit kat: wasser und Quelle „OSM node/…“ in plan/punkte.yaml) wird weiter gelesen, solange es die Datei gibt.

Ergebnis: reisen/<reise>/inhalt/recherche/wasserstellen-osm.md (zur Durchsicht, ändert die Reise nicht).

Aufruf (in der Wurzel des Reisen-Repos):  engine/.venv/bin/python frieda/werkzeuge/wasser_pruefen.py <reise>
Braucht Internet. Kennung gegenüber OpenStreetMap: FR_KENNUNG der Instanz (engine/instanz.py).
"""
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import instanz  # noqa: E402
import schreiben  # noqa: E402  (Kartenpunkte als Dinge lesen)

WURZEL = instanz.wurzel()
OVERPASS = "https://overpass-api.de/api/interpreter"
KENNUNG = instanz.kennung()
GEPRUEFT_JAHRE = 3  # Prüfdatum im Eintrag (check_date, survey:date) gilt so lange als frisch

WASSER_SORTEN = ("trinkwasser", "quelle")   # Sorten (Rolle sorte), die punkte_holen.einordnen für Wasser vergibt
STUFEN = ("well documented", "with reservations", "uncertain")
HARTE_WARNUNGEN = ("no drinking water per OSM", "drinking_water=", "seasonal", "intermittent", "access", "condition", "note in entry", "fee")
WARNWORTE =re.compile(r"\b(seca|seco|dry|no\s*potable|no\s*beber|not\s*potable|nicht|kein|polluted|contaminad\w*)\b", re.I)


def pruefdatum(tags):
    """Jüngstes Prüfdatum aus den Tags (JJJJ[-MM[-TT]]) als date, sonst None."""
    daten = []
    for k in ("check_date", "survey:date", "check_date:drinking_water"):
        m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$", tags.get(k, ""))
        if m:
            try:
                daten.append(datetime.date(int(m[1]), int(m[2] or 1), int(m[3] or 1)))
            except ValueError:
                pass
    return max(daten) if daten else None


def bewerte(tags, heute):
    """(Stufe, Gründe) aus den OSM-Tags eines Wasserpunkts."""
    warn, belege = [], []
    dw = tags.get("drinking_water")
    trinkwasser = tags.get("amenity") == "drinking_water" and dw != "no" or dw == "yes"
    if dw == "no":
        warn.append("no drinking water per OSM")
    elif dw and dw not in ("yes", "no"):
        warn.append(f"drinking_water={dw}")
    if tags.get("seasonal") not in (None, "no") or tags.get("seasonal:water"):
        warn.append(f"seasonal ({tags.get('seasonal') or tags.get('seasonal:water')})")
    if tags.get("intermittent") not in (None, "no"):
        warn.append("intermittent: sometimes without water")
    if tags.get("access") in ("private", "no", "customers", "permit"):
        warn.append(f"access restricted ({tags['access']})")
    if tags.get("operational_status") not in (None, "working", "operational"):
        warn.append(f"condition: {tags['operational_status']}")
    if tags.get("fee") == "yes":
        warn.append("fee required")
    for k in ("note", "description", "note:es", "note:de"):
        if tags.get(k) and WARNWORTE.search(tags[k]):
            warn.append(f"note in entry: “{tags[k]}”")
            break
    datum = pruefdatum(tags)
    if trinkwasser:
        belege.append("entered as drinking water")
    else:
        warn.append("drinkability not entered (spring/well)")
    frisch = datum is not None and (heute - datum).days <= GEPRUEFT_JAHRE * 365
    if datum:
        (belege if frisch else warn).append(f"last checked {datum.isoformat()}")
    else:
        warn.append("no check date in the entry")
    if not warn:
        stufe = STUFEN[0]
    elif trinkwasser and not any(w.startswith(HARTE_WARNUNGEN) for w in warn):
        stufe = STUFEN[1]  # nur Prüfdatum fehlt oder ist alt
    else:
        stufe = STUFEN[2]
    return stufe, belege + warn


def wasserpunkte(dinge, altform=None):
    """-> [{etappe, osm ('node/123'), lage, name, art}] der Wasserpunkte. dinge: schreiben.kartenpunkte_lesen (Gruppe punkt, Rolle osm,
    Sorte aus WASSER_SORTEN); altform: Inhalt von plan/punkte.yaml (kat: wasser). Ein Punkt mit demselben OSM-Bezug zählt einmal."""
    aus, gesehen = [], set()
    for p in dinge or ():
        m = re.match(r"^(?:OSM )?((?:node|way|relation)/\d+)", str(p.get("osm") or ""))
        if p.get("gruppe") == "punkt" and m and p.get("sorte") in WASSER_SORTEN and m[1] not in gesehen:
            gesehen.add(m[1])
            aus.append({"etappe": p["an"], "osm": m[1], "lage": p["lage"], "name": p["name"], "art": p["art"]})
    for eid, ps in ((altform or {}).get("strecken") or {}).items():
        for p in ps or []:
            m = re.match(r"^OSM ((?:node|way|relation)/\d+)", p.get("quelle", ""))
            if p.get("kat") == "wasser" and m and m[1] not in gesehen:
                gesehen.add(m[1])
                aus.append({"etappe": eid, "osm": m[1], "lage": p["lage"], "name": p.get("name"), "art": p.get("art", "Wasser")})
    return aus


def osm_ids(punkte):
    """{'node': [ids], 'way': [...], 'relation': [...]} aus wasserpunkte()."""
    out = {}
    for p in punkte:
        typ, nr = p["osm"].split("/")
        out.setdefault(typ, set()).add(int(nr))
    return {k: sorted(v) for k, v in out.items()}


def abfragen(ids):
    teile = []
    for typ, liste in ids.items():
        for i in range(0, len(liste), 100):
            teile.append(f"{typ}(id:{','.join(map(str, liste[i:i + 100]))});")
    q = "[out:json][timeout:120];\n(" + "".join(teile) + ");\nout meta tags center;"
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(),
                                 headers={"User-Agent": KENNUNG})
    for versuch in range(4):  # Overpass ist öfter kurz überlastet
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 502, 503, 504) or versuch == 3:
                raise
            print(f"Overpass {e.code}, retrying in {30 * (versuch + 1)} s …", file=sys.stderr)
            time.sleep(30 * (versuch + 1))


def bericht(reise, stand, zeilen):
    z = {s: sum(1 for x in zeilen if x["stufe"] == s) for s in STUFEN}
    out = [f"# Water points per OpenStreetMap: state of the data ({reise})", "",
           f"Source: OpenStreetMap data (ODbL), queried on {stand} with frieda/werkzeuge/wasser_pruefen.py; this is the same data "
           "that Organic Maps shows. An assessment of the data, not a statement about the condition on site.", "",
           "“Well documented” means: entered as drinking water, no warnings, check date at most "
           f"{GEPRUEFT_JAHRE} years old. It does not mean the source is sure to flow at the time of the trip; "
           "water points change and must be checked again before the trip.", "",
           f"Result: {z[STUFEN[0]]} {STUFEN[0]}, {z[STUFEN[1]]} {STUFEN[1]}, {z[STUFEN[2]]} {STUFEN[2]}.", ""]
    for eid in dict.fromkeys(x["etappe"] for x in zeilen):
        out += [f"## {eid}", "", "| Level | Name / kind | Location | OSM | Reasons |", "|---|---|---|---|---|"]
        for x in zeilen:
            if x["etappe"] == eid:
                lat, lon = x["lage"]
                out.append(f"| {x['stufe']} | {x['name']} | {lat:.5f}, {lon:.5f} | {x['osm']} (last edited {x['bearbeitet']}) "
                           f"| {'; '.join(x['gruende'])} |")
        out.append("")
    return "\n".join(out)


def main(reise):
    rd = WURZEL / "reisen" / reise
    alt = rd / "plan/punkte.yaml"
    punkte = wasserpunkte(schreiben.kartenpunkte_lesen(rd),
                          (yaml.safe_load(alt.read_text(encoding="utf-8")) or {}) if alt.exists() else {})
    ids = osm_ids(punkte)
    if not ids:
        sys.exit("No OSM water points in the trip (things with the roles osm and sorte, sort trinkwasser or quelle).")
    print(f"Querying OpenStreetMap for {sum(map(len, ids.values()))} water points …", file=sys.stderr)
    antwort = abfragen(ids)
    osm = {f"{e['type']}/{e['id']}": e for e in antwort["elements"]}
    heute = datetime.date.today()
    zeilen, weg = [], []
    for p in punkte:
        e = osm.get(p["osm"])
        if not e:
            weg.append(p["osm"])  # in OSM gelöscht oder umgezogen
            continue
        tags = e.get("tags", {})
        stufe, gruende = bewerte(tags, heute)
        mitte = (e.get("center") or e).get("lat"), (e.get("center") or e).get("lon")   # ohne eigene Koordinaten die aus OSM
        lage = p["lage"] or ([mitte[0], mitte[1]] if None not in mitte else [0.0, 0.0])
        zeilen.append({"etappe": p["etappe"], "stufe": stufe, "gruende": gruende, "osm": p["osm"], "lage": lage,
                       "name": p["name"] or tags.get("name") or p["art"],
                       "bearbeitet": e.get("timestamp", "?")[:10]})
    text = bericht(reise, heute.isoformat(), zeilen)
    if weg:
        text += "\n## In OpenStreetMap nicht mehr vorhanden\n\n" + "\n".join(f"- {w}" for w in weg) + "\n"
    ziel = rd / "inhalt/recherche/wasserstellen-osm.md"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    print(f"{ziel.relative_to(WURZEL)}: " + ", ".join(f"{sum(1 for x in zeilen if x['stufe'] == s)} {s}" for s in STUFEN)
          + (f", {len(weg)} no longer in OSM" if weg else ""))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: engine/.venv/bin/python frieda/werkzeuge/wasser_pruefen.py <trip>")
    main(sys.argv[1])
