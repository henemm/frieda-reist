# Adversary Dialog — feature-12-profile
Spec: docs/specs/konnektor/profile-12.md
Datum: 2026-11-15 09:28

## Checkliste
- [x] **AC-1:** Given ein Konto / When ein gültiger Eintrag mit Herkunft gesetzt wird / Then erscheint er als `PR-<n>` mit Datum von Frieda, Nummern werden nie wiederverwendet, Längen und Anzahl sind begrenzt, und eine ältere Datenbank bekommt die Tabelle ohne Datenverlust (Test 1, 2, 3, 7).
- [x] **AC-2:** Given `profile_entry_set` / When `confirmed=true` oder `herkunft` fehlt / Then wird abgelehnt und nichts gespeichert (Test 9, 12).
- [x] **AC-3:** Given die Schreibgrenze je Konto ist erreicht / When gesetzt oder entfernt wird / Then wird Setzen abgelehnt, Entfernen funktioniert trotzdem und zählt nicht (Test 10).
- [x] **AC-4:** Given der Konnektor eines Kontos / When die Werkzeugliste abgefragt wird / Then gibt es `my_profile` (Alias `mein_profil`), `profile_entry_set` und `profile_entry_remove` als Konto-Werkzeuge ohne `reise`, mit deutschen Aliasen für Werkzeug- und Parameternamen und Beschreibungen in beiden Sprachen (Test 8, 11).
- [x] **AC-5:** Given ein Konto / When `anleitung_frieda` erzeugt wird / Then verlangt sie, nur Bestätigtes einzutragen, und nennt Bereiche höchstens als Beispiele (Test 13).
- [x] **AC-6:** Given eine Reise mit Baustein `profile` an, aus oder ohne `bausteine` / When ihre Anleitung erzeugt wird / Then heißt es bei an oder ohne `bausteine`: Profil nutzen und bei Wahlstellen als Grund nennen, bei aus: nicht nutzen; `NOCH_NICHT_GEBAUT` ist leer (Test 14, 15).
- [x] **AC-7:** Given Ida mit Profileinträgen / When sie Mein Konto öffnet, einen Text ändert oder einen Eintrag löscht / Then zeigt die Karte „Mein Profil“ nur ihre eigenen Einträge, Ändern und Löschen wirken nur mit `WHERE konto=?`, fremde Kennungen ändern nichts, Neuanlegen ist dort nicht möglich (Test 16, 17, 18, 19).
- [x] **AC-8:** Given ein Konto mit Profil / When es gelöscht oder mit einem anderen zusammengeführt wird / Then ist das Profil beim Löschen mit weg und hängt beim Zusammenführen ohne Kollision am bleibenden Konto (Test 5, 6).
- [x] **AC-9:** Given Ida und Karl mit Profilen / When Ida ihre Daten exportiert / Then enthält `person.json` Idas Profil und nie das von Karl (Test 22).
- [x] **AC-10:** Given Ida, Karl, Tom, Lea und Organisator:innen / When jemand Werkzeuge, Seiten oder Reisedaten abruft / Then sieht niemand außer der Person selbst ihr Profil (Test 20).
- [x] **AC-11:** Given ein Profileintrag / When er gesetzt, geändert, gelöscht oder exportiert wird / Then taucht sein Text nie in Logs, Meldungen, Push, Mails oder der Betreiber-Meldung auf (Test 21).
- [x] **AC-12:** Given die Datenschutzseite / When sie auf Deutsch oder Englisch aufgerufen wird / Then enthält sie den Art.-9-Absatz mit ausdrücklicher Einwilligung durch Bestätigung und das Profil in der Liste der Kontolöschung (Test 23).
- [x] **AC-13:** Given die fertige Änderung / When die Tests laufen / Then stehen alle sichtbaren Texte in beiden Sprachkatalogen, Ausnahmelisten sind nicht länger, `deploy.sh` ist unverändert, `docs/konnektor.md`, `docs/produkt.md` und die Verlaufszeile in ADR-0001 sind nachgezogen (Test 24, 25, 26).
- [x] **AC-14:** Given die Spec / When sie freigegeben wird / Then sind Karte „Mein Profil“ und Datenschutzabsatz dem Product Owner vorher als Artefakt-Entwurf gezeigt worden (#436); manuelles Prozess-Kriterium, kein automatisierter Test.

## Dialog
### Runde 1
**Adversary:** Alle 14 ACs gegen Code und Tests geprüft, zuerst die Spec, dann die geänderten Dateien. Prüfläufe in adversary-test-output.txt: 16 Suiten (test_profil, test_export, test_betreiber_meldung, test_regeln, test_texte, test_rechtliches, test_englisch_schnittstelle, test_grenzen, test_bauen, test_oauth, test_loeschen_konto, test_betrieb, test_konten, test_anmeldung, test_trennung, test_protokolle_ohne_pfade) mit -n 3. Lauf 1: 703 passed, 1 failed (test_anmeldung::test_pruefungen_buendeln_je_reise_und_tag, erwartet "2 details to check", bekam "2 Angaben zu prüfen"). Einzellauf dieses Tests: passed; zusammen mit test_profil einzeln und mit -n 3: 60 passed; Lauf 2 derselben 16 Suiten: 704 passed, 0 failed. Der Test liest texte.VORGABE gegen eine Sprache, die vom Lauf abhängt, und berührt den Profilcode nicht (F004).

Eigentumsprüfung: Mit einer temporären Sonde (Konnektor-Pfad aufruf_intern plus frieda_werkzeug, danach wieder entfernt) greift Karl auf Idas PR-1 zu mit den ids PR-1, pr-1, 1, PR-01, Leerzeichen davor oder danach, PR--1, PR-0, PR-99999999999999999999, PR- plus Ziffer 1 in Vollbreite, PR-1 plus Zeilenumbruch, jeweils für profil_eintrag_entfernen und profil_eintrag_setzen mit id. Ergebnis: überall "Eintrag … nicht gefunden", Idas Eintrag unverändert (Assertion). Eine leere oder fehlende id bei Setzen legt laut Spec einen NEUEN eigenen Eintrag an (PR-2, PR-3 für Karl), bei Entfernen "nicht gefunden". PR-0n trifft nur eigene Einträge, weil _profil_zeile immer WHERE id = ? AND konto = ? nutzt. Der Fehlertext enthält nur die eingegebene Kennung und verrät nichts über fremde Konten.
Code reference: engine/konten.py:737
Code reference: engine/konten.py:712
Code reference: engine/konten.py:750
Code reference: engine/konten.py:780

Bestätigung: Aufruf über den englischen Namen profile_entry_set mit area, origin, confirmed. Nur der JSON-Wert true wird akzeptiert; der String "true" oder "True", die Zahl 1, "yes", null, false, eine Liste und ein fehlendes Feld werden abgelehnt, nichts gespeichert (danach genau 1 Eintrag). Die Wahl ist streng (is not True) und für ein Einwilligungs-Flag nach Art. 9 richtig; sie sollte in docs/konnektor.md stehen (F006). Das Schema deklariert boolean, also schicken Clients ein JSON-Boolean.
Code reference: engine/konnektor.py:2455
Code reference: engine/schnittstelle.py:131
Parameter-Aliase: area, origin, confirmed stehen ausschließlich in PARAMETER_JE_WERKZEUG für profil_eintrag_setzen und nicht in der globalen PARAMETER-Tabelle; kein anderes Werkzeug nutzt sie, es gibt keine Kollision (Sonde).

Schreibgrenze: Ein Setzen mit ungültigem Inhalt (leerer Bereich) hinterlässt 1 Eintrag in schreibvorgaenge, weil schreiben_vormerken vor der Validierung läuft; nicht Bestätigtes zählt nicht (F001, LOW). Entfernen ruft die Grenze nie auf (Code und Test 10).
Code reference: engine/konnektor.py:2461

Mein Konto (HTTP, echter Dienst im Testaufbau, Sonde): Profiltext, Bereich und Herkunft mit script- und img-Markup erscheinen in /konto nicht roh (weder das script-Tag noch das img-Tag), Escaping über esc in profil_karte. POSTs mit unbekannter, leerer oder fehlender id, leerem Text, 600 Zeichen Text und fremder Sitzung (Karl löscht PR-1) liefern 200 ohne Traceback und ändern nichts. POST mit Origin null oder einer fremden Adresse sowie ohne Origin: 403; ohne Sitzung: 303. GET mit denselben Parametern ändert nichts (Test 18). Kein Formular zum Neuanlegen (Test 19). Profiltexte in stderr: Der einzige neue stderr-Schreiber gibt nur Kontokennung und das Wort schreiben aus, ohne Inhalt; log_message des Konnektors protokolliert nur Methode und Pfad.
Code reference: engine/anmeldung.py:1042
Code reference: engine/anmeldung.py:1590

Datenschutz und Wortlaut: recht.datenschutz.konto_loeschen enthält "dein Profil,"; konto.profil.titel "Mein Profil"; konto.profil.erklaerung und der Absatz recht.datenschutz.profil ("Dein Profil …", Art. 9, ausdrückliche Einwilligung) stehen in de und en. Der Kommentar in Issue #12 (OWNER, 15.11.2026) bestätigt die Freigabe unverändert. Den Artefakt-Entwurf selbst konnte ich nicht Zeichen für Zeichen vergleichen; geprüft ist nur, dass die im Auftrag genannten Wortlaute exakt vorkommen.
Code reference: engine/texte_de.py:3736
Code reference: engine/texte_en.py:3734
Code reference: engine/texte_de.py:3729
Code reference: engine/texte_en.py:3727

Weitere Prüfpunkte: Migration (CREATE TABLE IF NOT EXISTS, Test 7 grün), Zusammenführen (UPDATE profil SET konto, keine Obergrenze, Test 6 grün), Löschen (Tabellenliste, Test 5), Export (profil_liste nur für die eigene Kennung, Test 22), Vorgaben aus der Instanz, NOCH_NICHT_GEBAUT leer.
Code reference: engine/konten.py:665
Code reference: engine/anmeldung.py:954
Code reference: engine/instanz.py:258
Code reference: engine/reise.py:41

**Implementierer:** Kein Rückfragekanal; der Adversary hat die Gegenbelege selbst durch Tests und Code-Lesen erhoben. Nach Test-Output und Code sind AC-1 bis AC-13 belegt; F001 bis F004 und F006 sind kein Blocker, F005 ist ein Hinweis.

### Runde 2
**Adversary:** Zweite Runde gegen die Frühkonvergenz, gezielt gegen die Schwachstellen:
1. Profil im Export anderer Personen und in Reiseordnern: export_person ruft profil_liste nur mit der Kennung der Exportierenden; Test 21 und 22 prüfen die Suchmarke in allen Reiseordnern des ZIP, in Mails, Push und Betreiber-Meldung. Ergebnis: nicht gefunden (Tests grün).
2. Zusammenführen mit Obergrenze: das UPDATE ist unbedingt, die Obergrenze wird nur in profil_setzen beim Neuanlegen geprüft; das bleibende Konto kann über der Grenze liegen, weiteres Neuanlegen wird dann abgelehnt, Ändern und Löschen funktionieren. Entspricht der Spec (nichts geht verloren).
3. Gleichzeitigkeit: Anzahlprüfung und INSERT laufen in einer Transaktion, die sqlite3 erst mit dem INSERT öffnet; zwei gleichzeitige Neuanlagen können die Obergrenze um eins überschreiten (F003, LOW; nur das eigene Konto betroffen).
4. Alte Datenbank: Test 7 legt die Tabelle an, vorhandene Daten bleiben.
5. Nummern: AUTOINCREMENT in CREATE TABLE profil; Test 2 belegt PR-3 nach Löschen von PR-2.
6. Anleitung je Reise: anleitung() ergänzt profil_nutzen (bausteine None oder profile an) oder profil_nicht_nutzen. Der Satz nennt mein_profil, das Werkzeug gibt es aber nur im Konto-Konnektor; im reisebezogenen Zugang ohne konto_id fehlt es (F002, LOW). Die englische Ausgabe über namen_im_text nennt korrekt my_profile und profile_entry_set (Sonde).
7. test_profil.py wurde nach dem roten Test-Stand um zwei Zeilen geändert (Test 14 entfernt für "ohne bausteine" das Feld ganz, weil die Beispielreisen eine Liste tragen). Das ist sachlich richtig, schwächt keine Erwartung ab, wird aber festgehalten (F005).
Code reference: engine/konnektor.py:3107
Code reference: engine/konten.py:761

**Implementierer:** Keine Gegenargumente zu den LOW-Punkten; kein Befund bricht ein AC.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Structured Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:2461
  Description: schreiben_vormerken läuft vor profil_setzen; ein abgelehnter Eintrag (leerer Bereich, zu lang, Profil voll, fremde id) zählt zur Schreibgrenze (Sonde: 1 Vorgang nach einem Fehlversuch).
  Spec requirement: AC-3 — Setzen zählt zur Schreibgrenze.
  Conflict: Spec lässt offen, ob abgelehnte Versuche zählen; kein Verstoß, nur großzügiger als nötig.
  Remediation: Vormerken erst nach erfolgreichem profil_setzen oder so belassen und dokumentieren.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:3107
  Description: anleitung() nennt mein_profil auch für den reisebezogenen Zugang ohne konto_id, in dem es dieses Werkzeug nicht gibt.
  Spec requirement: AC-6 — Anleitung je Reise nennt Profil nutzen und als Grund nennen.
  Conflict: Hinweis auf ein Werkzeug, das im alten reisebezogenen Zugang fehlt.
  Remediation: Satz nur anhängen, wenn zugang konto_id enthält, oder ohne Werkzeugnamen formulieren.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/konten.py:761
  Description: Anzahl-Zählung und INSERT ohne exklusive Sperre; zwei parallele Neuanlagen desselben Kontos können die Obergrenze um eins überschreiten.
  Spec requirement: AC-1 — Anzahl ist begrenzt.
  Conflict: Obergrenze nicht streng atomar.
  Remediation: BEGIN IMMEDIATE vor dem COUNT oder bewusst hinnehmen (nur das eigene Konto betroffen).

Finding:
  ID: F004
  Severity: LOW
  Category: regression
  Code reference: engine/anmeldung.py:1590
  Description: Im ersten Lauf (-n 3) fiel test_anmeldung::test_pruefungen_buendeln_je_reise_und_tag aus (Meldung de statt texte.VORGABE en); allein, zusammen mit test_profil und im zweiten Lauf (704 passed) grün. Der Test hängt von der Reihenfolge ab und berührt den Profilcode nicht.
  Spec requirement: AC-13 — Tests grün.
  Conflict: instabiler bestehender Test; Ursache nicht in den Änderungen.
  Remediation: Test von texte.VORGABE lösen (Sprache des Kontos erwarten); eigenes Issue.

Finding:
  ID: F005
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/reise.py:41
  Description: Nach dem roten Test-Stand wurden test_profil.py (2 Zeilen), test_export.py, test_betreiber_meldung.py und test_regeln.py (Längengrenze Anleitung 4600 auf 4700) angepasst.
  Spec requirement: AC-13 — benannte Anpassungen bestehender Tests.
  Conflict: Keine Abschwächung festgestellt; die Anhebung ist durch die neuen Sätze gedeckt.
  Remediation: In der PR-Beschreibung nennen.

Finding:
  ID: F006
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/schnittstelle.py:131
  Description: Nur JSON-true bestätigt, der String "true" wird abgelehnt; die Wahl ist nicht dokumentiert.
  Spec requirement: AC-2 — confirmed=true nötig.
  Conflict: Kein Verstoß, Doku-Lücke.
  Remediation: Satz in docs/konnektor.md.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/konten.py:750
  Evidence: PR-n, datum von Frieda, AUTOINCREMENT, Längen und Anzahl aus instanz.py, CREATE TABLE IF NOT EXISTS; Test 1, 2, 3, 7 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/konnektor.py:2455
  Evidence: bestaetigt is not True lehnt ab; leere herkunft wirft profil_leer; Sonde mit 8 Varianten.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/konnektor.py:2457
  Evidence: schreibgrenze vor Setzen; Entfernen ohne Grenzprüfung; Test 10 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/konnektor.py:2281
  Evidence: drei Konto-Werkzeuge ohne reise, Namen und Alias in schnittstelle.py, Beschreibungen in de und en; Test 8, 11 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/konnektor.py:2319
  Evidence: anleitung_frieda hängt frieda.profil an; Bereiche nur als "etwa"; Test 13 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/konnektor.py:3107
  Evidence: profil_nutzen bei None oder profile an, sonst profil_nicht_nutzen; NOCH_NICHT_GEBAUT leer (reise.py:41); Test 14, 15 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/anmeldung.py:1590
  Evidence: POST-Zweige hinter Origin- und Sitzungsprüfung, WHERE konto = ?, Escaping, kein Neuanlegen; Sonde und Test 16 bis 19.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/konten.py:665
  Evidence: profil in der Löschliste; UPDATE profil SET konto beim Zusammenführen; Test 5, 6 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/anmeldung.py:954
  Evidence: person.json enthält profil_liste nur der eigenen Kennung; Test 22 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/konten.py:737
  Evidence: jede Profilabfrage filtert WHERE konto = ?; kein Profil in Reisewerkzeugen, Reisedaten oder Service Worker; Test 20 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/konnektor.py:2439
  Evidence: profil_werkzeug schreibt nur Kontokennung und das Wort schreiben nach stderr; Test 21 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/texte_de.py:3736
  Evidence: Absatz recht.datenschutz.profil in de und en, konto_loeschen nennt das Profil; Test 23 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/texte_en.py:3734
  Evidence: Schlüssel in beiden Katalogen, test_texte und test_rechtliches grün, deploy.sh unverändert, Doku und ADR-Zeile vorhanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/texte_de.py:3729
  Evidence: Kommentare in Issue #12 (OWNER, 15.11.2026) bestätigen die Freigabe unverändert; die genannten Wortlaute stehen exakt in texte_de.py.
  Status: CONFIRMED

## Verdict
VERIFIED

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 704 passed im zweiten Lauf (Lauf 1: 703 passed, 1 instabiler Fehlschlag ohne Bezug zum Profil, F004), 0 übersprungen
Edge cases: alle geprüft, kein Befund bricht ein AC (F001 bis F006 LOW)
Regressions: keine im Profilcode
Checklist: 14/14 points proven

## Geprüfte Dateien

- sha256:7504bd7adcd9771c415340563d560bafdb4f1b75cd727ae4312ce5f0e208c0a7  engine/anmeldung.py
- sha256:90e6d4d82c70fbc260077757c991f85f5fd06834194be71f9d4c7d1dbf75fe7a  engine/instanz.py
- sha256:5af84f2d29363fd60bae37a39f498437037fc597fb7b45c213d9a660c077c6b0  engine/konnektor.py
- sha256:4babca9144116d60af71a82b0fa80aa1ec23f0ec7225cb6a9d59e5e7091d38ac  engine/konten.py
- sha256:c04dadba72e6883cf9cb942dadb072d4de949a40e859534f8dd683680686cfd7  engine/reise.py
- sha256:7206a49ed4e149a64cdd45e4a0be2cc917bf01b6e348b5133a8d4bc4272066e3  engine/schnittstelle.py
- sha256:41579e315b1c98c42a28322176240a9e58cfecdce8d60a4557c3657ae0f3a07c  engine/texte_de.py
- sha256:2f9c688e477a66f4e74c2d718c3f399eb7669970e2e58aafd602ca04cfa4765c  engine/texte_en.py

## Prüfbasis

- base: 42b6017f3ff3820c624608387a2890348c574406
- blob:56a1b1a173b947b31649538d18e6bd7eb940da1b  engine/anmeldung.py
- blob:cdb07e3e670f961635932ed87ce3c2b946960753  engine/instanz.py
- blob:cdd51c3e8893193d229a0968b122facf4ab81d85  engine/konnektor.py
- blob:24238cab4baae052c3bd9dab231c54da22c13d63  engine/konten.py
- blob:38be1279aa30fff17290618314dfb98e691a5e5a  engine/reise.py
- blob:63f6ff82fc31d9d9bc541b720b63ae83b5f619e3  engine/schnittstelle.py
- blob:cfbb2ac54977cc711b50b8bac1e31b851f8db31e  engine/texte_de.py
- blob:81399833613bfe04cb920ddd131a84e428ed200a  engine/texte_en.py
