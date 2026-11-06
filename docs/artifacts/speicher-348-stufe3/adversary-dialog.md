# Adversary Dialog — speicher-348-stufe3
Spec: docs/specs/betrieb/speicher-348-stufe3.md
Datum: 2026-11-06 20:49

## Checkliste
- [x] **AC-1 Materialisieren:** Given eine importierte Beispielreise / When `materialisieren` läuft / Then entspricht der Ordner Byte für Byte `beispiel/reisen/<reise>` (gleiche Pfadmenge, gleiche Bytes, ohne `.git`), `<ordner>.stand` nennt die Stand-Nummer, und ein zweiter Aufruf auf einen vorhandenen Ordner ersetzt ihn, ohne alte Dateien zu behalten (eine zwischendurch gelöschte Datei fehlt).
- [x] **AC-2 Konsistente Nummer:** Given `materialisieren` hat Stand N exportiert / When danach ein Vorgang N+1 eintrifft / Then bleibt `<ordner>.stand` bei N, und `stand_nummer` meldet N+1.
- [x] **AC-3 Vergleich ohne Unterschied:** Given beide Beispielreisen importiert / When `vergleichen <reise> beispiel/reisen/<reise>` läuft / Then Ausgabe `gleich`, Exit 0 (Akzeptanz aus #348).
- [x] **AC-4 Vergleich mit Unterschieden:** Given eine geänderte, eine gelöschte und eine neue Datei im Ordner / When `vergleichen` läuft / Then je eine Zeile `verschieden`, `nur im Speicher`, `nur im Ordner`, am Ende `3 Unterschiede`, Exit 1.
- [x] **AC-5 Vergleich: Fehler:** Given unbekannte Reise / fehlender Ordner / Symlink im Ordner / gesperrte Datenbank (Schreibsperre einer zweiten Verbindung über die Wartezeit hinaus) / falsche Angaben / When `vergleichen` läuft / Then Exit 2 mit einer Zeile `ERROR: …`, nichts wird geschrieben.
- [x] **AC-6 Vergleich über Prüfsummen:** Given ein Speicher mit einer Reise mit großen Dateien / When `vergleichen` läuft / Then werden keine Inhalte als Bytes gelesen (der Test ersetzt `aktueller_stand` durch eine Falle, die scheitert; der Vergleich nutzt `_stand(..., "pruefsumme")`).
- [x] **AC-7 Vergleichslauf mit Stempel:** Given ein Bauordner mit Git-Reise `beispielreise` und dieselbe Reise im Speicher / When `betrieb/vergleichslauf.sh` läuft / Then Exit 0 und `vergleich/beispielreise.json` mit `ergebnis: gleich`, `stand`, `git`, `zeit`; nach einer Änderung im Speicher Exit 1 und `ergebnis: unterschied`; ein Fehler bei der einen Reise (Reise nur im Speicher, ohne Git-Ordner wird übersprungen; kaputter Speicher) bricht die andere nicht ab, Gesamt-Exit 2; der Bauordner bleibt unverändert (`git status` leer).
- [?] **AC-8 Messung:** Given die erfundene 110-MB-Testreise aus dem Messlauf von #347 (`betrieb/messlauf-schreibweg.py --auffuellen 110`, Ordner bleibt erhalten) / When Materialisieren und Vergleichen auf dem Server der Instanz gemessen werden / Then stehen die Zeiten im Issue #348 und liegen unter den Zielen aus „Zeitziele“. Nachweis, kein automatischer Test; der Kurzlauf des Messskripts bleibt Test (`test_messlauf_skript_gibt_kennzahlen_aus`).
- [?] **AC-9 Eine Testreise vollständig über die Datenbank bis zur Seite (Akzeptanz #348):** Given je ein Bauordner mit `FR_SPEICHERREISEN=<reise>` und die Beispielreise `beispielreise` bzw. `stadtwochenende` nur im Speicher / When ein Schreibvorgang (z. B. eine Frage anlegen, Stufe-2-Weg) den Stand erhöht und `veroeffentlichen.sh` läuft / Then entsteht `<FR_SEITEN>/<reise>/` mit `index.html`, `sw.js`, `manifest.json`, `daten.json` trägt `reise_stand.nummer` = `stand_nummer`, die neue Frage steht in den Daten, `…lauf.json` zeigt `veroeffentlicht`, `publish_status` (`stand.lesen`) meldet „enthalten“. Dasselbe gilt für beide Reisetypen. Der Browser-Rundgang der Prüfstelle (Frage 8) wird auf dem Server der Instanz mit einer Testreise abgenommen (`betrieb/pruefsitzung.py`, nie mit einer echten Reise).
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
- [x] **AC-28 Workflow überspringt Speicher-Reisen:** Given ein Reisen-Repo mit Git-Reise A und Speicher-Reise B (Liste in `betrieb/einstellungen.env`) und ein alter Stand / When `software-nachziehen.sh` läuft / Then wird nur A umgestellt (kein Bot-Commit in `reisen/B`) und geprüft; mit leerer Liste ändert sich das Verhalten nicht (bestehende Tests grün).
- [x] **AC-29 Keine neue Einheit:** Given die Vorlagen unter `betrieb/vorlagen/` / When `units.py pruefen` und der Test der Vorlagen laufen / Then gibt es keine neue `.service` oder `.timer`, und `ERLAUBT` in `units.py` ist unverändert.
- [x] **AC-30 Kein Handschritt (#250):** Given eine Instanz mit Speicher-Reise und ein neuer Software-Stand, der eine Umstellung verlangt / When der Stand im Bauordner ankommt / Then stellen die Läufe die Reise um, ohne dass jemand `neu.py` aufruft; die Dokumentation (`docs/betrieb.md`) nennt keinen Handschritt nach einem Software-Wechsel.
- [x] **AC-31 Zustand der Sicherung:** Given kein Speicher / eine frische Sicherung / eine Sicherung älter als die Frist / eine Datenbank ohne Sicherung / eine nicht lesbare Datenbank / When `zustand` läuft / Then Exit 0 / 0 / 1 / 1 / 2, die Zeilen nennen Alter und Zahl der Reisen, und der Befehl schreibt nichts (Änderungszeit der Datenbank und der Sicherung unverändert).
- [x] **AC-32 Stempel `.gebaut`:** Given ein gelungener Deploy einer Speicher-Reise / When der Lauf endet / Then enthält `…gebaut` `<nummer> <kennung>`; nach einem gescheiterten Bau bleibt er unverändert.
- [?] **AC-33 Dokumentation und Issue:** Given die Änderung / When `docs/betrieb.md` gelesen wird / Then beschreibt der Abschnitt Überwachung die vier Zustände mit Befehl und Schwelle; im Infra-Repo der Instanz liegt das Issue für den Teil-Check und ist in #348 verlinkt (Nachweis, kein Test).

## Dialog

Testlauf: `docs/artifacts/speicher-348-stufe3/adversary-test-output.txt` (test_speicher_stufe3, test_betrieb, test_reisespeicher, test_software_nachziehen: 238 passed, 0 failed, 0 übersprungen). Ganze Suite `engine/tests` mit `-n 3`: 1696 passed, 0 failed, 0 übersprungen (637 s). Basis: origin/main ist Vorfahr von HEAD (4 Commits davor); der Unterschied zu origin/main besteht aus den 24 Dateien der Stufe 3.

### Runde 1
**Adversary:** Nachprüfung von F001 bis F005 aus Lauf 1 mit anderen Fehlerarten (Wegwerf-Skripte im Scratchpad, kein Eingriff in Produktionscode, Tests, Spec).

- F001 (nachziehen-speicher, Exit 1 gegen 2): `engine/neu.py:1016` fängt jede Ausnahme außer OSError/sqlite3.Error der Reise selbst als Exit 2. Gegenversuche mit dem Vorgang einer kaputten `reise.yaml` im Speicher, je für Beispielreise und Städtewochenende: unlesbares YAML Exit 2 (beide), leere Datei Exit 2 (Wanderung) und Exit 0 "nichts umzustellen" (Städtewochenende), binärer Inhalt Exit 2 mit `UnicodeDecodeError` (beide), nur ein fremdes Feld Exit 2 (beide), Liste statt Abbildung Exit 2 (Wanderung) und Exit 0 (Städtewochenende), fehlende Datei Exit 2 (Wanderung) und Exit 0 (Städtewochenende), `reise.yaml` als Ordner Exit 0. In keinem Fall steigt die Stand-Nummer (Ausgabe "stand 2 -> 2"). Exit 0 heißt dort nur: nichts umzustellen; der anschließende Bau in `betrieb/deploy.sh` scheitert dann mit Exit 2 und macht die Reise rot, nicht zur Störung. Behoben, kein Exit 1 für Reiseinhalt mehr.
- F001, Reisenamen: Reise mit Leerzeichen, Umlauten, Semikolon, `../esc`, `a/b` und leerem Namen durch materialisieren, vergleichen und nachziehen-speicher: überall Exit 0. Ein Name `-v` scheitert in argparse (Exit 2), unerreichbar, weil `freischalten.sh` Namen auf `[a-z0-9-]` mit Buchstabe oder Ziffer vorn beschränkt.
- F002 (vergleichslauf ohne Liste): `betrieb/vergleichslauf.sh:40` bricht bei nicht lesbarem Speicher mit Exit 2 ab, wenn `alle` gesetzt ist; mit Liste wird `gesamt=2` gesetzt und je Reise gemeldet. Test `test_vergleichslauf_ohne_liste_meldet_unlesbaren_speicher` grün. Behoben.
- F003 (SIGPIPE): `betrieb/gemeinsam.sh:117` liest ohne Pipe per Here-String. Eigene Messung unter `set -euo pipefail`: Liste mit 3000 Namen 0 von 200 falsch negativ (Lauf 1: 200 von 200), Liste `a,b` 0 von 3000 (Lauf 1: 3 von 3000). Liste `" a , ,b ,a,a b"` ergibt `a`, `b`, `a`, `a b`, wie `instanz.speicherreisen()`. Behoben.
- F004 (Workflow liest die Liste): `betrieb/software-nachziehen.sh:78` nimmt die erste Zeile und lässt einen gesetzten Wert aus der Umgebung vor der Datei gelten, wie `fr_einlesen` in `betrieb/gemeinsam.sh:61`. Test `test_workflow_liest_die_liste_wie_der_server` belegt beides. Behoben.
- F005 (fehlende Tests): `test_speicher_reisen_werden_im_workflow_uebersprungen` und `test_workflow_liest_die_liste_wie_der_server` in `engine/tests/test_software_nachziehen.py`; `test_reise_ohne_plaene_materialisieren_vergleichen_nachziehen` in `engine/tests/test_speicher_stufe3.py`. Alle grün. Behoben.

Finding:
  ID: F007
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/gemeinsam.sh:107
  Description: `speicherreisen` zerlegt `FR_SPEICHERREISEN` mit `for r in $FR_SPEICHERREISEN` ohne abgeschaltete Dateinamen-Erweiterung. Ein Eintrag `*` (oder `x*`) wird zu den Namen im aktuellen Ordner. Messung: Liste `" a , ,b ,a,a b,*,x*"` liefert in der Shell zusätzlich `beispiel betrieb CLAUDE.md docs engine …`, Python liefert `*`. Außerdem zerlegt `betrieb/veroeffentlichen.sh:146` die Liste über `staende $liste` an Leerzeichen, so dass ein Eintrag `a b` dort zu `a` und `b` wird, während `ist_speicherreise` ihn als einen Namen kennt.
  Spec requirement: AC-18 — Shell und Python lesen die Liste gleich.
  Conflict: Nur für Namen mit Sternchen oder Leerzeichen; gültige Reisenamen (`[a-z0-9-]`, `betrieb/freischalten.sh`) sind nicht betroffen, es ist ein Tippfehler in der Einstellung. Auch eine doppelte Reise in der Liste (`a,a`) wird im Speicher-Teil zweimal gebaut, weil `pub` aus der Momentaufnahme von `staende` stammt (`betrieb/veroeffentlichen.sh:146`, Bedingung `"$n" != "$pub"`); harmlos, aber unnötig.
  Remediation: Dateinamen-Erweiterung im Aufruf von `speicherreisen` abschalten, Liste zeilenweise übergeben und lesen, Duplikate vorher entfernen.

**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Zweiter Durchgang: Regressionen der Fixes, Rebase, die in Lauf 1 offenen Punkte.

- Regression Exit-Codes `engine/neu.py` (`main` ab Zeile 1300): `nachziehen-speicher` gibt 0 (umgestellt oder nichts), 2 (Reise, Probebau, unbekannte Reise, ValueError) und 1 nur für OSError/sqlite3.Error der Infrastruktur und für drei Wettläufe. Die alten Befehle (`nachziehen`, `anlegen` …) laufen unverändert; die neue Zeile `parse_args(argv if argv[0] in sub.choices else argv[1:])` verträgt den Aufruf mit und ohne Programmnamen. Die ganze Suite (1696) ist grün, darunter die Tests, die `neu.main(["neu.py", …])` aufrufen.
- Regression `ist_speicherreise` (`betrieb/gemeinsam.sh:117`): leere Liste gibt "nein" (Messung "leer ok"), leerer Name "nein". Aufrufer: `betrieb/deploy.sh:35`, `betrieb/freischalten.sh:40`, `betrieb/veroeffentlichen.sh` (Zeilen 72, 124 ff.). Die Skripte setzen `pipefail`; die Funktion ist jetzt ohne Pipe.
- Regression `vergleichslauf.sh`: Stempel nur bei Vergleich (gleich, unterschied, fehler); der Bauordner bleibt unverändert (Export des Stands HEAD in einen Wegwerf-Ordner). Test `test_vergleichslauf_schreibt_stempel_und_exit_codes` grün. Lesung: Scheitert der Export selbst (beschädigtes Repository), bricht `set -e` mit `pipefail` das ganze Skript ab; sehr unwahrscheinlich, kein Befund.
- AC-9 mit dem echten `betrieb/deploy.sh` (in Lauf 1 nur Attrappe): eigener Lauf mit `FR_SPEICHERREISEN=<reise>`, Reise nur im Speicher, materialisiert nach `<FR_DIENST>/bau/reisen/<reise>`, Instanz-Ordner ohne `reisen/`: für Beispielreise und Städtewochenende Exit 0, `index.html`, `sw.js`, `manifest.json`, `daten.json` vorhanden, `reise_stand.nummer` 1 gleich `stand_nummer` 1. Dass ein Schreibvorgang den Stand erhöht und `publish_status` "enthalten" meldet, belegen die Tests `test_veroeffentlichen_baut_speicher_reise_bis_zur_seite` (beide Reisen) mit der Deploy-Attrappe. Nicht belegt: der Browser-Rundgang auf dem Server.
- AC-8: lokale Ersatzmessung aus Lauf 1 (110 MB: 0,8 s materialisieren, 0,2 s vergleichen) unverändert gültig, `vergleichen` liest nur Prüfsummen (`engine/reisespeicher.py:442`, Test `test_vergleichen_liest_keine_inhalte`). Nicht belegt: Messung auf dem Server der Instanz und Eintrag in #348; der einzige Kommentar in #348 (6.11.2026, 18:55 UTC) nennt keine Zeiten.
- AC-28: jetzt mit Tests belegt (siehe F005), `betrieb/software-nachziehen.sh:101` überspringt Umstellen und Tor, mit leerer Liste unverändert (bestehende Tests grün).
- AC-33: `docs/betrieb.md` beschreibt die vier Zustände mit Befehl und Schwelle (Test `test_doku_beschreibt_die_pruefbaren_zustaende`). Nicht belegt: Infra-Issue und Link in #348 (Suche in `henemm/henemm-infra` fand keins, keine Verlinkung im Kommentar).
- Rebase: `betrieb/deploy.sh:22-30` trägt `reisespeicher.py` in RM_MODULE, KN_MODULE, SB_MODULE und PS_MODULE; die Prüfung der Modullisten (`test_betrieb.py`) und `test_jede_modulliste_mit_stand_traegt_reisespeicher` sind grün. `engine/stand.py:129` importiert jetzt normal.
- Nicht gewertet (entschieden): Reise ohne Stempel `.gebaut` (Known Limitations), Teil-3-Satz "oder keinen Stempel", F006 (Entscheidung 7).

**Implementierer:** (nicht beteiligt)

## Confirmations

Confirmation:
  AC: AC-16, AC-2
  Code reference: engine/stand.py:129
  Evidence: `_aus_dem_speicher` begrenzt Nummer und Änderungsliste auf den Stand aus `<ordner>.stand` (`bis`), normaler Import statt importlib; Seite trägt N, auch wenn N+1 eintrifft.
  Status: CONFIRMED

Confirmation:
  AC: AC-12, AC-19, AC-32
  Code reference: betrieb/deploy.sh:35
  Evidence: Quelle der Reise je Eintrag in der Liste; die vier Modullisten (Zeilen 22 bis 30) tragen `reisespeicher.py`; echter Lauf für beide Beispielreisen mit Exit 0.
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: betrieb/freischalten.sh:39
  Evidence: `reise.yaml` wird im Bau-Ordner gefunden (`FR_REISENORDNER`, sonst Bau-Ordner der Speicher-Reise); Test `test_freischalten_findet_speicher_reise` grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-1, AC-2, AC-16
  Code reference: engine/reisespeicher.py:413
  Evidence: materialisieren exportiert nach `<ordner>.neu`, benennt um, schreibt `<ordner>.stand` atomar; `engine/stand.py:129` begrenzt die Änderungsliste der Seite auf diesen Stand. Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3, AC-4, AC-5, AC-6
  Code reference: engine/reisespeicher.py:442
  Evidence: vergleichen nur über Prüfsummen, Datenbank `mode=ro` (Zeile 393), Exit 0/1/2 im Befehl; Tests `test_vergleichen_*` grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/vergleichslauf.sh:40
  Evidence: Stempel je Reise, Exit 0/1/2, unlesbarer Speicher ohne Liste Exit 2 (F002 behoben), Bauordner unberührt; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9, AC-10, AC-13, AC-14, AC-15, AC-32
  Code reference: betrieb/veroeffentlichen.sh:146
  Evidence: Speicher-Teil läuft vor dem Netzabruf und ohne `gh`; Bau nur bei anderer Nummer, Stempel nur nach Exit 0 von `betrieb/deploy.sh`, Exit 2 rot je Reise, Exit 1 Störung. Der echte `betrieb/deploy.sh` baut beide Beispielreisen aus dem Speicher (eigener Lauf). Browser-Rundgang auf dem Server offen.
  Status: CONFIRMED

Confirmation:
  AC: AC-11, AC-12, AC-17, AC-18, AC-19
  Code reference: betrieb/gemeinsam.sh:117
  Evidence: leere Liste ruft nichts auf; `ist_speicherreise` ohne Pipe, gleiche Zerlegung wie Python (Randfall F007, LOW); Modullisten in `betrieb/deploy.sh:22` tragen `reisespeicher.py`; `betrieb/freischalten.sh:39` wählt den Ordner je Quelle.
  Status: CONFIRMED

Confirmation:
  AC: AC-20, AC-21, AC-22, AC-23, AC-24
  Code reference: engine/neu.py:1001
  Evidence: materialisieren, nachziehen, Probebau, genau ein Vorgang mit `erwartet=basis`, drei Versuche, jede Ausnahme der Reise Exit 2 (Gegenversuche in Runde 1), Infrastruktur Exit 1.
  Status: CONFIRMED

Confirmation:
  AC: AC-25, AC-26, AC-27, AC-30
  Code reference: betrieb/veroeffentlichen.sh:146
  Evidence: Umstellen nur bei geprüfter Software (Datei `veroeffentlicht` trägt die Kennung), sonst Warten mit Hinweis; Rot ohne `gh`; Nachlauf per `nochmal`; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-28
  Code reference: betrieb/software-nachziehen.sh:101
  Evidence: `aus_dem_speicher` überspringt Umstellen und Tor, Liste gelesen wie `fr_einlesen`; drei Tests in `engine/tests/test_software_nachziehen.py` grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-29, AC-31
  Code reference: engine/reisespeicher.py:463
  Evidence: `zustand` liest nur (`mode=ro`), Exit 0/1/2; keine neue Einheit (`test_keine_neue_einheit_fuer_stufe3`).
  Status: CONFIRMED

Confirmation:
  AC: AC-8, AC-33
  Code reference: docs/betrieb.md:1
  Evidence: Dokumentation und lokale Ersatzmessung belegt; Messung auf dem Server mit Eintrag in #348 und Infra-Issue mit Link fehlen. Nachweise außerhalb des Codes, laut Auftrag offen.
  Status: AMBIGUOUS

## Herkunft der Vorbedingungen

Kein Sprachprofil konfiguriert (`precondition_origins.default_lang`); keine Tabelle vom Orchestrator angehängt.

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Der Code hält den Gegenversuchen stand; F001 bis F005 aus Lauf 1 sind behoben. Offen und ehrlich benannt: F007 (LOW, Sternchen oder Leerzeichen in Reisenamen der Liste, doppelte Einträge) und die Nachweise außerhalb des Codes AC-8 (Serverzeiten in #348), AC-9 (Browser-Rundgang), AC-33 (Infra-Issue und Link).
Tests: 238 passed (vier Dateien), 1696 passed (ganze Suite), 0 failed, 0 übersprungen
Edge cases: F007 LOW; sonst alle geprüft, keine gebrochen
Regressions: keine gefunden
Checklist: 30/33 bewiesen, AC-8/9/33 nur im Code-Teil bewiesen

## Geprüfte Dateien

- sha256:458d379e8edc4002d93f238921812de0457758e7e5502e8f56883636db165b7f  betrieb/deploy.sh
- sha256:0679b017026e984ca5c9d5f5dfc13c03c3661a8ccf11ec11e7642e0df3703471  betrieb/freischalten.sh
- sha256:0dc7e707002407b932dc3ed1db0152f5e092a582462344addc250fc39cd1c232  betrieb/gemeinsam.sh
- sha256:0b0e0b13e1d5a9cc3bc47f133978729cc47beec105b90f526e8e4d29fcf34cbf  betrieb/software-nachziehen.sh
- sha256:98ac9b8ea4677445d6b4d4dfabdee972266d1aa44cacac748ba83c2596a74dfc  betrieb/vergleichslauf.sh
- sha256:babd224c8241bcd99173c2b0bf36b2bf827a8a48a03daa34db3b50f337fe3229  betrieb/veroeffentlichen.sh
- sha256:717862f3398903260b01cef67d085f9b7dc08962bbd2a0c96dd2109e7238378f  docs/betrieb.md
- sha256:c5ee73b1ea26aeb10c5f632bd30f1177868ac07c5b6dc39c04e7227e8f0ffae5  engine/neu.py
- sha256:daa0160a73656ced9c2e4cac2c6ce5dbcc7c31a990bcb8c000dd7078fa0fe17a  engine/reisespeicher.py
- sha256:fc444c19fad5784d692411cca075a73c32d9243e5ac2c3ced0ea5406bc979097  engine/stand.py

## Prüfbasis

- base: d3ea8c34a873fe28104a616f6b86f31e55ea09f4
- blob:6fdc93a482b16f90bb9eba065ed48f9d2adcdb36  betrieb/deploy.sh
- blob:23c0ba1b8164c623e9eb36c36d87b0e94ddd9931  betrieb/freischalten.sh
- blob:71ef82b8dca22382849ec376cd175dbaa45c9de7  betrieb/gemeinsam.sh
- blob:9a8dd281b37dd9c0ce65c5c869c8dba836f2d173  betrieb/software-nachziehen.sh
- blob:eb3bb03521eb98d0a6cd81592c175886e1f47482  betrieb/vergleichslauf.sh
- blob:109d49cb7f36de903725cc3d26f98aebf11bd37e  betrieb/veroeffentlichen.sh
- blob:7f4d1b3cbc38d9f9604e4dcd8eab3e736f50dde6  docs/betrieb.md
- blob:097c0eb0b2f9bbf052e61623466c86c913c6a1e3  engine/neu.py
- blob:e530f1d20dcebf49d0dc3dfb2aef19363d77f3a6  engine/reisespeicher.py
- blob:25459f0f73e2294800dd3c377c11861b79f31d0c  engine/stand.py
