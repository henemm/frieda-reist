---
spec_file: docs/specs/routen/dinge-als-moeglichkeit-453.md
spec_sha256: 3326912a726678713e772d04b77235fe1628c453812863fce2867953291d69c5
spec_frozen_sha256: fbbbc8aa255965c16d0a2a10a13a31dc67cf7f857e24c4aa6850541186afb6cb
---

# PO-Briefing: alternativen-453-dinge

- **Spec:** docs/specs/routen/dinge-als-moeglichkeit-453.md
- **Issue:** #453
- **Erstellt:** 2026-11-17

## Was gebaut wird

Jede Möglichkeit einer Wahlstelle verweist künftig über ein einziges Feld auf ihre Dinge; die Seite bleibt für Leser unverändert.

## Definition of Done

Beide Beispielreisen bauen mit gleichen Summen und gleicher Seite, bestehende Reisen werden automatisch umgestellt, und die gesamte Testsuite ist grün.

## Wie geprüft wird

Automatische Tests decken jede Anforderung ab; die Abnahme über den Konnektor an beiden Reisetypen erfolgt separat und von Hand.

## Kritische Anmerkungen

- Handgepflegte Reisedaten mit falscher Unterkunfts- oder Streckennummer fallen künftig auf, statt still zu bleiben.
- Alte Konnektor-Parameter funktionieren vorerst weiter; ihr Wegfall folgt später in einem eigenen Issue.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
