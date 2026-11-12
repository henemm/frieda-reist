---
entity_id: rolle-ohne-person-426
type: refactor
created: 2026-11-12
updated: 2026-11-12
status: draft
workflow: m7-426-konnektor-rolle-ohne-person
version: "1.0"
tags: [konnektor, aufraeumen, konten, m7]
---

# Konnektor ohne internen Zugang „Rolle ohne Person“ (#426)

## Approval

- [ ] Approved

## Purpose

Seit #421 erreicht man den Konnektor nur noch über das Konto, und die sprechende Person steht damit immer fest. Der interne Zugang `{reise, rolle}` ohne Person stammt aus der Zeit der Links, ist von außen nicht mehr erreichbar und wird nur noch von Tests benutzt. Er samt Namensfeld der Werkzeuge, den Texten für „Link ohne Person“ und den Rückfällen auf ein Namensargument wird entfernt. Für Personen ändert sich nichts Sichtbares.

## Ziel und Abgrenzung

- **Im Scope:**
  - `wer_spricht` kennt nur noch Zugänge mit `person`. Ein Zugang ohne Person liefert `None` (kein Zugriff, nie still Gast). Der Name kommt immer aus der Person; fehlt er im Eintrag, gilt der Schlüssel der Person.
  - Die Rückfälle `wer["name"] or args.get("name"/"vorname")` und ihre Fehlerzweige entfallen.
  - Das Feld `name` (`NAME_FELD`) fällt aus den Schemas aller Werkzeuge, ebenso `name` in `rueckmeldung_geben`. `vorname` bleibt nur bei `einladen` (dort der Name der eingeladenen Person, kein `NAME_FELD`).
  - Texte entfallen in allen `engine/texte_*.py`: `konnektor.einladen.6`, `konnektor.entscheiden.2`, `konnektor.ontologie_werkzeug.7`, `konnektor.werkzeug.14`, `konnektor.anleitung.du_ohne_name`, `konnektor.anleitung.mit.vorname`, `konnektor.feld.name_feld`, `konnektor.werkzeug.rueckmeldung_geben.name`, dazu `konnektor.frage_beantworten.4` (Name fehlt), weil alle seine Verwendungen im Code nur den Rückfall betreffen und damit unerreichbar werden; der Platzhalter `{vorname}` verschwindet aus `konnektor.anleitung.mit`. `konnektor.ausgabe.frage_beantworten.4` („Nicht gespeichert“) ist ein anderer Schlüssel und bleibt.
  - Tests: Zugänge ohne Person (`MITREISEND`, `GAST` in `test_konnektor.py`, Kurznamen über `conftest.mcp_intern`) werden auf Personen umgestellt.
  - Doku: Hinweise auf den Zugang ohne Namen streichen in `docs/konnektor.md` und `docs/auftraege/mehrsprachigkeit/M8.md`.
- **Nicht im Scope:** Konto-Weg und Anmeldung (unverändert), Einladungen, Rollenregeln, Format der Reisedaten.
- **Kern (ADR-0001):** Berührt weder Arten, Merkmale noch Grundformen; reine Entfernung toten Codes.
- **Abweichung vom Issue-Text (bewusst, Tech-Lead-Entscheidung):** Das Issue sieht einen Gast in der Beispielreise vor („ein Gast in der Beispielreise als Beispielwert“). Stattdessen entsteht die Gast-Person `kim` nur in der Testvorbereitung, in einer Kopie der Beispielreise, wie es `engine/tests/test_regeln.py` schon macht (dort `y["personen"]["kim"] = {"name": "Kim", "rolle": "gast", "reist": True}`). Gründe: Ein Gast in der Beispielreise änderte die Demoseite sichtbar, das Issue verlangt aber „ohne sichtbare Änderung“, und sichtbare Änderungen an Beispielen werden vorab als Entwurf gezeigt. Außerdem müssten Namenslisten und Personenzählungen anderer Tests nachgezogen werden (etwa englische Seiten, Personenzahlen). Die Lösung in der Testvorbereitung bleibt auf die Konnektortests begrenzt.
- **Verträglichkeit mit Clients:** Schickt ein Client noch `name` oder `vorname` mit, bekommt er keinen Fehler; das Argument wird ignoriert (der Konto-Weg entfernt `name` bereits per `args.pop("name")`, `vorname` filtert der vorhandene `rest`-Filter), der Name stammt aus der Person. Bei `einladen` gilt `vorname` weiter als Name der eingeladenen Person.
- **Instanzen und Datenformat:** Keine Formatänderung der Reisedaten, daher kein Eintrag in `neu.py nachziehen`. Weil sich die Schnittstelle des Konnektors ändert (Schemas, Texte), laufen vor dem Vorspulen die Tests der einbindenden Instanzen mit dem Branch.

