# Adversary Dialog — fix-602-pytest-tmp-pfade
Spec: docs/specs/betrieb/protokolle-pytest-tmp-602.md
Datum: 2026-11-21 20:09

## Checkliste
- [x] **AC-1:** Given ein Text mit dem pytest-Temp-Ordner und einem Namen, auch ohne `/tmp/`-Schrägstriche oder gekürzt / When die Prüfung läuft / Then wird er gemeldet (Test 1). Test: `engine/tests/test_protokolle_ohne_pfade.py::test_muster_erkennt_pfade`
- [x] **AC-2:** Given die Platzhalter `<benutzer>`, `<user>`, `*` und `...` / When die Prüfung läuft / Then wird nichts gemeldet (Test 2). Test: `engine/tests/test_protokolle_ohne_pfade.py::test_muster_erkennt_pfade`
- [ ] **AC-3:** Given die eingecheckten Dateien unter `docs/artifacts`, `docs/specs`, `docs/context` / When `test_protokolle_ohne_absolute_pfade` läuft / Then meldet er keinen Fund (Test 3), und kein echter Benutzername steht mehr im pytest-Temp-Ordner. Test: `engine/tests/test_protokolle_ohne_pfade.py::test_protokolle_ohne_absolute_pfade`
- [ ] **AC-4:** Given der Stand der Änderung / When die volle Prüfung und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) laufen / Then sind sie grün (Prüfung 6). Test: manuell und CI

## Dialog

### Runde 1
**Adversary:** Test `test_muster_erkennt_pytest_tmp` (Zeile 32-37) statt des in der Spec genannten `test_muster_erkennt_pfade` (Zeile 27): Defekt? Gezielter Lauf der Datei: 3 passed (adversary-test-output.txt). Muster `PYTEST_TMP = pytest-of-\w[\w-]*` (Zeile 10). Randfälle: Name am Zeilenende, Großbuchstaben, Ziffern/Unterstrich werden von `\w[\w-]*` erfasst; `<benutzer>`, `<user>`, `*`, `...` nicht, weil kein Wortzeichen folgt.
**Implementierer:** Beispieltest deckt voll, ohne Schrägstriche, gekürzt und die vier Platzhalter ab (Code reference: engine/tests/test_protokolle_ohne_pfade.py:32). Die Namensabweichung ist nur eine Benennungsabweichung; Spec nachziehen.

### Runde 2
**Adversary:** Bestandsprüfung. Alle 487 geänderten Zeilenpaare in docs/ maschinell verglichen: nach Normalisierung von `pytest-of-…` identisch, keine fremde Änderung; neue Datei test-green-output.txt (13 Zeilen). Suche nach `pytest-of-` ohne Platzhalter: nur Prosa in docs/context/fix-602 (ohne Namen). ABER: docs/artifacts/sicherheit-552-dienstrechte/test-red-output-nachtrag.txt:277 enthält `...-<Name>/pytest-15574/popen-gw2/...`: pytest hat den Ordner mitten in `pytest-of-<Name>` gekürzt, der echte Server-Benutzername steht dort noch im Klartext (Name hier nicht wiederholt). Das Muster erkennt es nicht (kein `pytest-of-`), die Ersetzung hat es nicht erfasst.
**Implementierer:** offen, siehe F001.

## Findings

Finding:
  ID: F001
  Severity: MEDIUM
  Category: spec_violation
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:10
  Description: PYTEST_TMP verlangt die Zeichenfolge `pytest-of-`. Eine von pytest mittig gekürzte Form (`...-<Name>/pytest-NNNN`) wird weder erkannt noch bereinigt; in docs/artifacts/sicherheit-552-dienstrechte/test-red-output-nachtrag.txt:277 steht so der echte Benutzername des Servers im Klartext.
  Spec requirement: AC-3 — kein echter Benutzername mehr im pytest-Temp-Ordner
  Conflict: Der Name ist in einer Kürzungsform noch öffentlich, die Prüfung bleibt grün.
  Remediation: Fundstelle auf `...-<benutzer>/pytest-15574` ändern; mindestens die Zeile bereinigen, optional ein zweites Muster für `-<name>/pytest-\d+`.

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:27
  Description: Die Spec ordnet AC-1/AC-2 `test_muster_erkennt_pfade` zu, geprüft werden sie von `test_muster_erkennt_pytest_tmp` (Zeile 32).
  Spec requirement: AC-1, AC-2 — Testzuordnung
  Conflict: Nur Benennungsabweichung, Verhalten stimmt.
  Remediation: Spec-Zuordnung auf den tatsächlichen Testnamen ändern.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:34
  Evidence: voll, ohne Schrägstriche und gekürzte Form werden gefunden (Test grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:36
  Evidence: die vier Platzhalter werden nicht gemeldet (Test grün).
  Status: CONFIRMED

AC-3: DISPROVEN wegen F001 (kein Confirmation). AC-4: Volle Suite vom Entwickler gemeldet (3454 passed), von mir nicht wiederholt; AMBIGUOUS.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: BROKEN
═══════════════════════════════════════
Finding F001: echter Benutzername bleibt in mittig gekürzter Form (`...-<Name>/pytest-15574`) in docs/artifacts/sicherheit-552-dienstrechte/test-red-output-nachtrag.txt:277.
  Severity: MEDIUM
  Evidence: engine/tests/test_protokolle_ohne_pfade.py:10
  Reproduction: in docs/ per grep nach `/pytest-15574` suchen und Zeile 277 der genannten Datei lesen.
Finding F002 (LOW): Testname in der Spec weicht ab, kein Defekt.
Tests (gezielt): 3 passed, 0 failed, 0 übersprungen. Volle Suite (3454 passed) vom Entwickler, nicht wiederholt.

## Geprüfte Dateien

- sha256:2eab6af23db5a2169c59e333085f8c61885c2c24dfdabeb57c0ffc8a37423830  engine/tests/test_protokolle_ohne_pfade.py

## Prüfbasis

- base: 1c455c21493de9ff025ecc7a42071e827276f780
- blob:70f7fc3328c5454585ede56981035400f031aca1  engine/tests/test_protokolle_ohne_pfade.py
