"""Routenmodell: Bausteine (Orte, Strecken, Unterkünfte, Tage) und Wahlstellen mit Optionen.

Eine Reise beschreibt in plan/routen.yaml alle Möglichkeiten auf einmal. Wahlstellen (V-01 …)
sitzen an jeder Ebene: ganze Route, Reiseteil, Strecke eines Tages, Unterkunft. Jede Option hat
einen Verlauf (vorgeschlagen, favorisiert, gewählt, verworfen, ersetzt). Der aktuelle Plan ist je
Wahlstelle die gewählte Option, sonst die favorisierte, sonst die erste noch gültige.

Unterschieden wird:
  Fehler     – das Modell ist kaputt (toter Verweis, doppelte ID, offene Wahl ohne F-Frage).
               Die Seite wird nicht gebaut.
  Warnungen  – der Plan geht (noch) nicht auf (Lücke zwischen Orten, Fixpunkt verfehlt).
               In der Planung ein normaler Zwischenstand; die Seite zeigt sie an.

Merkmale: Jede Wahlstelle hat einen Bereich (unterkunft, strecke, route, allgemein). Die Grundliste in
engine/merkmale.yaml sagt, welche Merkmale eine Option dort braucht; die Reise (routen.yaml „merkmale:“) und die
Wahlstelle („merkmale:“) können ergänzen. Werte stehen an der Option, bei Unterkünften an der Unterkunft (U-…).
Was fehlt, zeigt die Seite. Standard und Ablauf: docs/alternativen.md.

Hintergrund und Entscheidung: GitHub-Issue #9.
"""
import datetime
import re
from pathlib import Path

STATUS = ("vorgeschlagen", "favorisiert", "gewaehlt", "verworfen", "ersetzt")
NUR_ENTSCHEIDER = {"gewaehlt", "verworfen", "ersetzt"}
UNGUELTIG = {"verworfen", "ersetzt"}
ARTEN = {"planung", "unterwegs"}
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MUSTER = {"ort": r"O-\d+", "strecke": r"E-\d+[A-Za-z]?", "unterkunft": r"U-\d+",
          "tag": r"T-\d+", "wahl": r"V-\d+", "option": r"V-\d+\.[a-z]+", "wissen": r"W-\d+"}
BEREICHE = ("unterkunft", "strecke", "route", "allgemein")
# Eine Wahlstelle hat einen Bereich oder eine Art: die vier Grundbereiche, dazu jede Art, die die Grundliste
# (engine/merkmale.yaml) oder die Reise unter „merkmale:“ kennt (Fähre, Flug, Bahn, Essen, Erlebnis …).
# Ding-Formen: Aufenthalt (unterkunft, essen, erlebnis), Bewegung (strecke, faehre, flug, bahn, bus, mietwagen), Folge (route).
ART_MUSTER = r"[a-z][a-z0-9_]*"
# Übernachtungskategorien (generisch, für Karte, Legende, Vergleich). typ bleibt die freie Bezeichnung der Reise;
# fehlt kategorie, wird sie aus typ abgeleitet (TYP_KATEGORIE, klein geschrieben), sonst „sonstige“.
KATEGORIEN = {"hotel": "Hotel", "gasthaus": "Gasthaus", "ferienwohnung": "Ferienwohnung", "huette": "Hütte",
              "herberge": "Herberge", "camping": "Camping", "unterwegs": "Unterwegs", "privat": "Privat",
              "sonstige": "Sonstige"}
TYP_KATEGORIE = {
    **dict.fromkeys(("hotel", "stadthotel", "businesshotel", "designhotel", "landhotel", "resort", "lodge",
                     "berglodge", "motel", "onsen-hotel", "kapselhotel"), "hotel"),
    **dict.fromkeys(("gasthaus", "gasthof", "pension", "b&b", "bed & breakfast", "guesthouse", "ryokan", "minshuku",
                     "shukubō", "shukubo", "agriturismo", "finca", "landgasthof", "inn"), "gasthaus"),
    **dict.fromkeys(("ferienwohnung", "apartment", "wohnung", "ferienhaus", "machiya", "kominka", "airbnb"),
                    "ferienwohnung"),
    **dict.fromkeys(("hütte", "huette", "berghütte", "alpenvereinshütte", "refugi", "refugio", "refuge", "yamagoya",
                     "biwakschachtel"), "huette"),
    **dict.fromkeys(("herberge", "wanderherberge", "jugendherberge", "pilgerherberge", "hostel", "albergue",
                     "kokumin-shukusha"), "herberge"),
    **dict.fromkeys(("camping", "zelt", "zeltplatz", "wohnmobil", "biwak"), "camping"),
    **dict.fromkeys(("nachtzug", "schlafwagen", "fähre", "nachtfähre", "flug", "nachtbus"), "unterwegs"),
    **dict.fromkeys(("privat", "freunde", "familie", "bei freunden"), "privat"),
}


def kategorie(eintrag):
    """Kategorie einer Unterkunft oder Nacht: ausdrücklich, aus typ abgeleitet, „unterwegs“ an Bord, sonst „sonstige“."""
    if eintrag.get("kategorie"):
        return eintrag["kategorie"]
    if eintrag.get("an_bord"):
        return "unterwegs"
    return TYP_KATEGORIE.get(str(eintrag.get("typ") or "").strip().lower(), "sonstige")
TYPEN = {"text", "geld", "zahl", "auswahl"}
# Stufe eines Merkmals je Reise (ADR-0001, Paket O-0): pflicht und empfohlen zählen als „Fehlt noch“ und werden gemahnt,
# angeboten wird nur gezeigt, wenn ein Wert da ist, aus gilt für diese Reise nicht (kein Fehlt, keine Mahnung, kein Wächter).
# Ohne Angabe gilt empfohlen. Eine Reise setzt die Stufe eines Grundlisten-Merkmals unter merkmale: nur mit {stufe: …},
# eine Wahlstelle kann sie für sich wieder ändern. Die Stufe darf je Unterkunftstyp verschieden sein:
# stufe: {"*": aus, refugi: empfohlen} (Schlüssel: typ der Unterkunft, klein geschrieben; „*“ für alle übrigen).
STUFEN = ("pflicht", "empfohlen", "angeboten", "aus")
DEF_FELDER = {"name", "typ", "werte", "veraenderlich", "auto", "hilfe", "frage", "einheit", "stufe"}


def stufe_von(d, typ=None):
    """Stufe eines Merkmals für ein Ding mit diesem typ (Unterkunft) oder ohne (None: „*“)."""
    s = d.get("stufe", "empfohlen")
    if isinstance(s, dict):
        return s.get(str(typ or "").strip().lower(), s.get("*", "empfohlen"))
    return s


def zaehlt(d, typ=None):
    """Zählt das Merkmal als Lücke (Fehlt noch, Mahnung)? Nur pflicht und empfohlen, nie berechnete."""
    return not d.get("auto") and stufe_von(d, typ) in ("pflicht", "empfohlen")


def stufe_fehler(s):
    """Prüft eine Stufen-Angabe -> Fehlertext oder None."""
    if isinstance(s, dict):
        if not s or any(not re.fullmatch(r"\*|[a-z][a-z0-9_]*", str(k)) for k in s) or any(v not in STUFEN for v in s.values()):
            return f"stufe je Typ muss {{\"*\": …, <typ>: …}} mit Werten {', '.join(STUFEN)} sein."
        return None
    return None if s in STUFEN else f"stufe muss {', '.join(STUFEN)} sein."
WERT_FELDER = {"wert", "quelle", "geprueft", "notiz", "gilt"}
GRUNDLISTE = Path(__file__).with_name("merkmale.yaml")


def grundliste():
    import yaml
    return yaml.safe_load(GRUNDLISTE.read_text(encoding="utf-8")) or {}


def dauer(m):
    return f"{m // 60}:{m % 60:02d} h"


