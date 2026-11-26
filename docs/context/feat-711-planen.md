# Kontext: feat-711-planen (Issue #711, Etappe 2, Gruppe „Planen und entscheiden“, Teil 1)

## Auftrag
Unterseiten nach dem Muster der Reiseseite (Form: `docs/design.md`, „Form einer neuen Unterseite“), DE und EN. Teil 1:
`wahrheit` (Quelle `docs/funktionen/reisemodell.md`) und `gespraech` (`docs/funktionen/gespraech.md`). Teil 2 und 3 folgen
(alternativen, buchungen; gespraeche, lebenslauf). Die Namen der Bereiche stehen in `INFO_GRUPPEN` (Weg nur `[a-z]+`).

## Betroffene Dateien
- `engine/anmeldung.py`: zwei Einträge in `INFO_UNTERSEITEN`, kein Code.
- `engine/texte_de.py`, `engine/texte_en.py`: `info.bereich.<name>.…`.
- Bilder: vorhandene `wahl` und `tag` (keine neuen).

## Risiken
Grenze 250 Zeilen (Texte zählen doppelt). Beispiele nur aus den Beispielreisen, gegen `plan/routen.yaml` geprüft. Englische
Texte ohne deutsche Wörter (Erkennung im englischen Konto-Zugang). Tests laufen über `INFO_UNTERSEITEN`.

## Analysis
Type: Feature (nur Inhalt nach fertiger Form). Affected: `engine/anmeldung.py` MODIFY (zwei Einträge), `engine/texte_de.py` und
`engine/texte_en.py` MODIFY (je rund 70 Zeilen). Kein neues Bild, kein Code, kein neuer Test (die Tests laufen je Eintrag von
`INFO_UNTERSEITEN`). Risiko niedrig. Ansatz: Texte aus den Funktionsseiten für Nutzer kürzen, Beispiele gegen die Beispielreise
prüfen, Unterschriften nur nach dem Bild. Offene Fragen: keine.
