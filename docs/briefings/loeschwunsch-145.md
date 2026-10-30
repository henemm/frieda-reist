---
spec_file: docs/specs/konnektor/loeschwunsch.md
spec_sha256: b8ae33b3b10fb936dde5bb5a7ba34f9860944ab29a60d05adf81f2780918410c
spec_frozen_sha256: c36c4f1bb575b5cf9138bccb4622200954468e24735591fef7a660cebe80a921
---

# PO-Briefing: loeschwunsch-145

- **Spec:** docs/specs/konnektor/loeschwunsch.md
- **Issue:** #145
- **Erstellt:** 2026-10-30

## Was gebaut wird

Sagt jemand „lösch das“, wählt der Assistent den passenden Weg und erklärt, dass nichts gelöscht ist und wie man es zurückholt.

## Definition of Done

Nach Stornieren, Verwerfen oder Entfallen nennt die Antwort „Nicht gelöscht“ und den Rückholweg; Anleitung und Werkzeugbeschreibungen erklären den Löschwunsch.

## Wie geprüft wird

Tests prüfen, dass die Texte vorhanden sind; ob der Assistent sie im Gespräch wirklich befolgt, bleibt unbewiesen.

## Kritische Anmerkungen

- Zusatz: Spec nimmt Aufgaben und Fragen dazu und ändert auch Antworttexte außerhalb des Konnektors; das Ticket nennt nur Buchungen und Optionen.
- Entfallene Fragen lassen sich nicht zurückholen, nur durch neue Frage ersetzen.

## Freigabe-Frage

Soll der Umfang wie im Ticket auf Buchungen und Optionen beschränkt bleiben oder dürfen Aufgaben und Fragen dazukommen?

## Ampel

Ampel: rot
