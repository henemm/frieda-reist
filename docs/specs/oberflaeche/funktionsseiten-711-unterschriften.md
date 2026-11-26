---
entity_id: funktionsseiten-711-unterschriften
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-unterschriften
tags: [infoseite, funktionen, bildunterschrift, mehrsprachigkeit]
test_targets: [engine/texte_de.py, engine/texte_en.py, engine/tests/test_funktionsseiten_711.py]
---

# Bildunterschriften „Überblick“ und „Tag“ nur mit dem Sichtbaren (#711, Etappe 3, Teil 3)

Workflow: `feat-711-unterschriften`. Kontext: `docs/context/feat-711-unterschriften.md`.

## Source

`engine/texte_de.py`, `engine/texte_en.py`: `info.bereich.reiseseite.bild.reise`, `info.bereich.reiseseite.bild.tag`,
`info.bild.reise`, `info.bild.tag`; dazu `info.bereich.betrieb.gespraech.2`.

## Dependencies

| Abhängigkeit | Art |
|---|---|
| Bilder `engine/info/reise-<sp>.webp`, `tag-<sp>.webp` | beschreibt, unverändert |

## GitHub Issue

**Issue:** #711

## Approval

- [x] Approved: Regel „die Unterschrift beschreibt nur, was das Bild zeigt“ vom Product Owner am 26.11.2026 (Form der
  Unterseiten); Auftrag dieser Etappe.

## Purpose

Die Unterschriften der Bilder „Überblick“ und „Tag“ auf der Unterseite Reiseseite und auf der Infoseite versprechen mehr, als
die Handybilder zeigen (Zeitachse aller Tage, erwogene Pläne, Weg, Nacht, Quelle zu jeder Angabe). Sie sollen nur nennen, was
zu sehen ist: Überblick mit Titel, Zeitraum, Zähler bis zur Abreise, Anreise und Karte, unten die Reiter; Tag 2 mit den Plänen
A und B, kurzer Übersicht und dem Anfang der Zeitleiste (S-Bahn ab Dresden mit Zeiten und Quelle, darunter ihre Buchung).

## Prüfstelle (ADR-0001)

Nur Texte der Erklärseiten im Katalog (ADR-0006); keine Reisedaten, keine KI.

## Scope

1. Vier Unterschriften je DE und EN neu.
2. Fund des Adversary aus Teil 2: `info.bereich.betrieb.gespraech.2` nennt das Ziel „höchstens zwei Minuten“ der Quelle.
3. Tests: Die Unterschriften dieser Bilder nennen nichts, was das Bild nicht zeigt (Zeitachse aller Tage, Pläne, Nacht); die
   Blase der Betriebsseite nennt das Ziel der Quelle.

Estimated Changes: 3 Dateien, unter 50 Zeilen.

### Nicht im Scope
Andere Unterschriften; Bilder selbst; Verweis von GitHub auf die Webseite.

## Acceptance Criteria

- AC-1: `info.bereich.reiseseite.bild.reise` und `info.bild.reise` nennen in DE und EN weder die Zeitachse der Tage noch die
  erwogenen Pläne, sondern Zähler, Anreise und Karte (`test_unterschriften_nur_das_sichtbare`).
- AC-2: `info.bereich.reiseseite.bild.tag` und `info.bild.tag` nennen in DE und EN weder Nacht noch „jede Angabe“, sondern
  die Zeitleiste mit S-Bahn, Quelle und Buchung (`test_unterschriften_nur_das_sichtbare`).
- AC-3: `info.bereich.betrieb.gespraech.2` nennt „höchstens zwei Minuten“ (DE) und „two minutes“ (EN) (`test_betrieb_nennt_das_ziel_der_quelle`).
- AC-4: Texte vollständig, Fachwörter einheitlich (`test_texte`); Bilder unverändert.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/texte_de.py, engine/texte_en.py | MODIFY | fünf Texte je Sprache |
| engine/tests/test_funktionsseiten_711.py | MODIFY | zwei Tests |

## Test Plan

- RED: `test_unterschriften_nur_das_sichtbare` und `test_betrieb_nennt_das_ziel_der_quelle` → rot; dann Texte → grün.
- Danach `test_funktionsseiten_711.py`, `test_texte.py`, `test_englisch.py`, `test_infoseite.py`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine.

## Definition of Done

- [ ] Tests rot, dann grün; CI grün; Vorspulen auf `main`
- [ ] Auf der Instanz per `curl` geprüft

## Changelog

- 2026-11-26: Initial.
