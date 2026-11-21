# Context: fix-578-profil-nacharbeiten

## Request Summary
Vier kleine Befunde aus der unabhängigen Prüfung von #12 (Profile) beheben: Zählen erst nach gültigem Eintrag (F001),
Profil-Satz der Anleitung nur im Konto-Zugang (F002), Obergrenze der Profileinträge atomar (F003), reihenfolgeabhängiger
Test stabil (F004).

## Related Files
| File | Relevance |
|------|-----------|
| engine/konnektor.py `profil_werkzeug` (~2716) | F001: `schreiben_vormerken` vor `profil_setzen`; ein abgelehnter Eintrag (leer, zu lang, unbekannte PR-, Profil voll) zählt trotzdem |
| engine/konnektor.py `anleitung` (~3362, Satz ~3406) | F002: `profil_nutzen`/`profil_nicht_nutzen` wird immer angehängt, auch beim reisebezogenen Zugang `{reise, person}` ohne `konto_id` (initialize ~3605), wo es `mein_profil` nicht gibt |
| engine/konten.py `profil_setzen` (~758) | F003: `COUNT(*)` und `INSERT` in impliziter Transaktion (sqlite3 deferred); zwei Neuanlagen gleichzeitig können die Grenze um eins überschreiten |
| engine/konten.py `db()` (~195) | Verbindung, `timeout=10`, WAL |
| engine/reisespeicher.py `_transaktion` (~401) | Vorbild für `BEGIN IMMEDIATE` mit Rollback |
| engine/anmeldung.py `_anfrage`, `sprache_der_seite`, `tx` (~41–50) | F004: thread-lokale Seitensprache; ein früherer Test im selben Thread hinterlässt `_anfrage.sprache` |
| engine/tests/conftest.py (~70–83) | setzt je Test `texte.VORGABE_REISE="de"` und löscht `texte._aufruf.sprache`, aber nicht `anmeldung._anfrage.sprache` |
| engine/tests/test_anmeldung.py `test_pruefungen_buendeln_je_reise_und_tag` (~549) | F004: erwartet `texte.VORGABE`, `meldungen_ordnen` nutzt `sprache_der_seite()` |
| engine/tests/test_profil.py | bestehende Profil-Tests (Anleitung je Baustein ~326, Schreibgrenze Test 10) |

## Existing Patterns
- Schreibgrenze in `frieda_werkzeug`: `schreibgrenze(k)` prüfen, dann `schreiben_vormerken(k)`, dann Werkzeug.
- Atomare Schreibtransaktion: `BEGIN IMMEDIATE` + commit/rollback (reisespeicher).
- Testisolation thread-lokaler Sprache: autouse-Fixture in conftest mit `monkeypatch.delattr(..., raising=False)`.

## Dependencies
- Upstream: `konten.schreibgrenze`, `konten.schreiben_vormerken`, `konten.KontoFehler`, `instanz.grenze_profil_eintraege`.
- Downstream: Konnektor „Frieda“ (Werkzeug `profile_entry_set`), Mein Konto (ruft `profil_setzen`? nur `profil_aendern`), Anleitung beim `initialize` beider Zugänge.

## Existing Specs
- `docs/specs/konnektor/profile-12.md` — Punkt 7 (Setzen zählt zur Schreibgrenze), Test 10, AC-3; Anleitung je Baustein (Test 14).
- `docs/specs/konnektor/trennung-grenzen-380.md` — Schreibgrenze je Konto.

## Risks & Considerations
- F001: „Grenze erreicht“ muss weiterhin vor dem Schreiben ablehnen; nur das Zählen wandert hinter den Erfolg.
- F002: Anleitung im Konto-Zugang (`anleitung_frieda` → `anleitung` mit `konto_id`) muss den Satz unverändert behalten (Test 14).
- F003: `with v:` des sqlite3-Kontextmanagers committet/rollt zurück; `BEGIN IMMEDIATE` explizit davor setzen, ohne den Kontextmanager zu brechen.
- F004: Ursache ist Zustand zwischen Tests; Fix in conftest (Ursache), nicht nur im einen Test.
- Kein Format der Reisedaten betroffen, kein `nachziehen` nötig; keine Texte geändert.

## Analysis

