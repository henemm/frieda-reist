# Context: fix-356-playwright-ci

## Request Summary
Der CI-Schritt „Playwright und Browser“ hängt, wenn `apt` Systempakete vom Spiegel `azure.archive.ubuntu.com` lädt, und der Job läuft 25 Minuten bis zum Abbruch (#356). Der Schritt soll eine kurze eigene Zeitgrenze und einen zweiten Versuch bekommen. Außerdem ist zu prüfen, ob sich die Browser cachen lassen.

## Related Files
| File | Relevance |
|------|-----------|
| .github/workflows/tests.yml | Schritt „Playwright und Browser“ (Zeilen 40–45): `npx playwright install --with-deps chromium webkit`; Job-Grenze `timeout-minutes: 25`; Matrix `leer` und `instanz` |
| engine/tests/playwright/package.json, package-lock.json | feste Playwright-Version, möglicher Cache-Schlüssel |
| engine/tests/test_pwa.py | Browser-Prüfung `offline_im_browser`; Schlusschritt der CI verlangt, dass sie nicht übersprungen wird |
| CLAUDE.md | Ruleset von `main` bleibt unberührt; Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks` |

## Existing Patterns
- Python-Pakete werden mit `actions/setup-python` (`cache: pip`) gecacht.
- Der Schritt „Python-Pakete“ lädt `libcairo2` und `nginx-core` mit `apt-get` und hängt damit ebenfalls vom Spiegel ab.
- Die Version der Browser steckt in `package-lock.json`, der Browser-Cache lässt sich daran festmachen.
- Frühere Änderungen an der Zeitgrenze: #258 (40 Min.), #322 (25 Min. mit xdist).

## Dependencies
- Upstream: Paketspiegel von Ubuntu (apt), Playwright-CDN, npm.
- Downstream: beide Matrix-Jobs und der Schlusschritt „Browser-Prüfung darf nicht übersprungen worden sein“; die Pflichtprüfungen für den Push nach `main`.

## Existing Specs
- Keine einschlägige Spec. Ähnlich ist nur #202 (gleiche Prüfumgebung in CI und Instanz, Commit 5e2439f).

## Risks & Considerations
- `--with-deps` installiert Systempakete über apt. Bei einem Cache der Browser (`~/.cache/ms-playwright`) fehlen die Systempakete weiterhin, ein Cache allein löst das Problem also nur teilweise. Eine Alternative ist, bei einem Cache-Treffer nur `install-deps` auszuführen.
- Zeitgrenze und zweiter Versuch (`timeout-minutes` am Schritt plus eine Wiederholung, etwa per Schleife in der Shell, ohne neue Fremd-Action) lassen sich nur in der CI selbst testen.
- Das Ruleset darf nicht abgeschaltet werden. Die Änderung läuft über Branch `ci-356-playwright`, PR und grüne CI.
- Die Änderung betrifft nur die Workflow-Datei und keine Reisedaten, eine Umstellung in `neu.py nachziehen` ist nicht nötig.

## Analysis

### Type
Bug (CI, Paketspiegel hängt; kein Codefehler)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| .github/workflows/tests.yml | MODIFY | Schritte „Python-Pakete“ und „Playwright und Browser“: kurze Zeitgrenze, Wiederholung, apt-Timeouts, Browser-Cache |

### Scope Assessment
- Files: 1 (+ ggf. ein Test, der die Workflow-Datei prüft, falls vorhanden)
- Estimated LoC: +20/-4
- Risk Level: LOW (nur CI; Ruleset unberührt; nur in der CI selbst prüfbar)

### Technical Approach
1. apt direkt gegen das Hängen absichern: `apt-get -o Acquire::Retries=3 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30` (ein stehender Download bricht nach 30 s ab und wird wiederholt, statt 25 Min. zu warten). Gilt für beide Schritte, auch „Python-Pakete“ (gleiche Abhängigkeit vom Spiegel).
2. Schritt „Playwright und Browser“: `timeout-minutes: 10` am Schritt, darin Schleife mit zwei Versuchen, je `timeout 240` (kein Fremd-Action). Der Schritt-Abbruch ist nur Notbremse; die Wiederholung liegt in der Shell.
3. Cache (`actions/cache`, offizielle Action) für `~/.cache/ms-playwright`, Schlüssel `hashFiles('engine/tests/playwright/package-lock.json')` + OS. Bei Treffer nur `npx playwright install-deps chromium webkit` (apt bleibt nötig, aber kleiner), bei Fehlschlag voller Install. Gewinn: kein CDN-Download; apt-Abhängigkeit bleibt, daher ist Punkt 1 der eigentliche Schutz.
4. Nicht tun: Ruleset ändern, Job-Grenze 25 Min. ändern.

### Dependencies
Ubuntu-Spiegel (apt), Playwright-CDN, npm; Matrix `leer`/`instanz`; Schlusschritt „Browser-Prüfung darf nicht übersprungen worden sein“ bleibt unverändert.

### Befunde gegen den Plan
Cache allein löst das Problem nicht (Systempakete kommen aus apt). `timeout-minutes` am Schritt erlaubt keine Wiederholung im selben Schritt, deshalb Shell-Schleife.

### Open Questions
- [ ] Keine; Entscheidung: Cache mitnehmen (klein, offizielle Action) oder weglassen (weniger Bewegliches)? Empfehlung: mitnehmen.
