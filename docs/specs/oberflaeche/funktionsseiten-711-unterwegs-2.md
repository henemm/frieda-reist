---
entity_id: funktionsseiten-711-unterwegs-2
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-unterwegs-2
tags: [infoseite, funktionen, unterseite, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/info/erzeugen.py, engine/tests/test_funktionsseiten_711.py]
---

# Unterseiten „Zusammenarbeit“ und „Bilder“ (#711, Etappe 2, Unterwegs und gemeinsam, Teil 2)

Workflow: `feat-711-unterwegs-2`. Kontext: `docs/context/feat-711-unterwegs-2.md`. Form: `docs/design.md` („Form einer neuen
Unterseite“), Vorbild `docs/specs/oberflaeche/funktionsseiten-711-unterwegs.md`.

## Source

`engine/anmeldung.py` (`INFO_UNTERSEITEN`), `engine/texte_de.py`, `engine/texte_en.py` (`info.bereich.<name>`),
`engine/info/erzeugen.py` (`BILDER`).

## Dependencies

| Abhängigkeit | Art |
|---|---|
| `unterseite` in `engine/anmeldung.py` (Etappe 1) | nutzt |
| Rollziel `ziel` der Aufnahme (Teil 1) | nutzt |

## GitHub Issue

**Issue:** #711

## Approval

- [x] Approved: Form und Muster vom Product Owner am 26.11.2026 freigegeben; Etappe 2 füllt die Form mit Inhalt.

## Purpose

Interessenten verstehen, wie mehrere Personen eine Reise gemeinsam planen (Rollen, Einladen, Rückmeldungen, Fragen, Aufgaben,
Wünsche) und wie Bilder, eigene Fotos und das App-Symbol funktionieren, mit Beispielen und Handybildern aus der erfundenen
Wanderung.

## Prüfstelle (ADR-0001)

Nur Erklärseiten; Texte im Katalog (ADR-0006); keine Reisedaten, keine KI, nur Beispielreisen; vorhandene Bausteine (ADR-0002).

## Scope

1. `INFO_UNTERSEITEN` bekommt `zusammenarbeit` (Bilder `mitreisende`, `tag`; vier Blasen Karl/Claude) und `bilder` (Bilder
   `ort`, `etappe`, `lage`; vier Blasen Ida/Claude).
2. Texte `info.bereich.zusammenarbeit.…` und `info.bereich.bilder.…` in DE und EN, aus `docs/funktionen/zusammenarbeit.md`
   und `bilder.md`, ohne Werkzeugnamen und Issue-Nummern.
3. Neue Bilder in `BILDER`: `mitreisende` (Überblick, Ziel `.mitreisende`), `etappe` (E-02).
4. `test_unterseiten_unterwegs` verlangt auch die zwei Bereiche.

Estimated Changes: 5 Dateien (Bilder nicht mitgezählt), unter 250 Zeilen.

### Nicht im Scope
erinnerungen (Teil 3); andere Gruppen.

## Acceptance Criteria

- AC-1: `/info/funktionen/zusammenarbeit/` und `/info/funktionen/bilder/` liefern in DE und EN 200 mit allen Abschnitten aus
  dem Katalog und ihren Bildern (`test_unterseite[zusammenarbeit]`, `test_unterseite[bilder]`, `test_unterseiten_unterwegs`).
- AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- AC-3: Texte und Bilder vollständig je Sprache (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in
  `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- AC-4: Beispiele stimmen mit der Beispielreise überein (Ida organisiert, Karl wirkt mit und reist ab 14.5.; Frage zum letzten
  Tag; Karls Wunsch Kirnitzschtalbahn passt zum letzten Tag; 10 Punkte je Person; Frist 13.5.2027 für das Bahnticket;
  Titelbild Schrammsteine, Blick von der Brandaussicht von Romzig unter CC0; Hohnstein mit drei Bildern); jede
  Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.
- AC-5: Vorhandene Bilder bleiben unverändert im Commit.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | zwei Einträge in INFO_UNTERSEITEN |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der zwei Unterseiten |
| engine/info/erzeugen.py | MODIFY | zwei neue Bilder |
| engine/info/*.webp | CREATE | mitreisende, etappe je DE und EN |
| engine/tests/test_funktionsseiten_711.py | MODIFY | test_unterseiten_unterwegs |

## Test Plan

- RED: `test_unterseiten_unterwegs` verlangt `zusammenarbeit` und `bilder` → rot; dann Einträge, Texte und Bilder → grün.
- Danach `test_funktionsseiten_711.py`, `test_texte.py`, `test_englisch*.py`, `test_infoseite*.py`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine — reiner Inhalt in vorhandener Form; folgt ADR-0002, ADR-0003, ADR-0006.

## Definition of Done

- [ ] Tests rot, dann grün; CI grün; Vorspulen auf `main`
- [ ] Auf der Instanz per `curl` geprüft

## Changelog

- 2026-11-26: Initial.
