# Context: fix-626-umgebung-fingerabdruck

## Request Summary
Test F002 (`test_f002_rueckfall_mit_rot_datei_kein_erneuter_rollout_und_kein_nachziehen`) war lokal rot: Der zweite Lauf
meldet `Known red state …, checking again (environment changed)` und rollt den roten Commit erneut aus (#626).

## Ursache (nachgestellt)
`umgebung_stand` (betrieb/veroeffentlichen.sh) nimmt die Playwright-Version nur auf, wenn `PLAYWRIGHT_MODUL` gesetzt ist.

- Lauf 1 (Deploy der Dienste scheitert): `abhaengigkeiten_playwright` (Zeile ~783) setzt und exportiert `PLAYWRIGHT_MODUL`,
  **danach** schreibt `rot_schreiben` den Fingerabdruck → mit Playwright-Version.
- Lauf 2: `rot_erneut_pruefen` (Zeile ~729) läuft **vor** `abhaengigkeiten_playwright` → Variable leer → Fingerabdruck ohne
  Playwright-Version → „environment changed“ → erneuter Rollout, bei jedem Takt.

Gilt überall, wo npm vorhanden ist, also auch auf der Instanz (echter Betriebsfehler: ein gescheiterter Deploy wird jeden Takt
neu ausgerollt, statt bis zu neuem Commit, echter Umgebungsänderung oder Frist zu warten). Gleiches gilt für Rot-Dateien der
Art `reise` (Zeile ~961, ebenfalls nach `abhaengigkeiten_playwright`). Seit #628 setzen die Tests `VF_NPM` auf eine nicht
vorhandene Datei; damit ist der Test in CI und lokal grün, der Fehler aber nur verdeckt. Mit einer npm-Attrappe lokal rot
reproduziert.

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/veroeffentlichen.sh | `umgebung_stand`, `rot_schreiben`, `rot_erneut_pruefen`, `abhaengigkeiten_playwright` |
| betrieb/deploy.sh | Muster: ohne `PLAYWRIGHT_MODUL` die Kopie der Instanz `<FR_DIENST>/playwright/node_modules/playwright/index.mjs` |
| engine/konnektor.py | gleiches Rückfallmuster (`PLAYWRIGHT_MODUL`, sonst Kopie der Instanz) |
| engine/tests/test_software_weg_454.py | Fixture `sw`, Test F002 |
| engine/tests/test_betrieb.py | Test zu #203 (rot erneut prüfen), setzt `VF_UMGEBUNG` gezielt |
| engine/tests/conftest.py | Wächter `PLAYWRIGHT_ATTRAPPEN` (#628): Tests mit npm-Attrappe müssen dort stehen |

## Existing Patterns
- Rückfall auf die Playwright-Kopie der Instanz, wenn `PLAYWRIGHT_MODUL` fehlt (deploy.sh, konnektor.py).
- `VF_UMGEBUNG` überschreibt den Fingerabdruck in Tests (#203).

## Dependencies
- Upstream: `FR_PYTHON`, node, `<FR_DIENST>/playwright` (angelegt von `abhaengigkeiten_playwright`).
- Downstream: Rot-Datei `veroeffentlichen-rot` (Feld `umgebung`), Entscheidung „bekannter roter Stand überspringen“.

## Risks & Considerations
- Nach dem Wechsel ändert sich der Fingerabdruck einmalig (bestehende Rot-Datei ohne Playwright-Version) → einmal
  „environment changed“, danach stabil. Unkritisch (einmaliges Neuprüfen ist gewollt bei Unklarheit).
- Test mit npm-Attrappe legt `node_modules/playwright` unter tmp_path an → Eintrag in `PLAYWRIGHT_ATTRAPPEN` nötig.

## Analysis

### Type
Bug (Betriebsfehler, durch die Testumgebung seit #628 verdeckt)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| betrieb/veroeffentlichen.sh | MODIFY | `umgebung_stand` liest die Playwright-Version unabhängig davon, ob `abhaengigkeiten_playwright` in diesem Lauf schon lief: `PLAYWRIGHT_MODUL` nur so, wie es beim Start des Skripts gesetzt war (Einstellung der Instanz), sonst die Kopie der Instanz `<FR_DIENST>/playwright/node_modules/playwright/package.json` (Muster wie deploy.sh). Kopfkommentar zum Fingerabdruck ergänzen. |
| engine/tests/test_software_weg_454.py oder test_betrieb.py | MODIFY | Regressionstest: npm-Attrappe, Deploy der Dienste scheitert in Lauf 1, Lauf 2 ohne `VF_UMGEBUNG` → „Known red state … skipped“, kein zweiter `--dienste`-Aufruf. |
| engine/tests/conftest.py | MODIFY | neuen Test in `PLAYWRIGHT_ATTRAPPEN` eintragen (legt `node_modules/playwright` unter tmp_path an). |

### Scope Assessment
- Files: 3
- Estimated LoC: +40/-3
- Risk Level: LOW (nur der Fingerabdruck der Prüfumgebung; einmalig „environment changed“ nach dem Wechsel, danach stabil)

### Technical Approach
Ursache: Der Fingerabdruck hängt von einer Variable ab, die das Skript selbst mitten im Lauf setzt. Lauf 1 schreibt die
Rot-Datei nach `abhaengigkeiten_playwright` (mit Version), Lauf 2 vergleicht vorher (ohne Version) → jeder Takt rollt neu aus.
Gleiches für Rot-Dateien der Art `reise` (Zeile ~961). Bei `software_pruefen` läuft `abhaengigkeiten_playwright` in einer
Unterschale, dort bleibt die Variable im Elternprozess leer (bisher zufällig stabil).

Lösung: Beim Skriptstart `pw_modul_einstellung="${PLAYWRIGHT_MODUL:-}"` merken; `umgebung_stand` nimmt
`${pw_modul_einstellung:-$FR_DIENST/playwright/node_modules/playwright/index.mjs}` und liest daneben `package.json`
(fehlt sie: leer, wie bisher). Damit hängt der Fingerabdruck nur vom Zustand auf der Platte ab, nicht von der Reihenfolge im
Lauf; eine echte Neuinstallation (neue Version) zählt weiterhin als Umgebungsänderung.

Nicht gewählt: `VF_UMGEBUNG` im Fixture `sw` fest setzen (Vorschlag im Issue) — das verdeckt den Betriebsfehler nur weiter.
`VF_NPM`=nicht vorhanden bleibt im Fixture (#628), der Regressionstest setzt gezielt eine npm-Attrappe.

### Dependencies
- `FR_DIENST` ist vor `umgebung_stand` immer gesetzt (Rot-Datei liegt dort).
- Tests zu #203 (`VF_UMGEBUNG` gezielt) bleiben unberührt, `VF_UMGEBUNG` hat weiter Vorrang.

### Open Questions
- keine (reiner Betriebsfehler, keine Produktentscheidung)
