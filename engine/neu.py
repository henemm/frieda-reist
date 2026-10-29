"""Neue Reise anlegen, Abschnitte mit neuen IDs, Prüfung vor dem Bau (Paket H, docs/neue-reise.md).

Eine neue Reise entsteht aus Eckdaten und Personen, im Gespräch erfragt (Claude Code oder Claude-App). Grundlage ist
die Vorlage in engine/reisevorlage/; reise.yaml, reise.json und ids.yaml schreibt dieses Skript. Die Reise steht
danach im Status „idee“ und baut sofort.

  neu.py reise <reisen-ordner> --titel T --von JJJJ-MM-TT --bis JJJJ-MM-TT --person schluessel=Name:rolle[:nicht] …
         --wer Name [--ziel Ort] [--pfad ordner] [--untertitel U] [--herkunft H] [--ueberblick Text]
  neu.py id <reise-ordner> <W|F|O|U|E|T|V>        nächste freie ID, wird sofort als vergeben vermerkt
  neu.py abschnitt <reise-ordner> --titel T [--gruppe wissen|praxis|quelle] [--datei inhalt/wissen.md] [--text-datei P]
  neu.py pruefen <reise-ordner>                   Prüfung vor dem Bau mit verständlichen Meldungen

IDs werden nie neu vergeben: ids.yaml hält je Art die höchste je vergebene Nummer fest. Die nächste ID liegt über
dieser Marke und über jeder Nummer, die irgendwo in der Reise steht (auch im Verlauf von Verworfenem).
"""
import datetime
import json
import re
import string
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
from reise import PFAD_MUSTER, ROLLEN, reise_pfad, rolle_neu, schluessel_aus_name  # noqa: E402

VORLAGE = Path(__file__).with_name("reisevorlage")
ARTEN = ("W", "F", "O", "U", "E", "T", "V")          # nummerierte IDs; Pläne (P-A) und Aufgaben (AG, live) nicht
GRUPPEN = ("wissen", "praxis", "quelle")
ROLLE_TEXT = {"organisator": "organisiert", "mitwirkend": "bringt ein", "gast": "liest mit"}
BAUSTEINE_IDEE = ["rueckmeldungen", "fragen", "aufgaben", "wuensche"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
          "Dezember"]


class Fehler(Exception):
    """Eingabe passt nicht; der Text ist für Menschen geschrieben."""


# ---------- Hilfen ----------
def datum_text(d):
    return f"{d.day}.{d.month}.{d.year}"


def zeitraum_text(von, bis):
    if von.year == bis.year and von.month == bis.month:
        return f"{von.day}.–{bis.day}. {MONATE[von.month - 1]} {von.year}"
    if von.year == bis.year:
        return f"{von.day}.{von.month}.–{bis.day}.{bis.month}.{bis.year}"
    return f"{datum_text(von)}–{datum_text(bis)}"


def json_text(obj, tiefe=0):
    """JSON wie in den Reisen von Hand: zwei Leerzeichen, kurze Listen aus Werten in einer Zeile."""
    ein = "  " * (tiefe + 1)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        teile = [f"{ein}{json.dumps(k, ensure_ascii=False)}: {json_text(v, tiefe + 1)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(teile) + "\n" + "  " * tiefe + "}"
    if isinstance(obj, list) and all(not isinstance(x, (dict, list)) for x in obj):
        return json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, list):
        return "[\n" + ",\n".join(ein + json_text(x, tiefe + 1) for x in obj) + "\n" + "  " * tiefe + "]"
    return json.dumps(obj, ensure_ascii=False)


def lies_json(pfad):
    return json.loads(pfad.read_text(encoding="utf-8"))


def schreib_json(pfad, obj):
    pfad.write_text(json_text(obj) + "\n", encoding="utf-8")


