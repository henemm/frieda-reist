---
spec_file: docs/specs/betrieb/altformen-sprache-bestand-267-c2.md
spec_sha256: b8ecd392b425e7c5fe537f5a05051e125d50434015b11a8d780120865bd053c5
spec_frozen_sha256: 2696e658516554405c58851abe1e116ed8a95c17a78ebd847b30c333c20bb6b0
---

# PO-Briefing: altformen-267-c2

- **Spec:** docs/specs/betrieb/altformen-sprache-bestand-267-c2.md
- **Issue:** #267
- **Erstellt:** 2026-11-04

## Was gebaut wird

Reisen ohne Sprachangabe gelten nicht mehr stillschweigend als deutsch; der Bau meldet stattdessen einen klaren Fehler.

## Definition of Done

Eine Reise ohne Sprachangabe wird abgelehnt, nach dem Nachziehen baut sie deutsch, beide Beispielreisen bleiben unverändert, alle Tests laufen grün.

## Wie geprüft wird

Automatische Tests prüfen Fehlermeldung, Nachziehen und Einstellung; Gleichheit der Beispielreisen und der echten Reisen belegt nur ein Handnachweis im PR-Text.

## Kritische Anmerkungen

- Jede Reise ohne Sprachfeld baut danach nicht; Nachweis liegt vor (8 von 8 Reisen), wird vor Auslieferung erneut geprüft.
- Ticket-Kommentare waren nicht direkt lesbar; Abgleich stützte sich auf Spec und Kontextdokument.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
