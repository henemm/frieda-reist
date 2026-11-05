---
spec_file: docs/specs/oberflaeche/altformen-rest-215.md
spec_sha256: c4d902c0d6e5162f60cf4336f0469f9f321ee441ca1e056caad1697381f1da22
spec_frozen_sha256: 4e07f60ae01808a32ae67b2e77d9e874851806f9617e95c7bb6656607c413565
---

# PO-Briefing: fix-215-altformen

- **Spec:** docs/specs/oberflaeche/altformen-rest-215.md
- **Issue:** #215
- **Erstellt:** 2026-11-05

## Was gebaut wird

Alte „Zu tun“-Links bleiben gültig, und das veraltete Buchungsfeld wird automatisch in echte Buchungen umgewandelt.

## Definition of Done

Alte Lesezeichen und Push-Links öffnen „Zu tun“, die Umstellung läuft ohne Handarbeit und verändert keinen Buchungsstand.

## Wie geprüft wird

Automatische Tests prüfen Links, Umstellung, Wiederholung und Fehlermeldung an beiden Beispielreisen, nicht aber echte Reisen.

## Kritische Anmerkungen

- Freitext im alten Buchungsfeld wird zu „gebucht“; der Chip zeigt dann „gebucht“ statt des Textes. Entscheidung offen.
- Ob echte Reisen das alte Feld nutzen, zeigt erst deren Lauf; dann bricht der Bau bis zur Umstellung ab.

## Freigabe-Frage

Darf Freitext im alten Buchungsfeld künftig als „gebucht“ gelten, mit dem Text als Notiz statt im Chip?

## Ampel

Ampel: rot
