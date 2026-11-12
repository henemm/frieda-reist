# Context: Konnektor ohne Zugang „Rolle ohne Person“ (#426)

## Request Summary
Seit #421 erreicht man den Konnektor nur über das Konto; die sprechende Person steht immer fest. Der interne Zugang
`{"reise", "rolle"}` ohne Person (aus der Zeit der Links) samt Namensfeld der Werkzeuge und den Texten für „Link ohne
Person“ soll weg; die Tests, die ihn nutzen, laufen danach mit Personen der Beispielreisen. Keine sichtbare Änderung.

## Related Files
| File | Relevance |
|------|-----------|
| engine/konnektor.py:240 | `wer_spricht`: Zweig `zugang.get("rolle")` liefert `{"rolle", "name": None}` – entfällt |
| engine/konnektor.py:2401 | einziger Einstieg von außen (Konto): `{"reise", "person", "konto_id"}`, `args.pop("name")` (aber nicht `vorname`) |
| engine/konnektor.py:3024, 3075, 3288 | Aufrufer von `wer_spricht` (Anleitung, `werkzeug`, `werkzeuge_fuer`) mit Rückfall auf `{"rolle": "gast"}` |
| engine/konnektor.py:1593 | Kopieren aus einer anderen Reise: `wer_spricht` je Reise, None = keine Person dort |
| engine/konnektor.py:1560, 1952, 3102, 3114, 3149, 3202 | `wer["name"] or args.get("name"/"vorname")` – Rückfall auf Namensargument, wird tot |
| engine/konnektor.py:1900, 1994, 1562, 3202 | Fehlertexte `entscheiden.2`, `einladen.6`, `ontologie_werkzeug.7`, `werkzeug.14` bei `name` None |
| engine/konnektor.py:3035–3048 | Anleitung: `du_ohne_name`, `mit.vorname` bei `name` None |
| engine/konnektor.py:2511, 2515 ff. | Schemas: `name` in `rueckmeldung_geben`, `NAME_FELD` als `name`/`vorname` in ~20 Werkzeugen |
| engine/konnektor.py:1979 | `einladen` nutzt `vorname` für die eingeladene Person – NICHT `NAME_FELD`, bleibt |
| engine/texte_de.py, engine/texte_en.py | Schlüssel `konnektor.einladen.6`, `.entscheiden.2`, `.ontologie_werkzeug.7`, `.werkzeug.14`, `anleitung.du_ohne_name`, `anleitung.mit.vorname`, `feld.name_feld`, `werkzeug.rueckmeldung_geben.name`; Platzhalter `{vorname}` in `anleitung.mit` |
| engine/tests/conftest.py:86 | `mcp_intern` reicht `rolle` aus der Kurznamen-Datei durch |
| engine/tests/test_konnektor.py:22–24 | `MITREISEND` (Rolle ohne Person), `GAST` (Rolle gast ohne Person), ~70 Verwendungen |
| engine/tests/test_packliste.py | importiert `GAST` aus test_konnektor |
| engine/tests/test_regeln.py | eigene Zugänge, legt Gast `kim` per Fixture in die Reise (Muster für Gast als Person) |
| beispiel/reisen/beispielreise/reise.yaml | Personen nur `ida` (organisator), `karl` (mitwirkend); kein Gast |

## Existing Patterns
- Personen-Zugang in Tests: Kurzname → `{"reise", "person"}` (`KARL`, `ALT_ORGANISATOR`, `WEG`).
- Gast als Person: test_regeln ergänzt `kim` (rolle gast) in einer Kopie der Reise.
- Texte nur im Katalog; Prüfung `test_texte.py` (Ausnahmelisten nur kürzer); ungenutzte Schlüssel prüft der Katalogtest.

## Dependencies
- Upstream: `rueckmeldungen.personen_mit_einladungen`, `regeln.rolle_neu/darf`.
- Downstream: alle Schreibwerkzeuge des Konnektors, Anleitung (`initialize`), `tools/list`.

## Existing Specs
- docs/konnektor.md (Konnektorbeschreibung), ADR-0005 (Konten und Anmeldung), #421 (Links abgeschafft).

## Risks & Considerations
- `wer_spricht` ohne Person/Rolle muss sicher scheitern (None → kein Zugriff), nicht still als Gast laufen.
- Schemas ohne `name`/`vorname`: Clients, die das Feld noch senden, dürfen keinen Fehler bekommen (Konto-Weg poppt `name`; `vorname` wird bisher nur durch `rest`-Filter ignoriert).
- `frage_beantworten.4` („Name fehlt“) wird an mehreren Stellen nach dem Rückfall genutzt – prüfen, ob er ganz unerreichbar wird.
- Gast in der Beispielreise ändert die Demoseite und Zählungen in anderen Tests (Personenzahl, Seiteninhalt).
- Mehrsprachigkeitsauftrag `docs/auftraege/mehrsprachigkeit/M8.md` nennt einen der Texte.

## Analysis

