---
entity_id: vorgemerkte-durchlauf-529
type: feature
created: 2026-11-20
updated: 2026-11-20
status: draft
version: "1.0"
tags: [betrieb, loeschen, veroeffentlichen, tests]
workflow: test-529-vorgemerkte-durchlauf
---

# Veröffentlichen lässt eine zur Löschung vorgemerkte Reise im echten Durchlauf aus (Testnachzug zu #381, AC-6, #529)

Grundlage: `docs/context/test-529-vorgemerkte-durchlauf.md` (Kontext, Analyse, Probelauf). Vorgänger: `docs/specs/betrieb/loeschen-381.md` (Löschen von Reise und Konto, AC-6: eine vorgemerkte Reise wird nicht gebaut, ihre Seite verschwindet sofort), `docs/specs/betrieb/nginx-baustein-loeschen-527.md` (Stilvorbild, Fixture `kdb`).

## Approval

- [ ] Approved

## Purpose

Dass `betrieb/veroeffentlichen.sh` eine zur Löschung vorgemerkte Reise weder baut noch ausliefert und ihre Seite entfernt, ist bisher nur durch eine Quelltextprüfung belegt (`test_veroeffentlichen_kennt_vorgemerkte` in `engine/tests/test_loeschen_reise.py`). Diese Spec schließt die Lücke mit Tests, die das Skript echt ausführen, gegen beide Anordnungen des Skripts (neu und alt) und mit den beiden Beispielreisen. Das Verhalten ist durch den Probelauf der Analyse (20.11.2026) bereits belegt; es ändert sich kein Produktivcode.

## Entscheidungen (Tech Lead, nicht offen)

