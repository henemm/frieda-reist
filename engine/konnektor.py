#!/usr/bin/env python3
"""Konnektor für Frieda: macht eine Reise in der Claude-App nutzbar (MCP über HTTP).

In der Claude-App (Einstellungen → Konnektoren → eigenen Konnektor hinzufügen) wird ein geheimer Link
eingetragen. Danach kann Claude im Chat die Reise lesen (Tagesplan, Etappen, Varianten, offene Fragen,
Wissen) und Rückmeldungen abgeben. Ein Link gehört zu genau einer Reise und einer Person aus reise.yaml
(personen); die Rolle der Person entscheidet, was geht (docs/produkt.md, 26.10.2026):

  gast      lesen
  mitwirkend   dazu Rückmeldungen, Wünsche, Aufgaben (AG-…) und über den Schreibweg Werte, Dinge, Optionen, Wahlstellen,
               Fragen und Wissen (Eingaben, keine Entscheidungen); alles gilt sofort, auch auf der Webseite
  organisator    dazu Entscheidungen (entscheiden), Arten und Merkmale, Plan eines Tags, Status und Einstellungen der
               Reise, Einladungen (person_einladen). Seit 29.10.2026 (ADR-0001, Paket O-3) schreibt der Konnektor alles
               über den Schreibweg (engine/schreiben.py, Rollen- und Regelprüfung, Probebau) sofort ins Reisen-Repo;
               Änderungsaufträge (A-…, auftraege.jsonl) und der Einarbeiten-Lauf mit Claude Code sind entfallen.
  Paket C (26.10.2026): Mitwirkende beantworten Fragen (frage_beantworten); einladen darf, wer regeln.einladen
               erlaubt (Vorgabe: Organisator:innen); person_einladen legt die Person an und stellt ihren Zugang aus.

Paket H (27.10.2026): Ein Konto-Link gehört zu einer Person, nicht zu einer Reise („Frieda – meine Reisen“). Er zeigt die
eigenen Reisen (meine_reisen) und legt neue an (reise_anlegen); Anfragen und Meldungen liegen in <ablage>/_neu/.

Alte Links mit rolle mitreisend (vor dem 26.10.2026) gelten weiter als mitwirkend ohne festen Namen. Ein Link ohne Person (zugang <reise> mitwirkend) fragt nach dem Vornamen.

Gelesen wird die veröffentlichte Seite (<seiten>/<reise>/daten.json), also genau der Stand der Webseite.
Rückmeldungen gehen per HTTP an den Rückmeldedienst (ein Schreiber für eingang.jsonl), Aufträge schreibt
nur dieser Dienst.

Aufrufe:
  python3 engine/konnektor.py dienst                       Dienst starten
  python3 engine/konnektor.py zugang <reise> <person>|<rolle>      neuen geheimen Link anlegen (person aus reise.yaml
                                                           oder eingeladen; in der App geht das mit person_einladen)
  python3 engine/konnektor.py konto <schluessel> <Name>    persönlichen Konto-Link anlegen (meine Reisen, neue Reise)
  python3 engine/konnektor.py zugaenge                     angelegte Links zeigen
        Umgebung: KN_SEITEN, KN_ZUGAENGE (Standard aus engine/instanz.py: <Seiten>/_konnektor/zugaenge.json),
                  KN_RUECKMELDEDIENST (http://127.0.0.1:8771), KN_HOST (127.0.0.1), KN_PORT (8772),
                  KN_BASIS (öffentliche Adresse des Dienstes, für die Links), RM_ABLAGE wie beim Rückmeldedienst,
                  KN_SEITENLINKS (Links zu den Seiten je Reise, vom Betrieb geschrieben; Standard seiten.json neben
                  KN_ZUGAENGE)

HTTP (hinter nginx, Präfix /<instanz>-mcp/ -> /, docs/betrieb.md):
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
import anmeldung  # noqa: E402
import instanz  # noqa: E402
import konten  # noqa: E402
import oauth  # noqa: E402
import belege as bl  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
from reise import (ENTSCHEIDUNGEN, LESE_BAUSTEIN, REISE_ZIEL, ROLLEN, VORGABEN, darf, erlaubt,  # noqa: E402
                   konflikte, neue_reise_pruefen, rolle_neu, schluessel_aus_name, verhalten)
from routen import FARBEN, GRUNDFORMEN, STUFEN, TYPEN, art_schluessel, stufe_gilt, stufe_schluessel, stufe_wort  # noqa: E402  (Form der Ontologie, docs/ontologie.md)

PERSON_MUSTER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")
SCHREIB_WERKZEUGE = {"rueckmeldung_geben", "aufgabe_anlegen", "aufgabe_aendern", "rueckmeldung_erledigen",
                     "frage_beantworten", "entscheiden", "person_einladen", "person_entfernen", "wunsch_aendern"}
# Werkzeuge, die direkt in die Ontologie der Reise schreiben (ADR-0001, O-3; engine/schreiben.py): nur bei Instanzen mit
# Schreibweg (KN_SCHREIBDIENST); Organisator:innen schreiben, Mitwirkende schlagen vor (Rückmeldung der Art Ergänzung)
ONTOLOGIE_WERKZEUGE = ("art_definieren", "merkmal_definieren", "kategorie_definieren", "wert_eintragen", "ding_anlegen", "ding_aendern", "lage_eintragen",
                       "option_anlegen", "wahlstelle_anlegen", "frage_anlegen", "tag_aendern", "wissen_schreiben", "frage_schliessen",
                       "reise_status_setzen", "einstellung_setzen", "buchung_anlegen", "buchung_aendern")
# Aktion der Regelprüfung je Werkzeug; art_definieren und merkmal_definieren gehen für Mitwirkende als Rückmeldung (Vorschlag)
ONTOLOGIE_AKTION = {"art_definieren": "ontologie", "merkmal_definieren": "ontologie", "kategorie_definieren": "ontologie", "wert_eintragen": "wert",
                    "ding_anlegen": "ding", "ding_aendern": "ding", "lage_eintragen": "ding", "option_anlegen": "alternative",
                    "wahlstelle_anlegen": "alternative", "frage_anlegen": "frage", "tag_aendern": "plan", "wissen_schreiben": "wissen",
                    "frage_schliessen": "frage_schliessen", "reise_status_setzen": "einstellung", "einstellung_setzen": "einstellung",
                    "buchung_anlegen": "buchung", "buchung_aendern": "buchung"}
# Werkzeug -> Aktion der Regelprüfung (reise.AKTIONEN); rueckmeldung_geben mit Art Wunsch ist die Aktion „wunsch“
SCHREIB_AKTION = {"rueckmeldung_geben": "rueckmeldung", "aufgabe_anlegen": "aufgabe", "aufgabe_aendern": "aufgabe",
                  "entscheiden": "entscheiden", "rueckmeldung_erledigen": "rueckmeldung_erledigen",
                  "frage_beantworten": "antwort", "person_einladen": "einladen", "person_entfernen": "entfernen",
                  # Wunsch-Brett: sichtbar für alle, die abhaken dürfen; Punkte und Einplanen prüft der Dienst genauer
                  "wunsch_aendern": "wunsch_erlebt"}
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

CODE_DATEIEN = ("konnektor.py", "reise.py", "rueckmeldungen.py", "routen.py")


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
    return instanz.seiten()


def zugaenge_pfad():
    return instanz.zugaenge()


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
            if isinstance(z, dict) and "konto" in z:
                ok = isinstance(z["konto"], str) and PERSON_MUSTER.match(z["konto"]) and isinstance(z.get("name"), str) \
                    and z["name"].strip() and "reise" not in z
                return z if ok else None
            if not isinstance(z, dict) or not rm.REISE_MUSTER.match(z.get("reise", "")):
                return None
            if isinstance(z.get("person"), str) and PERSON_MUSTER.match(z["person"]):
                return z
            return z if rolle_neu(z.get("rolle")) in ROLLEN else None
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
        return {"rolle": rolle_neu(p["rolle"]), "name": p["name"]} if p else None
    rolle = zugang.get("rolle")
    return {"rolle": rolle_neu(rolle), "name": None}


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


def organisator_namen(d):
    return [p["name"] for p in ((d or {}).get("reise") or {}).get("personen") or [] if rolle_neu(p.get("rolle")) == "organisator"]


# ---------- Seite lesen und in Text verwandeln ----------

class Text(HTMLParser):
    """HTML der Seite -> schlichter Text (Absätze, Listen, Merkmallisten als „- Merkmal: Wert“, Tabellenzeilen mit |,
    Links als [Text](URL))."""
    BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "br", "blockquote", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.teile, self.link, self.zelle, self.dl = [], None, False, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "dl":
            self.dl = True
        if (tag in self.BLOCK and not (tag == "div" and self.dl)) or tag == "tr":   # Zeilen einer Merkmalliste ohne Leerzeile
            self.teile.append("\n")
        if tag in ("li", "dt"):
            self.teile.append("\n- ")
        elif tag == "dd":
            self.teile.append(": ")
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
        elif tag == "dl":
            self.dl = False
            self.teile.append("\n")
        elif tag in self.BLOCK and not (tag == "div" and self.dl):
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


# Friedas Symbol (Wegweiser, engine/marke/): Favicon und App-Symbol unter Friedas Adresse, Icons für serverInfo
MARKE = Path(__file__).resolve().parent / "marke"
MARKE_DATEIEN = {"/favicon.ico": ("favicon.ico", "image/x-icon"), "/favicon.svg": ("frieda.svg", "image/svg+xml"),
                 "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
                 "/icon-192.png": ("icon-192.png", "image/png"), "/icon-512.png": ("icon-512.png", "image/png")}


def frieda_symbole():
    """Friedas Symbol als MCP-Icons (serverInfo.icons, MCP 2025-11-25). Mit Friedas Adresse als HTTPS-Links, wie der
    Standard es vorsieht (Data-URIs lehnen manche Clients ab); ohne Adresse als Data-URIs; fehlen die Dateien: keine.
    claude.ai zeigt bei eigenen Konnektoren bisher das Google-Favicon der Hauptdomain statt dieser Icons
    (anthropics/claude-ai-mcp#152, offen, Stand 28.10.2026)."""
    b = oauth.basis()
    if b and (MARKE / "icon-192.png").exists():
        return [{"src": f"{b}/icon-192.png", "mimeType": "image/png", "sizes": ["192x192"]},
                {"src": f"{b}/icon-512.png", "mimeType": "image/png", "sizes": ["512x512"]},
                {"src": f"{b}/favicon.svg", "mimeType": "image/svg+xml", "sizes": ["any"]}]
    liste = []
    for g in (32, 192):
        try:
            roh = (MARKE / f"icon-{g}.png").read_bytes()
        except OSError:
            continue
        liste.append({"src": "data:image/png;base64," + base64.b64encode(roh).decode("ascii"),
                      "mimeType": "image/png", "sizes": [f"{g}x{g}"]})
    return liste


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
             + ("" if jetzt == _CODE_START else f" – auf dem Server liegt neuerer Code ({jetzt}), der Dienst braucht einen Neustart"))
    return "\n".join(z)


# Doppelte Merkmale erkennen (Paket 3, #18): Ein neuer Schlüssel aus einem Vorschlag, der einem bestehenden Merkmal der
# Art entspricht (z. B. „oeffnung“ neben „geoeffnet“), soll zusammengeführt statt neu angelegt werden. Nur generisch
# (Schreibweise, Wortstamm) und über die Zweitnamen „auch“, die die Reise in arten.yaml angibt; keine Wortliste in der
# Software (ADR-0001: kein Katalog).


def regel_stand(x):
    """Stand einer Option, auf die eine Regel zeigt (erfordert, schliesst_aus)."""
    return "verworfen" if not x.get("gueltig", True) else "im Plan" if x.get("im_plan") else "nicht im Plan"


def merkmal_norm(s):
    s = str(s).lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", s)


def gemeinsam(a, b):
    """Länge des längsten gemeinsamen Teilstücks zweier Wörter."""
    best = 0
    for i in range(len(a)):
        for j in range(i + best + 1, len(a) + 1):
            if a[i:j] in b:
                best = j - i
            else:
                break
    return best


def aehnliches_merkmal(schluessel, kriterien):
    """Bestehendes Merkmal (Definition) zu einem neuen Schlüssel, wenn es vermutlich dasselbe meint, sonst None:
    gleich nach Umlauten und Zeichen, ein Zweitname der Reise (auch) oder ein gemeinsamer Wortstamm von mindestens 5 Zeichen."""
    k = merkmal_norm(schluessel)
    for d in kriterien or []:
        for name in (d["id"], d.get("name", ""), *(d.get("auch") or [])):
            n = merkmal_norm(name)
            if not n:
                continue
            if k == n or gemeinsam(k, n) >= 5:
                return d
    return None


def stunden(minuten):
    return f"{minuten // 60}:{minuten % 60:02d} h" if minuten else ""


def datum_de(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day}.{d.month}.{d.year}"


