---
spec_file: docs/specs/fast/fix-369-legende-flake.md
spec_sha256: 969b06da9aa754248c59ac9233c771553b4ddb0c8262b67339c298a8d0bfd9e9
spec_frozen_sha256: e252be97906799acb477b1037d2998dcc2365d732e3ebf76cb183689f7d77d09
---

# PO-Briefing: fix-369-legende-flake

- **Spec:** docs/specs/fast/fix-369-legende-flake.md
- **Issue:** #369
- **Erstellt:** 2026-11-06

## Was gebaut wird

Der Test der Kartenlegende wartet, bis die Legende sichtbar ist, und schlägt dadurch nicht mehr zufällig fehl.

## Definition of Done

Der Legenden-Test läuft in allen vier Varianten grün, auch mindestens fünfmal hintereinander unter Last, ohne dass die schmale Variante schwankt.

## Wie geprüft wird

Ein Test sichert den Wartepunkt ab; dass die Schwankung wirklich weg ist, zeigen nur wiederholte Läufe, kein Beweis.

## Kritische Anmerkungen

- Die Ursache ist nur vermutet, der Fehler trat einmal auf; die Wiederholungsläufe sind daher kein sicherer Nachweis.
- Die Software selbst bleibt unverändert; nur das Messskript des Tests wird angepasst.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
