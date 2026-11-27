---
spec_file: docs/specs/fast/fix-730-zurueckholen-knopf.md
spec_sha256: 5d3def12d952310fdecaa1085ff639136306e6423b1dd9cc3b047c86a8cc04de
spec_frozen_sha256: 8b5f36c0243400d3c63ebaf690228cc383771092906cd38230c37052ccd50806
---

# PO-Briefing: fix-730-zurueckholen-knopf

- **Spec:** docs/specs/fast/fix-730-zurueckholen-knopf.md
- **Issue:** #730
- **Erstellt:** 2026-11-27

## Was gebaut wird

Organisator:innen sehen bei vorgemerkten Reisen in „Mein Konto“ wieder den Knopf „Reise zurückholen“ und können damit reagieren.

## Definition of Done

Als Organisator:in sehe ich bei jeder zum Löschen vorgemerkten Reise den Knopf, und Zurückholen klappt; Mitwirkende sehen ihn nicht.

## Wie geprüft wird

Automatische Tests prüfen Knopf und Zurückholen für Organisator:innen sowie fehlenden Knopf für Mitwirkende; ob die Anzeige auf deiner Instanz stimmt, prüfen sie nicht.

## Kritische Anmerkungen

- Du hattest „Wiederherstellen oder Info ausblenden“ offengelassen; die Spec wählt den Knopf. Die Info bleibt sichtbar, Mitwirkende können nur lesen.
- Der Test-Plan nennt nur einen Test; die Zuordnung zu AC-1 und AC-2 ist nicht einzeln ausgewiesen.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
