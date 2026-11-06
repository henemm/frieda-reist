# Adversary Dialog — speicher-348-stufe3
Spec: docs/specs/betrieb/speicher-348-stufe3.md
Datum: 2026-11-06 20:23

## Checkliste
- [x] **AC-1 Materialisieren:** Given eine importierte Beispielreise / When `materialisieren` läuft / Then entspricht der Ordner Byte für Byte `beispiel/reisen/<reise>` (gleiche Pfadmenge, gleiche Bytes, ohne `.git`), `<ordner>.stand` nennt die Stand-Nummer, und ein zweiter Aufruf auf einen vorhandenen Ordner ersetzt ihn, ohne alte Dateien zu behalten (eine zwischendurch gelöschte Datei fehlt).
- [x] **AC-2 Konsistente Nummer:** Given `materialisieren` hat Stand N exportiert / When danach ein Vorgang N+1 eintrifft / Then bleibt `<ordner>.stand` bei N, und `stand_nummer` meldet N+1.
- [x] **AC-3 Vergleich ohne Unterschied:** Given beide Beispielreisen importiert / When `vergleichen <reise> beispiel/reisen/<reise>` läuft / Then Ausgabe `gleich`, Exit 0 (Akzeptanz aus #348).
- [x] **AC-4 Vergleich mit Unterschieden:** Given eine geänderte, eine gelöschte und eine neue Datei im Ordner / When `vergleichen` läuft / Then je eine Zeile `verschieden`, `nur im Speicher`, `nur im Ordner`, am Ende `3 Unterschiede`, Exit 1.
- [x] **AC-5 Vergleich: Fehler:** Given unbekannte Reise / fehlender Ordner / Symlink im Ordner / gesperrte Datenbank (Schreibsperre einer zweiten Verbindung über die Wartezeit hinaus) / falsche Angaben / When `vergleichen` läuft / Then Exit 2 mit einer Zeile `ERROR: …`, nichts wird geschrieben.
- [x] **AC-6 Vergleich über Prüfsummen:** Given ein Speicher mit einer Reise mit großen Dateien / When `vergleichen` läuft / Then werden keine Inhalte als Bytes gelesen (der Test ersetzt `aktueller_stand` durch eine Falle, die scheitert; der Vergleich nutzt `_stand(..., "pruefsumme")`).
- [x] **AC-7 Vergleichslauf mit Stempel:** Given ein Bauordner mit Git-Reise `beispielreise` und dieselbe Reise im Speicher / When `betrieb/vergleichslauf.sh` läuft / Then Exit 0 und `vergleich/beispielreise.json` mit `ergebnis: gleich`, `stand`, `git`, `zeit`; nach einer Änderung im Speicher Exit 1 und `ergebnis: unterschied`; ein Fehler bei der einen Reise (Reise nur im Speicher, ohne Git-Ordner wird übersprungen; kaputter Speicher) bricht die andere nicht ab, Gesamt-Exit 2; der Bauordner bleibt unverändert (`git status` leer).
- [ ] **AC-8 Messung:** Given die erfundene 110-MB-Testreise aus dem Messlauf von #347 (`betrieb/messlauf-schreibweg.py --auffuellen 110`, Ordner bleibt erhalten) / When Materialisieren und Vergleichen auf dem Server der Instanz gemessen werden / Then stehen die Zeiten im Issue #348 und liegen unter den Zielen aus „Zeitziele“. Nachweis, kein automatischer Test; der Kurzlauf des Messskripts bleibt Test (`test_messlauf_skript_gibt_kennzahlen_aus`).
- [ ] **AC-9 Eine Testreise vollständig über die Datenbank bis zur Seite (Akzeptanz #348):** Given je ein Bauordner mit `FR_SPEICHERREISEN=<reise>` und die Beispielreise `beispielreise` bzw. `stadtwochenende` nur im Speicher / When ein Schreibvorgang (z. B. eine Frage anlegen, Stufe-2-Weg) den Stand erhöht und `veroeffentlichen.sh` läuft / Then entsteht `<FR_SEITEN>/<reise>/` mit `index.html`, `sw.js`, `manifest.json`, `daten.json` trägt `reise_stand.nummer` = `stand_nummer`, die neue Frage steht in den Daten, `…lauf.json` zeigt `veroeffentlicht`, `publish_status` (`stand.lesen`) meldet „enthalten“. Dasselbe gilt für beide Reisetypen. Der Browser-Rundgang der Prüfstelle (Frage 8) wird auf dem Server der Instanz mit einer Testreise abgenommen (`betrieb/pruefsitzung.py`, nie mit einer echten Reise).
- [x] **AC-10 Neu gebaut wird nach der Nummer:** Given eine veröffentlichte Speicher-Reise / When kein Vorgang dazukommt / Then baut der Lauf sie nicht (`deploy` wird nicht aufgerufen); When ein Vorgang dazukommt / Then wird genau diese Reise gebaut und keine andere; `git diff` spielt keine Rolle (der Git-Stand bleibt gleich).
- [x] **AC-11 Gemischter Betrieb:** Given eine Git-Reise A und eine Speicher-Reise B in einer Instanz / When ein Inhalt von A (Commit auf `main`) und einer von B (Vorgang) kommen / Then werden beide gebaut, die Stand-Datei `veroeffentlicht` trägt den Commit-SHA wie bisher, B hat ihre Nummer in `…lauf.json`, A bleibt bei der Git-Nummer; scheitert der Bau von A (Exit 2), wird B trotzdem veröffentlicht und umgekehrt (Rot-Datei `art=reise`, `reisen=` nennt die rote); ein Software-Wechsel baut alle Reisen beider Quellen.
- [x] **AC-12 Ohne Einstellung ändert sich nichts:** Given `FR_SPEICHERREISEN` leer oder nicht gesetzt / When `veroeffentlichen.sh`, `deploy.sh` und `freischalten.sh` laufen / Then rufen sie weder `reisespeicher.py` noch `python` für den Speicher auf (Attrappe `FR_PYTHON` protokolliert), die Ausgaben, Stempel und Dateien sind die der bisherigen Tests; alle bestehenden Tests in `test_betrieb.py` bleiben ohne geänderte Erwartung grün.
- [x] **AC-13 Ohne GitHub (Akzeptanz #348):** Given eine Speicher-Reise, ein Bauordner, dessen `origin` nicht erreichbar ist (Pfad existiert nicht), ein `gh`-Stub im `PATH`, der eine Marke schreibt und scheitert, `VF_LSREMOTE` scheiternd / When ein Schreibvorgang kommt und `veroeffentlichen.sh` läuft / Then ist die Seite der Speicher-Reise gebaut und veröffentlicht, die Marke fehlt (kein `gh` im Speicher-Teil), der Lauf endet wie bisher mit Fehler wegen `git fetch` und setzt weder `veroeffentlichen-erfolg` noch den Heartbeat. Ein Schreibvorgang über den Dienst ohne Netz gelingt (Stufe 2, `engine/tests/test_schreiben_speicher.py`, kein git).
- [x] **AC-14 Speicher-Teil vor dem Netz:** Given `git fetch` hängt oder scheitert / When der Lauf startet / Then ist der Speicher-Teil vor dem ersten `git fetch` gelaufen (Reihenfolge im Protokoll).
- [x] **AC-15 Ein Fehler hält nicht alle an:** Given eine Speicher-Reise, deren Bau scheitert (Exit 2) / When der Lauf endet / Then steht die Reise in der Rot-Datei, die Seite bleibt auf dem letzten guten Stand, `…lauf.json` zeigt `fehlgeschlagen` mit Grund, kein Stempel und kein Heartbeat; Given eine Infrastruktur-Störung (`deploy` Exit 1) / Then Exit 1 des Laufs, nichts gemerkt, der nächste Lauf wiederholt.
- [x] **AC-16 Stand-Nummer der Seite gehört zum Inhalt:** Given `materialisieren` hat Stand N festgehalten / When vor dem Bau ein Vorgang N+1 eintrifft / Then trägt die gebaute Seite `reise_stand.nummer` = N und die Änderungsliste endet bei N; der nächste Lauf baut N+1.
- [x] **AC-17 Freischalten findet die Reise:** Given eine Speicher-Reise ohne `reisen/<reise>` in Git / When `freischalten.sh` läuft / Then findet es `reise.yaml` im Bau-Ordner und schaltet frei wie bei Git-Reisen.
- [x] **AC-18 Die Liste lesen Shell und Python gleich:** Given `FR_SPEICHERREISEN=" a , ,b ,"` / When `ist_speicherreise` und `instanz.speicherreisen()` fragen / Then liefern beide `a` und `b`, sonst nichts.
- [x] **AC-19 Modullisten:** Given `deploy.sh` / When die Listen gegen die Importe geprüft werden / Then enthält jede Liste, die `stand.py` trägt, `reisespeicher.py`; der bestehende Test der Modullisten (`test_betrieb.py`) bleibt grün; `test_reisespeicher.py::test_jede_modulliste_mit_stand_traegt_reisespeicher` ersetzt den Stufe-2-Test.
- [x] **AC-20 Umstellen in einem Vorgang:** Given eine Speicher-Reise, die noch das alte Format trägt (Beispielreise mit entferntem `sprache:` in `reise.yaml` und `typ:` statt `art:` an einer Unterkunft; Städtewochenende mit entferntem `sprache:`) / When `neu.py nachziehen-speicher <reise> <ordner>` läuft / Then entsteht **genau ein** Vorgang (Person „Software-Nachziehen“, Werkzeug `nachziehen`, Grund mit den Meldungen, Kennung), die Stand-Nummer steigt um 1, und der Export des neuen Stands entspricht dem Ergebnis von `neu.py nachziehen` auf einer Kopie des Ordners.
- [x] **AC-21 Idempotent:** Given eine bereits umgestellte Reise / When der Befehl erneut läuft / Then `nichts umzustellen`, Exit 0, kein Vorgang, Nummer gleich; derselbe Lauf zweimal hintereinander (auch mit gleicher Kennung) trägt nie doppelt ein.
- [x] **AC-22 Probebau vor dem Eintragen:** Given eine Umstellung, nach der der Bau scheitert (eine Reise, die die neue Software nicht baut; im Test durch eine Attrappe des Probebaus erzwungen) / When der Befehl läuft / Then Exit 2, keine Zeile im Speicher, Stand unverändert.
- [x] **AC-23 Wettlauf mit dem Schreibweg:** Given zwischen Materialisieren und Eintragen schreibt der Schreibweg einen Vorgang / When der Befehl einträgt / Then `StandGeaendert`, neu materialisiert und umgestellt (kein Verlust der Schreib-Änderung), höchstens dreimal; nach drei Fehlschlägen Exit 1 und kein Vorgang des Nachziehens.
- [x] **AC-24 Ohne Daten kein Vorgang:** Given eine Reise in der Liste ohne Eintrag im Speicher oder mit leerem Stand / When der Speicher-Teil läuft / Then wird sie übersprungen (Hinweis im Protokoll), kein Fehler, kein Aufruf des Befehls.
- [x] **AC-25 Server stellt beim Software-Wechsel um:** Given ein Bauordner mit Speicher-Reise (alte Software-Kennung im Stempel `.gebaut`) und ein Software-Wechsel (Submodul auf neuen Stand, Tests der Software grün per `VF_PRUEFEN`) / When `veroeffentlichen.sh` (mit Nachlauf) läuft / Then ruft der Speicher-Teil `nachziehen-speicher` auf, baut danach und setzt den neuen Stempel; ohne Software-Wechsel ruft er den Befehl nicht auf (Attrappe protokolliert).
- [x] **AC-26 Ungeprüfte Software wird nicht übernommen:** Given ein Software-Wechsel mit rotem Tor (`VF_PRUEFEN` scheitert) / When der Lauf endet / Then bleibt der Stempel `.gebaut` der Speicher-Reisen bei der alten Kennung, der Befehl wird nicht aufgerufen, der Speicher-Teil baut nichts (auch keine Inhaltsänderung; Hinweis im Protokoll), und die Rot-Datei meldet `art=software`.
- [x] **AC-27 Rot ohne `gh`:** Given eine Speicher-Reise, die nach dem Software-Wechsel nicht baut / When der Lauf endet / Then steht die Reise in der Rot-Datei (`art=reise`), `alarm_pruefen` meldet nach der Schwelle über `FR_MELDEN` und ruft `rot-melden` (`VF_ROTMELDEN`), und ein `gh`-Stub im `PATH` wird nie gerufen.
- [ ] **AC-28 Workflow überspringt Speicher-Reisen:** Given ein Reisen-Repo mit Git-Reise A und Speicher-Reise B (Liste in `betrieb/einstellungen.env`) und ein alter Stand / When `software-nachziehen.sh` läuft / Then wird nur A umgestellt (kein Bot-Commit in `reisen/B`) und geprüft; mit leerer Liste ändert sich das Verhalten nicht (bestehende Tests grün).
- [x] **AC-29 Keine neue Einheit:** Given die Vorlagen unter `betrieb/vorlagen/` / When `units.py pruefen` und der Test der Vorlagen laufen / Then gibt es keine neue `.service` oder `.timer`, und `ERLAUBT` in `units.py` ist unverändert.
- [x] **AC-30 Kein Handschritt (#250):** Given eine Instanz mit Speicher-Reise und ein neuer Software-Stand, der eine Umstellung verlangt / When der Stand im Bauordner ankommt / Then stellen die Läufe die Reise um, ohne dass jemand `neu.py` aufruft; die Dokumentation (`docs/betrieb.md`) nennt keinen Handschritt nach einem Software-Wechsel.
- [x] **AC-31 Zustand der Sicherung:** Given kein Speicher / eine frische Sicherung / eine Sicherung älter als die Frist / eine Datenbank ohne Sicherung / eine nicht lesbare Datenbank / When `zustand` läuft / Then Exit 0 / 0 / 1 / 1 / 2, die Zeilen nennen Alter und Zahl der Reisen, und der Befehl schreibt nichts (Änderungszeit der Datenbank und der Sicherung unverändert).
- [x] **AC-32 Stempel `.gebaut`:** Given ein gelungener Deploy einer Speicher-Reise / When der Lauf endet / Then enthält `…gebaut` `<nummer> <kennung>`; nach einem gescheiterten Bau bleibt er unverändert.
- [ ] **AC-33 Dokumentation und Issue:** Given die Änderung / When `docs/betrieb.md` gelesen wird / Then beschreibt der Abschnitt Überwachung die vier Zustände mit Befehl und Schwelle; im Infra-Repo der Instanz liegt das Issue für den Teil-Check und ist in #348 verlinkt (Nachweis, kein Test).


## Dialog

Testlauf: `docs/artifacts/speicher-348-stufe3/adversary-test-output.txt` (test_speicher_stufe3, test_betrieb, test_reisespeicher, test_software_nachziehen: 231 passed, 0 failed, 0 übersprungen). Ganzsuite laut Auftrag 1687 passed.

### Runde 1
**Adversary:** Statische Prüfung aller Diffs plus Gegenversuche (Wegwerf-Skripte, danach gelöscht).

Finding:
  ID: F001
  Severity: HIGH
  Category: edge_case
  Code reference: engine/neu.py:1001
  Description: `nachziehen_speicher` ruft `nachziehen(ordner)` ohne Schutz auf; der Befehl in `main` (engine/neu.py:1303) fängt nur KeyError, ValueError, OSError und sqlite3.Error. Jede andere Ausnahme (etwa yaml.YAMLError bei kaputter `reise.yaml` im Speicher) endet als Traceback mit Exit 1.
  Spec requirement: AC-15 / Teil 3 — Exit 2 des Befehls zählt wie ein gescheiterter Bau, nur diese Reise ist rot, die anderen laufen weiter; Exit 1 nur für Infrastruktur.
  Conflict: Reproduktion (Fixture `sp`, Reise `stadtwochenende`, Vorgang mit unlesbarer `reise.yaml`, dann Software-Wechsel, `veroeffentlichen.sh`): Lauf endet mit Exit 1 und der Zeile "ERROR: stadtwochenende cannot be read from the trip store (… line: 2), the next run tries again." (betrieb/veroeffentlichen.sh:146, Zweig `*)` im Speicher-Teil gibt `return 1`). Der Speicher-Teil läuft vor dem Netzabruf; `speicher_reisen_lauf || return 1` stoppt damit den Git-Teil und alle weiteren Speicher-Reisen, in jedem 5-Minuten-Lauf erneut. Eine einzige Reise hält die ganze Instanz an. Nur der Probebau ist in `except Exception` gefasst, das Umstellen selbst nicht.
  Remediation: `nachziehen(ordner)` in dieselbe Ausnahmebehandlung wie den Probebau legen (jede Ausnahme außer sqlite3/OSError des Speichers: Exit 2, nichts geschrieben).

Finding:
  ID: F002
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/vergleichslauf.sh:37
  Description: Die Zeile `staende=... || staende=""` verschluckt den Fehler von `reisespeicher.py staende`. Im Modus ohne Reiseliste (`alle=1`) hat dann keine Reise einen Stand, jede wird mit "has no entry in the trip store" übersprungen.
  Spec requirement: AC-7 / Teil 1 — kaputter Speicher ist ein Fehler, Gesamt-Exit 2; Stempel `fehler`.
  Conflict: Reproduktion (Datenbank durch Müll ersetzt, `vergleichslauf.sh` ohne Argument): Exit 0, kein Stempel, nur Hinweiszeilen. Der Test `test_vergleichslauf_schreibt_stempel_und_exit_codes` prüft nur den Aufruf mit benannter Reise und fehlendem Speicher (dort kommt Exit 2 über `vergleichen`). Ein Vergleichslauf, der bei nicht lesbarer Datenbank "in Ordnung" meldet, ist die Voraussetzung zum Umschalten in Stufe 5 und damit irreführend.
  Remediation: Scheitert `staende`, im Modus ohne Liste Exit 2 mit der Fehlerzeile (kein stilles Überspringen); Test dafür.

Finding:
  ID: F003
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/gemeinsam.sh:117
  Description: `ist_speicherreise` ist eine Pipe aus `speicherreisen` und `grep -qxF`. Die aufrufenden Skripte setzen `set -euo pipefail` (betrieb/deploy.sh:7, betrieb/veroeffentlichen.sh:45, betrieb/freischalten.sh:18). `grep -q` beendet sich beim ersten Treffer; schreibt `printf` danach noch weitere Zeilen, stirbt der Schreiber mit SIGPIPE (141) und die Pipeline gilt als Fehlschlag.
  Spec requirement: AC-18 — die Shell liest die Liste wie Python; Entscheidung 3, Quelle je Reise.
  Conflict: Messung mit nachgebauter Funktion: Liste "a,b", Frage nach "a": 3 von 3000 Aufrufen falsch negativ; Liste mit 3000 Namen 200 von 200. Folge: eine Speicher-Reise gilt kurz als Git-Reise (deploy.sh meldet "Trip does not exist", Exit 1, Lauf gestoppt; `reise_stand_schreiben` und `reisen_des_laufs` verhalten sich anders). Selten, aber nicht deterministisch, und nur bei Reisen, die nicht die letzte der Liste sind.
  Remediation: ohne Pipe prüfen (Liste in eine Variable lesen und per Here-String mit grep prüfen, oder eine Schleife mit Vergleich).

Finding:
  ID: F004
  Severity: LOW
  Category: spec_violation
  Code reference: betrieb/software-nachziehen.sh:82
  Description: Der Workflow liest `FR_SPEICHERREISEN` mit `tail -1` (letzte Zeile gewinnt) und nur aus der Datei; `fr_einlesen` (betrieb/gemeinsam.sh:61) nimmt die erste Zeile und lässt einen gesetzten Wert aus der Umgebung gelten. Bei doppelter Zeile oder Wert nur in der Umgebung (systemd) sieht der Workflow eine andere Liste als der Server.
  Spec requirement: AC-28 — Workflow überspringt genau die Speicher-Reisen der Instanz.
  Conflict: Der Workflow stellt dann eine veraltete Kopie in Git um (Bot-Commit ohne Wirkung, verfälscht den Vergleichslauf). Kein Datenverlust.
  Remediation: `head -1` wie `fr_einlesen`; Hinweis in der Doku, dass die Liste in der Datei stehen muss.

Finding:
  ID: F005
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/tests/test_software_nachziehen.py:1
  Description: Die Spec ordnet AC-28 den Test `test_speicher_reisen_werden_im_workflow_uebersprungen` in dieser Datei zu; die Datei ist unverändert, der Test fehlt. Ebenso fehlt der in "Fehler- und Randfälle" verlangte Test mit einer Reise ohne Pläne (Status Idee) in test_speicher_stufe3.py (14 Tests, kein Treffer auf "Idee"). Den Workflow-Teil konnte ich nicht selbst fahren (der Dateiname der Einstellungen sperrt der Secrets-Hook).
  Spec requirement: AC-28, Definition of Done "jede AC durch automatischen Test belegt".
  Conflict: AC-28 ist nur durch Lesen belegt.
  Remediation: Test nachliefern.

Finding:
  ID: F006
  Severity: LOW
  Category: spec_violation
  Code reference: betrieb/veroeffentlichen.sh:156
  Description: Eine rote Reise im Git-Teil (Stand nicht gemerkt, Rot-Datei) hält den Software-Wechsel für Speicher-Reisen an: `geprueft` gilt nur, wenn `veroeffentlicht` die neue Kennung trägt, und der Hinweis "waits at its last good state" gilt dann auch für Inhaltsänderungen. Entspricht Entscheidung 7 (spec-konform), widerspricht aber dem Schwerpunkt "rote Reise hält andere nicht auf" in der Wirkung.
  Spec requirement: Entscheidung 7, AC-26.
  Conflict: Absicht der Spec; nur zur Kenntnis, kein Defekt der Umsetzung.
  Remediation: keine in dieser Stufe.

Konkret geprüft und gehalten: Ersetzen des Ordners (Umbenennen statt halber Ordner, `engine/reisespeicher.py:413`), Wettlauf mit höchstens drei Versuchen, Stempel und Heartbeat nur bei Erfolg beider Teile, Reise ohne Eintrag in der Liste (leere Liste: Rückkehr vor jedem Python-Aufruf, `betrieb/veroeffentlichen.sh:146`), Vergleich liest nur Prüfsummen und öffnet die Datenbank `mode=ro` (`engine/reisespeicher.py:393`, :442), Exit-Codes von `vergleichen` bei `--bis abc`, `--bis 999`, unbekannter Reise: jeweils 2. Echter Bau einer materialisierten Reise mit `bauen.py --reisen <Ordner>`: `reise_stand.nummer` stimmt (`engine/stand.py:151`).

**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Zweiter Durchgang gegen die nicht automatisch getesteten ACs.

- AC-16: `engine/stand.py:129` liest `<ordner>.stand` und begrenzt `verlauf(bis=)`; Gegenprobe mit materialisiertem Stand 1 und anschließendem Bau: Seite trägt Nummer 1. Gehalten.
- AC-17: `betrieb/freischalten.sh:39` findet `reise.yaml` über `FR_REISENORDNER` oder `<FR_DIENST>/bau/reisen`. Gehalten (Test `test_freischalten_findet_speicher_reise` grün).
- AC-9: Der Shell-Test benutzt eine Deploy-Attrappe; das echte `betrieb/deploy.sh` (Speicher-Modus, Zeile 35) wird nirgends gefahren. Ersatzprobe: `bauen.py --reisen <materialisierter Ordner>` erzeugt `index.html`, `manifest.json`, `daten.json` mit richtiger Nummer; `deploy.sh` selbst nicht gefahren. Browser-Rundgang und Nachweis in #348 fehlen (Issue hat einen Kommentar, ohne Messwerte oder Verweis auf ein Infra-Issue).
- AC-8: Ersatzmessung lokal mit 110 Zufallsfotos à 1 MB: importieren 0,9 s, materialisieren 0,8 s, vergleichen 0,2 s, Ziele (5 s, 10 s) deutlich unterschritten; die Messung auf dem Server der Instanz mit Eintrag im Issue #348 steht aus.
- AC-33: `docs/betrieb.md` beschreibt die vier Zustände mit Befehl und Schwelle (Abschnitt Überwachung). Das Issue im Infra-Repo und der Link in #348 sind nicht nachweisbar.
- AC-28: siehe F004/F005; Lesung: Umstellen und Tor überspringen die Reise (`betrieb/software-nachziehen.sh:100`, :131), leere Liste lässt alles unverändert.
- Nicht gewertet (entschieden): Reise ohne Stempel `.gebaut`, Teil-3-Satz "oder keinen Stempel".

**Implementierer:** (nicht beteiligt)

## Confirmations

Confirmation:
  AC: AC-1, AC-2
  Code reference: engine/reisespeicher.py:413
  Evidence: erst `<ordner>.neu` exportieren, dann umbenennen; Nummer vorher gelesen, `.stand` neben dem Ordner; Test grün und eigene Probe der `--bis`-Fälle.
  Status: CONFIRMED

Confirmation:
  AC: AC-3, AC-4, AC-5, AC-6
  Code reference: engine/reisespeicher.py:442
  Evidence: Vergleich über `_stand(..., "pruefsumme")` und `_ordner_lesen(summen=True)`; Fehler Exit 2 (eigene Probe: --bis abc, unbekannte Reise, Ordner fehlt).
  Status: CONFIRMED

Confirmation:
  AC: AC-31
  Code reference: engine/reisespeicher.py:463
  Evidence: `zustand` öffnet über `_nur_lesen` (mode=ro), Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-20, AC-21, AC-22, AC-23
  Code reference: engine/neu.py:1001
  Evidence: Schleife mit drei Versuchen, `StandGeaendert` führt zu erneutem Materialisieren, Probebau vor `ordner_als_vorgang`, `VorgangVorhanden` gibt "nichts umzustellen"; Tests grün. Ausnahme siehe F001.
  Status: CONFIRMED (mit F001)

Confirmation:
  AC: AC-16
  Code reference: engine/stand.py:129
  Evidence: `_materialisierter_stand` und `verlauf(bis=)`; Probe mit echtem Bau.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/vergleichslauf.sh:37
  Evidence: Stempel atomar, Exit 0/1/2, Bauordner unberührt (Archivexport aus HEAD); Lücke im Modus ohne Liste siehe F002.
  Status: CONFIRMED (mit F002)

Confirmation:
  AC: AC-10, AC-11, AC-13, AC-14, AC-15, AC-24, AC-25, AC-26, AC-27, AC-32
  Code reference: betrieb/veroeffentlichen.sh:146
  Evidence: Speicher-Teil vor dem Netzabruf, Stempel `.gebaut` nur nach Exit 0, `speicher_rot_melden` ohne `gh`, Rot-Datei als Vereinigung; zugehörige Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-12, AC-18
  Code reference: betrieb/gemeinsam.sh:117
  Evidence: leere Liste kehrt vor jedem Python-Aufruf zurück; Zerlegung der Liste gleich Python (`engine/instanz.py:98`). Wackelt wegen F003 unter pipefail.
  Status: CONFIRMED (mit F003)

Confirmation:
  AC: AC-19, AC-29, AC-30
  Code reference: betrieb/deploy.sh:20
  Evidence: `reisespeicher.py` in RM_MODULE, KN_MODULE, PS_MODULE; Modullisten-Test grün; keine neue Einheit.
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: betrieb/freischalten.sh:39
  Evidence: Reise im Bau-Ordner gefunden; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-28
  Code reference: betrieb/software-nachziehen.sh:82
  Evidence: nur durch Lesen belegt, kein Test (F004, F005).
  Status: AMBIGUOUS

## Herkunft der Vorbedingungen

Kein Sprachprofil konfiguriert (`precondition_origins.default_lang`); keine Tabelle vom Orchestrator angehängt.

## Verdict

═══════════════════════════════════════
VERDICT: BROKEN
═══════════════════════════════════════
Finding F001: nachziehen-speicher fängt nicht jede Ausnahme; ein Fehler beim Umstellen einer Reise (Exit 1) stoppt den ganzen Lauf samt Git-Teil und allen Speicher-Reisen.
  Severity: HIGH
  Evidence: engine/neu.py:1001, engine/neu.py:1303, betrieb/veroeffentlichen.sh:146
  Reproduction: Speicher-Reise mit unlesbarer reise.yaml, Software-Wechsel, veroeffentlichen.sh: Exit 1, jeder Lauf erneut.
Finding F002: vergleichslauf.sh ohne Reiseliste meldet bei unlesbarer Datenbank Exit 0 und schreibt keinen Stempel (MEDIUM, betrieb/vergleichslauf.sh:37).
Finding F003: ist_speicherreise falsch negativ unter pipefail (SIGPIPE), etwa 0,1 % bei zwei Namen (MEDIUM, betrieb/gemeinsam.sh:117).
Finding F004: Workflow liest die Liste anders als der Server (LOW, betrieb/software-nachziehen.sh:82).
Finding F005: Tests für AC-28 und die Reise ohne Pläne fehlen (LOW, engine/tests/test_software_nachziehen.py:1).
Finding F006: Roter Git-Teil hält Speicher-Reisen auf alter Software (LOW, spec-konform, betrieb/veroeffentlichen.sh:156).
Nachweise außerhalb des Codes offen: AC-8 (Messung auf dem Server), AC-9 (Browser-Rundgang), AC-33 (Infra-Issue und Link).

Tests: 231 passed, 0 failed, 0 übersprungen
Edge cases: F001 bis F003 gebrochen
Regressions: keine gefunden (Reise ohne Eintrag in FR_SPEICHERREISEN unverändert, bis auf F003)
Checklist: 29/33 bewiesen, AC-28 nur gelesen (AMBIGUOUS), AC-8/9/33 teilweise (Nachweis im Issue fehlt)

## Geprüfte Dateien

- sha256:458d379e8edc4002d93f238921812de0457758e7e5502e8f56883636db165b7f  betrieb/deploy.sh
- sha256:0679b017026e984ca5c9d5f5dfc13c03c3661a8ccf11ec11e7642e0df3703471  betrieb/freischalten.sh
- sha256:62b9ccde8932b222363f14c77093e02c6aa8f1aa4dd24a5d3963c02926b79470  betrieb/gemeinsam.sh
- sha256:e478eb987a086afa2689efcdc8969386284a1a80589e36fc52691eedf5a5675f  betrieb/software-nachziehen.sh
- sha256:71a6984b32acbc5bd813063deb03af229cd272c07e7d351a1612951cbd42b2a5  betrieb/vergleichslauf.sh
- sha256:babd224c8241bcd99173c2b0bf36b2bf827a8a48a03daa34db3b50f337fe3229  betrieb/veroeffentlichen.sh
- sha256:086a75814f5b4d27aa178e39914aaf375fe9893b45313e14027e155fe6b3c77b  engine/neu.py
- sha256:daa0160a73656ced9c2e4cac2c6ce5dbcc7c31a990bcb8c000dd7078fa0fe17a  engine/reisespeicher.py
- sha256:fc444c19fad5784d692411cca075a73c32d9243e5ac2c3ced0ea5406bc979097  engine/stand.py
- sha256:d54fda93779d9a30880ee8459085372390754f2f8eccdd72defe7d1d356581a3  engine/tests/test_software_nachziehen.py

## Prüfbasis

- base: e5dfe1b4a1d22ad91cabccc4dbc560c6eb7604d6
- blob:6fdc93a482b16f90bb9eba065ed48f9d2adcdb36  betrieb/deploy.sh
- blob:23c0ba1b8164c623e9eb36c36d87b0e94ddd9931  betrieb/freischalten.sh
- blob:6aad0314f5fcb57b5d6e6aa23790be83fadd60ab  betrieb/gemeinsam.sh
- blob:4a5956c39df450c5dab910a41f70eebaf11c022a  betrieb/software-nachziehen.sh
- blob:d9e99fccc4adbb4a0c102160d2f27064f3371cee  betrieb/vergleichslauf.sh
- blob:109d49cb7f36de903725cc3d26f98aebf11bd37e  betrieb/veroeffentlichen.sh
- blob:3bdb06310f7e4dc089b6a724508aea52ebf72744  engine/neu.py
- blob:e530f1d20dcebf49d0dc3dfb2aef19363d77f3a6  engine/reisespeicher.py
- blob:25459f0f73e2294800dd3c377c11861b79f31d0c  engine/stand.py
- blob:c9f0085968cd77cbf6198df93df824a02a873728  engine/tests/test_software_nachziehen.py

## Geprüfte Dateien

- sha256:458d379e8edc4002d93f238921812de0457758e7e5502e8f56883636db165b7f  betrieb/deploy.sh
- sha256:0679b017026e984ca5c9d5f5dfc13c03c3661a8ccf11ec11e7642e0df3703471  betrieb/freischalten.sh
- sha256:62b9ccde8932b222363f14c77093e02c6aa8f1aa4dd24a5d3963c02926b79470  betrieb/gemeinsam.sh
- sha256:e478eb987a086afa2689efcdc8969386284a1a80589e36fc52691eedf5a5675f  betrieb/software-nachziehen.sh
- sha256:71a6984b32acbc5bd813063deb03af229cd272c07e7d351a1612951cbd42b2a5  betrieb/vergleichslauf.sh
- sha256:babd224c8241bcd99173c2b0bf36b2bf827a8a48a03daa34db3b50f337fe3229  betrieb/veroeffentlichen.sh
- sha256:086a75814f5b4d27aa178e39914aaf375fe9893b45313e14027e155fe6b3c77b  engine/neu.py
- sha256:daa0160a73656ced9c2e4cac2c6ce5dbcc7c31a990bcb8c000dd7078fa0fe17a  engine/reisespeicher.py
- sha256:fc444c19fad5784d692411cca075a73c32d9243e5ac2c3ced0ea5406bc979097  engine/stand.py
- sha256:d54fda93779d9a30880ee8459085372390754f2f8eccdd72defe7d1d356581a3  engine/tests/test_software_nachziehen.py

## Prüfbasis

- base: e5dfe1b4a1d22ad91cabccc4dbc560c6eb7604d6
- blob:6fdc93a482b16f90bb9eba065ed48f9d2adcdb36  betrieb/deploy.sh
- blob:23c0ba1b8164c623e9eb36c36d87b0e94ddd9931  betrieb/freischalten.sh
- blob:6aad0314f5fcb57b5d6e6aa23790be83fadd60ab  betrieb/gemeinsam.sh
- blob:4a5956c39df450c5dab910a41f70eebaf11c022a  betrieb/software-nachziehen.sh
- blob:d9e99fccc4adbb4a0c102160d2f27064f3371cee  betrieb/vergleichslauf.sh
- blob:109d49cb7f36de903725cc3d26f98aebf11bd37e  betrieb/veroeffentlichen.sh
- blob:3bdb06310f7e4dc089b6a724508aea52ebf72744  engine/neu.py
- blob:e530f1d20dcebf49d0dc3dfb2aef19363d77f3a6  engine/reisespeicher.py
- blob:25459f0f73e2294800dd3c377c11861b79f31d0c  engine/stand.py
- blob:c9f0085968cd77cbf6198df93df824a02a873728  engine/tests/test_software_nachziehen.py
