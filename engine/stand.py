"""Reise-Stand (Epic #223): eine fortlaufende Nummer je Reise und der Weg eines Stands vom Sichern bis auf die Seite.

Nummer: je gesichertem Schreibvorgang +1. Für eine Reise aus FR_SPEICHERREISEN ist sie die Stand-Nummer im Reisespeicher
(engine/reisespeicher.py, ADR-0009, ab Stufe 2, #347), die Änderungsliste kommt aus seinem Verlauf. Für jede andere Reise
zählt bis Stufe 5 weiter Git (engine/stand_git.py): die Zahl der Commits, die den Ordner der Reise ändern; ein
Software-Update ändert den Ordner nicht und lässt sie stehen. Die Nummer steigt nur, Stand 43 enthält alles aus Stand 42.
Sie gehört zur Reise, nicht zum Bau: Der Bau liest sie nur ab. Fehlt die Quelle (Reise ohne Speichereintrag, ohne Git,
flacher Klon), fehlt die Nummer.

Weg eines Stands (docs/betrieb.md, „Reise-Stand“):
  gesichert      der Schreibweg (engine/schreiben.py) hat den Vorgang eingetragen (Speicher) bzw. nach main gebracht (Git)
  wird gebaut    betrieb/veroeffentlichen.sh baut die Seite der Reise neu
  veröffentlicht die Seite dieses Stands liegt auf dem Server (<Seiten>/<reise>/daten.json, reise_stand.nummer)
  auf dem Gerät  nur die Person sieht das, im Fuß der Seite
Fehlschlag: Scheitert der Bau, nennt der Zustand den Grund; die Seite bleibt auf dem bisherigen Stand.

Dateien im Dienstordner <FR_DIENST>/reise-stand/ (jede hat genau einen Schreiber):
  <reise>.gesichert.json   Schreibweg: {nummer, commit, zeit}
  <reise>.lauf.json        veroeffentlichen.sh: {zustand: baut | veroeffentlicht | fehlgeschlagen, nummer, gesichert, seit,
                           dauer, grund}
Gelesen wird nur auf dem Server (Rückmeldedienst api/stand, Konnektor publish_status), nie aus dem Speicher des Service
Workers. Zeiten stehen als UTC mit „Z“; angezeigt werden sie in der Ortszeit der Person (Seite: Gerät, Konnektor: Zeitzone
der Person, sonst FR_ZEITZONE der Instanz, sonst UTC, immer mit Angabe der Zone).
"""
import datetime
import importlib
import json
import os
import re
import sqlite3
from pathlib import Path

import instanz

ZIEL_SEKUNDEN = 120          # Zeitziel vom Sichern bis zur Veröffentlichung (Product Owner, E3, 2.11.2026)
AENDERUNGEN = 10             # so viele letzte Änderungen zeigt die Seite
ZUSTAENDE = ("wartet", "baut", "veroeffentlicht", "fehlgeschlagen")
ID_MUSTER = re.compile(r"(?<![\w-])([A-Z]{1,2}-\d+(?:\.[a-z0-9]+)?)(?![\w-])")
PERSON_TRAILER = "Frieda-Person"   # Zeile im Commit des Schreibwegs: wer den Eintrag gemacht hat


def nummer(ordner, rev="HEAD"):
    """Reise-Stand einer Git-Reise auf rev -> int oder None (engine/stand_git.py, bis Stufe 5)."""
    import stand_git
    return stand_git.nummer(ordner, rev)


def zeit_iso(t=None):
    """Zeitpunkt (datetime, Sekunden seit 1970 oder jetzt) als UTC-Text „2026-11-02T08:47:00Z“."""
    if t is None:
        t = datetime.datetime.now(datetime.timezone.utc)
    elif isinstance(t, (int, float)):
        t = datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
    elif t.tzinfo is None:
        t = t.astimezone()
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def zeit_lesen(text):
    """UTC-Text (oder ISO mit Zone) -> datetime mit Zone oder None."""
    if not isinstance(text, str) or not text:
        return None
    try:
        t = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


# ---------- Änderungsliste (S9): die letzten Änderungen in einfachen Worten, mit Person und Zeit ----------

def namen_der_ids(daten):
    """ID -> Name aus den Daten der Reise (alle Dinge, Tage, Wahlstellen, Optionen, Abschnitte, Fragen …). Ohne Kenntnis
    einzelner Grundformen: jedes Objekt mit id und name oder titel, und jede Zuordnung ID -> Objekt mit name oder titel."""
    namen = {}

    def name_von(o):
        for f in ("name", "titel"):
            if isinstance(o.get(f), str) and o[f].strip():
                return o[f].strip()
        return None

    def gehen(o):
        if isinstance(o, dict):
            i = o.get("id")
            if isinstance(i, str) and ID_MUSTER.fullmatch(i) and (n := name_von(o)):
                namen.setdefault(i, n)
            for k, v in o.items():
                if isinstance(k, str) and ID_MUSTER.fullmatch(k) and isinstance(v, dict) and (n := name_von(v)):
                    namen.setdefault(k, n)
                gehen(v)
        elif isinstance(o, list):
            for x in o:
                gehen(x)
    gehen(daten)
    return namen


