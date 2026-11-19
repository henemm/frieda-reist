---
spec_file: docs/specs/betrieb/nginx-baustein-loeschen-527.md
spec_sha256: f250f7b3fe82baf4f99617f64b5d7852f39fe08bac68c9f10f9c8ed57a7f3e3b
spec_frozen_sha256: 3853db0ff75d80ba4f316b610f969ae7b32a5f37806003bb992b1050af5c0428
---

# PO-Briefing: nginx-baustein-loeschen-527

- **Spec:** docs/specs/betrieb/nginx-baustein-loeschen-527.md
- **Issue:** #527
- **Erstellt:** 2026-11-19

## Was gebaut wird

Wird eine Reise endgültig gelöscht, verschwindet automatisch auch die technische Weiterleitung ihres alten Links, ohne Handarbeit.

## Definition of Done

Nach endgültigem Löschen einer Testreise ist ihre Weiterleitung beim nächsten Veröffentlichen weg, der Webserver läuft fehlerfrei weiter, und alle Tests sind grün.

## Wie geprüft wird

Automatische Tests mit Attrappen decken alle Anforderungen ab; das echte Entfernen auf dem Server wird nur einmal manuell nachgewiesen.

## Kritische Anmerkungen

- Scheitert das Entfernen dauerhaft, gibt es nur eine Warnzeile, keinen Alarm; das ist bewusst so entschieden.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
