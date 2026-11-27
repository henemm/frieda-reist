# Adversary Dialog — fix-738-erneuern-antwort
Spec: docs/specs/fast/fix-738-erneuern-antwort.md
Datum: 2026-11-27 19:12

## Checkliste
- [x] AC-1: Antwortet `/token` beim Erneuern mit HTTP 200 und leerem Körper, `[]` oder `{}`, beantwortet die Brücke jede Anfrage mit `-32603` und ihrer ID, läuft bis zum Ende der Eingabe weiter und endet mit Exit 0, ohne Traceback.
- [x] AC-2: Die Ablage des Zugangs bleibt dabei unverändert (Refresh-Token nicht überschrieben).
- [x] AC-3: Bestehende Tests des Testzugangs bleiben grün.

## Dialog

### Runde 1
**Adversary:** Behauptung: HTTP 200 mit leerem Körper, `[]`, `{}` beendet die Brücke weiter. Geprüft: `json.loads` ValueError, `[]`/`{}`/`null`/`"text"` TypeError bzw. KeyError, nur `access_token` KeyError, `expires_in` "abc" ValueError, Liste TypeError, ungültiges UTF-8 UnicodeDecodeError (ValueError) - alle im `except` abgedeckt. Die neue Ausnahme trägt eine feste Meldung ohne Token und ohne Körper (`from None` verwirft den Kontext). `self.daten` und `ablage_schreiben` laufen erst nach dem `try`, die Ablage bleibt also unverändert. Die Kontoprüfung (`konto_pruefen`, `Abbruch`) ist unberührt.
**Implementierer:** Test `test_bruecke_beantwortet_unbrauchbare_erneuerung_mit_fehler` (3 Körper) prüft Exit 0, IDs 1 und 2 mit -32603, kein Traceback und Ablage byte-gleich.

### Runde 2
**Adversary:** Weiter gebohrt: `expires_in` als `1e999` (Infinity) ergibt OverflowError, tief verschachteltes `[[[...` RecursionError; beides nicht gefangen (F001, niedrig, nur bei bösartigem oder defektem eigenem Server, außerhalb der Spec-Beispiele). Eine gültige Erneuerung danach: `ErneuernFehler` verlässt `erneuern` über `finally` (Sperre wird freigegeben), `self.daten` bleibt alt, die nächste Anfrage versucht erneut zu erneuern; Zustand wird nicht vergiftet. Der umgebaute `_bad_gateway`-Helfer nutzt `_anfrage_lesen` mit identischem Verhalten, AC-6 aus #669 ist grün.
**Implementierer:** Kein Gegenargument zu F001; wegen Spec-Umfang akzeptabel.

### Findings und Confirmations

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/testzugang.py:278
  Description: Das `except` fängt ValueError, TypeError, KeyError, AttributeError. `expires_in` mit Wert 1e999 (Python parst Infinity) wirft OverflowError, tiefe Verschachtelung RecursionError; beides fliegt weiter bis `main`.
  Spec requirement: AC-1 — unbrauchbare Antwort mit HTTP 200 darf die Brücke nicht beenden (Spec nennt nur leer, `[]`, `{}`)
  Conflict: Randfälle jenseits der drei Spec-Beispiele beenden die Brücke weiterhin.
  Remediation: `OverflowError` und `RecursionError` in das Tupel aufnehmen (oder `except Exception`).

Confirmation:
  AC: AC-1
  Code reference: betrieb/testzugang.py:277
  Evidence: Unbrauchbare Antwort wird zu ErneuernFehler; `_voruebergehend` (Zeile 343) macht daraus -32603 mit ID; Test mit leer, `[]`, `{}` grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: betrieb/testzugang.py:281
  Evidence: Zuweisung und `ablage_schreiben` stehen nach dem try; Test vergleicht Ablage-Bytes vorher und nachher.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_testzugang.py:526
  Evidence: `pytest -q -n 3 engine/tests/test_testzugang.py`: 26 passed, 0 failed, 0 übersprungen (inkl. #669-Tests).
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 26 passed, 0 failed, 0 übersprungen
Edge cases: geprüft; nur F001 (LOW, OverflowError/RecursionError) offen
Regressions: None found
Checklist: 3/3 points proven

## Geprüfte Dateien

- sha256:f32282c2dfc0cc7a161aded994613fe96863284ddc327b1ce3e30ed86bc2eaf5  betrieb/testzugang.py
- sha256:48413371e62c9467d76be915be3a948e74a63835cde79386253fe27c5cc115a7  engine/tests/test_testzugang.py

## Prüfbasis

- base: febd806074e1ffbb9c5264da21ff0cc39ee2e5d4
- blob:b52a2c3ae01053889f62851fe282fe0f57716570  betrieb/testzugang.py
- blob:f59073d23eda0a15ef15977d2aae2684adcdb234  engine/tests/test_testzugang.py
