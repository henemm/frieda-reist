# Adversary Dialog — speicher-347-stufe2
Spec: docs/specs/betrieb/schreibweg-speicher-347.md
Datum: 2026-11-06 09:14

## Checkliste
- [x] **AC-1 Schutz vor verlorenen Änderungen:** Given eine Reise im Speicher / When `vorgang_schreiben(..., erwartet=N)` läuft und der aktuelle Stand N, kleiner oder größer ist / Then nur bei Gleichheit entsteht ein Vorgang; sonst `StandGeaendert(erwartet, aktuell)` und keine neue Zeile; ohne `erwartet` bleibt das Verhalten der Stufe 1.
- [x] **AC-2 Wartezeit der Datenbank:** Given eine von einer anderen Verbindung gehaltene Schreibsperre / When `db(timeout=0.2)` bzw. ein Schreibzugriff damit läuft / Then kommt nach etwa 0,2 s `sqlite3.OperationalError`, nicht erst nach 10 s; ohne Parameter bleibt es bei 10 s.
- [x] **AC-3 Einzeldatei und Reisenliste:** Given zwei Reisen im Speicher / When `datei(reise, "plan/routen.yaml")` und `reisen()` laufen / Then liefert `datei` die Bytes genau dieser Datei (auch mit `bis=`), `KeyError` bei unbekannter Reise, Stand oder gelöschter Datei, und `reisen()` die sortierte Liste beider Reisen.
- [x] **AC-4 Baustein Ordner → Vorgang:** Given ein Ordner mit geänderten, neuen und fehlenden Dateien gegenüber `aktueller_stand(reise, basis)` / When der Baustein läuft / Then entsteht genau ein Vorgang mit den Änderungen und Löschungen (Tombstones); ohne Unterschied `ValueError`; mit `basis=0` für eine neue Reise.
- [x] **AC-5 Schalter:** Given `FR_SPEICHERREISEN` leer bzw. gesetzt / When `instanz` gefragt wird / Then leere Liste bzw. die genannten Reisen (Leerzeichen und Leerstellen ignoriert); `betrieb/einstellungen.beispiel` enthält `FR_SPEICHERREISEN`; ohne Einstellung schreibt jede Reise über Git wie vor dieser Stufe.
- [x] **AC-6 Speicherweg schreibt einen Vorgang:** Given eine Reise der Liste mit Speichereintrag (je eine Beispielreise) / When ein Werkzeug (z. B. eine Frage anlegen) den Dienst durchläuft / Then 200, `stand_nummer` +1, genau ein neuer Vorgang mit Titel, Person, Rolle, Werkzeug und Kennung, `commit` ist die Vorgangs-Nummer, und `aktueller_stand` enthält die geänderte Datei.
- [x] **AC-7 Ablehnungen lassen den Stand unverändert:** Given eine Reise im Speicher / When ein Vorgang an der Rolle, am Probebau, an „nichts geändert“ oder an der belegten Sperre (429) scheitert / Then die Antwort ist 422 bzw. 429, `stand_nummer` und `aktueller_stand` sind unverändert, und der temporäre Ordner ist gelöscht.
- [x] **AC-8 Reise ohne Speichereintrag:** Given eine Reise in `FR_SPEICHERREISEN` ohne Eintrag im Speicher / When ein Schreibvorgang kommt / Then 503 mit dem Text `reise_nicht_im_speicher`, ohne Vorgang und ohne Datei.
- [x] **AC-9 Git-Weg lehnt Listenreise ab:** Given eine Reise in `FR_SPEICHERREISEN` / When sie den Git-Weg (`schreiben_git`) erreicht / Then wird sie mit 503 und dem Text `reise_im_speicher` abgelehnt, ohne Commit und ohne fetch.
- [x] **AC-10 Konflikt:** Given zwischen Export und Eintragen schreibt ein anderer Vorgang auf dieselbe Reise / When der erste Vorgang einträgt / Then 503 mit dem Text `stand_geaendert`, kein zweiter Eintrag, Stand des anderen bleibt.
- [x] **AC-11 Nachprüfung nach Abbruch:** Given der Unterprozess überschreitet die Frist / When `nach_abbruch` läuft / Then bei vorhandener Kennung 200 „eingetragen trotz Abbruch“ mit dem Stand, bei fehlender Kennung 504 „nicht eingetragen“, bei nicht lesbarer Datenbank oder abgelaufener Prüffrist 504 „ungeprüft“; die Protokollzeilen der Meldungstabelle bleiben; Stand unverändert, wenn der Unterprozess vor dem Eintrag getötet wurde.
- [x] **AC-12 Fristen:** Given ein hängender Export oder Eintrag / When der Vorgang läuft / Then endet die Antwort nach höchstens `ZEIT_GESAMT + ZEIT_PRUEFUNG` Sekunden, die Datenbankwartezeit richtet sich nach der Restzeit, und die Zeile „Fertig <werkzeug> <code> in <Sekunden> s“ steht genau einmal im Protokoll; `ZEIT_GESAMT`, `ZEIT_SPERRE`, `ZEIT_PRUEFUNG` behalten die Werte 25, 3, 3.
- [x] **AC-13 Buchung:** Given eine Speicher-Reise mit Buchung B-01 in `plan/routen.yaml` / When `GET /<reise>/buchung/B-01` fragt / Then `{"gibt_es": true, "fuer": [...], "wer": ...}`; unbekannte Buchung oder Reise `{"gibt_es": false}`; Datenbank nicht erreichbar 503; Git-Reisen verhalten sich wie vorher.
- [x] **AC-14 Gesundheit:** Given der Dienst mit Speicher-Reisen / When `GET /gesund` fragt / Then 200 `{"gesund": true}`, wenn die Datenbank antwortet; 503 `{"gesund": false}`, wenn nicht. Ohne Speicher-Reisen prüft `/gesund` wie vorher den Git-Teil.
- [x] **AC-15 Neue Reise:** Given der Speicher kennt die Reisen A und B / When `reise_anlegen` mit einem neuen Namen in `FR_SPEICHERREISEN` läuft / Then entsteht die Reise als erster Vorgang (Stand 1) mit den erzeugten Dateien und neuen IDs ohne Kollision; ein vorhandener Name oder eine Ablehnung des Probebaus legt nichts an.
- [x] **AC-16 Stand-Nachweis:** Given ein Speicher-Vorgang / When `<reise>.gesichert.json` gelesen wird / Then enthält sie `nummer` = Stand-Nummer und `commit` = Vorgangs-Nummer; `stand.lesen` und `stand.enthalten` arbeiten unverändert über die Stand-Nummer.
- [x] **AC-17 Stand für die Seite:** Given eine Reise der Liste mit Speichereintrag / When `stand.fuer_seite` gerufen wird / Then Nummer, Zeit und Änderungsliste (neueste zuerst, Namen statt Kennungen, Person) kommen aus dem Speicher; eine Git-Reise liefert dasselbe wie vor der Verschiebung (`stand_git`); ohne Eintrag und ohne Git ist das Ergebnis `None`; der Probebau enthält keinen Stand.
- [x] **AC-18 Kein git (statisch):** Given der Quelltext von `engine/schreiben.py` und `engine/stand.py` / When er geprüft wird / Then enthält er keinen git-Aufruf (`"git"` in `subprocess`-Argumenten, `git(`) und keinen Modulebenen-Import von `schreiben_git` oder `stand_git`; die Importe geschehen nur in Funktionen des Git-Wegs.
- [x] **AC-19 Kein git (Laufzeit):** Given ein ausführbarer `git`-Stub im ersten Ordner des `PATH`, der bei jedem Aufruf eine Marke schreibt / When ein vollständiger Speicher-Vorgang einschließlich Probebau, ein abgelehnter Vorgang, `buchung`, `/gesund` und `fuer_seite` laufen / Then fehlt die Marke.
- [x] **AC-20 Git-Weg unverändert:** Given keine Einstellung `FR_SPEICHERREISEN` / When die bestehenden Tests des Git-Wegs laufen (`test_schreiben.py`, `test_stand.py`, `test_betrieb.py`, `test_software_nachziehen.py`, `test_bauen.py`, `test_pwa.py`, `test_art_uebersicht.py`) / Then sind sie grün, ohne dass sich ihre Erwartungen an Meldungen, Antwortfelder oder Protokollzeilen ändern; verschoben sind nur Importe der Fixtures.
- [x] **AC-21 Texte in allen Sprachen:** Given die vier neuen Schlüssel / When `test_texte.py` läuft / Then stehen sie in jeder `texte_<sprache>.py` (mindestens `de`, `en`) und in der Pseudo-Sprache der Tests; die Ausnahmelisten sind nicht länger geworden.
- [x] **AC-22 Modulliste des Betriebs:** Given `betrieb/deploy.sh` / When `SB_MODULE` gelesen und gegen die Importe von `schreiben.py` und seinen Folgemodulen verglichen wird / Then enthält sie `reisespeicher.py` und jedes Modul, das der Speicherweg und der Probebau laden; der Modullisten-Test (`test_jede_sprache_steht_in_den_modullisten_des_deploys`) bleibt grün.
- [x] **AC-23 Stufe-1-Test ersetzt:** Given der Stufe-1-Test „Schreibweg bindet den Speicher nicht ein“ / When er ersetzt wird / Then dürfen `schreiben.py`, `stand.py` und `deploy.sh` `reisespeicher` nennen, `konnektor.py` und `rueckmeldungen.py` weiterhin nicht (Stufe 3).
- [x] **AC-24 Messlauf:** Given `betrieb/messlauf-schreibweg.py` / When es mit `--weg speicher` und `--weg git`, nacheinander und parallel, mit beiden Beispielreisen läuft / Then gibt es Anzahl, Mittel, p50, p90, p99, Maximum und die Zahl der 504, 429 und 5xx aus; der Speicherweg zeigt im Lauf auf dem Server der Instanz keine Zeitüberschreitung, und p99 liegt deutlich unter 25 s. Die Werte stehen im Issue #347.
- [x] **AC-25 Doku:** Given die Änderung / When `docs/betrieb.md`, ADR-0009, `schreibweg-zeitgrenzen.md` und `betrieb/einstellungen.beispiel` gelesen werden / Then nennen sie `FR_SPEICHERREISEN`, den Speicherweg, die lokale Nachprüfung, das Fehlen des Bauens aus dem Speicher bis Stufe 3 und das Server-Backup als Vorbedingung; `engine/tests/test_protokolle_ohne_pfade.py` bleibt grün.

