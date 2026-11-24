---
spec_file: docs/specs/konnektor/veraltete-meldungen-687.md
spec_sha256: 2c93bb21a02d5ffb4045589e33c6532cf883dee6d6ccc2e2f906107eb47809fe
spec_frozen_sha256: 0fc4c6244f30400625454d01c3df21ffaa9ca46fe3a899f6c7a2cf08e9a37735
---

# PO-Briefing: fix-687-veraltete-meldungen

- **Spec:** docs/specs/konnektor/veraltete-meldungen-687.md
- **Issue:** #687 (zusammen mit #693)
- **Erstellt:** 2026-11-24

## Was gebaut wird

Meldungen zu entfernten Reisen und zu erledigten oder gelöschten Anfragen verschwinden aus Reiseübersicht und Mein Konto.

## Definition of Done

Entfernte Reisen und entschiedene oder gelöschte Anfragen erscheinen nicht mehr unter Meldungen, offene Meldungen bleiben sichtbar, Testanfragen werden weiterhin gemeldet.

## Wie geprüft wird

Automatische Tests decken jede Lage in Konnektor und Mein Konto ab; bereits eingereihte Push-Nachrichten und die Tageszusammenfassung sind nicht abgedeckt.

## Kritische Anmerkungen

- Push-Nachrichten und tägliche Zusammenfassung können eine bereits erledigte Anfrage noch nennen (dokumentierte Grenze).
- Bei Altmeldungen kann eine Adressänderung die Meldung vorzeitig verschwinden lassen, obwohl die Bitte offen ist.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
