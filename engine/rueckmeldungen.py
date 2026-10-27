#!/usr/bin/env python3
"""Rückmeldungen von der Reise-Seite – Ablage für Claude Code.


Die Seite schickt Kommentare, Fragen, Korrekturen und Ergänzungen zu einer ID (T-01, V-03.a, E-07 …)
an diesen Dienst. Er hängt sie an <ablage>/<reise>/eingang.jsonl an. Claude Code liest sie auf Zuruf
(„Rückmeldungen einarbeiten“), prüft sie, arbeitet sie ins Repo ein und setzt den Status mit Kommentar
in <ablage>/<reise>/status.json; die Seite zeigt Status und Kommentar an.
Wünsche (Art „Wunsch“, Ziel „wuensche“) sind Ideen der Mitreisenden ohne feste Stelle; die Seite zeigt sie im
Reiter „Wünsche“, wenn die Reise ihn einschaltet (reise.yaml bausteine).
Änderungsaufträge (A-…) von Bestimmern aus der Claude-App legt engine/konnektor.py in auftraege.jsonl ab;
liste und setze behandeln sie wie Rückmeldungen.

Aufgaben (AG-01 …, 24.10.2026): hängen an einer oder mehreren IDs, haben Zuständig, Priorität,
„ab“ und Frist, Status und Verlauf. Alle dürfen sie sofort anlegen und ändern (Seite und Claude-App).
Sie liegen live in <ablage>/<reise>/aufgaben.json, nicht im Repo; dieser Dienst ist ihr einziger Schreiber.
Nichts wird gelöscht: nicht mehr Nötiges bekommt den Status „entfaellt“.

Ein Dienst für alle Reisen. Eine Reise nimmt nur Rückmeldungen an, wenn ihr Ordner in der Ablage
existiert (legt das Veröffentlichen an). Die Ablage liegt außerhalb des Repos und außerhalb der Web-Ordner.

Aufrufe:
  python3 engine/rueckmeldungen.py liste <reise> [--alle]          neue und Konflikte (bzw. alle) zeigen, mit Aufträgen
  python3 engine/rueckmeldungen.py setze <reise> R-…|A-… STATUS [KOMMENTAR]
        STATUS: uebernommen | verworfen | rueckfrage | konflikt | neu
  python3 engine/rueckmeldungen.py aufgaben <reise> [--alle]       offene (bzw. alle) Aufgaben zeigen
  python3 engine/rueckmeldungen.py laeufe [<reise>] [--alle]       Läufe des automatischen Einarbeitens: Wartezeit,
        Dauer (Protokoll einarbeiten-laeufe.jsonl, geschrieben vom Betriebsskript; RM_LAEUFE überschreibt den Ort)
  python3 engine/rueckmeldungen.py dienst                          Dienst starten
        Umgebung: RM_ABLAGE (Standard /srv/reisehandbuch/_rueckmeldungen),
                  RM_HOST (127.0.0.1), RM_PORT (8771)

HTTP (hinter nginx, Präfix /<reise>-<token>/api/ -> /<reise>/):
  GET    /<reise>/rueckmeldungen          alle, neueste zuerst, mit Status und Kommentar
  POST   /<reise>/rueckmeldungen          neue Rückmeldung (JSON)
  DELETE /<reise>/rueckmeldungen/<R-id>   zurückziehen, nur solange der Status „neu“ ist
  GET    /<reise>/aufgaben                alle Aufgaben
  POST   /<reise>/aufgaben                neue Aufgabe (JSON, name = wer sie anlegt) -> AG-…
  PATCH  /<reise>/aufgaben/<AG-id>        Felder ändern, Status setzen, Kommentar in den Verlauf (name = wer)
  GET    /<reise>/gesund                  200, wenn die Ablage beschreibbar ist (für die Überwachung)
"""
import datetime
import json
import os
import re
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
    return Path(os.environ.get("RM_ABLAGE", "/srv/reisehandbuch/_rueckmeldungen"))


