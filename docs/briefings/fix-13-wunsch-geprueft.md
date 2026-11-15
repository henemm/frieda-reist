---
spec_file: docs/specs/fast/fix-13-wunsch-geprueft.md
spec_sha256: 7a57850880659faee34be5d7215f1231636c09f7154c75901b026b97317b3ba3
spec_frozen_sha256: ebddff36b5d7744f1154a7cc95f5f24cea421279ce1216498ee84130c607f261
---

# PO-Briefing: fix-13-wunsch-geprueft

- **Spec:** docs/specs/fast/fix-13-wunsch-geprueft.md
- **Issue:** #13
- **Erstellt:** 2026-11-15

## Was gebaut wird

Ein Wunsch, zu dem die KI einen Vorschlag eingetragen hat, steht im Wunsch-Brett sofort unter „geprüft“.

## Definition of Done

Nach einem Vorschlag der KI zeigt das Brett den Wunsch unter „geprüft“; Bilanz und Kontingent bleiben gleich, Einplanen bleibt Organisator:innen vorbehalten.

## Wie geprüft wird

Ein automatischer Test deckt Vorschlag, „passt nicht“ und gewählte Option ab; ein manueller Durchlauf mit der Beispielreise ergänzt ihn.

## Kritische Anmerkungen

- Die Spec korrigiert nur die Spalte; die Prüfung selbst (Lage, Saison, Öffnungszeiten) war schon da und wird nicht neu getestet.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
