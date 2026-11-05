---
entity_id: etappe-als-art-269
type: refactor
created: 2026-11-04
updated: 2026-11-04
status: draft
version: "1.0"
workflow: etappe-als-art-269
tags: [etappe, strecke, art, kennzahlen, routen, dossier, nachziehen]
test_targets: [engine/bauen.py, engine/routen.py, engine/vorlage.html, engine/neu.py, engine/tests/test_etappe_als_art.py, engine/tests/test_neu.py, engine/tests/test_bauen.py]
---

# Etappe als Art der Reise, nicht als Typ der Software (#269)

Workflow: `etappe-als-art-269`. Analyse: `docs/context/etappe-als-art-269.md`. Teil von #215 (Schuld Punkt 1). Verwandt: #268 (gleiche Dateien, muss zuerst auf `main`).

## GitHub Issue

**Issue:** #269 (Oberthema #215; Hinweis zu `tagZeile` aus #268)

## Approval

- [ ] Approved

Vorab entschieden: Die zwei Grundentscheidungen hat der Product Owner am 4.11.2026 getroffen (Abschnitt „Entscheidungen des Product Owners“). Die Spec selbst ist noch nicht freigegeben.

## Purpose

Die Software kennt heute „Etappe“ als festen Abschnittstyp (`typ === "etappe"`): Das Etappen-Dossier in Markdown legt über die feste Überschrift „Etappe N: Name“ Titel, ID und Kennzahlen fest, daneben stehen die Strecken in `plan/routen.yaml`. Die Kennzahlen werden dazu zweimal nach Namen sortiert (im Browser in `REGEL.*`/`kennzahlPaar`, in Python in `kennwerte()`). Nach dieser Spec ist eine Etappe eine **Strecke einer Art mit `summiert: true`**; Titel, Art und Kennzahlen stehen an der Strecke `E-…` in `routen.yaml`, das Dossier liefert nur Lesetext und Ebenen. Die Zuordnung der Kennzahlen zu Kennungen geschieht genau einmal, in Python.

## Source

- **File:** `engine/bauen.py`, `engine/routen.py`, `engine/vorlage.html`, `engine/neu.py`
- **Identifier:** `Bauen.daten()` (Etappen-Dossier, Z. 419–442), `Bauen.kennzahlen()` (Z. 1141), `routen.kennwerte()` (Z. 417), `Routen.strecke()` (Z. 541), `REGEL.gehzeit/aufstieg/abstieg/laenge`, `kennzahlPaar`, `kennzahlLeiste`, 22 Stellen `typ === "etappe"`, `neu.nachziehen()`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| #268 | Issue/PR | Ändert `routen.py`, `vorlage.html`, `konnektor.py`. **Muss vor jeder Änderung an diesen Dateien auf `main` sein**; #269 setzt danach auf `main` auf |
| `docs/adr/0001-kern.md` | ADR | Prüfstelle, unten beantwortet |
| `docs/adr/0003-heimat.md` | ADR | Heimat der Bewegung bleibt; keine zweite Darstellung |
| `docs/adr/0007-elternbezug.md`, `docs/ontologie.md` | ADR/Doku | Grundform `bewegung`, Artfeld `summiert` |
| `plan/arten.yaml` (Art-Feld `summiert`) | Reisedaten | Entscheidet, was „Etappe“ heißt (heute Art `wandern`) |
| `engine/texte_de.py`, `engine/texte_en.py`, alle `engine/texte_*.py` | Textkatalog | Wort „Etappe“, Kennzahlnamen, neue Meldungen |
| `engine/schreiben.py` | Schreibweg | Liest `etappen_*`-Einstellungen; Strecken-Schreiben bekommt `kennzahlen` |
| `beispiel/reisen/beispielreise` | Beispielreise | Dossier plus `etappen_kennzahlen`; Hauptprüfling der Umstellung |
| `beispiel/reisen/stadtwochenende` | Beispielreise | Ohne Etappen; darf sich nicht ändern (Frage 1 der Prüfstelle) |
| `<Reise A>` (echte Reise mit Etappen-Dossier) | private Reise | Wird nur durch `neu.py nachziehen` im Reisen-Repo umgestellt, hier nicht genannt |

## Scope

