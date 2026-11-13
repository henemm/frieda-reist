# Adversary Dialog — fix-550-537-wackelige-browsertests
Spec: docs/specs/betrieb/wackelige-browsertests-550-537.md
Datum: 2026-11-13 19:09

## Checkliste
- [x] **AC-1:** Given der Reise-Stand-Test mit Stub-Server (1 s Verzögerung) / When die Seite nach `reload` den allgemeinen Text „Neue Version des Handbuchs bereit.“ vor „Neu: Reise-Stand 2.“ zeigt / Then wartet `stand_browser.mjs` bis zu 15 s auf den Text „Neu: Reise-Stand“ in `#neu` und liest erst dann; bei Zeitüberschreitung liest es weiter, sodass der Test mit seiner Meldung scheitert (Test 5).
- [x] **AC-2:** Given der Packliste-Test / When nach dem Haken an „Wanderschuhe“ neu gezeichnet wird / Then wartet `seiten_packliste.mjs` vor dem Lesen von `knopf0` auf nicht leeren Text von `.pack-alle`; ebenso vor dem Lesen von `knopf` nach `reload` (Test 6).
- [x] **AC-3:** Given `bild(page, optionen)` mit einem Screenshot, der gelingt / When der Helfer läuft / Then ist das Ergebnis `true` bei genau einem Aufruf; scheitert der erste Versuch und gelingt der zweite, ist das Ergebnis `true` nach zwei Aufrufen (Test 1, 2).
- [x] **AC-4:** Given ein Screenshot, der immer scheitert / When der Helfer läuft / Then gibt er nach drei Fehlversuchen `false` zurück und wirft nicht; die Optionen gehen an jeden Versuch unverändert (Test 3, 4).
- [x] **AC-5:** Given Vollseitenbilder in `seiten_browser.mjs`, `seiten_brett.mjs` und `seiten_packliste.mjs` / When ein Bild endgültig scheitert / Then geht das Skript weiter, und `seiten_browser.mjs` nennt die fehlenden Bilder in `bilderFehlen` der JSON-Ausgabe.
- [x] **AC-6:** Given nicht leere `bilderFehlen` / When `test_seite.py` läuft / Then gibt es eine Warnung (`warnings.warn`) mit den Dateinamen und der Test ist grün, nicht rot (Test 7).
- [x] **AC-7:** Given der PR-Stand / When er mit `main` verglichen wird / Then sind `engine/vorlage.html`, die Engine, `betrieb/` und `.github/workflows/tests.yml` unverändert; die Höchsthöhe von 32000 px bleibt (Prüfung 8).
- [x] **AC-8:** Given der Lastaufbau (beide Tests, `-n 4`, zwei Prozesse Dauerlast, 11 Durchläufe) / When er nach der Umsetzung läuft / Then ist kein Durchlauf rot.
- [x] **AC-9:** Given der Stand nach AC-8 / When mehrere Gesamtläufe mit `-n 3` laufen / Then sind alle grün; der CI-Lauf mit `RH_BILDER` ist grün.

## Dialog

### Runde 1
**Adversary:** Quelltext und Diff gegen Basis 98104df gelesen, Tests selbst gelaufen (adversary-test-output.txt).

Confirmation:
  AC: AC-1
  Code reference: engine/tests/stand_browser.mjs:40
  Evidence: waitForFunction auf Text Neu: Reise-Stand in #neu, timeout 15000, catch liest weiter; Test scheitert sonst mit eigener Meldung, kein falsches Grün, kein Skriptabbruch.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/seiten_packliste.mjs:163
  Evidence: warte() (5 s) auf nicht leeren .pack-alle-Text vor knopf0, ebenso Zeile 172 nach reload vor knopf; catch fängt Zeitablauf; Prüfung in test_packliste.py unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/bild.mjs:5
  Evidence: Schleife bis 3 Versuche, true beim ersten Erfolg; test_bild_helfer.py 10 passed.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_bild_helfer.py:1
  Evidence: nach 3 Fehlversuchen false, try/catch wirft nie, Optionen unverändert durchgereicht; Tests 3 und 4 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/seiten_browser.mjs:132
  Evidence: bild() false führt zu bilderFehlen.push(Dateiname), Skript läuft weiter; bilderFehlen immer im JSON (Zeile 231), leer ohne RH_BILDER. Namenskonflikt in seiten_brett.mjs vermieden, Aufrufer heißt brettBild (Zeile 78, Import Zeile 6); packliste nutzt bild (Zeilen 116, 189). Eigener Lauf mit RH_BILDER erzeugte alle Bilder.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/tests/test_seite.py:26
  Evidence: bilder_fehlen_melden ruft warnings.warn mit Dateinamen, aufgerufen vor den Asserts (Zeile 55); Test bleibt grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/tests/seiten_browser.mjs:130
  Evidence: Diff-Vergleich mit Basis für Vorlage, Betrieb, Workflow-Datei leer; geänderte Nicht-Doku-Dateien nur unter engine/tests; 32000 px bleibt (Zeilen 130, 132).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/seiten_brett.mjs:78
  Evidence: brettBild ruft bild, kein Namenskonflikt, Skript läuft bei Fehlschlag weiter.
  Status: CONFIRMED

**Implementierer:** keine Einwände.

### Runde 2
**Adversary:** Gezielte Angriffe: Wartepunkt verdeckt echten Fehler? Nein, Zeitablauf wird nur verschluckt, danach wird gelesen und geprüft. bilderFehlen ohne RH_BILDER? Array immer ausgegeben. Import ./bild.mjs? funktioniert mit und ohne RH_BILDER. AC-8: last-output.txt 11 von 11 grün, eigene Stichprobe -n 4 mit 37 Tests grün. AC-9: Gesamtlauf 2721 passed belegt; mehrere Gesamtläufe und CI-Lauf mit RH_BILDER stehen bis Phase 7 aus.

