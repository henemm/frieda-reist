# Adversary Dialog — fix-628-playwright-tmp
Spec: docs/specs/betrieb/playwright-tmp-tests.md
Datum: 2026-11-19 12:31

## Checkliste
- [x] **AC-1:** Given die Fixture `sw` und npm im PATH / When der Software-Weg im Test läuft / Then liegt unter dem Dienstordner kein `playwright/node_modules`, und die Ausgabe zeigt „npm missing“ (Test 1). Test: `engine/tests/test_playwright_tmp_628.py::test_sw_legt_keine_playwright_kopie_an`
- [x] **AC-2:** Given jeder Test nach `instanz_leeren` / When `VF_NPM` gelesen wird / Then verweist es auf eine nicht vorhandene Datei (Test 2). Test: `engine/tests/test_playwright_tmp_628.py::test_instanz_leeren_setzt_vf_npm`
- [x] **AC-3:** Given eine untergeschobene Playwright-Installation bis Tiefe 3 unter `tmp_path` / When der Wächter läuft / Then scheitert der Test mit Fundort; ohne solche Installation bleibt er still (Test 3 und 4). Test: `engine/tests/test_playwright_tmp_628.py::test_waechter_erkennt_installation` und `::test_waechter_schweigt_ohne_installation`
- [x] **AC-4:** Given der Test mit npm-Attrappe in `test_betrieb.py` / When er läuft / Then ist er unverändert grün (Test 5). Test: `engine/tests/test_betrieb.py` (bestehender Test mit npm-Attrappe, `VF_NPM` selbst gesetzt)
- [x] **AC-5:** Given ein Lauf der Software-Weg-Tests mit `-n 3` / When der Platzverbrauch des temporären Ordners nach dem Lauf gemessen wird / Then liegt er deutlich unter 1 GB (Prüfung 6). Test: manuell (Messung im Nachweis)
- [x] **AC-6:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then ist `betrieb/veroeffentlichen.sh` unverändert (Prüfung 7), und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) sind grün. Test: manuell (Vergleich mit `main`) und CI

## Dialog

### Runde 1
**Adversary:** Ich gehe davon aus, dass die Änderung nur die Fixture `sw` trifft und andere Wege zu einem echten npm offen bleiben. Ich suche `veroeffentlichen.sh` und `SAUBER` in engine/tests: `SAUBER` (test_betrieb.py:28) entfernt alle `VF_`-Werte beim Import, also käme `VF_NPM` aus `instanz_leeren` in jedem Test, der `{**SAUBER, ...}` baut, nicht an. Betroffen wären Tests mit Repo, dessen `engine` auf die echte Engine verlinkt (Sperrdatei vorhanden): test_betrieb.py:932, 969, 998, 1254, 1588, 1694, 3438, 3653, 3698, test_nginx.py:553, `_software_repo` (test_software_weg_454.py:286, genutzt von `sw`, `alt`).
Beweis statt Vermutung: Ich habe eine protokollierende npm-Attrappe vorn in den PATH gesetzt und test_betrieb.py, test_nginx.py, test_software_weg_454.py, test_playwright_tmp_628.py, test_speicher_stufe5.py, test_profil.py, test_anstoss_pfad_570.py, test_software_nachziehen.py laufen lassen: 420 passed, Protokoll der Attrappe nicht entstanden, also kein einziger npm-Aufruf. Die übrigen Wege erreichen `abhaengigkeiten_playwright` nicht, oder sie setzen selbst `VF_NPM` (Attrappe). Nur `sw` (test_software_weg_454.py:345) und `alt` (:656) erreichten es und setzen jetzt `VF_NPM` auf eine nicht vorhandene Datei. AC-1: Test `test_sw_legt_keine_playwright_kopie_an` (test_playwright_tmp_628.py:30) fährt zwei Läufe mit npm-Attrappe im PATH und prüft kein Protokoll, kein `playwright/node_modules`, „npm missing“ in der Ausgabe: grün. AC-2: conftest.py:23 setzt `VF_NPM`, Test grün.
**Implementierer:** Bestätigt: Quelle sind `sw` und `alt`, Wächter fand `alt` selbst. Das Betriebsskript bleibt unverändert (veroeffentlichen.sh:633-635 liefert „npm missing“ und 0).

