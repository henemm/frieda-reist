---
entity_id: funktionsseiten-711-planen-2
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-planen-2
tags: [infoseite, funktionen, unterseite, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/info/erzeugen.py, engine/tests/test_funktionsseiten_711.py]
---

# Unterseiten „Alternativen und Entscheidungen“ und „Buchungen und Belege“ (#711, Etappe 2, Planen, Teil 2)

Workflow: `feat-711-planen-2`. Kontext: `docs/context/feat-711-planen-2.md`. Form: `docs/specs/oberflaeche/funktionsseiten-711-teil3.md`
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

Interessenten verstehen, wie Frieda Möglichkeiten vergleicht und Entscheidungen festhält und wie Buchungen mit Belegen,
Fristen und Erinnerungen funktionieren, mit Beispielen und Handybildern aus der erfundenen Wanderung.

## Prüfstelle (ADR-0001)

Nur Erklärseiten; Texte im Katalog (ADR-0006); keine Reisedaten, keine KI, nur Beispielreisen; vorhandene Bausteine (ADR-0002).

## Scope

1. `INFO_UNTERSEITEN` bekommt `alternativen` (Bilder `vergleich`, `wahl`, `zutun`; Gespräch Karl/Claude) und `buchungen`
   (Bilder `buchung`, `bahnbuchung`, `zubuchen`; vier Blasen Ida/Claude).
2. Texte `info.bereich.alternativen.…` und `info.bereich.buchungen.…` in DE und EN, aus `docs/funktionen/alternativen.md` und
   `buchungen.md`, ohne Werkzeugnamen und Issue-Nummern.
3. Neue Bilder in `engine/info/erzeugen.py` (`BILDER`): `vergleich` (V-01), `buchung` (B-01), `bahnbuchung` (B-02),
   `zubuchen` (zu-buchen), erzeugt mit `engine/info/erzeugen.py`.
4. `test_unterseiten_planen` nennt auch die zwei Bereiche.

Estimated Changes: 5 Dateien (Bilder nicht mitgezählt), unter 250 Zeilen.

### Nicht im Scope
Andere Unterseiten (Teil 3: gespraeche, lebenslauf; andere Gruppen).

## Acceptance Criteria

- AC-1: `/info/funktionen/alternativen/` und `/info/funktionen/buchungen/` liefern in DE und EN 200 mit allen Abschnitten aus dem
  Katalog und ihren Bildern (`test_unterseite[alternativen]`, `test_unterseite[buchungen]`, `test_unterseiten_planen`).
- AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- AC-3: Texte und Bilder vollständig je Sprache in den Maßen von `erzeugen` (`test_texte_und_bilder_jeder_unterseite`);
  Ausnahmelisten in `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- AC-4: Beispiele stimmen mit `beispiel/reisen/beispielreise` überein (Wahl V-01 mit drei Möglichkeiten, Hockstein, Bus nur mit
  Gepäck in der Pension Burgblick, Buchung HE-2027-0415 mit 30 € Anzahlung, S-Bahn von Karl, stornierte Buchung); jede
  Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | zwei Einträge in INFO_UNTERSEITEN |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der zwei Unterseiten |
| engine/info/erzeugen.py, engine/info/*.webp | MODIFY/CREATE | vier neue Bilder |
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