## Dialog

### Runde 1
**Adversary:** Ich gehe von einer kaputten Umsetzung aus und pruefe zuerst die Vertraege der Speicher-Schnittstelle und die Ablehnungswege.
Methode: Quelltext gelesen (schreiben.py Speicherweg ab Zeile 4504, reisespeicher.py Zusaetze, stand.py, schreiben_git.py, stand_git.py),
gezielte Tests und eigene Sonden gefahren (Ausgabe in adversary-test-output.txt). Die Tests sind seit dem RED-Commit unveraendert
(Bestandstests des Git-Wegs wurden nicht angepasst).

Finding:
  ID: F001
  Severity: HIGH
  Category: spec_violation
  Code reference: engine/schreiben.py:4541
  Description: Der Export der Arbeitskopie (reisespeicher.exportieren, ebenso reisen() Zeile 4521 und stand_nummer Zeile 4540) laeuft synchron im Dienst-Thread. Die Frist wird erst danach geprueft (Zeile 4544). Ein Export, der laenger als ZEIT_GESAMT dauert, wird nicht abgebrochen. Sonde: exportieren schlaeft 6 s, ZEIT_GESAMT=1 -> Antwort 504 nach 6.0 s (erlaubt: 1 + 3 = 4 s). Bei grossen Fotos als BLOB (Known Limitation der Spec) oder langsamer Platte kommt die Antwort nach 30 s und mehr; nginx (proxy_read_timeout 30 s) kappt vorher, die Person bekommt keine Meldung der Tabelle.
  Spec requirement: AC-12 - Given ein haengender Export oder Eintrag, Then endet die Antwort nach hoechstens ZEIT_GESAMT + ZEIT_PRUEFUNG Sekunden; Ablauf Schritt 6: Der Export zaehlt zur Frist.
  Conflict: Der Test test_speicherweg_haelt_die_fristen simuliert nur 1,2 s Export bei Frist 1 s und toleriert 1 + 3 + 1 s; ein wirklich haengender Export wird nicht belegt. Nur das Eintragen im Unterprozess ist hart begrenzt (SIGKILL der Gruppe). Die Folgen sind sicher (nichts geschrieben), aber die Zusage der Spec ist nicht eingehalten.
  Remediation: Export in den Unterprozess verlegen (er hat die harte Frist) oder in einem Thread mit join(timeout=Rest) abbrechen; Test mit einem Export, der laenger als ZEIT_GESAMT + ZEIT_PRUEFUNG schlaeft.

