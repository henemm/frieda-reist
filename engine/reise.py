"""Eckdaten, Status, Personen und Einstellungen einer Reise: reisen/<reise>/reise.yaml.

Hintergrund und Entscheidungen: docs/produkt.md (26.10.2026). Die Zuordnung der Inhalte (Überschrift
-> ID) bleibt in reise.json; hier steht, was die KI sicher lesen und ändern soll, ohne Inhalte zu berühren:

  zeitraum    {von, bis} als Datum; schon in der Idee bekannt, bevor es einen Plan gibt (Paket H)
  status      idee | planung | fest | unterwegs | danach | archiv, mit Verlauf (datum, wert, wer, grund)
  personen    {schluessel: {name, rolle, reist, notiz}}; Rollen gast < mitwirkend < organisator
  bausteine   zuschaltbare Teile (Liste); Plan, Wissen, Suche und Personen sind immer da
  regeln      Spielregeln mit Wert, fehlende kommen aus VORGABEN
  darstellung Startreiter, Reiternamen, Tiefe, Gruppen, Mahnungen im Plan (mahnungen: false blendet sie dort aus)

Fehler brechen den Bau ab (wie beim Routenmodell). Fehlt reise.yaml, kommen Eckdaten und Darstellung aus
reise.json (alte Form) mit einem Hinweis; Status ist dann „planung“, Personen gibt es keine.
"""
import datetime
import re
import unicodedata

STATUS = ("idee", "planung", "fest", "unterwegs", "danach", "archiv")
ROLLEN = ("gast", "mitwirkend", "organisator")          # aufsteigend: jede Stufe enthält die darunter
# Bis 28.10.2026 hießen die Rollen reisend, einbringer, bestimmer (mitreisend: noch älter). Gelesen werden sie weiter,
# geschrieben wird nur noch ROLLEN.
ROLLEN_ALT = {"reisend": "gast", "einbringer": "mitwirkend", "bestimmer": "organisator", "mitreisend": "mitwirkend"}


def rolle_neu(rolle):
    """Alter oder neuer Rollenschlüssel -> neuer Schlüssel (Unbekanntes bleibt unverändert)."""
    return ROLLEN_ALT.get(rolle, rolle)
BAUSTEINE = ("varianten", "karte", "tagesseiten", "rueckmeldungen", "fragen", "aufgaben", "wuensche",
             "waechter", "profile")
KERN = ("plan", "wissen", "suche", "personen")           # immer da, nicht abschaltbar
NOCH_NICHT_GEBAUT = {"profile": "Stufe 3"}
VORGABEN = {
    "konflikt": "offene_frage",          # zwei Organisator:innen entscheiden verschieden -> offene Frage, Meldung an beide
    "kontingent": {"art": "punkte", "je_person": 10},   # Wunsch-Brett: punkte | anzahl
    "einladen": "organisator",             # wer Personen einladen darf: organisator | mitwirkend
    # Paket E (Wächter und Erinnerer, Baustein waechter)
    "waechter_frist_tage": 60,           # veränderliche Angaben, deren Prüfdatum älter ist, prüft der Wächter neu
    "erinnerung_vorlauf_tage": 3,        # Aufgabenfristen werden so viele Tage vorher gemeldet
    "meldekanal": ["app", "nachricht"],  # app: beim Öffnen der Claude-App; nachricht: Sammelnachricht an den Betreiber
    # Paket J (Konten): uebergang = auf der Seite geht auch ein eingetippter Name; noetig = Mitmachen nur angemeldet
    "anmeldung": "uebergang",
}
KANAELE = ("app", "nachricht")           # E-Mail an alle gibt es (noch) nicht
REGEL_WERTE = {"konflikt": ("offene_frage",),
               "einladen": ("organisator", "mitwirkend"), "anmeldung": ("uebergang", "noetig")}
