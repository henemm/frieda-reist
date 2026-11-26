---
spec_file: docs/specs/oberflaeche/funktionsseiten-711-unterwegs.md
spec_sha256: 11a0c87f0f8bf349285b1136e912eec351779e1277957610e8561b35e55293d3
spec_frozen_sha256: 1de12a9a9274a2e14b98d3e3312d10a62dc74839adb986f35cf59fda5bd02649
---

# PO-Briefing: feat-711-unterwegs

- **Spec:** docs/specs/oberflaeche/funktionsseiten-711-unterwegs.md
- **Issue:** #711
- **Erstellt:** 2026-11-26

## Was gebaut wird

Zwei neue Erklärseiten zeigen, wie Frieda die Reisekarte zeichnet und die Packliste mit Summen und Zuständigen führt, auf Deutsch und Englisch.

## Definition of Done

Beide Seiten sind auf der Instanz in beiden Sprachen mit Text und Handybildern erreichbar, und die Funktionsübersicht verlinkt sie.

## Wie geprüft wird

Tests prüfen Erreichbarkeit, vollständige Texte und Bilder in beiden Sprachen sowie die Verlinkung; ob Beispiele und Bildunterschriften stimmen, prüft kein Test.

## Kritische Anmerkungen

- Beispieltreue und Bildunterschriften (Gewichte, Zuständige, Hotel) sind nur per Sichtprüfung kontrollierbar, ein Test dafür fehlt.
- Dass bestehende Bilder unverändert bleiben, ist keine geprüfte Zusage; die Bilder werden bei der Erzeugung neu geschrieben.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
