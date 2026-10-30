# Context: loeschwunsch-145

## Request Summary
Sagt jemand „lösch das“, soll der Assistent selbst den passenden Weg wählen (Buchung stornieren, Option verwerfen, Aufgabe entfällt …), nach Bestätigung handeln und in einem Satz sagen, was geschah und wie man es zurückholt (Issue #145). Nur Texte des Konnektors, keine neue Funktion.

## Related Files
| File | Relevance |
|------|-----------|
| engine/konnektor.py `BUCHUNG_AENDERN` (Z. ~2469) | Werkzeugbeschreibung; nennt Stornieren, aber nicht „Löschwunsch“ und nicht „zurückholbar“. |
| engine/konnektor.py `ENTSCHEIDEN` (Z. ~2605) | Beschreibung für verworfen/ersetzt; kein Hinweis auf Löschwunsch/Zurückholen. |
| engine/konnektor.py `aufgabe_aendern` (Z. ~2189) | Sagt schon „Gelöscht wird nie; … entfaellt“ – Vorbild für den Ton. |
| engine/konnektor.py `frage_schliessen` (Z. ~2410), Instruktionen (Z. ~2706ff.) | Frage: geklaert/entfaellt; Instruktionstext des Konnektors eignet sich für eine allgemeine Löschwunsch-Regel. |
| engine/schreiben.py `buchung_aendern` (Z. 1917) | Antworttext: „Buchung B-… (…): Status „gebucht“ → „storniert“. Grund: …“ – ohne „nicht gelöscht / zurückholbar“. |
| engine/schreiben.py `entscheiden` (Z. 1408, Text Z. ~1486) | Antworttext: „Entschieden: … ist verworfen …“ – ohne Hinweis auf Zurückholen. |
| engine/schreiben.py `frage_schliessen` (Z. 1599), `ding_aendern` (Z. 1075), `wissen_aendern` (Z. 2314) | Weitere Grundformen; prüfen, ob es ein Löschen/Entfallen gibt und welcher Weg passt. |
| engine/tests/test_konnektor.py (Z. ~855–880) | Vorhandene Tests zu buchung_aendern/zeige; Ort für den Test der Texte. |

## Existing Patterns
- Frieda löscht nie: Verlaufseinträge (Datum, Person, Grund); Aufgaben „entfällt“, Fragen „entfällt“, Buchungen „storniert“, Optionen „verworfen“.
- Zurückholen geht mit demselben Werkzeug: buchung_aendern status gebucht; entscheiden status gewaehlt (gleicher Status wird abgelehnt, anderer erlaubt).
- Antworttexte des Schreibwegs sind Klartext mit Grund; Tests prüfen Teilstrings.

## Dependencies
- Upstream: `schreiben.py`-Funktionen liefern (Titel, Text); `konnektor.py` reicht sie durch.
- Downstream: Tests, die Antworttexte wörtlich vergleichen (Z. 863 mockt den Text, prüft nur Argumente); Instanz-Doku `docs/konnektor.md` beschreibt die Werkzeuge.

## Existing Specs
- `docs/adr/0001-kern.md` (Prüfstelle: nichts Neues, nur Texte → vereinbar), `docs/konnektor.md`.

## Risks & Considerations
- Antworttext nur ergänzen, nicht ändern, damit bestehende Tests und der Wächter grün bleiben.
- Wahrheit wahren: Zurückholen nur nennen, wo es wirklich geht (Option nach „ersetzt“ ebenso; Buchung auch; Verlauf bleibt).
- Nichts Reisespezifisches in den Texten; Sprache Deutsch mit Umlauten.
- Für andere Grundformen (Ding, Wissen, Tag) zuerst prüfen, ob es überhaupt einen Weg gibt, sonst ehrlich „geht nur über Rückmeldung an Organisator:in“ sagen – in der Analyse klären.

## Analysis

### Type
Feature (nur Texte des Konnektors; keine neue Funktion, Art oder Baustein – mit ADR-0001 vereinbar, da nichts Neues in der Ontologie entsteht).

### Befund: Welcher Weg passt je Grundform (Stand des Codes)
| Löschwunsch bei … | Weg | Zurückholen | Werkzeug |
|---|---|---|---|
| Buchung | status `storniert` (Grund Pflicht, `schreiben.py` Z. ~1959) | status `gebucht` bzw. `angefragt` | `buchung_aendern` |
| Option einer Wahlstelle | `verworfen` oder `ersetzt` (nur Organisator:innen) | erneut `entscheiden` mit status `gewaehlt` (anderer Status als der jetzige) | `entscheiden` |
| Aufgabe | status `entfaellt` | status zurück auf offen (prüfen, was `aufgabe_aendern` erlaubt) | `aufgabe_aendern` (Text nennt „Gelöscht wird nie“ schon) |
| Offene Frage | status `entfaellt` | `frage_schliessen` kennt nur `geklaert`/`entfaellt`; Zurückholen = neue Frage oder Rückmeldung – **ehrlich benennen, nicht behaupten** | `frage_schliessen` |
| Ding (Unterkunft, Strecke, Ort), Wissen, Tag, Wahlstelle | **kein Löschweg**; `ding_aendern`/`wissen_aendern` ändern nur, alter Wert bleibt im Verlauf | – | Antwort: geht nicht über den Konnektor → Rückmeldung an Organisator:in (`rueckmeldung_geben`) |

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/konnektor.py `BUCHUNG_AENDERN`, `ENTSCHEIDEN`, `AUFGABE_AENDERN`, `frage_schliessen` | MODIFY | Beschreibung: Löschwunsch + passender Weg + Zurückholen |
| engine/konnektor.py `anleitung()` (Z. ~2700ff.) | MODIFY | Ein Absatz „Löschwunsch“: Frieda löscht nie; Tabelle oben in Worten; erst bestätigen lassen; danach ein Satz „was geschah, nicht gelöscht, so holt man es zurück“ |
| engine/schreiben.py `buchung_aendern` (Antworttext Z. ~2009) | MODIFY | bei Wechsel auf `storniert`: Satz „Nicht gelöscht; zurückholen mit Status gebucht.“ anhängen |
| engine/schreiben.py `entscheiden` (Text Z. ~1487) | MODIFY | bei `verworfen`/`ersetzt`: Satz „Nicht gelöscht; zurückholen mit entscheiden, Status gewählt.“ anhängen |
| engine/schreiben.py Aufgabe/Frage (Antworttexte) | MODIFY (prüfen) | gleicher Hinweis bei `entfaellt`, nur wo Zurückholen wirklich geht |
| engine/tests/test_konnektor.py | MODIFY | Test: Werkzeugbeschreibungen + Anleitung nennen Löschwunsch/Weg; Antworttexte von Stornieren/Verwerfen nennen „nicht gelöscht“ und Rückholweg |
| docs/konnektor.md | MODIFY | Abschnitt Löschwunsch (Doku des Konnektors) |

### Scope Assessment
- Files: 4–5 (konnektor.py, schreiben.py, test_konnektor.py, docs/konnektor.md; ggf. Test für schreiben)
- Estimated LoC: +60/-5
- Risk Level: LOW – nur Texte; Antworttexte werden nur ergänzt (Teilstring-Tests bleiben grün).

### Technical Approach
1. Zentrale Regel in `anleitung()` (gilt für jede Reise, nichts Reisespezifisches), je Werkzeug ein kurzer Querverweis in der Beschreibung.
2. Antworttexte ergänzen, nur an den Stellen, wo der Zustandswechsel „weg“ (storniert/verworfen/ersetzt/entfällt) tatsächlich eintritt – Wahrheit wahren, Zurückholen nur nennen, wo es geht.
3. Für Grundformen ohne Löschweg ehrlich sagen: nicht über den Konnektor, Rückmeldung an Organisator:in.
4. Reihenfolge: Spec → Tests (RED) → Texte (GREEN).

### Dependencies
- `konnektor.py` reicht die Texte aus `schreiben.py` durch; der Wächter nutzt Antworttexte nicht.
- Tests, die Antworttexte wörtlich vergleichen, gibt es laut Kontext nicht (Z. 863 mockt nur); beim Implementieren per Testlauf bestätigen.
- Mitwirkende dürfen nicht entscheiden → Löschwunsch bei Option: Mitwirkende bekommen den Weg „Rückmeldung“ statt `entscheiden`.

### Open Questions
- [ ] Aufgabe zurückholen: erlaubt `aufgabe_aendern` den Wechsel von `entfaellt` zurück auf offen? (in der Spec-Phase im Code prüfen; sonst Hinweis weglassen)
- [ ] Frage: Zurückholen geht nur über eine neue Frage – so im Text sagen, oder Hinweis weglassen? Empfehlung: ehrlich so sagen.
