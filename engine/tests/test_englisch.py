"""Leitplanke: Wer die Sprache nicht auf Deutsch gestellt hat, liest kein deutsches Wort (ADR-0006, Rückfall ist Englisch).

Ein durchgängiger Lauf in einer englischen Reise: Antworten, Commit-Nachrichten und alles, was die Software in Dateien der Reise schreibt,
dürfen kein deutsches Wort enthalten (engine/tests/englisch_hilfe.py). Die Schuldenlisten unten dürfen nur kürzer werden."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest  # noqa: E402,F401

import schnittstelle  # noqa: E402
import schreiben as sb  # noqa: E402
import texte  # noqa: E402
from englisch_hilfe import BEZEICHNER, datenformat, deutsche_woerter, ohne_schluessel  # noqa: E402
from test_schreiben import git, repo, schreiber  # noqa: E402,F401  (repo: Fixture)

NAMEN = {"ida", "karl"}   # Personen der Tests


def am_rand(text):
    """Wie der Konnektor einen Text dem Client gibt: Werkzeug- und Parameternamen so, wie tools/list sie zeigt."""
    return schnittstelle.parameter_im_text(schnittstelle.namen_im_text(text, streng=True))


def _auftrag(pfad="coast-trip-2027"):
    return {"id": "A-20261029-120000-abcd", "erstellt": "2026-10-29T12:00:00+00:00", "name": "Ida", "art": "Auftrag",
            "daten": {"neue_reise": {"titel": "Coast trip", "von": "2027-02-06", "bis": "2027-02-13", "ziel": "Dover", "pfad": pfad,
                                     "sprache": "en", "personen": {"ida": {"name": "Ida", "rolle": "organisator"},
                                                                    "karl": {"name": "Karl", "rolle": "mitwirkend"}},
                                     "wer": "Ida", "notiz": "Idea from the chat."}}}


def test_neue_englische_reise_enthaelt_kein_deutsches_wort(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("coast-trip-2027", "reise_anlegen", {"person": None, "name": "Ida", "rolle": "organisator", "args": {"auftrag": _auftrag()}})
    funde = {}
    erlaubt = NAMEN | BEZEICHNER
    erlaubt_datei = erlaubt | datenformat()   # Dateien der Reise nennen das Datenformat, Antworten und Commits nicht
    # Antwort an die Person, in ihrer Sprache gesetzt
    assert a.get("text_teile")
    funde["antwort"] = deutsche_woerter(texte.Satz.aus_json(a["text_teile"]).text("en"), erlaubt)
    funde["commit"] = deutsche_woerter(git(origin, "log", "-1", "--format=%B", "main"), erlaubt)
    for f in git(origin, "ls-tree", "-r", "--name-only", "main", "reisen/coast-trip-2027").splitlines():
        if f.endswith((".png", ".svg", ".jpg", ".gpx", ".pmtiles")):
            continue
        funde[f] = deutsche_woerter(ohne_schluessel(git(origin, "show", f"main:{f}")), erlaubt_datei)
    funde = {k: v for k, v in funde.items() if v}
    assert not funde, f"deutsche Wörter in einer englischen Reise: {funde}"


def _funde_des_letzten_commits(origin, antwort, erlaubt_text, erlaubt_datei):
    """Deutsche Wörter in Antwort, Commit-Nachricht und den hinzugefügten Zeilen des letzten Commits auf main."""
    funde = {}
    if antwort.get("text_teile"):
        funde["antwort"] = deutsche_woerter(am_rand(texte.Satz.aus_json(antwort["text_teile"]).text("en")), erlaubt_text)
    else:
        funde["antwort"] = deutsche_woerter(am_rand(str(antwort.get("text"))), erlaubt_text)
    funde["commit"] = deutsche_woerter(git(origin, "log", "-1", "--format=%B", "main"), erlaubt_text)
    diff = git(origin, "show", "-U0", "--format=", "main")
    neu = "\n".join(z[1:] for z in diff.splitlines() if z.startswith("+") and not z.startswith("+++"))
    funde["dateien"] = deutsche_woerter(ohne_schluessel(neu), erlaubt_datei)
    funde = {k: v for k, v in funde.items() if v}
    if funde.get("dateien"):   # die Zeilen dazu, damit ein Fund in der Meldung steht und nicht gesucht werden muss
        funde["zeilen"] = [z for z in neu.splitlines() if deutsche_woerter(ohne_schluessel(z), erlaubt_datei)][:6]
    return funde


# Bekannte Schuld: deutsche Wörter, die eine englische Reise noch zeigt (Datenwerte wie Rollen, Stufen, Typen, Farben, Baustein-Namen und
# Bezeichner in Commit-Texten). Die Liste darf nur kürzer werden: ein neues deutsches Wort lässt den Test scheitern, ein behobenes muss
# hier gestrichen werden. Ziel ist eine leere Liste.
BEKANNT = {}


def _vergleichen(alle):
    """alle: {Werkzeug: {Ort: [Wörter]}} gegen BEKANNT: Neues scheitert, Behobenes muss aus BEKANNT gestrichen werden."""
    gefunden = {w: {o: set(x) for o, x in orte.items()} for w, orte in alle.items()}
    neu = {w: {o: sorted(x - BEKANNT.get(w, {}).get(o, set())) for o, x in orte.items() if x - BEKANNT.get(w, {}).get(o, set())}
           for w, orte in gefunden.items()}
    neu = {w: o for w, o in neu.items() if o}
    assert not neu, f"neue deutsche Wörter in einer englischen Reise: {neu}"
    behoben = {w: {o: sorted(x - gefunden.get(w, {}).get(o, set())) for o, x in orte.items() if x - gefunden.get(w, {}).get(o, set())}
               for w, orte in BEKANNT.items()}
    behoben = {w: o for w, o in behoben.items() if o}
    assert not behoben, f"behoben, bitte aus BEKANNT streichen: {behoben}"


def test_englische_reise_schreibwerkzeuge_ohne_deutsches_wort(repo):
    """Die Schreibwerkzeuge in einer englischen Reise, mit englischen Eingaben: was die Person liest, was in den Commit und was in die
    Dateien der Reise kommt, enthält kein deutsches Wort."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    s.schreiben("coast-trip-2027", "reise_anlegen", {"person": None, "name": "Ida", "rolle": "organisator", "args": {"auftrag": _auftrag()}})
    s.vorbereiten()
    ida = {"person": "ida", "name": "Ida", "rolle": "organisator"}
    erlaubt_text = NAMEN | BEZEICHNER
    erlaubt_datei = erlaubt_text | datenformat()
    aufrufe = [
        ("wissen_schreiben", {"titel": "Ferries", "text": "Ferries run every hour.", "quelle": "Ferry timetable", "gruppe": "wissen"}),
        ("art_definieren", {"bezeichnung": "Inn", "grundform": "aufenthalt", "beschreibung": "a small inn", "grund": "first kind"}),
        ("kategorie_definieren", {"kategorie": "viewpoint", "bezeichnung": "Viewpoints", "gruppe": "punkt", "farbe": "#336699", "symbol": "karte"}),
        ("merkmal_definieren", {"art": "inn", "bezeichnung": "Breakfast", "typ": "auswahl", "werte": ["included", "extra", "none"], "grund": "needed"}),
        ("ding_anlegen", {"was": "ort", "titel": "Dover", "quelle": "Map", "hinweis": "Harbour town"}),
        ("frage_anlegen", {"text": "Is the inn open in May?", "bis": "March 2027"}),
        ("person_schreiben", {"schluessel": "anna", "vorname": "Anna", "rolle": "mitwirkend"}),
        ("einstellung_setzen", {"regeln": {"einladen": "organisator"}, "grund": "only organisers invite"}),
    ]
    alle = {}
    for werkzeug, args in aufrufe:
        a = s.schreiben("coast-trip-2027", werkzeug, {**ida, "args": args})
        funde = _funde_des_letzten_commits(origin, a, erlaubt_text, erlaubt_datei)
        if funde:
            alle[werkzeug] = funde
        s.vorbereiten()
    # Ablehnungen: dieselben Werkzeuge mit Eingaben, die die Prüfung zurückweist (Pflichtfeld fehlt, unbekannte ID, falscher Wert)
    ablehnungen = [("art_definieren", {}), ("kategorie_definieren", {}), ("merkmal_definieren", {"art": "nope"}), ("ding_anlegen", {"was": "ort"}),
                   ("ding_aendern", {"ziel": "O-99", "quelle": "x"}), ("frage_anlegen", {}), ("person_schreiben", {"schluessel": "Bad Key"}),
                   ("einstellung_setzen", {"sprache": "klingon"}), ("wissen_schreiben", {"titel": "x"}), ("entscheiden", {"option": "V-99.a"}),
                   ("termin_setzen", {"datum": "tomorrow"}), ("tag_anlegen", {}), ("option_anlegen", {"wahlstelle": "V-99"}),
                   ("buchung_anlegen", {}), ("wert_eintragen", {"ziel": "O-99"}), ("lage_eintragen", {"ziel": "O-99"})]
    for werkzeug, args in ablehnungen:
        try:
            s.schreiben("coast-trip-2027", werkzeug, {**ida, "args": args})
        except sb.Ablehnung as e:
            gefunden = deutsche_woerter(am_rand(e.text("en")), erlaubt_text)
            if gefunden:
                alle["Ablehnung " + werkzeug] = {"text": gefunden}
        s.vorbereiten()
    _vergleichen(alle)
