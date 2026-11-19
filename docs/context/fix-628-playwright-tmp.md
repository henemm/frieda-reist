# Context: fix-628-playwright-tmp

## Request Summary
Ein Testlauf legt je Test eine vollständige Playwright-Installation (rund 930 MB) im temporären Ordner ab; ein paralleler
Lauf füllt so bis zu 38 GB und die Platte des Servers (ENOSPC bei anderen Läufen). Ziel: Tests installieren nie echte
Browser, und ein Test sichert das ab (#628).

## Ursache (belegt)
- `betrieb/veroeffentlichen.sh:948` ruft seit #618 im Software-Weg `abhaengigkeiten_playwright` bedingungslos auf
  (Browser für das Seitenbild des Konnektors).
- `abhaengigkeiten_playwright` (`betrieb/veroeffentlichen.sh:627`) nimmt `npm="${VF_NPM:-npm}"`; ist npm im PATH
  (auf dem Server über fnm), installiert es `npm ci` und `playwright install chromium webkit` nach `$FR_DIENST/playwright`.
- Tests mit `FR_DIENST` unter `tmp_path` (Fixture `sw` in `engine/tests/test_software_weg_454.py:303`, `seiten/_dienst`)
  setzen kein `VF_NPM` → jeder Test bekommt eine eigene echte Installation.
- `engine/tests/conftest.py` (`instanz_leeren`) entfernt alle `VF_`-Werte, setzt aber keinen Ersatz für `VF_NPM`.

## Related Files
| File | Relevance |
|------|-----------|
| engine/tests/conftest.py | `instanz_leeren`: zentrale Stelle, die die Umgebung jedes Tests festlegt; hier `VF_NPM` auf eine nicht vorhandene Datei setzen |
| betrieb/veroeffentlichen.sh | `abhaengigkeiten_playwright` (Z. 627), Aufrufe Z. 824 (Prüfung im Klon), Z. 948 (Software-Weg), Z. 1200 (`abhaengigkeiten`) |
| engine/tests/test_software_weg_454.py | Fixture `sw` (Z. 296 ff.) und `l1` (Z. 66 ff.), betroffene Tests |
| engine/tests/test_betrieb.py | Z. 1140–1185: Test mit npm-Attrappe (`VF_NPM` selbst gesetzt), darf sich nicht ändern |

## Existing Patterns
- Externe Programme in Betriebsskripten haben Testhaken `VF_PIP`, `VF_NPM`, `VF_DEPLOY`, `VF_PRUEFEN`.
- `conftest.py` setzt Ordner der Instanz zentral auf tmp_path (FR_DIENST, FR_KONTEN …) – gleiches Muster für `VF_NPM`.
- Ohne npm: `abhaengigkeiten_playwright` gibt "npm missing" aus und gibt 0 zurück (kein Abbruch).

## Dependencies
- Upstream: npm/fnm im PATH der Testumgebung.
- Downstream: Browsertests nutzen `PLAYWRIGHT_MODUL`/`PLAYWRIGHT_BROWSERS_PATH` bzw. `playwright_pfad.py`, nicht `VF_NPM` → unberührt.
  Der Server-Lauf (`pruefen_lauf`) setzt `PLAYWRIGHT_*` vor pytest; `VF_NPM` wirkt nur in Unterprozessen der Tests.

## Risks & Considerations
- Tests, die echtes npm erwarten: keine gefunden (Test in test_betrieb setzt eigene Attrappe).
- Absicherung: Test, dass ein Software-Weg-Lauf im Test keinen `_dienst/playwright`-Ordner anlegt, und dass conftest `VF_NPM` setzt;
  eine allgemeine Größengrenze je tmp-Ordner wäre teuer (du über jeden Test) – Abwägung in der Spec.
- Alte Reste in /tmp/pytest-of-* räumt pytest selbst (behält 3 Läufe).

## Analysis

### Type
Bug (Testumgebung). Ursache im Kontext oben belegt und in der Analyse am Code nachgeprüft; keine Subagenten nötig.

### Nachprüfung (19.11.2026)
- Der Weg ins echte npm führt nicht über `os.environ`, sondern über selbst gebaute Umgebungen: Fixture `sw`
  (`test_software_weg_454.py` Z. 338) baut `env = {**SAUBER, …}`; `SAUBER` entsteht beim Import und entfernt alle `VF_`.
  Ein `VF_NPM` aus `conftest.instanz_leeren` käme dort **nicht** an. Der Kontext-Vorschlag (nur conftest) reicht also nicht.
- Nur `sw` trifft die Installation: Sein Software-Repo verlinkt `engine/` auf die echte Engine, also liegt
  `engine/tests/playwright/package-lock.json` vor. Die Fixture `vf` (`test_betrieb.py` Z. 179) läuft im Bauordner ohne
  diese Datei, `abhaengigkeiten_playwright` kehrt sofort zurück.
- `lauf_neu` (`test_software_weg_454.py` Z. 662) baut auf `vf["env"]` auf, ebenfalls ohne Sperrdatei, unkritisch.
- CI hat npm (installiert Playwright), also installierte auch dort jeder `sw`-Test; der Fix spart CI-Zeit.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/tests/test_software_weg_454.py | MODIFY | Fixture `sw`: `VF_NPM` auf eine nicht vorhandene Datei setzen (wie die übrigen `VF_`-Haken) |
| engine/tests/conftest.py | MODIFY | `instanz_leeren`: `VF_NPM` ebenso setzen (Tests, die `os.environ` weiterreichen); autouse-Wächter: nach jedem Test Fehler, wenn unter `tmp_path` eine Playwright-Installation (`*/playwright/node_modules`, bis Tiefe 3) liegt |
| engine/tests/test_playwright_tmp_628.py | CREATE | Tests: `sw`-Lauf legt kein `_dienst/playwright` an; Wächter erkennt eine untergeschobene Installation; conftest setzt `VF_NPM` |

### Scope Assessment
- Files: 3
- Estimated LoC: +60/-0
- Risk Level: LOW (nur Tests; Betriebsskript unverändert)

### Technical Approach
1. Ursache an der Quelle: `sw` setzt `VF_NPM` explizit auf eine nicht vorhandene Datei; das Skript meldet „npm missing“
   und macht weiter (Rückgabe 0, Verhalten der Tests unverändert).
2. Gleiches zentral in `instanz_leeren` für Aufrufe mit `os.environ`.
3. Absicherung gegen künftige Wege (neue Fixture mit eigener Umgebung): autouse-Wächter in `conftest.py` prüft nach jedem
   Test per `glob` (keine Größenmessung) auf `playwright/node_modules` unter `tmp_path` und lässt den Test scheitern.
   Abgewogen gegen den Vorschlag im Issue (Größengrenze < 50 MB je tmp-Ordner): `du` über jeden Test kostet bei ~2000 Tests
   spürbar Zeit und trifft auch legitime große Testdaten; die Existenzprüfung trifft genau den Fehler und kostet fast nichts.
   Gemeinsamer Browser-Cache (Vorschlag 1 im Issue) verworfen: Die Tests brauchen gar keine Installation, nur den Weg bis
   „npm missing“; ein Link auf den Cache würde den Installationsweg trotzdem durchlaufen.
- Betriebsskript bleibt unverändert: der Server braucht die Installation (#618).

### Dependencies
- Browsertests nutzen `PLAYWRIGHT_MODUL`/`playwright_pfad.py`, nicht `VF_NPM`, also unberührt.
- `test_betrieb.py` Z. 1140–1185 setzt eigene npm-Attrappe, überschreibt den Vorgabewert, bleibt grün.

### Open Questions
- keine (reine Testumgebung, keine Produktentscheidung)
