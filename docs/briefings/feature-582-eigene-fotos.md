---
spec_file: docs/specs/oberflaeche/bilder-582-eigene-fotos.md
spec_sha256: f3f7eca27a0f78c0e31f1dd429d47f6a7db290ec28591456dc1ed1526626012f
spec_frozen_sha256: d57ac990de89065754081b5aefb3fe46337d4935c9a21f2f8aa2659f92a0805b
---

# PO-Briefing: feature-582-eigene-fotos

- **Spec:** docs/specs/oberflaeche/bilder-582-eigene-fotos.md
- **Issue:** #582
- **Erstellt:** 2026-11-21

## Was gebaut wird

Mitwirkende laden eigene Fotos auf der Reiseseite oder per Chat-Link hoch und können sie später endgültig löschen.

## Definition of Done

Mitwirkende können Fotos hochladen und löschen, Standortdaten sind entfernt, der Personenhinweis erscheint, der Chat-Link funktioniert, und beide Beispielreisen laufen fehlerfrei.

## Wie geprüft wird

Automatische Tests und Browsertests belegen jede Anforderung; ob der Wortlaut gefällt, bleibt Sache der Entwurfsfreigabe.

## Kritische Anmerkungen

- Grenzen (12 MB je Foto, 150 MB je Reise, Link 30 Minuten, 10 Fotos) stammen vom Tech Lead.
- Gelöschte Fotos bleiben bis zu 30 Tage in Sicherungen und auf fremden Geräten; der Dialog sagt das ehrlich.
- Bildunterschriften werden beim Hochladen nicht abgefragt, nur später im Chat ergänzt.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
