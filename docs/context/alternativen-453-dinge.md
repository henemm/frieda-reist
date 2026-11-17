# Context: alternativen-453-dinge (#453, Variante b aus #353)

## Request Summary

Eine Möglichkeit (Option `V-…x`) einer Wahlstelle verweist heute über getrennte Felder je Grundform auf ihre Dinge:
`unterkuenfte: [U-…]`, `aufenthalte: [A-…]`, `orte: [O-…]`, `strecken: [E-…]`, daneben `folge: [T-…|V-…]` (Reiseteil).
Zu prüfen (ADR-0001, zehn Fragen; beide Beispielreisen) und gegebenenfalls umzusetzen: ein allgemeines Feld `dinge:` je
Möglichkeit, das die vier Ding-Felder ersetzt; Formatwechsel mit Umstellung in `neu.py nachziehen` (#250).

## Related Files

| Datei | Relevanz |
|---|---|
| `engine/routen.py` | Prüfung (869–875 nur A/O auf Existenz), `nur_in_verworfenen` 751, `art_der_wahl` 1406, `arten_der_option` 1428, `merkmale_pruefen` 1531, `merkmale_aus` 1621–1638, `nacht` 1753–1764, Halte 1780–1810, `alle_strecken` 2199, `unterkuenfte_aus` 2297, `wahl_aus` 2181–2185 (Seitendaten je Option) |
| `engine/schreiben.py` | `PLAIN_FELDER` 1241, `DING_ARTEN` 1236, `option_bauen` 2662–2671, `option_inhalt_ok` 4053 (Regel: `unterkuenfte`/`folge` allein, `strecken`/`aufenthalte`/`orte` zusammen), `option_aendern` 4108–4120 |
| `engine/konnektor.py` | `OPTION_FELDER` 2826–2840 (Schema option_create/option_update/choice_create), `option_text` 848 |
| `engine/schnittstelle.py` | englische Namen (accommodations, stays, places, legs, sequence), Liste 244 |
| `engine/karte.py` | 144–159: Plan/Alternative je Ding aus den Seitendaten |
| `engine/neu.py` | `nachziehen` 1047ff. (Inline-Umbenennung bei Wahlstellen 1102–1114 als Vorbild), `aufraeumen.art_der_option` 432, `arten_ableiten` 515–528 |
| `engine/vorlage.html` | liest `o.orte`, `o.strecken`, `o.aufenthalte`, `o.unterkuenfte`, `o.folge`, `o.tage` aus den Seitendaten |
| `engine/texte_*.py` | Feldbeschreibungen `konnektor.feld.option_felder.*`, Fehlertexte `schreiben.option_bauen.*`, `option_aendern.*`, `wahlstelle_anlegen.4`, `pruefung.routen.option_*` |
| `engine/packliste.py` | indirekt über `nur_in_verworfenen` |
| Tests | `test_option_orte.py` (17), `test_option_aufenthalte.py` (8), `test_schreiben.py`, `test_routen.py`; Browser `seiten_option_aufenthalt.mjs`, `seiten_option_ort.mjs` |
| `beispiel/reisen/beispielreise/plan/routen.yaml` | Optionen mit `folge`, `orte`, `unterkuenfte`; Stadtwochenende hat keine Wahlstellen |
| Doku | `docs/alternativen.md:21`, `docs/konnektor.md`, `docs/design.md:43`, `docs/ontologie.md:141` |

Nicht betroffen auf Optionsebene: `waechter.py`, `reisespeicher.py`, `kalender.py`, `bauen.py`.

## Existing Patterns

- **Gemischte ID-Listen gibt es schon:** Buchung `fuer: [U-01]`/`[E-20]`; Wahlstelle `an:` (Prüfung `routen.py` `an_pruefen`:
  Schleife über Arten, `ist(art, x)`, dann Menge); Elternbezug `an:` (ADR-0007), Packliste `an:` (ADR-0010).
- Grundform aus der ID: `routen.MUSTER` + `ist(art, wert)`; in `schreiben.py` Tabellen nach Präfix (`DING_ARTEN`, `{"U": "unterkuenfte", …}`).
- Formatwechsel: `neu.py nachziehen` ändert `roh` (geladen über den Reisespeicher), idempotent, Meldung über `texte`;
  `nachziehen_speicher` führt dasselbe auf dem Server aus; der Workflow „Software nachziehen“ stellt Reisen im selben Stand um.
- Konnektor: englische Parameternamen mit deutschem Alias (`schnittstelle.py`), Texte im Katalog je Sprache.

## Dependencies

- Upstream: `routen.MUSTER`/`ist`, Reisespeicher (Laden/Speichern der Routen), Textkatalog.
- Downstream: Seitendaten `R.wahlstellen[].optionen[]` (Vorlage, Karte), Konnektor-Ausgabe, Packliste, Instanz-Tests
  (Meldungstexte und Schema ändern sich → Tests der Instanz vor dem Vorspulen).

## Existing Specs

- `docs/specs/routen/orte-als-moeglichkeit-353.md` (Schritt 2 von #353, Prüfstelle, Risiken).
- `docs/alternativen.md` (Standard für Wahlstellen).

## Risks & Considerations

- Formatwechsel betrifft alle Reisen: Umstellung muss automatisch und idempotent sein (#250); Instanz nutzt heute
  `unterkuenfte`, `strecken`, `folge` in Optionen (Zählung ohne Inhalte).
- Konnektor-Schema ändert sich: AI-Clients mit altem Schema senden noch `unterkuenfte` usw. Entscheidung nötig, ob alte
  Parameter weiter angenommen werden (Übergang) oder sofort abgelehnt.
- Seitendaten: Wird `dinge` beim Laden in die bisherigen Gruppen aufgeteilt, bleiben Vorlage, Karte und viele interne Stellen
  unverändert (geringeres Risiko). Volle Umstellung aller Leser wäre ein großer Eingriff ohne Nutzen für den Menschen.
- `folge` ist keine Ding-Liste (Tage/Reiseteil, rekursiv mit Wahlstellen) und bleibt eigenes Feld (Frage im Analyse-Schritt).
- U- und E-IDs einer Option werden heute nicht auf Existenz geprüft (nur A/O) — Lücke, die eine Prüfung über Präfixe schließt.
- Regel „Unterkunft allein“ muss als Präfixregel erhalten bleiben (Nacht-Logik `nacht` liest Unterkünfte der Optionen).

## Analysis

### Type
Feature (Formatwechsel der Reisedaten, alle Reisen)

### Prüfstelle ADR-0001 (Vorab-Messung)
1 Ontologie: `dinge` ist ein Feld der Grundform Wahl, kein Katalog; besteht. Durchgespielt an der Wanderung (V-03 Unterkunft,
V-06 Orte, V-01 folge); das Stadtwochenende hat keine Wahlstellen → Tests mit erfundener Wahlstelle (A gegen A, z. B. zwei
Restaurants) als Testdaten, Beispielreise selbst unverändert. 2 Kein Katalog: besteht (Präfixe sind Grundformen). 3 Keine KI:
besteht (Präfixregel). 4 Tür: `things`/`dinge` im Konnektor + `docs/konnektor.md` Pflicht. 5 Herkunft: unverändert. 6 Rollen:
Entscheider-Sperre `option_aendern.9` bleibt. 7 IDs/Verlauf: keine neue ID, Wechsel als `wechsel("dinge", …)` im Verlauf;
Umstellung durch `nachziehen` als Formatwechsel. 8 PWA: Seitendaten behalten die Gruppen → Seite unverändert. 9 Claude Code: nein.
10 Doku: `docs/alternativen.md`, `konnektor.md`, `design.md`, `ontologie.md`.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/routen.py | MODIFY | Hilfsfunktion `dinge_aufteilen` (Präfix → Gruppe, unbekannter Präfix = Fehler); Normalisierer in `Routen.__init__` direkt nach `self.wahl = …` (≈696), vor der Prüfschleife, auf Kopien; Existenzprüfung je Präfix in der Schleife 869–875 (schließt U/E-Lücke für handgepflegtes YAML); alte Felder an Optionen = Prüffehler |
| engine/schreiben.py | MODIFY | `option_bauen` 2662–2671 liest `dinge` (Reihenfolge der Eingabe bleibt, Existenz über `id_liste`); `option_inhalt_ok` 4053 als Präfixregel {U} / {folge} / {E,A,O}; `option_aendern` 4108–4120 ein Feld `dinge`; `PLAIN_FELDER` + `dinge` |
| engine/konnektor.py | MODIFY | `OPTION_FELDER` 2826–2840: vier Felder raus, `dinge` rein; Eingabeschritt übersetzt alte Parameter in `dinge`, Mischung alt+neu = Ablehnung |
| engine/schnittstelle.py | MODIFY | `PARAMETER` `dinge → things`; alte Namen im Block „früher Namen, weiter angenommen“ (≈169) |
| engine/neu.py | MODIFY | `nachziehen`/`nachziehen_speicher`: Optionen alt → `dinge` an Stelle des ersten alten Felds (ruamel `insert`, Muster 1102–1114), idempotent; `aufraeumen.art_der_option` 432 und `arten_ableiten` 515–529 über `dinge_aufteilen` |
| engine/texte_*.py | MODIFY | `schreiben.option_bauen.2`, `option_aendern.5`, `konnektor.feld.option_felder.*`, neue `pruefung.routen.option_*` (unbekanntes/fehlendes Ding, altes Feld), Meldung für `nachziehen` |
| beispiel/reisen/beispielreise/plan/routen.yaml | MODIFY | V-03, V-06 auf `dinge:` |
| engine/tests/* | MODIFY/CREATE | test_option_orte, test_option_aufenthalte, test_schreiben, test_routen, test_neu (Idempotenz), Konnektor-Übergang, Stadtwochenende-Fall |
| docs/* | MODIFY | alternativen.md:21, konnektor.md (37, 56, 459), design.md:43, ontologie.md:141 |

Unverändert: vorlage.html, karte.py, packliste.py, waechter.py, kalender.py, bauen.py, Browser-Tests (Seitendaten behalten Gruppen).

### Scope Assessment
- Files: ~10 Code/Daten + Doku + Tests
- Estimated LoC: +350/-120 (inkl. Tests)
- Risk Level: MEDIUM (Formatwechsel aller Reisen, Konnektor-Schema; Leser bleiben durch Normalisierer unberührt)

### Technical Approach
Speicherformat `dinge:` (gemischte IDs U/A/O/E, Eingabereihenfolge), `folge` bleibt eigenes Feld. Intern teilt eine einzige
Hilfsfunktion `dinge` beim Laden nach Präfix in die bisherigen Gruppen auf; alle Leser (nacht, Halte, merkmale, wahl_aus,
Karte, Vorlage, Packliste) bleiben unverändert. Wichtig: Aufteilung in `Routen.__init__` vor der Prüfschleife, nicht erst in
`wahl_aus`, weil viele Leser `self.wahl`/`self.option` direkt lesen. Konnektor: alte Parameter weiter annehmen und übersetzen
(nicht mehr im Schema), Mischung ablehnen. Reihenfolge: Hilfsfunktion → Routen → nachziehen → schreiben → Konnektor →
Texte/Beispiel/Doku → Tests inkl. Instanz-Tests vor dem Vorspulen.

### Präzisierung zum Kontext
Die Existenzlücke U/E besteht nur im Prüfer (handgepflegtes YAML); der Schreibweg prüft über `id_liste` bereits alle Präfixe.

### Dependencies
`routen.MUSTER`/`ist`; Reisespeicher; Textkatalog; Instanz-Tests (Schema, Meldungstexte).

### Open Questions
- keine Produktfrage; Übergangsdauer für alte Konnektor-Parameter: bis der Formatwechsel auf der Instanz gelaufen ist, Wegfall in einem Folge-Issue mit Datum (Tech-Entscheidung).
