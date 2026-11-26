---
entity_id: funktionsseiten-711-konto
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-konto
tags: [infoseite, funktionen, unterseite, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/info/erzeugen.py, engine/tests/test_funktionsseiten_711.py]
---

# Unterseiten „Konto und Datenschutz“ und „Sprachen“ (#711, Etappe 3, Konto und Betrieb, Teil 1)

Workflow: `feat-711-konto`. Kontext: `docs/context/feat-711-konto.md`. Form: `docs/design.md` („Form einer neuen
Unterseite“), Vorbild `docs/specs/oberflaeche/funktionsseiten-711-unterwegs-3.md`.

## Source

`engine/anmeldung.py` (`INFO_UNTERSEITEN`), `engine/texte_de.py`, `engine/texte_en.py` (`info.bereich.<name>`),
`engine/info/erzeugen.py` (`BILDER`).

## Dependencies

| Abhängigkeit | Art |
|---|---|
| `unterseite` in `engine/anmeldung.py` (Etappe 1) | nutzt |
| Rollziel `ziel` der Aufnahme (Etappe 2) | nutzt |

## GitHub Issue

**Issue:** #711

## Approval

- [x] Approved: Form und Muster vom Product Owner am 26.11.2026 freigegeben; Etappe 3 füllt die Form mit Inhalt.

## Purpose

Interessenten verstehen, wie Anmeldung ohne Passwort, Mein Konto, die Verbindung mit Claude, Profil, Export und Löschen
funktionieren, und wie Frieda mit Sprachen umgeht (Sprache der Reise, des Kontos, Umschalter für Gäste; Inhalte werden nie
übersetzt).

## Prüfstelle (ADR-0001)

Nur Erklärseiten; Texte im Katalog (ADR-0006); keine Reisedaten, keine KI, nur Beispielreisen; vorhandene Bausteine (ADR-0002).

## Scope

1. `INFO_UNTERSEITEN` bekommt `konto` (Bilder `fuss`, `mitreisende`) und `sprachen` (Bilder `fuss`, `tag`).
2. Texte `info.bereich.konto.…` und `info.bereich.sprachen.…` in DE und EN, aus `docs/funktionen/konto.md` und
   `docs/funktionen/sprachen.md`, ohne Werkzeugnamen und Issue-Nummern.
3. Neues Bild in `BILDER`: `fuss` (Überblick, Ziel `#fuss`: Sprachzeile für Gäste und Rechtszeile). Mein Konto lässt sich
   ohne Anmeldung nicht aufnehmen; die Konto-Seite nutzt deshalb Fuß und Mitreisende.
4. `test_unterseiten_konto` verlangt `konto` und `sprachen`.

Estimated Changes: 5 Dateien (Bilder nicht mitgezählt), unter 250 Zeilen.

### Nicht im Scope
Unterseite „Selbst betreiben“ (Teil 2); Bildunterschriften der Reiseseite; Verweis von GitHub auf die Webseite.

## Acceptance Criteria

- AC-1: `/info/funktionen/konto/` und `/info/funktionen/sprachen/` liefern in DE und EN 200 mit allen Abschnitten aus dem
  Katalog und ihren Bildern (`test_unterseite[konto]`, `test_unterseite[sprachen]`, `test_unterseiten_konto`).
- AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- AC-3: Texte und Bilder vollständig je Sprache (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in
  `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- AC-4: Inhalte stimmen mit der Quelle überein (Code sechsstellig, zehn Minuten, einmal; Anmeldung ein Jahr je Gerät; vier
  Schritte zum Verbinden; Profil nur mit Bestätigung, nur für dich sichtbar; ZIP-Export; Löschen mit Häkchen; Warteliste;
  neues Konto in der Sprache des Browsers, sonst Englisch; Inhalte nie übersetzt); jede Bildunterschrift beschreibt nur, was
  das Bild in DE und EN zeigt.
- AC-5: Vorhandene Bilder bleiben unverändert im Commit.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | zwei Einträge in INFO_UNTERSEITEN |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der Unterseiten |
| engine/info/erzeugen.py | MODIFY | ein neues Bild |
| engine/info/*.webp | CREATE | fuss je DE und EN |
| engine/tests/test_funktionsseiten_711.py | MODIFY | test_unterseiten_konto |

## Test Plan

- RED: `test_unterseiten_konto` verlangt `konto` und `sprachen` → rot; dann Einträge, Texte und Bild → grün.
- Danach `test_funktionsseiten_711.py`, `test_texte.py`, `test_englisch*.py`, `test_infoseite*.py`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine — reiner Inhalt in vorhandener Form; folgt ADR-0002, ADR-0003, ADR-0006.

## Definition of Done

- [ ] Tests rot, dann grün; CI grün; Vorspulen auf `main`
- [ ] Auf der Instanz per `curl` geprüft

## Changelog

- 2026-11-26: Initial.
