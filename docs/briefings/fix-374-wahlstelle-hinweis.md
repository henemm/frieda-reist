---
spec_file: docs/specs/fast/fix-374-wahlstelle-hinweis.md
spec_sha256: 38f493df732309c0a036cd53f42f219471a8aa6ce05bd5d7ea822ac600ec4c4e
spec_frozen_sha256: d514461a6cb3174cb2ce5fd5c2a984d2f0083322ded18f1c984fcd7d7a8ef77c
---

# PO-Briefing: fix-374-wahlstelle-hinweis

- **Spec:** docs/specs/fast/fix-374-wahlstelle-hinweis.md
- **Issue:** #374
- **Erstellt:** 2026-11-06

## Was gebaut wird

Die Meldung beim Anlegen einer Wahlstelle ohne Optionen nennt künftig alle fünf möglichen Inhalte einer Option, auf Deutsch und Englisch.

## Definition of Done

Wer eine Wahlstelle ohne Optionen anlegt, bekommt in beiden Sprachen eine Meldung mit Unterkünften, Strecken, Aufenthalten, Orten und Folge.

## Wie geprüft wird

Ein Test prüft, dass beide Sprachtexte alle fünf Sorten nennen; dass die Ablehnung selbst unverändert bleibt, prüft er nicht eigens.

## Kritische Anmerkungen

- AC-3 (Verhalten unverändert) hat keinen eigenen Test; es ändert sich aber laut Spec nur ein Text. Information, keine Entscheidung.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
