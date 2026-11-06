---
entity_id: orte-als-moeglichkeit-353
type: feature
created: 2026-11-06
updated: 2026-11-06
status: draft
workflow: 353-orte-als-moeglichkeit
issue: 353
---

# Orte als Möglichkeiten einer Wahlstelle (#353, Schritt 2)

Kontext und Analyse: [docs/context/353-orte-als-moeglichkeit.md](../../context/353-orte-als-moeglichkeit.md) (Abschnitt „Analysis“ ist verbindlich).
Vorlage ist Schritt 1 (Aufenthalte ohne Nacht als Möglichkeit, Commit efb4920).

## Source

- **Datei:** `engine/routen.py` (Hauptstelle: Lesen und Prüfen der Optionen, `art_der_wahl`, `arten_der_option`, `merkmale_pruefen`, `merkmale_aus`, `nacht`)
- **Identifier:** Feld `orte` einer Option (`V-….x`) in `plan/routen.yaml`; Schreibweg `option_bauen`, `option_inhalt_ok`, `option_aendern` in `engine/schreiben.py`; `OPTION_FELDER` in `engine/konnektor.py`

## Purpose (Anlass)

Der Grundsatz „Alternativen kann jedes Ding sein, nur der Tag nicht“ (Product Owner, 6.11.2026, #353) gilt nach Schritt 1 für
Unterkünfte, Strecken, Aufenthalte und Reiseteile, aber noch nicht für Orte (`O-…`). Eine Schlechtwetter- oder Gipfelalternative
ist oft schlicht ein anderer Ort („Wasserfall oder Altendorf“). Orte haben seit ADR-0008 (Schritt a) eine freiwillige Art mit
Merkmalen; was fehlt, ist das Feld `orte:` an einer Möglichkeit mit Prüfung, Vergleich, Karte, Seite und Schreibweg.

**Bedeutung „ein Ort ist gewählt“ (Entscheidung des Tech Leads):** ein Ziel ohne Rechenbedeutung. Der Ort erscheint am Tag, im
Vergleich und auf der Karte. Anschluss, `start_ort`/`end_ort`, `tag_lauf` und der Ort der Nacht ändern sich nicht. „Ort der Nacht
aus `orte:`“ (Variante b) ist vertagt und steht als Vermerk in `docs/alternativen.md`.

## Scope

**In:**

- `orte: [O-…]` an einer Möglichkeit: lesen, prüfen (Prüfschlüssel `option_ort`), ausgeben, schreiben (`choice_create`,
  `option_create`, `option_update`), im Konnektor-Schema (`OPTION_FELDER`) und in `show`.
- Sortenregel: `orte` allein oder zusammen mit `aufenthalte` und/oder `strecken`; `unterkuenfte` und `folge` bleiben allein.
- Art und Merkmale: Art der Wahlstelle ohne `art:` aus dem ersten Ding mit Art (beim Ort nur, wenn er eine Art hat); Vergleich
  zeigt die Merkmale aller beteiligten Arten; Ort ohne Art ist erlaubt (nur Text, Plus, Minus).
- Karte: Ort einer Möglichkeit zählt als „im Plan verwendet“ und bekommt auf der Übersicht einen Punkt (Stand `plan`/`alternative`).
- Seite: Ortszeile mit Link zur Ortsseite in `optionBlock` und `optionEinzelheiten`.
- Warnung, wenn `nacht: V-…` nur Optionen mit `orte` (ohne Unterkunft) hat.
- `neu.py arten_ableiten`: Zweig für `orte`.
- Beispielreise: eine neue erfundene Wahlstelle mit zwei Orten (einer mit Art, O-06 ohne Art), als Beispielwert markiert.
- Texte in allen Sprachdateien, Doku, Tests.

**Nicht in diesem Schritt:**

- Ort der Nacht aus `orte:` (Variante b): vertagt, nur Vermerk in der Doku.
- Neues Tagesfeld für besuchte Orte und eigene Tageszeile für Orte: kein Format-Umbau; der Ort kommt über `wahl:` am Tag in den
  Wahlstellen-Block des Tags.
- Eintrag im Kalender (ein Ort hat keine Zeit).
- Erweiterung von `regeln_im_plan`/`im_plan` um Orte, die nur in einer Möglichkeit stehen (wie bei Aufenthalten in Schritt 1).
  Grenze: `an: O-…` einer anderen Wahlstelle wird durch einen solchen Ort nicht erreicht.
- Eigene Kennzeichnung „Alternative“ für den Kartenpunkt: er sieht aus wie ein normaler Planort (bewusste Grenze).
- Keine Umstellung des Datenformats: `orte:` an der Option kommt nur dazu, `neu.py nachziehen` fasst Optionen nicht an.

## Prüfstelle ADR-0001 (zehn Fragen, kurz)

1. Ontologie: betrifft die Grundformen Wahl und Ort; durchgespielt an der Wanderung (neue Wahlstelle) und am Stadtwochenende
   (keine Wahlstelle, Orte ohne Art, baut unverändert).
2. Kein Katalog in der Software: keine Art, kein Merkmal; Merkmale kommen aus der Art des Orts in der Reise.
3. Keine KI: reine Prüfregeln (Existenz, Sorten).
4. Tür für Claude: Feld `orte` in `choice_create`/`option_create`/`option_update`, Ausgabe in `show`, Doku `docs/konnektor.md`.
5. Herkunft: Merkmalwerte am Ort/an der Option mit der bestehenden Herkunftspflicht (`quelle`).
6. Rollen: Entscheidung weiter über `decide`.
7. IDs und Verlauf: keine neue ID-Sorte, nichts wird überschrieben.
8. PWA: Option zeigt Ortszeile, Vergleich und Karte; offline wie bisher; Browser-Rundgang in der Abnahme.
9. Claude Code: keine Reiseinhalte, nur erfundene Beispieldaten.
10. Doku: `docs/ontologie.md`, `docs/alternativen.md`, `docs/konnektor.md`, `docs/design.md`.

Kein Widerspruch zum Kern erkannt; kein Rückgriff auf den Product Owner nötig.

## Lösung

Stellen sind mit Funktionsnamen benannt (Zeilen verschieben sich).

### `engine/routen.py`

- **Prüfung der Optionen** (in der Schleife über `o in opts`, dort wo `option_aufenthalt` geprüft wird): für jedes `oid2` in
  `o.get("orte")` Fehler `texte.satz("pruefung.routen.option_ort", vid=…, oid=…, ort=…)`, wenn `oid2 not in self.orte`.
- **`art_der_wahl`**: nach den Aufenthalten ein Zweig über `o.get("orte")` mit `self.o_art.get(ort)`; Reihenfolge der Dinge in der
  Möglichkeit bleibt „erste Unterkunft, erster Aufenthalt, erster Ort“; ein Ort ohne Art zählt nicht (kein Fehler).
- **`arten_der_option`**: um `self.o_art.get(x) for x in o.get("orte")` ergänzen (Orte ohne Art fallen durch den vorhandenen
  Filter `x in self.arten` heraus).
- **`merkmale_pruefen`**: neues `o_extra` neben `u_extra`/`a_extra`/`s_extra`, gefüllt aus `o.get("orte")` mit den Kriterien der
  Wahlstelle; die Schleife über `self.orte` (heute `self.werte(oid, …, self.katalog.get(self.o_art[oid], {}))`) bekommt
  `{**Katalog der eigenen Art, **o_extra.get(oid, {})}`. Orte ohne Art bleiben ausgenommen (keine Merkmale).
- **`merkmale_aus`**: `for o2 in (o.get("orte") or [])[:1]: mk.update(self.mk_ort.get(o2, {}))`.
- **Ausgabe der Option** (Dict mit `"strecken": …, "unterkuenfte": …, "aufenthalte": …` in der Ausgabe der Wahlstellen): Feld
  `"orte": o.get("orte")`.
- **`nacht`** (Zweig `ist("wahl", n)`): Hat die Wahlstelle Optionen mit `orte`, aber keine mit `unterkuenfte`, gibt es die Warnung
  `pruefung.routen.nacht_nur_orte` (über `self.warne`); `ort` bleibt wie heute `next(iter(orte), None)` (also `None`), der
  Anschluss ändert sich nicht.
- **Unberührt:** `anschluss`, `tag_lauf`, `aufenthalte_des_tages`, `regeln_im_plan`.

### `engine/schreiben.py`

- **`PLAIN_FELDER`**: `"orte"` ergänzen (Listenwerte ohne Anführungszeichen schreiben, wie `aufenthalte`).
- **`option_bauen`**: `og = id_liste(o, "orte", r"O-\d+", roh, "orte")`; in `option_inhalt_ok` und in die Schleife der Felder
  aufnehmen.
- **`option_inhalt_ok`**: Teilmengenregel: `sorten <= {"strecken", "aufenthalte", "orte"}` oder höchstens eine Sorte
  (`unterkuenfte` und `folge` nur allein). Der Docstring nennt die neue Regel.
- **`option_aendern`**: Feld `orte` wie `aufenthalte` (setzen, ersetzen, leeren); Prüfung mit `option_inhalt_ok` auf dem
  zusammengeführten Stand (`option_aendern.5`).
- **`choice_create`** nutzt `option_bauen` je Option und bekommt `orte` damit mit.

### `engine/konnektor.py`

- **`OPTION_FELDER`**: Feld `orte` (Array von Strings, `description` mit `@konnektor.feld.option_felder.orte`), wirkt auf
  `choice_create`, `option_create` und über die Ableitung auf `option_update`.
- **`show`** (`Handbuch.option_text`): eine neue Zeile nennt die Orte der Möglichkeit mit Namen (`Handbuch.ort`), Vorsatz aus dem
  Katalog (neuer Schlüssel `konnektor.ausgabe.option_text.orte`). Aufenthalte und Strecken der Möglichkeit gibt `option_text` heute
  nicht aus; das bleibt so (nicht Teil dieses Schritts).

### `engine/texte_de.py`, `engine/texte_en.py` (und jede weitere Sprachdatei)

- Neu: `konnektor.feld.option_felder.orte`, `konnektor.ausgabe.option_text.orte`, `pruefung.routen.option_ort`, `pruefung.routen.nacht_nur_orte`.
- Geändert: `schreiben.option_bauen.2` und `schreiben.option_aendern.5` (Sorten nennen: `orte` allein oder mit `aufenthalte`/
  `strecken`), `schreiben.option_aendern.8` (Aufzählung der änderbaren Felder, ergänzt um `aufenthalte` und `orte`).
- Die Ausnahmelisten in `engine/tests/test_texte.py` dürfen nicht länger werden.

### `engine/karte.py`

- **`dinge_bezug`**: in beiden Schleifen (Wahlstellen des Tags: Stand `plan` bei `aktiv`, sonst `alternative`; Wahlstellen mit `an:`)
  auch `o.get("orte")` führen, wie `aufenthalte`. `stand`/`tage` enthalten dann auch O-IDs; der Docstring sagt es.
- **`orte_im_plan`**: Orte mit `stand.get(oid, "frei") != "frei"` kommen in die Menge (zusätzlich zur Verwendung durch Strecken,
  Tage, Unterkünfte, Aufenthalte). Regionen (Orte, an denen andere Orte hängen) bleiben ohne Punkt.

### `engine/vorlage.html`

- **`optionBlock`** und **`optionEinzelheiten`**: nach den Aufenthalten eine Zeile je `o.orte` mit Name und Link `#O-…` zur
  Ortsseite (Heimat des Orts bleibt dort, ADR-0003): vorhandene Bausteine `ortChips`/`tagOrteZeilen`-Zeile nutzen (kein neuer
  Baustein; entsteht doch einer, gelten die Regeln aus ADR-0002 und `docs/design.md`). Ein Ort ohne Ortsseite zeigt nur den Namen.
- Der Wahlstellen-Block des Tags zeigt die Option bereits; keine neue Tageszeile.

### `engine/neu.py`

- **`arten_ableiten`**: in der Schleife über die Optionen einer Wahlstelle ohne `bereich`/`art` ein Zweig über `o.get("orte")`:
  `b = b or (r.get("orte") or {}).get(oid, {}).get("art")` (nur wenn gesetzt, nur wenn die Art in den abgeleiteten Arten vorkommt).
  Kein Handschritt, kein Umbau von Bestandsdaten.

### Beispielreise `beispiel/reisen/beispielreise/plan/routen.yaml`

- Eine neue erfundene Wahlstelle (Nummer frei, nicht V-01, das an `folge` hängt) mit zwei Möglichkeiten: Ort mit Art (z. B.
  `O-05`, `ort_am_weg`) und `O-06` ohne Art; an einem Tag über `wahl:` angebunden; jeder Text als „(Beispiel)“ markiert,
  `quelle: "erfunden (Beispiel)"`. Die Orte werden so gewählt, dass die Tests aus #335 (Übersicht nur mit Orten des Plans,
  Zählungen) keine bisherige Annahme verlieren (siehe Risiken).
