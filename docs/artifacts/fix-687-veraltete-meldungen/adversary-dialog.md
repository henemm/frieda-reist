# Adversary Dialog — fix-687-veraltete-meldungen
Spec: docs/specs/konnektor/veraltete-meldungen-687.md
Datum: 2026-11-24 18:47

## Checkliste
- [x] **AC-1:** Given eine Meldung `neue_reise` zu einer Reise / When die Reise vorgemerkt wird / Then verschwindet die Meldung bei Konnektor und Mein Konto. PROVEN: `test_neue_reise_vorgemerkt_verschwindet`; Code `engine/rueckmeldungen.py:437-438` (ziel nicht in `vorgemerkte_reisen`), angewendet `engine/rueckmeldungen.py:464`; dieselbe Quelle für Konnektor (`engine/konnektor.py:2591`) und Mein Konto (`engine/anmeldung.py:640`, `:663`).
- [x] **AC-2:** Given dieselbe Lage / When die Reise endgültig entfernt ist / Then bleibt sie weg. PROVEN: `test_neue_reise_entfernt_verschwindet`; `konten.vorgemerkte_reisen` vereinigt `reise_loeschung` und `loeschprotokoll` (`engine/konten.py:1236`).
- [x] **AC-3:** Given die Reise ist vorgemerkt / When sie zurückgeholt wird / Then erscheint die Meldung wieder. PROVEN: `test_neue_reise_zurueckgeholt_erscheint_wieder` (Datei dazwischen byte-gleich).
- [x] **AC-4:** Given eine nicht vorgemerkte Reise ohne Mitgliedschaft / When gelesen wird / Then bleibt die Meldung sichtbar. PROVEN: `test_neue_reise_ohne_mitgliedschaft_bleibt` (Maßstab ist die Vormerkung, nicht die Mitgliedschaft).
- [x] **AC-5:** Given eine Bitte "Reisen anlegen" / When sie freigeschaltet wird / Then verschwindet die Meldung bei den Betreibern. PROVEN: `test_bitte_freigeschaltet_verschwindet`; Feld `konto` geschrieben in `engine/anmeldung.py:1728`, geprüft in `engine/rueckmeldungen.py:441-443`.
- [x] **AC-6:** Bitte abgelehnt: Meldung weg. PROVEN: `test_bitte_abgelehnt_verschwindet` (`konten.anfragen()` filtert `status = offen`, `engine/konten.py:888`).
- [x] **AC-7:** Konto gelöscht: Meldung weg. PROVEN: `test_bitte_konto_geloescht_verschwindet`.
- [x] **AC-8:** Konten zusammengeführt: Meldung weg. PROVEN: `test_bitte_konten_zusammengefuehrt_verschwindet` (`engine/konten.py:717` löscht die Bitte des Quellkontos).
- [x] **AC-9:** Offene Bitte bleibt sichtbar. PROVEN: `test_offene_bitte_bleibt_sichtbar` (Karl offen, Lea entschieden: genau eine Meldung, die von Karl).
- [x] **AC-10:** Wartelisten-Eintrag freigegeben: Meldung weg. PROVEN: `test_wartelisten_eintrag_freigegeben_verschwindet`; `engine/rueckmeldungen.py:444-446` mit `konten.warteliste()`.
- [x] **AC-11:** Wartelisten-Eintrag gelöscht: Meldung weg. PROVEN: `test_wartelisten_eintrag_geloescht_verschwindet`.
- [x] **AC-12:** Offener Wartelisten-Eintrag bleibt sichtbar. PROVEN: `test_offener_wartelisten_eintrag_bleibt_sichtbar`.
- [x] **AC-13:** Adresse geändert, Bitte mit Feld `konto` bleibt. PROVEN: `test_adresse_geaendert_bitte_mit_feld_konto_bleibt` (prüft auch `roh["konto"] == "k-karl"` aus der Ablage, also das Schreiben in `engine/anmeldung.py:1728`).
- [x] **AC-14:** Altmeldung ohne Feld `konto` über Adresse. PROVEN: `test_altmeldung_ohne_feld_konto_ueber_adresse` (Groß-/Kleinschreibung; `engine/rueckmeldungen.py:421-429`, `:444-446`).
- [x] **AC-15:** Altmeldung ohne Feld und ohne `t` bleibt. PROVEN: `test_nicht_zuzuordnende_altmeldung_bleibt` (auch Ablauf nach 20 Tagen).
- [x] **AC-16:** Unlesbares `t` wirft nicht, Meldung bleibt. PROVEN: `test_unlesbares_t_wirft_nicht` (18 Formen von t, beide Arten), `test_unlesbares_konto_wirft_nicht` (5 Formen von konto, ziel None und 7).
- [x] **AC-17:** Andere Arten unverändert. PROVEN: `test_andere_arten_unveraendert`; `engine/rueckmeldungen.py:439-440` (alles außer den drei Arten gilt).
- [x] **AC-18:** Mehrere Betreiber, eine Entscheidung gilt für alle. PROVEN: `test_mehrere_betreiber_entscheidung_gilt_fuer_alle`.
- [x] **AC-19:** Wirkung in `my_trips` und auf `/konto`. PROVEN: `test_wirkung_im_konnektor_my_trips`, `test_wirkung_auf_mein_konto`, zusätzlich `test_zahl_der_gelesenen_sinkt_im_konnektor`, `test_veraltete_meldung_laesst_sich_nicht_mehr_oeffnen`.
- [x] **AC-20:** `meldungen.jsonl` bleibt unverändert. PROVEN: `test_filter_nur_beim_lesen` (byte-gleich); der Filter ist reine Listenbildung ohne Schreibzugriff (`engine/rueckmeldungen.py:464`).
- [x] **AC-21:** Testanfrage nicht unterdrückt. PROVEN: `test_testanfrage_wird_nicht_unterdrueckt`; im Code keine Sonderbehandlung von Adressen.
- [ ] **AC-22:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün. NICHT BELEGT, siehe Runde 2: Gesamtlauf unter macOS rot (92 failed, 41 errors, 403 skipped, nur Server- und Betriebs-Testdateien), grüner Lauf nur Teillauf (2596 passed, 302 skipped), CI (Linux) steht aus.

