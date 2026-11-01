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
           gibt (Beleg vor dem Veröffentlichen, Issue #135). Ein Schreibvorgang zur Zeit (Sperre). Je Anfrage bringt er die Arbeitskopie auf origin/main und startet dort einen
           Unterprozess `anwenden` mit dem Code dieser Arbeitskopie, damit Code und Daten denselben Stand haben.
  Arbeit   `schreiben.py anwenden` liest die Anfrage als JSON von stdin, prüft Rolle und Status, ändert die Dateien,
           baut zur Probe, committet, pusht nach main, stößt das Veröffentlichen an und antwortet auf stdout als JSON.

Arbeitskopie: <Wurzel>-schreiben (FR_SCHREIBKOPIE), ein Git-Worktree des Reisen-Repos ohne eigenen Branch (steht auf
origin/main). Sie gehört allein dem Schreibweg. Veröffentlicht wird wie nach jedem Zusammenführen: betrieb/veroeffentlichen.sh
holt main in den Bauordner (im Hintergrund; hält der Timer gerade die Sperre, holt er es nach).

Regeln vor dem Schreiben (Prüfstelle ADR-0001): Rolle und Status (reise.erlaubt mit reise.yaml der Arbeitskopie, nicht
nur mit dem, was der Konnektor sagt), Form der Arten und Merkmale (docs/ontologie.md), Probebau (routen.arten_pruefen und
alles andere, was der Generator prüft). Lehnt der Schreibweg ab, bleibt die Arbeitskopie unverändert und der AI-Client
bekommt den Grund in einfachen Worten.

Aufruf von Hand: `schreiben.py vorbereiten` (Arbeitskopie anlegen), `schreiben.py normalisieren <reise>` (Routendatei in die Form
bringen, die der Schreibweg schreibt; in einer Sitzung im Reisen-Repo).
Für Tests überschreibbar: SB_VEROEFFENTLICHEN (Skript statt betrieb/veroeffentlichen.sh), FR_SCHREIBKOPIE, FR_SB_PORT.
"""
import datetime
import fcntl
import hmac
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instanz  # noqa: E402
import konten  # noqa: E402
import texte  # noqa: E402

REISE_MUSTER = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
SCHLUESSEL_MUSTER = re.compile(r"^[a-z][a-z0-9_]*$")
MAX_BODY = 64 * 1024
MAX_TEXT = 500          # Namen, Hilfe, Fragen, Beschreibungen
MAX_WERTE = 20
# Zeitgrenzen in Sekunden: ZEIT_GESAMT + ZEIT_PRUEFUNG bleibt unter den 30 s von proxy_read_timeout
# (betrieb/vorlagen/nginx-konnektor.conf), sonst erreicht die Meldung die App nie
ZEIT_GESAMT = 25        # Sperre, Vorbereiten und Anwenden zusammen
ZEIT_SPERRE = 3         # Wartezeit auf die Sperre der Reise (Teil von ZEIT_GESAMT)
ZEIT_PRUEFUNG = 3       # nach einem Abbruch: ist der Vorgang trotzdem auf origin/main angekommen?
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
            "start_ende_setzen": "einstellung"}   # reise.AKTIONEN
HINWEISE_HOECHSTENS = 10   # neue Warnungen des Probebaus in der Antwort (Issue #142)
S = texte.satz   # Satz des Katalogs, in jeder Sprache lesbar (Bestätigungen, ADR-0006)
verbinden = texte.Satz.verbinden


def kurz_namen(geaendert):
    """Die Feldnamen am Anfang der Änderungssätze, für den Titel („beginn; ende“): bis zum ersten Leerzeichen oder Anführungszeichen,
    in der Sprache gelesen, in der der Titel steht (jeder Satz trägt seine Teile)."""
    return texte.Satz.verbinden([re.split(r"[ :„“]", str(g))[0] for g in geaendert], "; ")


def stufe_satz(s):
    """Wie routen.stufe_wort („nötig (pflicht)“), aber als Satz in jeder Sprache."""
    from routen import STUFEN_WORTE, stufe_wort
    if isinstance(s, str) and s in STUFEN_WORTE and s != "aus":
        return S("schreiben.stufe." + s) + f" ({s})"
    return stufe_wort(s)
GRUNDFORM_WORT = texte.gruppe("de", "schreiben.grundform")   # Katalog in texte_de.py (ADR-0006)


def sprache_von(reise_dir):
    """Sprache der Reise (reise.yaml sprache): in ihr schreibt der Schreibweg alles, was in Dateien der Reise landet."""
    from reise import sprache_von as von
    return von(reise_dir)


class Ablehnung(Exception):
    """Der Schreibweg lehnt ab; der Text ist für den AI-Client (einfache Worte, nennt den Grund). Der Satz steht im Katalog
    (schreiben.*, ADR-0006): Ablehnung("schreiben.werkzeug.n", feld=wert …). str(e) ist der Satz auf Deutsch (Bestand, Protokoll),
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


def git(ordner, *args, fehler=True, frist=None):
    """git-Aufruf -> stdout; mit `frist` (Sekunden) wird er danach samt Unterprozessen beendet (subprocess.TimeoutExpired)."""
    if frist is None:
        r = subprocess.run(["git", "-C", str(ordner), *args], capture_output=True, text=True)
    else:
        r = befehl_mit_frist(["git", "-C", str(ordner), *args], "", frist)
    if fehler and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def wurzel():
    return Path(os.environ.get("FR_WURZEL") or instanz.wurzel())


def schreibkopie(w=None):
    w = Path(w or wurzel())
    return Path(os.environ.get("FR_SCHREIBKOPIE") or f"{w}-schreiben")


def text_wert(args, feld, pflicht=False, laenge=MAX_TEXT, absaetze=False):
    """Ein Textfeld der Anfrage, bereinigt -> str oder None (fehlt oder leer). absaetze: Absätze (Leerzeilen) bleiben, für
    Lesetexte und Wissen; sonst wird jeder Weißraum ein Leerzeichen."""
    v = args.get(feld)
    if v is None or (isinstance(v, str) and not v.strip()):
        if pflicht:
            raise Ablehnung("schreiben.text_wert.1", feld=feld)
        return None
    if not isinstance(v, str):
        raise Ablehnung("schreiben.text_wert.2", feld=feld)
    if absaetze:
        v = "\n\n".join(" ".join(a.split()) for a in re.split(r"\n\s*\n", v.replace("\r\n", "\n")) if a.strip())
    else:
        v = " ".join(v.split())
    if len(v) > laenge:
        raise Ablehnung("schreiben.text_wert.3", feld=feld, laenge=laenge)
    return v


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
    if not re.fullmatch(ART_MUSTER, key) or key in (UNTERWEGS, ALLGEMEIN):
        raise Ablehnung("schreiben.art_definieren.2", key=key, w2=UNTERWEGS, w3=ALLGEMEIN)
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
        if not geaendert:
            raise Ablehnung("schreiben.art_definieren.10", w1=a.get('name', key), key=key)
        arten[key] = {k: a[k] for k in ("grundform", "name", "farbe", "symbol", "buchbar", "summiert", "beschreibung", "merkmale",
                                        "lesetext", "buchung_merkmale") if k in a}
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
    """Eine Kategorie der Kartenpunkte anlegen oder ändern, auch den Zusatz zu einer art. -> (Titel, Text)."""
    from bauen import KATEGORIE_FARBEN, KATEGORIE_GRUPPEN, KATEGORIE_MUSTER, SYMBOLE
    kategorien = kategorien_laden(reise_dir)
    name = text_wert(args, "bezeichnung", laenge=80)
    key = text_wert(args, "kategorie", pflicht=True, laenge=40).lower()
    if not re.fullmatch(KATEGORIE_MUSTER, key):
        raise Ablehnung("schreiben.kategorie_definieren.1", key=key)
    gruppe = text_wert(args, "gruppe", laenge=20)
    if gruppe is not None and gruppe.lower() not in KATEGORIE_GRUPPEN:
        raise Ablehnung("schreiben.kategorie_definieren.2", w1=', '.join(KATEGORIE_GRUPPEN))
    farbe = text_wert(args, "farbe", laenge=20)
    if farbe is not None and farbe.lower() not in KATEGORIE_FARBEN and not re.fullmatch(r"#[0-9a-fA-F]{6}", farbe):
        raise Ablehnung("schreiben.kategorie_definieren.3", w1=', '.join(KATEGORIE_FARBEN))
    symbol = text_wert(args, "symbol", laenge=20)
    if symbol is not None and symbol not in SYMBOLE:
        raise Ablehnung("schreiben.kategorie_definieren.4", w1=', '.join(SYMBOLE))
    einzahl = text_wert(args, "einzahl", laenge=80)
    nummeriert = bool_wert(args, "nummeriert")
    art = text_wert(args, "art", laenge=40)
    art_name, art_symbol = text_wert(args, "art_bezeichnung", laenge=80), text_wert(args, "art_symbol", laenge=20)
    art_hinweis, art_umriss = text_wert(args, "art_hinweis"), bool_wert(args, "art_umriss")
    if art_symbol is not None and art_symbol not in SYMBOLE:
        raise Ablehnung("schreiben.kategorie_definieren.5", w1=', '.join(SYMBOLE))
    if art is None and any(x is not None for x in (art_name, art_symbol, art_hinweis, art_umriss)):
        raise Ablehnung("schreiben.kategorie_definieren.6")
    grund = text_wert(args, "grund")
    geaendert = []
    if key not in kategorien:
        if name is None or gruppe is None or farbe is None:
            raise Ablehnung("schreiben.kategorie_definieren.7")
        k = {"gruppe": gruppe.lower(), "name": name}
        titel, kopf = f"Kategorie „{name}“ ({key}) angelegt", S("schreiben.antwort.kategorie.angelegt", w1=name, w2=key, w3=k["gruppe"], w4=farbe)
        neu = True
    else:
        k = kategorien[key]
        neu = False
        if gruppe is not None and gruppe.lower() != k.get("gruppe"):
            raise Ablehnung("schreiben.kategorie_definieren.8", w1=k.get('name', key), w2=k.get('gruppe'))
        if name is not None and name != k.get("name"):
            geaendert.append(S("schreiben.antwort.art.name", w1=k.get("name"), w2=name))
            k["name"] = name
    for feld, wert in (("einzahl", einzahl), ("farbe", farbe), ("symbol", symbol)):
        if wert is not None and wert != k.get(feld):
            k[feld] = wert
            geaendert.append(f"{feld} {wert}")
    if nummeriert is not None and bool(k.get("nummeriert")) != nummeriert:
        k["nummeriert"] = nummeriert or None
        if not nummeriert:
            k.pop("nummeriert", None)
        geaendert.append(S("schreiben.antwort.kategorie.nummeriert" if nummeriert else "schreiben.antwort.kategorie.nicht_nummeriert"))
    if art is not None:
        arten = k.setdefault("arten", {})
        a = arten.get(art) if isinstance(arten.get(art), dict) else {}
        for feld, wert in (("name", art_name), ("symbol", art_symbol), ("hinweis", art_hinweis)):
            if wert is not None and wert != a.get(feld):
                a[feld] = wert
                geaendert.append(f"art {art}: {feld} {wert}")
        if art_umriss is not None and bool(a.get("umriss")) != art_umriss:
            a["umriss"] = True if art_umriss else None
            if not art_umriss:
                a.pop("umriss", None)
            geaendert.append(S("schreiben.antwort.kategorie.umriss" if art_umriss else "schreiben.antwort.kategorie.ohne_umriss", w1=art))
        arten[art] = a
    if neu:
        k["farbe"] = farbe
        kategorien[key] = {f: k[f] for f in ("gruppe", "name", "einzahl", "farbe", "symbol", "nummeriert", "arten") if k.get(f)}
        text = kopf + (S("schreiben.antwort.kategorie.ausserdem", w1=", ".join(map(str, geaendert))) if geaendert else "") + "."
    else:
        if not geaendert:
            raise Ablehnung("schreiben.kategorie_definieren.9", w1=k.get('name', key), key=key)
        kategorien[key] = {f: k[f] for f in ("gruppe", "name", "einzahl", "farbe", "symbol", "nummeriert", "arten") if k.get(f)}
        titel = S("schreiben.titel.kategorie_geaendert", w1=k['name'], w2=key)
        text = S("schreiben.antwort.kategorie.geaendert", w1=k["name"], w2=key) + verbinden(geaendert) + "."
    kategorien_speichern(reise_dir, kategorien, wer)
    return titel, text + (S("schreiben.antwort.grund", w1=grund) if grund else "")


def rolle_pruefen(merkmale, key, rolle, typ):
    """Die Rolle kosten braucht den Typ geld und gilt je Art nur einmal."""
    if rolle == "kosten" and typ != "geld":
        raise Ablehnung("schreiben.rolle_pruefen.1")
    andere = next((k for k, d in merkmale.items() if k != key and isinstance(d, dict) and d.get("rolle") == rolle), None)
    if andere:
        raise Ablehnung("schreiben.rolle_pruefen.2", rolle=rolle, w2=merkmale[andere].get('name', andere), andere=andere)


def buchung_merkmal_definieren(reise_dir, wer, args, arten, art):
    """Ein Merkmal der Buchungen einer Art anlegen oder ändern (#166): Name, Typ (Auswahl mit Werten), Einheit, Hilfe, Frage.
    Keine Stufe, Rolle oder Prüfdatum: der Wert ist eine gebuchte Tatsache mit der Herkunft der Buchung. -> (Titel, Text)."""
    from routen import TYPEN, art_schluessel
    for f in ("stufe", "veraenderlich", "rolle", "auch", "nach_buchung"):
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
                                           "hilfe", "frage", "auch") if k in d}
        titel = S("schreiben.titel.merkmal_geaendert", w1=d['name'], w2=key, w3=a.get('name', art))
        text = S("schreiben.antwort.merkmal.geaendert", w1=d["name"], w2=key, w3=a.get("name", art)) + verbinden(geaendert) + "."
    a["merkmale"] = merkmale
    arten_speichern(reise_dir, arten, wer)
    return titel, text + (S("schreiben.antwort.grund", w1=grund) if grund else "")


