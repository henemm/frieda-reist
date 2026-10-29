"""Schreibweg: Der Konnektor schreibt direkt in die Ontologie der Reise (ADR-0001, Paket O-3).

Frieda enthält keine KI. Was im AI-Client (Claude-App) erarbeitet wird, kommt über den Konnektor hierher und wird
sofort geschrieben: in das Reisen-Repo (plan/arten.yaml: Arten und Merkmale; plan/routen.yaml: Werte an Dingen), geprüft mit einem
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
AKTIONEN = {"art_definieren": "ontologie", "merkmal_definieren": "ontologie", "wert_eintragen": "wert"}   # reise.AKTIONEN
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


WERKZEUGE = {"art_definieren": art_definieren, "merkmal_definieren": merkmal_definieren, "wert_eintragen": wert_eintragen}


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
                            None, eck.get("regeln"))
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
        if werkzeug not in WERKZEUGE:
            raise Ablehnung(f"Unbekanntes Werkzeug „{werkzeug}“.")
        reise_dir = self.arbeit / "reisen" / reise
        if not (reise_dir / "reise.json").exists():
            raise Ablehnung(f"Die Reise „{reise}“ gibt es im Repo nicht.")
        args = anfrage.get("args") if isinstance(anfrage.get("args"), dict) else {}
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
        if len(teile) != 2 or not REISE_MUSTER.match(teile[0]) or teile[1] not in WERKZEUGE:
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
