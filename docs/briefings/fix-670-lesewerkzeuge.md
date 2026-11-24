---
spec_file: docs/specs/konnektor/lesewerkzeuge-670.md
spec_sha256: 418e51e6843e29b3465c5791740e8b207914c56edf2a750325d1e580f385c88d
spec_frozen_sha256: 2d6b08a1daea91d2c69215ba579d3e500063d9128b527613fb973b3edfe540ef
---

# PO-Briefing: fix-670-lesewerkzeuge

- **Spec:** docs/specs/konnektor/lesewerkzeuge-670.md
- **Issue:** #670
- **Erstellt:** 2026-11-24

## Was gebaut wird

Reisen und Profil lassen sich in Testsitzungen lesen; der Testzugang erkennt die Betreiberadresse zuverlässig und lehnt sie ab.

## Definition of Done

Reisen und Profil sind in Testsitzungen abrufbar, die Betreiberadresse wird als Testkonto abgelehnt, und alle automatischen Tests laufen grün.

## Wie geprüft wird

Automatische Tests belegen Erlaubnis, Kalendersperre und Adressprüfung; das Zusammenspiel auf dem Live-Server wird nicht automatisch geprüft.

## Kritische Anmerkungen

- Abweichung vom Ticket: Der Kalender bekommt keinen Lese-Hinweis, weil „neu“ den Kalenderlink unwiderruflich erneuert; er bleibt in Testsitzungen gesperrt.

## Freigabe-Frage

Darf der Kalender entgegen dem Ticket gesperrt bleiben, weil er den Kalenderlink unwiderruflich erneuern kann?

## Ampel

Ampel: rot
