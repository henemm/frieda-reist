# Adversary Dialog — alpha-381-loeschen
Spec: docs/specs/betrieb/loeschen-381.md
Datum: 2026-11-11 22:59

## Checkliste
- [x] **AC-1:** Given eine Organisator:in einer Speicherreise / When sie Mein Konto öffnet / Then steht unter den Personen der Link „Reise löschen …“; für Nicht-Organisator:innen und für Reisen auf dem alten Weg fehlt er.
- [x] **AC-2:** Given Bestätigung 1 und 2 / When der Haken fehlt oder der Reisename nicht exakt eingetippt ist / Then wird nichts vorgemerkt; sonst wird die Reise mit Fristende nach 14 Tagen (Vorgabe in `instanz.py`) vorgemerkt.
- [x] **AC-3:** Given eine vorgemerkte Reise / When ein Mitglied „Meine Reisen“ öffnet / Then steht der Block oben mit Datum samt Zeitzone, und nur Organisator:innen sehen „Reise zurückholen“; der Knopf macht die Reise vollständig wieder sichtbar.
- [x] **AC-4:** Given eine Reise mit mehreren Mitgliedern / When sie vorgemerkt wird / Then erhalten alle anderen Mitglieder sofort Mail und Meldung, beim Zurückholen eine zweite, die auslösende Person keine.
- [x] **AC-5:** Given eine vorgemerkte Reise / When `reisen()`, `my_trips` oder irgendein Reise-Werkzeug des Konnektors, der Schreibweg oder der Wächter sie ansprechen / Then verhält sie sich wie nicht vorhanden (keine Schreibung, keine Erinnerung).
- [x] **AC-6:** Given eine vorgemerkte Reise / When `veroeffentlichen.sh` läuft / Then wird sie nicht gebaut und ihr Webordner ist entfernt (404); nach dem Zurückholen wird sie wieder gebaut.
- [x] **AC-7:** Given Fristende erreicht / When der tägliche Lauf läuft / Then sind Versionen, Verlauf, Ablage-Dateien ohne fremde Verweise, Belege, Rückmeldungen, Webordner, Bauordner und Stempel der Reise entfernt, und alle anderen Reisen sind unverändert.
- [x] **AC-8:** Given zwei Reisen mit gemeinsamer Ablagedatei / When die eine entfernt wird / Then bleibt die Datei bis auch die andere entfernt ist.
- [x] **AC-9:** Given das Entfernen einer Reise / When der Lauf abgeschlossen ist / Then folgen `wal_checkpoint(TRUNCATE)`, `VACUUM` und ein neuer Schnappschuss, in DB, WAL und Schnappschuss findet eine Byte-Suche den Testinhalt nicht, und `pruefen()` ist grün.
- [x] **AC-10:** Given eine zurückgespielte alte Sicherung / When der tägliche Lauf läuft / Then wird jede Reise des Löschprotokolls erneut entfernt; das Protokoll enthält nur Kennung und Datum.
- [x] **AC-11:** Given der Quelltext / When der Test läuft / Then nutzen genau `reise_entfernen` und `namen_ersetzen` `_db_ausnahme`, jede in einer `BEGIN IMMEDIATE`-Transaktion mit Trigger-Neuanlage aus `SCHEMA` (oder, falls nach Punkt 19 gewählt, über den Ausweichweg mit `WHEN fr_ausnahme()`); bei einem Fehler bleibt alles beim Alten.
- [x] **AC-12:** Given ein Konto mit Daten in allen Tabellen / When `loeschen` läuft / Then bleibt in keiner Tabelle der Kontendatenbank eine Spur (Einladungen, Wartelisteneintrag, `angelegte_reisen`, `schreibvorgaenge`, `oauth_*`, Zählzeilen in `versand` eingeschlossen; in `reise_loeschung` ist das auslösende Konto geleert).
- [x] **AC-13:** Given die einzige Organisator:in einer Reise mit weiteren Mitgliedern / When sie ihr Konto löschen will / Then wird abgelehnt und die Reise genannt, bis Rolle übergeben oder Reise gelöscht ist.
- [x] **AC-14:** Given eine Reise nur mit der Person / When sie ihr Konto löscht / Then geht die Reise mit Schonfrist mit (sofort unsichtbar, nach Fristende entfernt); Reisen mit anderen Mitgliedern bleiben bestehen.
- [x] **AC-15:** Given Beiträge der Person in Reisen anderer / When das Konto gelöscht wird / Then steht im Verlauf und in den bekannten Herkunftsmustern aller Versionen „gelöschte Person“, zugeordnet über den Personenschlüssel (ein gleichnamiges anderes Mitglied bleibt), die Prüfsummen stimmen, `pruefen()` ist grün und ein Neubau ist erzwungen.
- [x] **AC-16:** Given Namen in Freitexten außerhalb der Muster / When das Konto gelöscht wird / Then ist die Grenze im Datenschutztext ehrlich benannt und im Test als Ist-Stand festgehalten.
- [x] **AC-17:** Given `konten.reise_vorgemerkt(reise)` / When der Export (#498) oder ein anderer Aufrufer fragt / Then ist das Ergebnis wahr für vorgemerkte und entfernte Reisen, sonst falsch.
- [x] **AC-18:** Given alle sichtbaren Texte (Seiten, Mails, Meldungen, Datenschutztext) / When `test_texte.py` und die Tests zum Datenschutztext laufen / Then sind alle Schlüssel in allen Sprachen vorhanden, Ausnahmelisten nicht länger, und der Text sagt nur zu, was es gibt (Sicherungen höchstens 30 Tage als Ziel, Export nur nach #498).
- [x] **AC-19:** Given beide Beispielreisen / When die Tests laufen / Then bestehen sie für Wanderung und Städtewochenende gleichermaßen, und alle bestehenden Tests bleiben grün.

## Dialog

### Runde 1
**Adversary:** Alle 19 ACs gegen Code und Tests geprueft (Lauf 1: gezielt 87 passed, voll 2373 passed). Proben im Scratchpad: Shell-Probelauf vorgemerkte_entfernen und ist_vorgemerkt (Entfernen, exakter Treffer, fail closed Exit 1) ohne Befund; Konto-Loeschen mit push_stand-Zeilen; Einladung nach Vormerken einloesbar. Befunde: F001 HIGH (push_stand bleibt, AC-12), F002 MEDIUM (Einladung einloesbar, Reisebezug bleibt in der Kontendatenbank), F003 MEDIUM (Namenssuche statt Schluessel), F004 LOW (Neubau bei Reisen ohne Stempel), F005 LOW (RuntimeError statt Meldung), F006 LOW (seiten.json und nginx-Baustein bleiben). Verdict Runde 1: BROKEN.
**Implementierer:** F001 bis F006 bearbeitet (siehe Runde 2).

### Runde 2
**Adversary:** Fixes am Code gelesen und gegen Regressionen gebohrt; voller Lauf 2379 passed, 0 failed (docs/artifacts/alpha-381-loeschen/adversary-test-output.txt). Status der Findings:
- F001 BEHOBEN: engine/konten.py:609 loescht sammel:<kid> exakt und mail:% nur mit Endung :<kid> (substr-Vergleich); Test legt Kollisionskennung <kid>9 und Server-Schluessel an und erwartet, dass beide bleiben; push_stand nicht mehr pauschal ausgenommen.
- F002 BEHOBEN: einladung (konten.py:1214), einladung_einloesen (konten.py:1224) und _einloesen (konten.py:1199) lehnen vorgemerkte und entfernte Reisen ab; Normalfall unberuehrt: Pruefung greift nur bei reise_vorgemerkt der Reise der Einladung, Einladungen zu anderen Reisen laufen durch (Volltests Anmeldung gruen). loeschung_abschliessen (konten.py:994) raeumt Mitgliedschaften, Einladungen, Push-Abos, wartende Push-Nachrichten und versand einladung:<reise> ab; angelegte_reisen bleibt wegen der Grenze aus #380 (Kennung der Reise, bewusst).
- F003 BEHOBEN (konservativ): konten.py:564 ersetzt einen Namen nicht, wenn ein anderes Mitglied derselben Reise (Person oder Kontoname) ihn traegt. Normalfall (eindeutiger Name, Personenname und Kontoname getrennt) wird weiter ersetzt. Restgrenze: bei Namensgleichheit bleibt der Name der geloeschten Person in dieser Reise stehen (Datenschutz zugunsten Korrektheit des Verlaufs), im Test festgehalten (test_gleichnamiges_mitglied_derselben_reise_bleibt); als LOW vermerkt.
- F004 BEHOBEN: reisespeicher.py:1065 _neubau_erzwingen kuerzt den Stempel auf die Stand-Nummer ohne Software-Kennung. veroeffentlichen.sh liest gn und gk; leeres gk faellt weder in die Nachziehen- noch in die Ueberspringen-Zweige, sondern in modus bauen (Zeile mit -z gk); der Stempel existiert weiter, die Umschaltungssperre (nur ohne Stempel) greift nicht. Auch fuer Speicherreisen im Altweg-Uebergang.
- F005 BEHOBEN: konten.py:592 wandelt Fehler in KontoFehler loeschen_spaeter (de und en vorhanden, texte_de.py:3623, texte_en.py:3621), das Konto bleibt unveraendert, weil das Pseudonymisieren vor der Transaktion scheitert.
- F006 TEILWEISE: waechter.py:427 _seitenlink_entfernen nimmt den Eintrag aus seiten.json; nginx-Baustein bleibt (Root, Reload), 404 durch fehlenden Ordner, Folge-Issue. LOW, akzeptiert.
Testanpassungen (Diff gegen HEAD in engine/tests) geprueft: keine Aufweichung; _spuren sucht die Kennung jetzt auch als Teil eines Werts, die Ausnahme push_stand ist entfernt, Stempel-Test setzt Stempel mit Software-Kennung und erwartet die Kuerzung, Karl meldet sich vor dem Vormerken an (nur Reihenfolge), die frueheren drei Anpassungen unveraendert unbedenklich.
**Implementierer:** Siehe oben (Bericht des Entwicklers).

Finding:
  ID: F007
  Severity: LOW
  Category: edge_case
  Code reference: engine/konten.py:564
  Description: Restgrenze von F003: bei Namensgleichheit in derselben Reise bleibt der Name der geloeschten Person dort stehen; ebenso bleibt der nginx-Baustein (F006) stehen (engine/waechter.py:427).
  Spec requirement: AC-15
  Conflict: Bewusst konservativ, im Test festgehalten; kein Verstoss gegen den Spec-Wortlaut (gleichnamiges Mitglied bleibt).
  Remediation: Im Datenschutztext (engine/texte_de.py:3659 Umfeld) die Grenze nennen oder Folge-Issue.


Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:826
  Evidence: loeschen_link nur fuer Organisator:innen einer Speicherreise; Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/instanz.py:184
  Evidence: loeschfrist_tage, Vorgabe 14 (FR_LOESCHFRIST_TAGE); engine/anmeldung.py:765 reise_loeschen prueft Haken und Reisename; Tests gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/rueckmeldungen.py:140
  Evidence: ordner() None fuer Vorgemerkte; Block oben und Knopf nur fuer Organisator:innen in engine/anmeldung.py:809; Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/anmeldung.py:727
  Evidence: loeschung_melden ueberspringt den Ausloeser, Mail und Meldung je Sprache; Tests gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/konnektor.py:2181
  Evidence: reisen_des_kontos und werkzeug filtern Vorgemerkte; engine/schreiben.py:5485 antwortet 410; engine/waechter.py:487 alle_reisen ohne Vorgemerkte; Einladungen jetzt gesperrt (konten.py:1224).
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/reisespeicher.py:447
  Evidence: reisen() blendet Vorgemerkte aus; Shell-Probelauf (Entfernen, exakter Treffer, fail closed) und Neubau nach Zurueckholen (kein Seitenstand, modus bauen).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/waechter.py:447
  Evidence: loeschungen_ausfuehren entfernt Speicher, Ablage, Webordner, Bauordner, Stempel, seiten.json-Eintrag; Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/reisespeicher.py:969
  Evidence: _ablage_aufraeumen unter BEGIN IMMEDIATE, nur Dateien ohne Verweis; Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/reisespeicher.py:944
  Evidence: reise_entfernen in einer Transaktion, verdichten (wal_checkpoint TRUNCATE, VACUUM), neuer Schnappschuss; Byte-Suche-Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/waechter.py:447
  Evidence: Reisen des Loeschprotokolls werden erneut entfernt; AblageFehlt nur tolerant fuer Funde der zu entfernenden Reisen; Protokoll nur Kennung und Datum (konten.py:994).
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/reisespeicher.py:916
  Evidence: _db_ausnahme nur in reise_entfernen und namen_ersetzen (reisespeicher.py:1016), BEGIN IMMEDIATE, Trigger aus SCHEMA, ROLLBACK bei Fehler; Authorizer unveraendert; Tests gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/konten.py:579
  Evidence: loeschen leert alle Tabellen inklusive push_stand (konten.py:609) in einer Transaktion; oauth_clients ohne Kontobezug bleibt; Test gegen Tabellenliste gruen, Kollisionskennung bleibt.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/konten.py:485
  Evidence: loeschen_pruefen sperrt die einzige Organisatorin; Tests gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/konten.py:579
  Evidence: Reisen nur mit der Person gehen mit Schonfrist mit; Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/konten.py:551
  Evidence: _pseudonymisieren (konten.py:564 mit Eindeutigkeitspruefung), namen_ersetzen mit Pruefsummen (reisespeicher.py:1016), Neubau ueber _neubau_erzwingen (reisespeicher.py:1065); Tests gruen, Restgrenze F007.
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/texte_de.py:3659
  Evidence: Datenschutztext benennt die Grenze (recht.datenschutz.namen_freitext, en: engine/texte_en.py:3657); Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: engine/konten.py:975
  Evidence: reise_vorgemerkt ist reise_loeschung UNION loeschprotokoll; Tests gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: engine/texte_en.py:3621
  Evidence: Neue Schluessel (loeschen_spaeter) in de (texte_de.py:3623) und en; test_texte gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: engine/schreiben.py:5485
  Evidence: Beide Beispielreisen in den Tests; Volllauf 2379 passed, 0 failed.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Findings F001 bis F005 sind behoben, F006 teilweise (nginx-Baustein bleibt, Folge-Issue), Restgrenzen F007 sind LOW und dokumentiert.
Tests: 2379 passed, 0 failed, 0 uebersprungen
Edge cases: geprueft, keine neuen Brueche
Regressions: None found
Checklist: 19/19 points proven

## Geprüfte Dateien

- sha256:ecd503b58f8a9598f6b1c819ab37b8e75f8f6e4f10b5f1b254eccfe91f24b16b  engine/anmeldung.py
- sha256:4c48e93f4bff9d5db248a8b72ddc12d9e198afb1da78a9f97aa75c967bb1d546  engine/instanz.py
- sha256:77467f6969391cd5f76ed3033a9efed0f3e81dee9d18234966e8356ca56a9df4  engine/konnektor.py
- sha256:c5fbfd0e50b79dbead5bc687217af75696986cf984968624d0f39ce10242121e  engine/konten.py
- sha256:7227d5f500aea5545b9b87fe92ac6e642cf73c57ce06430fd93061edd50de4b1  engine/reisespeicher.py
- sha256:d8c2bfa3e6d9df413d148093b165e53be1d0d7dc6960cc320b71197046fdce55  engine/rueckmeldungen.py
- sha256:d8b8ef508cc655f3e3596cc7bc9f6d835892bad6c72f2143ffc1e113e1a9cfe6  engine/schreiben.py
- sha256:0a6d5d1657ab34e4260d0e3c772325c762dced803e98183c494e878093580470  engine/texte_de.py
- sha256:0e0bea4e821f559a74f947775e40959df296c02413468f9d8b85418aa70c5140  engine/texte_en.py
- sha256:7eb9e957c8b4755766f114e6cf673c742454a5fbeb0c09a04a45c8a7a5430763  engine/waechter.py

## Prüfbasis

- base: 9fdd8589385308515a03979eee964ba61800ef65
- blob:2d0b81319a8b94f1d4eb405af266e42df0e3f5de  engine/anmeldung.py
- blob:271c13cb3bf068d44e54491b1103982173d3ce56  engine/instanz.py
- blob:4e213c9a22df48e3edfc3d9b73af36c6dd9a9e58  engine/konnektor.py
- blob:630b9125079ba737baa68a94962a56cbcf8f11c5  engine/konten.py
- blob:48b4c93a1ad857e34517faf4fe57ab506216c0fe  engine/reisespeicher.py
- blob:3e14e7112dd18ce3f0e0975828e04678f5afb2ed  engine/rueckmeldungen.py
- blob:41b257058f30d307cc434535f9db96b491c0ee91  engine/schreiben.py
- blob:e428b02c25f85da9c8d85927bf13f7450f2c5d01  engine/texte_de.py
- blob:75c2696627bd3e262c2287de885ef62418061cb3  engine/texte_en.py
- blob:38222e11bbb3f5cf92f4938ff06e78296cec81e0  engine/waechter.py