Confirmation:
  AC: AC-8
  Code reference: engine/tests/test_bild_helfer.py:50
  Evidence: last-output.txt 11 Durchläufe ohne Rot, plus eigener Lauf in adversary-test-output.txt.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/tests/test_seite.py:55
  Evidence: Gesamtlauf test-green-output.txt 2721 passed; eigener Lauf 37 und 35 passed. Mehrere Läufe und CI offen, laut Spec Phase 7, als offener Punkt akzeptabel.
  Status: CONFIRMED

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/seiten_packliste.mjs:172
  Description: catch verschluckt jeden Fehler beim Warten, nicht nur Zeitablauf.
  Spec requirement: AC-9 (Teil CI-Lauf mit RH_BILDER, mehrere Gesamtläufe)
  Conflict: kein Defekt; Folgefehler träten beim anschließenden Lesen ohnehin auf. AC-9 vollständig erst in Phase 7 belegbar.
  Remediation: Nachweise in Phase 7 nachholen.

**Implementierer:** F001 als offener Punkt akzeptiert.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
**VERIFIED**

AC-1 bis AC-8 bewiesen, AC-9 Gesamtlauf bewiesen; mehrere Gesamtläufe und CI-Lauf mit RH_BILDER offen bis Phase 7 (F001, LOW, kein Defekt).

VERDICT: VERIFIED

## Geprüfte Dateien

- sha256:da3cc375edd6826fd216cc86f6d1839e5a45ccccc70bfa9e188c150e794199f9  engine/tests/bild.mjs
- sha256:11bf0c0227945476bee5371b081b68aa212b3e811cbdd83d970c9f462cec3cda  engine/tests/seiten_brett.mjs
- sha256:1c6887ee1f023eadcb33e313a9b7f738e3e459e95a8a13ab2a19232044b45a5d  engine/tests/seiten_browser.mjs
- sha256:9189ba618791d2df0f7f9f5fb7fdd80799249c91d76493e2d780f96d00d050fe  engine/tests/seiten_packliste.mjs
- sha256:a4835f840a168a86f66adad118a349846583b50c4079f6c3d72e297d616c152f  engine/tests/stand_browser.mjs
- sha256:992e1656d2b1224d59b7d00525bd1db73da0b5360fac76a89611adbf7aeb7831  engine/tests/test_bild_helfer.py
- sha256:14382117e0614e7e036edf67d8237f7155953b19f65ac253140a416eceea6e57  engine/tests/test_seite.py

## Prüfbasis

- base: 98104df75af71edb0c3e38fb884966cdb74d59cf
- blob:f2f2f6a336e04f8f75c9dcdf5e1764568927aa6f  engine/tests/bild.mjs
- blob:c0b72129040244f568ca526e5638f181b08ad3da  engine/tests/seiten_brett.mjs
- blob:ba612e217dced917ff77b441bbeb41f1666b9b73  engine/tests/seiten_browser.mjs
- blob:a256fbb0fb8d1785bf65ab4a8c8c6e81c4bc4819  engine/tests/seiten_packliste.mjs
- blob:c0f83260ea204090f6e66ae2ae89df2c7d5f0428  engine/tests/stand_browser.mjs
- blob:eb2789c418b18e6add8487d3eee5349fe7f9fc79  engine/tests/test_bild_helfer.py
- blob:aa2955999af77af118e1a4ace1192c066b651dd8  engine/tests/test_seite.py

## Geprüfte Dateien

- sha256:da3cc375edd6826fd216cc86f6d1839e5a45ccccc70bfa9e188c150e794199f9  engine/tests/bild.mjs
- sha256:11bf0c0227945476bee5371b081b68aa212b3e811cbdd83d970c9f462cec3cda  engine/tests/seiten_brett.mjs
- sha256:1c6887ee1f023eadcb33e313a9b7f738e3e459e95a8a13ab2a19232044b45a5d  engine/tests/seiten_browser.mjs
- sha256:9189ba618791d2df0f7f9f5fb7fdd80799249c91d76493e2d780f96d00d050fe  engine/tests/seiten_packliste.mjs
- sha256:a4835f840a168a86f66adad118a349846583b50c4079f6c3d72e297d616c152f  engine/tests/stand_browser.mjs
- sha256:992e1656d2b1224d59b7d00525bd1db73da0b5360fac76a89611adbf7aeb7831  engine/tests/test_bild_helfer.py
- sha256:14382117e0614e7e036edf67d8237f7155953b19f65ac253140a416eceea6e57  engine/tests/test_seite.py

## Prüfbasis

- base: 98104df75af71edb0c3e38fb884966cdb74d59cf
- blob:f2f2f6a336e04f8f75c9dcdf5e1764568927aa6f  engine/tests/bild.mjs
- blob:c0b72129040244f568ca526e5638f181b08ad3da  engine/tests/seiten_brett.mjs
- blob:ba612e217dced917ff77b441bbeb41f1666b9b73  engine/tests/seiten_browser.mjs
- blob:a256fbb0fb8d1785bf65ab4a8c8c6e81c4bc4819  engine/tests/seiten_packliste.mjs
- blob:c0f83260ea204090f6e66ae2ae89df2c7d5f0428  engine/tests/stand_browser.mjs
- blob:eb2789c418b18e6add8487d3eee5349fe7f9fc79  engine/tests/test_bild_helfer.py
- blob:aa2955999af77af118e1a4ace1192c066b651dd8  engine/tests/test_seite.py
