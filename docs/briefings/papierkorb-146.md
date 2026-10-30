---
spec_file: docs/specs/oberflaeche/papierkorb-146.md
spec_sha256: 69e688fd31de5b55cac8f574535c2e9b8216d747c70bb36672418810f0b77230
spec_frozen_sha256: 2639f5a2d29178ab433d2eb2ae6a1546d74d7f4ce303b558f28bdc8ba2503d93
---

# PO-Briefing: papierkorb-146

- **Spec:** docs/specs/oberflaeche/papierkorb-146.md
- **Issue:** #146
- **Erstellt:** 2026-10-30

## Was gebaut wird

Stornierte Buchungen stehen nur noch zugeklappt als „Storniert (n)“ am jeweiligen Eintrag, nicht mehr als Karte mitten im Tag.

## Definition of Done

Die Beispielreise zeigt die stornierte Buchung nur zugeklappt unter „Storniert (1)“, ein Link darauf öffnet sie, alle Tests laufen grün.

## Wie geprüft wird

Browser-Tests belegen Verstecken, Aufklappen, Link und Zählung; Strecke, Aufenthalt und Tageskasten prüft nur ein Quelltext-Test, nicht der Browser.

## Kritische Anmerkungen

- Neu seit erster Freigabe: „Alle Möglichkeiten“ erscheint bei mehr als einer Option, zählt aber nur gültige (Entscheidung des PO).
- Ticket verlangte Sammelstelle mit Zurückholen-Knopf; beides fehlt, Zurückholen nur im Gespräch mit Frieda (Folge-Issue #149).

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
