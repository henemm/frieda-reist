#!/usr/bin/env python3
"""Rückmeldungen von der Reise-Seite – der Eingang der Reise.


Die Seite schickt Kommentare, Fragen, Korrekturen und Ergänzungen zu einer ID (T-01, V-03.a, E-07 …)
an diesen Dienst. Er hängt sie an <ablage>/<reise>/eingang.jsonl an. Eine Organisator:in arbeitet sie im AI-Client
über den Konnektor ein (prüfen, mit den Schreibwerkzeugen eintragen, rueckmeldung_erledigen; ADR-0001) und setzt so
den Status mit Kommentar in <ablage>/<reise>/status.json; die Seite zeigt Status und Kommentar an.
Wünsche (Art „Wunsch“, Ziel „wuensche“) sind Ideen der Mitreisenden ohne feste Stelle; die Seite zeigt sie im
Reiter „Wünsche“, wenn die Reise ihn einschaltet (reise.yaml bausteine).
Änderungsaufträge (A-…, auftraege.jsonl) gab es bis zum 29.10.2026; alte bleiben lesbar, liste und setze behandeln
sie wie Rückmeldungen.

Aufgaben (AG-01 …, 24.10.2026): hängen an einer oder mehreren IDs, haben Zuständig, Priorität,
„ab“ und Frist, Status und Verlauf. Alle dürfen sie sofort anlegen und ändern (Seite und Claude-App).
Sie liegen live in <ablage>/<reise>/aufgaben.json, nicht im Repo; dieser Dienst ist ihr einziger Schreiber.
Nichts wird gelöscht: nicht mehr Nötiges bekommt den Status „entfaellt“.

Wunsch-Brett (Paket G, 27.10.2026): Punkte, „eingeplant“ und „erlebt“ zu jedem Wunsch liegen live in
<ablage>/<reise>/brett.json (siehe wunsch_aendern); die Spalte des Bretts wird berechnet.

Ein Dienst für alle Reisen. Eine Reise nimmt nur Rückmeldungen an, wenn ihr Ordner in der Ablage
existiert (legt das Veröffentlichen an). Die Ablage liegt außerhalb des Repos und außerhalb der Web-Ordner.

Aufrufe:
  python3 engine/rueckmeldungen.py liste <reise> [--alle]          neue und Konflikte (bzw. alle) zeigen, mit Aufträgen
  python3 engine/rueckmeldungen.py setze <reise> R-…|A-… STATUS [KOMMENTAR]
        STATUS: uebernommen | verworfen | rueckfrage | konflikt | neu
  python3 engine/rueckmeldungen.py aufgaben <reise> [--alle]       offene (bzw. alle) Aufgaben zeigen
  python3 engine/rueckmeldungen.py dienst                          Dienst starten
        Umgebung: RM_ABLAGE (Standard aus engine/instanz.py: <Seiten>/_rueckmeldungen),
                  RM_HOST (127.0.0.1), RM_PORT (8771)

HTTP (hinter nginx, Präfix /<reise>-<token>/api/ -> /<reise>/):
  GET    /<reise>/rueckmeldungen          alle, neueste zuerst, mit Status und Kommentar
  POST   /<reise>/rueckmeldungen          neue Rückmeldung (JSON)
  DELETE /<reise>/rueckmeldungen/<R-id>   zurückziehen, nur solange der Status „neu“ ist
  GET    /<reise>/aufgaben                alle Aufgaben
  POST   /<reise>/aufgaben                neue Aufgabe (JSON, name = wer sie anlegt) -> AG-…
  PATCH  /<reise>/aufgaben/<AG-id>        Felder ändern, Status setzen, Kommentar in den Verlauf (name = wer)
  GET    /<reise>/brett                   Wunsch-Brett: Wünsche mit Spalte, Punkten, Vorschlag; Bilanz je Person
  PATCH  /<reise>/rueckmeldungen/<R-id>   Wunsch auf dem Brett: punkte, erlebt, eingeplant (+ bezug), kommentar (name = wer);
                                          eingeplant nur vom Konnektor oder angemeldeten Organisator:innen
  PATCH  /<reise>/rueckmeldungen/<R-id|A-id>  nur vom Konnektor (Organisator:in erledigt im Gespräch): {status, kommentar} setzt
                                          uebernommen, verworfen oder rueckfrage mit Kommentar für die Seite (O-3)
  GET    /<reise>/ich                     angemeldet als (Konto, Person der Reise), Regel anmeldung, Basis-Adresse
  GET    /<reise>/belege[?buchung=B-01]   Belege zu Buchungen, die die Person sehen darf (engine/belege.py, #76)
  GET    /<reise>/belege/<D-id>           die Datei selbst (PDF, Bild), wenn die Person sie sehen darf
  POST   /<reise>/belege/<B-id>           Datei hochladen (Body = Datei, X-Frieda-Datei = Name, ?name= bei eingetipptem Namen)
  PATCH  /<reise>/belege/<D-id>           {sichtbar: beteiligte | alle} (Organisator:in), {zurueckziehen: true} (wer hochlud, Organisator:in)
  GET    /<reise>/gesund                  200, wenn die Ablage beschreibbar ist (für die Überwachung)

Wer schreibt (Paket J, docs/konten.md): Der Konnektor schickt das Dienst-Geheimnis (X-Frieda-Dienst) und den Namen der
Person, die er erkannt hat. Alles andere gilt als Seite: Name und Rolle kommen aus der Sitzung (Cookie __Host-frieda,
Origin muss Friedas Adresse sein) und der Mitgliedschaft; ohne Sitzung 401, ohne Mitgliedschaft 403. Solange die Reise
die Regel anmeldung: uebergang hat, geht auf der Seite auch ein eingetippter Name (wie bisher).
"""
import datetime
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import belege as bl  # noqa: E402
import instanz  # noqa: E402
import konten  # noqa: E402
import reise as rg  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent
# Wunsch: Idee für die Reise (Ort, Erlebnis, Essen) ohne feste Stelle, ziel = WUNSCH_ZIEL (25.10.2026)
ARTEN = {"Kommentar", "Frage", "Korrektur", "Ergänzung", "Antwort", "Wunsch"}
WUNSCH_ZIEL = "wuensche"
# konflikt: Entscheidung widerspricht einer anderen (reise.konflikte); wartet auf eine offene Frage, wird nicht eingearbeitet
STATUSWERTE = {"neu", "uebernommen", "verworfen", "rueckfrage", "konflikt"}
LAENGE = {"ziel": 80, "text": 4000, "quelle": 300, "name": 80}
ZIEL_MUSTER = re.compile(r"^[A-Za-z0-9][\w.\-]{0,79}$", re.ASCII)
REISE_MUSTER = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
RID_MUSTER = re.compile(r"^R-\d{8}-\d{6}-[0-9a-f]{4}$")
AID_MUSTER = re.compile(r"^A-\d{8}-\d{6}-[0-9a-f]{4}$")   # Änderungsaufträge (Übergang, bis O-3 sie abschafft)
MAX_BODY = 16 * 1024
MAX_JE_MINUTE = 30
DOPPELT_SEKUNDEN = 600   # identische Rückmeldung innerhalb dieser Zeit = Doppelklick / erneut gesendet
INHALT = ("name", "art", "ziel", "text", "quelle")

AG_MUSTER = re.compile(r"^AG-\d{2,}$")
AG_STATUS = ("offen", "in_arbeit", "erledigt", "entfaellt")
AG_PRIO = ("hoch", "normal", "niedrig")
AG_LAENGE = {"titel": 200, "zustaendig": 80, "notiz": 2000, "kommentar": 500, "name": 80}
AG_FELDER = ("titel", "bezug", "zustaendig", "prioritaet", "ab", "frist", "notiz", "status")
MAX_BEZUG = 10
MAX_AUFGABEN = 2000

_sperre = threading.Lock()
_zeiten = {}


def ablage():
    return instanz.ablage()


