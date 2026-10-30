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
holt main in den Veröffentlichungsordner (im Hintergrund; hält der Timer gerade die Sperre, holt er es nach).

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
            "plan_aendern": "plan", "merkmal_zusammenfuehren": "ontologie", "arten_uebernehmen": "ontologie", "wunsch_vorschlagen": "wunsch"}   # reise.AKTIONEN
ARTEN_KOPF = ("# Arten und Merkmale dieser Reise (docs/ontologie.md, ADR-0001). {herkunft}\n"
              "# Felder je Art: grundform (aufenthalt | bewegung | folge), name, farbe, summiert, merkmale, lesetext (Gliederung des\n"
              "# Lesetexts: je Rubrik name und hilfe); je Merkmal: name, typ,\n"
              "# werte, veraenderlich, stufe (pflicht | empfohlen | angeboten | aus), auto, hilfe, frage, auch.\n")
GRUNDFORM_WORT = {"aufenthalt": "Aufenthalt", "bewegung": "Bewegung", "folge": "Folge"}


class Ablehnung(Exception):
    """Der Schreibweg lehnt ab; der Text ist für den AI-Client (einfache Worte, nennt den Grund)."""


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
            raise Ablehnung(f"„{feld}“ fehlt.")
        return None
    if not isinstance(v, str):
        raise Ablehnung(f"„{feld}“ muss Text sein.")
    if absaetze:
        v = "\n\n".join(" ".join(a.split()) for a in re.split(r"\n\s*\n", v.replace("\r\n", "\n")) if a.strip())
    else:
        v = " ".join(v.split())
    if len(v) > laenge:
        raise Ablehnung(f"„{feld}“ ist zu lang (höchstens {laenge} Zeichen).")
    return v


def bool_wert(args, feld):
    v = args.get(feld)
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "ja", "wahr", "false", "nein", "falsch"):
        return v.strip().lower() in ("true", "ja", "wahr")
    raise Ablehnung(f"„{feld}“ muss ja oder nein sein.")


def liste_wert(args, feld, laenge=MAX_WERTE):
    v = args.get(feld)
    if v is None or v == "" or v == []:
        return None
    if isinstance(v, str):
        v = [t for t in (x.strip() for x in v.split("|" if "|" in v else ",")) if t]
    if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
        raise Ablehnung(f"„{feld}“ muss eine Liste von Texten sein.")
    v = list(dict.fromkeys(" ".join(x.split()) for x in v))
    if len(v) > laenge:
        raise Ablehnung(f"„{feld}“ hat zu viele Einträge (höchstens {laenge}).")
    return v


# ---------- Arten und Merkmale (plan/arten.yaml) ----------

def arten_text(arten, herkunft):
    """Inhalt von plan/arten.yaml: Kopfkommentar der Software, dann die Arten; Wertelisten ausgeschrieben statt als Anker."""
    import yaml

    class Ohne_Verweise(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True
    return ARTEN_KOPF.format(herkunft=herkunft) + yaml.dump({"arten": arten}, Dumper=Ohne_Verweise, allow_unicode=True,
                                                             sort_keys=False, width=120)


def arten_laden(reise_dir):
    import yaml
    p = Path(reise_dir) / "plan" / "arten.yaml"
    if not p.exists():
        return {}
    try:
        roh = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise Ablehnung(f"plan/arten.yaml ist kein gültiges YAML ({e}); das muss jemand in einer Sitzung richten.")
    arten = roh.get("arten") if isinstance(roh, dict) else None
    return arten if isinstance(arten, dict) else {}


def arten_speichern(reise_dir, arten, wer):
    p = Path(reise_dir) / "plan" / "arten.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    herkunft = (f"Gepflegt im Gespräch über den Konnektor (zuletzt {datetime.date.today().isoformat()}, {wer['name']}); "
                "der Verlauf steht in der Geschichte des Repos.")
    p.write_text(arten_text(arten, herkunft), encoding="utf-8")


def lesetext_gliederung(roh):
    """Gliederung des Lesetexts einer Art aus der Anfrage (Liste von {rubrik, name, hilfe} oder {schluessel: {name, hilfe}})
    -> {rubrik: {name, hilfe}} in der Reihenfolge, None ohne Angabe, {} zum Entfernen (leere Liste)."""
    from routen import art_schluessel
    if roh is None:
        return None
    if isinstance(roh, dict):
        roh = [{"rubrik": k, **(v if isinstance(v, dict) else {"name": v})} for k, v in roh.items()]
    if not isinstance(roh, list):
        raise Ablehnung("„lesetext“ ist eine Liste von Rubriken {rubrik, name, hilfe} in Lesereihenfolge (leer entfernt die Gliederung).")
    aus = {}
    for r in roh:
        if not isinstance(r, dict) or not str(r.get("name") or "").strip():
            raise Ablehnung("Jede Rubrik des Lesetexts braucht einen Namen (das Stichwort vor dem Absatz, z. B. Charakter).")
        name = str(r["name"]).strip()[:60]
        key = art_schluessel(r.get("rubrik") or name)
        if not key or not SCHLUESSEL_MUSTER.match(key) or key in aus:
            raise Ablehnung(f"Rubrik „{name}“: Schlüssel „{key}“ taugt nicht oder kommt doppelt vor.")
        if any(x["name"].casefold() == name.casefold() for x in aus.values()):
            raise Ablehnung(f"Rubrik „{name}“ kommt doppelt vor.")
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
            raise Ablehnung("„bezeichnung“ fehlt (die Art braucht einen Namen, z. B. Refugi).")
        key = art_schluessel(name)
    key = key.lower()
    if not re.fullmatch(ART_MUSTER, key) or key in (UNTERWEGS, ALLGEMEIN):
        raise Ablehnung(f"„{key}“ taugt nicht als Schlüssel einer Art (Kleinbuchstaben, Ziffern, Unterstrich; nicht "
                        f"{UNTERWEGS} oder {ALLGEMEIN}).")
    grundform = text_wert(args, "grundform", laenge=20)
    if grundform is not None and grundform.lower() not in GRUNDFORMEN:
        raise Ablehnung(f"„grundform“ muss eine von {', '.join(GRUNDFORMEN)} sein.")
    farbe = text_wert(args, "farbe", laenge=20)
    if farbe is not None and farbe.lower() not in FARBEN:
        raise Ablehnung(f"„farbe“ muss eine von {', '.join(FARBEN)} sein.")
    beschreibung = text_wert(args, "beschreibung")
    summiert = bool_wert(args, "summiert")
    buchbar = bool_wert(args, "buchbar")
    symbol = text_wert(args, "symbol", laenge=20)
    if symbol is not None and symbol.lower() not in SYMBOLE_ARTEN:
        raise Ablehnung(f"„symbol“ muss eines der Seite sein: {', '.join(SYMBOLE_ARTEN)}.")
    lesetext = lesetext_gliederung(args.get("lesetext"))
    grund = text_wert(args, "grund")
    neu = key not in arten
    if neu:
        if name is None:
            raise Ablehnung("„bezeichnung“ fehlt (die Art braucht einen Namen, z. B. Refugi).")
        if grundform is None:
            raise Ablehnung(f"„grundform“ fehlt: {', '.join(GRUNDFORMEN)} (docs/ontologie.md). Übernachten ist Aufenthalt, "
                            "Wandern oder Bahnfahren Bewegung, ein Reiseteil aus mehreren Tagen Folge.")
        grundform = grundform.lower()
        a = {"grundform": grundform, "name": name}
        if grundform == "aufenthalt":
            belegt = [x.get("farbe") for x in arten.values() if x.get("grundform") == "aufenthalt"]
            a["farbe"] = (farbe or next((f for f in FARBEN if f not in belegt), FARBEN[len(belegt) % len(FARBEN)])).lower()
        elif farbe:
            a["farbe"] = farbe.lower()
        if summiert and grundform != "bewegung":
            raise Ablehnung("„summiert“ gibt es nur bei Bewegung (aus eigener Kraft: Gehzeit, Länge, Höhenmeter werden summiert).")
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
            namen = {"gehzeit": "Gehzeit", "laenge": "Länge", "hoehenmeter": "Höhenmeter", "tage": "Tage",
                     "unterkuenfte": "Unterkünfte", "anschluss": "Anschluss"}
            a["merkmale"] = {m: {"name": namen.get(m, m.capitalize()), "auto": m} for m in auto}
        arten[key] = a
        titel = f"Art „{name}“ ({key}) angelegt"
        text = (f"Art „{name}“ angelegt: Schlüssel {key}, Grundform {GRUNDFORM_WORT[grundform]}"
                + (f", Farbe {a['farbe']}" if a.get("farbe") else "") + (", summiert" if a.get("summiert") else "") + "."
                + (f" Berechnete Merkmale dazu: {', '.join(auto)}." if auto else "")
                + " Merkmale legst du mit merkmal_definieren an (im Gespräch: Was muss zu jeder Sache dieser Art bekannt sein?).")
    else:
        a = arten[key]
        if grundform is not None and grundform.lower() != a.get("grundform"):
            raise Ablehnung(f"Die Grundform von „{a.get('name', key)}“ lässt sich nicht ändern ({a.get('grundform')}); dafür "
                            "eine neue Art anlegen.")
        if summiert and a.get("grundform") != "bewegung":
            raise Ablehnung("„summiert“ gibt es nur bei Bewegung.")
        geaendert = []
        if name is not None and name != a.get("name"):
            geaendert.append(f"Name „{a.get('name')}“ → „{name}“")
            a["name"] = name
        if farbe is not None and farbe.lower() != a.get("farbe"):
            geaendert.append(f"Farbe {farbe.lower()}")
            a["farbe"] = farbe.lower()
        if beschreibung is not None and beschreibung != a.get("beschreibung"):
            geaendert.append("Beschreibung")
            a["beschreibung"] = beschreibung
        if summiert is not None and bool(a.get("summiert")) != summiert:
            geaendert.append("summiert" if summiert else "nicht mehr summiert")
            if summiert:
                a["summiert"] = True
            else:
                a.pop("summiert", None)
        if symbol is not None and symbol.lower() != a.get("symbol"):
            geaendert.append(f"Symbol {symbol.lower()}")
            a["symbol"] = symbol.lower()
        if buchbar is not None and bool(a.get("buchbar", a.get("grundform") == "aufenthalt")) != buchbar:
            geaendert.append("buchbar (hat einen Buchungsstand)" if buchbar else "nicht buchbar")
            a["buchbar"] = buchbar
        if lesetext is not None and lesetext != a.get("lesetext"):
            geaendert.append("Gliederung des Lesetexts: " + ", ".join(r["name"] for r in lesetext.values()))
            a["lesetext"] = lesetext
        if not geaendert:
            raise Ablehnung(f"Die Art „{a.get('name', key)}“ ({key}) gibt es schon, und nichts daran soll sich ändern. Merkmale "
                            "ändert merkmal_definieren.")
        arten[key] = {k: a[k] for k in ("grundform", "name", "farbe", "symbol", "buchbar", "summiert", "beschreibung", "merkmale",
                                        "lesetext") if k in a}
        titel = f"Art „{a['name']}“ ({key}) geändert"
        text = f"Art „{a['name']}“ ({key}) geändert: " + ", ".join(geaendert) + "."
    arten_speichern(reise_dir, arten, wer)
    return titel, text + (f" Grund: {grund}." if grund else "")


# ---------- Kategorien der Kartenpunkte (plan/kategorien.yaml) ----------

KATEGORIEN_KOPF = ("# Kategorien der Kartenpunkte dieser Reise (docs/ontologie.md „Kartenpunkte“, ADR-0001). {herkunft}\n"
                   "# Felder je Kategorie: gruppe (punkt = Etappen-Karte, wissen = Karte im Wissensabschnitt), name, einzahl, farbe\n"
                   "# (blau | braun | lila | gruen | tuerkis | oliv | grau | rosa | schiefer | kontrast | #rrggbb), symbol,\n"
                   "# nummeriert (Punkt zeigt seine Nummer statt eines Symbols), arten (Zusatz je art eines Punkts: name, symbol,\n"
                   "# hinweis, umriss).\n")


def kategorien_laden(reise_dir):
    import yaml
    p = Path(reise_dir) / "plan" / "kategorien.yaml"
    if not p.exists():
        return {}
    try:
        roh = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise Ablehnung(f"plan/kategorien.yaml ist kein gültiges YAML ({e}); das muss jemand in einer Sitzung richten.")
    k = roh.get("kategorien") if isinstance(roh, dict) else None
    return k if isinstance(k, dict) else {}


def kategorien_speichern(reise_dir, kategorien, wer):
    import yaml

    class Ohne_Verweise(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True
    p = Path(reise_dir) / "plan" / "kategorien.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    herkunft = (f"Gepflegt im Gespräch über den Konnektor (zuletzt {datetime.date.today().isoformat()}, {wer['name']}); "
                "der Verlauf steht in der Geschichte des Repos.")
    p.write_text(KATEGORIEN_KOPF.format(herkunft=herkunft)
                 + yaml.dump({"kategorien": kategorien}, Dumper=Ohne_Verweise, allow_unicode=True, sort_keys=False, width=120),
                 encoding="utf-8")


def kategorie_definieren(reise_dir, wer, args):
    """Eine Kategorie der Kartenpunkte anlegen oder ändern, auch den Zusatz zu einer art. -> (Titel, Text)."""
    from bauen import KATEGORIE_FARBEN, KATEGORIE_GRUPPEN, KATEGORIE_MUSTER, SYMBOLE
    kategorien = kategorien_laden(reise_dir)
    name = text_wert(args, "bezeichnung", laenge=80)
    key = text_wert(args, "kategorie", pflicht=True, laenge=40).lower()
    if not re.fullmatch(KATEGORIE_MUSTER, key):
        raise Ablehnung(f"„{key}“ taugt nicht als Schlüssel einer Kategorie (Kleinbuchstaben, Ziffern, Unterstrich).")
    gruppe = text_wert(args, "gruppe", laenge=20)
    if gruppe is not None and gruppe.lower() not in KATEGORIE_GRUPPEN:
        raise Ablehnung(f"„gruppe“ muss eine von {', '.join(KATEGORIE_GRUPPEN)} sein.")
    farbe = text_wert(args, "farbe", laenge=20)
    if farbe is not None and farbe.lower() not in KATEGORIE_FARBEN and not re.fullmatch(r"#[0-9a-fA-F]{6}", farbe):
        raise Ablehnung(f"„farbe“ muss eine von {', '.join(KATEGORIE_FARBEN)} oder #rrggbb sein.")
    symbol = text_wert(args, "symbol", laenge=20)
    if symbol is not None and symbol not in SYMBOLE:
        raise Ablehnung(f"„symbol“ muss eines von {', '.join(SYMBOLE)} sein.")
    einzahl = text_wert(args, "einzahl", laenge=80)
    nummeriert = bool_wert(args, "nummeriert")
    art = text_wert(args, "art", laenge=40)
    art_name, art_symbol = text_wert(args, "art_bezeichnung", laenge=80), text_wert(args, "art_symbol", laenge=20)
    art_hinweis, art_umriss = text_wert(args, "art_hinweis"), bool_wert(args, "art_umriss")
    if art_symbol is not None and art_symbol not in SYMBOLE:
        raise Ablehnung(f"„art_symbol“ muss eines von {', '.join(SYMBOLE)} sein.")
    if art is None and any(x is not None for x in (art_name, art_symbol, art_hinweis, art_umriss)):
        raise Ablehnung("Für Angaben zu einer art (art_bezeichnung, art_symbol, art_hinweis, art_umriss) fehlt „art“ (das art-Wort der Punkte).")
    grund = text_wert(args, "grund")
    geaendert = []
    if key not in kategorien:
        if name is None or gruppe is None or farbe is None:
            raise Ablehnung("Eine neue Kategorie braucht „bezeichnung“ (Name in der Legende), „gruppe“ (punkt = Etappen-Karte, "
                            "wissen = Karte im Wissensabschnitt) und „farbe“.")
        k = {"gruppe": gruppe.lower(), "name": name}
        titel, kopf = f"Kategorie „{name}“ ({key}) angelegt", f"Kategorie „{name}“ angelegt: Schlüssel {key}, Gruppe {k['gruppe']}, Farbe {farbe}"
        neu = True
    else:
        k = kategorien[key]
        neu = False
        if gruppe is not None and gruppe.lower() != k.get("gruppe"):
            raise Ablehnung(f"Die Gruppe von „{k.get('name', key)}“ lässt sich nicht ändern ({k.get('gruppe')}); dafür eine neue Kategorie anlegen.")
        if name is not None and name != k.get("name"):
            geaendert.append(f"Name „{k.get('name')}“ → „{name}“")
            k["name"] = name
    for feld, wert in (("einzahl", einzahl), ("farbe", farbe), ("symbol", symbol)):
        if wert is not None and wert != k.get(feld):
            k[feld] = wert
            geaendert.append(f"{feld} {wert}")
    if nummeriert is not None and bool(k.get("nummeriert")) != nummeriert:
        k["nummeriert"] = nummeriert or None
        if not nummeriert:
            k.pop("nummeriert", None)
        geaendert.append("nummeriert" if nummeriert else "nicht mehr nummeriert")
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
            geaendert.append(f"art {art}: " + ("Umriss" if art_umriss else "ohne Umriss"))
        arten[art] = a
    if neu:
        k["farbe"] = farbe
        kategorien[key] = {f: k[f] for f in ("gruppe", "name", "einzahl", "farbe", "symbol", "nummeriert", "arten") if k.get(f)}
        text = kopf + (f" (außerdem: {', '.join(geaendert)})" if geaendert else "") + "."
    else:
        if not geaendert:
            raise Ablehnung(f"Die Kategorie „{k.get('name', key)}“ ({key}) gibt es schon, und nichts daran soll sich ändern.")
        kategorien[key] = {f: k[f] for f in ("gruppe", "name", "einzahl", "farbe", "symbol", "nummeriert", "arten") if k.get(f)}
        titel = f"Kategorie „{k['name']}“ ({key}) geändert"
        text = f"Kategorie „{k['name']}“ ({key}) geändert: " + ", ".join(geaendert) + "."
    kategorien_speichern(reise_dir, kategorien, wer)
    return titel, text + (f" Grund: {grund}." if grund else "")


