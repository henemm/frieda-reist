---
entity_id: loeschwunsch
type: module
created: 2026-10-30
updated: 2026-10-30
status: active
version: "1.0"
tags: [konnektor, texte, loeschen, stornieren, verwerfen]
---

# Konnektor: Löschwunsch („lösch das“) führt zum passenden Weg (#145)

## Approval

- [x] Approved (Product Owner, 2026-10-30)

## Purpose

Nutzer sagen „löschen“, wo Frieda nichts löscht. Der Assistent soll bei einem Löschwunsch selbst den passenden Weg wählen (Buchung stornieren, Option verwerfen, Aufgabe entfällt, Frage entfällt), nach Bestätigung handeln und in einem Satz sagen, was geschah, dass nichts gelöscht ist und wie man es zurückholt. Wo es keinen Weg gibt, sagt er das ehrlich und verweist auf eine Rückmeldung an die Organisator:in.

Das Ticket nennt Buchungen und Optionen; die Spec nimmt bewusst Aufgaben und Fragen dazu, weil Nutzer auch dort „löschen“ sagen und Frieda dort ebenfalls nie löscht (Antworttexte in `schreiben.py` werden dafür nur ergänzt).

Nur Texte des Konnektors (Anleitung, Werkzeugbeschreibungen, Antworttexte). Keine neue Funktion, keine neue Art, kein neuer Baustein, keine neue Grundform. Prüfstelle ADR-0001: vereinbar, denn die Ontologie bleibt unberührt.

## Source

- **File:** `engine/konnektor.py`, `engine/schreiben.py`
- **Identifier:** `anleitung()`, `BUCHUNG_AENDERN`, `ENTSCHEIDEN`, `aufgabe_aendern` (Eintrag in `WERKZEUGE`), `frage_schliessen` (Werkzeug), `schreiben.buchung_aendern`, `schreiben.entscheiden`, `schreiben.frage_schliessen`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `schreiben.buchung_aendern` / `entscheiden` / `frage_schliessen` | Funktionen | liefern (Titel, Text); der Konnektor reicht sie durch |
| `rueckmeldungen.aufgabe_aendern` | Funktion | schreibt Aufgaben (`entfaellt`, wieder `offen`); Antworttext kommt aus dem Konnektor |
| `engine/tests/test_konnektor.py` | Test | prüft Teilstrings; Ort der neuen Tests |
| `docs/konnektor.md` | Doku | Werkzeugbeschreibung, bekommt den Abschnitt Löschwunsch |

## Scope

- **Affected Files:** `engine/konnektor.py`, `engine/schreiben.py`, `engine/tests/test_konnektor.py`, `docs/konnektor.md`
- **Estimated Changes:** ca. +60/-5 LoC
- **Nicht im Scope:** neuer Löschweg, neues Werkzeug, Status „gelöscht“, Wiedereröffnen von Fragen (gibt es nicht), Vorlage/Seite, Wächter, `engine/vendor/`. Antworttexte werden nur ergänzt, nie umformuliert.

## Implementation Details

### Welcher Weg passt (Stand des Codes)

| Löschwunsch bei | Weg | Zurückholen | Werkzeug |
|---|---|---|---|
| Buchung | Status `storniert`, Grund Pflicht | Status `gebucht` (bzw. `angefragt`) | `buchung_aendern` |
| Option einer Wahlstelle (nur Organisator:innen) | `verworfen` oder `ersetzt` | `entscheiden` mit Status `gewaehlt` | `entscheiden` |
| Aufgabe | Status `entfaellt` | Status `offen` („wieder offen“) | `aufgabe_aendern` |
| Offene Frage | Status `entfaellt` | **kein Wiedereröffnen**; bei Bedarf neue Frage (`frage_anlegen`) | `frage_schliessen` |
| Ding (Unterkunft, Strecke, Ort), Wissen, Tag, Wahlstelle, Plan | **kein Löschweg**; Ändern lässt den alten Wert im Verlauf | – | Antwort: geht nicht über den Konnektor → Rückmeldung (`rueckmeldung_geben`) an die Organisator:in |

Mitwirkende dürfen Optionen nicht entscheiden: Für sie lautet der Weg bei einer Option ebenfalls Rückmeldung.

### Änderungen