def ordner(reise):
    """Ordner einer Reise oder None, wenn die Reise keine Rückmeldungen annimmt."""
    if not REISE_MUSTER.match(reise or ""):
        return None
    p = ablage() / reise
    return p if p.is_dir() else None


# ---------- Regeln der Reise (Rolle, Status, Bausteine) ----------

def seiten():
    return Path(os.environ.get("RM_SEITEN") or os.environ.get("KN_SEITEN") or "/srv/reisehandbuch")


def zustand(reise):
    """Status, Bausteine, Personen und Regeln aus der veröffentlichten Seite (<seiten>/<reise>/daten.json) oder None,
    wenn sie nicht lesbar ist (dann gelten nur die technischen Prüfungen, wie bisher). Eingeladene Personen, die noch
    nicht in reise.yaml stehen, zählen schon (einladungen.json)."""
    try:
        d = json.loads((seiten() / reise / "daten.json").read_text(encoding="utf-8"))["reise"]
        return {"status": d["status"]["wert"], "bausteine": d["bausteine"], "regeln": d.get("regeln") or {},
                "personen": personen_mit_einladungen(d["personen"], ordner(reise))}
    except (OSError, ValueError, KeyError, TypeError):
        return None


# ---------- Einladungen (Paket C): Personen, die in der Claude-App eingeladen wurden ----------
# Sie liegen live in <ablage>/<reise>/einladungen.json, weil der Dienst das Repo nicht ändert. Zugang und Rolle gelten
# sofort; Claude Code übernimmt die Person beim Einarbeiten nach reise.yaml (Auftrag mit daten.einladung). Steht sie dort,
# gilt die Angabe aus reise.yaml.
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
    aus = list(personen or [])
    schluessel = {p.get("schluessel") for p in aus}
    namen = {str(p.get("name", "")).casefold() for p in aus}
    for k, e in einladungen_lesen(o).items():
        if isinstance(e, dict) and k not in schluessel and str(e.get("name", "")).casefold() not in namen \
                and e.get("rolle") in rg.ROLLEN:
            aus.append({"schluessel": k, "name": e["name"], "rolle": e["rolle"], "reist": bool(e.get("reist", True)),
                        "notiz": e.get("notiz", ""), "eingeladen": True})
    return aus


