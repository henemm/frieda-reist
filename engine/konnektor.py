#!/usr/bin/env python3
"""Konnektor fürs Reisehandbuch: macht eine Reise in der Claude-App nutzbar (MCP über HTTP).

In der Claude-App (Einstellungen → Konnektoren → eigenen Konnektor hinzufügen) wird ein geheimer Link
eingetragen. Danach kann Claude im Chat die Reise lesen (Tagesplan, Etappen, Varianten, offene Fragen,
Wissen) und Rückmeldungen abgeben. Ein Link gehört zu genau einer Reise und einer Person aus reise.yaml
(personen); die Rolle der Person entscheidet, was geht (docs/produkt.md, 26.10.2026):

  reisend      lesen
  einbringer   dazu Rückmeldungen, Wünsche, Alternativen vorschlagen (landen im Eingang wie die von der Seite),
               Aufgaben (AG-…) anlegen, ändern, abhaken – wirkt sofort, auch auf der Webseite (24.10.2026)
  bestimmer    dazu Änderungsaufträge, Entscheidungen (entscheiden) und Einladungen (person_einladen). Aufträge
               ändern nichts sofort; sie liegen in <ablage>/<reise>/auftraege.jsonl und werden von Claude Code
               geprüft und übernommen (ops/einarbeiten.sh). Eine Entscheidung wird je nach regeln.entscheidungsweg
               sofort vom Dienst geprüft und festgehalten (direkt) oder als Auftrag in Claude Code geprüft (auftrag).
  Paket C (26.10.2026): Einbringer beantworten Fragen (frage_beantworten); einladen darf, wer regeln.einladen
               erlaubt (Vorgabe: Bestimmer); person_einladen legt die Person an und stellt ihren Zugang aus.

Alte Links mit rolle mitreisend (vor dem 26.10.2026) gelten weiter als einbringer ohne festen Namen. Ein Link ohne Person (zugang <reise> einbringer) fragt nach dem Vornamen.

Gelesen wird die veröffentlichte Seite (<seiten>/<reise>/daten.json), also genau der Stand der Webseite.
Rückmeldungen gehen per HTTP an den Rückmeldedienst (ein Schreiber für eingang.jsonl), Aufträge schreibt
nur dieser Dienst.

Aufrufe:
  python3 engine/konnektor.py dienst                       Dienst starten
  python3 engine/konnektor.py zugang <reise> <person>|<rolle>      neuen geheimen Link anlegen (person aus reise.yaml
                                                           oder eingeladen; in der App geht das mit person_einladen)
  python3 engine/konnektor.py zugaenge                     angelegte Links zeigen
        Umgebung: KN_SEITEN (Standard /srv/reisehandbuch), KN_ZUGAENGE (/srv/reisehandbuch/_konnektor/zugaenge.json),
                  KN_RUECKMELDEDIENST (http://127.0.0.1:8771), KN_HOST (127.0.0.1), KN_PORT (8772),
                  KN_BASIS (öffentliche Adresse des Dienstes, für die Links), RM_ABLAGE wie beim Rückmeldedienst

HTTP (hinter nginx, Präfix /reisehandbuch-mcp/ -> /):
  POST /<token>     MCP (JSON-RPC, Streamable HTTP ohne Sitzung, Antwort als JSON)
  GET  /gesund      Readiness (Zugänge lesbar, verlinkte Reisen veröffentlicht), ohne Token
"""
import base64
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import threading
import urllib.error
import urllib.request
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rueckmeldungen as rm  # noqa: E402
from reise import (ENTSCHEIDUNGEN, LESE_BAUSTEIN, REISE_ZIEL, ROLLEN, VORGABEN, darf, erlaubt,  # noqa: E402
                   konflikte, schluessel_aus_name, verhalten)

ALTE_ROLLEN = {"mitreisend": "einbringer"}   # Links von vor dem 26.10.2026
PERSON_MUSTER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")
SCHREIB_WERKZEUGE = {"rueckmeldung_geben", "aufgabe_anlegen", "aufgabe_aendern", "alternative_vorschlagen",
                     "frage_beantworten", "entscheiden", "person_einladen"}
# Werkzeug -> Aktion der Regelprüfung (reise.AKTIONEN); rueckmeldung_geben mit Art Wunsch ist die Aktion „wunsch“
SCHREIB_AKTION = {"rueckmeldung_geben": "rueckmeldung", "aufgabe_anlegen": "aufgabe", "aufgabe_aendern": "aufgabe",
                  "alternative_vorschlagen": "alternative", "auftrag_geben": "auftrag", "entscheiden": "entscheiden",
                  "frage_beantworten": "antwort", "person_einladen": "einladen"}
# Werkzeuge, die zusätzlich eine zweite Aktion brauchen: eine Antwort landet als Rückmeldung (Art Antwort) im Eingang
ZUSATZ_AKTION = {"frage_beantworten": "rueckmeldung"}
WORT = {"gewaehlt": "gewählt", "verworfen": "verworfen", "ersetzt": "ersetzt"}
MAX_GRUND = 500
PROTOKOLLE = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
MAX_BODY = 64 * 1024
MAX_AUFTRAG = 4000
TOKEN_MUSTER = re.compile(r"^[A-Za-z0-9_-]{20,100}$")
AID_MUSTER = re.compile(r"^A-\d{8}-\d{6}-[0-9a-f]{4}$")

_sperre = threading.Lock()

CODE_DATEIEN = ("konnektor.py", "reise.py", "rueckmeldungen.py")


def code_stand():
    """Kurzer Hash des Codes, den der Dienst von der Platte lädt (konnektor.py und die Module daneben)."""
    h = hashlib.sha256()
    for n in CODE_DATEIEN:
        try:
            h.update((Path(__file__).resolve().parent / n).read_bytes())
        except OSError:
            h.update(b"-")
    return h.hexdigest()[:8]


_START = datetime.datetime.now().astimezone()
_CODE_START = code_stand()   # Stand des Codes beim Start; weicht er später von der Platte ab, fehlt ein Neustart


def seiten():
    return Path(os.environ.get("KN_SEITEN", "/srv/reisehandbuch"))


def zugaenge_pfad():
    return Path(os.environ.get("KN_ZUGAENGE", "/srv/reisehandbuch/_konnektor/zugaenge.json"))


