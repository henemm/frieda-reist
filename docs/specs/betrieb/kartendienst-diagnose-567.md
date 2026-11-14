---
entity_id: kartendienst-diagnose-567
type: bugfix
created: 2026-11-14
updated: 2026-11-14
status: draft
workflow: fix-567-kartendienst-diagnose
---

# Kartendienst-Rückfall beobachtbar machen, Test-Stummel `Kaputt` sauber beenden (#567)

Grundlage: `docs/context/fix-567-kartendienst-diagnose.md` (Kontext, Befund, Analyse) und Issue #567 (Kommentar „Ursachensuche, Stand 2“).

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es kommt nur eine Protokollzeile im Fehlerpfad dazu, dazu ändern sich Tests und die Doku einer Spec. Rückgabewerte, Rückfallverhalten und Oberfläche bleiben unverändert; der Kern aus ADR-0001 ist nicht berührt.

## Purpose

Der Test `test_kartenpunkte_dienstwahl_an_beiden_beispielreisen` war einmal rot (`assert (0 == 1)` bei `len(eigen.anfragen) == 1 and oeffentlich.anfragen == []`) und ließ sich nicht nachstellen. Weil der Wechsel vom eigenen auf den öffentlichen Kartendienst heute ohne jede Spur geschieht, ist nicht erkennbar, warum der eigene Dienst keine Anfrage bekam. Diese Änderung hinterlässt beim Wechsel eine Protokollzeile mit Grund, gibt dem Test aussagekräftige Meldungen und beendet den nachweislich unsauberen Test-Stummel `Kaputt` deterministisch.

## Ursachen / Befund

1. **Stiller Wechsel (Beobachtungslücke).** `overpass_eigen` liefert `None` bei einer Ausnahme (URLError, HTTPException, TimeoutError, OSError, ValueError) und bei einer Antwort ohne Liste `elements`; `overpass_holen` wechselt dann ohne Spur auf den öffentlichen Dienst. Das gilt auch im Betrieb: ein ausgefallener eigener Kartendienst bliebe unbemerkt.
2. **Zusicherung ohne Diagnose.** Die erste Zusicherung des Dienstwahl-Tests trägt keine Meldung. Das rote `0 == 1` sagt nicht, ob der öffentliche Stummel gefragt wurde und welcher Dienst in `a["text"]` steht.
3. **Unsauberer Stummel `Kaputt`.** `schliessen()` ruft nur `close()`. Ein Faden, der in `accept()` blockiert, wird unter Linux dadurch nicht geweckt und bleibt hängen (Fadenzahl im Worker 3 auf 9). Die Leseschleife dreht endlos bei `recv() == b""`. Mögliche Folge, nicht belegt: ein Faden erwischt eine bereits geschlossene und neu vergebene Dateinummer und nimmt Verbindungen eines anderen Sockets an.
4. **Ausgeschlossen:** Cache-Vermutung (`dienst_waehlen` liest `abdeckung.json` bei jedem Aufruf frisch); Aushungern des Vorab-Abrufs (Protokoll des roten Laufs zeigt `Done kartenpunkte_holen 200 in 1.1 s`, keine Zeile `Prefetch … skipped`). In 3 Gesamtläufen `-n 3` und 60 Folgeläufen mit Diagnose-Plugin war nichts rot.

## Source

