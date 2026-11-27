---
spec_file: docs/specs/fast/fix-669-bruecke-netzfehler.md
spec_sha256: 966135f76f8ec7895b950df73f9e7d8f65354764beb19aaa120c040bf5ccec11
spec_frozen_sha256: 138c515ac7aa304b898eba319f3c432b4b50021e7185841c443fbc5cf07a00d9
---

# PO-Briefing: fix-669-bruecke-netzfehler

- **Spec:** docs/specs/fast/fix-669-bruecke-netzfehler.md
- **Issue:** #669
- **Erstellt:** 2026-11-27

## Was gebaut wird

Der Testzugang zu Frieda bricht bei Netzproblemen nicht mehr ab, sondern meldet pro Anfrage einen Fehler und läuft weiter.

## Definition of Done

Bei unerreichbarer Instanz erhält jede Anfrage eine Fehlermeldung, die Brücke bleibt aktiv und leitet nach Wiederkehr des Netzes wieder weiter.

## Wie geprüft wird

Automatische Tests prüfen Netzfehler beim Start, mitten im Betrieb und bei gescheiterter Token-Erneuerung; weitere Konnektoren werden nicht abgesichert.

## Kritische Anmerkungen

- Zweiter Teil des Tickets (Sperre auf weitere Konnektoren erweitern) bleibt bewusst ungeändert, da es keine weiteren Konnektoren gibt.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
