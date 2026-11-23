---
spec_file: docs/specs/fast/fix-634-status-archiv.md
spec_sha256: bf06b38ae935d573f457b6631baf87482feb917fd37287c9e4d0c7a68f395cb1
spec_frozen_sha256: 81af35039dc5b87fe58a5dc2fff09f47d71fac405e488af6bad417322c68bfc2
---

# PO-Briefing: fix-634-status-archiv

- **Spec:** docs/specs/fast/fix-634-status-archiv.md
- **Issue:** #634
- **Erstellt:** 2026-11-23

## Was gebaut wird

Archivierte Reisen zeigen unter dem Titel das Wort „Archiviert“ statt eines Fehlertexts und keinen Tage-Countdown mehr.

## Definition of Done

Eine archivierte Reise zeigt „Archiviert“ (englisch „Archived“), kein „noch n Tage“; alle anderen Status verhalten sich unverändert.

## Wie geprüft wird

Tests prüfen, dass jeder Status in jeder Sprache einen Text hat und die archivierte Seite Wort statt Rohschlüssel ohne Zähler zeigt.

## Kritische Anmerkungen

- Den im Issue offenen Countdown entfernt die Spec bei archivierten Reisen; das ist eine kleine Produktentscheidung, hier vom Tech Lead getroffen.
- Briefing ohne Zugriff auf Issue-Kommentare erstellt; Abgleich nur gegen den im Auftrag genannten Issue-Titel und die Countdown-Frage.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