Finding:
  ID: F002
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/schreiben.py:4558
  Description: speicher_gesund() ruft reisespeicher.db(timeout=ZEIT_PRUEFUNG), ohne zu pruefen, ob die Datenbank existiert. db() legt sie an, wenn sie fehlt (reisespeicher.py:109-119). Sonde: ohne reisen.db liefert speicher_gesund True und legt reisen.db (Modus 600) mit dem Besitzer des Dienstbenutzers an. reisen() (reisespeicher.py:255) vermeidet genau das.
  Spec requirement: AC-14 - 200 gesund, wenn die Datenbank antwortet; Risiko Dateirechte: die Datei gehoert dem ersten Oeffner.
  Conflict: Eine Gesundheitsabfrage (Monitor, jede Minute) hat einen Schreib-Nebeneffekt: Bei falsch gesetztem FR_SPEICHER meldet sie gesund und legt eine leere Datenbank am falschen Ort an; bei frischem Speicher gehoert die Datei dem Dienstbenutzer statt dem Waechter. Kein Alarm, wo einer noetig waere.
  Remediation: Zuerst reisespeicher.pfad().exists() pruefen (fehlt sie: nicht gesund) oder die Datei nur lesend oeffnen.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/instanz.py:98
  Description: speicherreisen() liest FR_SPEICHERREISEN bei jeder Anfrage aus der Einstellungsdatei; einstellungen() (instanz.py:39-44) gibt bei jedem OSError ein leeres Ergebnis zurueck. Ist die Datei in dem Moment nicht lesbar (Austausch beim Zusammenfuehren im Arbeitsbaum, Rechte), ist die Liste leer und eine Speicher-Reise schreibt ueber den Git-Weg. Dessen Schutz (schreiben_git.py:172) fragt dieselbe Funktion und lehnt dann nicht ab.
  Spec requirement: AC-9 / Schalter - kein Doppelschreiben; eine Reise der Liste darf nie ueber den Git-Weg schreiben.
  Conflict: Der Schalter faellt bei einem Lesefehler auf Git zurueck statt zu scheitern. Fenster klein, in dieser Stufe ist keine echte Reise umgeschaltet; relevant ab Stufe 5.
  Remediation: Lesefehler der Einstellungsdatei von fehlender Datei unterscheiden (Fehler statt leere Liste) oder der Git-Weg lehnt zusaetzlich ab, wenn die Reise im Speicher einen Eintrag hat.

