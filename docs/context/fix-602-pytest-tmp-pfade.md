# Context: fix-602-pytest-tmp-pfade

## Request Summary
Die Prüfung auf absolute Pfade in öffentlichen Protokollen soll auch die Temp-Ordner von pytest
(`/tmp/pytest-of-<name>/…`) erkennen; vorhandene Protokolle werden auf `pytest-of-<benutzer>` umgeschrieben (#602).

## Related Files
| File | Relevance |
|------|-----------|
| engine/tests/test_protokolle_ohne_pfade.py | Muster `ABSOLUT` und Prüfung über `docs/artifacts`, `docs/specs`, `docs/context`; hier kommt das neue Muster und ein Test dazu |
| docs/artifacts/*/test-*-output*.txt (29 Dateien in 28 Ordnern) | enthalten rund 500 Vorkommen von `/tmp/pytest-of-` mit echtem Benutzernamen |
| docs/context/fix-628-playwright-tmp.md | nennt `/tmp/pytest-of-*` (Glob, kein Name) – muss erlaubt bleiben |
| engine/tests/test_betrieb.py:565 | Docstring mit `/tmp/pytest-of-<user>` – nicht im geprüften Bereich |

## Existing Patterns
- Platzhalter in Protokollen: `<benutzer>` (22×) und `<user>` (59×) sind bereits im Bestand; beide gelten als erlaubt.
- Bestehendes Muster ist ein einziger Regex mit Negativ-Lookbehind; `test_muster_erkennt_pfade` prüft positive und negative Beispiele.
- Ältere Bereinigung (#601) hat bereits auf `pytest-of-<benutzer>` umgeschrieben.

## Dependencies
- Upstream: die Liste der eingecheckten Dateien (nur sie werden geprüft).
- Downstream: Jeder künftige Workflow, der Testausgaben nach `docs/artifacts/` kopiert, wird vom Test erfasst.

## Existing Specs
- keine eigene Spec; Regel in CLAUDE.md („Was nie hierher gehört“).

## Risks & Considerations
- Gekürzte Pfade wie `/tmp/pytest-...` oder `/tmp/pytest-of-...` (Ellipsen) verraten nichts und dürfen nicht anschlagen; nur ein echter Name nach `pytest-of-` zählt.
- Erlaubt bleiben: `<benutzer>`, `<user>`, `*`, `...`.
- Andere Temp-Pfade (`/tmp/tmpXXXX`, Lock-Dateien) enthalten keinen Benutzernamen – außerhalb des Auftrags.
- Umschreiben ist rein textuell, keine Testlogik betroffen.

## Analysis

### Type
Bug (Lücke in einer Schutzprüfung: Benutzername des Servers in öffentlichen Protokollen)

### Befund (gemessen)
- Suche über das Repo: 35 Dateien unter `docs/` mit `pytest-of-`; davon 503× `/tmp/pytest-of-<echter Name>/…`.
- Zusätzlich drei Formen, die ein Muster nur mit `/tmp/` verfehlen würde:
  - ohne Schrägstriche (kopierte `PosixPath('tmppytest-of-<name>pytest-16482popen-…')`, rund 35× in `docs/artifacts/bilder-455-stufe1/test-red-output.txt`),
  - gekürzt mit sichtbarem Namen (`/tmp/pytest-of-<name>...itt0`),
  - gekürzt mit Namensanfang (`<tmp>/pytest-of-<zwei Buchstaben>...`).
- Erlaubt und schon vorhanden: `pytest-of-<benutzer>` (22×), `pytest-of-<user>` (59×), `pytest-of-*` (1×), `pytest-of-...` (1×).
- Außerhalb von `docs/` nur Platzhalter (`pytest.ini`, `engine/tests/test_betrieb.py`) – nicht betroffen.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/tests/test_protokolle_ohne_pfade.py | MODIFY | zweites Muster `PYTEST_TMP` = `pytest-of-` gefolgt von einem Wortzeichen (also nicht `<`, `*`, `.`), unabhängig vom Präfix `/tmp/`; Prüfschleife meldet Funde beider Muster; Beispieltest für positive (voller Pfad, Form ohne Schrägstriche, gekürzter Namensanfang, jeweils mit dem erfundenen Namen `jemand`; Beispiele nur im Test) und negative Fälle (`<benutzer>`, `<user>`, `*`, `...`) |
| docs/artifacts/*/test-*.txt, ggf. docs/specs, docs/context (35 Dateien) | MODIFY | rein textuell `pytest-of-<Name>` → `pytest-of-<benutzer>` (auch Kurzform mit Namensanfang) |

### Scope Assessment
- Files: 1 Testdatei + rund 35 Protokolle (nur Text)
- Estimated LoC: Test +10/−3; Protokolle ~540 Zeilen ersetzt (1:1)
- Risk Level: LOW – keine Laufzeitlogik, nur Prüfung und Dokumente

### Technical Approach
1. Muster: `PYTEST_TMP = re.compile(r"pytest-of-\w[\w-]*")`. Bewusst ohne `/tmp/`-Präfix, weil die Form ohne Schrägstriche sonst durchrutscht; `\w` direkt nach dem Bindestrich schließt alle Platzhalter (`<`, `*`, `.`) aus und erfasst auch gekürzte Namensanfänge.
2. Prüfschleife: je Zeile beide Muster prüfen (`ABSOLUT.search(zeile) or PYTEST_TMP.search(zeile)`), Fundmeldung unverändert.
3. Beispieltest mit erfundenem Namen `jemand` (kein echter Name im Testcode).
4. Bereinigung per `sed` über die betroffenen Dateien: zuerst der echte Name mit Fortsetzung, dann die gekürzte Form; danach volle Prüfung grün.
5. Ursache: Workflow-Protokolle werden roh kopiert. Diese Prüfung läuft in CI (`tests (leer)`) und ist das Sicherheitsnetz für künftige Protokolle; eine automatische Bereinigung beim Kopieren läge im Workflow-Plugin, nicht in diesem Repo (kein Auftrag hier).
6. RED-/GREEN-Protokolle dieses Workflows selbst nur mit Platzhalter ablegen, sonst schlägt die eigene Prüfung an.

### Dependencies
- Nur die eingecheckten Dateien unter `docs/artifacts`, `docs/specs`, `docs/context`; keine Instanz nutzt diese Dateien (kein Instanz-Testlauf nötig).

### Open Questions
- keine