def gilt_am(m, datum):
    """Der Wert eines Merkmals für ein Datum (ISO-Text): der Eintrag mit passendem „gilt“, sonst der ohne Datum, sonst None.
    m: ein Wert aus Option["merkmale"] (mit „je_datum“, wenn es Werte je Nacht gibt)."""
    if not m:
        return None
    for e in m.get("je_datum") or []:
        if datum in e["gilt"]:
            return e
    return None if m.get("gilt") else m


def ist(art, wert):
    return isinstance(wert, str) and re.fullmatch(MUSTER[art], wert) is not None


def zahl(text):
    """'15,9 km' -> 15.9, 'ca. 290' -> 290.0, sonst None."""
    m = re.search(r"\d+(?:[.,]\d+)?", str(text or ""))
    return float(m.group(0).replace(",", ".")) if m else None


def minuten(text):
    """'5:00 h' -> 300, 'ca. 4:00' -> 240, '2 h' -> 120."""
    t = str(text or "")
    m = re.search(r"(\d+):(\d{2})", t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    z = zahl(t)
    return round(z * 60) if z is not None else None


def kennwerte(k):
    """Kennzahlen einer Strecke (Schlüssel wie im Dossier) -> Zahlen für Summen."""
    k = k or {}

    def such(*namen):
        for n in k:
            if any(n.lower().startswith(x) for x in namen):
                return k[n]
        return None
    return {"min": minuten(such("gehzeit", "dauer")), "auf": zahl(such("aufstieg")),
            "ab": zahl(such("abstieg")), "km": zahl(such("länge", "km"))}


def verhalten_anwenden(route, v):
    """Status der Reise wirkt auf das fertige Routenmodell (docs/produkt.md, Paket B). v: reise.verhalten(status).
    idee ohne Warnungen; ab fest werden offene Planungs-Wahlstellen und ungeprüfte veränderliche Angaben der aktiven
    Optionen zur Mahnung (route["mahnungen"], Liste {bezug, text}). Der Plan bleibt vollständig, nichts wird versteckt."""
    if not route:
        return route
    if not v.get("warnungen"):
        route["warnungen"] = []
    mahnungen = []
    if v.get("mahnung_planung"):
        for w in route.get("wahlstellen") or []:
            gueltig = [o for o in w["optionen"] if o["status"] not in UNGUELTIG]
            if w.get("art") == "planung" and w["offen"] and len(gueltig) > 1:
                mahnungen.append({"bezug": w["id"], "text": f"{w['id']} {w['titel']}: noch offen, obwohl die Reise fest ist "
                                  f"({len(gueltig)} Kandidaten). Bitte entscheiden."})
            for o in w["optionen"]:
                if o["aktiv"]:
                    namen = {k["id"]: k["name"] for k in w["kriterien"] if stufe_von(k) != "aus"}
                    ung = [namen[k] for k, m in o["merkmale"].items() if m.get("ungeprueft") and k in namen]
                    if ung:
                        mahnungen.append({"bezug": o["id"], "text": f"{o['id']} {o['titel']}: {', '.join(ung)} "
                                          "ohne Prüfdatum. Veränderliche Angaben bitte nachschlagen und mit Datum eintragen."})
        defs = {k["id"]: k for k in (route.get("merkmale") or {}).get("unterkunft") or []}
        for uid, u in (route.get("unterkuenfte") or {}).items():
            ung = [k for k, m in (u.get("merkmale") or {}).items()
                   if m.get("ungeprueft") and stufe_von(defs.get(k, {}), u.get("typ")) != "aus"]
            if ung and u.get("naechte"):
                mahnungen.append({"bezug": uid, "text": f"{uid} {u.get('name')}: {', '.join(ung)} ohne Prüfdatum."})
    route["mahnungen"] = mahnungen
    return route


class Routen:
    def __init__(self, roh, etappen, fragen, fehler, id_anlegen, quelle="plan/routen.yaml", zwang=None, grund=None,
                 entscheider=None, wissen=None):
        """roh: geladenes YAML. etappen: {E-ID: Etappe aus dem Dossier}. fragen: {F-ID: Status-Text}.
        entscheider: Namen, die gewaehlt/verworfen/ersetzt setzen dürfen (Organisator:innen aus reise.yaml); None: aus dem YAML.
        zwang: {V-ID: Option-ID} – für benannte Pläne; erzwingt eine Option, auch eine verworfene.
        grund: Grundliste der Merkmale (Standard: engine/merkmale.yaml).
        wissen: bekannte W-IDs (Abschnitte wie Essen, Ausflug, Praxis), an denen eine Wahlstelle hängen darf; None: ungeprüft."""
        self.r = roh or {}
        self.grund = grundliste() if grund is None else grund
        self.katalog = {}         # Bereich -> {Merkmal: Definition}, Grundliste plus Reise
        self.kriterien = {}       # V-ID -> (Bereich, {Merkmal: Definition})
        self.mk_option = {}       # V-01.a -> {Merkmal: Wert}
        self.mk_unterkunft = {}   # U-01 -> {Merkmal: Wert}
        self.mk_strecke = {}      # E-01 -> {Merkmal: Wert} (Bewegungen: Fähre, Flug, Bahn …)
        self.bereiche = tuple(BEREICHE) + tuple(k for k in (self.grund if isinstance(self.grund, dict) else {})
                                                if k not in BEREICHE and isinstance(k, str))
        self.etappen = etappen
        self.fragen = fragen
        self.fehler = fehler
        self.id_anlegen = id_anlegen
        self.q = quelle
        self.warnungen = []
        self.entscheider = set(self.r.get("entscheider", []) if entscheider is None else entscheider)
        self.orte = self.r.get("orte") or {}
        self.strecken = self.r.get("strecken") or {}
        self.unterkuenfte = self.r.get("unterkuenfte") or {}
        self.tage = self.r.get("tage") or {}
        self.wahl = self.r.get("wahlstellen") or {}
        self.wissen = wissen
        self.option = {}          # V-01.a -> (V-01, Option)
        self.auswahl = {}         # V-01 -> aktive Option-ID
        self.tag_benutzt = {}     # T-ID -> Fundstelle
        self.zwang = zwang or {}
        self.erfordert = {}       # V-01.a -> [Option-IDs], die im Plan stehen müssen
        self.schliesst = {}       # V-01.a -> {Option-IDs}, die nicht zugleich im Plan stehen dürfen (beidseitig)
        self.grenzen = {}         # V-ID -> (Index erster Tag, Index Tag danach) im aktuellen Plan
        self.im_plan = None       # Option-IDs, die der aktuelle Plan erreicht (nach bauen)
        self.plan_tage = []
        self.ist_plan = zwang is not None   # Unterlauf für einen benannten Plan: keine Pläne darin

    # ---------- Hilfen ----------
    def warne(self, bezug, text):
        w = {"bezug": bezug, "text": text}
        if w not in self.warnungen:
            self.warnungen.append(w)

    def fehl(self, text):
        self.fehler.append(f"{self.q}: {text}")

    def strecke(self, sid):
        """Strecke mit Titel und Kennzahlen; Dossier-Etappen werden um von/nach ergänzt."""
        s = dict(self.strecken.get(sid) or {})
        e = self.etappen.get(sid)
        if e:
            s.setdefault("titel", e["titel"])
            s.setdefault("kennzahlen", e.get("kennzahlen", {}))
            s["dossier"] = True
        return s

    def status(self, opt):
        v = opt.get("verlauf") or []
        return v[-1].get("status", "vorgeschlagen") if v else "vorgeschlagen"

    def ort_name(self, oid):
        return (self.orte.get(oid) or {}).get("name", oid)

    # ---------- Bausteine prüfen ----------
    def bausteine(self):
        for art, menge in (("ort", self.orte), ("strecke", self.strecken), ("unterkunft", self.unterkuenfte),
                           ("tag", self.tage), ("wahl", self.wahl)):
            for i in menge:
                if not ist(art, i):
                    self.fehl(f"„{i}“ ist keine gültige ID für {art}.")
        for oid in self.orte:
            self.id_anlegen(oid, self.q)
        for sid, s in self.strecken.items():
            if sid not in self.etappen:
                self.id_anlegen(sid, self.q)
                if not s.get("titel"):
                    self.fehl(f"Strecke {sid} braucht einen Titel (sie steht nicht im Etappen-Dossier).")
            for k in ("von", "nach"):
                if s.get(k) and s[k] not in self.orte:
                    self.fehl(f"Strecke {sid}: Ort {s[k]} gibt es nicht.")
            z = s.get("zweig_von")
            if z and z not in self.strecken and z not in self.etappen:
                self.fehl(f"Strecke {sid}: zweig_von {z} gibt es nicht.")
        for uid, u in self.unterkuenfte.items():
            self.id_anlegen(uid, self.q)
            if u.get("ort") not in self.orte:
                self.fehl(f"Unterkunft {uid}: Ort {u.get('ort')} gibt es nicht.")
            if u.get("frage") and u["frage"] not in self.fragen:
                self.fehl(f"Unterkunft {uid}: Frage {u['frage']} gibt es nicht.")
            if u.get("kategorie") and u["kategorie"] not in KATEGORIEN:
                self.fehl(f"Unterkunft {uid}: kategorie muss {', '.join(KATEGORIEN)} sein.")
        for tid in self.tage:
            self.id_anlegen(tid, self.q)
        for vid, w in self.wahl.items():
            self.id_anlegen(vid, self.q)
            if w.get("art") not in ARTEN:
                self.fehl(f"Wahlstelle {vid}: art muss planung oder unterwegs sein.")
            if w.get("frage") and w["frage"] not in self.fragen:
                self.fehl(f"Wahlstelle {vid}: Frage {w['frage']} gibt es nicht.")
            opts = w.get("optionen") or []
            if not opts:
                self.fehl(f"Wahlstelle {vid} hat keine Optionen.")
            self.an_pruefen(vid, w)
            for o in opts:
                oid = o.get("id", "")
                if not ist("option", oid) or not oid.startswith(vid + "."):
                    self.fehl(f"Wahlstelle {vid}: Option „{oid}“ muss {vid}.a, {vid}.b … heißen.")
                    continue
                self.id_anlegen(oid, self.q)
                self.option[oid] = (vid, o)
                self.verlauf_pruefen(oid, o)
            self.waehle(vid, w)
        self.regeln_pruefen()
        self.merkmale_pruefen()

    def an_pruefen(self, vid, w):
        """„an:“ nennt die IDs, an denen die Wahlstelle hängt: Tag, Strecke, Unterkunft, Ort, Wahlstelle oder ein Abschnitt
        des Wissens (W-…, z. B. Essen, Ausflug). Jedes Element kann so Alternativen tragen (28.10.2026)."""
        an = w.get("an")
        if an is None:
            return
        if not isinstance(an, list):
            self.fehl(f"Wahlstelle {vid}: an muss eine Liste von IDs sein.")
            return
        for x in an:
            for art, menge in (("tag", self.tage), ("strecke", {**self.etappen, **self.strecken}),
                               ("unterkunft", self.unterkuenfte), ("ort", self.orte), ("wahl", self.wahl),
                               ("wissen", self.wissen)):
                if ist(art, x):
                    if menge is not None and x not in menge:
                        self.fehl(f"Wahlstelle {vid}: an {x} gibt es nicht.")
                    break
            else:
                self.fehl(f"Wahlstelle {vid}: an „{x}“ ist weder Tag, Strecke, Unterkunft, Ort, Wahlstelle noch Abschnitt (W-…).")

    def regeln_pruefen(self):
        """Voraussetzungen zwischen Optionen verschiedener Wahlstellen (Paket 4, #18): erfordert (diese Option geht nur
        zusammen mit jener) und schliesst_aus (nie beide zugleich; gilt in beide Richtungen)."""
        for oid, (vid, o) in self.option.items():
            gesehen = {}
            for feld in ("erfordert", "schliesst_aus"):
                liste = o.get(feld)
                if liste is None:
                    continue
                if not isinstance(liste, list):
                    self.fehl(f"{oid}: {feld} muss eine Liste von Optionen sein (z. B. [V-02.b]).")
                    continue
                gut = []
                for x in liste:
                    if x not in self.option:
                        self.fehl(f"{oid}: {feld} {x} – diese Option gibt es nicht.")
                    elif self.option[x][0] == vid:
                        self.fehl(f"{oid}: {feld} {x} gehört zur selben Wahlstelle {vid}; dort gilt ohnehin nur eine Option.")
                    elif x in gesehen:
                        self.fehl(f"{oid}: {x} steht unter {gesehen[x]} und {feld}.")
                    else:
                        gesehen[x] = feld
                        gut.append(x)
                if feld == "erfordert":
                    je = {}
                    for x in gut:
                        je.setdefault(self.option[x][0], []).append(x)
                    for v, xs in je.items():
                        if len(xs) > 1:
                            self.fehl(f"{oid}: erfordert {', '.join(xs)} – von {v} kann nur eine Option im Plan stehen.")
                    self.erfordert[oid] = gut
                    if self.status(o) not in UNGUELTIG:
                        for x in gut:
                            if self.status(self.option[x][1]) in UNGUELTIG:
                                self.warne(oid, f"{oid} setzt {x} voraus, aber {x} ist {self.status(self.option[x][1])}.")
                else:
                    for x in gut:
                        self.schliesst.setdefault(oid, set()).add(x)
                        self.schliesst.setdefault(x, set()).add(oid)

    def regeln_im_plan(self, tage, orte):
        """Welche Optionen der aktuelle Plan erreicht, und ob er die Voraussetzungen erfüllt. Erreicht ist eine Wahlstelle,
        wenn die Folge durch sie läuft, ein Tag im Plan sie nennt (Strecke, Nacht, unterwegs) oder ihr „an“ auf etwas
        im Plan zeigt. Die Auswahl allein reicht nicht: Jede Wahlstelle hat eine, auch wenn der Plan nie hinkommt."""
        erreicht = set(self.grenzen)
        for t in tage:
            erreicht |= set(t["wahlstellen"])
            if t["nacht"] and t["nacht"].get("wahl"):
                erreicht.add(t["nacht"]["wahl"])
        im_plan = {t["id"] for t in tage} | {s["id"] for t in tage for s in t["strecken"]} | set(orte) \
            | {t["nacht"]["unterkunft"] for t in tage if t["nacht"] and t["nacht"].get("unterkunft")}
        neu = True
        while neu:
            neu = False
            for vid, w in self.wahl.items():
                if vid not in erreicht and any(x in im_plan or x in erreicht for x in w.get("an") or []
                                               if isinstance(x, str)):
                    erreicht.add(vid)
                    neu = True
        self.im_plan = {self.auswahl[v] for v in erreicht if v in self.auswahl}
        titel = lambda x: f"{x} „{self.option[x][1].get('titel', x)}“"
        for oid in sorted(self.im_plan):
            for x in self.erfordert.get(oid, []):
                if x in self.im_plan:
                    continue
                vx = self.option[x][0]
                wo = f"im Plan ist {self.auswahl[vx]}" if vx in erreicht and vx in self.auswahl else f"{vx} liegt nicht im Plan"
                self.warne("plan", f"{titel(oid)} setzt {titel(x)} voraus, {wo}.")
            for x in sorted(self.schliesst.get(oid, ())):
                if x in self.im_plan and oid < x:
                    self.warne("plan", f"{titel(oid)} und {titel(x)} schließen sich aus, stehen aber beide im Plan.")

    def regel_aus(self, oid):
        """Voraussetzungen einer Option für die Seite: mit Titel, ob sie im Plan stehen und ob sie noch gelten."""
        def zeile(x):
            v, o = self.option[x]
            return {"id": x, "titel": o.get("titel", x), "wahl": v, "im_plan": x in (self.im_plan or ()),
                    "gueltig": self.status(o) not in UNGUELTIG}
        return {"im_plan": oid in (self.im_plan or ()), "erfordert": [zeile(x) for x in self.erfordert.get(oid, [])],
                "schliesst_aus": [zeile(x) for x in sorted(self.schliesst.get(oid, ()))]}

    def verlauf_pruefen(self, oid, o):
        vorher = None
        for e in o.get("verlauf") or []:
            st = e.get("status")
            if st not in STATUS:
                self.fehl(f"{oid}: Status „{st}“ unbekannt (erlaubt: {', '.join(STATUS)}).")
            if st in NUR_ENTSCHEIDER and e.get("wer") not in self.entscheider:
                self.fehl(f"{oid}: „{st}“ darf nur {', '.join(sorted(self.entscheider)) or 'der Entscheider'} setzen "
                          f"(steht: {e.get('wer')}).")
            if st == "favorisiert" and e.get("wer") not in self.entscheider and not e.get("grund"):
                self.fehl(f"{oid}: „favorisiert“ von {e.get('wer') or 'Claude'} braucht eine Begründung (grund).")
            if st == "ersetzt" and not e.get("durch"):
                self.fehl(f"{oid}: „ersetzt“ braucht „durch“ (die neue Option).")
            d = e.get("datum")
            if not isinstance(d, datetime.date):
                self.fehl(f"{oid}: Verlaufseintrag ohne gültiges Datum (JJJJ-MM-TT).")
            elif vorher and d < vorher:
                self.fehl(f"{oid}: Verlauf ist nicht zeitlich sortiert.")
            else:
                vorher = d

    # ---------- Merkmale ----------
    def definitionen(self, wo, roh, bereich, grund=False):
        """Merkmal-Definitionen prüfen -> {Merkmal: Definition}."""
        aus = {}
        if not isinstance(roh, dict):
            self.fehl(f"{wo}: merkmale muss eine Liste „name: {{…}}“ sein.")
            return aus
        for k, d in roh.items():
            if not re.fullmatch(r"[a-z][a-z0-9_]*", str(k)):
                self.fehl(f"{wo}: Merkmal „{k}“: nur Kleinbuchstaben, Ziffern und _ (z. B. preis, onsen).")
                continue
            if isinstance(d, dict) and set(d) == {"stufe"} and k in self.katalog.get(bereich, {}):
                # nur die Stufe eines bekannten Merkmals ändern (Reise: aus; Wahlstelle: wieder empfohlen)
                if stufe_fehler(d["stufe"]):
                    self.fehl(f"{wo}: Merkmal {k}: {stufe_fehler(d['stufe'])}")
                    continue
                aus[k] = {**self.katalog[bereich][k], "stufe": d["stufe"]}
                continue
            if not isinstance(d, dict) or not d.get("name"):
                self.fehl(f"{wo}: Merkmal {k} braucht einen Namen (name: …).")
                continue
            if set(d) - DEF_FELDER:
                self.fehl(f"{wo}: Merkmal {k}: unbekannte Felder {', '.join(sorted(set(d) - DEF_FELDER))}.")
            if d.get("stufe") and stufe_fehler(d["stufe"]):
                self.fehl(f"{wo}: Merkmal {k}: {stufe_fehler(d['stufe'])}")
            typ = d.get("typ", "text")
            if typ not in TYPEN:
                self.fehl(f"{wo}: Merkmal {k}: typ muss {', '.join(sorted(TYPEN))} sein.")
            if typ == "auswahl" and not (isinstance(d.get("werte"), list) and d["werte"]):
                self.fehl(f"{wo}: Merkmal {k} ist eine Auswahl und braucht werte: […].")
            if d.get("auto") and not grund:
                self.fehl(f"{wo}: Merkmal {k}: auto gibt es nur in der Grundliste (engine/merkmale.yaml).")
            if k in self.katalog.get(bereich, {}) and not grund:
                self.fehl(f"{wo}: Merkmal {k} gibt es für {bereich} schon.")
            aus[k] = {"name": d["name"], "typ": typ, **{f: d[f] for f in ("werte", "veraenderlich", "auto", "hilfe",
                                                                          "frage", "einheit", "stufe") if d.get(f)}}
        return aus

    def bereich(self, w):
        b = w.get("bereich")
        if b:
            return b
        opts = w.get("optionen") or []
        for feld, name in (("unterkuenfte", "unterkunft"), ("strecken", "strecke"), ("folge", "route")):
            if any(o.get(feld) for o in opts):
                return self.art_der_strecken(opts) if name == "strecke" else name
        return "allgemein"

    def art_der_strecken(self, opts):
        """Bereich für Optionen mit Strecken: die gemeinsame Art (faehre, flug …), wenn die Grundliste sie kennt, sonst strecke."""
        arten = set()
        for o in opts:
            for sid in o.get("strecken") or []:
                a = (self.strecken.get(sid) or {}).get("art", "wandern")
                arten.add(a if isinstance(a, str) else None)
        if len(arten) == 1:
            a = next(iter(arten))
            if a and a != "wandern" and a in self.bereiche:
                return a
        return "strecke"

    def werte(self, wo, roh, kriterien):
        """Werte einer Option, Unterkunft oder Strecke prüfen -> {Merkmal: {wert, quelle, geprueft, notiz, ungeprueft}}.
        Ein Wert kann je Nacht oder Datum verschieden sein: eine Liste von Einträgen, jeder mit „gilt“ (Datum oder Liste
        von Daten); ein Eintrag ohne „gilt“ ist der Wert für alle übrigen Tage. Das Ergebnis trägt dann „je_datum“."""
        aus = {}
        if roh is None:
            return aus
        if not isinstance(roh, dict):
            self.fehl(f"{wo}: merkmale muss „merkmal: wert“ sein.")
            return aus
        for k, v in roh.items():
            d = kriterien.get(k)
            if d is None:
                self.fehl(f"{wo}: Merkmal „{k}“ gibt es hier nicht (bekannt: {', '.join(kriterien) or 'keine'}). "
                          f"Ein neues Merkmal unter merkmale: in routen.yaml oder an der Wahlstelle anlegen.")
                continue
            if d.get("auto"):
                self.fehl(f"{wo}: {d['name']} wird aus dem Plan berechnet und nicht eingetragen.")
                continue
            eintraege = [self.wert_eintrag(wo, k, d, x) for x in (v if isinstance(v, list) else [v])]
            eintraege = [x for x in eintraege if x]
            if not eintraege:
                continue
            ohne = [x for x in eintraege if not x.get("gilt")]
            if len(ohne) > 1:
                self.fehl(f"{wo}: {k} hat mehrere Werte ohne „gilt“; je Datum angeben.")
            tage = [t for x in eintraege for t in x.get("gilt") or []]
            if len(tage) != len(set(tage)):
                self.fehl(f"{wo}: {k}: ein Datum steht in zwei Werten.")
            aus[k] = dict(ohne[0] if ohne else eintraege[0])
            if any(x.get("gilt") for x in eintraege):
                aus[k]["je_datum"] = [x for x in eintraege if x.get("gilt")]
        return aus

    def wert_eintrag(self, wo, k, d, v):
        """Ein Wert eines Merkmals prüfen -> Eintrag oder None (bei Fehlern, die schon gemeldet sind)."""
        e = dict(v) if isinstance(v, dict) else {"wert": v}
        if set(e) - WERT_FELDER:
            self.fehl(f"{wo}: {k}: unbekannte Felder {', '.join(sorted(set(e) - WERT_FELDER))} "
                      f"(erlaubt: {', '.join(sorted(WERT_FELDER))}).")
        w = e.get("wert")
        w = {True: "ja", False: "nein"}.get(w, w) if isinstance(w, bool) else w
        if w is None or str(w).strip() == "":
            self.fehl(f"{wo}: {k} ohne Wert. Fehlt der Wert, das Merkmal weglassen.")
            return None
        if d["typ"] == "auswahl" and w not in d.get("werte", []):
            self.fehl(f"{wo}: {k} = „{w}“, erlaubt: {', '.join(map(str, d['werte']))}.")
        if d["typ"] == "zahl" and not isinstance(w, (int, float)):
            self.fehl(f"{wo}: {k} muss eine Zahl sein.")
        g = e.get("geprueft")
        if g is not None and not isinstance(g, datetime.date):
            self.fehl(f"{wo}: {k}: geprueft muss ein Datum sein (JJJJ-MM-TT).")
            g = None
        gilt = e.get("gilt")
        if gilt is not None:
            liste = gilt if isinstance(gilt, list) else [gilt]
            if not liste or not all(isinstance(x, datetime.date) for x in liste):
                self.fehl(f"{wo}: {k}: gilt muss ein Datum oder eine Liste von Daten sein (JJJJ-MM-TT).")
                gilt = None
            else:
                gilt = [x.isoformat() for x in liste]
        out = {"wert": str(w), "quelle": e.get("quelle"), "notiz": e.get("notiz"),
               "geprueft": g.isoformat() if g else None,
               "ungeprueft": bool(d.get("veraenderlich")) and g is None}
        if gilt:
            out["gilt"] = gilt
        return out

    def merkmale_pruefen(self):
        if not isinstance(self.grund, dict):
            self.grund = {}
        for b in self.bereiche:
            self.katalog[b] = self.definitionen(f"engine/merkmale.yaml {b}", self.grund.get(b) or {}, b, grund=True)
        eigen = self.r.get("merkmale") or {}
        for b, roh in (eigen.items() if isinstance(eigen, dict) else []):
            if b not in self.bereiche:
                # eine Reise darf eine neue Art anlegen (z. B. restaurant), wenn sie ihre Merkmale gleich mitbringt
                if not (re.fullmatch(ART_MUSTER, str(b)) and isinstance(roh, dict) and roh):
                    self.fehl(f"merkmale: Bereich „{b}“ gibt es nicht (bekannt: {', '.join(self.bereiche)}). Eine neue Art "
                              f"braucht einen Namen aus Kleinbuchstaben und mindestens ein Merkmal.")
                    continue
                self.bereiche += (b,)
                self.katalog[b] = {}
            self.katalog[b].update(self.definitionen(f"merkmale.{b}", roh or {}, b))
        u_extra, s_extra = {}, {}
        for vid, w in self.wahl.items():
            b = self.bereich(w)
            if b not in self.bereiche:
                self.fehl(f"Wahlstelle {vid}: bereich muss {', '.join(self.bereiche)} sein.")
                b = "allgemein"
            krit = dict(self.katalog[b])
            krit.update(self.definitionen(f"Wahlstelle {vid}", w.get("merkmale") or {}, b))
            self.kriterien[vid] = (b, krit)
            for o in w.get("optionen") or []:
                if o.get("id") in self.option:
                    self.mk_option[o["id"]] = self.werte(o["id"], o.get("merkmale"), krit)
                if b == "unterkunft":
                    for u in o.get("unterkuenfte") or []:
                        u_extra.setdefault(u, {}).update(krit)
                else:
                    for sid in o.get("strecken") or []:
                        s_extra.setdefault(sid, {}).update(krit)
        for uid, u in self.unterkuenfte.items():
            krit = {**self.katalog["unterkunft"], **u_extra.get(uid, {})}
            self.mk_unterkunft[uid] = self.werte(uid, u.get("merkmale"), krit)
        # Bewegungen (Strecken mit Art Fähre, Flug …): Werte dürfen an der Strecke stehen, wie bei Unterkünften an U-…
        for sid, st in self.strecken.items():
            if st.get("merkmale") is None:
                continue
            a = st.get("art", "wandern")
            basis = self.katalog.get(a if isinstance(a, str) and a in self.katalog and a != "wandern" else "strecke", {})
            self.mk_strecke[sid] = self.werte(sid, st.get("merkmale"), {**basis, **s_extra.get(sid, {})})

    def auto_werte(self, bereich, o):
        """Berechnete Merkmale einer Option (Kennzahlen ihrer Strecken bzw. Tage)."""
        s = None
        if bereich == "strecke" and o.get("strecken"):
            s = self.summe([{"strecken": o["strecken"], "nacht": None}])
        elif bereich == "route" and o.get("folge"):
            s = self.option_summe(o)
        if not s:
            return {}
        f = set(s["fehlend"])
        werte = {"gehzeit": dauer(s["min"]) if s["min"] and "min" not in f else None,
                 "laenge": f"{s['km']:g} km".replace(".", ",") if s["km"] and "km" not in f else None,
                 "hoehenmeter": f"↑ {s['auf']:.0f} m, ↓ {s['ab']:.0f} m" if s["auf"] and not {"auf", "ab"} & f else None,
                 "tage": (f"{s['tage']} Tage" if s["tage"] != 1 else "1 Tag") if bereich == "route" else None,
                 "unterkuenfte": ", ".join(f"{n}× {k}" for k, n in s["unterkunftstypen"].items()) or None}
        return {k: {"wert": v, "auto": True} for k, v in werte.items() if v}

    def anschluss(self, vid, o):
        """Passt die Option an ihre Stelle im aktuellen Plan? Vergleicht, wo der Plan davor endet, mit ihrem ersten Tag,
        und ihr Ende mit dem, was danach kommt (Paket 4, #18). Nur für ausgearbeitete Optionen (mit „folge“, auch leer)
        an Wahlstellen, durch die der aktuelle Plan läuft. Lücken heißen wie die Warnungen des Plans."""
        if vid not in self.grenzen or o.get("folge") is None:
            return {}
        a, e = self.grenzen[vid]
        tage, start, ende = self.plan_tage, self.r.get("start") or {}, self.r.get("ende") or {}
        davor = tage[a - 1]["end_ort"] if a else start.get("ort")
        danach = self.tag_lauf(tage[e]["id"], None)[3] if e < len(tage) else ende.get("ort")
        luecken, pos, anfang = [], davor, None
        tids = [t for t, _ in self.folge(o.get("folge"), o.get("id"))]
        for i, tid in enumerate(tids):
            _, _, pos, anf = self.tag_lauf(tid, pos)
            if i == 0:
                anfang = anf
        if tids:
            if davor and anfang and davor != anfang:
                luecken.append(f"Lücke am Anfang: {self.ort_name(davor)} → {self.ort_name(anfang)}")
            if pos and danach and pos != danach:
                luecken.append(f"Lücke am Ende: {self.ort_name(pos)} → {self.ort_name(danach)}")
            bekannt = davor and anfang and pos and (danach or e >= len(tage))
        else:
            if davor and danach and davor != danach:
                luecken.append(f"Lücke: {self.ort_name(davor)} → {self.ort_name(danach)}")
            bekannt = davor and danach
        if not luecken and not bekannt:
            return {}
        notiz = "Berechnet aus dem aktuellen Plan: davor " + (
            f"in {self.ort_name(davor)}" if a else f"Reisebeginn in {self.ort_name(davor)}") + (
            ", danach " + (f"weiter ab {self.ort_name(danach)}" if e < len(tage) else f"Reiseende in {self.ort_name(danach)}")
            if danach else ", danach Reiseende") + "."
        return {"anschluss": {"wert": "; ".join(luecken) or "nahtlos", "auto": True, "notiz": notiz}}

    def merkmale_aus(self, vid, o):
        b, krit = self.kriterien.get(vid, ("allgemein", {}))
        mk = {}
        if b == "unterkunft":
            for u in (o.get("unterkuenfte") or [])[:1]:
                mk.update(self.mk_unterkunft.get(u, {}))
        elif b != "route":
            for sid in (o.get("strecken") or [])[:1]:
                mk.update(self.mk_strecke.get(sid, {}))
        mk.update(self.mk_option.get(o.get("id"), {}))
        auto = self.auto_werte(b, o)
        if b == "route":
            auto.update(self.anschluss(vid, o))
        mk.update({k: auto[d["auto"]] for k, d in krit.items() if d.get("auto") in auto})
        typ = next((self.unterkuenfte.get(u, {}).get("typ") for u in (o.get("unterkuenfte") or [])[:1]), None)
        return {k: mk[k] for k in krit if k in mk}, [k for k, d in krit.items() if zaehlt(d, typ) and k not in mk]

    def waehle(self, vid, w):
        opts = [o for o in w.get("optionen") or [] if o.get("id") in self.option]
        gewaehlt = [o for o in opts if self.status(o) == "gewaehlt"]
        if len(gewaehlt) > 1:
            self.fehl(f"Wahlstelle {vid}: mehrere Optionen gewählt ({', '.join(o['id'] for o in gewaehlt)}).")
        gueltig = [o for o in opts if self.status(o) not in UNGUELTIG]
        fav = [o for o in gueltig if self.status(o) == "favorisiert"]
        aktiv = (gewaehlt or fav or gueltig or [None])[0]
        if aktiv is None:
            if opts:
                self.fehl(f"Wahlstelle {vid}: alle Optionen sind verworfen. Mindestens eine muss gültig bleiben.")
            return
        self.auswahl[vid] = aktiv["id"]
        if vid in self.zwang:
            self.auswahl[vid] = self.zwang[vid]
            return
        offen = not gewaehlt
        f = w.get("frage")
        if w.get("art") == "planung" and offen and len(gueltig) > 1 and not f:
            self.fehl(f"Wahlstelle {vid} ist offen und braucht eine F-Frage (frage: F-…).")
        if f and f in self.fragen:
            f_offen = "offen" in self.fragen[f].lower()
            if offen and len(gueltig) > 1 and not f_offen:
                self.warne(vid, f"{vid} ist noch offen, aber {f} steht nicht mehr auf offen.")
            if not offen and f_offen:
                self.warne(vid, f"{vid} ist entschieden, aber {f} steht noch auf offen.")

    # ---------- Folge durchlaufen ----------
    def folge(self, liste, wo, tiefe=0):
        """Folge aus Tagen, Wahlstellen und Teilen -> Liste (T-ID, Teil-Titel) in aktueller Auswahl."""
        aus = []
        if tiefe > 20:
            self.fehl(f"{wo}: Wahlstellen sind zu tief oder im Kreis verschachtelt.")
            return aus
        for el in liste or []:
            if isinstance(el, dict) and "teil" in el:
                for tid, teil in self.folge(el.get("folge"), wo, tiefe + 1):
                    aus.append((tid, teil or el["teil"]))
            elif ist("tag", el):
                if el not in self.tage:
                    self.fehl(f"{wo}: Tag {el} gibt es nicht.")
                    continue
                aus.append((el, None))
            elif ist("wahl", el):
                if el not in self.wahl:
                    self.fehl(f"{wo}: Wahlstelle {el} gibt es nicht.")
                    continue
                oid = self.auswahl.get(el)
                if oid:
                    aus += self.folge(self.option[oid][1].get("folge"), oid, tiefe + 1)
            else:
                self.fehl(f"{wo}: „{el}“ ist weder Tag, Wahlstelle noch Teil.")
        return aus

    def alle_tage_in(self, liste, sammel, wo):
        """Alle Tage einer Folge über alle Optionen (für 'in welchen Optionen kommt was vor')."""
        for el in liste or []:
            if isinstance(el, dict) and "teil" in el:
                self.alle_tage_in(el.get("folge"), sammel, wo)
            elif ist("tag", el):
                sammel.setdefault(el, set()).add(wo)
            elif ist("wahl", el) and el in self.wahl:
                for o in self.wahl[el].get("optionen") or []:
                    self.alle_tage_in(o.get("folge"), sammel, o.get("id"))

    def strecken_des_tages(self, tid, liste):
        """Strecken-Liste eines Tages (E- und V-IDs) -> [(E-ID, V-ID oder None)] in aktueller Auswahl."""
        aus = []
        for el in liste or []:
            if ist("wahl", el):
                if el not in self.wahl:
                    self.fehl(f"{tid}: Wahlstelle {el} gibt es nicht.")
                    continue
                oid = self.auswahl.get(el)
                for s in (self.option[oid][1].get("strecken") if oid else None) or []:
                    aus.append((s, el))
            else:
                aus.append((el, None))
        for s, _ in aus:
            if s not in self.strecken and s not in self.etappen:
                self.fehl(f"{tid}: Strecke {s} gibt es nicht.")
        return aus

    def nacht(self, tid, n):
        """-> {ort, unterkunft, wahl, hinweis} oder None (letzter Tag)."""
        if n is None:
            return None
        if isinstance(n, dict):
            if n.get("ort") and n["ort"] not in self.orte:
                self.fehl(f"{tid}: Ort {n['ort']} gibt es nicht.")
            if n.get("kategorie") and n["kategorie"] not in KATEGORIEN:
                self.fehl(f"{tid}: kategorie muss {', '.join(KATEGORIEN)} sein.")
            return {"ort": n.get("ort"), "hinweis": n.get("hinweis"), "typ": n.get("typ"), "an_bord": bool(n.get("an_bord")),
                    "kategorie": kategorie(n) if (n.get("typ") or n.get("kategorie") or n.get("an_bord")) else None}
        if ist("unterkunft", n):
            if n not in self.unterkuenfte:
                self.fehl(f"{tid}: Unterkunft {n} gibt es nicht.")
                return None
            return {"ort": self.unterkuenfte[n].get("ort"), "unterkunft": n}
        if ist("wahl", n):
            if n not in self.wahl:
                self.fehl(f"{tid}: Wahlstelle {n} gibt es nicht.")
                return None
            uids = [u for o in self.wahl[n].get("optionen") or [] for u in o.get("unterkuenfte") or []]
            for u in uids:
                if u not in self.unterkuenfte:
                    self.fehl(f"{n}: Unterkunft {u} gibt es nicht.")
            orte = {self.unterkuenfte[u].get("ort") for u in uids if u in self.unterkuenfte}
            if len(orte) > 1:
                self.warne(n, f"{n}: Die Kandidaten liegen in verschiedenen Orten ({', '.join(map(self.ort_name, orte))}).")
            oid = self.auswahl.get(n)
            akt = (self.option[oid][1].get("unterkuenfte") or [None])[0] if oid else None
            return {"ort": next(iter(orte), None), "wahl": n, "unterkunft": akt}
        if ist("ort", n):
            if n not in self.orte:
                self.fehl(f"{tid}: Ort {n} gibt es nicht.")
            return {"ort": n}
        self.fehl(f"{tid}: Übernachtung „{n}“ ist weder Unterkunft, Wahlstelle noch Ort.")
        return None

    def tag_lauf(self, tid, pos, warnen=False):
        """Ein Tag im aktuellen Plan: (Strecken, Nacht, Ort am Abend, Ort am Anfang). Der Anfang ist der Start der
        ersten Strecke, an einem Tag ohne Strecke der Ort der Nacht. warnen: Lücken melden (nur der Plan selbst)."""
        t = self.tage[tid]
        strecken = self.strecken_des_tages(tid, t.get("strecken"))
        anfang = None
        for i, (sid, _) in enumerate(strecken):
            s = self.strecke(sid)
            von = s.get("von")
            z = s.get("zweig_von")
            if z:  # Teilstück-Alternative: zweigt von einer anderen Strecke ab und ersetzt deren Rest
                von = self.strecke(z).get("von")
            if i == 0:
                anfang = von
            if warnen and von and pos and von != pos:
                self.warne(tid, f"{tid}: Lücke – der Tag steht in {self.ort_name(pos)}, "
                                f"{sid} beginnt in {self.ort_name(von)}.")
            pos = s.get("nach") or pos
        n = self.nacht(tid, t.get("nacht"))
        if n and n.get("ort") and not n.get("an_bord"):
            if not strecken:
                anfang = n["ort"]
            if warnen and pos and n["ort"] != pos:
                self.warne(tid, f"{tid}: Der Weg von {self.ort_name(pos)} nach {self.ort_name(n['ort'])} fehlt.")
            pos = n["ort"]
        return strecken, n, pos, anfang

    def grenzen_suchen(self, liste, n=0, tiefe=0):
        """Wo jede Wahlstelle im aktuellen Plan steht: self.grenzen[V-ID] = (Index ihres ersten Tags, Index des Tags
        danach); bei einer Option ohne Tage sind beide gleich. Zählt wie folge()."""
        if tiefe > 20:
            return n
        for el in liste or []:
            if isinstance(el, dict) and "teil" in el:
                n = self.grenzen_suchen(el.get("folge"), n, tiefe + 1)
            elif ist("tag", el):
                n += el in self.tage
            elif ist("wahl", el) and el in self.wahl:
                a = n
                oid = self.auswahl.get(el)
                if oid:
                    n = self.grenzen_suchen(self.option[oid][1].get("folge"), n, tiefe + 1)
                self.grenzen[el] = (a, n)
        return n

    # ---------- Ergebnis ----------
    def bauen(self):
        self.bausteine()
        start = self.r.get("start") or {}
        ende = self.r.get("ende") or {}
        if not isinstance(start.get("datum"), datetime.date):
            self.fehl("start.datum fehlt (JJJJ-MM-TT).")
            return None
        folge = self.folge(self.r.get("route"), "route")
        self.grenzen_suchen(self.r.get("route"))

        tage, pos = [], start.get("ort")
        for i, (tid, teil) in enumerate(folge):
            if tid in self.tag_benutzt:
                self.fehl(f"Tag {tid} kommt im aktuellen Plan zweimal vor.")
            self.tag_benutzt[tid] = True
            t = self.tage[tid]
            datum = start["datum"] + datetime.timedelta(days=i)
            start_ort = pos
            strecken, n, pos, _ = self.tag_lauf(tid, pos, warnen=True)
            unterwegs = [el for el in t.get("strecken") or [] if ist("wahl", el)]
            unterwegs += [el for el in t.get("wahl") or []]
            for el in t.get("wahl") or []:
                if el not in self.wahl:
                    self.fehl(f"{tid}: Wahlstelle {el} gibt es nicht.")
            tage.append({"id": tid, "nr": i + 1, "datum": datum.isoformat(),
                         "wochentag": WOCHENTAGE[datum.weekday()], "teil": teil,
                         "titel": t.get("titel", ""), "text": t.get("text", ""),
                         "start_ort": start_ort, "end_ort": pos,
                         "strecken": [{"id": s, "wahl": v} for s, v in strecken],
                         "wahlstellen": unterwegs, "nacht": n})

        # Fixpunkte und Ende
        nach_datum = {t["datum"]: t for t in tage}
        for fp in self.r.get("fixpunkte") or []:
            d = fp.get("datum")
            if not isinstance(d, datetime.date):
                self.fehl(f"Fixpunkt „{fp.get('titel')}“ ohne gültiges Datum.")
                continue
            t = nach_datum.get(d.isoformat())
            if not t:
                self.warne("plan", f"Fixpunkt {d:%d.%m.} ({fp.get('titel')}) liegt außerhalb des Plans.")
                continue
            orte = {t["start_ort"], t["end_ort"]} | {self.strecke(s["id"]).get(k) for s in t["strecken"]
                                                     for k in ("von", "nach")}
            if fp.get("ort") and fp["ort"] not in orte:
                self.warne(t["id"], f"Fixpunkt {d:%d.%m.} ({fp.get('titel')}): Der Plan ist an diesem Tag nicht in "
                                    f"{self.ort_name(fp['ort'])}.")
            t.setdefault("fixpunkte", []).append(fp.get("titel", ""))
        if isinstance(ende.get("datum"), datetime.date) and tage:
            letzt = datetime.date.fromisoformat(tage[-1]["datum"])
            diff = (letzt - ende["datum"]).days
            if diff:
                self.warne("plan", f"Der aktuelle Plan endet am {letzt:%d.%m.}, die Reise aber am "
                                   f"{ende['datum']:%d.%m.} ({'+' if diff > 0 else ''}{diff} Tag(e)).")
            if ende.get("ort") and tage[-1]["end_ort"] != ende["ort"]:
                self.warne(tage[-1]["id"], f"Der Plan endet in {self.ort_name(tage[-1]['end_ort'])}, "
                                           f"die Reise endet in {self.ort_name(ende['ort'])}.")

        self.plan_tage = tage
        self.regeln_im_plan(tage, {o for t in tage for o in (t["start_ort"], t["end_ort"])}
                            | {self.strecke(s["id"]).get(k) for t in tage for s in t["strecken"] for k in ("von", "nach")})
        # Was kommt wo vor
        in_opt = {}
        self.alle_tage_in(self.r.get("route"), in_opt, "route")
        for tid, wo in in_opt.items():
            if len(wo) > 1:
                self.fehl(f"Tag {tid} steht in mehreren Optionen ({', '.join(sorted(wo))}). "
                          f"Ein Tag gehört zu genau einer Option; für eine Variante einen neuen Tag anlegen.")
        for tid in self.tage:
            if tid not in in_opt:
                self.warne(tid, f"Tag {tid} kommt in keiner Option vor.")
        for vid, w in self.wahl.items():
            frei = not w.get("an") and not any(vid in (t.get("strecken") or []) or vid == t.get("nacht")
                                               or vid in (t.get("wahl") or []) for t in self.tage.values())
            if frei and not self.kommt_in_folge_vor(vid):
                self.warne(vid, f"Wahlstelle {vid} wird nirgends verwendet.")

        aktiv_strecken = {s["id"] for t in tage for s in t["strecken"]}
        aktiv_tage = {t["id"] for t in tage}
        weitere = {}
        for tid, t in self.tage.items():
            if tid in aktiv_tage:
                continue
            weitere[tid] = {"id": tid, "titel": t.get("titel", ""), "text": t.get("text", ""),
                            "strecken": [{"id": s, "wahl": v} for s, v in self.strecken_des_tages(tid, t.get("strecken"))],
                            "wahlstellen": [el for el in t.get("strecken") or [] if ist("wahl", el)] + list(t.get("wahl") or []),
                            "nacht": self.nacht(tid, t.get("nacht"))}
        return {
            "tage": tage,
            "weitere_tage": weitere,
            "summe": self.summe(tage),
            "plaene": [] if self.ist_plan else self.plaene(tage),
            "wahlstellen": [self.wahl_aus(vid, w) for vid, w in self.wahl.items()],
            "orte": {k: {"name": v.get("name", k), "hinweis": v.get("hinweis")} for k, v in self.orte.items()},
            "strecken": {sid: self.strecke_aus(sid) for sid in sorted(set(self.strecken) | aktiv_strecken)},
            "unterkuenfte": self.unterkuenfte_aus(tage),
            "kategorien": KATEGORIEN,
            "aktiv_strecken": sorted(aktiv_strecken),
            "merkmale": {b: [{"id": k, **d} for k, d in krit.items()] for b, krit in self.katalog.items()},
            "warnungen": self.warnungen,
        }

    def plaene(self, aktuelle_tage):
        """Benannte Pläne (P-A …): feste Kombinationen von Optionen, jeweils vollständig durchgerechnet."""
        aus = []
        for p in self.r.get("plaene") or []:
            pid = p.get("id", "")
            if not re.fullmatch(r"P-[A-Za-z0-9]+", pid):
                self.fehl(f"Plan „{pid}“: ID muss P-… heißen.")
                continue
            self.id_anlegen(pid, self.q)
            zwang = {}
            for oid in p.get("auswahl") or []:
                if oid not in self.option:
                    self.fehl(f"Plan {pid}: Option {oid} gibt es nicht.")
                    continue
                vid = self.option[oid][0]
                if vid in zwang:
                    self.fehl(f"Plan {pid}: zwei Optionen für {vid} ({zwang[vid]}, {oid}).")
                zwang[vid] = oid
            r = Routen(self.r, self.etappen, self.fragen, [], lambda *a: None, self.q, zwang, self.grund,
                       entscheider=sorted(self.entscheider))
            erg = r.bauen()
            if not erg:
                continue
            aktuell = [t["id"] for t in erg["tage"]] == [t["id"] for t in aktuelle_tage] and \
                all(self.auswahl.get(v) == o for v, o in zwang.items())
            aus.append({"id": pid, "titel": p.get("titel", pid), "kurz": p.get("kurz", pid), "farbe": p.get("farbe"),
                        "text": p.get("text", ""), "plus": p.get("plus", []), "minus": p.get("minus", []),
                        "auswahl": list(zwang.values()), "aktuell": aktuell,
                        "tage": erg["tage"], "summe": erg["summe"],
                        # nur, was diesen Plan betrifft (Lücken, Fixpunkte, Reiseende), nicht Hinweise zu Wahlstellen
                        "warnungen": [w for w in erg["warnungen"]
                                      if w not in self.warnungen and not w["bezug"].startswith("V-")]})
        return aus

    def kommt_in_folge_vor(self, vid):
        def such(liste):
            for el in liste or []:
                if el == vid:
                    return True
                if isinstance(el, dict) and such(el.get("folge")):
                    return True
                if ist("wahl", el) and el in self.wahl:
                    if any(such(o.get("folge")) for o in self.wahl[el].get("optionen") or []):
                        return True
            return False
        return such(self.r.get("route"))

    def summe(self, tage):
        """tage: [{strecken: [E-ID oder {id}], nacht}] -> Kennzahlen; fehlend = Felder, für die Angaben fehlen."""
        s = {"tage": len(tage), "naechte": sum(1 for t in tage if t["nacht"]), "min": 0, "auf": 0, "ab": 0, "km": 0.0,
             "fehlend": set(), "laengster": None, "unterkunftstypen": {}}
        for nr, t in enumerate(tage, 1):
            tag_min = 0
            for x in t["strecken"]:
                st = self.strecke(x["id"] if isinstance(x, dict) else x)
                if st.get("art", "wandern") != "wandern":
                    continue
                w = kennwerte(st.get("kennzahlen"))
                for k in ("min", "auf", "ab", "km"):
                    if w[k] is None:
                        s["fehlend"].add(k)
                    else:
                        s[k] += w[k]
                tag_min += w["min"] or 0
            if tag_min and (not s["laengster"] or tag_min > s["laengster"]["min"]):
                s["laengster"] = {"min": tag_min, "nr": nr, "id": t.get("id")}
            n = t["nacht"] or {}
            typ = self.unterkuenfte[n["unterkunft"]].get("typ") if n.get("unterkunft") in self.unterkuenfte else n.get("typ")
            if n and not n.get("an_bord"):
                typ = typ or "offen"
                s["unterkunftstypen"][typ] = s["unterkunftstypen"].get(typ, 0) + 1
        s["km"] = round(s["km"], 1)
        s["fehlend"] = sorted(s["fehlend"])
        s["unvollstaendig"] = bool(s["fehlend"])
        return s

    def option_summe(self, o):
        """Kennzahlen einer Option für sich (ihre eigenen Tage in aktueller Unterauswahl)."""
        tids = [t for t, _ in self.folge(o.get("folge"), o.get("id"))]
        if not tids:
            return None
        tage = []
        for tid in tids:
            t = self.tage[tid]
            tage.append({"id": tid, "nacht": self.nacht(tid, t.get("nacht")),
                         "strecken": [s for s, _ in self.strecken_des_tages(tid, t.get("strecken"))]})
        return self.summe(tage)

    def wahl_aus(self, vid, w):
        akt = self.auswahl.get(vid)
        opts = []
        for o in w.get("optionen") or []:
            oid = o.get("id")
            if oid not in self.option:
                continue
            mk, fehlt = self.merkmale_aus(vid, o)
            opts.append({
                "merkmale": mk, "fehlt": fehlt,
                "id": oid, "titel": o.get("titel", oid), "status": self.status(o), "aktiv": oid == akt,
                "verlauf": [{**e, "datum": e["datum"].isoformat() if isinstance(e.get("datum"), datetime.date)
                             else str(e.get("datum"))} for e in o.get("verlauf") or []],
                "text": o.get("text", ""), "plus": o.get("plus", []), "minus": o.get("minus", []),
                "ausloeser": o.get("ausloeser"), "quelle": o.get("quelle"), "siehe": o.get("siehe"),
                "strecken": o.get("strecken"), "unterkuenfte": o.get("unterkuenfte"),
                "tage": [t for t, _ in self.folge(o.get("folge"), oid)] if o.get("folge") else None,
                "folge": list(o.get("folge") or []),
                "alle_strecken": sorted(self.alle_strecken(o)),
                "summe": self.option_summe(o) if o.get("folge") else None,
                **self.regel_aus(oid),
            })
        an = [tid for tid, t in self.tage.items()
              if vid in (t.get("strecken") or []) or vid == t.get("nacht") or vid in (t.get("wahl") or [])]
        an_ids = [x for x in w.get("an") or [] if isinstance(x, str)]
        offen = not any(o["status"] == "gewaehlt" for o in opts)
        b, krit = self.kriterien.get(vid, ("allgemein", {}))
        return {"bereich": b, "kriterien": [{"id": k, **d} for k, d in krit.items()],
                "id": vid, "titel": w.get("titel", vid), "art": w.get("art"), "frage": w.get("frage"),
                "text": w.get("text", ""), "an": an, "an_ids": an_ids, "offen": offen, "optionen": opts}

    def alle_strecken(self, o, tiefe=0):
        """Alle Strecken einer Option: eigene und die ihrer Tage, über alle Unteroptionen."""
        aus = set(o.get("strecken") or [])
        if tiefe > 20:
            return aus
        tage = {}
        self.alle_tage_in(o.get("folge"), tage, o.get("id"))
        for tid in tage:
            for el in (self.tage.get(tid) or {}).get("strecken") or []:
                if ist("wahl", el) and el in self.wahl:
                    for u in self.wahl[el].get("optionen") or []:
                        aus |= self.alle_strecken(u, tiefe + 1)
                else:
                    aus.add(el)
        return aus

    def strecke_aus(self, sid):
        s = self.strecke(sid)
        # Bewegungen mit eigener Merkmalliste (Fähre, Flug …): Werte und Lücken wie bei Unterkünften (Paket 3, #18)
        a = s.get("art")
        b = a if isinstance(a, str) and a != "wandern" and a in self.katalog else None
        mk = self.mk_strecke.get(sid, {})
        merkmale = {"bereich": b, "merkmale": mk,
                    "fehlt": [k for k, d in self.katalog[b].items() if zaehlt(d) and k not in mk]} if b else \
            ({"merkmale": mk, "fehlt": []} if mk else {})
        return {"titel": s.get("titel", sid), "von": s.get("von"), "nach": s.get("nach"), "art": s.get("art"),
                "rolle": s.get("rolle", "haupt"), "zweig_von": s.get("zweig_von"), "kennzahlen": s.get("kennzahlen") or {},
                "quelle": s.get("quelle"), "siehe": s.get("siehe"), "text": s.get("text", ""),
                "dossier": bool(s.get("dossier")), **merkmale}

    def unterkuenfte_aus(self, tage):
        naechte = {}
        for t in tage:
            n = t["nacht"] or {}
            ziel = [n["unterkunft"]] if n.get("unterkunft") else []
            if n.get("wahl"):
                ziel = [u for o in self.wahl[n["wahl"]].get("optionen") or [] for u in o.get("unterkuenfte") or []]
            for u in ziel:
                naechte.setdefault(u, []).append(t["id"])
        aus = {}
        for uid, u in self.unterkuenfte.items():
            aus[uid] = {k: u.get(k) for k in ("name", "ort", "typ", "kontakt", "hinweis", "quelle", "frage")}
            aus[uid]["kategorie"] = kategorie(u)
            aus[uid]["buchung"] = u.get("buchung", "offen")
            aus[uid]["naechte"] = naechte.get(uid, [])
            mk = self.mk_unterkunft.get(uid, {})
            aus[uid]["merkmale"] = mk
            aus[uid]["fehlt"] = [k for k, d in self.katalog.get("unterkunft", {}).items() if zaehlt(d, u.get("typ")) and k not in mk]
        return aus
