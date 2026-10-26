"""GPX-Tracks für die Karte: lesen, vereinfachen, Orte und Punkte an die Tracks heften.

Wird von bauen.py aufgerufen, wenn plan/karte.yaml einen Abschnitt `gpx:` hat
(Strecken-ID -> Datei relativ zur Reise). Die Tracks ersetzen dann die schematischen
Wege aus karte.yaml; Orte rücken an Anfang und Ende ihrer Tracks, Wegpunkte (`punkte`)
an den nächsten Punkt einer Linie. Was keinen Track hat, bleibt schematisch, seine
Endpunkte folgen aber den verschobenen Orten.
"""
import math
import xml.etree.ElementTree as ET

# Toleranz der Vereinfachung in Metern: auf dem Telefon nicht zu sehen, spart 80–90 % der Punkte
TOLERANZ_M = 8
# Weiter als so weit von jeder Linie entfernt wird ein Wegpunkt nicht verschoben
FANG_M = 1500


def lesen(pfad):
    """Alle Trackpunkte (Breite, Länge) aller Segmente einer GPX-Datei, in Reihenfolge."""
    wurzel = ET.parse(pfad).getroot()
    pts = []
    for p in wurzel.iter():
        if p.tag.rsplit("}", 1)[-1] == "trkpt":
            pts.append((float(p.get("lat")), float(p.get("lon"))))
    if not pts:  # manche Dateien enthalten nur eine Route
        for p in wurzel.iter():
            if p.tag.rsplit("}", 1)[-1] == "rtept":
                pts.append((float(p.get("lat")), float(p.get("lon"))))
    return pts


def _xy(p, breite0):
    """Grad -> Meter in einer flachen Näherung um breite0 (genau genug für einige 10 km)."""
    return (p[1] * 111320 * math.cos(math.radians(breite0)), p[0] * 110540)


def vereinfachen(pts, toleranz_m=TOLERANZ_M):
    """Douglas-Peucker, ohne Rekursion (lange Tracks)."""
    if len(pts) < 3:
        return list(pts)
    b0 = pts[0][0]
    xy = [_xy(p, b0) for p in pts]
    behalten = [False] * len(pts)
    behalten[0] = behalten[-1] = True
    stapel = [(0, len(pts) - 1)]
    while stapel:
        a, e = stapel.pop()
        (ax, ay), (ex, ey) = xy[a], xy[e]
        dx, dy = ex - ax, ey - ay
        laenge = math.hypot(dx, dy)
        weit, wo = 0.0, None
        for i in range(a + 1, e):
            px, py = xy[i]
            d = abs(dy * px - dx * py + ex * ay - ey * ax) / laenge if laenge else math.hypot(px - ax, py - ay)
            if d > weit:
                weit, wo = d, i
        if wo is not None and weit > toleranz_m:
            behalten[wo] = True
            stapel += [(a, wo), (wo, e)]
    return [p for p, k in zip(pts, behalten) if k]


def abstand_m(p, q):
    b0 = (p[0] + q[0]) / 2
    (x1, y1), (x2, y2) = _xy(p, b0), _xy(q, b0)
    return math.hypot(x2 - x1, y2 - y1)


def runden(p):
    return [round(p[0], 6), round(p[1], 6)]


def einbauen(k, strecken, lade):
    """Ersetzt in der Karte k (dict aus karte.yaml) die Wege durch GPX-Tracks.

    strecken: Strecken aus der Route (ID -> {von, nach, ...}), für Anfang und Ende.
    lade(rel) -> Liste von Punkten; wirft OSError/ET.ParseError bei Problemen.
    Gibt eine Liste von Fehlermeldungen zurück.
    """
    fehler = []
    wege = k.setdefault("wege", {})
    alt = {oid: tuple(o["lage"]) for oid, o in (k.get("orte") or {}).items() if o.get("lage")}
    neu = {}
    tracks = {}
    for sid, rel in (k.get("gpx") or {}).items():
        try:
            pts = lade(rel)
        except (OSError, ET.ParseError) as e:
            fehler.append(f"gpx: {sid}: {rel} nicht lesbar ({e}).")
            continue
        if len(pts) < 2:
            fehler.append(f"gpx: {sid}: {rel} enthält keinen Track.")
            continue
        linie = [runden(p) for p in vereinfachen(pts)]
        tracks[sid] = linie
        st = strecken.get(sid) or {}
        for oid, p in ((st.get("von"), linie[0]), (st.get("nach"), linie[-1])):
            if oid and oid in alt and oid not in neu:
                neu[oid] = p
    # Orte an die Tracks heften
    for oid, p in neu.items():
        k["orte"][oid]["lage"] = p
    verschoben = {alt[oid]: neu[oid] for oid in neu}
    folgen = lambda w: [list(verschoben.get(tuple(p), p)) for p in w]
    # Wege ohne Track: Punkte, die auf einem verschobenen Ort lagen, ziehen mit
    for art in ("wege", "unmarkiert"):
        for sid, w in list((k.get(art) or {}).items()):
            if art == "wege" and sid in tracks:
                continue
            k[art][sid] = folgen(w)
    for sid, linie in tracks.items():
        wege[sid] = linie
        # Ein schematisch nicht markiertes Stück passt nicht zum Track: dann gilt der ganze Track als markiert
        (k.get("unmarkiert") or {}).pop(sid, None)
    # Wegpunkte an den nächsten Punkt einer Linie (exakt derselbe Punkt, damit die Seite ihn als „auf der Linie“ erkennt)
    alle = [p for w in wege.values() for p in w]
    for pk in k.get("punkte") or []:
        if not pk.get("lage") or not alle:
            continue
        best = min(alle, key=lambda q: abstand_m(pk["lage"], q))
        if abstand_m(pk["lage"], best) <= FANG_M:
            pk["lage"] = list(best)
    return fehler
