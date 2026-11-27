---
spec_file: docs/specs/konto/bitte-nach-entzug-695.md
spec_sha256: 93cf677dea71563d328092e8bed5c45e1591e77c16c371fe0e89c6d17a45e010
spec_frozen_sha256: b928f068d34879b1830eedf9cf94c9218407a96b3636ed788a602406a87ab798
---

# PO-Briefing: fix-695-anfrage-nach-entzug

- **Spec:** docs/specs/konto/bitte-nach-entzug-695.md
- **Issue:** #695
- **Erstellt:** 2026-11-27

## Was gebaut wird

Wer das Recht „Reisen anlegen“ verloren hat, kann erneut darum bitten, statt dass Frieda mit einem Fehler abbricht.

## Definition of Done

Nach einem Entzug des Rechts führt die Bitte weder im Assistenten noch auf „Mein Konto“ zum Fehler, und der Betreiber wird einmal benachrichtigt.

## Wie geprüft wird

Automatische Tests prüfen Konto, Assistent, Kontoseite und Betreiber-Meldung; eine ausdrücklich abgelehnte Bitte bleibt abgelehnt.

## Kritische Anmerkungen

- Das Ticket lässt offen, ob nach Entzug neu gebeten werden darf; die Spec entscheidet das selbst mit Ja.
- Begrenzung: Solange eine Bitte offen liegt, entsteht keine zweite Meldung; neu geöffnet wird nur nach erneuter Freischaltung und Entzug.

## Freigabe-Frage

Soll eine Person, der das Recht „Reisen anlegen“ wieder entzogen wurde, erneut darum bitten dürfen?

## Ampel

Ampel: rot
