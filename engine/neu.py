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
from reise import PFAD_MUSTER, ROLLEN, reise_pfad, schluessel_aus_name  # noqa: E402

VORLAGE = Path(__file__).with_name("reisevorlage")
ARTEN = ("W", "F", "O", "U", "E", "T", "V")          # nummerierte IDs; Pläne (P-A) und Aufgaben (AG, live) nicht
GRUPPEN = ("wissen", "praxis", "quelle")
ROLLE_TEXT = {"bestimmer": "bestimmt", "einbringer": "bringt ein", "reisend": "liest mit"}
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
    """„hanna=Hanna:einbringer“ oder „Ben:reisend:nicht“ -> (schluessel, {name, rolle[, reist]})."""
    schluessel, _, rest = text.rpartition("=") if "=" in text else ("", "", text)
    teile = [t.strip() for t in rest.split(":")]
    if len(teile) < 2 or not teile[0]:
        raise Fehler(f"Person „{text}“: bitte als Name:rolle angeben, z. B. Hanna:einbringer.")
    name, rolle = teile[0], teile[1]
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
    bestimmer = [p["name"] for p in personen.values() if p.get("rolle") == "bestimmer"]
    if not bestimmer:
        raise Fehler("Mindestens eine Person braucht die Rolle bestimmer: Sie entscheidet und setzt den Status.")
    if wer not in bestimmer:
        raise Fehler(f"Anlegen darf nur, wer auf der Reise bestimmt. {wer} steht nicht als bestimmer in den Personen.")
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
        "# Status und Einstellungen ändert nur ein Bestimmer, mit Verlaufseintrag.\n\n"
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
    Die Notiz übernimmt das Einarbeiten in eigenen Worten in den Überblick; hier steht nur, woher die Reise kommt."""
    n = (auftrag.get("daten") or {}).get("neue_reise")
    if not n:
        raise Fehler(f"{auftrag.get('id')}: kein Auftrag für eine neue Reise.")
    return anlegen(reisen_dir, n["titel"], datetime.date.fromisoformat(n["von"]), datetime.date.fromisoformat(n["bis"]),
                   n["personen"], n["wer"], ziel=n.get("ziel") or None, pfad=n["pfad"],
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
    r.add_argument("--wer", required=True, help="Name der Person, die anlegt (bestimmer)")
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
    x = ap.parse_args(argv[1:])
    try:
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
