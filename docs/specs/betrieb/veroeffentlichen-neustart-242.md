---
entity_id: veroeffentlichen-neustart-242
type: bugfix
created: 2026-11-02
updated: 2026-11-02
status: draft
workflow: fix-242-einstellungen-neustart
---

# Veröffentlichen liest geänderte Einstellungen im selben Lauf (#242)

Grundlage: `docs/context/fix-242-einstellungen-neustart.md` (Kontext und Analyse). Vorbild für Aufbau: `docs/specs/betrieb/veroeffentlichen-warnung-142.md`.

## Approval

- [ ] Approved

## Purpose

`betrieb/veroeffentlichen.sh` liest die Einstellungen der Instanz (`betrieb/einstellungen.env` im Reisen-Repo) beim Start und holt erst danach `origin/main`. Eine Einstellung, die mit einem Stand auf `main` ankommt (etwa `FR_ADRESSE`), wirkt deshalb erst im nächsten Lauf; bis dahin baut und veröffentlicht der Lauf mit dem alten Wert. Nach dem Vorspulen soll der Lauf erkennen, dass sich die Einstellungsdatei geändert hat, und sich selbst mit den neuen Werten neu starten.

## Ziel

Ein Lauf von `veroeffentlichen.sh`, der durch das Vorspulen eine geänderte Einstellungsdatei bekommt, baut, veröffentlicht und schaltet mit den neuen Werten frei, noch im selben Lauf und ohne Handarbeit.

## Problem und Ursache (belegt)

- `betrieb/gemeinsam.sh` liest die Einstellungen beim Einlesen der Datei (`fr_einlesen`, Zeile 58) und danach `<FR_DIENST>/betrieb.env` (Zeile 66), noch bevor `main()` in `veroeffentlichen.sh` `git fetch` (Zeile 305) und `git merge -q --ff-only` (Zeile 310) ausführt.
- Kernrisiko: `fr_einlesen` übernimmt nur, was noch nicht gesetzt ist (`[ -n "${!name+x}" ] || export …`, Zeile 54), und `gemeinsam.sh` exportiert alle `FR_*`-Werte samt abgeleiteten (`FR_KN_ADRESSE` aus `FR_ADRESSE`, `FR_SEITEN`, `FR_DIENST` …). Ein bloßes `exec "$0" "$@"` erbt diese Werte, der Neustart bliebe wirkungslos. Vor dem Neustart müssen deshalb alle `FR_*`-Werte entfernt werden, die nicht vom Aufruf (systemd, Hand, Tests) stammen.
- `nachlauf()` (Zeile 405) macht schon `exec "$0"` (ohne Argumente) und zeigt, dass die Sperre (fd 9) beim erneuten Öffnen frei wird.

## Source

- **Files:** `betrieb/gemeinsam.sh`, `betrieb/veroeffentlichen.sh`
- **Identifier:** `fr_einlesen`, neue Hilfsfunktion zum Entfernen der nicht vom Aufruf stammenden `FR_*`-Werte, `main()` und `nachlauf()` in `veroeffentlichen.sh`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/gemeinsam.sh` | Shell-Datei | Einlesen der Einstellungen, Vorgaben, Export; hier wird gemerkt, was vom Aufruf stammt |
| `betrieb/einstellungen.beispiel` | Vorlage | `test_beispiel_einstellungen_sind_vollstaendig` prüft, dass jede `FR_*`-Einstellung dort erklärt ist; interne Merker dürfen dort nicht auftauchen müssen |
| `sha256sum` | Befehl | Prüfsumme der Einstellungsdatei |
| `git fetch`, `git merge --ff-only`, `git submodule update` | Befehle | Vorspulen, das die Datei ändern kann |
| `deploy.sh`, `freischalten.sh`, `zustellen.py`, Timer, Schreibweg | Aufrufer und Aufgerufene | Schnittstelle bleibt gleich (Aufruf unverändert) |
| `engine/tests/test_betrieb.py`, Fixture `vf` | Test | Origin, Bauordner und Attrappen; Vorbild `test_veroeffentlichen_holt_einen_waehrend_des_laufs_angestossenen_stand_gleich_nach` |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/gemeinsam.sh` | MODIFY | Vor dem ersten Einlesen die Namen der schon gesetzten `FR_*`-Werte merken (Variable ohne `FR_`-Präfix, beim Neustart nicht überschreiben); neue Hilfsfunktion, die alle übrigen `FR_*` entfernt |
| `betrieb/veroeffentlichen.sh` | MODIFY | Prüfsumme der Einstellungsdatei vor `git fetch` und nach `merge` und `submodule update`; bei Abweichung Meldung, Aufräumen, `exec "$0" "$@"`; Merker gegen einen zweiten Neustart |
| `engine/tests/test_betrieb.py` | MODIFY | Neue Tests (siehe Test Plan) |
| `docs/betrieb.md` | MODIFY | Abschnitte „Veröffentlichen“ und „Einstellungen“: geänderte Einstellungen wirken im selben Lauf |

