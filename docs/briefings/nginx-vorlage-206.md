---
spec_file: docs/specs/fast/nginx-vorlage-206.md
spec_sha256: cd3fbee69aea4a38aa3e9236550ad4bfba4c4c03846d94d00237fc8412c5ae88
spec_frozen_sha256: 96cfaaf105f4a0982aab989430a255b96df89df5ce619b1738eb0e80aa856c1e
---

# PO-Briefing: nginx-vorlage-206

- **Spec:** docs/specs/fast/nginx-vorlage-206.md
- **Issue:** #206
- **Erstellt:** 2026-11-03

## Was gebaut wird

Die Server-Vorlage für die Drosselung bekommt den Stand des Servers; ein täglicher Abgleich meldet Abweichungen als ein Issue.

## Definition of Done

Der Abgleich meldet bei Abweichung genau ein Issue mit dem Befehl, bleibt sonst still, und am Server wurde nichts verändert.

## Wie geprüft wird

Tests mit echtem Webserver belegen Zonen und Ausnahme eigener Adressen, Attrappen den Abgleich; die Wirkung auf dem Live-Server bleibt ungeprüft.

## Kritische Anmerkungen

- Die eigentliche Umstellung der Drosseln auf dem Server ist ein späterer Schritt und braucht Ihre separate Freigabe.
- Die Ausnahme für eigene Adressen ist nur sicher, solange der Server keine fremden Adressen aufruft; Annahme ist dokumentiert.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