def rolle_von(z, name):
    """Rolle einer Person aus reise.yaml nach Namen. Wer auf der Seite einen unbekannten Namen eintippt, kommt über den
    geheimen Link der Reise und gilt als Einbringer; eine bekannte Person hat die Rolle aus reise.yaml (reisend: nur lesen)."""
    for p in (z or {}).get("personen") or []:
        if p["name"].casefold() == (name or "").strip().casefold():
            return p["rolle"]
    return "einbringer"


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
    """Änderungsaufträge von Bestimmern aus der Claude-App (schreibt engine/konnektor.py). Nicht auf der Seite."""
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

    def do_GET(self):
        t = self._teile()
        if not t or t[2] is not None:
            return self._antwort(404, {"fehler": "unbekannt"})
        o, was, _ = t
        if was == "gesund":
            ok = os.access(o, os.W_OK)
            return self._antwort(200 if ok else 503, {"gesund": ok})
        if was == "aufgaben":
            return self._antwort(200, aufgaben(o))
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
        if not t or t[1] != "aufgaben" or not AG_MUSTER.match(t[2] or ""):
            return self._antwort(404, {"fehler": "unbekannt"})
        roh, fehlt = self._json()
        if fehlt:
            return
        if (nein := schreibrecht(t[0].name, "aufgabe", roh.get("name") if isinstance(roh, dict) else None)):
            return self._antwort(403, {"fehler": nein})
        with _sperre:
            if gedrosselt(t[0]):
                return self._antwort(429, {"fehler": "zu viele Änderungen, bitte kurz warten"})
            a, fehler, code = aufgabe_aendern(t[0], t[2], roh)
        self._antwort(code, {"fehler": fehler} if fehler else a)

    def do_POST(self):
        t = self._teile()
        if not t or t[1] not in ("rueckmeldungen", "aufgaben") or t[2] is not None:
            return self._antwort(404, {"fehler": "unbekannt"})
        o = t[0]
        roh, fehlt = self._json()
        if fehlt:
            return
        if t[1] == "aufgaben":
            if (nein := schreibrecht(o.name, "aufgabe", roh.get("name") if isinstance(roh, dict) else None)):
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
        if z and rg.verhalten(z["status"])["schreiben"] == "nichts":
            return self._antwort(403, {"fehler": "Die Reise ist archiviert: Es kann nur gelesen werden."})
        with _sperre:
            eingang = o / "eingang.jsonl"
            if not eingang.exists():
                return self._antwort(404, {"fehler": "nicht gefunden"})
            if status_lesen(o).get(rid, {}).get("status", "neu") != "neu":
                return self._antwort(409, {"fehler": "schon bearbeitet, kann nicht mehr zurückgezogen werden"})
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
    o = ordner(reise)
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
    for e in reversed(es):
        print(f"{e['id']}  {e['erstellt'][:16].replace('T', ' ')} UTC  {e.get('name')}  [{e['status']}]")
        daten = e.get("daten") or {}
        if daten.get("pruefung"):
            print(f"  PRÜFAUFTRAG des Wächters (keine Entscheidung eines Bestimmers): veränderliche Angaben nachschlagen, "
                  f"Prüfdatum und Quelle eintragen; bei Abweichung nichts ändern, sondern eine offene Frage anlegen.")
        elif daten.get("weg") == "direkt":
            print(f"  ENTSCHEIDUNG von {e.get('name')} im Gespräch (Claude-App), Weg direkt: bereits geprüft (Rolle, Option, "
                  f"Konflikte). Einarbeiten, nicht neu entscheiden.")
        elif daten.get("einladung"):
            print(f"  EINLADUNG von {e.get('name')} (Claude-App): Zugang und Rolle gelten schon. In reise.yaml unter personen "
                  f"eintragen (Schlüssel, name, rolle, reist, notiz wie im Text).")
        elif e["art"] == "Auftrag":
            print(f"  ÄNDERUNGSAUFTRAG von {e.get('name')} (Bestimmer, Claude-App) – zählt als Entscheidung:")
        if e["status"] == "konflikt":
            print("  KONFLIKT: widerspricht einer anderen Entscheidung. Nichts übernehmen. Offene Frage (F-…) anlegen, "
                  "beide Seiten darin nennen, dann mit „setze … rueckfrage“ auf die Frage verweisen.")
        print(f"  {e['ziel']} ({titel.get(e['ziel'], 'ID nicht auf der Seite')}) [{e['art']}]:")
        print("    " + e["text"].replace("\n", "\n    "))
        if e.get("quelle"):
            print(f"  Quelle: {e['quelle']}")
        if e.get("kommentar"):
            print(f"  → {e['kommentar']}")
    print(f"\n{len(es)} Rückmeldung(en).")