- Das Stadtwochenende bekommt keine Wahlstelle.

## Betroffene Dateien

| Datei | Änderung |
|---|---|
| `engine/routen.py` | MODIFY: Prüfung `option_ort`, `art_der_wahl`, `arten_der_option`, `merkmale_pruefen`, `merkmale_aus`, Ausgabe der Option, Warnung in `nacht` |
| `engine/schreiben.py` | MODIFY: `PLAIN_FELDER`, `option_bauen`, `option_inhalt_ok`, `option_aendern` |
| `engine/konnektor.py` | MODIFY: `OPTION_FELDER.orte`, `show` |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY: drei neue Schlüssel, drei geänderte |
| `engine/karte.py` | MODIFY: `dinge_bezug`, `orte_im_plan` |
| `engine/vorlage.html` | MODIFY: `optionBlock`, `optionEinzelheiten` |
| `engine/neu.py` | MODIFY: `arten_ableiten` |
| `engine/tests/test_option_orte.py` | CREATE |
| `engine/tests/seiten_option_ort.mjs` | CREATE |
| `beispiel/reisen/beispielreise/plan/routen.yaml` | MODIFY: neue Wahlstelle, Tag mit `wahl:` |
| `docs/ontologie.md`, `docs/alternativen.md`, `docs/konnektor.md`, `docs/design.md` | MODIFY (siehe Dokumentation) |

