# Kontext: feat-711-planen-2 (Issue #711, Etappe 2, Gruppe „Planen und entscheiden“, Teil 2)

## Auftrag
Unterseiten `alternativen` (Quelle `docs/funktionen/alternativen.md`) und `buchungen` (`docs/funktionen/buchungen.md`), DE und
EN, nach dem Muster der Reiseseite. Teil 1 (wahrheit, gespraech): `docs/context/feat-711-planen.md`.

## Betroffene Dateien
- `engine/anmeldung.py`: zwei Einträge in `INFO_UNTERSEITEN`.
- `engine/texte_de.py`, `engine/texte_en.py`: `info.bereich.alternativen.…`, `info.bereich.buchungen.…`.
- `engine/info/erzeugen.py`: neue Bilder `vergleich` (V-01), `buchung` (B-01), `bahnbuchung` (B-02), `zubuchen` (zu-buchen),
  dazu die vorhandenen `wahl` und `zutun`; `engine/info/<bild>-de.webp` und `-en.webp`.
- `engine/tests/test_funktionsseiten_711.py`: `test_unterseiten_planen` um die zwei Bereiche erweitert.

## Risiken
Englische Fachwörter nach `VERBOTENE_FACHWOERTER` (choice, leg, rejected, thing). Grenze 250 Zeilen.

## Analysis
Type: Feature (Inhalt in fertiger Form). Risiko niedrig. Offene Fragen: keine.
