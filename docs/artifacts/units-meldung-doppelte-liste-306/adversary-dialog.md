# Adversary Dialog — units-meldung-doppelte-liste-306
Spec: docs/specs/fast/units-meldung-doppelte-liste-306.md
Datum: 2026-11-04 18:04

## Checkliste
- [x] AC-1: Fehlt das Hilfsprogramm und gibt es Abweichungen, die es beheben würde, enthält die Ausgabe von `units.py installieren` die Meldung „is not installed“ und keine Zeile der Abweichungsliste; Ausgang 5.
- [x] AC-2: Die Meldung aus `veroeffentlichen.sh` (`pruefen` plus „Install attempt“) enthält jede Abweichung genau einmal.
- [x] AC-3: Die übrigen Zweige von `installieren` verhalten sich unverändert (bestehende Tests grün).
- [x] AC-4: `engine/.venv/bin/python -m pytest -q engine/tests/test_units.py` grün; vor der Änderung ist der erweiterte Test rot.

## Dialog

### Runde 1
**Adversary:** AC-1: Zweig „Hilfsprogramm fehlt“ gibt nach dem Diff nur noch die Meldung aus. Ist `erg` danach toter Code? Beeinflusst das den Ausgang? Gibt es Wege, auf denen `pruefen` die Liste nicht liefert, sodass sie fehlt?
**Implementierer:** Code reference: betrieb/units.py:168 — nur `print(...)` und `return 5`; `erg` wird weiter für `zu_tun` (Zeile 158) und den Zweig „nichts zu tun“ genutzt, also kein toter Code. Ausgang 5 und Wortlaut unverändert. Code reference: betrieb/veroeffentlichen.sh:472 — `aus` kommt aus `pruefen` (Ausgang 3), das die Liste immer enthält; `installieren` wird nur bei rc=3 aufgerufen (Zeile 474-479), `pruefen` liefert dort also vorher die Liste. Hängt die Abweichung nach der Installation noch an (rc≠0), steht sie in `aus` (Zeile 478) plus „Install attempt“ (Zeile 479). Eine verlorene Liste gibt es nicht: Der Weg „Hilfsprogramm fehlt“ erreicht `installieren` nur über rc=3, und die zweite Prüfung in Zeile 478 liefert sie erneut. Code reference: engine/tests/test_units.py:194 — prüft „is not installed“ vorhanden und `FR_ZEITZONE` abwesend, Ausgang 5 (Zeile 191).
**Adversary:** AC-3/AC-4: Rot/Grün belegt?
**Implementierer:** RED-Beleg docs/artifacts/units-meldung-doppelte-liste-306/test-red-output.txt: „1 failed“, Assertion zeigt die doppelte Zeile `probe-konnektor.service: allowed, add ... FR_ZEITZONE`. Eigener Lauf: `pytest -q engine/tests/test_units.py` -> 23 passed. Andere Zweige (betrieb/units.py:176 install failed, :185-187 Neuprüfung) im Diff unberührt (eine Zeile entfernt).

### Runde 2
**Adversary:** Suche nach Duplikaten in den übrigen Pfaden von veroeffentlichen.sh: AC-2 sagt „jede Abweichung genau einmal“. Schlägt das Installieren fehl (Hilfsprogramm Ausgang 1) oder scheitert der Neustart, bleibt die Abweichung bestehen: `installieren` gibt sie in Zeile 186 (`ausgeben(erneut)`) aus, und `pruefen` (Zeile 478) enthält sie ebenfalls. Damit steht sie in „Install attempt“ doppelt.
**Implementierer:** Stimmt, aber außerhalb des Auftrags: Die Spec verbietet ausdrücklich Änderungen an den übrigen Zweigen („Was darf sich nicht ändern“), und der Issue-Punkt betrifft nur den Weg „Hilfsprogramm fehlt“. AC-2 ist für diesen Weg erfüllt (Code reference: betrieb/veroeffentlichen.sh:479), für den Weg „Installation scheitert, Abweichung bleibt“ gilt es wortwörtlich nicht (Finding F001, MEDIUM, Folge-Issue). Fingerabdruck: `fp` (veroeffentlichen.sh:482) wird aus `aus` gebildet, `aus` wird kürzer, daher einmalige Neumeldung, wie in der Spec als bekannte Folge vermerkt; der Merker wird nur bei erfolgreichem `fr_melden` geschrieben (Zeile 485-486), kein Meldungsverlust.
**Adversary:** Grenzfälle: Leere Ausgabe von `installieren`?
**Implementierer:** Die Meldung ist immer nicht leer; sonst „no output“ (veroeffentlichen.sh:479). Ausgang 5 wird mit `|| true` verschluckt (Zeile 477), wie vorher.

