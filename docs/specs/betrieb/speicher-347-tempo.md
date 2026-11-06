---
entity_id: speicher-347-tempo
type: refactor
created: 2026-11-06
updated: 2026-11-06
status: draft
workflow: speicher-347-tempo
---

# Schreibweg über den Reisespeicher: zwei Tempo-Änderungen ohne Formatänderung (#347)

Grundlage: `docs/context/speicher-347-tempo.md` (Kontext und Analyse), Messung im Issue #347 (cProfile, 6.11.2026).

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** keine (reine Tempo-Änderung innerhalb von ADR-0009; Format, Schnittstelle und Verhalten des Reisespeichers bleiben, der Kern aus ADR-0001 ist nicht berührt)

## Purpose

Der Schreibweg über den Reisespeicher ist bei einer großen Reise (110-MB-Testreise) 3- bis 4-mal langsamer als Git (Mittel 5,4 s statt 1,6 s je Vorgang) und hält die Sperre je Reise so lange, dass im parallelen Lauf 5 Anfragen mit 429 abgewiesen wurden. Das Profil nennt zwei Stellen, die ohne jede Formatänderung schneller werden: (1) `ordner_als_vorgang` holt den ganzen Vorher-Stand als Bytes, nur um ihn mit dem Ordner zu vergleichen; (2) die Abfrage in `_stand` holt die Spalte `inhalt` für alle Versionen aller Pfade statt nur für die neuesten.

## Ziel

Beide Stellen sind umgebaut, das Verhalten bleibt Byte für Byte gleich, und der Messlauf (`betrieb/messlauf-schreibweg.py --auffuellen 110`) zeigt eine messbar kürzere Zeit je Vorgang. Eine Zahl wird nicht versprochen: erwartet sind rund 2,5 s statt rund 4,7 s je Vorgang. „So schnell wie Git“ (1,6 s) wird damit voraussichtlich nicht erreicht; das wird im Issue offen so benannt.

## Source