class Handbuch:
    """Alles, was eine Reise-Seite zeigt, nach ID nachschlagbar."""

    def __init__(self, d, aufgaben=None, offene_entscheidungen=None, antworten=None, meldungen=None, belege=None):
        self.d = d
        self.aufgaben = aufgaben
        self.belege = belege or {}       # B-ID -> Belege aus der Ablage (Rückmeldedienst), soweit die Person sie sehen darf
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

    def buchung_text(self, b):
        """Eine Buchung (B-…, #76) für die Claude-App: Dinge, Status, Nummer, Anbieter, Preis, Frist, Storno, Herkunft, Belege, Verlauf."""
        z = ["Für: " + "; ".join(f"{x} {self.titel_von(x)}" for x in b.get("fuer") or []), f"Status: {b.get('status')}"]
        for k, name in (("nummer", "Nummer: "), ("bei", "Gebucht bei: "), ("preis", "Preis: "), ("bezahlt", "Bezahlt: ")):
            if b.get(k):
                z.append(name + str(b[k]))
        if b.get("frist"):
            z.append(f"Frist {datum_de(b['frist'])}" + (f": {b['frist_was']}" if b.get("frist_was") else ""))
        if b.get("storno") or b.get("storno_bis"):
            z.append("Storno: " + (b.get("storno") or "") + (f" (bis {datum_de(b['storno_bis'])})" if b.get("storno_bis") else ""))
        if b.get("gebucht_am") or b.get("wer"):
            z.append("Gebucht " + (f"am {datum_de(b['gebucht_am'])} " if b.get("gebucht_am") else "") + (f"von {b['wer']}" if b.get("wer") else ""))
        if b.get("notiz"):
            z.append(b["notiz"])
        if b.get("quelle"):
            z.append("Quelle: " + str(b["quelle"]))
        belege = (self.belege or {}).get(b.get("id")) or []
        z.append("Belege: " + ("; ".join(f"{x.get('name')} ({x.get('wer')}, {str(x.get('hochgeladen', ''))[:10]}"
                                          + (", für alle sichtbar" if x.get("sichtbar") == "alle" else "") + ")" for x in belege)
                               if belege else "keine (die Person hängt sie auf der Reiseseite bei der Buchung an)"))
        if b.get("verlauf"):
            z.append("Verlauf: " + "; ".join(f"{datum_de(v['datum'])} {v.get('wer')}: {v.get('was')}" + (f" ({v['grund']})" if v.get("grund") else "")
                                             for v in b["verlauf"] if v.get("datum")))
        return "\n".join(z)

    def titel_von(self, x):
        r = self.r
        d = (r.get("unterkuenfte") or {}).get(x) or (r.get("aufenthalte") or {}).get(x)
        return (d or {}).get("name") or ((r.get("strecken") or {}).get(x) or {}).get("titel") or ""

    def aufenthalt(self, aid):
        """Aufenthalt ohne Nacht (A-…): Name, Art, Zeit, Buchungsstand."""
        a = (self.r.get("aufenthalte") or {}).get(aid) or {}
        art = ((self.r.get("arten") or {}).get(a.get("art")) or {}).get("name") or a.get("art") or ""
        return ", ".join(x for x in [f"{a.get('name', aid)} ({aid})", art, a.get("zeit"), f"Buchung: {a['buchung']}" if a.get("buchung") else ""] if x)

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
        if t.get("aufenthalte"):
            z.append("Aufenthalte: " + "; ".join(self.aufenthalt(a) for a in t["aufenthalte"]))
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
        if id_ in (self.r.get("aufenthalte") or {}):   # Aufenthalt ohne Nacht (A-…): Zeile wie im Tag, dann Merkmale
            a = self.r["aufenthalte"][id_]
            z = [self.aufenthalt(id_), "in " + self.ort(a.get("ort")), *( [a["hinweis"]] if a.get("hinweis") else []),
                 *( ["an: " + ", ".join(a["tage"])] if a.get("tage") else []), *( ["Quelle: " + a["quelle"]] if a.get("quelle") else [])]
            z += self.merkmal_zeilen((self.r.get("merkmale") or {}).get(a.get("art")), a.get("merkmale"), a.get("fehlt"))
            return "\n".join(z)
        if id_ in (self.r.get("unterkuenfte") or {}):   # Aufenthalt: Merkmale seiner Art (plan/arten.yaml)
            b = self.r["unterkuenfte"][id_].get("art")
            return None, b, (self.r.get("merkmale") or {}).get(b) or []
        st = (self.r.get("strecken") or {}).get(id_)
        if st is not None:   # Bewegung: Merkmale ihrer Art
            b = st.get("bereich")
            return None, b, (self.r.get("merkmale") or {}).get(b) or []
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
        for k, name in (("erfordert", "Setzt voraus"), ("schliesst_aus", "Schließt aus")):
            if o.get(k):
                z.append(f"{name}: " + "; ".join(f"{x['id']} „{x['titel']}“ ({regel_stand(x)})" for x in o[k]))
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
            if s.get("merkmale") or s.get("fehlt"):
                z.append("Merkmale:")
                z += self.merkmal_zeilen((r.get("merkmale") or {}).get(s.get("bereich")), s.get("merkmale"), s.get("fehlt"))
            z += self.lesetext_zeilen(s)
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
                    z.append(name + str(u[k]) + (f" ({u['buchung_id']}, zeige {u['buchung_id']})" if k == "buchung" and u.get("buchung_id") else ""))
            # Lage (ADR-0004): Adresse und Koordinaten mit Herkunft; fehlt beides, trägt lage_eintragen sie nach
            for k, name in (("adresse", "Adresse: "), ("punkt", "Koordinaten: ")):
                v = u.get(k)
                if v:
                    w = ", ".join(map(str, v["wert"])) if k == "punkt" else v["wert"]
                    z.append(f"{name}{w} ({v.get('quelle') or 'ohne Quelle'}{', geprüft ' + v['geprueft'] if v.get('geprueft') else ''})")
            if not u.get("adresse") and not u.get("punkt"):
                z.append("Lage: fehlt (lage_eintragen)")
            if u.get("naechte"):
                z.append("Nächte: " + ", ".join(u["naechte"]))
            if u.get("merkmale") or u.get("fehlt"):
                z.append("Merkmale:")
                z += self.merkmal_zeilen((r.get("merkmale") or {}).get(u.get("art")), u.get("merkmale"), u.get("fehlt"))
            e[uid] = (u.get("name") or uid, "\n".join(z))
        for bid, b in (r.get("buchungen") or {}).items():   # Buchung als eigenes Ding (#76)
            e[bid] = (f"Buchung {b.get('status')}: {b.get('titel') or bid}", self.buchung_text(b))
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
        if self.r.get("buchungen"):
            bs = list(self.r["buchungen"].values())
            gezaehlt = {s: len([b for b in bs if b.get("status") == s]) for s in ("gebucht", "angefragt", "storniert")}
            z.append("## Buchungen: " + ", ".join(f"{n} {s}" for s, n in gezaehlt.items() if n) + " (zeige B-…)")
            heute = datetime.date.today().isoformat()
            fristen = sorted((b for b in bs if b.get("status") != "storniert" and (b.get("frist") or b.get("storno_bis"))),
                             key=lambda b: min(x for x in (b.get("frist"), b.get("storno_bis")) if x))[:5]
            z += [f"- {b['id']} {b.get('titel')}: " + ", ".join(x for x in (
                f"Frist {datum_de(b['frist'])}" + (f" ({b['frist_was']})" if b.get("frist_was") else "") + (" überfällig" if b["frist"] < heute else "") if b.get("frist") else "",
                f"kostenlos stornierbar bis {datum_de(b['storno_bis'])}" if b.get("storno_bis") else "") if x) for b in fristen]
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

    def lesetext_zeilen(self, s):
        """Gliederung des Lesetexts der Art einer Strecke (plan/arten.yaml lesetext, docs/ontologie.md) als Anleitung für
        den AI-Client: Rubriken in ihrer Reihenfolge, jede als Absatz mit fettem Stichwort."""
        art = s.get("bereich") or s.get("art") or "wandern"
        rubriken = (((self.r.get("arten") or {}).get(art if isinstance(art, str) else "kombiniert")) or {}).get("lesetext")
        if not rubriken:
            return []
        return ["Gliederung des Lesetexts (Abschnitt Zusammenfassung; je Rubrik ein Absatz, der mit dem fetten Stichwort "
                "beginnt, z. B. „**" + rubriken[0]["name"] + ".** …“; Rubriken ohne Inhalt weglassen; Herkunft nennen):"] + [
            f"- {x['name']}" + (f": {x['hilfe']}" if x.get("hilfe") else "") for x in rubriken]

    def merkmale(self, ziel, bereich):
        """Welche Merkmale eine Alternative braucht, was schon da ist und was fehlt (Werkzeug merkmale)."""
        katalog = self.r.get("merkmale") or {}
        if ziel:
            w, b, krit = self.kriterien_von(ziel)
            if krit is None:
                return None, "Zu dieser ID gibt es keine Merkmale. Erlaubt: Wahlstelle V-…, Option V-….a, Unterkunft U-… oder Strecke E-…."
        elif bereich in katalog:
            w, b, krit = None, bereich, katalog[bereich]
        else:
            return None, f"ziel (V-…, U-…, E-…) oder bereich angeben: eine Art dieser Reise ({', '.join(katalog) or 'keine definiert'})."
        z = [f"# Merkmale für Bereich {b}" + (f" – {w['id']} {w['titel']}" if w else f" – {ziel}" if ziel else ""),
             "Vorgehen: Erst selbst recherchieren (Hinweis „so finden“), dann die Person nur nach dem fragen, was offen "
             "bleibt (Hinweis „fragen“). Veränderliche Werte mit Prüfdatum. Werte an einer vorhandenen Stelle trägst du mit "
             "wert_eintragen ein (sofort, mit Herkunft); eine neue Alternative: ding_anlegen (Unterkunft, Strecke) und option_anlegen an der Wahlstelle, vorher kurz bestätigen lassen. Ist ein Wert je Datum verschieden (z. B. "
             "Preis je Nacht), mehrere Werte mit gilt (JJJJ-MM-TT) angeben; einer ohne gilt steht für alle übrigen Tage. "
             "Das sind die Merkmale dieser Reise für diese Art (plan/arten.yaml, von den Reisenden festgelegt). Ein neues "
             "Merkmal nur, wenn es hier nichts Passendes gibt; dann wird es an der Art der Reise definiert (merkmal_definieren: "
             "Organisator:innen legen fest, Mitwirkende schlagen vor).",
             "## Liste"]
        for k in krit:
            st = k.get("stufe", "empfohlen")   # Stufe je Reise (routen.yaml merkmale: {…: {stufe: …}}); je Unterkunftstyp als Objekt
            if not stufe_gilt(st):   # gilt für diese Reise nicht (aus, auch je Typ überall aus): bleibt unsichtbar
                continue
            art = k.get("typ", "text") + (f" ({' | '.join(k['werte'])})" if k.get("werte") else "")
            zeile = f"- {k['id']} – {k['name']}: {art}"
            # Stufen für Menschen: nötig, gut zu wissen, zusätzlich (Product Owner 29.10.2026); Schlüssel in Klammern
            if isinstance(st, dict):
                zeile += "; Stufe je Unterkunftstyp: " + stufe_wort(st)
            elif st == "pflicht":
                zeile += "; nötig (pflicht): ohne Wert eine Lücke"
            elif st == "angeboten":
                zeile += "; zusätzlich (angeboten): nur eintragen, wenn es die Person interessiert, fehlt sonst nicht"
            else:
                zeile += "; gut zu wissen (empfohlen): ohne Wert keine Mahnung"
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
        elif ziel in (self.r.get("unterkuenfte") or {}):
            u = self.r["unterkuenfte"][ziel]
            z.append(f"## {ziel} {u.get('name')}")
            z += self.merkmal_zeilen(krit, u.get("merkmale"), u.get("fehlt")) or ["(keine Merkmale)"]
        elif ziel:
            s = self.r["strecken"][ziel]
            z.append(f"## {ziel} {s.get('titel') or ziel}")
            z += self.merkmal_zeilen(krit, s.get("merkmale"), s.get("fehlt")) or ["(keine Merkmale)"]
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
        Hinweise mit, die die Person wissen soll, die aber nichts verhindern. Widersprüche zwischen Organisator:innen prüft
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
                                + ". Recherchieren und mit wert_eintragen (Herkunft, Prüfdatum) nachtragen.")
            offen = [namen.get(k, k) for k, v in (o.get("merkmale") or {}).items() if v.get("ungeprueft")]
            if offen:
                hinweise.append("Ungeprüfte veränderliche Angaben: " + ", ".join(offen) + " – vor dem Buchen nachschlagen.")
            # Quellen prüfen: geprüft, aber älter als die Frist des Wächters (regeln.waechter_frist_tage)
            frist = ((self.d.get("reise") or {}).get("regeln") or {}).get("waechter_frist_tage", VORGABEN["waechter_frist_tage"])
            veraenderlich = {k["id"] for k in w.get("kriterien") or [] if k.get("veraenderlich")}
            stichtag = heute or datetime.date.today()
            alt = []
            for k, v in (o.get("merkmale") or {}).items():
                for e in [v] + list(v.get("je_datum") or []):
                    g = e.get("geprueft")
                    if k in veraenderlich and g and (stichtag - datetime.date.fromisoformat(g)).days > frist:
                        alt.append(f"{namen.get(k, k)} (geprüft {datum_de(g)}, Quelle {e.get('quelle') or 'unbekannt'})")
            if alt:
                hinweise.append(f"Älter als {frist} Tage: " + ", ".join(alt) + " – vor dem Buchen neu nachschlagen.")
        # Regeln zwischen Optionen (Paket 4): nichts verhindern, aber sagen, was dann nicht mehr zusammenpasst
        if status == "gewaehlt":
            for x in o.get("erfordert") or []:
                if not x["im_plan"]:
                    hinweise.append(f"{oid} setzt {x['id']} „{x['titel']}“ voraus; das steht derzeit nicht im Plan"
                                    + ("" if x["gueltig"] else " und ist verworfen") + ".")
            for x in o.get("schliesst_aus") or []:
                if x["im_plan"]:
                    hinweise.append(f"{oid} und {x['id']} „{x['titel']}“ schließen sich aus; {x['id']} steht derzeit im Plan.")
        if status in ("verworfen", "ersetzt"):
            for w2 in self.r.get("wahlstellen", []):
                for o2 in w2["optionen"]:
                    if o2.get("im_plan") and o2["status"] not in ("verworfen", "ersetzt") and \
                            any(x["id"] == oid for x in o2.get("erfordert") or []):
                        hinweise.append(f"{o2['id']} „{o2['titel']}“ steht im Plan und setzt {oid} voraus.")
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

def ausstehend_datei():
    """Links neuer Reisen, die veroeffentlichen.sh zustellt (betrieb/zustellen.py), sobald die Seite online ist (Dienstordner)."""
    return Path(os.environ.get("KN_AUSSTEHEND") or rm.dienstordner() / "neue-reisen-ausstehend.jsonl")


def rueckmeldung_senden(reise, eintrag):
    """An den Rückmeldedienst, damit eingang.jsonl nur einen Schreiber hat. -> (antwort, fehler)"""
    return dienst_anfrage("POST", f"{reise}/rueckmeldungen", eintrag)


def schreibdienst():
    """Adresse des Schreibwegs (engine/schreiben.py dienst), leer: bei dieser Instanz nicht eingerichtet."""
    return os.environ.get("KN_SCHREIBDIENST", "").rstrip("/")


def schreib_anfrage(reise, werkzeug_, anfrage):
    """Direkt in die Ontologie der Reise schreiben (ADR-0001, O-3): der Schreibweg prüft Rolle, Status und Form, baut zur
    Probe, sichert und veröffentlicht. -> (antwort, fehler)"""
    req = urllib.request.Request(f"{schreibdienst()}/{reise}/{werkzeug_}", method="POST",
                                 data=json.dumps(anfrage, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "X-Frieda-Dienst": konten.dienst_geheimnis()})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        try:
            return None, json.loads(e.read()).get("fehler", f"Fehler {e.code}")
        except (json.JSONDecodeError, AttributeError):
            return None, f"Fehler {e.code}"
    except (urllib.error.URLError, OSError):
        return None, "Der Schreibweg ist nicht erreichbar, bitte später noch einmal"


def ontologie_text(name, args):
    """Vorschlag oder Eintrag in Worten: welche Art, welches Merkmal, welche Felder."""
    felder = ("art", "kategorie", "bezeichnung", "einzahl", "gruppe", "symbol", "nummeriert", "art_bezeichnung", "art_symbol",
              "art_hinweis", "art_umriss", "grundform", "farbe", "beschreibung", "summiert", "merkmal", "typ", "werte", "veraenderlich",
              "stufe", "einheit", "hilfe", "frage", "auch", "grund")
    teile = []
    for f in felder:
        v = args.get(f)
        if v in (None, "", []):
            continue
        if f == "stufe":   # für Menschen in Worten (nötig, gut zu wissen, zusätzlich; Product Owner 29.10.2026)
            s = stufe_schluessel(v)
            v = "abgeschaltet (aus)" if s == "aus" else stufe_wort(s) if s else v
        teile.append(f"{f}: {' | '.join(map(str, v)) if isinstance(v, list) else v}")
    return ({"art_definieren": "Art festlegen", "kategorie_definieren": "Kartenkategorie festlegen"}.get(name, "Merkmal festlegen")) + " – " + "; ".join(teile)


def ids_der_reise(d):
    """Alle IDs, an denen etwas hängen kann (für Vorprüfungen im Konnektor)."""
    r = d.get("route") or {}
    ids = set(r.get("unterkuenfte") or {}) | set(r.get("aufenthalte") or {}) | set(r.get("strecken") or {}) | set(r.get("orte") or {})
    ids |= {t["id"] for t in r.get("tage") or []} | {w["id"] for w in r.get("wahlstellen") or []}
    ids |= {o["id"] for w in r.get("wahlstellen") or [] for o in w["optionen"]} | {a["id"] for a in d.get("abschnitte") or []}
    return ids


def merkmal_hinweise(d, art, merkmale):
    """Unbekannte Merkmale in einer Anfrage -> Hinweistext (ähnliches Merkmal nennen) oder None."""
    if not isinstance(merkmale, dict) or not art:
        return None
    krit = ((d.get("route") or {}).get("merkmale") or {}).get(art) or []
    bekannt = {k["id"] for k in krit} | {x for k in krit for x in (k.get("auch") or [])}
    fremd = [str(k) for k in merkmale if str(k).lower() not in bekannt]
    if not fremd:
        return None
    z = []
    for k in fremd:
        a = aehnliches_merkmal(k, krit)
        z.append(f"„{k}“ gibt es an der Art {art} nicht" + (f"; gemeint ist wohl {a['id']} – {a['name']}" if a else
                 "; ein neues Merkmal legt ein:e Organisator:in mit merkmal_definieren an (du kannst es damit vorschlagen)"))
    return "Nicht eingetragen: " + "; ".join(z) + "."


def ontologie_werkzeug(reise, d, wer, zugang, name, args):
    """Werkzeuge, die direkt in die Reise schreiben (ADR-0001, O-3; engine/schreiben.py): Rolle und Status prüft der Konnektor vor dem
    Senden, der Schreibweg noch einmal mit reise.yaml. art_definieren und merkmal_definieren gehen für Mitwirkende als Rückmeldung
    der Art Ergänzung (Vorschlag). -> (Text, ist_fehler)"""
    if not all(isinstance(v, (str, bool, int, float, list, dict, type(None))) for v in args.values()):
        return "Alle Angaben müssen Text, Zahlen, ja/nein, Listen oder Objekte sein.", True
    aktion = ONTOLOGIE_AKTION[name]
    vorschlag = aktion == "ontologie" and not darf(wer["rolle"], "organisator")
    if (nein := recht(wer["rolle"], d, "rueckmeldung" if vorschlag else aktion)):
        return nein, True
    if not schreibdienst():
        return ("Bei dieser Instanz ist der Schreibweg nicht eingerichtet (engine/schreiben.py dienst, docs/betrieb.md); bis dahin "
                "ändert eine Sitzung im Reisen-Repo die Reise."), True
    name_ = wer["name"] or args.get("name") or args.get("vorname")
    if not isinstance(name_, str) or not name_.strip():
        return ("Das geht nur mit dem persönlichen Link: Jede Änderung gehört genau einer Person, und dieser Link kennt keinen Namen."
                if aktion == "ontologie" and not vorschlag else "Name fehlt: bitte die Person nach ihrem Vornamen fragen."), True
    wer = {**wer, "name": name_.strip()}
    rest = {k: v for k, v in args.items() if k not in ("name", "vorname", "trotzdem")}
    if vorschlag:
        ziel = art_schluessel(str(args.get("kategorie") or args.get("art") or args.get("bezeichnung") or "")) or "allgemein"
        e, fehler = rueckmeldung_senden(reise, {"name": wer["name"], "art": "Ergänzung", "ziel": ziel[:rm.LAENGE["ziel"]],
                                                "text": ontologie_text(name, rest)[:rm.LAENGE["text"]], "quelle": "über Claude"})
        if fehler:
            return f"Nicht gespeichert: {fehler}", True
        organisator = " und ".join(organisator_namen(d)) or "ein:e Organisator:in"
        return (f"Vorschlag {e['id']} gespeichert. Arten und Merkmale legen Organisator:innen fest; {organisator} sieht den Vorschlag "
                "unter rueckmeldungen und kann ihn im Gespräch übernehmen."), False
    # Vorprüfungen mit dem veröffentlichten Stand (der Schreibweg prüft noch einmal mit dem Repo)
    route = d.get("route") or {}
    if name == "merkmal_definieren" and not args.get("trotzdem"):
        art = str(args.get("art") or "").strip().lower()
        krit = (route.get("merkmale") or {}).get(art) or []
        key = art_schluessel(str(args.get("merkmal") or args.get("bezeichnung") or ""))
        if key and key not in {k["id"] for k in krit}:
            aehnlich = aehnliches_merkmal(key, krit)
            if aehnlich:
                return (f"Nicht angelegt: Bei der Art {art} gibt es schon ein ähnliches Merkmal, {aehnlich['id']} – {aehnlich['name']}. "
                        "Das vorhandene nutzen oder mit merkmal_definieren ändern; ist es wirklich ein anderes, noch einmal mit "
                        "trotzdem = true."), True
    if name in ("wert_eintragen", "ding_aendern", "tag_aendern", "lage_eintragen"):
        ziel = str(args.get("ziel") or "").strip()
        if ziel and ziel not in ids_der_reise(d):
            return f"„{ziel}“ gibt es in dieser Reise nicht. Mit suche oder ueberblick die ID finden.", True
    if name == "buchung_anlegen":
        fuer = args.get("fuer")
        fuer = [x.strip() for x in fuer.split(",")] if isinstance(fuer, str) else list(fuer or [])
        fremd = [x for x in fuer if not isinstance(x, str) or x not in ids_der_reise(d)]
        if fremd:
            return f"{', '.join(map(str, fremd))} gibt es in dieser Reise nicht (fuer: Unterkunft U-…, Aufenthalt A-… oder Strecke E-…).", True
    if name == "buchung_aendern":
        ziel = str(args.get("ziel") or "").strip().upper()
        if ziel not in (route.get("buchungen") or {}):
            return f"Die Buchung „{ziel}“ gibt es nicht (zeige U-…/E-… nennt die Buchung, ueberblick zählt sie).", True
    if name == "ding_anlegen":
        if (h := merkmal_hinweise(d, str(args.get("art") or "").lower(), args.get("merkmale"))):
            return h, True
    if name == "option_anlegen":
        vid = str(args.get("wahlstelle") or "").strip()
        w = next((w for w in route.get("wahlstellen") or [] if w["id"] == vid), None)
        if w is None:
            return f"Die Wahlstelle „{vid}“ gibt es nicht; varianten zeigt alle. Fehlt sie wirklich, wahlstelle_anlegen.", True
        if (h := merkmal_hinweise(d, w.get("bereich"), args.get("merkmale"))):
            return h, True
    if name == "frage_schliessen":
        fid = str(args.get("frage") or "").strip().upper()
        zeile = next((z for z in (d.get("fragen") or {}).get("zeilen", []) if z["id"] == fid), None)
        if zeile is None:
            return f"Die Frage „{fid}“ gibt es nicht. Mit offene_fragen die richtige F-… finden.", True
    if name == "wissen_schreiben" and args.get("abschnitt"):
        wid = str(args.get("abschnitt") or "").strip().upper()
        if wid not in {a["id"] for a in d.get("abschnitte") or []}:
            return f"Den Abschnitt „{wid}“ gibt es nicht (ueberblick zeigt das Inhaltsverzeichnis).", True
    if name in ("wahlstelle_anlegen", "frage_anlegen"):
        fremd = [x for x in (args.get("an" if name == "wahlstelle_anlegen" else "bezug") or []) if isinstance(x, str) and x not in ids_der_reise(d)]
        if fremd:
            return f"{', '.join(fremd)} gibt es in dieser Reise nicht.", True
    antwort, fehler = schreib_anfrage(reise, name, {"person": zugang.get("person"), "name": wer["name"], "rolle": wer["rolle"], "args": rest})
    if fehler:
        return f"Nicht eingetragen: {fehler}", True
    return (f"Eingetragen und gesichert ({wer['name']}): {antwort.get('text', '')} Es gilt ab jetzt; die Seite und die Werkzeuge "
            "zeige, merkmale und varianten zeigen den neuen Stand, sobald veröffentlicht ist (wenige Minuten)."), False


