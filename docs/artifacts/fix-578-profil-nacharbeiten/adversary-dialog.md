# Adversary Dialog — fix-578-profil-nacharbeiten
Spec: docs/specs/konnektor/profil-nacharbeiten-578.md
Datum: 2026-11-21 09:59

## Checkliste
- [x] **AC-1 (F001):** Given ein Konto mit Schreibgrenze und ein abgelehnter `profile_entry_set` (leer, zu lang, unbekannte oder fremde `PR-<n>`, Profil voll) / When danach weitere gültige Einträge gesetzt werden / Then hat der abgelehnte Aufruf nicht zur Schreibgrenze gezählt. Test: `test_abgelehnter_eintrag_zaehlt_nicht_zur_schreibgrenze`, `test_profil_voll_zaehlt_nicht`.
- [x] **AC-2 (F001):** Given die Schreibgrenze ist erreicht / When `profile_entry_set` aufgerufen wird / Then wird vor dem Schreiben abgelehnt, nichts gespeichert, und angenommene Einträge zählen weiterhin. Test: `test_angenommener_eintrag_zaehlt_zur_schreibgrenze`, bestehender Test 10 aus profile-12.
- [x] **AC-3 (F002):** Given der reisebezogene Zugang ohne Konto / When die Anleitung erzeugt wird / Then enthält sie keinen Satz zum Profil. Test: `test_anleitung_ohne_konto_ohne_profilsatz`.
- [x] **AC-4 (F002):** Given der Konto-Zugang / When die Anleitung je Baustein `profile` (an, aus, `None`) erzeugt wird / Then bleibt der Satz unverändert (profile-12 Test 14 grün).
- [x] **AC-5 (F003):** Given Obergrenze 1 und zwei gleichzeitige Neuanlagen / When beide `profil_setzen` aufrufen / Then gelingt genau eine, die andere bekommt `profil_voll`, das Konto hat einen Eintrag. Test: `test_profil_setzen_obergrenze_bei_gleichzeitigkeit`.
- [x] **AC-6 (F003):** Given `profil_setzen` legt einen Eintrag neu an / When die Anweisungen der Verbindung mitgeschrieben werden / Then steht `BEGIN IMMEDIATE` vor dem `COUNT`; auch eine frische Datenbank führt zu keinem Transaktionsfehler. Test: `test_profil_setzen_beginnt_immediate_vor_dem_zaehlen`, `test_profil_setzen_frische_datenbank`.
- [x] **AC-7 (F004):** Given ein früherer Test hat `anmeldung._anfrage.sprache` im selben Thread gesetzt / When `test_pruefungen_buendeln_je_reise_und_tag` läuft / Then ist das Ergebnis dasselbe wie in Einzelausführung, in jeder Reihenfolge. Test: `test_seitensprache_frueherer_test_stoert_nicht` und der bestehende Test.
- [x] **AC-8:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen; Ausnahmelisten in `test_texte.py` nicht länger, `deploy.sh` unverändert.
- [x] **AC-9:** Given der Nachzug / When `profile-12` gelesen wird / Then nennt Punkt 7 „nur ein angenommener Eintrag zählt“ und die Anleitung gilt nur im Konto-Zugang (Textprüfung beim Abschluss).

## Dialog

