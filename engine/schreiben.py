"""Schreibweg: Der Konnektor schreibt direkt in die Ontologie der Reise (ADR-0001, Paket O-3).

Frieda enthält keine KI. Was im AI-Client (Claude-App) erarbeitet wird, kommt über den Konnektor hierher und wird
sofort geschrieben: in das Reisen-Repo (plan/arten.yaml: Arten und Merkmale; plan/routen.yaml: Werte, Dinge, Wahlstellen, Optionen, Entscheidungen, Plan;
offene-fragen.md: Fragen; inhalt/*.md: Wissen; reise.yaml: Personen), geprüft mit einem
Probebau, gesichert als Commit mit Person und Werkzeug, nach main gebracht und veröffentlicht. Dieses Modul ist die
einzige Stelle, an der ein Dienst Reisedateien ändert.

Zwei Teile:
  Dienst   `schreiben.py dienst` auf 127.0.0.1:<FR_SB_PORT> (8773), nur für den Konnektor (Header X-Frieda-Dienst, das
           gemeinsame Dienst-Geheimnis). POST /<reise>/<werkzeug> mit {"person", "name", "rolle", "args"}; die Antwort
           nennt bei einem neuen Ding seine ID. GET /<reise>/buchung/<B-id> sagt, ob es die Buchung auf origin/main schon
           gibt (Beleg vor dem Veröffentlichen, Issue #135). Ein Schreibvorgang je Reise zur Zeit (Sperre).
  Arbeit   `schreiben.py anwenden` liest die Anfrage als JSON von stdin, prüft Rolle und Status, ändert die Dateien,
           baut zur Probe, sichert, stößt das Veröffentlichen an und antwortet auf stdout als JSON.

Zwei Wege, gewählt je Reise (FR_SPEICHERREISEN, engine/instanz.py; Stufe 2, #347, ADR-0009):
  Speicherweg  Reise in der Liste: Die Arbeitskopie ist ein Export des Reisespeichers (engine/reisespeicher.py) in einen
           temporären Ordner; `anwenden` läuft mit dem Code dieses Dienstes und trägt das Ergebnis als genau einen Vorgang
           ein (erwartet = Stand des Exports). Nach einem Abbruch wird lokal im Speicher nachgesehen. Kein git.
  Git-Weg  jede andere Reise, bis Stufe 5 (engine/schreiben_git.py): Arbeitskopie <Wurzel>-schreiben-<reise>
           (FR_SCHREIBKOPIE) auf origin/main, `anwenden` mit dem Code dieser Arbeitskopie, Commit und Push nach main.
Veröffentlicht wird wie nach jedem Zusammenführen: betrieb/veroeffentlichen.sh (im Hintergrund; bis Stufe 3, #348, baut es nur
aus Git, eine Speicher-Reise wartet so lange).

Regeln vor dem Schreiben (Prüfstelle ADR-0001): Rolle und Status (reise.erlaubt mit reise.yaml der Arbeitskopie, nicht
nur mit dem, was der Konnektor sagt), Form der Arten und Merkmale (docs/ontologie.md), Probebau (routen.arten_pruefen und
alles andere, was der Generator prüft). Lehnt der Schreibweg ab, bleibt der Stand der Reise unverändert und der AI-Client
bekommt den Grund in einfachen Worten.

Aufruf von Hand: `schreiben.py vorbereiten` (Arbeitskopie anlegen), `schreiben.py normalisieren <reise>` (Routendatei in die Form
bringen, die der Schreibweg schreibt; in einer Sitzung im Reisen-Repo).
Für Tests überschreibbar: SB_VEROEFFENTLICHEN (Skript statt betrieb/veroeffentlichen.sh), FR_SCHREIBKOPIE, FR_SB_PORT.
"""
import copy
import datetime
import fcntl
import hmac
import json
import os
import re
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instanz  # noqa: E402
import kartendienst  # noqa: E402
import konten  # noqa: E402
import stand as reisestand  # noqa: E402
import texte  # noqa: E402

REISE_MUSTER = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
SCHLUESSEL_MUSTER = re.compile(r"^[a-z][a-z0-9_]*$")
MAX_BODY = 64 * 1024
MAX_TEXT = 500          # Namen, Hilfe, Fragen, Beschreibungen
MAX_WERTE = 20
# Zeitgrenzen in Sekunden: ZEIT_VORAB (nur kartenpunkte_holen, vor der Sperre) + ZEIT_GESAMT + ZEIT_PRUEFUNG bleibt unter der
# Wartezeit des Konnektors (schreib_anfrage, 120 s) und unter proxy_read_timeout von /mcp (300 s, betrieb/vorlagen/nginx-konnektor*.inc),
# sonst erreicht die Meldung die App nie; ZEIT_GESAMT + ZEIT_PRUEFUNG allein bleibt unter 60 s
ZEIT_GESAMT = 25        # Sperre, Vorbereiten und Anwenden zusammen
ZEIT_SPERRE = 3         # Wartezeit auf die Sperre der Reise (Teil von ZEIT_GESAMT)
ZEIT_PRUEFUNG = 3       # nach einem Abbruch: ist der Vorgang trotzdem eingetragen (Speicher lokal, Git auf origin/main)?
LOG_LAENGE = 200        # Zeichen eines Ablehnungsgrunds im Protokoll
AKTIONEN = {"art_definieren": "ontologie", "merkmal_definieren": "ontologie", "kategorie_definieren": "ontologie", "wert_eintragen": "wert",
            "ding_anlegen": "ding", "ding_aendern": "ding", "option_anlegen": "alternative", "wahlstelle_anlegen": "alternative",
            "frage_anlegen": "frage", "entscheiden": "entscheiden", "tag_aendern": "plan", "wissen_schreiben": "wissen",
            "frage_schliessen": "frage_schliessen", "person_schreiben": "einladen", "lage_eintragen": "ding",
            "reise_status_setzen": "einstellung", "einstellung_setzen": "einstellung",
            "buchung_anlegen": "buchung", "buchung_aendern": "buchung",
            "tag_anlegen": "plan", "termin_setzen": "plan", "wahlstelle_aendern": "plan", "option_aendern": "alternative",
            "wissen_aendern": "wissen", "lesetext_schreiben": "wissen", "reise_aendern": "einstellung", "plan_anlegen": "plan",
            "plan_aendern": "plan", "merkmal_zusammenfuehren": "ontologie", "arten_uebernehmen": "ontologie", "wunsch_vorschlagen": "wunsch",
            "start_ende_setzen": "einstellung", "symbol_setzen": "einstellung", "kartenansicht_setzen": "karte", "track_anhaengen": "ding", "kartenpunkte_holen": "karte",
            "gegenstand_anlegen": "gegenstand", "gegenstand_aendern": "gegenstand", "packliste_uebernehmen": "packliste_uebernehmen"}   # reise.AKTIONEN
HINWEISE_HOECHSTENS = 10   # neue Warnungen des Probebaus in der Antwort (Issue #142)
S = texte.satz   # Satz des Katalogs, in jeder Sprache lesbar (Bestätigungen, ADR-0006)
verbinden = texte.Satz.verbinden


def werkzeug_name(sprache, werkzeug):
    """Name des Werkzeugs, wie ihn der Commit nennt: der englische Name der Schnittstelle, in einer Sprache mit deutschen Aliassen
    (inhalt.schreiben.werkzeug_alias = 1) der interne."""
    if texte.t(sprache, "inhalt.schreiben.werkzeug_alias") == "1":
        return werkzeug
    import schnittstelle
    return schnittstelle.INTERN_ZU_ENGLISCH.get(werkzeug, werkzeug)


def lesbar(reise_dir, teile, trenner="; "):
    """Teile (Sätze oder feste Texte) als ein Text in der Sprache der Reise, für Einträge, die in Dateien der Reise geschrieben werden."""
    return texte.Satz.verbinden(teile, trenner).text(sprache_von(reise_dir))


def wechsel(feld, alt, neu, quotiert=False):
    """Eine Änderung für Antwort und Commit: „<Feld> <alt> → <neu>“, mit Anführungszeichen um Texte. Feldnamen und Datenwerte setzt der
    Katalog in der Sprache des Lesers; fehlt der alte Wert, steht ein Strich."""
    return S("schreiben.antwort.wechsel_text" if quotiert else "schreiben.antwort.wechsel", w1=feld, w2=anzeige_text(alt if alt not in (None, "") or quotiert else "–"),
             w3=anzeige_text(neu if neu not in (None, "") or quotiert else "–"))


def anzeige_text(v):
    """Ein Wert aus reise.yaml für einen Satz: Listen und Abschnitte als Folge ihrer Teile (Datenwerte darin übersetzt der Katalog)."""
    if isinstance(v, bool):
        return S("schreiben.wert_ja" if v else "schreiben.wert_nein")
    if isinstance(v, datetime.date) and not isinstance(v, datetime.datetime):
        return texte.Datum(v)
    if isinstance(v, (list, tuple)):
        return texte.Satz("[") + texte.Satz.verbinden([S("schreiben.wert_text", w1=x) for x in v], ", ") + "]"
    if isinstance(v, dict):
        return texte.Satz.verbinden([S("schreiben.antwort.feld_wert", w1=k, w2=anzeige_text(x)) for k, x in v.items()], ", ")
    return v if isinstance(v, str) else str(v)


def am_rand(sprache, text):
    """Ein Text für Commit und Antwort so, wie der Client die Schnittstelle sieht: englische Werkzeug- und Parameternamen; in einer
    Sprache mit deutschen Aliassen (inhalt.schreiben.werkzeug_alias = 1) bleiben die internen."""
    if texte.t(sprache, "inhalt.schreiben.werkzeug_alias") == "1":
        return text
    import schnittstelle
    return schnittstelle.parameter_im_text(schnittstelle.namen_im_text(text, streng=True))


def kurz_namen(geaendert):
    """Die Feldnamen am Anfang der Änderungssätze, für den Titel („beginn; ende“): bis zum ersten Leerzeichen oder Anführungszeichen,
    in der Sprache gelesen, in der der Titel steht (jeder Satz trägt seine Teile)."""
    return texte.Satz.verbinden([g.anfang() if isinstance(g, texte.Satz) else re.split(r"[ :„“]", str(g))[0] for g in geaendert], "; ")


def stufe_satz(s):
    """Wie routen.stufe_wort („nötig (pflicht)“), aber als Satz in jeder Sprache."""
    from routen import stufe_satz as satz
    return satz(s)


GRUNDFORM_WORT = texte.gruppe("de", "schreiben.grundform")   # Katalog in texte_de.py (ADR-0006)


def sprache_von(reise_dir):
    """Sprache der Reise (reise.yaml sprache): in ihr schreibt der Schreibweg alles, was in Dateien der Reise landet."""
    from reise import sprache_von as von
    return von(reise_dir)


class Ablehnung(Exception):
    """Der Schreibweg lehnt ab; der Text ist für den AI-Client (einfache Worte, nennt den Grund). Der Satz steht im Katalog
    (schreiben.*, ADR-0006): Ablehnung("schreiben.werkzeug.n", feld=wert …). str(e) ist der Satz im Rückfall (texte.VORGABE_REISE; Protokoll),
    text(sprache) der in der Sprache der Person; der Dienst schickt Schlüssel und Werte mit, der Konnektor setzt den Satz zusammen.
    Ein fertiger Satz ohne Schlüssel gilt weiter, wie er ist."""

    def __init__(self, text_oder_schluessel, **werte):
        if isinstance(text_oder_schluessel, texte.Satz) and text_oder_schluessel.schluessel:   # zum Beispiel die Begründung von reise.erlaubt
            self.schluessel, self.werte = text_oder_schluessel.schluessel, dict(text_oder_schluessel.werte)
            super().__init__(str(text_oder_schluessel))
            return
        self.schluessel = text_oder_schluessel if re.fullmatch(r"(schreiben|dienst)(\.[A-Za-z0-9_]+)+", str(text_oder_schluessel)) else None
        self.werte = {k: texte.Datum(v) if isinstance(v, datetime.date) and not isinstance(v, datetime.datetime)
                       else v if isinstance(v, (str, int, float, bool, texte.Satz)) or v is None else str(v) for k, v in werte.items()}
        super().__init__(texte.t(texte.VORGABE_REISE, self.schluessel, **self._werte_in(texte.VORGABE_REISE))
                         if self.schluessel else text_oder_schluessel)

    def _werte_in(self, sprache):
        """Werte für den Katalog; Sätze (zum Beispiel Prüfmeldungen der Reise) in dieser Sprache."""
        return {k: texte.wert_in(sprache, v) for k, v in self.werte.items()}

    def text(self, sprache):
        return texte.t(sprache, self.schluessel, **self._werte_in(sprache)) if self.schluessel else str(self)

    def werte_json(self):
        """Werte für den Weg zum Konnektor; Sätze reisen mit ihren Schlüsseln ({"satz": …}, texte.Satz.aus_json)."""
        return {k: texte.wert_json(v) for k, v in self.werte.items()}


# ---------- Hilfen ----------

def befehl_mit_frist(argv, eingabe, frist, env=None):
    """Befehl in eigener Prozessgruppe ausführen -> CompletedProcess. Nach `frist` Sekunden wird die ganze Gruppe beendet
    (auch Enkel wie ein git push unter dem Anwenden) und subprocess.TimeoutExpired geworfen."""
    if frist <= 0:
        raise subprocess.TimeoutExpired(argv, frist)
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                         start_new_session=True)
    try:
        out, err = p.communicate(eingabe, timeout=frist)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.wait()
        for strom in (p.stdin, p.stdout, p.stderr):   # nicht leerlesen: ein abgelöster Prozess kann sie noch offen halten
            try:
                strom.close()
            except OSError:
                pass
        raise subprocess.TimeoutExpired(argv, frist)
    return subprocess.CompletedProcess(argv, p.returncode, out, err)


def wurzel():
    return Path(os.environ.get("FR_WURZEL") or instanz.wurzel())


def schreibkopie(w=None):
    w = Path(w or wurzel())
    return Path(os.environ.get("FR_SCHREIBKOPIE") or f"{w}-schreiben")


def text_wert(args, feld, pflicht=False, laenge=MAX_TEXT, absaetze=False):
    """Ein Textfeld der Anfrage, bereinigt -> str oder None (fehlt oder leer). absaetze: für Lesetexte und Wissen bleiben
    Zeilen und Absätze, damit Tabellen und Listen im Markdown ankommen (#274); bereinigt wird nur am Zeilenende, mehrere
    Leerzeilen werden eine. Sonst wird jeder Weißraum ein Leerzeichen."""
    v = args.get(feld)
    if v is None or (isinstance(v, str) and not v.strip()):
        if pflicht:
            raise Ablehnung("schreiben.text_wert.1", feld=feld)
        return None
    if not isinstance(v, str):
        raise Ablehnung("schreiben.text_wert.2", feld=feld)
    if absaetze:
        zeilen = [z.rstrip() for z in v.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        v = re.sub(r"\n{3,}", "\n\n", "\n".join(zeilen)).strip()
    else:
        v = " ".join(v.split())
    if len(v) > laenge:
        raise Ablehnung("schreiben.text_wert.kurz" if laenge <= KURZ_FELD else "schreiben.text_wert.3", feld=feld, laenge=laenge)
    if not absaetze:
        sauber(v, feld)
    return v


# Saubere Daten (Product Owner 10.11.2026, #476): Was auf der Seite steht, trägt keine Herkunft (die gehört in quelle), keine
# Dateinamen, keine internen Kennungen (F-04, V-01.a, Auftrags- und Rückmelde-Nummern) und keine Bezeichnungen wie „Plan A“;
# Uhrzeiten stehen in Zeitfeldern. Geprüft wird beim Schreiben; Lesetexte und Wissen (Absätze) bleiben frei.
KURZ_FELD = 60
SICHTBARE_FELDER = {"titel", "name", "hinweis", "text", "preis", "bezahlt", "ab_was", "frist_was", "vor_ort_zahlen", "bei", "storno",
                    "anreise_ab", "abreise_bis", "neuer_titel", "untertitel", "wert"}
_URL = re.compile(r"https?://\S+|\b[\w.-]+\.(?:com|de|org|net|es|eu|info|io)(?:/\S*)?", re.I)
SAUBER_MUSTER = (   # (Schlüssel, Muster, auch in quelle)
    ("herkunft", re.compile(r"\b(?:OSM|OpenStreetMap)\s+(?:node|way|relation)\b|\b(?:node|way|relation)/\d+"), False),
    ("datei", re.compile(r"\b[\w-]+\.(?:pdf|txt|jpe?g|png|heic|docx?|xlsx?|gpx|html?|md|ya?ml|json|csv)\b", re.I), True),
    ("kennung", re.compile(r"\b(?:AG|[TEOUAVFWBPGR])-\d+(?:\.[a-z]+)?\b"), True),
    ("plan", re.compile(r"\bPlan [A-Z]\b"), True),
)
ZEIT_IM_TEXT = re.compile(r"\b\d{1,2}:\d{2}\b|\b\d{1,2}\s*Uhr\b")


def sauber(v, feld):
    """Prüft einen sichtbaren Text oder eine Herkunft (#476); lehnt mit Grund ab. Adressen von Webseiten bleiben außen vor."""
    if feld not in SICHTBARE_FELDER and feld != "quelle":
        return
    if feld == "wert" and SAUBER_MUSTER[2][1].fullmatch(str(v).strip()):
        return   # ein Wert, der nur eine Kennung ist, ist ein Verweis auf ein Ding (z. B. die Unterkunft eines Wegpunkts)
    t = _URL.sub(" ", str(v))
    if feld != "quelle":   # Herkunft in Worten („laut …“) in jeder Sprache des Katalogs
        for k in texte.sprachen():
            muster = (getattr(texte.sprache(k), "TEXTE", {}) or {}).get("schreiben.sauber.muster_herkunft")
            if muster and (m := re.search(muster, str(v))):
                raise Ablehnung("schreiben.sauber.herkunft", feld=feld, fund=m.group(0))
    for schluessel, muster, in_quelle in SAUBER_MUSTER:
        if feld == "quelle" and not in_quelle:
            continue
        if (m := muster.search(t)):
            raise Ablehnung("schreiben.sauber." + schluessel, feld=feld, fund=m.group(0))
    if feld in ("ab_was", "frist_was") and (m := ZEIT_IM_TEXT.search(t)):
        raise Ablehnung("schreiben.sauber.zeit", feld=feld, fund=m.group(0))


def bool_wert(args, feld):
    v = args.get(feld)
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "ja", "wahr", "false", "nein", "falsch"):
        return v.strip().lower() in ("true", "ja", "wahr")
    raise Ablehnung("schreiben.bool_wert.1", feld=feld)


def liste_wert(args, feld, laenge=MAX_WERTE):
    v = args.get(feld)
    if v is None or v == "" or v == []:
        return None
    if isinstance(v, str):
        v = [t for t in (x.strip() for x in v.split("|" if "|" in v else ",")) if t]
    if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
        raise Ablehnung("schreiben.liste_wert.1", feld=feld)
    v = list(dict.fromkeys(" ".join(x.split()) for x in v))
    if len(v) > laenge:
        raise Ablehnung("schreiben.liste_wert.2", feld=feld, laenge=laenge)
    return v


# ---------- Arten und Merkmale (plan/arten.yaml) ----------

def arten_text(arten, herkunft, sprache=None):
    """Inhalt von plan/arten.yaml: Kopfkommentar der Software (in der Sprache der Reise), dann die Arten; Wertelisten ausgeschrieben statt als Anker."""
    import yaml

    class Ohne_Verweise(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True
    return texte.t(sprache or texte.VORGABE_REISE, "inhalt.schreiben.arten_kopf", herkunft=herkunft) + yaml.dump({"arten": arten}, Dumper=Ohne_Verweise, allow_unicode=True,
                                                             sort_keys=False, width=120)


def arten_laden(reise_dir):
    import yaml
    p = Path(reise_dir) / "plan" / "arten.yaml"
    if not p.exists():
        return {}
    try:
        roh = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise Ablehnung("schreiben.arten_laden.1", e=e)
    arten = roh.get("arten") if isinstance(roh, dict) else None
    return arten if isinstance(arten, dict) else {}


def arten_speichern(reise_dir, arten, wer):
    p = Path(reise_dir) / "plan" / "arten.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    sp = sprache_von(reise_dir)   # Kopf und Herkunft stehen in der Sprache der Reise
    herkunft = texte.t(sp, "inhalt.schreiben.gepflegt", datum=datetime.date.today().isoformat(), wer=wer["name"])
    p.write_text(arten_text(arten, herkunft, sp), encoding="utf-8")


def lesetext_gliederung(roh):
    """Gliederung des Lesetexts einer Art aus der Anfrage (Liste von {rubrik, name, hilfe} oder {schluessel: {name, hilfe}})
    -> {rubrik: {name, hilfe}} in der Reihenfolge, None ohne Angabe, {} zum Entfernen (leere Liste)."""
    from routen import art_schluessel
    if roh is None:
        return None
    if isinstance(roh, dict):
        roh = [{"rubrik": k, **(v if isinstance(v, dict) else {"name": v})} for k, v in roh.items()]
    if not isinstance(roh, list):
        raise Ablehnung("schreiben.klammer.lesetext")
    aus = {}
    for r in roh:
        if not isinstance(r, dict) or not str(r.get("name") or "").strip():
            raise Ablehnung("schreiben.lesetext_gliederung.1")
        name = str(r["name"]).strip()[:60]
        key = art_schluessel(r.get("rubrik") or name)
        if not key or not SCHLUESSEL_MUSTER.match(key) or key in aus:
            raise Ablehnung("schreiben.lesetext_gliederung.2", name=name, key=key)
        if any(x["name"].casefold() == name.casefold() for x in aus.values()):
            raise Ablehnung("schreiben.lesetext_gliederung.3", name=name)
        aus[key] = {"name": name}
        if str(r.get("hilfe") or "").strip():
            aus[key]["hilfe"] = str(r["hilfe"]).strip()[:400]
    return aus


def art_definieren(reise_dir, wer, args):
    """Eine Art anlegen oder ändern (Bezeichnung, Grundform beim Anlegen, Farbe, Symbol, buchbar, summiert, Beschreibung,
    Gliederung des Lesetexts). -> (Titel für den Commit, Text für den AI-Client)."""
    from routen import ALLGEMEIN, ART_MUSTER, AUTO_JE_GRUNDFORM, FARBEN, GRUNDFORMEN, SYMBOLE_ARTEN, UNTERWEGS, art_schluessel
    arten = arten_laden(reise_dir)
    name = text_wert(args, "bezeichnung", laenge=80)
    key = text_wert(args, "art", laenge=40)
    if key is None:
        if name is None:
            raise Ablehnung("schreiben.art_definieren.1")
        key = art_schluessel(name)
    key = key.lower()
    if key in (UNTERWEGS, ALLGEMEIN):
        raise Ablehnung("schreiben.art_definieren.reserviert", key=key, w2=UNTERWEGS, w3=ALLGEMEIN)
    if not re.fullmatch(ART_MUSTER, key):
        raise Ablehnung("schreiben.art_definieren.2", key=key, w2=art_schluessel(key) or key)
    grundform = text_wert(args, "grundform", laenge=20)
    if grundform is not None and grundform.lower() not in GRUNDFORMEN:
        raise Ablehnung("schreiben.art_definieren.3", w1=', '.join(GRUNDFORMEN))
    farbe = text_wert(args, "farbe", laenge=20)
    if farbe is not None and farbe.lower() not in FARBEN:
        raise Ablehnung("schreiben.art_definieren.4", w1=', '.join(FARBEN))
    beschreibung = text_wert(args, "beschreibung")
    summiert = bool_wert(args, "summiert")
    buchbar = bool_wert(args, "buchbar")
    symbol = text_wert(args, "symbol", laenge=20)
    if symbol is not None and symbol.lower() not in SYMBOLE_ARTEN:
        raise Ablehnung("schreiben.art_definieren.5", w1=', '.join(SYMBOLE_ARTEN))
    lesetext = lesetext_gliederung(args.get("lesetext"))
    # Kartenpunkte (ADR-0007, Schritt d): gruppe macht aus der Art eine Kartenkategorie (punkt: Karte der Etappe, wissen: Karte im Wissen)
    from routen import ART_GRUPPEN
    gruppe = text_wert(args, "gruppe", laenge=20)
    if gruppe is not None and gruppe.lower() not in ART_GRUPPEN:
        raise Ablehnung("schreiben.kategorie_definieren.2", w1=', '.join(ART_GRUPPEN))
    einzahl, nummeriert = text_wert(args, "einzahl", laenge=80), bool_wert(args, "nummeriert")
    grund = text_wert(args, "grund")
    neu = key not in arten
    if neu:
        if name is None:
            raise Ablehnung("schreiben.art_definieren.1")
        if grundform is None:
            raise Ablehnung("schreiben.art_definieren.6", w1=', '.join(GRUNDFORMEN))
        grundform = grundform.lower()
        a = {"grundform": grundform, "name": name}
        if grundform == "aufenthalt":
            belegt = [x.get("farbe") for x in arten.values() if x.get("grundform") == "aufenthalt"]
            a["farbe"] = (farbe or next((f for f in FARBEN if f not in belegt), FARBEN[len(belegt) % len(FARBEN)])).lower()
        elif farbe:
            a["farbe"] = farbe.lower()
        if summiert and grundform != "bewegung":
            raise Ablehnung("schreiben.art_definieren.7")
        if summiert:
            a["summiert"] = True
        if symbol:
            a["symbol"] = symbol.lower()
        if buchbar is not None and buchbar != (grundform == "aufenthalt"):   # Vorgabe: Aufenthalte buchbar, sonst nicht
            a["buchbar"] = buchbar
        if beschreibung:
            a["beschreibung"] = beschreibung
        if lesetext:
            a["lesetext"] = lesetext
        if gruppe or einzahl or nummeriert:
            if grundform != "aufenthalt":
                raise Ablehnung("schreiben.art_definieren.gruppe_form")
            a.update({k: v for k, v in (("gruppe", gruppe.lower() if gruppe else None), ("einzahl", einzahl), ("nummeriert", True if nummeriert else None)) if v})
            a["buchbar"] = False if gruppe else a.get("buchbar", True)
        auto = AUTO_JE_GRUNDFORM.get(grundform, ()) if (grundform == "folge" or summiert) else ()
        if auto:
            sp = sprache_von(reise_dir)   # die Namen stehen in der Sprache der Reise
            namen = {m: texte.t(sp, "inhalt.schreiben.auto." + m) for m in ("gehzeit", "laenge", "hoehenmeter", "tage", "unterkuenfte", "anschluss")}
            a["merkmale"] = {m: {"name": namen.get(m, m.capitalize()), "auto": m} for m in auto}
        arten[key] = a
        titel = S("schreiben.titel.art_angelegt", w1=name, w2=key)
        text = (S("schreiben.antwort.art.angelegt", w1=name, w2=key) + S("schreiben.grundform." + grundform)
                + (S("schreiben.antwort.art.farbe", w1=a["farbe"]) if a.get("farbe") else "") + (S("schreiben.antwort.art.summiert") if a.get("summiert") else "") + "."
                + (S("schreiben.antwort.art.berechnet", w1=", ".join(auto)) if auto else "") + S("schreiben.antwort.art.merkmale_hinweis"))
    else:
        a = arten[key]
        if grundform is not None and grundform.lower() != a.get("grundform"):
            raise Ablehnung("schreiben.art_definieren.8", w1=a.get('name', key), w2=a.get('grundform'))
        if summiert and a.get("grundform") != "bewegung":
            raise Ablehnung("schreiben.art_definieren.9")
        geaendert = []
        if name is not None and name != a.get("name"):
            geaendert.append(S("schreiben.antwort.art.name", w1=a.get("name"), w2=name))
            a["name"] = name
        if farbe is not None and farbe.lower() != a.get("farbe"):
            geaendert.append(S("schreiben.antwort.art.farbe_neu", w1=farbe.lower()))
            a["farbe"] = farbe.lower()
        if beschreibung is not None and beschreibung != a.get("beschreibung"):
            geaendert.append(S("schreiben.antwort.art.beschreibung"))
            a["beschreibung"] = beschreibung
        if summiert is not None and bool(a.get("summiert")) != summiert:
            geaendert.append(S("schreiben.antwort.art.summiert_an" if summiert else "schreiben.antwort.art.summiert_aus"))
            if summiert:
                a["summiert"] = True
            else:
                a.pop("summiert", None)
        if symbol is not None and symbol.lower() != a.get("symbol"):
            geaendert.append(S("schreiben.antwort.art.symbol", w1=symbol.lower()))
            a["symbol"] = symbol.lower()
        if buchbar is not None and bool(a.get("buchbar", a.get("grundform") == "aufenthalt")) != buchbar:
            geaendert.append(S("schreiben.antwort.art.buchbar" if buchbar else "schreiben.antwort.art.nicht_buchbar"))
            a["buchbar"] = buchbar
        if lesetext is not None and lesetext != a.get("lesetext"):
            geaendert.append(S("schreiben.antwort.art.lesetext", w1=", ".join(r["name"] for r in lesetext.values())))
            a["lesetext"] = lesetext
        for feld, wert in (("gruppe", gruppe.lower() if gruppe else None), ("einzahl", einzahl)):
            if wert is not None and wert != a.get(feld):
                if a.get("grundform") != "aufenthalt":
                    raise Ablehnung("schreiben.art_definieren.gruppe_form")
                a[feld] = wert
                geaendert.append(S("schreiben.antwort.feld_wert", w1=feld, w2=wert))
        if nummeriert is not None and bool(a.get("nummeriert")) != nummeriert:
            if nummeriert:
                a["nummeriert"] = True
            else:
                a.pop("nummeriert", None)
            geaendert.append(S("schreiben.antwort.kategorie.nummeriert" if nummeriert else "schreiben.antwort.kategorie.nicht_nummeriert"))
        if not geaendert:
            raise Ablehnung("schreiben.art_definieren.10", w1=a.get('name', key), key=key)
        arten[key] = {k: a[k] for k in ART_FELDER_REIHE if k in a}
        titel = S("schreiben.titel.art_geaendert", w1=a['name'], w2=key)
        text = S("schreiben.antwort.art.geaendert", w1=a["name"], w2=key) + verbinden(geaendert) + "."
    arten_speichern(reise_dir, arten, wer)
    return titel, text + (S("schreiben.antwort.grund", w1=grund) if grund else "")


# ---------- Kategorien der Kartenpunkte (plan/kategorien.yaml) ----------



def kategorien_laden(reise_dir):
    import yaml
    p = Path(reise_dir) / "plan" / "kategorien.yaml"
    if not p.exists():
        return {}
    try:
        roh = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise Ablehnung("schreiben.kategorien_laden.1", e=e)
    k = roh.get("kategorien") if isinstance(roh, dict) else None
    return k if isinstance(k, dict) else {}


def kategorien_speichern(reise_dir, kategorien, wer):
    import yaml

    class Ohne_Verweise(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True
    p = Path(reise_dir) / "plan" / "kategorien.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    sp = sprache_von(reise_dir)   # Kopf und Herkunft stehen in der Sprache der Reise
    herkunft = texte.t(sp, "inhalt.schreiben.gepflegt", datum=datetime.date.today().isoformat(), wer=wer["name"])
    p.write_text(texte.t(sp, "inhalt.schreiben.kategorien_kopf", herkunft=herkunft)
                 + yaml.dump({"kategorien": kategorien}, Dumper=Ohne_Verweise, allow_unicode=True, sort_keys=False, width=120),
                 encoding="utf-8")


def kategorie_definieren(reise_dir, wer, args):
    """Eine Kartenkategorie anlegen oder ändern (ADR-0007, Schritt d: eine Kategorie ist eine Art der Grundform aufenthalt mit gruppe,
    auch ohne Merkmale), dazu der Zusatz zu einer art (sorten). Alias von kind_define (art_definieren). -> (Titel, Text)"""
    from routen import ART_GRUPPEN, ART_MUSTER, SYMBOLE_ARTEN
    from bauen import KATEGORIE_FARBEN, KATEGORIE_MUSTER
    arten = arten_laden(reise_dir)
    name = text_wert(args, "bezeichnung", laenge=80)
    key = text_wert(args, "kategorie", pflicht=True, laenge=40).lower()
    if not re.fullmatch(KATEGORIE_MUSTER, key) or not re.fullmatch(ART_MUSTER, key):
        raise Ablehnung("schreiben.kategorie_definieren.1", key=key)
    gruppe = text_wert(args, "gruppe", laenge=20)
    if gruppe is not None and gruppe.lower() not in ART_GRUPPEN:
        raise Ablehnung("schreiben.kategorie_definieren.2", w1=', '.join(ART_GRUPPEN))
    farbe = text_wert(args, "farbe", laenge=20)
    if farbe is not None and farbe.lower() not in KATEGORIE_FARBEN and not re.fullmatch(r"#[0-9a-fA-F]{6}", farbe):
        raise Ablehnung("schreiben.kategorie_definieren.3", w1=', '.join(KATEGORIE_FARBEN))
    symbol = text_wert(args, "symbol", laenge=20)
    if symbol is not None and symbol not in SYMBOLE_ARTEN:
        raise Ablehnung("schreiben.kategorie_definieren.4", w1=', '.join(SYMBOLE_ARTEN))
    einzahl = text_wert(args, "einzahl", laenge=80)
    nummeriert = bool_wert(args, "nummeriert")
    sorte = text_wert(args, "art", laenge=40)
    sorte_name, sorte_symbol = text_wert(args, "art_bezeichnung", laenge=80), text_wert(args, "art_symbol", laenge=20)
    sorte_hinweis, sorte_umriss = text_wert(args, "art_hinweis"), bool_wert(args, "art_umriss")
    if sorte_symbol is not None and sorte_symbol not in SYMBOLE_ARTEN:
        raise Ablehnung("schreiben.kategorie_definieren.5", w1=', '.join(SYMBOLE_ARTEN))
    if sorte is None and any(x is not None for x in (sorte_name, sorte_symbol, sorte_hinweis, sorte_umriss)):
        raise Ablehnung("schreiben.kategorie_definieren.6")
    grund = text_wert(args, "grund")
    geaendert = []
    if key not in arten:
        if name is None or gruppe is None or farbe is None:
            raise Ablehnung("schreiben.kategorie_definieren.7")
        k = {"grundform": "aufenthalt", "name": name, "gruppe": gruppe.lower()}
        titel, kopf = S("schreiben.titel.kategorie_angelegt", w1=name, w2=key), S("schreiben.antwort.kategorie.angelegt", w1=name, w2=key, w3=k["gruppe"], w4=farbe)
        neu = True
    else:
        k = arten[key]
        neu = False
        if k.get("grundform") != "aufenthalt":
            raise Ablehnung("schreiben.kategorie_definieren.keine_aufenthaltsart", w1=k.get("name", key))
        if gruppe is not None and gruppe.lower() != k.get("gruppe"):
            if k.get("gruppe"):
                raise Ablehnung("schreiben.kategorie_definieren.8", w1=k.get('name', key), w2=k.get('gruppe'))
            k["gruppe"] = gruppe.lower()
            geaendert.append(S("schreiben.antwort.feld_wert", w1="gruppe", w2=gruppe.lower()))
        if name is not None and name != k.get("name"):
            geaendert.append(S("schreiben.antwort.art.name", w1=k.get("name"), w2=name))
            k["name"] = name
    for feld, wert in (("einzahl", einzahl), ("farbe", farbe), ("symbol", symbol)):
        if wert is not None and wert != k.get(feld):
            k[feld] = wert
            geaendert.append(S("schreiben.antwort.feld_wert", w1=feld, w2=wert))
    if nummeriert is not None and bool(k.get("nummeriert")) != nummeriert:
        if nummeriert:
            k["nummeriert"] = True
        else:
            k.pop("nummeriert", None)
        geaendert.append(S("schreiben.antwort.kategorie.nummeriert" if nummeriert else "schreiben.antwort.kategorie.nicht_nummeriert"))
    if sorte is not None:
        sorten = k.setdefault("sorten", {})
        a = sorten.get(sorte) if isinstance(sorten.get(sorte), dict) else {}
        for feld, wert in (("name", sorte_name), ("symbol", sorte_symbol), ("hinweis", sorte_hinweis)):
            if wert is not None and wert != a.get(feld):
                a[feld] = wert
                geaendert.append(S("schreiben.antwort.kategorie.art_feld", w1=sorte, w2=feld, w3=wert))
        if sorte_umriss is not None and bool(a.get("umriss")) != sorte_umriss:
            if sorte_umriss:
                a["umriss"] = True
            else:
                a.pop("umriss", None)
            geaendert.append(S("schreiben.antwort.kategorie.umriss" if sorte_umriss else "schreiben.antwort.kategorie.ohne_umriss", w1=sorte))
        sorten[sorte] = a
    if neu:
        k["farbe"] = farbe
        k["buchbar"] = False   # ein Kartenpunkt wird nicht gebucht
        arten[key] = {f: k[f] for f in ("grundform", "name", "farbe", "symbol", "buchbar", "gruppe", "einzahl", "nummeriert", "sorten") if k.get(f) not in (None, "") or f == "buchbar"}
        text = kopf + (S("schreiben.antwort.kategorie.ausserdem", w1=verbinden(geaendert, ", ")) if geaendert else "") + "."
    else:
        if not geaendert:
            raise Ablehnung("schreiben.kategorie_definieren.9", w1=k.get('name', key), key=key)
        arten[key] = {f: k[f] for f in ART_FELDER_REIHE if f in k}
        titel = S("schreiben.titel.kategorie_geaendert", w1=k['name'], w2=key)
        text = S("schreiben.antwort.kategorie.geaendert", w1=k["name"], w2=key) + verbinden(geaendert) + "."
    arten_speichern(reise_dir, arten, wer)
    return titel, text + (S("schreiben.antwort.grund", w1=grund) if grund else "")


# Felder einer Art in der Reihenfolge, in der die Datei sie schreibt (ADR-0007: dazu die Felder einer früheren Kartenkategorie)
ART_FELDER_REIHE = ("grundform", "name", "farbe", "symbol", "buchbar", "summiert", "beschreibung", "merkmale", "lesetext", "buchung_merkmale",
                    "gruppe", "einzahl", "nummeriert", "sorten")


def rolle_pruefen(merkmale, key, rolle, typ):
    """Die Rolle kosten braucht den Typ geld, summe den Typ zahl oder geld, hero den Typ text; jede Rolle gilt je Art nur einmal,
    summe darf mehrfach vorkommen (Gewicht und Preis, ADR-0010)."""
    from routen import ROLLEN_MEHRFACH
    if rolle == "kosten" and typ != "geld":
        raise Ablehnung("schreiben.rolle_pruefen.1")
    if rolle == "summe" and typ not in ("zahl", "geld"):
        raise Ablehnung("schreiben.rolle_pruefen.summe")
    if rolle == "hero" and typ != "text":
        raise Ablehnung("schreiben.rolle_pruefen.3")
    if rolle in ROLLEN_MEHRFACH:
        return
    andere = next((k for k, d in merkmale.items() if k != key and isinstance(d, dict) and d.get("rolle") == rolle), None)
    if andere:
        raise Ablehnung("schreiben.rolle_pruefen.2", rolle=rolle, w2=merkmale[andere].get('name', andere), andere=andere)


def buchung_merkmal_definieren(reise_dir, wer, args, arten, art):
    """Ein Merkmal der Buchungen einer Art anlegen oder ändern (#166): Name, Typ (Auswahl mit Werten), Einheit, Hilfe, Frage.
    Keine Stufe, Rolle oder Prüfdatum: der Wert ist eine gebuchte Tatsache mit der Herkunft der Buchung. -> (Titel, Text)."""
    from routen import TYPEN, art_schluessel
    for f in ("stufe", "veraenderlich", "rolle", "auch", "nach_buchung", "lang"):
        if args.get(f) not in (None, "", [], False):
            raise Ablehnung("schreiben.buchung_merkmal.nicht", f=f)
    a = arten[art]
    merkmale = a.get("buchung_merkmale") if isinstance(a.get("buchung_merkmale"), dict) else {}
    name = text_wert(args, "bezeichnung", laenge=80)
    key = text_wert(args, "merkmal", laenge=40)
    if key is None:
        if name is None:
            raise Ablehnung("schreiben.buchung_merkmal.bezeichnung")
        key = art_schluessel(name)
    key = key.lower()
    if not SCHLUESSEL_MUSTER.match(key):
        raise Ablehnung("schreiben.merkmal_definieren.2", key=key)
    typ = text_wert(args, "typ", laenge=20)
    if typ is not None and typ.lower() not in TYPEN:
        raise Ablehnung("schreiben.merkmal_definieren.3", w1=', '.join(sorted(TYPEN)))
    werte = liste_wert(args, "werte")
    einheit, hilfe, frage, grund = (text_wert(args, f) for f in ("einheit", "hilfe", "frage", "grund"))
    if key not in merkmale:
        if name is None:
            raise Ablehnung("schreiben.buchung_merkmal.bezeichnung")
        typ = (typ or "text").lower()
        if typ == "auswahl" and not werte:
            raise Ablehnung("schreiben.buchung_merkmal.auswahl_werte")
        if werte and typ != "auswahl":
            raise Ablehnung("schreiben.merkmal_definieren.9")
        d = {"name": name, "typ": typ}
        for f, v in (("werte", werte), ("einheit", einheit), ("hilfe", hilfe), ("frage", frage)):
            if v:
                d[f] = v
        merkmale[key] = d
        titel = S("schreiben.titel.buchung_merkmal_angelegt", w1=name, w2=key, w3=a.get('name', art))
        text = (S("schreiben.antwort.buchung_merkmal.angelegt", w1=name, w2=key, w3=a.get("name", art), w4=typ)
                + (f" ({' | '.join(werte)})" if werte else "") + S("schreiben.antwort.buchung_merkmal.hinweis"))
    else:
        d = merkmale[key]
        geaendert = []
        if typ is not None and typ.lower() != d.get("typ", "text"):
            if typ.lower() == "auswahl" and not (werte or d.get("werte")):
                raise Ablehnung("schreiben.merkmal_definieren.11")
            geaendert.append(S("schreiben.antwort.merkmal.typ", w1=typ.lower()))
            d["typ"] = typ.lower()
            if typ.lower() != "auswahl":
                d.pop("werte", None)
        if werte is not None:
            if d.get("typ", "text") != "auswahl":
                raise Ablehnung("schreiben.merkmal_definieren.9")
            if werte != d.get("werte"):
                geaendert.append(S("schreiben.antwort.merkmal.werte", w1=" | ".join(werte)))
                d["werte"] = werte
        if name is not None and name != d.get("name"):
            geaendert.append(S("schreiben.antwort.art.name", w1=d.get("name"), w2=name))
            d["name"] = name
        for f, v in (("einheit", einheit), ("hilfe", hilfe), ("frage", frage)):
            if v is not None and v != d.get(f):
                geaendert.append(S("schreiben.antwort.merkmal.feld." + f))
                d[f] = v
        if not geaendert:
            raise Ablehnung("schreiben.buchung_merkmal.unveraendert", w1=d.get("name", key), key=key, w3=a.get("name", art))
        merkmale[key] = {k: d[k] for k in ("name", "typ", "werte", "einheit", "hilfe", "frage") if k in d}
        titel = S("schreiben.titel.buchung_merkmal_geaendert", w1=d['name'], w2=key, w3=a.get('name', art))
        text = S("schreiben.antwort.buchung_merkmal.geaendert", w1=d["name"], w2=key, w3=a.get("name", art)) + verbinden(geaendert) + "."
    a["buchung_merkmale"] = merkmale
    arten_speichern(reise_dir, arten, wer)
    return titel, text + (S("schreiben.antwort.grund", w1=grund) if grund else "")


def merkmal_definieren(reise_dir, wer, args):
    """Ein Merkmal einer Art anlegen oder ändern (umbenennen, Stufe, abschalten mit Stufe aus). fuer: ding (Vorgabe, das
    Angebot) oder buchung (Merkmale der Buchungen dieser Art, #166). -> (Titel, Text)."""
    from routen import ROLLEN, STUFEN, TYPEN, art_schluessel, stufe_schluessel, stufe_wort
    arten = arten_laden(reise_dir)
    art = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
    if art not in arten:
        raise Ablehnung("schreiben.art_unbekannt_vorhanden", art=art, arten=", ".join(arten)) if arten else Ablehnung("schreiben.art_unbekannt", art=art)
    fuer = (text_wert(args, "fuer", laenge=20) or "ding").lower()
    if fuer not in ("ding", "buchung"):
        raise Ablehnung("schreiben.merkmal_definieren.fuer")
    if fuer == "buchung":
        return buchung_merkmal_definieren(reise_dir, wer, args, arten, art)
    a = arten[art]
    merkmale = a.get("merkmale") if isinstance(a.get("merkmale"), dict) else {}
    name = text_wert(args, "bezeichnung", laenge=80)
    key = text_wert(args, "merkmal", laenge=40)
    if key is None:
        if name is None:
            raise Ablehnung("schreiben.merkmal_definieren.1")
        key = art_schluessel(name)
    key = key.lower()
    if not SCHLUESSEL_MUSTER.match(key):
        raise Ablehnung("schreiben.merkmal_definieren.2", key=key)
    typ = text_wert(args, "typ", laenge=20)
    if typ is not None and typ.lower() not in TYPEN:
        raise Ablehnung("schreiben.merkmal_definieren.3", w1=', '.join(sorted(TYPEN)))
    stufe = text_wert(args, "stufe", laenge=20)
    if stufe is not None:   # Schlüssel oder Wort für Menschen (nötig, gut zu wissen, zusätzlich); gespeichert wird der Schlüssel
        stufe = stufe_schluessel(stufe)
        if stufe is None:
            raise Ablehnung("schreiben.merkmal_definieren.4", w1=', '.join(STUFEN))
    werte = liste_wert(args, "werte")
    veraenderlich = bool_wert(args, "veraenderlich")
    nach_buchung = bool_wert(args, "nach_buchung")   # bleibt sichtbar, wenn das Ding gebucht ist (31.10.2026)
    lang = bool_wert(args, "lang")   # Text darf länger als KURZ_TEXT sein (#476)
    einheit, hilfe, frage, grund = (text_wert(args, f) for f in ("einheit", "hilfe", "frage", "grund"))
    rolle = text_wert(args, "rolle", laenge=20)
    if rolle is not None and rolle not in ("", "keine", *ROLLEN):
        raise Ablehnung("schreiben.merkmal_definieren.5", w1=', '.join(ROLLEN))
    rolle = None if rolle is None else (rolle if rolle in ROLLEN else "")
    auch = liste_wert(args, "auch")
    if auch is not None:
        auch = [art_schluessel(x) for x in auch]
        if any(not SCHLUESSEL_MUSTER.match(x) or x == key for x in auch):
            raise Ablehnung("schreiben.merkmal_definieren.6")
    for k, d in merkmale.items():
        if k != key and isinstance(d, dict) and key in (d.get("auch") or []):
            raise Ablehnung("schreiben.merkmal_definieren.7", key=key, w2=a.get('name', art), w3=d.get('name', k), k=k)
    neu = key not in merkmale
    if neu:
        if name is None:
            raise Ablehnung("schreiben.merkmal_definieren.1")
        typ = (typ or "text").lower()
        if typ == "auswahl" and not werte:
            raise Ablehnung("schreiben.merkmal_definieren.8")
        if werte and typ != "auswahl":
            raise Ablehnung("schreiben.merkmal_definieren.9")
        d = {"name": name, "typ": typ}
        if werte:
            d["werte"] = werte
        if veraenderlich:
            d["veraenderlich"] = True
        if nach_buchung:
            d["nach_buchung"] = True
        if lang:
            d["lang"] = True
        if einheit:
            d["einheit"] = einheit
        if stufe and stufe != "empfohlen":
            d["stufe"] = stufe
        for f, v in (("hilfe", hilfe), ("frage", frage), ("auch", auch)):
            if v:
                d[f] = v
        if rolle:
            rolle_pruefen(merkmale, key, rolle, typ)
            d["rolle"] = rolle
        merkmale[key] = d
        titel = S("schreiben.titel.merkmal_angelegt", w1=name, w2=key, w3=a.get('name', art))
        text = (S("schreiben.antwort.merkmal.angelegt", w1=name, w2=key, w3=a.get("name", art), w4=typ)
                + (f" ({' | '.join(werte)})" if werte else "") + (S("schreiben.antwort.merkmal.veraenderlich_hinweis") if veraenderlich else "")
                + S("schreiben.antwort.merkmal.stufe_kopf") + stufe_satz(stufe or "empfohlen")
                + (S("schreiben.antwort.merkmal.nach_buchung_hinweis") if nach_buchung else "") + ".")
    else:
        d = merkmale[key]
        if d.get("auto") and any(x is not None for x in (typ, werte, veraenderlich, einheit, rolle, nach_buchung)):
            raise Ablehnung("schreiben.merkmal_definieren.10", w1=d.get('name', key))
        geaendert = []
        if rolle is not None and rolle != (d.get("rolle") or ""):
            if rolle:
                rolle_pruefen(merkmale, key, rolle, (typ or d.get("typ", "text")).lower())
                d["rolle"] = rolle
                geaendert.append(S("schreiben.antwort.merkmal.rolle", w1=rolle))
            else:
                d.pop("rolle", None)
                geaendert.append(S("schreiben.antwort.merkmal.keine_rolle"))
        if typ is not None and typ.lower() != d.get("typ", "text"):
            if typ.lower() == "auswahl" and not (werte or d.get("werte")):
                raise Ablehnung("schreiben.merkmal_definieren.11")
            geaendert.append(S("schreiben.antwort.merkmal.typ", w1=typ.lower()))
            d["typ"] = typ.lower()
            if typ.lower() != "auswahl":
                d.pop("werte", None)
        if werte is not None:
            if d.get("typ", "text") != "auswahl":
                raise Ablehnung("schreiben.merkmal_definieren.9")
            if werte != d.get("werte"):
                geaendert.append(S("schreiben.antwort.merkmal.werte", w1=" | ".join(werte)))
                d["werte"] = werte
        if name is not None and name != d.get("name"):
            geaendert.append(S("schreiben.antwort.art.name", w1=d.get("name"), w2=name))
            d["name"] = name
        if veraenderlich is not None and bool(d.get("veraenderlich")) != veraenderlich:
            geaendert.append(S("schreiben.antwort.merkmal.veraenderlich" if veraenderlich else "schreiben.antwort.merkmal.nicht_veraenderlich"))
            if veraenderlich:
                d["veraenderlich"] = True
            else:
                d.pop("veraenderlich", None)
        if nach_buchung is not None and bool(d.get("nach_buchung")) != nach_buchung:
            geaendert.append(S("schreiben.antwort.merkmal.nach_buchung_an" if nach_buchung else "schreiben.antwort.merkmal.nach_buchung_aus"))
            if nach_buchung:
                d["nach_buchung"] = True
            else:
                d.pop("nach_buchung", None)
        if lang is not None and bool(d.get("lang")) != lang:
            geaendert.append(S("schreiben.antwort.merkmal.lang_an" if lang else "schreiben.antwort.merkmal.lang_aus"))
            if lang:
                d["lang"] = True
            else:
                d.pop("lang", None)
        if stufe is not None and stufe != (d.get("stufe") if isinstance(d.get("stufe"), str) else "empfohlen"):
            geaendert.append(S("schreiben.antwort.merkmal.stufe_aus") if stufe == "aus" else S("schreiben.antwort.merkmal.stufe_kopf_geaendert") + stufe_satz(stufe))
            if stufe == "empfohlen":
                d.pop("stufe", None)
            else:
                d["stufe"] = stufe
        for f, v in (("einheit", einheit), ("hilfe", hilfe), ("frage", frage)):
            if v is not None and v != d.get(f):
                geaendert.append(S("schreiben.antwort.merkmal.feld." + f))
                d[f] = v
        if auch is not None and auch != d.get("auch"):
            geaendert.append(S("schreiben.antwort.merkmal.auch", w1=", ".join(auch)))
            d["auch"] = auch
        if not geaendert:
            raise Ablehnung("schreiben.merkmal_definieren.12", w1=d.get('name', key), key=key, w3=a.get('name', art))
        merkmale[key] = {k: d[k] for k in ("name", "typ", "werte", "auto", "veraenderlich", "einheit", "stufe", "rolle", "nach_buchung",
                                           "lang", "hilfe", "frage", "auch") if k in d}
        titel = S("schreiben.titel.merkmal_geaendert", w1=d['name'], w2=key, w3=a.get('name', art))
        text = S("schreiben.antwort.merkmal.geaendert", w1=d["name"], w2=key, w3=a.get("name", art)) + verbinden(geaendert) + "."
    a["merkmale"] = merkmale
    arten_speichern(reise_dir, arten, wer)
    return titel, text + (S("schreiben.antwort.grund", w1=grund) if grund else "")


# ---------- Werte an Dingen (plan/routen.yaml) ----------
# Die Routendatei wird mit ruamel.yaml rund gelesen und geschrieben: Kommentare, Reihenfolge und Fließform bleiben; nur von
# Hand umbrochene Fließ-Mappings werden in eine Zeile gezogen (einmalige Normalform, danach ändert ein Schreibvorgang nur seine Stelle).
ZIEL_MUSTER = re.compile(r"^(U-\d+|A-\d+|O-\d+|E-\d+[A-Za-z]?|V-\d+\.[a-z])$")


def yaml_rund():
    from ruamel.yaml import YAML
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    y.representer.ignore_aliases = lambda *a: True     # gleiche Daten je Eintrag ausschreiben statt als Anker
    return y


def routen_geruest(reise_dir):
    """Leerer Plan einer Reise, die noch keinen hat (neu aus der App, Status idee): Start und Ende aus dem Zeitraum in
    reise.yaml, noch ohne Ort. Der erste Eintrag (Ort, Strecke, Tag ...) legt ihn an (frieda-reist #135)."""
    import yaml
    try:
        z = (yaml.safe_load((Path(reise_dir) / "reise.yaml").read_text(encoding="utf-8")) or {}).get("zeitraum") or {}
    except (OSError, yaml.YAMLError):
        z = {}
    if not (isinstance(z.get("von"), datetime.date) and isinstance(z.get("bis"), datetime.date)):
        raise Ablehnung("schreiben.routen_geruest.1")
    return {"start": {"datum": z["von"]}, "ende": {"datum": z["bis"]}, "orte": {}, "strecken": {}, "tage": {}, "route": []}


def plan_sicherstellen(reise_dir):
    """Eine Reise aus der App hat noch keinen Plan: legt plan/routen.yaml (routen_geruest) an und trägt ihn in reise.json
    ein, damit der Generator ihn liest (Probebau, Arten der Reise, Seite). Eingetragen wird er erst, wenn die Reise
    Arten hat: Ein Plan ohne Arten baut nicht (docs/ontologie.md). Vorhandenes bleibt unberührt."""
    reise_dir = Path(reise_dir)
    if not (reise_dir / "plan" / "routen.yaml").exists():
        routen_speichern(reise_dir, routen_geruest(reise_dir))
    rj = reise_dir / "reise.json"
    if rj.exists() and arten_laden(reise_dir):
        try:
            cfg = json.loads(rj.read_text(encoding="utf-8"))
        except ValueError:
            raise Ablehnung("schreiben.reise_json.unlesbar")
        routen = cfg.get("routen") or {}
        neu_ = dict(routen)
        neu_.setdefault("datei", "plan/routen.yaml")
        if "tagesplan" not in neu_:
            # ohne diese Abschnitte zeigt die Seite keine Tage und keine Unterkünfte (bauen.py, route_ansicht); Titel in der
            # Sprache der Reise, neue W-IDs aus ids.yaml (der Generator legt die Abschnitte dann selbst an)
            import reise as reise_modul
            sprache = reise_modul.sprache_von(reise_dir)
            neu_["tagesplan"] = [neue_id(reise_dir, "W"), texte.t(sprache, "seite.suche.tagesplan")]
            if "unterkuenfte" not in neu_:
                neu_["unterkuenfte"] = [neue_id(reise_dir, "W"), texte.t(sprache, "seite.suche.unterkuenfte")]
        if neu_ != routen:
            cfg["routen"] = neu_
            rj.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def routen_laden(reise_dir):
    p = Path(reise_dir) / "plan" / "routen.yaml"
    if not p.exists():
        plan_sicherstellen(reise_dir)
    try:
        return yaml_rund().load(p.read_text(encoding="utf-8"))
    except Exception as e:   # ruamel wirft verschiedene Fehlerklassen
        raise Ablehnung("schreiben.routen_laden.2", __name__=type(e).__name__)


def routen_speichern(reise_dir, roh):
    import io
    out = io.StringIO()
    yaml_rund().dump(roh, out)
    (Path(reise_dir) / "plan" / "routen.yaml").write_text(out.getvalue(), encoding="utf-8")


def routen_normalisieren(reise_dir):
    """Datei einmal rund schreiben (Normalform des Schreibwegs) -> True, wenn sich der Text geändert hat."""
    p = Path(reise_dir) / "plan" / "routen.yaml"
    alt = p.read_text(encoding="utf-8")
    routen_speichern(reise_dir, routen_laden(reise_dir))
    return p.read_text(encoding="utf-8") != alt


def ding_finden(roh, ziel):
    """-> (Knoten in der Routendatei, Beschreibung) für U-…, A-…, O-…, E-… oder eine Option V-01.a."""
    if ziel.startswith("O-"):
        k = (roh.get("orte") or {}).get(ziel)
        if k is None:
            raise Ablehnung("schreiben.ding_aendern.2", ziel=ziel)
        return k, f"{ziel} {k.get('name', '')}".strip()
    if ziel.startswith("U-"):
        k = (roh.get("unterkuenfte") or {}).get(ziel)
        if k is None:
            raise Ablehnung("schreiben.ding_finden.1", ziel=ziel)
        return k, f"{ziel} {k.get('name', '')}".strip()
    if ziel.startswith("A-"):
        k = (roh.get("aufenthalte") or {}).get(ziel)
        if k is None:
            raise Ablehnung("schreiben.ding_finden.2", ziel=ziel)
        return k, f"{ziel} {k.get('name', '')}".strip()
    if ziel.startswith("E-"):
        k = (roh.get("strecken") or {}).get(ziel)
        if k is None:
            raise Ablehnung("schreiben.ding_finden.3", ziel=ziel)
        return k, f"{ziel} {k.get('titel', '')}".strip()
    vid = ziel.split(".")[0]
    w = (roh.get("wahlstellen") or {}).get(vid)
    for o in (w or {}).get("optionen") or []:
        if isinstance(o, dict) and o.get("id") == ziel:
            return o, f"{ziel} {o.get('titel', '')}".strip()
    raise Ablehnung("schreiben.ding_finden.4", ziel=ziel)


def datum(text, feld, k):
    """ISO-Text -> datetime.date oder Ablehnung."""
    try:
        return datetime.date.fromisoformat(str(text).strip())
    except (ValueError, TypeError):
        raise Ablehnung("schreiben.datum.1", k=k, feld=feld)


def wert_eintraege(args, k, definition, heute, herkunft=True):
    """Die neuen Werte aus der Anfrage prüfen -> Liste von Einträgen {wert, quelle, geprueft?, notiz?, gilt?} (Daten als date).
    Herkunftspflicht: jeder Wert braucht quelle; ein veränderliches Merkmal auch geprueft (nicht in der Zukunft).
    herkunft=False: ausdrückliche Ausnahme der Gegenstände der Packliste (ADR-0010): keine Herkunft nötig, das Prüfdatum bleibt."""
    roh = args.get("werte")
    if roh in (None, "", []):
        roh = [{f: args.get(f) for f in ("wert", "quelle", "geprueft", "notiz", "gilt")}]
    if not isinstance(roh, list) or not all(isinstance(x, dict) for x in roh):
        raise Ablehnung("schreiben.klammer.werte")
    aus = []
    for x in roh:
        x = {**{f: args.get(f) for f in ("quelle", "geprueft", "notiz") if args.get(f) not in (None, "")}, **x}
        wert = x.get("wert")
        if isinstance(wert, bool):
            wert = "ja" if wert else "nein"
        if wert is None or str(wert).strip() == "":
            raise Ablehnung("schreiben.wert_eintraege.1", k=k)
        wert = " ".join(str(wert).split()) if not isinstance(wert, (int, float)) else wert
        if definition.get("typ") == "auswahl" and str(wert) not in [str(v) for v in definition.get("werte") or []]:
            raise Ablehnung("schreiben.wert_eintraege.2", k=k, wert=wert, w3=', '.join(map(str, definition.get('werte') or [])))
        if definition.get("typ") == "link":
            from routen import ist_link
            if not ist_link(wert):
                raise Ablehnung("schreiben.wert_eintraege.link", k=k, wert=wert)
        elif isinstance(wert, str) and definition.get("typ") in (None, "text"):
            # Saubere Daten (#476): Text-Merkmale kurz, außer die Reise markiert sie als lang; keine Herkunft und keine Kennungen im Wert
            from routen import KURZ_TEXT
            if len(wert) > KURZ_TEXT and not definition.get("lang"):
                raise Ablehnung("schreiben.wert_eintraege.lang", k=k, laenge=KURZ_TEXT)
            sauber(wert, "wert")
        if x.get("quelle"):
            sauber(x["quelle"], "quelle")
        if definition.get("typ") == "zahl":
            try:
                wert = float(str(wert).replace(",", "."))
                wert = int(wert) if wert == int(wert) else wert
            except ValueError:
                raise Ablehnung("schreiben.wert_eintraege.3", k=k)
        quelle = x.get("quelle")
        if herkunft and (not isinstance(quelle, str) or not quelle.strip()):
            raise Ablehnung("schreiben.wert_eintraege.4", k=k)
        e = {"wert": wert}
        if isinstance(quelle, str) and quelle.strip():
            e["quelle"] = " ".join(quelle.split())[:MAX_TEXT]
        g = x.get("geprueft")
        if g not in (None, ""):
            e["geprueft"] = datum(g, "geprueft", k)
            if e["geprueft"] > heute:
                raise Ablehnung("schreiben.wert_eintraege.5", k=k)
        elif definition.get("veraenderlich"):
            raise Ablehnung("schreiben.wert_eintraege.6", k=k, w2=heute.isoformat())
        if x.get("notiz") not in (None, ""):
            e["notiz"] = " ".join(str(x["notiz"]).split())[:MAX_TEXT]
        gilt = x.get("gilt")
        if gilt not in (None, "", []):
            tage = [datum(t, "gilt", k) for t in (gilt if isinstance(gilt, list) else [gilt])]
            e["gilt"] = tage[0] if len(tage) == 1 else tage
        aus.append(e)
    ohne = [e for e in aus if "gilt" not in e]
    if len(ohne) > 1:
        raise Ablehnung("schreiben.wert_eintraege.7", k=k)
    tage = [t for e in aus for t in (e["gilt"] if isinstance(e.get("gilt"), list) else [e["gilt"]] if "gilt" in e else [])]
    if len(tage) != len(set(tage)):
        raise Ablehnung("schreiben.wert_eintraege.8", k=k)
    return aus


def gilt_tage(e):
    g = e.get("gilt") if isinstance(e, dict) else None
    return set(g if isinstance(g, list) else [g] if g is not None else [])


def wert_text(e):
    if not isinstance(e, dict):
        return str(e)
    t = str(e.get("wert"))
    if e.get("gilt") is not None:
        g = e["gilt"] if isinstance(e["gilt"], list) else [e["gilt"]]
        t = t + S("schreiben.antwort.wert.am", w1=verbinden([S("schreiben.antwort.datum", w1=texte.DatumKurz(x)) if isinstance(x, datetime.date) else str(x) for x in g]))
    return t


def wert_eintragen(reise_dir, wer, args, heute=None):
    """Einen oder mehrere Werte eines Merkmals an U-…, E-… oder einer Option eintragen (ersetzt den Wert für dieselben Tage,
    der Verlauf steht in der Geschichte des Repos). -> (Titel, Text)."""
    import bauen
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    from ruamel.yaml.scalarstring import DoubleQuotedScalarString
    heute = heute or datetime.date.today()
    ziel = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip()
    if not ZIEL_MUSTER.match(ziel):
        raise Ablehnung("schreiben.wert_eintragen.1")
    k = (text_wert(args, "merkmal", pflicht=True, laenge=40) or "").lower()
    # Leerer Wert entfernt den Wert, immer: auch bei einem abgeschalteten (Stufe aus) oder nicht mehr definierten Merkmal (#474)
    if "wert" in args and args.get("werte") in (None, "", []) and (args.get("wert") is None or str(args.get("wert")).strip() == ""):
        return wert_leeren(reise_dir, ziel, k)
    with tempfile.TemporaryDirectory(prefix="frieda-probe-") as tmp:
        try:
            d = bauen.Bauer(reise_dir, tmp).daten()
        except bauen.BauFehler as e:
            raise Ablehnung("schreiben.bau.nicht_jetzt", meldungen=texte.Satz.verbinden(e.meldungen, " "))
    route = d.get("route") or {}
    # Merkmale, die an dieser Stelle gelten (wie der Generator sie zuordnet), und der heutige Wert
    if ziel.startswith("V-"):
        w = next((w for w in route.get("wahlstellen") or [] if any(o["id"] == ziel for o in w["optionen"])), None)
        if w is None:
            raise Ablehnung("schreiben.ding_finden.4", ziel=ziel)
        krit = w.get("kriterien") or []
        heutige = next(o for o in w["optionen"] if o["id"] == ziel).get("merkmale") or {}
    elif ziel.startswith("O-"):   # Ort mit Art (ADR-0008, Punkt 3)
        u = (route.get("orte") or {}).get(ziel)
        if u is None:
            raise Ablehnung("schreiben.ding_aendern.2", ziel=ziel)
        if not u.get("art"):
            raise Ablehnung("schreiben.wert_eintragen.ort_ohne_art", ziel=ziel)
        krit = (route.get("merkmale") or {}).get(u.get("art")) or []
        heutige = u.get("merkmale") or {}
    elif ziel.startswith(("U-", "A-")):
        u = (route.get("unterkuenfte" if ziel.startswith("U-") else "aufenthalte") or {}).get(ziel)
        if u is None:
            raise Ablehnung("schreiben.wert_eintragen.2" if ziel.startswith("U-") else "schreiben.wert_eintragen.2b", ziel=ziel)
        krit = (route.get("merkmale") or {}).get(u.get("art")) or []
        heutige = u.get("merkmale") or {}
    else:
        st = (route.get("strecken") or {}).get(ziel)
        if st is None:
            raise Ablehnung("schreiben.ding_finden.3", ziel=ziel)
        if isinstance(st.get("art"), list):
            raise Ablehnung("schreiben.wert_eintragen.3", ziel=ziel, w2=' + '.join(st['art']))
        krit = (route.get("merkmale") or {}).get(st.get("art_schluessel") or st.get("art")) or []
        heutige = st.get("merkmale") or {}
    definition = next((x for x in krit if x["id"] == k), None) or next((x for x in krit if k in (x.get("auch") or [])), None)
    if definition is None:
        raise Ablehnung("schreiben.wert_eintragen.4", k=k, ziel=ziel, w3=', '.join(x['id'] for x in krit) or 'keine')
    k = definition["id"]
    if definition.get("auto"):
        raise Ablehnung("schreiben.wert_eintragen.5", w1=definition['name'])
    if (definition.get("stufe") if isinstance(definition.get("stufe"), str) else None) == "aus":
        raise Ablehnung("schreiben.wert_eintragen.6", w1=definition['name'])
    neue = wert_eintraege(args, k, definition, heute)
    # In der Datei: vorhandene Einträge für dieselben Tage ersetzen, andere behalten
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, ziel)
    merkmale = knoten.get("merkmale")
    if merkmale is None:
        merkmale = CommentedMap()
        knoten["merkmale"] = merkmale
    # Einzelform (ein Eintrag ohne Liste) ist gültig und bleibt Lesetoleranz; der Bau liest dieselbe Form (routen.py,
    # v if isinstance(v, list) else [v]). Kein Umstellen: ein nackter Wert hat keine Herkunft, die nachziehen erfinden dürfte (ADR-0001).
    alt = merkmale.get(k)
    alte = list(alt) if isinstance(alt, list) else [alt] if alt is not None else []
    alte = [x if isinstance(x, dict) else {"wert": x} for x in alte]
    ersetzt, bleibt = [], []
    for e in alte:
        tage = gilt_tage(e)
        if any(gilt_tage(n) == tage or (tage and gilt_tage(n) & tage) for n in neue):
            ersetzt.append(e)
        else:
            bleibt.append(e)

    def fliess(e):
        m = CommentedMap()
        for f in ("wert", "gilt", "geprueft", "quelle", "notiz"):
            if f in e:
                m[f] = DoubleQuotedScalarString(e[f]) if isinstance(e[f], str) else e[f]   # wie von Hand geschrieben
        if isinstance(m.get("gilt"), list):
            g = CommentedSeq(m["gilt"])
            g.fa.set_flow_style()
            m["gilt"] = g
        m.fa.set_flow_style()
        return m
    eintraege = bleibt + neue
    if len(eintraege) == 1 and "gilt" not in eintraege[0]:
        merkmale[k] = fliess(eintraege[0])
    else:
        liste = CommentedSeq([fliess(e) for e in eintraege])
        merkmale[k] = liste
    routen_speichern(reise_dir, roh)
    name = definition.get("name") or k
    neu_text = verbinden([wert_text(e) for e in neue], "; ")
    alt_text = verbinden([wert_text(e) for e in ersetzt], "; ")
    titel = S("schreiben.titel.wert_alt", w1=bezeichnung, w2=name, w3=alt_text, w4=neu_text) if alt_text else S("schreiben.titel.wert", w1=bezeichnung, w2=name, w3=neu_text)
    text = (S("schreiben.antwort.wert.kopf", w1=name, w2=bezeichnung, w3=neu_text)
            + (S("schreiben.antwort.wert.vorher", w1=alt_text) if alt_text else "")
            + S("schreiben.antwort.herkunft", w1="; ".join(dict.fromkeys(e["quelle"] for e in neue)))
            + (S("schreiben.antwort.geprueft", w1=", ".join(dict.fromkeys(e["geprueft"].isoformat() for e in neue if "geprueft" in e))) if any("geprueft" in e for e in neue) else "")
            + ".")
    return titel, text


def wert_leeren(reise_dir, ziel, k):
    """Den Wert eines Merkmals an einem Ding oder einer Option entfernen (alle Einträge, auch je Datum; #474). Geht immer, auch
    wenn das Merkmal abgeschaltet oder nicht mehr definiert ist; der alte Wert bleibt in der Geschichte. -> (Titel, Text)."""
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, ziel)
    merkmale = knoten.get("merkmale") or {}
    if k not in merkmale:
        raise Ablehnung("schreiben.wert_leeren.1", k=k, ziel=bezeichnung, w3=", ".join(map(str, merkmale)) or "keine")
    alt = merkmale[k]
    alte = alt if isinstance(alt, list) else [alt]
    alt_text = verbinden([wert_text(e if isinstance(e, dict) else {"wert": e}) for e in alte], "; ")
    del merkmale[k]
    if not merkmale and "merkmale" in knoten:
        del knoten["merkmale"]
    routen_speichern(reise_dir, roh)
    return S("schreiben.titel.wert_geleert", w1=bezeichnung, w2=k), S("schreiben.antwort.wert.geleert", w1=k, w2=bezeichnung, w3=alt_text)


# ---------- Dinge, Wahlstellen, Optionen (plan/routen.yaml) ----------
DING_ARTEN = {"unterkunft": ("U", "unterkuenfte"), "aufenthalt": ("A", "aufenthalte"), "strecke": ("E", "strecken"), "ort": ("O", "orte")}
ID_MUSTER = re.compile(r"^(T-\d+|E-\d+[A-Za-z]?|U-\d+|A-\d+|O-\d+|V-\d+|W-\d+(\.[\w-]+)?|F-\d+|B-\d+|G-\d+)$")


PLAIN_FELDER = {"id", "status", "wer", "art", "wann", "typ", "rolle", "ort", "von", "nach", "frage", "siehe", "bereich", "an", "unterkuenfte", "aufenthalte", "orte",
                "strecken", "folge", "erfordert", "schliesst_aus", "auswahl", "fuer"}
PLAIN_MUSTER = re.compile(r"^[^\W\d_][\w .\-]*$")


def skalar(k, v):
    """Text so schreiben, wie die Dateien es von Hand tun: Namen, IDs und Schlüssel ohne, Fließtext mit Anführungszeichen."""
    from ruamel.yaml.scalarstring import DoubleQuotedScalarString
    if not isinstance(v, str):
        return v
    if k in PLAIN_FELDER and PLAIN_MUSTER.match(v) and v.lower() not in ("yes", "no", "true", "false", "null", "on", "off"):
        return v
    return DoubleQuotedScalarString(v)


def fliess_map(d):
    """dict -> CommentedMap in Fließform; Daten als Datum, Listen in Fließform."""
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    m = CommentedMap()
    for k, v in d.items():
        if isinstance(v, list):
            l = CommentedSeq([skalar(k, x) for x in v])
            l.fa.set_flow_style()
            m[k] = l
        else:
            m[k] = skalar(k, v)
    m.fa.set_flow_style()
    return m


def block_map(d):
    """dict -> CommentedMap in Blockform (Zeile je Feld), Werte wie fliess_map."""
    from ruamel.yaml.comments import CommentedMap
    m = CommentedMap()
    for k, v in fliess_map(d).items():
        m[k] = v
    return m


def id_liste(args, feld, muster, roh, menge=None, pflicht=False):
    """Liste von IDs aus der Anfrage prüfen (Form und Existenz in der Routendatei) -> Liste oder None."""
    v = args.get(feld)
    if v in (None, "", []):
        if pflicht:
            raise Ablehnung("schreiben.text_wert.1", feld=feld)
        return None
    if isinstance(v, str):
        v = [x.strip() for x in v.split(",") if x.strip()]
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise Ablehnung("schreiben.id_liste.1", feld=feld)
    for x in v:
        if not re.fullmatch(muster, x):
            raise Ablehnung("schreiben.id_liste.2", feld=feld, x=x)
        if menge is not None and x not in (roh.get(menge) or {}):
            raise Ablehnung("schreiben.id_liste.3", feld=feld, x=x)
    return v


def merkmale_werte(roh_merkmale, krit, heute, vorgabe=None, herkunft=True):
    """Merkmale eines neuen Dings oder einer Option aus der Anfrage -> {schluessel: Eintrag | [Einträge]} (geprüft wie wert_eintragen)."""
    if roh_merkmale in (None, "", {}):
        return {}
    if not isinstance(roh_merkmale, dict):
        raise Ablehnung("schreiben.klammer.merkmale")
    aus = {}
    for k, v in roh_merkmale.items():
        k = str(k).lower()
        d = next((x for x in krit if x["id"] == k), None) or next((x for x in krit if k in (x.get("auch") or [])), None)
        if d is None:
            raise Ablehnung("schreiben.merkmale_werte.1", k=k, w2=', '.join(x['id'] for x in krit) or 'keine')
        if d.get("auto"):
            raise Ablehnung("schreiben.wert_eintragen.5", w1=d['name'])
        if isinstance(v, list):
            a = {"werte": v}
        elif isinstance(v, dict):
            a = dict(v)
        else:
            a = {"wert": v}
        for f, w in (vorgabe or {}).items():     # quelle und geprueft dürfen einmal für alle Merkmale stehen
            if w not in (None, "") and a.get(f) in (None, ""):
                a[f] = w
        eintraege = wert_eintraege(a, d["id"], d, heute, herkunft)
        aus[d["id"]] = eintraege[0] if len(eintraege) == 1 and "gilt" not in eintraege[0] else eintraege
    return aus


def merkmale_knoten(werte):
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    m = CommentedMap()
    for k, v in werte.items():
        if isinstance(v, list):
            m[k] = CommentedSeq([fliess_map(e) for e in v])
        else:
            m[k] = fliess_map(v)
    return m


# Typisierte Merkmale der Grundformen (ADR-0007, Schritt b): Lage, Zeit und Track stehen als Merkmale mit Typ (und Rolle) am Ding.
# Welche die Grundform fest trägt, legt diese Tabelle fest (Eingabenamen, siehe routen.EINGABE_MERKMALE); die Namen sind
# Schlüssel der Reise, gelesen wird nur nach Typ und Rolle.
GRUNDFORM_MERKMALE = {"ort": ("koordinaten",), "unterkunft": ("adresse", "koordinaten", "buchungslink"),
                      "aufenthalt": ("adresse", "koordinaten", "zeitraum", "buchungslink"), "strecke": ("abfahrt", "ankunft", "gpx")}


def lage_lesen(knoten):
    """Die typisierten Merkmale eines Knotens als feste Felder gelesen (Lesesicht des Bau: adresse, punkt, beginn, ende, ab, an, gpx,
    buchungslink) -> dict. Alte Felder und neue Merkmale ergeben dasselbe."""
    from routen import lage_merkmale_falten
    return lage_merkmale_falten(dict(knoten), "", lambda *a, **k: None)


def lage_merkmal_schreiben(knoten, name, wert, quelle, geprueft=None, notiz=None):
    """Das typisierte Merkmal name (Eingabename aus routen.EINGABE_MERKMALE) am Knoten setzen: ein vorhandenes mit gleichem Typ und
    gleicher Rolle wird ersetzt (gleich unter welchem Namen), sonst entsteht es unter name. Der Wert trägt Typ und Rolle selbst."""
    from routen import EINGABE_MERKMALE
    typ, rolle = EINGABE_MERKMALE[name]
    if isinstance(wert, dict):   # zeitraum: Uhrzeiten in Anführungszeichen, damit YAML sie nicht als Zahl liest
        wert = fliess_map({k: skalar("wert", v) for k, v in wert.items()})
    e = {"typ": typ, **({"rolle": rolle} if rolle else {}), "wert": wert, "quelle": quelle,
         **({"geprueft": geprueft} if geprueft else {}), **({"notiz": notiz} if notiz else {})}
    mk = knoten.get("merkmale")
    if mk is None:
        mk = knoten["merkmale"] = merkmale_knoten({})
    vorhanden = next((k for k, v in mk.items() if isinstance(v, dict) and v.get("typ") == typ and (typ == "zeitraum" or v.get("rolle") == rolle)), None)
    mk[vorhanden or name] = fliess_map(e)
    altes_feld_entfernen(knoten, name)


ALTE_FELDER = {"adresse": ("adresse",), "koordinaten": ("punkt",), "gpx": ("gpx",), "zeitraum": ("beginn", "ende"), "abfahrt": ("ab",),
               "ankunft": ("an",), "buchungslink": ("buchungslink",)}


def altes_feld_entfernen(knoten, name):
    """Das feste Feld, das das Merkmal name ersetzt, vom Knoten nehmen (eine Datei, die noch nicht nachgezogen ist, wird beim ersten
    Schreiben umgestellt). An einer Strecke ist an eine Kennung der Elternbezug und bleibt."""
    from routen import ist_eltern
    for feld in ALTE_FELDER[name]:
        if feld == "an" and ist_eltern(knoten.get("an")):
            continue
        if feld in knoten:
            del knoten[feld]


def lage_merkmal_entfernen(knoten, name):
    """Das typisierte Merkmal name (nach Typ und Rolle gesucht) entfernen -> True, wenn eines da war."""
    from routen import EINGABE_MERKMALE
    typ, rolle = EINGABE_MERKMALE[name]
    mk = knoten.get("merkmale") or {}
    k = next((k for k, v in mk.items() if isinstance(v, dict) and v.get("typ") == typ and (typ == "zeitraum" or v.get("rolle") == rolle)), None)
    alt = any(f in knoten for f in ALTE_FELDER[name])
    altes_feld_entfernen(knoten, name)
    if k is None:
        return alt
    del mk[k]
    if not mk:
        del knoten["merkmale"]
    return True


def felder_zu_merkmalen(knoten, bestand=None):
    """Umstellung (neu.py nachziehen, ADR-0007 Schritt b): die festen Felder adresse, punkt, gpx, beginn/ende, ab, an (Zeit) und
    buchungslink eines Knotens werden typisierte Merkmale mit denselben Werten. Herkunft: die der Aussage, sonst die des Dings,
    sonst „Bestand“. -> Liste der umgestellten Felder (leer: nichts zu tun)."""
    from routen import ist_eltern
    bestand = knoten.get("quelle") or bestand or "Bestand"
    umgestellt = []
    for feld, name in (("adresse", "adresse"), ("punkt", "koordinaten"), ("gpx", "gpx"), ("ab", "abfahrt"), ("an", "ankunft"),
                       ("buchungslink", "buchungslink")):
        v = knoten.get(feld)
        if v is None or (feld == "an" and ist_eltern(v)):
            continue
        if isinstance(v, dict):
            wert, q, g, n = v.get("datei") if feld == "gpx" else v.get("wert"), v.get("quelle") or bestand, v.get("geprueft"), v.get("notiz")
        else:
            wert, q, g, n = v, bestand, None, None
        del knoten[feld]
        lage_merkmal_schreiben(knoten, name, wert, q, g, n)
        umgestellt.append(feld)
    if knoten.get("beginn") is not None:
        b, e = knoten.pop("beginn"), knoten.pop("ende", None)
        lage_merkmal_schreiben(knoten, "zeitraum", {"beginn": b, **({"ende": e} if e else {})}, bestand)
        umgestellt.append("beginn")
        if e:
            umgestellt.append("ende")
    if umgestellt and hasattr(knoten, "fa") and knoten.fa.flow_style():
        knoten.fa.set_block_style()   # ein langer Fließ-Eintrag wird lesbar
    return umgestellt


def zeitraum_setzen(knoten, beginn, ende, quelle):
    """beginn und ende (Uhrzeit HH:MM oder None) als Merkmal zeitraum setzen; ohne beginn entfällt es."""
    if not beginn:
        lage_merkmal_entfernen(knoten, "zeitraum")
        return
    lage_merkmal_schreiben(knoten, "zeitraum", {"beginn": beginn, **({"ende": ende} if ende else {})}, quelle)


def felder_aus_merkmalen(args, was):
    """Die Felder der Grundform (ort, von, nach, zeit, frage, ausserhalb) aus args["merkmale"] nach oben holen -> neue args.
    Ein Feld, das schon oben steht, darf nicht noch einmal in merkmale stehen."""
    from routen import FEST_ALIAS, GRUNDFORM_FELDER
    m = args.get("merkmale")
    if not isinstance(m, dict):
        return args
    oben, rest = {}, {}
    for k, v in m.items():
        n = FEST_ALIAS.get(str(k).lower(), str(k).lower())
        if n in GRUNDFORM_FELDER.get(was, ()):
            if args.get(n) not in (None, "") or n in oben:
                raise Ablehnung("schreiben.fest_wert.doppelt", name=n)
            oben[n] = v
        else:
            rest[k] = v
    return {**args, **oben, "merkmale": rest}


def stufe_von_def(x):
    s = x.get("stufe")
    return (s.get("*") or "empfohlen") if isinstance(s, dict) else (s or "empfohlen")


def merkmale_fest_trennen(args, was, katalog):
    """Aus args["merkmale"] die Merkmale der Grundform (Eingabenamen) herauslösen, die die Art nicht selbst unter diesem Namen
    kennt -> (Rest der Merkmale, {Eingabename: Wert-Angabe}). Ein Name, der nicht zur Grundform gehört, bleibt im Rest."""
    from routen import FEST_ALIAS
    roh = args.get("merkmale")
    if not isinstance(roh, dict):
        return roh, {}
    fest, rest = {}, {}
    for k, v in roh.items():
        n = FEST_ALIAS.get(str(k).lower(), str(k).lower())
        # ein abgeschaltetes Merkmal der Art (Stufe aus) nimmt dem festen Feld den Namen nicht weg (#471: Ankunft als Zeitfeld)
        if n in GRUNDFORM_MERKMALE.get(was, ()) and not any((x["id"] == n or n in (x.get("auch") or [])) and stufe_von_def(x) != "aus" for x in katalog):
            fest[n] = v
        else:
            rest[k] = v
    return rest, fest


def fest_wert(name, v, quelle, geprueft):
    """Angabe eines festen Merkmals aus der Anfrage -> (wert, quelle, geprueft). v: Wert oder {wert, quelle, geprueft}. Prüft den Typ."""
    from routen import EINGABE_MERKMALE, lage_wert_gueltig, ist_link, UHRZEIT
    a = dict(v) if isinstance(v, dict) and "wert" in v else {"wert": v}
    w = a["wert"]
    typ = EINGABE_MERKMALE[name][0]
    if name == "koordinaten":
        w = koordinaten_wert({"koordinaten": w if not isinstance(w, list) else ", ".join(map(str, w))})
    elif name == "zeitraum":
        if isinstance(w, str):
            w = dict(zip(("beginn", "ende"), [x.strip() for x in re.split(r"\s*[-–]\s*", w) if x.strip()]))
        elif isinstance(w, dict):   # englische Schlüssel (start_time, end_time) gelten als Eingabe
            w = {{"start_time": "beginn", "end_time": "ende"}.get(k, k): x for k, x in w.items()}
        if not lage_wert_gueltig("zeitraum", w):
            raise Ablehnung("schreiben.fest_wert.zeitraum")
    elif name in ("abfahrt", "ankunft"):
        w = zeit_wert({"x": w}, "x")
        if not w:
            raise Ablehnung("schreiben.fest_wert.leer", name=name)
    elif name == "buchungslink":
        w = str(w).strip()
        if not ist_link(w):
            raise Ablehnung("schreiben.ding_anlegen.4")
    elif typ == "adresse":
        w = str(w).strip()
        if not lage_wert_gueltig("adresse", w):
            raise Ablehnung("schreiben.fest_wert.leer", name=name)
    q = a.get("quelle") or quelle
    if not q:
        raise Ablehnung("schreiben.text_wert.1", feld="quelle")
    g = a.get("geprueft")
    return w, q, (datum(g, "geprueft", name) if g else geprueft)


def route_stand(reise_dir):
    """Probebau des heutigen Stands -> d["route"] (Arten, Merkmale je Art, Wahlstellen mit Kriterien)."""
    import bauen
    plan_sicherstellen(reise_dir)
    with tempfile.TemporaryDirectory(prefix="frieda-probe-") as tmp:
        try:
            return bauen.Bauer(reise_dir, tmp).daten().get("route") or {}
        except bauen.BauFehler as e:
            raise Ablehnung("schreiben.bau.nicht_jetzt", meldungen=texte.Satz.verbinden(e.meldungen, " "))


def neue_id(reise_dir, kuerzel):
    import neu
    try:
        return neu.naechste_id(Path(reise_dir), kuerzel)
    except neu.Fehler as e:
        raise Ablehnung(e.args[0] if e.args and isinstance(e.args[0], texte.Satz) else str(e))


def uhrzeit_wert(args, feld):
    """beginn oder ende (#77, Kalender): Uhrzeit HH:MM (Ortszeit), leer -> "" (entfernen), fehlt -> None."""
    from routen import UHRZEIT
    v = text_wert(args, feld, laenge=5)
    if v is None or v == "":
        return v
    v = v.strip()
    if re.fullmatch(r"\d:\d\d", v):
        v = "0" + v
    if not UHRZEIT.match(v):
        raise Ablehnung("schreiben.uhrzeit_wert.1", feld=feld)
    return v


def ding_anlegen(reise_dir, wer, args, heute=None):
    """Eine Unterkunft, Strecke oder einen Ort anlegen (neue ID aus ids.yaml, nie neu vergeben). -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    was = (text_wert(args, "was", pflicht=True, laenge=20) or "").lower()
    if was not in DING_ARTEN:
        raise Ablehnung("schreiben.ding_anlegen.1")
    args = felder_aus_merkmalen(args, was)   # ort, von, nach, zeit, frage, ausserhalb dürfen in merkmale stehen (ADR-0007, Schritt c)
    kuerzel, abschnitt = DING_ARTEN[was]
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    arten = route.get("arten") or {}
    quelle = text_wert(args, "quelle", pflicht=True)
    hinweis = text_wert(args, "hinweis")
    d = {}
    fest = {}   # feste Merkmale der Grundform aus der Anfrage: Eingabename -> Wert (ADR-0007, Schritt b)
    if was == "ort":
        d["name"] = text_wert(args, "name_des_dings", laenge=120) or text_wert(args, "titel", pflicht=True, laenge=120)
        if (art := (text_wert(args, "art", laenge=40) or "").lower()):   # freiwillig (ADR-0008, Punkt 3)
            if art not in arten or arten[art].get("grundform") != "ort":
                raise Ablehnung("schreiben.ding_anlegen.ort_art", w1=', '.join(k for k, a in arten.items() if a.get('grundform') == 'ort') or 'keine')
            d["art"] = art
    elif was in ("unterkunft", "aufenthalt"):
        d["name"] = text_wert(args, "name_des_dings", laenge=120) or text_wert(args, "titel", pflicht=True, laenge=120)
        d["ort"] = (id_liste(args, "ort", r"O-\d+", roh, "orte", pflicht=True) or [None])[0]
        art = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
        if art not in arten or arten[art].get("grundform") != "aufenthalt":
            raise Ablehnung("schreiben.ding_anlegen.2", w1=', '.join(k for k, a in arten.items() if a.get('grundform') == 'aufenthalt') or 'keine')
        d["art"] = art    # nur art: (der alte Schlüssel typ wird gelesen, nie mehr geschrieben; docs/ontologie.md)
        if was == "aufenthalt" and (zeit := text_wert(args, "zeit", laenge=80)):
            d["zeit"] = zeit
        if text_wert(args, "buchung", laenge=80):
            raise Ablehnung("schreiben.ding_anlegen.3")
        if (link := text_wert(args, "buchungslink", laenge=600)):
            if not link.startswith(("http://", "https://")):
                raise Ablehnung("schreiben.ding_anlegen.4")
            fest["buchungslink"] = link
        if (frage := text_wert(args, "frage", laenge=10)):
            if not re.fullmatch(r"F-\d+", frage):
                raise Ablehnung("schreiben.ding_anlegen.5")
            d["frage"] = frage
    else:
        d["titel"] = text_wert(args, "titel", pflicht=True, laenge=200)
        d["von"] = (id_liste(args, "von", r"O-\d+", roh, "orte", pflicht=True) or [None])[0]
        d["nach"] = (id_liste(args, "nach", r"O-\d+", roh, "orte", pflicht=True) or [None])[0]
        art = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
        if art not in arten or arten[art].get("grundform") != "bewegung":
            raise Ablehnung("schreiben.ding_anlegen.6", w1=', '.join(k for k, a in arten.items() if a.get('grundform') == 'bewegung') or 'keine')
        d["art"] = art
        if args.get("kennzahlen") is not None:   # Kennzahlen an der Strecke (#269); die Herkunft der Strecke gilt für sie
            d["kennzahlen"] = fliess_map(kennzahlen_wert(args, fahrt=ist_fahrt(arten, art)))
        if args.get("abschnitte") not in (None, "", []):   # Zwischenstopps (#509)
            d["abschnitte"] = abschnitte_wert(args, roh, d["nach"], fahrt=ist_fahrt(arten, art))
        for k, name in (("ab", "abfahrt"), ("an", "ankunft")):   # Zeitpunkte (Issue #135): HH:MM oder JJJJ-MM-TTTHH:MM+HH:MM
            if k == "an" and ist_eltern_wert(args.get("an")):   # Elternbezug statt Ankunftszeit (ADR-0007)
                continue
            if (z := zeit_wert(args, k)):
                fest[name] = z
    if was == "aufenthalt":   # Uhrzeit für den Kalender (#77), als Merkmal zeitraum
        zr = {feld: u for feld in ("beginn", "ende") if (u := uhrzeit_wert(args, feld))}
        if zr.get("ende") and not zr.get("beginn"):
            raise Ablehnung("schreiben.ding_anlegen.7")
        if zr:
            fest["zeitraum"] = zr
    if (eltern := text_wert(args, "an", laenge=20)) and (was != "strecke" or ist_eltern_wert(eltern)):   # Elternbezug (ADR-0007)
        eltern_wert_pruefen(reise_dir, roh, None, eltern, was)
        d["an"] = eltern
    if was == "ort" and bool_wert(args, "ausserhalb"):
        d["ausserhalb"] = True   # Ort der An- und Abreise außerhalb der Reisegegend (Issue #135)
    if hinweis:
        d["hinweis"] = hinweis
    d["quelle"] = quelle
    # Lage gleich beim Anlegen (Epic #225, K2/K3): Koordinaten (Ort, Unterkunft, Aufenthalt), Adresse (nicht beim Ort)
    punkt, adresse = koordinaten_wert(args), text_wert(args, "adresse", laenge=300)
    if was == "strecke" and (punkt or adresse):
        raise Ablehnung("schreiben.ding_anlegen.lage_strecke")
    if was == "ort" and adresse:
        raise Ablehnung("schreiben.lage_eintragen.ort_adresse")
    g = datum(args["geprueft"], "geprueft", "Lage") if args.get("geprueft") else heute
    if adresse:
        fest["adresse"] = adresse
    if punkt:
        fest["koordinaten"] = punkt
    katalog = (route.get("merkmale") or {}).get(d.get("art")) or []
    rest_merkmale, aus_merkmalen = merkmale_fest_trennen(args, was, katalog) if was != "ort" or d.get("art") else (None, {})
    if was == "ort" and not d.get("art") and isinstance(args.get("merkmale"), dict):
        aus_merkmalen = {str(k).lower(): v for k, v in args["merkmale"].items() if str(k).lower() in GRUNDFORM_MERKMALE["ort"]}
    for name, v in aus_merkmalen.items():
        if name in fest:
            raise Ablehnung("schreiben.fest_wert.doppelt", name=name)
        fest[name] = v
    erlaubt = [n for n in GRUNDFORM_MERKMALE[was] if n != "gpx"]   # ein Track kommt mit item_update an eine vorhandene Strecke
    for name in fest:
        if name not in erlaubt:
            raise Ablehnung("schreiben.fest_wert.nicht_fuer", name=name, was=S("schreiben.ding_wort." + was), w1=", ".join(erlaubt))
    festwerte = {name: fest_wert(name, v, quelle, g) for name, v in fest.items()}
    werte = merkmale_werte(rest_merkmale, katalog, heute,
                           {"quelle": quelle, "geprueft": args.get("geprueft")}) if was != "ort" or d.get("art") else {}
    did = neue_id(reise_dir, kuerzel)
    knoten = fliess_map(d) if was not in ("unterkunft", "aufenthalt") else block_map(d)
    if festwerte and was in ("ort", "strecke"):
        knoten = block_map(d)
    if werte:
        if was in ("strecke", "ort"):
            knoten = block_map(d)
        knoten["merkmale"] = merkmale_knoten(werte)
    for name, (w, q, gp) in festwerte.items():
        lage_merkmal_schreiben(knoten, name, w, q, gp if name in ("adresse", "koordinaten") else None)
    lage = {"punkt": {"wert": festwerte["koordinaten"][0]}} if "koordinaten" in festwerte else {}
    roh.setdefault(abschnitt, type(roh)())
    roh[abschnitt][did] = knoten
    name = d.get("name") or d.get("titel")
    titel = S("schreiben.titel.ding_angelegt", w1=did, w2=name, w3=S("schreiben.ding_wort." + was))
    text = (S("schreiben.antwort.ding." + was, w1=did, w2=name)
            + (S("schreiben.antwort.ding.in", w1=route.get("orte", {}).get(d["ort"], {}).get("name", d["ort"])) if was in ("unterkunft", "aufenthalt") else "")
            + (S("schreiben.antwort.ding.art", w1=d["art"]) if d.get("art") else "") + (S("schreiben.antwort.ding.merkmale", w1=", ".join(werte)) if werte else "")
            + S("schreiben.antwort.ding.herkunft_punkt", w1=quelle)
            + (S("schreiben.antwort.ding.alternative") if was == "unterkunft" else "")
            + (S("schreiben.antwort.ding.an_einen_tag") if was == "aufenthalt" and not d.get("an") else "")   # mit an: hat er seinen Platz (#432)
            + (S("schreiben.antwort.ding.mit_koordinaten", w1=", ".join(map(str, lage["punkt"]["wert"]))) if "punkt" in lage
               else S("schreiben.antwort.ding.ohne_koordinaten") if was != "strecke" else ""))
    routen_speichern(reise_dir, roh)
    return titel, text


AENDERBAR = {"unterkunft": ("name", "ort", "art", "hinweis", "quelle", "buchungslink", "frage", "an"),
             "aufenthalt": ("name", "ort", "art", "zeit", "beginn", "ende", "hinweis", "quelle", "buchungslink", "frage", "an"),
             "strecke": ("titel", "von", "nach", "art", "ab", "an", "hinweis", "quelle", "kennzahlen", "abschnitte"), "ort": ("name", "art", "hinweis", "quelle", "ausserhalb", "an")}


def kennzahlen_wert(args, alt=None, herkunft=None, fahrt=False):
    """Kennzahlen einer Strecke (#269): Kennung -> Wert (routen.KENNZAHLEN: gehzeit und fahrzeit als Text h:mm, aufstieg, abstieg in
    m, laenge in km; eigene Namen der Reise erlaubt). Zahlen bleiben Zahlen; ein leerer Wert entfernt die Kennzahl. alt: die
    bisherigen. Herkunft je Wert (#508): ein Wert darf {wert, quelle, geprueft} sein; herkunft ({quelle, geprueft}) gilt für die neuen
    Werte ohne eigene, dann steht der Wert mit seiner Herkunft, sonst gilt die der Strecke. fahrt: die Strecke ist eine Fahrt (Art
    nicht summiert), ihre Zeit heißt fahrzeit, auch wenn gehzeit kam. -> dict"""
    from schnittstelle import KENNZAHL_ALIAS
    from routen import ZEIT_KENNZAHLEN
    from neu import kennung_der_kennzahl   # Katalognamen („Gehzeit“, „Aufstieg (Hm)“) -> Kennung, nur ganze Namen (F105)
    k = args.get("kennzahlen")
    if not isinstance(k, dict) or not k:
        raise Ablehnung("schreiben.kennzahlen.form")
    neu = dict(alt or {})
    for n, v in k.items():
        n = str(n).strip()
        n = KENNZAHL_ALIAS.get(n.lower()) or kennung_der_kennzahl(n)   # Namen der Schnittstelle und des Katalogs -> Kennung
        if fahrt and n == "gehzeit":   # eine Fahrt hat keine Gehzeit (#508)
            n = "fahrzeit"
        h = dict(herkunft or {})
        if isinstance(v, dict):   # {wert, quelle, geprueft}: die eigene Herkunft des Werts
            if not set(v) <= {"wert", "quelle", "geprueft"} or "wert" not in v:
                raise Ablehnung("schreiben.kennzahlen.form")
            h.update({x: v[x] for x in ("quelle", "geprueft") if v.get(x) not in (None, "")})
            v = v["wert"]
        if not n or len(n) > 40 or isinstance(v, bool) or not isinstance(v, (str, int, float)) or len(str(v)) > 80 \
                or (n in ZEIT_KENNZAHLEN and not isinstance(v, str)):   # Zeiten sind Text h:mm
            raise Ablehnung("schreiben.kennzahlen.form")
        if isinstance(v, str) and not v.strip():
            neu.pop(n, None)
            continue
        v = v.strip() if isinstance(v, str) else v
        if h.get("quelle"):
            e = {"wert": v, "quelle": " ".join(str(h["quelle"]).split())[:600]}
            if h.get("geprueft"):
                e["geprueft"] = h["geprueft"] if isinstance(h["geprueft"], datetime.date) else datum(h["geprueft"], "geprueft", n)
            neu[n] = fliess_map(e)
        else:
            neu[n] = v
    return neu


ABSCHNITT_ALIAS = {"to_place": "nach", "after": "nach", "figures": "kennzahlen", "stop": "halt"}
HALT_ALIAS = {"purpose": "zweck", "duration": "dauer"}


def abschnitte_wert(args, roh, nach, alt=None, herkunft=None, fahrt=False):
    """Zwischenstopps einer Strecke (#509): Liste von Abschnitten in Reihenfolge, je {nach: O-…, kennzahlen, halt: {zweck,
    dauer h:mm}}; der letzte endet am Ziel der Strecke (ohne nach: dort) und hat keinen Halt. Ersetzt die bisherige Liste; eine
    Kennzahl, die im Abschnitt mit demselben Ziel schon so stand, behält ihre Herkunft. Leere Liste: keine Abschnitte. -> Liste oder None"""
    from routen import kz_wert
    liste = args.get("abschnitte")
    if liste in ("", []):
        return None
    if not isinstance(liste, list) or len(liste) < 2 or len(liste) > 30 or not all(isinstance(a, dict) for a in liste):
        raise Ablehnung("schreiben.abschnitte.form")
    alt_je = {a.get("nach"): a for a in alt or [] if isinstance(a, dict)}
    orte = roh.get("orte") or {}
    aus = []
    for i, a in enumerate(liste):
        a = {ABSCHNITT_ALIAS.get(str(k), str(k)): v for k, v in a.items()}
        if not set(a) <= {"nach", "kennzahlen", "halt"}:
            raise Ablehnung("schreiben.abschnitte.form")
        letzter = i == len(liste) - 1
        ziel = str(a.get("nach") or (nach if letzter else "")).strip()
        if not ziel or ziel not in orte:
            raise Ablehnung("schreiben.abschnitte.ort", w1=ziel or "–")
        if letzter and ziel != nach:
            raise Ablehnung("schreiben.abschnitte.ende", w1=ziel, w2=nach)
        e = {"nach": ziel}
        if a.get("kennzahlen") not in (None, {}, ""):
            vorher = dict((alt_je.get(ziel) or {}).get("kennzahlen") or {})
            k = kennzahlen_wert({"kennzahlen": a["kennzahlen"]}, None, herkunft, fahrt)
            k = {n: (vorher[n] if n in vorher and kz_wert(vorher[n]) == kz_wert(v) else v) for n, v in k.items()}
            if k:
                e["kennzahlen"] = fliess_map(k)
        h = a.get("halt")
        if h not in (None, {}, ""):
            h = {HALT_ALIAS.get(str(k), str(k)): v for k, v in h.items()} if isinstance(h, dict) else None
            if letzter or not h or not set(h) <= {"zweck", "dauer"}:
                raise Ablehnung("schreiben.abschnitte.halt", w1=ziel)
            halt = {}
            if str(h.get("zweck") or "").strip():
                halt["zweck"] = " ".join(str(h["zweck"]).split())[:80]
            if str(h.get("dauer") or "").strip():
                d = str(h["dauer"]).strip()
                if not re.fullmatch(r"\d{1,2}:\d{2}", d):
                    raise Ablehnung("schreiben.abschnitte.halt", w1=ziel)
                halt["dauer"] = skalar("dauer", d)
            e["halt"] = fliess_map(halt)
        aus.append(fliess_map(e))
    return aus


def ist_fahrt(arten, art):
    """Ist eine Strecke dieser Art eine Fahrt (ihre Art zählt nicht in die Kennzahlen, Merkmal summiert)? Ohne Art: nein."""
    from routen import KOMBINIERT
    if art in (None, "", []):
        return False
    a = arten.get(KOMBINIERT if isinstance(art, list) else str(art))
    return a is not None and not a.get("summiert")


def ist_eltern_wert(wert):
    """Ist der Wert von an ein Elternbezug (Kennung oder „reise“) und keine Uhrzeit? (ADR-0007; bei einer Strecke war an die Ankunftszeit)"""
    from routen import ist_eltern
    return ist_eltern(str(wert).strip()) if wert is not None else False


def wissen_ids(reise_dir):
    """Alle Kennungen von Abschnitten des Wissens (W-…) und Etappen der Reise aus reise.json."""
    import json
    try:
        cfg = json.loads((Path(reise_dir) / "reise.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {wid for titel_zu in (cfg.get("abschnitte") or {}).values() for wid, _g in titel_zu.values()}


def eltern_wert_pruefen(reise_dir, roh, did, wert, was=None):
    """Ist wert ein zulässiger Elternbezug für did (bei einem neuen Ding None, dann sagt was die Grundform)? Sonst Ablehnung.
    Ein Tag geht über tag_aendern; ein Ort liegt nur in einem Ort (ADR-0008, Punkt 2)."""
    from routen import ist, ELTERN_ARTEN, REISE_ALS_ELTERN
    if not ist_eltern_wert(wert):
        raise Ablehnung("schreiben.ding_aendern.an_form")
    if wert == did:
        raise Ablehnung("schreiben.ding_aendern.an_selbst")
    art = next((a for a in ELTERN_ARTEN if ist(a, wert)), None)
    if (was == "ort" or (did and ist("ort", did))) and art != "ort":
        raise Ablehnung("schreiben.ding_aendern.an_ort", x=wert)
    if art == "tag":
        raise Ablehnung("schreiben.ding_aendern.an_tag", tid=wert)
    if wert == REISE_ALS_ELTERN:
        return
    menge = {"ort": "orte", "strecke": "strecken", "aufenthalt": "aufenthalte", "unterkunft": "unterkuenfte"}.get(art)
    if wert not in (roh.get(menge) or {}) and wert not in wissen_ids(reise_dir):
        raise Ablehnung("schreiben.ding_aendern.an_unbekannt", x=wert)
    # Kreis: führt die Kette der Eltern von wert zurück zu did?
    gruppen = [roh.get(g) or {} for g in ("orte", "strecken", "unterkuenfte", "aufenthalte")]
    x, schritte = wert, 0
    while x and schritte < 20:
        if x == did:
            raise Ablehnung("schreiben.ding_aendern.an_kreis", ziel=did)
        n = next((g[x] for g in gruppen if x in g), None)
        x = n.get("an") if isinstance(n, dict) and ist_eltern_wert(n.get("an")) else None
        schritte += 1


def eltern_aendern(reise_dir, roh, did, was, knoten, wert, geaendert):
    """Elternbezug (an:, ADR-0007) eines Dings setzen, ändern oder entfernen (leer = Vorgabe der Grundform). Ein Aufenthalt mit Tag,
    der an ein anderes Ding gehängt wird, wird von seinen Tagen gelöst (#235). Hängt Einträge an geaendert."""
    alt = knoten.get("an") if ist_eltern_wert(knoten.get("an")) else None
    if was == "strecke" and knoten.get("an") is not None and alt is None:
        raise Ablehnung("schreiben.ding_aendern.an_zeit", ziel=did)
    wert = str(wert).strip()
    if not wert:
        if alt is not None:
            geaendert.append(S("schreiben.antwort.ding.entfernt", w1="an", w2=alt))
            del knoten["an"]
        return
    eltern_wert_pruefen(reise_dir, roh, did, wert)
    if alt == wert:
        return
    knoten["an"] = skalar("an", wert)
    geaendert.append(S("schreiben.antwort.ding.wechsel", w1="an", w2=alt, w3=wert) if alt is not None else S("schreiben.antwort.ding.neu", w1="an", w2=wert))
    if was == "aufenthalt":
        for tid_, t in (roh.get("tage") or {}).items():
            liste = list(t.get("aufenthalte") or [])
            if did in liste:
                liste.remove(did)
                if liste:
                    t["aufenthalte"] = fliess_map({"aufenthalte": liste})["aufenthalte"]
                else:
                    t.pop("aufenthalte", None)
                geaendert.append(S("schreiben.antwort.ding.vom_tag_geloest", w1=tid_))


def zeit_wert(args, feld):
    """Zeitpunkt einer Bewegung aus der Anfrage -> Text in gültiger Form, "" (leer: entfernen) oder None (fehlt)."""
    from routen import zeitpunkt
    v = args.get(feld)
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return ""
    if zeitpunkt(v) is None:
        raise Ablehnung("schreiben.zeit_wert.1", feld=feld)
    return v


def ding_aendern(reise_dir, wer, args, heute=None):
    """item_update (ADR-0007, Schritt c): Felder und Merkmale eines Dings ändern, der Elternbezug an, die Lage, Zeiten, der Track und
    die Merkmale der Art in einem Werkzeug. Verteilt auf die Teile: Felder (_ding_aendern_felder), Lage (lage_eintragen), Track
    (track_anhaengen) und je Merkmal der Art wert_eintragen. Die Gestalten der früheren Werkzeuge wert_eintragen (merkmal, wert),
    lage_eintragen (adresse, koordinaten) und track_anhaengen (gpx) gelten weiter. -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    ziel = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip()
    if args.get("merkmal") is not None and (args.get("wert") is not None or args.get("werte") is not None):   # Gestalt von wert_eintragen
        return wert_eintragen(reise_dir, wer, args, heute)
    if isinstance(args.get("gpx"), str) and re.fullmatch(r"E-\d+[A-Za-z]?", ziel):   # Gestalt von track_anhaengen
        return track_anhaengen(reise_dir, wer, args, heute)
    ist_option = bool(re.fullmatch(r"V-\d+\.[a-z]+", ziel))
    was = next((w for w, (k, _) in DING_ARTEN.items() if ziel.startswith(k + "-")), None)
    merkmale = args.get("merkmale")
    if merkmale in (None, "", {}) and not ist_option and not any(args.get(k) is not None for k in ("adresse", "koordinaten")):
        return _ding_aendern_felder(reise_dir, wer, args, heute)
    if merkmale not in (None, "", {}) and not isinstance(merkmale, dict):
        raise Ablehnung("schreiben.klammer.merkmale")
    if was is None and not ist_option:
        raise Ablehnung("schreiben.ding_aendern.1")
    merkmale = dict(merkmale or {})
    args = {**args, "merkmale": merkmale}
    teile = []   # (Titel, Text)
    if was:
        args = felder_aus_merkmalen(args, was)
        merkmale = args["merkmale"]
        route = route_stand(reise_dir)
        roh = routen_laden(reise_dir)
        knoten, _ = ding_finden(roh, ziel) if was != "ort" else ((roh.get("orte") or {}).get(ziel), ziel)
        if knoten is None:
            raise Ablehnung("schreiben.ding_aendern.2", ziel=ziel)
        art = knoten.get("art")
        katalog = (route.get("merkmale") or {}).get(art) or []
        merkmale, fest = merkmale_fest_trennen({"merkmale": merkmale}, was if was != "strecke" else "strecke", katalog)
        merkmale = merkmale or {}
        # feste Merkmale der Grundform -> die Parameter der Teile
        felder = {k: v for k, v in args.items() if k not in ("merkmale", "adresse", "koordinaten", "gpx", "grund", "geprueft")}
        lage = {k: args[k] for k in ("adresse", "koordinaten") if args.get(k) is not None}
        for name, v in fest.items():
            if name in ("adresse", "koordinaten"):
                if name in lage:
                    raise Ablehnung("schreiben.fest_wert.doppelt", name=name)
                lage[name] = v["wert"] if isinstance(v, dict) and "wert" in v else v
            elif name == "zeitraum":
                zr = fest_wert("zeitraum", v, "x", None)[0]
                felder["beginn"], felder["ende"] = zr["beginn"], zr.get("ende", "")
            elif name == "abfahrt":
                felder["ab"] = fest_wert("abfahrt", v, "x", None)[0]
            elif name == "ankunft":
                if ist_eltern_wert(felder.get("an")):
                    raise Ablehnung("schreiben.fest_wert.doppelt", name="ankunft")
                felder["an"] = fest_wert("ankunft", v, "x", None)[0]
            elif name == "buchungslink":
                felder["buchungslink"] = fest_wert("buchungslink", v, "x", None)[0]
            elif name == "gpx":
                gpx_text = v
        if "merkmal" in felder:
            felder.pop("merkmal")
        felder.update({k: args[k] for k in ("geprueft",) if args.get(k) is not None})
        brauchbar = {k for k in felder if k not in ("ziel", "vorname", "name", "grund", "quelle", "geprueft") and felder[k] is not None}
        nur_quelle = felder.get("quelle") is not None and not (brauchbar or lage or fest.get("gpx") is not None or merkmale)
        if brauchbar or nur_quelle:   # quelle gehört den neuen Angaben, die des Dings ändert sie nur allein (#508)
            teile.append(_ding_aendern_felder(reise_dir, wer, felder, heute))
        if lage:
            teile.append(lage_eintragen(reise_dir, wer, {**{k: args[k] for k in ("quelle", "geprueft", "grund") if args.get(k) is not None},
                                                         "ziel": ziel, **lage}, heute))
        if fest.get("gpx") is not None:
            teile.append(track_anhaengen(reise_dir, wer, {"ziel": ziel, "gpx": gpx_text, "quelle": args.get("quelle"), "grund": args.get("grund")}, heute))
    for k, v in merkmale.items():   # Merkmale der Art: je eines wie wert_eintragen
        a = {"ziel": ziel, "merkmal": str(k), **{x: args[x] for x in ("quelle", "geprueft", "grund") if args.get(x) is not None}}
        if isinstance(v, list):
            a["werte"] = v
        elif isinstance(v, dict):
            a.update(v)
        else:
            a["wert"] = v
        teile.append(wert_eintragen(reise_dir, wer, a, heute))
    if not teile:
        raise Ablehnung("schreiben.ding_aendern.6", bezeichnung=ziel, w2=', '.join(AENDERBAR.get(was or "", ())))
    if len(teile) == 1:
        return teile[0]
    return teile[0][0], texte.Satz.verbinden([t for _, t in teile], " ")


def _ding_aendern_felder(reise_dir, wer, args, heute=None):
    """Felder einer Unterkunft, Strecke oder eines Orts ändern (Name, Ort, Art, Hinweis, Elternbezug, Zeiten …). -> (Titel, Text)."""
    from reise import darf
    ziel = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip()
    was = next((w for w, (k, _) in DING_ARTEN.items() if ziel.startswith(k + "-")), None)
    if was is None or not ID_MUSTER.match(ziel):
        raise Ablehnung("schreiben.ding_aendern.1")
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, ziel) if was != "ort" else ((roh.get("orte") or {}).get(ziel), ziel)
    if knoten is None:
        raise Ablehnung("schreiben.ding_aendern.2", ziel=ziel)
    if was == "ort":
        bezeichnung = f"{ziel} {knoten.get('name', '')}".strip()
    arten = route.get("arten") or {}
    if text_wert(args, "buchung", laenge=80) is not None:
        raise Ablehnung("schreiben.ding_aendern.3")
    if args.get("neuer_name") is not None:   # der Konnektor nimmt name als Vornamen der sprechenden Person; der neue Name heißt dort neuer_name
        args = {**args, "name": args["neuer_name"]}
    geaendert = []
    zeit_neu = {}
    # quelle ändert die Herkunft des Dings nur, wenn sie allein kommt; mit anderen Angaben gehört sie diesen (#508)
    quelle_neu = text_wert(args, "quelle", laenge=600)
    nur_quelle = not any(args.get(f) is not None for f in AENDERBAR[was] if f != "quelle")
    quelle_fest = quelle_neu or knoten.get("quelle") or S("schreiben.quelle_gespraech", w1=wer.get("name", ""))
    eltern = args.get("an") if args.get("an") is not None and (was != "strecke" or ist_eltern_wert(args.get("an"))) else None
    if eltern is not None:   # Elternbezug (ADR-0007); an einer Strecke bleibt eine Uhrzeit die Ankunftszeit
        eltern_aendern(reise_dir, roh, ziel, was, knoten, eltern, geaendert)
    for feld in AENDERBAR[was]:
        if feld not in args or args.get(feld) is None:
            continue
        if feld == "an" and eltern is not None:
            continue
        if feld == "quelle" and not nur_quelle:
            continue
        if feld == "name":
            v = text_wert(args, "name", pflicht=True, laenge=120)
        elif feld in ("ort", "von", "nach"):
            v = (id_liste(args, feld, r"O-\d+", roh, "orte", pflicht=True) or [None])[0]
        elif feld == "art":
            if not darf(wer["rolle"], "organisator"):
                raise Ablehnung("schreiben.ding_aendern.4")
            v = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
            g = "aufenthalt" if was in ("unterkunft", "aufenthalt") else "ort" if was == "ort" else "bewegung"
            if v not in arten or arten[v].get("grundform") != g:
                raise Ablehnung("schreiben.ding_aendern.5", w1=S("schreiben.grundform_art." + g), w2=', '.join(k for k, a in arten.items() if a.get('grundform') == g) or 'keine')
        elif feld == "buchungslink":
            v = text_wert(args, feld, laenge=600) or ""
            if v and not v.startswith(("http://", "https://")):
                raise Ablehnung("schreiben.ding_anlegen.4")
        elif feld == "frage":
            v = text_wert(args, feld, laenge=10) or ""
            if v and not re.fullmatch(r"F-\d+", v):
                raise Ablehnung("schreiben.ding_anlegen.5")
        elif feld in ("beginn", "ende"):
            v = uhrzeit_wert(args, feld) or ""
        elif feld in ("ab", "an"):
            v = zeit_wert(args, feld)
        elif feld == "kennzahlen":   # Kennung -> Wert an der Strecke (#269), mit den bisherigen zusammengeführt
            from routen import kz_wert
            alt = dict(knoten.get("kennzahlen") or {})
            herkunft = {"quelle": quelle_neu, "geprueft": args.get("geprueft")} if quelle_neu else None
            v = kennzahlen_wert(args, alt, herkunft, ist_fahrt(arten, knoten.get("art")))
            if v != alt:
                zeile = lambda d: ", ".join(f"{n} {kz_wert(w)}" for n, w in d.items()) or "–"
                geaendert.append(S("schreiben.antwort.ding.wechsel", w1=feld, w2=zeile(alt), w3=zeile(v)))
                if v:
                    knoten["kennzahlen"] = fliess_map(v)
                else:
                    del knoten["kennzahlen"]
            continue
        elif feld == "abschnitte":   # Zwischenstopps (#509): die ganze Liste in Reihenfolge
            from routen import kz_wert
            alt = list(knoten.get("abschnitte") or [])
            herkunft = {"quelle": quelle_neu, "geprueft": args.get("geprueft")} if quelle_neu else None
            v = abschnitte_wert(args, roh, args.get("nach") or knoten.get("nach"), alt, herkunft, ist_fahrt(arten, knoten.get("art")))
            zeile = lambda ab: " → ".join(str(a.get("nach")) + (" (" + ", ".join(f"{n} {kz_wert(w)}" for n, w in a["kennzahlen"].items()) + ")"
                                                                  if a.get("kennzahlen") else "") for a in ab or []) or "–"
            if (v or []) != alt:
                geaendert.append(S("schreiben.antwort.ding.wechsel", w1=S("schreiben.abschnitte.name"), w2=zeile(alt), w3=zeile(v)))
                if v:
                    knoten["abschnitte"] = v
                else:
                    del knoten["abschnitte"]
            continue
        elif feld == "ausserhalb":
            v = bool_wert(args, feld)
            if v is False and feld in knoten:
                geaendert.append(S("schreiben.antwort.ding.ausserhalb_entfernt"))
                del knoten[feld]
                continue
            if not v or knoten.get(feld):
                continue
            geaendert.append(S("schreiben.antwort.ding.ausserhalb"))
            knoten[feld] = True
            continue
        else:
            v = text_wert(args, feld, laenge=600 if feld == "quelle" else MAX_TEXT) or ""
        if feld in ("beginn", "ende"):   # Merkmal zeitraum (ADR-0007): beide zusammen am Schluss
            zeit_neu[feld] = v
            continue
        if feld in ("ab", "an", "buchungslink"):   # typisierte Merkmale abfahrt, ankunft, buchungslink
            name = {"ab": "abfahrt", "an": "ankunft"}.get(feld, feld)
            alt = lage_lesen(knoten).get(feld)
            if v == "":
                if lage_merkmal_entfernen(knoten, name) and alt is not None:
                    geaendert.append(S("schreiben.antwort.ding.entfernt", w1=feld, w2=alt))
            elif str(alt) != str(v):
                lage_merkmal_schreiben(knoten, name, v, quelle_fest)
                geaendert.append(S("schreiben.antwort.ding.wechsel", w1=feld, w2=alt, w3=v) if alt is not None else S("schreiben.antwort.ding.neu", w1=feld, w2=v))
            continue
        alt = knoten.get(feld)
        if v == "" and feld in ("hinweis", "buchungslink", "frage", "zeit", "beginn", "ende", "ab", "an"):
            if feld in knoten:
                geaendert.append(S("schreiben.antwort.ding.entfernt", w1=feld, w2=alt))
                del knoten[feld]
            continue
        if str(alt) == str(v):
            continue
        geaendert.append(S("schreiben.antwort.ding.wechsel", w1=feld, w2=alt, w3=v) if alt is not None else S("schreiben.antwort.ding.neu", w1=feld, w2=v))
        knoten[feld] = skalar(feld, v)
        if feld == "art" and "typ" in knoten:   # räumt einen früheren typ: auf, sobald art: steht
            del knoten["typ"]
    if zeit_neu:   # beginn und ende zusammen als Merkmal zeitraum
        gelesen = lage_lesen(knoten)
        b, e = (zeit_neu.get(k, gelesen.get(k)) or None for k in ("beginn", "ende"))
        if e and not b:
            raise Ablehnung("schreiben.ding_anlegen.7")
        for k in ("beginn", "ende"):
            alt, neu_ = gelesen.get(k), (b, e)[k == "ende"]
            if k in zeit_neu and alt != neu_:
                geaendert.append(S("schreiben.antwort.ding.wechsel", w1=k, w2=alt, w3=neu_) if alt and neu_ else
                                 S("schreiben.antwort.ding.neu", w1=k, w2=neu_) if neu_ else S("schreiben.antwort.ding.entfernt", w1=k, w2=alt))
        if any(k in zeit_neu and gelesen.get(k) != (b, e)[k == "ende"] for k in ("beginn", "ende")):
            zeitraum_setzen(knoten, b, e, quelle_fest)
    if not geaendert:
        raise Ablehnung("schreiben.ding_aendern.6", bezeichnung=bezeichnung, w2=', '.join(AENDERBAR[was]))
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    titel = S("schreiben.titel.geaendert", w1=bezeichnung, w2=kurz_namen(geaendert))
    text = f"{bezeichnung}: " + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund else "")
    return titel, text


def koordinaten_wert(args):
    """„koordinaten“ aus der Anfrage („Breite, Länge“ in Grad) -> [Breite, Länge] oder None."""
    if args.get("koordinaten") in (None, ""):
        return None
    roh = args["koordinaten"]
    try:
        punkt = [round(float(x), 6) for x in (roh if isinstance(roh, list) else re.split(r"[,;\s]+", str(roh).strip())) if x != ""]
    except ValueError:
        punkt = []
    if len(punkt) != 2 or not (-90 <= punkt[0] <= 90 and -180 <= punkt[1] <= 180):
        raise Ablehnung("schreiben.lage_eintragen.3")
    return punkt


def lage_eintragen(reise_dir, wer, args, heute=None):
    """Lage einer Unterkunft oder eines Aufenthalts (ADR-0004): Adresse und/oder Koordinaten, je mit Herkunft (quelle) und Prüfdatum;
    bei einem Ort nur Koordinaten (Position auf der Karte, Epic #225). -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    ziel = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip()
    if not re.fullmatch(r"(U|A|O)-\d+", ziel):
        raise Ablehnung("schreiben.lage_eintragen.1")
    roh = routen_laden(reise_dir)
    if ziel.startswith("O-"):
        knoten, bezeichnung = (roh.get("orte") or {}).get(ziel), ziel
        if knoten is not None:
            bezeichnung = f"{ziel} {knoten.get('name', '')}".strip()
    else:
        knoten, bezeichnung = ding_finden(roh, ziel)
    if knoten is None:
        raise Ablehnung("schreiben.ding_aendern.2", ziel=ziel)
    quelle = text_wert(args, "quelle", pflicht=True, laenge=600)
    g = datum(args["geprueft"], "geprueft", "Lage") if args.get("geprueft") else heute
    if g > heute:
        raise Ablehnung("schreiben.lage_eintragen.2")
    adresse = text_wert(args, "adresse", laenge=300)
    if adresse and ziel.startswith("O-"):
        raise Ablehnung("schreiben.lage_eintragen.ort_adresse")
    punkt = koordinaten_wert(args)
    gelesen = lage_lesen(knoten)
    # Leerer Text nimmt die Koordinaten heraus (PO 4.11.2026): das Ding bleibt, steht aber nicht mehr auf der Karte
    weg = args.get("koordinaten") == "" and isinstance(gelesen.get("punkt"), dict)
    if not adresse and not punkt and not weg:
        raise Ablehnung("schreiben.lage_eintragen.4")
    geaendert = []
    if weg:
        alt = gelesen["punkt"].get("wert")
        mk = knoten.get("merkmale") or {}
        for k in [k for k, v in mk.items() if isinstance(v, dict) and v.get("typ") == "koordinaten"]:
            del mk[k]
        altes_feld_entfernen(knoten, "koordinaten")
        geaendert.append(S("schreiben.antwort.lage.koordinaten_entfernt", w1=", ".join(map(str, alt)) if isinstance(alt, list) else alt))
    for feld, wert in (("adresse", adresse), ("punkt", punkt)):
        if not wert:
            continue
        alt = (gelesen.get(feld) or {}).get("wert") if isinstance(gelesen.get(feld), dict) else None
        lage_merkmal_schreiben(knoten, "adresse" if feld == "adresse" else "koordinaten", wert, quelle, g)
        text = ", ".join(map(str, wert)) if feld == "punkt" else wert
        geaendert.append(S("schreiben.antwort.lage.koordinaten" if feld == "punkt" else "schreiben.antwort.lage.adresse", w1=text)
                         + (S("schreiben.antwort.lage.war", w1=", ".join(map(str, alt)) if isinstance(alt, list) else alt) if alt else ""))
    routen_speichern(reise_dir, roh)
    grund = text_wert(args, "grund")
    # Adresse ohne Koordinaten (K3): Frieda soll Koordinaten recherchieren; bis dahin nennt der Kartenstatus den Eintrag
    ohne = not weg and not isinstance(lage_lesen(knoten).get("punkt"), dict)
    return (S("schreiben.titel.lage", w1=bezeichnung),
            f"{bezeichnung}: " + verbinden(geaendert, "; ") + S("schreiben.antwort.lage.herkunft", w1=quelle, w2=g.isoformat())
            + (S("schreiben.antwort.grund", w1=grund) if grund else "") + (S("schreiben.antwort.lage.koordinaten_fehlen") if ohne else ""))


# ---------- Karte (Epic #225): Ansichten, GPX-Tracks, Punkte aus OpenStreetMap ----------

def kartenansicht_setzen(reise_dir, wer, args, heute=None):
    """Kartenansicht (#236, K5): Titel und Auswahl aus Tagen, Strecken und Arten; ersetzt eine Ansicht gleichen Titels, entfernen
    nimmt sie heraus. Steht als Teil des Plans in routen.yaml (karten_ansichten). -> (Titel, Text)."""
    from ruamel.yaml.comments import CommentedSeq
    titel = text_wert(args, "titel", pflicht=True, laenge=80).strip()
    route = route_stand(reise_dir)
    auswahl = {}
    bekannt = {"tage": [t["id"] for t in route.get("tage") or []] + list(route.get("weitere_tage") or {}),
               "strecken": list(route.get("strecken") or {}), "arten": list(route.get("arten") or {})}
    for feld in ("tage", "strecken", "arten"):
        liste = liste_wert(args, feld, laenge=60) or []
        for x in liste:
            if x not in bekannt[feld]:
                raise Ablehnung("schreiben.kartenansicht.unbekannt", feld=feld, x=x, w1=", ".join(bekannt[feld]) or "–")
        if liste:
            auswahl[feld] = liste
    uebersicht = uebersicht_wert(reise_dir, args)   # Arten, deren Übersicht unter der Karte dieser Ansicht steht (ADR-0007, Schritt e)
    if uebersicht:
        auswahl["uebersicht"] = uebersicht
    entfernen = bool_wert(args, "entfernen")
    roh = routen_laden(reise_dir)
    ansichten = roh.get("karten_ansichten")
    if ansichten is None:
        ansichten = roh["karten_ansichten"] = CommentedSeq()
    alt = next((i for i, a in enumerate(ansichten) if isinstance(a, dict) and a.get("titel") == titel), None)
    if entfernen:
        if alt is None:
            raise Ablehnung("schreiben.kartenansicht.fehlt", titel=titel, w1=", ".join(str(a.get("titel")) for a in ansichten) or "–")
        del ansichten[alt]
        if not ansichten:
            del roh["karten_ansichten"]
        routen_speichern(reise_dir, roh)
        return S("schreiben.titel.kartenansicht_entfernt", titel=titel), S("schreiben.antwort.kartenansicht.entfernt", titel=titel)
    if not auswahl:
        raise Ablehnung("schreiben.kartenansicht.leer")
    knoten = fliess_map({"titel": titel, **auswahl})
    if alt is None:
        ansichten.append(knoten)
    else:
        ansichten[alt] = knoten
    routen_speichern(reise_dir, roh)
    worte = "; ".join(f"{S('schreiben.kartenansicht.feld.' + k)}: {', '.join(v)}" for k, v in auswahl.items())
    return (S("schreiben.titel.kartenansicht", titel=titel),
            S("schreiben.antwort.kartenansicht." + ("ersetzt" if alt is not None else "angelegt"), titel=titel, w1=worte))


# Größte GPX-Datei im Gespräch (Zeichen); der Konnektor nimmt höchstens 64 KB je Anfrage (MAX_BODY)
MAX_GPX = 60000


def track_anhaengen(reise_dir, wer, args, heute=None):
    """GPX-Track an eine Strecke hängen (K13): die Datei kommt als Text aus dem Gespräch, liegt danach unter medien/gpx/ der Reise
    und ersetzt auf der Karte die schematische Linie; benannte Wegpunkte werden nummerierte Punkte (K15). -> (Titel, Text)."""
    from defusedxml import ElementTree as DET
    heute = heute or datetime.date.today()
    ziel = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip()
    if not re.fullmatch(r"E-\d+[A-Za-z]?", ziel):
        raise Ablehnung("schreiben.track.ziel")
    quelle = text_wert(args, "quelle", pflicht=True, laenge=600)
    text = args.get("gpx")
    if not isinstance(text, str) or not text.strip():
        raise Ablehnung("schreiben.text_wert.1", feld="gpx")
    if len(text) > MAX_GPX:
        raise Ablehnung("schreiben.track.gross", n=MAX_GPX)
    try:
        wurzel = DET.fromstring(text.encode("utf-8"))
    except Exception:   # noqa: BLE001 – kaputtes oder gefährliches XML: abgelehnt
        raise Ablehnung("schreiben.track.kein_gpx")
    namen = [e.tag.rsplit("}", 1)[-1] for e in wurzel.iter()]
    punkte = sum(1 for n in namen if n in ("trkpt", "rtept"))
    if namen[0] != "gpx" or punkte < 2:
        raise Ablehnung("schreiben.track.kein_gpx")
    roh = routen_laden(reise_dir)
    knoten = (roh.get("strecken") or {}).get(ziel)
    if knoten is None:
        raise Ablehnung("schreiben.ding_finden.3", ziel=ziel)
    rel = f"medien/gpx/{ziel.lower()}.gpx"
    datei = Path(reise_dir) / rel
    datei.parent.mkdir(parents=True, exist_ok=True)
    war = datei.exists()
    datei.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    lage_merkmal_schreiben(knoten, "gpx", rel, quelle, heute)
    routen_speichern(reise_dir, roh)
    wp = sum(1 for e in wurzel.iter() if e.tag.rsplit("}", 1)[-1] == "wpt" and any(c.tag.rsplit("}", 1)[-1] == "name" and (c.text or "").strip() for c in e))
    bezeichnung = f"{ziel} {knoten.get('titel', '')}".strip()
    return (S("schreiben.titel.track", w1=bezeichnung),
            S("schreiben.antwort.track." + ("ersetzt" if war else "angehaengt"), w1=bezeichnung, n=punkte, w2=rel)
            + (S("schreiben.antwort.track.wegpunkte", n=wp) if wp else "") + S("schreiben.antwort.lage.herkunft", w1=quelle, w2=heute.isoformat()))


# Punkte aus OpenStreetMap (K14): feste Abfrage der Tags, die die Person im Gespräch wählt; keine KI. Overpass-API (ODbL)
OVERPASS = kartendienst.OVERPASS   # Vorgabe; FR_OVERPASS überschreibt sie (zur Laufzeit gelesen)
OSM_TAG = re.compile(r"^[a-z][a-z0-9_:]{0,40}(=[A-Za-z0-9_:;. -]{1,60})?$")
MAX_TREFFER = 200
OSM_ZEIT = 12            # Sekunden: eigener Abruf im Vorgang (Rückfall), der Schreibvorgang hat insgesamt ZEIT_GESAMT
OSM_FRIST_VORAB = 45     # Frist des Abrufs vor der Sperre, mit Wiederholung und Pause (#240)
OSM_PAUSE = 2            # Pause vor der einen Wiederholung
OSM_REST_WIEDERHOLUNG = 15   # wiederholt wird nur, wenn noch so viele Sekunden der Frist übrig sind
ZEIT_VORAB_VORB = 10     # höchstens für Lesekopie, Rollenprüfung und Abfrage vor dem Abruf
ZEIT_VORAB = ZEIT_VORAB_VORB + OSM_FRIST_VORAB   # Vorab-Fenster vor der Sperre insgesamt


def overpass_holen(abfrage, frist, rahmen=None):
    """Overpass-Abfrage (ohne Zeitangabe) mit eigener Frist in Sekunden -> JSON (dict). Ist ein eigener Kartendienst eingestellt
    (FR_KARTENDIENST, #444) und liegt der Rahmen der Abfrage (ohne Angabe aus der Abfrage gelesen) ganz in seiner Abdeckung, wird
    zuerst er gefragt, höchstens kartendienst.TEILFRIST_EIGEN Sekunden und ohne Wiederholung; scheitert er, bekommt der öffentliche
    Dienst die Restfrist. Beide teilen sich dieselbe Frist. Mit eingestelltem eigenem Dienst trägt die Antwort „dienst“ und „stand“
    (kartendienst.stempeln); ohne ihn ist sie genau die des öffentlichen Dienstes. Wirft Ablehnung wie overpass_oeffentlich."""
    ende = time.monotonic() + frist
    if not kartendienst.eigener_dienst():
        return overpass_oeffentlich(abfrage, kartendienst.oeffentlicher_dienst(), frist)
    rahmen = rahmen if rahmen is not None else kartendienst.rahmen_aus_abfrage(abfrage)
    dienst, adresse = kartendienst.dienst_waehlen(rahmen)
    if dienst == "eigen":
        antwort = overpass_eigen(abfrage, adresse, min(kartendienst.TEILFRIST_EIGEN, frist))
        if antwort is not None:
            return kartendienst.stempeln(antwort, "eigen")
        adresse = kartendienst.oeffentlicher_dienst()
    return kartendienst.stempeln(overpass_oeffentlich(abfrage, adresse, ende - time.monotonic()), "oeffentlich")


def overpass_senden(adresse, abfrage, frist, timeout):
    """Eine Anfrage an einen Overpass-Dienst mit [timeout:frist] in der Abfrage -> JSON. Fehler gehen an den Aufrufer."""
    import urllib.parse
    import urllib.request
    text = abfrage.replace("[out:json]", f"[out:json][timeout:{max(1, int(frist))}]", 1)
    req = urllib.request.Request(adresse, data=urllib.parse.urlencode({"data": text}).encode(),
                                 headers={"User-Agent": instanz.kennung()})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def overpass_eigen(abfrage, adresse, frist):
    """Der eigene Kartendienst: ein Versuch mit der Teilfrist -> JSON mit „elements“ (auch leer: innerhalb der Abdeckung ist
    „keine Treffer“ ein Ergebnis) oder None bei Fehler, Zeitüberschreitung oder Antwort ohne „elements“."""
    import http.client
    import urllib.error
    try:
        antwort = overpass_senden(adresse, abfrage, frist, max(0.1, frist))
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError):   # auch abgebrochene Antworten
        return None
    return antwort if isinstance(antwort, dict) and isinstance(antwort.get("elements"), list) else None


def overpass_oeffentlich(abfrage, adresse, frist):
    """Der öffentliche Dienst mit Frist in Sekunden -> JSON (dict). Nach einer schnellen Fehlerantwort (429/502/503/504) genau
    eine Wiederholung nach OSM_PAUSE, wenn noch OSM_REST_WIEDERHOLUNG Sekunden übrig sind; nach einer Zeitüberschreitung nie.
    Wirft Ablehnung mit verständlichem Grund (Limit, Zeit, Netz)."""
    import http.client
    import urllib.error
    ende = time.monotonic() + frist
    for versuch in (1, 2):
        try:
            return overpass_senden(adresse, abfrage, frist, max(0.1, ende - time.monotonic()))
        except urllib.error.HTTPError as e:
            fehler = Ablehnung("schreiben.kartenpunkte.limit" if e.code in (429, 504) else "schreiben.kartenpunkte.dienst", w1=e.code)
            if versuch == 2 or e.code not in (429, 502, 503, 504) or ende - time.monotonic() < OSM_REST_WIEDERHOLUNG:
                raise fehler
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError) as e:
            raise Ablehnung("schreiben.kartenpunkte.dienst", w1=type(e).__name__)
        time.sleep(OSM_PAUSE)
    raise fehler   # nicht erreichbar: der zweite Versuch kehrt zurück oder wirft


def overpass_abfragen(abfrage):
    """Overpass-Abfrage (ohne Zeitangabe) -> JSON (dict). Steht in der Datei aus FR_OSM_VORAB (vom Dienst vor der Sperre
    geholt) dieselbe Abfrage, kommt die Antwort von dort; sonst eigener Abruf mit der kurzen Frist OSM_ZEIT. Tests ersetzen
    diese Funktion."""
    pfad = os.environ.get("FR_OSM_VORAB")
    if pfad:
        try:
            vorab = json.loads(Path(pfad).read_text(encoding="utf-8"))
            if isinstance(vorab, dict) and vorab.get("abfrage") == abfrage and isinstance(vorab.get("antwort"), dict):
                return vorab["antwort"]
        except (OSError, ValueError):
            pass
    return overpass_holen(abfrage, OSM_ZEIT)


def abstand_zur_linie_m(p, linie):
    """Kürzester Abstand eines Punkts zu einer Linie (Liste von [Breite, Länge]) in Metern, flache Näherung."""
    import math
    b0 = p[0]
    xy = lambda q: (q[1] * 111320 * math.cos(math.radians(b0)), q[0] * 110540)
    px, py = xy(p)
    best = float("inf")
    for a, b in zip(linie, linie[1:] or linie):
        (ax, ay), (bx, by) = xy(a), xy(b)
        dx, dy = bx - ax, by - ay
        t = 0 if not (dx or dy) else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(px - ax - t * dx, py - ay - t * dy))
    return best


def art_rolle_sichern(art_def, rolle):
    """Der Schlüssel des Merkmals einer Art (Wörterbuch aus arten.yaml) mit dieser Rolle; fehlt es, wird es angelegt (ADR-0007, Schritt d)
    -> Schlüssel."""
    from routen import ROLLEN_MERKMAL
    mk = art_def.setdefault("merkmale", {})
    for k, d in mk.items():
        if isinstance(d, dict) and d.get("rolle") == rolle:
            return k
    schl, name_key, typ = ROLLEN_MERKMAL[rolle]
    mk[schl] = {"name": texte.t(texte.VORGABE_REISE, name_key), "typ": typ, "rolle": rolle, "stufe": "angeboten"}
    return schl


PUNKT_FELDER_ROLLEN = (("nr", "nummer"), ("auch", "alias"), ("art", "sorte"), ("osm", "osm"), ("trinkbar", "trinkbar"), ("offen", "oeffnung"), ("id", "bezug"))
OSM_BEZUG = re.compile(r"^OSM ((?:node|way|relation)/\d+)")


def kartenpunkte_ablegen(reise_dir, wer, an, punkte, heute=None, aktualisieren=False):
    """Kartenpunkte als Dinge ablegen (ADR-0007, Schritt d; gemeinsam für den Konnektor und die Werkzeuge punkte_holen und
    wissen_punkte_holen). punkte: Liste von {name, kat (Schlüssel der Art mit gruppe), lage, quelle, nr, auch, art (Sorte), osm, trinkbar, offen,
    id, hinweis, geprueft}; an: Strecke oder Abschnitt des Wissens, an dem sie hängen. Ein Punkt mit demselben OSM-Bezug (Rolle osm oder
    „OSM node/…“ am Anfang der Quelle der Koordinaten), sonst mit demselben Namen, Art und Nummer an diesem Elternelement ist schon da: er
    bleibt unverändert (aktualisieren: Koordinaten und Rollenwerte werden gesetzt). Nichts wird gelöscht, IDs bleiben.
    -> {"neu": [ID], "vorhanden": [ID], "unbekannt": [Art]} (unbekannt: Arten, die die Reise nicht mit gruppe kennt; ihre Punkte werden nicht abgelegt)."""
    heute = heute or datetime.date.today()
    arten = arten_laden(reise_dir)
    vorher = copy.deepcopy(arten)
    ergebnis = {"neu": [], "vorhanden": [], "unbekannt": []}
    roh = routen_laden(reise_dir)
    aufenthalte = roh.setdefault("aufenthalte", type(roh)())

    def rollen_von(art):   # Rolle -> Schlüssel des Merkmals dieser Art
        return {d.get("rolle"): k for k, d in ((arten.get(art) or {}).get("merkmale") or {}).items() if isinstance(d, dict) and d.get("rolle")}

    def koordinaten_von(knoten):
        return next((v for v in (knoten.get("merkmale") or {}).values() if isinstance(v, dict) and v.get("typ") == "koordinaten"), None)

    def schluessel(art, knoten, name=None, osm=None, nummer=None):
        rollen = rollen_von(art)
        mk = knoten.get("merkmale") or {} if knoten is not None else {}
        wert = lambda r: (mk.get(rollen.get(r)) or {}).get("wert") if rollen.get(r) else None
        o = osm if knoten is None else wert("osm")
        if not o and knoten is not None:
            k = koordinaten_von(knoten)
            o = (OSM_BEZUG.match(str((k or {}).get("quelle") or "")) or [None, None])[1]
        if o:
            return ("osm", o)
        return ("name", art, str(name if knoten is None else knoten.get("name")).casefold(), str((nummer if knoten is None else wert("nummer")) or ""))

    vorhanden = {}
    for aid, k in aufenthalte.items():
        if isinstance(k, dict) and k.get("an") == an and k.get("art") in arten:
            vorhanden[schluessel(k["art"], k)] = (aid, k)
    quelle_gesamt = S("schreiben.kartenpunkte.quelle", w1=heute.isoformat()).text(sprache_von(reise_dir))
    for p in punkte:
        kat = p.get("kat")
        if not (arten.get(kat) or {}).get("gruppe"):
            if kat not in ergebnis["unbekannt"]:
                ergebnis["unbekannt"].append(kat)
            continue
        art_def = arten[kat]
        quelle = p.get("quelle") or quelle_gesamt
        g = p.get("geprueft") or heute
        g = g if isinstance(g, datetime.date) else datetime.date.fromisoformat(str(g))
        name = p.get("name") or art_def.get("einzahl") or art_def.get("name") or kat
        roll = {}
        for feld, rolle in PUNKT_FELDER_ROLLEN:
            wert = p.get(feld)
            if wert not in (None, "", [], {}):
                roll[rolle] = "; ".join(wert) if isinstance(wert, list) else wert
        for rolle in roll:
            art_rolle_sichern(art_def, rolle)
        schl = rollen_von(kat)
        key = schluessel(kat, None, name=name, osm=p.get("osm"), nummer=p.get("nr"))
        if key in vorhanden:
            aid, k = vorhanden[key]
            ergebnis["vorhanden"].append(aid)
            if aktualisieren:
                if p.get("lage"):
                    lage_merkmal_schreiben(k, "koordinaten", [float(x) for x in p["lage"]], quelle, g)
                for rolle, wert in roll.items():
                    k.setdefault("merkmale", merkmale_knoten({}))[schl[rolle]] = fliess_map({"wert": wert, "quelle": quelle})
            continue
        d = {"name": name, "art": kat, "an": an, "quelle": quelle}
        if p.get("hinweis"):
            d["hinweis"] = p["hinweis"]
        k = block_map(d)
        if p.get("lage"):
            lage_merkmal_schreiben(k, "koordinaten", [float(x) for x in p["lage"]], quelle, g)
        for rolle, wert in roll.items():
            k.setdefault("merkmale", merkmale_knoten({}))[schl[rolle]] = fliess_map({"wert": wert, "quelle": quelle})
        aid = neue_id(reise_dir, "A")
        aufenthalte[aid] = k
        vorhanden[key] = (aid, k)
        ergebnis["neu"].append(aid)
    if arten != vorher:
        arten_speichern(reise_dir, arten, wer)
    routen_speichern(reise_dir, roh)
    return ergebnis


def kartenpunkte_lesen(reise_dir):
    """Die Kartenpunkte einer Reise, wie sie als Dinge stehen (ADR-0007, Schritt d; Gegenstück zu kartenpunkte_ablegen, gelesen von den
    Werkzeugen adressen_holen und wasser_pruefen): Aufenthalte, deren Art eine gruppe hat und die an einer Strecke oder einem Abschnitt
    hängen (an:). Werte stehen in den Merkmalen der Art und werden nach Rolle gelesen (nummer, alias, sorte, osm, trinkbar, oeffnung,
    bezug), nie nach dem Namen der Art oder des Merkmals.
    -> [{id, name, art, gruppe, an, lage, quelle, nummer, alias, sorte, osm, trinkbar, oeffnung, bezug}] (fehlende Werte None)."""
    from routen import ist_eltern
    arten = arten_laden(reise_dir)
    aufenthalte = (routen_laden(reise_dir) or {}).get("aufenthalte") or {}
    aus = []
    for aid, k in aufenthalte.items():
        if not isinstance(k, dict):
            continue
        art = arten.get(k.get("art"))
        if not isinstance(art, dict) or not art.get("gruppe") or not ist_eltern(k.get("an")):
            continue
        mk = k.get("merkmale") or {}
        rollen = {d.get("rolle"): s for s, d in (art.get("merkmale") or {}).items() if isinstance(d, dict) and d.get("rolle")}
        koordinaten = next((v for v in mk.values() if isinstance(v, dict) and v.get("typ") == "koordinaten"), None)
        p = {"id": aid, "name": k.get("name"), "art": k["art"], "gruppe": art["gruppe"], "an": k["an"],
             "lage": [float(x) for x in koordinaten["wert"]] if koordinaten and koordinaten.get("wert") else None,
             "quelle": (koordinaten or {}).get("quelle") or k.get("quelle")}
        for rolle in ("nummer", "alias", "sorte", "osm", "trinkbar", "oeffnung", "bezug"):
            v = mk.get(rollen.get(rolle)) if rollen.get(rolle) else None
            p[rolle] = v.get("wert") if isinstance(v, dict) else None
        aus.append(p)
    return aus


def kartenpunkte_abfrage(reise_dir, args):
    """Prüfungen und Abfrage für kartenpunkte_holen -> (abfrage, linie, abstand, tags, sid, kat, route); die Abfrage trägt keine
    Zeitangabe (overpass_holen setzt sie). Wirft dieselben Ablehnungen wie kartenpunkte_holen."""
    sid = (text_wert(args, "strecke", pflicht=True, laenge=20) or "").strip()
    kat = (text_wert(args, "kategorie", pflicht=True, laenge=40) or "").strip()
    tags = liste_wert(args, "osm", laenge=10) or []
    if not tags:
        raise Ablehnung("schreiben.text_wert.1", feld="osm")
    for t in tags:
        if not OSM_TAG.match(t):
            raise Ablehnung("schreiben.kartenpunkte.tag", t=t)
    try:
        abstand = int(args.get("abstand_m") or 150)
    except (TypeError, ValueError):
        raise Ablehnung("schreiben.kartenpunkte.abstand")
    if not 10 <= abstand <= 3000:
        raise Ablehnung("schreiben.kartenpunkte.abstand")
    route = route_stand(reise_dir)
    kategorien = {k: d for k, d in (route.get("arten") or {}).items() if d.get("gruppe")}   # Arten mit gruppe (ADR-0007, Schritt d)
    punkt_kats = [k for k, d in kategorien.items() if d["gruppe"] == "punkt"]
    if kat not in punkt_kats:
        raise Ablehnung("schreiben.kartenpunkte.kategorie", kat=kat, w1=", ".join(punkt_kats) or "–")
    if sid not in (route.get("strecken") or {}):
        raise Ablehnung("schreiben.ding_finden.3", ziel=sid)
    k = route.get("karte") or {}
    linie = (k.get("wege") or {}).get(sid)
    if not linie:
        st, orte = route["strecken"][sid], k.get("orte") or {}
        a, b = (orte.get(st.get("von")) or {}).get("lage"), (orte.get(st.get("nach")) or {}).get("lage")
        linie = [a, b] if a and b else None
    if not linie:
        raise Ablehnung("schreiben.kartenpunkte.keine_linie", sid=sid)
    rand_b = abstand / 110540
    rand_l = abstand / 70000
    bbox = (f"{min(p[0] for p in linie) - rand_b:.5f},{min(p[1] for p in linie) - rand_l:.5f},"
            f"{max(p[0] for p in linie) + rand_b:.5f},{max(p[1] for p in linie) + rand_l:.5f}")
    def filter_von(t):
        key, _, wert = t.partition("=")
        return f'["{key}"="{wert}"]' if wert else f'["{key}"]'
    abfrage = "[out:json];(" + "".join(f"nwr{filter_von(t)}({bbox});" for t in tags) + ");out center tags;"
    return abfrage, linie, abstand, tags, sid, kat, route


def kartenpunkte_holen(reise_dir, wer, args, heute=None):
    """Punkte aus OpenStreetMap längs einer Strecke (K14): die Person wählt im Gespräch die Kategorie der Reise (plan/kategorien.yaml,
    Gruppe punkt) und die OSM-Tags (z. B. amenity=drinking_water). Treffer bis abstand_m von der Linie kommen mit Quelle und Stand
    nach plan/punkte.yaml; ein zweiter Aufruf ersetzt die Treffer derselben Kategorie an dieser Strecke. -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    abfrage, linie, abstand, tags, sid, kat, route = kartenpunkte_abfrage(reise_dir, args)
    kategorien = {k: d for k, d in (route.get("arten") or {}).items() if d.get("gruppe")}
    antwort = overpass_abfragen(abfrage)
    stand = kartendaten_stand(antwort) or heute
    quelle_schluessel = {"eigen": "schreiben.kartenpunkte.quelle.eigen", "oeffentlich": "schreiben.kartenpunkte.quelle.oeffentlich"}.get(
        (antwort or {}).get("dienst"), "schreiben.kartenpunkte.quelle")   # gestempelt (#444): Dienst und Stand der Daten
    treffer, gesehen = [], set()
    for e in (antwort or {}).get("elements") or []:
        lat, lon = e.get("lat", (e.get("center") or {}).get("lat")), e.get("lon", (e.get("center") or {}).get("lon"))
        if lat is None or lon is None:
            continue
        lage = [round(float(lat), 6), round(float(lon), 6)]
        oid = f"{e.get('type', 'node')}/{e.get('id')}"
        if oid in gesehen or abstand_zur_linie_m(lage, linie) > abstand:
            continue
        gesehen.add(oid)
        tg = e.get("tags") or {}
        art = next((tg.get(t.partition("=")[0]) for t in tags if tg.get(t.partition("=")[0])), None)
        p = {"name": tg.get("name"), "kat": kat, "art": art, "lage": lage, "osm": oid,
             "quelle": S(quelle_schluessel, w1=stand.isoformat()).text(texte.aufruf_sprache()), "geprueft": heute}
        treffer.append({x: v for x, v in p.items() if v not in (None, "")})
        if len(treffer) >= MAX_TREFFER:
            break
    # Treffer werden Dinge (A-…): Aufenthalte der Art kat mit an: <Strecke>, Koordinaten, OSM-Bezug (Rolle osm) und Sorte (Rolle sorte).
    # Ein zweiter Aufruf aktualisiert die Dinge mit demselben OSM-Bezug; nichts wird gelöscht (IDs bleiben).
    quelle_text = S(quelle_schluessel, w1=stand.isoformat()).text(sprache_von(reise_dir))
    ergebnis = kartenpunkte_ablegen(reise_dir, wer, sid, [{**p, "kat": kat, "quelle": quelle_text, "geprueft": heute} for p in treffer], heute=heute,
                                    aktualisieren=True)
    alt = ergebnis["vorhanden"]
    name = kategorien[kat]["name"]
    beispiele = ", ".join(dict.fromkeys(p["name"] for p in treffer if p.get("name")))
    return (S("schreiben.titel.kartenpunkte", w1=sid, w2=name, n=len(treffer)),
            S("schreiben.antwort.kartenpunkte", w1=sid, w2=name, n=len(treffer), m=len(alt), w3=", ".join(tags))
            + (S("schreiben.antwort.kartenpunkte.beispiele", w1=beispiele[:300]) if beispiele else "") + kartenpunkte_herkunft(antwort, stand))


def kartendaten_stand(antwort):
    """Stand der Kartendaten aus einer gestempelten Antwort („stand“, kartendienst.stempeln) als date, sonst None."""
    try:
        return datetime.date.fromisoformat(str((antwort or {}).get("stand") or "")[:10])
    except ValueError:
        return None


def kartenpunkte_herkunft(antwort, stand):
    """Schluss der Antwort von kartenpunkte_holen: Lizenz und Stand der Daten (Stand heute, wenn die Antwort keinen nennt) und,
    wenn die Antwort gestempelt ist, welcher Dienst geantwortet hat (#444)."""
    dienst = (antwort or {}).get("dienst")
    teil = (S("schreiben.antwort.kartenpunkte.lizenz.stand", w1=stand.isoformat()) if kartendaten_stand(antwort)
            else S("schreiben.antwort.kartenpunkte.lizenz"))
    schluessel = {"eigen": "schreiben.antwort.kartenpunkte.dienst.eigen",
                  "oeffentlich": "schreiben.antwort.kartenpunkte.dienst.oeffentlich"}.get(dienst)
    return teil + (S(schluessel) if schluessel else "")


def frage_zeile(reise_dir, text, bis=None):
    """Eine Zeile in offene-fragen.md anhängen (Tabelle | ID | Was | Bis | Status |) -> neue F-ID."""
    p = Path(reise_dir) / "offene-fragen.md"
    if not p.exists():
        raise Ablehnung("schreiben.frage_zeile.1")
    zeilen = p.read_text(encoding="utf-8").splitlines()
    letzte = max((i for i, z in enumerate(zeilen) if re.match(r"^\|\s*F-\d+\s*\|", z)), default=None)
    kopf = next((i for i, z in enumerate(zeilen) if re.match(r"^\|\s*ID\s*\|", z, re.I)), None)
    if letzte is None and kopf is None:
        raise Ablehnung("schreiben.frage_zeile.2")
    fid = neue_id(reise_dir, "F")
    sauber = lambda t: " ".join(str(t).replace("|", "/").split())
    neu = f"| {fid} | {sauber(text)} | {sauber(bis) if bis else '–'} | offen |"
    stelle = letzte if letzte is not None else kopf + 1
    zeilen.insert(stelle + 1, neu)
    p.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return fid


def frage_anlegen(reise_dir, wer, args, heute=None):
    """Eine offene Frage (F-…) anlegen: etwas, das zu klären oder zu entscheiden ist. -> (Titel, Text)."""
    text = text_wert(args, "text", pflicht=True, laenge=1000)
    bis = text_wert(args, "bis", laenge=60)
    bezug = id_liste(args, "bezug", r"(T-\d+|E-\d+[A-Za-z]?|U-\d+|O-\d+|V-\d+(\.[a-z])?|W-\d+(\.[\w-]+)?)", routen_laden(reise_dir))
    if bezug:
        text = f"{text} ({', '.join(bezug)})" if not any(b in text for b in bezug) else text
    fid = frage_zeile(reise_dir, text, bis)
    return S("schreiben.titel.frage_angelegt", w1=fid), S("schreiben.antwort.frage.angelegt", w1=fid, w2=text) + (S("schreiben.antwort.frage.bis", w1=bis) if bis else "") + S("schreiben.antwort.frage.von", w1=wer["name"])


def option_bauen(roh, route, vid, o, wer, heute, bereich):
    """Eine Option aus der Anfrage -> CommentedMap (Status vorgeschlagen mit Verlauf). bereich: Art der Dinge der Wahlstelle
    (Schlüssel aus plan/arten.yaml) für die Merkmale. Herkunft (quelle) ist Pflicht (ADR-0001, Frage 5); sie gilt als Vorgabe
    für die Merkmale der Option."""
    if not isinstance(o, dict):
        raise Ablehnung("schreiben.option_bauen.1")
    d = {"id": None, "titel": text_wert(o, "titel", pflicht=True, laenge=200)}
    if (t := text_wert(o, "text", laenge=2000)):
        d["text"] = t
    for f in ("plus", "minus"):
        if (l := liste_wert(o, f, laenge=10)):
            d[f] = l
    u = id_liste(o, "unterkuenfte", r"U-\d+", roh, "unterkuenfte")
    st = id_liste(o, "strecken", r"E-\d+[A-Za-z]?", roh, "strecken")
    fo = id_liste(o, "folge", r"T-\d+", roh, "tage")
    au = id_liste(o, "aufenthalte", r"A-\d+", roh, "aufenthalte")
    og = id_liste(o, "orte", r"O-\d+", roh, "orte")
    if not option_inhalt_ok({"unterkuenfte": u, "strecken": st, "folge": fo, "aufenthalte": au, "orte": og}):
        raise Ablehnung("schreiben.option_bauen.2", w1=d['titel'])
    for k, v in (("unterkuenfte", u), ("strecken", st), ("folge", fo), ("aufenthalte", au), ("orte", og)):
        if v:
            d[k] = v
    optionen_ids = {x["id"] for w in route.get("wahlstellen") or [] for x in w["optionen"]}
    for f in ("erfordert", "schliesst_aus"):
        l = id_liste(o, f, r"V-\d+\.[a-z]", roh)
        if l:
            fehlt = [x for x in l if x not in optionen_ids]
            if fehlt:
                raise Ablehnung("schreiben.option_bauen.3", w1=d['titel'], f=f, w3=', '.join(fehlt))
            d[f] = l
    if (siehe := text_wert(o, "siehe", laenge=20)):
        if not ID_MUSTER.match(siehe):
            raise Ablehnung("schreiben.option_bauen.4")
        d["siehe"] = siehe
    if (a := text_wert(o, "ausloeser")):
        d["ausloeser"] = a
    quelle = text_wert(o, "quelle", laenge=600)
    if not quelle:
        raise Ablehnung("schreiben.option_bauen.5", w1=d['titel'])
    d["quelle"] = quelle
    verlauf = {"datum": heute, "status": "vorgeschlagen", "wer": wer["name"]}
    if (g := text_wert(o, "grund")):
        verlauf["grund"] = g
    krit = (route.get("merkmale") or {}).get(bereich) or []
    if vid:
        w = next((w for w in route.get("wahlstellen") or [] if w["id"] == vid), None)
        if w is not None:
            krit = w.get("kriterien") or krit
    werte = merkmale_werte(o.get("merkmale"), krit, heute, {"quelle": quelle, "geprueft": o.get("geprueft")})
    knoten = block_map(d)
    if werte:
        knoten["merkmale"] = merkmale_knoten(werte)
    from ruamel.yaml.comments import CommentedSeq
    knoten["verlauf"] = CommentedSeq([fliess_map(verlauf)])
    return knoten, d, werte


def option_anlegen(reise_dir, wer, args, heute=None):
    """Eine Option an einer bestehenden Wahlstelle anlegen, Status vorgeschlagen (die Entscheidung bleibt bei den
    Organisator:innen). -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    vid = (text_wert(args, "wahlstelle", pflicht=True, laenge=10) or "").strip()
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    w = (roh.get("wahlstellen") or {}).get(vid) if re.fullmatch(r"V-\d+", vid) else None
    if w is None:
        raise Ablehnung("schreiben.option_anlegen.1", vid=vid)
    wr = next((x for x in route.get("wahlstellen") or [] if x["id"] == vid), {})
    optionen = w.get("optionen")
    if optionen is None:
        from ruamel.yaml.comments import CommentedSeq
        optionen = CommentedSeq()
        w["optionen"] = optionen
    vergeben = {o.get("id") for o in optionen if isinstance(o, dict)}
    buchstabe = next((c for c in "abcdefghijklmnopqrstuvwxyz" if f"{vid}.{c}" not in vergeben), None)
    if buchstabe is None:
        raise Ablehnung("schreiben.option_anlegen.2", vid=vid)
    oid = f"{vid}.{buchstabe}"
    knoten, d, werte = option_bauen(roh, route, vid, args, wer, heute, wr.get("art"))
    knoten["id"] = oid
    knoten.move_to_end("id", last=False)
    optionen.append(knoten)
    routen_speichern(reise_dir, roh)
    titel = S("schreiben.titel.option_vorgeschlagen", w1=oid, w2=d['titel'], w3=vid)
    text = (S("schreiben.antwort.option.angelegt", w1=oid, w2=d["titel"], w3=vid, w4=wr.get("titel", ""))
            + (S("schreiben.antwort.ding.merkmale", w1=", ".join(werte)) if werte else "") + S("schreiben.antwort.option.herkunft", w1=d["quelle"])
            + S("schreiben.antwort.option.entscheiden"))
    return titel, text


def wahlstelle_anlegen(reise_dir, wer, args, heute=None):
    """Eine Wahlstelle mit mindestens einer Option anlegen; sie hängt mit „an“ an Tagen, Strecken, Unterkünften, Orten oder
    Abschnitten. Der Plan selbst (welche Nacht welche Wahlstelle nutzt) ändert sich dadurch nicht. -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    arten = route.get("arten") or {}
    d = {"titel": text_wert(args, "titel", pflicht=True, laenge=200)}
    # wann: planung | unterwegs (bis 29.10.2026 hieß das art:); art: die Art der Dinge, zwischen denen gewählt wird (alt bereich:)
    art = text_wert(args, "wann", laenge=20)
    bereich = text_wert(args, "art", laenge=40)
    if art is None and bereich in ("planung", "unterwegs"):   # alte Form: art = wann
        art, bereich = bereich, None
    if bereich is None:
        bereich = text_wert(args, "bereich", laenge=40)
    art = (art or "planung").lower()
    if art not in ("planung", "unterwegs"):
        raise Ablehnung("schreiben.wahlstelle_anlegen.1")
    d["wann"] = art
    if bereich is not None:
        bereich = bereich.lower()
        if bereich not in arten:
            raise Ablehnung("schreiben.wahlstelle_anlegen.2", w1=', '.join(arten) or 'keine')
        d["art"] = bereich
    an = id_liste(args, "an", r"(T-\d+|E-\d+[A-Za-z]?|U-\d+|A-\d+|O-\d+|V-\d+|W-\d+(\.[\w-]+)?)", roh)
    if an:
        for x in an:
            menge = {"T": "tage", "E": "strecken", "U": "unterkuenfte", "A": "aufenthalte", "O": "orte", "V": "wahlstellen"}.get(x[0])
            if menge and x not in (roh.get(menge) or {}):
                raise Ablehnung("schreiben.wahlstelle_anlegen.3", x=x)
        d["an"] = an
    if (frage := text_wert(args, "frage", laenge=10)):
        if not re.fullmatch(r"F-\d+", frage):
            raise Ablehnung("schreiben.ding_anlegen.5")
        d["frage"] = frage
    if (t := text_wert(args, "text", laenge=2000)):
        d["text"] = t
    optionen = args.get("optionen")
    if not isinstance(optionen, list) or not optionen:
        raise Ablehnung("schreiben.wahlstelle_anlegen.4")
    if len(optionen) > 26:
        raise Ablehnung("schreiben.wahlstelle_anlegen.5")
    vid = neue_id(reise_dir, "V")
    if art == "planung" and not frage:
        # Eine offene Planungs-Wahlstelle braucht eine Frage; sie entsteht hier mit (bis: Angabe oder „vor Abreise“)
        frage = frage_zeile(reise_dir, f"{d['titel']}: welche Option? ({vid})", text_wert(args, "bis", laenge=60) or "vor Abreise")
        d["frage"] = frage
    from ruamel.yaml.comments import CommentedSeq
    knoten = block_map(d)
    liste = CommentedSeq()
    namen = []
    for i, o in enumerate(optionen):
        ok, od, _ = option_bauen(roh, route, None, o, wer, heute, bereich)
        ok["id"] = f"{vid}.{'abcdefghijklmnopqrstuvwxyz'[i]}"
        ok.move_to_end("id", last=False)
        liste.append(ok)
        namen.append(f"{ok['id']} „{od['titel']}“")
    knoten["optionen"] = liste
    roh.setdefault("wahlstellen", type(roh)())
    roh["wahlstellen"][vid] = knoten
    routen_speichern(reise_dir, roh)
    titel = S("schreiben.titel.wahlstelle_angelegt", w1=vid, w2=d['titel'])
    text = (S("schreiben.antwort.wahlstelle.angelegt", w1=vid, w2=d["titel"], w3=art) + (f", {bereich}" if bereich else "")
            + (S("schreiben.antwort.wahlstelle.an", w1=", ".join(an)) if an else "")
            + S("schreiben.antwort.wahlstelle.mit", w1=", ".join(namen)) + (S("schreiben.antwort.wahlstelle.frage", w1=frage) if art == "planung" else ""))
    return titel, text


# ---------- Entscheiden und Plan (plan/routen.yaml, offene-fragen.md) ----------
ENTSCHEIDUNGEN = ("gewaehlt", "verworfen", "ersetzt")
WORT = texte.gruppe("de", "schreiben.wort")


def frage_status_setzen(reise_dir, fid, status):
    """Status-Zelle einer Frage in offene-fragen.md setzen -> True, wenn die Zeile gefunden wurde."""
    p = Path(reise_dir) / "offene-fragen.md"
    if not p.exists():
        return False
    zeilen = p.read_text(encoding="utf-8").splitlines()
    for i, z in enumerate(zeilen):
        if re.match(rf"^\|\s*{re.escape(fid)}\s*\|", z):
            zellen = [x.strip() for x in z.strip().strip("|").split("|")]
            if len(zellen) >= 4:
                zellen[-1] = " ".join(str(status).replace("|", "/").split())
                zeilen[i] = "| " + " | ".join(zellen) + " |"
                p.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
                return True
    return False


def entscheiden(reise_dir, wer, args, heute=None):
    """Entscheidung einer Organisator:in über eine Option: Verlaufseintrag (Datum, Status, Person, Grund) direkt in routen.yaml.
    gewählt setzt bisher gewählte Optionen derselben Wahlstelle auf ersetzt und klärt die Frage der Wahlstelle, sobald alle
    Wahlstellen an dieser Frage etwas gewählt haben; verworfen oder
    ersetzt ohne verbleibende Wahl öffnet die Frage wieder. Widersprüche zwischen Organisator:innen prüft der Konnektor vorher
    (regeln.konflikt). -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    oid = (text_wert(args, "option", pflicht=True, laenge=12) or "").strip()
    status = (text_wert(args, "status", pflicht=True, laenge=12) or "").lower()
    grund = text_wert(args, "grund", pflicht=True)
    durch = text_wert(args, "ersetzt_durch", laenge=12)
    quelle = text_wert(args, "quelle")
    if status not in ENTSCHEIDUNGEN:
        raise Ablehnung("schreiben.entscheiden.1", w1=', '.join(ENTSCHEIDUNGEN))
    if not re.fullmatch(r"V-\d+\.[a-z]", oid):
        raise Ablehnung("schreiben.entscheiden.2")
    vid = oid.split(".")[0]
    route = route_stand(reise_dir)
    wr = next((w for w in route.get("wahlstellen") or [] if w["id"] == vid), None)
    o = next((x for x in (wr or {}).get("optionen") or [] if x["id"] == oid), None)
    if o is None:
        raise Ablehnung("schreiben.entscheiden.3", oid=oid)
    if o.get("status") == status:
        raise Ablehnung("schreiben.entscheiden.4", oid=oid, w2=WORT[status])
    if status == "ersetzt":
        od = next((x for x in wr["optionen"] if x["id"] == durch), None) if durch else None
        if od is None or durch == oid:
            raise Ablehnung("schreiben.entscheiden.5", vid=vid)
        if od.get("status") in ("verworfen", "ersetzt"):
            raise Ablehnung("schreiben.entscheiden.6", durch=durch, w2=WORT[od['status']])
    elif durch:
        raise Ablehnung("schreiben.entscheiden.7")
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, oid)
    from ruamel.yaml.comments import CommentedSeq
    eintrag = {"datum": heute, "status": status, "wer": wer["name"], "grund": grund + (f" (Quelle: {quelle})" if quelle else "")}
    if durch:
        eintrag["durch"] = durch
    verlauf = knoten.get("verlauf")
    if verlauf is None:
        verlauf = CommentedSeq()
        knoten["verlauf"] = verlauf
    verlauf.append(fliess_map(eintrag))
    ersetzt = []
    nicht_gewaehlt = []
    wieder = []
    if status == "gewaehlt":
        for x in wr["optionen"]:
            if x["id"] != oid and x.get("status") == "gewaehlt":
                k2, _ = ding_finden(roh, x["id"])
                v2 = k2.get("verlauf")
                if v2 is None:
                    v2 = CommentedSeq()
                    k2["verlauf"] = v2
                v2.append(fliess_map({"datum": heute, "status": "ersetzt", "wer": wer["name"], "durch": oid,
                                      "grund": texte.t(sprache_von(reise_dir), "inhalt.schreiben.verlauf.ersetzt_durch", oid=oid, titel=o["titel"], grund=grund)}))
                ersetzt.append(x["id"])
        # Die übrigen Optionen der Wahlstelle sind damit nicht gewählt: ersetzt durch die gewählte (Product Owner 31.10.2026)
        for x in wr["optionen"]:
            if x["id"] != oid and x.get("status") in (None, "vorgeschlagen", "favorisiert"):
                k2, _ = ding_finden(roh, x["id"])
                v2 = k2.get("verlauf")
                if v2 is None:
                    v2 = CommentedSeq()
                    k2["verlauf"] = v2
                v2.append(fliess_map({"datum": heute, "status": "ersetzt", "wer": wer["name"], "durch": oid,
                                      "grund": texte.t(sprache_von(reise_dir), "inhalt.schreiben.verlauf.nicht_gewaehlt", oid=oid, titel=o["titel"])}))
                nicht_gewaehlt.append(x["id"])
    elif status in ("verworfen", "ersetzt"):
        # Wird die gewählte Option verworfen, kommen die dadurch ausgeschiedenen wieder ins Spiel
        for x in wr["optionen"]:
            if x["id"] != oid and x.get("status") == "ersetzt" and o.get("status") == "gewaehlt" \
                    and (x.get("verlauf") or [{}])[-1].get("durch") == oid and (x["verlauf"][-1].get("grund") or "").startswith(tuple(texte.inhaltswoerter("inhalt.schreiben.verlauf.nicht_gewaehlt_anfang"))):
                k2, _ = ding_finden(roh, x["id"])
                k2["verlauf"].append(fliess_map({"datum": heute, "status": "vorgeschlagen", "wer": wer["name"],
                                                 "grund": texte.t(sprache_von(reise_dir), "inhalt.schreiben.verlauf.wieder_offen", oid=oid)}))
                wieder.append(x["id"])
    routen_speichern(reise_dir, roh)
    frage_text = ""
    if wr.get("frage"):
        gewaehlt_danach = status == "gewaehlt" or any(x.get("status") == "gewaehlt" and x["id"] != oid for x in wr["optionen"])
        # Hängen weitere Wahlstellen an derselben Frage und ist dort noch nichts gewählt, bleibt die Frage offen
        noch_offen = [w["id"] for w in route.get("wahlstellen") or [] if w["id"] != vid and w.get("frage") == wr["frage"]
                      and not any(x.get("status") == "gewaehlt" for x in w.get("optionen") or [])]
        if status == "gewaehlt" and noch_offen:
            frage_text = S("schreiben.antwort.entscheiden.frage_offen", n=len(noch_offen), w1=wr["frage"], w2=", ".join(noch_offen))
            # Die KI im AI-Client fragt die Person danach einzeln, je Wahlstelle eine Auswahlfrage (Product Owner 29.10.2026)
            wahl = {w["id"]: w for w in route.get("wahlstellen") or []}
            frage_text += (S("schreiben.antwort.entscheiden.einzeln")
                           + " · ".join(f"{v} {wahl[v].get('titel', '')}: " + ", ".join(
                               f"{x['id']} {x.get('titel', '')}" for x in wahl[v].get("optionen") or []
                               if x.get("status") not in ("verworfen", "ersetzt")) for v in noch_offen) + ".")
        elif status == "gewaehlt":
            sp = sprache_von(reise_dir)
            ok = frage_status_setzen(reise_dir, wr["frage"], f"{texte.wort(sp, 'inhalt.frage.geklaert')} {texte.datum(heute, sp)}: {wer['name']}, {o['titel']} ({oid})")
            frage_text = S("schreiben.antwort.entscheiden.geklaert", w1=wr["frage"]) if ok else ""
        elif not gewaehlt_danach:
            ok = frage_status_setzen(reise_dir, wr["frage"], texte.wort(sprache_von(reise_dir), "inhalt.frage.offen"))
            frage_text = S("schreiben.antwort.entscheiden.danach_offen_frage", w1=vid, w2=wr["frage"]) if ok else S("schreiben.antwort.entscheiden.danach_offen", w1=vid)
    titel = S("schreiben.titel.entschieden_ersetzt", w1=oid, w2=o["titel"], w3=S("schreiben.wort." + status), w4=durch) if durch else S("schreiben.titel.entschieden", w1=oid, w2=o["titel"], w3=S("schreiben.wort." + status))
    text = (S("schreiben.antwort.entscheiden.kopf", w1=oid, w2=o["titel"], w3=vid, w4=wr.get("titel", "")) + S("schreiben.wort." + status)
            + (S("schreiben.antwort.entscheiden.ersetzt_durch", w1=durch) if durch else "")
            + S("schreiben.antwort.entscheiden.klammer", w1=wer["name"], w2=heute, w3=grund)
            + (S("schreiben.antwort.entscheiden.bisher", w1=", ".join(ersetzt)) if ersetzt else "") + (S("schreiben.antwort.entscheiden.nicht_gewaehlt", w1=", ".join(nicht_gewaehlt)) if nicht_gewaehlt else "")
            + (S("schreiben.antwort.entscheiden.wieder", w1=", ".join(wieder)) if wieder else "")
            + frage_text)
    if status in ("verworfen", "ersetzt"):
        text += S("schreiben.antwort.entscheiden.nicht_geloescht")
    return titel, text


def tag_aendern(reise_dir, wer, args, heute=None):
    """Einen Tag des Plans ändern: Titel, Text, Nacht (U-…, V-… oder leer), Strecken (E-…/V-…), Wahlstellen unterwegs (V-…),
    Aufenthalte ohne Nacht (A-…, in der Zeitleiste des Tags).
    Nur Organisator:innen (es ändert den Plan). -> (Titel, Text)."""
    tid = (text_wert(args, "ziel", pflicht=True, laenge=10) or "").strip()
    roh = routen_laden(reise_dir)
    t = (roh.get("tage") or {}).get(tid) if re.fullmatch(r"T-\d+", tid) else None
    if t is None:
        raise Ablehnung("schreiben.tag_aendern.1", tid=tid)
    geaendert = []
    for feld in ("titel", "text"):
        if args.get(feld) is not None:
            v = text_wert(args, feld, laenge=2000 if feld == "text" else 200) or ""
            if v != (t.get(feld) or ""):
                geaendert.append(wechsel(feld, t.get(feld) or "", v, quotiert=True))
                if v:
                    t[feld] = skalar(feld, v)
                else:
                    t.pop(feld, None)
    if args.get("nacht") is not None:
        n = str(args.get("nacht") or "").strip()
        if n and not re.fullmatch(r"(U-\d+|V-\d+|O-\d+)", n):
            raise Ablehnung("schreiben.tag_aendern.2")
        menge = {"U": "unterkuenfte", "V": "wahlstellen", "O": "orte"}.get(n[:1])
        if n and n not in (roh.get(menge) or {}):
            raise Ablehnung("schreiben.tag_aendern.3", n=n)
        if str(t.get("nacht") or "") != n:
            geaendert.append(wechsel("nacht", t.get("nacht") or "–", n or "–", quotiert=True))
            if n:
                t["nacht"] = n
            else:
                t.pop("nacht", None)
    for feld, muster, mengen in (("strecken", r"(E-\d+[A-Za-z]?|V-\d+)", {"E": "strecken", "V": "wahlstellen"}),
                                 ("wahl", r"V-\d+", {"V": "wahlstellen"}), ("aufenthalte", r"A-\d+", {"A": "aufenthalte"})):
        if args.get(feld) is None:
            continue
        liste = id_liste(args, feld, muster, roh) or []
        for x in liste:
            if x not in (roh.get(mengen[x[:1]]) or {}):
                raise Ablehnung("schreiben.id_liste.3", feld=feld, x=x)
        if list(t.get(feld) or []) != liste:
            geaendert.append(wechsel(feld, list(t.get(feld) or []), liste))
            if liste:
                t[feld] = fliess_map({feld: liste})[feld]
            else:
                t.pop(feld, None)
    if not geaendert:
        raise Ablehnung("schreiben.tag_aendern.4", tid=tid)
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    return S("schreiben.titel.geaendert", w1=tid, w2=kurz_namen(geaendert)), \
        f"{tid} {t.get('titel', '')}: " + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund else "")


# ---------- Wissen, Fragen schließen, Personen (inhalt/*.md, offene-fragen.md, reise.yaml) ----------
PERSON_MUSTER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


def uebersicht_wert(reise_dir, args):
    """Arten, deren Übersicht bei einem Abschnitt oder einer Kartenansicht steht (ADR-0007, Schritt e) aus der Anfrage -> Liste, [] zum
    Entfernen, None ohne Angabe. Jede Art muss es in der Reise geben."""
    if args.get("uebersicht") is None:
        return None
    if args["uebersicht"] in ("", []):
        return []
    liste = liste_wert(args, "uebersicht", laenge=60)
    arten = (route_stand(reise_dir).get("arten") or {})
    for x in liste:
        if x not in arten:
            raise Ablehnung("schreiben.uebersicht.art", x=x, w1=", ".join(arten) or "–")
    return liste


def uebersicht_setzen(reise_dir, wid, arten):
    """reise.json uebersichten: {W-…: [Art, …]} für einen Abschnitt setzen oder (leere Liste) entfernen -> Satz oder None (nichts geändert)."""
    import json
    p = Path(reise_dir) / "reise.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    u = cfg.get("uebersichten") or {}
    if list(u.get(wid) or []) == list(arten):
        return None
    if arten:
        u[wid] = list(arten)
    else:
        u.pop(wid, None)
    if u:
        cfg["uebersichten"] = u
    else:
        cfg.pop("uebersichten", None)
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return S("schreiben.antwort.uebersicht.gesetzt", w1=wid, w2=", ".join(arten)) if arten else S("schreiben.antwort.uebersicht.entfernt", w1=wid)


def wissen_schreiben(reise_dir, wer, args, heute=None):
    """Wissen in eigenen Worten mit Herkunft: ein neuer Abschnitt (W-ID aus ids.yaml, Zuordnung in reise.json) oder ein Absatz
    unter einem vorhandenen Abschnitt (abschnitt = W-ID oder titel). Herkunft (quelle) ist Pflicht und steht am Absatz. -> (Titel, Text)."""
    import json
    import neu
    heute = heute or datetime.date.today()
    text = text_wert(args, "text", pflicht=True, laenge=6000, absaetze=True)
    quelle = text_wert(args, "quelle", pflicht=True)
    gruppe = (text_wert(args, "gruppe", laenge=20) or "wissen").lower()
    if gruppe not in neu.GRUPPEN:
        raise Ablehnung("schreiben.kategorie_definieren.2", w1=', '.join(neu.GRUPPEN))
    datei = text_wert(args, "datei", laenge=80) or "inhalt/wissen.md"
    if not re.fullmatch(r"inhalt/[a-z0-9_-]+\.md", datei):
        raise Ablehnung("schreiben.wissen_schreiben.1")
    abschnitt = text_wert(args, "abschnitt", laenge=120)
    titel = text_wert(args, "titel", laenge=120)
    cfg = json.loads((Path(reise_dir) / "reise.json").read_text(encoding="utf-8"))
    zu = cfg.get("abschnitte") or {}
    uebersicht = uebersicht_wert(reise_dir, args)
    absatz = f"{text}\n\n" + texte.t(sprache_von(reise_dir), "inhalt.schreiben.herkunft.eingetragen", quelle=quelle, datum=texte.datum(heute, sprache_von(reise_dir)), wer=wer["name"])
    # Vorhandener Abschnitt? (W-ID oder Titel in reise.json)
    treffer = None
    for d_, titel_zu in zu.items():
        for t, (wid, _g) in titel_zu.items():
            if (abschnitt and abschnitt.upper() == wid) or (titel and titel == t and (not abschnitt)):
                treffer = (d_, t, wid)
    if abschnitt and treffer is None:
        raise Ablehnung("schreiben.wissen_schreiben.2", abschnitt=abschnitt)
    if treffer:
        d_, t, wid = treffer
        f = Path(reise_dir) / d_
        zeilen = f.read_text(encoding="utf-8").split("\n")
        start = next((i for i, z in enumerate(zeilen) if re.fullmatch(rf"## {re.escape(t)}\s*", z)), None)
        if start is None:
            raise Ablehnung("schreiben.wissen_schreiben.3", t=t, d_=d_)
        ende = next((i for i in range(start + 1, len(zeilen)) if zeilen[i].startswith("## ")), len(zeilen))
        while ende > start + 1 and not zeilen[ende - 1].strip():
            ende -= 1
        zeilen[ende:ende] = ["", *absatz.split("\n")]
        f.write_text("\n".join(zeilen).rstrip("\n") + "\n", encoding="utf-8")
        mehr = uebersicht_setzen(reise_dir, wid, uebersicht) if uebersicht is not None else None
        return (S("schreiben.titel.abschnitt_ergaenzt", w1=wid, w2=t),
                S("schreiben.antwort.abschnitt.ergaenzt_text", w1=wid, w2=t, w3=d_) + S("schreiben.antwort.herkunft", w1=quelle) + "." + (" " + mehr if mehr else ""))
    if not titel:
        raise Ablehnung("schreiben.wissen_schreiben.4")
    try:
        wid = neu.abschnitt(Path(reise_dir), titel, gruppe, datei, absatz)
    except neu.Fehler as e:
        raise Ablehnung(str(e))
    mehr = uebersicht_setzen(reise_dir, wid, uebersicht) if uebersicht is not None else None
    return (S("schreiben.titel.titel_angelegt", w1=wid, w2=titel),
            S("schreiben.antwort.abschnitt.neu", w1=wid, w2=titel, w3=datei, w4=gruppe) + S("schreiben.antwort.herkunft", w1=quelle) + "." + (" " + mehr if mehr else ""))


def frage_schliessen(reise_dir, wer, args, heute=None):
    """Eine offene Frage als geklärt oder entfallen eintragen (Organisator:innen), mit Ergebnis und Datum. -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    fid = (text_wert(args, "frage", pflicht=True, laenge=10) or "").upper()
    if not re.fullmatch(r"F-\d+", fid):
        raise Ablehnung("schreiben.ding_anlegen.5")
    ergebnis = text_wert(args, "ergebnis", pflicht=True)
    status = (text_wert(args, "status", laenge=20) or "geklaert").lower()
    if status not in ("geklaert", "entfaellt"):
        raise Ablehnung("schreiben.frage_schliessen.1")
    sp = sprache_von(reise_dir)   # der Status in offene-fragen.md steht in der Sprache der Reise
    wort = texte.wort(sp, "inhalt.frage.geklaert" if status == "geklaert" else "inhalt.frage.entfaellt")
    if not frage_status_setzen(reise_dir, fid, f"{wort} {texte.datum(heute, sp)}: {wer['name']}, {ergebnis}"):
        raise Ablehnung("schreiben.frage_schliessen.2", fid=fid)
    text = S("schreiben.antwort.frage.ist", w1=fid, w2=wort, w3=wer["name"], w4=heute, w5=ergebnis)
    if status == "entfaellt":
        text += S("schreiben.antwort.frage.nicht_geloescht")
    return f"{fid} {wort}", text


def person_schreiben(reise_dir, wer, args, heute=None):
    """Eine Person in reise.yaml anlegen oder ändern (Name, Rolle, reist, Notiz, von, bis). Niemand wird gestrichen: Wer
    ausscheidet, wird gast und reist nicht mehr (der Verlauf nennt ihn weiter). Höchstens die eigene Rolle vergeben. -> (Titel, Text)."""
    from reise import ROLLEN, darf, rolle_neu
    heute = heute or datetime.date.today()
    schluessel = (text_wert(args, "schluessel", pflicht=True, laenge=40) or "").lower()
    if not PERSON_MUSTER.match(schluessel):
        raise Ablehnung("schreiben.person_schreiben.1")
    p = Path(reise_dir) / "reise.yaml"
    if not p.exists():
        raise Ablehnung("schreiben.person_schreiben.2")
    roh = yaml_rund().load(p.read_text(encoding="utf-8"))
    personen = roh.get("personen")
    if personen is None:
        from ruamel.yaml.comments import CommentedMap
        personen = CommentedMap()
        roh["personen"] = personen
    vorhanden = personen.get(schluessel)
    name = text_wert(args, "name_der_person", laenge=80) or text_wert(args, "vorname", laenge=80)
    rolle = text_wert(args, "rolle", laenge=20)
    if rolle is not None:
        rolle = rolle_neu(rolle.lower())
        if rolle not in ROLLEN:
            raise Ablehnung("schreiben.person_schreiben.3", w1=', '.join(ROLLEN))
        if not darf(wer["rolle"], rolle):
            raise Ablehnung("schreiben.person_schreiben.4", w1=wer['rolle'])
    reist = bool_wert(args, "reist")
    notiz = text_wert(args, "notiz", laenge=300)
    if args.get("ausgeschieden"):   # der Konnektor meldet nur, dass die Person ausscheidet: die Notiz schreibt der Schreibweg in der Sprache der Reise
        sp = sprache_von(reise_dir)
        grund_ = args["ausgeschieden"] if isinstance(args["ausgeschieden"], str) else ""
        notiz = (texte.t(sp, "inhalt.schreiben.ausgeschieden", datum=texte.datum(heute, sp), wer=wer["name"]) + (f": {grund_}" if grund_ else ""))[:300]
    von, bis = (datum(args[f], f, "Person") if args.get(f) not in (None, "") else None for f in ("von", "bis"))
    geaendert = []
    if vorhanden is None:
        if not name:
            raise Ablehnung("schreiben.person_schreiben.5")
        d = {"name": name, "rolle": rolle or "mitwirkend", "reist": True if reist is None else reist}
        for k, v in (("notiz", notiz), ("von", von), ("bis", bis)):
            if v is not None:
                d[k] = v
        personen[schluessel] = fliess_map(d)
        titel = S("schreiben.titel.person_aufgenommen", w1=name, w2=schluessel, w3=d['rolle'])
        text = S("schreiben.antwort.person.aufgenommen", w1=name, w2=schluessel, w3=d["rolle"]) + S("schreiben.antwort.person.mit" if d["reist"] else "schreiben.antwort.person.nicht_mit")
    else:
        if vorhanden.get("rolle") == "organisator" and rolle not in (None, "organisator") and not darf(wer["rolle"], "organisator"):
            raise Ablehnung("schreiben.person_schreiben.6")
        for k, v in (("name", name), ("rolle", rolle), ("reist", reist), ("notiz", notiz), ("von", von), ("bis", bis)):
            if v is None or vorhanden.get(k) == v:
                continue
            geaendert.append(wechsel(k, vorhanden.get(k), v, quotiert=True) if vorhanden.get(k) is not None else S("schreiben.antwort.setzen_text", w1=k, w2=anzeige_text(v)))
            vorhanden[k] = skalar(k, v) if k != "name" else skalar("titel", v)
        if not geaendert:
            raise Ablehnung("schreiben.person_schreiben.7", w1=vorhanden.get('name', schluessel))
        titel = S("schreiben.titel.person_geaendert", w1=vorhanden.get('name', schluessel), w2=schluessel)
        text = S("schreiben.antwort.name_kopf", w1=vorhanden.get("name", schluessel)) + verbinden(geaendert, "; ") + "."
    import io
    out = io.StringIO()
    yaml_rund().dump(roh, out)
    p.write_text(out.getvalue(), encoding="utf-8")
    return titel, text


# ---------- Status und Einstellungen der Reise (reise.yaml), neue Reise ----------

def reise_yaml_laden(reise_dir):
    p = Path(reise_dir) / "reise.yaml"
    if not p.exists():
        raise Ablehnung("schreiben.person_schreiben.2")
    return p, yaml_rund().load(p.read_text(encoding="utf-8"))


def reise_yaml_speichern(p, roh):
    import io
    out = io.StringIO()
    yaml_rund().dump(roh, out)
    p.write_text(out.getvalue(), encoding="utf-8")


def reise_status_setzen(reise_dir, wer, args, heute=None):
    """Status der Reise (idee, planung, fest, unterwegs, danach, archiv) mit Verlaufseintrag (Datum, Wert, Person, Grund);
    nur Organisator:innen, in jedem Status (auch aus dem Archiv zurück). -> (Titel, Text)."""
    from reise import STATUS
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    heute = heute or datetime.date.today()
    wert = (text_wert(args, "status", pflicht=True, laenge=20) or "").lower()
    if wert not in STATUS:
        raise Ablehnung("schreiben.entscheiden.1", w1=', '.join(STATUS))
    grund = text_wert(args, "grund", pflicht=True)
    p, roh = reise_yaml_laden(reise_dir)
    st = roh.get("status")
    if not isinstance(st, dict):
        st = CommentedMap()
        roh["status"] = st
    alt = st.get("wert")
    if alt == wert:
        raise Ablehnung("schreiben.reise_status_setzen.1", wert=wert)
    st["wert"] = wert
    verlauf = st.get("verlauf")
    if verlauf is None:
        verlauf = CommentedSeq()
        st["verlauf"] = verlauf
    verlauf.append(fliess_map({"datum": heute, "wert": wert, "wer": wer["name"], "grund": grund}))
    reise_yaml_speichern(p, roh)
    return S("schreiben.titel.status", w1=alt or "–", w2=wert), S("schreiben.antwort.status.text", w1=wert, w2=alt or "–", w3=wer["name"], w4=heute, w5=grund)


def einstellung_setzen(reise_dir, wer, args, heute=None):
    """Einstellungen der Reise: bausteine (vollständige Liste), regeln (Name: Wert) und sprache (de, en …); nur Organisator:innen. Was gilt, prüft der
    Probebau (reise.py). -> (Titel, Text)."""
    from reise import ALTE_BAUSTEINE, BAUSTEINE, KERN, VORGABEN
    from ruamel.yaml.comments import CommentedMap
    p, roh = reise_yaml_laden(reise_dir)
    geaendert = []
    bausteine = args.get("bausteine")
    if bausteine is not None:
        liste = liste_wert({"b": bausteine}, "b", laenge=20) or []
        # Bausteine, die es nicht mehr gibt (tagesseiten, #214): still herausnehmen, nicht ablehnen, nicht schreiben
        liste = [b for b in liste if b not in ALTE_BAUSTEINE]
        fremd = [b for b in liste if b not in BAUSTEINE and b not in KERN]
        if fremd:
            raise Ablehnung("schreiben.einstellung_setzen.1", w1=', '.join(fremd), w2=', '.join(BAUSTEINE))
        liste = [b for b in dict.fromkeys(liste) if b not in KERN]
        if list(roh.get("bausteine") or []) != liste:
            geaendert.append(wechsel("bausteine", list(roh.get("bausteine") or []), liste))
            roh["bausteine"] = fliess_map({"bausteine": liste})["bausteine"]
    regeln = args.get("regeln")
    if regeln not in (None, {}):
        if not isinstance(regeln, dict):
            raise Ablehnung("schreiben.klammer.regeln")
        r = roh.get("regeln")
        if r is None:
            r = CommentedMap()
            roh["regeln"] = r
        for k, v in regeln.items():
            if k not in VORGABEN:
                raise Ablehnung("schreiben.einstellung_setzen.2", k=k, w2=', '.join(VORGABEN))
            if isinstance(v, str) and v.strip().lstrip("-").isdigit():
                v = int(v)
            if isinstance(VORGABEN[k], bool):   # ja/nein-Regeln (waechter_zahlung)
                if isinstance(v, str) and v.strip().lower() in ("true", "ja", "an", "false", "nein", "aus"):
                    v = v.strip().lower() in ("true", "ja", "an")
                if not isinstance(v, bool):
                    raise Ablehnung("schreiben.regeln.bool", k=k)
            if r.get(k) == v:
                continue
            geaendert.append(S("schreiben.antwort.einstellung.regel", w1=k, w2=anzeige_text(r.get(k, VORGABEN[k])), w3=anzeige_text(v)))
            r[k] = skalar(k, v) if isinstance(v, str) else v
    sprache = args.get("sprache")
    if sprache not in (None, ""):
        sprache = str(sprache).strip().lower()
        if not texte.gueltig(sprache):
            raise Ablehnung("schreiben.einstellung_setzen.3", sprache=sprache, w2=', '.join(texte.SPRACHEN))
        if roh.get("sprache") != sprache:   # ohne Feld ist jede Angabe eine Änderung
            geaendert.append(S("schreiben.antwort.einstellung.sprache",
                               w1=roh.get("sprache") or S("schreiben.antwort.einstellung.sprache_ungesetzt"), w2=sprache))
            roh["sprache"] = sprache
    if not geaendert:
        raise Ablehnung("schreiben.einstellung_setzen.4")
    grund = text_wert(args, "grund")
    reise_yaml_speichern(p, roh)
    return S("schreiben.titel.einstellungen", w1=kurz_namen(geaendert)), \
        S("schreiben.antwort.einstellungen.kopf") + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund else "") \
        + kartenstatus(reise_dir, roh)


def kartenstatus(reise_dir, roh):
    """Kartenstatus nach einer Änderung der Einstellungen (#233, K11): ist der Baustein Karte an, sagt die Antwort, ob die
    Karte entsteht, aus wie vielen Punkten, und welche Einträge keine Koordinaten haben (Probebau). -> Satz oder ""."""
    import karte
    if "karte" not in list(roh.get("bausteine") or []):
        return ""
    try:
        st = (route_stand(reise_dir) or {}).get("karte_status")
    except Ablehnung:
        return ""
    s = karte.status_satz(st)
    return S("schreiben.antwort.kartenstatus") + s if s else ""


def symbol_setzen(reise_dir, wer, args, heute=None):
    """App-Symbol der Reise (Issue #252): ein SVG als Text (svg) oder ein PNG als Base64 (png_base64, quadratisch, mindestens
    512 Pixel) wird medien/icon.svg oder medien/icon.png, das andere fällt weg; entfernen nimmt das eigene Symbol heraus, dann
    zeichnet der Generator wieder den Kurznamen. Nur Organisator:innen (Aktion einstellung). -> (Titel, Text)."""
    import base64
    import binascii
    import io
    import bauen
    svg = args.get("svg")
    png = args.get("png_base64")
    entfernen = bool_wert(args, "entfernen")
    gewaehlt = [x for x in (isinstance(svg, str) and svg.strip(), isinstance(png, str) and png.strip(), entfernen) if x]
    if len(gewaehlt) != 1:
        raise Ablehnung("schreiben.symbol.eines")
    medien = Path(reise_dir) / "medien"
    vorher = bauen.symbol_motiv(reise_dir)
    grund = text_wert(args, "grund")
    zusatz = S("schreiben.antwort.grund", w1=grund) if grund else ""
    if entfernen:
        if not vorher:
            raise Ablehnung("schreiben.symbol.keines")
        for n in bauen.SYMBOL_DATEIEN:
            (medien / n).unlink(missing_ok=True)
        return S("schreiben.titel.symbol_entfernt"), S("schreiben.antwort.symbol.entfernt") + zusatz
    if isinstance(svg, str) and svg.strip():
        inhalt = svg.strip().encode("utf-8")
        name = "icon.svg"
        if len(inhalt) > bauen.SYMBOL_MAX:
            raise Ablehnung("schreiben.symbol.zu_gross", kb=bauen.SYMBOL_MAX // 1024)
        if (fehler := bauen.svg_pruefen(svg.strip())):
            raise Ablehnung(fehler)
        try:
            bauen.icon_aus_svg(inhalt, 64)     # zur Probe rechnen: was CairoSVG nicht zeichnen kann, kommt nicht in die Reise
        except Exception:   # noqa: BLE001 – CairoSVG wirft je nach Fehler verschiedene Ausnahmen
            raise Ablehnung("schreiben.symbol.svg_kaputt")
        inhalt += b"\n"
    else:
        try:
            inhalt = base64.b64decode(re.sub(r"\s+", "", png.strip().split(",", 1)[-1] if png.strip().startswith("data:") else png.strip()),
                                      validate=True)
        except (binascii.Error, ValueError):
            raise Ablehnung("schreiben.symbol.png_base64")
        name = "icon.png"
        if len(inhalt) > bauen.SYMBOL_MAX:
            raise Ablehnung("schreiben.symbol.zu_gross", kb=bauen.SYMBOL_MAX // 1024)
        from PIL import Image, UnidentifiedImageError
        try:
            with Image.open(io.BytesIO(inhalt)) as im:
                art, (b, h) = im.format, im.size
                im.load()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise Ablehnung("schreiben.symbol.png_kaputt")
        if art != "PNG":
            raise Ablehnung("schreiben.symbol.png_kaputt")
        if b != h:
            raise Ablehnung("schreiben.symbol.png_quadrat", b=b, h=h)
        if b < bauen.SYMBOL_PNG_MIN:
            raise Ablehnung("schreiben.symbol.png_klein", b=b, min=bauen.SYMBOL_PNG_MIN)
    medien.mkdir(parents=True, exist_ok=True)
    (medien / name).write_bytes(inhalt)
    for n in bauen.SYMBOL_DATEIEN:
        if n != name:
            (medien / n).unlink(missing_ok=True)
    return (S("schreiben.titel.symbol_" + ("ersetzt" if vorher else "gesetzt"), w1=name),
            S("schreiben.antwort.symbol." + ("ersetzt" if vorher else "gesetzt"), w1=name) + zusatz)


def reise_anlegen(reisen_dir, wer, args, heute=None):
    """Neue Reise aus einer geprüften Anfrage der Claude-App (Konnektor reise_anlegen, daten.neue_reise) -> (Titel, Text, Ordner).
    Läuft auf Ebene des Repos, nicht einer Reise."""
    import neu
    import shutil
    auftrag = args.get("auftrag")
    if not isinstance(auftrag, dict) or not isinstance((auftrag.get("daten") or {}).get("neue_reise"), dict):
        raise Ablehnung("schreiben.reise_anlegen.1")
    n = auftrag["daten"]["neue_reise"]
    if not REISE_MUSTER.match(str(n.get("pfad") or "")):
        raise Ablehnung("schreiben.reise_anlegen.2")
    if (Path(reisen_dir) / n["pfad"]).exists():
        raise Ablehnung("schreiben.reise_anlegen.3", w1=n['pfad'])
    try:
        ordner = neu.aus_auftrag(Path(reisen_dir), auftrag, heute=heute)
    except neu.Fehler as e:
        raise Ablehnung(str(e))
    ok, meldungen = neu.pruefen(ordner)
    if not ok:
        shutil.rmtree(ordner, ignore_errors=True)
        raise Ablehnung("schreiben.bau.baut_nicht", meldungen=" ".join(meldungen))
    return S("schreiben.titel.reise_angelegt", w1=ordner.name), S("schreiben.antwort.reise.angelegt", w1=n["titel"], w2=ordner.name), ordner.name



# ---------- Buchung (B-…, #76, Product Owner 29.10.2026): eigenes Ding zu Unterkunft, Aufenthalt oder Strecke ----------

def zeitpunkt_wert(args, feld):
    """frist und ab einer Buchung (#472): Datum JJJJ-MM-TT oder Zeitpunkt JJJJ-MM-TTTHH:MM (auch mit Leerzeichen statt T)
    -> date, Text „JJJJ-MM-TTTHH:MM“, None (fehlt) oder "" (leer: entfernen)."""
    v = args.get(feld)
    if isinstance(v, str) and (m := re.fullmatch(r"\s*(\d{4}-\d{2}-\d{2})[T ](\d{1,2}):(\d{2})\s*", v)):
        try:
            datetime.date.fromisoformat(m.group(1))
            if int(m.group(2)) < 24 and int(m.group(3)) < 60:
                return f"{m.group(1)}T{int(m.group(2)):02d}:{m.group(3)}"
        except ValueError:
            pass
        raise Ablehnung("schreiben.zeitpunkt_wert.1", feld=feld)
    try:
        return datum_wert(args, feld)
    except Ablehnung:
        raise Ablehnung("schreiben.zeitpunkt_wert.1", feld=feld)


def datum_wert(args, feld):
    """Datum JJJJ-MM-TT aus der Anfrage -> date, None (fehlt) oder "" (leer: entfernen)."""
    v = args.get(feld)
    if v is None:
        return None
    if isinstance(v, datetime.date):
        return v
    s = str(v).strip()
    if s == "":
        return ""
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        raise Ablehnung("schreiben.datum_wert.1", feld=feld)


def buchung_fuer(args, roh, route):
    """fuer: eine oder mehrere IDs von Unterkünften, Aufenthalten oder Strecken, die es in der Reise gibt."""
    v = args.get("fuer")
    if isinstance(v, str):
        v = [x.strip() for x in v.split(",") if x.strip()]
    if not v or not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise Ablehnung("schreiben.buchung_fuer.1")
    bekannt = set(roh.get("unterkuenfte") or {}) | set(roh.get("aufenthalte") or {}) | set(roh.get("strecken") or {}) | set(route.get("strecken") or {})
    for x in v:
        if not re.fullmatch(r"(U|A)-\d+|E-\d+[A-Za-z]?", x) or x not in bekannt:
            raise Ablehnung("schreiben.buchung_fuer.2", x=x)
    return v


# Kurzfelder (Product Owner 10.11.2026, #476): Preis, Zahlung, ab/was, frist/was, vor Ort höchstens 60 Zeichen, Einzelheiten in die Notiz
BUCHUNG_TEXTE = {"nummer": 80, "bei": 120, "preis": 60, "bezahlt": 60, "frist_was": 60, "storno": 400, "notiz": MAX_TEXT, "ab_was": 60,
                 "anreise_ab": 40, "abreise_bis": 40, "vor_ort_zahlen": 60}
# Felder einer Buchung in Worten für Antwort und Verlauf (Menschen lesen Wörter, keine Schlüssel; Product Owner 29.10.2026)
BUCHUNG_WORTE = texte.gruppe("de", "schreiben.buchung")


def zahlung_wert(args):
    """zahlung (Zahlstand, #166) aus der Anfrage -> Schlüssel, "" (leer: entfernen) oder None (nicht angegeben)."""
    from routen import ZAHLUNG, ZAHLUNG_ALIAS, zahlung_schluessel, zahlung_wort
    if args.get("zahlung") is None:
        return None
    v = text_wert(args, "zahlung", laenge=20)
    if v is None:
        return ""
    z = zahlung_schluessel(v)
    if z is None:
        raise Ablehnung("schreiben.zahlung.ungueltig", w1=", ".join(ZAHLUNG), w2=", ".join(ZAHLUNG_ALIAS),
                        w3=verbinden([zahlung_wort(k) for k in ZAHLUNG], "; "))
    return z


def buchung_merkmal_defs(route, fuer):
    """Merkmale, die eine Buchung tragen darf (#166): die Merkmale der Buchungen aller Arten ihrer Dinge (plan/arten.yaml,
    buchung_merkmale), in der Reihenfolge der Definition. -> ({Merkmal: Definition}, [Arten])"""
    katalog = route.get("buchung_merkmale") or {}
    defs, arten = {}, []
    for x in fuer:
        d = (route.get("unterkuenfte") or {}).get(x) or (route.get("aufenthalte") or {}).get(x) or {}
        a = d.get("art") or ((route.get("strecken") or {}).get(x) or {}).get("art_schluessel")
        if a and a not in arten:
            arten.append(a)
            for k in katalog.get(a) or []:
                defs.setdefault(k["id"], k)
    return defs, arten


def buchung_merkmale_wert(args, route, fuer):
    """merkmale einer Buchung aus der Anfrage: {Merkmal: Wert} -> {Schlüssel: Wert oder "" (entfernen)} oder None.
    Erlaubt sind die Merkmale der Buchungen der Arten ihrer Dinge; Auswahl nur mit einem der Werte, Zahl als Zahl."""
    v = args.get("merkmale")
    if v is None:
        return None
    if not isinstance(v, dict):
        raise Ablehnung("schreiben.merkmale.form")
    defs, arten = buchung_merkmal_defs(route, fuer)
    if not defs:
        raise Ablehnung("schreiben.merkmale.keine", w1=", ".join(arten) or S("schreiben.merkmale.dieser_dinge"))
    aus = {}
    for k, w in v.items():
        key = str(k).strip().lower()
        if key not in defs:
            key = next((x for x, d in defs.items() if str(d.get("name", "")).casefold() == str(k).strip().casefold()), None)
        if key is None:
            moeglich = ", ".join(f"{x} ({d['name']})" for x, d in defs.items())
            raise Ablehnung("schreiben.merkmale.unbekannt", k=k, w2=", ".join(arten), moeglich=moeglich)
        d = defs[key]
        if w is None or (isinstance(w, str) and not w.strip()):
            aus[key] = ""
            continue
        if isinstance(w, (dict, list)):
            raise Ablehnung("schreiben.merkmale.wert_text", name=d["name"])
        typ = d.get("typ", "text")
        if typ == "auswahl":
            treffer = next((x for x in d.get("werte") or [] if str(x).casefold() == str(w).strip().casefold()), None)
            if treffer is None:
                raise Ablehnung("schreiben.merkmale.nicht_unter_werten", name=d["name"], w=w, werte=" | ".join(map(str, d.get("werte") or [])))
            aus[key] = treffer
        elif typ == "zahl":
            t = str(w).strip().replace(",", ".")
            try:
                z = float(t)
            except ValueError:
                raise Ablehnung("schreiben.merkmale.zahl", name=d["name"], w=w)
            aus[key] = int(z) if z.is_integer() else z
        else:
            aus[key] = " ".join(str(w).split())[:200]
    return aus


def merkmale_text(werte, defs):
    """Merkmale der Buchung für Antwort und Verlauf: „Ticketart: Sparpreis, Sitzplätze: 2“."""
    teile = []
    for k, v in werte.items():
        d = defs.get(k) or {}
        teile.append(f"{d.get('name', k)}: {v}" + (f" {d['einheit']}" if d.get("einheit") else ""))
    return ", ".join(teile)


def buchung_personen(args, reise_dir):
    """personen einer Buchung aus der Anfrage: Liste von Namen oder {Name: Angabe} -> dict oder None (nicht angegeben)."""
    v = args.get("personen")
    if v is None:
        return None
    if isinstance(v, str):
        v = [x.strip() for x in v.split(",") if x.strip()]
    if isinstance(v, list):
        v = {str(x): "" for x in v}
    if not isinstance(v, dict) or any(not str(k).strip() for k in v):
        raise Ablehnung("schreiben.klammer.personen")
    import bauen, tempfile
    with tempfile.TemporaryDirectory(prefix="frieda-probe-") as ziel:
        bekannt = {p.get("name", "").casefold() for p in (bauen.Bauer(reise_dir, ziel).eck.get("personen") or [])}
    fremd = [k for k in v if str(k).strip().casefold() not in bekannt]
    if fremd:
        raise Ablehnung("schreiben.buchung_personen.1", w1=', '.join(fremd))
    return {" ".join(str(k).split()): " ".join(str(x or "").split())[:200] for k, x in v.items()}


def buchung_preise(args, fuer):
    """preise einer Buchung: {ID aus fuer: Betrag} -> dict oder None."""
    v = args.get("preise")
    if v is None:
        return None
    if not isinstance(v, dict) or any(not isinstance(x, str) for x in v.values()):
        raise Ablehnung("schreiben.klammer.preise")
    fremd = [k for k in v if k not in fuer]
    if fremd:
        raise Ablehnung("schreiben.buchung_preise.1", w1=', '.join(fremd), w2=', '.join(fuer))
    return {k: " ".join(x.split())[:120] for k, x in v.items() if x.strip()}


def buchung_je_ding(args, fuer):
    """je_ding einer Buchung (#473): {ID aus fuer: {ab, ab_was, frist, frist_was}} -> dict (leer: entfernen) oder None (nicht angegeben).
    ab und frist wie bei der Buchung (Datum oder mit Uhrzeit), die Texte kurz."""
    from routen import JE_DING_FELDER
    v = args.get("je_ding")
    if v is None:
        return None
    if v == "":
        return {}
    if isinstance(v, str) and v.strip().startswith("{"):   # ein AI-Client mit älterer Werkzeugliste schickt das Objekt als Text
        try:
            v = json.loads(v)
        except ValueError:
            raise Ablehnung("schreiben.je_ding.form", w1=", ".join(JE_DING_FELDER))
    if not isinstance(v, dict) or any(not isinstance(x, dict) for x in v.values()):
        raise Ablehnung("schreiben.je_ding.form", w1=", ".join(JE_DING_FELDER))
    fremd = [k for k in v if k not in fuer]
    if fremd:
        raise Ablehnung("schreiben.buchung_preise.1", w1=", ".join(fremd), w2=", ".join(fuer))
    aus = {}
    englisch = {"available_from": "ab", "available_from_what": "ab_was", "deadline": "frist", "deadline_what": "frist_was"}
    for x, felder in v.items():
        felder = {englisch.get(f, f): w for f, w in felder.items()}
        falsch = [f for f in felder if f not in JE_DING_FELDER]
        if falsch:
            raise Ablehnung("schreiben.je_ding.form", w1=", ".join(JE_DING_FELDER))
        e = {}
        for f in JE_DING_FELDER:
            w = zeitpunkt_wert(felder, f) if f in ("ab", "frist") else text_wert(felder, f, laenge=BUCHUNG_TEXTE[f])
            if w not in (None, ""):
                e[f] = w
        if e:
            aus[x] = e
    return aus


def je_ding_map(je):
    """je_ding für die Datei: Zeile je Ding, darin Fließform."""
    from ruamel.yaml.comments import CommentedMap
    m = CommentedMap()
    for x, e in je.items():
        m[x] = fliess_map(e)
    return m


def je_ding_text(je):
    """Angaben je Ding als Satz in der Sprache der Person (nicht als fertiger Text, sonst bliebe er in der Vorgabesprache)."""
    return verbinden([S("schreiben.antwort.buchung.je_ding_teil", ding=x, felder=verbinden(
        [S("schreiben.antwort.buchung.je_ding_feld", wort=S("schreiben.buchung." + f), wert=w) for f, w in e.items()], ", "))
        for x, e in je.items()], "; ")


def ab_frist_pruefen(b):
    """Eine Angabe genau einmal (#476): „ab“ und „frist“ am selben Tag mit gleichem oder enthaltenem Text meinen dasselbe; für
    die Buchung und je Ding."""
    norm = lambda t: re.sub(r"\W+", "", str(t or "").casefold())
    for t in [b, *((b.get("je_ding") or {}).values())]:
        ab, fr = t.get("ab"), t.get("frist")
        if ab and fr and str(ab)[:10] == str(fr)[:10]:
            a, f = norm(t.get("ab_was")), norm(t.get("frist_was"))
            if a == f or (a and f and (a in f or f in a)):
                raise Ablehnung("schreiben.ab_frist_doppelt", datum=texte.Datum(datetime.date.fromisoformat(str(ab)[:10])))


def buchung_anlegen(reise_dir, wer, args, heute=None):
    """Eine Buchung anlegen (neue B-ID): zu welchen Dingen, Status, Nummer, Anbieter, Preis, Zahlstand, Frist, Stornoregel, Merkmale
    der Buchung, Herkunft. -> (Titel, Text)."""
    from routen import BUCHUNG_STATUS, zahlung_wort
    heute = heute or datetime.date.today()
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    fuer = buchung_fuer(args, roh, route)
    status = (text_wert(args, "status", laenge=20) or "gebucht").lower()
    if status not in BUCHUNG_STATUS:
        raise Ablehnung("schreiben.buchung_anlegen.1", w1=', '.join(BUCHUNG_STATUS))
    quelle = text_wert(args, "quelle", pflicht=True, laenge=600)
    zahlung = zahlung_wert(args)
    if zahlung == "erstattet" and status != "storniert":
        raise Ablehnung("schreiben.zahlung.erstattet")
    mk = {k: v for k, v in (buchung_merkmale_wert(args, route, fuer) or {}).items() if v != ""}
    d = {"fuer": fuer, "status": status}
    for k, laenge in BUCHUNG_TEXTE.items():
        if k == "notiz":
            continue
        if k == "bezahlt" and zahlung:   # der Zahlstand steht vor seinen Einzelheiten
            d["zahlung"] = zahlung
        if (v := text_wert(args, k, laenge=laenge)):
            d[k] = v
    for k in ("frist", "storno_bis", "gebucht_am", "ab", "anreise", "abreise"):
        v = zeitpunkt_wert(args, k) if k in ("frist", "ab") else datum_wert(args, k)
        if v:
            d[k] = v
    d.setdefault("gebucht_am", heute)
    pers, preise, je = buchung_personen(args, reise_dir), buchung_preise(args, fuer), buchung_je_ding(args, fuer)
    if pers:
        d["personen"] = pers
    if preise:
        d["preise"] = preise
    d["wer"] = wer["name"]
    d["quelle"] = quelle
    if (notiz := text_wert(args, "notiz")):
        d["notiz"] = notiz
    grund = text_wert(args, "grund")
    bid = neue_id(reise_dir, "B")
    ab_frist_pruefen({**d, "je_ding": je or {}})
    knoten = block_map(d)
    if je:   # Angaben je Ding (#473), vor wer
        knoten.insert(list(knoten).index("wer"), "je_ding", je_ding_map(je))
    if mk:   # Merkmale der Buchung in einer Zeile, vor wer
        knoten.insert(list(knoten).index("wer"), "merkmale", fliess_map(mk))
    from ruamel.yaml.comments import CommentedSeq
    verlauf = CommentedSeq()
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": "angelegt", **({"grund": grund} if grund else {})}))
    knoten["verlauf"] = verlauf
    roh.setdefault("buchungen", type(roh)())
    roh["buchungen"][bid] = knoten
    routen_speichern(reise_dir, roh)
    namen = ", ".join(f"{x} {buchung_dingname(roh, route, x)}" for x in fuer)
    titel = S("schreiben.titel.buchung_angelegt", w1=bid, w2=S("seite.buchung.status." + status), w3=namen)
    text = (S("schreiben.antwort.buchung.angelegt", w1=bid) + S("seite.buchung.status." + status) + S("schreiben.antwort.buchung.angelegt_fuer", w1=namen)
            + (S("schreiben.antwort.buchung.nr", w1=d["nummer"]) if d.get("nummer") else "")
            + (S("schreiben.antwort.buchung.bei", w1=d["bei"]) if d.get("bei") else "") + (S("schreiben.antwort.buchung.preis", w1=d["preis"]) if d.get("preis") else "")
            + (S("schreiben.antwort.buchung.zahlung", w1=zahlung_wort(zahlung)) if zahlung else "") + (f" ({d['bezahlt']})" if d.get("bezahlt") else "")
            + (f", {merkmale_text(mk, buchung_merkmal_defs(route, fuer)[0])}" if mk else "")
            + (S("schreiben.antwort.buchung.frist", w1=d["frist"]) + (f" ({d['frist_was']})" if d.get("frist_was") else "") if d.get("frist") else "")
            + (S("schreiben.antwort.buchung.storno", w1=d["storno"]) if d.get("storno") else "")
            + (S("schreiben.antwort.buchung.storno_bis", w1=d["storno_bis"]) if d.get("storno_bis") else "")
            + (S("schreiben.antwort.buchung.zeitraum", w1=d.get("anreise") or "…", w2=d.get("abreise") or "…") if d.get("anreise") or d.get("abreise") else "")
            + "".join(f", {S('schreiben.buchung.' + k)} {d[k]}" for k in ("anreise_ab", "abreise_bis", "vor_ort_zahlen") if d.get(k))
            + (S("schreiben.antwort.buchung.ab", w1=d["ab"]) + (f" ({d['ab_was']})" if d.get("ab_was") else "") if d.get("ab") else "")
            + (S("schreiben.antwort.buchung.preise", w1=", ".join(f"{k} {v}" for k, v in preise.items())) if preise else "")
            + (S("schreiben.antwort.buchung.je_ding", w1=je_ding_text(je)) if je else "")
            + (S("schreiben.antwort.buchung.reisende_liste", w1=", ".join(f"{k}{(' (' + v + ')') if v else ''}" for k, v in pers.items())) if pers else "")
            + S("schreiben.antwort.herkunft", w1=quelle) + ".")   # zum Beleg sagt der Konnektor etwas: er weiß, ob einer mitkam
    return titel, text


def buchung_dingname(roh, route, x):
    d = (roh.get("unterkuenfte") or {}).get(x) or (roh.get("aufenthalte") or {}).get(x) or {}
    return d.get("name") or ((route.get("strecken") or {}).get(x) or {}).get("titel") or ((roh.get("strecken") or {}).get(x) or {}).get("titel") or ""


def buchung_aendern(reise_dir, wer, args, heute=None):
    """Felder einer Buchung ändern (Status, Nummer, Frist, Storno …); jede Änderung bekommt einen Verlaufseintrag mit Person,
    Datum und Grund. Leerer Text entfernt ein Feld. -> (Titel, Text)."""
    from routen import BUCHUNG_STATUS, zahlung_wort
    heute = heute or datetime.date.today()
    bid = (text_wert(args, "ziel", pflicht=True, laenge=10) or "").strip().upper()
    if not re.fullmatch(r"B-\d+", bid):
        raise Ablehnung("schreiben.buchung_aendern.1")
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    knoten = (roh.get("buchungen") or {}).get(bid)
    if knoten is None:
        raise Ablehnung("schreiben.buchung_aendern.2", bid=bid)
    # Mitwirkende ändern nur, was sie selbst eingetragen haben (wer); Organisator:innen alles (Product Owner 29.10.2026, wie bei Belegen)
    if wer["rolle"] != "organisator" and str(knoten.get("wer") or "").strip().casefold() != wer["name"].casefold():
        raise Ablehnung("schreiben.buchung_aendern.3", bid=bid, w2=knoten.get('wer') or 'jemand anderes')
    grund = text_wert(args, "grund")
    status_vorher = knoten.get("status", "gebucht")
    geaendert, kurz = [], []   # ausführlich für die Antwort, kurz für den Verlauf

    def setze(feld, neu, wort=None):
        wort = wort or BUCHUNG_WORTE.get(feld, feld)
        wort_satz = S("schreiben.buchung." + feld) if feld in BUCHUNG_WORTE else wort   # in der Antwort in der Sprache der Person
        alt = knoten.get(feld)
        alt_t = texte.Datum(alt) if isinstance(alt, datetime.date) else (", ".join(alt) if isinstance(alt, list) else alt)
        neu_t = texte.Datum(neu) if isinstance(neu, datetime.date) else (", ".join(neu) if isinstance(neu, list) else neu)
        if neu in ("", None):
            if feld in knoten:
                geaendert.append(S("schreiben.antwort.buchung.entfernt", w1=wort_satz, w2=alt_t))
                kurz.append(S("schreiben.antwort.entfernt_feld", w1=wort_satz))
                del knoten[feld]
            return
        if alt_t == neu_t:
            return
        geaendert.append(S("schreiben.antwort.ding.wechsel", w1=wort_satz, w2=alt_t, w3=neu_t) if alt is not None else S("schreiben.antwort.ding.neu", w1=wort_satz, w2=neu_t))
        kurz.append(wort or feld)
        knoten[feld] = skalar(feld, neu) if isinstance(neu, str) else neu

    if "fuer" in args and args.get("fuer") is not None:
        setze("fuer", buchung_fuer(args, roh, route))
    if (status := text_wert(args, "status", laenge=20)) is not None:
        if status.lower() not in BUCHUNG_STATUS:
            raise Ablehnung("schreiben.buchung_anlegen.1", w1=', '.join(BUCHUNG_STATUS))
        if status.lower() == "storniert" and knoten.get("status", "gebucht") != "storniert" and not grund:
            raise Ablehnung("schreiben.buchung_aendern.4")
        setze("status", status.lower(), "Status")
    for k, laenge in BUCHUNG_TEXTE.items():
        if k in args and args.get(k) is not None:
            setze(k, text_wert(args, k, laenge=laenge) or "")
    if "quelle" in args and args.get("quelle") is not None:
        q = text_wert(args, "quelle", laenge=600)
        if not q:
            raise Ablehnung("schreiben.buchung_aendern.5")
        setze("quelle", q, "Herkunft")
    for k in ("frist", "storno_bis", "gebucht_am", "ab", "anreise", "abreise"):
        v = zeitpunkt_wert(args, k) if k in ("frist", "ab") else datum_wert(args, k)
        if v is not None:
            setze(k, v)
            if k == "ab" and v == "" and "ab_was" in knoten:   # ohne Ab-Termin kein „was ab dann geht“
                setze("ab_was", "")
    pers = buchung_personen(args, reise_dir)
    if pers is not None:
        if dict(knoten.get("personen") or {}) != pers:
            alt = knoten.get("personen")
            geaendert.append(S("schreiben.buchung.personen") + f" {', '.join(f'{k}{(' (' + v + ')') if v else ''}' for k, v in pers.items()) or '–'}")
            kurz.append("Reisende")
            (knoten.__setitem__("personen", block_map(pers)) if pers else knoten.pop("personen", None))
    fuer_jetzt = [knoten["fuer"]] if isinstance(knoten.get("fuer"), str) else list(knoten.get("fuer") or [])
    zahlung = zahlung_wert(args)
    if zahlung is not None:
        alt_z = knoten.get("zahlung")
        if zahlung != (alt_z or ""):
            if zahlung:
                geaendert.append(S("schreiben.antwort.buchung.zahlung_von", w1=zahlung_wort(alt_z), w2=zahlung_wort(zahlung)) if alt_z
                                 else S("schreiben.antwort.buchung.zahlung_neu", w1=zahlung_wort(zahlung)))
                if "zahlung" not in knoten and "bezahlt" in knoten:   # vor seinen Einzelheiten
                    knoten.insert(list(knoten).index("bezahlt"), "zahlung", zahlung)
                else:
                    knoten["zahlung"] = zahlung
            else:
                geaendert.append(S("schreiben.antwort.buchung.zahlung_weg", w1=zahlung_wort(alt_z)))
                del knoten["zahlung"]
            kurz.append("Zahlung")
    if knoten.get("zahlung") == "erstattet" and knoten.get("status", "gebucht") != "storniert":
        raise Ablehnung("schreiben.zahlung.erstattet")
    mk = buchung_merkmale_wert(args, route, fuer_jetzt)
    if mk is not None:
        defs = buchung_merkmal_defs(route, fuer_jetzt)[0]
        alt_mk = dict(knoten.get("merkmale") or {})
        neu_mk = {k: v for k, v in {**alt_mk, **mk}.items() if v != ""}
        if neu_mk != alt_mk:
            weg = [k for k in alt_mk if k not in neu_mk]
            anders = {k: v for k, v in neu_mk.items() if alt_mk.get(k) != v}
            geaendert.append(S("schreiben.antwort.buchung.merkmale_kopf", w1=verbinden(([merkmale_text(anders, defs)] if anders else [])
                                                     + [S("schreiben.antwort.buchung.merkmal_entfernt", w1=(defs.get(k) or {}).get("name", k)) for k in weg], "; ")))
            kurz.append(", ".join((defs.get(k) or {}).get("name", k) for k in [*anders, *weg]))
            if neu_mk and "merkmale" in knoten:
                knoten["merkmale"] = fliess_map(neu_mk)
            elif neu_mk:
                knoten.insert(list(knoten).index("wer") if "wer" in knoten else len(knoten), "merkmale", fliess_map(neu_mk))
            else:
                knoten.pop("merkmale", None)
    preise = buchung_preise(args, fuer_jetzt)
    if preise is not None and dict(knoten.get("preise") or {}) != preise:
        geaendert.append(S("schreiben.buchung.preise") + " " + (", ".join(f"{k} {v}" for k, v in preise.items()) or S("schreiben.antwort.buchung.preise_entfernt")))
        kurz.append("Preise je Ding")
        (knoten.__setitem__("preise", fliess_map(preise)) if preise else knoten.pop("preise", None))
    je = buchung_je_ding(args, fuer_jetzt)
    if je is not None:
        alt_je = {str(x): dict(v) for x, v in (knoten.get("je_ding") or {}).items()}
        if alt_je != je:
            geaendert.append(S("schreiben.buchung.je_ding") + " " + (je_ding_text(je) or S("schreiben.antwort.buchung.preise_entfernt")))
            kurz.append(S("schreiben.buchung.je_ding"))
            if not je:
                knoten.pop("je_ding", None)
            elif "je_ding" in knoten:
                knoten["je_ding"] = je_ding_map(je)
            else:
                knoten.insert(list(knoten).index("wer") if "wer" in knoten else len(knoten), "je_ding", je_ding_map(je))
    if not geaendert:
        raise Ablehnung("schreiben.buchung_aendern.6", bid=bid, w2=', '.join(BUCHUNG_TEXTE))
    ab_frist_pruefen(knoten)
    from ruamel.yaml.comments import CommentedSeq
    verlauf = knoten.get("verlauf")
    if verlauf is None:
        verlauf = CommentedSeq()
        knoten["verlauf"] = verlauf
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": lesbar(reise_dir, kurz), **({"grund": grund} if grund else {})}))
    routen_speichern(reise_dir, roh)
    fuer = knoten.get("fuer")
    fuer = [fuer] if isinstance(fuer, str) else list(fuer or [])
    namen = ", ".join(f"{x} {buchung_dingname(roh, route, x)}" for x in fuer)
    titel = S("schreiben.titel.geaendert", w1=bid, w2=verbinden(kurz, "; "))
    text = S("schreiben.antwort.buchung.kopf", w1=bid, w2=namen) + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund else "")
    if knoten.get("status") == "storniert" and status_vorher != "storniert":
        text += S("schreiben.antwort.buchung.nicht_geloescht")
    return titel, text


# ---------- Abgleich 29.10.2026 (docs/abgleich-2026-10-29.md, Paket 3): die Tür für alle Grundformen ----------
# Tag anlegen, feste Termine, Wahlstelle und Option ändern (auch favorisieren), Wissen ändern, Lesetext einer Strecke,
# Eckdaten der Reise, benannte Pläne, Merkmale zusammenführen, Arten einer anderen Reise übernehmen, Vorschlag zu einem Wunsch.

def route_liste_finden(roh, tid):
    """Die Liste in route: (oben oder in einem Teil), die den Tag tid enthält -> (Liste, Index) oder (None, None)."""
    for liste in [roh.get("route") or []] + [t.get("folge") for t in (roh.get("route") or []) if isinstance(t, dict) and isinstance(t.get("folge"), list)]:
        for i, el in enumerate(liste):
            if el == tid:
                return liste, i
    return None, None


def tag_anlegen(reise_dir, wer, args, heute=None):
    """Einen Tag anlegen (neue T-ID) und in die Route stellen: nach einem Tag (nach), vor einem (vor) oder am Ende; mit Titel,
    Text, Nacht, Strecken, Wahlstellen und Aufenthalten wie tag_aendern. Nur Organisator:innen (ändert den Plan). -> (Titel, Text)."""
    from ruamel.yaml.comments import CommentedSeq
    roh = routen_laden(reise_dir)
    d = {"titel": text_wert(args, "titel", pflicht=True, laenge=200)}
    if (t := text_wert(args, "text", laenge=2000)):
        d["text"] = t
    n = str(args.get("nacht") or "").strip()
    if n:
        if not re.fullmatch(r"(U-\d+|V-\d+|O-\d+)", n):
            raise Ablehnung("schreiben.tag_anlegen.1")
        if n not in (roh.get({"U": "unterkuenfte", "V": "wahlstellen", "O": "orte"}[n[0]]) or {}):
            raise Ablehnung("schreiben.tag_aendern.3", n=n)
    for feld, muster, mengen in (("strecken", r"(E-\d+[A-Za-z]?|V-\d+)", {"E": "strecken", "V": "wahlstellen"}),
                                 ("wahl", r"V-\d+", {"V": "wahlstellen"}), ("aufenthalte", r"A-\d+", {"A": "aufenthalte"})):
        liste = id_liste(args, feld, muster, roh)
        for x in liste or []:
            if x not in (roh.get(mengen[x[0]]) or {}) and not (feld == "strecken" and x.startswith("E-")):
                raise Ablehnung("schreiben.id_liste.3", feld=feld, x=x)
        if liste:
            d[feld] = liste
    nach, vor = text_wert(args, "nach", laenge=10), text_wert(args, "vor", laenge=10)
    if nach and vor:
        raise Ablehnung("schreiben.tag_anlegen.2")
    anker = nach or vor
    liste, i = (None, None)
    if anker:
        if not re.fullmatch(r"T-\d+", anker) or anker not in (roh.get("tage") or {}):
            raise Ablehnung("schreiben.tag_anlegen.3", w1='nach' if nach else 'vor', anker=anker)
        liste, i = route_liste_finden(roh, anker)
        if liste is None:
            raise Ablehnung("schreiben.tag_anlegen.4", anker=anker)
    tid = neue_id(reise_dir, "T")
    if n:
        d["nacht"] = n
    roh.setdefault("tage", type(roh)())
    roh["tage"][tid] = fliess_map(d)
    if liste is not None:
        liste.insert(i + (1 if nach else 0), tid)
        wo = S("schreiben.antwort.tag.nach" if nach else "schreiben.antwort.tag.vor", w1=anker)
    elif args.get("ohne_route"):
        wo = S("schreiben.antwort.tag.ohne_route")
    else:
        route = roh.get("route")
        if route is None:
            route = CommentedSeq()
            roh["route"] = route
        route.append(tid)
        wo = S("schreiben.antwort.tag.ende")
    routen_speichern(reise_dir, roh)
    return S("schreiben.titel.titel_angelegt", w1=tid, w2=d["titel"]), S("schreiben.antwort.tag.angelegt", w1=tid, w2=d["titel"]) + wo + S("schreiben.antwort.tag.pruefung")


def termin_setzen(reise_dir, wer, args, heute=None):
    """Feste Termine der Reise (fixpunkte in plan/routen.yaml): anlegen (datum, titel, ort, quelle), ändern (datum + alter Titel,
    neue Felder) oder entfernen (entfernen: true mit grund). Nur Organisator:innen. -> (Titel, Text)."""
    from ruamel.yaml.comments import CommentedSeq
    roh = routen_laden(reise_dir)
    datum_ = datum_wert(args, "datum")
    if not datum_:
        raise Ablehnung("schreiben.termin_setzen.1")
    titel = text_wert(args, "titel", pflicht=True, laenge=200)
    fix = roh.get("fixpunkte")
    if fix is None:
        fix = CommentedSeq()
        roh["fixpunkte"] = fix
    alt = next((f for f in fix if isinstance(f, dict) and f.get("datum") == datum_ and str(f.get("titel")) == titel), None)
    grund = text_wert(args, "grund")
    if bool_wert(args, "entfernen"):
        if alt is None:
            raise Ablehnung("schreiben.termin_setzen.2", w1=datum_.isoformat(), titel=titel)
        if not grund:
            raise Ablehnung("schreiben.termin_setzen.3")
        fix.remove(alt)
        routen_speichern(reise_dir, roh)
        return S("schreiben.titel.termin_entfernt", w1=texte.DatumKurz(datum_), w2=titel), S("schreiben.antwort.termin.entfernt", w1=datum_, w2=titel) + S("schreiben.antwort.grund", w1=grund)
    ort = text_wert(args, "ort", laenge=10)
    if ort and (not re.fullmatch(r"O-\d+", ort) or ort not in (roh.get("orte") or {})):
        raise Ablehnung("schreiben.termin_setzen.4", ort=ort)
    quelle = text_wert(args, "quelle", laenge=600)
    neuer_titel = text_wert(args, "neuer_titel", laenge=200)
    if alt is not None:
        geaendert = []
        if neuer_titel and neuer_titel != titel:
            geaendert.append(wechsel("titel", titel, neuer_titel, quotiert=True)); alt["titel"] = skalar("x", neuer_titel)
        if ort is not None and ort != alt.get("ort"):
            geaendert.append(S("schreiben.antwort.setzen", w1="ort", w2=ort or "–")); (alt.__setitem__("ort", ort) if ort else alt.pop("ort", None))
        if quelle and quelle != alt.get("quelle"):
            geaendert.append("Herkunft"); alt["quelle"] = skalar("x", quelle)
        if not geaendert:
            raise Ablehnung("schreiben.termin_setzen.5")
        routen_speichern(reise_dir, roh)
        return S("schreiben.titel.termin_geaendert", w1=texte.DatumKurz(datum_)), S("schreiben.antwort.termin.kopf", w1=datum_) + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund else "")
    if not quelle:
        raise Ablehnung("schreiben.termin_setzen.6")
    d = {"datum": datum_}
    if ort:
        d["ort"] = ort
    d["titel"] = titel
    d["quelle"] = quelle
    fix.append(fliess_map(d))
    routen_speichern(reise_dir, roh)
    return S("schreiben.titel.termin_angelegt", w1=texte.DatumKurz(datum_), w2=titel), S("schreiben.antwort.termin.angelegt", w1=datum_, w2=titel) + (S("schreiben.antwort.ding.in", w1=ort) if ort else "") + S("schreiben.antwort.herkunft", w1=quelle) + "."


def wahlstelle_aendern(reise_dir, wer, args, heute=None):
    """Felder einer Wahlstelle ändern: titel, text, an, frage, wann, art (Art der Dinge), stufen (Merkmal: Stufe für diese
    Wahlstelle). Nur Organisator:innen (sie bestimmt Vergleich und Entscheidung). -> (Titel, Text)."""
    from routen import stufe_schluessel
    from ruamel.yaml.comments import CommentedMap
    vid = (text_wert(args, "ziel", pflicht=True, laenge=10) or "").strip()
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    w = (roh.get("wahlstellen") or {}).get(vid) if re.fullmatch(r"V-\d+", vid) else None
    if w is None:
        raise Ablehnung("schreiben.wahlstelle_aendern.1", vid=vid)
    arten = route.get("arten") or {}
    geaendert = []
    for feld, laenge in (("titel", 200), ("text", 2000)):
        if args.get(feld) is not None:
            v = text_wert(args, feld, laenge=laenge) or ""
            if feld == "titel" and not v:
                raise Ablehnung("schreiben.wahlstelle_aendern.2")
            if v != (w.get(feld) or ""):
                geaendert.append(wechsel(feld, w.get(feld) or "", v, quotiert=True))
                (w.__setitem__(feld, skalar(feld, v)) if v else w.pop(feld, None))
    if args.get("wann") is not None:
        wann = str(args.get("wann") or "").strip().lower()
        if wann not in ("planung", "unterwegs"):
            raise Ablehnung("schreiben.wahlstelle_aendern.3")
        alt = w.get("wann") or (w.get("art") if w.get("art") in ("planung", "unterwegs") else "planung")
        if wann != alt:
            geaendert.append(wechsel("wann", alt, wann))
            if w.get("art") in ("planung", "unterwegs"):
                del w["art"]
            w["wann"] = wann
    if args.get("art") is not None:
        art = str(args.get("art") or "").strip().lower()
        if art and art not in arten:
            raise Ablehnung("schreiben.wahlstelle_aendern.4", w1=', '.join(arten) or 'keine')
        alt = w.get("bereich") or (w.get("art") if w.get("art") not in ("planung", "unterwegs") else None)
        if (art or None) != alt:
            geaendert.append(S("schreiben.antwort.ding.pfeil", w1="art", w2=alt or "–", w3=art or S("schreiben.antwort.plan.aus_optionen")))
            w.pop("bereich", None)
            if w.get("art") not in ("planung", "unterwegs"):
                w.pop("art", None)
            if art:
                w["art"] = art
    if args.get("an") is not None:
        an = id_liste(args, "an", r"(T-\d+|E-\d+[A-Za-z]?|U-\d+|A-\d+|O-\d+|V-\d+|W-\d+(\.[\w-]+)?)", roh) or []
        for x in an:
            menge = {"T": "tage", "E": "strecken", "U": "unterkuenfte", "A": "aufenthalte", "O": "orte", "V": "wahlstellen"}.get(x[0])
            if menge and x not in (roh.get(menge) or {}):
                raise Ablehnung("schreiben.wahlstelle_anlegen.3", x=x)
        if list(w.get("an") or []) != an:
            geaendert.append(wechsel("an", list(w.get("an") or []), an))
            (w.__setitem__("an", fliess_map({"an": an})["an"]) if an else w.pop("an", None))
    if args.get("frage") is not None:
        f = str(args.get("frage") or "").strip()
        if f and not re.fullmatch(r"F-\d+", f):
            raise Ablehnung("schreiben.wahlstelle_aendern.5")
        if f != (w.get("frage") or ""):
            geaendert.append(wechsel("frage", w.get("frage") or "–", f or "–"))
            (w.__setitem__("frage", f) if f else w.pop("frage", None))
    stufen = args.get("stufen")
    if stufen not in (None, {}):
        if not isinstance(stufen, dict):
            raise Ablehnung("schreiben.klammer.stufen")
        wr = next((x for x in route.get("wahlstellen") or [] if x["id"] == vid), {})
        bekannt = {k["id"] for k in wr.get("kriterien") or []}
        mk = w.get("merkmale")
        if mk is None:
            mk = CommentedMap()
            w["merkmale"] = mk
        for k, st in stufen.items():
            k = str(k).lower()
            if k not in bekannt:
                raise Ablehnung("schreiben.wahlstelle_aendern.6", k=k, w2=', '.join(sorted(bekannt)) or 'keine')
            s = stufe_schluessel(str(st))
            if s is None:
                raise Ablehnung("schreiben.wahlstelle_aendern.7", st=st, k=k)
            alt = (mk.get(k) or {}).get("stufe") if isinstance(mk.get(k), dict) else None
            if alt != s:
                geaendert.append(S("schreiben.antwort.ding.pfeil", w1=S("schreiben.antwort.merkmal.stufe_kopf_geaendert") + f"{k}:", w2=alt or S("schreiben.antwort.art.wie_art"), w3=s))
                mk[k] = fliess_map({"stufe": s})
    if not geaendert:
        raise Ablehnung("schreiben.wahlstelle_aendern.8", vid=vid)
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    return S("schreiben.titel.geaendert", w1=vid, w2=kurz_namen(geaendert)), S("schreiben.antwort.wahlstelle.kopf", w1=vid, w2=w.get("titel", "")) + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund else "")


def option_inhalt_ok(neu):
    """Was eine Möglichkeit enthält: Unterkünfte, Strecken, Aufenthalte ohne Nacht, Orte oder ein Reiseteil (folge).
    Unterkünfte und folge stehen allein; Strecken, Aufenthalte und Orte dürfen beliebig zusammen stehen (Gipfelalternative:
    Weg und Rast; Ort mit Museum darin, #353)."""
    sorten = {k for k, v in neu.items() if v}
    return len(sorten) <= 1 or sorten <= {"strecken", "aufenthalte", "orte"}


def option_aendern(reise_dir, wer, args, heute=None):
    """Felder einer Option ändern: titel, text, plus, minus, erfordert, schliesst_aus, ausloeser, siehe, unterkuenfte, strecken,
    aufenthalte, orte, folge, quelle; favorisieren (favorisiert: true mit grund) als Verlaufseintrag (Mitwirkende dürfen; gewählt, verworfen,
    ersetzt nur mit entscheiden). -> (Titel, Text)."""
    from reise import darf
    heute = heute or datetime.date.today()
    oid = (text_wert(args, "ziel", pflicht=True, laenge=12) or "").strip()
    if not re.fullmatch(r"V-\d+\.[a-z]", oid):
        raise Ablehnung("schreiben.option_aendern.1")
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, oid)
    if knoten is None:
        raise Ablehnung("schreiben.entscheiden.3", oid=oid)
    vid = oid.split(".")[0]
    geaendert = []
    for feld, laenge in (("titel", 200), ("text", 2000), ("ausloeser", 600), ("quelle", 600)):
        if args.get(feld) is not None:
            v = text_wert(args, feld, laenge=laenge) or ""
            if feld in ("titel", "quelle") and not v:
                raise Ablehnung("schreiben.option_aendern.2", feld=feld)
            if v != (knoten.get(feld) or ""):
                geaendert.append(wechsel(feld, knoten.get(feld) or "", v, quotiert=True))
                (knoten.__setitem__(feld, skalar(feld, v)) if v else knoten.pop(feld, None))
    for feld in ("plus", "minus"):
        if args.get(feld) is not None:
            l = liste_wert(args, feld, laenge=10) or []
            if list(knoten.get(feld) or []) != l:
                geaendert.append(wechsel(feld, list(knoten.get(feld) or []), l))
                (knoten.__setitem__(feld, fliess_map({feld: l})[feld]) if l else knoten.pop(feld, None))
    if args.get("siehe") is not None:
        s = str(args.get("siehe") or "").strip()
        if s and not ID_MUSTER.match(s):
            raise Ablehnung("schreiben.option_aendern.3")
        if s != (knoten.get("siehe") or ""):
            geaendert.append(wechsel("siehe", knoten.get("siehe") or "–", s or "–"))
            (knoten.__setitem__("siehe", s) if s else knoten.pop("siehe", None))
    optionen_ids = {x["id"] for w in route.get("wahlstellen") or [] for x in w["optionen"]}
    for feld in ("erfordert", "schliesst_aus"):
        if args.get(feld) is not None:
            l = id_liste(args, feld, r"V-\d+\.[a-z]", roh) or []
            fehlt = [x for x in l if x not in optionen_ids]
            if fehlt or any(x.startswith(vid + ".") for x in l):
                raise Ablehnung("schreiben.option_aendern.4", feld=feld, w2=', '.join(fehlt) or 'eine Option derselben Wahlstelle')
            if list(knoten.get(feld) or []) != l:
                geaendert.append(wechsel(feld, list(knoten.get(feld) or []), l))
                (knoten.__setitem__(feld, fliess_map({feld: l})[feld]) if l else knoten.pop(feld, None))
    inhalt = {}
    for feld, muster, menge in (("unterkuenfte", r"U-\d+", "unterkuenfte"), ("strecken", r"E-\d+[A-Za-z]?", "strecken"), ("folge", r"T-\d+", "tage"),
                                ("aufenthalte", r"A-\d+", "aufenthalte"), ("orte", r"O-\d+", "orte")):
        if args.get(feld) is not None:
            inhalt[feld] = id_liste(args, feld, muster, roh, menge) or []
    if inhalt:
        neu = {f: (inhalt[f] if f in inhalt else list(knoten.get(f) or [])) for f in ("unterkuenfte", "strecken", "folge", "aufenthalte", "orte")}
        if not option_inhalt_ok(neu):
            raise Ablehnung("schreiben.option_aendern.5")
        for f, l in inhalt.items():
            if list(knoten.get(f) or []) != l:
                geaendert.append(wechsel(f, list(knoten.get(f) or []), l))
                (knoten.__setitem__(f, fliess_map({f: l})[f]) if l else knoten.pop(f, None))
    grund = text_wert(args, "grund")
    if bool_wert(args, "favorisiert"):
        if not grund:
            raise Ablehnung("schreiben.option_aendern.6")
        from routen import UNGUELTIG
        o = next((x for w in route.get("wahlstellen") or [] for x in w["optionen"] if x["id"] == oid), {})
        if o.get("status") in UNGUELTIG or o.get("status") == "gewaehlt":
            raise Ablehnung("schreiben.option_aendern.7", oid=oid, w2=o.get('status'))
        from ruamel.yaml.comments import CommentedSeq
        verlauf = knoten.get("verlauf")
        if verlauf is None:
            verlauf = CommentedSeq()
            knoten["verlauf"] = verlauf
        verlauf.append(fliess_map({"datum": heute, "status": "favorisiert", "wer": wer["name"], "grund": grund}))
        geaendert.append(S("schreiben.antwort.option.favorisiert", w1=wer["name"]))
    if not geaendert:
        raise Ablehnung("schreiben.option_aendern.8", oid=oid)
    routen_speichern(reise_dir, roh)
    return S("schreiben.titel.geaendert", w1=oid, w2=kurz_namen(geaendert)), S("schreiben.antwort.option.kopf", w1=oid, w2=knoten.get("titel", "")) + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund and not bool_wert(args, "favorisiert") else "")


def abschnitt_finden(reise_dir, wid):
    """-> (Datei, Titel) eines W-Abschnitts aus reise.json oder (None, None)."""
    import json
    cfg = json.loads((Path(reise_dir) / "reise.json").read_text(encoding="utf-8"))
    for d_, titel_zu in (cfg.get("abschnitte") or {}).items():
        for t, (w, _g) in titel_zu.items():
            if w == wid:
                return d_, t
    return None, None


def abschnitt_grenzen(zeilen, titel):
    """-> (start, ende) der Zeilen eines ## Abschnitts (Überschrift eingeschlossen, ohne Leerzeilen am Ende) oder (None, None)."""
    start = next((i for i, z in enumerate(zeilen) if re.fullmatch(rf"## {re.escape(titel)}\s*", z)), None)
    if start is None:
        return None, None
    ende = next((i for i in range(start + 1, len(zeilen)) if zeilen[i].startswith("## ")), len(zeilen))
    while ende > start + 1 and not zeilen[ende - 1].strip():
        ende -= 1
    return start, ende


def wissen_aendern(reise_dir, wer, args, heute=None):
    """Einen W-Abschnitt berichtigen: text ersetzt den Inhalt des Abschnitts (Herkunft Pflicht), neuer_titel benennt ihn um
    (die ID bleibt, reise.json wird nachgezogen). Mit grund. -> (Titel, Text)."""
    import json
    heute = heute or datetime.date.today()
    wid = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip().upper()
    if not re.fullmatch(r"W-\d+", wid):
        raise Ablehnung("schreiben.wissen_aendern.1")
    datei, titel = abschnitt_finden(reise_dir, wid)
    if datei is None:
        raise Ablehnung("schreiben.wissen_aendern.2", wid=wid)
    f = Path(reise_dir) / datei
    zeilen = f.read_text(encoding="utf-8").split("\n")
    start, ende = abschnitt_grenzen(zeilen, titel)
    if start is None:
        raise Ablehnung("schreiben.wissen_aendern.3", titel=titel, datei=datei)
    text = text_wert(args, "text", laenge=12000, absaetze=True)
    neuer_titel = text_wert(args, "neuer_titel", laenge=120)
    grund = text_wert(args, "grund", pflicht=True)
    uebersicht = uebersicht_wert(reise_dir, args)
    geaendert = []
    if uebersicht is not None and (satz := uebersicht_setzen(reise_dir, wid, uebersicht)):
        geaendert.append(satz)
    if text:
        quelle = text_wert(args, "quelle", pflicht=True)
        absatz = f"{text}\n\n" + texte.t(sprache_von(reise_dir), "inhalt.schreiben.herkunft.berichtigt", quelle=quelle, datum=texte.datum(heute, sprache_von(reise_dir)), wer=wer["name"], grund=grund)
        zeilen[start + 1:ende] = ["", *absatz.split("\n")]
        geaendert.append(S("schreiben.antwort.abschnitt.inhalt_ersetzt"))
    if neuer_titel and neuer_titel != titel:
        if neuer_titel.startswith("#") or "|" in neuer_titel:
            raise Ablehnung("schreiben.wissen_aendern.4")
        zeilen[start] = f"## {neuer_titel}"
        p = Path(reise_dir) / "reise.json"
        cfg = json.loads(p.read_text(encoding="utf-8"))
        zu = cfg["abschnitte"][datei]
        if neuer_titel in zu:
            raise Ablehnung("schreiben.wissen_aendern.5", neuer_titel=neuer_titel, datei=datei)
        cfg["abschnitte"][datei] = {(neuer_titel if t == titel else t): v for t, v in zu.items()}
        p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        geaendert.append(wechsel("titel", titel, neuer_titel, quotiert=True))
    if not geaendert:
        raise Ablehnung("schreiben.wissen_aendern.6")
    f.write_text("\n".join(zeilen).rstrip("\n") + "\n", encoding="utf-8")
    return S("schreiben.titel.geaendert", w1=wid, w2=verbinden(geaendert, "; ")), S("schreiben.antwort.abschnitt.kopf", w1=wid, w2=neuer_titel or titel, w3=datei) + verbinden(geaendert, "; ") + S("schreiben.antwort.abschnitt.grund_ende", w1=grund)


def rubriken_pruefen(text, rubriken, ziel):
    """Jedes fette Stichwort am Absatzanfang muss eine Rubrik der Gliederung sein, wenn die Art eine hat (docs/ontologie.md)."""
    if not rubriken:
        return
    namen = {r["name"].casefold() for r in rubriken}
    fremd = [w for w in re.findall(r"^\*\*([^*]{1,60})\*\*", text, flags=re.M) if w.strip().rstrip(".:").casefold() not in namen]
    if fremd:
        raise Ablehnung("schreiben.lesetext_schreiben.4", w1=fremd[0].strip().rstrip('.:'), w2=', '.join(r['name'] for r in rubriken), eid=ziel)


def lesetext_schreiben(reise_dir, wer, args, heute=None):
    """Den Lesetext einer Etappe (Abschnitt „Zusammenfassung“ im Etappen-Dossier, Ebene „Der Weg“) oder eines Orts (Text unter
    „## O-… Name“ im Ortsdossier, ADR-0008, #334) schreiben oder ersetzen, gegliedert nach den Rubriken der Art (je Absatz
    „**Rubrik.** …“); Herkunft Pflicht. -> (Titel, Text)."""
    import json
    heute = heute or datetime.date.today()
    eid = (text_wert(args, "ziel", pflicht=True, laenge=12) or "").strip().upper()
    if re.fullmatch(r"O-\d+[A-Za-z]?", eid):
        return ort_lesetext_schreiben(reise_dir, wer, args, eid, heute)
    if re.fullmatch(r"[UA]-\d+[A-Za-z]?", eid):
        return ding_lesetext_schreiben(reise_dir, wer, args, eid, heute)
    if not re.fullmatch(r"E-\d+[A-Za-z]?", eid):
        raise Ablehnung("schreiben.lesetext_schreiben.1")
    text = text_wert(args, "text", pflicht=True, laenge=12000, absaetze=True)
    quelle = text_wert(args, "quelle", pflicht=True)
    cfg = json.loads((Path(reise_dir) / "reise.json").read_text(encoding="utf-8"))
    d_rel = cfg.get("etappen_dossier")
    if not d_rel or not (Path(reise_dir) / d_rel).exists():
        raise Ablehnung("schreiben.lesetext_schreiben.2")
    import bauen
    f = Path(reise_dir) / d_rel
    zeilen = f.read_text(encoding="utf-8").split("\n")
    start = None
    for i, z in enumerate(zeilen):   # der Abschnitt der Strecke: Überschrift „## E-03 Name“ (#269)
        m = z.startswith("## ") and bauen.STRECKE_UEBERSCHRIFT.match(z[3:].strip())
        if m and m.group(1).upper() == eid:
            start = i
            break
    if start is None:
        raise Ablehnung("schreiben.lesetext_schreiben.3", eid=eid, d_rel=d_rel)
    ende = next((i for i in range(start + 1, len(zeilen)) if zeilen[i].startswith("## ")), len(zeilen))
    # Rubriken der Art prüfen: jedes fette Stichwort am Absatzanfang muss eine Rubrik sein, wenn die Art eine Gliederung hat
    route = route_stand(reise_dir)
    st = (route.get("strecken") or {}).get(eid) or {}
    rubriken_pruefen(text, (((route.get("arten") or {}).get(st.get("art_schluessel"))) or {}).get("lesetext") or [], eid)
    absatz = f"{text}\n\n" + texte.t(sprache_von(reise_dir), "inhalt.schreiben.herkunft.geschrieben", quelle=quelle, datum=texte.datum(heute, sprache_von(reise_dir)), wer=wer["name"])
    zs = next((i for i in range(start + 1, ende) if re.fullmatch(r"###\s+Zusammenfassung\s*", zeilen[i])), None)
    if zs is not None:
        ze = next((i for i in range(zs + 1, ende) if zeilen[i].startswith("### ")), ende)
        while ze > zs + 1 and not zeilen[ze - 1].strip():
            ze -= 1
        zeilen[zs + 1:ze] = *absatz.split("\n"),
        was = "ersetzt"   # Schlüssel schreiben.antwort.lesetext.<was>
    else:
        # vor dem ersten Unterabschnitt, nach der Einleitung (kursive Zeile) der Etappe
        erster = next((i for i in range(start + 1, ende) if zeilen[i].startswith("### ")), ende)
        zeilen[erster:erster] = ["### Zusammenfassung", *absatz.split("\n"), ""]
        was = "angelegt"
    f.write_text("\n".join(zeilen).rstrip("\n") + "\n", encoding="utf-8")
    return S("schreiben.titel.lesetext_" + was, w1=eid), S("schreiben.antwort.lesetext." + was, w1=eid, w2=d_rel) + S("schreiben.antwort.herkunft", w1=quelle) + "."


def ding_lesetext_schreiben(reise_dir, wer, args, did, heute):
    """Lesetext einer Unterkunft oder eines Aufenthalts (#334): Feld lesetext am Ding in routen.yaml ({text, quelle,
    geschrieben, wer}); die Karte des Dings an seiner Heimat zeigt ihn. Rubriken der Art des Dings. Ersetzt einen alten Text."""
    text = text_wert(args, "text", pflicht=True, laenge=12000, absaetze=True)
    quelle = text_wert(args, "quelle", pflicht=True)
    route = route_stand(reise_dir)
    d = (route.get("unterkuenfte" if did.startswith("U-") else "aufenthalte") or {}).get(did)
    if d is None:
        raise Ablehnung("schreiben.lesetext_schreiben.ding_fehlt", did=did)
    rubriken_pruefen(text, (((route.get("arten") or {}).get(d.get("art"))) or {}).get("lesetext") or [], did)
    roh = routen_laden(reise_dir)
    knoten, _ = ding_finden(roh, did)
    if knoten is None:
        raise Ablehnung("schreiben.lesetext_schreiben.ding_fehlt", did=did)
    from ruamel.yaml.scalarstring import LiteralScalarString
    was = "ersetzt" if knoten.get("lesetext") else "angelegt"
    knoten["lesetext"] = {"text": LiteralScalarString(text.rstrip("\n") + "\n") if "\n" in text else text, "quelle": quelle,
                          "geschrieben": heute, "wer": wer["name"]}
    routen_speichern(reise_dir, roh)
    return (S("schreiben.titel.lesetext_" + was, w1=did),
            S("schreiben.antwort.lesetext.ding_" + was, w1=f"{did} {d.get('name') or ''}".strip()) + S("schreiben.antwort.herkunft", w1=quelle) + ".")


FUSSNOTE = re.compile(r"^\[\^[^\]]+\]:")


def ort_lesetext_schreiben(reise_dir, wer, args, oid, heute):
    """Lesetext eines Orts: der Text unter „## O-… Name“ vor dem ersten Unterabschnitt im Ortsdossier (reise.json orte_dossiers),
    auf der Ortsseite oben. Unterabschnitte (### …) und Fußnoten bleiben. Fehlt der Abschnitt, kommt er ans Ende des ersten
    Ortsdossiers; fehlt das Dossier, entsteht inhalt/orte.md und wird in reise.json eingetragen. Rubriken der Art des Orts."""
    import json
    text = text_wert(args, "text", pflicht=True, laenge=12000, absaetze=True)
    quelle = text_wert(args, "quelle", pflicht=True)
    route = route_stand(reise_dir)
    o = (route.get("orte") or {}).get(oid)
    if o is None:
        raise Ablehnung("schreiben.lesetext_schreiben.ort_fehlt", oid=oid)
    rubriken_pruefen(text, (((route.get("arten") or {}).get(o.get("art"))) or {}).get("lesetext") or [], oid)
    absatz = f"{text}\n\n" + texte.t(sprache_von(reise_dir), "inhalt.schreiben.herkunft.geschrieben", quelle=quelle, datum=texte.datum(heute, sprache_von(reise_dir)), wer=wer["name"])
    p_cfg = Path(reise_dir) / "reise.json"
    cfg = json.loads(p_cfg.read_text(encoding="utf-8"))
    dossiers = [d for d in (cfg.get("orte_dossiers") or []) if isinstance(d, str)]
    kopf = re.compile(r"^##\s+(O-\d+[A-Za-z]?)\s")
    for d_rel in dossiers:   # der Abschnitt des Orts, wo er schon steht
        f = Path(reise_dir) / d_rel
        zeilen = f.read_text(encoding="utf-8").split("\n") if f.exists() else []
        start = next((i for i, z in enumerate(zeilen) if (m := kopf.match(z + " ")) and m.group(1).upper() == oid), None)
        if start is not None:
            break
    else:
        start = None
    if start is not None:
        ende = next((i for i in range(start + 1, len(zeilen)) if zeilen[i].startswith("## ")), len(zeilen))
        erster = next((i for i in range(start + 1, ende) if zeilen[i].startswith("### ")), ende)
        fussnoten = [z for z in zeilen[start + 1:erster] if FUSSNOTE.match(z)]   # Belege der Unterabschnitte bleiben
        neu = ["", *absatz.split("\n"), ""] + (fussnoten + [""] if fussnoten else [])
        zeilen[start + 1:erster] = neu
        was = "ersetzt"
    else:
        if not dossiers:
            d_rel = "inhalt/orte.md"
            cfg["orte_dossiers"] = [d_rel]
            p_cfg.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            d_rel = dossiers[0]
        f = Path(reise_dir) / d_rel
        zeilen = f.read_text(encoding="utf-8").rstrip("\n").split("\n") if f.exists() and f.read_text(encoding="utf-8").strip() else []
        name = o.get("name") or oid
        zeilen += ([""] if zeilen else []) + [f"## {oid} {name}", "", *absatz.split("\n")]
        was = "angelegt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(zeilen).rstrip("\n") + "\n", encoding="utf-8")
    return (S("schreiben.titel.lesetext_" + was, w1=oid),
            S("schreiben.antwort.lesetext.ort_" + was, w1=oid, w2=d_rel) + S("schreiben.antwort.herkunft", w1=quelle) + ".")


def reise_aendern(reise_dir, wer, args, heute=None):
    """Eckdaten der Reise ändern: titel, untertitel, kurz, ziel, von, bis (Zeitraum). Nur Organisator:innen, mit grund; der Verlauf
    steht in reise.yaml unter verlauf. -> (Titel, Text)."""
    from ruamel.yaml.comments import CommentedSeq
    heute = heute or datetime.date.today()
    grund = text_wert(args, "grund", pflicht=True)
    p, roh = reise_yaml_laden(reise_dir)
    geaendert = []
    from reise import ZIEL_LAENGE
    for feld, laenge in (("titel", 120), ("untertitel", 200), ("kurz", 40), ("ziel", ZIEL_LAENGE)):
        if args.get(feld) is not None:
            v = text_wert(args, feld, laenge=laenge) or ""
            if feld == "titel" and not v:
                raise Ablehnung("schreiben.wahlstelle_aendern.2")
            if v != (roh.get(feld) or ""):
                geaendert.append(wechsel(feld, roh.get(feld) or "", v, quotiert=True))
                (roh.__setitem__(feld, skalar("x", v)) if v else roh.pop(feld, None))
    von, bis = datum_wert(args, "von"), datum_wert(args, "bis")
    if von or bis:
        z = roh.get("zeitraum")
        if z is None:
            from ruamel.yaml.comments import CommentedMap
            z = CommentedMap()
            roh["zeitraum"] = z
        neu_von, neu_bis = von or z.get("von"), bis or z.get("bis")
        if not (neu_von and neu_bis):
            raise Ablehnung("schreiben.reise_aendern.1")
        if neu_bis < neu_von:
            raise Ablehnung("schreiben.reise_aendern.2")
        for k, v in (("von", von), ("bis", bis)):
            if v and v != z.get(k):
                geaendert.append(wechsel(k, z.get(k) or "–", v))
                z[k] = v
    if not geaendert:
        raise Ablehnung("schreiben.reise_aendern.3")
    verlauf = roh.get("verlauf")
    if verlauf is None:
        verlauf = CommentedSeq()
        roh["verlauf"] = verlauf
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": lesbar(reise_dir, geaendert), "grund": grund}))
    reise_yaml_speichern(p, roh)
    return S("schreiben.titel.eckdaten", w1=kurz_namen(geaendert)), S("schreiben.antwort.eckdaten.kopf") + verbinden(geaendert, "; ") + S("schreiben.antwort.eckdaten.grund_ende", w1=grund)


def start_ende_neu(args, roh):
    """Neue Werte für Start und Ende des Plans aus der Anfrage -> {(teil, feld): wert}; wert "" heißt entfernen. Prüft Form
    und Existenz der Orte; start_datum darf nicht leer sein (ohne baut die Reise nicht)."""
    neu = {}
    for teil in ("start", "ende"):
        d = datum_wert(args, f"{teil}_datum")
        if d is not None:
            neu[(teil, "datum")] = d
        if args.get(f"{teil}_ort") is not None:
            o = text_wert(args, f"{teil}_ort", laenge=10) or ""
            if o and (not re.fullmatch(r"O-\d+", o) or o not in (roh.get("orte") or {})):
                raise Ablehnung("schreiben.start_ende_neu.1", teil=teil, o=o)
            neu[(teil, "ort")] = o
    if neu.get(("start", "datum")) == "":
        raise Ablehnung("schreiben.start_ende_neu.2")
    if neu.get(("start", "ort")) == "":
        raise Ablehnung("schreiben.start_ende_neu.3")
    return neu


def start_ende_setzen(reise_dir, wer, args, heute=None):
    """Start und Ende des Plans (start, ende in plan/routen.yaml): start_datum, start_ort, ende_datum, ende_ort; leerer Text
    entfernt ende_datum bzw. ende_ort. Nur Organisator:innen, mit grund; der Verlauf steht in reise.yaml. -> (Titel, Text)."""
    from ruamel.yaml.comments import CommentedSeq
    heute = heute or datetime.date.today()
    grund = text_wert(args, "grund", pflicht=True)
    roh = routen_laden(reise_dir)
    neu = start_ende_neu(args, roh)
    geaendert, antwort_teile, verschoben = [], [], False
    for (teil, feld), v in neu.items():
        knoten = roh.get(teil) or {}
        alt = knoten.get(feld)
        if v == (alt if alt is not None else ""):
            continue
        satz_name = S(f"schreiben.antwort.start_ende.{teil}_{feld}")
        geaendert.append(satz_name + " " + anzeige_text(alt or "–") + " → " + anzeige_text(v) if v else satz_name + " " + anzeige_text(alt) + S("schreiben.antwort.start_ende.entfernt"))
        antwort_teile.append(geaendert[-1])
        verschoben = verschoben or (teil, feld) == ("start", "datum")
        if teil not in roh or roh.get(teil) is None:
            roh[teil] = fliess_map({})
        (roh[teil].__setitem__(feld, v) if v else roh[teil].pop(feld, None))
    if not geaendert:
        raise Ablehnung("schreiben.start_ende_setzen.1")
    s, e = (roh.get("start") or {}).get("datum"), (roh.get("ende") or {}).get("datum")
    if isinstance(s, datetime.date) and isinstance(e, datetime.date) and e < s:
        raise Ablehnung("schreiben.start_ende_setzen.2", w1=e.isoformat(), w2=s.isoformat())
    if "ende" in roh and not roh.get("ende"):
        del roh["ende"]
    routen_speichern(reise_dir, roh)
    p, ry = reise_yaml_laden(reise_dir)
    verlauf = ry.get("verlauf")
    if verlauf is None:
        verlauf = CommentedSeq()
        ry["verlauf"] = verlauf
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": lesbar(reise_dir, geaendert), "grund": grund}))
    reise_yaml_speichern(p, ry)
    text = verbinden(antwort_teile, "; ") + S("schreiben.antwort.eckdaten.grund_ende_kurz", w1=grund)
    if verschoben:
        text = text + S("schreiben.antwort.start_ende.verschoben")
    return texte.t(texte.VORGABE_REISE, "schreiben.titel.start_ende_setzen"), text   # Titel des Eintrags (Commit): Sprache der Reise-Dateien


PLAN_FARBEN = ("a", "b", "c", "d")


def plan_felder(args, roh, route, d, geaendert=None):
    """Felder eines benannten Plans aus der Anfrage in d (CommentedMap) übernehmen; geaendert sammelt die Änderungen."""
    optionen_ids = {x["id"]: w["id"] for w in route.get("wahlstellen") or [] for x in w["optionen"]}
    for feld, laenge in (("kurz", 40), ("titel", 200), ("text", 2000)):
        if args.get(feld) is not None:
            v = text_wert(args, feld, laenge=laenge) or ""
            if feld != "text" and not v:
                raise Ablehnung("schreiben.option_aendern.2", feld=feld)
            if v != (d.get(feld) or ""):
                if geaendert is not None:
                    geaendert.append(wechsel(feld, d.get(feld) or "", v, quotiert=True))
                (d.__setitem__(feld, skalar(feld, v)) if v else d.pop(feld, None))
    if args.get("farbe") is not None:
        farbe = str(args.get("farbe") or "").strip().lower()
        if farbe not in PLAN_FARBEN:
            raise Ablehnung("schreiben.plan_felder.1", w1=', '.join(PLAN_FARBEN))
        if farbe != d.get("farbe"):
            if geaendert is not None:
                geaendert.append(wechsel("farbe", d.get("farbe") or "–", farbe))
            d["farbe"] = farbe
    if args.get("auswahl") is not None:
        auswahl = id_liste(args, "auswahl", r"V-\d+\.[a-z]", roh) or []
        fehlt = [x for x in auswahl if x not in optionen_ids]
        if fehlt:
            raise Ablehnung("schreiben.plan_felder.2", w1=', '.join(fehlt))
        je = {}
        for x in auswahl:
            if optionen_ids[x] in je:
                raise Ablehnung("schreiben.plan_felder.3", w1=optionen_ids[x], w2=je[optionen_ids[x]], x=x)
            je[optionen_ids[x]] = x
        if list(d.get("auswahl") or []) != auswahl:
            if geaendert is not None:
                geaendert.append(wechsel("auswahl", list(d.get("auswahl") or []), auswahl))
            d["auswahl"] = fliess_map({"auswahl": auswahl})["auswahl"]
    for feld in ("plus", "minus"):
        if args.get(feld) is not None:
            l = liste_wert(args, feld, laenge=10) or []
            if list(d.get(feld) or []) != l:
                if geaendert is not None:
                    geaendert.append(wechsel(feld, list(d.get(feld) or []), l))
                (d.__setitem__(feld, fliess_map({feld: l})[feld]) if l else d.pop(feld, None))


def plan_anlegen(reise_dir, wer, args, heute=None):
    """Einen benannten Plan (P-A, P-B …) anlegen: kurz, titel, auswahl (eine Option je Wahlstelle), farbe, plus, minus, text,
    quelle. Nur Organisator:innen. -> (Titel, Text)."""
    from ruamel.yaml.comments import CommentedSeq
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    plaene = roh.get("plaene")
    if plaene is None:
        plaene = CommentedSeq()
        roh["plaene"] = plaene
    vergeben = {p.get("id") for p in plaene if isinstance(p, dict)}
    pid = next((f"P-{b}" for b in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if f"P-{b}" not in vergeben), None)
    if pid is None:
        raise Ablehnung("schreiben.plan_anlegen.1")
    if not args.get("kurz"):
        args = {**args, "kurz": f"Plan {pid[2:]}"}
    if not args.get("titel"):
        raise Ablehnung("schreiben.plan_anlegen.2")
    if not args.get("auswahl"):
        raise Ablehnung("schreiben.plan_anlegen.3")
    quelle = text_wert(args, "quelle", pflicht=True)
    d = block_map({"id": pid})
    plan_felder(args, roh, route, d)
    d["quelle"] = skalar("quelle", quelle)
    plaene.append(d)
    routen_speichern(reise_dir, roh)
    return S("schreiben.titel.plan_angelegt", w1=pid, w2=d["kurz"]), S("schreiben.antwort.plan.angelegt", w1=pid, w2=d["kurz"], w3=d["titel"], w4=", ".join(d.get("auswahl") or [])) + S("schreiben.antwort.herkunft", w1=quelle) + S("schreiben.antwort.plan.entscheiden")


def plan_aendern(reise_dir, wer, args, heute=None):
    """Felder eines benannten Plans ändern (kurz, titel, text, farbe, auswahl, plus, minus), mit grund. Nur Organisator:innen. -> (Titel, Text)."""
    pid = (text_wert(args, "ziel", pflicht=True, laenge=10) or "").strip().upper()
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    d = next((p for p in roh.get("plaene") or [] if isinstance(p, dict) and p.get("id") == pid), None)
    if d is None:
        raise Ablehnung("schreiben.plan_aendern.1", pid=pid)
    geaendert = []
    plan_felder(args, roh, route, d, geaendert)
    if not geaendert:
        raise Ablehnung("schreiben.plan_aendern.2", pid=pid)
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    return S("schreiben.titel.geaendert", w1=pid, w2=kurz_namen(geaendert)), S("schreiben.antwort.plan.kopf", w1=pid, w2=d.get("kurz", "")) + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund else "")


def merkmal_zusammenfuehren(reise_dir, wer, args, heute=None):
    """Zwei Merkmale einer Art zusammenführen: die Werte von „von“ hängen an „nach“ (wo „nach“ schon einen Wert hat, bleibt
    der; der andere steht in der Notiz), „von“ entfällt aus der Definition und wird ein weiterer Name von „nach“. Nur
    Organisator:innen, mit grund. -> (Titel, Text)."""
    art = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
    von = (text_wert(args, "von", pflicht=True, laenge=40) or "").lower()
    nach = (text_wert(args, "nach", pflicht=True, laenge=40) or "").lower()
    grund = text_wert(args, "grund", pflicht=True)
    arten = arten_laden(reise_dir)
    if art not in arten:
        raise Ablehnung("schreiben.merkmal_zusammenfuehren.1", art=art, w2=', '.join(arten) or 'keine')
    mk = arten[art].get("merkmale") if isinstance(arten[art].get("merkmale"), dict) else {}
    if von == nach or von not in mk or nach not in mk:
        raise Ablehnung("schreiben.merkmal_zusammenfuehren.2", art=art, w2=', '.join(mk) or 'keine')
    if mk[von].get("auto") or mk[nach].get("auto"):
        raise Ablehnung("schreiben.merkmal_zusammenfuehren.3")
    if mk[von].get("typ", "text") != mk[nach].get("typ", "text"):
        raise Ablehnung("schreiben.merkmal_zusammenfuehren.4", w1=mk[von].get('typ', 'text'), w2=mk[nach].get('typ', 'text'))
    roh = routen_laden(reise_dir)
    route = route_stand(reise_dir)
    grundform = arten[art].get("grundform")
    umgehaengt, behalten = [], []

    def umhaengen(did, knoten):
        m = knoten.get("merkmale")
        if not isinstance(m, dict) or von not in m:
            return
        alt = m.pop(von)
        if nach in m:
            behalten.append(did)
            e = m[nach] if isinstance(m[nach], dict) else None
            if e is not None:
                w = alt.get("wert") if isinstance(alt, dict) else alt
                e["notiz"] = skalar("notiz", (f"{e.get('notiz')}; " if e.get("notiz") else "") + f"vorher auch {von}: {w}")
        else:
            m[nach] = alt
            umgehaengt.append(did)

    menge = {"aufenthalt": ("unterkuenfte", "aufenthalte"), "bewegung": ("strecken",), "folge": ()}.get(grundform, ())
    for abschnitt in menge:
        for did, knoten in (roh.get(abschnitt) or {}).items():
            if isinstance(knoten, dict) and knoten.get("art") == art:
                umhaengen(did, knoten)
    for w in route.get("wahlstellen") or []:
        if w.get("art") != art:
            continue
        wk = (roh.get("wahlstellen") or {}).get(w["id"]) or {}
        for o in wk.get("optionen") or []:
            if isinstance(o, dict):
                umhaengen(o.get("id"), o)
        if isinstance(wk.get("merkmale"), dict) and von in wk["merkmale"]:
            del wk["merkmale"][von]
    routen_speichern(reise_dir, roh)
    auch = [x for x in (mk[nach].get("auch") or []) if x != von] + [von] + [x for x in (mk[von].get("auch") or []) if x not in (mk[nach].get("auch") or []) and x != nach]
    mk[nach]["auch"] = auch
    del mk[von]
    arten[art]["merkmale"] = mk
    arten_speichern(reise_dir, arten, wer)
    return S("schreiben.titel.zusammengefuehrt", w1=art, w2=von, w3=nach), (S("schreiben.antwort.zusammen.aufgegangen", w1=von, w2=art, w3=nach, w4=len(umgehaengt))
            + (S("schreiben.antwort.zusammen.behalten", w1=", ".join(behalten), w2=nach) if behalten else "")
            + S("schreiben.antwort.zusammen.name", w1=von, w2=nach, w3=grund))


def artvorlagen(sprache=None):
    """Vorlagen für Arten (ADR-0011, #477) in der Sprache der Reise, sonst der Vorgabesprache: {art: Definition} ohne Werte.
    Liegen neben dem Code (engine/artvorlagen/<sprache>.yaml); auf dem Server im Dienstordner."""
    import yaml
    ordner = Path(__file__).resolve().parent / "artvorlagen"
    for sp in (sprache, texte.VORGABE):
        p = ordner / f"{sp}.yaml"
        if sp and p.exists():
            return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("arten") or {}
    return {}


def arten_uebernehmen(reise_dir, wer, args, heute=None):
    """Arten (mit Merkmalen und Gliederung) einer anderen Reise derselben Person als Kopie übernehmen, nur die, die es hier noch
    nicht gibt (oder die in „arten“ genannten). Nur auf ausdrückliche Nachfrage (Product Owner 28.10.2026); der Konnektor
    prüft, dass die Person auf beiden Reisen dabei ist. Nur Organisator:innen. Mit vorlage: true aus den Vorlagen der Software
    (ADR-0011, #477): nur Merkmale, keine Werte. -> (Titel, Text)."""
    if bool_wert(args, "vorlage"):
        fremd = artvorlagen(sprache_von(reise_dir))
        von = str(S("schreiben.arten_uebernehmen.vorlage"))
    else:
        von = (text_wert(args, "von_reise", pflicht=True, laenge=60) or "").strip()
        if not REISE_MUSTER.match(von):
            raise Ablehnung("schreiben.arten_uebernehmen.1")
        quelle_dir = Path(reise_dir).parent / von
        if quelle_dir.resolve() == Path(reise_dir).resolve() or not (quelle_dir / "plan" / "arten.yaml").exists():
            raise Ablehnung("schreiben.arten_uebernehmen.2", von=von)
        fremd = arten_laden(quelle_dir)
    eigene = arten_laden(reise_dir)
    gewuenscht = liste_wert(args, "arten", laenge=40)
    gewuenscht = [a.lower() for a in gewuenscht] if gewuenscht else [a for a in fremd if a not in eigene]
    fehlt = [a for a in gewuenscht if a not in fremd]
    if fehlt:
        raise Ablehnung("schreiben.arten_uebernehmen.3", von=von, w2=', '.join(fehlt), w3=', '.join(fremd))
    da = [a for a in gewuenscht if a in eigene]
    if da:
        raise Ablehnung("schreiben.arten_uebernehmen.4", w1=', '.join(da))
    if not gewuenscht:
        raise Ablehnung("schreiben.arten_uebernehmen.5", von=von)
    import copy
    for a in gewuenscht:
        eigene[a] = copy.deepcopy(fremd[a])
    arten_speichern(reise_dir, eigene, wer)
    grund = text_wert(args, "grund")
    return S("schreiben.titel.arten_uebernommen", w1=von, w2=", ".join(gewuenscht)), (S("schreiben.antwort.uebernommen", w1=von)
            + verbinden([S("schreiben.antwort.uebernommen_art", w1=a, w2=fremd[a].get("name", a), n=len(fremd[a].get("merkmale") or {})) for a in gewuenscht]) + "."
            + (S("schreiben.antwort.grund", w1=grund) if grund else ""))


def wunsch_vorschlagen(reise_dir, wer, args, heute=None):
    """Vorschlag zu einem Wunsch (plan/wuensche.yaml, Wunsch-Brett): an welche Stellen er passt (bezug), eine Notiz mit Herkunft
    und, wenn daraus eine Option wurde, deren ID. Eingeplant wird er erst durch eine Organisator:in. -> (Titel, Text)."""
    import io
    rid = (text_wert(args, "wunsch", pflicht=True, laenge=40) or "").strip()
    if not re.fullmatch(r"R-\d{8}-\d{6}-[0-9a-z]{4}", rid):
        raise Ablehnung("schreiben.wunsch_vorschlagen.1")
    notiz = text_wert(args, "notiz", pflicht=True, laenge=600)
    roh_r = routen_laden(reise_dir)
    bezug = id_liste(args, "bezug", r"(T-\d+|E-\d+[A-Za-z]?|U-\d+|A-\d+|O-\d+|V-\d+|W-\d+(\.[\w-]+)?)", roh_r) or []
    for x in bezug:
        menge = {"T": "tage", "E": "strecken", "U": "unterkuenfte", "A": "aufenthalte", "O": "orte", "V": "wahlstellen"}.get(x[0])
        if menge and x not in (roh_r.get(menge) or {}):
            raise Ablehnung("schreiben.wunsch_vorschlagen.2", x=x)
    option = text_wert(args, "option", laenge=12)
    if option and not any(o.get("id") == option for w in (roh_r.get("wahlstellen") or {}).values() for o in (w.get("optionen") or []) if isinstance(o, dict)):
        raise Ablehnung("schreiben.wunsch_vorschlagen.3", option=option)
    p = Path(reise_dir) / "plan" / "wuensche.yaml"
    y = yaml_rund()
    roh = y.load(p.read_text(encoding="utf-8")) if p.exists() else None
    if roh is None:
        from ruamel.yaml.comments import CommentedMap
        roh = CommentedMap()
        roh.yaml_set_start_comment(texte.t(sprache_von(reise_dir), "inhalt.schreiben.wuensche_kopf"))
    neu_ = {"bezug": bezug, "notiz": notiz}
    if option:
        neu_["option"] = option
    war = rid in roh
    roh[rid] = block_map(neu_)
    out = io.StringIO()
    y.dump(roh, out)
    p.write_text(out.getvalue(), encoding="utf-8")
    return S("schreiben.titel.wunsch_" + ("geaendert" if war else "eingetragen"), w1=rid[:14]), (S("schreiben.antwort.wunsch.geaendert" if war else "schreiben.antwort.wunsch.eingetragen") + (", ".join(bezug) or S("schreiben.antwort.wunsch.keine_stelle"))
            + (S("schreiben.antwort.wunsch.option", w1=option) if option else "") + S("schreiben.antwort.wunsch.brett", w1=notiz))


# ---------- Packliste (plan/packliste.yaml, ADR-0010, Issue #370) ----------
# Gegenstände (G-…) mit der Kategorie als Art (grundform gegenstand). Ein Schreibvorgang je Werkzeug, Verlaufseintrag mit Person, Datum
# und Grund. Der Packstand (abgehakt, je Person) liegt nicht hier, sondern live beim Rückmeldedienst. Eine Herkunft braucht ein
# Gegenstand nicht (ausdrückliche Ausnahme von ADR-0001, Punkt 5); Merkmale mit veraenderlich behalten ihr Prüfdatum.
GEGENSTAND_ELTERN = ("strecke", "aufenthalt", "unterkunft", "ort")
GEGENSTAND_MENGE = {"strecke": "strecken", "aufenthalt": "aufenthalte", "unterkunft": "unterkuenfte", "ort": "orte"}
GEGENSTAND_TITEL_MAX = 120


def packliste_laden(reise_dir):
    """plan/packliste.yaml rund gelesen -> Wörterbuch mit Liste gegenstaende; eine Reise ohne Datei bekommt eine leere mit Kopfkommentar."""
    from ruamel.yaml.comments import CommentedMap, CommentedSeq
    p = Path(reise_dir) / "plan" / "packliste.yaml"
    roh = None
    if p.exists():
        try:
            roh = yaml_rund().load(p.read_text(encoding="utf-8"))
        except Exception as e:   # ruamel wirft verschiedene Fehlerklassen
            raise Ablehnung("schreiben.packliste_laden.1", __name__=type(e).__name__)
    if roh is None:
        roh = CommentedMap()
        roh.yaml_set_start_comment(texte.t(sprache_von(reise_dir), "inhalt.schreiben.packliste_kopf"))
    if not isinstance(roh, dict) or not isinstance(roh.get("gegenstaende") or [], list):
        raise Ablehnung("schreiben.packliste_laden.1", __name__="Form")
    if roh.get("gegenstaende") is None:
        roh["gegenstaende"] = CommentedSeq()
    return roh


def packliste_speichern(reise_dir, roh):
    import io
    out = io.StringIO()
    yaml_rund().dump(roh, out)
    p = Path(reise_dir) / "plan" / "packliste.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(out.getvalue(), encoding="utf-8")


def gegenstand_arten(reise_dir):
    """Arten der Reise mit Grundform gegenstand -> {Schlüssel: Definition}."""
    return {k: a for k, a in arten_laden(reise_dir).items() if isinstance(a, dict) and a.get("grundform") == "gegenstand"}


def gegenstand_art(reise_dir, text, pflicht=True):
    """Kategorie aus der Anfrage -> Schlüssel; sonst Ablehnung mit den vorhandenen Kategorien."""
    arten = gegenstand_arten(reise_dir)
    if not arten:
        raise Ablehnung("schreiben.gegenstand.keine_arten")
    art = (text or "").strip().lower()
    if not art:
        if pflicht:
            raise Ablehnung("schreiben.gegenstand.art_fehlt", w1=", ".join(arten))
        return None
    if art not in arten:
        # Name statt Schlüssel („Kleidung“) nimmt die Software an, wenn er eindeutig ist
        gleich = [k for k, a in arten.items() if str(a.get("name", "")).casefold() == art]
        if len(gleich) == 1:
            return gleich[0]
        raise Ablehnung("schreiben.gegenstand.art_unbekannt", art=art, w1=", ".join(arten))
    return art


def gegenstand_krit(route, art):
    """Merkmale einer Art, wie merkmale_werte sie erwartet ([{id, name, typ, …}]) aus dem Probebau."""
    return (route.get("merkmale") or {}).get(art) or []


def gegenstand_an(roh_route, wert):
    """Elternbezug eines Gegenstands prüfen -> Kennung. Strecke, Aufenthalt, Unterkunft oder Ort der Reise; ein Tag nicht (ADR-0007)."""
    from routen import ist
    x = str(wert).strip()
    art = next((a for a in GEGENSTAND_ELTERN if ist(a, x)), None)
    if art is None:
        raise Ablehnung("schreiben.gegenstand.an_form", x=x, w1=", ".join(GEGENSTAND_ELTERN))
    if x not in (roh_route.get(GEGENSTAND_MENGE[art]) or {}):
        raise Ablehnung("schreiben.gegenstand.an_unbekannt", x=x)
    return x


def gegenstand_person(reise_dir, text):
    """Person der Reise (Name oder Schlüssel, Groß- und Kleinschreibung egal) -> ihr Name; sonst Ablehnung."""
    _, roh = reise_yaml_laden(reise_dir)
    personen = {}
    for k, v in (roh.get("personen") or {}).items():
        if isinstance(v, dict) and v.get("name"):
            personen[str(v["name"]).casefold()] = str(v["name"])
            personen.setdefault(str(k).casefold(), str(v["name"]))
    name = personen.get(str(text).strip().casefold())
    if name is None:
        raise Ablehnung("schreiben.gegenstand.wer_unbekannt", x=str(text).strip(), w1=", ".join(dict.fromkeys(personen.values())) or "–")
    return name


def gegenstand_wert_knoten(e):
    """Wert eines Merkmals für die Datei: ein einfacher Wert steht schlicht („gewicht: 420“), mit Prüfdatum oder Notiz als Wörterbuch."""
    if set(e) == {"wert"}:
        return e["wert"]
    return fliess_map(e)


def gegenstand_merkmale(args, krit, heute, alt=None):
    """Merkmale aus der Anfrage prüfen -> (neue Werte der Datei {Schlüssel: Wert | None}, Wörter für die Antwort). None entfernt ein Merkmal
    (leerer Wert). Nur Merkmale der Art; Gültigkeit je Datum gibt es für Gegenstände nicht."""
    roh = args.get("merkmale")
    if roh in (None, "", {}):
        return {}
    if not isinstance(roh, dict):
        raise Ablehnung("schreiben.klammer.merkmale")
    aus = {}
    for k, v in roh.items():
        if v is None or (isinstance(v, str) and not v.strip()):
            d = next((x for x in krit if x["id"] == str(k).lower()), None)
            if d is None:
                raise Ablehnung("schreiben.merkmale_werte.1", k=str(k).lower(), w2=", ".join(x["id"] for x in krit) or "keine")
            aus[d["id"]] = None
            continue
        for sk, e in merkmale_werte({k: v}, krit, heute, herkunft=False).items():
            if isinstance(e, list) or "gilt" in e:
                raise Ablehnung("schreiben.gegenstand.gilt", k=sk)
            aus[sk] = e
    return aus


def gegenstand_finden(roh, gid):
    for g in roh.get("gegenstaende") or []:
        if isinstance(g, dict) and g.get("id") == gid:
            return g
    return None


def gegenstand_eintrag_text(g, art_name=None):
    return f"{g.get('id')} {g.get('titel')}" + (f" ({art_name})" if art_name else "")


def gegenstand_anlegen(reise_dir, wer, args, heute=None):
    """Einen Gegenstand der Packliste anlegen (neue G-ID): Kategorie (Art), Titel, Merkmale, an, wer packt, Notiz. -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    route = route_stand(reise_dir)
    roh_route = routen_laden(reise_dir)
    art = gegenstand_art(reise_dir, text_wert(args, "art", laenge=40))
    titel = text_wert(args, "titel", pflicht=True, laenge=GEGENSTAND_TITEL_MAX)
    werte = {k: v for k, v in gegenstand_merkmale(args, gegenstand_krit(route, art), heute).items() if v is not None}
    d = {"id": None, "art": art, "titel": titel}
    an = text_wert(args, "an", laenge=20)
    if an:
        d["an"] = gegenstand_an(roh_route, an)
    traeger = text_wert(args, "wer", laenge=80)
    if traeger:
        d["wer"] = gegenstand_person(reise_dir, traeger)
    if (notiz := text_wert(args, "notiz")):
        d["notiz"] = notiz
    grund = text_wert(args, "grund")
    gid = neue_id(reise_dir, "G")
    d["id"] = gid
    from ruamel.yaml.comments import CommentedSeq
    knoten = block_map({k: v for k, v in d.items() if k != "id"})
    knoten.insert(0, "id", gid)
    if werte:
        knoten.insert(list(knoten).index("art") + 2, "merkmale", fliess_map({}))
        for k, e in werte.items():
            knoten["merkmale"][k] = gegenstand_wert_knoten(e)
    verlauf = CommentedSeq()
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": "angelegt", **({"grund": grund} if grund else {})}))
    knoten["verlauf"] = verlauf
    roh = packliste_laden(reise_dir)
    aehnlich = gegenstaende_aehnlich(roh["gegenstaende"], titel)   # vor dem Anhängen: Hinweis auf Doppelte (#508)
    roh["gegenstaende"].append(knoten)
    packliste_speichern(reise_dir, roh)
    art_name = arten_laden(reise_dir)[art].get("name", art)
    defs = {x["id"]: x for x in gegenstand_krit(route, art)}
    mk_text = ", ".join(f"{defs[k]['name']} {e['wert']}{(' ' + defs[k]['einheit']) if defs[k].get('einheit') else ''}" for k, e in werte.items())
    return (S("schreiben.titel.gegenstand_angelegt", w1=gid, w2=titel, w3=art_name),
            S("schreiben.antwort.gegenstand.angelegt", w1=gid, w2=titel, w3=art_name) + (S("schreiben.antwort.gegenstand.merkmale", w1=mk_text) if mk_text else "")
            + (S("schreiben.antwort.gegenstand.an", w1=d["an"]) if d.get("an") else "")
            + (S("schreiben.antwort.gegenstand.wer", w1=d["wer"]) if d.get("wer") else "") + "."
            + (S("schreiben.antwort.grund", w1=grund) if grund else "")
            + (S("schreiben.antwort.gegenstand.aehnlich", w1=", ".join(gegenstand_eintrag_text(g) for g in aehnlich)) if aehnlich else ""))


def titel_wurzel(t):
    """Titel eines Gegenstands -> Vergleichsform: klein, ohne Klammerzusatz, Satzzeichen und Mengenangaben, Wörter ohne Endung -e/-n/-s."""
    t = re.sub(r"\([^)]*\)", " ", str(t or "").lower())
    woerter = [w for w in re.findall(r"[^\W\d_]+", t) if len(w) > 1]
    return " ".join(re.sub(r"(en|er|e|n|s)$", "", w) if len(w) > 4 else w for w in woerter)


def gegenstaende_aehnlich(gegenstaende, titel):
    """Aktive Gegenstände der Packliste mit (fast) gleichem Titel wie titel: gleiche Vergleichsform, oder die eine steckt als ganzes
    Wort oder Wortende in der anderen („Kotbeutel“, „Kotbeutel für Hund“, „Hundekotbeutel“). Nur ein Hinweis, angelegt wird trotzdem (#508). -> Liste"""
    neu = titel_wurzel(titel)
    if len(neu) < 3:
        return []
    treffer = []
    for g in gegenstaende or []:
        if not isinstance(g, dict) or g.get("status") == "entfaellt":
            continue
        alt = titel_wurzel(g.get("titel"))
        zusammen = any(a != b and (a.endswith(b) or b.endswith(a)) and min(len(a), len(b)) >= 5   # „Hundekotbeutel“ und „Kotbeutel“
                       for a in alt.split() for b in neu.split())
        if alt and len(alt) >= 3 and (alt == neu or zusammen or re.search(rf"\b{re.escape(neu)}\b", alt) or re.search(rf"\b{re.escape(alt)}\b", neu)):
            treffer.append(g)
    return treffer


def gegenstand_eigen(g, wer):
    """Darf eine Mitwirkende diesen Gegenstand ändern? Ja, wenn sie ihn angelegt hat oder er ihr zugewiesen ist (wer)."""
    name = wer["name"].casefold()
    if str(g.get("wer") or "").casefold() == name:
        return True
    erster = next((e for e in g.get("verlauf") or [] if isinstance(e, dict)), None)
    return bool(erster) and str(erster.get("wer") or "").casefold() == name


def gegenstand_aendern(reise_dir, wer, args, heute=None):
    """Einen Gegenstand ändern: Kategorie, Titel, Merkmale, an, wer packt, Notiz, Status (entfaellt mit Grund; aktiv holt ihn zurück). Leerer
    Text entfernt ein Feld. Mitwirkende ändern eigene (angelegt oder zugewiesen), Organisator:innen alle. -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    gid = (text_wert(args, "ziel", pflicht=True, laenge=10) or "").strip().upper()
    if not re.fullmatch(r"G-\d+", gid):
        raise Ablehnung("schreiben.gegenstand.ziel_form")
    roh = packliste_laden(reise_dir)
    g = gegenstand_finden(roh, gid)
    if g is None:
        raise Ablehnung("schreiben.gegenstand.ziel_unbekannt", gid=gid)
    if wer["rolle"] != "organisator" and not gegenstand_eigen(g, wer):
        raise Ablehnung("schreiben.gegenstand.fremd", gid=gid)
    route = route_stand(reise_dir)
    roh_route = routen_laden(reise_dir)
    arten = arten_laden(reise_dir)
    grund = text_wert(args, "grund")
    geaendert, kurz = [], []

    def feld(name, neu_wert, wort):
        """Textfeld setzen (leer entfernt es); Eintrag für Antwort und Verlauf."""
        alt = g.get(name)
        if neu_wert in ("", None):
            if name in g:
                geaendert.append(S("schreiben.antwort.ding.entfernt", w1=wort, w2=alt))
                kurz.append(wort)
                del g[name]
            return
        if alt == neu_wert:
            return
        geaendert.append(S("schreiben.antwort.ding.wechsel", w1=wort, w2=alt, w3=neu_wert) if alt is not None else S("schreiben.antwort.ding.neu", w1=wort, w2=neu_wert))
        kurz.append(wort)
        if name not in g and "verlauf" in g:   # der Verlauf bleibt am Ende des Eintrags
            g.insert(list(g).index("verlauf"), name, skalar(name, neu_wert))
        else:
            g[name] = skalar(name, neu_wert)

    art_neu = gegenstand_art(reise_dir, text_wert(args, "art", laenge=40), pflicht=False)
    art = art_neu or g.get("art")
    krit = gegenstand_krit(route, art)
    if art_neu and art_neu != g.get("art"):
        # Werte, die die neue Kategorie nicht kennt, müssen im selben Aufruf ausdrücklich entfernt werden (leerer Wert); nichts entfällt still
        ids = {x["id"] for x in krit}
        entfernen = {k for k, v in (args.get("merkmale") or {}).items() if v in ("", None)} if isinstance(args.get("merkmale"), dict) else set()
        fremd = [k for k in (g.get("merkmale") or {}) if k not in ids and k not in entfernen]
        if fremd:
            raise Ablehnung("schreiben.gegenstand.art_merkmale", art=art_neu, w1=", ".join(fremd))
        feld("art", art_neu, S("schreiben.gegenstand.wort.kategorie"))
        for k in [k for k in (g.get("merkmale") or {}) if k not in ids]:
            alt = g["merkmale"][k]
            geaendert.append(S("schreiben.antwort.ding.entfernt", w1=k, w2=alt.get("wert") if isinstance(alt, dict) else alt))
            kurz.append(k)
            del g["merkmale"][k]
        if "merkmale" in g and not g["merkmale"]:
            del g["merkmale"]
        args = {**args, "merkmale": {k: v for k, v in args["merkmale"].items() if k in ids}} if isinstance(args.get("merkmale"), dict) else args
    titel = text_wert(args, "titel", laenge=GEGENSTAND_TITEL_MAX)
    if titel is not None:
        if not titel:
            raise Ablehnung("schreiben.gegenstand.titel_leer")
        feld("titel", titel, S("schreiben.gegenstand.wort.titel"))
    if args.get("an") is not None:
        an = text_wert(args, "an", laenge=20)
        feld("an", gegenstand_an(roh_route, an) if an else "", "an")
    if args.get("wer") is not None:
        traeger = text_wert(args, "wer", laenge=80)
        feld("wer", gegenstand_person(reise_dir, traeger) if traeger else "", S("schreiben.gegenstand.wort.wer"))
    if args.get("notiz") is not None:
        feld("notiz", text_wert(args, "notiz"), S("schreiben.gegenstand.wort.notiz"))
    defs = {x["id"]: x for x in krit}
    for k, e in gegenstand_merkmale(args, krit, heute).items():
        name = defs[k]["name"]
        alt = (g.get("merkmale") or {}).get(k)
        alt_w = alt.get("wert") if isinstance(alt, dict) else alt
        if e is None:
            if alt is not None:
                geaendert.append(S("schreiben.antwort.ding.entfernt", w1=name, w2=alt_w))
                kurz.append(name)
                del g["merkmale"][k]
                if not g["merkmale"]:
                    del g["merkmale"]
            continue
        neu_k = gegenstand_wert_knoten(e)
        if alt == neu_k or (isinstance(alt, dict) and isinstance(neu_k, dict) and dict(alt) == dict(neu_k)):
            continue
        geaendert.append(S("schreiben.antwort.ding.wechsel", w1=name, w2=alt_w, w3=e["wert"]) if alt is not None else S("schreiben.antwort.ding.neu", w1=name, w2=e["wert"]))
        kurz.append(name)
        if "merkmale" not in g:
            g.insert(list(g).index("art") + 2, "merkmale", fliess_map({}))
        g["merkmale"][k] = neu_k
    status = text_wert(args, "status", laenge=20)
    weggelassen = False
    if status is not None:
        status = status.lower()
        if status not in ("entfaellt", "aktiv"):
            raise Ablehnung("schreiben.gegenstand.status")
        if status == "entfaellt" and g.get("status") != "entfaellt":
            if not grund:
                raise Ablehnung("schreiben.gegenstand.status_grund")
            if "verlauf" in g:
                g.insert(list(g).index("verlauf"), "status", "entfaellt")
            else:
                g["status"] = "entfaellt"
            geaendert.append(S("schreiben.antwort.gegenstand.entfaellt"))
            kurz.append(S("schreiben.gegenstand.wort.weggelassen"))
            weggelassen = True
        elif status == "aktiv" and g.get("status") == "entfaellt":
            del g["status"]
            geaendert.append(S("schreiben.antwort.gegenstand.aktiv"))
            kurz.append(S("schreiben.gegenstand.wort.zurueckgeholt"))
    if not geaendert:
        raise Ablehnung("schreiben.gegenstand.nichts_geaendert", gid=gid)
    from ruamel.yaml.comments import CommentedSeq
    if g.get("verlauf") is None:
        g["verlauf"] = CommentedSeq()
    g["verlauf"].append(fliess_map({"datum": heute, "wer": wer["name"], "was": lesbar(reise_dir, kurz), **({"grund": grund} if grund else {})}))
    packliste_speichern(reise_dir, roh)
    art_name = (arten.get(art) or {}).get("name", art)
    return (S("schreiben.titel.geaendert", w1=gid, w2=verbinden(kurz, "; ")),
            S("schreiben.antwort.gegenstand.kopf", w1=gid, w2=g.get("titel"), w3=art_name) + verbinden(geaendert, "; ") + "."
            + (S("schreiben.antwort.grund", w1=grund) if grund else "") + (S("schreiben.antwort.gegenstand.nicht_geloescht") if weggelassen else ""))


def fremde_datei(reise_dir, von, rel):
    """Datei einer anderen Reise der Instanz lesen -> Text oder None: aus dem Ordner neben dieser Reise (Git-Weg), sonst aus dem Reisespeicher."""
    p = Path(reise_dir).parent / von / rel
    if p.exists():
        return p.read_text(encoding="utf-8")
    try:
        import reisespeicher
    except ImportError:
        return None
    try:
        return reisespeicher.datei(von, rel).decode("utf-8")
    except (KeyError, OSError, sqlite3.Error, UnicodeDecodeError, reisespeicher.AblageFehlt, reisespeicher.AblageFehler):
        return None   # nicht lesbar, auch eine fehlende oder beschädigte Datei der Ablage (#349)


def packliste_uebernehmen(reise_dir, wer, args, heute=None):
    """Kategorien (Arten mit grundform gegenstand) und Gegenstände einer anderen Reise derselben Person als Vorschlag übernehmen: Kopie mit
    neuen G-IDs, ohne Packstand, ohne an: (die Dinge der alten Reise gibt es hier nicht) und ohne wer; weggelassene Gegenstände bleiben
    weg. Gibt es die Kategorie hier schon, kommen ihre Gegenstände hinein; Werte von Merkmalen, die sie nicht kennt, entfallen. Der
    Konnektor prüft, dass die Person auf beiden Reisen dabei ist. Nur Organisator:innen. -> (Titel, Text)"""
    import copy
    import yaml
    heute = heute or datetime.date.today()
    von = (text_wert(args, "von_reise", pflicht=True, laenge=60) or "").strip()
    if not REISE_MUSTER.match(von) or von == Path(reise_dir).name:
        raise Ablehnung("schreiben.packliste_uebernehmen.1")
    try:
        fremd_arten = yaml.safe_load(fremde_datei(reise_dir, von, "plan/arten.yaml") or "") or {}
        fremd_liste = yaml.safe_load(fremde_datei(reise_dir, von, "plan/packliste.yaml") or "") or {}
    except yaml.YAMLError:
        raise Ablehnung("schreiben.packliste_uebernehmen.2", von=von)
    fremd_arten = {k: a for k, a in ((fremd_arten.get("arten") if isinstance(fremd_arten, dict) else None) or {}).items()
                   if isinstance(a, dict) and a.get("grundform") == "gegenstand"}
    if not fremd_arten:
        raise Ablehnung("schreiben.packliste_uebernehmen.2", von=von)
    gewuenscht = liste_wert(args, "arten", laenge=40)
    gewuenscht = [a.lower() for a in gewuenscht] if gewuenscht else list(fremd_arten)
    fehlt = [a for a in gewuenscht if a not in fremd_arten]
    if fehlt:
        raise Ablehnung("schreiben.packliste_uebernehmen.3", von=von, w2=", ".join(fehlt), w3=", ".join(fremd_arten))
    eigene = arten_laden(reise_dir)
    for a in gewuenscht:     # eine Kategorie hier mit anderer Grundform wäre ein Widerspruch
        if a in eigene and eigene[a].get("grundform") != "gegenstand":
            raise Ablehnung("schreiben.packliste_uebernehmen.4", art=a, w1=eigene[a].get("grundform"))
    neue_arten = [a for a in gewuenscht if a not in eigene]
    for a in neue_arten:
        eigene[a] = copy.deepcopy(fremd_arten[a])
    if neue_arten:
        arten_speichern(reise_dir, eigene, wer)
    quellen = [g for g in (fremd_liste.get("gegenstaende") if isinstance(fremd_liste, dict) else None) or []
               if isinstance(g, dict) and g.get("art") in gewuenscht and g.get("status") != "entfaellt" and g.get("titel")]
    route = route_stand(reise_dir)
    roh = packliste_laden(reise_dir)
    from ruamel.yaml.comments import CommentedSeq
    angelegt, verloren = [], []
    for q in quellen:
        krit = {x["id"]: x for x in gegenstand_krit(route, q["art"])}
        d = {"art": q["art"], "titel": str(q["titel"])[:GEGENSTAND_TITEL_MAX]}
        if q.get("notiz"):
            d["notiz"] = str(q["notiz"])[:MAX_TEXT]
        gid = neue_id(reise_dir, "G")
        knoten = block_map(d)
        knoten.insert(0, "id", gid)
        mk = {}
        for k, v in (q.get("merkmale") or {}).items():
            if k in krit and not krit[k].get("auto"):
                e = dict(v) if isinstance(v, dict) else {"wert": v}
                mk[k] = {f: e[f] for f in ("wert", "geprueft", "notiz") if e.get(f) not in (None, "")}
            else:
                verloren.append(f"{q['titel']}: {k}")
        if mk:
            knoten.insert(list(knoten).index("titel") + 1, "merkmale", fliess_map({}))
            for k, e in mk.items():
                knoten["merkmale"][k] = gegenstand_wert_knoten(e)
        verlauf = CommentedSeq()
        verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": lesbar(reise_dir, [S("schreiben.gegenstand.wort.uebernommen_aus", w1=von)]),
                                   **({"grund": g_} if (g_ := text_wert(args, "grund")) else {})}))
        knoten["verlauf"] = verlauf
        roh["gegenstaende"].append(knoten)
        angelegt.append(gid)
    if not neue_arten and not angelegt:
        raise Ablehnung("schreiben.packliste_uebernehmen.5", von=von)
    packliste_speichern(reise_dir, roh)
    grund = text_wert(args, "grund")
    return (S("schreiben.titel.packliste_uebernommen", w1=von, w2=len(angelegt)),
            S("schreiben.antwort.packliste.uebernommen", w1=von, n=len(angelegt))
            + (S("schreiben.antwort.packliste.kategorien", w1=", ".join(neue_arten)) if neue_arten else "")
            + (S("schreiben.antwort.packliste.verloren", w1="; ".join(verloren)) if verloren else "")
            + S("schreiben.antwort.packliste.vorschlag") + (S("schreiben.antwort.grund", w1=grund) if grund else ""))


WERKZEUGE = {"art_definieren": art_definieren, "merkmal_definieren": merkmal_definieren, "kategorie_definieren": kategorie_definieren, "wert_eintragen": wert_eintragen,
             "ding_anlegen": ding_anlegen, "ding_aendern": ding_aendern, "option_anlegen": option_anlegen,
             "wahlstelle_anlegen": wahlstelle_anlegen, "frage_anlegen": frage_anlegen, "entscheiden": entscheiden,
             "tag_aendern": tag_aendern, "wissen_schreiben": wissen_schreiben, "frage_schliessen": frage_schliessen,
             "person_schreiben": person_schreiben, "lage_eintragen": lage_eintragen, "reise_status_setzen": reise_status_setzen,
             "einstellung_setzen": einstellung_setzen, "buchung_anlegen": buchung_anlegen, "buchung_aendern": buchung_aendern,
             # Abgleich 29.10.2026 (Paket 3): die Tür für alle Grundformen
             "tag_anlegen": tag_anlegen, "termin_setzen": termin_setzen, "wahlstelle_aendern": wahlstelle_aendern,
             "option_aendern": option_aendern, "wissen_aendern": wissen_aendern, "lesetext_schreiben": lesetext_schreiben,
             "reise_aendern": reise_aendern, "plan_anlegen": plan_anlegen, "plan_aendern": plan_aendern,
             "merkmal_zusammenfuehren": merkmal_zusammenfuehren, "arten_uebernehmen": arten_uebernehmen, "wunsch_vorschlagen": wunsch_vorschlagen,
             "start_ende_setzen": start_ende_setzen, "symbol_setzen": symbol_setzen,
             # Karte (Epic #225)
             "kartenansicht_setzen": kartenansicht_setzen, "track_anhaengen": track_anhaengen, "kartenpunkte_holen": kartenpunkte_holen,
             # Packliste (ADR-0010, #370)
             "gegenstand_anlegen": gegenstand_anlegen, "gegenstand_aendern": gegenstand_aendern, "packliste_uebernehmen": packliste_uebernehmen}
REPO_WERKZEUGE = {"reise_anlegen": reise_anlegen}   # arbeiten auf reisen/, nicht in einer Reise


# ---------- Der Schreibvorgang ----------

def warnungen_des_baus(reise_dir):
    """Daten der Reise bauen wie das Tor -> Warnungen [(bezug, text)]; wirft bauen.BauFehler."""
    import bauen
    with tempfile.TemporaryDirectory(prefix="frieda-probe-") as ziel:
        d = bauen.Bauer(reise_dir, ziel).daten()
    return [(w["bezug"], w["text"]) for w in (d.get("route") or {}).get("warnungen") or []]


def neue_hinweise(vorher, nachher):
    """Warnungen, die der Eintrag neu erzeugt hat, als Zeilen „<bezug>: <text>“ (höchstens HINWEISE_HOECHSTENS, dann „und N weitere“)."""
    neu = [texte.Satz(f"{b}: ") + t for b, t in nachher if (b, t) not in set(vorher)]
    if len(neu) > HINWEISE_HOECHSTENS:
        return neu[:HINWEISE_HOECHSTENS] + [texte.satz("schreiben.hinweise.weitere", n=len(neu) - HINWEISE_HOECHSTENS)]
    return neu


class Schreiber:
    """Arbeitskopie einer Reise für den Schreibweg: ändern, prüfen, sichern, veröffentlichen. Zwei Träger: der Reisespeicher
    (basis gesetzt: die Arbeitskopie ist ein Export des Stands basis, Stufe 2, #347) oder bis Stufe 5 eine Git-Arbeitskopie
    (basis None, engine/schreiben_git.py)."""

    def __init__(self, wurzel, arbeit=None, veroeffentlichen=None):
        self.wurzel = Path(wurzel)
        self.arbeit = Path(arbeit or schreibkopie(self.wurzel))
        self.veroeffentlichen = veroeffentlichen or os.environ.get("SB_VEROEFFENTLICHEN") \
            or str(self.wurzel / "frieda" / "betrieb" / "veroeffentlichen.sh")
        self.ende = None     # time.monotonic(), bis zu der ein Vorgang fertig sein muss (anwenden_extern); None: ohne Frist
        self.basis = None    # Speicherweg: Stand-Nummer, aus der die Arbeitskopie stammt (0: neue Reise); None: Git-Weg

    def rest(self):
        """Sekunden bis self.ende (None: ohne Frist)."""
        return None if self.ende is None else self.ende - time.monotonic()

    def vorbereiten(self):
        """Git-Weg: Arbeitskopie anlegen oder auf origin/main bringen (engine/schreiben_git.py)."""
        import schreiben_git
        schreiben_git.vorbereiten(self)

    def wer_pruefen(self, reise_dir, anfrage, werkzeug):
        """Person, Rolle und Status mit reise.yaml der Arbeitskopie prüfen -> {"name", "rolle", "person"}."""
        from reise import erlaubt, rolle_neu
        import bauen
        with tempfile.TemporaryDirectory(prefix="frieda-probe-") as ziel:
            try:
                eck = bauen.Bauer(reise_dir, ziel).eck
            except bauen.BauFehler as e:
                raise Ablehnung("schreiben.bau.lesen", meldungen=texte.Satz.verbinden(e.meldungen, " "))
        rolle = rolle_neu(anfrage.get("rolle"))
        person = anfrage.get("person")
        p = next((x for x in eck.get("personen") or [] if person and x.get("schluessel") == person), None)
        if p:
            rolle = rolle_neu(p.get("rolle"))     # reise.yaml gilt vor dem, was der Konnektor sagt
        name = (p or {}).get("name") or anfrage.get("name")
        if not isinstance(name, str) or not name.strip():
            raise Ablehnung("schreiben.wer_pruefen.1")
        ok, grund = erlaubt(AKTIONEN[werkzeug], rolle, (eck.get("status") or {}).get("wert") or "planung", eck.get("bausteine"),
                            None, eck.get("regeln"))   # einladen richtet sich nach regeln.einladen der Reise
        if not ok:
            raise Ablehnung(grund)
        return {"name": name.strip(), "rolle": rolle, "person": person, "titel": eck.get("titel") or reise_dir.name}

    def probebau(self, reise_dir):
        """Probebau wie im Tor: nur ein Baufehler lehnt ab -> Warnungen des Baus [(bezug, text)]."""
        import bauen
        try:
            return warnungen_des_baus(reise_dir)
        except bauen.BauFehler as e:
            raise Ablehnung("schreiben.bau.nichts_geaendert", meldungen=texte.Satz.verbinden(e.meldungen, " "))

    def vorher(self, reise_dir):
        """Warnungen des Stands vor dem Eintrag; baut er nicht, gibt es keinen Vergleich (leer)."""
        import bauen
        try:
            return warnungen_des_baus(reise_dir)
        except bauen.BauFehler:
            return []

    def verwerfen(self, reise=None):
        """Nach einer Ablehnung: Reste in der Arbeitskopie verwerfen. Speicherweg: nichts zu tun (die Arbeitskopie ist je
        Vorgang frisch und wird gelöscht); Git-Weg: zurücksetzen (reise None: alle Reisen, reise_anlegen)."""
        if self.basis is None:
            import schreiben_git
            schreiben_git.verwerfen(self, reise)

    def anwenden_im_ordner(self, reise, werkzeug, anfrage):
        """Anfrage prüfen, Rolle und Status prüfen, das Werkzeug in der Arbeitskopie anwenden und zur Probe bauen ->
        (reise, reise_dir, wer, titel, text, hinweise); sonst Ablehnung (die Arbeitskopie ist dann verworfen)."""
        if not REISE_MUSTER.match(reise or ""):
            raise Ablehnung("schreiben.schreiben.1")
        if werkzeug not in WERKZEUGE and werkzeug not in REPO_WERKZEUGE:
            raise Ablehnung("schreiben.schreiben.2", werkzeug=werkzeug)
        args = anfrage.get("args") if isinstance(anfrage.get("args"), dict) else {}
        reise_dir = self.arbeit / "reisen" / reise
        hinweise = []
        if werkzeug in REPO_WERKZEUGE:
            # Neue Reise: der Konnektor hat Person und Recht geprüft (Konto darf Reisen anlegen); hier Form und Probebau
            name = anfrage.get("name")
            if not isinstance(name, str) or not name.strip():
                raise Ablehnung("schreiben.wer_pruefen.1")
            wer = {"name": name.strip(), "rolle": anfrage.get("rolle") or "organisator", "person": anfrage.get("person"), "titel": "Reisen"}
            try:
                titel, text, reise = REPO_WERKZEUGE[werkzeug](self.arbeit / "reisen", wer, args)
                reise_dir = self.arbeit / "reisen" / reise
                self.probebau(reise_dir)
            except Ablehnung:
                self.verwerfen()
                raise
        else:
            if not (reise_dir / "reise.json").exists():
                raise Ablehnung("schreiben.schreiben.3", reise=reise)
            wer = self.wer_pruefen(reise_dir, anfrage, werkzeug)
            vorher = self.vorher(reise_dir)
            try:
                titel, text = WERKZEUGE[werkzeug](reise_dir, wer, args)
                hinweise = neue_hinweise(vorher, self.probebau(reise_dir))
            except Ablehnung:
                self.verwerfen(reise)
                raise
        return reise, reise_dir, wer, titel, text, hinweise

    def nachricht(self, reise_dir, werkzeug, wer, titel, text):
        """Kopf (Titel der Reise), Titel, Text und Fuß des Vorgangs in der Sprache der Reise (Variante A) -> (kopf, titel,
        text, fuss). Der Git-Weg macht daraus die Commit-Nachricht, der Speicherweg Titel und Grund des Vorgangs."""
        sp = sprache_von(reise_dir)
        rolle = texte.t(sp, "inhalt.schreiben.rolle." + str(wer["rolle"]))
        kopf = texte.t(sp, "inhalt.schreiben.reisen_titel") if werkzeug in REPO_WERKZEUGE else wer["titel"]
        fuss = texte.t(sp, "inhalt.schreiben.commit_fuss", werkzeug=werkzeug_name(sp, werkzeug), wer=wer["name"],
                       rolle=wer["rolle"] if rolle.startswith("inhalt.") else rolle, datum=datetime.date.today().isoformat())
        return (kopf, am_rand(sp, titel.text(sp) if isinstance(titel, texte.Satz) else titel),
                am_rand(sp, text.text(sp) if isinstance(text, texte.Satz) else text), fuss)

    def antwort(self, reise, titel, text, hinweise, commit, nummer):
        """Antwort eines gelungenen Schreibvorgangs: commit ist der Commit (Git) bzw. die Vorgangs-Nummer (Speicher),
        nummer der neue Reise-Stand."""
        antwort = {"ok": True, "text": text, "commit": commit,
                   "stand": {"gesichert": nummer, "veroeffentlicht": reisestand.veroeffentlicht(reise)[0]}}
        if isinstance(text, texte.Satz) and text.mit_schluesseln():   # der Konnektor setzt den Satz in der Sprache der Person zusammen
            antwort["text_teile"] = text.teile_json()
        if (m := re.match(r"^([A-Z]+-\d+(?:\.[\w-]+)?) ", titel)):   # neu angelegtes Ding: seine ID, damit der Konnektor weitermachen kann
            antwort["id"] = m.group(1)
        if hinweise:   # nur neue Warnungen; reise_anlegen (REPO_WERKZEUGE) hat keinen Vergleich
            antwort["hinweise"] = [str(h) for h in hinweise]
            antwort["hinweise_teile"] = [h.teile_json() if isinstance(h, texte.Satz) else str(h) for h in hinweise]
        return antwort

    def schreiben(self, reise, werkzeug, anfrage):
        """Ein Schreibvorgang in der vorbereiteten Arbeitskopie -> {"ok": True, "text", "commit", "stand"}; sonst Ablehnung.
        Speicherweg: genau ein Vorgang im Reisespeicher (erwartet=basis, Wartezeit der Datenbank = Rest der Frist);
        reisespeicher.StandGeaendert und sqlite3.Error gehen an anwenden. Git-Weg: Commit nach main (schreiben_git)."""
        if self.basis is None:
            import schreiben_git
            return schreiben_git.schreiben(self, reise, werkzeug, anfrage)
        import reisespeicher
        reise, reise_dir, wer, titel, text, hinweise = self.anwenden_im_ordner(reise, werkzeug, anfrage)
        _, titel_, text_, fuss = self.nachricht(reise_dir, werkzeug, wer, titel, text)
        rest = self.rest()
        try:
            v = reisespeicher.ordner_als_vorgang(
                reise, reise_dir, self.basis, wer=" ".join(wer["name"].split()), werkzeug=werkzeug,
                titel=(str(titel_).splitlines() or [""])[0], grund=f"{text_}\n\n{fuss}", kennung=os.environ.get("FR_VORGANG") or None,
                rolle=str(wer["rolle"]), timeout=10 if rest is None else max(0.1, rest))
        except reisespeicher.NichtsGeaendert:
            raise Ablehnung("schreiben.schreiben.4")
        reisestand.gesichert_schreiben(reise, v.stand, str(v.nummer))
        self.veroeffentlichen_anstossen()
        return self.antwort(reise, titel, text, hinweise, str(v.nummer), v.stand)

    def buchung_im_repo(self, reise, bid):
        """Git-Reise: gibt es die Buchung B-… auf origin/main? (engine/schreiben_git.py, Issue #135)."""
        import schreiben_git
        return schreiben_git.buchung_im_repo(self, reise, bid)

    def buchung_im_speicher(self, reise, bid):
        """Speicher-Reise: gibt es die Buchung B-… im neuesten Stand? -> {"gibt_es", "fuer", "wer"}. Liest nur
        plan/routen.yaml, ohne Sperre; fehlt Reise oder Datei: gibt es nicht. Datenbank nicht lesbar: sqlite3.Error."""
        import reisespeicher
        if not buchung_anfrage_gueltig(reise, bid):
            return {"gibt_es": False}
        try:
            text = reisespeicher.datei(reise, "plan/routen.yaml").decode("utf-8", errors="replace")
        except KeyError:
            return {"gibt_es": False}
        return buchung_aus_routen(text, bid)

    def veroeffentlichen_anstossen(self):
        """Veröffentlichen im Hintergrund (holt main in den Bauordner, baut, prüft). Hält ein anderer Lauf die Sperre,
        merkt das Skript das, und der laufende Lauf veröffentlicht danach gleich noch einmal (#230). Niedrige Priorität wie im Dienst
        veroeffentlichen.service, damit Schreibvorgänge während der Tests nicht warten (fehlen nice oder ionice, ohne sie).
        Die Ausgabe geht in <FR_DIENST>/veroeffentlichen-anstoss.log (nach /dev/null, wenn die Datei nicht zu öffnen ist): Die
        Ausgabe des Anwendens ist die Leitung zum Dienst, die das Skript sonst bis zu seinem Ende offen hielte; die Datei
        zeigt, was der Anstoß tat (#398). Ein fehlgeschlagener Lauf wiederholt der Timer, mit Protokoll. Wirft nie.
        Das Veröffentlichen baut auch Reisen aus dem Reisespeicher (Stufe 3, #348)."""
        if not self.veroeffentlichen or not Path(self.veroeffentlichen).exists():
            return
        # Ohne TMPDIR: Der Schreib-Unterprozess setzt es auf seinen Arbeitsordner, der mit dem Vorgang verschwindet; das Skript
        # (mktemp) fand dann keinen Ordner und baute eine Speicher-Reise erst im nächsten Takt des Timers (#398).
        env = {**{k: v for k, v in os.environ.items() if k not in ("TMPDIR", "TMP", "TEMP")}, "FR_WURZEL": str(self.wurzel)}
        prioritaet = (["nice", "-n", "10"] if shutil.which("nice") else []) + \
                     (["ionice", "-c", "2", "-n", "7"] if shutil.which("ionice") else [])
        try:
            datei = instanz.dienst() / "veroeffentlichen-anstoss.log"
            if datei.exists() and datei.stat().st_size > 1_000_000:   # wächst nicht ohne Ende: ab 1 MB von vorn
                datei.unlink()
            protokoll = open(datei, "ab")
        except OSError:
            protokoll = subprocess.DEVNULL
        for argv in ([*prioritaet, self.veroeffentlichen], [self.veroeffentlichen]):
            try:
                if protokoll is not subprocess.DEVNULL:
                    protokoll.write(f"--- {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {' '.join(argv[:1])}\n".encode()); protokoll.flush()
                subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=protokoll, stderr=protokoll,
                                 start_new_session=True)
                return
            except OSError as e:
                sys.stderr.write(f"Publishing not started ({' '.join(argv[:1])}): {e}\n")
            finally:
                if protokoll is not subprocess.DEVNULL:
                    protokoll.flush()


def buchung_anfrage_gueltig(reise, bid):
    return bool(REISE_MUSTER.match(reise or "")) and bool(re.fullmatch(r"B-\d+", bid or ""))


def buchung_aus_routen(text, bid):
    """Buchung bid aus dem Text von plan/routen.yaml -> {"gibt_es", "fuer", "wer"}."""
    import yaml
    try:
        b = ((yaml.safe_load(text) or {}).get("buchungen") or {}).get(bid) if text else None
    except yaml.YAMLError:
        b = None
    if not isinstance(b, dict):
        return {"gibt_es": False}
    fuer = b.get("fuer")
    return {"gibt_es": True, "fuer": [fuer] if isinstance(fuer, str) else [str(x) for x in (fuer or [])], "wer": b.get("wer")}


def abgelehnt(werkzeug, e):
    """Antwort auf eine Ablehnung -> (422, Antwort); der Grund steht im Protokoll (Werkzeug, Code, Regel; ein Zeilenumbruch
    oder Überlänge hat dort nichts zu suchen)."""
    grund = " ".join(str(e).split())[:LOG_LAENGE]
    sys.stderr.write(f"Rejected {werkzeug} 422: {grund}\n")
    antwort = {"ok": False, "fehler": str(e)}
    if e.schluessel:   # der Konnektor setzt den Satz in der Sprache der Person zusammen
        antwort.update(fehler_code=e.schluessel, werte=e.werte_json())
    return 422, antwort


def speicher_fehler(werkzeug, e):
    """Datenbank nicht erreichbar, nicht lesbar oder über die Frist gesperrt -> (503, Antwort)."""
    sys.stderr.write(f"Store {werkzeug} 503: {' '.join(f'{type(e).__name__}: {e}'.split())[:LOG_LAENGE]}\n")
    return 503, fehler_antwort("schreiben.dienst.speicher_nicht_erreichbar")


def ist_ablage_fehler(e):
    """Fehlt eine Datei in der Ablage des Reisespeichers oder ist sie beschädigt (Stufe 4, #349)?"""
    import reisespeicher
    return isinstance(e, (reisespeicher.AblageFehlt, reisespeicher.AblageFehler))


def ablage_fehler(werkzeug, reise, e):
    """Datei der Ablage fehlt oder ist beschädigt -> (503, Antwort mit pruefung.bauen.79/.80); nichts geschrieben."""
    import reisespeicher
    sys.stderr.write(f"Store {werkzeug} 503: {' '.join(f'{type(e).__name__}: {e}'.split())[:LOG_LAENGE]}\n")
    a = Ablehnung(reisespeicher.ablage_satz(e, reise))
    return 503, {"ok": False, "fehler": str(a), "fehler_code": a.schluessel, "werte": a.werte_json()}


def anwenden(wurzel_, arbeit, reise, werkzeug, anfrage, basis=None, frist=None):
    """Ein Schreibvorgang (Arbeitskopie ist vorbereitet) -> Antwort-Objekt mit HTTP-Code. basis gesetzt: Speicherweg mit
    der Frist frist (Sekunden ab jetzt) für das Eintragen; sonst Git-Weg."""
    s = Schreiber(wurzel_, arbeit)
    if basis is not None:
        s.basis = basis
        # etwas vor der Frist des Dienstes, damit die eigene Antwort ihn noch erreicht
        s.ende = None if frist is None else time.monotonic() + max(0.1, frist - 0.5)
    try:
        return 200, s.schreiben(reise, werkzeug, anfrage)
    except Ablehnung as e:
        return abgelehnt(werkzeug, e)
    except Exception as e:
        if s.basis is None:
            raise
        import reisespeicher
        if isinstance(e, reisespeicher.StandGeaendert):
            sys.stderr.write(f"Conflict {werkzeug} 503: {e}\n")
            return 503, fehler_antwort("schreiben.dienst.stand_geaendert")
        if isinstance(e, sqlite3.Error):
            return speicher_fehler(werkzeug, e)
        if ist_ablage_fehler(e):
            return ablage_fehler(werkzeug, reise, e)
        raise


# ---------- Dienst ----------

def fehler_antwort(schluessel, mit_ok=True):
    """Antwort mit Fehler aus dem Katalog: Text im Rückfall der Software, dazu der Schlüssel, damit der Konnektor ihn in der Sprache der Person setzt."""
    e = Ablehnung(schluessel)
    antwort = {"fehler": str(e), "fehler_code": e.schluessel, "werte": e.werte_json()}
    return {"ok": False, **antwort} if mit_ok else antwort

def sperrdatei(reise):
    name = instanz.wert("FR_INSTANZ", instanz.VORGABE_INSTANZ)
    return Path(instanz.wert("FR_SPERREN", "/tmp")) / f"{name}-schreiben-{reise}.lock"


def sperre_nehmen(f, frist=None):
    """Sperre der Datei f nehmen; True, sobald sie da ist, False, wenn sie nach `frist` Sekunden noch belegt ist."""
    ende = time.monotonic() + (ZEIT_SPERRE if frist is None else frist)
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            if time.monotonic() >= ende:
                return False
            time.sleep(0.05)


def vorgang_eingetragen(s, kennung):
    """Git-Weg: ist der Vorgang mit dieser Kennung auf origin/main angekommen? -> True, False oder None (engine/schreiben_git.py)."""
    import schreiben_git
    return schreiben_git.vorgang_eingetragen(s, kennung)


def vorgang_vorhanden(kennung):
    """Speicherweg: ist der Vorgang mit dieser Kennung eingetragen? -> Vorgang, False oder None (Prüfung nicht möglich).
    Liest nur, lokal im Reisespeicher, mit der Prüffrist ZEIT_PRUEFUNG als Wartezeit der Datenbank. Ein getöteter
    Unterprozess hat seine Transaktion zurückgerollt: „nicht eingetragen“ ist sicher."""
    import reisespeicher
    try:
        v = reisespeicher.vorgang_eingetragen(kennung, timeout=ZEIT_PRUEFUNG)
    except (sqlite3.Error, OSError):
        return None
    return v or False


def nicht_eingetragen(werkzeug):
    sys.stderr.write(f"Timeout {werkzeug} 504: aborted, not saved\n")
    return 504, fehler_antwort("schreiben.dienst.zu_lange_nicht")


def ungeprueft(werkzeug):
    sys.stderr.write(f"Timeout {werkzeug} 504: aborted, unchecked\n")
    return 504, fehler_antwort("schreiben.dienst.zu_lange_ungeprueft")


def eingetragen_trotz_abbruch(werkzeug, reise=None, nummer=None, commit=None):
    """Antwort, wenn der Vorgang trotz Abbruch eingetragen ist; mit reise auch der Stand (gesichert.json wie nach Erfolg)."""
    sys.stderr.write(f"Timeout {werkzeug} 504: aborted, saved\n")
    text = S("schreiben.dienst.verzoegert")
    antwort = {"ok": True, "text": str(text), "text_teile": text.teile_json(), "hinweis": str(text)}
    if reise:
        reisestand.gesichert_schreiben(reise, nummer, commit)
        antwort["stand"] = {"gesichert": nummer, "veroeffentlicht": reisestand.veroeffentlicht(reise)[0]}
    if commit:
        antwort["commit"] = commit
    return 200, antwort


def nach_abbruch(s, werkzeug, kennung, reise=None):
    """Speicherweg: Antwort, nachdem das Anwenden von der Frist abgebrochen wurde; nachgesehen wird lokal im Speicher
    (Meldungstabelle in docs/specs/betrieb/schreibweg-zeitgrenzen.md). Der Git-Weg hat schreiben_git.nach_abbruch."""
    ergebnis = vorgang_vorhanden(kennung)
    if ergebnis:
        return eingetragen_trotz_abbruch(werkzeug, reise, ergebnis.stand, str(ergebnis.nummer))
    if ergebnis is False:
        return nicht_eingetragen(werkzeug)
    return ungeprueft(werkzeug)


def ausgabe_lesen(r):
    """Ausgabe des Unterprozesses `anwenden` -> (Code, Antwort); sein Protokoll geht ins eigene."""
    if r.stderr:
        sys.stderr.write(r.stderr)
    try:
        code, antwort = json.loads(r.stdout)
        return int(code), antwort
    except (ValueError, TypeError):
        sys.stderr.write(f"apply: code {r.returncode}, output: {r.stdout[-500:]}\n")
        return 500, fehler_antwort("schreiben.dienst.fehlgeschlagen")


def kartenpunkte_vorab(s, reise, anfrage, vorab):
    """Abruf bei Overpass für kartenpunkte_holen vor der Sperre (#240) -> Pfad der Antwortdatei in `vorab` oder None (dann ruft
    der Vorgang selbst ab). Lesekopie des Stands (Speicher: Export, Git: Kopie aus der Wurzel), Rolle und Abfrage prüfen, alles in
    höchstens ZEIT_VORAB_VORB Sekunden; lehnt das ab, kein Abruf: der Vorgang lehnt mit demselben Grund ab. Scheitert der Abruf
    (OSM_FRIST_VORAB), wirft er die Ablehnung. Die Antwort kommt nur aus dem Netz, nie aus der Anfrage. Wird der Faden der
    Vorbereitung nicht rechtzeitig fertig, räumt er `vorab` selbst weg, sobald er endet (der Dienst hat ihn dann schon gelöscht)."""
    kopie, ergebnis, zustand, schloss = Path(vorab) / "kopie" / "reisen" / reise, {}, {}, threading.Lock()

    def vorbereiten():
        try:
            if not REISE_MUSTER.match(reise or ""):
                return
            if reise in instanz.speicherreisen():
                import reisespeicher
                reisespeicher.exportieren(reise, kopie, bis=reisespeicher.stand_nummer(reise))
            else:
                shutil.copytree(Path(s.wurzel) / "reisen" / reise, kopie, symlinks=True)
            args = anfrage.get("args") if isinstance(anfrage.get("args"), dict) else {}
            s.wer_pruefen(kopie, anfrage, "kartenpunkte_holen")
            ergebnis["abfrage"] = kartenpunkte_abfrage(kopie, args)[0]
        except Exception:     # Ablehnung oder Fehler: maßgeblich bleibt der Vorgang
            pass
        finally:
            with schloss:
                zustand["fertig"] = True
                if zustand.get("abgebrochen"):
                    shutil.rmtree(vorab, ignore_errors=True)
    faden = threading.Thread(target=vorbereiten, daemon=True)
    faden.start()
    faden.join(ZEIT_VORAB_VORB)
    with schloss:
        if not zustand.get("fertig"):
            zustand["abgebrochen"] = True
    if zustand.get("abgebrochen"):
        sys.stderr.write(f"Prefetch kartenpunkte_holen: preparation exceeded {ZEIT_VORAB_VORB} s, skipped\n")
        return None
    abfrage = ergebnis.get("abfrage")
    if not abfrage:
        return None
    try:
        antwort = overpass_holen(abfrage, OSM_FRIST_VORAB)
    except Ablehnung:
        raise
    except Exception as e:     # unerwarteter Fehler: der Vorgang ruft selbst ab
        sys.stderr.write(f"Prefetch kartenpunkte_holen: {' '.join(f'{type(e).__name__}: {e}'.split())[:LOG_LAENGE]}\n")
        return None
    datei = Path(vorab) / "osm.json"
    datei.write_text(json.dumps({"abfrage": abfrage, "antwort": antwort}), encoding="utf-8")
    return str(datei)


def anwenden_extern(s, reise, werkzeug, anfrage):
    """Ein Schreibvorgang des Dienstes -> (Code, Antwort). Der Weg richtet sich nach der Reise: steht sie in
    FR_SPEICHERREISEN, über den Reisespeicher (vorgang_speicher), sonst bis Stufe 5 über Git (schreiben_git.vorgang).
    Sperre und Arbeitskopie gibt es je Reise: Was bei einer Reise hängt, hält die anderen nicht auf (flock gilt auch zwischen
    Threads, jeder öffnet die Datei selbst). Alles zusammen dauert höchstens ZEIT_GESAMT + ZEIT_PRUEFUNG Sekunden, bei
    kartenpunkte_holen davor noch das Vorab-Fenster ZEIT_VORAB ohne Sperre (#240); die Dauer jedes Vorgangs steht im
    Protokoll, auch nach einem unerwarteten Fehler (500)."""
    start = time.monotonic()
    code, antwort = 500, fehler_antwort("schreiben.dienst.fehlgeschlagen")
    vorab = None
    try:
        osm_vorab = None
        if werkzeug == "kartenpunkte_holen":
            vorab = tempfile.mkdtemp(prefix="frieda-osm-")
            osm_vorab = kartenpunkte_vorab(s, reise, anfrage, vorab)
        if reise in instanz.speicherreisen():
            code, antwort = vorgang_speicher(s, reise, werkzeug, anfrage, time.monotonic(), osm_vorab=osm_vorab)
        else:
            import schreiben_git
            code, antwort = schreiben_git.vorgang(s, reise, werkzeug, anfrage, time.monotonic(), osm_vorab=osm_vorab)
    except Ablehnung as e:     # Vorab-Abruf gescheitert: ohne Sperre, ohne Vorgang
        code, antwort = abgelehnt(werkzeug, e)
    except instanz.EinstellungenNichtLesbar as e:      # #361: nie auf den Git-Weg ausweichen, wenn die Liste unbekannt ist
        sys.stderr.write(f"Error {werkzeug} 503: settings not readable: {' '.join(str(e).split())[:LOG_LAENGE]}\n")
        code, antwort = 503, fehler_antwort("schreiben.dienst.einstellungen_nicht_lesbar")
    except Exception as e:
        grund = " ".join(f"{type(e).__name__}: {e}".split())[:LOG_LAENGE]
        sys.stderr.write(f"Error {werkzeug} 500: {grund}\n")
    finally:
        if vorab:
            shutil.rmtree(vorab, ignore_errors=True)
        sys.stderr.write(f"Done {werkzeug} {code} in {time.monotonic() - start:.1f} s\n")
    return code, antwort


def vorab_umgebung(env, osm_vorab):
    """Umgebung des Unterprozesses `anwenden` mit FR_OSM_VORAB, wenn der Dienst vorab abgerufen hat, sonst ohne."""
    env.pop("FR_OSM_VORAB", None)
    if osm_vorab:
        env["FR_OSM_VORAB"] = str(osm_vorab)
    return env


def git_reisen(wurzel_):
    """Namen der Reisen im Ordner reisen/ des Reisen-Repos (Git-Reisen), ohne Git zu fragen."""
    try:
        return [p.name for p in (Path(wurzel_) / "reisen").iterdir() if p.is_dir() and REISE_MUSTER.match(p.name)]
    except OSError:
        return []


def vorgang_speicher(s, reise, werkzeug, anfrage, start, osm_vorab=None):
    """Ein Schreibvorgang über den Reisespeicher (Stufe 2, #347, ADR-0009) -> (Code, Antwort). Sperre der Reise (bei
    reise_anlegen der Reisen), Reise im Speicher?, Arbeitskopie als Export des Stands basis in einem temporären Ordner,
    dann `anwenden` mit dem Code dieses Dienstes (im Betrieb <FR_DIENST>) in der Frist; der Unterprozess trägt den Vorgang
    selbst ein (eine Transaktion, erwartet=basis). Der temporäre Ordner wird in jedem Fall gelöscht. osm_vorab: Antwortdatei
    des Vorab-Abrufs (kartenpunkte_holen), geht als FR_OSM_VORAB an den Unterprozess."""
    import reisespeicher
    ende = start + ZEIT_GESAMT
    if not REISE_MUSTER.match(reise or ""):
        return abgelehnt(werkzeug, Ablehnung("schreiben.schreiben.1"))
    if werkzeug not in WERKZEUGE and werkzeug not in REPO_WERKZEUGE:
        return abgelehnt(werkzeug, Ablehnung("schreiben.schreiben.2", werkzeug=werkzeug))
    neue_reise = werkzeug in REPO_WERKZEUGE
    with open(sperrdatei("reisen" if neue_reise else reise), "w") as f:
        if not sperre_nehmen(f):
            sys.stderr.write(f"Locked {werkzeug} 429: lock of the trip still held after {ZEIT_SPERRE} s\n")
            return 429, fehler_antwort("schreiben.dienst.besetzt")
        kennung = secrets.token_hex(6)
        tmp = Path(tempfile.mkdtemp(prefix="frieda-schreiben-"))
        arbeit = tmp / "kopie"
        abgebrochen = threading.Event()
        ergebnis = {}

        def vorbereiten():
            """Reise im Speicher?, Stand merken, exportieren. Läuft in einem Faden, damit ein hängender Speicher die Frist
            nicht überdauert; wird er nach Fristablauf doch noch fertig, räumt er den temporären Ordner selbst weg."""
            try:
                bekannt = reisespeicher.reisen()
                if not neue_reise and reise not in bekannt:   # nie aus einer leeren Arbeitskopie schreiben
                    ergebnis["basis"] = None
                elif neue_reise:
                    # bekannte Reisen als leere Ordner: neu.py prüft Namen und IDs wie in einem Repo
                    (arbeit / "reisen").mkdir(parents=True)
                    for name in sorted(set(bekannt) | set(git_reisen(s.wurzel))):
                        (arbeit / "reisen" / name).mkdir(exist_ok=True)
                    ergebnis["basis"] = 0
                else:
                    # Stufe 5 (#350): erste Umschaltung einer Reise aus Git nur mit gültigem Vergleichsstempel
                    frei, grund = reisespeicher.umschaltung_frei(reise)
                    if not frei:
                        ergebnis["gesperrt"] = grund
                        return
                    basis = reisespeicher.stand_nummer(reise)
                    reisespeicher.exportieren(reise, arbeit / "reisen" / reise, bis=basis)
                    ergebnis["basis"] = basis
            except BaseException as e:   # an den Dienst-Faden weitergeben
                ergebnis["fehler"] = e
            finally:
                if abgebrochen.is_set():
                    shutil.rmtree(tmp, ignore_errors=True)

        try:
            (tmp / "tmp").mkdir()     # temporäre Ordner des Unterprozesses (Probebau), mit diesem gelöscht
            faden = threading.Thread(target=vorbereiten, daemon=True)
            faden.start()
            faden.join(max(0.0, ende - time.monotonic()))
            if faden.is_alive():
                abgebrochen.set()
                return nicht_eingetragen(werkzeug)     # noch nichts angewendet, keine Prüfung nötig
            if isinstance(ergebnis.get("fehler"), (sqlite3.Error, OSError)):
                return speicher_fehler(werkzeug, ergebnis["fehler"])
            if "fehler" in ergebnis and ist_ablage_fehler(ergebnis["fehler"]):
                return ablage_fehler(werkzeug, reise, ergebnis["fehler"])
            if "fehler" in ergebnis:
                raise ergebnis["fehler"]
            basis = ergebnis.get("basis")
            if basis is None and "gesperrt" not in ergebnis:
                sys.stderr.write(f"Store {werkzeug} 503: trip {reise} is in FR_SPEICHERREISEN but not in the store\n")
                return 503, fehler_antwort("schreiben.dienst.reise_nicht_im_speicher")
            if "gesperrt" in ergebnis:
                sys.stderr.write(f"Store {werkzeug} 503: trip {reise} is not cleared for the switch ({ergebnis['gesperrt']})\n")
                return 503, fehler_antwort("schreiben.dienst.umschaltung_nicht_freigegeben")
            if time.monotonic() >= ende:
                return nicht_eingetragen(werkzeug)     # noch nichts angewendet, keine Prüfung nötig
            env = vorab_umgebung({**os.environ, "FR_WURZEL": str(s.wurzel), "FR_SCHREIBKOPIE": str(arbeit), "FR_VORGANG": kennung,
                                  "FR_SPEICHER_BASIS": str(basis), "FR_SB_FRIST": f"{ende - time.monotonic():.3f}",
                                  "TMPDIR": str(tmp / "tmp")}, osm_vorab)
            try:
                r = befehl_mit_frist([sys.executable, str(Path(__file__).resolve()), "anwenden", reise, werkzeug],
                                     json.dumps(anfrage), ende - time.monotonic(), env=env)
            except subprocess.TimeoutExpired:
                return nach_abbruch(s, werkzeug, kennung, reise)
            return ausgabe_lesen(r)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def speicher_gesund():
    """Antwortet die Datenbank des Reisespeichers (SELECT 1, Wartezeit ZEIT_PRUEFUNG)?"""
    import reisespeicher
    from contextlib import closing
    if not reisespeicher.pfad().exists():   # fehlt die Datenbank, ist der Speicher nicht da (nichts anlegen)
        return False
    try:
        with closing(reisespeicher.db(timeout=ZEIT_PRUEFUNG)) as v:
            v.execute("SELECT 1").fetchone()
        return True
    except (sqlite3.Error, OSError):
        return False


class Dienst(BaseHTTPRequestHandler):
    server_version = "Frieda-Schreibweg"
    sys_version = ""
    schreiber = None

    def _senden(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        pfad = self.path.split("?", 1)[0]
        if pfad == "/gesund":
            # Speicher-Reisen: die Datenbank antwortet; Git-Reisen (keine Liste oder ein Repo neben ihr): der Git-Teil
            s = self.schreiber or Schreiber(wurzel())
            try:
                liste = instanz.speicherreisen()
            except instanz.EinstellungenNichtLesbar as e:      # #361: unbekannte Liste ist nicht gesund
                sys.stderr.write(f"Error gesund 503: settings not readable: {' '.join(str(e).split())[:LOG_LAENGE]}\n")
                return self._senden(503, {"gesund": False})
            ok = speicher_gesund() if liste else True
            if ok and (not liste or (s.wurzel / ".git").exists()):
                import schreiben_git
                ok = schreiben_git.gesund(s)
            return self._senden(200 if ok else 503, {"gesund": ok})
        teile = pfad.strip("/").split("/")
        if len(teile) == 3 and teile[1] == "buchung":   # GET /<reise>/buchung/<B-id>: gibt es sie schon? (Beleg vor dem Veröffentlichen)
            if not hmac.compare_digest(self.headers.get("X-Frieda-Dienst", ""), konten.dienst_geheimnis()):
                return self._senden(403, fehler_antwort("schreiben.dienst.nur_konnektor", mit_ok=False))
            s = self.schreiber or Schreiber(wurzel())
            try:
                im_speicher = teile[0] in instanz.speicherreisen()
            except instanz.EinstellungenNichtLesbar as e:      # #361
                sys.stderr.write(f"Error buchung 503: settings not readable: {' '.join(str(e).split())[:LOG_LAENGE]}\n")
                return self._senden(503, fehler_antwort("schreiben.dienst.einstellungen_nicht_lesbar", mit_ok=False))
            if im_speicher:
                try:
                    return self._senden(200, s.buchung_im_speicher(teile[0], teile[2]))
                except (sqlite3.Error, OSError) as e:
                    sys.stderr.write(f"Error buchung 503: {' '.join(str(e).split())[:LOG_LAENGE]}\n")
                    return self._senden(503, fehler_antwort("schreiben.dienst.speicher_nicht_erreichbar", mit_ok=False))
            try:
                return self._senden(200, s.buchung_im_repo(teile[0], teile[2]))
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                sys.stderr.write(f"Error buchung 503: {' '.join(str(e).split())[:LOG_LAENGE]}\n")
                return self._senden(503, fehler_antwort("schreiben.dienst.repo_nicht_erreichbar", mit_ok=False))
        self._senden(404, fehler_antwort("schreiben.dienst.unbekannt", mit_ok=False))

    def do_POST(self):
        if not hmac.compare_digest(self.headers.get("X-Frieda-Dienst", ""), konten.dienst_geheimnis()):
            return self._senden(403, fehler_antwort("schreiben.dienst.nur_konnektor", mit_ok=False))
        teile = self.path.split("?", 1)[0].strip("/").split("/")
        if len(teile) != 2 or not REISE_MUSTER.match(teile[0]) or (teile[1] not in WERKZEUGE and teile[1] not in REPO_WERKZEUGE):
            return self._senden(404, fehler_antwort("schreiben.dienst.unbekannt", mit_ok=False))
        try:
            laenge = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            laenge = 0
        if laenge <= 0 or laenge > MAX_BODY:
            return self._senden(413, fehler_antwort("schreiben.dienst.zu_gross", mit_ok=False))
        try:
            anfrage = json.loads(self.rfile.read(laenge).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._senden(400, fehler_antwort("schreiben.dienst.kein_json", mit_ok=False))
        if not isinstance(anfrage, dict):
            return self._senden(400, fehler_antwort("schreiben.dienst.kein_objekt", mit_ok=False))
        code, antwort = anwenden_extern(self.schreiber or Schreiber(wurzel()), teile[0], teile[1], anfrage)
        self._senden(code, antwort)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.command} {self.path.split('?', 1)[0]} {args[1] if len(args) > 1 else ''}\n")


def dienst():
    host = os.environ.get("FR_SB_HOST", "127.0.0.1")
    port = int(os.environ.get("FR_SB_PORT", "8773"))
    s = Schreiber(wurzel())
    Dienst.schreiber = s
    print(f"Schreibweg auf {host}:{port}, Repo {s.wurzel}, Arbeitskopie {s.arbeit}", flush=True)
    ThreadingHTTPServer((host, port), Dienst).serve_forever()


def main(a):
    if a[:1] == ["dienst"]:
        dienst()
    elif a[:1] == ["anwenden"] and len(a) == 3:
        anfrage = json.loads(sys.stdin.read() or "{}")
        basis = os.environ.get("FR_SPEICHER_BASIS")      # gesetzt: Speicherweg (vorgang_speicher), sonst Git-Weg
        frist = os.environ.get("FR_SB_FRIST")
        code, antwort = anwenden(wurzel(), schreibkopie(), a[1], a[2], anfrage, basis=int(basis) if basis else None,
                                 frist=float(frist) if frist else None)
        print(json.dumps([code, antwort], ensure_ascii=False))
    elif a[:1] == ["normalisieren"] and len(a) == 2:
        # Routendatei einer Reise einmal rund schreiben (Normalform des Schreibwegs), in einer Sitzung im Reisen-Repo
        geaendert = routen_normalisieren(wurzel() / "reisen" / a[1])
        print(f"reisen/{a[1]}/plan/routen.yaml " + ("in Normalform gebracht." if geaendert else "war schon in Normalform."))
    elif a[:1] == ["vorbereiten"]:
        import schreiben_git
        schreiben_git.vorbereiten_aufruf()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    # Als Modul „schreiben“ ausführen, nicht als __main__: schreiben_git importiert schreiben, und zwei Kopien hätten zwei
    # Klassen Ablehnung (eine Ablehnung des Git-Wegs käme sonst als Fehler 500 an)
    import schreiben
    sys.exit(schreiben.main(sys.argv[1:]))