1. **`anleitung()`:** ein Absatz „Löschwunsch“ (reiseunabhängig, für alle Rollen): Frieda löscht nie; bei „lösch das“ den Weg aus der Tabelle wählen; die Person kurz bestätigen lassen (was genau, mit Grund); danach in einem Satz sagen, was geschah, dass es nicht gelöscht ist und wie man es zurückholt; wo es keinen Weg gibt, das sagen und auf die Rückmeldung verweisen.
2. **Werkzeugbeschreibungen** `BUCHUNG_AENDERN`, `ENTSCHEIDEN`, `aufgabe_aendern`, `frage_schliessen`: je ein kurzer Satz „Bei einem Löschwunsch …“ mit dem eigenen Weg und dem Rückholweg. Bei `frage_schliessen` ehrlich: Eine entfallene Frage wird nicht wieder geöffnet; bei Bedarf neue Frage.
3. **Antworttext `schreiben.buchung_aendern`:** beim Wechsel auf `storniert` angehängt: „Nicht gelöscht, die Buchung steht weiter mit Verlauf da; zurückholen mit Status gebucht.“
4. **Antworttext `schreiben.entscheiden`:** bei `verworfen`/`ersetzt` angehängt: „Nicht gelöscht, die Option bleibt mit Verlauf stehen; zurückholen mit entscheiden, Status gewählt.“
5. **Antworttext `schreiben.frage_schliessen`:** bei `entfaellt` angehängt: „Nicht gelöscht, die Frage steht weiter mit Verlauf da; ein Wiedereröffnen gibt es nicht, bei Bedarf eine neue Frage anlegen.“
6. **Antworttext Aufgabe (`entfaellt`):** Hinweis „Nicht gelöscht; zurückholen mit Status offen.“ im Antworttext des Konnektors (Stelle beim Implementieren im Aufruf von `rueckmeldungen.aufgabe_aendern` festlegen).
7. **`docs/konnektor.md`:** Abschnitt „Löschwunsch“ mit der Tabelle in Worten.

Sprache: Deutsch mit Umlauten; nichts Reisespezifisches.

## Expected Behavior

- **Input:** Eine Person sagt dem Assistenten „lösch das“ zu einer Buchung, Option, Aufgabe oder Frage.
- **Output:** Der Assistent nennt (nach der Anleitung) den passenden Weg, lässt bestätigen, ruft das Werkzeug auf; die Antwort des Werkzeugs sagt, dass nichts gelöscht ist, und wie man es zurückholt (bzw. dass es bei Fragen kein Zurückholen gibt).
- **Side effects:** Keine. Bestehende Zustandswechsel, Verläufe und Regeln der Werkzeuge bleiben unverändert.

## Acceptance Criteria

- **AC-1:** Die Anleitung enthält den Absatz zum Löschwunsch (Frieda löscht nie; Weg je Grundform; erst bestätigen lassen; ein Satz danach; ehrlicher Verweis auf die Rückmeldung, wo es keinen Weg gibt). Er steht für jede Rolle (Gast, Mitwirkende, Organisator:in) in der Anleitung.
- **AC-2:** Die Beschreibungen von `buchung_aendern`, `entscheiden`, `aufgabe_aendern` und `frage_schliessen` nennen den Löschwunsch und den eigenen Weg samt Rückholweg.
- **AC-3:** Der Antworttext nach dem Stornieren einer Buchung enthält „Nicht gelöscht“ und den Rückholweg (Status gebucht). Nach einer anderen Änderung der Buchung (z. B. Nummer) steht der Hinweis nicht.
- **AC-4:** Der Antworttext nach `entscheiden` mit `verworfen` oder `ersetzt` enthält „Nicht gelöscht“ und den Rückholweg (entscheiden, Status gewählt). Bei `gewaehlt` steht der Hinweis nicht.
- **AC-5:** Der Antworttext nach `frage_schliessen` mit `entfaellt` sagt ehrlich, dass es kein Wiedereröffnen gibt; bei `geklaert` steht er nicht.
- **AC-6:** Der Antworttext nach Aufgabe `entfaellt` nennt „wieder offen“ als Rückholweg.
- **AC-7:** Die bisherigen Antwortsätze bleiben unverändert und stehen vor dem Zusatz (Teilstring-Tests der bestehenden Tests bleiben grün).
- **AC-8:** Die Texte nennen nichts Reisespezifisches; in der Beispielreise (Ida, Karl) gibt es keine Namen oder Pfade außerhalb davon.
- **AC-9:** `engine/.venv/bin/python -m pytest -q engine/tests` ist insgesamt grün; die neuen Tests sind ohne die Änderungen rot (TDD RED).

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** ADR-0001 (Kern und Prüfstelle). Keine neue ADR nötig: Das Vorhaben ändert nur Texte des Konnektors, es entsteht weder eine Art noch ein Baustein noch eine Grundform (ADR-0002, ADR-0003 unberührt).

