# Mini-Spec: units-meldung-doppelte-liste-306

Issue #306, zweiter Punkt (der erste Punkt, die Serveradresse in der Spec, ist durch 1c97bf8 erledigt). Die Spec `units-abgleich-260.md` ist durch den Spec-Freeze gesperrt und bleibt unverändert.

## Was ändert sich

- `betrieb/units.py`, `installieren()`, Zweig „Hilfsprogramm fehlt“: Es wird nur noch die Meldung ausgegeben (`units helper … is not installed, nothing installed …`), nicht mehr zusätzlich die Liste der Abweichungen (`ausgeben(erg)` entfällt). Ausgang 5 bleibt.
- Grund: `veroeffentlichen.sh` hängt die Ausgabe von `installieren` („Install attempt“) an die Ausgabe von `pruefen` an, und `pruefen` enthält dieselbe Liste bereits. Sie stand daher doppelt in der Meldung.
- `engine/tests/test_units.py`: `test_installieren_ohne_hilfsprogramm_meldet_ausgang_5` prüft zusätzlich, dass die Liste nicht in der Ausgabe steht.

## Was darf sich nicht ändern

- Ausgang 5 und der Wortlaut der Meldung.
- Alle anderen Zweige von `installieren` (nichts zu tun, Fehler beim Installieren, Fehler beim Neustart, Neuprüfung) geben unverändert aus.
- `pruefen` und `veroeffentlichen.sh`.

## Bekannte Folge

Der Fingerabdruck der Meldung (Merker `units-gemeldet`) ändert sich einmalig, weil die Ausgabe kürzer wird: Eine bereits gemeldete Abweichung wird einmal neu gemeldet. Harmlos (eine normale Meldung, kein Ausfall).

## Acceptance Criteria

- AC-1: Fehlt das Hilfsprogramm und gibt es Abweichungen, die es beheben würde, enthält die Ausgabe von `units.py installieren` die Meldung „is not installed“ und keine Zeile der Abweichungsliste; Ausgang 5.
- AC-2: Die Meldung aus `veroeffentlichen.sh` (`pruefen` plus „Install attempt“) enthält jede Abweichung genau einmal.
- AC-3: Die übrigen Zweige von `installieren` verhalten sich unverändert (bestehende Tests grün).
- AC-4: `engine/.venv/bin/python -m pytest -q engine/tests/test_units.py` grün; vor der Änderung ist der erweiterte Test rot.

## Inline-Test

- [ ] `test_units.py::test_installieren_ohne_hilfsprogramm_meldet_ausgang_5`: Ausgang 5, „is not installed“ in der Ausgabe, kein `FR_ZEITZONE` in der Ausgabe (AC-1, AC-4). AC-2 folgt aus AC-1, weil `pruefen` die Liste weiter liefert.
