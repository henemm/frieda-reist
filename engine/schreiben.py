"""Schreibweg: Der Konnektor schreibt direkt in die Ontologie der Reise (ADR-0001, Paket O-3).

Frieda enthält keine KI. Was im AI-Client (Claude-App) erarbeitet wird, kommt über den Konnektor hierher und wird
sofort geschrieben: in das Reisen-Repo (plan/arten.yaml: Arten und Merkmale; plan/routen.yaml: Werte, Dinge, Wahlstellen, Optionen, Entscheidungen, Plan;
offene-fragen.md: Fragen; inhalt/*.md: Wissen; reise.yaml: Personen), geprüft mit einem
Probebau, gesichert als Commit mit Person und Werkzeug, nach main gebracht und veröffentlicht. Dieses Modul ist die
einzige Stelle, an der ein Dienst Reisedateien ändert.

Zwei Teile:
  Dienst   `schreiben.py dienst` auf 127.0.0.1:<FR_SB_PORT> (8773), nur für den Konnektor (Header X-Frieda-Dienst, das
           gemeinsame Dienst-Geheimnis). POST /<reise>/<werkzeug> mit {"person", "name", "rolle", "args"}. Ein
           Schreibvorgang zur Zeit (Sperre). Je Anfrage bringt er die Arbeitskopie auf origin/main und startet dort einen
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
import subprocess
import sys
import tempfile
import threading
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
ZEIT_ANWENDEN = 150     # Sekunden für einen Schreibvorgang (fetch, Probebau, push)
AKTIONEN = {"art_definieren": "ontologie", "merkmal_definieren": "ontologie", "wert_eintragen": "wert",
            "ding_anlegen": "ding", "ding_aendern": "ding", "option_anlegen": "alternative", "wahlstelle_anlegen": "alternative",
            "frage_anlegen": "frage", "entscheiden": "entscheiden", "tag_aendern": "plan", "wissen_schreiben": "wissen",
            "frage_schliessen": "frage_schliessen", "person_schreiben": "einladen", "reise_status_setzen": "einstellung",
            "einstellung_setzen": "einstellung"}   # reise.AKTIONEN
ARTEN_KOPF = ("# Arten und Merkmale dieser Reise (docs/ontologie.md, ADR-0001). {herkunft}\n"
              "# Felder je Art: grundform (aufenthalt | bewegung | folge), name, farbe, summiert, merkmale, lesetext (Gliederung des\n"
              "# Lesetexts: je Rubrik name und hilfe); je Merkmal: name, typ,\n"
              "# werte, veraenderlich, stufe (pflicht | empfohlen | angeboten | aus), auto, hilfe, frage, auch.\n")
GRUNDFORM_WORT = {"aufenthalt": "Aufenthalt", "bewegung": "Bewegung", "folge": "Folge"}
_sperre = threading.Lock()


class Ablehnung(Exception):
    """Der Schreibweg lehnt ab; der Text ist für den AI-Client (einfache Worte, nennt den Grund)."""


# ---------- Hilfen ----------

def git(ordner, *args, fehler=True):
    r = subprocess.run(["git", "-C", str(ordner), *args], capture_output=True, text=True)
    if fehler and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def wurzel():
    return Path(os.environ.get("FR_WURZEL") or instanz.wurzel())


def schreibkopie(w=None):
    w = Path(w or wurzel())
    return Path(os.environ.get("FR_SCHREIBKOPIE") or f"{w}-schreiben")


def text_wert(args, feld, pflicht=False, laenge=MAX_TEXT):
    """Ein Textfeld der Anfrage, bereinigt -> str oder None (fehlt oder leer)."""
    v = args.get(feld)
    if v is None or (isinstance(v, str) and not v.strip()):
        if pflicht:
            raise Ablehnung(f"„{feld}“ fehlt.")
        return None
    if not isinstance(v, str):
        raise Ablehnung(f"„{feld}“ muss Text sein.")
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


def art_definieren(reise_dir, wer, args):
    """Eine Art anlegen oder ändern. -> (Titel für den Commit, Text für den AI-Client)."""
    from routen import ALLGEMEIN, ART_MUSTER, AUTO_JE_GRUNDFORM, FARBEN, GRUNDFORMEN, UNTERWEGS, art_schluessel
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
        if beschreibung:
            a["beschreibung"] = beschreibung
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
        if not geaendert:
            raise Ablehnung(f"Die Art „{a.get('name', key)}“ ({key}) gibt es schon, und nichts daran soll sich ändern. Merkmale "
                            "ändert merkmal_definieren.")
        arten[key] = {k: a[k] for k in ("grundform", "name", "farbe", "summiert", "beschreibung", "merkmale", "lesetext")
                     if k in a}
        titel = f"Art „{a['name']}“ ({key}) geändert"
        text = f"Art „{a['name']}“ ({key}) geändert: " + ", ".join(geaendert) + "."
    arten_speichern(reise_dir, arten, wer)
    return titel, text + (f" Grund: {grund}." if grund else "")


def merkmal_definieren(reise_dir, wer, args):
    """Ein Merkmal einer Art anlegen oder ändern (umbenennen, Stufe, abschalten mit Stufe aus). -> (Titel, Text)."""
    from routen import STUFEN, TYPEN, art_schluessel
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
    if stufe is not None and stufe.lower() not in STUFEN:
        raise Ablehnung(f"„stufe“ muss eine von {', '.join(STUFEN)} sein (pflicht und empfohlen zählen als „fehlt noch“, angeboten "
                        "wird nur gezeigt, aus gilt für diese Reise nicht).")
    werte = liste_wert(args, "werte")
    veraenderlich = bool_wert(args, "veraenderlich")
    einheit, hilfe, frage, grund = (text_wert(args, f) for f in ("einheit", "hilfe", "frage", "grund"))
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
        if stufe and stufe.lower() != "empfohlen":
            d["stufe"] = stufe.lower()
        for f, v in (("hilfe", hilfe), ("frage", frage), ("auch", auch)):
            if v:
                d[f] = v
        merkmale[key] = d
        titel = f"Merkmal „{name}“ ({key}) an {a.get('name', art)} angelegt"
        text = (f"Merkmal „{name}“ ({key}) an der Art {a.get('name', art)} angelegt: Typ {typ}"
                + (f" ({' | '.join(werte)})" if werte else "") + (", veränderlich (braucht Prüfdatum)" if veraenderlich else "")
                + f", Stufe {(stufe or 'empfohlen').lower()}.")
    else:
        d = merkmale[key]
        if d.get("auto"):
            raise Ablehnung(f"„{d.get('name', key)}“ wird aus dem Plan berechnet; daran lässt sich nur Name und Stufe ändern."
                            if any(x is not None for x in (typ, werte, veraenderlich, einheit)) else "")
        geaendert = []
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
        if stufe is not None and stufe.lower() != (d.get("stufe") if isinstance(d.get("stufe"), str) else "empfohlen"):
            geaendert.append("abgeschaltet (Stufe aus)" if stufe.lower() == "aus" else f"Stufe {stufe.lower()}")
            if stufe.lower() == "empfohlen":
                d.pop("stufe", None)
            else:
                d["stufe"] = stufe.lower()
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
        merkmale[key] = {k: d[k] for k in ("name", "typ", "werte", "auto", "veraenderlich", "einheit", "stufe", "hilfe", "frage", "auch")
                         if k in d}
        titel = f"Merkmal „{d['name']}“ ({key}) an {a.get('name', art)} geändert"
        text = f"Merkmal „{d['name']}“ ({key}) an der Art {a.get('name', art)} geändert: " + ", ".join(geaendert) + "."
    a["merkmale"] = merkmale
    arten_speichern(reise_dir, arten, wer)
    return titel, text + (f" Grund: {grund}." if grund else "")


# ---------- Werte an Dingen (plan/routen.yaml) ----------
# Die Routendatei wird mit ruamel.yaml rund gelesen und geschrieben: Kommentare, Reihenfolge und Fließform bleiben; nur von
# Hand umbrochene Fließ-Mappings werden in eine Zeile gezogen (einmalige Normalform, danach ändert ein Schreibvorgang nur seine Stelle).
ZIEL_MUSTER = re.compile(r"^(U-\d+|E-\d+[A-Za-z]?|V-\d+\.[a-z])$")


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
    """-> (Knoten in der Routendatei, Beschreibung) für U-…, E-… oder eine Option V-01.a."""
    if ziel.startswith("U-"):
        k = (roh.get("unterkuenfte") or {}).get(ziel)
        if k is None:
            raise Ablehnung(f"Die Unterkunft {ziel} gibt es nicht.")
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
    elif ziel.startswith("U-"):
        u = (route.get("unterkuenfte") or {}).get(ziel)
        if u is None:
            raise Ablehnung(f"Die Unterkunft {ziel} gibt es nicht.")
        krit = (route.get("merkmale") or {}).get(u.get("art")) or []
        heutige = u.get("merkmale") or {}
    else:
        st = (route.get("strecken") or {}).get(ziel)
        if st is None:
            raise Ablehnung(f"Die Strecke {ziel} gibt es nicht.")
        krit = (route.get("merkmale") or {}).get(st.get("art") or st.get("bereich")) or []
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
DING_ARTEN = {"unterkunft": ("U", "unterkuenfte"), "strecke": ("E", "strecken"), "ort": ("O", "orte")}
ID_MUSTER = re.compile(r"^(T-\d+|E-\d+[A-Za-z]?|U-\d+|O-\d+|V-\d+|W-\d+(\.[\w-]+)?|F-\d+)$")


PLAIN_FELDER = {"id", "status", "wer", "art", "typ", "ort", "von", "nach", "frage", "siehe", "bereich", "an", "unterkuenfte",
                "strecken", "folge", "erfordert", "schliesst_aus", "auswahl"}
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


def ding_anlegen(reise_dir, wer, args, heute=None):
    """Eine Unterkunft, Strecke oder einen Ort anlegen (neue ID aus ids.yaml, nie neu vergeben). -> (Titel, Text)."""
    heute = heute or datetime.date.today()
    was = (text_wert(args, "was", pflicht=True, laenge=20) or "").lower()
    if was not in DING_ARTEN:
        raise Ablehnung("„was“ muss unterkunft, strecke oder ort sein.")
    kuerzel, abschnitt = DING_ARTEN[was]
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    arten = route.get("arten") or {}
    quelle = text_wert(args, "quelle", pflicht=True)
    hinweis = text_wert(args, "hinweis")
    d = {}
    if was == "ort":
        d["name"] = text_wert(args, "name_des_dings", laenge=120) or text_wert(args, "titel", pflicht=True, laenge=120)
    elif was == "unterkunft":
        d["name"] = text_wert(args, "name_des_dings", laenge=120) or text_wert(args, "titel", pflicht=True, laenge=120)
        d["ort"] = (id_liste(args, "ort", r"O-\d+", roh, "orte", pflicht=True) or [None])[0]
        art = (text_wert(args, "art", pflicht=True, laenge=40) or "").lower()
        if art not in arten or arten[art].get("grundform") != "aufenthalt":
            raise Ablehnung(f"„art“ muss eine Aufenthalts-Art dieser Reise sein ({', '.join(k for k, a in arten.items() if a.get('grundform') == 'aufenthalt') or 'keine'}); "
                            "eine neue legt ein:e Organisator:in mit art_definieren an.")
        d["typ"] = arten[art].get("name") or art
        d["art"] = art
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
    if hinweis:
        d["hinweis"] = hinweis
    d["quelle"] = quelle
    werte = merkmale_werte(args.get("merkmale"), (route.get("merkmale") or {}).get(d.get("art")) or [], heute,
                           {"quelle": quelle, "geprueft": args.get("geprueft")}) if was != "ort" else {}
    did = neue_id(reise_dir, kuerzel)
    knoten = fliess_map(d) if was != "unterkunft" else block_map(d)
    if werte:
        if was == "strecke":
            knoten = block_map(d)
        knoten["merkmale"] = merkmale_knoten(werte)
    roh.setdefault(abschnitt, type(roh)())
    roh[abschnitt][did] = knoten
    name = d.get("name") or d.get("titel")
    titel = f"{did} {name} angelegt ({was})"
    text = (f"{was.capitalize()} {did} „{name}“ angelegt" + (f" in {route.get('orte', {}).get(d['ort'], {}).get('name', d['ort'])}" if was == "unterkunft" else "")
            + (f", Art {d['art']}" if d.get("art") else "") + (f", Merkmale: {', '.join(werte)}" if werte else "") + f". Herkunft: {quelle}."
            + (" Als Alternative gehört es noch in eine Wahlstelle (option_anlegen oder wahlstelle_anlegen)." if was == "unterkunft" else ""))
    routen_speichern(reise_dir, roh)
    return titel, text


AENDERBAR = {"unterkunft": ("name", "ort", "art", "hinweis", "quelle", "buchungslink", "frage"),
             "strecke": ("titel", "von", "nach", "art", "hinweis", "quelle"), "ort": ("name", "hinweis", "quelle")}


def ding_aendern(reise_dir, wer, args, heute=None):
    """Felder einer Unterkunft, Strecke oder eines Orts ändern (nicht die Merkmale: wert_eintragen). -> (Titel, Text)."""
    from reise import darf
    ziel = (text_wert(args, "ziel", pflicht=True, laenge=20) or "").strip()
    was = next((w for w, (k, _) in DING_ARTEN.items() if ziel.startswith(k + "-")), None)
    if was is None or not ID_MUSTER.match(ziel):
        raise Ablehnung("„ziel“ muss eine Unterkunft U-…, eine Strecke E-… oder ein Ort O-… sein.")
    route = route_stand(reise_dir)
    roh = routen_laden(reise_dir)
    knoten, bezeichnung = ding_finden(roh, ziel) if was != "ort" else ((roh.get("orte") or {}).get(ziel), ziel)
    if knoten is None:
        raise Ablehnung(f"{ziel} gibt es nicht.")
    if was == "ort":
        bezeichnung = f"{ziel} {knoten.get('name', '')}".strip()
    arten = route.get("arten") or {}
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
            g = "aufenthalt" if was == "unterkunft" else "bewegung"
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
        else:
            v = text_wert(args, feld, laenge=600 if feld == "quelle" else MAX_TEXT) or ""
        alt = knoten.get(feld) if feld != "art" else (knoten.get("art") or knoten.get("typ"))
        if v == "" and feld in ("hinweis", "buchungslink", "frage"):
            if feld in knoten:
                geaendert.append(f"{feld} entfernt (war „{alt}“)")
                del knoten[feld]
            continue
        if str(alt) == str(v):
            continue
        geaendert.append(f"{feld} „{alt}“ → „{v}“" if alt is not None else f"{feld} „{v}“")
        knoten[feld] = skalar(feld, v)
        if feld == "art" and was == "unterkunft":
            knoten["typ"] = skalar("typ", arten[v].get("name") or v)
    if not geaendert:
        raise Ablehnung(f"Nichts zu ändern an {bezeichnung} (änderbar: {', '.join(AENDERBAR[was])}; Merkmale mit wert_eintragen).")
    grund = text_wert(args, "grund")
    routen_speichern(reise_dir, roh)
    titel = f"{bezeichnung} geändert: " + "; ".join(g.split(" „")[0] for g in geaendert)
    text = f"{bezeichnung}: " + "; ".join(geaendert) + "." + (f" Grund: {grund}." if grund else "")
    return titel, text


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
    """Eine Option aus der Anfrage -> CommentedMap (Status vorgeschlagen mit Verlauf). bereich: Art der Wahlstelle für die Merkmale."""
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
    quelle = text_wert(o, "quelle") or f"Vorschlag von {wer['name']} im Gespräch (Claude-App)"
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
    knoten, d, werte = option_bauen(roh, route, vid, args, wer, heute, wr.get("bereich"))
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
    art = (text_wert(args, "art", laenge=20) or "planung").lower()
    if art not in ("planung", "unterwegs"):
        raise Ablehnung("„art“ einer Wahlstelle ist planung (vor der Abreise entscheiden) oder unterwegs (mit Auslöser).")
    d["art"] = art
    bereich = text_wert(args, "bereich", laenge=40)
    if bereich is not None:
        bereich = bereich.lower()
        if bereich not in arten:
            raise Ablehnung(f"„bereich“ muss eine Art dieser Reise sein ({', '.join(arten) or 'keine'}).")
        d["bereich"] = bereich
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
    gewählt setzt bisher gewählte Optionen derselben Wahlstelle auf ersetzt und klärt die Frage der Wahlstelle; verworfen oder
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
        if status == "gewaehlt":
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
    """Einen Tag des Plans ändern: Titel, Text, Nacht (U-…, V-… oder leer), Strecken (E-…/V-…), Wahlstellen unterwegs (V-…).
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
                                 ("wahl", r"V-\d+", {"V": "wahlstellen"})):
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
        raise Ablehnung(f"Nichts zu ändern an {tid} (titel, text, nacht, strecken, wahl).")
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
    text = text_wert(args, "text", pflicht=True, laenge=6000)
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


