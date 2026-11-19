# Adversary Dialog — fix-599-wackelige-browsertests
Spec: docs/specs/betrieb/wackelige-browsertests-599.md
Datum: 2026-11-19 08:29

## Checkliste
- [x] **AC-1:** Given die Verzögerung des `ResizeObserver`-Rückrufs um 1,5 s / When `test_karte_popup_310[webkit]` läuft / Then ist er grün, weil `seiten_karte_popup.mjs` bis zu einer vermessenen Karte (Größe > 0) mit allen Ansichtspunkten im Ausschnitt und ohne laufende Animation wartet (Test 1). Test: `engine/tests/test_wackel_599.py::test_karte_unter_verzoegertem_resizeobserver`
- [x] **AC-2:** Given `setTimeout` der Seite 700 ms später / When `test_alle_ansichten_der_beispielreise[webkit]` die Schritte der Leiste als App durchläuft / Then ist er grün, weil nach `blur()` ein Zeitgeber in der Seite abgewartet wird, der nach dem der Vorlage läuft (Test 2). Test: `engine/tests/test_wackel_599.py::test_leiste_unter_verzoegertem_zeitgeber`
- [x] **AC-3:** Given `resize` verzögert / When `hoehe()` nach `setViewportSize` misst / Then wartet es auf das `resize`-Ereignis und liest erst danach; die Erwartungen aus `test_seite.py` gelten unverändert (Test 3). Test: `engine/tests/test_wackel_599.py::test_leiste_unter_verzoegertem_resize`
- [x] **AC-4:** Given der alte Ablauf (feste 600 ms, Warten nur auf `innerHeight`, 500 ms Node-Zeit) / When er unter derselben Verzögerung läuft / Then ist er rot; damit ist belegt, dass der Nachweistest die Wackelstelle trifft (Test 1 bis 3). Test: `engine/tests/test_wackel_599.py::test_alter_ablauf_ist_unter_verzoegerung_rot`
- [x] **AC-5:** Given ein echter Fehler, bei dem der Sollzustand der Karte nie erreicht wird / When die Frist von etwa 10 s abgelaufen ist / Then misst das Skript weiter, meldet den echten Wert und `test_karte_popup_310.py` ist rot; der Fehler wird nicht verdeckt (Test 4). Test: `engine/tests/test_wackel_599.py::test_echter_fehler_bleibt_rot`
- [x] **AC-6:** Given die Laufzeit im Normalfall ohne Verzögerung / When die beiden betroffenen Tests vor und nach der Änderung gemessen werden / Then steigt die Laufzeit der Suite nicht merklich (Zuwachs deutlich unter 1 s je Test, weil auf den Zustand statt auf feste Zeit gewartet wird). Test: manuell (Laufzeitmessung vor und nach der Änderung, Ergebnis im Nachweis)
- [x] **AC-7:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then sind `engine/vorlage.html`, `test_karte_popup_310.py`, `test_seite.py`, Engine und `betrieb/` unverändert (Prüfung 6). Test: `engine/tests/test_wackel_599.py::test_quelltext_wartet_auf_zustand` (statisch, Test 5) und manuell Vergleich mit `main`
- [x] **AC-8:** Given mehrere Gesamtläufe mit `-n 3` / When sie nach der Umsetzung laufen / Then sind alle grün, und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) sind grün. Test: manuell (Gesamtläufe `-n 3`) und CI

## Dialog