def rolle_pruefen(merkmale, key, rolle, typ):
    """Die Rolle kosten braucht den Typ geld und gilt je Art nur einmal."""
    if rolle == "kosten" and typ != "geld":
        raise Ablehnung("Die Rolle kosten braucht den Typ geld (ein Betrag mit Währung).")
    andere = next((k for k, d in merkmale.items() if k != key and isinstance(d, dict) and d.get("rolle") == rolle), None)
    if andere:
        raise Ablehnung(f"Die Rolle {rolle} hat an dieser Art schon das Merkmal „{merkmale[andere].get('name', andere)}“ ({andere}); "
                        "erst dort die Rolle nehmen (rolle: keine).")


def merkmal_definieren(reise_dir, wer, args):
    """Ein Merkmal einer Art anlegen oder ändern (umbenennen, Stufe, abschalten mit Stufe aus). -> (Titel, Text)."""
    from routen import ROLLEN, STUFEN, TYPEN, art_schluessel, stufe_schluessel, stufe_wort
    arten = arten_laden(reise_dir)
    art = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
    if art not in arten:
        raise Ablehnung(f"Die Art „{art}“ gibt es bei dieser Reise nicht" + (f" (vorhanden: {', '.join(arten)})" if arten else "")
                        + ". Erst mit art_definieren anlegen.")
    a = arten[art]
    merkmale = a.get("merkmale") if isinstance(a.get("merkmale"), dict) else {}
    name = text_wert(args, "bezeichnung", laenge=80)
    key = text_wert(args, "merkmal", laenge=40)
    if key is None:
        if name is None:
            raise Ablehnung("„bezeichnung“ fehlt (das Merkmal braucht einen Namen, z. B. Stornierung).")
        key = art_schluessel(name)
    key = key.lower()
    if not SCHLUESSEL_MUSTER.match(key):
        raise Ablehnung(f"„{key}“ taugt nicht als Schlüssel eines Merkmals (Kleinbuchstaben, Ziffern, Unterstrich).")
    typ = text_wert(args, "typ", laenge=20)
    if typ is not None and typ.lower() not in TYPEN:
        raise Ablehnung(f"„typ“ muss einer von {', '.join(sorted(TYPEN))} sein.")
    stufe = text_wert(args, "stufe", laenge=20)
    if stufe is not None:   # Schlüssel oder Wort für Menschen (nötig, gut zu wissen, zusätzlich); gespeichert wird der Schlüssel
        stufe = stufe_schluessel(stufe)
        if stufe is None:
            raise Ablehnung(f"„stufe“ muss eine von {', '.join(STUFEN)} sein: pflicht = nötig (ohne Wert eine Lücke), "
                            "empfohlen = gut zu wissen (Vorgabe; ohne Wert keine Mahnung), angeboten = zusätzlich (nur mit Wert "
                            "sichtbar), aus gilt für diese Reise nicht.")
    werte = liste_wert(args, "werte")
    veraenderlich = bool_wert(args, "veraenderlich")
    einheit, hilfe, frage, grund = (text_wert(args, f) for f in ("einheit", "hilfe", "frage", "grund"))
    rolle = text_wert(args, "rolle", laenge=20)
    if rolle is not None and rolle not in ("", "keine", *ROLLEN):
        raise Ablehnung(f"„rolle“ muss eine von {', '.join(ROLLEN)} sein (kosten: der Preis des Dings, den die Seite über die Reise "
                        "summiert) oder keine.")
    rolle = None if rolle is None else (rolle if rolle in ROLLEN else "")
    auch = liste_wert(args, "auch")
    if auch is not None:
        auch = [art_schluessel(x) for x in auch]
        if any(not SCHLUESSEL_MUSTER.match(x) or x == key for x in auch):
            raise Ablehnung("„auch“: andere Namen desselben Merkmals als Schlüssel (Kleinbuchstaben), nicht der eigene.")
    for k, d in merkmale.items():
        if k != key and isinstance(d, dict) and key in (d.get("auch") or []):
            raise Ablehnung(f"„{key}“ ist bei {a.get('name', art)} schon ein anderer Name für das Merkmal „{d.get('name', k)}“ ({k}). "
                            "Das vorhandene Merkmal ändern statt ein zweites anlegen.")
    neu = key not in merkmale
    if neu:
        if name is None:
            raise Ablehnung("„bezeichnung“ fehlt (das Merkmal braucht einen Namen, z. B. Stornierung).")
        typ = (typ or "text").lower()
        if typ == "auswahl" and not werte:
            raise Ablehnung("Ein Merkmal vom Typ auswahl braucht „werte“ (die möglichen Antworten, z. B. inklusive | gegen Aufpreis | keins | unklar).")
        if werte and typ != "auswahl":
            raise Ablehnung("„werte“ gibt es nur beim Typ auswahl.")
        d = {"name": name, "typ": typ}
        if werte:
            d["werte"] = werte
        if veraenderlich:
            d["veraenderlich"] = True
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
        titel = f"Merkmal „{name}“ ({key}) an {a.get('name', art)} angelegt"
        text = (f"Merkmal „{name}“ ({key}) an der Art {a.get('name', art)} angelegt: Typ {typ}"
                + (f" ({' | '.join(werte)})" if werte else "") + (", veränderlich (braucht Prüfdatum)" if veraenderlich else "")
                + f", Stufe {stufe_wort(stufe or 'empfohlen')}.")
    else:
        d = merkmale[key]
        if d.get("auto") and any(x is not None for x in (typ, werte, veraenderlich, einheit, rolle)):
            raise Ablehnung(f"„{d.get('name', key)}“ wird aus dem Plan berechnet; daran lassen sich nur Name, Stufe, Hilfe und "
                            "weitere Namen ändern.")
        geaendert = []
        if rolle is not None and rolle != (d.get("rolle") or ""):
            if rolle:
                rolle_pruefen(merkmale, key, rolle, (typ or d.get("typ", "text")).lower())
                d["rolle"] = rolle
                geaendert.append(f"Rolle {rolle}")
            else:
                d.pop("rolle", None)
                geaendert.append("keine Rolle mehr")
        if typ is not None and typ.lower() != d.get("typ", "text"):
            if typ.lower() == "auswahl" and not (werte or d.get("werte")):
                raise Ablehnung("Der Typ auswahl braucht „werte“.")
            geaendert.append(f"Typ {typ.lower()}")
            d["typ"] = typ.lower()
            if typ.lower() != "auswahl":
                d.pop("werte", None)
        if werte is not None:
            if d.get("typ", "text") != "auswahl":
                raise Ablehnung("„werte“ gibt es nur beim Typ auswahl.")
            if werte != d.get("werte"):
                geaendert.append("Werte " + " | ".join(werte))
                d["werte"] = werte
        if name is not None and name != d.get("name"):
            geaendert.append(f"Name „{d.get('name')}“ → „{name}“")
            d["name"] = name
        if veraenderlich is not None and bool(d.get("veraenderlich")) != veraenderlich:
            geaendert.append("veränderlich" if veraenderlich else "nicht mehr veränderlich")
            if veraenderlich:
                d["veraenderlich"] = True
            else:
                d.pop("veraenderlich", None)
        if stufe is not None and stufe != (d.get("stufe") if isinstance(d.get("stufe"), str) else "empfohlen"):
            geaendert.append("abgeschaltet (Stufe aus)" if stufe == "aus" else f"Stufe {stufe_wort(stufe)}")
            if stufe == "empfohlen":
                d.pop("stufe", None)
            else:
                d["stufe"] = stufe
        for f, v in (("einheit", einheit), ("hilfe", hilfe), ("frage", frage)):
            if v is not None and v != d.get(f):
                geaendert.append(f.capitalize())
                d[f] = v
        if auch is not None and auch != d.get("auch"):
            geaendert.append("andere Namen " + ", ".join(auch))
            d["auch"] = auch
        if not geaendert:
            raise Ablehnung(f"Das Merkmal „{d.get('name', key)}“ ({key}) gibt es an {a.get('name', art)} schon, und nichts daran soll "
                            "sich ändern.")
        merkmale[key] = {k: d[k] for k in ("name", "typ", "werte", "auto", "veraenderlich", "einheit", "stufe", "rolle", "hilfe", "frage",
                                           "auch") if k in d}
        titel = f"Merkmal „{d['name']}“ ({key}) an {a.get('name', art)} geändert"
        text = f"Merkmal „{d['name']}“ ({key}) an der Art {a.get('name', art)} geändert: " + ", ".join(geaendert) + "."
    a["merkmale"] = merkmale
    arten_speichern(reise_dir, arten, wer)
    return titel, text + (f" Grund: {grund}." if grund else "")


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


def routen_laden(reise_dir):
    p = Path(reise_dir) / "plan" / "routen.yaml"
    if not p.exists():
        raise Ablehnung("Diese Reise hat noch keinen Plan (plan/routen.yaml).")
    try:
        return yaml_rund().load(p.read_text(encoding="utf-8"))
    except Exception as e:   # ruamel wirft verschiedene Fehlerklassen
        raise Ablehnung(f"plan/routen.yaml lässt sich nicht lesen ({type(e).__name__}); das muss jemand in einer Sitzung richten.")


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
            raise Ablehnung(f"Die Unterkunft {ziel} gibt es nicht.")
        return k, f"{ziel} {k.get('name', '')}".strip()
    if ziel.startswith("A-"):
        k = (roh.get("aufenthalte") or {}).get(ziel)
        if k is None:
            raise Ablehnung(f"Den Aufenthalt {ziel} gibt es nicht.")
        return k, f"{ziel} {k.get('name', '')}".strip()
    if ziel.startswith("E-"):
        k = (roh.get("strecken") or {}).get(ziel)
        if k is None:
            raise Ablehnung(f"Die Strecke {ziel} gibt es nicht.")
        return k, f"{ziel} {k.get('titel', '')}".strip()
    vid = ziel.split(".")[0]
    w = (roh.get("wahlstellen") or {}).get(vid)
    for o in (w or {}).get("optionen") or []:
        if isinstance(o, dict) and o.get("id") == ziel:
            return o, f"{ziel} {o.get('titel', '')}".strip()
    raise Ablehnung(f"Die Option {ziel} gibt es nicht.")


def datum(text, feld, k):
    """ISO-Text -> datetime.date oder Ablehnung."""
    try:
        return datetime.date.fromisoformat(str(text).strip())
    except (ValueError, TypeError):
        raise Ablehnung(f"{k}: „{feld}“ als Datum JJJJ-MM-TT angeben.")


