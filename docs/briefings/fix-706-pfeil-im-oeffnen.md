---
spec_file: docs/specs/oberflaeche/pfeil-im-oeffnen-706.md
spec_sha256: 3b36c520736aaba4cc52addaaa7a42dcc6efb0866c2eff2cdc200284f54d5d08
spec_frozen_sha256: 6220dc8d0ab8ed0ce911d4e3eeca75ee1c0b85bd43a45d3f75e4e9ce60dbea7c
---

# PO-Briefing: fix-706-pfeil-im-oeffnen

- **Spec:** docs/specs/oberflaeche/pfeil-im-oeffnen-706.md
- **Issue:** #706
- **Erstellt:** 2026-11-27

## Was gebaut wird

Der Pfeilknopf in der Großansicht reagiert erst, wenn die Ansicht fertig geöffnet ist, und zeigt dann nie ein leeres Bild.

## Definition of Done

Pfeil während des Öffnens bleibt wirkungslos, danach blättert er normal, und „Foto entfernen“ meint immer das gezeigte Foto.

## Wie geprüft wird

Automatische Browsertests in Chromium und WebKit prüfen Pfeil im Öffnen, Blättern danach und Löschen; echte Geräte werden nicht geprüft.

## Kritische Anmerkungen

- Ein Pfeildruck während der rund 0,4 Sekunden des Öffnens geht verloren; man muss erneut drücken, wie bei Pfeiltaste und Wischen.
- Früheres Verhalten aus #689 ändert sich: Klick auf „Foto entfernen“, dann Pfeil blättert nicht mehr; die Frage kommt nach dem Öffnen.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
