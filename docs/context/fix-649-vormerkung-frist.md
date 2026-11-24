# Context: fix-649-vormerkung-frist

## Request Summary
Befund F006 aus der zweiten Prüfung von #582: Der tägliche Wächter verwirft eine unbestätigte Vormerkung einer Fotolöschung
auch, wenn der zugehörige Vorgang von `bild_entfernen` gerade läuft. Scheitert danach zusätzlich das Bestätigen, fehlt die
Zeile, und das Nachholen des Leerens entfällt. Abhilfe: Vormerkungen erst nach einer Frist (eine Stunde) verwerfen, mit Test.

## Related Files
| File | Relevance |
|------|-----------|
| engine/konten.py | Tabelle `bild_loeschungen` (Schema ~Z. 180, nachträgliche Spalten `BILD_LOESCHUNG_SPALTEN` ~Z. 1292, Ergänzung in `db()` ~Z. 223), `bild_loeschung_vormerken`, `_bestaetigen`, `_verwerfen`, `bild_loeschungen()` |
| engine/waechter.py | `_bildloeschung_nachholen` (~Z. 547): unbestätigte Zeile + Eintrag nicht entfernt → `bild_loeschung_verwerfen` |
| engine/schreiben.py | `ordner_als_vorgang`-Pfad (~Z. 5677): vormerken → Vorgang → `bild_endgueltig_entfernen` (bestätigen, leeren); Zeitgrenze des Vorgangs `timeout` (Sekunden, Rest der Anfragezeit) |
| engine/tests/test_bilder_eigen.py | `test_liegengebliebene_vormerkung_ohne_vorgang_schadet_nicht` erwartet heute sofortiges Verwerfen (muss die Zeit vorstellen), `test_alte_protokollzeilen_ohne_neue_spalten_gelten_weiter` (Formatwechsel) |
| docs/betrieb.md Z. 114 | beschreibt „eine Vormerkung ohne festgeschriebenen Vorgang verwirft der Wächter“ — um die Frist ergänzen |
| docs/specs/oberflaeche/bilder-582-eigene-fotos.md | Spec von #582 |