def wert_eintraege(args, k, definition, heute):
    """Die neuen Werte aus der Anfrage prüfen -> Liste von Einträgen {wert, quelle, geprueft?, notiz?, gilt?} (Daten als date).
    Herkunftspflicht: jeder Wert braucht quelle; ein veränderliches Merkmal auch geprueft (nicht in der Zukunft)."""
    roh = args.get("werte")
    if roh in (None, "", []):
        roh = [{f: args.get(f) for f in ("wert", "quelle", "geprueft", "notiz", "gilt")}]
    if not isinstance(roh, list) or not all(isinstance(x, dict) for x in roh):
        raise Ablehnung("„werte“ muss eine Liste von Einträgen {wert, quelle, geprueft, gilt, notiz} sein.")
    aus = []
    for x in roh:
        x = {**{f: args.get(f) for f in ("quelle", "geprueft", "notiz") if args.get(f) not in (None, "")}, **x}
        wert = x.get("wert")
        if isinstance(wert, bool):
            wert = "ja" if wert else "nein"
        if wert is None or str(wert).strip() == "":
            raise Ablehnung(f"{k}: „wert“ fehlt. Fehlt der Wert, nichts eintragen.")
        wert = " ".join(str(wert).split()) if not isinstance(wert, (int, float)) else wert
        if definition.get("typ") == "auswahl" and str(wert) not in [str(v) for v in definition.get("werte") or []]:
            raise Ablehnung(f"{k} = „{wert}“ geht nicht, erlaubt: {', '.join(map(str, definition.get('werte') or []))}.")
        if definition.get("typ") == "zahl":
            try:
                wert = float(str(wert).replace(",", "."))
                wert = int(wert) if wert == int(wert) else wert
            except ValueError:
                raise Ablehnung(f"{k} muss eine Zahl sein.")
        quelle = x.get("quelle")
        if not isinstance(quelle, str) or not quelle.strip():
            raise Ablehnung(f"{k}: „quelle“ fehlt. Jede Angabe nennt ihre Herkunft (Website mit Adresse, Buch mit Seite, Anruf, "
                            "die Person im Gespräch); ohne Herkunft wird nichts eingetragen.")
        e = {"wert": wert, "quelle": " ".join(quelle.split())[:MAX_TEXT]}
        g = x.get("geprueft")
        if g not in (None, ""):
            e["geprueft"] = datum(g, "geprueft", k)
            if e["geprueft"] > heute:
                raise Ablehnung(f"{k}: das Prüfdatum liegt in der Zukunft.")
        elif definition.get("veraenderlich"):
            raise Ablehnung(f"{k} ist veränderlich (Preise, Zeiten, Öffnung): „geprueft“ mit dem Datum des Nachschlagens angeben "
                            f"(heute: {heute.isoformat()}).")
        if x.get("notiz") not in (None, ""):
            e["notiz"] = " ".join(str(x["notiz"]).split())[:MAX_TEXT]
        gilt = x.get("gilt")
        if gilt not in (None, "", []):
            tage = [datum(t, "gilt", k) for t in (gilt if isinstance(gilt, list) else [gilt])]
            e["gilt"] = tage[0] if len(tage) == 1 else tage
        aus.append(e)
    ohne = [e for e in aus if "gilt" not in e]
    if len(ohne) > 1:
        raise Ablehnung(f"{k}: mehrere Werte ohne „gilt“; je Datum angeben, höchstens einer gilt für alle übrigen Tage.")
    tage = [t for e in aus for t in (e["gilt"] if isinstance(e.get("gilt"), list) else [e["gilt"]] if "gilt" in e else [])]
    if len(tage) != len(set(tage)):
        raise Ablehnung(f"{k}: ein Datum steht in zwei Werten.")
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
        t += " (am " + ", ".join(x.strftime("%d.%m.") if hasattr(x, "strftime") else str(x) for x in g) + ")"
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
        raise Ablehnung("„ziel“ muss eine Unterkunft U-…, eine Strecke E-… oder eine Option V-01.a sein.")
    k = (text_wert(args, "merkmal", pflicht=True, laenge=40) or "").lower()
    with tempfile.TemporaryDirectory(prefix="frieda-probe-") as tmp:
        try:
            d = bauen.Bauer(reise_dir, tmp).daten()
        except bauen.BauFehler as e:
            raise Ablehnung("Die Reise lässt sich gerade nicht bauen; erst das richten: " + " ".join(e.meldungen))
    route = d.get("route") or {}
    # Merkmale, die an dieser Stelle gelten (wie der Generator sie zuordnet), und der heutige Wert
    if ziel.startswith("V-"):
        w = next((w for w in route.get("wahlstellen") or [] if any(o["id"] == ziel for o in w["optionen"])), None)
        if w is None:
            raise Ablehnung(f"Die Option {ziel} gibt es nicht.")
        krit = w.get("kriterien") or []
        heutige = next(o for o in w["optionen"] if o["id"] == ziel).get("merkmale") or {}
    elif ziel.startswith(("U-", "A-")):
        u = (route.get("unterkuenfte" if ziel.startswith("U-") else "aufenthalte") or {}).get(ziel)
        if u is None:
            raise Ablehnung(f"{'Die Unterkunft' if ziel.startswith('U-') else 'Den Aufenthalt'} {ziel} gibt es nicht.")
        krit = (route.get("merkmale") or {}).get(u.get("art")) or []
        heutige = u.get("merkmale") or {}
    else:
        st = (route.get("strecken") or {}).get(ziel)
        if st is None:
            raise Ablehnung(f"Die Strecke {ziel} gibt es nicht.")
        if isinstance(st.get("art"), list):
            raise Ablehnung(f"Die Strecke {ziel} hat mehrere Arten ({' + '.join(st['art'])}); Werte stehen an der Option der Wahlstelle "
                            "(wert_eintragen mit V-01.a), nicht an der kombinierten Strecke.")
        krit = (route.get("merkmale") or {}).get(st.get("art_schluessel") or st.get("art")) or []
        heutige = st.get("merkmale") or {}
    definition = next((x for x in krit if x["id"] == k), None) or next((x for x in krit if k in (x.get("auch") or [])), None)
    if definition is None:
        raise Ablehnung(f"Das Merkmal „{k}“ gibt es an {ziel} nicht (bekannt: {', '.join(x['id'] for x in krit) or 'keine'}). "
                        "Ein neues Merkmal legt ein:e Organisator:in mit merkmal_definieren an der Art an.")
    k = definition["id"]
    if definition.get("auto"):
        raise Ablehnung(f"„{definition['name']}“ wird aus dem Plan berechnet und nicht eingetragen.")
    if (definition.get("stufe") if isinstance(definition.get("stufe"), str) else None) == "aus":
        raise Ablehnung(f"„{definition['name']}“ ist bei dieser Reise abgeschaltet (Stufe aus); erst mit merkmal_definieren einschalten.")
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
    neu_text = "; ".join(wert_text(e) for e in neue)
    alt_text = "; ".join(wert_text(e) for e in ersetzt)
    titel = f"{bezeichnung}: {name} {('„' + alt_text + '“ → ') if alt_text else ''}„{neu_text}“"
    text = (f"{name} an {bezeichnung}: {neu_text}" + (f" (vorher: {alt_text})" if alt_text else "")
            + f". Herkunft: {'; '.join(dict.fromkeys(e['quelle'] for e in neue))}"
            + (f", geprüft {', '.join(dict.fromkeys(e['geprueft'].isoformat() for e in neue if 'geprueft' in e))}" if any('geprueft' in e for e in neue) else "")
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
            raise Ablehnung(f"„{feld}“ fehlt.")
        return None
    if isinstance(v, str):
        v = [x.strip() for x in v.split(",") if x.strip()]
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise Ablehnung(f"„{feld}“ muss eine Liste von IDs sein.")
    for x in v:
        if not re.fullmatch(muster, x):
            raise Ablehnung(f"„{feld}“: „{x}“ ist hier keine gültige ID.")
        if menge is not None and x not in (roh.get(menge) or {}):
            raise Ablehnung(f"„{feld}“: {x} gibt es nicht.")
    return v


def merkmale_werte(roh_merkmale, krit, heute, vorgabe=None):
    """Merkmale eines neuen Dings oder einer Option aus der Anfrage -> {schluessel: Eintrag | [Einträge]} (geprüft wie wert_eintragen)."""
    if roh_merkmale in (None, "", {}):
        return {}
    if not isinstance(roh_merkmale, dict):
        raise Ablehnung("„merkmale“ muss ein Objekt {merkmal: {wert, quelle, geprueft, gilt, notiz}} sein.")
    aus = {}
    for k, v in roh_merkmale.items():
        k = str(k).lower()
        d = next((x for x in krit if x["id"] == k), None) or next((x for x in krit if k in (x.get("auch") or [])), None)
        if d is None:
            raise Ablehnung(f"Das Merkmal „{k}“ gibt es an dieser Art nicht (bekannt: {', '.join(x['id'] for x in krit) or 'keine'}). "
                            "Ein neues Merkmal legt ein:e Organisator:in mit merkmal_definieren an.")
        if d.get("auto"):
            raise Ablehnung(f"„{d['name']}“ wird aus dem Plan berechnet und nicht eingetragen.")
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
    with tempfile.TemporaryDirectory(prefix="frieda-probe-") as tmp:
        try:
            return bauen.Bauer(reise_dir, tmp).daten().get("route") or {}
        except bauen.BauFehler as e:
            raise Ablehnung("Die Reise lässt sich gerade nicht bauen; erst das richten: " + " ".join(e.meldungen))


def neue_id(reise_dir, kuerzel):
    import neu
    try:
        return neu.naechste_id(Path(reise_dir), kuerzel)
    except neu.Fehler as e:
        raise Ablehnung(str(e))


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
        raise Ablehnung(f"„{feld}“ muss eine Uhrzeit HH:MM sein (z. B. 09:30).")
    return v


def ding_anlegen(reise_dir, wer, args, heute=None):
    """Eine Unterkunft, Strecke oder einen Ort anlegen (neue ID aus ids.yaml, nie neu vergeben). -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    was = (text_wert(args, "was", pflicht=True, laenge=20) or "").lower()
    if was not in DING_ARTEN:
        raise Ablehnung("„was“ muss unterkunft, aufenthalt (ohne Nacht: Besichtigung, Essen, Besuch), strecke oder ort sein.")
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
            raise Ablehnung(f"„art“ muss eine Aufenthalts-Art dieser Reise sein ({', '.join(k for k, a in arten.items() if a.get('grundform') == 'aufenthalt') or 'keine'}); "
                            "eine neue legt ein:e Organisator:in mit art_definieren an.")
        d["art"] = art    # nur art: (der alte Schlüssel typ wird gelesen, nie mehr geschrieben; docs/ontologie.md)
        if was == "aufenthalt" and (zeit := text_wert(args, "zeit", laenge=80)):
            d["zeit"] = zeit
        if text_wert(args, "buchung", laenge=80):
            raise Ablehnung("Einen Buchungsstand gibt es nur als Buchung (buchung_anlegen: Nummer, Frist, Stornoregel, Herkunft); "
                            "das freie Feld buchung wird seit 29.10.2026 nicht mehr geschrieben.")
        if (link := text_wert(args, "buchungslink", laenge=600)):
            if not link.startswith(("http://", "https://")):
                raise Ablehnung("„buchungslink“ muss mit http:// oder https:// beginnen.")
            d["buchungslink"] = link
        if (frage := text_wert(args, "frage", laenge=10)):
            if not re.fullmatch(r"F-\d+", frage):
                raise Ablehnung("„frage“ muss eine F-… sein.")
            d["frage"] = frage
    else:
        d["titel"] = text_wert(args, "titel", pflicht=True, laenge=200)
        d["von"] = (id_liste(args, "von", r"O-\d+", roh, "orte", pflicht=True) or [None])[0]
        d["nach"] = (id_liste(args, "nach", r"O-\d+", roh, "orte", pflicht=True) or [None])[0]
        art = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
        if art not in arten or arten[art].get("grundform") != "bewegung":
            raise Ablehnung(f"„art“ muss eine Bewegungs-Art dieser Reise sein ({', '.join(k for k, a in arten.items() if a.get('grundform') == 'bewegung') or 'keine'}); "
                            "eine neue legt ein:e Organisator:in mit art_definieren an.")
        d["art"] = art
        for k in ("ab", "an"):   # Zeitpunkte (Issue #135): HH:MM oder JJJJ-MM-TTTHH:MM+HH:MM
            if (z := zeit_wert(args, k)):
                d[k] = z
    if was == "aufenthalt":   # Uhrzeit für den Kalender (#77)
        for feld in ("beginn", "ende"):
            if (u := uhrzeit_wert(args, feld)):
                d[feld] = u
        if d.get("ende") and not d.get("beginn"):
            raise Ablehnung("„ende“ nur zusammen mit „beginn“.")
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
    titel = f"{did} {name} angelegt ({was})"
    text = (f"{was.capitalize()} {did} „{name}“ angelegt" + (f" in {route.get('orte', {}).get(d['ort'], {}).get('name', d['ort'])}" if was in ("unterkunft", "aufenthalt") else "")
            + (f", Art {d['art']}" if d.get("art") else "") + (f", Merkmale: {', '.join(werte)}" if werte else "") + f". Herkunft: {quelle}."
            + (" Als Alternative gehört es noch in eine Wahlstelle (option_anlegen oder wahlstelle_anlegen)." if was == "unterkunft" else "")
            + (" Er gehört noch an einen Tag (tag_aendern mit aufenthalte)." if was == "aufenthalt" else ""))
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
        raise Ablehnung(f"„{feld}“ ist eine Uhrzeit HH:MM (am Tag der Strecke) oder ein Zeitpunkt JJJJ-MM-TTTHH:MM+HH:MM (mit Zeitzone).")
    return v


def ding_aendern(reise_dir, wer, args, heute=None):
    """Felder einer Unterkunft, Strecke oder eines Orts ändern (nicht die Merkmale: wert_eintragen). -> (Titel, Text)."""
    from reise import darf
    from routen import art_schluessel
    ziel = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip()
    was = next((w for w, (k, _) in DING_ARTEN.items() if ziel.startswith(k + "-")), None)
    if was is None or not ID_MUSTER.match(ziel):
        raise Ablehnung("„ziel“ muss eine Unterkunft U-…, ein Aufenthalt A-…, eine Strecke E-… oder ein Ort O-… sein.")
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, ziel) if was != "ort" else ((roh.get("orte") or {}).get(ziel), ziel)
    if knoten is None:
        raise Ablehnung(f"{ziel} gibt es nicht.")
    if was == "ort":
        bezeichnung = f"{ziel} {knoten.get('name', '')}".strip()
    arten = route.get("arten") or {}
    if text_wert(args, "buchung", laenge=80) is not None:
        raise Ablehnung("Einen Buchungsstand gibt es nur als Buchung (buchung_anlegen, buchung_aendern); das freie Feld buchung wird "
                        "seit 29.10.2026 nicht mehr geschrieben.")
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
                raise Ablehnung("Die Art eines Dings ändern dürfen nur Organisator:innen (sie bestimmt, welche Merkmale gelten).")
            v = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
            g = "aufenthalt" if was in ("unterkunft", "aufenthalt") else "bewegung"
            if v not in arten or arten[v].get("grundform") != g:
                raise Ablehnung(f"„art“ muss eine {g.capitalize()}s-Art dieser Reise sein ({', '.join(k for k, a in arten.items() if a.get('grundform') == g) or 'keine'}).")
        elif feld == "buchungslink":
            v = text_wert(args, feld, laenge=600) or ""
            if v and not v.startswith(("http://", "https://")):
                raise Ablehnung("„buchungslink“ muss mit http:// oder https:// beginnen.")
        elif feld == "frage":
            v = text_wert(args, feld, laenge=10) or ""
            if v and not re.fullmatch(r"F-\d+", v):
                raise Ablehnung("„frage“ muss eine F-… sein.")
        elif feld in ("beginn", "ende"):
            v = uhrzeit_wert(args, feld) or ""
        elif feld in ("ab", "an"):
            v = zeit_wert(args, feld)
        elif feld == "ausserhalb":
            v = bool_wert(args, feld)
            if v is False and feld in knoten:
                geaendert.append("ausserhalb entfernt (Ort der Reisegegend)")
                del knoten[feld]
                continue
            if not v or knoten.get(feld):
                continue
            geaendert.append("ausserhalb (Ort der An- und Abreise)")
            knoten[feld] = True
            continue
        else:
            v = text_wert(args, feld, laenge=600 if feld == "quelle" else MAX_TEXT) or ""
        alt = knoten.get(feld) if feld != "art" else (knoten.get("art") or art_schluessel(knoten.get("typ")))
        if v == "" and feld in ("hinweis", "buchungslink", "frage", "zeit", "beginn", "ende", "ab", "an"):
            if feld in knoten:
                geaendert.append(f"{feld} entfernt (war „{alt}“)")
                del knoten[feld]
            continue
        if str(alt) == str(v):
            continue
        geaendert.append(f"{feld} „{alt}“ → „{v}“" if alt is not None else f"{feld} „{v}“")
        knoten[feld] = skalar(feld, v)
        if feld == "art" and "typ" in knoten:   # Brücke typ: entfällt, sobald art: steht
            del knoten["typ"]
    if not geaendert:
        raise Ablehnung(f"Nichts zu ändern an {bezeichnung} (änderbar: {', '.join(AENDERBAR[was])}; Merkmale mit wert_eintragen).")
    if knoten.get("ende") and not knoten.get("beginn"):
        raise Ablehnung("„ende“ nur zusammen mit „beginn“.")
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    titel = f"{bezeichnung} geändert: " + "; ".join(g.split(" „")[0] for g in geaendert)
    text = f"{bezeichnung}: " + "; ".join(geaendert) + "." + (f" Grund: {grund}." if grund else "")
    return titel, text


def lage_eintragen(reise_dir, wer, args, heute=None):
    """Lage einer Unterkunft (ADR-0004): Adresse und/oder Koordinaten, je mit Herkunft (quelle) und Prüfdatum. -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    ziel = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip()
    if not re.fullmatch(r"(U|A)-\d+", ziel):
        raise Ablehnung("„ziel“ muss eine Unterkunft U-… oder ein Aufenthalt A-… sein.")
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, ziel)
    if knoten is None:
        raise Ablehnung(f"{ziel} gibt es nicht.")
    quelle = text_wert(args, "quelle", pflicht=True, laenge=600)
    g = datum(args["geprueft"], "geprueft", "Lage") if args.get("geprueft") else heute
    if g > heute:
        raise Ablehnung("„geprueft“ darf nicht in der Zukunft liegen.")
    adresse = text_wert(args, "adresse", laenge=300)
    punkt = None
    if args.get("koordinaten") not in (None, ""):
        try:
            punkt = [round(float(x), 6) for x in re.split(r"[,;\s]+", str(args["koordinaten"]).strip()) if x]
        except ValueError:
            punkt = []
        if len(punkt) != 2 or not (-90 <= punkt[0] <= 90 and -180 <= punkt[1] <= 180):
            raise Ablehnung("„koordinaten“ als „Breite, Länge“ in Grad angeben, z. B. „39.7671, 2.7149“.")
    if not adresse and not punkt:
        raise Ablehnung("Bitte „adresse“ (Straße Nr., PLZ Ort) oder „koordinaten“ (Breite, Länge) angeben.")
    geaendert = []
    for feld, wert in (("adresse", adresse), ("punkt", punkt)):
        if not wert:
            continue
        alt = (knoten.get(feld) or {}).get("wert") if isinstance(knoten.get(feld), dict) else None
        knoten[feld] = fliess_map({"wert": wert, "quelle": quelle, "geprueft": g})
        text = ", ".join(map(str, wert)) if feld == "punkt" else wert
        geaendert.append(f"{'Koordinaten' if feld == 'punkt' else 'Adresse'} „{text}“" + (f" (war „{', '.join(map(str, alt)) if isinstance(alt, list) else alt}“)" if alt else ""))
    routen_speichern(reise_dir, roh)
    grund = text_wert(args, "grund")
    return (f"{bezeichnung}: Lage eingetragen",
            f"{bezeichnung}: " + "; ".join(geaendert) + f". Herkunft: {quelle}, geprüft {g.isoformat()}." + (f" Grund: {grund}." if grund else ""))