- **File:** `engine/reisespeicher.py`
- **Identifier:** `_stand`, `ordner_als_vorgang`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `_stand(v, reise, bis, spalte)` | Funktion | Aufrufer: `_eintragen` (Prüfsumme), `importieren` (Prüfsumme), `zuruecksetzen` (Inhalt, zwei Stände), `aktueller_stand` und damit `exportieren` und der Dienst (Inhalt) |
| `ordner_als_vorgang` | Funktion | einziger Aufrufer: `engine/schreiben.py` (Schreibweg) |
| `_summe` | Funktion | SHA-256 des Inhalts; die Prüfsumme, die `_eintragen` schon als Maßstab für „unverändert“ nimmt |
| `versionen` (PK `(vorgang, pfad)`, Index `versionen_pfad (reise, pfad, vorgang)`) | Tabelle | kein Schemawechsel |
| `betrieb/messlauf-schreibweg.py` | Skript | unverändert, für die Wiederholung der Messung |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/reisespeicher.py` | MODIFY | `_stand`: Abfrage in zwei Stufen; `ordner_als_vorgang`: Vergleich über Prüfsummen |
| `engine/tests/test_reisespeicher.py` | MODIFY | Gleichheitstests gegen eine Referenzabfrage (alte Form) und Tests für `ordner_als_vorgang` |

### Estimated Changes

- Files: 2
- LoC: +30/-15 (Code), +80 (Tests)

### Nicht im Scope

- Format der Datenbank, Schema, Schnittstelle (Rückgabewerte, Ausnahmen `KeyError`, `NichtsGeaendert`, `StandGeaendert`), Meldungstexte.
- Der Probebau (zweimal, rund 1,2 s) und die Fotos in der Datenbank (Stufe 4, #349).
- Prüfsummen von außen mitgeben, um in `_eintragen` nicht neu zu hashen (spart nur rund 0,3 s).
- Umschalten einer echten Reise auf den Speicherweg (`FR_SPEICHERREISEN` bleibt leer).

## Implementation Details

1. **`_stand` in zwei Stufen, eine Abfrage.** Innen läuft die Fensterfunktion nur über `pfad`, `vorgang` und `inhalt IS NULL AS weg` der Versionen im Stand `bis` (Tombstone-Erkennung bleibt an `inhalt`, nicht an `pruefsumme`, damit eine leere Datei nicht als gelöscht gilt). Außen werden die Gewinner-Zeilen (`rang = 1 AND NOT weg`) per Primärschlüssel `(vorgang, pfad)` mit `versionen` verbunden, und erst dort wird die gewünschte Spalte gelesen. `ORDER BY pfad` bleibt. Keine Schleife je Pfad. Vor dem Festlegen wird mit `EXPLAIN QUERY PLAN` und einer Zeitmessung auf der 110-MB-Testreise geprüft, dass SQLite die Inhalte nicht doch in die Sortierung kopiert; sonst wird die Innenabfrage als `MATERIALIZED`-CTE geschrieben.
2. **`ordner_als_vorgang` vergleicht Prüfsummen.** Der Vorher-Stand kommt als `_stand(..., spalte="pruefsumme")` in einer eigenen kurzen Verbindung wie bisher; unbekannte Basis ergibt weiter einen leeren Vorher-Stand (`KeyError` abgefangen), `basis=0` ebenso. `nachher` bleibt Bytes (wird zum Schreiben gebraucht). Eine Datei gilt als geändert, wenn `vorher.get(p) != _summe(b)`; fehlende Dateien werden wie bisher als Tombstone geschrieben.
3. **Messlauf wiederholen.** Nach dem Umbau läuft `betrieb/messlauf-schreibweg.py --auffuellen 110` erneut; die Zahlen (Mittel je Vorgang, Anzahl 429) kommen als Kommentar ins Issue, vorher/nachher nebeneinander, auch wenn das Ziel verfehlt wird.

## Expected Behavior

- **Input:** unverändert (`reise`, `bis`, `spalte`; `reise`, `ordner`, `basis`, …).
- **Output:** exakt dieselben Rückgabewerte, Reihenfolgen und Ausnahmen wie vorher; nur die Rechenzeit sinkt.
- **Side effects:** keine; es entstehen weder neue Spalten noch neue Dateien.

## Test Plan

### Automated Tests (TDD RED)

Die Gleichheitstests vergleichen `_stand` mit einer Referenzabfrage in der alten Form, die im Test steht. Sie sind vor dem Umbau grün, weil sie Verhalten festhalten; rot ist nur der Test, der die Zweistufigkeit prüft (Test 1).

- [ ] Test 1 (`test_stand_holt_inhalt_nur_fuer_neueste_versionen`): GIVEN eine Reise, in der eine Datei in vielen Versionen vorliegt / WHEN `_stand` mit `spalte="inhalt"` läuft / THEN liest SQLite nur die Inhalte der neuesten Versionen (Nachweis über `EXPLAIN QUERY PLAN` des Statements: die Inhaltsspalte steht nicht in der Fenster-Unterabfrage).
- [ ] Test 2 (`test_stand_gleich_referenz`): GIVEN mehrere Versionen je Pfad, geänderte und unveränderte Dateien / WHEN `_stand` für `inhalt` und `pruefsumme` läuft / THEN gleich der Referenzabfrage, gleiche Reihenfolge der Pfade.
- [ ] Test 3 (`test_stand_tombstone_und_neu_angelegt`): GIVEN ein gelöschter Pfad und ein gelöschter, danach neu angelegter Pfad / THEN fehlt der erste, der zweite hat den neuen Inhalt.
- [ ] Test 4 (`test_stand_leere_datei_ist_nicht_geloescht`): GIVEN eine Datei mit `b""` / THEN steht sie im Stand (mit leerem Inhalt und der Prüfsumme der leeren Eingabe).
- [ ] Test 5 (`test_stand_bis`): GIVEN mehrere Stände / WHEN `bis` ein früherer Stand ist / THEN gleich der Referenz; unbekannte Reise oder unbekannter Stand: `KeyError` wie bisher.
- [ ] Test 6 (`test_ordner_als_vorgang_ohne_aenderung`): GIVEN ein Ordner gleich dem Stand `basis` / THEN `NichtsGeaendert`.
- [ ] Test 7 (`test_ordner_als_vorgang_aenderung_und_loeschung`): GIVEN geänderte, neue und fehlende Dateien / THEN ein Vorgang mit genau diesen Unterschieden, fehlende als Tombstone.
- [ ] Test 8 (`test_ordner_als_vorgang_unbekannte_basis_und_basis_null`): GIVEN `basis=0` und eine unbekannte Basis / THEN alle Dateien als neu, wie bisher.
- [ ] Test 9 (`test_ordner_als_vorgang_holt_keine_inhalte_des_vorher_standes`): GIVEN ein Ordner / WHEN `ordner_als_vorgang` läuft / THEN wird `_stand` mit `spalte="pruefsumme"` aufgerufen (Aufrufspur), nicht `aktueller_stand`.

Vorhandene Tests (`test_reisespeicher.py` 40, `test_schreiben_speicher.py`, `test_stand.py`, `test_betrieb.py`) bleiben unverändert grün; sie sind das Netz.

### Manuelle Prüfung

- Messlauf `betrieb/messlauf-schreibweg.py --auffuellen 110` vor und nach dem Umbau; Zahlen ins Issue #347.
- Prüfung an der Testreise bleibt Pflicht, bevor die erste echte Reise auf den Speicherweg geschaltet wird.

## Acceptance Criteria

- **AC-1:** Given eine Reise mit vielen Versionen je Pfad / When `_stand` den Stand bildet / Then liest die Abfrage die gewünschte Spalte nur für die jeweils neueste Version je Pfad, in einer Abfrage und ohne Schleife je Pfad (Test 1).
- **AC-2:** Given beliebige Reisen mit Löschungen, neu angelegten Pfaden, leeren Dateien und Stand `bis` / When `_stand` läuft / Then sind Ergebnis, Reihenfolge und Ausnahmen gleich dem Verhalten vor dem Umbau (Test 2 bis 5).
- **AC-3:** Given ein Ordner und eine Basis / When `ordner_als_vorgang` läuft / Then entstehen dieselben Vorgänge und Ausnahmen wie vorher, und der Vorher-Stand wird über Prüfsummen statt Bytes gebildet (Test 6 bis 9).
- **AC-4:** Given die 110-MB-Testreise / When der Messlauf nach dem Umbau läuft / Then liegt das Mittel je Vorgang unter dem Wert vor dem Umbau (5,4 s), und die Zahlen stehen vorher/nachher im Issue; das Verfehlen von 1,6 s (Git) wird offen benannt.
- **AC-5:** Given der Branch / When `engine/.venv/bin/python -m pytest -q engine/tests` läuft / Then ist alles grün ohne echte Reisen, und die vorhandenen Tests sind unverändert.

## Risks

- **Netto-Ersparnis kleiner als im Issue:** Hash über 110 MB kostet rund 0,3 s; erwartet ist rund 1,2 s Ersparnis bei Punkt 2 statt 1,5 s. Der Messlauf entscheidet, nicht die Schätzung.
- **SQLite kopiert die Inhalte trotzdem in die Sortierung:** dann `MATERIALIZED`-CTE (siehe Implementation Details 1); Test 1 hält die Zusage fest.
- **Tombstone und leere Datei verwechselt:** Erkennung bleibt an `inhalt IS NULL` (Test 4).
- **Betrieb:** `FR_SPEICHERREISEN` ist leer, keine echte Reise nutzt den Speicherweg; das Risiko ist niedrig.

## Definition of Done

- [ ] AC-1 bis AC-3 durch Test 1 bis 9 belegt
- [ ] Messlauf nach dem Umbau im Issue #347, vorher/nachher
- [ ] Vollständiger Testlauf grün, Pflichtprüfungen der CI grün, Weg nach `main` wie üblich
- [ ] Issue #347 erst schließen, wenn alles dazu erledigt ist (Stufen 3/4 laufen unter eigenen Issues)

## Changelog

- 2026-11-06: Initiale Spec (#347, Tempo-Nachbesserung zu Stufe 2)