### Estimated Changes

- Dateien: ca. 13
- LoC: +300/−20 (rund die Hälfte Tests)
- Risiko: MITTEL (viele Stellen, aber ein neues optionales Feld nach erprobtem Muster; Bestand ohne `orte:` bleibt gleich)

## Dependencies

| Abhängigkeit | Richtung | Bemerkung |
|---|---|---|
| `o_art`, `mk_ort` (ADR-0008 Schritt a); `bezug`, Übersicht nur mit Orten des Plans (Schritt b) | upstream | unverändert |
| Schritt 1 (`aufenthalte`, gemischte Arten, `arten_der_option`) | upstream | Muster und Funktionen |
| Vergleich/Option auf der Seite, Karte, Konnektor, Wächter | downstream | lesen das neue Feld |
| Tests der Instanzen im Reisen-Repo | downstream | Meldungstexte und Konnektor-Schema ändern sich |

## Acceptance Criteria

Alle prüfbar durch Tests in `engine/tests/test_option_orte.py` (Funktionen `test_…`) oder `seiten_option_ort.mjs`; Testdaten nur
erfundene Daten und die beiden Beispielreisen.

- **AC-1 (Ort mit Art):** Given eine Wahlstelle mit Möglichkeit `orte: [O-05]` (Art `ort_am_weg`), when der Bau läuft, then steht
  `orte` in der Ausgabe der Option, kein Fehler, und die Merkmale der Art von O-05 stehen im Vergleich. Test
  `test_ort_als_option_wird_gelesen_und_verglichen`.
