---
entity_id: funktionsseiten-711-betrieb
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-betrieb
tags: [infoseite, funktionen, unterseite, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/tests/test_funktionsseiten_711.py]
---

# Unterseite „Selbst betreiben“ (#711, Etappe 3, Konto und Betrieb, Teil 2)

Workflow: `feat-711-betrieb`. Kontext: `docs/context/feat-711-betrieb.md`. Form: `docs/design.md` („Form einer neuen
Unterseite“), Vorbild `docs/specs/oberflaeche/funktionsseiten-711-konto.md`.

## Source

`engine/anmeldung.py` (`INFO_UNTERSEITEN`, `unterseite`), `engine/texte_de.py`, `engine/texte_en.py` (`info.bereich.<name>`).

## Dependencies

| Abhängigkeit | Art |
|---|---|
| `unterseite` in `engine/anmeldung.py` (Etappe 1) | nutzt und erweitert um einen Link zur technischen Doku |
| `instanz.QUELLCODE` | nutzt (Adresse des Repos) |
| Bilder `fuss`, `reise` | nutzt, vorhanden |

## GitHub Issue

**Issue:** #711

## Approval

- [x] Approved: Form und Muster vom Product Owner am 26.11.2026 freigegeben; Etappe 3 füllt die Form mit Inhalt.

## Purpose

Wer Frieda auf einem eigenen Server betreiben will, versteht in kurzer Form, was eine Instanz ist, was auf dem Server läuft
(ohne KI), wie Daten getrennt und gesichert werden und wie neue Software ankommt, und findet die technische Anleitung im Repo
(`docs/betrieb.md`) über einen Link. Die Seite bleibt kurz; Einzelheiten stehen nur in der Anleitung.

## Prüfstelle (ADR-0001)

Nur Erklärseiten; Texte im Katalog (ADR-0006); keine Reisedaten, keine KI, nichts Instanzspezifisches (der Link kommt aus
`instanz.QUELLCODE`); vorhandene Bausteine (ADR-0002).

## Scope

1. `INFO_UNTERSEITEN` bekommt `betrieb` (Bilder `fuss`, `reise`; zwei Blasen) mit dem neuen, optionalen Feld `doku` (Pfad im
   Repo, hier `docs/betrieb.md`).
2. `unterseite` zeigt bei `doku` unter „Siehe auch“ zusätzlich einen Link auf `<QUELLCODE>/blob/main/<doku>` (neues Fenster,
   Text `info.bereich.<name>.doku`).
3. Texte `info.bereich.betrieb.…` in DE und EN, kurz, aus `docs/funktionen/selbst-betreiben.md`.
4. Zwei Textfunde aus Teil 1: `info.bereich.sprachen.wer` (DE mit Doppelpunkten) und `info.bereich.sprachen.wie.1.text`
   (Meldungen selbst in der Sprache der Reise).
5. `test_unterseiten_konto` verlangt die ganze Gruppe; ein Test prüft den Link zur Anleitung.
6. Form in `docs/design.md` um `doku` ergänzt.

Estimated Changes: 5 Dateien, unter 250 Zeilen.

### Nicht im Scope
Bildunterschriften der Reiseseite; Verweis von GitHub auf die Webseite.

## Acceptance Criteria

- AC-1: `/info/funktionen/betrieb/` liefert in DE und EN 200 mit allen Abschnitten und Bildern (`test_unterseite[betrieb]`).
- AC-2: Die Übersicht hat keine Zeile „Seite folgt“ mehr (`test_unterseiten_konto`, `test_uebersicht_alle_funktionen`).
- AC-3: Die Unterseite verlinkt die Anleitung `docs/betrieb.md` im Repo aus `instanz.QUELLCODE`, mit `target="_blank"` und
  `rel="noopener"`; Seiten ohne `doku` haben keinen solchen Link (`test_link_zur_anleitung`).
- AC-4: Texte vollständig je Sprache; Ausnahmelisten nicht länger; Fachwörter einheitlich (`test_texte`). Inhalt treu zur
  Quelle (keine KI auf dem Server; Reisespeicher nur anhängen; tägliche Sicherung; neue Software erst nach Prüfung, Rückfall
  auf den letzten guten Stand; Veröffentlichen höchstens 2 Minuten als Ziel); Bildunterschriften nur das Sichtbare.
- AC-5: Vorhandene Bilder unverändert.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | Eintrag betrieb, Link zur Anleitung in `unterseite` |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der Unterseite, zwei Korrekturen |
| engine/tests/test_funktionsseiten_711.py | MODIFY | Gruppe vollständig, Link zur Anleitung |
| docs/design.md | MODIFY | Feld `doku` in der Form |

## Test Plan

- RED: `test_unterseiten_konto` (ganze Gruppe) und `test_link_zur_anleitung` → rot; dann grün.
- Danach `test_funktionsseiten_711.py`, `test_texte.py`, `test_englisch*.py`, `test_infoseite*.py`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine — Inhalt in vorhandener Form, ein optionaler Link; folgt ADR-0002, ADR-0003, ADR-0006.

## Definition of Done

- [ ] Tests rot, dann grün; CI grün; Vorspulen auf `main`
- [ ] Auf der Instanz per `curl` geprüft

## Changelog

- 2026-11-26: Initial.