def setze(reise, rid, status, kommentar):
    o = muss_ordner(reise)
    if status not in STATUSWERTE:
        sys.exit(f"Status muss einer von {', '.join(sorted(STATUSWERTE))} sein.")
    with _sperre:
        if rid not in {e["id"] for e in eintraege(o) + auftraege(o)}:
            sys.exit(f"{rid} gibt es nicht.")
        alle = status_lesen(o)
        alle[rid] = {"status": status, "kommentar": kommentar, "datum": datetime.date.today().isoformat()}
        schreiben(o / "status.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
    print(f"{rid}: {status}" + (f" – {kommentar}" if kommentar else ""))


def laeufe_datei():
    """Protokoll der Einarbeitungsläufe: Standard <Ablage>/../_dienst/einarbeiten-laeufe.jsonl."""
    return Path(os.environ.get("RM_LAEUFE") or ablage().parent / "_dienst" / "einarbeiten-laeufe.jsonl")


def laeufe_lesen(reise=None):
    """Läufe, neueste zuletzt; mit reise nur die, an denen diese Reise beteiligt war. Kaputte Zeilen werden übersprungen."""
    try:
        zeilen = laeufe_datei().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    liste = []
    for z in zeilen:
        try:
            lauf = json.loads(z)
        except ValueError:
            continue
        if isinstance(lauf, dict) and (reise is None or reise in str(lauf.get("reisen", "")).split()):
            liste.append(lauf)
    return liste


def minuten_text(sekunden):
    if not isinstance(sekunden, (int, float)):
        return "?"
    return f"{sekunden / 60:.0f} min" if sekunden >= 90 else f"{sekunden:.0f} s"


def laeufe_text(liste, ausfuehrlich=True, tage=30, jetzt=None):
    """Zusammenfassung der Läufe. ausfuehrlich=False: nur ‚zuletzt eingearbeitet‘ (für Personen ohne Bestimmerrolle).
    Kosten stehen nur im Protokoll, nicht in der Anzeige (Entscheidung vom 26.10.2026: Kosten werden nicht gebraucht)."""
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    ok = [x for x in liste if x.get("ergebnis") == "ok"]
    z = []
    if not ok:
        z.append("Noch nichts automatisch eingearbeitet.")
    else:
        l = ok[-1]
        z.append(f"Zuletzt eingearbeitet: {l.get('zeit', '?')[:16].replace('T', ' ')} UTC, {l.get('anzahl', '?')} Eingabe(n)"
                 + ("" if l.get("online") == "ja" else " (noch nicht online)"))
    if not ausfuehrlich:
        return "\n".join(z)
    if liste and liste[-1].get("ergebnis") != "ok":
        z.append(f"Der letzte Lauf ist fehlgeschlagen ({liste[-1].get('zeit', '?')[:16].replace('T', ' ')} UTC).")
    grenze = (jetzt - datetime.timedelta(days=tage)).isoformat(timespec="seconds")
    neu = [x for x in liste if str(x.get("zeit", "")) >= grenze]
    warte = [x["eingabe_bis_ende_s"] for x in neu if x.get("ergebnis") == "ok" and isinstance(x.get("eingabe_bis_ende_s"), (int, float))]
    z.append(f"Letzte {tage} Tage: {len(neu)} Läufe, davon {sum(1 for x in neu if x.get('ergebnis') != 'ok')} fehlgeschlagen")
    if warte:
        z.append(f"- Von der Eingabe bis fertig: im Schnitt {minuten_text(sum(warte) / len(warte))}, "
                 f"am längsten {minuten_text(max(warte))}")
    if ok and isinstance(ok[-1].get("eingabe_bis_ende_s"), (int, float)):
        z.append(f"- Letzter erfolgreicher Lauf: {minuten_text(ok[-1]['eingabe_bis_ende_s'])} von der Eingabe bis fertig, "
                 f"Lauf selbst {minuten_text(ok[-1].get('dauer_s'))}")
    return "\n".join(z)


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
    elif a[:1] == ["laeufe"]:
        reise = next((x for x in a[1:] if not x.startswith("--")), None)
        gelaufen = laeufe_lesen(reise)
        print(laeufe_text(gelaufen))
        if "--alle" in a:
            for l in gelaufen:
                print(f"{l.get('zeit', '?')[:16]}  {l.get('ergebnis')}  {l.get('reisen')}  {l.get('anzahl')} Eingabe(n)  "
                      f"Wartezeit {minuten_text(l.get('eingabe_bis_ende_s'))}  Dauer {minuten_text(l.get('dauer_s'))}  "
                      f"online {l.get('online')}")
    elif a[:1] == ["setze"] and len(a) >= 4:
        setze(a[1], a[2], a[3], " ".join(a[4:]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
