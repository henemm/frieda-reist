---
spec_file: docs/specs/konnektor/loeschwunsch.md
spec_sha256: dcc0cb4cddca5dfee5c5c322a6b21834d448cabe43b129bb4eae3d557e37bd1b
spec_frozen_sha256: 8a7984eb3a64d8b96144eefa7dff5f1fd83ed797c8a7f6161944e2a1a3d87b80
---

# PO-Briefing: loeschwunsch-145

- **Spec:** docs/specs/konnektor/loeschwunsch.md
- **Issue:** #145
- **Erstellt:** 2026-10-30

## Was gebaut wird

Bei „lösch das“ wählt der Assistent den passenden Weg und sagt, dass nichts gelöscht ist und wie man es zurückholt.

## Definition of Done

Nach Stornieren, Verwerfen oder Entfallen nennt die Antwort „Nicht gelöscht“ samt Rückholweg; Anleitung und Werkzeugbeschreibungen erklären den Löschwunsch.

## Wie geprüft wird

Tests prüfen, dass die Texte vorhanden sind; ob der Assistent sie im Gespräch wirklich befolgt, bleibt unbewiesen.

## Kritische Anmerkungen

- Umfang über das Ticket hinaus (Aufgaben, Fragen) – von dir mit der Freigabe entschieden; entfallene Fragen lassen sich nicht zurückholen.
- Änderungen bei der Umsetzung: Längengrenze der Anleitung 3650→3900, ein Test mit unzulässigen Testdaten korrigiert.
- Hinweis auf Rückmeldung steht mit „sofern erlaubt“, weil Gäste keine Rückmeldung geben können.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
