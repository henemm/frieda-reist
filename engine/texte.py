"""Zugriff auf die Textkataloge der Software (ADR-0006, docs/mehrsprachigkeit.md).

Jede Sprache ist eine Datei engine/texte_<kürzel>.py mit NAME, LOCALE, RICHTUNG, PLURAL, DATUM, DATUM_KURZ, ZEIT und TEXTE.
Dieses Modul kennt keine Sprache beim Namen: SPRACHEN ist die Liste der Dateien (de, en und alles aus
FR_TEXTE_ZUSATZ, kommagetrennt, Modul aus dem Suchpfad; die Tests laden so eine Pseudo-Sprache).
"""
import datetime
import importlib
import os
import re

BASIS = ("de", "en")
VORGABE = "en"          # Sprache einer Person, deren Wunsch nicht erkennbar ist; Reisen ohne Feld sprache bauen mit "de"
VORGABE_REISE = "de"
PFLICHTFELDER = ("NAME", "LOCALE", "RICHTUNG", "PLURAL", "DATUM", "DATUM_KURZ", "ZEIT", "WOCHENTAGE_KURZ", "TEXTE")
KATEGORIEN = ("zero", "one", "two", "few", "many", "other")   # Pluralkategorien nach CLDR

_module = {}


def _zusatz():
    return tuple(k.strip() for k in os.environ.get("FR_TEXTE_ZUSATZ", "").split(",") if k.strip())


def sprachen():
    """Die Sprachen der Software in der Reihenfolge ihrer Dateien (de, en, dann die Zusätze)."""
    return BASIS + tuple(k for k in _zusatz() if k not in BASIS)


def __getattr__(name):
    """texte.SPRACHEN wird bei jedem Zugriff gelesen, damit eine Umgebungsvariable der Tests sofort gilt."""
    if name == "SPRACHEN":
        return sprachen()
    raise AttributeError(name)


def sprache(kuerzel):
    """Das Modul einer Sprache oder None, wenn es sie nicht gibt."""
    if kuerzel not in sprachen():
        return None
    if kuerzel not in _module:
        _module[kuerzel] = importlib.import_module(f"texte_{kuerzel}")
    return _module[kuerzel]


def gueltig(kuerzel):
    return kuerzel in sprachen()


def _fuellen(text, werte):
    try:
        return text.format(**werte)
    except (KeyError, IndexError, ValueError):
        return text   # nie ein Absturz wegen eines Textes


def plural(kuerzel, n):
    """Pluralkategorie von n in dieser Sprache (zero, one, two, few, many, other)."""
    modul = sprache(kuerzel) or sprache(VORGABE)
    return modul.PLURAL(n)


def t(kuerzel, schluessel, **werte):
    """Text zu einem Schlüssel in der Sprache. Gibt es den Wert n, wählt PLURAL die Kategorie (Schlüssel.<kategorie>, Rückfall
    Schlüssel.other, dann Schlüssel). Fehlt der Schlüssel, gilt Englisch, dann kommt der Schlüssel selbst zurück."""
    for k in (kuerzel, VORGABE):
        modul = sprache(k)
        if modul is None:
            continue
        kandidaten = [schluessel]
        if "n" in werte:
            kandidaten = [f"{schluessel}.{modul.PLURAL(werte['n'])}", f"{schluessel}.other", schluessel]
        for kandidat in kandidaten:
            if kandidat in modul.TEXTE:
                return _fuellen(modul.TEXTE[kandidat], werte)
    return schluessel


def gruppe(kuerzel, praefix):
    """Alle Texte unter einem Präfix als Wörterbuch Rest-des-Schlüssels -> Text (mit Rückfall auf Englisch je Eintrag)."""
    ergebnis = {}
    for k in (VORGABE, kuerzel):   # erst Englisch, dann die Sprache: deren Texte überschreiben
        modul = sprache(k)
        if modul is not None:
            ergebnis.update({s[len(praefix) + 1:]: v for s, v in modul.TEXTE.items() if s.startswith(praefix + ".")})
    return ergebnis


def aus_header(wert):
    """Beste Sprache aus einem Accept-Language-Header (q-Werte, Region abgeschnitten: de-AT -> de), sonst VORGABE."""
    kandidaten = []
    for i, teil in enumerate(str(wert or "").split(",")):
        felder = [f.strip() for f in teil.split(";")]
        tag = felder[0].lower()
        if not tag or tag == "*":
            continue
        q = 1.0
        for f in felder[1:]:
            m = re.fullmatch(r"q\s*=\s*([0-9.]+)", f)
            if m:
                try:
                    q = float(m.group(1))
                except ValueError:
                    q = 0.0
        kandidaten.append((-q, i, tag.split("-")[0]))
    for _, _, tag in sorted(kandidaten):
        if gueltig(tag):
            return tag
    return VORGABE


def _datum(d):
    if isinstance(d, str):
        d = datetime.date.fromisoformat(d[:10])
    return d


def datum(d, kuerzel):
    """Datum mit Jahr in der Form der Sprache (Deutsch 13.5.2027, Englisch 13/5/2027)."""
    return _datum(d).strftime((sprache(kuerzel) or sprache(VORGABE)).DATUM)


def datum_kurz(d, kuerzel):
    """Datum ohne Jahr (Deutsch 13.5., Englisch 13/5)."""
    return _datum(d).strftime((sprache(kuerzel) or sprache(VORGABE)).DATUM_KURZ)


def wochentag(d, kuerzel):
    """Kurzer Wochentag (Deutsch Do, Englisch Thu) aus der Sprachdatei; strftime hängt an der Sprache des Rechners und taugt nicht."""
    return (sprache(kuerzel) or sprache(VORGABE)).WOCHENTAGE_KURZ[_datum(d).weekday()]


def zeit(z, kuerzel):
    """Uhrzeit (datetime.time oder datetime) in der Form der Sprache."""
    return z.strftime((sprache(kuerzel) or sprache(VORGABE)).ZEIT)


def seite():
    """Katalog aller Sprachen für die Seite (liegt offline in der Seite, damit der Umschalter ohne Netz geht)."""
    ergebnis = {}
    for k in sprachen():
        modul = sprache(k)
        ergebnis[k] = {"name": modul.NAME, "locale": modul.LOCALE, "richtung": modul.RICHTUNG,
                       "datum": modul.DATUM, "datum_kurz": modul.DATUM_KURZ, "zeit": modul.ZEIT,
                       "texte": {s: v for s, v in modul.TEXTE.items() if s.startswith("seite.")}}
    return ergebnis


def inhaltswoerter(schluessel):
    """Die Wörter, die ein Schlüssel in allen Sprachen hat (für die Erkennung von Inhalt, der in irgendeiner Sprache geschrieben ist)."""
    woerter = set()
    for k in sprachen():
        text = sprache(k).TEXTE.get(schluessel)
        if text:
            woerter.add(text)
    return woerter