# ---------- Werte an Dingen (plan/routen.yaml) ----------
# Die Routendatei wird mit ruamel.yaml rund gelesen und geschrieben: Kommentare, Reihenfolge und Fließform bleiben; nur von
# Hand umbrochene Fließ-Mappings werden in eine Zeile gezogen (einmalige Normalform, danach ändert ein Schreibvorgang nur seine Stelle).
ZIEL_MUSTER = re.compile(r"^(U-\d+|A-\d+|E-\d+[A-Za-z]?|V-\d+\.[a-z])$")


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
        if not cfg.get("routen"):
            cfg["routen"] = {"datei": "plan/routen.yaml"}
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
    """-> (Knoten in der Routendatei, Beschreibung) für U-…, A-…, E-… oder eine Option V-01.a."""
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


def wert_eintraege(args, k, definition, heute):
    """Die neuen Werte aus der Anfrage prüfen -> Liste von Einträgen {wert, quelle, geprueft?, notiz?, gilt?} (Daten als date).
    Herkunftspflicht: jeder Wert braucht quelle; ein veränderliches Merkmal auch geprueft (nicht in der Zukunft)."""
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
        if definition.get("typ") == "zahl":
            try:
                wert = float(str(wert).replace(",", "."))
                wert = int(wert) if wert == int(wert) else wert
            except ValueError:
                raise Ablehnung("schreiben.wert_eintraege.3", k=k)
        quelle = x.get("quelle")
        if not isinstance(quelle, str) or not quelle.strip():
            raise Ablehnung("schreiben.wert_eintraege.4", k=k)
        e = {"wert": wert, "quelle": " ".join(quelle.split())[:MAX_TEXT]}
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
    elif ziel.startswith(("U-", "A-")):
        u = (route.get("unterkuenfte" if ziel.startswith("U-") else "aufenthalte") or {}).get(ziel)
        if u is None:
            raise Ablehnung("schreiben.wert_eintragen.2", w1='Die Unterkunft' if ziel.startswith('U-') else 'Den Aufenthalt', ziel=ziel)
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


