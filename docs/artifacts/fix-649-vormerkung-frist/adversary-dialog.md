# Adversary Dialog — fix-649-vormerkung-frist
Spec: docs/specs/betrieb/vormerkung-frist-649.md
Datum: 2026-11-24 09:38

## Checkliste
- [x] **AC-1:** Given eine unbestätigte Vormerkung, die jünger als `BILD_VORMERKUNG_FRIST` ist und deren Eintrag nicht entfernt ist / When der Wächter läuft / Then bleibt die Zeile bestehen und ein späteres Bestätigen gelingt.
- [x] **AC-2:** Given eine unbestätigte Vormerkung, die älter als `BILD_VORMERKUNG_FRIST` ist und deren Eintrag nicht entfernt ist / When der Wächter läuft / Then wird sie verworfen.
- [x] **AC-3:** Given eine liegengebliebene unbestätigte Zeile / When dieselbe Löschung erneut vorgemerkt wird / Then wird `vorgemerkt` auf die aktuelle Zeit gesetzt und der Wächter verwirft sie innerhalb der Frist nicht.
- [x] **AC-4:** Given `bild_loeschung_verwerfen` ohne `nur_aelter_als` / When aufgerufen / Then verhält es sich unverändert; `schreiben.py` braucht keine Änderung.
- [x] **AC-5:** Given eine Kontendatenbank von vor dem Update / When sie geöffnet wird / Then ergänzt `db()` die Spalte `vorgemerkt` mit Standard 0 ohne Handschritt, und alte Zeilen gelten als älter als die Frist.
- [x] **AC-6:** Given eine bestätigte Zeile / When der Wächter oder `bild_loeschung_verwerfen` mit Frist läuft / Then bleibt sie unberührt.
- [x] **AC-7:** Given eine junge Zeile, deren Eintrag schon entfernt ist / When der Wächter läuft / Then wird sie wie bisher sofort bestätigt.
- [x] **AC-8:** Given `bild_loeschungen()` / When aufgerufen / Then enthält jede Zeile das Feld `vorgemerkt`.
- [x] **AC-9:** Given `docs/betrieb.md` / When gelesen / Then nennt sie die Frist von einer Stunde, und die gesamte Testsuite ist grün.

## Dialog

### Runde 1
**Adversary:** Ich gehe von einem fehlerhaften Stand aus und fordere je AC einen Codepfad. Gezielter Lauf `engine/tests/test_bilder_eigen.py`: 82 passed (docs/artifacts/fix-649-vormerkung-frist/adversary-test-output.txt). Voller Lauf laut Nachweisdatei: 3589 passed.

Confirmation:
  AC: AC-1
  Code reference: engine/waechter.py:562
  Evidence: Verwerfen nur mit nur_aelter_als=BILD_VORMERKUNG_FRIST; junge Zeile bleibt, bild_loeschung_bestaetigen (engine/konten.py:1326) legt per ON CONFLICT UPDATE normal fest. Test test_junge_vormerkung_bleibt_beim_waechter_und_laesst_sich_bestaetigen.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/konten.py:1339
  Evidence: DELETE mit `vorgemerkt <= _jetzt() - nur_aelter_als`; Grenze inklusiv. Test test_liegengebliebene_vormerkung_ohne_vorgang_schadet_nicht (Zeit vorgestellt) grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/konten.py:1305
  Evidence: UPDATE setzt vorgemerkt = _jetzt() per CASE nur bei bestaetigt = 0; INSERT setzt _jetzt(). Test test_vormerkung_auf_alter_zeile_frischt_den_zeitpunkt_auf grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/konten.py:1339
  Evidence: Zweig nur_aelter_als is None ist der alte DELETE unverändert; engine/schreiben.py:5737 ruft ohne Frist, schreiben.py nicht im Diff.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/konten.py:1294
  Evidence: Spalte in BILD_LOESCHUNG_SPALTEN, db() (konten.py:223) ergänzt per ALTER TABLE ADD COLUMN mit konstantem Standard 0 (in SQLite zulässig, NOT NULL mit DEFAULT); 0 <= jetzt-3600 also alt. Test test_alte_unbestaetigte_zeilen_ohne_zeitpunkt_gelten_als_alt grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/konten.py:1339
  Evidence: Beide DELETE-Zweige enthalten bestaetigt = 0; Wächter erreicht den Verwerfen-Zweig nur bei not z["bestaetigt"] (engine/waechter.py:560). Test test_bestaetigte_zeile_bleibt_in_jedem_alter grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/waechter.py:563
  Evidence: Ist der Eintrag entfernt, wird ohne Altersprüfung sofort bestätigt. Test test_junge_vormerkung_mit_entferntem_eintrag_wird_sofort_bestaetigt grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/konten.py:1365
  Evidence: bild_loeschungen() liefert "vorgemerkt": z[5] aus erweitertem SELECT; Spaltenreihenfolge im SELECT passt zu z[5].
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/konten.py:1297
  Evidence: BILD_VORMERKUNG_FRIST = 3600; docs/betrieb.md nennt „nach einer Stunde“ (Diff Zeile 114); test_frist_ist_eine_stunde und test_betrieb_nennt_die_frist_von_einer_stunde grün; volle Suite 3589 passed.
  Status: CONFIRMED

