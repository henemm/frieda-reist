---
spec_file: docs/specs/fast/fix-656-vorab-ordner-faden.md
spec_sha256: b6587337a0710b89f783334222a32371a86239e122d01e505e18b8aab5dc5011
spec_frozen_sha256: 1ff619e09962fb885f8ec5d5b8d39503a950725b2cd41adbaa3fb3179660f0ee
---

# PO-Briefing: fix-656-vorab-ordner-faden

- **Spec:** docs/specs/fast/fix-656-vorab-ordner-faden.md
- **Issue:** #656
- **Erstellt:** 2026-11-25

## Was gebaut wird

Ein gelegentlich rot werdender Test wird stabil, indem er auf nachlaufende Hintergrundvorgänge wartet, bevor aufgeräumt wird.

## Definition of Done

Alle vier Fälle des Tests laufen 30-mal hintereinander und in der CI grün, ohne dass der Ordnerfehler wieder auftritt.

## Wie geprüft wird

Neue Tests belegen Warten, Zeitgrenze und Fehlerfall; der Ausfall wird gezielt nachgestellt, beweist aber nicht, dass der CI-Fehler genau so entstand.

## Kritische Anmerkungen

- Ursache im CI-Lauf nur nachgestellt, nicht bewiesen; tritt der Fehler erneut auf, wäre es ein anderer Weg.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