## Source

- **File:** `engine/konnektor.py`
- **Identifier:** `def wer_spricht` (Zeile 240) sowie die Aufrufer in Anleitung, `werkzeug`, `werkzeuge_fuer`, das Kopieren aus einer anderen Reise, die Schema-Liste mit `NAME_FELD`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/konnektor.py` (`wer_spricht`, `werkzeug`, `werkzeuge_fuer`, Anleitung, `antwort_fuer`) | Code | Ort der Änderung; Konto-Weg setzt immer `person` |
| `engine/rueckmeldungen.py` (`personen_mit_einladungen`) | Code | Personen der Reise inklusive Eingeladener |
| `engine/reise.py` / `regeln` (`rolle_neu`, `darf`) | Code | Rolle der Person, Rechteprüfung |
| `engine/texte_de.py`, `engine/texte_en.py`, weitere `engine/texte_*.py` | Code | Schlüssel entfernen |
| `engine/tests/test_texte.py` | Test | Katalog vollständig, Ausnahmelisten nur kürzer, ungenutzte Schlüssel |
| `engine/tests/conftest.py` (`mcp_intern`) | Test | reicht nur noch `reise`, `person`, `sprache` durch |
| `engine/tests/test_regeln.py` | Test | Muster für Gast `kim` in einer Kopie der Beispielreise |
| `engine/tests/test_packliste.py` | Test | importiert `GAST` aus `test_konnektor` |
| ADR-0005, #421 | Entscheidung | Konto, Rolle gehört zur Reise; Links abgeschafft |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konnektor.py` | MODIFY | `wer_spricht` nur mit Person, sonst `None`; Rückfälle auf Namensargument, die Zweige mit `frage_beantworten.4`, `ontologie_werkzeug.7`, `entscheiden.2`, `einladen.6`, `werkzeug.14` und in der Anleitung `du_ohne_name`, `mit.vorname` entfernen; `NAME_FELD` und `name` in `rueckmeldung_geben` aus den Schemas; `einladen` behält `vorname` |
| `engine/texte_de.py`, `engine/texte_en.py`, weitere `engine/texte_*.py` | MODIFY | die oben genannten Schlüssel entfernen; Platzhalter `{vorname}` aus `anleitung.mit` |
| `engine/tests/conftest.py` | MODIFY | `mcp_intern`: Zugang nur mit `reise`, `person`, `sprache`; Docstring ohne `rolle` |
| `engine/tests/test_konnektor.py` | MODIFY | `MITREISEND` (rund 56 Stellen) wird `KARL`, Erwartungen auf „Karl“; `GAST` (rund 19 Stellen) wird Person `kim` (Rolle gast) in einer Kopie der Beispielreise der Fixture `seiten`; Tests, die nur den Namens-Rückfall prüfen, entfallen; neue Tests siehe unten |
| `engine/tests/test_packliste.py` | MODIFY | nutzt `GAST` weiter, nun Person `kim`; falls eine eigene Reisekopie gebaut wird, ebenfalls mit `kim` |
| `engine/tests/test_texte.py` | MODIFY (nur falls nötig) | Ausnahmelisten dürfen nur kürzer werden |
| `docs/konnektor.md` | MODIFY | Hinweis auf Zugang ohne Namen streichen |
| `docs/auftraege/mehrsprachigkeit/M8.md` | MODIFY | Nennung des entfernten Textes streichen |

### Estimated Changes

- Files: 8 bis 9
- LoC: +60 / -200 (überwiegend Tests umstellen, Texte löschen)
- Risiko: niedrig bis mittel (zentrale Funktion, aber von außen nur der Konto-Weg, der immer eine Person setzt)

## Implementation Details

