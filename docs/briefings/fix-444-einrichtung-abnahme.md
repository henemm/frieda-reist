---
spec_file: docs/specs/betrieb/einrichtung-abnahme-444.md
spec_sha256: 7fe155c56f557e43a12af80e0b2488b1e8bdadd6b7abe4688d88fcbe978c930e
spec_frozen_sha256: 6d4a7ae9fd94cabe41d6235ecc32b4ffa30ae00a2b491f7f5edd624fd0ae4916
---

# PO-Briefing: fix-444-einrichtung-abnahme

- **Spec:** docs/specs/betrieb/einrichtung-abnahme-444.md
- **Issue:** #444
- **Erstellt:** 2026-11-10

## Was gebaut wird

Der eigene Kartendienst wird auf dem Server eingerichtet, an Testreisen abgenommen, überwacht und der Testaufbau entfernt.

## Definition of Done

Der Dienst liefert Wasserstellen der Balearen in unter 10 Sekunden, ruht nach 15 Minuten ohne Container, und alle Sieben Prüfpunkte sind protokolliert.

## Wie geprüft wird

Nur manuell am laufenden Dienst mit Testreisen und Protokoll; es gibt keine neuen automatischen Tests, weil keine Software geändert wird.

## Kritische Anmerkungen

- Die Prüfregel für das Städtewochenende ist sprachlich verworren, lässt aber beide Ausgänge (Ablehnung oder öffentlicher Dienst) zu.
- Die Warnung ab 40 Tagen erscheint nur als Hinweis; die Aktualisierung der Kartendaten bleibt Handarbeit.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
