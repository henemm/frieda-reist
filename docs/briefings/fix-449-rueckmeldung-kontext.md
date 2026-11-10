---
spec_file: docs/specs/oberflaeche/rueckmeldung-kontext-449.md
spec_sha256: b11f1c979f43ad83ff544e5c253ea268ed060250113f200f0a3050ef7afcb94d
spec_frozen_sha256: fb1eed1582a4df3200506918fdc9845817d3abd7a99e253574d27cee01c7280c
---

# PO-Briefing: fix-449-rueckmeldung-kontext

- **Spec:** docs/specs/oberflaeche/rueckmeldung-kontext-449.md
- **Issue:** #449
- **Erstellt:** 2026-11-10

## Was gebaut wird

Jede Rückmeldung von der Seite speichert mit, in welcher Ansicht und an welchem Abschnitt sie entstand, und der Konnektor zeigt das an.

## Definition of Done

Eine Rückmeldung zeigt im Konnektor eine Zeile "Ort" mit Ansicht, Abschnitt und Stand; alte Rückmeldungen bleiben unverändert, alle Tests grün.

## Wie geprüft wird

Automatische Tests prüfen beide Beispielreisen, Offline-Senden, ungültige Angaben und Anzeige in allen Sprachen; echte Handys und Reisen werden nicht geprüft.

## Kritische Anmerkungen

- Abweichung vom Ticket: Ungültiger Ort wird still verworfen, die Rückmeldung trotzdem angenommen, statt sie abzuweisen.
- Ticket nennt "show" im Konnektor; das gibt es nicht, angezeigt wird nur in der Rückmeldungsliste.

## Freigabe-Frage

Soll eine Rückmeldung mit ungültigem Ort trotzdem angenommen werden (empfohlen, nichts geht verloren) oder wie im Ticket abgewiesen werden?

## Ampel

Ampel: rot
