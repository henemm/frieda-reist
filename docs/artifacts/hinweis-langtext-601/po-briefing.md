---
spec_file: docs/specs/fast/fix-601-hinweis-langtext.md
spec_sha256: 6b9beb9bbe6fd1e395576470042fe48ea24f6a8658c9592cc2704b519e56f2e9
spec_frozen_sha256: a25fc1df002078681f8acb7f2ce2e9d55db04cfed9326076de5729d4dca7c147
---

# PO-Briefing: hinweis-langtext-601

- **Spec:** docs/specs/fast/fix-601-hinweis-langtext.md
- **Issue:** #601
- **Erstellt:** 2026-11-16

## Was gebaut wird

Hinweise zu Unterkunft, Aufenthalt, Ort und Strecke behalten Zeilen, Fettdruck und nummerierte Listen und erscheinen auf der Reiseseite richtig formatiert.

## Definition of Done

Ein mehrzeiliger Hinweis mit Fettem und Liste wird gespeichert, auf der Reiseseite und im Kalender ohne Sternchen und mit Zeilen angezeigt.

## Wie geprüft wird

Automatische Tests prüfen Speichern, Ablehnen von Überschriften und HTML, Kalender und Seite an beiden Beispielreisen; echte Reisen und bereits geplättete Texte werden nicht geprüft.

## Kritische Anmerkungen

- Bereits geplättete Hinweise werden nicht repariert; Frieda muss sie neu eintragen (von Ihnen so entschieden, Spec erwähnt es nicht).

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
