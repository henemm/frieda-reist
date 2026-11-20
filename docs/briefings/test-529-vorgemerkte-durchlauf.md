---
spec_file: docs/specs/betrieb/vorgemerkte-durchlauf-529.md
spec_sha256: 7aaebb59a6ba160f54dc198672e77724c99b4a8eb41c02979dddeedf1a1f3d2c
spec_frozen_sha256: bef521d049a528df86e21181044ab61e749dddd63041ea431d5a40b6c4cadcb2
---

# PO-Briefing: test-529-vorgemerkte-durchlauf

- **Spec:** docs/specs/betrieb/vorgemerkte-durchlauf-529.md
- **Issue:** #529
- **Erstellt:** 2026-11-20

## Was gebaut wird

Automatische Tests beweisen, dass das Veröffentlichen eine zum Löschen vorgemerkte Reise tatsächlich auslässt und ihre Seite entfernt.

## Definition of Done

Alle sieben Prüfungen laufen grün, ohne dass am Veröffentlichen etwas geändert wurde, und die bestehende Gesamtprüfung bleibt grün.

## Wie geprüft wird

Echte Veröffentlichungsläufe mit beiden Beispielreisen, neuer und alter Ablauf, inklusive Zurückholen und kaputter Liste; nicht geprüft: Reisen aus Git.

## Kritische Anmerkungen

- Das Ticket nennt den Filter für Git-Reisen mit; die Spec lässt ihn weg, weil Löschen dort ohnehin unmöglich ist.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
