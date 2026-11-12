# Context: software-weg-454

## Request Summary

Folge von #350 (Variante B aus `docs/context/speicher-stufe5-350.md`): Die Instanz holt die Software direkt aus diesem öffentlichen Repo. Das Reisen-Repo der Instanz wird reines Archiv, die Workflows der Instanz bei GitHub („Software nachziehen“, Tests) entfallen. Prüfung vor dem Deploy und Rückfall auf den letzten guten Stand bleiben, kein Handschritt beim Wechsel (#250).

## Heutige Anordnung (Stand 12.11.2026)

- **Bauordner** `FR_WURZEL` (Instanz: `<FR_SEITEN>/_bau`) ist ein Klon des privaten Reisen-Repos auf `main`; die Software ist darin das Submodul `frieda/`. Alle systemd-Units starten `<FR_WURZEL>/frieda/betrieb/<skript>`; `FR_PYTHON` ist `<FR_WURZEL>/engine/.venv/bin/python`.
- **Einstellungen** der Instanz liegen versioniert im Reisen-Repo: `betrieb/einstellungen.env` (darin `FR_SPEICHERREISEN`), `betrieb/melden.sh` (Meldeweg), `tests/` (Instanz-Tests: Betrieb, „privat“-Prüfung, Reisen). Geheimes in `<FR_DIENST>/betrieb.env`, `konten.env`.
- **Software-Weg:** `veroeffentlichen.sh` → `git fetch origin main` des Reisen-Repos → `software_anstossen` (`git ls-remote` auf main der Software, bei neuem Stand `gh workflow run software-nachziehen`) → Workflow im Reisen-Repo hebt den Submodul-Zeiger (Tor: `engine/tests`, Bau jeder Git-Reise, `neu.py nachziehen` für Git-Reisen) und committet → nächster Lauf: `git merge --ff-only`, `git submodule update`, Prüfung (`ci_nachweis`: Pflichtprüfungen des Software-Commits grün auf GitHub, sonst pytest auf dem Server), Deploy aller Reisen, Stempel `veroeffentlicht` = Commit des Reisen-Repos.
- **Software-Kennung** (`software_kennung`): `HEAD:frieda` im Bauordner; Reisen aus dem Speicher werden erst mit einer neuen Kennung nachgezogen, wenn der Git-Teil sie veröffentlicht hat (`veroeffentlicht` zeigt auf einen Commit mit dieser Kennung).
- **Rot-Datei** `veroeffentlichen-rot`: Commit des Reisen-Repos, Art (software|reise), Reisen; „Bekannter roter Stand“ hängt am Commit.
- **Anstoß von der Seite** (`_anstoss.json`, `anstoss_weitergeben`) startet denselben Workflow.
- **Monitor der Infrastruktur** prüft den Rückstand `.git/modules/frieda/HEAD` gegen `main` der Software (`git ls-remote`, > ~6 h) – Abhängigkeit in `henemm-infra/scripts/monitor.sh`.

## Stand der Reisen auf der Instanz

- 10 Reiseordner im Bauordner, 6 davon in `FR_SPEICHERREISEN` (alle echten Reisen und zwei Testreisen). 4 liegen nur noch in Git (Test- und Probereisen); vor dem Wechsel klären: in den Speicher übernehmen (Vergleichslauf + Umschaltung) oder vorgemerkt/gelöscht.
- **Lücke:** Neue Reisen (`trip_create`, `reise_anlegen`) gehen über den Git-Weg (`schreiben.py` wählt per `FR_SPEICHERREISEN`, eine neue Reise steht dort nicht). Ohne Reisen-Repo muss eine neue Reise im Speicher entstehen, und „im Speicher“ darf nicht mehr an einer Liste im versionierten Einstellungsfile hängen (Vorgabe: alle Reisen im Speicher).

## Related Files

