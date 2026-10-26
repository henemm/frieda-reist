#!/usr/bin/env python3
"""Konnektor fürs Reisehandbuch: macht eine Reise in der Claude-App nutzbar (MCP über HTTP).

In der Claude-App (Einstellungen → Konnektoren → eigenen Konnektor hinzufügen) wird ein geheimer Link
eingetragen. Danach kann Claude im Chat die Reise lesen (Tagesplan, Etappen, Varianten, offene Fragen,
Wissen) und Rückmeldungen abgeben. Ein Link gehört zu genau einer Reise und einer Person aus reise.yaml
(personen); die Rolle der Person entscheidet, was geht (docs/produkt.md, 26.10.2026):

  reisend      lesen
  einbringer   dazu Rückmeldungen, Wünsche, Alternativen vorschlagen (landen im Eingang wie die von der Seite),
               Aufgaben (AG-…) anlegen, ändern, abhaken – wirkt sofort, auch auf der Webseite (24.10.2026)
  bestimmer    dazu Änderungsaufträge (24.10.2026: Ändern nur als Auftrag, Variante B; „direkt“ folgt
               mit Paket C). Aufträge ändern nichts sofort; sie liegen in <ablage>/<reise>/auftraege.jsonl und
               werden von Claude Code geprüft und übernommen, seit 25.10.2026 stündlich automatisch (ops/einarbeiten.sh).

Alte Links mit rolle mitreisend (vor dem 26.10.2026) gelten weiter als einbringer ohne festen Namen. Ein Link ohne Person (zugang <reise> einbringer) fragt nach dem Vornamen.

Gelesen wird die veröffentlichte Seite (<seiten>/<reise>/daten.json), also genau der Stand der Webseite.
Rückmeldungen gehen per HTTP an den Rückmeldedienst (ein Schreiber für eingang.jsonl), Aufträge schreibt
nur dieser Dienst.

Aufrufe:
  python3 engine/konnektor.py dienst                       Dienst starten
  python3 engine/konnektor.py zugang <reise> <person>|<rolle>      neuen geheimen Link anlegen (person aus reise.yaml)
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
from reise import ROLLEN, darf  # noqa: E402

ALTE_ROLLEN = {"mitreisend": "einbringer"}   # Links von vor dem 26.10.2026
PERSON_MUSTER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")
SCHREIB_WERKZEUGE = {"rueckmeldung_geben", "aufgabe_anlegen", "aufgabe_aendern", "alternative_vorschlagen"}
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


def wer_spricht(zugang, d):
    """Zugang + veröffentlichte Daten -> {"rolle", "name"} (name None: im Gespräch nach dem Vornamen fragen)
    oder None, wenn der Zugang zu keiner Person der Reise mehr gehört."""
    personen = ((d or {}).get("reise") or {}).get("personen") or []
    if zugang.get("person"):
        p = next((x for x in personen if x.get("schluessel") == zugang["person"]), None)
        return {"rolle": p["rolle"], "name": p["name"]} if p else None
    rolle = zugang.get("rolle")
    return {"rolle": ALTE_ROLLEN.get(rolle, rolle), "name": None}


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

    def __init__(self, d, aufgaben=None):
        self.d = d
        self.aufgaben = aufgaben
        self.r = d.get("route") or {}
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
        return "\n".join(z)

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
        if self.r.get("tage"):
            z.append("## Tagesplan (aktueller Stand)")
            teil = None
            for t in self.r["tage"]:
                if t.get("teil") and t["teil"] != teil:
                    teil = t["teil"]
                    z.append(f"### {teil}")
                z.append(f"- {t['id']} Tag {t['nr']}, {t['wochentag']} {datum_de(t['datum'])}: {t['titel']}"
                         + (f" – Nacht: {self.nacht(t.get('nacht'))}" if t.get("nacht") else ""))
        offen = self.offene()
        z.append(f"## Offene Fragen: {len(offen)} (Werkzeug offene_fragen)")
        if self.aufgaben is not None:
            offene_ag = [a for a in self.aufgaben if a["status"] in ("offen", "in_arbeit")]
            heute = datetime.date.today().isoformat()
            ueber = [a for a in offene_ag if a.get("frist") and a["frist"] < heute]
            z.append(f"## Offene Aufgaben: {len(offene_ag)}" + (f", davon {len(ueber)} überfällig" if ueber else "")
                     + " (Werkzeug aufgaben)")
            z += [f"- {a['id']} Frist {a['frist']}: {a['titel']}" for a in ueber]
        if self.r.get("wahlstellen"):
            z.append("## Wahlstellen (Werkzeug varianten)")
            z += [f"- {w['id']} {w['titel']}" + (" – offen" if w.get("offen") else "") for w in self.r["wahlstellen"]]
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
        dran = aufgaben_filter(self.aufgaben or [], {"bezug": id_, "status": "alle"})
        if dran:
            aus += "\n\n## Aufgaben hier\n" + rm.aufgaben_text(dran, self.titel())
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


def liste_text(reise, mit_auftraegen):
    o = rm.ordner(reise)
    if o is None:
        return "Für diese Reise gibt es noch keine Rückmeldungen."
    es = rm.eintraege(o) + (rm.auftraege(o) if mit_auftraegen else [])
    es.sort(key=lambda e: e.get("erstellt", ""), reverse=True)
    if not es:
        return "Noch keine Rückmeldungen."
    z = []
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
         "bereich": {"type": "string", "enum": ["unterkunft", "strecke", "route", "allgemein"],
                     "description": "nur ohne ziel: Liste für eine ganz neue Wahlstelle"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "alternative_vorschlagen", "description": "Neue Alternative weitergeben (z. B. ein weiteres Hotel, eine andere "
     "Strecke, eine andere Route), mit Merkmalen nach der Liste aus merkmale. Erst selbst recherchieren, dann nur nach Lücken "
     "fragen, dann den Vorschlag kurz bestätigen lassen. Ändert nichts sofort: Er wird automatisch geprüft und als Option "
     "mit Status vorgeschlagen eingearbeitet, in der Regel innerhalb einer Stunde.",
     "inputSchema": {"type": "object", "properties": {
         "wahlstelle": {"type": "string", "description": "bestehende Wahlstelle V-…, zu der die Alternative gehört"},
         "an": {"type": "string", "description": "nur ohne wahlstelle: ID, an der eine neue Wahlstelle entsteht (T-…, U-…, E-…)"},
         "bereich": {"type": "string", "enum": ["unterkunft", "strecke", "route", "allgemein"],
                     "description": "nur ohne wahlstelle"},
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
               "auftrag": {"type": "string", "description": "was geändert werden soll, max. 4000 Zeichen"}},
               "required": ["auftrag"]}}


def anleitung(zugang, d):
    rs = (d or {}).get("reise", {})
    wer = wer_spricht(zugang, d) or {"rolle": "reisend", "name": None}
    bestimmer = bestimmer_namen(d)
    wer_entscheidet = (" und ".join(bestimmer) + (" entscheiden" if len(bestimmer) > 1 else " entscheidet")) if bestimmer \
        else "Bestimmer entscheiden"
    status = (rs.get("status") or {}).get("wert")
    z = [f"Reisehandbuch „{rs.get('titel', zugang['reise'])}“ ({rs.get('untertitel', '')})"
         + (f", Status {status}" if status else "") + f". {wer_entscheidet}; "
         "Inhalte nennen ihre Herkunft, Annahmen sind markiert. Jede Stelle hat eine feste ID (T- Tag, E- Etappe/Strecke, "
         "O- Ort, U- Unterkunft, V- Wahlstelle mit Optionen V-01.a, P- Plan, F- offene Frage, W- Wissen). "
         "Mit ueberblick beginnen, dann zeige/suche. IDs in Antworten nennen.",
         "Am Reisehandbuch selbst wird über diesen Konnektor nichts direkt geändert. Status gewählt/verworfen setzen nur "
         f"{' und '.join(bestimmer) or 'Bestimmer'}. Ausnahme Aufgaben (AG-…): Einbringer und Bestimmer dürfen sie sofort "
         "anlegen, ändern und abhaken (aufgabe_anlegen, aufgabe_aendern); vorher kurz bestätigen lassen, was genau "
         "eingetragen wird. Veränderliche Angaben (Fahrpläne, Öffnungszeiten, Preise) haben ein Prüfdatum; darauf hinweisen."]
    name = f"Du sprichst mit {wer['name']}" if wer["name"] else "Du sprichst mit einer Person ohne festen Namen"
    if wer["rolle"] == "bestimmer":
        z.append(f"{name} (Bestimmer). Wünsche zu Änderungen oder Entscheidungen gibst du mit auftrag_geben weiter "
                 "(vorher kurz bestätigen lassen); sie werden automatisch geprüft und in der Regel innerhalb einer Stunde eingearbeitet, den Stand zeigt rueckmeldungen. Sag nie, etwas sei schon geändert.")
    elif wer["rolle"] == "einbringer":
        z.append(f"{name} (Einbringer). Ihre Hinweise sind Vorschläge, keine Entscheidungen. "
                 + ("" if wer["name"] else "Für rueckmeldung_geben und Aufgaben brauchst du ihren Vornamen: einmal fragen, "
                    "nicht raten, dann im Gespräch beibehalten. ")
                 + "„Meine Aufgaben“ = aufgaben mit zustaendig = dieser Vorname.")
    else:
        z.append(f"{name} (Rolle reisend): nur lesen. Rückmeldungen, Aufgaben und Vorschläge gehen mit diesem Zugang nicht; "
                 "wer mitgestalten will, bittet einen Bestimmer um einen eigenen Zugang.")
    z.append("Alternativen (eine weitere Unterkunft, Strecke, Route): erst merkmale aufrufen, die Merkmale selbst "
             "recherchieren, dann gezielt nur nach Lücken fragen (z. B. Preis, Frühstück), dann mit alternative_vorschlagen "
             "weitergeben; vorher kurz bestätigen lassen.")
    if "wuensche" in (rs.get("bausteine") or []):
        z.append("Ideen und Wünsche für die Reise (ein Ort, ein Erlebnis, ein Essen, auch vage) hältst du mit "
                 "rueckmeldung_geben, art Wunsch, fest; vorher kurz bestätigen lassen. Sie stehen auf der Seite im Reiter "
                 "„Wünsche“ und werden automatisch geprüft, in der Regel innerhalb einer Stunde. Ein Wunsch ist ein Vorschlag, keine Entscheidung.")
    return " ".join(z)


def werkzeug(zugang, name, args):
    """-> (text, ist_fehler)"""
    reise = zugang["reise"]
    args = args if isinstance(args, dict) else {}
    wer = wer_spricht(zugang, daten(reise))
    if wer is None:
        return "Dieser Zugang gehört zu keiner Person der Reise (mehr). Einen Bestimmer um einen neuen Link bitten.", True
    bestimmer = darf(wer["rolle"], "bestimmer")
    if name in SCHREIB_WERKZEUGE and not darf(wer["rolle"], "einbringer"):
        return "Mit diesem Zugang kann man nur lesen (Rolle reisend). Wer mitgestalten will, braucht einen Zugang als Einbringer.", True
    if name == "rueckmeldungen":
        return liste_text(reise, bestimmer), False
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
        if not isinstance(auftrag, str) or not isinstance(ziel, str):
            return "Auftrag und ID müssen Text sein.", True
        e, fehler = auftrag_anlegen(reise, ziel, auftrag, name=wer["name"] or "Bestimmer")
        if fehler:
            return f"Nicht gespeichert: {fehler}", True
        return (f"Auftrag {e['id']} gespeichert. Er wird automatisch geprüft und in der Regel "
                "innerhalb einer Stunde eingearbeitet, bis dahin bleibt das Reisehandbuch unverändert."), False

    d = daten(reise)
    if d is None:
        return "Die Seite dieser Reise ist noch nicht veröffentlicht.", True
    h = Handbuch(d, aufgaben_von(reise))
    if name == "aufgaben":
        liste = aufgaben_filter(h.aufgaben, args)
        return (rm.aufgaben_text(liste, h.titel()) if liste else "Keine passenden Aufgaben."), False
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
        wer = wer_spricht(zugang, daten(zugang["reise"])) or {"rolle": "reisend"}
        werkzeuge = [w for w in WERKZEUGE if darf(wer["rolle"], "einbringer") or w["name"] not in SCHREIB_WERKZEUGE]
        return ok({"tools": werkzeuge + ([AUFTRAG] if darf(wer["rolle"], "bestimmer") else [])})
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
    personen = {p["schluessel"]: p for p in (d.get("reise") or {}).get("personen") or []}
    if wen in personen:
        z = {"reise": reise, "person": wen}
        wer = f"{personen[wen]['name']}, {personen[wen]['rolle']}"
    elif wen in ROLLEN:
        z = {"reise": reise, "rolle": wen}
        wer = f"{wen} ohne festen Namen"
    else:
        sys.exit(f"„{wen}“ ist weder eine Person der Reise ({', '.join(personen) or 'keine in reise.yaml'}) "
                 f"noch eine Rolle ({', '.join(ROLLEN)}).")
    p = zugaenge_pfad()
    p.parent.mkdir(parents=True, exist_ok=True)
    alle = zugaenge()
    token = secrets.token_urlsafe(24)
    alle[token] = {**z, "angelegt": datetime.date.today().isoformat()}
    rm.schreiben(p, json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
    os.chmod(p, 0o600)
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
