---
spec_file: docs/specs/fast/fix-669-bruecke-netzfehler.md
spec_sha256: 8e4f3e1003b12b40dc09c85b5e2de411d9df8a29008542214c53131e0d786687
spec_frozen_sha256: 733fdc160916120a6d8c827e9d238ac8721a40f79f683baa2da730ee4efd5e66
---

# PO-Briefing: fix-669-bruecke-netzfehler

- **Spec:** docs/specs/fast/fix-669-bruecke-netzfehler.md
- **Issue:** #669
- **Erstellt:** 2026-11-27

## Was gebaut wird

Der Testzugang zu Frieda bleibt bei Netzproblemen am Leben und meldet einen Fehler, statt für die ganze Sitzung auszufallen.

## Definition of Done

Ist die Instanz nicht erreichbar, bekommt jede Anfrage eine Fehlermeldung, und die Brücke arbeitet nach Wiederkehr der Verbindung ohne Neustart weiter.

## Wie geprüft wird

Automatische Tests simulieren unerreichbare Instanz, Ausfall mitten im Lauf und gescheiterte Erneuerung; nicht geprüft wird die Brücke gegen die echte Instanz.

## Kritische Anmerkungen

- Zusätzlich zum Ticket: Auch ein Netzfehler beim Start beendet die Brücke nicht; die Kontoprüfung wird nachgeholt, Sicherheitsabbrüche bleiben.
- Zweiter Befund (weitere Konnektoren sperren) wurde geprüft und bewusst nicht geändert, da es nur den einen Konnektor gibt.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
