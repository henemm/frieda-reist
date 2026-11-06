---
spec_file: docs/specs/routen/orte-als-moeglichkeit-353.md
spec_sha256: 2284c35ca342d8287e984fc9219774862655a0fb1a6a8bc0729bd5541b8c2012
spec_frozen_sha256: 187aceb2e8d58629f4f75aede0eca0ea546d7355a15e8ad6ddee01bea37e5a81
---

# PO-Briefing: 353-orte-als-moeglichkeit

- **Spec:** docs/specs/routen/orte-als-moeglichkeit-353.md
- **Issue:** #353
- **Erstellt:** 2026-11-06

## Was gebaut wird

Auch ein Ort kann künftig eine Alternative einer Wahlstelle sein, etwa „Wasserfall oder Altendorf“, sichtbar am Tag, im Vergleich und auf der Karte.

## Definition of Done

Die Beispielwanderung zeigt eine Wahlstelle mit zwei Orten samt Vergleich, Link und Kartenpunkt, über Claude anlegbar, und alle Tests sind grün.

## Wie geprüft wird

Automatische Tests und ein Browser-Test belegen alle Punkte; ob die Anzeige gut aussieht, zeigt nur der Rundgang bei der Abnahme.

## Kritische Anmerkungen

- Ein gewählter Ort ändert weder Nachtort noch Anschluss; „Übernachten in A oder B“ als Ortswahl ist vertagt, es gibt nur eine Warnung.
- Der Kartenpunkt eines Orts, der nur Alternative ist, sieht aus wie ein normaler Planort.
- Der Nachweis, dass die Tests der Instanzen nichts brechen, steht nur als Pflicht im Pull Request, nicht in der Testliste.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
