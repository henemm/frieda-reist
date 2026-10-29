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

Merkmale: Jedes Ding hat eine Art, die die Reise in plan/arten.yaml definiert (docs/ontologie.md): Unterkunft über typ
oder art, Strecke über art, Wahlstelle über bereich oder ihre Optionen. Die Art sagt, welche Merkmale es gibt; eine
Wahlstelle kann für sich ergänzen. Werte stehen an der Option, bei Unterkünften an der Unterkunft (U-…), bei Bewegungen an
der Strecke. Was fehlt, zeigt die Seite. Standard und Ablauf: docs/alternativen.md.

Hintergrund und Entscheidung: GitHub-Issue #9.
"""
import datetime
import re
import unicodedata

STATUS = ("vorgeschlagen", "favorisiert", "gewaehlt", "verworfen", "ersetzt")
NUR_ENTSCHEIDER = {"gewaehlt", "verworfen", "ersetzt"}
UNGUELTIG = {"verworfen", "ersetzt"}
ARTEN = {"planung", "unterwegs"}
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
# Uhrzeit einer Bewegung oder eines Aufenthalts (beginn, ende; #77 Kalender), Ortszeit am Ort des Dings
UHRZEIT = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
MUSTER = {"ort": r"O-\d+", "strecke": r"E-\d+[A-Za-z]?", "unterkunft": r"U-\d+", "aufenthalt": r"A-\d+",
          "tag": r"T-\d+", "wahl": r"V-\d+", "option": r"V-\d+\.[a-z]+", "wissen": r"W-\d+", "buchung": r"B-\d+"}
# Buchung (Product Owner 29.10.2026, frieda-reist #76): eigenes Ding B-… in routen.yaml unter buchungen:, gehört zu einem
# oder mehreren Aufenthalten (U-, A-) oder Bewegungen (E-) („fuer“). Felder: status, nummer, bei, preis, bezahlt, frist,
# frist_was, storno, storno_bis, gebucht_am, wer, quelle (Pflicht: Herkunft), notiz, verlauf. Der Beleg (PDF, Bild)
# liegt nie im Repo, sondern in der Ablage der Instanz (Rückmeldedienst, docs/betrieb.md „Belege“).
BUCHUNG_STATUS = ("angefragt", "gebucht", "storniert")
BUCHUNG_FELDER = ("fuer", "status", "nummer", "bei", "preis", "bezahlt", "frist", "frist_was", "storno", "storno_bis", "gebucht_am",
                  "wer", "quelle", "notiz", "verlauf")
BUCHUNG_DATEN = ("frist", "storno_bis", "gebucht_am")
# Grundformen der Reise-Ontologie (docs/ontologie.md, ADR-0001): Aufenthalt (Unterkunft, Nacht), Bewegung (Strecke),
# Folge (Tag, Reiseteil). Welche Arten es davon gibt (Hotel, Refugi, Wanderung, Bahn, Reiseteil …) und welche Merkmale
# eine Art hat, sagt allein die Reise in plan/arten.yaml. Die Software kennt nur die Grundformen, die Form eines
# Merkmals und die berechneten Kennzahlen je Grundform.
GRUNDFORMEN = ("aufenthalt", "bewegung", "folge")
AUTO_JE_GRUNDFORM = {"bewegung": ("gehzeit", "laenge", "hoehenmeter"), "folge": ("tage", "gehzeit", "unterkuenfte", "anschluss")}
ART_MUSTER = r"[a-z][a-z0-9_]*"
ART_FELDER = {"grundform", "name", "farbe", "symbol", "buchbar", "merkmale", "beschreibung", "summiert", "lesetext"}
# Symbole der Seite, die eine Art tragen darf (engine/bauen.py SYMBOLE, Lucide); ohne Angabe das Symbol der Grundform
SYMBOLE_ARTEN = ("unterkunft", "zelt", "einkehr", "ticket", "museum", "wandern", "bus", "bahn", "schiff", "flug", "auto", "rad",
                 "taxi", "strecke", "ort", "karte", "plan")
GRUNDFORM_SYMBOL = {"aufenthalt": "unterkunft", "bewegung": "strecke", "folge": "plan"}
# Gliederung des Lesetexts einer Art (docs/ontologie.md „Lesetext“): Rubriken in ihrer Reihenfolge, jede mit Namen (das
# Stichwort am Anfang eines Absatzes) und Hilfe für den AI-Client. Welche Rubriken es gibt, sagt allein die Reise.
RUBRIK_FELDER = {"name", "hilfe"}
# Farben der Seite für Arten (engine/vorlage.html, --farbe-*); ohne Angabe grau
FARBEN = ("blau", "braun", "lila", "gruen", "tuerkis", "oliv", "grau", "rosa", "schiefer")
UNTERWEGS = "unterwegs"     # Nacht an Bord (Nachtfähre, Nachtzug): keine Art der Reise, feste Darstellung
ALLGEMEIN = "allgemein"     # Wahlstelle ohne Art: keine Merkmale
KOMBINIERT = "kombiniert"   # Strecke mit mehreren Arten (bahn und bus): die Reise definiert diese Art, wenn sie vorkommt


def art_schluessel(text):
    """Art aus einer freien Bezeichnung (typ einer Unterkunft): klein, Umlaute und Akzente aufgelöst, Rest zu _."""
    t = str(text or "").strip().lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("&", "und")):
        t = t.replace(a, b)
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_") or None
TYPEN = {"text", "geld", "zahl", "auswahl"}
# Stufe eines Merkmals (docs/ontologie.md): nur pflicht zählt als „Fehlt noch“ (Paket O-5); empfohlen ist Spalte im Vergleich,
# ohne Wert keine Lücke und keine Mahnung (Product Owner 29.10.2026); angeboten
# wird nur gezeigt, wenn ein Wert da ist, aus gilt nicht (kein Fehlt, keine Mahnung, kein Wächter). Ohne Angabe gilt
# empfohlen. Die Reise setzt sie in arten.yaml, eine Wahlstelle ändert sie für sich mit {stufe: …}. Die Stufe darf je
# typ einer Unterkunft verschieden sein: stufe: {"*": aus, refugi: empfohlen} (klein geschrieben; „*“ für alle übrigen).
# Für Menschen heißen die Stufen „nötig“, „gut zu wissen“, „zusätzlich“ (Product Owner 29.10.2026); „aus“ bleibt unsichtbar.
# In Dateien und Werkzeugen bleiben die Schlüssel; die Wörter nimmt der Schreibweg als Eingabe ebenfalls an (stufe_schluessel).
STUFEN = ("pflicht", "empfohlen", "angeboten", "aus")
STUFEN_WORTE = {"pflicht": "nötig", "empfohlen": "gut zu wissen", "angeboten": "zusätzlich", "aus": "aus"}


def stufe_wort(s):
    """Wort einer Stufe für Menschen: „nötig (pflicht)“; eine Stufe je Typ wird je Typ genannt („sonst“ für „*“,
    „gilt nicht“ statt des Schlüssels aus, der für Menschen unsichtbar bleibt; Product Owner 29.10.2026)."""
    if isinstance(s, dict):
        return ", ".join(f"{'sonst' if t == '*' else t}: {'gilt nicht' if v == 'aus' else stufe_wort(v)}" for t, v in s.items())
    return f"{STUFEN_WORTE.get(s, s)} ({s})" if s in STUFEN_WORTE and s != "aus" else str(s)


def stufe_gilt(s):
    """Gilt das Merkmal für diese Reise überhaupt (Stufe nicht aus; bei Stufe je Typ nicht überall aus)?"""
    if isinstance(s, dict):
        return any(v != "aus" for v in s.values())
    return s != "aus"


def stufe_schluessel(text):
    """Eingabe einer Stufe (Schlüssel oder Wort, beliebige Schreibung) -> Schlüssel oder None, wenn unbekannt."""
    t = re.sub(r"\s+", " ", str(text or "").strip().lower())
    if t in STUFEN:
        return t
    for k, w in STUFEN_WORTE.items():
        if t == w or t == w.replace("ö", "oe"):
            return k
    return None
DEF_FELDER = {"name", "typ", "werte", "veraenderlich", "auto", "hilfe", "frage", "einheit", "stufe", "auch"}


def stufe_von(d, typ=None):
    """Stufe eines Merkmals für ein Ding mit diesem typ (Unterkunft) oder ohne (None: „*“)."""
    s = d.get("stufe", "empfohlen")
    if isinstance(s, dict):
        return s.get(str(typ or "").strip().lower(), s.get("*", "empfohlen"))
    return s


def zaehlt(d, typ=None):
    """Zählt das Merkmal als Lücke („Fehlt noch“, Zähler im Vergleich)? Nur pflicht (Paket O-5), nie berechnete."""
    return not d.get("auto") and stufe_von(d, typ) == "pflicht"



def stufe_fehler(s):
    """Prüft eine Stufen-Angabe -> Fehlertext oder None."""
    if isinstance(s, dict):
        if not s or any(not re.fullmatch(r"\*|[a-z][a-z0-9_]*", str(k)) for k in s) or any(v not in STUFEN for v in s.values()):
            return f"stufe je Typ muss {{\"*\": …, <typ>: …}} mit Werten {', '.join(STUFEN)} sein."
        return None
    return None if s in STUFEN else f"stufe muss {', '.join(STUFEN)} sein."
WERT_FELDER = {"wert", "quelle", "geprueft", "notiz", "gilt"}


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
        for uid, u in (route.get("unterkuenfte") or {}).items():
            defs = {k["id"]: k for k in (route.get("merkmale") or {}).get(u.get("art")) or []}
            ung = [k for k, m in (u.get("merkmale") or {}).items()
                   if m.get("ungeprueft") and stufe_von(defs.get(k, {}), u.get("typ")) != "aus"]
            if ung and u.get("naechte"):
                mahnungen.append({"bezug": uid, "text": f"{uid} {u.get('name')}: {', '.join(ung)} ohne Prüfdatum."})
    route["mahnungen"] = mahnungen
    return route


class Routen:
    def __init__(self, roh, etappen, fragen, fehler, id_anlegen, quelle="plan/routen.yaml", zwang=None, arten=None,
                 entscheider=None, wissen=None):
        """roh: geladenes YAML. etappen: {E-ID: Etappe aus dem Dossier}. fragen: {F-ID: Status-Text}.
        entscheider: Namen, die gewaehlt/verworfen/ersetzt setzen dürfen (Organisator:innen aus reise.yaml); None: aus dem YAML.
        zwang: {V-ID: Option-ID} – für benannte Pläne; erzwingt eine Option, auch eine verworfene.
        arten: geladenes plan/arten.yaml der Reise (Arten und Merkmale, docs/ontologie.md).
        wissen: bekannte W-IDs (Abschnitte wie Essen, Ausflug, Praxis), an denen eine Wahlstelle hängen darf; None: ungeprüft."""
        self.r = roh or {}
        self.arten_roh = arten
        self.arten = {}           # Art -> {name, grundform, farbe, symbol, buchbar, summiert}, aus plan/arten.yaml der Reise
        self.a_art = {}           # A-01 -> Art (Aufenthalt ohne Nacht, Paket O-5)
        self.mk_aufenthalt = {}   # A-01 -> {Merkmal: Wert}
        self.katalog = {}         # Art -> {Merkmal: Definition}
        self.u_art = {}           # U-01 -> Art
        self.kriterien = {}       # V-ID -> (Art, {Merkmal: Definition})
        self.mk_option = {}       # V-01.a -> {Merkmal: Wert}
        self.mk_unterkunft = {}   # U-01 -> {Merkmal: Wert}
        self.mk_strecke = {}      # E-01 -> {Merkmal: Wert} (Bewegungen: Fähre, Flug, Bahn …)
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
        self.aufenthalte = self.r.get("aufenthalte") or {}   # Aufenthalte ohne Nacht: Besichtigung, Essen, Besuch (A-…)
        self.buchungen = self.r.get("buchungen") or {}       # Buchungen (B-…) zu Unterkünften, Aufenthalten, Strecken (#76)
        self.buchung_je_ding = {}                            # U-01/A-01/E-01 -> B-ID der geltenden Buchung (nicht storniert)
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
    def uhrzeit_pruefen(self, d, wo):
        """beginn und ende (#77, Kalender): Uhrzeit HH:MM als Text, ende nur mit beginn. Ende vor Beginn heißt: am Tag danach."""
        for k in ("beginn", "ende"):
            if d.get(k) is not None and not (isinstance(d[k], str) and UHRZEIT.match(d[k])):
                self.fehl(f"{wo}: {k} muss eine Uhrzeit HH:MM in Anführungszeichen sein (z. B. \"09:30\").")
        if d.get("ende") is not None and d.get("beginn") is None:
            self.fehl(f"{wo}: ende ohne beginn.")

    def bausteine(self):
        for art, menge in (("ort", self.orte), ("strecke", self.strecken), ("unterkunft", self.unterkuenfte),
                           ("aufenthalt", self.aufenthalte), ("buchung", self.buchungen), ("tag", self.tage), ("wahl", self.wahl)):
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
            self.uhrzeit_pruefen(s, f"Strecke {sid}")
            z = s.get("zweig_von")
            if z and z not in self.strecken and z not in self.etappen:
                self.fehl(f"Strecke {sid}: zweig_von {z} gibt es nicht.")
        self.arten_pruefen()
        for sid, s in self.strecken.items():
            self.strecken_art(s, f"Strecke {sid}")
        for uid, u in self.unterkuenfte.items():
            self.id_anlegen(uid, self.q)
            if u.get("ort") not in self.orte:
                self.fehl(f"Unterkunft {uid}: Ort {u.get('ort')} gibt es nicht.")
            if u.get("frage") and u["frage"] not in self.fragen:
                self.fehl(f"Unterkunft {uid}: Frage {u['frage']} gibt es nicht.")
            self.u_art[uid] = self.art_von(u, f"Unterkunft {uid}")
            self.lage_pruefen(u, f"Unterkunft {uid}")
        for aid, a in self.aufenthalte.items():
            # Aufenthalt ohne Nacht (Paket O-5): Ort, Art (Grundform aufenthalt), Herkunft; zeit ist freier Text („10–12 Uhr“)
            self.id_anlegen(aid, self.q)
            if not isinstance(a, dict) or not a.get("name"):
                self.fehl(f"Aufenthalt {aid} braucht einen Namen (name: …).")
                continue
            if a.get("ort") not in self.orte:
                self.fehl(f"Aufenthalt {aid}: Ort {a.get('ort')} gibt es nicht.")
            if not a.get("quelle"):
                self.fehl(f"Aufenthalt {aid}: quelle fehlt (Herkunft).")
            self.uhrzeit_pruefen(a, f"Aufenthalt {aid}")
            self.a_art[aid] = self.art_von(a, f"Aufenthalt {aid}")
            self.lage_pruefen(a, f"Aufenthalt {aid}")
        self.buchungen_pruefen()
        for tid, t in self.tage.items():
            self.id_anlegen(tid, self.q)
            for aid in t.get("aufenthalte") or []:
                if aid not in self.aufenthalte:
                    self.fehl(f"{tid}: Aufenthalt {aid} gibt es nicht.")
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

    def buchungen_pruefen(self):
        """Buchungen (B-…, #76): gehören zu vorhandenen Dingen, haben Status, Herkunft und gültige Daten. Eine nicht
        stornierte Buchung setzt den Buchungsstand ihrer Dinge (buchung_je_ding); zwei geltende für dasselbe Ding sind eine Warnung."""
        for bid, b in self.buchungen.items():
            self.id_anlegen(bid, self.q)
            if not isinstance(b, dict):
                self.fehl(f"Buchung {bid} muss Felder haben (fuer, status, quelle …).")
                continue
            for k in b:
                if k not in BUCHUNG_FELDER:
                    self.fehl(f"Buchung {bid}: unbekanntes Feld „{k}“ (möglich: {', '.join(BUCHUNG_FELDER)}).")
            fuer = b.get("fuer")
            fuer = [fuer] if isinstance(fuer, str) else list(fuer or [])
            if not fuer:
                self.fehl(f"Buchung {bid}: fuer fehlt (welche Unterkunft U-…, welcher Aufenthalt A-… oder welche Strecke E-… ist gebucht).")
            for x in fuer:
                if not (x in self.unterkuenfte or x in self.aufenthalte or x in self.strecken or x in self.etappen):
                    self.fehl(f"Buchung {bid}: {x} gibt es nicht (fuer nennt Unterkünfte, Aufenthalte oder Strecken).")
            if b.get("status", "gebucht") not in BUCHUNG_STATUS:
                self.fehl(f"Buchung {bid}: status muss {', '.join(BUCHUNG_STATUS)} sein.")
            if not b.get("quelle"):
                self.fehl(f"Buchung {bid}: quelle fehlt (Herkunft, z. B. „Buchungsbestätigung per Mail vom …“).")
            for k in BUCHUNG_DATEN:
                v = b.get(k)
                if v is not None and not isinstance(v, datetime.date):
                    try:
                        datetime.date.fromisoformat(str(v))
                    except ValueError:
                        self.fehl(f"Buchung {bid}: {k} muss ein Datum JJJJ-MM-TT sein.")
            for e in b.get("verlauf") or []:   # wie jeder Verlauf: wer hat wann (ADR-0001)
                if not isinstance(e, dict) or not isinstance(e.get("datum"), datetime.date) or not e.get("wer"):
                    self.fehl(f"Buchung {bid}: jeder Verlaufseintrag braucht datum (JJJJ-MM-TT) und wer.")
                    break
            if b.get("status", "gebucht") != "storniert":
                for x in fuer:
                    alt = self.buchung_je_ding.get(x)
                    if alt and alt != bid:
                        self.warne(bid, f"Buchung {bid} und {alt} gelten beide für {x}.")
                    # Welche gilt (Product Owner 29.10.2026): gebucht vor angefragt, dann die jüngste (gebucht_am), dann die spätere
                    if alt is None or self.buchung_rang(bid) >= self.buchung_rang(alt):
                        self.buchung_je_ding[x] = bid

    def buchung_rang(self, bid):
        """Vorrang einer Buchung für den Buchungsstand ihres Dings: (gebucht?, gebucht_am)."""
        b = self.buchungen.get(bid)
        b = b if isinstance(b, dict) else {}
        am = b.get("gebucht_am")
        if not isinstance(am, datetime.date):
            try:
                am = datetime.date.fromisoformat(str(am)) if am else datetime.date.min
            except ValueError:
                am = datetime.date.min
        return (b.get("status", "gebucht") == "gebucht", am)

    def buchung_aus(self, bid):
        """Eine Buchung für die Seite und den Konnektor: Felder als Text, Daten als ISO, Verlauf, Titel aus ihren Dingen."""
        b = self.buchungen.get(bid)
        b = b if isinstance(b, dict) else {}
        iso = lambda v: v.isoformat() if isinstance(v, datetime.date) else (str(v) if v else None)
        fuer = [b["fuer"]] if isinstance(b.get("fuer"), str) else list(b.get("fuer") or [])
        namen = [(self.unterkuenfte.get(x) or self.aufenthalte.get(x) or {}).get("name") or self.strecke(x).get("titel") or x for x in fuer]
        aus = {"id": bid, "fuer": fuer, "titel": ", ".join(namen), "status": str(b.get("status") or "gebucht")}
        for k in ("nummer", "bei", "preis", "bezahlt", "frist_was", "storno", "wer", "quelle", "notiz"):
            aus[k] = str(b[k]) if b.get(k) not in (None, "") else None
        for k in BUCHUNG_DATEN:
            aus[k] = iso(b.get(k))
        aus["verlauf"] = [{**{kk: iso(vv) if kk == "datum" else vv for kk, vv in v.items()}} for v in b.get("verlauf") or [] if isinstance(v, dict)]
        return aus

    def lage_pruefen(self, d, wo):
        """Lage eines Aufenthalts (ADR-0004): adresse und punkt, beide als Aussage mit Herkunft
        ({wert, quelle, geprueft}); punkt.wert ist [Breite, Länge]. Beide sind freiwillig; ob eine Lage fehlt, mahnt der Bau."""
        for feld in ("adresse", "punkt"):
            v = d.get(feld)
            if v is None:
                continue
            if not isinstance(v, dict) or set(v) - {"wert", "quelle", "geprueft", "notiz"} or not v.get("quelle"):
                self.fehl(f"{wo}: {feld} braucht {{wert, quelle}} (Herkunft), dazu geprueft (Datum).")
                continue
            w = v.get("wert")
            if feld == "adresse" and not (isinstance(w, str) and w.strip()):
                self.fehl(f"{wo}: adresse.wert muss ein Text sein (Straße Nr., PLZ Ort).")
            if feld == "punkt" and not (isinstance(w, list) and len(w) == 2 and all(isinstance(x, (int, float)) for x in w)
                                         and -90 <= w[0] <= 90 and -180 <= w[1] <= 180):
                self.fehl(f"{wo}: punkt.wert braucht [Breite, Länge] in Grad.")
            g = v.get("geprueft")
            if g is not None and not isinstance(g, datetime.date):
                self.fehl(f"{wo}: {feld}.geprueft muss ein Datum sein (JJJJ-MM-TT).")

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

    # ---------- Arten und Merkmale (docs/ontologie.md) ----------
    def arten_pruefen(self):
        """plan/arten.yaml der Reise prüfen -> self.arten, self.katalog. Jede Art hat genau eine Grundform."""
        if self.arten or self.katalog:
            return
        roh = self.arten_roh
        if isinstance(roh, dict) and "arten" in roh:
            roh = roh["arten"]
        if not isinstance(roh, dict) or not roh:
            self.fehl("plan/arten.yaml fehlt oder hat keine Arten („arten:“). Jede Reise legt ihre Arten und Merkmale selbst "
                      "fest (docs/ontologie.md); aus Bestandsdaten ableiten: engine/neu.py arten-ableiten <reise>.")
            return
        for a, d in roh.items():
            wo = f"arten.yaml {a}"
            if not re.fullmatch(ART_MUSTER, str(a)) or a in (UNTERWEGS, ALLGEMEIN):
                self.fehl(f"{wo}: Art „{a}“: nur Kleinbuchstaben, Ziffern und _ (nicht {UNTERWEGS}, {ALLGEMEIN}).")
                continue
            if not isinstance(d, dict) or d.get("grundform") not in GRUNDFORMEN:
                self.fehl(f"{wo}: grundform muss {', '.join(GRUNDFORMEN)} sein.")
                continue
            if set(d) - ART_FELDER:
                self.fehl(f"{wo}: unbekannte Felder {', '.join(sorted(set(d) - ART_FELDER))}.")
            if d.get("farbe") and d["farbe"] not in FARBEN:
                self.fehl(f"{wo}: farbe muss {', '.join(FARBEN)} sein.")
            if d.get("symbol") and d["symbol"] not in SYMBOLE_ARTEN:
                self.fehl(f"{wo}: symbol muss {', '.join(SYMBOLE_ARTEN)} sein.")
            # buchbar: das Ding dieser Art hat einen Buchungsstand (Zu buchen, Stand der Vorbereitung); Vorgabe: Aufenthalte ja
            self.arten[a] = {"name": str(d.get("name") or a), "grundform": d["grundform"], "farbe": d.get("farbe") or "grau",
                             "symbol": d.get("symbol") or GRUNDFORM_SYMBOL[d["grundform"]],
                             "buchbar": bool(d.get("buchbar", d["grundform"] == "aufenthalt")),
                             "summiert": bool(d.get("summiert")), "beschreibung": d.get("beschreibung")}
            if "lesetext" in d:
                self.arten[a]["lesetext"] = self.lesetext_pruefen(wo, d["lesetext"])
            self.katalog[a] = self.definitionen(wo, d.get("merkmale") or {}, a, grundform=d["grundform"], neu=True)

    def lesetext_pruefen(self, wo, roh):
        """Gliederung des Lesetexts einer Art -> [{id, name, hilfe}] in der Reihenfolge der Datei. Nur die Form wird
        geprüft: Schlüssel, Name, bekannte Felder, kein Name doppelt."""
        aus = []
        if not isinstance(roh, dict) or not roh:
            self.fehl(f"{wo}: lesetext muss eine Liste „rubrik: {{name: …, hilfe: …}}“ sein.")
            return aus
        for k, d in roh.items():
            if not re.fullmatch(r"[a-z][a-z0-9_]*", str(k)):
                self.fehl(f"{wo}: Rubrik „{k}“: nur Kleinbuchstaben, Ziffern und _ (z. B. charakter, ankommen).")
                continue
            if not isinstance(d, dict) or not d.get("name"):
                self.fehl(f"{wo}: Rubrik {k} braucht einen Namen (name: …), er steht als Stichwort vor dem Absatz.")
                continue
            if set(d) - RUBRIK_FELDER:
                self.fehl(f"{wo}: Rubrik {k}: unbekannte Felder {', '.join(sorted(set(d) - RUBRIK_FELDER))}.")
            if any(r["name"].casefold() == str(d["name"]).casefold() for r in aus):
                self.fehl(f"{wo}: Rubrik {k}: Name „{d['name']}“ gibt es schon.")
            aus.append({"id": k, "name": str(d["name"]), "hilfe": d.get("hilfe")})
        return aus

    def grundform(self, art):
        return (self.arten.get(art) or {}).get("grundform")

    def art_von(self, eintrag, wo):
        """Art einer Unterkunft oder Nacht: art:, sonst aus typ; an Bord ohne Angabe: unterwegs. Prüft gegen arten.yaml."""
        a = eintrag.get("art") or art_schluessel(eintrag.get("typ"))
        if not a:
            if eintrag.get("an_bord"):
                return UNTERWEGS
            self.fehl(f"{wo}: braucht typ oder art (eine Art aus plan/arten.yaml).")
            return None
        if a not in self.arten:
            self.fehl(f"{wo}: Art „{a}“ steht nicht in plan/arten.yaml. Im Gespräch anlegen (docs/ontologie.md), bekannt: "
                      f"{', '.join(k for k, v in self.arten.items() if v['grundform'] == 'aufenthalt') or 'keine'}.")
            return None
        if self.grundform(a) != "aufenthalt":
            self.fehl(f"{wo}: Art „{a}“ ist {self.grundform(a)}, hier braucht es einen Aufenthalt.")
        return a

    def strecken_art(self, s, wo=None):
        """Art einer Strecke: art (Vorgabe wandern), eine Liste mehrerer Arten gilt als kombiniert. Prüft, wenn wo gegeben."""
        a = s.get("art", "wandern")
        a = KOMBINIERT if isinstance(a, list) else str(a)
        if wo and self.arten:
            if a not in self.arten:
                self.fehl(f"{wo}: Art „{a}“ steht nicht in plan/arten.yaml (Grundform bewegung). Im Gespräch anlegen.")
            elif self.grundform(a) != "bewegung":
                self.fehl(f"{wo}: Art „{a}“ ist {self.grundform(a)}, eine Strecke braucht eine Bewegung.")
        return a

    def definitionen(self, wo, roh, art, grundform=None, neu=False):
        """Merkmal-Definitionen prüfen -> {Merkmal: Definition}. neu: die Art selbst wird definiert (arten.yaml);
        sonst ergänzt eine Wahlstelle die Art oder ändert nur die Stufe eines Merkmals."""
        aus = {}
        if not isinstance(roh, dict):
            self.fehl(f"{wo}: merkmale muss eine Liste „name: {{…}}“ sein.")
            return aus
        for k, d in roh.items():
            if not re.fullmatch(r"[a-z][a-z0-9_]*", str(k)):
                self.fehl(f"{wo}: Merkmal „{k}“: nur Kleinbuchstaben, Ziffern und _ (z. B. preis, onsen).")
                continue
            if isinstance(d, dict) and set(d) == {"stufe"} and k in self.katalog.get(art, {}):
                # nur die Stufe eines Merkmals der Art ändern (Wahlstelle: aus oder wieder empfohlen)
                if stufe_fehler(d["stufe"]):
                    self.fehl(f"{wo}: Merkmal {k}: {stufe_fehler(d['stufe'])}")
                    continue
                aus[k] = {**self.katalog[art][k], "stufe": d["stufe"]}
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
            if d.get("auto") and d["auto"] not in AUTO_JE_GRUNDFORM.get(grundform or "", ()):
                self.fehl(f"{wo}: Merkmal {k}: auto „{d['auto']}“ gibt es für die Grundform {grundform or '–'} nicht; "
                          f"berechnet werden {', '.join(f'{g}: {', '.join(v)}' for g, v in AUTO_JE_GRUNDFORM.items())}.")
            if k in self.katalog.get(art, {}) and not neu:
                self.fehl(f"{wo}: Merkmal {k} gibt es für {art} schon (nur {{stufe: …}} ändert die Stufe).")
            aus[k] = {"name": d["name"], "typ": typ, **{f: d[f] for f in ("werte", "veraenderlich", "auto", "hilfe",
                                                                          "frage", "einheit", "stufe", "auch") if d.get(f)}}
        return aus

    def art_der_wahl(self, w, vid):
        """Art der Dinge, zwischen denen eine Wahlstelle wählt: bereich:, sonst aus den Optionen (erste Unterkunft, gemeinsame
        Art der Strecken, die eine Folge-Art der Reise). Ohne Art: allgemein, keine Merkmale."""
        b = w.get("bereich")
        if b:
            if b != ALLGEMEIN and b not in self.arten:
                self.fehl(f"Wahlstelle {vid}: bereich „{b}“ steht nicht in plan/arten.yaml (bekannt: {', '.join(self.arten)}).")
                return ALLGEMEIN
            return b
        opts = w.get("optionen") or []
        for o in opts:
            for u in o.get("unterkuenfte") or []:
                if self.u_art.get(u):
                    return self.u_art[u]
        arten = {self.strecken_art(self.strecken[sid]) for o in opts for sid in o.get("strecken") or [] if sid in self.strecken}
        if arten:
            a = next(iter(arten)) if len(arten) == 1 else None
            return a if a in self.arten else ALLGEMEIN
        if any(o.get("folge") is not None for o in opts):
            folgen = [a for a, d in self.arten.items() if d["grundform"] == "folge"]
            return folgen[0] if len(folgen) == 1 else ALLGEMEIN
        return ALLGEMEIN

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
                          f"Ein neues Merkmal bei der Art in plan/arten.yaml oder an der Wahlstelle anlegen.")
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
        self.arten_pruefen()
        if self.r.get("merkmale") is not None:
            self.fehl("merkmale: in routen.yaml gibt es nicht mehr. Arten und Merkmale stehen je Art in plan/arten.yaml "
                      "(docs/ontologie.md); eine Wahlstelle darf weiter eigene merkmale: ergänzen.")
        u_extra, s_extra = {}, {}
        for vid, w in self.wahl.items():
            b = self.art_der_wahl(w, vid)
            krit = dict(self.katalog.get(b, {}))
            krit.update(self.definitionen(f"Wahlstelle {vid}", w.get("merkmale") or {}, b, grundform=self.grundform(b)))
            self.kriterien[vid] = (b, krit)
            for o in w.get("optionen") or []:
                if o.get("id") in self.option:
                    self.mk_option[o["id"]] = self.werte(o["id"], o.get("merkmale"), krit)
                if self.grundform(b) == "aufenthalt":
                    for u in o.get("unterkuenfte") or []:
                        u_extra.setdefault(u, {}).update(krit)
                else:
                    for sid in o.get("strecken") or []:
                        s_extra.setdefault(sid, {}).update(krit)
        for uid, u in self.unterkuenfte.items():
            if self.u_art.get(uid) is None:   # Art unbekannt, schon gemeldet
                continue
            krit = {**self.katalog.get(self.u_art.get(uid), {}), **u_extra.get(uid, {})}
            self.mk_unterkunft[uid] = self.werte(uid, u.get("merkmale"), krit)
        for aid, a in self.aufenthalte.items():
            if self.a_art.get(aid) is not None and isinstance(a, dict):
                self.mk_aufenthalt[aid] = self.werte(aid, a.get("merkmale"), self.katalog.get(self.a_art[aid], {}))
        # Bewegungen: Werte dürfen an der Strecke stehen, wie bei Unterkünften an U-…
        for sid, st in self.strecken.items():
            if st.get("merkmale") is None:
                continue
            basis = self.katalog.get(self.strecken_art(st), {})
            self.mk_strecke[sid] = self.werte(sid, st.get("merkmale"), {**basis, **s_extra.get(sid, {})})

    def auto_werte(self, art, o):
        """Berechnete Merkmale einer Option (Kennzahlen ihrer Strecken bzw. Tage), je Grundform der Art."""
        s, g = None, self.grundform(art)
        if g == "bewegung" and o.get("strecken"):
            s = self.summe([{"strecken": o["strecken"], "nacht": None}])
        elif g == "folge" and o.get("folge"):
            s = self.option_summe(o)
        if not s:
            return {}
        f = set(s["fehlend"])
        werte = {"gehzeit": dauer(s["min"]) if s["min"] and "min" not in f else None,
                 "laenge": f"{s['km']:g} km".replace(".", ",") if s["km"] and "km" not in f else None,
                 "hoehenmeter": f"↑ {s['auf']:.0f} m, ↓ {s['ab']:.0f} m" if s["auf"] and not {"auf", "ab"} & f else None,
                 "tage": (f"{s['tage']} Tage" if s["tage"] != 1 else "1 Tag") if g == "folge" else None,
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
        b, krit = self.kriterien.get(vid, (ALLGEMEIN, {}))
        g = self.grundform(b)
        mk = {}
        if g == "aufenthalt":
            for u in (o.get("unterkuenfte") or [])[:1]:
                mk.update(self.mk_unterkunft.get(u, {}))
        elif g == "bewegung":
            for sid in (o.get("strecken") or [])[:1]:
                mk.update(self.mk_strecke.get(sid, {}))
        mk.update(self.mk_option.get(o.get("id"), {}))
        auto = self.auto_werte(b, o)
        if g == "folge":
            auto.update(self.anschluss(vid, o))
        mk.update({k: auto[d["auto"]] for k, d in krit.items() if d.get("auto") in auto})
        typ = next((self.unterkuenfte.get(u, {}).get("typ") for u in (o.get("unterkuenfte") or [])[:1]), None)
        return {k: mk[k] for k in krit if k in mk}, [k for k, d in krit.items() if zaehlt(d, typ) and k not in mk]

    def frage_wird_gebraucht(self, frage, ausser):
        """Hängt die Frage noch an einer anderen, offenen Wahlstelle? Dann bleibt sie offen, auch wenn eine entschieden ist."""
        for xid, x in self.wahl.items():
            if xid == ausser or x.get("frage") != frage:
                continue
            opts = [o for o in x.get("optionen") or [] if o.get("id") in self.option]
            if not any(self.status(o) == "gewaehlt" for o in opts) and len([o for o in opts if self.status(o) not in UNGUELTIG]) > 1:
                return True
        return False

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
            if not offen and f_offen and not self.frage_wird_gebraucht(f, vid):
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
            a = self.art_von(n, f"{tid} nacht") if (n.get("typ") or n.get("art") or n.get("an_bord")) else None
            return {"ort": n.get("ort"), "hinweis": n.get("hinweis"), "typ": n.get("typ"), "an_bord": bool(n.get("an_bord")),
                    "art": a}
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
                         "aufenthalte": [a for a in t.get("aufenthalte") or [] if a in self.aufenthalte],
                         "wahlstellen": unterwegs, "nacht": n})

        # Tage unter einer offenen Planungs-Wahlstelle sind vorläufig (#77): der Kalender zeigt nur Entschiedenes
        for vid, (a, e) in self.grenzen.items():
            w = self.wahl.get(vid) or {}
            if w.get("art") == "planung" and not any(self.status(o) == "gewaehlt" for o in w.get("optionen") or []):
                for t in tage[a:e]:
                    t.setdefault("vorlaeufig", []).append(vid)

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
                            "aufenthalte": [a for a in t.get("aufenthalte") or [] if a in self.aufenthalte],
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
            "aufenthalte": self.aufenthalte_aus(tage),
            "buchungen": {bid: self.buchung_aus(bid) for bid in self.buchungen},
            # Arten der Reise (plan/arten.yaml): Name, Grundform, Farbe, Symbol, buchbar; die Seite kennt keine Art selbst
            "arten": {a: dict(d) for a, d in self.arten.items()},
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
            r = Routen(self.r, self.etappen, self.fragen, [], lambda *a: None, self.q, zwang, self.arten_roh,
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
                # Kennzahlen (Gehzeit, Höhenmeter, Länge) summieren nur Arten mit summiert: true (aus eigener Kraft)
                if not (self.arten.get(self.strecken_art(st)) or {}).get("summiert"):
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
            a = self.u_art.get(n["unterkunft"]) if n.get("unterkunft") in self.unterkuenfte else n.get("art")
            if n and not n.get("an_bord"):
                typ = (self.arten.get(a) or {}).get("name") or "offen"
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
        b, krit = self.kriterien.get(vid, (ALLGEMEIN, {}))
        return {"bereich": b, "grundform": self.grundform(b), "kriterien": [{"id": k, **d} for k, d in krit.items()],
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
        # Bewegungen: Werte und Lücken nach der Art der Strecke (plan/arten.yaml), wie bei Unterkünften
        b = self.strecken_art(s)
        b = b if b in self.katalog else None
        mk = self.mk_strecke.get(sid, {})
        merkmale = {"bereich": b, "merkmale": mk,
                    "fehlt": [k for k, d in self.katalog[b].items() if zaehlt(d) and k not in mk]} if b else \
            ({"merkmale": mk, "fehlt": []} if mk else {})
        return {"titel": s.get("titel", sid), "von": s.get("von"), "nach": s.get("nach"), "art": s.get("art"),
                "buchung": self.buchung_von(s, b, sid), "buchung_id": self.buchung_id(sid),
                "rolle": s.get("rolle", "haupt"), "zweig_von": s.get("zweig_von"), "kennzahlen": s.get("kennzahlen") or {},
                "quelle": s.get("quelle"), "siehe": s.get("siehe"), "text": s.get("text", ""),
                "beginn": s.get("beginn"), "ende": s.get("ende"), "dossier": bool(s.get("dossier")), **merkmale}

    def buchung_von(self, d, art, did=None):
        """Buchungsstand eines Dings: der Status seiner geltenden Buchung (B-…, #76), sonst der Eintrag buchung:, sonst
        „offen“ bei einer buchbaren Art, sonst None (kein Stand)."""
        if did and did in self.buchung_je_ding:
            return str(self.buchungen[self.buchung_je_ding[did]].get("status") or "gebucht")
        if d.get("buchung") is not None:
            return str(d["buchung"])
        return "offen" if (self.arten.get(art) or {}).get("buchbar") or did in self.buchung_je_ding else None

    def buchung_id(self, did):
        """B-ID der geltenden Buchung eines Dings oder None."""
        return self.buchung_je_ding.get(did)

    def lage_aus(self, d):
        for feld in ("adresse", "punkt"):
            v = d.get(feld) if isinstance(d.get(feld), dict) else None
            yield feld, ({"wert": v.get("wert"), "quelle": v.get("quelle"), "notiz": v.get("notiz"),
                          "geprueft": v["geprueft"].isoformat() if isinstance(v.get("geprueft"), datetime.date) else None} if v else None)

    def aufenthalte_aus(self, tage):
        """Aufenthalte ohne Nacht (A-…): wie Unterkünfte, mit zeit (Text) und den Tagen, an denen sie stehen."""
        an_tagen = {}
        for t in tage:
            for aid in t.get("aufenthalte") or []:
                an_tagen.setdefault(aid, []).append(t["id"])
        aus = {}
        for aid, a in self.aufenthalte.items():
            if not isinstance(a, dict):
                continue
            art = self.a_art.get(aid)
            mk = self.mk_aufenthalt.get(aid, {})
            aus[aid] = {**{k: a.get(k) for k in ("name", "ort", "zeit", "beginn", "ende", "kontakt", "hinweis", "quelle", "frage", "buchungslink")},
                        **dict(self.lage_aus(a)), "art": art, "buchung": self.buchung_von(a, art, aid), "buchung_id": self.buchung_id(aid),
                        "tage": an_tagen.get(aid, []),
                        "merkmale": mk, "fehlt": [k for k, d in self.katalog.get(art, {}).items() if zaehlt(d) and k not in mk]}
        return aus

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
            aus[uid] = {k: u.get(k) for k in ("name", "ort", "typ", "kontakt", "hinweis", "quelle", "frage", "buchungslink")}
            # Lage (ADR-0004): Adresse und Punkt als Aussage mit Herkunft; der Bau ergänzt den Punkt aus plan/punkte.yaml
            for feld in ("adresse", "punkt"):
                v = u.get(feld) if isinstance(u.get(feld), dict) else None
                aus[uid][feld] = {"wert": v.get("wert"), "quelle": v.get("quelle"), "notiz": v.get("notiz"),
                                  "geprueft": v["geprueft"].isoformat() if isinstance(v.get("geprueft"), datetime.date) else None} if v else None
            a = self.u_art.get(uid)
            aus[uid]["art"] = a
            aus[uid]["buchung"] = self.buchung_von(u, a, uid)
            aus[uid]["buchung_id"] = self.buchung_id(uid)
            aus[uid]["naechte"] = naechte.get(uid, [])
            mk = self.mk_unterkunft.get(uid, {})
            aus[uid]["merkmale"] = mk
            aus[uid]["fehlt"] = [k for k, d in self.katalog.get(a, {}).items() if zaehlt(d, u.get("typ")) and k not in mk]
        return aus
