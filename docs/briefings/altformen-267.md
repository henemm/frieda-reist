---
spec_file: docs/specs/betrieb/altformen-entfernen-267.md
spec_sha256: 5a5aa75cebd8cd650521adc5397e524cc9bff5674b4847b05f5a2f4148000d2e
spec_frozen_sha256: f6168f23816b2c6e432d8946f0cd5223195008dd4daad78f252dd03f3a2f1bf7
---

# PO-Briefing: altformen-267

- **Spec:** docs/specs/betrieb/altformen-entfernen-267.md
- **Issue:** #267
- **Erstellt:** 2026-11-03

## Was gebaut wird

Veraltete Reiseformen verschwinden aus der Software; Reisen ohne Sprachangabe werden beim Nachziehen automatisch umgestellt, ohne Handarbeit.

## Definition of Done

Alle Reisen bauen unverändert, vier Reisen tragen automatisch die Sprache Deutsch, und fehlende Reisedatei oder Sprachangabe ergibt eine klare Fehlermeldung.

## Wie geprüft wird

Automatische Tests und Probebau beider Beispielreisen belegen Umstellung und Fehlermeldungen; die Umstellung der echten Reisen wird nur manuell nachgewiesen.

## Kritische Anmerkungen

- Abweichung: Der Einzelwert bei Merkmalen bleibt erhalten, obwohl die Anfrage ihn nennt; die Spec entscheidet das selbst.
- Zwei Kriterien (Umstellung echter Reisen, Freigabe des Entfernens der Bestandssprache) sind nur manuell prüfbar, ohne automatischen Test.

## Freigabe-Frage

Darf der Einzelwert bei Merkmalen bleiben, statt wie in der Anfrage genannt entfernt zu werden?

## Ampel

Ampel: rot
