# Context: fix-242-einstellungen-neustart

## Request Summary
Issue #242: `veroeffentlichen.sh` liest die Einstellungen der Instanz (`betrieb/einstellungen.env` im Reisen-Repo) beim Start und holt erst danach `origin/main`. Eine geänderte Einstellung (z. B. `FR_ADRESSE`) wirkt deshalb erst im nächsten Lauf. Vorschlag aus dem Issue: nach dem Vorspulen prüfen, ob sich die Einstellungsdatei geändert hat, und das Skript mit denselben Argumenten neu starten (`exec`). Test in `engine/tests/test_betrieb.py`.

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/veroeffentlichen.sh | `main()`: `git fetch` (Z. 305), `git merge --ff-only` (Z. 310), `submodule update` (Z. 312). Hier muss der Neustart nach dem Vorspulen hin. `nachlauf()` (Z. ~404) macht schon `exec "$0"` (ohne Argumente) |
| betrieb/gemeinsam.sh | `fr_einlesen` (Z. 43–56): `[ -n "${!name+x}" ] \|\| export …` – schon Gesetztes gewinnt. Liest zuerst `FR_EINSTELLUNGEN` bzw. `$FR_WURZEL/betrieb/einstellungen.env`, danach `$FR_DIENST/betrieb.env`. Exportiert danach alle FR_-Vorgaben |
| betrieb/einstellungen.beispiel | Erklärt jede FR_-Einstellung; Test `test_beispiel_einstellungen_sind_vollstaendig` prüft das |
| engine/tests/test_betrieb.py | Fixture `vf` (Origin, Bauordner, Attrappen), Vorbild: `test_veroeffentlichen_holt_einen_waehrend_des_laufs_angestossenen_stand_gleich_nach` |
| docs/betrieb.md | Abschnitt „Veröffentlichen“ (Z. 103 ff.) und „Einstellungen“ (Z. 171 ff.) |

## Existing Patterns
- Alles steckt in `main()`, damit bash das Skript vollständig einliest, bevor git es (Submodul) ersetzt. Ein `exec` nach dem Vorspulen startet die neue Fassung des Skripts – ein Zusatznutzen.
- `nachlauf()` nutzt bereits `exec "$0"`; die Sperre (fd 9) wird beim erneuten Öffnen frei. Argumente (`--immer`) gehen dort verloren.
- Zustand liegt nur in `FR_DIENST` (Stand, Rot-Datei, Merker).

## Dependencies
- Upstream: git (fetch/merge), `gemeinsam.sh`, Einstellungsdatei im Reisen-Repo, `betrieb.env` im Dienstordner (nicht in git).
- Downstream: `deploy.sh`, `freischalten.sh`, `zustellen.py`, Timer `<instanz>-veroeffentlichen.timer`, Schreibweg (startet den Lauf nach jedem Schreibvorgang).

## Existing Specs
- Keine Spec zum Veröffentlichen; das Verhalten steht in `docs/betrieb.md`. ADR-0001 (Kern/Prüfstelle) ist nicht berührt (reiner Betrieb).

## Risks & Considerations
1. **Kernrisiko: exportierte Werte überleben `exec`.** `fr_einlesen` lässt Vorhandenes stehen; `gemeinsam.sh` exportiert FR_ADRESSE usw. Ein bloßes `exec "$0" "$@"` erbt die alten Werte, der Neustart brächte nichts. Vor dem Neustart müssen die aus der Datei (und aus `betrieb.env`) übernommenen Variablen wieder entfernt werden (`unset`). Dazu muss `fr_einlesen` merken, welche Namen es selbst gesetzt hat (Unterschied zu Werten aus systemd/Aufruf, die weiter gelten sollen).
2. **Endlosschleife vermeiden:** nur neu starten, wenn die Datei sich wirklich geändert hat (Prüfsumme vor/nach dem Vorspulen), und höchstens einmal je Lauf (Merker in der Umgebung).
3. **Zweite Quelle:** `betrieb.env` im Dienstordner liegt nicht in git, ändert sich also nicht durch das Vorspulen und wird beim Neustart einfach neu gelesen.
4. **`FR_EINSTELLUNGEN` kann außerhalb des Repos zeigen:** dann ändert das Vorspulen nichts; die Prüfsumme deckt das ab, kein Sonderfall.
5. **Argumente:** `--immer` muss erhalten bleiben (`"$@"`); `nachlauf()` verliert sie bisher – in der Analyse klären, ob bewusst.
6. **Zustand vor dem Neustart:** Sperre, `rm -f "$nochmal"` und Anstoß-Weitergabe sind schon erfolgt; nach `exec` läuft alles erneut. Die Sperre wird frei und neu genommen; ein zwischenzeitlich gesetzter „nochmal“-Merker darf nicht verloren gehen.
7. **Zwei Workflows zu #242** (`fix-242-einstellungen-nachladen`, `fix-242-einstellungen-neustart`); aktiv ist `…-neustart` (Vorschlag aus dem Issue). Der andere ist ein Duplikat und wird beim Abschluss bereinigt.
8. Regeln aus CLAUDE.md: Meldungen im Skript englisch, Doku deutsch; ändert der PR Umgebungswerte, laufen vor dem Vorspulen die Tests der einbindenden Instanzen mit; Issue trägt Label `lokal` (Abnahme im Betrieb auf dem Server).

## Analysis