def dienst_anfrage(methode, pfad, daten):
    """Schreibender Aufruf beim Rückmeldedienst (einziger Schreiber der Ablage). -> (antwort, fehler)"""
    basis = os.environ.get("KN_RUECKMELDEDIENST", "http://127.0.0.1:8771").rstrip("/")
    req = urllib.request.Request(f"{basis}/{pfad}", method=methode,
                                 data=json.dumps(daten, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "X-Frieda-Dienst": konten.dienst_geheimnis()})
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


def brett_text(b, titel=None):
    """Wunsch-Brett als Text für die Claude-App: Spalten mit Wünschen, dann Bilanz je Person."""
    titel = titel or {}
    k = b["kontingent"]
    punkte = k["art"] == "punkte"
    stelle = lambda ids: ", ".join(f"{x} {titel[x]}" if titel.get(x) else x for x in ids)
    z = ["## Wunsch-Brett (" + (f"je Person {k['je_person']} Punkte für die eigenen Wünsche" if punkte else
                                f"je Person höchstens {k['je_person']} Wünsche") + ")"]
    for sp in b["spalten"]:
        liste = [w for w in b["wuensche"] if w["spalte"] == sp["id"]]
        z.append(f"### {sp['titel']} ({len(liste)})")
        for w in sorted(liste, key=lambda w: -w["punkte"]):
            z.append(f"- {w['id']} · {w['name']}" + (f" · {w['punkte']} Punkte" if punkte and w["punkte"] else "") + f": {w['text']}")
            if w["status"] == "rueckfrage":
                z.append(f"  Rückfrage: {w['kommentar']}")
            elif w["kommentar"]:
                z.append(f"  Claude: {w['kommentar']}")
            v = w.get("vorschlag") or {}
            if v.get("bezug") or v.get("notiz") or v.get("option"):
                z.append("  Vorschlag: " + "; ".join(x for x in (
                    f"passt zu {stelle(v['bezug'])}" if v.get("bezug") else "",
                    f"Option {v['option']}" + (" (gewählt)" if v.get("gewaehlt") else " (zur Wahl)") if v.get("option") else "",
                    v.get("notiz") or "") if x))
            if w.get("eingeplant"):
                e = w["eingeplant"]
                z.append(f"  Eingeplant von {e['wer']} am {e['datum']}" + (f": {stelle(e['bezug'])}" if e.get("bezug") else ""))
            if w.get("erlebt"):
                z.append(f"  Erlebt ✓ {w['erlebt']['wer']} am {w['erlebt']['datum']}")
    z.append("### Bilanz je Person")
    for p in b["bilanz"]:
        z.append(f"- {p['name']}: {p['wuensche']} Wünsche, {p['eingeplant']} eingeplant, {p['erlebt']} erlebt, "
                 + (f"{p['frei']} von {k['je_person']} Punkten frei" if punkte else f"noch {p['frei']} Wünsche frei"))
    return "\n".join(z)


def wuensche_kurz(reise):
    """Eine Zeile für den Überblick: wie viele Wünsche in welcher Spalte."""
    o = rm.ordner(reise)
    if o is None:
        return ""
    b = rm.brett(o, rm.zustand(reise))
    if not b["wuensche"]:
        return "\n## Wünsche: noch keine (Werkzeug wuensche)"
    zahl = {s["titel"]: sum(1 for w in b["wuensche"] if w["spalte"] == s["id"]) for s in b["spalten"]}
    return (f"\n## Wünsche: {len(b['wuensche'])} (" + ", ".join(f"{t.lower()} {n}" for t, n in zahl.items() if n)
            + ") (Werkzeug wuensche)")


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


def belege_von(reise, wer):
    """Belege je Buchung aus der Ablage (engine/belege.py, #76), soweit diese Person sie sehen darf -> {B-ID: [Beleg]}."""
    o = rm.ordner(reise)
    aus = {}
    for b in (bl.liste(o, wer.get("name"), wer.get("rolle")) if o else []):
        aus.setdefault(b["buchung"], []).append(b)
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

def konflikt_pruefen(reise, d, wer, oid, status):
    """Widerspricht die Entscheidung einer anderen Organisator:in (regeln.konflikt = offene_frage)? -> (Beschreibung, Beteiligte) oder (None, [])."""
    regeln = ((d or {}).get("reise") or {}).get("regeln") or {}
    if regeln.get("konflikt", "offene_frage") != "offene_frage":
        return None, []
    alt = konflikte({"wer": wer, "ziel": oid, "entscheidung": status}, stehende_entscheidungen(reise, d))
    if not alt:
        return None, []
    return "; ".join(f"{x['quelle']}: {x['entscheidung']} {x['ziel']}" for x in alt), alt


def entscheiden(reise, d, h, wer, args):
    """Werkzeug entscheiden. Rolle, Status und Baustein sind schon geprüft. Der Dienst prüft die Entscheidung im Moment
    (Handbuch.entscheidung_pruefen). Mit Schreibweg (ADR-0001, O-3) schreibt er den Verlaufseintrag sofort in routen.yaml der
    Reise; ein Widerspruch zu einer anderen Organisator:in wird nicht übernommen, sondern eine offene Frage mit Meldung an beide.
    -> (Text, ist_fehler)"""
    if not wer["name"]:
        return ("Entscheiden geht nur mit dem persönlichen Link: Jede Entscheidung gehört genau einer Person, und dieser Link "
                "kennt keinen Namen. Ein:e Organisator:in kann mit person_einladen einen persönlichen Link ausstellen."), True
    if not all(isinstance(args.get(k) or "", str) for k in ("option", "status", "grund", "ersetzt_durch", "quelle")):
        return "Alle Angaben müssen Text sein.", True
    ergebnis, hinweise, fehler = h.entscheidung_pruefen(args, wer["name"])
    if fehler:
        return "Nicht entschieden:\n" + "\n".join(f"- {f}" for f in fehler), True
    text_, daten_ = ergebnis
    wort = WORT[daten_["entscheidung"]]
    if schreibdienst():
        beschr, alt = konflikt_pruefen(reise, d, wer["name"], daten_["option"], daten_["entscheidung"])
        if beschr:
            frage = (f"Widerspruch zwischen Organisator:innen zu {daten_['option']}: {wer['name']} will {wort} ({daten_['grund']}), aber "
                     f"{beschr}. Einigen, dann entscheiden.")
            antwort, fehler = schreib_anfrage(reise, "frage_anlegen", {"person": wer.get("person"), "name": wer["name"], "rolle": wer["rolle"],
                                                                       "args": {"text": frage, "bis": "vor Abreise", "bezug": [daten_["wahlstelle"]]}})
            m_ = re.search(r"\bF-\d+\b", (antwort or {}).get("text", "")) if antwort else None
            fid = m_.group(0) if m_ else None
            o = rm.ordner(reise)
            organisator = set(organisator_namen(d)) & ({wer["name"]} | {x["wer"] for x in alt})
            if o is not None:
                rm.meldung_anlegen(o, organisator or {wer["name"]}, "konflikt", daten_["option"],
                                   f"{wer['name']} will {daten_['entscheidung']} {daten_['option']}, aber {beschr}. Beides gilt nicht, bis ihr "
                                   f"euch einig seid" + (f"; offene Frage {fid}" if fid else "") + ".", [])
            return (f"Nicht entschieden: {daten_['option']} {wort} zu setzen widerspricht einer anderen Entscheidung ({beschr}). Nichts wird "
                    f"übernommen, bis ihr euch einig seid: " + (f"Dafür steht jetzt die offene Frage{' ' + fid if fid else ''}, und" if antwort and not fehler
                                                               else "Es gibt dafür eine Meldung, und")
                    + " alle beteiligten Organisator:innen bekommen sie zu sehen. Sag nie, etwas sei schon entschieden."), False
        rest = {k: args[k] for k in ("option", "status", "grund", "ersetzt_durch", "quelle") if args.get(k)}
        antwort, fehler = schreib_anfrage(reise, "entscheiden", {"person": wer.get("person"), "name": wer["name"], "rolle": wer["rolle"], "args": rest})
        if fehler:
            return f"Nicht entschieden: {fehler}", True
        z = [f"{antwort.get('text', '')} Gesichert; es gilt ab jetzt, die Seite zeigt es in wenigen Minuten."]
        if hinweise:
            z.append("Hinweise:\n" + "\n".join(f"- {x}" for x in hinweise))
        return "\n".join(z), False
    return ("Bei dieser Instanz ist der Schreibweg nicht eingerichtet (engine/schreiben.py dienst, docs/betrieb.md); entscheiden geht "
            "erst damit."), True


def frage_beantworten(reise, d, h, wer, args):
    """Werkzeug frage_beantworten: Die Antwort geht als Rückmeldung (Art Antwort) an die Frage. Sie ist eine Eingabe;
    ob die Frage geklärt ist, entscheidet ein:e Organisator:in. -> (Text, ist_fehler)"""
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
    organisator = " und ".join(organisator_namen(d)) or "ein:e Organisator:in"
    z = [f"Antwort {e['id']} gespeichert, sie hängt an {fid} (zeige {fid} listet sie). Die Frage bleibt offen: Eine Antwort ist "
         f"eine Eingabe, ob damit geklärt ist und was daraus folgt, entscheidet {organisator}."]
    if stelle:
        z.append(f"Die Frage gehört zur Wahlstelle {stelle['id']} {stelle['titel']}."
                 + (" Als Organisator:in kannst du dort mit entscheiden entscheiden." if darf(wer["rolle"], "organisator") else ""))
    return " ".join(z), False


# ---------- Personen einladen (Paket C) ----------

def zugang_ausstellen(z):
    """Neuen geheimen Link anlegen -> Token. z: {"reise", "person"} oder {"reise", "rolle"}. Schreibt zugaenge.json
    (Rechte 600); der Dienst braucht dafür Schreibrecht auf den Ordner (Einstellung des Dienstes im Betrieb)."""
    p = zugaenge_pfad()
    with _sperre:
        p.parent.mkdir(parents=True, exist_ok=True)
        alle = zugaenge()
        token = secrets.token_urlsafe(24)
        alle[token] = {**z, "angelegt": datetime.date.today().isoformat()}
        rm.schreiben(p, json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
        os.chmod(p, 0o600)
    return token


def einladen(reise, d, wer, args, mit_konto=False):
    """person_einladen: Person mit Rolle anlegen und ihren Zugang ausstellen. Eine Person, die es schon gibt, bekommt
    einen weiteren Link (ihre Rolle ändert sich dabei nie: das ist eine Einstellung der Reise). -> (Text, ist_fehler)
    mit_konto (Konnektor „Frieda“, Paket J): statt eines Links geht eine Einladung an die E-Mail-Adresse; sie gilt beim
    Anmelden (docs/konten.md). Auch eine Person, die es schon gibt, lässt sich so mit ihrem Konto verknüpfen."""
    if mit_konto:
        try:
            email = konten.adresse(args.get("email"))
        except konten.KontoFehler:
            return "email fehlt oder ist keine E-Mail-Adresse: An welche Adresse soll die Einladung gehen?", True
    vorname = args.get("vorname")
    rolle = rolle_neu(args.get("rolle") or "mitwirkend")
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
                "Bitte ein:e Organisator:in um einen persönlichen Link."), True
    if not mit_konto and not os.environ.get("KN_BASIS"):
        return "Die Adresse für Links ist auf dem Server nicht eingerichtet (KN_BASIS). Das muss der Betreiber ergänzen.", True
    o = rm.ordner(reise)
    if o is None:
        return "Diese Reise nimmt noch keine Eingaben an.", True
    personen = personen_der_reise(reise, d)
    vorhanden = next((p for p in personen if p["name"].casefold() == vorname.casefold()
                      or p["schluessel"] == (args.get("schluessel") or "").strip()), None)
    if vorhanden:
        if args.get("rolle") and rolle != vorhanden["rolle"]:
            # Rolle ändern: eine Einstellung der Reise, nur Organisator:innen, direkt nach reise.yaml (person_schreiben)
            if not darf(wer["rolle"], "organisator"):
                return f"{vorhanden['name']} ist schon dabei, mit der Rolle {vorhanden['rolle']}. Die Rolle ändern nur Organisator:innen.", True
            if not schreibdienst():
                return f"{vorhanden['name']} ist schon dabei, mit der Rolle {vorhanden['rolle']}. Die Rolle ändern geht erst mit eingerichtetem Schreibweg.", True
            a_, fehler = schreib_anfrage(reise, "person_schreiben", {"person": wer.get("person"), "name": wer["name"], "rolle": wer["rolle"],
                                                                     "args": {"schluessel": vorhanden["schluessel"], "rolle": rolle}})
            if fehler:
                return f"Rolle nicht geändert: {fehler}", True
            return (f"{vorhanden['name']} hat jetzt die Rolle {rolle} (vorher {vorhanden['rolle']}); die Seite zeigt es in wenigen Minuten. "
                    "Der Link bleibt derselbe."), False
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
                "Für mehr Rechte muss ein:e Organisator:in einladen."), True
    if not neu and not darf(wer["rolle"], rolle):
        return f"Einen Link für {vorhanden['name']} (Rolle {rolle}) kann nur jemand mit mindestens dieser Rolle ausstellen.", True
    if neu:
        with _sperre:
            if len(rm.einladungen_lesen(o)) >= rm.MAX_EINLADUNGEN:
                return "Es sind schon sehr viele Einladungen vorgemerkt (einladungen.json); der Betreiber räumt sie auf.", True
    if mit_konto:
        # Eine Person, die schon in der Reise steht, mit einem Konto verknüpfen heißt: wer die Adresse hat, spricht als sie.
        # Deshalb nur durch Organisator:innen, und Organisator:innen selbst verknüpft nur der Betreiber (konten.py einladen), sonst könnte
        # man sich per eigener Adresse als eine andere Organisator:in ausgeben (Prüfung J3, 27.10.2026).
        if not neu and not darf(wer["rolle"], "organisator"):
            return ("Eine Person, die schon in der Reise steht, mit einem Konto verknüpfen darf nur ein:e Organisator:in."), True
        if not neu and vorhanden["rolle"] == "organisator":
            return (f"{vorhanden['name']} organisiert die Reise mit. Organisator:innen verknüpft der Betreiber mit ihrem Konto, "
                    "nicht das Gespräch."), True
        return einladen_per_mail(reise, d, o, wer, args, vorname if neu else vorhanden["name"], rolle, schluessel, neu,
                                 notiz, email)
    try:
        token = zugang_ausstellen({"reise": reise, "person": schluessel})
    except OSError:
        return ("Der Link konnte nicht angelegt werden: Der Dienst darf die Zugänge nicht schreiben. Das muss der "
                "Betreiber einrichten (Schreibrecht auf die Datei KN_ZUGAENGE, docs/konnektor.md)."), True
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
        person_sichern(reise, wer, text_, schluessel, eintrag, name_von)
    z = [(f"{vorname} ist eingeladen" if neu else f"Neuer Link für {vorhanden['name']}") + f" (Rolle {rolle}). Der Link:",
         link, "",
         "Den Link nur an diese Person geben, am besten privat: Wer ihn kennt, spricht in der Reise als " + vorname + ". "
         "Sie trägt ihn in der Claude-App ein (Einstellungen → Konnektoren → Eigenen Konnektor hinzufügen, ohne Anmeldung); "
         "dafür braucht sie ein Claude-Konto, in dem eigene Konnektoren erlaubt sind.",
         {"gast": "Mit der Rolle gast kann sie nur lesen.",
          "mitwirkend": "Als Mitwirkende:r gibt sie Wünsche, Rückmeldungen, Aufgaben und Antworten; entscheiden kann sie nicht.",
          "organisator": "Als Organisator:in entscheidet sie mit, setzt Status und Einstellungen und lädt Personen ein."}[rolle]]
    if neu:
        z.append("Auf der Seite steht die Person in wenigen Minuten.")
    return "\n".join(z), False


