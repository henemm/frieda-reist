---
spec_file: docs/specs/betrieb/speicher-350-stufe5.md
spec_sha256: 10469c7501ae3a17ca7e54cfb72656f449564722515ba47554c1563250d24f11
spec_frozen_sha256: 080ba43f5e2ce9648e3bf731cff245d7313353c334784c118260b6cd69394eb2
---

# PO-Briefing: speicher-stufe5-350

- **Spec:** docs/specs/betrieb/speicher-350-stufe5.md
- **Issue:** #350
- **Erstellt:** 2026-11-09

## Was gebaut wird

Reisen lassen sich abgesichert einzeln auf den neuen Speicher umschalten, und das Veröffentlichen übersteht einen GitHub-Ausfall.

## Definition of Done

Eine Reise ohne bestandenen Vergleich lässt sich nicht umschalten, und bei GitHub-Ausfall bleibt das Veröffentlichen der Speicher-Reisen grün.

## Wie geprüft wird

Automatische Tests prüfen jede Anforderung an beiden Beispielreisen; echte Umschaltung, Rückspielversuch der Sicherung und Zeitmessung gehören nicht dazu.

## Kritische Anmerkungen

- Abweichung vom Ticket: Die GitHub-Workflows entfallen nicht, sondern bleiben bis zu einem Folge-Issue (#454) bestehen.
- Sicherung außer Haus und Zurücksetzen sind nur Dokumentation beziehungsweise schon gebaut; das Ticket ist erst nach der Umschaltung echter Reisen erfüllt.

## Freigabe-Frage

Sollen die GitHub-Workflows wie im Ticket verlangt jetzt entfallen, oder wie vorgeschlagen später im Folge-Issue #454?

## Ampel

Ampel: rot
