---
spec_file: docs/specs/fast/fix-697-wackel-absturz.md
spec_sha256: 0ce94476651ca246cb0690042739289ccd9c207b6cd8c82a8b66d7a704d41df4
spec_frozen_sha256: 3b2694110e3c977683ec50f4380ce82f729219bdc04fa0fc23761aeecf5c26f8
---

# PO-Briefing: fix-697-wackel-absturz

- **Spec:** docs/specs/fast/fix-697-wackel-absturz.md
- **Issue:** #697
- **Erstellt:** 2026-11-28

## Was gebaut wird

Ein unter Last gelegentlich rot werdender Prüftest zählt den erwarteten Absturz des alten Ablaufs künftig nicht mehr als Fehler.

## Definition of Done

Die Testdatei läuft vollständig grün, auch wiederholt unter Last, und der Test für den neuen Ablauf scheitert weiterhin bei jedem Absturz.

## Wie geprüft wird

Ein Ersatzskript, das sofort abstürzt, weist beide Verhalten ohne Browser nach; ob der Wackler unter Last verschwindet, zeigt nur Beobachtung.

## Kritische Anmerkungen

- Keine — Spec deckt die Anfrage ab, jede Anforderung hat einen Test.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