- **File:** `engine/schreiben.py`, `engine/tests/test_kartendienst.py`, `engine/tests/test_schreiben.py`
- **Identifier:** `overpass_eigen` (Protokollzeile), `overpass_holen`, Stummel `Kaputt`, Test `test_kartenpunkte_dienstwahl_an_beiden_beispielreisen`; Vorbild der Zeile: `kartenpunkte_vorab`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `overpass_abfragen` | function | nutzt `overpass_holen`; Verhalten unverändert |
| `kartenpunkte_vorab` | function | nutzt `overpass_holen`; Verhalten unverändert, Vorbild der Protokollzeile (`sys.stderr.write(... [:LOG_LAENGE])`) |
| `kartendienst.dienst_waehlen`, `kartendienst.abdeckung` | module | Wahl nach Abdeckung, unverändert |
| `LOG_LAENGE` | Konstante | Kürzung der Protokollzeile |
| `docs/specs/betrieb/eigener-kartendienst-444.md` | Spec | AC-6 wird ergänzt |
| `engine/tests/test_protokolle_ohne_pfade.py` | Test | betrifft nur Doku-Nachweise; die Zeile enthält keine Pfade |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/schreiben.py` | MODIFY | `overpass_eigen`: beim Scheitern genau eine Protokollzeile auf stderr |
| `engine/tests/test_kartendienst.py` | MODIFY | `Kaputt` sauber beenden; Rückfall-Tests prüfen die Protokollzeile; neuer Test zum Fadenende |
| `engine/tests/test_schreiben.py` | MODIFY | Dienstwahl-Test: Zusicherungen mit Diagnose-Meldungen |
| `docs/specs/betrieb/eigener-kartendienst-444.md` | MODIFY | AC-6 ergänzen: Rückfall hinterlässt eine Protokollzeile mit Grund |

### Estimated Changes

- Files: 4
- LoC: +60/-10
- Risiko: niedrig (eine zusätzliche Zeile im Fehlerpfad, sonst Tests und Doku)

### Out of Scope

- Textkatalog-Eintrag (die Zeile ist für Personen nicht sichtbar), Alarm über den Meldeweg, Teil-Check in `monitor.sh`. Eine dauerhafte Überwachung des eigenen Kartendienstes wäre ein eigenes Thema und gegebenenfalls ein Folge-Issue.
- Wiederholen oder Lockern des Dienstwahl-Tests.
- Änderung von Rückgabewerten oder Rückfallverhalten von `overpass_eigen` und `overpass_holen`.

## Implementation Details

1. **Protokollzeile in `overpass_eigen`** (nicht in `overpass_holen`, damit jeder der beiden `None`-Fälle seine eigene Begründung trägt). Sie geht auf stderr, ist englisch und einzeilig (Leerraum zusammengezogen), der Fehlertext auf `LOG_LAENGE` gekürzt, nach dem Muster von `kartenpunkte_vorab`:
   - Ausnahme: `Own map service failed (URLError: ...), falling back to public` mit Fehlerart und Text.
   - Antwort ohne Liste `elements`: `Own map service answered without elements, falling back to public`.
   - Keine Adresse des Dienstes in der Zeile (Instanzdetail). Im Erfolgsfall keine Zeile. Rückgabewerte und Rückfallverhalten bleiben unverändert.
2. **Rückfall-Tests** in `test_kartendienst.py` prüfen die Zeile mit `capfd` bzw. `capsys` für: Fehlerantwort (`Kaputt`), nicht erreichbar, Antwort ohne `elements`. Ein Test prüft, dass bei Erfolg keine Zeile entsteht.
3. **Dienstwahl-Test** in `test_schreiben.py`: Die Zusicherungen bekommen Meldungen mit beiden Anfragelisten (`eigen.anfragen`, `oeffentlich.anfragen`), `a["text"]` und dem eingefangenen stderr. Sonst unverändert: keine Wiederholung, kein Lockern.
4. **`Kaputt` deterministisch beenden:** `schliessen()` ruft `shutdown(SHUT_RDWR)` vor `close()`, wartet auf den Faden mit `join` und Frist; die Leseschleife bricht bei `recv() == b""` ab.
5. **Spec 444:** AC-6 in `docs/specs/betrieb/eigener-kartendienst-444.md` wird um „hinterlässt eine Protokollzeile mit Grund“ ergänzt (Teil dieses Vorhabens).

## Expected Behavior

- Scheitert der eigene Kartendienst (Fehler, nicht erreichbar, Nicht-JSON, Antwort ohne `elements`), steht im Dienst-Journal genau eine Zeile mit dem Grund; die Abfrage wird weiter wie bisher vom öffentlichen Dienst beantwortet.
- Antwortet der eigene Dienst gültig (auch mit leerer Trefferliste), entsteht keine Zeile.
- Wird der Dienstwahl-Test noch einmal rot, zeigt die Meldung beide Anfragelisten, den gewählten Dienst und die Protokollzeile; das nächste Rot ist damit erklärbar.
- Nach `schliessen()` läuft kein Faden des Stummels `Kaputt` mehr.

## Test Plan

### Automated Tests (TDD RED)

In `engine/tests/test_kartendienst.py`:

- [ ] Test 1 (`test_rueckfall_fehlerantwort_schreibt_protokollzeile`): GIVEN der eigene Dienst antwortet mit Fehler (Stummel `Kaputt`) / WHEN `overpass_holen` läuft / THEN steht auf stderr genau eine Zeile `Own map service failed (` mit Fehlerart, `falling back to public`, ohne Adresse, höchstens `LOG_LAENGE` lang, einzeilig.
- [ ] Test 2 (`test_rueckfall_nicht_erreichbar_schreibt_protokollzeile`): GIVEN der eigene Dienst ist nicht erreichbar / WHEN `overpass_holen` läuft / THEN steht genau eine Zeile mit Fehlerart und `falling back to public`.
- [ ] Test 3 (`test_rueckfall_ohne_elements_schreibt_protokollzeile`): GIVEN der eigene Dienst antwortet gültig, aber ohne Liste `elements` / WHEN `overpass_holen` läuft / THEN steht genau die Zeile `Own map service answered without elements, falling back to public`.
- [ ] Test 4 (`test_erfolg_schreibt_keine_protokollzeile`): GIVEN der eigene Dienst antwortet gültig (auch mit leerer Trefferliste) / WHEN `overpass_holen` läuft / THEN entsteht keine Zeile über den eigenen Dienst auf stderr.
- [ ] Test 5 (`test_kaputt_beendet_faden_nach_schliessen`): GIVEN der Stummel `Kaputt` mit laufendem Faden, auch mit einem in `accept()` wartenden / WHEN `schliessen()` aufgerufen wird / THEN ist der Faden des Stummels nicht mehr am Leben (`is_alive()` falsch) und `schliessen()` kehrt innerhalb der Frist zurück.

In `engine/tests/test_schreiben.py`:

- [ ] Test 6 (`test_kartenpunkte_dienstwahl_an_beiden_beispielreisen`, geändert): GIVEN der Test mit Diagnose-Meldungen / WHEN er läuft / THEN gelten dieselben Zusicherungen wie bisher, und ihre Meldungen enthalten beide Anfragelisten, `a["text"]` und das eingefangene stderr. Ein Rot-Nachweis der Meldung ist nicht nötig; sie wird im Review gegen den Quelltext geprüft.

Vor der Umsetzung rot: Test 1 bis 3 (keine Zeile), Test 5 (Faden läuft weiter). Test 4 und 6 sind schon vor der Umsetzung grün und sichern das Verhalten.

### Manuelle Prüfung (Erfolgsnachweis)

- Mehrere Gesamtläufe `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` ohne Rot.
- Folgeläufe der Kartentests (`test_kartendienst.py` und Kartentests von `test_schreiben.py`, 4 parallel) ohne Rot.
- Vergleich mit `main`: `overpass_eigen` ändert nur die Protokollzeile, Rückgabewerte und Rückfall bleiben gleich.
- Vor dem Vorspulen laufen die Tests der einbindenden Instanz gegen den Stand (CLAUDE.md); neu ist nur eine Zeile, kein geänderter Text.

## Acceptance Criteria

- **AC-1 (Fehler):** Given der eigene Kartendienst antwortet mit Fehler oder ist nicht erreichbar / When `overpass_holen` läuft / Then steht genau eine Protokollzeile `Own map service failed (<Fehlerart>: <Text>), falling back to public` auf stderr, einzeilig, Fehlertext auf `LOG_LAENGE` gekürzt, ohne Adresse; Rückgabe und Rückfall sind wie bisher
  - Test: `engine/tests/test_kartendienst.py::test_rueckfall_fehlerantwort_schreibt_protokollzeile`, `::test_rueckfall_nicht_erreichbar_schreibt_protokollzeile`
- **AC-2 (Antwort ohne elements):** Given der eigene Dienst antwortet gültig ohne Liste `elements` / When `overpass_holen` läuft / Then steht genau die Zeile `Own map service answered without elements, falling back to public`
  - Test: `engine/tests/test_kartendienst.py::test_rueckfall_ohne_elements_schreibt_protokollzeile`
- **AC-3 (Erfolg ohne Zeile):** Given der eigene Dienst antwortet gültig / When `overpass_holen` läuft / Then entsteht keine Zeile über den eigenen Dienst
  - Test: `engine/tests/test_kartendienst.py::test_erfolg_schreibt_keine_protokollzeile`
- **AC-4 (Stummel endet):** Given der Stummel `Kaputt` / When `schliessen()` aufgerufen wird / Then ist sein Faden danach nicht mehr am Leben und die Leseschleife endet bei `recv() == b""`
  - Test: `engine/tests/test_kartendienst.py::test_kaputt_beendet_faden_nach_schliessen`
- **AC-5 (Diagnose im Dienstwahl-Test):** Given der Dienstwahl-Test wird rot / When die Zusicherung scheitert / Then zeigt die Meldung beide Anfragelisten, `a["text"]` und das eingefangene stderr; die Zusicherungen selbst bleiben unverändert (keine Wiederholung, kein Lockern)
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_dienstwahl_an_beiden_beispielreisen`
- **AC-6 (Spec 444):** Given `docs/specs/betrieb/eigener-kartendienst-444.md` / When die Änderung steht / Then nennt AC-6 dort zusätzlich, dass der Rückfall eine Protokollzeile mit Grund hinterlässt
  - Prüfung: Sichtprüfung der Spec im Review
- **AC-7 (Verhalten unverändert):** Given die bestehenden Tests zu Rückfall, Teilfrist und Gesamtfrist (AC-5 bis AC-7 der Spec 444) / When der Stand läuft / Then sind sie unverändert grün
  - Test: `engine/tests/test_kartendienst.py` insgesamt

## Known Limitations

- **Die Ursache des einen roten Laufs bleibt unbelegt.** Die Änderung macht das nächste Rot erklärbar und beseitigt einen nachgewiesenen Mangel im Stummel (Faden hängt in `accept()`, Fadenzahl 3 auf 9, mögliche Wiederverwendung der Dateinummer). Sie behauptet keine Behebung.
- Die Protokollzeile erscheint nur im Dienst-Journal; eine Überwachung des eigenen Kartendienstes ist damit nicht gegeben (Out of Scope).
- Der Zusammenhang zwischen Stummel und rotem Lauf ist wegen des Zeitpunkts (71 % des Laufs) eher unwahrscheinlich; wird er widerlegt, zeigt die neue Zeile die tatsächliche Ursache.
- Bei einer falsch eingestellten Adresse des eigenen Dienstes (etwa ungültiges Format) kann die Fehlermeldung der Bibliothek die Adresse selbst enthalten und damit in der Zeile stehen. Das betrifft nur Fehlkonfiguration, nicht Ausfall oder Nichterreichbarkeit; die Zeile bleibt im Dienst-Journal der eigenen Instanz.

## Abschlusskriterium für Issue #567

Das Issue wird nicht mit der Auslieferung geschlossen, sondern bleibt mit Beobachtungsauftrag offen. Es wird geschlossen, wenn alle drei Punkte erfüllt sind:

1. Der Stand ist auf `main` ausgeliefert, die Pflichtprüfungen sind grün.
2. Nach der Auslieferung sind mehrere Gesamtläufe `-n 3` und Folgeläufe der Kartentests grün.
3. Die Protokollzeile steht im Betrieb (Stand auf der Instanz eingespielt, Zeile im Dienst-Journal bei einem gestellten Ausfall des eigenen Dienstes nachgewiesen oder im Test nachgewiesen und im Betrieb ausgeliefert).

Wird der Test vorher noch einmal rot, geht die neue Meldung samt Protokollzeile ins Issue, und die Ursachensuche setzt dort an.

## Definition of Done

- [ ] AC-1 bis AC-7 durch Test 1 bis 6 und Sichtprüfung belegt
- [ ] Wiederholungsläufe grün (Gesamtläufe `-n 3`, Folgeläufe der Kartentests)
- [ ] Pflichtprüfungen grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Auslieferung nur über den normalen Weg
- [ ] Issue #567 nach dem Abschlusskriterium behandeln

## Changelog

- 2026-11-14: Initiale Spec (#567)
