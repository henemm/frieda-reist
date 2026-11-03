---
spec_file: docs/specs/betrieb/altformen-entfernen-267.md
spec_sha256: 715b9eddd2e4dc9f525c54c3518b58b6c53c6a21e8f4927c6bb0bcdc98f53a51
spec_frozen_sha256: cf417fc384977110d9593693fe59f16db03f2c2b7fcd4cc19b7df6c2a810797d
---

# PO-Briefing: altformen-267-b

- **Spec:** docs/specs/betrieb/altformen-entfernen-267.md
- **Issue:** #267
- **Erstellt:** 2026-11-03

## Was gebaut wird

Das automatische Nachziehen trägt in Reisen ohne Sprachangabe die Sprache Deutsch ein, damit später kein Notbehelf dafür mehr nötig ist.

## Definition of Done

Fehlt die Sprache, steht sie nach dem Nachziehen als Deutsch in der Reisedatei; ein zweiter Lauf ändert nichts, andere Angaben bleiben unberührt.

## Wie geprüft wird

Automatische Tests prüfen Eintrag, Meldung und Unveränderlichkeit; dass der Server-Lauf die vier echten Reisen wirklich umstellt, zeigt erst ein späterer manueller Nachweis.

## Kritische Anmerkungen

- Ohne Test: Die Umstellung der vier echten Reisen ist erst nach der Auslieferung prüfbar, nicht vor Freigabe.
- Die Spec nennt zwei Orte für die neuen Tests; maßgeblich ist die spätere Festlegung.
- Eine unbekannte Sprache bleibt bewusst unverändert; der Bau meldet sie weiter.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