# Regeln des Einarbeiten-Laufs (bis 29.10.2026, ADR-0001 Paket O-3): der Konnektor schreibt direkt, es gibt keinen Lauf
# mehr. Eine reise.yaml, die sie noch nennt, baut weiter; sie bekommt einen Hinweis und die Regeln sind ohne Wirkung.
ALTE_REGELN = ("entscheidungsweg", "sammelzeit_minuten")
KONTINGENT_ARTEN = ("punkte", "anzahl")
DARSTELLUNG = ("start", "tiefe", "varianten_titel", "plan_reiter", "gruppen", "mahnungen")
PERSON_FELDER = {"name", "rolle", "reist", "notiz", "von", "bis"}   # von/bis: reist nur einen Teil mit
ALTE_ECKDATEN = ("titel", "untertitel", "pfad", "kurz")


# ---------- Regeln, die die Maschine prüft (Paket B, docs/produkt.md) ----------
# Verhalten je Status. schreiben: alles | nachlese (Plan gesperrt, Rückmeldungen und Aufgaben gehen) | nichts.
VERHALTEN = {
    "idee":      {"warnungen": False, "luecken": False, "mahnung_planung": False, "fristen": False, "start": None,
                  "ausloeser_vor": False, "schreiben": "alles", "waechter": False},
    "planung":   {"warnungen": True, "luecken": True, "mahnung_planung": False, "fristen": False, "start": None,
                  "ausloeser_vor": False, "schreiben": "alles", "waechter": False},
    "fest":      {"warnungen": True, "luecken": True, "mahnung_planung": True, "fristen": True, "start": None,
                  "ausloeser_vor": False, "schreiben": "alles", "waechter": True},
    "unterwegs": {"warnungen": True, "luecken": True, "mahnung_planung": True, "fristen": True, "start": "heute",
                  "ausloeser_vor": True, "schreiben": "alles", "waechter": True},
    "danach":    {"warnungen": True, "luecken": True, "mahnung_planung": False, "fristen": False, "start": None,
                  "ausloeser_vor": False, "schreiben": "nachlese", "waechter": False},
    "archiv":    {"warnungen": True, "luecken": True, "mahnung_planung": False, "fristen": False, "start": None,
                  "ausloeser_vor": False, "schreiben": "nichts", "waechter": False},
}
# Schreibende Aktionen: Mindestrolle, Baustein (None: immer da) und der Grad von „schreiben“, der sie noch erlaubt.
AKTIONEN = {
    "rueckmeldung": {"rolle": "mitwirkend", "baustein": "rueckmeldungen", "ab": ("alles", "nachlese")},
    "wunsch":       {"rolle": "mitwirkend", "baustein": "wuensche", "ab": ("alles",)},
    # Paket G (Wunsch-Brett): abhaken dürfen alle Mitwirkenden, auch in der Nachlese; einplanen nur Organisator:innen
    "wunsch_erlebt":    {"rolle": "mitwirkend", "baustein": "wuensche", "ab": ("alles", "nachlese")},
    "wunsch_einplanen": {"rolle": "organisator", "baustein": "wuensche", "ab": ("alles",)},
    "aufgabe":      {"rolle": "mitwirkend", "baustein": "aufgaben", "ab": ("alles", "nachlese")},
    "alternative":  {"rolle": "mitwirkend", "baustein": "varianten", "ab": ("alles",)},
    "auftrag":      {"rolle": "organisator", "baustein": None, "ab": ("alles",)},
    # Paket C: Gespräch für alle. Entscheiden gilt für Wahlstellen (Baustein varianten); eine Antwort auf eine Frage
    # braucht den Baustein fragen; wer einladen darf, steht je Reise in regeln.einladen (hier nur die Vorgabe).
    "entscheiden":  {"rolle": "organisator", "baustein": "varianten", "ab": ("alles",)},
    "antwort":      {"rolle": "mitwirkend", "baustein": "fragen", "ab": ("alles", "nachlese")},
    "einladen":     {"rolle": "organisator", "baustein": None, "ab": ("alles", "nachlese")},
    # Paket J: eine Person aus der Reise nehmen (Konto-Verknüpfung und alte Links enden sofort)
    "entfernen":    {"rolle": "organisator", "baustein": None, "ab": ("alles", "nachlese")},
    # ADR-0001, O-3: Arten und Merkmale der Reise (ihre Ontologie) im Gespräch festlegen; Mitwirkende schlagen vor (Rückmeldung)
    "ontologie":    {"rolle": "organisator", "baustein": None, "ab": ("alles",)},
    # O-3: Werte an Unterkünften, Strecken und Optionen eintragen (mit Herkunft und Prüfdatum); Mitwirkende und Organisator:innen
    "wert":         {"rolle": "mitwirkend", "baustein": None, "ab": ("alles",)},
    # O-3: Unterkünfte, Strecken, Orte anlegen und ändern (Eingaben mit Herkunft; die Art eines Dings ändern nur Organisator:innen)
    "ding":         {"rolle": "mitwirkend", "baustein": None, "ab": ("alles",)},
    # O-3: eine offene Frage anlegen (zu klären oder zu entscheiden); Baustein fragen
    "frage":        {"rolle": "mitwirkend", "baustein": "fragen", "ab": ("alles",)},
    # O-3: den Plan ändern (Tage: Nacht, Strecken, Wahlstellen) – nur Organisator:innen
    "plan":         {"rolle": "organisator", "baustein": None, "ab": ("alles",)},
    # O-3: Wissen in eigenen Worten mit Herkunft (auch in der Nachlese); Fragen schließen und Rückmeldungen erledigen nur Organisator:innen
    "wissen":       {"rolle": "mitwirkend", "baustein": None, "ab": ("alles", "nachlese")},
    "frage_schliessen":       {"rolle": "organisator", "baustein": "fragen", "ab": ("alles", "nachlese")},
    "rueckmeldung_erledigen": {"rolle": "organisator", "baustein": "rueckmeldungen", "ab": ("alles", "nachlese")},
    # O-3: Status und Einstellungen der Reise – nur Organisator:innen, in jedem Status (auch aus dem Archiv zurück)
    "einstellung":  {"rolle": "organisator", "baustein": None, "ab": ("alles", "nachlese", "nichts")},
}
# Lesende Konnektor-Werkzeuge, die zu einem zuschaltbaren Baustein gehören
LESE_BAUSTEIN = {"offene_fragen": "fragen", "varianten": "varianten", "merkmale": "varianten",
                 "aufgaben": "aufgaben", "rueckmeldungen": "rueckmeldungen", "wuensche": "wuensche"}
