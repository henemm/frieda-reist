"""Hilfe für Tests, die die Werkzeugliste des Konnektors lesen (ADR-0006, M8b): tools/list zeigt englische Namen, die Tests prüfen
mit den internen (deutschen) Namen. Die Mengenvergleiche werden über die Namenstabelle abgebildet, nicht umgeschrieben."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import schnittstelle  # noqa: E402


def intern_liste(ergebnis):
    """Ergebnis von tools/list: jedes Werkzeug trägt zusätzlich den Namen, den der Client sieht (name_aussen); name ist der interne."""
    for w in (ergebnis or {}).get("tools", []):
        w["name_aussen"] = w["name"]
        w["name"] = schnittstelle.intern_name(w["name"])
    return ergebnis


def N(text):
    """Text so, wie ihn der Konnektor nach außen sagt (Werkzeugnamen englisch)."""
    return schnittstelle.namen_im_text(text)
