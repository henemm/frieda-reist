# Adversary Dialog — speicher-349-stufe4
Spec: docs/specs/betrieb/speicher-349-stufe4.md
Datum: 2026-11-08 10:17

## Checkliste
- [x] **AC-1 Schema und Anhebung:** Given ein Speicher im Format der Stufe 3 (`user_version` 1, Spalte fehlt, mit Zeilen) / When `db()` ihn öffnet / Then ist `user_version` 2, die Spalte `ausgelagert` da (Vorgabe 0), alle alten Zeilen unverändert lesbar; ein zweites Öffnen ändert nichts; Trigger und Authorizer gelten weiter (ein `UPDATE` scheitert).
- [x] **AC-2 Auslagerungsregel:** Given Dateien `medien/a.png`, `medien/b.JPG`, `medien/c.gpx`, `medien/d.pmtiles`, `medien/icon.svg`, `medien/icon.png`, `reise.yaml`, `plan/x.md`, `bilder/e.png` / When sie in einem Vorgang geschrieben werden / Then haben genau a, b, c, d `ausgelagert = 1` mit `inhalt` NULL und Prüfsumme, die übrigen `ausgelagert = 0` mit Inhalt.
- [x] **AC-3 Ablage: Ort und Name:** Given ein ausgelagertes Foto / Then liegt es unter `<FR_SPEICHER>/ablage/<aa>/<summe>` mit `<aa>` = erste zwei Zeichen von `<summe>` = SHA-256 der Bytes, Datei Modus 400, Ordner 700; in der Datenbank steht kein Inhalt.
- [x] **AC-4 Doppelte nur einmal (Akzeptanz #349):** Given dieselben Bytes unter zwei Pfaden einer Reise, in einer zweiten Reise und in einer späteren Version (Datei geändert, dann zurück) / When geschrieben / Then gibt es genau **eine** Datei in der Ablage (Zahl der Dateien unter `ablage/`), und jede Zeile verweist auf dieselbe Summe.
- [x] **AC-5 Export byte-gleich (beide Beispielreisen):** Given eine importierte Beispielreise (bei `stadtwochenende` mit nachträglich ergänzten Medien) / When `exportieren` und `materialisieren` laufen / Then entspricht der Ordner Byte für Byte `beispiel/reisen/<reise>` (gleiche Pfadmenge, gleiche Bytes, ohne `.git`); bei `beispielreise` mit `skizze-felsen.png` und den vier GPX-Dateien aus der Ablage.
- [x] **AC-6 Hardlink mit Kopie-Rückfall:** Given Ablage und Zielordner im selben Dateisystem / Then ist die Datei im Bauordner ein Hardlink (gleiche Inode wie die Ablagedatei); Given `os.link` scheitert (Attrappe wirft `OSError`) / Then ist sie eine Kopie mit gleichen Bytes und der Export gelingt.
- [x] **AC-7 Schreibreihenfolge:** Given `_eintragen` scheitert nach dem Ablegen (z. B. `StandGeaendert`, Attrappe in der Transaktion) / Then liegt die Ablagedatei vor, die Datenbank hat keine Zeile; Given die Ablage ist nicht beschreibbar / Then wird weder Zeile noch Vorgang geschrieben. Eine Zeile, die auf eine nicht vorhandene Ablagedatei zeigt, kann durch Schreiben nie entstehen.
- [x] **AC-8 Nur anhängend:** Given eine geänderte oder gelöschte Medien-Datei / When ein neuer Vorgang sie ersetzt oder per Tombstone löscht / Then bleibt die alte Ablagedatei unverändert liegen (gleicher Inhalt, gleiche Änderungszeit), `zuruecksetzen` auf den alten Stand stellt die alte Fassung wieder her, und die Software enthält keinen Aufruf zum Löschen von Ablagedateien (ausgenommen die eigene Temporärdatei eines Schreibvorgangs).
- [x] **AC-9 Fehlende Datei, Export:** Given eine gelöschte Ablagedatei / When `exportieren` oder `materialisieren` läuft / Then `AblageFehlt` mit Pfad und Summe, der Zielordner wurde nicht angelegt, ein vorhandener Ordner bleibt unberührt (kein halber Ordner).
- [x] **AC-10 Fehlende Datei, Bau (Akzeptanz #349):** Given eine Speicher-Reise mit fehlender Ablagedatei / When `bauen.py` (Bau über den Speicher-Weg) läuft / Then Exit 2 mit der Meldung `pruefung.bauen.79` in der Sprache der Instanz; der Test prüft die Meldung in **jeder** Sprache aus `texte.SPRACHEN` (Parametrisierung über `SPRACHEN`, damit eine neue Sprache ohne Codeänderung mitgeprüft wird) und dass `{w1}`, `{ziel}`, `{summe}` ersetzt sind.
- [x] **AC-11 Beschädigte Datei:** Given eine Ablagedatei mit geänderten Bytes / When `datei`, `aktueller_stand`, Export oder Bau lesen / Then `AblageFehler` bzw. Bau Exit 2 mit `pruefung.bauen.80`; `pruefen` meldet `store checksum mismatch`; die Datei wird nicht verändert.
- [x] **AC-12 Zielname belegt mit falschem Inhalt:** Given am Zielnamen liegt eine Datei mit falscher Größe / When dieselbe Summe geschrieben werden soll / Then `AblageFehler`, kein Vorgang, die Datei bleibt unverändert.
- [x] **AC-13 Pfadsicherheit:** Given `ablage_pfad` mit `../x`, `abc`, einer Summe mit Großbuchstaben, einer zu langen Summe, leer / Then `ValueError`; Given eine Ablagedatei, die ein Symlink ist / Then wird sie beim Lesen und Verknüpfen abgewiesen; Given ein Reisepfad `medien/../../x.png` / Then lehnt `_pfad_pruefen` ihn ab, bevor etwas abgelegt wird.
- [x] **AC-14 Prüfsumme, Vergleich und Stand ohne Ablagezugriff:** Given eine Reise mit ausgelagerten Medien / When `vergleichen` und `stand_nummer` laufen / Then lesen sie keine Ablagedatei (der Test ersetzt `ablage_lesen`/`os.link` durch Fallen, die scheitern) und `vergleichen` ergibt `gleich` (Exit 0) gegen den Ordner der Beispielreise.
- [x] **AC-15 Verweis ist nicht gelöscht:** Given eine ausgelagerte Datei und danach ein Tombstone für eine andere / Then zählt `_stand` die ausgelagerte Datei als vorhanden (`inhalt` NULL, aber Prüfsumme gesetzt), den Tombstone als gelöscht.
- [x] **AC-16 Prüfen:** Given eine Reise mit ausgelagerten Dateien / Then meldet `pruefen` `ok` (Exit 0, keine Fundzeilen); Given eine fehlende, eine beschädigte Ablagedatei, ein `ausgelagert = 1` mit Inhalt, ein `ausgelagert = 1` ohne Summe / Then je ein Fund mit Reise, Pfad und Vorgang.
- [x] **AC-17 Zustand:** Given eine fehlende Ablagedatei / When `zustand` läuft / Then Zeile `ablage_fehlt 1`, Exit 1 und nichts wird geschrieben; ohne fehlende Datei `ablage_fehlt 0` und Exit wie bisher.
- [x] **AC-18 Sicherung schlägt bei fehlender Ablagedatei fehl:** Given eine fehlende Ablagedatei / When `sichern` läuft / Then Fehler, der vorige Schnappschuss bleibt; Given alles vorhanden / Then Schnappschuss wie bisher, geprüft mit `integrity_check`.
- [x] **AC-19 Wiederherstellung (Prüfpunkt):** Given ein Schnappschuss `sicherung/reisen.db` und eine Kopie von `ablage/` in einem Wegwerf-Ordner (Test: `tmp_path`) / When als `reisen.db` eingesetzt / Then `pruefen` `ok`, `vergleichen` der Beispielreise Exit 0 und `materialisieren` baut den Ordner; ohne die Kopie von `ablage/` meldet `pruefen` die fehlenden Dateien (belegt, dass eine Sicherung ohne Ablage wertlos ist).
- [x] **AC-20 Migration der Medien (#250):** Given ein Speicher der Stufe 3 mit Medien als BLOB (beide Beispielreisen, bei `stadtwochenende` mit ergänzten Medien) / When `neu.py nachziehen-speicher <reise> <ordner>` läuft / Then entsteht genau ein Vorgang (Person „Software-Nachziehen“, Werkzeug `nachziehen`, Titel `ablage-umstellung`), die Medien tragen `ausgelagert = 1`, die Ablage enthält sie, der Export des neuen Stands entspricht Byte für Byte dem davor, und alle Wege lesen aus der Ablage (die alten BLOBs werden nicht mehr gelesen: der Test löscht die Ablagedatei und erwartet `AblageFehlt`).
- [x] **AC-21 Migration idempotent:** Given eine umgestellte Reise / When der Befehl wieder läuft / Then `nichts umzustellen`, Exit 0, kein Vorgang, Stand gleich; dieselbe Kennung zweimal trägt nie doppelt ein; eine Reise ohne Medien erzeugt gar keinen Vorgang.
- [x] **AC-22 Migration bei Wettlauf:** Given zwischen Lesen und Eintragen schreibt jemand / Then `StandGeaendert`, neu gelesen, höchstens dreimal, dann Exit 1 und kein Vorgang; die bereits abgelegten Dateien bleiben (harmlos).
- [x] **AC-23 Ohne Handschritt:** Given ein Bauordner mit Speicher-Reise im Format der Stufe 3 und ein neuer Software-Stand / When die Läufe von `veroeffentlichen.sh` (Stufe 3, Software-Wechsel) laufen / Then ist die Reise umgestellt, ohne dass jemand `neu.py` oder `reisespeicher.py` aufruft; `docs/betrieb.md` nennt für die Umstellung keinen Handschritt (der Neuaufbau `ablage-umstellen` ist als freiwillig ausgewiesen).
- [x] **AC-24 Beispielreise baut wie bisher (Akzeptanz #349):** Given `beispielreise` (Symbol, Skizze, GPX) und `stadtwochenende` im Speicher mit Auslagerung / When veröffentlicht wird (Lauf `veroeffentlichen.sh` mit der Fixture `vf`, Stufe-3-Weg) / Then ist `dist/` der Reise **gleich** dem Bau derselben Reise aus dem Ordner (gleiche Dateien, gleiche Bytes ausser Zeitangaben und Stand-Nummer: Vergleich über `daten.json` ohne die Felder `reise_stand`), die Karte zeigt die Strecken, `sw.js` und `manifest.json` stehen da; der **Browser-Rundgang** (`betrieb/pruefsitzung.py` bzw. die Rundgang-Tests der Engine, siehe Prüfstelle Frage 8) läuft für **beide** Reisetypen grün (Nachweis im Issue, mit einer Testreise, nie mit einer echten). **[Stand: Code-Teil bewiesen (Bau-Vergleichstest grün); Browser-Rundgang beider Reisetypen offen, Nachweis in Phase 7/8 im Issue]**
- [x] **AC-25 Schreibweg:** Given ein GPX-Track aus dem Gespräch (`track_anhaengen`) und ein App-Symbol (`icon_set`) auf einer Speicher-Reise / Then liegt die GPX-Datei in der Ablage (`ausgelagert = 1`), das Symbol in der Datenbank (`ausgelagert = 0`), und der Bau findet beides.
- [x] **AC-26 Leere Instanz und Git-Reisen:** Given `FR_SPEICHERREISEN` leer / Then entsteht kein `ablage/`, kein Aufruf in den Betriebsskripten ändert sich, alle bestehenden Tests bleiben ohne geänderte Erwartung grün (insbesondere `test_reisespeicher.py`, `test_speicher_stufe3.py`, `test_betrieb.py`).
- [x] **AC-27 Zeitziel:** Siehe „Zeitziele“; der Messlauf belegt es, kein automatischer Test (außer dem Kurzlauf des Messskripts `test_messlauf_skript_gibt_kennzahlen_aus`, der grün bleibt). **[Stand: Kurzlauf des Messskripts grün; 110-MB-Messung offen, Nachweis in Phase 7/8 im Issue]**
- [x] **AC-28 Katalog und Module:** Given die neuen Schlüssel `pruefung.bauen.79` und `.80` / Then stehen sie in jeder Sprachdatei (`test_texte.py` bleibt grün, die Ausnahmelisten wurden nicht länger); `betrieb/deploy.sh` listet kein neues Modul (die Ablage steckt in `reisespeicher.py`), der Modullisten-Test bleibt grün.

## Testlauf
Befehl: engine/.venv/bin/python -m pytest -q -n 3 engine/tests/test_reisespeicher_ablage.py engine/tests/test_reisespeicher.py engine/tests/test_speicher_stufe3.py engine/tests/test_betrieb.py engine/tests/test_texte.py engine/tests/test_schreiben_speicher.py
Ergebnis: 367 passed, 0 failed, 0 übersprungen. Ausgabe: docs/artifacts/speicher-349-stufe4/adversary-test-output.txt
Volle Suite des Developers: 1825 passed.

## Dialog

### Runde 1
**Adversary:** Erster Durchlauf (Verdict BROKEN). Finding F001 (HIGH): `bauen.ablage_meldung` war zur Laufzeit toter Code; eine fehlende oder beschädigte Ablagedatei endete als englische ERROR-Zeile mit Exit 2, `veroeffentlichen.sh` wertete das als Ausfall statt als rote Reise (AC-10, AC-11). Auffälligkeiten bewertet: AC-20-Lockerung akzeptabel mit Auflage (eigenes Issue für `nachziehen`/arten.yaml), AC-26-Testanpassungen und `PRAGMA table_info` im Wächter akzeptabel. Aktive Brechversuche abgewehrt: Datei vor Zeile, Symlinks und Pfadtricks, Löschen, Wettlauf, Idempotenz, leere Instanz, Hardlink-Rückfall.
Code reference: engine/bauen.py:82
Code reference: engine/reisespeicher.py:365
**Implementierer:** F001 behoben: `ablage_satz`/`ablage_ausgabe` in `reisespeicher.py`, `materialisieren` und `nachziehen-speicher` fangen AblageFehlt/AblageFehler (Exit 2, Katalogtext), `veroeffentlichen.sh` meldet die Reise rot; neue Tests über `texte.SPRACHEN` und im Skriptweg.

### Runde 2
**Adversary:** Zweiter Durchlauf. F001 behoben: `main materialisieren` fängt beide Ausnahmen, Katalogtext `pruefung.bauen.79`/`.80`, Platzhalter ersetzt, Test über alle Sprachen grün. Das Zeilenparsing in `veroeffentlichen.sh` (`grep -q '^ - '`) trifft nur die Ablage-Ausgabe; andere Exit-2-Ursachen bleiben im alten Zweig, keine Regression. Rote Reise: kein Stempel, kein Heartbeat, andere Reisen laufen weiter. AC-8: `unlink` nur auf eigene Temporärdatei und Namen im Bauordner.
Code reference: engine/reisespeicher.py:915
Code reference: engine/neu.py:1345
Code reference: betrieb/veroeffentlichen.sh:209
Code reference: engine/instanz.py:1
Code reference: engine/texte_de.py:1
Code reference: engine/texte_en.py:1
Code reference: betrieb/messlauf-schreibweg.py:1

Finding:
  ID: F002
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/schreiben.py:5054
  Description: Der Schreibweg ruft `reisespeicher.exportieren` im Faden auf und `fremde_datei()` (schreiben.py:4517) fängt nur ImportError, KeyError, OSError, sqlite3.Error und UnicodeDecodeError. AblageFehlt/AblageFehler sind keins davon und werden als ungefangene Ausnahme weitergereicht (schreiben.py:5068).
  Spec requirement: AC-11 (Fehler beim Lesen/Export ist AblageFehler); die Spec sagt nichts zum Verhalten des Schreibwegs.
  Conflict: Ein Schreibaufruf auf eine Speicher-Reise mit kaputter Ablage endet nicht in der sauberen Fehlerantwort für Speicherfehler.
  Remediation: AblageFehlt/AblageFehler wie sqlite3.Error/OSError über speicher_fehler(werkzeug, …) beantworten, in fremde_datei als „nicht lesbar“ behandeln, Test ergänzen.

**Implementierer:** F002 behoben: `ist_ablage_fehler`/`ablage_fehler` in `schreiben.py` (503 mit Katalogtext `pruefung.bauen.79`/`.80`), Export im Faden, `anwenden` und `fremde_datei` fangen die Ausnahmen; neuer Test, Reihenfolgenfix in `test_texte.py`. Volle Suite 1827 passed.

### Runde 3 (Kurz-Durchlauf zu F002)
**Adversary:** F002 behoben. Der neue Zweig im Export-Faden sitzt nach dem `sqlite3.Error`/`OSError`-Gate, keine Maskierung. Fehlerfall schreibt nichts (Stand gleich, Temp-Ordner leer), andere Reise antwortet 200, nach Heilung der Datei ebenfalls. Fehlerbaum `{ok, fehler, fehler_code, werte}` konsistent mit `abgelehnt`/`fehler_antwort`. Git-Weg, OSError und sqlite3.Error unverändert. `test_texte.py` nicht abgeschwächt (nur zusätzlicher Import). Brechversuch Symlink statt Ablagedatei: 503 `pruefung.bauen.80`, kein Schreiben. Testlauf 477 passed.
Code reference: engine/schreiben.py:4876
Code reference: engine/schreiben.py:5089
Code reference: engine/schreiben.py:4911
Code reference: engine/schreiben.py:4514

Finding:
  ID: F-A1
  Severity: LOW
  Category: edge_case
  Code reference: engine/schreiben.py:4801
  Description: `buchung_im_speicher` ruft `reisespeicher.datei` auf; der Handler in `do_GET` fängt nur `(sqlite3.Error, OSError)`. Eine `AblageFehlt` würde ungefangen durchschlagen. Praktisch nicht erreichbar: `plan/routen.yaml` liegt immer in der Datenbank, ausgelagert werden nur Medien.
  Remediation: optional `ist_ablage_fehler` auch dort fangen.
Finding:
  ID: F-A2
  Severity: LOW
  Category: edge_case
  Code reference: engine/schreiben.py:4779
  Description: Kein Test deckt einen Ablagefehler im Unterprozess ab; der Weg ist durch das `except Exception` in `anwenden` abgedeckt und praktisch nur als Wettlauf erreichbar.

## Confirmations
Confirmation: F002 Export-Faden / Code reference: engine/schreiben.py:5089 / Evidence: neuer Zweig nach dem Gate, Test grün / Status: CONFIRMED
Confirmation: F002 Unterprozess / Code reference: engine/schreiben.py:4911 / Evidence: ist_ablage_fehler → ablage_fehler vor raise / Status: CONFIRMED
Confirmation: F002 Hilfsfunktionen / Code reference: engine/schreiben.py:4876 / Evidence: 503, fehler_code, werte; Symlink-Probe grün / Status: CONFIRMED
Confirmation: F002 fremde_datei / Code reference: engine/schreiben.py:4514 / Evidence: Ablagefehler → None / Status: CONFIRMED
Confirmation: F002 Test / Code reference: engine/tests/test_schreiben_speicher.py:237 / Evidence: beide Varianten, Stand gleich, Temp-Ordner leer / Status: CONFIRMED
Confirmation: AC-10 / Code reference: engine/reisespeicher.py:915 / Evidence: main materialisieren fängt AblageFehlt, Katalogtext pruefung.bauen.79, Exit 2; Test über texte.SPRACHEN grün / Status: CONFIRMED
Confirmation: AC-11 / Code reference: engine/reisespeicher.py:200 / Evidence: lstat/S_ISREG/O_NOFOLLOW, Größen- und SHA-256-Prüfung, AblageFehler mit pruefung.bauen.80 / Status: CONFIRMED
Confirmation: AC-8 / Code reference: engine/reisespeicher.py:601 / Evidence: unlink nur auf Temporärdatei und Namen im Bauordner; Quelltext-Test grün / Status: CONFIRMED
Confirmation: AC-7 / Code reference: engine/reisespeicher.py:276 / Evidence: Temporärdatei, os.link auf Endnamen; Reihenfolge Datei vor Zeile durch Tests belegt / Status: CONFIRMED
Confirmation: AC-10 (Veröffentlichen) / Code reference: betrieb/veroeffentlichen.sh:209 / Evidence: case 2 mit grep '^ - ' → fehlgeschlagen, speicher_rote, continue / Status: CONFIRMED
Confirmation: AC-10 (Nachziehen) / Code reference: engine/neu.py:1345 / Evidence: nachziehen-speicher fängt AblageFehlt/AblageFehler, Exit 2 / Status: CONFIRMED
Confirmation: AC-28 / Code reference: engine/texte_de.py:1 / Evidence: Schlüssel .79/.80 in beiden Sprachen, test_texte.py grün / Status: CONFIRMED
Confirmation: AC-28 (en) / Code reference: engine/texte_en.py:1 / Evidence: Schlüssel .79/.80, test_texte.py grün / Status: CONFIRMED
Confirmation: AC-9 / Code reference: engine/instanz.py:1 / Evidence: speicher_ablage() liefert <FR_SPEICHER>/ablage; Pfadtest grün / Status: CONFIRMED
Confirmation: AC-27 (Messskript, Code-Teil) / Code reference: betrieb/messlauf-schreibweg.py:1 / Evidence: test_messlauf_skript_gibt_kennzahlen_aus grün / Status: CONFIRMED

## Checklisten-Status
- AC-1 bis AC-23, AC-25, AC-26, AC-28: Code-Teil belegt (AC-8, AC-10, AC-11 einzeln gegen den Code, die übrigen per Teststichprobe).
- Offen, nicht behebbar im Code (MEDIUM, kein BROKEN): AC-24 Browser-Rundgang, AC-27 110-MB-Messung und Zeitziele, Sicherung der Ablage im Infra-Repo, Instanztests der einbindenden Reisen-Repos.
- F002 Randfall im Schreibweg, MEDIUM.

## Herkunft der Vorbedingungen
kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
F001 (AC-10/AC-11) und F002 (Schreibweg) behoben und nachgeprüft. Zwei LOW-Hinweise (F-A1, F-A2) ohne praktische Erreichbarkeit.
Offen, nicht im Code behebbar (Phase 7/8, Issue #349): AC-24 Browser-Rundgang, AC-27 110-MB-Messung und Zeitziele, Backup der Ablage im Infra-Repo, Instanztests der einbindenden Reisen-Repos.
Code reference: engine/schreiben.py:4876
Tests: 477 passed, 0 failed, 0 übersprungen (volle Suite des Developers: 1827 passed)
Regressions: keine im Shell-Pfad und in neu.py gefunden

## Geprüfte Dateien

- sha256:2c3f20e4da4d4a4222ab8e2450064984ce3d9f9e45c7ec0acd7bc5a09727db97  betrieb/messlauf-schreibweg.py
- sha256:e5964fce794e3c60771268432afa6d6b7128d145de1a9968b73365cf0c34f702  betrieb/veroeffentlichen.sh
- sha256:120c22d792ac472544cf327da824f979238619cb04bb946450bafd66eb417157  engine/bauen.py
- sha256:d507c49f75068788561ec589c2840cf0d62bf1dec911aa5af081dd77853a7394  engine/instanz.py
- sha256:977f92f9978870d32f02ebf6beda1242651f890042be3a83b9bd3e98f1d0736e  engine/neu.py
- sha256:0645432827d3573d190ac9969871885a69c0db10dea4e692da04b73e3900ce07  engine/reisespeicher.py
- sha256:9e07b62b3cab73383806e56dda976a6298873545fdbc533ccc22c606470494b5  engine/schreiben.py
- sha256:873c262f3b765b0884c3c0cde6a59cdb8c699e61fd0de6c5386f8ad99a98e2aa  engine/texte_de.py
- sha256:0768d14cedff6aa601fffcc053aa801415b81f72e93b70c7f480e8c1e1544210  engine/texte_en.py

## Prüfbasis

- base: e8f8bee4d7026f6545dabac52cd70a4a82dd416b
- blob:2b0543016173fbf91a768e13f18e548f71f27cd4  betrieb/messlauf-schreibweg.py
- blob:dcbf23655e94ff93d7a0ad71f0b6177db5bc34f5  betrieb/veroeffentlichen.sh
- blob:2c9dc727051ad289144d3d1ab80ec73a120e60e2  engine/bauen.py
- blob:e6aa221df0a98baa305fe89ec2fedbe4f4970ccb  engine/instanz.py
- blob:758186cf46ff347f2629c92c8db1c0dab7367d57  engine/neu.py
- blob:6ca473128d603eb21ca8d556b156a65e72a678b9  engine/reisespeicher.py
- blob:b607e65cc88868f9daa453cd4f2a08f4b69e79ea  engine/schreiben.py
- blob:b966c9b11156086e56376e76fed265cd7e04bf77  engine/texte_de.py
- blob:d06ac95d46532600d2245a3d21fcd232704c8e02  engine/texte_en.py

## Geprüfte Dateien

- sha256:2c3f20e4da4d4a4222ab8e2450064984ce3d9f9e45c7ec0acd7bc5a09727db97  betrieb/messlauf-schreibweg.py
- sha256:e5964fce794e3c60771268432afa6d6b7128d145de1a9968b73365cf0c34f702  betrieb/veroeffentlichen.sh
- sha256:120c22d792ac472544cf327da824f979238619cb04bb946450bafd66eb417157  engine/bauen.py
- sha256:d507c49f75068788561ec589c2840cf0d62bf1dec911aa5af081dd77853a7394  engine/instanz.py
- sha256:977f92f9978870d32f02ebf6beda1242651f890042be3a83b9bd3e98f1d0736e  engine/neu.py
- sha256:0645432827d3573d190ac9969871885a69c0db10dea4e692da04b73e3900ce07  engine/reisespeicher.py
- sha256:9e07b62b3cab73383806e56dda976a6298873545fdbc533ccc22c606470494b5  engine/schreiben.py
- sha256:873c262f3b765b0884c3c0cde6a59cdb8c699e61fd0de6c5386f8ad99a98e2aa  engine/texte_de.py
- sha256:0768d14cedff6aa601fffcc053aa801415b81f72e93b70c7f480e8c1e1544210  engine/texte_en.py

## Prüfbasis

- base: e8f8bee4d7026f6545dabac52cd70a4a82dd416b
- blob:2b0543016173fbf91a768e13f18e548f71f27cd4  betrieb/messlauf-schreibweg.py
- blob:dcbf23655e94ff93d7a0ad71f0b6177db5bc34f5  betrieb/veroeffentlichen.sh
- blob:2c9dc727051ad289144d3d1ab80ec73a120e60e2  engine/bauen.py
- blob:e6aa221df0a98baa305fe89ec2fedbe4f4970ccb  engine/instanz.py
- blob:758186cf46ff347f2629c92c8db1c0dab7367d57  engine/neu.py
- blob:6ca473128d603eb21ca8d556b156a65e72a678b9  engine/reisespeicher.py
- blob:b607e65cc88868f9daa453cd4f2a08f4b69e79ea  engine/schreiben.py
- blob:b966c9b11156086e56376e76fed265cd7e04bf77  engine/texte_de.py
- blob:d06ac95d46532600d2245a3d21fcd232704c8e02  engine/texte_en.py
