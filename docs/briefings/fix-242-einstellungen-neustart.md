---
spec_file: docs/specs/betrieb/veroeffentlichen-neustart-242.md
spec_sha256: 936168fa5bdc9c18b886815a35225ee5bccf747f5295f5a18b338080c6fbdae3
spec_frozen_sha256: f9603bfb7979c7988abb7a5ef64e4d36a8c9ff550f728d88761b951ca31d598b
---

# PO-Briefing: fix-242-einstellungen-neustart

- **Spec:** docs/specs/betrieb/veroeffentlichen-neustart-242.md
- **Issue:** #242
- **Erstellt:** 2026-11-02

## Was gebaut wird

Geänderte Einstellungen einer Instanz, etwa die Adresse, gelten schon im selben Veröffentlichungslauf statt erst im nächsten.

## Definition of Done

Nach einer Änderung der Adresse im Reisen-Repo baut und schaltet der erste Lauf bereits mit dem neuen Wert frei.

## Wie geprüft wird

Automatische Tests prüfen neuen Wert, Vorrang des Aufrufs, keine Endlosschleife und erhaltene Optionen; das Verhalten auf dem echten Server prüft nur die Abnahme im Betrieb.

## Kritische Anmerkungen

- Zusatz: Eine geänderte Skriptfassung aus dem Submodul wirkt ebenfalls sofort; im Ticket nicht verlangt, aber harmlos.
- Dokumentations-Anforderung (AC-10) hat keinen automatischen Test.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
