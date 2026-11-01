"""Erkennung deutscher Wörter in Text, den eine Person mit englischer Sprache sieht (Leitplanke: Englisch ist immer der Rückfall).

Ein Wort gilt als deutsch, wenn es kein englisches Wort ist und im deutschen Wörterbuch (pyspellchecker) oder im deutschen Katalog
der Software vorkommt. Wörter, die in beiden Sprachen gelten (Hotel, Name, Status, Plan), zählen nicht."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import texte  # noqa: E402
from spellchecker import SpellChecker  # noqa: E402

_WORT = re.compile(r"[A-Za-zÄÖÜäöüß]{3,}")
_EN = SpellChecker(language="en")
_DE = SpellChecker(language="de")
_KATALOG = None


def _katalog_woerter():
    global _KATALOG
    if _KATALOG is None:
        _KATALOG = {w.lower() for v in texte.sprache("de").TEXTE.values() for w in _WORT.findall(re.sub(r"\{\w+\}", "", v))}
        _KATALOG = {w for w in _KATALOG if w not in _EN}
    return _KATALOG


def deutsche_woerter(text, erlaubt=frozenset()):
    """Die deutschen Wörter in text (kleingeschrieben, ohne die erlaubten), in der Reihenfolge ihres Auftretens."""
    gefunden = []
    for w in _WORT.findall(re.sub(r"\{\w+\}", "", text or "")):
        w = w.lower()
        if w in erlaubt or w in gefunden or w in _EN:
            continue
        if w in _DE or w in _katalog_woerter():
            gefunden.append(w)
    return gefunden


# Wörter, die keine deutsche Sprache sind, sondern Namen von Dateien, Formaten, Produkten und Beispielen im englischen Text
BEZEICHNER = frozenset({
    "yaml", "json", "pdf", "jpeg", "png", "webp", "heic", "txt", "https", "http", "url", "app", "adr", "pmtiles", "openstreetmap", "gpx",
    "repo", "frieda", "claude", "rrggbb", "kontext", "herkunft", "reise", "inhalt", "wissen", "plan", "ids", "routen", "arten", "kategorien",
    "wuensche", "offene", "fragen", "ontologie", "rueckmeldungen", "einladungen", "auftraege", "reisen", "produkt", "abschnitte",
})


def ohne_schluessel(text):
    """Dateitext ohne die Schlüssel von YAML-Zeilen (Schlüssel sind das Datenformat, nicht Text für Personen); Rest unverändert."""
    zeilen = []
    for z in text.splitlines():
        m = re.match(r"^\s*(?:-\s+)?[\w.-]+:(?:\s+(.*))?$", z)
        zeilen.append((m.group(1) or "") if m and not z.lstrip().startswith("#") else z)
    return "\n".join(zeilen)


def datenformat():
    """Wörter des Datenformats der Reise (Schlüssel und Werte in den Dateien, Parameternamen): sie bleiben deutsch (ADR-0006), stehen aber in
    Dateien, die die Software schreibt. In Antworten und Commit-Nachrichten sind sie nicht erlaubt."""
    import schnittstelle
    woerter = set()
    for name in [*schnittstelle.PARAMETER, *schnittstelle.NAMEN.values(), *schnittstelle.ENUM_ALIAS.values()]:
        woerter.update(w.lower() for w in re.split(r"[^A-Za-zÄÖÜäöüß]+", name) if len(w) >= 3)
    woerter.update(k[len("wert."):].lower() for k in texte.sprache("de").TEXTE if k.startswith("wert."))   # gespeicherte Datenwerte
    woerter.update({"aufenthalt", "bewegung", "folge", "blau", "braun", "lila", "gruen", "tuerkis", "oliv", "grau", "rosa", "schiefer", "kontrast",
                    "geld", "beispiel", "beispielreise", "veraenderlich", "stufe", "hilfe", "typ", "preis", "merkmale", "grundform"})
    return frozenset(woerter)
