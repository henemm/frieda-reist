---
spec_file: docs/specs/oberflaeche/loeschfrage-grossansicht-689.md
spec_sha256: ea073327143427693bdd1ff6a36df6c901b2e8cd07e0e6b76e00ca56b281d9cb
spec_frozen_sha256: a1ac72c9fdcc2ff1f963f9a4f24e504f08de2dcd229e3f78b6e3548b95a018a8
---

# PO-Briefing: fix-689-loeschdialog-uebergang

- **Spec:** docs/specs/oberflaeche/loeschfrage-grossansicht-689.md
- **Issue:** #689
- **Erstellt:** 2026-11-25

## Was gebaut wird

Tippt man in der Großansicht früh auf „Foto entfernen“, kommt die Löschfrage zuverlässig, und der Test dazu wackelt nicht mehr.

## Definition of Done

Früher Klick auf „Foto entfernen“ zeigt nach dem Öffnen genau eine Löschfrage zum angetippten Foto, und der Test besteht in drei CI-Läufen.

## Wie geprüft wird

Automatische Tests stellen den frühen Klick künstlich her und prüfen Frage und gelöschtes Foto; ob der CI-Ausfall genau so entstand, bleibt unbewiesen.

## Kritische Anmerkungen

- Abweichung: Das Ticket wollte nur den Test ändern; die Spec ändert auch das Verhalten der Seite für Nutzer.
- CI-Ausfall als genau dieser Seitenfehler ist unbewiesen; längere Wartezeit allein hätte nicht geholfen.

## Freigabe-Frage

Soll Claude über den Test hinaus auch das Verhalten der Seite ändern, wie beschrieben?

## Ampel

Ampel: rot
