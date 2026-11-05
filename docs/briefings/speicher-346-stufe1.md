---
spec_file: docs/specs/betrieb/reisespeicher-346.md
spec_sha256: 740de4e6a9c97b1773c9f1b5fd5786331ae3f17c20d3f701f720630c3046fc94
spec_frozen_sha256: 018605695e1c939a67ca7183975c8a343a285bfb3bba7ce5d5827286fca8a01b
---

# PO-Briefing: speicher-346-stufe1

- **Spec:** docs/specs/betrieb/reisespeicher-346.md
- **Issue:** #346
- **Erstellt:** 2026-11-05

## Was gebaut wird

Reisedaten liegen in einer Datenbank mit unveränderlichem Verlauf und lassen sich zurückholen, zurücksetzen und täglich sichern.

## Definition of Done

Beide Beispielreisen kommen Byte-gleich aus der Datenbank zurück, der Verlauf ist nicht änderbar, die tägliche Sicherung samt Rückspieltest läuft.

## Wie geprüft wird

Automatische Tests belegen jede Anforderung; nicht bewiesen ist Schutz gegen jemanden, der die Datei direkt bearbeitet.

## Kritische Anmerkungen

- Stand-Nummer zählt Schreibvorgänge statt, wie im Ticket wörtlich, Datei-Versionen; zusätzlich Spalten Titel und Rolle.
- Ticket-Text nicht abrufbar; nur gegen das Kontextdokument geprüft.

## Freigabe-Frage

Soll die Stand-Nummer wie heute je Schreibvorgang um eins steigen, statt je geänderter Datei?

## Ampel

Ampel: rot
