# Adversary Dialog — speicher-346-stufe1
Spec: docs/specs/betrieb/reisespeicher-346.md
Datum: 2026-11-05 20:40

## Checkliste
- [x] **AC-1:** Import und Export beider Beispielreisen (`beispiel/reisen/beispielreise`, `beispiel/reisen/stadtwochenende`) liefern einen Ordner mit gleicher Pfadmenge und Byte für Byte gleichen Dateien (Test 1).
- [x] **AC-2:** `exportieren(reise, ziel, bis=N)` liefert den Stand N einschließlich fehlender (gelöschter) Dateien und Dateien in alter Fassung (Test 2).
- [x] **AC-3:** Über `db()` scheitern UPDATE, DELETE, `INSERT OR REPLACE`, `DROP TRIGGER` und `DROP TABLE` auf beiden Tabellen; die Daten bleiben unverändert (Test 3).
- [x] **AC-4:** Eine bekannte Kennung schreibt nichts und löst `VorgangVorhanden(nummer, stand)` aus; `vorgang_eingetragen(kennung)` findet den Vorgang (Test 4).
- [x] **AC-5:** `stand_nummer` ist `max(stand)`: Import mit `ab=N` ergibt `N+1`, jeder weitere Vorgang `+1` unabhängig von der Zahl der Dateien; unbekannte Reise gibt `None` (Test 5).
- [x] **AC-6:** Unveränderte Dateien erzeugen keine Versionszeile; ein Vorgang ohne jede Änderung ist ein Fehler und legt nichts an (Test 6).
- [x] **AC-7:** `zuruecksetzen` erzeugt einen neuen Vorgang mit Person und Grund, der Verlauf bleibt vollständig, und der neue Stand gleicht dem Ziel-Stand (Test 7).
- [x] **AC-8:** Symlinks, Pfade mit `..` oder NUL, ein nicht leeres Export-Ziel werden abgelehnt, und außerhalb des Ziels wird nichts geschrieben (Test 8).
- [x] **AC-9:** `sichern()` erzeugt `<Speicher>/sicherung/reisen.db` mit bestandenem `integrity_check`; der Rückspieltest (Schnappschuss als neue Datenbank, Export vergleichen) ist grün (Test 9).
- [x] **AC-10:** `pruefen()` findet eine manipulierte Prüfsumme und meldet Reise und Pfad; bei gesunden Daten ist die Liste leer (Test 10).
- [x] **AC-11:** `instanz.speicher()` folgt `FR_SPEICHER` mit Vorgabe `seiten() / "_speicher"`; `betrieb/einstellungen.beispiel` enthält `FR_SPEICHER`; `engine/reisespeicher.py` enthält keine Instanzwerte (Ort nur über `instanz.speicher()`) (Test 12, Test 16 und `test_beispiel_einstellungen_sind_vollstaendig`).
- [x] **AC-12:** `betrieb/waechter.sh` sichert täglich beide Datenbanken; ein Fehlschlag der Reisen-Sicherung meldet `fr_melden high`, ohne die Konten-Sicherung zu verhindern (Test 13).
- [x] **AC-13:** Weder `betrieb/deploy.sh` noch Schreibweg, Konnektor, Rückmeldedienst oder `stand.py` binden `reisespeicher` ein; der Test zur Modulliste ist grün, und der Schreibweg schreibt nicht in den Speicher (Test 14).
- [x] **AC-14:** ADR-0008 (`docs/adr/0008-reisespeicher.md`) mit Index-Zeile in `docs/adr/README.md` und die Ergänzungen in `docs/betrieb.md` liegen vor; ADR-0008 nennt die ehrliche Grenze des Nur-anhängen-Schutzes (Test 15); `engine/tests/test_protokolle_ohne_pfade.py` bleibt grün.
- [x] **AC-15:** Import, Vorgang, Export und Sicherung gelingen ohne auffindbares `git` (Test 16).
- [x] **AC-16:** Die Befehle `importieren`, `exportieren [--bis N]`, `verlauf`, `zuruecksetzen`, `pruefen`, `sichern` über `main` liefern die erwartete Ausgabe und Exitcode 0, bei Fehlern einen Exitcode ungleich 0 (Test 11).

## Dialog