def ohne_kennungen(text, namen):
    """Kennungen im Text durch Namen ersetzen („U-03 „Hotel Sol“ angelegt“ -> „„Hotel Sol“ angelegt“). Steht der Name schon
    dahinter, fällt nur die Kennung weg; unbekannte Kennungen bleiben."""
    def ersetzen(m):
        i = m.group(1)
        n = namen.get(i)
        if not n:
            return i
        rest = text[m.end():]
        if re.match(r"\s*[„\"“']?" + re.escape(n), rest):
            return ""
        return f"„{n}“"
    neu = ID_MUSTER.sub(ersetzen, text)
    return re.sub(r"\s{2,}", " ", re.sub(r"^\s+|\(\s*\)", "", neu)).strip()


def aenderungen(ordner, namen=None, n=AENDERUNGEN):
    """Die letzten n Änderungen einer Git-Reise -> [{nummer, zeit, was, wer}], neueste zuerst (engine/stand_git.py)."""
    import stand_git
    return stand_git.aenderungen(ordner, namen, n)


def _aus_dem_speicher(reise, namen):
    """Nummer und Änderungsliste einer Reise aus dem Reisespeicher -> (nummer, liste) oder (None, []) ohne Eintrag. Liest
    nur; ohne Datenbank wird keine angelegt, eine nicht lesbare zählt wie keine (der Bau bricht daran nicht ab).
    Der Speicher wird über importlib geladen: reisespeicher importiert seinerseits stand (zeit_iso), und Konnektor und
    Rückmeldedienst, die stand laden, rufen fuer_seite nie (sie lesen den Speicher erst ab Stufe 3, #348); das Modul
    liegt über SB_MODULE (betrieb/deploy.sh) im selben Dienstordner."""
    # Bewusst kein „import reisespeicher“: Die Prüfung der Modullisten (engine/tests/test_betrieb.py) folgt auch Importen in
    # Funktionen und verlangte reisespeicher.py dann in RM_MODULE und KN_MODULE, was der Test zu Stufe 2 (AC-23,
    # test_reisespeicher.py) bis Stufe 3 verbietet. Ruft künftig ein anderer Dienst als Bau und Schreibweg fuer_seite (oder
    # liest er sonst den Speicher), braucht er reisespeicher.py in seiner Modulliste in betrieb/deploy.sh; mit Stufe 3 wird
    # daraus ein normaler Import und die Listen werden ergänzt.
    rs = importlib.import_module("reisespeicher")
    try:
        if not rs.pfad().exists():
            return None, []
        gesamt = rs.stand_nummer(reise)
        if gesamt is None:
            return None, []
        verlauf = rs.verlauf(reise, n=AENDERUNGEN)
    except (sqlite3.Error, OSError):
        return None, []
    return gesamt, [{"nummer": e["nummer"], "zeit": e["zeit"], "was": ohne_kennungen(e["was"], namen), "wer": e["wer"] or None}
                    for e in verlauf]


def fuer_seite(ordner, daten):
    """Reise-Stand für die Seite (daten.reise_stand): {nummer, zeit, aenderungen} oder None ohne Quelle. Der Bau kennt nur
    den Ordner; die Reise ist sein Name. Steht sie in FR_SPEICHERREISEN, kommt alles aus dem Reisespeicher (ohne Eintrag:
    None), sonst aus Git (engine/stand_git.py, bis Stufe 5). zeit ist der Zeitpunkt der letzten Änderung. Keine Bauzeit:
    gleicher Inhalt ergibt dieselbe Seite (Service Worker, bauen.py)."""
    if Path(ordner).name in instanz.speicherreisen():
        n, liste = _aus_dem_speicher(Path(ordner).name, namen_der_ids(daten))
    else:
        n = nummer(ordner)
        liste = aenderungen(ordner, namen_der_ids(daten)) if n is not None else []
    if n is None:
        return None
    return {"nummer": n, "zeit": liste[0]["zeit"] if liste else None, "aenderungen": liste}


# ---------- Zustand auf dem Server (S3–S5) ----------

def ordner_dienst():
    return instanz.dienst() / "reise-stand"


