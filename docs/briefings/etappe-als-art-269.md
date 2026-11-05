---
spec_file: docs/specs/oberflaeche/etappe-als-art-269.md
spec_sha256: c12d3d4d5c0d631c72b7988263a92d519eb8cfe9db2964c93f44c8f4ac335604
spec_frozen_sha256: df3db2b997ff40ee47049a1000886f2a542cb4e5e6e9e57cb2f1b503386c53a0
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