## Findings
Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/units.py:186
  Description: Nach fehlgeschlagener Installation oder Neustart gibt `installieren` die verbleibende Abweichungsliste aus; veroeffentlichen.sh:478-479 hängt sie an die Prüfung an, in der sie ebenfalls steht.
  Spec requirement: AC-2 — jede Abweichung genau einmal in der Meldung
  Conflict: In diesem Pfad steht die Abweichung doppelt. Die Spec schließt die Änderung aber aus („übrige Zweige unverändert“), AC-2 ist nur für den Weg „Hilfsprogramm fehlt“ belegt.
  Remediation: Folge-Issue: veroeffentlichen.sh soll die Liste aus der Ausgabe von `installieren` nicht anhängen oder `installieren` nur Fehlerzeilen ausgeben lassen. AC-2 in der Spec auf den Weg „Hilfsprogramm fehlt“ eingrenzen.

## Confirmations
Confirmation:
  AC: AC-1
  Code reference: betrieb/units.py:168
  Evidence: Nur Meldung und `return 5`, Test engine/tests/test_units.py:191-194 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: betrieb/veroeffentlichen.sh:479
  Evidence: Für den Weg „Hilfsprogramm fehlt“ liefert `pruefen` die Liste einmal, „Install attempt“ enthält nur die Meldung. Für andere Pfade siehe F001 (außerhalb des Auftrags).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_units.py:184
  Evidence: Der Diff entfernt nur eine Zeile; 23 Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_units.py:194
  Evidence: test-red-output.txt zeigt rot vor der Änderung, eigener Lauf 23 passed.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
**VERIFIED**
mit F001 (MEDIUM, außerhalb des Auftrags, Folge-Issue empfohlen). Tests: 23 passed, 0 failed.

## Geprüfte Dateien

- sha256:5d3b1413427eec090b4a8b5ca9f3ea6b5825599e4c037030ba8f294b8fb5945e  betrieb/units.py
- sha256:561e3ee73b127577bc524bc015a1fed62c07cb675edfb5b1ba0f63dd07e74bc6  betrieb/veroeffentlichen.sh
- sha256:5ab2e9233039b0b1927fb7ba18d937db9db7379b6cc760ef2ba4dd5012ad86fb  engine/tests/test_units.py

## Prüfbasis

- base: fb06deef8c038b9261b08f90305639d07d5a2db8
- blob:a403b991058b64bfb9c760ec21e1be2aa2f916d7  betrieb/units.py
- blob:dc7525c2c6f2a5cb4e394983533a9b0712f7d9a0  betrieb/veroeffentlichen.sh
- blob:6ee820d6787c2965a8837349f50fa7df1114a4b5  engine/tests/test_units.py

## Geprüfte Dateien

- sha256:5d3b1413427eec090b4a8b5ca9f3ea6b5825599e4c037030ba8f294b8fb5945e  betrieb/units.py
- sha256:561e3ee73b127577bc524bc015a1fed62c07cb675edfb5b1ba0f63dd07e74bc6  betrieb/veroeffentlichen.sh
- sha256:5ab2e9233039b0b1927fb7ba18d937db9db7379b6cc760ef2ba4dd5012ad86fb  engine/tests/test_units.py

## Prüfbasis

- base: fb06deef8c038b9261b08f90305639d07d5a2db8
- blob:a403b991058b64bfb9c760ec21e1be2aa2f916d7  betrieb/units.py
- blob:dc7525c2c6f2a5cb4e394983533a9b0712f7d9a0  betrieb/veroeffentlichen.sh
- blob:6ee820d6787c2965a8837349f50fa7df1114a4b5  engine/tests/test_units.py

## Geprüfte Dateien

- sha256:5d3b1413427eec090b4a8b5ca9f3ea6b5825599e4c037030ba8f294b8fb5945e  betrieb/units.py
- sha256:561e3ee73b127577bc524bc015a1fed62c07cb675edfb5b1ba0f63dd07e74bc6  betrieb/veroeffentlichen.sh
- sha256:5ab2e9233039b0b1927fb7ba18d937db9db7379b6cc760ef2ba4dd5012ad86fb  engine/tests/test_units.py

## Prüfbasis

- base: fb06deef8c038b9261b08f90305639d07d5a2db8
- blob:a403b991058b64bfb9c760ec21e1be2aa2f916d7  betrieb/units.py
- blob:dc7525c2c6f2a5cb4e394983533a9b0712f7d9a0  betrieb/veroeffentlichen.sh
- blob:6ee820d6787c2965a8837349f50fa7df1114a4b5  engine/tests/test_units.py
