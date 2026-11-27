# Adversary Dialog — fix-730-zurueckholen-knopf
Spec: docs/specs/fast/fix-730-zurueckholen-knopf.md
Datum: 2026-11-27 13:48

## Checkliste
- [x] AC-1: Ist die Seite einer vorgemerkten Reise abgebaut, zeigt „Mein Konto“ einer Organisator:in den Knopf „Reise zurückholen“; Zurückholen gelingt.
- [x] AC-2: Eine Mitwirkende sieht in derselben Lage den Block ohne Knopf und kann nicht zurückholen.
- [x] AC-3: Bestehende Tests zum Löschen und zum Export bleiben grün.

## Dialog

### Runde 1
**Adversary:** Angriffe auf `_person` (engine/anmeldung.py:729-736): (a) reise.yaml mit Liste statt Zuordnung: `isinstance(personen, dict)` greift nicht, Liste läuft wie bisher. (b) Personen ohne dict-Wert (`karl: null`, Skalar): `isinstance(p, dict)` filtert. (c) leere/fehlende `personen`: `or []` liefert leere Liste, Ergebnis `{}`. (d) Seite noch da (`z` oder `rm.zustand` nicht None): Zweig nicht betreten, Verhalten unverändert. (e) Speicher unlesbar: `_reise_aus_speicher` gibt `{}`, dann `{}`. (f) Ein `schluessel`-Feld im Wert wird vom Zuordnungsschlüssel überschrieben, richtig, da der Schlüssel maßgeblich ist.
**Implementierer:** Alle Fälle durch den Code gedeckt. Tests gezielt gelaufen: 121 passed (test_loeschen_reise, test_export, test_anmeldung, -n 3), siehe test-run-output.txt.

### Runde 2
**Adversary:** Aufrufer: Zeile 741 (`ist_organisatorin`) und 773 (Block/Knopf) sind der Fehlerpfad und nun behoben. Zeile 976 (`export_person`, ruft ohne z) liest jetzt ebenfalls die echte Rolle statt leer, vorher "gast"; das ist ein Nebeneffekt zugunsten der Richtigkeit, kein Bruch. Zeile 1047 (`_export_rolle`) bricht bei `zs is None` vorher mit "gast" ab und erreicht den Speicher-Rückfall nie; die Spec-Aussage, der Export-Rückweg werde mitgespeist, stimmt dort nur für `export_person`. Sicherheit: Knopf weiter nur bei Rolle organisator; Mitwirkende bekommt `rolle: mitwirkend`, der Test beweist: kein Knopf und Zurückholen per POST bleibt wirkungslos.
**Implementierer:** Test `test_knopf_auch_bei_abgebauter_seite` (engine/tests/test_loeschen_reise.py:302) baut den Fall nach (daten.json entfernt, `rm.zustand` None) und prüft AC-1 und AC-2 inklusive POST.

## Befunde und Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:734
  Evidence: Zuordnung aus reise.yaml wird in Personen mit schluessel umgewandelt, ist_organisatorin (741) und Block (773) finden die Rolle; Test prüft Knopf und erfolgreiches Zurückholen.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:773
  Evidence: Knopf nur bei Rolle organisator; Test zeigt Mitwirkende ohne Knopf und POST ohne Wirkung (reise_vorgemerkt bleibt wahr).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/anmeldung.py:976
  Evidence: 121 Tests in test_loeschen_reise, test_export, test_anmeldung grün (test-run-output.txt).
  Status: CONFIRMED

Finding:
  ID: F001
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/anmeldung.py:1047
  Description: _export_rolle bricht bei fehlender Seite mit "gast" ab und nutzt den Speicher-Rückfall von _person nicht.
  Spec requirement: Spec Ursache nennt den Export als Mitbetroffenen, AC nicht.
  Conflict: Rolle im Export bleibt bei abgebauter Seite "gast"; nicht Teil der AC, kein Test bricht.
  Remediation: Optional in eigenem Ticket; hier nicht nötig.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 121 passed, 0 failed, 0 übersprungen (gezielt)
Checklist: 3/3 points proven. F001 ist LOW und außerhalb der AC.

## Geprüfte Dateien

- sha256:0976ded86ca1c9e2a864ce3f84daf9f5f4770aace4f1fe39b830e9edf831608d  engine/anmeldung.py

## Prüfbasis

- base: b92ac18e4a973d80db4eb2afba53966e4232d0f0
- blob:f609d55db9a680a1e786574a2314ce4e30cace6e  engine/anmeldung.py
