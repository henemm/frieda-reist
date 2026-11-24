---
spec_file: docs/specs/betrieb/testkonto-648.md
spec_sha256: 680615e462e4802dde57c43df9494468845bcc4cd7ab8aaec3d534856d2e09e6
spec_frozen_sha256: 08c1fe23a12afd30d410e01f1189fea04abfc0a5460a17619bc860c3ba51abd6
---

# PO-Briefing: feature-648-testkonto

- **Spec:** docs/specs/betrieb/testkonto-648.md
- **Issue:** #648
- **Erstellt:** 2026-11-24

## Was gebaut wird

Claude testet künftig mit einem eigenen Testkonto statt in Ihrem Konto, und Ihre alten Testreisen werden gelöscht.

## Definition of Done

Eine Abnahme lief vollständig über das Testkonto, in Ihrem Konto steht keine Testreise mehr, Regel und Sperre sind aktiv.

## Wie geprüft wird

Automatische Tests prüfen Einrichtung, Sperre und Vormerken; die vollständige Abnahme und das Aufräumen Ihres Kontos werden nur von Hand nachgewiesen.

## Kritische Anmerkungen

- Endgültig gelöscht werden Ihre Testreisen erst nach 14 Tagen Schonfrist; unsichtbar sind sie sofort.
- Ob zwei alte Testreisen überhaupt löschbar sind, ist ungeprüft; die Spec nimmt es einfach an.
- Lesen über Ihren Konnektor bleibt in Claude Code erlaubt; gesperrt ist nur Schreiben.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
