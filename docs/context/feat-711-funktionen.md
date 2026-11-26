# Kontext: feat-711-funktionen (Issue #711, Etappe 1, Teil 2)

## Auftrag
Zweiter Teil des freigegebenen Entwurfs (Product Owner, 26.11.2026): Auf der Infoseite ersetzt die Karte „Was Frieda alles
kann“ mit dem Knopf „Alle Funktionen ansehen“ den Link nach GitHub; neue Seite „Alle Funktionen“ unter `/info/funktionen/`
mit drei Orten, drei Gruppen (eine Zeile je Bereich, Titel und Satz, „Seite folgt“ ohne Link), „Wer darf was“. Teil 1
(Galerie) ist ausgeliefert (PR #712); Teil 3 bringt die Muster-Unterseite „Reiseseite“.

## Betroffene Dateien
- `engine/anmeldung.py`: `info_seite` (Karte statt GitHub-Link, Reihenfolge wie Entwurf: Prinzipien, Bilder, Karte, Gespräche,
  Erste Schritte), neue `funktionen_seite`, Helfer `info_kopf`, `info_fuss`, `info_abschnitt`, `info_zeile`; Datenform
  `INFO_ORTE`, `INFO_GRUPPEN`, `INFO_ROLLEN`, `INFO_UNTERSEITEN` (in Teil 2 leer), Weg `INFO_WEG`; Routen in `bearbeiten`, `ist_unsere`.
- `engine/konnektor.py`: unverändert; `/info/…` geht seit Teil 1 an die Anmeldeseiten, wenn `ist_unsere` es kennt.
- `engine/texte_de.py`, `engine/texte_en.py`: neue Schlüssel; `info.funktionen.satz`, `.link`, `.datei` entfallen.
- `engine/instanz.py`: `quellcode_datei` wird unbenutzt und entfällt; `engine/tests/texte_xx.py`: Sonderfall `info.funktionen.datei` entfällt.
- Tests: `engine/tests/test_infoseite.py` (Test des GitHub-Links entfällt), neu `engine/tests/test_funktionsseiten_711.py`.
- Doku: `docs/design.md` (Infoseite, neuer Abschnitt Funktionsseiten), `docs/sprachen.md` (Hinweis auf `info.funktionen.datei`).

## Risiken
- Wege unter /info/: nur `/info/funktionen/` und `/info/funktionen/<bereich>/` mit Kleinbuchstaben; alles andere bleibt 404.
- Grenze 250 Zeilen: Texte der Unterseite erst in Teil 3.

## Analysis
Type: Feature. Ansatz wie in `docs/context/feat-711-galerie.md`, Abschnitt Technical Approach. Risiko niedrig (nur Erklärseiten,
keine Reisedaten, kein neuer nginx-Ort). Offene Fragen: keine.
