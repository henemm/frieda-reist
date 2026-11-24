# Context: fix-661-seitenwechsel-warten

## Request Summary
Der Rundgang `seiten_browser.mjs` wird unter Last zufällig rot (#661, #664). Er soll nach einem Seitenwechsel warten, bis die
Seite die neue Ansicht gezeichnet hat; echte Fehler bleiben rot.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/tests/seiten_browser.mjs` | vier Stellen `location.hash = h` mit festen 15 ms danach (Zeilen 36, 73, 208, 225); Absturzstelle Zeile 216 |
| `engine/tests/verzoegerung.mjs` | künstliche Verzögerung aus #599; kennt `hashchange` noch nicht |
| `engine/tests/test_wackel_599.py` | Nachweise unter Verzögerung, `_leiste` startet den ganzen Rundgang (daher der Name im CI-Fehler) |
| `engine/tests/test_seite.py` | startet den Rundgang dreimal (Zeilen 48, 135, 164), prüft die gespeicherten Ansichten (Zeile 94: #664) |
| `engine/vorlage.html` | `route()` (Zeile 6640) läuft im Hörer für `hashchange` (Zeile 6757); wird nicht geändert |

## Root Cause (belegt)
- `location.hash = …` löst `hashchange` erst in einer späteren Aufgabe der Seite aus; `route()` zeichnet dort synchron.
  15 ms Node-Zeit garantieren das nicht.
- #661: Bei 1300 px ist die letzte Route `V-03` (Heimat `T-02`, dort steht der geöffnete Vergleich `V-02`). Ist noch `T-03`
  (Heimat von `V-06`) gezeichnet, gibt es `[data-vgl="V-02"]` nicht und `box` ist null.
- #664: `1200#V-01` enthält noch den Tag `T-03` statt `T-05`.
- Nachgestellt mit Chromium und der Beispielreise: `hashchange` nur für `#V-03` um 200 ms verzögert ergibt den Absturz, nur für
  `#V-01` verzögert die falsche Ansicht. WebKit lokal nicht geprüft (nicht installiert).
- Werden alle Wechsel um 150 ms verzögert, weichen 72 von 180 Ansichten ab, das Skript endet aber mit 0: auch grüne Läufe können die
  falsche Ansicht gemessen haben.

## Existing Patterns
- `hoehe()` in `seiten_browser.mjs` (#599): Hörer vor der Änderung einhängen, danach auf das Ereignis warten.
- `verzoegerung.mjs`: je Verzögerung ein Feld in `RH_VERZOEGERN`; Tests zeigen Rot am alten und Grün am neuen Ablauf, dazu eine
  Prüfung am Quelltext.

## Dependencies
- Upstream: Playwright, `verzoegerung.mjs`, gebaute Beispielreise.
- Downstream: `test_seite.py`, `test_wackel_599.py`, `test_bild_helfer.py` (liest den Quelltext).

## Existing Specs
- `docs/specs/betrieb/wackelige-browsertests-599.md` (Vorbild), dazu `-568.md` und `-550-537.md`

## Risks & Considerations
- Gleicher Hash (erste Route `""`, erneuter Wechsel auf dieselbe): kein `hashchange`, das Warten darf dort nicht hängen.
- Wirft `route()` einen Fehler, muss das Warten trotzdem enden (der Skriptfehler wird über `pageerror` gemeldet).
- Aufeinanderfolgende Routen mit derselben Heimat zeichnen dieselbe Ansicht; Warten auf einen bestimmten Inhalt taugt nicht.
- `test_alter_ablauf_ist_unter_verzoegerung_rot` wird in CI übersprungen (flacher Checkout); der Nachweis für RED braucht das nicht.
- Außerhalb des Umfangs: andere Messskripte mit festen Wartezeiten nach dem Wechsel, am knappsten `sprachen_rundgang.mjs` (12 ms,
  Zeile 84).

## Analysis

### Type
Bug (nur Testwerkzeug; die Software selbst bleibt unverändert). Schließt #661 und #664.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/tests/seiten_browser.mjs` | MODIFY | Helfer `gehe(p, h)` statt Hash setzen und 15 ms, an vier Stellen |
| `engine/tests/verzoegerung.mjs` | MODIFY | neues Feld `hashchange` (Hörer an window später; auf Wunsch nur für einen bestimmten Hash) |
| `engine/tests/test_wackel_599.py` | MODIFY | Nachweise unter verzögertem Seitenwechsel, Prüfung am Quelltext |

### Scope Assessment
- Files: 3
- Estimated LoC: +60/-10
- Risk Level: LOW

### Technical Approach
`gehe(p, h)`: in der Seite zuerst einen Hörer für `hashchange` einhängen, dann `location.hash` setzen, auf das Ereignis warten
(der Hörer der Vorlage ist früher angemeldet, läuft also davor), danach zwei `requestAnimationFrame`. Ändert sich die Adresse
nicht (gleicher Hash), kommt kein Ereignis: Hörer entfernen und nur die zwei Bilder abwarten.

Erprobt an einer Wegwerf-Kopie (Chromium, Beispielreise, 180 Ansichten je Lauf), Abweichungen je Ablauf gegen seinen eigenen
Lauf ohne Verzögerung:

| Ablauf | 0 ms | 40 ms | 150 ms | nur `#V-03` 200 ms |
|--------|------|-------|--------|--------------------|
| heute (15 ms) | Basis | 57 | 72 | Absturz (`parentElement` null) |
| warten auf `hashchange` | 0 | 9 | 27 | 2, kein Absturz |
| warten auf `hashchange` und zwei Bilder | 0 | 0 | 0 | 0, kein Absturz |

Nur die letzte Fassung genügt. Laufzeit je Rundgang ohne Verzögerung: 18 s mit den zwei Bildern, 11 s ohne sie
(heutiger Ablauf nicht gemessen).

### Befunde gegen den Plan
- Die gespeicherten Ansichten unterscheiden sich vom heutigen Ablauf (u. a. `E-01`, `E-02`, `bausteine`), weil heute teils vor dem
  nächsten Bild gemessen wird (vermutlich „Weiterlesen“, siehe Kommentar in `sprachen_rundgang.mjs`; Inhalt der Abweichungen nicht
  einzeln geprüft). Die Erwartungen in `test_seite.py` sind mit den neuen Ansichten noch nicht gelaufen.
- WebKit (dort trat der Fehler in CI auf) ist lokal nicht installiert; der Beweis für WebKit kommt aus der CI oder nach Installation.
- Bei den Nachweisen mit Verzögerung die Laufzeit begrenzen: gezielte Verzögerung einzelner Wechsel statt aller (61 s bei 150 ms).

### Dependencies
Keine neuen. `test_bild_helfer.py` liest den Quelltext von `seiten_browser.mjs` (prüfen, dass es grün bleibt).
Lokale Umgebung: Python aus `engine/.venv` des Haupt-Checkouts; Playwright ist dort nicht installiert, in einem Ordner außerhalb
des Repos mit `npm ci` aus `engine/tests/playwright` und über `PLAYWRIGHT_MODUL` angeben.

### Open Questions
Keine. Außerhalb: andere Skripte mit festen Wartezeiten (`sprachen_rundgang.mjs`, 12 ms) als eigenes Issue, falls sie wackeln.
- 2026-11-24 (TDD RED): Test 3 läuft in beiden Browsern statt nur in WebKit; nach der Textersetzung wird die Sicherheitsregel der Seite mit `bauen.skripte_festlegen` neu festgelegt (sonst läuft das geänderte Skript nicht).
- Installation des WebKit-Browsers lokal versucht (Playwright 1.59.1, Ordner außerhalb des Repos): kam nicht voran und wurde abgebrochen. RED lief nur in Chromium (headless shell 1217 aus dem üblichen Playwright-Ordner, `npm ci` außerhalb des Repos, `PLAYWRIGHT_MODUL`); WebKit belegt die CI.
- 2026-11-24 (GREEN): Die Bilder nach `gehe` laufen unter festgestellter Playwright-Uhr als Zeitgeber; `zeitgeber` in `verzoegerung.mjs` verlangsamt deshalb nur noch Zeitgeber ab 20 ms (sonst dauert `test_leiste_unter_verzoegertem_zeitgeber` 349 s statt 20 s). Der Nachweis aus #599 trifft weiter. Die abweichenden Ansichten sind klassiert: nur „weiterlesen“, Klasse `kurz` und die Bausteinseite waren im alten Ablauf noch nicht fertig; Details in `test-green-output.txt`.
