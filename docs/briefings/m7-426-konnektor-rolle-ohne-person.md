---
spec_file: docs/specs/konnektor/rolle-ohne-person-426.md
spec_sha256: c4120b8f725923a757cd7a8097166390688d419a3fcda7932dc46abbfd7efc5e
spec_frozen_sha256: 0fe2515a8674ad4ae0e5ef88ed4a0d5d6ce072098cdb9b104095c714b80653c8
---

# PO-Briefing: m7-426-konnektor-rolle-ohne-person

- **Spec:** docs/specs/konnektor/rolle-ohne-person-426.md
- **Issue:** #426
- **Erstellt:** 2026-11-12

## Was gebaut wird

Ein alter, nicht mehr erreichbarer Zugang ohne Person samt zugehöriger Namensabfragen und Texte wird entfernt; für Nutzer ändert sich nichts.

## Definition of Done

Alle Tests laufen grün, die alten Texte und Namensfelder sind verschwunden, und der Konnektor funktioniert über das Konto unverändert.

## Wie geprüft wird

Automatische Tests belegen jede Anforderung, darunter dass ein Zugang ohne Person nichts darf; die Prüfung auf dem echten Server erfolgt nur per Stichprobe.

## Kritische Anmerkungen

- Abweichung vom Ticket: Der Gast kommt nicht in die Beispielreise, sondern nur in die Testvorbereitung, damit die Demoseite unverändert bleibt.

## Freigabe-Frage

Ist es für dich in Ordnung, dass der Gast nur in den Tests entsteht und nicht in der Beispielreise?

## Ampel

Ampel: rot