NEU = "_neu"   # Ablage für Anfragen nach neuen Reisen und Meldungen an Konten (gehört zu keiner Reise, Paket H)


def ordner_neu(anlegen=False):
    p = ablage() / NEU
    if anlegen:
        p.mkdir(parents=True, exist_ok=True)
    return p if p.is_dir() else None


def ordner(reise):
    """Ordner einer Reise oder None, wenn die Reise keine Rückmeldungen annimmt."""
    if not REISE_MUSTER.match(reise or ""):
        return None
    p = ablage() / reise
    return p if p.is_dir() else None


# ---------- Regeln der Reise (Rolle, Status, Bausteine) ----------

def seiten():
    return instanz.seiten()


def buchung_bekannt(reise, bid):
    """Gibt es die Buchung B-… in der veröffentlichten Seite der Reise (route.buchungen)?"""
    try:
        alles = json.loads((seiten() / reise / "daten.json").read_text(encoding="utf-8"))
        return bid in ((alles.get("route") or {}).get("buchungen") or {})
    except (OSError, ValueError, AttributeError):
        return False


def seher(ident, z, getippt=None):
    """Wer sieht Belege: -> (Name, Rolle). Angemeldet: Person der Reise; der Konnektor nennt den Namen; die Seite ohne
    Anmeldung ist Gast (sieht nur für alle freigegebene Belege; ein eingetippter Name öffnet keine fremden Belege)."""
    if ident["art"] == "dienst":
        return getippt, rolle_von(z, getippt) if getippt else None
    if ident["art"] == "konto":
        p = ident.get("person")
        return (p["name"], rg.rolle_neu(p.get("rolle"))) if p else (None, "gast")   # angemeldet, aber nicht in der Reise: wie ein Gast
    return None, "gast"


def zustand(reise):
    """Status, Bausteine, Personen und Regeln aus der veröffentlichten Seite (<seiten>/<reise>/daten.json) oder None,
    wenn sie nicht lesbar ist (dann gelten nur die technischen Prüfungen, wie bisher). Eingeladene Personen, die noch
    nicht in reise.yaml stehen, zählen schon (einladungen.json)."""
    try:
        alles = json.loads((seiten() / reise / "daten.json").read_text(encoding="utf-8"))
        d = alles["reise"]
        return {"status": d["status"]["wert"], "bausteine": d["bausteine"], "regeln": d.get("regeln") or {},
                "personen": personen_mit_einladungen(d["personen"], ordner(reise)),
                "wunsch_vorschlaege": alles.get("wunsch_vorschlaege") or {}}
    except (OSError, ValueError, KeyError, TypeError):
        return None


# ---------- Einladungen (Paket C): Personen, die in der Claude-App eingeladen wurden ----------
# Sie liegen live in <ablage>/<reise>/einladungen.json, weil der Dienst das Repo nicht ändert. Zugang und Rolle gelten
# sofort; der Konnektor schreibt die Person zugleich über den Schreibweg nach reise.yaml (person_schreiben). Steht sie
# dort, gilt die Angabe aus reise.yaml.
MAX_EINLADUNGEN = 50


