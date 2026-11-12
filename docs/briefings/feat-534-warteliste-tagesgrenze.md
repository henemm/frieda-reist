---
spec_file: docs/specs/betrieb/warteliste-tagesgrenze-534.md
spec_sha256: 639d46fb4ee5339f60e97210bfa64a553f65a79814ea391ce67ccde5d103411b
spec_frozen_sha256: 84a900567aa9dacadf1815345d74a4f86f98c0d79faff617d2198aeb738228be
---

# PO-Briefing: feat-534-warteliste-tagesgrenze

- **Spec:** docs/specs/betrieb/warteliste-tagesgrenze-534.md
- **Issue:** #534
- **Erstellt:** 2026-11-12

## Was gebaut wird

Die Warteliste nimmt pro Tag höchstens 20 neue Anmeldungen an, danach erscheint freundlich „Heute sind alle Plätze vergeben“.

## Definition of Done

Nach der 20. Anmeldung eines Tages wird jede weitere abgewiesen, ohne Mail und Speicherung, und der Betreiber erhält einmal täglich eine Meldung.

## Wie geprüft wird

Automatische Tests prüfen Grenze, Tageswechsel, Meldung genau einmal und Texte in Deutsch und Englisch, nicht aber das tatsächliche Resend-Gesamtkontingent.

## Kritische Anmerkungen

- Ein Ansturm kann die Grenze in Minuten füllen; danach sind alle bis Mitternacht UTC abgewiesen, ohne Warteschlange.
- Zusatz: Auch die erneute Mail an unbestätigte Adressen zählt, und die Meldung löst zusätzlich eine Benachrichtigung aus.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
