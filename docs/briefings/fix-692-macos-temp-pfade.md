---
spec_file: docs/specs/fast/fix-692-macos-temp-pfade.md
spec_sha256: 9148ccb55843e4bd4880dc5ea5e104efcb91afc32363633f897d08d396f5798d
spec_frozen_sha256: ed21d4f44951fd8b785271fb55e3f35b66871d424e6b950f20a778cb45fc4dba
---

# PO-Briefing: fix-692-macos-temp-pfade

- **Spec:** docs/specs/fast/fix-692-macos-temp-pfade.md
- **Issue:** #692
- **Erstellt:** 2026-11-27

## Was gebaut wird

Die Protokollprüfung schlägt künftig auch an, wenn ein Protokoll Temp-Ordner eines Mac-Rechners nennt.

## Definition of Done

Die Prüfung meldet Mac-Temp-Pfade unter „/private/var/…“, „/private/tmp/…“ und „/var/folders/…“, und die bereinigten Protokolle von #694 und #656 bestehen sie.

## Wie geprüft wird

Ein neuer Testfall belegt erkannte und erlaubte Pfadformen, die Prüfung läuft über alle Protokolle; sonst ist nichts abgesichert.

## Kritische Anmerkungen

- Abweichung vom Wortlaut: „/private/var/folders“ wird nur mit echtem Namen dahinter gemeldet, gekürzte Schreibweise mit „…“ bleibt erlaubt.
- Zusatz: Protokoll von #694 (198 Zeilen) und eine Zeile in #656 werden mitbereinigt; #656 hast du freigegeben.
- Einfaches „/tmp/…“ bleibt bewusst erlaubt, weil es keinen Rechner verrät.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