def frage_zeile(reise_dir, text, bis=None):
    """Eine Zeile in offene-fragen.md anhängen (Tabelle | ID | Was | Bis | Status |) -> neue F-ID."""
    p = Path(reise_dir) / "offene-fragen.md"
    if not p.exists():
        raise Ablehnung("Diese Reise hat keine Datei offene-fragen.md.")
    zeilen = p.read_text(encoding="utf-8").splitlines()
    letzte = max((i for i, z in enumerate(zeilen) if re.match(r"^\|\s*F-\d+\s*\|", z)), default=None)
    kopf = next((i for i, z in enumerate(zeilen) if re.match(r"^\|\s*ID\s*\|", z, re.I)), None)
    if letzte is None and kopf is None:
        raise Ablehnung("offene-fragen.md hat keine Tabelle mit der Spalte ID; das muss jemand in einer Sitzung richten.")
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
    return f"Frage {fid} angelegt", f"Offene Frage {fid} angelegt: {text}" + (f", bis {bis}" if bis else "") + f" (von {wer['name']})."


def option_bauen(roh, route, vid, o, wer, heute, bereich):
    """Eine Option aus der Anfrage -> CommentedMap (Status vorgeschlagen mit Verlauf). bereich: Art der Dinge der Wahlstelle
    (Schlüssel aus plan/arten.yaml) für die Merkmale. Herkunft (quelle) ist Pflicht (ADR-0001, Frage 5); sie gilt als Vorgabe
    für die Merkmale der Option."""
    if not isinstance(o, dict):
        raise Ablehnung("Jede Option ist ein Objekt mit titel und Inhalt (unterkuenfte, strecken oder folge).")
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
        raise Ablehnung(f"Option „{d['titel']}“: nur eines von unterkuenfte, strecken oder folge.")
    for k, v in (("unterkuenfte", u), ("strecken", st), ("folge", fo)):
        if v:
            d[k] = v
    optionen_ids = {x["id"] for w in route.get("wahlstellen") or [] for x in w["optionen"]}
    for f in ("erfordert", "schliesst_aus"):
        l = id_liste(o, f, r"V-\d+\.[a-z]", roh)
        if l:
            fehlt = [x for x in l if x not in optionen_ids]
            if fehlt:
                raise Ablehnung(f"Option „{d['titel']}“: {f} {', '.join(fehlt)} gibt es nicht.")
            d[f] = l
    if (siehe := text_wert(o, "siehe", laenge=20)):
        if not ID_MUSTER.match(siehe):
            raise Ablehnung("„siehe“ muss eine ID sein (z. B. W-05).")
        d["siehe"] = siehe
    if (a := text_wert(o, "ausloeser")):
        d["ausloeser"] = a
    quelle = text_wert(o, "quelle", laenge=600)
    if not quelle:
        raise Ablehnung(f"Option „{d['titel']}“: quelle fehlt (Herkunft: Website, Buch mit Seite, Anruf oder „Name im Gespräch“). "
                        "Ohne Herkunft wird nichts eingetragen.")
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
        raise Ablehnung(f"Die Wahlstelle {vid} gibt es nicht (varianten zeigt alle); eine neue mit wahlstelle_anlegen.")
    wr = next((x for x in route.get("wahlstellen") or [] if x["id"] == vid), {})
    optionen = w.get("optionen")
    if optionen is None:
        from ruamel.yaml.comments import CommentedSeq
        optionen = CommentedSeq()
        w["optionen"] = optionen
    vergeben = {o.get("id") for o in optionen if isinstance(o, dict)}
    buchstabe = next((c for c in "abcdefghijklmnopqrstuvwxyz" if f"{vid}.{c}" not in vergeben), None)
    if buchstabe is None:
        raise Ablehnung(f"{vid} hat schon 26 Optionen.")
    oid = f"{vid}.{buchstabe}"
    knoten, d, werte = option_bauen(roh, route, vid, args, wer, heute, wr.get("art"))
    knoten["id"] = oid
    knoten.move_to_end("id", last=False)
    optionen.append(knoten)
    routen_speichern(reise_dir, roh)
    titel = f"{oid} „{d['titel']}“ an {vid} vorgeschlagen"
    text = (f"Option {oid} „{d['titel']}“ an der Wahlstelle {vid} {wr.get('titel', '')} angelegt, Status vorgeschlagen"
            + (f", Merkmale: {', '.join(werte)}" if werte else "") + f". Herkunft: {d['quelle']}. "
            "Ob sie gewählt wird, entscheidet ein:e Organisator:in (entscheiden).")
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
        raise Ablehnung("„wann“ einer Wahlstelle ist planung (vor der Abreise entscheiden) oder unterwegs (mit Auslöser).")
    d["wann"] = art
    if bereich is not None:
        bereich = bereich.lower()
        if bereich not in arten:
            raise Ablehnung(f"„art“ muss eine Art dieser Reise sein ({', '.join(arten) or 'keine'}): die Art der Dinge, zwischen "
                            "denen gewählt wird.")
        d["art"] = bereich
    an = id_liste(args, "an", r"(T-\d+|E-\d+[A-Za-z]?|U-\d+|O-\d+|V-\d+|W-\d+(\.[\w-]+)?)", roh)
    if an:
        for x in an:
            menge = {"T": "tage", "E": "strecken", "U": "unterkuenfte", "O": "orte", "V": "wahlstellen"}.get(x[0])
            if menge and x not in (roh.get(menge) or {}):
                raise Ablehnung(f"„an“: {x} gibt es nicht.")
        d["an"] = an
    if (frage := text_wert(args, "frage", laenge=10)):
        if not re.fullmatch(r"F-\d+", frage):
            raise Ablehnung("„frage“ muss eine F-… sein.")
        d["frage"] = frage
    if (t := text_wert(args, "text", laenge=2000)):
        d["text"] = t
    optionen = args.get("optionen")
    if not isinstance(optionen, list) or not optionen:
        raise Ablehnung("„optionen“ fehlt: mindestens eine Option (titel und unterkuenfte, strecken oder folge).")
    if len(optionen) > 26:
        raise Ablehnung("Höchstens 26 Optionen.")
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
    titel = f"Wahlstelle {vid} „{d['titel']}“ angelegt"
    text = (f"Wahlstelle {vid} „{d['titel']}“ ({art}" + (f", {bereich}" if bereich else "") + (f", an {', '.join(an)}" if an else "")
            + f") angelegt mit {', '.join(namen)}, alle vorgeschlagen. Entscheiden können Organisator:innen (entscheiden)."
            + (f" Dazu die offene Frage {frage}." if art == "planung" else ""))
    return titel, text


# ---------- Entscheiden und Plan (plan/routen.yaml, offene-fragen.md) ----------
ENTSCHEIDUNGEN = ("gewaehlt", "verworfen", "ersetzt")
WORT = {"gewaehlt": "gewählt", "verworfen": "verworfen", "ersetzt": "ersetzt"}


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
        raise Ablehnung(f"„status“ muss einer von {', '.join(ENTSCHEIDUNGEN)} sein.")
    if not re.fullmatch(r"V-\d+\.[a-z]", oid):
        raise Ablehnung("„option“ muss eine Option V-01.a sein (varianten zeigt sie).")
    vid = oid.split(".")[0]
    route = route_stand(reise_dir)
    wr = next((w for w in route.get("wahlstellen") or [] if w["id"] == vid), None)
    o = next((x for x in (wr or {}).get("optionen") or [] if x["id"] == oid), None)
    if o is None:
        raise Ablehnung(f"Die Option {oid} gibt es nicht.")
    if o.get("status") == status:
        raise Ablehnung(f"{oid} ist schon {WORT[status]}; daran ändert sich nichts.")
    if status == "ersetzt":
        od = next((x for x in wr["optionen"] if x["id"] == durch), None) if durch else None
        if od is None or durch == oid:
            raise Ablehnung(f"„ersetzt“ braucht ersetzt_durch, eine andere Option derselben Wahlstelle {vid}.")
        if od.get("status") in ("verworfen", "ersetzt"):
            raise Ablehnung(f"{durch} ist selbst {WORT[od['status']]} und kann nichts ersetzen.")
    elif durch:
        raise Ablehnung("ersetzt_durch gibt es nur beim Status ersetzt.")
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
    routen_speichern(reise_dir, roh)
    frage_text = ""
    if wr.get("frage"):
        gewaehlt_danach = status == "gewaehlt" or any(x.get("status") == "gewaehlt" and x["id"] != oid for x in wr["optionen"])
        # Hängen weitere Wahlstellen an derselben Frage und ist dort noch nichts gewählt, bleibt die Frage offen
        noch_offen = [w["id"] for w in route.get("wahlstellen") or [] if w["id"] != vid and w.get("frage") == wr["frage"]
                      and not any(x.get("status") == "gewaehlt" for x in w.get("optionen") or [])]
        if status == "gewaehlt" and noch_offen:
            frage_text = f" Frage {wr['frage']} bleibt offen, weil dort noch {', '.join(noch_offen)} zu entscheiden {'ist' if len(noch_offen) == 1 else 'sind'}."
            # Die KI im AI-Client fragt die Person danach einzeln, je Wahlstelle eine Auswahlfrage (Product Owner 29.10.2026)
            wahl = {w["id"]: w for w in route.get("wahlstellen") or []}
            frage_text += (" Frag die Person jetzt einzeln nach, je Wahlstelle eine eigene Frage mit den Möglichkeiten zur Auswahl "
                           "(mit dem Fragewerkzeug der App, wenn es eins gibt), eine nach der anderen: "
                           + " · ".join(f"{v} {wahl[v].get('titel', '')}: " + ", ".join(
                               f"{x['id']} {x.get('titel', '')}" for x in wahl[v].get("optionen") or []
                               if x.get("status") not in ("verworfen", "ersetzt")) for v in noch_offen) + ".")
        elif status == "gewaehlt":
            ok = frage_status_setzen(reise_dir, wr["frage"], f"geklärt {heute.strftime('%-d.%-m.%Y')}: {wer['name']}, {o['titel']} ({oid})")
            frage_text = f" Frage {wr['frage']} ist damit geklärt." if ok else ""
        elif not gewaehlt_danach:
            ok = frage_status_setzen(reise_dir, wr["frage"], "offen")
            frage_text = f" {vid} ist danach offen, Frage {wr['frage']} wieder offen." if ok else f" {vid} ist danach offen."
    titel = f"{oid} „{o['titel']}“ {WORT[status]}" + (f" (ersetzt durch {durch})" if durch else "")
    text = (f"Entschieden: {oid} „{o['titel']}“ ({vid} {wr.get('titel', '')}) ist {WORT[status]}" + (f", ersetzt durch {durch}" if durch else "")
            + f" ({wer['name']}, {heute.strftime('%-d.%-m.%Y')}, Grund: {grund})." + (f" Bisher gewählt und dadurch ersetzt: {', '.join(ersetzt)}." if ersetzt else "")
            + frage_text)
    return titel, text


def tag_aendern(reise_dir, wer, args, heute=None):
    """Einen Tag des Plans ändern: Titel, Text, Nacht (U-…, V-… oder leer), Strecken (E-…/V-…), Wahlstellen unterwegs (V-…),
    Aufenthalte ohne Nacht (A-…, in der Zeitleiste des Tags).
    Nur Organisator:innen (es ändert den Plan). -> (Titel, Text)."""
    tid = (text_wert(args, "ziel", pflicht=True, laenge=10) or "").strip()
    roh = routen_laden(reise_dir)
    t = (roh.get("tage") or {}).get(tid) if re.fullmatch(r"T-\d+", tid) else None
    if t is None:
        raise Ablehnung(f"Den Tag {tid} gibt es nicht.")
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
            raise Ablehnung("„nacht“ ist eine Unterkunft U-…, eine Wahlstelle V-…, ein Ort O-… oder leer (keine Nacht, letzter Tag).")
        menge = {"U": "unterkuenfte", "V": "wahlstellen", "O": "orte"}.get(n[:1])
        if n and n not in (roh.get(menge) or {}):
            raise Ablehnung(f"„nacht“: {n} gibt es nicht.")
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
                raise Ablehnung(f"„{feld}“: {x} gibt es nicht.")
        if list(t.get(feld) or []) != liste:
            geaendert.append(f"{feld} {list(t.get(feld) or [])} → {liste}")
            if liste:
                t[feld] = fliess_map({feld: liste})[feld]
            else:
                t.pop(feld, None)
    if not geaendert:
        raise Ablehnung(f"Nichts zu ändern an {tid} (titel, text, nacht, strecken, wahl, aufenthalte).")
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    return f"{tid} geändert: " + "; ".join(g.split(" ")[0] for g in geaendert), \
        f"{tid} {t.get('titel', '')}: " + "; ".join(geaendert) + "." + (f" Grund: {grund}." if grund else "")


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
        raise Ablehnung(f"„gruppe“ muss eine von {', '.join(neu.GRUPPEN)} sein.")
    datei = text_wert(args, "datei", laenge=80) or "inhalt/wissen.md"
    if not re.fullmatch(r"inhalt/[a-z0-9_-]+\.md", datei):
        raise Ablehnung("„datei“ muss eine Datei unter inhalt/ sein, z. B. inhalt/wissen.md.")
    abschnitt = text_wert(args, "abschnitt", laenge=120)
    titel = text_wert(args, "titel", laenge=120)
    cfg = json.loads((Path(reise_dir) / "reise.json").read_text(encoding="utf-8"))
    zu = cfg.get("abschnitte") or {}
    absatz = f"{text}\n\n*Herkunft: {quelle}; eingetragen am {heute.strftime('%-d.%-m.%Y')} von {wer['name']} über den Konnektor.*"
    # Vorhandener Abschnitt? (W-ID oder Titel in reise.json)
    treffer = None
    for d_, titel_zu in zu.items():
        for t, (wid, _g) in titel_zu.items():
            if (abschnitt and abschnitt.upper() == wid) or (titel and titel == t and (not abschnitt)):
                treffer = (d_, t, wid)
    if abschnitt and treffer is None:
        raise Ablehnung(f"Den Abschnitt „{abschnitt}“ gibt es nicht (W-ID aus ueberblick oder zeige).")
    if treffer:
        d_, t, wid = treffer
        f = Path(reise_dir) / d_
        zeilen = f.read_text(encoding="utf-8").split("\n")
        start = next((i for i, z in enumerate(zeilen) if re.fullmatch(rf"## {re.escape(t)}\s*", z)), None)
        if start is None:
            raise Ablehnung(f"Die Überschrift „{t}“ steht nicht in {d_}; das muss jemand in einer Sitzung richten.")
        ende = next((i for i in range(start + 1, len(zeilen)) if zeilen[i].startswith("## ")), len(zeilen))
        while ende > start + 1 and not zeilen[ende - 1].strip():
            ende -= 1
        zeilen[ende:ende] = ["", *absatz.split("\n")]
        f.write_text("\n".join(zeilen).rstrip("\n") + "\n", encoding="utf-8")
        return f"{wid} „{t}“ ergänzt", f"Abschnitt {wid} „{t}“ ({d_}) ergänzt. Herkunft: {quelle}."
    if not titel:
        raise Ablehnung("„titel“ (neuer Abschnitt) oder „abschnitt“ (W-ID eines vorhandenen) fehlt.")
    try:
        wid = neu.abschnitt(Path(reise_dir), titel, gruppe, datei, absatz)
    except neu.Fehler as e:
        raise Ablehnung(str(e))
    return f"{wid} „{titel}“ angelegt", f"Neuer Abschnitt {wid} „{titel}“ in {datei} (Gruppe {gruppe}). Herkunft: {quelle}."