# ---------- Dinge, Wahlstellen, Optionen (plan/routen.yaml) ----------
DING_ARTEN = {"unterkunft": ("U", "unterkuenfte"), "aufenthalt": ("A", "aufenthalte"), "strecke": ("E", "strecken"), "ort": ("O", "orte")}
ID_MUSTER = re.compile(r"^(T-\d+|E-\d+[A-Za-z]?|U-\d+|A-\d+|O-\d+|V-\d+|W-\d+(\.[\w-]+)?|F-\d+|B-\d+)$")


PLAIN_FELDER = {"id", "status", "wer", "art", "wann", "typ", "ort", "von", "nach", "frage", "siehe", "bereich", "an", "unterkuenfte",
                "strecken", "folge", "erfordert", "schliesst_aus", "auswahl", "fuer"}
PLAIN_MUSTER = re.compile(r"^[A-Za-zÄÖÜäöüß][\w .\-äöüÄÖÜß]*$")


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


def merkmale_werte(roh_merkmale, krit, heute, vorgabe=None):
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
        eintraege = wert_eintraege(a, d["id"], d, heute)
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
    kuerzel, abschnitt = DING_ARTEN[was]
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    arten = route.get("arten") or {}
    quelle = text_wert(args, "quelle", pflicht=True)
    hinweis = text_wert(args, "hinweis")
    d = {}
    if was == "ort":
        d["name"] = text_wert(args, "name_des_dings", laenge=120) or text_wert(args, "titel", pflicht=True, laenge=120)
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
            d["buchungslink"] = link
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
        for k in ("ab", "an"):   # Zeitpunkte (Issue #135): HH:MM oder JJJJ-MM-TTTHH:MM+HH:MM
            if (z := zeit_wert(args, k)):
                d[k] = z
    if was == "aufenthalt":   # Uhrzeit für den Kalender (#77)
        for feld in ("beginn", "ende"):
            if (u := uhrzeit_wert(args, feld)):
                d[feld] = u
        if d.get("ende") and not d.get("beginn"):
            raise Ablehnung("schreiben.ding_anlegen.7")
    if was == "ort" and bool_wert(args, "ausserhalb"):
        d["ausserhalb"] = True   # Ort der An- und Abreise außerhalb der Reisegegend (Issue #135)
    if hinweis:
        d["hinweis"] = hinweis
    d["quelle"] = quelle
    werte = merkmale_werte(args.get("merkmale"), (route.get("merkmale") or {}).get(d.get("art")) or [], heute,
                           {"quelle": quelle, "geprueft": args.get("geprueft")}) if was != "ort" else {}
    did = neue_id(reise_dir, kuerzel)
    knoten = fliess_map(d) if was not in ("unterkunft", "aufenthalt") else block_map(d)
    if werte:
        if was == "strecke":
            knoten = block_map(d)
        knoten["merkmale"] = merkmale_knoten(werte)
    roh.setdefault(abschnitt, type(roh)())
    roh[abschnitt][did] = knoten
    name = d.get("name") or d.get("titel")
    titel = S("schreiben.titel.ding_angelegt", w1=did, w2=name, w3=S("schreiben.ding_wort." + was))
    text = (S("schreiben.antwort.ding." + was, w1=did, w2=name)
            + (S("schreiben.antwort.ding.in", w1=route.get("orte", {}).get(d["ort"], {}).get("name", d["ort"])) if was in ("unterkunft", "aufenthalt") else "")
            + (S("schreiben.antwort.ding.art", w1=d["art"]) if d.get("art") else "") + (S("schreiben.antwort.ding.merkmale", w1=", ".join(werte)) if werte else "")
            + S("schreiben.antwort.ding.herkunft_punkt", w1=quelle)
            + (S("schreiben.antwort.ding.alternative") if was == "unterkunft" else "")
            + (S("schreiben.antwort.ding.an_einen_tag") if was == "aufenthalt" else ""))
    routen_speichern(reise_dir, roh)
    return titel, text


AENDERBAR = {"unterkunft": ("name", "ort", "art", "hinweis", "quelle", "buchungslink", "frage"),
             "aufenthalt": ("name", "ort", "art", "zeit", "beginn", "ende", "hinweis", "quelle", "buchungslink", "frage"),
             "strecke": ("titel", "von", "nach", "art", "ab", "an", "hinweis", "quelle"), "ort": ("name", "hinweis", "quelle", "ausserhalb")}


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
    """Felder einer Unterkunft, Strecke oder eines Orts ändern (nicht die Merkmale: wert_eintragen). -> (Titel, Text)."""
    from reise import darf
    from routen import art_schluessel
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
    for feld in AENDERBAR[was]:
        if feld not in args or args.get(feld) is None:
            continue
        if feld == "name":
            v = text_wert(args, "name", pflicht=True, laenge=120)
        elif feld in ("ort", "von", "nach"):
            v = (id_liste(args, feld, r"O-\d+", roh, "orte", pflicht=True) or [None])[0]
        elif feld == "art":
            if not darf(wer["rolle"], "organisator"):
                raise Ablehnung("schreiben.ding_aendern.4")
            v = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
            g = "aufenthalt" if was in ("unterkunft", "aufenthalt") else "bewegung"
            if v not in arten or arten[v].get("grundform") != g:
                raise Ablehnung("schreiben.ding_aendern.5", w1=g.capitalize(), w2=', '.join(k for k, a in arten.items() if a.get('grundform') == g) or 'keine')
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
        alt = knoten.get(feld) if feld != "art" else (knoten.get("art") or art_schluessel(knoten.get("typ")))
        if v == "" and feld in ("hinweis", "buchungslink", "frage", "zeit", "beginn", "ende", "ab", "an"):
            if feld in knoten:
                geaendert.append(S("schreiben.antwort.ding.entfernt", w1=feld, w2=alt))
                del knoten[feld]
            continue
        if str(alt) == str(v):
            continue
        geaendert.append(S("schreiben.antwort.ding.wechsel", w1=feld, w2=alt, w3=v) if alt is not None else S("schreiben.antwort.ding.neu", w1=feld, w2=v))
        knoten[feld] = skalar(feld, v)
        if feld == "art" and "typ" in knoten:   # Brücke typ: entfällt, sobald art: steht
            del knoten["typ"]
    if not geaendert:
        raise Ablehnung("schreiben.ding_aendern.6", bezeichnung=bezeichnung, w2=', '.join(AENDERBAR[was]))
    if knoten.get("ende") and not knoten.get("beginn"):
        raise Ablehnung("schreiben.ding_anlegen.7")
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    titel = S("schreiben.titel.geaendert", w1=bezeichnung, w2=kurz_namen(geaendert))
    text = f"{bezeichnung}: " + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund else "")
    return titel, text