### Type
Feature (Aufräumen, rein intern; keine sichtbare Änderung für Personen)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/konnektor.py | MODIFY | `wer_spricht`: nur noch Zugang mit `person`; ohne Person → None (kein Zugriff, nie still Gast). Rückfälle `wer["name"] or args.get("name"/"vorname")` entfallen (Zeilen ~1560, 1952, 3102, 3114, 3149, 3175, 3202); damit auch die Zweige mit `frage_beantworten.4`, `ontologie_werkzeug.7`, `entscheiden.2`, `einladen.6`, `werkzeug.14`. Anleitung: `du_ohne_name`, `mit.vorname` weg. Schemas: `NAME_FELD` und `name` in `rueckmeldung_geben` weg. `einladen` behält `vorname` (Name der eingeladenen Person). Filter `rest` ignoriert `name`/`vorname` weiter, damit alte Clients keinen Fehler bekommen; `args.pop("name")` im Konto-Weg bleibt. |
| engine/texte_de.py, engine/texte_en.py (+ weitere texte_*.py) | MODIFY | Schlüssel entfernen: `konnektor.einladen.6`, `.entscheiden.2`, `.ontologie_werkzeug.7`, `.werkzeug.14`, `frage_beantworten.4` (falls danach unbenutzt), `anleitung.du_ohne_name`, `anleitung.mit.vorname`, `feld.name_feld`, `werkzeug.rueckmeldung_geben.name`; Platzhalter `{vorname}` aus `anleitung.mit`. |
| engine/tests/conftest.py | MODIFY | `mcp_intern` reicht nur noch `reise`, `person`, `sprache` durch. |
| engine/tests/test_konnektor.py | MODIFY | `MITREISEND` (56 Stellen) → `KARL`; Aufrufe mit `name="Anna"` usw. ohne Namensargument, Erwartungen auf „Karl“; Tests, die nur den Rückfall prüfen (Name fehlt), entfallen. `GAST` (19 Stellen) wird ein Zugang mit Person `kim` (Rolle gast). Neuer Test: Zugang ohne Person (nur Rolle) → kein Zugriff. |
| engine/tests/test_packliste.py | MODIFY | `GAST` bleibt importiert, zeigt jetzt auf Person `kim`. |
| docs/konnektor.md, docs/auftraege/mehrsprachigkeit/M8.md | MODIFY | Hinweise auf Zugang ohne Namen streichen. |

### Scope Assessment
- Files: ~7–9
- Estimated LoC: +60 / −200 (überwiegend Tests umstellen und Texte löschen)
- Risk Level: LOW–MEDIUM (zentrale Funktion `wer_spricht`, aber von außen nur der Konto-Weg, der immer eine Person setzt)

### Technical Approach
1. `wer_spricht` ohne Rollen-Zweig; Aufrufer mit Rückfall `or {"rolle": "gast", ...}` (Anleitung, `tools/list`) prüfen: ohne Person kein Gast-Rückfall mehr für Schreibwerkzeuge; Anleitung/`tools/list` dürfen weiter den Gast-Text zeigen (nur Lesen), Werkzeugaufrufe ohne Person enden mit dem bestehenden Fehler „gehört zu keiner Person“.
2. Name kommt immer aus der Person (`wer["name"]`); hat ein Eintrag keinen Namen, nimmt `wer_spricht` den Schlüssel (Datenrobustheit statt Fehlertext).
3. Schemas und Texte entfernen; Katalogtest (ungenutzte Schlüssel) und `test_texte.py` sichern die Vollständigkeit.
4. **Gast nicht in die Beispielreise, sondern in der Testvorbereitung** (Abweichung vom Issue-Text, Tech-Lead-Entscheidung): Die Fixture `seiten` baut aus einer Kopie der Beispielreise mit zusätzlicher Person `kim` (gast), wie es `test_regeln` schon macht. Grund: Ein Gast in der Beispielreise wäre eine sichtbare Änderung der Demoseite (Issue verlangt „keine sichtbare Änderung“, Regel „erst zeigen, dann bauen“) und zöge Folgeänderungen in Namenslisten anderer Tests nach (`test_englisch*`, Personenzählungen). Die Fixture-Lösung bleibt auf die Konnektortests begrenzt.

### Dependencies
- Upstream: `personen_der_reise` (veröffentlichte Daten + Einladungen), `regeln.rolle_neu/darf`.
- Downstream: alle Werkzeuge über `werkzeug()`, Anleitung (`initialize`), `tools/list`, `werkzeuge_fuer`, Kopieren aus anderer Reise (Zeile ~1593, nutzt schon None = keine Person).
- Keine Änderung an Reisedaten-Format → kein `neu.py nachziehen` nötig. Meldungstexte ändern sich nur für unerreichbare Fälle; Instanz-Tests vor dem Ausliefern trotzdem laufen lassen (Texte/Schnittstelle des Konnektors).

### Open Questions
- keine (Gast-Platz als Tech-Lead-Entscheidung oben begründet)

## Hinweise aus TDD RED (für /50-implement)
- Neue Testdatei `engine/tests/test_rolle_ohne_person_426.py` (nutzt `umgebung` aus `test_regeln`, Gast `kim` als Person).
- RED: 6 Tests rot (AC-1, AC-2, Name aus Schlüssel, AC-5, AC-8, AC-7); 4 laufen schon grün als Wächter gegen Rückschritte (AC-3, AC-4, Anleitung, Einladen mit `vorname`).
- AC-7 findet Zugänge nur mit Rolle auch außerhalb von `test_konnektor.py`: `test_brett.py:235` (`zugang_dazu(..., rolle="organisator")`), `test_stand.py:287/294` (`antwort_auf({"reise", "rolle": "organisator"})`), `test_gespraech.py:108/168/265`, `test_konnektor.py:223/224/273/333/720/1036–1038`. Diese auf Personen umstellen (Ida als Organisatorin, Karl als Mitwirkender, Kim als Gast).
