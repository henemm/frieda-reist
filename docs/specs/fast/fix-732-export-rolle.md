# Mini-Spec: fix-732-export-rolle

Issue #732. Nebenbefund aus #730: Im Datenexport („Meine Daten herunterladen“ in Mein Konto) gilt man als Gast, wenn
die veröffentlichte Seite der Reise fehlt.

## Ursache

`_export_rolle` (`engine/anmeldung.py`) kehrt mit „gast“ zurück, sobald `rm.zustand(reise)` keinen Zustand der Seite
liefert. Der Rückweg über `reise.yaml` im Reisespeicher, den `_person` seit #730 kennt, wird so nie erreicht.

Vorgemerkte Reisen kommen gar nicht in den Export (`export_bauen` lässt sie aus). Betroffen sind Reisen im
Reisespeicher ohne lesbare Seite, etwa eine neue Reise vor dem ersten Veröffentlichen. Dort werden die Belege
(`belege.liste` nach Name und Rolle) so gefiltert, als wäre die Person Gast: Eine Organisatorin bekommt nur die Belege
für alle, ihre eigenen und die nur für Beteiligte nicht.

## Was ändert sich

- `engine/anmeldung.py`, `_export_rolle`: Kein vorzeitiges „gast“ mehr; Name und Rolle kommen immer über `_person`
  (Seite, sonst `reise.yaml`). Findet `_person` niemanden, bleibt es wie bisher: Name des Kontos, Rolle „gast“.
- `engine/tests/test_export.py`: Test mit Reise im Speicher und ohne `daten.json` der Seite.

## Was darf sich nicht ändern

- Verhalten bei veröffentlichter Seite; welche Reisen exportiert werden; Inhalt von `person.json`.
- Unbekannte Person oder Reise ohne lesbaren Stand: weiter Gast mit dem Namen des Kontos.
- Kein Eingriff in Reisedaten oder Konten einer Instanz.

## Acceptance Criteria

- AC-1: Liegt die Reise im Reisespeicher und fehlt ihre Seite, enthält der Export einer Organisatorin dieselben Belege
  wie bei veröffentlichter Seite (Rolle aus `reise.yaml`).
- AC-2: Eine Mitwirkende bekommt in derselben Lage nur die Belege, die `belege.liste` ihr als Mitwirkende zeigt.
- AC-3: Fehlt die Seite und steht die Reise nicht im Speicher, bleibt es bei Gast mit dem Namen des Kontos.
- AC-4: Bestehende Tests zum Export und zum Löschen bleiben grün.
