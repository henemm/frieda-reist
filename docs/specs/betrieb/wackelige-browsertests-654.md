---
entity_id: wackelige-browsertests-654
type: bugfix
created: 2026-11-25
updated: 2026-11-25
status: draft
workflow: fix-654-sw-test-bild
---

# Service-Worker-Test „vergisst gelöschtes Bild“ stabilisieren (#654)

Grundlage: `docs/context/fix-654-sw-test-bild.md` (Kontext, Befunde 1 bis 10, Analyse). Aufbau wie `wackelige-browsertests-599.md` und `wackelige-browsertests-661.md`.

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es ändern sich nur ein Testserver, ein Messskript und ein neuer Nachweistest. Service Worker, Vorlage, Engine und Betrieb bleiben unverändert, der Kern aus ADR-0001 ist nicht berührt.

## Purpose

`test_bilder_eigen.py::test_browser_service_worker_vergisst_geloeschtes_bild[chromium]` scheiterte einmal in der CI (Lauf 44999677401, Versuch 1, Job `tests (instanz)`) mit `{'fehler': [], 'vorher': 2, 'nachher': 2}`. Ein roter Software-Test hält die Übernahme eines neuen Software-Stands an. Der Test soll so umgebaut werden, dass die bekannten, nachgestellten Wege zu `nachher: 2` ohne Produktfehler nicht mehr rot machen, dass die Prüfung nicht schwächer wird (sie wird strenger), und dass ein erneuter Ausfall seinen Grund in der Meldung nennt.

**Ehrlichkeit über die Reichweite:** Der Auslöser in der CI ist nicht bewiesen. Das Protokoll enthält weder den Fehler von `update()` noch die Anfragen an `sw.js`; ohne eingespielten Fehler trat `nachher: 2` lokal in keinem Lauf auf (Befund 6). Der Umbau deckt die nachgestellten Wege ab (Befunde 2, 3, 4) und macht einen erneuten Ausfall erklärbar. Er beweist keine Behebung. Das wird so auch im Pull Request und im Issue gesagt.

## Ursachen (Befunde, nachgestellt oder gelesen)

Gemessen auf macOS mit Chromium 147 und Playwright 1.59.1, in einer Kopie des Skripts (Details im Kontextdokument):

1. Im Normalfall ist das Bild kurz nach `update()` weg (1 bis 2 ms, unter Last bis 271 ms). Der Test wartet bereits bis zu 10 s; „zu früh gemessen“ erklärt `nachher: 2` nicht.
2. Scheitert der Abruf von `sw.js` dauerhaft, entsteht exakt `vorher: 2, nachher: 2` ohne Fehler, weil `.catch(() => {})` in `seiten_bilder_eigen.mjs:185` den Fehler verschluckt. Nach einem einmaligen Abbruch holt Chromium das Update von selbst nach (rund 1,7 s); der Test bleibt dann grün.
3. Antwortet der Server auf `sw.js` mit `304 unverändert` (neue Datei mit der Änderungszeit der alten), entsteht dasselbe Bild, 2 von 2 Läufen; `update()` meldet dabei „ok“. Dass es in der CI dieselbe Sekunde war, ist unbelegt und wenig wahrscheinlich.
4. Der Testserver (`_Server`, `engine/tests/test_bilder_eigen.py:1374-1390`) hat die Standard-Warteschlange von 5. Damit scheiterte die Anmeldung des Workers in 9/150, 13/120, 4/100, 3/100 und 0/100 Läufen, mit 128 in 0/200. In der CI lief die Anmeldung (`vorher: 2`), das Bild ist also ein anderes; Linux behandelt volle Warteschlangen anders.
5. Nicht bestätigt: Rückholen des Bildes aus dem HTTP-Cache des Browsers (0/18, mit `no-cache` 0/6).
6. Im Produkt wurde kein Weg gefunden, der nach der Installation des neuen Workers dauerhaft `nachher: 2` ergibt (Befund 8). Folgerung, nicht Beweis: Im roten Lauf wurde kein neuer Worker installiert.
7. `activate` in `engine/sw.vorlage.js` löscht den ganzen alten Speicher. Übernähme der neue Worker, wäre `nachher == 0` auch ohne `bilderVergessen`. Der heutige Test prüft das nicht (Befund 10).

## Source