1. **Nur Tests, keine Änderung an `betrieb/veroeffentlichen.sh`.** Der Probelauf zeigt, dass AC-6 aus #381 vollständig erfüllt ist. Die Tests sind Nachweistests (sie sind schon beim ersten Lauf grün); die Quelltextprüfung in `test_loeschen_reise.py` bleibt als billige Vorab-Prüfung stehen.
2. **Beide Aufrufstellen von `vorgemerkte_entfernen` werden im echten Lauf geprüft:** `main_klon` (neue Anordnung, #454, heutiger Betriebsweg) und der Lauf der alten Anordnung. Der fachlich echte Fall ist in beiden der Speicher-Teil, denn Löschen ist nur für Reisen im Reisespeicher erlaubt (`anmeldung._loeschen_erlaubt`).
3. **Neue Anordnung über die Fixture `sw`** aus `engine/tests/test_software_weg_454.py` (Import wie bei `vf` in `test_nginx_baustein_loeschen_527.py`: `from test_software_weg_454 import sw`). Sie setzt `FR_KONTEN` schon in der Lauf- und in der Testumgebung, hat beide Beispielreisen (`beispielreise`, `stadtwochenende`) im Speicher und protokolliert Deploys in `deploy.log` im Format „<reise> <kopf>“ (`sw.zeilen("deploy.log")`; das Protokoll wird nicht geleert, Tests zählen vorher und nachher).
4. **Alte Anordnung über `sp`** (Fixture aus `test_betrieb.py`, baut auf `vf` auf; Reisen `beispielreise`, `stadtwochenende` im Speicher, Deploy-Attrappe schreibt `daten.json` in die Seite) **plus Kontendatenbank**. `FR_KONTEN` muss zusätzlich in die Laufumgebung (`sp["lauf"](FR_KONTEN=...)`); `sp["deploys"]()` liefert und leert das Deploy-Protokoll.
5. **Eine gemeinsame Hilfsfunktion `konto_anlegen(konten_ordner)`** in der neuen Testdatei legt die Kontendatenbank an: Umgebungswert `FR_KONTEN` (per `monkeypatch`) auf den Ordner, `FR_MAIL_DATEI` in den tmp-Ordner, dann ein erfundenes Konto `k-ida` (`ida@example.invalid`, Name Ida) mit `INSERT` in `konten` über `konten.db()`, genau wie die Fixture `kdb` in `test_nginx_baustein_loeschen_527.py`. Daraus entsteht eine lokale Fixture `kdb` für die alte Anordnung; für `sw` genügt der Aufruf mit dem von `sw` gesetzten `FR_KONTEN`. Keine Abhängigkeit von der Datei des Tests zu #527 (Fixture wird nicht importiert, um die Dateien unabhängig zu halten).
6. **Vormerken und Zurückholen mit den echten Funktionen:** `konten.loeschung_vormerken("stadtwochenende", "k-ida")` und `konten.loeschung_zurueckholen("stadtwochenende", "k-ida")`. Die Liste für den Lauf liefert der echte Befehl `engine/konten.py vorgemerkt`, keine Attrappe.
7. **Fail closed mit echter Störung:** Die Kontendatenbank (`<FR_KONTEN>/konten.db`) wird durch Text ersetzt, der keine SQLite-Datei ist. Dann scheitert `konten.py vorgemerkt` wirklich, nicht über eine Attrappe.
8. **Erwartete Meldungen** (stehen im Skript, englischer Protokollstil, kein Textkatalog): „<reise> is marked for deletion: page removed.“ und „ERROR: the list of deleted trips cannot be read, the next run tries again.“ Die Tests prüfen jeweils den festen Anfang beziehungsweise Kern („is marked for deletion: page removed.“, „the list of deleted trips cannot be read“).
9. **Reise-Kennungen:** nur `beispielreise` und `stadtwochenende` (in der alten Anordnung zusätzlich die in `vf` vorhandene `zweitreise`, falls ein Test sie braucht); keine echten Reisen, keine Pfade, Adressen oder Zugangsdaten.

## Source

- **Files:** `engine/tests/test_vorgemerkte_durchlauf_529.py` (neu); geprüft wird `betrieb/veroeffentlichen.sh` (nur lesen)
- **Identifier:** `vorgemerkte_entfernen`, `ist_vorgemerkt`, Aufrufstellen in `main_klon` und im Lauf der alten Anordnung

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/veroeffentlichen.sh` (`vorgemerkte_entfernen`, `ist_vorgemerkt`, `main_klon`) | Skript | geprüftes Verhalten, unverändert |
| `engine/konten.py` (`loeschung_vormerken`, `loeschung_zurueckholen`, `db`, Befehl `vorgemerkt`) | Modul | echte Vormerkung, Zurückholen und Liste für den Lauf |
| `engine/reisespeicher.py` (`staende`, `importieren`) | Modul | Seitenstand aus `daten.json` entscheidet beim Zurückholen über den Neubau |
| Fixture `sw` (`engine/tests/test_software_weg_454.py`) | Test | neue Anordnung (`main_klon`), `FR_KONTEN`, Deploy-Protokoll |
| Fixtures `vf`, `sp` (`engine/tests/test_betrieb.py`) | Test | alte Anordnung, Skriptlauf, Deploy-Attrappe, Reisespeicher |
| Fixture `kdb` (Muster aus `engine/tests/test_nginx_baustein_loeschen_527.py`) | Test | Kontendatenbank mit erfundenem Konto, als eigene Kopie in der neuen Datei |
| `engine/tests/test_loeschen_reise.py` (`test_veroeffentlichen_kennt_vorgemerkte`) | Test | Quelltextprüfung, bleibt unverändert bestehen |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/tests/test_vorgemerkte_durchlauf_529.py` | CREATE | Skriptläufe von `veroeffentlichen.sh` mit vorgemerkter Reise, neue und alte Anordnung |
| `betrieb/veroeffentlichen.sh` | READ | keine Änderung (Probelauf belegt AC-6) |
| `engine/tests/test_loeschen_reise.py` | READ | Quelltextprüfung bleibt |

### Nicht im Scope

- Änderung am Verhalten von Veröffentlichen, am Löschprotokoll oder an `konten.py`.
- Der Git-Teil des Laufs mit einer vorgemerkten Git-Reise. Löschen ist nur für Reisen im Reisespeicher erlaubt; eine Git-Reise ließe sich nicht vormerken (Nebenbefund der Analyse: sie würde nach dem Zurückholen ohne Änderung nicht neu gebaut, das ist ohne Fehlerfolge).
- Der nginx-Baustein entfernter Reisen (eigene Spec #527).

### Estimated Changes

- Files: 1 (neu)
- LoC: +120/-0
- Risiko niedrig: nur Tests, keine Produktivänderung. Laufzeit etwa 8 Skriptläufe zu je etwa einer Sekunde, mit `-n 3` unkritisch.

## Implementation Details

Die neue Testdatei `engine/tests/test_vorgemerkte_durchlauf_529.py` hat vier Teile (Code steht in der Datei, nicht hier):

1. **Aufbau:** Kopf wie in `test_nginx_baustein_loeschen_527.py` (Pfade, `sys.path`, `import konten`, Fixtures `vf`, `sp`, `sw` importieren). Hilfsfunktion `konto_anlegen`, Fixture `kdb` für die alte Anordnung, kleine Hilfen: `_seite_da(seiten, reise)` (Ordner mit `daten.json` vorhanden) und `_neue_deploys(sw, vorher)` (Zeilen von `deploy.log` seit dem Zählerstand `vorher`, nur die Reisenamen).
2. **Neue Anordnung (`sw`):**
   - Lauf 1 ohne Vormerkung: Exit 0, beide Reisen gebaut, beide Seiten da.
   - Vormerken von `stadtwochenende`, Lauf 2: Exit 0, Seite `stadtwochenende` weg, kein neuer Deploy für `stadtwochenende`, Zeile „is marked for deletion: page removed.“ in der Ausgabe, `beispielreise` unberührt (Seite da, nicht erneut gebaut, solange sich nichts geändert hat).
   - Lauf 3 mit `--immer`: `stadtwochenende` wird weiterhin nicht gebaut und hat keine Seite, `beispielreise` wird gebaut.
   - Zurückholen, Lauf 4: Exit 0, `stadtwochenende` wird wieder gebaut, Seite wieder da. (Die Seite hat nach dem Entfernen keinen Stand mehr; der Speicher-Stand ist ungleich dem Seitenstand.)
   - Kaputte Kontendatenbank (Text statt SQLite): Lauf endet mit Exit 1, die Fehlerzeile steht in der Ausgabe, kein Deploy (Zählerstand unverändert), keine Seite entfernt (beide Seiten bleiben, wie sie waren).
3. **Alte Anordnung (`sp` plus `kdb`):** Lauf mit `FR_KONTEN` in der Umgebung (`FR_SPEICHERREISEN=""`, wie bei den vorhandenen Speicher-Tests; jede Reise wird vom Speicher-Teil oder vom Git-Teil gebaut, hier genügt der Speicher-Teil). Vormerken von `stadtwochenende`: Seite weg, `sp["deploys"]()` ohne `stadtwochenende`, Exit 0, Meldung; kaputte Datenbank: Exit 1, Fehlerzeile, kein Deploy, Seite bleibt (fail closed).
4. **Bestehende Quelltextprüfung bleibt:** `test_veroeffentlichen_kennt_vorgemerkte` in `test_loeschen_reise.py` wird nicht angefasst.

Hinweis zur Seitenprüfung in `sw`: Die Seiten liegen unter dem Ordner `seiten` der Fixture (`sw.seiten`); die Deploy-Attrappe legt `<seiten>/<reise>/daten.json` an, wenn der materialisierte Bauordner der Reise existiert. Der Fixture-Ordner `_dienst`, `_software` und `_speicher` liegt ebenfalls dort und wird von den Tests nicht verändert.

## Test Plan

### Automated Tests (TDD RED)

Die Tests sind Nachweistests zu bereits bestehendem Verhalten (Probelauf grün); sie müssen beim ersten Lauf grün sein. Nicht verhaltensändernd, daher kein RED-Zustand erwartet; Aussagekraft prüft der Adversary-Schritt, indem er den Aufruf von `vorgemerkte_entfernen` am Skript kurz auskommentiert und die Tests rot werden sieht (Mutationsprobe, nicht eingecheckt).

- [ ] Test 1 (AC-1, neue Anordnung): GIVEN `sw` mit beiden Beispielreisen im Speicher und einem erfundenen Konto, `stadtwochenende` vorgemerkt WHEN `veroeffentlichen.sh` läuft THEN Exit 0, `<seiten>/stadtwochenende` ist weg, `deploy.log` hat keine neue Zeile für `stadtwochenende`, die Ausgabe enthält „stadtwochenende is marked for deletion: page removed.“
- [ ] Test 2 (AC-2, neue Anordnung): GIVEN derselbe Aufbau WHEN der Lauf zusätzlich `beispielreise` betrifft THEN bleibt deren Seite unberührt und sie wird nicht für die Vormerkung der anderen Reise entfernt
- [ ] Test 3 (AC-3, neue Anordnung): GIVEN `stadtwochenende` ist vorgemerkt WHEN `veroeffentlichen.sh --immer` läuft THEN wird `beispielreise` gebaut, `stadtwochenende` nicht, und ihre Seite bleibt weg
- [ ] Test 4 (AC-4, neue Anordnung): GIVEN `stadtwochenende` ist vorgemerkt und die Seite entfernt WHEN `konten.loeschung_zurueckholen` aufgerufen wurde und der nächste Lauf folgt THEN baut er `stadtwochenende` wieder, die Seite ist wieder da, Exit 0
- [ ] Test 5 (AC-5, neue Anordnung): GIVEN beide Seiten stehen und `<FR_KONTEN>/konten.db` enthält Text statt einer SQLite-Datei WHEN `veroeffentlichen.sh` läuft THEN Exit 1, Ausgabe enthält „the list of deleted trips cannot be read“, kein neuer Deploy, keine Seite entfernt
- [ ] Test 6 (AC-6, alte Anordnung): GIVEN `sp` mit Kontendatenbank und `FR_KONTEN` in der Laufumgebung, `stadtwochenende` zuvor gebaut und dann vorgemerkt WHEN `veroeffentlichen.sh` läuft THEN Exit 0, Seite weg, kein Deploy von `stadtwochenende`, die Meldung steht in der Ausgabe
- [ ] Test 7 (AC-6, alte Anordnung, fail closed): GIVEN `sp` mit unlesbarer Kontendatenbank WHEN `veroeffentlichen.sh` läuft THEN Exit 1, Fehlerzeile, `sp["deploys"]()` leer, bestehende Seiten bleiben

Beide Beispielreisen: Die Tests laufen gegen `beispielreise` (Wanderung mit Varianten) und `stadtwochenende` (ohne Wanderung); vorgemerkt wird die Reise ohne Wanderung, die Wanderung dient als unberührte Vergleichsreise.

## Expected Behavior

- **Input:** Eine Reise im Speicher steht bei Aufruf von `veroeffentlichen.sh` in der Liste von `konten.py vorgemerkt`.
- **Output:** Ihre Seite ist entfernt, sie wird nicht gebaut (auch nicht mit `--immer`), Exit 0, Protokollzeile „<reise> is marked for deletion: page removed.“; andere Reisen laufen unberührt weiter. Nach dem Zurückholen baut der nächste Lauf sie wieder.
- **Fehlerfall:** Ist die Liste nicht lesbar, Exit 1 mit Fehlerzeile, nichts wird gebaut, keine Seite entfernt.

## Known Limitations

- Der Git-Teil des Laufs wird nicht mit einer vorgemerkten Git-Reise geprüft (Begründung unter „Nicht im Scope“).
- Der Nachweis gilt für die Skripttexte dieses Stands; ändert jemand die Meldungstexte, müssen die Tests (feste Textanteile) mit angepasst werden.

## Acceptance Criteria

- **AC-1:** Given `stadtwochenende` ist vorgemerkt (neue Anordnung) / When Veröffentlichen läuft / Then Exit 0, die Seite ist entfernt, kein Deploy der Reise, Meldung „is marked for deletion: page removed.“ steht in der Ausgabe. Test: 1.
- **AC-2:** Given eine zweite, nicht vorgemerkte Reise / When die vorgemerkte entfernt wird / Then bleibt die andere Reise unberührt. Test: 2.
- **AC-3:** Given eine vorgemerkte Reise / When Veröffentlichen mit `--immer` läuft / Then wird sie weiterhin nicht gebaut, die anderen werden gebaut. Test: 3.
- **AC-4:** Given die Vormerkung wird zurückgeholt / When der nächste Lauf folgt / Then wird die Reise wieder gebaut und ihre Seite ist wieder da. Test: 4.
- **AC-5:** Given die Kontendatenbank ist unlesbar (neue Anordnung) / When Veröffentlichen läuft / Then Exit 1 mit Fehlerzeile, kein Deploy, keine Seite entfernt (fail closed). Test: 5.
- **AC-6:** Given die alte Anordnung (`sp` mit Kontendatenbank) / When Veröffentlichen läuft / Then gelten dieselben Aussagen für Vormerkung (Seite weg, kein Bau, Exit 0) und für die unlesbare Datenbank (Exit 1, kein Bau, Seiten bleiben). Test: 6, 7.
- **AC-7:** Given die neue Testdatei und `test_loeschen_reise.py` / When `engine/.venv/bin/python -m pytest -q engine/tests -n 3` läuft / Then ist alles grün, die Quelltextprüfung besteht unverändert, `betrieb/veroeffentlichen.sh` ist nicht geändert und die Tests brauchen keine echten Reisen.

## Definition of Done

- [ ] AC-1 bis AC-7 sind durch Tests belegt, die Tests sind ohne Änderung an `betrieb/veroeffentlichen.sh` grün.
- [ ] Mutationsprobe im Adversary-Schritt: Mit entferntem Aufruf von `vorgemerkte_entfernen` (an jeder der beiden Stellen) werden die zugehörigen Tests rot; die Änderung wird nicht eingecheckt.
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n 3` ist ohne echte Reisen grün.
- [ ] Prüfstelle ADR-0001 im Pull Request beantwortet (siehe unten).
- [ ] #529 mit Hinweis auf die neuen Tests kommentiert und erst nach Auslieferung auf `main` geschlossen.

## Prüfstelle ADR-0001 (kurz)

Betrieb und Tests, nicht Kern: keine neue Grundform, keine Art, kein Merkmal, keine Änderung der Reise-Ontologie. Nichts Reisespezifisches in der Engine und nichts Instanzspezifisches in `betrieb/`; es ändert sich kein Produktivcode. Beide Reisetypen: die Tests laufen gegen die Wanderung (`beispielreise`) und das Wochenende ohne Wanderung (`stadtwochenende`). Keine eigene KI, keine neue Fremdbibliothek, keine Sprache im Code, keine neuen sichtbaren Texte. Kein Widerspruch zum Kern.

## Risiken

- **Nur der Speicher-Teil wird geprüft:** Das ist der einzige fachlich mögliche Fall (Löschen nur für Speicherreisen); die Quelltextprüfung deckt den Git-Teil weiter ab.
- **Zerbrechliche Textanteile:** Geprüft werden nur feste Kernsätze der Meldungen, nicht die ganze Ausgabe.
- **Laufzeit:** etwa 8 Skriptläufe, vertretbar; keine Netzzugriffe, Attrappen für Deploy, Heartbeat und Melden stammen aus den Fixtures.
- **Kopierte Fixture `kdb`:** weicht sie später von der Fassung in der Datei zu #527 ab, bleibt jede Datei für sich gültig.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Reiner Testnachzug zu bestehendem, in #381 festgelegtem Verhalten; es wird weder eine Architekturgrenze berührt noch Produktivcode geändert.

## Changelog

- 2026-11-20: Initial spec created (Issue #529; echte Skriptläufe für vorgemerkte Reisen in neuer und alter Anordnung, ohne Änderung an `veroeffentlichen.sh`)