### Type
Bug (vier kleine Befunde aus der Prüfung von #12, alle niedrig). Umfang klein und vollständig im Kontext belegt; die
Codestellen wurden direkt gelesen, auf Explore-/Plan-Subagenten wurde deshalb verzichtet.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/konnektor.py `profil_werkzeug` (~2734–2740) | MODIFY | F001: `schreibgrenze` bleibt vor dem Schreiben; `schreiben_vormerken(k)` wandert hinter ein erfolgreiches `profil_setzen` (abgelehnte Einträge – leer, zu lang, unbekannte/fremde PR-, Profil voll – zählen nicht) |
| engine/konnektor.py `anleitung` (~3405–3406) | MODIFY | F002: Profil-Satz (`profil_nutzen`/`profil_nicht_nutzen`) nur, wenn `zugang.get("konto_id")` gesetzt ist; im reisebezogenen Zugang (initialize ~3605) entfällt er ganz |
| engine/konten.py `profil_setzen` (~764–775) | MODIFY | F003: im Zweig Neuanlage (und einheitlich für beide Zweige) `v.execute("BEGIN IMMEDIATE")` am Anfang der Transaktion, damit COUNT und INSERT unter derselben Schreibsperre laufen; `with v:` committet bzw. rollt zurück wie bisher |
| engine/tests/conftest.py `rueckfall_deutsch` (~72–83) | MODIFY | F004: zusätzlich `anmeldung._anfrage.sprache` löschen (nur wenn `anmeldung` schon in `sys.modules`, kein Import-Seiteneffekt) |
| engine/tests/test_profil.py | MODIFY | neue Tests: abgelehnter Eintrag zählt nicht zur Schreibgrenze; Anleitung ohne Konto ohne Profil-Satz, mit Konto unverändert; Obergrenze unter Gleichzeitigkeit |
| engine/tests/test_anmeldung.py | MODIFY (ggf.) | Reihenfolge-Test: Seitensprache eines früheren Tests im selben Thread setzen, danach `meldungen_ordnen` → `texte.VORGABE` (belegt den conftest-Fix) |
| docs/specs/konnektor/profile-12.md | MODIFY | Punkt 7 präzisieren („nur ein angenommener Eintrag zählt“), Anleitung nur im Konto-Zugang |

### Scope Assessment
- Files: 4 Code/Test-Dateien + 1 Spec
- Estimated LoC: +60/-5 (überwiegend Tests)
- Risk Level: LOW — isolierte Stellen, keine Datenformate, keine Texte, kein `nachziehen`

### Technical Approach
- F001: Reihenfolge `bestaetigt` → `schreibgrenze` → `profil_setzen` → `schreiben_vormerken`. Gleiches Muster wie
  „erst prüfen, dann zählen“; die Grenze lehnt weiterhin vor dem Schreiben ab. Restfenster (zwei gleichzeitige Aufrufe
  am Rand der Grenze) ist dasselbe wie bei allen anderen Schreibwerkzeugen und nicht Teil dieses Befunds.
- F002: Bedingung an `konto_id` knüpfen, nicht an die Bausteine. Test 14 (Konto-Zugang je Baustein) bleibt unverändert grün.
- F003: Muster `BEGIN IMMEDIATE` aus `reisespeicher._transaktion`. `konten.db()` nutzt den Standard-Isolationsmodus
  (implizite Transaktionen erst vor INSERT/UPDATE/DELETE); `PRAGMA foreign_keys`/`journal_mode` öffnen keine Transaktion,
  ein explizites `BEGIN IMMEDIATE` direkt nach dem Öffnen ist daher zulässig. Vor dem Bauen prüfen: `db()` legt beim
  ersten Öffnen Tabellen an – darf danach keine offene Transaktion hinterlassen (sonst „cannot start a transaction within a
  transaction“); Test mit frischer Datenbank deckt das ab. Test-Idee deterministisch: Grenze auf 1, zwei Threads mit
  Barriere rufen `profil_setzen` gleichzeitig auf → genau einer gelingt, einer bekommt `profil_voll`; zusätzlich per
  `sqlite3`-Trace (oder Patch von `db`) belegen, dass `BEGIN IMMEDIATE` vor dem COUNT läuft (der Thread-Test allein ist
  ohne Sperre nur wahrscheinlich, nicht sicher rot).
- F004: Ursache ist thread-lokaler Zustand zwischen Tests → Fix im autouse-Fixture (Ursache), nicht im Einzeltest.
  Die weiteren thread-lokalen Zustände (`konnektor._zone`, `konnektor._gesichert`) sind nicht Teil des Befunds; beim
  Bauen kurz prüfen, ob sie dasselbe Muster haben, und nur bei Befund mitnehmen.

### Dependencies
- `konten.schreibgrenze`, `konten.schreiben_vormerken`, `konten.KontoFehler`, `instanz.grenze_profil_eintraege`
- `texte._aufruf`, `anmeldung._anfrage`, `anmeldung.sprache_der_seite`, `anmeldung.meldungen_ordnen`
- Konnektor-Werkzeug `profile_entry_set`, Anleitung beim `initialize` beider Zugänge

### Open Questions
- keine (reine Fehlerbehebung, keine Produktentscheidung, keine sichtbaren Texte)
