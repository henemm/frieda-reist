---
spec_file: docs/specs/betrieb/dienstrechte-552.md
spec_sha256: 16fe5c8e42a774b88086d7bf0a6eff1d28b5f6b52a61eee99338524199f813d3
spec_frozen_sha256: 81feaa3dc054a916e4c47088d4ed729798209be22f39250c3981685551fdee66
---

# PO-Briefing: sicherheit-552-dienstrechte

- **Spec:** docs/specs/betrieb/dienstrechte-552.md
- **Issue:** #552
- **Erstellt:** 2026-11-13

## Was gebaut wird

Ein gekaperter Internet-Dienst kommt nicht mehr an Administratorrechte, und Einladen, Erledigen und Einplanen prüfen die aktuelle Rolle.

## Definition of Done

Alle Tests grün, die Anleitung beschreibt den neuen Weg, und die echte Instanz ist umgestellt und im privaten Ticket abgehakt.

## Wie geprüft wird

Automatische Tests belegen jedes Kriterium; die Umstellung der echten Instanz und der Schreibtest unter Sandbox lassen sich nur dort nachweisen.

## Kritische Anmerkungen

- Der Server-Admin bleibt Dienstbenutzer; die Härtung wirkt über die Dienst-Abschottung, nicht über Rechteregeln (bewusst, dokumentiert).
- Fällt der Schreibdienst aus, sind Einladen, Erledigen und Einplanen kurz gesperrt (gewollt).

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
