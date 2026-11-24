---
entity_id: vormerkung-frist-649
type: bugfix
created: 2026-11-24
updated: 2026-11-24
status: draft
workflow: fix-649-vormerkung-frist
version: "1.0"
tags: [bilder, loeschen, waechter, kontendatenbank, vormerkung]
---

# Vormerkung einer Fotolöschung erst nach einer Frist verwerfen (#649, Nachtrag zu #582, Befund F006)

## Approval

- [ ] Approved

## Purpose

Der tägliche Wächter verwirft heute jede unbestätigte Vormerkung einer Fotolöschung, deren Eintrag noch nicht entfernt ist, ohne auf ihr Alter zu achten. Läuft er genau zwischen Vormerkung und Festschreiben des Löschvorgangs und scheitert danach auch das Bestätigen, fehlt die Zeile, und das Leeren der Bildablage wird nie nachgeholt. Diese Spec führt einen Zeitpunkt der Vormerkung und eine Frist von einer Stunde ein: Der Wächter verwirft nur Vormerkungen, die älter als die Frist sind.

## Source

- **Kontext und Analyse (verbindlich):** `docs/context/fix-649-vormerkung-frist.md`, Abschnitte „Analysis“ und „Technical Approach“.
- **Übergeordnete Spec:** `docs/specs/oberflaeche/bilder-582-eigene-fotos.md` (echtes Löschen, `bild_entfernen`, Löschprotokoll `bild_loeschungen`).
- **Files:**
  - `engine/konten.py`: Tabelle `bild_loeschungen`, `BILD_LOESCHUNG_SPALTEN`, `db()`, `bild_loeschung_vormerken`, `bild_loeschung_verwerfen`, `bild_loeschungen()`
  - `engine/waechter.py`: `_bildloeschung_nachholen`
  - `engine/schreiben.py`: unverändert (Pfad vormerken, Vorgang, `bild_endgueltig_entfernen`)

## Dependencies

| Abhängigkeit | Art | Bedeutung |
|---|---|---|
| `konten.db()` | intern | öffnet die Kontendatenbank und ergänzt fehlende Spalten beim Öffnen |
| `konten._jetzt()` | intern | Zeit in REAL-Sekunden (UTC); Tests stellen sie mit `monkeypatch` vor |
| `bilder.entfernt` | intern | prüft, ob der Eintrag im neuesten Stand schon entfernt ist |
| `waechter.bildloeschungen_nachholen` | Downstream | täglicher Lauf `waechter.py loeschen` |
| Schreibweg `schreiben.py` | Downstream | ruft `bild_loeschung_verwerfen` ohne Frist; Signatur bleibt kompatibel |
| #582 (Bilder Stufe 2) | Voraussetzung | Tabelle, Vormerken, Bestätigen, Nachholen sind auf `main` |
| Instanzen | Betrieb | keine Änderung an Meldungstexten, Umgebungswerten oder Schnittstellen |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/konten.py | MODIFY | Spalte `vorgemerkt`, Konstante `BILD_VORMERKUNG_FRIST`, Zeitpunkt setzen, Altersprüfung im Verwerfen, `bild_loeschungen()` liefert `vorgemerkt` |
| engine/waechter.py | MODIFY | `_bildloeschung_nachholen` verwirft nur mit Frist; Docstring |
| engine/tests/test_bilder_eigen.py | MODIFY | neue Tests, zwei bestehende angepasst |
| docs/betrieb.md | MODIFY | Z. ~114: Frist von einer Stunde ergänzen |
| engine/schreiben.py | keine | bewusst unverändert: sein Verwerfen nach gescheitertem Vorgang gilt der eigenen Vormerkung und braucht keine Frist |

### Estimated Changes

- Files: 4
- LoC: +40/-8
- Risiko: niedrig; betrifft nur unbestätigte Zeilen des Foto-Löschprotokolls

## Implementation Details