## Definition of Done

- [ ] Anleitung enthält den Löschwunsch-Absatz (alle Rollen)
- [ ] Beschreibungen von `buchung_aendern`, `entscheiden`, `aufgabe_aendern`, `frage_schliessen` nennen Löschwunsch und Rückholweg
- [ ] Antworttexte (Stornieren, Verwerfen/Ersetzen, Aufgabe/Frage `entfaellt`) nennen „Nicht gelöscht“ und den Rückholweg
- [ ] Neue Tests in `test_konnektor.py` (vorher rot, jetzt grün)
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests` insgesamt grün
- [ ] `docs/konnektor.md` hat den Abschnitt Löschwunsch

## Test Plan

- `test_konnektor.py`: (a) `anleitung()` für Gast, Mitwirkende und Organisator:in enthält das Stichwort Löschwunsch und die Wege; (b) `WERKZEUGE` und die abgesetzten Konstanten enthalten je den Satz zum Löschwunsch; (c) Antworttexte von `buchung_aendern` (storniert vs. Nummer ändern), `entscheiden` (verworfen, ersetzt, gewaehlt) und `frage_schliessen` (entfaellt vs. geklaert) auf der Beispielreise-Kopie; (d) Aufgabe `entfaellt` über den Konnektor-Aufruf mit Mock des Schreibwegs, wie die vorhandenen Tests.
- Kriterium 8 (nichts Reisespezifisches): Ein Test sammelt alle neuen Texte (Anleitung-Absatz, Beschreibungen, Zusätze der Antworttexte) und prüft, dass darin weder Pfade (`/home`, `/var`), Adressen (`http`, `@`) noch Namen aus Reisen vorkommen; erlaubt sind nur Werkzeug- und Statusnamen.
- Gegenprobe ohne Änderung: die neuen Tests sind rot.
- Alle vorhandenen Tests unverändert grün.

## Known Limitations

- Für Ding, Wissen, Tag, Wahlstelle und Plan gibt es keinen Löschweg; der Assistent verweist auf die Rückmeldung. Ob das Produkt später einen Weg braucht, ist eine eigene Frage an den Kern (ADR-0001), nicht Teil dieses Vorhabens.
- Offene Fragen lassen sich nicht wieder öffnen; Zurückholen nur über eine neue Frage.
- Ob der Assistent den Hinweis wirklich einhält, hängt vom AI-Client ab; geprüft wird, dass die Texte da sind.

## Offene Punkte

- Keine für den Product Owner: Beide Fragen der Analyse sind im Code beantwortet (Aufgabe: „wieder offen“ gibt es; Frage: kein Wiedereröffnen, so wird es ehrlich gesagt).

## Changelog

- 2026-10-30: Erstfassung.
- 2026-10-30: Definition of Done, ADR-Abschnitt und Test zu Kriterium 8 ergänzt; Umfang um Aufgaben und Fragen erweitert (begründet in Purpose); Briefing nennt dazu eine Freigabe-Frage.
- 2026-10-30 (Umsetzung): Ausnahmen von AC-7/AC-9 begründet. (1) Die Längengrenze der Anleitung in `test_regeln.py` stieg von 3650 auf 3900 Zeichen, weil der Absatz aus AC-1 sonst nicht hineinpasst (vorher 3640). Der Absatz ist bewusst knapp, die Rückholwege stehen in Werkzeugbeschreibungen und Antworttexten. (2) Im Test zu AC-4 war die Konstellation „ersetzt“ unzulässig (V-03.b war schon verworfen); die Testdaten nutzen jetzt V-02.a → V-02.b, die Regel in `entscheiden` blieb unverändert. (3) Der Hinweis auf `rueckmeldung_geben` im Anleitungs-Absatz steht mit „sofern erlaubt“, weil Gäste keine Rückmeldung geben können.
