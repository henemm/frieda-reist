---
spec_file: docs/specs/fast/fix-685-bausteine.md
spec_sha256: c17402c7a9927786cc09dbab2d3e1da08ebf00a5da79804b198fefadab4d856d
spec_frozen_sha256: b5cf04c6a57912597a4ea7920616260c29972646aeda750af6b8fc73ada20b5a
---

# PO-Briefing: fix-685-bausteine

- **Spec:** docs/specs/fast/fix-685-bausteine.md
- **Issue:** #685
- **Erstellt:** 2026-11-24

## Was gebaut wird

Drei Kartentests prüfen wieder mit genau dem gewünschten Funktionsumfang statt still mit allen Funktionen der Beispielreise.

## Definition of Done

Die drei Kartentests laufen grün mit dem gewünschten Satz, und eine nicht passende Einstellungszeile lässt den Test laut scheitern.

## Wie geprüft wird

Die Kartentests laufen erneut, und ein Zusatztest belegt das laute Scheitern; am Produkt selbst ändert sich nichts.

## Kritische Anmerkungen

- Ob die Tests mit dem gewünschten Satz noch dasselbe prüfen, ist offen; Erwartungen könnten angepasst werden, dann im PR erklärt.
- Der Zusatztest ist erst während der Umsetzung geplant, noch nicht geschrieben.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
