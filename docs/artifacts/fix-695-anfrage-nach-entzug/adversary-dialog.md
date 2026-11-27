# Adversary Dialog — fix-695-anfrage-nach-entzug
Spec: docs/specs/konto/bitte-nach-entzug-695.md
Datum: 2026-11-27 20:41

## Checkliste
- [x] **AC-1:** Given ein Konto wurde freigeschaltet und danach ist das Recht `reise_anlegen` entzogen / When `reisen_anlegen_anfragen(kid)` läuft / Then liefert sie `offen`, und die Bitte steht in `anfragen()` (status offen, `erstellt` heute, `entschieden` leer).
- [x] **AC-2:** Given derselbe Zustand / When das Konnektor-Werkzeug `trip_create_request` aufgerufen wird / Then antwortet es ohne Abbruch mit dem Text „liegt beim Betreiber“ und ohne Fehlerflag.
- [x] **AC-3:** Given derselbe Zustand / When auf Mein Konto die Aktion `anfragen` ausgelöst wird / Then liegt die Bitte offen vor, und die Seite zeigt danach „liegt beim Betreiber“ statt des Knopfs.
- [x] **AC-4:** Given eine abgelehnte Bitte / When das Konto erneut bittet / Then bleibt sie `abgelehnt` (Regression); ebenso unverändert: offene Bitte bleibt `offen`, Konto mit Recht liefert `schon_erlaubt`.
- [x] **AC-5:** Given das Wiederöffnen / When die Aktion `anfragen` auf Mein Konto läuft / Then bekommt der Betreiber die Meldung `anfrage_reisen` (einmal, wie bei einer ersten Bitte).

## Dialog

### Runde 1
**Adversary:** Beweise je AC. Tests test_konten.py, test_oauth.py, test_anmeldung.py (neue Tests zu #695): 81 passed (pytest -n 3). Der Diff `git diff 8c88b6e -- engine/konten.py` ist klein: Nur bei Status `freigeschaltet` ohne Recht wird per UPDATE auf `offen` gesetzt (erstellt heute, entschieden NULL), in derselben Transaktion wie das Lesen.

Confirmation:
  AC: AC-1
  Code reference: engine/konten.py:988
  Evidence: UPDATE anfragen SET status='offen', erstellt=?, entschieden=NULL, danach `return "offen"`; test_nach_entzug_des_rechts_neu_bitten prüft status/entschieden in anfragen().
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/konten.py:991
  Evidence: Die Funktion liefert nur noch offen/schon_erlaubt/abgelehnt, das Wörterbuch in konnektor.py (reisen_anlegen_anfragen) kennt alle drei, kein KeyError mehr; test_bitte_nach_entzug_des_rechts: kein Fehlerflag, Text „beim Betreiber“.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/konten.py:988
  Evidence: Aktion `anfragen` in anmeldung.py ruft reisen_anlegen_anfragen; die Seite wählt anhand des Status aus anfragen(nur_offen=False) den Hinweis `anlegen_offen`; test_bitte_nach_entzug_auf_mein_konto prüft Knopf vorher da, nachher Hinweis ohne Knopf.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/konten.py:985
  Evidence: Reihenfolge: Recht -> schon_erlaubt; Zeile mit anderem Status (abgelehnt/offen) -> unverändert zurück. Eigenes Probe-Skript: freischalten(ja=False) danach bitten bleibt abgelehnt, auch nach Wiederöffnung und erneutem Freischalten/Ablehnen.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/konten.py:991
  Evidence: Rückgabe `offen` löst in anmeldung.py (Aktion anfragen) betreiber_melden(k) einmal je Klick aus; test_bitte_nach_entzug_auf_mein_konto findet die Meldung anfrage_reisen beim Betreiber.
  Status: CONFIRMED

### Runde 2
**Adversary:** Randfälle, mit eigenem Probe-Skript (Scratchpad, nicht im Repo) gegen die echte Konten-Datenbank:
- Konto ohne Zeile: Bitte legt offen an (unverändert). OK.
- Freischalten ohne vorherige Bitte, Entzug, bitten: `offen`. OK.
- Wiederholtes Bitten bei offener Bitte: bleibt `offen`, genau eine Zeile, `erstellt` unverändert. OK.
- Wiederöffnen nach 3 Tagen: `erstellt` neu, `entschieden` leer. Erneutes Freischalten -> `schon_erlaubt`; erneuter Entzug -> wieder `offen`. OK.
- Abgelehnt nach Entzug-Zyklus: bleibt `abgelehnt`. OK.
- Unbekanntes Konto: KontoFehler wie zuvor. OK.
- Race: Lesen und UPDATE in einer Transaktion (`with closing(db()) as v, v`); die Rückkehr nach dem UPDATE ist konsistent, ein zweiter gleichzeitiger Aufruf sieht danach `offen` und meldet nicht erneut in der Funktion.
**Implementierer:** keine Gegenrede.

Anmerkung (kein Befund, vorbestehend): Die Seite verbirgt den Knopf bei offener Bitte; ein erneutes POST von `anfragen` bei offener Bitte (Replay) liefert `offen` und meldet erneut an den Betreiber. Das war schon vor #695 so (erste Bitte), die Spec verlangt „einmal“ je Wiederöffnen/Klick, nicht Entprellung. Nicht Teil des Auftrags.

Befunde: keine.

## Herkunft der Vorbedingungen

Kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Betroffenes Feld `anfragen.status = freigeschaltet`: Schreibstelle `freischalten(ja=True)` (engine/konten.py), Bedingung davor: Betreiber schaltet frei. Test für diesen Weg: test_nach_entzug_des_rechts_neu_bitten, test_bitte_nach_entzug_des_rechts, test_bitte_nach_entzug_auf_mein_konto.

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 81 passed, 0 failed, 0 übersprungen (test_konten, test_oauth, test_anmeldung); Gesamtlauf läuft in CI
Edge cases: alle geprüft, keiner gebrochen
Regressions: keine gefunden
Checklist: 5/5 Punkte bewiesen

## Geprüfte Dateien

- sha256:be9d615e4295efcec58cd11bfb990b1f8de0688a20dae668feaa3bd15d422e8d  engine/konten.py

## Prüfbasis

- base: 8c88b6e6c52c53899b71284ceb69547d3a498689
- blob:3814c6b7d48d0ff790073a5457aaf59fa2c7dd62  engine/konten.py