def person_aus_text(text):
    """„hanna=Hanna:mitwirkend“ oder „Ben:gast:nicht“ -> (schluessel, {name, rolle[, reist]})."""
    schluessel, _, rest = text.rpartition("=") if "=" in text else ("", "", text)
    teile = [t.strip() for t in rest.split(":")]
    if len(teile) < 2 or not teile[0]:
        raise Fehler(f"Person „{text}“: bitte als Name:rolle angeben, z. B. Hanna:mitwirkend.")
    name, rolle = teile[0], rolle_neu(teile[1])
    if rolle not in ROLLEN:
        raise Fehler(f"Person {name}: Rolle „{rolle}“ gibt es nicht; möglich sind {', '.join(ROLLEN)}.")
    p = {"name": name, "rolle": rolle}
    if len(teile) > 2:
        if teile[2] not in ("reist", "nicht"):
            raise Fehler(f"Person {name}: drittes Feld ist „reist“ oder „nicht“ (reist nicht mit).")
        p["reist"] = teile[2] == "reist"
    return (schluessel.strip() or schluessel_aus_name(name)), p


# ---------- IDs ----------
def _nummern(reise_dir, art):
    muster = re.compile(rf"(?<![A-Za-z0-9]){art}-(\d+)")
    n = 0
    for f in reise_dir.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".yaml", ".yml", ".json") and "medien" not in f.relative_to(reise_dir).parts:
            for m in muster.finditer(f.read_text(encoding="utf-8", errors="replace")):
                n = max(n, int(m.group(1)))
    return n


def naechste_id(reise_dir, art):
    """Nächste freie ID einer Art; die Marke in ids.yaml steigt sofort, damit keine ID zweimal vergeben wird."""
    if art not in ARTEN:
        raise Fehler(f"IDs der Art „{art}“ vergibt dieses Skript nicht; möglich sind {', '.join(ARTEN)}.")
    reise_dir = Path(reise_dir)
    datei = reise_dir / "ids.yaml"
    marken = (yaml.safe_load(datei.read_text(encoding="utf-8")) or {}) if datei.exists() else {}
    n = max(int(marken.get(art) or 0), _nummern(reise_dir, art)) + 1
    if isinstance(marken.get("ids"), dict):
        # Reise mit ID-Liste (je Art alle vergebenen IDs): die neue ID kommt dazu, Liste und Kopfkommentar bleiben
        marken["ids"].setdefault(art, []).append(f"{art}-{n:02d}")
        kopf = "".join(z for z in datei.read_text(encoding="utf-8").splitlines(keepends=True)
                       if z.startswith("#"))
        datei.write_text(kopf + yaml.safe_dump(marken, sort_keys=False, allow_unicode=True, default_flow_style=None,
                                               width=10**6), encoding="utf-8")
    else:
        marken[art] = n
        schreib_marken(reise_dir, marken)
    return f"{art}-{n:02d}"


def schreib_marken(reise_dir, marken):
    marken = {a: marken[a] for a in ARTEN if a in marken}
    (Path(reise_dir) / "ids.yaml").write_text("# Höchste je vergebene Nummer je Art (engine/neu.py). IDs werden nie "
                                              "neu vergeben.\n" + yaml.safe_dump(marken, sort_keys=False),
                                              encoding="utf-8")