### Runde 1
**Adversary:** Beweis je AC verlangt (Testausgabe, Code-Pfad). Lauf: `pytest -q engine/tests/test_reisespeicher.py engine/tests/test_betrieb.py engine/tests/test_protokolle_ohne_pfade.py` = 154 passed, 0 failed, 0 skipped (docs/artifacts/speicher-346-stufe1/adversary-test-output.txt); `test_reisespeicher.py` allein 41 passed in 1.66 s (unter 5 s). Der Diff gegen die Abzweigung 6a99d74 fuer schreiben.py, stand.py, konnektor.py, rueckmeldungen.py, deploy.sh ist leer, also unveraendert; `grep reisespeicher` in diesen fuenf Dateien: kein Treffer. (Hinweis: Der Diff gegen origin/main zeigt viele fremde Dateien, weil origin/main dem Branch voraus ist; der Vergleich mit der Abzweigung ist der richtige.)
**Implementierer:** (Belege aus Code und Tests)
- AC-1: `test_beispielreise_geht_byte_gleich_durch_import_und_export` (beide Reisen parametrisiert) gruen; Code: `_ordner_lesen`, `exportieren` binaer (Modus "xb").
- AC-2: `test_export_eines_alten_stands` gruen; eigener Lauf: Stand 1 bis 4 einer Reise mit Loeschung und Wiederkehr exportiert korrekt, Stand 0, -1 und 99 geben `KeyError`.
- AC-3: `test_verlauf_laesst_sich_ueber_db_weder_aendern_noch_loeschen` gruen; eigener Lauf: UPDATE, DELETE, INSERT OR REPLACE, REPLACE INTO, UPSERT (ON CONFLICT DO UPDATE), DROP TABLE/TRIGGER/INDEX, ALTER TABLE (RENAME, ADD COLUMN), writable_schema scheitern, Zaehlung (3 Vorgaenge, 5 Versionen) unveraendert. Einschraenkung siehe Runde 2 (F001).
- AC-4: `test_bekannte_kennung_schreibt_nichts` gruen; `_eintragen` prueft die Kennung zuerst; nach einem `ValueError` ("nothing changed") bleibt die Kennung unbenutzt (Rollback in `_transaktion`), eigener Lauf bestaetigt.
- AC-5: `test_stand_nummer_zaehlt_vorgaenge_ab_uebernommener_zahl` gruen; Stand = (ab oder hoechster) + 1, `stand_nummer` ist MAX(stand) und None bei unbekannter Reise.
- AC-6: `test_unveraenderte_dateien_ergeben_keine_zeile` gruen; Loeschen einer unbekannten Datei ergibt `ValueError`, keine Zeile (eigener Lauf).
- AC-7: `test_zuruecksetzen_ist_ein_neuer_vorgang` und `test_zuruecksetzen_ohne_abweichung_oder_ohne_angaben_scheitert` gruen; eigener Lauf: unbekannter Stand `KeyError`, aktueller Stand `ValueError`, leere Person `ValueError`.
- AC-8: `test_symlink_bricht_den_import_ab`, `test_export_prueft_pfade_und_schreibt_nichts_ausserhalb`, `test_export_in_nicht_leeres_ziel_scheitert` gruen; eigener Lauf: Symlink im Unterordner, Symlink als Wurzel und FIFO werden abgelehnt (die Reise bleibt unbekannt).
- AC-9: `test_sichern_und_zurueckspielen` gruen; `sichern` nutzt die Backup-API, integrity_check, os.replace, `finally` raeumt die Temp-Datei.
- AC-10: `test_pruefen_findet_verfaelschte_pruefsumme` gruen; gesunde Daten geben eine leere Liste (eigener Lauf).
- AC-11: `test_ort_des_speichers`, `test_einstellungen_beispiel_nennt_den_speicher`, `test_quelltext_ohne_instanzwerte` gruen; `instanz.speicher()` mit Vorgabe seiten()/"_speicher".
- AC-12: `betrieb/waechter.sh` ruft beide Sicherungen je in einem "if !"-Block mit fr_melden high und fehler=1 auf, erst danach exit 1; der Waechtertest in test_betrieb.py ist gruen.
- AC-13: Test 14 gruen, Diff leer, kein Treffer fuer reisespeicher.
- AC-14: `test_adr_und_betriebsdoku` gruen, ADR-0008 hat die Abschnitte und die Grenze (Stichwort "Schreibzugriff auf die Datei"), Index-Zeile 0008 vorhanden, `test_protokolle_ohne_pfade.py` gruen.
- AC-15: `test_laeuft_ohne_git` gruen; Modul ohne subprocess.
- AC-16: `test_befehle` gruen; eigener Lauf mit 18 Aufrufen: falsche Argumente Exitcode 1 (Hilfe), Fehler Exitcode 2, `pruefen` mit Abweichung Exitcode 3, Erfolg 0.

