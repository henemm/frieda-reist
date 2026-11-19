---
spec_file: docs/specs/betrieb/wackelige-browsertests-599.md
spec_sha256: f3bf3c210f0420543838e06bb9763fe7bfbdc5cb65e6cfab483cd2212068368d
spec_frozen_sha256: b6b4164f580b96e42fd161ba71774136e8e2e18b487b31bb1063150b65cf3457
---

# PO-Briefing: fix-599-wackelige-browsertests

- **Spec:** docs/specs/betrieb/wackelige-browsertests-599.md
- **Issue:** #599
- **Erstellt:** 2026-11-19

## Was gebaut wird

Zwei Browser-Prüfungen warten auf den tatsächlichen Endzustand statt auf feste Zeiten und scheitern unter Last nicht mehr zufällig.

## Definition of Done

Beide Prüfungen laufen auch unter künstlicher Verzögerung grün, mehrere Gesamtläufe bleiben ohne Rot, echte Fehler werden weiterhin gemeldet.

## Wie geprüft wird

Ein neuer Test verzögert die Seite künstlich: alter Ablauf rot, neuer grün, echter Fehler bleibt rot; Laufzeit nur manuell gemessen.

## Kritische Anmerkungen

- Neue Testhülle für die Verzögerung kam hinzu; sie betrifft nur Testcode, Seite und Betrieb bleiben unverändert.
- Künstliche Verzögerung bildet echte Serverlast nur nach; bei erneutem Rot wird nachgebessert.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
