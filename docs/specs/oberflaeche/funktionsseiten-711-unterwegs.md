---
entity_id: funktionsseiten-711-unterwegs
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-unterwegs
tags: [infoseite, funktionen, unterseite, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/info/erzeugen.py, engine/info/aufnehmen.mjs, engine/tests/test_funktionsseiten_711.py]
---

# Unterseiten „Karte“ und „Packliste“ (#711, Etappe 2, Unterwegs und gemeinsam, Teil 1)

Workflow: `feat-711-unterwegs`. Kontext: `docs/context/feat-711-unterwegs.md`. Form: `docs/design.md` („Form einer neuen
Unterseite“), Vorbild `docs/specs/oberflaeche/funktionsseiten-711-planen-2.md`.

## Source

`engine/anmeldung.py` (`INFO_UNTERSEITEN`), `engine/texte_de.py`, `engine/texte_en.py` (`info.bereich.<name>`),
`engine/info/erzeugen.py` (`BILDER`), `engine/info/aufnehmen.mjs`.

## Dependencies

| Abhängigkeit | Art |
|---|---|
| `unterseite` in `engine/anmeldung.py` (Etappe 1) | nutzt |
| `engine/info/erzeugen.py`, `aufnehmen.mjs` | erweitert (optionales Rollziel) |

## GitHub Issue

**Issue:** #711

## Approval

- [x] Approved: Form und Muster vom Product Owner am 26.11.2026 freigegeben; Etappe 2 füllt die Form mit Inhalt.

## Purpose

Interessenten verstehen, wie Frieda die Karte der Reise aus dem Plan zeichnet und wie die Packliste mit Summen, Zuständigen und
Haken funktioniert, mit Beispielen und Handybildern aus den erfundenen Beispielreisen.

## Prüfstelle (ADR-0001)

Nur Erklärseiten; Texte im Katalog (ADR-0006); keine Reisedaten, keine KI, nur Beispielreisen; vorhandene Bausteine (ADR-0002).

## Scope

1. `INFO_UNTERSEITEN` bekommt `karte` (Bilder `karte`, `lage`; vier Blasen Ida/Claude) und `packliste` (Bilder `summen`,
   `packliste`; vier Blasen Ida/Claude).
2. Texte `info.bereich.karte.…` und `info.bereich.packliste.…` in DE und EN, aus `docs/funktionen/karte.md` und
   `packliste.md`, ohne Werkzeugnamen und Issue-Nummern.
3. `aufnehmen.mjs` nimmt je Bild ein optionales `ziel` (CSS-Selektor) und rollt die Ansicht dorthin, weil die Karte im
   Überblick kein eigenes Sprungziel hat. Neue Bilder in `BILDER`: `karte` (Überblick, Ziel `.kartenbox`), `lage` (U-01),
   `summen` (Packliste der Wanderung); vorhanden: `packliste` (Stadtwochenende).
4. Ein Test `test_unterseiten_unterwegs` verlangt die Bereiche der Gruppe, die es schon gibt.

Estimated Changes: 6 Dateien (Bilder nicht mitgezählt), unter 250 Zeilen.

### Nicht im Scope
zusammenarbeit, bilder (Teil 2), erinnerungen (Teil 3); andere Gruppen.

## Acceptance Criteria

- AC-1: `/info/funktionen/karte/` und `/info/funktionen/packliste/` liefern in DE und EN 200 mit allen Abschnitten aus dem
  Katalog und ihren Bildern (`test_unterseite[karte]`, `test_unterseite[packliste]`, `test_unterseiten_unterwegs`).
- AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- AC-3: Texte und Bilder vollständig je Sprache in den Maßen von `erzeugen` (`test_texte_und_bilder_jeder_unterseite`);
  Ausnahmelisten in `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- AC-4: Beispiele stimmen mit den Beispielreisen überein (Packliste 2810 g, 900/980/930 g, 70 € Anschaffung; Wanderstöcke am
  ersten Wandertag, Stirnlampe an der Wanderherberge Altendorf von Karl, Erste-Hilfe-Set trägt Ida, Sonnencreme weggelassen;
  Stadtwochenende: Ausweis packt Lea; Hotel am Elbufer mit Adresse und Kartenlinks; Bahn gestrichelt); jede Bildunterschrift
  beschreibt nur, was das Bild in DE und EN zeigt.
- AC-5: Ohne `ziel` nimmt `aufnehmen.mjs` jedes Bild wie bisher auf; vorhandene Bilder bleiben unverändert im Commit.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | zwei Einträge in INFO_UNTERSEITEN |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der zwei Unterseiten |
| engine/info/erzeugen.py, engine/info/aufnehmen.mjs | MODIFY | drei neue Bilder, optionales Rollziel |
| engine/info/*.webp | CREATE | karte, lage, summen je DE und EN |
| engine/tests/test_funktionsseiten_711.py | MODIFY | test_unterseiten_unterwegs |

## Test Plan

- RED: `test_unterseiten_unterwegs` verlangt `karte` und `packliste` → rot; dann Einträge, Texte und Bilder → grün.
- Danach `test_funktionsseiten_711.py`, `test_texte.py`, `test_englisch*.py`, `test_infoseite*.py`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine — reiner Inhalt in vorhandener Form; folgt ADR-0002, ADR-0003, ADR-0006.

## Definition of Done

- [ ] Tests rot, dann grün; CI grün; Vorspulen auf `main`
- [ ] Auf der Instanz per `curl` geprüft

## Changelog

- 2026-11-26: Initial.
