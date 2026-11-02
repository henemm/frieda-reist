---
spec_file: docs/specs/betrieb/software-wechsel-ohne-handarbeit-250.md
spec_sha256: 20e51f2dd261a71af7264d15c773ba097fdbc2744d7f2def2c0706d6adc8ba04
spec_frozen_sha256: 970d37411ea9348f71b36b48528229e018b074783c34d49bae9ef5e5278902fd
---

# PO-Briefing: software-wechsel-ohne-handarbeit-250

- **Spec:** docs/specs/betrieb/software-wechsel-ohne-handarbeit-250.md
- **Issue:** #250
- **Erstellt:** 2026-11-02

## Was gebaut wird

Ein Software-Wechsel stellt alle Reisen selbständig um und stößt sich vom Server aus an, ohne jeden Handschritt.

## Definition of Done

Nach einem neuen Software-Stand sind alle Reisen automatisch umgestellt und gebaut, ohne Handgriff und ohne Mail-Flut bei rotem Tor.

## Wie geprüft wird

Automatische Tests prüfen Umstellung, Wettlauf beim Speichern, Anstoß und Mail-Regel; Anleitung und Tests der Instanz werden nur von Hand abgenommen.

## Kritische Anmerkungen

- Anleitung und Regel in der Dokumentation (AC-8) sowie Instanz-Tests (AC-9) haben keinen automatischen Test, nur Abnahme.
- Einmalig muss der Ablauf per Pull Request in das Reisen-Repo kopiert werden; bis dahin läuft der alte Ablauf.
- Dienste laufen nach dem Commit kurz mit altem Code; ein Schreibvorgang kann dann einmal abgelehnt werden.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
