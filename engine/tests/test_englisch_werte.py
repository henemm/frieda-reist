"""Leitplanke: Datenwerte, Werkzeug- und Parameternamen erscheinen in einer englischen Reise nur englisch (ADR-0006, docs/sprachen.md).

Spielt die Aufrufe der Schreibwerkzeuge aus aufrufe_schreiben.json (gesammelt aus test_schreiben.py) in der Beispielreise mit Sprache en
durch und sucht in Antworten, Ablehnungen und Commit-Nachrichten nach den deutschen Wörtern der Schnittstelle: Datenwerte (wert.* im
Katalog), interne Werkzeugnamen und interne Parameternamen in Anführungszeichen. Inhalte, die die Person selbst eingegeben hat, zählen nicht.
Die Liste BEKANNT darf nur kürzer werden."""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest  # noqa: E402,F401

import schnittstelle  # noqa: E402
import schreiben as sb  # noqa: E402
import texte  # noqa: E402
from test_englisch import am_rand  # noqa: E402
from test_schreiben import BEISPIEL, IDA, KARL, git, repo, schreiber  # noqa: E402,F401

AUFRUFE = json.loads((Path(__file__).resolve().parent / "aufrufe_schreiben.json").read_text(encoding="utf-8"))

# Wörter, die zugleich englisch (oder Name) sind und deshalb nicht gesucht werden
GLEICH = {"text", "plan", "bus", "taxi", "ticket", "museum", "link", "normal", "auto", "name", "status", "hotel"}


def deutsche_werte():
    woerter = {k[len("wert."):] for k in texte.sprache("de").TEXTE if k.startswith("wert.")}
    return {w for w in woerter if w.lower() not in GLEICH and texte.datenwert("en", w) != w}


def schnittstellenwoerter():
    """Deutsche Wörter der Schnittstelle, die eine Person mit englischer Sprache nicht lesen soll."""
    muster = [r"(?<![\w./-])(" + "|".join(sorted(map(re.escape, deutsche_werte()), key=len, reverse=True)) + r")(?![\w-]|\.(?:md|yaml))"]
    werkzeuge = [n for n in schnittstelle.NAMEN.values() if "_" in n or n == "ueberblick"]
    muster.append(r"(?<![\w.-])(" + "|".join(sorted(map(re.escape, werkzeuge), key=len, reverse=True)) + r")(?![\w-])")
    parameter = [p for p, e in schnittstelle.PARAMETER.items() if p != e]
    muster.append(r"[„“\"](" + "|".join(sorted(map(re.escape, parameter), key=len, reverse=True)) + r")[“”\"]")
    return [re.compile(m) for m in muster]


def eingaben(x):
    """Alle Wörter der Texte, die die Person selbst eingegeben hat (Werte der Argumente, die keine Datenwerte sind)."""
    if isinstance(x, dict):
        return set().union(*(eingaben(v) for v in x.values())) if x else set()
    if isinstance(x, list):
        return set().union(*(eingaben(v) for v in x)) if x else set()
    if isinstance(x, str) and x not in deutsche_werte():
        return set(re.findall(r"[\wäöüÄÖÜß-]+", x))
    return set()


def funde(text, args, muster):
    gefunden = []
    eigen = eingaben(args)
    for m in muster:
        for tr in m.finditer(text or ""):
            f = tr.group(1)
            if f not in eigen and f not in gefunden:
                gefunden.append(f)
                if os.environ.get("ZZ_FUNDE"):
                    with open(os.environ["ZZ_FUNDE"], "a", encoding="utf-8") as d:
                        d.write(f"{f}\t{text[max(0, tr.start() - 70):tr.end() + 50]!r}\n")
    return gefunden


# Bekannte Schuld je Werkzeug (Wörter). Darf nur kürzer werden.
BEKANNT = {}


def test_englische_reise_zeigt_keinen_deutschen_datenwert(repo):
    wurzel, origin, arbeit, _ = repo
    yaml = wurzel / "reisen" / "beispielreise" / "reise.yaml"
    text = yaml.read_text(encoding="utf-8")
    yaml.write_text(re.sub(r"(?m)^sprache:.*\n", "", text) + "sprache: en\n", encoding="utf-8")
    git(wurzel, "add", "-A")
    git(wurzel, "commit", "-q", "-m", "Beispielreise englisch")
    git(wurzel, "push", "-q", "origin", "main")
    s = schreiber(repo)
    muster = schnittstellenwoerter()
    gefunden = {}
    for zeile, werkzeug, wer, args in AUFRUFE:
        if werkzeug == "alles_loeschen":
            continue
        s.vorbereiten()
        antwort = IDA if wer == "IDA" else KARL
        try:
            a = s.schreiben("beispielreise", werkzeug, {**antwort, "args": args})
            text_an = am_rand(texte.Satz.aus_json(a["text_teile"]).text("en")) if a.get("text_teile") else am_rand(str(a.get("text")))
            commit = git(origin, "log", "-1", "--format=%B", "main")
            f = funde(text_an, args, muster) + [x for x in funde(commit, args, muster) if x not in funde(text_an, args, muster)]
        except sb.Ablehnung as e:
            f = funde(am_rand(e.text("en")), args, muster)
        if f:
            gefunden.setdefault(werkzeug, set()).update(f)
    neu = {w: sorted(x - BEKANNT.get(w, set())) for w, x in gefunden.items() if x - BEKANNT.get(w, set())}
    assert not neu, f"deutsche Wörter der Schnittstelle in einer englischen Reise: {neu}"
    behoben = {w: sorted(x - gefunden.get(w, set())) for w, x in BEKANNT.items() if x - gefunden.get(w, set())}
    assert not behoben, f"behoben, bitte aus BEKANNT streichen: {behoben}"
