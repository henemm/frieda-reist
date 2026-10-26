"""Eckdaten, Status, Personen und Einstellungen einer Reise: reisen/<reise>/reise.yaml.

Hintergrund und Entscheidungen: docs/produkt.md (26.10.2026). Die Zuordnung der Inhalte (Überschrift
-> ID) bleibt in reise.json; hier steht, was die KI sicher lesen und ändern soll, ohne Inhalte zu berühren:

  status      idee | planung | fest | unterwegs | danach | archiv, mit Verlauf (datum, wert, wer, grund)
  personen    {schluessel: {name, rolle, reist, notiz}}; Rollen reisend < einbringer < bestimmer
  bausteine   zuschaltbare Teile (Liste); Plan, Wissen, Suche und Personen sind immer da
  regeln      Spielregeln mit Wert, fehlende kommen aus VORGABEN
  darstellung Startreiter, Reiternamen, Tiefe, Gruppen

Fehler brechen den Bau ab (wie beim Routenmodell). Fehlt reise.yaml, kommen Eckdaten und Darstellung aus
reise.json (alte Form) mit einem Hinweis; Status ist dann „planung“, Personen gibt es keine.
"""
import datetime

STATUS = ("idee", "planung", "fest", "unterwegs", "danach", "archiv")
ROLLEN = ("reisend", "einbringer", "bestimmer")          # aufsteigend: jede Stufe enthält die darunter
BAUSTEINE = ("varianten", "karte", "tagesseiten", "rueckmeldungen", "fragen", "aufgaben", "wuensche",
             "waechter", "profile")
KERN = ("plan", "wissen", "suche", "personen")           # immer da, nicht abschaltbar
NOCH_NICHT_GEBAUT = {"waechter": "Stufe 2", "profile": "Stufe 3"}
VORGABEN = {
    "entscheidungsweg": "direkt",        # direkt (im Gespräch, geprüft) | auftrag (Prüfung vor Übernahme)
    "konflikt": "offene_frage",          # zwei Bestimmer entscheiden verschieden -> offene Frage, Meldung an beide
    "kontingent": {"art": "punkte", "je_person": 10},   # Wunsch-Brett: punkte | anzahl
    "einladen": "bestimmer",             # wer Personen einladen darf: bestimmer | einbringer
    "sammelzeit_minuten": 5,             # Eingaben sammeln, bevor das Einarbeiten startet
}
REGEL_WERTE = {"entscheidungsweg": ("direkt", "auftrag"), "konflikt": ("offene_frage",),
               "einladen": ("bestimmer", "einbringer")}
KONTINGENT_ARTEN = ("punkte", "anzahl")
DARSTELLUNG = ("start", "tiefe", "varianten_titel", "plan_reiter", "gruppen")
PERSON_FELDER = {"name", "rolle", "reist", "notiz"}
ALTE_ECKDATEN = ("titel", "untertitel", "pfad", "kurz")


# ---------- Regeln, die die Maschine prüft (Paket B, docs/produkt.md) ----------
# Verhalten je Status. schreiben: alles | nachlese (Plan gesperrt, Rückmeldungen und Aufgaben gehen) | nichts.
VERHALTEN = {
    "idee":      {"warnungen": False, "luecken": False, "mahnung_planung": False, "fristen": False, "start": None,
                  "ausloeser_vor": False, "schreiben": "alles"},
    "planung":   {"warnungen": True, "luecken": True, "mahnung_planung": False, "fristen": False, "start": None,
                  "ausloeser_vor": False, "schreiben": "alles"},
    "fest":      {"warnungen": True, "luecken": True, "mahnung_planung": True, "fristen": True, "start": None,
                  "ausloeser_vor": False, "schreiben": "alles"},
    "unterwegs": {"warnungen": True, "luecken": True, "mahnung_planung": True, "fristen": True, "start": "heute",
                  "ausloeser_vor": True, "schreiben": "alles"},
    "danach":    {"warnungen": True, "luecken": True, "mahnung_planung": False, "fristen": False, "start": None,
                  "ausloeser_vor": False, "schreiben": "nachlese"},
    "archiv":    {"warnungen": True, "luecken": True, "mahnung_planung": False, "fristen": False, "start": None,
                  "ausloeser_vor": False, "schreiben": "nichts"},
}
# Schreibende Aktionen: Mindestrolle, Baustein (None: immer da) und der Grad von „schreiben“, der sie noch erlaubt.
AKTIONEN = {
    "rueckmeldung": {"rolle": "einbringer", "baustein": "rueckmeldungen", "ab": ("alles", "nachlese")},
    "wunsch":       {"rolle": "einbringer", "baustein": "wuensche", "ab": ("alles",)},
    "aufgabe":      {"rolle": "einbringer", "baustein": "aufgaben", "ab": ("alles", "nachlese")},
    "alternative":  {"rolle": "einbringer", "baustein": "varianten", "ab": ("alles",)},
    "auftrag":      {"rolle": "bestimmer", "baustein": None, "ab": ("alles",)},
}
# Lesende Konnektor-Werkzeuge, die zu einem zuschaltbaren Baustein gehören
LESE_BAUSTEIN = {"offene_fragen": "fragen", "varianten": "varianten", "merkmale": "varianten",
                 "aufgaben": "aufgaben", "rueckmeldungen": "rueckmeldungen"}