def frage_schliessen(reise_dir, wer, args, heute=None):
    """Eine offene Frage als geklärt oder entfallen eintragen (Organisator:innen), mit Ergebnis und Datum. -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    fid = (text_wert(args, "frage", pflicht=True, laenge=10) or "").upper()
    if not re.fullmatch(r"F-\d+", fid):
        raise Ablehnung("„frage“ muss eine F-… sein.")
    ergebnis = text_wert(args, "ergebnis", pflicht=True)
    status = (text_wert(args, "status", laenge=20) or "geklaert").lower()
    if status not in ("geklaert", "entfaellt"):
        raise Ablehnung("„status“ ist geklaert oder entfaellt.")
    wort = "geklärt" if status == "geklaert" else "entfällt"
    if not frage_status_setzen(reise_dir, fid, f"{wort} {heute.strftime('%-d.%-m.%Y')}: {wer['name']}, {ergebnis}"):
        raise Ablehnung(f"Die Frage {fid} gibt es nicht (offene_fragen zeigt alle).")
    return f"{fid} {wort}", f"Frage {fid} ist {wort} ({wer['name']}, {heute.strftime('%-d.%-m.%Y')}): {ergebnis}"


def person_schreiben(reise_dir, wer, args, heute=None):
    """Eine Person in reise.yaml anlegen oder ändern (Name, Rolle, reist, Notiz, von, bis). Niemand wird gestrichen: Wer
    ausscheidet, wird gast und reist nicht mehr (der Verlauf nennt ihn weiter). Höchstens die eigene Rolle vergeben. -> (Titel, Text)."""
    from reise import ROLLEN, darf, rolle_neu
    heute = heute or datetime.date.today()
    schluessel = (text_wert(args, "schluessel", pflicht=True, laenge=40) or "").lower()
    if not PERSON_MUSTER.match(schluessel):
        raise Ablehnung("„schluessel“: klein, Buchstaben und Ziffern, z. B. anna.")
    p = Path(reise_dir) / "reise.yaml"
    if not p.exists():
        raise Ablehnung("Diese Reise hat keine reise.yaml.")
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
            raise Ablehnung(f"„rolle“ muss eine von {', '.join(ROLLEN)} sein.")
        if not darf(wer["rolle"], rolle):
            raise Ablehnung(f"Du kannst höchstens eine Rolle vergeben, die du selbst hast (du: {wer['rolle']}).")
    reist = bool_wert(args, "reist")
    notiz = text_wert(args, "notiz", laenge=300)
    von, bis = (datum(args[f], f, "Person") if args.get(f) not in (None, "") else None for f in ("von", "bis"))
    geaendert = []
    if vorhanden is None:
        if not name:
            raise Ablehnung("„vorname“ fehlt (die Person braucht einen Namen).")
        d = {"name": name, "rolle": rolle or "mitwirkend", "reist": True if reist is None else reist}
        for k, v in (("notiz", notiz), ("von", von), ("bis", bis)):
            if v is not None:
                d[k] = v
        personen[schluessel] = fliess_map(d)
        titel = f"Person {name} ({schluessel}) aufgenommen, Rolle {d['rolle']}"
        text = f"{name} steht jetzt in der Reise ({schluessel}, Rolle {d['rolle']}, reist {'mit' if d['reist'] else 'nicht mit'})."
    else:
        if vorhanden.get("rolle") == "organisator" and rolle not in (None, "organisator") and not darf(wer["rolle"], "organisator"):
            raise Ablehnung("Die Rolle einer Organisator:in ändert nur ein:e Organisator:in.")
        for k, v in (("name", name), ("rolle", rolle), ("reist", reist), ("notiz", notiz), ("von", von), ("bis", bis)):
            if v is None or vorhanden.get(k) == v:
                continue
            geaendert.append(f"{k} „{vorhanden.get(k)}“ → „{v}“" if vorhanden.get(k) is not None else f"{k} „{v}“")
            vorhanden[k] = skalar(k, v) if k != "name" else skalar("titel", v)
        if not geaendert:
            raise Ablehnung(f"Nichts zu ändern an {vorhanden.get('name', schluessel)}.")
        titel = f"Person {vorhanden.get('name', schluessel)} ({schluessel}) geändert"
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
        raise Ablehnung("Diese Reise hat keine reise.yaml.")
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
        raise Ablehnung(f"„status“ muss einer von {', '.join(STATUS)} sein.")
    grund = text_wert(args, "grund", pflicht=True)
    p, roh = reise_yaml_laden(reise_dir)
    st = roh.get("status")
    if not isinstance(st, dict):
        st = CommentedMap()
        roh["status"] = st
    alt = st.get("wert")
    if alt == wert:
        raise Ablehnung(f"Die Reise hat schon den Status {wert}.")
    st["wert"] = wert
    verlauf = st.get("verlauf")
    if verlauf is None:
        verlauf = CommentedSeq()
        st["verlauf"] = verlauf
    verlauf.append(fliess_map({"datum": heute, "wert": wert, "wer": wer["name"], "grund": grund}))
    reise_yaml_speichern(p, roh)
    return f"Status {alt or '–'} → {wert}", f"Die Reise hat jetzt den Status {wert} (vorher {alt or '–'}; {wer['name']}, {heute.strftime('%-d.%-m.%Y')}, Grund: {grund})."


def einstellung_setzen(reise_dir, wer, args, heute=None):
    """Einstellungen der Reise: bausteine (vollständige Liste) und regeln (Name: Wert); nur Organisator:innen. Was gilt, prüft der
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
            raise Ablehnung(f"Unbekannte Bausteine: {', '.join(fremd)} (bekannt: {', '.join(BAUSTEINE)}).")
        liste = [b for b in dict.fromkeys(liste) if b not in KERN]
        if list(roh.get("bausteine") or []) != liste:
            geaendert.append(f"bausteine {list(roh.get('bausteine') or [])} → {liste}")
            roh["bausteine"] = fliess_map({"bausteine": liste})["bausteine"]
    regeln = args.get("regeln")
    if regeln not in (None, {}):
        if not isinstance(regeln, dict):
            raise Ablehnung("„regeln“ muss ein Objekt {regel: wert} sein.")
        r = roh.get("regeln")
        if r is None:
            r = CommentedMap()
            roh["regeln"] = r
        for k, v in regeln.items():
            if k not in VORGABEN:
                raise Ablehnung(f"Unbekannte Regel „{k}“ (bekannt: {', '.join(VORGABEN)}).")
            if isinstance(v, str) and v.strip().lstrip("-").isdigit():
                v = int(v)
            if r.get(k) == v:
                continue
            geaendert.append(f"regeln.{k} „{r.get(k, VORGABEN[k])}“ → „{v}“")
            r[k] = skalar(k, v) if isinstance(v, str) else v
    if not geaendert:
        raise Ablehnung("Nichts zu ändern (bausteine als Liste oder regeln als Objekt angeben).")
    grund = text_wert(args, "grund")
    reise_yaml_speichern(p, roh)
    return "Einstellungen geändert: " + "; ".join(g.split(" ")[0] for g in geaendert), \
        "Einstellungen: " + "; ".join(geaendert) + "." + (f" Grund: {grund}." if grund else "")


def reise_anlegen(reisen_dir, wer, args, heute=None):
    """Neue Reise aus einer geprüften Anfrage der Claude-App (Konnektor reise_anlegen, daten.neue_reise) -> (Titel, Text, Ordner).
    Läuft auf Ebene des Repos, nicht einer Reise."""
    import neu
    import shutil
    auftrag = args.get("auftrag")
    if not isinstance(auftrag, dict) or not isinstance((auftrag.get("daten") or {}).get("neue_reise"), dict):
        raise Ablehnung("Die Anfrage beschreibt keine neue Reise.")
    n = auftrag["daten"]["neue_reise"]
    if not REISE_MUSTER.match(str(n.get("pfad") or "")):
        raise Ablehnung("Der Ordner der Reise ist ungültig.")
    if (Path(reisen_dir) / n["pfad"]).exists():
        raise Ablehnung(f"Den Ordner reisen/{n['pfad']} gibt es schon.")
    try:
        ordner = neu.aus_auftrag(Path(reisen_dir), auftrag, heute=heute)
    except neu.Fehler as e:
        raise Ablehnung(str(e))
    ok, meldungen = neu.pruefen(ordner)
    if not ok:
        shutil.rmtree(ordner, ignore_errors=True)
        raise Ablehnung("Die Reise baut nicht: " + " ".join(meldungen))
    return f"Neue Reise {ordner.name} angelegt", f"Die Reise „{n['titel']}“ ist angelegt (Ordner {ordner.name}, Status Idee).", ordner.name



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
        raise Ablehnung(f"„{feld}“ muss ein Datum JJJJ-MM-TT sein.")


def buchung_fuer(args, roh, route):
    """fuer: eine oder mehrere IDs von Unterkünften, Aufenthalten oder Strecken, die es in der Reise gibt."""
    v = args.get("fuer")
    if isinstance(v, str):
        v = [x.strip() for x in v.split(",") if x.strip()]
    if not v or not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise Ablehnung("„fuer“ fehlt: welche Unterkunft (U-…), welcher Aufenthalt (A-…) oder welche Strecke (E-…) ist gebucht; eine oder mehrere IDs.")
    bekannt = set(roh.get("unterkuenfte") or {}) | set(roh.get("aufenthalte") or {}) | set(roh.get("strecken") or {}) | set(route.get("strecken") or {})
    for x in v:
        if not re.fullmatch(r"(U|A)-\d+|E-\d+[A-Za-z]?", x) or x not in bekannt:
            raise Ablehnung(f"„fuer“: {x} gibt es in dieser Reise nicht (Unterkunft U-…, Aufenthalt A-… oder Strecke E-…).")
    return v


BUCHUNG_TEXTE = {"nummer": 80, "bei": 120, "preis": 120, "bezahlt": 200, "frist_was": 120, "storno": 400, "notiz": MAX_TEXT, "ab_was": 120}
# Felder einer Buchung in Worten für Antwort und Verlauf (Menschen lesen Wörter, keine Schlüssel; Product Owner 29.10.2026)
BUCHUNG_WORTE = {"fuer": "Gehört zu", "status": "Status", "nummer": "Nummer", "bei": "Gebucht bei", "preis": "Preis", "bezahlt": "Bezahlt",
                 "frist": "Frist", "frist_was": "Was bis zur Frist", "storno": "Stornoregel", "storno_bis": "Stornofrist",
                 "gebucht_am": "Gebucht am", "quelle": "Herkunft", "notiz": "Notiz", "ab": "Ab", "ab_was": "Was ab dann geht",
                 "personen": "Reisende", "preise": "Preise je Ding"}


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
        raise Ablehnung("„personen“ ist eine Liste von Namen oder {Name: Angabe} (z. B. {\"Ida\": \"Sitz 12A, 23 kg Gepäck\"}).")
    import bauen, tempfile
    with tempfile.TemporaryDirectory(prefix="frieda-probe-") as ziel:
        bekannt = {p.get("name", "").casefold() for p in (bauen.Bauer(reise_dir, ziel).eck.get("personen") or [])}
    fremd = [k for k in v if str(k).strip().casefold() not in bekannt]
    if fremd:
        raise Ablehnung(f"„personen“: {', '.join(fremd)} steht nicht in der Reise (reise.yaml personen); erst einladen (person_einladen).")
    return {" ".join(str(k).split()): " ".join(str(x or "").split())[:200] for k, x in v.items()}


def buchung_preise(args, fuer):
    """preise einer Buchung: {ID aus fuer: Betrag} -> dict oder None."""
    v = args.get("preise")
    if v is None:
        return None
    if not isinstance(v, dict) or any(not isinstance(x, str) for x in v.values()):
        raise Ablehnung("„preise“ ist {ID: Betrag}, z. B. {\"E-28\": \"120 €\", \"E-29\": \"110 €\"}.")
    fremd = [k for k in v if k not in fuer]
    if fremd:
        raise Ablehnung(f"„preise“: {', '.join(fremd)} gehört nicht zu dieser Buchung (fuer: {', '.join(fuer)}).")
    return {k: " ".join(x.split())[:120] for k, x in v.items() if x.strip()}


def buchung_anlegen(reise_dir, wer, args, heute=None):
    """Eine Buchung anlegen (neue B-ID): zu welchen Dingen, Status, Nummer, Anbieter, Preis, Frist, Stornoregel, Herkunft. -> (Titel, Text)."""
    from routen import BUCHUNG_STATUS
    heute = heute or datetime.date.today()
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    fuer = buchung_fuer(args, roh, route)
    status = (text_wert(args, "status", laenge=20) or "gebucht").lower()
    if status not in BUCHUNG_STATUS:
        raise Ablehnung(f"„status“ muss {', '.join(BUCHUNG_STATUS)} sein.")
    quelle = text_wert(args, "quelle", pflicht=True, laenge=600)
    d = {"fuer": fuer, "status": status}
    for k, laenge in BUCHUNG_TEXTE.items():
        if k == "notiz":
            continue
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
    from ruamel.yaml.comments import CommentedSeq
    verlauf = CommentedSeq()
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": "angelegt", **({"grund": grund} if grund else {})}))
    knoten["verlauf"] = verlauf
    roh.setdefault("buchungen", type(roh)())
    roh["buchungen"][bid] = knoten
    routen_speichern(reise_dir, roh)
    namen = ", ".join(f"{x} {buchung_dingname(roh, route, x)}" for x in fuer)
    titel = f"{bid} Buchung {status}: {namen}"
    text = (f"Buchung {bid} angelegt ({status}) für {namen}" + (f", Nr. {d['nummer']}" if d.get("nummer") else "")
            + (f", bei {d['bei']}" if d.get("bei") else "") + (f", Preis {d['preis']}" if d.get("preis") else "")
            + (f", Frist {d['frist'].strftime('%-d.%-m.%Y')}" + (f" ({d['frist_was']})" if d.get("frist_was") else "") if d.get("frist") else "")
            + (f", Storno: {d['storno']}" if d.get("storno") else "") + (f" (bis {d['storno_bis'].strftime('%-d.%-m.%Y')})" if d.get("storno_bis") else "")
            + (f", Ab {d['ab'].strftime('%-d.%-m.%Y')}" + (f" ({d['ab_was']})" if d.get("ab_was") else "") if d.get("ab") else "")
            + (", Preise: " + ", ".join(f"{k} {v}" for k, v in preise.items()) if preise else "")
            + (", Reisende: " + ", ".join(f"{k}{(' (' + v + ')') if v else ''}" for k, v in pers.items()) if pers else "")
            + f". Herkunft: {quelle}. Den Beleg hängt die Person auf der Seite bei dieser Buchung an oder im Gespräch mit beleg_anlegen; "
            "er bleibt außerhalb des Repos.")
    return titel, text