- **File:** `engine/tests/test_bilder_eigen.py`, `engine/tests/seiten_bilder_eigen.mjs`, `engine/tests/test_wackel_654.py`
- **Identifier:** `class _Server` und `test_browser_service_worker_vergisst_geloeschtes_bild` (Python), Art `sw` (Skript), neue Nachweise `test_wackel_654`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/tests/test_pwa.py` (Zeilen 105 bis 140) | Muster | Testserver, der `If-Modified-Since` verwirft (#154) und die Anfragen protokolliert |
| `engine/tests/pwa_browser.mjs` (Zeilen 50 bis 91) | Muster | auf Zustände des Workers warten, `update()` ohne Verschlucken; Zeile 74 verschluckt absichtlich (kaputtes Update), dort nichts zu tun |
| `engine/tests/test_wackel_599.py` | Muster | Nachweis unter eingespieltem Fehler, ein echter Fehler bleibt rot |
| `betrieb/vorlagen/nginx-reise.conf` (Zeile 13) | Vorbild | der echte Server sendet `Cache-Control: no-cache` |
| `engine/sw.vorlage.js` (Zeilen 37 bis 84) | Produkt, nur gelesen | `install` ruft `bilderVergessen` vor dem Laden; wird nicht geändert |
| `docs/specs/oberflaeche/bilder-582-eigene-fotos.md`, AC-15 (V15) | Spec | gelöschtes Bild ist nach dem nächsten Laden aus dem Cache entfernt; die Prüfung bleibt in dieser Form, nur strenger |
| Playwright (Chromium, WebKit), Node | extern | Browser für das Messskript; WebKit lokal nicht installiert, gemessen wird es erst in der CI |
| `bauen.py` | Engine | baut die Beispielreise (mit und ohne entferntes Bild) |
| `_Server` und `_node` im Test der Seite (`test_browser_hochladen_hinweis_nennung_und_loeschen`, #689) | Mitnutzer | müssen nach dem Umbau unverändert laufen |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/tests/test_bilder_eigen.py` | MODIFY | `_Server`: `If-Modified-Since` verwerfen, `Cache-Control: no-cache`, Warteschlange (`request_queue_size`) 128, Protokoll (Pfad, Status), einspielbare Fehler für die Nachweise; Test verlangt zusätzlich `waiting` bei aktivem altem Worker und nennt die Diagnose |
| `engine/tests/seiten_bilder_eigen.mjs` | MODIFY | Art `sw` (Zeilen 162 bis 188): nur den Anstoß begrenzt wiederholen, Fehler sammeln, auf den installierten neuen Worker warten, erst dann zählen; Ausgabe um Fehler, Zustände, Zahl der Anstöße erweitert |
| `engine/tests/test_wackel_654.py` | CREATE | Nachweise mit eingespielten Fehlern und Gegenproben (Chromium und WebKit, soweit vorhanden) |

Unverändert: `engine/sw.vorlage.js`, `engine/vorlage.html`, Engine, `betrieb/`, `engine/tests/test_pwa.py`, `engine/tests/pwa_browser.mjs`, Gate-Konfiguration und `.github/workflows/tests.yml`.

### Estimated Changes

- Files: 3 (nur Tests)
- LoC: etwa +220/-15

### Out of Scope

- #656 und #689 (eigene Issues; #689 betrifft dasselbe Skript, `frage()`, und bleibt danach dran). `_Server` und `_node` dürfen den Test der Seite nicht brechen.
- Das schmale Zeitfenster im Produkt aus Befund 9 (ein Abruf des alten Workers, der nach `bilderVergessen` mit 200 endet und das Bild wieder in den alten Speicher legt): nur gelesen, nicht nachgestellt; eigenes Issue #702.
- Jede Änderung am Service Worker oder an der Vorlage.
- Änderungen an der Gate-Konfiguration.

## Implementation Details

Grundsatz: Wiederholt wird nur der Anstoß, nie die Prüfung; geprüft wird weiter `nachher == 0`, und zusätzlich, dass der neue Worker wirklich installiert wurde.

