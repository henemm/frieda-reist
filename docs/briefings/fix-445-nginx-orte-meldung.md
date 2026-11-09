---
spec_file: docs/specs/betrieb/wegepruefung-ohne-alarm-445.md
spec_sha256: 87a4c96ff297a1619109e0a63ff6fc25c504617633e7d07bb6e05c47e5b69108
spec_frozen_sha256: 2327bcb297d35ca52fbbe429faa4236901fd10bcd2a1d5ea48b3cc7cb8ff42b9
---

# PO-Briefing: fix-445-nginx-orte-meldung

- **Spec:** docs/specs/betrieb/wegepruefung-ohne-alarm-445.md
- **Issue:** #445
- **Erstellt:** 2026-11-09

## Was gebaut wird

Die Wegeprüfung schickt keinen Telegram-Alarm mehr; fehlende Konnektor-Pfade erscheinen nur noch als Warnung.

## Definition of Done

Keine neuen Telegram-Meldungen zu nginx-Pfaden, Bilder der Infoseite laden auf dem Server, und die sechs alten Nachrichten sind erledigt.

## Wie geprüft wird

Ein automatischer Test belegt: Warnzeile ja, Meldung nein; Serverumstellung und Überwachungs-Check werden nur manuell geprüft.

## Kritische Anmerkungen

- Vorhaben 3 (neue Orte automatisch einrichten) fehlt bewusst; Ihre Entscheidung vom 9.11., eigener Schritt. Bis dahin bleibt es Handarbeit.
- Der Überwachungs-Check liegt in einem anderen Repository und hat keinen automatischen Test.
- Ohne Telegram erfahren Sie fehlende Orte nicht sofort, nur über Issue und Überwachung.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