ENTSCHEIDUNGEN = ("gewaehlt", "verworfen", "ersetzt")
REISE_ZIEL = "reise"    # Aufträge an dieses Ziel (Status, Einstellungen) gehen in jedem Status


def verhalten(status):
    return dict(VERHALTEN.get(status) or VERHALTEN["planung"])


def mindestrolle(aktion, regeln=None):
    """Mindestrolle einer Aktion; „einladen“ richtet sich nach regeln.einladen der Reise."""
    if aktion == "einladen":
        return rolle_neu((regeln or {}).get("einladen") or VORGABEN["einladen"])
    return AKTIONEN[aktion]["rolle"]


def erlaubt(aktion, rolle, status, bausteine, ziel=None, regeln=None):
    """Darf diese Rolle jetzt schreiben? -> (True, "") oder (False, Begründung in einfachen Worten).
    bausteine: eingeschaltete Bausteine der Reise (None: nicht bekannt, nicht prüfen).
    regeln: Spielregeln der Reise (nur für „einladen“ nötig)."""
    a = AKTIONEN[aktion]
    mind = mindestrolle(aktion, regeln)
    if not darf(rolle, mind):
        return False, (f"Mit diesem Zugang kann man nur lesen (Rolle {rolle or 'unbekannt'}). Dafür braucht man die Rolle "
                       "mitwirkend." if mind == "mitwirkend" else "Das dürfen nur Organisator:innen.")
    if a["baustein"] and bausteine is not None and a["baustein"] not in bausteine:
        return False, f"Der Baustein „{a['baustein']}“ ist bei dieser Reise ausgeschaltet."
    schreiben = verhalten(status)["schreiben"]
    if schreiben not in a["ab"] and not (aktion == "auftrag" and ziel == REISE_ZIEL):
        grund = {"nachlese": "Die Reise ist vorbei (Status danach): Der Plan ist schreibgeschützt, nur Rückmeldungen und "
                             "Aufgaben gehen noch.",
                 "nichts": "Die Reise ist archiviert: Es kann nur gelesen werden."}[schreiben]
        return False, grund + " Ein:e Organisator:in kann den Status zurücksetzen (Auftrag an „reise“)."
    return True, ""


