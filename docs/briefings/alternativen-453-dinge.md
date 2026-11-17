---
spec_file: docs/specs/routen/dinge-als-moeglichkeit-453.md
spec_sha256: 1737d5068c4c979f949663951d7cbd1e83ddc9c51d4bff07f7640c8d16ec6699
spec_frozen_sha256: af212aaf947f7438f7b36552a93a53c6efeb970dc59ed950ac9a99003f610736
---

# PO-Briefing: alternativen-453-dinge

- **Spec:** docs/specs/routen/dinge-als-moeglichkeit-453.md
- **Issue:** #453
- **Erstellt:** 2026-11-17

## Was gebaut wird

Jede Wahlmöglichkeit einer Reise nimmt künftig Dinge beliebiger Art in einer gemeinsamen Liste auf, statt je Art eine eigene.

## Definition of Done

Beide Beispielreisen bauen fehlerfrei mit unveränderten Zahlen und unveränderter Seite, vorhandene Reisen sind automatisch umgestellt, und die Dokumentation ist angepasst.

## Wie geprüft wird

Automatische Tests belegen jede Anforderung, auch Umstellung und Konnektor; die Abnahme mit der Claude-App an zwei Testreisen erfolgt von Hand.

## Kritische Anmerkungen

- Zusatz: Fehlerhafte Verweise auf Unterkünfte und Strecken werden künftig gemeldet; falsch gepflegte Reisedaten brechen dann sichtbar.
- Alte Konnektor-Eingaben gelten übergangsweise weiter; ihr Wegfall folgt später in einem eigenen Ticket.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
