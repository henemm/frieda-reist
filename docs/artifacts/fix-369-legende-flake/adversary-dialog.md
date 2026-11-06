# Adversary Dialog — fix-369-legende-flake
Spec: docs/specs/fast/fix-369-legende-flake.md
Datum: 2026-11-06

## Checkliste
- AC Wartepunkt nach Klick mit Zeitgrenze, Fehler abgefangen: PROVEN
- AC keine Lockerung der Prüfungen, nur Messskript und Test geändert: PROVEN
- AC Seite ohne Ebenen scheitert weiter: PROVEN (Mutation M2)
- AC test_legende_nach_arten in allen vier Fällen grün, stabil: PROVEN (60 von 60 Läufen)
- AC statischer Test rot ohne Wartestelle: PROVEN (M1, M1b)

## Dialog

### Runde 1
**Adversary:** Erste Fassung (waitForFunction mit .some): 2 von 6 Läufen rot ohne Last, 1 von 3 mit Last; Zeilen mit Breite 0. Befund F001 (BROKEN).
**Implementierer:** Bedingung zu schwach; Ursache war eine nicht aufgeklappte Liste.

### Runde 2
**Adversary:** Neue Fassung (bis 4 Versuche, Klick nur bei geschlossener Liste, atomare Messung in der Wartebedingung, Rückfall auf alte Messung). 30 Läufe ohne Last: 30 von 30 grün (test-30-ohne-last.txt). 30 Läufe mit 4 Busy-Loops: 30 von 30 grün (test-30-mit-last.txt). Mutationen: waitForFunction entfernt -> statischer Test rot; .every -> .some -> statischer Test rot; Selektor der Zeilen kaputt (Seite ohne Ebenen) -> test_legende_nach_arten in 4 von 4 Fällen rot, kein falsches Grün. Geänderte Dateien: nur seiten_karte_legende.mjs und test_karte_legende.py.
**Implementierer:** Nichts offen.
Restrisiko (nicht blockierend): Der Rückfall nach 4 Versuchen misst wie vorher, die Flake wäre nur bei vier verfehlten Versuchen (je 2 s) wieder möglich.

## Herkunft der Vorbedingungen
kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Findings

Finding:
  ID: F001
  Severity: HIGH
  Category: spec_violation
  Code reference: engine/tests/seiten_karte_legende.mjs:24
  Description: Erste Fassung wartete mit .some; behoben durch Schleife mit atomarer Messung (Zeilen 24-46).
  Spec requirement: keine Schwankung bei [390-chromium]
  Conflict: in der ersten Fassung ja, in der überarbeiteten nicht mehr (60 von 60 grün).
  Remediation: umgesetzt. Status: RESOLVED

Confirmation:
  AC: Wartepunkt und stabile Messung
  Code reference: engine/tests/seiten_karte_legende.mjs:28
  Evidence: Schleife mit expanded-Prüfung, every(breit>0 und hoch>0), Timeout 2 s je Versuch; 60 von 60 grüne Läufe.
  Status: CONFIRMED

Confirmation:
  AC: Statischer Test gegen Verschwinden der Wartestelle
  Code reference: engine/tests/test_karte_legende.py:90
  Evidence: rot bei Entfernen von waitForFunction und bei .some statt .every.
  Status: CONFIRMED

## Verdict
VERDICT: VERIFIED
Tests: 5 passed je Lauf, 60 von 60 Läufen grün, 0 failed, 0 übersprungen

## Geprüfte Dateien

- sha256:85c052fba8f7fe2fcbca767a6830be4bc812091013370571c9410beef8c27418  engine/tests/seiten_karte_legende.mjs
- sha256:040bd05fdec75ef95bb494baf6d96adea39a30f2ef795b380538089c07e0dca0  engine/tests/test_karte_legende.py

## Prüfbasis

- base: e5dfe1b4a1d22ad91cabccc4dbc560c6eb7604d6
- blob:e386ba34663e857efb76a4baf6c0e630b896bb77  engine/tests/seiten_karte_legende.mjs
- blob:069a6240f034195bf007e8ed92257258a8f4d136  engine/tests/test_karte_legende.py
