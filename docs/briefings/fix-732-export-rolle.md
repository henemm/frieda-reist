---
spec_file: docs/specs/fast/fix-732-export-rolle.md
spec_sha256: 57bfd13a033816de0e387b668adc666bc088a983903cf4fd60f7ebfe023e4d22
spec_frozen_sha256: aa320c0ace73872710d31ca96feab48c73e5faabb7e7312a552102cb209052f6
---

# PO-Briefing: fix-732-export-rolle

- **Spec:** docs/specs/fast/fix-732-export-rolle.md
- **Issue:** #732
- **Erstellt:** 2026-11-27

## Was gebaut wird

Der Datenexport erkennt die richtige Rolle einer Person auch dann, wenn die Reiseseite noch nicht veröffentlicht ist.

## Definition of Done

Eine Organisatorin erhält im Export ohne veröffentlichte Seite dieselben Belege wie mit Seite; Unbekannte bleiben Gast.

## Wie geprüft wird

Ein automatischer Test mit Reise ohne Seite; nachgewiesen wird die Belegauswahl, Inhalt und Auswahl der Reisen bleiben unverändert.

## Kritische Anmerkungen

- Das Ticket nennt vorgemerkte Reisen; laut Spec landen die nicht im Export, betroffen sind Reisen ohne Seite. Wirkung enger als beschrieben.
- Nur ein Test genannt; für Mitwirkende (AC-2) und unbekannte Reise (AC-3) ist ein eigener Test nicht ausdrücklich zugesagt.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
