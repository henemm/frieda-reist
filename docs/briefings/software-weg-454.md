---
spec_file: docs/specs/betrieb/software-weg-454.md
spec_sha256: 6c37697138132096f61366933394ad0bd7adefa79f69bebe92dd75602142e185
spec_frozen_sha256: 9d12b1b6b9cf223567143b9c0a59e44f91987e5b3cee66359a6a88c1aca6d9b0
---

# PO-Briefing: software-weg-454

- **Spec:** docs/specs/betrieb/software-weg-454.md
- **Issue:** #454
- **Erstellt:** 2026-11-12

## Was gebaut wird

Die Instanz holt die Software direkt aus dem öffentlichen Bestand, prüft sie vor dem Umschalten und fällt bei Fehlern zurück.

## Definition of Done

Alle Reisen liegen im Speicher, der Umzug läuft ohne Handarbeit, und Veröffentlichen, Wächter und Schreiben arbeiten über die neuen Pfade fehlerfrei.

## Wie geprüft wird

Automatische Tests mit Beispielreisen belegen jede Anforderung; der echte Umzug auf dem Live-Server wird nur manuell beobachtet.

## Kritische Anmerkungen

- Nur die Kontext-Zusammenfassung des Tickets gelesen, nicht den Ticket-Text selbst; Abgleich daher eingeschränkt.
- Zusatz: Der Lauf schaltet übrige Git-Reisen selbst um, nur bei Gleichheit, sonst bleiben sie unverändert.
- Zweite Lieferung wird erst ausgeliefert, wenn Überwachung und Sicherung des Servers angepasst sind.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
