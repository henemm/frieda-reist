---
spec_file: docs/specs/betrieb/wackelige-browsertests-654.md
spec_sha256: 83ffa5ef13a24359a22d97f86411a002956d09b562cafb538324ed3eeb38859e
spec_frozen_sha256: 533da01a63d7e2ffecd096b97c1c9a41a786363607f6d5ac63d063caa0c4cbf1
---

# PO-Briefing: fix-654-sw-test-bild

- **Spec:** docs/specs/betrieb/wackelige-browsertests-654.md
- **Issue:** #654
- **Erstellt:** 2026-11-25

## Was gebaut wird

Ein wackeliger automatischer Test zum Vergessen gelöschter Bilder wird robuster, strenger und nennt bei erneutem Ausfall den Grund.

## Definition of Done

Der Test und seine neuen Nachweise laufen in mindestens drei CI-Läufen in beiden Browsern grün, das Produkt bleibt unverändert.

## Wie geprüft wird

Acht Nachweistests mit eingespielten Fehlern zeigen, dass bekannte Ausfallwege grün bleiben und echte Fehler rot; die CI-Ursache selbst beweisen sie nicht.

## Kritische Anmerkungen

- Das Ticket verlangt, die Ursache zu klären; der Auslöser in der CI bleibt laut Spec unbewiesen.
- Ob der neue Worker in beiden Browsern wirklich wartet, ist ungemessen; sonst geht die Spec zurück.
- Webkit ist lokal nicht prüfbar, erst die CI zeigt es.

## Freigabe-Frage

Genügt dir ein robusterer, selbsterklärender Test, obwohl die eigentliche Ursache des CI-Ausfalls unbewiesen bleibt?

## Ampel

Ampel: rot