1. **`_Server`.** Verwirft `If-Modified-Since` (wie `test_pwa.py`, #154), sendet `Cache-Control: no-cache` (wie nginx), stellt `request_queue_size` auf 128 und führt ein Protokoll der Anfragen (Pfad, Status). Für die Nachweise lassen sich Fehler einspielen (Abruf von `sw.js` abbrechen: einmal, mehrfach begrenzt, dauerhaft). Ohne eingespielte Fehler liefert er alle Dateien regulär aus (mit Warteschlange 128, `no-cache`, nie 304), damit der Test der Seite (#689) unverändert läuft.
2. **Art `sw` im Skript.** Nach dem Hinlegen des neuen Stands und dem Neuladen wird `update()` angestoßen. Schlägt es fehl, wird der Fehler gesammelt (nicht verschluckt) und der Anstoß wiederholt, hart begrenzt durch eine Frist von **20 s** (im Test für Nachweis c verkürzbar). Danach wird gewartet, bis `waiting` der Registrierung gesetzt ist; das Warten endet sonst, wenn ein neuer Worker `active` geworden ist oder die Frist abläuft. Danach wird genau einmal gezählt (`nachher`), ohne Warteschleife: `bilderVergessen` läuft in `install`, ist also fertig, sobald `waiting` gesetzt ist. Zustände werden nur über `installing`, `waiting` und `active` der Registrierung gelesen (gilt auch für WebKit). Die Ausgabe enthält zusätzlich: gesammelte Fehler von `update()`, Zustände (vor dem neuen Stand und nach dem Warten), Zahl der Anstöße.
3. **Strengere Prüfung im Test.** Verlangt werden: `vorher > 0`; vor dem neuen Stand kein `waiting`; danach ein `waiting`, während der alte Worker noch `active` ist; `nachher == 0`. Damit kann `activate` (löscht den ganzen alten Speicher) die Prüfung nicht erfüllen. Scheitert der Test, nennt die Meldung die Fehler von `update()`, die Zustände und die Anfragen an `sw.js` mit Status. Der Test wird nie übersprungen, auch nicht, wenn der neue Worker nicht kommt. Ablauf und Prüfung liegen in gemeinsamen Hilfsfunktionen in `test_bilder_eigen.py`; Test und Nachweise rufen dieselben auf, „rot“ heißt in den Nachweisen: diese Prüfung wirft `AssertionError` mit dem genannten Inhalt. 
4. **Nachweise (`test_wackel_654.py`).** Je Nachweis ein Test, parametrisiert über `chromium` und `webkit` (soweit der Browser vorhanden ist), mit dem Server aus Punkt 1:
   - a) Abruf von `sw.js` nach dem neuen Stand einmal abgebrochen, und dreimal abgebrochen: grün. Dass der einmalige Abbruch schon heute grün ist (Chromium holt selbst nach), macht ihn zum Wächter.
   - b) neue `sw.js` mit der Änderungszeit der alten: grün (der heutige Server ergäbe 304).
   - c) `sw.js` dauerhaft abgebrochen: rot, und die Meldung nennt Fehler von `update()`, Zustände und Anfragen.
   - d) Gegenprobe Produktfehler: gebaute Kopie des neuen Stands ohne den Aufruf von `bilderVergessen` (Textersetzung nur in der Kopie unter `tmp_path`; der Nachweis prüft, dass die Ersetzung gegriffen hat): rot mit `nachher > 0`.
   - e) Gegenprobe Übernahme: gebaute Kopie ohne `bilderVergessen`, die sich sofort selbst aktiviert (`skipWaiting` in der Kopie): rot, obwohl `nachher == 0`, weil kein `waiting` bei aktivem altem Worker vorliegt. Die Seite lädt bei der Übernahme neu (`controllerchange` in der Vorlage); das Skript muss das ohne Absturz überstehen und das Ergebnis trotzdem ausgeben.
   - f) `_Server` direkt per HTTP geprüft, ohne Browser: Warteschlange 128, `Cache-Control: no-cache`, kein 304 trotz `If-Modified-Since`.
5. **Vorher-Messung (kein Dauer-Test).** Vor dem Umbau wird einmal gemessen und im Nachweis (Pull Request) festgehalten: Bei c) liefert der heutige Ablauf dasselbe Bild wie in der CI (`vorher: 2, nachher: 2`, `fehler: []`); bei d) ist der heutige Test bereits rot.

## Test Plan

### Automated Tests (TDD RED)

Nachweise in `engine/tests/test_wackel_654.py`, der umgebaute Test in `engine/tests/test_bilder_eigen.py`.