### Estimated Changes

- Files: 4
- LoC: +45/-2 (Skripte ca. 20, Tests ca. 25, Doku ca. 3)

### Nicht im Scope

- Das Nachladen im selben Prozess (verworfen: fehleranfällig bei abgeleiteten Werten und beim Vorrang des Aufrufs vor der Datei).
- `nachlauf()` und sein `exec "$0"` ohne Argumente (`--immer` geht dort bisher verloren) bleiben unverändert; das ist nicht Teil dieses Issues.
- Andere Skripte als `veroeffentlichen.sh` (`deploy.sh`, `freischalten.sh`, `waechter.sh` lesen die Einstellungen beim Start und laufen kurz).
- Änderung der Einstellungsdatei von `<FR_DIENST>/betrieb.env`: liegt nicht in git, ändert sich durch das Vorspulen nicht und wird beim Neustart einfach neu gelesen.
- Das private Reisen-Repo und seine Tests.
- Neue Einstellungen oder Änderungen an `betrieb/einstellungen.beispiel`.

## Implementation Details

1. **Aufruf-Namen merken.** `gemeinsam.sh` legt vor dem ersten `fr_einlesen` die Namen aller bereits in der Umgebung stehenden `FR_*`-Variablen in einem internen Merker ab, nur wenn dieser noch nicht gesetzt ist, damit er einen `exec` übersteht. Der Name des Merkers hat kein `FR_`-Präfix (Entscheidung Tech Lead): Er wird nicht von der Aufräum-Schleife erfasst, steht nicht in der Einstellungsvorlage, und `test_beispiel_einstellungen_sind_vollstaendig` bleibt grün.
2. **Aufräumen.** Eine neue Hilfsfunktion in `gemeinsam.sh` entfernt (`unset`) jede `FR_*`-Variable, deren Name nicht im Merker steht: Werte aus Datei, Dienst-Datei, Vorgaben und abgeleitete (etwa `FR_KN_ADRESSE`, `FR_GEPRUEFT`, `FR_WEGE_SPAETER`, `FR_BIBLIOTHEKEN_NEU`). Werte vom Aufruf, darunter `FR_WURZEL` und `FR_EINSTELLUNGEN`, bleiben. Die abgeleiteten Werte `RM_ABLAGE`, `KN_SEITEN`, `KN_ZUGAENGE`, `KN_BASIS` (ohne `FR_`-Präfix, von `gemeinsam.sh` mit `:=` gesetzt) erben den alten Wert ebenfalls und werden mit entfernt, sofern sie nicht vom Aufruf stammen; der Merker deckt deshalb auch sie ab.
3. **Auslöser.** `main()` bildet die `sha256sum` der Datei `${FR_EINSTELLUNGEN:-$FR_WURZEL/betrieb/einstellungen.env}` vor `git fetch`. Direkt nach `git merge --ff-only` und `git submodule update`, vor `abhaengigkeiten` und dem Bauen, bildet es sie erneut. Eine fehlende Datei zählt als eigener Wert (leer), sodass Erscheinen und Verschwinden eine Änderung ist. Ungleich: Meldung (englisch, wie die übrigen Meldungen des Skripts), Aufräumen nach Schritt 2, `exec "$0" "$@"`.
4. **Keine Schleife.** Nach dem `exec` ist „vorher“ der neue Stand der Datei, die Prüfsummen sind gleich, es folgt kein weiterer Neustart. Zusätzlich verhindert ein Merker ohne `FR_`-Präfix in der Umgebung einen zweiten Neustart im selben Lauf; `nachlauf()` setzt ihn zurück, damit ein dort ausgelöster neuer Lauf wieder neu starten darf.
5. **Position.** Der Zweig „Stand unverändert“ (früher `return` in Zeile 308) liegt vor dem Vorspulen und bleibt unberührt. Nach dem Neustart holt `git fetch` nichts Neues mehr, `merge` ist ein Nichts, und der Lauf baut mit den neuen Werten. Zusatznutzen: Eine geänderte `gemeinsam.sh` oder `veroeffentlichen.sh` aus dem Submodul wirkt dadurch ebenfalls im selben Lauf.
6. **Sperre und „nochmal“-Merker.** `exec` gibt fd 9 beim erneuten `exec 9>` frei (bewährt durch `nachlauf`). Ein zwischenzeitlich gesetzter Merker `veroeffentlichen-nochmal` geht nicht verloren, weil der neue Lauf `git fetch` erst danach ausführt. Die Trap `nachlauf` läuft bei `exec` nicht, das ist gewollt.
7. **Argumente.** `"$@"` hält `--immer` und Argumente mit Leerzeichen heil.