## Dialog

### Runde 1
**Adversary:** Review des Diffs gegen 93915e8 und der 26 Tests in `engine/tests/test_meldungen_veraltet.py`.
Code reference: engine/rueckmeldungen.py:421 (meldung_adresse), engine/rueckmeldungen.py:432 (ohne_reise_gilt), engine/rueckmeldungen.py:464 (Filter in meldungen_des_kontos).
Code reference: engine/anmeldung.py:1728 (betreiber_melden schreibt `konto` nur bei Art anfrage_reisen und vorhandener Kennung).
- Randfälle der Ablage: `meldungen()` überspringt kaputte JSON-Zeilen (`engine/rueckmeldungen.py:359-362`). Die neue Prüfung wirft nicht: ziel wird als `str(... or "")` verglichen (Liste, Zahl, None unschädlich), `konto` zählt nur als nicht leerer str, sonst Rückfall auf `t`; `t` wird auf Liste, Paarform, Schlüssel und dict geprüft, `email` nur als str. Nicht neu und nicht im Scope: eine gültige JSON-Zeile, die kein Objekt ist, ließe schon `meldungen()` (`m.get`) werfen.
- Ohne Kontendatenbank: `konten.vorgemerkte_reisen()` legt nichts an (`engine/konten.py:1233`). `anfragen()` und `warteliste()` öffnen die Datenbank über `db()` (legt sie an), aber `meldungen_des_kontos` ruft davor ohnehin `konten.mitgliedschaften` auf (gleiche Wirkung wie bisher); die Mengen werden nur bei passender Art und höchstens einmal geladen (`test_mengen_hoechstens_einmal_und_nur_bei_bedarf`).
- Aufrufer von `betreiber_melden`: `engine/anmeldung.py:1539` (Art betrieb, k=None), `:1560` (Warteliste, k=None), `:1649` und `engine/konnektor.py:2647` (Sitzungskonto mit id). Ohne Konto oder Kennung kein Feld, Push-Tests mit `TOM` ohne id grün (test_push.py im Lauf in Runde 2).
- Leser von `meldungen_des_kontos`: `engine/konnektor.py:2591`, `engine/anmeldung.py:640`, `:663`, `:1672` (gefilterte Meldungen werden nicht als gelesen vermerkt, gewollt). Push liest über `meldungen_aktuell` (`engine/push.py:573`), nicht über den Filter; `meldungen_aktuell` unverändert, Push unberührt (bekannte Grenze der Spec).
- Übereinstimmung mit Mein Konto: Maßstab sind dieselben Funktionen wie bei Freischaltungen und Warteliste (`konten.anfragen()` mit status offen, `konten.warteliste()` bestätigt und nicht freigegeben), keine nachgebaute Bedingung.
- Datenschutz: Das Feld `konto` (interne Kennung) steht nur in `meldungen.jsonl`. `meldungen_des_kontos` gibt nur reise, id, erstellt, text, art, ziel, bezug, t, gelesen heraus (`engine/rueckmeldungen.py:472`), also sehen Konnektor-Ausgabe, HTML und Push-Nutzlast es nicht; Empfänger sind Betreiber, die die Kennung im Formular "freischalten" (`wer`) ohnehin verwenden. Keine Adresse in neuen Werten (ADRESSE sperrt nur URLs).
- Mutationstest in einer Kopie im Scratchpad (Kopie von engine, beispiel, betrieb, werkzeuge; Repo unverändert), Lauf von `test_meldungen_veraltet.py`: A Filter aus: 26 von 26 rot. B neue_reise immer sichtbar: 11 rot. D Bitte mit konto immer gültig: 13 rot. G Warteliste prüft anfragen statt warteliste: 9 rot. F Unzuordenbares wird versteckt: 3 rot (AC-15, AC-16). E Altmeldung ohne casefold: 1 rot (AC-14). I Feld konto ignoriert: 1 rot (AC-13). Keine überlebende Mutation unter diesen sieben. Nicht ausgeführt: Entfernen von `extra={"konto": ...}` in `engine/anmeldung.py` (nur durch die Assertion `roh.get("konto") == "k-karl"` in AC-13 gedeckt, nicht als Mutation gelaufen).
**Implementierer:** keine Antwort (Adversary-Lauf ohne Dialogpartner); Entwicklerangaben nur aus den abgelegten Dateien.

