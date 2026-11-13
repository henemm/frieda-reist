---
entity_id: wackelige-browsertests-550-537
type: bugfix
created: 2026-11-13
updated: 2026-11-13
status: draft
workflow: fix-550-537-wackelige-browsertests
---

# Wackelige Browsertests stabilisieren (#550, #537)

Grundlage: `docs/context/fix-550-537-wackelige-browsertests.md` (Kontext, Reproduktion, Analyse).

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es ändern sich nur Testskripte und Testhilfen. Seite, Vorlage, Engine und Betrieb bleiben unverändert, der Kern aus ADR-0001 ist nicht berührt.

## Purpose

Drei Browsertests scheitern gelegentlich, ohne dass sich die Seite geändert hat: zwei WebKit-Tests unter voller Parallel-Last auf dem Server (#550) und der Vollseiten-Screenshot der Bausteinseite in der CI (#537). Die Tests sollen auf den fachlichen Zielzustand warten statt auf einen Zeitpunkt, und die Vollseitenbilder sollen robust und nicht mehr Ursache eines roten Laufs sein.

## Ursachen

1. **Reise-Stand-Test (#550).** Nach `reload` mit Stand 2 laufen zwei Wege um die Wette: Der Service Worker zeigt `#neu` mit dem allgemeinen Text „Neue Version des Handbuchs bereit.“, und `api/stand` (Stub, antwortet nach 1 s, #321) setzt danach „Neu: Reise-Stand 2.“. `stand_browser.mjs` wartet nur auf `#neu:not([hidden])` und liest sofort; ist der allgemeine Text zuerst da, liest der Test den Zwischenstand. Der Endzustand der Seite ist richtig.
2. **Packliste-Test (#550).** `plAlleKnopf()` erzeugt den Knopf leer, den Text setzt `stand()` erst per `setTimeout`. Nach dem Haken an „Wanderschuhe“ wird neu gezeichnet; der Test liest `knopf0` im selben Takt, also `""`. Für Nutzer ist das höchstens ein Bild lang leer.
3. **Bausteinseite (#537).** `Page.captureScreenshot` scheitert gelegentlich im CI-Runner bei Vollseitenbildern bis 32000 px Höhe. Betrifft nur Läufe mit `RH_BILDER` (nur CI); die Bilder dienen der Durchsicht, kein Test prüft sie.

## Source

- **File:** `engine/tests/stand_browser.mjs`, `engine/tests/seiten_packliste.mjs`, `engine/tests/seiten_browser.mjs`, `engine/tests/seiten_brett.mjs`, `engine/tests/test_seite.py`
- **Identifier:** Messskripte der Tests `test_reise_stand_im_browser`, `test_packliste_im_browser`, Bausteinseite in `test_seite.py`; neuer Helfer `bild` in `engine/tests/bild.mjs`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| Playwright (Chromium, WebKit), Node | extern | Browser für die Messskripte, `PLAYWRIGHT` |
| `engine/tests/test_pwa.py` (`test_reise_stand_im_browser`) | Test | ruft `stand_browser.mjs` auf, Stub-Server mit 1 s Verzögerung (#321) |
| `engine/tests/test_packliste.py` (`test_packliste_im_browser`) | Test | prüft `knopf0 == "Alle aufklappen"` (#511) |
| `engine/tests/test_seite.py` | Test | ruft `seiten_browser.mjs` auf, legt den Bildordner an |
| `.github/workflows/tests.yml` | CI | setzt `RH_BILDER`, Artefakt `bausteine`; bleibt unverändert |
| Muster #369, #457 | Vorgehen | Wartebedingung statt Zeit, bei Zeitüberschreitung weiterlesen |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/tests/stand_browser.mjs` | MODIFY | Nach `reload` per `waitForFunction` auf den Text „Neu: Reise-Stand“ in `#neu` warten (15 s, bei Zeitüberschreitung weiterlesen) |
| `engine/tests/seiten_packliste.mjs` | MODIFY | Vor dem Lesen von `knopf0` und nach `reload` (`knopf`) mit `warte()` auf nicht leeren Text von `.pack-alle` warten; Vollseitenbilder über den Helfer |
| `engine/tests/bild.mjs` | CREATE | Helfer `bild(page, optionen)`: bis zu 3 Versuche mit kurzer Pause; endgültiges Scheitern gibt `false` zurück, wirft nicht |
| `engine/tests/seiten_browser.mjs` | MODIFY | Bausteinseite über den Helfer; fehlende Bilder als Liste `bilderFehlen` in der JSON-Ausgabe |
| `engine/tests/seiten_brett.mjs` | MODIFY | Vollseitenbilder über den Helfer |
| `engine/tests/test_seite.py` | MODIFY | Fehlende Bilder (`bilderFehlen`) als `warnings.warn`, nicht rot |
| `engine/tests/test_bild_helfer.py` | CREATE | Test des Helfers mit gestellter Seite ohne Browser, über `node` aufgerufen |

### Estimated Changes

- Files: 7
- LoC: +60/-10

### Out of Scope

- Änderung der Vorlage (insbesondere `plAlleKnopf`: den Knopftext sofort beim Erzeugen zu setzen). Der leere Knopf ist für Nutzer nicht bemerkbar; eine Produktänderung wäre gesondert abzuwägen.
- Senken der Höchsthöhe von 32000 px bei Vollseitenbildern (kleiner würde Bausteine abschneiden). Erst wenn die Warnung trotz Wiederholung wiederkehrt, wird die Höhe gesenkt und im Issue vermerkt.
- Engine, Betrieb, `.github/workflows/tests.yml`, Ruleset von `main`.
- Die festen Pausen im Packliste-Skript (400 ms, #503 gewollt; 300 ms nach Nachreichen).

## Implementation Details

Wartebedingung statt Zeitpunkt (Muster #369, #457): auf den fachlichen Zielzustand warten, nicht auf ein Zwischensignal.

1. **`stand_browser.mjs`:** Nach `reload` mit Stand 2 `waitForFunction` auf `#neu` mit Text, der „Neu: Reise-Stand“ enthält, Zeitgrenze 15 s. Läuft sie ab, wird das abgefangen und trotzdem gelesen, damit der Test mit seiner bisherigen Meldung scheitert und nicht mit einem Abbruch des Skripts. Zeigt die Seite wirklich nie den Stand, bleibt der Test rot.
2. **`seiten_packliste.mjs`:** Vor `knopf0 = texte(".pack-alle")[0]` und vor dem Lesen von `knopf` nach `reload` mit dem vorhandenen Helfer `warte()` auf nicht leeren Text von `.pack-alle` warten (Zeitgrenze des Helfers, 5 s, Abbruch abfangen und weiterlesen). Die Prüfung `== "Alle aufklappen"` in `test_packliste.py` bleibt unverändert.
3. **`bild.mjs`:** `bild(page, optionen)` ruft `page.screenshot(optionen)` bis zu dreimal auf, mit kurzer Pause (z. B. 500 ms) zwischen den Versuchen. Beim ersten Erfolg endet es mit `true`; nach dem dritten Fehlversuch gibt es `false` zurück, ohne zu werfen.
4. **Aufrufer:** `seiten_browser.mjs`, `seiten_brett.mjs` und `seiten_packliste.mjs` nehmen ihre Vollseitenbilder über `bild`. `seiten_browser.mjs` sammelt Dateien, deren Bild `false` lieferte, in `bilderFehlen` der JSON-Ausgabe (leere Liste, wenn alles gelang oder `RH_BILDER` fehlt).
5. **`test_seite.py`:** Ist `bilderFehlen` nicht leer, ruft der Test `warnings.warn` mit den Dateinamen auf; der Test bleibt grün. Die Warnung steht in der Warnungsübersicht des CI-Logs.

Begründung für Warnung statt Rot: Die Bilder sind Beiwerk zur Durchsicht; ein roter Lauf hielte die Auslieferung für etwas Nebensächliches an. Fehlende Bilder bleiben über die Warnung und die Liste dennoch sichtbar.

## Test Plan

### Automated Tests (TDD RED)

Neuer Test `engine/tests/test_bild_helfer.py` (ruft `bild.mjs` über `node` mit einer gestellten Seite auf, ohne Browser):

- [ ] Test 1 (`test_bild_ohne_fehler_ein_aufruf`): GIVEN eine gestellte Seite, deren `screenshot` gelingt / WHEN `bild` aufgerufen wird / THEN liefert es `true` und `screenshot` wurde genau einmal aufgerufen.
- [ ] Test 2 (`test_bild_erfolg_im_zweiten_versuch`): GIVEN `screenshot` wirft beim ersten Aufruf, gelingt beim zweiten / WHEN `bild` aufgerufen wird / THEN liefert es `true` nach genau zwei Aufrufen.
- [ ] Test 3 (`test_bild_nach_drei_fehlversuchen_false`): GIVEN `screenshot` wirft immer / WHEN `bild` aufgerufen wird / THEN liefert es `false`, wirft nicht und `screenshot` wurde genau dreimal aufgerufen.
- [ ] Test 4 (`test_bild_gibt_optionen_weiter`): GIVEN Optionen mit `fullPage` und `path` / WHEN `bild` aufgerufen wird / THEN erhält `screenshot` dieselben Optionen bei jedem Versuch.

Statische Prüfungen (im selben oder in den bestehenden Testmodulen):

- [ ] Test 5 (`test_stand_skript_wartet_auf_reise_stand_text`): GIVEN `stand_browser.mjs` / WHEN der Quelltext gelesen wird / THEN steht nach `reload` ein `waitForFunction` auf den Text „Neu: Reise-Stand“ mit 15 s Zeitgrenze (damit der Wartepunkt nicht versehentlich verschwindet).
- [ ] Test 6 (`test_packliste_skript_wartet_auf_knopftext`): GIVEN `seiten_packliste.mjs` / THEN steht vor dem Lesen von `knopf0` und von `knopf` nach `reload` ein Wartepunkt auf nicht leeren Text von `.pack-alle`.
- [ ] Test 7 (`test_bilderfehlen_ist_warnung_nicht_rot`): GIVEN eine JSON-Ausgabe von `seiten_browser.mjs` mit nicht leerer `bilderFehlen` / WHEN `test_seite.py` sie auswertet / THEN gibt es eine Warnung und der Test bleibt grün.

Vor der Umsetzung rot: Test 1 bis 6 (Helfer und Wartepunkte fehlen), Test 7.

### Manuelle Prüfung (Erfolgsnachweis)

- Prüfung 8 (Vorlage unverändert): Vergleich des PR-Stands mit `main` zeigt keine Änderung an `engine/vorlage.html`, der Engine, `betrieb/` und `.github/workflows/tests.yml` (kein Dauertest).
- Lastaufbau: beide betroffenen Tests (Chromium und WebKit) mit `-n 4`, zwei Prozesse Dauerlast daneben, 11 Durchläufe, ohne Rot (vorher drei von elf rot).
- Danach mehrere Gesamtläufe `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` ohne Rot.
- CI-Lauf mit `RH_BILDER`: beide Matrix-Jobs grün, Artefakt `bausteine` vorhanden.

## Acceptance Criteria

- **AC-1:** Given der Reise-Stand-Test mit Stub-Server (1 s Verzögerung) / When die Seite nach `reload` den allgemeinen Text „Neue Version des Handbuchs bereit.“ vor „Neu: Reise-Stand 2.“ zeigt / Then wartet `stand_browser.mjs` bis zu 15 s auf den Text „Neu: Reise-Stand“ in `#neu` und liest erst dann; bei Zeitüberschreitung liest es weiter, sodass der Test mit seiner Meldung scheitert (Test 5).
- **AC-2:** Given der Packliste-Test / When nach dem Haken an „Wanderschuhe“ neu gezeichnet wird / Then wartet `seiten_packliste.mjs` vor dem Lesen von `knopf0` auf nicht leeren Text von `.pack-alle`; ebenso vor dem Lesen von `knopf` nach `reload` (Test 6).
- **AC-3:** Given `bild(page, optionen)` mit einem Screenshot, der gelingt / When der Helfer läuft / Then ist das Ergebnis `true` bei genau einem Aufruf; scheitert der erste Versuch und gelingt der zweite, ist das Ergebnis `true` nach zwei Aufrufen (Test 1, 2).
- **AC-4:** Given ein Screenshot, der immer scheitert / When der Helfer läuft / Then gibt er nach drei Fehlversuchen `false` zurück und wirft nicht; die Optionen gehen an jeden Versuch unverändert (Test 3, 4).
- **AC-5:** Given Vollseitenbilder in `seiten_browser.mjs`, `seiten_brett.mjs` und `seiten_packliste.mjs` / When ein Bild endgültig scheitert / Then geht das Skript weiter, und `seiten_browser.mjs` nennt die fehlenden Bilder in `bilderFehlen` der JSON-Ausgabe.
- **AC-6:** Given nicht leere `bilderFehlen` / When `test_seite.py` läuft / Then gibt es eine Warnung (`warnings.warn`) mit den Dateinamen und der Test ist grün, nicht rot (Test 7).
- **AC-7:** Given der PR-Stand / When er mit `main` verglichen wird / Then sind `engine/vorlage.html`, die Engine, `betrieb/` und `.github/workflows/tests.yml` unverändert; die Höchsthöhe von 32000 px bleibt (Prüfung 8).
- **AC-8:** Given der Lastaufbau (beide Tests, `-n 4`, zwei Prozesse Dauerlast, 11 Durchläufe) / When er nach der Umsetzung läuft / Then ist kein Durchlauf rot.
- **AC-9:** Given der Stand nach AC-8 / When mehrere Gesamtläufe mit `-n 3` laufen / Then sind alle grün; der CI-Lauf mit `RH_BILDER` ist grün.

## Risks

- **Wartepunkt verdeckt echten Fehler:** Zeigt die Seite wirklich nie den Stand oder den Knopftext, scheitert der Test weiter, weil bei Zeitüberschreitung weitergelesen wird (kein falsches Grün).
- **Fehlende Bilder bleiben unbemerkt:** Gegenmaßnahme: Warnung mit Dateinamen im CI-Log und `bilderFehlen`. Kehrt die Warnung trotz Wiederholung wieder, Höhe senken und im Issue vermerken.
- **Weitere Ursachen unter Last:** Der Lastaufbau kann andere wackelige Stellen zeigen (z. B. `ergebnis.liste` direkt nach dem Klick auf `[data-stand-liste]`). Dann wird dort nach demselben Muster ein Wartepunkt ergänzt; ohne Last-Rot bleibt es bei den drei Ursachen.
- **Nur in der CI prüfbar:** Das Scheitern des Screenshots lässt sich dort nicht erzwingen; die Zusage stützt sich auf die Helfer-Tests und mehrere CI-Läufe.

## Definition of Done

- [ ] AC-1 bis AC-7 durch Test 1 bis 8 belegt
- [ ] AC-8 und AC-9 durch Lastaufbau, Gesamtläufe und CI-Lauf mit `RH_BILDER` belegt
- [ ] Pflichtprüfungen grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Auslieferung nur über den normalen Weg
- [ ] Issues #550 und #537 erst nach grünem Lauf auf `main` schließen

## Changelog

- 2026-11-13: Initiale Spec (#550, #537)
