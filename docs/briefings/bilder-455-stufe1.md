---
spec_file: docs/specs/oberflaeche/bilder-455-stufe1.md
spec_sha256: 6a91f55f92d0d090b34b7cfe63d63df58952a36c32234605d7051a5db786a5f8
spec_frozen_sha256: 72f3d72a2ae2710a2a3bd2573543c3484bc5c458231edb711aeb1bbf7070e8ad
---

# PO-Briefing: bilder-455-stufe1

- **Spec:** docs/specs/oberflaeche/bilder-455-stufe1.md
- **Issue:** #455 (mit #581)
- **Erstellt:** 2026-11-15

## Was gebaut wird

Reisen bekommen freie Bilder aus Wikimedia Commons mit Urheber und Lizenz, und fremde Bildadressen im Text werden gesperrt.

## Definition of Done

Claude fügt ein freies Commons-Bild hinzu, die Reise zeigt es mit Namensnennung, auch offline, und fremde Bildadressen im Text führen zu einem Fehler.

## Wie geprüft wird

Automatische Tests mit nachgebauten Commons-Antworten und Browser-Seitentests belegen Lizenzregel, Rechte, Sperre und Darstellung; echtes Netz und echte Reisen werden nicht getestet.

## Kritische Anmerkungen

- Das Doku-Kriterium (AC-17) hat keinen eigenen Test; Prüfung nur durch Nachlesen.
- Lieferung in drei Teilen: Titelbild, Kopfbilder und Kachel in „Meine Reisen“ erscheinen erst mit Teil 2 und 3.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
