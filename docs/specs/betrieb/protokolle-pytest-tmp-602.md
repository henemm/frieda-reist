---
entity_id: protokolle-pytest-tmp-602
type: bugfix
created: 2026-11-21
updated: 2026-11-21
status: draft
workflow: fix-602-pytest-tmp-pfade
---

# Protokollprüfung erkennt die Temp-Ordner von pytest (#602)

Grundlage: `docs/context/fix-602-pytest-tmp-pfade.md` (Befund, Analyse). Vorbild für den Aufbau: `docs/specs/betrieb/playwright-tmp-tests.md`.

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es ändern sich nur eine Schutzprüfung in den Tests und der Text öffentlicher Protokolle. Engine, Vorlage und Betrieb bleiben unberührt, der Kern aus ADR-0001 ist nicht berührt.

## Purpose

Öffentliche Protokolle unter `docs/` dürfen keinen Benutzernamen des Servers enthalten (CLAUDE.md, „Was nie hierher gehört“). Die Prüfung `test_protokolle_ohne_pfade.py` erkennt Pfade unter `/home`, `/srv` usw., aber nicht die Temp-Ordner von pytest (Ordner `/tmp/pytest-of-` plus Benutzername). Deshalb steht der Name in rund 35 Dateien (gemessen: rund 500 Vorkommen). Die Prüfung soll diese Lücke schließen, und der Bestand soll bereinigt werden.

## Befund

- 35 Dateien unter `docs/` enthalten den Temp-Ordner von pytest; die meisten tragen einen echten Namen.
- Neben der vollen Form mit `/tmp/` gibt es drei Formen, die ein Muster nur mit `/tmp/` übersähe: ohne Schrägstriche (kopierte Pfadobjekte, in denen `tmp` und `pytest-of-<Name>` ohne Trenner aneinanderhängen), gekürzt mit sichtbarem Namen und gekürzt mit Namensanfang.
- Schon vorhandene, erlaubte Platzhalter: `pytest-of-<benutzer>`, `pytest-of-<user>`, `pytest-of-*`, `pytest-of-...`.

## Source

