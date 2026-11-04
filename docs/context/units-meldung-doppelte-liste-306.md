# Context: units-meldung-doppelte-liste-306

## Request Summary
Issue #306, zweiter Punkt: Die Meldung „Units differ from the templates“ enthält die Liste der Abweichungen doppelt, wenn das Hilfsprogramm mit Root-Rechten fehlt. Der erste Punkt des Issues (Serveradresse in der Spec) ist durch Commit 1c97bf8 (#302) bereits erledigt.

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/units.py | `installieren()` gibt bei fehlendem Hilfsprogramm die Meldung und dazu `ausgeben(erg)` aus (Ausgang 5) |
| betrieb/veroeffentlichen.sh | `units_abgleichen()` ruft `installieren`, dann `pruefen`, und hängt die Ausgabe von `installieren` als „Install attempt“ an die Ausgabe von `pruefen` |
| engine/tests/test_units.py | `test_installieren_ohne_hilfsprogramm_meldet_ausgang_5` prüft bisher nur den Ausgang |
| docs/specs/fast/units-abgleich-260.md | Spec des Abgleichs (durch Spec-Freeze gesperrt; hier nicht betroffen) |

## Existing Patterns
- `pruefen` gibt die Liste aus, `installieren` ruft nach dem Installieren `pruefen` erneut und gibt dessen Ergebnis aus.
- Fehlerzweige von `installieren` sagen in einer Zeile, was fehlt (`install failed …`, `restart failed …`).

## Dependencies
- Upstream: `pruefen`, `ausgeben`, `ausgang` in units.py.
- Downstream: `veroeffentlichen.sh` (Fingerabdruck der Ausgabe für den Merker `units-gemeldet`, Text der normalen Meldung).

## Existing Specs
- `docs/specs/fast/units-abgleich-260.md` (Ausgang 5: Hilfsprogramm fehlt oder scheitert).

## Risks & Considerations
- Der Fingerabdruck der Meldung ändert sich einmalig, weil die Ausgabe kürzer wird: Eine bereits gemeldete Abweichung wird einmal neu gemeldet. Harmlos (eine normale Meldung).
- Wer `units.py installieren` von Hand ohne Hilfsprogramm aufruft, sieht die Liste nicht mehr; die Meldung verweist auf `units.py pruefen`.

## Analysis

### Type
Bug (kosmetisch, zweiter Punkt von #306; erster Punkt durch 1c97bf8 erledigt)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| betrieb/units.py | MODIFY | Zweig „Hilfsprogramm fehlt“ in `installieren()` (Z. 167–170): `ausgeben(erg)` entfernen; Meldung verweist auf `units.py pruefen` |
| engine/tests/test_units.py | MODIFY | Test prüft zusätzlich, dass die Liste nicht in der Ausgabe steht (im Arbeitsbaum bereits begonnen) |

### Scope Assessment
- Files: 2
- Estimated LoC: +4/-1
- Risk Level: LOW

### Technical Approach
In `installieren()` im Zweig „Hilfsprogramm fehlt“ nur die Meldung ausgeben, `ausgeben(erg)` streichen, Ausgang 5 bleibt. `veroeffentlichen.sh` hängt die Ausgabe von `installieren` als „Install attempt“ an die Ausgabe von `pruefen`, die dieselbe Liste enthält; die Wurzel der Doppelung ist genau dieser Zweig. Alternativ in der Shell kürzen: verworfen, da die Ausgabe von `installieren` in anderen Zweigen (Fehler, Neuprüfung) eigenständig sinnvoll ist.

### Dependencies
- `pruefen`, `ausgeben`, `ausgang` in units.py; Downstream `veroeffentlichen.sh` (Fingerabdruck, Merker `units-gemeldet`).

### Befunde gegen den Plan
Keine. Der Fingerabdruck ändert sich einmalig (eine Abweichung wird einmal neu gemeldet), harmlos.

### Open Questions
- [ ] Keine. Die Spec `units-abgleich-260.md` ist gesperrt und nicht betroffen; der Spec-Punkt (Serveradresse) ist erledigt.