Finding:
  ID: F004
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/stand.py:127
  Description: Bekannte Auffaelligkeit 1. importlib.import_module(reisespeicher) umgeht die statischen Modullisten-Pruefungen (test_betrieb.py Zeile 1371-1391 sieht den Import nicht). Laufzeitbewertung: sicher. Alle Listen aus betrieb/deploy.sh installieren in denselben Ordner FR_DIENST; reisespeicher.py liegt dort ueber SB_MODULE. fuer_seite wird nur von bauen.Bauer.schreiben (bauen.py:1229) gerufen; Konnektor, Rueckmeldedienst und Push laden bauen nicht und rufen weder fuer_seite noch nummer/aenderungen (Suche in engine/, betrieb/, werkzeuge/). Sonde: Dienstordner-Simulation nur mit SB_MODULE-Dateien laeuft vollstaendig.
  Spec requirement: Spec-Hinweis zu stand.py (reisespeicher nur innerhalb von Funktionen); AC-23 erlaubt stand.py ausdruecklich, reisespeicher zu nennen.
  Conflict: Das Umgehen war nicht noetig (ein Funktionsimport ist nach AC-23 zulaessig) und versteckt die Abhaengigkeit: Ruft ein Dienst mit anderer Liste spaeter fuer_seite (Stufe 3), merkt es kein Test. Nur Wartbarkeit.
  Remediation: Normalen Funktionsimport nutzen und den Modullisten-Test fuer RM/KN/PS mit begruendeter Ausnahme ergaenzen, oder einen Test, der fuer_seite in diesen Diensten verbietet.

Finding:
  ID: F005
  Severity: LOW
  Category: spec_violation
  Code reference: docs/betrieb.md:19
  Description: Die Tabellenzeile zum Reisespeicher sagt weiter: in Stufe 1 schreibt nur der Betreiber hinein, der Schreibweg bleibt auf Git. Das widerspricht dem neuen Absatz (Zeile 86-90) derselben Datei.
  Spec requirement: AC-25 - Doku nennt den Speicherweg konsistent.
  Conflict: Widerspruch innerhalb der Betriebsdoku; der Doku-Test prueft nur Stichworte.
  Remediation: Zeile 19 auf Stufe 2 (Schalter je Reise) anpassen.

Antwort Implementierer: nicht beteiligt (Kontextisolation).

