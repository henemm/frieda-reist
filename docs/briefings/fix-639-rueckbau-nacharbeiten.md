---
spec_file: docs/specs/betrieb/rueckbau-nacharbeiten-639.md
spec_sha256: cc911d64abdda077676ae2615a13698964a94a889c570c76597b124715cb6dd3
spec_frozen_sha256: 9839e0158e325891a81733f282ceceb959abc94c43baa8770ba278bf54fb1a26
---

# PO-Briefing: fix-639-rueckbau-nacharbeiten

- **Spec:** docs/specs/betrieb/rueckbau-nacharbeiten-639.md
- **Issue:** #639
- **Erstellt:** 2026-11-23

## Was gebaut wird

Fünf kleine Mängel aus der Prüfung des Umbaus werden behoben: sicheres Aufräumen, ehrliche Fehlermeldung bei unlesbarem Speicher, richtige Anleitung.

## Definition of Done

Das Aufräumen löscht keine Konten-, Ablage- oder Konnektor-Daten mehr, ein Speicherfehler wird als solcher gemeldet, und die Anleitung stimmt.

## Wie geprüft wird

Automatische Tests belegen jeden der fünf Punkte; das Zusammenspiel mit der echten Instanz wird nicht getestet, nur deren vorhandene Tests laufen mit.

## Kritische Anmerkungen

- Bei Speicherfehlern kommt im Konnektor künftig "Dienst nicht erreichbar" statt "Ablehnung"; bewusste Verhaltensänderung im Fehlerfall, im Issue erwünscht.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
