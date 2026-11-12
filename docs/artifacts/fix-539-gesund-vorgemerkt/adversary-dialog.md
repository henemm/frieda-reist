# Adversary Dialog — fix-539-gesund-vorgemerkt
Spec: docs/specs/konnektor/gesund-vorgemerkt-539.md
Datum: 2026-11-12 17:19

## Checkliste
- [x] **AC-1:** Given eine zur Löschung vorgemerkte Reise ohne Seite, die noch in `seiten.json` steht, und mindestens eine gesunde freigeschaltete Reise / When `/gesund` abgefragt wird / Then 200 mit `{"gesund": true}`. Test: `test_gesund_ueberspringt_zur_loeschung_vorgemerkte_reise`.
- [x] **AC-2:** Given eine nicht vorgemerkte Reise in `seiten.json` ohne Seite / When `/gesund` abgefragt wird / Then 503 mit `{"gesund": false}` (fehlende Seite bleibt ein Fehler). Test: derselbe, erster Schritt.
- [x] **AC-3:** Given `seiten.json` enthält nur vorgemerkte Reisen / When `/gesund` abgefragt wird / Then 503 mit `{"gesund": false}`. Test: derselbe, letzter Schritt.
- [x] **AC-4:** Given keine Kontendatenbank vorhanden / When `/gesund` abgefragt wird / Then Verhalten und Antwortformat wie zuvor; `test_gesund_ohne_token` bleibt grün.
- [x] **AC-5:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen.

## Dialog

### Runde 1
**Adversary:** Beweis für AC-1 bis AC-3: Der Test läuft grün (`adversary-test-output.txt`, 2 passed). Der Abzug `set(seitenlinks()) - konten.vorgemerkte_reisen()` steht in `gesund()`. Wie kann die Menge falsch sein? Schritt für Schritt: nicht vorgemerkte Reise ohne Seite gibt 503 (AC-2), vorgemerkt gibt 200 (AC-1), nur Vormerk gibt leere Menge und `not reisen` greift (AC-3).
Code reference: engine/konnektor.py:3274
**Implementierer:** Der Test deckt alle drei Schritte ab, das Probe-Skript bestätigt sie. AC-4: ohne Datenbank gibt `vorgemerkte_reisen()` früh `set()` zurück und legt keine Datei an (Probe 1: DB angelegt? False). `test_gesund_ohne_token` ist grün. AC-5: Gesamtlauf 2504 passed in `test-green-output.txt`.
Code reference: engine/konten.py:1074
Code reference: engine/tests/test_konnektor.py:336

### Runde 2
**Adversary:** Randfälle. (a) Datenbank existiert, aber ohne die Tabellen (alte Instanz): `db()` führt bei jedem Öffnen `executescript(SCHEMA)` mit `CREATE TABLE IF NOT EXISTS` aus (engine/konten.py:200, Schema ab Zeile 171), legt die Tabellen also an. Probe 2 liefert ohne Fehler 503 (Reise b hat keine Seite), danach funktioniert der Vormerk (Probe 3: 200). (b) Wiederherstellung: nach `loeschung_zurueckholen` zählt die Reise wieder, fehlt die Seite, gibt es wieder 503 (Probe 4), korrekt. (c) Abgeschlossene Löschung (Löschprotokoll) wird ebenfalls übersprungen (Probe 5). (d) Leistung: eine Verbindung und eine UNION-Abfrage je Aufruf, keine Schleife; `db()` führt bei jedem Öffnen das Schema-Skript aus, wie überall im Modul, bei Bereitschaftsabfragen vernachlässigbar. (e) Ausnahme aus `vorgemerkte_reisen` (kaputte Datenbankdatei, Probe 6): `gesund()` fängt sie nicht, und `do_GET` hat kein `except`. Es gibt weder 500 noch 503, sondern eine abgebrochene Verbindung (nginx zeigt 502). Der Monitor schlägt trotzdem an (fail-closed); eine kaputte Kontendatenbank ist für den Konnektor ohnehin ein Fehler. Neu ist nur die Abhängigkeit von der Datenbank.
Code reference: engine/konnektor.py:3374
**Implementierer:** Kein Verstoß gegen die Spec, die ein Abfangen nicht verlangt. Als LOW-Finding F001 vermerkt.

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:3274
  Description: `gesund()` ruft `konten.vorgemerkte_reisen()` ohne Fehlerbehandlung auf; bei beschädigter Kontendatenbank (sqlite3.DatabaseError) entsteht eine ungefangene Ausnahme, die Verbindung bricht ab (nginx 502) statt sauber 503 mit `{"gesund": false}`.
  Spec requirement: AC-4 — Antwortformat und Statuscodes unverändert (nur der Fall ohne Datenbank ist ausdrücklich geregelt).
  Conflict: Kein Verstoß gegen eine AC; für die Überwachung wirkt es wie ein Fehler (Alarm bleibt). Nur das Format der Fehlerantwort weicht ab.
  Remediation: Optional `except sqlite3.Error` um den Abzug und 503 liefern. Nicht blockierend.

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/konnektor.py:3274
  Evidence: Abzug der vorgemerkten Reisen; Test Schritt 2 grün, Probe 3 liefert 200.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_konnektor.py:343
  Evidence: nicht vorgemerkte Reise ohne Seite bleibt 503; Probe 4 nach Wiederherstellung ebenso.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/konnektor.py:3275
  Evidence: leere Restmenge löst `not reisen` aus, 503; letzter Testschritt grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/konten.py:1074
  Evidence: ohne Datenbank leere Menge, keine Datei angelegt (Probe 1); `test_gesund_ohne_token` in den 2 grünen gesund-Tests.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_konnektor.py:336
  Evidence: Gesamtlauf 2504 passed in test-green-output.txt, ohne Übersprungene.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

