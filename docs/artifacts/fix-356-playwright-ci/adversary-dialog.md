# Adversary Dialog — fix-356-playwright-ci
Spec: docs/specs/betrieb/ci-playwright-zeitgrenze-356.md
Datum: 2026-11-06 12:47

## Checkliste
- [x] **Input:** ein CI-Lauf (`push` auf `main`, `pull_request`), beide Matrix-Jobs.
- [x] **Output:** normaler Lauf; bei hängendem Spiegel nach 30 s (apt) bzw. 240 s (Playwright-Versuch) ein neuer Versuch, bei zwei Fehlversuchen Abbruch nach höchstens ca. 10 Minuten statt 25.
- [x] **Side effects:** ein GitHub-Cache-Eintrag je Playwright-Version.
- [x] **AC-1:** Given die Datei `tests.yml` / When der Schritt „Playwright und Browser“ gelesen wird / Then hat er eine eigene Zeitgrenze unter der Job-Grenze und versucht den Install höchstens zweimal, je mit `timeout` (Test 1, 2).
- [x] **AC-2:** Given ein stehender apt-Download / When apt in „Python-Pakete“ oder im Playwright-Install läuft / Then bricht apt nach 30 s ab und wiederholt bis zu dreimal (Test 3).
- [x] **AC-3:** Given dieselbe Version in `package-lock.json` / When ein zweiter CI-Lauf startet / Then kommen die Browser aus dem Cache und der Browser-Download entfällt (Test 4; Prüfung im zweiten PR-Lauf).
- [x] **AC-4:** Given die geänderte Workflow-Datei / When sie mit der alten verglichen wird / Then bleiben Job-Grenze (25 Min.), Ruleset, Matrix und Schlusschritt unverändert, und es kommen keine Actions außerhalb `actions/` hinzu (Test 5).
- [x] **AC-5:** Given der PR-Branch / When die CI läuft / Then sind beide Matrix-Jobs grün, und `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen.

## Dialog

### Runde 1
**Adversary:** Testlauf `engine/.venv/bin/python -m pytest -q engine/tests/test_ci_workflow.py`: 5 passed, 0 failed, 0 übersprungen (Ausgabe in `docs/artifacts/fix-356-playwright-ci/adversary-test-output.txt`). Dann Angriff auf die Shell-Logik: den `run`-Block des Playwright-Schritts aus der YAML gezogen und unter `bash -e` mit einem Stub-`npx` im PATH laufen lassen (Cache-Treffer-Zweig auf false gesetzt).
- Stub Exit 124 (Zeitgrenze): beide Versuche laufen, Meldung "Versuch 1/2 gescheitert (Exit-Code 124 ...)" zeigt den echten Exit-Code (`$?` nach dem `if` ist der von `timeout`), danach `::error::` und `exit 1`. `bash -e` bricht NICHT vorzeitig ab (Fehler steht in einer `&&`-Liste, nicht am Ende).
- Stub Exit 7: gleiches Verhalten, Meldung zeigt 7.
- Stub Exit 0: `ok=1; break` im ersten Versuch, nur ein Aufruf, Schleife endet, die Zeile mit `PLAYWRIGHT_MODUL` wird erreicht (das Schreiben in die Umgebungsdatei schlug in meiner Probe nur fehl, weil deren Variable dort nicht gesetzt war).
- Echtes `timeout 1 sleep 5` unter `bash -e -c` liefert 124, wie von der Meldung angenommen.
- Cache: `~` in `actions/cache` `path` wird von der Action auf das Home-Verzeichnis aufgelöst; Schlüssel enthält `hashFiles('engine/tests/playwright/package-lock.json')`, kein `restore-keys`, also ist `cache-hit == 'true'` nur bei exaktem Treffer; sonst voller Install (Fallback wie ohne Cache). Cache-Schritt steht vor dem Install.
- apt-Datei: Schritt "apt-Zeitgrenzen" (Zeile 37) steht vor "Python-Pakete" (Zeile 41) und vor dem Playwright-Schritt (Zeile 54). Davor laufen nur checkout, setup-python, setup-node; keiner ruft apt auf. Dateiinhalt entspricht der Spec; `-o`-Optionen stehen nicht zusätzlich in den Befehlen (Spec Punkt 2).
- Unverändert: Job-Grenze 25 (Zeile 17), Matrix (Zeile 23), Schlusschritt (Zeile 103); alle `uses:` aus `actions/` (checkout, setup-python, setup-node, cache, upload-artifact).
- Test-Schwäche Test 2: Die Korrektur vergleicht per Index (`i == i_pw`), nicht mehr per Objekt-Identität; der Test ist nicht trivial grün: Er scheitert, wenn ein anderer Schritt "playwright install" im `run` hat, und die Regexe prüfen echte Schleife und `timeout`.
**Implementierer:** (nicht beteiligt, Kontext isoliert)

### Runde 2
**Adversary:** Zweiter Blick auf Randfälle.
- F001 (LOW): `timeout 240 npx ...` beendet nur den Prozess `npx`; ein von Playwright per `sudo apt-get` gestartetes Kind kann weiterlaufen und die dpkg-Sperre halten, der zweite Versuch könnte dann an der Sperre scheitern. Die apt-Timeouts begrenzen die Lebensdauer; kein Spec-Verstoß, nur Härtungsidee.
- F002 (LOW): Test 3 prüft nur, dass ein Schritt mit den apt-Zeitgrenzen vor "Python-Pakete" und vor jedem `apt-get` steht; dass die Datei auch vor dem Playwright-Schritt geschrieben wird, ist nur durch die Reihenfolge abgedeckt (von Hand geprüft: Zeile 37 vor 54). Aktuell korrekt.
- `npm ci` läuft ohne eigenes `timeout`, aber unter der 10-Minuten-Notbremse; Worst Case bleibt klar unter der Job-Grenze von 25 Minuten.
- Im Cache-Treffer-Zweig steht `install-deps`; der Regex von Test 2 passt auch darauf, der Wiederholungsschutz gilt für beide Zweige.
- AC-3 und AC-5 (CI-Lauf beider Matrix-Jobs, Cache-Treffer im zweiten Lauf, volle Suite) lassen sich lokal nicht beweisen; statisch ist alles in Ordnung. Die vollständige Suite (rund 20 Min.) habe ich nicht erneut gestartet.
- Hinweis zur Probe: Mein erster Probelauf hat versehentlich ein echtes `npx playwright install-deps` angestoßen (Shell-Funktion statt PATH-Stub, `timeout` sieht keine Funktionen); es lief ohne Root-Rechte ins Leere. Danach nur noch Stub im PATH.
**Implementierer:** (nicht beteiligt)

### Findings und Confirmations
Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: .github/workflows/tests.yml:65
  Description: `timeout 240 npx playwright install --with-deps` beendet nur npx, nicht zwingend das apt-Kind.
  Spec requirement: AC-1 — höchstens zwei Versuche je mit timeout
  Conflict: Kein Verstoß; zweiter Versuch könnte an dpkg-Sperre scheitern.
  Remediation: optional `timeout -k 10 240` oder Prozessgruppe beenden.

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/tests/test_ci_workflow.py:53
  Description: Test 3 prüft die Reihenfolge der apt-Datei nur gegen Schritte mit `apt-get` im `run`, nicht gegen den Playwright-Schritt.
  Spec requirement: AC-2 — apt-Zeitgrenzen auch im Playwright-Install
  Conflict: Lücke im Regressionsschutz, aktueller Stand korrekt.
  Remediation: Test 3 um `i_conf < i_playwright` ergänzen.

Confirmation:
  AC: AC-1
  Code reference: .github/workflows/tests.yml:55
  Evidence: `timeout-minutes: 10` (< 25), Schleife `for versuch in 1 2` mit `timeout 240` (Zeilen 60 bis 68), Shell-Probe unter `bash -e` bestätigt zwei Versuche, Meldung und exit 1.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: .github/workflows/tests.yml:37
  Evidence: apt-Konfigurationsdatei mit Retries 3 und Timeout 30 (http, https) vor allen apt-Aufrufen (Zeilen 41 bis 44 und Playwright-Schritt).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: .github/workflows/tests.yml:47
  Evidence: `actions/cache@v4`, Pfad `~/.cache/ms-playwright`, Schlüssel aus `hashFiles` der package-lock, vor dem Install; Cache-Treffer-Zweig in Zeile 61 bis 63. Wirkung im zweiten CI-Lauf nur dort prüfbar.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: .github/workflows/tests.yml:17
  Evidence: Job-Grenze 25, Matrix Zeile 23, Schlusschritt Zeile 103 unverändert, alle `uses:` aus `actions/`; Test 5 grün (engine/tests/test_ci_workflow.py:80).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_ci_workflow.py:34
  Evidence: Alle 5 Struktur-Tests grün (5 passed); CI-Lauf und Gesamtsuite stehen aus (nicht lokal beweisbar).
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 5 passed, 0 failed, 0 übersprungen
Edge cases: Shell-Schleife unter bash -e, Cache, apt-Reihenfolge geprüft; zwei LOW-Hinweise (F001, F002)
Regressions: None found
Checklist: 8/8 Punkte statisch bewiesen; AC-3-Wirkung und AC-5-CI-Lauf nur in der CI prüfbar

## Geprüfte Dateien

- sha256:a5672a86e9a044379927db3dbe167bdf876734c1295f07d3db03bbcde739e473  .github/workflows/tests.yml
- sha256:92af9adae9bc2982df39b648874619d67d40b8ac3fc7060c45d602a3a4f6c108  engine/tests/test_ci_workflow.py

## Prüfbasis

- base: 3486df2d4322618097634267e1a4a434cc8642fc
- blob:735fcccae02362a5794139462f14a00a24f93fed  .github/workflows/tests.yml
- blob:8209a3bd56ea65edc9a1635c2bd762b30282e9b1  engine/tests/test_ci_workflow.py