### Runde 2
**Adversary:** Eigene Grenzfaelle mit Wegwerf-Skripten (nur im Scratchpad, nur FR_SPEICHER und FR_SEITEN dort). Ergebnisse:
1. Alle Standard-Angriffe aus Test 3 werden gestoppt (siehe oben), auch REPLACE INTO, UPSERT, ALTER TABLE RENAME, writable_schema.
2. Umgehung: Der Authorizer sperrt PRAGMA recursive_triggers und PRAGMA foreign_keys nicht. Nach recursive_triggers=OFF und foreign_keys=OFF ueber db() ersetzt INSERT OR REPLACE INTO vorgaenge (nummer 77, stand 1) den Vorgang mit Stand 1, ohne dass ein DELETE-Trigger feuert: Der Verlauf verliert den Vorgang samt Kennung, `aktueller_stand(reise, 1)` ist danach leer, die Versionszeilen bleiben verwaist. `pruefen()` meldet nur "stand 1 of operation 77 does not follow stand 2". Mit nur recursive_triggers=OFF stoppt noch der Fremdschluessel. Siehe F001.
3. Pfade: "a//b", "/x", "a/./b", "a/", "", "..", "a/../b" und NUL werden abgelehnt. Ein Backslash-Pfad und ".git/config" werden angenommen; der Export von ".git/config" legt einen Ordner .git im Ziel an, obwohl der Import .git auslaesst. Siehe F003.
4. Eine Reise mit Datei q und q/r im selben Vorgang wird gespeichert, der Export scheitert mit `FileExistsError` und laesst ein halb beschriebenes Ziel zurueck. Siehe F004.
5. `vorgang_eingetragen` auf einer Instanz ohne Datenbank legt Ordner und Datei an (`db()`), obwohl die Spec "kein Schreibzugriff" sagt. Siehe F002.
6. Export-Ziel ist ein Symlink auf einen fremden leeren Ordner: der Export schreibt dort hinein (aufgeloester Pfad). Siehe F005.
7. Tombstone-Wiederkehr (Stand 1 Datei, 2 weg, 3 wieder) und Export von Stand 1 bis 4 stimmen; die Kennung bleibt nach `ValueError` unbenutzt.
8. `sichern` bei fehlschlagendem integrity_check: Der Code wirft vor os.replace, `finally` loescht die Temp-Datei, die alte Sicherung bleibt (per Code geprueft, keine kaputte Datei erzeugt). Ohne Datenbank gibt `sichern` still None und Exitcode 0 (spec-konform).
9. Waechter: Reihenfolge Konten, dann Reisespeicher, beide in "if !", set -e greift nicht; der Fehlschlag der ersten verhindert die zweite nicht.
**Implementierer:** F001 ist real und mit zwei PRAGMAs reproduzierbar (Wegwerf-Skript im Scratchpad). Die uebrigen Punkte sind kleine Abweichungen ohne Datenverlust im Verlauf.

