# Kontext: feat-711-unterwegs (Issue #711, Etappe 2, Gruppe „Unterwegs und gemeinsam“)

## Auftrag
Die übrigen Unterseiten der Gruppe „Unterwegs und gemeinsam“, DE und EN, nach dem Muster der vorhandenen Unterseiten:
`karte`, `packliste` (Teil 1), `zusammenarbeit`, `bilder` (Teil 2), `erinnerungen` (Teil 3). Quellen
`docs/funktionen/{karte,packliste,zusammenarbeit,bilder,erinnerungen}.md`, für Nutzer umgeschrieben.

## Betroffene Dateien
- `engine/anmeldung.py`: Einträge in `INFO_UNTERSEITEN`.
- `engine/texte_de.py`, `engine/texte_en.py`: `info.bereich.<name>.…`.
- `engine/info/erzeugen.py`: neue Bilder; `engine/info/aufnehmen.mjs`: optionales `ziel` (CSS-Selektor), an das die Aufnahme
  rollt, weil Karte, Mitreisende und Kalender kein eigenes Sprungziel haben.
- `engine/tests/test_funktionsseiten_711.py`: Test für die Gruppe (Muster `test_unterseiten_planen`).

## Bestehende Muster
Teil „Planen“: `docs/context/feat-711-planen*.md`, Form in `docs/design.md` („Form einer neuen Unterseite“).

## Erkenntnisse zu den Bildern (Aufnahme ohne Netz und ohne `api/`)
- Rückmeldungen, Aufgaben, Fragen, Wünsche und „Für dich“ kommen live über `api/` und sind in der Aufnahme leer; sie taugen
  nicht als Bild. Die Tagesseite der Beispielreise hat keinen Kartenausschnitt.
- Brauchbar: Karte im Überblick (`.kartenbox`), Hotel am Elbufer (U-01: Bild mit Nennung, Adresse, Kartenlinks), Packliste der
  Beispielreise (Planen mit Summen), Mitreisende im Überblick (`.mitreisende`), Kopfbild der Etappe (E-02),
  „Ganze Reise in den Kalender“ (`.reise-tage > .chips`), vorhandene Bilder `ort`, `bahnbuchung`, `packliste`.

## Risiken
Englische Fachwörter (`VERBOTENE_FACHWOERTER`: thing, leg, attribute; Gegenstand = gear). Deutsche Wörter, die im Englischen
fehlen. Grenze 250 Zeilen je PR, daher drei PRs. `erzeugen.py` erzeugt alle Bilder neu: nicht betroffene zurücksetzen.

## Analysis
Type: Feature (Inhalt in fertiger Form, Muster der Gruppe „Planen“). Risiko niedrig: nur Texte, Bilder und Einträge in
`INFO_UNTERSEITEN`; die Seite selbst ist fertig und wird von `test_unterseite` je Eintrag geprüft.

Affected Files: `engine/anmeldung.py` (MODIFY), `engine/texte_de.py`, `engine/texte_en.py` (MODIFY), `engine/info/erzeugen.py`
(MODIFY), `engine/info/aufnehmen.mjs` (MODIFY, optionales `ziel`), `engine/info/<bild>-{de,en}.webp` (CREATE),
`engine/tests/test_funktionsseiten_711.py` (MODIFY).

Ansatz und Reihenfolge: drei PRs unter 250 Zeilen. Teil 1 karte (Bilder `karte`, `lage`) und packliste (`summen`, vorhandenes
`packliste`) mit dem Rollziel der Aufnahme; Teil 2 zusammenarbeit (`mitreisende`, `tag`) und bilder (`etappe`, `lage`, `ort`);
Teil 3 erinnerungen (`bahnbuchung`, `kalender`). Bildunterschriften nach dem tatsächlichen Bild; in EN zeigen die Bilder die
Inhalte der Reise auf Deutsch, die Unterschrift nennt daher keine deutschen Beschriftungen.

Dependencies: Übersicht `funktionen_seite` verlinkt automatisch, sobald ein Bereich in `INFO_UNTERSEITEN` steht.
Open Questions: keine.
