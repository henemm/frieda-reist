# Adversary Dialog — fix-661-seitenwechsel-warten
Spec: docs/specs/betrieb/wackelige-browsertests-661.md
Datum: 2026-11-24 15:14

## Checkliste
- [x] **AC-1:** Given `hashchange` nur für `#V-03` um 200 ms verzögert / When der Rundgang `seiten_browser.mjs` läuft / Then stürzt er nicht ab und `behaelter.spalte.vergleich` ist gemessen (#661). Test: `engine/tests/test_wackel_599.py::test_rundgang_unter_verzoegertem_wechsel_auf_v03`
- [x] **AC-2:** Given `hashchange` nur für `#V-01` um 200 ms verzögert / When der Rundgang läuft / Then enthält `dom["1200#V-01"]` die Ansicht von `V-01` statt `T-03`, mit der Erwartung aus `test_seite.py` (#664). Test: `engine/tests/test_wackel_599.py::test_rundgang_unter_verzoegertem_wechsel_auf_v01`
- [x] **AC-3:** Given eine Seite, die bei `#E-02` wirft und bei `#V-01` nichts zeichnet / When der Rundgang läuft / Then steht der Wurf in `fehler`, die Erwartung an `dom["1200#V-01"]` ist verletzt, und das Skript endet vor der Frist; das Warten verdeckt nichts. Test: `engine/tests/test_wackel_599.py::test_echter_fehler_im_wechsel_bleibt_rot`
- [x] **AC-4:** Given ein Wechsel auf den bereits gesetzten Hash / When `gehe(p, h)` aufgerufen wird / Then kehrt es innerhalb von 5 s zurück. Test: `engine/tests/test_wackel_599.py::test_gleicher_hash_haengt_nicht`
- [x] **AC-5:** Given der Quelltext von `seiten_browser.mjs` / When er gelesen wird / Then steht kein `location.hash` mit `waitForTimeout(15)` mehr und alle vier Wechsel gehen über `gehe`. Test: `engine/tests/test_wackel_599.py::test_quelltext_wechsel_ueber_gehe`
- [x] **AC-6:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then sind `engine/vorlage.html`, Engine, `betrieb/`, `test_seite.py` und `test_bild_helfer.py` unverändert, nur die drei genannten Dateien (und diese Spec samt Kontext) sind geändert. Test: von Claude ausgeführt (Vergleich mit `main`); `engine/tests/test_bild_helfer.py` und `engine/tests/test_seite.py` laufen grün.
- [x] **AC-7:** Given der Rundgang ohne Verzögerung / When er vor und nach der Änderung gemessen wird / Then dauert ein Rundgang (Chromium, Beispielreise, lokal) höchstens 30 s (Erprobung: 18 s), und beide Werte stehen im Nachweis. Test: von Claude ausgeführt (Laufzeitmessung vorher und nachher, Ergebnis im Nachweis)
- [x] **AC-8:** Given der Stand vor der Auslieferung / When die Pflichtprüfungen laufen / Then sind `tests (leer)`, `tests (instanz)` und `gitleaks` grün, ebenso die WebKit-Läufe der CI. Test: von Claude ausgeführt (Gesamtlauf `-n 3`) und CI [Prüfer: lokaler Teil bewiesen, CI-Teil offen bis nach der Auslieferung]

## Dialog

### Runde 1
**Adversary:** Ansatz: gehe() ist falsch, bis das Gegenteil bewiesen ist. Alles selbst erzeugt, Ausgaben in `docs/artifacts/fix-661-seitenwechsel-warten/adversary-test-output.txt` (Abschnitte in Klammern).

Belege Runde 1 (Tests und Verzögerung):
- Gezielter Lauf Chromium: 41 passed, 0 failed (Abschnitt 1): alle fünf neuen Tests, `test_seite.py`, `test_bild_helfer.py`, `test_protokolle_ohne_pfade.py`.
- Gesamtlauf `-n 3` ohne WebKit: 99 failed, 41 errors, 3247 passed. Alle roten Tests liegen in Betriebs- und Server-Skripten (Linux-Werkzeuge `getent`, `flock`, `shopt globasciiranges` fehlen auf macOS). Am unveränderten Basisstand acfc83c (aus dem Repo exportiert) ebenso 99 + 41, die Namen der roten Tests sind identisch (Abschnitte 2, 3). Kein roter Test in `test_wackel_599.py`, `test_seite.py`, `test_bild_helfer.py`.
- Rundgang unter Verzögerung aller Wechsel: 0 ms (zweiter Lauf) 0 Abweichungen, 40 ms 0, 150 ms 0 von 180 Ansichten, `fehler` leer (Abschnitt 4). Der Rundgang liefert also dieselben Ansichten wie ohne Verzögerung.
- Mutation A (gehe ohne Warten) und A15 (alter Ablauf, 15 ms): Test 1 (`#V-03`, 200 ms) stürzt ab, Test 2 (`#V-01`, 200 ms) liefert die falsche Ansicht (Abschnitt 5). RED-Wirkung der Tests 1 und 2 bewiesen.
- Mutation B (nur Ereignis) und C (Ereignis und ein Bild) bleiben in Tests 1 und 2 grün. B weicht bei allen Wechseln 40 ms in 64, bei 150 ms in 60 Ansichten ab, C in 0. Die zwei Bilder sind also nur durch Test 5 (genau zwei `requestAnimationFrame` im Quelltext) gesichert, nicht durch ein Verhalten. Das widerspricht der Spec-Tabelle ("nur die letzte Fassung genügt") für C, weil ein Bild in Chromium reicht; kein Mangel der Umsetzung (F002).

Randfälle (Abschnitt 7), alle mit Frist 5 s je Schritt: Wechsel auf "" ohne vorhandenen Hash, gleicher Hash zweimal, Hash mit vorangestelltem Gatter, Wechsel auf "" von V-01 aus, Alias `offen` (route() ruft `replaceState` und benennt in `zu-tun` um), Alias nochmals, Hash mit Sonderzeichen, kaputte Prozent-Kodierung (route() wirft `URIError`, `pageerror` meldet, gehe kehrt nach 32 ms zurück), noch offenes Ereignis vor gehe: kein Hänger, keine falsche Ansicht.

**Implementierer:** Kein Implementierer beteiligt (Kontextisolation). Gegenbeleg aus Spec und Kontext: Die Messreihe der Spec (0, 0, 0 bei 0, 40, 150 ms) wurde unabhängig bestätigt; die Spec-Aussage zu C ist nicht reproduzierbar, ohne Folgen für die Abnahme.

### Runde 2
**Adversary:** Runde 2 gegen die Stellen, an denen die Umsetzung noch brechen könnte.

- Wirft route() oder bleibt eine Ansicht ungezeichnet (Test 3): Dieselbe Textersetzung wie im Test auf der gebauten Seite: Wurf steht in `fehler`, `dom["1200#V-01"]` erfüllt `_v01_stimmt` nicht, das Skript endet nach 12 bis 19 s (Abschnitt 6). Mutation D (gehe wartet auf geänderten Seiteninhalt, ohne Frist) hängt: Frist abgelaufen nach 90 s, der Test mit Frist 300 s würde rot. Test 3 erkennt also sowohl das Verdecken (Inhalt) als auch ein hängendes Warten. Mutation A (ohne Warten) besteht Test 3 erwartungsgemäß; er schützt nicht gegen fehlendes Warten, das tun Tests 1, 2, 5.
- Änderung an `zeitgeber` (nur noch ab 20 ms): Das Skript vor #599 (Stand 5f36075) bleibt mit der neuen Hülle unter `zeitgeber 700` rot (`_leiste_stimmt` False, app.zu 488 statt 788), ohne Verzögerung grün; das ausgelieferte Skript bleibt grün (Abschnitt 8). Der Nachweis aus #599 ist nicht entwertet. Das Feld wird nur in `test_wackel_599.py` verwendet (Suche im Ordner `engine/tests`).
- Hash-Filter und Hörerreihenfolge in der Hülle: `trifft()` entkodiert `newURL`; der Hörer von gehe wird wie der Hörer der Vorlage um dieselbe Zeit verzögert, die Anmeldereihenfolge bleibt (`verzoegerung.mjs:27-35`). Bei gleichem Hash bleibt die Hülle um den entfernten Hörer ohne Folge (Test 4 grün).
- Laufzeit AC-7: vorher 15,2 s, nachher 18,5 s je Rundgang inklusive Bau (drei Läufe im Wechsel), Grenze 30 s (Abschnitt 9).
- AC-6: Gegenüber dem Basisstand acfc83c ändern sich im Code nur die drei genannten Dateien; `engine/vorlage.html`, Engine, `betrieb/`, `test_seite.py`, `test_bild_helfer.py` sind unverändert (Abschnitt 10). Das lokale Zweig-Etikett des Hauptzweigs ist älter als der Basisstand und würde fremde Änderungen zeigen.
- Schwachstelle gehe: Hat sich die Adresse geändert, kommt aber kein `hashchange` (denkbar in WebKit bei Wechsel von "keine Fragmentkennung" auf leere), wartet gehe ohne Frist; das Skript hängt bis zur Frist des Aufrufers (600 s). Chromium zeigt das nicht (Adresse bleibt gleich). Test 4 prüft genau diesen Schritt, aber in WebKit nur in der CI (F001).
- AC-8: Lokal nicht beweisbar; erst nach Auslieferung und CI.

**Implementierer:** Kein Implementierer beteiligt. Offene Punkte gehen an den Auslieferer: CI mit WebKit abwarten; F001 beobachten.

## Befunde (Structured Findings)

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/seiten_browser.mjs:13
  Description: gehe(p, h) wartet bei geänderter Adresse ohne Obergrenze auf `hashchange`; kommt das Ereignis nie, bleibt `p.evaluate` offen und der Rundgang hängt bis zur Frist des Aufrufers.
  Spec requirement: AC-4 — gehe kehrt bei gleichem Hash innerhalb von 5 s zurück (für den Fall geänderter Adresse ohne Ereignis keine Aussage)
  Conflict: In Chromium nicht auslösbar (alle Randfälle in Abschnitt 7 kehren zurück). In WebKit ist der Wechsel von "ohne Fragment" auf Leerhash lokal nicht prüfbar; Test 4 deckt ihn ab, aber erst in der CI.
  Remediation: Erst die WebKit-Läufe der CI abwarten. Nur falls sie hängen: Rückfall mit Frist (zum Beispiel nach 2 s ohne Ereignis weiter) in gehe, die einen echten Ausfall nicht verdeckt, weil der Inhalt nicht bewertet wird.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/test_wackel_599.py:259
  Description: Die zwei Bilder nach dem Ereignis sind nur statisch abgesichert (Zählung `requestAnimationFrame` gleich 2). Mutation C (ein Bild) und B (kein Bild) bleiben in den Verhaltenstests 1 und 2 grün; B gibt bei 40 und 150 ms 64 beziehungsweise 60 abweichende Ansichten, nur der Quelltexttest schlägt an.
  Spec requirement: AC-5 — Quelltext prüft, dass alle Wechsel über gehe gehen (Zahl der Bilder nicht gefordert)
  Conflict: Kein Widerspruch zur Spec; die Spec-Aussage "nur zwei Bilder genügen" ist für ein Bild in Chromium nicht reproduzierbar (C: 0 Abweichungen).
  Remediation: Keine Pflicht. Optional ein Verhaltenstest mit allen Wechseln bei 40 ms (dauert rund 30 s), der B erkennt.

## Bestätigungen (Confirmations)

Confirmation:
  AC: AC-1
  Code reference: engine/tests/seiten_browser.mjs:13
  Evidence: `test_rundgang_unter_verzoegertem_wechsel_auf_v03[chromium]` grün (Test in `engine/tests/test_wackel_599.py:197`); Mutation ohne Warten stürzt ab, Original misst `vergleich.breite` 340.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_wackel_599.py:208
  Evidence: `test_rundgang_unter_verzoegertem_wechsel_auf_v01[chromium]` grün; ohne Warten (A_ohne, A15) erfüllt `dom["1200#V-01"]` die Erwartung nicht; mit gehe ist `_v01_stimmt` wahr, und 0 Abweichungen bei 0, 40, 150 ms für alle Wechsel.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_wackel_599.py:216
  Evidence: `test_echter_fehler_im_wechsel_bleibt_rot[chromium]` grün; eigener Lauf: Wurf in `fehler`, V-01 nicht erfüllt, Skript endet; eine Mutation mit hängendem Warten (D) läuft in die Frist.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_wackel_599.py:231
  Evidence: `test_gleicher_hash_haengt_nicht[chromium]` grün; eigene Randfälle (Abschnitt 7) alle unter 40 ms zurück; in WebKit offen bis zur CI (F001).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_wackel_599.py:259
  Evidence: `test_quelltext_wechsel_ueber_gehe` grün; vier `await gehe(p, h)` an `seiten_browser.mjs:48, 84, 218, 234`, kein `waitForTimeout(15)`; die Mutationen B und C lassen die Zählung der Bilder rot werden.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/tests/verzoegerung.mjs:26
  Evidence: Gegenüber dem Basisstand acfc83c ändern sich im Code nur `seiten_browser.mjs`, `verzoegerung.mjs`, `test_wackel_599.py`; `test_seite.py` und `test_bild_helfer.py` laufen grün. Die Änderung `zeitgeber` ab 20 ms entwertet #599 nicht (Skript vor #599 bleibt rot).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/tests/seiten_browser.mjs:13
  Evidence: Rundgang vorher 15,2 s, nachher 18,5 s (je drei Läufe, inklusive Bau); Grenze 30 s.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/tests/test_wackel_599.py:197
  Evidence: Lokaler Teil: Gesamtlauf, alle roten Tests (99 + 41) sind umgebungsbedingt und am unveränderten Stand identisch. Der Teil der CI (tests (leer), tests (instanz), Prüfung auf Geheimnisse, WebKit) ist ausdrücklich offen und erst nach der Auslieferung beweisbar.
  Status: CONFIRMED (lokaler Teil); CI offen

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hat den Prüfversuch überstanden. AC-8 (CI mit WebKit) ist nicht vor der Auslieferung beweisbar und bleibt als offener Auslieferungspunkt stehen.
Tests: 41 passed, 0 failed, 0 übersprungen im gezielten Lauf (Chromium); Gesamtlauf 3247 passed, 99 failed und 41 errors, alle umgebungsbedingt (Linux-Werkzeuge fehlen auf macOS) und am unveränderten Basisstand acfc83c mit identischen Namen rot
Edge cases: Gleicher Hash, Alias mit replaceState, Sonderzeichen, kaputte Kodierung, Wurf in route(), offenes Ereignis, Verzögerung 0/40/150 ms für alle Wechsel: keine gebrochen
Regressions: Keine gefunden (#599 bleibt nachgewiesen)
Checklist: 7/8 lokal bewiesen, AC-8 lokal nur zum Teil (CI offen)
Befunde: F001 (LOW, WebKit-Hänger in gehe ohne Frist, nur mit der CI prüfbar), F002 (LOW, zwei Bilder nur statisch abgesichert)

## Geprüfte Dateien

- sha256:48b8bb060616057016bf0cbad587e7285ac6eb3ace96b75bc9ba8d4b23d434c8  engine/tests/seiten_browser.mjs
- sha256:a0b9fa42e2e1b3327a44bf9b7d359fa1ad7289b091beaa8ae5f9c257d357dda1  engine/tests/test_wackel_599.py
- sha256:a9deb10840be1dfc951000b2f8a7e5c4973b48088aebc64545c29d70add72cdb  engine/tests/verzoegerung.mjs

## Prüfbasis

- base: acfc83cbff428b28b063b0276cd323e223a8a636
- blob:3c712447e9239d88547843b7605aad70d2239f9d  engine/tests/seiten_browser.mjs
- blob:395360810315867edde9b28515a7000eeb8dcff8  engine/tests/test_wackel_599.py
- blob:23cd9f44341994e53593b6ea73698be2fbf60670  engine/tests/verzoegerung.mjs