def person_sichern(reise, wer, text_, schluessel, eintrag, name_von):
    """Neue Person nach reise.yaml über den Schreibweg (person_schreiben). Scheitert das, gilt die Person trotzdem schon
    (einladungen.json); der Fehler steht im Protokoll und als Meldung an die Organisator:innen."""
    if not schreibdienst():
        sys.stderr.write(f"person_schreiben {reise}/{schluessel}: kein Schreibweg (KN_SCHREIBDIENST)\n")
        return
    a, fehler = schreib_anfrage(reise, "person_schreiben", {"person": wer.get("person"), "name": name_von, "rolle": wer["rolle"],
                                                            "args": {"schluessel": schluessel, "vorname": eintrag["name"], "rolle": eintrag["rolle"],
                                                                     "reist": eintrag.get("reist", True), "notiz": eintrag.get("notiz")}})
    if fehler:
        sys.stderr.write(f"person_schreiben {reise}/{schluessel}: {fehler}\n")
        o = rm.ordner(reise)
        if o is not None:
            rm.meldung_anlegen(o, [name_von], "technik", "reise", f"{eintrag['name']} ist eingeladen (Zugang gilt), steht aber noch nicht "
                               f"in der Reise: {fehler} Bitte noch einmal mit person_einladen oder dem Betreiber sagen.")


# ---------- Konto: meine Reisen und neue Reise (Paket H) ----------
def seitenlinks():
    """Links zu den Seiten je Reise {reise: url}; schreibt der Betrieb beim Freischalten (fehlt die Datei: keine)."""
    p = Path(os.environ.get("KN_SEITENLINKS") or zugaenge_pfad().with_name("seiten.json"))
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def vergebene_pfade():
    """Ordner veröffentlichter Reisen, vorhandene Ablagen und neue Reisen, die schon angefragt sind."""
    pfade = {p.name for p in seiten().iterdir() if p.is_dir() and not p.name.startswith("_")} if seiten().is_dir() else set()
    if rm.ablage().is_dir():
        pfade |= {o.name for o in rm.ablage().iterdir() if o.is_dir() and rm.REISE_MUSTER.match(o.name)}
    o = rm.ordner_neu()
    if o:
        pfade |= {e["daten"]["neue_reise"]["pfad"] for e in rm.auftraege(o)
                  if (e.get("daten") or {}).get("neue_reise") and e["status"] not in ("verworfen", "rueckfrage")}
    return pfade


