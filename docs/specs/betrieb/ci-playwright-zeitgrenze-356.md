---
entity_id: ci-playwright-zeitgrenze-356
type: bugfix
created: 2026-11-06
updated: 2026-11-06
status: draft
workflow: fix-356-playwright-ci
---

# CI: Paketinstallation mit kurzer Zeitgrenze und zweitem Versuch (#356)

Grundlage: `docs/context/fix-356-playwright-ci.md` (Kontext und Analyse).

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** keine (nur CI-Konfiguration, berührt den Kern aus ADR-0001 nicht)

## Purpose

Der CI-Schritt „Playwright und Browser“ ruft `npx playwright install --with-deps chromium webkit` auf. `--with-deps` lädt Systempakete per `apt` vom Spiegel `azure.archive.ubuntu.com`. Antwortet der Spiegel nicht, steht der Download, und der Job läuft bis zur Job-Grenze von 25 Minuten, ohne dass eine Prüfung läuft. Der Schritt „Python-Pakete“ (`apt-get install libcairo2 nginx-core`) hängt vom selben Spiegel ab. Beide Schritte sollen ein Hängen früh erkennen und einmal wiederholen.

## Ziel

Hängt der Spiegel kurz, läuft die CI trotzdem durch (zweiter Versuch). Hängt er dauerhaft, scheitert der Job nach wenigen Minuten statt nach 25, mit einer klaren Meldung.

## Source

- **File:** `.github/workflows/tests.yml`
- **Schritte:** „Python-Pakete“, „Playwright und Browser (feste Version …)“

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| Ubuntu-Spiegel (apt) | extern | Systempakete für Python-Pakete und Browser |
| Playwright-CDN, npm | extern | Browser und Node-Pakete |
| `engine/tests/playwright/package-lock.json` | Datei | feste Playwright-Version, Schlüssel des Browser-Caches |
| `actions/cache` | offizielle Action | Browser-Cache (`~/.cache/ms-playwright`) |
| Schritt „Browser-Prüfung darf nicht übersprungen worden sein“ | CI-Schritt | bleibt unverändert |
| `engine/tests/test_ci_workflow.py` | neuer Test | liest `tests.yml` und prüft die Zusagen (siehe Test Plan) |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `.github/workflows/tests.yml` | MODIFY | apt mit Wiederholungen und Timeouts; Schritt mit eigener Zeitgrenze und zweitem Versuch; Browser-Cache |
| `engine/tests/test_ci_workflow.py` | CREATE | Struktur-Prüfung der Workflow-Datei (PyYAML ist bereits Abhängigkeit) |

### Estimated Changes

- Files: 2
- LoC: +25/-4 (Workflow ca. 20, Test ca. 40)

### Nicht im Scope

