---
spec_file: docs/specs/betrieb/speicher-348-stufe3.md
spec_sha256: 22bf079ca9882f8e119f76c7d0f0f8674259b28f870624fc52ea45631d9b1d60
spec_frozen_sha256: 95a90d81d8b7afc4453a7744aa6bf8e61a9087a30f2b2df662f8d118aabd258a
---

# PO-Briefing: speicher-348-stufe3

- **Spec:** docs/specs/betrieb/speicher-348-stufe3.md
- **Issue:** #348
- **Erstellt:** 2026-11-06

## Was gebaut wird

Der Server veröffentlicht Reisen aus der Datenbank, stellt sie bei neuer Software selbst um und vergleicht sie mit Git.

## Definition of Done

Eine Testreise erscheint allein aus der Datenbank auf der Seite, auch ohne GitHub; der Vergleich der Beispielreisen meldet keinen Unterschied.

## Wie geprüft wird

Automatische Tests prüfen beide Beispielreisen, Lauf ohne Netz und Umstellung; Zeiten, Browser-Rundgang und Rückholung aus dem Archiv sind nur Handnachweise.

## Kritische Anmerkungen

- Abweichung: Software-Vorrücken bleibt vorerst beim GitHub-Workflow; auf dem Server läuft nur die Umstellung der Reisen.
- Abweichung: Bei rotem Tor legt der Server kein Issue an, sondern nutzt Rot-Datei und Meldeweg.
- Überwachung: Nur prüfbare Zustände; der Alarm-Check selbst entsteht erst in einem separaten Infra-Issue.

## Freigabe-Frage

Sind beide Abweichungen (Software-Vorrücken beim Workflow, kein Issue bei Rot) akzeptiert?

## Ampel

Ampel: rot
