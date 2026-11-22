---
spec_file: docs/specs/betrieb/umgebung-fingerabdruck-626.md
spec_sha256: 6fcc510418df5a021af14afee5f14652a1462ee95015790375a0855ed9f6ead8
spec_frozen_sha256: 1d797852e1a7380366e1c20ec5b2de2b8d315f38b36d2d3ca31633eac9d1cd1e
---

# PO-Briefing: fix-626-umgebung-fingerabdruck

- **Spec:** docs/specs/betrieb/umgebung-fingerabdruck-626.md
- **Issue:** #626
- **Erstellt:** 2026-11-22

## Was gebaut wird

Ein gescheitertes Veröffentlichen wird nicht mehr bei jedem Takt neu ausgerollt, sondern wartet auf eine Änderung oder den Fristablauf.

## Definition of Done

Nach einem gescheiterten Veröffentlichen meldet der nächste Lauf „bekannter roter Stand übersprungen“, rollt nichts erneut aus, und alle Tests sind grün.

## Wie geprüft wird

Neue Tests stellen den Fehler mit einer Attrappe nach und belegen Überspringen sowie Neuprüfung bei echter Änderung; eine echte Instanz wird nicht geprüft.

## Kritische Anmerkungen

- Abweichend vom Ticket-Vorschlag (Testumgebung fest setzen) wird die Ursache im Skript behoben, sonst bliebe der Fehler verdeckt.
- Nach der Umstellung erscheint einmalig eine zusätzliche Neuprüfung bestehender roter Stände; danach ist der Wert stabil.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
