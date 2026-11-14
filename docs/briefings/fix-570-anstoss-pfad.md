---
spec_file: docs/specs/betrieb/anstoss-pfad-570.md
spec_sha256: 0c4745377044e038ea58a5ac79462a34ddfb77a6a48f0fa5436d3690b3eb4e4b
spec_frozen_sha256: b3e10dcace3a8f036bb31c962120b7c41ba5f7b5e52b5d06e484eed7cdfddf36
---

# PO-Briefing: fix-570-anstoss-pfad

- **Spec:** docs/specs/betrieb/anstoss-pfad-570.md
- **Issue:** #570
- **Erstellt:** 2026-11-14

## Was gebaut wird

Änderungen aus der Claude-App erscheinen auf der Seite wieder nach Sekunden statt erst nach bis zu fünf Minuten.

## Definition of Done

Nach einer Änderung in der Claude-App zeigt die Seite den neuen Stand binnen Sekunden, und das Anstoß-Protokoll bekommt wieder einen Eintrag.

## Wie geprüft wird

Automatische Tests belegen die Pfadwahl in beiden Anordnungen und die Meldung bei fehlendem Skript; die Wirkung auf dem Server wird manuell abgenommen.

## Kritische Anmerkungen

- Keine — Spec deckt die Anfrage ab, jede Anforderung hat einen Test.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