Herkunft der Vormerk-Menge: `konten.vorgemerkte_reisen()` in engine/konten.py liest die Tabellen `reise_loeschung` (gesetzt von `loeschung_vormerken`, wenn Organisator:innen eine Reise vormerken) und `loeschprotokoll` (gesetzt von `loeschung_abschliessen` nach dem Entfernen). Ohne Datenbankdatei ist die Menge leer. Test für diesen Weg: `test_gesund_ueberspringt_zur_loeschung_vorgemerkte_reise` (löst den Vormerk über `loeschung_vormerken` aus). Der Zweig über das Löschprotokoll ist nur durch das Probe-Skript (Probe 5) belegt, kein Repo-Test.

## Verdict

VERDICT: VERIFIED

Tests: 2 passed (gesund), Gesamtlauf 2504 passed, 0 failed, 0 übersprungen
Edge cases: alle geprüft, einer als LOW (F001) vermerkt, nicht blockierend
Regressions: keine gefunden (einziger Aufrufer von gesund() ist do_GET)
Checklist: 5/5 points proven

## Geprüfte Dateien

- sha256:bf245610ca451cf6c149a6361115fafc6a7297afcc97c8a60f12960a0bc764ab  engine/konnektor.py
- sha256:9698d09713f744707a2f326a61f2d432782b24688fd322fd66a93e0994015eaf  engine/konten.py
- sha256:ddc4535700cba18921ca09dfce79c5bcc61b1140ebd37497386be0e80fbd25b5  engine/tests/test_konnektor.py

## Prüfbasis

- base: da287d81aec6a7414a8d2438529ae0f014eaffc6
- blob:e7816177ff4c9a12d5b493d9f4e421480b06807f  engine/konnektor.py
- blob:6f0eddf7aee88724e404dd90a774fec35d120a39  engine/konten.py
- blob:d0086d9cb5845ee33d9e11069901f1be3d27c5d7  engine/tests/test_konnektor.py

## Geprüfte Dateien

- sha256:bf245610ca451cf6c149a6361115fafc6a7297afcc97c8a60f12960a0bc764ab  engine/konnektor.py
- sha256:9698d09713f744707a2f326a61f2d432782b24688fd322fd66a93e0994015eaf  engine/konten.py
- sha256:ddc4535700cba18921ca09dfce79c5bcc61b1140ebd37497386be0e80fbd25b5  engine/tests/test_konnektor.py

## Prüfbasis

- base: da287d81aec6a7414a8d2438529ae0f014eaffc6
- blob:e7816177ff4c9a12d5b493d9f4e421480b06807f  engine/konnektor.py
- blob:6f0eddf7aee88724e404dd90a774fec35d120a39  engine/konten.py
- blob:d0086d9cb5845ee33d9e11069901f1be3d27c5d7  engine/tests/test_konnektor.py
