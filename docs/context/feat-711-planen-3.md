# Kontext: feat-711-planen-3 (Issue #711, Etappe 2, Gruppe „Planen und entscheiden“, Teil 3)

## Auftrag
Unterseiten `gespraeche` (Quelle `docs/funktionen/gute-gespraeche.md`) und `lebenslauf` (`docs/funktionen/lebenszyklus.md`),
DE und EN, nach dem Muster der Reiseseite. Teil 1 und 2: `docs/context/feat-711-planen.md`, `feat-711-planen-2.md`.

## Betroffene Dateien
- `engine/anmeldung.py`: zwei Einträge in `INFO_UNTERSEITEN`.
- `engine/texte_de.py`, `engine/texte_en.py`: `info.bereich.gespraeche.…`, `info.bereich.lebenslauf.…`.
- `engine/info/erzeugen.py`: neues Bild `stadt` (Stadtwochenende, Überblick, Status „Idee“); vorhandenes `zutun`.
- `engine/tests/test_funktionsseiten_711.py`: `test_unterseiten_planen` um die zwei Bereiche erweitert.

## Risiken
Deutsche Texte ohne „Beispielreise“ (die Erkennung deutscher Wörter im englischen Konto-Zugang lernt aus dem Katalog).
Statusnamen im Englischen wie auf der Seite (Idea, Planning, Fixed, Travelling, After, Archived).

## Analysis
Type: Feature (Inhalt in fertiger Form). Risiko niedrig. Offene Fragen: keine.