WERKZEUGE = {"art_definieren": art_definieren, "merkmal_definieren": merkmal_definieren, "wert_eintragen": wert_eintragen,
             "ding_anlegen": ding_anlegen, "ding_aendern": ding_aendern, "option_anlegen": option_anlegen,
             "wahlstelle_anlegen": wahlstelle_anlegen, "frage_anlegen": frage_anlegen, "entscheiden": entscheiden,
             "tag_aendern": tag_aendern, "wissen_schreiben": wissen_schreiben, "frage_schliessen": frage_schliessen,
             "person_schreiben": person_schreiben, "reise_status_setzen": reise_status_setzen, "einstellung_setzen": einstellung_setzen}
REPO_WERKZEUGE = {"reise_anlegen": reise_anlegen}   # arbeiten auf reisen/, nicht in einer Reise


# ---------- Der Schreibvorgang ----------

class Schreiber:
    """Arbeitskopie des Reisen-Repos für den Schreibweg: holen, ändern, prüfen, sichern, veröffentlichen."""

    def __init__(self, wurzel, arbeit=None, veroeffentlichen=None):
        self.wurzel = Path(wurzel)
        self.arbeit = Path(arbeit or schreibkopie(self.wurzel))
        self.veroeffentlichen = veroeffentlichen or os.environ.get("SB_VEROEFFENTLICHEN") \
            or str(self.wurzel / "frieda" / "betrieb" / "veroeffentlichen.sh")

    def vorbereiten(self):
        """Arbeitskopie anlegen oder auf origin/main bringen; eigene Reste verwerfen."""
        git(self.wurzel, "fetch", "-q", "origin", "main")
        if not (self.arbeit / ".git").exists():
            self.arbeit.parent.mkdir(parents=True, exist_ok=True)
            git(self.wurzel, "worktree", "prune")
            git(self.wurzel, "worktree", "add", "-q", "--detach", str(self.arbeit), "origin/main")
        else:
            git(self.arbeit, "reset", "-q", "--hard")
            git(self.arbeit, "clean", "-qfd", "--", "reisen")
            git(self.arbeit, "checkout", "-q", "--detach", "origin/main")
        if (self.arbeit / ".gitmodules").exists():
            git(self.arbeit, "submodule", "update", "--init", "--quiet")

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
        git(self.arbeit, "add", "-A", "--", f"reisen/{reise}")
        git(self.arbeit, "commit", "-q", "-m", nachricht)
        commit = self.hochladen(reise)
        self.veroeffentlichen_anstossen()
        return {"ok": True, "text": text, "commit": commit}

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
        meldet das Skript „Läuft schon“, und der Timer holt es in wenigen Minuten nach."""
        if not self.veroeffentlichen or not Path(self.veroeffentlichen).exists():
            return
        env = {**os.environ, "FR_WURZEL": str(self.wurzel)}
        subprocess.Popen([self.veroeffentlichen], env=env, stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr,
                         start_new_session=True)


def anwenden(wurzel_, arbeit, reise, werkzeug, anfrage):
    """Ein Schreibvorgang (Arbeitskopie ist vorbereitet) -> Antwort-Objekt mit HTTP-Code."""
    s = Schreiber(wurzel_, arbeit)
    try:
        return 200, s.schreiben(reise, werkzeug, anfrage)
    except Ablehnung as e:
        return 422, {"ok": False, "fehler": str(e)}


# ---------- Dienst ----------

def sperrdatei():
    name = instanz.wert("FR_INSTANZ", instanz.VORGABE_INSTANZ)
    return Path(instanz.wert("FR_SPERREN", "/tmp")) / f"{name}-schreiben.lock"


def anwenden_extern(s, reise, werkzeug, anfrage):
    """Arbeitskopie holen und `anwenden` mit dem Code der Arbeitskopie ausführen -> (Code, Antwort)."""
    with _sperre, open(sperrdatei(), "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            s.vorbereiten()
        except RuntimeError as e:
            sys.stderr.write(f"Arbeitskopie: {e}\n")
            return 503, {"ok": False, "fehler": "Das Repo der Reisen ist gerade nicht erreichbar; bitte später noch einmal."}
        skript = s.arbeit / "engine" / "schreiben.py"
        if not skript.exists():
            return 503, {"ok": False, "fehler": "Die Software auf main kennt den Schreibweg noch nicht."}
        try:
            r = subprocess.run([sys.executable, str(skript), "anwenden", reise, werkzeug], input=json.dumps(anfrage),
                               capture_output=True, text=True, timeout=ZEIT_ANWENDEN,
                               env={**os.environ, "FR_WURZEL": str(s.wurzel), "FR_SCHREIBKOPIE": str(s.arbeit)})
        except subprocess.TimeoutExpired:
            return 504, {"ok": False, "fehler": "Das Schreiben hat zu lange gedauert; bitte prüfen, ob es angekommen ist."}
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
        if self.path.split("?", 1)[0] == "/gesund":
            s = self.schreiber or Schreiber(wurzel())
            ok = (s.wurzel / ".git").exists() and subprocess.run(["git", "-C", str(s.wurzel), "rev-parse", "--git-dir"],
                                                               capture_output=True).returncode == 0
            return self._senden(200 if ok else 503, {"gesund": ok})
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
