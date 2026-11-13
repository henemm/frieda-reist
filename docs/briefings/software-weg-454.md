---
spec_file: docs/specs/betrieb/software-weg-454.md
spec_sha256: d1d39d1bb035768c97c6c9332e51e19793c42d42ae36948ef3f251d08f13d017
spec_frozen_sha256: 58d0c019a9ce4dab18d0c2534152f37617bd0db6bb7c911c296ac1f54a82c926
---

# PO-Briefing: software-weg-454

- **Spec:** docs/specs/betrieb/software-weg-454.md
- **Issue:** #454
- **Erstellt:** 2026-11-13

## Was gebaut wird

Die Instanz holt ihre Software direkt aus der öffentlichen Quelle, alle Reisen liegen im Speicher, das private Reisen-Archiv entfällt.

## Definition of Done

Veröffentlichen, Wächter, Schreibweg und Kartendienst laufen auf der Instanz über die neuen Pfade grün, neue Reisen entstehen im Speicher, Rückweg ist dokumentiert.

## Wie geprüft wird

Automatische Tests mit beiden Beispielreisen und Attrappen decken jede Anforderung ab; der echte Server-Umzug und die Units-Umstellung werden nur live abgenommen.

## Kritische Anmerkungen

- Testplan nennt für das Scheitern am Units-Abgleich (Vorgabe des PO) keinen ausdrücklichen Test; Abdeckung nur über Testnamen unklar.
- Lieferung 2 geht erst live, wenn henemm-infra#436 (Überwachung, Sicherung) erledigt ist; Units stellt Claude einmalig um.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
