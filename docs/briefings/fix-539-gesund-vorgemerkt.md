---
spec_file: docs/specs/konnektor/gesund-vorgemerkt-539.md
spec_sha256: 30292815a3ae0053a9399603286f5a0a5326cd768119c63b8053191814a87798
spec_frozen_sha256: 3237354f54409f5bd8cc9513d0c290af40432b90cc4419dd6fef7596942d4f9d
---

# PO-Briefing: fix-539-gesund-vorgemerkt

- **Spec:** docs/specs/konnektor/gesund-vorgemerkt-539.md
- **Issue:** #539
- **Erstellt:** 2026-11-12

## Was gebaut wird

Die Bereitschaftsprüfung meldet keine Störung mehr, nur weil eine Reise zur Löschung vorgemerkt ist.

## Definition of Done

Eine zur Löschung vorgemerkte Reise löst keinen Alarm aus: Die Prüfung meldet „gesund“, solange mindestens eine andere Reise in Ordnung ist.

## Wie geprüft wird

Ein Test spielt das Vormerken nach; fehlende Seiten nicht vorgemerkter Reisen bleiben Fehler. Das Aufräumen des Seitenlinks wird nicht geprüft.

## Kritische Anmerkungen

- Keine — Spec deckt die Anfrage ab, jede Anforderung hat einen Test.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
