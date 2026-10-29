---
spec_file: docs/specs/betrieb/schreibweg-zeitgrenzen.md
spec_sha256: f0e1f76cfc75be5165f07b0fb934e4bc90a4226990b5e9ec97e1c740b63e3d8c
spec_frozen_sha256: 9c68c1f020ca258706612d6b615718d1196c4fbc85267674f80d3cb2ff801864
---

# PO-Briefing: schreibweg-zeitgrenzen-118-121

- **Spec:** docs/specs/betrieb/schreibweg-zeitgrenzen.md
- **Issue:** #118 (bündelt #119, #120, #121)
- **Erstellt:** 2026-10-29

## Was gebaut wird

Zu langsame Schreibvorgänge geben der Claude-App binnen 28 Sekunden eine verständliche Meldung, ob eingetragen wurde.

## Definition of Done

Ein verlangsamter Schreibvorgang liefert der App binnen 28 Sekunden „eingetragen“ oder „nicht eingetragen“; das Protokoll zeigt jede Dauer.

## Wie geprüft wird

Automatische Tests simulieren Hänger und prüfen Fristen, Meldungen, Sperre und Protokoll; echte Last und Dauern messen sie nicht.

## Kritische Anmerkungen

- Zusatz zum Ticket: Vorgangskennung in Commits und Dauer-Protokollzeile, damit nach Abbruch prüfbar ist, ob eingetragen wurde.
- Frist 25 s plus 3 s ohne Messwerte geschätzt; große Reisen könnten regelmäßig abgebrochen werden.
- Abbruch während Übertragung kann Einträge doppelt erzeugen; Entdopplung fehlt, asynchrones Schreiben bleibt Folge-Issue.

## Freigabe-Frage

Akzeptieren Sie die geschätzte 28-Sekunden-Grenze und die zusätzliche Kennung in Commits, obwohl Dauern noch nicht gemessen wurden?

## Ampel

Ampel: rot
