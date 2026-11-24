---
spec_file: docs/specs/betrieb/vormerkung-frist-649.md
spec_sha256: 1dbd8f0a3a3d6cb7b6489bf8026719b8f633142ad01a5f3d685042e038b154e6
spec_frozen_sha256: dcaa14ce565bd95ddca8b4f90390fef854638963b2536f3532ee1daa75381e7b
---

# PO-Briefing: fix-649-vormerkung-frist

- **Spec:** docs/specs/betrieb/vormerkung-frist-649.md
- **Issue:** #649
- **Erstellt:** 2026-11-24

## Was gebaut wird

Der tägliche Wächter verwirft die Vormerkung einer Fotolöschung erst nach einer Stunde, sodass kein Foto in alten Versionen liegen bleibt.

## Definition of Done

Eine frische Löschvormerkung übersteht den Wächterlauf, eine über eine Stunde alte unbestätigte wird weiterhin verworfen, und alle Tests laufen grün.

## Wie geprüft wird

Automatische Tests prüfen junge, alte, bestätigte und bereits entfernte Vormerkungen sowie alte Datenbanken; den echten Zufall des Zeitfensters beweisen sie nicht.

## Kritische Anmerkungen

- Keine — Spec deckt die Anfrage ab, jede Anforderung hat einen Test.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
