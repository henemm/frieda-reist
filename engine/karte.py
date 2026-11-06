"""Automatische Karte aus dem Plan (Epic #225): alles mit Lage kommt auf die Karte, ohne plan/karte.yaml.

Ist der Baustein Karte an und hat die Reise mindestens zwei Punkte mit Lage (Orte, Unterkünfte, Aufenthalte mit
Koordinaten), baut bauen.py daraus die Karte. Sie hat dieselbe Form wie eine handgepflegte Karte aus plan/karte.yaml
(rahmen, kueste, orte, wege), damit die Seite sie gleich zeichnet, und zusätzlich:

- dinge: Unterkünfte und Aufenthalte mit Koordinaten, je mit Art, Stand (plan, alternative, frei) und den Tagen, zu denen
  sie gehören (für Ansichten und Tageskarten),
- legende: Name und Farbe je Art (aus plan/arten.yaml, eine Kartenkategorie gleichen Schlüssels überschreibt sie),
- schematisch: Strecken ohne GPX-Track; die Seite zeichnet sie gestrichelt und nennt sie in der Legende „schematisch“,
- grundkarten: Plan für die Offline-Grundkarte (Rahmen und Zoom nach Fläche, Detailkarten für lange Fahrten; #239).

Die Software kennt dabei keine Art (ADR-0001): Name und Farbe kommen aus der Reise. Alles hier ist eine feste Regel,
keine KI; Koordinaten recherchiert der AI-Client. Fehler lassen den Bau nicht scheitern: der Kartenstatus nennt den Grund.
"""
import math

import routen
import texte

# Mindestens so viele Punkte mit Lage braucht eine automatische Karte (K1)
MIN_PUNKTE = 2
# Rand um die Punkte: Anteil der Spanne, mindestens so viele Grad
RAND = 0.12
RAND_MIN = 0.01
# Offline-Grundkarte (#239, K18): höchste Zoomstufe und höchstens so viele Kacheln je Karte in ihrer höchsten Stufe
# (etwa 30 bis 60 MB je Karte; der Offline-Speicher der App soll nicht volllaufen)
ZOOM_MAX = 15
ZOOM_MIN = 8
KACHELN_MAX = 2500
# Detailkarten langer Fahrten: Punkte, die näher als so viele km beieinander liegen, bilden ein Gebiet; höchstens so viele
DETAIL_ABSTAND_KM = 15
DETAILS_MAX = 6


def ist_lage(w):
    return isinstance(w, (list, tuple)) and len(w) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in w) \
        and -90 <= w[0] <= 90 and -180 <= w[1] <= 180


def punkt_von(d):
    """Koordinaten eines Dings oder Orts (Feld punkt als Aussage {wert, …}) -> [Breite, Länge] oder None."""
    p = (d or {}).get("punkt")
    w = p.get("wert") if isinstance(p, dict) else None
    return [float(w[0]), float(w[1])] if ist_lage(w) else None


def rahmen_aus(punkte, rand=RAND, rand_min=RAND_MIN):
    """Rahmen um Punkte plus Rand -> {nord, sued, west, ost}."""
    b = [p[0] for p in punkte]
    l = [p[1] for p in punkte]
    db = max((max(b) - min(b)) * rand, rand_min)
    dl = max((max(l) - min(l)) * rand, rand_min)
    return {"nord": round(max(b) + db, 4), "sued": round(min(b) - db, 4), "west": round(min(l) - dl, 4), "ost": round(max(l) + dl, 4)}


def _kachel(breite, laenge, z):
    n = 2 ** z
    x = (laenge + 180) / 360 * n
    b = math.radians(max(min(breite, 85.05), -85.05))
    y = (1 - math.asinh(math.tan(b)) / math.pi) / 2 * n
    return x, y


def kacheln(rahmen, z):
    """Zahl der Kacheln eines Rahmens in Zoomstufe z (Web-Mercator)."""
    x0, y0 = _kachel(rahmen["nord"], rahmen["west"], z)
    x1, y1 = _kachel(rahmen["sued"], rahmen["ost"], z)
    return (int(x1) - int(x0) + 1) * (int(y1) - int(y0) + 1)


def zoom_fuer(rahmen):
    """Höchste Zoomstufe (bis ZOOM_MAX), in der der Rahmen höchstens KACHELN_MAX Kacheln hat (K18: Zoom nach Fläche)."""
    for z in range(ZOOM_MAX, ZOOM_MIN - 1, -1):
        if kacheln(rahmen, z) <= KACHELN_MAX:
            return z
    return ZOOM_MIN


