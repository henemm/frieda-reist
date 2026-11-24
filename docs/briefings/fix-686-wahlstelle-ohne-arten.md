---
spec_file: docs/specs/konnektor/plan-ohne-arten-686.md
spec_sha256: 946f02bd923d5b153d4989767ebea68d1fbb07140582e8e5a31c99120bd574e3
spec_frozen_sha256: d8bd671733305324c5a79460483dfd7a53770107d639c58c83e174e7ea768040
---

# PO-Briefing: fix-686-wahlstelle-ohne-arten

- **Spec:** docs/specs/konnektor/plan-ohne-arten-686.md
- **Issue:** #686
- **Erstellt:** 2026-11-24

## Was gebaut wird

Reisen ohne Arten lehnen Plan-Eingaben klar ab, statt Erfolg zu melden; mit Arten erscheint der Plan sofort sichtbar.

## Definition of Done

Eine Auswahl in einer Reise ohne Arten wird mit Hinweis abgelehnt; nach Übernahme von Arten ist der Plan sichtbar und entscheidbar.

## Wie geprüft wird

Automatische Tests prüfen Ablehnung, Sichtbarkeit nach Arten, Reparatur bestehender Reisen und beide Beispielreisen; die echte Darstellung im Browser prüfen sie nicht.

## Kritische Anmerkungen

- Nicht nur Auswahlen: alle Plan-Eingaben (Tage, Dinge, Termine) werden in Reisen ohne Arten künftig abgelehnt, nicht nur die gemeldete.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