### Runde 2
**Adversary:** Ausnahmeliste `PLAYWRIGHT_ATTRAPPEN` (conftest.py:52-56) und Wächter (conftest.py:60-70). Prüfung: (a) Die drei Namen existieren wirklich (test_betrieb.py:963, 1143; test_seite_ansehen.py:229), keine veraltete Liste. (b) Schlüssel ist `path.name::originalname`: `originalname` ohne Parameter, also würde ein parametrisierter Test seine Ausnahme für alle Varianten erhalten; die drei Tests sind nicht parametrisiert, kein Problem heute. (c) Zu breit? Ausnahme gilt für den ganzen Test, nicht nur für die Attrappe; ein Test dieser drei könnte also eine echte Installation verstecken. Gegenmaßnahme besteht: dieselben Tests setzen eigene Attrappen und `VF_NPM` aus der Vorgabe zeigt ins Leere; die Messung (316M für die ganze Suite) belegt, dass nichts Großes liegt. Schlüssel nutzt den Dateinamen ohne Ordner, eine gleichnamige Datei in anderem Ordner würde mitgemeint: theoretisch, LOW. (d) Wächter schlägt an: Test 3 (Tiefe 1 bis 3 gefunden, Tiefe 4 nicht) und Test 4 (ähnliche Ordner still), beide grün; `glob` auf Verzeichnisse mit `is_dir()`. (e) Nebeneffekt: der Wächter prüft nach dem Test (`yield`), ein Fehler im Teardown wird als „error“ gemeldet, nicht als „failed“; das reicht, der Lauf wird rot. (f) AC-4: test_betrieb.py:1143 läuft unverändert grün (292 passed in den vier genannten Dateien, Ausgabe docs/artifacts/fix-628-playwright-tmp/adversary-test-output.txt). (g) AC-5: test-green-output.txt zeigt 3329 passed und 316M temporärer Ordner. (h) AC-6: `git diff origin/main -- betrieb/veroeffentlichen.sh` leer (0 Zeilen). CI-Pflichtprüfungen können erst nach dem Push belegt werden: offen nach Auslieferung, kein Defekt.
**Implementierer:** Die Grenzen der Liste und der Tiefe sind in der Spec unter Risks dokumentiert und gewollt; die Liste darf nur kürzer werden.

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/conftest.py:52
  Description: Ausnahmeliste vergleicht `Dateiname::originalname`, ignoriert Ordner und Parameter; gilt für den ganzen Test.
  Spec requirement: AC-3 — Wächter scheitert bei Installation unter tmp_path
  Conflict: Nur theoretisch zu breit (gleichnamige Datei oder parametrisierte Variante würde mit ausgenommen); heute nicht ausgelöst.
  Remediation: Optional `request.node.nodeid` (relativ) statt Dateiname nutzen.

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_software_weg_454.py:345
  Evidence: `sw` setzt `VF_NPM` auf nicht vorhandene Datei; Test mit npm-Attrappe im PATH ruft sie nie auf, „npm missing“ erscheint; die Fixture `alt` zusätzlich in Zeile 656.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/conftest.py:23
  Evidence: `instanz_leeren` setzt `VF_NPM` auf `tmp_path/kein-npm`; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/conftest.py:60
  Evidence: autouse-Wächter ruft `playwright_funde` (Zeile 42) nach jedem Test; Tests 3 und 4 in test_playwright_tmp_628.py:57 und :70 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_playwright_tmp_628.py:30
  Evidence: test_betrieb.py-Attrappentest unverändert grün (292 passed); Gegenprobe mit npm-Shim im PATH über acht Dateien: 420 passed, null npm-Aufrufe.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_playwright_tmp_628.py:30
  Evidence: test-green-output.txt: 3329 passed, temporärer Ordner 316M.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/tests/test_playwright_tmp_628.py:1
  Evidence: Diff veroeffentlichen.sh gegen origin/main leer; CI-Teil offen bis nach der Auslieferung (kein Defekt).
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 292 passed (vier Dateien), 420 passed (Gegenprobe mit npm-Shim), volle Suite 3329 passed, 0 failed, 0 übersprungen
Edge cases: geprüft, nichts gebrochen (F001 LOW)
Regressions: keine
Checklist: 6/6 (AC-6 CI-Teil offen bis nach der Auslieferung)

## Geprüfte Dateien

- sha256:80d786207fe41fbc46e409687cb844f078b21bdbf0acb1f6b8e5c7d0666ac0f0  engine/tests/conftest.py
- sha256:f6e4fb020aa4ea0f41366bb3c0a01bd778e985d9bedfaf39906dd0c7ad07730f  engine/tests/test_playwright_tmp_628.py
- sha256:4b59f6fd6607344afa7954868bd33da380dab51f6ca9e0be824d63aac0466d32  engine/tests/test_software_weg_454.py

## Prüfbasis

- base: 85e4a28d998f170290275fc41f7e58bfc5a3af30
- blob:b1caf790da20733b6f76e0996e5fc8b0467897de  engine/tests/conftest.py
- blob:fa2293baabf05b3cb38de4c0ac10df915edc959f  engine/tests/test_playwright_tmp_628.py
- blob:e6268c4ccf38e4ac316439e1ad0e6d7a068a60e8  engine/tests/test_software_weg_454.py

## Geprüfte Dateien

- sha256:80d786207fe41fbc46e409687cb844f078b21bdbf0acb1f6b8e5c7d0666ac0f0  engine/tests/conftest.py
- sha256:f6e4fb020aa4ea0f41366bb3c0a01bd778e985d9bedfaf39906dd0c7ad07730f  engine/tests/test_playwright_tmp_628.py
- sha256:4b59f6fd6607344afa7954868bd33da380dab51f6ca9e0be824d63aac0466d32  engine/tests/test_software_weg_454.py

## Prüfbasis

- base: 85e4a28d998f170290275fc41f7e58bfc5a3af30
- blob:b1caf790da20733b6f76e0996e5fc8b0467897de  engine/tests/conftest.py
- blob:fa2293baabf05b3cb38de4c0ac10df915edc959f  engine/tests/test_playwright_tmp_628.py
- blob:e6268c4ccf38e4ac316439e1ad0e6d7a068a60e8  engine/tests/test_software_weg_454.py
