# Adversary Dialog — fix-602-pytest-tmp-pfade
Spec: docs/specs/betrieb/protokolle-pytest-tmp-602.md
Datum: 2026-11-21 20:12

## Checkliste
- [x] **AC-1:** Given ein Text mit dem pytest-Temp-Ordner und einem Namen, auch ohne `/tmp/`-Schrägstriche oder gekürzt / When die Prüfung läuft / Then wird er gemeldet (Test 1). Test: `engine/tests/test_protokolle_ohne_pfade.py::test_muster_erkennt_pfade`
- [x] **AC-2:** Given die Platzhalter `<benutzer>`, `<user>`, `*` und `...` / When die Prüfung läuft / Then wird nichts gemeldet (Test 2). Test: `engine/tests/test_protokolle_ohne_pfade.py::test_muster_erkennt_pfade`
- [x] **AC-3:** Given die eingecheckten Dateien unter `docs/artifacts`, `docs/specs`, `docs/context` / When `test_protokolle_ohne_absolute_pfade` läuft / Then meldet er keinen Fund (Test 3), und kein echter Benutzername steht mehr im pytest-Temp-Ordner. Test: `engine/tests/test_protokolle_ohne_pfade.py::test_protokolle_ohne_absolute_pfade`
- [x] **AC-4:** Given der Stand der Änderung / When die volle Prüfung und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) laufen / Then sind sie grün (Prüfung 6). Test: manuell und CI

## Dialog

### Runde 1
**Adversary:** Nachbesserung gegen F001/F002 des Runde-1-Dialogs geprüft. Muster Zeile 10: `pytest-of-\w[\w-]*|\.\.\.-\w+/pytest-\d`. Gezielter Lauf der Datei: 3 passed (adversary-test-output.txt). Die frühere Fundstelle in sicherheit-552-dienstrechte/test-red-output-nachtrag.txt:277 trägt jetzt `<tmp>/pytest-of-<benutzer>/pytest-15574/...`, kein Name mehr. Positivbeispiel `...-<name>/pytest-15574/popen-gw2/x` (Zeile 34) wird erkannt, Negativbeispiel `...-<benutzer>/pytest-15574/popen-gw2` (Zeile 35) nicht. Eigener Gegenversuch: `...-<name>/pytest-1` erkannt; `re.../pytest-20203/x` (kein Name, mehrere Stellen in rueckbau-557) nicht gemeldet; `pytest-of-` allein und `pytest-of-<b>` still.
**Implementierer:** Beide Zweige und beide Beispielgruppen decken AC-1 und AC-2 ab (Code reference: engine/tests/test_protokolle_ohne_pfade.py:34). F002 ist eine Benennungsabweichung der eingefrorenen Spec, das Verhalten stimmt.

### Runde 2
**Adversary:** Bestandssuche nach weiteren Formen: Suche nach dem Serverbenutzer als Wort in docs/ leer; ebenso Varianten mit `/`, `-`, `_` davor oder danach. `pytest-of-` ohne Platzhalter steht nur als Prosa oder Musterbeschreibung in docs/context/fix-602-pytest-tmp-pfade.md und der Spec (ohne Namen; vom Test nicht gemeldet, weil `<`, `*` oder `.` folgen). Gekürzte Formen `.../pytest-NNNN` ohne Namen: nur rueckbau-557, kein Name. `/tmp/<Name>`-Pfade mit Benutzernamen: keine. Diff von docs/context: genau drei Zeilen, nur der Benutzername durch „den Betriebsbenutzer“ ersetzt (feat-445 zwei Zeilen, fix-445 eine), Satzbau stimmt, keine Nebenänderung. Fehlalarm: test_protokolle_ohne_absolute_pfade ist über den ganzen eingecheckten Bestand grün, also kein Fehlalarm des neuen Zweigs. Theoretische Restlücke (LOW, keine Fundstelle im Bestand, von der Spec nicht gefordert): eine Kürzung ohne Bindestrich vor dem Namensrest (`...mand/pytest-1`) würde nicht erkannt. AC-4: volle Suite laut Auftrag nicht wiederholt; seither nur Testdatei und Doku geändert, gezielter Lauf grün.
**Implementierer:** Restlücke bewusst offen, nicht im Bestand und nicht gefordert.

## Findings

Keine offenen Findings. F001 aus dem Runde-1-Dialog ist behoben und verifiziert; F002 (LOW, Testname in der Spec) hat keine Verhaltensfolge.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:34
  Evidence: volle Form, Form ohne Schrägstriche, gekürzt mit Namensanfang und mittig gekürzt (`...-<name>/pytest-15574`) werden erkannt; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:35
  Evidence: `<benutzer>`, `<user>`, `*`, `...` und `...-<benutzer>/pytest-...` werden nicht gemeldet; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:10
  Evidence: test_protokolle_ohne_absolute_pfade grün über alle eingecheckten Dateien; eigene Suche nach dem Benutzernamen in docs/ ohne Treffer.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:14
  Evidence: gezielter Lauf 3 passed; volle Suite 3454 passed vom Entwickler vor der Nachbesserung gemeldet (nicht wiederholt), seither nur Testdatei und Doku geändert; CI bei Auslieferung.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 3 passed, 0 failed, 0 übersprungen (gezielt; volle Suite nicht wiederholt)
Edge cases: geprüft, nur theoretische LOW-Restlücke ohne Bestandsfund
Regressions: keine
Checklist: 4/4

## Geprüfte Dateien

- sha256:67a6f048a6e9e034c2ff9be14923a3c0d2dd94b304338c0f758c8b92fab54c02  engine/tests/test_protokolle_ohne_pfade.py

## Prüfbasis

- base: 1c455c21493de9ff025ecc7a42071e827276f780
- blob:9fde4c899a7afc289640f68c4475bc152609e53d  engine/tests/test_protokolle_ohne_pfade.py

## Geprüfte Dateien

- sha256:67a6f048a6e9e034c2ff9be14923a3c0d2dd94b304338c0f758c8b92fab54c02  engine/tests/test_protokolle_ohne_pfade.py

## Prüfbasis

- base: 1c455c21493de9ff025ecc7a42071e827276f780
- blob:9fde4c899a7afc289640f68c4475bc152609e53d  engine/tests/test_protokolle_ohne_pfade.py