### Runde 2
**Adversary:** Zweiter, unabhängiger Durchgang: Läufe, Doku, AC-22.
- Gezielter Lauf (Ausgabe in `docs/artifacts/fix-687-veraltete-meldungen/adversary-test-output.txt`): `test_meldungen_veraltet.py`, `test_anmeldung.py`, `test_warteliste.py`, `test_push.py`, `test_trennung.py`, `test_loeschen_reise.py`, `test_export.py` mit `-n 3`: 265 passed, 0 failed, 0 übersprungen. Zusätzlich `test_protokolle_ohne_pfade.py` und `test_texte.py`: 93 passed.
- Doku-Sätze geprüft: `docs/funktionen/erinnerungen.md` (Meldung zur neuen Reise verschwindet mit dem Löschen und kommt mit dem Zurückholen wieder, Anfrage verschwindet nach Entscheidung: stimmt mit AC-1 bis AC-3, AC-5 bis AC-8), `docs/konnektor.md` (gefiltert beim Lesen, Datei unverändert: stimmt mit AC-20), `docs/konten.md` (Bitte und Warteliste-Meldung verschwinden bei Entscheidung oder wenn das Konto weg ist: stimmt mit AC-5 bis AC-11). Kleine Unschärfe, kein Finding: Spec sagt "vorgemerkt oder entfernt", erinnerungen.md sagt "gelöscht".
- AC-22 selbst geprüft: Die macOS-Fehler des Gesamtlaufs liegen nur in `test_nginx.py`, `test_nginx_reise_helfer.py`, `test_betrieb.py`, `test_kartendienst_skript.py`, `test_units.py`, `test_nginx_helfer.py`, `test_kartendienst.py`, `test_units_helfer.py`, `test_rueckbau_557.py` (Server- und Betriebsskripte). Prüfung des Entwicklerberichts: diese neun Dateien in Kopien einmal mit dem geänderten Stand und einmal mit `rueckmeldungen.py` und `anmeldung.py` aus 93915e8 gelaufen: beide Male 108 failed, 503 passed, 101 skipped, 41 errors (die Kopie ohne `docs/` hat mehr Fehler als der Gesamtlauf; aussagekräftig ist nur der Vergleich der zwei Stände). Das belegt, dass die Fehler nicht von der Änderung stammen, aber nicht, dass der Lauf grün ist. Es gibt keinen grünen Gesamtlauf: `test-green-output.txt` (2596 passed, 302 übersprungen) ist ein Teillauf ohne diese neun Dateien, der Gesamtlauf hatte 403 übersprungen. Einziger Beleg für AC-22 wäre die Linux-CI nach dem Commit.
- Skepsis gegenüber Runde 1: Alle 21 inhaltlichen ACs sind je durch einen Test belegt, dessen Fehlschlagen unter Mutation gezeigt wurde; der grüne Lauf allein wurde nicht akzeptiert.

