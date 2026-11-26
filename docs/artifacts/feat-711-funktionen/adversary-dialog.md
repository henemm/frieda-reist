# Adversary Dialog — feat-711-funktionen
Spec: docs/specs/oberflaeche/funktionsseiten-711-teil2.md
Datum: 2026-11-26 17:07

## Checkliste
- [x] AC-1: Infoseite DE und EN, an `/` und `/info/`: Karte `.karte.einstieg` mit Titel, Satz und Knopf nach `/info/funktionen/`; kein Link auf `docs/funktionen` oder `README.en.md`; „Quellcode (AGPL)“ bleibt im Fuß.
- [x] AC-2: `/info/funktionen/` DE und EN: Titel der Seite, Zurück-Link, Satz, drei Orte, drei Gruppen, jeder Bereich mit Titel, Satz und Anker; Bereiche ohne Unterseite mit „Seite folgt“ und ohne Link; „Wer darf was“ mit drei Rollen; Sprachumschalter auf derselben Adresse; alle Texte aus dem Katalog.
- [x] AC-3: Wege: ohne Schrägstrich 303 (mit Sprache); unbekannter oder noch nicht vorhandener Bereich 404; POST 303 zurück; HEAD 200; angemeldet „Mein Konto“ im Kopf.
- [x] AC-4 (Browser, 390 px und 1280 px, DE und EN): kein seitlicher Überlauf, keine Skriptfehler; am Handy die drei Orte untereinander, am Rechner nebeneinander; jede Zeile mindestens 44 px hoch.
- [x] AC-5: Die Ausnahmelisten in `test_texte.py` werden nicht länger; alle Tests grün.

## Dialog

### Runde 1
**Adversary:** Suite (233 Tests, 0 Fehler, 0 übersprungen): grün. Nachprobe der Fixes in Chromium an 320, 390, 640, 760, 900, 1024, 1280, 1920 px, DE und EN: nie seitlicher Überlauf; Orte untereinander bei 320 und 390 (Karten 288 bzw. 358 px breit), ab 640 drei nebeneinander (192 px, ab 760 224 px, gleiche Oberkante); Zeilen mindestens 78 px. F001 behoben. 404-Weg: `/info/funktionen/x` und ohne Schrägstrich geben sofort 404, die Prüfung steht vor der Umleitung (engine/anmeldung.py:1708); F003 behoben. docs/konten.md beschreibt Infoseite, `/info/funktionen/` und `/info/galerie.js`; Reste von `quellcode_datei` und `info.funktionen.satz/.link/.datei` gibt es außerhalb der Artefakte nicht mehr; F002 behoben.
**Implementierer:** (nicht beteiligt)

### Runde 2
**Adversary:** Nachgebohrt: (a) Der Raster-Fix ist auf `.prinzipien.orte` begrenzt (engine/anmeldung.py:195), die Prinzipien-Karten der Infoseite behalten ihr Raster. (b) INFO_WEG erlaubt nur `[a-z]+`; Großschreibung, Unterpfade und `/info/funktionenx/` fallen durch und geben 404 (im Test). (c) Alle Texte der Seite stammen aus dem Katalog DE und EN (engine/texte_de.py:3792, engine/texte_en.py:3790); `test_texte.py` ist unverändert, die Ausnahmen in `texte_xx.py` werden kürzer. (d) Quellcode-Link im Fuß bleibt aus instanz.QUELLCODE (engine/instanz.py:31). Neue Befunde: keine.
**Implementierer:** (nicht beteiligt)

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1507
  Evidence: Karte `.karte.einstieg` mit Titel, Satz, Knopf nach /info/funktionen/; kein Link auf docs/funktionen; Quellcode im Fuß; Test test_infoseite_fuehrt_zu_allen_funktionen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1539
  Code reference: engine/texte_de.py:3792
  Code reference: engine/texte_en.py:3790
  Evidence: funktionen_seite baut Zurück-Link, Satz, Orte, Gruppen mit Anker, Marke "Seite folgt", Rollen; Texte in engine/texte_de.py:3792 und engine/texte_en.py:3790.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/anmeldung.py:1708
  Evidence: 404 für unbekannte Bereiche vor der Umleitung, 303 ohne Schrägstrich mit Query, POST 303, HEAD 200, Konto im Kopf; test_wege_der_funktionsseiten grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/anmeldung.py:195
  Evidence: auto-fit minmax(12rem,1fr); gemessen 320 bis 1920 px DE/EN ohne Überlauf, drei nebeneinander ab 640, untereinander bis 390, Zeilen mindestens 78 px.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/instanz.py:31
  Evidence: quellcode_datei entfernt, Ausnahme in texte_xx.py entfernt, test_texte.py unverändert; 233 Tests grün.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Die Änderung schreibt keine neuen Felder; INFO_UNTERSEITEN ist absichtlich leer, der Zweig mit Unterseiten wird in Teil 2 von keinem Produktionsweg erreicht.


## Verdict

VERDICT: VERIFIED
Tests: 233 passed, 0 failed, 0 übersprungen
Edge cases: Zwischenbreiten 320 bis 1920 px geprüft, keine Befunde
Regressions: None found
Checklist: 5/5 points proven

## Geprüfte Dateien

- sha256:264a37758f90a973941f6650641b32e0842f9acd5d091b75792527196155e446  engine/anmeldung.py
- sha256:8a1722e8a322f07cd93e86112bed2208b3411d7b0eeb47dfef7cd05e4d475c11  engine/instanz.py
- sha256:ca7f2cb14790139de5e0cf5cbd81bd4b8291064283950180665ebfa0dbfc7a21  engine/texte_de.py
- sha256:0e60a03bc31c9f285b84e81a442bfedd2a4a16e6a135cbf16b3ca6874211cfb7  engine/texte_en.py

## Prüfbasis

- base: aad85d07dc66ae7e868ba7190089cd70b9ff3adc
- blob:641f53befc43e3ce5e9a5eccd2ec1bba4f939246  engine/anmeldung.py
- blob:1637a27b8d3d220d4ea69d3e0b0ef63904746fe8  engine/instanz.py
- blob:acb9228c28e54d27f44917aae912be7a350d2e65  engine/texte_de.py
- blob:8a712dad6693ac1b944ffb38b5bea8ff35a432d2  engine/texte_en.py
