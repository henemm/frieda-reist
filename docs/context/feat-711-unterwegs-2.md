# Kontext: feat-711-unterwegs-2 (Issue #711, Etappe 2, Gruppe „Unterwegs und gemeinsam“, Teil 2)

## Auftrag
Unterseiten `zusammenarbeit` (Quelle `docs/funktionen/zusammenarbeit.md`) und `bilder` (`docs/funktionen/bilder.md`), DE und
EN. Teil 1 (karte, packliste, Rollziel der Aufnahme): `docs/context/feat-711-unterwegs.md`.

## Betroffene Dateien
- `engine/anmeldung.py`: zwei Einträge in `INFO_UNTERSEITEN`.
- `engine/texte_de.py`, `engine/texte_en.py`: `info.bereich.zusammenarbeit.…`, `info.bereich.bilder.…`.
- `engine/info/erzeugen.py`: neue Bilder `mitreisende` (Überblick, Ziel `.mitreisende`) und `etappe` (E-02); vorhanden
  `tag`, `ort`, `lage`.
- `engine/tests/test_funktionsseiten_711.py`: `test_unterseiten_unterwegs` um die zwei Bereiche erweitert.

## Risiken
Rückmeldungen, Aufgaben und Wünsche kommen live über `api/` und fehlen in der Aufnahme; die Bilder zeigen daher Mitreisende,
Stand der Vorbereitung und Sprechblasen. Englische Fachwörter nach `VERBOTENE_FACHWOERTER`. Grenze 250 Zeilen.

## Analysis
Type: Feature (Inhalt in fertiger Form, Muster Teil 1). Risiko niedrig. Offene Fragen: keine.