ENTSCHEIDUNGEN = ("gewaehlt", "verworfen", "ersetzt")
REISE_ZIEL = "reise"    # Aufträge an dieses Ziel (Status, Einstellungen) gehen in jedem Status


def verhalten(status):
    return dict(VERHALTEN.get(status) or VERHALTEN["planung"])


def erlaubt(aktion, rolle, status, bausteine, ziel=None):
    """Darf diese Rolle jetzt schreiben? -> (True, "") oder (False, Begründung in einfachen Worten).
    bausteine: eingeschaltete Bausteine der Reise (None: nicht bekannt, nicht prüfen)."""
    a = AKTIONEN[aktion]
    if not darf(rolle, a["rolle"]):
        return False, (f"Mit diesem Zugang kann man nur lesen (Rolle {rolle or 'unbekannt'}). Dafür braucht man die Rolle "
                       "einbringer." if a["rolle"] == "einbringer" else "Das dürfen nur Bestimmer.")
    if a["baustein"] and bausteine is not None and a["baustein"] not in bausteine:
        return False, f"Der Baustein „{a['baustein']}“ ist bei dieser Reise ausgeschaltet."
    schreiben = verhalten(status)["schreiben"]
    if schreiben not in a["ab"] and not (aktion == "auftrag" and ziel == REISE_ZIEL):
        grund = {"nachlese": "Die Reise ist vorbei (Status danach): Der Plan ist schreibgeschützt, nur Rückmeldungen und "
                             "Aufgaben gehen noch.",
                 "nichts": "Die Reise ist archiviert: Es kann nur gelesen werden."}[schreiben]
        return False, grund + " Ein Bestimmer kann den Status zurücksetzen (Auftrag an „reise“)."
    return True, ""


def stelle(ziel):
    """Wahlstelle, zu der ein Ziel gehört: V-01.a -> V-01, sonst das Ziel selbst."""
    return str(ziel).split(".")[0]


def widerspruch(a, b):
    """Zwei Entscheidungen {wer, ziel, entscheidung} von verschiedenen Personen widersprechen sich, wenn sie dasselbe
    Ziel verschieden entscheiden oder an einer Wahlstelle zwei verschiedene Optionen wählen."""
    if a["wer"] == b["wer"] or stelle(a["ziel"]) != stelle(b["ziel"]):
        return False
    if a["ziel"] == b["ziel"]:
        return a["entscheidung"] != b["entscheidung"]
    return a["entscheidung"] == b["entscheidung"] == "gewaehlt"


def konflikte(neu, bisherige):
    """Entscheidungen aus bisherige, die neu widersprechen."""
    return [b for b in bisherige if widerspruch(neu, b)]


def darf(rolle, mindestens):
    """Rolle erreicht die Stufe? darf("bestimmer", "einbringer") -> True."""
    return rolle in ROLLEN and mindestens in ROLLEN and ROLLEN.index(rolle) >= ROLLEN.index(mindestens)


def regeln_mit_vorgaben(eigen):
    r = dict(VORGABEN)
    r["kontingent"] = dict(VORGABEN["kontingent"])
    for k, v in (eigen or {}).items():
        if k == "kontingent" and isinstance(v, dict):
            r["kontingent"].update(v)
        else:
            r[k] = v
    return r


