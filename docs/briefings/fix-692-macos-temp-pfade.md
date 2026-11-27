---
spec_file: docs/specs/fast/fix-692-macos-temp-pfade.md
spec_sha256: cac6facf688c8f6c56d1ed10cb22de0a237db73c6ab43a4cf81823d8fdde309b
spec_frozen_sha256: dee6c256fcf0fb50507414c79789bc33e5990a589bc7047bc67a194d497c5d02
---

# PO-Briefing: fix-692-macos-temp-pfade

- **Spec:** docs/specs/fast/fix-692-macos-temp-pfade.md
- **Issue:** #692
- **Erstellt:** 2026-11-27

## Was gebaut wird

Die Protokollprüfung schlägt künftig auch an, wenn ein Protokoll Temp-Ordner eines Mac-Rechners nennt.

## Definition of Done

Die Prüfung meldet Mac-Temp-Pfade unter „/private/var/…“, „/private/tmp/…“ und „/var/folders/…“, und das bereinigte Protokoll von #694 besteht sie.

## Wie geprüft wird

Ein neuer Testfall belegt erkannte und erlaubte Pfadformen, die Prüfung läuft über alle Protokolle; künftige Protokolle bleiben nur durch diese Prüfung abgesichert.

## Kritische Anmerkungen

- Leichte Abweichung: „/private/var/folders“ wird nur mit echtem Namen dahinter gemeldet, gekürzte Schreibweise mit „…“ bleibt erlaubt.
- Zusatz zum Ticket: Das Protokoll von #694 (198 Zeilen plus gekürzte Reste) wird mitbereinigt.
- Einfaches „/tmp/…“ bleibt bewusst erlaubt, weil es keinen Rechner verrät.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
