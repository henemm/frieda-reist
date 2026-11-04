---
spec_file: docs/specs/routen/kennzahlen-268.md
spec_sha256: 84a45378f07187ff5bf9f518ec87753ca59b58cffdd89de71dc365021c498ca9
spec_frozen_sha256: 41d5fdf207d9bd55ab53d77adf66722e1f07fe2b20764f075dc4306eb72b04cf
---

# PO-Briefing: kennzahlen-268

- **Spec:** docs/specs/routen/kennzahlen-268.md
- **Issue:** #268
- **Erstellt:** 2026-11-04

## Was gebaut wird

Gehzeit, Länge und Höhenmeter werden nur noch an einer Stelle berechnet; Seite und Konnektor zeigen dieselben Werte.

## Definition of Done

Beide Beispielreisen zeigen unveränderte Werte, und fehlende Angaben erscheinen als „Angaben fehlen“ statt als Null oder leer.

## Wie geprüft wird

Automatische Tests prüfen Summen, Sonderfälle und Texte beider Beispielreisen; echte Reisen prüft nur ein Probebau vor dem Vorspulen.

## Kritische Anmerkungen

- Die Zuordnung der Kennzahl-Namen bleibt vorerst doppelt auf der Seite; im Ticket-Kommentar auf #269 verschoben, nicht vom PO entschieden.
- Echte Reisen können erstmals Werte oder „Angaben fehlen“ zeigen; sichtbar erst im Probebau.
- Konnektor zeigt bei fehlenden Angaben neuen Text statt „0:00“; gewolltes Zusatzverhalten, in der Spec benannt.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