def abstand_km(p, q):
    b = math.radians((p[0] + q[0]) / 2)
    return math.hypot((q[1] - p[1]) * 111.32 * math.cos(b), (q[0] - p[0]) * 110.54)


def gebiete(punkte, abstand=DETAIL_ABSTAND_KM):
    """Punkte zu Gebieten zusammenfassen (einfache Kette: liegt ein Punkt nah an einem Punkt des Gebiets, gehört er dazu)."""
    gruppen = []
    for p in punkte:
        nah = [g for g in gruppen if any(abstand_km(p, q) <= abstand for q in g)]
        neu = [p] + [q for g in nah for q in g]
        gruppen = [g for g in gruppen if g not in nah] + [neu]
    return gruppen


def mit_rand(r, anteil=0.15):
    """Rahmen plus Rand je Seite (wie maxBounds der Seite: auf breiten Bildschirmen bleibt neben dem Rahmen keine leere Fläche)."""
    db, dl = (r["nord"] - r["sued"]) * anteil, (r["ost"] - r["west"]) * anteil
    return {"nord": round(r["nord"] + db, 4), "sued": round(r["sued"] - db, 4), "west": round(r["west"] - dl, 4), "ost": round(r["ost"] + dl, 4)}


def grundkarten_plan(rahmen, punkte):
    """Plan der Offline-Grundkarte (#239): die Übersicht (Kartenrahmen mit Rand) in der Zoomstufe nach Fläche; ist sie gröber als
    ZOOM_MAX (lange Fahrt), dazu Detailkarten der Gebiete, in denen Punkte beieinander liegen.
    -> {zoom, rahmen, details: [{name, rahmen, zoom}]}"""
    rahmen = mit_rand(rahmen)
    z = zoom_fuer(rahmen)
    aus = {"rahmen": rahmen, "zoom": z, "details": []}
    if z >= ZOOM_MAX or not punkte:
        return aus
    gs = sorted(gebiete(punkte), key=lambda g: -len(g))[:DETAILS_MAX]
    for i, g in enumerate(sorted(gs, key=lambda g: (min(p[0] for p in g), min(p[1] for p in g))), 1):
        r = rahmen_aus(g, rand=0.2, rand_min=0.03)
        aus["details"].append({"name": f"detail-{i}", "rahmen": r, "zoom": zoom_fuer(r)})
    return aus


def _farbe_name(art, arten, kategorien):
    """Name und Farbe einer Art auf der Karte (K4): aus der Art, eine Kartenkategorie gleichen Schlüssels überschreibt."""
    a = arten.get(art) or {}
    k = kategorien.get(art) or {}
    return {"name": k.get("name") or a.get("name") or art, "farbe": k.get("farbe") or a.get("farbe") or "grau",
            **({"symbol": k.get("symbol") or a.get("symbol")} if k.get("symbol") or a.get("symbol") else {})}


def dinge_bezug(route):
    """Stand und Tage je Unterkunft, Aufenthalt und Ort einer Möglichkeit (#353): plan (an einem Tag des Plans), alternative (nur in einer Option oder an einem
    Tag außerhalb des Plans) oder frei (an keinem Tag, in keiner Option; K7). Tage: Tage des Plans, an denen das Ding steht,
    und die Tage, an denen eine Wahlstelle mit ihm als Option hängt (für Ansichten „Tag mit Alternativen“). Orte (O-…) stehen nur
    darin, wenn sie Möglichkeit einer Wahlstelle sind."""
    stand, tage = {}, {}
    def dazu(did, s, tid=None):
        if stand.get(did) != "plan":
            stand[did] = s
        if tid:
            tage.setdefault(did, [])
            if tid not in tage[did]:
                tage[did].append(tid)
    wahl = {w["id"]: w for w in route.get("wahlstellen") or []}
    for t in route.get("tage") or []:
        for aid in t.get("aufenthalte") or []:
            dazu(aid, "plan", t["id"])
        for vid in t.get("wahlstellen") or []:   # Aufenthalte und Orte in den Möglichkeiten einer Wahlstelle des Tags (#353)
            for o in (wahl.get(vid) or {}).get("optionen") or []:
                for aid in (o.get("aufenthalte") or []) + (o.get("orte") or []):
                    dazu(aid, "plan" if o.get("aktiv") else "alternative", t["id"])
        n = t.get("nacht") or {}
        if n.get("unterkunft"):
            dazu(n["unterkunft"], "plan", t["id"])
        if n.get("wahl") and n["wahl"] in wahl:
            for o in wahl[n["wahl"]]["optionen"]:
                for uid in o.get("unterkuenfte") or []:
                    dazu(uid, "plan" if o.get("aktiv") else "alternative", t["id"])
    # Tag außerhalb des Plans: gehört zu den Tagen, an denen seine Wahlstelle hängt
    tag_an = {}
    for w in wahl.values():
        for o in w["optionen"]:
            for tid in o.get("tage") or []:
                tag_an.setdefault(tid, []).extend(w.get("an") or [])
            for uid in (o.get("unterkuenfte") or []) + (o.get("aufenthalte") or []) + (o.get("orte") or []):
                if stand.get(uid) != "plan":
                    dazu(uid, "alternative")
                for tid in w.get("an") or []:
                    dazu(uid, stand[uid], tid)
    for tid, t in (route.get("weitere_tage") or {}).items():
        for aid in t.get("aufenthalte") or []:
            dazu(aid, "alternative")
            for x in tag_an.get(tid) or []:
                dazu(aid, stand[aid], x)
        n = t.get("nacht") or {}
        if n.get("unterkunft"):
            dazu(n["unterkunft"], "alternative")
            for x in tag_an.get(tid) or []:
                dazu(n["unterkunft"], stand[n["unterkunft"]], x)
    return stand, tage


