# Context: speicher-347-tempo

## Request Summary
Der Schreibweg über den Reisespeicher (#347, ausgeliefert mit PR #362) ist bei großen Reisen (110-MB-Testreise) 3- bis 4-mal langsamer als Git (Mittel 5,4 s statt 1,6 s je Vorgang) und hält im parallelen Lauf die Sperre je Reise so lange, dass 5 Anfragen mit 429 abgewiesen wurden. Die Aufschlüsselung im Issue (cProfile, 6.11.2026) nennt zwei kleine Ansatzpunkte ohne Formatänderung. Ziel: beide umsetzen, danach den Messlauf wiederholen.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/reisespeicher.py:150` `_stand` | Fensterabfrage (ROW_NUMBER über alle Versionen der Reise) holt die Spalte `inhalt` für alle Versionen, nicht nur für die neuesten; rund 1,3 s SQL-Zeit auf der Testreise (Ansatzpunkt 2) |
| `engine/reisespeicher.py:237` `ordner_als_vorgang` | holt über `aktueller_stand(reise, basis)` alle Dateien als Bytes, nur um sie mit dem Ordner zu vergleichen; rund 1,5 s (Ansatzpunkt 1) |
| `engine/reisespeicher.py:169` `_eintragen` | liest den Stand noch einmal über `_stand(spalte="pruefsumme")` und vergleicht Prüfsummen; Vorbild für den Vergleich in Ansatzpunkt 1 |
| `engine/reisespeicher.py:291` `aktueller_stand`, `:316` `exportieren` | Export in die Arbeitskopie (Dienst), nutzt `_stand` mit Inhalt |
| `engine/reisespeicher.py:371` `importieren`, `:388` `zuruecksetzen` | weitere Aufrufer von `_stand` (Prüfsumme bzw. Inhalt, zwei Stände) |
| `engine/schreiben.py:4776` | einzige Aufrufstelle von `ordner_als_vorgang` im Schreibweg; Frist über `self.rest()` |
| `betrieb/messlauf-schreibweg.py` | Messlauf mit `--auffuellen 110`, für die Wiederholung der Messwerte |
| `engine/tests/test_reisespeicher.py` (40 Tests), `test_schreiben_speicher.py`, `test_stand.py`, `test_betrieb.py` | Absicherung; Verhalten darf sich nicht ändern |
| `docs/context/speicher-347-stufe2.md`, `docs/specs/betrieb/schreibweg-speicher-347.md`, `docs/context/reisespeicher-346.md` | bisherige Analyse und Spec der Stufen 1 und 2 |

## Existing Patterns
- `_stand(v, reise, bis, spalte)` ist die eine Stelle, die den Stand einer Reise bildet (neueste Version je Pfad, Tombstones ausgenommen). `spalte="pruefsumme"` gibt es schon und wird von `_eintragen` und `importieren` genutzt.
- Die Prüfsumme ist SHA-256 des Inhalts (`_summe`); `_eintragen` überspringt Dateien mit gleicher Prüfsumme. Der Vergleich über Prüfsummen ist also schon die Regel für „unverändert“.
- Nur anhängen: `versionen` wird nie geändert; der neueste Stand je Pfad ergibt sich allein aus `vorgang`-Nummer und `stand`.

## Dependencies
- Upstream: SQLite (Fensterfunktionen), `hashlib`.
- Downstream: Schreibweg (`schreiben.py`), `stand.py`/`stand_git.py`-Weg für Speicherreisen, Export in die Arbeitskopie, `betrieb/messlauf-schreibweg.py`, `importieren`/`zuruecksetzen`/`pruefen`. Die öffentliche Schnittstelle (Rückgabewerte, Ausnahmen `KeyError`, `NichtsGeaendert`, `StandGeaendert`) darf sich nicht ändern.

## Existing Specs
- `docs/specs/betrieb/schreibweg-speicher-347.md` (Stufe 2, ausgeliefert): AC-24 Messlauf; die Tempo-Änderung ändert kein Verhalten, nur die Zeit.
- `docs/specs/betrieb/reisespeicher-346.md` (Schnittstelle des Speichers).

## Risks & Considerations
- Verhalten muss Byte für Byte gleich bleiben: gleicher Stand, gleiche Ausnahmen, gleiche Reihenfolge (`ORDER BY pfad`). Die vorhandenen 40 Speicher-Tests plus Schreibweg-Tests sind das Netz; für beide Änderungen kommen Tests dazu (gleiches Ergebnis wie vorher, Tombstones, mehrere Versionen je Pfad, Stand `bis`).
- Ansatzpunkt 1: Prüfsumme der Dateien im Ordner wird nach dem Lesen berechnet (SHA-256 über 110 MB kostet im Prozess rund 0,3 s). Das ist deutlich weniger als die 1,5 s fürs Holen der Bytes, die Ersparnis ist aber netto kleiner als im Issue angegeben. Im Messlauf prüfen.
- Ansatzpunkt 2: Zuerst nur (pfad, vorgang) der jeweils neuesten Version bestimmen, dann die Inhalte dieser Versionen holen. Muss mit `bis`, Tombstones und Pfaden, die erst gelöscht und dann neu angelegt wurden, gleich rechnen. Eine Zweitabfrage je Pfad vermeiden (viele kleine Abfragen sind bei vielen Dateien langsamer als eine).
- Im Betrieb ist `FR_SPEICHERREISEN` leer; keine echte Reise nutzt den Speicherweg. Das Risiko für den Betrieb ist niedrig, die Prüfung an der Testreise bleibt trotzdem Pflicht, bevor die erste echte Reise umgeschaltet wird.
- Der Rest (Probebau zweimal, rund 1,2 s) und die Fotos in der Datenbank (bis Stufe 4, #349) bleiben ausdrücklich außerhalb dieses Vorhabens.

## Analysis

### Type
Feature (reine Tempo-Änderung, kein neues Verhalten). Nachbesserung zu #347, Stufe 2.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/reisespeicher.py` `_stand` | MODIFY | Zweistufig in einer Abfrage: innen nur (pfad, vorgang, weg) der neuesten Version je Pfad (Fenster ohne Inhalt in der Sortierung), außen Join auf `versionen` über den Primärschlüssel (vorgang, pfad) und erst dort die Spalte holen |
| `engine/reisespeicher.py` `ordner_als_vorgang` | MODIFY | Vorher-Stand als Prüfsummen (`_stand(..., spalte="pruefsumme")`) statt Bytes; Dateien des Ordners mit `_summe` vergleichen; gleiche Ausnahmen (`KeyError` bei unbekannter Basis → leerer Vorher-Stand) |
| `engine/tests/test_reisespeicher.py` | MODIFY | Gleichheitstests alt/neu (Referenz-Abfrage im Test), Tombstones, gelöschter und neu angelegter Pfad, mehrere Versionen je Pfad, `bis`, leere Datei (b"" ≠ gelöscht), `ordner_als_vorgang` ohne Änderung / mit Änderung / mit Löschung / unbekannter Basis |
| `betrieb/messlauf-schreibweg.py` | unverändert | nur erneut laufen lassen (`--auffuellen 110`), Messwerte ins Issue |

### Scope Assessment
- Files: 1 Code-Datei, 1 Testdatei; keine Formatänderung, keine Textänderung
- Estimated LoC: +30/-15 (Code), +80 (Tests)
- Risk Level: LOW (Betrieb: `FR_SPEICHERREISEN` leer, keine echte Reise betroffen; Netz sind 40 Speicher-Tests plus Schreibweg-Tests)

### Technical Approach
1. `_stand`: Eine Abfrage, zwei Stufen. Die Fensterfunktion läuft nur über `pfad`, `vorgang` und `inhalt IS NULL` (Tombstone-Erkennung bleibt an `inhalt`, nicht an `pruefsumme`, damit eine leere Datei nicht als gelöscht gilt). Der Join holt die gewünschte Spalte nur für die Gewinner-Zeilen per Primärschlüssel. Eine Abfrage, keine Schleife je Pfad. Ergebnis, Sortierung (`ORDER BY pfad`) und Ausnahmen bleiben gleich. Vor dem Bauen mit `EXPLAIN QUERY PLAN` und Zeitmessung auf der 110-MB-Testreise prüfen, dass SQLite die Inhalte nicht doch in die Sortierung kopiert; sonst `MATERIALIZED`-CTE.
2. `ordner_als_vorgang`: Vorher als Prüfsummen holen (eigene kurze Verbindung wie bisher), `nachher` bleibt Bytes (wird zum Schreiben gebraucht), Vergleich `vorher.get(p) != _summe(b)`. Rund 0,3 s SHA-256 statt rund 1,5 s Bytes holen; die Ersparnis ist netto kleiner als im Issue (rund 1,2 s).
3. Erwartung: von rund 4,7 s auf rund 2,5 s je Vorgang; die 429er im Parallellauf sollten verschwinden oder deutlich weniger werden. „So schnell wie Git“ (1,6 s) wird damit nicht erreicht; der Rest (Probebau zweimal, Fotos in der Datenbank) bleibt bei #349 bzw. außerhalb.

### Dependencies
- Aufrufer von `_stand`: `_eintragen` (Prüfsumme), `importieren` (Prüfsumme), `zuruecksetzen` (Inhalt, zwei Stände), `aktueller_stand` (Inhalt; Export, Dienst)
- Einziger Aufrufer von `ordner_als_vorgang`: `engine/schreiben.py:4776`
- Indizes vorhanden: PK `(vorgang, pfad)` und `versionen_pfad (reise, pfad, vorgang)`; kein Schemawechsel

### Befunde, die gegen den Plan sprechen
- Netto-Ersparnis bei Punkt 1 kleiner als im Issue genannt (Hash-Kosten); der Messlauf entscheidet, keine Zahl versprechen.
- Das Ziel „so schnell wie Git“ wird mit diesen zwei Punkten voraussichtlich nicht erreicht; im Issue offen benennen.
- Alternative „Prüfsummen mitgeben statt in `_eintragen` neu zu hashen“ spart nur rund 0,3 s und bleibt außen vor.

### Open Questions
- [ ] Keine für den Product Owner. Technisch bis zur Messung offen: Reicht die zweistufige Abfrage, oder kopiert SQLite die Inhalte trotzdem (dann `MATERIALIZED`-CTE)?
