---
entity_id: playwright-tmp-tests
type: bugfix
created: 2026-11-19
updated: 2026-11-19
status: draft
workflow: fix-628-playwright-tmp
---

# Tests installieren keine echte Playwright-Kopie (#628)

Grundlage: `docs/context/fix-628-playwright-tmp.md` (Ursache, Nachprüfung, Analyse).

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es ändern sich nur die Umgebung der Tests und ein neuer Nachweistest. Seite, Vorlage, Engine und Betriebsskripte bleiben unverändert, der Kern aus ADR-0001 ist nicht berührt.

## Purpose

Ein Testlauf legt je Test der Software-Weg-Tests eine vollständige Playwright-Installation (rund 930 MB, Browser und Module) im temporären Ordner ab. Ein paralleler Lauf füllt so bis zu 38 GB und die Platte des Servers; andere Läufe scheitern dann mit „kein Platz mehr“. Die Tests brauchen diese Installation nicht. Sie sollen nie echte Browser installieren, und ein Wächter soll verhindern, dass dieser Fehler über einen künftigen Weg zurückkehrt.

## Ursache

1. `betrieb/veroeffentlichen.sh` ruft im Software-Weg seit #618 bedingungslos `abhaengigkeiten_playwright` auf (Browser für das Seitenbild des Konnektors). Die Funktion nimmt `npm="${VF_NPM:-npm}"`; ist npm im PATH, laufen `npm ci` und `playwright install chromium webkit` in den Dienstordner.
2. Die Fixture `sw` in `engine/tests/test_software_weg_454.py` baut ihre Umgebung selbst (`env = {**SAUBER, …}`), `SAUBER` entfernt beim Import alle `VF_`-Werte. Ein `VF_NPM` aus `conftest.py` käme dort nicht an. Das Software-Repo der Fixture verlinkt `engine/` auf die echte Engine, daher liegt die Sperrdatei der Playwright-Module vor und die Installation läuft wirklich.
3. Die Fixture `alt` (`lauf_alt`, `lauf_neu`) baut mit `_software_repo` ebenfalls ein Repo mit Verweis auf die echte Engine und installierte daher auch; sie setzt `VF_NPM` jetzt ebenso (in der Umsetzung vom Wächter gefunden). Die Fixture `vf` baut ohne Sperrdatei und ist unkritisch.
4. Die CI hat npm ebenfalls, installierte also auch dort je `sw`-Test; die Änderung spart dort Zeit.

## Source

- **File:** `engine/tests/test_software_weg_454.py`, `engine/tests/conftest.py`, `engine/tests/test_playwright_tmp_628.py`
- **Identifier:** Fixture `sw`, Fixture `instanz_leeren`, neuer autouse-Wächter in `conftest.py`, neue Testdatei `test_playwright_tmp_628.py`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/veroeffentlichen.sh` (`abhaengigkeiten_playwright`) | Betriebsskript | liest `VF_NPM`; ohne nutzbares npm meldet es „npm missing“ und gibt 0 zurück; bleibt unverändert |
| Testhaken `VF_PIP`, `VF_NPM`, `VF_DEPLOY`, `VF_PRUEFEN` | Muster | bestehendes Vorgehen für externe Programme in Betriebsskripten |
| `engine/tests/conftest.py` (`instanz_leeren`) | Test | legt die Umgebung jedes Tests zentral fest, entfernt bisher alle `VF_`-Werte |
| `engine/tests/test_betrieb.py` (Test mit npm-Attrappe, `VF_NPM` selbst gesetzt) | Test | überschreibt den Vorgabewert, bleibt unverändert und grün |
| Browsertests (`PLAYWRIGHT_MODUL`, `PLAYWRIGHT_BROWSERS_PATH`, `playwright_pfad.py`) | Test | nutzen `VF_NPM` nicht, bleiben unberührt; der Server-Lauf setzt `PLAYWRIGHT_*` vor pytest |
| pytest-Fixture `tmp_path` | extern | Ort, unter dem der Wächter sucht; alte Läufe räumt pytest selbst (behält 3) |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/tests/test_software_weg_454.py` | MODIFY | Fixtures `sw` und `alt`: `VF_NPM` auf eine nicht vorhandene Datei setzen, wie die übrigen `VF_`-Haken |
| `engine/tests/conftest.py` | MODIFY | `instanz_leeren` setzt `VF_NPM` ebenso (für Tests, die `os.environ` weiterreichen); autouse-Wächter prüft nach jedem Test, ob unter `tmp_path` eine Playwright-Installation liegt, und lässt den Test sonst scheitern |
| `engine/tests/test_playwright_tmp_628.py` | CREATE | Nachweistests (siehe Test Plan) |

