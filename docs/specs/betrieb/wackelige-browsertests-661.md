---
entity_id: wackelige-browsertests-661
type: bugfix
created: 2026-11-24
updated: 2026-11-24
status: draft
workflow: fix-661-seitenwechsel-warten
---

# Rundgang wartet nach Seitenwechsel auf die neue Ansicht (#661, #664)

Grundlage: `docs/context/fix-661-seitenwechsel-warten.md` (Kontext, Analyse, Ursachen). Aufbau wie `wackelige-browsertests-599.md`.

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es ändern sich nur Testwerkzeuge (Rundgang, Verzögerungshülle, Nachweistest). Seite, Vorlage, Engine und Betrieb bleiben unverändert, der Kern aus ADR-0001 ist nicht berührt.

## Purpose

Der Rundgang `seiten_browser.mjs` wird unter Last zufällig rot (#661: Absturz im Prüfschritt der Behälter; #664: gespeicherte Ansicht `1200#V-01` zeigt den falschen Tag), obwohl die Seite keinen Fehler hat. Er soll nach jedem Seitenwechsel warten, bis die Seite die neue Ansicht gezeichnet hat, und dabei echte Fehler weiterhin rot lassen. Ein roter Software-Test hält die Übernahme eines neuen Software-Stands an.

## Ursachen

Belegt im Kontextdokument:

1. `location.hash = …` löst `hashchange` erst in einer späteren Aufgabe der Seite aus; `route()` zeichnet im Hörer synchron. Feste 15 ms Node-Zeit nach dem Setzen garantieren das nicht. Betroffen sind vier Stellen in `engine/tests/seiten_browser.mjs` (Zeilen 36, 73, 208, 225).
2. #661: Bei 1300 px ist die letzte Route `V-03` (Heimat `T-02`, dort steht der geöffnete Vergleich `V-02`). Ist noch `T-03` (Heimat von `V-06`) gezeichnet, gibt es `[data-vgl="V-02"]` nicht, `box` ist null und das Skript stürzt ab (Zeile 216).
3. #664: `1200#V-01` enthält noch den Tag `T-03` statt `T-05`.
4. Nachgestellt mit Chromium und der Beispielreise: `hashchange` nur für `#V-03` um 200 ms verzögert ergibt den Absturz, nur für `#V-01` die falsche Ansicht. Werden alle Wechsel um 150 ms verzögert, weichen 72 von 180 Ansichten ab, das Skript endet aber mit 0: auch grüne Läufe können die falsche Ansicht gemessen haben.

Für Nutzer ist das kein Fehler; die Seite zeichnet auf langsamen Geräten nur etwas später.

## Source

- **File:** `engine/tests/seiten_browser.mjs`, `engine/tests/verzoegerung.mjs`, `engine/tests/test_wackel_599.py`
- **Identifier:** neuer Helfer `gehe(p, h)` in `seiten_browser.mjs`, neues Feld `hashchange` (und `hash`) in `RH_VERZOEGERN`, neue Tests in `test_wackel_599.py`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| Playwright (Chromium, WebKit), Node | extern | Browser für den Rundgang; WebKit lokal nicht installiert, Beleg dafür kommt aus der CI |
| `route()` (`engine/vorlage.html`, Zeile 6640) und `hashchange`-Hörer (Zeile 6757) | Vorlage | zeichnet die Ansicht; wird nur gelesen |
| `hoehe()` in `seiten_browser.mjs` (#599) | Muster | Hörer vor der Änderung einhängen, danach auf das Ereignis warten |
| `engine/tests/verzoegerung.mjs` (#599) | Test-Hülle | künstliche Verzögerung je Feld in `RH_VERZOEGERN` |
| `engine/tests/test_seite.py` | Test | startet den Rundgang dreimal (Zeilen 48, 135, 164) und prüft die gespeicherten Ansichten (Zeile 94: #664); bleibt unverändert |
| `engine/tests/test_bild_helfer.py` | Test | liest den Quelltext von `seiten_browser.mjs`; muss grün bleiben |
| gebaute Beispielreise | Testdaten | Grundlage des Rundgangs (erfunden) |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/tests/seiten_browser.mjs` | MODIFY | Helfer `gehe(p, h)`; ersetzt an den vier Stellen Hash setzen und `waitForTimeout(15)` |
| `engine/tests/verzoegerung.mjs` | MODIFY | neues Feld `hashchange` (Hörer an `window` laufen später), optional nur für einen bestimmten Hash über das Feld `hash` |
| `engine/tests/test_wackel_599.py` | MODIFY | Nachweise unter verzögertem Seitenwechsel, Test für echten Fehler, Prüfung am Quelltext |

Unverändert: `engine/vorlage.html`, Engine, `betrieb/`, `engine/tests/test_seite.py` und `engine/tests/test_bild_helfer.py`. Die Erwartungen in `test_seite.py` werden nicht gelockert.

### Estimated Changes

- Files: 3
- LoC: etwa +110/-10

### Out of Scope

- Andere Messskripte mit festen Wartezeiten nach dem Wechsel, am knappsten `sprachen_rundgang.mjs` (12 ms, Zeile 84); eigenes Issue, falls sie wackeln.
- Feste Wartezeiten in `seiten_browser.mjs` außerhalb der vier Wechsel.
- Änderung der Vorlage.

## Implementation Details

Grundsatz: auf das Ereignis warten, an dem die Seite hängt, nie auf einen bestimmten Inhalt, damit eine falsch gezeichnete Ansicht rot bleibt.

1. **Helfer `gehe(p, h)`** (`seiten_browser.mjs`). In der Seite wird zuerst ein einmaliger Hörer für `hashchange` eingehängt (vor dem Setzen), dann `location.hash = h` gesetzt und auf das Ereignis gewartet. Der Hörer der Vorlage ist früher angemeldet und läuft daher davor. Danach folgen zwei `requestAnimationFrame`.
2. **Gleicher Hash.** Ändert sich die Adresse nicht (erste Route `""`, erneuter Wechsel auf dieselbe), kommt kein Ereignis. Ob sie sich geändert hat, zeigt der Vergleich von `location.href` vor und nach dem Setzen. Ohne Änderung wird nicht auf das Ereignis gewartet, der Hörer entfernt (bleibt er unter `verzoegerung.mjs` hängen, weil dort eine Hülle angemeldet ist, schadet das nicht: er gilt nur einmal und ändert nichts an der Seite), und es werden nur die zwei Bilder abgewartet.
3. **Wurf in `route()`.** Wirft `route()`, endet das Warten trotzdem (das Ereignis ist ausgelöst, der Hörer der Vorlage hat geworfen); `pageerror` meldet den Fehler wie bisher.
4. **Alle vier Stellen** (Zeilen 36, 73, 208, 225) rufen `gehe(p, h)` auf; kein `location.hash = h` mit `waitForTimeout(15)` bleibt.
5. **`verzoegerung.mjs`.** Neues Feld `hashchange` (Millisekunden): Hörer für `hashchange` an `window` laufen so viel später; optional nur für einen bestimmten Hash über das Feld `hash` (z. B. `V-03`). Der Hörer von `gehe()` ist selbst ein Hörer an `window` und wird um dieselbe Zeit verzögert; die Anmeldereihenfolge bleibt erhalten, das bildet ein spät eintreffendes Ereignis nach.
6. **Erprobung** (Chromium, Beispielreise, 180 Ansichten je Lauf, Abweichungen gegen den eigenen Lauf ohne Verzögerung):

   | Ablauf | 0 ms | 40 ms | 150 ms | nur `#V-03` 200 ms |
   |--------|------|-------|--------|--------------------|
   | heute (15 ms) | Basis | 57 | 72 | Absturz (`parentElement` null) |
   | warten auf `hashchange` | 0 | 9 | 27 | 2, kein Absturz |
   | `hashchange` und zwei Bilder | 0 | 0 | 0 | 0, kein Absturz |

   Nur die letzte Fassung genügt.
7. **Nachweis eines echten Fehlers (Test 3), ohne Änderung der Vorlage.** Der Test baut die Beispielreise in `tmp_path` und ändert nur dort die gebaute Seite: Der Aufruf `route();` im `hashchange`-Hörer (Zeile 6757 der Vorlage) wird durch Textersetzung zu „bei `#E-02` werfen, bei `#V-01` nichts zeichnen, sonst `route()`“. Der Test prüft, dass die Ersetzung genau einmal gegriffen hat. Ein Lauf deckt beide Fälle ab: Der Wurf steht in `fehler` der Ausgabe; `dom["1200#V-01"]` erfüllt die Erwartung aus Test 2 nicht (die Prüfung in `test_seite.py` wäre also rot); das Skript endet vor der Frist des Tests.

## Test Plan

### Automated Tests (TDD RED)

Alle in `engine/tests/test_wackel_599.py`, Chromium und WebKit parametrisiert (`BROWSER`), soweit der Browser vorhanden ist. Gezielte Verzögerung einzelner Wechsel statt aller, um die Laufzeit zu begrenzen (alle Wechsel um 150 ms: 61 s). RED muss am heutigen Stand belegt sein, ohne Historie (die CI checkt flach aus).

- [ ] Test 1 (#661): GIVEN `hashchange` nur für `#V-03` um 200 ms verzögert / WHEN der Rundgang läuft / THEN gibt es keinen Absturz und `behaelter.spalte.vergleich` ist gemessen.
- [ ] Test 2 (#664): GIVEN `hashchange` nur für `#V-01` um 200 ms verzögert / WHEN der Rundgang läuft / THEN zeigt `dom["1200#V-01"]` `V-01` (Heimat `T-05`, nicht `T-03`), geprüft mit den Erwartungen an `V-01` wie in `test_seite.py` (Zeilen 93 bis 96).
- [ ] Test 3 (echter Fehler bleibt rot): GIVEN eine gebaute Seite im `tmp_path`, die bei `#E-02` wirft und bei `#V-01` nichts zeichnet (Abschnitt 7) / WHEN der Rundgang läuft / THEN steht der Wurf in `fehler`, `dom["1200#V-01"]` erfüllt die Erwartung aus Test 2 nicht, und das Skript endet vor der Frist. Nur ein Browser (WebKit, wie der Wächter aus #599; fehlt er lokal, Chromium).
- [ ] Test 4 (gleicher Hash): GIVEN der Quelltext von `gehe` aus `seiten_browser.mjs` (per Muster herausgelesen) in einem kurzen Playwright-Skript auf der gebauten Beispielreise / WHEN zweimal nacheinander auf denselben Hash und einmal von der Startseite auf `""` gewechselt wird / THEN endet jeder Aufruf innerhalb von 5 s, und die Seite zeigt danach die Ansicht dieses Hashes.
- [ ] Test 5 (statisch): GIVEN der Quelltext von `seiten_browser.mjs` / WHEN er gelesen wird / THEN steht kein `location.hash = h` mehr mit `waitForTimeout(15)`, und alle vier Wechsel laufen über `gehe`; gesetzt wird `location.hash` nur noch in `gehe`.

Vor der Änderung rot: Test 1, 2, 4 und 5. Test 3 ist ein Wächter und schon vorher grün.

Dazu: `engine/tests/test_bild_helfer.py` bleibt grün. Scheitert in `test_seite.py` eine Erwartung mit den neuen Ansichten, wird erst geklärt, ob es ein echter Fehler ist (dann Product Owner bzw. eigenes Issue); nie wird die Erwartung oder das Warten angepasst, um grün zu werden.

### Messungen

- Laufzeit: Rundgang ohne Verzögerung vorher und nachher messen. In der Erprobung 18 s mit den zwei Bildern (11 s ohne); der heutige Ablauf ist nicht gemessen.

## Acceptance Criteria

- **AC-1:** Given `hashchange` nur für `#V-03` um 200 ms verzögert / When der Rundgang `seiten_browser.mjs` läuft / Then stürzt er nicht ab und `behaelter.spalte.vergleich` ist gemessen (#661).
  Test: `engine/tests/test_wackel_599.py::test_rundgang_unter_verzoegertem_wechsel_auf_v03`
- **AC-2:** Given `hashchange` nur für `#V-01` um 200 ms verzögert / When der Rundgang läuft / Then enthält `dom["1200#V-01"]` die Ansicht von `V-01` statt `T-03`, mit der Erwartung aus `test_seite.py` (#664).
  Test: `engine/tests/test_wackel_599.py::test_rundgang_unter_verzoegertem_wechsel_auf_v01`
- **AC-3:** Given eine Seite, die bei `#E-02` wirft und bei `#V-01` nichts zeichnet / When der Rundgang läuft / Then steht der Wurf in `fehler`, die Erwartung an `dom["1200#V-01"]` ist verletzt, und das Skript endet vor der Frist; das Warten verdeckt nichts.
  Test: `engine/tests/test_wackel_599.py::test_echter_fehler_im_wechsel_bleibt_rot`
- **AC-4:** Given ein Wechsel auf den bereits gesetzten Hash / When `gehe(p, h)` aufgerufen wird / Then kehrt es innerhalb von 5 s zurück.
  Test: `engine/tests/test_wackel_599.py::test_gleicher_hash_haengt_nicht`
- **AC-5:** Given der Quelltext von `seiten_browser.mjs` / When er gelesen wird / Then steht kein `location.hash` mit `waitForTimeout(15)` mehr und alle vier Wechsel gehen über `gehe`.
  Test: `engine/tests/test_wackel_599.py::test_quelltext_wechsel_ueber_gehe`
- **AC-6:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then sind `engine/vorlage.html`, Engine, `betrieb/`, `test_seite.py` und `test_bild_helfer.py` unverändert, nur die drei genannten Dateien (und diese Spec samt Kontext) sind geändert.
  Test: von Claude ausgeführt (Vergleich mit `main`); `engine/tests/test_bild_helfer.py` und `engine/tests/test_seite.py` laufen grün.
- **AC-7:** Given der Rundgang ohne Verzögerung / When er vor und nach der Änderung gemessen wird / Then dauert ein Rundgang (Chromium, Beispielreise, lokal) höchstens 30 s (Erprobung: 18 s), und beide Werte stehen im Nachweis.
  Test: von Claude ausgeführt (Laufzeitmessung vorher und nachher, Ergebnis im Nachweis)
- **AC-8:** Given der Stand vor der Auslieferung / When die Pflichtprüfungen laufen / Then sind `tests (leer)`, `tests (instanz)` und `gitleaks` grün, ebenso die WebKit-Läufe der CI.
  Test: von Claude ausgeführt (Gesamtlauf `-n 3`) und CI

## Risks

- **Warten verdeckt echten Fehler:** Es wird auf das Ereignis und zwei Bilder gewartet, nie auf einen Sollinhalt; eine falsch gezeichnete Ansicht bleibt in der gespeicherten Ansicht sichtbar (AC-3).
- **Gespeicherte Ansichten ändern sich gegenüber heute** (u. a. `E-01`, `E-02`, `bausteine`), weil heute teils vor dem nächsten Bild gemessen wird (vermutlich „Weiterlesen“, siehe Kommentar in `sprachen_rundgang.mjs`; Inhalt der Abweichungen nicht einzeln geprüft). Die Erwartungen in `test_seite.py` sind mit den neuen Ansichten noch nicht gelaufen. Maßnahme: erst klären, ob echter Fehler (Product Owner bzw. eigenes Issue), nie Erwartung oder Warten anpassen.
- **WebKit lokal nicht installiert:** Der Fehler trat in WebKit der CI auf; der Beleg dafür kommt aus der CI oder nach Installation.
- **Nachweis nicht identisch mit echter Last:** Die Verzögerung stellt die Wackelstelle nach. Tritt danach noch Rot auf, wird die Stelle nach demselben Muster ergänzt.
- **Laufzeit:** Zwei Bilder je Wechsel erhöhen die Laufzeit; Nachweise mit gezielter Verzögerung begrenzen sie.

## Definition of Done

- [ ] AC-1 bis AC-5 durch Tests belegt, RED am heutigen Stand vorher gezeigt
- [ ] AC-6 und AC-7 durch Vergleich mit `main` und Laufzeitmessung belegt
- [ ] AC-8: Pflichtprüfungen grün, ebenso die WebKit-Läufe in der CI (lokal nicht möglich)
- [ ] Auslieferung nur über den normalen Weg (Pull Request, grüne Pflichtprüfungen, Vorspulen)
- [ ] Issues #661 und #664 erst nach grünem Lauf auf `main` schließen

## Changelog

- 2026-11-24: Initiale Spec (#661, #664)
