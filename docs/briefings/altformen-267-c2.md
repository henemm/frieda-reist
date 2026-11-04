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

- Jede Reise ohne Sprachfeld baut danach nicht; Nachweis liegt vor, wird vor Auslieferung erneut geprüft.
- Berichtigung: Deutsch bekommt eine eigene Kennzeichnung für die Namen der Schnittstelle, weil der Katalog nicht alle Werte enthält.
- Ticket-Kommentare waren nicht lesbar; Abgleich stützt sich auf Spec und Gesamtspec.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