Confirmation:
  AC: AC-1
  Code reference: engine/reisespeicher.py:177
  Evidence: erwartet wird in der Schreib-Transaktion nach der Kennungspruefung verglichen; StandGeaendert (Zeile 54) mit erwartet und aktuell; erwartet=0 bei unbekannter Reise heisst Stand 0. Test test_erwartet_schuetzt_vor_verlorenen_aenderungen gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/reisespeicher.py:103
  Evidence: db(timeout=10) reicht den Parameter an sqlite3.connect. Sonde: vorgang_schreiben(timeout=0.3) gegen fremde Schreibsperre -> OperationalError nach 0.31 s; Lesezugriffe (reisen, stand_nummer, datei, vorgang_eingetragen) warten im WAL-Modus nie.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/reisespeicher.py:263
  Evidence: datei() liest eine Zeile, KeyError bei unbekannter Reise, Stand und geloeschter Datei; reisen() (Zeile 255) sortiert, ohne Datenbank leer, ohne sie anzulegen.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/reisespeicher.py:237
  Evidence: ordner_als_vorgang bildet Tombstones fuer fehlende Dateien, NichtsGeaendert (Unterklasse von ValueError) ohne Unterschied, basis=0 ueberspringt aktueller_stand, erwartet=basis geht an vorgang_schreiben. Ein fehlender oder symlinkter Ordner loescht nichts (ValueError aus _ordner_lesen).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/instanz.py:98
  Evidence: Leere Umgebung gilt vor der Datei, Leerstellen und leere Teile fallen weg; betrieb/einstellungen.beispiel nennt FR_SPEICHERREISEN. Randfall siehe F003.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/schreiben.py:4266
  Evidence: Schreiber.schreiben traegt genau einen Vorgang ein (ordner_als_vorgang mit erwartet=basis), schreibt gesichert.json, antwortet mit commit = Vorgangs-Nummer. Sonde mit dem Code aus einem nachgebauten Dienstordner: frage_anlegen 200, commit 3, stand 2; ein Vorgang listet nur die geaenderten Dateien (ids.yaml, offene-fragen.md), keine Reste aus dem Probebau.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/schreiben.py:4554
  Evidence: finally: shutil.rmtree(tmp) umschliesst Export, Unterprozess und Nachpruefung; 422 und 429 kommen vor jedem Schreibzugriff. Test prueft beide Beispielreisen, Stand und aktueller_stand vorher/nachher sowie leeres TMPDIR.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:4524
  Evidence: Reise nicht in reisen() -> 503 reise_nicht_im_speicher vor Kennung, tmp und Unterprozess; Datenbank kaputt -> 503 speicher_nicht_erreichbar (Zeile 4523).
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/schreiben_git.py:172
  Evidence: Der Git-Weg lehnt eine Reise der Liste ab, bevor Sperre, Arbeitskopie oder fetch kommen (Test setzt den Origin auf eine nicht vorhandene Adresse). Wegen F003 nur so stark wie die Einstellungsdatei lesbar ist.
  Status: CONFIRMED

### Runde 2
**Adversary:** Zweite Runde mit harten Sonden: Abbruch, Konflikt, Fristen, Dienstordner, entfernte Namen, Doku. Jede Zeile hat einen eigenen Nachweis.

Confirmation:
  AC: AC-10
  Code reference: engine/schreiben.py:4376
  Evidence: StandGeaendert im Unterprozess -> 503 stand_geaendert, kein zweiter Eintrag (Pruefung und Schreiben in derselben BEGIN-IMMEDIATE-Transaktion, reisespeicher.py:177). Test schiebt einen fremden Vorgang zwischen Export und Eintragen; Stand des anderen bleibt, tmp leer.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/schreiben.py:4451
  Evidence: nach_abbruch: gefunden -> 200 verzoegert mit Stand und Vorgangs-Nummer; False -> 504 nicht eingetragen; None (sqlite3.Error/OSError, Zeile 4423) -> 504 ungeprueft. Echte SIGKILL-Sonde: 60 Laeufe mit ZEIT_GESAMT 0,25 bis 1,43 s, 15x 504 mit unveraendertem Stand, 45x 200 mit Stand +1, kein inkonsistenter Fall, tmp immer leer. Der Test fakt befehl_mit_frist, die Sonde schliesst die Luecke.
  Status: CONFIRMED

AC-12 (Widerspruch, siehe F001): Code reference: engine/schreiben.py:4510. Die Konstanten 25/3/3 stehen in Zeile 66-68; Unterprozess und Eintrag sind hart begrenzt (befehl_mit_frist, Zeile 180) und die Fertig-Zeile steht genau einmal (finally in anwenden_extern, Zeile 4491). Der Export vor dem Unterprozess ist nicht begrenzt. Status: DISPROVEN fuer den Teil haengender Export.

