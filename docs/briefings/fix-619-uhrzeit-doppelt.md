---
spec_file: docs/specs/oberflaeche/uhrzeit-doppelt-619.md
spec_sha256: c1fb9a4939d4164a1ab6a06a18b278dd6ccf54dd63dbcec9292ae7530baa0eb1
spec_frozen_sha256: f66f78fe16770260f3ba220dce2518da5b1fc757149a14474a16e0277953be7c
---

# PO-Briefing: fix-619-uhrzeit-doppelt

- **Spec:** docs/specs/oberflaeche/uhrzeit-doppelt-619.md
- **Issue:** #619
- **Erstellt:** 2026-11-22

## Was gebaut wird

Die Uhrzeit eines Aufenthalts erscheint auf der Seite, im Assistenten und im Kalender nur noch einmal statt doppelt.

## Definition of Done

Bei der Burg Hohnstein steht nur noch „nach der Wanderung“ plus 16:00–18:00 Uhr; beim Stadtwochenende erscheint die Uhrzeit überall genau einmal.

## Wie geprüft wird

Automatische Tests an beiden Beispielreisen belegen die einmalige Uhrzeit und unveränderte Reisedaten; das Aussehen im Browser prüft kein Test.

## Kritische Anmerkungen

- Der Kalender war im Ticket nicht genannt, wird aber mitgeändert; gleiche Ursache, kleine Erweiterung.
- Ungewöhnliche Schreibweisen („ab 16 Uhr“, abweichende Zeiten) bleiben bewusst unverändert, die Uhrzeit kann dort weiter doppelt erscheinen.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