def einladungen_lesen(o):
    """-> {schluessel: {name, rolle, reist, notiz, eingeladen_von, datum}}; fehlt die Datei oder ist sie kaputt: leer."""
    if o is None:
        return {}
    try:
        roh = json.loads((o / "einladungen.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return roh if isinstance(roh, dict) else {}


def personen_mit_einladungen(personen, o):
    """Personen aus reise.yaml plus Eingeladene, die dort (nach Schlüssel oder Namen) noch fehlen."""
    aus = [p | {"rolle": rg.rolle_neu(p.get("rolle"))} if isinstance(p, dict) else p for p in personen or []]
    schluessel = {p.get("schluessel") for p in aus}
    namen = {str(p.get("name", "")).casefold() for p in aus}
    for k, e in einladungen_lesen(o).items():
        if isinstance(e, dict) and k not in schluessel and str(e.get("name", "")).casefold() not in namen \
                and rg.rolle_neu(e.get("rolle")) in rg.ROLLEN:
            aus.append({"schluessel": k, "name": e["name"], "rolle": rg.rolle_neu(e["rolle"]), "reist": bool(e.get("reist", True)),
                        "notiz": e.get("notiz", ""), "eingeladen": True})
    return aus


def rolle_von(z, name):
    """Rolle einer Person aus reise.yaml nach Namen. Wer auf der Seite einen unbekannten Namen eintippt, kommt über den
    geheimen Link der Reise und gilt als Mitwirkende:r; eine bekannte Person hat die Rolle aus reise.yaml (gast: nur lesen)."""
    for p in (z or {}).get("personen") or []:
        if p["name"].casefold() == (name or "").strip().casefold():
            return p["rolle"]
    return "mitwirkend"


def schreibrecht(reise, aktion, name):
    """Darf diese Person jetzt schreiben? -> Fehlertext oder None. Aufrufer: der HTTP-Dienst bei jedem Schreiben."""
    z = zustand(reise)
    if z is None:
        return None
    ok, grund = rg.erlaubt(aktion, rolle_von(z, name), z["status"], z["bausteine"], regeln=z.get("regeln"))
    return None if ok else grund


def status_lesen(o):
    try:
        return json.loads((o / "status.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


# ---------- Meldungen an Personen (Konflikte; Zustellung folgt mit Paket E) ----------

def meldung_anlegen(o, an, art, ziel, text, auftraege=(), schluessel=None, bezug=None, zeit=None, extra=None):
    """Meldung an Personen (Namen) in meldungen.jsonl. Der Konnektor zeigt sie der Person (Überblick, rueckmeldungen).
    schluessel: Kennung gegen doppelte Meldungen (Wächter und Erinnerer, Paket E); bezug: AG-… oder „reise“, damit eine
    erledigte Meldung verschwindet (meldungen_aktuell); zeit: nur für Tests; extra: weitere Felder (status_bei)."""
    jetzt = zeit or datetime.datetime.now(datetime.timezone.utc)
    m = {"id": f"M-{jetzt:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}", "erstellt": jetzt.isoformat(timespec="seconds"),
         "an": sorted(set(an)), "art": art, "ziel": ziel, "text": text, "auftraege": list(auftraege)}
    if schluessel:
        m["schluessel"] = schluessel
    if bezug:
        m["bezug"] = bezug
    m.update(extra or {})
    with (o / "meldungen.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(m, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return m


def meldungen(o, an=None):
    """Meldungen, neueste zuerst; an: nur die an diese Person."""
    p = o / "meldungen.jsonl"
    liste = []
    if p.exists():
        for zeile in p.read_text(encoding="utf-8").splitlines():
            try:
                m = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            if an is None or an.casefold() in (x.casefold() for x in m.get("an", [])):
                liste.append(m)
    return sorted(liste, key=lambda m: m.get("erstellt", ""), reverse=True)


# Arten von Meldungen, die der Wächter und Erinnerer anlegt (Baustein waechter; ausgeschaltet verschwinden sie)
WAECHTER_ARTEN = ("erinnerung", "status", "pruefung")
MELDUNG_TAGE = 14   # so lange zeigt der Konnektor Meldungen; Konflikte bleiben stehen


def meldungen_aktuell(o, an, aufgaben=None, status=None, bausteine=None, heute=None, tage=MELDUNG_TAGE):
    """Meldungen an eine Person, die noch gelten: Erinnerungen zu erledigten Aufgaben, Statusmeldungen nach dem Wechsel
    und Meldungen älter als <tage> Tage fallen weg (Konflikte nie); ohne Baustein waechter auch die des Wächters.
    aufgaben: Liste aus aufgaben(o); status: Status der Reise jetzt."""
    heute = heute or datetime.date.today()
    offen = {a["id"] for a in aufgaben or [] if a["status"] in ("offen", "in_arbeit")}
    aus = []
    for m in meldungen(o, an):
        if m.get("art") in WAECHTER_ARTEN and bausteine is not None and "waechter" not in bausteine:
            continue
        if m.get("art") != "konflikt":
            try:
                if (heute - datetime.date.fromisoformat(m["erstellt"][:10])).days > tage:
                    continue
            except (KeyError, ValueError):
                pass
        if str(m.get("bezug", "")).startswith("AG-") and aufgaben is not None and m["bezug"] not in offen:
            continue
        if m.get("art") == "status" and status and m.get("status_bei") and m["status_bei"] != status:
            continue
        aus.append(m)
    return aus


def schreiben(pfad, text):
    tmp = pfad.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(pfad)


def eintraege(o, datei="eingang.jsonl"):
    """Alle Rückmeldungen einer Reise, neueste zuerst, mit Status und Kommentar von Claude."""
    status = status_lesen(o)
    liste = []
    eingang = o / datei
    if eingang.exists():
        for zeile in eingang.read_text(encoding="utf-8").splitlines():
            if not zeile.strip():
                continue
            try:
                e = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            s = status.get(e.get("id"), {})
            e["status"] = s.get("status", "neu")
            e["kommentar"] = s.get("kommentar", "")
            liste.append(e)
    return sorted(liste, key=lambda e: e.get("erstellt", ""), reverse=True)


def auftraege(o):
    """Änderungsaufträge von Organisator:innen aus der Claude-App (schreibt engine/konnektor.py). Nicht auf der Seite."""
    return eintraege(o, "auftraege.jsonl")


def pruefen(roh):
    """Eingabe prüfen und auf erlaubte Felder kürzen. -> (eintrag, fehler)"""
    if not isinstance(roh, dict):
        return None, "kein Objekt"
    e = {}
    for feld in INHALT:
        wert = roh.get(feld, "")
        if not isinstance(wert, str):
            return None, f"{feld} muss Text sein"
        e[feld] = wert.strip()
    if e["art"] not in ARTEN:
        return None, "unbekannte Art"
    if e["art"] == "Wunsch" and not e["ziel"]:
        e["ziel"] = WUNSCH_ZIEL
    if not ZIEL_MUSTER.match(e["ziel"]):
        return None, "ungültige ID"
    if not e["text"]:
        return None, "Text fehlt"
    if not e["name"]:
        return None, "Name fehlt"
    if "\n" in e["name"]:
        return None, "Name nur in einer Zeile"
    for feld, n in LAENGE.items():
        if len(e[feld]) > n:
            return None, f"{feld} zu lang (max. {n} Zeichen)"
    jetzt = datetime.datetime.now(datetime.timezone.utc)
    e["id"] = f"R-{jetzt:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
    e["erstellt"] = jetzt.isoformat(timespec="seconds")
    return e, None


# ---------- Aufgaben ----------

def aufgaben_lesen(o):
    try:
        return json.loads((o / "aufgaben.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"naechste": 1, "aufgaben": []}


def aufgaben(o):
    return aufgaben_lesen(o)["aufgaben"]


def ist_datum(t):
    try:
        datetime.date.fromisoformat(t)
        return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", t))
    except ValueError:
        return False


def ag_felder(roh, neu):
    """Erlaubte Felder einer Aufgabe prüfen. neu=True: Titel Pflicht. -> (felder, fehler)"""
    f = {}
    for k in AG_FELDER:
        if k not in roh:
            continue
        v = roh[k]
        if k == "bezug":
            if isinstance(v, str):
                v = [x for x in re.split(r"[,\s]+", v) if x]
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                return None, "bezug muss eine Liste von IDs sein"
            v = list(dict.fromkeys(x.strip() for x in v if x.strip()))
            if len(v) > MAX_BEZUG:
                return None, f"höchstens {MAX_BEZUG} Bezüge"
            if not all(ZIEL_MUSTER.match(x) for x in v):
                return None, "ungültige ID im Bezug"
        else:
            if v is None:
                v = ""
            if not isinstance(v, str):
                return None, f"{k} muss Text sein"
            v = v.strip()
            if k in AG_LAENGE and len(v) > AG_LAENGE[k]:
                return None, f"{k} zu lang (max. {AG_LAENGE[k]} Zeichen)"
            if k in ("titel", "zustaendig") and "\n" in v:
                return None, f"{k} nur in einer Zeile"
            if k in ("ab", "frist") and v and not ist_datum(v):
                return None, f"{k} muss ein Datum JJJJ-MM-TT sein"
            if k == "prioritaet" and v not in AG_PRIO:
                return None, f"Priorität: {', '.join(AG_PRIO)}"
            if k == "status" and v not in AG_STATUS:
                return None, f"Status: {', '.join(AG_STATUS)}"
            if k == "titel" and not v:
                return None, "Titel fehlt"
        f[k] = v
    if neu and not f.get("titel"):
        return None, "Titel fehlt"
    return f, None


def wer(roh):
    n = roh.get("name", "") if isinstance(roh, dict) else ""
    if not isinstance(n, str) or not n.strip():
        return None, "Name fehlt"
    n = n.strip()
    if "\n" in n or len(n) > AG_LAENGE["name"]:
        return None, "Name nur in einer Zeile, max. 80 Zeichen"
    return n, None


def jetzt_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def aufgabe_anlegen(o, roh):
    """-> (aufgabe, fehler). Aufrufer hält _sperre."""
    if not isinstance(roh, dict):
        return None, "kein Objekt"
    name, fehler = wer(roh)
    if fehler:
        return None, fehler
    f, fehler = ag_felder(roh, True)
    if fehler:
        return None, fehler
    alle = aufgaben_lesen(o)
    if len(alle["aufgaben"]) >= MAX_AUFGABEN:
        return None, "zu viele Aufgaben"
    zeit = jetzt_iso()
    a = {"id": f"AG-{alle['naechste']:02d}", "titel": f["titel"], "bezug": f.get("bezug", []),
         "zustaendig": f.get("zustaendig", ""), "prioritaet": f.get("prioritaet") or "normal",
         "ab": f.get("ab", ""), "frist": f.get("frist", ""), "notiz": f.get("notiz", ""),
         "status": f.get("status") or "offen", "erstellt": zeit, "erstellt_von": name, "geaendert": zeit,
         "erledigt": zeit[:10] if f.get("status") == "erledigt" else "",
         "verlauf": [{"zeit": zeit, "wer": name, "was": "angelegt"}]}
    alle["naechste"] += 1
    alle["aufgaben"].append(a)
    schreiben(o / "aufgaben.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
    return a, None


def aufgabe_aendern(o, agid, roh):
    """-> (aufgabe, fehler, code). Aufrufer hält _sperre."""
    if not isinstance(roh, dict):
        return None, "kein Objekt", 400
    name, fehler = wer(roh)
    if fehler:
        return None, fehler, 400
    f, fehler = ag_felder(roh, False)
    if fehler:
        return None, fehler, 400
    kommentar = roh.get("kommentar", "")
    if not isinstance(kommentar, str) or len(kommentar.strip()) > AG_LAENGE["kommentar"]:
        return None, "Kommentar zu lang (max. 500 Zeichen)", 400
    kommentar = kommentar.strip()
    alle = aufgaben_lesen(o)
    a = next((x for x in alle["aufgaben"] if x["id"] == agid), None)
    if a is None:
        return None, "nicht gefunden", 404
    diff = {k: [a.get(k), v] for k, v in f.items() if a.get(k) != v}
    if not diff and not kommentar:
        return a, None, 200
    zeit = jetzt_iso()
    for k, (_, v) in diff.items():
        a[k] = v
    if "status" in diff:
        a["erledigt"] = zeit[:10] if a["status"] == "erledigt" else ""
    eintrag = {"zeit": zeit, "wer": name, "was": "geändert" if diff else "Kommentar"}
    if diff:
        eintrag["felder"] = diff
    if kommentar:
        eintrag["kommentar"] = kommentar
    a["verlauf"].append(eintrag)
    a["geaendert"] = zeit
    schreiben(o / "aufgaben.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
    return a, None, 200


# ---------- Wunsch-Brett (Paket G) ----------
# Zu jedem Wunsch (Rückmeldung der Art Wunsch) hält brett.json fest, was nicht von Claude kommt: die Punkte der Person,
# die ihn eingebracht hat (wie wichtig er ihr ist), „eingeplant“ (nur Organisator:innen) und „erlebt“ (alle Mitwirkenden, unterwegs
# und danach), je mit Verlauf. Claudes Vorschlag (passt zu Tag …, daraus wurde Option …) steht im Repo
# (plan/wuensche.yaml) und kommt über daten.json. Die Spalte des Bretts wird daraus berechnet, nie gespeichert.
# Nichts wird gelöscht; ein Wunsch, der nicht passt, gibt seine Punkte frei.
SPALTEN = ("eingebracht", "geprueft", "eingeplant", "erlebt", "passt_nicht")
SPALTEN_TITEL = {"eingebracht": "Eingebracht", "geprueft": "Geprüft", "eingeplant": "Eingeplant", "erlebt": "Erlebt",
                 "passt_nicht": "Passt nicht"}
MAX_PUNKTE = 100
ERLEBT_AB = ("unterwegs", "danach")


def brett_lesen(o):
    try:
        roh = json.loads((o / "brett.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return roh if isinstance(roh, dict) else {}


def kontingent(z):
    """regeln.kontingent der Reise mit Vorgaben: {art: punkte|anzahl, je_person}."""
    k = dict(rg.VORGABEN["kontingent"])
    k.update(((z or {}).get("regeln") or {}).get("kontingent") or {})
    return k


def wuensche(o):
    """Alle Wünsche einer Reise (Rückmeldungen der Art Wunsch), neueste zuerst."""
    return [e for e in eintraege(o) if e.get("art") == "Wunsch"]


def spalte(e, b, vorschlag=None):
    """Spalte eines Wunsches. passt nicht: Claude hat ihn verworfen; erlebt: abgehakt; eingeplant: ein:e Organisator:in hat ihn
    bestätigt oder die Option, die aus ihm wurde, gewählt; geprüft: Claude hat ihn aufgenommen; sonst eingebracht."""
    if e.get("status") == "verworfen":
        return "passt_nicht"
    if (b or {}).get("erlebt"):
        return "erlebt"
    if (b or {}).get("eingeplant") or (vorschlag or {}).get("gewaehlt"):
        return "eingeplant"
    return "geprueft" if e.get("status") == "uebernommen" else "eingebracht"


def _schluessel(name):
    return (name or "").strip().casefold()


def vergeben(liste, brett_, name, ohne=None):
    """Punkte, die eine Person auf ihre Wünsche verteilt hat (Wünsche, die nicht passen, zählen nicht)."""
    return sum(int((brett_.get(e["id"]) or {}).get("punkte") or 0) for e in liste
               if _schluessel(e.get("name")) == _schluessel(name) and e["id"] != ohne and e.get("status") != "verworfen")


def aktive_wuensche(liste, name):
    return sum(1 for e in liste if _schluessel(e.get("name")) == _schluessel(name) and e.get("status") != "verworfen")


def brett(o, z=None):
    """Das Brett zum Anzeigen (Seite und Claude-App): Wünsche mit Spalte, Punkten, Vorschlag, eingeplant und erlebt;
    Bilanz je Person (alle sehen sie); Kontingent der Reise."""
    k = kontingent(z)
    b = brett_lesen(o)
    vorschlaege = (z or {}).get("wunsch_vorschlaege") or {}
    liste = wuensche(o)
    aus = []
    for e in liste:
        be = b.get(e["id"]) or {}
        v = vorschlaege.get(e["id"])
        aus.append({**{x: e.get(x, "") for x in ("id", "name", "text", "quelle", "erstellt", "status", "kommentar")},
                    "spalte": spalte(e, be, v), "punkte": int(be.get("punkte") or 0) if k["art"] == "punkte" else 0,
                    "eingeplant": be.get("eingeplant"), "erlebt": be.get("erlebt"), "vorschlag": v,
                    "verlauf": be.get("verlauf", [])})
    # Bilanz: alle, die Wünsche einbringen dürfen, und alle, die schon welche haben
    namen = {}
    for p in (z or {}).get("personen") or []:
        if rg.darf(p.get("rolle"), "mitwirkend"):
            namen.setdefault(_schluessel(p["name"]), p["name"])
    for e in liste:
        namen.setdefault(_schluessel(e.get("name")), e.get("name", ""))
    bilanz = []
    for s, name in namen.items():
        eigene = [w for w in aus if _schluessel(w["name"]) == s]
        zeile = {"name": name, "wuensche": len(eigene), **{sp: sum(1 for w in eigene if w["spalte"] == sp) for sp in SPALTEN}}
        if k["art"] == "punkte":
            zeile["punkte"] = vergeben(liste, b, name)
            zeile["frei"] = max(0, k["je_person"] - zeile["punkte"])
        else:
            zeile["frei"] = max(0, k["je_person"] - aktive_wuensche(liste, name))
        bilanz.append(zeile)
    return {"kontingent": k, "spalten": [{"id": s, "titel": SPALTEN_TITEL[s]} for s in SPALTEN], "wuensche": aus,
            "bilanz": sorted(bilanz, key=lambda x: x["name"].casefold())}


def wunsch_annehmen(o, z, name):
    """Darf diese Person noch einen Wunsch einbringen (regeln.kontingent art anzahl)? -> Fehlertext oder None."""
    k = kontingent(z)
    if k["art"] == "anzahl" and aktive_wuensche(wuensche(o), name) >= k["je_person"]:
        return (f"Höchstens {k['je_person']} Wünsche je Person. Erst einen eigenen Wunsch zurückziehen, oder er wird "
                "geprüft und passt nicht.")
    return None


def wunsch_aendern(o, rid, roh, z):
    """Wunsch auf dem Brett ändern: punkte (nur wer ihn eingebracht hat, im Kontingent), erlebt (alle Mitwirkenden,
    unterwegs und danach), eingeplant mit bezug (nur Organisator:innen); kommentar geht in den Verlauf.
    z: zustand(reise) oder None (dann nur die technischen Prüfungen). -> (wunsch, fehler, code). Aufrufer hält _sperre."""
    if not isinstance(roh, dict):
        return None, "kein Objekt", 400
    name, fehler = wer(roh)
    if fehler:
        return None, fehler, 400
    e = next((x for x in wuensche(o) if x["id"] == rid), None)
    if e is None:
        return None, "Diesen Wunsch gibt es nicht.", 404
    felder = {}
    aktionen = []
    if "punkte" in roh:
        p = roh["punkte"]
        if not isinstance(p, int) or isinstance(p, bool) or not 0 <= p <= MAX_PUNKTE:
            return None, f"punkte muss eine ganze Zahl von 0 bis {MAX_PUNKTE} sein", 400
        felder["punkte"] = p
        aktionen.append("wunsch")
    for f in ("erlebt", "eingeplant"):
        if f in roh:
            if not isinstance(roh[f], bool):
                return None, f"{f} muss ja oder nein sein (true/false)", 400
            aktionen.append("wunsch_erlebt" if f == "erlebt" else "wunsch_einplanen")
    bezug = []
    if "bezug" in roh:
        bezug, fehler = ag_felder({"bezug": roh["bezug"]}, False)
        if fehler:
            return None, fehler, 400
        bezug = bezug["bezug"]
        if roh.get("eingeplant") is not True:
            return None, "bezug gehört zu eingeplant: true", 400
    kommentar = roh.get("kommentar", "")
    if not isinstance(kommentar, str) or len(kommentar.strip()) > AG_LAENGE["kommentar"]:
        return None, "Kommentar zu lang (max. 500 Zeichen)", 400
    kommentar = kommentar.strip()
    if not aktionen and not kommentar:
        return None, "Nichts zu ändern (punkte, erlebt, eingeplant oder kommentar).", 400
    if z is not None:
        for a in aktionen or ["wunsch_erlebt"]:   # nur ein Kommentar: darf, wer auch abhaken darf
            ok, grund = rg.erlaubt(a, rolle_von(z, name), z["status"], z["bausteine"], regeln=z.get("regeln"))
            if not ok:
                return None, grund, 403
    if aktionen and e.get("status") == "verworfen":
        return None, "Dieser Wunsch passt nicht (so geprüft); er bleibt so stehen.", 409
    alle = brett_lesen(o)
    b = alle.setdefault(rid, {"punkte": 0, "eingeplant": None, "erlebt": None, "verlauf": []})
    if "punkte" in felder:
        k = kontingent(z)
        if k["art"] != "punkte":
            return None, "Diese Reise zählt Wünsche, keine Punkte.", 400
        if _schluessel(e.get("name")) != _schluessel(name):
            return None, f"Punkte verteilt nur, wer den Wunsch eingebracht hat ({e.get('name')}).", 403
        frei = k["je_person"] - vergeben(wuensche(o), alle, name, ohne=rid)
        if felder["punkte"] > frei:
            return None, f"So viele Punkte sind nicht mehr frei: noch {max(0, frei)} von {k['je_person']}.", 409
    heute = datetime.date.today().isoformat()
    if "erlebt" in roh:
        if z is not None and z["status"] not in ERLEBT_AB:
            return None, "Abhaken geht erst, wenn die Reise läuft (Status unterwegs) und danach.", 409
        felder["erlebt"] = {"wer": name, "datum": heute} if roh["erlebt"] else None
    if "eingeplant" in roh:
        felder["eingeplant"] = {"wer": name, "datum": heute, "bezug": bezug} if roh["eingeplant"] else None
    # Nur echte Änderungen zählen; wer etwas schon Abgehaktes noch einmal abhakt, ändert nichts (Nachreichen ohne Netz)
    diff = {}
    for f, v in felder.items():
        alt = b.get(f)
        gleich = (alt == v) if f == "punkte" else (bool(alt) == bool(v) and (f != "eingeplant" or not v
                                                                              or (alt or {}).get("bezug") == v["bezug"]))
        if not gleich:
            diff[f] = [alt, v]
    if not diff and not kommentar:
        if not b["verlauf"]:
            del alle[rid]
        return {"id": rid, **b}, None, 200
    zeit = jetzt_iso()
    for f, (_, v) in diff.items():
        b[f] = v
    eintrag = {"zeit": zeit, "wer": name, "was": "geändert" if diff else "Kommentar"}
    if diff:
        eintrag["felder"] = {f: [a, v] if f == "punkte" else [bool(a), bool(v)] for f, (a, v) in diff.items()}
    if kommentar:
        eintrag["kommentar"] = kommentar
    b["verlauf"].append(eintrag)
    schreiben(o / "brett.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
    return {"id": rid, **b}, None, 200


# ---------- Wer schreibt? (Paket J, Konten) ----------
# Nur der Konnektor kennt das Dienst-Geheimnis (Header X-Frieda-Dienst); er hat die Person schon selbst erkannt und
# schickt ihren Namen mit. Alles andere ist die Seite (fail-closed, auch ohne X-Forwarded-For). Auf der Seite kommt der
# Name aus der Sitzung (Cookie) und der Mitgliedschaft in der Reise; ein eingetippter Name zählt nur, solange die Reise
# die Regel anmeldung: uebergang hat.
COOKIE = "__Host-frieda"


def sitzungs_token(cookie_kopf):
    import http.cookies
    c = http.cookies.SimpleCookie()
    try:
        c.load(cookie_kopf or "")
    except http.cookies.CookieError:
        return None
    return c[COOKIE].value if COOKIE in c else None


def wer_ist(headers, reise, z=None, lesen=False):
    """-> {"art": "dienst"} | {"art": "konto", "konto", "person"|None} | {"art": "seite"} | {"art": "fremd"}.
    „fremd“: Sitzung, aber die Anfrage kommt nicht von Friedas eigener Adresse (Origin) – kein Schreiben (CSRF).
    lesen: nur lesende Anfrage (GET, der Browser schickt kein Origin; fremde Seiten können die Antwort nicht lesen)."""
    if hmac_gleich(headers.get("X-Frieda-Dienst", ""), konten.dienst_geheimnis()):
        return {"art": "dienst"}
    token = sitzungs_token(headers.get("Cookie"))
    k = konten.sitzung(token) if token else None
    if not k:
        return {"art": "seite"}
    if not lesen and (not konten.basis() or headers.get("Origin") != konten.basis()):
        return {"art": "fremd"}
    schl = konten.mitglied(k["id"], reise)
    z = z if z is not None else zustand(reise)
    person = next((p for p in (z or {}).get("personen") or [] if p.get("schluessel") == schl), None) if schl else None
    return {"art": "konto", "konto": k, "person": person}


def hmac_gleich(a, b):
    return bool(a) and bool(b) and secrets.compare_digest(a.encode(), b.encode())


def anmeldung_regel(z):
    return ((z or {}).get("regeln") or {}).get("anmeldung") or rg.VORGABEN["anmeldung"]


def name_fuer(ident, z, getippt):
    """Name, unter dem geschrieben wird. -> (name, None) oder (None, (code, fehler))."""
    if ident["art"] == "dienst":
        return getippt, None
    if ident["art"] == "fremd":
        return None, (403, "Diese Anfrage kommt nicht von Frieda selbst.")
    if ident["art"] == "konto" and ident["person"]:
        return ident["person"]["name"], None
    if anmeldung_regel(z) == "uebergang" or z is None:
        return getippt, None
    if ident["art"] == "konto":
        return None, (403, "Du bist bei dieser Reise nicht eingeladen. Bitte die Person fragen, die die Reise bestimmt.")
    return None, (401, "Bitte melde dich an, um mitzumachen.")


def gedrosselt(o):
    """True, wenn diese Reise in der letzten Minute schon MAX_JE_MINUTE Schreibzugriffe hatte. Aufrufer hält _sperre."""
    jetzt = time.monotonic()
    zeiten = _zeiten.setdefault(o.name, [])
    zeiten[:] = [z for z in zeiten if jetzt - z < 60]
    if len(zeiten) >= MAX_JE_MINUTE:
        return True
    zeiten.append(jetzt)
    return False


class Dienst(BaseHTTPRequestHandler):
    server_version = "Rueckmeldungen"
    sys_version = ""

    def _antwort(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _teile(self):
        """/<reise>/<was>[/<id>] -> (ordner, was, id) oder None"""
        teile = self.path.split("?", 1)[0].strip("/").split("/")
        if len(teile) not in (2, 3):
            return None
        o = ordner(teile[0])
        if o is None:
            return None
        return o, teile[1], teile[2] if len(teile) == 3 else None

    def _datei(self, b, pfad):
        """Einen Beleg ausliefern (zum Ansehen im Browser; der Name steht im Content-Disposition)."""
        try:
            daten = pfad.read_bytes()
        except OSError:
            return self._antwort(404, {"fehler": "Die Datei fehlt in der Ablage."})
        self.send_response(200)
        self.send_header("Content-Type", b["typ"])
        self.send_header("Content-Length", str(len(daten)))
        self.send_header("Content-Disposition", "inline; filename*=UTF-8''" + urllib.parse.quote(b["name"]))
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(daten)

    def _kalender(self, o, token=None):
        """Kalender der Reise (#77, engine/kalender.py): Abo mit geheimem Wort (Kalender-Apps melden sich nicht an) oder
        Datei zum Herunterladen, ganz oder für ein Ding (?id=T-…/U-…/A-…/E-…/B-…/AG-…)."""
        import kalender
        if token is not None and not konten.kalender_konto(o.name, token.removesuffix(".ics")):
            return self._antwort(404, {"fehler": "Diesen Kalender gibt es nicht (mehr). Den aktuellen Link gibt es unter „Mein Konto“."})
        try:
            daten = json.loads((seiten() / o.name / "daten.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return self._antwort(503, {"fehler": "Die Seite der Reise ist gerade nicht lesbar."})
        nur = (self._query().get("id") or [None])[0] if token is None else None
        if nur is not None and not ZIEL_MUSTER.match(nur):
            return self._antwort(400, {"fehler": "ungültige ID"})
        text = kalender.ics(daten, o.name, aufgaben(o), nur=nur)
        if text is None:
            return self._antwort(404, {"fehler": "Dazu gibt es noch keinen Kalendereintrag (noch nicht entschieden oder ohne Datum)."})
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/calendar; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if token is None:
            self.send_header("Content-Disposition", f'attachment; filename="{o.name}{"-" + nur if nur else ""}.ics"')
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _query(self):
        return urllib.parse.parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}

    def do_GET(self):
        t = self._teile()
        if t and t[1] == "belege":
            # Belege (#76): Liste oder Datei, nur was die Person sehen darf
            o, _, did = t
            z = zustand(o.name)
            q = self._query()
            name, rolle = seher(wer_ist(self.headers, o.name, z, lesen=True), z, (q.get("name") or [None])[0])
            if did is None:
                return self._antwort(200, bl.liste(o, name, rolle, (q.get("buchung") or [None])[0]))
            b = bl.finden(o, did)
            if b is None or not bl.darf_sehen(b, name, rolle):
                return self._antwort(404, {"fehler": "Diesen Beleg gibt es nicht, oder er ist für dich nicht sichtbar."})
            return self._datei(b, bl.datei_pfad(o, b))
        if t and t[1] == "kalender" and t[2]:
            return self._kalender(t[0], t[2])
        if not t or t[2] is not None:
            return self._antwort(404, {"fehler": "unbekannt"})
        o, was, _ = t
        if was == "kalender.ics":
            return self._kalender(o)
        if was == "gesund":
            ok = os.access(o, os.W_OK)
            return self._antwort(200 if ok else 503, {"gesund": ok})
        if was == "aufgaben":
            return self._antwort(200, aufgaben(o))
        if was == "brett":
            return self._antwort(200, brett(o, zustand(o.name)))
        if was == "ich":
            z = zustand(o.name)
            i = wer_ist(self.headers, o.name, z, lesen=True)
            k = i.get("konto") if i["art"] == "konto" else None
            p = i.get("person") if k else None
            return self._antwort(200, {
                "basis": konten.basis(), "anmeldung": anmeldung_regel(z),
                "konto": {"name": k["name"], "email": k["email"]} if k else None,
                "person": {f: p.get(f) for f in ("schluessel", "name", "rolle")} if p else None})
        if was != "rueckmeldungen":
            return self._antwort(404, {"fehler": "unbekannt"})
        self._antwort(200, eintraege(o))

    def _json(self):
        """Body als JSON -> (objekt, None) oder (None, True) nach gesendeter Fehlerantwort."""
        try:
            laenge = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            laenge = 0
        if laenge <= 0 or laenge > MAX_BODY:
            self._antwort(413, {"fehler": "zu groß oder leer"})
            return None, True
        try:
            return json.loads(self.rfile.read(laenge).decode("utf-8")), None
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._antwort(400, {"fehler": "kein gültiges JSON"})
            return None, True

    def do_PATCH(self):
        t = self._teile()
        if t and t[1] == "belege":
            # Beleg (#76): Sichtbarkeit (Organisator:in) oder zurückziehen (wer hochlud, Organisator:in)
            o, _, did = t
            if bl.finden(o, did or "") is None:
                return self._antwort(404, {"fehler": "Diesen Beleg gibt es nicht."})
            roh, fehlt = self._json()
            if fehlt:
                return
            if not isinstance(roh, dict):
                return self._antwort(400, {"fehler": "kein Objekt"})
            z = zustand(o.name)
            ident = wer_ist(self.headers, o.name, z)
            name, nein = name_fuer(ident, z, roh.get("name"))
            if nein:
                return self._antwort(nein[0], {"fehler": nein[1]})
            if ident["art"] == "seite":   # eingetippter Name genügt für Belege nicht (sie sind sensibel)
                return self._antwort(401, {"fehler": "Bitte melde dich an, um Belege zu ändern."})
            _, rolle = seher(ident, z, name)
            with _sperre:
                b, nein = bl.aendern(o, did, roh, name, rolle)
            return self._antwort(nein[0], {"fehler": nein[1]}) if nein else self._antwort(200, b)
        wunsch = bool(t) and t[1] == "rueckmeldungen" and bool(RID_MUSTER.match(t[2] or ""))
        erledigen = bool(t) and t[1] == "rueckmeldungen" and bool(AID_MUSTER.match(t[2] or ""))
        if not t or not (wunsch or erledigen) and (t[1] != "aufgaben" or not AG_MUSTER.match(t[2] or "")):
            return self._antwort(404, {"fehler": "unbekannt"})
        roh, fehlt = self._json()
        if fehlt:
            return
        if not isinstance(roh, dict):
            return self._antwort(400, {"fehler": "kein Objekt"})
        z = zustand(t[0].name)
        ident = wer_ist(self.headers, t[0].name, z)
        if erledigen or (wunsch and "status" in roh):
            # Status setzen (O-3, rueckmeldung_erledigen): nur der Konnektor, der die Organisator:in erkannt hat
            if ident["art"] != "dienst":
                return self._antwort(403, {"fehler": "Den Status setzt nur ein:e Organisator:in in der Claude-App."})
            kommentar = str(roh.get("kommentar") or "").strip()[:LAENGE["text"]]
            with _sperre:
                e, fehler = status_setzen(t[0], t[2], str(roh.get("status") or ""), kommentar, roh.get("name"))
            return self._antwort(400 if fehler else 200, {"fehler": fehler} if fehler else {"id": t[2], **e})
        name, nein = name_fuer(ident, z, roh.get("name"))
        if nein:
            return self._antwort(nein[0], {"fehler": nein[1]})
        roh = {**roh, "name": name}
        if wunsch:
            # Wunsch-Brett: Rechte, Kontingent und Status prüft wunsch_aendern (auch für den Konnektor). Einplanen ist eine
            # Entscheidung: nur der Konnektor (Person erkannt) oder eine angemeldete Person, die die Reise bestimmt; ein
            # eingetippter Name genügt nicht.
            bestimmt = ident["art"] == "konto" and (ident["person"] or {}).get("rolle") == "organisator"
            if "eingeplant" in roh and ident["art"] != "dienst" and not bestimmt:
                return self._antwort(403, {"fehler": "Einplanen dürfen nur Organisator:innen: in der Claude-App oder angemeldet "
                                                     "auf der Seite."})
            with _sperre:
                if gedrosselt(t[0]):
                    return self._antwort(429, {"fehler": "zu viele Änderungen, bitte kurz warten"})
                w, fehler, code = wunsch_aendern(t[0], t[2], roh, z)
            return self._antwort(code, {"fehler": fehler} if fehler else w)
        if (nein := schreibrecht(t[0].name, "aufgabe", roh.get("name"))):
            return self._antwort(403, {"fehler": nein})
        with _sperre:
            if gedrosselt(t[0]):
                return self._antwort(429, {"fehler": "zu viele Änderungen, bitte kurz warten"})
            a, fehler, code = aufgabe_aendern(t[0], t[2], roh)
        self._antwort(code, {"fehler": fehler} if fehler else a)

    def _beleg_hochladen(self, o, bid):
        """POST /<reise>/belege/<B-id>: Body ist die Datei (#76). Rolle wie beim Eintragen einer Buchung (Aktion buchung)."""
        if not bl.BID_MUSTER.match(bid or "") or not buchung_bekannt(o.name, bid):
            return self._antwort(404, {"fehler": f"Die Buchung {bid} gibt es nicht (oder sie ist noch nicht veröffentlicht)."})
        try:
            laenge = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            laenge = 0
        if laenge <= 0:
            return self._antwort(400, {"fehler": "Die Datei ist leer."})
        if laenge > bl.MAX_DATEI:
            # Etwas zu große Dateien lesen und verwerfen, damit der Browser die Antwort noch bekommt; nginx begrenzt den
            # Body vorher (client_max_body_size), ganz große Anfragen werden ungelesen beendet
            if laenge <= 2 * bl.MAX_DATEI:
                self.rfile.read(laenge)
            else:
                self.close_connection = True
            return self._antwort(413, {"fehler": f"Die Datei ist zu groß (höchstens {bl.MAX_DATEI // 1024 // 1024} MB)."})
        z = zustand(o.name)
        ident = wer_ist(self.headers, o.name, z)
        name, nein = name_fuer(ident, z, (self._query().get("name") or [None])[0])
        if nein:
            self.close_connection = True
            return self._antwort(nein[0], {"fehler": nein[1]})
        if ident["art"] == "seite":   # Belege nur angemeldet (Product Owner 29.10.2026): ein eingetippter Name trägt „nur für dich
            self.close_connection = True   # und Organisator:innen sichtbar“ nicht, auch nicht bei der Übergangsregel
            return self._antwort(401, {"fehler": "Bitte melde dich an, um Belege anzuhängen; sie sind nur für dich und die Organisator:innen sichtbar."})
        if not name:
            self.close_connection = True
            return self._antwort(400, {"fehler": "Name fehlt (wer lädt den Beleg hoch?)."})
        if (nein := schreibrecht(o.name, "buchung", name)):
            self.close_connection = True
            return self._antwort(403, {"fehler": nein})
        daten = self.rfile.read(laenge)
        dateiname = urllib.parse.unquote(self.headers.get("X-Frieda-Datei", ""))
        with _sperre:
            if gedrosselt(o):
                return self._antwort(429, {"fehler": "zu viele Änderungen, bitte kurz warten"})
            b, nein = bl.ablegen(o, bid, name, dateiname, daten)
        return self._antwort(nein[0], {"fehler": nein[1]}) if nein else self._antwort(201, b)

    def do_POST(self):
        t = self._teile()
        if t and t[1] == "belege" and t[2]:
            return self._beleg_hochladen(t[0], t[2])
        if not t or t[1] not in ("rueckmeldungen", "aufgaben") or t[2] is not None:
            return self._antwort(404, {"fehler": "unbekannt"})
        o = t[0]
        roh, fehlt = self._json()
        if fehlt:
            return
        if not isinstance(roh, dict):
            return self._antwort(400, {"fehler": "kein Objekt"})
        name, nein = name_fuer(wer_ist(self.headers, o.name), zustand(o.name), roh.get("name"))
        if nein:
            return self._antwort(nein[0], {"fehler": nein[1]})
        roh = {**roh, "name": name}
        if t[1] == "aufgaben":
            if (nein := schreibrecht(o.name, "aufgabe", roh.get("name"))):
                return self._antwort(403, {"fehler": nein})
            with _sperre:
                if gedrosselt(o):
                    return self._antwort(429, {"fehler": "zu viele Änderungen, bitte kurz warten"})
                a, fehler = aufgabe_anlegen(o, roh)
            return self._antwort(400, {"fehler": fehler}) if fehler else self._antwort(201, a)
        e, fehler = pruefen(roh)
        if fehler:
            return self._antwort(400, {"fehler": fehler})
        if (nein := schreibrecht(o.name, "wunsch" if e["art"] == "Wunsch" else "rueckmeldung", e["name"])):
            return self._antwort(403, {"fehler": nein})
        with _sperre:
            grenze = (datetime.datetime.now(datetime.timezone.utc)
                      - datetime.timedelta(seconds=DOPPELT_SEKUNDEN)).isoformat(timespec="seconds")
            for alt in eintraege(o):
                if alt.get("erstellt", "") < grenze:
                    break
                if all(alt.get(k, "") == e.get(k, "") for k in INHALT):
                    return self._antwort(200, alt)
            if e["art"] == "Wunsch" and (nein := wunsch_annehmen(o, zustand(o.name), e["name"])):
                return self._antwort(409, {"fehler": nein})
            if gedrosselt(o):
                return self._antwort(429, {"fehler": "zu viele Rückmeldungen, bitte kurz warten"})
            with (o / "eingang.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
        self._antwort(201, {**e, "status": "neu", "kommentar": ""})

    def do_DELETE(self):
        t = self._teile()
        if not t or t[1] != "rueckmeldungen" or not RID_MUSTER.match(t[2] or ""):
            return self._antwort(404, {"fehler": "unbekannt"})
        o, _, rid = t
        z = zustand(o.name)
        ident = wer_ist(self.headers, o.name, z)
        ich, nein = name_fuer(ident, z, None)
        if nein:
            return self._antwort(nein[0], {"fehler": nein[1]})
        if z and rg.verhalten(z["status"])["schreiben"] == "nichts":
            return self._antwort(403, {"fehler": "Die Reise ist archiviert: Es kann nur gelesen werden."})
        with _sperre:
            eingang = o / "eingang.jsonl"
            if not eingang.exists():
                return self._antwort(404, {"fehler": "nicht gefunden"})
            if status_lesen(o).get(rid, {}).get("status", "neu") != "neu":
                return self._antwort(409, {"fehler": "schon bearbeitet, kann nicht mehr zurückgezogen werden"})
            if any((brett_lesen(o).get(rid) or {}).get(f) for f in ("erlebt", "eingeplant")):
                return self._antwort(409, {"fehler": "steht auf dem Brett schon als eingeplant oder erlebt"})
            zeilen = eingang.read_text(encoding="utf-8").splitlines(keepends=True)
            rest, weg = [], None
            for z in zeilen:
                try:
                    e = json.loads(z)
                    if e.get("id") == rid:
                        weg = e
                        continue
                except json.JSONDecodeError:
                    pass
                rest.append(z)
            if weg is None:
                return self._antwort(404, {"fehler": "nicht gefunden"})
            if ident["art"] == "konto" and str(weg.get("name", "")).casefold() != (ich or "").casefold():
                return self._antwort(403, {"fehler": "Zurückziehen kann nur, wer die Rückmeldung geschrieben hat."})
            # Zurückziehen ist Schreiben: dieselbe Prüfung wie beim Absenden (Rolle des Absenders, Baustein, Status)
            if (nein := schreibrecht(o.name, "wunsch" if weg.get("art") == "Wunsch" else "rueckmeldung", weg.get("name"))):
                return self._antwort(403, {"fehler": nein})
            schreiben(eingang, "".join(rest))
        self._antwort(200, {"geloescht": rid})

    def log_message(self, fmt, *args):
        # Nur Methode und Ergebnis protokollieren, keine Inhalte
        sys.stderr.write(f"{self.command} {args[1] if len(args) > 1 else ''}\n")


def dienst():
    host = os.environ.get("RM_HOST", "127.0.0.1")
    port = int(os.environ.get("RM_PORT", "8771"))
    print(f"Rückmeldedienst auf {host}:{port}, Ablage {ablage()}", flush=True)
    ThreadingHTTPServer((host, port), Dienst).serve_forever()


def titel_zu(reise):
    """ID -> Titel aus der zuletzt gebauten Seite, damit die Liste lesbar ist."""
    p = WURZEL / "dist" / reise / "daten.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    t = {WUNSCH_ZIEL: "Wunschliste"}
    for a in d.get("abschnitte", []):
        t[a["id"]] = a["titel"]
        for b in a.get("bloecke", []):
            t[b["id"]] = f"{a['titel']} › {b['titel']}"
    for z in d.get("fragen", {}).get("zeilen", []):
        t[z["id"]] = z["zellen"][1] if len(z["zellen"]) > 1 else z["id"]
    r = d.get("route") or {}
    for x in r.get("tage", []):
        t[x["id"]] = f"Tag {x['nr']} ({x['datum']}): {x['titel']}"
    for k, x in (r.get("weitere_tage") or {}).items():
        t[k] = f"Variante: {x['titel']}"
    for k, u in (r.get("unterkuenfte") or {}).items():
        t[k] = u.get("name", k)
    for x in r.get("plaene", []):
        t[x["id"]] = f"{x['kurz']}: {x['titel']}"
    for w in r.get("wahlstellen", []):
        t[w["id"]] = w["titel"]
        for o in w["optionen"]:
            t[o["id"]] = f"{w['titel']} › {o['titel']}"
    return t


def muss_ordner(reise):
    o = ordner_neu() if reise == NEU else ordner(reise)
    if o is None:
        sys.exit(f"Reise „{reise}“ nimmt keine Rückmeldungen an (Ordner {ablage() / reise} fehlt).")
    return o


def liste(reise, alle):
    o = muss_ordner(reise)
    es = [e for e in eintraege(o) + auftraege(o) if alle or e["status"] in ("neu", "konflikt")]
    es.sort(key=lambda e: e.get("erstellt", ""), reverse=True)
    if not es:
        print("Keine neuen Rückmeldungen." if not alle else "Keine Rückmeldungen.")
        return
    titel = titel_zu(reise)
    br = brett_lesen(o)
    for e in reversed(es):
        print(f"{e['id']}  {e['erstellt'][:16].replace('T', ' ')} UTC  {e.get('name')}  [{e['status']}]")
        if e.get("art") == "Wunsch":
            b = br.get(e["id"]) or {}
            print(f"  WUNSCH ({b.get('punkte') or 0} Punkte von {e.get('name')}): Vorschlag in plan/wuensche.yaml (bezug, notiz "
                  "mit Herkunft, option); einplanen nur Organisator:innen. Punkte = Priorität, keine Entscheidung."
                  + (" Schon eingeplant von einer Organisator:in." if b.get("eingeplant") else "")
                  + (" Schon erlebt." if b.get("erlebt") else ""))
        daten = e.get("daten") or {}
        if daten.get("pruefung"):
            print("  PRÜFAUFTRAG des Wächters (bis 28.10.2026; seitdem Meldungen): veränderliche Angaben, die nachzuschlagen waren.")
        elif daten.get("weg") == "direkt":
            print(f"  ENTSCHEIDUNG von {e.get('name')} im Gespräch (Claude-App, bis 29.10.2026 als Auftrag): bereits geprüft.")
        elif daten.get("neue_reise"):
            print(f"  NEUE REISE von {e.get('name')} (Claude-App): reisen/{daten['neue_reise']['pfad']}, legt der Schreibweg an.")
        elif daten.get("einladung"):
            print(f"  EINLADUNG von {e.get('name')} (Claude-App, bis 29.10.2026 als Auftrag): Zugang und Rolle gelten.")
        elif e["art"] == "Auftrag":
            print(f"  ÄNDERUNGSAUFTRAG von {e.get('name')} (Organisator:in, Claude-App, bis 29.10.2026) – zählt als Entscheidung; "
                  "wird im AI-Client eingetragen und mit rueckmeldung_erledigen abgeschlossen:")
        if e["status"] == "konflikt":
            print("  KONFLIKT: widerspricht einer anderen Entscheidung; nichts davon gilt, bis die Organisator:innen es klären.")
        print(f"  {e['ziel']} ({titel.get(e['ziel'], 'ID nicht auf der Seite')}) [{e['art']}]:")
        print("    " + e["text"].replace("\n", "\n    "))
        if e.get("quelle"):
            print(f"  Quelle: {e['quelle']}")
        if e.get("kommentar"):
            print(f"  → {e['kommentar']}")
    print(f"\n{len(es)} Rückmeldung(en).")


def status_setzen(o, rid, status, kommentar, wer=None):
    """Status einer Rückmeldung oder eines Auftrags setzen -> (Eintrag, None) oder (None, Fehler). Aufrufer hält _sperre."""
    if status not in STATUSWERTE:
        return None, f"Status muss einer von {', '.join(sorted(STATUSWERTE))} sein."
    if rid not in {e["id"] for e in eintraege(o) + auftraege(o)}:
        return None, f"{rid} gibt es nicht."
    alle = status_lesen(o)
    alle[rid] = {"status": status, "kommentar": kommentar, "datum": datetime.date.today().isoformat(), **({"wer": wer} if wer else {})}
    schreiben(o / "status.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
    return alle[rid], None


def setze(reise, rid, status, kommentar):
    o = muss_ordner(reise)
    with _sperre:
        _, fehler = status_setzen(o, rid, status, kommentar)
    if fehler:
        sys.exit(fehler)
    print(f"{rid}: {status}" + (f" – {kommentar}" if kommentar else ""))


def dienstordner():
    """Ordner der Dienste neben der Ablage (<Seiten>/_dienst): Stände, Stempel, vorgemerkte Links neuer Reisen."""
    return ablage().parent / "_dienst"


def aufgaben_text(liste, titel=None, fristen=True):
    """Lesbare Aufgabenliste (Kommandozeile und Konnektor). titel: ID -> Titel. fristen: False vor dem Status „fest“,
    dann steht die Frist da, aber nichts ist überfällig (Verhalten je Status)."""
    heute = datetime.date.today().isoformat()
    z = []
    for a in liste:
        teile = [f"{a['id']} [{a['status']}]"]
        if a.get("prioritaet") and a["prioritaet"] != "normal":
            teile.append(f"Priorität {a['prioritaet']}")
        if a.get("frist"):
            teile.append(f"Frist {a['frist']}" + (" ÜBERFÄLLIG" if fristen and a["frist"] < heute and a["status"] in ("offen", "in_arbeit") else ""))
        if a.get("ab"):
            teile.append(f"ab {a['ab']}")
        if a.get("zustaendig"):
            teile.append(f"zuständig {a['zustaendig']}")
        z.append(" · ".join(teile) + f": {a['titel']}")
        if a.get("bezug"):
            z.append("  an: " + ", ".join(f"{b} ({titel[b]})" if titel and b in titel else b for b in a["bezug"]))
        if a.get("notiz"):
            z.append("  Notiz: " + a["notiz"].replace("\n", " "))
        letzte = a["verlauf"][-1] if a.get("verlauf") else None
        if letzte:
            z.append(f"  zuletzt: {letzte['zeit'][:10]} {letzte['wer']} – {letzte['was']}"
                     + (f": {letzte['kommentar']}" if letzte.get("kommentar") else ""))
    return "\n".join(z)


def ag_sortierung(a):
    """Offene zuerst, darin hoch vor normal vor niedrig, dann nach Frist (ohne Frist zuletzt)."""
    return (AG_STATUS.index(a["status"]) if a["status"] in AG_STATUS else 9,
            AG_PRIO.index(a.get("prioritaet", "normal")) if a.get("prioritaet") in AG_PRIO else 1,
            a.get("frist") or "9999", a["id"])


def aufgaben_liste(reise, alle):
    o = muss_ordner(reise)
    es = sorted((a for a in aufgaben(o) if alle or a["status"] in ("offen", "in_arbeit")), key=ag_sortierung)
    if not es:
        print("Keine offenen Aufgaben." if not alle else "Keine Aufgaben.")
        return
    z = zustand(reise)
    print(aufgaben_text(es, titel_zu(reise), rg.verhalten(z["status"])["fristen"] if z else True))
    print(f"\n{len(es)} Aufgabe(n).")


def main(a):
    if a[:1] == ["dienst"]:
        dienst()
    elif a[:1] == ["liste"] and len(a) >= 2:
        liste(a[1], "--alle" in a)
    elif a[:1] == ["aufgaben"] and len(a) >= 2:
        aufgaben_liste(a[1], "--alle" in a)
    elif a[:1] == ["setze"] and len(a) >= 4:
        setze(a[1], a[2], a[3], " ".join(a[4:]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
