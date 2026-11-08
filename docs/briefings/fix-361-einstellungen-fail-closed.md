---
spec_file: docs/specs/betrieb/einstellungen-fail-closed-361.md
spec_sha256: 2f7a03d5cdce1f09e0d9bcc655c11db9f3c7a1a4073119715b0e7a8d8fce600d
spec_frozen_sha256: 0aa4d40f000387850286d64032ca550879fa15efc64a6eb5cb1ea73c501ac367
---

# PO-Briefing: fix-361-einstellungen-fail-closed

- **Spec:** docs/specs/betrieb/einstellungen-fail-closed-361.md
- **Issue:** #361
- **Erstellt:** 2026-11-08

## Was gebaut wird

Wenn die Einstellungsdatei nicht lesbar ist, lehnt der Dienst Speicher-Reisen mit Fehler ab, statt sie fälschlich über Git zu führen.

## Definition of Done

Bei vorhandener, unlesbarer Einstellungsdatei antwortet der Schreibdienst mit 503 statt über Git zu schreiben; eine fehlende Datei verhält sich unverändert.

## Wie geprüft wird

Automatische Tests belegen jede Anforderung; entzogene Dateirechte werden unter root nur ersatzweise geprüft.

## Kritische Anmerkungen

- Über das Ticket hinaus stoppt ein Lesefehler auch Statusabfrage, Buchungsabfrage, Seitenbau und Veröffentlichen, nicht nur das Schreiben.
- Veröffentlichen bricht künftig ab, wo es bisher still weiterlief.

## Freigabe-Frage

Soll ein Lesefehler auch Seitenbau, Veröffentlichen, Status- und Buchungsabfrage stoppen, nicht nur das Schreiben?

## Ampel

Ampel: rot
