---
spec_file: docs/specs/konnektor/profil-nacharbeiten-578.md
spec_sha256: eaa3adf37187b4ad44d645beccdbc09cc28869a3f61855b7f5cdff403420763a
spec_frozen_sha256: 9b8eb023c890fdfe6fec3fb7ac6907690dbb6415735ccb54da9afcf8d1c1352d
---

# PO-Briefing: fix-578-profil-nacharbeiten

- **Spec:** docs/specs/konnektor/profil-nacharbeiten-578.md
- **Issue:** #578
- **Erstellt:** 2026-11-21

## Was gebaut wird

Vier kleine Mängel an den Profilen werden behoben, ohne dass sich Texte, Bedienung oder gespeicherte Daten ändern.

## Definition of Done

Abgelehnte Profileinträge verbrauchen kein Schreibkontingent mehr, die Obergrenze hält auch bei gleichzeitigem Anlegen, Hinweise erscheinen nur dort, wo es Profile gibt, alle Tests grün.

## Wie geprüft wird

Neue automatische Tests belegen jeden der vier Punkte und bestehende Tests bleiben grün; die Nachführung der Profil-Spezifikation wird nur per Textprüfung kontrolliert.

## Kritische Anmerkungen

- Keine — Spec deckt die Anfrage ab, jede Anforderung hat einen Test.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
