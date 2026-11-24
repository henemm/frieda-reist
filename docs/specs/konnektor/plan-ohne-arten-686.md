---
entity_id: plan-ohne-arten-686
type: bugfix
created: 2026-11-24
updated: 2026-11-24
status: draft
workflow: fix-686-wahlstelle-ohne-arten
version: "1.0"
tags: [konnektor, schreibweg, plan, arten, nachziehen, m7]
---

# Plan-Werkzeuge in Reisen ohne Arten lehnen ab, Arten tragen den Plan sofort ein (#686)

## Approval

- [ ] Approved

## Purpose

In einer Reise ohne Arten melden die Plan-Werkzeuge des Konnektors (zuerst aufgefallen bei `choice_create`) Erfolg, schreiben aber in eine `plan/routen.yaml`, die nicht in `reise.json` eingetragen ist. Der Generator liest diesen Plan nicht, die Wahlstelle ist nirgends sichtbar und nicht entscheidbar. Künftig meldet ein Schreibwerkzeug nie Erfolg für etwas, das danach nicht existiert: Ohne Arten lehnt der Schreibweg mit klarer Begründung ab, und sobald eine Reise Arten hat, wird ein vorhandener Plan sofort eingetragen und sichtbar.

## Ziel und Abgrenzung

- **Im Scope:**
  - `routen_speichern` in `engine/schreiben.py` wird die eine geprüfte Schreibstelle des Plans im Schreibweg. Hat die Reise keine Arten (`arten_laden` leer), wirft sie `Ablehnung("schreiben.plan.ohne_arten")`. Der Hinweis im Text: zuerst Arten übernehmen (`kinds_adopt`) oder definieren (`kind_define`). Die Prüfung sitzt zentral, nicht je Werkzeug, damit sie alle heutigen und künftigen Aufrufer deckt (30 Aufrufstellen in `schreiben.py`). Sie sitzt nicht in `route_stand`, weil lesende Wege (`uebersicht_wert`, `kartenstatus`) darüber laufen.
  - Mit Arten ruft `routen_speichern` nach dem Schreiben `plan_sicherstellen` auf; der Plan steht danach in `reise.json` und ist sichtbar.
  - Neue rohe Funktion `routen_datei_schreiben` (ohne Prüfung, ohne Eintragen) für das Gerüst in `plan_sicherstellen`, für `routen_normalisieren` und für die Aufrufe in `engine/neu.py` (Zeilen 355 und 1138).
  - `arten_speichern` (damit `art_definieren`, `arten_uebernehmen`, `merkmal_*`): liegt `plan/routen.yaml` schon vor, trägt danach `plan_sicherstellen` den Plan ein.
  - `neu.py nachziehen`: eine Reise mit Arten und `plan/routen.yaml`, aber ohne `routen` in `reise.json` (Altlast dieses Fehlers) bekommt den Eintrag. Das läuft beim Veröffentlichen über `nachziehen-speicher`, ohne Handschritt.
  - Textschlüssel `schreiben.plan.ohne_arten` in `engine/texte_de.py` und `engine/texte_en.py` (alle vorhandenen Sprachen).
  - Doku `docs/funktionen/` (Nutzersicht): Pläne, Auswahlen und Tage brauchen zuerst Arten.
- **Nicht im Scope:**
  - Einen Plan ohne Arten in `reise.json` einzutragen: Das widerspricht der Bau-Regel (`pruefung.routen.51`, `docs/ontologie.md`), die Reise würde nicht mehr bauen.
  - Arten automatisch anlegen oder vorschlagen (ADR-0011: Vorlagen bleiben ein Angebot).
  - Nebenbefund Meldungen zu gelöschten Testreisen in `my_trips`: eigenes Issue #687.
  - Die Beschreibungen der Konnektor-Werkzeuge bleiben unverändert: Der Weg zu den Arten steht im Ablehnungstext, den der AI-Client im Moment des Bedarfs bekommt; ein Zusatz in rund 30 Werkzeugbeschreibungen würde nur Text verdoppeln.