Confirmation:
  AC: AC-13
  Code reference: engine/schreiben.py:4293
  Evidence: buchung_im_speicher liest nur plan/routen.yaml ueber datei(); unbekannte Reise, Datei oder Buchung -> gibt_es False; sqlite3.Error/OSError -> 503 (Zeile 4603); Reisen des Git-Wegs laufen unveraendert ueber schreiben_git.buchung_im_repo (Zeile 4607). Geheimnispruefung vor der Wegwahl (Zeile 4597).
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/schreiben.py:4586
  Evidence: Mit Speicher-Reisen antwortet /gesund nach SELECT 1; ohne Liste wie vorher der Git-Teil. Beachte: In einer echten Instanz hat das Reisen-Repo immer einen .git-Ordner, daher prueft /gesund dort auch den Git-Teil (Bedingung Zeile 4591); das entspricht dem Wortlaut der Spec (beide Wege muessen gesund sein). Nebeneffekt der Pruefung siehe F002.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/schreiben.py:4533
  Evidence: reise_anlegen: bekannte Reisen aus dem Speicher und aus reisen/ als leere Ordner, Sperre reisen, basis=0, erster Vorgang Stand 1. Sonde im nachgebauten Dienstordner: 200, Stand 1, reisen() enthaelt alle drei Reisen. Vorhandener Name und leere Anfrage -> 422 ohne Wirkung (Test).
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/schreiben.py:4284
  Evidence: gesichert_schreiben(reise, v.stand, str(v.nummer)) nach dem Eintrag; Test liest nummer = 2 und commit = Vorgangs-Nummer, stand.lesen/enthalten unveraendert.
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: engine/stand.py:141
  Evidence: fuer_seite waehlt ueber den Ordnernamen den Speicher, sonst stand_git; ohne Eintrag None (_aus_dem_speicher faengt sqlite3.Error/OSError). Der Probebau ruft fuer_seite nicht, weil bauen.py:1229 nur in Bauer.schreiben steht, nicht in daten(); die in der Spec genannte Aenderung an bauen.py ist daher unnoetig und unterblieben. test_probebau_ohne_stand schuetzt das.
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: engine/stand_git.py:19
  Evidence: Alle Aufrufe des Programms git liegen in stand_git.py und schreiben_git.py; schreiben.py und stand.py haben keinen solchen Aufruf (befehl_mit_frist, Zeile 180, ist neutral) und importieren die Git-Module nur in Funktionen (schreiben.py:4156, 4202, 4271, 4290, 4412, 4486, 4592, 4662; stand.py:44, 117). Zusaetzliche Suche nach dem Wort in schreiben.py und stand.py: nur Kommentare, Docstrings und Namen.
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: engine/schreiben.py:4504
  Evidence: Speicherweg und Kindprozess starten das Programm git nie (Stub im PATH bleibt ohne Marke, Test gruen). Randbemerkung: veroeffentlichen_anstossen (Zeile 4305) startet im Betrieb weiter betrieb/veroeffentlichen.sh, das selbst git nutzt; im Test ersetzt ein Stub das Skript. Von der Spec gedeckt (Stufe 3).
  Status: CONFIRMED

Confirmation:
  AC: AC-20
  Code reference: engine/schreiben_git.py:169
  Evidence: Der Git-Weg ist wortgleich verschoben (vorgang, vorbereiten, hochladen, Aufraeumen alter Sperren). Bestandstests test_schreiben.py, test_stand.py (Bestand), test_betrieb.py (Bestand) sind seit dem RED-Commit unveraendert und gruen (253 passed fuer die Dateien des Git-Wegs, Gesamtlauf 1519). Entfernte Namen (schreiben.git, schreiben.vorgang, Sperrenraeumen, Schreiber.hochladen, stand.git, stand._person) haben in engine/, betrieb/, werkzeuge/ keine Nutzer; was werkzeuge/ und neu.py aus schreiben.py brauchen, ist vorhanden. Private Tests der Instanzen sind hier nicht pruefbar (Vorbedingung der Spec).
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: engine/texte_de.py:868
  Evidence: Die vier Schluessel stehen in texte_de.py (868-871) und texte_en.py:867-870 sowie in der Pseudo-Sprache (Test test_neue_schluessel_in_allen_sprachen); test_texte.py gruen, Ausnahmelisten unveraendert.
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: engine/texte_en.py:867
  Evidence: Englische Fassung aller vier Schluessel vorhanden, inhaltlich gleichwertig, Platzhalter keine.
  Status: CONFIRMED

Confirmation:
  AC: AC-22
  Code reference: betrieb/deploy.sh:27
  Evidence: Eigene Importhuelle (AST, auch Funktionsimporte und importlib) von schreiben.py und schreiben_git.py: bauen gpx instanz kalender karte konten neu reise reisespeicher routen schnittstelle schreiben schreiben_git stand stand_git texte; keine fehlt in SB_MODULE. Nicht nur statisch: Ein Ordner mit genau den Dateien aus SB_MODULE plus vorlage.html, sw.vorlage.js, vendor/ und reisevorlage/ fuehrt frage_anlegen, art_definieren und reise_anlegen im Speicherweg fehlerfrei aus (Probebau inklusive). Dateien neben den Modulen (bauen.py:1230, 1269, 1307, 1435; neu.py:43) sind durch die neuen install- und rsync-Zeilen gedeckt.
  Status: CONFIRMED

Confirmation:
  AC: AC-23
  Code reference: engine/stand.py:127
  Evidence: stand.py, schreiben.py und deploy.sh nennen reisespeicher; konnektor.py und rueckmeldungen.py nicht; Test test_nur_schreibweg_und_stand_binden_den_speicher_ein gruen. Wartungsnotiz F004.
  Status: CONFIRMED