Finding:
  ID: F001
  Severity: MEDIUM
  Category: spec_violation
  Code reference: engine/rueckmeldungen.py:464
  Description: Kein Mangel im Code. AC-22 verlangt einen grünen Gesamtlauf; vorliegend ist der macOS-Gesamtlauf rot (92 failed, 41 errors, 403 skipped) und der grüne Lauf ein Teillauf mit 302 übersprungenen. Die Rotfälle sind laut Vergleichslauf unabhängig von der Änderung.
  Spec requirement: AC-22 — alles grün
  Conflict: AC-22 ist derzeit nicht belegt; belegbar nur durch die Linux-CI (`tests (leer)`, `tests (instanz)`) nach dem Commit.
  Remediation: Committen, CI abwarten, erst bei grüner CI vorspulen.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/anmeldung.py:1728
  Description: Wird die Bitte mehrfach gestellt (`reisen_anlegen_anfragen` liefert für eine offene Bitte erneut offen, `engine/konten.py:880`), entstehen mehrere Meldungen mit demselben konto; sie verschwinden gemeinsam mit der Entscheidung.
  Spec requirement: Spec, Abgrenzung "Zweimal gebeten: zwei Meldungen, beide verschwinden mit der Entscheidung"
  Conflict: keiner, bewusst dokumentiert; nur Beobachtung.
  Remediation: keine.

Confirmation:
  AC: AC-1 bis AC-12, AC-14 bis AC-21
  Code reference: engine/rueckmeldungen.py:432
  Evidence: ohne_reise_gilt deckt neue_reise, anfrage_reisen (Feld konto, sonst Adresse), anfrage_warteliste und alle übrigen Arten ab; sieben Mutationen rot, 26 von 26 Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/anmeldung.py:1728
  Evidence: extra konto nur bei Art anfrage_reisen und Konto mit Kennung; der Test liest `konto` aus der Ablage, Mutation I (Feld ignoriert) rot.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
AMBIGUOUS. AC-1 bis AC-21 halten dem Adversary-Test stand, kein Code-Mangel gefunden. AC-22 (grüner Gesamtlauf) ist nicht belegt: macOS-Gesamtlauf rot in neun Server-Testdateien (unabhängig von der Änderung), nur Teillauf grün, CI steht aus. Deshalb kein VERIFIED.
Tests: gezielter Lauf 265 passed, 0 failed, 0 übersprungen; Zusatzlauf 93 passed.

## Geprüfte Dateien

- sha256:7efe1f19552d78f580c17eb91ef02b7b2ac43d8bfa8115fa2817ffcac107321a  engine/anmeldung.py
- sha256:112f94cd236864f7f3d5202e468f62abd2d095d0a72d40497d3106ccb269f65f  engine/rueckmeldungen.py

## Prüfbasis

- base: 35e2d890bf82b956fbe78a698e42757e510ec42b
- blob:84f88a0c39f56a5207cee13c3c0304719f511958  engine/anmeldung.py
- blob:6677a9f21164b882f9ed608055428aa18f605dea  engine/rueckmeldungen.py
