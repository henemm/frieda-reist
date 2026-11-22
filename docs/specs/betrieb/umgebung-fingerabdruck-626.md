---
entity_id: umgebung-fingerabdruck-626
type: bugfix
created: 2026-11-22
updated: 2026-11-22
status: draft
version: "1.0"
tags: [betrieb, veroeffentlichen, rot-datei, playwright]
workflow: fix-626-umgebung-fingerabdruck
---

# Umgebungs-Fingerabdruck beim Veröffentlichen stabil (#626)

Grundlage: `docs/context/fix-626-umgebung-fingerabdruck.md` (Kontext, Analyse, Ursache nachgestellt). Vorgänger: #203 (Fingerabdruck der Prüfumgebung in der Rot-Datei), #628 (Tests setzen `VF_NPM` auf eine nicht vorhandene Datei).

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Reiner Betriebsfehler im Veröffentlichungsskript. Prüfung gegen ADR-0001 (Kern): keine neue Grundform, kein Merkmal, nichts Reise- oder Instanzspezifisches in der Engine, keine Änderung an Seite, Konnektor oder Reisedaten. Es ändert sich nur, welche Eingaben den Fingerabdruck der Prüfumgebung bilden. Keine Produktentscheidung nötig.

## Purpose

Ein gescheitertes Veröffentlichen soll bis zu einem neuen Commit, einer echten Änderung der Prüfumgebung oder dem Ablauf der Frist als „bekannter roter Stand“ übersprungen werden. Heute rollt es bei jedem Takt erneut aus, weil sich der Fingerabdruck der Umgebung zwischen dem Schreiben und dem Prüfen der Rot-Datei von selbst ändert. Die Spec macht den Fingerabdruck unabhängig von der Reihenfolge im Lauf.

## Problem

Test F002 (`test_f002_rueckfall_mit_rot_datei_kein_erneuter_rollout_und_kein_nachziehen` in `engine/tests/test_software_weg_454.py`) war lokal rot: Der zweite Lauf meldete `Known red state …, checking again (environment changed)` und rollte den roten Commit erneut aus. In CI und im Standardlauf war der Test grün, weil die Tests seit #628 `VF_NPM` auf eine nicht vorhandene Datei setzen; der Fehler war verdeckt, nicht behoben. Mit einer npm-Attrappe ließ er sich lokal nachstellen.

Auf einer Instanz mit npm ist es ein echter Betriebsfehler: Ein gescheiterter Deploy der Dienste wird jeden Takt neu ausgerollt, statt zu warten.

## Ursache

`umgebung_stand` in `betrieb/veroeffentlichen.sh` (Zeile 374) nimmt die Playwright-Version nur auf, wenn `PLAYWRIGHT_MODUL` gesetzt ist (Zeile 381). Diese Variable setzt und exportiert `abhaengigkeiten_playwright` erst mitten im Lauf (Zeile 498).

- **Lauf 1:** `abhaengigkeiten_playwright` (Aufruf Zeile 783) läuft, der Deploy der Dienste scheitert, danach schreibt `rot_schreiben` (Zeile 787, Fingerabdruck in Zeile 370) die Rot-Datei, also mit Playwright-Version.
- **Lauf 2:** `rot_erneut_pruefen` (Aufruf Zeile 729, Vergleich Zeile 390) läuft vor `abhaengigkeiten_playwright`; die Variable ist leer, der Fingerabdruck hat keine Playwright-Version, er weicht ab, es folgt `environment changed` und ein neuer Rollout, bei jedem Takt.

Dasselbe gilt für Rot-Dateien der Art `reise` (`rot_schreiben` in Zeile 961 steht ebenfalls nach `abhaengigkeiten_playwright`). Bei `software_pruefen` (Zeile 657) läuft `abhaengigkeiten_playwright` in einer Unterschale; die Variable bleibt im Elternprozess leer, dort war der Fingerabdruck bisher nur zufällig stabil.

## Lösung

Der Fingerabdruck hängt nur vom Zustand auf der Platte ab, nicht von der Reihenfolge im Lauf.