## Existing Patterns
- Zeit in der Kontendatenbank als REAL-Sekunden (UTC) über `konten._jetzt()` (z. B. `reise_loeschung.wann`, `hochladelinks.erstellt`); Tests stellen die Zeit mit `monkeypatch.setattr(konten, "_jetzt", ...)` vor.
- Spalte `datum` von `bild_loeschungen` ist nur das Tagesdatum (Löschprotokoll: nur Kennung und Datum) → reicht nicht für eine Frist in Stunden.
- Neue Spalten älterer Datenbanken: Eintrag in `BILD_LOESCHUNG_SPALTEN`, `db()` ergänzt beim Öffnen (kein Handschritt, #250).
- Fristen als Modulkonstante in `konten.py` (z. B. `HOCHLADELINK_MINUTEN`).

## Dependencies
- Upstream: `konten.db()`, `konten._jetzt()`, `bilder.entfernt`.
- Downstream: `waechter.bildloeschungen_nachholen` (täglicher Lauf `waechter.py loeschen`), Schreibweg `schreiben.py`.

## Existing Specs
- `docs/specs/oberflaeche/bilder-582-eigene-fotos.md`

## Risks & Considerations
- Zeilen von vor der neuen Spalte (Default 0 = „sehr alt“) werden wie bisher verworfen — richtig, die stammen aus der Zeit vor dem Update und sind sicher älter als eine Stunde.
- Bestätigte Zeilen bleiben unberührt (Frist gilt nur für unbestätigte).
- Eine junge unbestätigte Zeile, deren Eintrag im neuesten Stand schon entfernt ist, wird weiter sofort bestätigt (kein Grund zu warten).
- Die Frist muss deutlich über der Zeitgrenze eines Schreibvorgangs liegen (Sekunden); eine Stunde genügt.

## Analysis

### Type
Bug (Befund F006, LOW, Nachtrag zu #582)

### Ursache
`waechter._bildloeschung_nachholen` verwirft jede unbestätigte Zeile, deren Eintrag im neuesten Stand nicht entfernt ist –
ohne Blick auf ihr Alter. Die Tabelle kennt nur das Tagesdatum (`datum`), also keinen Zeitpunkt der Vormerkung. Läuft der
Wächter genau zwischen Vormerkung und Festschreiben des Vorgangs (Fenster: Sekunden, `timeout` des Vorgangs), verschwindet
die Zeile; scheitert danach auch `bild_loeschung_bestaetigen`, fehlt das Protokoll und das Leeren wird nie nachgeholt.

Nebenbefund derselben Lücke: `bild_loeschung_vormerken` lässt eine schon vorhandene unbestätigte (alte, liegengebliebene)
Zeile unverändert und liefert False. Ohne Auffrischen des Zeitpunkts hätte so eine neue Vormerkung das Alter der alten und
würde trotz Frist sofort verworfen → beim UPDATE einer unbestätigten Zeile den Zeitpunkt neu setzen.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/konten.py | MODIFY | Spalte `vorgemerkt REAL NOT NULL DEFAULT 0` (Schema + `BILD_LOESCHUNG_SPALTEN`, Ergänzung beim Öffnen); Konstante `BILD_VORMERKUNG_FRIST = 3600` (Sekunden); `bild_loeschung_vormerken` schreibt `_jetzt()` (INSERT und UPDATE einer unbestätigten Zeile); `bild_loeschung_verwerfen(reise, bid, nur_aelter_als=None)` – mit Angabe nur Zeilen mit `vorgemerkt <= _jetzt() - nur_aelter_als` (Prüfung atomar im DELETE, kein Wettlauf zwischen Lesen und Löschen); `bild_loeschungen()` liefert zusätzlich `vorgemerkt` |
| engine/waechter.py | MODIFY | `_bildloeschung_nachholen`: verwirft nur mit `nur_aelter_als=konten.BILD_VORMERKUNG_FRIST`; eine junge Vormerkung bleibt unangetastet (nächster Lauf); Docstring |
| engine/schreiben.py | — | unverändert: sein `bild_vormerkung_verwerfen` nach gescheitertem Vorgang verwirft weiter ohne Frist (eigene Vormerkung) |
| engine/tests/test_bilder_eigen.py | MODIFY/ADD | neuer Test: junge Vormerkung, Eintrag nicht entfernt → Wächter lässt sie stehen; Bestätigen klappt danach normal; Test „liegengebliebene Vormerkung“ stellt `konten._jetzt` über die Frist vor; Test: erneute Vormerkung auf alter unbestätigter Zeile frischt den Zeitpunkt auf; Formatwechsel-Test erwartet `vorgemerkt: 0` (alte Zeilen gelten als alt) |
| docs/betrieb.md | MODIFY | Z. 114: „eine Vormerkung ohne festgeschriebenen Vorgang verwirft der Wächter nach einer Stunde“ |

### Scope Assessment
- Files: 4 (konten, waechter, Test, betrieb.md)
- Estimated LoC: +40/-8
- Risk Level: LOW – nur unbestätigte Zeilen des Foto-Löschprotokolls; bestätigte Zeilen und der Weg „Eintrag entfernt → bestätigen“ bleiben unverändert

### Technical Approach
Zeitpunkt der Vormerkung als REAL-Sekunden (UTC, `konten._jetzt()`) wie bei `hochladelinks.erstellt`. Frist als Modulkonstante
(eine Stunde, weit über der Zeitgrenze eines Schreibvorgangs). Die Altersprüfung steckt im DELETE von
`bild_loeschung_verwerfen` (Parameter), damit eine zwischen Lesen und Verwerfen aufgefrischte Vormerkung nicht verloren geht.
Formatwechsel automatisch beim Öffnen der Datenbank (`db()`), Default 0 → Zeilen von vorher gelten als alt (#250, kein
Handschritt, kein `nachziehen` nötig, da Kontendatenbank, nicht Reisedaten).

Alternativen verworfen: Frist über das Tagesdatum `datum` (zu grob, Wächter läuft täglich kurz nach Mitternacht → ein
Vorgang vom Vortag 23:59 wäre jung, einer von 00:00 nicht unterscheidbar); Prüfung nur im Wächter per `_jetzt()` ohne SQL-
Bedingung (Wettlauf mit erneuter Vormerkung).

### Dependencies
- Upstream: `konten.db()`, `konten._jetzt()`, `bilder.entfernt`
- Downstream: `waechter.bildloeschungen_nachholen` (täglich), Schreibweg `schreiben.py` (ruft `bild_loeschung_verwerfen` ohne Frist – Signatur bleibt kompatibel)
- Instanz: keine Änderung an Meldungstexten, Umgebungswerten oder Schnittstellen; Spalte wird beim Öffnen ergänzt

### Open Questions
- keine (Frist 1 Stunde steht im Issue-Plan; rein technisch)
