---
spec_file: docs/specs/betrieb/altformen-typ-art-267-d.md
spec_sha256: 56a918db193cbedb33128f1edf70aefdfe4ea1b403971ec42c5968bcbf025027
spec_frozen_sha256: dfa6ebe73a4a2e338fdfa8f82ce0a4738325c92d6c9231fd1fb49463898b0599
---

# PO-Briefing: altformen-267-d

- **Spec:** docs/specs/betrieb/altformen-typ-art-267-d.md
- **Issue:** #267
- **Erstellt:** 2026-11-04

## Was gebaut wird

Der alte Schlüssel „typ“ für Unterkunft, Aufenthalt und Nacht wird nicht mehr gelesen; die Reise bricht laut mit Hinweis auf die Umstellung.

## Definition of Done

Alle Beispielreisen bauen mit „art“ fehlerfrei, eine Reise mit altem „typ“ meldet verständlich den Fehler, und das Nachziehen stellt sie wieder auf grün.

## Wie geprüft wird

Automatische Tests belegen Fehlermeldung, Umstellung und unveränderte Ausgabe; ob die echten Reisen bauen, zeigt nur ein manueller Probelauf im PR-Text.

## Kritische Anmerkungen

- Die Einzelform bei Merkmalswerten bleibt, entgegen der Ticket-Zeile „skalar/Liste“; nur ein Kommentar kommt hinzu. Das entschied bereits die Gesamtspec.
- Die Spec berichtigt die Gesamtspec: Der Fehler für fehlende Art heisst Meldung 62, nicht 65. Reine Korrektur, keine Wirkung.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
