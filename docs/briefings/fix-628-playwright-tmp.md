---
spec_file: docs/specs/betrieb/playwright-tmp-tests.md
spec_sha256: 846da7994dd4e13463ee9a133dad98817b0004afe9dc57d5a086f30c6320a21d
spec_frozen_sha256: 84e4f0dc35eeb9c333b692fc7292b1f677589ee6f9cb1f48f973dca3ef04680a
---

# PO-Briefing: fix-628-playwright-tmp

- **Spec:** docs/specs/betrieb/playwright-tmp-tests.md
- **Issue:** #628
- **Erstellt:** 2026-11-19

## Was gebaut wird

Testläufe legen keine 930-MB-Browserkopie je Test mehr an, und eine Prüfung schlägt an, falls das wiederkehrt.

## Definition of Done

Ein paralleler Testlauf belegt deutlich unter 1 GB temporären Platz statt bis zu 38 GB, und alle Pflichtprüfungen sind grün.

## Wie geprüft wird

Automatische Tests belegen, dass keine Kopie entsteht und der Wächter anschlägt; die Platzmessung des Gesamtlaufs erfolgt nur manuell.

## Kritische Anmerkungen

- Statt einer Größengrenze je Test prüft der Wächter nur auf Browserkopien; andere Platzfresser blieben unentdeckt. Begründet, Ziel des Tickets bleibt erfüllt.
- Der Wächter sucht nur bis Tiefe 3; drei bestehende Tests stehen auf einer Ausnahmeliste.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