- **AC-2 (Ort ohne Art):** Given eine Möglichkeit `orte: [O-06]` (keine Art), when der Bau läuft, then kein Fehler und keine
  Warnung; der Vergleich zeigt nur Text, Plus und Minus der Möglichkeit, keine Ortsmerkmale. Test
  `test_ort_ohne_art_ist_erlaubt_und_vergleicht_nur_text`.
- **AC-3 (unbekannter Ort):** Given `orte: [O-99]`, when der Bau läuft, then genau ein Prüffehler `option_ort` mit Wahlstelle,
  Möglichkeit und Ort; der Bau meldet ihn wie `option_aufenthalt`. Test `test_unbekannter_ort_in_option_ist_ein_fehler`.
- **AC-4 (Sortenregel):** Given Möglichkeiten mit (a) `orte` allein, (b) `orte` + `aufenthalte`, (c) `orte` + `strecken`,
  (d) `orte` + `aufenthalte` + `strecken`, then sind sie gültig; given `orte` + `unterkuenfte` oder `orte` + `folge` (und
  `unterkuenfte`/`folge` mit anderen Sorten), then ist es ungültig (`option_inhalt_ok` falsch, Ablehnung `option_bauen.2`/
  `option_aendern.5`); `unterkuenfte` und `folge` allein bleiben gültig. Test `test_sortenregel_orte_mit_aufenthalten_und_strecken`.
