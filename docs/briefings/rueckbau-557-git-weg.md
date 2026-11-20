---
spec_file: docs/specs/betrieb/rueckbau-git-weg-557.md
spec_sha256: 1176a8a27d6565efb393748ffb7c64c3ca2aeeb9dd89ed1eeeb34ddd7e08813c
spec_frozen_sha256: e6714db4cc50c5f23e2fa6c6ee137b5a7bafad3a193be9d6f08b9de4b5003f59
---

# PO-Briefing: rueckbau-557-git-weg

- **Spec:** docs/specs/betrieb/rueckbau-git-weg-557.md
- **Issue:** #557
- **Erstellt:** 2026-11-20

## Was gebaut wird

Der alte Reiseablage-Weg und der alte Bauordner auf dem Server verschwinden vollständig; Reisen laufen nur noch über den Speicher.

## Definition of Done

Ein Veröffentlichungslauf endet grün, der alte Ordner ist nach einer Sicherung entfernt, die Überwachung meldet keinen Fehlalarm, alle Tests sind grün.

## Wie geprüft wird

Automatische Tests an beiden Beispielreisen belegen Sicherung, Löschbedingungen und Fehlerfälle; Zeitplan-Abschaltung, Überwachung und Archivierung werden nur manuell im Ticket abgenommen.

## Kritische Anmerkungen

- Endgültig: Es gibt keinen Rückweg mehr; die Sicherung liegt auf demselben Server, sonst bleiben Reisespeicher und archiviertes Reisen-Repo.
- Löschen darf erst nach umgestellter Überwachung geschehen, sonst Fehlalarm; das prüft nur der Tech Lead von Hand.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
