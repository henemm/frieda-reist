---
spec_file: docs/specs/betrieb/konto-loeschen-ablage-neu-694.md
spec_sha256: b9346eb1d8da87ad66f9b161f932573a0a56cdb51760c81d93c87c988d88dccb
spec_frozen_sha256: e30eb0ac05a371dc49e0172bd31836fb05bef970820eaaa20a555e23c0e0ec51
---

# PO-Briefing: fix-694-konto-loeschen-ablage-neu

- **Spec:** docs/specs/betrieb/konto-loeschen-ablage-neu-694.md
- **Issue:** #694
- **Erstellt:** 2026-11-27

## Was gebaut wird

Beim Löschen eines Kontos verschwinden Name und Adresse auch aus Betreiber-Meldungen, Wartelisten-Anfragen und Aufträgen ohne Reise.

## Definition of Done

Nach dem Löschen findet eine Textsuche in der Ablage ohne Reise weder Name noch Adresse der Person, fremde Einträge bleiben unverändert.

## Wie geprüft wird

Automatische Tests prüfen jede Lage samt Fehlerfall und fremden Einträgen; Mails, die Betreiber:innen schon erhielten, bleiben unberührt.

## Kritische Anmerkungen

- Eine ausstehende neue Reise bleibt bis zu fünf Minuten sichtbar, dann wird sie zur Löschung vorgemerkt (von dir freigegeben).
- Aufträge bleiben als Beleg bestehen, nur mit „gelöschte Person“; Statusangaben und frei geschriebene Namen werden nicht durchsucht.

## Freigabe-Frage

Keine – Ampel gruen.

## Ampel

Ampel: gruen