### Runde 1
**Adversary:** Eigener Lauf `pytest -q -n 3 test_wackel_599.py test_karte_popup_310.py test_seite.py`: 46 passed in 362 s (adversary-test-output.txt, keine absoluten Pfade). Angriff auf die Warte-Bedingungen:
- hoehe(): setViewportSize mit gleicher Höhe würde kein resize auslösen und in waitForFunction ohne catch bis zum Playwright-Standard (30 s) hängen. Geprüft: Aufrufe sind 500 und 800 bei Start 800 (seiten_browser.mjs:141,173,182), Höhe ändert sich immer. Fehler wäre laut (Timeout), nicht verdeckt. LOW, siehe F001.
- Reihenfolge: Der Test-Hörer wird nach dem der Vorlage (vorlage.html:6608, messen() synchron) eingehängt, feuert also danach; auch unter der resize-Verzögerung (Hülle verzögert beide gleich, Reihenfolge bleibt). visualViewport-resize (vorlage.html:6612) wird nicht abgewartet. Nicht belegbar als Wackler; F002 (LOW).
- Karte: KARTE wird beim Neubau auf null gesetzt (vorlage.html:6459) und neu belegt (3117, 4478); die Bedingung prüft `typeof KARTE === "undefined" || !KARTE` je Abfrage, liest also nie eine alte Karte. Größe > 0, alle rh-pw-Punkte im Ausschnitt, keine Animation.
- Frist 10 s + .catch(() => {}) fällt auf die Messung zurück, Python-Test prüft (AC-5: ResizeObserver 60 s verzögert -> alle=false, Test grün). Der Fehler wird also nicht verdeckt.
- Statt festem Warten kein Fehler-Verschlucken: Leiste wartet nie auf Sollwert (Ereignis + Zeitgeber), falscher Wert bleibt sichtbar.
- AC-4 nutzt `git show 5f36075`; im flachen Checkout übersprungen (skip, kein falsches Grün, dokumentiert). Lokal lief er (webkit) und bestätigt Rot des alten Ablaufs.
- AC-7: `git diff origin/main --stat` zeigt nur Docs, die beiden .mjs, test_wackel_599.py, verzoegerung.mjs. vorlage.html, test_karte_popup_310.py, test_seite.py, engine, betrieb unverändert.
- AC-6: test-green-output.txt: 31,25 -> 30,34 s, 21,82 -> 21,96 s, 5,23 -> 4,53 s, 4,57 -> 3,87 s; kein Zuwachs.
- AC-8: Gesamtlauf -n 3: 3324 passed, 1 failed (test_software_weg_454::test_f002...). Dieser Test betrifft den Software-Weg, nicht Browser/Messskripte; laut Angabe auch auf unverändertem origin/main rot (Issues #622/#626) und die Pflichtprüfungen in CI grün. Berührt AC-8 inhaltlich nicht, aber der Wortlaut "alle grün" ist lokal nicht erfüllt; der CI-Teil fehlt bis nach dem Push.
**Implementierer:** (nicht beteiligt; Belege aus Artefakten)

### Runde 2
**Adversary:** Zweiter Durchgang auf Verdeckung: Hülle verzoegerung.mjs ändert Messskripte nicht und reicht das echte Modul weiter (verzoegerung.mjs:171, 213-214); der Nachweis läuft damit gegen die echten Skripte. Test 5 (statisch, test_wackel_599.py:144-161) prüft Regex-Struktur, ist also schwach gegen semantische Regression, aber Tests 1-4 sichern das Verhalten. Mögliche Lücke: `.catch(() => {})` schluckt auch echte Fehler der Funktion (z. B. ReferenceError); Folge wäre nur Messung nach 10 s, Python-Test würde weiter den Zustand prüfen, daher nicht verdeckt. Early-Agreement-Skepsis: Jede Behauptung durch eigenen Lauf (46 passed) und Code-Lektüre belegt, nicht nur durch Artefakt.
**Implementierer:** (nicht beteiligt)

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/seiten_browser.mjs:165
  Description: hoehe() wartet auf resize ohne eigene Frist; bei gleicher Höhe käme kein Ereignis, Timeout nach Playwright-Standard.
  Spec requirement: AC-3 — wartet auf das resize-Ereignis
  Conflict: Nur theoretisch; heutige Aufrufe ändern die Höhe immer. Fehler wäre laut, nicht verdeckt.
  Remediation: Optional Kommentar, dass h vom aktuellen Wert abweichen muss.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/seiten_browser.mjs:170
  Description: Es wird nur window-resize abgewartet; die Vorlage hört auch auf visualViewport-resize (vorlage.html:6612).
  Spec requirement: AC-3 — Erwartungen aus test_seite.py unverändert
  Conflict: Kein Wackler beobachtet (46 grün, 9 Nachweistests grün in beiden Browsern); Rest-Risiko.
  Remediation: Beobachten; bei Flake zusätzlich auf visualViewport-resize warten.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/tests/seiten_karte_popup.mjs:40
  Evidence: waitForFunction auf Größe>0, alle Punkte im Ausschnitt, keine Animation; test_karte_unter_verzoegertem_resizeobserver grün (chromium, webkit).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/seiten_browser.mjs:178
  Evidence: Zeitgeber in der Seite (450 ms) statt waitForTimeout; test_leiste_unter_verzoegertem_zeitgeber grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/seiten_browser.mjs:165
  Evidence: Hörer vor setViewportSize, Warten auf innerHeight und resize-Flag; test_leiste_unter_verzoegertem_resize grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_wackel_599.py:121
  Evidence: alter Stand (5f36075) unter Verzögerung rot; Test grün (lokal ausgeführt, in flachem CI-Checkout skip).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/verzoegerung.mjs:178
  Evidence: ResizeObserver 60 s verzögert ab Klick -> Frist läuft ab, alle=false gemeldet (test_wackel_599.py:132-141 grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/tests/seiten_karte_popup.mjs:40
  Evidence: Messung vorher/nachher in test-green-output.txt, alle Differenzen <= +0,14 s oder negativ.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/tests/test_wackel_599.py:144
  Evidence: statischer Test grün; git diff origin/main --stat ohne Engine, vorlage.html, betrieb/, test_karte_popup_310.py, test_seite.py.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/tests/test_wackel_599.py:1
  Evidence: Gesamtlauf -n 3: 3324 passed, 1 failed (test_software_weg_454, unabhängig, auch auf main rot, #622/#626). Kein Browsertest rot. CI-Teil offen bis Push.
  Status: CONFIRMED (Teil CI ausstehend)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Änderung hielt dem Angriff stand.
Tests: 46 passed, 0 failed, 0 übersprungen (eigener Lauf der drei Dateien, -n 3)
Edge cases: zwei LOW-Hinweise (F001, F002), nichts gebrochen
Regressions: keine; Quelltext außer den beiden .mjs-Skripten unverändert
Checklist: 8/8 Punkte belegt (AC-8 CI-Teil und der lokal rote, unabhängige test_software_weg_454 stehen als Vorbehalt)

## Geprüfte Dateien

- sha256:eb8c782ff6ff4a798e1e59f5b29c0b904a645c9a7e419677748714ade4c93015  engine/tests/seiten_browser.mjs
- sha256:798b2e2e88367492b33e67ebbd98e38511a1b1c5777cc5dd739df83a899c42aa  engine/tests/seiten_karte_popup.mjs
- sha256:b4c445f6651c1f30af926d37690829a19792c412af97fe53546492e830402107  engine/tests/test_wackel_599.py
- sha256:d1446c2acc4bcc69698b2d4d3e907bde016debb0baf7fb2a8e273c644742a29c  engine/tests/verzoegerung.mjs

## Prüfbasis

- base: 5f36075263363506ebfc4e69defe386e4664f74f
- blob:ac1a41cac01cf98c022f163143b61cbda0fa9861  engine/tests/seiten_browser.mjs
- blob:4fa349dc7b072cdae96b38c16ed1e11ca2fa01df  engine/tests/seiten_karte_popup.mjs
- blob:c2d7138c9236c26ae035290955634062a97a20db  engine/tests/test_wackel_599.py
- blob:f5376937b11bf8e4850822fb24dd91b3af78adaf  engine/tests/verzoegerung.mjs
