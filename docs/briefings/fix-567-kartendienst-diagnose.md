---
spec_file: docs/specs/betrieb/kartendienst-diagnose-567.md
spec_sha256: c9b37d24f210178b76f956af233b439245b9ad9408bf52ac4002b229462bd005
spec_frozen_sha256: 36ce4c792e72fa4db50be518818d066b812fc854969fc3b06d3bb7116581f0f9
---

# PO-Briefing: fix-567-kartendienst-diagnose

- **Spec:** docs/specs/betrieb/kartendienst-diagnose-567.md
- **Issue:** #567
- **Erstellt:** 2026-11-14

## Was gebaut wird

Fällt der eigene Kartendienst aus, hinterlässt der Wechsel zum öffentlichen Dienst künftig eine Protokollzeile mit Grund.

## Definition of Done

Gesamtläufe der Tests bleiben mehrfach grün, die Protokollzeile erscheint bei Ausfall, das Ticket schließt erst nach Beobachtung im Betrieb.

## Wie geprüft wird

Fünf neue Tests belegen Protokollzeile und sauberes Beenden des Test-Stummels; ob der seltene Fehler behoben ist, weist nichts nach.

## Kritische Anmerkungen

- Ticket verlangte Ursache klären und Test deterministisch machen; geliefert wird nur Beobachtbarkeit, der Fehler kann wiederkehren.
- Protokollzeile steht nur im Journal; weder Alarm noch Überwachung bei Ausfall des eigenen Kartendienstes.

## Freigabe-Frage

Akzeptierst du, dass die Ursache offen bleibt und das Ticket erst nach Beobachtung im Betrieb geschlossen wird?

## Ampel

Ampel: rot