- [ ] Test 1 (a, einmal): GIVEN `sw.js` wird nach dem neuen Stand einmal abgebrochen / WHEN der Ablauf der Art `sw` läuft / THEN ist er grün, `nachher == 0`, und jeder gescheiterte Anstoß steht in der Ausgabe (keiner, wenn der eigene Abruf des Browsers den Abbruch verbraucht, Befund 2; dass Fehler gesammelt werden, belegen Test 2 und Test 4).
- [ ] Test 2 (a, mehrfach): GIVEN `sw.js` wird dreimal abgebrochen / WHEN der Ablauf läuft / THEN ist er grün innerhalb der Frist.
- [ ] Test 3 (b): GIVEN die neue `sw.js` hat die Änderungszeit der alten / WHEN der Ablauf läuft / THEN ist er grün; der Server beantwortet nie mit 304.
- [ ] Test 4 (c): GIVEN `sw.js` wird dauerhaft abgebrochen (verkürzte Frist) / WHEN der Ablauf läuft / THEN ist er rot, und die Meldung nennt Fehler von `update()`, Zustände und Anfragen mit Status.
- [ ] Test 5 (d): GIVEN der neue Stand ohne Aufruf von `bilderVergessen` (Ersetzung in der Kopie belegt) / WHEN der Ablauf läuft / THEN ist er rot mit `nachher > 0`.
- [ ] Test 6 (e): GIVEN der neue Stand ohne `bilderVergessen`, der sich mit `skipWaiting` sofort aktiviert / WHEN der Ablauf läuft / THEN ist er rot, obwohl `nachher == 0`, weil kein `waiting` bei aktivem altem Worker vorliegt.
- [ ] Test 7 (f): GIVEN `_Server` / WHEN er direkt per HTTP abgefragt wird (auch mit `If-Modified-Since`) / THEN gilt Warteschlange 128, `Cache-Control: no-cache` und kein 304.
- [ ] Test 8 (Mitnutzer): GIVEN der umgebaute `_Server` / WHEN `test_browser_hochladen_hinweis_nennung_und_loeschen` läuft / THEN ist er unverändert grün.

Der umgebaute Test `test_browser_service_worker_vergisst_geloeschtes_bild` bleibt grün (Chromium und WebKit).

### Messungen

- Laufzeit des umgebauten Tests im Normalfall vorher und nachher (lokal, Chromium).
- Vorher-Messung nach Implementation Details 5, im Pull Request festgehalten.
- CI: der betroffene Test und die Nachweise in mindestens 3 CI-Läufen grün, in beiden Browsern (siehe AC-9).

## Acceptance Criteria

- **AC-1:** Given `sw.js` wird nach dem neuen Stand einmal abgebrochen / When der Test des Service Workers läuft / Then ist er grün, weil nur der Anstoß wiederholt wird.
  Test: `engine/tests/test_wackel_654.py::test_sw_einmal_abgebrochen_gruen`
- **AC-2:** Given `sw.js` wird dreimal abgebrochen / When der Test läuft / Then ist er grün innerhalb der Frist von 20 s.
  Test: `engine/tests/test_wackel_654.py::test_sw_mehrfach_abgebrochen_gruen`
- **AC-3:** Given die neue `sw.js` trägt die Änderungszeit der alten / When der Test läuft / Then ist er grün, weil der Testserver `If-Modified-Since` verwirft und nie mit 304 antwortet.
  Test: `engine/tests/test_wackel_654.py::test_sw_gleiche_aenderungszeit_gruen`
- **AC-4:** Given `sw.js` wird dauerhaft abgebrochen / When die Frist (im Test verkürzt) abläuft / Then ist der Test rot und die Meldung nennt Fehler von `update()`, Zustände und Anfragen an `sw.js` mit Status; er wird nicht übersprungen.
  Test: `engine/tests/test_wackel_654.py::test_sw_dauerhaft_abgebrochen_rot_mit_grund`
- **AC-5:** Given der neue Stand ohne den Aufruf von `bilderVergessen` (nur in der gebauten Kopie ersetzt, Ersetzung belegt) / When der Test läuft / Then ist er rot mit `nachher > 0`; die Gegenprobe bleibt rot.
  Test: `engine/tests/test_wackel_654.py::test_sw_ohne_bilder_vergessen_rot`
- **AC-6:** Given der neue Stand ohne `bilderVergessen`, der sich sofort selbst aktiviert (`skipWaiting` in der Kopie) / When der Test läuft / Then ist er rot, obwohl `nachher == 0`, weil kein `waiting` bei aktivem altem Worker vorliegt; `activate` kann die Prüfung nicht erfüllen.
  Test: `engine/tests/test_wackel_654.py::test_sw_sofortige_uebernahme_rot`
