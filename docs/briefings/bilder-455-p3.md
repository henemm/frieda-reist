---
spec_file: docs/specs/oberflaeche/bilder-455-p3.md
spec_sha256: 85b627f1145a29d7956659cbbd4b760ea56dba8bc58044e3289df9991b5553d0
spec_frozen_sha256: 534155524e476b1afc1536edc29e3f5f7e1dcb6a6a9091806ca7522fb7d3a29c
---

# PO-Briefing: bilder-455-p3

- **Spec:** docs/specs/oberflaeche/bilder-455-p3.md
- **Issue:** #455
- **Erstellt:** 2026-11-17

## Was gebaut wird

„Meine Reisen“ zeigt jede Reise als Kachel mit Titelbild, ersatzweise farbiger Fläche mit App-Symbol, nur für Mitglieder sichtbar.

## Definition of Done

Auf dem Server zeigt „Meine Reisen“ Kacheln, Fremde sehen keine Bilder, die Dokumentation ist nachgeführt, und die Tickets #455 und #581 sind geschlossen.

## Wie geprüft wird

Automatische Tests prüfen Zugriffsschutz, Kachel-Varianten und Handybreite; ob die Optik gefällt, prüft kein Test, die Darstellung ist aber freigegeben.

## Kritische Anmerkungen

- Der „geheime Link“ aus dem Ticket entfällt seit #421; die Spec prüft stattdessen, dass Bildadressen nie die Seitenadresse enthalten.
- Ein ersetztes Titelbild erscheint wegen Zwischenspeicherung bis zu 24 Stunden verzögert.
- Doku-Einträge zu Ontologie und Kern-Verlauf haben keinen eigenen Test.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
