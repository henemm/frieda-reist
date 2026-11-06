# Context: Speicher Stufe 2 – Schreibweg über die Datenbank statt Git (#347)

## Request Summary

Der Schreibweg (Konnektor → `engine/schreiben.py`) soll jeden Schreibvorgang als eine Transaktion im Reisespeicher
(`engine/reisespeicher.py`, ADR-0009, Stufe 1 auf `main`) ablegen statt als Commit mit fetch/rebase/push. Die Arbeitskopie
(YAML mit Kommentaren) entsteht aus der Datenbank, Rolle prüfen, Werkzeug anwenden und Probebau bleiben. `stand.py` liest Stand-Nummer
und Änderungsliste aus der Versionstabelle; `neu.py` (Anlegen) und `nachziehen` schreiben über dieselbe Schicht. Dazu ein
Messlauf (Mittel, p90, p99, Zeitüberschreitungen; auch mehrere Reisen gleichzeitig).

Akzeptanz (Issue): kein `git` mehr im Schreibweg und in `stand.py` (Test); alle Tests ohne echte Reisen grün mit beiden
Beispielreisen; Messwerte im Issue (keine Zeitüberschreitungen, p99 deutlich unter 25 s); abgelehnte Vorgänge (Rolle,
Probebau, Sperre) lassen den Stand unverändert (Test).

## Related Files

