---
spec_file: docs/specs/konnektor/trennung-grenzen-380.md
spec_sha256: e8c693d179754a59c59ac514196febf55bfcf2f21e53f00a4008c226e170b61e
spec_frozen_sha256: f824fc4c9bc0c8015f67864447d94a246a4da6c19c69a6e5965f813db5889431
---

# PO-Briefing: alpha-380-trennung

- **Spec:** docs/specs/konnektor/trennung-grenzen-380.md
- **Issue:** #380
- **Erstellt:** 2026-11-11

## Was gebaut wird

Jeder Tester sieht und ändert nur eigene Reisen (per Test belegt); zusätzlich gibt es Mengengrenzen je Person.

## Definition of Done

Die Testreihe mit zwei Konten ist grün, und wer zu viele Reisen oder Änderungen macht, bekommt in der Claude-App einen verständlichen Satz mit Wartezeit.

## Wie geprüft wird

Automatische Tests mit erfundenen Konten belegen Trennung und Grenzen; mehrere Mandanten in einer Instanz werden nicht geprüft.

## Kritische Anmerkungen

- Lesen über den geheimen Seitenlink bleibt ohne Anmeldung; so von Ihnen entschieden (#421), wird nur dokumentiert.
- Grenzwerte 10 Reisen und 300 Änderungen je Stunde sind Vorschläge der Technik, je Instanz änderbar.
- Gelöschte oder archivierte Reisen geben die Reisezahl nicht frei; mehrere Konten umgehen die Grenzen.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
