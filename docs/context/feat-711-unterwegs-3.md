# Kontext: feat-711-unterwegs-3 (Issue #711, Etappe 2, Gruppe „Unterwegs und gemeinsam“, Teil 3)

## Auftrag
Unterseite `erinnerungen` (Quelle `docs/funktionen/erinnerungen.md`), DE und EN. Damit hat die Gruppe alle Unterseiten.
Teil 1 und 2: `docs/context/feat-711-unterwegs.md`, `docs/context/feat-711-unterwegs-2.md`.

## Betroffene Dateien
- `engine/anmeldung.py`: ein Eintrag in `INFO_UNTERSEITEN`.
- `engine/texte_de.py`, `engine/texte_en.py`: `info.bereich.erinnerungen.…`.
- `engine/info/erzeugen.py`: neues Bild `kalender` (Überblick, Ziel `.reise-tage > .chips`); vorhanden `bahnbuchung`.
- `engine/tests/test_funktionsseiten_711.py`: `test_unterseiten_unterwegs` verlangt die ganze Gruppe.

## Risiken
„Für dich“ und Mein Konto brauchen eine Anmeldung und fehlen in der Aufnahme; die Bilder zeigen eine Frist an der Buchung und
den Kalender-Link. Die Beispielreise hat den Baustein `waechter` nicht und steht auf „planung“: das Gespräch sagt das so.

## Analysis
Type: Feature (Inhalt in fertiger Form, Muster Teil 1 und 2). Risiko niedrig. Offene Fragen: keine.