### Runde 3
**Adversary:** Nachpruefung nach dem Fix des Entwicklers (Iteration 2). Meine Umgehungsskripte aus Runde 2 laufen erneut gegen den neuen Code:
1. F001: `PRAGMA recursive_triggers=OFF` und `PRAGMA foreign_keys=OFF` scheitern jetzt mit "not authorized" (Authorizer verweigert jede PRAGMA mit Wert, Zeile 85). INSERT OR REPLACE nach dem Versuch: ebenfalls verweigert; Zaehlung (3 Vorgaenge, 5 Versionen) und `pruefen()` unveraendert leer.
2. Neue Umgehungsversuche, alle gestoppt: `PRAGMA main.recursive_triggers=0`, Kleinschreibung, Klammerform `PRAGMA recursive_triggers(0)`, `main.foreign_keys(0)`, defer_foreign_keys, journal_mode, locking_mode, schema_version, wal_checkpoint, case_sensitive_like, writable_schema (auch als Funktion), `VACUUM` und `VACUUM INTO`, ATTACH, `load_extension`, `executescript` mit DELETE oder PRAGMA, CREATE TEMP TRIGGER auf die Tabelle (SQLite lehnt ab). Erlaubt bleiben nur lesende Abfragen (`pragma_recursive_triggers`, `PRAGMA integrity_check`, `data_version`), die nichts aendern.
3. Pfade: Backslash und .git werden jetzt abgelehnt; Datei/Ordner-Kollision (q und q/r) wird im selben Vorgang und ueber getrennte Vorgaenge abgelehnt (nach Loeschen von q ist q/r erlaubt, der Export gelingt); ein Export in ein Symlink-Ziel scheitert mit "target is a symlink" und schreibt nichts.
4. Regression: importieren (neu, unveraendert, geaenderte Datei), zuruecksetzen, sichern, pruefen und verlauf arbeiten weiter; Sicherung wird erzeugt, pruefen ist leer.
5. Neuer Befund F006: Die Backup-API von Python ueberschreibt eine Verbindung aus db() als Ziel (`sqlite3.connect(andere.db).backup(v)`): Danach fehlen in der Datei beide Tabellen. Der Authorizer sieht diese API nicht. Das ist ein bewusster Aufruf einer anderen API, kein SQL ueber db(), und gleichwertig zum direkten Oeffnen der Datei (die dokumentierte Grenze). Kein Software-Fehler im Schreibweg wuerde das tun. Ich fuehre es als MEDIUM ohne Blockade; Abhilfe: im ADR in einem Satz nennen. Ebenso kann CREATE TEMP TABLE vorgaenge die Tabelle nur in der eigenen Verbindung ueberdecken (keine Wirkung auf die Datei).
**Implementierer:** Status der Findings: F001 behoben (Authorizer Zeile 79 bis 88, Test test_pragma_mit_wert_und_attach_scheitern_ueber_db), F003 behoben (_pfad_pruefen Zeile 111 ff, Test test_backslash_und_git_pfade_im_vorgang), F004 behoben (_kollision_pruefen, Tests test_datei_und_ordner_gleichen_namens_werden_abgelehnt und test_export_mit_kollision_schreibt_nichts), F005 behoben (Test test_export_in_symlink_als_ziel_scheitert), F002 akzeptiert (entspricht dem Muster von konten.py, db() legt beim ersten Zugriff an), F006 MEDIUM, nicht blockierend: ADR-0008 ergänzt (Zeile 28), geprüft (Satz beschreibt die Online-Backup-Schnittstelle mit einer Verbindung des Moduls als Ziel korrekt, keine absoluten Pfade, keine Reisenamen; test_adr_und_betriebsdoku und test_protokolle_ohne_pfade grün). Tests: 163 passed, 0 failed, 0 skipped (Waechter, Betrieb, Protokolle und Speicher zusammen); `test_reisespeicher.py` allein 50 passed in 1.66 s. Schreibweg, Konnektor, Rueckmeldedienst, stand.py und deploy.sh weiterhin unveraendert gegenueber 6a99d74.

## Findings

Finding:
  ID: F001
  Severity: HIGH
  Category: security
  Code reference: engine/reisespeicher.py:78
  Description: Der Authorizer _waechter verweigert UPDATE und DELETE, DROP, ALTER und writable_schema, laesst aber PRAGMA recursive_triggers und PRAGMA foreign_keys zu (Zeilen 80 bis 86). Die Trigger-Schicht haengt an recursive_triggers = ON (Zeile 100).
  Spec requirement: AC-3 und Definition of Done: "Der Verlauf laesst sich ueber db() weder aendern noch loeschen"; Spec "Nur anhaengen": INSERT OR REPLACE darf nicht am Schutz vorbei loeschen.
  Conflict: Nach PRAGMA recursive_triggers=OFF und PRAGMA foreign_keys=OFF ersetzt INSERT OR REPLACE INTO vorgaenge einen vorhandenen Vorgang ohne Trigger: Verlaufseintrag und Kennung sind weg, Stand 1 ist leer. Nur pruefen() meldet es, und nur als Stand-Folge-Fehler.
  Remediation: Im Authorizer SQLITE_PRAGMA fuer recursive_triggers, foreign_keys, ignore_check_constraints und trusted_schema verweigern (wie writable_schema); zusaetzlich INSERT OR REPLACE auf beide Tabellen abfangen (z. B. SQLITE_DBCONFIG_DEFENSIVE oder Konfliktpruefung); Test 3 um beide PRAGMAs erweitern.

