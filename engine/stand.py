"""Reise-Stand (Epic #223): eine fortlaufende Nummer je Reise und der Weg eines Stands vom Sichern bis auf die Seite.

Nummer: die Zahl der Commits, die den Ordner der Reise ändern (git rev-list --count HEAD -- <ordner>). Jeder gesicherte
Schreibvorgang ist ein Commit in reisen/<reise>/ und erhöht sie um 1; ein Software-Update (Submodul frieda/) ändert den
Ordner nicht und lässt sie stehen. main wächst nur (vorspulen, docs/betrieb.md), deshalb steigt die Nummer und Stand 43
enthält alles aus Stand 42. Die Nummer gehört zur Reise, nicht zum Bau: Der Bau liest sie nur ab. In einem flachen Klon
wäre die Zahl falsch und fehlt deshalb; ohne Git fehlt sie auch.

Weg eines Stands (docs/betrieb.md, „Reise-Stand“):
  gesichert      der Schreibweg (engine/schreiben.py) hat den Commit nach main gebracht
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
import json
import os
import re
import subprocess
from pathlib import Path

import instanz

ZIEL_SEKUNDEN = 120          # Zeitziel vom Sichern bis zur Veröffentlichung (Product Owner, E3, 2.11.2026)
AENDERUNGEN = 10             # so viele letzte Änderungen zeigt die Seite
ZUSTAENDE = ("wartet", "baut", "veroeffentlicht", "fehlgeschlagen")
ID_MUSTER = re.compile(r"(?<![\w-])([A-Z]{1,2}-\d+(?:\.[a-z0-9]+)?)(?![\w-])")
PERSON_TRAILER = "Frieda-Person"   # Zeile im Commit des Schreibwegs: wer den Eintrag gemacht hat


def git(ordner, *args):
    """git im Ordner -> Ausgabe ohne Rand oder None (kein Git, Fehler)."""
    try:
        r = subprocess.run(["git", "-C", str(ordner), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def nummer(ordner, rev="HEAD"):
    """Reise-Stand des Ordners auf rev -> int oder None (ohne Git, flacher Klon, nichts eingecheckt)."""
    if not Path(ordner).is_dir() or git(ordner, "rev-parse", "--is-shallow-repository") != "false":
        return None
    n = git(ordner, "rev-list", "--count", rev, "--", ".")
    return int(n) if n and n.isdigit() and int(n) > 0 else None


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


def _person(nachricht, autor):
    """Wer eine Änderung gemacht hat: die Zeile Frieda-Person des Schreibwegs, sonst der Autor des Commits."""
    for z in reversed(nachricht.splitlines()):
        if z.startswith(PERSON_TRAILER + ":"):
            return z.split(":", 1)[1].strip() or None
    return autor or None


def aenderungen(ordner, namen=None, n=AENDERUNGEN):
    """Die letzten n Änderungen der Reise -> [{nummer, zeit, was, wer}], neueste zuerst. was ist die erste Zeile des Commits
    ohne den Titel der Reise davor, mit Namen statt Kennungen."""
    gesamt = nummer(ordner)
    if not gesamt:
        return []
    roh = git(ordner, "log", f"-{n}", "--format=%ct%x1f%an%x1f%B%x1e", "--", ".")
    if not roh:
        return []
    liste = []
    for i, eintrag in enumerate(x for x in roh.split("\x1e") if x.strip()):
        teile = eintrag.strip("\n").split("\x1f", 2)
        if len(teile) != 3 or not teile[0].strip().isdigit():
            continue
        zeit, autor, nachricht = int(teile[0].strip()), teile[1].strip(), teile[2].strip()
        was = (nachricht.splitlines() or [""])[0]
        if ": " in was:   # „<Titel der Reise>: <was>“ (Schreibweg)
            was = was.split(": ", 1)[1]
        liste.append({"nummer": gesamt - i, "zeit": zeit_iso(zeit), "was": ohne_kennungen(was, namen or {}),
                      "wer": _person(nachricht, autor)})
    return liste


def fuer_seite(ordner, daten):
    """Reise-Stand für die Seite (daten.reise_stand): {nummer, zeit, aenderungen} oder None ohne Git. zeit ist der Zeitpunkt
    der letzten Änderung (Commit). Keine Bauzeit: gleicher Inhalt ergibt dieselbe Seite (Service Worker, bauen.py)."""
    n = nummer(ordner)
    if n is None:
        return None
    liste = aenderungen(ordner, namen_der_ids(daten))
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