- **AC-5 (Schreibweg):** Given eine frische Testreise, when `choice_create` (mit `orte` in den Optionen), `option_create` und
  `option_update` (setzen, ersetzen, leeren) laufen, then steht `orte` in `plan/routen.yaml` als Liste von O-IDs, der Verlauf ist
  angehängt, nichts ist überschrieben; ein unbekannter Ort wird mit Begründung abgelehnt; `option_update` mit nur `orte` ist
  eine Änderung (nicht `option_aendern.8`). Test `test_schreibweg_nimmt_orte_in_optionen`.
- **AC-6 (Konnektor-Schema und show):** Given `OPTION_FELDER`, then enthält es `orte` (Array von Strings) mit Beschreibung aus dem
  Katalog; `show` einer Wahlstelle nennt die Orte der Möglichkeit mit Namen. Test `test_konnektor_schema_und_show_kennen_orte`.
- **AC-7 (gemischter Vergleich):** Given eine Wahlstelle ohne `art:` mit Möglichkeiten Ort (Art `ort_am_weg`) und Aufenthalt (Art
  `besichtigung`), when der Bau läuft, then enthalten die Kriterien der Wahlstelle die Merkmale beider Arten, und jede Möglichkeit
  mahnt nur Pflichtmerkmale ihrer eigenen Art. Test `test_gemischter_vergleich_ort_und_aufenthalt`.
- **AC-8 (Art der Wahlstelle):** Given eine Wahlstelle ohne `art:`, deren erste Möglichkeit einen Ort ohne Art und deren zweite
  einen Ort mit Art hat, then ist die Art der Wahlstelle die Art des ersten Orts mit Art; haben alle Orte keine Art, dann
  `allgemein` ohne Fehler. Test `test_art_der_wahlstelle_aus_erstem_ort_mit_art`.