def ort_lagen(route):
    """Lage je Ort: eigener Punkt, sonst der erste Punkt einer Unterkunft oder eines Aufenthalts an diesem Ort (routen.ort_lagen)."""
    return routen.ort_lagen(route)


def regionen(route):
    """Orte, an denen andere Orte hängen (an: O-…, ADR-0008, Punkt 5): kein Punkt auf der Karte."""
    orte = route.get("orte") or {}
    return {e for k, e in (route.get("eltern") or {}).items() if k in orte and e in orte}


def orte_im_plan(route, stand):
    """Orte, die im Plan vorkommen (ADR-0008, Punkt 5): Station einer Strecke, Anfang oder Ende eines Tags, Ort einer Unterkunft oder
    eines Aufenthalts, der an einem Tag oder in einer Option steht, oder selbst Möglichkeit einer Wahlstelle (#353). Ein Ort ohne
    Verwendung erscheint nicht auf der Übersicht."""
    orte = route.get("orte") or {}
    im = {s.get(k) for s in (route.get("strecken") or {}).values() for k in ("von", "nach")}
    im |= {t.get(k) for t in route.get("tage") or [] for k in ("start_ort", "end_ort")}
    for menge in ("unterkuenfte", "aufenthalte"):
        im |= {d.get("ort") for did, d in (route.get(menge) or {}).items() if stand.get(did, "frei") != "frei"}
    im |= {oid for oid in orte if stand.get(oid, "frei") != "frei"}
    return {o for o in im if o in orte}


def schematische_wege(route, orte):
    """Wege ohne GPX (K8): Stationen in Tagesreihenfolge. Hat ein Tag genau eine Strecke, liegen seine Aufenthalte mit Lage
    zwischen Anfang und Ende (Ladestopp, Rast); sonst die gerade Linie von Ort zu Ort."""
    aufenthalte = route.get("aufenthalte") or {}
    wege = {}
    alle_tage = list(route.get("tage") or []) + list((route.get("weitere_tage") or {}).values())
    for t in alle_tage:
        sids = [s["id"] for s in t.get("strecken") or []]
        for sid in sids:
            if sid in wege:
                continue
            s = (route.get("strecken") or {}).get(sid) or {}
            a, b = orte.get(s.get("von")), orte.get(s.get("nach"))
            if not a or not b:
                continue
            mitte = [punkt_von(aufenthalte.get(x)) for x in t.get("aufenthalte") or []] if len(sids) == 1 else []
            weg = [a, *[p for p in mitte if p], b]
            if len(weg) == 2 and a == b:
                continue
            wege[sid] = weg
    return wege