# ---------- Reise anlegen ----------
def anlegen(reisen_dir, titel, von, bis, personen, wer, ziel=None, pfad=None, untertitel=None,
            herkunft="Gespräch in Claude Code", ueberblick=None, heute=None):
    """Legt reisen_dir/<pfad> aus der Vorlage an -> Ordner. personen: {schluessel: {name, rolle[, reist, notiz]}}."""
    heute = heute or datetime.date.today()
    titel = (titel or "").strip()
    if not titel:
        raise Fehler("Die Reise braucht einen Titel.")
    if not isinstance(von, datetime.date) or not isinstance(bis, datetime.date):
        raise Fehler("Zeitraum: von und bis als Datum angeben (JJJJ-MM-TT).")
    if bis < von:
        raise Fehler(f"Zeitraum: Das Ende ({datum_text(bis)}) liegt vor dem Anfang ({datum_text(von)}).")
    if not personen:
        raise Fehler("Die Reise braucht mindestens eine Person, die bestimmt.")
    organisator = [p["name"] for p in personen.values() if p.get("rolle") == "organisator"]
    if not organisator:
        raise Fehler("Mindestens eine Person braucht die Rolle organisator: Sie entscheidet und setzt den Status.")
    if wer not in organisator:
        raise Fehler(f"Anlegen darf nur, wer auf der Reise bestimmt. {wer} steht nicht als organisator in den Personen.")
    pfad = pfad or reise_pfad(titel, von.year)
    if not PFAD_MUSTER.match(pfad):
        raise Fehler(f"Ordnername „{pfad}“: nur Kleinbuchstaben, Ziffern und Bindestrich.")
    ziel_dir = Path(reisen_dir) / pfad
    if ziel_dir.exists():
        raise Fehler(f"Eine Reise „{pfad}“ gibt es schon. Bitte einen anderen Ordnernamen wählen (--pfad).")

    zt = zeitraum_text(von, bis)
    werte = {
        "titel": titel, "zeitraum_text": zt, "ziel_text": ziel or "noch offen", "wer": wer,
        "personen_text": ", ".join(f"{p['name']} ({ROLLE_TEXT[p['rolle']]}{'' if p.get('reist', True) else ', reist nicht mit'})"
                                   for p in personen.values()),
        "heute_text": datum_text(heute), "herkunft": herkunft,
        "ueberblick": ueberblick or "Noch leer. Hier steht, was über Ziel und Gegend wichtig ist, in eigenen Worten "
                                    "und mit Quelle.",
    }
    for f in sorted(VORLAGE.rglob("*")):
        if f.is_file():
            z = ziel_dir / f.relative_to(VORLAGE)
            z.parent.mkdir(parents=True, exist_ok=True)
            z.write_text(string.Template(f.read_text(encoding="utf-8")).substitute(werte), encoding="utf-8")
    (ziel_dir / "medien").mkdir(exist_ok=True)

    reise = {
        "titel": titel,
        "untertitel": untertitel or (f"{ziel}, {zt}" if ziel else zt),
        "pfad": pfad,
        "zeitraum": {"von": von, "bis": bis},
        "status": {"wert": "idee", "verlauf": [{"datum": heute, "wert": "idee", "wer": wer,
                                                 "grund": f"Reise angelegt ({herkunft})"}]},
        "personen": personen,
        "bausteine": BAUSTEINE_IDEE,
        "darstellung": {"gruppen": {"wissen": "Wissen", "praxis": "Praxis", "quelle": "Quellen"}},
    }
    (ziel_dir / "reise.yaml").write_text(
        "# Eckdaten, Zeitraum, Status, Personen und Einstellungen (engine/reise.py, docs/produkt.md).\n"
        "# Status und Einstellungen ändert nur ein:e Organisator:in, mit Verlaufseintrag.\n\n"
        + yaml.safe_dump(reise, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")
    schreib_json(ziel_dir / "reise.json", {
        "plan": "plan/plan.md",
        "fragen": "offene-fragen.md",
        "abschnitte": {
            "plan/plan.md": {"Eckdaten": ["W-01", "plan"]},
            "inhalt/wissen.md": {"Überblick": ["W-02", "wissen"], "Quellen": ["W-03", "quelle"]},
        },
    })
    schreib_marken(ziel_dir, {"W": 3, "F": 1})   # vergeben von der Vorlage: W-01 bis W-03, F-01
    return ziel_dir


def aus_auftrag(reisen_dir, auftrag, heute=None):
    """Reise aus einem Auftrag „reise_anlegen“ der Claude-App (daten.neue_reise, vom Konnektor geprüft) -> Ordner.
    Die Notiz (in der App schon in eigenen Worten mit Herkunft) wird der Überblick, mit Name und Datum davor."""
    n = (auftrag.get("daten") or {}).get("neue_reise")
    if not n:
        raise Fehler(f"{auftrag.get('id')}: kein Auftrag für eine neue Reise.")
    datum = datum_text(datetime.date.fromisoformat(str(auftrag.get("erstellt", ""))[:10] or (heute or datetime.date.today()).isoformat()))
    ueberblick = f"Notiz von {n['wer']} aus der Claude-App ({datum}):\n\n{n['notiz']}" if n.get("notiz") else None
    return anlegen(reisen_dir, n["titel"], datetime.date.fromisoformat(n["von"]), datetime.date.fromisoformat(n["bis"]),
                   n["personen"], n["wer"], ziel=n.get("ziel") or None, pfad=n["pfad"], ueberblick=ueberblick,
                   herkunft=f"Auftrag {auftrag['id']} aus der Claude-App", heute=heute)


# ---------- Abschnitt mit neuer ID ----------
def abschnitt(reise_dir, titel, gruppe="wissen", datei="inhalt/wissen.md", text=""):
    """Hängt „## titel“ an datei an und ordnet ihm eine neue W-ID zu -> ID."""
    reise_dir = Path(reise_dir)
    titel = (titel or "").strip()
    if not titel or "\n" in titel:
        raise Fehler("Der Abschnitt braucht einen Titel in einer Zeile.")
    if gruppe not in GRUPPEN:
        raise Fehler(f"Gruppe „{gruppe}“ gibt es nicht; möglich sind {', '.join(GRUPPEN)}.")
    cfg = lies_json(reise_dir / "reise.json")
    zuordnung = cfg.setdefault("abschnitte", {}).setdefault(datei, {})
    if titel in zuordnung:
        raise Fehler(f"In {datei} gibt es schon einen Abschnitt „{titel}“ ({zuordnung[titel][0]}).")
    f = reise_dir / datei
    if f.exists() and re.search(rf"^## {re.escape(titel)}\s*$", f.read_text(encoding="utf-8"), re.M):
        raise Fehler(f"In {datei} steht die Überschrift „{titel}“ schon, aber ohne ID. Bitte in reise.json zuordnen.")
    neu = naechste_id(reise_dir, "W")
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# {cfg_titel(reise_dir)}\n", encoding="utf-8")
    alt = f.read_text(encoding="utf-8").rstrip("\n")
    f.write_text(f"{alt}\n\n## {titel}\n\n{text.strip()}\n" if text.strip() else f"{alt}\n\n## {titel}\n",
                 encoding="utf-8")
    zuordnung[titel] = [neu, gruppe]
    schreib_json(reise_dir / "reise.json", cfg)
    return neu


def cfg_titel(reise_dir):
    p = Path(reise_dir) / "reise.yaml"
    try:
        return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("titel") or Path(reise_dir).name
    except (OSError, yaml.YAMLError):
        return Path(reise_dir).name


# ---------- Prüfung vor dem Bau ----------
DATEI_SCHLUESSEL = ("plan", "fragen", "etappen_dossier", "unterkuenfte_dossier", "orte_wissen", "wissen_punkte")


def pruefen(reise_dir):
    """-> (ok, meldungen). Prüft Dateien und Schreibweise, dann einen Probebau; die Meldungen sagen, was zu tun ist."""
    reise_dir = Path(reise_dir)
    m = []
    if not reise_dir.is_dir():
        return False, [f"Den Ordner {reise_dir} gibt es nicht."]
    ry = reise_dir / "reise.yaml"
    if not ry.exists():
        m.append("reise.yaml fehlt. Neue Reisen legt „neu.py reise“ an.")
    else:
        try:
            yaml.safe_load(ry.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            z = getattr(e, "problem_mark", None)
            m.append(f"reise.yaml ist nicht lesbar{f' (Zeile {z.line + 1}, Spalte {z.column + 1})' if z else ''}: "
                     f"{getattr(e, 'problem', None) or e}. Oft fehlt ein Doppelpunkt oder die Einrückung stimmt nicht.")
    rj = reise_dir / "reise.json"
    cfg = None
    if not rj.exists():
        m.append("reise.json fehlt: Sie ordnet den Überschriften ihre IDs zu.")
    else:
        try:
            cfg = lies_json(rj)
        except json.JSONDecodeError as e:
            m.append(f"reise.json ist nicht lesbar (Zeile {e.lineno}, Spalte {e.colno}): {e.msg}. "
                     "Oft fehlt ein Komma oder ein Anführungszeichen.")
    if isinstance(cfg, dict):
        dateien = [cfg.get(k) for k in DATEI_SCHLUESSEL] + list(cfg.get("abschnitte") or {}) \
            + list(cfg.get("orte_dossiers") or []) + [(cfg.get("routen") or {}).get(k) for k in ("datei", "karte")]
        for d in dict.fromkeys(x for x in dateien if x):
            if not (reise_dir / d).exists():
                m.append(f"reise.json nennt die Datei {d}, die es nicht gibt. Datei anlegen oder den Eintrag entfernen.")
    if m:
        return False, m
    with tempfile.TemporaryDirectory() as t:
        try:
            bauen.Bauer(reise_dir, Path(t) / reise_dir.name).daten()
        except bauen.BauFehler as e:
            return False, list(e.meldungen)
        except Exception as e:   # unerwartet: trotzdem lesbar melden statt eines Python-Fehlers
            return False, [f"Unerwarteter Fehler beim Probebau ({type(e).__name__}: {e}). Bitte an die Technik geben."]
    return True, []


# ---------- Arten aus Bestandsdaten ableiten (Paket O-2, docs/ontologie.md) ----------
FARBEN_REIHE = ("blau", "gruen", "braun", "tuerkis", "lila", "oliv", "rosa", "schiefer", "grau")


def arten_ableiten(reise_dir, namen=None, summiert=(), definitionen=None, schreiben=True):
    """plan/arten.yaml aus plan/routen.yaml ableiten, ohne eine ID oder einen Wert zu ändern: jeder vorkommende typ einer
    Unterkunft oder Nacht wird eine Art der Grundform aufenthalt, jede art einer Strecke eine Art der Grundform bewegung
    (eine Liste mehrerer Arten: kombiniert), Wahlstellen mit Folge-Optionen bekommen die Art reiseteil. Belegte Merkmale
    werden an der Art definiert (Stufe empfohlen, wenn bei mehr als der Hälfte der Dinge belegt, sonst angeboten); eine
    Stufen-Vorgabe aus routen.yaml merkmale: (Brücke aus Paket O-0) gilt vor der Zählung. Unbelegte Merkmale kommen nicht
    hinein. namen: {art: Anzeigename}; summiert: Arten aus eigener Kraft (Kennzahlen werden summiert); definitionen:
    {merkmal: Definition} als Vorlage für Namen, Typ und Hilfetexte (sonst Name aus dem Schlüssel, Typ text).
    Danach prüft die Organisator:in die Arten im Gespräch. -> Text der Datei."""
    import yaml
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from routen import art_schluessel, AUTO_JE_GRUNDFORM
    namen, definitionen = dict(namen or {}), dict(definitionen or {})
    r = yaml.safe_load((reise_dir / "plan/routen.yaml").read_text(encoding="utf-8")) or {}
    arten = {}      # art -> {grundform, name, dinge: [merkmale-dicts], typ_roh}

    def art(key, grundform, name=None):
        if key not in arten:
            arten[key] = {"grundform": grundform, "name": namen.get(key) or name or key.capitalize(), "dinge": []}
        return arten[key]

    def stufe_vorgabe(k, typ):
        s = (((r.get("merkmale") or {}).get("unterkunft") or {}).get(k) or {}).get("stufe")
        if isinstance(s, dict):
            return s.get(art_schluessel(typ) or "", s.get("*"))
        return s

    for u in (r.get("unterkuenfte") or {}).values():
        a = art(u.get("art") or art_schluessel(u.get("typ")) or "unterkunft", "aufenthalt", u.get("typ"))
        a["dinge"].append(("aufenthalt", u.get("typ"), u.get("merkmale") or {}))
    for t in (r.get("tage") or {}).values():
        n = t.get("nacht")
        if isinstance(n, dict) and (n.get("typ") or n.get("art")) and not n.get("an_bord"):
            art(n.get("art") or art_schluessel(n.get("typ")), "aufenthalt", n.get("typ"))["dinge"].append(("aufenthalt", n.get("typ"), {}))
    for s in (r.get("strecken") or {}).values():
        k = s.get("art", "wandern")
        k = "kombiniert" if isinstance(k, list) else str(k)
        art(k, "bewegung")["dinge"].append(("bewegung", None, s.get("merkmale") or {}))
    wahl = r.get("wahlstellen") or {}
    for vid, w in (wahl.items() if isinstance(wahl, dict) else ((x["id"], x) for x in wahl)):
        opts = w.get("optionen") or []
        b = w.get("bereich")
        if b and b not in arten:
            art(b, "bewegung" if any(o.get("strecken") for o in opts) else "aufenthalt")
        if any(o.get("folge") is not None for o in opts):
            b = b or "reiseteil"
            art(b, "folge")
        if not b:
            for o in opts:
                for uid in o.get("unterkuenfte") or []:
                    u = (r.get("unterkuenfte") or {}).get(uid) or {}
                    b = b or u.get("art") or art_schluessel(u.get("typ"))
                for sid in o.get("strecken") or []:
                    sa = ((r.get("strecken") or {}).get(sid) or {}).get("art", "wandern")
                    b = b or ("kombiniert" if isinstance(sa, list) else str(sa))
        if b in arten:
            for o in opts:
                if o.get("merkmale"):
                    arten[b]["dinge"].append((arten[b]["grundform"], None, o["merkmale"]))
    # definitionen darf auch die alte Grundliste (je Bereich) sein: dann je Art ihr Bereich oder der ihrer Grundform
    gruppiert = definitionen and all(isinstance(v, dict) and all(isinstance(x, dict) for x in v.values()) for v in definitionen.values())
    aus = {}
    for key, a in arten.items():
        g, dinge = a["grundform"], a["dinge"]
        if gruppiert:
            definitionen = (definitionen if "_alle" in definitionen else {"_alle": definitionen})
            alle = definitionen["_alle"]
            definitionen_art = alle.get(key) or alle.get({"aufenthalt": "unterkunft", "bewegung": "strecke", "folge": "route"}[g]) or {}
        else:
            definitionen_art = definitionen
        zaehl = {}
        for _, typ, mk in dinge:
            for k in mk:
                zaehl.setdefault(k, []).append(typ)
        merkmale = {}
        if g in AUTO_JE_GRUNDFORM and (g == "folge" or key in summiert):
            for k in AUTO_JE_GRUNDFORM[g]:
                d = dict(definitionen_art.get(k) or {"name": k.capitalize()})
                merkmale[k] = {"name": d.get("name", k.capitalize()), "auto": k}
        for k, typen in zaehl.items():
            vor = stufe_vorgabe(k, typen[0]) if g == "aufenthalt" else None
            # aus, aber belegt: Wert bleibt (nichts wird gelöscht), die Stufe aus sagt, dass es nicht zählt
            d = {f: v for f, v in (definitionen_art.get(k) or {}).items() if f in ("name", "typ", "werte", "veraenderlich", "hilfe", "frage", "einheit")}
            d.setdefault("name", k.capitalize())
            d["stufe"] = vor or ("empfohlen" if len(typen) * 2 > max(len(dinge), 1) else "angeboten")
            merkmale[k] = d
        # Merkmale, die der Product Owner per Stufe ausdrücklich für diese Art verlangt (O-0-Brücke), auch ohne Wert
        for k, dv in (((r.get("merkmale") or {}).get("unterkunft") or {}).items() if g == "aufenthalt" else []):
            vor = stufe_vorgabe(k, dinge[0][1] if dinge else None)
            if vor and vor != "aus" and k not in merkmale:
                d = {f: v for f, v in (definitionen_art.get(k) or {}).items() if f in ("name", "typ", "werte", "veraenderlich", "hilfe", "frage", "einheit")}
                d.setdefault("name", k.capitalize())
                d["stufe"] = vor
                merkmale[k] = d
        eintrag = {"grundform": g, "name": a["name"]}
        if g == "aufenthalt":
            eintrag["farbe"] = FARBEN_REIHE[len([x for x in aus.values() if x["grundform"] == "aufenthalt"]) % len(FARBEN_REIHE)]
        if key in summiert:
            eintrag["summiert"] = True
        if merkmale:
            eintrag["merkmale"] = merkmale
        aus[key] = eintrag
    from schreiben import arten_text     # dieselbe Form wie beim Schreiben über den Konnektor (O-3)
    text = arten_text(aus, f"Abgeleitet aus plan/routen.yaml am {datetime.date.today().isoformat()} (engine/neu.py arten-ableiten); "
                      "danach im Gespräch geprüft und geschärft.")
    if schreiben:
        (reise_dir / "plan/arten.yaml").write_text(text, encoding="utf-8")
    return text


# ---------- Aufruf ----------
def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="engine/neu.py", description="Neue Reise anlegen, IDs vergeben, vor dem Bau prüfen.")
    sub = ap.add_subparsers(dest="befehl", required=True)
    r = sub.add_parser("reise", help="neue Reise aus der Vorlage anlegen")
    r.add_argument("reisen", type=Path)
    r.add_argument("--titel", required=True)
    r.add_argument("--von", required=True, type=datetime.date.fromisoformat)
    r.add_argument("--bis", required=True, type=datetime.date.fromisoformat)
    r.add_argument("--person", action="append", required=True, help="schluessel=Name:rolle[:reist|nicht]")
    r.add_argument("--wer", required=True, help="Name der Person, die anlegt (organisator)")
    r.add_argument("--ziel")
    r.add_argument("--pfad")
    r.add_argument("--untertitel")
    r.add_argument("--herkunft", default="Gespräch in Claude Code")
    r.add_argument("--ueberblick")
    i = sub.add_parser("id", help="nächste freie ID vergeben")
    i.add_argument("reise", type=Path)
    i.add_argument("art", choices=ARTEN)
    a = sub.add_parser("abschnitt", help="Abschnitt mit neuer W-ID anhängen")
    a.add_argument("reise", type=Path)
    a.add_argument("--titel", required=True)
    a.add_argument("--gruppe", default="wissen", choices=GRUPPEN)
    a.add_argument("--datei", default="inhalt/wissen.md")
    a.add_argument("--text-datei", type=Path)
    p = sub.add_parser("pruefen", help="vor dem Bau prüfen")
    p.add_argument("reise", type=Path)
    g = sub.add_parser("arten-ableiten", help="plan/arten.yaml aus den Bestandsdaten der Reise ableiten (Paket O-2)")
    g.add_argument("reise", type=Path)
    g.add_argument("--name", action="append", default=[], help="art=Anzeigename, z. B. faehre=Fähre")
    g.add_argument("--summiert", default="", help="Arten aus eigener Kraft, Komma-Liste, z. B. wandern,rad")
    g.add_argument("--definitionen", type=Path, help="YAML {merkmal: {name, typ, …}} als Vorlage für Namen und Hilfetexte")
    x = ap.parse_args(argv[1:])
    try:
        if x.befehl == "arten-ableiten":
            import yaml
            defs = yaml.safe_load(x.definitionen.read_text(encoding="utf-8")) if x.definitionen else {}
            print(arten_ableiten(x.reise, dict(n.split("=", 1) for n in x.name), set(filter(None, x.summiert.split(","))), defs))
            return 0
        if x.befehl == "reise":
            personen = dict(person_aus_text(t) for t in x.person)
            d = anlegen(x.reisen, x.titel, x.von, x.bis, personen, x.wer, ziel=x.ziel, pfad=x.pfad,
                        untertitel=x.untertitel, herkunft=x.herkunft, ueberblick=x.ueberblick)
            ok, m = pruefen(d)
            print(f"Angelegt: {d} (Status idee)." + ("" if ok else " Prüfung meldet:\n - " + "\n - ".join(m)))
            return 0 if ok else 1
        if x.befehl == "id":
            print(naechste_id(x.reise, x.art))
            return 0
        if x.befehl == "abschnitt":
            text = x.text_datei.read_text(encoding="utf-8") if x.text_datei else ""
            print(abschnitt(x.reise, x.titel, x.gruppe, x.datei, text))
            return 0
        ok, m = pruefen(x.reise)
        if ok:
            print(f"In Ordnung: {cfg_titel(x.reise)} baut ohne Fehler.")
            return 0
        print(f"Die Reise baut noch nicht. {len(m)} Punkt{'e' if len(m) != 1 else ''} zu beheben:")
        for n, t in enumerate(m, 1):
            print(f" {n}. {t}")
        return 1
    except Fehler as e:
        print(f"Nicht möglich: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