- **File:** `engine/tests/test_protokolle_ohne_pfade.py`
- **Identifier:** Muster `PYTEST_TMP`, Test `test_protokolle_ohne_absolute_pfade`, Test `test_muster_erkennt_pfade`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `ABSOLUT` in `test_protokolle_ohne_pfade.py` | Muster | bestehendes Muster für absolute Pfade, bleibt unverändert |
| `git ls-files` über `docs/artifacts`, `docs/specs`, `docs/context` | Werkzeug | bestimmt die geprüften Dateien (nur eingecheckte) |
| `docs/context/fix-628-playwright-tmp.md` | Dokument | nennt den Glob `pytest-of-*`; muss erlaubt bleiben |
| `engine/tests/test_betrieb.py` | Test | enthält einen Platzhalter, liegt nicht im geprüften Bereich, unverändert |
| CI-Pflichtprüfung `tests (leer)` | CI | führt die Prüfung für jeden künftigen Stand aus |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/tests/test_protokolle_ohne_pfade.py` | MODIFY | zweites Muster `PYTEST_TMP`, Prüfschleife meldet beide Muster, Beispieltest |
| `docs/artifacts/*/test-*output*.txt` und weitere Dateien unter `docs/` mit Fund (rund 35) | MODIFY | rein textuell Name auf `pytest-of-<benutzer>` |
| `docs/specs/betrieb/protokolle-pytest-tmp-602.md` | CREATE | diese Spec |

### Estimated Changes

- Files: 1 Testdatei, rund 35 Protokolle, 1 Spec
- LoC: Test +10/-3; Protokolle rund 540 Zeilen 1:1 ersetzt

### Out of Scope

- Andere Temp-Pfade ohne Benutzernamen (`/tmp/tmpXXXX`, Lock-Dateien).
- Eine automatische Bereinigung beim Kopieren von Protokollen; sie läge im Workflow-Plugin, nicht in diesem Repo.

## Implementation Details

1. **Muster.** `PYTEST_TMP = re.compile(r"pytest-of-\w[\w-]*")`. Bewusst ohne `/tmp/`-Präfix, damit auch die Form ohne Schrägstriche und gekürzte Namensanfänge anschlagen. Das Wortzeichen direkt nach dem Bindestrich schließt alle Platzhalter aus, weil `<`, `*` und `.` keine Wortzeichen sind.
2. **Erlaubt bleiben** `pytest-of-<benutzer>`, `pytest-of-<user>`, `pytest-of-*` und `pytest-of-...`.
3. **Prüfschleife.** Je Zeile werden beide Muster geprüft (`ABSOLUT` oder `PYTEST_TMP`); Fundmeldung und Ausgabeform bleiben wie bisher und nennen Datei, Zeile und Fund.
4. **Beispieltest** mit erfundenem Namen `jemand`; im Testcode steht kein echter Name. Die Beispiele (voller Pfad mit `/tmp/`, Form ohne Schrägstriche, gekürzter Namensanfang) stehen im Test, nicht in dieser Spec, weil die Spec selbst geprüft wird.
5. **Bereinigung.** Alle Dateien unter `docs/` mit Fund werden rein textuell auf `pytest-of-<benutzer>` umgeschrieben (zuerst der Name mit seiner Fortsetzung, dann die gekürzte Form). Testlogik in den Protokollen ist nicht betroffen. Danach läuft die volle Prüfung.
6. **Eigene Protokolle.** Die RED- und GREEN-Protokolle dieses Workflows werden nur mit dem Platzhalter abgelegt, sonst schlägt die eigene Prüfung an. Der echte Name erscheint auch in dieser Spec nicht.

## Erwartetes Verhalten

- Ein Protokoll mit dem pytest-Temp-Ordner und folgendem Namen macht `test_protokolle_ohne_absolute_pfade` rot und nennt Datei, Zeile und Fund.
- Protokolle mit den vier erlaubten Platzhaltern bleiben grün.
- Nach der Bereinigung enthält kein eingecheckter Text unter den geprüften Ordnern mehr einen Namen im pytest-Temp-Ordner.

## Test Plan

### Automated Tests (TDD RED)

Alle in `engine/tests/test_protokolle_ohne_pfade.py`.

- [ ] Test 1 (Muster erkennt Namen): GIVEN Beispiele mit erfundenem Namen `jemand` als voller Pfad mit `/tmp/`, ohne Schrägstriche und als gekürzter Namensanfang / WHEN `PYTEST_TMP` darauf angewendet wird / THEN schlägt es bei jedem an.
- [ ] Test 2 (Muster schweigt bei Platzhaltern): GIVEN `pytest-of-<benutzer>`, `pytest-of-<user>`, `pytest-of-*` und `pytest-of-...` / WHEN `PYTEST_TMP` angewendet wird / THEN schlägt es bei keinem an.
- [ ] Test 3 (Prüfung über den Bestand): GIVEN der Bestand vor der Bereinigung / WHEN `test_protokolle_ohne_absolute_pfade` läuft / THEN ist er rot (RED) mit den Fundstellen; GIVEN der bereinigte Bestand / WHEN er läuft / THEN ist er grün.
- [ ] Test 4 (bestehendes Muster): GIVEN die bisherigen Beispiele / WHEN `test_muster_erkennt_pfade` läuft / THEN bleibt er unverändert grün.

### Manuelle Prüfung

- Prüfung 5: Eine Suche über `docs/` nach dem pytest-Temp-Ordner mit Wortzeichen direkt danach ergibt keinen Treffer.
- Prüfung 6: Volle Testprüfung (`engine/.venv/bin/python -m pytest -q engine/tests`, parallel mit `-n 3`) ist grün.

## Acceptance Criteria

- **AC-1:** Given ein Text mit dem pytest-Temp-Ordner und einem Namen, auch ohne `/tmp/`-Schrägstriche oder gekürzt / When die Prüfung läuft / Then wird er gemeldet (Test 1).
  Test: `engine/tests/test_protokolle_ohne_pfade.py::test_muster_erkennt_pfade`
- **AC-2:** Given die Platzhalter `<benutzer>`, `<user>`, `*` und `...` / When die Prüfung läuft / Then wird nichts gemeldet (Test 2).
  Test: `engine/tests/test_protokolle_ohne_pfade.py::test_muster_erkennt_pfade`
- **AC-3:** Given die eingecheckten Dateien unter `docs/artifacts`, `docs/specs`, `docs/context` / When `test_protokolle_ohne_absolute_pfade` läuft / Then meldet er keinen Fund (Test 3), und kein echter Benutzername steht mehr im pytest-Temp-Ordner.
  Test: `engine/tests/test_protokolle_ohne_pfade.py::test_protokolle_ohne_absolute_pfade`
- **AC-4:** Given der Stand der Änderung / When die volle Prüfung und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) laufen / Then sind sie grün (Prüfung 6).
  Test: manuell und CI

## Risks

- **Zu breit:** Das Muster schlägt auch bei einem harmlosen Wort nach dem Bindestrich an, etwa in einer Erklärung. Akzeptiert: ein Platzhalter ist dann leicht zu schreiben, die Meldung nennt die Stelle.
- **Zu eng:** Ein Benutzername in einem anderen Temp-Pfad wird nicht erkannt; dafür greift weiter `ABSOLUT` für Heimatordner und Verwandtes.

## Bekannte Einschränkungen

- Die Prüfung ersetzt keine Bereinigung beim Entstehen der Protokolle; sie fängt nur, was eingecheckt werden soll.
- Andere Temp-Pfade ohne Benutzernamen bleiben bewusst unbeachtet.

## Definition of Done

- [ ] AC-1 bis AC-3 durch Test 1 bis 3 belegt
- [ ] AC-4 durch volle Prüfung und grüne Pflichtprüfungen belegt
- [ ] Auslieferung nur über den normalen Weg (Pull Request, grüne Pflichtprüfungen, Vorspulen)
- [ ] Issue #602 erst nach grünem Lauf auf `main` schließen

## Changelog

- 2026-11-21: Initiale Spec (#602)