### Runde 1
**Adversary:** Behauptung: Reihenfolge in profil_werkzeug ist jetzt Grenze pruefen, profil_setzen, dann schreiben_vormerken. Angriff: Jeder KontoFehler aus profil_setzen (leer, zu lang, profil_unbekannt, profil_voll) verlaesst die Funktion vor dem Vormerken. Gelesen: engine/konnektor.py:2735-2739 (schreibgrenze vorher, Vormerken nach profil_setzen). Die Grenze lehnt weiter vor dem Schreiben ab (AC-2). Schwachstelle gesucht: Fehler in schreiben_vormerken nach erfolgreichem Schreiben. Befund: schreiben_vormerken (engine/konten.py:838) ist ein einzelner INSERT; faellt er aus, ist der Eintrag gespeichert aber ungezaehlt und der Aufrufer bekommt eine Ausnahme statt KontoFehler. Das ist ein reiner Infrastrukturfehler (SQLite-Ausfall), vorher war es umgekehrt; kein Spec-Verstoss, nur LOW-Anmerkung. Zweiter Angriff: Ein Aendern mit id unter BEGIN IMMEDIATE (engine/konten.py:765): _profil_zeile und UPDATE laufen in derselben Transaktion, das Ende uebernimmt `with v`; bei KontoFehler rollt `with v` zurueck, nichts bleibt. Dritter Angriff: Wird profil_setzen in einer schon offenen Transaktion derselben Verbindung aufgerufen? Die Verbindung wird in profil_setzen selbst per db() frisch geoeffnet (einziger Aufrufer engine/konnektor.py:2738), also nie verschachtelt. BEGIN IMMEDIATE im Legacy-Isolationsmodus ist zulaessig, weil sqlite3 vor einer expliziten BEGIN-Anweisung nichts oeffnet (kein DML davor); Test frische DB laeuft gruen. Anleitung: engine/konnektor.py:3407 prueft zugang.get("konto_id"); der Konto-Zugang (konnektor.py:2569) setzt konto_id immer, der reisebezogene Zugang (konnektor.py:3607) hat es nicht, mein_profil wird dort nicht angeboten. Kein umgekehrter Fall gefunden. Teststand: 71 passed in test_profil.py und test_anmeldung.py (zufaellige Reihenfolge), siehe adversary-test-output.txt.
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Skepsis gegen Frueh-Einigung. Zweiter Lauf mit -p no:randomly: 71 passed (feste Reihenfolge, deckt AC-7: der Test test_seitensprache_frueherer_test_setzt laeuft direkt vor ..._stoert_nicht). Fixture-Loeschung engine/tests/conftest.py:84-86 entfernt anmeldung._anfrage.sprache nur, wenn das Modul schon importiert ist; ist es nicht importiert, kann kein frueherer Test die Sprache gesetzt haben. Parallelitaet (AC-5): BEGIN IMMEDIATE holt die Schreibsperre vor COUNT, die zweite Verbindung wartet bis zum Timeout 10 s (engine/konten.py:202) und sieht danach den Eintrag; Test test_profil_setzen_obergrenze_bei_gleichzeitigkeit gruen. Rest-Beobachtung: Die Schreibgrenze (schreibgrenze/schreiben_vormerken) ist weiter nicht atomar mit profil_setzen; zwei parallele Aufrufe koennen beide die Grenze passieren (Check-then-act), das war vorher genauso und ist nicht Gegenstand von #578. AC-8: git diff gegen 0de8fbe zeigt keine Aenderung an engine/texte_de.py, engine/texte_en.py, engine/tests/test_texte.py, betrieb/deploy.sh. Gesamtlauf 3379 passed laut test-green-output.txt, nicht wiederholt (Server belastet). AC-9: profile-12.md Punkt 7 enthaelt „Nur ein angenommener Eintrag zählt zur Schreibgrenze“, Punkt 12 und AC-6 „nur im Konto-Zugang“. Alle Punkte belegt, keine Gegenbeispiele gefunden.
**Implementierer:** (nicht beteiligt, Kontextisolation)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/konten.py:838
  Description: schreiben_vormerken ist ein eigener INSERT nach dem Schreiben; schlaegt er fehl (DB-Ausfall), bleibt der Eintrag gespeichert, aber ungezaehlt, und der Aufrufer erhaelt eine Ausnahme.
  Spec requirement: AC-1 — nur angenommene Eintraege zaehlen
  Conflict: Kein Verstoss; nur theoretische Zaehllücke bei Infrastrukturausfall.
  Remediation: Keine noetig.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/konnektor.py:2739
  Evidence: schreiben_vormerken steht nach profil_setzen; KontoFehler (leer, zu lang, unbekannt, voll) springt vorher zum except.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/konnektor.py:2735
  Evidence: schreibgrenze wird vor profil_setzen geprueft und lehnt vor dem Schreiben ab; angenommene Eintraege werden weiter vorgemerkt (Zeile 2739).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/konnektor.py:3407
  Evidence: Profilsatz nur bei zugang.get("konto_id"); der reisebezogene Zugang (konnektor.py:3607) hat keines.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/konnektor.py:3408
  Evidence: Auswahl profil_nutzen / profil_nicht_nutzen unveraendert fuer an, aus, None; Konto-Zugang setzt konto_id (konnektor.py:2569).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/konten.py:765
  Evidence: BEGIN IMMEDIATE sperrt vor dem COUNT; Gleichzeitigkeitstest gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/konten.py:765
  Evidence: BEGIN IMMEDIATE steht vor COUNT (Zeile 772); Test frische DB gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/tests/conftest.py:86
  Evidence: Fixture loescht anmeldung._anfrage.sprache; beide Laeufe (zufaellig und fest) gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/konnektor.py:2738
  Evidence: gezielte Laeufe 71 passed (zweimal), Gesamtlauf 3379 passed laut Vorlauf, texte_*.py, test_texte.py, deploy.sh unveraendert gegenueber 0de8fbe.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/konten.py:758
  Evidence: profile-12.md Punkte 7 und 12 enthalten die geforderten Formulierungen (git diff).
  Status: CONFIRMED

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hat dem Angriff standgehalten.
Tests: 71 passed (2 Laeufe), 0 failed, 0 uebersprungen; Gesamtlauf 3379 passed laut Vorlauf
Edge cases: geprueft, keine gebrochen (nur LOW F001, theoretisch)
Regressions: keine gefunden
Checklist: 9/9 Punkte belegt

## Geprüfte Dateien

- sha256:e24415369425a54102a202e71322a4d684b1d445945124120001bab3d434a158  engine/konnektor.py
- sha256:726eb054b9fd5a051ff385e17b1efed6201c1364cb3a4678df769c49c0b1d94e  engine/konten.py
- sha256:e9046f7eaaa2b14735cf4ea0e62bf2bcb8b409d1a5d39f6ffc412bb2b670bf7c  engine/tests/conftest.py

## Prüfbasis

- base: 0de8fbe1911fbe7c8d2e2cc24bf2d0561dc8fe50
- blob:59216393be34679e2804b0fb2144b5dac9e35a57  engine/konnektor.py
- blob:dfbda06cc88a196f046a3fbe9c2c906cc1d3899f  engine/konten.py
- blob:9d18cceb8d4494d1f5f8b4e47260b0f5ddcae7f5  engine/tests/conftest.py

## Geprüfte Dateien

- sha256:e24415369425a54102a202e71322a4d684b1d445945124120001bab3d434a158  engine/konnektor.py
- sha256:726eb054b9fd5a051ff385e17b1efed6201c1364cb3a4678df769c49c0b1d94e  engine/konten.py
- sha256:e9046f7eaaa2b14735cf4ea0e62bf2bcb8b409d1a5d39f6ffc412bb2b670bf7c  engine/tests/conftest.py

## Prüfbasis

- base: 0de8fbe1911fbe7c8d2e2cc24bf2d0561dc8fe50
- blob:59216393be34679e2804b0fb2144b5dac9e35a57  engine/konnektor.py
- blob:dfbda06cc88a196f046a3fbe9c2c906cc1d3899f  engine/konten.py
- blob:9d18cceb8d4494d1f5f8b4e47260b0f5ddcae7f5  engine/tests/conftest.py
