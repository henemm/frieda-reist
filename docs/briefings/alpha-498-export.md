---
spec_file: docs/specs/betrieb/export-498.md
spec_sha256: 5edf291ea5ec1bcbedd69d7898170f6a07e19fc878713848e0cca5805786419c
spec_frozen_sha256: 3bebcf0463aafe3d93cf6d90fbe0ebb2eb173f4633df1a9c02b73e2bada4b844
---

# PO-Briefing: alpha-498-export

- **Spec:** docs/specs/betrieb/export-498.md
- **Issue:** #498
- **Erstellt:** 2026-11-12

## Was gebaut wird

Auf „Mein Konto“ lädt jede Person per Knopf alle ihre Reisen, Beiträge, sichtbaren Belege und Kontoangaben als ZIP herunter.

## Definition of Done

Der Knopf liefert eine gültige ZIP mit allen eigenen Reisen und Kontoangaben, ohne fremde E-Mail-Adressen; der Datenschutztext nennt den Export.

## Wie geprüft wird

Automatische Tests belegen jede Anforderung an beiden Beispielreisen; ob große Reisen innerhalb der Zeitgrenze durchkommen, wird erst nach dem Ausliefern gemessen.

## Kritische Anmerkungen

- Beiträge: Mitwirkende und Gäste bekommen alle Aufgaben, Wünsche, Packliste und Rückmeldungen, nicht nur eigene, wie im Entwurf gedacht.
- Sehr große Reisen könnten an der 60-Sekunden-Grenze scheitern; die Person sähe dann den Fehlertext.

## Freigabe-Frage

Sollen Mitwirkende und Gäste im Export alle Beiträge der Reise erhalten, wie die Reiseseite sie zeigt, oder nur ihre eigenen?

## Ampel

Ampel: rot
