---
spec_file: docs/specs/betrieb/warteliste-382.md
spec_sha256: 7f0582d1ebd01024fb9db1e84ac0e18e9725df80316e019dec48eb2c43f70dce
spec_frozen_sha256: 7250a78b0bb75b0f65e691df0be6057e01b2e26d1e1c463ee5cfcc72c7b4da5c
---

# PO-Briefing: warteliste-382

- **Spec:** docs/specs/betrieb/warteliste-382.md
- **Issue:** #382
- **Erstellt:** 2026-11-06

## Was gebaut wird

Interessenten tragen sich mit E-Mail ein und bestätigen per Mail; der Betreiber gibt einzelne frei und sie dürfen Reisen anlegen.

## Definition of Done

Eintrag, Bestätigung und Freigabe laufen mit erfundenen Adressen durch, Missbrauch wird abgewiesen, Freigegebene erhalten ihre Mail und das Recht, Doku steht.

## Wie geprüft wird

Automatische Tests decken Eintrag, Bestätigung, Freigabe, Grenzen und Betreiber-Recht ab; Wortlaut der Mails und der Seite prüft niemand.

## Kritische Anmerkungen

- Statt der vorhandenen Einladungsfunktion verschickt die Freigabe eine eigene Mail mit Anmeldelink; das Ticket nannte „Einladung“.
- Zusatz ohne Auftrag: Meldung an die Betreiber bei jedem bestätigten Eintrag; sie hat einen Test.
- Der Hinweis auf das bezahlte Claude-Konto steht im Verhalten, aber in keinem Test.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