- Das Ruleset von `main` und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`).
- Die Job-Grenze `timeout-minutes: 25` (bleibt).
- Neue Fremd-Actions (nur `actions/cache` aus dem GitHub-Eigenbestand).
- Der Workflow `software-nachziehen.yml` und die Reisen-Repos.
- Ein eigener Paketspiegel oder Container-Image mit vorinstallierten Browsern.

## Implementation Details

1. **apt gegen Hängen.** In „Python-Pakete“ laufen `apt-get update` und `apt-get install` mit `-o Acquire::Retries=3 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30`. Ein stehender Download bricht nach 30 s ab und wird von apt selbst wiederholt.
2. **apt-Optionen für Playwright.** Die Optionen gelten auch für das apt, das Playwright aufruft: per Datei `/etc/apt/apt.conf.d/80-ci-zeitgrenzen` (Inhalt `Acquire::Retries "3"; Acquire::http::Timeout "30"; Acquire::https::Timeout "30";`), die ein eigener Schritt vor beiden Installationen schreibt. Die Datei ist die einzige Quelle; die `-o`-Optionen aus Punkt 1 entfallen dann und stehen nicht zusätzlich in den Befehlen.
3. **Zeitgrenze und zweiter Versuch.** Der Schritt „Playwright und Browser“ bekommt `timeout-minutes: 10` als Notbremse. Im Schritt läuft der Install in einer Schleife mit zwei Versuchen, jeder mit `timeout 240`. Scheitern beide, endet der Schritt mit Fehler und einer Meldung, welcher Versuch woran scheiterte. Kein Fremd-Action.
4. **Cache.** Vor dem Install: `actions/cache` für `~/.cache/ms-playwright`, Schlüssel `playwright-${{ runner.os }}-${{ hashFiles('engine/tests/playwright/package-lock.json') }}`. Bei Treffer genügt `npx playwright install-deps chromium webkit` (nur Systempakete), sonst der volle Install. Die Systempakete kommen so oder so aus apt; der Cache spart nur den Download der Browser von der CDN. Wirkt der Cache nicht, ist das Verhalten wie ohne.
5. **Rest unverändert.** `PLAYWRIGHT_MODUL` wird weiter gesetzt, der Schlusschritt „Browser-Prüfung darf nicht übersprungen worden sein“ bleibt.

## Expected Behavior

- **Input:** ein CI-Lauf (`push` auf `main`, `pull_request`), beide Matrix-Jobs.
- **Output:** normaler Lauf; bei hängendem Spiegel nach 30 s (apt) bzw. 240 s (Playwright-Versuch) ein neuer Versuch, bei zwei Fehlversuchen Abbruch nach höchstens ca. 10 Minuten statt 25.
- **Side effects:** ein GitHub-Cache-Eintrag je Playwright-Version.

## Test Plan

### Automated Tests (TDD RED)

In `engine/tests/test_ci_workflow.py` (liest `.github/workflows/tests.yml` mit PyYAML):

- [ ] Test 1 (`test_playwright_schritt_hat_eigene_zeitgrenze`): GIVEN `tests.yml` / WHEN der Schritt, dessen Name mit „Playwright und Browser“ beginnt, gelesen wird / THEN hat er `timeout-minutes` kleiner als die Job-Grenze.
- [ ] Test 2 (`test_playwright_install_wird_wiederholt`): GIVEN derselbe Schritt / THEN enthält sein `run` eine Schleife mit zwei Versuchen und `timeout` je Versuch, und `playwright install` steht nur darin.
- [ ] Test 3 (`test_apt_hat_zeitgrenzen`): GIVEN die Workflow-Datei / THEN setzt ein Schritt vor „Python-Pakete“ die apt-Zeitgrenzen (`Acquire::Retries`, `Acquire::http::Timeout`), und kein Schritt ruft `apt-get` ohne diese Vorbereitung auf.
- [ ] Test 4 (`test_browser_cache_schluessel_aus_package_lock`): GIVEN die Workflow-Datei / THEN gibt es einen `actions/cache`-Schritt für `~/.cache/ms-playwright` mit `hashFiles('engine/tests/playwright/package-lock.json')` im Schlüssel, vor dem Install-Schritt.
- [ ] Test 5 (`test_unveraendert_wichtiges`): GIVEN die Workflow-Datei / THEN steht der Job weiter bei `timeout-minutes: 25`, der Schlusschritt „Browser-Prüfung darf nicht übersprungen worden sein“ existiert, und alle `uses:` stammen von `actions/`.

Alle fünf sind vor der Umsetzung rot, außer Test 5 (Regressionsschutz).

### Manuelle Prüfung (nur in der CI möglich)

- Der PR-Lauf beider Matrix-Jobs ist grün; der zweite Lauf (Cache-Treffer) ist grün und zeigt „Cache restored“.
- Hängen des Spiegels lässt sich nicht gezielt auslösen; die Zusage stützt sich auf Test 1 bis 4 und die Dokumentation der Optionen.

## Acceptance Criteria

- **AC-1:** Given die Datei `tests.yml` / When der Schritt „Playwright und Browser“ gelesen wird / Then hat er eine eigene Zeitgrenze unter der Job-Grenze und versucht den Install höchstens zweimal, je mit `timeout` (Test 1, 2).
- **AC-2:** Given ein stehender apt-Download / When apt in „Python-Pakete“ oder im Playwright-Install läuft / Then bricht apt nach 30 s ab und wiederholt bis zu dreimal (Test 3).
- **AC-3:** Given dieselbe Version in `package-lock.json` / When ein zweiter CI-Lauf startet / Then kommen die Browser aus dem Cache und der Browser-Download entfällt (Test 4; Prüfung im zweiten PR-Lauf).
- **AC-4:** Given die geänderte Workflow-Datei / When sie mit der alten verglichen wird / Then bleiben Job-Grenze (25 Min.), Ruleset, Matrix und Schlusschritt unverändert, und es kommen keine Actions außerhalb `actions/` hinzu (Test 5).
- **AC-5:** Given der PR-Branch / When die CI läuft / Then sind beide Matrix-Jobs grün, und `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen.

## Risks

- **Nur in der CI prüfbar:** Verhalten bei hängendem Spiegel nicht erzwingbar. Gegenmaßnahme: Struktur-Tests und zwei PR-Läufe; bei Fehlern `gh run rerun`.
- **Cache mit Browsern, aber ohne Systempakete:** deshalb Cache-Treffer → `install-deps`, nie „nichts“.
- **`timeout 240` zu knapp** für den vollen Install auf langsamem Runner: Browser-Download plus apt dauert üblicherweise unter 3 Minuten; der zweite Versuch und die 10-Minuten-Notbremse fangen das ab. Wird es knapp, Wert anheben.
- **apt-Konfiguration als Datei:** greift nur mit `sudo`; GitHub-Runner erlauben das.

## Definition of Done

- [ ] AC-1 bis AC-4 durch Test 1 bis 5 belegt
- [ ] PR-Lauf beider Matrix-Jobs grün, zweiter Lauf mit Cache-Treffer grün
- [ ] Pflichtprüfungen grün, Push nach `main` nur über den normalen Weg (Ruleset unberührt)
- [ ] Issue #356 erst nach Lauf auf `main` schließen

## Changelog

- 2026-11-06: Initiale Spec (#356)
