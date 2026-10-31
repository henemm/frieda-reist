---
spec_file: docs/specs/betrieb/software-nachziehen-161.md
spec_sha256: 311e99c1530e1073a8b138ae6c52ff2359e5eb1cfc65cf153771dac8eaad94c6
spec_frozen_sha256: c68e0ce15ea74a52a4fec8be23d6649297b8cfd3bd7e49dbac66091961dfea4b
---

# PO-Briefing: 161-software-nachziehen

- **Spec:** docs/specs/betrieb/software-nachziehen-161.md
- **Issue:** #161
- **Erstellt:** 2026-10-31

## Was gebaut wird

Neue Software gelangt automatisch und nur bei grünen Tests in die Instanz; ein Rückstand über 6 Stunden wird gemeldet.

## Definition of Done

Ein neuer Stand erscheint binnen 30 Minuten als Bot-Commit im Reisen-Repo, rote Tests erzeugen ein Issue, der Monitor zeigt grün.

## Wie geprüft wird

Automatische Tests prüfen Aufbau von Vorlage, Doku und Monitor-Check; ob rote Tests wirklich ein Issue erzeugen, zeigt erst ein echter Lauf.

## Kritische Anmerkungen

- Messgröße weicht vom Ticket ab: Rückstand zählt ab Erstsichtung, nicht ab Commit-Datum; sonst Fehlalarm. Spec begründet das.
- AC-6 und AC-13 sind Betriebsabnahmen (PR-Merge, Journal), keine automatischen Tests.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
