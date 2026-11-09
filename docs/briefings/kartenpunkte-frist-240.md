---
spec_file: docs/specs/betrieb/kartenpunkte-frist-240.md
spec_sha256: ba28499d8dd61894b8108b56f73421b9bb68b22c2d19ed10c96f03313ab0df4a
spec_frozen_sha256: ffb1e5bed84bd95522205f57b85dd93ed65f926fda58f467ad03bab6889c8753
---

# PO-Briefing: kartenpunkte-frist-240

- **Spec:** docs/specs/betrieb/kartenpunkte-frist-240.md
- **Issue:** #240
- **Erstellt:** 2026-11-09

## Was gebaut wird

Das Kartenwerkzeug wartet auf den langsamen OpenStreetMap-Dienst lange genug, damit Wasser- und Einkehr-Punkte entlang der Strecke tatsächlich eintreffen.

## Definition of Done

Am echten Dienst liefert eine Testreise Treffer mit Quelle und Stand, ein zweiter Aufruf verdoppelt nichts, das Städtewochenende lehnt sofort ab.

## Wie geprüft wird

Automatische Tests mit erfundenen Antworten belegen alle Anforderungen; ob der echte Dienst und die Claude-App die Wartezeit mitmachen, zeigt nur die Abnahme.

## Kritische Anmerkungen

- Antworten dauern künftig bis etwa eine Minute; ob die Claude-App so lange wartet, ist offen, Folge-Issue möglich.
- Der echte Overpass-Dienst bleibt unzuverlässig; bei Überlast gibt es weiterhin eine Ablehnung, nur später.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
