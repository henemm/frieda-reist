---
spec_file: docs/specs/betrieb/rechtliches-383.md
spec_sha256: 621fb78a8986f07e08d0645f410353630bb68f3ebff247696d0b5fd219568c25
spec_frozen_sha256: 6cbaec1c02eda717e963f0f2b83f6b453f914f1c00fa4c4e1606b8321f425dd6
---

# PO-Briefing: feature-383-datenschutz-impressum

- **Spec:** docs/specs/betrieb/rechtliches-383.md
- **Issue:** #383
- **Erstellt:** 2026-11-07

## Was gebaut wird

Besucher finden vor Warteliste und Anmeldung Datenschutz, Impressum mit Betreiber und Alpha-Hinweis, verlinkt auch in der Fußzeile der Reiseseiten.

## Definition of Done

Die drei Seiten sind auf der Instanz in Deutsch und Englisch erreichbar und verlinkt, und der Product Owner hat die Texte rechtlich bestätigt.

## Wie geprüft wird

Tests prüfen Seiten, Sprachen, Verlinkung und Betreiberangaben mit erfundenen Werten; ob der Datenschutztext inhaltlich stimmt und rechtlich reicht, prüft nur der Product Owner.

## Kritische Anmerkungen

- Abweichung vom Ticket: Löschen und Exportieren stehen im Datenschutztext nur als „folgt“, weil die Funktion fehlt (#381).
- Die Anforderung „Inhalt entspricht der Tabelle“ ist nicht messbar; Fotos und Sicherung außer Haus sind nicht ausdrücklich getestet.
- Zusätzlich gebaut, ungefragt: eigene Alpha-Seite, Rechtszeile immer sichtbar in der Reise-Fußzeile.

## Freigabe-Frage

Darf die Datenschutzerklärung beim Start Löschen und Exportieren der Warteliste- und Reisedaten nur als „folgt“ ankündigen?

## Ampel

Ampel: rot
