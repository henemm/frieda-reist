"""Leitplanke: Was der Konnektor beim Verbindungsaufbau und in tools/list einer englischen Person zeigt, enthält kein deutsches Wort
(ADR-0006, Rückfall ist Englisch): Werkzeugnamen, Parameternamen (auch verschachtelt), Aufzählungswerte, Beschreibungen und die Anweisungen
(initialize). Die Beispielreise ist deutsch; ihr Titel und ihre Namen sind Inhalt der Reise und zählen nicht."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest  # noqa: E402

import konnektor as kn  # noqa: E402
from englisch_hilfe import BEZEICHNER, deutsche_woerter  # noqa: E402
from test_konnektor import BEISPIEL, seiten  # noqa: E402,F401  (seiten: Fixture)

# Eigennamen aus den Beispielen der Beschreibungen (Orte, Anbieter, Pensionen), keine deutschen Wörter
EIGENNAMEN = frozenset({"elbblick", "eurowings", "refugi", "pnr", "ryokan", "carrer", "lluna", "ller", "popup", "sóller", "soller", "münster", "allgäu", "pdfs", "webcal"})
# Bekannte Schuld: {Ort: [Wörter]}. Darf nur kürzer werden; Ziel ist eine leere Liste.
BEKANNT = {}


def _beschreibungen(x, pfad, aus):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "description" and isinstance(v, str):
                aus[pfad + ".description"] = v
            else:
                if k in ("properties",) and isinstance(v, dict):
                    for p in v:
                        aus[pfad + f".{p}#name"] = p.replace("_", " ")
                if k == "enum" and isinstance(v, list):
                    for w in v:
                        if isinstance(w, str):
                            aus[pfad + f".enum:{w}"] = w.replace("_", " ")
                _beschreibungen(v, pfad + "." + k, aus)
    elif isinstance(x, list):
        for i, e in enumerate(x):
            _beschreibungen(e, pfad, aus)


def _funde(texte_je_ort, erlaubt):
    funde = {}
    for ort, t in texte_je_ort.items():
        w = deutsche_woerter(t, erlaubt)
        if w:
            funde[ort] = w
    return funde


def _vergleichen(funde):
    gefunden = {o: set(w) for o, w in funde.items()}
    neu = {o: sorted(w - set(BEKANNT.get(o, ()))) for o, w in gefunden.items() if w - set(BEKANNT.get(o, ()))}
    assert not neu, f"deutsche Wörter in der englischen Schnittstelle: {neu}"
    behoben = {o: sorted(set(w) - gefunden.get(o, set())) for o, w in BEKANNT.items() if set(w) - gefunden.get(o, set())}
    assert not behoben, f"behoben, bitte aus BEKANNT streichen: {behoben}"


@pytest.fixture
def zugang(seiten, monkeypatch):
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    monkeypatch.setenv("KN_SCHREIBDIENST", "http://127.0.0.1:9")   # ohne Schreibweg gäbe es die Schreibwerkzeuge nicht
    return {"reise": "beispielreise", "person": "ida", "sprache": "en"}


def _antwort(zugang, methode):
    a = kn.antwort_auf(zugang, {"jsonrpc": "2.0", "id": 1, "method": methode, "params": {}})
    return a["result"]


def test_tools_list_einer_englischen_person_ohne_deutsches_wort(zugang):
    erlaubt = BEZEICHNER | EIGENNAMEN | {"ida", "karl"}
    texte_je_ort = {}
    for w in _antwort(zugang, "tools/list")["tools"]:
        texte_je_ort[w["name"] + "#name"] = w["name"].replace("_", " ")
        texte_je_ort[w["name"] + ".description"] = w["description"]
        aus = {}
        _beschreibungen(w["inputSchema"], w["name"], aus)
        texte_je_ort.update(aus)
    assert len(texte_je_ort) > 500
    _vergleichen(_funde(texte_je_ort, erlaubt))


def test_anweisungen_einer_englischen_person_ohne_deutsches_wort(zugang, seiten):
    """initialize: die Anweisungen für die KI. Titel und Untertitel der (deutschen) Beispielreise stehen darin als Inhalt der Reise."""
    anweisung = _antwort(zugang, "initialize")["instructions"]
    d = kn.daten("beispielreise")["reise"]
    for inhalt in (d.get("titel"), d.get("untertitel")):
        if inhalt:
            anweisung = anweisung.replace(inhalt, "")
    funde = _funde({"instructions": anweisung}, BEZEICHNER | EIGENNAMEN | {"ida", "karl"})
    assert not funde, f"deutsche Wörter in den Anweisungen: {funde}"


def test_konto_zugang_einer_englischen_person_ohne_deutsches_wort(seiten, monkeypatch):
    """Der Zugang über das Konto (Frieda): Konto-Werkzeuge, Reise-Werkzeuge mit Angabe der Reise und Anweisungen."""
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    monkeypatch.setenv("KN_SCHREIBDIENST", "http://127.0.0.1:9")
    konto = {"id": "K-1", "name": "Ida", "email": "ida@example.invalid", "sprache": "en"}
    monkeypatch.setattr(kn, "reisen_des_kontos", lambda k: [("beispielreise", "ida", kn.daten("beispielreise"))])
    monkeypatch.setattr(kn.konten, "recht", lambda k, r: True)
    erlaubt = BEZEICHNER | EIGENNAMEN | {"ida", "karl"}
    anweisung = kn.anleitung_frieda(konto, "en")
    d = kn.daten("beispielreise")["reise"]
    for inhalt in (d.get("titel"), d.get("untertitel")):
        if inhalt:
            anweisung = anweisung.replace(inhalt, "")
    je_ort = {"instructions": re.sub("(?i)beispielreise", "", kn.schnittstelle.namen_im_text(anweisung))}   # Ordnername der Reise
    werkzeuge = kn.schnittstelle.aussen(kn.lokalisiert(kn.frieda_werkzeuge(konto), "en"))
    assert len(werkzeuge) > 40
    for w in werkzeuge:
        je_ort[w["name"] + "#name"] = w["name"].replace("_", " ")
        je_ort[w["name"] + ".description"] = w["description"]
        aus = {}
        _beschreibungen(w["inputSchema"], w["name"], aus)
        je_ort.update(aus)
    funde = _funde(je_ort, erlaubt)
    assert not funde, f"deutsche Wörter im Konto-Zugang: {funde}"