Finding:
  ID: F002
  Severity: LOW
  Category: spec_violation
  Code reference: engine/reisespeicher.py:213
  Description: vorgang_eingetragen (und stand_nummer, verlauf, aktueller_stand) rufen db(), das bei fehlender Datei Ordner und Datenbank anlegt (Zeilen 92 bis 106).
  Spec requirement: Schnittstelle: vorgang_eingetragen "kein Schreibzugriff".
  Conflict: Ein reiner Lesezugriff erzeugt Datei und Schema.
  Remediation: Lesefunktionen ohne Anlegen oeffnen (mode=ro) oder das Anlegen ausdruecklich dokumentieren.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/reisespeicher.py:111
  Description: _pfad_pruefen lehnt "", ".", ".." und leere Teile ab, nicht aber Backslash und Pfade unter .git.
  Spec requirement: Pfadregeln (POSIX); der Import nimmt .git aus.
  Conflict: vorgang_schreiben("a", ".git/config") wird gespeichert und beim Export als .git ins Ziel geschrieben; ein erneuter Import liesse die Datei als Tombstone fallen.
  Remediation: Pfade mit erstem Teil .git und mit Backslash ablehnen.

Finding:
  ID: F004
  Severity: LOW
  Category: edge_case
  Code reference: engine/reisespeicher.py:232
  Description: Der Export prueft Pfade, aber nicht, ob eine Datei zugleich Ordner eines anderen Pfades ist (q und q/r).
  Spec requirement: Export (Docstring Zeilen 233 bis 234): bricht ab, bevor etwas geschrieben ist.
  Conflict: Der Export wirft FileExistsError erst beim Schreiben und hinterlaesst ein halb beschriebenes Ziel; _eintragen hat den Konflikt zuvor zugelassen.
  Remediation: In _eintragen und im Plan des Exports Datei/Ordner-Konflikte erkennen (ein Pfad ist Praefix eines anderen).

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/reisespeicher.py:239
  Description: ziel.resolve() folgt einem Symlink als Ziel; der Export schreibt in den dahinter liegenden leeren Ordner.
  Spec requirement: AC-8: ausserhalb des Ziels wird nichts geschrieben.
  Conflict: Das Ziel ist formal der Symlink, geschrieben wird beim Ziel des Links. Nur bei leerem Ziel und einem vom Betreiber benannten Pfad, daher gering.
  Remediation: Ein Ziel, das ein Symlink ist, ablehnen.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/reisespeicher.py:258
  Evidence: _ordner_lesen und exportieren (binaer, Modus "xb"); Test 1 gruen fuer beide Beispielreisen.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/reisespeicher.py:124
  Evidence: _stand waehlt je Pfad die juengste Version mit stand <= bis, Tombstones fallen weg; eigener Lauf Stand 1 bis 4.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/reisespeicher.py:59
  Evidence: Trigger und Authorizer stoppen die in Test 3 genannten Anweisungen; Einschraenkung siehe F001.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/reisespeicher.py:146
  Evidence: Kennungspruefung vor jedem Schreiben, VorgangVorhanden(nummer, stand); vorgang_eingetragen ab Zeile 213.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/reisespeicher.py:170
  Evidence: Stand = (ab oder hoechster) + 1; stand_nummer ist MAX, None bei unbekannter Reise.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/reisespeicher.py:168
  Evidence: Leeres neu gibt ValueError, Rollback in _transaktion (Zeile 181).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/reisespeicher.py:301
  Evidence: Pflichtfelder, neuer Vorgang mit herkunft zuruecksetzen:<bis>, Verlauf unveraendert; Fehler bei unbekanntem oder aktuellem Stand.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/reisespeicher.py:261
  Evidence: Symlink, Sonderdatei, "..", NUL und nicht leeres Ziel abgelehnt (eigener Lauf); der Export prueft aufgeloeste Pfade (Zeilen 243 bis 245).
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/reisespeicher.py:350
  Evidence: Backup-API, integrity_check, atomares os.replace, Temp-Datei im finally geloescht; Test 9 gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/reisespeicher.py:319
  Evidence: Pruefsummen neu gerechnet, Meldung mit Reise und Pfad; Test 10 gruen, gesunde Daten leer.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/instanz.py:91
  Evidence: speicher() = wert("FR_SPEICHER") or seiten()/"_speicher"; Zeile in betrieb/einstellungen.beispiel:30; das Modul liest keine Umgebung (Test 16).
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: betrieb/waechter.sh:30
  Evidence: Zweite Sicherung mit fr_melden high und fehler=1, beide laufen unabhaengig; Test 13 gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: betrieb/deploy.sh:1
  Evidence: Diff gegen 6a99d74 fuer schreiben.py, stand.py, konnektor.py, rueckmeldungen.py, deploy.sh leer; kein Treffer fuer reisespeicher.
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: docs/adr/0008-reisespeicher.md:28
  Evidence: Abschnitte Status bis Verlauf, ehrliche Grenze Zeile 28, Index-Zeile docs/adr/README.md:14, docs/betrieb.md:37.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/reisespeicher.py:27
  Evidence: Importe nur collections, hashlib, os, sqlite3, contextlib, pathlib, instanz, stand; kein subprocess.
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/reisespeicher.py:393
  Evidence: main gibt 0, bei falschen Argumenten 1, bei Fehlern 2, bei Abweichung von pruefen 3 (eigener Lauf).
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Status der Findings (Iteration 2)