Confirmation:
  AC: AC-24
  Code reference: betrieb/messlauf-schreibweg.py:141
  Evidence: Das Skript gibt Anzahl, Mittel, p50, p90, p99, Maximum, 504/429/5xx fuer nacheinander und parallel aus, mit beiden Beispielreisen und Kopien; Export- und Probebauzeit einzeln (Zeile 152). Lokale Laeufe: Speicherweg 24 Vorgaenge, Mittel 0,44 s, Max 0,91 s, parallel Max 2,49 s, 0 Zeitueberschreitungen; der alte Weg zweimal gefahren, einmal 1x 5xx (Rebase-Wettlauf, Verhalten wie vorher). Offen: Der Lauf auf dem Server der Instanz und die Werte im Issue 347 liegen mir nicht vor; das ist Prozessnachweis, kein Code.
  Status: CONFIRMED (Skript), Serverwerte offen

Confirmation:
  AC: AC-25
  Code reference: docs/betrieb.md:90
  Evidence: betrieb.md (Zeile 86-90), ADR-0009 (Zeile 35 und 43), schreibweg-zeitgrenzen.md und einstellungen.beispiel nennen Schalter, Speicherweg, lokale Nachpruefung, kein Bauen bis Stufe 3 und das Server-Backup als Vorbedingung; test_protokolle_ohne_pfade.py gruen. Restfehler F005 (Zeile 19).
  Status: CONFIRMED

Weitere Code-Referenzen zur Abdeckung (Pflichtdateien): Code reference: engine/instanz.py:98, engine/reisespeicher.py:237, engine/schreiben_git.py:172, engine/stand_git.py:19, engine/texte_de.py:868, engine/texte_en.py:867, betrieb/messlauf-schreibweg.py:141.

**Implementierer:** nicht beteiligt (Kontextisolation).

### Runde 3 (nach Nachbesserung)
**Adversary:** Der Entwickler hat F001, F002, F004, F005 bearbeitet; F003 bleibt bewusst offen (Issue fuer Stufe 5).

Confirmation:
  AC: AC-12
  Code reference: engine/schreiben.py:4554
  Evidence: reisen(), stand_nummer und Export laufen in einem Faden (Zeile 4527-4548), der Dienst wartet mit join(timeout=Rest) und antwortet bei Hang mit 504 nicht eingetragen ohne Unterprozess (4555-4557). Meine Sonde von vorher (Export schlaeft, ZEIT_GESAMT=1): Antwort jetzt nach 1,0 s statt 6,0 s. F001 behoben.
  Status: CONFIRMED

Angriff auf die Faden-Loesung:
- Sperre frei, alter Faden laeuft noch: Der Faden liest nur (reisen, stand_nummer, exportieren) und schreibt nur in den eigenen temporaeren Ordner; er haelt weder die flock-Sperre noch startet er den Unterprozess. Ein Folgevorgang ist unbeeintraechtigt: Sonde, danach ein normaler Vorgang auf derselben Reise: 200, Stand +1, tmp leer.
- Spaet fertiger Faden kann nichts eintragen: Er setzt nur ergebnis[basis]; die Auswertung ist nach dem Return vorbei, der Eintrag geschieht ausschliesslich im Unterprozess (schreiben.py:4571). Stand nach 5 abgebrochenen Vorgaengen und 4 s Wartezeit unveraendert.
- Lecks: 5 wiederholte Haenger (Export 3 s, Frist 1 s): jede Antwort 1,0 s, bis zu 3 Faeden gleichzeitig; nach dem Auslaufen 0 Faeden, tmp leer (Faden raeumt selbst, Zeile 4546-4548; der Dienst raeumt zusaetzlich in 4576-4577). Das Rennen is_alive/abgebrochen.set ist harmlos: laeuft der Faden dazwischen aus, raeumt der Dienst. Legt der Export Ordner nach dem Dienst-rmtree neu an, raeumt der Faden erneut.
- Restrisiko (LOW, F006): ein dauerhaft haengender Speicher laesst je Anfrage einen Daemon-Faden samt Datenbankverbindung zurueck, ohne Obergrenze ausser den Anfragen (die Sperre je Reise wird nach der Antwort frei). Ohne Datenbank-Hang endet jeder Faden von selbst; Lesezugriffe blockieren im WAL-Modus nicht. Akzeptabel, beobachten.

Confirmation:
  AC: AC-14
  Code reference: engine/schreiben.py:4584
  Evidence: speicher_gesund prueft zuerst reisespeicher.pfad().exists() und legt nichts mehr an; Test gruen. F002 behoben.
  Status: CONFIRMED

