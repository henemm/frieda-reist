---
spec_file: docs/specs/betrieb/speicher-349-stufe4.md
spec_sha256: cc48be6be8dcda4aae6a99683abec3ae88f7060751cce1778e72bad54999f10a
spec_frozen_sha256: 28fc7b0cd7bc591a050abea95da00753b947c9d97ad8825ae7d563f4d9b428b2
---

# PO-Briefing: speicher-349-stufe4

- **Spec:** docs/specs/betrieb/speicher-349-stufe4.md
- **Issue:** #349
- **Erstellt:** 2026-11-08

## Was gebaut wird

Fotos und GPX-Dateien liegen als Dateien in einer Ablage auf dem Server statt in der Datenbank; Seiten bauen wie bisher.

## Definition of Done

Beide Beispielreisen bauen mit ausgelagerten Fotos und GPX unverändert, Browser-Rundgang ist grün, Doppelte liegen einmal, fehlende Datei bricht den Bau mit Meldung ab.

## Wie geprüft wird

Automatische Tests belegen Ablage, Doppelte, Fehlerfälle, Umstellung und Sicherungs-Wiederherstellung; Browser-Rundgang und Zeitmessung sind nur manuelle Nachweise, die Server-Sicherung selbst ist ungetestet.

## Kritische Anmerkungen

- Abweichung: Verweiszeilen und alte Fotodaten bleiben in der Datenbank, Platz spart erst ein freiwilliger Neuaufbau.
- Sicherung der Ablage außer Haus liegt im Infra-Repo; hier nur simuliert getestet.
- Hardlink-Annahme A-2 offen: Bauordner und Ablage teilen Dateien.

## Freigabe-Frage

Akzeptierst du, dass alte Fotos in der Datenbank bleiben und nur neue Fotos Platz sparen?

## Ampel

Ampel: rot
