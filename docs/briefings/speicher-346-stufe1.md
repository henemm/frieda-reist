---
spec_file: docs/specs/betrieb/reisespeicher-346.md
spec_sha256: 60493c4a440cca895eebe3a6803cf86ce13ba1e361da3b3eb19e2761fda7e894
spec_frozen_sha256: 26f3a0796f0c6893e1dbca1c6c81804bfe74275cd7dd45d13fc97b5f99d88b6e
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
- Issue-Text nicht abrufbar; geprüft gegen das Kontextdokument.

## Freigabe-Frage

Soll die Stand-Nummer wie heute je Schreibvorgang um eins steigen, statt je geänderter Datei?

## Ampel

Ampel: rot
