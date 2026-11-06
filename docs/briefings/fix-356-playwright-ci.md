---
spec_file: docs/specs/betrieb/ci-playwright-zeitgrenze-356.md
spec_sha256: d0d3cf3dadb658b635aab762312f18051f65e3e0b1e719a1062bb1e79e986d44
spec_frozen_sha256: b2bcb70860b348fd0a1df7ac83db314fc26d9881f7c70f724841646fa1a23dbb
---

# PO-Briefing: fix-356-playwright-ci

- **Spec:** docs/specs/betrieb/ci-playwright-zeitgrenze-356.md
- **Issue:** #356
- **Erstellt:** 2026-11-06

## Was gebaut wird

Die CI bricht hängende Paketdownloads früh ab, wiederholt sie einmal und speichert die Browser zwischen.

## Definition of Done

Beide Prüfläufe im Pull Request sind grün, der zweite Lauf zeigt einen Cache-Treffer, und ein Hänger kostet höchstens etwa zehn Minuten.

## Wie geprüft wird

Fünf Struktur-Tests lesen die Workflow-Datei; ein echtes Hängen des Spiegels beweisen sie nicht, nur die Pull-Request-Läufe zeigen die Wirkung.

## Kritische Anmerkungen

- Zusatz: Auch der Schritt „Python-Pakete“ bekommt Zeitgrenzen, obwohl das Ticket nur Playwright nennt; gleiche Ursache.
- Ein hängender Spiegel lässt sich nicht erzwingen; die Wirkung bleibt bis zum nächsten echten Hänger unbewiesen.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
