---
spec_file: docs/specs/konnektor/profile-12.md
spec_sha256: d60928facf80d2632b6f18283fae518daf8a499443d67a8eb2126f4bb654dda3
spec_frozen_sha256: 22d1d6644077d857e8c57a2115db2536e5dd2eb347a014863c17f4f3efa787af
---

# PO-Briefing: feature-12-profile

- **Spec:** docs/specs/konnektor/profile-12.md
- **Issue:** #12
- **Erstellt:** 2026-11-15

## Was gebaut wird

Jede Person bekommt ein privates Vorlieben-Profil, das Claude nur nach ihrer Bestätigung füllt und das sie selbst ändern oder löschen kann.

## Definition of Done

Auf „Mein Konto“ sieht, ändert und löscht Ida ihr Profil; Karl, Organisatoren und Export sehen nichts Fremdes, Kontolöschung entfernt es.

## Wie geprüft wird

Automatische Tests belegen Speichern, Löschen, Abschottung, Export und Datenschutztext; ob Claude das Profil in Vorschlägen wirklich als Grund nennt, bleibt unprüfbar.

## Kritische Anmerkungen

- Profil als Begründung bei Wahlstellen wirkt nur über Anleitungstext an Claude; getestet wird der Wortlaut, nicht das Verhalten.
- Das Lesen des Profils bleibt auch bei ausgeschaltetem Baustein technisch möglich; nur die Anleitung verbietet die Nutzung.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
