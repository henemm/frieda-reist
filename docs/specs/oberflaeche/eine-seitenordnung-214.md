---
entity_id: eine-seitenordnung-214
type: bugfix
created: 2026-11-02
updated: 2026-11-02
status: approved
version: "1.0"
workflow: fix-214-eine-seitenordnung
tags: [vorlage, seitenordnung, heimat, zeitachse, plan, tagesseiten]
test_targets: [engine/vorlage.html, engine/tests/test_eine_seitenordnung.py, engine/tests/test_seite.py]
---

# Eine Seitenordnung für alle Reisen (#214)

Workflow: `fix-214-eine-seitenordnung`. Analyse: `docs/context/fix-214-eine-seitenordnung.md`. Ursprungsanfrage: Issue #214 mit Kommentar (weitere technische Schulden: #215).

## GitHub Issue

**Issue:** #214 (Folgeschulden: #215)

## Approval

- [x] Approved (Product Owner, 2.11.2026, Kommentar in #214)
- [x] Die fünf Entscheidungen des Product Owners (Abschnitt „Entscheidungen des Product Owners“) sind getroffen: Alle fünf Empfehlungen gelten.

Die Richtung („eine Ordnung für alle, der alte Zweig entfällt“) hat der Product Owner am 2.11.2026 freigegeben („ja, so klingt es richtig“).

## Purpose

Die Seitenordnung aus ADR-0003 (Zeitachse in einer Spalte, je Tag eine Tagesseite, jedes Ding genau einmal vollständig, „Zu tun“ mit „Zu entscheiden“ und „Zu buchen“) gilt heute nur für eine Reise, die drei Dinge zugleich hat: einen vollständig gewählten Plan, den Baustein `tagesseiten` und keine Einstellung `darstellung.tiefe`. Jede andere Reise, auch **jede neue**, bekommt die alte Plan-Seite (`PLAN_DA` in `engine/vorlage.html`): Tageskästen in zwei Spalten, Unterkünfte als Liste darüber, dieselbe Buchung an der Liste und an jeder Nacht. Ein Familienbesuch mit Ferienhaus über sechs Nächte zeigt die Buchung siebenmal vollständig.

Nach dieser Spec gibt es eine Seitenordnung. Der alte Zweig wird entfernt, nicht ergänzt. Ob Pläne existieren, ob sie entschieden sind und welche Einstellungen die Reise hat, ändert nur, **was am Tag steht** (Marke „offen“, Vergleich an der Heimat), nie den Aufbau der Seite.

## Source

- **File:** `engine/vorlage.html`
- **Identifier:** `PLAN_FEST`, `PLAN_TAGE`, `PLAN_DA` (Z. 1055–1081), `ansichtStart`, `ansichtReise`, `tagesplan`, `unterkuenfte`, `nachtZeile`, `wahlZeile`, `wegVerlauf`, `heimat`, `ansichtPlanDetail`, `ETAPPE_TAG`, `ETAPPEN_REITER`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `R.tage`, `R.summe`, `R.plaene[].aktuell`, `R.unterkuenfte[].naechte`, `R.aufenthalte`, `R.buchungen`, `R.wahlstellen[].an` | Reisemodell (`engine/routen.py`, `bauen()`) | Liefert immer `tage` des aktuellen Plans, auch ohne benannte Pläne. Wird nicht geändert |
| `D.reise.bausteine`, `D.reise.tiefe`, `D.reise.plan_reiter`, `D.reise.status` | Einstellungen der Reise (`reise.yaml`) | Steuern bisher den Zweig; danach nicht mehr den Aufbau |
| `docs/adr/0001-kern.md` | ADR | Prüfstelle (zehn Fragen), unten beantwortet |
| `docs/adr/0003-heimat.md` | ADR | Eine Heimat je Grundform; Nachtrag zu Punkt 3 |
| `docs/specs/oberflaeche/tagesseite-plan.md` (#144) | Spec | Tagesnummer und Datum; bekommt einen Nachtrag |
| `docs/specs/oberflaeche/papierkorb-146.md` | Spec | Stornierte Buchungen eingeklappt; gilt weiter, der zugehörige Test wird umgeschrieben |
| `engine/reisevorlage/` | Vorlage | Ausgangspunkt einer neuen Reise; Browser-Rundgang |
| `beispiel/reisen/beispielreise` | Beispielreise | Einzige Testreise (Ida und Karl); die Form ohne Pläne wird im Test per `copytree` abgeleitet |
| Parallele Arbeit an #202/#203 | andere Sitzung | `requirements.txt`, `.github/workflows/tests.yml`, `betrieb/veroeffentlichen.sh`: **nicht anfassen** |

## Scope

### Im Scope

- Eine Zeitachse und je Tag eine Tagesseite für jede Reise mit Tagen.
- Die Heimat jedes Dings wird an einer Stelle berechnet (`heimat`) und gilt überall gleich.
- „Zu tun“ mit „Zu entscheiden“ und „Zu buchen“ immer.
- Wahlen mit `an:` erscheinen immer an ihrem Element.
- Alter Zweig `PLAN_DA` und alles, was nur an ihm hängt, entfällt.
- Tests, Texte, Dokumentation, ADR-0003-Nachtrag.

### Nicht im Scope

- **Inhalte echter Reisen.** Sie werden im Gespräch über den Konnektor bereinigt (Issue #214, „Nicht hier“). Diese Spec ändert keine Reisedaten und keine Migration.
- **#215** (Reisetyp im Code, doppelte Regeln, Altformen, nur eine Testreise). Hier entsteht nur die zweite Testform ohne Pläne, soweit die Zählprüfung sie braucht.
- **Datenmodell und Python-Seite:** `routen.py`, `konnektor.py` (außer der Beschreibung von `setting_set`), `waechter.py`, `rueckmeldungen.py`.
- **Parallele Arbeit an #202/#203:** `requirements.txt`, `tests.yml`, `veroeffentlichen.sh`.
- **Echte Reisen im Repo:** Das Repo ist öffentlich. Spec, Tests und Commits nennen nur die Beispielreise (Ida und Karl) und Reisetypen als Gattung.

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/vorlage.html` | MODIFY | `PLAN_ANSICHT` einführen; `PLAN_DA`, `PLAN_TAGE`, Reiter „Plan“, `tagesplan()`, `unterkuenfte()`, `ansichtPlan`, `ansichtRahmen`, `entscheidungen`, `fragenKarte` entfernen; `heimat()`, Startseite, Routing, Zurück-Link, Etappen vereinheitlichen; `ZU_TUN` immer an; Kopfkommentar und Bausteinseite; `id` von `nachtZeile`/`wahlZeile` eindeutig |
| `engine/reise.py` | MODIFY | Baustein `tagesseiten` und Einstellung `plan_reiter` werden gelesen und ignoriert (alte `reise.yaml` bleibt gültig) |
| `engine/neu.py` | MODIFY ggf. | `BAUSTEINE_IDEE` nur, falls der Baustein bleibt |
| `engine/texte_de.py`, `engine/texte_en.py` und alle weiteren `engine/texte_*.py` | MODIFY | Nicht mehr genutzte Schlüssel (`seite.plan.*` u. a.) entfernen; Beschreibung von `setting_set` im Konnektor ohne `tagesseiten` |
| `engine/tests/test_texte.py` | MODIFY | Ausnahmelisten dürfen nur kürzer werden |
| `engine/tests/test_eine_seitenordnung.py` | CREATE | Zählprüfung und ID-Prüfung in vier Fällen (Name vorläufig) |
| `engine/tests/seiten_eine_seitenordnung.mjs` | CREATE | Browser-Teil dazu (Name vorläufig) |
| `engine/tests/test_seite.py` | MODIFY | #146-Test und `test_buchung_hat_eine_heimat_auch_ohne_tagesseiten` umschreiben; Rundgang über frische Reise |
| `engine/tests/test_heimat_unterkunft.py`, `test_tagesplan.py`, `test_reiseueberblick.py`, `test_tagesseite.py`, `test_b2_ansichten.py` | MODIFY | Fälle ohne Pläne, Pläne offen, `tiefe` |
| `engine/tests/seiten_tagesplan.mjs` und weitere `seiten_*.mjs`, `sprachen_rundgang.mjs` | MODIFY/DELETE | `seiten_tagesplan.mjs` entfällt oder wird neu geschrieben |
| `docs/adr/0003-heimat.md` | MODIFY | Nachtrag zu Punkt 3 und zur Zeile „Buchung“ (kein „ohne Tagesseiten“ mehr) |
| `docs/design.md` | MODIFY | „Spalten“, „Seitenordnung“, Tabellen mit „ohne Tagesseiten“ |
| `docs/produkt.md`, `docs/neue-reise.md`, `docs/konnektor.md` | MODIFY | Baustein `tagesseiten` ist kein Schalter mehr |
| `docs/specs/oberflaeche/tagesseite-plan.md` | MODIFY | Nachtrag: Tagesnummer ohne Pläne aus `R.tage` |

### Estimated Changes

- Files: ca. 20 (eine Kerndatei, der Rest Tests und Dokumentation)
- LoC: `vorlage.html` netto −150 bis −250; Tests +150 bis +250; Dokumentation ±100
- Risk Level: **hoch** (zentrale Seitenlogik, drei von vier laufenden echten Reisen ändern ihr Aussehen)

## Definition of Done

- [ ] Alle Acceptance Criteria K1–K11 sind durch automatische Tests oder die genannte Prüfung belegt.
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests` ist grün, ohne echte Reisen.
- [ ] Im Code gibt es `PLAN_DA` und `PLAN_TAGE` nicht mehr (`grep` ohne Treffer).
- [ ] Der Browser-Rundgang über eine frische Reise aus `engine/reisevorlage` und über die Beispielreise ist grün.
- [ ] ADR-0003, `docs/design.md`, die Spec zu #144 und die Doku zum Baustein `tagesseiten` sind nachgetragen.
- [ ] Abnahme an zwei Reisetypen (siehe „Abnahme“) ist erfolgt.

## Implementation Details

### Kernidee: `PLAN_ANSICHT`

Eine neue Größe `PLAN_ANSICHT` ist der Plan, den die Zeitachse zeigt. Sie ersetzt `PLAN_TAGE` und ist immer gesetzt:

| Fall | `PLAN_ANSICHT` |
|---|---|
| (a) ohne Pläne | Ein Plan-Objekt aus dem Modell: `tage` und `summe` von `R`, keine Auswahl, Titel ist der Reisename |
| (b) Pläne offen | Der Plan mit `aktuell === true`, sonst wie (a) |
| (c) Plan fest | `PLAN_FEST` |
| (d) `darstellung.tiefe` | wie (b) bzw. (c); `tiefe` steuert die Startseite nicht mehr |

`PLAN_FEST` bleibt nur als „es ist entschieden“: Tagesnummer und Datum (#144), Titel „Reise“, Mahnlogik. Daraus folgt:

1. `ansichtStart` ruft immer `ansichtReise(m, PLAN_ANSICHT)`. Der Reiter „Plan“ entfällt; `#plan` führt zur Reise (wie heute schon bei gewähltem Plan).
2. `heimat()` bricht nicht mehr bei fehlendem `PLAN_TAGE` ab und ist die **einzige** Stelle, die die Heimat eines Dings bestimmt. Tageskasten und Listen fragen sie, sie rechnen nicht selbst.
3. **Genau einmal vollständig.** Wo der Tageskasten heute Unterkunft, Buchung, Aufenthalt oder Wahlvergleich ohne Prüfung zeigt, gilt die Prüfung „erste Nacht, erster Tag, erstes Ding“, die auf der Tagesseite (`nachtAbschnitt`) schon besteht. Sonst steht eine Zeile oder ein Chip mit einem Link zur Heimat.
4. `nachtZeile` und `wahlZeile` setzen heute beide `id = w.id` im selben Kasten. Die ID gehört nur dem Element, das die Heimat ist; das andere trägt keine oder eine abgeleitete ID. Das Sprungziel `#V-…` bleibt eindeutig.
5. „Zu tun“ (`ZU_TUN`) ist immer an. Wahlen mit `an: [W-…]` oder `[O-…]` und solche an Tag, Strecke oder Unterkunft erscheinen an ihrem Element in jedem Fall.
6. Der Zurück-Link der Tagesseite führt immer zur Reise, an dieselbe Zeile (ADR-0003 Punkt 4). Heute führt er je nach Zweig an drei Ziele.
7. Das Routing (`#plan`, `#varianten`, `#offen`, Tages-IDs) verliert die Zweige `PLAN_DA` und `!TIEFE`.
8. `design.md` „Spalten“: Die Tage stehen nirgends in zwei Spalten. Der Satz zu Plan-Tagen in zwei Spalten entfällt, die Angabe `vglMax` für den Vergleich bleibt.

### Reihenfolge der Commits

1. Spec, ADR-0003-Nachtrag, `design.md` (nach Freigabe).
2. Rote Tests: Testreise ohne Pläne, Zählprüfung, ID-Prüfung, Rundgang über frische Reise.
3. `PLAN_ANSICHT`, `heimat()`, Startseite, Routing.
4. Alten Zweig entfernen.
5. Tests und Dokumentation bereinigen, Baustein `tagesseiten` stilllegen.

## Entscheidungen des Product Owners

Fünf Fragen lassen sich nicht aus den Regeln ableiten. Jede hat eine Empfehlung. **Die Spec baut auf den Empfehlungen auf, vorbehaltlich Freigabe.** Antwortet der Product Owner anders, ändern sich nur die genannten Stellen.

### 1. Was zeigt die Seite vor der Entscheidung, wenn es mehrere Pläne gibt?

- **Empfehlung:** Die Zeitachse des aktuellen Plans (`R.tage`) mit der Marke „offen“ an Tagen mit offener Wahl. Der Vergleich ganzer Pläne bleibt im Reiter „Pläne“ (`varianten`).
- **Begründung:** Der Aufbau der Seite soll nicht davon abhängen, ob entschieden ist (Ziel von #214). Der aktuelle Plan ist schon heute der Plan, den Übersicht, Kalender und Wächter rechnen; die Seite zeigt dasselbe wie sie.
- **Folge für laufende Reisen:** Eine Rundreise mit mehreren Plänen zeigt statt Plan-Kästen die Zeitachse. Die Pläne selbst bleiben im Reiter „Pläne“ erhalten.
- **Alternative:** Vor der Entscheidung eine Auswahl „Welchen Plan ansehen?“ auf der Startseite. Das bringt den Planbezug zurück an die Startseite und macht Tagesnummern je nach Auswahl verschieden (das war der Fehler von #144). Nicht empfohlen.

### 2. Bleibt der Baustein `tagesseiten`?

- **Empfehlung:** Er entfällt als Schalter. Tagesseiten gehören zur Grundform Tag und gibt es immer. Der Wert in einer alten `reise.yaml` wird gelesen und ignoriert; keine Datenmigration.
- **Begründung:** Ein Schalter für die Seitenordnung widerspricht ihrem Ziel. Die Software kennt Grundformen (ADR-0001), und der Tag ist eine.
- **Folge für laufende Reisen:** Reisen ohne diesen Baustein bekommen Tagesseiten. Der Baustein verschwindet aus der Bausteinseite und aus `setting_set` des Konnektors.
- **Alternative:** Der Baustein bleibt, ist bei neuen Reisen an. Dann gäbe es weiter zwei Seitenordnungen, nur anders ausgelöst. Nicht empfohlen.

### 3. Was braucht `darstellung.tiefe` noch?

- **Empfehlung:** Nur noch den Plan-Baum im Reiter „Pläne“ (`ansichtPlanDetail`). Die Einstellung steuert nicht mehr die Startseite, die Tagesseiten und den Zurück-Link.
- **Begründung:** Der Plan-Baum ist eine Darstellung der Pläne, keine andere Seitenordnung. Dort ist er an seiner Heimat.
- **Folge für laufende Reisen:** Die Rundreise mit `tiefe: true` ist die am stärksten betroffene Reise: ihre Startseite wird zur Zeitachse; der Baum bleibt unter „Pläne“ erreichbar.
- **Alternative:** `tiefe` ganz streichen und den Baum nur aus der Zahl der Pläne ableiten. Das geht weiter, nimmt der Reise aber eine Einstellung. Erst nach der Abnahme der Rundreise zu entscheiden.

### 4. Was wird aus `darstellung.plan_reiter`?

- **Empfehlung:** Die genannten Rahmenabschnitte wandern in den Reiter „Wissen“, der `plan`-Abschnitte dort schon vorsieht („Über diesen Plan“). Die Einstellung wird ignoriert.
- **Begründung:** ADR-0003 Punkt 3 kennt den Reiter „Plan“ nicht mehr als dauerhaften Reiter; Plantext gehört nach „Wissen“.
- **Folge für laufende Reisen:** Die Rundreise mit `plan_reiter` verliert den Reiter „Plan“; ihre Abschnitte stehen unter „Wissen“.
- **Alternative:** Der Reiter bleibt, wenn die Reise ihn verlangt. Dann bliebe ein Rest des alten Zweigs. Nicht empfohlen.

### 5. Etappen bei offenen Plänen

- **Empfehlung:** Die Zuordnung der Etappen zu Tagen (`ETAPPE_TAG`) und der Reiter „Etappen“ (`ETAPPEN_REITER`) richten sich nach `PLAN_ANSICHT`. Auch bei offenen Plänen gilt ein Tag mit Etappe als „Tag mit Etappe“. Geprüft an der Beispielreise mit offenem Plan.
- **Begründung:** Eine Regel für alle Fälle; sonst bliebe `PLAN_FEST` als zweiter Zweig.
- **Folge für laufende Reisen:** Eine Etappenwanderung mit offenem Plan zeigt den Reiter „Etappen“ und die Etappen am Tag früher als bisher (schon vor der Entscheidung).
- **Alternative:** Etappen erst nach der Entscheidung. Das erhält den Unterschied, den #214 beseitigen soll.

## Test Plan

### Automated Tests (TDD RED)

Alle Tests laufen mit `engine/.venv/bin/python -m pytest -q engine/tests` ohne echte Reisen. Dateinamen und Testnamen sind vorläufig und werden in Phase 4 festgelegt.

- [ ] Test 1: GIVEN eine Reise ohne Pläne und ohne Wahlstellen (Kopie der Beispielreise, im Test abgeleitet) WHEN die Startseite gebaut wird THEN steht die Zeitachse in einer Spalte, je Tag eine Zeile mit genau einem Link.
- [ ] Test 2: GIVEN die Fälle (a) bis (d) WHEN die Startseite und jede Tagesseite gebaut sind THEN steht jede Buchung, Unterkunft, jeder Aufenthalt und jeder Wahlvergleich genau einmal vollständig.
- [ ] Test 3: GIVEN dieselben Fälle WHEN das DOM jeder Ansicht geprüft wird THEN kommt keine ID doppelt vor.
- [ ] Test 4: GIVEN ein Tag, an dem eine Nacht und eine Wahl dieselbe Kennung teilen WHEN er gebaut wird THEN trägt nur die Heimat die ID (eigener Test für `nachtZeile`/`wahlZeile`).
- [ ] Test 5: GIVEN eine neue Reise aus `engine/reisevorlage` WHEN sie im Browser angesehen wird THEN gleicht ihr Aufbau der Beispielreise (Zeitachse, Reiter, „Zu tun“), nicht der alten Seite.
- [ ] Test 6: GIVEN eine Reise ohne Pläne WHEN „Zu tun“ geöffnet wird THEN stehen „Zu entscheiden“ und „Zu buchen“ da.

### Testreise ohne Pläne

Im Test per `shutil.copytree` aus `beispiel/reisen/beispielreise` abgeleitet (wie `test_heimat_unterkunft.py` und `test_tagesplan.py`). Die Demo bleibt unverändert. Abgeleitete Werte sind erfunden und als **Beispielwert** markiert:

- keine Pläne (`P-…` entfernt, es gilt `R.tage`) und keine Wahlstellen;
- eine gebuchte Unterkunft über mehrere Nächte (Beispielwert: drei Nächte, eine Buchung);
- ein Aufenthalt ohne Nacht, der über mehrere Tage steht (Beispielwert: zwei Tage).

### Testmatrix

Je Fall wird gezählt (Zählprüfung „genau einmal vollständig“), dazu „keine doppelte ID im DOM“ in Startseite und Tagesseiten.

| Fall | Aufbau der Testreise | Buchung | Unterkunft | Aufenthalt | Wahlvergleich | ID-Prüfung |
|---|---|---|---|---|---|---|
| (a) ohne Pläne | Ableitung wie oben | 1 | 1 | 1 | entfällt (keine Wahlstellen) | ja |
| (b) Pläne offen | Beispielreise mit mehreren Plänen, keiner gewählt | 1 | 1 | 1 | 1 je Wahlstelle | ja |
| (c) Plan fest | Beispielreise, ein Plan gewählt | 1 | 1 | 1 | 1 je Wahlstelle | ja |
| (d) `darstellung.tiefe` | Beispielreise mit `tiefe: true` (Kopie im Test) | 1 | 1 | 1 | 1 je Wahlstelle | ja |

Ausdrücklich:

- `test_stornierte_buchung_eingeklappt_am_ding` (#146, `test_seite.py`) wird **bewusst umgeschrieben**. Er verlangt heute in der Schleife `for o in s["b01"]`, dass die Buchung an **jedem** Ding vollständig steht. Er verlangt danach: genau ein Ding mit vollem Block; die übrigen Dinge zeigen den Chip. Die Wirkung aus #146 (stornierte Buchung nur im zugeklappten Block „Storniert (n)“, Link bleibt gültig) bleibt Teil des Tests.
- `test_buchung_hat_eine_heimat_auch_ohne_tagesseiten` verlangt nicht mehr nur „sichtbar“, sondern „genau einmal vollständig“ und wird umbenannt, weil es „ohne Tagesseiten“ nicht mehr gibt.
- `test_unterkunft_vollstaendig_nur_an_der_ersten_nacht` (#157) gilt nun in allen vier Fällen, nicht nur im gewählten Plan.
- Eigener Test für die doppelte ID von `nachtZeile`/`wahlZeile` (Test 4).
- Browser-Rundgang über eine frisch aus `engine/reisevorlage` angelegte Reise (Test 5). `test_neu.py` baut sie nur; der Rundgang sieht sie im Browser an.
- Die Spec zu #144 (`tagesseite-plan.md`) bekommt einen Nachtrag: Ohne Pläne kommt die Tagesnummer aus `R.tage`; Nummer und Datum bleiben überall gleich (Übersicht, Tagesseite). Ein Test im Fall (a) prüft das.

## Acceptance Criteria

Die acht Kriterien aus #214, jedes einem geplanten Test zugeordnet (Dateien und Namen vorläufig).

- [ ] **K1. Die Startseite einer Reise ohne Pläne zeigt die Zeitachse in einer Spalte, je Tag eine Zeile mit genau einem Link.**
  Test: `test_eine_seitenordnung.py::test_ohne_plaene_zeitachse_eine_spalte_ein_link` (Fall a; Browser-Teil `seiten_eine_seitenordnung.mjs`).
- [ ] **K2. Jede Buchung, Unterkunft, jeder Aufenthalt und jeder Wahlvergleich steht in jedem Fall genau einmal vollständig; überall sonst steht eine Zeile oder ein Chip mit Link.**
  Tests: `test_eine_seitenordnung.py::test_genau_einmal_vollstaendig[ohne_plaene|plaene_offen|plan_fest|tiefe]`; dazu `test_seite.py::test_stornierte_buchung_eingeklappt_am_ding` (umgeschrieben) und `test_seite.py::test_buchung_genau_einmal_vollstaendig` (umbenannt).
- [ ] **K3. Keine doppelten IDs im DOM, in allen vier Fällen.**
  Tests: `test_eine_seitenordnung.py::test_keine_doppelte_id[ohne_plaene|plaene_offen|plan_fest|tiefe]` und `test_eine_seitenordnung.py::test_nachtzeile_und_wahlzeile_teilen_keine_id`.
- [ ] **K4. „Zu tun“ zeigt „Zu entscheiden“ und „Zu buchen“ auch ohne Pläne.**
  Test: `test_eine_seitenordnung.py::test_zu_tun_auch_ohne_plaene`; Bestand: `test_reiseueberblick.py`.
- [ ] **K5. Wahlen mit `an:` erscheinen an ihrem Element, in allen Fällen.**
  Test: `test_eine_seitenordnung.py::test_wahl_mit_an_steht_am_element[plaene_offen|plan_fest|tiefe]` (Wahlen an Tag, Strecke, Unterkunft, Ort und Abschnitt des Wissens). Fall (a) hat keine Wahlstellen; seine Prüfung ist, dass keine Marke und kein Vergleich erscheint.
- [ ] **K6. Eine frisch angelegte Reise sieht im Browser wie die Beispielreise aus, nicht wie die alte Seite.**
  Test: `test_seite.py::test_neue_reise_aus_der_vorlage_im_browser` (Rundgang über `engine/reisevorlage`, erweitert aus `test_neue_reise_aus_der_vorlage`).
- [ ] **K7. `engine/.venv/bin/python -m pytest -q engine/tests` ist grün.**
  Prüfung: ganzer Lauf, dazu die Ausnahmelisten in `test_texte.py` (nur kürzer).
- [ ] **K8. ADR-0003 und `docs/design.md` sind nachgetragen, die Prüfstelle ist im PR beantwortet.**
  Prüfung: Durchsicht im PR; Prüfstelle siehe unten. Die Nachträge sind Teil von Commit 1.

Zusätzlich:

- [ ] **K9.** Die fünf Entscheidungen des Product Owners sind getroffen und in ADR-0003 und `design.md` eingetragen.
- [ ] **K10.** Die Tagesnummer ohne Pläne kommt aus `R.tage` und stimmt mit der Übersicht überein (`test_tagesseite.py::test_tagesnummer_ohne_plaene_aus_tage`, Nachtrag zu #144).
- [ ] **K11.** Die Rundreise mit `tiefe` und `plan_reiter` verliert keine Information: Plan-Baum unter „Pläne“, Rahmenabschnitte unter „Wissen“ (`test_tagesplan.py::test_tiefe_nur_noch_plan_baum`, `test_reiseueberblick.py::test_plan_reiter_abschnitte_unter_wissen`).

## Prüfstelle ADR-0001

Durchgespielt an zwei Reisetypen: **Etappenwanderung mit Varianten** (Beispielreise: Pläne, Wahlstellen, Tagesseiten) und **Reise ohne Alternativen** (Familienbesuch: keine Pläne, keine Wahlstellen, ein Ferienhaus über mehrere Nächte).

| Nr. | Frage | Antwort |
|---|---|---|
| 1 | Ontologie statt Sonderfall | Besteht. Die Änderung betrifft nur Grundformen (Tag, Aufenthalt, Buchung, Wahl). Nichts Reisespezifisches in der Software. Wanderung: Zeitachse, Vergleich an der Nacht. Familienbesuch: Zeitachse, ein Ferienhaus mit einer Buchung an der ersten Nacht. Beides mit derselben Seite |
| 2 | Kein Katalog | Besteht. Keine Art und kein Merkmal wird eingeführt oder vorausgesetzt |
| 3 | Keine KI in Frieda | Besteht. Reine Darstellung |
| 4 | Die Tür | Besteht. Konnektor und Daten unverändert; `setting_set` nennt `tagesseiten` nicht mehr (`docs/konnektor.md`) |
| 5 | Herkunft | Nicht berührt. Keine neue Aussage |
| 6 | Rollen entscheiden | Besteht. Keine Entscheidung ohne Person und Datum; offene Wahlen bleiben offen |
| 7 | IDs und Verlauf | Besteht. Keine ID wird vergeben, gelöscht oder überschrieben. Alte `reise.yaml` bleibt gültig; die Zählung der IDs im DOM wird eindeutig |
| 8 | PWA | Besteht, wenn der Browser-Rundgang für beide Reisetypen grün ist und die Seite offline weiter lädt (Service Worker unverändert) |
| 9 | Claude Code | Besteht. Reiseinhalte werden nicht in Claude Code geändert |
| 10 | Dokumentation | ADR-0003 (Nachtrag), `docs/design.md`, `docs/produkt.md`, `docs/neue-reise.md`, `docs/konnektor.md`, dieses Dokument |

## Risiken

- **Laufende echte Reisen ändern ihr Aussehen.** Drei von vier haben heute die alte Seite (Rundreise, Familienbesuch, Skiurlaub). Vorbeugung: Fotos vorher und nachher je Reisetyp, vor dem Zusammenführen.
- **Rundreise mit `tiefe` und `plan_reiter` ist das größte Risiko.** Sie hat Pläne, einen Plan-Baum und den Reiter „Plan“ mit Rahmenabschnitten. Sie wird zuerst geprüft; Entscheidungen 3 und 4 betreffen sie unmittelbar.
- **Ein Zweig wird übersehen.** `PLAN_DA` steht an vielen Stellen in einer Datei von ca. 4700 Zeilen. Vorbeugung: Zählprüfung und ID-Prüfung in allen vier Fällen, Suche nach `PLAN_DA`, `PLAN_TAGE`, `TIEFE` nach dem Umbau ohne Treffer.
- **Doppelte IDs verschwinden mit dem alten Zweig nicht von selbst** (`nachtZeile`/`wahlZeile`). Eigener Test.
- **Etappen bei offenen Plänen** erscheinen früher (Entscheidung 5).
- **Konflikte mit der parallelen Arbeit** an #202/#203: Dateien bleiben unberührt.
- **Öffentliches Repo:** Keine Namen, Orte oder Daten echter Reisen in Tests, Fotos, Commits.

## Abnahme

Nie nur an der Wanderung (Erfahrung aus #214: genau das hat den Fehler übersehen).

1. **Fotos vorher und nachher je Reisetyp** beim Product Owner (privat, nicht im Repo): Rundreise zuerst, dann Familienbesuch, Etappenwanderung, Skiurlaub.
2. **Frische Testreise über den Konnektor** angelegt (nicht eine echte Reise): Seite ansehen, eine Unterkunft über mehrere Nächte mit einer Buchung eintragen, einen Aufenthalt über mehrere Tage, eine Wahlstelle. Danach prüfen: jedes Ding einmal vollständig, Rest Zeilen.
3. **Zwei Reisetypen:** Wanderung mit Varianten und Reise ohne Alternativen, je mit Browser-Rundgang (Handy und Rechner).
4. `engine/.venv/bin/python -m pytest -q engine/tests` grün; ADR-0003-Nachtrag und `design.md` stehen im selben PR.
5. Nach dem Zusammenführen: Prüfung der echten Reisen nach dem Veröffentlichen liegt beim Product Owner im Reise-Repo (außerhalb dieses Repos).

## Doku-Änderungen

- `docs/adr/0003-heimat.md`: Nachtrag zu Punkt 3 (Reiter hängen nicht an „Plan gewählt“; es gibt keinen Reiter „Plan“ mehr, vorbehaltlich Entscheidung 4) und zur Zeile „Buchung“ (kein „ohne Tagesseiten“ mehr); Verlaufseintrag mit Verweis auf #214.
- `docs/design.md`: „Spalten“ (keine zwei Spalten für Tage), „Seitenordnung“ (Reiter, Zeitachse), Tabellen mit „ohne Tagesseiten“ (Buchung, Wahlstelle und weitere Zeilen).
- `docs/produkt.md` und `docs/neue-reise.md`: Baustein `tagesseiten` ist kein Schalter mehr; neue Reisen haben Tagesseiten von Anfang an.
- `docs/konnektor.md`: `setting_set` ohne `tagesseiten`; Hinweis, dass ältere Einstellungen ignoriert werden.
- `docs/specs/oberflaeche/tagesseite-plan.md`: Nachtrag zur Tagesnummer ohne Pläne.
- Texte in **allen** Sprachen in `engine/texte_*.py` (nicht mehr genutzte Schlüssel entfernen); die Ausnahmelisten in `engine/tests/test_texte.py` dürfen nur kürzer werden.
- Kopfkommentar der Vorlage und Bausteinseite (`#bausteine`): Baustein `tagesseiten` entfällt.

## Known Limitations

- Mehrere vollständig gewählte Pläne: `PLAN_FEST` ist der erste Plan (wie in #144).
- Reisen mit sehr vielen Tagen zeigen eine lange Zeitachse; Gliederung nach Reiseabschnitten ist nicht Teil dieses Fehlers (siehe #215).

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** Nachtrag zu ADR-0003 (kein neues ADR)
- **Rationale:** Die Entscheidung „eine Heimat je Grundform, eine Seitenordnung“ steht schon in ADR-0003. Dieser Fehler stellt sie für alle Reisen her. Neu zu entscheiden ist nur, dass die Reiter nicht mehr an „Plan gewählt“ hängen (Punkt 3), und die Folgen für `tagesseiten`, `tiefe` und `plan_reiter` (Entscheidungen 2 bis 4). Das gehört als Nachtrag zu ADR-0003.

## Changelog

- 2026-11-02: Erstfassung (#214), Entscheidungen des Product Owners offen (vorbehaltlich Freigabe)
- 2026-11-02: Freigabe durch den Product Owner, alle fünf Empfehlungen gelten. Entscheidung 5 präzisiert: Die frühere „Folge“ nannte den Reiter „Etappen“ bei offenen Plänen; nach dem Mechanismus (`ETAPPEN_REITER` folgt `PLAN_ANSICHT`) verhält sich ein offener Plan wie ein fester, der Reiter entfällt. RED-Phase: Tests in `engine/tests/test_eine_seitenordnung.py` und `seiten_eine_seitenordnung.mjs` (Namen festgelegt); Fall (a) hat Bausteine nur `[karte]`, Fall (d) `tiefe` und `plan_reiter: [W-02]` ohne Baustein `tagesseiten`. Die Unterkunft hat in allen Fällen mehrere Nächte, der Aufenthalt A-01 steht an zwei Tagen (Beispielwerte). K4 „Zu entscheiden“ wird in einer Form ohne Pläne mit einer offenen Wahlstelle geprüft (ohne Wahlstellen gibt es nichts zu entscheiden). Entscheidung 5 hat ihren eigenen Test: `test_eine_seitenordnung.py::test_etappen_bei_offenen_plaenen_wie_bei_festem_plan`.
- 2026-11-02: Umsetzung (GREEN, Adversary VERIFIED). Auslegungen: Der Vergleich ganzer Pläne aus Entscheidung 1 und 3 ist eine eigene Seite `#plaene` mit einer Karte „… zur Wahl →“ im Überblick (nur bei Baustein `varianten`, mehreren Plänen und keinem gewählten), kein eigener Reiter; der erste Reiter heißt bei offenen Plänen „Varianten“, sonst „Reise“. `TIEFE` bleibt für den Plan-Baum (Entscheidung 3); die Suche ohne Treffer gilt nur für `PLAN_DA` und `PLAN_TAGE`. In `test_genau_einmal_vollstaendig` prüft die Schleife über die Sprungziele „voll und Tagesseite“ nur für die Dinge mit voller Form (B-01, U-01, A-01); Orte ohne volle Form (O-03) konnten das nie erfüllen. Die Zählung der Wahlvergleiche bleibt unverändert. Alte Bausteine (`tagesseiten`) verwirft auch `setting_set` still.
