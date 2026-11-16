"""Textformen (#594, Product Owner 16.11.2026): Jedes Textfeld hat genau eine von drei Formen.

  kurz      eine Zeile, keine Formatierung: Titel, Namen, Merkmalswerte, Preise, Fristen. Diese stehen auch in Kacheln,
            auf der Karte, im Kalender und in Meldungen, wo Formatierung stören würde.
  lang      Langtext: Absätze (Leerzeile), Zeilenumbrüche, Aufzählungen, fett, kursiv, Links (Markdown). Keine
            Überschriften, Tabellen, Bilder oder HTML. Für alle, auch für Eingaben der Mitreisenden.
  dokument  Wissen und Lesetexte: alles vom Langtext, dazu Zwischenüberschriften, Tabellen und Bilder (docs/design.md,
            Reisetexte; gebaut in bauen.py).

Dieses Register ist die eine Stelle für Form und Höchstlänge der langen Felder. Der Schreibweg und der Rückmeldedienst prüfen
danach, der Konnektor beschreibt jedes Feld daraus für den AI-Client (konnektor.lokalisiert), die Seite zeigt Langtext über
den Baustein „Langtext“ (Atom, vorlage.html), Kalender und Meldungen nehmen klartext(). Ohne Abhängigkeiten, damit jeder
Dienst es laden kann.
"""
import re

KURZ, LANG, DOKUMENT = "kurz", "lang", "dokument"

# Feld -> (Form, Höchstlänge in Zeichen). Der Name ist fachlich (Grundform.Feld), nicht der Name eines Werkzeugs: mehrere
# Werkzeuge teilen sich ein Feld (day_create und day_update schreiben beide tag.text).
FELDER = {
    "tag.text": (LANG, 4000),
    "wahlstelle.text": (LANG, 2000),
    "option.text": (LANG, 2000),
    "plan.text": (LANG, 2000),
    "frage.text": (LANG, 1000),
    "buchung.storno": (LANG, 400),
    "buchung.notiz": (LANG, 500),
    "gegenstand.notiz": (LANG, 500),
    "wunsch.notiz": (LANG, 600),
    "aufgabe.notiz": (LANG, 2000),
    "aufgabe.kommentar": (LANG, 500),
    "rueckmeldung.text": (LANG, 4000),
    "rueckmeldung.kommentar": (LANG, 4000),
    "wunsch.kommentar": (LANG, 500),
    "antwort.text": (LANG, 4000),
    "merkmal.lang": (LANG, 2000),
    "ding.hinweis": (LANG, 1000),
    "wissen.text": (DOKUMENT, 6000),
    "wissen.aendern": (DOKUMENT, 12000),
    "lesetext.text": (DOKUMENT, 12000),
}

# Langtexte in einer Zeile: fett, kursiv und Links, aber keine Absätze, weil das Feld in einer Tabellenzeile gespeichert wird
# (offene-fragen.md).
EINZEILIG = {"frage.text"}


def form(feld):
    return FELDER[feld][0]


def laenge(feld):
    return FELDER[feld][1]


def schema(feld, beschreibung=None):
    """Eigenschaft im Schema eines Werkzeugs: konnektor.lokalisiert ergänzt die Beschreibung um Form und Länge aus dem Register
    und nimmt die Markierung wieder heraus, bevor die Liste den AI-Client erreicht."""
    if feld not in FELDER:
        raise KeyError(feld)
    e = {"type": "string", "x-textform": feld}
    if beschreibung:
        e["description"] = beschreibung
    return e


# Was ein Langtext nicht enthalten darf (Form „dokument“ oder HTML). Der Schreibweg lehnt es mit dem Namen des Fundes ab;
# Eingaben der Mitreisenden werden nicht abgelehnt, die Seite zeigt solche Zeilen als einfachen Text.
_NICHT_IM_LANGTEXT = (
    ("ueberschrift", re.compile(r"^ {0,3}#{1,6}(\s|$)", re.M)),
    ("tabelle", re.compile(r"^ {0,3}\|.*\|\s*$", re.M)),
    ("bild", re.compile(r"!\[[^\]]*\]\(")),
    ("html", re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(\s[^>]*)?/?>")),
    ("code", re.compile(r"^ {0,3}(```|~~~)", re.M)),
)


def langtext_fund(text):
    """Erstes, was ein Langtext nicht kann -> (Art, Fund) oder None. Arten: ueberschrift, tabelle, bild, html, code."""
    for art, muster in _NICHT_IM_LANGTEXT:
        if (m := muster.search(text or "")):
            return art, m.group(0).strip()[:40]
    return None


def bereinigen(text):
    """Zeilen und Absätze bleiben (Listen und Umbrüche sind Inhalt), bereinigt wird am Zeilenende; mehr als eine Leerzeile
    wird eine."""
    zeilen = [z.rstrip() for z in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(zeilen)).strip()


_LINK = re.compile(r"\[([^\]\n]+)\]\((\S+?)\)")
_FETT = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")
_KURSIV = re.compile(r"(?<![\w*])([*_])(?=\S)(.+?)(?<=\S)\1(?![\w*])")
_LISTE = re.compile(r"^(\s*)[*+]\s+", re.M)
_ESC = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>])")


def klartext(text, eine_zeile=False):
    """Langtext als einfacher Text für Kalender, Meldungen, Kürzungen: ohne Sternchen und Linkklammern, Aufzählungen mit „-“.
    eine_zeile: Absätze und Umbrüche werden „ · “ bzw. Leerzeichen (für eine Zeile in einer Meldung)."""
    if not text:
        return ""
    t = _LINK.sub(lambda m: m.group(1) if m.group(1) == m.group(2) else f"{m.group(1)} ({m.group(2)})", str(text))
    t = _FETT.sub(r"\2", t)
    t = _KURSIV.sub(r"\2", t)
    t = _LISTE.sub(r"\1- ", t)
    t = _ESC.sub(r"\1", t)
    if eine_zeile:
        t = " · ".join(" ".join(a.split()) for a in re.split(r"\n\s*\n", t) if a.strip())
    return t.strip()
