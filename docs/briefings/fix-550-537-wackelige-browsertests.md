---
spec_file: docs/specs/betrieb/wackelige-browsertests-550-537.md
spec_sha256: 4f5b5b722f5241115bf2a7ce1555ae1004b5d12b24e7d2fc649c41ae8838857b
spec_frozen_sha256: 7d4537481516fec273dc740fd532617abb8c7c08abc873cdc4adede747e38209
---

# PO-Briefing: fix-550-537-wackelige-browsertests

- **Spec:** docs/specs/betrieb/wackelige-browsertests-550-537.md
- **Issue:** #550 und #537
- **Erstellt:** 2026-11-13

## Was gebaut wird

Drei gelegentlich grundlos rot werdende Prüfungen laufen zuverlässig; die Seite selbst bleibt für Nutzer unverändert.

## Definition of Done

Elf Belastungsläufe und mehrere Gesamtläufe bleiben ohne Rot, die automatische Prüfung in der Auslieferung ist grün, die Seite ist unverändert.

## Wie geprüft wird

Kleine Tests belegen das Wiederholen der Bildaufnahme; das Warten der Browsertests belegen nur Belastungsläufe, nicht ein gezielt erzwungener Fehler.

## Kritische Anmerkungen

- Scheitern Bausteinbilder dreimal, gibt es nur eine Warnung statt Rot; fehlende Bilder könnten übersehen werden.
- Der Bildfehler in der Auslieferungsprüfung lässt sich nicht erzwingen; Wirkung zeigt sich erst über mehrere echte Läufe.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