| Datei | Relevanz |
|-------|----------|
| `engine/reisespeicher.py` (455 Z.) | Schnittstelle aus Stufe 1: `vorgang_schreiben`, `stand_nummer`, `aktueller_stand(bis)`, `vorgang_eingetragen(kennung)`, `verlauf(n)`, `exportieren`, `importieren(ab)`, `VorgangVorhanden`, `db()` (WAL, Trigger, Authorizer). Ort `instanz.speicher()` |
| `engine/schreiben.py` (4561 Z.) | Git-Schicht: `git()` Z.199, `Schreiber.vorbereiten` Z.4148 (fetch, worktree add/reset/clean/checkout, submodule update), `schreiben` Z.4202 (Rücksetzen per git checkout/clean bei Ablehnung, `git status` für „nichts geändert“, Commit-Nachricht mit `Frieda-Person`/`Frieda-Vorgang`, `hochladen`), `buchung_im_repo` Z.4268 (git show origin/main), `hochladen` Z.4285 (push/rebase dreimal), `vorgang_eingetragen` Z.4362 (git log --grep), `nach_abbruch` Z.4378, `git_sperren_raeumen` Z.4415, `vorgang` Z.4434 (Sperre je Reise, Arbeitskopie je Reise `<arbeit>-<reise>`, startet `anwenden` als Unterprozess **mit dem Code der Arbeitskopie**), `Dienst.do_GET /gesund` (prüft `.git`), `main vorbereiten`. Konstanten `ZEIT_GESAMT=25`, `ZEIT_SPERRE=3`, `ZEIT_PRUEFUNG=3` |
| `engine/stand.py` (268 Z.) | `nummer()` = `git rev-list --count`, `aenderungen()` = `git log` mit Trailer `Frieda-Person`, `fuer_seite()` (vom Bau genutzt), `gesichert_schreiben()` (Dienstordner `reise-stand/<reise>.gesichert.json`), `lesen()`/`enthalten()` (Konnektor `publish_status`, Rückmeldedienst `api/stand`) |
| `engine/neu.py` (1152 Z.) | `anlegen()` und `nachziehen()` schreiben direkt per `write_text` in einen Reiseordner; Befehl `nachziehen` läuft im Workflow „Software nachziehen“ des Reisen-Repos (Commit im Repo) |
| `engine/bauen.py` | ruft `stand.fuer_seite(reise_dir, daten)` → Stand-Nummer und Änderungsliste auf der Seite |
| `engine/konnektor.py` | ruft den Schreibweg per HTTP (`POST /<reise>/<werkzeug>`, `GET /<reise>/buchung/<B>`), liest `stand.lesen` für `publish_status` |
| `betrieb/veroeffentlichen.sh` | baut aus dem Git-Bauordner: fetch, ff-merge `origin/main`, Stand-Nummer per `git rev-list` (Z.73–79), geänderte Reisen per `git diff` (Z.116). **Liest nicht aus dem Speicher** – das ist Stufe 3 (#348) |
| `betrieb/deploy.sh` | Modullisten `SB_MODULE` (Z.25), `KN_MODULE`, `RM_MODULE`; `reisespeicher.py` fehlt noch (Kommentar #347: kommt jetzt hinein); `test_betrieb.py` prüft die Liste |
| `docs/adr/0009-reisespeicher.md` | Entscheidung, Konsequenzen für Stufe 2 und 3 |
| `docs/betrieb.md` | Reise-Stand, Server-Backup `<FR_SPEICHER>/sicherung/` als Pflicht der Instanz |
| Tests mit echtem Git: `test_schreiben.py`, `test_stand.py`, `test_betrieb.py`, `test_software_nachziehen.py`, `test_bauen.py`, `test_pwa.py`, `test_art_uebersicht.py`, `test_reisespeicher.py`, `test_protokolle_ohne_pfade.py` | Fixtures bauen Git-Repos mit `origin`; müssen auf Speicher-Fixtures umgestellt werden (Schreibweg, Stand) |

## Existing Patterns

- **Speicherzugriff:** `reisespeicher.db()` mit `closing`, `_transaktion` (BEGIN IMMEDIATE), Sperrfehler als `sqlite3.OperationalError`; Konten liegen ebenso in SQLite (`konten.py`, ADR-0005).
- **Sperre je Reise:** `fcntl.flock` auf `<FR_SPERREN>/<instanz>-schreiben-<reise>.lock`, Wartezeit `ZEIT_SPERRE`; bleibt laut Issue.
- **Frist:** `befehl_mit_frist` beendet den Unterprozess `anwenden` samt Enkeln nach `ZEIT_GESAMT`; danach `nach_abbruch` mit Kennung `FR_VORGANG` (heute `secrets.token_hex(6)`).
- **Byte-gleicher Export/Import** in Stufe 1 (`exportieren`, `_ordner_lesen`): Grundlage für „Arbeitskopie aus der DB“ und „geänderte Dateien zurück“.
- **Änderungsliste:** erste Zeile „<Titel>: <was>“, Person aus Trailer; `verlauf()` liefert schon `nummer=stand, zeit, was=titel, wer` (Kommentar im Issue).
- **Texte** nur aus `texte_<sprache>.py` (ADR-0006); Commit-Fuß `inhalt.schreiben.commit_fuss` wird zum Grund/Titel des Vorgangs.

## Dependencies

- Upstream: `reisespeicher.py`, `instanz.py` (`speicher()`, `dienst()`, `seiten()`), `bauen.py` (Probebau, `Bauer.eck`), `reise.py` (Rollen), `texte`, ruamel/yaml der Werkzeuge.
- Downstream: Konnektor (Antwortfelder `commit`, `stand.gesichert`, `stand.veroeffentlicht`, `id`, `hinweise`), `bauen.py` (`reise_stand` auf der Seite), Rückmeldedienst `api/stand`, `veroeffentlichen.sh` (Stand-Nummer, Bauordner), Workflow „Software nachziehen“ der Reisen-Repos, Tests der Instanzen.

## Existing Specs

- `docs/specs/betrieb/reisespeicher-346.md` – Stufe 1, Schnittstelle verbindlich
- `docs/context/speicher-346-stufe1.md` – Analyse mit Vorschlag der Schnittstelle (auch im Issue-Kommentar)
- Specs zum Schreibweg/Reise-Stand unter `docs/specs/` (#223, #226, #229, #258) – für die Analyse zu sichten

## Risks & Considerations

1. **Übergang ohne Bruch im Betrieb (Kern der Analyse):** Heute wird nach einem Schreibvorgang `veroeffentlichen.sh` angestoßen, das aus Git baut. Schreibt Stufe 2 nur noch in die DB, sieht der Bau die Änderung erst mit Stufe 3. Epic-Rahmen: „eine Quelle der Wahrheit je Reise, kein Doppelschreiben; der Schalter liegt in der Reise bzw. Instanz“. Ein Merge nach `main` erreicht die Instanzen über „Software nachziehen“ automatisch. Die Analyse muss klären: Schalter je Instanz/Reise mit Git als Vorgabe bis Stufe 3/5 (dann widerspricht „kein git im Schreibweg“ der Akzeptanz, solange der Altweg lebt) **oder** Stufe 2 liefert den Speicherweg nur für Reisen, die im Speicher liegen, und der Bau bekommt in Stufe 2 schon einen Export aus der DB **oder** Stufe 2 und 3 gehen gemeinsam nach `main`. Entscheidung gehört ggf. zum PO (Spec-Freigabe).
2. **Software-Stand der Arbeitskopie:** Heute führt `vorgang` `anwenden` mit dem Code aus der Git-Arbeitskopie aus (Software passend zum Stand von `main` der Reisen). Ohne Git läuft der installierte Code (`deploy.sh`); dann muss `schreiben.py` mit allen von ihm geladenen Modulen (`bauen.py`, `neu.py`, `routen.py`, …) in `<FR_DIENST>` liegen oder aus dem Bauordner kommen – betrifft `SB_MODULE` und den Test dazu.
3. **Kennung und Nachprüfung:** `kennung` erzeugt der Aufrufer vor dem Unterprozess; `vorgang_eingetragen(kennung)` ersetzt `git log --grep`. Wird der Unterprozess nach `BEGIN IMMEDIATE` getötet, rollt SQLite zurück – Antwort „nicht eingetragen“ ist dann sicher.
4. **Abgelehnte Vorgänge:** Rücksetzen per `git checkout/clean` entfällt; die Arbeitskopie ist frisch aus der DB je Vorgang (temporärer Ordner) – eine Ablehnung schreibt nichts. Test: Stand-Nummer und Inhalt unverändert nach Rolle/Probebau/Sperre.
5. **Neue Reise (`reise_anlegen`, REPO_WERKZEUGE):** braucht noch keinen Speicher-Eintrag; Kennung der neuen Reise kommt aus `reisen/` (IDs, Ordnername) – aus der DB ableiten (Reisen-Liste im Speicher).
6. **`buchung_im_repo`:** `git show origin/main:…routen.yaml` → `aktueller_stand(reise)`.
7. **`/gesund`:** prüft heute `.git`; künftig Datenbank erreichbar.
8. **Antwortfeld `commit`:** Konnektor und Instanz-Tests könnten es nutzen → Vorgangs-Nummer statt Hash; Schnittstelle für Instanzen, vor dem Vorspulen Instanz-Tests laufen lassen (CLAUDE.md).
9. **`stand.py` ohne Git:** `fuer_seite()` liest heute aus dem Ordner; künftig aus dem Speicher – aber der Bau kennt nur den Ordner. Zuordnung Ordner → Reise (Name) und Instanz-Speicher nötig; ohne Speichereintrag (Beispielreisen im Repo, CI) bleibt die Nummer `None` wie heute ohne Git.
10. **`neu.py nachziehen`:** läuft heute im Reisen-Repo per Workflow; „über dieselbe Schicht“ heißt: Arbeitskopie aus DB, nachziehen, geänderte Dateien als Vorgang (Werkzeug `nachziehen`). Ob das in Stufe 2 oder 3 (Betrieb/Nachziehen) gehört, klärt die Analyse.
11. **Messlauf:** Vergleich zu heute (379 Vorgänge, Mittel 2,7 s, p99 ~25 s mit 5 Zeitüberschreitungen); Werkzeug/Skript für Messlauf mit beiden Beispielreisen, auch parallel; SQLite sperrt die ganze Datei (WAL, 10 s Wartezeit).
12. **Vorbedingung Betrieb:** Server-Backup sichert `<FR_SPEICHER>/sicherung/` (henemm-infra), bevor eine Instanz umschaltet.
13. **Umfang:** `schreiben.py` hat 54 Git-Stellen, aber die rund 3000 Zeilen Werkzeuge bleiben unverändert; Hauptarbeit in `Schreiber`, `vorgang`, `stand.py` und den Test-Fixtures.

## Analysis

### Type
Feature (Umbau des Schreibwegs, Teil des Epics #345)

### Befunde, die den Ansatz bestimmen

- Ein Merge nach `main` erreicht alle Instanzen automatisch („Software nachziehen“). Bis Stufe 3 (#348) baut `veroeffentlichen.sh` nur aus Git. Schriebe eine Reise ab dem Merge in den Speicher, bliebe ihre Seite stehen; außerdem verlangt das Epic vor dem Umschalten einer Reise Vergleichslauf, Sicherung außer Haus und Rückspielversuch. Deshalb darf der Merge das Verhalten keiner laufenden Instanz ändern.
- `stand.lesen`/`enthalten` vergleichen über Stand-Nummern, nicht über den Commit; der Konnektor liest das Antwortfeld `commit` nicht (nur `gesichert.json` speichert es).
- Heute läuft `anwenden` mit dem Code der Git-Arbeitskopie (`<arbeit>/engine/schreiben.py`), der Dienst selbst aus `<FR_DIENST>` (ExecStart `__DIENST__/schreiben.py dienst`). Ohne Git-Arbeitskopie braucht `anwenden` den installierten Code samt Probebau (`bauen.py`, `routen.py`, `gpx.py`, `karte.py`, `reisespeicher.py`, Vorlagen, `vendor/`).
- `stand.fuer_seite` wird vom Bau aufgerufen (`bauen.py:1229`, auch im Probebau) und ruft Git; „kein git in `stand.py`“ verlangt, dass der Git-Teil auszieht.
- Stufe-1-Test `test_reisespeicher.py:570` (AC-13: Schreibweg bindet den Speicher nicht ein) wird bewusst ersetzt: `schreiben.py`, `stand.py`, `deploy.sh` dürfen ihn jetzt nennen, `konnektor.py` und `rueckmeldungen.py` weiter nicht (Stufe 3).
- `reisespeicher` importiert `stand.zeit_iso`: `stand.py` darf `reisespeicher` nur in Funktionen importieren (Zirkel).
- Lücken der Stufe-1-Schnittstelle: kein Schutz gegen verlorene Änderungen zwischen Export und Schreiben (Schreiber ohne Reise-Sperre: `importieren`, später Nachziehen), keine Einzeldatei-Abfrage (`buchung_im_repo` lüde sonst alle Fotos), keine Reisenliste (`reise_anlegen` braucht sie für IDs/Kollision), `db()` mit festem `timeout=10` (muss sich nach der Restzeit der 25-s-Frist richten).
- Spec `docs/specs/betrieb/schreibweg-zeitgrenzen.md` (Fristen 3/25/3 s, Meldungstabelle 200/504/429/422) ist git-bezogen formuliert; Meldungen bleiben, die Nachprüfung wird lokal.

### Auslieferungs-Optionen

| | Bruchrisiko im Betrieb | Akzeptanz #347 | Aufwand | Epic-Rahmen |
|---|---|---|---|---|
| A Schalter je Reise, Git als Vorgabe, Altweg bis Stufe 5 | gering: ohne Einstellung ändert sich nichts | erfüllt, wenn der Git-Weg in eigene Module zieht (Auslegung durch PO) | mittel, ca. +1300/−350 Zeilen | passt („Schalter in Reise bzw. Instanz“, Umschalten erst nach Stufe 3/5) |
| B Git-Weg sofort ersetzen | hoch: Seiten frieren ein, Reisen fehlen im leeren Speicher | formal voll | wie A plus Notbehelfe | verletzt Vorbedingungen des Umschaltens |
| C Stufe 2 und 3 gemeinsam | mittel bis hoch, sehr breite Prüfung | erfüllt | groß | Schalter bleibt trotzdem nötig (Instanzen schalten in Stufe 5) |

### Technical Approach (Empfehlung: Option A)

1. **Schalter je Reise als Einstellung der Instanz** (`FR_SPEICHERREISEN=<reise>,…` in `einstellungen.env`, Vorgabe leer = Git). Eine Reise im Speicherweg braucht zusätzlich einen Eintrag im Speicher, sonst 503 ohne Wirkung (nie aus einer leeren Arbeitskopie schreiben). Der Git-Weg lehnt eine Reise der Liste ab (kein Doppelschreiben). Nicht „Eintrag im Speicher = umgeschaltet“, weil Import und Vergleichslauf (Stufe 3) den Eintrag vorab brauchen und sonst unbemerkt umschalten würden; nicht in der Reise selbst, weil der Schalter dann in dem Speicher läge, den er auswählt.
2. **Git-Weg zieht aus:** `git()`, `vorbereiten`, `hochladen`, `git_sperren_raeumen`, Git-Nachprüfung, Git-`buchung_im_repo`, Git-Teil von `/gesund` nach `engine/schreiben_git.py`; `nummer`, `aenderungen`, `git()` aus `stand.py` nach `engine/stand_git.py`, nur bei Bedarf geladen. Entfällt in Stufe 5.
3. **Speicherweg je Vorgang:** Sperre je Reise (flock, wie heute) → Kennung vor dem Unterprozess (wie heute) → Arbeitskopie: temporärer Ordner, `exportieren(reise, tmp/reisen/<reise>)`, Basis-Stand merken → `anwenden` im Unterprozess mit dem Code aus `<FR_DIENST>` (Rolle, Werkzeug, Probebau unverändert) → geänderte Dateien gegen `aktueller_stand(reise, basis)` → `vorgang_schreiben(..., erwartet=basis)` in einer Transaktion (Titel/Text/Fuß der Commit-Nachricht werden `titel`/`grund`, Person `wer`, Rolle `rolle`) → Ordner löschen. Ablehnung schreibt nichts; leerer Vorgang → `schreiben.schreiben.4`.
4. **Nach Abbruch:** `vorgang_eingetragen(kennung)` statt fetch + `git log --grep`; ein getöteter Unterprozess rollt SQLite zurück. Meldungstabelle der Zeitgrenzen-Spec bleibt.
5. **Zusätze zur Speicher-Schnittstelle:** `vorgang_schreiben(..., erwartet=None)` (Konflikt bei abweichendem Stand), `db(timeout=…)`, `datei(reise, pfad)`, `reisen()`.
6. **Weitere Stellen:** `buchung_im_repo` → `datei(reise, "routen.yaml")`; `/gesund` → Datenbank `SELECT 1` (Git-Weg wie heute); `reise_anlegen` → Arbeitskopie mit den bekannten Reisen als leere Ordner, Sperre „reisen“, erster Vorgang der neuen Reise; Antwortfeld `commit` bleibt mit der Vorgangs-Nummer (`gesichert.json` ebenso); `stand.fuer_seite` → Speicher-Reise aus `verlauf`/`stand_nummer`, Git-Reise aus `stand_git`, Probebau ohne Stand.
7. **Betrieb:** `SB_MODULE` in `deploy.sh` um `reisespeicher.py` und die Module des Probebaus samt Vorlagen/`vendor/` erweitern, Listentest (`test_texte.py:313`) mitziehen. `veroeffentlichen_anstossen` bleibt; für Speicher-Reisen zeigt `publish_status` bis Stufe 3 „wartet“ (Doku).
8. **„Kein git“ prüfbar:** statischer Test (in `schreiben.py` und `stand.py` kein git-Aufruf, kein Import von `*_git` auf Modulebene) und Laufzeittest mit `git`-Stub im PATH, der eine Marke schreibt: ein vollständiger Speicher-Vorgang einschließlich Probebau darf ihn nie aufrufen.
9. **Messlauf** (`betrieb/messlauf-schreibweg.py`, kein Test): temporäre Instanz, beide Beispielreisen plus Kopien unter anderem Namen; nacheinander und parallel (mehrere Reisen gleichzeitig, mehrere Vorgänge auf derselben Reise → 429 getrennt gezählt); Werkzeugmix; Mittel, p50, p90, p99, Maximum, 504/429/5xx, Export- und Probebauzeit einzeln; dasselbe Skript mit `--weg git` (lokaler Origin, also nur Richtwert) gegen `--weg speicher`. Belastbarer Wert: Lauf auf dem Server der Instanz mit einer erfundenen Testreise, die mit Fotos auf die Größe der größten echten Reise aufgefüllt ist (Fotos sind bis Stufe 4 Blobs in der Datenbank und treiben den Export). Werte ins Issue, daneben die Betriebswerte (379 Vorgänge, Mittel 2,7 s, p99 ≈ 25 s, 5 Zeitüberschreitungen).

### Affected Files (with changes)

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/schreiben.py` | MODIFY | Schalter, Speicherweg (Arbeitskopie aus Speicher, Transaktion, Nachprüfung, buchung, gesund, reise_anlegen); Git-Teile entfernt |
| `engine/schreiben_git.py` | CREATE | bisheriger Git-Weg (verschoben, bis Stufe 5) |
| `engine/stand.py` | MODIFY | Stand-Nummer und Änderungsliste aus dem Speicher; Git-Teil entfernt |
| `engine/stand_git.py` | CREATE | bisherige Git-Zählung (verschoben, bis Stufe 5) |
| `engine/reisespeicher.py` | MODIFY | `erwartet`, `db(timeout)`, `datei`, `reisen` |
| `engine/bauen.py` | MODIFY | Stand je Weg, Probebau ohne Stand |
| `engine/instanz.py` | MODIFY | Einstellung `FR_SPEICHERREISEN` |
| `engine/texte_*.py` | MODIFY | neue Meldungen (Speicher nicht erreichbar, Reise nicht im Speicher, Konflikt) |
| `betrieb/deploy.sh` | MODIFY | `SB_MODULE` erweitert |
| `betrieb/einstellungen.beispiel`, `docs/betrieb.md`, `docs/adr/0009-reisespeicher.md`, `docs/specs/betrieb/schreibweg-zeitgrenzen.md` | MODIFY | Schalter, Speicherweg, Nachprüfung lokal |
| `betrieb/messlauf-schreibweg.py` | CREATE | Messlauf |
| `engine/tests/test_schreiben_speicher.py` | CREATE | Speicherweg, Ablehnungen lassen Stand unverändert, Abbruch, kein git (statisch + Stub), beide Beispielreisen |
| `engine/tests/test_schreiben.py` (+ Nutzer der Fixture `repo`) | MODIFY | Fixture für beide Wege, wo sinnvoll |
| `engine/tests/test_stand.py`, `test_reisespeicher.py`, `test_texte.py`, `test_betrieb.py` | MODIFY | Stand aus Speicher; AC-13 ersetzen; Modulliste |

### Scope Assessment
- Files: ca. 20
- Estimated LoC: +1300 / −350 (ohne Doku)
- Risk Level: MEDIUM — zentraler Schreibweg, aber hinter einem Schalter mit Git als Vorgabe; ohne Einstellung bleibt der Betrieb unverändert.

### Dependencies
- Upstream: `reisespeicher.py` (Stufe 1), `instanz.py`, `bauen.py` (Probebau), `reise.py`, `texte`.
- Downstream: Konnektor (Antwortfelder unverändert), Rückmeldedienst `api/stand`, `bauen.py`, Tests der Instanzen (vor dem Vorspulen mit dem Branch laufen lassen).
- Betrieb: Server-Backup von `<FR_SPEICHER>/sicherung/` (henemm-infra) ist Pflicht, bevor eine Instanz eine Reise umschaltet; Rechte der Datenbankdatei (Modus 600, gehört dem ersten Öffner) für den Dienstbenutzer.

### Reihenfolge
1. Spec, Freigabe. 2. Tests rot (kein git, Ablehnungen, Abbruch, beide Beispielreisen). 3. Zusätze am Speicher. 4. Git-Weg verschieben, ohne Verhaltensänderung (alle Git-Tests grün). 5. Speicherweg. 6. `deploy.sh` und Listentests. 7. `bauen.py`. 8. Messlauf, Werte ins Issue. 9. Doku, ADR, Instanz-Tests.

### Entscheidungen des Product Owners (6.11.2026)
- „Kein git“ gilt für die Module: Git-Weg abtrennen (`schreiben_git.py`, `stand_git.py`), Schalter je Reise mit Git als Vorgabe, Altweg fällt mit Stufe 5. Prüfung statisch und per git-Stub.
- Nachziehen: Stufe 2 baut den gemeinsamen Baustein „Ordner vorher/nachher → ein Vorgang“ (auch für `reise_anlegen`); der Aufruf durch `neu.py nachziehen` kommt mit Stufe 3 (#348).

### Open Questions (PO, beantwortet)
- [x] Auslegung „kein git mehr im Schreibweg“: Gilt das für die Module `schreiben.py`/`stand.py` (Git-Weg lebt bis zum Umschalten in Stufe 5 in eigenen Modulen) oder für jede Instanz ab sofort (dann Option B oder C)? Empfehlung: Module, Option A.
- [x] `neu.py nachziehen` über die Speicherschicht: Issue nennt Stufe 2, das Epic legt Nachziehen auf dem Server in Stufe 3. Empfehlung: Stufe 2 baut den gemeinsamen Baustein „Ordner vorher/nachher → ein Vorgang“ (für `reise_anlegen` ohnehin nötig), der Aufruf durch Nachziehen kommt mit Stufe 3.
