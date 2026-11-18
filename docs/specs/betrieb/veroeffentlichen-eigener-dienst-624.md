---
entity_id: veroeffentlichen-eigener-dienst-624
type: feature
created: 2026-11-18
updated: 2026-11-18
status: draft
version: "1.0"
tags: [betrieb, systemd, veroeffentlichen, speicher, schreibweg]
workflow: 624-veroeffentlichen-eigener-dienst
---

# Veröffentlichen als eigener Dienst: Merker und systemd-Path-Einheit statt Kindprozess (#624)

Grundlage: `docs/context/624-veroeffentlichen-eigener-dienst.md` (Kontext, Analyse, Befunde 1 bis 6). Vorgänger und Auslöser: `docs/specs/betrieb/speichergrenzen-538.md` (Entscheidung 3 nennt #624 als Folge). Zeitziel: #230 (zwei Minuten vom Speichern bis zur aktuellen Seite).

## Approval

- [ ] Approved

## Purpose

Der Schreibweg startet das Veröffentlichen heute als Kindprozess (`Popen`) und hält es damit in der Speichergrenze, den Rechtebeschränkungen (`NoNewPrivileges`) und dem Lebenszyklus des Schreibdienstes fest: Die Speicherspitze von 3,4 GiB zwingt zu einer groben Grenze von 5G, Freischalten und Neustarts über `sudo` scheitern (#465, #494), und ein Neustart des Schreibdienstes tötet ein laufendes Veröffentlichen. Künftig legt der Schreibweg nur noch einen Merker; eine systemd-Path-Einheit startet daraufhin den schon vorhandenen eigenen Dienst `<instanz>-veroeffentlichen.service`. Danach kann die Grenze des Schreibdienstes auf 512M sinken, ohne dass das Zeitziel leidet.

## Entscheidungen (Tech Lead, nicht offen)

1. **Kein Kindprozess mehr.** `veroeffentlichen_anstossen` in `engine/schreiben.py` legt nur den Merker `<FR_DIENST>/veroeffentlichen-anstoss` an. Die Funktion wirft nie; ein Fehler beim Anlegen steht nur im Protokoll. „Leer = aus“ über `SB_VEROEFFENTLICHEN` bleibt: ist das Skript dort leer gesetzt, wird kein Merker angelegt. Die Protokolldatei `veroeffentlichen-anstoss.log` entfällt. Der Git-Weg (`engine/schreiben_git.py`) nutzt denselben Anstoß.
2. **Neue Vorlage** `betrieb/vorlagen/veroeffentlichen.path` mit `PathExists=__DIENST__/veroeffentlichen-anstoss`, `Unit=__INSTANZ__-veroeffentlichen.service` und `WantedBy=paths.target`. `PathExists` statt `PathChanged`, damit systemd nach dem Ende des Dienstes erneut prüft und ein Anstoß, der während eines Laufs kam, nicht verloren geht.
3. **Merker vor der Sperre löschen.** `betrieb/veroeffentlichen.sh` entfernt `veroeffentlichen-anstoss` am Anfang, vor `flock`. Dadurch bleibt der Merker nie liegen, die Path-Einheit löst keine Endlosschleife und kein Trigger-Limit aus. Ist die Sperre belegt (auch durch einen Lauf außerhalb der Einheit), greift das vorhandene `veroeffentlichen-nochmal` (Nachlauf). Der Merker `-nochmal` behält seine Bedeutung „nach dem laufenden Lauf“; er wird nicht wiederverwendet. Zweite Sicherung: `veroeffentlichen.service` entfernt den Merker schon vor dem Skript (`ExecStartPre=-/bin/rm -f __DIENST__/veroeffentlichen-anstoss`). Bricht das Skript vor seinem eigenen `rm` ab (unlesbare Einstellungen, `nur_bauordner`, `mkdir` scheitert), bleibt so kein Merker liegen, und die Path-Einheit startet den Dienst nicht immer wieder, bis die Startbegrenzung von systemd sie auf `failed` setzt. Das `rm` im Skript bleibt für Läufe außerhalb der Einheit.
4. **`schreiben.service`:** `MemoryHigh=384M`, `MemoryMax=512M`; der Kommentar „bis #624“ entfällt und nennt den neuen Stand. `MemorySwapMax` sinkt von 1G auf 256M (gleiches Verhältnis wie beim Konnektor mit 1G Hauptspeicher und 256M Swap): Ohne Kindprozess braucht der Schreibdienst keinen großen Swap, und ein großer Swap würde ein Leck weiter verschleppen statt begrenzen. Alle drei Werte liegen im erlaubten Muster `^[1-9][0-9]{0,4}[MG]$`; der Abgleich installiert sie ohne Root-Schritt.
5. **Einrichten:** `betrieb/einrichten.sh` erzeugt und installiert auch `.path`-Vorlagen und aktiviert `<instanz>-veroeffentlichen.path` (`enable --now`). `betrieb/units.py` kennt `.path` in `EINHEITEN`; eine fehlende `.path`-Einheit ist eine gesperrte, gemeldete Abweichung (normale Meldung, kein Alarm). `betrieb/vorlagen/units-installieren.py` bleibt unverändert: Eine `.path`-Einheit ist nicht automatisch installierbar, es gibt keine neue Sicherheitsentscheidung.
6. **Übergang ohne aktive Path-Einheit:** Der Merker bleibt liegen, der Timer (alle fünf Minuten) veröffentlicht. Es gibt keinen Rückfall auf `Popen`, denn der liefe nach dem Abgleich von `MemoryMax=512M` in den Speicherabbruch (Analyse, Befund 2). Folge im Übergangsfenster: bis zu fünf Minuten Latenz statt sofort, nichts geht verloren, nichts stürzt ab.
7. **Auslieferung durch Claude, kein Handschritt für den Product Owner:** Nach `main` führt Claude auf der Instanz einmalig `betrieb/einrichten.sh --installieren` aus (Muster #454, Root über `sudo` im Skript). Die Umstellung gehört zu „fertig“.
8. **Zeitziel unverändert:** Die Path-Einheit reagiert sofort; das Zeitziel von zwei Minuten (#230) bleibt.
9. **Messlauf:** `betrieb/messlauf-schreibweg.py` prüft in der Sandbox den Merker statt eines Skriptstarts.

## Source

- **Files:** `engine/schreiben.py`, `engine/schreiben_git.py`, `betrieb/veroeffentlichen.sh`, `betrieb/vorlagen/veroeffentlichen.path`, `betrieb/vorlagen/schreiben.service`, `betrieb/einrichten.sh`, `betrieb/units.py`, `betrieb/messlauf-schreibweg.py`, `docs/betrieb.md`
- **Identifier:** `veroeffentlichen_anstossen`, `EINHEITEN` (in `units.py`), Sperrblock in `veroeffentlichen.sh`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/schreiben.py` (`veroeffentlichen_anstossen`, Skriptpfad aus `SB_VEROEFFENTLICHEN`) | Modul | legt künftig nur den Merker an |
| `engine/schreiben_git.py` | Modul | Git-Weg, ruft denselben Anstoß |
| `betrieb/veroeffentlichen.sh` (Sperre `veroeffentlichen.lock`, Merker `veroeffentlichen-nochmal`) | Skript | löscht den Anstoß-Merker vor `flock`; Nachlauf bleibt |
| `betrieb/vorlagen/veroeffentlichen.service` / `.timer` | Vorlage | bestehender Dienst (oneshot, ohne `NoNewPrivileges`), Timer als Rückfall |
| `betrieb/units.py` (`EINHEITEN`, `abgleich()`) | Modul | kennt künftig `.path`-Einheiten |
| `betrieb/vorlagen/units-installieren.py` | Root-Helfer | unverändert; `.path` bleibt gesperrt |
| `betrieb/einrichten.sh --installieren` | Skript | erzeugt und installiert Einheiten, aktiviert die Path-Einheit (Einmalschritt der Auslieferung) |
| `betrieb/messlauf-schreibweg.py` | Skript | Messlauf in der Sandbox |
| systemd (Path-Einheiten, `PathExists=`), `flock` | Fremd | Auslösung und Sperre; keine neue Bibliothek |
| Reisen-Repo der Instanz | Fremd | dessen Tests laufen vor dem Vorspulen mit dem Branch (Anstoß-Protokolldatei entfällt, Verhalten des Anstoßes ändert sich) |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/schreiben.py` | MODIFY | `veroeffentlichen_anstossen`: Merker statt `Popen`, wirft nie, „leer = aus“ bleibt, Anstoß-Protokolldatei entfällt |
| `engine/schreiben_git.py` | MODIFY (nur falls nötig) | Aufruf bleibt; Stummel und Kommentar prüfen |
| `betrieb/vorlagen/veroeffentlichen.path` | CREATE | `PathExists`, `Unit`, `WantedBy=paths.target` |
| `betrieb/veroeffentlichen.sh` | MODIFY | Anstoß-Merker vor `flock` löschen |
| `betrieb/vorlagen/veroeffentlichen.service` | MODIFY | `ExecStartPre` entfernt den Anstoß-Merker vor dem Skript (zweite Sicherung, Entscheidung 3) |
| `betrieb/vorlagen/schreiben.service` | MODIFY | 384M/512M, Swap 256M, Kommentar ohne „bis #624“ |
| `betrieb/einrichten.sh` | MODIFY | `.path`-Vorlagen erzeugen und installieren, `enable --now <instanz>-veroeffentlichen.path` |
| `betrieb/units.py` | MODIFY | `EINHEITEN` kennt `.path` |
| `betrieb/messlauf-schreibweg.py` | MODIFY | prüft Merker statt Skriptstart |
| `docs/betrieb.md` | MODIFY | Anstoß über Merker und Path-Einheit, Grenze 512M, Auslieferungsschritt, Wegfall des Protokolls |
| `docs/specs/betrieb/speichergrenzen-538.md` | MODIFY | Verweis: Folge #624 erledigt; Wertetabelle für `schreiben` im Changelog nachgezogen |
| `engine/tests/test_anstoss_pfad_570.py` | MODIFY | die sieben Tests prüfen Merker statt Skriptlauf |
| `engine/tests/test_schreiben.py`, `test_schreiben_speicher.py`, `test_software_weg_454.py`, `test_speicher_stufe5.py`, `test_stand.py` | MODIFY | Stummel mit `SB_VEROEFFENTLICHEN` prüfen den Merker |
| `engine/tests/test_units.py` | MODIFY | `EINHEITEN` mit `.path`, fehlende `.path` = gesperrt |
| `engine/tests/test_units_helfer.py` | MODIFY | Helfer lehnt `.path` weiter ab (Test der Kategorie „sechs Einheiten“ bleibt gültig) |
| `engine/tests/test_betrieb.py` | MODIFY | Speichergrenzen für `schreiben`, Doku ohne „bis #624“, Path-Vorlage, `einrichten.sh`, Merker vor Sperre |

Keine Änderung: `betrieb/vorlagen/units-installieren.py`, `betrieb/vorlagen/veroeffentlichen.timer`, `ERLAUBT`.

### Nicht im Scope

- Erweiterung der Erlaubnisliste oder des Root-Hilfsprogramms um `.path`-Einheiten (wäre eine Sicherheitsentscheidung des Product Owners; der Einmalschritt bei der Auslieferung genügt).
- Neue Grenzen für `veroeffentlichen.service` (bleibt ohne Speichergrenze, `speichergrenzen-538` Entscheidung 4).
- Änderungen an Inhalt oder Ablauf des Veröffentlichens selbst (Bauen, Hochladen, Prüfen).
- Änderung der Grenzen von `rueckmeldungen`, `push`, `konnektor`.
- Ein Rückfall auf `Popen` oder ein zweiter Auslösemechanismus neben der Path-Einheit.

### Estimated Changes

- Files: etwa 17 bis 19, Schätzung (davon 8 bis 11 Tests, einige nur falls nötig; eine neue Vorlage)
- LoC: +250/-120
- Risiko mittel: zentraler Weg „Speichern, dann Seite aktuell“; abgesichert durch den Timer als Rückfall, keine Datenänderung.

## Implementation Details

### Schreibweg

`veroeffentlichen_anstossen` ermittelt den Skriptpfad wie bisher (Argument, dann `SB_VEROEFFENTLICHEN`, dann `veroeffentlichen_skript(wurzel)`); ist er leer, geschieht nichts. Sonst wird `<FR_DIENST>/veroeffentlichen-anstoss` angelegt (Datei anlegen, vorhandene nicht verändern). Jede Ausnahme wird gefangen und nur ins Protokoll geschrieben; der Aufrufer (Speicherweg und Git-Weg) merkt davon nichts. `nice` und `ionice` entfallen im Schreibweg, sie stehen in der Einheit `veroeffentlichen.service` (`Nice=10`).

### Skript

Am Anfang von `betrieb/veroeffentlichen.sh`, vor dem `flock`-Aufruf, wird der Merker mit `rm -f` entfernt. Danach unverändert: Sperre holen; belegt, dann `veroeffentlichen-nochmal` anlegen und beenden; der laufende Lauf startet im Nachlauf neu. Damit überlebt jeder Anstoß, der nach dem Entfernen kommt, als neuer Merker und löst nach Ende des Dienstes einen weiteren Lauf aus (`PathExists` prüft erneut).

### Einheiten

`veroeffentlichen.path` ist eine Vorlage mit den Platzhaltern `__DIENST__` und `__INSTANZ__`, die `einrichten.sh` wie die übrigen Vorlagen per `sed` ersetzt. `units.py` nimmt `.path` in `EINHEITEN` auf; eine fehlende installierte Einheit ist eine gesperrte Abweichung, die `veroeffentlichen.sh` als normale Meldung (Merker `units-gemeldet`, kein Alarm) meldet. `schreiben.service` trägt die neuen Grenzen; der Kommentar nennt die Messung vom 17.11.2026, den Wegfall des Kindprozesses und das Nachmessen.

### Wirkung für die Rechte

Der von der Einheit gestartete Lauf erbt kein `NoNewPrivileges`; `sudo -n` für Freischalten und ausstehende Neustarts gelingt damit direkt (Nebennutzen zu #465 und #494). Ein Neustart des Schreibdienstes beendet das Veröffentlichen nicht mehr.

### Auslieferungs- und Abnahmeschritte auf der Instanz

Nach dem Vorspulen auf `main` und dem Software-Stand auf der Instanz:

1. `betrieb/einrichten.sh --installieren` einmal ausführen (Claude, Muster #454).
2. `systemctl is-active <instanz>-veroeffentlichen.path` liefert `active`.
3. `systemctl show -p MemoryHigh -p MemoryMax -p MemorySwapMax <instanz>-schreiben` zeigt 384M, 512M, 256M (in Bytes angezeigt); `<instanz>-veroeffentlichen.service` zeigt unverändert `infinity`.
4. Ein Anstoß aus der Testreise (vorhandene eigene Testreise, nicht neu anlegen; danach zurückstellen): Eintrag über den Schreibweg, Seite ist innerhalb von zwei Minuten aktuell (Uhrzeiten mit Zeitzone im Nachweis).
5. `units.py pruefen` endet mit 0 (keine Abweichung).
6. Der Schreibdienst läuft nach dem Anstoß ohne Neustart weiter (Journal ohne Speicherabbruch, Zeile „memory peak“ unter 512M).

Der Nachweis steht ohne Serverpfade und ohne echte Reisen im Issue #624; erst danach wird es geschlossen.

## Test Plan

### Automated Tests (TDD RED)

- [ ] Test 1 (AC-1): GIVEN ein leeres Dienstverzeichnis und ein gesetztes `SB_VEROEFFENTLICHEN` WHEN `veroeffentlichen_anstossen` läuft THEN existiert `veroeffentlichen-anstoss`, und kein Kindprozess wurde gestartet (Stummel wurde nicht ausgeführt)
- [ ] Test 2 (AC-2): GIVEN `SB_VEROEFFENTLICHEN` ist leer WHEN `veroeffentlichen_anstossen` läuft THEN entsteht kein Merker
- [ ] Test 3 (AC-3): GIVEN das Dienstverzeichnis ist nicht beschreibbar WHEN `veroeffentlichen_anstossen` läuft THEN wirft die Funktion nicht und der Fehler steht im Protokoll
- [ ] Test 4 (AC-4): GIVEN ein Speichern über den Speicherweg und über den Git-Weg WHEN es gelingt THEN liegt je genau ein Merker, und die Datei `veroeffentlichen-anstoss.log` wird nicht mehr angelegt
- [ ] Test 5 (AC-5): GIVEN die Vorlage `veroeffentlichen.path` WHEN sie gelesen wird THEN enthält sie `PathExists=__DIENST__/veroeffentlichen-anstoss`, `Unit=__INSTANZ__-veroeffentlichen.service` und `WantedBy=paths.target`
- [ ] Test 6 (AC-6): GIVEN `veroeffentlichen.sh` mit gesetztem Merker und belegter Sperre WHEN das Skript startet THEN ist der Anstoß-Merker weg, `veroeffentlichen-nochmal` ist gesetzt, und es läuft nichts weiter
- [ ] Test 7 (AC-6): GIVEN `veroeffentlichen.sh` mit gesetztem Merker und freier Sperre WHEN das Skript startet THEN ist der Merker vor dem Sperrblock entfernt (Reihenfolge im Skripttext und im Lauf)
- [ ] Test 8 (AC-7): GIVEN die Vorlage `schreiben.service` WHEN sie gelesen wird THEN stehen `MemoryHigh=384M`, `MemoryMax=512M`, `MemorySwapMax=256M` darin, High ist kleiner als Max, und „bis #624“ kommt nicht mehr vor
- [ ] Test 9 (AC-8): GIVEN `einrichten.sh` WHEN der Text geprüft wird THEN erzeugt und installiert es `.path`-Vorlagen und aktiviert `<instanz>-veroeffentlichen.path`
- [ ] Test 10 (AC-9): GIVEN `units.py` WHEN `EINHEITEN` gelesen wird THEN enthält es `veroeffentlichen.path`; GIVEN die Einheit fehlt installiert WHEN `pruefen` läuft THEN ist es eine gesperrte Abweichung (Ausgang ungleich 0)
- [ ] Test 11 (AC-10): GIVEN das Root-Hilfsprogramm WHEN seine Einheitenliste gelesen wird THEN enthält sie weiterhin nur die sechs `.service`-Einheiten und keine `.path`
- [ ] Test 12 (AC-11): GIVEN `messlauf-schreibweg.py` WHEN der Text geprüft wird THEN prüft es den Merker und startet kein Skript
- [ ] Test 13 (AC-12): GIVEN `docs/betrieb.md` und `speichergrenzen-538.md` WHEN sie gelesen werden THEN beschreiben sie Merker, Path-Einheit, 512M und den Auslieferungsschritt, und „bis #624“ steht nirgends mehr als offener Zustand
- [ ] Test 14 (AC-13): GIVEN `engine/` und `betrieb/` WHEN nach `Popen` im Anstoß gesucht wird THEN startet der Anstoß keinen Prozess mehr

Geändert werden die bestehenden Tests: `test_anstoss_pfad_570.py` (alle sieben), die Stummel-Tests in `test_schreiben.py`, `test_schreiben_speicher.py`, `test_software_weg_454.py`, `test_speicher_stufe5.py`, `test_stand.py` (Merker statt Skriptlauf), `test_betrieb.py` (Speichergrenzen und Doku, ehemals 2565 bis 2592), `test_units.py`. Neu sind Test 5 bis 14 in `test_betrieb.py` bzw. `test_units.py`.

Instanz-Nachweis (AC-14) ist kein CI-Test, siehe dort.

## Expected Behavior

- **Input:** Ein erfolgreiches Speichern im Schreibweg (Speicher- oder Git-Weg).
- **Output:** Merker `veroeffentlichen-anstoss`; die Path-Einheit startet `<instanz>-veroeffentlichen.service`; das Skript entfernt den Merker, veröffentlicht, die Seite ist aktuell.
- **Side effects:** Kein Kindprozess im Schreibdienst; Speicherspitze des Schreibdienstes entfällt; kein `NoNewPrivileges` im Lauf; ein Neustart des Schreibdienstes beendet das Veröffentlichen nicht. Ohne aktive Path-Einheit veröffentlicht der Timer (bis zu fünf Minuten Latenz).

## Known Limitations

- Bis zum Einmalschritt (`einrichten.sh --installieren`) ist die Path-Einheit nicht aktiv und die fehlende Einheit eine gesperrte Abweichung mit einer einmaligen normalen Meldung; die Latenz beträgt dann bis zu fünf Minuten.
- Andere Instanzen brauchen denselben Einmalschritt je Instanz; bis dahin gilt dasselbe Übergangsverhalten.
- Läuft das Veröffentlichen schon und kommt ein weiterer Anstoß, wartet dieser bis zum Ende des laufenden Laufs (Nachlauf); die Zwei-Minuten-Marke gilt für den Normalfall eines freien Dienstes.

## Acceptance Criteria

Erfolgskriterien aus dem Issue: Der Schreibweg startet das Veröffentlichen nicht mehr selbst, eine eigene Einheit übernimmt, die Grenze des Schreibdienstes sinkt auf 512M, das Zeitziel bleibt.

- **AC-1:** (Merker statt Prozess) GIVEN ein leeres Dienstverzeichnis und ein gesetztes `SB_VEROEFFENTLICHEN` WHEN `veroeffentlichen_anstossen` läuft THEN existiert `<FR_DIENST>/veroeffentlichen-anstoss`, und das Skript wurde nicht ausgeführt. Test: `test_anstoss_pfad_570.py::test_anstoss_legt_nur_merker`.
- **AC-2:** (leer = aus) GIVEN `SB_VEROEFFENTLICHEN` ist leer WHEN der Anstoß läuft THEN wird kein Merker angelegt. Test: `test_anstoss_pfad_570.py::test_leeres_skript_legt_keinen_merker`.
- **AC-3:** (wirft nie) GIVEN das Dienstverzeichnis ist nicht beschreibbar WHEN der Anstoß läuft THEN wirft die Funktion nicht, und der Fehler steht nur im Protokoll. Test: `test_anstoss_pfad_570.py::test_anstoss_wirft_nie`.
- **AC-4:** (beide Wege, kein Anstoß-Protokoll) GIVEN ein erfolgreiches Speichern im Speicherweg und im Git-Weg WHEN es abgeschlossen ist THEN liegt der Merker, und `veroeffentlichen-anstoss.log` entsteht nicht. Test: `test_schreiben_speicher.py::test_speichern_legt_anstoss_merker`, `test_schreiben.py::test_git_weg_legt_anstoss_merker`.
- **AC-5:** (Path-Vorlage) GIVEN `betrieb/vorlagen/veroeffentlichen.path` WHEN sie gelesen wird THEN enthält sie genau `PathExists=__DIENST__/veroeffentlichen-anstoss`, `Unit=__INSTANZ__-veroeffentlichen.service` und `WantedBy=paths.target`. Test: `test_betrieb.py::test_veroeffentlichen_path_vorlage`.
- **AC-6:** (Merker vor Sperre) GIVEN `veroeffentlichen.sh` WHEN es startet, mit freier oder mit belegter Sperre THEN ist der Anstoß-Merker vor dem `flock`-Aufruf entfernt; bei belegter Sperre ist zusätzlich `veroeffentlichen-nochmal` gesetzt. Test: `test_betrieb.py::test_merker_vor_sperre_entfernt`, `test_betrieb.py::test_belegte_sperre_setzt_nochmal`.
- **AC-7:** (Grenze 512M) GIVEN `schreiben.service` WHEN sie gelesen wird THEN stehen `MemoryHigh=384M`, `MemoryMax=512M`, `MemorySwapMax=256M` darin, `MemoryHigh` ist kleiner als `MemoryMax`, und der Text „bis #624“ fehlt. Test: `test_betrieb.py::test_dauerdienste_tragen_speichergrenzen` (angepasst).
- **AC-8:** (Einrichten) GIVEN `betrieb/einrichten.sh` WHEN es Einheiten erzeugt und installiert THEN behandelt es `.path`-Vorlagen wie `.service` und `.timer` und aktiviert `<instanz>-veroeffentlichen.path`. Test: `test_betrieb.py::test_einrichten_aktiviert_path_einheit`.
- **AC-9:** (Abgleich meldet fehlende Path-Einheit) GIVEN `EINHEITEN` in `units.py` WHEN sie gelesen wird THEN enthält sie die Path-Einheit; GIVEN sie ist nicht installiert WHEN `units.py pruefen` läuft THEN ist es eine gesperrte Abweichung (Ausgang ungleich 0), und `veroeffentlichen.sh` setzt nur eine normale Meldung ab, keinen Alarm. Test: `test_units.py::test_path_einheit_in_einheiten`, `test_units.py::test_fehlende_path_einheit_ist_gesperrt`.
- **AC-10:** (Helfer unverändert) GIVEN `units-installieren.py` WHEN seine Einheitenliste gelesen wird THEN enthält sie nur die sechs `.service`-Einheiten, und `ERLAUBT` ist unverändert und gleich der in `units.py`. Test: `test_units_helfer.py::test_ac1_alle_sechs_einheiten_sind_erlaubt` (bestehend), `test_units.py::test_helfer_erlaubnisliste_gleich` (bestehend).
- **AC-11:** (Messlauf) GIVEN `betrieb/messlauf-schreibweg.py` WHEN es den Anstoß in der Sandbox prüft THEN prüft es den Merker und startet kein Skript. Test: `test_betrieb.py::test_messlauf_prueft_merker`.
- **AC-12:** (Doku) GIVEN `docs/betrieb.md` und `docs/specs/betrieb/speichergrenzen-538.md` WHEN sie gelesen werden THEN beschreiben sie Merker, Path-Einheit, die Grenze 512M, den Auslieferungsschritt und den Wegfall des Anstoß-Protokolls, und „bis #624“ steht nicht mehr als offener Zustand. Test: `test_betrieb.py::test_doku_beschreibt_veroeffentlichen_dienst`.
- **AC-13:** (kein Kindprozess) GIVEN der Quelltext von `veroeffentlichen_anstossen` WHEN er geprüft wird THEN startet er keinen Prozess (kein `Popen`, kein `subprocess`). Test: `test_anstoss_pfad_570.py::test_anstoss_startet_keinen_prozess`.
- **AC-14:** (Instanz umgestellt, Teil von „fertig“) GIVEN die Software ist ausgeliefert WHEN `einrichten.sh --installieren` einmal auf der Instanz gelaufen ist THEN gilt: `systemctl is-active <instanz>-veroeffentlichen.path` ist `active`; `systemctl show` für `<instanz>-schreiben` zeigt 384M, 512M und 256M; ein Anstoß aus der vorhandenen Testreise führt innerhalb von zwei Minuten zur aktuellen Seite; `units.py pruefen` endet mit 0; der Schreibdienst läuft ohne Speicherabbruch. Ausnahme mit Begründung: braucht systemd und Root auf dem echten Server und läuft nicht in CI; der Nachweis steht im Issue #624 (ohne Serverpfade, Uhrzeiten mit Zeitzone), erst dann wird es geschlossen.

## Definition of Done

- [ ] AC-1 bis AC-13 sind durch die genannten Tests belegt; AC-14 durch den Nachweis auf der Instanz.
- [ ] `engine/.venv/bin/python -m pytest -q -n auto engine/tests` ist ohne echte Reisen grün; die Tests der einbindenden Instanzen laufen vor dem Vorspulen mit diesem Stand.
- [ ] Prüfstelle ADR-0001 im Pull Request beantwortet (siehe unten).
- [ ] Die Instanz ist umgestellt (AC-14); erst danach wird #624 geschlossen.

## Prüfstelle ADR-0001 (kurz)

Betrieb, nicht Kern: Das Vorhaben berührt weder Grundformen der Reise-Ontologie noch Arten oder Merkmale. Nichts Reisespezifisches in der Engine; nichts Instanzspezifisches in `betrieb/` (Einheitenname, Dienstordner und Skript kommen über die Platzhalter `__INSTANZ__` und `__DIENST__` aus den Einstellungen der Instanz). Beide Reisetypen: reiseunabhängig, Tests laufen ohne echte Reisen. Keine eigene KI, keine neue Fremdbibliothek, keine Sprache im Code (der Anstoß hat keine sichtbaren Texte). Kein Widerspruch zum Kern.

## Risiken

- **Endlosschleife der Path-Einheit:** bliebe der Merker liegen, startete systemd den Dienst immer wieder. Gegenmaßnahme: Merker vor `flock` löschen (AC-6), Test auf Reihenfolge.
- **Übergang ohne aktive Path-Einheit:** Der Abgleich bringt `MemoryMax=512M` ohne Root auf die Instanz, die `.path`-Einheit nicht. Gegenmaßnahme: kein Rückfall auf `Popen`; der Timer veröffentlicht, Latenz bis fünf Minuten, einmalige normale Meldung; Auslieferung führt den Einmalschritt unmittelbar aus.
- **Latenz (#230):** bei laufendem Dienst wartet ein weiterer Anstoß bis zum Ende des Laufs. Gegenmaßnahme: Nachlauf über `PathExists` und `veroeffentlichen-nochmal`; Messung in AC-14.
- **Grenze zu eng:** 512M reicht nur, solange kein Kindprozess im Schreibdienst läuft. Gegenmaßnahme: Wegfall von `Popen` (AC-13), Nachmessen über „memory peak“, weiche Grenze 384M vor der harten.
- **Reisen-Repo der Instanz:** Dessen Tests kannten die Anstoß-Protokolldatei oder den Skriptstart. Gegenmaßnahme: Tests der einbindenden Instanz mit dem Branch vor dem Vorspulen.
- **Mehrere Instanzen auf einem Server:** Einheitenname und Merker tragen die Instanz bzw. liegen im Dienstordner der Instanz.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue
- **Rationale:** Betriebsumbau nach etablierten Mustern (Merkerdateien in `<FR_DIENST>`, systemd-Path-Einheit statt Kindprozess, Auslieferung der Einheiten per `einrichten.sh --installieren` wie bei #454); keine Architekturgrenze aus den ADRs 0001 bis 0011 wird berührt. Die Entscheidungen stehen in dieser Spec, in `docs/betrieb.md` und im Issue.

## Changelog

- 2026-11-18: Initial spec created (Issue #624; Merker und Path-Einheit statt `Popen`, `schreiben` auf 512M, Swap auf 256M)
- 2026-11-18: Nachbesserung nach Prüfung: ExecStartPre entfernt den Merker vor dem Start
