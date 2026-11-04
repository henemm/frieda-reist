---
spec_file: docs/specs/oberflaeche/etappe-als-art-269.md
spec_sha256: 7317410b4d4ff16a45e97ad5bb28236f416d3378aac63b7dca45093cbe43123a
spec_frozen_sha256: 1c7059d236a0c216a24a56499f618cba01318ecd1788f2036a6cfed290bfa3fa
---

# PO-Briefing: etappe-als-art-269

- **Spec:** docs/specs/oberflaeche/etappe-als-art-269.md
- **Issue:** #269
- **Erstellt:** 2026-11-04

## Was gebaut wird

Etappen sind künftig frei benennbare Strecken der Reise; Titel und Kennzahlen stehen an der Strecke, nicht mehr im Dossier-Text.

## Definition of Done

Beispielreise zeigt Etappen, Tage und Karte mit gleichen Werten wie vorher, Stadtwochenende bleibt unverändert, alle Tests sind grün, die Umstellung läuft automatisch.

## Wie geprüft wird

Automatische Tests an beiden Beispielreisen und ein Browser-Vergleich der Werte vorher/nachher; echte Reisen werden nicht getestet, nur über die Umstellung nachgezogen.

## Kritische Anmerkungen

- Ticket nannte Kennzahlen „aus der Arten-Datei“; die Spec legt sie an die Strecke (von Ihnen am 4.11. entschieden).
- Beginn erst nach Abschluss von #268; diese Bedingung wird nur per Prozess geprüft, ohne Test.
- Das Verbot alter Begriffe im Code ist nur für die Seitenvorlage getestet, nicht für den übrigen Code.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
