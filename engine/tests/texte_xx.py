"""Pseudo-Sprache nur für Tests (ADR-0006, Punkt 9). Sie hat absichtlich andere Eigenschaften als Deutsch und Englisch:
andere Ziffern (ar-EG), Schreibrichtung rtl, sechs Pluralkategorien, jeder Text markiert. Geladen über
FR_TEXTE_ZUSATZ=xx, wenn engine/tests im Suchpfad liegt. Sie beweist bei jedem Lauf, dass eine neue Sprache
eine Datei ist und keine Codeänderung."""
import texte_en

NAME = "Pseudo"
LOCALE = "ar-EG"
RICHTUNG = "rtl"
DATUM = texte_en.DATUM
DATUM_KURZ = texte_en.DATUM_KURZ
ZEIT = texte_en.ZEIT
DATUM_ZEIT = texte_en.DATUM_ZEIT
WOCHENTAGE_KURZ = tuple(f"[xx {w}]" for w in texte_en.WOCHENTAGE_KURZ)


def PLURAL(n):
    """Arabische Regel nach CLDR: zero, one, two, few, many, other."""
    if n == 0:
        return "zero"
    if n == 1:
        return "one"
    if n == 2:
        return "two"
    if 3 <= n % 100 <= 10:
        return "few"
    if 11 <= n % 100 <= 99:
        return "many"
    return "other"


TEXTE = {k: f"[xx {v}]" for k, v in texte_en.TEXTE.items()}
# Wo Englisch nur one/other kennt, gibt die Pseudo-Sprache jeder weiteren Kategorie einen eigenen, erkennbaren Text:
# so zeigt ein Test, ob der Code die Kategorie wirklich über PLURAL wählt.
for _k, _v in list(TEXTE.items()):
    if _k.endswith(".other"):
        for _kat in ("zero", "two", "few", "many"):
            TEXTE[_k[:-len("other")] + _kat] = _v.replace("[xx ", f"[xx {_kat} ", 1)