def _lies(p):
    try:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _schreiben(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".{os.getpid()}.neu")
    tmp.write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def gesichert_schreiben(reise, n, commit=None, zeit=None):
    """Der Schreibweg hat Stand n der Reise nach main gebracht. Wirft nie (das Sichern ist schon geschehen)."""
    if n is None:
        return
    try:
        _schreiben(ordner_dienst() / f"{reise}.gesichert.json", {"nummer": int(n), "commit": commit, "zeit": zeit or zeit_iso()})
    except OSError:
        pass


def veroeffentlicht(reise):
    """Was auf dem Server liegt: (nummer, zeit der letzten Änderung) aus <Seiten>/<reise>/daten.json, oder (None, None)."""
    try:
        d = json.loads((instanz.seiten() / reise / "daten.json").read_text(encoding="utf-8"))
        rs = d.get("reise_stand") or {}
        return (rs.get("nummer") if isinstance(rs.get("nummer"), int) else None), rs.get("zeit")
    except (OSError, ValueError, AttributeError):
        return None, None


def _rot():
    """Rot-Datei des Veröffentlichens (betrieb/veroeffentlichen.sh) -> {commit, art, reisen, seit, tests …}."""
    try:
        zeilen = (instanz.dienst() / "veroeffentlichen-rot").read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    return dict(z.split("=", 1) for z in zeilen if "=" in z)


def lesen(reise, jetzt=None):
    """Zustand des Reise-Stands auf dem Server -> {
         gesichert: {nummer, zeit}, veroeffentlicht: {nummer, zeit}, zustand: wartet | baut | veroeffentlicht | fehlgeschlagen
         | unbekannt, seit, grund, grund_art (bau | software), dauer (Sekunden vom Sichern bis zur Veröffentlichung bzw. bis
         jetzt), ziel (Sekunden), ueber_ziel}"""
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    g = _lies(ordner_dienst() / f"{reise}.gesichert.json")
    lauf = _lies(ordner_dienst() / f"{reise}.lauf.json")
    pub_n, pub_aenderung = veroeffentlicht(reise)
    zahlen = [x for x in (g.get("nummer"), lauf.get("nummer"), pub_n) if isinstance(x, int)]
    ges_n = max(zahlen) if zahlen else None
    # Zeit des gesicherten Stands: aus der Datei, die die höchste Nummer kennt
    if isinstance(g.get("nummer"), int) and g["nummer"] == ges_n:
        ges_zeit = g.get("zeit")
    elif lauf.get("nummer") == ges_n:
        ges_zeit = lauf.get("gesichert")
    else:
        ges_zeit = pub_aenderung
    pub_zeit = lauf.get("seit") if lauf.get("zustand") == "veroeffentlicht" and lauf.get("nummer") == pub_n else None
    if pub_zeit is None and pub_n is not None:
        try:
            pub_zeit = zeit_iso((instanz.seiten() / reise / "daten.json").stat().st_mtime)
        except OSError:
            pub_zeit = None
    erg = {"gesichert": {"nummer": ges_n, "zeit": ges_zeit}, "veroeffentlicht": {"nummer": pub_n, "zeit": pub_zeit},
           "zustand": "unbekannt", "seit": None, "grund": None, "grund_art": None, "dauer": None,
           "ziel": ZIEL_SEKUNDEN, "ueber_ziel": False}
    if ges_n is None:
        return erg
    rot = _rot()
    if pub_n is not None and pub_n >= ges_n:
        erg.update(zustand="veroeffentlicht", seit=pub_zeit)
        if lauf.get("nummer") == pub_n and isinstance(lauf.get("dauer"), (int, float)):
            erg["dauer"] = int(lauf["dauer"])
    elif lauf.get("zustand") == "fehlgeschlagen" and lauf.get("nummer") == ges_n:
        erg.update(zustand="fehlgeschlagen", seit=lauf.get("seit"), grund=lauf.get("grund") or None, grund_art="bau")
    elif rot.get("art") == "software":
        erg.update(zustand="fehlgeschlagen", seit=rot.get("seit"), grund=rot.get("tests") or None, grund_art="software")
    elif lauf.get("zustand") == "baut" and lauf.get("nummer") == ges_n:
        erg.update(zustand="baut", seit=lauf.get("seit"))
    else:
        erg.update(zustand="wartet", seit=ges_zeit)
    if erg["dauer"] is None and erg["zustand"] in ("wartet", "baut") and (t := zeit_lesen(ges_zeit)):
        erg["dauer"] = max(0, int((jetzt - t).total_seconds()))
    erg["ueber_ziel"] = erg["dauer"] is not None and erg["dauer"] > ZIEL_SEKUNDEN
    return erg


def enthalten(zustand, n):
    """Ist Stand n veröffentlicht? -> True, False oder None (unbekannt)."""
    pub = (zustand.get("veroeffentlicht") or {}).get("nummer")
    if not isinstance(n, int) or pub is None:
        return None
    return n <= pub