## Expected Behavior

- **Input:** ein Lauf von `veroeffentlichen.sh`, dessen `git merge` die Einstellungsdatei ändert (oder `FR_EINSTELLUNGEN` zeigt auf eine Datei, die sich während des Laufs ändert).
- **Output:** eine Protokollzeile über den Neustart, danach ein normaler Lauf mit den neuen Werten.
- **Side effects:** höchstens ein `exec` je Lauf; keine neuen Dateien, keine neue Schnittstelle.

## Test Plan

### Automated Tests (TDD RED)

In `engine/tests/test_betrieb.py` mit Fixture `vf`:

- [ ] Test 1 (`test_veroeffentlichen_uebernimmt_geaenderte_einstellungen_im_selben_lauf`): GIVEN ein Origin, dessen neuer Commit `FR_ADRESSE` in `betrieb/einstellungen.env` ändert, und ein Bauordner mit dem alten Wert / WHEN ein Lauf ohne weitere Angabe läuft / THEN sieht die Deploy-Attrappe (oder ein Protokoll des Laufs) schon den neuen Wert, und das Protokoll enthält die Zeile über den Neustart.
- [ ] Test 2 (`test_veroeffentlichen_wert_aus_dem_aufruf_gewinnt_auch_nach_dem_neustart`): GIVEN dieselbe Änderung und `FR_ADRESSE` ist im Aufruf gesetzt / WHEN der Lauf läuft / THEN gilt weiter der Wert aus dem Aufruf, nicht der aus der Datei.
- [ ] Test 3 (`test_veroeffentlichen_unveraenderte_einstellungen_starten_nicht_neu`): GIVEN ein neuer Commit, der die Einstellungsdatei nicht ändert / WHEN der Lauf läuft / THEN steht im Protokoll kein Neustart, und das Skript wird nur einmal gestartet (Zähler in der Attrappe oder im Protokoll).
- [ ] Test 4 (`test_veroeffentlichen_startet_hoechstens_einmal_neu`): GIVEN eine Änderung der Einstellungsdatei durch das Vorspulen / WHEN der Lauf läuft / THEN gibt es genau einen Neustart je Lauf und keine Endlosschleife (Lauf endet innerhalb der Zeitgrenze des Tests).
- [ ] Test 5 (`test_veroeffentlichen_neustart_behaelt_immer`): GIVEN `--immer` und geänderte Einstellungen / WHEN der Lauf läuft / THEN läuft der Neustart ebenfalls mit `--immer` (derselbe Stand wird erneut gebaut, obwohl er schon veröffentlicht ist).
- [ ] Test 6 (`test_veroeffentlichen_einstellungen_ausserhalb_des_repos_starten_nicht_neu`): GIVEN `FR_EINSTELLUNGEN` zeigt auf eine Datei außerhalb des Repos, die das Vorspulen nicht ändert / WHEN der Lauf läuft / THEN kein Neustart.
- [ ] Test 7 (`test_veroeffentlichen_neue_oder_entfernte_einstellungsdatei_ist_eine_aenderung`): GIVEN ein Commit, der die Einstellungsdatei neu anlegt (Fall A) oder entfernt (Fall B) / WHEN der Lauf läuft / THEN Neustart in beiden Fällen, bei B ohne die Werte aus der entfernten Datei (parametrisiert).
- [ ] Test 8 (`test_interne_merker_haben_kein_fr_praefix`): GIVEN `betrieb/gemeinsam.sh` und `betrieb/veroeffentlichen.sh` / WHEN ihr Text gelesen wird / THEN tragen die neuen Merker (Aufruf-Namen, Neustart) kein `FR_`-Präfix; bestehender `test_beispiel_einstellungen_sind_vollstaendig` bleibt grün.

