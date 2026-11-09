---
spec_file: docs/specs/betrieb/eigener-kartendienst-444.md
spec_sha256: 4914c53f0dd3159c7b8b6c0f7e7a7f5329214197596be331df9179f2b9f567ec
spec_frozen_sha256: 1aa975dddc470ae7d3eef932f81472bdbd7ecc79f6eb4a0ed5083688e388881a
---

# PO-Briefing: feat-444-eigener-kartendienst

- **Spec:** docs/specs/betrieb/eigener-kartendienst-444.md
- **Issue:** #444
- **Erstellt:** 2026-11-09

## Was gebaut wird

Kartenpunkte für Reisen kommen aus einem eigenen, nur bei Bedarf laufenden Kartendienst des Servers; der öffentliche Dienst bleibt Reserve.

## Definition of Done

Am eingerichteten Server liefert die Punktabfrage für eine Wanderung Treffer in wenigen Sekunden, und nach 15 Minuten Ruhe läuft kein Dienst mehr.

## Wie geprüft wird

Automatische Tests mit Attrappen belegen Dienstwahl, Rückfall und Fristen; echter Container und Ruhezustand werden nur bei der manuellen Abnahme geprüft.

## Kritische Anmerkungen

- Zusätzlich zum Ticket: Treffertexte nennen Stand der Daten und genutzten Dienst; monatliche automatische Aktualisierung samt Überwachungs-Check.
- Fällt der eigene Dienst aus, bleiben dem öffentlichen Dienst im Kurzabruf nur 2 Sekunden; sonst Ablehnung wie bisher.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
