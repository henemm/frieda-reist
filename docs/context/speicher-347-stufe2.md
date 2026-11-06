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
