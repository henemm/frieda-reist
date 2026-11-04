---
entity_id: kennzahlen-268
type: refactor
created: 2026-11-04
updated: 2026-11-04
status: draft
workflow: kennzahlen-268
issue: 268
---

# Kennzahlen an einer Stelle (#268, Teil 2 von #215)

Kontext und Analyse: [docs/context/kennzahlen-268.md](../../context/kennzahlen-268.md) (Abschnitt „Analysis“ ist verbindlich).
Vorbereitung für #269 (Etappe als Art der Reise).

## Purpose (Anlass)

Die Regeln für Kennzahlen (Gehzeit/Dauer, Länge, Aufstieg/Abstieg) und für das Merkmal `summiert` einer Art stehen heute an
mehreren Stellen: im Routenmodell (`engine/routen.py`, `summe`, `kennwerte`), auf der Seite (`tagKm`/`tagMin`, `REGEL.*`,
`summiertArt`, drei verschiedene Bedingungen für „hat Wanderdaten?“) und im Konnektor (`Handbuch.summe`). Die Stellen weichen ab:
„2 h“ und englische Schlüssel („Length“) zählen im Routenmodell, aber nicht in der Tageszeile; eine Strecke mit kombinierter Art
(`art: [wandern, bahn]`) zählt auf der Seite als summiert, in der Summe des Plans nicht. Nach dem Umbau rechnet nur das Routenmodell;
Seite und Konnektor zeigen das Ergebnis (ADR-0001: die Reise sagt mit `summiert`, was zählt; die Software rechnet es einmal).

## Scope

**In:**

- `engine/routen.py`: eine Rechenstelle `strecken_summe`; `kennzahlen` je Tag (für `R.tage` und jeden `p.tage`); `summe.mit_kennzahlen`;
  Höhenmeter-Text in `auto_werte` aus dem Katalog.
- `engine/vorlage.html`: `tagKm`/`tagMin` entfallen; „hat Kennzahlen“ nur über `s.mit_kennzahlen`; `summiert` nur über `st.summiert`;
  `↑ … m`/`↓ … m` über `T()`.
- `engine/konnektor.py`: `Handbuch.summe` über `mit_kennzahlen`; fehlende Angaben gekennzeichnet statt `0:00`.
- `engine/texte_de.py`, `engine/texte_en.py` (und jede weitere Sprachdatei, die der Katalog findet): neue Schlüssel.
- Tests und `docs/design.md`.

**Nicht in #268** (bleibt für #269):

- Zuordnung roher Kennzahl-Namen zu Kennungen (`REGEL.gehzeit/aufstieg/abstieg/laenge`, `kennzahlPaar`): bleibt auf der Seite.
- Dossier-Etappen (`bauen.py` 441, 1141–1150): unverändert; hier umgebaut, würde es mit „Etappe als Art“ noch einmal umgebaut.
- Rohe `kennzahlen` als Text in `konnektor.py` (Ausgabe von Strecken, ca. 753, 792): keine Rechnung, bleibt.
- Kein Format der Reisedaten ändert sich (nur abgeleitete Werte in `daten.json`) → keine Umstellung in `neu.py nachziehen`.
- `schreiben.py`, `waechter.py`, `karte.py`, `neu.py` unberührt.

## Prüfstelle ADR-0001 (zehn Fragen, kurz)

Beide Beispielreisen bauen unverändert grün und zeigen unveränderte Werte (Frage 1: Wanderung mit Pläne und Varianten, Städtewochenende
ohne Gehzeit). Es kommen weder Art-Namen noch Reisespezifisches in Engine oder Vorlage; die Regel hängt am Merkmal `summiert` der Art
aus `arten.yaml` (Arten gehören der Reise). Es entstehen keine neuen Grundformen und keine neue Form eines Merkmals. Es werden keine
Werte erfunden: fehlen Angaben, steht „Angaben fehlen“ statt einer Null. Sichtbare Texte stehen im Katalog in allen Sprachen
(ADR-0006). Instanzspezifisches kommt nicht vor. Ein Handschritt nach dem Software-Wechsel entsteht nicht. Keine KI in Frieda. Kein
Widerspruch zum Kern erkannt; kein Rückgriff auf den Product Owner nötig.

## Lösung

### `engine/routen.py`