1. **`wer_spricht`:** Ohne `zugang["person"]` sofort `None`. Mit Person: Eintrag in `personen_der_reise` suchen; gefunden → `{"rolle": rolle_neu(...), "name": <Name oder Schlüssel>}`, sonst `None`. Der Rollen-Zweig entfällt vollständig.
2. **Aufrufer:** Wo heute `wer_spricht(...) or {"rolle": "gast", ...}` steht (Anleitung, `werkzeug`, `werkzeuge_fuer`), darf Anleitung und `tools/list` weiter die Gast-Sicht zeigen (nur Lesen); Werkzeugaufrufe ohne Person enden mit dem vorhandenen Fehler „gehört zu keiner Person“. Das Kopieren aus einer anderen Reise nutzt `None` schon als „keine Person dort“ und bleibt gleich. Vor dem Entfernen jeder Stelle wird geprüft, dass kein Pfad bleibt, der ohne Person als Gast schreibt.
3. **Namen:** Überall `wer["name"]` statt `wer["name"] or args.get(...)`. Die Zweige, die bei fehlendem Namen `konnektor.frage_beantworten.4` zurückgaben, entfallen; danach darf kein Aufruf des Schlüssels mehr im Code stehen (der Katalogtest für ungenutzte Schlüssel sichert das ab).
4. **Schemas:** `NAME_FELD` und `name` bei `rueckmeldung_geben` entfernen; `vorname` nur bei `einladen`. Überzählige Argumente `name`/`vorname` werden wie bisher aus den Argumenten gefiltert, nie als Fehler gemeldet.
5. **Texte:** Schlüssel in allen `engine/texte_*.py` gleichzeitig entfernen; der Code kennt keine Sprache beim Namen.
6. **Tests (Testvorbereitung):** Die Fixture `seiten` in `test_konnektor.py` baut die Seiten aus einer Kopie der Beispielreise mit zusätzlicher Person `kim` (Rolle gast); die Kurznamen-Datei bildet `GAST` auf `{"reise": "beispielreise", "person": "kim"}` und `KARL` auf `karl` ab. `MITREISEND` entfällt. `engine/tests/test_packliste.py` bleibt am importierten `GAST`; Beispielreise im Repo bleibt unverändert.

## Test Plan

### Automated Tests (TDD RED)

- [ ] `test_zugang_ohne_person_hat_keinen_zugriff`: GIVEN Zugang `{"reise": "beispielreise", "rolle": "mitreisend"}` ohne Person WHEN `wer_spricht` und ein schreibendes Werkzeug (`rueckmeldung_geben`) darüber aufgerufen werden THEN liefert `wer_spricht` `None`, das Werkzeug lehnt ab, nichts wird gespeichert, und es läuft nichts still als Gast.
- [ ] `test_tools_list_ohne_name_und_vorname_ausser_einladen`: GIVEN Karl als Person WHEN `tools/list` abgefragt wird THEN steht in keinem Schema ein Feld `name`, und `vorname` nur im Schema von `einladen` (`person_einladen`).
- [ ] `test_ueberzaehliges_namensargument_ohne_fehler`: GIVEN Karl WHEN `rueckmeldung_geben` mit zusätzlichem `name="Anna"` (und ein anderes Werkzeug mit `vorname="Anna"`) aufgerufen wird THEN kommt kein Fehler wegen des Arguments, und der gespeicherte Name ist „Karl“.
- [ ] `test_gast_als_person_kim_liest_schreibt_nicht`: GIVEN `GAST` als Person `kim` (Rolle gast) WHEN sie `overview` und `show` aufruft THEN klappt das; WHEN sie `rueckmeldung_geben` oder `aufgabe_anlegen` aufruft THEN lehnt der Konnektor ab und nichts wird geschrieben.
- [ ] `test_name_kommt_aus_der_person`: GIVEN Person ohne `name` im Eintrag (Datenrobustheit) WHEN `wer_spricht` aufgerufen wird THEN ist der Name der Schlüssel der Person, nicht `None`.
- [ ] `test_anleitung_ohne_namensfrage`: GIVEN Karl WHEN `initialize` die Anleitung liefert THEN enthält sie seinen Namen und keine Aufforderung, nach dem Vornamen zu fragen (in de und en).
- [ ] `test_einladen_vorname_bleibt`: GIVEN Ida (organisator) WHEN sie `person_einladen` mit `vorname` und `email` der eingeladenen Person aufruft THEN wird die Person mit diesem Namen eingeladen.
- [ ] `test_doku_nennt_keinen_zugang_ohne_namen`: GIVEN `docs/konnektor.md` und `docs/auftraege/mehrsprachigkeit/M8.md` WHEN sie durchsucht werden THEN beschreibt keine von beiden einen Zugang ohne Person oder eine Abfrage des eigenen Vornamens.
- [ ] Umgestellt statt neu: bestehende Konnektortests (Rückmeldung, Aufgabe, Entscheiden, Einplanen, Ontologie, Packliste) laufen mit `KARL`/`GAST`=`kim` grün; `test_texte.py` und der Test auf ungenutzte Katalogschlüssel bleiben grün, Ausnahmelisten nicht länger.

## Acceptance Criteria

