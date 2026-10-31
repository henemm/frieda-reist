---
spec_file: docs/specs/betrieb/veroeffentlichen-warnung-142.md
spec_sha256: 7af27f159f92df018c3a8431a0357f46ac278b14d50894f5b5d5174b4c45c220
spec_frozen_sha256: 314add648092aed5a167223c0cb24c63d0d1b03098950f5716aa0acc0d6c67f5
---

# PO-Briefing: fix-142-veroeffentlichen-warnung

- **Spec:** docs/specs/betrieb/veroeffentlichen-warnung-142.md
- **Issue:** #142
- **Erstellt:** 2026-10-31

## Was gebaut wird

Warnungen einer Reise stoppen das Veröffentlichen nicht mehr, echte Fehler lösen Alarm aus, Start und Ende setzt man per Konnektor.

## Definition of Done

Eine Reise mit Warnung geht online, eine kaputte Reise hält andere nicht auf, nach 30 Minuten Rot kommt genau eine Meldung.

## Wie geprüft wird

Automatische Tests mit Attrappen belegen jede Anforderung; echter Betrieb mit echten Reisen und echter Alarmzustellung wird nicht getestet.

## Kritische Anmerkungen

- Inhaltstests des privaten Reisen-Repos sperren nicht mehr; Inhaltsfehler fängt nur noch der Bau (bewusste Folge von Punkt 1).
- Bei einer roten Reise bleibt der Betriebs-Monitor ohne Erfolgsmeldung, obwohl die anderen Reisen online sind.
- Roter Stand wird erst bei neuem Commit oder manuell erneut geprüft.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
