---
spec_file: docs/specs/betrieb/altformen-entfernen-267.md
spec_sha256: b6b787f06a4fdb4c148d1834a7830c9c2d76eb51875abd013fce2b177753df98
spec_frozen_sha256: c7cf222a419639b05d5d0d43a260aa21e26e7bf30e5341557c1a58a310605dec
---

# PO-Briefing: altformen-267-b

- **Spec:** docs/specs/betrieb/altformen-entfernen-267.md
- **Issue:** #267
- **Erstellt:** 2026-11-03

## Was gebaut wird

Das Nachziehen trägt in Reisen ohne Sprachangabe automatisch Deutsch ein, damit der stille Notbehelf später entfallen kann.

## Definition of Done

Fehlt die Sprache, steht nach dem Nachziehen „Deutsch“ in der Reisedatei; ein zweiter Lauf ändert nichts, vorhandene Angaben bleiben unberührt.

## Wie geprüft wird

Automatische Tests prüfen Eintrag, Meldung und Unveränderlichkeit; ob der Server-Lauf die vier echten Reisen umstellt, zeigt erst ein manueller Nachweis danach.

## Kritische Anmerkungen

- Umstellung der vier echten Reisen ist erst nach Auslieferung prüfbar; die Spec macht sie ausdrücklich zur Voraussetzung für den nächsten Schritt.
- Eine unbekannte Sprache bleibt bewusst unverändert; der Bau meldet sie weiter.
- Seit dem letzten Briefing nur Überschrift umbenannt (Acceptance Criteria), inhaltlich unverändert.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
