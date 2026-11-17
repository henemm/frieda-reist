---
entity_id: speichergrenzen-538
type: feature
created: 2026-11-17
updated: 2026-11-17
status: draft
version: "1.0"
tags: [betrieb, systemd, speicher, einheiten, sicherheit]
workflow: memorymax-538
---

# Speichergrenzen für die Dauerdienste der Instanz (#538)

Grundlage: `docs/context/memorymax-538.md` (Kontext, Messung, Analyse, Variantenvergleich). Vorbild für Erlaubnisliste und Meldeweg: `docs/specs/fast/units-meldung-doppelte-liste-306.md`. Abgrenzung zu den Rechten der Units: `docs/specs/betrieb/dienstrechte-552.md`, Entscheidung 8.

## Approval

- [ ] Approved

## Purpose

Die vier Dauerdienste der Instanz (Rückmeldedienst, Konnektor, Schreibweg, Push) laufen ohne Speichergrenze; ein Speicherleck in einem Dienst träfe den ganzen Server, auch über den Swap. Jeder Dienst bekommt eine weiche und eine harte Speichergrenze und eine Swap-Grenze, bemessen nach der Messung vom 17.11.2026. Damit der automatische Einheiten-Abgleich diese Zeilen ohne Handarbeit installieren und später nachstellen darf, wird die Erlaubnisliste `ERLAUBT` um drei einschränkende Schlüssel mit engem Wertmuster ergänzt.

## Entscheidungen (Tech Lead, nicht offen)

1. **Variante C gewählt** (Analyse, Variantenvergleich): je Dienst `MemoryHigh` (weiche Drossel vor dem Kill), `MemoryMax` (harte Grenze) und `MemorySwapMax`. Der Vorschlag im Issue (`MemoryMax=512M` für alle) ist verworfen: Der Schreibweg startet das Veröffentlichen als Kindprozess in seiner eigenen cgroup (Spitze 3,4 GiB), jedes Speichern würde abgeschossen.
2. **Werte nach Messung** (Spitze der letzten 60 Tage, Faktor mindestens 3, außer beim Schreibweg):

| Dienst | höchste Spitze | MemoryHigh | MemoryMax | MemorySwapMax |
|--------|----------------|-----------|-----------|---------------|
| rueckmeldungen | 42 MiB | 192M | 256M | 128M |
| push | 73 MiB | 192M | 256M | 128M |
| konnektor | 326 MiB (Chromium für das Seitenbild) | 768M | 1G | 256M |
| schreiben | 3,4 GiB (angestoßenes Veröffentlichen) | 4G | 5G | 1G |

3. **`schreiben` bleibt bewusst grob**, bis das Folge-Issue #624 das Veröffentlichen aus der cgroup des Schreibdienstes löst; danach wird die Grenze auf 512M gesenkt (eigene Änderung, eigener Wert in dieser Tabelle).
4. **`veroeffentlichen.service` bekommt keine Grenze** (eigene Einheit, kurzlebig, läuft auch unter den größten Lasten wie pytest mit mehreren Prozessen).
5. **Swap eigens begrenzen**: In cgroup v2 begrenzt `MemoryMax` nur den Arbeitsspeicher; auf der Instanz ist ein 2-GiB-Swapfile aktiv (am 17.11.2026 zu 1,6 GiB belegt). Ohne `MemorySwapMax` wiche ein Leck in den Swap aus und träfe den Server trotzdem.
6. **Erlaubnisliste statt einmaliger Root-Installation** (Variante E verworfen): Sonst bräuchte jede künftige Wertänderung wieder Root auf jeder Instanz. Ressourcengrenzen schränken nur ein und öffnen keine Rechte; der schlimmste Missbrauch ist ein Neustart des Dienstes (Verfügbarkeit), nie mehr Zugriff. Das ist die Abgrenzung zu `dienstrechte-552` Entscheidung 8 (Sandbox-Werte wie `ReadWritePaths` bleiben außerhalb der Liste).
7. **Wertmuster eng**: `^[1-9][0-9]{0,4}[MG]$`, angewendet als vollständiger Treffer (kein Zeilenumbruch am Ende). Ausgeschlossen sind `infinity`, `0`, Prozentwerte, Einheiten K und T, führende Nullen, mehr als fünf Ziffern, Kleinbuchstaben-Einheiten und Werte ohne Einheit.
8. **Einmal Root nach dem Ausliefern**: Das auf der Instanz installierte Hilfsprogramm kennt die alte Erlaubnisliste; bis es erneuert ist, ist die neue Zeile eine gesperrte Abweichung (nur eine normale Meldung, kein Alarm). Erneuert wird es bewusst mit `betrieb/einrichten.sh --installieren` (Claude hat dafür Rechte auf dieser Instanz). Die Umstellung gehört zu „fertig“.

