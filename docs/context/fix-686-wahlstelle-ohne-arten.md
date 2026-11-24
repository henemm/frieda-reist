# Context: fix-686-wahlstelle-ohne-arten

## Request Summary
In einer Reise ohne Arten meldet `choice_create` (Schreibweg `wahlstelle_anlegen`) Erfolg, die Wahlstelle ist danach aber
nirgends sichtbar und nicht entscheidbar. Ziel (#686): Ein Schreibwerkzeug meldet nie Erfolg für etwas, das danach nicht
existiert; außerdem soll die Übernahme oder Definition von Arten den Plan sofort sichtbar machen.

## Related Files
| File | Relevance |
|------|-----------|
| engine/schreiben.py:923 `plan_sicherstellen` | legt `plan/routen.yaml` an, trägt ihn aber nur mit Arten in `reise.json` ein |
| engine/schreiben.py:951 `routen_laden`, :962 `routen_speichern` | einzige Lese-/Schreibstelle des Plans im Schreibweg (30 Aufrufer von `routen_speichern`) |
| engine/schreiben.py:1509 `route_stand` | Probebau; ruft `plan_sicherstellen`; ohne Eintrag liefert er `{}` statt einer Ablehnung |
| engine/schreiben.py:2733 `wahlstelle_anlegen` | legt Frage (`frage_zeile`) und Wahlstelle an, ohne zu prüfen, ob der Plan gebaut wird |
| engine/schreiben.py:350 `arten_speichern`, :384 `art_definieren`, :4738 `arten_uebernehmen` | Arten schreiben; tragen den Plan nicht ein |
| engine/schreiben.py:5666 `Schreiber.schreiben` | ein Vorgang = eine Arbeitskopie; jede `Ablehnung` verwirft alles (auch eine schon angelegte Frage) |
| engine/bauen.py:801 | Routenmodell nur, wenn `reise.json` `routen` hat (`if r_cfg:`) |
| engine/routen.py, texte_de.py `pruefung.routen.51` | ein Plan ohne Arten ist ein Baufehler („plan/arten.yaml fehlt oder hat keine Arten“) |
| engine/neu.py:1062 `nachziehen` | Umstellung bestehender Reisen (Regel: kein Handschritt nach Software-Wechsel) |
| engine/tests/test_neu.py:275 | frische Reise aus der Vorlage über den Schreibweg füllen (Arten zuerst) |

## Existing Patterns
- Ablehnungen mit Textschlüssel `schreiben.<funktion>.<n>` in `engine/texte_<sprache>.py` (alle Sprachen), `raise Ablehnung(...)`.
- `route_stand` als Vorprüfung fast aller Schreibwerkzeuge des Plans; `plan_sicherstellen` wird dort schon aufgerufen.
- Rücknahme ist automatisch: `Ablehnung` → keine Fassung im Reisespeicher.

## Dependencies
- Upstream: `bauen.Bauer`, `arten_laden`, `reise.json` (`routen.datei`, `tagesplan`, `unterkuenfte`), `ids.yaml` (neue_id).
- Downstream: alle Plan-Werkzeuge des Konnektors (item_create, day_*, plan_*, choice_*, option_*, booking_*, start_end_set, fixed_date_set, decide …).

## Existing Specs
- docs/specs/routen/, docs/specs/konnektor/ (Schreibweg), docs/ontologie.md (Arten), ADR-0001 Kern, ADR-0011 Vorlagen für Arten.

## Erste Einschätzung
- Variante „Plan auch ohne Arten eintragen“ widerspricht dem Bau (`pruefung.routen.51`): die Reise würde nicht mehr bauen.
  Bleibt: Schreibweg lehnt Schreiben in den Plan ohne Arten mit klarer Begründung ab, zentral (nicht je Werkzeug), und
  `art_definieren`/`arten_uebernehmen` tragen den Plan sofort ein.
- Bestehende Reisen mit Arten, aber ohne Eintrag (Altlast aus dem Fehler): `nachziehen` trägt den Plan ein.

## Risks & Considerations
- Zentraler Haken in `routen_speichern` trifft auch `plan_sicherstellen` (Gerüst) → dort intern schreiben.
- Werkzeuge, die heute ohne Arten „funktionieren“ (z. B. Start/Ende, Tag ohne Nacht?) würden abgelehnt; prüfen, ob eines davon
  tatsächlich sichtbar wirkt (dann wäre es heute schon unsichtbar → gleiche Lücke).
- Alle Sprachen für den neuen Text; Konnektor-Beschreibung von choice_create ggf. Hinweis.
- Nebenbefund (Meldungen zu gelöschten Testreisen in my_trips) ist ein eigenes Thema → eigenes Issue.

## Analysis

### Type
Bug (Schreibweg meldet Erfolg für Plan-Inhalte, die der Bau still übergeht).

### Befund (über die Wahlstelle hinaus)
Nicht nur `wahlstelle_anlegen` ist betroffen: Jedes Werkzeug, das `routen_speichern` aufruft, schreibt in einer Reise ohne
Arten in eine `plan/routen.yaml`, die nicht in `reise.json` eingetragen ist, und meldet Erfolg. Ohne `route_stand` (also ganz
ohne Probebau) schreiben: `wert_eintragen`, `wert_leeren`, `lage_eintragen`, `track_anhaengen`, `kartenpunkte_ablegen`,
`tag_aendern`, `tag_anlegen`, `termin_setzen`, `start_ende_setzen`. Mit `route_stand` (Probebau liefert `{}` statt Fehler):
`ding_anlegen`, `wahlstelle_anlegen`, `option_anlegen`, `entscheiden`, `buchung_*`, `plan_*` usw. Eine Prüfung je Werkzeug
würde Lücken lassen; die Prüfung gehört an die eine Schreibstelle.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/schreiben.py | MODIFY | `routen_speichern` wird die geprüfte Schreibstelle der Werkzeuge: ohne Arten `Ablehnung("schreiben.plan.ohne_arten")` (Hinweis: erst kinds_adopt oder kind_define); mit Arten nach dem Schreiben Plan eintragen (`plan_sicherstellen`). Neue rohe Funktion (z. B. `routen_datei_schreiben`) ohne Prüfung für `plan_sicherstellen` (Gerüst), `routen_normalisieren`, `neu.py` |
| engine/schreiben.py | MODIFY | `arten_speichern` (also `art_definieren`, `arten_uebernehmen`, `merkmal_*`): liegt `plan/routen.yaml` schon vor, trägt danach `plan_sicherstellen` den Plan ein (zweiter Teil des Issues) |
| engine/neu.py | MODIFY | Aufrufe :355, :1138 auf die rohe Funktion; `nachziehen`: Reise mit Arten und `routen.yaml`, aber ohne Eintrag in `reise.json` bekommt ihn (Altlast des Fehlers; läuft über `nachziehen-speicher` beim Veröffentlichen) |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Ablehnungstext `schreiben.plan.ohne_arten` in beiden Sprachen |
| engine/konnektor.py / schnittstelle | evtl. MODIFY | Beschreibung von choice_create/item_create: Plan braucht Arten (nur wenn die Beschreibungen das heute nicht sagen) |
| engine/tests/test_schreiben*.py (neu: test_plan_ohne_arten_686.py) | CREATE | RED: Reise ohne Arten → choice_create, item_create, start_end_set, day_create werden abgelehnt, keine Frage F-… bleibt; kinds_adopt nach vorhandener routen.yaml → reise.json hat `routen`; nachziehen trägt Altlast ein; Beispielreisen unverändert |
| docs/funktionen/ (Seite zu Varianten/Plan) | MODIFY | Nutzersicht: Pläne, Auswahlen und Tage brauchen zuerst Arten |

### Scope Assessment
- Files: ~6 (+1 Testdatei)
- Estimated LoC: +120/-10
- Risk Level: MEDIUM — zentrale Schreibstelle aller Plan-Werkzeuge; Beispielreisen haben Arten und Eintrag (unberührt),
  aber Tests, die Plan-Werkzeuge an Reisen ohne Arten rufen, werden rot und zeigen, wo heute still „Erfolg“ gemeldet wurde.

### Technical Approach
1. Plan ohne Arten eintragen ist ausgeschlossen (Bau-Regel `pruefung.routen.51`, ontologie.md): Reise würde nicht mehr bauen.
2. Zentrale Ablehnung in `routen_speichern` (eine Stelle, deckt alle heutigen und künftigen Werkzeuge). `Schreiber.schreiben`
   verwirft bei `Ablehnung` die ganze Arbeitskopie → die schon angelegte offene Frage verschwindet mit. Keine Prüfung in
   `route_stand`, weil `uebersicht_wert`/`kartenstatus` lesend darüber laufen.
3. Einheitliches Eintragen: nach jedem geprüften Schreiben und nach `arten_speichern` (wenn ein Plan existiert)
   `plan_sicherstellen` → der Plan ist sofort sichtbar, ohne Umweg über ein weiteres Werkzeug.
4. `nachziehen` heilt Reisen, die durch den Fehler Arten + Plan, aber keinen Eintrag haben (Regel: kein Handschritt).
5. Am Kern gemessen (ADR-0001): keine neue Grundform, keine Arten in der Software (ADR-0011 bleibt Angebot), nur eine klare
   Ablehnung statt stiller Lücke → kein Konflikt.

### Dependencies
`bauen.Bauer` (Bedingung `if r_cfg:`), `arten_laden`, `neue_id` (W-IDs für tagesplan/unterkuenfte), `Schreiber.schreiben`
(Rücknahme bei Ablehnung), `neu.nachziehen`/`nachziehen_speicher`. Ein Test nutzt `routen_speichern` direkt
(`tests/test_hinweis_604.py`) – prüfen, ob seine Reise Arten hat.

### Out of Scope
Nebenbefund (Meldungen zu gelöschten Testreisen in my_trips) → eigenes Issue #687.

### Open Questions
- keine (technische Entscheidung; Verhalten folgt der bestehenden Bau-Regel)
