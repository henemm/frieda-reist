---
entity_id: funktionsseiten-711-planen-3
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-planen-3
tags: [infoseite, funktionen, unterseite, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/info/erzeugen.py, engine/tests/test_funktionsseiten_711.py]
---

# Unterseiten „Gute Gespräche“ und „Von der Idee bis zum Archiv“ (#711, Etappe 2, Planen, Teil 3)

Workflow: `feat-711-planen-3`. Kontext: `docs/context/feat-711-planen-3.md`. Form: `docs/specs/oberflaeche/funktionsseiten-711-teil3.md`
und `docs/design.md` („Form einer neuen Unterseite“).

## Source

`engine/anmeldung.py` (`INFO_UNTERSEITEN`), `engine/texte_de.py`, `engine/texte_en.py` (`info.bereich.<name>`).

## Dependencies

| Abhängigkeit | Art |
|---|---|
| `unterseite` in `engine/anmeldung.py` (Etappe 1) | nutzt |

## GitHub Issue

**Issue:** #711

## Approval

- [x] Approved: Form und Muster vom Product Owner am 26.11.2026 freigegeben; Etappe 2 füllt die Form mit Inhalt.

## Purpose

Interessenten sehen an typischen Abläufen, wie man mit Claude gut plant, und verstehen den Weg einer Reise von der Idee bis
ins Archiv mit Status und Bausteinen, mit Beispielen aus beiden Beispielreisen.

## Prüfstelle (ADR-0001)

Nur Erklärseiten; Texte im Katalog (ADR-0006); keine Reisedaten, keine KI, nur Beispielreisen; vorhandene Bausteine (ADR-0002).

## Scope

1. `INFO_UNTERSEITEN` bekommt `gespraeche` (Bild `zutun`; vier Blasen Ida/Claude) und `lebenslauf` (Bilder `stadt`, `zutun`;
   Gespräch Ida/Claude).
2. Texte `info.bereich.gespraeche.…` und `info.bereich.lebenslauf.…` in DE und EN, aus `docs/funktionen/gute-gespraeche.md` und
   `lebenszyklus.md`, ohne Werkzeugnamen und Issue-Nummern.
3. Neues Bild `stadt` (Überblick des Stadtwochenendes im Status „Idee“) in `engine/info/erzeugen.py`.
4. `test_unterseiten_planen` nennt alle sechs Bereiche der Gruppe.

Estimated Changes: 5 Dateien (Bilder nicht mitgezählt), unter 250 Zeilen.

### Nicht im Scope
Unterseiten anderer Gruppen.

## Acceptance Criteria

- AC-1: `/info/funktionen/gespraeche/` und `/info/funktionen/lebenslauf/` liefern in DE und EN 200 mit allen Abschnitten aus dem
  Katalog und ihren Bildern (`test_unterseite[gespraeche]`, `test_unterseite[lebenslauf]`, `test_unterseiten_planen`).
- AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- AC-3: Texte und Bilder vollständig je Sprache in den Maßen von `erzeugen` (`test_texte_und_bilder_jeder_unterseite`);
  Ausnahmelisten in `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`, `test_englisch_schnittstelle`).
- AC-4: Beispiele stimmen mit den Beispielreisen überein (Tag 3 Hohnstein–Brand–Altendorf 10,7 km, ca. 4 h, 400 m Aufstieg,
  Gasthaus an der Brandaussicht; Stadtwochenende im Status „Idee“ ohne Varianten und Karte; Malerweg im Status „Planung“);
  jede Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | zwei Einträge in INFO_UNTERSEITEN |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der zwei Unterseiten |
| engine/info/erzeugen.py, engine/info/*.webp | MODIFY/CREATE | ein neues Bild |
| engine/tests/test_funktionsseiten_711.py | MODIFY | test_unterseiten_planen |

## Test Plan

- RED: `test_unterseiten_planen` verlangt die zwei Bereiche → rot; dann Einträge, Texte und Bilder → grün.
- Danach `test_funktionsseiten_711.py`, `test_texte.py`, `test_englisch*.py`, `test_infoseite*.py`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine — reiner Inhalt in vorhandener Form; folgt ADR-0002, ADR-0003, ADR-0006.

## Definition of Done

- [ ] Tests rot, dann grün; CI grün; Vorspulen auf `main`
- [ ] Auf der Instanz per `curl` geprüft

## Changelog

- 2026-11-26: Initial.