## Source

- **Files:** `betrieb/vorlagen/{rueckmeldungen,konnektor,schreiben,push}.service`, `betrieb/units.py`, `betrieb/vorlagen/units-installieren.py`, `docs/betrieb.md`
- **Identifier:** `ERLAUBT` (in `units.py` und im Hilfsprogramm), `DAUERDIENSTE`, `abgleich()`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/units.py` (`ERLAUBT`, `abgleich()`) | Modul | Erlaubnisliste und Abgleich der installierten Units gegen die Vorlagen |
| `betrieb/vorlagen/units-installieren.py` | Root-Helfer | eigene, gleiche Erlaubnisliste; installiert nur erlaubte Abweichungen |
| `betrieb/einrichten.sh --erzeugen/--installieren` | Skript | erzeugt Units aus den Vorlagen, erneuert Helfer und sudoers (Einmalschritt) |
| `betrieb/veroeffentlichen.sh` (`units_abgleichen`) | Skript | ruft `units.py pruefen/installieren`; gesperrte Abweichung wird eine normale Meldung, entprellt über den Merker `units-gemeldet` |
| `engine/schreiben.py`, `engine/konnektor.py` | Modul | erzeugen die Lastspitzen (Veröffentlichen als Kindprozess, Chromium für `seite_ansehen`) |
| systemd mit cgroup v2 (Ubuntu 24.04) | Fremd | `MemoryHigh`, `MemoryMax`, `MemorySwapMax`, Speicher- und Swap-Buchführung |
| `docs/specs/betrieb/dienstrechte-552.md` | Spec | Entscheidung 8 wird um die Abgrenzung ergänzt |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/vorlagen/rueckmeldungen.service` | MODIFY | drei Zeilen mit Werten der Tabelle, Kommentar mit Spitze und Messdatum |
| `betrieb/vorlagen/push.service` | MODIFY | wie oben |
| `betrieb/vorlagen/konnektor.service` | MODIFY | wie oben |
| `betrieb/vorlagen/schreiben.service` | MODIFY | wie oben, Kommentar nennt #624 und den späteren Wert |
| `betrieb/units.py` | MODIFY | `ERLAUBT` um `("Service","MemoryHigh")`, `("Service","MemoryMax")`, `("Service","MemorySwapMax")` mit gemeinsamem Muster; Kopfkommentar |
| `betrieb/vorlagen/units-installieren.py` | MODIFY | dieselben Einträge, identisch zu `units.py`; Kopfkommentar |
| `engine/tests/test_units.py` | MODIFY | feste Namensliste der Erlaubnisliste erweitern, Wertmuster gut und schlecht, Gleichheit beider Listen |
| `engine/tests/test_units_helfer.py` | MODIFY | Helfer nimmt nur gültige Werte; installiert eine reine Grenz-Abweichung; lehnt ungültige ab |
| `engine/tests/test_betrieb.py` | MODIFY | jede Dauerdienst-Vorlage trägt die Grenzen, High kleiner als Max; `veroeffentlichen.service` ohne Grenze |
| `docs/betrieb.md` | MODIFY | Abschnitt „Einheiten abgleichen (#260)“ (erlaubte Zeilen) und neuer Absatz „Speichergrenzen (#538)“ mit Werten, Nachmessen, Einmalschritt |
| `docs/specs/betrieb/dienstrechte-552.md` | MODIFY | Entscheidung 8: Abgrenzung Ressourcengrenzen gegen Sandbox-Werte |

Keine Änderung: `betrieb/einrichten.sh` (kopiert Vorlagen per `sed`), `betrieb/messlauf-schreibweg.py`, `DAUERDIENSTE`, `betrieb/veroeffentlichen.sh`.

### Estimated Changes

- Files: 11
- LoC: +150/-5 (davon etwa 100 Tests)
- Risiko niedrig: nur einschränkende Zeilen; schlimmster Fall ist der Neustart eines Dienstes bei echtem Leck.

## Implementation Details

### Vorlagen

Jede der vier Vorlagen im Abschnitt `[Service]` bekommt `MemoryHigh=`, `MemoryMax=` und `MemorySwapMax=` mit den Werten aus Entscheidung 2. Davor steht ein Kommentar mit der gemessenen Spitze, dem Messdatum (17.11.2026) und dem Hinweis, wie nachgemessen wird (Journalzeile „memory peak“ des Dienstes). Die Werte sind in der Vorlage fest, nicht über Platzhalter (sie sind keine Instanz-Einstellung; eine Instanz mit anderem Bedarf ändert sie in ihrer Unit, der Abgleich übernimmt jeden Wert im erlaubten Muster).

### Erlaubnisliste

`ERLAUBT` in `units.py` und im Hilfsprogramm bekommt drei Einträge nach dem Vorbild von `TimeoutStartSec` (Schlüssel auf Muster). Das Muster ist `^[1-9][0-9]{0,4}[MG]$`, geprüft als vollständiger Treffer. Beide Listen bleiben identisch; ein vorhandener Test erzwingt die Gleichheit. Der Kopfkommentar beider Dateien nennt die erlaubten Zeilen.

### Verhalten bei altem Hilfsprogramm

Kennt das installierte Hilfsprogramm die neuen Schlüssel noch nicht, ist die Grenzzeile eine gesperrte Abweichung: `veroeffentlichen.sh` meldet sie genau einmal als normale Meldung (Merker `units-gemeldet`, kein Alarm). Bei Ausgang 4 (gemischte Abweichung) werden auch erlaubte Zeilen nicht installiert; das ist Bestand und bleibt. Nach `einrichten.sh --installieren` entfällt die Abweichung.

### Dokumentation

`docs/betrieb.md`: Die Liste der erlaubten Zeilen nennt die drei Schlüssel samt Muster; ein neuer Absatz „Speichergrenzen (#538)“ enthält die Tabelle, die Begründung, das Nachmessen, den Einmalschritt je Instanz und den Hinweis auf #624. `dienstrechte-552.md` Entscheidung 8 erhält einen Satz zur Abgrenzung.

## Test Plan

### Automated Tests (TDD RED)

- [ ] Test 1 (AC-1): GIVEN die vier Dauerdienst-Vorlagen WHEN sie gelesen werden THEN trägt jede `MemoryHigh`, `MemoryMax` und `MemorySwapMax`, und jeder Wert passt auf das Muster
- [ ] Test 2 (AC-2): GIVEN die Werte jeder Vorlage WHEN sie in Megabyte umgerechnet werden THEN ist `MemoryHigh` kleiner als `MemoryMax`
- [ ] Test 3 (AC-3): GIVEN `veroeffentlichen.service` WHEN die Vorlage gelesen wird THEN enthält sie keine der drei Zeilen
- [ ] Test 4 (AC-4): GIVEN `ERLAUBT` in `units.py` WHEN die Schlüssel gelesen werden THEN gehören die drei neuen dazu und alle früheren bleiben
- [ ] Test 5 (AC-5): GIVEN `ERLAUBT` in `units.py` und im Hilfsprogramm WHEN sie verglichen werden THEN sind sie gleich (Schlüssel und Muster)
- [ ] Test 6 (AC-6): GIVEN gültige Werte (`256M`, `1G`, `4G`, `99999M`) WHEN sie gegen das Muster geprüft werden THEN werden sie angenommen
- [ ] Test 7 (AC-7): GIVEN `infinity`, `0`, `0M`, `50%`, `512K`, `1T`, `0256M`, `100000M`, `256m`, `256`, `256M` mit angehängtem Zeilenumbruch WHEN sie geprüft werden THEN wird jeder abgelehnt, in `units.py` wie im Hilfsprogramm
- [ ] Test 8 (AC-8): GIVEN eine installierte Unit, die sich von der Vorlage nur in einer Grenzzeile mit gültigem Wert unterscheidet WHEN `units.py` und das Hilfsprogramm laufen THEN gilt die Abweichung als erlaubt und wird installiert
- [ ] Test 9 (AC-9): GIVEN eine Abweichung mit ungültigem Wert (`infinity`) WHEN `units.py pruefen` läuft THEN ist sie eine gesperrte Abweichung, und `veroeffentlichen.sh` setzt eine normale Meldung ab, keinen Alarm
- [ ] Test 10 (AC-10): GIVEN ein Hilfsprogramm mit der alten Erlaubnisliste (ohne die drei Schlüssel) WHEN die Grenzzeile abweicht THEN ist es eine gesperrte Abweichung mit genau einer normalen Meldung und demselben Merker `units-gemeldet`
- [ ] Test 11 (AC-11): GIVEN `docs/betrieb.md` WHEN gelesen THEN nennt sie die drei Schlüssel und den Abschnitt „Speichergrenzen (#538)“, und `dienstrechte-552.md` Entscheidung 8 nennt die Abgrenzung

Instanz-Nachweis (AC-12) ist kein CI-Test, siehe dort.

## Expected Behavior

- **Input:** Vorlagen der vier Dauerdienste, installierte Units der Instanz.
- **Output:** Units mit den drei Zeilen je Dienst; `units.py pruefen` endet mit 0, wenn installiert und Vorlage übereinstimmen.
- **Side effects:** Überschreitet ein Dienst `MemoryHigh`, wird er gedrosselt; überschreitet er `MemoryMax` oder `MemorySwapMax`, beendet systemd Prozesse seiner cgroup (Neustart durch den Dienst-Manager nach den vorhandenen `Restart=`-Vorgaben). Beim Schreibweg bedeutet das für ein laufendes angestoßenes Veröffentlichen: kein Fehler an den Aufrufer, die Sperre ist frei, der Timer (alle 5 Minuten) holt nach.

## Known Limitations

- `schreiben` trägt bis #624 die grobe Grenze (4G/5G), weil das angestoßene Veröffentlichen in seiner cgroup läuft; der Schutz gegen ein Leck im Schreibweg selbst ist dort schwächer.
- Nebenbefunde, nicht Teil dieser Spec: Das angestoßene Veröffentlichen erbt `NoNewPrivileges=yes` (#465), und ein Neustart von `schreiben` beendet ein laufendes angestoßenes Veröffentlichen mit (`KillMode=control-group`).
- Andere Instanzen brauchen den Einmalschritt (`einrichten.sh --installieren`) je Instanz; bis dahin eine einmalige normale Meldung.
- Die Werte sind Messwerte vom 17.11.2026 und müssen bei deutlich gewachsener Last nachgemessen werden (Anleitung in `docs/betrieb.md`).
- Die Abgrenzung zu Spec 552 steht als datierter Nachtrag zu Entscheidung 8 im Changelog von `dienstrechte-552.md`, nicht im Text der Entscheidung selbst: Deren freigegebener Teil gehört zu einem abgeschlossenen Workflow und ist gesperrt. Inhaltlich ist es dieselbe Abgrenzung.

## Acceptance Criteria

Erfolgskriterien aus dem Issue: Ein Speicherleck in einem Dauerdienst trifft nicht den ganzen Server; der Einheiten-Abgleich installiert die Zeilen ohne Handarbeit; die Instanz ist umgestellt.

- **AC-1:** (Grenzen vorhanden) GIVEN die Vorlagen `rueckmeldungen`, `push`, `konnektor`, `schreiben` WHEN sie gelesen werden THEN enthält jede genau eine Zeile `MemoryHigh=`, `MemoryMax=` und `MemorySwapMax=` mit den Werten aus Entscheidung 2. Test: `test_betrieb.py::test_dauerdienste_tragen_speichergrenzen`.
- **AC-2:** (weich vor hart) GIVEN die Werte einer Vorlage WHEN sie in Megabyte umgerechnet werden (G = 1024 M) THEN ist `MemoryHigh` kleiner als `MemoryMax`. Test: `test_betrieb.py::test_speicher_high_kleiner_max`.
- **AC-3:** (Veröffentlichen ohne Grenze) GIVEN `veroeffentlichen.service` WHEN die Vorlage gelesen wird THEN steht keine Zeile `MemoryHigh`, `MemoryMax` oder `MemorySwapMax` darin. Test: `test_betrieb.py::test_veroeffentlichen_ohne_speichergrenze`.
- **AC-4:** (Erlaubnisliste erweitert) GIVEN `ERLAUBT` in `units.py` WHEN die Schlüssel gelesen werden THEN enthält sie genau die früheren Einträge plus `("Service","MemoryHigh")`, `("Service","MemoryMax")`, `("Service","MemorySwapMax")`, und keine Sandbox- oder Benutzerzeile. Test: `test_units.py::test_erlaubnisliste_schluessel` (bestehender Test, feste Namensliste erweitert).
- **AC-5:** (Listen gleich) GIVEN `ERLAUBT` in `units.py` und im Hilfsprogramm WHEN sie verglichen werden THEN sind sie in Schlüsseln und Mustern identisch. Test: `test_units.py::test_helfer_erlaubnisliste_gleich` (bestehender Test).
- **AC-6:** (gültige Werte) GIVEN die Werte `256M`, `1G`, `4G`, `99999M` WHEN sie gegen das Muster geprüft werden THEN werden sie angenommen, in `units.py` und im Hilfsprogramm. Test: `test_units.py::test_speicherwert_gueltig`, `test_units_helfer.py::test_speicherwert_gueltig`.
- **AC-7:** (Negativfälle des Musters) GIVEN `infinity`, `0`, `0M`, `50%`, `512K`, `1T`, `0256M`, `100000M` (zu lang), `256m`, `256` (ohne Einheit) und `256M` mit Zeilenumbruch am Ende WHEN sie geprüft werden THEN wird jeder abgelehnt, in `units.py` wie im Hilfsprogramm. Test: `test_units.py::test_speicherwert_ungueltig`, `test_units_helfer.py::test_speicherwert_ungueltig`.
- **AC-8:** (Installation einer Grenz-Abweichung) GIVEN eine installierte Unit, die sich von der Vorlage nur in einer Grenzzeile mit gültigem Wert unterscheidet WHEN der Abgleich läuft THEN gilt sie als erlaubte Abweichung und das Hilfsprogramm installiert sie; GIVEN sie enthält zusätzlich eine nicht erlaubte Zeile THEN installiert das Hilfsprogramm nichts. Test: `test_units_helfer.py::test_grenzabweichung_wird_installiert`, `test_units_helfer.py::test_gemischte_abweichung_wird_nicht_installiert`.
- **AC-9:** (ungültiger Wert gesperrt) GIVEN eine Grenzzeile mit ungültigem Wert WHEN `units.py pruefen` läuft THEN ist sie eine gesperrte Abweichung (Ausgang ungleich 0), das Hilfsprogramm installiert nichts, und `veroeffentlichen.sh` setzt nur eine normale Meldung ab, keinen Alarm. Test: `test_units.py::test_ungueltige_grenze_ist_gesperrt`, `test_betrieb.py::test_units_abweichung_nur_normale_meldung` (bestehende Prüfung der Meldestufe um diesen Fall ergänzt).
- **AC-10:** (alter Helfer) GIVEN ein Hilfsprogramm mit der alten Erlaubnisliste ohne die drei Schlüssel WHEN eine Grenzzeile abweicht THEN ist sie eine gesperrte Abweichung, die genau eine normale Meldung auslöst (Merker `units-gemeldet`, kein Alarm, keine Wiederholung bei jedem Lauf). Test: `test_units.py::test_alter_helfer_nur_normale_meldung`.
- **AC-11:** (Doku) GIVEN `docs/betrieb.md` und `docs/specs/betrieb/dienstrechte-552.md` WHEN sie gelesen werden THEN nennt `betrieb.md` die drei Schlüssel, das Muster, die Werte und den Einmalschritt (Absatz „Speichergrenzen (#538)“), und Entscheidung 8 der Spec 552 nennt die Abgrenzung Ressourcengrenzen gegen Sandbox-Werte. Test: `test_betrieb.py::test_doku_beschreibt_speichergrenzen`.
- **AC-12:** (Instanz umgestellt, Teil von „fertig“) GIVEN die Software ist ausgeliefert WHEN `einrichten.sh --installieren` einmal mit Root-Rechten auf der Instanz gelaufen ist THEN liefert `systemctl show -p MemoryHigh -p MemoryMax -p MemorySwapMax <dienst>` für jeden der vier Dienste die Werte aus Entscheidung 2, `veroeffentlichen.service` zeigt `infinity`, `units.py pruefen` endet mit 0, und Schreiben, Veröffentlichen und ein Seitenbild über den Konnektor laufen danach ohne Fehler durch. Ausnahme mit Begründung: Der Nachweis braucht systemd und Root auf dem echten Server und läuft nicht in CI; er wird im Issue #538 festgehalten (ohne Serverpfade), erst dann wird es geschlossen.

## Definition of Done

- [ ] AC-1 bis AC-11 sind durch die genannten Tests belegt; AC-12 durch den Nachweis auf der Instanz.
- [ ] `engine/.venv/bin/python -m pytest -q -n auto engine/tests` ist ohne echte Reisen grün; die Tests der einbindenden Instanzen laufen vor dem Vorspulen mit diesem Stand (Units und Erlaubnisliste ändern sich).
- [ ] Folge-Issue #624 (Veröffentlichen aus der cgroup des Schreibdienstes lösen, danach `schreiben` auf 512M) ist angelegt und in `docs/betrieb.md` und in der Vorlage `schreiben.service` genannt.
- [ ] Die Instanz ist umgestellt (AC-12); erst danach wird #538 geschlossen.

## Offene Punkte für den Product Owner

- **Sicherheitsentscheidung (fällt mit der Spec-Freigabe):** Neue Einträge in `ERLAUBT` sind laut `docs/betrieb.md` eine Sicherheitsentscheidung des Product Owners. Gefragt ist die Freigabe von `MemoryHigh`, `MemoryMax` und `MemorySwapMax` mit dem Muster `^[1-9][0-9]{0,4}[MG]$`. Empfehlung: freigeben. Die Zeilen können nur einschränken (kein `infinity`, keine 0, keine Prozent- oder K/T-Werte), öffnen keine Rechte, und der schlimmste Missbrauch ist der Neustart eines Dienstes. Die Alternative (Zeilen nur per Root-Schritt, ohne Erlaubnisliste) vermeidet den Eintrag, verlangt aber bei jeder künftigen Wertänderung Root auf jeder Instanz.

## Prüfstelle ADR-0001 (kurz)

Betrieb, nicht Kern: Das Vorhaben berührt weder Grundformen der Reise-Ontologie noch Arten oder Merkmale; nichts Reisespezifisches in der Engine, nichts Instanzspezifisches in `betrieb/` (Werte stehen in den Vorlagen, Benutzer und Pfade kommen wie bisher aus den Einstellungen). Beide Reisetypen: reiseunabhängig, Tests laufen ohne echte Reisen. Keine eigene KI, keine neue Fremdbibliothek, keine Sprache im Code. Kein Widerspruch zum Kern.

## Risiken

- **Grenze zu eng:** Ein Dienst wird bei einer unerwarteten Spitze gedrosselt oder neu gestartet. Gegenmaßnahme: Faktor mindestens 3 über der Spitze von 60 Tagen, weiche Grenze vor der harten, Nachmessen in `docs/betrieb.md`.
- **Veröffentlichen unter `schreiben`:** zu knappe Grenze würde Veröffentlichen abbrechen; darum bleibt die Grenze grob (5G) bis #624. Folge eines Abbruchs: Timer holt nach.
- **Henne-Ei beim Hilfsprogramm:** bis zum Einmalschritt eine einmalige normale Meldung (AC-10), kein Alarm.
- **Swap-Buchführung:** `MemorySwapMax` wirkt nur bei aktiver Swap-Buchführung des Kernels; der Nachweis (AC-12) prüft die Werte per `systemctl show`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue
- **Rationale:** Betriebshärtung nach etabliertem Muster (systemd-Ressourcengrenzen, Erlaubnisliste mit engem Wertmuster wie bei `TimeoutStartSec`, #260); keine Architekturgrenze aus den ADRs 0001 bis 0011 wird berührt. Die Entscheidungen stehen in dieser Spec, in `docs/betrieb.md` und im Issue.

## Changelog

- 2026-11-17: Initial spec created (Issue #538, Variante C aus der Analyse)
- 2026-11-17: Abgrenzung zu Spec 552 als Nachtrag zu Entscheidung 8 in deren Changelog statt im gesperrten Entscheidungstext (Entscheidung Tech Lead); Test `test_doku_beschreibt_speichergrenzen` liest den Changelog
