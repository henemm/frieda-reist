# Adversary Dialog — fix-654-sw-test-bild
Spec: docs/specs/betrieb/wackelige-browsertests-654.md
Datum: 2026-11-25 09:00

## Checkliste
- [x] **AC-1:** Given `sw.js` wird nach dem neuen Stand einmal abgebrochen / When der Test des Service Workers läuft / Then ist er grün, weil nur der Anstoß wiederholt wird. Test: `engine/tests/test_wackel_654.py::test_sw_einmal_abgebrochen_gruen`
- [x] **AC-2:** Given `sw.js` wird dreimal abgebrochen / When der Test läuft / Then ist er grün innerhalb der Frist von 20 s. Test: `engine/tests/test_wackel_654.py::test_sw_mehrfach_abgebrochen_gruen`
- [x] **AC-3:** Given die neue `sw.js` trägt die Änderungszeit der alten / When der Test läuft / Then ist er grün, weil der Testserver `If-Modified-Since` verwirft und nie mit 304 antwortet. Test: `engine/tests/test_wackel_654.py::test_sw_gleiche_aenderungszeit_gruen`
- [x] **AC-4:** Given `sw.js` wird dauerhaft abgebrochen / When die Frist (im Test verkürzt) abläuft / Then ist der Test rot und die Meldung nennt Fehler von `update()`, Zustände und Anfragen an `sw.js` mit Status; er wird nicht übersprungen. Test: `engine/tests/test_wackel_654.py::test_sw_dauerhaft_abgebrochen_rot_mit_grund`
- [x] **AC-5:** Given der neue Stand ohne den Aufruf von `bilderVergessen` (nur in der gebauten Kopie ersetzt, Ersetzung belegt) / When der Test läuft / Then ist er rot mit `nachher > 0`; die Gegenprobe bleibt rot. Test: `engine/tests/test_wackel_654.py::test_sw_ohne_bilder_vergessen_rot`
- [x] **AC-6:** Given der neue Stand ohne `bilderVergessen`, der sich sofort selbst aktiviert (`skipWaiting` in der Kopie) / When der Test läuft / Then ist er rot, obwohl `nachher == 0`, weil kein `waiting` bei aktivem altem Worker vorliegt; `activate` kann die Prüfung nicht erfüllen. Test: `engine/tests/test_wackel_654.py::test_sw_sofortige_uebernahme_rot`
- [x] **AC-7:** Given `_Server` / When er direkt per HTTP abgefragt wird / Then hat er Warteschlange 128, sendet `Cache-Control: no-cache` und antwortet auch bei `If-Modified-Since` nie mit 304. Test: `engine/tests/test_wackel_654.py::test_server_queue_nocache_kein_304`
- [x] **AC-8:** Given der umgebaute `_Server` / When der Test der Seite (#689) läuft / Then ist er unverändert grün. Test: `engine/tests/test_bilder_eigen.py::test_browser_hochladen_hinweis_nennung_und_loeschen`
- [ ] **AC-9 (OFFEN BIS CI, kein Defekt):** Given der Stand vor der Auslieferung / When der betroffene Test und die Nachweise in der CI in beiden Browsern laufen / Then sind sie in mindestens 3 CI-Läufen grün (`gh run rerun` genügt); ebenso die Pflichtprüfungen `tests (leer)`, `tests (instanz)` und `gitleaks`. Test: von Claude ausgeführt (CI-Läufe), WebKit nur dort messbar
- [x] **AC-10:** Given der Normalfall ohne eingespielten Fehler / When der umgebaute Test vor und nach der Änderung gemessen wird / Then steigt die Laufzeit um weniger als 1 s. Test: von Claude ausgeführt (Laufzeitmessung, Ergebnis im Nachweis)
- [x] **AC-11:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then sind `engine/sw.vorlage.js`, `engine/vorlage.html`, Engine und `betrieb/` unverändert; geändert sind nur die drei genannten Dateien (und Unterlagen unter `docs/`). Test: von Claude ausgeführt (Vergleich mit `main`)

## Dialog

Testlauf (Chromium, WebKit lokal nicht installiert): `docs/artifacts/fix-654-sw-test-bild/adversary-test-output.txt`, 9 passed, 0 failed, 0 übersprungen; dreimal wiederholt mit `-n 8`: 3 x 9 grün. Mutationen jeweils in einer Kopie von engine/, beispiel/, betrieb/ im Scratchpad (nichts unter engine/ im Worktree geändert).

### Runde 1
**Adversary:** Lies die Spec, nicht den Code-Kommentar. Pro AC ein eigener Beweis.
- AC-1 bis AC-3: `test_wackel_654.py:69,78,85` grün (Ausgabe). Beweis, dass sie den Fehler wirklich einspielen: sie prüfen selbst, dass `abgebrochen` genau `anzahl` mal im Protokoll steht (`:63`) und dass die Änderungszeit gleich, der Inhalt aber anders ist (`:90`). Mutation M10 (Server bricht nie ab): AC-1, AC-2, AC-4 rot. Mutation M1 (If-Modified-Since nicht verworfen): AC-3, AC-7 und der Test des Service Workers rot.
- AC-4: Meldung nennt Fehler von update(), Zustände, Anfragen mit Status (`test_bilder_eigen.py:1496` bis 1511); Test `:98` prüft alle drei Teile wörtlich. Nicht übersprungen: `_browser_bereit` überspringt nur ohne Playwright, wie vorher. Mutation M4 (Fehler von update() nicht sammeln): AC-1, AC-2, AC-4 rot.
- AC-5: Ersetzung belegt (`_ersetzen` prüft count == 1, `:51`). Mutation M8 (Aufruf in der Produktdatei weg): Test des Service Workers rot, AC-5 rot (Ersetzung greift nicht mehr).
- AC-6: `:124`; Mutation M5b (Prüfung "alter Worker aktiv" weg): AC-6 rot; M5a (waiting-Prüfung weg): AC-6 und AC-4 rot. Produktmutation M11 (`skipWaiting` in install der echten Vorlage): Test des Service Workers rot.
- AC-7: `:139`; Mutationen M2 (Warteschlange 5), M3 (kein no-cache), M1: jeweils rot.
- AC-8: grün, mit `_Server` ohne eingespielte Fehler.
- AC-10: meine eigene Messung, 4 Wechselläufe: vorher (origin/main) 1,91 bis 1,97 s, nachher 2,14 bis 2,38 s; Zuwachs etwa 0,2 bis 0,4 s, unter 1 s. Nachweis der Gegenseite `laufzeit-messung.txt` stimmt in der Größenordnung (dort 0,01 s).
- AC-11: `git diff origin/main --name-only` ohne `docs/`: genau `engine/tests/seiten_bilder_eigen.mjs`, `engine/tests/test_bilder_eigen.py`, `engine/tests/test_wackel_654.py`. sw.vorlage.js, vorlage.html, betrieb/ unberührt.
- Schwächer als origin/main? Alt: fehler == [], vorher > 0, nachher == 0 (mit bis zu 10 s Nachzählen). Neu: dieselben drei Bedingungen plus waiting/active; gezählt wird einmal nach dem Warten auf `waiting` (install läuft bilderVergessen vor `waiting`, `sw.vorlage.js:46`). Kein Nachzählen mehr, also strenger, nicht schwächer. Der Fehlerzweig `Execution context was destroyed` wiederholt nur die Auswertung (höchstens 5 Mal), nie die Prüfung.
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Nachbohren bei allem, was nur ein Lauf belegt.
- Wiederholung: 3 Durchgänge mit `-n 8` (9 Tests): 27 von 27 grün; Autor meldet 696 von 696 (nicht von mir wiederholt).
- Produktfehler durch wiederholte Anstöße verdeckt? Es wird nur nachgestoßen, wenn `update()` selbst scheitert (`seiten_bilder_eigen.mjs:237`). Mutation M12 (Produkt: Installation scheitert beim ersten Mal, beim zweiten gelingt sie): Test rot (kein wartender Worker), nach rund 31 s, also nicht verdeckt.
- Hängt das Skript? Frist begrenzt `anstossen` per Wettlauf, `neuerWorker` und `aufgeraeumt` prüfen die Frist. Mutation M15 (Server antwortet auf sw.js gar nicht, schläft 25 s statt zu schließen), Frist 3 s: Lauf endet nach 4,7 s. Der Test scheitert dort nur an der erwarteten Meldungsform, es hängt nichts. Obergrenze Gesamtlauf bleibt das bestehende `_node`-Zeitlimit von 600 s (wie auf origin/main). M12 mit Frist 20 s: 31 s.
- Mutation M6 (nicht auf neuen Worker warten, sofort zählen): sechs Tests rot, also keine Zufallstreffer. Mutation M9 (Produkt löscht nichts): Test des Service Workers und AC-1 bis AC-3 rot (AC-5 bleibt rot wie vorgesehen).
- Auffälligkeit, kein Befund: Mutation M2 (Warteschlange 5) macht auch `test_sw_gleiche_aenderungszeit_gruen` rot, nicht nur AC-7; unklar ob Zufall oder Warteschlangeneffekt; AC-7 bleibt verlässlich rot.
- WebKit: lokal nicht ausführbar, daher nicht gemessen; nur über die CI belegbar (AC-9).
**Implementierer:** (nicht beteiligt, Kontextisolation)

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/test_wackel_654.py:69
  Description: Test AC-1 verlangt nur `len(updateFehler) <= 1`. Verbraucht der eigene Abruf des Browsers den einzigen Abbruch, gelingt der erste Anstoß, und der Wiederholungszweig läuft nicht. Der Kommentar nennt das offen.
  Spec requirement: AC-1, Fehler wird gesammelt
  Conflict: Der Nachweis "nur der Anstoß wird wiederholt" ist dann für diesen Lauf nicht belegt; AC-2 und AC-4 decken die Wiederholung aber verlässlich (`anstoesse > 1` verlangt).
  Remediation: Keine nötig; optional einen Abbruch erst nach dem ersten Anstoß einspielen.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/test_bilder_eigen.py:1446
  Description: Die harte Obergrenze eines Laufs ist das unveränderte `_node`-Zeitlimit von 600 s; die Frist von 20 s begrenzt nur den Anstoß und das Warten, einzelne Seitenaufrufe können bis zu 15 s Standardzeit zusätzlich brauchen.
  Spec requirement: Implementation Details 2, harte Frist
  Conflict: Gemessen höchstens rund 31 s im Fehlerfall (M12), also praktisch hart, formal aber nicht auf 20 s begrenzt.
  Remediation: Keine nötig.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_wackel_654.py:69
  Evidence: grün; Mutationen M10 und M4 rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_wackel_654.py:78
  Evidence: grün, dauerMs unter 20000, anstoesse > 1; M10 und M4 rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_bilder_eigen.py:1417
  Evidence: Server verwirft If-Modified-Since; Test `test_wackel_654.py:85` grün, M1 rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/seiten_bilder_eigen.mjs:164
  Evidence: Art sw sammelt Fehler, begrenzt durch Frist; Test `test_wackel_654.py:98` grün, nennt Fehler, Zustände, Anfragen; M4, M5a, M10, M15 verhalten sich wie erwartet.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_wackel_654.py:113
  Evidence: Ersetzung belegt, rot mit nachher > 0 und Meldung beginnt mit "Bild noch im Speicher"; M8 rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/tests/test_bilder_eigen.py:1496
  Evidence: _sw_pruefen verlangt waiting bei aktivem altem Worker; Test `test_wackel_654.py:124` rot wie vorgesehen (nachher == 0 trotzdem); M5a, M5b, M11 rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/tests/test_bilder_eigen.py:1421
  Evidence: Warteschlange 128 (Zeile 1421), no-cache (1401), kein 304 (1417); Test `test_wackel_654.py:139` grün; M1, M2, M3 rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/tests/test_bilder_eigen.py:1461
  Evidence: `test_browser_hochladen_hinweis_nennung_und_loeschen` grün mit dem umgebauten Server.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/tests/seiten_bilder_eigen.mjs:208
  Evidence: eigene Messung vorher 1,91 bis 1,97 s, nachher 2,14 bis 2,38 s (4 Wechselläufe); Zuwachs unter 1 s.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/tests/test_wackel_654.py:1
  Evidence: `git diff origin/main --name-only` außerhalb docs/: nur die drei genannten Testdateien.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`) — in `openspec.yaml` und `.claude/settings*.json` geprüft, kein Eintrag.

## Verdict

AC-9 ist OFFEN BIS CI (3 grüne CI-Läufe, WebKit nur dort messbar) und nicht abgehakt; das ist kein Defekt. Alle übrigen Punkte sind belegt. WebKit-Verhalten (waiting im Zustand `waiting` in WebKit, Risiko der Spec) ist ungemessen.

VERDICT: VERIFIED
(vorbehaltlich AC-9 in der CI; 9 passed, 0 failed, 0 übersprungen lokal in Chromium)

## Geprüfte Dateien

- sha256:e5799dd83a7b99c79f0fb633fc3e906590bfa1bc20a1c36fb8aec781525bb995  engine/tests/seiten_bilder_eigen.mjs
- sha256:10c5885dbb023a7ef38d974bdc52079eca78fca4e1b145b27c4349214dfba54b  engine/tests/test_bilder_eigen.py
- sha256:6ba205604d3527f144cb495c98f2883a07c013cb9bd5680314248a62e8202e6e  engine/tests/test_wackel_654.py

## Prüfbasis

- base: 16ed58c86fbda2cc730abd935107cdb94824ddb2
- blob:3d7d32827e90716a6cc0359e8e9aa5424833101c  engine/tests/seiten_bilder_eigen.mjs
- blob:3dbb3f1624258187fef265b37f38269ce78baa7d  engine/tests/test_bilder_eigen.py
- blob:2509f10ae0cd1b6d2e640e26a263640b7f721b55  engine/tests/test_wackel_654.py

## Geprüfte Dateien

- sha256:e5799dd83a7b99c79f0fb633fc3e906590bfa1bc20a1c36fb8aec781525bb995  engine/tests/seiten_bilder_eigen.mjs
- sha256:10c5885dbb023a7ef38d974bdc52079eca78fca4e1b145b27c4349214dfba54b  engine/tests/test_bilder_eigen.py
- sha256:6ba205604d3527f144cb495c98f2883a07c013cb9bd5680314248a62e8202e6e  engine/tests/test_wackel_654.py

## Prüfbasis

- base: 16ed58c86fbda2cc730abd935107cdb94824ddb2
- blob:3d7d32827e90716a6cc0359e8e9aa5424833101c  engine/tests/seiten_bilder_eigen.mjs
- blob:3dbb3f1624258187fef265b37f38269ce78baa7d  engine/tests/test_bilder_eigen.py
- blob:2509f10ae0cd1b6d2e640e26a263640b7f721b55  engine/tests/test_wackel_654.py
