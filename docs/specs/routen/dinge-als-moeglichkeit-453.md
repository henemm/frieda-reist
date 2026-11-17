---
entity_id: dinge-als-moeglichkeit-453
type: refactor
created: 2026-11-17
updated: 2026-11-17
status: draft
workflow: alternativen-453-dinge
issue: 453
---

# Allgemeines Feld `dinge:` je Möglichkeit einer Wahlstelle (#453, Variante b aus #353)

Kontext und Analyse: [docs/context/alternativen-453-dinge.md](../../context/alternativen-453-dinge.md) (Abschnitt „Analysis“ ist verbindlich).
Vorläufer: [orte-als-moeglichkeit-353](orte-als-moeglichkeit-353.md) (Schritt 2 von #353), der das vierte Ding-Feld einführte.

## Approval

- [ ] Approved

## Source

- **Datei:** `engine/routen.py` (Laden und Prüfen der Optionen in `Routen.__init__`, neue Hilfsfunktion `dinge_aufteilen`)
- **Identifier:** Feld `dinge` einer Option (`V-….x`) in `plan/routen.yaml`; Schreibweg `option_bauen`, `option_inhalt_ok`,
  `option_aendern`, `PLAIN_FELDER` in `engine/schreiben.py`; `OPTION_FELDER` in `engine/konnektor.py`; `nachziehen` und
  `nachziehen_speicher` in `engine/neu.py`

## Purpose

Heute verweist eine Möglichkeit über vier getrennte Felder auf ihre Dinge (`unterkuenfte`, `aufenthalte`, `orte`, `strecken`).
Das widerspricht dem Grundsatz „Alternativen kann jedes Ding sein“ (#353): jede neue Grundform brächte ein weiteres Feld mit
Sonderfällen in Prüfung, Schreibweg und Konnektor. Ein einziges Feld `dinge:` mit gemischten IDs (Präfix = Grundform) macht die
Möglichkeit offen für jedes Ding und schließt nebenbei eine Prüflücke (U- und E-IDs einer Möglichkeit werden heute nicht auf
Existenz geprüft). Für Leserinnen und Leser der Seite ändert sich nichts.

## Scope

**In:**

- Speicherformat: `dinge: [U-…|A-…|O-…|E-…]` (gemischte IDs, Eingabereihenfolge bleibt) ersetzt `unterkuenfte`, `aufenthalte`, `orte`,
  `strecken` an Optionen. `folge: [T-…|V-…]` bleibt eigenes Feld (Reiseteil, keine Ding-Liste).
- Hilfsfunktion `dinge_aufteilen` in `engine/routen.py`: teilt `dinge` nach Präfix in die bisherigen Gruppen auf; aufgerufen in
  `Routen.__init__` direkt nach `self.wahl = …`, vor der Prüfschleife, auf Kopien. Alle Leser (`nacht`, Halte, `merkmale_*`,
  `wahl_aus`, Karte, Vorlage, Packliste) bleiben unverändert, die Seitendaten ebenso.
- Prüfer: unbekannter Präfix = Fehler; Existenzprüfung für alle vier Präfixe; alte Felder an Optionen = Prüffehler.
- Inhaltsregel als Präfixregel: `{U}` allein, `{folge}` allein, `{E, A, O}` zusammen.
- Schreibweg: `option_bauen`, `option_inhalt_ok`, `option_aendern`, `PLAIN_FELDER` mit einem Feld `dinge`; Verlauf `wechsel("dinge", …)`.
- Konnektor: Schema `things` (englisch) mit deutschem Alias `dinge`; die alten Parameter (`accommodations`, `stays`, `places`, `legs`
  bzw. deutsch `unterkuenfte`, `aufenthalte`, `orte`, `strecken`) werden weiter angenommen und in `dinge` übersetzt, stehen aber
  nicht mehr im Schema; Mischung alt + neu = Ablehnung.
- Formatwechsel (#250): `neu.py nachziehen` und `nachziehen_speicher` stellen Optionen von den alten Feldern auf `dinge` um
  (an der Stelle des ersten alten Felds, idempotent, Meldung über `texte`); `aufraeumen.art_der_option` und `arten_ableiten` lesen
  über `dinge_aufteilen`.
- Texte in allen `engine/texte_*.py`; Beispielreise Wanderung: V-03 und V-06 auf `dinge:`.
- Doku: `docs/alternativen.md`, `docs/konnektor.md`, `docs/design.md`, `docs/ontologie.md`.

**Nicht in diesem Vorhaben:**

- Wegfall der alten Konnektor-Parameter: Folge-Issue mit Datum, nachdem der Formatwechsel auf der Instanz gelaufen ist.
- Umstellung der Leser auf `dinge` statt auf die aufgeteilten Gruppen (großer Eingriff ohne Nutzen für den Menschen).
- Neue Bedeutung einer Möglichkeit (keine neue Rechenregel, kein „Ort der Nacht aus Orten“).
- `folge` in `dinge` aufnehmen.
- Änderung der Seite, der Seitendaten, der Karte, des Kalenders, der Packliste, des Wächters.
- Änderung der Beispielreise Stadtwochenende (sie hat keine Wahlstellen; der Testfall nutzt eine erfundene Wahlstelle als Testdaten).

## Datenformat vorher und nachher

Vorher (Beispielreise, Auszug):

```yaml
V-03:
  optionen:
    - id: V-03.a
      unterkuenfte: [U-02]
V-06:
  optionen:
    - id: V-06.a
      orte: [O-04]
    - id: V-06.b
      orte: [O-06]
```

Nachher:

```yaml
V-03:
  optionen:
    - id: V-03.a
      dinge: [U-02]
V-06:
  optionen:
    - id: V-06.a
      dinge: [O-04]
    - id: V-06.b
      dinge: [O-06]
```

Gemischt (gültig, Eingabereihenfolge bleibt): `dinge: [E-02, A-01, O-04]`. Ungültig: `dinge: [U-02, O-04]` (U nur allein),
`dinge: [X-01]` (unbekannter Präfix), `dinge: [O-99]` (unbekanntes Ding), `unterkuenfte: [U-02]` neben oder statt `dinge` (altes Feld).

## Prüfstelle ADR-0001 (zehn Fragen)

1. Ontologie: `dinge` ist ein Feld der Grundform Wahl, kein Katalog; durchgespielt an der Wanderung (V-03 Unterkunft, V-06 Orte,
   V-01 `folge`) und am Stadtwochenende (keine Wahlstellen; Testfall mit erfundener Wahlstelle A gegen A, etwa zwei Restaurants).
2. Kein Katalog in der Software: die Präfixe sind Grundformen, keine Arten oder Merkmale.
3. Keine KI: reine Präfix- und Existenzregeln.
4. Tür für Claude: `things`/`dinge` im Konnektor, `docs/konnektor.md` Pflicht; Übergang für alte Parameter.
5. Herkunft: unverändert (Merkmale mit `quelle`).
6. Rollen: Entscheider-Sperre `option_aendern.9` bleibt.
7. IDs und Verlauf: keine neue ID-Sorte; Wechsel erscheint als `wechsel("dinge", …)`; Umstellung durch `nachziehen` als Formatwechsel, Reisespeicher nur anhängend.
8. PWA: Seitendaten behalten die Gruppen, die Seite bleibt unverändert; Browser-Tests laufen unverändert weiter.
9. Claude Code: keine Reiseinhalte, nur erfundene Beispieldaten.
10. Doku: `docs/alternativen.md`, `docs/konnektor.md`, `docs/design.md`, `docs/ontologie.md`.

Kein Widerspruch zum Kern erkannt; kein Rückgriff auf den Product Owner nötig.

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `routen.MUSTER`, `routen.ist` | module | Grundform aus dem ID-Präfix |
| Reisespeicher (`engine/reisespeicher.py`) | module | Laden und Speichern der Routen; Umstellung läuft über `roh` |
| Textkatalog `engine/texte*.py` | module | Prüf-, Ablehnungs- und Nachziehtexte in allen Sprachen |
| `engine/schnittstelle.py` | module | englischer Name `things`, alte Namen als „weiter angenommen“ |
| Orte-als-Möglichkeit (#353 Schritt 2) | spec | liefert Sortenregel und Muster; wird durch Präfixregel abgelöst |
| Tests der einbindenden Instanzen | downstream | Schema und Meldungstexte ändern sich; Lauf vor dem Vorspulen |

## Scope (betroffene Dateien)

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/routen.py` | MODIFY | `dinge_aufteilen`; Aufruf in `Routen.__init__` vor der Prüfschleife; Existenzprüfung je Präfix (Prüfschleife bei `option_aufenthalt`/`option_ort`); Prüffehler für alte Felder und unbekannten Präfix |
| `engine/schreiben.py` | MODIFY | `option_bauen` (liest `dinge`, Reihenfolge bleibt, Existenz über `id_liste`), `option_inhalt_ok` (Präfixregel), `option_aendern` (ein Feld), `PLAIN_FELDER` |
| `engine/konnektor.py` | MODIFY | `OPTION_FELDER`: vier Felder raus, `dinge` rein; Eingabeschritt übersetzt alte Parameter, Mischung = Ablehnung |
| `engine/schnittstelle.py` | MODIFY | `dinge` → `things`; alte Namen im Block „früher Namen, weiter angenommen“ |
| `engine/neu.py` | MODIFY | `nachziehen`, `nachziehen_speicher` (Umstellung, idempotent); `aufraeumen.art_der_option`, `arten_ableiten` über `dinge_aufteilen` |
| `engine/texte_de.py`, `engine/texte_en.py`, weitere `texte_*.py` | MODIFY | `schreiben.option_bauen.2`, `schreiben.option_aendern.5`, `konnektor.feld.option_felder.*`, neue `pruefung.routen.option_*` (unbekanntes Ding, unbekannter Präfix, altes Feld), Meldung für `nachziehen`, Ablehnung bei Mischung |
| `beispiel/reisen/beispielreise/plan/routen.yaml` | MODIFY | V-03, V-06 auf `dinge:` |
| `engine/tests/test_option_dinge.py` | CREATE | Tests zu den Acceptance Criteria |
| `engine/tests/test_option_orte.py`, `test_option_aufenthalte.py`, `test_schreiben.py`, `test_routen.py`, `test_neu.py` | MODIFY | Testdaten und Erwartungen auf `dinge:` (anpassen, nicht abschwächen) |
| `docs/alternativen.md`, `docs/konnektor.md`, `docs/design.md`, `docs/ontologie.md` | MODIFY | Feld `dinge`, Präfixregel, Konnektor-Übergang |

Unverändert: `engine/vorlage.html`, `engine/karte.py`, `engine/packliste.py`, `engine/waechter.py`, `engine/kalender.py`,
`engine/bauen.py`, `engine/reisespeicher.py`, Browser-Tests.

### Estimated Changes

- Dateien: ca. 10 Code/Daten, 4 Doku, mehrere Testdateien
- LoC: +350/−120 (inkl. Tests)
- Risiko: MITTEL (Formatwechsel aller Reisen, Konnektor-Schema; Leser bleiben durch die Aufteilung unberührt)

## Implementation Details

Stellen sind mit Funktionsnamen benannt (Zeilen verschieben sich).

- **`dinge_aufteilen`** (`engine/routen.py`): nimmt die `dinge`-Liste einer Option und liefert die Gruppen `unterkuenfte`,
  `aufenthalte`, `orte`, `strecken` (Reihenfolge je Gruppe wie in der Eingabe). Präfix `U` → Unterkünfte, `A` → Aufenthalte,
  `O` → Orte, `E` → Strecken; jeder andere Präfix ist ein Fehler. Einzige Stelle, die Präfixe kennt; `schreiben.py`, `neu.py`
  nutzen sie ebenfalls.
- **`Routen.__init__`:** Die Aufteilung läuft direkt nach `self.wahl = …`, vor der Prüfschleife, und arbeitet auf Kopien der
  Optionen (die geladenen Rohdaten bleiben unverändert, damit der Schreibweg das Format nicht verliert). Grund für diesen Ort: viele
  Leser lesen `self.wahl`/`self.option` direkt, nicht erst `wahl_aus`.
- **Prüfschleife:** je Ding Existenz gegen die passende Menge (`self.unterkuenfte`, `self.aufenthalte`, `self.orte`, `self.strecken`);
  Fehler `pruefung.routen.option_*` mit Wahlstelle, Möglichkeit und Ding. Altes Feld an einer Option (`unterkuenfte`, `aufenthalte`,
  `orte`, `strecken`) = eigener Prüffehler mit Hinweis auf `dinge`. Der Prüfer und die Aufteilung zusammen schließen die
  Existenzlücke für U und E im handgepflegten YAML (der Schreibweg prüft über `id_liste` schon alle Präfixe).
- **Inhaltsregel:** Präfixmenge der Dinge ist `{U}`, oder `{E, A, O}` (nicht leer, Teilmenge), und `folge` nie zusammen mit `dinge`.
- **`schreiben.py`:** `option_bauen` liest `dinge` in Eingabereihenfolge; `option_inhalt_ok` wendet die Präfixregel an (Docstring
  nennt sie); `option_aendern` setzt, ersetzt oder leert `dinge`; `PLAIN_FELDER` führt `dinge` als Listenwert ohne Anführungszeichen.
- **`konnektor.py` / `schnittstelle.py`:** `OPTION_FELDER` hat `dinge` (Array von Strings, Beschreibung `@konnektor.feld.option_felder.dinge`),
  englisch `things`. Der Eingabeschritt übersetzt die alten Parameter (englisch wie deutsch) in `dinge`, wenn `dinge`/`things`
  fehlt; sind alte und neue Parameter zugleich gesetzt, lehnt er mit Begründung ab. Die alten Parameter stehen nicht im Schema.
- **`neu.py`:** `nachziehen` und `nachziehen_speicher` setzen für jede Option mit alten Feldern `dinge` an die Stelle des ersten alten
  Felds (ruamel `insert`, Muster der Umbenennung bei Wahlstellen), mit den IDs in der Reihenfolge der alten Felder
  `unterkuenfte, aufenthalte, orte, strecken` (Eingabereihenfolge der Quelle, soweit sie erkennbar ist); die alten Felder
  fallen weg. Gibt es `dinge` schon, wird nichts doppelt umgestellt. Meldung über `texte`. `art_der_option` und `arten_ableiten`
  nutzen `dinge_aufteilen`.
- **Beispielreise:** V-03 `dinge: [U-02]`/`[U-03]`, V-06 `dinge: [O-04]`/`[O-06]`; V-01 behält `folge`.

## Test Plan

### Automated Tests (TDD RED)

Neue Datei `engine/tests/test_option_dinge.py`; Testdaten nur erfundene Daten und die beiden Beispielreisen (Abwandlungen als Daten
über yaml, nicht über Textanker). Die Spalte nennt das zugehörige Acceptance Criterion.

| Test | Prüft |
|------|-------|
| `test_dinge_wird_in_gruppen_aufgeteilt_und_baut` | AC-1 |
| `test_dinge_bewahrt_eingabereihenfolge` | AC-2 |
| `test_unbekannter_praefix_ist_ein_fehler` | AC-3 |
| `test_unbekanntes_ding_je_praefix_ist_ein_fehler` | AC-4 |
| `test_altes_feld_an_option_ist_pruefehler` | AC-5 |
| `test_praefixregel_u_allein_folge_allein_e_a_o_zusammen` | AC-6 |
| `test_schreibweg_nimmt_dinge_und_verlauf_hat_wechsel` | AC-7 |
| `test_option_update_dinge_setzen_ersetzen_leeren` | AC-8 |
| `test_konnektor_schema_hat_things_mit_alias_dinge` | AC-9 |
| `test_konnektor_alte_parameter_werden_uebersetzt` | AC-10 |
| `test_konnektor_mischung_alt_und_neu_wird_abgelehnt` | AC-11 |
| `test_nachziehen_stellt_optionen_auf_dinge_um` | AC-12 |
| `test_nachziehen_ist_idempotent` | AC-13 |
| `test_nachziehen_speicher_stellt_um_und_ist_idempotent` | AC-14 |
| `test_beispielreise_wanderung_nutzt_dinge_und_baut_gleich` | AC-15 |
| `test_stadtwochenende_baut_unveraendert_und_erfundene_wahlstelle_a_gegen_a` | AC-16 |
| `test_seitendaten_unveraendert_gegen_vorher` | AC-17 |
| `test_arten_ableiten_und_art_der_option_ueber_dinge` | AC-18 |
| `test_neue_schluessel_in_allen_sprachen` (plus bestehende `test_texte.py`) | AC-19 |
| gesamte Suite `engine/.venv/bin/python -m pytest -q engine/tests -n auto` | AC-20 |
| Tests der Instanzen mit dem Branch | AC-21 |

GIVEN/WHEN/THEN, Beispiel: GIVEN eine Wahlstelle V-91 am Tag T-03 mit den Möglichkeiten a `dinge: [E-02, O-04]` und b `dinge: [A-01]`,
WHEN `bauen()` läuft, THEN trägt die Ausgabe von V-91.a `strecken: [E-02]` und `orte: [O-04]`, V-91.b `aufenthalte: [A-01]`, es gibt
keinen Fehler, und `daten.json` ist bis auf diese Wahlstelle gleich dem Stand mit den alten Feldern.

Abnahme (außerhalb der Suite): über den Konnektor an einer frischen oder vorhandenen eigenen Testreise, nie an echten Reisen,
an beiden Reisetypen (Wanderung mit Plänen, Reise ohne Pläne wie das Stadtwochenende).

## Acceptance Criteria

Alle prüfbar durch Tests in `engine/tests/test_option_dinge.py`.

**Laden und Prüfen**

- **AC-1 (Aufteilen):** Given eine Möglichkeit mit `dinge: [E-02, A-01, O-04]`, when die Reise lädt und baut, then stehen
  `strecken`, `aufenthalte` und `orte` in der Ausgabe der Option wie bei den alten Feldern, ohne Fehler.
- **AC-2 (Reihenfolge):** Given `dinge: [O-06, O-04]`, when die Reise lädt, then bleibt die Reihenfolge der Eingabe in der Gruppe `orte` erhalten.
- **AC-3 (unbekannter Präfix):** Given `dinge: [X-01]`, when die Reise lädt, then genau ein Prüffehler mit Wahlstelle, Möglichkeit und ID; der Bau meldet ihn wie die übrigen Optionsfehler.
- **AC-4 (Existenz je Präfix):** Given je ein unbekanntes `U-99`, `E-99`, `A-99`, `O-99` in einer Möglichkeit, when die Reise lädt, then gibt es je einen Prüffehler (auch für U und E, die vorher ungeprüft blieben).
- **AC-5 (alte Felder):** Given eine Option mit `unterkuenfte`, `aufenthalte`, `orte` oder `strecken` (allein oder neben `dinge`), when die Reise lädt, then ein Prüffehler mit Hinweis auf `dinge`; `folge` bleibt ohne Fehler.
- **AC-6 (Präfixregel):** Given Möglichkeiten (a) `{U}` allein, (b) `folge` allein, (c) `{E, A, O}` in jeder Teilmenge, then gültig; Given `{U, O}`, `{U, E}`, `{folge, dinge}` oder leeres `dinge`, then ungültig (`option_inhalt_ok` falsch bzw. Prüffehler).

**Schreibweg**

- **AC-7 (Schreiben):** Given eine Testreise, when `choice_create`/`option_create` Optionen mit `dinge` anlegen, then steht `dinge` in `plan/routen.yaml` als Liste der IDs in Eingabereihenfolge, der Verlauf enthält `wechsel("dinge", …)`, nichts wird überschrieben; ein unbekanntes Ding oder eine ungültige Mischung wird mit Begründung abgelehnt (`schreiben.option_bauen.2`).
- **AC-8 (Ändern):** Given eine bestehende Möglichkeit, when `option_update` `dinge` setzt, ersetzt oder leert, then gilt die Präfixregel auf dem zusammengeführten Stand (`schreiben.option_aendern.5`); ein Update mit nur `dinge` ist eine Änderung, nicht `option_aendern.8`; die Entscheider-Sperre `option_aendern.9` bleibt.

**Konnektor**

- **AC-9 (Schema):** Given `OPTION_FELDER` und das erzeugte Schema, then enthält es `things` (Array von Strings, Beschreibung aus dem Katalog) mit deutschem Alias `dinge` und keines der vier alten Felder.
- **AC-10 (Übergang):** Given ein Aufruf mit den alten Parametern (englisch `accommodations`, `stays`, `places`, `legs` und deutsch `unterkuenfte`, `aufenthalte`, `orte`, `strecken`), when der Konnektor ihn verarbeitet, then wird er angenommen und als `dinge` geschrieben (Eingabereihenfolge: Unterkünfte, Aufenthalte, Orte, Strecken, wie sie übergeben wurden), und das Ergebnis ist dasselbe wie bei `things`.
- **AC-11 (Mischung):** Given ein Aufruf mit `things`/`dinge` und zugleich einem alten Parameter, then Ablehnung mit Begründung aus dem Katalog; nichts wird geschrieben.

**Formatwechsel (#250)**

- **AC-12 (Umstellen):** Given eine Reise mit alten Feldern an Optionen, when `neu.py nachziehen` läuft, then haben alle Optionen `dinge` an Stelle des ersten alten Felds, die alten Felder sind weg, die Reihenfolge der IDs bleibt, `folge` und andere Felder bleiben unberührt, und die Meldung kommt aus `texte`; die Reise baut danach mit gleicher Ausgabe wie vorher.
- **AC-13 (Idempotenz):** Given dieselbe Reise nach `nachziehen`, when `nachziehen` erneut läuft, then ist das Ergebnis byte-gleich und es gibt keine Meldung.
- **AC-14 (Server-Variante):** Given eine Reise im Reisespeicher mit mehreren Versionen, when `nachziehen_speicher` läuft, then steht die umgestellte Fassung als neue, angehängte Version; ein zweiter Lauf legt keine weitere an.

**Beispielreisen und Seite**

- **AC-15 (Wanderung):** Given `beispiel/reisen/beispielreise`, when sie baut, then nutzen V-03 und V-06 `dinge:`, es gibt keinen Fehler, und Summe 595 min, 25,4 km, ↑1075, ↓1025 sowie die Pläne P-A 610 min und P-B 595 min sind unverändert.
- **AC-16 (Stadtwochenende):** Given `beispiel/reisen/stadtwochenende` (keine Wahlstellen), when sie baut, then baut sie ohne Fehler und Warnung, `daten.json` ist gleich dem Stand vorher; Given dazu im Test eine erfundene Wahlstelle am Sonntag: Möglichkeit a `dinge: [A-02]` (Stadtmuseum) gegen Möglichkeit b `dinge: [A-90]` (erfundenes zweites Ziel, nur in den Testdaten angelegt), then baut sie ohne Fehler, die Beispielreise selbst bleibt unverändert.
- **AC-17 (Seite unverändert):** Given die gebaute Wanderung vor und nach der Umstellung, then sind die Seitendaten `R.wahlstellen[].optionen[]` inhaltlich gleich (gleiche Gruppen `unterkuenfte`, `aufenthalte`, `orte`, `strecken`, `folge`); `vorlage.html` und `karte.py` sind nicht geändert; die Browser-Tests `seiten_option_aufenthalt.mjs` und `seiten_option_ort.mjs` bestehen unverändert.
- **AC-18 (Ableiten):** Given eine Reise ohne `arten.yaml` mit `dinge` an Optionen, when `arten_ableiten` und `aufraeumen.art_der_option` laufen, then liefern sie dieselben Arten wie vorher mit den alten Feldern.

**Texte und Gesamtlauf**

- **AC-19 (Texte):** Given alle Sprachdateien, then stehen die neuen und geänderten Schlüssel (`konnektor.feld.option_felder.dinge`, `pruefung.routen.option_*`, `schreiben.option_bauen.2`, `schreiben.option_aendern.5`, Nachziehmeldung, Mischungs-Ablehnung) in allen Sprachen, und die Ausnahmelisten in `engine/tests/test_texte.py` sind nicht länger geworden.
- **AC-20 (Gesamtlauf):** `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen (CI: `tests (leer)`, `tests (instanz)`, `gitleaks` auf dem vorgespulten Commit).
- **AC-21 (Instanz-Tests, Nachweis im PR-Text):** Weil Schema und Meldungstexte sich ändern, laufen vor dem Vorspulen die Tests der einbindenden Instanzen mit dem Branch (Anleitung im Reisen-Repo der Instanz); es kommt kein Fehler gegenüber `main` hinzu.

## Risiken

- **Formatwechsel aller Reisen:** Eine Reise nach dem Software-Wechsel ohne Umstellung wäre ein Prüffehler (alte Felder). Gegenmittel: Umstellung im selben Schritt wie der Software-Stand (`nachziehen`, Workflow „Software nachziehen“), Idempotenztest (#250); kein Handschritt.
- **AI-Clients mit altem Schema:** senden noch `unterkuenfte` usw. Gegenmittel: alte Parameter weiter angenommen und übersetzt; Wegfall erst in einem Folge-Issue mit Datum, nachdem die Instanz umgestellt ist.
- **Aufteilung zu spät:** erfolgt sie erst in `wahl_aus`, sehen `nacht`, Halte und `merkmale_*` (lesen `self.wahl` direkt) keine Gruppen. Deshalb Aufteilung in `Routen.__init__` vor der Prüfschleife, auf Kopien; AC-1 und AC-15 decken es.
- **Prüfer wird strenger:** U und E werden nun auf Existenz geprüft; handgepflegtes YAML mit falscher ID bricht dann sichtbar (gewollt, vorher stiller Fehler). Die Beispielreisen und die Tests sind vorab zu prüfen.
- **Regel „Unterkunft allein“:** muss als Präfixregel erhalten bleiben, sonst ändert sich die Nacht-Logik (`nacht` liest Unterkünfte der Optionen); AC-6 und AC-15.
- **Instanz nutzt `unterkuenfte`, `strecken`, `folge` in Optionen (Zählung ohne Inhalte):** Instanz-Tests vor dem Vorspulen (AC-21).
- **Stadtwochenende ohne Wahlstelle:** die Beispielreise prüft die Änderung nicht; deshalb Testfall mit erfundener Wahlstelle (AC-16), nie Änderung an der Beispielreise.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue.
- **Rationale:** Vereinheitlicht ein Feldformat nach dem bestehenden Muster gemischter ID-Listen (`fuer:` der Buchung, `an:` von
  Wahlstellen, ADR-0007, ADR-0010) innerhalb des Kerns nach [ADR-0001](../../adr/0001-kern.md); keine neue Grundform, kein Katalog.
  Messung siehe Prüfstelle oben.

## Definition of Done

- [ ] AC-1 bis AC-19 durch automatische Tests belegt, AC-20 grün
- [ ] AC-21 im PR-Text belegt
- [ ] Doku (vier Dateien) angepasst
- [ ] Abnahme am Konnektor an beiden Reisetypen
- [ ] Folge-Issue für den Wegfall der alten Konnektor-Parameter mit Datum angelegt
- [ ] CI grün, Stand auf `main` ausgeliefert, Umstellung der Reisen mit `nachziehen` im selben Schritt
- [ ] Kommentar in #453 mit Stand

## Changelog

- 2026-11-17: Initial spec created (dinge-als-moeglichkeit-453).