- **`strecken_summe(strecken) -> {min, auf, ab, km, fehlend}`** (Methode von `Routen`): die innere Schleife aus `summe`
  (heute ab Zeile 1712: `self.strecke(...)`, Filter über `strecken_art(st)` und `summiert`, `kennwerte(...)`, Summen und `fehlend`).
  Genau hier gilt die Regel „kombinierte Art folgt `summiert` der Art `kombiniert`“. Rückgabe: Zahlen, `fehlend` als sortierte Liste.
  Zusätzlich liefert sie, ob mindestens eine summierte Strecke vorkam (`gezaehlt`, intern), woraus `mit_kennzahlen` folgt.
- **`summe(tage)`** (heute 1706) nutzt `strecken_summe` je Tag und addiert; `laengster` aus der Tagessumme `min`. Neu: `mit_kennzahlen`
  (bool) = in mindestens einem Tag zählte eine summierte Strecke. `min`, `auf`, `ab`, `km`, `fehlend`, `unvollstaendig` bleiben mit
  gleichen Werten.
- **Tag-Dict in `bauen()`**: neues Feld `kennzahlen: {min, km, auf, ab, fehlend, gezaehlt}`; Zahlen (nicht formatierte Texte). Da die
  Tage eines Plans in einem eigenen `Routen(..., zwang).bauen()`-Lauf entstehen, tragen `R.tage` und jeder `p.tage` die Werte ihrer
  eigenen Wahl. Keine Rechnung über globale Tag-IDs.
- **Strecken**: `summiert` je Strecke (heute in `strecke_aus`) bleibt die einzige Quelle für die Seite; Regel kombinierter Art wie in
  `strecken_summe` (eine gemeinsame Hilfe, kein zweiter Code).
- **`auto_werte`** (Zeile 1255, `hoehenmeter` Zeile 1267): fester Text `f"↑ {…} m, ↓ {…} m"` wird zu `self.t("seite.kennzahl.…")`-Aufruf mit
  dem neuen Katalogschlüssel (siehe unten); Verhalten und Bedingung (`auf` vorhanden, nicht `{"auf","ab"} & f`) bleiben.

### `engine/vorlage.html`

- `tagKm` (2244) und `tagMin` (2251) entfallen. Aufrufer (`tagZeile`, Tabellen der Pläne und Zeitachse) lesen `t.kennzahlen.min`/`.km`
  und formatieren mit `dauer`/`kmText` (Sprache der Hülle). Kein Muster `/^(länge|strecke|km)/` mehr auf der Seite für Tagessummen.
- `summeText` (1326), `steckbrief` (~2264) und `reiseKennzahlen` (2935) entscheiden über `s.mit_kennzahlen` statt `s.km`/`s.min||s.km||s.auf`.
  Fehlen bei `mit_kennzahlen` Angaben, zeigt die Seite die vorhandenen Texte `seite.steckbrief.angaben_fehlen` und `seite.summe.unvollstaendig`.
- `summiertArt` (1273), `streckeZeile` (~1410) und Wegverlauf (~1476) lesen nur `st.summiert` der Strecke. Aufrufer mit Ersatzobjekt
  (`|| {}`, `|| {titel: id}`) ergeben wie heute „nicht summiert“. Die Kartenlegende (~2835) filtert Arten und bleibt auf Art-Ebene
  (`R.arten`, reine Darstellung).
- `kennzahlPaar` (1337): `↑ ${v} m`/`↓ ${v} m` über `T("seite.kennzahl.hoehe_auf", …)`/`…_ab` (neue Schlüssel, siehe unten).
  `REGEL.*` bleibt (Nicht-Scope).

### `engine/konnektor.py`

`Handbuch.summe` (664–673; Aufrufer 735, 862, 1190) entscheidet über `s["mit_kennzahlen"]` statt `s.get("min")`. Ist `unvollstaendig`
(Angaben fehlen), steht an der Stelle der Gehzeit/des Werts ein Katalogtext („Angaben fehlen“) statt `0:00`.

### Texte (`engine/texte_<sprache>.py`, alle Sprachen)

Neue Schlüssel (Namen für die Umsetzung, Muster der Datei; genaue Ablage im Katalog nach den Regeln aus `docs/sprachen.md`):

- `seite.kennzahl.hoehe_auf` und `seite.kennzahl.hoehe_ab` (de: `↑ {v} m`, `↓ {v} m`; en dasselbe mit „m“).
- `routen.auto.hoehenmeter` (de: `↑ {auf} m, ↓ {ab} m`; en gleich) für `auto_werte`; Wiederverwendung von `seite.kennzahl.auf_ab` ist nicht
  möglich (anderes Muster „Hm“), daher eigener Schlüssel.