| Datei | Relevanz |
|------|-----------|
| `betrieb/veroeffentlichen.sh` | Software-Weg: `main()` (fetch/merge/submodule), `software_anstossen`, `anstoss_weitergeben`, `software_kennung`, `ci_nachweis`, Rot-Datei, `reisen_des_laufs`, `git_reisen_uebrig`, Tests des Reisen-Repos (`tests/`), `units_abgleichen`, `nginx_abgleichen` |
| `betrieb/software-nachziehen.sh`, `.yml` | Workflow im Reisen-Repo; entfällt |
| `betrieb/gemeinsam.sh` | `FR_WURZEL` (Superprojekt des Submoduls), `nur_bauordner --main`, Einstellungsdatei `<FR_WURZEL>/betrieb/einstellungen.env`, Vorgaben (`FR_PYTHON`, `FR_SCHREIBKOPIE`) |
| `betrieb/deploy.sh` | kopiert Module aus `<FR_WURZEL>/engine` nach `<FR_DIENST>`; `nur_bauordner --main`; Git-Reisen aus `<FR_WURZEL>/reisen` |
| `betrieb/einrichten.sh` | `gh auth status`, `git ls-remote origin` |
| `betrieb/waechter.sh`, `vergleichslauf.sh`, `freischalten.sh`, Unit-/nginx-Vorlagen | Pfade unter `frieda/betrieb` |
| `engine/schreiben.py`, `schreiben_git.py`, `stand_git.py`, `instanz.py` | Wahl Git-/Speicherweg je Reise (`speicherreisen()`), neue Reisen über Git |
| `engine/rueckmeldungen.py` | Anstoß von der Seite (`api/aktualisieren`, `_anstoss.json`) |
| `docs/betrieb.md` | Abschnitte „Umschaltung einer Reise“ (Punkt 7), „Veröffentlichen“, „Anstoß“, „Überwachung“, „Neue Instanz einrichten“, „Bauordner und Arbeitsordner“ |
| `docs/adr/0009-reisespeicher.md` | Stufen; Stufe 5 nennt #454 als Folge |
| `henemm-infra/scripts/monitor.sh` (anderes Repo) | Rückstands-Check über `.git/modules/frieda/HEAD` |
| Reisen-Repo der Instanz (privat) | `.github/workflows/*`, `betrieb/einstellungen.env`, `betrieb/melden.sh`, `tests/` |

## Existing Patterns