def auto(route, kategorien=None, gpx_wege=None):
    """Automatische Karte aus dem Plan -> (karte oder None, status).

    route: Routendaten aus routen.py (orte, unterkuenfte, aufenthalte mit punkt, tage, strecken, arten).
    kategorien: Kartenkategorien der Reise (plan/kategorien.yaml); eine Kategorie mit dem Schlüssel einer Art überschreibt
    Name und Farbe der Art. gpx_wege: Strecken-ID -> Linie aus einem GPX-Track (ersetzt die schematische Linie)."""
    kategorien = kategorien or {}
    gpx_wege = gpx_wege or {}
    arten = route.get("arten") or {}
    orte = ort_lagen(route)
    stand, tage = dinge_bezug(route)
    # Übersicht (ADR-0008, Punkt 5): nur Orte des Plans, Regionen ohne Punkt; die Lage aller Orte bleibt für die Linien
    ohne_punkt = regionen(route) | (set(route.get("orte") or {}) - orte_im_plan(route, stand))
    dinge, ohne = [], []
    for oid, o in (route.get("orte") or {}).items():
        if oid not in orte and oid not in ohne_punkt and not o.get("ausserhalb"):
            ohne.append(o.get("name") or oid)
    for menge in ("unterkuenfte", "aufenthalte"):
        for did, d in (route.get(menge) or {}).items():
            if (arten.get(d.get("art")) or {}).get("gruppe"):
                continue   # Kartenpunkte (Art mit gruppe, ADR-0007) stehen auf den Karten der Etappen und des Wissens, nicht auf der Übersicht
            p = punkt_von(d)
            if not p:
                ohne.append(d.get("name") or did)
                continue
            dinge.append({"id": did, "name": d.get("name") or did, "art": d.get("art"), "lage": p,
                          "stand": stand.get(did, "frei"), "tage": tage.get(did, [])})
    punkte = [p for oid, p in orte.items() if oid not in ohne_punkt] + [d["lage"] for d in dinge]
    eindeutig = {tuple(p) for p in punkte}
    status = {"gebaut": False, "art": "auto", "punkte": len(eindeutig), "ohne_lage": ohne}
    if len(eindeutig) < MIN_PUNKTE:
        status["grund"] = "zu_wenig_punkte"
        return None, status
    wege = schematische_wege(route, orte)
    for sid, w in gpx_wege.items():
        if len(w) >= 2:
            wege[sid] = w
    linien = [q for w in wege.values() for q in w]
    rahmen = rahmen_aus(punkte + linien)
    breit = 1.0 + (rahmen["ost"] - rahmen["west"]) + (rahmen["nord"] - rahmen["sued"])
    k = {
        "auto": True,
        "rahmen": rahmen,
        # Land als großes Rechteck (ohne Grundkarte zeichnet die Seite es als Hintergrund, wie bei der Beispielreise)
        "kueste": [[rahmen["nord"] + breit, rahmen["west"] - breit], [rahmen["nord"] + breit, rahmen["ost"] + breit],
                   [rahmen["sued"] - breit, rahmen["ost"] + breit], [rahmen["sued"] - breit, rahmen["west"] - breit]],
        "orte": {oid: {"lage": p, **({"punkt": False} if oid in ohne_punkt else {})} for oid, p in orte.items()},
        "wege": wege,
        "schematisch": sorted(sid for sid in wege if sid not in gpx_wege),
        "linien": "alle",
        "dinge": dinge,
        "legende": {a: _farbe_name(a, arten, kategorien) for a in dict.fromkeys(d["art"] for d in dinge if d.get("art"))},
        "grundkarten": grundkarten_plan(rahmen, punkte),
    }
    status["gebaut"] = True
    return k, status


# Höchstens so viele Einträge ohne Lage nennt der Kartenstatus mit Namen, dahinter die Zahl der übrigen
OHNE_LAGE_NAMEN = 12


def status_satz(st):
    """Kartenstatus in Worten (K11, overview und setting_set): gebaut oder nicht, Grund, Zahl der Punkte, Einträge ohne Lage
    (mit Namen, K3). -> texte.Satz (in jeder Sprache lesbar) oder None ohne Status."""
    if not st:
        return None
    if st.get("gebaut"):
        s = texte.satz("konnektor.karte.gebaut_" + ("hand" if st.get("art") == "hand" else "auto"), n=st.get("punkte", 0))
    else:
        s = texte.satz("konnektor.karte.nicht_gebaut." + (st.get("grund") or "unbekannt"), n=st.get("punkte", 0))
        if st.get("meldungen"):
            s = s + " " + texte.Satz.verbinden(st["meldungen"][:3], " ")
    ohne = st.get("ohne_lage") or []
    if ohne:
        namen = ", ".join(ohne[:OHNE_LAGE_NAMEN]) + (f" (+{len(ohne) - OHNE_LAGE_NAMEN})" if len(ohne) > OHNE_LAGE_NAMEN else "")
        s = s + " " + texte.satz("konnektor.karte.ohne_lage", n=len(ohne), namen=namen)
    return s
