---
spec_file: docs/specs/konto/push-absender-709.md
spec_sha256: 1a020e96fc62e3279c24d59a4ede0b3f2a846088fbae5608368aafb718cd1739
spec_frozen_sha256: f99c8336faa5e37d97b72239a6e7e4cc5d32bc5b39084e88896f4f0efa6ac4af
---

# PO-Briefing: fix-709-push-absender

- **Spec:** docs/specs/konto/push-absender-709.md
- **Issue:** #709
- **Erstellt:** 2026-11-28

## Was gebaut wird

Wer Push in der Frieda-App eingeschaltet hat, bekommt Nachrichten nur noch dort, ohne fremden Reisenamen als Absender.

## Definition of Done

Neue-Reise-Nachricht erscheint auf dem iPhone einmal, mit Absender Frieda, und Mein Konto zählt ein Gerät statt zwei.

## Wie geprüft wird

Automatische Tests prüfen Auswahl der Abos, Versand und Gerätezählung; echte iPhone-Anzeige des Absenders prüfen sie nicht.

## Kritische Anmerkungen

- Geräte, die nur ein altes Reise-Abo haben, bekommen keine Push mehr, sobald das Konto anderswo die App nutzt.
- Gefragt war nur nach dem Grund; die Spec liefert zusätzlich diese Korrektur, gestützt auf Entscheidung vom 2.11.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