### Type
Bug (Betrieb, keine Reiseinhalte; ADR-0001 nicht berührt)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| betrieb/gemeinsam.sh | MODIFY | Beim Laden die Namen der schon vom Aufruf (systemd, Hand) gesetzten `FR_*`-Werte merken (`_fr_aufruf_namen`, beim Neustart nicht überschreiben). Neue Hilfsfunktion, die vor dem Neustart alle übrigen `FR_*` entfernt (aus Datei, Dienst-Datei, Vorgaben und abgeleitete wie `FR_KN_ADRESSE`) |
| betrieb/veroeffentlichen.sh | MODIFY | Prüfsumme der Einstellungsdatei (`${FR_EINSTELLUNGEN:-$FR_WURZEL/betrieb/einstellungen.env}`) zu Beginn von `main()` und direkt nach `merge --ff-only` und `submodule update`; bei Abweichung Meldung, Aufräumen, `exec "$0" "$@"` |
| engine/tests/test_betrieb.py | MODIFY | Neuer Test mit Fixture `vf`: Origin ändert `FR_ADRESSE`, ein Lauf, Ergebnis trägt schon den neuen Wert. Gegenproben: Wert aus dem Aufruf gewinnt weiter; unveränderte Datei startet nicht neu (keine Schleife) |
| docs/betrieb.md | MODIFY | Abschnitte „Veröffentlichen“ und „Einstellungen“: geänderte Einstellungen wirken im selben Lauf |

### Scope Assessment
- Files: 4
- Estimated LoC: +45/-2 (Skripte ca. 20, Test ca. 25, Doku ca. 3)
- Risk Level: MITTEL. Das Skript läuft alle 5 Minuten auf dem Live-Server; ein Fehler bricht aber höchstens einen Lauf ab, der Timer versucht es erneut.

### Technical Approach
1. **Kernproblem ist nicht der Neustart, sondern was ihn überlebt.** `fr_einlesen` lässt Gesetztes stehen, und `gemeinsam.sh` exportiert alle `FR_*`-Werte samt abgeleiteten (`FR_KN_ADRESSE:=$FR_ADRESSE`, `FR_SEITEN`, `FR_DIENST` …). Ein nacktes `exec "$0" "$@"` erbt sie, der Neustart bliebe wirkungslos. Lösung: beim ersten Laden die Namen der bereits vorhandenen `FR_*` in `_fr_aufruf_namen` ablegen (nur wenn noch nicht gesetzt, damit die Liste den `exec` überlebt). Vor dem Neustart alle übrigen `FR_*` mit `unset` entfernen. Werte aus systemd/Aufruf gelten weiter, alles Abgeleitete wird neu berechnet.
2. **Auslöser:** `sha256sum` der Einstellungsdatei vor `git fetch` und nach Vorspulen/Submodul-Update; ungleich → Neustart. Gleich → nichts. Keine Schleife: Nach dem `exec` ist „vorher“ der neue Stand. Zusätzlich ein Merker `_fr_neustart=1` gegen einen zweiten Neustart im selben Lauf; `nachlauf()` setzt ihn zurück.
3. **Position:** unmittelbar nach `merge`/`submodule update`, vor `abhaengigkeiten` und Bauen. Dann nutzen Bauen, Freischalten und `seiten.json` den neuen Wert. Der Fall „Stand unverändert“ (früher `return`) bleibt unberührt. Zusatznutzen: eine geänderte `gemeinsam.sh`/`veroeffentlichen.sh` aus dem Submodul wirkt auch schon im selben Lauf.
4. **Argumente:** `"$@"` (`--immer`) bleibt erhalten. `nachlauf()` lässt `--immer` weg; das bleibt unverändert (nicht Teil dieses Issues).
5. **Sperre und „nochmal“-Merker:** `exec` gibt fd 9 beim erneuten `exec 9>` frei (bewährt durch `nachlauf`). Ein zwischenzeitlich gesetzter Merker ist unkritisch, weil der neue Lauf `git fetch` erst danach ausführt. Die Trap `nachlauf` läuft bei `exec` nicht, das ist gewollt.
6. **Verworfene Alternative:** Werte im selben Prozess nachladen. Fehleranfällig (abgeleitete Werte, Vorrang Aufruf vor Datei); `exec` ist einfacher und robuster.

### Befunde gegen den Plan
Keine, die den Ansatz kippen. Zu beachten: (a) `FR_EINSTELLUNGEN` außerhalb des Repos: Prüfsumme gleich, kein Neustart, korrekt. (b) Datei erscheint oder verschwindet: zählt als Änderung, gewollt. (c) Argumente mit Leerzeichen bleiben dank `"$@"` heil.

### Dependencies
`deploy.sh`, `freischalten.sh`, `zustellen.py`, Timer und Schreibweg rufen `veroeffentlichen.sh` nur auf; die Schnittstelle bleibt gleich. Interne Merker ohne `FR_`-Präfix benennen, damit `test_beispiel_einstellungen_sind_vollstaendig` und die Aufräum-Schleife sie nicht erfassen. Vor dem Vorspulen laufen die Tests der einbindenden Instanzen mit dem Branch (CLAUDE.md).

### Open Questions
- [x] Interne Merker ohne `FR_`-Präfix: ja (Tech-Lead-Entscheidung).
- [ ] Doppelter Workflow `fix-242-einstellungen-nachladen` beim Abschluss bereinigen.
