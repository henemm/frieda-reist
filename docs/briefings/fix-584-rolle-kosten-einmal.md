---
spec_file: docs/specs/betrieb/rolle-kosten-einmal-584.md
spec_sha256: 5377e36b5227d2d4ffb90a4edd89b02d8c29a7e5a144728a6039a0807e86f1eb
spec_frozen_sha256: 504c5203f2369a6de755a58c45dcbf686130e28fb8be22df36cc684287145b3a
---

# PO-Briefing: fix-584-rolle-kosten-einmal

- **Spec:** docs/specs/betrieb/rolle-kosten-einmal-584.md
- **Issue:** #584
- **Erstellt:** 2026-11-20

## Was gebaut wird

Beim Veröffentlichen überschreibt die Software nicht mehr bewusst gesetzte Entscheidungen, etwa dass die Herberge keine Kostenrolle hat.

## Definition of Done

Ein zweiter Umstellungslauf an der Beispielreise und am Stadtwochenende ändert keine Datei, und die Herberge bleibt ohne Kostenrolle.

## Wie geprüft wird

Automatische Tests prüfen alter Stand, neuer Stand und Probelauf an beiden Beispielreisen; die Tests der Instanz laufen vor der Auslieferung mit.

## Kritische Anmerkungen

- Restfall bewusst hingenommen: Eine Reise ganz ohne Rolle, die das einzige Kostenmerkmal selbst entfernte, bekäme es zurück. Praktisch ausgeschlossen.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