Unverändert: `betrieb/veroeffentlichen.sh` (der Server braucht die Installation, #618), `engine/tests/test_betrieb.py`, Engine, Vorlage, `.github/workflows/tests.yml`.

### Estimated Changes

- Files: 3
- LoC: +60/-0

### Out of Scope

- Änderung des Betriebsskripts oder des Verhaltens auf dem Server.
- Aufräumen alter Reste in den temporären Ordnern früherer Läufe (macht pytest selbst).

## Implementation Details

1. **Quelle behoben.** `sw` setzt `VF_NPM` auf einen Pfad, den es nicht gibt. `abhaengigkeiten_playwright` meldet „npm missing“ und kehrt mit 0 zurück; das Verhalten der Tests bleibt sonst unverändert.
2. **Zentral.** `instanz_leeren` setzt `VF_NPM` auf eine nicht vorhandene Datei, damit auch Aufrufe mit weitergereichtem `os.environ` nie ein echtes npm erreichen. Tests, die `VF_NPM` selbst setzen (Attrappe), überschreiben den Wert.
3. **Wächter.** Ein autouse-Fixture in `conftest.py` prüft nach jedem Test per `glob`, ob unter `tmp_path` ein Ordner `playwright/node_modules` bis Tiefe 3 liegt. Wenn ja, scheitert der Test mit dem Fundort in der Meldung. Es wird keine Größe gemessen.
4. **Abwägung gegen die Vorschläge im Issue.**
   - *Größengrenze je tmp-Ordner (etwa unter 50 MB):* verworfen. Ein `du` über jeden der rund 2000 Tests kostet spürbar Zeit und trifft auch legitime große Testdaten, also Fehlalarme. Die Existenzprüfung trifft genau den beobachteten Fehler und kostet fast nichts. Nachteil: ein anderer Platzfresser wird nicht erkannt; dafür ist dieser Wächter nicht gedacht.
   - *Gemeinsamer Browser-Cache für alle Tests:* verworfen. Die Tests brauchen keine Installation, nur den Weg bis „npm missing“. Ein Link auf einen Cache würde den Installationsweg (`npm ci`, Prüfungen) weiter durchlaufen, wäre langsamer und hinge von einem gemeinsamen Zustand zwischen parallelen Läufen ab.
5. Die Wirkung der Wächter-Prüfung selbst wird in der neuen Datei mit einer untergeschobenen Attrappe belegt, ohne etwas Echtes zu installieren.

## Test Plan

### Automated Tests (TDD RED)

Alle in `engine/tests/test_playwright_tmp_628.py`.

- [ ] Test 1 (Software-Weg legt nichts an): GIVEN die Fixture `sw` mit Sperrdatei der Playwright-Module und npm im PATH / WHEN der Software-Weg einmal läuft / THEN gibt es unter `FR_DIENST` keinen Ordner `playwright/node_modules` und die Ausgabe enthält „npm missing“; vor der Änderung rot.
- [ ] Test 2 (Zentrale Vorgabe): GIVEN ein beliebiger Test nach `instanz_leeren` / WHEN `os.environ["VF_NPM"]` gelesen wird / THEN zeigt er auf eine nicht vorhandene Datei; vor der Änderung rot.
- [ ] Test 3 (Wächter schlägt an): GIVEN eine untergeschobene Attrappe `playwright/node_modules` unter `tmp_path` / WHEN die Wächter-Prüfung aufgerufen wird / THEN meldet sie einen Fehler mit dem Fundort; liegt die Attrappe auf Tiefe 4 oder tiefer, meldet sie keinen Fehler (bewusste Grenze, siehe Risks).
- [ ] Test 4 (Wächter schweigt): GIVEN ein `tmp_path` ohne Playwright-Ordner, aber mit ähnlich benannten Ordnern (`playwright` ohne `node_modules`) / WHEN die Wächter-Prüfung läuft / THEN meldet sie keinen Fehler.
- [ ] Test 5 (Attrappe bleibt wirksam): GIVEN der Test in `test_betrieb.py` mit eigener npm-Attrappe / WHEN er läuft / THEN ist er unverändert grün, weil seine eigene `VF_NPM`-Einstellung den Vorgabewert überschreibt.

### Manuelle Prüfung

- Prüfung 6: Ein Lauf der Software-Weg-Tests (`test_software_weg_454.py`) mit `-n 3`; danach der Platzverbrauch des temporären Ordners dieses Laufs: deutlich unter 1 GB statt Vielfachem von 930 MB.
- Prüfung 7: Vergleich mit `main` zeigt keine Änderung an `betrieb/veroeffentlichen.sh`.

## Acceptance Criteria

- **AC-1:** Given die Fixture `sw` und npm im PATH / When der Software-Weg im Test läuft / Then liegt unter dem Dienstordner kein `playwright/node_modules`, und die Ausgabe zeigt „npm missing“ (Test 1).
  Test: `engine/tests/test_playwright_tmp_628.py::test_sw_legt_keine_playwright_kopie_an`
- **AC-2:** Given jeder Test nach `instanz_leeren` / When `VF_NPM` gelesen wird / Then verweist es auf eine nicht vorhandene Datei (Test 2).
  Test: `engine/tests/test_playwright_tmp_628.py::test_instanz_leeren_setzt_vf_npm`
- **AC-3:** Given eine untergeschobene Playwright-Installation bis Tiefe 3 unter `tmp_path` / When der Wächter läuft / Then scheitert der Test mit Fundort; ohne solche Installation bleibt er still (Test 3 und 4).
  Test: `engine/tests/test_playwright_tmp_628.py::test_waechter_erkennt_installation` und `::test_waechter_schweigt_ohne_installation`
- **AC-4:** Given der Test mit npm-Attrappe in `test_betrieb.py` / When er läuft / Then ist er unverändert grün (Test 5).
  Test: `engine/tests/test_betrieb.py` (bestehender Test mit npm-Attrappe, `VF_NPM` selbst gesetzt)
- **AC-5:** Given ein Lauf der Software-Weg-Tests mit `-n 3` / When der Platzverbrauch des temporären Ordners nach dem Lauf gemessen wird / Then liegt er deutlich unter 1 GB (Prüfung 6).
  Test: manuell (Messung im Nachweis)
- **AC-6:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then ist `betrieb/veroeffentlichen.sh` unverändert (Prüfung 7), und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) sind grün.
  Test: manuell (Vergleich mit `main`) und CI