- `konnektor.summe.angaben_fehlen` (de: „Gehzeit, Höhenmeter und Länge: Angaben fehlen“; en sinngemäß).
- Ausnahmelisten in `engine/tests/test_texte.py` dürfen nicht länger werden.

## Source

- **Datei:** `engine/routen.py` — **Identifier:** `Routen.summe`, `Routen.option_summe`, `Routen.auto_werte`, `kennwerte`, `Routen.bauen` (Tag-Dict), neu `Routen.strecken_summe`
- **Datei:** `engine/vorlage.html` — **Identifier:** `tagKm`, `tagMin`, `summeText`, `steckbrief`, `reiseKennzahlen`, `summiertArt`, `streckeZeile`, `kennzahlPaar`
- **Datei:** `engine/konnektor.py` — **Identifier:** `Handbuch.summe`

## Betroffene Dateien

| Datei | Änderung |
|---|---|
| `engine/routen.py` | MODIFY: `strecken_summe`, `kennzahlen` je Tag, `summe.mit_kennzahlen`, Höhenmeter-Text aus Katalog |
| `engine/vorlage.html` | MODIFY: `tagKm`/`tagMin` weg; Entscheidungen über `mit_kennzahlen` und `st.summiert`; `↑/↓ m` über `T()` |
| `engine/konnektor.py` | MODIFY: `Handbuch.summe` über `mit_kennzahlen`, fehlende Angaben gekennzeichnet |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY: drei bis vier neue Schlüssel |
| `engine/tests/test_routen.py` | MODIFY: Tageswerte, `mit_kennzahlen`, kombinierte Art |
| `engine/tests/test_texte.py` | MODIFY: `Handbuch.summe` mit/ohne Angaben, neue Schlüssel in allen Sprachen |
| `engine/tests/test_design.py` | MODIFY: Quelltext-Prüfung, dass die Vorlage keine eigene Tagessumme mehr rechnet |
| `engine/tests/test_bauen.py` | MODIFY: Tageswerte je Plan der Beispielreise |
| Browser-Test `engine/tests/test_eine_seitenordnung.py` | MODIFY: Tageszeile beider Beispielreisen |
| `docs/design.md` | MODIFY: Regel ergänzen (Zeilen ca. 13, 75, 85, 178) |

### Estimated Changes

- Dateien: ca. 10 (3 Code, 2 Texte, Tests, Doku)
- LoC: +120/−50 (Code ca. +55/−45, Tests ca. +60)
- Risiko: MITTEL (Routenmodell und Vorlage zentral; sichtbare Werte der Beispiele bleiben gleich)

## Dependencies

| Abhängigkeit | Richtung | Bemerkung |
|---|---|---|
| `plan/arten.yaml` (`summiert`), `routen.yaml` (rohe `kennzahlen`) | upstream | unverändert |
| `routen.kennwerte`, `texte.inhaltswoerter` (`inhalt.kennzahl.*`) | upstream | die eine Erkennung der Schlüssel, unverändert |
| `bauen.py` (`D.route`) | downstream | reicht die neuen Felder in `daten.json` weiter |
| Vorlage, Konnektor, Browser-Tests | downstream | lesen nur das Ergebnis |
| Instanz-Tests im Reisen-Repo | downstream | `daten.json` bekommt neue Felder (CLAUDE.md: Tests der Instanzen mit dem Branch vor dem Vorspulen) |
| #269 (Etappe als Art) | später | baut auf der einen Stelle auf; kein Etappen-Sonderfall |

## Acceptance Criteria

Alle prüfbar durch Tests oder die genannten Befehle; ohne echte Reisen.

- **AC-1 (Beispielwanderung unverändert):** Given `beispiel/reisen/beispielreise`, when sie baut, then zeigt die Reise die Summe 595 min,
  25,4 km, ↑1075, ↓1025 (`fehlend` leer, `mit_kennzahlen` wahr), die Pläne P-A 610 min und P-B 595 min; je Plan ist die Summe der
  `kennzahlen.min` aller Tage in `p.tage` gleich `p.summe.min`, und für die Reise gilt dasselbe für `R.tage` und `R.summe`.
