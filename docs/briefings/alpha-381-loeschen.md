---
spec_file: docs/specs/betrieb/loeschen-381.md
spec_sha256: 823b4c20de4bd06f73d942c66ab4dd098bac9d226e2944da7b48b8eefb3db58c
spec_frozen_sha256: e65f436a03368d5b10da56632e075cdbe1afc877059051b2f6bb391b6f310b74
---

# PO-Briefing: alpha-381-loeschen

- **Spec:** docs/specs/betrieb/loeschen-381.md
- **Issue:** #381
- **Erstellt:** 2026-11-11

## Was gebaut wird

Organisator:innen löschen Reisen mit 14 Tagen Rückholfrist, jede Person löscht ihr Konto, ihr Name verschwindet überall.

## Definition of Done

Gelöschte Reisen sind nach 14 Tagen samt Fotos und Belegen unauffindbar, gelöschte Konten hinterlassen keine Spur, Namen erscheinen als „gelöschte Person“.

## Wie geprüft wird

Automatische Tests belegen jede Anforderung an beiden Beispielreisen; ob Sicherungskopien auf dem Server nach 30 Tagen verschwinden, prüft kein Test.

## Kritische Anmerkungen

- Sicherungen: 30-Tage-Ziel liegt außerhalb der Software, getrennt zu klären (eigenes Aufgabenblatt); bis dahin nur Ziel, keine Garantie.
- Namen in frei getippten Texten werden nur teilweise gefunden; Datenschutztext benennt das offen.
- Issue-Kommentare konnte der Prüfer nicht lesen; Abgleich nur mit Kontextdokument.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
