---
entity_id: einstellungen-fail-closed-361
type: bugfix
created: 2026-11-08
updated: 2026-11-08
status: draft
workflow: fix-361-einstellungen-fail-closed
version: "1.0"
tags: [reisespeicher, einstellungen, fail-closed, schreibweg, veroeffentlichen, betrieb, epic-345]
---

# Lesefehler der Einstellungen schaltet keine Speicher-Reise auf den Git-Weg (#361, Epic #345)

Grundlage: `docs/context/fix-361-einstellungen-fail-closed.md` (Kontext und Analyse), ADR-0009, Befund F003 aus der Prüfung von #347.

## Approval

- [ ] Approved

## Purpose

Welche Reisen im Reisespeicher liegen, steht in `FR_SPEICHERREISEN` (Umgebung oder Einstellungsdatei der Instanz). Kann die Einstellungsdatei **existiert, aber nicht gelesen werden** (Rechte, Dateisystemfehler), liefert `instanz.einstellungen()` heute `{}`; die Liste der Speicher-Reisen ist dann leer, und eine Speicher-Reise würde über Git geschrieben, gebaut und angezeigt. Das wäre ein stiller Weg der Daten in die falsche Quelle. Diese Änderung macht daraus einen lauten Fehler (fail closed), bevor in Stufe 5 (#350) echte Reisen umgeschaltet werden.

Eine **fehlende** Datei bleibt normal (Beispielreisen, Tests, Instanzen ohne Speicher-Reisen): keine Speicher-Reisen, alles über Git.

## Source

- **File:** `engine/instanz.py`, `engine/schreiben.py`, `engine/schreiben_git.py`, `engine/stand.py`, `engine/texte_<sprache>.py`, `betrieb/gemeinsam.sh`
- **Identifier:** `instanz.speicherreisen`, `instanz.EinstellungenNichtLesbar` (neu), `schreiben.anwenden_extern`, `schreiben_git.vorgang`, `stand.fuer_seite`, `fr_einlesen`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/instanz.py` | Modul | `einstellungen()` und `wert()` bleiben nachsichtig (Pfade, Ablage, Zeitzone brauchen weiter Vorgaben); nur `speicherreisen()` wird streng |
| `engine/schreiben.py` | Modul | `anwenden_extern`, `/gesund`, Buchungsabfrage: die drei Weichen zwischen Speicher und Git; `fehler_antwort` |
| `engine/schreiben_git.py` | Modul | Schutz `reise_im_speicher` in `vorgang` (zweite Sicherung) |
| `engine/stand.py` | Modul | `fuer_seite` wählt die Quelle über `speicherreisen()` |
| `betrieb/gemeinsam.sh` | Shell | `fr_einlesen`, von `veroeffentlichen.sh` und `software-nachziehen.sh` benutzt |
| `engine/texte_de.py`, `texte_en.py` und weitere `texte_<sprache>.py`, `engine/tests/test_texte.py` | Textkatalog | ein neuer Schlüssel in allen Sprachen |

## Scope

- **Affected Files:** `engine/instanz.py`, `engine/schreiben.py`, `engine/schreiben_git.py`, `engine/stand.py`, `engine/texte_*.py`, `betrieb/gemeinsam.sh`; Tests in `engine/tests/test_schreiben_speicher.py`, `test_stand.py`, `test_betrieb.py` und die neue Datei `test_instanz.py`
- **Estimated Changes:** ca. +70/-5 Zeilen Code, +90 Zeilen Tests
- **Nicht im Scope:** Umschalten echter Reisen (#350); Nachsicht von `einstellungen()`/`wert()` ändern; Format der Reisedaten (kein `nachziehen` nötig); neue Überwachung (`/gesund` und das Protokoll melden den Fehler bereits über den vorhandenen Monitor).

## Implementation Details

```
instanz.py
  class EinstellungenNichtLesbar(OSError)
  speicherreisen():
    Umgebung FR_SPEICHERREISEN gesetzt (auch leer) -> gilt, Datei wird nicht gelesen
    sonst Datei lesen:
      FileNotFoundError           -> keine Speicher-Reisen (wie bisher)
      anderer OSError (Rechte, Verzeichnis statt Datei, E/A) -> raise EinstellungenNichtLesbar
  einstellungen(), wert(): unverändert (nachsichtig)

schreiben.py
  anwenden_extern: speicherreisen() vor der Weiche; EinstellungenNichtLesbar ->
    Protokollzeile "Error <werkzeug> 503: settings not readable: <Grund>" auf stderr,
    Code 503, fehler_antwort("schreiben.dienst.einstellungen_nicht_lesbar")
  /gesund: EinstellungenNichtLesbar -> 503 {"gesund": false}
  GET /<reise>/buchung/<B>: EinstellungenNichtLesbar -> 503 mit demselben Katalogtext (mit_ok=False)

schreiben_git.vorgang: EinstellungenNichtLesbar beim Schutz -> 503 (wie oben), bevor etwas geholt wird

stand.fuer_seite: EinstellungenNichtLesbar wird nicht gefangen -> der Bau bricht laut ab

gemeinsam.sh fr_einlesen:
  Datei fehlt                       -> return 0 (wie bisher)
  Datei vorhanden, aber nicht lesbar -> "ERROR: <datei> exists but cannot be read" auf stderr, exit 1
```

## Expected Behavior

- **Input:** Einstellungsdatei vorhanden, aber nicht lesbar; `FR_SPEICHERREISEN` nicht in der Umgebung.
- **Output:** Schreibvorgang, `/gesund`, Buchungsabfrage: 503 mit Katalogtext; Seitenbau und Veröffentlichen brechen mit klarer Fehlermeldung ab. Kein Vorgang läuft über Git.
- **Side effects:** Eine Protokollzeile auf stderr je abgewiesenem Vorgang. Nichts wird geschrieben, geholt oder gebaut.
- **Unverändert:** Datei fehlt -> alles über Git. `FR_SPEICHERREISEN` in der Umgebung gilt weiter vor der Datei, auch bei unlesbarer Datei. Der Dienst startet und beantwortet Anfragen weiter; nur die vier Weichen lehnen ab.

## Known Limitations

- Eine Datei, die lesbar, aber inhaltlich falsch ist (Tippfehler im Namen), bleibt ein Betriebsfehler außerhalb dieser Änderung.
- Unter `root` greifen entzogene Dateirechte nicht; der Test mit `chmod 000` wird dort übersprungen, die Ersatztests (Verzeichnis statt Datei, gepatchtes Lesen) laufen immer.

## Definition of Done

Fertig ist diese Änderung, wenn:

- [ ] Jede Acceptance Criterion unten ist durch einen automatischen Test belegt
- [ ] Bei vorhandener, unlesbarer Einstellungsdatei lehnt der Schreibdienst eine Speicher-Reise mit 503 ab, statt sie über Git zu schreiben
- [ ] Eine fehlende Einstellungsdatei verhält sich wie vorher (Beispielreisen, Tests, Instanzen ohne Datei)
- [ ] Keine bestehende Funktion ist dabei kaputtgegangen (Regressionslauf grün, Tests der einbindenden Instanzen mit dem Branch grün)

## Acceptance Criteria

- **AC-1:** Given die Einstellungsdatei existiert, ist aber nicht lesbar, und `FR_SPEICHERREISEN` ist nicht in der Umgebung / When `instanz.speicherreisen()` aufgerufen wird / Then wird `EinstellungenNichtLesbar` ausgelöst (kein leeres Ergebnis).
  - Test: `engine/tests/test_instanz.py::test_speicherreisen_unlesbare_datei_loest_aus` (Datei durch Verzeichnis ersetzt) und `::test_speicherreisen_chmod_000` (übersprungen unter root)
- **AC-2:** Given die Einstellungsdatei fehlt / When `speicherreisen()` aufgerufen wird / Then ist die Liste leer, ohne Ausnahme.
  - Test: `engine/tests/test_instanz.py::test_speicherreisen_fehlende_datei_ist_leer`
- **AC-3:** Given `FR_SPEICHERREISEN` ist in der Umgebung gesetzt und die Datei ist unlesbar / When `speicherreisen()` aufgerufen wird / Then gilt der Umgebungswert, ohne Ausnahme.
  - Test: `engine/tests/test_instanz.py::test_speicherreisen_umgebung_gilt_vor_unlesbarer_datei`
- **AC-4:** Given unlesbare Datei / When `einstellungen()` oder `wert()` gerufen wird / Then liefern sie weiter `{}` bzw. die Vorgabe (der Dienst fällt nicht ganz aus).
  - Test: `engine/tests/test_instanz.py::test_einstellungen_und_wert_bleiben_nachsichtig`
- **AC-5:** Given unlesbare Datei / When ein Schreibvorgang für irgendeine Reise ankommt (`anwenden_extern`) / Then Antwort 503 mit dem Text `schreiben.dienst.einstellungen_nicht_lesbar`, Protokollzeile auf stderr, und weder `schreiben_git.vorgang` noch `vorgang_speicher` wird ausgeführt.
  - Test: `engine/tests/test_schreiben_speicher.py::test_unlesbare_einstellungen_lehnen_ab_ohne_git`
- **AC-6:** Given unlesbare Datei / When `schreiben_git.vorgang` direkt gerufen wird / Then 503 vor jedem Holen aus Git.
  - Test: `engine/tests/test_schreiben_speicher.py::test_git_vorgang_direkt_unlesbare_einstellungen`
- **AC-7:** Given unlesbare Datei / When `GET /gesund` oder `GET /<reise>/buchung/<B>` kommt / Then 503 (`{"gesund": false}` bzw. Katalogtext).
  - Test: `engine/tests/test_schreiben_speicher.py::test_gesund_und_buchung_unlesbare_einstellungen`
- **AC-8:** Given unlesbare Datei / When `stand.fuer_seite` aufgerufen wird / Then bricht es mit `EinstellungenNichtLesbar` ab und liefert nie einen Stand aus Git.
  - Test: `engine/tests/test_stand.py::test_fuer_seite_unlesbare_einstellungen_bricht_ab`
- **AC-9:** Given fehlende Datei / When Schreibvorgang einer Git-Reise / Then läuft er wie bisher über Git.
  - Test: `engine/tests/test_schreiben_speicher.py::test_fehlende_einstellungen_git_weg_unveraendert`
- **AC-10:** Given der Schlüssel `schreiben.dienst.einstellungen_nicht_lesbar` / When der Textkatalog geprüft wird / Then ist er in allen Sprachen vorhanden, die Ausnahmelisten in `test_texte.py` sind nicht länger geworden.
  - Test: `engine/tests/test_texte.py` (bestehende Prüfungen)
- **AC-11:** Given `fr_einlesen` mit vorhandener, nicht lesbarer Datei / When es läuft / Then Abbruch mit Fehlermeldung auf stderr und Exit-Code ungleich 0; mit fehlender Datei Exit-Code 0 wie bisher.
  - Test: `engine/tests/test_betrieb.py::test_fr_einlesen_unlesbare_datei_bricht_ab` und `::test_fr_einlesen_fehlende_datei_ist_ok`

## Test Plan

Automatische Tests (jeweils an eine AC oben gebunden):
- `engine/.venv/bin/python -m pytest -q engine/tests/test_instanz.py engine/tests/test_schreiben_speicher.py engine/tests/test_stand.py engine/tests/test_betrieb.py engine/tests/test_texte.py`
- danach der volle Lauf mit `-n 3`
- vor dem Vorspulen: Tests der einbindenden Instanzen mit dem Branch (Meldungstext und `gemeinsam.sh` sind Schnittstellen)

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Setzt ADR-0009 (Reisespeicher als Wahrheit der Speicher-Reisen) nur konsequent um; keine neue Grundform, kein neues Format, kein Widerspruch zum Kern (ADR-0001).

## Changelog

- 2026-11-08: Initial spec created