def zugaenge():
    try:
        return json.loads(zugaenge_pfad().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def zugang_zu(token):
    """Token -> {"reise", "person"} bzw. {"reise", "rolle"} oder None. Bei jeder Anfrage neu gelesen: neue Links ohne Neustart."""
    if not TOKEN_MUSTER.match(token or ""):
        return None
    try:
        alle = zugaenge().items()
    except (OSError, ValueError, AttributeError):  # Datei kaputt oder unlesbar: niemand kommt rein, kein Absturz
        return None
    for t, z in alle:
        if hmac.compare_digest(t, token):
            if not isinstance(z, dict) or not rm.REISE_MUSTER.match(z.get("reise", "")):
                return None
            if isinstance(z.get("person"), str) and PERSON_MUSTER.match(z["person"]):
                return z
            return z if z.get("rolle") in ROLLEN or z.get("rolle") in ALTE_ROLLEN else None
    return None


def personen_der_reise(reise, d):
    """Personen aus reise.yaml (veröffentlichte Seite) plus Eingeladene, die dort noch fehlen (einladungen.json)."""
    return rm.personen_mit_einladungen(((d or {}).get("reise") or {}).get("personen") or [], rm.ordner(reise))


def wer_spricht(zugang, d):
    """Zugang + veröffentlichte Daten -> {"rolle", "name"} (name None: im Gespräch nach dem Vornamen fragen)
    oder None, wenn der Zugang zu keiner Person der Reise mehr gehört."""
    personen = personen_der_reise(zugang.get("reise"), d)
    if zugang.get("person"):
        p = next((x for x in personen if x.get("schluessel") == zugang["person"]), None)
        return {"rolle": p["rolle"], "name": p["name"]} if p else None
    rolle = zugang.get("rolle")
    return {"rolle": ALTE_ROLLEN.get(rolle, rolle), "name": None}


def zustand_von(d):
    """Status und eingeschaltete Bausteine aus den veröffentlichten Daten (None: unbekannt, dann keine Prüfung)."""
    rs = (d or {}).get("reise") or {}
    return (rs.get("status") or {}).get("wert"), rs.get("bausteine")


def regeln_von(d):
    return ((d or {}).get("reise") or {}).get("regeln") or {}


def recht(rolle, d, aktion, ziel=None):
    """Regelprüfung beim Schreiben (reise.erlaubt) mit dem Stand der Reise -> Fehlertext oder None."""
    status, bausteine = zustand_von(d)
    ok, grund = erlaubt(aktion, rolle, status or "planung", bausteine, ziel, regeln_von(d))
    return None if ok else grund


def bestimmer_namen(d):
    return [p["name"] for p in ((d or {}).get("reise") or {}).get("personen") or [] if p.get("rolle") == "bestimmer"]


# ---------- Seite lesen und in Text verwandeln ----------

class Text(HTMLParser):
    """HTML der Seite -> schlichter Text (Absätze, Listen, Tabellenzeilen mit |, Links als [Text](URL))."""
    BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "br", "blockquote", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.teile, self.link, self.zelle = [], None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.BLOCK or tag == "tr":
            self.teile.append("\n")
        if tag == "li":
            self.teile.append("\n- ")
        elif tag in ("td", "th"):
            self.teile.append(" | " if self.zelle else "| ")
            self.zelle = True
        elif tag == "tr":
            self.zelle = False
        elif tag == "a" and a.get("href", "").startswith("http"):
            self.link = a["href"]
            self.teile.append("[")
        elif tag == "img":
            self.teile.append(f"[Bild{': ' + a['alt'] if a.get('alt') else ''}]")

    def handle_endtag(self, tag):
        if tag == "a" and self.link:
            self.teile.append(f"]({self.link})")
            self.link = None
        elif tag == "tr":
            self.teile.append(" |")
        elif tag in self.BLOCK:
            self.teile.append("\n")

    def handle_data(self, data):
        self.teile.append(re.sub(r"\s+", " ", data))


def text(h):
    if not h:
        return ""
    p = Text()
    p.feed(h)
    t = "".join(p.teile)
    t = "\n".join(re.sub(r"\s*\|\s*", " | ", z).strip() if z.lstrip().startswith("|") else z.strip()
                  for z in t.splitlines())
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def daten(reise):
    try:
        return json.loads((seiten() / reise / "daten.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def symbole(reise):
    """Symbol der Reise (dasselbe wie auf der Seite) als MCP-Icons für serverInfo; die Claude-App zeigt es beim
    Konnektor. Data-URIs, damit kein weiterer Abruf und kein weiterer Pfad nötig ist. Fehlt es: keine Icons."""
    liste = []
    for g in (32, 192):
        try:
            roh = (seiten() / reise / f"icon-{g}.png").read_bytes()
        except OSError:
            continue
        liste.append({"src": "data:image/png;base64," + base64.b64encode(roh).decode("ascii"),
                      "mimeType": "image/png", "sizes": [f"{g}x{g}"]})
    return liste


def zeit_de(t):
    return t.astimezone().strftime("%d.%m.%Y %H:%M")


def stand_text(reise):
    """Woran man in der App sieht, ob das Veröffentlichen gelaufen ist: Bauzeit der Seite und Stand des Dienstes."""
    z = ["## Stand"]
    try:
        gebaut = datetime.datetime.fromtimestamp((seiten() / reise / "daten.json").stat().st_mtime).astimezone()
        z.append(f"- Reise zuletzt veröffentlicht: {zeit_de(gebaut)}")
    except OSError:
        z.append("- Reise: Zeitpunkt der Veröffentlichung unbekannt")
    jetzt = code_stand()
    z.append(f"- Konnektor gestartet: {zeit_de(_START)}, Code {_CODE_START}"
             + ("" if jetzt == _CODE_START else f" – auf dem Server liegt neuerer Code ({jetzt}), der Dienst braucht einen Neustart"
                " (sudo systemctl restart reisehandbuch-konnektor)"))
    return "\n".join(z)


def einarbeiten_text(reise, bestimmer):
    """Stand des automatischen Einarbeitens. Kosten und Wartezeiten sehen nur Bestimmer (Henning, 26.10.2026)."""
    liste = rm.laeufe_lesen(reise if not bestimmer else None)
    return "## Einarbeiten" + (" (alle Reisen zusammen)" if bestimmer else "") + "\n" + rm.laeufe_text(liste, mit_kosten=bestimmer)


def stunden(minuten):
    return f"{minuten // 60}:{minuten % 60:02d} h" if minuten else ""


def datum_de(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day}.{d.month}.{d.year}"


class Handbuch:
    """Alles, was eine Reise-Seite zeigt, nach ID nachschlagbar."""

    def __init__(self, d, aufgaben=None, offene_entscheidungen=None, antworten=None, meldungen=None):
        self.d = d
        self.aufgaben = aufgaben
        self.meldungen = meldungen or []   # Meldungen an die sprechende Person (Wächter, Erinnerer, Konflikte)
        self.offene_entscheidungen = offene_entscheidungen or {}   # Option-ID -> eingetragene, noch nicht eingearbeitete Entscheidungen
        self.antworten = antworten or {}                            # F-ID -> Antworten aus dem Eingang
        self.r = d.get("route") or {}
        rs = d.get("reise") or {}
        self.v = rs.get("verhalten") or verhalten((rs.get("status") or {}).get("wert"))
        self.bausteine = rs.get("bausteine")   # None: unbekannt, alles zeigen
        self.orte = self.r.get("orte") or {}
        self.eintraege = {}   # ID -> (Titel, Text)
        self.sammeln()

    def ort(self, oid):
        return (self.orte.get(oid) or {}).get("name") or oid or "?"

    def nacht(self, n):
        if not n:
            return ""
        if n.get("an_bord"):
            return "an Bord"
        teile = [self.ort(n.get("ort"))]
        u = (self.r.get("unterkuenfte") or {}).get(n.get("unterkunft") or "")
        if u:
            if u.get("name") == teile[0]:  # Unterkunft ist selbst der Ort (z. B. eine Hütte)
                teile.pop()
            teile.append(f"{u.get('name')} ({n['unterkunft']})")
        elif n.get("hinweis") or n.get("typ"):
            teile.append(n.get("hinweis") or n.get("typ"))
        if n.get("wahl"):
            teile.append(f"Wahl {n['wahl']}")
        return ", ".join(teile)

    def strecke(self, sid):
        s = (self.r.get("strecken") or {}).get(sid) or {}
        return s.get("titel") or sid

    def tag_text(self, t, datum=True):
        z = []
        if datum and t.get("datum"):
            z.append(f"Tag {t['nr']}, {t['wochentag']} {datum_de(t['datum'])}" + (f" ({t['teil']})" if t.get("teil") else ""))
        if t.get("strecken"):
            z.append("Wege: " + "; ".join(f"{self.strecke(s['id'])} ({s['id']}"
                                           + (f", Wahl {s['wahl']}" if s.get("wahl") else "") + ")"
                                           for s in t["strecken"]))
        if t.get("nacht"):
            z.append("Nacht: " + self.nacht(t["nacht"]))
        if t.get("fixpunkte"):
            z.append("Fest: " + "; ".join(t["fixpunkte"]))
        if t.get("wahlstellen"):
            z.append("Unterwegs zu entscheiden: " + ", ".join(t["wahlstellen"]))
        if t.get("text"):
            z.append(t["text"])
        return "\n".join(z)

    def summe(self, s):
        if not s:
            return ""
        z = [f"{s.get('tage')} Tage, {s.get('naechte')} Nächte"]
        if s.get("min"):
            z.append(f"Gehzeit {stunden(s['min'])}, ↑ {s.get('auf'):.0f} Hm, ↓ {s.get('ab'):.0f} Hm, {s.get('km')} km")
        if s.get("unterkunftstypen"):
            z.append("Unterkünfte: " + ", ".join(f"{k} {v}" for k, v in s["unterkunftstypen"].items()))
        return "; ".join(z)

    def merkmal_zeilen(self, kriterien, werte, fehlt=None):
        """Merkmale einer Option oder Unterkunft als Zeilen (Standard: docs/alternativen.md)."""
        z = []
        for k in kriterien or []:
            v = (werte or {}).get(k["id"])
            if not v:
                continue
            zusatz = [v["notiz"]] if v.get("notiz") else []
            if v.get("geprueft"):
                zusatz.append(f"geprüft {datum_de(v['geprueft'])}")
            elif v.get("ungeprueft"):
                zusatz.append("ungeprüft, vor Gebrauch nachschlagen")
            if v.get("quelle"):
                zusatz.append(f"Quelle: {v['quelle']}")
            if v.get("auto"):
                zusatz.append("berechnet")
            z.append(f"- {k['name']}: {v['wert']}" + (f" ({'; '.join(zusatz)})" if zusatz else ""))
        if fehlt:
            namen = {k["id"]: k["name"] for k in kriterien or []}
            z.append("Fehlt noch: " + ", ".join(namen.get(k, k) for k in fehlt))
        return z

    def kriterien_von(self, id_):
        """-> (Wahlstelle, Bereich, Kriterien) zu V-…, V-….x oder U-…"""
        for w in self.r.get("wahlstellen", []):
            if id_ == w["id"] or any(o["id"] == id_ for o in w["optionen"]):
                return w, w.get("bereich", "allgemein"), w.get("kriterien") or []
        if id_ in (self.r.get("unterkuenfte") or {}):
            return None, "unterkunft", (self.r.get("merkmale") or {}).get("unterkunft") or []
        return None, None, None

    def option_text(self, o, w=None):
        z = [f"Status: {o.get('status')}" + (" (im aktuellen Plan)" if o.get("aktiv") else "")]
        if w and (o.get("merkmale") or o.get("fehlt")):
            z.append("Merkmale:")
            z += self.merkmal_zeilen(w.get("kriterien"), o.get("merkmale"), o.get("fehlt"))
        for k, name in (("text", ""), ("ausloeser", "Auslöser: "), ("quelle", "Quelle: "), ("siehe", "Siehe: ")):
            if o.get(k):
                z.append(name + str(o[k]))
        if o.get("plus"):
            z.append("Dafür: " + "; ".join(o["plus"]))
        if o.get("minus"):
            z.append("Dagegen: " + "; ".join(o["minus"]))
        if o.get("tage"):
            z.append("Tage: " + ", ".join(o["tage"]))
        if o.get("summe"):
            z.append("Summe: " + self.summe(o["summe"]))
        for v in o.get("verlauf") or []:
            z.append(f"Verlauf {v.get('datum')}: {v.get('status')}" + (f" ({v['wer']})" if v.get("wer") else "")
                     + (f" – {v['grund']}" if v.get("grund") else ""))
        z += self.offen_zeilen(o["id"])
        return "\n".join(z)

    def offen_zeilen(self, oid):
        """Entscheidungen zu dieser Option, die eingetragen, aber noch nicht in der Seite eingearbeitet sind."""
        return [f"Eingetragen, noch nicht auf der Seite: {WORT.get(e['entscheidung'], e['entscheidung'])} von {e['wer']} "
                f"am {datum_de(e['datum'])} ({e['auftrag']}, "
                + ("im Gespräch geprüft" if e["weg"] == "direkt" else "als Auftrag, wird noch geprüft")
                + (", WIDERSPRUCH – wartet auf eine offene Frage" if e["status"] == "konflikt" else "") + ")"
                for e in self.offene_entscheidungen.get(oid, [])]

    def sammeln(self):
        e = self.eintraege
        for a in self.d.get("abschnitte", []):
            z = []
            if a.get("kennzahlen"):
                z.append("; ".join(f"{k}: {v}" for k, v in a["kennzahlen"].items()))
            z.append(text(a.get("intro")))
            if a.get("tabelle"):
                t = a["tabelle"]
                z.append(" | ".join(t["spalten"]))
                z += [f"{r['id']}: " + " | ".join(r["zellen"]) for r in t["zeilen"]]
            z.append(text(a.get("nach")))
            if a.get("route_ansicht") == "tagesplan":
                z.append("(Tagesplan: siehe Überblick bzw. die einzelnen Tage T-…)")
            if a.get("route_ansicht") == "unterkuenfte":
                z.append("(Unterkünfte: siehe die einzelnen U-…)")
            if a.get("bloecke"):
                z.append("Unterabschnitte: " + "; ".join(f"{b['id']} {b['titel']}" for b in a["bloecke"]))
            # Orte ↔ Recherche (reise.json orte_wissen)
            if a.get("wissen"):
                z.append("Aus der Recherche: " + "; ".join(f"{w['id']} {w['titel']}" + (f" ({w['notiz']})" if w.get("notiz") else "")
                                                         for w in a["wissen"]))
            if a.get("orte"):
                z.append("Orte: " + ", ".join(a["orte"]))
            e[a["id"]] = (a["titel"], "\n\n".join(x for x in z if x))
            for b in a.get("bloecke", []):
                e[b["id"]] = (f"{a['titel']} › {b['titel']}",
                              "\n\n".join(x for x in (("Orte: " + ", ".join(b["orte"])) if b.get("orte") else "", text(b.get("html"))) if x))
        f = self.d.get("fragen") or {}
        for zeile in f.get("zeilen", []):
            e[zeile["id"]] = (zeile["zellen"][1] if len(zeile["zellen"]) > 1 else zeile["id"],
                              "\n".join(f"{k}: {v}" for k, v in zip(f["spalten"], zeile["zellen"])))
        r = self.r
        for t in r.get("tage", []):
            e[t["id"]] = (f"Tag {t['nr']} ({datum_de(t['datum'])}): {t['titel']}", self.tag_text(t))
        for tid, t in (r.get("weitere_tage") or {}).items():
            e[tid] = (f"Variante: {t['titel']}", "Nicht im aktuellen Plan (gehört zu einer anderen Option).\n"
                      + self.tag_text(t, datum=False))
        for oid, o in self.orte.items():
            e.setdefault(oid, (o.get("name") or oid, o.get("hinweis") or ""))
        for sid, s in (r.get("strecken") or {}).items():
            z = [f"{self.ort(s.get('von'))} → {self.ort(s.get('nach'))}" + (f" ({' + '.join(s['art']) if isinstance(s['art'], list) else s['art']})" if s.get("art") else "")]
            if s.get("kennzahlen") and sid not in e:  # bei Etappen stehen sie schon im Dossier
                z.append("; ".join(f"{k}: {v}" for k, v in s["kennzahlen"].items()))
            for k in ("text", "quelle", "siehe"):
                if s.get(k):
                    z.append(("Quelle: " if k == "quelle" else "Siehe: " if k == "siehe" else "") + str(s[k]))
            if sid in e:  # Etappe aus dem Dossier: Text dort, Strecke ergänzt
                titel, alt = e[sid]
                e[sid] = (titel, "\n".join(z) + "\n\n" + alt)
            else:
                e[sid] = (s.get("titel") or sid, "\n".join(z))
        for uid, u in (r.get("unterkuenfte") or {}).items():
            z = [f"{u.get('typ') or ''} in {self.ort(u.get('ort'))}".strip()]
            for k, name in (("hinweis", ""), ("kontakt", "Kontakt: "), ("buchung", "Buchung: "),
                            ("frage", "Offene Frage: "), ("quelle", "Quelle: ")):
                if u.get(k):
                    z.append(name + str(u[k]))
            if u.get("naechte"):
                z.append("Nächte: " + ", ".join(u["naechte"]))
            if u.get("merkmale") or u.get("fehlt"):
                z.append("Merkmale:")
                z += self.merkmal_zeilen((r.get("merkmale") or {}).get("unterkunft"), u.get("merkmale"), u.get("fehlt"))
            e[uid] = (u.get("name") or uid, "\n".join(z))
        for p in r.get("plaene", []):
            z = [p.get("text") or "", "Auswahl: " + ", ".join(p.get("auswahl") or [])]
            if p.get("aktuell"):
                z.append("Das ist der aktuelle Plan.")
            if p.get("plus"):
                z.append("Dafür: " + "; ".join(p["plus"]))
            if p.get("minus"):
                z.append("Dagegen: " + "; ".join(p["minus"]))
            z += [f"{t['id']} {t['titel']}" + (f" – Nacht: {self.nacht(t.get('nacht'))}" if t.get("nacht") else "")
                  for t in p.get("tage", [])]
            e[p["id"]] = (f"{p['kurz']}: {p['titel']}", "\n".join(x for x in z if x))
        for w in r.get("wahlstellen", []):
            z = [f"Art: {w.get('art')}" + (" (offen)" if w.get("offen") else "")]
            if w.get("frage"):
                z.append(f"Frage: {w['frage']}")
            if w.get("text"):
                z.append(w["text"])
            z += [f"{o['id']} {o['titel']} – {o.get('status')}" + (" (aktuell)" if o.get("aktiv") else "")
                  for o in w["optionen"]]
            e[w["id"]] = (w["titel"], "\n".join(z))
            for o in w["optionen"]:
                e[o["id"]] = (f"{w['titel']} › {o['titel']}", self.option_text(o, w))

    # ---------- Antworten der Werkzeuge ----------
    def ueberblick(self):
        rs = self.d.get("reise", {})
        z = [f"# {rs.get('titel')}", rs.get("untertitel", "")]
        if self.d.get("plan_kopf"):
            z.append(text(self.d["plan_kopf"]))
        if self.r.get("summe"):
            z.append("Aktueller Plan: " + self.summe(self.r["summe"]))
        if self.v["start"] == "heute" and self.r.get("tage"):
            heute = datetime.date.today().isoformat()
            tag = next((t for t in self.r["tage"] if t["datum"] == heute), None)
            z.append("## Heute" + (f": {tag['id']} Tag {tag['nr']}, {tag['titel']}"
                                    + (f" – Nacht: {self.nacht(tag.get('nacht'))}" if tag.get("nacht") else "")
                                    if tag else ": kein Tag im Plan"))
        if self.r.get("tage"):
            z.append("## Tagesplan (aktueller Stand)")
            teil = None
            for t in self.r["tage"]:
                if t.get("teil") and t["teil"] != teil:
                    teil = t["teil"]
                    z.append(f"### {teil}")
                z.append(f"- {t['id']} Tag {t['nr']}, {t['wochentag']} {datum_de(t['datum'])}: {t['titel']}"
                         + (f" – Nacht: {self.nacht(t.get('nacht'))}" if t.get("nacht") else ""))
        if self.an("fragen"):
            z.append(f"## Offene Fragen: {len(self.offene())} (Werkzeug offene_fragen)")
        if self.aufgaben is not None and self.an("aufgaben"):
            offene_ag = [a for a in self.aufgaben if a["status"] in ("offen", "in_arbeit")]
            heute = datetime.date.today().isoformat()
            ueber = [a for a in offene_ag if a.get("frist") and a["frist"] < heute] if self.v["fristen"] else []
            z.append(f"## Offene Aufgaben: {len(offene_ag)}" + (f", davon {len(ueber)} überfällig" if ueber else "")
                     + " (Werkzeug aufgaben)")
            z += [f"- {a['id']} Frist {a['frist']}: {a['titel']}" for a in ueber]
        if self.meldungen:
            z.append("## Meldungen an dich")
            z += [f"- {m['erstellt'][:10]}: {m['text']}" for m in self.meldungen[:10]]
        if self.r.get("mahnungen"):
            z.append("## Mahnungen (die Reise ist fest oder unterwegs)")
            z += [f"- {m['text']}" for m in self.r["mahnungen"]]
        if self.r.get("wahlstellen") and self.an("varianten"):
            z.append("## Wahlstellen (Werkzeug varianten)")
            z += [f"- {w['id']} {w['titel']}" + (" – offen" if w.get("offen") else "")
                  + (" – unterwegs wählen" if w.get("art") == "unterwegs" and self.v["ausloeser_vor"] else "")
                  for w in sorted(self.r["wahlstellen"], key=lambda w: not (self.v["ausloeser_vor"] and w.get("art") == "unterwegs"))]
        z.append("## Inhalt (mit zeige nachschlagen)")
        z += [f"- {a['id']} {a['titel']}" for a in self.d.get("abschnitte", [])]
        if self.r.get("warnungen"):
            z.append("## Hinweise der Prüfung")
            z += [f"- {w['text']}" for w in self.r["warnungen"]]
        return "\n".join(x for x in z if x)

    def zeige(self, id_):
        if self.aufgaben is not None and rm.AG_MUSTER.match(id_):
            a = next((x for x in self.aufgaben if x["id"] == id_), None)
            return (aufgabe_text(a, self.titel()), None) if a else (None, "Diese Aufgabe gibt es nicht.")
        if id_ not in self.eintraege:
            nah = [k for k in self.eintraege if k.lower().startswith(id_.lower())][:20]
            return None, ("Diese ID gibt es nicht." + (f" Meinst du: {', '.join(nah)}?" if nah else ""))
        titel, t = self.eintraege[id_]
        aus = f"{id_} – {titel}\n\n{t}".strip()
        if self.antworten.get(id_):
            aus += "\n\n## Antworten (Eingaben, keine Entscheidung)\n" + "\n".join(
                f"- {a['erstellt'][:10]} {a.get('name')}: {a['text']}" + (f" (Quelle: {a['quelle']})" if a.get("quelle") else "")
                for a in self.antworten[id_])
        dran = aufgaben_filter(self.aufgaben or [], {"bezug": id_, "status": "alle"})
        if dran:
            aus += "\n\n## Aufgaben hier\n" + rm.aufgaben_text(dran, self.titel(), self.v["fristen"])
        return aus, None

    def titel(self):
        return {k: t for k, (t, _) in self.eintraege.items()}

    def suche(self, begriff, grenze=25):
        worte = [w for w in begriff.lower().split() if w]
        treffer = []
        for k, (titel, t) in self.eintraege.items():
            ganz = f"{titel}\n{t}".lower()
            if worte and all(w in ganz for w in worte):
                pos = ganz.find(worte[0])
                schnipsel = f"{titel}\n{t}"[max(0, pos - 80):pos + 160].replace("\n", " ")
                treffer.append(f"- {k} {titel}: …{schnipsel}…")
        if not treffer:
            return "Nichts gefunden."
        mehr = f"\n(… und {len(treffer) - grenze} weitere, genauer suchen)" if len(treffer) > grenze else ""
        return "\n".join(treffer[:grenze]) + mehr

    def an(self, baustein):
        """Ist der Baustein bei dieser Reise eingeschaltet? Unbekannt (alte Daten) zählt als an."""
        return self.bausteine is None or baustein in self.bausteine

    def offene(self):
        return [z for z in (self.d.get("fragen") or {}).get("zeilen", []) if z.get("status", "").lower().startswith("offen")]

    def fragen(self, alle):
        f = self.d.get("fragen") or {}
        zeilen = f.get("zeilen", []) if alle else self.offene()
        if not zeilen:
            return "Keine offenen Fragen." if not alle else "Keine Fragen."
        return "\n".join([" | ".join(f.get("spalten", []))] + [" | ".join(z["zellen"]) for z in zeilen])

    def merkmale(self, ziel, bereich):
        """Welche Merkmale eine Alternative braucht, was schon da ist und was fehlt (Werkzeug merkmale)."""
        katalog = self.r.get("merkmale") or {}
        if ziel:
            w, b, krit = self.kriterien_von(ziel)
            if krit is None:
                return None, "Zu dieser ID gibt es keine Merkmale. Erlaubt: Wahlstelle V-…, Option V-….a, Unterkunft U-…."
        elif bereich in katalog:
            w, b, krit = None, bereich, katalog[bereich]
        else:
            return None, f"ziel (V-…, U-…) oder bereich ({', '.join(katalog) or 'unterkunft, strecke, route'}) angeben."
        z = [f"# Merkmale für Bereich {b}" + (f" – {w['id']} {w['titel']}" if w else f" – {ziel}" if ziel else ""),
             "Vorgehen: Erst selbst recherchieren (Hinweis „so finden“), dann die Person nur nach dem fragen, was offen "
             "bleibt (Hinweis „fragen“). Veränderliche Werte mit Prüfdatum. Eine neue Alternative mit "
             "alternative_vorschlagen weitergeben, vorher kurz bestätigen lassen.", "## Liste"]
        for k in krit:
            art = k.get("typ", "text") + (f" ({' | '.join(k['werte'])})" if k.get("werte") else "")
            zeile = f"- {k['id']} – {k['name']}: {art}"
            if k.get("auto"):
                zeile += "; wird aus dem Plan berechnet, nicht eintragen"
            if k.get("veraenderlich"):
                zeile += "; veränderlich, braucht Prüfdatum"
            if k.get("hilfe"):
                zeile += f"; so finden: {k['hilfe']}"
            if k.get("frage"):
                zeile += f"; fragen: „{k['frage']}“"
            z.append(zeile)
        if w:
            for o in w["optionen"]:
                z.append(f"## {o['id']} {o['titel']} ({o.get('status')})")
                z += self.merkmal_zeilen(krit, o.get("merkmale"), [] if o.get("status") in ("verworfen", "ersetzt")
                                         else o.get("fehlt")) or ["(keine Merkmale)"]
        elif ziel:
            u = self.r["unterkuenfte"][ziel]
            z.append(f"## {ziel} {u.get('name')}")
            z += self.merkmal_zeilen(krit, u.get("merkmale"), u.get("fehlt")) or ["(keine Merkmale)"]
        return "\n".join(z), None

    def option(self, oid):
        """-> (Wahlstelle, Option) zu einer Option-ID V-01.a oder (None, None)."""
        for w in self.r.get("wahlstellen", []):
            for o in w["optionen"]:
                if o["id"] == oid:
                    return w, o
        return None, None

    def entscheidung_pruefen(self, args, wer, heute=None):
        """Eine Entscheidung im Gespräch prüfen (Paket C). Die Maschine lehnt Unstimmiges ab (Rückgabe fehler) und gibt
        Hinweise mit, die die Person wissen soll, die aber nichts verhindern. Widersprüche zwischen Bestimmern prüft
        danach konflikt_melden. -> (daten, hinweise, fehler); bei fehler ist daten None."""
        fehler, hinweise = [], []
        oid = str(args.get("option") or "").strip()
        status = str(args.get("status") or "").strip()
        grund = str(args.get("grund") or "").strip()
        durch = str(args.get("ersetzt_durch") or "").strip()
        quelle = str(args.get("quelle") or "").strip()
        w, o = self.option(oid)
        if o is None:
            stelle = next((x for x in self.r.get("wahlstellen", []) if x["id"] == oid), None)
            if stelle:
                return None, [], [f"{oid} ist eine Wahlstelle. Entschieden wird über eine Option: "
                                  + ", ".join(f"{x['id']} {x['titel']}" for x in stelle["optionen"]) + "."]
            return None, [], [f"Die Option „{oid}“ gibt es nicht. Mit varianten die Wahlstellen und ihre Optionen (V-01.a) ansehen."]
        if status not in ENTSCHEIDUNGEN:
            fehler.append(f"status muss einer von {', '.join(ENTSCHEIDUNGEN)} sein.")
        if not grund:
            fehler.append("Der Grund fehlt: jede Entscheidung hat einen Grund (in den Worten der Person), der in den Verlauf kommt.")
        elif len(grund) > MAX_GRUND or "\n" in grund:
            fehler.append(f"Der Grund passt in eine Zeile mit höchstens {MAX_GRUND} Zeichen.")
        if status == "ersetzt":
            wd, od = self.option(durch)
            if not durch:
                fehler.append("Bei „ersetzt“ gehört dazu, wodurch die Option ersetzt wird (ersetzt_durch, z. B. V-01.b).")
            elif od is None or wd is not w or durch == oid:
                fehler.append(f"ersetzt_durch muss eine andere Option derselben Wahlstelle {w['id']} sein "
                              f"({', '.join(x['id'] for x in w['optionen'] if x['id'] != oid)}).")
            elif od["status"] in ("verworfen", "ersetzt"):
                fehler.append(f"{durch} ist selbst {WORT[od['status']]} und kann nichts ersetzen.")
        elif durch:
            fehler.append("ersetzt_durch gibt es nur beim Status ersetzt.")
        if status in ENTSCHEIDUNGEN and o["status"] == status:
            fehler.append(f"{oid} ist schon {WORT[status]}; daran ändert sich nichts.")
        for e in self.offene_entscheidungen.get(oid, []):
            if e["wer"] == wer and e["entscheidung"] == status and e["status"] != "konflikt":
                fehler.append(f"Dieselbe Entscheidung liegt schon vor ({e['auftrag']}); sie wird noch eingearbeitet.")
        if fehler:
            return None, [], fehler
        andere = [x for x in w["optionen"] if x["id"] != oid and x["status"] == "gewaehlt"]
        if status == "gewaehlt" and andere:
            hinweise.append(f"{', '.join(x['id'] for x in andere)} ist bisher gewählt und wird dadurch ersetzt "
                            "(mit eigenem Verlaufseintrag).")
        if status in ("verworfen", "ersetzt") and o["status"] == "gewaehlt" and not andere:
            hinweise.append(f"{oid} war die gewählte Option: {w['id']} ist danach offen"
                            + (f" (Frage {w['frage']})" if w.get("frage") else "") + ".")
        if status == "gewaehlt":
            namen = {k["id"]: k["name"] for k in w.get("kriterien") or []}
            if o.get("fehlt"):
                hinweise.append("Es fehlen noch Merkmale: " + ", ".join(namen.get(k, k) for k in o["fehlt"])
                                + ". Sie werden beim Einarbeiten recherchiert und ergänzt.")
            offen = [namen.get(k, k) for k, v in (o.get("merkmale") or {}).items() if v.get("ungeprueft")]
            if offen:
                hinweise.append("Ungeprüfte veränderliche Angaben: " + ", ".join(offen) + " – vor dem Buchen nachschlagen.")
        if w.get("art") == "unterwegs" and not self.v["ausloeser_vor"]:
            hinweise.append(f"{w['id']} ist eine Wahlstelle für unterwegs"
                            + (f" (Auslöser: {o['ausloeser']})" if o.get("ausloeser") else "")
                            + ": Sie wird normalerweise erst unterwegs entschieden.")
        heute = heute or datetime.date.today()
        text_ = (f"Entscheidung von {wer} am {datum_de(heute.isoformat())}: {oid} „{o['titel']}“ ({w['id']} {w['titel']}) "
                 f"ist {WORT[status]}" + (f", ersetzt durch {durch}" if durch else "") + f".\nGrund: {grund}\n"
                 f"Herkunft: Entscheidung von {wer} im Gespräch in der Claude-App" + (f"; Quelle: {quelle}" if quelle else "")
                 + ".\nEinzutragen: Verlaufseintrag an der Option "
                 f"{{datum: {heute.isoformat()}, status: {status}, wer: {wer}, grund: …}}"
                 + (f"; bisher gewählt: {', '.join(x['id'] for x in andere)} bekommt ersetzt" if status == "gewaehlt" and andere else "")
                 + (f"; Frage {w['frage']} als geklärt eintragen" if w.get("frage") and status == "gewaehlt" else "") + ".")
        if hinweise:
            text_ += "\nHinweise der Vorprüfung:\n" + "\n".join(f"- {x}" for x in hinweise)
        daten = {"entscheidung": status, "option": oid, "wahlstelle": w["id"], "grund": grund, "datum": heute.isoformat(),
                 **({"ersetzt_durch": durch} if durch else {}), **({"quelle": quelle} if quelle else {}),
                 "hinweise": hinweise}
        return (text_, daten), hinweise, None

    def vorschlag(self, args):
        """Neue Alternative prüfen -> (Text für Auftrag/Rückmeldung, Ziel, Daten) oder Fehler."""
        katalog = self.r.get("merkmale") or {}
        vid = str(args.get("wahlstelle") or "").strip()
        an = str(args.get("an") or "").strip()
        titel = str(args.get("titel") or "").strip()
        if not titel:
            return None, "titel fehlt: Name der Alternative, z. B. das Hotel."
        if vid:
            w = next((x for x in self.r.get("wahlstellen", []) if x["id"] == vid), None)
            if not w:
                return None, f"Wahlstelle {vid} gibt es nicht. Mit varianten die richtige finden oder leer lassen."
            b, krit = w.get("bereich", "allgemein"), w.get("kriterien") or []
        else:
            w, b = None, str(args.get("bereich") or "")
            if b not in katalog:
                return None, f"Ohne Wahlstelle bitte bereich angeben ({', '.join(katalog)})."
            if not an or an not in self.eintraege:
                return None, "Ohne Wahlstelle bitte an angeben: die ID, an der die Alternative hängt (z. B. T-05, U-11)."
            krit = katalog[b]
        defs = {k["id"]: k for k in krit}
        roh = args.get("merkmale") or {}
        if not isinstance(roh, dict):
            return None, "merkmale muss ein Objekt {merkmal: {wert, quelle, geprueft, notiz}} sein."
        werte, neu = {}, []
        for k, v in roh.items():
            v = v if isinstance(v, dict) else {"wert": v}
            wert = str(v.get("wert", "")).strip()
            if not wert:
                continue
            d = defs.get(k)
            if d and d.get("auto"):
                continue
            if d and d.get("werte") and wert not in d["werte"]:
                return None, f"{k} = „{wert}“ geht nicht, erlaubt: {', '.join(d['werte'])}."
            g = str(v.get("geprueft") or "").strip()
            if g:
                try:
                    datetime.date.fromisoformat(g)
                except ValueError:
                    return None, f"{k}: geprueft als JJJJ-MM-TT angeben."
            werte[k] = {"wert": wert, **{f: str(v[f]).strip() for f in ("quelle", "notiz") if v.get(f)},
                        **({"geprueft": g} if g else {})}
            if not d:
                neu.append(k)
        listen = {f: [str(x) for x in args.get(f) or [] if str(x).strip()] for f in ("plus", "minus")}
        z = [f"Neue Alternative „{titel}“ " + (f"für {vid} ({w['titel']})" if w else f"an {an}, neue Wahlstelle")
             + f", Bereich {b}. Standard: docs/alternativen.md; Status höchstens vorgeschlagen."]
        if werte:
            z.append("Merkmale:")
            for k, v in werte.items():
                zusatz = [f"geprüft {v['geprueft']}"] if v.get("geprueft") else []
                zusatz += [f"Quelle: {v['quelle']}"] if v.get("quelle") else []
                zusatz += [v["notiz"]] if v.get("notiz") else []
                z.append(f"- {k}{' (neues Merkmal)' if k in neu else ''}: {v['wert']}"
                         + (f" ({'; '.join(zusatz)})" if zusatz else ""))
        fehlt = [d["name"] for d in krit if not d.get("auto") and d["id"] not in werte]
        if fehlt:
            z.append("Fehlt noch: " + ", ".join(fehlt))
        if listen["plus"]:
            z.append("Dafür: " + "; ".join(listen["plus"]))
        if listen["minus"]:
            z.append("Dagegen: " + "; ".join(listen["minus"]))
        for f, name in (("text", ""), ("quelle", "Quelle: ")):
            if str(args.get(f) or "").strip():
                z.append(name + str(args[f]).strip())
        daten = {"wahlstelle": vid or None, "an": an or None, "bereich": b, "titel": titel, "merkmale": werte, **listen}
        return ("\n".join(z), vid or an, daten), None

    def varianten(self):
        z = []
        for p in self.r.get("plaene", []):
            z.append(f"- {p['id']} {p['kurz']}: {p['titel']}" + (" (aktueller Plan)" if p.get("aktuell") else "")
                     + f" – Auswahl {', '.join(p.get('auswahl') or [])}")
        if z:
            z.insert(0, "## Benannte Pläne")
        z.append("## Wahlstellen")
        for w in self.r.get("wahlstellen", []):
            z.append(f"### {w['id']} {w['titel']} ({w.get('art')}" + (", offen" if w.get("offen") else "")
                     + (f", Frage {w['frage']}" if w.get("frage") else "") + ")")
            if w.get("text"):
                z.append(w["text"])
            for o in w["optionen"]:
                z.append(f"- {o['id']} {o['titel']} – {o.get('status')}" + (" (aktuell)" if o.get("aktiv") else "")
                         + (f"; dafür: {'; '.join(o['plus'])}" if o.get("plus") else "")
                         + (f"; dagegen: {'; '.join(o['minus'])}" if o.get("minus") else "")
                         + (f"; {self.summe(o['summe'])}" if o.get("summe") else ""))
                z += ["  " + x for x in self.merkmal_zeilen(w.get("kriterien"), o.get("merkmale"))
                      if not x.startswith("Fehlt")]
                z += ["  " + x for x in self.offen_zeilen(o["id"])]
        return "\n".join(z)


# ---------- Rückmeldungen und Aufträge ----------

def rueckmeldung_senden(reise, eintrag):
    """An den Rückmeldedienst, damit eingang.jsonl nur einen Schreiber hat. -> (antwort, fehler)"""
    return dienst_anfrage("POST", f"{reise}/rueckmeldungen", eintrag)


def dienst_anfrage(methode, pfad, daten):
    """Schreibender Aufruf beim Rückmeldedienst (einziger Schreiber der Ablage). -> (antwort, fehler)"""
    basis = os.environ.get("KN_RUECKMELDEDIENST", "http://127.0.0.1:8771").rstrip("/")
    req = urllib.request.Request(f"{basis}/{pfad}", method=methode,
                                 data=json.dumps(daten, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        try:
            return None, json.loads(e.read()).get("fehler", f"Fehler {e.code}")
        except (json.JSONDecodeError, AttributeError):
            return None, f"Fehler {e.code}"
    except (urllib.error.URLError, OSError):
        return None, "Rückmeldedienst nicht erreichbar, bitte später noch einmal"


def aufgaben_von(reise):
    o = rm.ordner(reise)
    return sorted(rm.aufgaben(o), key=rm.ag_sortierung) if o else []


def aufgabe_text(a, titel):
    """Eine Aufgabe ausführlich, mit Verlauf."""
    z = [rm.aufgaben_text([a], titel)]
    z.append(f"  angelegt {a['erstellt'][:10]} von {a.get('erstellt_von')}"
             + (f", erledigt am {a['erledigt']}" if a.get("erledigt") else ""))
    for v in a.get("verlauf", [])[1:]:
        felder = "; ".join(f"{k}: {alt or '–'} → {neu or '–'}" for k, (alt, neu) in (v.get("felder") or {}).items())
        z.append(f"  {v['zeit'][:10]} {v['wer']}: " + "; ".join(x for x in (felder, v.get("kommentar", "")) if x))
    return "\n".join(z)


def aufgaben_filter(liste, args):
    bezug = str(args.get("bezug") or "").strip()
    wer = str(args.get("zustaendig") or "").strip().lower()
    status = str(args.get("status") or "offen").strip()
    if bezug:
        liste = [a for a in liste if any(b == bezug or b.startswith(bezug + ".") for b in a.get("bezug", []))]
    if wer:
        liste = [a for a in liste if a.get("zustaendig", "").lower() == wer]
    if status == "offen":
        liste = [a for a in liste if a["status"] in ("offen", "in_arbeit")]
    elif status != "alle":
        liste = [a for a in liste if a["status"] == status]
    return liste


def auftrag_anlegen(reise, ziel, auftrag, daten=None, name="Bestimmer"):
    o = rm.ordner(reise)
    if o is None:
        return None, "Diese Reise nimmt noch keine Aufträge an."
    ziel, auftrag = (ziel or "").strip(), (auftrag or "").strip()
    if ziel and not rm.ZIEL_MUSTER.match(ziel):
        return None, "ungültige ID"
    if not auftrag:
        return None, "Auftrag fehlt"
    if len(auftrag) > MAX_AUFTRAG:
        return None, f"Auftrag zu lang (max. {MAX_AUFTRAG} Zeichen)"
    jetzt = datetime.datetime.now(datetime.timezone.utc)
    e = {"id": f"A-{jetzt:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}", "erstellt": jetzt.isoformat(timespec="seconds"),
         "name": name, "art": "Auftrag", "ziel": ziel or "allgemein", "text": auftrag, "quelle": "Claude-App"}
    if daten:
        e["daten"] = daten
    with _sperre:
        with (o / "auftraege.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
    return e, None


def stehende_entscheidungen(reise, d):
    """Entscheidungen, gegen die eine neue geprüft wird: die letzte Entscheidung je Option im veröffentlichten Plan
    und alle noch nicht bearbeiteten Aufträge mit Entscheidung. -> [{wer, ziel, entscheidung, quelle}]"""
    aus = []
    for w in ((d or {}).get("route") or {}).get("wahlstellen") or []:
        for o in w.get("optionen") or []:
            v = (o.get("verlauf") or [{}])[-1]
            if v.get("status") in ENTSCHEIDUNGEN and v.get("wer"):
                aus.append({"wer": v["wer"], "ziel": o["id"], "entscheidung": v["status"],
                            "quelle": f"{v['wer']} am {v.get('datum')} im Plan"})
    ordner = rm.ordner(reise)
    for a in rm.auftraege(ordner) if ordner else []:
        ent = (a.get("daten") or {}).get("entscheidung")
        if ent in ENTSCHEIDUNGEN and a["status"] in ("neu", "rueckfrage", "konflikt"):
            aus.append({"wer": a.get("name"), "ziel": a.get("ziel"), "entscheidung": ent, "auftrag": a["id"],
                        "quelle": f"Auftrag {a['id']} von {a.get('name')}"})
    return aus


def konflikt_melden(reise, auftrag, d):
    """Widerspricht die Entscheidung im Auftrag einer anderen (Regel regeln.konflikt = offene_frage)? Dann bekommen
    sie und die widersprechenden noch offenen Aufträge den Status „konflikt“ (nichts wird übernommen; Claude Code legt
    die offene Frage an), und alle beteiligten Bestimmer erhalten eine Meldung. -> Beschreibung oder None."""
    regeln = ((d or {}).get("reise") or {}).get("regeln") or {}
    if regeln.get("konflikt", "offene_frage") != "offene_frage":
        return None
    neu = {"wer": auftrag["name"], "ziel": auftrag["ziel"], "entscheidung": auftrag["daten"]["entscheidung"]}
    alt = konflikte(neu, stehende_entscheidungen(reise, d))
    alt = [a for a in alt if a.get("auftrag") != auftrag["id"]]
    if not alt:
        return None
    o = rm.ordner(reise)
    beschr = "; ".join(f"{a['quelle']}: {a['entscheidung']} {a['ziel']}" for a in alt)
    betroffen = [auftrag["id"]] + [a["auftrag"] for a in alt if a.get("auftrag")]
    with _sperre:
        status = rm.status_lesen(o)
        for aid in betroffen:
            status[aid] = {"status": "konflikt", "datum": datetime.date.today().isoformat(),
                           "kommentar": "Widerspruch zwischen Bestimmern: wird zur offenen Frage, nichts wird übernommen."}
        rm.schreiben(o / "status.json", json.dumps(status, ensure_ascii=False, indent=1) + "\n")
    bestimmer = set(bestimmer_namen(d)) & ({neu["wer"]} | {a["wer"] for a in alt})
    rm.meldung_anlegen(o, bestimmer or {neu["wer"]}, "konflikt", auftrag["ziel"],
                       f"{neu['wer']} will {neu['entscheidung']} {neu['ziel']}, aber {beschr}. Beides gilt nicht, bis ihr euch "
                       f"einig seid; Claude legt dafür eine offene Frage an.", betroffen)
    return beschr


def offene_entscheidungen(reise):
    """Entscheidungen im Gespräch, die eingetragen, aber noch nicht eingearbeitet sind: Option-ID -> Liste."""
    o = rm.ordner(reise)
    aus = {}
    for a in rm.auftraege(o) if o else []:
        dt = a.get("daten") or {}
        if dt.get("option") and dt.get("entscheidung") in ENTSCHEIDUNGEN and a["status"] in ("neu", "rueckfrage", "konflikt"):
            aus.setdefault(dt["option"], []).append({"wer": a.get("name"), "entscheidung": dt["entscheidung"], "auftrag": a["id"],
                                                     "datum": dt.get("datum") or a["erstellt"][:10], "status": a["status"],
                                                     "weg": dt.get("weg", "auftrag")})
    return aus


def antworten_von(reise):
    """Antworten (Rückmeldungen der Art Antwort) je Frage-ID, älteste zuerst."""
    o = rm.ordner(reise)
    aus = {}
    for e in reversed(rm.eintraege(o) if o else []):
        if e.get("art") == "Antwort" and e.get("status") != "verworfen":
            aus.setdefault(e["ziel"], []).append(e)
    return aus


# ---------- Entscheiden und Fragen beantworten (Paket C) ----------

def entscheiden(reise, d, h, wer, args):
    """Werkzeug entscheiden. Rolle, Status und Baustein sind schon geprüft. Der Dienst prüft die Entscheidung im Moment
    (Handbuch.entscheidung_pruefen) und hält sie als geprüften Auftrag fest; bei regeln.entscheidungsweg = direkt gilt sie
    damit, bei auftrag prüft sie zusätzlich Claude Code, bevor sie gilt. Ein Widerspruch zu einem anderen Bestimmer wird nicht
    übernommen, sondern zur offenen Frage (konflikt_melden). -> (Text, ist_fehler)"""
    if not wer["name"]:
        return ("Entscheiden geht nur mit dem persönlichen Link: Jede Entscheidung gehört genau einer Person, und dieser Link "
                "kennt keinen Namen. Ein Bestimmer kann mit person_einladen einen persönlichen Link ausstellen."), True
    if not all(isinstance(args.get(k) or "", str) for k in ("option", "status", "grund", "ersetzt_durch", "quelle")):
        return "Alle Angaben müssen Text sein.", True
    ergebnis, hinweise, fehler = h.entscheidung_pruefen(args, wer["name"])
    if fehler:
        return "Nicht entschieden:\n" + "\n".join(f"- {f}" for f in fehler), True
    text_, daten_ = ergebnis
    regeln = regeln_von(d)
    weg = regeln.get("entscheidungsweg") or VORGABEN["entscheidungsweg"]
    daten_.update({"weg": weg, "geprueft": weg == "direkt"})
    e, fehler = auftrag_anlegen(reise, daten_["option"], text_, daten_, name=wer["name"])
    if fehler:
        return f"Nicht gespeichert: {fehler}", True
    wort = WORT[daten_["entscheidung"]]
    k = konflikt_melden(reise, e, d)
    if k:
        return (f"Nicht entschieden: {daten_['option']} {wort} zu setzen widerspricht einer anderen Entscheidung ({k}). Nichts wird "
                f"übernommen, bis ihr euch einig seid: Daraus wird eine offene Frage, und alle beteiligten Bestimmer bekommen "
                f"eine Meldung (festgehalten als {e['id']}). Sag nie, etwas sei schon entschieden."), False
    z = []
    if weg == "direkt":
        z.append(f"Entscheidung {e['id']} geprüft und festgehalten: {daten_['option']} ist {wort} ({wer['name']}, "
                 f"{datum_de(daten_['datum'])}, Grund: {daten_['grund']}). Sie gilt ab jetzt. Auf der Seite steht sie, sobald "
                 "eingearbeitet ist (Sammelzeit, dann ein Lauf; den Stand zeigt rueckmeldungen).")
    else:
        z.append(f"Entscheidungsauftrag {e['id']} gespeichert: {daten_['option']} {wort} ({wer['name']}, "
                 f"{datum_de(daten_['datum'])}). Auf dieser Reise gilt der Weg auftrag: Er wird erst in Claude Code geprüft und "
                 "eingearbeitet, vorher ist nichts entschieden. Den Stand zeigt rueckmeldungen.")
    if hinweise:
        z.append("Hinweise:\n" + "\n".join(f"- {x}" for x in hinweise))
    return "\n".join(z), False


def frage_beantworten(reise, d, h, wer, args):
    """Werkzeug frage_beantworten: Die Antwort geht als Rückmeldung (Art Antwort) an die Frage. Sie ist eine Eingabe;
    ob die Frage geklärt ist, entscheidet ein Bestimmer. -> (Text, ist_fehler)"""
    if (nein := recht(wer["rolle"], d, "rueckmeldung")):
        return nein, True
    fid = args.get("frage")
    antwort = args.get("antwort")
    if not isinstance(fid, str) or not isinstance(antwort, str) or not isinstance(args.get("quelle") or "", str):
        return "frage, antwort und quelle müssen Text sein.", True
    fid, antwort = fid.strip(), antwort.strip()
    zeile = next((z for z in (h.d.get("fragen") or {}).get("zeilen", []) if z["id"] == fid), None)
    if zeile is None:
        return f"Die Frage „{fid}“ gibt es nicht. Mit offene_fragen die richtige F-… finden.", True
    if not zeile.get("status", "").lower().startswith("offen"):
        return (f"{fid} ist nicht mehr offen ({zeile.get('status')}). Neue Erkenntnisse dazu gibst du mit rueckmeldung_geben "
                "(Art Kommentar oder Korrektur) weiter."), True
    if not antwort:
        return "Die Antwort fehlt.", True
    name_ = wer["name"] or args.get("name")
    if not isinstance(name_, str) or not name_.strip():
        return "Name fehlt: bitte die Person nach ihrem Vornamen fragen.", True
    e, fehler = rueckmeldung_senden(reise, {"name": name_, "art": "Antwort", "ziel": fid, "text": antwort,
                                            "quelle": str(args.get("quelle") or "über Claude")})
    if fehler:
        return f"Nicht gespeichert: {fehler}", True
    stelle = next((w for w in h.r.get("wahlstellen", []) if w.get("frage") == fid), None)
    bestimmer = " und ".join(bestimmer_namen(d)) or "ein Bestimmer"
    z = [f"Antwort {e['id']} gespeichert, sie hängt an {fid} (zeige {fid} listet sie). Die Frage bleibt offen: Eine Antwort ist "
         f"eine Eingabe, ob damit geklärt ist und was daraus folgt, entscheidet {bestimmer}."]
    if stelle:
        z.append(f"Die Frage gehört zur Wahlstelle {stelle['id']} {stelle['titel']}."
                 + (" Als Bestimmer kannst du dort mit entscheiden entscheiden." if darf(wer["rolle"], "bestimmer") else ""))
    return " ".join(z), False


# ---------- Personen einladen (Paket C) ----------

def zugang_ausstellen(z):
    """Neuen geheimen Link anlegen -> Token. z: {"reise", "person"} oder {"reise", "rolle"}. Schreibt zugaenge.json
    (Rechte 600); der Dienst braucht dafür Schreibrecht auf den Ordner (ops/reisehandbuch-konnektor.service)."""
    p = zugaenge_pfad()
    with _sperre:
        p.parent.mkdir(parents=True, exist_ok=True)
        alle = zugaenge()
        token = secrets.token_urlsafe(24)
        alle[token] = {**z, "angelegt": datetime.date.today().isoformat()}
        rm.schreiben(p, json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
        os.chmod(p, 0o600)
    return token


def einladen(reise, d, wer, args):
    """person_einladen: Person mit Rolle anlegen und ihren Zugang ausstellen. Eine Person, die es schon gibt, bekommt
    einen weiteren Link (ihre Rolle ändert sich dabei nie: das ist eine Einstellung der Reise). -> (Text, ist_fehler)"""
    vorname = args.get("vorname")
    rolle = args.get("rolle") or "einbringer"
    notiz = args.get("notiz") or ""
    if not isinstance(vorname, str) or not isinstance(rolle, str) or not isinstance(notiz, str) \
            or not isinstance(args.get("schluessel") or "", str):
        return "Vorname, Rolle, Schlüssel und Notiz müssen Text sein.", True
    vorname, notiz = vorname.strip(), notiz.strip()
    if not vorname or "\n" in vorname or len(vorname) > rm.LAENGE["name"]:
        return "vorname fehlt (eine Zeile, höchstens 80 Zeichen): wen soll ich einladen?", True
    if len(notiz) > 300 or "\n" in notiz:
        return "Die Notiz passt in eine Zeile mit höchstens 300 Zeichen.", True
    if rolle not in ROLLEN:
        return f"Rolle muss eine von {', '.join(ROLLEN)} sein.", True
    name_von = wer["name"]
    if not name_von:
        return ("Einladen geht nur mit dem persönlichen Link: Der Link ohne Person kennt deinen Namen nicht. "
                "Bitte einen Bestimmer um einen persönlichen Link."), True
    if not os.environ.get("KN_BASIS"):
        return "Die Adresse für Links ist auf dem Server nicht eingerichtet (KN_BASIS). Das muss der Betreiber ergänzen.", True
    o = rm.ordner(reise)
    if o is None:
        return "Diese Reise nimmt noch keine Eingaben an.", True
    personen = personen_der_reise(reise, d)
    vorhanden = next((p for p in personen if p["name"].casefold() == vorname.casefold()
                      or p["schluessel"] == (args.get("schluessel") or "").strip()), None)
    if vorhanden:
        if args.get("rolle") and rolle != vorhanden["rolle"]:
            return (f"{vorhanden['name']} ist schon dabei, mit der Rolle {vorhanden['rolle']}. Die Rolle ändern ist eine "
                    "Einstellung der Reise: auftrag_geben (ziel reise)."), True
        rolle, neu = vorhanden["rolle"], False
        schluessel = vorhanden["schluessel"]
    else:
        schluessel = (args.get("schluessel") or "").strip() or schluessel_aus_name(vorname)
        if not PERSON_MUSTER.match(schluessel):
            return ("Aus dem Namen lässt sich kein Schlüssel bilden (klein, ohne Umlaute, Buchstaben und Ziffern). "
                    "Bitte schluessel angeben, z. B. „anna“."), True
        neu = True
    if neu and not darf(wer["rolle"], rolle):
        return (f"Du kannst höchstens eine Rolle vergeben, die du selbst hast (du: {wer['rolle']}, gewünscht: {rolle}). "
                "Für mehr Rechte muss ein Bestimmer einladen."), True
    if not neu and not darf(wer["rolle"], rolle):
        return f"Einen Link für {vorhanden['name']} (Rolle {rolle}) kann nur jemand mit mindestens dieser Rolle ausstellen.", True
    if neu:
        with _sperre:
            if len(rm.einladungen_lesen(o)) >= rm.MAX_EINLADUNGEN:
                return "Es sind schon sehr viele Einladungen offen; bitte zuerst einarbeiten lassen.", True
    try:
        token = zugang_ausstellen({"reise": reise, "person": schluessel})
    except OSError:
        return ("Der Link konnte nicht angelegt werden: Der Dienst darf die Zugänge nicht schreiben. Das muss der "
                "Betreiber einrichten (ops/README.md)."), True
    link = f"{basis()}/{token}"
    heute = datetime.date.today().isoformat()
    if neu:
        eintrag = {"name": vorname, "rolle": rolle, "reist": args.get("reist", True) is not False,
                   "notiz": notiz or f"eingeladen von {name_von} am {datum_de(heute)} über die Claude-App",
                   "eingeladen_von": name_von, "datum": heute}
        with _sperre:
            alle = rm.einladungen_lesen(o)
            alle[schluessel] = eintrag
            rm.schreiben(o / "einladungen.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
        text_ = (f"Einladung von {name_von}: {vorname} als {rolle} in reise.yaml unter personen aufnehmen, Schlüssel "
                 f"{schluessel}, reist: {'ja' if eintrag['reist'] else 'nein'}, notiz: „{eintrag['notiz']}“. "
                 "Zugang und Rolle gelten schon (einladungen.json); der Link ist ausgestellt.")
        auftrag_anlegen(reise, REISE_ZIEL, text_, {"einladung": {"schluessel": schluessel, **eintrag}}, name=name_von)
    z = [(f"{vorname} ist eingeladen" if neu else f"Neuer Link für {vorhanden['name']}") + f" (Rolle {rolle}). Der Link:",
         link, "",
         "Den Link nur an diese Person geben, am besten privat: Wer ihn kennt, spricht in der Reise als " + vorname + ". "
         "Sie trägt ihn in der Claude-App ein (Einstellungen → Konnektoren → Eigenen Konnektor hinzufügen, ohne Anmeldung); "
         "dafür braucht sie ein Claude-Konto, in dem eigene Konnektoren erlaubt sind.",
         {"reisend": "Mit der Rolle reisend kann sie nur lesen.",
          "einbringer": "Als Einbringer gibt sie Wünsche, Rückmeldungen, Aufgaben und Antworten; entscheiden kann sie nicht.",
          "bestimmer": "Als Bestimmer entscheidet sie mit, setzt Status und Einstellungen und lädt Personen ein."}[rolle]]
    if neu:
        z.append("Auf der Seite steht die Person, sobald eingearbeitet ist.")
    return "\n".join(z), False


def meldungen_fuer(reise, name, d):
    """Meldungen, die für diese Person noch gelten (nicht erledigt, nicht zu alt, Baustein waechter an)."""
    o = rm.ordner(reise)
    if o is None or not name:
        return []
    status, bausteine = zustand_von(d)
    return rm.meldungen_aktuell(o, name, rm.aufgaben(o), status, bausteine)


def liste_text(reise, mit_auftraegen, name=None, d=None):
    o = rm.ordner(reise)
    if o is None:
        return "Für diese Reise gibt es noch keine Rückmeldungen."
    es = rm.eintraege(o) + (rm.auftraege(o) if mit_auftraegen else [])
    es.sort(key=lambda e: e.get("erstellt", ""), reverse=True)
    z = []
    ms = meldungen_fuer(reise, name, d)[:10]
    if ms:
        z.append("## Meldungen an dich")
        z += [f"- {m['erstellt'][:10]} {m['art']} zu {m['ziel']}: {m['text']}" for m in ms]
        z.append("## Rückmeldungen")
    if not es:
        return "\n".join(z + ["Noch keine Rückmeldungen."])
    for e in es[:50]:
        z.append(f"- {e['id']} {e['erstellt'][:10]} {e.get('name')} [{e.get('art')} zu {e.get('ziel')}] "
                 f"Status: {e['status']}" + (f" – {e['kommentar']}" if e.get("kommentar") else ""))
        z.append("  " + e.get("text", "").replace("\n", " ")[:300])
    return "\n".join(z)


# ---------- MCP ----------

ZIEL_FELD = {"type": "string", "description": "ID, z. B. T-03, E-07, U-02, V-01.a, F-04, W-06 (aus ueberblick, suche oder zeige)"}

WERKZEUGE = [
    {"name": "ueberblick", "description": "Überblick über die Reise: Eckdaten, Tagesplan mit IDs, Anzahl offener Fragen, "
     "Wahlstellen und Inhaltsverzeichnis. Zuerst aufrufen.",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "zeige", "description": "Volltext zu einer ID: Tag (T-), Etappe/Strecke (E-), Ort (O-), Unterkunft (U-), "
     "Wahlstelle (V-) oder Option (V-01.a), Plan (P-), offene Frage (F-), Wissens-Abschnitt (W-, auch W-06.unterabschnitt).",
     "inputSchema": {"type": "object", "properties": {"id": ZIEL_FELD}, "required": ["id"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "suche", "description": "Volltextsuche im ganzen Reisehandbuch. Alle Wörter müssen vorkommen. Liefert IDs mit Ausschnitt.",
     "inputSchema": {"type": "object", "properties": {"begriff": {"type": "string"}}, "required": ["begriff"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "offene_fragen", "description": "Offene Fragen und To-dos (F-…) mit Frist und Status.",
     "inputSchema": {"type": "object", "properties": {"alle": {"type": "boolean", "description": "auch erledigte"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "varianten", "description": "Alle Alternativen: benannte Pläne (P-…) und Wahlstellen (V-…) mit Optionen, "
     "Status, Dafür/Dagegen und Summen.",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "rueckmeldungen", "description": "Bisherige Rückmeldungen mit Status (neu, übernommen, verworfen, Rückfrage) "
     "und Antwort; bei Bestimmern auch die Aufträge.",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "rueckmeldung_geben", "description": "Rückmeldung zu einer ID abgeben: Kommentar, Frage, Korrektur, Ergänzung "
     "oder Antwort (auf eine offene Frage F-…). Oder ein Wunsch: eine Idee für die Reise (Ort, Erlebnis, Essen), auch "
     "ohne passende ID; dann ziel leer lassen. Landet im Eingang und wird automatisch geprüft und "
     "eingearbeitet, in der Regel innerhalb einer Stunde; sie ändert nichts sofort. Vorher den Text mit der Person abstimmen.",
     "inputSchema": {"type": "object", "properties": {
         "ziel": {**ZIEL_FELD, "description": ZIEL_FELD["description"] + "; bei art Wunsch leer lassen"},
         "art": {"type": "string", "enum": sorted(rm.ARTEN)},
         "text": {"type": "string", "description": "in den Worten der Person, max. 4000 Zeichen"},
         "name": {"type": "string", "description": "Vorname der Person, die die Rückmeldung gibt. Wenn unbekannt: einmal fragen, "
                  "nicht raten. Gehört der Link zu einer Person, entfällt das."},
         "quelle": {"type": "string", "description": "woher die Angabe stammt (Link, Buch mit Seite), falls vorhanden"}},
         "required": ["art", "text"]}},
]
NAME_FELD = {"type": "string", "description": "Vorname der Person, die gerade spricht (für den Verlauf). Wenn unbekannt: "
             "einmal fragen, nicht raten. Gehört der Link zu einer Person, entfällt das."}
WERKZEUGE += [
    {"name": "merkmale", "description": "Welche Merkmale eine Alternative braucht (z. B. bei Unterkünften Preis, Frühstück, "
     "Öffnung), je mit Hinweis zum Recherchieren und zum gezielten Nachfragen; zu einer Wahlstelle auch, was jede Option "
     "schon hat und was fehlt. Vor alternative_vorschlagen aufrufen.",
     "inputSchema": {"type": "object", "properties": {
         "ziel": {"type": "string", "description": "Wahlstelle V-…, Option V-….a oder Unterkunft U-…"},
         "bereich": {"type": "string",
                     "description": "nur ohne ziel: Art der Alternative für die Liste (unterkunft, strecke, route, faehre, flug, "
                                    "bahn, bus, mietwagen, essen, erlebnis oder eine Art der Reise)"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "alternative_vorschlagen", "description": "Neue Alternative weitergeben (z. B. ein weiteres Hotel, eine andere "
     "Strecke, eine andere Route), mit Merkmalen nach der Liste aus merkmale. Erst selbst recherchieren, dann nur nach Lücken "
     "fragen, dann den Vorschlag kurz bestätigen lassen. Ändert nichts sofort: Er wird automatisch geprüft und als Option "
     "mit Status vorgeschlagen eingearbeitet, in der Regel innerhalb einer Stunde.",
     "inputSchema": {"type": "object", "properties": {
         "wahlstelle": {"type": "string", "description": "bestehende Wahlstelle V-…, zu der die Alternative gehört"},
         "an": {"type": "string", "description": "nur ohne wahlstelle: ID, an der eine neue Wahlstelle entsteht (T-…, U-…, E-…)"},
         "bereich": {"type": "string",
                     "description": "nur ohne wahlstelle: Art der Alternative (unterkunft, strecke, route, faehre, flug, bahn, "
                                    "bus, mietwagen, essen, erlebnis oder eine Art der Reise; Liste aus merkmale)"},
         "titel": {"type": "string", "description": "Name der Alternative, z. B. „Hotel Sa Plana“"},
         "merkmale": {"type": "object", "description": "{merkmal: {wert, quelle, geprueft (JJJJ-MM-TT), notiz}}; Schlüssel aus "
                      "merkmale. Eigene Kriterien der Person als neuer Schlüssel (z. B. pool) sind erlaubt.",
                      "additionalProperties": {"type": "object", "properties": {
                          "wert": {"type": "string"}, "quelle": {"type": "string"}, "geprueft": {"type": "string"},
                          "notiz": {"type": "string"}}, "required": ["wert"]}},
         "plus": {"type": "array", "items": {"type": "string"}, "description": "was dafür spricht"},
         "minus": {"type": "array", "items": {"type": "string"}, "description": "was dagegen spricht"},
         "text": {"type": "string", "description": "kurze Beschreibung"},
         "quelle": {"type": "string", "description": "woher die Alternative stammt (Link, Gespräch)"},
         "name": NAME_FELD}, "required": ["titel"]}},
]
AG_EIGENSCHAFTEN = {
    "titel": {"type": "string", "description": "kurz, was zu tun ist (max. 200 Zeichen)"},
    "bezug": {"type": "array", "items": {"type": "string"},
              "description": "IDs, an denen die Aufgabe hängt (z. B. [\"U-13\", \"T-07\"]); leer = allgemein"},
    "zustaendig": {"type": "string", "description": "Vorname der Person, die sich kümmert"},
    "prioritaet": {"type": "string", "enum": list(rm.AG_PRIO)},
    "ab": {"type": "string", "description": "frühester Termin JJJJ-MM-TT (z. B. Buchung öffnet), leer = sofort"},
    "frist": {"type": "string", "description": "erledigt sein bis JJJJ-MM-TT, leer = ohne Frist"},
    "notiz": {"type": "string", "description": "Details, Links, Kontakt (max. 2000 Zeichen)"},
}
WERKZEUGE += [
    {"name": "aufgaben", "description": "Aufgaben (AG-…) mit Status, Priorität, Frist, ab wann, Zuständig und Bezug. "
     "Standard: nur offene. Filter nach Bezug (z. B. U-13 oder T-07), Zuständig oder Status.",
     "inputSchema": {"type": "object", "properties": {
         "bezug": {"type": "string", "description": "nur Aufgaben an dieser ID"},
         "zustaendig": {"type": "string", "description": "nur Aufgaben dieser Person"},
         "status": {"type": "string", "enum": ["offen", "alle", *rm.AG_STATUS],
                    "description": "offen = offen und in Arbeit (Standard)"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "aufgabe_anlegen", "description": "Neue Aufgabe an einer oder mehreren IDs anlegen. Wirkt sofort (auch auf der "
     "Webseite). Vorher Titel, Frist und Zuständig mit der Person abstimmen; nichts erfinden.",
     "inputSchema": {"type": "object", "properties": {**AG_EIGENSCHAFTEN, "name": NAME_FELD}, "required": ["titel"]}},
    {"name": "aufgabe_aendern", "description": "Aufgabe ändern: abhaken (status erledigt), in Arbeit, entfällt, wieder offen, "
     "Frist/Zuständig/Priorität/Notiz ändern oder einen Kommentar in den Verlauf schreiben. Nur angegebene Felder ändern "
     "sich. Wirkt sofort. Gelöscht wird nie; nicht mehr Nötiges bekommt status entfaellt.",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string", "description": "AG-…"},
         "status": {"type": "string", "enum": list(rm.AG_STATUS)},
         **AG_EIGENSCHAFTEN,
         "kommentar": {"type": "string", "description": "kurze Notiz für den Verlauf, z. B. „gebucht, Bestätigung per Mail“"},
         "name": NAME_FELD}, "required": ["id"]}},
]
AUFTRAG = {"name": "auftrag_geben", "description": "Nur für Bestimmer: Änderungsauftrag ans Reisehandbuch, z. B. eine Option "
           "wählen oder verwerfen, eine offene Frage schließen, einen Tag ändern. Ändert NICHTS sofort: Der Auftrag wird "
           "automatisch geprüft (Quellen, Regeln) und in der Regel innerhalb einer Stunde übernommen; den Stand zeigt rueckmeldungen. Klar und vollständig "
           "formulieren, bei Entscheidungen auch den Grund.",
           "inputSchema": {"type": "object", "properties": {
               "ziel": {**ZIEL_FELD, "description": ZIEL_FELD["description"] + "; leer lassen, wenn es um mehreres geht"},
               "entscheidung": {"type": "string", "enum": list(ENTSCHEIDUNGEN),
                                "description": "nur wenn der Auftrag eine Entscheidung ist: gewaehlt, verworfen oder ersetzt "
                                "(ziel = die Option oder Wahlstelle, über die entschieden wird). Widerspricht sie der "
                                "Entscheidung eines anderen Bestimmers, wird daraus eine offene Frage; sonst leer lassen."},
               "auftrag": {"type": "string", "description": "was geändert werden soll, max. 4000 Zeichen"}},
               "required": ["auftrag"]}}


ENTSCHEIDEN = {"name": "entscheiden", "description": "Nur für Bestimmer: im Gespräch über eine Option einer Wahlstelle entscheiden "
               "(gewaehlt, verworfen oder ersetzt). Erst varianten/zeige ansehen und den Grund mit der Person klären, dann kurz "
               "bestätigen lassen. Der Dienst prüft sofort: Gibt es die Option, ist der Status stimmig, ist ein Grund da, "
               "widerspricht es einem anderen Bestimmer? Unstimmiges lehnt er mit Begründung ab, Hinweise (fehlende oder "
               "ungeprüfte Merkmale) gibt er mit. Auf dieser Reise gilt der Entscheidungsweg direkt (geprüft und mit Datum "
               "festgehalten, sofort gültig) oder auftrag (wird zusätzlich in Claude Code geprüft, bevor es gilt); die Antwort "
               "sagt, welcher. Auf die Seite kommt es mit dem nächsten Einarbeiten.",
               "inputSchema": {"type": "object", "properties": {
                   "option": {"type": "string", "description": "Option, über die entschieden wird, z. B. V-01.b (aus varianten)"},
                   "status": {"type": "string", "enum": list(ENTSCHEIDUNGEN),
                              "description": "gewaehlt = diese Option nehmen; verworfen = nicht nehmen; ersetzt = durch eine andere Option ersetzt"},
                   "grund": {"type": "string", "description": "Warum, in den Worten der Person, eine Zeile (kommt in den Verlauf)"},
                   "ersetzt_durch": {"type": "string", "description": "nur bei ersetzt: die andere Option derselben Wahlstelle"},
                   "quelle": {"type": "string", "description": "woran sich die Entscheidung stützt (Link, Gespräch), falls vorhanden"}},
                   "required": ["option", "status", "grund"]}}
FRAGE_BEANTWORTEN = {"name": "frage_beantworten", "description": "Eine offene Frage (F-…) beantworten. Die Antwort hängt an der Frage "
                     "(zeige F-… listet sie) und ist eine Eingabe: ob die Frage damit geklärt ist und was daraus folgt, "
                     "entscheidet ein Bestimmer. Vorher die Antwort mit der Person abstimmen; Herkunft nennen, Annahmen markieren.",
                     "inputSchema": {"type": "object", "properties": {
                         "frage": {"type": "string", "description": "F-… aus offene_fragen"},
                         "antwort": {"type": "string", "description": "die Antwort in den Worten der Person, max. 4000 Zeichen"},
                         "quelle": {"type": "string", "description": "woher die Angabe stammt (Link, Buch mit Seite), falls vorhanden"},
                         "name": NAME_FELD}, "required": ["frage", "antwort"]}}
PERSON_EINLADEN = {"name": "person_einladen", "description": "Eine Person zur Reise einladen: legt sie mit Rolle an und stellt ihren "
                   "persönlichen Link für die Claude-App aus (gilt sofort). Wer einladen darf, regelt die Reise "
                   "(regeln.einladen); man kann höchstens die eigene Rolle vergeben. Vorher Vorname und Rolle mit der Person "
                   "abstimmen und den Link danach nur an diese Person weitergeben lassen. Gibt es die Person schon, bekommt sie "
                   "einen weiteren Link; ihre Rolle ändert sich dabei nicht.",
                   "inputSchema": {"type": "object", "properties": {
                       "vorname": {"type": "string", "description": "Vorname der einzuladenden Person"},
                       "rolle": {"type": "string", "enum": list(ROLLEN),
                                 "description": "reisend liest; einbringer gibt Wünsche, Rückmeldungen, Aufgaben, Antworten; "
                                 "bestimmer entscheidet und lädt ein. Standard einbringer."},
                       "reist": {"type": "boolean", "description": "reist die Person mit? Standard ja (nein: gestaltet nur mit)"},
                       "notiz": {"type": "string", "description": "kurze Notiz zur Person, eine Zeile"},
                       "schluessel": {"type": "string", "description": "nur wenn nötig: Kurzname für den Zugang (klein, ohne Umlaute)"},
                       "name": NAME_FELD}, "required": ["vorname"]}}


STATUS_SATZ = {
    "idee": "Die Reise ist erst eine Idee: Eckdaten, Personen und Wünsche sammeln, kein Plan nötig, keine Warnungen.",
    "planung": "Alles ist offen; Lücken und offene Wahlstellen sind normaler Zwischenstand.",
    "fest": "Der Plan steht, das Buchen läuft: Offene Planungs-Wahlstellen und Aufgabenfristen mahnst du an.",
    "unterwegs": "Die Reise läuft: Heute und Wahlstellen mit Auslöser kommen zuerst; Rückmeldungen sind Notizen vom Weg.",
    "danach": "Die Reise ist vorbei: Der Plan ist schreibgeschützt, nur Rückmeldungen (Nachlese) und Aufgaben gehen noch.",
    "archiv": "Die Reise ist archiviert: Es kann nur gelesen werden.",
}


def anleitung(zugang, d):
    """Kurze Verfassung für die KI: Aufgabe, Grenzen, Rollen, Status. Was die Maschine prüft, steht nicht darin."""
    rs = (d or {}).get("reise", {})
    wer = wer_spricht(zugang, d) or {"rolle": "reisend", "name": None}
    bestimmer = bestimmer_namen(d)
    namen = " und ".join(bestimmer) or "Bestimmer"
    status = (rs.get("status") or {}).get("wert")
    bausteine = rs.get("bausteine")
    z = [f"Aufgabe: Du hilfst bei der Reise „{rs.get('titel', zugang['reise'])}“ ({rs.get('untertitel', '')})"
         + (f", Status {status}" if status else "") + ". Du liest vor, schlägst vor, prüfst und gibst Eingaben weiter; "
         f"{namen} {'entscheiden' if len(bestimmer) > 1 else 'entscheidet'}, du nie.",
         "Grenzen: Über den Konnektor ändert sich nichts sofort (Ausnahme Aufgaben AG-…); sag nie, etwas sei schon geändert. "
         "Status gewählt/verworfen/ersetzt und Einstellungen setzen nur Bestimmer. Nichts erfinden: Herkunft nennen, Annahmen "
         "markieren, veränderliche Angaben (Fahrpläne, Öffnungszeiten, Preise) mit Prüfdatum. Vor jedem Eintragen kurz "
         "bestätigen lassen, was genau eingetragen wird. Die Regeln prüft der Dienst; lehnt er etwas ab, gib den Grund weiter.",
         "IDs: T- Tag, E- Etappe/Strecke, O- Ort, U- Unterkunft, V- Wahlstelle mit Optionen V-01.a, P- Plan, F- offene Frage, "
         "W- Wissen, AG- Aufgabe. Mit ueberblick beginnen, dann zeige/suche; IDs in Antworten nennen.",
         "Rollen: reisend liest; einbringer gibt dazu Rückmeldungen, Antworten, Aufgaben und Vorschläge; bestimmer entscheidet "
         "dazu, setzt Status und Einstellungen und lädt ein."]
    name = f"Du sprichst mit {wer['name']}" if wer["name"] else "Du sprichst mit einer Person ohne festen Namen"
    regeln = rs.get("regeln") or {}
    weg = regeln.get("entscheidungsweg") or VORGABEN["entscheidungsweg"]
    einladen_ab = regeln.get("einladen") or VORGABEN["einladen"]
    kann_einladen = darf(wer["rolle"], einladen_ab)
    if wer["rolle"] == "bestimmer":
        z.append(f"{name} (Bestimmer). Entscheidungen über Optionen einer Wahlstelle trägst du mit entscheiden ein (Option, "
                 "Status, Grund; vorher kurz bestätigen lassen). "
                 + ("Auf dieser Reise gilt der Weg direkt: Der Dienst prüft im selben Moment, lehnt Unstimmiges mit Begründung ab "
                    "und hält die Entscheidung mit Datum fest; sie gilt dann, auf der Seite steht sie nach dem nächsten "
                    "Einarbeiten. " if weg == "direkt" else
                    "Auf dieser Reise gilt der Weg auftrag: Eine Entscheidung ist ein Auftrag und gilt erst, wenn sie in Claude "
                    "Code geprüft und eingearbeitet ist; sag nie, es sei schon entschieden. ")
                 + "Widerspricht sie der eines anderen Bestimmers, wird daraus eine offene Frage, und alle Beteiligten bekommen "
                 "eine Meldung. Andere Wünsche zu Änderungen gibst du mit auftrag_geben weiter. Personen lädst du mit "
                 "person_einladen ein (Rolle und Link gelten sofort). Fragen (F-…) kannst du mit frage_beantworten beantworten. "
                 "Den Stand zeigt rueckmeldungen.")
    elif wer["rolle"] == "einbringer":
        z.append(f"{name} (Einbringer). Ihre Hinweise sind Vorschläge, keine Entscheidungen: Entscheiden und Aufträge geben "
                 f"kann sie nicht, das bleibt bei {namen}. Offene Fragen beantwortet sie mit frage_beantworten. "
                 + ("Sie darf Personen einladen (person_einladen), höchstens mit der Rolle einbringer. " if kann_einladen else "")
                 + ("" if wer["name"] else "Für Rückmeldungen und Aufgaben brauchst du ihren Vornamen: einmal fragen, "
                    "nicht raten, dann im Gespräch beibehalten. ")
                 + "„Meine Aufgaben“ = aufgaben mit zustaendig = dieser Vorname.")
    else:
        z.append(f"{name} (Rolle reisend): nur lesen. Rückmeldungen, Antworten, Aufgaben und Vorschläge gehen mit diesem Zugang "
                 "nicht; wer mitgestalten will, bittet einen Bestimmer um eine andere Rolle."
)
    if status in STATUS_SATZ:
        z.append("Status: " + STATUS_SATZ[status])
    aus = [b for b in ("varianten", "fragen", "aufgaben", "rueckmeldungen", "wuensche") if bausteine is not None and b not in bausteine]
    if wer["name"] is None and wer["rolle"] != "reisend":
        z.append("Dieser Link gehört keiner Person: Entscheiden und Einladen gehen nur mit einem persönlichen Link.")
    if aus:
        z.append("Bei dieser Reise ausgeschaltet (Werkzeuge fehlen, Daten bleiben): " + ", ".join(aus) + ".")
    if bausteine is None or "varianten" in bausteine:
        z.append("Alternativen (eine weitere Unterkunft, Strecke, Route): erst merkmale aufrufen, die Merkmale selbst "
                 "recherchieren, dann gezielt nur nach Lücken fragen, dann mit alternative_vorschlagen weitergeben.")
    if bausteine is None or "waechter" in bausteine:
        z.append("Wächter und Erinnerer sind an: Meldungen an die Person (Fristen, ab-Termine, Statuswechsel, Prüfungen "
                 "veränderlicher Angaben) stehen im ueberblick unter „Meldungen an dich“. Nenne sie zu Beginn und frag, ob "
                 "etwas davon erledigt werden soll. Den Reisestatus wechselt nur ein Bestimmer, nie du.")
    if "wuensche" in (bausteine or []):
        z.append("Ideen und Wünsche für die Reise (ein Ort, ein Erlebnis, ein Essen, auch vage) hältst du mit "
                 "rueckmeldung_geben, art Wunsch, fest. Sie stehen auf der Seite im Reiter „Wünsche“. Ein Wunsch ist ein "
                 "Vorschlag, keine Entscheidung.")
    return " ".join(z)


def werkzeug(zugang, name, args):
    """-> (text, ist_fehler)"""
    reise = zugang["reise"]
    args = args if isinstance(args, dict) else {}
    wer = wer_spricht(zugang, daten(reise))
    if wer is None:
        return "Dieser Zugang gehört zu keiner Person der Reise (mehr). Einen Bestimmer um einen neuen Link bitten.", True
    bestimmer = darf(wer["rolle"], "bestimmer")
    d = daten(reise)
    # Regeln prüft die Maschine, bei jedem Aufruf (nicht nur beim Anzeigen der Werkzeuge): Rolle, Baustein, Status
    status, bausteine = zustand_von(d)
    if name in LESE_BAUSTEIN and bausteine is not None and LESE_BAUSTEIN[name] not in bausteine:
        return f"Der Baustein „{LESE_BAUSTEIN[name]}“ ist bei dieser Reise ausgeschaltet.", True
    aktion = SCHREIB_AKTION.get(name)
    if aktion == "rueckmeldung" and str(args.get("art")) == "Wunsch":
        aktion = "wunsch"
    if aktion and (nein := recht(wer["rolle"], d, aktion, str(args.get("ziel") or "").strip() or None)):
        return nein, True
    if name == "rueckmeldungen":
        return liste_text(reise, bestimmer, wer["name"], d), False
    if name == "rueckmeldung_geben":
        e = {k: args.get(k, "") for k in rm.INHALT}
        if wer["name"]:
            e["name"] = wer["name"]
        if not all(isinstance(v, str) for v in e.values()):
            return "Alle Angaben müssen Text sein.", True
        if not e["name"].strip():
            return "Name fehlt: bitte die Person nach ihrem Vornamen fragen.", True
        e["quelle"] = e["quelle"] or "über Claude"
        antwort, fehler = rueckmeldung_senden(reise, e)
        if fehler:
            return f"Nicht gespeichert: {fehler}", True
        return f"Gespeichert als {antwort['id']} (Status neu). Wird beim nächsten Einarbeiten geprüft.", False
    if name == "auftrag_geben":
        if not bestimmer:
            return "Aufträge können nur Bestimmer geben. Bitte rueckmeldung_geben nutzen.", True
        auftrag = args.get("auftrag", "")
        ziel = args.get("ziel", "")
        entscheidung = args.get("entscheidung") or ""
        if not isinstance(auftrag, str) or not isinstance(ziel, str) or not isinstance(entscheidung, str):
            return "Auftrag, ID und Entscheidung müssen Text sein.", True
        if entscheidung and entscheidung not in ENTSCHEIDUNGEN:
            return f"Entscheidung muss eine von {', '.join(ENTSCHEIDUNGEN)} sein (oder leer bleiben).", True
        if entscheidung and not ziel.strip():
            return "Eine Entscheidung braucht die ID, über die entschieden wird (ziel, z. B. V-01.b).", True
        e, fehler = auftrag_anlegen(reise, ziel, auftrag, {"entscheidung": entscheidung} if entscheidung else None,
                                    name=wer["name"] or "Bestimmer")
        if fehler:
            return f"Nicht gespeichert: {fehler}", True
        text_ = (f"Auftrag {e['id']} gespeichert. Er wird automatisch geprüft und in der Regel "
                 "innerhalb einer Stunde eingearbeitet, bis dahin bleibt das Reisehandbuch unverändert.")
        if entscheidung:
            k = konflikt_melden(reise, e, d)
            if k:
                text_ = (f"Auftrag {e['id']} gespeichert, aber er widerspricht einer anderen Entscheidung ({k}). "
                         "Nichts wird übernommen: Daraus wird eine offene Frage, und alle beteiligten Bestimmer bekommen eine "
                         "Meldung. Sag nie, etwas sei schon entschieden.")
        return text_, False

    d = daten(reise)
    if d is None:
        return "Die Seite dieser Reise ist noch nicht veröffentlicht.", True
    h = Handbuch(d, aufgaben_von(reise), offene_entscheidungen(reise), antworten_von(reise),
                 meldungen_fuer(reise, wer["name"], d))
    if name == "entscheiden":
        return entscheiden(reise, d, h, wer, args)
    if name == "frage_beantworten":
        return frage_beantworten(reise, d, h, wer, args)
    if name == "person_einladen":
        return einladen(reise, d, wer, args)
    if name == "aufgaben":
        liste = aufgaben_filter(h.aufgaben, args)
        return (rm.aufgaben_text(liste, h.titel(), h.v["fristen"]) if liste else "Keine passenden Aufgaben."), False
    if name in ("aufgabe_anlegen", "aufgabe_aendern"):
        roh = {k: args[k] for k in (*rm.AG_FELDER, "kommentar") if k in args}
        roh["name"] = wer["name"] or args.get("name", "")
        if not isinstance(roh["name"], str) or not roh["name"].strip():
            return "Name fehlt: bitte die Person nach ihrem Vornamen fragen.", True
        unbekannt = [b for b in (roh.get("bezug") or []) if isinstance(b, str) and b not in h.eintraege]
        if unbekannt:
            return f"Diese IDs gibt es nicht: {', '.join(unbekannt)}. Mit suche die richtige ID finden.", True
        if name == "aufgabe_anlegen":
            a, fehler = dienst_anfrage("POST", f"{reise}/aufgaben", roh)
        else:
            agid = str(args.get("id", "")).strip()
            if not rm.AG_MUSTER.match(agid):
                return "ID muss AG-… sein.", True
            a, fehler = dienst_anfrage("PATCH", f"{reise}/aufgaben/{agid}", roh)
        if fehler:
            return f"Nicht gespeichert: {fehler}", True
        return "Gespeichert (gilt sofort):\n" + aufgabe_text(a, h.titel()), False
    if name == "ueberblick":
        return h.ueberblick() + "\n" + stand_text(reise) + "\n" + einarbeiten_text(reise, bestimmer), False
    if name == "zeige":
        t, fehler = h.zeige(str(args.get("id", "")).strip())
        return (fehler, True) if fehler else (t, False)
    if name == "suche":
        begriff = str(args.get("begriff", "")).strip()
        return (h.suche(begriff), False) if begriff else ("Suchbegriff fehlt.", True)
    if name == "offene_fragen":
        return h.fragen(bool(args.get("alle"))), False
    if name == "varianten":
        return h.varianten(), False
    if name == "merkmale":
        t, fehler = h.merkmale(str(args.get("ziel") or "").strip(), str(args.get("bereich") or "").strip())
        return (fehler, True) if fehler else (t, False)
    if name == "alternative_vorschlagen":
        v, fehler = h.vorschlag(args)
        if fehler:
            return fehler, True
        text_, ziel, daten_ = v
        if bestimmer:
            e, fehler = auftrag_anlegen(reise, ziel, text_, daten_, name=wer["name"] or "Bestimmer")
        else:
            name_ = wer["name"] or args.get("name")
            if not isinstance(name_, str) or not name_.strip():
                return "Name fehlt: bitte die Person nach ihrem Vornamen fragen.", True
            e, fehler = rueckmeldung_senden(reise, {"name": name_, "art": "Ergänzung", "ziel": ziel,
                                                    "text": text_[:rm.LAENGE["text"]],
                                                    "quelle": str(args.get("quelle") or "über Claude")[:rm.LAENGE["quelle"]]})
        if fehler:
            return f"Nicht gespeichert: {fehler}", True
        return (f"Vorschlag {e['id']} gespeichert. Er wird automatisch geprüft und in der Regel innerhalb einer Stunde als "
                "Option (Status vorgeschlagen) eingearbeitet, bis dahin bleibt das Reisehandbuch unverändert.\n\n" + text_), False
    return f"Unbekanntes Werkzeug {name}.", True


def antwort_auf(zugang, nachricht):
    """Eine JSON-RPC-Nachricht -> Antwort-Objekt oder None (Benachrichtigung)."""
    if not isinstance(nachricht, dict) or nachricht.get("jsonrpc") != "2.0" or not isinstance(nachricht.get("method"), str):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "ungültige Anfrage"}}
    if "id" not in nachricht:
        return None
    nid, methode, p = nachricht["id"], nachricht["method"], nachricht.get("params") or {}

    def ok(ergebnis):
        return {"jsonrpc": "2.0", "id": nid, "result": ergebnis}

    if methode == "initialize":
        gewuenscht = p.get("protocolVersion") if isinstance(p, dict) else None
        rs = (daten(zugang["reise"]) or {}).get("reise", {})
        return ok({"protocolVersion": gewuenscht if gewuenscht in PROTOKOLLE else PROTOKOLLE[0],
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": f"reisehandbuch-{zugang['reise']}", "title": rs.get("titel", "Reisehandbuch"),
                                  "version": "1", **({"icons": ik} if (ik := symbole(zugang["reise"])) else {})},
                   "instructions": anleitung(zugang, daten(zugang["reise"]))})
    if methode == "ping":
        return ok({})
    if methode == "tools/list":
        d = daten(zugang["reise"])
        wer = wer_spricht(zugang, d) or {"rolle": "reisend"}
        _, bausteine = zustand_von(d)
        # Sichtbar ist, was diese Rolle bei diesem Status und diesen Bausteinen darf (aufgerufen wird trotzdem noch einmal geprüft)
        werkzeuge = []
        for w in WERKZEUGE + [AUFTRAG, ENTSCHEIDEN, FRAGE_BEANTWORTEN, PERSON_EINLADEN]:
            n = w["name"]
            if n in LESE_BAUSTEIN and bausteine is not None and LESE_BAUSTEIN[n] not in bausteine:
                continue
            if n in SCHREIB_AKTION:
                aktionen = ["rueckmeldung", "wunsch"] if n == "rueckmeldung_geben" else [SCHREIB_AKTION[n]]
                if not any(recht(wer["rolle"], d, a) is None for a in aktionen) and not (n == "auftrag_geben" and darf(wer["rolle"], "bestimmer")):
                    continue
                if n in ZUSATZ_AKTION and recht(wer["rolle"], d, ZUSATZ_AKTION[n]) is not None:
                    continue
            if n == "rueckmeldung_geben" and recht(wer["rolle"], d, "wunsch") is not None:
                art = {**w["inputSchema"]["properties"]["art"], "enum": [a for a in rm.ARTEN if a != "Wunsch"]}
                w = {**w, "inputSchema": {**w["inputSchema"], "properties": {**w["inputSchema"]["properties"], "art": art}}}
                w["inputSchema"]["properties"]["art"]["enum"].sort()
            werkzeuge.append(w)
        return ok({"tools": werkzeuge})
    if methode == "tools/call":
        t, fehler = werkzeug(zugang, p.get("name"), p.get("arguments"))
        return ok({"content": [{"type": "text", "text": t}], "isError": fehler})
    return {"jsonrpc": "2.0", "id": nid, "error": {"code": -32601, "message": f"unbekannt: {methode}"}}


def gesund():
    """-> (HTTP-Code, Antwort). Verrät weder Tokens noch Reisen."""
    try:
        reisen = {z.get("reise") for z in zugaenge().values()}
    except (OSError, ValueError, AttributeError):
        return 503, {"gesund": False}
    if not reisen or any(daten(r) is None for r in reisen):
        return 503, {"gesund": False}
    return 200, {"gesund": True}


class Dienst(BaseHTTPRequestHandler):
    server_version = "Reisehandbuch-Konnektor"
    sys_version = ""

    def _senden(self, code, obj=None, extra=None):
        body = b"" if obj is None else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        if obj is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _zugang(self):
        teile = self.path.split("?", 1)[0].strip("/").split("/")
        return zugang_zu(teile[0]) if len(teile) == 1 else None

    def do_GET(self):
        # Readiness für BetterStack ohne geheimen Link: Zugänge lesbar und jede verlinkte Reise veröffentlicht
        if self.path.split("?", 1)[0] == "/gesund":
            return self._senden(*gesund())
        # Kein SSE-Kanal: der Dienst schickt nie von sich aus etwas (Streamable HTTP erlaubt 405).
        if self._zugang() is None:
            return self._senden(404, {"fehler": "unbekannt"})
        self._senden(405, {"fehler": "nur POST"}, {"Allow": "POST"})

    do_DELETE = do_GET

    def do_POST(self):
        zugang = self._zugang()
        if zugang is None:
            return self._senden(404, {"fehler": "unbekannt"})
        try:
            laenge = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            laenge = 0
        if laenge <= 0 or laenge > MAX_BODY:
            return self._senden(413, {"fehler": "zu groß oder leer"})
        try:
            roh = json.loads(self.rfile.read(laenge).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._senden(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "kein JSON"}})
        if isinstance(roh, list):
            antworten = [a for a in (antwort_auf(zugang, n) for n in roh) if a is not None]
            return self._senden(200, antworten) if antworten else self._senden(202)
        a = antwort_auf(zugang, roh)
        return self._senden(200, a) if a is not None else self._senden(202)

    def log_message(self, fmt, *args):
        # Kein Token und keine Inhalte ins Protokoll
        sys.stderr.write(f"{self.command} {args[1] if len(args) > 1 else ''}\n")


def dienst():
    host = os.environ.get("KN_HOST", "127.0.0.1")
    port = int(os.environ.get("KN_PORT", "8772"))
    print(f"Konnektor auf {host}:{port}, Seiten {seiten()}, Zugänge {zugaenge_pfad()}", flush=True)
    ThreadingHTTPServer((host, port), Dienst).serve_forever()


def basis():
    return os.environ.get("KN_BASIS", "http://127.0.0.1:8772").rstrip("/")


def zugang_anlegen(reise, wen):
    """wen: Schlüssel einer Person aus reise.yaml (personen) oder eine Rolle ohne festen Namen."""
    if not rm.REISE_MUSTER.match(reise):
        sys.exit("Aufruf: zugang <reise> <person>|<rolle>")
    d = daten(reise)
    if d is None:
        sys.exit(f"Reise „{reise}“ ist unter {seiten()} nicht veröffentlicht (erst ops/deploy.sh {reise}).")
    personen = {p["schluessel"]: p for p in personen_der_reise(reise, d)}
    if wen in personen:
        z = {"reise": reise, "person": wen}
        wer = f"{personen[wen]['name']}, {personen[wen]['rolle']}"
    elif wen in ROLLEN:
        z = {"reise": reise, "rolle": wen}
        wer = f"{wen} ohne festen Namen"
    else:
        sys.exit(f"„{wen}“ ist weder eine Person der Reise ({', '.join(personen) or 'keine in reise.yaml'}) "
                 f"noch eine Rolle ({', '.join(ROLLEN)}).")
    token = zugang_ausstellen(z)
    print(f"{reise} ({wer}): {basis()}/{token}")


def zugaenge_zeigen():
    alle = zugaenge()
    if not alle:
        print("Keine Zugänge angelegt.")
    for t, z in alle.items():
        wer = z.get("person") or f"Rolle {z.get('rolle')}"
        print(f"{z.get('reise')} ({wer}, {z.get('angelegt', '?')}): {basis()}/{t}")


def main(a):
    if a[:1] == ["dienst"]:
        dienst()
    elif a[:1] == ["zugang"] and len(a) == 3:
        zugang_anlegen(a[1], a[2])
    elif a[:1] == ["zugaenge"]:
        zugaenge_zeigen()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