def buchung_dingname(roh, route, x):
    d = (roh.get("unterkuenfte") or {}).get(x) or (roh.get("aufenthalte") or {}).get(x) or {}
    return d.get("name") or ((route.get("strecken") or {}).get(x) or {}).get("titel") or ((roh.get("strecken") or {}).get(x) or {}).get("titel") or ""


def buchung_aendern(reise_dir, wer, args, heute=None):
    """Felder einer Buchung ändern (Status, Nummer, Frist, Storno …); jede Änderung bekommt einen Verlaufseintrag mit Person,
    Datum und Grund. Leerer Text entfernt ein Feld. -> (Titel, Text)."""
    from routen import BUCHUNG_STATUS
    heute = heute or datetime.date.today()
    bid = (text_wert(args, "ziel", pflicht=True, laenge=10) or "").strip().upper()
    if not re.fullmatch(r"B-\d+", bid):
        raise Ablehnung("„ziel“ muss eine Buchung B-… sein.")
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    knoten = (roh.get("buchungen") or {}).get(bid)
    if knoten is None:
        raise Ablehnung(f"Die Buchung {bid} gibt es nicht.")
    # Mitwirkende ändern nur, was sie selbst eingetragen haben (wer); Organisator:innen alles (Product Owner 29.10.2026, wie bei Belegen)
    if wer["rolle"] != "organisator" and str(knoten.get("wer") or "").strip().casefold() != wer["name"].casefold():
        raise Ablehnung(f"Die Buchung {bid} hat {knoten.get('wer') or 'jemand anderes'} eingetragen; ändern darf sie nur diese Person "
                        "oder eine Organisator:in.")
    grund = text_wert(args, "grund")
    geaendert, kurz = [], []   # ausführlich für die Antwort, kurz für den Verlauf

    def setze(feld, neu, wort=None):
        wort = wort or BUCHUNG_WORTE.get(feld, feld)
        alt = knoten.get(feld)
        alt_t = alt.strftime("%-d.%-m.%Y") if isinstance(alt, datetime.date) else (", ".join(alt) if isinstance(alt, list) else alt)
        neu_t = neu.strftime("%-d.%-m.%Y") if isinstance(neu, datetime.date) else (", ".join(neu) if isinstance(neu, list) else neu)
        if neu in ("", None):
            if feld in knoten:
                geaendert.append(f"{wort or feld} entfernt (war „{alt_t}“)")
                kurz.append(f"{wort or feld} entfernt")
                del knoten[feld]
            return
        if alt_t == neu_t:
            return
        geaendert.append(f"{wort or feld} „{alt_t}“ → „{neu_t}“" if alt is not None else f"{wort or feld} „{neu_t}“")
        kurz.append(wort or feld)
        knoten[feld] = skalar(feld, neu) if isinstance(neu, str) else neu

    if "fuer" in args and args.get("fuer") is not None:
        setze("fuer", buchung_fuer(args, roh, route))
    if (status := text_wert(args, "status", laenge=20)) is not None:
        if status.lower() not in BUCHUNG_STATUS:
            raise Ablehnung(f"„status“ muss {', '.join(BUCHUNG_STATUS)} sein.")
        if status.lower() == "storniert" and knoten.get("status", "gebucht") != "storniert" and not grund:
            raise Ablehnung("Stornieren braucht einen Grund (grund), er steht im Verlauf.")
        setze("status", status.lower(), "Status")
    for k, laenge in BUCHUNG_TEXTE.items():
        if k in args and args.get(k) is not None:
            setze(k, text_wert(args, k, laenge=laenge) or "")
    if "quelle" in args and args.get("quelle") is not None:
        q = text_wert(args, "quelle", laenge=600)
        if not q:
            raise Ablehnung("„quelle“ darf nicht leer sein (Herkunft).")
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
            geaendert.append(f"Reisende {', '.join(f'{k}{(' (' + v + ')') if v else ''}' for k, v in pers.items()) or '–'}")
            kurz.append("Reisende")
            (knoten.__setitem__("personen", block_map(pers)) if pers else knoten.pop("personen", None))
    fuer_jetzt = [knoten["fuer"]] if isinstance(knoten.get("fuer"), str) else list(knoten.get("fuer") or [])
    preise = buchung_preise(args, fuer_jetzt)
    if preise is not None and dict(knoten.get("preise") or {}) != preise:
        geaendert.append("Preise je Ding " + (", ".join(f"{k} {v}" for k, v in preise.items()) or "entfernt"))
        kurz.append("Preise je Ding")
        (knoten.__setitem__("preise", fliess_map(preise)) if preise else knoten.pop("preise", None))
    if not geaendert:
        raise Ablehnung(f"Nichts zu ändern an {bid} (änderbar: fuer, status, {', '.join(BUCHUNG_TEXTE)}, quelle, frist, storno_bis, gebucht_am, ab, personen, preise).")
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
    titel = f"{bid} geändert: " + "; ".join(kurz)
    text = f"Buchung {bid} ({namen}): " + "; ".join(geaendert) + "." + (f" Grund: {grund}." if grund else "")
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
            raise Ablehnung("„nacht“ ist eine Unterkunft U-…, eine Wahlstelle V-… oder ein Ort O-….")
        if n not in (roh.get({"U": "unterkuenfte", "V": "wahlstellen", "O": "orte"}[n[0]]) or {}):
            raise Ablehnung(f"„nacht“: {n} gibt es nicht.")
    for feld, muster, mengen in (("strecken", r"(E-\d+[A-Za-z]?|V-\d+)", {"E": "strecken", "V": "wahlstellen"}),
                                 ("wahl", r"V-\d+", {"V": "wahlstellen"}), ("aufenthalte", r"A-\d+", {"A": "aufenthalte"})):
        liste = id_liste(args, feld, muster, roh)
        for x in liste or []:
            if x not in (roh.get(mengen[x[0]]) or {}) and not (feld == "strecken" and x.startswith("E-")):
                raise Ablehnung(f"„{feld}“: {x} gibt es nicht.")
        if liste:
            d[feld] = liste
    nach, vor = text_wert(args, "nach", laenge=10), text_wert(args, "vor", laenge=10)
    if nach and vor:
        raise Ablehnung("Entweder „nach“ oder „vor“ angeben, nicht beides.")
    anker = nach or vor
    liste, i = (None, None)
    if anker:
        if not re.fullmatch(r"T-\d+", anker) or anker not in (roh.get("tage") or {}):
            raise Ablehnung(f"„{'nach' if nach else 'vor'}“: den Tag {anker} gibt es nicht.")
        liste, i = route_liste_finden(roh, anker)
        if liste is None:
            raise Ablehnung(f"{anker} steht nicht in der Route (sondern in einer Option); den neuen Tag dort mit option_aendern (folge) einhängen.")
    tid = neue_id(reise_dir, "T")
    if n:
        d["nacht"] = n
    roh.setdefault("tage", type(roh)())
    roh["tage"][tid] = fliess_map(d)
    if liste is not None:
        liste.insert(i + (1 if nach else 0), tid)
        wo = f"{'nach' if nach else 'vor'} {anker}"
    elif args.get("ohne_route"):
        wo = "noch nicht in der Route (für eine Variante: option_aendern mit folge)"
    else:
        route = roh.get("route")
        if route is None:
            route = CommentedSeq()
            roh["route"] = route
        route.append(tid)
        wo = "am Ende der Route"
    routen_speichern(reise_dir, roh)
    return f"{tid} „{d['titel']}“ angelegt", f"Tag {tid} „{d['titel']}“ angelegt, {wo}. Der Generator prüft, ob der Plan aufgeht (Datum ergibt sich aus der Reihenfolge)."


def termin_setzen(reise_dir, wer, args, heute=None):
    """Feste Termine der Reise (fixpunkte in plan/routen.yaml): anlegen (datum, titel, ort, quelle), ändern (datum + alter Titel,
    neue Felder) oder entfernen (entfernen: true mit grund). Nur Organisator:innen. -> (Titel, Text)."""
    from ruamel.yaml.comments import CommentedSeq
    roh = routen_laden(reise_dir)
    datum_ = datum_wert(args, "datum")
    if not datum_:
        raise Ablehnung("„datum“ fehlt (JJJJ-MM-TT).")
    titel = text_wert(args, "titel", pflicht=True, laenge=200)
    fix = roh.get("fixpunkte")
    if fix is None:
        fix = CommentedSeq()
        roh["fixpunkte"] = fix
    alt = next((f for f in fix if isinstance(f, dict) and f.get("datum") == datum_ and str(f.get("titel")) == titel), None)
    grund = text_wert(args, "grund")
    if bool_wert(args, "entfernen"):
        if alt is None:
            raise Ablehnung(f"Am {datum_.isoformat()} gibt es keinen Termin „{titel}“.")
        if not grund:
            raise Ablehnung("Entfernen braucht einen Grund (steht im Verlauf).")
        fix.remove(alt)
        routen_speichern(reise_dir, roh)
        return f"Termin {datum_.strftime('%-d.%-m.')} „{titel}“ entfernt", f"Fester Termin am {datum_.strftime('%-d.%-m.%Y')} „{titel}“ entfernt. Grund: {grund}."
    ort = text_wert(args, "ort", laenge=10)
    if ort and (not re.fullmatch(r"O-\d+", ort) or ort not in (roh.get("orte") or {})):
        raise Ablehnung(f"„ort“: {ort} gibt es nicht.")
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
            raise Ablehnung("Den Termin gibt es schon, und nichts daran soll sich ändern.")
        routen_speichern(reise_dir, roh)
        return f"Termin {datum_.strftime('%-d.%-m.')} geändert", f"Fester Termin am {datum_.strftime('%-d.%-m.%Y')}: " + "; ".join(geaendert) + "." + (f" Grund: {grund}." if grund else "")
    if not quelle:
        raise Ablehnung("„quelle“ fehlt (Herkunft des Termins: Buchung, Mail, die Person im Gespräch).")
    d = {"datum": datum_}
    if ort:
        d["ort"] = ort
    d["titel"] = titel
    d["quelle"] = quelle
    fix.append(fliess_map(d))
    routen_speichern(reise_dir, roh)
    return f"Termin {datum_.strftime('%-d.%-m.')} „{titel}“", f"Fester Termin am {datum_.strftime('%-d.%-m.%Y')} „{titel}“ angelegt" + (f" in {ort}" if ort else "") + f". Herkunft: {quelle}."


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
        raise Ablehnung(f"Die Wahlstelle {vid} gibt es nicht.")
    arten = route.get("arten") or {}
    geaendert = []
    for feld, laenge in (("titel", 200), ("text", 2000)):
        if args.get(feld) is not None:
            v = text_wert(args, feld, laenge=laenge) or ""
            if feld == "titel" and not v:
                raise Ablehnung("Der Titel darf nicht leer sein.")
            if v != (w.get(feld) or ""):
                geaendert.append(f"{feld} „{w.get(feld) or ''}“ → „{v}“")
                (w.__setitem__(feld, skalar(feld, v)) if v else w.pop(feld, None))
    if args.get("wann") is not None:
        wann = str(args.get("wann") or "").strip().lower()
        if wann not in ("planung", "unterwegs"):
            raise Ablehnung("„wann“ ist planung oder unterwegs.")
        alt = w.get("wann") or (w.get("art") if w.get("art") in ("planung", "unterwegs") else "planung")
        if wann != alt:
            geaendert.append(f"wann {alt} → {wann}")
            if w.get("art") in ("planung", "unterwegs"):
                del w["art"]
            w["wann"] = wann
    if args.get("art") is not None:
        art = str(args.get("art") or "").strip().lower()
        if art and art not in arten:
            raise Ablehnung(f"„art“ muss eine Art dieser Reise sein ({', '.join(arten) or 'keine'}) oder leer (aus den Optionen).")
        alt = w.get("bereich") or (w.get("art") if w.get("art") not in ("planung", "unterwegs") else None)
        if (art or None) != alt:
            geaendert.append(f"art {alt or '–'} → {art or '– (aus den Optionen)'}")
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
                raise Ablehnung(f"„an“: {x} gibt es nicht.")
        if list(w.get("an") or []) != an:
            geaendert.append(f"an {list(w.get('an') or [])} → {an}")
            (w.__setitem__("an", fliess_map({"an": an})["an"]) if an else w.pop("an", None))
    if args.get("frage") is not None:
        f = str(args.get("frage") or "").strip()
        if f and not re.fullmatch(r"F-\d+", f):
            raise Ablehnung("„frage“ muss eine F-… sein oder leer.")
        if f != (w.get("frage") or ""):
            geaendert.append(f"frage {w.get('frage') or '–'} → {f or '–'}")
            (w.__setitem__("frage", f) if f else w.pop("frage", None))
    stufen = args.get("stufen")
    if stufen not in (None, {}):
        if not isinstance(stufen, dict):
            raise Ablehnung("„stufen“ ist ein Objekt {merkmal: stufe} (nötig, gut zu wissen, zusätzlich, aus).")
        wr = next((x for x in route.get("wahlstellen") or [] if x["id"] == vid), {})
        bekannt = {k["id"] for k in wr.get("kriterien") or []}
        mk = w.get("merkmale")
        if mk is None:
            mk = CommentedMap()
            w["merkmale"] = mk
        for k, st in stufen.items():
            k = str(k).lower()
            if k not in bekannt:
                raise Ablehnung(f"Das Merkmal „{k}“ gibt es an dieser Wahlstelle nicht (bekannt: {', '.join(sorted(bekannt)) or 'keine'}).")
            s = stufe_schluessel(str(st))
            if s is None:
                raise Ablehnung(f"Stufe „{st}“ für {k}: nötig (pflicht), gut zu wissen (empfohlen), zusätzlich (angeboten) oder aus.")
            alt = (mk.get(k) or {}).get("stufe") if isinstance(mk.get(k), dict) else None
            if alt != s:
                geaendert.append(f"Stufe {k}: {alt or 'wie die Art'} → {s}")
                mk[k] = fliess_map({"stufe": s})
    if not geaendert:
        raise Ablehnung(f"Nichts zu ändern an {vid} (titel, text, wann, art, an, frage, stufen).")
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    return f"{vid} geändert: " + "; ".join(g.split(" ")[0] for g in geaendert), f"Wahlstelle {vid} „{w.get('titel', '')}“: " + "; ".join(geaendert) + "." + (f" Grund: {grund}." if grund else "")