- **AC-1:** Given ein Zugang `{reise, rolle}` ohne `person` / When `wer_spricht` ihn auflöst / Then ist das Ergebnis `None`, und ein Werkzeugaufruf damit endet mit „gehört zu keiner Person“, ohne Schreiben und ohne Gast-Rückfall. Test: `test_zugang_ohne_person_hat_keinen_zugriff`.
- **AC-2:** Given beliebige Person der Reise / When `tools/list` geliefert wird / Then hat kein Werkzeugschema ein Feld `name`, und `vorname` kommt nur bei `einladen` vor. Test: `test_tools_list_ohne_name_und_vorname_ausser_einladen`.
- **AC-3:** Given ein Client sendet weiter `name` oder `vorname` / When er ein Werkzeug aufruft / Then gibt es keinen Fehler, das Argument wirkt nicht, und der Name im Verlauf ist der der Person. Test: `test_ueberzaehliges_namensargument_ohne_fehler`.
- **AC-4:** Given Gast `kim` als Person (Kopie der Beispielreise in der Testvorbereitung) / When sie liest / Then klappt es, / When sie schreibt / Then wird abgelehnt. Test: `test_gast_als_person_kim_liest_schreibt_nicht`. Die Beispielreise im Repo und ihre Demoseite bleiben unverändert (kein Gast dort).
- **AC-5:** Given die Texte entfernt sind / When der Katalog geprüft wird / Then fehlen `konnektor.einladen.6`, `.entscheiden.2`, `.ontologie_werkzeug.7`, `.werkzeug.14`, `.frage_beantworten.4`, `anleitung.du_ohne_name`, `anleitung.mit.vorname`, `feld.name_feld`, `werkzeug.rueckmeldung_geben.name` in allen `engine/texte_*.py` zugleich, kein Code verweist mehr darauf, und `engine/tests/test_texte.py` ist grün mit nicht längeren Ausnahmelisten. Test: `engine/tests/test_texte.py` (bestehend) plus Suche im Code.
- **AC-6:** Given Karl / When die Anleitung erzeugt wird / Then fragt sie nie nach dem Vornamen, und `einladen` nimmt weiter `vorname` der eingeladenen Person. Tests: `test_anleitung_ohne_namensfrage`, `test_einladen_vorname_bleibt`.
- **AC-7:** Given die Tests nutzen nur Personen der Beispielreisen (plus `kim` in der Testvorbereitung) / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün; weder `MITREISEND` noch ein Zugang mit `rolle` ohne `person` kommt in `engine/tests/` vor.
- **AC-8:** Given die Änderung berührt die Konnektor-Schnittstelle / When sie ausgeliefert werden soll / Then laufen vorher die Tests der einbindenden Instanzen mit dem Branch grün; Doku in `docs/konnektor.md` und `docs/auftraege/mehrsprachigkeit/M8.md` nennt den Zugang ohne Namen nicht mehr. Test: `test_doku_nennt_keinen_zugang_ohne_namen` (sucht in beiden Dateien nach Hinweisen auf Vornamen-Abfrage bzw. Zugang ohne Person).

## Definition of Done

- [ ] Tests zu AC-1 bis AC-8 geschrieben, zuerst rot, danach grün
- [ ] Gesamtlauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün, ohne echte Reisen
- [ ] Die neun Textschlüssel in allen `engine/texte_*.py` entfernt, `engine/tests/test_texte.py` grün, Ausnahmelisten nicht länger
- [ ] `docs/konnektor.md` und `docs/auftraege/mehrsprachigkeit/M8.md` bereinigt
- [ ] Tests der einbindenden Instanzen mit dem Branch grün
- [ ] Pflichtprüfungen der CI grün, ausgeliefert, Konnektor auf dem Server neu gestartet und per Konto geprüft
- [ ] Issue #426 mit Abschlusskommentar geschlossen

## Known Limitations

- Alte Clients mit zwischengespeicherten Schemas dürfen `name`/`vorname` weiter senden; es bleibt wirkungslos.
- `kim` als Gast liegt nur in der Testvorbereitung; wird später ein Gast in der Beispielreise gewünscht, ist das eine eigene Entscheidung mit Entwurf vorab.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Entfernung toten Codes nach der bestehenden Entscheidung ADR-0005 (Identität gehört zum Konto, Rolle zur Reise) und #421; keine neue Grundform, kein neues Datenformat.

## Changelog

- 2026-11-12: Initial spec created (Entwurf) für #426; Gast `kim` bewusst in der Testvorbereitung statt in der Beispielreise.
