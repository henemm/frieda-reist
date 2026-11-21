---
spec_file: docs/specs/betrieb/protokolle-pytest-tmp-602.md
spec_sha256: 30b30eb3ec490a99f61e49a9fb6956526046ff4901327974aed2c0d76207c2a5
spec_frozen_sha256: 67b5617fe430f339a72bdd4af28400aefbee26cf950c96a4dd53c66f617cdc58
---

# PO-Briefing: fix-602-pytest-tmp-pfade

- **Spec:** docs/specs/betrieb/protokolle-pytest-tmp-602.md
- **Issue:** #602
- **Erstellt:** 2026-11-21

## Was gebaut wird

Öffentliche Testprotokolle verraten den Benutzernamen des Servers nicht mehr, und eine Schutzprüfung verhindert das künftig.

## Definition of Done

Kein veröffentlichtes Protokoll enthält mehr einen echten Benutzernamen, die neue Prüfung schlägt bei einem Namen an, und alle Pflichtprüfungen sind grün.

## Wie geprüft wird

Automatische Tests zeigen, dass Namen erkannt und Platzhalter akzeptiert werden; die Bereinigung der Protokolle prüft nur eine manuelle Suche.

## Kritische Anmerkungen

- Die Prüfung ist breiter als verlangt: Sie greift auch ohne Ordnerpfad und kann harmlose Texte melden. Folge: gelegentlich Platzhalter nötig.
- Betroffen sind 35 Dateien statt der im Ticket genannten rund 30; rein textuelle Ersetzung.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