def lage_eintragen(reise_dir, wer, args, heute=None):
    """Lage einer Unterkunft (ADR-0004): Adresse und/oder Koordinaten, je mit Herkunft (quelle) und Prüfdatum. -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    ziel = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip()
    if not re.fullmatch(r"(U|A)-\d+", ziel):
        raise Ablehnung("schreiben.lage_eintragen.1")
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, ziel)
    if knoten is None:
        raise Ablehnung("schreiben.ding_aendern.2", ziel=ziel)
    quelle = text_wert(args, "quelle", pflicht=True, laenge=600)
    g = datum(args["geprueft"], "geprueft", "Lage") if args.get("geprueft") else heute
    if g > heute:
        raise Ablehnung("schreiben.lage_eintragen.2")
    adresse = text_wert(args, "adresse", laenge=300)
    punkt = None
    if args.get("koordinaten") not in (None, ""):
        try:
            punkt = [round(float(x), 6) for x in re.split(r"[,;\s]+", str(args["koordinaten"]).strip()) if x]
        except ValueError:
            punkt = []
        if len(punkt) != 2 or not (-90 <= punkt[0] <= 90 and -180 <= punkt[1] <= 180):
            raise Ablehnung("schreiben.lage_eintragen.3")
    if not adresse and not punkt:
        raise Ablehnung("schreiben.lage_eintragen.4")
    geaendert = []
    for feld, wert in (("adresse", adresse), ("punkt", punkt)):
        if not wert:
            continue
        alt = (knoten.get(feld) or {}).get("wert") if isinstance(knoten.get(feld), dict) else None
        knoten[feld] = fliess_map({"wert": wert, "quelle": quelle, "geprueft": g})
        text = ", ".join(map(str, wert)) if feld == "punkt" else wert
        geaendert.append(S("schreiben.antwort.lage.koordinaten" if feld == "punkt" else "schreiben.antwort.lage.adresse", w1=text)
                         + (S("schreiben.antwort.lage.war", w1=", ".join(map(str, alt)) if isinstance(alt, list) else alt) if alt else ""))
    routen_speichern(reise_dir, roh)
    grund = text_wert(args, "grund")
    return (S("schreiben.titel.lage", w1=bezeichnung),
            f"{bezeichnung}: " + verbinden(geaendert, "; ") + S("schreiben.antwort.lage.herkunft", w1=quelle, w2=g.isoformat()) + (S("schreiben.antwort.grund", w1=grund) if grund else ""))


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
    if sum(1 for x in (u, st, fo) if x) > 1:
        raise Ablehnung("schreiben.option_bauen.2", w1=d['titel'])
    for k, v in (("unterkuenfte", u), ("strecken", st), ("folge", fo)):
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
    an = id_liste(args, "an", r"(T-\d+|E-\d+[A-Za-z]?|U-\d+|O-\d+|V-\d+|W-\d+(\.[\w-]+)?)", roh)
    if an:
        for x in an:
            menge = {"T": "tage", "E": "strecken", "U": "unterkuenfte", "O": "orte", "V": "wahlstellen"}.get(x[0])
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
                                      "grund": f"ersetzt durch {oid} „{o['titel']}“: {grund}"}))
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
                geaendert.append(f"{feld} „{t.get(feld) or ''}“ → „{v}“")
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
            geaendert.append(f"nacht „{t.get('nacht') or '–'}“ → „{n or '–'}“")
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
            geaendert.append(f"{feld} {list(t.get(feld) or [])} → {liste}")
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
        return S("schreiben.titel.abschnitt_ergaenzt", w1=wid, w2=t), S("schreiben.antwort.abschnitt.ergaenzt_text", w1=wid, w2=t, w3=d_) + S("schreiben.antwort.herkunft", w1=quelle) + "."
    if not titel:
        raise Ablehnung("schreiben.wissen_schreiben.4")
    try:
        wid = neu.abschnitt(Path(reise_dir), titel, gruppe, datei, absatz)
    except neu.Fehler as e:
        raise Ablehnung(str(e))
    return S("schreiben.titel.titel_angelegt", w1=wid, w2=titel), S("schreiben.antwort.abschnitt.neu", w1=wid, w2=titel, w3=datei, w4=gruppe) + S("schreiben.antwort.herkunft", w1=quelle) + "."


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
            geaendert.append(f"{k} „{vorhanden.get(k)}“ → „{v}“" if vorhanden.get(k) is not None else f"{k} „{v}“")
            vorhanden[k] = skalar(k, v) if k != "name" else skalar("titel", v)
        if not geaendert:
            raise Ablehnung("schreiben.person_schreiben.7", w1=vorhanden.get('name', schluessel))
        titel = S("schreiben.titel.person_geaendert", w1=vorhanden.get('name', schluessel), w2=schluessel)
        text = f"{vorhanden.get('name', schluessel)}: " + "; ".join(geaendert) + "."
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
    return f"Status {alt or '–'} → {wert}", S("schreiben.antwort.status.text", w1=wert, w2=alt or "–", w3=wer["name"], w4=heute, w5=grund)


def einstellung_setzen(reise_dir, wer, args, heute=None):
    """Einstellungen der Reise: bausteine (vollständige Liste), regeln (Name: Wert) und sprache (de, en …); nur Organisator:innen. Was gilt, prüft der
    Probebau (reise.py). -> (Titel, Text)."""
    from reise import BAUSTEINE, KERN, VORGABEN
    from ruamel.yaml.comments import CommentedMap
    p, roh = reise_yaml_laden(reise_dir)
    geaendert = []
    bausteine = args.get("bausteine")
    if bausteine is not None:
        liste = liste_wert({"b": bausteine}, "b", laenge=20) or []
        fremd = [b for b in liste if b not in BAUSTEINE and b not in KERN]
        if fremd:
            raise Ablehnung("schreiben.einstellung_setzen.1", w1=', '.join(fremd), w2=', '.join(BAUSTEINE))
        liste = [b for b in dict.fromkeys(liste) if b not in KERN]
        if list(roh.get("bausteine") or []) != liste:
            geaendert.append(f"bausteine {list(roh.get('bausteine') or [])} → {liste}")
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
            geaendert.append(f"regeln.{k} „{r.get(k, VORGABEN[k])}“ → „{v}“")
            r[k] = skalar(k, v) if isinstance(v, str) else v
    sprache = args.get("sprache")
    if sprache not in (None, ""):
        sprache = str(sprache).strip().lower()
        if not texte.gueltig(sprache):
            raise Ablehnung("schreiben.einstellung_setzen.3", sprache=sprache, w2=', '.join(texte.SPRACHEN))
        if str(roh.get("sprache") or texte.BESTAND_REISE) != sprache:
            geaendert.append(f"sprache „{roh.get('sprache') or texte.BESTAND_REISE}“ → „{sprache}“")
            roh["sprache"] = sprache
    if not geaendert:
        raise Ablehnung("schreiben.einstellung_setzen.4")
    grund = text_wert(args, "grund")
    reise_yaml_speichern(p, roh)
    return S("schreiben.titel.einstellungen", w1=kurz_namen(geaendert)), \
        S("schreiben.antwort.einstellungen.kopf") + verbinden(geaendert, "; ") + "." + (S("schreiben.antwort.grund", w1=grund) if grund else "")


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


BUCHUNG_TEXTE = {"nummer": 80, "bei": 120, "preis": 120, "bezahlt": 200, "frist_was": 120, "storno": 400, "notiz": MAX_TEXT, "ab_was": 120}
# Felder einer Buchung in Worten für Antwort und Verlauf (Menschen lesen Wörter, keine Schlüssel; Product Owner 29.10.2026)
BUCHUNG_WORTE = texte.gruppe("de", "schreiben.buchung")


def zahlung_wert(args):
    """zahlung (Zahlstand, #166) aus der Anfrage -> Schlüssel, "" (leer: entfernen) oder None (nicht angegeben)."""
    from routen import ZAHLUNG, ZAHLUNG_ALIAS, ZAHLUNG_WORTE, zahlung_schluessel
    if args.get("zahlung") is None:
        return None
    v = text_wert(args, "zahlung", laenge=20)
    if v is None:
        return ""
    z = zahlung_schluessel(v)
    if z is None:
        raise Ablehnung("schreiben.zahlung.ungueltig", w1=", ".join(ZAHLUNG), w2=", ".join(ZAHLUNG_ALIAS),
                        w3="; ".join(ZAHLUNG_WORTE[k] for k in ZAHLUNG))
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


def buchung_anlegen(reise_dir, wer, args, heute=None):
    """Eine Buchung anlegen (neue B-ID): zu welchen Dingen, Status, Nummer, Anbieter, Preis, Zahlstand, Frist, Stornoregel, Merkmale
    der Buchung, Herkunft. -> (Titel, Text)."""
    from routen import BUCHUNG_STATUS, ZAHLUNG_WORTE
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
    for k in ("frist", "storno_bis", "gebucht_am", "ab"):
        v = datum_wert(args, k)
        if v:
            d[k] = v
    d.setdefault("gebucht_am", heute)
    pers, preise = buchung_personen(args, reise_dir), buchung_preise(args, fuer)
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
    knoten = block_map(d)
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
            + (S("schreiben.antwort.buchung.zahlung", w1=ZAHLUNG_WORTE[zahlung]) if zahlung else "") + (f" ({d['bezahlt']})" if d.get("bezahlt") else "")
            + (f", {merkmale_text(mk, buchung_merkmal_defs(route, fuer)[0])}" if mk else "")
            + (S("schreiben.antwort.buchung.frist", w1=d["frist"]) + (f" ({d['frist_was']})" if d.get("frist_was") else "") if d.get("frist") else "")
            + (S("schreiben.antwort.buchung.storno", w1=d["storno"]) if d.get("storno") else "")
            + (S("schreiben.antwort.buchung.storno_bis", w1=d["storno_bis"]) if d.get("storno_bis") else "")
            + (S("schreiben.antwort.buchung.ab", w1=d["ab"]) + (f" ({d['ab_was']})" if d.get("ab_was") else "") if d.get("ab") else "")
            + (S("schreiben.antwort.buchung.preise", w1=", ".join(f"{k} {v}" for k, v in preise.items())) if preise else "")
            + (S("schreiben.antwort.buchung.reisende_liste", w1=", ".join(f"{k}{(' (' + v + ')') if v else ''}" for k, v in pers.items())) if pers else "")
            + S("schreiben.antwort.herkunft", w1=quelle) + ".")   # zum Beleg sagt der Konnektor etwas: er weiß, ob einer mitkam
    return titel, text