## Risks

- **Wächter zu eng:** Er sucht nur `playwright/node_modules` bis Tiefe 3. Legt ein künftiger Weg die Installation tiefer oder unter anderem Namen ab, wird das nicht erkannt. Akzeptiert: der beobachtete Fehler ist abgedeckt, die Prüfung bleibt billig.
- **Wächter zu breit:** Ein Test, der bewusst eine Playwright-Struktur unter `tmp_path` anlegt, scheitert. Drei bestehende Tests tun das mit einer Attrappe von wenigen Bytes (zwei in `test_betrieb.py`, einer in `test_seite_ansehen.py`); sie stehen in der Ausnahmeliste `PLAYWRIGHT_ATTRAPPEN` in `conftest.py`, die nur kürzer werden darf. Verworfen: den Wächter erst bei `playwright-core` anschlagen zu lassen, weil er dann eine Installation ohne dieses Modul übersähe und Test 3 seine Wirkung nicht mehr an der einfachen Attrappe zeigen könnte. Für Test 3 liegt die Attrappe außerhalb von `tmp_path`.
- **Test erwartet echtes npm:** Keiner gefunden; der Test in `test_betrieb.py` setzt eine eigene Attrappe.

## Definition of Done

- [ ] AC-1 bis AC-4 durch Test 1 bis 5 belegt
- [ ] AC-5 und AC-6 durch Messung, Vergleich mit `main` und grüne Pflichtprüfungen belegt
- [ ] Auslieferung nur über den normalen Weg (Pull Request, grüne Pflichtprüfungen, Vorspulen)
- [ ] Issue #628 erst nach grünem Lauf auf `main` schließen

## Changelog

- 2026-11-19: Initiale Spec (#628)
- 2026-11-19: Umsetzung: zweite Quelle Fixture `alt`, Ausnahmeliste für drei Attrappen-Tests (#628)