def person_entfernen(reise, d, wer, args):
    """person_entfernen (Organisator:in): Verknüpfung mit dem Konto und alte Links enden sofort; in reise.yaml wird die Person
    über den Schreibweg zum Gast, der nicht mitreist (person_schreiben; niemand wird gestrichen). Organisator:innen und sich
    selbst nimmt man so nicht heraus. -> (Text, ist_fehler)"""
    gesucht = str(args.get("person") or "").strip()
    p = next((x for x in personen_der_reise(reise, d)
              if x["schluessel"] == gesucht or x["name"].casefold() == gesucht.casefold()), None) if gesucht else None
    if not p:
        return "Wen? Bitte person angeben (Vorname oder Schlüssel aus dem Überblick).", True
    if not wer["name"] or p["name"].casefold() == wer["name"].casefold():
        return "Dich selbst nimmst du so nicht aus der Reise.", True
    if p["rolle"] == "organisator":
        return (f"{p['name']} organisiert die Reise mit. Ein:e Organisator:in nimmt man nicht im Gespräch heraus; dafür sprechen "
                "die Organisator:innen miteinander und ändern die Rolle (person_einladen mit anderer Rolle geht nicht), sonst der Betreiber."), True
    grund = str(args.get("grund") or "").strip()[:300]
    konten.entfernen(reise, p["schluessel"])
    with _sperre:
        alle = zugaenge()
        rest = {t: z for t, z in alle.items() if not (z.get("reise") == reise and z.get("person") == p["schluessel"])}
        if len(rest) != len(alle):
            rm.schreiben(zugaenge_pfad(), json.dumps(rest, ensure_ascii=False, indent=1) + "\n")
            os.chmod(zugaenge_pfad(), 0o600)
    o = rm.ordner(reise)
    if p.get("eingeladen") and o is not None:
        with _sperre:
            alle = rm.einladungen_lesen(o)
            alle.pop(p["schluessel"], None)
            rm.schreiben(o / "einladungen.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
    else:
        # Niemand wird gestrichen (der Verlauf nennt die Person weiter): sie wird gast und reist nicht mehr
        if not schreibdienst():
            return "Zugang beendet; in die Reise schreiben geht erst mit eingerichtetem Schreibweg (docs/betrieb.md).", True
        a, fehler = schreib_anfrage(reise, "person_schreiben", {"person": wer.get("person"), "name": wer["name"], "rolle": wer["rolle"],
                                                                "args": {"schluessel": p["schluessel"], "rolle": "gast", "reist": False,
                                                                         "notiz": f"ausgeschieden am {datum_de(datetime.date.today().isoformat())} ({wer['name']})"
                                                                                  + (f": {grund}" if grund else "")}})
        if fehler:
            return f"Zugang beendet, aber nicht in die Reise geschrieben: {fehler}", True
    return (f"{p['name']} ist aus der Reise genommen: Zugang über Konto und Links endet sofort. "
            + ("" if p.get("eingeladen") else "In der Reise steht die Person als Gast, die nicht mitreist (der Verlauf nennt sie weiter); "
               "die Seite zeigt es in wenigen Minuten.")), False


def einladen_per_mail(reise, d, o, wer, args, name, rolle, schluessel, neu, notiz, email):
    """Teil von einladen für den Konnektor „Frieda“: Person (falls neu) in einladungen.json und als Auftrag, dann die
    Einladung über engine/konten.py (Mail mit Hinweis zum Anmelden, gilt sofort, wenn die Adresse ein Konto hat)."""
    try:
        r = konten.einladen(reise, schluessel, email, rolle, name, wer["name"],
                            titel=((d or {}).get("reise") or {}).get("titel"), seite=seitenlinks().get(reise))
    except konten.KontoFehler as f:
        return f"Nicht eingeladen: {f}", True
    if neu:
        heute = datetime.date.today().isoformat()
        eintrag = {"name": name, "rolle": rolle, "reist": args.get("reist", True) is not False,
                   "notiz": notiz or f"eingeladen von {wer['name']} am {datum_de(heute)} über die Claude-App",
                   "eingeladen_von": wer["name"], "datum": heute}
        with _sperre:
            alle = rm.einladungen_lesen(o)
            alle[schluessel] = eintrag
            rm.schreiben(o / "einladungen.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
        person_sichern(reise, wer, f"Einladung von {wer['name']}: {name} als {rolle} in reise.yaml unter personen "
                       f"aufnehmen, Schlüssel {schluessel}, reist: {'ja' if eintrag['reist'] else 'nein'}, notiz: "
                       f"„{eintrag['notiz']}“. Rolle gilt schon (einladungen.json); die Einladung ging per Mail.",
                       schluessel, eintrag, wer["name"])
    return ((f"{name} ist eingeladen (Rolle {rolle})." if neu else f"Einladung für {name} (Rolle {rolle}) verschickt.")
            + f" Eine Mail ist an {email} unterwegs. "
            + ("Die Adresse hat schon ein Konto: Die Reise steht ab jetzt bei ihren Reisen."
               if r["sofort"] else "Sobald sie sich mit dieser Adresse bei Frieda anmeldet (oder über den Link in der "
               "Mail), ist sie dabei.")), False


def reise_kurz(reise):
    """Titel und Seitenlink einer veröffentlichten Reise (für die Anmeldeseiten) oder None."""
    d = daten(reise)
    if not d:
        return None
    return {"titel": (d.get("reise") or {}).get("titel", reise), "seite": seitenlinks().get(reise)}


def reisen_von(konto):
    """Veröffentlichte Reisen, auf denen die Person des Kontos dabei ist (Schlüssel oder Name) -> Liste von Einträgen."""
    name = konto["name"].casefold()
    links, zug = seitenlinks(), zugaenge()
    aus = []
    for f in sorted(seiten().glob("*/daten.json")) if seiten().is_dir() else []:
        reise = f.parent.name
        d = daten(reise)
        if not d:
            continue
        p = next((x for x in personen_der_reise(reise, d)
                  if x.get("schluessel") == konto["konto"] or str(x.get("name", "")).casefold() == name), None)
        if not p:
            continue
        rs = d.get("reise") or {}
        apps = [t for t, z in zug.items() if z.get("reise") == reise and z.get("person") == p["schluessel"]]
        aus.append({"reise": reise, "titel": rs.get("titel", reise), "untertitel": rs.get("untertitel", ""),
                    "status": (rs.get("status") or {}).get("wert"), "rolle": p["rolle"], "seite": links.get(reise),
                    "app": f"{basis()}/{apps[-1]}" if apps and os.environ.get("KN_BASIS") else None})
    return aus


def meine_reisen(konto):
    """Text für das Werkzeug meine_reisen: Meldungen, eigene Reisen mit Links, angefragte neue Reisen."""
    z = []
    o = rm.ordner_neu()
    if o:
        ms = rm.meldungen_aktuell(o, konto["name"])
        if ms:
            z.append("Meldungen an dich:")
            z += [f"- {datum_de(m['erstellt'][:10])}: {m['text']}" for m in ms]
            z.append("")
    reisen = reisen_von(konto)
    z.append(f"Deine Reisen ({len(reisen)}):" if reisen else "Noch keine Reise, auf der du dabei bist.")
    for r in reisen:
        z.append(f"- {r['titel']} ({r['untertitel']}), Status {r['status']}, du: {r['rolle']}")
        z.append(f"  Seite: {r['seite'] or 'Link liegt beim Betreiber'}")
        z.append(f"  Claude-App: {r['app'] or 'noch kein persönlicher Link (beim Betreiber oder einer Organisator:in der Reise erfragen)'}")
    if o:
        offen = [e for e in rm.auftraege(o) if e.get("name") == konto["name"] and (e.get("daten") or {}).get("neue_reise")
                 and e["status"] in ("neu", "rueckfrage")]
        if offen:
            z += ["", "Angefragte neue Reisen:"]
            z += [f"- {e['daten']['neue_reise']['titel']} ({e['id']}): "
                  + ("wird angelegt" if e["status"] == "neu" else f"Rückfrage: {e.get('kommentar') or 'siehe Betreiber'}")
                  for e in offen]
    return "\n".join(z)


def reise_anlegen(konto, args):
    """reise_anlegen: prüft die Eingaben sofort, legt in <ablage>/_neu die Anfrage als Beleg ab und lässt den Schreibweg die
    Reise anlegen. Sobald die Seite online ist, bekommt die Person eine Meldung mit den Links (meine_reisen).
    -> (Text, ist_fehler)"""
    o = rm.ordner_neu(anlegen=True)
    with _sperre:
        neu, fehler = neue_reise_pruefen(args, konto["name"], vergebene_pfade())
        if fehler:
            return f"Nicht angelegt: {fehler}", True
        if not schreibdienst():
            return ("Nicht angelegt: Der Schreibweg dieser Instanz ist nicht eingerichtet (KN_SCHREIBDIENST), ohne ihn kann der "
                    "Dienst keine Reise anlegen. Das muss der Betreiber einrichten (docs/betrieb.md, Schreibweg)."), True
        wer_text = ", ".join(f"{p['name']} ({p['rolle']}{'' if p.get('reist', True) else ', reist nicht mit'})"
                             for p in neu["personen"].values())
        text_ = (f"Neue Reise anlegen: „{neu['titel']}“, {datum_de(neu['von'])} bis {datum_de(neu['bis'])}"
                 + (f", Ziel {neu['ziel']}" if neu["ziel"] else "") + f". Personen: {wer_text}. Ordner reisen/{neu['pfad']}."
                 + (f"\nNotiz: {neu['notiz']}" if neu["notiz"] else ""))
        jetzt = datetime.datetime.now(datetime.timezone.utc)
        e = {"id": f"A-{jetzt:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}", "erstellt": jetzt.isoformat(timespec="seconds"),
             "name": konto["name"], "konto": konto["konto"], "art": "Auftrag", "ziel": "allgemein",
             "text": text_[:MAX_AUFTRAG], "quelle": "Claude-App", "daten": {"neue_reise": neu}}
        if konto.get("konto_id"):
            # Konnektor „Frieda“: wer anlegt, wird nach dem Anlegen mit seinem Konto verknüpft; wer eine Adresse hat,
            # bekommt eine Einladung per Mail (im Betrieb, sobald die Seite online ist). Adressen nie ins Repo.
            e["konto_id"] = konto["konto_id"]
            mails = []
            for x in args.get("personen") or []:
                if isinstance(x, dict) and x.get("email"):
                    try:
                        adr = konten.adresse(x["email"])
                    except konten.KontoFehler:
                        return f"Nicht angelegt: „{x.get('vorname')}“ hat keine gültige E-Mail-Adresse.", True
                    schl = next((k_ for k_, p_ in neu["personen"].items() if p_["name"] == str(x.get("vorname")).strip()),
                                None)
                    if schl:
                        mails.append({"schluessel": schl, "email": adr, "rolle": neu["personen"][schl]["rolle"],
                                      "name": neu["personen"][schl]["name"]})
            e["einladen"] = mails
        with (o / "auftraege.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
    # ADR-0001, O-3: die Reise entsteht sofort über den Schreibweg; die Links kommen, sobald die Seite online ist
    # (veroeffentlichen.sh stellt sie zu, Datei neue-reisen-ausstehend.jsonl im Dienstordner)
    a, fehler = schreib_anfrage(neu["pfad"], "reise_anlegen", {"person": None, "name": konto["name"], "rolle": "organisator",
                                                               "args": {"auftrag": e}})
    with _sperre:
        rm.status_setzen(o, e["id"], "rueckfrage" if fehler else "uebernommen",
                         f"Nicht angelegt: {fehler}" if fehler else f"Angelegt als {neu['pfad']}. Die Links stehen in meine_reisen, sobald die Seite online ist.")
        if not fehler:
            person = next(k_ for k_, p_ in neu["personen"].items() if p_["name"] == neu["wer"])
            ausstehend_datei().parent.mkdir(parents=True, exist_ok=True)
            with ausstehend_datei().open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ordner": neu["pfad"], "aid": e["id"], "name": konto["name"], "person": person}, ensure_ascii=False) + "\n")
    if fehler:
        return f"Nicht angelegt: {fehler}", True
    return (f"Die Reise „{neu['titel']}“ ist angelegt (Status Idee, Ordner {neu['pfad']}). In wenigen Minuten ist die Seite online; "
            "dann steht die Reise in meine_reisen"
            + (", und die Personen mit Adresse bekommen eine Einladung per Mail" if e.get("einladen") else
               ", mit dem Link zur Seite und dem Link für die Claude-App unter „Meldungen an dich“") + "."), False


# ---------- Konnektor „Frieda“ (Paket J3): ein Zugang für alle Reisen, angemeldet mit dem Konto (OAuth) ----------

REISEN_ANLEGEN_ANFRAGEN = {"name": "reisen_anlegen_anfragen", "description": "Bitten, Reisen anlegen zu dürfen. Das "
                           "entscheidet der Betreiber; bis dahin kann die Person bei Reisen mitmachen, zu denen sie "
                           "eingeladen ist.", "inputSchema": {"type": "object", "properties": {}}}
ANFRAGE_ENTSCHEIDEN = {"name": "anfrage_entscheiden", "description": "Nur für den Betreiber: eine Bitte „Reisen anlegen“ "
                       "annehmen oder ablehnen (offene Bitten stehen in meine_reisen). Vorher bestätigen lassen.",
                       "inputSchema": {"type": "object", "properties": {
                           "email": {"type": "string", "description": "Adresse des Kontos aus der Liste der Bitten"},
                           "erlauben": {"type": "boolean", "description": "true: darf Reisen anlegen; false: abgelehnt"}},
                           "required": ["email", "erlauben"]}}
EMAIL_FELD = {"type": "string", "description": "E-Mail-Adresse der Person: Sie bekommt die Einladung per Mail und meldet "
              "sich damit bei Frieda an. Vorher mit der einladenden Person abstimmen."}


def reisen_des_kontos(k):
    """[(reise, schluessel, daten)] der Reisen, mit denen das Konto verknüpft ist und die veröffentlicht sind."""
    aus = []
    for m in konten.mitgliedschaften(k["id"]):
        d = daten(m["reise"])
        if d:
            aus.append((m["reise"], m["schluessel"], d))
    return aus


def frieda_werkzeuge(k):
    """Konto-Werkzeuge plus alle Reise-Werkzeuge, die auf mindestens einer Reise des Kontos gehen, je mit Angabe reise."""
    eigene = [MEINE_REISEN, REISE_ANLEGEN_MIT_MAIL if konten.recht(k, "reise_anlegen") else REISEN_ANLEGEN_ANFRAGEN]
    if konten.recht(k, "betreiber"):
        eigene.append(ANFRAGE_ENTSCHEIDEN)
    reisen = reisen_des_kontos(k)
    je_name, wo = {}, {}
    for reise, schl, _ in reisen:
        for w in werkzeuge_fuer({"reise": reise, "person": schl}):
            je_name.setdefault(w["name"], w)
            wo.setdefault(w["name"], []).append(reise)
    aus = list(eigene)
    for n, w in je_name.items():
        schema = dict(w["inputSchema"])
        eig = {k_: v for k_, v in schema.get("properties", {}).items() if k_ != "name"}   # der Name kommt aus dem Konto
        if n == "person_einladen":
            eig["email"] = EMAIL_FELD
        eig["reise"] = {"type": "string", "enum": wo[n],
                        "description": "Ordner der Reise (aus meine_reisen)" + ("" if len(reisen) > 1 else "; optional")}
        pflicht = [x for x in schema.get("required", []) if x != "name"]
        if n == "person_einladen":
            pflicht.append("email")
        if len(reisen) > 1:
            pflicht.append("reise")
        aus.append({**w, "inputSchema": {**schema, "properties": eig, "required": pflicht}})
    return aus


# Wie Frieda mit der Person spricht (28.10.2026): Kennungen sind für die Werkzeuge da, nicht für die Person
SPRACHE = ("In Antworten Namen statt Kennungen: „Zugfahrt Münster → Duisburg am 8.1.“ statt „AG-01“. IDs nur für "
           "die Werkzeuge oder auf Nachfrage, A-/R-Nummern nie.")


def anleitung_frieda(k):
    reisen = reisen_des_kontos(k)
    z = [f"Aufgabe: Du bist Frieda, der Reiseassistent von {k['name']} (angemeldet als {k['email']}). Dieser Konnektor "
         "gilt für alle Reisen der Person; jedes Reise-Werkzeug braucht die Angabe reise (Ordner, siehe meine_reisen"
         + (")" if len(reisen) > 1 else "; bei nur einer Reise darf sie fehlen)") + ". Beginne mit meine_reisen und "
         "nenne Meldungen zuerst. Personen lädst du per E-Mail-Adresse ein (person_einladen mit email); Links gibt es "
         "nicht mehr. Neue Reisen: reise_anlegen, wenn die Person das darf, sonst reisen_anlegen_anfragen. " + SPRACHE]
    for reise, schl, d in reisen:
        z += ["", f"## Reise {reise}", anleitung({"reise": reise, "person": schl, "konto_id": k["id"]}, d)]
    if not reisen:
        z += ["", "Die Person hat noch keine Reisen. Wer eine Reise bestimmt, kann sie mit ihrer Adresse einladen."]
    return "\n".join(z)


def meine_reisen_konto(k):
    z = []
    o = rm.ordner_neu()
    if o:
        ms = rm.meldungen_aktuell(o, k["name"])
        if ms:
            z += ["Meldungen an dich:", *[f"- {datum_de(m['erstellt'][:10])}: {m['text']}" for m in ms], ""]
    reisen = reisen_des_kontos(k)
    z.append(f"Deine Reisen ({len(reisen)}):" if reisen else
             "Noch keine Reise. Wer eine Reise bestimmt, kann dich mit deiner E-Mail-Adresse einladen.")
    links = seitenlinks()
    for reise, schl, d in reisen:
        rs = d.get("reise") or {}
        p = next((x for x in personen_der_reise(reise, d) if x.get("schluessel") == schl), {})
        z.append(f"- {rs.get('titel', reise)} ({rs.get('untertitel', '')}), reise: {reise}, Status "
                 f"{(rs.get('status') or {}).get('wert')}, du: {p.get('rolle', '?')}")
        z.append(f"  Seite: {links.get(reise) or 'Link liegt beim Betreiber'}")
    if konten.recht(k, "reise_anlegen"):
        z += ["", "Du darfst neue Reisen anlegen (reise_anlegen)."]
    if o:
        offen = [e for e in rm.auftraege(o) if e.get("konto_id") == k["id"] and (e.get("daten") or {}).get("neue_reise")
                 and e["status"] in ("neu", "rueckfrage")]
        if offen:
            z += ["", "Angefragte neue Reisen:"]
            z += [f"- {e['daten']['neue_reise']['titel']} ({e['id']}): "
                  + ("wird angelegt" if e["status"] == "neu" else f"Rückfrage: {e.get('kommentar') or 'siehe Betreiber'}")
                  for e in offen]
    if konten.recht(k, "betreiber"):
        bitten = konten.anfragen()
        if bitten:
            z += ["", "Offene Bitten „Reisen anlegen“ (anfrage_entscheiden):",
                  *[f"- {a['name']} ({a['email']}), seit {a['erstellt'][:10]}" for a in bitten]]
    return "\n".join(z)


def frieda_werkzeug(k, name, args):
    args = dict(args) if isinstance(args, dict) else {}
    if name == "meine_reisen":
        return meine_reisen_konto(k), False
    if name == "reise_anlegen":
        if not konten.recht(k, "reise_anlegen"):
            return "Reisen anlegen darfst du noch nicht. Mit reisen_anlegen_anfragen kannst du darum bitten.", True
        return reise_anlegen({"konto": schluessel_aus_name(k["name"]) or "person", "name": k["name"],
                              "konto_id": k["id"]}, args)
    if name == "reisen_anlegen_anfragen":
        st = konten.reisen_anlegen_anfragen(k["id"])
        if st == "offen":
            anmeldung.betreiber_melden(k)
        return {"offen": "Deine Bitte liegt beim Betreiber. Du bekommst Bescheid in meine_reisen.",
                "schon_erlaubt": "Du darfst schon Reisen anlegen (reise_anlegen).",
                "abgelehnt": "Deine Bitte wurde abgelehnt. Bei Fragen wende dich an den Betreiber."}[st], False
    if name == "anfrage_entscheiden":
        if not konten.recht(k, "betreiber"):
            return "Das darf nur der Betreiber.", True
        try:
            wer = konten.konto_per_email(args.get("email"))
        except konten.KontoFehler as f:
            return str(f), True
        if not wer:
            return "Kein Konto mit dieser Adresse.", True
        konten.freischalten(wer["id"], ja=args.get("erlauben") is True)
        return f"{wer['name']} darf {'jetzt' if args.get('erlauben') is True else 'weiterhin keine'} Reisen anlegen.", False
    reisen = reisen_des_kontos(k)
    reise = args.pop("reise", None) or (reisen[0][0] if len(reisen) == 1 else None)
    if not reise:
        return "Welche Reise? Bitte reise angeben (Ordner aus meine_reisen).", True
    schl = next((s_ for r, s_, _ in reisen if r == reise), None)
    if not schl:
        return "Bei dieser Reise bist du nicht dabei (oder sie ist nicht veröffentlicht).", True
    args.pop("name", None)
    return werkzeug({"reise": reise, "person": schl, "konto_id": k["id"]}, name, args)


def frieda_antwort(zugang, nid, methode, p, ok):
    k = konten.konto(zugang["konto_id"])
    if not k or k["gesperrt"]:
        return {"jsonrpc": "2.0", "id": nid, "error": {"code": -32001, "message": "Konto gesperrt oder gelöscht"}}
    if methode == "initialize":
        gewuenscht = p.get("protocolVersion") if isinstance(p, dict) else None
        return ok({"protocolVersion": gewuenscht if gewuenscht in PROTOKOLLE else PROTOKOLLE[0],
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": "frieda", "title": "Frieda", "version": "1", "icons": frieda_symbole()},
                   "instructions": anleitung_frieda(k)})
    if methode == "ping":
        return ok({})
    if methode == "tools/list":
        return ok({"tools": frieda_werkzeuge(k)})
    if methode == "tools/call":
        t, fehler = frieda_werkzeug(k, p.get("name"), p.get("arguments"))
        return ok({"content": [{"type": "text", "text": t}], "isError": fehler})
    return {"jsonrpc": "2.0", "id": nid, "error": {"code": -32601, "message": f"unbekannt: {methode}"}}


MEINE_REISEN = {"name": "meine_reisen", "description": "Deine Reisen mit Rolle, Status, Link zur Seite und Link für die "
                "Claude-App; dazu Meldungen an dich (z. B. eine neu angelegte Reise) und angefragte neue Reisen.",
                "inputSchema": {"type": "object", "properties": {}}}


def anleitung_konto(konto):
    return (f"Aufgabe: Du bist Frieda, die Reiseplanung von {konto['name']}. Mit diesem Zugang siehst du die Reisen der "
            "Person (meine_reisen) und legst neue an (reise_anlegen). Für eine einzelne Reise gibt es eigene Konnektoren; "
            "Plan, Wissen und Rückmeldungen laufen dort. Beginne mit meine_reisen und nenne Meldungen zuerst. "
            "Neue Reise: Titel, Zeitraum, Ziel und Personen mit Rollen im Gespräch klären (gast liest, mitwirkend gibt "
            "Wünsche, Rückmeldungen und Aufgaben, organisator entscheidet mit), vor dem Anlegen bestätigen lassen. Bekanntes "
            "(Ideen, schon Gebuchtes, Quellen wie Bücher, Fotos, PDFs) in eigenen Worten mit Herkunft in die Notiz, nie "
            "abschreiben, nichts erfinden. Die Reise entsteht erst im Betrieb, sag nie, sie sei schon angelegt. Links sind "
            "persönlich: nur dieser Person zeigen. " + SPRACHE)


def konto_antwort(konto, nid, methode, p, ok):
    if methode == "initialize":
        gewuenscht = p.get("protocolVersion") if isinstance(p, dict) else None
        return ok({"protocolVersion": gewuenscht if gewuenscht in PROTOKOLLE else PROTOKOLLE[0],
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": "frieda", "title": "Frieda – meine Reisen", "version": "1",
                                  "icons": frieda_symbole()},
                   "instructions": anleitung_konto(konto)})
    if methode == "ping":
        return ok({})
    if methode == "tools/list":
        return ok({"tools": [MEINE_REISEN, REISE_ANLEGEN]})
    if methode == "tools/call":
        name, args = p.get("name"), p.get("arguments") if isinstance(p.get("arguments"), dict) else {}
        if name == "meine_reisen":
            t, fehler = meine_reisen(konto), False
        elif name == "reise_anlegen":
            t, fehler = reise_anlegen(konto, args)
        else:
            t, fehler = f"Unbekanntes Werkzeug {name}.", True
        return ok({"content": [{"type": "text", "text": t}], "isError": fehler})
    return {"jsonrpc": "2.0", "id": nid, "error": {"code": -32601, "message": f"unbekannt: {methode}"}}


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
     "Aufenthalt ohne Nacht (A-), Buchung (B-, mit Belegen), Wahlstelle (V-) oder Option (V-01.a), Plan (P-), offene Frage (F-), "
     "Wissens-Abschnitt (W-, auch W-06.unterabschnitt).",
     "inputSchema": {"type": "object", "properties": {"id": ZIEL_FELD}, "required": ["id"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "suche", "description": "Volltextsuche in der ganzen Reise. Alle Wörter müssen vorkommen. Liefert IDs mit Ausschnitt.",
     "inputSchema": {"type": "object", "properties": {"begriff": {"type": "string"}}, "required": ["begriff"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "offene_fragen", "description": "Offene Fragen und To-dos (F-…) mit Frist und Status.",
     "inputSchema": {"type": "object", "properties": {"alle": {"type": "boolean", "description": "auch erledigte"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "varianten", "description": "Alle Alternativen: benannte Pläne (P-…) und Wahlstellen (V-…) mit Optionen, "
     "Status, Dafür/Dagegen und Summen.",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "rueckmeldungen", "description": "Bisherige Rückmeldungen mit Status (neu, übernommen, verworfen, Rückfrage) "
     "und Antwort; bei Organisator:innen auch die Aufträge.",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "rueckmeldung_geben", "description": "Rückmeldung zu einer ID abgeben: Kommentar, Frage, Korrektur, Ergänzung "
     "oder Antwort (auf eine offene Frage F-…). Oder ein Wunsch: eine Idee für die Reise (Ort, Erlebnis, Essen), auch "
     "ohne passende ID; dann ziel leer lassen. Landet im Eingang und wird automatisch geprüft und "
     "eingearbeitet, in der Regel in wenigen Minuten; sie ändert nichts sofort. Vorher den Text mit der Person abstimmen.",
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
WERT_SCHEMA = {"type": "object", "properties": {
    "wert": {"type": "string"}, "quelle": {"type": "string"}, "geprueft": {"type": "string"}, "notiz": {"type": "string"},
    "gilt": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
             "description": "nur bei Werten je Datum: Datum JJJJ-MM-TT oder Liste solcher Daten"}}, "required": ["wert"]}
WERKZEUGE += [
    {"name": "merkmale", "description": "Welche Merkmale eine Alternative braucht (z. B. bei Unterkünften Preis, Frühstück, "
     "Öffnung), je mit Hinweis zum Recherchieren und zum gezielten Nachfragen; zu einer Wahlstelle auch, was jede Option "
     "schon hat und was fehlt. Vor wert_eintragen, option_anlegen und ding_anlegen aufrufen.",
     "inputSchema": {"type": "object", "properties": {
         "ziel": {"type": "string", "description": "Wahlstelle V-…, Option V-….a, Unterkunft U-… oder Strecke E-… (z. B. eine Fähre)"},
         "bereich": {"type": "string",
                     "description": "nur ohne ziel: eine Art dieser Reise (ihre Arten und Merkmale stehen in plan/arten.yaml; "
                                    "ohne Angabe nennt die Antwort die bekannten Arten)"}}},
     "annotations": {"readOnlyHint": True}},
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
WERKZEUGE += [
    {"name": "wuensche", "description": "Wunsch-Brett: alle Wünsche (R-…) nach Spalten (eingebracht, geprüft, eingeplant, "
     "erlebt, passt nicht) mit Punkten, Vorschlag von Claude (passt zu …), wer eingeplant und wer abgehakt hat; dazu die "
     "Bilanz je Person und das Kontingent.",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "wunsch_aendern", "description": "Wunsch auf dem Brett ändern, wirkt sofort (auch auf der Webseite): punkte = "
     "wie wichtig der Person ihr eigener Wunsch ist (nur eigene Wünsche, im Kontingent, umverteilen erlaubt); erlebt = "
     "abhaken (unterwegs und danach, alle Mitwirkenden); eingeplant mit bezug (nur Organisator:innen); kommentar für den Verlauf. "
     "Nur angegebene Felder ändern sich. Vorher kurz bestätigen lassen.",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string", "description": "R-… (aus wuensche)"},
         "punkte": {"type": "integer", "minimum": 0, "description": "neue Punktzahl dieses Wunsches"},
         "erlebt": {"type": "boolean"},
         "eingeplant": {"type": "boolean"},
         "bezug": {"type": "array", "items": {"type": "string"},
                   "description": "nur mit eingeplant true: wo eingeplant (z. B. [\"T-03\"]); leer = ohne feste Stelle"},
         "kommentar": {"type": "string", "description": "kurze Notiz für den Verlauf"},
         "name": NAME_FELD}, "required": ["id"]}},
]
# Ontologie der Reise im Gespräch (ADR-0001, O-3; docs/ontologie.md): die Software kennt nur die Form, die Reise ihre Arten
ART_DEFINIEREN = {"name": "art_definieren", "description": "Eine Art dieser Reise anlegen oder ändern (Hotel, Refugi, Ryokan, "
                  "Zugfahrt, Reiseteil …). Organisator:innen schreiben damit direkt in die Ontologie der Reise (plan/arten.yaml): "
                  "gilt sofort, die Seite zeigt es in wenigen Minuten. Mitwirkende schlagen damit vor (wird eine Rückmeldung). "
                  "Vorher kurz bestätigen lassen, was genau eingetragen wird; beim Anlegen fragen, was zu jeder Sache dieser Art "
                  "bekannt sein muss, und die Merkmale danach mit merkmal_definieren anlegen. Eine Art hat genau eine Grundform: "
                  "aufenthalt (an einem Ort sein, übernachten), bewegung (von Ort zu Ort), folge (ein Abschnitt aus mehreren Tagen). "
                  "Die Grundform lässt sich später nicht ändern.",
                  "inputSchema": {"type": "object", "properties": {
                      "art": {"type": "string", "description": "Schlüssel der Art (klein, ohne Umlaute, z. B. refugi); leer: aus der "
                              "Bezeichnung. Zum Ändern den vorhandenen Schlüssel (aus merkmale)"},
                      "bezeichnung": {"type": "string", "description": "Anzeigename, z. B. Refugi (beim Anlegen nötig)"},
                      "grundform": {"type": "string", "enum": list(GRUNDFORMEN), "description": "beim Anlegen nötig"},
                      "farbe": {"type": "string", "enum": list(FARBEN),
                                "description": "Farbe auf Karte, Legende und Vergleich; Aufenthalte bekommen sonst die nächste freie"},
                      "beschreibung": {"type": "string", "description": "ein Satz, was diese Art bei dieser Reise meint"},
                      "summiert": {"type": "boolean", "description": "nur Bewegung aus eigener Kraft (Wandern, Rad): Gehzeit, Länge, "
                                   "Höhenmeter werden summiert und als berechnete Merkmale angelegt"},
                      "grund": {"type": "string", "description": "warum (steht im Verlauf)"},
                      "name": NAME_FELD}}}
KATEGORIE_DEFINIEREN = {"name": "kategorie_definieren", "description": "Eine Kategorie der Kartenpunkte dieser Reise anlegen oder ändern "
                        "(z. B. Einkehr, Wasser, Schauplatz, Bahnhof): Name in der Legende, Farbe, Symbol und, was ein art-Wort der Punkte "
                        "(z. B. quelle, hotel) auf der Karte heißt. Gruppe punkt gehört zur Etappen-Karte, wissen zur Karte in einem "
                        "Wissensabschnitt. Organisator:innen schreiben direkt (plan/kategorien.yaml, gilt sofort, Seite in wenigen Minuten), "
                        "Mitwirkende schlagen vor. Punkte mit einer Kategorie, die die Reise nicht kennt, lassen den Bau scheitern: erst "
                        "die Kategorie anlegen. Vorher kurz bestätigen lassen, was genau eingetragen wird.",
                        "inputSchema": {"type": "object", "properties": {
                            "kategorie": {"type": "string", "description": "Schlüssel (klein, ohne Umlaute, z. B. einkehr)"},
                            "bezeichnung": {"type": "string", "description": "Name in der Legende, Mehrzahl bei Punkten (beim Anlegen nötig)"},
                            "einzahl": {"type": "string", "description": "Name für einen einzelnen Punkt, falls anders"},
                            "gruppe": {"type": "string", "enum": ["punkt", "wissen"], "description": "beim Anlegen nötig; später nicht änderbar"},
                            "farbe": {"type": "string", "description": "blau, braun, lila, gruen, tuerkis, oliv, grau, rosa, schiefer, kontrast "
                                      "(Schriftfarbe der Seite) oder #rrggbb (beim Anlegen nötig)"},
                            "symbol": {"type": "string", "description": "Symbol im Punkt, eines der Seite (z. B. einkehr, wasser, unterkunft, bus)"},
                            "nummeriert": {"type": "boolean", "description": "der Punkt zeigt seine Nummer (nr) statt eines Symbols"},
                            "art": {"type": "string", "description": "nur für Angaben zu einem art-Wort der Punkte dieser Kategorie (z. B. quelle)"},
                            "art_bezeichnung": {"type": "string", "description": "Name dieser art auf der Karte"},
                            "art_symbol": {"type": "string", "description": "Symbol dieser art"},
                            "art_hinweis": {"type": "string", "description": "Satz im Popup dieser art, z. B. Trinkbarkeit ungeprüft"},
                            "art_umriss": {"type": "boolean", "description": "Punkt dieser art als Umriss statt gefüllt (für Ungeprüftes)"},
                            "grund": {"type": "string", "description": "warum (steht im Verlauf)"},
                            "name": NAME_FELD}}}
MERKMAL_DEFINIEREN = {"name": "merkmal_definieren", "description": "Ein Merkmal einer Art dieser Reise anlegen oder ändern: "
                      "umbenennen, Typ und Werte, veränderlich (braucht dann ein Prüfdatum), Stufe (nötig | gut zu wissen | zusätzlich; "
                      "aus schaltet es für diese Reise ab), Hilfe zum Recherchieren, Frage an die Person, weitere Namen. "
                      "Organisator:innen schreiben damit direkt (gilt sofort, Seite in wenigen Minuten), Mitwirkende schlagen vor. "
                      "Vorher merkmale aufrufen (kein Doppeltes anlegen) und kurz bestätigen lassen, was genau eingetragen wird.",
                      "inputSchema": {"type": "object", "properties": {
                          "art": {"type": "string", "description": "Schlüssel der Art, z. B. refugi (aus merkmale)"},
                          "merkmal": {"type": "string", "description": "Schlüssel des Merkmals (klein, z. B. stornierung); leer: aus "
                                      "der Bezeichnung. Zum Ändern den vorhandenen Schlüssel"},
                          "bezeichnung": {"type": "string", "description": "Anzeigename, z. B. Stornierung (beim Anlegen nötig)"},
                          "typ": {"type": "string", "enum": sorted(TYPEN), "description": "Vorgabe text; auswahl braucht werte"},
                          "werte": {"type": "array", "items": {"type": "string"}, "description": "mögliche Antworten bei typ auswahl, "
                                    "z. B. [kostenlos, gegen Gebühr, nicht möglich, unklar]"},
                          "veraenderlich": {"type": "boolean", "description": "Preise, Zeiten, Öffnungszeiten: der Wert braucht ein Prüfdatum"},
                          "stufe": {"type": "string", "enum": list(STUFEN), "description": "Für die Person heißen sie: pflicht = "
                                    "„nötig“ (ohne Wert eine Lücke, „Fehlt noch“), empfohlen = „gut zu wissen“ (Vorgabe; Spalte im "
                                    "Vergleich, ohne Wert keine Mahnung), angeboten = „zusätzlich“ (nur mit Wert sichtbar, im Vergleich "
                                    "aufgeklappt); aus gilt für diese Reise nicht und wird nicht genannt"},
                          "einheit": {"type": "string", "description": "hinter Zahlen, z. B. km oder h"},
                          "hilfe": {"type": "string", "description": "wie man den Wert findet (Website, Buch, Anruf)"},
                          "frage": {"type": "string", "description": "wonach die Person gefragt wird, wenn der Wert fehlt"},
                          "auch": {"type": "array", "items": {"type": "string"}, "description": "weitere Namen, unter denen dasselbe gemeint ist"},
                          "trotzdem": {"type": "boolean", "description": "true, wenn ein ähnliches Merkmal gemeldet wurde und es wirklich "
                                       "ein anderes ist"},
                          "grund": {"type": "string", "description": "warum (steht im Verlauf)"},
                          "name": NAME_FELD},
                          "required": ["art"]}}
MERKMALE_FELD = {"type": "object", "description": "{merkmal: wert | {wert, quelle, geprueft, gilt, notiz} | [solche je Datum]}; Schlüssel aus merkmale "
                 "(ein unbekanntes Merkmal legt ein:e Organisator:in erst mit merkmal_definieren an); quelle und geprueft dürfen auch oben stehen",
                 "additionalProperties": True}
QUELLE_FELD = {"type": "string", "description": "Herkunft: Website mit Adresse, Buch mit Seite, Anruf, „Name im Gespräch“ (Pflicht)"}
DING_ANLEGEN = {"name": "ding_anlegen", "description": "Eine Unterkunft, einen Aufenthalt ohne Nacht (Besichtigung, Essen, Besuch), eine "
                "Strecke oder einen Ort in der Reise anlegen (neue ID). Schreibt sofort; Herkunft (quelle) ist Pflicht. Unterkunft und Aufenthalt "
                "brauchen ort (O-…) und art (Aufenthalts-Art der Reise), eine Strecke von, nach und art (Bewegungs-Art). Merkmale (Preis, "
                "Frühstück …) gleich mit; veränderliche mit geprueft. Ein Aufenthalt gehört danach an einen Tag (tag_aendern, aufenthalte), "
                "eine Unterkunft als Alternative mit option_anlegen an die Wahlstelle. Vorher kurz bestätigen lassen.",
                "inputSchema": {"type": "object", "properties": {
                    "was": {"type": "string", "enum": ["unterkunft", "aufenthalt", "strecke", "ort"]},
                    "titel": {"type": "string", "description": "Name der Unterkunft, des Aufenthalts oder des Orts, Titel der Strecke"},
                    "ort": {"type": "string", "description": "Unterkunft, Aufenthalt: Ort O-… (fehlt er, erst mit ding_anlegen was=ort anlegen)"},
                    "zeit": {"type": "string", "description": "Aufenthalt: wann, als Text („10–12 Uhr“, „abends“)"},
                    "buchung": {"type": "string", "description": "Buchungsstand, z. B. gebucht oder offen; Vorgabe offen bei buchbarer Art"},
                    "von": {"type": "string", "description": "Strecke: Start O-…"}, "nach": {"type": "string", "description": "Strecke: Ziel O-…"},
                    "art": {"type": "string", "description": "Art dieser Reise (Schlüssel aus merkmale), z. B. pension oder bus"},
                    "hinweis": {"type": "string"}, "buchungslink": {"type": "string", "description": "Unterkunft: Adresse zum Buchen"},
                    "frage": {"type": "string", "description": "Unterkunft: offene Frage F-…, zu der sie gehört"},
                    "merkmale": MERKMALE_FELD, "quelle": QUELLE_FELD, "geprueft": {"type": "string", "description": "Prüfdatum für die Merkmale, JJJJ-MM-TT"},
                    "name": NAME_FELD},
                    "required": ["was", "titel", "quelle"]}}
DING_AENDERN = {"name": "ding_aendern", "description": "Felder einer Unterkunft (name, ort, art, hinweis, quelle, buchungslink, frage, buchung), "
                "eines Aufenthalts ohne Nacht (dazu zeit), einer Strecke (titel, von, nach, art, hinweis, quelle, buchung) oder eines Orts (name, "
                "hinweis, quelle) ändern; schreibt sofort, der alte Wert bleibt im Verlauf. buchung ist der Buchungsstand („gebucht“, „offen“, "
                "„Zeitfenster 10 Uhr“), er steht auf der Seite unter Zu buchen. Merkmale ändert wert_eintragen. Die Art ändern dürfen nur "
                "Organisator:innen. Leerer Text entfernt hinweis, buchungslink, frage, zeit oder buchung.",
                "inputSchema": {"type": "object", "properties": {
                    "ziel": {"type": "string", "description": "U-…, A-…, E-… oder O-…"}, "zeit": {"type": "string"}, "buchung": {"type": "string"},
                    "name": {"type": "string", "description": "neuer Name (Unterkunft, Ort)"}, "titel": {"type": "string", "description": "neuer Titel (Strecke)"},
                    "ort": {"type": "string"}, "von": {"type": "string"}, "nach": {"type": "string"}, "art": {"type": "string"},
                    "hinweis": {"type": "string"}, "quelle": {"type": "string"}, "buchungslink": {"type": "string"}, "frage": {"type": "string"},
                    "grund": {"type": "string", "description": "warum (steht im Verlauf)"}, "vorname": NAME_FELD},
                    "required": ["ziel"]}}
LAGE_EINTRAGEN = {"name": "lage_eintragen", "description": "Lage einer Unterkunft eintragen: Adresse (Straße Nr., PLZ Ort) und/oder "
                  "Koordinaten (Breite, Länge). Jede Unterkunft im Plan braucht eine Lage; die Seite verlinkt sie mit Google Maps "
                  "(und Apple Karten). Herkunft (quelle) ist Pflicht, z. B. Website des Hauses oder OpenStreetMap. Schreibt sofort; "
                  "vorher kurz bestätigen lassen.",
                  "inputSchema": {"type": "object", "properties": {
                      "ziel": {"type": "string", "description": "U-…"},
                      "adresse": {"type": "string", "description": "Postadresse, z. B. „Carrer de sa Lluna 21, 07100 Sóller“"},
                      "koordinaten": {"type": "string", "description": "„Breite, Länge“ in Grad, z. B. „39.7671, 2.7149“"},
                      "quelle": QUELLE_FELD, "geprueft": {"type": "string", "description": "Datum des Nachschlagens, JJJJ-MM-TT (Vorgabe heute)"},
                      "grund": {"type": "string"}, "vorname": NAME_FELD},
                      "required": ["ziel", "quelle"]}}
OPTION_FELDER = {"titel": {"type": "string", "description": "Name der Option, z. B. „Pension Elbblick“"},
                 "text": {"type": "string", "description": "kurze Beschreibung"},
                 "unterkuenfte": {"type": "array", "items": {"type": "string"}, "description": "U-… (Aufenthalt); fehlt die Unterkunft, erst ding_anlegen"},
                 "strecken": {"type": "array", "items": {"type": "string"}, "description": "E-… (Bewegung)"},
                 "folge": {"type": "array", "items": {"type": "string"}, "description": "T-… (Reiseteil aus Tagen)"},
                 "plus": {"type": "array", "items": {"type": "string"}, "description": "was dafür spricht"},
                 "minus": {"type": "array", "items": {"type": "string"}, "description": "was dagegen spricht"},
                 "erfordert": {"type": "array", "items": {"type": "string"}, "description": "Optionen V-01.b anderer Wahlstellen, die dazu nötig sind"},
                 "schliesst_aus": {"type": "array", "items": {"type": "string"}, "description": "Optionen, die nie zusammen mit dieser gehen"},
                 "ausloeser": {"type": "string", "description": "bei Wahlstellen unterwegs: wann diese Option gilt"},
                 "siehe": {"type": "string", "description": "ID mit mehr dazu, z. B. W-05"},
                 "merkmale": MERKMALE_FELD, "quelle": {"type": "string", "description": "woher die Alternative stammt; Vorgabe: Vorschlag der Person im Gespräch"},
                 "grund": {"type": "string", "description": "warum sie vorgeschlagen wird (Verlauf)"}}
OPTION_ANLEGEN = {"name": "option_anlegen", "description": "Eine Alternative als Option an eine bestehende Wahlstelle hängen (ein weiteres Hotel, "
                  "eine andere Strecke, eine andere Route), Status vorgeschlagen; schreibt sofort. Erst merkmale aufrufen und recherchieren, "
                  "Unterkunft oder Strecke mit ding_anlegen anlegen, dann kurz bestätigen lassen. Entscheiden bleibt bei den Organisator:innen.",
                  "inputSchema": {"type": "object", "properties": {"wahlstelle": {"type": "string", "description": "V-… (aus varianten)"},
                                                                   **OPTION_FELDER, "name": NAME_FELD},
                                  "required": ["wahlstelle", "titel"]}}
WAHLSTELLE_ANLEGEN = {"name": "wahlstelle_anlegen", "description": "Eine neue Wahlstelle mit mindestens einer Option anlegen, wenn es noch keine "
                      "gibt (varianten zeigt alle). Sie hängt mit an an Tagen, Strecken, Unterkünften, Orten oder Abschnitten; den Plan "
                      "selbst ändert sie nicht. planung: vor der Abreise entscheiden (offen braucht eine Frage F-…); unterwegs: mit Auslöser. "
                      "Schreibt sofort, alle Optionen vorgeschlagen.",
                      "inputSchema": {"type": "object", "properties": {
                          "titel": {"type": "string"}, "art": {"type": "string", "enum": ["planung", "unterwegs"]},
                          "an": {"type": "array", "items": {"type": "string"}, "description": "IDs, an denen die Wahl hängt (T-…, E-…, U-…, O-…, W-…)"},
                          "bereich": {"type": "string", "description": "Art der Dinge, zwischen denen gewählt wird (Schlüssel aus merkmale); sonst aus den Optionen"},
                          "frage": {"type": "string", "description": "offene Frage F-… dazu"}, "text": {"type": "string"},
                          "optionen": {"type": "array", "items": {"type": "object", "properties": OPTION_FELDER, "required": ["titel"]}},
                          "name": NAME_FELD},
                          "required": ["titel", "optionen"]}}
FRAGE_ANLEGEN = {"name": "frage_anlegen", "description": "Eine offene Frage (F-…) anlegen: etwas, das noch zu klären oder zu entscheiden "
                 "ist (Aufgaben sind Dinge, die zu tun sind: aufgabe_anlegen). Schreibt sofort nach offene-fragen.md. Vorher kurz bestätigen lassen.",
                 "inputSchema": {"type": "object", "properties": {
                     "text": {"type": "string", "description": "die Frage in einem Satz"},
                     "bis": {"type": "string", "description": "bis wann zu klären, z. B. „vor Abreise“ oder ein Datum"},
                     "bezug": {"type": "array", "items": {"type": "string"}, "description": "IDs, zu denen die Frage gehört (T-, U-, E-, V-, W-)"},
                     "name": NAME_FELD}, "required": ["text"]}}
TAG_AENDERN = {"name": "tag_aendern", "description": "Nur für Organisator:innen: einen Tag des Plans ändern: Titel, Text, die Nacht (Unterkunft "
               "U-…, Wahlstelle V-… oder leer), die Strecken (E-… oder Wahlstellen V-…), Wahlstellen unterwegs (wahl), Aufenthalte ohne Nacht "
               "(aufenthalte: A-…, in der Zeitleiste des Tags). So wird z. B. eine feste "
               "Unterkunft zur Wahl zwischen mehreren (nacht = die neue Wahlstelle). Schreibt sofort; der Generator prüft, ob der Plan aufgeht. "
               "Vorher kurz bestätigen lassen.",
               "inputSchema": {"type": "object", "properties": {
                   "ziel": {"type": "string", "description": "T-…"}, "titel": {"type": "string"}, "text": {"type": "string"},
                   "nacht": {"type": "string", "description": "U-…, V-…, O-… oder leer"},
                   "strecken": {"type": "array", "items": {"type": "string"}}, "wahl": {"type": "array", "items": {"type": "string"}},
                   "aufenthalte": {"type": "array", "items": {"type": "string"}, "description": "A-… in der Reihenfolge des Tags"},
                   "grund": {"type": "string", "description": "warum (steht im Verlauf)"}, "vorname": NAME_FELD},
                   "required": ["ziel"]}}
WISSEN_SCHREIBEN = {"name": "wissen_schreiben", "description": "Wissen zur Reise festhalten (Geschichte, Natur, Praxis, Quellen): einen "
                    "neuen Abschnitt anlegen (titel) oder einen vorhandenen ergänzen (abschnitt = W-ID). In eigenen Worten, nie Buchtext "
                    "abschreiben; die Herkunft (quelle) ist Pflicht und steht am Absatz. Schreibt sofort. Vorher kurz bestätigen lassen.",
                    "inputSchema": {"type": "object", "properties": {
                        "titel": {"type": "string", "description": "Titel eines neuen Abschnitts"},
                        "abschnitt": {"type": "string", "description": "W-ID eines vorhandenen Abschnitts, der ergänzt wird"},
                        "text": {"type": "string", "description": "der Text in eigenen Worten (Markdown erlaubt), max. 6000 Zeichen"},
                        "quelle": QUELLE_FELD,
                        "gruppe": {"type": "string", "enum": ["wissen", "praxis", "quelle"], "description": "neuer Abschnitt: Rubrik (Vorgabe wissen)"},
                        "datei": {"type": "string", "description": "neuer Abschnitt: Datei unter inhalt/ (Vorgabe inhalt/wissen.md)"},
                        "name": NAME_FELD}, "required": ["text", "quelle"]}}
FRAGE_SCHLIESSEN = {"name": "frage_schliessen", "description": "Nur für Organisator:innen: eine offene Frage (F-…) als geklärt oder entfallen "
                    "eintragen, mit Ergebnis in einem Satz. Schreibt sofort nach offene-fragen.md. Antworten von Mitwirkenden (frage_beantworten) "
                    "sind Eingaben; geklärt ist eine Frage erst damit.",
                    "inputSchema": {"type": "object", "properties": {
                        "frage": {"type": "string", "description": "F-…"},
                        "ergebnis": {"type": "string", "description": "was herausgekommen ist oder entschieden wurde"},
                        "status": {"type": "string", "enum": ["geklaert", "entfaellt"], "description": "Vorgabe geklaert"},
                        "vorname": NAME_FELD}, "required": ["frage", "ergebnis"]}}
RUECKMELDUNG_ERLEDIGEN = {"name": "rueckmeldung_erledigen", "description": "Nur für Organisator:innen: eine Rückmeldung oder einen Auftrag "
                          "(R-…, A-… aus rueckmeldungen) abschließen, nachdem der Inhalt mit den Werkzeugen eingetragen ist: Status "
                          "uebernommen (aufgenommen), verworfen (passt nicht) oder rueckfrage, mit einem Kommentar in einfachen Worten, "
                          "der auf der Seite steht (wo es gelandet ist oder warum nicht). Gilt sofort.",
                          "inputSchema": {"type": "object", "properties": {
                              "id": {"type": "string", "description": "R-… oder A-…"},
                              "status": {"type": "string", "enum": ["uebernommen", "verworfen", "rueckfrage"]},
                              "kommentar": {"type": "string", "description": "für die Person, die die Rückmeldung gab"},
                              "vorname": NAME_FELD}, "required": ["id", "status", "kommentar"]}}
REISE_STATUS_SETZEN = {"name": "reise_status_setzen", "description": "Nur für Organisator:innen: den Status der Reise wechseln (idee, planung, "
                       "fest, unterwegs, danach, archiv), mit Grund; schreibt sofort mit Verlauf in die Reise. Wächter und Seite melden den "
                       "fälligen Wechsel, wechseln ihn aber nie selbst. Vorher kurz bestätigen lassen.",
                       "inputSchema": {"type": "object", "properties": {
                           "status": {"type": "string", "enum": ["idee", "planung", "fest", "unterwegs", "danach", "archiv"]},
                           "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["status", "grund"]}}
EINSTELLUNG_SETZEN = {"name": "einstellung_setzen", "description": "Nur für Organisator:innen: Bausteine der Reise (vollständige Liste, z. B. "
                      "varianten, karte, tagesseiten, rueckmeldungen, fragen, aufgaben, wuensche, waechter) oder Spielregeln (regeln, z. B. einladen: "
                      "mitwirkend, waechter_frist_tage: 45) setzen; schreibt sofort, der alte Wert steht im Verlauf.",
                      "inputSchema": {"type": "object", "properties": {
                          "bausteine": {"type": "array", "items": {"type": "string"}},
                          "regeln": {"type": "object", "additionalProperties": True},
                          "grund": {"type": "string"}, "vorname": NAME_FELD}}}
BUCHUNG_FELDER_SCHEMA = {
    "status": {"type": "string", "enum": ["angefragt", "gebucht", "storniert"], "description": "Vorgabe gebucht"},
    "nummer": {"type": "string", "description": "Buchungsnummer, Buchungscode, PNR"},
    "bei": {"type": "string", "description": "wo gebucht: Anbieter oder Portal, z. B. booking.com, direkt per Mail, bahn.de"},
    "preis": {"type": "string", "description": "Gesamtpreis mit Währung und wofür, z. B. „240 € für 2 Nächte“"},
    "bezahlt": {"type": "string", "description": "was schon bezahlt ist, z. B. „Anzahlung 50 €, Rest vor Ort“"},
    "frist": {"type": "string", "description": "JJJJ-MM-TT: bis wann etwas zu tun ist (Restzahlung, Ticket laden); der Wächter erinnert"},
    "frist_was": {"type": "string", "description": "was bis zur Frist zu tun ist"},
    "storno": {"type": "string", "description": "Stornoregel in Worten, z. B. „kostenlos bis 7 Tage vorher, danach 1 Nacht“"},
    "storno_bis": {"type": "string", "description": "JJJJ-MM-TT: bis wann kostenlos stornierbar; der Wächter erinnert"},
    "gebucht_am": {"type": "string", "description": "JJJJ-MM-TT (Vorgabe heute)"},
    "notiz": {"type": "string"}}
BUCHUNG_ANLEGEN = {"name": "buchung_anlegen", "description": "Eine Buchung als eigenes Ding (B-…) eintragen: für welche Unterkunft (U-…), "
                   "welchen Aufenthalt (A-…) oder welche Strecke (E-…), Status, Buchungsnummer, Anbieter, Preis, Frist, Stornoregel. "
                   "Schreibt sofort; Herkunft (quelle) ist Pflicht, z. B. „Buchungsbestätigung per Mail vom …“. Liest die Person dir eine "
                   "Bestätigung vor oder zeigt sie dir, trägst du daraus Nummer, Frist und Stornoregel ein (vorher kurz bestätigen lassen). "
                   "Den Beleg selbst (PDF, Bild) hängt die Person angemeldet auf der Reiseseite bei der Buchung an; er liegt nie im Repo "
                   "und ist nur für sie und Organisator:innen sichtbar, bis eine Organisator:in ihn für alle freigibt.",
                   "inputSchema": {"type": "object", "properties": {
                       "fuer": {"type": "array", "items": {"type": "string"}, "description": "U-…, A-… oder E-…, eine oder mehrere"},
                       **BUCHUNG_FELDER_SCHEMA, "quelle": QUELLE_FELD, "grund": {"type": "string"}, "vorname": NAME_FELD},
                       "required": ["fuer", "quelle"]}}
BUCHUNG_AENDERN = {"name": "buchung_aendern", "description": "Felder einer Buchung B-… ändern (Status gebucht/storniert, Nummer, Frist, "
                   "Stornoregel, Preis …); schreibt sofort, jede Änderung steht mit Person, Datum und Grund im Verlauf. Leerer Text "
                   "entfernt ein Feld (z. B. frist: \"\" nach Erledigung). Mitwirkende ändern nur Buchungen, die sie selbst eingetragen "
                   "haben, Organisator:innen alle; Stornieren braucht einen Grund. Vorher kurz bestätigen lassen.",
                   "inputSchema": {"type": "object", "properties": {
                       "ziel": {"type": "string", "description": "B-…"},
                       "fuer": {"type": "array", "items": {"type": "string"}}, **BUCHUNG_FELDER_SCHEMA,
                       "quelle": {"type": "string", "description": "neue Herkunft, falls sie sich ändert"},
                       "grund": {"type": "string", "description": "warum (steht im Verlauf)"}, "vorname": NAME_FELD},
                       "required": ["ziel"]}}
WERT_SCHEMA_EINTRAG = {"type": "object", "properties": {
    "wert": {"type": "string"}, "gilt": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
             "description": "Datum JJJJ-MM-TT oder Liste, wenn der Wert nur für diese Tage gilt (Preis je Nacht)"},
    "geprueft": {"type": "string"}, "quelle": {"type": "string"}, "notiz": {"type": "string"}}, "required": ["wert"]}
WERT_EINTRAGEN = {"name": "wert_eintragen", "description": "Einen Wert eines Merkmals an einer Unterkunft (U-…), Strecke (E-…) oder "
                  "Option (V-01.a) eintragen: Preis, Frühstück, Öffnung, Dauer … Schreibt sofort in die Reise (gilt ab jetzt, Seite in "
                  "wenigen Minuten) und ersetzt den bisherigen Wert für dieselben Tage; der alte bleibt im Verlauf. Jede Angabe braucht "
                  "ihre Herkunft (quelle); veränderliche Merkmale (Preise, Zeiten, Öffnung) auch das Prüfdatum (geprueft, Datum des "
                  "Nachschlagens). Vorher merkmale aufrufen (welche Merkmale es an dieser Stelle gibt, erlaubte Auswahlwerte) und "
                  "kurz bestätigen lassen, was genau eingetragen wird. Mitwirkende und Organisator:innen.",
                  "inputSchema": {"type": "object", "properties": {
                      "ziel": {"type": "string", "description": "U-…, E-… oder V-01.a (aus ueberblick, zeige, merkmale)"},
                      "merkmal": {"type": "string", "description": "Schlüssel des Merkmals, z. B. preis (aus merkmale)"},
                      "wert": {"type": "string", "description": "der Wert, bei Auswahl einer der erlaubten Werte; bei Geld mit Währung"},
                      "quelle": {"type": "string", "description": "Herkunft: Website mit Adresse, Buch mit Seite, Anruf, „Name im Gespräch“"},
                      "geprueft": {"type": "string", "description": "Datum des Nachschlagens JJJJ-MM-TT (bei veränderlichen Merkmalen nötig)"},
                      "gilt": WERT_SCHEMA_EINTRAG["properties"]["gilt"],
                      "notiz": {"type": "string", "description": "Einschränkung, Rechnung, Widerspruch zwischen Quellen"},
                      "werte": {"type": "array", "items": WERT_SCHEMA_EINTRAG,
                                "description": "statt wert: mehrere Werte je Datum auf einmal (quelle und geprueft dürfen oben stehen)"},
                      "name": NAME_FELD},
                      "required": ["ziel", "merkmal"]}}


ENTSCHEIDEN = {"name": "entscheiden", "description": "Nur für Organisator:innen: im Gespräch über eine Option einer Wahlstelle entscheiden "
               "(gewaehlt, verworfen oder ersetzt). Erst varianten/zeige ansehen und den Grund mit der Person klären, dann kurz "
               "bestätigen lassen. Der Dienst prüft sofort: Gibt es die Option, ist der Status stimmig, ist ein Grund da, "
               "widerspricht es einer anderen Organisator:in? Unstimmiges lehnt er mit Begründung ab, Hinweise (fehlende oder "
               "ungeprüfte Merkmale) gibt er mit. Die Entscheidung steht sofort mit Datum, Person und Grund im Plan; die Seite "
               "zeigt sie in wenigen Minuten.",
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
                     "entscheidet ein:e Organisator:in. Vorher die Antwort mit der Person abstimmen; Herkunft nennen, Annahmen markieren.",
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
                                 "description": "gast liest; mitwirkend gibt Wünsche, Rückmeldungen, Aufgaben, Antworten; "
                                 "organisator entscheidet und lädt ein. Standard mitwirkend."},
                       "reist": {"type": "boolean", "description": "reist die Person mit? Standard ja (nein: gestaltet nur mit)"},
                       "notiz": {"type": "string", "description": "kurze Notiz zur Person, eine Zeile"},
                       "schluessel": {"type": "string", "description": "nur wenn nötig: Kurzname für den Zugang (klein, ohne Umlaute)"},
                       "name": NAME_FELD}, "required": ["vorname"]}}


PERSON_ENTFERNEN = {"name": "person_entfernen", "description": "Nur für Organisator:innen: eine Person aus der Reise nehmen. Ihr "
                    "Zugang (Konto und Links) endet sofort; Beiträge und Verlauf bleiben mit ihrem Namen stehen. Organisator:innen "
                    "und sich selbst nimmt man so nicht heraus. Vorher bestätigen lassen.",
                    "inputSchema": {"type": "object", "properties": {
                        "person": {"type": "string", "description": "Vorname oder Schlüssel der Person"},
                        "grund": {"type": "string", "description": "kurz, warum (optional, eine Zeile)"},
                        "name": NAME_FELD}, "required": ["person"]}}


REISE_ANLEGEN = {"name": "reise_anlegen", "description": "Eine neue Reise anlegen. "
                 "Vorher im Gespräch Titel, Zeitraum, Ziel und Personen mit Rollen klären und bestätigen lassen; wer anlegt, "
                 "bestimmt auf der neuen Reise. Was schon bekannt ist (Ideen, Unterkunft, Quellen), kommt in notiz: Bücher, "
                 "Fotos und PDFs in eigenen Worten zusammenfassen, mit Herkunft (Buch und Seite, Link), nie abschreiben. "
                 "Die Reise entsteht in wenigen Minuten im Status idee; danach zeigt meine_reisen eine Meldung mit dem Link "
                 "zur Seite und dem Link für die Claude-App. Sag nie, die Reise sei schon angelegt.",
                 "inputSchema": {"type": "object", "properties": {
                     "titel": {"type": "string", "description": "Titel der Reise, z. B. „Winterwoche im Allgäu“"},
                     "von": {"type": "string", "description": "erster Tag, JJJJ-MM-TT"},
                     "bis": {"type": "string", "description": "letzter Tag, JJJJ-MM-TT"},
                     "ziel": {"type": "string", "description": "Ziel oder Gegend, eine Zeile"},
                     "personen": {"type": "array", "description": "weitere Personen (die anlegende Person kommt von selbst "
                                  "als organisator dazu)", "items": {"type": "object", "properties": {
                                      "vorname": {"type": "string"},
                                      "rolle": {"type": "string", "enum": list(ROLLEN),
                                                "description": "gast liest; mitwirkend gibt Wünsche, Rückmeldungen, "
                                                "Aufgaben, Antworten; organisator entscheidet mit. Standard mitwirkend."},
                                      "reist": {"type": "boolean", "description": "reist mit? Standard ja"},
                                      "notiz": {"type": "string", "description": "kurze Notiz zur Person, eine Zeile"}},
                                      "required": ["vorname"]}},
                     "notiz": {"type": "string", "description": "was schon bekannt ist, in eigenen Worten mit Herkunft"},
                     "pfad": {"type": "string", "description": "nur wenn nötig: Ordnername (klein, Bindestriche)"}},
                     "required": ["titel", "von", "bis"]}}


def _mit_mail(w):
    """reise_anlegen im Konnektor „Frieda“: Personen mit E-Mail-Adresse, die eine Einladung bekommen."""
    import copy
    w = copy.deepcopy(w)
    w["description"] = w["description"].replace(
        "danach zeigt meine_reisen eine Meldung mit dem Link zur Seite und dem Link für die Claude-App",
        "danach steht sie in meine_reisen, und Personen mit E-Mail-Adresse bekommen eine Einladung per Mail")
    w["inputSchema"]["properties"]["personen"]["items"]["properties"]["email"] = EMAIL_FELD
    return w


REISE_ANLEGEN_MIT_MAIL = _mit_mail(REISE_ANLEGEN)


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
    wer = wer_spricht(zugang, d) or {"rolle": "gast", "name": None}
    organisator = organisator_namen(d)
    namen = " und ".join(organisator) or "Organisator:in"
    status = (rs.get("status") or {}).get("wert")
    bausteine = rs.get("bausteine")
    z = [f"Aufgabe: Du hilfst bei der Reise „{rs.get('titel', zugang['reise'])}“ ({rs.get('untertitel', '')})"
         + (f", Status {status}" if status else "") + ". Du liest vor, schlägst vor, prüfst und gibst Eingaben weiter; "
         f"{namen} {'entscheiden' if len(organisator) > 1 else 'entscheidet'}, du nie.",
         "Grenzen: Was du mit den Werkzeugen einträgst, prüft der Dienst nach Regeln und schreibt es sofort in die Reise; "
         "die Seite zeigt es in wenigen Minuten. Rückmeldungen (rueckmeldung_geben) und Antworten sind Eingaben, die eine "
         "Organisator:in einarbeitet. "
         + ("" if schreibdienst() else "Der Schreibweg dieser Instanz ist nicht eingerichtet: Eintragen geht nicht, nur Lesen, "
            "Rückmeldungen und Aufgaben. ")
         + "Status gewählt/verworfen/ersetzt und Einstellungen setzen nur Organisator:innen. Nichts erfinden: Herkunft nennen, Annahmen "
         "markieren, veränderliche Angaben (Fahrpläne, Öffnungszeiten, Preise) mit Prüfdatum. Vor jedem Eintragen kurz "
         "bestätigen lassen, was genau eingetragen wird. Die Regeln prüft der Dienst; lehnt er etwas ab, gib den Grund weiter.",
         "IDs: T- Tag, E- Etappe/Strecke, O- Ort, U- Unterkunft, A- Aufenthalt ohne Nacht, B- Buchung, V- Wahlstelle mit "
         "Optionen V-01.a, P- Plan, F- offene Frage, W- Wissen, AG- Aufgabe. Mit ueberblick beginnen, dann zeige/suche. " + SPRACHE,
         "Rollen: gast liest; mitwirkend gibt dazu Rückmeldungen, Antworten, Aufgaben und Vorschläge; organisator entscheidet "
         "dazu, setzt Status und Einstellungen und lädt ein."]
    name = f"Du sprichst mit {wer['name']}" if wer["name"] else "Du sprichst mit einer Person ohne festen Namen"
    regeln = rs.get("regeln") or {}
    einladen_ab = regeln.get("einladen") or VORGABEN["einladen"]
    kann_einladen = darf(wer["rolle"], einladen_ab)
    direkt = schreibdienst()
    if wer["rolle"] == "organisator":
        z.append(f"{name} (Organisator:in). Entscheidungen über Optionen einer Wahlstelle trägst du mit entscheiden ein (Option, "
                 "Status, Grund; vorher kurz bestätigen lassen). Sind mehrere Wahlstellen offen, fragst du sie einzeln nacheinander, "
                 "je Wahlstelle eine Frage mit den Möglichkeiten zur Auswahl (mit dem Fragewerkzeug der App, wenn es eins gibt). "
                 + ("Der Dienst prüft im selben Moment, lehnt Unstimmiges mit Begründung ab und schreibt die Entscheidung mit Datum, "
                    "Person und Grund in den Plan; sie gilt ab jetzt, die Seite zeigt sie in wenigen Minuten. " if direkt else
                    "Ohne eingerichteten Schreibweg geht Entscheiden nicht; der Betreiber richtet ihn ein. ")
                 + "Widerspricht sie der einer anderen Organisator:in, wird daraus eine offene Frage, und alle Beteiligten bekommen "
                 "eine Meldung. Personen lädst du mit "
                 + ("person_einladen und ihrer E-Mail-Adresse ein (die Rolle gilt sofort, die Einladung kommt per Mail); "
                    "mit person_entfernen nimmst du jemanden heraus. " if "konto_id" in zugang else
                    "person_einladen ein (Rolle und Link gelten sofort). ")
                 + "Den Stand zeigt rueckmeldungen."
                 + (" Du schreibst direkt in die Reise, geprüft von Regeln: Arten und Merkmale (art_definieren, merkmal_definieren; bei einer "
                    "neuen Art fragen, was zu jeder Sache bekannt sein muss und was sich ändern kann), Kartenkategorien (kategorie_definieren), Werte mit Herkunft und Prüfdatum "
                    "(wert_eintragen; erst selbst recherchieren, merkmale sagt wo), Unterkünfte, Strecken, Orte (ding_anlegen, ding_aendern), "
                    "Alternativen (option_anlegen, wahlstelle_anlegen), der Plan eines Tags (tag_aendern), Wissen in eigenen Worten mit "
                    "Herkunft (wissen_schreiben), Fragen (frage_anlegen, frage_beantworten, frage_schliessen), Buchungen als eigenes Ding "
                    "mit Nummer, Frist und Stornoregel (buchung_anlegen, buchung_aendern; den Beleg hängt die Person auf der Reiseseite an), "
                    "Status und Einstellungen "
                    "(reise_status_setzen, einstellung_setzen). Rückmeldungen der Seite arbeitest du ein: prüfen, eintragen, dann "
                    "rueckmeldung_erledigen mit Kommentar in einfachen Worten. Vor jedem Eintragen den Wortlaut bestätigen lassen."
                    if direkt else ""))
    elif wer["rolle"] == "mitwirkend":
        z.append(f"{name} (Mitwirkende:r). Ihre Hinweise sind Vorschläge, keine Entscheidungen: Entscheiden "
                 f"kann sie nicht, das bleibt bei {namen}. Offene Fragen beantwortet sie mit frage_beantworten. "
                 + ("Sie schreibt direkt in die Reise: Werte mit Herkunft und Prüfdatum (wert_eintragen), Unterkünfte, Strecken, Orte "
                    "(ding_anlegen, ding_aendern), Alternativen als Vorschlag (option_anlegen, wahlstelle_anlegen), Wissen in eigenen Worten "
                    "mit Herkunft (wissen_schreiben), Fragen (frage_anlegen), Buchungen, die sie selbst gemacht hat (buchung_anlegen, "
                    "buchung_aendern; den Beleg hängt sie auf der Reiseseite an). Arten und Merkmale schlägt sie mit art_definieren und "
                    "merkmal_definieren vor (wird eine Rückmeldung). " if direkt else "")
                 + ("Sie darf Personen einladen (person_einladen), höchstens mit der Rolle mitwirkend. " if kann_einladen else "")
                 + ("" if wer["name"] else "Für Rückmeldungen und Aufgaben brauchst du ihren Vornamen: einmal fragen, "
                    "nicht raten, dann im Gespräch beibehalten. ")
                 + "„Meine Aufgaben“ = aufgaben mit zustaendig = dieser Vorname.")
    else:
        z.append(f"{name} (Rolle gast): nur lesen. Rückmeldungen, Antworten, Aufgaben und Vorschläge gehen mit diesem Zugang "
                 "nicht; wer mitgestalten will, bittet ein:e Organisator:in um eine andere Rolle."
)
    if status in STATUS_SATZ:
        z.append("Status: " + STATUS_SATZ[status])
    aus = [b for b in ("varianten", "fragen", "aufgaben", "rueckmeldungen", "wuensche") if bausteine is not None and b not in bausteine]
    if wer["name"] is None and wer["rolle"] != "gast":
        z.append("Dieser Link gehört keiner Person: Entscheiden und Einladen gehen nur mit einem persönlichen Link.")
    if aus:
        z.append("Bei dieser Reise ausgeschaltet (Werkzeuge fehlen, Daten bleiben): " + ", ".join(aus) + ".")
    if bausteine is None or "varianten" in bausteine:
        z.append("Alternativen (eine weitere Unterkunft, Strecke, Route): erst merkmale aufrufen, die Merkmale selbst "
                 "recherchieren, dann gezielt nur nach Lücken fragen, dann anlegen (ding_anlegen, option_anlegen; neue Wahlstelle: "
                 "wahlstelle_anlegen).")
    if bausteine is None or "waechter" in bausteine:
        z.append("Wächter und Erinnerer sind an: Meldungen an die Person (Fristen, ab-Termine, Statuswechsel, Prüfungen "
                 "veränderlicher Angaben) stehen im ueberblick unter „Meldungen an dich“. Nenne sie zu Beginn und frag, ob "
                 "etwas davon erledigt werden soll. Den Reisestatus wechselt nur ein:e Organisator:in, nie du.")
    if "wuensche" in (bausteine or []):
        z.append("Wünsche (Ort, Erlebnis, Essen, auch vage) hältst du mit rueckmeldung_geben, art Wunsch, fest; wuensche zeigt "
                 "das Brett. Mit wunsch_aendern: Punkte (wie wichtig) nur auf eigene Wünsche, abhaken unterwegs alle, "
                 "einplanen nur Organisator:innen. Ein Wunsch ist ein Vorschlag, keine Entscheidung.")
    return " ".join(z)


def werkzeug(zugang, name, args):
    """-> (text, ist_fehler)"""
    reise = zugang["reise"]
    args = args if isinstance(args, dict) else {}
    wer = wer_spricht(zugang, daten(reise))
    if wer is None:
        return "Dieser Zugang gehört zu keiner Person der Reise (mehr). Ein:e Organisator:in um einen neuen Link bitten.", True
    organisator = darf(wer["rolle"], "organisator")
    d = daten(reise)
    # Regeln prüft die Maschine, bei jedem Aufruf (nicht nur beim Anzeigen der Werkzeuge): Rolle, Baustein, Status
    status, bausteine = zustand_von(d)
    if name in LESE_BAUSTEIN and bausteine is not None and LESE_BAUSTEIN[name] not in bausteine:
        return f"Der Baustein „{LESE_BAUSTEIN[name]}“ ist bei dieser Reise ausgeschaltet.", True
    if name in ONTOLOGIE_WERKZEUGE:
        return ontologie_werkzeug(reise, d, wer, zugang, name, args)
    aktion = SCHREIB_AKTION.get(name)
    if aktion == "rueckmeldung" and str(args.get("art")) == "Wunsch":
        aktion = "wunsch"
    if aktion and (nein := recht(wer["rolle"], d, aktion, str(args.get("ziel") or "").strip() or None)):
        return nein, True
    if name == "rueckmeldungen":
        return liste_text(reise, organisator, wer["name"], d), False
    if name == "rueckmeldung_erledigen":
        rid = str(args.get("id") or "").strip()
        if not (rm.RID_MUSTER.match(rid) or AID_MUSTER.match(rid)):
            return "id muss R-… oder A-… sein (aus rueckmeldungen).", True
        kommentar = str(args.get("kommentar") or "").strip()
        if not kommentar:
            return "Der Kommentar fehlt: in einfachen Worten, wo die Rückmeldung gelandet ist oder warum sie nicht passt.", True
        name_ = wer["name"] or args.get("vorname")
        if not isinstance(name_, str) or not name_.strip():
            return "Name fehlt: bitte die Person nach ihrem Vornamen fragen.", True
        a, fehler = dienst_anfrage("PATCH", f"{reise}/rueckmeldungen/{rid}", {"status": str(args.get("status") or ""), "kommentar": kommentar,
                                                                               "name": name_.strip()})
        if fehler:
            return f"Nicht gesetzt: {fehler}", True
        return (f"{rid} ist jetzt {a['status']} („{kommentar}“). Die Seite zeigt es der Person nach dem nächsten Laden; nichts weiter zu tun, "
                "wenn der Inhalt schon eingetragen ist."), False
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
        return (f"Gespeichert als {antwort['id']} (Status neu). Eine Organisator:in sieht es unter rueckmeldungen, trägt es ein "
                "und schließt es mit rueckmeldung_erledigen ab."), False
    d = daten(reise)
    if d is None:
        return "Die Seite dieser Reise ist noch nicht veröffentlicht.", True
    h = Handbuch(d, aufgaben_von(reise), offene_entscheidungen(reise), antworten_von(reise),
                 meldungen_fuer(reise, wer["name"], d), belege_von(reise, wer))
    if name == "entscheiden":
        return entscheiden(reise, d, h, {**wer, "person": zugang.get("person")}, args)
    if name == "frage_beantworten":
        return frage_beantworten(reise, d, h, wer, args)
    if name == "person_einladen":
        return einladen(reise, d, {**wer, "person": zugang.get("person")}, args, mit_konto="konto_id" in zugang)
    if name == "person_entfernen":
        return person_entfernen(reise, d, {**wer, "person": zugang.get("person")}, args)
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
    if name == "wuensche":
        o = rm.ordner(reise)
        return (brett_text(rm.brett(o, rm.zustand(reise)), h.titel()) if o else "Noch keine Wünsche."), False
    if name == "wunsch_aendern":
        rid = str(args.get("id", "")).strip()
        if not rm.RID_MUSTER.match(rid):
            return "ID muss R-… sein (aus wuensche).", True
        roh = {k: args[k] for k in ("punkte", "erlebt", "eingeplant", "bezug", "kommentar") if k in args}
        if "eingeplant" in roh and not (wer["name"] and organisator):
            return ("Einplanen geht nur für Organisator:innen mit dem persönlichen Link: Es ist eine Entscheidung, und dieser Link "
                    "kennt keinen Namen." if organisator else "Einplanen dürfen nur Organisator:innen."), True
        roh["name"] = wer["name"] or args.get("name", "")
        if not isinstance(roh["name"], str) or not roh["name"].strip():
            return "Name fehlt: bitte die Person nach ihrem Vornamen fragen.", True
        unbekannt = [b for b in (roh.get("bezug") or []) if isinstance(b, str) and b not in h.eintraege]
        if unbekannt:
            return f"Diese IDs gibt es nicht: {', '.join(unbekannt)}. Mit suche die richtige ID finden.", True
        w, fehler = dienst_anfrage("PATCH", f"{reise}/rueckmeldungen/{rid}", roh)
        if fehler:
            return f"Nicht gespeichert: {fehler}", True
        teile = [f"{w['punkte']} Punkte"] + (["eingeplant"] if w.get("eingeplant") else []) + (["erlebt"] if w.get("erlebt") else [])
        return f"Gespeichert (gilt sofort): {rid} – " + ", ".join(teile) + ".", False
    if name == "ueberblick":
        return (h.ueberblick() + "\n" + stand_text(reise)
                + (wuensche_kurz(reise) if "wuensche" in (zustand_von(d)[1] or []) else "")), False
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

    if "konto_id" in zugang:
        return frieda_antwort(zugang, nid, methode, p, ok)
    if "konto" in zugang:
        return konto_antwort(zugang, nid, methode, p, ok)
    if methode == "initialize":
        gewuenscht = p.get("protocolVersion") if isinstance(p, dict) else None
        rs = (daten(zugang["reise"]) or {}).get("reise", {})
        return ok({"protocolVersion": gewuenscht if gewuenscht in PROTOKOLLE else PROTOKOLLE[0],
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": f"frieda-{zugang['reise']}", "title": rs.get("titel", "Frieda Reist"),
                                  "version": "1", **({"icons": ik} if (ik := symbole(zugang["reise"])) else {})},
                   "instructions": anleitung(zugang, daten(zugang["reise"]))})
    if methode == "ping":
        return ok({})
    if methode == "tools/list":
        return ok({"tools": werkzeuge_fuer(zugang)})
    if methode == "tools/call":
        t, fehler = werkzeug(zugang, p.get("name"), p.get("arguments"))
        return ok({"content": [{"type": "text", "text": t}], "isError": fehler})
    return {"jsonrpc": "2.0", "id": nid, "error": {"code": -32601, "message": f"unbekannt: {methode}"}}


def werkzeuge_fuer(zugang):
    """Werkzeuge, die dieser Zugang sieht: was die Rolle bei diesem Status und diesen Bausteinen darf (aufgerufen wird
    trotzdem noch einmal geprüft)."""
    d = daten(zugang["reise"])
    wer = wer_spricht(zugang, d) or {"rolle": "gast"}
    _, bausteine = zustand_von(d)
    werkzeuge = []
    ontologie = [ART_DEFINIEREN, MERKMAL_DEFINIEREN, KATEGORIE_DEFINIEREN, WERT_EINTRAGEN, DING_ANLEGEN, DING_AENDERN, LAGE_EINTRAGEN, OPTION_ANLEGEN, WAHLSTELLE_ANLEGEN,
                 FRAGE_ANLEGEN, TAG_AENDERN, WISSEN_SCHREIBEN, FRAGE_SCHLIESSEN, REISE_STATUS_SETZEN, EINSTELLUNG_SETZEN,
                 BUCHUNG_ANLEGEN, BUCHUNG_AENDERN] if schreibdienst() else []
    for w in WERKZEUGE + [ENTSCHEIDEN, FRAGE_BEANTWORTEN, PERSON_EINLADEN, PERSON_ENTFERNEN, RUECKMELDUNG_ERLEDIGEN] + ontologie:
        n = w["name"]
        if n in LESE_BAUSTEIN and bausteine is not None and LESE_BAUSTEIN[n] not in bausteine:
            continue
        if n in ONTOLOGIE_WERKZEUGE:   # direkt schreiben; Arten und Merkmale schlagen Mitwirkende vor (als Rückmeldung)
            a = ONTOLOGIE_AKTION[n]
            if recht(wer["rolle"], d, a) is None or (a == "ontologie" and recht(wer["rolle"], d, "rueckmeldung") is None):
                werkzeuge.append(w)
            continue
        if n in SCHREIB_AKTION:
            aktionen = ["rueckmeldung", "wunsch"] if n == "rueckmeldung_geben" else [SCHREIB_AKTION[n]]
            if not any(recht(wer["rolle"], d, a) is None for a in aktionen):
                continue
            if n in ZUSATZ_AKTION and recht(wer["rolle"], d, ZUSATZ_AKTION[n]) is not None:
                continue
        if n == "rueckmeldung_geben" and recht(wer["rolle"], d, "wunsch") is not None:
            art = {**w["inputSchema"]["properties"]["art"], "enum": [a for a in rm.ARTEN if a != "Wunsch"]}
            w = {**w, "inputSchema": {**w["inputSchema"], "properties": {**w["inputSchema"]["properties"], "art": art}}}
            w["inputSchema"]["properties"]["art"]["enum"].sort()
        werkzeuge.append(w)
    return werkzeuge


def gesund():
    """-> (HTTP-Code, Antwort). Verrät weder Tokens noch Reisen. Bereit, wenn jede freigeschaltete Reise (seiten.json) und
    jede Reise mit altem Link veröffentlicht ist; ohne alte Links zählen nur die freigeschalteten."""
    try:
        reisen = {z.get("reise") for z in zugaenge().values() if "konto" not in z} | set(seitenlinks())
    except (OSError, ValueError, AttributeError):
        return 503, {"gesund": False}
    if not reisen or any(daten(r) is None for r in reisen):
        return 503, {"gesund": False}
    return 200, {"gesund": True}


class Dienst(BaseHTTPRequestHandler):
    server_version = "Frieda-Konnektor"
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

    def _marke(self, pfad):
        name, art = MARKE_DATEIEN[pfad]
        try:
            body = (MARKE / name).read_bytes()
        except OSError:
            return self._senden(404, {"fehler": "unbekannt"})
        self.send_response(200)
        self.send_header("Content-Type", art)
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _zugang(self):
        teile = self.path.split("?", 1)[0].strip("/").split("/")
        return zugang_zu(teile[0]) if len(teile) == 1 else None

    def _anmeldung(self):
        """Friedas Anmeldeseiten (engine/anmeldung.py, Paket J2) und OAuth-Endpunkte (engine/oauth.py, J3)."""
        body = b""
        if self.command == "POST":
            try:
                laenge = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                laenge = 0
            if laenge < 0 or laenge > MAX_BODY:
                return self._senden(413, {"fehler": "zu groß"})
            body = self.rfile.read(laenge)
        ip = self.client_address[0]
        if ip in ("127.0.0.1", "::1") and self.headers.get("X-Real-IP"):
            ip = self.headers["X-Real-IP"].strip()      # hinter nginx: echte Adresse für die Begrenzung
        if oauth.ist_unsere(self.path):
            code, kopf, inhalt = oauth.bearbeiten(self.command, self.path, self.headers, body, ip)
        else:
            code, kopf, inhalt = anmeldung.bearbeiten(self.command, self.path, self.headers, body, ip, reise_kurz)
        self.send_response(code)
        grund = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                 "Referrer-Policy": "same-origin",   # nicht no-referrer: dann schicken Browser „Origin: null“
                 "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; form-action 'self'; "
                                            "frame-ancestors 'none'; base-uri 'none'"}
        eigene = {k for k, _ in kopf}
        for k, v in [*((k, v) for k, v in grund.items() if k not in eigene), *kopf]:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(inhalt)))
        self.end_headers()
        self.wfile.write(inhalt)

    def do_GET(self):
        # Readiness für BetterStack ohne geheimen Link: Zugänge lesbar und jede verlinkte Reise veröffentlicht
        if self.path.split("?", 1)[0] == "/gesund":
            return self._senden(*gesund())
        if self.path.split("?", 1)[0] in MARKE_DATEIEN:
            return self._marke(self.path.split("?", 1)[0])
        if anmeldung.ist_unsere(self.path) or oauth.ist_unsere(self.path):
            return self._anmeldung()
        if self.path.split("?", 1)[0] == "/mcp":
            if not oauth.basis() or not konten.oauth_konto(oauth.bearer(self.headers) or ""):
                return self._senden(401, {"fehler": "Anmeldung nötig"}, {"WWW-Authenticate": oauth.www_authenticate()})
            return self._senden(405, {"fehler": "nur POST"}, {"Allow": "POST"})
        # Kein SSE-Kanal: der Dienst schickt nie von sich aus etwas (Streamable HTTP erlaubt 405).
        if self._zugang() is None:
            return self._senden(404, {"fehler": "unbekannt"})
        self._senden(405, {"fehler": "nur POST"}, {"Allow": "POST"})

    do_DELETE = do_GET

    def do_POST(self):
        if anmeldung.ist_unsere(self.path) or oauth.ist_unsere(self.path):
            return self._anmeldung()
        if self.path.split("?", 1)[0] == "/mcp":
            # Konnektor „Frieda“ (Paket J3): Bearer-Token aus OAuth; ohne gültiges 401 mit Zeiger auf die Metadaten
            t = oauth.bearer(self.headers)
            k = konten.oauth_konto(t) if t and oauth.basis() else None
            if not k:
                return self._senden(401, {"fehler": "Anmeldung nötig"},
                                    {"WWW-Authenticate": oauth.www_authenticate(fehler=bool(t))})
            zugang = {"konto_id": k["id"]}
        else:
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
        sys.exit(f"Reise „{reise}“ ist unter {seiten()} nicht veröffentlicht (erst bauen und veröffentlichen).")
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


def konto_anlegen(schluessel, name):
    """Persönlicher Konto-Link: meine Reisen und neue Reise anlegen (Paket H). Wer einen hat, darf Reisen anlegen."""
    if not PERSON_MUSTER.match(schluessel) or not name.strip() or "\n" in name:
        sys.exit("Aufruf: konto <schluessel> <Name>  (Schlüssel klein, ohne Umlaute, z. B. hanna)")
    token = zugang_ausstellen({"konto": schluessel, "name": name.strip()})
    print(f"Konto {schluessel} ({name.strip()}): {basis()}/{token}")


def zugaenge_zeigen():
    alle = zugaenge()
    if not alle:
        print("Keine Zugänge angelegt.")
    for t, z in alle.items():
        if "konto" in z:
            print(f"Konto {z['konto']} ({z.get('name')}, {z.get('angelegt', '?')}): {basis()}/{t}")
            continue
        wer = z.get("person") or f"Rolle {z.get('rolle')}"
        print(f"{z.get('reise')} ({wer}, {z.get('angelegt', '?')}): {basis()}/{t}")


def main(a):
    if a[:1] == ["dienst"]:
        dienst()
    elif a[:1] == ["zugang"] and len(a) == 3:
        zugang_anlegen(a[1], a[2])
    elif a[:1] == ["konto"] and len(a) == 3:
        konto_anlegen(a[1], a[2])
    elif a[:1] == ["zugaenge"]:
        zugaenge_zeigen()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
