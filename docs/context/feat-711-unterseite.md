# Kontext: feat-711-unterseite (Issue #711, Etappe 1, Teil 3)

## Auftrag
Dritter Teil des freigegebenen Entwurfs (Product Owner, 26.11.2026): Muster-Unterseite „Reiseseite“ unter
`/info/funktionen/reiseseite/` und die Form, in der die übrigen rund 15 Unterseiten mit wenig Code dazukommen. Teil 1 (Galerie,
#712) und Teil 2 (Übersicht „Alle Funktionen“, #713) liegen vor.

## Betroffene Dateien
- `engine/anmeldung.py`: `INFO_UNTERSEITEN` bekommt den Eintrag „reiseseite“; neue Funktion `unterseite` mit Helfern `nummern`,
  `info_liste`, `info_klappen`, `blasen` (Sprechblasen, auch von den Gesprächen der Infoseite genutzt); Route in `bearbeiten`.
- `engine/texte_de.py`, `engine/texte_en.py`: `info.unterseite.…` (Überschriften) und `info.bereich.reiseseite.…`.
- `engine/info/erzeugen.py`: Bilder `ort` und `zutun`, Prüfung gegen alle Bilder der Erklärseiten (`alle_bilder`);
  `engine/info/ort-*.webp`, `zutun-*.webp`.
- Tests: `engine/tests/test_funktionsseiten_711.py`, `test_infoseite_galerie_711.py` (Galerie auch auf der Unterseite), `test_infoseite.py`.
- Doku: `docs/design.md` (Funktionsseiten, Form neuer Unterseiten), `docs/sprachen.md`.

## Bestehende Muster
Bausteine der Konnektorseiten: `.karte`, `.abschnitt`, `.liste` mit `.zeile`, `details` mit `.inhalt`, `.darf`, `ul.punkte`,
`.blase`, `.zurueck`, Galerie `bildReihe` (Teil 1). Neu nur kleine Moleküle: `.kurz` (Wo/Wer), `.siehe` (Pillen-Links).

## Risiken
Grenze 250 Zeilen; Texte zählen in zwei Sprachen. Bilder nur aus den erfundenen Beispielreisen.

## Analysis
Type: Feature. Risiko niedrig (Erklärseite, keine Reisedaten). Offene Fragen: keine.