**Implementierer:** keine Einwände.

### Runde 2
**Adversary:** Frühe Einigkeit ist verdächtig, daher gezielte Angriffe:
- Wettlauf Lesen/Verwerfen: Wächter liest z unbestätigt, dann frischt ein Vormerken auf oder der Schreibweg bestätigt. Die Altersprüfung und bestaetigt = 0 stehen im selben DELETE (engine/konten.py:1339): eine aufgefrischte oder bestätigte Zeile bleibt. Kein Verlust.
- Zeitstempel bei bestätigter Zeile: vorgemerkt bleibt unverändert (CASE), bei Neuanlage per bild_loeschung_bestaetigen 0; belanglos, da bestätigte Zeilen nie verworfen werden (bestaetigt = 0 im DELETE).
- NULL/0: Spalte NOT NULL DEFAULT 0; alte Zeilen 0 gelten als alt (gewollt, Spec Punkt 1).
- Zeitumstellung: _jetzt() ist time.time() (UTC-Epoche), keine lokale Zeit; unkritisch. Eine rückwärts springende Systemuhr verlängert nur die Schonfrist, verwirft nichts zu früh.
- Erneutes Vormerken einer liegengebliebenen Zeile liefert False; scheitert danach der Vorgang, verwirft schreiben.py sie nicht (vorgemerkt False), die Frist räumt sie nach einer Stunde ab. Das ist bisheriges Verhalten und nach Spec vertretbar.
- Regression: einzige Aufrufer von bild_loeschung_verwerfen sind waechter.py:562 und schreiben.py:5737 (Signatur kompatibel). Weitere Leser von bild_loeschungen() erhalten nur ein zusätzliches Dictionary-Feld; Tests in test_betrieb.py laut Auftrag grün.
- Rechtsfolge einer jungen, liegengebliebenen Zeile: Sie bleibt höchstens eine Stunde länger; der Wächter läuft täglich, das Nachholen verzögert sich also höchstens um einen Lauf. Kein Spec-Verstoß.

Finding (nicht blockierend):
  ID: F001
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/waechter.py:547
  Description: Der erweiterte Docstring von _bildloeschung_nachholen hat eine sehr lange Zeile (Umbruch fehlt nach „neu bewertet.“).
  Spec requirement: AC-9 — nur Doku, keine Funktion
  Conflict: reiner Stilpunkt, keine Auswirkung
  Remediation: Zeile umbrechen

**Implementierer:** F001 ist kosmetisch.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hat den Angriffen standgehalten.
Tests: 82 passed (test_bilder_eigen.py, eigener Lauf), 0 failed, 0 übersprungen; volle Suite laut Nachweis 3589 passed
Edge cases: Wettlauf, 0/NULL, Zeitstempel bestätigter Zeilen, Zeitbasis geprüft, nichts gebrochen
Regressions: None found
Checklist: 9/9 points proven
Finding F001 (LOW, kosmetisch, nicht blockierend)

## Geprüfte Dateien

- sha256:49d50632cd02626f31a29a58e65a4a4f21cd0b78e3e1005402af75077d9415fe  engine/konten.py
- sha256:00a7876ed436f57ed5d98f75ef188bb1f4b9e3eb79870215bca2f09cb587e0ac  engine/waechter.py

## Prüfbasis

- base: 26e0a991558317bae265d6f2470ec1001a302411
- blob:63691c07e89e497717672af4e3c9e669e5faa9bf  engine/konten.py
- blob:0f74f5567a9c5665519965a0f002b64c20786608  engine/waechter.py
