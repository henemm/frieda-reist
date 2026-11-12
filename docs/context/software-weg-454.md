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
- **Tests, die die Anordnung nachbauen:** `test_betrieb.py` (Fixtures `vf`, `an` mit echtem Submodul, `sp`, `instanz`, `fs`, `wa`), `test_software_nachziehen.py` (`software`, `sn`), `test_schreiben.py` (`repo`), `test_stand.py` (`reisen_repo`), `test_speicher_stufe5.py` (`s5`), weitere mit FR_WURZEL; `.github/workflows/tests.yml:121–128` (Instanz-Lauf mit `FR_WURZEL=<FR_SEITEN>/_bau`).
- **Anstoß von der Seite:** `engine/rueckmeldungen.py:968–994` (`_anstoss.json`), Texte `seite.rahmen.release.*` in allen Sprachen, `anstoss_weitergeben`.

## Analysis

### Type
Feature (Umbau des Lieferwegs der Software zur Instanz, Folge von #350 Variante B)

### Befund aus der Instanz (12.11.2026, ohne Namen)
- Die Liste der Speicherreisen kommt auf der Instanz aus `<FR_DIENST>/betrieb.env` (überschreibt `einstellungen.env`); sechs Reisen sind im Speicher, darunter alle echten.
- Vier Reisen liegen nur in Git: drei Test-/Probereisen und eine heute über den Konnektor neu angelegte (`trip_create` → Git-Weg). Die Lücke „neue Reise entsteht in Git“ ist real und wächst mit jeder neuen Reise.
- Weitere Abhängigkeiten am Pfad des Bauordners außerhalb dieses Repos: Das Server-Backup ruft `<Bauordner>/frieda/betrieb/sichern.sh`, der Monitor liest `.git/modules/frieda/HEAD`, `melden.sh` (Meldeweg) und `tests/` liegen im Reisen-Repo.
- Takt des Veröffentlichens: alle 5 Minuten (`veroeffentlichen.timer`).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/instanz.py` | MODIFY | `speicherreisen()`: Mitgliedschaft im Reisespeicher statt Liste; `FR_SPEICHERREISEN` nur noch Übergang (wirkungslos, kein Handschritt) |
| `engine/schreiben.py` | MODIFY | `trip_create`/`reise_anlegen` legen die Reise im Speicher an (Anfangsvorgang), nie mehr in Git |
| `engine/neu.py`, `engine/reisespeicher.py` | MODIFY | Anlegen im Speicher; automatische Umschaltung übriger Git-Reisen (Vergleich wie `vergleichslauf.sh`, nur bei „gleich“) |
| `betrieb/veroeffentlichen.sh` | MODIFY | Software-Weg neu: Abruf im Software-Klon, Nachweis der Pflichtprüfungen für den geholten Commit **vor** dem Umschalten, sonst Tests auf dem Server in eigenem Arbeitsbaum; letzter guter Stand (`<FR_DIENST>/software-gut`) und Rückfall; Kennung, Rot-Datei und Stempel am Software-Commit; Git-Teil (Reisen-Repo, `reisen_des_laufs`, Tests des Reisen-Repos) und `software_anstossen` entfallen; `anstoss_weitergeben` stößt nur einen Lauf an |
| `betrieb/gemeinsam.sh` | MODIFY | `FR_WURZEL` = Software-Klon (kein Superprojekt); Einstellungen der Instanz aus `<FR_DIENST>/instanz/einstellungen.env` (Übergang: alter Ort als Rückfall); `FR_PYTHON` an festem Ort außerhalb des Klons |
| `betrieb/einrichten.sh` | MODIFY | ohne `gh auth` und Reisen-Repo; legt den Software-Klon an; Umzug einer bestehenden Instanz automatisch und wiederholbar |
| `betrieb/deploy.sh`, `waechter.sh`, `sichern.sh`, `freischalten.sh`, `units.py`, `vorlagen/*`, Usage-Texte in `werkzeuge/` | MODIFY | Pfade `__WURZEL__/betrieb/…` statt `__WURZEL__/frieda/betrieb/…`; keine Reisen mehr aus `<FR_WURZEL>/reisen` |
| `engine/rueckmeldungen.py`, `engine/texte_*.py` | MODIFY | Anstoß der Seite: Lauf anstoßen statt Workflow (Texte `seite.rahmen.release.*` prüfen) |
| `engine/tests/test_betrieb.py`, `test_software_nachziehen.py`, `test_speicher_stufe5.py`, `test_schreiben.py`, `test_stand.py` | MODIFY/CREATE | Fixtures ohne Superprojekt; neue Tests: Software-Weg, Rückfall, Umzug, neue Reise im Speicher, automatische Umschaltung |
| `.github/workflows/tests.yml` | MODIFY | Instanz-Lauf ohne Superprojekt `_bau` |
| `docs/betrieb.md`, `docs/adr/0009-reisespeicher.md` | MODIFY | Bauordner, Veröffentlichen, Anstoß, Überwachung, Einrichten, Umzug |
| `henemm-infra/scripts/monitor.sh`, Backup-Aufruf (anderes Repo) | MODIFY | Rückstand gegen den Software-Klon; Pfad zu `sichern.sh`; beide Anordnungen zulassen (Issue in henemm-infra) |
| Reisen-Repo der Instanz (privat) | MODIFY | wird Archiv: Workflows aus; `einstellungen.env`, `melden.sh`, `tests/` ziehen beim Umzug automatisch um |

### Scope Assessment
- Files: ~20 in diesem Repo, dazu Infra und Reisen-Repo
- Estimated LoC: +900/-500 (etwa die Hälfte Tests)
- Risk Level: HIGH — Lieferweg aller Reisen und Dienste; Pfade sämtlicher Units ändern sich; der Wechsel muss im laufenden Betrieb automatisch und umkehrbar geschehen.

### Technical Approach (Empfehlung)
Zwei Lieferungen unter #454 mit einer Spec; Aufräumen als eigenes Folge-Issue.

**Lieferung 1 – Alle Reisen im Speicher (Voraussetzung, ohne Pfadwechsel):**
- Im Speicher ist, was im Speicher steht: `speicherreisen()` liest die Reisen aus dem Reisespeicher; die Liste in den Einstellungen wird überflüssig.
- Neue Reisen entstehen im Speicher (Anfangsvorgang wie bei der Umschaltung) und werden vom Speicher-Teil gebaut.
- Übrige Git-Reisen schaltet der Veröffentlichen-Lauf selbst um: Vergleich wie `vergleichslauf.sh`, nur bei „gleich“ umschalten, sonst Hinweis und die Reise bleibt in Git (kein Datenverlust, kein Löschen).

**Lieferung 2 – Software direkt:**
- Bauordner = Klon des öffentlichen Software-Repos (`<FR_SEITEN>/_software`, nur `main`, Vorspulen). Muster „erst prüfen, dann umschalten“: Abruf → Commit von `origin/main` → Nachweis der Pflichtprüfungen genau dieses Commits (main ist geschützt; Abfrage ohne Anmeldung, nur einmal je neuem Stand) → erst dann Umschalten des Arbeitsbaums. Ohne Nachweis: Tests auf dem Server in einem eigenen Arbeitsbaum des neuen Commits; rot → der Klon bleibt auf dem letzten guten Stand, Rot-Datei am Software-Commit, Alarm wie bisher.
- Stempel `veroeffentlicht` und Software-Kennung = Commit der Software; der Speicher-Teil zieht Reisen nach, sobald dieser Commit veröffentlicht ist (Logik bleibt, nur die Quelle der Kennung ändert sich).
- Einstellungen und Meldeweg der Instanz an festen Ort `<FR_DIENST>/instanz/` (vom Server-Backup erfasst); Python-Umgebung an festem Ort außerhalb des Klons.
- Umzug ohne Handschritt (#250): Der letzte Software-Stand, der noch über das Submodul kommt, legt im grünen Lauf den Klon an, kopiert Einstellungen und Meldeweg, gleicht die Units auf die neuen Pfade ab (vorhandenes Root-Hilfsprogramm) und lässt den alten Bauordner als Rückweg unangetastet. Die Units werden als letzter Schritt umgestellt; scheitert vorher etwas, bleibt alles beim alten Weg. Nach dem Umschalten Neustart des Skripts (`exec`, Muster #242).
- Anstoß von der Seite stößt nur noch einen Lauf an.
- Instanz-Tests: Betrieb wird durch Software-Tests mit `einstellungen.beispiel` und den Umzugstest abgedeckt; Inhaltstests echter Reisen entfallen mit dem Archiv (jede Reise wird bei jedem Bau geprüft). Die Prüfung „nichts Privates in der Software“ läuft als nicht sperrende Prüfung auf dem Server aus `<FR_DIENST>/instanz/tests/` weiter, falls vorhanden.

**Folge-Issue (nicht #454):** Rückbau des Git-Wegs (`schreiben_git.py`, `stand_git.py`, `vergleichslauf.sh`, `FR_SCHREIBKOPIE`, `_bau-schreiben-*`), `software-nachziehen.*`, Archivierung des Reisen-Repos.

### Befunde gegen den Plan
- Pfadwechsel aller Units ist das Hauptrisiko: abgefedert durch Umstellen der Units als letzten Schritt und den unangetasteten alten Bauordner.
- Abfragen der Prüfergebnisse ohne Anmeldung sind auf 60 je Stunde begrenzt; bei Abfrage nur je neuem Stand unkritisch, Rückfall Tests auf dem Server bleibt.
- Zwei Fremd-Repos (Infra: Monitor und Backup-Pfad; Reisen-Repo) müssen mitziehen, sonst falscher Alarm bzw. Sicherung ohne frischen Schnappschuss. Deshalb Lieferung 2 erst ausliefern, wenn die Infra beide Anordnungen akzeptiert.

### Dependencies
- Lieferung 2 setzt Lieferung 1 auf der Instanz voraus (keine Reise mehr in Git).
- Infra: `monitor.sh` (Rückstand), Backup-Aufruf von `sichern.sh` – Issue in henemm-infra.
- Tests der einbindenden Instanz mit dem Branch laufen lassen (Umgebungswerte und Dateiformate ändern sich).

### Open Questions
- Keine Produktfrage: Alle Entscheidungen sind technisch (Ort der Einstellungen, Umzugsweg, Test-Reisen umschalten statt löschen).
