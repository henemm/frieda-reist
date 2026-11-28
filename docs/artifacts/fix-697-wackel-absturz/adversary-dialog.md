# Adversary Dialog — fix-697-wackel-absturz
Spec: docs/specs/fast/fix-697-wackel-absturz.md
Datum: 2026-11-28 10:13

## Checkliste
- [x] AC-1: Ein Rundgang-Skript, das mit Rückgabecode ≠ 0 endet, ergibt mit `erwarte_ok=False` eine nicht stimmende Leiste, ohne dass der Test scheitert.
- [x] AC-2: Dasselbe Skript lässt `_leiste` mit dem Standard (`erwarte_ok=True`) weiterhin scheitern (strenger neuer Ablauf).
- [x] AC-3: `test_wackel_599.py` ist vollständig grün (lokal: 3 bestanden, 16 Browsertests übersprungen wegen fehlendem Playwright; Browserteil folgt aus der CI).

## Dialog

### Runde 1
**Adversary:** Beweis für AC-1/AC-2 verlangt. Lauf: `pytest -q -n 3 --basetemp=<scratchpad>/pt-adv engine/tests/test_wackel_599.py` ergibt "3 passed, 16 skipped". Der neue Test `test_absturz_des_alten_ablaufs_zaehlt_als_rot` hat kein Browser-Skip, nur node; er lief also wirklich (3 bestanden enthält ihn). Er prüft mit einem Ersatzskript (exit 1) beide Richtungen: `erwarte_ok=False` ergibt `_leiste_stimmt(None) is False` und der Standard wirft AssertionError.
**Implementierer:** (Diff und Spec geprüft, keine Gegenrede.)

### Runde 2
**Adversary:** Edge Cases.
- Bleiben alle anderen Aufrufer streng? `grep erwarte_ok` zeigt es nur in den Zeilen 71-87 und 165-166 und 176. Die Aufrufer in den Zeilen 146, 154, 218, 228, 242 nutzen den Standard True, also bleibt ein Absturz des neuen Ablaufs rot.
- Rutscht ein Absturz des neuen Ablaufs im alten-Ablauf-Test durch? Dort wird nur das Skript des alten Standes (`alt`) mit `erwarte_ok=False` gestartet. Der neue Ablauf wird im selben Test nicht aufgerufen, seine Leiste prüfen die Tests ab Zeile 143.
- Schwächung von AC-4 aus #599? Ein Absturz des alten Rundgangs ist ein Fehlschlag des alten Ablaufs, gemeint ist "alter Ablauf rot". Ein Zeitüberschreitungsfehler (`subprocess.TimeoutExpired`) wird weiterhin nicht gefangen, und ein Rückgabecode 0 mit kaputter Ausgabe scheitert weiter. Einzige Lockerung: jeder Code ≠ 0, auch ein Fehler im Aufbau (z. B. fehlendes node-Modul, Tippfehler im Skript). Das ist eine Restschwäche, die ein "rot" vortäuschen könnte; sie ist aber durch den Test der Karte (`_karte`, unverändert, Zeile 162) und die Gegenprobe des neuen Ablaufs begrenzt. Als LOW vermerkt.
- `_leiste_stimmt(None)` gibt False statt TypeError, andere Aufrufer übergeben nie None, da nur `erwarte_ok=False` None liefert.
**Implementierer:** Kein Einwand.

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/test_wackel_599.py:79
  Description: `if not erwarte_ok and aus.returncode != 0: return None` wertet jeden Rückgabecode ≠ 0 als "alter Ablauf rot", auch einen Absturz aus anderem Grund als dem Wackel-Symptom (z. B. fehlendes Modul).
  Spec requirement: AC-1 — Absturz zählt als nicht stimmende Leiste
  Conflict: Der Nachweis "alter Ablauf rot" könnte durch eine kaputte Umgebung vorgetäuscht werden; kein Verstoß gegen die Spec, die genau das verlangt.
  Remediation: Optional stderr auf `box.parentElement` prüfen; nicht nötig für die Freigabe.

Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_wackel_599.py:79
  Evidence: Rückgabecode ≠ 0 und erwarte_ok=False ergibt None; `_leiste_stimmt(None)` (Zeile 108) ist False; Test Zeile 176 bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_wackel_599.py:80
  Evidence: Im Standard erreicht der Lauf `assert aus.returncode == 0`; Test Zeile 177-178 erwartet AssertionError und bestand.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_wackel_599.py:165
  Evidence: Lokal 3 bestanden, 0 fehlgeschlagen, 16 übersprungen (Playwright fehlt). Der geänderte Browsertest (Zeilen 162-166) ist lokal nicht ausgeführt; er folgt aus der CI.
  Status: CONFIRMED (lokal, mit Vorbehalt Browserteil)

## Herkunft der Vorbedingungen

Rein testseitige Änderung; es werden keine Produktionsfelder geschrieben. Es gibt keine verdächtigen Zeilen. Die einzige neue Verzweigung (Rückgabecode ≠ 0 mit erwarte_ok=False) wird vom Test `test_absturz_des_alten_ablaufs_zaehlt_als_rot` genau auf diesem Weg ausgelöst.

## Verdict
VERDICT: VERIFIED
Tests: 3 bestanden, 0 fehlgeschlagen, 16 übersprungen (Browsertests, Playwright lokal nicht installiert; CI führt sie aus).
Edge cases: geprüft, nur F001 (LOW).
Regressions: keine; alle anderen Aufrufer nutzen den strengen Standard.
Checklist: 3/3 (AC-3 lokal mit Vorbehalt Browserteil in CI).

## Geprüfte Dateien

- sha256:9519caef1559747ebab0ac4b61774e32e0c0966116f04c843fd23862686bc9db  engine/tests/test_wackel_599.py

## Prüfbasis

- base: 1f2e0dd0109c719c484d1b44cc577daec5945678
- blob:f19554e1395409edfc3cec591b8b246702b04a8d  engine/tests/test_wackel_599.py
