---
spec_file: docs/specs/betrieb/wackelige-browsertests-568.md
spec_sha256: 3d1301e069250440ba09fdf6693cc1ab7822052dc6ccea2baa1491d56894cdb7
spec_frozen_sha256: 8818e952ab588d07af2886aa3ef7c61230b47ca17fc15255c63566e7f8f2975a
---

# PO-Briefing: fix-568-kartenlegende-wackelig

- **Spec:** docs/specs/betrieb/wackelige-browsertests-568.md
- **Issue:** #568
- **Erstellt:** 2026-11-21

## Was gebaut wird

Der Browsertest der Kartenlegende läuft nicht mehr zufällig rot, weil er auf den fertig geladenen Seitenzustand wartet.

## Definition of Done

Zwanzig Wiederholungsläufe beider betroffenen Browsertests unter Last bleiben grün, danach sind alle Pflichtprüfungen auf der Hauptversion grün.

## Wie geprüft wird

Automatische Tests belegen, dass die Seite das Fertig-Signal immer setzt und danach nicht mehr neu zeichnet; die 20 Wiederholungen laufen manuell.

## Kritische Anmerkungen

- Die Seite bekommt ein unsichtbares Fertig-Signal; das Ticket nannte nur den Test als Ort der Korrektur. Für Nutzer unverändert.
- Zusätzlich wird ein zweiter Bildtest mit demselben Fehlermuster korrigiert; im Ticket nicht genannt.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