### Im Scope

1. **Datenformat:** Strecke in `routen.yaml` trägt `titel`, `art` und `kennzahlen` mit festen Kennungen (siehe Implementation Details).
2. **Dossier:** Die Überschrift „Etappe N: Name“ ist keine Regel mehr. Ein Dossier-Abschnitt gehört zu einer Strecke, wenn seine Überschrift die ID trägt (z. B. `E-03`), nicht über `etappen_muster`. Er liefert nur `intro`, Blöcke und Ebenen.
3. **`routen.py`** liefert je Strecke fertige Kennzahlen mit Kennung; `kennwerte()` sortiert nicht mehr nach Namen, es liest Kennungen.
4. **Seite:** `REGEL.gehzeit/aufstieg/abstieg/laenge`, `kennzahlPaar` und die Namenssuche an `st.kennzahlen` (Tagesminuten) entfallen. Die Seite zeigt fertige Paare.
5. **`typ === "etappe"`** (22 Stellen) wird durch „Strecke, deren Art `summiert: true` hat“ ersetzt (ein Prädikat, einmal definiert, aus `R.arten`).
6. **Reiter „Etappen“** zeigt alle Strecken mit summierter Art; das Wort „Etappe“ bleibt festes Oberflächenwort im Textkatalog.
7. **`daten()`** wird aufgeteilt (Dossier-Lesetext / Orte / Route), `kennzahlen()` und `etappen_muster` entfallen.
8. **Migration** `neu.py nachziehen`: Titel und Kennzahlen aus dem Dossier einmal in die Strecken, danach entfallen `etappen_kennzahlen` und `etappen_muster` aus `reise.json`.
9. **`tagZeile` (Hinweis aus #268):** Hat ein Tag eine summierte Strecke, aber ohne Gehzeit, steht dort „Angaben fehlen“ statt einer leeren Zeile (Text im Katalog). Entscheidung: **im Scope**, weil nach dem Umbau Kennzahlen fehlen dürfen und die Seite sie nicht mehr aus Namen erraten kann; das Erkennen ist ein Einzeiler am neuen Prädikat.
10. Tests, Texte, Doku (`docs/design.md`, Kopfkommentar der Vorlage, `docs/ontologie.md`).

### Nicht im Scope

- **`lesetext_schreiben` ohne Dossier** (heute Ablehnung „kein Etappen-Dossier“): eigenes Folge-Issue.
- **Echte Reisen:** keine Inhalte; sie werden nur über `nachziehen` im Reisen-Repo umgestellt.
- **Neue Arten oder Merkmale**, Änderungen am Karten- oder Buchungsmodell.
- **Alles, was #268 gehört** (siehe Dependencies).
- Eine eigene Eingabemaske für Kennzahlen im Konnektor über das hinaus, was `item_update` an Strecken schon kann.

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/bauen.py | MODIFY | `daten()` aufteilen; Dossier-Abschnitte per ID statt „Etappe N: Name“; `kennzahlen()`/`etappen_muster` entfallen; Meldung bei unbekannter ID |
| engine/routen.py | MODIFY | Kennzahlen je Strecke fertig mit Kennung; `kennwerte()` liest Kennungen; `strecke()` ohne Dossier-Sonderfall (erst nach #268) |
| engine/vorlage.html | MODIFY | `REGEL.gehzeit/aufstieg/abstieg/laenge`, `kennzahlPaar` entfernen; 22 Stellen `typ === "etappe"` durch ein Prädikat; `tagZeile` „Angaben fehlen“; Kopfkommentar (erst nach #268) |
| engine/neu.py | MODIFY | `nachziehen`: Dossier-Titel/-Kennzahlen in Strecken, Aufräumen von `reise.json`; Test |
| engine/schreiben.py | MODIFY | Strecken-Kennzahlen schreiben und prüfen; `etappen_*`-Einstellungen nicht mehr nötig |
| engine/texte_de.py, texte_en.py, weitere texte_*.py | MODIFY | Meldungen, „Angaben fehlen“; Ausnahmelisten in `test_texte.py` nur kürzer |
| beispiel/reisen/beispielreise/plan/routen.yaml, reise.json, inhalt/etappen.md | MODIFY | Auf neues Format (durch `nachziehen` erzeugt, nicht von Hand) |
| engine/tests/test_etappe_als_art.py | CREATE | Neue Tests |
| engine/tests/test_bauen.py, test_neu.py, test_routen.py, test_schreiben.py | MODIFY | Auf neues Format umstellen |
| docs/design.md, docs/ontologie.md, docs/konnektor.md, CLAUDE.md | MODIFY | „Etappe“ = Strecke summierter Art; Aufbau-Zeile nur, falls `etappen_*` genannt |

### Estimated Changes

- Files: 14 bis 16
- LoC: +300/−350 (grob)

## Implementation Details

### Datenformat vorher / nachher

Vorher: `routen.yaml` kennt `E-01: {von, nach, art: wandern, quelle}` ohne Titel und Kennzahlen; Titel „Etappe 1: Stadt Wehlen → Hohnstein“ und die Eckdaten-Tabelle stehen im Dossier (`inhalt/etappen.md`); `reise.json` nennt `etappen_kennzahlen` (Namen wie „Gehzeit“, „Aufstieg (Hm)“) und `etappen_muster`.

Nachher: `E-01: {titel: "Stadt Wehlen → Hohnstein", von, nach, art: wandern, kennzahlen: {gehzeit: "3:30", aufstieg: 380, abstieg: 220, laenge: 11.5}, quelle: …}`. Kennungen: `gehzeit`, `aufstieg`, `abstieg`, `laenge` (die Schlüssel der Kennzahlen der Seite, nicht deutsche Anzeigenamen); Zahlen bleiben Zahlen, die Gehzeit Text im Format `h:mm` (festgelegt; `minuten()` liest es, abweichende Schreibweisen im Bestand übernimmt `nachziehen` unverändert). Eigene, unbekannte Kennzahlen der Reise bleiben unter ihrem Namen erlaubt und werden unverändert angezeigt. Das Dossier-Markdown behält Überschrift und Blöcke; die Überschrift trägt die ID (festgelegt: `## E-01 Stadt Wehlen → Hohnstein`, ID als erstes Wort der Überschrift). „Etappe 1“ als Nummer entfällt; die Reihenfolge ergibt sich aus Tag und Strecke.

### Ablauf

1. `routen.py` normalisiert beim Laden einmal: `kennzahlen` je Strecke als Mapping Kennung → Wert; liefert `R.strecken[].kennzahlen` fertig (Kennung, Wert, Einheit-Text aus dem Katalog) an die Seite. Summen (`kennwerte()`) lesen dieselben Kennungen.
2. `bauen.py` liest das Dossier nur noch als Text zu Strecken-IDs; Abschnitt ohne bekannte Strecke wird gemeldet (Nummer im Katalog), nicht still ignoriert.
3. Die Seite kennt ein Prädikat `summiert(strecke)` (Art laut `R.arten`), keine Namen.
4. `neu.py nachziehen` ist idempotent und verändert Reisen ohne Dossier nicht (`stadtwochenende`).

## Entscheidungen des Product Owners

- [x] **Dossier (4.11.2026):** Etappen leben in `plan/routen.yaml` (Titel, Art, Kennzahlen an der Strecke `E-…`). Das Dossier bleibt nur als Markdown für Lesetext und Ebenen, verknüpft über die ID; die feste Regel „Etappe N: Name“ entfällt. `nachziehen` zieht Titel und Kennzahlen einmal um (Beispielreise und die private Reise).
- [x] **Wort „Etappe“ (4.11.2026):** bleibt festes Wort der Oberfläche (Textkatalog, alle Sprachen). Der Reiter „Etappen“ zeigt alle Strecken, deren Art `summiert: true` hat. Die Reise nennt ihre Art frei.

## Test Plan

### Automated Tests (TDD RED)

Neue Datei `engine/tests/test_etappe_als_art.py`, Umstellungen in den bestehenden Dateien. Jeder Test läuft gegen beide Beispielreisen, wo es Sinn ergibt.

- [ ] Test 1: GIVEN Beispielreise mit neuem Format WHEN gebaut THEN hat jede Strecke der Art `wandern` Titel und Kennzahlen mit den Kennungen `gehzeit`, `aufstieg`, `abstieg`, `laenge`, und weder die Dossier-Daten (`daten()`) noch das Routenmodell enthalten einen Abschnitt mit `typ == "etappe"`.
- [ ] Test 2: GIVEN Beispielreise im alten Format (Dossier mit „Etappe N: Name“, `etappen_kennzahlen`) WHEN `nachziehen` THEN stehen Titel und Kennzahlen an `E-01…E-04` in `routen.yaml`, `reise.json` hat weder `etappen_kennzahlen` noch `etappen_muster`, und ein zweiter Lauf ändert nichts.
- [ ] Test 3: GIVEN `stadtwochenende` (ohne Etappen) WHEN gebaut und `nachziehen` THEN Seite und Dateien unverändert, kein Reiter „Etappen“, keine Fehlermeldung.
- [ ] Test 4: GIVEN eine Reise, in der eine andere Art `summiert: true` hat (kopierte Beispielreise, Art umbenannt in „spaziergang“) WHEN gebaut THEN zeigt der Reiter „Etappen“ genau diese Strecken, und eine Strecke der Art `bahn` (nicht summiert) erscheint dort nicht.
- [ ] Test 5: GIVEN die Seite WHEN der Quelltext von `engine/vorlage.html` gelesen wird THEN enthält er weder `REGEL.gehzeit`, `REGEL.aufstieg`, `REGEL.abstieg`, `REGEL.laenge`, `kennzahlPaar` noch `typ === "etappe"`.
- [ ] Test 6: GIVEN Python `kennwerte()` WHEN Kennzahlen mit Kennungen übergeben THEN stimmen Minuten, Auf- und Abstieg und Kilometer; Namen in Landessprache werden nicht mehr gesucht.
- [ ] Test 7: GIVEN ein Dossier-Abschnitt, dessen ID keine Strecke ist WHEN gebaut THEN bricht der Bau mit einer Meldung aus dem Textkatalog (nicht still).
- [ ] Test 8: GIVEN ein Tag mit summierter Strecke ohne `gehzeit` WHEN die Tagesseite gebaut wird THEN steht „Angaben fehlen“ (Katalogtext, in allen Sprachen vorhanden).
- [ ] Test 9: GIVEN Textkatalog WHEN `test_texte.py` läuft THEN sind alle neuen Schlüssel in jeder Sprache da und die Ausnahmelisten nicht länger.
- [ ] Test 10: GIVEN Browser-Rundgang (`engine/tests/seiten_browser.mjs`, gegen Werte aus dem Bau vor der Umstellung) WHEN Beispielreise geöffnet THEN zeigen Etappenseite, Tagesseite und Karte dieselben Kennzahlen wie vor der Umstellung (Vergleich der Werte aus dem alten Bau).

## Acceptance Criteria

- **AC-1:** (Test 1, 10): Die Seite der Beispielreise zeigt Etappenseiten, Tagesseiten, Kennzahlen und Karte inhaltlich wie vorher (Werte gleich, Reihenfolge gleich).
- **AC-2:** (Test 5): `grep` auf `REGEL.gehzeit`, `kennzahlPaar`, `typ === "etappe"`, `etappen_muster` in `engine/` (außer `neu.py nachziehen` und Tests der Umstellung) findet nichts.
- **AC-3:** (alle Tests): `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün (beide Beispielreisen, auch `stadtwochenende` ohne Etappen).
- **AC-4:** (Test 2, 3): `neu.py nachziehen` stellt die Beispielreise ohne Handschritt um, ist idempotent und lässt Reisen ohne Dossier unberührt.
- **AC-5:** (Test 4): Eine Reise mit anderer summierter Art (nicht `wandern`) bekommt ihre Etappen im Reiter „Etappen“, ohne dass Code den Artnamen kennt.
- **AC-6:** (Test 9): Das Wort „Etappe“ steht nur im Textkatalog (alle Sprachen); `test_texte.py` bleibt grün.
- **AC-7:** (Test 8): Tag mit summierter Strecke ohne Angaben zeigt „Angaben fehlen“.
- **AC-8:** (Prozess, kein Test): Umsetzung beginnt erst, wenn #268 auf `main` ist (vor dem ersten Edit an `routen.py`/`vorlage.html` geprüft); der Branch setzt auf diesen Stand auf.

## Definition of Done

- [ ] Alle Acceptance Criteria K1–K8 sind durch die genannten Tests oder Prüfungen belegt.
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests` ist grün, ohne echte Reisen.
- [ ] `grep` nach `REGEL.gehzeit`, `kennzahlPaar`, `typ === "etappe"`, `etappen_muster` in `engine/` ohne Treffer (außer `nachziehen` und dessen Tests).
- [ ] `neu.py nachziehen` ist idempotent, getestet an beiden Beispielreisen.
- [ ] Browser-Rundgang über Beispielreise, `stadtwochenende` und eine frische Reise aus `engine/reisevorlage` ist grün.
- [ ] Tests der einbindenden Instanzen laufen mit dem Branch grün, bevor vorgespult wird.
- [ ] Doku (`docs/design.md`, `docs/ontologie.md`, `docs/konnektor.md`, Kopfkommentar der Vorlage) ist nachgetragen.

## Prüfstelle ADR-0001

Kurzfassung (die zehn Fragen werden im PR mit dem Template beantwortet):

- **Frage 1 (zwei Reisetypen):** `beispielreise` mit Etappen und `stadtwochenende` ohne; beide in den Tests.
- **Kern:** Die Software kennt nur die Grundform `bewegung` und das Artfeld `summiert`; „Etappe“ als Typ der Software entfällt. Das Wort „Etappe“ ist ein Oberflächenwort, keine Ontologie-Art.
- **Nichts Reisespezifisches in der Engine:** Kennzahlnamen („Aufstieg (Hm)“) gehören der Reise und wandern beim Umstellen in Kennungen; unbekannte bleiben erlaubt.
- **Nichts Instanzspezifisches:** keine Pfade oder Namen echter Reisen.

## Risiken

- **Mittel bis hoch:** zentrale Seitenlogik an 22 Stellen. Gegenmittel: ein Prädikat, Wertevergleich vor/nach (Test 10), beide Beispielreisen.
- **Formatwechsel:** Eine private Reise mit Dossier muss im selben Commit wie der neue Software-Stand umgestellt werden (Workflow „Software nachziehen“); sonst bricht der Bau. Vor dem Vorspulen laufen die Tests der einbindenden Instanzen mit dem Branch.
- **Dossier-Überschriften:** Sind in einer Reise Überschrift und ID nicht eindeutig zuzuordnen, meldet `nachziehen` offen statt zu raten.
- **Gehzeitformat:** uneinheitliche Schreibweisen im Bestand (`3:30`, `3,5 h`); `nachziehen` übernimmt den Text unverändert, Normalisierung nur über `minuten()`.
- **Konflikt mit #268** in `routen.py`/`vorlage.html`: durch Reihenfolge ausgeschlossen.

## Abnahme

- Test an zwei Reisetypen (Beispielreise und `stadtwochenende`), zusätzlich eine frische, neue Reise ohne Pläne (#214).
- Konnektor-Abnahme an einer frischen Testreise, nie an echten Reisen: Strecke mit Kennzahlen anlegen, Reiter „Etappen“ prüfen.
- Browser-Rundgang auf Etappenseite, Tagesseite, Karte.

## Doku-Änderungen

`docs/design.md` (Baustein Kennzahlenleiste, „Etappe“), `docs/ontologie.md` (Etappe als Art mit `summiert`), `docs/konnektor.md` (Kennzahlen an Strecken), Kopfkommentar von `engine/vorlage.html`, `CLAUDE.md` (Aufbau-Zeile, falls `etappen_*` genannt).

## Known Limitations

- Reisen ohne Dossier können `lesetext_schreiben` weiter nicht nutzen (Folge-Issue).
- Kennzahlen sind frei bis auf die vier festen Kennungen; keine Prüfung auf Plausibilität der Werte.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Der Umbau setzt ADR-0001 (Arten gehören der Reise) und ADR-0007 (Grundform, `summiert`) um; es entsteht keine neue Grundsatzentscheidung. Die zwei Festlegungen (Dossier, Wort „Etappe“) stehen als Entscheidung des Product Owners in dieser Spec.

## Changelog

- 2026-11-04: Initial spec created