def buchung_dingname(roh, route, x):
    d = (roh.get("unterkuenfte") or {}).get(x) or (roh.get("aufenthalte") or {}).get(x) or {}
    return d.get("name") or ((route.get("strecken") or {}).get(x) or {}).get("titel") or ((roh.get("strecken") or {}).get(x) or {}).get("titel") or ""


def buchung_aendern(reise_dir, wer, args, heute=None):
    """Felder einer Buchung ändern (Status, Nummer, Frist, Storno …); jede Änderung bekommt einen Verlaufseintrag mit Person,
    Datum und Grund. Leerer Text entfernt ein Feld. -> (Titel, Text)."""
    from routen import BUCHUNG_STATUS, ZAHLUNG_WORTE
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
                kurz.append(f"{wort or feld} entfernt")
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
    for k in ("frist", "storno_bis", "gebucht_am", "ab"):
        v = datum_wert(args, k)
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
                geaendert.append(S("schreiben.antwort.buchung.zahlung_von", w1=ZAHLUNG_WORTE.get(alt_z, alt_z), w2=ZAHLUNG_WORTE[zahlung]) if alt_z
                                 else S("schreiben.antwort.buchung.zahlung_neu", w1=ZAHLUNG_WORTE[zahlung]))
                if "zahlung" not in knoten and "bezahlt" in knoten:   # vor seinen Einzelheiten
                    knoten.insert(list(knoten).index("bezahlt"), "zahlung", zahlung)
                else:
                    knoten["zahlung"] = zahlung
            else:
                geaendert.append(S("schreiben.antwort.buchung.zahlung_weg", w1=ZAHLUNG_WORTE.get(alt_z, alt_z)))
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
            geaendert.append(S("schreiben.antwort.buchung.merkmale_kopf", w1="; ".join(([merkmale_text(anders, defs)] if anders else [])
                                                     + [S("schreiben.antwort.buchung.merkmal_entfernt", w1=(defs.get(k) or {}).get("name", k)) for k in weg])))
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
    if not geaendert:
        raise Ablehnung("schreiben.buchung_aendern.6", bid=bid, w2=', '.join(BUCHUNG_TEXTE))
    from ruamel.yaml.comments import CommentedSeq
    verlauf = knoten.get("verlauf")
    if verlauf is None:
        verlauf = CommentedSeq()
        knoten["verlauf"] = verlauf
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": "; ".join(kurz), **({"grund": grund} if grund else {})}))
    routen_speichern(reise_dir, roh)
    fuer = knoten.get("fuer")
    fuer = [fuer] if isinstance(fuer, str) else list(fuer or [])
    namen = ", ".join(f"{x} {buchung_dingname(roh, route, x)}" for x in fuer)
    titel = S("schreiben.titel.geaendert", w1=bid, w2="; ".join(kurz))
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
            geaendert.append(f"Titel „{titel}“ → „{neuer_titel}“"); alt["titel"] = skalar("x", neuer_titel)
        if ort is not None and ort != alt.get("ort"):
            geaendert.append(f"Ort {ort or '–'}"); (alt.__setitem__("ort", ort) if ort else alt.pop("ort", None))
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
                geaendert.append(f"{feld} „{w.get(feld) or ''}“ → „{v}“")
                (w.__setitem__(feld, skalar(feld, v)) if v else w.pop(feld, None))
    if args.get("wann") is not None:
        wann = str(args.get("wann") or "").strip().lower()
        if wann not in ("planung", "unterwegs"):
            raise Ablehnung("schreiben.wahlstelle_aendern.3")
        alt = w.get("wann") or (w.get("art") if w.get("art") in ("planung", "unterwegs") else "planung")
        if wann != alt:
            geaendert.append(f"wann {alt} → {wann}")
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
            geaendert.append(f"an {list(w.get('an') or [])} → {an}")
            (w.__setitem__("an", fliess_map({"an": an})["an"]) if an else w.pop("an", None))
    if args.get("frage") is not None:
        f = str(args.get("frage") or "").strip()
        if f and not re.fullmatch(r"F-\d+", f):
            raise Ablehnung("schreiben.wahlstelle_aendern.5")
        if f != (w.get("frage") or ""):
            geaendert.append(f"frage {w.get('frage') or '–'} → {f or '–'}")
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