Confirmation:
  AC: AC-23
  Code reference: engine/stand.py:127
  Evidence: importlib bleibt mit Begruendungskommentar; als LOW akzeptiert (F004), Laufzeit sicher.
  Status: CONFIRMED

Confirmation:
  AC: AC-25
  Code reference: docs/betrieb.md:19
  Evidence: Tabellenzeile sagt jetzt: ab Stufe 2 schreibt der Schreibweg in den Speicher; F005 behoben.
  Status: CONFIRMED

Confirmation:
  AC: AC-24
  Code reference: betrieb/messlauf-schreibweg.py:141
  Evidence: Skript und Kennzahlen belegt (Runde 2); Serverwerte im Issue 347 sind Prozessnachweis, kein Code.
  Status: CONFIRMED

F003 (LOW, Code reference: engine/instanz.py:98) bleibt offen und ist als akzeptiertes LOW-Finding vermerkt (Issue fuer Stufe 5; Code reference: engine/schreiben_git.py:172). Pflichtdateien weiter zitiert: engine/reisespeicher.py:237, engine/stand_git.py:19, engine/texte_de.py:868, engine/texte_en.py:867.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

F001 (HIGH) und F002 (MEDIUM) behoben und per Sonde bestaetigt; F004, F005 behoben bzw. mit Begruendung akzeptiert; F003 (LOW) und F006 (LOW) als akzeptierte Restrisiken vermerkt.
Tests: 241 gezielt passed (Speicher, Stand, Betrieb, Texte, Pfade), Gesamtlauf 1521 passed, 0 failed, 0 uebersprungen
Edge cases: Faden-Lecks, Folgevorgang, spaeter Faden, Abbruch geprueft, nichts gebrochen
Regressions: Keine
Checklist: 25/25 Punkte bewiesen (AC-24 Serverwerte als Prozessnachweis offen)

## Geprüfte Dateien

- sha256:62e934ee550efa2fe5bc0bd6d90c663af2f41e0e46b5373bc4775dd2dd677904  betrieb/deploy.sh
- sha256:7eed8ca39d76f20058161075b3cf0ee00a0a2c54123dabcb969c26718eb37ebd  betrieb/messlauf-schreibweg.py
- sha256:67528fd46c1533fc79c4fdf13a3f100a7094943e4f24071d2fa0ef2f4646c001  docs/betrieb.md
- sha256:df4cab60634469a9ec4e5ea67c342ef8111582bdacc488df8e94142bf83aab51  engine/instanz.py
- sha256:2d43b163f33b789101e7bf8c2442257c6cf7f1386f4fd05fd15bb2c6b73d37f5  engine/reisespeicher.py
- sha256:0c2e454e99721233e5191202a31e2d7e73fb1e5853c531cbe63d7762b48ede47  engine/schreiben.py
- sha256:0397ce336cd896078888f60da633f21d5a018a4396fad28d22391403d8953fc9  engine/schreiben_git.py
- sha256:64c08f5ec3fa5b5dedcc045909925218848179530c846ecd1c2936578af8c7c2  engine/stand.py
- sha256:2ceae44b6846c207997a60c0b5cf3a8e352fd7b36d30ada0aab0d6680a92536b  engine/stand_git.py
- sha256:c5f1a4117e352e6c7d958c7652b4b088a38df8a67172368a7c95461450c4b40f  engine/texte_de.py
- sha256:f2ec76f8be81034e5566ef1dc07a9e62be92943c1eccf31f106ac58014adfec5  engine/texte_en.py

## Prüfbasis

- base: d5261e6e252d5250a0b2957ef5911cfa36424095
- blob:4ebf787d94e320fb96eb13263cf09c6558b4a703  betrieb/deploy.sh
- blob:d0c6ecc800d03725e3aba83a204529f904ee352f  betrieb/messlauf-schreibweg.py
- blob:7d1af06d91e4018bf246e303673620fb65f52deb  docs/betrieb.md
- blob:f27f4cba0b6c91747ffa164fd3b7192f1bc179e1  engine/instanz.py
- blob:436e18ea2aa937435abd116f818dd2591503019c  engine/reisespeicher.py
- blob:324c70ce72d490fb69d49c4a8ce124c4dc25999d  engine/schreiben.py
- blob:0ca5b9e8e783a3ff90efe46025634cf69d73f391  engine/schreiben_git.py
- blob:037c6a8775a8fcf735431cb70049c7f9c3bb576f  engine/stand.py
- blob:42e1e1b6d05f215e29eace1683ddf307d4b57a7e  engine/stand_git.py
- blob:bfb40cbea2b7d11c328d69e3c7c998fa0bb39d67  engine/texte_de.py
- blob:e07d149be00c9d6dfc17a884a87d53dd3db61875  engine/texte_en.py
