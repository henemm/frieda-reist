---
spec_file: docs/specs/betrieb/kartendienst-ueberwachen-573.md
spec_sha256: e2b3efc46ffb687f9df52fcbfe1ddd7fcc212672f772f0cf7b3b9da999c66ff7
spec_frozen_sha256: 9b3f516c76ce1356a81aefa07146e7e41657da6b8a9f1652090c22a49fc851b0
---

# PO-Briefing: 573-kartendienst-ueberwachen

- **Spec:** docs/specs/betrieb/kartendienst-ueberwachen-573.md
- **Issue:** #573
- **Erstellt:** 2026-11-14

## Was gebaut wird

Fällt der eigene Kartendienst dauerhaft aus, kommt eine einmalige, unaufdringliche Warnung statt stillem Wechsel auf den öffentlichen Dienst.

## Definition of Done

Nach drei Fehlschlägen in Folge innerhalb von 24 Stunden erscheint genau eine Warnung, beim nächsten Erfolg eine Entwarnung; der ruhende Dienst wird nie geweckt.

## Wie geprüft wird

Automatische Tests prüfen Erfolgszeile, Warnschwelle, Entwarnung und Entprellung; nicht belegt ist, dass der Dienst beim nächsten Zugriff wirklich startet.

## Kritische Anmerkungen

- Ohne Kartenabfragen gibt es keine Aussage; ein Dienst, der bei jedem Zugriff scheitert, fällt erst bei der dritten Abfrage auf.
- Zusatz gegenüber dem Ticket: Die Engine schreibt künftig auch bei Erfolg eine Protokollzeile, damit die Entwarnung erkennbar ist.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