- **Kern (ADR-0001):** Keine neue Grundform, keine Art und kein Merkmal in der Software, nichts Reisespezifisches. Nur eine klare Ablehnung statt stiller Lücke; wirkt für alle Reisen und Instanzen gleich. Beide Beispielreisen haben Arten und Eintrag und bleiben unverändert.
- **Betroffene Werkzeuge (im Code geprüft):** Ohne jeden Probebau schreiben `wert_eintragen`, `wert_leeren`, `lage_eintragen`, `track_anhaengen`, `kartenpunkte_ablegen`, `tag_aendern`, `tag_anlegen`, `termin_setzen`, `start_ende_setzen`. Mit `route_stand` (liefert ohne Eintrag `{}` statt eines Fehlers) arbeiten unter anderem `ding_anlegen`, `wahlstelle_anlegen`, `option_anlegen`, `entscheiden`, `buchung_*`, `plan_*`. Alle laufen über `routen_speichern`; eine Einzelprüfung ließe Lücken.
- **Aufrufer der rohen Funktion (im Code geprüft):** `plan_sicherstellen` (Gerüst, Zeile 929), `routen_normalisieren` (Zeile 973), `neu.py` Zeilen 355 (`umbrechen`) und 1138 (`nachziehen`). `engine/tests/test_hinweis_604.py` ruft `sb.routen_speichern` in `flach_machen` auf einer Kopie der Beispielreisen; beide haben Arten, der Test bleibt grün und braucht keine Änderung.
- **Rücknahme:** `Schreiber.schreiben` verwirft bei jeder `Ablehnung` die ganze Arbeitskopie. Eine im selben Vorgang schon angelegte offene Frage (`frage_zeile` in `wahlstelle_anlegen`) verschwindet damit; es bleibt keine Frage F-… ohne Wahlstelle.
- **Instanzen und Datenformat:** Die Eintragung in `reise.json` ist eine Umstellung bestehender Reisen und kommt deshalb mit Test in `neu.py nachziehen` (Regel: Handschritt nach Software-Wechsel ist ein Fehler der Software, #250, #557). Ändert sich der Text einer Ablehnung, den eine Instanz nutzt, laufen vor dem Vorspulen die Tests der einbindenden Instanzen mit dem Zweig.

## Source

- **File:** `engine/schreiben.py`
- **Identifier:** `def routen_speichern`, `def plan_sicherstellen`, `def arten_speichern`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `arten_laden` | Code (`engine/schreiben.py`) | Entscheidet, ob die Reise Arten hat |
| `plan_sicherstellen`, `routen_geruest` | Code (`engine/schreiben.py`) | Legt das Gerüst an und trägt `routen` in `reise.json` ein (`datei`, `tagesplan`, `unterkuenfte`) |
| `neue_id` / `ids.yaml` | Code | W-IDs für `tagesplan` und `unterkuenfte` |
| `Schreiber.schreiben`, `Ablehnung` | Code (`engine/schreiben.py`) | Ein Vorgang gleich eine Arbeitskopie; Rücknahme bei Ablehnung |
| `bauen.Bauer` (Bedingung `if r_cfg:`) | Code (`engine/bauen.py`) | Routenmodell nur mit `routen` in `reise.json` |
| `routen.py`, Text `pruefung.routen.51` | Code | Bau-Regel: Plan ohne Arten ist ein Baufehler |
| `neu.nachziehen`, `nachziehen_speicher` | Code (`engine/neu.py`) | Heilung bestehender Reisen beim Veröffentlichen |
| `engine/texte_de.py`, `engine/texte_en.py` | Textkatalog | Text der Ablehnung in allen Sprachen |
| #250, #557, #686, #687 | Issues | Kein Handschritt nach Software-Wechsel; Umstellung im Speicher; dieses Issue; Nebenbefund |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/schreiben.py` | MODIFY | `routen_speichern` prüft Arten und trägt danach den Plan ein; neue `routen_datei_schreiben` (roh); `plan_sicherstellen` und `routen_normalisieren` nutzen sie; `arten_speichern` trägt einen vorhandenen Plan ein |
| `engine/neu.py` | MODIFY | Zeilen 355 und 1138 auf `routen_datei_schreiben`; `nachziehen` trägt `routen` für Reisen mit Arten und Plan ohne Eintrag nach |
| `engine/texte_de.py` | MODIFY | `schreiben.plan.ohne_arten` |
| `engine/texte_en.py` | MODIFY | `schreiben.plan.ohne_arten` |
| `engine/tests/test_plan_ohne_arten_686.py` | CREATE | Tests dieser Spec |
| `docs/funktionen/alternativen.md`, `docs/funktionen/reisemodell.md` | MODIFY | Nutzersicht: erst Arten, dann Pläne, Auswahlen und Tage (nur die zuständige Seite, wo es passt) |

### Estimated Changes

- Files: 7 (+1 Testdatei)
- LoC: +120/-10
- Risiko: mittel (zentrale Schreibstelle aller Plan-Werkzeuge). Bestehende Tests, die Plan-Werkzeuge an Reisen ohne Arten rufen, werden rot und zeigen, wo bisher still Erfolg gemeldet wurde; sie bekommen vorher Arten (wie `test_neu.py` um Zeile 275: erst Arten, dann Plan).

## Implementation Details

1. `routen_datei_schreiben(reise_dir, roh)` enthält den bisherigen Rumpf von `routen_speichern` (rundes YAML nach `plan/routen.yaml`), ohne Prüfung und ohne Eintragen. `plan_sicherstellen` (Gerüst), `routen_normalisieren` und beide Stellen in `neu.py` rufen sie.
2. `routen_speichern(reise_dir, roh)`: Ist `arten_laden(reise_dir)` leer, `raise Ablehnung("schreiben.plan.ohne_arten")`, bevor etwas geschrieben wird. Sonst `routen_datei_schreiben`, danach `plan_sicherstellen` (legt nichts Vorhandenes neu an, trägt nur `routen` nach, wenn es fehlt).
3. `routen_laden` legt bei fehlender Datei weiter das Gerüst an (roh, ohne Eintrag); die Ablehnung kommt erst beim Speichern. Lesende Wege bleiben ohne Ablehnung.
4. `arten_speichern`: Nach dem Schreiben von `plan/arten.yaml` ruft sie `plan_sicherstellen` auf, wenn `plan/routen.yaml` existiert. Ohne Plan bleibt es wie bisher (Plan entsteht beim ersten Plan-Werkzeug).
5. `neu.py nachziehen`: Hat die Reise Arten, eine `plan/routen.yaml` und keinen Eintrag `routen` in `reise.json`, ruft sie `plan_sicherstellen` (im Vorschaumodus nur Meldung). Zweiter Lauf ändert nichts.
6. Text `schreiben.plan.ohne_arten` in Alltagssprache: Der Plan dieser Reise braucht zuerst Arten; erst `kinds_adopt` (Vorlagen übernehmen) oder `kind_define` nutzen, dann erneut versuchen. Alle Sprachen, keine Texte im Code (ADR-0006, Ausnahmelisten in `test_texte.py` nur kürzer).

## Test Plan

### Automated Tests (TDD RED)

Datei: `engine/tests/test_plan_ohne_arten_686.py`. Reisen entstehen aus einer Kopie der Beispielreise, bei der `plan/arten.yaml`, `plan/routen.yaml` und der Eintrag `routen` in `reise.json` entfernt sind, oder frisch über `trip_create`/die Vorlage; erfundene Daten (Ida, Karl, Tom, Lea). Aufruf wie in den Konnektor-Tests über den Schreibweg.

- [ ] `test_wahlstelle_ohne_arten_wird_abgelehnt`: GIVEN eine Reise ohne Arten WHEN `choice_create` (Schreibweg `wahlstelle_anlegen`) mit Titel und zwei Optionen läuft THEN Ablehnung mit dem Text `schreiben.plan.ohne_arten`, es entsteht keine neue Fassung im Reisespeicher und keine offene Frage F-… bleibt zurück.
- [ ] `test_plan_werkzeuge_ohne_arten_werden_abgelehnt` (parametrisiert): GIVEN dieselbe Reise WHEN `item_create`, `start_end_set`, `day_create`, `fixed_date_set` laufen THEN je Ablehnung mit demselben Text; `reise.json` hat danach kein `routen`.
- [ ] `test_ablehnung_in_allen_sprachen`: GIVEN die Sprachen aus `engine/texte_*.py` WHEN der Schlüssel `schreiben.plan.ohne_arten` aufgelöst wird THEN ist der Text in jeder Sprache vorhanden und nennt `kinds_adopt` und `kind_define`.
- [ ] `test_arten_uebernehmen_traegt_vorhandenen_plan_ein`: GIVEN eine Reise ohne Arten, bei der `plan/routen.yaml` (Gerüst) schon liegt, aber `reise.json` kein `routen` hat WHEN `kinds_adopt` Arten übernimmt THEN hat `reise.json` `routen` mit `datei`, `tagesplan` und `unterkuenfte`, und `choice_create` gelingt danach.
- [ ] `test_art_definieren_traegt_plan_ein`: wie zuvor, mit `kind_define` statt `kinds_adopt`.
- [ ] `test_plan_nach_erstem_werkzeug_sofort_sichtbar`: GIVEN eine Reise mit Arten, aber noch ohne Plan WHEN `choice_create` gelingt THEN steht `routen` in `reise.json` und der Probebau der Reise enthält die Wahlstelle.
- [ ] `test_nachziehen_heilt_altlast`: GIVEN eine Reise mit Arten und `plan/routen.yaml`, ohne `routen` in `reise.json` WHEN `neu.py nachziehen` mit Schreiben läuft THEN steht `routen` darin; ein zweiter Lauf meldet nichts und ändert nichts; im Vorschaumodus bleibt die Datei unverändert und die Meldung erscheint.
- [ ] `test_nachziehen_speicher_beim_veroeffentlichen_heilt_altlast`: GIVEN dieselbe Altlast im Reisespeicher WHEN `nachziehen-speicher` läuft THEN enthält die neue Fassung den Eintrag.
- [ ] `test_roh_schreiben_ohne_arten_erlaubt`: GIVEN eine Reise ohne Arten WHEN `plan_sicherstellen` das Gerüst anlegt und `neu.py umbrechen` schreibt THEN keine Ablehnung (rohe Funktion).
- [ ] `test_beispielreisen_unveraendert` (parametrisiert über `beispielreise`, `stadtwochenende`): GIVEN die Beispielreise mit Arten WHEN ein Plan-Werkzeug (z. B. `option_create`/`question_create`-Folge oder `tag_aendern`) läuft THEN gelingt es wie bisher, `reise.json` und `plan/routen.yaml` bleiben außer dem Gewollten byte-gleich.
- [ ] Bestehend, bleibt grün: `test_hinweis_604.py` (`flach_machen`), `test_neu.py` (Vorlage füllen, Arten zuerst), Textprüfungen in `test_texte.py`, Betriebstests; Tests, die Plan-Werkzeuge an Reisen ohne Arten rufen, bekommen Arten oder erwarten die Ablehnung.

## Acceptance Criteria

- **AC-1:** Given eine Reise ohne Arten / When `choice_create` mit zwei Optionen läuft / Then lehnt der Schreibweg mit `schreiben.plan.ohne_arten` ab, es gibt keine neue Fassung und keine offene Frage F-… ohne Wahlstelle. Test: `test_wahlstelle_ohne_arten_wird_abgelehnt`.
- **AC-2:** Given eine Reise ohne Arten / When `item_create`, `start_end_set`, `day_create` oder `fixed_date_set` laufen / Then lehnt jedes mit demselben Text ab und `reise.json` bleibt ohne `routen`. Test: `test_plan_werkzeuge_ohne_arten_werden_abgelehnt`.
- **AC-3:** Given der Ablehnungstext / When er in jeder Sprache aufgelöst wird / Then ist er vorhanden und nennt den Weg über Arten (`kinds_adopt`, `kind_define`); der Text steht nur in den `texte_<sprache>.py`. Test: `test_ablehnung_in_allen_sprachen`.
- **AC-4:** Given eine Reise ohne Arten, aber mit Gerüst `plan/routen.yaml` / When Arten übernommen oder definiert werden / Then steht `routen` sofort in `reise.json` und der Plan ist ohne weiteres Werkzeug sichtbar und beschreibbar. Tests: `test_arten_uebernehmen_traegt_vorhandenen_plan_ein`, `test_art_definieren_traegt_plan_ein`.
- **AC-5:** Given eine Reise mit Arten und noch ohne Plan / When das erste Plan-Werkzeug gelingt / Then ist der Plan eingetragen und im Probebau enthalten. Test: `test_plan_nach_erstem_werkzeug_sofort_sichtbar`.
- **AC-6:** Given eine Reise mit Arten und `plan/routen.yaml`, aber ohne `routen` / When `neu.py nachziehen` (auch über `nachziehen-speicher` beim Veröffentlichen) läuft / Then wird der Eintrag ergänzt, ein zweiter Lauf ändert nichts, die Vorschau schreibt nichts. Tests: `test_nachziehen_heilt_altlast`, `test_nachziehen_speicher_beim_veroeffentlichen_heilt_altlast`.
- **AC-7:** Given die rohe Funktion / When Gerüst, `umbrechen` und `nachziehen` in einer Reise ohne Arten schreiben / Then lehnen sie nicht ab. Test: `test_roh_schreiben_ohne_arten_erlaubt`.
- **AC-8:** Given die beiden Beispielreisen / When Plan-Werkzeuge laufen und der Generator baut / Then verhalten sie sich wie bisher, ohne Änderung an den Beispielreisen. Test: `test_beispielreisen_unveraendert`.
- **AC-9:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen.

## Definition of Done

- [ ] Rote Tests bestätigt, danach Korrektur, Tests grün
- [ ] Gesamtlauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün
- [ ] Doku unter `docs/funktionen/` nachgezogen
- [ ] Tests der einbindenden Instanzen mit dem Zweig gelaufen (Text einer Ablehnung geändert)
- [ ] Pflichtprüfungen der CI grün, ausgeliefert, Konnektor auf dem Server neu gestartet
- [ ] Issue #686 mit Abschlusskommentar geschlossen; Nebenbefund als #687 bleibt offen

## Known Limitations

- Ein Plan-Werkzeug in einer Reise ohne Arten wird abgelehnt, auch wenn es heute scheinbar „funktioniert“. Es wirkte bisher nie sichtbar (der Generator las den Plan nicht), die Ablehnung macht die Lücke nur ehrlich.
- Die Meldungen zu gelöschten Testreisen in `my_trips` sind nicht Teil dieser Änderung (#687).

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Fehlerkorrektur im Sinne der bestehenden Bau-Regel (Plan braucht Arten, ADR-0001 und ADR-0011 bleiben unberührt); keine neue Grundform, kein neues Datenformat, nur eine zentrale Prüfung und eine Umstellung bestehender Reisen in `nachziehen`.

## Changelog

- 2026-11-24: Initial spec created (Entwurf) für #686.