- **AC-9 (Karte):** Given ein Ort, der nur in einer Möglichkeit einer Wahlstelle am Tag steht, when die Karte gebaut wird, then
  bekommt er auf der Übersicht einen Punkt; `dinge_bezug` gibt `plan` für den Ort der aktiven Möglichkeit und `alternative` für
  den anderer Möglichkeiten; ein Ort ohne jede Verwendung bleibt ohne Punkt (Regel aus #335 gilt weiter). Test
  `test_ort_der_moeglichkeit_bekommt_punkt_auf_uebersicht`.
- **AC-10 (Nacht, Warnung):** Given `nacht: V-…`, deren Möglichkeiten nur `orte` haben, when der Bau läuft, then gibt es die Warnung
  `nacht_nur_orte` (kein Fehler), und `nacht.ort` ist unverändert (`None`). Test `test_nacht_nur_mit_orten_warnt_und_aendert_nichts`.
- **AC-11 (Nachtort und Anschluss unverändert):** Given dieselbe Reise mit und ohne `orte:` in einer Wahlstelle am Tag, then sind
  `start_ort`/`end_ort`, Nachtort und Anschluss aller Tage gleich. Test `test_orte_in_option_aendern_nachtort_und_anschluss_nicht`.
- **AC-12 (Kalender):** Given ein Ort als entschiedene Möglichkeit, when der Kalender gebaut wird, then enthält er keinen Eintrag für
  den Ort; die übrigen Einträge sind unverändert. Test `test_kalender_hat_keinen_eintrag_fuer_orte`.
- **AC-13 (Seite):** Given die gebaute Wanderung mit der neuen Wahlstelle, when die Tagesseite im Browser geöffnet ist, then zeigt
  die Option eine Ortszeile mit dem Ortsnamen und einem Link `#O-…` zur Ortsseite (im `optionBlock` des Tags und in
  `optionEinzelheiten`), der Vergleich enthält die Merkmale des Orts mit Art, und es gibt keine Seitenfehler. Test
  `test_seite_zeigt_ort_der_option` mit `seiten_option_ort.mjs`.
- **AC-14 (Beispielreise Wanderung):** Given `beispiel/reisen/beispielreise`, when sie baut, then enthält sie die neue Wahlstelle mit
  zwei Orten (einer mit Art, O-06 ohne), alle Werte als Beispiel markiert; Summe 595 min, 25,4 km, ↑1075, ↓1025 und die
  Pläne P-A 610 min und P-B 595 min sind unverändert. Test `test_beispielreise_hat_wahlstelle_mit_orten`.
- **AC-15 (Stadtwochenende):** Given `beispiel/reisen/stadtwochenende` (keine Wahlstelle, Orte ohne Art), when sie baut, then
  baut sie ohne Fehler und Warnung, und `daten.json` unterscheidet sich vom Stand vor der Änderung nicht. Test
  `test_stadtwochenende_baut_unveraendert`.
- **AC-16 (Bestand ohne `orte:`):** Given Reisen ohne `orte:` an Optionen, then sind Ausgabe der Optionen und alle Werte gleich wie
  vorher; das Feld `orte` steht dort als `None`/fehlt (wie `aufenthalte`). Test `test_bestand_ohne_orte_bleibt_gleich`.
- **AC-17 (Texte):** Given alle Sprachdateien, then stehen `konnektor.feld.option_felder.orte`, `pruefung.routen.option_ort` und
  `pruefung.routen.nacht_nur_orte` in allen Sprachen, die geänderten Schlüssel nennen die Sorten richtig, und die Ausnahmelisten
  in `engine/tests/test_texte.py` sind nicht länger geworden. Test: bestehende Prüfungen in `test_texte.py` plus
  `test_neue_schluessel_der_orte_in_allen_sprachen`.
- **AC-18 (`arten_ableiten`):** Given eine Reise ohne `arten.yaml`, deren Wahlstelle nur Optionen mit `orte` hat (Ort mit `art`),
  when `arten_ableiten` läuft, then ist die Art der Wahlstelle die des ersten Orts mit Art; ohne Art am Ort entsteht keine Art
  und kein Fehler. Test `test_arten_ableiten_kennt_orte_in_optionen`.
- **AC-19 (Gesamtlauf):** `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen (CI auf dem vorgespulten
  Commit); die frischen #335-Tests zur Karte (`test_karte_*`, `test_art_uebersicht.py`, `seiten_karte.mjs`,
  `seiten_art_uebersicht.mjs`) sowie `test_tagesplan.py` und `test_tagesseite.py` bestehen ohne Abschwächung.
- **AC-20 (Instanz-Tests, Nachweis im PR-Text):** Weil Meldungstexte und Konnektor-Schema sich ändern, laufen vor dem Vorspulen die
  Tests der einbindenden Instanzen mit dem Branch; Vergleichsbasis sind die 13 bekannten Fehler in main (ADR-0008, nicht von
  #353); es kommt kein neuer Fehler hinzu.

## Test Plan (Geplante Tests)

| Datei | Test | Prüft |
|---|---|---|
| `engine/tests/test_option_orte.py` | `test_ort_als_option_wird_gelesen_und_verglichen` | AC-1 |
| `engine/tests/test_option_orte.py` | `test_ort_ohne_art_ist_erlaubt_und_vergleicht_nur_text` | AC-2 |
| `engine/tests/test_option_orte.py` | `test_unbekannter_ort_in_option_ist_ein_fehler` | AC-3 |
| `engine/tests/test_option_orte.py` | `test_sortenregel_orte_mit_aufenthalten_und_strecken` | AC-4 |
| `engine/tests/test_option_orte.py` | `test_schreibweg_nimmt_orte_in_optionen` | AC-5 |
| `engine/tests/test_option_orte.py` | `test_konnektor_schema_und_show_kennen_orte` | AC-6 |
| `engine/tests/test_option_orte.py` | `test_gemischter_vergleich_ort_und_aufenthalt` | AC-7 |
| `engine/tests/test_option_orte.py` | `test_art_der_wahlstelle_aus_erstem_ort_mit_art` | AC-8 |
| `engine/tests/test_option_orte.py` | `test_ort_der_moeglichkeit_bekommt_punkt_auf_uebersicht` | AC-9 |
| `engine/tests/test_option_orte.py` | `test_nacht_nur_mit_orten_warnt_und_aendert_nichts` | AC-10 |
| `engine/tests/test_option_orte.py` | `test_orte_in_option_aendern_nachtort_und_anschluss_nicht` | AC-11 |
| `engine/tests/test_option_orte.py` | `test_kalender_hat_keinen_eintrag_fuer_orte` | AC-12 |
| `engine/tests/test_option_orte.py` + `seiten_option_ort.mjs` | `test_seite_zeigt_ort_der_option` (Browser) | AC-13 |
| `engine/tests/test_option_orte.py` | `test_beispielreise_hat_wahlstelle_mit_orten` | AC-14 |
| `engine/tests/test_option_orte.py` | `test_stadtwochenende_baut_unveraendert` | AC-15 |
| `engine/tests/test_option_orte.py` | `test_bestand_ohne_orte_bleibt_gleich` | AC-16 |
| `engine/tests/test_texte.py` | bestehende Schlüssel-/Sprachprüfungen; `test_neue_schluessel_der_orte_in_allen_sprachen` | AC-17 |
| `engine/tests/test_option_orte.py` (eine eigene Testdatei für `arten_ableiten` gibt es nicht) | `test_arten_ableiten_kennt_orte_in_optionen` | AC-18 |
| gesamte Suite | `pytest -q engine/tests` | AC-19 |
| Tests der Instanzen mit dem Branch | Anleitung im Reisen-Repo der Instanz | AC-20 |

GIVEN/WHEN/THEN, Beispiel: GIVEN eine Wahlstelle V-91 am Tag T-03 mit den Möglichkeiten „Altendorf“ (`orte: [O-04]`) und
„Lichtenhainer Wasserfall“ (`orte: [O-06]`), WHEN `bauen()` läuft, THEN trägt V-91.a und V-91.b das Feld `orte`, der Vergleich hat
die Merkmale von `ort_am_weg`, O-06 bleibt ohne Merkmale, und die Seite verlinkt beide Orte.

Abnahme (außerhalb der Suite): über den Konnektor an einer frischen Testreise, nie an echten Reisen, und an beiden Reisetypen
(Wanderung mit Plänen, Reise ohne Pläne wie das Stadtwochenende).

## Risiken

- **Kartentests von #335:** Ein neuer Ort im Plan der Beispielreise kann „Übersicht nur mit Orten des Plans“, Zählungen und
  Seitenprüfungen ändern (`test_karte_*`, `test_art_uebersicht.py`, `seiten_karte.mjs`, `seiten_art_uebersicht.mjs`,
  `test_tagesplan.py`, `test_tagesseite.py`). Vor dem Ändern der Beispielreise diese Tests lesen; Orte der neuen Wahlstelle so
  wählen, dass sie keine bisherige Annahme brechen (Orte, die ohnehin im Plan stehen, plus O-06). Erwartete Zählungen nur
  anpassen, wenn die Änderung begründet ist, nie abschwächen.
- **Tests der Instanz sind Pflicht vor dem Vorspulen** (`option_bauen.2`, `option_aendern.5/.8` und das Konnektor-Schema ändern
  sich); Vergleichsbasis: 13 bekannte Fehler in main, nicht von #353.
- **Kartenpunkt ohne Kennzeichnung:** der Ort einer Alternative sieht aus wie ein Planort. Bewusste Grenze, Vermerk in der Doku.
- **`regeln_im_plan`:** ein Ort nur in einer Möglichkeit zählt nicht als „im Plan“; `an: O-…` einer anderen Wahlstelle erreicht ihn
  nicht (wie bei Aufenthalten in Schritt 1).
- **Latente Mehrdeutigkeit in `nacht`** (`next(iter(orte))` bei mehreren Unterkunftsorten) bleibt und wird durch die Warnung nicht
  schlimmer.
- **Viele Stellen:** vergessene Stelle erzeugt stillen Ausfall (Ort fehlt auf Seite oder Karte); die Tests AC-1 bis AC-13 decken je
  eine Stelle ab.

## Dokumentation

- `docs/ontologie.md`: der Satz „Orte als Möglichkeit folgen in Schritt 2“ wird zur Aussage, dass ein Ort Möglichkeit sein kann
  (Ziel ohne Rechenbedeutung, Art freiwillig).
- `docs/alternativen.md`: `orte:` in der Aufzählung der Dinge einer Möglichkeit und in der Sortenregel (Zeilen zu Sorten);
  neuer Vermerk **Vertagt: Ort der Nacht aus `orte:` (Variante b)** mit Begründung (Beispiele sind Ziele; „Übernachten in A oder B“
  ist die Unterkunft am Ort) und Hinweis auf die Warnung `nacht_nur_orte`; Grenze zu `regeln_im_plan` und zum Kartenpunkt.
- `docs/konnektor.md`: Feld `orte` bei `choice_create`/`option_create`/`option_update` und in `show`.
- `docs/design.md`: Ortszeile in der Möglichkeit (wiederverwendeter Baustein, Heimat bleibt die Ortsseite, ADR-0003).

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue.
- **Rationale:** Setzt ADR-0008 (Orte mit Art) und das Muster aus Schritt 1 fort; Messung am Kern nach
  [ADR-0001](../../adr/0001-kern.md) siehe oben. Die Bedeutung „Ort gewählt“ ist eine Tech-Lead-Entscheidung innerhalb des Kerns.

## Definition of Done

- [ ] AC-1 bis AC-18 durch automatische Tests belegt, AC-19 grün
- [ ] AC-20 im PR-Text belegt
- [ ] Doku (vier Dateien) angepasst
- [ ] Browser-Rundgang an beiden Reisetypen
- [ ] CI grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Commit auf `main` vorgespult
- [ ] Kommentar in #353 mit Stand (Schritt 2 erledigt, Variante b vertagt)

## Changelog

- 2026-11-06: Initial spec created (orte-als-moeglichkeit-353).
- 2026-11-06 (TDD RED): Hinweise für die Umsetzung aus dem Schreiben der Tests:
  - `test_option_orte.py` ändert `plan/routen.yaml` und `plan/arten.yaml` als Daten (yaml), nicht über Textanker; die
    Abwandlungen nutzen V-90 bis V-98 und O-90 bis O-92. Die Wahlstelle der Beispielreise (AC-14) bekommt deshalb eine andere
    Nummer: **V-06** (V-04/V-05 belegt `test_tagesplan.py`), an **T-03** über `wahl:`, Möglichkeiten Altendorf (O-04, Art
    `ort_am_weg`) und Lichtenhainer Wasserfall (O-06, ohne Art).
  - Die Art `ort_am_weg` der Beispielreise hat keine Merkmale; AC-1/AC-7/AC-13 fügen im Test das erfundene Pflichtmerkmal
    `einkehr` hinzu (Wert an O-04). `arten.yaml` der Beispielreise muss dafür nicht geändert werden.
  - AC-9 nutzt einen neuen Ort O-90 mit eigener Lage: O-01 bis O-06 sind alle Station einer Strecke und hätten schon heute einen Punkt.
  - AC-18 ist nur erreichbar, wenn der Art-Schlüssel des Orts auch sonst abgeleitet wird (Test: Ort mit Art `pension`); eine nicht
    abgeleitete Ortsart (`ort_am_weg`) darf die Art einer Unterkunft in derselben Wahlstelle nicht verdrängen (also nicht naiv
    `b = b or ort_art`).
  - Bestehende Tests, die die Umsetzung berührt (anpassen, nicht abschwächen): `test_option_aufenthalte.py` ersetzt die T-03-Zeile
    der Beispielreise wörtlich (`TAG`); bekommt T-03 `wahl: [V-06]`, muss dieser Anker mitgehen. Dieselbe Datei prüft
    `match="nur eines von"` (Text von `option_aendern.5`, der sich ändert): auf `e.value.schluessel` umstellen.
  - AC-5 prüft die Ablehnung über `Ablehnung.schluessel == "schreiben.option_aendern.5"`; AC-6 sucht den Vorsatz
    `konnektor.ausgabe.option_text.orte` in `zeige("V-91.b")` (Handbuch spricht die Vorgabesprache).
- 2026-11-06 (GREEN, Adversary F001, Entscheidung des Tech Leads): Die Mahnregel in `merkmale_aus` gilt für jede Wahlstelle ohne
    `art:` und jede Möglichkeit mit Dingen: gemahnt werden nur die Pflichtmerkmale der eigenen Arten und der Wahlstelle (AC-7
    verallgemeinert). Folge im Bestand: weniger Mahnungen, nie mehr (z. B. Gasthof gegen Pension: der Gasthof mahnt kein
    Pflichtmerkmal der Pension mehr). Begründung: dieselbe Regel für alle Sorten statt einer Sonderregel für Orte. Seite: `ortChips`
    verlinkt immer; ein Ort ohne Ortsseite kommt bei gültiger Reise nicht vor (`option_ort`).
- 2026-11-06 (Validierung): Der Hinweis `schreiben.option_bauen.1` nennt `aufenthalte` und `orte` noch nicht als Inhalt einer
  Option (Adversary F003, nur Text, im Bestand schon für `aufenthalte`); erfasst als #364. Die Beispielreise nutzt für AC-1 O-04
  (Art `ort_am_weg`), nicht O-05 wie in Lösung und AC-1 notiert. Der AC-9-Test prüft den Stand `alternative` jetzt ohne Bedingung.

## Approval

- [ ] Approved
