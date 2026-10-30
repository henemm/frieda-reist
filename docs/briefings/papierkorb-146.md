---
spec_file: docs/specs/oberflaeche/papierkorb-146.md
spec_sha256: f071aef63eeff621cb61e0bcf5c73b9f50442c7e5110f40a26604c839545586a
spec_frozen_sha256: 2f869c051215c96aab282189e7fd1722a198305642b5e7440e5cdd5b039d2066
---

# PO-Briefing: papierkorb-146

- **Spec:** docs/specs/oberflaeche/papierkorb-146.md
- **Issue:** #146
- **Erstellt:** 2026-10-30

## Was gebaut wird

Stornierte Buchungen verschwinden aus dem Tagesverlauf und stehen nur noch in einer zugeklappten Zeile „Storniert“ am jeweiligen Eintrag.

## Definition of Done

Die Beispielreise zeigt die stornierte Buchung nur zugeklappt unter „Storniert (1)“, ein Link darauf öffnet sie, alle Tests laufen grün.

## Wie geprüft wird

Browser-Tests belegen Verstecken, Aufklappen, Link und Zählung; Strecke, Aufenthalt und Tageskasten prüft nur ein Quelltext-Test, nicht der Browser.

## Kritische Anmerkungen

- Ticket verlangte Sammelstelle mit Zurückholen-Knopf; beides fehlt, Zurückholen nur im Gespräch mit Frieda (Folge-Issue #149).
- Aufgaben und Fragen bleiben unverändert; nur Buchungen werden eingeklappt.

## Freigabe-Frage

Genügt dir „zugeklappt am Eintrag“ mit Zurückholen im Gespräch mit Frieda, statt einer Sammelstelle mit Zurückholen-Knopf?

## Ampel

Ampel: rot
