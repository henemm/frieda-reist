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

HTTP (hinter nginx an der Wurzel von FR_KN_ADRESSE, Vorlage betrieb/vorlagen/nginx-konnektor.conf, docs/betrieb.md):
  POST /mcp         MCP für den Konnektor „Frieda“ mit OAuth (engine/oauth.py); dazu Anmeldung und Konto (engine/anmeldung.py)
  POST /<token>     MCP über einen geheimen Link aus der Zeit vor den Konten (Übergang; früher unter /<instanz>-mcp/)
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
import kalender  # noqa: E402
import konten  # noqa: E402
import oauth  # noqa: E402
import belege as bl  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import schnittstelle  # noqa: E402
import texte  # noqa: E402
from reise import (ENTSCHEIDUNGEN, LESE_BAUSTEIN, ROLLEN, VORGABEN, darf, erlaubt,  # noqa: E402
                   konflikte, neue_reise_pruefen, rolle_neu, schluessel_aus_name, verhalten)
from routen import FARBEN, GRUNDFORMEN, STUFEN, SYMBOLE_ARTEN, TYPEN, ZAHLUNG, ZAHLUNG_ALIAS, ZAHLUNG_WORTE, art_schluessel, stufe_gilt, stufe_schluessel, stufe_wort  # noqa: E402  (Form der Ontologie, docs/ontologie.md)

PERSON_MUSTER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")
SCHREIB_WERKZEUGE = {"rueckmeldung_geben", "aufgabe_anlegen", "aufgabe_aendern", "rueckmeldung_erledigen",
                     "frage_beantworten", "entscheiden", "person_einladen", "person_entfernen", "wunsch_aendern", "beleg_anlegen"}
# Werkzeuge, die direkt in die Ontologie der Reise schreiben (ADR-0001, O-3; engine/schreiben.py): nur bei Instanzen mit
# Schreibweg (KN_SCHREIBDIENST); Organisator:innen schreiben, Mitwirkende schlagen vor (Rückmeldung der Art Ergänzung)
ONTOLOGIE_WERKZEUGE = ("art_definieren", "merkmal_definieren", "kategorie_definieren", "wert_eintragen", "ding_anlegen", "ding_aendern", "lage_eintragen",
                       "option_anlegen", "wahlstelle_anlegen", "frage_anlegen", "tag_aendern", "wissen_schreiben", "frage_schliessen",
                       "reise_status_setzen", "einstellung_setzen", "buchung_anlegen", "buchung_aendern",
                       # Abgleich 29.10.2026 (Paket 3): die Tür für alle Grundformen
                       "tag_anlegen", "termin_setzen", "wahlstelle_aendern", "option_aendern", "wissen_aendern", "lesetext_schreiben",
                       "reise_aendern", "plan_anlegen", "plan_aendern", "merkmal_zusammenfuehren", "arten_uebernehmen", "wunsch_vorschlagen",
                       "start_ende_setzen")
# Aktion der Regelprüfung je Werkzeug; art_definieren und merkmal_definieren gehen für Mitwirkende als Rückmeldung (Vorschlag)
ONTOLOGIE_AKTION = {"art_definieren": "ontologie", "merkmal_definieren": "ontologie", "kategorie_definieren": "ontologie", "wert_eintragen": "wert",
                    "ding_anlegen": "ding", "ding_aendern": "ding", "lage_eintragen": "ding", "option_anlegen": "alternative",
                    "wahlstelle_anlegen": "alternative", "frage_anlegen": "frage", "tag_aendern": "plan", "wissen_schreiben": "wissen",
                    "frage_schliessen": "frage_schliessen", "reise_status_setzen": "einstellung", "einstellung_setzen": "einstellung",
                    "buchung_anlegen": "buchung", "buchung_aendern": "buchung",
                    "tag_anlegen": "plan", "termin_setzen": "plan", "wahlstelle_aendern": "plan", "option_aendern": "alternative",
                    "wissen_aendern": "wissen", "lesetext_schreiben": "wissen", "reise_aendern": "einstellung", "plan_anlegen": "plan",
                    "plan_aendern": "plan", "merkmal_zusammenfuehren": "ontologie", "arten_uebernehmen": "ontologie", "wunsch_vorschlagen": "wunsch",
                    "start_ende_setzen": "einstellung"}
# Werkzeug -> Aktion der Regelprüfung (reise.AKTIONEN); rueckmeldung_geben mit Art Wunsch ist die Aktion „wunsch“
SCHREIB_AKTION = {"rueckmeldung_geben": "rueckmeldung", "aufgabe_anlegen": "aufgabe", "aufgabe_aendern": "aufgabe", "beleg_anlegen": "buchung",
                  "entscheiden": "entscheiden", "rueckmeldung_erledigen": "rueckmeldung_erledigen",
                  "frage_beantworten": "antwort", "person_einladen": "einladen", "person_entfernen": "entfernen",
                  # Wunsch-Brett: sichtbar für alle, die abhaken dürfen; Punkte und Einplanen prüft der Dienst genauer
                  "wunsch_aendern": "wunsch_erlebt"}
# Werkzeuge, die zusätzlich eine zweite Aktion brauchen: eine Antwort landet als Rückmeldung (Art Antwort) im Eingang
ZUSATZ_AKTION = {"frage_beantworten": "rueckmeldung"}
WORT = texte.gruppe("de", "konnektor.wort")   # Wörter der Entscheidungen; Katalog in texte_de.py (ADR-0006)
MAX_GRUND = 500
PROTOKOLLE = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
MAX_BODY = 64 * 1024
MAX_AUFTRAG = 4000
TOKEN_MUSTER = re.compile(r"^[A-Za-z0-9_-]{20,100}$")
AID_MUSTER = re.compile(r"^A-\d{8}-\d{6}-[0-9a-f]{4}$")

_sperre = threading.Lock()

CODE_DATEIEN = ("konnektor.py", "reise.py", "rueckmeldungen.py", "routen.py", "schnittstelle.py", "texte.py")
SPRACHDATEIEN = tuple(f"texte_{k}.py" for k in texte._dateien())   # jede Sprachdatei neben dem Code zählt zum Stand


def antworttext(t):
    """Text einer Antwort für den Client: ein Satz aus dem Katalog in der Sprache des Aufrufs, Werkzeugnamen so, wie tools/list sie zeigt."""
    if isinstance(t, texte.Satz):
        t = t.text(texte.aufruf_sprache())
    return schnittstelle.namen_im_text(t, streng=True)


def code_stand():
    """Kurzer Hash des Codes, den der Dienst von der Platte lädt (konnektor.py und die Module daneben)."""
    h = hashlib.sha256()
    for n in CODE_DATEIEN + SPRACHDATEIEN:
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


def sprache_des_zugangs(zugang):
    """Sprache für diese Anfrage (ADR-0006): die des Kontos; bei Übergangs-Links ohne Konto die der Reise (veröffentlichte Daten);
    sonst die Vorgabe der Personen."""
    if zugang.get("konto_id"):
        k = konten.konto(zugang["konto_id"])
        if k:
            return k["sprache"]
    s = (((daten(zugang.get("reise") or "") or {}).get("reise") or {}).get("sprache")) if zugang.get("reise") else None
    # ohne Konto und ohne lesbare Reise (alte Konto-Links): die Sprache des Bestands
    return s if texte.gueltig(s or "") else texte.VORGABE_REISE


def tk(schluessel, /, **werte):
    """Text des Konnektors aus dem Katalog in der Sprache des laufenden Aufrufs (texte.aufruf_sprache); ohne Aufruf (Tests, Skripte)
    ist es die Sprache des Bestands."""
    return texte.t(texte.aufruf_sprache(), schluessel, **werte)


def tkd(schluessel, /, **werte):
    """Wie tk, aber immer in der Sprache des Bestands: für Text, der in die Ablage der Reise geschrieben wird (Einträge, Herkunft)."""
    return texte.t(texte.VORGABE_REISE, schluessel, **werte)


def lokalisiert(werkzeuge, sprache):
    """Kopie der Werkzeugliste, in der jede Beschreibung der Form "@schlüssel" durch den Text des Katalogs in der Sprache ersetzt ist
    (ADR-0006): Namen, Schemata und Hinweise bleiben gleich, nur die Beschreibungen folgen der Sprache der Person."""
    def gehe(x):
        if isinstance(x, dict):
            return {k: (texte.t(sprache, v[1:]) if k == "description" and isinstance(v, str) and v.startswith("@") else gehe(v))
                    for k, v in x.items()}
        if isinstance(x, list):
            return [gehe(e) for e in x]
        return x
    return gehe(werkzeuge)


def aufruf_intern(werkzeuge, name, args):
    """tools/call von außen -> (interner Name, interne Argumente): englische und deutsche Namen gelten gleich, auch gemischt
    (ADR-0006, Punkt 4). werkzeuge ist die interne Liste, aus der das Schema des Werkzeugs stammt."""
    intern = schnittstelle.intern_name(name) if isinstance(name, str) else name
    schema = next((w["inputSchema"] for w in werkzeuge if w["name"] == intern), None)
    return intern, schnittstelle.intern_argumente(intern, args, schema)


def sprache_setzen_werkzeug(sprache):
    """Konto-Werkzeug sprache_setzen: Beschreibung in der Sprache der Person, die Wahl aus den Sprachen des Katalogs."""
    return {"name": "sprache_setzen", "description": texte.t(sprache, "konnektor.werkzeug.sprache_setzen"),
            "inputSchema": {"type": "object", "properties": {"sprache": {
                "type": "string", "enum": list(texte.SPRACHEN),
                "description": texte.t(sprache, "konnektor.werkzeug.sprache_setzen.sprache")}}, "required": ["sprache"]}}


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
            self.teile.append(tk("konnektor.ausgabe.handle_starttag.1", w1=': ' + a['alt'] if a.get('alt') else ''))

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
# Schrift der Anmelde- und Kontoseiten (Source Sans 3, engine/vendor/fonts/; im Dienst neben den Modulen in schrift/)
SCHRIFT = next((d for d in (Path(__file__).resolve().parent / "schrift", Path(__file__).resolve().parent / "vendor" / "fonts")
                if d.is_dir()), Path(__file__).resolve().parent / "schrift")
SCHRIFT_DATEIEN = {f"/schrift/{n}": (n, "font/woff2") for n in
                   ("source-sans-3-latin-wght-normal.woff2", "source-sans-3-latin-ext-wght-normal.woff2")}


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


def zeit_de(t, sprache=None):
    """Zeitpunkt mit Datum in der Sprache (bis M10 die der Reise-Vorgabe, dann die der Person)."""
    return texte.datum_zeit(t.astimezone(), sprache or texte.aufruf_sprache())


def stand_text(reise):
    """Woran man in der App sieht, ob das Veröffentlichen gelaufen ist: Bauzeit der Seite und Stand des Dienstes."""
    z = [tk("konnektor.ausgabe.stand_text.1")]
    try:
        gebaut = datetime.datetime.fromtimestamp((seiten() / reise / "daten.json").stat().st_mtime).astimezone()
        z.append(tk("konnektor.stand_text.1", w1=zeit_de(gebaut)))
    except OSError:
        z.append(tk("konnektor.stand_text.2"))
    jetzt = code_stand()
    z.append(tk("konnektor.ausgabe.stand_text.2", w1=zeit_de(_START), w2=_CODE_START)
             + ("" if jetzt == _CODE_START else tk("konnektor.stand_text.3", jetzt=jetzt)))
    return "\n".join(z)


# Doppelte Merkmale erkennen (Paket 3, #18): Ein neuer Schlüssel aus einem Vorschlag, der einem bestehenden Merkmal der
# Art entspricht (z. B. „oeffnung“ neben „geoeffnet“), soll zusammengeführt statt neu angelegt werden. Nur generisch
# (Schreibweise, Wortstamm) und über die Zweitnamen „auch“, die die Reise in arten.yaml angibt; keine Wortliste in der
# Software (ADR-0001: kein Katalog).


def regel_stand(x):
    """Stand einer Option, auf die eine Regel zeigt (erfordert, schliesst_aus)."""
    return "verworfen" if not x.get("gueltig", True) else tk("konnektor.ausgabe.regel_stand.1") if x.get("im_plan") else tk("konnektor.regel_stand.1")


def merkmal_norm(s):
    s = str(s).lower()
    for a, b in ((tkd("konnektor.merkmal_norm.1"), "ae"), (tkd("konnektor.merkmal_norm.2"), "oe"), (tkd("konnektor.merkmal_norm.3"), "ue"), (tkd("konnektor.merkmal_norm.4"), "ss")):
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


