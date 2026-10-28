#!/usr/bin/env python3
"""Wasserstellen prüfen: wie belastbar sind die OSM-Angaben zu den Wasserpunkten einer Reise?

Organic Maps zeigt OpenStreetMap-Daten; es gibt dort keine eigene Wasserdatenbank. Dieses Skript nimmt
die Wasserpunkte aus reisen/<reise>/plan/punkte.yaml (Quelle „OSM node/…“), holt sie mit allen Tags
und Bearbeitungsdaten noch einmal von Overpass (OpenStreetMap, ODbL) und stuft sie nach der Datenlage ein.
Die Einstufung sagt, wie gut belegt ein Eintrag ist, nicht, ob die Quelle zur Reisezeit wirklich läuft.

Ergebnis: reisen/<reise>/inhalt/recherche/wasserstellen-osm.md (zur Durchsicht, ändert punkte.yaml nicht).

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

WURZEL = instanz.wurzel()
OVERPASS = "https://overpass-api.de/api/interpreter"
KENNUNG = instanz.kennung()
GEPRUEFT_JAHRE = 3  # Prüfdatum im Eintrag (check_date, survey:date) gilt so lange als frisch

STUFEN = ("gut belegt", "mit Vorbehalt", "unsicher")
HARTE_WARNUNGEN = ("laut OSM kein", "drinking_water=", "saisonal", "zeitweise", "Zugang", "Zustand", "Hinweis", "kostenpflichtig")
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
        warn.append("laut OSM kein Trinkwasser")
    elif dw and dw not in ("yes", "no"):
        warn.append(f"drinking_water={dw}")
    if tags.get("seasonal") not in (None, "no") or tags.get("seasonal:water"):
        warn.append(f"saisonal ({tags.get('seasonal') or tags.get('seasonal:water')})")
    if tags.get("intermittent") not in (None, "no"):
        warn.append("zeitweise ohne Wasser (intermittent)")
    if tags.get("access") in ("private", "no", "customers", "permit"):
        warn.append(f"Zugang eingeschränkt ({tags['access']})")
    if tags.get("operational_status") not in (None, "working", "operational"):
        warn.append(f"Zustand: {tags['operational_status']}")
    if tags.get("fee") == "yes":
        warn.append("kostenpflichtig")
    for k in ("note", "description", "note:es", "note:de"):
        if tags.get(k) and WARNWORTE.search(tags[k]):
            warn.append(f"Hinweis im Eintrag: „{tags[k]}“")
            break
    datum = pruefdatum(tags)
    if trinkwasser:
        belege.append("als Trinkwasser eingetragen")
    else:
        warn.append("Trinkbarkeit nicht eingetragen (Quelle/Brunnen)")
    frisch = datum is not None and (heute - datum).days <= GEPRUEFT_JAHRE * 365
    if datum:
        (belege if frisch else warn).append(f"zuletzt geprüft {datum.isoformat()}")
    else:
        warn.append("kein Prüfdatum im Eintrag")
    if not warn:
        stufe = STUFEN[0]
    elif trinkwasser and not any(w.startswith(HARTE_WARNUNGEN) for w in warn):
        stufe = STUFEN[1]  # nur Prüfdatum fehlt oder ist alt
    else:
        stufe = STUFEN[2]
    return stufe, belege + warn


def osm_ids(punkte):
    """{'node': [ids], 'way': [...], 'relation': [...]} aus den Quellen 'OSM node/123, Stand …'."""
    out = {}
    for p in punkte:
        m = re.match(r"^OSM (node|way|relation)/(\d+)", p.get("quelle", ""))
        if p.get("kat") == "wasser" and m:
            out.setdefault(m[1], set()).add(int(m[2]))
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
            print(f"Overpass {e.code}, neuer Versuch in {30 * (versuch + 1)} s …", file=sys.stderr)
            time.sleep(30 * (versuch + 1))


def bericht(reise, stand, zeilen):
    z = {s: sum(1 for x in zeilen if x["stufe"] == s) for s in STUFEN}
    out = [f"# Wasserstellen laut OpenStreetMap: Datenlage ({reise})", "",
           f"Herkunft: OpenStreetMap-Daten (ODbL), abgefragt am {stand} mit frieda/werkzeuge/wasser_pruefen.py; das sind dieselben Daten, "
           "die Organic Maps zeigt. Eigene Prüfung der Datenlage, keine Aussage über den Zustand vor Ort.", "",
           "„Gut belegt“ heißt: als Trinkwasser eingetragen, keine Warnhinweise, Prüfdatum höchstens "
           f"{GEPRUEFT_JAHRE} Jahre alt. Es heißt nicht, dass die Quelle zur Reisezeit sicher läuft; "
           "Wasserstellen sind veränderlich und vor der Reise nachzuprüfen.", "",
           f"Ergebnis: {z[STUFEN[0]]} gut belegt, {z[STUFEN[1]]} mit Vorbehalt, {z[STUFEN[2]]} unsicher.", ""]
    for eid in dict.fromkeys(x["etappe"] for x in zeilen):
        out += [f"## {eid}", "", "| Stufe | Name / Art | Lage | OSM | Gründe |", "|---|---|---|---|---|"]
        for x in zeilen:
            if x["etappe"] == eid:
                lat, lon = x["lage"]
                out.append(f"| {x['stufe']} | {x['name']} | {lat:.5f}, {lon:.5f} | {x['osm']} (zuletzt bearbeitet {x['bearbeitet']}) "
                           f"| {'; '.join(x['gruende'])} |")
        out.append("")
    return "\n".join(out)


def main(reise):
    rd = WURZEL / "reisen" / reise
    daten = yaml.safe_load((rd / "plan/punkte.yaml").read_text(encoding="utf-8"))
    strecken = daten.get("strecken") or {}
    alle = [p for ps in strecken.values() for p in ps]
    ids = osm_ids(alle)
    if not ids:
        sys.exit("Keine OSM-Wasserpunkte in punkte.yaml.")
    print(f"Frage {sum(map(len, ids.values()))} Wasserpunkte bei OpenStreetMap ab …", file=sys.stderr)
    antwort = abfragen(ids)
    osm = {f"{e['type']}/{e['id']}": e for e in antwort["elements"]}
    heute = datetime.date.today()
    zeilen, weg = [], []
    for eid, ps in strecken.items():
        for p in ps:
            m = re.match(r"^OSM ((?:node|way|relation)/\d+)", p.get("quelle", ""))
            if p.get("kat") != "wasser" or not m:
                continue
            e = osm.get(m[1])
            if not e:
                weg.append(m[1])  # in OSM gelöscht oder umgezogen
                continue
            tags = e.get("tags", {})
            stufe, gruende = bewerte(tags, heute)
            zeilen.append({"etappe": eid, "stufe": stufe, "gruende": gruende, "osm": m[1], "lage": p["lage"],
                           "name": p.get("name") or tags.get("name") or p.get("art", "Wasser"),
                           "bearbeitet": e.get("timestamp", "?")[:10]})
    text = bericht(reise, heute.isoformat(), zeilen)
    if weg:
        text += "\n## In OpenStreetMap nicht mehr vorhanden\n\n" + "\n".join(f"- {w}" for w in weg) + "\n"
    ziel = rd / "inhalt/recherche/wasserstellen-osm.md"
    ziel.write_text(text, encoding="utf-8")
    print(f"{ziel.relative_to(WURZEL)}: " + ", ".join(f"{sum(1 for x in zeilen if x['stufe'] == s)} {s}" for s in STUFEN)
          + (f", {len(weg)} nicht mehr in OSM" if weg else ""))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: engine/.venv/bin/python frieda/werkzeuge/wasser_pruefen.py <reise>")
    main(sys.argv[1])
