---
entity_id: anstoss-pfad-570
type: bugfix
created: 2026-11-14
updated: 2026-11-14
status: draft
workflow: fix-570-anstoss-pfad
---

# Schreibweg stößt Veröffentlichen auch im Software-Klon an (#570)

Grundlage: `docs/context/fix-570-anstoss-pfad.md` (Kontext, Ursache, Analyse) und Issue #570.

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Reine Betriebsfehlerbehebung: Der Schreibweg übernimmt für den Pfad des Veröffentlichen-Skripts dieselbe Regel, die die Shell-Seite (`fr_alte_anordnung`) schon hat, und meldet ein fehlendes Skript, statt zu schweigen. Die Anordnung selbst entschied die Spec zu #454; Format der Reisedaten, Oberfläche und Kern (ADR-0001) bleiben unberührt.

## Purpose

Nach jedem Schreibvorgang stößt der Schreibweg das Veröffentlichen sofort an, damit die Seite innerhalb von Sekunden den neuen Stand zeigt. Im Software-Klon (neue Anordnung aus #454) sucht er das Skript aber am alten Ort `<wurzel>/frieda/betrieb/veroeffentlichen.sh`, findet es nicht und kehrt still zurück. Die Seite erscheint dann erst mit dem nächsten Timer-Lauf (bis zu 5 Minuten später); im Anstoß-Protokoll fehlt jeder Eintrag. Diese Änderung wählt den Pfad je Anordnung nach derselben Regel wie die Shell-Seite und hinterlässt bei fehlendem Skript eine Zeile im Journal.

## Ursachen / Befund

1. **Fester alter Pfad.** `Schreiber.__init__` in `engine/schreiben.py` setzt die Vorgabe fest auf `<wurzel>/frieda/betrieb/veroeffentlichen.sh`. Im Software-Klon ist die Wurzel der Klon selbst, ein Ordner `frieda/` existiert nicht. Es ist die einzige Python-Stelle, die diesen Pfad noch fest annimmt; im Betrieb setzt keine Unit `SB_VEROEFFENTLICHEN`, es gilt also immer die Vorgabe.
2. **Stilles Zurückkehren.** `veroeffentlichen_anstossen` kehrt bei nicht vorhandenem Skript ohne jede Zeile zurück. Der Fehler blieb unsichtbar; nur die Laufzeit-Warnung über 120 s zeigte ihn indirekt.
3. **Lücke in den Tests.** Jeder Test setzt `SB_VEROEFFENTLICHEN` oder gibt das Skript ausdrücklich mit; die Vorgabe des Pfads war nie geprüft, und der Fall „Software-Klon als Wurzel“ kam nicht vor.

## Source

- **File:** `engine/schreiben.py`
- **Identifier:** `Schreiber.__init__` (Vorgabe), `veroeffentlichen_anstossen`, neue Funktion `veroeffentlichen_skript(wurzel)`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `fr_alte_anordnung` in `betrieb/gemeinsam.sh` | Shell-Funktion | Vorbild der Regel; die Python-Regel muss identisch sein: alt, wenn `<wurzel>/.gitmodules` existiert oder `<wurzel>/frieda/betrieb` ein Ordner ist |
| `engine/schreiben_git.py` | Modul | erzeugt `Schreiber` und reicht `s.veroeffentlichen` weiter; profitiert ohne Änderung |
| `SB_VEROEFFENTLICHEN` | Umgebungswert | überschreibt die Vorgabe; behält Vorrang |
| Argument `veroeffentlichen` von `Schreiber` | Parameter | überschreibt alles; behält Vorrang |
| `docs/specs/betrieb/software-weg-454.md` | Spec | neue Anordnung; beide Anordnungen gelten bis zum Rückbau |
| `betrieb/messlauf-schreibweg.py` | Skript | setzt absichtlich ein fehlendes Skript (Veröffentlichen aus); bekommt künftig nur die stderr-Zeile, erwünscht |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/schreiben.py` | MODIFY | neue Funktion `veroeffentlichen_skript(wurzel)`; Vorgabe in `Schreiber.__init__` daraus; Kopfkommentar (Pfad je Anordnung); fehlendes Skript → eine Zeile auf stderr statt stillem `return` |
| `engine/tests/test_anstoss_pfad_570.py` | CREATE | Tests zu Vorgabe in beiden Anordnungen, Vorrang und fehlendem Skript |

### Estimated Changes

- Files: 2
- LoC: +15/-3 Code, +60 Tests
- Risiko: niedrig (Regel identisch zur Shell-Seite; die alte Anordnung liefert denselben Pfad wie bisher)

### Out of Scope

- Änderungen an `betrieb/deploy.sh` (kein neues Modul), Units, Reisedaten-Format (kein `nachziehen`) und Meldungstexten für Instanzen.
- Alarm über den Meldeweg oder Teil-Check in `monitor.sh`: ein fehlendes Skript ist hier ein Programmfehler, kein Ausfall, den der Betreiber beheben könnte.
- Rückbau der alten Anordnung.
- Änderung der Shell-Seite (`fr_alte_anordnung` bleibt, wie es ist).

## Implementation Details

1. **`veroeffentlichen_skript(wurzel)`:** Ist `<wurzel>/.gitmodules` vorhanden oder `<wurzel>/frieda/betrieb` ein Ordner, gilt die alte Anordnung und die Funktion liefert `<wurzel>/frieda/betrieb/veroeffentlichen.sh`; sonst `<wurzel>/betrieb/veroeffentlichen.sh`. Sie prüft nur die Anordnung, nicht das Skript, und ändert nichts auf der Platte.
2. **`Schreiber.__init__`:** Reihenfolge der Quellen: Argument, dann `SB_VEROEFFENTLICHEN`, dann `veroeffentlichen_skript(self.wurzel)`. Ein ausdrücklich leerer Pfad bleibt leer und schaltet das Veröffentlichen aus.
3. **`veroeffentlichen_anstossen`:** Leerer Pfad: weiter still zurück (gewollt ausgeschaltet). Nicht vorhandenes Skript: genau eine Zeile `Publishing not started (<pfad>): script missing` auf `sys.stderr`, dann zurück; kein Prozessstart, keine Ausnahme. Die Zeile landet im Journal des Dienstes (`<FR_DIENST>`).
4. **Kopfkommentar** in `engine/schreiben.py`: nennt den Pfad je Anordnung statt nur des alten.
5. **Warum englisch und nicht im Textkatalog (ADR-0006):** ADR-0006 verlangt Texte im Katalog für alles, was Personen sehen (Seite, Konnektor, Mails, Fehler). Die Zeile geht nur ins Journal des Dienstes und richtet sich an den Betrieb. Sie ist Betriebsprotokoll wie die bestehende Meldung `Publishing not started …` beim Startfehler des Skripts und folgt deren englischem Wortlaut. Eine Person bekommt sie nie zu sehen; ein Katalogeintrag wäre unnötig, und die Ausnahmelisten in `engine/tests/test_texte.py` bleiben unberührt.
6. **Keine Pfade in Doku und Tests:** Die Spec und die Tests nennen keine absoluten Pfade und keine Serveradressen; Tests arbeiten mit Wurzeln unter `tmp_path`. Der Pfad in der stderr-Zeile ist der zur Laufzeit gebildete Pfad und steht nur im Journal, nicht in Nachweisen im Repo.

## Expected Behavior

- Im Software-Klon stößt jeder Schreibvorgang das Skript `<wurzel>/betrieb/veroeffentlichen.sh` an; die Seite zeigt den neuen Stand nach Sekunden.
- In der alten Anordnung gilt unverändert `<wurzel>/frieda/betrieb/veroeffentlichen.sh`.
- Fehlt das Skript, steht eine Zeile im Journal; der Schreibvorgang selbst gelingt wie bisher.

## Test Plan

### Automated Tests (TDD RED)

In `engine/tests/test_anstoss_pfad_570.py`:

- [ ] Test 1 (`test_vorgabe_alte_anordnung_mit_gitmodules`): GIVEN eine Wurzel mit Datei `.gitmodules` / WHEN `veroeffentlichen_skript(wurzel)` und `Schreiber(wurzel)` ohne Argument und ohne `SB_VEROEFFENTLICHEN` / THEN der Pfad ist `<wurzel>/frieda/betrieb/veroeffentlichen.sh`.
- [ ] Test 2 (`test_vorgabe_alte_anordnung_mit_ordner`): GIVEN eine Wurzel mit Ordner `frieda/betrieb`, ohne `.gitmodules` / WHEN die Vorgabe bestimmt wird / THEN `<wurzel>/frieda/betrieb/veroeffentlichen.sh`.
- [ ] Test 3 (`test_vorgabe_neue_anordnung`): GIVEN eine Wurzel ohne `.gitmodules` und ohne Ordner `frieda/betrieb` / WHEN die Vorgabe bestimmt wird / THEN `<wurzel>/betrieb/veroeffentlichen.sh`.
- [ ] Test 4 (`test_vorrang_argument_umgebung_vorgabe`): GIVEN Software-Klon-Wurzel, `SB_VEROEFFENTLICHEN` gesetzt / WHEN `Schreiber` mit und ohne Argument entsteht / THEN gilt das Argument vor dem Umgebungswert und der Umgebungswert vor der Vorgabe.
- [ ] Test 5 (`test_anstoss_neue_anordnung_startet_skript`): GIVEN ein Software-Klon unter `tmp_path` mit Stummel `betrieb/veroeffentlichen.sh`, der eine Markierungsdatei schreibt / WHEN ein Schreibvorgang das Veröffentlichen anstößt, ohne `SB_VEROEFFENTLICHEN` / THEN läuft der Stummel (Markierungsdatei vorhanden).
- [ ] Test 6 (`test_fehlendes_skript_schreibt_eine_zeile`): GIVEN ein Pfad zu einem nicht vorhandenen Skript / WHEN `veroeffentlichen_anstossen` läuft / THEN steht genau eine Zeile `Publishing not started (<pfad>): script missing` auf stderr, es wird kein Prozess gestartet und keine Ausnahme geworfen.
- [ ] Test 7 (`test_leerer_pfad_bleibt_still`): GIVEN ein leerer Pfad / WHEN `veroeffentlichen_anstossen` läuft / THEN keine Zeile auf stderr, kein Prozessstart.

Vor der Umsetzung rot: Test 3, 5, 6 (alter fester Pfad, stilles Zurückkehren). Test 1, 2, 4, 7 sichern bestehendes Verhalten und sind teils schon grün.

### Bestehende Tests

- `engine/tests/test_schreiben.py` (Anstoß: Priorität, Protokoll, ohne nice) und `engine/tests/test_software_weg_454.py` bleiben unverändert grün. Tests mit dem Repo selbst als Wurzel setzen weiterhin den Stummel über `SB_VEROEFFENTLICHEN`.

### Abnahme auf dem Server

Nach dem Einspielen und einem Schreibvorgang (frische Testreise, nie eine echte Reise; Konnektor): neuer Eintrag im Anstoß-Protokoll `veroeffentlichen-anstoss.log` der Instanz (`<FR_DIENST>`) und die Seite zeigt den Stand nach Sekunden statt nach Minuten. Im Journal von `<FR_DIENST>` steht keine Zeile `script missing`.

## Acceptance Criteria

- **AC-1 (alte Anordnung, `.gitmodules`):** Given eine Wurzel mit `.gitmodules` / When die Vorgabe bestimmt wird / Then ist sie `<wurzel>/frieda/betrieb/veroeffentlichen.sh`
  - Test: `engine/tests/test_anstoss_pfad_570.py::test_vorgabe_alte_anordnung_mit_gitmodules`
- **AC-2 (alte Anordnung, Ordner):** Given eine Wurzel mit Ordner `frieda/betrieb`, ohne `.gitmodules` / When die Vorgabe bestimmt wird / Then ist sie ebenfalls `<wurzel>/frieda/betrieb/veroeffentlichen.sh`
  - Test: `engine/tests/test_anstoss_pfad_570.py::test_vorgabe_alte_anordnung_mit_ordner`
- **AC-3 (neue Anordnung):** Given eine Wurzel ohne `.gitmodules` und ohne Ordner `frieda/betrieb` / When die Vorgabe bestimmt wird / Then ist sie `<wurzel>/betrieb/veroeffentlichen.sh`
  - Test: `engine/tests/test_anstoss_pfad_570.py::test_vorgabe_neue_anordnung`
- **AC-4 (Vorrang):** Given ein Argument, `SB_VEROEFFENTLICHEN` und die Vorgabe / When `Schreiber` entsteht / Then gilt das Argument vor `SB_VEROEFFENTLICHEN` vor der Vorgabe
  - Test: `engine/tests/test_anstoss_pfad_570.py::test_vorrang_argument_umgebung_vorgabe`
- **AC-5 (Anstoß im Software-Klon):** Given ein Software-Klon mit Skript unter `betrieb/` und ohne `SB_VEROEFFENTLICHEN` / When ein Schreibvorgang das Veröffentlichen anstößt / Then wird das Skript gestartet
  - Test: `engine/tests/test_anstoss_pfad_570.py::test_anstoss_neue_anordnung_startet_skript`
- **AC-6 (fehlendes Skript):** Given ein nicht vorhandenes Skript / When `veroeffentlichen_anstossen` läuft / Then steht genau eine Zeile `Publishing not started (<pfad>): script missing` auf stderr, es startet kein Prozess und es wird keine Ausnahme geworfen
  - Test: `engine/tests/test_anstoss_pfad_570.py::test_fehlendes_skript_schreibt_eine_zeile`
- **AC-7 (leerer Pfad):** Given ein leerer Pfad / When `veroeffentlichen_anstossen` läuft / Then bleibt es still und es startet kein Prozess
  - Test: `engine/tests/test_anstoss_pfad_570.py::test_leerer_pfad_bleibt_still`
- **AC-8 (Bestand):** Given die bestehenden Anstoß-Tests / When der Stand läuft / Then sind sie unverändert grün
  - Test: `engine/tests/test_schreiben.py` (Anstoß) und `engine/tests/test_software_weg_454.py`
- **AC-9 (Betrieb):** Given die Instanz mit dem neuen Stand / When ein Schreibvorgang erfolgt / Then steht ein neuer Eintrag im Anstoß-Protokoll von `<FR_DIENST>` und die Seite zeigt den Stand nach Sekunden statt nach Minuten
  - Prüfung: Abnahme auf dem Server mit frischer Testreise, nach dem Einspielen

## Prüfstelle ADR-0001 (knapp)

Der Kern ist nicht berührt: kein neues Konzept, keine neue Grundform, nichts Reise- oder Instanzspezifisches in der Engine. Es ist eine Betriebsfehlerbehebung für alle Instanzen und beide Beispielreisen gleichermaßen; der Pfad hängt nur von der Anordnung der Wurzel ab, nicht von der Reise.

## Known Limitations

- Die Regel steht an zwei Stellen (Shell und Python). Der Test zu AC-1 bis AC-3 hält die Python-Seite fest; ein gemeinsamer Test gegen die Shell-Funktion ist nicht Teil dieses Vorhabens.
- Die Journal-Zeile ist keine Überwachung; sie macht den Fehler sichtbar, alarmiert aber nicht (Out of Scope).

## Definition of Done

- [ ] AC-1 bis AC-8 durch Test 1 bis 7 und die bestehenden Tests belegt
- [ ] Pflichtprüfungen grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Auslieferung nur über den normalen Weg
- [ ] Tests der einbindenden Instanz gegen den Stand (CLAUDE.md), da der Schreibweg betroffen ist
- [ ] AC-9 auf dem Server nachgewiesen, danach Issue #570 schließen

## Changelog

- 2026-11-14: Initiale Spec (#570)