- Prüfung vor Deploy: `ci_nachweis` (Pflichtprüfungen des genauen Software-Commits grün auf GitHub) ersetzt die Testrunde auf dem Server; sonst pytest auf dem Server. Main der Software ist geschützt, also liegt dort nur grün Geprüftes.
- Rückfall: Eine Reise bleibt bei rotem Bau auf dem letzten guten Stand (Webordner wird nur bei Erfolg ersetzt); Rot-Datei verhindert wiederholtes Prüfen desselben roten Stands.
- Formatwechsel für Speicherreisen: `neu.py nachziehen-speicher` beim Veröffentlichen, nur bei grünem Probebau (#348).
- Einstellungen: Umgebung vor Datei; geheime Werte in `<FR_DIENST>/betrieb.env`.
- Neustart des Laufs nach geänderten Einstellungen (`exec "$0"`, #242) – Muster für „Skript ändert sich unter sich selbst“.

## Dependencies

- Upstream: GitHub (öffentliches Repo lesbar ohne Anmeldung; Check-Runs per API), Reisespeicher, Ablage, Einstellungen.
- Downstream: alle systemd-Units der Instanz (Pfade), Schreibweg (Code aus `<FR_DIENST>`), Wächter, Monitor der Infrastruktur, Reisen-Repo der Instanz (Workflows, Tests), Seite (Fuß: „Stände noch nicht auf dem Server“, Anstoß).

## Existing Specs

- `docs/context/speicher-stufe5-350.md` (Variante A/B), Specs der Speicher-Stufen 1–5 unter `docs/specs/`.

## Risks & Considerations

- Live-System: Der Wechsel selbst (neuer Bauordner bzw. neue Pfade in den Units) muss automatisch und umkehrbar sein; ein halber Wechsel darf das Veröffentlichen nicht stilllegen.
- Skripte ändern sich unter sich selbst (Lauf aus dem Ordner, der gerade aktualisiert wird) – Muster aus `software-nachziehen.sh` (alles in `main()`) bzw. `exec`.
- Instanz-Einstellungen und Meldeweg verlieren ihr versioniertes Zuhause; neuer Ort und Umzug ohne Handschritt.
- Instanz-Tests (`tests/` im Reisen-Repo) laufen heute beim Software-Wechsel; ohne Reisen-Repo entfällt ihr Platz.
- Monitor in `henemm-infra` muss mitziehen (Issue dort).
- Mehrere Instanzen: nichts Instanzspezifisches in die Software.
- Neue Reisen und die 4 Git-Reisen müssen vorher im Speicher sein.

## Inventar (Suche über betrieb/, engine/, werkzeuge/, docs/, .github/)

- **Units aus dem Bauordner:** `veroeffentlichen.service`, `waechter.service`, `kartendienst/kartendienst-aktualisieren.service` starten `__WURZEL__/frieda/betrieb/…`; `push.service` und `schreiben.service` nutzen `__PYTHON__` (= `engine/.venv` im Bauordner), `schreiben.service` dazu die Arbeitskopie `__WURZEL__-schreiben` (Git-Worktree). Rückmeldedienst und Konnektor starten aus `__DIENST__`. Erzeugt von `einrichten.sh --erzeugen` (sed auf `__WURZEL__`, `__PYTHON__`), abgeglichen nach jedem grünen Lauf von `units_abgleichen`/`betrieb/units.py` (Root-Hilfsprogramm `<instanz>-units-installieren`). nginx-Vorlagen hängen nicht am Bauordner.
- **Submodul-Annahmen:** `gemeinsam.sh` (Wurzel über `--show-superproject-working-tree`), `veroeffentlichen.sh` (`software_kennung`, `ci_nachweis`, `software_anstossen`, `submodule update`), `einrichten.sh:72` (`engine -> frieda/engine`), `engine/schreiben_git.py:47`, `engine/neu.py:1074`, `engine/stand_git.py:6`, Usage-Texte in `werkzeuge/` (`frieda/werkzeuge/…`), `werkzeuge/grundkarte_auto.py:45` (Wurzel = `reise_dir.parent.parent`).
- **Git-Weg der Reisen** (tot, sobald alle Reisen im Speicher sind und neue dort entstehen): `engine/schreiben_git.py` (alle Aufrufe aus `schreiben.py`), `engine/stand_git.py` (aus `stand.py`, `reisespeicher.py:687`), `FR_SCHREIBKOPIE`, `reisen_des_laufs`, `git_reisen_uebrig`, `vergleichslauf.sh`. Rückbau nicht Teil von #454, aber der neue Software-Weg darf den Git-Weg nicht mehr brauchen.
- **Tests, die die Anordnung nachbauen:** `test_betrieb.py` (Fixtures `vf`, `an` mit echtem Submodul, `sp`, `instanz`, `fs`, `wa`), `test_software_nachziehen.py` (`software`, `sn`), `test_schreiben.py` (`repo`), `test_stand.py` (`reisen_repo`), `test_speicher_stufe5.py` (`s5`), weitere mit FR_WURZEL; `.github/workflows/tests.yml:121–128` (Instanz-Lauf mit `FR_WURZEL=/srv/beispiel/_bau`).
- **Anstoß von der Seite:** `engine/rueckmeldungen.py:968–994` (`_anstoss.json`), Texte `seite.rahmen.release.*` in allen Sprachen, `anstoss_weitergeben`.