Rot vor der Umsetzung: Test 1, 2, 7 und 8. Test 3, 4, 5 und 6 dürfen grün starten; sie sind Regressionsschutz gegen Schleife, verlorenes `--immer` und falschen Neustart, das Testprotokoll nennt das.

## Acceptance Criteria

- [ ] AC-1: Ändert das Vorspulen die Einstellungsdatei, baut, veröffentlicht und schaltet derselbe Lauf mit den neuen Werten (`FR_ADRESSE`, abgeleitetes `FR_KN_ADRESSE` und `KN_BASIS` eingeschlossen) frei, ohne zweiten Timer-Lauf. Test 1.
- [ ] AC-2: Ein Wert, der im Aufruf (systemd, Hand, Tests) gesetzt ist, gewinnt vor der Datei, auch nach dem Neustart. Test 2.
- [ ] AC-3: Bleibt die Einstellungsdatei unverändert, gibt es keinen Neustart und keine Schleife; der Lauf verhält sich wie bisher. Test 3.
- [ ] AC-4: Je Lauf gibt es höchstens einen Neustart; nach dem Neustart führt eine weitere Prüfung nicht erneut zum `exec`. Test 4.
- [ ] AC-5: `--immer` und alle übrigen Argumente bleiben beim Neustart erhalten. Test 5.
- [ ] AC-6: Zeigt `FR_EINSTELLUNGEN` auf eine Datei außerhalb des Repos, die das Vorspulen nicht ändert, gibt es keinen Neustart; ändert sie sich während des Laufs, zählt das ebenfalls (die Prüfsumme gilt für die tatsächlich gelesene Datei). Test 6.
- [ ] AC-7: Erscheint die Datei oder verschwindet sie durch das Vorspulen, gilt das als Änderung und löst genau einen Neustart aus. Test 7.
- [ ] AC-8: Die neuen internen Merker tragen kein `FR_`-Präfix, die Aufräum-Schleife entfernt sie nicht, und `test_beispiel_einstellungen_sind_vollstaendig` bleibt grün. Test 8.
- [ ] AC-9: Ein Lauf ohne neuen Stand (Zweig „Stand unverändert“) und das Verhalten der Rot-Datei, des Stempels und des Heartbeats ändern sich nicht (bestehende Tests in `test_betrieb.py` bleiben grün).
- [ ] AC-10: `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen; `docs/betrieb.md` beschreibt das neue Verhalten.

## Risks

- **Exportierte Werte überleben `exec`** (Kernrisiko): ohne das Aufräumen bliebe der Neustart wirkungslos. Gegenmaßnahme: Merker der Aufruf-Namen und Test 1 mit einem abgeleiteten Wert.
- **Zu aggressives Aufräumen:** Werden Werte vom Aufruf entfernt (etwa `FR_WURZEL`), bricht der Lauf ab (`nur_bauordner`). Gegenmaßnahme: Merker wird vor dem ersten Einlesen gebildet; Test 2.
- **Endlosschleife:** durch Prüfsumme (Gleichheit nach dem Neustart) und Merker begrenzt; Test 4.
- **Merker geht beim `exec` verloren oder wird zu früh überschrieben:** Der Merker der Aufruf-Namen wird nur gesetzt, wenn er fehlt; sonst zählten die beim ersten Laden abgeleiteten Werte beim zweiten Laden als vom Aufruf stammend. Test 1 bis 4 decken das ab.
- **Zweite Quelle `betrieb.env`:** wird beim Neustart neu gelesen, ändert sich nicht durch das Vorspulen; kein Sonderfall.
- **Live-Betrieb:** Das Skript läuft alle 5 Minuten auf dem Server. Ein Fehler bricht höchstens einen Lauf ab, der Timer wiederholt ihn. Abnahme im Betrieb (Label `lokal`) auf dem Server durch den Betrieb. Ändert der PR Umgebungswerte, laufen vor dem Vorspulen die Tests der einbindenden Instanzen mit dem Branch (CLAUDE.md).
- **Doppelter Workflow:** `fix-242-einstellungen-nachladen` ist ein Duplikat und wird beim Abschluss bereinigt.

## Definition of Done

- [ ] Jede Acceptance Criterion (AC-1 bis AC-10) ist durch einen automatischen Test belegt (Test 1 bis 8)
- [ ] Geänderte Einstellungen wirken im selben Lauf (Bau, Freischalten, `seiten.json`)
- [ ] Werte aus dem Aufruf gewinnen weiter; keine Endlosschleife; höchstens ein Neustart je Lauf; `--immer` bleibt erhalten
- [ ] Neue Merker tragen kein `FR_`-Präfix; `test_beispiel_einstellungen_sind_vollstaendig` bleibt grün
- [ ] `docs/betrieb.md` beschreibt das neue Verhalten (Abschnitte „Veröffentlichen“ und „Einstellungen“)
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen
- [ ] Tests der einbindenden Instanzen laufen vor dem Vorspulen mit dem Branch
- [ ] Keine Namen echter Reisen, Personen oder Server in Code, Tests, Doku

## Doku-Änderung

`docs/betrieb.md`, Abschnitt „Veröffentlichen“: ein bis zwei Sätze, dass das Skript nach dem Vorspulen eine geänderte Einstellungsdatei erkennt und sich mit denselben Argumenten neu startet. Abschnitt „Einstellungen“: eine Zeile, dass Änderungen der Einstellungsdatei im Reisen-Repo im selben Lauf wirken, Werte aus dem Aufruf aber weiter Vorrang haben, und dass `betrieb.env` nicht in git liegt. Keine neue Einstellung, daher keine Änderung an `betrieb/einstellungen.beispiel`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** reines Betriebsdetail ohne Berührung der Grundformen der Reise-Ontologie (ADR-0001, Prüfstelle nicht betroffen); der Neustart per `exec` folgt dem schon vorhandenen Muster in `nachlauf()`.

## Changelog

- 2026-11-02: Initial spec created