- F001 behoben, F003 behoben, F004 behoben, F005 behoben (Runde 3).
- F002 LOW akzeptiert: entspricht dem Muster von konten.py.
- F006 MEDIUM (neu, nicht blockierend):

Finding:
  ID: F006
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/reisespeicher.py:98
  Description: db() liefert eine normale sqlite3-Verbindung; die Backup-API von Python (andere Verbindung als Quelle, die db()-Verbindung als Ziel) umgeht den Authorizer und ersetzt den Dateiinhalt.
  Spec requirement: Ehrliche Grenze: kein Schutz gegen Schreibzugriff auf die Datei.
  Conflict: Liegt an der Grenze des Schutzes, ist aber im ADR nicht ausdruecklich genannt.
  Status: ADR-0008 ergänzt (Zeile 28), geprüft.
  Remediation: Einen Satz im ADR-0008; Gegenmittel bleiben pruefen und die Sicherung ausser Haus.

## Verdict

VERDICT: VERIFIED

Alle 16 ACs sind belegt, F001 ist behoben und nicht mehr umgehbar (PRAGMA, ATTACH, VACUUM, executescript, load_extension geprueft), F003 bis F005 behoben, F002 akzeptiert, F006 MEDIUM als dokumentierbare Grenze. Tests: 163 passed, 0 failed, 0 skipped.

Code reference: engine/instanz.py:91
Code reference: engine/reisespeicher.py:79

## Geprüfte Dateien

- sha256:db21cb28836951f57e3bdf3f48c1ca1e5b30b3a6c4e66694fc62cbe045d00cc1  betrieb/deploy.sh
- sha256:e28cb33efa305e5e6ec208b944da0674f37e2e915dd21adc42da09d310235aef  betrieb/waechter.sh
- sha256:db79a2fb1477cb6bb8ef858b22f6e38f885eeba203d2036ba3cbb8702fdb182d  docs/adr/0008-reisespeicher.md
- sha256:e9dcbe527711c2572936873ccd5e07d6c9a32edd3a1b996f361f3a74313a4d1c  engine/instanz.py
- sha256:890679e3afb1c5b77c5f8a92def6ebb198ea02a60c59798ff198a0f80e398861  engine/reisespeicher.py

## Prüfbasis

- base: 6a99d7491883862910f3ba27191ca502a2e93e6d
- blob:3eefb8ccc13f0e3aef3ecb49fe43bac25d0be02c  betrieb/deploy.sh
- blob:4d62be79c3d74b810885d5c522f9d6ea63b49fe7  betrieb/waechter.sh
- blob:0b493c81ed343b3b48b02bc601649157645bf7d4  docs/adr/0008-reisespeicher.md
- blob:d9250ff1477990263aa8dc97f30aa7b36d983246  engine/instanz.py
- blob:46d1db762c1a4abfe61129535b708f51fc1099d7  engine/reisespeicher.py