- **AC-7:** Given `_Server` / When er direkt per HTTP abgefragt wird / Then hat er Warteschlange 128, sendet `Cache-Control: no-cache` und antwortet auch bei `If-Modified-Since` nie mit 304.
  Test: `engine/tests/test_wackel_654.py::test_server_queue_nocache_kein_304`
- **AC-8:** Given der umgebaute `_Server` / When der Test der Seite (#689) läuft / Then ist er unverändert grün.
  Test: `engine/tests/test_bilder_eigen.py::test_browser_hochladen_hinweis_nennung_und_loeschen`
- **AC-9:** Given der Stand vor der Auslieferung / When der betroffene Test und die Nachweise in der CI in beiden Browsern laufen / Then sind sie in mindestens 3 CI-Läufen grün (`gh run rerun` genügt); ebenso die Pflichtprüfungen `tests (leer)`, `tests (instanz)` und `gitleaks`.
  Test: von Claude ausgeführt (CI-Läufe), WebKit nur dort messbar
- **AC-10:** Given der Normalfall ohne eingespielten Fehler / When der umgebaute Test vor und nach der Änderung gemessen wird / Then steigt die Laufzeit um weniger als 1 s.
  Test: von Claude ausgeführt (Laufzeitmessung, Ergebnis im Nachweis)
- **AC-11:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then sind `engine/sw.vorlage.js`, `engine/vorlage.html`, Engine und `betrieb/` unverändert; geändert sind nur die drei genannten Dateien (und Unterlagen unter `docs/`).
  Test: von Claude ausgeführt (Vergleich mit `main`)

## Risks

- **Auslöser nicht bewiesen:** Der Umbau beweist keine Behebung. Tritt der Ausfall erneut auf, nennt die Meldung nun Fehler, Zustände und Anfragen; die Ursache wird dann nach dem Muster ergänzt und im Issue vermerkt.
- **`waiting` nicht immer erreicht:** Ob der neue Worker nach dem Neuladen in beiden Browsern immer im Zustand `waiting` ankommt, ist noch zu messen. Wird er dort doch aktiv, braucht die Prüfung eine andere Form; sie wird nicht weggelassen. In diesem Fall geht die Spec zurück in die Abstimmung.
- **WebKit lokal nicht gemessen:** WebKit ist lokal nicht installiert; dort gilt erst die CI. Vor dem Ausliefern laufen beide Browser mehrfach in der CI (AC-9).
- **Wiederholter Anstoß kann einen flüchtigen Installationsfehler des Produkts überdecken:** Deshalb stehen die Zahl der Anstöße und jeder Fehler in der Ausgabe und in der Meldung bei Rot. Wiederholt wird nie die Prüfung, nur der Anstoß, hart begrenzt nach Zeit.
- **Schwächere Prüfung unbemerkt:** Die Gegenproben (AC-5, AC-6) sind der Wächter; sie zeigen, dass ein Produktfehler und eine Übernahme ohne Entfernen rot bleiben.
- **Mitnutzer `_Server`:** Der Test der Seite (#689) nutzt denselben Server; AC-8 sichert ab, dass er unverändert läuft.
- **Laufzeit:** Der Normalfall wartet weiter auf Zustände statt auf feste Zeit; Zuwachs unter 1 s (AC-10). Die Frist von 20 s gilt nur im Fehlerfall.

## Definition of Done

- [ ] AC-1 bis AC-8 durch Tests belegt, RED am heutigen Stand vorher gezeigt, Vorher-Messung im Nachweis festgehalten
- [ ] AC-9: betroffener Test und Nachweise in mindestens 3 CI-Läufen grün, beide Browser, Pflichtprüfungen grün
- [ ] AC-10 und AC-11 durch Laufzeitmessung und Vergleich mit `main` belegt
- [ ] Pull Request und Issue #654 sagen ausdrücklich, dass der Auslöser in der CI nicht bewiesen ist und der Umbau keine Behebung beweist
- [ ] Auslieferung nur über den normalen Weg (Pull Request, grüne Pflichtprüfungen, Vorspulen)
- [ ] Issue #654 erst nach grünem Lauf auf `main` schließen

## Changelog

- 2026-11-25: Initiale Spec (#654)
