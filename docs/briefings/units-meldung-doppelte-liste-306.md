---
spec_file: docs/specs/fast/units-meldung-doppelte-liste-306.md
spec_sha256: e08a3e038e32165c8b83e33156cecb4c0c58bd8e90f5e59f3bcc3f5d10190817
spec_frozen_sha256: 49839eeba00f58fed7c73137584faa7d3da077c066f5aa9eaaf4e763efb7ec41
---

# PO-Briefing: units-meldung-doppelte-liste-306

- **Spec:** docs/specs/fast/units-meldung-doppelte-liste-306.md
- **Issue:** #306
- **Erstellt:** 2026-11-04

## Was gebaut wird

Die Meldung über abweichende Einheiten nennt jede Abweichung nur noch einmal, auch wenn das Hilfsprogramm fehlt.

## Definition of Done

Fehlt das Hilfsprogramm, erscheint in der Meldung jede Abweichung genau einmal, und der Ausgang bleibt unverändert.

## Wie geprüft wird

Ein Test belegt, dass die Liste bei fehlendem Hilfsprogramm nicht mehr doppelt erscheint; das Gesamtergebnis der Meldung wird nicht direkt getestet.

## Kritische Anmerkungen

- Die Anforderung „jede Abweichung genau einmal“ (AC-2) hat keinen eigenen Test, sie wird nur abgeleitet.
- Bereits gemeldete Abweichungen werden einmalig erneut gemeldet; laut Spec harmlos.
- Erster Punkt des Issues (Serveradresse) ist laut Anfrage schon erledigt, nicht Teil dieser Spec.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