def option_aendern(reise_dir, wer, args, heute=None):
    """Felder einer Option ändern: titel, text, plus, minus, erfordert, schliesst_aus, ausloeser, siehe, unterkuenfte, strecken,
    folge, quelle; favorisieren (favorisiert: true mit grund) als Verlaufseintrag (Mitwirkende dürfen; gewählt, verworfen,
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
                geaendert.append(f"{feld} „{knoten.get(feld) or ''}“ → „{v}“")
                (knoten.__setitem__(feld, skalar(feld, v)) if v else knoten.pop(feld, None))
    for feld in ("plus", "minus"):
        if args.get(feld) is not None:
            l = liste_wert(args, feld, laenge=10) or []
            if list(knoten.get(feld) or []) != l:
                geaendert.append(f"{feld} {list(knoten.get(feld) or [])} → {l}")
                (knoten.__setitem__(feld, fliess_map({feld: l})[feld]) if l else knoten.pop(feld, None))
    if args.get("siehe") is not None:
        s = str(args.get("siehe") or "").strip()
        if s and not ID_MUSTER.match(s):
            raise Ablehnung("schreiben.option_aendern.3")
        if s != (knoten.get("siehe") or ""):
            geaendert.append(f"siehe {knoten.get('siehe') or '–'} → {s or '–'}")
            (knoten.__setitem__("siehe", s) if s else knoten.pop("siehe", None))
    optionen_ids = {x["id"] for w in route.get("wahlstellen") or [] for x in w["optionen"]}
    for feld in ("erfordert", "schliesst_aus"):
        if args.get(feld) is not None:
            l = id_liste(args, feld, r"V-\d+\.[a-z]", roh) or []
            fehlt = [x for x in l if x not in optionen_ids]
            if fehlt or any(x.startswith(vid + ".") for x in l):
                raise Ablehnung("schreiben.option_aendern.4", feld=feld, w2=', '.join(fehlt) or 'eine Option derselben Wahlstelle')
            if list(knoten.get(feld) or []) != l:
                geaendert.append(f"{feld} {list(knoten.get(feld) or [])} → {l}")
                (knoten.__setitem__(feld, fliess_map({feld: l})[feld]) if l else knoten.pop(feld, None))
    inhalt = {}
    for feld, muster, menge in (("unterkuenfte", r"U-\d+", "unterkuenfte"), ("strecken", r"E-\d+[A-Za-z]?", "strecken"), ("folge", r"T-\d+", "tage")):
        if args.get(feld) is not None:
            inhalt[feld] = id_liste(args, feld, muster, roh, menge) or []
    if inhalt:
        neu = {f: (inhalt[f] if f in inhalt else list(knoten.get(f) or [])) for f in ("unterkuenfte", "strecken", "folge")}
        if sum(1 for v in neu.values() if v) > 1:
            raise Ablehnung("schreiben.option_aendern.5")
        for f, l in inhalt.items():
            if list(knoten.get(f) or []) != l:
                geaendert.append(f"{f} {list(knoten.get(f) or [])} → {l}")
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
    geaendert = []
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
        geaendert.append(f"Titel „{titel}“ → „{neuer_titel}“")
    if not geaendert:
        raise Ablehnung("schreiben.wissen_aendern.6")
    f.write_text("\n".join(zeilen).rstrip("\n") + "\n", encoding="utf-8")
    return S("schreiben.titel.geaendert", w1=wid, w2="; ".join(geaendert)), S("schreiben.antwort.abschnitt.kopf", w1=wid, w2=neuer_titel or titel, w3=datei) + verbinden(geaendert, "; ") + S("schreiben.antwort.abschnitt.grund_ende", w1=grund)


def lesetext_schreiben(reise_dir, wer, args, heute=None):
    """Den Lesetext einer Etappe (Abschnitt „Zusammenfassung“ im Etappen-Dossier, Ebene „Der Weg“) schreiben oder ersetzen,
    gegliedert nach den Rubriken der Art (je Absatz „**Rubrik.** …“); Herkunft Pflicht. -> (Titel, Text)."""
    import json
    heute = heute or datetime.date.today()
    eid = (text_wert(args, "ziel", pflicht=True, laenge=12) or "").strip().upper()
    if not re.fullmatch(r"E-\d+[A-Za-z]?", eid):
        raise Ablehnung("schreiben.lesetext_schreiben.1")
    text = text_wert(args, "text", pflicht=True, laenge=12000, absaetze=True)
    quelle = text_wert(args, "quelle", pflicht=True)
    cfg = json.loads((Path(reise_dir) / "reise.json").read_text(encoding="utf-8"))
    d_rel = cfg.get("etappen_dossier")
    if not d_rel or not (Path(reise_dir) / d_rel).exists():
        raise Ablehnung("schreiben.lesetext_schreiben.2")
    import bauen
    muster = re.compile(cfg.get("etappen_muster") or bauen.etappen_muster())
    f = Path(reise_dir) / d_rel
    zeilen = f.read_text(encoding="utf-8").split("\n")
    start = None
    for i, z in enumerate(zeilen):
        m = z.startswith("## ") and muster.match(z[3:].strip())
        if m and "E-" + (m.group(1).zfill(3) if m.group(1)[-1].isalpha() else m.group(1).zfill(2)) == eid:
            start = i
            break
    if start is None:
        raise Ablehnung("schreiben.lesetext_schreiben.3", eid=eid, d_rel=d_rel)
    ende = next((i for i in range(start + 1, len(zeilen)) if zeilen[i].startswith("## ")), len(zeilen))
    # Rubriken der Art prüfen: jedes fette Stichwort am Absatzanfang muss eine Rubrik sein, wenn die Art eine Gliederung hat
    route = route_stand(reise_dir)
    st = (route.get("strecken") or {}).get(eid) or {}
    rubriken = (((route.get("arten") or {}).get(st.get("art_schluessel"))) or {}).get("lesetext") or []
    if rubriken:
        namen = {r["name"].casefold() for r in rubriken}
        fremd = [w for w in re.findall(r"^\*\*([^*]{1,60})\*\*", text, flags=re.M) if w.strip().rstrip(".:").casefold() not in namen]
        if fremd:
            raise Ablehnung("schreiben.lesetext_schreiben.4", w1=fremd[0].strip().rstrip('.:'), w2=', '.join(r['name'] for r in rubriken), eid=eid)
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


def reise_aendern(reise_dir, wer, args, heute=None):
    """Eckdaten der Reise ändern: titel, untertitel, kurz, von, bis (Zeitraum). Nur Organisator:innen, mit grund; der Verlauf
    steht in reise.yaml unter verlauf. -> (Titel, Text)."""
    from ruamel.yaml.comments import CommentedSeq
    heute = heute or datetime.date.today()
    grund = text_wert(args, "grund", pflicht=True)
    p, roh = reise_yaml_laden(reise_dir)
    geaendert = []
    for feld, laenge in (("titel", 120), ("untertitel", 200), ("kurz", 40)):
        if args.get(feld) is not None:
            v = text_wert(args, feld, laenge=laenge) or ""
            if feld == "titel" and not v:
                raise Ablehnung("schreiben.wahlstelle_aendern.2")
            if v != (roh.get(feld) or ""):
                geaendert.append(f"{feld} „{roh.get(feld) or ''}“ → „{v}“")
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
                geaendert.append(f"{k} {z.get(k) or '–'} → {v}")
                z[k] = v
    if not geaendert:
        raise Ablehnung("schreiben.reise_aendern.3")
    verlauf = roh.get("verlauf")
    if verlauf is None:
        verlauf = CommentedSeq()
        roh["verlauf"] = verlauf
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": "; ".join(geaendert), "grund": grund}))
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
        name = ("Start" if teil == "start" else "Ende") + " des Plans: " + ("Datum" if feld == "datum" else "Ort")
        geaendert.append(f"{name} {alt or '–'} → {v}" if v else f"{name} {alt} entfernt")
        satz_name = S(f"schreiben.antwort.start_ende.{teil}_{feld}")
        antwort_teile.append(satz_name + f" {alt or '–'} → {v}" if v else satz_name + f" {alt}" + S("schreiben.antwort.start_ende.entfernt"))
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
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": "; ".join(geaendert), "grund": grund}))
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
                    geaendert.append(f"{feld} „{d.get(feld) or ''}“ → „{v}“")
                (d.__setitem__(feld, skalar(feld, v)) if v else d.pop(feld, None))
    if args.get("farbe") is not None:
        farbe = str(args.get("farbe") or "").strip().lower()
        if farbe not in PLAN_FARBEN:
            raise Ablehnung("schreiben.plan_felder.1", w1=', '.join(PLAN_FARBEN))
        if farbe != d.get("farbe"):
            if geaendert is not None:
                geaendert.append(f"farbe {d.get('farbe') or '–'} → {farbe}")
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
                geaendert.append(f"auswahl {list(d.get('auswahl') or [])} → {auswahl}")
            d["auswahl"] = fliess_map({"auswahl": auswahl})["auswahl"]
    for feld in ("plus", "minus"):
        if args.get(feld) is not None:
            l = liste_wert(args, feld, laenge=10) or []
            if list(d.get(feld) or []) != l:
                if geaendert is not None:
                    geaendert.append(f"{feld} {list(d.get(feld) or [])} → {l}")
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
            if isinstance(knoten, dict) and (knoten.get("art") or art_schluessel_von(knoten)) == art:
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


def art_schluessel_von(knoten):
    from routen import art_schluessel
    return art_schluessel(knoten.get("typ")) if knoten.get("typ") else None


def arten_uebernehmen(reise_dir, wer, args, heute=None):
    """Arten (mit Merkmalen und Gliederung) einer anderen Reise derselben Person als Kopie übernehmen, nur die, die es hier noch
    nicht gibt (oder die in „arten“ genannten). Nur auf ausdrückliche Nachfrage (Product Owner 28.10.2026); der Konnektor
    prüft, dass die Person auf beiden Reisen dabei ist. Nur Organisator:innen. -> (Titel, Text)."""
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
            + verbinden([S("schreiben.antwort.uebernommen_art", w1=a, w2=fremd[a].get("name", a), w3=len(fremd[a].get("merkmale") or {})) for a in gewuenscht]) + "."
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
             "start_ende_setzen": start_ende_setzen}
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
    """Arbeitskopie des Reisen-Repos für den Schreibweg: holen, ändern, prüfen, sichern, veröffentlichen."""

    def __init__(self, wurzel, arbeit=None, veroeffentlichen=None):
        self.wurzel = Path(wurzel)
        self.arbeit = Path(arbeit or schreibkopie(self.wurzel))
        self.veroeffentlichen = veroeffentlichen or os.environ.get("SB_VEROEFFENTLICHEN") \
            or str(self.wurzel / "frieda" / "betrieb" / "veroeffentlichen.sh")
        self.ende = None     # time.monotonic(), bis zu der ein Vorgang fertig sein muss (anwenden_extern); None: ohne Frist

    def rest(self):
        """Sekunden bis self.ende (None: ohne Frist)."""
        return None if self.ende is None else self.ende - time.monotonic()

    def vorbereiten(self):
        """Arbeitskopie anlegen oder auf origin/main bringen; eigene Reste verwerfen. Jeder git-Aufruf bekommt den Rest der
        Frist (subprocess.TimeoutExpired, wenn sie abläuft)."""
        git(self.wurzel, "fetch", "-q", "origin", "main", frist=self.rest())
        if not (self.arbeit / ".git").exists():
            self.arbeit.parent.mkdir(parents=True, exist_ok=True)
            git(self.wurzel, "worktree", "prune", frist=self.rest())
            git(self.wurzel, "worktree", "add", "-q", "--detach", str(self.arbeit), "origin/main", frist=self.rest())
        else:
            git(self.arbeit, "reset", "-q", "--hard", frist=self.rest())
            git(self.arbeit, "clean", "-qfd", "--", "reisen", frist=self.rest())
            git(self.arbeit, "checkout", "-q", "--detach", "origin/main", frist=self.rest())
        if (self.arbeit / ".gitmodules").exists():
            git(self.arbeit, "submodule", "update", "--init", "--quiet", frist=self.rest())

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

    def schreiben(self, reise, werkzeug, anfrage):
        """Ein Schreibvorgang in der vorbereiteten Arbeitskopie -> {"ok": True, "text", "commit"}; sonst Ablehnung."""
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
                git(self.arbeit, "reset", "-q", "--hard")
                git(self.arbeit, "clean", "-qfd", "--", "reisen")
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
                git(self.arbeit, "checkout", "-q", "--", f"reisen/{reise}")
                git(self.arbeit, "clean", "-qfd", "--", f"reisen/{reise}")
                raise
        if not git(self.arbeit, "status", "--porcelain", "--", f"reisen/{reise}"):
            raise Ablehnung("schreiben.schreiben.4")
        sp = sprache_von(reise_dir)   # Titel, Text und Fuß des Commits stehen in der Sprache der Reise (Variante A)
        nachricht = (f"{wer['titel']}: {titel.text(sp) if isinstance(titel, texte.Satz) else titel}\n\n"
                     f"{text.text(sp) if isinstance(text, texte.Satz) else text}\n\n"
                     + texte.t(sp, "inhalt.schreiben.commit_fuss", werkzeug=werkzeug, wer=wer["name"], rolle=wer["rolle"],
                               datum=datetime.date.today().isoformat()) + "\n")
        if os.environ.get("FR_VORGANG"):     # Kennung des Vorgangs: nach einem Abbruch findet vorgang_eingetragen den Eintrag
            nachricht += f"\nFrieda-Vorgang: {os.environ['FR_VORGANG']}\n"
        git(self.arbeit, "add", "-A", "--", f"reisen/{reise}")
        git(self.arbeit, "commit", "-q", "-m", nachricht)
        commit = self.hochladen(reise)
        self.veroeffentlichen_anstossen()
        antwort = {"ok": True, "text": text, "commit": commit}
        if isinstance(text, texte.Satz) and text.mit_schluesseln():   # der Konnektor setzt den Satz in der Sprache der Person zusammen
            antwort["text_teile"] = text.teile_json()
        if (m := re.match(r"^([A-Z]+-\d+(?:\.[\w-]+)?) ", titel)):   # neu angelegtes Ding: seine ID, damit der Konnektor weitermachen kann
            antwort["id"] = m.group(1)
        if hinweise:   # nur neue Warnungen; reise_anlegen (REPO_WERKZEUGE) hat keinen Vergleich
            antwort["hinweise"] = [str(h) for h in hinweise]
            antwort["hinweise_teile"] = [h.teile_json() if isinstance(h, texte.Satz) else str(h) for h in hinweise]
        return antwort

    def buchung_im_repo(self, reise, bid):
        """Gibt es die Buchung B-… auf origin/main (auch wenn die Seite noch nicht neu gebaut ist)? -> {"gibt_es", "fuer", "wer"}.
        Liest nur (git show), ohne Sperre und ohne Arbeitskopie; der Konnektor fragt so, bevor er einen Beleg ablegt (Issue #135)."""
        import yaml
        if not REISE_MUSTER.match(reise or "") or not re.fullmatch(r"B-\d+", bid or ""):
            return {"gibt_es": False}
        git(self.wurzel, "fetch", "-q", "origin", "main", frist=ZEIT_PRUEFUNG)
        text = git(self.wurzel, "show", f"origin/main:reisen/{reise}/plan/routen.yaml", fehler=False, frist=ZEIT_PRUEFUNG)
        try:
            b = ((yaml.safe_load(text) or {}).get("buchungen") or {}).get(bid) if text else None
        except yaml.YAMLError:
            b = None
        if not isinstance(b, dict):
            return {"gibt_es": False}
        fuer = b.get("fuer")
        return {"gibt_es": True, "fuer": [fuer] if isinstance(fuer, str) else [str(x) for x in (fuer or [])], "wer": b.get("wer")}

    def hochladen(self, reise):
        """Nach main pushen; kam inzwischen etwas anderes an, darauf aufsetzen (höchstens dreimal)."""
        for versuch in range(3):
            r = subprocess.run(["git", "-C", str(self.arbeit), "push", "-q", "origin", "HEAD:main"], capture_output=True, text=True)
            if r.returncode == 0:
                return git(self.arbeit, "rev-parse", "HEAD")
            sys.stderr.write(f"Hochladen, Versuch {versuch + 1}: git push fehlgeschlagen: {r.stderr.strip()}\n")
            git(self.arbeit, "fetch", "-q", "origin", "main")
            rb = subprocess.run(["git", "-C", str(self.arbeit), "rebase", "-q", "origin/main"], capture_output=True, text=True)
            if rb.returncode != 0:
                sys.stderr.write(f"Hochladen, Versuch {versuch + 1}: git rebase fehlgeschlagen: {rb.stderr.strip() or rb.stdout.strip()}\n")
                git(self.arbeit, "rebase", "--abort", fehler=False)
                git(self.arbeit, "reset", "-q", "--hard", "origin/main")
                raise Ablehnung("schreiben.hochladen.1", reise=reise)
        git(self.arbeit, "reset", "-q", "--hard", "origin/main")
        raise Ablehnung("schreiben.hochladen.2")

    def veroeffentlichen_anstossen(self):
        """Veröffentlichen im Hintergrund (holt main in den Bauordner, baut, prüft). Hält der Timer die Sperre,
        meldet das Skript „Läuft schon“, und der Timer holt es in wenigen Minuten nach. Niedrige Priorität wie im Dienst
        veroeffentlichen.service, damit Schreibvorgänge während der Tests nicht warten (fehlen nice oder ionice, ohne sie).
        Die Ausgabe geht nach /dev/null: Die Ausgabe des Anwendens ist die Leitung zum Dienst, die das Skript sonst bis zu
        seinem Ende offen hielte. Ein fehlgeschlagener Lauf wiederholt der Timer, mit Protokoll. Wirft nie."""
        if not self.veroeffentlichen or not Path(self.veroeffentlichen).exists():
            return
        env = {**os.environ, "FR_WURZEL": str(self.wurzel)}
        prioritaet = (["nice", "-n", "10"] if shutil.which("nice") else []) + \
                     (["ionice", "-c", "2", "-n", "7"] if shutil.which("ionice") else [])
        for argv in ([*prioritaet, self.veroeffentlichen], [self.veroeffentlichen]):
            try:
                subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
                return
            except OSError as e:
                sys.stderr.write(f"Veröffentlichen nicht gestartet ({' '.join(argv[:1])}): {e}\n")


def anwenden(wurzel_, arbeit, reise, werkzeug, anfrage):
    """Ein Schreibvorgang (Arbeitskopie ist vorbereitet) -> Antwort-Objekt mit HTTP-Code."""
    s = Schreiber(wurzel_, arbeit)
    try:
        return 200, s.schreiben(reise, werkzeug, anfrage)
    except Ablehnung as e:
        # Grund ins Protokoll (Werkzeug, Code, Regel; ein Zeilenumbruch oder Überlänge hat dort nichts zu suchen)
        grund = " ".join(str(e).split())[:LOG_LAENGE]
        sys.stderr.write(f"Abgelehnt {werkzeug} 422: {grund}\n")
        antwort = {"ok": False, "fehler": str(e)}
        if e.schluessel:   # der Konnektor setzt den Satz in der Sprache der Person zusammen
            antwort.update(fehler_code=e.schluessel, werte=e.werte_json())
        return 422, antwort


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
    """Ist der Vorgang mit dieser Kennung auf origin/main angekommen? -> True, False oder None (Prüfung nicht möglich).
    Holen und Suchen zusammen höchstens ZEIT_PRUEFUNG Sekunden; der alte Stand von origin/main gilt nicht als Antwort."""
    ende = time.monotonic() + ZEIT_PRUEFUNG
    try:
        git(s.wurzel, "fetch", "-q", "origin", "main", frist=ende - time.monotonic())
        return bool(git(s.wurzel, "log", "--format=%H", "--fixed-strings", f"--grep=Frieda-Vorgang: {kennung}", "origin/main",
                        frist=ende - time.monotonic()))
    except (RuntimeError, subprocess.TimeoutExpired):
        return None


def nicht_eingetragen(werkzeug):
    sys.stderr.write(f"Zeit {werkzeug} 504: abgebrochen, nicht eingetragen\n")
    return 504, fehler_antwort("schreiben.dienst.zu_lange_nicht")


def nach_abbruch(s, werkzeug, kennung):
    """Antwort, nachdem das Anwenden von der Frist abgebrochen wurde: Ergebnis auf origin/main nachsehen."""
    ergebnis = vorgang_eingetragen(s, kennung)
    if ergebnis:
        sys.stderr.write(f"Zeit {werkzeug} 504: abgebrochen, eingetragen\n")
        text = S("schreiben.dienst.verzoegert")
        return 200, {"ok": True, "text": str(text), "text_teile": text.teile_json(), "hinweis": str(text)}
    if ergebnis is False:
        return nicht_eingetragen(werkzeug)
    sys.stderr.write(f"Zeit {werkzeug} 504: abgebrochen, ungeprüft\n")
    return 504, fehler_antwort("schreiben.dienst.zu_lange_ungeprueft")


def anwenden_extern(s, reise, werkzeug, anfrage):
    """Arbeitskopie holen und `anwenden` mit dem Code der Arbeitskopie ausführen -> (Code, Antwort).
    Sperre und Arbeitskopie gibt es je Reise: Was bei einer Reise hängt, hält die anderen nicht auf (flock gilt auch zwischen
    Threads, jeder öffnet die Datei selbst). Alles zusammen dauert höchstens ZEIT_GESAMT + ZEIT_PRUEFUNG Sekunden; die Dauer
    jedes Vorgangs steht im Protokoll, auch nach einem unerwarteten Fehler (500)."""
    start = time.monotonic()
    code, antwort = 500, fehler_antwort("schreiben.dienst.fehlgeschlagen")
    try:
        code, antwort = vorgang(s, reise, werkzeug, anfrage, start)
    except Exception as e:
        grund = " ".join(f"{type(e).__name__}: {e}".split())[:LOG_LAENGE]
        sys.stderr.write(f"Fehler {werkzeug} 500: {grund}\n")
    finally:
        sys.stderr.write(f"Fertig {werkzeug} {code} in {time.monotonic() - start:.1f} s\n")
    return code, antwort


def git_sperren_raeumen(arbeit):
    """Veraltete Sperren von git (index.lock, HEAD.lock …) im eigenen git-Ordner der Arbeitskopie entfernen: Ein nach Fristablauf
    beendetes git kann sie hinterlassen. Nur unter der Sperre der Reise aufrufen; der gemeinsame git-Ordner des Repos bleibt
    unberührt (dort arbeiten andere Reisen und das Veröffentlichen). Die Arbeitskopie ist ein Worktree: .git ist eine Datei
    „gitdir: <Repo>/.git/worktrees/<Name>“."""
    punkt_git = Path(arbeit) / ".git"
    if punkt_git.is_file():
        zeile = punkt_git.read_text(encoding="utf-8").strip()
        if not zeile.startswith("gitdir:"):
            return
        gitdir = Path(arbeit) / zeile[len("gitdir:"):].strip()     # absolut bleibt absolut
    elif punkt_git.is_dir():
        gitdir = punkt_git
    else:
        return
    for f in gitdir.glob("*.lock"):
        f.unlink(missing_ok=True)
        sys.stderr.write(f"Arbeitskopie: veraltete Sperre {f.name} entfernt\n")


def vorgang(s, reise, werkzeug, anfrage, start):
    s = Schreiber(s.wurzel, Path(f"{s.arbeit}-{reise}"), s.veroeffentlichen)
    s.ende = start + ZEIT_GESAMT
    with open(sperrdatei(reise), "w") as f:
        if not sperre_nehmen(f):
            sys.stderr.write(f"Gesperrt {werkzeug} 429: Sperre der Reise nach {ZEIT_SPERRE} s noch belegt\n")
            return 429, fehler_antwort("schreiben.dienst.besetzt")
        try:
            git_sperren_raeumen(s.arbeit)     # unter der Sperre der Reise: kein anderes git arbeitet in dieser Kopie
            s.vorbereiten()
        except subprocess.TimeoutExpired:
            return nicht_eingetragen(werkzeug)     # noch nichts angewendet, keine Prüfung nötig
        except RuntimeError as e:
            sys.stderr.write(f"Arbeitskopie: {e}\n")
            return 503, fehler_antwort("schreiben.dienst.repo_nicht_erreichbar_spaeter")
        skript = s.arbeit / "engine" / "schreiben.py"
        if not skript.exists():
            sys.stderr.write(f"Arbeitskopie: {skript} fehlt\n")
            return 503, fehler_antwort("schreiben.dienst.software_alt")
        if s.rest() <= 0:
            return nicht_eingetragen(werkzeug)
        kennung = secrets.token_hex(6)
        try:
            r = befehl_mit_frist([sys.executable, str(skript), "anwenden", reise, werkzeug], json.dumps(anfrage), s.rest(),
                                 env={**os.environ, "FR_WURZEL": str(s.wurzel), "FR_SCHREIBKOPIE": str(s.arbeit),
                                      "FR_VORGANG": kennung})
        except subprocess.TimeoutExpired:
            return nach_abbruch(s, werkzeug, kennung)
        if r.stderr:
            sys.stderr.write(r.stderr)
        try:
            code, antwort = json.loads(r.stdout)
            return int(code), antwort
        except (ValueError, TypeError):
            sys.stderr.write(f"anwenden: Code {r.returncode}, Ausgabe: {r.stdout[-500:]}\n")
            return 500, fehler_antwort("schreiben.dienst.fehlgeschlagen")


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
            s = self.schreiber or Schreiber(wurzel())
            ok = (s.wurzel / ".git").exists() and subprocess.run(["git", "-C", str(s.wurzel), "rev-parse", "--git-dir"],
                                                               capture_output=True).returncode == 0
            return self._senden(200 if ok else 503, {"gesund": ok})
        teile = pfad.strip("/").split("/")
        if len(teile) == 3 and teile[1] == "buchung":   # GET /<reise>/buchung/<B-id>: gibt es sie im Repo? (Beleg vor dem Veröffentlichen)
            if not hmac.compare_digest(self.headers.get("X-Frieda-Dienst", ""), konten.dienst_geheimnis()):
                return self._senden(403, fehler_antwort("schreiben.dienst.nur_konnektor", mit_ok=False))
            try:
                return self._senden(200, (self.schreiber or Schreiber(wurzel())).buchung_im_repo(teile[0], teile[2]))
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                sys.stderr.write(f"Fehler buchung 503: {' '.join(str(e).split())[:LOG_LAENGE]}\n")
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
        code, antwort = anwenden(wurzel(), schreibkopie(), a[1], a[2], anfrage)
        print(json.dumps([code, antwort], ensure_ascii=False))
    elif a[:1] == ["normalisieren"] and len(a) == 2:
        # Routendatei einer Reise einmal rund schreiben (Normalform des Schreibwegs), in einer Sitzung im Reisen-Repo
        geaendert = routen_normalisieren(wurzel() / "reisen" / a[1])
        print(f"reisen/{a[1]}/plan/routen.yaml " + ("in Normalform gebracht." if geaendert else "war schon in Normalform."))
    elif a[:1] == ["vorbereiten"]:
        s = Schreiber(wurzel())
        s.vorbereiten()
        print(f"Arbeitskopie {s.arbeit} steht auf {git(s.arbeit, 'rev-parse', '--short', 'HEAD')}.")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
