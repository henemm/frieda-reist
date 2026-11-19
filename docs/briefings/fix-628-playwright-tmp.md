---
spec_file: docs/specs/betrieb/playwright-tmp-tests.md
spec_sha256: af0343f3db3bc672a7c2cec307e3b816e518b30e9c956ea73edc27088e29324c
spec_frozen_sha256: e0a6eaf1ef04af4e521c94bbe3a8dac4f63c4484e011212a2762e34cf9cf4684
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

- Abweichung: Verlangt war eine Größengrenze per Test; die Spec prüft nur auf Browserkopien. Andere Platzfresser blieben unentdeckt.
- Der Wächter sucht nur bis Tiefe 3 unter bekanntem Namen; künftige Varianten könnten durchrutschen.

## Freigabe-Frage

Genügt ein Wächter nur gegen Browserkopien, oder soll wie verlangt eine allgemeine Größengrenze je Test-Ordner gelten?

## Ampel

Ampel: rot