1. Beim Skriptstart, nach dem Laden der Einstellungen und vor jedem Aufruf von `abhaengigkeiten_playwright`, merkt das Skript `pw_modul_einstellung="${PLAYWRIGHT_MODUL:-}"`. Das ist der Wert, den die Instanz eingestellt hat (oder leer).
2. `umgebung_stand` nimmt als Modul `${pw_modul_einstellung:-$FR_DIENST/playwright/node_modules/playwright/index.mjs}` (Rückfall auf die Kopie der Instanz, Muster wie `betrieb/deploy.sh` und `engine/konnektor.py`) und liest daneben `package.json` (erste Zeile mit `"version"`). Fehlt die Datei, bleibt der Teil leer wie bisher; der Lauf bricht nicht ab.
3. `VF_UMGEBUNG` behält Vorrang (Zeile 375, Tests zu #203 bleiben unberührt).
4. Der Kopfkommentar von `umgebung_stand` nennt, woher die Playwright-Version kommt (Einstellung beim Start, sonst Kopie der Instanz) und dass der Wert bewusst nicht von der Reihenfolge im Lauf abhängt.

Das gilt für Rot-Dateien beider Arten (Software-Deploy und `reise`), weil beide dieselbe Funktion nutzen.

Eine echte Neuinstallation von Playwright mit anderer Version unter `<FR_DIENST>/playwright` ändert `package.json` und zählt weiterhin als Umgebungsänderung.

## Source

- **File:** `betrieb/veroeffentlichen.sh`
- **Identifier:** `umgebung_stand`, `rot_schreiben`, `rot_erneut_pruefen`, `abhaengigkeiten_playwright`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `FR_DIENST` | Einstellung | Ort der Rot-Datei und der Playwright-Kopie `<FR_DIENST>/playwright`; ist vor `umgebung_stand` immer gesetzt |
| `PLAYWRIGHT_MODUL` | Einstellung der Instanz | Wert beim Skriptstart wird gemerkt, Rückfall auf die Kopie der Instanz |
| `<FR_DIENST>/playwright/node_modules/playwright/package.json` | Datei | Quelle der Playwright-Version im Fingerabdruck |
| `VF_UMGEBUNG` | Testvariable (#203) | überschreibt den Fingerabdruck, behält Vorrang |
| `VF_NPM` | Testvariable (#628) | npm-Pfad; Standard in Tests: nicht vorhanden; der Regressionstest setzt gezielt eine Attrappe |
| `betrieb/deploy.sh`, `engine/konnektor.py` | Muster | gleicher Rückfall ohne `PLAYWRIGHT_MODUL` |
| `PLAYWRIGHT_ATTRAPPEN` in `engine/tests/conftest.py` | Wächter (#628) | Tests mit Playwright-Attrappe unter `tmp_path` stehen dort oder räumen sie selbst weg (hier: Fixture `mit_npm`) |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/veroeffentlichen.sh` | MODIFY | `pw_modul_einstellung` beim Start merken, `umgebung_stand` auf Einstellung oder Kopie der Instanz umstellen, Kopfkommentar ergänzen |
| `engine/tests/test_software_weg_454.py` (Fixture `sw`, neben F002) | MODIFY | Regressionstests (siehe Test Plan) |

Unverändert: `betrieb/deploy.sh`, `engine/konnektor.py`, Fixture `sw` (bleibt bei `VF_NPM` = nicht vorhanden), Engine, Seite, Gate-Konfiguration.

### Estimated Changes

- Files: 2
- LoC: +150/-3 (überwiegend Tests)

## Implementation Details

Eine Zeile am Skriptanfang (nach den Einstellungen) und eine geänderte Zeile in `umgebung_stand`; der Rest ist Kommentar und Test. Kein neuer Zustand auf der Platte, kein neues Feld in der Rot-Datei. Die Umstellung der Funktion ist schreibend wie lesend dieselbe (`rot_schreiben` und `rot_erneut_pruefen` rufen beide `umgebung_stand`), daher stimmen beide Seiten des Vergleichs in jedem Lauf überein, solange auf der Platte nichts geändert wurde.

## Test Plan

### Automated Tests (TDD RED)

- [ ] Test 1 (Regression, Software): GIVEN eine npm-Attrappe (`VF_NPM`), die `node_modules/playwright` mit `package.json` unter `<FR_DIENST>/playwright` anlegt, kein `VF_UMGEBUNG` gesetzt, und der Deploy der Dienste scheitert in Lauf 1 / WHEN Lauf 2 mit demselben Commit läuft / THEN meldet er `Known red state … skipped`, nicht `environment changed`, und es gibt genau einen `--dienste`-Aufruf insgesamt.
- [ ] Test 2 (Reise): GIVEN dieselbe Attrappe und eine Rot-Datei der Art `reise` / WHEN das Veröffentlichen erneut läuft, ohne dass sich Umgebung, Commit oder Frist geändert haben / THEN wird der rote Stand übersprungen (kein erneuter Lauf der Reise).
- [ ] Test 3 (echte Änderung zählt): GIVEN eine Rot-Datei aus Lauf 1 / WHEN vor Lauf 2 die Version in `<FR_DIENST>/playwright/node_modules/playwright/package.json` geändert wird / THEN meldet Lauf 2 `environment changed` und prüft erneut.
- [ ] Test 4 (VF_UMGEBUNG vorrangig): GIVEN `VF_UMGEBUNG` gesetzt und eine geänderte Playwright-Version / WHEN der Fingerabdruck berechnet wird / THEN hängt er nur von `VF_UMGEBUNG` ab (bestehender Test zu #203 bleibt grün).
- [ ] Test 5 (fehlende Datei): GIVEN weder `PLAYWRIGHT_MODUL` noch eine Kopie unter `<FR_DIENST>/playwright` / WHEN der Fingerabdruck berechnet wird / THEN bricht der Lauf nicht ab und der Playwright-Teil ist leer wie bisher.
- [ ] Wächter aus #628: Die Fixture `mit_npm` entfernt die Attrappe unter `<FR_DIENST>/playwright` nach dem Test; kein Eintrag in `PLAYWRIGHT_ATTRAPPEN` (die Liste darf laut Kommentar nur kürzer werden).
- [ ] Test 6 (AC-7): Der Kopfkommentar von `umgebung_stand` nennt #626, die Reihenfolge im Lauf und `<FR_DIENST>/playwright`.

Vor der Änderung sind Test 1, Test 2 und Test 6 rot, Test 3 bis 5 dienen als Wächter. Test 2 stellt den Vergleich für die Art `reise` nach, indem die Rot-Datei nach Lauf 1 auf den nächsten Commit zeigt: Im normalen Ablauf trägt eine Rot-Datei der Art `reise` den laufenden Commit, `rot_erneut_pruefen` wird für sie erst mit einem gleichen neuen Commit erreicht.

## Acceptance Criteria

- **AC-1:** Given ein gescheiterter Deploy der Dienste (Lauf 1) und unveränderte Umgebung / When Lauf 2 ohne `VF_UMGEBUNG` mit npm-Attrappe läuft / Then steht im Protokoll `Known red state … skipped` und es gibt insgesamt genau einen `--dienste`-Aufruf (Test 1).
- **AC-2:** Given eine Rot-Datei der Art `reise` und unveränderte Umgebung / When erneut veröffentlicht wird / Then wird der rote Stand übersprungen (Test 2).
- **AC-3:** Given eine geänderte Playwright-Version unter `<FR_DIENST>/playwright` / When der rote Stand geprüft wird / Then meldet das Skript `environment changed` (Test 3).
- **AC-4:** Given `VF_UMGEBUNG` gesetzt / When der Fingerabdruck berechnet wird / Then gilt nur dieser Wert (Test 4).
- **AC-5:** Given keine Playwright-Kopie und kein `PLAYWRIGHT_MODUL` / When der Fingerabdruck berechnet wird / Then bricht nichts ab (Test 5).
- **AC-6:** Given der Stand der Änderung / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then sind alle Tests grün, auch F002 ohne Verdecken durch `VF_NPM`, und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) sind grün.
- **AC-7:** Given der Kopfkommentar von `umgebung_stand` / When er gelesen wird / Then nennt er die Quelle der Playwright-Version und dass sie nicht von der Reihenfolge im Lauf abhängt.

## Nicht-Ziele

- `VF_UMGEBUNG` im Fixture `sw` fest setzen (Vorschlag im Issue): bewusst nicht, es verdeckt den Betriebsfehler nur weiter. `VF_NPM` = nicht vorhanden bleibt im Fixture (#628); nur der Regressionstest setzt gezielt eine Attrappe.
- Keine Änderung an `deploy.sh`, Konnektor, Frist `FR_ROT_NEU_PRUEFEN_MINUTEN` oder Format der Rot-Datei.
- Keine Änderung der Gate-Konfiguration.

## Risks

- **Einmalige Neuprüfung nach dem Wechsel:** Bestehende Rot-Dateien tragen den alten Fingerabdruck. Einmal erscheint `environment changed` und der Stand wird erneut geprüft, danach ist der Wert stabil. Unkritisch, ein einmaliges Neuprüfen bei Unklarheit ist gewollt; ein Handschritt ist nicht nötig.
- **Instanz ohne npm und ohne Playwright-Kopie:** Der Teil bleibt leer, Verhalten wie bisher.
- **Test mit Attrappe legt `node_modules/playwright` unter `tmp_path` an:** die Fixture `mit_npm` räumt sie nach dem Test weg, der Wächter aus #628 bleibt unverändert.

## Definition of Done

- [ ] AC-1 bis AC-7 durch Tests und Prüfung belegt
- [ ] Auslieferung nur über den normalen Weg (Pull Request, grüne Pflichtprüfungen, Vorspulen)
- [ ] Issue #626 erst nach grünem Lauf auf `main` schließen

## Changelog

- 2026-11-22: Initiale Spec (#626)
- 2026-11-22: TDD RED: Attrappe wird aufgeräumt statt in `PLAYWRIGHT_ATTRAPPEN` eingetragen; Test 6 für AC-7; Nachstellung für Art `reise` erklärt
