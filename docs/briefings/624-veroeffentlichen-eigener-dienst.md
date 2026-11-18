---
spec_file: docs/specs/betrieb/veroeffentlichen-eigener-dienst-624.md
spec_sha256: 063a2c48896f6bcceb795c8391e5f4614988838f7c745eddae698b3bda3b8971
spec_frozen_sha256: 3bbf046bb673deae47c731d79f5d28784adb77f846de906e288d214319694f74
---

# PO-Briefing: 624-veroeffentlichen-eigener-dienst

- **Spec:** docs/specs/betrieb/veroeffentlichen-eigener-dienst-624.md
- **Issue:** #624
- **Erstellt:** 2026-11-18

## Was gebaut wird

Das Veröffentlichen nach dem Speichern läuft als eigener Dienst, sodass der Schreibdienst mit viel weniger Speicher auskommt.

## Definition of Done

Nach einem Eintrag ist die Seite binnen zwei Minuten aktuell, der Schreibdienst läuft mit 512 MB ohne Abbruch, die Instanz ist umgestellt.

## Wie geprüft wird

Automatische Tests belegen Merker, Einheit, Grenzen und Doku; Zeitziel und Umstellung der echten Instanz werden nur manuell nachgewiesen.

## Kritische Anmerkungen

- Zusätzlich zum Ticket sinkt auch der Auslagerungsspeicher des Schreibdienstes von 1G auf 256M; fachlich unkritisch.
- Bis zur einmaligen Umstellung der Instanz dauert Veröffentlichen bis zu fünf Minuten; Claude führt sie bei der Auslieferung aus.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