1. **Spalte:** `vorgemerkt REAL NOT NULL DEFAULT 0` in `bild_loeschungen`, im Schema und in `BILD_LOESCHUNG_SPALTEN`. `db()` ergänzt sie beim Öffnen älterer Datenbanken automatisch (Formatwechsel ohne Handschritt, #250; `neu.py nachziehen` ist nicht nötig, da Kontendatenbank und keine Reisedaten). Bestehende Zeilen erhalten 0 und gelten damit als sehr alt; sie stammen aus der Zeit vor dem Update und werden wie bisher verworfen.
2. **Konstante:** `BILD_VORMERKUNG_FRIST = 3600` (Sekunden) in `engine/konten.py`, weit über der Zeitgrenze eines Schreibvorgangs (Sekunden).
3. **Vormerken:** `bild_loeschung_vormerken` schreibt `_jetzt()` beim INSERT und frischt den Zeitpunkt auf, wenn schon eine unbestätigte Zeile besteht. Sonst erbte eine neue Vormerkung das Alter einer liegengebliebenen alten und würde trotz Frist sofort verworfen. Bestätigte Zeilen bleiben unberührt, der Rückgabewert bleibt wie bisher.
4. **Verwerfen:** `bild_loeschung_verwerfen(reise, bid, nur_aelter_als=None)`. Ohne Angabe wie bisher (nur unbestätigte Zeile). Mit Angabe löscht der DELETE nur Zeilen mit `vorgemerkt <= _jetzt() - nur_aelter_als`; die Altersprüfung steckt in der SQL-Bedingung, damit eine zwischen Lesen und Verwerfen aufgefrischte Vormerkung nicht verloren geht.
5. **Lesen:** `bild_loeschungen()` liefert zusätzlich `vorgemerkt`.
6. **Wächter:** `_bildloeschung_nachholen` verwirft eine unbestätigte Zeile, deren Eintrag nicht entfernt ist, nur mit `nur_aelter_als=konten.BILD_VORMERKUNG_FRIST`. Eine junge Vormerkung bleibt unangetastet und wird im nächsten Lauf neu bewertet. Ist der Eintrag im neuesten Stand schon entfernt, wird die Zeile weiter sofort bestätigt, auch wenn sie jung ist.
7. **Doku:** `docs/betrieb.md` Z. ~114: „eine Vormerkung ohne festgeschriebenen Vorgang verwirft der Wächter nach einer Stunde“.

Verworfene Alternativen: Frist über das Tagesdatum `datum` (zu grob, der Wächter läuft täglich); Prüfung nur im Wächter ohne SQL-Bedingung (Wettlauf mit erneuter Vormerkung).

## Test Plan

### Automated Tests (TDD RED)

Alle in `engine/tests/test_bilder_eigen.py`, nur mit erfundenen Daten der Beispielreise.

- [ ] Test 1: GIVEN eine junge unbestätigte Vormerkung, Eintrag nicht entfernt, WHEN der Wächter nachholt, THEN bleibt die Zeile stehen, und `bild_loeschung_bestaetigen` klappt danach normal.
- [ ] Test 2: GIVEN eine liegengebliebene Vormerkung ohne Vorgang und `konten._jetzt` um mehr als `BILD_VORMERKUNG_FRIST` vorgestellt, WHEN der Wächter nachholt, THEN wird die Zeile verworfen (bestehender Test `test_liegengebliebene_vormerkung_ohne_vorgang_schadet_nicht`, angepasst).
- [ ] Test 3: GIVEN eine alte unbestätigte Zeile, WHEN erneut vorgemerkt wird, THEN steht `vorgemerkt` auf dem neuen `_jetzt()`, und ein Verwerfen mit Frist lässt die Zeile stehen.
- [ ] Test 4: GIVEN eine Zeile, WHEN `bild_loeschung_verwerfen` ohne `nur_aelter_als` aufgerufen wird, THEN wird sie wie bisher sofort verworfen (Schreibweg).
- [ ] Test 5: GIVEN eine bestätigte Zeile, WHEN mit Frist verworfen wird, THEN bleibt sie in jedem Alter erhalten.
- [ ] Test 6: GIVEN eine Kontendatenbank ohne die Spalte `vorgemerkt`, WHEN sie geöffnet wird, THEN ist die Spalte ergänzt und alte Zeilen haben `vorgemerkt` 0 (bestehender Formatwechsel-Test `test_alte_protokollzeilen_ohne_neue_spalten_gelten_weiter`, angepasst); der Wächter verwirft sie wie alt.
- [ ] Test 7: GIVEN eine junge unbestätigte Zeile, deren Eintrag im neuesten Stand schon entfernt ist, WHEN der Wächter nachholt, THEN wird sie sofort bestätigt.

Zusätzlich muss die gesamte Suite `engine/.venv/bin/python -m pytest -q engine/tests` grün bleiben (inklusive `test_betrieb.py`, `test_protokolle_ohne_pfade.py`).

## Acceptance Criteria

- **AC-1:** Given eine unbestätigte Vormerkung, die jünger als `BILD_VORMERKUNG_FRIST` ist und deren Eintrag nicht entfernt ist / When der Wächter läuft / Then bleibt die Zeile bestehen und ein späteres Bestätigen gelingt.
- **AC-2:** Given eine unbestätigte Vormerkung, die älter als `BILD_VORMERKUNG_FRIST` ist und deren Eintrag nicht entfernt ist / When der Wächter läuft / Then wird sie verworfen.
- **AC-3:** Given eine liegengebliebene unbestätigte Zeile / When dieselbe Löschung erneut vorgemerkt wird / Then wird `vorgemerkt` auf die aktuelle Zeit gesetzt und der Wächter verwirft sie innerhalb der Frist nicht.
- **AC-4:** Given `bild_loeschung_verwerfen` ohne `nur_aelter_als` / When aufgerufen / Then verhält es sich unverändert; `schreiben.py` braucht keine Änderung.
- **AC-5:** Given eine Kontendatenbank von vor dem Update / When sie geöffnet wird / Then ergänzt `db()` die Spalte `vorgemerkt` mit Standard 0 ohne Handschritt, und alte Zeilen gelten als älter als die Frist.
- **AC-6:** Given eine bestätigte Zeile / When der Wächter oder `bild_loeschung_verwerfen` mit Frist läuft / Then bleibt sie unberührt.
- **AC-7:** Given eine junge Zeile, deren Eintrag schon entfernt ist / When der Wächter läuft / Then wird sie wie bisher sofort bestätigt.
- **AC-8:** Given `bild_loeschungen()` / When aufgerufen / Then enthält jede Zeile das Feld `vorgemerkt`.
- **AC-9:** Given `docs/betrieb.md` / When gelesen / Then nennt sie die Frist von einer Stunde, und die gesamte Testsuite ist grün.

## Definition of Done

- [ ] AC-1 bis AC-9 durch Tests in `engine/tests/test_bilder_eigen.py` belegt
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests` ohne echte Reisen grün (CI: `tests (leer)`, `tests (instanz)`, `gitleaks`)
- [ ] `docs/betrieb.md` nennt die Frist von einer Stunde
- [ ] Kein Handschritt in Instanzen nötig (Spalte wird beim Öffnen der Kontendatenbank ergänzt)
- [ ] Issue #649 nach Auslieferung auf `main` geschlossen

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Fehlerbehebung innerhalb der bestehenden Löschlogik von #582; keine neue Grundform, kein neues Format der Reisedaten, keine Abweichung vom Kern (ADR-0001). Die Frist ist eine Modulkonstante, die Spalte in der Kontendatenbank wird beim Öffnen automatisch ergänzt.

## Changelog

- 2026-11-24: Initial spec created
