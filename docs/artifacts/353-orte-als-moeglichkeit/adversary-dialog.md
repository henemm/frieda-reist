# Adversary Dialog — 353-orte-als-moeglichkeit
Spec: docs/specs/routen/orte-als-moeglichkeit-353.md
Datum: 2026-11-06 11:19

## Checkliste
- [x] **AC-1 (Ort mit Art):** Given eine Wahlstelle mit Möglichkeit `orte: [O-05]` (Art `ort_am_weg`), when der Bau läuft, then steht `orte` in der Ausgabe der Option, kein Fehler, und die Merkmale der Art von O-05 stehen im Vergleich. Test `test_ort_als_option_wird_gelesen_und_verglichen`.
- [x] **AC-2 (Ort ohne Art):** Given eine Möglichkeit `orte: [O-06]` (keine Art), when der Bau läuft, then kein Fehler und keine Warnung; der Vergleich zeigt nur Text, Plus und Minus der Möglichkeit, keine Ortsmerkmale. Test `test_ort_ohne_art_ist_erlaubt_und_vergleicht_nur_text`.
- [x] **AC-3 (unbekannter Ort):** Given `orte: [O-99]`, when der Bau läuft, then genau ein Prüffehler `option_ort` mit Wahlstelle, Möglichkeit und Ort; der Bau meldet ihn wie `option_aufenthalt`. Test `test_unbekannter_ort_in_option_ist_ein_fehler`.
- [x] **AC-4 (Sortenregel):** Given Möglichkeiten mit (a) `orte` allein, (b) `orte` + `aufenthalte`, (c) `orte` + `strecken`, (d) `orte` + `aufenthalte` + `strecken`, then sind sie gültig; given `orte` + `unterkuenfte` oder `orte` + `folge` (und `unterkuenfte`/`folge` mit anderen Sorten), then ist es ungültig (`option_inhalt_ok` falsch, Ablehnung `option_bauen.2`/ `option_aendern.5`); `unterkuenfte` und `folge` allein bleiben gültig. Test `test_sortenregel_orte_mit_aufenthalten_und_strecken`.
- [x] **AC-5 (Schreibweg):** Given eine frische Testreise, when `choice_create` (mit `orte` in den Optionen), `option_create` und `option_update` (setzen, ersetzen, leeren) laufen, then steht `orte` in `plan/routen.yaml` als Liste von O-IDs, der Verlauf ist angehängt, nichts ist überschrieben; ein unbekannter Ort wird mit Begründung abgelehnt; `option_update` mit nur `orte` ist eine Änderung (nicht `option_aendern.8`). Test `test_schreibweg_nimmt_orte_in_optionen`.
- [x] **AC-6 (Konnektor-Schema und show):** Given `OPTION_FELDER`, then enthält es `orte` (Array von Strings) mit Beschreibung aus dem Katalog; `show` einer Wahlstelle nennt die Orte der Möglichkeit mit Namen. Test `test_konnektor_schema_und_show_kennen_orte`.
- [x] **AC-7 (gemischter Vergleich):** Given eine Wahlstelle ohne `art:` mit Möglichkeiten Ort (Art `ort_am_weg`) und Aufenthalt (Art `besichtigung`), when der Bau läuft, then enthalten die Kriterien der Wahlstelle die Merkmale beider Arten, und jede Möglichkeit mahnt nur Pflichtmerkmale ihrer eigenen Art. Test `test_gemischter_vergleich_ort_und_aufenthalt`.
- [x] **AC-8 (Art der Wahlstelle):** Given eine Wahlstelle ohne `art:`, deren erste Möglichkeit einen Ort ohne Art und deren zweite einen Ort mit Art hat, then ist die Art der Wahlstelle die Art des ersten Orts mit Art; haben alle Orte keine Art, dann `allgemein` ohne Fehler. Test `test_art_der_wahlstelle_aus_erstem_ort_mit_art`.
- [x] **AC-9 (Karte):** Given ein Ort, der nur in einer Möglichkeit einer Wahlstelle am Tag steht, when die Karte gebaut wird, then bekommt er auf der Übersicht einen Punkt; `dinge_bezug` gibt `plan` für den Ort der aktiven Möglichkeit und `alternative` für den anderer Möglichkeiten; ein Ort ohne jede Verwendung bleibt ohne Punkt (Regel aus #335 gilt weiter). Test `test_ort_der_moeglichkeit_bekommt_punkt_auf_uebersicht`.
- [x] **AC-10 (Nacht, Warnung):** Given `nacht: V-…`, deren Möglichkeiten nur `orte` haben, when der Bau läuft, then gibt es die Warnung `nacht_nur_orte` (kein Fehler), und `nacht.ort` ist unverändert (`None`). Test `test_nacht_nur_mit_orten_warnt_und_aendert_nichts`.
- [x] **AC-11 (Nachtort und Anschluss unverändert):** Given dieselbe Reise mit und ohne `orte:` in einer Wahlstelle am Tag, then sind `start_ort`/`end_ort`, Nachtort und Anschluss aller Tage gleich. Test `test_orte_in_option_aendern_nachtort_und_anschluss_nicht`.
- [x] **AC-12 (Kalender):** Given ein Ort als entschiedene Möglichkeit, when der Kalender gebaut wird, then enthält er keinen Eintrag für den Ort; die übrigen Einträge sind unverändert. Test `test_kalender_hat_keinen_eintrag_fuer_orte`.
- [x] **AC-13 (Seite):** Given die gebaute Wanderung mit der neuen Wahlstelle, when die Tagesseite im Browser geöffnet ist, then zeigt die Option eine Ortszeile mit dem Ortsnamen und einem Link `#O-…` zur Ortsseite (im `optionBlock` des Tags und in `optionEinzelheiten`), der Vergleich enthält die Merkmale des Orts mit Art, und es gibt keine Seitenfehler. Test `test_seite_zeigt_ort_der_option` mit `seiten_option_ort.mjs`.
- [x] **AC-14 (Beispielreise Wanderung):** Given `beispiel/reisen/beispielreise`, when sie baut, then enthält sie die neue Wahlstelle mit zwei Orten (einer mit Art, O-06 ohne), alle Werte als Beispiel markiert; Summe 595 min, 25,4 km, ↑1075, ↓1025 und die Pläne P-A 610 min und P-B 595 min sind unverändert. Test `test_beispielreise_hat_wahlstelle_mit_orten`.
- [x] **AC-15 (Stadtwochenende):** Given `beispiel/reisen/stadtwochenende` (keine Wahlstelle, Orte ohne Art), when sie baut, then baut sie ohne Fehler und Warnung, und `daten.json` unterscheidet sich vom Stand vor der Änderung nicht. Test `test_stadtwochenende_baut_unveraendert`.
- [x] **AC-16 (Bestand ohne `orte:`):** Given Reisen ohne `orte:` an Optionen, then sind Ausgabe der Optionen und alle Werte gleich wie vorher; das Feld `orte` steht dort als `None`/fehlt (wie `aufenthalte`). Test `test_bestand_ohne_orte_bleibt_gleich`.
- [x] **AC-17 (Texte):** Given alle Sprachdateien, then stehen `konnektor.feld.option_felder.orte`, `pruefung.routen.option_ort` und `pruefung.routen.nacht_nur_orte` in allen Sprachen, die geänderten Schlüssel nennen die Sorten richtig, und die Ausnahmelisten in `engine/tests/test_texte.py` sind nicht länger geworden. Test: bestehende Prüfungen in `test_texte.py` plus `test_neue_schluessel_der_orte_in_allen_sprachen`.
- [x] **AC-18 (`arten_ableiten`):** Given eine Reise ohne `arten.yaml`, deren Wahlstelle nur Optionen mit `orte` hat (Ort mit `art`), when `arten_ableiten` läuft, then ist die Art der Wahlstelle die des ersten Orts mit Art; ohne Art am Ort entsteht keine Art und kein Fehler. Test `test_arten_ableiten_kennt_orte_in_optionen`.
- [x] **AC-19 (Gesamtlauf):** `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen (CI auf dem vorgespulten Commit); die frischen #335-Tests zur Karte (`test_karte_*`, `test_art_uebersicht.py`, `seiten_karte.mjs`, `seiten_art_uebersicht.mjs`) sowie `test_tagesplan.py` und `test_tagesseite.py` bestehen ohne Abschwächung.
- [x] **AC-20 (Instanz-Tests, Nachweis im PR-Text):** Weil Meldungstexte und Konnektor-Schema sich ändern, laufen vor dem Vorspulen die Tests der einbindenden Instanzen mit dem Branch; Vergleichsbasis sind die 13 bekannten Fehler in main (ADR-0008, nicht von #353); es kommt kein neuer Fehler hinzu.

## Dialog

### Runde 1
**Adversary:** Behauptung: Orte sind Möglichkeiten einer Wahlstelle (Ziel ohne Rechenbedeutung). Ich gehe davon aus, dass die Umsetzung falsch ist, und prüfe zuerst Test, dann den Bestand.

Testlauf (Nachweis `adversary-test-output.txt`: 152 bestanden, 0 übersprungen, gezielt: test_option_orte, test_option_aufenthalte, test_texte, test_karte_auto, test_tagesplan, test_tagesseite; Volllauf `adversary-test-output-full.txt`: `-n auto`, 1563 bestanden, 0 fehlgeschlagen, 0 übersprungen). Grün allein beweist nichts: Die Testanpassungen und die Mahnregel sind der Angriffspunkt.

Angriff 1 (Mahnregel für ALLE Wahlstellen ohne `art:`): `merkmale_aus` bekommt `eigene_dinge`; damit ist `gefordert` für jede Möglichkeit mit Dingen einer Wahlstelle ohne `art:` eingeschränkt, auch ohne Orte.
Code reference: engine/routen.py:1427
Vergleichsbau mit dem Stand 9a468cd (eigener Arbeitsbaum im Scratchpad), dieselbe Beispielreise:
- Beispielreise ohne V-06 (nur `orte: null` kommt als neues Feld dazu): Wahlstellen und Warnungen sonst Byte für Byte gleich. Ebenso mit fünf gemischten Wahlstellen (Strecke/Aufenthalt, Unterkunft/Unterkunft, Strecke/Strecke, Aufenthalt/Aufenthalt, Unterkunft/Strecke): kein Unterschied.
- Abwandlung: Wahlstelle ohne `art:`, Möglichkeit a = Gasthof (U-03), Möglichkeit b = Pension (U-02). Vorher: V-96.a mahnt `geoeffnet` (Pflicht der Pension, weil a die Art der Wahlstelle trägt). Jetzt: `fehlt` leer. Das ist eine Verhaltensänderung bei Bestand ohne `orte:` (AC-16 wörtlich: "Ausgabe der Optionen und alle Werte gleich").
- Gegenargument: AC-7 verlangt, dass jede Möglichkeit nur die Pflicht ihrer eigenen Art mahnt; mit Ort (Art ort_am_weg) in der ersten Möglichkeit und Aufenthalt in der zweiten geht das nur, wenn auch die erste Möglichkeit eingeschränkt wird. Die Verallgemeinerung folgt also dem Geist von AC-7, steht aber weder in der Lösung der Spec noch im Changelog. Fund F001 (MEDIUM, AMBIGUOUS). Engere Lösung möglich: `eigene_dinge` nur, wenn die Möglichkeit selbst `orte` hat.
Die Schreibweise der Merkmale (`o_extra`) und `merkmale_aus` für Orte:
Code reference: engine/routen.py:1329
Code reference: engine/routen.py:1414

Angriff 2 (Testanpassungen gegen c2f78d9):
- test_option_orte.py AC-10: V-95 bekam `frage="F-01"`. Ursache ist eine offene Planungswahl ohne Frage (pruefung.routen.97), unabhängig von `orte`. Alle Behauptungen des Tests (Warnung, `ort` None, `wahl`) sind unverändert: nicht abgeschwächt.
- seiten_option_ort.mjs: Tabelle umschalten und Vergleich neu öffnen (WebKit lädt bei goto neu). Die Behauptungen am Ende (Links `#O-04`/`#O-06` im Block, Link in den Einzelheiten, keine Seitenfehler) sind unverändert; der Test klickt gezielter statt breiter. Nicht abgeschwächt. Schwach bleibt die Vorgabe der Spec selbst: `"#O-04" in links_einzelheiten or "#O-06" in ...` (oder statt und), aus dem RED-Commit.
- test_schreiben.py: V-07 statt V-04 (V-06 belegt jetzt die Beispielreise, V-04/V-05 der Tagesplan-Test), Folge der Spec (Changelog), keine Abschwächung. Der T-03-Text in test_tag_aendern enthält `wahl: [V-06]`: gleiche Folge.
- test_eine_seitenordnung.py: `T-03.wahl` wird entfernt, wo die Wahlstellen entfernt werden: nötig, sonst hinge der Tag an einer fehlenden Wahlstelle.
- test_option_aufenthalte.py: Anker-Zeile mit `wahl: [V-06]`, dazu `match="nur eines von"` auf `e.value.schluessel == "schreiben.option_aendern.5"`: laut Changelog vorgegeben, strenger, nicht schwächer.

Angriff 3 (Sortenregel, alle 32 Teilmengen der fünf Sorten durchgerechnet): gültig sind genau die leere Menge, jede einzelne Sorte und jede Teilmenge von strecken/aufenthalte/orte; `unterkuenfte` und `folge` mit jeder anderen Sorte ungültig. Auch ein Eintrag mit leerer Liste zählt nicht als Sorte.
Code reference: engine/schreiben.py:3567
Leeren: `option_aendern` mit `orte: []` setzt `inhalt["orte"] = []` und entfernt das Feld; das Zusammenführen prüft den Stand danach.
Code reference: engine/schreiben.py:3624
Code reference: engine/schreiben.py:2297
Code reference: engine/schreiben.py:1103
Nicht ausgenutzt, aber vorhanden (Bestand): `option_bauen.1` im Katalog nennt als Inhalt weiterhin nur "unterkuenfte, strecken oder folge" (LOW, F003).

Angriff 4 (Texte): `orte` fehlt als eindeutiges Wort in `_text_parameter` der Schnittstelle (nur die englischen Namen der Beschreibungen); die Beschreibung bleibt in englischer Fassung mit dem deutschen Wort, wie bei strecken und aufenthalte im Text. Alias `places` ist eingetragen und kollidiert mit nichts.
Code reference: engine/schnittstelle.py:98
Code reference: engine/texte_de.py:1123
Code reference: engine/texte_en.py:1122
Alle vier neuen und die geänderten Schlüssel stehen in beiden Sprachdateien (nur de und en vorhanden). Die Ausnahmelisten in test_texte.py sind nicht angefasst.

Angriff 5 (Stadtwochenende, AC-15): `daten.json` mit beiden Ständen gebaut und mit `cmp` verglichen: identisch (Byte für Byte). Das ist stärker als die Zeilenzahl im Test.

Angriff 6 (Ortsseite): Die Spec sagt "Ein Ort ohne Ortsseite zeigt nur den Namen", die Umsetzung verlinkt immer. Prüfung: Jeder Ort in `R.orte` hat eine Ortsseite (Seitenart "ort"), die Prüfung `option_ort` lässt nur vorhandene Orte zu. Der Fall "Ort ohne Seite" kann bei gültiger Reise nicht auftreten; es entsteht kein toter Link. Abweichung vom Wortlaut ohne Wirkung (LOW, F002). Zusätzlich setzt die Umsetzung die Ortszeile auch in die erste Spalte der Vergleichstabelle und in die Karten des Vergleichs (über die Spec hinaus); der Browser-Test zeigt keine Seitenfehler.
Code reference: engine/vorlage.html:2127
Code reference: engine/vorlage.html:2283
Code reference: engine/vorlage.html:2329

**Implementierer:** (nicht beteiligt; Kontextisolation)

### Runde 2
**Adversary:** Zweite Runde, tiefer an den übrigen Stellen. Früh-Einigkeits-Skepsis: Nach Runde 1 ist alles grün bis auf F001; ich prüfe deshalb jede Stelle einzeln und nicht über das Gesamtergebnis.

- AC-3 / Prüfung: unbekannter Ort ergibt genau einen Fehler `option_ort` mit Wahlstelle, Möglichkeit und Ort (Test test_unbekannter_ort_in_option_ist_ein_fehler grün).
Code reference: engine/routen.py:703
- AC-8 / Art der Wahlstelle: Reihenfolge der Dinge in einer Möglichkeit bleibt Unterkunft, Aufenthalt, Ort; ein Ort ohne Art zählt nicht. `arten_der_option` filtert Orte ohne Art über `x in self.arten`.
Code reference: engine/routen.py:1207
Code reference: engine/routen.py:1226
- AC-10 / Nacht: Die Warnung hängt an `not uids`, also nur wenn keine Möglichkeit eine Unterkunft hat. Gemischt (eine Möglichkeit mit Unterkunft, eine mit Ort) gibt es keine Warnung, wie die Spec "keine mit unterkuenfte". `warne` entfernt Doppelte, daher genau eine Meldung, auch wenn `nacht` mehrfach läuft. `ort` bleibt None.
Code reference: engine/routen.py:1548
- AC-11: Der Zweig der Nacht und `anschluss`/`tag_lauf` lesen `orte` nirgends (der Test vergleicht Tagesläufe mit und ohne `orte`).
- AC-6 / show: Orte mit Name und ID, Schema `OPTION_FELDER.orte` als Array von Strings.
Code reference: engine/konnektor.py:738
Code reference: engine/konnektor.py:2567
- AC-9 / Karte: `dinge_bezug` führt Orte in beiden Schleifen (aktiv: plan, sonst alternative); `orte_im_plan` nimmt nur Orte mit Stand ungleich "frei". Regionen bleiben über `regionen()` ohne Punkt, weil `ohne_punkt` sie getrennt abzieht. Einziger Verbraucher von `stand` außerhalb der Karte ist `bauen.karte_bauen` (`aid not in stand` nur für Aufenthalte): O-IDs in `stand` stören dort nicht.
Code reference: engine/karte.py:144
Code reference: engine/karte.py:159
Code reference: engine/karte.py:197
- AC-18 / `arten_ableiten`: Die Art eines Orts zählt nur, wenn sie in den abgeleiteten Arten steht (`oa if oa in arten`); eine nicht abgeleitete Ortsart (ort_am_weg) verdrängt keine Unterkunftsart. Beobachtung: Die Schleife läuft je Möglichkeit in Reihenfolge; steht der Ort mit abgeleiteter Art in der ersten und die Unterkunft in einer späteren Möglichkeit, gewinnt der Ort. Das entspricht `art_der_wahl` (erste Möglichkeit gewinnt), ist also konsistent.
Code reference: engine/neu.py:373
- AC-5: PLAIN_FELDER schreibt Listen ohne Anführungszeichen; Ablehnung unbekannter Orte über `id_liste(... "orte")` mit `roh["orte"]`; Änderung nur mit `orte` ist eine Änderung (`option_aendern.8` nur ohne Änderung).
- AC-12 / Kalender: kein Zugriff auf `orte` der Option in kalender.py (Test grün).
- AC-14: Beispielreise V-06, Pläne und Summen unverändert (Test grün; Vergleichsbau ohne V-06 stimmt mit dem Basisstand überein).
- AC-19: Volllauf `-n auto` 1563 bestanden, 0 übersprungen; #335-Tests und Tagesplan/Tagesseite im gezielten Lauf grün.
- AC-20: Nachgereicht vom Orchestrator nach dem Rebase auf origin/main: Instanz-Tests mit main und mit dem Branch, 13 gleiche bekannte Fehler, kein neuer (docs/artifacts/353-orte-als-moeglichkeit/instanz-tests.md).

Letzter Versuch, etwas zu brechen: Wahlstelle ohne `art:` mit Ort ohne Art als einziger Möglichkeit (AC-2): `eigene_dinge` wahr, `arten` leer, `gefordert` nur aus `wahl_eigene`, also keine Mahnung und keine Warnung; Text/Plus/Minus bleiben. Ort mit Art in Wahlstelle mit `art:`: `eigene_dinge` falsch, Verhalten wie bisher. Keine weiteren Brüche gefunden.

**Implementierer:** (nicht beteiligt; Kontextisolation)

## Findings

Finding:
  ID: F001
  Severity: MEDIUM
  Category: regression
  Code reference: engine/routen.py:1427
  Description: `eigene_dinge` schränkt `gefordert` für jede Möglichkeit mit Dingen in einer Wahlstelle ohne `art:` ein, nicht nur für Möglichkeiten mit `orte`.
  Spec requirement: AC-16 — Bestand ohne `orte:`: Ausgabe der Optionen und alle Werte gleich wie vorher (zugleich AC-7: jede Möglichkeit mahnt nur ihre eigene Art)
  Conflict: Wahlstelle ohne `art:`, Möglichkeit a = Gasthof (U-03), b = Pension (U-02): vorher `fehlt: [geoeffnet]` in a, jetzt leer. Vergleich mit Stand 9a468cd an der Beispielreise mit zwei zusätzlichen Wahlstellen. Betrifft nur Wahlstellen ohne `art:` mit gemischten Arten; nur weniger Mahnungen, keine zusätzlichen. Nicht in der Lösung der Spec genannt.
  Remediation: Entweder bewusst übernehmen (Changelog/Doku der Spec, Test mit Gasthof/Pension) oder `eigene_dinge` auf Möglichkeiten mit `orte` beschränken (AC-7 bleibt erfüllt, weil die Aufenthalt-Möglichkeit schon über `arten[0] != b` eingeschränkt wird).

Finding:
  ID: F002
  Severity: LOW
  Category: spec_violation
  Code reference: engine/vorlage.html:1259
  Description: `ortChips` verlinkt jeden Ort auf `#O-…`; die Spec nennt "Ort ohne Ortsseite zeigt nur den Namen".
  Spec requirement: AC-13 / Lösung vorlage.html — Ortszeile mit Link zur Ortsseite
  Conflict: Der Fall tritt bei gültiger Reise nicht auf (jeder geprüfte Ort hat eine Seite), daher keine Wirkung; Wortlaut weicht ab. Zusätzlich steht die Ortszeile in der Vergleichstabelle (erste Spalte) und in den Vergleichskarten, über die Spec hinaus.
  Remediation: Spec-Satz streichen oder präzisieren.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/texte_de.py:1603
  Description: `schreiben.option_bauen.1` nennt als Inhalt einer Option nur "unterkuenfte, strecken oder folge"; `aufenthalte` und `orte` fehlen (bei `aufenthalte` schon im Bestand).
  Spec requirement: AC-17 — geänderte Schlüssel nennen die Sorten richtig (Liste der Spec: option_bauen.2, option_aendern.5 und .8)
  Conflict: Nur Hinweistext, kein Verhalten; nicht in der Liste der Spec.
  Remediation: Beim nächsten Textdurchgang ergänzen.

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/routen.py:1329
  Evidence: `o_extra` gibt dem Ort die Kriterien der Wahlstelle; Test test_ort_als_option_wird_gelesen_und_verglichen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/routen.py:1427
  Evidence: Ort ohne Art: `arten` leer, keine Mahnung, keine Ortsmerkmale; Test grün; Runde 2.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/routen.py:703
  Evidence: genau ein Fehler `option_ort` mit vid, oid, ort.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/schreiben.py:3567
  Evidence: alle 32 Teilmengen der fünf Sorten durchgerechnet, genau die Regel der Spec.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/schreiben.py:3624
  Evidence: setzen, ersetzen, leeren über `inhalt`; Ablehnung `option_aendern.5`; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/konnektor.py:2567
  Evidence: `OPTION_FELDER.orte`, `show` Zeile mit Namen (konnektor.py:738); Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/routen.py:1414
  Evidence: Merkmale beider Arten in den Kriterien, jede Möglichkeit mahnt ihre eigene Art; mit Vorbehalt F001 zur Reichweite der Regel.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/routen.py:1207
  Evidence: erster Ort mit Art, Ort ohne Art zählt nicht; sonst allgemein.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/karte.py:197
  Evidence: Ort mit Stand ungleich frei kommt in die Menge; Regionen bleiben ausgenommen.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/routen.py:1548
  Evidence: Warnung nur ohne Unterkunft in allen Möglichkeiten, genau eine, `ort` None.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/routen.py:1909
  Evidence: `orte` nur im Ausgabefeld; Nacht, Anschluss, tag_lauf lesen es nicht.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/routen.py:1909
  Evidence: kalender.py liest `orte` der Option nirgends; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/vorlage.html:2283
  Evidence: Ortszeile in optionBlock (2283) und optionEinzelheiten (2329), Browser-Test grün ohne Seitenfehler; F002 zum Wortlaut.
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/routen.py:1909
  Evidence: Beispielreise mit V-06 (O-04 mit Art, O-06 ohne); Vergleichsbau ohne V-06 gleich dem Basisstand; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/routen.py:1909
  Evidence: `daten.json` des Stadtwochenendes mit Basisstand und neuem Stand per `cmp` identisch.
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/routen.py:1427
  Evidence: Beispielreise ohne V-06 und fünf gemischte Wahlstellen gleich dem Basisstand (nur `orte: null` neu); Ausnahme F001 (gemischte Unterkunftsarten ohne `art:`).
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: engine/texte_de.py:2698
  Evidence: vier neue Schlüssel in de (1123, 2147, 2698, 2699) und en (1122, 2146, 2697, 2698), geänderte Schlüssel nennen die Sorten; test_texte.py grün, Ausnahmelisten unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: engine/neu.py:373
  Evidence: Art des Orts nur, wenn abgeleitet; eine nicht abgeleitete Ortsart verdrängt keine Unterkunftsart; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: engine/karte.py:144
  Evidence: Volllauf mit -n auto: 1563 bestanden, 0 fehlgeschlagen, 0 übersprungen.
  Status: CONFIRMED

Confirmation:
  AC: AC-20
  Code reference: engine/schnittstelle.py:98
  Evidence: Instanz-Tests noch nicht gelaufen (Meldungstexte und Schema ändern sich); offen, kein Defekt. Status AMBIGUOUS bis der Nachweis im PR-Text steht.
  Status: AMBIGUOUS

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: AMBIGUOUS
═══════════════════════════════════════
Ambiguous findings (require human review):
  F001: Die Mahnregel ist für alle Wahlstellen ohne `art:` geändert (Bestand mit gemischten Unterkunftsarten mahnt weniger). Entweder durch AC-7 gedeckt oder Verstoß gegen AC-16; die Spec entscheidet es nicht.
  AC-20: Instanz-Tests stehen aus (offen, kein Defekt).

Proven points: 19/20 (AC-1 bis AC-19; AC-16 mit Ausnahme F001)
Tests: 1563 passed, 0 failed, 0 übersprungen (Volllauf); 152 passed, 0 failed, 0 übersprungen (gezielt)
Edge cases: geprüft, außer F001 nichts gebrochen; F002 und F003 niedrig
Regressions: F001 (nur weniger Mahnungen, Wahlstellen ohne art: mit gemischten Arten)
Checklist: 19/20 bewiesen, AC-20 offen
Recommendation: Entscheidung zu F001 (übernehmen und dokumentieren oder auf Möglichkeiten mit orte beschränken), AC-20 vor dem Vorspulen ausführen.

Nachtrag Orchestrator (2026-11-06): F001 vom Tech Lead übernommen und in Spec (Changelog) und docs/alternativen.md vermerkt; F003 als #364 erfasst; AC-20 nach Rebase auf origin/main belegt (instanz-tests.md, kein neuer Fehler). Verdict bleibt AMBIGUOUS, Weitergabe mit Freigabe des Product Owners (override-ambiguous).

## Geprüfte Dateien

- sha256:901941e2ac8f5ca69f6cc89db6b585c2ee1987e7040bc67c3a793c1cd97a322b  engine/karte.py
- sha256:949d2bab810722e188430b044a813b51816c3f745fb3d67b7fe9d39ec32bc82e  engine/konnektor.py
- sha256:57e9ca972f9605bbd333cc6abce578295e5b24706024cd67f1e7620e46ca3738  engine/neu.py
- sha256:582199551e537e988d7b8ba206905d4ebc7b758603d9a5ac5f4634e82d924627  engine/routen.py
- sha256:f84f0ed6b3c9c84609da493d48e5adf22d4a0cc9c16c1f63b97034fae0e673f9  engine/schnittstelle.py
- sha256:e28ca8d08be22a640d91c2598fc87ec3eba83520e61b955838354d930172746d  engine/schreiben.py
- sha256:5536f65fcbfaf2512cb62c6f84d107572161920bb89f16e12991fb99274bbfaa  engine/texte_de.py
- sha256:0ffa7d04f2991e5767876171527fd8b22216baa0fb755eb05eef59730817302b  engine/texte_en.py
- sha256:20c814a91b0a2138063a6606fb8610de18baa84042493dce33a158f93c948a7f  engine/vorlage.html

## Prüfbasis

- base: 7274cbd80abd99234ca60f8241d8f11cfa92d8d9
- blob:64c00a3a01dbc661149fe98cc79e3ce11a96e483  engine/karte.py
- blob:7ce99538f839056a1d0d88ff4dcd7d4398b7a737  engine/konnektor.py
- blob:fc277add56ba375f5afd0b6341b0c3922f281a8c  engine/neu.py
- blob:b75f0c8a35b8033e15dbf96235fb4b5cfb9e3dcf  engine/routen.py
- blob:73fa561113f8e16b13295b15ceb0567f70d298a0  engine/schnittstelle.py
- blob:933e69aa5ae89a61a13fd7d15373091e11dbb41e  engine/schreiben.py
- blob:8bb9ac6e6a61c0223c77056117ed5e3330d17032  engine/texte_de.py
- blob:37cec65137c17806bbb52a8dfe867fb9115da139  engine/texte_en.py
- blob:b3f84ba73d8c71250b963431f7af953c349f98f6  engine/vorlage.html
