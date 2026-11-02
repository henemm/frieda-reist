---
spec_file: docs/specs/oberflaeche/eine-seitenordnung-214.md
spec_sha256: eff02083f20d618cc438dbad72618678be98c0af76603022b2fb6d11d2d2015d
spec_frozen_sha256: 4a699ee802b442b10c05e49c91602092fee2b745833b8a2c313f11bd80106a8a
---

# PO-Briefing: fix-214-eine-seitenordnung

- **Spec:** docs/specs/oberflaeche/eine-seitenordnung-214.md
- **Issue:** #214
- **Erstellt:** 2026-11-02

## Was gebaut wird

Jede Reise, auch neue, bekommt dieselbe Seitenordnung; Buchungen und Unterkünfte stehen nur noch einmal vollständig da.

## Definition of Done

Frische Testreise und Beispielreise zeigen Zeitachse und je Ding eine vollständige Stelle; Fotos der Rundreise vorher und nachher sind abgenommen.

## Wie geprüft wird

Tests zählen in vier Reisefällen jedes Ding und jede Kennung; das Aussehen echter Reisen prüft nur die manuelle Abnahme.

## Kritische Anmerkungen

- Fünf Entscheidungen, je mit Empfehlung: Pläne offen als Zeitachse; Tagesseiten immer; Tiefe nur Plan-Baum; Plan-Reiter nach Wissen; Etappen früher.
- Drei echte Reisen ändern ihr Aussehen, die Rundreise am stärksten.
- Etappen bei offenen Plänen (Entscheidung 5) hat keinen eigenen Test.

## Freigabe-Frage

Stimmst du allen fünf Empfehlungen zu, oder soll eine davon anders entschieden werden?

## Ampel

Ampel: rot
