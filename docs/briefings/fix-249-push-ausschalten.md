---
spec_file: docs/specs/fast/fix-249-push-ausschalten.md
spec_sha256: c0853ae54cf98e2d87e778831fd661c616b6c49ad8d943e34b6b5cceed51d07f
spec_frozen_sha256: bc6fa2b233b0994a0e99c58629d7081025dd7f37bd4d523fb4e13722ff8f4ca1
---

# PO-Briefing: fix-249-push-ausschalten

- **Spec:** docs/specs/fast/fix-249-push-ausschalten.md
- **Issue:** #249
- **Erstellt:** 2026-11-02

## Was gebaut wird

Nach dem Einschalten der Benachrichtigungen zeigt Mein Konto nur den Zustand; Ausschalten liegt versteckt unter „Konfigurieren“.

## Definition of Done

Nach dem Einschalten schaltet ein zweites Tippen an derselben Stelle nichts mehr aus; „Auf diesem Gerät ausschalten“ steht unter „Konfigurieren“.

## Wie geprüft wird

Tests prüfen Platz und Quelltext des Knopfs; das echte Verhalten auf dem Handy zeigt nur die manuelle Abnahme.

## Kritische Anmerkungen

- Das Ausschalten per Handy-Browser ist nicht automatisch testbar; Abnahme hängt an den drei manuellen Schritten.
- Zusätzlich neuer Hinweistext „Ausschalten unter ‚Konfigurieren‘“, den das Issue nicht verlangte; harmlos.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
