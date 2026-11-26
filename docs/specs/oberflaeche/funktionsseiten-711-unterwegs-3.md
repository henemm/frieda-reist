---
entity_id: funktionsseiten-711-unterwegs-3
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-unterwegs-3
tags: [infoseite, funktionen, unterseite, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/info/erzeugen.py, engine/tests/test_funktionsseiten_711.py]
---

# Unterseite „Erinnerungen und Meldungen“ (#711, Etappe 2, Unterwegs und gemeinsam, Teil 3)

Workflow: `feat-711-unterwegs-3`. Kontext: `docs/context/feat-711-unterwegs-3.md`. Form: `docs/design.md` („Form einer neuen
Unterseite“), Vorbild `docs/specs/oberflaeche/funktionsseiten-711-unterwegs-2.md`.

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

Interessenten verstehen, woran Frieda erinnert, wem sie es meldet, auf welchen Wegen (Seite, Push, Mail) und wie die Reise in
den eigenen Kalender kommt, mit Beispielen und Handybildern aus der erfundenen Wanderung.

## Prüfstelle (ADR-0001)

Nur Erklärseiten; Texte im Katalog (ADR-0006); keine Reisedaten, keine KI, nur Beispielreisen; vorhandene Bausteine (ADR-0002).

## Scope

1. `INFO_UNTERSEITEN` bekommt `erinnerungen` (Bilder `bahnbuchung`, `kalender`; vier Blasen Ida/Claude).
2. Texte `info.bereich.erinnerungen.…` in DE und EN, aus `docs/funktionen/erinnerungen.md`, ohne Werkzeugnamen und
   Issue-Nummern.
3. Neues Bild in `BILDER`: `kalender` (Überblick, Ziel `.reise-tage > .chips`).
4. `test_unterseiten_unterwegs` verlangt alle Bereiche der Gruppe außer der schon vorhandenen Reiseseite.

Estimated Changes: 5 Dateien (Bilder nicht mitgezählt), unter 250 Zeilen.

### Nicht im Scope
Gruppe „Konto und Betrieb“; Verweis von GitHub auf die Webseite.

## Acceptance Criteria

- AC-1: `/info/funktionen/erinnerungen/` liefert in DE und EN 200 mit allen Abschnitten aus dem Katalog und seinen Bildern
  (`test_unterseite[erinnerungen]`, `test_unterseiten_unterwegs`).
- AC-2: Die Übersicht verlinkt den Bereich statt „Seite folgt“; die Gruppe „Unterwegs und gemeinsam“ hat keine Zeile
  „Seite folgt“ mehr (`test_uebersicht_alle_funktionen`).
- AC-3: Texte und Bilder vollständig je Sprache (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in
  `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- AC-4: Beispiele stimmen mit der Beispielreise und der Quelle überein (S-Bahn-Buchung von Karl mit Frist 13.5. „Ticket in die
  App laden“; Pension Burgblick und Wanderherberge Altendorf nicht gebucht; Weg zum Zug am letzten Tag offen; Status
  „planung“ ohne Baustein `waechter`; drei Tage Vorlauf, 60 Tage Prüfalter, Ruhezeit 21:30–7:00, 14 Tage); jede
  Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.
- AC-5: Vorhandene Bilder bleiben unverändert im Commit.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | ein Eintrag in INFO_UNTERSEITEN |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der Unterseite |
| engine/info/erzeugen.py | MODIFY | ein neues Bild |
| engine/info/*.webp | CREATE | kalender je DE und EN |
| engine/tests/test_funktionsseiten_711.py | MODIFY | test_unterseiten_unterwegs |

## Test Plan

- RED: `test_unterseiten_unterwegs` verlangt `erinnerungen` → rot; dann Eintrag, Texte und Bild → grün.
- Danach `test_funktionsseiten_711.py`, `test_texte.py`, `test_englisch*.py`, `test_infoseite*.py`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine — reiner Inhalt in vorhandener Form; folgt ADR-0002, ADR-0003, ADR-0006.

## Definition of Done

- [ ] Tests rot, dann grün; CI grün; Vorspulen auf `main`
- [ ] Auf der Instanz per `curl` geprüft

## Changelog

- 2026-11-26: Initial.