def _klein(text, laenge):
    t = (text or "").strip().casefold()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:laenge].strip("-")


def schluessel_aus_name(name):
    """Vorname -> Schlüssel für reise.yaml personen und den Zugang: klein, ohne Umlaute und Sonderzeichen."""
    return _klein(name, 40)


# ---------- Neue Reise (Paket H, docs/neue-reise.md) ----------
PFAD_MUSTER = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")   # passt in die Ablage (rueckmeldungen.REISE_MUSTER)
MAX_NOTIZ = 4000
MAX_PERSONEN = 20


def reise_pfad(titel, jahr=None):
    """Titel (und Jahr, falls nicht schon darin) -> Ordnername der Reise, z. B. „winterwoche-allgaeu-2027“."""
    return _klein(titel if jahr is None or str(jahr) in (titel or "") else f"{titel} {jahr}", 40)


def neue_reise_pruefen(args, wer, vergeben=()):
    """Eingaben für eine neue Reise prüfen (Konnektor mit Konto-Link, Werkzeug reise_anlegen). wer: Name der anlegenden
    Person, sie wird Organisator:in. vergeben: Ordnernamen, die es schon gibt. -> (daten, None) oder (None, Grund in einfachen Worten)."""
    def zeile(k, laenge, pflicht=False):
        v = args.get(k)
        if v is None or v == "":
            return (None, f"{k} fehlt.") if pflicht else ("", None)
        if not isinstance(v, str) or "\n" in v.strip() or len(v.strip()) > laenge:
            return None, f"{k}: eine Zeile Text, höchstens {laenge} Zeichen."
        return v.strip(), None
    titel, f = zeile("titel", 80, True)
    if f:
        return None, f
    ziel, f = zeile("ziel", 80)
    if f:
        return None, f
    try:
        von, bis = (datetime.date.fromisoformat(str(args.get(k) or "")) for k in ("von", "bis"))
    except ValueError:
        return None, "von und bis als Datum angeben (JJJJ-MM-TT), z. B. 2027-02-06."
    if bis < von:
        return None, "Das Ende liegt vor dem Anfang."
    if (bis - von).days > 366:
        return None, "Eine Reise dauert hier höchstens ein Jahr."
    notiz = args.get("notiz") or ""
    if not isinstance(notiz, str) or len(notiz) > MAX_NOTIZ:
        return None, f"notiz: Text mit höchstens {MAX_NOTIZ} Zeichen."
    roh = args.get("personen") or []
    if not isinstance(roh, list) or len(roh) > MAX_PERSONEN:
        return None, f"personen: Liste mit höchstens {MAX_PERSONEN} Personen."
    if not wer:
        return None, "Eine Reise anlegen geht nur mit einem persönlichen Konto-Link."
    personen = {}
    for p in [{"vorname": wer, "rolle": "organisator"}] + roh:
        if not isinstance(p, dict) or not isinstance(p.get("vorname"), str) or not p["vorname"].strip() \
                or "\n" in p["vorname"].strip() or len(p["vorname"].strip()) > 80:
            return None, "Jede Person braucht einen Vornamen (eine Zeile)."
        name, rolle = p["vorname"].strip(), rolle_neu(p.get("rolle") or "mitwirkend")
        if rolle not in ROLLEN:
            return None, f"{name}: Rolle muss eine von {', '.join(ROLLEN)} sein."
        k = schluessel_aus_name(name)
        if not k:
            return None, f"{name}: Aus dem Namen lässt sich kein Schlüssel bilden."
        if k in personen:
            if name.casefold() == wer.casefold() and personen[k]["name"] == wer:
                if rolle != "organisator":
                    return None, f"{wer} legt die Reise an und bestimmt deshalb mit (Rolle organisator)."
                eintrag = personen[k]
            else:
                return None, f"{name} steht zweimal in der Liste."
        else:
            eintrag = personen[k] = {"name": name, "rolle": rolle}
        if p.get("reist") is False:
            eintrag["reist"] = False
        if isinstance(p.get("notiz"), str) and p["notiz"].strip():
            if "\n" in p["notiz"].strip() or len(p["notiz"].strip()) > 300:
                return None, f"{name}: Notiz in einer Zeile, höchstens 300 Zeichen."
            eintrag["notiz"] = p["notiz"].strip()
    pfad = args.get("pfad") or reise_pfad(titel, von.year)
    if not isinstance(pfad, str) or not PFAD_MUSTER.match(pfad):
        return None, "pfad: nur Kleinbuchstaben, Ziffern und Bindestrich, 2 bis 40 Zeichen."
    if pfad in vergeben:
        return None, (f"Eine Reise mit dem Ordnernamen „{pfad}“ gibt es schon oder ist angefragt. Bitte einen anderen "
                      "Titel oder pfad wählen.")
    return {"titel": titel, "von": von.isoformat(), "bis": bis.isoformat(), "ziel": ziel, "pfad": pfad,
            "personen": personen, "wer": wer, "notiz": notiz.strip()}, None


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
    """Rolle erreicht die Stufe? darf("organisator", "mitwirkend") -> True."""
    rolle, mindestens = rolle_neu(rolle), rolle_neu(mindestens)
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

    def zeitraum(self):
        """Zeitraum der Reise {von, bis} (ISO), schon vor dem Plan; fehlt er, None."""
        z = self.r.get("zeitraum")
        if z is None:
            return None
        if not isinstance(z, dict) or set(z) != {"von", "bis"} \
                or not all(isinstance(z[k], datetime.date) for k in ("von", "bis")):
            self.fehl("zeitraum muss {von: JJJJ-MM-TT, bis: JJJJ-MM-TT} sein.")
            return None
        if z["bis"] < z["von"]:
            self.fehl(f"zeitraum: bis ({z['bis']}) liegt vor von ({z['von']}).")
            return None
        return {"von": z["von"].isoformat(), "bis": z["bis"].isoformat()}

    def status(self):
        if self.alt:
            return {"wert": "planung", "verlauf": []}
        st = self.r.get("status")
        if not isinstance(st, dict) or st.get("wert") not in STATUS:
            self.fehl(f"status.wert muss eines von {', '.join(STATUS)} sein.")
            return {"wert": "planung", "verlauf": []}
        verlauf = st.get("verlauf") or []
        vorher = None
        organisator = self.organisator_namen()
        for e in verlauf:
            if not isinstance(e, dict):
                self.fehl("status.verlauf: Eintrag muss {datum, wert, wer, grund} sein.")
                continue
            if e.get("wert") not in STATUS:
                self.fehl(f"status.verlauf: Status „{e.get('wert')}“ unbekannt.")
            if e.get("wer") not in organisator:
                self.fehl(f"status.verlauf: den Status darf nur ein:e Organisator:in setzen "
                          f"({', '.join(sorted(organisator)) or 'keiner eingetragen'}), steht: {e.get('wer')}.")
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
            if rolle_neu(p.get("rolle")) not in ROLLEN:
                self.fehl(f"Person „{k}“: rolle muss eines von {', '.join(ROLLEN)} sein.")
                continue
            unbekannt = set(p) - PERSON_FELDER
            if unbekannt:
                self.fehl(f"Person „{k}“: unbekannte Felder {', '.join(sorted(unbekannt))}.")
            if p["name"] in namen:
                self.fehl(f"Name „{p['name']}“ kommt zweimal vor; Namen müssen eindeutig sein.")
            namen.add(p["name"])
            teil = {}
            for f in ("von", "bis"):   # reist nur einen Teil mit (Reiseüberblick: „Karl ab 14.5.“)
                if p.get(f) is None:
                    continue
                if isinstance(p[f], datetime.date):
                    teil[f] = p[f].isoformat()
                else:
                    self.fehl(f"Person „{k}“: {f} muss ein Datum sein (JJJJ-MM-TT).")
            aus.append({"schluessel": str(k), "name": p["name"], "rolle": rolle_neu(p["rolle"]),
                        "reist": bool(p.get("reist", True)), "notiz": p.get("notiz") or "", **teil})
        if not self.alt and not any(p["rolle"] == "organisator" for p in aus):
            self.fehl("Mindestens eine Person braucht die Rolle organisator.")
        return aus

    def organisator_namen(self):
        roh = self.r.get("personen") or {}
        if not isinstance(roh, dict):   # Fehlermeldung kommt aus personen()
            return set()
        return {p.get("name") for p in roh.values() if isinstance(p, dict) and rolle_neu(p.get("rolle")) == "organisator"}

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
            if k in ALTE_REGELN:
                self.hinweise.append(f"reise.yaml: regeln.{k} gibt es seit dem 29.10.2026 nicht mehr (der Konnektor schreibt "
                                     "direkt, kein Einarbeiten-Lauf); der Eintrag ist ohne Wirkung und kann weg.")
            elif k not in VORGABEN:
                self.fehl(f"unbekannte Regel „{k}“ (bekannt: {', '.join(VORGABEN)}).")
        r = regeln_mit_vorgaben({k: v for k, v in eigen.items() if k in VORGABEN})
        r["einladen"] = rolle_neu(r["einladen"])
        for k, erlaubt in REGEL_WERTE.items():
            if r[k] not in erlaubt:
                self.fehl(f"regeln.{k} muss eines von {', '.join(erlaubt)} sein.")
        kt = r["kontingent"]
        if kt.get("art") not in KONTINGENT_ARTEN:
            self.fehl(f"regeln.kontingent.art muss {' oder '.join(KONTINGENT_ARTEN)} sein.")
        if not isinstance(kt.get("je_person"), int) or isinstance(kt.get("je_person"), bool) or kt["je_person"] < 0:
            self.fehl("regeln.kontingent.je_person muss eine ganze Zahl ab 0 sein.")
        for k, kleinste in (("waechter_frist_tage", 1), ("erinnerung_vorlauf_tage", 0)):
            if not isinstance(r[k], int) or isinstance(r[k], bool) or r[k] < kleinste:
                self.fehl(f"regeln.{k} muss eine ganze Zahl ab {kleinste} sein.")
        kanal = r["meldekanal"]
        if not isinstance(kanal, list) or not kanal or not all(isinstance(x, str) for x in kanal):
            self.fehl(f"regeln.meldekanal muss eine Liste aus {', '.join(KANAELE)} sein.")
        elif set(kanal) - set(KANAELE):
            self.fehl(f"regeln.meldekanal: {', '.join(sorted(set(kanal) - set(KANAELE)))} gibt es nicht "
                      f"(möglich: {', '.join(KANAELE)}; E-Mail an alle ist noch nicht gebaut).")
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
                "start": quelle.get("start"), "mahnungen": quelle.get("mahnungen", True) is not False}

    def daten(self):
        """-> Eintrag „reise“ für daten.json; Fehler stehen danach in self.fehler."""
        if not self.alt:
            for k in self.r:
                if k not in ALTE_ECKDATEN + ("zeitraum", "status", "personen", "bausteine", "regeln", "darstellung"):
                    self.fehl(f"unbekannter Schlüssel „{k}“.")
        d = self.eckdaten()
        d.update(self.darstellung())
        d["zeitraum"] = None if self.alt else self.zeitraum()
        d["status"] = self.status()
        d["personen"] = self.personen()
        d["bausteine"] = self.bausteine()
        d["regeln"] = self.regeln()
        d["verhalten"] = verhalten(d["status"]["wert"])
        return d