def option_aendern(reise_dir, wer, args, heute=None):
    """Felder einer Option ändern: titel, text, plus, minus, erfordert, schliesst_aus, ausloeser, siehe, unterkuenfte, strecken,
    folge, quelle; favorisieren (favorisiert: true mit grund) als Verlaufseintrag (Mitwirkende dürfen; gewählt, verworfen,
    ersetzt nur mit entscheiden). -> (Titel, Text)."""
    from reise import darf
    heute = heute or datetime.date.today()
    oid = (text_wert(args, "ziel", pflicht=True, laenge=12) or "").strip()
    if not re.fullmatch(r"V-\d+\.[a-z]", oid):
        raise Ablehnung("„ziel“ muss eine Option V-01.a sein.")
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, oid)
    if knoten is None:
        raise Ablehnung(f"Die Option {oid} gibt es nicht.")
    vid = oid.split(".")[0]
    geaendert = []
    for feld, laenge in (("titel", 200), ("text", 2000), ("ausloeser", 600), ("quelle", 600)):
        if args.get(feld) is not None:
            v = text_wert(args, feld, laenge=laenge) or ""
            if feld in ("titel", "quelle") and not v:
                raise Ablehnung(f"„{feld}“ darf nicht leer sein.")
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
            raise Ablehnung("„siehe“ muss eine ID sein (z. B. W-05) oder leer.")
        if s != (knoten.get("siehe") or ""):
            geaendert.append(f"siehe {knoten.get('siehe') or '–'} → {s or '–'}")
            (knoten.__setitem__("siehe", s) if s else knoten.pop("siehe", None))
    optionen_ids = {x["id"] for w in route.get("wahlstellen") or [] for x in w["optionen"]}
    for feld in ("erfordert", "schliesst_aus"):
        if args.get(feld) is not None:
            l = id_liste(args, feld, r"V-\d+\.[a-z]", roh) or []
            fehlt = [x for x in l if x not in optionen_ids]
            if fehlt or any(x.startswith(vid + ".") for x in l):
                raise Ablehnung(f"„{feld}“: {', '.join(fehlt) or 'eine Option derselben Wahlstelle'} geht nicht.")
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
            raise Ablehnung("Eine Option hat nur eines von unterkuenfte, strecken oder folge.")
        for f, l in inhalt.items():
            if list(knoten.get(f) or []) != l:
                geaendert.append(f"{f} {list(knoten.get(f) or [])} → {l}")
                (knoten.__setitem__(f, fliess_map({f: l})[f]) if l else knoten.pop(f, None))
    grund = text_wert(args, "grund")
    if bool_wert(args, "favorisiert"):
        if not grund:
            raise Ablehnung("Favorisieren braucht einen Grund (steht im Verlauf).")
        from routen import UNGUELTIG
        o = next((x for w in route.get("wahlstellen") or [] for x in w["optionen"] if x["id"] == oid), {})
        if o.get("status") in UNGUELTIG or o.get("status") == "gewaehlt":
            raise Ablehnung(f"{oid} ist {o.get('status')}; favorisieren geht nur bei vorgeschlagenen Optionen.")
        from ruamel.yaml.comments import CommentedSeq
        verlauf = knoten.get("verlauf")
        if verlauf is None:
            verlauf = CommentedSeq()
            knoten["verlauf"] = verlauf
        verlauf.append(fliess_map({"datum": heute, "status": "favorisiert", "wer": wer["name"], "grund": grund}))
        geaendert.append(f"favorisiert ({wer['name']})")
    if not geaendert:
        raise Ablehnung(f"Nichts zu ändern an {oid} (titel, text, plus, minus, erfordert, schliesst_aus, ausloeser, siehe, unterkuenfte, strecken, folge, quelle, favorisiert).")
    routen_speichern(reise_dir, roh)
    return f"{oid} geändert: " + "; ".join(g.split(" ")[0] for g in geaendert), f"Option {oid} „{knoten.get('titel', '')}“: " + "; ".join(geaendert) + "." + (f" Grund: {grund}." if grund and not bool_wert(args, "favorisiert") else "")


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
        raise Ablehnung("„ziel“ muss ein Abschnitt W-… sein (Unterabschnitte W-05.x gehören zu ihrem Abschnitt).")
    datei, titel = abschnitt_finden(reise_dir, wid)
    if datei is None:
        raise Ablehnung(f"Den Abschnitt {wid} gibt es nicht.")
    f = Path(reise_dir) / datei
    zeilen = f.read_text(encoding="utf-8").split("\n")
    start, ende = abschnitt_grenzen(zeilen, titel)
    if start is None:
        raise Ablehnung(f"Die Überschrift „{titel}“ steht nicht in {datei}; das muss jemand in einer Sitzung richten.")
    text = text_wert(args, "text", laenge=12000, absaetze=True)
    neuer_titel = text_wert(args, "neuer_titel", laenge=120)
    grund = text_wert(args, "grund", pflicht=True)
    geaendert = []
    if text:
        quelle = text_wert(args, "quelle", pflicht=True)
        absatz = f"{text}\n\n*Herkunft: {quelle}; berichtigt am {heute.strftime('%-d.%-m.%Y')} von {wer['name']} über den Konnektor ({grund}).*"
        zeilen[start + 1:ende] = ["", *absatz.split("\n")]
        geaendert.append("Inhalt ersetzt")
    if neuer_titel and neuer_titel != titel:
        if neuer_titel.startswith("#") or "|" in neuer_titel:
            raise Ablehnung("Der neue Titel darf keine Raute und keinen Strich enthalten.")
        zeilen[start] = f"## {neuer_titel}"
        p = Path(reise_dir) / "reise.json"
        cfg = json.loads(p.read_text(encoding="utf-8"))
        zu = cfg["abschnitte"][datei]
        if neuer_titel in zu:
            raise Ablehnung(f"Die Überschrift „{neuer_titel}“ gibt es in {datei} schon.")
        cfg["abschnitte"][datei] = {(neuer_titel if t == titel else t): v for t, v in zu.items()}
        p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        geaendert.append(f"Titel „{titel}“ → „{neuer_titel}“")
    if not geaendert:
        raise Ablehnung("Nichts zu ändern: text (ersetzt den Inhalt, mit quelle) oder neuer_titel angeben.")
    f.write_text("\n".join(zeilen).rstrip("\n") + "\n", encoding="utf-8")
    return f"{wid} geändert: " + "; ".join(geaendert), f"Abschnitt {wid} „{neuer_titel or titel}“ ({datei}): " + "; ".join(geaendert) + f". Grund: {grund}."


def lesetext_schreiben(reise_dir, wer, args, heute=None):
    """Den Lesetext einer Etappe (Abschnitt „Zusammenfassung“ im Etappen-Dossier, Ebene „Der Weg“) schreiben oder ersetzen,
    gegliedert nach den Rubriken der Art (je Absatz „**Rubrik.** …“); Herkunft Pflicht. -> (Titel, Text)."""
    import json
    heute = heute or datetime.date.today()
    eid = (text_wert(args, "ziel", pflicht=True, laenge=12) or "").strip().upper()
    if not re.fullmatch(r"E-\d+[A-Za-z]?", eid):
        raise Ablehnung("„ziel“ muss eine Etappe E-… sein.")
    text = text_wert(args, "text", pflicht=True, laenge=12000, absaetze=True)
    quelle = text_wert(args, "quelle", pflicht=True)
    cfg = json.loads((Path(reise_dir) / "reise.json").read_text(encoding="utf-8"))
    d_rel = cfg.get("etappen_dossier")
    if not d_rel or not (Path(reise_dir) / d_rel).exists():
        raise Ablehnung("Diese Reise hat kein Etappen-Dossier (reise.json etappen_dossier); ein Lesetext gehört zu einer Etappe darin.")
    import bauen
    muster = re.compile(cfg.get("etappen_muster") or bauen.ETAPPEN_MUSTER)
    f = Path(reise_dir) / d_rel
    zeilen = f.read_text(encoding="utf-8").split("\n")
    start = None
    for i, z in enumerate(zeilen):
        m = z.startswith("## ") and muster.match(z[3:].strip())
        if m and "E-" + (m.group(1).zfill(3) if m.group(1)[-1].isalpha() else m.group(1).zfill(2)) == eid:
            start = i
            break
    if start is None:
        raise Ablehnung(f"Die Etappe {eid} steht nicht im Etappen-Dossier ({d_rel}); eine Fahrt ohne Dossier bekommt ihren Text mit ding_aendern (hinweis).")
    ende = next((i for i in range(start + 1, len(zeilen)) if zeilen[i].startswith("## ")), len(zeilen))
    # Rubriken der Art prüfen: jedes fette Stichwort am Absatzanfang muss eine Rubrik sein, wenn die Art eine Gliederung hat
    route = route_stand(reise_dir)
    st = (route.get("strecken") or {}).get(eid) or {}
    rubriken = (((route.get("arten") or {}).get(st.get("art_schluessel"))) or {}).get("lesetext") or []
    if rubriken:
        namen = {r["name"].casefold() for r in rubriken}
        fremd = [w for w in re.findall(r"^\*\*([^*]{1,60})\*\*", text, flags=re.M) if w.strip().rstrip(".:").casefold() not in namen]
        if fremd:
            raise Ablehnung(f"Stichwort „{fremd[0].strip().rstrip('.:')}“ ist keine Rubrik der Art (Gliederung: {', '.join(r['name'] for r in rubriken)}; zeige {eid} nennt die Hilfe je Rubrik).")
    absatz = f"{text}\n\n*Herkunft: {quelle}; geschrieben am {heute.strftime('%-d.%-m.%Y')} von {wer['name']} über den Konnektor.*"
    zs = next((i for i in range(start + 1, ende) if re.fullmatch(r"###\s+Zusammenfassung\s*", zeilen[i])), None)
    if zs is not None:
        ze = next((i for i in range(zs + 1, ende) if zeilen[i].startswith("### ")), ende)
        while ze > zs + 1 and not zeilen[ze - 1].strip():
            ze -= 1
        zeilen[zs + 1:ze] = *absatz.split("\n"),
        was = "ersetzt"
    else:
        # vor dem ersten Unterabschnitt, nach der Einleitung (kursive Zeile) der Etappe
        erster = next((i for i in range(start + 1, ende) if zeilen[i].startswith("### ")), ende)
        zeilen[erster:erster] = ["### Zusammenfassung", *absatz.split("\n"), ""]
        was = "angelegt"
    f.write_text("\n".join(zeilen).rstrip("\n") + "\n", encoding="utf-8")
    return f"{eid}: Lesetext {was}", f"Lesetext der Etappe {eid} {was} (Abschnitt Zusammenfassung in {d_rel}). Herkunft: {quelle}."


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
                raise Ablehnung("Der Titel darf nicht leer sein.")
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
            raise Ablehnung("Diese Reise hat noch keinen Zeitraum; von und bis zusammen angeben (JJJJ-MM-TT).")
        if neu_bis < neu_von:
            raise Ablehnung("„bis“ liegt vor „von“.")
        for k, v in (("von", von), ("bis", bis)):
            if v and v != z.get(k):
                geaendert.append(f"{k} {z.get(k) or '–'} → {v}")
                z[k] = v
    if not geaendert:
        raise Ablehnung("Nichts zu ändern (titel, untertitel, kurz, von, bis).")
    verlauf = roh.get("verlauf")
    if verlauf is None:
        verlauf = CommentedSeq()
        roh["verlauf"] = verlauf
    verlauf.append(fliess_map({"datum": heute, "wer": wer["name"], "was": "; ".join(geaendert), "grund": grund}))
    reise_yaml_speichern(p, roh)
    return "Eckdaten geändert: " + "; ".join(g.split(" ")[0] for g in geaendert), "Eckdaten der Reise: " + "; ".join(geaendert) + f". Grund: {grund}. (Start und Ende des Plans stehen in plan/routen.yaml.)"


PLAN_FARBEN = ("a", "b", "c", "d")


def plan_felder(args, roh, route, d, geaendert=None):
    """Felder eines benannten Plans aus der Anfrage in d (CommentedMap) übernehmen; geaendert sammelt die Änderungen."""
    optionen_ids = {x["id"]: w["id"] for w in route.get("wahlstellen") or [] for x in w["optionen"]}
    for feld, laenge in (("kurz", 40), ("titel", 200), ("text", 2000)):
        if args.get(feld) is not None:
            v = text_wert(args, feld, laenge=laenge) or ""
            if feld != "text" and not v:
                raise Ablehnung(f"„{feld}“ darf nicht leer sein.")
            if v != (d.get(feld) or ""):
                if geaendert is not None:
                    geaendert.append(f"{feld} „{d.get(feld) or ''}“ → „{v}“")
                (d.__setitem__(feld, skalar(feld, v)) if v else d.pop(feld, None))
    if args.get("farbe") is not None:
        farbe = str(args.get("farbe") or "").strip().lower()
        if farbe not in PLAN_FARBEN:
            raise Ablehnung(f"„farbe“ muss eine von {', '.join(PLAN_FARBEN)} sein (Planfarben der Seite).")
        if farbe != d.get("farbe"):
            if geaendert is not None:
                geaendert.append(f"farbe {d.get('farbe') or '–'} → {farbe}")
            d["farbe"] = farbe
    if args.get("auswahl") is not None:
        auswahl = id_liste(args, "auswahl", r"V-\d+\.[a-z]", roh) or []
        fehlt = [x for x in auswahl if x not in optionen_ids]
        if fehlt:
            raise Ablehnung(f"„auswahl“: {', '.join(fehlt)} gibt es nicht.")
        je = {}
        for x in auswahl:
            if optionen_ids[x] in je:
                raise Ablehnung(f"„auswahl“: zwei Optionen für {optionen_ids[x]} ({je[optionen_ids[x]]}, {x}).")
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
        raise Ablehnung("Es gibt schon 26 Pläne.")
    if not args.get("kurz"):
        args = {**args, "kurz": f"Plan {pid[2:]}"}
    if not args.get("titel"):
        raise Ablehnung("„titel“ fehlt.")
    if not args.get("auswahl"):
        raise Ablehnung("„auswahl“ fehlt: je Wahlstelle die Option, die dieser Plan nimmt (V-01.b, …).")
    quelle = text_wert(args, "quelle", pflicht=True)
    d = block_map({"id": pid})
    plan_felder(args, roh, route, d)
    d["quelle"] = skalar("quelle", quelle)
    plaene.append(d)
    routen_speichern(reise_dir, roh)
    return f"Plan {pid} „{d['kurz']}“ angelegt", f"Benannter Plan {pid} „{d['kurz']}: {d['titel']}“ angelegt mit {', '.join(d.get('auswahl') or [])}. Herkunft: {quelle}. Gewählt wird ein Plan über seine Optionen (entscheiden)."


def plan_aendern(reise_dir, wer, args, heute=None):
    """Felder eines benannten Plans ändern (kurz, titel, text, farbe, auswahl, plus, minus), mit grund. Nur Organisator:innen. -> (Titel, Text)."""
    pid = (text_wert(args, "ziel", pflicht=True, laenge=10) or "").strip().upper()
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    d = next((p for p in roh.get("plaene") or [] if isinstance(p, dict) and p.get("id") == pid), None)
    if d is None:
        raise Ablehnung(f"Den Plan {pid} gibt es nicht (varianten zeigt alle).")
    geaendert = []
    plan_felder(args, roh, route, d, geaendert)
    if not geaendert:
        raise Ablehnung(f"Nichts zu ändern an {pid} (kurz, titel, text, farbe, auswahl, plus, minus).")
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    return f"{pid} geändert: " + "; ".join(g.split(" ")[0] for g in geaendert), f"Plan {pid} „{d.get('kurz', '')}“: " + "; ".join(geaendert) + "." + (f" Grund: {grund}." if grund else "")


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
        raise Ablehnung(f"Die Art „{art}“ gibt es nicht ({', '.join(arten) or 'keine'}).")
    mk = arten[art].get("merkmale") if isinstance(arten[art].get("merkmale"), dict) else {}
    if von == nach or von not in mk or nach not in mk:
        raise Ablehnung(f"„von“ und „nach“ müssen zwei verschiedene Merkmale der Art {art} sein ({', '.join(mk) or 'keine'}).")
    if mk[von].get("auto") or mk[nach].get("auto"):
        raise Ablehnung("Berechnete Merkmale lassen sich nicht zusammenführen.")
    if mk[von].get("typ", "text") != mk[nach].get("typ", "text"):
        raise Ablehnung(f"Die Typen passen nicht zusammen ({mk[von].get('typ', 'text')} und {mk[nach].get('typ', 'text')}); erst mit merkmal_definieren angleichen.")
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
    return f"{art}: {von} → {nach} zusammengeführt", (f"Merkmal {von} der Art {art} ist in {nach} aufgegangen: {len(umgehaengt)} Wert(e) umgehängt"
            + (f", bei {', '.join(behalten)} blieb der Wert von {nach} (der andere steht in der Notiz)" if behalten else "")
            + f"; „{von}“ ist jetzt ein weiterer Name von {nach}. Grund: {grund}.")