def datum_de(iso, sprache=None):
    """Datum mit Jahr in der Sprache (bis M10 die der Reise-Vorgabe, dann die der Person)."""
    return texte.datum(iso, sprache or texte.aufruf_sprache())


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
            return tk("konnektor.ausgabe.nacht.1")
        teile = [self.ort(n.get("ort"))]
        u = (self.r.get("unterkuenfte") or {}).get(n.get("unterkunft") or "")
        if u:
            if u.get("name") == teile[0]:  # Unterkunft ist selbst der Ort (z. B. eine Hütte)
                teile.pop()
            teile.append(f"{u.get('name')} ({n['unterkunft']})")
        elif n.get("hinweis") or n.get("art_name"):
            teile.append(n.get("hinweis") or n.get("art_name"))
        if n.get("wahl"):
            teile.append(tk("konnektor.ausgabe.nacht.2", w1=n['wahl']))
        return ", ".join(teile)

    def buchung_text(self, b):
        """Eine Buchung (B-…, #76) für die Claude-App: Dinge, Status, Nummer, Anbieter, Preis, Frist, Storno, Herkunft, Belege, Verlauf."""
        z = [tk("konnektor.buchung_text.1") + "; ".join(f"{x} {self.titel_von(x)}" for x in b.get("fuer") or []), tk("konnektor.ausgabe.buchung_text.1", w1=b.get('status'))]
        for k, name in (("nummer", tk("konnektor.ausgabe.buchung_text.2")), ("bei", tk("konnektor.ausgabe.buchung_text.3")), ("preis", tk("konnektor.ausgabe.buchung_text.4"))):
            if b.get(k):
                z.append(name + str(b[k]))
        if b.get("zahlung") or b.get("bezahlt"):   # Zahlstand (#166) mit seinen Einzelheiten
            z.append(tk("konnektor.ausgabe.buchung_text.15") + " · ".join(x for x in (ZAHLUNG_WORTE.get(b.get("zahlung"), b.get("zahlung")), b.get("bezahlt")) if x))
        for m in b.get("merkmale") or []:   # Merkmale der Buchung (#166), Herkunft wie die Buchung
            z.append(f"{m['name']}: {m['wert']}" + (f" {m['einheit']}" if m.get("einheit") else ""))
        if b.get("preise"):
            z.append(tk("konnektor.ausgabe.buchung_text.7") + "; ".join(f"{x} {self.titel_von(x)}: {p}" for x, p in b["preise"].items()))
        if b.get("personen"):
            z.append(tk("konnektor.ausgabe.buchung_text.8") + "; ".join(f"{n}" + (f" ({a})" if a else "") for n, a in b["personen"].items()))
        if b.get("ab"):
            z.append(tk("konnektor.ausgabe.buchung_text.ab", w1=datum_de(b['ab'])) + (f": {b['ab_was']}" if b.get("ab_was") else ""))
        if b.get("frist"):
            z.append(tk("konnektor.ausgabe.buchung_text.9", w1=datum_de(b['frist'])) + (f": {b['frist_was']}" if b.get("frist_was") else ""))
        if b.get("storno") or b.get("storno_bis"):
            z.append(tk("konnektor.ausgabe.buchung_text.11") + (b.get("storno") or "") + (tk("konnektor.ausgabe.buchung_text.12", w1=datum_de(b['storno_bis'])) if b.get("storno_bis") else ""))
        if b.get("gebucht_am") or b.get("wer"):
            z.append(tk("konnektor.ausgabe.buchung_text.13") + (tk("konnektor.ausgabe.buchung_text.am", w1=datum_de(b['gebucht_am'])) if b.get("gebucht_am") else "") + (tk("konnektor.ausgabe.buchung_text.14", w1=b['wer']) if b.get("wer") else ""))
        if b.get("notiz"):
            z.append(b["notiz"])
        if b.get("quelle"):
            z.append(tk("konnektor.ausgabe.option_text.2") + str(b["quelle"]))
        belege = (self.belege or {}).get(b.get("id")) or []
        z.append(tk("konnektor.ausgabe.buchung_text.6") + ("; ".join(f"{x.get('name')} ({x.get('wer')}, {str(x.get('hochgeladen', ''))[:10]}"
                                          + (tk("konnektor.beleg.fuer_alle") if x.get("sichtbar") == "alle" else "") + ")" for x in belege)
                               if belege else tk("konnektor.buchung_text.2")))
        if b.get("verlauf"):
            z.append(tk("konnektor.ausgabe.buchung_text.10") + "; ".join(f"{datum_de(v['datum'])} {v.get('wer')}: {v.get('was')}" + (f" ({v['grund']})" if v.get("grund") else "")
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
        uhr = "–".join(x for x in (a.get("beginn"), a.get("ende")) if x)
        return ", ".join(x for x in [f"{a.get('name', aid)} ({aid})", art, a.get("zeit"), uhr and uhr + " Uhr",
                                     f"Buchung: {a['buchung']}" if a.get("buchung") else ""] if x)

    def strecke(self, sid):
        s = (self.r.get("strecken") or {}).get(sid) or {}
        return s.get("titel") or sid

    def tag_text(self, t, datum=True):
        z = []
        if datum and t.get("datum"):
            z.append(tk("konnektor.ausgabe.tag_text.1", w1=t['nr'], w2=texte.wochentag(t['datum'], texte.aufruf_sprache()), w3=datum_de(t['datum'])) + (f" ({t['teil']})" if t.get("teil") else ""))
        if t.get("strecken"):
            z.append(tk("konnektor.ausgabe.tag_text.2") + "; ".join(f"{self.strecke(s['id'])} ({s['id']}"
                                           + (tk("konnektor.ausgabe.wahl", w1=s['wahl']) if s.get("wahl") else "") + ")"
                                           for s in t["strecken"]))
        if t.get("aufenthalte"):
            z.append(tk("konnektor.ausgabe.tag_text.3") + "; ".join(self.aufenthalt(a) for a in t["aufenthalte"]))
        if t.get("nacht"):
            z.append(tk("konnektor.ausgabe.tag_text.4") + self.nacht(t["nacht"]))
        if t.get("fixpunkte"):
            z.append(tk("konnektor.ausgabe.tag_text.5") + "; ".join(t["fixpunkte"]))
        if t.get("wahlstellen"):
            z.append(tk("konnektor.ausgabe.tag_text.6") + ", ".join(t["wahlstellen"]))
        if t.get("text"):
            z.append(t["text"])
        return "\n".join(z)

    def summe(self, s):
        if not s:
            return ""
        z = [tk("konnektor.summe.1", w1=s.get('tage'), w2=s.get('naechte'))]
        if s.get("min"):
            z.append(f"Gehzeit {stunden(s['min'])}, ↑ {s.get('auf'):.0f} Hm, ↓ {s.get('ab'):.0f} Hm, {s.get('km')} km")
        if s.get("unterkunftstypen"):
            z.append(tk("konnektor.summe.2") + ", ".join(f"{k} {v}" for k, v in s["unterkunftstypen"].items()))
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
                zusatz.append(tk("konnektor.merkmal_zeilen.1", w1=datum_de(v['geprueft'])))
            elif v.get("ungeprueft"):
                zusatz.append(tk("konnektor.merkmal_zeilen.2"))
            if v.get("quelle"):
                zusatz.append(tk("konnektor.ausgabe.merkmal_zeilen.1", w1=v['quelle']))
            if v.get("auto"):
                zusatz.append("berechnet")
            z.append(f"- {k['name']}: {v['wert']}" + (f" ({'; '.join(zusatz)})" if zusatz else ""))
        if fehlt:
            namen = {k["id"]: k["name"] for k in kriterien or []}
            z.append(tk("konnektor.ausgabe.merkmal_zeilen.2") + ", ".join(namen.get(k, k) for k in fehlt))
        return z

    def kriterien_von(self, id_):
        """-> (Wahlstelle, Bereich, Kriterien) zu V-…, V-….x oder U-…"""
        for w in self.r.get("wahlstellen", []):
            if id_ == w["id"] or any(o["id"] == id_ for o in w["optionen"]):
                return w, w.get("art") or "allgemein", w.get("kriterien") or []
        if id_ in (self.r.get("aufenthalte") or {}):   # Aufenthalt ohne Nacht (A-…): Zeile wie im Tag, dann Merkmale
            a = self.r["aufenthalte"][id_]
            z = [self.aufenthalt(id_), "in " + self.ort(a.get("ort")), *( [a["hinweis"]] if a.get("hinweis") else []),
                 *( [tk("konnektor.ausgabe.kriterien_von.1") + ", ".join(a["tage"])] if a.get("tage") else []), *( [tk("konnektor.ausgabe.option_text.2") + a["quelle"]] if a.get("quelle") else [])]
            z += self.merkmal_zeilen((self.r.get("merkmale") or {}).get(a.get("art")), a.get("merkmale"), a.get("fehlt"))
            return "\n".join(z)
        if id_ in (self.r.get("unterkuenfte") or {}):   # Aufenthalt: Merkmale seiner Art (plan/arten.yaml)
            b = self.r["unterkuenfte"][id_].get("art")
            return None, b, (self.r.get("merkmale") or {}).get(b) or []
        st = (self.r.get("strecken") or {}).get(id_)
        if st is not None:   # Bewegung: Merkmale ihrer Art
            b = st.get("art_schluessel")
            return None, b, (self.r.get("merkmale") or {}).get(b) or []
        return None, None, None

    def option_text(self, o, w=None):
        z = [tk("konnektor.ausgabe.buchung_text.1", w1=o.get('status')) + (tk("konnektor.ausgabe.option_text.5") if o.get("aktiv") else "")]
        if w and (o.get("merkmale") or o.get("fehlt")):
            z.append(tk("konnektor.ausgabe.option_text.1"))
            z += self.merkmal_zeilen(w.get("kriterien"), o.get("merkmale"), o.get("fehlt"))
        for k, name in (("text", ""), ("ausloeser", tk("konnektor.option_text.1")), ("quelle", tk("konnektor.ausgabe.option_text.2")), ("siehe", tk("konnektor.ausgabe.option_text.3"))):
            if o.get(k):
                z.append(name + str(o[k]))
        if o.get("plus"):
            z.append(tk("konnektor.option_text.3") + "; ".join(o["plus"]))
        if o.get("minus"):
            z.append(tk("konnektor.ausgabe.option_text.6") + "; ".join(o["minus"]))
        if o.get("tage"):
            z.append(tk("konnektor.ausgabe.option_text.7") + ", ".join(o["tage"]))
        for k, name in (("erfordert", tk("konnektor.ausgabe.option_text.4")), ("schliesst_aus", tk("konnektor.option_text.2"))):
            if o.get(k):
                z.append(f"{name}: " + "; ".join(f"{x['id']} „{x['titel']}“ ({regel_stand(x)})" for x in o[k]))
        if o.get("summe"):
            z.append(tk("konnektor.ausgabe.option_text.8") + self.summe(o["summe"]))
        for v in o.get("verlauf") or []:
            z.append(tk("konnektor.ausgabe.option_text.9", w1=v.get('datum'), w2=v.get('status')) + (f" ({v['wer']})" if v.get("wer") else "")
                     + (f" – {v['grund']}" if v.get("grund") else ""))
        z += self.offen_zeilen(o["id"])
        return "\n".join(z)

    def offen_zeilen(self, oid):
        """Entscheidungen zu dieser Option, die eingetragen, aber noch nicht in der Seite eingearbeitet sind."""
        return [tk("konnektor.offen_zeilen.1", w1=WORT.get(e['entscheidung'], e['entscheidung']), w2=e['wer'], w3=datum_de(e['datum']), w4=e['auftrag'])
                + (tk("konnektor.offen_zeilen.3") if e["weg"] == "direkt" else tk("konnektor.offen_zeilen.4"))
                + (tk("konnektor.offen_zeilen.2") if e["status"] == "konflikt" else "") + ")"
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
                z.append(tk("konnektor.sammeln.1"))
            if a.get("route_ansicht") == "unterkuenfte":
                z.append(tk("konnektor.sammeln.2"))
            if a.get("bloecke"):
                z.append(tk("konnektor.ausgabe.sammeln.12") + "; ".join(f"{b['id']} {b['titel']}" for b in a["bloecke"]))
            # Orte ↔ Recherche (reise.json orte_wissen)
            if a.get("wissen"):
                z.append(tk("konnektor.sammeln.5") + "; ".join(f"{w['id']} {w['titel']}" + (f" ({w['notiz']})" if w.get("notiz") else "")
                                                         for w in a["wissen"]))
            if a.get("orte"):
                z.append(tk("konnektor.ausgabe.sammeln.13") + ", ".join(a["orte"]))
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
            e[t["id"]] = (tk("konnektor.ausgabe.sammeln.1", w1=t['nr'], w2=datum_de(t['datum']), w3=t['titel']), self.tag_text(t))
        for tid, t in (r.get("weitere_tage") or {}).items():
            e[tid] = (tk("konnektor.ausgabe.sammeln.2", w1=t['titel']), tk("konnektor.sammeln.3")
                      + self.tag_text(t, datum=False))
        for oid, o in self.orte.items():
            e.setdefault(oid, (o.get("name") or oid, o.get("hinweis") or ""))
        for sid, s in (r.get("strecken") or {}).items():
            z = [f"{self.ort(s.get('von'))} → {self.ort(s.get('nach'))}" + (f" ({' + '.join(s['art']) if isinstance(s['art'], list) else s['art']})" if s.get("art") else "")
                 + (tk("konnektor.ausgabe.sammeln.18", w1=s['ab']) if s.get("ab") else "") + (tk("konnektor.ausgabe.sammeln.14", w1=s['an']) if s.get("an") else "")]
            if s.get("kennzahlen") and sid not in e:  # bei Etappen stehen sie schon im Dossier
                z.append("; ".join(f"{k}: {v}" for k, v in s["kennzahlen"].items()))
            if s.get("buchung"):   # eine Zeile mit Verweis auf die Heimat der Buchung (ADR-0003)
                z.append(tk("konnektor.ausgabe.sammeln.15", w1=s['buchung']) + (tk("konnektor.ausgabe.zeige_hinweis", w1=s['buchung_id']) if s.get("buchung_id") else ""))
            if s.get("beginn"):
                z.append(tk("konnektor.ausgabe.sammeln.19", w1=s['beginn']) + (f"–{s['ende']}" if s.get("ende") else "") + " Uhr")
            for k in ("text", "quelle", "siehe"):
                if s.get(k):
                    z.append((tk("konnektor.ausgabe.option_text.2") if k == "quelle" else tk("konnektor.ausgabe.option_text.3") if k == "siehe" else "") + str(s[k]))
            if s.get("merkmale") or s.get("fehlt"):
                z.append(tk("konnektor.ausgabe.option_text.1"))
                z += self.merkmal_zeilen((r.get("merkmale") or {}).get(s.get("art_schluessel")), s.get("merkmale"), s.get("fehlt"))
            z += self.lesetext_zeilen(s)
            if sid in e:  # Etappe aus dem Dossier: Text dort, Strecke ergänzt
                titel, alt = e[sid]
                e[sid] = (titel, "\n".join(z) + "\n\n" + alt)
            else:
                e[sid] = (s.get("titel") or sid, "\n".join(z))
        for uid, u in (r.get("unterkuenfte") or {}).items():
            z = [f"{((self.r.get('arten') or {}).get(u.get('art')) or {}).get('name') or ''} in {self.ort(u.get('ort'))}".strip()]
            for k, name in (("hinweis", ""), ("kontakt", tk("konnektor.ausgabe.sammeln.4")), ("buchung", tk("konnektor.ausgabe.sammeln.5")),
                            ("frage", tk("konnektor.ausgabe.sammeln.6")), ("quelle", tk("konnektor.ausgabe.option_text.2"))):
                if u.get(k):
                    z.append(name + str(u[k]) + (tk("konnektor.ausgabe.zeige_hinweis", w1=u['buchung_id']) if k == "buchung" and u.get("buchung_id") else ""))
            # Lage (ADR-0004): Adresse und Koordinaten mit Herkunft; fehlt beides, trägt lage_eintragen sie nach
            for k, name in (("adresse", tk("konnektor.ausgabe.sammeln.7")), ("punkt", tk("konnektor.ausgabe.sammeln.8"))):
                v = u.get(k)
                if v:
                    w = ", ".join(map(str, v["wert"])) if k == "punkt" else v["wert"]
                    z.append(f"{name}{w} ({v.get('quelle') or tk("konnektor.ausgabe.sammeln.20")}{tk("konnektor.sammeln.7") + v['geprueft'] if v.get('geprueft') else ''})")
            if not u.get("adresse") and not u.get("punkt"):
                z.append(tk("konnektor.ausgabe.sammeln.9"))
            if u.get("naechte"):
                z.append(tk("konnektor.sammeln.6") + ", ".join(u["naechte"]))
            if u.get("merkmale") or u.get("fehlt"):
                z.append(tk("konnektor.ausgabe.option_text.1"))
                z += self.merkmal_zeilen((r.get("merkmale") or {}).get(u.get("art")), u.get("merkmale"), u.get("fehlt"))
            e[uid] = (u.get("name") or uid, "\n".join(z))
        for bid, b in (r.get("buchungen") or {}).items():   # Buchung als eigenes Ding (#76)
            e[bid] = (tk("konnektor.ausgabe.sammeln.3", w1=b.get('status'), w2=b.get('titel') or bid), self.buchung_text(b))
        for p in r.get("plaene", []):
            z = [p.get("text") or "", tk("konnektor.ausgabe.sammeln.10") + ", ".join(p.get("auswahl") or [])]
            if p.get("aktuell"):
                z.append(tk("konnektor.sammeln.4"))
            if p.get("plus"):
                z.append(tk("konnektor.option_text.3") + "; ".join(p["plus"]))
            if p.get("minus"):
                z.append(tk("konnektor.ausgabe.option_text.6") + "; ".join(p["minus"]))
            z += [f"{t['id']} {t['titel']}" + (tk("konnektor.ausgabe.sammeln.16", w1=self.nacht(t.get('nacht'))) if t.get("nacht") else "")
                  for t in p.get("tage", [])]
            e[p["id"]] = (f"{p['kurz']}: {p['titel']}", "\n".join(x for x in z if x))
        for w in r.get("wahlstellen", []):
            z = [f"Art: {w.get('art')}" + (tk("konnektor.ausgabe.sammeln.17") if w.get("offen") else "")]
            if w.get("frage"):
                z.append(tk("konnektor.ausgabe.sammeln.11", w1=w['frage']))
            if w.get("text"):
                z.append(w["text"])
            z += [f"{o['id']} {o['titel']} – {o.get('status')}" + (tk("konnektor.ausgabe.aktuell") if o.get("aktiv") else "")
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
            z.append(tk("konnektor.ausgabe.ueberblick.6") + self.summe(self.r["summe"]))
        if self.v["start"] == "heute" and self.r.get("tage"):
            heute = datetime.date.today().isoformat()
            tag = next((t for t in self.r["tage"] if t["datum"] == heute), None)
            z.append(tk("konnektor.ausgabe.ueberblick.7") + (tk("konnektor.ausgabe.ueberblick.14", w1=tag['id'], w2=tag['nr'], w3=tag['titel'])
                                    + (tk("konnektor.ausgabe.sammeln.16", w1=self.nacht(tag.get('nacht'))) if tag.get("nacht") else "")
                                    if tag else tk("konnektor.ueberblick.3")))
        if self.r.get("tage"):
            z.append(tk("konnektor.ausgabe.ueberblick.2"))
            teil = None
            for t in self.r["tage"]:
                if t.get("teil") and t["teil"] != teil:
                    teil = t["teil"]
                    z.append(f"### {teil}")
                z.append(tk("konnektor.ausgabe.ueberblick.9", w1=t['id'], w2=t['nr'], w3=texte.wochentag(t['datum'], texte.aufruf_sprache()), w4=datum_de(t['datum']), w5=t['titel'])
                         + (tk("konnektor.ausgabe.sammeln.16", w1=self.nacht(t.get('nacht'))) if t.get("nacht") else ""))
        if self.an("fragen"):
            z.append(tk("konnektor.ausgabe.ueberblick.3", w1=len(self.offene())))
        if self.aufgaben is not None and self.an("aufgaben"):
            offene_ag = [a for a in self.aufgaben if a["status"] in ("offen", "in_arbeit")]
            heute = datetime.date.today().isoformat()
            ueber = [a for a in offene_ag if a.get("frist") and a["frist"] < heute] if self.v["fristen"] else []
            z.append(tk("konnektor.ausgabe.ueberblick.10", w1=len(offene_ag)) + (tk("konnektor.ueberblick.5", w1=len(ueber)) if ueber else "")
                     + tk("konnektor.ausgabe.ueberblick.8"))
            z += [tk("konnektor.ausgabe.ueberblick.4", w1=a['id'], w2=a['frist'], w3=a['titel']) for a in ueber]
        if self.r.get("buchungen"):
            bs = list(self.r["buchungen"].values())
            gezaehlt = {tk(f"konnektor.ausgabe.ueberblick.status_{s}"): len([b for b in bs if b.get("status") == s]) for s in ("gebucht", "angefragt", "storniert")}
            z.append(tk("konnektor.ausgabe.ueberblick.13") + ", ".join(f"{n} {s}" for s, n in gezaehlt.items() if n) + tk("konnektor.ausgabe.ueberblick.zeige_b"))
            heute = datetime.date.today().isoformat()
            fristen = sorted((b for b in bs if b.get("status") != "storniert" and (b.get("frist") or b.get("storno_bis"))),
                             key=lambda b: min(x for x in (b.get("frist"), b.get("storno_bis")) if x))[:5]
            z += [f"- {b['id']} {b.get('titel')}: " + ", ".join(x for x in (
                tk("konnektor.ausgabe.fristen.1", w1=datum_de(b['frist'])) + (f" ({b['frist_was']})" if b.get("frist_was") else "") + (tk("konnektor.buchung.ueberfaellig") if b["frist"] < heute else "") if b.get("frist") else "",
                tk("konnektor.ausgabe.fristen.2", w1=datum_de(b['storno_bis'])) if b.get("storno_bis") else "") if x) for b in fristen]
        if self.meldungen:
            z.append(tk("konnektor.ausgabe.liste_text.1"))
            z += [f"- {m['erstellt'][:10]}: {m['text']}" for m in self.meldungen[:10]]
        if self.r.get("mahnungen"):
            z.append(tk("konnektor.ueberblick.1"))
            z += [f"- {m['text']}" for m in self.r["mahnungen"]]
        if self.r.get("wahlstellen") and self.an("varianten"):
            z.append(tk("konnektor.ausgabe.ueberblick.5"))
            z += [f"- {w['id']} {w['titel']}" + (tk("konnektor.ausgabe.ueberblick.15") if w.get("offen") else "")
                  + (tk("konnektor.ueberblick.4") if w.get("wann") == "unterwegs" and self.v["ausloeser_vor"] else "")
                  for w in sorted(self.r["wahlstellen"], key=lambda w: not (self.v["ausloeser_vor"] and w.get("wann") == "unterwegs"))]
        z.append(tk("konnektor.ausgabe.ueberblick.1"))
        z += [f"- {a['id']} {a['titel']}" for a in self.d.get("abschnitte", [])]
        if self.r.get("warnungen"):
            z.append(tk("konnektor.ueberblick.2"))
            z += [f"- {w['text']}" for w in self.r["warnungen"]]
        return "\n".join(x for x in z if x)

    def zeige(self, id_):
        if self.aufgaben is not None and rm.AG_MUSTER.match(id_):
            a = next((x for x in self.aufgaben if x["id"] == id_), None)
            return (aufgabe_text(a, self.titel()), None) if a else (None, tk("konnektor.zeige.1"))
        if id_ not in self.eintraege:
            nah = [k for k in self.eintraege if k.lower().startswith(id_.lower())][:20]
            return None, (tk("konnektor.zeige.2")
                          + (tk("konnektor.ausgabe.zeige.3", w1=', '.join(nah)) if nah else ""))
        titel, t = self.eintraege[id_]
        aus = f"{id_} – {titel}\n\n{t}".strip()
        if self.antworten.get(id_):
            aus += tk("konnektor.ausgabe.zeige.1") + "\n".join(
                f"- {a['erstellt'][:10]} {a.get('name')}: {a['text']}" + (f" (Quelle: {a['quelle']})" if a.get("quelle") else "")
                for a in self.antworten[id_])
        dran = aufgaben_filter(self.aufgaben or [], {"bezug": id_, "status": "alle"})
        if dran:
            aus += tk("konnektor.ausgabe.zeige.2") + rm.aufgaben_text(dran, self.titel(), self.v["fristen"])
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
            return tk("konnektor.ausgabe.suche.1")
        mehr = tk("konnektor.ausgabe.suche.mehr", w1=len(treffer) - grenze) if len(treffer) > grenze else ""
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
            return tk("konnektor.ausgabe.fragen.1") if not alle else tk("konnektor.ausgabe.fragen.2")
        return "\n".join([" | ".join(f.get("spalten", []))] + [" | ".join(z["zellen"]) for z in zeilen])

    def lesetext_zeilen(self, s):
        """Gliederung des Lesetexts der Art einer Strecke (plan/arten.yaml lesetext, docs/ontologie.md) als Anleitung für
        den AI-Client: Rubriken in ihrer Reihenfolge, jede als Absatz mit fettem Stichwort."""
        art = s.get("art_schluessel")
        rubriken = (((self.r.get("arten") or {}).get(art)) or {}).get("lesetext")
        if not rubriken:
            return []
        return [tk("konnektor.lesetext_zeilen.1") + rubriken[0]["name"] + tk("konnektor.ausgabe.lesetext_zeilen.1")] + [
            f"- {x['name']}" + (f": {x['hilfe']}" if x.get("hilfe") else "") for x in rubriken]

    def merkmale(self, ziel, bereich):
        """Welche Merkmale eine Alternative braucht, was schon da ist und was fehlt (Werkzeug merkmale)."""
        katalog = self.r.get("merkmale") or {}
        if ziel:
            w, b, krit = self.kriterien_von(ziel)
            if krit is None:
                return None, tk("konnektor.merkmale.4")
        elif bereich in katalog:
            w, b, krit = None, bereich, katalog[bereich]
        else:
            return None, (tk("konnektor.merkmale.5", w1=', '.join(katalog) or tk("konnektor.ausgabe.merkmale.keine")))
        z = [tk("konnektor.ausgabe.merkmale.2", b=b) + (f" – {w['id']} {w['titel']}" if w else f" – {ziel}" if ziel else ""),
             tk("konnektor.merkmale.1"),
             tk("konnektor.ausgabe.merkmale.1")]
        for k in krit:
            st = k.get("stufe", "empfohlen")   # Stufe je Reise (routen.yaml merkmale: {…: {stufe: …}}); je Unterkunftstyp als Objekt
            if not stufe_gilt(st):   # gilt für diese Reise nicht (aus, auch je Typ überall aus): bleibt unsichtbar
                continue
            art = k.get("typ", "text") + (f" ({' | '.join(k['werte'])})" if k.get("werte") else "")
            zeile = f"- {k['id']} – {k['name']}: {art}"
            # Stufen für Menschen: nötig, gut zu wissen, zusätzlich (Product Owner 29.10.2026); Schlüssel in Klammern
            if isinstance(st, dict):
                zeile += tk("konnektor.ausgabe.merkmale.3") + stufe_wort(st)
            elif st == "pflicht":
                zeile += tk("konnektor.merkmale.6")
            elif st == "angeboten":
                zeile += tk("konnektor.merkmale.7")
            else:
                zeile += tk("konnektor.merkmale.8")
            if k.get("auto"):
                zeile += tk("konnektor.merkmale.2")
            if k.get("veraenderlich"):
                zeile += tk("konnektor.merkmale.3")
            if k.get("nach_buchung"):
                zeile += tk("konnektor.merkmale.nach_buchung")
            if k.get("hilfe"):
                zeile += tk("konnektor.ausgabe.merkmal.so_finden", w1=k['hilfe'])
            if k.get("frage"):
                zeile += tk("konnektor.ausgabe.merkmal.fragen", w1=k['frage'])
            z.append(zeile)
        if w:
            for o in w["optionen"]:
                z.append(f"## {o['id']} {o['titel']} ({o.get('status')})")
                z += self.merkmal_zeilen(krit, o.get("merkmale"), [] if o.get("status") in ("verworfen", "ersetzt")
                                         else o.get("fehlt")) or [tk("konnektor.ausgabe.merkmale.4")]
        elif ziel in (self.r.get("unterkuenfte") or {}):
            u = self.r["unterkuenfte"][ziel]
            z.append(f"## {ziel} {u.get('name')}")
            z += self.merkmal_zeilen(krit, u.get("merkmale"), u.get("fehlt")) or [tk("konnektor.ausgabe.merkmale.4")]
        elif ziel:
            s = self.r["strecken"][ziel]
            z.append(f"## {ziel} {s.get('titel') or ziel}")
            z += self.merkmal_zeilen(krit, s.get("merkmale"), s.get("fehlt")) or [tk("konnektor.ausgabe.merkmale.4")]
        bm = (self.r.get("buchung_merkmale") or {}).get(b) or []
        if bm:   # #166: was erst durch das Buchen entsteht, steht an der Buchung (buchung_anlegen/buchung_aendern, merkmale)
            z += [tk("konnektor.ausgabe.merkmale.5"), tk("konnektor.ausgabe.merkmale.6")]
            for k in bm:
                z.append(f"- {k['id']} – {k['name']}: {k.get('typ', 'text')}" + (f" ({' | '.join(k['werte'])})" if k.get("werte") else "")
                         + (tk("konnektor.ausgabe.merkmale.7", w1=k["hilfe"]) if k.get("hilfe") else "")
                         + (tk("konnektor.ausgabe.merkmale.8", w1=k["frage"]) if k.get("frage") else ""))
        return "\n".join(z), None

    def kategorien(self):
        """Die Kartenkategorien dieser Reise (plan/kategorien.yaml) in Worten (Werkzeug kategorien)."""
        k = self.d.get("kategorien") or {}
        if not k:
            return (tk("konnektor.kategorien.1"))
        z = [tk("konnektor.ausgabe.kategorien.1"),
             tk("konnektor.kategorien.2")]
        for gruppe, titel in (("punkt", "Etappen-Karte"), ("wissen", tk("konnektor.ausgabe.kategorien.2"))):
            sub = {a: d for a, d in k.items() if d.get("gruppe") == gruppe}
            if not sub:
                continue
            z.append(tk("konnektor.ausgabe.kategorien.3", gruppe=gruppe, titel=titel))
            for a, d in sub.items():
                zeile = f"- {a} – {d.get('name')}"
                if d.get("einzahl"):
                    zeile += f" (einzeln: {d['einzahl']})"
                zeile += tk("konnektor.ausgabe.kategorien.4", w1=d.get('farbe'))
                zeile += tk("konnektor.ausgabe.kategorien.5") if d.get("nummeriert") else tk("konnektor.ausgabe.kategorien.6", w1=d.get('symbol') or 'keins')
                z.append(zeile)
                for w, ad in (d.get("arten") or {}).items():
                    teile = [ad.get("name") or w] + ([tk("konnektor.ausgabe.kategorien.9", w1=ad['symbol'])] if ad.get("symbol") else []) \
                        + ([tk("konnektor.ausgabe.kategorien.8")] if ad.get("umriss") else []) + ([tk("konnektor.ausgabe.kategorien.7", w1=ad['hinweis'])] if ad.get("hinweis") else [])
                    z.append(tk("konnektor.ausgabe.art_zeile", w1=w) + "; ".join(teile))
        return "\n".join(z)

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
                return None, [], [tk("konnektor.entscheidung_pruefen.24", oid=oid)
                                  + ", ".join(f"{x['id']} {x['titel']}" for x in stelle["optionen"]) + "."]
            return None, [], [tk("konnektor.entscheidung_pruefen.6", oid=oid)]
        if status not in ENTSCHEIDUNGEN:
            fehler.append(tk("konnektor.entscheidung_pruefen.1", w1=', '.join(ENTSCHEIDUNGEN)))
        if not grund:
            fehler.append(tk("konnektor.entscheidung_pruefen.2"))
        elif len(grund) > MAX_GRUND or "\n" in grund:
            fehler.append(tk("konnektor.entscheidung_pruefen.7", w1=MAX_GRUND))
        if status == "ersetzt":
            wd, od = self.option(durch)
            if not durch:
                fehler.append(tk("konnektor.entscheidung_pruefen.8"))
            elif od is None or wd is not w or durch == oid:
                fehler.append(tk("konnektor.ausgabe.entscheidung_pruefen.1", w1=w['id'], w2=', '.join(x['id'] for x in w['optionen'] if x['id'] != oid)))
            elif od["status"] in ("verworfen", "ersetzt"):
                fehler.append(tk("konnektor.entscheidung_pruefen.17", durch=durch, w2=WORT[od['status']]))
        elif durch:
            fehler.append(tk("konnektor.entscheidung_pruefen.9"))
        if status in ENTSCHEIDUNGEN and o["status"] == status:
            fehler.append(tk("konnektor.entscheidung_pruefen.3", oid=oid, w2=WORT[status]))
        for e in self.offene_entscheidungen.get(oid, []):
            if e["wer"] == wer and e["entscheidung"] == status and e["status"] != "konflikt":
                fehler.append(tk("konnektor.entscheidung_pruefen.10", w1=e['auftrag']))
        if fehler:
            return None, [], fehler
        andere = [x for x in w["optionen"] if x["id"] != oid and x["status"] == "gewaehlt"]
        if status == "gewaehlt" and andere:
            hinweise.append(tk("konnektor.entscheidung_pruefen.4", w1=', '.join(x['id'] for x in andere)))
        if status in ("verworfen", "ersetzt") and o["status"] == "gewaehlt" and not andere:
            hinweise.append(tk("konnektor.entscheidung_pruefen.13", oid=oid, w2=w['id'])
                            + (tk("konnektor.ausgabe.entscheidung_pruefen.4", w1=w['frage']) if w.get("frage") else "") + ".")
        if status == "gewaehlt":
            namen = {k["id"]: k["name"] for k in w.get("kriterien") or []}
            if o.get("fehlt"):
                hinweise.append(tk("konnektor.entscheidung_pruefen.18") + ", ".join(namen.get(k, k) for k in o["fehlt"])
                                + tk("konnektor.entscheidung_pruefen.14"))
            offen = [namen.get(k, k) for k, v in (o.get("merkmale") or {}).items() if v.get("ungeprueft")]
            if offen:
                hinweise.append(tk("konnektor.entscheidung_pruefen.19") + ", ".join(offen) + tk("konnektor.ausgabe.entscheidung_pruefen.2"))
            # Quellen prüfen: geprüft, aber älter als die Frist des Wächters (regeln.waechter_frist_tage)
            frist = ((self.d.get("reise") or {}).get("regeln") or {}).get("waechter_frist_tage", VORGABEN["waechter_frist_tage"])
            veraenderlich = {k["id"] for k in w.get("kriterien") or [] if k.get("veraenderlich")}
            stichtag = heute or datetime.date.today()
            alt = []
            for k, v in (o.get("merkmale") or {}).items():
                for e in [v] + list(v.get("je_datum") or []):
                    g = e.get("geprueft")
                    if k in veraenderlich and g and (stichtag - datetime.date.fromisoformat(g)).days > frist:
                        alt.append(tk("konnektor.entscheidung_pruefen.20", w1=namen.get(k, k), w2=datum_de(g), w3=e.get('quelle') or 'unbekannt'))
            if alt:
                hinweise.append(tk("konnektor.entscheidung_pruefen.21", frist=frist) + ", ".join(alt) + tk("konnektor.ausgabe.entscheidung_pruefen.3"))
        # Regeln zwischen Optionen (Paket 4): nichts verhindern, aber sagen, was dann nicht mehr zusammenpasst
        if status == "gewaehlt":
            for x in o.get("erfordert") or []:
                if not x["im_plan"]:
                    hinweise.append(tk("konnektor.entscheidung_pruefen.25", oid=oid, w2=x['id'], w3=x['titel'])
                                    + ("" if x["gueltig"] else tk("konnektor.entscheidung_pruefen.27")) + ".")
            for x in o.get("schliesst_aus") or []:
                if x["im_plan"]:
                    hinweise.append(tk("konnektor.entscheidung_pruefen.29", oid=oid, id=x["id"], titel=x["titel"]))
        if status in ("verworfen", "ersetzt"):
            for w2 in self.r.get("wahlstellen", []):
                for o2 in w2["optionen"]:
                    if o2.get("im_plan") and o2["status"] not in ("verworfen", "ersetzt") and \
                            any(x["id"] == oid for x in o2.get("erfordert") or []):
                        hinweise.append(tk("konnektor.entscheidung_pruefen.22", w1=o2['id'], w2=o2['titel'], oid=oid))
        if w.get("wann") == "unterwegs" and not self.v["ausloeser_vor"]:
            hinweise.append(tk("konnektor.entscheidung_pruefen.15", w1=w['id'])
                            + (tk("konnektor.entscheidung_pruefen.23", w1=o['ausloeser']) if o.get("ausloeser") else "")
                            + tk("konnektor.entscheidung_pruefen.11"))
        heute = heute or datetime.date.today()
        text_ = (tkd("konnektor.entscheidung_pruefen.28", wer=wer, w2=datum_de(heute.isoformat()), oid=oid, w4=o['titel'], w5=w['id'], w6=w['titel'], w7=WORT[status]) + (tkd("konnektor.ausgabe.entscheidung_pruefen.ersetzt_durch", w1=durch) if durch else "") + tkd("konnektor.entscheidung_pruefen.26", grund=grund, wer=wer) + (tk("konnektor.ausgabe.entscheidung_pruefen.5", quelle=quelle) if quelle else "")
                 + tkd("konnektor.ausgabe.entscheidung_pruefen.einzutragen", w1=f"{{datum: {heute.isoformat()}, status: {status}, wer: {wer}, grund: …}}")
                 + (tkd("konnektor.entscheidung_pruefen.16", w1=', '.join(x['id'] for x in andere)) if status == "gewaehlt" and andere else "")
                 + (tkd("konnektor.entscheidung_pruefen.12", w1=w['frage']) if w.get("frage") and status == "gewaehlt" else "") + ".")
        if hinweise:
            text_ += tkd("konnektor.entscheidung_pruefen.5") + "\n".join(f"- {x}" for x in hinweise)
        daten = {"entscheidung": status, "option": oid, "wahlstelle": w["id"], "grund": grund, "datum": heute.isoformat(),
                 **({"ersetzt_durch": durch} if durch else {}), **({"quelle": quelle} if quelle else {}),
                 "hinweise": hinweise}
        return (text_, daten), hinweise, None

    def varianten(self):
        z = []
        for p in self.r.get("plaene", []):
            z.append(f"- {p['id']} {p['kurz']}: {p['titel']}" + (tk("konnektor.ausgabe.varianten.3") if p.get("aktuell") else "")
                     + tk("konnektor.ausgabe.varianten.2", w1=', '.join(p.get('auswahl') or [])))
        if z:
            z.insert(0, tk("konnektor.varianten.1"))
        z.append(tk("konnektor.ausgabe.varianten.1"))
        for w in self.r.get("wahlstellen", []):
            z.append(f"### {w['id']} {w['titel']} ({w.get('art')}" + (tk("konnektor.ausgabe.varianten.5") if w.get("offen") else "")
                     + (tk("konnektor.ausgabe.varianten.4", w1=w['frage']) if w.get("frage") else "") + ")")
            if w.get("text"):
                z.append(w["text"])
            for o in w["optionen"]:
                z.append(f"- {o['id']} {o['titel']} – {o.get('status')}" + (tk("konnektor.ausgabe.aktuell") if o.get("aktiv") else "")
                         + (tk("konnektor.varianten.2", w1='; '.join(o['plus'])) if o.get("plus") else "")
                         + (tk("konnektor.ausgabe.dagegen", w1='; '.join(o['minus'])) if o.get("minus") else "")
                         + (f"; {self.summe(o['summe'])}" if o.get("summe") else ""))
                z += ["  " + x for x in self.merkmal_zeilen(w.get("kriterien"), o.get("merkmale"))
                      if not x.startswith(tk("konnektor.ausgabe.merkmal_zeilen.2"))]
                z += ["  " + x for x in self.offen_zeilen(o["id"])]
        return "\n".join(z)


# ---------- Rückmeldungen und Aufträge ----------

def ausstehend_datei():
    """Links neuer Reisen, die veroeffentlichen.sh zustellt (betrieb/zustellen.py), sobald die Seite online ist. Liegt
    neben den Zugängen im Ordner des Konnektors: Nur den darf der Konnektor beschreiben, der Dienstordner ist für ihn
    schreibgeschützt (betrieb/vorlagen/konnektor.service)."""
    return Path(os.environ.get("KN_AUSSTEHEND") or zugaenge_pfad().with_name("neue-reisen-ausstehend.jsonl"))


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
            antwort = json.loads(r.read())
        if isinstance(antwort, dict) and antwort.get("text_teile"):   # Bestätigung in der Sprache der Person (ADR-0006)
            antwort["text"] = texte.Satz.aus_json(antwort["text_teile"]).text(texte.aufruf_sprache())
        return antwort, None
    except urllib.error.HTTPError as e:
        try:
            antwort = json.loads(e.read())
            werte = {n: texte.Satz.aus_json(v["satz"]) if isinstance(v, dict) and "satz" in v else v
                     for n, v in (antwort.get("werte") or {}).items()}
            return None, texte.Satz(antwort.get("fehler", f"Fehler {e.code}"), antwort.get("fehler_code"), werte)
        except (json.JSONDecodeError, AttributeError):
            return None, tk("konnektor.ausgabe.schreib_anfrage.1", w1=e.code)
    except (urllib.error.URLError, OSError):
        return None, tk("konnektor.schreib_anfrage.1")


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
            v = tkd("konnektor.ausgabe.ontologie.aus") if s == "aus" else stufe_wort(s) if s else v
        teile.append(f"{f}: {' | '.join(map(str, v)) if isinstance(v, list) else v}")
    return tkd({"art_definieren": "konnektor.ausgabe.ontologie.art", "kategorie_definieren": "konnektor.ausgabe.ontologie.kategorie"}.get(name, "konnektor.ausgabe.ontologie.merkmal")) + " – " + "; ".join(teile)


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
    krit = ((d.get("route") or {}).get("merkmale") or {}).get(art)
    if krit is None:   # die Art ist der Seite noch nicht bekannt (gerade angelegt): der Schreibweg prüft mit dem Repo
        return None
    bekannt = {k["id"] for k in krit} | {x for k in krit for x in (k.get("auch") or [])}
    fremd = [str(k) for k in merkmale if str(k).lower() not in bekannt]
    if not fremd:
        return None
    z = []
    for k in fremd:
        a = aehnliches_merkmal(k, krit)
        z.append(tk("konnektor.merkmal_hinweise.1", k=k, art=art) + (tk("konnektor.ausgabe.gemeint_wohl", w1=a['id'], w2=a['name']) if a else
                 tk("konnektor.merkmal_hinweise.2")))
    return tk("konnektor.ausgabe.merkmal_hinweise.1") + "; ".join(z) + "."


def hinweise_text(antwort):
    """Neue Warnungen des Probebaus (Feld hinweise des Schreibwegs, Issue #142) als Absatz; kein Fehler, eingetragen ist trotzdem."""
    antwort = antwort or {}
    h = [texte.Satz.aus_json(x).text(texte.aufruf_sprache()) if isinstance(x, list) else str(x) for x in antwort.get("hinweise_teile") or []] \
        or antwort.get("hinweise") or []
    return (tk("konnektor.ausgabe.hinweise_text.1") + "\n".join(f"- {x}" for x in h)) if h else ""


def ontologie_werkzeug(reise, d, wer, zugang, name, args):
    """Werkzeuge, die direkt in die Reise schreiben (ADR-0001, O-3; engine/schreiben.py): Rolle und Status prüft der Konnektor vor dem
    Senden, der Schreibweg noch einmal mit reise.yaml. art_definieren und merkmal_definieren gehen für Mitwirkende als Rückmeldung
    der Art Ergänzung (Vorschlag). -> (Text, ist_fehler)"""
    if not all(isinstance(v, (str, bool, int, float, list, dict, type(None))) for v in args.values()):
        return tk("konnektor.ontologie_werkzeug.3"), True
    aktion = ONTOLOGIE_AKTION[name]
    vorschlag = aktion == "ontologie" and not darf(wer["rolle"], "organisator")
    if (nein := recht(wer["rolle"], d, "rueckmeldung" if vorschlag else aktion)):
        return nein, True
    if not schreibdienst():
        return (tk("konnektor.ontologie_werkzeug.4")), True
    name_ = wer["name"] or args.get("name") or args.get("vorname")
    if not isinstance(name_, str) or not name_.strip():
        return (tk("konnektor.ontologie_werkzeug.7")
                if aktion == "ontologie" and not vorschlag else tk("konnektor.frage_beantworten.4")), True
    wer = {**wer, "name": name_.strip()}
    rest = {k: v for k, v in args.items() if k not in ("name", "vorname", "trotzdem") and not k.startswith("beleg_")}   # ein neuer Name eines Dings heißt neuer_name
    if vorschlag:
        ziel = art_schluessel(str(args.get("kategorie") or args.get("art") or args.get("bezeichnung") or "")) or "allgemein"
        e, fehler = rueckmeldung_senden(reise, {"name": wer["name"], "art": tkd("konnektor.ontologie_werkzeug.8"), "ziel": ziel[:rm.LAENGE["ziel"]],
                                                "text": ontologie_text(name, rest)[:rm.LAENGE["text"]], "quelle": tkd("konnektor.werkzeug.4")})
        if fehler:
            return tk("konnektor.ausgabe.frage_beantworten.4", fehler=fehler), True
        organisator = tk("konnektor.und").join(organisator_namen(d)) or tk("konnektor.ausgabe.frage_beantworten.1")
        return (tk("konnektor.ontologie_werkzeug.5", w1=e['id'], organisator=organisator)), False
    # Vorprüfungen mit dem veröffentlichten Stand (der Schreibweg prüft noch einmal mit dem Repo)
    route = d.get("route") or {}
    if name == "merkmal_definieren" and not args.get("trotzdem"):
        art = str(args.get("art") or "").strip().lower()
        bereich = "buchung_merkmale" if str(args.get("fuer") or "").strip().lower() == "buchung" else "merkmale"
        krit = (route.get(bereich) or {}).get(art) or []
        key = art_schluessel(str(args.get("merkmal") or args.get("bezeichnung") or ""))
        if key and key not in {k["id"] for k in krit}:
            aehnlich = aehnliches_merkmal(key, krit)
            if aehnlich:
                return (tk("konnektor.ontologie_werkzeug.12", art=art, w2=aehnlich['id'], w3=aehnlich['name'])), True
    # Was die veröffentlichte Seite noch nicht kennt (gerade angelegt, Issue #135), prüft der Schreibweg mit dem Repo: hier
    # keine Ablehnung wegen einer unbekannten ID, nur Hinweise, die der veröffentlichte Stand sicher weiß
    if name == "arten_uebernehmen":
        # nur Reisen derselben Person (Product Owner 28.10.2026): Konto oder Zugang muss auf beiden Reisen stehen
        von = str(args.get("von_reise") or "").strip()
        dv = daten(von) if rm.REISE_MUSTER.match(von) else None
        if not dv or von == reise:
            return tk("konnektor.ontologie_werkzeug.9", von=von), True
        if wer_spricht({**zugang, "reise": von}, dv) is None:
            return tk("konnektor.ontologie_werkzeug.10", von=von), True
    if name == "wunsch_vorschlagen":
        rid = str(args.get("wunsch") or "").strip()
        if not any(w.get("id") == rid for w in (wuensche_liste(reise) or [])):
            return tk("konnektor.ontologie_werkzeug.11", rid=rid), True
    if name == "ding_anlegen":
        if (h := merkmal_hinweise(d, str(args.get("art") or "").lower(), args.get("merkmale"))):
            return h, True
    if name == "option_anlegen":
        vid = str(args.get("wahlstelle") or "").strip()
        w = next((w for w in route.get("wahlstellen") or [] if w["id"] == vid), None)
        if w is not None and (h := merkmal_hinweise(d, w.get("art"), args.get("merkmale"))):
            return h, True
    beleg = {k: v for k, v in args.items() if k.startswith("beleg_") and v}
    if beleg and name != "buchung_anlegen":
        return tk("konnektor.ontologie_werkzeug.6"), True
    if beleg and beleg_daten(args, "beleg_")[0] is None:   # Beleg vorher prüfen: die Buchung soll nicht ohne ihn angelegt werden
        return beleg_daten(args, "beleg_")[1], True
    antwort, fehler = schreib_anfrage(reise, name, {"person": zugang.get("person"), "name": wer["name"], "rolle": wer["rolle"], "args": rest})
    if fehler:
        return tk("konnektor.ausgabe.ontologie_werkzeug.1", fehler=fehler), True
    text = (tk("konnektor.ontologie_werkzeug.1", w1=wer['name'], w2=antwort.get('text', ''))) + hinweise_text(antwort)
    if beleg:   # in einem Schritt (Issue #135): die Buchung ist im Repo, der Beleg geht sofort in die Ablage
        bid = str(antwort.get("id") or "")
        if not re.fullmatch(r"B-\d+", bid):
            return text + tk("konnektor.ontologie_werkzeug.13"), False
        bt, bf = beleg_ablegen(reise, bid, wer["name"], args, im_repo=True, praefix="beleg_")
        return text + (" " + bt if not bf else tk("konnektor.ontologie_werkzeug.14", bt=bt)), False
    if name == "buchung_anlegen":
        text += tk("konnektor.ontologie_werkzeug.2")
    return text, False


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
            return None, tk("konnektor.ausgabe.schreib_anfrage.1", w1=e.code)
    except (urllib.error.URLError, OSError):
        return None, tk("konnektor.dienst_anfrage.1")


def beleg_daten(args, praefix=""):
    """Abschrift (text) oder Datei (daten_base64) aus der Anfrage -> (dateiname, bytes) oder (None, fehler)."""
    text, b64 = str(args.get(praefix + "text") or ""), str(args.get(praefix + "base64" if praefix else "daten_base64") or "").strip()
    if b64:
        import base64, binascii
        try:
            inhalt = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError):
            return None, tk("konnektor.beleg_daten.1", w1=praefix + 'base64' if praefix else 'daten_base64')
        return str(args.get(praefix + "dateiname") or "Beleg").strip(), inhalt
    if text.strip():
        dateiname = str(args.get(praefix + "dateiname") or "Abschrift").strip()
        if not dateiname.lower().endswith((".txt", ".md")):
            dateiname += ".txt"
        return dateiname, text.strip().encode("utf-8") + b"\n"
    return None, (tk("konnektor.ausgabe.beleg_daten.1", praefix=praefix, w2=praefix + 'base64' if praefix else 'daten_base64'))


def beleg_ablegen(reise, bid, name, args, im_repo=False, praefix=""):
    """Beleg aus der Anfrage an die Buchung hängen -> (Text, ist_fehler)."""
    dateiname, inhalt = beleg_daten(args, praefix)
    if dateiname is None:
        return inhalt, True
    a, fehler = beleg_senden(reise, bid, name, dateiname, inhalt, im_repo)
    if fehler:
        return tk("konnektor.ausgabe.beleg_ablegen.1", fehler=fehler), True
    return (tk("konnektor.beleg_ablegen.1", w1=a['id'], w2=a['name'], bid=bid, w4=a.get('groesse', 0), name=name)), False


def buchung_im_repo(reise, bid):
    """Gibt es die Buchung schon im Repo, auch wenn die Seite sie noch nicht zeigt? Fragt den Schreibweg (GET /<reise>/buchung/<B-id>).
    -> (True | False | None, fehler); None: nicht prüfbar."""
    if not schreibdienst():
        return None, tk("konnektor.buchung_im_repo.1")
    req = urllib.request.Request(f"{schreibdienst()}/{reise}/buchung/{bid}", headers={"X-Frieda-Dienst": konten.dienst_geheimnis()})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return bool(json.loads(r.read()).get("gibt_es")), None
    except urllib.error.HTTPError as e:
        return None, tk("konnektor.ausgabe.buchung_im_repo.1", w1=e.code)
    except (urllib.error.URLError, OSError, ValueError):
        return None, tk("konnektor.schreib_anfrage.1")


def beleg_senden(reise, bid, name, dateiname, daten, im_repo=False):
    """Datei an den Rückmeldedienst (einziger Schreiber der Ablage): POST /<reise>/belege/<B-id>, Body ist die Datei. -> (antwort, fehler)
    im_repo: die Buchung ist im Repo geprüft, aber noch nicht veröffentlicht (gerade angelegt); der Dienst nimmt sie dann trotzdem an."""
    basis = os.environ.get("KN_RUECKMELDEDIENST", "http://127.0.0.1:8771").rstrip("/")
    req = urllib.request.Request(f"{basis}/{reise}/belege/{bid}?name={urllib.parse.quote(name)}", method="POST", data=daten,
                                 headers={"Content-Type": "application/octet-stream", "X-Frieda-Dienst": konten.dienst_geheimnis(),
                                          "X-Frieda-Datei": urllib.parse.quote(dateiname), **({"X-Frieda-Buchung": "im-repo"} if im_repo else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        try:
            return None, json.loads(e.read()).get("fehler", f"Fehler {e.code}")
        except (json.JSONDecodeError, AttributeError):
            return None, tk("konnektor.ausgabe.schreib_anfrage.1", w1=e.code)
    except (urllib.error.URLError, OSError):
        return None, tk("konnektor.dienst_anfrage.1")


def brett_text(b, titel=None):
    """Wunsch-Brett als Text für die Claude-App: Spalten mit Wünschen, dann Bilanz je Person."""
    titel = titel or {}
    k = b["kontingent"]
    punkte = k["art"] == "punkte"
    stelle = lambda ids: ", ".join(f"{x} {titel[x]}" if titel.get(x) else x for x in ids)
    z = [tk("konnektor.ausgabe.brett_text.2") + (tk("konnektor.brett_text.2", w1=k['je_person']) if punkte else
                                tk("konnektor.brett_text.3", w1=k['je_person'])) + ")"]
    for sp in b["spalten"]:
        liste = [w for w in b["wuensche"] if w["spalte"] == sp["id"]]
        z.append(f"### {sp['titel']} ({len(liste)})")
        for w in sorted(liste, key=lambda w: -w["punkte"]):
            z.append(f"- {w['id']} · {w['name']}" + (tk("konnektor.ausgabe.brett_text.7", w1=w['punkte']) if punkte and w["punkte"] else "") + f": {w['text']}")
            if w["status"] == "rueckfrage":
                z.append(tk("konnektor.brett_text.4", w1=w['kommentar']))
            elif w["kommentar"]:
                z.append(tk("konnektor.ausgabe.brett_text.5", w1=w['kommentar']))
            v = w.get("vorschlag") or {}
            if v.get("bezug") or v.get("notiz") or v.get("option"):
                z.append(tk("konnektor.ausgabe.brett_text.6") + "; ".join(x for x in (
                    tk("konnektor.ausgabe.passt_zu", w1=stelle(v['bezug'])) if v.get("bezug") else "",
                    f"Option {v['option']}" + (tk("konnektor.option.gewaehlt") if v.get("gewaehlt") else tk("konnektor.option.zur_wahl")) if v.get("option") else "",
                    v.get("notiz") or "") if x))
            if w.get("eingeplant"):
                e = w["eingeplant"]
                z.append(tk("konnektor.brett_text.6", w1=e['wer'], w2=e['datum']) + (f": {stelle(e['bezug'])}" if e.get("bezug") else ""))
            if w.get("erlebt"):
                z.append(tk("konnektor.ausgabe.brett_text.3", w1=w['erlebt']['wer'], w2=w['erlebt']['datum']))
    z.append(tk("konnektor.ausgabe.brett_text.1"))
    for p in b["bilanz"]:
        z.append(tk("konnektor.brett_text.1", w1=p['name'], w2=p['wuensche'], w3=p['eingeplant'], w4=p['erlebt'])
                 + (tk("konnektor.ausgabe.brett_text.4", w1=p['frei'], w2=k['je_person']) if punkte else tk("konnektor.brett_text.5", w1=p['frei'])))
    return "\n".join(z)


def wuensche_liste(reise):
    """Alle Wünsche der Reise (Brett), für Vorprüfungen -> Liste oder []."""
    o = rm.ordner(reise)
    return rm.brett(o, rm.zustand(reise))["wuensche"] if o else []


def wuensche_kurz(reise):
    """Eine Zeile für den Überblick: wie viele Wünsche in welcher Spalte."""
    o = rm.ordner(reise)
    if o is None:
        return ""
    b = rm.brett(o, rm.zustand(reise))
    if not b["wuensche"]:
        return tk("konnektor.wuensche_kurz.1")
    zahl = {s["titel"]: sum(1 for w in b["wuensche"] if w["spalte"] == s["id"]) for s in b["spalten"]}
    return (tk("konnektor.wuensche_kurz.2", w1=len(b['wuensche'])) + ", ".join(f"{t.lower()} {n}" for t, n in zahl.items() if n)
            + tk("konnektor.ausgabe.wuensche_kurz.1"))


def aufgaben_von(reise):
    o = rm.ordner(reise)
    return sorted(rm.aufgaben(o), key=rm.ag_sortierung) if o else []


def aufgabe_text(a, titel):
    """Eine Aufgabe ausführlich, mit Verlauf."""
    z = [rm.aufgaben_text([a], titel)]
    z.append(tk("konnektor.ausgabe.aufgabe_text.1", w1=a['erstellt'][:10], w2=a.get('erstellt_von'))
             + (tk("konnektor.ausgabe.aufgaben.1", w1=a['erledigt']) if a.get("erledigt") else ""))
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
                            "quelle": tkd("konnektor.stehende_entscheidungen.1", w1=v['wer'], w2=v.get('datum'))})
    ordner = rm.ordner(reise)
    for a in rm.auftraege(ordner) if ordner else []:
        ent = (a.get("daten") or {}).get("entscheidung")
        if ent in ENTSCHEIDUNGEN and a["status"] in ("neu", "rueckfrage", "konflikt"):
            aus.append({"wer": a.get("name"), "ziel": a.get("ziel"), "entscheidung": ent, "auftrag": a["id"],
                        "quelle": tkd("konnektor.ausgabe.stehende_entscheidungen.1", w1=a['id'], w2=a.get('name'))})
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
        return (tk("konnektor.entscheiden.2")), True
    if not all(isinstance(args.get(k) or "", str) for k in ("option", "status", "grund", "ersetzt_durch", "quelle")):
        return tk("konnektor.entscheiden.3"), True
    ergebnis, hinweise, fehler = h.entscheidung_pruefen(args, wer["name"])
    if fehler:
        return tk("konnektor.ausgabe.entscheiden.1") + "\n".join(f"- {f}" for f in fehler), True
    text_, daten_ = ergebnis
    wort = WORT[daten_["entscheidung"]]
    if schreibdienst():
        beschr, alt = konflikt_pruefen(reise, d, wer["name"], daten_["option"], daten_["entscheidung"])
        if beschr:
            frage = (tk("konnektor.entscheiden.4", w1=daten_['option'], w2=wer['name'], wort=wort, w4=daten_['grund'], beschr=beschr))
            antwort, fehler = schreib_anfrage(reise, "frage_anlegen", {"person": wer.get("person"), "name": wer["name"], "rolle": wer["rolle"],
                                                                       "args": {"text": frage, "bis": tkd("konnektor.ausgabe.entscheiden.4"), "bezug": [daten_["wahlstelle"]]}})
            m_ = re.search(r"\bF-\d+\b", (antwort or {}).get("text", "")) if antwort else None
            fid = m_.group(0) if m_ else None
            o = rm.ordner(reise)
            organisator = set(organisator_namen(d)) & ({wer["name"]} | {x["wer"] for x in alt})
            if o is not None:
                rm.meldung_anlegen(o, organisator or {wer["name"]}, "konflikt", daten_["option"],
                                   tk("konnektor.entscheiden.8", w1=wer['name'], w2=daten_['entscheidung'], w3=daten_['option'], beschr=beschr) + (tk("konnektor.ausgabe.entscheiden.5", fid=fid) if fid else "") + ".", [])
            return (tk("konnektor.entscheiden.7", w1=daten_['option'], wort=wort, beschr=beschr) + (tk("konnektor.entscheiden.9", w1=' ' + fid if fid else '') if antwort and not fehler
                                                               else tk("konnektor.entscheiden.10"))
                    + tk("konnektor.entscheiden.6")), False
        rest = {k: args[k] for k in ("option", "status", "grund", "ersetzt_durch", "quelle") if args.get(k)}
        antwort, fehler = schreib_anfrage(reise, "entscheiden", {"person": wer.get("person"), "name": wer["name"], "rolle": wer["rolle"], "args": rest})
        if fehler:
            return tk("konnektor.ausgabe.entscheiden.2", fehler=fehler), True
        z = [tk("konnektor.entscheiden.5", w1=antwort.get('text', ''))]
        if hinweise:
            z.append(tk("konnektor.ausgabe.entscheiden.3") + "\n".join(f"- {x}" for x in hinweise))
        return "\n".join(z) + hinweise_text(antwort), False
    return (tk("konnektor.entscheiden.1")), True


def frage_beantworten(reise, d, h, wer, args):
    """Werkzeug frage_beantworten: Die Antwort geht als Rückmeldung (Art Antwort) an die Frage. Sie ist eine Eingabe;
    ob die Frage geklärt ist, entscheidet ein:e Organisator:in. -> (Text, ist_fehler)"""
    if (nein := recht(wer["rolle"], d, "rueckmeldung")):
        return nein, True
    fid = args.get("frage")
    antwort = args.get("antwort")
    if not isinstance(fid, str) or not isinstance(antwort, str) or not isinstance(args.get("quelle") or "", str):
        return tk("konnektor.frage_beantworten.1"), True
    fid, antwort = fid.strip(), antwort.strip()
    zeile = next((z for z in (h.d.get("fragen") or {}).get("zeilen", []) if z["id"] == fid), None)
    if zeile is None:
        return tk("konnektor.frage_beantworten.2", fid=fid), True
    if not zeile.get("status", "").lower().startswith("offen"):
        return (tk("konnektor.frage_beantworten.3", fid=fid, w2=zeile.get('status'))), True
    if not antwort:
        return tk("konnektor.ausgabe.frage_beantworten.2"), True
    name_ = wer["name"] or args.get("name")
    if not isinstance(name_, str) or not name_.strip():
        return tk("konnektor.frage_beantworten.4"), True
    e, fehler = rueckmeldung_senden(reise, {"name": name_, "art": tkd("konnektor.ausgabe.frage_beantworten.3"), "ziel": fid, "text": antwort,
                                            "quelle": str(args.get("quelle") or tkd("konnektor.werkzeug.4"))})
    if fehler:
        return tk("konnektor.ausgabe.frage_beantworten.4", fehler=fehler), True
    stelle = next((w for w in h.r.get("wahlstellen", []) if w.get("frage") == fid), None)
    organisator = tk("konnektor.und").join(organisator_namen(d)) or tk("konnektor.ausgabe.frage_beantworten.1")
    z = [tk("konnektor.frage_beantworten.7", id=e["id"], fid=fid, organisator=organisator)]
    if stelle:
        z.append(tk("konnektor.frage_beantworten.5", w1=stelle['id'], w2=stelle['titel'])
                 + (tk("konnektor.frage_beantworten.6") if darf(wer["rolle"], "organisator") else ""))
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
            return tk("konnektor.einladen.24"), True
    vorname = args.get("vorname")
    rolle = rolle_neu(args.get("rolle") or "mitwirkend")
    notiz = args.get("notiz") or ""
    if not isinstance(vorname, str) or not isinstance(rolle, str) or not isinstance(notiz, str) \
            or not isinstance(args.get("schluessel") or "", str):
        return tk("konnektor.einladen.2"), True
    vorname, notiz = vorname.strip(), notiz.strip()
    if not vorname or "\n" in vorname or len(vorname) > rm.LAENGE["name"]:
        return tk("konnektor.einladen.3"), True
    if len(notiz) > 300 or "\n" in notiz:
        return tk("konnektor.einladen.4"), True
    if rolle not in ROLLEN:
        return tk("konnektor.einladen.5", w1=', '.join(ROLLEN)), True
    name_von = wer["name"]
    if not name_von:
        return (tk("konnektor.einladen.6")), True
    if not mit_konto and not os.environ.get("KN_BASIS"):
        return tk("konnektor.einladen.7"), True
    o = rm.ordner(reise)
    if o is None:
        return tk("konnektor.einladen.8"), True
    personen = personen_der_reise(reise, d)
    vorhanden = next((p for p in personen if p["name"].casefold() == vorname.casefold()
                      or p["schluessel"] == (args.get("schluessel") or "").strip()), None)
    if vorhanden:
        if args.get("rolle") and rolle != vorhanden["rolle"]:
            # Rolle ändern: eine Einstellung der Reise, nur Organisator:innen, direkt nach reise.yaml (person_schreiben)
            if not darf(wer["rolle"], "organisator"):
                return tk("konnektor.einladen.25", w1=vorhanden['name'], w2=vorhanden['rolle']), True
            if not schreibdienst():
                return tk("konnektor.einladen.26", w1=vorhanden['name'], w2=vorhanden['rolle']), True
            a_, fehler = schreib_anfrage(reise, "person_schreiben", {"person": wer.get("person"), "name": wer["name"], "rolle": wer["rolle"],
                                                                     "args": {"schluessel": vorhanden["schluessel"], "rolle": rolle}})
            if fehler:
                return tk("konnektor.einladen.27", fehler=fehler), True
            return (tk("konnektor.einladen.13", w1=vorhanden['name'], rolle=rolle, w3=vorhanden['rolle'])), False
        rolle, neu = vorhanden["rolle"], False
        schluessel = vorhanden["schluessel"]
    else:
        schluessel = (args.get("schluessel") or "").strip() or schluessel_aus_name(vorname)
        if not PERSON_MUSTER.match(schluessel):
            return (tk("konnektor.einladen.14")), True
        neu = True
    if neu and not darf(wer["rolle"], rolle):
        return (tk("konnektor.einladen.9", w1=wer['rolle'], rolle=rolle)), True
    if not neu and not darf(wer["rolle"], rolle):
        return tk("konnektor.einladen.10", w1=vorhanden['name'], rolle=rolle), True
    if neu:
        with _sperre:
            if len(rm.einladungen_lesen(o)) >= rm.MAX_EINLADUNGEN:
                return tk("konnektor.einladen.28"), True
    if mit_konto:
        # Eine Person, die schon in der Reise steht, mit einem Konto verknüpfen heißt: wer die Adresse hat, spricht als sie.
        # Deshalb nur durch Organisator:innen, und Organisator:innen selbst verknüpft nur der Betreiber (konten.py einladen), sonst könnte
        # man sich per eigener Adresse als eine andere Organisator:in ausgeben (Prüfung J3, 27.10.2026).
        if not neu and not darf(wer["rolle"], "organisator"):
            return (tk("konnektor.einladen.15")), True
        if not neu and vorhanden["rolle"] == "organisator":
            return (tk("konnektor.einladen.16", w1=vorhanden['name'])), True
        return einladen_per_mail(reise, d, o, wer, args, vorname if neu else vorhanden["name"], rolle, schluessel, neu,
                                 notiz, email)
    try:
        token = zugang_ausstellen({"reise": reise, "person": schluessel})
    except OSError:
        return (tk("konnektor.einladen.17")), True
    link = f"{basis()}/{token}"
    heute = datetime.date.today().isoformat()
    if neu:
        eintrag = {"name": vorname, "rolle": rolle, "reist": args.get("reist", True) is not False,
                   "notiz": notiz or tkd("konnektor.einladen.18", name_von=name_von, w2=datum_de(heute)),
                   "eingeladen_von": name_von, "datum": heute}
        with _sperre:
            alle = rm.einladungen_lesen(o)
            alle[schluessel] = eintrag
            rm.schreiben(o / "einladungen.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
        text_ = (tkd("konnektor.einladen.1", name_von=name_von, vorname=vorname, rolle=rolle, schluessel=schluessel, w5='ja' if eintrag['reist'] else 'nein', w6=eintrag['notiz']))
        person_sichern(reise, wer, text_, schluessel, eintrag, name_von)
    z = [(tk("konnektor.ausgabe.einladen.eingeladen", w1=vorname) if neu else tk("konnektor.einladen.19", w1=vorhanden['name'])) + tk("konnektor.ausgabe.einladen.1", rolle=rolle),
         link, "",
         tk("konnektor.einladen.20") + vorname + tk("konnektor.einladen.11"),
         {"gast": tk("konnektor.einladen.21"),
          "mitwirkend": tk("konnektor.einladen.22"),
          "organisator": tk("konnektor.einladen.23")}[rolle]]
    if neu:
        z.append(tk("konnektor.einladen.12"))
    return "\n".join(z), False


def person_sichern(reise, wer, text_, schluessel, eintrag, name_von):
    """Neue Person nach reise.yaml über den Schreibweg (person_schreiben). Scheitert das, gilt die Person trotzdem schon
    (einladungen.json); der Fehler steht im Protokoll und als Meldung an die Organisator:innen."""
    if not schreibdienst():
        sys.stderr.write(f"person_schreiben {reise}/{schluessel}: no write path (KN_SCHREIBDIENST)\n")
        return
    a, fehler = schreib_anfrage(reise, "person_schreiben", {"person": wer.get("person"), "name": name_von, "rolle": wer["rolle"],
                                                            "args": {"schluessel": schluessel, "vorname": eintrag["name"], "rolle": eintrag["rolle"],
                                                                     "reist": eintrag.get("reist", True), "notiz": eintrag.get("notiz")}})
    if fehler:
        sys.stderr.write(f"person_schreiben {reise}/{schluessel}: {fehler}\n")
        o = rm.ordner(reise)
        if o is not None:
            rm.meldung_anlegen(o, [name_von], "technik", "reise", tk("konnektor.person_sichern.1", w1=eintrag['name'], fehler=fehler))


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
        return tk("konnektor.person_entfernen.1"), True
    if not wer["name"] or p["name"].casefold() == wer["name"].casefold():
        return tk("konnektor.person_entfernen.2"), True
    if p["rolle"] == "organisator":
        return (tk("konnektor.person_entfernen.3", w1=p['name'])), True
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
            return tk("konnektor.person_entfernen.5"), True
        a, fehler = schreib_anfrage(reise, "person_schreiben", {"person": wer.get("person"), "name": wer["name"], "rolle": wer["rolle"],
                                                                "args": {"schluessel": p["schluessel"], "rolle": "gast", "reist": False,
                                                                         "notiz": tkd("konnektor.ausgabe.ausscheiden.1", w1=datum_de(datetime.date.today().isoformat(), texte.VORGABE_REISE), w2=wer['name'])
                                                                                  + (f": {grund}" if grund else "")}})
        if fehler:
            return tk("konnektor.person_entfernen.6", fehler=fehler), True
    return (tk("konnektor.person_entfernen.4", w1=p['name'])
            + ("" if p.get("eingeladen") else tk("konnektor.person_entfernen.7"))), False


def einladen_per_mail(reise, d, o, wer, args, name, rolle, schluessel, neu, notiz, email):
    """Teil von einladen für den Konnektor „Frieda“: Person (falls neu) in einladungen.json und als Auftrag, dann die
    Einladung über engine/konten.py (Mail mit Hinweis zum Anmelden, gilt sofort, wenn die Adresse ein Konto hat)."""
    try:
        r = konten.einladen(reise, schluessel, email, rolle, name, wer["name"],
                            titel=((d or {}).get("reise") or {}).get("titel"), seite=seitenlinks().get(reise))
    except konten.KontoFehler as f:
        return tk("konnektor.ausgabe.einladen_per_mail.1", f=f), True
    if neu:
        heute = datetime.date.today().isoformat()
        eintrag = {"name": name, "rolle": rolle, "reist": args.get("reist", True) is not False,
                   "notiz": notiz or tkd("konnektor.einladen_per_mail.2", w1=wer['name'], w2=datum_de(heute)),
                   "eingeladen_von": wer["name"], "datum": heute}
        with _sperre:
            alle = rm.einladungen_lesen(o)
            alle[schluessel] = eintrag
            rm.schreiben(o / "einladungen.json", json.dumps(alle, ensure_ascii=False, indent=1) + "\n")
        person_sichern(reise, wer, tkd("konnektor.einladen_per_mail.1", w1=wer['name'], name=name, rolle=rolle, schluessel=schluessel, w5='ja' if eintrag['reist'] else 'nein', w6=eintrag['notiz']),
                       schluessel, eintrag, wer["name"])
    return ((tk("konnektor.ausgabe.einladen_per_mail.2", name=name, rolle=rolle) if neu else tk("konnektor.einladen_per_mail.6", name=name, rolle=rolle))
            + tk("konnektor.einladen_per_mail.3", email=email)
            + (tk("konnektor.einladen_per_mail.4")
               if r["sofort"] else tk("konnektor.einladen_per_mail.5"))), False


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
            z.append(tk("konnektor.ausgabe.meine_reisen.5"))
            z += [f"- {datum_de(m['erstellt'][:10])}: {m['text']}" for m in ms]
            z.append("")
    reisen = reisen_von(konto)
    z.append(tk("konnektor.ausgabe.meine_reisen.1", w1=len(reisen)) if reisen else tk("konnektor.meine_reisen.1"))
    for r in reisen:
        z.append(tk("konnektor.ausgabe.meine_reisen.2", w1=r['titel'], w2=r['untertitel'], w3=r['status'], w4=r['rolle']))
        z.append(tk("konnektor.ausgabe.meine_reisen.3", w1=r['seite'] or tk("konnektor.ausgabe.meine_reisen.7")))
        z.append(tk("konnektor.ausgabe.meine_reisen.4", w1=r['app'] or tk("konnektor.meine_reisen.2")))
    if o:
        offen = [e for e in rm.auftraege(o) if e.get("name") == konto["name"] and (e.get("daten") or {}).get("neue_reise")
                 and e["status"] in ("neu", "rueckfrage")]
        if offen:
            z += ["", tk("konnektor.ausgabe.meine_reisen.6")]
            z += [f"- {e['daten']['neue_reise']['titel']} ({e['id']}): "
                  + (tk("konnektor.ausgabe.wird_angelegt") if e["status"] == "neu" else tk("konnektor.meine_reisen.3", w1=e.get('kommentar') or tk("konnektor.ausgabe.siehe_betreiber")))
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
            return tk("konnektor.ausgabe.reise_anlegen.2", fehler=fehler), True
        if not schreibdienst():
            return (tk("konnektor.reise_anlegen.1")), True
        wer_text = ", ".join(p['name'] + " (" + p['rolle'] + ("" if p.get('reist', True) else ", " + tk("konnektor.ausgabe.einladen.reist_nicht_mit")) + ")"
                             for p in neu["personen"].values())
        text_ = (tkd("konnektor.ausgabe.reise_anlegen.5", w1=neu['titel'], w2=datum_de(neu['von']), w3=datum_de(neu['bis']))
                 + (tkd("konnektor.ausgabe.reise_anlegen.6", w1=neu['ziel']) if neu["ziel"] else "") + tkd("konnektor.ausgabe.reise_anlegen.3", wer_text=wer_text, w2=neu['pfad'])
                 + (tkd("konnektor.ausgabe.reise_anlegen.4", w1=neu['notiz']) if neu["notiz"] else ""))
        jetzt = datetime.datetime.now(datetime.timezone.utc)
        e = {"id": f"A-{jetzt:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}", "erstellt": jetzt.isoformat(timespec="seconds"),
             "name": konto["name"], "konto": konto["konto"], "art": tkd("konnektor.ausgabe.reise_anlegen.1"), "ziel": "allgemein",
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
                        return tk("konnektor.reise_anlegen.6", w1=x.get('vorname')), True
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
    # (veroeffentlichen.sh stellt sie zu, Datei neue-reisen-ausstehend.jsonl im Ordner des Konnektors)
    a, fehler = schreib_anfrage(neu["pfad"], "reise_anlegen", {"person": None, "name": konto["name"], "rolle": "organisator",
                                                               "args": {"auftrag": e}})
    with _sperre:
        rm.status_setzen(o, e["id"], "rueckfrage" if fehler else "uebernommen",
                         tk("konnektor.ausgabe.reise_anlegen.2", fehler=fehler) if fehler else tk("konnektor.reise_anlegen.2", w1=neu['pfad']))
        if not fehler:
            person = next(k_ for k_, p_ in neu["personen"].items() if p_["name"] == neu["wer"])
            ausstehend_datei().parent.mkdir(parents=True, exist_ok=True)
            with ausstehend_datei().open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ordner": neu["pfad"], "aid": e["id"], "name": konto["name"], "person": person}, ensure_ascii=False) + "\n")
    if fehler:
        return tk("konnektor.ausgabe.reise_anlegen.2", fehler=fehler), True
    return (tk("konnektor.reise_anlegen.3", w1=neu['titel'], w2=neu['pfad'])
            + (tk("konnektor.reise_anlegen.4") if e.get("einladen") else
               tk("konnektor.reise_anlegen.5")) + "."), False


# ---------- Konnektor „Frieda“ (Paket J3): ein Zugang für alle Reisen, angemeldet mit dem Konto (OAuth) ----------

REISEN_ANLEGEN_ANFRAGEN = {"name": "reisen_anlegen_anfragen", "description": "@konnektor.werkzeug.reisen_anlegen_anfragen", "inputSchema": {"type": "object", "properties": {}}}
KALENDER = {"name": "kalender", "description": "@konnektor.werkzeug.kalender",
            "inputSchema": {"type": "object", "properties": {
                "neu": {"type": "boolean", "description": "@konnektor.werkzeug.kalender.neu"}}}}
ANFRAGE_ENTSCHEIDEN = {"name": "anfrage_entscheiden", "description": "@konnektor.werkzeug.anfrage_entscheiden",
                       "inputSchema": {"type": "object", "properties": {
                           "email": {"type": "string", "description": "@konnektor.werkzeug.anfrage_entscheiden.email"},
                           "erlauben": {"type": "boolean", "description": "@konnektor.werkzeug.anfrage_entscheiden.erlauben"}},
                           "required": ["email", "erlauben"]}}
EMAIL_FELD = {"type": "string", "description": "@konnektor.feld.email_feld"}


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
    eigene.append(KALENDER)
    eigene.append(sprache_setzen_werkzeug(k["sprache"]))
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
                        "description": "@konnektor.feld.reise_ordner" if len(reisen) > 1 else "@konnektor.feld.reise_ordner_optional"}
        pflicht = [x for x in schema.get("required", []) if x != "name"]
        if n == "person_einladen":
            pflicht.append("email")
        if len(reisen) > 1:
            pflicht.append("reise")
        aus.append({**w, "inputSchema": {**schema, "properties": eig, "required": pflicht}})
    return aus


# Wie Frieda mit der Person spricht (28.10.2026): Kennungen sind für die Werkzeuge da, nicht für die Person.
# Alle Sätze der Anleitung stehen im Katalog (konnektor.anleitung.*, ADR-0006); hier bleiben nur die Bedingungen.
def anl(sprache, schluessel, **werte):
    return texte.t(sprache, "konnektor.anleitung." + schluessel, **werte)


STATUS_SAETZE = ("idee", "planung", "fest", "unterwegs", "danach", "archiv")   # Statuswerte, zu denen die Anleitung einen Satz hat


def anleitung_frieda(k, sprache=None):
    sprache = sprache or k.get("sprache") or texte.VORGABE_REISE
    reisen = reisen_des_kontos(k)
    z = [anl(sprache, "frieda.aufgabe_viele" if len(reisen) > 1 else "frieda.aufgabe_eine", name=k["name"], email=k["email"],
             kennungen=anl(sprache, "kennungen_regel"))]
    for reise, schl, d in reisen:
        z += ["", anl(sprache, "frieda.reise_kopf", reise=reise),
              anleitung({"reise": reise, "person": schl, "konto_id": k["id"], "sprache": sprache}, d)]
    if not reisen:
        z += ["", anl(sprache, "frieda.keine_reisen"), "", anl(sprache, "antwortsprache")]
    return "\n".join(z)


def meine_reisen_konto(k):
    z = []
    o = rm.ordner_neu()
    if o:
        ms = rm.meldungen_aktuell(o, k["name"])
        if ms:
            z += [tk("konnektor.ausgabe.meine_reisen.5"), *[f"- {datum_de(m['erstellt'][:10])}: {m['text']}" for m in ms], ""]
    reisen = reisen_des_kontos(k)
    z.append(tk("konnektor.ausgabe.meine_reisen.1", w1=len(reisen)) if reisen else
             tk("konnektor.meine_reisen_konto.1"))
    links = seitenlinks()
    for reise, schl, d in reisen:
        rs = d.get("reise") or {}
        p = next((x for x in personen_der_reise(reise, d) if x.get("schluessel") == schl), {})
        z.append(tk("konnektor.ausgabe.meine_reisen_konto.1", w1=rs.get('titel', reise), w2=rs.get('untertitel', ''), reise=reise, w4=(rs.get('status') or {}).get('wert'), w5=p.get('rolle', '?')))
        z.append(tk("konnektor.ausgabe.meine_reisen.3", w1=links.get(reise) or tk("konnektor.ausgabe.meine_reisen.7")))
    if konten.recht(k, "reise_anlegen"):
        z += ["", tk("konnektor.ausgabe.meine_reisen_konto.2")]
    if o:
        offen = [e for e in rm.auftraege(o) if e.get("konto_id") == k["id"] and (e.get("daten") or {}).get("neue_reise")
                 and e["status"] in ("neu", "rueckfrage")]
        if offen:
            z += ["", tk("konnektor.ausgabe.meine_reisen.6")]
            z += [f"- {e['daten']['neue_reise']['titel']} ({e['id']}): "
                  + (tk("konnektor.ausgabe.wird_angelegt") if e["status"] == "neu" else tk("konnektor.meine_reisen.3", w1=e.get('kommentar') or tk("konnektor.ausgabe.siehe_betreiber")))
                  for e in offen]
    if konten.recht(k, "betreiber"):
        bitten = konten.anfragen()
        if bitten:
            z += ["", tk("konnektor.ausgabe.meine_reisen_konto.3"),
                  *[tk("konnektor.ausgabe.anfrage_seit", w1=a['name'], w2=a['email'], w3=a['erstellt'][:10]) for a in bitten]]
    return "\n".join(z)


def frieda_werkzeug(k, name, args):
    args = dict(args) if isinstance(args, dict) else {}
    if name == "meine_reisen":
        return meine_reisen_konto(k), False
    if name == "reise_anlegen":
        if not konten.recht(k, "reise_anlegen"):
            return tk("konnektor.frieda_werkzeug.2"), True
        return reise_anlegen({"konto": schluessel_aus_name(k["name"]) or "person", "name": k["name"],
                              "konto_id": k["id"]}, args)
    if name == "reisen_anlegen_anfragen":
        st = konten.reisen_anlegen_anfragen(k["id"])
        if st == "offen":
            anmeldung.betreiber_melden(k)
        return {"offen": tk("konnektor.frieda_werkzeug.5"),
                "schon_erlaubt": tk("konnektor.ausgabe.frieda_werkzeug.3"),
                "abgelehnt": tk("konnektor.frieda_werkzeug.6")}[st], False
    if name == "kalender":
        return kalender_link(k, args.get("neu") is True)
    if name == "sprache_setzen":
        try:
            neu = konten.sprache_setzen(k["id"], args.get("sprache"))
        except konten.KontoFehler as f:
            return f.text(k["sprache"]), True
        return texte.t(neu, "konnektor.sprache_gesetzt", name=texte.sprache(neu).NAME), False
    if name == "anfrage_entscheiden":
        if not konten.recht(k, "betreiber"):
            return tk("konnektor.frieda_werkzeug.3"), True
        try:
            wer = konten.konto_per_email(args.get("email"))
        except konten.KontoFehler as f:
            return str(f), True
        if not wer:
            return tk("konnektor.frieda_werkzeug.4"), True
        konten.freischalten(wer["id"], ja=args.get("erlauben") is True)
        return tk("konnektor.ausgabe.frieda_werkzeug.jetzt" if args.get('erlauben') is True else "konnektor.ausgabe.frieda_werkzeug.weiterhin_keine", w1=wer['name']), False
    reisen = reisen_des_kontos(k)
    reise = args.pop("reise", None) or (reisen[0][0] if len(reisen) == 1 else None)
    if not reise:
        return tk("konnektor.ausgabe.frieda_werkzeug.2"), True
    schl = next((s_ for r, s_, _ in reisen if r == reise), None)
    if not schl:
        return tk("konnektor.frieda_werkzeug.1"), True
    args.pop("name", None)
    return werkzeug({"reise": reise, "person": schl, "konto_id": k["id"]}, name, args)


def kalender_link(k, neu=False):
    """Text für das Werkzeug kalender: persönlicher Abo-Link über alle Reisen (#77, engine/kalender.py)."""
    if not os.environ.get("KN_BASIS"):
        return tk("konnektor.kalender_link.1"), True
    url = kalender.abo_url(basis(), konten.kalender_token(k["id"], erneuern=neu))
    return ("\n".join([tk("konnektor.kalender.neu" if neu else "konnektor.kalender.link"),
                       tk("konnektor.ausgabe.kalender.iphone", w1=kalender.webcal(url)),
                       tk("konnektor.ausgabe.kalender.google", w1=kalender.google(url)),
                       tk("konnektor.ausgabe.kalender.outlook", w1=kalender.outlook(url, tk("kalender.abo_name"))),
                       tk("konnektor.ausgabe.kalender.url", w1=url),
                       tk("konnektor.kalender.hinweis")]),
            False)


def frieda_antwort(zugang, nid, methode, p, ok):
    k = konten.konto(zugang["konto_id"])
    if not k or k["gesperrt"]:
        return {"jsonrpc": "2.0", "id": nid, "error": {"code": -32001, "message": tk("konnektor.frieda_antwort.1")}}
    if methode == "initialize":
        gewuenscht = p.get("protocolVersion") if isinstance(p, dict) else None
        return ok({"protocolVersion": gewuenscht if gewuenscht in PROTOKOLLE else PROTOKOLLE[0],
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": "frieda", "title": tk("konnektor.ausgabe.frieda_antwort.1"), "version": "1", "icons": frieda_symbole()},
                   "instructions": schnittstelle.namen_im_text(anleitung_frieda(k))})
    if methode == "ping":
        return ok({})
    if methode == "tools/list":
        return ok({"tools": schnittstelle.aussen(lokalisiert(frieda_werkzeuge(k), k["sprache"]))})
    if methode == "tools/call":
        name_i, args_i = aufruf_intern(frieda_werkzeuge(k), p.get("name"), p.get("arguments"))
        t, fehler = frieda_werkzeug(k, name_i, args_i)
        return ok({"content": [{"type": "text", "text": antworttext(t)}], "isError": fehler})
    return {"jsonrpc": "2.0", "id": nid, "error": {"code": -32601, "message": f"unbekannt: {methode}"}}


MEINE_REISEN = {"name": "meine_reisen", "description": "@konnektor.werkzeug.meine_reisen",
                "inputSchema": {"type": "object", "properties": {}}}


def anleitung_konto(konto, sprache=None):
    sprache = sprache or konto.get("sprache") or texte.VORGABE_REISE
    return (anl(sprache, "konto.aufgabe", name=konto["name"], kennungen=anl(sprache, "kennungen_regel"))
            + " " + anl(sprache, "antwortsprache"))


def konto_antwort(konto, nid, methode, p, ok):
    if methode == "initialize":
        gewuenscht = p.get("protocolVersion") if isinstance(p, dict) else None
        return ok({"protocolVersion": gewuenscht if gewuenscht in PROTOKOLLE else PROTOKOLLE[0],
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": "frieda", "title": tk("konnektor.ausgabe.konto_antwort.1"), "version": "1",
                                  "icons": frieda_symbole()},
                   "instructions": schnittstelle.namen_im_text(anleitung_konto(konto))})
    if methode == "ping":
        return ok({})
    if methode == "tools/list":
        return ok({"tools": schnittstelle.aussen(lokalisiert([MEINE_REISEN, REISE_ANLEGEN], sprache_des_zugangs(konto)))})
    if methode == "tools/call":
        name, args = aufruf_intern([MEINE_REISEN, REISE_ANLEGEN], p.get("name"), p.get("arguments") if isinstance(p.get("arguments"), dict) else {})
        if name == "meine_reisen":
            t, fehler = meine_reisen(konto), False
        elif name == "reise_anlegen":
            t, fehler = reise_anlegen(konto, args)
        else:
            t, fehler = tk("konnektor.ausgabe.werkzeug.1", name=name), True
        return ok({"content": [{"type": "text", "text": antworttext(t)}], "isError": fehler})
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
        return tk("konnektor.liste_text.1")
    es = rm.eintraege(o) + (rm.auftraege(o) if mit_auftraegen else [])
    es.sort(key=lambda e: e.get("erstellt", ""), reverse=True)
    z = []
    ms = meldungen_fuer(reise, name, d)[:10]
    if ms:
        z.append(tk("konnektor.ausgabe.liste_text.1"))
        z += [f"- {m['erstellt'][:10]} {m['art']} zu {m['ziel']}: {m['text']}" for m in ms]
        z.append(tk("konnektor.liste_text.2"))
    if not es:
        return "\n".join(z + [tk("konnektor.rueckmeldungen.keine")])
    for e in es[:50]:
        z.append(tk("konnektor.ausgabe.liste_text.2", w1=e['id'], w2=e['erstellt'][:10], w3=e.get('name'), w4=e.get('art'), w5=e.get('ziel'), w6=e['status']) + (f" – {e['kommentar']}" if e.get("kommentar") else ""))
        z.append("  " + e.get("text", "").replace("\n", " ")[:300])
    return "\n".join(z)


# ---------- MCP ----------

ZIEL_FELD = {"type": "string", "description": "@konnektor.feld.ziel_feld"}

WERKZEUGE = [
    {"name": "ueberblick", "description": "@konnektor.werkzeug.ueberblick",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "zeige", "description": "@konnektor.werkzeug.zeige",
     "inputSchema": {"type": "object", "properties": {"id": ZIEL_FELD}, "required": ["id"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "suche", "description": "@konnektor.werkzeug.suche",
     "inputSchema": {"type": "object", "properties": {"begriff": {"type": "string"}}, "required": ["begriff"]},
     "annotations": {"readOnlyHint": True}},
    {"name": "offene_fragen", "description": "@konnektor.werkzeug.offene_fragen",
     "inputSchema": {"type": "object", "properties": {"alle": {"type": "boolean", "description": "@konnektor.werkzeug.offene_fragen.alle"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "varianten", "description": "@konnektor.werkzeug.varianten",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "rueckmeldungen", "description": "@konnektor.werkzeug.rueckmeldungen",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "rueckmeldung_geben", "description": "@konnektor.werkzeug.rueckmeldung_geben",
     "inputSchema": {"type": "object", "properties": {
         "ziel": {**ZIEL_FELD, "description": "@konnektor.werkzeug.rueckmeldung_geben.ziel"},
         "art": {"type": "string", "enum": sorted(rm.ARTEN)},
         "text": {"type": "string", "description": "@konnektor.werkzeug.rueckmeldung_geben.text"},
         "name": {"type": "string", "description": "@konnektor.werkzeug.rueckmeldung_geben.name"},
         "quelle": {"type": "string", "description": "@konnektor.werkzeug.rueckmeldung_geben.quelle"}},
         "required": ["art", "text"]}},
]
NAME_FELD = {"type": "string", "description": "@konnektor.feld.name_feld"}
WERT_SCHEMA = {"type": "object", "properties": {
    "wert": {"type": "string"}, "quelle": {"type": "string"}, "geprueft": {"type": "string"}, "notiz": {"type": "string"},
    "gilt": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
             "description": "@konnektor.feld.wert_schema.gilt"}}, "required": ["wert"]}
WERKZEUGE += [
    {"name": "kategorien", "description": "@konnektor.werkzeug.kategorien",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "merkmale", "description": "@konnektor.werkzeug.merkmale",
     "inputSchema": {"type": "object", "properties": {
         "ziel": {"type": "string", "description": "@konnektor.werkzeug.merkmale.ziel"},
         "art": {"type": "string",
                 "description": "@konnektor.werkzeug.merkmale.art"}}},
     "annotations": {"readOnlyHint": True}},
]
AG_EIGENSCHAFTEN = {
    "titel": {"type": "string", "description": "@konnektor.feld.ag_eigenschaften.titel"},
    "bezug": {"type": "array", "items": {"type": "string"},
              "description": "@konnektor.feld.ag_eigenschaften.bezug"},
    "zustaendig": {"type": "string", "description": "@konnektor.feld.ag_eigenschaften.zustaendig"},
    "prioritaet": {"type": "string", "enum": list(rm.AG_PRIO)},
    "ab": {"type": "string", "description": "@konnektor.feld.ag_eigenschaften.ab"},
    "frist": {"type": "string", "description": "@konnektor.feld.ag_eigenschaften.frist"},
    "notiz": {"type": "string", "description": "@konnektor.feld.ag_eigenschaften.notiz"},
}
WERKZEUGE += [
    {"name": "aufgaben", "description": "@konnektor.werkzeug.aufgaben",
     "inputSchema": {"type": "object", "properties": {
         "bezug": {"type": "string", "description": "@konnektor.werkzeug.aufgaben.bezug"},
         "zustaendig": {"type": "string", "description": "@konnektor.werkzeug.aufgaben.zustaendig"},
         "status": {"type": "string", "enum": ["offen", "alle", *rm.AG_STATUS],
                    "description": "@konnektor.werkzeug.aufgaben.status"}}},
     "annotations": {"readOnlyHint": True}},
    {"name": "aufgabe_anlegen", "description": "@konnektor.werkzeug.aufgabe_anlegen",
     "inputSchema": {"type": "object", "properties": {**AG_EIGENSCHAFTEN, "name": NAME_FELD}, "required": ["titel"]}},
    {"name": "aufgabe_aendern", "description": "@konnektor.werkzeug.aufgabe_aendern",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string", "description": "@konnektor.werkzeug.aufgabe_aendern.id"},
         "status": {"type": "string", "enum": list(rm.AG_STATUS)},
         **AG_EIGENSCHAFTEN,
         "kommentar": {"type": "string", "description": "@konnektor.werkzeug.aufgabe_aendern.kommentar"},
         "name": NAME_FELD}, "required": ["id"]}},
]
WERKZEUGE += [
    {"name": "wuensche", "description": "@konnektor.werkzeug.wuensche",
     "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}},
    {"name": "wunsch_aendern", "description": "@konnektor.werkzeug.wunsch_aendern",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string", "description": "@konnektor.werkzeug.wunsch_aendern.id"},
         "punkte": {"type": "integer", "minimum": 0, "description": "@konnektor.werkzeug.wunsch_aendern.punkte"},
         "erlebt": {"type": "boolean"},
         "eingeplant": {"type": "boolean"},
         "bezug": {"type": "array", "items": {"type": "string"},
                   "description": "@konnektor.werkzeug.wunsch_aendern.bezug"},
         "kommentar": {"type": "string", "description": "@konnektor.werkzeug.wunsch_aendern.kommentar"},
         "name": NAME_FELD}, "required": ["id"]}},
]
# Ontologie der Reise im Gespräch (ADR-0001, O-3; docs/ontologie.md): die Software kennt nur die Form, die Reise ihre Arten
ART_DEFINIEREN = {"name": "art_definieren", "description": "@konnektor.werkzeug.art_definieren",
                  "inputSchema": {"type": "object", "properties": {
                      "art": {"type": "string", "description": "@konnektor.werkzeug.art_definieren.art"},
                      "bezeichnung": {"type": "string", "description": "@konnektor.werkzeug.art_definieren.bezeichnung"},
                      "grundform": {"type": "string", "enum": list(GRUNDFORMEN), "description": "@konnektor.werkzeug.art_definieren.grundform"},
                      "farbe": {"type": "string", "enum": list(FARBEN),
                                "description": "@konnektor.werkzeug.art_definieren.farbe"},
                      "beschreibung": {"type": "string", "description": "@konnektor.werkzeug.art_definieren.beschreibung"},
                      "summiert": {"type": "boolean", "description": "@konnektor.werkzeug.art_definieren.summiert"},
                      "symbol": {"type": "string", "enum": list(SYMBOLE_ARTEN), "description": "@konnektor.werkzeug.art_definieren.symbol"},
                      "buchbar": {"type": "boolean", "description": "@konnektor.werkzeug.art_definieren.buchbar"},
                      "lesetext": {"type": "array", "items": {"type": "object", "properties": {"rubrik": {"type": "string"}, "name": {"type": "string"}, "hilfe": {"type": "string"}}, "required": ["name"]},
                                   "description": "@konnektor.werkzeug.art_definieren.lesetext"},
                      "grund": {"type": "string", "description": "@konnektor.werkzeug.art_definieren.grund"},
                      "name": NAME_FELD}}}
KATEGORIE_DEFINIEREN = {"name": "kategorie_definieren", "description": "@konnektor.werkzeug.kategorie_definieren",
                        "inputSchema": {"type": "object", "properties": {
                            "kategorie": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.kategorie"},
                            "bezeichnung": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.bezeichnung"},
                            "einzahl": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.einzahl"},
                            "gruppe": {"type": "string", "enum": ["punkt", "wissen"], "description": "@konnektor.werkzeug.kategorie_definieren.gruppe"},
                            "farbe": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.farbe"},
                            "symbol": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.symbol"},
                            "nummeriert": {"type": "boolean", "description": "@konnektor.werkzeug.kategorie_definieren.nummeriert"},
                            "art": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.art"},
                            "art_bezeichnung": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.art_bezeichnung"},
                            "art_symbol": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.art_symbol"},
                            "art_hinweis": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.art_hinweis"},
                            "art_umriss": {"type": "boolean", "description": "@konnektor.werkzeug.kategorie_definieren.art_umriss"},
                            "grund": {"type": "string", "description": "@konnektor.werkzeug.kategorie_definieren.grund"},
                            "name": NAME_FELD}}}
MERKMAL_DEFINIEREN = {"name": "merkmal_definieren", "description": "@konnektor.werkzeug.merkmal_definieren",
                      "inputSchema": {"type": "object", "properties": {
                          "art": {"type": "string", "description": "@konnektor.werkzeug.merkmal_definieren.art"},
                          "fuer": {"type": "string", "enum": ["ding", "buchung"], "description": "@konnektor.werkzeug.merkmal_definieren.fuer"},
                          "merkmal": {"type": "string", "description": "@konnektor.werkzeug.merkmal_definieren.merkmal"},
                          "bezeichnung": {"type": "string", "description": "@konnektor.werkzeug.merkmal_definieren.bezeichnung"},
                          "typ": {"type": "string", "enum": sorted(TYPEN), "description": "@konnektor.werkzeug.merkmal_definieren.typ"},
                          "werte": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.werkzeug.merkmal_definieren.werte"},
                          "veraenderlich": {"type": "boolean", "description": "@konnektor.werkzeug.merkmal_definieren.veraenderlich"},
                          "nach_buchung": {"type": "boolean", "description": "@konnektor.werkzeug.merkmal_definieren.nach_buchung"},
                          "stufe": {"type": "string", "enum": list(STUFEN), "description": "@konnektor.werkzeug.merkmal_definieren.stufe"},
                          "einheit": {"type": "string", "description": "@konnektor.werkzeug.merkmal_definieren.einheit"},
                          "hilfe": {"type": "string", "description": "@konnektor.werkzeug.merkmal_definieren.hilfe"},
                          "frage": {"type": "string", "description": "@konnektor.werkzeug.merkmal_definieren.frage"},
                          "auch": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.werkzeug.merkmal_definieren.auch"},
                          "rolle": {"type": "string", "enum": ["kosten", "keine"], "description": "@konnektor.werkzeug.merkmal_definieren.rolle"},
                          "trotzdem": {"type": "boolean", "description": "@konnektor.werkzeug.merkmal_definieren.trotzdem"},
                          "grund": {"type": "string", "description": "@konnektor.werkzeug.merkmal_definieren.grund"},
                          "name": NAME_FELD},
                          "required": ["art"]}}
MERKMALE_FELD = {"type": "object", "description": "@konnektor.feld.merkmale_feld",
                 "additionalProperties": True}
QUELLE_FELD = {"type": "string", "description": "@konnektor.feld.quelle_feld"}
UHRZEIT_FELD = {"type": "string", "description": "@konnektor.feld.uhrzeit_feld"}
DING_ANLEGEN = {"name": "ding_anlegen", "description": "@konnektor.werkzeug.ding_anlegen",
                "inputSchema": {"type": "object", "properties": {
                    "was": {"type": "string", "enum": ["unterkunft", "aufenthalt", "strecke", "ort"]},
                    "titel": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.titel"},
                    "ort": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.ort"},
                    "zeit": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.zeit"},
                    "beginn": UHRZEIT_FELD, "ende": {**UHRZEIT_FELD, "description": "@konnektor.werkzeug.ding_anlegen.ende"},
                    "von": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.von"}, "nach": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.nach"},
                    "ab": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.ab"},
                    "an": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.an"},
                    "ausserhalb": {"type": "boolean", "description": "@konnektor.werkzeug.ding_anlegen.ausserhalb"},
                    "art": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.art"},
                    "hinweis": {"type": "string"}, "buchungslink": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.buchungslink"},
                    "frage": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.frage"},
                    "merkmale": MERKMALE_FELD, "quelle": QUELLE_FELD, "geprueft": {"type": "string", "description": "@konnektor.werkzeug.ding_anlegen.geprueft"},
                    "name": NAME_FELD},
                    "required": ["was", "titel", "quelle"]}}
DING_AENDERN = {"name": "ding_aendern", "description": "@konnektor.werkzeug.ding_aendern",
                "inputSchema": {"type": "object", "properties": {
                    "ziel": {"type": "string", "description": "@konnektor.werkzeug.ding_aendern.ziel"}, "zeit": {"type": "string"},
                    "neuer_name": {"type": "string", "description": "@konnektor.werkzeug.ding_aendern.neuer_name"}, "titel": {"type": "string", "description": "@konnektor.werkzeug.ding_aendern.titel"},
                    "beginn": UHRZEIT_FELD, "ende": {**UHRZEIT_FELD, "description": "@konnektor.werkzeug.ding_aendern.ende"},
                    "ort": {"type": "string"}, "von": {"type": "string"}, "nach": {"type": "string"}, "art": {"type": "string"},
                    "ab": {"type": "string", "description": "@konnektor.werkzeug.ding_aendern.ab"},
                    "an": {"type": "string", "description": "@konnektor.werkzeug.ding_aendern.an"}, "ausserhalb": {"type": "boolean", "description": "@konnektor.werkzeug.ding_aendern.ausserhalb"},
                    "hinweis": {"type": "string"}, "quelle": {"type": "string"}, "buchungslink": {"type": "string"}, "frage": {"type": "string"},
                    "grund": {"type": "string", "description": "@konnektor.werkzeug.ding_aendern.grund"}, "vorname": NAME_FELD},
                    "required": ["ziel"]}}
LAGE_EINTRAGEN = {"name": "lage_eintragen", "description": "@konnektor.werkzeug.lage_eintragen",
                  "inputSchema": {"type": "object", "properties": {
                      "ziel": {"type": "string", "description": "@konnektor.werkzeug.lage_eintragen.ziel"},
                      "adresse": {"type": "string", "description": "@konnektor.werkzeug.lage_eintragen.adresse"},
                      "koordinaten": {"type": "string", "description": "@konnektor.werkzeug.lage_eintragen.koordinaten"},
                      "quelle": QUELLE_FELD, "geprueft": {"type": "string", "description": "@konnektor.werkzeug.lage_eintragen.geprueft"},
                      "grund": {"type": "string"}, "vorname": NAME_FELD},
                      "required": ["ziel", "quelle"]}}
OPTION_FELDER = {"titel": {"type": "string", "description": "@konnektor.feld.option_felder.titel"},
                 "text": {"type": "string", "description": "@konnektor.feld.option_felder.text"},
                 "unterkuenfte": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.feld.option_felder.unterkuenfte"},
                 "strecken": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.feld.option_felder.strecken"},
                 "folge": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.feld.option_felder.folge"},
                 "plus": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.feld.option_felder.plus"},
                 "minus": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.feld.option_felder.minus"},
                 "erfordert": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.feld.option_felder.erfordert"},
                 "schliesst_aus": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.feld.option_felder.schliesst_aus"},
                 "ausloeser": {"type": "string", "description": "@konnektor.feld.option_felder.ausloeser"},
                 "siehe": {"type": "string", "description": "@konnektor.feld.option_felder.siehe"},
                 "merkmale": MERKMALE_FELD, "quelle": {"type": "string", "description": "@konnektor.feld.option_felder.quelle"},
                 "grund": {"type": "string", "description": "@konnektor.feld.option_felder.grund"}}
OPTION_ANLEGEN = {"name": "option_anlegen", "description": "@konnektor.werkzeug.option_anlegen",
                  "inputSchema": {"type": "object", "properties": {"wahlstelle": {"type": "string", "description": "@konnektor.werkzeug.option_anlegen.wahlstelle"},
                                                                   **OPTION_FELDER, "name": NAME_FELD},
                                  "required": ["wahlstelle", "titel", "quelle"]}}
WAHLSTELLE_ANLEGEN = {"name": "wahlstelle_anlegen", "description": "@konnektor.werkzeug.wahlstelle_anlegen",
                      "inputSchema": {"type": "object", "properties": {
                          "titel": {"type": "string"}, "wann": {"type": "string", "enum": ["planung", "unterwegs"], "description": "@konnektor.werkzeug.wahlstelle_anlegen.wann"},
                          "an": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.werkzeug.wahlstelle_anlegen.an"},
                          "art": {"type": "string", "description": "@konnektor.werkzeug.wahlstelle_anlegen.art"},
                          "frage": {"type": "string", "description": "@konnektor.werkzeug.wahlstelle_anlegen.frage"}, "text": {"type": "string"},
                          "optionen": {"type": "array", "items": {"type": "object", "properties": OPTION_FELDER, "required": ["titel", "quelle"]}},
                          "name": NAME_FELD},
                          "required": ["titel", "optionen"]}}
FRAGE_ANLEGEN = {"name": "frage_anlegen", "description": "@konnektor.werkzeug.frage_anlegen",
                 "inputSchema": {"type": "object", "properties": {
                     "text": {"type": "string", "description": "@konnektor.werkzeug.frage_anlegen.text"},
                     "bis": {"type": "string", "description": "@konnektor.werkzeug.frage_anlegen.bis"},
                     "bezug": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.werkzeug.frage_anlegen.bezug"},
                     "name": NAME_FELD}, "required": ["text"]}}
TAG_AENDERN = {"name": "tag_aendern", "description": "@konnektor.werkzeug.tag_aendern",
               "inputSchema": {"type": "object", "properties": {
                   "ziel": {"type": "string", "description": "@konnektor.werkzeug.tag_aendern.ziel"}, "titel": {"type": "string"}, "text": {"type": "string"},
                   "nacht": {"type": "string", "description": "@konnektor.werkzeug.tag_aendern.nacht"},
                   "strecken": {"type": "array", "items": {"type": "string"}}, "wahl": {"type": "array", "items": {"type": "string"}},
                   "aufenthalte": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.werkzeug.tag_aendern.aufenthalte"},
                   "grund": {"type": "string", "description": "@konnektor.werkzeug.tag_aendern.grund"}, "vorname": NAME_FELD},
                   "required": ["ziel"]}}
WISSEN_SCHREIBEN = {"name": "wissen_schreiben", "description": "@konnektor.werkzeug.wissen_schreiben",
                    "inputSchema": {"type": "object", "properties": {
                        "titel": {"type": "string", "description": "@konnektor.werkzeug.wissen_schreiben.titel"},
                        "abschnitt": {"type": "string", "description": "@konnektor.werkzeug.wissen_schreiben.abschnitt"},
                        "text": {"type": "string", "description": "@konnektor.werkzeug.wissen_schreiben.text"},
                        "quelle": QUELLE_FELD,
                        "gruppe": {"type": "string", "enum": ["wissen", "praxis", "quelle"], "description": "@konnektor.werkzeug.wissen_schreiben.gruppe"},
                        "datei": {"type": "string", "description": "@konnektor.werkzeug.wissen_schreiben.datei"},
                        "name": NAME_FELD}, "required": ["text", "quelle"]}}
FRAGE_SCHLIESSEN = {"name": "frage_schliessen", "description": "@konnektor.werkzeug.frage_schliessen",
                    "inputSchema": {"type": "object", "properties": {
                        "frage": {"type": "string", "description": "@konnektor.werkzeug.frage_schliessen.frage"},
                        "ergebnis": {"type": "string", "description": "@konnektor.werkzeug.frage_schliessen.ergebnis"},
                        "status": {"type": "string", "enum": ["geklaert", "entfaellt"], "description": "@konnektor.werkzeug.frage_schliessen.status"},
                        "vorname": NAME_FELD}, "required": ["frage", "ergebnis"]}}
RUECKMELDUNG_ERLEDIGEN = {"name": "rueckmeldung_erledigen", "description": "@konnektor.werkzeug.rueckmeldung_erledigen",
                          "inputSchema": {"type": "object", "properties": {
                              "id": {"type": "string", "description": "@konnektor.werkzeug.rueckmeldung_erledigen.id"},
                              "status": {"type": "string", "enum": ["uebernommen", "verworfen", "rueckfrage"]},
                              "kommentar": {"type": "string", "description": "@konnektor.werkzeug.rueckmeldung_erledigen.kommentar"},
                              "vorname": NAME_FELD}, "required": ["id", "status", "kommentar"]}}
REISE_STATUS_SETZEN = {"name": "reise_status_setzen", "description": "@konnektor.werkzeug.reise_status_setzen",
                       "inputSchema": {"type": "object", "properties": {
                           "status": {"type": "string", "enum": ["idee", "planung", "fest", "unterwegs", "danach", "archiv"]},
                           "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["status", "grund"]}}
EINSTELLUNG_SETZEN = {"name": "einstellung_setzen", "description": "@konnektor.werkzeug.einstellung_setzen",
                      "inputSchema": {"type": "object", "properties": {
                          "bausteine": {"type": "array", "items": {"type": "string"}},
                          "regeln": {"type": "object", "additionalProperties": True},
                          "sprache": {"type": "string", "enum": list(texte.SPRACHEN), "description": "@konnektor.werkzeug.einstellung_setzen.sprache"},
                          "grund": {"type": "string"}, "vorname": NAME_FELD}}}
BUCHUNG_FELDER_SCHEMA = {
    "status": {"type": "string", "enum": ["angefragt", "gebucht", "storniert"], "description": "@konnektor.feld.buchung_felder_schema.status"},
    "nummer": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.nummer"},
    "bei": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.bei"},
    "preis": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.preis"},
    "zahlung": {"type": "string", "enum": [*ZAHLUNG, *ZAHLUNG_ALIAS, ""], "description": "@konnektor.feld.buchung_felder_schema.zahlung"},
    "bezahlt": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.bezahlt"},
    "frist": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.frist"},
    "frist_was": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.frist_was"},
    "storno": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.storno"},
    "storno_bis": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.storno_bis"},
    "gebucht_am": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.gebucht_am"},
    "ab": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.ab"},
    "ab_was": {"type": "string", "description": "@konnektor.feld.buchung_felder_schema.ab_was"},
    "personen": {"type": "object", "additionalProperties": {"type": "string"},
                 "description": "@konnektor.feld.buchung_felder_schema.personen"},
    "preise": {"type": "object", "additionalProperties": {"type": "string"},
               "description": "@konnektor.feld.buchung_felder_schema.preise"},
    "merkmale": {"type": "object", "additionalProperties": {"type": ["string", "number"]},
                 "description": "@konnektor.feld.buchung_felder_schema.merkmale"},
    "notiz": {"type": "string"}}
BUCHUNG_ANLEGEN = {"name": "buchung_anlegen", "description": "@konnektor.werkzeug.buchung_anlegen",
                   "inputSchema": {"type": "object", "properties": {
                       "fuer": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.werkzeug.buchung_anlegen.fuer"},
                       **BUCHUNG_FELDER_SCHEMA, "quelle": QUELLE_FELD, "grund": {"type": "string"},
                       "beleg_text": {"type": "string", "description": "@konnektor.werkzeug.buchung_anlegen.beleg_text"},
                       "beleg_base64": {"type": "string", "description": "@konnektor.werkzeug.buchung_anlegen.beleg_base64"},
                       "beleg_dateiname": {"type": "string", "description": "@konnektor.werkzeug.buchung_anlegen.beleg_dateiname"},
                       "vorname": NAME_FELD},
                       "required": ["fuer", "quelle"]}}
BUCHUNG_AENDERN = {"name": "buchung_aendern", "description": "@konnektor.werkzeug.buchung_aendern",
                   "inputSchema": {"type": "object", "properties": {
                       "ziel": {"type": "string", "description": "@konnektor.werkzeug.buchung_aendern.ziel"},
                       "fuer": {"type": "array", "items": {"type": "string"}}, **BUCHUNG_FELDER_SCHEMA,
                       "quelle": {"type": "string", "description": "@konnektor.werkzeug.buchung_aendern.quelle"},
                       "grund": {"type": "string", "description": "@konnektor.werkzeug.buchung_aendern.grund"}, "vorname": NAME_FELD},
                       "required": ["ziel"]}}
WERT_SCHEMA_EINTRAG = {"type": "object", "properties": {
    "wert": {"type": "string"}, "gilt": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
             "description": "@konnektor.feld.wert_schema_eintrag.gilt"},
    "geprueft": {"type": "string"}, "quelle": {"type": "string"}, "notiz": {"type": "string"}}, "required": ["wert"]}
# ---------- Abgleich 29.10.2026 (Paket 3): die Tür für alle Grundformen (docs/abgleich-2026-10-29.md) ----------
TAG_ANLEGEN = {"name": "tag_anlegen", "description": "@konnektor.werkzeug.tag_anlegen",
               "inputSchema": {"type": "object", "properties": {
                   "titel": {"type": "string"}, "text": {"type": "string"}, "nach": {"type": "string", "description": "@konnektor.werkzeug.tag_anlegen.nach"},
                   "vor": {"type": "string", "description": "@konnektor.werkzeug.tag_anlegen.vor"}, "ohne_route": {"type": "boolean"},
                   "nacht": {"type": "string", "description": "@konnektor.werkzeug.tag_anlegen.nacht"}, "strecken": {"type": "array", "items": {"type": "string"}},
                   "wahl": {"type": "array", "items": {"type": "string"}}, "aufenthalte": {"type": "array", "items": {"type": "string"}},
                   "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["titel"]}}
TERMIN_SETZEN = {"name": "termin_setzen", "description": "@konnektor.werkzeug.termin_setzen",
                 "inputSchema": {"type": "object", "properties": {
                     "datum": {"type": "string", "description": "@konnektor.werkzeug.termin_setzen.datum"}, "titel": {"type": "string"}, "neuer_titel": {"type": "string"},
                     "ort": {"type": "string", "description": "@konnektor.werkzeug.termin_setzen.ort"}, "quelle": QUELLE_FELD, "entfernen": {"type": "boolean"},
                     "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["datum", "titel"]}}
WAHLSTELLE_AENDERN = {"name": "wahlstelle_aendern", "description": "@konnektor.werkzeug.wahlstelle_aendern",
                      "inputSchema": {"type": "object", "properties": {
                          "ziel": {"type": "string", "description": "@konnektor.werkzeug.wahlstelle_aendern.ziel"}, "titel": {"type": "string"}, "text": {"type": "string"},
                          "wann": {"type": "string", "enum": ["planung", "unterwegs"]}, "art": {"type": "string"},
                          "an": {"type": "array", "items": {"type": "string"}}, "frage": {"type": "string"},
                          "stufen": {"type": "object", "additionalProperties": True},
                          "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["ziel"]}}
OPTION_AENDERN = {"name": "option_aendern", "description": "@konnektor.werkzeug.option_aendern",
                  "inputSchema": {"type": "object", "properties": {
                      "ziel": {"type": "string", "description": "@konnektor.werkzeug.option_aendern.ziel"}, **{k: v for k, v in OPTION_FELDER.items() if k != "merkmale"},
                      "favorisiert": {"type": "boolean"}, "vorname": NAME_FELD}, "required": ["ziel"]}}
WISSEN_AENDERN = {"name": "wissen_aendern", "description": "@konnektor.werkzeug.wissen_aendern",
                  "inputSchema": {"type": "object", "properties": {
                      "ziel": {"type": "string", "description": "@konnektor.werkzeug.wissen_aendern.ziel"}, "text": {"type": "string"}, "quelle": QUELLE_FELD,
                      "neuer_titel": {"type": "string"}, "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["ziel", "grund"]}}
LESETEXT_SCHREIBEN = {"name": "lesetext_schreiben", "description": "@konnektor.werkzeug.lesetext_schreiben",
                      "inputSchema": {"type": "object", "properties": {
                          "ziel": {"type": "string", "description": "@konnektor.werkzeug.lesetext_schreiben.ziel"}, "text": {"type": "string", "description": "@konnektor.werkzeug.lesetext_schreiben.text"},
                          "quelle": QUELLE_FELD, "vorname": NAME_FELD}, "required": ["ziel", "text", "quelle"]}}
REISE_AENDERN = {"name": "reise_aendern", "description": "@konnektor.werkzeug.reise_aendern",
                 "inputSchema": {"type": "object", "properties": {
                     "titel": {"type": "string"}, "untertitel": {"type": "string"}, "kurz": {"type": "string"},
                     "von": {"type": "string"}, "bis": {"type": "string"}, "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["grund"]}}
START_ENDE_SETZEN = {"name": "start_ende_setzen", "description": "@konnektor.werkzeug.start_ende_setzen",
                     "inputSchema": {"type": "object", "properties": {
                         "start_datum": {"type": "string"}, "start_ort": {"type": "string", "description": "O-…"},
                         "ende_datum": {"type": "string"}, "ende_ort": {"type": "string", "description": "O-…"},
                         "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["grund"]}}
PLAN_FELDER_SCHEMA = {"kurz": {"type": "string", "description": "@konnektor.feld.plan_felder_schema.kurz"}, "titel": {"type": "string"}, "text": {"type": "string"},
                      "farbe": {"type": "string", "enum": ["a", "b", "c", "d"]},
                      "auswahl": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.feld.plan_felder_schema.auswahl"},
                      "plus": {"type": "array", "items": {"type": "string"}}, "minus": {"type": "array", "items": {"type": "string"}}}
PLAN_ANLEGEN = {"name": "plan_anlegen", "description": "@konnektor.werkzeug.plan_anlegen",
                "inputSchema": {"type": "object", "properties": {**PLAN_FELDER_SCHEMA, "quelle": QUELLE_FELD, "vorname": NAME_FELD},
                                "required": ["titel", "auswahl", "quelle"]}}
PLAN_AENDERN = {"name": "plan_aendern", "description": "@konnektor.werkzeug.plan_aendern",
                "inputSchema": {"type": "object", "properties": {"ziel": {"type": "string", "description": "@konnektor.werkzeug.plan_aendern.ziel"}, **PLAN_FELDER_SCHEMA,
                                                                 "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["ziel"]}}
MERKMAL_ZUSAMMENFUEHREN = {"name": "merkmal_zusammenfuehren", "description": "@konnektor.werkzeug.merkmal_zusammenfuehren",
                           "inputSchema": {"type": "object", "properties": {
                               "art": {"type": "string"}, "von": {"type": "string"}, "nach": {"type": "string"}, "grund": {"type": "string"},
                               "vorname": NAME_FELD}, "required": ["art", "von", "nach", "grund"]}}
ARTEN_UEBERNEHMEN = {"name": "arten_uebernehmen", "description": "@konnektor.werkzeug.arten_uebernehmen",
                     "inputSchema": {"type": "object", "properties": {
                         "von_reise": {"type": "string", "description": "@konnektor.werkzeug.arten_uebernehmen.von_reise"},
                         "arten": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.werkzeug.arten_uebernehmen.arten"},
                         "grund": {"type": "string"}, "vorname": NAME_FELD}, "required": ["von_reise"]}}
WUNSCH_VORSCHLAGEN = {"name": "wunsch_vorschlagen", "description": "@konnektor.werkzeug.wunsch_vorschlagen",
                      "inputSchema": {"type": "object", "properties": {
                          "wunsch": {"type": "string", "description": "@konnektor.werkzeug.wunsch_vorschlagen.wunsch"},
                          "bezug": {"type": "array", "items": {"type": "string"}, "description": "@konnektor.werkzeug.wunsch_vorschlagen.bezug"},
                          "notiz": {"type": "string", "description": "@konnektor.werkzeug.wunsch_vorschlagen.notiz"},
                          "option": {"type": "string", "description": "@konnektor.werkzeug.wunsch_vorschlagen.option"},
                          "vorname": NAME_FELD}, "required": ["wunsch", "notiz"]}}
BELEG_ANLEGEN = {"name": "beleg_anlegen", "description": "@konnektor.werkzeug.beleg_anlegen",
                 "inputSchema": {"type": "object", "properties": {
                     "buchung": {"type": "string", "description": "@konnektor.werkzeug.beleg_anlegen.buchung"},
                     "dateiname": {"type": "string", "description": "@konnektor.werkzeug.beleg_anlegen.dateiname"},
                     "text": {"type": "string", "description": "@konnektor.werkzeug.beleg_anlegen.text"},
                     "daten_base64": {"type": "string", "description": "@konnektor.werkzeug.beleg_anlegen.daten_base64"},
                     "vorname": NAME_FELD}, "required": ["buchung"]}}
WERT_EINTRAGEN = {"name": "wert_eintragen", "description": "@konnektor.werkzeug.wert_eintragen",
                  "inputSchema": {"type": "object", "properties": {
                      "ziel": {"type": "string", "description": "@konnektor.werkzeug.wert_eintragen.ziel"},
                      "merkmal": {"type": "string", "description": "@konnektor.werkzeug.wert_eintragen.merkmal"},
                      "wert": {"type": "string", "description": "@konnektor.werkzeug.wert_eintragen.wert"},
                      "quelle": {"type": "string", "description": "@konnektor.werkzeug.wert_eintragen.quelle"},
                      "geprueft": {"type": "string", "description": "@konnektor.werkzeug.wert_eintragen.geprueft"},
                      "gilt": WERT_SCHEMA_EINTRAG["properties"]["gilt"],
                      "notiz": {"type": "string", "description": "@konnektor.werkzeug.wert_eintragen.notiz"},
                      "werte": {"type": "array", "items": WERT_SCHEMA_EINTRAG,
                                "description": "@konnektor.werkzeug.wert_eintragen.werte"},
                      "name": NAME_FELD},
                      "required": ["ziel", "merkmal"]}}


ENTSCHEIDEN = {"name": "entscheiden", "description": "@konnektor.werkzeug.entscheiden",
               "inputSchema": {"type": "object", "properties": {
                   "option": {"type": "string", "description": "@konnektor.werkzeug.entscheiden.option"},
                   "status": {"type": "string", "enum": list(ENTSCHEIDUNGEN),
                              "description": "@konnektor.werkzeug.entscheiden.status"},
                   "grund": {"type": "string", "description": "@konnektor.werkzeug.entscheiden.grund"},
                   "ersetzt_durch": {"type": "string", "description": "@konnektor.werkzeug.entscheiden.ersetzt_durch"},
                   "quelle": {"type": "string", "description": "@konnektor.werkzeug.entscheiden.quelle"}},
                   "required": ["option", "status", "grund"]}}
FRAGE_BEANTWORTEN = {"name": "frage_beantworten", "description": "@konnektor.werkzeug.frage_beantworten",
                     "inputSchema": {"type": "object", "properties": {
                         "frage": {"type": "string", "description": "@konnektor.werkzeug.frage_beantworten.frage"},
                         "antwort": {"type": "string", "description": "@konnektor.werkzeug.frage_beantworten.antwort"},
                         "quelle": {"type": "string", "description": "@konnektor.werkzeug.frage_beantworten.quelle"},
                         "name": NAME_FELD}, "required": ["frage", "antwort"]}}
PERSON_EINLADEN = {"name": "person_einladen", "description": "@konnektor.werkzeug.person_einladen",
                   "inputSchema": {"type": "object", "properties": {
                       "vorname": {"type": "string", "description": "@konnektor.werkzeug.person_einladen.vorname"},
                       "rolle": {"type": "string", "enum": list(ROLLEN),
                                 "description": "@konnektor.werkzeug.person_einladen.rolle"},
                       "reist": {"type": "boolean", "description": "@konnektor.werkzeug.person_einladen.reist"},
                       "notiz": {"type": "string", "description": "@konnektor.werkzeug.person_einladen.notiz"},
                       "schluessel": {"type": "string", "description": "@konnektor.werkzeug.person_einladen.schluessel"},
                       "name": NAME_FELD}, "required": ["vorname"]}}


PERSON_ENTFERNEN = {"name": "person_entfernen", "description": "@konnektor.werkzeug.person_entfernen",
                    "inputSchema": {"type": "object", "properties": {
                        "person": {"type": "string", "description": "@konnektor.werkzeug.person_entfernen.person"},
                        "grund": {"type": "string", "description": "@konnektor.werkzeug.person_entfernen.grund"},
                        "name": NAME_FELD}, "required": ["person"]}}


REISE_ANLEGEN = {"name": "reise_anlegen", "description": "@konnektor.werkzeug.reise_anlegen",
                 "inputSchema": {"type": "object", "properties": {
                     "titel": {"type": "string", "description": "@konnektor.werkzeug.reise_anlegen.titel"},
                     "von": {"type": "string", "description": "@konnektor.werkzeug.reise_anlegen.von"},
                     "bis": {"type": "string", "description": "@konnektor.werkzeug.reise_anlegen.bis"},
                     "ziel": {"type": "string", "description": "@konnektor.werkzeug.reise_anlegen.ziel"},
                     "personen": {"type": "array", "description": "@konnektor.werkzeug.reise_anlegen.personen", "items": {"type": "object", "properties": {
                                      "vorname": {"type": "string"},
                                      "rolle": {"type": "string", "enum": list(ROLLEN),
                                                "description": "@konnektor.werkzeug.reise_anlegen.personen.items.rolle"},
                                      "reist": {"type": "boolean", "description": "@konnektor.werkzeug.reise_anlegen.personen.items.reist"},
                                      "notiz": {"type": "string", "description": "@konnektor.werkzeug.reise_anlegen.personen.items.notiz"}},
                                      "required": ["vorname"]}},
                     "notiz": {"type": "string", "description": "@konnektor.werkzeug.reise_anlegen.notiz"},
                     "pfad": {"type": "string", "description": "@konnektor.werkzeug.reise_anlegen.pfad"},
                     "sprache": {"type": "string", "enum": list(texte.SPRACHEN), "description": "@konnektor.werkzeug.reise_anlegen.sprache"}},
                     "required": ["titel", "von", "bis"]}}


def _mit_mail(w):
    """reise_anlegen im Konnektor „Frieda“: Personen mit E-Mail-Adresse, die eine Einladung bekommen."""
    import copy
    w = copy.deepcopy(w)
    w["description"] = "@konnektor.werkzeug.reise_anlegen.mit_mail"   # eigener Text statt Ersetzen im Wortlaut (ADR-0006)
    w["inputSchema"]["properties"]["personen"]["items"]["properties"]["email"] = EMAIL_FELD
    return w


REISE_ANLEGEN_MIT_MAIL = _mit_mail(REISE_ANLEGEN)


def anleitung(zugang, d):
    """Kurze Verfassung für die KI: Aufgabe, Grenzen, Rollen, Status. Was die Maschine prüft, steht nicht darin. Die Sätze stehen im
    Katalog in der Sprache des Zugangs (zugang["sprache"], ADR-0006); hier stehen nur die Bedingungen."""
    sp = zugang.get("sprache") or texte.VORGABE_REISE
    rs = (d or {}).get("reise", {})
    wer = wer_spricht(zugang, d) or {"rolle": "gast", "name": None}
    organisator = organisator_namen(d)
    namen = tk("konnektor.und").join(organisator) or tk("konnektor.ausgabe.anleitung.1")
    status = (rs.get("status") or {}).get("wert")
    bausteine = rs.get("bausteine")
    kennungen = anl(sp, "kennungen_regel")
    z = [anl(sp, "aufgabe_mehrere" if len(organisator) > 1 else "aufgabe_einer", titel=rs.get("titel", zugang["reise"]),
             untertitel=rs.get("untertitel", ""), namen=namen, status_teil=anl(sp, "status_teil", status=status) if status else ""),
         anl(sp, "grenzen", kein_schreibweg="" if schreibdienst() else anl(sp, "kein_schreibweg")),
         anl(sp, "ids", kennungen=kennungen),
         anl(sp, "rollen")]
    name = anl(sp, "du_mit_name", name=wer["name"]) if wer["name"] else anl(sp, "du_ohne_name")
    regeln = rs.get("regeln") or {}
    einladen_ab = regeln.get("einladen") or VORGABEN["einladen"]
    kann_einladen = darf(wer["rolle"], einladen_ab)
    direkt = schreibdienst()
    if wer["rolle"] == "organisator":
        z.append(anl(sp, "org", name=name,
                     pruefung=anl(sp, "org.pruefung_direkt" if direkt else "org.pruefung_ohne"),
                     einladen=anl(sp, "org.einladen_konto" if "konto_id" in zugang else "org.einladen_link"),
                     direkt=anl(sp, "org.direkt") if direkt else ""))
    elif wer["rolle"] == "mitwirkend":
        z.append(anl(sp, "mit", name=name, namen=namen, direkt=anl(sp, "mit.direkt") if direkt else "",
                     einladen=anl(sp, "mit.einladen") if kann_einladen else "",
                     vorname="" if wer["name"] else anl(sp, "mit.vorname")))
    else:
        z.append(anl(sp, "gast", name=name))
    z.append(anl(sp, "loeschwunsch"))
    if status in STATUS_SAETZE:
        z.append(anl(sp, "status_label", satz=anl(sp, "status." + status)))
    aus = [b for b in ("varianten", "fragen", "aufgaben", "rueckmeldungen", "wuensche") if bausteine is not None and b not in bausteine]
    if wer["name"] is None and wer["rolle"] != "gast":
        z.append(anl(sp, "link_ohne_person"))
    if aus:
        z.append(anl(sp, "ausgeschaltet", liste=", ".join(aus)))
    if bausteine is None or "varianten" in bausteine:
        z.append(anl(sp, "alternativen"))
    if bausteine is None or "waechter" in bausteine:
        z.append(anl(sp, "waechter"))
    if "wuensche" in (bausteine or []):
        z.append(anl(sp, "wuensche"))
    z.append(anl(sp, "antwortsprache"))
    return " ".join(z)


def werkzeug(zugang, name, args):
    """-> (text, ist_fehler)"""
    reise = zugang["reise"]
    args = args if isinstance(args, dict) else {}
    wer = wer_spricht(zugang, daten(reise))
    if wer is None:
        return tk("konnektor.werkzeug.1"), True
    organisator = darf(wer["rolle"], "organisator")
    d = daten(reise)
    # Regeln prüft die Maschine, bei jedem Aufruf (nicht nur beim Anzeigen der Werkzeuge): Rolle, Baustein, Status
    status, bausteine = zustand_von(d)
    if name in LESE_BAUSTEIN and bausteine is not None and LESE_BAUSTEIN[name] not in bausteine:
        return tk("konnektor.werkzeug.2", w1=LESE_BAUSTEIN[name]), True
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
            return tk("konnektor.werkzeug.8"), True
        kommentar = str(args.get("kommentar") or "").strip()
        if not kommentar:
            return tk("konnektor.werkzeug.9"), True
        name_ = wer["name"] or args.get("vorname")
        if not isinstance(name_, str) or not name_.strip():
            return tk("konnektor.frage_beantworten.4"), True
        a, fehler = dienst_anfrage("PATCH", f"{reise}/rueckmeldungen/{rid}", {"status": str(args.get("status") or ""), "kommentar": kommentar,
                                                                               "name": name_.strip()})
        if fehler:
            return tk("konnektor.ausgabe.werkzeug.2", fehler=fehler), True
        return (tk("konnektor.werkzeug.3", rid=rid, w2=a['status'], kommentar=kommentar)), False
    if name == "beleg_anlegen":
        bid = str(args.get("buchung") or "").strip().upper()
        if not re.fullmatch(r"B-\d+", bid):
            return tk("konnektor.werkzeug.10"), True
        name_ = wer["name"] or args.get("vorname")
        if not isinstance(name_, str) or not name_.strip():
            return tk("konnektor.frage_beantworten.4"), True
        im_repo = False
        if bid not in ((d.get("route") or {}).get("buchungen") or {}):   # noch nicht veröffentlicht? Dann zählt das Repo (Issue #135)
            im_repo, fehler = buchung_im_repo(reise, bid)
            if fehler:
                return tk("konnektor.ausgabe.beleg_ablegen.1", fehler=fehler), True
            if not im_repo:
                return tk("konnektor.werkzeug.13", bid=bid), True
        return beleg_ablegen(reise, bid, name_.strip(), args, im_repo)
    if name == "rueckmeldung_geben":
        e = {k: args.get(k, "") for k in rm.INHALT}
        if wer["name"]:
            e["name"] = wer["name"]
        if not all(isinstance(v, str) for v in e.values()):
            return tk("konnektor.entscheiden.3"), True
        if not e["name"].strip():
            return tk("konnektor.frage_beantworten.4"), True
        e["quelle"] = e["quelle"] or tkd("konnektor.werkzeug.4")
        antwort, fehler = rueckmeldung_senden(reise, e)
        if fehler:
            return tk("konnektor.ausgabe.frage_beantworten.4", fehler=fehler), True
        return (tk("konnektor.werkzeug.5", w1=antwort['id'])), False
    d = daten(reise)
    if d is None:
        return tk("konnektor.werkzeug.6"), True
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
        return (rm.aufgaben_text(liste, h.titel(), h.v["fristen"]) if liste else tk("konnektor.ausgabe.werkzeug.3")), False
    if name in ("aufgabe_anlegen", "aufgabe_aendern"):
        roh = {k: args[k] for k in (*rm.AG_FELDER, "kommentar") if k in args}
        roh["name"] = wer["name"] or args.get("name", "")
        if not isinstance(roh["name"], str) or not roh["name"].strip():
            return tk("konnektor.frage_beantworten.4"), True
        unbekannt = [b for b in (roh.get("bezug") or []) if isinstance(b, str) and b not in h.eintraege]
        if unbekannt:
            return tk("konnektor.werkzeug.11", w1=', '.join(unbekannt)), True
        if name == "aufgabe_anlegen":
            a, fehler = dienst_anfrage("POST", f"{reise}/aufgaben", roh)
        else:
            agid = str(args.get("id", "")).strip()
            if not rm.AG_MUSTER.match(agid):
                return tk("konnektor.ausgabe.id_muss_ag"), True
            a, fehler = dienst_anfrage("PATCH", f"{reise}/aufgaben/{agid}", roh)
        if fehler:
            return tk("konnektor.ausgabe.frage_beantworten.4", fehler=fehler), True
        zusatz = (tk("konnektor.werkzeug.7")
                  if name == "aufgabe_aendern" and str(args.get("status", "")).strip().lower() == "entfaellt" else "")
        return tk("konnektor.ausgabe.werkzeug.5") + aufgabe_text(a, h.titel()) + zusatz, False
    if name == "wuensche":
        o = rm.ordner(reise)
        return (brett_text(rm.brett(o, rm.zustand(reise)), h.titel()) if o else tk("konnektor.werkzeug.12")), False
    if name == "wunsch_aendern":
        rid = str(args.get("id", "")).strip()
        if not rm.RID_MUSTER.match(rid):
            return tk("konnektor.ausgabe.id_muss_r"), True
        roh = {k: args[k] for k in ("punkte", "erlebt", "eingeplant", "bezug", "kommentar") if k in args}
        if "eingeplant" in roh and not (wer["name"] and organisator):
            return (tk("konnektor.werkzeug.14") if organisator else tk("konnektor.werkzeug.15")), True
        roh["name"] = wer["name"] or args.get("name", "")
        if not isinstance(roh["name"], str) or not roh["name"].strip():
            return tk("konnektor.frage_beantworten.4"), True
        unbekannt = [b for b in (roh.get("bezug") or []) if isinstance(b, str) and b not in h.eintraege]
        if unbekannt:
            return tk("konnektor.werkzeug.11", w1=', '.join(unbekannt)), True
        w, fehler = dienst_anfrage("PATCH", f"{reise}/rueckmeldungen/{rid}", roh)
        if fehler:
            return tk("konnektor.ausgabe.frage_beantworten.4", fehler=fehler), True
        teile = [tk("konnektor.ausgabe.werkzeug.6", w1=w['punkte'])] + (["eingeplant"] if w.get("eingeplant") else []) + (["erlebt"] if w.get("erlebt") else [])
        return tk("konnektor.ausgabe.werkzeug.7", rid=rid) + ", ".join(teile) + ".", False
    if name == "ueberblick":
        return (h.ueberblick() + "\n" + stand_text(reise)
                + (wuensche_kurz(reise) if "wuensche" in (zustand_von(d)[1] or []) else "")), False
    if name == "zeige":
        t, fehler = h.zeige(str(args.get("id", "")).strip())
        return (fehler, True) if fehler else (t, False)
    if name == "suche":
        begriff = str(args.get("begriff", "")).strip()
        return (h.suche(begriff), False) if begriff else (tk("konnektor.ausgabe.werkzeug.4"), True)
    if name == "offene_fragen":
        return h.fragen(bool(args.get("alle"))), False
    if name == "varianten":
        return h.varianten(), False
    if name == "kategorien":
        return h.kategorien(), False
    if name == "merkmale":
        t, fehler = h.merkmale(str(args.get("ziel") or "").strip(), str(args.get("art") or args.get("bereich") or "").strip())
        return (fehler, True) if fehler else (t, False)
    return tk("konnektor.ausgabe.werkzeug.1", name=name), True


def antwort_auf(zugang, nachricht):
    """Eine JSON-RPC-Nachricht -> Antwort-Objekt oder None (Benachrichtigung)."""
    if not isinstance(nachricht, dict) or nachricht.get("jsonrpc") != "2.0" or not isinstance(nachricht.get("method"), str):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": tk("konnektor.antwort_auf.1")}}
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
                   "instructions": schnittstelle.namen_im_text(anleitung(zugang, daten(zugang["reise"])))})
    if methode == "ping":
        return ok({})
    if methode == "tools/list":
        return ok({"tools": schnittstelle.aussen(lokalisiert(werkzeuge_fuer(zugang), zugang.get("sprache") or texte.VORGABE_REISE))})
    if methode == "tools/call":
        name_i, args_i = aufruf_intern(werkzeuge_fuer(zugang), p.get("name"), p.get("arguments"))
        t, fehler = werkzeug(zugang, name_i, args_i)
        return ok({"content": [{"type": "text", "text": antworttext(t)}], "isError": fehler})
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
                 BUCHUNG_ANLEGEN, BUCHUNG_AENDERN, TAG_ANLEGEN, TERMIN_SETZEN, WAHLSTELLE_AENDERN, OPTION_AENDERN, WISSEN_AENDERN,
                 LESETEXT_SCHREIBEN, REISE_AENDERN, START_ENDE_SETZEN, PLAN_ANLEGEN, PLAN_AENDERN, MERKMAL_ZUSAMMENFUEHREN, ARTEN_UEBERNEHMEN,
                 WUNSCH_VORSCHLAGEN] if schreibdienst() else []
    for w in WERKZEUGE + [ENTSCHEIDEN, FRAGE_BEANTWORTEN, PERSON_EINLADEN, PERSON_ENTFERNEN, RUECKMELDUNG_ERLEDIGEN, BELEG_ANLEGEN] + ontologie:
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
        if code not in (204, 304):
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _marke(self, pfad):
        ordner, (name, art) = (MARKE, MARKE_DATEIEN[pfad]) if pfad in MARKE_DATEIEN else (SCHRIFT, SCHRIFT_DATEIEN[pfad])
        try:
            body = (ordner / name).read_bytes()
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
                return self._senden(413, {"fehler": tk("konnektor._anmeldung.1")})
            body = self.rfile.read(laenge)
        ip = self.client_address[0]
        if ip in ("127.0.0.1", "::1") and self.headers.get("X-Real-IP"):
            ip = self.headers["X-Real-IP"].strip()      # hinter nginx: echte Adresse für die Begrenzung
        methode = "GET" if self.command == "HEAD" else self.command     # HEAD: Kopf wie bei GET, ohne Inhalt
        if oauth.ist_unsere(self.path):
            code, kopf, inhalt = oauth.bearbeiten(methode, self.path, self.headers, body, ip)
        else:
            code, kopf, inhalt = anmeldung.bearbeiten(methode, self.path, self.headers, body, ip, reise_kurz)
        self.send_response(code)
        grund = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                 "Referrer-Policy": "same-origin",   # nicht no-referrer: dann schicken Browser „Origin: null“
                 "Content-Security-Policy": "default-src 'none'; img-src 'self'; font-src 'self'; style-src 'unsafe-inline'; form-action 'self'; "
                                            "frame-ancestors 'none'; base-uri 'none'"}
        eigene = {k for k, _ in kopf}
        for k, v in [*((k, v) for k, v in grund.items() if k not in eigene), *kopf]:
            self.send_header(k, v)
        if code not in (204, 304):
            self.send_header("Content-Length", str(len(inhalt)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(inhalt)

    def do_GET(self):
        # Readiness für BetterStack ohne geheimen Link: Zugänge lesbar und jede verlinkte Reise veröffentlicht
        if self.path.split("?", 1)[0] == "/gesund":
            return self._senden(*gesund())
        if self.path.split("?", 1)[0] in MARKE_DATEIEN or self.path.split("?", 1)[0] in SCHRIFT_DATEIEN:
            return self._marke(self.path.split("?", 1)[0])
        if anmeldung.ist_unsere(self.path) or oauth.ist_unsere(self.path):
            return self._anmeldung()
        if self.path.split("?", 1)[0] == "/mcp":
            if not oauth.basis() or not konten.oauth_konto(oauth.bearer(self.headers) or ""):
                return self._senden(401, {"fehler": tk("konnektor.do_get.1")}, {"WWW-Authenticate": oauth.www_authenticate()})
            return self._senden(405, {"fehler": "nur POST"}, {"Allow": "POST"})
        # Kein SSE-Kanal: der Dienst schickt nie von sich aus etwas (Streamable HTTP erlaubt 405).
        if self._zugang() is None:
            return self._senden(404, {"fehler": "unbekannt"})
        self._senden(405, {"fehler": "nur POST"}, {"Allow": "POST"})

    do_DELETE = do_GET
    do_HEAD = do_GET    # Kalender-Apps und Prüfdienste fragen mit HEAD, ob es die Adresse gibt; 501 lässt das Abo scheitern

    def _erlaubt(self):
        p = self.path.split("?", 1)[0]
        return "GET, HEAD, OPTIONS" if p.startswith("/kalender/") or p in MARKE_DATEIEN or p in SCHRIFT_DATEIEN \
            or p == "/gesund" else "GET, HEAD, POST, OPTIONS"

    def do_OPTIONS(self):
        """Welche Methoden gehen (RFC 9110). Ohne Access-Control-Kopf: Browser anderer Seiten dürfen weiterhin nichts."""
        self._senden(204, extra={"Allow": self._erlaubt()})

    def _nicht_erlaubt(self):
        """WebDAV und CalDAV (PROPFIND, REPORT, …) und alles Unbekannte: 405 mit Allow statt 501. Kalender-Apps prüfen
        so, ob eine Adresse CalDAV spricht, und nehmen bei 405 das einfache Abo (GET)."""
        self._senden(405, {"fehler": "unbekannt"}, {"Allow": self._erlaubt()})

    def __getattr__(self, name):
        # BaseHTTPRequestHandler sucht do_<METHODE>; jede Methode ohne eigenen Zweig bekommt 405
        if name.startswith("do_"):
            return self._nicht_erlaubt
        raise AttributeError(name)

    def do_POST(self):
        if anmeldung.ist_unsere(self.path) or oauth.ist_unsere(self.path):
            return self._anmeldung()
        if self.path.split("?", 1)[0] == "/mcp":
            # Konnektor „Frieda“ (Paket J3): Bearer-Token aus OAuth; ohne gültiges 401 mit Zeiger auf die Metadaten
            t = oauth.bearer(self.headers)
            k = konten.oauth_konto(t) if t and oauth.basis() else None
            if not k:
                return self._senden(401, {"fehler": tk("konnektor.do_get.1")},
                                    {"WWW-Authenticate": oauth.www_authenticate(fehler=bool(t))})
            zugang = {"konto_id": k["id"], "sprache": k["sprache"]}
        else:
            zugang = self._zugang()
        if zugang is None:
            return self._senden(404, {"fehler": "unbekannt"})
        zugang = {**zugang, "sprache": zugang.get("sprache") or sprache_des_zugangs(zugang)}
        texte.aufruf_sprache(zugang["sprache"])
        try:
            laenge = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            laenge = 0
        if laenge <= 0 or laenge > MAX_BODY:
            return self._senden(413, {"fehler": tk("konnektor.do_post.1")})
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
        wer = tk("konnektor.ausgabe.zugang_anlegen.1", wen=wen)
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
        wer = z.get("person") or tk("konnektor.ausgabe.zugaenge_zeigen.1", w1=z.get('rolle'))
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
