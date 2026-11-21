---
entity_id: profil-nacharbeiten-578
type: bugfix
created: 2026-11-21
updated: 2026-11-21
status: draft
workflow: fix-578-profil-nacharbeiten
version: "1.0"
tags: [konnektor, profil, schreibgrenze, konten, tests, m7]
---

# Profile: kleine Nacharbeiten aus der Prüfung von #12 (#578)

## Approval

- [ ] Approved

## Purpose

Die unabhängige Prüfung der Profile (#12, Spec `profile-12`) fand vier kleine Mängel, alle niedrig. Ein abgelehnter Profileintrag verbraucht heute Schreibgrenze, die Anleitung nennt das Profil auch dort, wo es das Werkzeug nicht gibt, die Obergrenze der Einträge hält bei gleichzeitigem Anlegen nicht sicher, und ein Test hängt von der Reihenfolge ab. Diese Spec behebt alle vier, ohne Texte, Datenformat oder Schnittstelle zu ändern.

## Ziel und Abgrenzung

- **Im Scope:**
  - F001: Ein Profileintrag zählt nur dann zur Schreibgrenze je Konto, wenn er angenommen wurde. Die Grenze lehnt weiterhin vor dem Schreiben ab.
  - F002: Der Profil-Satz der Anleitung (`profil_nutzen` bzw. `profil_nicht_nutzen`) steht nur im Konto-Zugang, nicht im reisebezogenen Zugang ohne Konto.
  - F003: Zählen und Einfügen in `profil_setzen` laufen unter derselben Schreibsperre (`BEGIN IMMEDIATE`); die Obergrenze je Konto wird auch bei gleichzeitigen Neuanlagen nie überschritten.
  - F004: Der Test `test_anmeldung::test_pruefungen_buendeln_je_reise_und_tag` ist nicht mehr von der Reihenfolge abhängig; die Ursache (thread-lokale Seitensprache überlebt zwischen Tests) wird im autouse-Fixture von `engine/tests/conftest.py` behoben.
  - Die Spec `profile-12` wird im Zuge der Umsetzung nachgezogen (siehe Umsetzung, Punkt 5).
- **Nicht im Scope (Nicht-Ziele):**
  - Keine neuen oder geänderten sichtbaren Texte (Kataloge `texte_de.py` und `texte_en.py` bleiben unverändert).
  - Kein Datenformat, keine Schemaänderung, kein Eintrag in `neu.py nachziehen`.
  - Das Restfenster der Schreibgrenze bei gleichzeitigen Aufrufen anderer Werkzeuge am Rand der Grenze (Prüfen und Zählen sind je Werkzeug zwei Schritte, wie bei allen anderen Schreibwerkzeugen) bleibt bestehen und ist nicht Teil dieser Änderung.
  - Weitere thread-lokale Zustände (`konnektor._zone`, `konnektor._gesichert`) werden nur angefasst, wenn beim Bauen derselbe Mangel nachweisbar ist.
  - Keine Änderung an `profile_entry_remove` (zählt und blockiert weiterhin nie).
- **Kern (ADR-0001):** Berührt weder Arten, Merkmale noch Grundformen und nichts Reisespezifisches; wirkt für alle Reisen und Instanzen gleich. Beide Beispielreisen (`beispielreise`, `stadtwochenende`) verhalten sich unverändert, soweit sie das Profil nutzen.

## Source

- **File:** `engine/konnektor.py`, `engine/konten.py`, `engine/tests/conftest.py`
- **Identifier:** `profil_werkzeug`, `anleitung`, `profil_setzen`, Fixture `rueckfall_deutsch`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `konten.schreibgrenze`, `konten.schreiben_vormerken` | Code (`engine/konten.py`) | Schreibgrenze je Konto (#380); Reihenfolge im Profilwerkzeug ändert sich |
| `konten.KontoFehler` | Code | Fehler `profil_voll`, leer, zu lang, nicht gefunden; bleiben unverändert |
| `instanz.grenze_profil_eintraege` | Code (`engine/instanz.py`) | Obergrenze der Einträge je Konto |
| `reisespeicher._transaktion` | Code (`engine/reisespeicher.py`) | Vorbild für `BEGIN IMMEDIATE` mit Rollback |
| `anmeldung._anfrage`, `sprache_der_seite`, `meldungen_ordnen` | Code (`engine/anmeldung.py`) | Thread-lokale Seitensprache (F004) |
| `texte._aufruf`, `texte.VORGABE` | Code (`engine/texte.py`) | Sprachvorgabe der Tests |
| `profile-12` | Spec | Punkt 7, Test 10, AC-3, Test 14; wird mit dieser Änderung präzisiert |
| `trennung-grenzen-380` | Spec | Schreibgrenze je Konto |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konnektor.py` | MODIFY | F001 `profil_werkzeug`: `schreiben_vormerken` nach erfolgreichem `profil_setzen`; F002 `anleitung`: Profil-Satz nur mit `konto_id` |
| `engine/konten.py` | MODIFY | F003 `profil_setzen`: `BEGIN IMMEDIATE` vor dem Zählen |
| `engine/tests/conftest.py` | MODIFY | F004: `anmeldung._anfrage.sprache` je Test zurücksetzen |
| `engine/tests/test_profil.py` | MODIFY | neue Tests für F001, F002, F003 |
| `engine/tests/test_anmeldung.py` | MODIFY | Test, der den Fixture-Fix für F004 belegt |
| `docs/specs/konnektor/profile-12.md` | MODIFY | Punkt 7 und Anleitung präzisieren (Umsetzung Punkt 5) |

### Estimated Changes

- Files: 6 (4 Code/Test, 1 Spec, diese Spec)
- LoC: +60/-5 (überwiegend Tests)
- Risiko: niedrig

## Implementation Details

1. **F001 (`profil_werkzeug`, `engine/konnektor.py`):** Reihenfolge `bestaetigt` prüfen, `schreibgrenze(k)`, `profil_setzen(...)`, danach `schreiben_vormerken(k)`. Wirft `profil_setzen` einen `KontoFehler` (leer, zu lang, unbekannte oder fremde `PR-<n>`, Profil voll), wird nicht gezählt. Die Grenze lehnt weiterhin vor dem Schreiben ab; nur das Zählen wandert hinter den Erfolg.
2. **F002 (`anleitung`, `engine/konnektor.py`):** Der Satz zum Profil wird nur angehängt, wenn `zugang.get("konto_id")` gesetzt ist. Im reisebezogenen Zugang `{reise, person}` ohne Konto entfällt er, weil dort `mein_profil` nicht existiert. Die Bedingung hängt an `konto_id`, nicht am Baustein `profile`; im Konto-Zugang bleibt der Satz je Baustein unverändert (profile-12 Test 14).
3. **F003 (`profil_setzen`, `engine/konten.py`):** Am Anfang der Schreibtransaktion läuft `BEGIN IMMEDIATE` (Muster `reisespeicher._transaktion`), damit `COUNT(*)` und `INSERT` unter derselben Schreibsperre stehen; der Zweig „vorhandenen Eintrag ändern“ nutzt dieselbe Transaktion. `with v:` committet bzw. rollt wie bisher zurück. Vor dem Bauen prüfen, dass `db()` beim ersten Öffnen (Tabellen anlegen) keine offene Transaktion hinterlässt, sonst Fehler „cannot start a transaction within a transaction“; der Test mit frischer Datenbank deckt das ab. Die Wartezeit der Verbindung (`timeout=10`) bleibt.
4. **F004 (`engine/tests/conftest.py`):** Im autouse-Fixture `rueckfall_deutsch` wird zusätzlich `anmeldung._anfrage.sprache` gelöscht (`monkeypatch.delattr(..., raising=False)`), und zwar nur, wenn `anmeldung` schon in `sys.modules` ist (kein Import-Nebeneffekt). Ursache ist Zustand zwischen Tests im selben Thread, deshalb Fix im Fixture und nicht im Einzeltest.
5. **Nachzug `docs/specs/konnektor/profile-12.md` (Teil der Umsetzung, nicht jetzt):** Punkt 7: „Setzen zählt zur Schreibgrenze je Konto“ wird präzisiert zu „nur ein angenommener Eintrag zählt; abgelehnte Einträge (leer, zu lang, unbekannte oder fremde `PR-<n>`, Profil voll) zählen nicht, die Grenze selbst lehnt weiterhin vor dem Schreiben ab“. Punkt 12 und AC-6 nennen, dass der Anleitungssatz zum Profil nur im Konto-Zugang erscheint, nicht im reisebezogenen Zugang ohne Konto. Test 10 und Test 14 bekommen je einen Halbsatz dazu. Änderung im Changelog von `profile-12` vermerken.

## Test Plan

### Automated Tests (TDD RED)

Alle neuen Tests liegen vor der Korrektur rot vor.

- [ ] `engine/tests/test_profil.py::test_abgelehnter_eintrag_zaehlt_nicht_zur_schreibgrenze` (F001): GIVEN Schreibgrenze je Konto auf 2 und ein Konto ohne Zähler WHEN `profile_entry_set` mit leerem Text, mit zu langem Text und mit unbekannter `PR-<n>` je abgelehnt wird THEN bleibt der Zähler des Kontos unverändert; WHEN danach zwei gültige Einträge gesetzt werden THEN gelingen beide.
- [ ] `engine/tests/test_profil.py::test_angenommener_eintrag_zaehlt_zur_schreibgrenze` (F001, Gegenprobe): GIVEN Schreibgrenze 1 WHEN ein gültiger Eintrag gesetzt wird THEN zählt er; WHEN ein zweiter folgt THEN wird er von der Schreibgrenze abgelehnt, nichts gespeichert.
- [ ] `engine/tests/test_profil.py::test_profil_voll_zaehlt_nicht` (F001): GIVEN Obergrenze der Einträge erreicht WHEN ein weiterer Eintrag abgelehnt wird (`profil_voll`) THEN steigt der Zähler nicht.
- [ ] `engine/tests/test_profil.py::test_anleitung_ohne_konto_ohne_profilsatz` (F002): GIVEN der reisebezogene Zugang `{reise, person}` ohne `konto_id` WHEN `anleitung` erzeugt wird (Baustein `profile` an, aus und `bausteine` `None`) THEN fehlen `profil_nutzen` und `profil_nicht_nutzen` in der Anleitung; getestet an `beispielreise` und `stadtwochenende`.
- [ ] Bestehend, bleibt grün (Test 14 aus profile-12): GIVEN der Konto-Zugang mit Baustein `profile` an, aus oder `None` WHEN `anleitung` erzeugt wird THEN enthält sie den Satz unverändert.
- [ ] `engine/tests/test_profil.py::test_profil_setzen_beginnt_immediate_vor_dem_zaehlen` (F003, deterministisch): GIVEN `db` ist so gepatcht, dass die Verbindung ihre Anweisungen mitschreibt (Trace-Callback) WHEN `profil_setzen` ein neues Profil anlegt THEN steht `BEGIN IMMEDIATE` in der Mitschrift vor dem `COUNT`.
- [ ] `engine/tests/test_profil.py::test_profil_setzen_obergrenze_bei_gleichzeitigkeit` (F003): GIVEN Obergrenze 1 und ein Konto ohne Einträge WHEN zwei Threads hinter einer Barriere gleichzeitig `profil_setzen` mit Neuanlage aufrufen THEN gelingt genau einer, der andere bekommt `profil_voll`, und das Konto hat genau einen Eintrag. Der Thread-Test allein ist ohne Sperre nur wahrscheinlich rot, der Trace-Test belegt die Reihenfolge sicher.
- [ ] `engine/tests/test_profil.py::test_profil_setzen_frische_datenbank` (F003): GIVEN eine noch nicht angelegte Kontendatenbank WHEN `profil_setzen` als erster Zugriff läuft THEN gelingt es ohne Fehler „cannot start a transaction within a transaction“.
- [ ] `engine/tests/test_anmeldung.py::test_seitensprache_frueherer_test_stoert_nicht` (F004): GIVEN ein vorheriger Test setzt im selben Thread `anmeldung._anfrage.sprache` auf `en` WHEN der nächste Test beginnt THEN ist `anmeldung.sprache_der_seite()` wieder die Vorgabe und `meldungen_ordnen` liefert `texte.VORGABE`. Zwei Tests in fester Reihenfolge (erster setzt, zweiter prüft), damit der Fixture-Fix belegt ist.
- [ ] Bestehend, bleibt grün und läuft unabhängig von der Reihenfolge: `test_anmeldung::test_pruefungen_buendeln_je_reise_und_tag`, auch mit `-p no:randomly` und in umgekehrter Reihenfolge der Datei.

## Acceptance Criteria

- **AC-1 (F001):** Given ein Konto mit Schreibgrenze und ein abgelehnter `profile_entry_set` (leer, zu lang, unbekannte oder fremde `PR-<n>`, Profil voll) / When danach weitere gültige Einträge gesetzt werden / Then hat der abgelehnte Aufruf nicht zur Schreibgrenze gezählt. Test: `test_abgelehnter_eintrag_zaehlt_nicht_zur_schreibgrenze`, `test_profil_voll_zaehlt_nicht`.
- **AC-2 (F001):** Given die Schreibgrenze ist erreicht / When `profile_entry_set` aufgerufen wird / Then wird vor dem Schreiben abgelehnt, nichts gespeichert, und angenommene Einträge zählen weiterhin. Test: `test_angenommener_eintrag_zaehlt_zur_schreibgrenze`, bestehender Test 10 aus profile-12.
- **AC-3 (F002):** Given der reisebezogene Zugang ohne Konto / When die Anleitung erzeugt wird / Then enthält sie keinen Satz zum Profil. Test: `test_anleitung_ohne_konto_ohne_profilsatz`.
- **AC-4 (F002):** Given der Konto-Zugang / When die Anleitung je Baustein `profile` (an, aus, `None`) erzeugt wird / Then bleibt der Satz unverändert (profile-12 Test 14 grün).
- **AC-5 (F003):** Given Obergrenze 1 und zwei gleichzeitige Neuanlagen / When beide `profil_setzen` aufrufen / Then gelingt genau eine, die andere bekommt `profil_voll`, das Konto hat einen Eintrag. Test: `test_profil_setzen_obergrenze_bei_gleichzeitigkeit`.
- **AC-6 (F003):** Given `profil_setzen` legt einen Eintrag neu an / When die Anweisungen der Verbindung mitgeschrieben werden / Then steht `BEGIN IMMEDIATE` vor dem `COUNT`; auch eine frische Datenbank führt zu keinem Transaktionsfehler. Test: `test_profil_setzen_beginnt_immediate_vor_dem_zaehlen`, `test_profil_setzen_frische_datenbank`.
- **AC-7 (F004):** Given ein früherer Test hat `anmeldung._anfrage.sprache` im selben Thread gesetzt / When `test_pruefungen_buendeln_je_reise_und_tag` läuft / Then ist das Ergebnis dasselbe wie in Einzelausführung, in jeder Reihenfolge. Test: `test_seitensprache_frueherer_test_stoert_nicht` und der bestehende Test.
- **AC-8:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen; Ausnahmelisten in `test_texte.py` nicht länger, `deploy.sh` unverändert.
- **AC-9:** Given der Nachzug / When `profile-12` gelesen wird / Then nennt Punkt 7 „nur ein angenommener Eintrag zählt“ und die Anleitung gilt nur im Konto-Zugang (Textprüfung beim Abschluss).

## Definition of Done

- [ ] Neue Tests rot bestätigt, danach Korrektur, Tests grün
- [ ] Gesamtlauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün
- [ ] `profile-12` nachgezogen (Punkt 7, Punkt 12/AC-6, Changelog)
- [ ] Pflichtprüfungen der CI grün, ausgeliefert
- [ ] Issue #578 mit Abschlusskommentar je Befund geschlossen

## Risks

- **F001:** Die Reihenfolge darf die Ablehnung durch die Grenze nicht aufweichen: `schreibgrenze` prüft weiter vor dem Schreiben. Ein Fehler beim Zählen nach erfolgreichem Schreiben darf den Eintrag nicht rückgängig machen; er wird wie bei den übrigen Werkzeugen behandelt.
- **F002:** Eine Bedingung am Baustein statt an `konto_id` würde Test 14 brechen; deshalb an `konto_id` geknüpft.
- **F003:** `BEGIN IMMEDIATE` in einer Verbindung mit offener impliziter Transaktion schlägt fehl; daher der Test mit frischer Datenbank. Längere Sperre ist unkritisch (kurze Transaktion, WAL, `timeout=10`); Lesezugriffe anderer Verbindungen blockieren nicht.
- **F004:** Ein zu weit gefasstes Zurücksetzen könnte Tests stören, die die Seitensprache bewusst vorbelegen; das Fixture läuft vor dem Test, Tests setzen den Wert selbst. Importreihenfolge: kein Import von `anmeldung` im Fixture.
- Kein Datenformat betroffen, daher kein `nachziehen` und keine Umstellung bestehender Reisen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Fehlerbehebung innerhalb bestehender Muster (Schreibgrenze #380, `BEGIN IMMEDIATE` wie im Reisespeicher, ADR-0009); keine neue Grundform, kein neues Datenformat, keine Schnittstellenänderung.

## Changelog

- 2026-11-21: Initial spec created (Entwurf) für #578.