- **AC-2 (Stadtwochenende):** Given `beispiel/reisen/stadtwochenende` (keine summierte Strecke), when sie baut, then ist
  `summe.mit_kennzahlen` falsch, jeder Tag hat `kennzahlen` mit Nullwerten ohne `fehlend`, und die gebaute Seite zeigt weder Gehzeit noch
  km noch Höhenmeter noch „Angaben fehlen“ (Browser- oder Seitentest).
- **AC-3 (Zeiten und Schlüssel):** Given eine Wanderstrecke mit Kennzahlen „2 h“ (statt `h:mm`) und der englische Schlüssel „Length“
  (statt „Länge“), when der Bau läuft, then zählen beide in `tag.kennzahlen` (2 h = 120 min; „Length“ = km) und die Seite zeigt sie in der
  Tageszeile.
- **AC-4 (kombinierte Art):** Given eine Strecke mit `art: [wandern, bahn]` (nur eine Art summiert), when der Bau läuft, then gilt
  dieselbe Regel in `summe`, in `tag.kennzahlen` und in `strecke.summiert`; Seite (Linienstil, Gehzeit/Dauer, Etappenkarte,
  `streckeZeile`, Wegverlauf) liest nur `strecke.summiert`; ein Test mit beiden Seiten (Summe und Anzeige) widerspricht sich nicht.
- **AC-5 (Angaben fehlen statt Null):** Given eine summierte Strecke ohne Kennzahlen, when der Bau läuft, then ist `mit_kennzahlen`
  wahr, `fehlend` nennt die Felder, und Seite (Steckbrief/Reiseüberblick) und Konnektor (`Handbuch.summe`) zeigen „Angaben fehlen“
  (Katalogtext) statt nichts oder `0:00`.
- **AC-6 (nur eine Stelle):** Given der Quelltext von `engine/vorlage.html`, then enthält er weder `tagKm` noch `tagMin` und keine
  Bedingung `s.min || s.km || s.auf`; `steckbrief`, `summeText`, `reiseKennzahlen` und `Handbuch.summe` lesen `mit_kennzahlen`;
  `summiertArt`, `streckeZeile` und Wegverlauf enthalten kein `artDef(…).summiert`. Die Kartenlegende bleibt auf Art-Ebene.
- **AC-7 (keine festen Texte):** Given `routen.py` und `vorlage.html`, then enthalten sie kein festes `↑ … m, ↓ … m` und kein
  `↑ ${v} m`; die Texte kommen aus dem Katalog; die neuen Schlüssel stehen in allen Sprachen, `engine/tests/test_texte.py` ist grün und
  die Ausnahmelisten sind nicht länger geworden.
- **AC-8 (Sprache der Hülle):** Given Beispielreise in Pseudo-Sprache/Englisch, when die Seite die Tageszeile und Höhenmeter zeigt,
  then stehen die Texte in der Sprache der Hülle, Zahlen über `dauer`/`kmText` formatiert (bestehende Tests `test_seite_sprachen.py`
  bleiben grün).
- **AC-9 (Plan-Tage):** Given eine Reise mit zwei Plänen, deren Tage verschiedene Wahlen tragen, when der Bau läuft, then
  trägt jeder `p.tage[i].kennzahlen` die Werte seiner eigenen Wahl; ein Wechsel der Wahl in der Seite ändert keine Tagessumme außerhalb
  des Plans.
- **AC-10 (Konnektor):** Given eine Summe mit `mit_kennzahlen` falsch, when `Handbuch.summe` formatiert, then steht keine Gehzeit-Zeile;
  given `mit_kennzahlen` wahr und vollständig, then steht dieselbe Zeile wie heute (gleiche Werte wie `konnektor.summe.gehzeit`).
