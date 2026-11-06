# Context: Speicher Stufe 3, Betrieb auf dem Server (#348)

## Request Summary

Teil des Epics #345 (ADR-0009). Veröffentlichen und „Software nachziehen“ sollen aus dem Reisespeicher (SQLite, `engine/reisespeicher.py`) arbeiten statt aus Git; dazu ein Vergleichslauf als Befehl (Export aus der Datenbank gegen den Dateistand aus Git je Reise) und zwei Überwachungen (Software-Stand, Aktualität der Sicherung). Akzeptanz laut Issue: eine Testreise läuft vollständig über die Datenbank bis zur veröffentlichten Seite; Vergleichslauf ohne Unterschied an den Beispielreisen; Server schreibt und veröffentlicht ohne GitHub-Zugang (Test mit gesperrtem Netz); Doku und Vorlagen aktuell; keine Handschritte nach einem Software-Wechsel (#250).

Stufe 2 (#347) ist auf `main`: Schreibweg über den Speicher mit Schalter `FR_SPEICHERREISEN` je Reise, Git bleibt Vorgabe. Zusätzlich gehört der Rest von #347 hierher: die Rückholung der Sicherung aus dem Off-Site-Archiv, sobald der Speicherordner auf dem Server existiert und ein Backup mit ihm gelaufen ist (als Prüfpunkt in diesem Issue geführt).

## Related Files

| Datei | Relevanz |
|-------|----------|
| `betrieb/veroeffentlichen.sh` (535 Z.) | Baut heute nur aus Git: `reise_stand_schreiben` (Z. 73–79: `git rev-list --count`, `git log`), `reisen_des_laufs` (108–122: `git diff --name-only`), Stand-Datei `veroeffentlicht` mit Commit-SHA (354, 459–460), `git fetch`, ff-Merge, Submodul (351–359), `software_anstossen` (243–275, `git ls-remote`, `gh workflow run`), `anstoss_weitergeben` (228–241) |
| `betrieb/deploy.sh` (103 Z.) | Bau und Kopieren einer Reise; Modullisten `RM_MODULE`, `KN_MODULE`, `SB_MODULE`, `PS_MODULE` (Listentest in `engine/tests/test_betrieb.py`); prüft Git-Sauberkeit von `engine/` und `reisen/<reise>` (Z. 35) und `FR_GEPRUEFT` gegen `git rev-parse HEAD` (45) |
| `betrieb/gemeinsam.sh` | Einstellungen, Vorgaben, `nur_bauordner`; `FR_SPEICHER` und `FR_SPEICHERREISEN` fehlen hier (nur in `engine/instanz.py` und `betrieb/einstellungen.beispiel`) |
| `betrieb/software-nachziehen.sh` (166 Z.), `betrieb/software-nachziehen.yml` (81 Z.) | Nachziehen heute als GitHub-Workflow im Reisen-Repo: Vorwärts-Prüfung, `neu.py nachziehen` je Reise, Tor (Tests der Software, Bau jeder Reise), Bot-Commit, Push, bei Rot Issue mit Label `software-nachziehen` |
| `betrieb/einrichten.sh`, `betrieb/units.py`, `betrieb/vorlagen/` | Erzeugt systemd-Einheiten aus Vorlagen; `units.py pruefen` sperrt neue Einheiten und alle Timer (Sicherheitsentscheidung des Product Owners); das root-Hilfsprogramm kennt nur feste Arten |
| `betrieb/waechter.sh` | Täglich: Schnappschuss `<FR_SPEICHER>/sicherung/reisen.db` und Konten; Stempel `waechter-erfolg` |
| `engine/reisespeicher.py` (533 Z.) | `stand_nummer`, `exportieren(reise, ziel, bis)` (Ziel muss leer sein), `importieren(..., ab)`, `ordner_als_vorgang` (Ordner gegen Stand, ein Vorgang; Docstring nennt `nachziehen` als späteren Nutzer), `_ordner_lesen`, `_stand(…, "pruefsumme")`, `pruefen`, `sichern` |
| `engine/stand.py`, `engine/stand_git.py` | Stand-Nummer und Änderungsliste; `fuer_seite` wählt Speicher oder Git nach `instanz.speicherreisen()`; `stand.py` lädt den Speicher per `importlib` und kündigt einen normalen Import „mit Stufe 3“ an |
| `engine/instanz.py` | `speicher()`, `speicherreisen()` (Umgebung vor Einstellungsdatei) |
| `engine/neu.py` | `nachziehen(reise_dir, strecken_arten, schreiben)` (Z. ~878–975) schreibt direkt in einen Ordner; idempotent |
| `engine/bauen.py` | Liest `<reisen>/<reise>` als Ordner (`reise.json` Pflicht, `reise.yaml`), kennt weder Git noch Speicher; Medien nach `ziel/medien` |
| `docs/betrieb.md` | Abschnitte Veröffentlichen, Reise-Stand, Anstoß, Software nachziehen, Überwachung, „Speicherweg, Grenzen bis Stufe 3“ (um Z. 90) |
| `betrieb/einstellungen.beispiel` | Hinweis „bis Stufe 3 (#348) baut das Veröffentlichen nicht aus dem Speicher“ (Z. 174–179) |

## Existing Patterns

- **Eine Quelle je Reise:** Der Schalter `FR_SPEICHERREISEN` entscheidet je Reise zwischen Speicher und Git (Option A, Product Owner 6.11.2026). Der Git-Weg lebt bis Stufe 5 in `schreiben_git.py` und `stand_git.py`. Stufe 3 darf daran nichts brechen: ohne Einstellung ändert sich im Betrieb nichts.
- **„Stand“ einer Reise ist die Zahl der Vorgänge** (ADR-0009, Punkt 3). Die Seite trägt ihre Stand-Nummer in `daten.json` (`reise_stand.nummer`); `stand.veroeffentlicht(reise)` liest sie, `stand.lesen` ergibt `wartet | baut | veroeffentlicht | fehlgeschlagen`. Eine Funktion „geändert seit dem letzten Bau“ gibt es nicht; sie folgt aus dem Vergleich von `reisespeicher.stand_nummer` mit der veröffentlichten Nummer.
- **Lauf-Stand je Reise** `<FR_DIENST>/reise-stand/<reise>.lauf.json`, Stempel und Rot-Datei im Dienstordner; die Stand-Datei `veroeffentlicht` ist dagegen **instanzweit** und enthält einen Commit-SHA.
- **Ordner als Vorgang:** `ordner_als_vorgang` ist der vorgesehene gemeinsame Baustein für `reise_anlegen` und `nachziehen`.
- **Tor beim Nachziehen:** Rot sperrt bei den Tests der Software (nur bei neuem Stand) und beim Bau jeder Reise; Tests des Reisen-Repos sind nur eine Warnung; ein offenes Issue ist die Meldung (Spec 168, 161).
- **Anstoß vom Server:** `veroeffentlichen.sh` stößt den Workflow schon an (`git ls-remote`, Merker `nachziehen-angestossen`, Wartezeit `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN`).
- **Neue Einheiten sind gesperrt:** `units.py` erlaubt nur Änderungen an `FR_DIENST`, `FR_ZEITZONE`, `TimeoutStartSec`; neue Timer und Einheiten brauchen einen bewussten Schritt eines Menschen (Product Owner). Ein vorhandener Timer, `veroeffentlichen` alle 5 Minuten, läuft schon.
- **Meldewege:** Heartbeat nur bei fachlichem Erfolg (globale Regel); Überwachung als Teil-Check im Monitor der Instanz, nicht als eigener Monitor.

## Dependencies

- Upstream: `reisespeicher.py` (Stufe 1 und 2), `instanz.py`, `bauen.py`, `neu.py nachziehen`, Git des Bauordners und des öffentlichen Software-Repos (Quelle neuer Stände: `main` per `git ls-remote`, Submodul `frieda/`), `gh` (Workflow starten, Issue anlegen), Python, Node und Playwright auf dem Server.
- Downstream: Konnektor und Rückmeldedienst (`publish_status`, `api/stand`, laden den Speicher laut ADR erst ab Stufe 3), Seite (`reise_stand` im Bau), Monitor der Instanz (außerhalb dieses Repos), Reisen-Repos der Instanzen (Workflow „Software nachziehen“ liegt dort als kopierte Vorlage), Tests der einbindenden Instanzen.

## Existing Specs

- `docs/specs/betrieb/reisespeicher-346.md` (Stufe 1), `schreibweg-speicher-347.md` (Stufe 2, nennt ausdrücklich: Veröffentlichen aus dem Speicher, Aufruf des Bausteins durch `nachziehen`, Vergleichslauf und Umschalten sind Stufe 3 und 5), `speicher-347-tempo.md`
- `docs/specs/betrieb/software-nachziehen-161.md`, `-168.md`, `software-wechsel-ohne-handarbeit-250.md`, `veroeffentlichen-neustart-242.md`, `veroeffentlichen-warnung-142.md`, `bauordner-137.md`
- `docs/adr/0009-reisespeicher.md` (Konsequenzen zu Stufe 3: „Veröffentlichen und Nachziehen lesen aus dem Speicher; ein Anfangsvorgang je Reise mit Vermerk ‚vorher in Git‘ und übernommener Stand-Nummer genügt“)
- `docs/context/speicher-347-stufe2.md`

## Befunde, die die Analyse klären muss

1. **Eine Speicher-Reise wird heute nicht neu gebaut.** `veroeffentlichen.sh` baut nur, wenn sich `reisen/` im Git ändert oder ein Software-Wechsel vorliegt. Beim Bau kommt `reise_stand` über `stand.fuer_seite` aus dem Speicher, `reise_stand_schreiben` im Skript schreibt aber die Git-Nummer: Der Weg ist halb umgestellt.
2. **Materialisierung:** `exportieren` verlangt ein leeres Ziel, der Generator liest `<reisen>/<reise>`. Offen ist, wohin materialisiert wird (Bauordner `reisen/` ist ein Git-Ordner mit Hygieneprüfungen in `deploy.sh`), und was mit Medien (Fotos liegen bis Stufe 4 als BLOB in der Datenbank) passiert.
3. **Gemischter Betrieb:** Eine Instanz hat Git-Reisen und Speicher-Reisen gleichzeitig (Schalter je Reise). Veröffentlichen, die instanzweite Stand-Datei (Commit-SHA) und „Software-Wechsel baut alle Reisen“ müssen beides tragen.
4. **Vergleichslauf:** Es gibt ihn nicht; Bausteine sind `_ordner_lesen`, `_stand(…, pruefsumme)` und `exportieren`. Offen: Befehl, Ausgabe, Exit-Codes, wie er als „Voraussetzung zum Umschalten“ erzwungen oder nur gemeldet wird.
5. **Nachziehen auf dem Server:** Der Workflow ist durch und durch GitHub (Runner, Bot-Nutzer, `GITHUB_*`, `gh issue`). Auf dem Server fehlen dokumentiert: Rechte von `gh` für Issues, ein schreibbarer Bauordner für das Submodul, ein Zeitgeber. Die Spec 161 hat `submodule update --remote` auf dem Server ausdrücklich verworfen. Offen: Quelle des Software-Stands ohne GitHub-API, Ersatz für den Bot-Commit (ein Vorgang je Reise, Werkzeug `nachziehen`), Ersatz für das Issue als Meldung, Verhalten ohne Netz.
6. **Zeitgeber:** Neue Timer sind gesperrt. Mögliche Wege sind der vorhandene Lauf von `veroeffentlichen` (alle 5 Minuten) mitzunutzen oder eine neue Einheit, die der Product Owner freigeben müsste.
7. **Überwachung:** „Software-Stand hängt zurück“ ist im Repo nur beschrieben und im Infra-Repo der Instanz umgesetzt; „Aktualität der Sicherung“ gibt es außer dem Stempel `waechter-erfolg` (36 h) nicht. Der Code dazu liegt außerhalb dieses Repos.
8. **Gemischtes Verhalten des Konnektors:** Laut ADR lesen Konnektor und Rückmeldedienst den Speicher erst ab Stufe 3; der Test `test_reisespeicher.py` (Modulbindung, um Z. 572) verbietet das heute und muss bewusst angepasst werden.

## Risks & Considerations

- **Kritischer Pfad:** Veröffentlichen und Software-Wechsel laufen für alle Reisen der Instanz über diese Skripte; ein Fehler kann alle Seiten stehen lassen. Die Tests nutzen echte Git-Repos mit Attrappen (`VF_*`-Haken in `test_betrieb.py`); jede Änderung braucht dort grüne Läufe, die Instanz-Tests laufen vor dem Vorspulen mit dem Branch (Hinweis im Issue und in CLAUDE.md).
- **Kein Handschritt nach einem Software-Wechsel** (#250): Jede Umstellung muss selbst laufen; neue Einstellungen brauchen Vorgaben und Doku in `einstellungen.beispiel`.
- **Nichts Instanzspezifisches** in `betrieb/` oder der Engine (Pfade, Adressen, Benutzer kommen aus den Einstellungen; Anteile der Instanz gehören ins private Reisen-Repo, dort Issue #252).
- **Keine KI auf dem Server** (ADR-0001): Nachziehen und Vergleich sind feste Programme.
- **Rote Phase Nachziehen ohne Netz:** Der Server darf ohne GitHub weiter schreiben und veröffentlichen; Nachziehen selbst braucht den Software-Stand, also ein Netz. Das muss getrennt bleiben, damit ein Ausfall von GitHub das Veröffentlichen nicht blockiert.
- **Umschalten echter Reisen ist nicht Teil dieser Stufe** (Stufe 5, #350): hier nur die Fähigkeit und der Vergleichslauf; vorher Rückspielversuch aus dem Off-Site-Archiv.
- **Reihenfolge mit #349 (Stufe 4):** Fotos als BLOB machen Export und Bau langsam; die Auslagerung kommt danach. Stufe 3 darf das nicht vorwegnehmen, aber Export und Bau müssen mit der 110-MB-Testreise noch tragbar sein (Messlauf aus #347).
- **Offene Fragen an den Product Owner** wären Sicherheitsentscheidungen: neue systemd-Einheit, `gh`-Rechte des Dienstbenutzers für Issues, Ablösung des GitHub-Workflows als einziger Weg.

## Analysis

### Type
Feature (Betrieb, kritischer Pfad: Veröffentlichen und Software-Wechsel aller Reisen einer Instanz)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/reisespeicher.py` | MODIFY | Neue Funktionen: Materialisierung in einen Bauordner (auf Basis `exportieren`, Ziel wird ersetzt), Vergleich Speicher gegen Ordner (auf Basis `_ordner_lesen`/Prüfsummen), neue Unterbefehle im `main` |
| Vergleichslauf (neues Modul oder Unterbefehl) | CREATE | Je Reise Export aus Datenbank gegen Dateistand aus Git; Exit 0 = gleich, 1 = Unterschied, 2 = Fehler; Ausgabe mit Dateiliste |
| `betrieb/veroeffentlichen.sh` | MODIFY | Quelle je Reise (`FR_SPEICHERREISEN`): Speicher-Reisen werden neu gebaut, wenn `stand_nummer` ≠ veröffentlichte Nummer (nicht `git diff`); `reise_stand_schreiben` nimmt für sie die Speicher-Nummer; Speicher-Teil läuft unabhängig vom Erfolg von `git fetch` |
| `betrieb/deploy.sh` | MODIFY | Speicher-Reise vor dem Bau in einen eigenen Ordner materialisieren; Git-Sauberkeitsprüfung nur für Git-Reisen; Modullisten ergänzen |
| `betrieb/gemeinsam.sh` | MODIFY | `FR_SPEICHER`, `FR_SPEICHERREISEN` einlesen |
| `betrieb/software-nachziehen.sh` (+ Aufruf vom Server-Lauf) | MODIFY | Nachziehen für Speicher-Reisen auf dem Server, vom vorhandenen 5-Minuten-Lauf aufgerufen (keine neue Einheit); `neu.py nachziehen` auf materialisiertem Ordner, Ergebnis über `ordner_als_vorgang` |
| `betrieb/software-nachziehen.yml` | KEEP/MODIFY | Bleibt für Git-Reisen bis Stufe 5 |
| `engine/stand.py`, `engine/stand_git.py` | MODIFY | Hinweis „mit Stufe 3“ einlösen |
| `engine/tests/test_reisespeicher.py` (~Z. 572) | MODIFY | Modulbindungs-Test bewusst anpassen |
| `engine/tests/test_betrieb.py`, neue Tests | MODIFY/CREATE | Speicher-Reise bis zur Seite; Vergleichslauf an beiden Beispielreisen ohne Unterschied; Lauf ohne Netz; gemischter Betrieb |
| `betrieb/einstellungen.beispiel`, `docs/betrieb.md` | MODIFY | „bis Stufe 3“-Hinweise ersetzen; Vergleichslauf, Server-Nachziehen, Überwachung |
| `docs/specs/betrieb/` | CREATE | Spec Stufe 3 (Phase 3) |

### Scope Assessment
- Files: ca. 12–15 (4–5 neu)
- Estimated LoC: +700/−150
- Risk Level: HIGH — die Skripte laufen für alle Reisen der Instanz. Gegenmittel: Schalter je Reise, ohne Einstellung ändert sich nichts; Git-Weg bleibt bis Stufe 5 unangetastet.

### Technical Approach (Empfehlung)
Vier einzeln lieferbare Teile, jeder auf `main`, wenn grün:

1. **Materialisieren + Vergleichslauf** (Bausteine bestehen). Materialisiert wird **außerhalb** des Git-Bauordners (`<FR_DIENST>/bau/<reise>`), damit Hygieneprüfungen und `git diff` unberührt bleiben. Medien bis Stufe 4 als BLOB mit exportieren; Messung mit der 110-MB-Testreise.
2. **Veröffentlichen aus dem Speicher (gemischt):** Speicher-Reisen zuerst, unabhängig von `git fetch` (Akzeptanz „ohne GitHub“); danach der bestehende Git-Teil. Die instanzweite Stand-Datei (Commit-SHA) bleibt für Git; für Speicher-Reisen zählt die Nummer in `reise-stand/<reise>.lauf.json`. Software-Wechsel baut weiter alle Reisen.
3. **Nachziehen auf dem Server:** Software-Stand = Submodul-Stand im Bauordner (kein `submodule update --remote`, Spec 161). Ablauf: Vorwärts-Prüfung → `neu.py nachziehen` je Speicher-Reise → Tor (Tests der Software nur bei neuem Stand, Bau jeder Reise) → bei Grün ein Vorgang je Reise (idempotent, keine Änderung = kein Vorgang). Rot: Rot-Datei + normale Meldung (Issue nur, wenn der Product Owner `gh`-Rechte freigibt). Nachziehen braucht Netz, blockiert das Veröffentlichen aber nie.
4. **Überwachung:** Dieses Repo liefert prüfbare Zustände (Stempel `waechter-erfolg`, Zeit der letzten Sicherung, Rückstand des Software-Stands); der Teil-Check kommt in `henemm-infra/scripts/monitor.sh` (selbst umsetzen, Issue dort).

Rückholung aus dem Off-Site-Archiv (Rest #347) bleibt Prüfpunkt, kein Code.

### Befunde, die gegen den Plan sprechen
Keine zwingenden. Einschränkungen: gemischter Betrieb verdoppelt Pfade bis Stufe 5; Nachziehen braucht Netz (vom Veröffentlichen getrennt); große Fotos als BLOB können das Zeitziel (120 s) reißen — Befund für #349, nicht für diese Stufe.

### Varianten Materialisierung (Zahlen folgen als Messung in Phase 5)
| Variante | Vorteil | Nachteil |
|----------|---------|----------|
| Export nach `<FR_DIENST>/bau/<reise>` je Lauf (empfohlen) | Bauordner unberührt, einfach, idempotent | Exportzeit je Lauf |
| Export nach `reisen/<reise>` im Bauordner | Weniger Skriptänderung | Verletzt „Uncommitted changes“-Prüfung, Gefahr versehentlichen Committens |
| Dauerhafter Ordner mit Abgleich | Schnell | Zweite Wahrheit, Drift, mit Stufe 4 überflüssig |

### Dependencies
- Upstream: `reisespeicher.py`, `instanz.py`, `bauen.py`, `neu.py nachziehen`, `stand.py`, Git des Bauordners, `gh`.
- Downstream: Konnektor, Rückmeldedienst, Monitor der Instanz, Reisen-Repos mit kopiertem Workflow, Tests der einbindenden Instanzen (vor dem Vorspulen mit dem Branch laufen lassen).

### Open Questions
- [ ] Zeitgeber: vorhandenen 5-Minuten-Timer mitnutzen (Empfehlung, keine neue Einheit). Nur wenn eine eigene Einheit gewünscht ist, muss der Product Owner freigeben (`units.py` sperrt neue).
- [ ] `gh`-Rechte des Dienstbenutzers für Issues bei Rot (Sicherheitsentscheidung). Empfehlung: zunächst nur Rot-Datei + normale Meldung.
- [ ] Vergleichslauf als Voraussetzung zum Umschalten erzwingen? Empfehlung: in Stufe 3 Befehl + Stempel mit Zeit/Ergebnis, Erzwingung in Stufe 5 (#350).
