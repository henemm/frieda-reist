---
spec_file: docs/specs/betrieb/veroeffentlichen-eigener-dienst-624.md
spec_sha256: 971bab758735b112673fd6505f81750016ce5f57c9ea28152c80f6c6dd9768e8
spec_frozen_sha256: 0c2b8d59578fa56e5de3a20b02d94a56d609ca293be8c0bd8d8aa9b053316924
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

Automatische Tests belegen Auslöser, Einheit, Grenzen und Doku; Zeitziel und Umstellung der echten Instanz werden nur manuell nachgewiesen.

## Kritische Anmerkungen

- Zusätzlich zum Ticket sinkt der Auslagerungsspeicher des Schreibdienstes von 1G auf 256M; fachlich unkritisch.
- Bis zur einmaligen Umstellung der Instanz dauert Veröffentlichen bis zu fünf Minuten; Claude führt sie bei der Auslieferung aus.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
