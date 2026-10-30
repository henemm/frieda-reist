---
entity_id: tagesseite-plan
type: module
created: 2026-10-30
updated: 2026-10-30
status: draft
version: "1.0"
tags: [vorlage, tagesseite, plan, ortsseite]
---

# Tagesseite: Nummer und Datum aus dem gewählten Plan (#144)

## Approval

- [ ] Approved

## Purpose

Ist ein Plan vollständig gewählt (Status fest), soll die Tagesseite Nummer und Datum aus diesem Plan zeigen, wie die Übersicht. Bisher nimmt sie bei direktem Aufruf den ersten Plan der Liste, der den Tag enthält. Das kann ein verworfener Plan mit einer zusätzlichen Nacht sein: Die Seite zeigt dann „Tag N+1“ und ein um einen Tag späteres Datum, und zwei Tagesseiten tragen dieselbe Nummer und dasselbe Datum. Das kann zu Fehlbuchungen führen.

## Source

- **File:** `engine/vorlage.html`
- **Identifier:** `ansichtTag`, `ansichtOrt`, `PLAN_FEST`, `PLAN_ZULETZT`, `planFest`, `planZu`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `R.plaene`, `R.tage`, `R.weitere_tage` | Reisemodell (aus `engine/routen.py`, `bauen()`/`plaene()`) | Tage je Plan; `R.tage` ist der aktuelle Plan. Wird nicht geändert |
| `PLAN_FEST` (Z. 889) | Konstante | Erster vollständig gewählter Plan; Karte und Reiseüberblick richten sich schon danach |
| `PLAN_ZULETZT`, `planZu` | Zustand | Zuletzt angesehener Plan; gilt nur in der Vergleichsphase |
| `engine/tests/test_tagesseite.py`, `seiten_tagesseite.mjs` | Test (Playwright) | Ort des Regressionstests |
| `docs/adr/0001-kern.md`, `docs/adr/0003-heimat.md` | ADR | Prüfstelle; keine neue Art, kein neuer Baustein, keine neue Grundform |

## Scope

- **Affected Files:** `engine/vorlage.html`, `engine/tests/test_tagesseite.py`, `engine/tests/seiten_tagesseite.mjs`
- **Estimated Changes:** ca. +10/-3 LoC Vorlage, ca. +50 LoC Test
- **Nicht im Scope:** Python-Seite (`routen.py`, `konnektor.py`, `waechter.py`, `rueckmeldungen.py`); sie rechnen aus `R.tage` bzw. je Plan mit eigener Beschriftung und sind richtig. Der Fall „mehrere Pläne vollständig gewählt“ (`find` nimmt den ersten) bleibt wie er ist. Die Prüfung in einer echten Reise nach dem Veröffentlichen liegt außerhalb dieses Repos (Product Owner, Reise-Repo).

## Implementation Details

1. **`ansichtTag`:** Enthält `PLAN_FEST` den Tag (`PLAN_FEST.tage.some(t => t.id === tid)`), ist `p = PLAN_FEST`. Sonst bleibt die bisherige Suche (`mit.find(PLAN_ZULETZT) || mit[0] || planZu(PLAN_ZULETZT)`). Kopf, Blättern und Zurück-Link folgen aus `p`. Tage, die `PLAN_FEST` nicht enthält (nur in verworfenen Varianten, `R.weitere_tage`), nehmen weiter den bisherigen Weg.
2. **`ansichtOrt`:** Ist ein Plan gewählt, führt „Kommt vor in“ nur Tage von `PLAN_FEST` auf (gleiche Regel wie die Tagesseite, die dann keine Pläne nennt); der Zurück-Link nimmt `PLAN_FEST` statt `PLAN_ZULETZT`. Ohne gewählten Plan bleibt alles gleich. (Entscheidung des Product Owners, siehe Offene Punkte.)
3. Keine Änderung an Daten, Python, Konnektor oder `engine/vendor/`.

## Expected Behavior

- **Input:** Aufruf einer Tagesseite (`#<Tag-ID>`), direkt oder durch Blättern, Lesezeichen, Neuladen.
- **Output:** Mit `PLAN_FEST`, der den Tag enthält: Nummer, Datum und Wochentag aus `PLAN_FEST`, identisch zur Übersicht (`R.tage`); Zurück-Link zeigt auf diesen Plan; Vor/Zurück blättert in dessen Tagen. Ohne `PLAN_FEST`: unverändert (planabhängige Nummer, Planchips).
- **Side effects:** Keine.

## Acceptance Criteria

1. Mit gewähltem Plan und davor stehendem verworfenen Plan mit einer zusätzlichen Nacht zeigt jede Tagesseite des gewählten Plans bei direktem Aufruf dieselbe Nummer und dasselbe Datum wie die Übersicht.
2. Dasselbe gilt, wenn ein weiterer verworfener Plan einen Tag weglässt.
3. Es erscheinen nie zwei Tagesseiten des gewählten Plans mit gleicher Nummer und gleichem Datum.
4. Blättern (← / →) auf einer Tagesseite bleibt im gewählten Plan.
5. Ohne gewählten Plan (Vergleichsphase) bleibt das Verhalten unverändert: planabhängige Nummer, Planchips am Tag, bestehende Tests grün.
6. Tage, die nur in einer verworfenen Variante vorkommen, werden weiter angezeigt.
7. Ortsseite: Mit gewähltem Plan nennt „Kommt vor in“ nur Tage des gewählten Plans, der Zurück-Link führt zu diesem; ohne gewählten Plan unverändert.
8. Regressionstest mit der Beispielreise (Kopie im Test, Demo bleibt unverändert; Zusatzpläne als Beispielwert markiert): ohne Fix rot, mit Fix grün. `engine/.venv/bin/python -m pytest -q engine/tests` ist insgesamt grün.
9. Prüfung der weiteren Stellen ist dokumentiert: Übersicht, Wahlstellen-Titel, Konnektor, Erinnerungen, Fristen, Wächter und Kalenderexport rechnen aus `R.tage` oder je Plan beschriftet (kein Planbezug über `ansichtTag`); eine Suche nach Plan-Zugriffen im Kalenderexport fand keinen.

## Test Plan

- Playwright-Test in `test_tagesseite.py` / `seiten_tagesseite.mjs`: Beispielreise kopieren, Plan A fest, davor ein verworfener Plan mit zusätzlicher Nacht, ein weiterer, der einen Tag weglässt. Jede Tagesseite direkt aufrufen, Nummer und Datum gegen die Übersicht prüfen; Blättern prüfen; Ortsseite prüfen.
- Gegenprobe ohne Fix: Test muss rot sein (TDD RED).
- Vergleichsphase (kein `PLAN_FEST`): vorhandene Tests unverändert grün.

## Known Limitations

- Mehrere vollständig gewählte Pläne: `PLAN_FEST` ist der erste; bestehendes Verhalten, nicht Teil dieses Fehlers.

## Offene Punkte

- Product Owner bestätigt: „Kommt vor in“ zeigt bei gewähltem Plan nur den gewählten Plan (Empfehlung: ja). Sonst entfällt Punkt 2 samt Kriterium 7, die Tagesseite bleibt unberührt.

## Changelog

- 2026-10-30: Erstfassung (#144)
