"""Neue Reise anlegen, IDs vergeben, Prüfung vor dem Bau (Paket H, docs/neue-reise.md).

Als Modul ist neu.py Technik des Schreibwegs: schreiben.py legt Reisen aus der Claude-App an (aus_auftrag), vergibt IDs
(naechste_id) und hängt Wissensabschnitte an (abschnitt). Reiseinhalte entstehen nur dort, im AI-Client über den
Konnektor (ADR-0001, Präzisierung 3).

Als Befehl ist neu.py ein Werkzeug des Betreibers für Struktur, nie für Inhalt:

  neu.py reise <reisen-ordner> --titel T --von JJJJ-MM-TT --bis JJJJ-MM-TT --person schluessel=Name:rolle[:nicht] …
         --wer Name [--ziel Ort] [--pfad ordner] [--sprache S] [--untertitel U] [--herkunft H]
                                                  nur die erste Reise einer Instanz, leer im Status „idee“
                                                  (docs/betrieb.md, Neue Instanz einrichten, Schritt 7); alle weiteren
                                                  Reisen und alle Inhalte entstehen in der Claude-App (trip_create)
  neu.py pruefen <reise-ordner>                   Prüfung vor dem Bau mit verständlichen Meldungen
  neu.py arten-ableiten <reise-ordner> …          plan/arten.yaml aus den Bestandsdaten ableiten (docs/ontologie.md, O-2)
  neu.py nachziehen <reise-ordner> [--strecke E-15=kombiniert …]
                                                  Schlüssel einer bestehenden Reise auf den Stand vom 29.10.2026 bringen
                                                  (docs/ontologie.md): typ→art, bereich→art, art→wann an Wahlstellen,
                                                  rolle kosten, Ebenen in reise.json, Eckdaten aus der früheren Vorlage
                                                  (#217), Titel und Kennzahlen der Etappen aus dem Dossier an die Strecken
                                                  (#269), eine Lage je Ort und gleichnamigem Wegpunkt (ADR-0008);
                                                  keine ID, kein Wert ändert sich
  neu.py nachziehen-speicher <reise> <ordner>     dasselbe für eine Reise im Reisespeicher (#348), auf dem Server vom Lauf
                                                  veroeffentlichen.sh: materialisieren, nachziehen, Probebau, ein Vorgang;
                                                  Exit 0 umgestellt oder nichts umzustellen, 2 Bau rot, 1 nochmal versuchen

IDs werden nie neu vergeben: ids.yaml hält je Art die höchste je vergebene Nummer fest. Die nächste ID liegt über
dieser Marke und über jeder Nummer, die irgendwo in der Reise steht (auch im Verlauf von Verworfenem).
"""
import copy
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
import texte  # noqa: E402
from reise import (PFAD_MUSTER, ROLLEN, reise_pfad, rolle_neu, schluessel_aus_name, sprache_pruefen, sprache_von,  # noqa: E402
                   zeitraum_text)

VORLAGEN = Path(__file__).with_name("reisevorlage")   # je Sprache ein Ordner (de, en …); fehlt er, gilt der englische (texte.VORGABE, ADR-0006, Punkt 9)


def vorlage_ordner(sprache):
    return VORLAGEN / sprache if (VORLAGEN / sprache).is_dir() else VORLAGEN / texte.VORGABE
ARTEN = ("W", "F", "O", "U", "A", "E", "T", "V", "B", "G")     # nummerierte IDs (A = Aufenthalt ohne Nacht, B = Buchung, G = Gegenstand der Packliste); Pläne (P-A) und Aufgaben (AG, live) nicht
GRUPPEN = ("wissen", "praxis", "quelle")
BAUSTEINE_IDEE = ["rueckmeldungen", "fragen", "aufgaben", "wuensche"]


class Fehler(Exception):
    """Eingabe passt nicht; der Text ist für Menschen geschrieben."""


# ---------- Hilfen ----------
def datum_text(d, sprache=None):
    return texte.datum(d, sprache or texte.VORGABE_REISE)


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
        raise Fehler(texte.satz("pruefung.neu.1", text=text))
    name, rolle = teile[0], rolle_neu(teile[1])
    if rolle not in ROLLEN:
        raise Fehler(texte.satz("pruefung.neu.2", name=name, rolle=rolle, w1=', '.join(ROLLEN)))
    p = {"name": name, "rolle": rolle}
    if len(teile) > 2:
        if teile[2] not in ("reist", "nicht"):
            raise Fehler(texte.satz("pruefung.neu.3", name=name))
        p["reist"] = teile[2] == "reist"
    return (schluessel.strip() or schluessel_aus_name(name)), p


# ---------- IDs ----------
def _nummern(reise_dir, art):
    muster = re.compile(rf"(?<![A-Za-z0-9]){art}-(\d+)(?![\d-])")   # A-01, nicht A-20261028-… (alte Aufträge)
    n = 0
    for f in reise_dir.rglob("*"):
        if f.is_file() and f.suffix in (".md", ".yaml", ".yml", ".json") and "medien" not in f.relative_to(reise_dir).parts:
            for m in muster.finditer(f.read_text(encoding="utf-8", errors="replace")):
                n = max(n, int(m.group(1)))
    return n


def naechste_id(reise_dir, art):
    """Nächste freie ID einer Art; die Marke in ids.yaml steigt sofort, damit keine ID zweimal vergeben wird."""
    if art not in ARTEN:
        raise Fehler(texte.satz("pruefung.neu.4", art=art, w1=', '.join(ARTEN)))
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
    (Path(reise_dir) / "ids.yaml").write_text(texte.t(sprache_von(reise_dir), "inhalt.neu.ids_kopf") + "\n"
                                              + yaml.safe_dump(marken, sort_keys=False), encoding="utf-8")


