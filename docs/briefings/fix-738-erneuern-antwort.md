---
spec_file: docs/specs/fast/fix-738-erneuern-antwort.md
spec_sha256: 8447e9166c4645cbeb9f6d94032192aff84155712463037576b2fa753fb1a500
spec_frozen_sha256: efb9d53bd99e46882cefee1dca1b4a11f5013e076c0821889850e08b7a58093a
---

# PO-Briefing: fix-738-erneuern-antwort

- **Spec:** docs/specs/fast/fix-738-erneuern-antwort.md
- **Issue:** #738
- **Erstellt:** 2026-11-27

## Was gebaut wird

Liefert der Anmeldedienst beim Erneuern eine unbrauchbare Antwort, bleibt die Testzugang-Verbindung am Leben und meldet nur einen Fehler.

## Definition of Done

Bei leerer, falsch geformter oder unvollständiger Antwort beantwortet die Verbindung jede Anfrage mit Fehler, läuft weiter, endet sauber, und die gespeicherten Zugangsdaten bleiben unverändert.

## Wie geprüft wird

Ein automatischer Test simuliert leere, leere-Liste- und leere-Objekt-Antworten; andere Fehlformen, etwa kaputten Text, prüft er nicht ausdrücklich.

## Kritische Anmerkungen

- Test nennt nur drei Antwortformen; Antwort mit nur einem fehlenden Token oder ungültigem Text ist nicht ausdrücklich getestet.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