- **AC-11 (Gesamtlauf):** `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen (CI auf dem vorgespulten Commit).
- **AC-12 (Instanz-Tests, Nachweis im PR-Text):** Weil `daten.json` neue Felder bekommt, laufen vor dem Vorspulen die Tests der
  einbindenden Instanzen mit dem Branch und sind grün; der Probebau aller echten Reisen mit dem Branch ist grün (lesend).

## Test Plan (Geplante Tests)

| Datei | Test (Skizze) | Prüft |
|---|---|---|
| `engine/tests/test_routen.py` | `test_strecken_summe_zaehlt_nur_summierte_arten` | AC-4, Bus zählt nicht |
| `engine/tests/test_routen.py` | `test_tag_kennzahlen_2h_und_length_zaehlen` | AC-3 |
| `engine/tests/test_routen.py` | `test_tag_kennzahlen_summe_gleich_summe_der_tage` | AC-1, beide Reisen (parametrisiert) |
| `engine/tests/test_routen.py` | `test_mit_kennzahlen_wanderung_wahr_stadtwochenende_falsch` | AC-1, AC-2 |
| `engine/tests/test_routen.py` | `test_kombinierte_art_summe_tag_und_strecke_gleich` | AC-4 |
| `engine/tests/test_routen.py` | `test_summierte_strecke_ohne_angaben_fehlend_und_mit_kennzahlen` | AC-5 |
| `engine/tests/test_bauen.py` | `test_plan_tage_tragen_eigene_kennzahlen` | AC-9; P-A 610, P-B 595 |
| `engine/tests/test_texte.py` | `test_handbuch_summe_mit_und_ohne_kennzahlen`, `test_handbuch_summe_angaben_fehlen` | AC-5, AC-10 |
| `engine/tests/test_texte.py` | bestehende Schlüssel-/Sprachprüfungen | AC-7 |
| `engine/tests/test_design.py` | `test_vorlage_ohne_eigene_tagessumme_und_summiert_nur_von_strecke` | AC-6, AC-7 (Quelltext) |
| `engine/tests/test_eine_seitenordnung.py` (Browser) | Tageszeile Wanderung unverändert; Stadtwochenende ohne Gehzeit/km | AC-1, AC-2, AC-8 |

GIVEN/WHEN/THEN: z. B. GIVEN eine Strecke `kennzahlen: {Length: "8 km", Dauer: "2 h"}` an einer summierten Art, WHEN `bauen()` läuft, THEN
ist `tag.kennzahlen == {min: 120, km: 8.0, …}`. GIVEN das Stadtwochenende, WHEN die Seite gebaut wird, THEN enthält die Tageszeile
weder Gehzeit noch km. Testdaten: nur erfundene Daten und die beiden Beispielreisen.

## Risiken

- **Ausgabeformat ändert sich** (neue Felder je Tag): Instanz-Tests der einbindenden Reisen mit dem Branch (AC-12).
- **Sichtbare Abweichungen in echten Reisen:** „2 h“, englische Schlüssel, kombinierte Art und „summierte Strecke ohne Angaben“ können
  dort erstmals Werte oder „Angaben fehlen“ zeigen, wo vorher nichts stand. An den Beispielen keine Änderung; der Probebau der echten
  Reisen (lesend) zeigt es vorher.
- **`vorlage.html` groß und viel getestet** (WebKit): Änderungen klein halten, Browser-Tests der Tageszeile ausführen.
- **Doppelte Erkennung bleibt vorübergehend** (`REGEL.*`/`kennzahlPaar`): bewusst, #269.
- **Konnektor-Text ändert sich** bei fehlenden Angaben (bisher `0:00`): gewollt, AC-5.

## Dokumentation

`docs/design.md`: Regel ergänzen „Kennzahlen rechnet das Routenmodell, die Seite zeigt sie: Summe, Tageswerte und `summiert` kommen aus
`routen.py`; Seite und Konnektor lesen `summe.mit_kennzahlen`, `tag.kennzahlen` und `strecke.summiert`“; Abschnitte Kennzahlenleiste
(Z. 13), „ein Wert steht einmal“ (Z. 75), Kennzahlen mit/ohne Wanderdaten (Z. 85, 178) angleichen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Keine neue Architekturentscheidung: Das Muster „die Seite zeigt fertige Werte aus `routen.py`“ (Kommentar zu `summe`, `arten.kosten`,
  `eltern`) wird auf die Kennzahlen ausgeweitet; Messung am Kern nach [ADR-0001](../../adr/0001-kern.md) siehe oben, Texte nach
  [ADR-0006](../../adr/0006-mehrsprachigkeit.md).

## Definition of Done

- [ ] AC-1 bis AC-10 durch automatische Tests belegt, AC-11 grün
- [ ] AC-12 im PR-Text belegt
- [ ] CI grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Commit auf `main` vorgespult
- [ ] Kommentar in #268 und #215 mit Stand; #269 weiß, was bleibt (Namenszuordnung, Dossier-Etappen)

## Changelog

- 2026-11-04: Initial spec created (kennzahlen-268).

## Approval

- [ ] Approved