# ---------- Reise anlegen ----------
def anlegen(reisen_dir, titel, von, bis, personen, wer, ziel=None, pfad=None, untertitel=None,
            herkunft=None, ueberblick=None, heute=None, sprache=None):
    """Legt reisen_dir/<pfad> aus der Vorlage an -> Ordner. personen: {schluessel: {name, rolle[, reist, notiz]}}."""
    heute = heute or datetime.date.today()
    titel = (titel or "").strip()
    if not titel:
        raise Fehler(texte.satz("pruefung.neu.5"))
    if not isinstance(von, datetime.date) or not isinstance(bis, datetime.date):
        raise Fehler(texte.satz("pruefung.neu.6"))
    if bis < von:
        raise Fehler(texte.satz("pruefung.neu.7", w1=datum_text(bis), w2=datum_text(von)))
    if not personen:
        raise Fehler(texte.satz("pruefung.neu.8"))
    organisator = [p["name"] for p in personen.values() if p.get("rolle") == "organisator"]
    if not organisator:
        raise Fehler(texte.satz("pruefung.neu.9"))
    if wer not in organisator:
        raise Fehler(texte.satz("pruefung.neu.10", wer=wer))
    sprache, fehler = sprache_pruefen(sprache)
    if fehler:
        raise Fehler(fehler)
    pfad = pfad or reise_pfad(titel, von.year)
    if not PFAD_MUSTER.match(pfad):
        raise Fehler(texte.satz("pruefung.neu.11", pfad=pfad))
    ziel_dir = Path(reisen_dir) / pfad
    if ziel_dir.exists():
        raise Fehler(texte.satz("pruefung.neu.12", pfad=pfad))

    # Alles, was die Software in Dateien der Reise schreibt, folgt der Sprache der Reise (ADR-0006, Punkt 5)
    # Eckdaten (Zeitraum, Ziel, Personen, Status) stehen nur in reise.yaml; Untertitel und Eckdaten-Abschnitt baut der Generator
    # daraus, damit sie nach trip_update, trip_status_set oder person_invite nicht veralten (#217)
    herkunft = herkunft or texte.t(sprache, "inhalt.neu.herkunft_gespraech")
    werte = {"titel": titel, "ueberblick": ueberblick or texte.t(sprache, "inhalt.neu.ueberblick_leer")}
    vorlage = vorlage_ordner(sprache)
    for f in sorted(vorlage.rglob("*")):
        if f.is_file():
            z = ziel_dir / f.relative_to(vorlage)
            z.parent.mkdir(parents=True, exist_ok=True)
            z.write_text(string.Template(f.read_text(encoding="utf-8")).substitute(werte), encoding="utf-8")
    (ziel_dir / "medien").mkdir(exist_ok=True)

    reise = {
        "titel": titel,
        **({"untertitel": untertitel.strip()} if (untertitel or "").strip() else {}),
        **({"ziel": ziel.strip()} if (ziel or "").strip() else {}),
        "pfad": pfad,
        "sprache": sprache,
        "zeitraum": {"von": von, "bis": bis},
        "status": {"wert": "idee", "verlauf": [{"datum": heute, "wert": "idee", "wer": wer,
                                                 "grund": texte.t(sprache, "inhalt.neu.reise_angelegt", herkunft=herkunft)}]},
        "personen": personen,
        "bausteine": BAUSTEINE_IDEE,
        "darstellung": {"gruppen": {g: texte.wort(sprache, f"inhalt.gruppe.{g}") for g in GRUPPEN}},
    }
    (ziel_dir / "reise.yaml").write_text(
        texte.t(sprache, "inhalt.neu.reise_yaml_kopf") + "\n\n"
        + yaml.safe_dump(reise, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")
    schreib_json(ziel_dir / "reise.json", {
        "plan": "plan/plan.md",
        "eckdaten": "W-01",
        "fragen": "offene-fragen.md",
        "abschnitte": {
            "plan/plan.md": {texte.wort(sprache, "inhalt.ebene.eckdaten"): ["W-01", "plan"]},
            "inhalt/wissen.md": {texte.wort(sprache, "inhalt.abschnitt.ueberblick"): ["W-02", "wissen"],
                                 texte.wort(sprache, "inhalt.ebene.quellen"): ["W-03", "quelle"]},
        },
    })
    schreib_marken(ziel_dir, {"W": 3, "F": 1})   # vergeben von der Vorlage: W-01 bis W-03, F-01
    return ziel_dir


def aus_auftrag(reisen_dir, auftrag, heute=None):
    """Reise aus einem Auftrag „reise_anlegen“ der Claude-App (daten.neue_reise, vom Konnektor geprüft) -> Ordner.
    Die Notiz (in der App schon in eigenen Worten mit Herkunft) wird der Überblick, mit Name und Datum davor."""
    n = (auftrag.get("daten") or {}).get("neue_reise")
    if not n:
        raise Fehler(texte.satz("pruefung.neu.13", w1=auftrag.get('id')))
    sprache = n.get("sprache") or texte.VORGABE_REISE
    datum = datum_text(datetime.date.fromisoformat(str(auftrag.get("erstellt", ""))[:10] or (heute or datetime.date.today()).isoformat()), sprache)
    ueberblick = texte.t(sprache, "inhalt.neu.notiz_von", wer=n["wer"], datum=datum, notiz=n["notiz"]) if n.get("notiz") else None
    return anlegen(reisen_dir, n["titel"], datetime.date.fromisoformat(n["von"]), datetime.date.fromisoformat(n["bis"]),
                   n["personen"], n["wer"], ziel=n.get("ziel") or None, pfad=n["pfad"], ueberblick=ueberblick,
                   herkunft=texte.t(n.get("sprache") or texte.VORGABE_REISE, "inhalt.neu.herkunft_auftrag", id=auftrag["id"]), heute=heute, sprache=n.get("sprache"))


# ---------- Abschnitt mit neuer ID ----------
def abschnitt(reise_dir, titel, gruppe="wissen", datei="inhalt/wissen.md", text=""):
    """Hängt „## titel“ an datei an und ordnet ihm eine neue W-ID zu -> ID."""
    reise_dir = Path(reise_dir)
    titel = (titel or "").strip()
    if not titel or "\n" in titel:
        raise Fehler(texte.satz("pruefung.neu.14"))
    if gruppe not in GRUPPEN:
        raise Fehler(texte.satz("pruefung.neu.15", gruppe=gruppe, w1=', '.join(GRUPPEN)))
    cfg = lies_json(reise_dir / "reise.json")
    zuordnung = cfg.setdefault("abschnitte", {}).setdefault(datei, {})
    if titel in zuordnung:
        raise Fehler(texte.satz("pruefung.neu.16", datei=datei, titel=titel, w1=zuordnung[titel][0]))
    f = reise_dir / datei
    if f.exists() and re.search(rf"^## {re.escape(titel)}\s*$", f.read_text(encoding="utf-8"), re.M):
        raise Fehler(texte.satz("pruefung.neu.17", datei=datei, titel=titel))
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
        return False, [texte.satz("pruefung.neu_pruefen.1", reise_dir=reise_dir)]
    ry = reise_dir / "reise.yaml"
    if not ry.exists():
        m.append(texte.satz("pruefung.neu_pruefen.2"))
    else:
        try:
            yaml.safe_load(ry.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            z = getattr(e, "problem_mark", None)
            problem = getattr(e, "problem", None) or e
            m.append(texte.satz("pruefung.neu_pruefen.yaml_ort", zeile=z.line + 1, spalte=z.column + 1, problem=problem) if z
                     else texte.satz("pruefung.neu_pruefen.yaml", problem=problem))
    rj = reise_dir / "reise.json"
    cfg = None
    if not rj.exists():
        m.append(texte.satz("pruefung.neu_pruefen.3"))
    else:
        try:
            cfg = lies_json(rj)
        except json.JSONDecodeError as e:
            m.append(texte.satz("pruefung.neu_pruefen.4", w1=e.lineno, w2=e.colno, w3=e.msg))
    if isinstance(cfg, dict):
        dateien = [cfg.get(k) for k in DATEI_SCHLUESSEL] + list(cfg.get("abschnitte") or {}) \
            + list(cfg.get("orte_dossiers") or []) + [(cfg.get("routen") or {}).get(k) for k in ("datei", "karte")]
        for d in dict.fromkeys(x for x in dateien if x):
            if not (reise_dir / d).exists():
                m.append(texte.satz("pruefung.neu_pruefen.5", d=d))
    if m:
        return False, m
    with tempfile.TemporaryDirectory() as t:
        try:
            bauen.Bauer(reise_dir, Path(t) / reise_dir.name).daten()
        except bauen.BauFehler as e:
            return False, list(e.meldungen)
        except Exception as e:   # unerwartet: trotzdem lesbar melden statt eines Python-Fehlers
            return False, [texte.satz("pruefung.neu_pruefen.6", w1=type(e).__name__, e=e)]
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
        k = s.get("art")
        if not k:
            continue   # ohne Art: der Bau meldet es; die Software kennt keine Vorgabe (ADR-0001)
        k = "kombiniert" if isinstance(k, list) else str(k)
        art(k, "bewegung")["dinge"].append(("bewegung", None, s.get("merkmale") or {}))
    wahl = r.get("wahlstellen") or {}
    for vid, w in (wahl.items() if isinstance(wahl, dict) else ((x["id"], x) for x in wahl)):
        opts = w.get("optionen") or []
        b = w.get("bereich") or (w.get("art") if w.get("art") not in ("planung", "unterwegs") else None)
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
                    sa = ((r.get("strecken") or {}).get(sid) or {}).get("art")
                    b = b or (sa and ("kombiniert" if isinstance(sa, list) else str(sa)))
                # Ort als Möglichkeit (#353): seine Art nur, wenn sie auch sonst abgeleitet wird (Orte bekommen hier keine eigene Art)
                for oid in o.get("orte") or []:
                    oa = ((r.get("orte") or {}).get(oid) or {}).get("art")
                    b = b or (oa if oa in arten else None)
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
    sp = sprache_von(reise_dir)   # Kopfkommentar und Herkunft in der Sprache der Reise
    text = arten_text(aus, texte.t(sp, "inhalt.schreiben.abgeleitet", datum=datetime.date.today().isoformat()), sp)
    if schreiben:
        (reise_dir / "plan/arten.yaml").write_text(text, encoding="utf-8")
    return text


# ---------- Schlüssel einer Reise nachziehen (Abgleich 29.10.2026, docs/abgleich-2026-10-29.md) ----------
# Feld eines früheren Kartenpunkts -> Rolle des Merkmals, das es ersetzt (routen.ROLLEN, routen.ROLLEN_MERKMAL)
PUNKT_ROLLEN = {"nr": "nummer", "auch": "alias", "art": "sorte", "osm": "osm", "trinkbar": "trinkbar", "offen": "oeffnung", "id": "bezug"}


def kartenpunkte_umstellen(reise_dir, roh, schreiben, meldungen):
    """ADR-0007, Schritt d: Kartenpunkte (plan/punkte.yaml, Punkte in der Datei reise.json wissen_punkte) werden Aufenthalte (A-…) mit
    Art, ID, Herkunft, Koordinaten und an: (der Strecke, an der sie liegen, oder dem Block des Wissens); die Kategorien
    (plan/kategorien.yaml) gehen in den Arten (arten.yaml) auf, mit den Rollen der Merkmale für Nummer, weitere Namen, Sorte, OSM-Bezug und
    Trinkbarkeit. Neue IDs aus ids.yaml; die alten Dateien entfallen. Probelauf (schreiben=False): nur melden."""
    import schreiben as sb
    from routen import SYMBOLE_ARTEN
    reise_dir = Path(reise_dir)
    plan = reise_dir / "plan"
    kat_datei, punkte_datei = plan / "kategorien.yaml", plan / "punkte.yaml"
    cfg_datei = reise_dir / "reise.json"
    cfg = json.loads(cfg_datei.read_text(encoding="utf-8")) if cfg_datei.exists() else {}
    wissen_rel = cfg.get("wissen_punkte")
    wissen_datei = reise_dir / wissen_rel if wissen_rel else None
    lies = lambda p: (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p and p.exists() else {}
    kategorien = (lies(kat_datei).get("kategorien") or {}) if kat_datei.exists() else {}
    punkte, wissen = lies(punkte_datei), lies(wissen_datei)
    je_strecke = punkte.get("strecken") or {}
    je_block = wissen.get("bloecke") or {}
    # Was nicht zum Ding wird (ohne_karte mit Begründung, ohne Lage mit Suchbegriffen, unbekannte Kategorie), bleibt mit allen Feldern in der
    # Datei: nichts geht verloren, der Bau liest es wie vorher, ein zweiter Lauf findet nichts mehr zu tun
    verschiebbar = lambda p: isinstance(p, dict) and not p.get("ohne_karte") and p.get("lage") is not None and p.get("kat") in kategorien
    anzahl = sum(1 for v in list(je_strecke.values()) + list(je_block.values()) for p in v or [] if verschiebbar(p))
    if not (kategorien or anzahl):
        return
    meldungen.append(f"{anzahl} map points → things (A-…), {len(kategorien)} categories → kinds (arten.yaml)")
    # gebiet, suche und von_hand dienten dem Suchwerkzeug; das Ergebnis steht in lage und quelle des Dings (sichtbar machen statt still verwerfen)
    suchfelder = sum(1 for v in list(je_strecke.values()) + list(je_block.values()) for p in v or []
                     if verschiebbar(p) and any(p.get(f) for f in ("gebiet", "suche", "von_hand")))
    if suchfelder:
        meldungen.append(f"{suchfelder} moved points had gebiet, suche or von_hand: not carried over, the result stands in lage and quelle")
    if not schreiben:
        return
    arten = sb.arten_laden(reise_dir)
    vorher = copy.deepcopy(arten)
    art_von = {}   # Kategorie -> Schlüssel der Art
    gruppe_von = {}
    for k, d in kategorien.items():
        d = d if isinstance(d, dict) else {}
        art = k if (k not in arten or (arten[k] or {}).get("grundform") == "aufenthalt") else f"punkt_{k}"
        a = arten.setdefault(art, {"grundform": "aufenthalt"})
        art_von[k], gruppe_von[k] = art, d.get("gruppe") or "punkt"
        for feld, wert in (("name", d.get("name")), ("einzahl", d.get("einzahl")), ("farbe", d.get("farbe")),
                           ("symbol", d.get("symbol") if d.get("symbol") in SYMBOLE_ARTEN else None), ("gruppe", d.get("gruppe")),
                           ("nummeriert", True if d.get("nummeriert") else None), ("sorten", d.get("arten") or None)):
            if wert not in (None, "", {}) and feld not in a:
                a[feld] = wert
        a.setdefault("buchbar", False)
    stand = punkte.get("stand") or wissen.get("stand")
    ida = {}   # Art -> {feld: Schlüssel des Merkmals}, damit jede Art die Rollen nur einmal bekommt

    def merkmal_schluessel(art, feld):
        return sb.art_rolle_sichern(arten[art], PUNKT_ROLLEN[feld])

    ids = {}
    aufenthalte = roh.setdefault("aufenthalte", type(roh)())

    def anlegen(an, p, wo):
        kat = p.get("kat")
        if p.get("ohne_karte"):
            meldungen.append(f"{wo} {p.get('name')}: marked ohne_karte, not moved (stays in the file)")
            return False
        if p.get("lage") is None:
            meldungen.append(f"{wo} {p.get('name')}: no lage yet, not moved (stays in the file)")
            return False
        if kat not in art_von:   # Kategorie fehlt: der Punkt bleibt in der Datei, nichts geht verloren
            meldungen.append(f"OPEN {wo} {p.get('name')}: category {kat} is not defined; the point was not moved (stays in the file)")
            return False
        art = art_von[kat]
        quelle = p.get("quelle") or sb.lesbar(reise_dir, [sb.S("schreiben.quelle_bestand")])
        g = p.get("geprueft", stand)
        # Ohne Namen (OSM-Treffer wie Trinkwasser) lehnt der Bau den Aufenthalt ab: der Name kommt aus der Art, wie bei map_points_fetch (#295)
        name = p.get("name") or arten[art].get("einzahl") or arten[art].get("name") or kat
        d = {"name": name, "art": art, "an": an, "quelle": quelle}
        if p.get("hinweis"):
            d["hinweis"] = p["hinweis"]
        aid = sb.neue_id(reise_dir, "A")
        knoten = sb.block_map(d)
        if p.get("lage"):
            sb.lage_merkmal_schreiben(knoten, "koordinaten", [float(x) for x in p["lage"]], quelle, g if isinstance(g, (datetime.date, type(None))) else
                                      datetime.date.fromisoformat(str(g)))
        for feld in ("nr", "auch", "art", "osm", "trinkbar", "offen", "id"):
            wert = p.get(feld)
            if feld == "art" and wert is None:
                continue
            if wert in (None, ""):
                continue
            schl = merkmal_schluessel(art, feld)
            wert = "; ".join(wert) if isinstance(wert, list) else wert
            mk = knoten.get("merkmale")
            if mk is None:
                mk = knoten["merkmale"] = sb.merkmale_knoten({})
            mk[schl] = sb.fliess_map({"wert": wert, "quelle": quelle})
        aufenthalte[aid] = knoten   # der Punkt einer Unterkunft trägt deren Kennung (Rolle bezug) und liefert ihr die Lage wie bisher
        return True

    bleibt_strecken, bleibt_bloecke = {}, {}
    for sid, liste in je_strecke.items():
        for p in liste or []:
            # Eine Strecke, die es in plan/routen.yaml nicht gibt, kann nichts tragen (an: würde ins Leere zeigen und den Bau brechen, #357):
            # der Punkt bleibt in der Datei, wie vorher gelesen, und die Umstellung scheitert nicht
            if sid not in (roh.get("strecken") or {}):
                if verschiebbar(p):
                    meldungen.append(texte.t(sprache_von(reise_dir), "pruefung.neu.nachziehen.punkt_ohne_strecke", sid=sid, name=p.get("name") or "?"))
                bleibt_strecken.setdefault(sid, []).append(dict(p, kat=art_von.get(p.get("kat"), p.get("kat"))))
                continue
            if not anlegen(sid, p, sid):
                bleibt_strecken.setdefault(sid, []).append(dict(p, kat=art_von.get(p.get("kat"), p.get("kat"))))
    for bid, liste in je_block.items():
        for p in liste or []:
            if not anlegen(bid, p, bid):
                bleibt_bloecke.setdefault(bid, []).append(dict(p, kat=art_von.get(p.get("kat"), p.get("kat"))))
    # Rollen nur, wo sie gebraucht werden; nummeriert braucht die Rolle nummer
    neue_arten = {a: d for a, d in arten.items() if a not in vorher}
    geaendert = [a for a in vorher if vorher[a] != arten[a]]
    arten_datei = plan / "arten.yaml"
    if arten_datei.exists() and not geaendert:   # nur neue Arten: anhängen, damit die Kommentare der Datei bleiben
        text = arten_datei.read_text(encoding="utf-8")
        neu_text = yaml.safe_dump(neue_arten, sort_keys=False, allow_unicode=True, width=120)
        arten_datei.write_text(text.rstrip("\n") + "\n  # map points (formerly plan/kategorien.yaml, ADR-0007): kinds with gruppe\n"
                               + "".join("  " + z + "\n" for z in neu_text.splitlines()), encoding="utf-8")
    else:
        sb.arten_speichern(reise_dir, arten, {"name": "Betrieb (neu.py nachziehen)"})
    kat_datei.unlink(missing_ok=True)
    if bleibt_strecken:
        kopf = "".join(z for z in punkte_datei.read_text(encoding="utf-8").splitlines(keepends=True) if z.startswith("#"))
        punkte_datei.write_text(kopf + yaml.safe_dump({k: v for k, v in {"stand": punkte.get("stand"), "strecken": bleibt_strecken}.items() if v},
                                                      sort_keys=False, allow_unicode=True, width=10000), encoding="utf-8")
    else:
        punkte_datei.unlink(missing_ok=True)
    if wissen_datei and wissen_datei.exists():
        rest = {k: v for k, v in wissen.items() if k != "bloecke"}
        if bleibt_bloecke:
            rest["bloecke"] = bleibt_bloecke
        if set(rest) - {"stand"}:
            kopf = "".join(z for z in wissen_datei.read_text(encoding="utf-8").splitlines(keepends=True) if z.startswith("#"))
            wissen_datei.write_text(kopf + yaml.safe_dump(rest, sort_keys=False, allow_unicode=True), encoding="utf-8")
        else:
            wissen_datei.unlink()
            cfg.pop("wissen_punkte", None)
            cfg_datei.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------- Etappe als Strecke einer Art (#269) ----------
# Bis #269 legte das Etappen-Dossier über die Überschrift „Etappe N: Name“ Titel und Kennung fest, die Kennzahlen kamen aus seiner
# Eckdaten-Tabelle (Namen in reise.json etappen_kennzahlen). Jetzt stehen Titel und Kennzahlen an der Strecke in routen.yaml, die
# Überschrift trägt die Kennung („## E-03 Name“). Nur hier, beim Umstellen, werden Namen der Reise einmal Kennungen zugeordnet.
def alte_etappen_ueberschrift(cfg):
    """Die frühere Regel der Überschrift („Etappe 3: Name“, englisch „Stage 3: Name“; reise.json etappen_muster)."""
    return re.compile(cfg.get("etappen_muster") or
                      r"^(?:" + texte.inhaltsmuster("inhalt.etappe") + r")\s+(\d+[A-Za-z]?)\s*:\s*(.+)$")


def alte_etappen_id(nummer):
    return "E-" + (nummer.zfill(3) if nummer[-1].isalpha() else nummer.zfill(2))


def kennung_der_kennzahl(name):
    """Name einer Kennzahl („Gehzeit“, „Aufstieg (Hm)“, „Länge (km)“, in jeder Sprache des Katalogs) -> Kennung (routen.KENNZAHLEN).
    Nur der ganze Name zählt, eine Einheit in Klammern darf folgen; ein Anfang reicht nicht: „Km-Stand“, „Dauer der Pause“ oder
    „Aufstiegshilfe“ bleiben eigene Namen der Reise, wie jeder andere Name."""
    n = re.sub(r"\s*\([^)]*\)\s*$", "", str(name)).strip().lower()
    for kennung, schluessel, roh in (("gehzeit", ("gehzeit", "dauer"), ()), ("aufstieg", ("aufstieg",), ()),
                                     ("abstieg", ("abstieg",), ()), ("laenge", ("laenge",), ("km",))):
        if n == kennung or n in roh or n in {w.lower() for s in schluessel for w in texte.inhaltswoerter("inhalt.kennzahl." + s)}:
            return kennung
    return name


def kennzahl_wert(text):
    """Zahlen bleiben Zahlen („485“ -> 485, „10,7“ -> 10.7); jede andere Schreibweise („ca. 3:40 h“, „8,1 km“) bleibt Text."""
    t = str(text).strip()
    if re.fullmatch(r"\d+", t):
        return int(t)
    if re.fullmatch(r"\d+[.,]\d+", t):
        return float(t.replace(",", "."))
    return t


def gleicher_wert(a, b):
    """Derselbe Wert in Dossier und Strecke? „485“ und 485, „10,7“ und 10.7 sind gleich; Text muss gleich lauten."""
    x, y = kennzahl_wert(a), kennzahl_wert(b)
    return float(x) == float(y) if all(isinstance(v, (int, float)) for v in (x, y)) else str(x) == str(y)


def kennzahlen_kennungen(roh, sprache, meldungen):
    """#269: Kennzahlen, die eine Strecke in routen.yaml schon unter Namen trug („Gehzeit“, „Länge (km)“), bekommen ihre Kennung;
    eigene Namen der Reise bleiben. gehzeit steht in Anführungszeichen (ohne liest YAML „3:30“ als Zahl). Ein zweiter Lauf findet nichts."""
    from ruamel.yaml.scalarstring import DoubleQuotedScalarString
    for sid, st in ((roh or {}).get("strecken") or {}).items():
        km = st.get("kennzahlen") if isinstance(st, dict) else None
        if not hasattr(km, "insert"):
            continue
        for k in list(km.keys()):
            neu = kennung_der_kennzahl(str(k))
            if neu != k and neu in km:   # zwei Werte für eine Kennzahl: nichts umstellen, offen melden
                meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.kennzahl_kollision", sid=sid, alt=k, neu=neu, w1=km[k], w2=km[neu]))
            elif neu != k:
                pos, v = list(km.keys()).index(k), km.pop(k)
                km.insert(pos, neu, v)
                meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.kennzahl_kennung", sid=sid, alt=k, neu=neu))
        g = km.get("gehzeit")
        if isinstance(g, str) and not isinstance(g, DoubleQuotedScalarString):
            km["gehzeit"] = DoubleQuotedScalarString(g)


def eckdaten_zeilen(zeilen, start, ende):
    """Ein Parser für Lesen und Entfernen (F102): Eckdaten-Unterabschnitt im Abschnitt zeilen[start:ende] ->
    (Zeilen von Überschrift bis Unterabschnittsende, Tabellenzeilen, [(Zeile, Name ohne Sternchen, Wert)]); ohne Eckdaten None."""
    kopf = next((j for j in range(start, ende) if zeilen[j].startswith("### ") and bauen.slug(zeilen[j][4:]) == "eckdaten"), None)
    if kopf is None:
        return None
    schluss = next((j for j in range(kopf + 1, ende) if zeilen[j].startswith("### ")), ende)
    tabelle = [j for j in range(kopf + 1, schluss) if bauen.ist_tabellenzeile(zeilen[j])]
    daten = [(j, c[0].strip("* "), c[1].strip() if len(c) > 1 else "") for j in tabelle[2:] for c in [bauen.zellen(zeilen[j])]]
    return range(kopf, schluss), tabelle, daten


def eckdaten_raus(zeilen, eck, raus):
    """Zu entfernende Zeilen: die übertragenen; bleibt keine Datenzeile, auch Kopf und Trennlinie, und steht dann nichts mehr im
    Unterabschnitt, auch die Überschrift „Eckdaten“ (F107)."""
    bereich, tabelle, daten = eck
    if not daten or not raus >= {j for j, _, _ in daten}:
        return raus
    raus = raus | set(tabelle[:2])
    return raus | set(bereich) if all(j in raus or not zeilen[j].strip() for j in bereich[1:]) else raus


STELLE_METER = 100   # gleichnamige Wegpunkte so nah beieinander sind dieselbe Stelle (Etappenende und -anfang im selben Dorf: real bis 37 m)


def name_gleich(s):
    """Name für den genauen Vergleich: Unicode-Form NFC, Leerraum am Rand weg."""
    import unicodedata
    return unicodedata.normalize("NFC", str(s or "")).strip()


def name_aehnlich(s):
    """Name für den Vergleich „nur ähnlich“: ohne Akzente, Groß- und Kleinschreibung und Satzzeichen."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def abstand_m(a, b):
    """Abstand zweier Punkte [Breite, Länge] in Metern (Haversine)."""
    import math
    la1, lo1, la2, lo2 = (math.radians(float(x)) for x in (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def orte_lage_zusammenfuehren(reise_dir, roh, schreiben, meldungen):
    """ADR-0008, Schritt c (#335): eine Lage je Stelle. Ein Ort und die gleichnamigen Wegpunkte (Aufenthalte an einer Strecke mit
    eigenen Koordinaten) werden zusammengeführt: Der Ort übernimmt Koordinaten und Herkunft des ersten Wegpunkts, wenn er keine eigenen
    hat; jeder Wegpunkt verliert seine Koordinaten und verweist mit dem Merkmal der Rolle bezug auf den Ort (fehlt es der Art, legt
    arten.yaml es an). Ein Wegpunkt, der schon die Lage einer Unterkunft an diesem Ort ist, bleibt, wie er ist: der Ort liegt über
    die Unterkunft dort. Gemeldet statt geraten wird: Wegpunkte mehr als STELLE_METER vom Ort oder voneinander, ein Wegpunkt, der auf
    etwas anderes verweist, ein Name, der nur ähnlich ist, und ein Ort mit Unterorten (Region, kein Punkt). Orte außerhalb bleiben.
    IDs bleiben, nichts wird gelöscht."""
    import schreiben as sb
    orte, auf, strecken = (roh.get(g) or {} for g in ("orte", "aufenthalte", "strecken"))
    if not orte or not auf:
        return
    sprache = sprache_von(reise_dir)
    arten = sb.arten_laden(reise_dir)
    arten_neu = False
    unterorte = {o.get("an") for o in orte.values() if isinstance(o, dict)}
    unterkuenfte = {k: v for k, v in (roh.get("unterkuenfte") or {}).items() if isinstance(v, dict)}

    def koordinaten(d):
        for v in (d.get("merkmale") or {}).values():
            if isinstance(v, dict) and v.get("typ") == "koordinaten" and not v.get("rolle"):
                w = v.get("wert")
                return (v, [float(w[0]), float(w[1])]) if isinstance(w, (list, tuple)) and len(w) == 2 else (None, None)
        return None, None

    def bezug_schluessel(art):
        mk = (arten.get(art) or {}).get("merkmale") or {}
        return next((k for k, d in mk.items() if isinstance(d, dict) and d.get("rolle") == "bezug"), None)

    def bezug(a):
        k = bezug_schluessel(a.get("art"))
        v = (a.get("merkmale") or {}).get(k) if k else None
        return str(v.get("wert") if isinstance(v, dict) else v) if v is not None else None

    for oid, o in orte.items():
        if not isinstance(o, dict) or o.get("ausserhalb") or not name_gleich(o.get("name")):
            continue
        name = name_gleich(o["name"])
        wegpunkte = [(aid, a) for aid, a in auf.items() if isinstance(a, dict) and a.get("an") in strecken and koordinaten(a)[1]]
        for aid, a in wegpunkte:
            if name_gleich(a.get("name")) != name and name_aehnlich(a.get("name")) == name_aehnlich(name):
                meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.ort_aehnlich", oid=oid, name=name, aid=aid, wp=a.get("name")))
        paare = [(aid, a) for aid, a in wegpunkte if name_gleich(a.get("name")) == name]
        if not paare:
            continue
        if oid in unterorte:
            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.ort_region", oid=oid, name=name, ids=", ".join(i for i, _ in paare)))
            continue
        # verweist der Wegpunkt auf eine Unterkunft an diesem Ort, ist er deren Lage und der Ort liegt schon über sie dort (ort_lagen)
        fremd = [(aid, b) for aid, a in paare if (b := bezug(a)) and b != oid and (unterkuenfte.get(b) or {}).get("ort") != oid]
        for aid, b in fremd:
            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.ort_fremd", oid=oid, name=name, aid=aid, bezug=b))
        paare = [(aid, a) for aid, a in paare if not bezug(a)]
        if not paare:
            continue
        eigen_v, eigen = koordinaten(o)
        bezugspunkt = eigen or koordinaten(paare[0][1])[1]
        weit = max(abstand_m(bezugspunkt, koordinaten(a)[1]) for _, a in paare)
        if weit > STELLE_METER:
            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.ort_weit", oid=oid, name=name, ids=", ".join(i for i, _ in paare),
                                     m=round(weit), grenze=STELLE_METER))
            continue
        if not eigen:
            v, w = koordinaten(paare[0][1])
            if schreiben:
                if hasattr(o, "fa") and o.fa.flow_style():
                    o.fa.set_block_style()   # ein langer Fließ-Eintrag wird lesbar
                sb.lage_merkmal_schreiben(o, "koordinaten", w, v.get("quelle") or paare[0][1].get("quelle"), v.get("geprueft"), v.get("notiz"))
            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.ort_lage", oid=oid, name=name, aid=paare[0][0]))
        for aid, a in paare:
            if not schreiben:
                continue
            k = bezug_schluessel(a.get("art"))
            if k is None:   # die Art kennt noch keinen Bezug: Merkmal „Ort“ mit Rolle bezug (wie station in der Beispielreise)
                art_def = arten.setdefault(a.get("art"), {"grundform": "aufenthalt"})
                art_def.setdefault("merkmale", {})["station"] = {"name": texte.t(sprache, "inhalt.rolle.bezug_ort"), "typ": "text",
                                                                 "rolle": "bezug", "stufe": "angeboten"}
                k, arten_neu = "station", True
            v, _ = koordinaten(a)
            quelle = v.get("quelle") or a.get("quelle")
            sb.lage_merkmal_entfernen(a, "koordinaten")
            mk = a.get("merkmale")
            if mk is None:
                mk = a["merkmale"] = sb.merkmale_knoten({})
            mk[k] = sb.fliess_map({"wert": oid, "quelle": quelle})
        meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.ort_bezug", oid=oid, name=name, ids=", ".join(i for i, _ in paare)))
    if arten_neu:
        sb.arten_speichern(reise_dir, arten, {"name": "Betrieb (neu.py nachziehen)"})


def etappen_nachziehen(reise_dir, roh, schreiben, meldungen):
    """#269: Titel und fehlende Kennzahlen der Etappen aus dem Dossier an die Strecken in routen.yaml (vorhandene bleiben), die
    Überschriften „Etappe N: Name“ in Etappen- und Unterkünfte-Dossier werden „E-0N Name“, reise.json verliert etappen_kennzahlen und
    etappen_muster. Nie Daten verlieren: eine Eckdaten-Zeile entfällt nur, wenn ihr Wert nachgelesen an der Strecke steht. Bei jeder
    Unsicherheit (keine Strecke, doppelte Nummer, zwei Namen einer Kennung, anderer Wert an der Strecke) OFFEN-Meldung, der Abschnitt
    bleibt, wie er ist, und die Einstellungen bleiben für einen späteren Lauf. Ein zweiter Lauf findet nichts."""
    import io
    from ruamel.yaml.scalarstring import DoubleQuotedScalarString
    import schreiben as sb
    cfg_pfad = reise_dir / "reise.json"
    if not cfg_pfad.exists():
        return lambda: None
    cfg = lies_json(cfg_pfad)
    sprache = sprache_von(reise_dir)
    muster = alte_etappen_ueberschrift(cfg)
    gewuenscht = cfg.get("etappen_kennzahlen") or []
    strecken = (roh or {}).get("strecken") or {}
    dateien, offen, unsicher = {}, False, set()
    for schluessel in ("etappen_dossier", "unterkuenfte_dossier"):
        rel = cfg.get(schluessel)
        if not rel or not (reise_dir / rel).exists():
            continue
        zeilen = (reise_dir / rel).read_text(encoding="utf-8").split("\n")
        geaendert, raus = False, set()
        # Zwei Überschriften mit derselben Nummer sind nicht eindeutig zuzuordnen: offen melden statt zu raten (Spec, Risiken)
        ids = [alte_etappen_id(m.group(1)) for z in zeilen if (m := z.startswith("## ") and muster.match(z[3:].strip()))]
        doppelt = {e for e in ids if ids.count(e) > 1}
        for eid in sorted(doppelt):
            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.etappe_doppelt", eid=eid, datei=rel))
            offen = True
        for i, z in enumerate(zeilen):
            m = z.startswith("## ") and muster.match(z[3:].strip())
            if not m or alte_etappen_id(m.group(1)) in doppelt | unsicher:
                continue
            eid, name = alte_etappen_id(m.group(1)), m.group(2).strip()
            st = strecken.get(eid)
            if not isinstance(st, dict):
                meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.etappe_ohne_strecke", eid=eid, titel=z[3:].strip(), datei=rel))
                continue   # Archiv-Text: bleibt in der Datei, der Bau übergeht ihn (#357); nichts bleibt für die Hand offen
            if schluessel == "etappen_dossier":
                ende = next((j for j in range(i + 1, len(zeilen)) if zeilen[j].startswith("## ")), len(zeilen))
                eck = eckdaten_zeilen(zeilen, i + 1, ende)
                was, erster, raus_e, konflikt = [], {}, {}, set()
                if not st.get("titel"):
                    st.insert(0, "titel", DoubleQuotedScalarString(name))
                    was.append("titel")
                if not hasattr(st.get("kennzahlen"), "insert"):
                    pos = list(st.keys()).index("quelle") if "quelle" in st else len(st)
                    st.insert(pos, "kennzahlen", sb.fliess_map({}))
                km = st["kennzahlen"]
                for n in gewuenscht:   # Reihenfolge der Reise; die erste Zeile einer Kennung gilt wie bisher, keine wird überschrieben
                    for j, _, w in [d for d in (eck[2] if eck else []) if d[1] == n and d[2]]:
                        k, melde = kennung_der_kennzahl(n), None
                        if k in erster:
                            melde = texte.t(sprache, "pruefung.neu.nachziehen.etappe_kennzahl_doppelt", eid=eid, name=n, erster=erster[k], kennung=k, datei=rel)
                        elif k not in km:
                            km[k] = sb.skalar(k, w if k == "gehzeit" else kennzahl_wert(w))   # gehzeit bleibt Text
                            was.append(k)
                        erster.setdefault(k, n)
                        if melde is None and gleicher_wert(km[k], w):
                            raus_e[j] = (n, k, w)
                        else:
                            meldungen.append(melde or texte.t(sprache, "pruefung.neu.nachziehen.etappe_kennzahl_anders", eid=eid, name=n, kennung=k, w1=w, w2=km[k], datei=rel))
                            konflikt.add(j)   # es gilt der Wert an der Strecke, die abweichende Zeile bleibt als Text stehen (#357)
                if raus_e:   # nachgelesen, wie der Bau routen.yaml liest (PyYAML): nur was dort gleich steht, verlässt das Dossier
                    aus = io.StringIO()
                    sb.yaml_rund().dump(roh, aus)
                    g = ((((yaml.safe_load(aus.getvalue()) or {}).get("strecken") or {}).get(eid) or {}).get("kennzahlen") or {})
                    for j, (n, k, w) in list(raus_e.items()):
                        if g.get(k) is None or (k == "gehzeit" and not isinstance(g[k], str)) or not gleicher_wert(g[k], w):
                            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.etappe_kennzahl_anders", eid=eid, name=n, kennung=k, w1=w, w2=g.get(k), datei=rel))
                            konflikt.add(j)
                if not km:
                    del st["kennzahlen"]
                if was:
                    meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.etappe", eid=eid, was=", ".join(was), datei=rel))
                raus |= eckdaten_raus(zeilen, eck, set(raus_e) - konflikt) if eck else set()
            neu = f"## {eid} {name}"
            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.etappe_ueberschrift", datei=rel, alt=z[3:].strip(), neu=neu[3:]))
            zeilen[i] = neu
            geaendert = True
        if geaendert:
            dateien[reise_dir / rel] = "\n".join(z for j, z in enumerate(zeilen) if j not in raus)
    # Bleibt eine Etappe offen, bleiben auch die Einstellungen, damit ein Lauf nach dem Anlegen der Strecke sie noch umstellen kann
    alt = [] if offen else [k for k in ("etappen_kennzahlen", "etappen_muster") if k in cfg]
    if alt:
        meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.etappe_einstellungen"))

    def fertig():   # erst nach dem Speichern von routen.yaml: das Dossier gibt nur ab, was dort schon steht
        if not schreiben:
            return
        for p, text in dateien.items():
            p.write_text(text, encoding="utf-8")
        if alt:
            for k in alt:
                del cfg[k]
            schreib_json(cfg_pfad, cfg)
    return fertig


def nachziehen(reise_dir, strecken_arten=None, schreiben=True):
    """Nur Schlüssel, keine Inhalte: Unterkunft und Nacht typ: → art:; Wahlstelle bereich: → art:, art: planung|unterwegs →
    wann:; Strecke ohne art: bekommt die in strecken_arten genannte ({E-15: kombiniert}), sonst wird sie gemeldet; das
    Merkmal mit Schlüssel preis (Typ geld) einer Aufenthalts-Art bekommt rolle: kosten, wenn die Art noch keine Rolle hat;
    reise.json bekommt die bisherige Vorgabe der Ebene „Unterwegs nachschlagen“, wenn die Reise ein Etappen-Dossier hat;
    Eckdaten aus der früheren Vorlage stellt eckdaten_nachziehen um (#217); reise.yaml ohne sprache bekommt sprache: de
    (sprache_nachziehen, #267), vor den Schritten, die die Sprache der Reise lesen; Titel und Kennzahlen der Etappen kommen aus
    dem Dossier an die Strecken (etappen_nachziehen, #269); das frühere Feld buchung: an Dingen wird zur Buchung B-…
    (buchung_nachziehen, #215); Ort und gleichnamige Wegpunkte bekommen eine Lage (orte_lage_zusammenfuehren, ADR-0008).
    Kommentare und Form der Dateien bleiben (ruamel). -> Liste der Meldungen (was geändert oder offen ist)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from routen import WANN, art_schluessel
    import schreiben as sb
    reise_dir = Path(reise_dir)
    strecken_arten = dict(strecken_arten or {})
    meldungen = sprache_nachziehen(reise_dir, schreiben)
    roh = sb.routen_laden(reise_dir) if (reise_dir / "plan" / "routen.yaml").exists() else None   # ohne Plan (Status idee): nur arten.yaml und reise.json

    def typ_zu_art(knoten, wo):
        if not isinstance(knoten, dict) or knoten.get("typ") is None:
            return
        if knoten.get("art") is None:
            a = art_schluessel(knoten["typ"])
            knoten.insert(list(knoten.keys()).index("typ"), "art", a)
            meldungen.append(f"{wo}: typ “{knoten['typ']}” → art {a}")
        else:
            meldungen.append(f"{wo}: typ “{knoten['typ']}” removed (art {knoten['art']} is already there)")
        del knoten["typ"]

    for uid, u in ((roh or {}).get("unterkuenfte") or {}).items():
        typ_zu_art(u, uid)
    for tid, t in ((roh or {}).get("tage") or {}).items():
        if isinstance(t, dict):
            typ_zu_art(t.get("nacht"), f"{tid} nacht")
    for sid, st in ((roh or {}).get("strecken") or {}).items():
        if isinstance(st, dict) and not st.get("art"):
            if sid in strecken_arten:
                st["art"] = strecken_arten[sid]
                meldungen.append(f"{sid}: art {strecken_arten[sid]} (given)")
            else:
                meldungen.append(f"OPEN {sid}: no kind; give it with --strecke {sid}=<art> (the build requires it)")
    # Typisierte Merkmale (ADR-0007, Schritt b): feste Felder adresse, punkt, beginn/ende, ab, an (Zeit), buchungslink, gpx → merkmale:
    for gruppe, wort in (("orte", "Ort"), ("strecken", "Strecke"), ("unterkuenfte", "Unterkunft"), ("aufenthalte", "Aufenthalt")):
        for did, k in ((roh or {}).get(gruppe) or {}).items():
            if isinstance(k, dict):
                for feld in sb.felder_zu_merkmalen(k, sb.lesbar(reise_dir, [sb.S("schreiben.quelle_bestand")])):
                    meldungen.append(f"{did}: {feld} → merkmale (typisiert)")
    if roh is not None:
        kartenpunkte_umstellen(reise_dir, roh, schreiben, meldungen)
        orte_lage_zusammenfuehren(reise_dir, roh, schreiben, meldungen)   # ADR-0008, Schritt c: eine Lage je Stelle
    for vid, w in ((roh or {}).get("wahlstellen") or {}).items():
        if not isinstance(w, dict):
            continue
        alt_art, bereich = w.get("art"), w.get("bereich")
        if alt_art in WANN:
            w.insert(list(w.keys()).index("art"), "wann", alt_art)
            del w["art"]
            meldungen.append(f"{vid}: art {alt_art} → wann {alt_art}")
        if bereich is not None:
            if w.get("art") is None:
                w.insert(list(w.keys()).index("bereich"), "art", bereich)
                meldungen.append(f"{vid}: bereich {bereich} → art {bereich}")
            del w["bereich"]
    buchung_nachziehen(reise_dir, roh, schreiben, meldungen)   # #215: Feld buchung: an Dingen -> Buchung B-…
    kennzahlen_kennungen(roh, sprache_von(reise_dir), meldungen)   # #269: Namen der Kennzahlen in routen.yaml -> Kennungen
    dossier_fertig = etappen_nachziehen(reise_dir, roh, schreiben, meldungen)   # #269: Titel und Kennzahlen an die Strecken
    if schreiben and roh is not None:
        sb.routen_speichern(reise_dir, roh)
    dossier_fertig()   # Dossier und reise.json erst nach routen.yaml

    # arten.yaml: rolle kosten am Merkmal preis (Typ geld) der Aufenthalts-Arten
    if (reise_dir / "plan" / "arten.yaml").exists():
        arten = sb.arten_laden(reise_dir)
        geaendert = False
        for a, d in arten.items():
            mk = d.get("merkmale") if isinstance(d.get("merkmale"), dict) else {}
            if d.get("grundform") != "aufenthalt" or any(isinstance(m, dict) and m.get("rolle") for m in mk.values()):
                continue
            m = mk.get("preis")
            if isinstance(m, dict) and m.get("typ") == "geld":
                m["rolle"] = "kosten"
                geaendert = True
                meldungen.append(f"arten.yaml {a}: attribute preis gets rolle kosten")
        if geaendert and schreiben:
            sb.arten_speichern(reise_dir, arten, {"name": "Betrieb (neu.py nachziehen)"})

    # reise.json: bisherige Vorgabe der Ebene „Unterwegs nachschlagen“ (bis 29.10.2026 in der Software)
    cfg_pfad = reise_dir / "reise.json"
    if cfg_pfad.exists():
        cfg = lies_json(cfg_pfad)
        if cfg.get("etappen_dossier") and "etappen_ebenen" not in cfg:
            # die frühere Vorgabe war deutsch (#217): Wert der Umstellung, unabhängig von der Sprache der Reise
            cfg["etappen_ebenen"] = {"unterwegs": texte.t("de", "inhalt.nachziehen.unterwegs").split("|")}
            meldungen.append("reise.json: etappen_ebenen with the previous default for “Look up on the way”")
            if schreiben:   # in der Form der Datei (json.dumps mit Einrückung 2), damit nur die neue Zeile im Diff steht
                cfg_pfad.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        meldungen += eckdaten_nachziehen(reise_dir, cfg, schreiben)
    meldungen += reste_nachziehen(reise_dir, schreiben)
    return meldungen


def probebau(ordner):
    """Probebau mit der laufenden Software wie im Tor; ein Baufehler wirft (bauen.BauFehler)."""
    with tempfile.TemporaryDirectory(prefix="frieda-probe-") as ziel:
        bauen.Bauer(Path(ordner), ziel).daten()


def software_kennung():
    """Stand der laufenden Software (Commit des Ordners der Software; in einer Instanz das Submodul frieda/) oder ''."""
    import subprocess
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).resolve().parent), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


NACHZIEHEN_VERSUCHE = 3   # wie der Workflow beim Push: bei einem Wettlauf mit dem Schreibweg neu, nie erzwungen


def nachziehen_speicher(reise, ordner):
    """Eine Reise aus dem Reisespeicher auf den Stand der laufenden Software umstellen (#348, auf dem Server vom Lauf
    veroeffentlichen.sh): materialisieren nach ordner, nachziehen, Probebau, dann genau ein Vorgang (Person
    „Software-Nachziehen“, Werkzeug nachziehen). Nur Schlüssel, keine Inhalte. -> (Exit, Ausgabe): 0 umgestellt oder nichts
    umzustellen, 2 Probebau rot (nichts geschrieben), 1 dreimal Wettlauf mit dem Schreibweg (der nächste Lauf wiederholt)."""
    import sqlite3
    import reisespeicher as rs
    ordner = Path(ordner)
    kennung = software_kennung()[:12] or "unknown"
    for _ in range(NACHZIEHEN_VERSUCHE):
        basis = rs.materialisieren(reise, ordner)
        try:
            meldungen = nachziehen(ordner)
        except (OSError, sqlite3.Error):   # Ordner oder Speicher nicht erreichbar: Störung, der nächste Lauf wiederholt
            raise
        except Exception as e:   # die Reise selbst lässt sich nicht umstellen (etwa kaputte reise.yaml): wie ein roter Bau
            return 2, [f"ERROR: {reise} cannot be converted, nothing written: {type(e).__name__}: {e}"]
        warnungen = [f"Warning: {m}" for m in meldungen if m.startswith(("OPEN", "OFFEN"))]
        if not rs.vergleichen(reise, ordner, bis=basis):
            zeilen = warnungen
            break
        try:
            probebau(ordner)
        except Exception as e:   # jeder Fehler des Baus sperrt: nichts eintragen
            gruende = list(getattr(e, "meldungen", None) or [e])
            return 2, warnungen + [f"ERROR: build of {reise} after the conversion failed, nothing written:"] \
                + [f" - {g}" for g in gruende]
        try:
            v = rs.ordner_als_vorgang(reise, ordner, basis, wer="Software-Nachziehen", werkzeug="nachziehen",
                                      titel=f"software {kennung}", grund="\n".join(meldungen),
                                      kennung=f"nachziehen:{kennung}:{reise}:{basis}", rolle="")
        except rs.StandGeaendert:
            continue
        except (rs.VorgangVorhanden, rs.NichtsGeaendert):
            zeilen = warnungen
            break
        rs.stand_datei(ordner).write_text(f"{v.stand}\n", encoding="utf-8")
        zeilen = warnungen + meldungen + [f"umgestellt, stand {v.stand}"]
        break
    else:
        return 1, [f"ERROR: {reise} changed {NACHZIEHEN_VERSUCHE} times during the conversion, the next run tries again."]
    return ablage_umstellen(reise, ordner, zeilen)


def ablage_umstellen(reise, ordner, zeilen):
    """Zweiter, getrennter Vorgang des Nachziehens (Stufe 4, #349): Medien, deren Bytes noch in der Datenbank liegen, in die
    Ablage des Speichers (reisespeicher.auslagern, Inhalt unverändert, kein Probebau). zeilen: Ausgabe des ersten Teils.
    -> (Exit, Ausgabe): 0 umgestellt oder nichts umzustellen, 1 dreimal Wettlauf mit dem Schreibweg."""
    import reisespeicher as rs
    for _ in range(NACHZIEHEN_VERSUCHE):
        basis = rs.stand_nummer(reise) or 0
        try:
            v = rs.auslagern(reise, basis, wer="Software-Nachziehen", werkzeug="nachziehen", titel="ablage-umstellung",
                             grund="media moved to the store (#349)", kennung=f"ablage:{reise}:{basis}")
        except rs.StandGeaendert:
            continue
        except rs.VorgangVorhanden:
            v = None
        if v is None:
            return 0, zeilen if any(z.startswith("umgestellt") for z in zeilen) else zeilen + ["nichts umzustellen"]
        rs.materialisieren(reise, ordner, bis=v.stand)
        return 0, zeilen + [f"ablage-umstellung, stand {v.stand}"]
    return 1, zeilen + [f"ERROR: {reise} changed {NACHZIEHEN_VERSUCHE} times while moving media to the store, "
                        "the next run tries again."]


BUCHUNG_STAND_ALT = ("angefragt", "gebucht")   # Werte des früheren Felds buchung:, die als Status der Buchung bleiben


def buchung_nachziehen(reise_dir, roh, schreiben, meldungen):
    """Das frühere Feld buchung: an Unterkünften, Aufenthalten und Strecken (#215) wird zur Buchung B-…: offen oder leer
    entfällt (ohne Buchung gilt „offen“); hat das Ding schon eine geltende Buchung, entfällt nur das Feld; angefragt und
    gebucht werden eine Buchung mit diesem Status; jeder andere Text eine Buchung gebucht mit dem Text als Notiz und einer
    Meldung zum Prüfen. Die Nummer folgt den vorhandenen IDs. Ohne das Feld bleibt alles, wie es ist. Ändert roh."""
    if not isinstance(roh, dict):
        return
    import schreiben as sb
    sprache = sprache_von(reise_dir)
    buchungen = roh.get("buchungen") if isinstance(roh.get("buchungen"), dict) else {}

    def geltende(did):
        for bid, b in buchungen.items():
            fuer = b.get("fuer") if isinstance(b, dict) else None
            fuer = [fuer] if isinstance(fuer, str) else list(fuer or [])
            if did in fuer and b.get("status", "gebucht") != "storniert":
                return bid
        return None

    zaehler = [None]

    def neue_bid():
        if schreiben:
            return naechste_id(reise_dir, "B")
        if zaehler[0] is None:   # ohne Schreiben: nur rechnen, ids.yaml bleibt
            datei = Path(reise_dir) / "ids.yaml"
            marken = (yaml.safe_load(datei.read_text(encoding="utf-8")) or {}) if datei.exists() else {}
            zaehler[0] = max(int(marken.get("B") or 0), _nummern(Path(reise_dir), "B"))
        zaehler[0] += 1
        return f"B-{zaehler[0]:02d}"

    for gruppe in ("unterkuenfte", "aufenthalte", "strecken"):
        for did, d in (roh.get(gruppe) or {}).items():
            if not isinstance(d, dict) or "buchung" not in d:
                continue
            wert = d["buchung"]
            text = "" if wert is None else str(wert).strip()
            del d["buchung"]
            if not text or text == "offen":
                meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.buchung_entfernt", wo=did))
                continue
            alt = geltende(did)
            if alt:
                meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.buchung_vorhanden", wo=did, bid=alt))
                continue
            status = text if text in BUCHUNG_STAND_ALT else "gebucht"
            neu_b = {"fuer": [did], "status": status, "quelle": texte.t(sprache, "inhalt.nachziehen.buchung_quelle")}
            if text not in BUCHUNG_STAND_ALT:
                neu_b["notiz"] = text
            bid = neue_bid()
            if not isinstance(roh.get("buchungen"), dict):
                roh["buchungen"] = type(roh)()
                buchungen = roh["buchungen"]
            roh["buchungen"][bid] = sb.block_map(neu_b)
            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.buchung", wo=did, status=text, bid=bid))
            if text not in BUCHUNG_STAND_ALT:
                meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.buchung_pruefen", wo=did, text=text))


SPRACHE_NACHZIEHEN = "de"   # trägt nachziehen ein, weil für Reisen ohne Feld sprache bisher Deutsch galt (keine Lesetoleranz mehr); die Umstellung ändert kein Verhalten
VOR_SPRACHE = ("titel", "untertitel", "ziel", "pfad")   # Schlüssel vor sprache, Reihenfolge wie in anlegen


def sprache_nachziehen(reise_dir, schreiben=True):
    """reise.yaml ohne sprache (oder leer) bekommt sprache: de (#267). Nur diese eine Zeile ändert sich: Sie ersetzt eine
    leere Zeile sprache: oder steht hinter dem letzten der Schlüssel aus VOR_SPRACHE, ohne sie als erster Schlüssel nach dem
    Kopfkommentar. Steht schon ein Wert (auch ein unbekannter), bleibt die Datei unberührt; den Wert prüft der Bau. -> Meldungen."""
    import schreiben as sb
    y = Path(reise_dir) / "reise.yaml"
    if not y.is_file():
        return []
    text = y.read_bytes().decode("utf-8")   # ohne Übersetzung der Zeilenenden: eine Datei mit CRLF behält sie (F001)
    roh = sb.yaml_rund().load(text)
    if not isinstance(roh, dict):
        return []
    wert = roh.get("sprache")
    if wert is not None and not (isinstance(wert, str) and not wert.strip()):
        return []
    zeilen = text.splitlines(keepends=True)
    nl = "\r\n" if "\r\n" in text else "\n"   # Zeilenende der Datei für die neue Zeile
    neu_zeile = f"sprache: {SPRACHE_NACHZIEHEN}"
    if "sprache" in roh:   # leer: dieselbe Zeile, ein Kommentar dahinter bleibt
        i = roh.lc.key("sprache")[0]
        rest = re.search(r"\s#.*$", zeilen[i].rstrip("\r\n"))
        ende = zeilen[i][len(zeilen[i].rstrip("\r\n")):]
        zeilen[i] = neu_zeile + (rest.group(0) if rest else "") + ende
    else:
        schluessel = list(roh.keys())
        vor = [k for k in VOR_SPRACHE if k in roh]
        if vor:
            k = vor[-1]
            i = roh.lc.key(k)[0] + 1
            naechste = schluessel.index(k) + 1
            bis = roh.lc.key(schluessel[naechste])[0] if naechste < len(schluessel) else len(zeilen)
            while i < bis and zeilen[i][:1] in (" ", "\t"):   # mehrzeiliger Wert des Vorgängers
                i += 1
        else:
            i = roh.lc.key(schluessel[0])[0] if schluessel else len(zeilen)
        if i > 0 and i == len(zeilen) and not zeilen[-1].endswith("\n"):
            zeilen[-1] += nl
        zeilen.insert(i, neu_zeile + nl)
    if schreiben:
        y.write_bytes("".join(zeilen).encode("utf-8"))
    return [texte.t(SPRACHE_NACHZIEHEN, "inhalt.nachziehen.sprache_eingetragen")]


VORLAGE_VOR_217 = Path(__file__).resolve().parent / "altformen" / "vorlage-vor-217"   # <sprache>/CLAUDE.md, kontext/herkunft.md


def _zeilen_normal(text):
    """CRLF zu LF, Leerzeilen am Ende entfernt -> Liste der Zeilen."""
    zeilen = text.replace("\r\n", "\n").split("\n")
    while zeilen and not zeilen[-1].strip():
        zeilen.pop()
    return zeilen


def ist_vorlagen_kopie(text, muster):
    """True, wenn text nur die ausgefüllte frühere Vorlage muster ist: gleiche Zeilenzahl, jede Zeile passt vollständig zur
    Zeile des Musters, ein Platzhalter $wort steht für beliebigen Text. Eine leere Datei passt nie."""
    zeilen, vorlage = _zeilen_normal(text), _zeilen_normal(muster)
    if not zeilen or len(zeilen) != len(vorlage):
        return False
    for z, m in zip(zeilen, vorlage):
        teile = re.split(r"\$[A-Za-z_]+", m)
        if not re.fullmatch(".*".join(re.escape(t) for t in teile), z):
            return False
    return True


def reste_nachziehen(reise_dir, schreiben=True):
    """Reste der früheren Vorlage (#250): CLAUDE.md und kontext/herkunft.md gehen, wenn sie nur ausgefüllte Kopien der Vorlage
    (engine/altformen/vorlage-vor-217/<sprache>/) sind; ein dadurch leeres kontext/ geht mit. Eigene Dateien bleiben ohne
    Meldung, die Software liest sie nicht. Der Kopfkommentar der reise.yaml mit wörtlichem \\n (#218) bekommt echte
    Zeilenumbrüche. -> Meldungen."""
    reise_dir = Path(reise_dir)
    sprache = sprache_von(reise_dir)
    meldungen = []
    for rel in ("CLAUDE.md", "kontext/herkunft.md"):
        pfad = reise_dir / rel
        if not pfad.is_file():
            continue
        text = pfad.read_text(encoding="utf-8", errors="replace")
        muster = [m.read_text(encoding="utf-8") for m in sorted(VORLAGE_VOR_217.glob(f"*/{rel}"))]
        if not any(ist_vorlagen_kopie(text, m) for m in muster):
            continue
        meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.rest", datei=rel))
        if schreiben:
            pfad.unlink()
            ordner = pfad.parent
            if ordner != reise_dir and not any(ordner.iterdir()):
                ordner.rmdir()
    y = reise_dir / "reise.yaml"
    if y.is_file():
        text = y.read_text(encoding="utf-8")
        zeilen = text.split("\n")
        i = 0
        while i < len(zeilen) and zeilen[i].startswith("#"):
            zeilen[i] = re.sub(r"\\n(?=#)", "\n", zeilen[i])
            i += 1
        neu_text = "\n".join(zeilen)
        if neu_text != text:
            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.kopfkommentar"))
            if schreiben:
                y.write_text(neu_text, encoding="utf-8")
    return meldungen


def eckdaten_nachziehen(reise_dir, cfg, schreiben=True):
    """Reisen von vor #217: Die Vorlage schrieb die Eckdaten als festen Text in plan/plan.md (Zeitraum, Ziel, Wer, Satz zur Idee)
    und den Untertitel als Kopie von Ziel und Zeitraum. Jetzt baut der Generator beides aus reise.yaml. Entfernt werden nur
    Zeilen genau dieser Form; das Ziel kommt nach reise.yaml, ein Untertitel, der nur die Kopie ist, entfällt, reise.json
    nennt den Abschnitt unter „eckdaten“. Keine ID ändert sich. -> Meldungen."""
    import reise as rs
    import schreiben as sb
    plan_rel = cfg.get("plan")
    if cfg.get("eckdaten") or not plan_rel or not (reise_dir / plan_rel).exists() or not (reise_dir / "reise.yaml").exists():
        return []
    eck_woerter = texte.inhaltswoerter("inhalt.ebene.eckdaten")
    zuordnung = (cfg.get("abschnitte") or {}).get(plan_rel) or {}
    titel = next((t for t in zuordnung if t in eck_woerter), None)
    if not titel:
        return []
    sid = zuordnung[titel][0]
    anfang = {f: tuple(f"- {texte.t(k, 'inhalt.eckdaten.' + f, zeitraum='', ziel='', personen='')}".rstrip() for k in texte.sprachen())
              for f in ("zeitraum", "ziel", "wer")}
    idee = {f"- {texte.t(k, 'inhalt.eckdaten.idee')}" for k in texte.sprachen()}
    offen = {texte.t(k, "inhalt.neu.ziel_offen") for k in texte.sprachen()}
    plan_pfad = reise_dir / plan_rel
    zeilen = plan_pfad.read_text(encoding="utf-8").split("\n")
    kopf = next((i for i, z in enumerate(zeilen) if z.strip() == f"## {titel}"), None)
    if kopf is None:
        return []
    ende = next((i for i in range(kopf + 1, len(zeilen)) if zeilen[i].startswith("## ")), len(zeilen))
    behalten, ziel, gefunden = [], None, False
    for z in zeilen[kopf + 1:ende]:
        art = next((f for f, a in anfang.items() if z.startswith(a)), None)
        if art == "ziel":
            wert = z.split(":", 1)[1].strip()
            ziel = None if wert in offen else wert
        if art is None and z.rstrip() not in idee:
            behalten.append(z)
        else:
            gefunden = True
    if not gefunden:   # eigene Eckdaten, nicht aus der Vorlage: bleiben, wie sie sind
        return []
    sprache = rs.sprache_von(reise_dir)   # Meldungen und Untertitel in der Sprache der Reise
    meldungen = [texte.t(sprache, "pruefung.neu.nachziehen.eckdaten", datei=plan_rel, sid=sid)]
    p, roh = sb.reise_yaml_laden(reise_dir)
    if ziel and not roh.get("ziel") and len(ziel) <= rs.ZIEL_LAENGE:
        roh.insert(list(roh.keys()).index("pfad") if "pfad" in roh else len(roh), "ziel", sb.skalar("ziel", ziel))
        meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.ziel", ziel=ziel))
    z = roh.get("zeitraum")
    if roh.get("untertitel") and isinstance(z, dict) and all(isinstance(z.get(k), datetime.date) for k in ("von", "bis")):
        kopie = rs.untertitel_aus(roh.get("ziel") or "", {"von": z["von"].isoformat(), "bis": z["bis"].isoformat()}, sprache)
        if roh["untertitel"] == kopie:
            del roh["untertitel"]
            meldungen.append(texte.t(sprache, "pruefung.neu.nachziehen.untertitel"))
    if schreiben:
        while behalten and not behalten[0].strip():
            behalten.pop(0)
        neu_zeilen = zeilen[:kopf + 1] + ([""] + behalten if any(x.strip() for x in behalten) else []) + zeilen[ende:]
        plan_pfad.write_text("\n".join(neu_zeilen).rstrip("\n") + "\n", encoding="utf-8")
        sb.reise_yaml_speichern(p, roh)
        cfg_neu = {}
        for k, v in cfg.items():   # „eckdaten“ gleich hinter „plan“, in der Form der Datei
            cfg_neu[k] = v
            if k == "plan":
                cfg_neu["eckdaten"] = sid
        (reise_dir / "reise.json").write_text(json.dumps(cfg_neu, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return meldungen


# ---------- Aufruf ----------
def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="engine/neu.py", description="Create the first trip of an instance, check before the build, bring existing trips up to date (structure only, never content).")
    sub = ap.add_subparsers(dest="befehl", required=True)
    r = sub.add_parser("reise", help="create the first trip of an instance empty from the template")
    r.add_argument("reisen", type=Path)
    r.add_argument("--titel", required=True)
    r.add_argument("--von", required=True, type=datetime.date.fromisoformat)
    r.add_argument("--bis", required=True, type=datetime.date.fromisoformat)
    r.add_argument("--person", action="append", required=True, help="key=Name:role[:travels|not]")
    r.add_argument("--wer", required=True, help="name of the person creating the trip (organiser)")
    r.add_argument("--ziel")
    r.add_argument("--pfad")
    r.add_argument("--sprache", help="language code (texte.SPRACHEN), default en")
    r.add_argument("--untertitel")
    r.add_argument("--herkunft", help="default: first trip of the instance by the operator")
    p = sub.add_parser("pruefen", help="check before the build")
    p.add_argument("reise", type=Path)
    g = sub.add_parser("arten-ableiten", help="derive plan/arten.yaml from the existing data of the trip (package O-2)")
    g.add_argument("reise", type=Path)
    g.add_argument("--name", action="append", default=[], help="art=display name, e.g. ferry=Ferry")
    g.add_argument("--summiert", default="", help="kinds under one's own power, comma list, e.g. hiking,cycling")
    g.add_argument("--definitionen", type=Path, help="YAML {merkmal: {name, typ, …}} as a template for names and help texts")
    nz = sub.add_parser("nachziehen", help="bring the keys of an existing trip to the state of 29.10.2026 (keys only)")
    nz.add_argument("reise", type=Path)
    nz.add_argument("--strecke", action="append", default=[], help="E-ID=art for legs without a kind, e.g. E-15=kombiniert")
    ns = sub.add_parser("nachziehen-speicher", help="bring a trip in the trip store up to date on the server (keys only, one operation)")
    ns.add_argument("reise")
    ns.add_argument("ordner", type=Path, help="working folder, replaced (e.g. <FR_DIENST>/bau/reisen/<trip>)")
    # mit oder ohne Programmnamen vorn (sys.argv oder nur die Angaben)
    x = ap.parse_args(argv if argv and argv[0] in sub.choices else argv[1:])
    try:
        if x.befehl == "nachziehen-speicher":
            import sqlite3
            import reisespeicher as rs
            try:
                rc, zeilen = nachziehen_speicher(x.reise, x.ordner)
            except KeyError as e:
                rc, zeilen = 2, [f"ERROR: unknown trip in the trip store: {e.args[0] if e.args else ''}"]
            except ValueError as e:
                rc, zeilen = 2, [f"ERROR: {e}"]
            except (rs.AblageFehlt, rs.AblageFehler) as e:   # Ablage lückenhaft oder beschädigt: rote Reise (#349)
                rc, zeilen = 2, rs.ablage_ausgabe(e, x.reise)
            except (OSError, sqlite3.Error) as e:   # Datenbank gesperrt oder nicht lesbar: der nächste Lauf wiederholt
                rc, zeilen = 1, [f"ERROR: {e}"]
            print("\n".join(zeilen))
            return rc
        if x.befehl == "nachziehen":
            m = nachziehen(x.reise, dict(t.split("=", 1) for t in x.strecke))
            print("\n".join(m) if m else "Nothing to bring up to date.")
            return 1 if any(t.startswith("OPEN") for t in m) else 0
        if x.befehl == "arten-ableiten":
            import yaml
            defs = yaml.safe_load(x.definitionen.read_text(encoding="utf-8")) if x.definitionen else {}
            print(arten_ableiten(x.reise, dict(n.split("=", 1) for n in x.name), set(filter(None, x.summiert.split(","))), defs))
            return 0
        if x.befehl == "reise":
            personen = dict(person_aus_text(t) for t in x.person)
            d = anlegen(x.reisen, x.titel, x.von, x.bis, personen, x.wer, ziel=x.ziel, pfad=x.pfad, sprache=x.sprache,
                        untertitel=x.untertitel,
                        herkunft=x.herkunft or texte.t(sprache_pruefen(x.sprache)[0], "inhalt.neu.herkunft_gespraech_betreiber"))
            ok, m = pruefen(d)
            print(f"Created: {d} (status idee)." + ("" if ok else " The check reports:\n - " + "\n - ".join(m)))
            return 0 if ok else 1
        ok, m = pruefen(x.reise)
        if ok:
            print(f"OK: {cfg_titel(x.reise)} builds without errors.")
            return 0
        print(f"The trip does not build yet. {len(m)} point{'s' if len(m) != 1 else ''} to fix:")
        for n, t in enumerate(m, 1):
            print(f" {n}. {t}")
        return 1
    except Fehler as e:
        print(f"Not possible: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
