---
entity_id: funktionsseiten-711-planen-1
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-planen
tags: [infoseite, funktionen, unterseite, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/tests/test_funktionsseiten_711.py]
---

# Unterseiten „Die Reise als geprüfte Wahrheit“ und „Planen im Gespräch“ (#711, Etappe 2, Planen, Teil 1)

Workflow: `feat-711-planen`. Kontext: `docs/context/feat-711-planen.md`. Form: `docs/specs/oberflaeche/funktionsseiten-711-teil3.md`
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

Interessenten verstehen auf je einer Seite, wie Frieda eine Reise festhält (Herkunft, Prüfdatum, nichts geht verloren) und wie
man mit Claude plant und verbindet, mit Beispielen aus der erfundenen Wanderung (Ida und Karl).

## Prüfstelle (ADR-0001)

Nur Erklärseiten; Texte im Katalog (ADR-0006); keine Reisedaten, keine KI, nur Beispielreisen; vorhandene Bausteine (ADR-0002).

## Scope

1. `INFO_UNTERSEITEN` bekommt `wahrheit` (Bild `wahl`, Gespräch Ida/Claude, Siehe: gespraech, alternativen, buchungen, packliste)
   und `gespraech` (Bild `tag`, vier Blasen, Siehe: gespraeche, wahrheit, alternativen, konto).
2. Texte `info.bereich.wahrheit.…` und `info.bereich.gespraech.…` in DE und EN: lead, wo, wer, Bildunterschrift, tun, wie,
   Gespräch, Rollen, gut. Quelle: `docs/funktionen/reisemodell.md` und `gespraech.md`, ohne Werkzeugnamen und Issue-Nummern.
3. Kein neues Bild, kein Code.

Estimated Changes: 3 Dateien (Bilder nicht mitgezählt), unter 250 Zeilen.

### Nicht im Scope
Andere Unterseiten (Teil 2: alternativen, buchungen; Teil 3: gespraeche, lebenslauf; andere Gruppen).

## Acceptance Criteria

- AC-1: `/info/funktionen/wahrheit/` und `/info/funktionen/gespraech/` liefern in DE und EN 200 mit allen Abschnitten aus dem
  Katalog (`test_unterseite[wahrheit]`, `test_unterseite[gespraech]`).
- AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- AC-3: Texte und Bilder vollständig je Sprache (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in `test_texte.py`
  nicht länger; englische Texte ohne deutsche Wörter (`test_englisch_schnittstelle`).
- AC-4: Beispiele stimmen mit `beispiel/reisen/beispielreise` überein (Preise 85 €/70 €, 120 €/140 € am Samstag, Wahl der Pension
  Burgblick durch Ida, „nicht gebucht“); Bildunterschriften beschreiben nur, was das Bild zeigt.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | zwei Einträge in INFO_UNTERSEITEN |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der zwei Unterseiten |

## Test Plan

- RED: Einträge zuerst ohne Texte → `test_unterseite[...]` und Texttests rot; dann Texte → grün.
- Danach `test_funktionsseiten_711.py`, `test_texte.py`, `test_englisch*.py`, `test_infoseite*.py`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine — reiner Inhalt in vorhandener Form; folgt ADR-0002, ADR-0003, ADR-0006.

## Definition of Done

- [ ] Tests rot, dann grün; CI grün; Vorspulen auf `main`
- [ ] Auf der Instanz per `curl` geprüft

## Changelog

- 2026-11-26: Initial.
