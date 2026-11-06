---
spec_file: docs/specs/betrieb/schreibweg-speicher-347.md
spec_sha256: e517cd7b740232171cf0647edd8c0d7c20fbf745e8f5fbfe4b17a19e9bfeecfd
spec_frozen_sha256: a1650f5c42f12147c93e4c34c706b328c5781f975ea0b897721c5d6ffe112cdb
---

# PO-Briefing: speicher-347-stufe2

- **Spec:** docs/specs/betrieb/schreibweg-speicher-347.md
- **Issue:** #347
- **Erstellt:** 2026-11-06

## Was gebaut wird

Änderungen an Reisen werden in einer Datenbank statt über Git gespeichert, je Reise umschaltbar.

## Definition of Done

Alle Tests sind grün, keine echte Reise ist umgeschaltet, und die Messwerte im Issue zeigen keine Zeitüberschreitungen und deutlich kürzere Spitzenzeiten.

## Wie geprüft wird

Automatische Tests prüfen Speicherweg, Ablehnungen und Kein-Git an beiden Beispielreisen; die echte Geschwindigkeit auf dem Server zeigt nur der manuelle Messlauf.

## Kritische Anmerkungen

- Das Tempoziel (deutlich unter 25 s) ist nur durch manuellen Messlauf auf dem Server belegt, nicht automatisch.
- Umgeschaltete Reisen werden bis Stufe 3 nicht neu veröffentlicht; deshalb schaltet vorerst keine echte Reise um.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
