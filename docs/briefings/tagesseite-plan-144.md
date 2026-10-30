---
spec_file: docs/specs/oberflaeche/tagesseite-plan.md
spec_sha256: 365a7312905777bc649b4c46e6218ac1ebb6f54f87e92f608ff3a6bec7881ea9
spec_frozen_sha256: ba254c6f16a60202d631df985ec097a4c024194afe60a24dc011eefe700f44e0
---

# PO-Briefing: tagesseite-plan-144

- **Spec:** docs/specs/oberflaeche/tagesseite-plan.md
- **Issue:** #144
- **Erstellt:** 2026-10-30

## Was gebaut wird

Bei gewähltem Plan zeigt jede Tagesseite Nummer und Datum aus diesem Plan, passend zur Übersicht.

## Definition of Done

Bei gewähltem und verworfenen Plänen zeigt jede Tagesseite dieselbe Nummer und dasselbe Datum wie die Übersicht, ohne Doppelungen.

## Wie geprüft wird

Ein Browser-Test mit Kopie der Beispielreise prüft Nummer, Datum, Blättern und Ortsseite; echte Reisen prüft er nicht.

## Kritische Anmerkungen

- Zusatz: Die Ortsseite nennt bei gewähltem Plan nur noch diesen Plan; im Ticket nicht verlangt, Entscheidung offen.
- Prüfung in einer echten Reise nach dem Veröffentlichen (Ticket-Punkt d) liegt bei Ihnen, nicht in der Spec.
- Sind mehrere Pläne vollständig gewählt, bleibt der Fehler bestehen.

## Freigabe-Frage

Soll die Ortsseite bei gewähltem Plan nur diesen Plan zeigen, und darf die Tagesseite wie beschrieben korrigiert werden?

## Ampel

Ampel: rot
