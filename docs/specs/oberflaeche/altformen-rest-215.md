---
entity_id: altformen-rest-215
type: refactor
created: 2026-11-05
updated: 2026-11-05
status: draft
version: "1.0"
workflow: fix-215-altformen
tags: [altformen, route, zu-tun, buchung, nachziehen, push]
test_targets: [engine/vorlage.html, engine/routen.py, engine/push.py, engine/bauen.py, engine/neu.py, engine/tests/test_altformen_rest_215.py, engine/tests/seiten_browser.mjs, engine/tests/pwa_browser.mjs]
---

# Altformen-Reste: Route `offen` und Bestandsfeld `buchung` (#215, Teil 3)

Workflow: `fix-215-altformen`. Analyse: `docs/context/fix-215-altformen.md`. Oberthema #215 (technische Schulden); Teile 1, 2, 4, 5 sind erledigt (#269, #268, Kleinigkeit, `stadtwochenende`).

## GitHub Issue

**Issue:** #215 (dieser Teil schließt #215)

## Approval

- [ ] Approved

Vorab entschieden (Product Owner, 5.11.2026): Beide Reste werden hier umgesetzt, danach wird #215 geschlossen.

## Purpose

Zwei Altformen werden entfernt, ohne dass ein Handschritt bleibt (CLAUDE.md, #250):

1. **Route `offen`:** Der Reiter heißt auf der Seite seit 28.10.2026 „Zu tun“, im Code (Reiterschlüssel, Hash, Symbolzuordnung, Push-Ziel) noch `offen`. Neu heißt die Route `zu-tun`. Der Hash `#offen` bleibt als dauerhafter Alias (Lesetoleranz), weil gespeicherte Lesezeichen und bereits versandte Push-Benachrichtigungen ihn tragen.
2. **Bestandsfeld `buchung:`** an Unterkünften, Aufenthalten und Strecken in `plan/routen.yaml`: Der Buchungsstand kommt nur noch aus Buchungen `B-…`. Das Feld wird beim Lesen nicht mehr ausgewertet; `neu.py nachziehen` stellt vorhandene Einträge um.

Klarstellung gegenüber der Analyse: Die Seite liest `d.buchung` weiter. Das ist aber nicht das Eingabefeld, sondern der von `routen.py` berechnete Stand (`buchung_von`: Status der geltenden Buchung, sonst „offen“ bei buchbarer Art). Der Lesepfad, der entfällt, liegt in `engine/routen.py` (`buchung_von`, Zweig `d.get("buchung")`), nicht in der Vorlage.

## Source

- **File:** `engine/vorlage.html`, `engine/routen.py`, `engine/push.py`, `engine/bauen.py`, `engine/neu.py`
- **Identifier:** `REITER`/`REIHE`/`START`/`route()`/`offenZahl()` (Vorlage 1147–1154, 5038, 5080–5115), `push.py` Z. 313 (`ziel = "offen"`), `bauen.py` Z. 1419 (Symbol), `Routen.buchung_von()` (Z. 1835), `neu.nachziehen()`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `docs/adr/0001-kern.md` | ADR | Prüfstelle, unten beantwortet |
| `docs/adr/0003-heimat.md` | ADR | Buchung hat ihre Heimat in `B-…`, keine zweite Eingabeform |
| `engine/texte_*.py` | Textkatalog | Schlüssel `seite.reiter.offen` (Name; Wortlaut „Zu tun“ bleibt), neue Meldungen der Umstellung |
| `#267` (`sprache_nachziehen`, `reste_nachziehen`) | Vorbild | Muster für Umstellung mit Meldung und Idempotenz |
| Instanzen / Reisen-Repos | extern | Instanz-Tests vor dem Vorspulen (CLAUDE.md); ob eine echte Reise `buchung:` nutzt, zeigt nur der Lauf von `nachziehen` dort |

## Scope

### Im Scope

1. Reiterschlüssel, Reihenfolge (`REIHE`), `START`, Route in `route()`, `offenZahl()` und das Symbol in `bauen.py` heißen `zu-tun` statt `offen`.
2. `#offen` leitet beim Start und bei `hashchange` auf `#zu-tun` um (Adresszeile wird ersetzt, `replaceState`, kein zusätzlicher Verlaufseintrag). Gilt auch für `reise.json` `start: offen` (alter Startreiter wird als `zu-tun` gelesen).
3. `push.py` erzeugt künftig `#zu-tun` als Ziel; bereits versandte Adressen mit `#offen` funktionieren über den Alias.
4. `Routen.buchung_von()` liest das Eingabefeld `buchung:` nicht mehr. Steht es noch in einer `routen.yaml`, meldet die Prüfung einen Fehler mit Verweis auf `neu.py nachziehen` (Katalogtext, alle Sprachen), statt es still zu ignorieren (sonst würde ein gebuchtes Ding plötzlich „offen“ aussehen).
5. `neu.py nachziehen` stellt `buchung:` an Dingen um (siehe Implementation Details), mit Meldung, idempotent, ohne Eingriff bei Reisen ohne das Feld.
6. Kommentar in `beispiel/reisen/beispielreise/plan/routen.yaml` („ein eigener Eintrag buchung: ginge auch“) entfällt; `docs/` und Kopfkommentar der Vorlage nennen die Route `zu-tun`.
7. Tests (neu und umgestellte Browser-Tests, Routenname).

### Nicht im Scope

- `varianten_titel` bleibt (Entscheidung #267, von einer Reise genutzt).
- Einzelform der Merkmalswerte bleibt (Lesetoleranz laut Gesamtspec #267).
- Das Wort im Textkatalog („Zu tun“) und die Textschlüssel selbst ändern sich nicht; der Schlüssel `seite.reiter.offen` darf bleiben (Name eines Katalogeintrags, keine Altform der Daten). Ein Umbenennen würde alle Sprachdateien berühren ohne Nutzen.
- Offene Aufgaben-Status `offen` (`AG_STATUS`) und Chip-Zustand `offen`: eigene, gültige Begriffe.
- Echte Reisen (nur über `nachziehen` im Reisen-Repo).

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/vorlage.html | MODIFY | Route/Reiter `zu-tun`; Alias `#offen` und `start: offen` |
| engine/bauen.py | MODIFY | Symbolzuordnung `zu-tun` |
| engine/push.py | MODIFY | Push-Ziel `zu-tun` |
| engine/routen.py | MODIFY | `buchung_von` ohne Eingabefeld; Prüfung meldet übriggebliebenes `buchung:` |
| engine/neu.py | MODIFY | `nachziehen`: `buchung:` → Buchung `B-…` |
| engine/texte_de.py, texte_en.py, weitere texte_*.py | MODIFY | Neue Prüf- und Umstellungsmeldungen in allen Sprachen |
| engine/tests/seiten_browser.mjs, seiten_zu_tun.mjs, seiten_reise.mjs, seiten_eine_seitenordnung.mjs, sprachen_rundgang.mjs, stil_abzug.mjs, pwa_browser.mjs | MODIFY | Route `zu-tun`; alter Link `#offen` bleibt als Test |
| engine/tests/test_altformen_rest_215.py | CREATE | Neue Tests |
| engine/tests/test_routen.py, test_neu.py, test_push.py | MODIFY | Auf neues Verhalten umstellen |
| beispiel/reisen/beispielreise/plan/routen.yaml | MODIFY | Kommentar entfernen |
| docs/design.md, docs/abgleich-2026-10-29.md | MODIFY | Nur, wo `offen` als Route steht |

### Estimated Changes

- Files: ca. 14
- LoC: +150/−60
- Risiko: MITTEL (Datenformat, gespeicherte Links, Push-Adressen)

## Implementation Details

### Route

`REITER`-Eintrag `["zu-tun", …]`, `REIHE` entsprechend. In `route()` wird vor der Auswertung `h === "offen"` zu `"zu-tun"` normalisiert und der Hash per `history.replaceState` ersetzt. Dasselbe für `START` (aus `reise.json` `start`). Alle bisherigen Zweige `zeigeReiter("offen")` heißen `zeigeReiter("zu-tun")`; `offenZahl()` sucht `a[href="#zu-tun"]`. Unterziele (`#zu-entscheiden`, `#zu-buchen`, `#aufgaben`, `#fragen`, `#rueckmeldungen`) bleiben unverändert.

### Umstellung `buchung:`

Für jede Unterkunft, jeden Aufenthalt und jede Strecke mit Eingabefeld `buchung:` in `routen.yaml`:

| Wert | Umstellung |
|------|-----------|
| `offen` oder leer | Schlüssel wird gelöscht (entspricht dem Standard „offen“; keine Buchung) |
| `angefragt` | neue Buchung `B-NN` mit `fuer: [<ID>]`, `status: angefragt` |
| `gebucht` | neue Buchung `B-NN` mit `fuer: [<ID>]`, `status: gebucht` |
| jeder andere Text | neue Buchung `B-NN`, `status: gebucht`, der Text wörtlich im Feld `notiz`; zusätzlich Meldung „bitte prüfen“ |

Neue Buchungen bekommen `quelle` (Pflicht der Prüfung) mit dem Katalogtext „übernommen aus dem früheren Feld buchung (nachziehen)“. Die laufende Nummer vergibt `nachziehen` nach den vorhandenen IDs. Hat das Ding bereits eine geltende Buchung, wird nur der Schlüssel gelöscht (die Buchung gewinnt schon heute). Kommentare und Form der Datei bleiben (ruamel, wie im Rest von `nachziehen`).

Offene Entscheidung für den Product Owner: Der „andere Text“ gilt als `gebucht`. Das erhält den bisherigen Stand (die Vorlage rechnet `gebucht = nicht offen/angefragt`). **Sichtbare Abweichung:** Bisher zeigt der Chip den Freitext selbst (`text: d.buchung`), nach der Umstellung steht dort „gebucht“, und der Text liegt in der `notiz` der Buchung. Das ist die einzige sichtbare Änderung der Spec; sie betrifft nur Reisen mit Freitext im alten Feld (die Beispielreisen haben keinen).

### Prüfstelle (ADR-0001)

Die Software kennt weiter nur Grundformen; `zu-tun` ist ein Oberflächenschlüssel, keine Reiseart. Das Feld `buchung:` verschwindet zugunsten der einen Heimat der Buchung (ADR-0003). Beide Beispielreisen (Wanderung und Stadtwochenende) sind betroffen und werden getestet; die Umstellung ändert keine sichtbare Seite, außer dem Chip-Text bei Freitext im alten Feld (siehe Umstellung `buchung:`).

## Test Plan

### Automated Tests (TDD RED)

Neue Datei `engine/tests/test_altformen_rest_215.py`, Umstellungen in den bestehenden Dateien.

- [ ] Test 1: GIVEN gebaute Seite beider Beispielreisen WHEN der Reiter „Zu tun“ im Browser geöffnet wird THEN lautet der Hash `#zu-tun`, der Reiter ist aktiv und zeigt dieselben Inhalte wie vorher.
- [ ] Test 2: GIVEN ein alter Link `…#offen` WHEN die Seite geöffnet wird THEN zeigt sie den Reiter „Zu tun“ und die Adresszeile steht auf `#zu-tun` (ohne neuen Verlaufseintrag).
- [ ] Test 3: GIVEN `reise.json` mit `start: offen` WHEN die Seite gebaut und geöffnet wird THEN beginnt sie auf „Zu tun“.
- [ ] Test 4: GIVEN neue Push-Meldung nur mit Aufgaben/Rückmeldungen WHEN `push.py` das Ziel bildet THEN ist es `zu-tun`; die Service-Worker-Prüfung (`pwa_browser.mjs`) mit der alten URL `#offen` öffnet weiter den Reiter.
- [ ] Test 5: GIVEN `routen.yaml` mit `buchung: angefragt` an U-01 ohne Buchung WHEN `nachziehen` THEN gibt es eine Buchung mit `fuer: [U-01]`, `status: angefragt`, `quelle` gesetzt, das Feld `buchung:` ist weg, und der gebaute Stand von U-01 ist unverändert „angefragt“.
- [ ] Test 6: GIVEN `buchung: offen` WHEN `nachziehen` THEN verschwindet nur der Schlüssel, es entsteht keine Buchung, der Stand bleibt „offen“.
- [ ] Test 7: GIVEN `buchung: "Zusage per Telefon"` WHEN `nachziehen` THEN entsteht eine Buchung `gebucht` mit `notiz` gleich dem Text und eine Prüf-Meldung; der gebaute Chip zeigt „gebucht“ (bewusste Abweichung, der Test prüft das).
- [ ] Test 8: GIVEN ein Ding hat `buchung: gebucht` und bereits die Buchung B-01 WHEN `nachziehen` THEN entsteht keine zweite Buchung, nur der Schlüssel entfällt.
- [ ] Test 9: GIVEN zweiter Lauf von `nachziehen` und `stadtwochenende` ohne Feld WHEN gelaufen THEN keine Änderung, keine Meldung.
- [ ] Test 10: GIVEN `routen.yaml` mit übrig gebliebenem `buchung:` WHEN gebaut (ohne `nachziehen`) THEN bricht die Prüfung mit der Katalogmeldung ab, die `neu.py nachziehen` nennt (kein stilles Ignorieren).
- [ ] Test 11: GIVEN Textkatalog WHEN `test_texte.py` läuft THEN sind die neuen Schlüssel in jeder Sprache da und die Ausnahmelisten nicht länger.
- [ ] Test 12: GIVEN Quelltext von `engine/vorlage.html` WHEN gelesen THEN kommt `"offen"` nicht mehr als Reiter- oder Routenschlüssel vor (außer dem einen Alias).

## Acceptance Criteria

- **AC-1:** (Test 1, 3): Der Reiter heißt im Code `zu-tun`; die Seite beider Beispielreisen zeigt ihn wie bisher.
- **AC-2:** (Test 2, 4): Alte Adressen `#offen` (Lesezeichen, Push) öffnen weiter „Zu tun“; neue Push-Meldungen tragen `#zu-tun`.
- **AC-3:** (Test 5–9): `neu.py nachziehen` stellt `buchung:` ohne Handschritt um, verliert keinen Buchungsstand, ist idempotent und lässt Reisen ohne das Feld unberührt.
- **AC-4:** (Test 10): Ein verbliebenes `buchung:` wird nie still ignoriert.
- **AC-5:** (Test 11): `test_texte.py` bleibt grün, Ausnahmelisten nur kürzer.
- **AC-6:** (alle Tests): `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün; die Browser-Tests laufen über beide Beispielreisen.
- **AC-7:** (Prozess): Vor dem Vorspulen laufen die Tests der einbindenden Instanzen mit dem Branch (Push-Ziel und Datenformat betreffen sie); danach wird #215 mit Hinweis auf #267/#268/#269 geschlossen.

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** keine (bestehend: ADR-0001, ADR-0003)

Keine neue ADR. Der Umbau folgt `ADR-0001` (Kern: nichts Reisespezifisches, keine Altformen ohne Umstellung) und `ADR-0003` (eine Heimat je Grundform: die Buchung wohnt in `B-…`). Begründung: Beide Reste sind Aufräumen bestehender Entscheidungen, keine neue Richtung.

## Definition of Done

- [ ] Alle Tests 1–12 sind geschrieben, zuerst rot, dann grün
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests` ist grün (Beispielreise und Stadtwochenende), Browser-Tests laufen über beide
- [ ] `neu.py nachziehen` stellt `buchung:` um, idempotent, mit Test gegen beide Beispielreisen
- [ ] Alter Link `#offen` und alte Push-Adresse öffnen „Zu tun“ (Browser-Test)
- [ ] Tests der einbindenden Instanzen mit dem Branch sind vor dem Vorspulen grün
- [ ] Pull Request, CI grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Vorspulen auf `main`
- [ ] #215 mit Hinweis auf #267/#268/#269 geschlossen

## Known Limitations

- Ob eine echte Reise `buchung:` nutzt, ist hier nicht prüfbar; die Instanz-Tests und der Lauf von `nachziehen` im Reisen-Repo zeigen es.
- `#offen` bleibt dauerhaft als Alias im Code (bewusst: Lesetoleranz für gespeicherte Links, keine Altform der Daten).

## Changelog

- 2026-11-05: Erstfassung