def art_schluessel_von(knoten):
    from routen import art_schluessel
    return art_schluessel(knoten.get("typ")) if knoten.get("typ") else None


def arten_uebernehmen(reise_dir, wer, args, heute=None):
    """Arten (mit Merkmalen und Gliederung) einer anderen Reise derselben Person als Kopie übernehmen, nur die, die es hier noch
    nicht gibt (oder die in „arten“ genannten). Nur auf ausdrückliche Nachfrage (Product Owner 28.10.2026); der Konnektor
    prüft, dass die Person auf beiden Reisen dabei ist. Nur Organisator:innen. -> (Titel, Text)."""
    von = (text_wert(args, "von_reise", pflicht=True, laenge=60) or "").strip()
    if not REISE_MUSTER.match(von):
        raise Ablehnung("„von_reise“ ist der Ordner einer Reise (aus meine_reisen).")
    quelle_dir = Path(reise_dir).parent / von
    if quelle_dir.resolve() == Path(reise_dir).resolve() or not (quelle_dir / "plan" / "arten.yaml").exists():
        raise Ablehnung(f"Die Reise „{von}“ hat keine Arten (plan/arten.yaml) oder ist diese Reise.")
    fremd = arten_laden(quelle_dir)
    eigene = arten_laden(reise_dir)
    gewuenscht = liste_wert(args, "arten", laenge=40)
    gewuenscht = [a.lower() for a in gewuenscht] if gewuenscht else [a for a in fremd if a not in eigene]
    fehlt = [a for a in gewuenscht if a not in fremd]
    if fehlt:
        raise Ablehnung(f"Die Reise „{von}“ kennt {', '.join(fehlt)} nicht (sie hat: {', '.join(fremd)}).")
    da = [a for a in gewuenscht if a in eigene]
    if da:
        raise Ablehnung(f"{', '.join(da)} gibt es hier schon; vorhandene Arten ändert art_definieren.")
    if not gewuenscht:
        raise Ablehnung(f"Alle Arten von „{von}“ gibt es hier schon.")
    import copy
    for a in gewuenscht:
        eigene[a] = copy.deepcopy(fremd[a])
    arten_speichern(reise_dir, eigene, wer)
    grund = text_wert(args, "grund")
    return f"Arten aus {von} übernommen: {', '.join(gewuenscht)}", (f"Aus der Reise „{von}“ übernommen (als Kopie, hier frei änderbar): "
            + ", ".join(f"{a} „{fremd[a].get('name', a)}“ ({len((fremd[a].get('merkmale') or {}))} Merkmale)" for a in gewuenscht) + "."
            + (f" Grund: {grund}." if grund else ""))


def wunsch_vorschlagen(reise_dir, wer, args, heute=None):
    """Vorschlag zu einem Wunsch (plan/wuensche.yaml, Wunsch-Brett): an welche Stellen er passt (bezug), eine Notiz mit Herkunft
    und, wenn daraus eine Option wurde, deren ID. Eingeplant wird er erst durch eine Organisator:in. -> (Titel, Text)."""
    import io
    rid = (text_wert(args, "wunsch", pflicht=True, laenge=40) or "").strip()
    if not re.fullmatch(r"R-\d{8}-\d{6}-[0-9a-z]{4}", rid):
        raise Ablehnung("„wunsch“ ist die Kennung des Wunschs (R-…, aus wuensche).")
    notiz = text_wert(args, "notiz", pflicht=True, laenge=600)
    roh_r = routen_laden(reise_dir)
    bezug = id_liste(args, "bezug", r"(T-\d+|E-\d+[A-Za-z]?|U-\d+|A-\d+|O-\d+|V-\d+|W-\d+(\.[\w-]+)?)", roh_r) or []
    for x in bezug:
        menge = {"T": "tage", "E": "strecken", "U": "unterkuenfte", "A": "aufenthalte", "O": "orte", "V": "wahlstellen"}.get(x[0])
        if menge and x not in (roh_r.get(menge) or {}):
            raise Ablehnung(f"„bezug“: {x} gibt es nicht.")
    option = text_wert(args, "option", laenge=12)
    if option and not any(o.get("id") == option for w in (roh_r.get("wahlstellen") or {}).values() for o in (w.get("optionen") or []) if isinstance(o, dict)):
        raise Ablehnung(f"„option“: {option} gibt es nicht.")
    p = Path(reise_dir) / "plan" / "wuensche.yaml"
    y = yaml_rund()
    roh = y.load(p.read_text(encoding="utf-8")) if p.exists() else None
    if roh is None:
        from ruamel.yaml.comments import CommentedMap
        roh = CommentedMap()
        roh.yaml_set_start_comment("Vorschläge zu Wünschen (Wunsch-Brett, engine/bauen.py wunsch_vorschlaege): je Wunsch (R-…) die Stellen, an die er passt,\n"
                                   "eine kurze Notiz mit Herkunft und, wenn daraus eine Option wurde, deren ID. Eingeplant wird er erst durch eine Organisator:in.")
    neu_ = {"bezug": bezug, "notiz": notiz}
    if option:
        neu_["option"] = option
    war = rid in roh
    roh[rid] = block_map(neu_)
    out = io.StringIO()
    y.dump(roh, out)
    p.write_text(out.getvalue(), encoding="utf-8")
    return f"Vorschlag zu Wunsch {rid[:14]}… {'geändert' if war else 'eingetragen'}", (f"Vorschlag zum Wunsch {'geändert' if war else 'eingetragen'}: passt zu {', '.join(bezug) or 'keiner festen Stelle'}"
            + (f", Option {option}" if option else "") + f". {notiz} Das Brett zeigt ihn unter „geprüft“; einplanen tut eine Organisator:in.")


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
             "merkmal_zusammenfuehren": merkmal_zusammenfuehren, "arten_uebernehmen": arten_uebernehmen, "wunsch_vorschlagen": wunsch_vorschlagen}
REPO_WERKZEUGE = {"reise_anlegen": reise_anlegen}   # arbeiten auf reisen/, nicht in einer Reise


# ---------- Der Schreibvorgang ----------

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
                raise Ablehnung("Die Reise lässt sich nicht lesen: " + " ".join(e.meldungen))
        rolle = rolle_neu(anfrage.get("rolle"))
        person = anfrage.get("person")
        p = next((x for x in eck.get("personen") or [] if person and x.get("schluessel") == person), None)
        if p:
            rolle = rolle_neu(p.get("rolle"))     # reise.yaml gilt vor dem, was der Konnektor sagt
        name = (p or {}).get("name") or anfrage.get("name")
        if not isinstance(name, str) or not name.strip():
            raise Ablehnung("Schreiben geht nur mit einer Person (Name fehlt).")
        ok, grund = erlaubt(AKTIONEN[werkzeug], rolle, (eck.get("status") or {}).get("wert") or "planung", eck.get("bausteine"),
                            None, eck.get("regeln"))   # einladen richtet sich nach regeln.einladen der Reise
        if not ok:
            raise Ablehnung(grund)
        return {"name": name.strip(), "rolle": rolle, "person": person, "titel": eck.get("titel") or reise_dir.name}

    def probebau(self, reise_dir):
        import bauen
        with tempfile.TemporaryDirectory(prefix="frieda-probe-") as ziel:
            try:
                bauen.Bauer(reise_dir, ziel).daten()
            except bauen.BauFehler as e:
                raise Ablehnung("So lässt sich die Reise nicht bauen, nichts geändert: " + " ".join(e.meldungen))

    def schreiben(self, reise, werkzeug, anfrage):
        """Ein Schreibvorgang in der vorbereiteten Arbeitskopie -> {"ok": True, "text", "commit"}; sonst Ablehnung."""
        if not REISE_MUSTER.match(reise or ""):
            raise Ablehnung("Unbekannte Reise.")
        if werkzeug not in WERKZEUGE and werkzeug not in REPO_WERKZEUGE:
            raise Ablehnung(f"Unbekanntes Werkzeug „{werkzeug}“.")
        args = anfrage.get("args") if isinstance(anfrage.get("args"), dict) else {}
        reise_dir = self.arbeit / "reisen" / reise
        if werkzeug in REPO_WERKZEUGE:
            # Neue Reise: der Konnektor hat Person und Recht geprüft (Konto darf Reisen anlegen); hier Form und Probebau
            name = anfrage.get("name")
            if not isinstance(name, str) or not name.strip():
                raise Ablehnung("Schreiben geht nur mit einer Person (Name fehlt).")
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
                raise Ablehnung(f"Die Reise „{reise}“ gibt es im Repo nicht.")
            wer = self.wer_pruefen(reise_dir, anfrage, werkzeug)
            try:
                titel, text = WERKZEUGE[werkzeug](reise_dir, wer, args)
                self.probebau(reise_dir)
            except Ablehnung:
                git(self.arbeit, "checkout", "-q", "--", f"reisen/{reise}")
                git(self.arbeit, "clean", "-qfd", "--", f"reisen/{reise}")
                raise
        if not git(self.arbeit, "status", "--porcelain", "--", f"reisen/{reise}"):
            raise Ablehnung("Das ändert nichts.")
        nachricht = (f"{wer['titel']}: {titel}\n\n{text}\n\nÜber den Konnektor ({werkzeug}) von {wer['name']} ({wer['rolle']}), "
                     f"{datetime.date.today().isoformat()}; Prüfung: Rolle, Status, Form, Probebau (engine/schreiben.py).\n")
        if os.environ.get("FR_VORGANG"):     # Kennung des Vorgangs: nach einem Abbruch findet vorgang_eingetragen den Eintrag
            nachricht += f"\nFrieda-Vorgang: {os.environ['FR_VORGANG']}\n"
        git(self.arbeit, "add", "-A", "--", f"reisen/{reise}")
        git(self.arbeit, "commit", "-q", "-m", nachricht)
        commit = self.hochladen(reise)
        self.veroeffentlichen_anstossen()
        antwort = {"ok": True, "text": text, "commit": commit}
        if (m := re.match(r"^([A-Z]+-\d+(?:\.[\w-]+)?) ", titel)):   # neu angelegtes Ding: seine ID, damit der Konnektor weitermachen kann
            antwort["id"] = m.group(1)
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
            git(self.arbeit, "fetch", "-q", "origin", "main")
            rb = subprocess.run(["git", "-C", str(self.arbeit), "rebase", "-q", "origin/main"], capture_output=True, text=True)
            if rb.returncode != 0:
                git(self.arbeit, "rebase", "--abort", fehler=False)
                git(self.arbeit, "reset", "-q", "--hard", "origin/main")
                raise Ablehnung(f"Gleichzeitig hat jemand dieselbe Stelle der Reise „{reise}“ geändert; nichts geschrieben. "
                                "Bitte noch einmal versuchen.")
        git(self.arbeit, "reset", "-q", "--hard", "origin/main")
        raise Ablehnung("Das Repo war dauernd beschäftigt; nichts geschrieben. Bitte noch einmal versuchen.")

    def veroeffentlichen_anstossen(self):
        """Veröffentlichen im Hintergrund (holt main in den Veröffentlichungsordner, baut, prüft). Hält der Timer die Sperre,
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
        return 422, {"ok": False, "fehler": str(e)}


# ---------- Dienst ----------

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
    return 504, {"ok": False, "fehler": "Das Schreiben hat zu lange gedauert und ist nicht eingetragen; bitte noch einmal versuchen."}


def nach_abbruch(s, werkzeug, kennung):
    """Antwort, nachdem das Anwenden von der Frist abgebrochen wurde: Ergebnis auf origin/main nachsehen."""
    ergebnis = vorgang_eingetragen(s, kennung)
    if ergebnis:
        sys.stderr.write(f"Zeit {werkzeug} 504: abgebrochen, eingetragen\n")
        text = "Es hat länger gedauert, ist aber eingetragen."
        return 200, {"ok": True, "text": text, "hinweis": text}
    if ergebnis is False:
        return nicht_eingetragen(werkzeug)
    sys.stderr.write(f"Zeit {werkzeug} 504: abgebrochen, ungeprüft\n")
    return 504, {"ok": False, "fehler": "Das Schreiben hat zu lange gedauert; bitte prüfen, ob es angekommen ist."}


def anwenden_extern(s, reise, werkzeug, anfrage):
    """Arbeitskopie holen und `anwenden` mit dem Code der Arbeitskopie ausführen -> (Code, Antwort).
    Sperre und Arbeitskopie gibt es je Reise: Was bei einer Reise hängt, hält die anderen nicht auf (flock gilt auch zwischen
    Threads, jeder öffnet die Datei selbst). Alles zusammen dauert höchstens ZEIT_GESAMT + ZEIT_PRUEFUNG Sekunden; die Dauer
    jedes Vorgangs steht im Protokoll, auch nach einem unerwarteten Fehler (500)."""
    start = time.monotonic()
    code, antwort = 500, {"ok": False, "fehler": "Schreiben fehlgeschlagen (Fehler im Dienst); der Betreiber sieht es im Protokoll."}
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
            return 429, {"ok": False, "fehler": "Bei dieser Reise läuft gerade ein anderer Schreibvorgang; bitte gleich noch einmal versuchen."}
        try:
            git_sperren_raeumen(s.arbeit)     # unter der Sperre der Reise: kein anderes git arbeitet in dieser Kopie
            s.vorbereiten()
        except subprocess.TimeoutExpired:
            return nicht_eingetragen(werkzeug)     # noch nichts angewendet, keine Prüfung nötig
        except RuntimeError as e:
            sys.stderr.write(f"Arbeitskopie: {e}\n")
            return 503, {"ok": False, "fehler": "Das Repo der Reisen ist gerade nicht erreichbar; bitte später noch einmal."}
        skript = s.arbeit / "engine" / "schreiben.py"
        if not skript.exists():
            sys.stderr.write(f"Arbeitskopie: {skript} fehlt\n")
            return 503, {"ok": False, "fehler": "Die Software auf main kennt den Schreibweg noch nicht."}
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
            return 500, {"ok": False, "fehler": "Schreiben fehlgeschlagen (Fehler im Dienst); der Betreiber sieht es im Protokoll."}


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
                return self._senden(403, {"fehler": "nur für den Konnektor"})
            try:
                return self._senden(200, (self.schreiber or Schreiber(wurzel())).buchung_im_repo(teile[0], teile[2]))
            except (RuntimeError, subprocess.TimeoutExpired) as e:
                sys.stderr.write(f"Fehler buchung 503: {' '.join(str(e).split())[:LOG_LAENGE]}\n")
                return self._senden(503, {"fehler": "Das Repo ist gerade nicht erreichbar."})
        self._senden(404, {"fehler": "unbekannt"})

    def do_POST(self):
        if not hmac.compare_digest(self.headers.get("X-Frieda-Dienst", ""), konten.dienst_geheimnis()):
            return self._senden(403, {"fehler": "nur für den Konnektor"})
        teile = self.path.split("?", 1)[0].strip("/").split("/")
        if len(teile) != 2 or not REISE_MUSTER.match(teile[0]) or (teile[1] not in WERKZEUGE and teile[1] not in REPO_WERKZEUGE):
            return self._senden(404, {"fehler": "unbekannt"})
        try:
            laenge = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            laenge = 0
        if laenge <= 0 or laenge > MAX_BODY:
            return self._senden(413, {"fehler": "zu groß oder leer"})
        try:
            anfrage = json.loads(self.rfile.read(laenge).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._senden(400, {"fehler": "kein JSON"})
        if not isinstance(anfrage, dict):
            return self._senden(400, {"fehler": "kein Objekt"})
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
