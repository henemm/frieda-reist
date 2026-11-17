---
spec_file: docs/specs/betrieb/speichergrenzen-538.md
spec_sha256: 4d81e7357253f69f0a438f2b9fe9dba00d119381566315577c34211e0cb37a56
spec_frozen_sha256: 6dc6c7e65c1498218394cc1f28bf170b4b530d5e1fa38dc6e5716b30f4d3a3d1
---

# PO-Briefing: memorymax-538

- **Spec:** docs/specs/betrieb/speichergrenzen-538.md
- **Issue:** #538
- **Erstellt:** 2026-11-17

## Was gebaut wird

Die vier Dauerdienste bekommen Speichergrenzen, damit ein Speicherleck nicht den ganzen Server lahmlegt.

## Definition of Done

Alle vier Dienste laufen auf der Instanz mit ihren Grenzen; Speichern, Veröffentlichen und Seitenbild funktionieren danach fehlerfrei.

## Wie geprüft wird

Automatische Tests prüfen Vorlagen, Erlaubnisliste und Werte; die Wirkung auf dem echten Server wird nur von Hand nachgewiesen.

## Kritische Anmerkungen

- Abweichung vom Ticket: je Dienst eigene Werte statt überall 512M, zusätzlich weiche Grenze und Swap-Grenze; Schreibweg bekommt 5G.
- Neue Einträge in der Erlaubnisliste sind laut Betriebsdoku Ihre Sicherheitsentscheidung; sie erlauben nur Einschränkungen.

## Freigabe-Frage

Geben Sie die drei neuen Grenz-Einträge in der Erlaubnisliste und die vom Ticket abweichenden Werte frei?

## Ampel

Ampel: rot