class Reise:
    def __init__(self, roh, cfg, fehler, hinweise, quelle="reise.yaml"):
        """roh: geladenes reise.yaml (None, wenn die Datei fehlt). cfg: reise.json (für die alte Form).
        fehler/hinweise: Listen des Bauers, in die geschrieben wird."""
        self.alt = roh is None
        self.r = roh or {}
        self.cfg = cfg or {}
        self.fehler = fehler
        self.hinweise = hinweise
        self.q = quelle

    def fehl(self, text):
        self.fehler.append(f"{self.q}: {text}")

    # ---------- Teile ----------
    def eckdaten(self):
        quelle = self.cfg if self.alt else self.r
        if self.alt:
            self.hinweise.append("reise.yaml fehlt: Eckdaten und Darstellung kommen aus reise.json (alte Form); "
                                 "Status planung, keine Personen. Siehe docs/produkt.md.")
        else:
            for k in ALTE_ECKDATEN + DARSTELLUNG + ("funktionen",):
                if k in self.cfg:
                    self.fehl(f"„{k}“ steht noch in reise.json; es gehört nach reise.yaml"
                              + (" (bausteine)" if k == "funktionen" else " (darstellung)" if k in DARSTELLUNG else "")
                              + ".")
        e = {k: quelle.get(k) for k in ALTE_ECKDATEN}
        for k in ("titel", "pfad"):
            if not isinstance(e.get(k), str) or not e[k].strip():
                self.fehl(f"„{k}“ fehlt.")
        e["untertitel"] = e.get("untertitel") or ""
        return e

    def status(self):
        if self.alt:
            return {"wert": "planung", "verlauf": []}
        st = self.r.get("status")
        if not isinstance(st, dict) or st.get("wert") not in STATUS:
            self.fehl(f"status.wert muss eines von {', '.join(STATUS)} sein.")
            return {"wert": "planung", "verlauf": []}
        verlauf = st.get("verlauf") or []
        vorher = None
        bestimmer = self.bestimmer_namen()
        for e in verlauf:
            if not isinstance(e, dict):
                self.fehl("status.verlauf: Eintrag muss {datum, wert, wer, grund} sein.")
                continue
            if e.get("wert") not in STATUS:
                self.fehl(f"status.verlauf: Status „{e.get('wert')}“ unbekannt.")
            if e.get("wer") not in bestimmer:
                self.fehl(f"status.verlauf: den Status darf nur ein Bestimmer setzen "
                          f"({', '.join(sorted(bestimmer)) or 'keiner eingetragen'}), steht: {e.get('wer')}.")
            d = e.get("datum")
            if not isinstance(d, datetime.date):
                self.fehl("status.verlauf: Eintrag ohne gültiges Datum (JJJJ-MM-TT).")
            elif vorher and d < vorher:
                self.fehl("status.verlauf ist nicht zeitlich sortiert.")
            else:
                vorher = d
        if not verlauf:
            self.fehl("status braucht einen Verlauf (wer hat ihn wann gesetzt).")
        elif isinstance(verlauf[-1], dict) and verlauf[-1].get("wert") != st["wert"]:
            self.fehl(f"status.wert ({st['wert']}) passt nicht zum letzten Verlaufseintrag ({verlauf[-1].get('wert')}).")
        return {"wert": st["wert"],
                "verlauf": [{**e, "datum": e["datum"].isoformat()} for e in verlauf
                            if isinstance(e, dict) and isinstance(e.get("datum"), datetime.date)]}

    def personen(self):
        roh = self.r.get("personen") or {}
        if not isinstance(roh, dict):
            self.fehl("personen muss „schluessel: {name, rolle, reist}“ sein.")
            return []
        aus, namen = [], set()
        for k, p in roh.items():
            if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not p["name"].strip():
                self.fehl(f"Person „{k}“ braucht einen Namen.")
                continue
            if p.get("rolle") not in ROLLEN:
                self.fehl(f"Person „{k}“: rolle muss eines von {', '.join(ROLLEN)} sein.")
                continue
            unbekannt = set(p) - PERSON_FELDER
            if unbekannt:
                self.fehl(f"Person „{k}“: unbekannte Felder {', '.join(sorted(unbekannt))}.")
            if p["name"] in namen:
                self.fehl(f"Name „{p['name']}“ kommt zweimal vor; Namen müssen eindeutig sein.")
            namen.add(p["name"])
            aus.append({"schluessel": str(k), "name": p["name"], "rolle": p["rolle"],
                        "reist": bool(p.get("reist", True)), "notiz": p.get("notiz") or ""})
        if not self.alt and not any(p["rolle"] == "bestimmer" for p in aus):
            self.fehl("Mindestens eine Person braucht die Rolle bestimmer.")
        return aus

    def bestimmer_namen(self):
        roh = self.r.get("personen") or {}
        return {p.get("name") for p in roh.values() if isinstance(p, dict) and p.get("rolle") == "bestimmer"}

    def bausteine(self):
        if self.alt:
            return [b for b in BAUSTEINE if b not in NOCH_NICHT_GEBAUT and b != "wuensche"]
        roh = self.r.get("bausteine")
        if roh is None:
            self.fehl("bausteine fehlt (Liste; leer heißt nur der Kern).")
            return []
        if not isinstance(roh, list):
            self.fehl("bausteine muss eine Liste sein.")
            return []
        aus = []
        for b in roh:
            if b in KERN:
                self.hinweise.append(f"reise.yaml: „{b}“ ist Kern und immer da; der Eintrag unter bausteine ist unnötig.")
            elif b not in BAUSTEINE:
                self.fehl(f"unbekannter Baustein „{b}“ (bekannt: {', '.join(BAUSTEINE)}).")
            elif b in aus:
                self.fehl(f"Baustein „{b}“ steht zweimal.")
            else:
                if b in NOCH_NICHT_GEBAUT:
                    self.hinweise.append(f"reise.yaml: Baustein „{b}“ ist eingeschaltet, aber noch nicht gebaut "
                                         f"({NOCH_NICHT_GEBAUT[b]}).")
                aus.append(b)
        return aus

    def regeln(self):
        eigen = self.r.get("regeln") or {}
        if not isinstance(eigen, dict):
            self.fehl("regeln muss „regel: wert“ sein.")
            eigen = {}
        for k in eigen:
            if k not in VORGABEN:
                self.fehl(f"unbekannte Regel „{k}“ (bekannt: {', '.join(VORGABEN)}).")
        r = regeln_mit_vorgaben({k: v for k, v in eigen.items() if k in VORGABEN})
        for k, erlaubt in REGEL_WERTE.items():
            if r[k] not in erlaubt:
                self.fehl(f"regeln.{k} muss eines von {', '.join(erlaubt)} sein.")
        kt = r["kontingent"]
        if kt.get("art") not in KONTINGENT_ARTEN:
            self.fehl(f"regeln.kontingent.art muss {' oder '.join(KONTINGENT_ARTEN)} sein.")
        if not isinstance(kt.get("je_person"), int) or isinstance(kt.get("je_person"), bool) or kt["je_person"] < 0:
            self.fehl("regeln.kontingent.je_person muss eine ganze Zahl ab 0 sein.")
        s = r["sammelzeit_minuten"]
        if not isinstance(s, int) or isinstance(s, bool) or s < 0:
            self.fehl("regeln.sammelzeit_minuten muss eine ganze Zahl ab 0 sein.")
        return r

    def darstellung(self):
        quelle = self.cfg if self.alt else (self.r.get("darstellung") or {})
        if not isinstance(quelle, dict):
            self.fehl("darstellung muss „schluessel: wert“ sein.")
            quelle = {}
        if not self.alt:
            for k in quelle:
                if k not in DARSTELLUNG:
                    self.fehl(f"darstellung: unbekannter Schlüssel „{k}“ (bekannt: {', '.join(DARSTELLUNG)}).")
        return {"gruppen": quelle.get("gruppen") or {}, "tiefe": bool(quelle.get("tiefe")),
                "plan_reiter": quelle.get("plan_reiter"), "varianten_titel": quelle.get("varianten_titel", "Varianten"),
                "start": quelle.get("start")}

    def daten(self):
        """-> Eintrag „reise“ für daten.json; Fehler stehen danach in self.fehler."""
        if not self.alt:
            for k in self.r:
                if k not in ALTE_ECKDATEN + ("status", "personen", "bausteine", "regeln", "darstellung"):
                    self.fehl(f"unbekannter Schlüssel „{k}“.")
        d = self.eckdaten()
        d.update(self.darstellung())
        d["status"] = self.status()
        d["personen"] = self.personen()
        d["bausteine"] = self.bausteine()
        d["regeln"] = self.regeln()
        d["verhalten"] = verhalten(d["status"]["wert"])
        return d
