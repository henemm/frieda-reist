# Adversary Dialog — fix-669-bruecke-netzfehler
Spec: docs/specs/fast/fix-669-bruecke-netzfehler.md
Datum: 2026-11-27 18:01

## Checkliste
- [x] AC-1: Ist der Konnektor nicht erreichbar, antwortet die Brücke auf jede Anfrage mit `-32603` und der ID der Anfrage; Benachrichtigungen bleiben ohne Antwort; Exit-Code 0, kein Traceback.
- [x] AC-2: Ein Netzfehler mitten im Lauf ergibt eine Fehlerantwort; die Brücke läuft weiter und leitet nach Wiederkehr des Konnektors wieder weiter.
- [x] AC-3: Nach einem Netzfehler beim Start wird die Kontoprüfung vor der nächsten Weiterleitung nachgeholt; erst danach wird weitergeleitet. Gehört der Zugang einem anderen Konto, bricht die Brücke auch dann ohne Weiterleitung ab. test_bruecke_bricht_nach_netzfehler_beim_start_bei_anderem_konto_ab
- [x] AC-4: Scheitert die Token-Erneuerung, antwortet die Brücke mit `-32603` und läuft weiter; kein Token in der Ausgabe.
- [x] AC-6: Antwortet der Konnektor bei der Kontoprüfung (beim Start oder nachgeholt) mit einem Serverfehler 5xx, etwa 502 hinter nginx während eines Neustarts, gilt das wie ein Netzfehler: Fehlerantwort `-32603`, Prüfung bleibt ausstehend, nichts wird weitergeleitet, die Brücke läuft weiter. Andere Antworten (4xx, 200 ohne Ergebnis) brechen wie bisher ab. (Befund F001 der Prüfung zu #669.)
- [x] AC-5: Abbruch bei falschem Konto oder Betreiber, Abbruch bei fehlender Ablage oder fehlendem Instanzwert sowie das Erneuern bei Ablauf und bei 401 bleiben unverändert.

## Dialog

### Runde 1
**Adversary:** Neuprüfung nach Commit db626fc. `pytest engine/tests/test_testzugang.py`: 23 passed, 0 failed, 0 übersprungen. Jede AC gegen den Code geprüft, dazu Fake-Konnektor-Proben (502, 403, 502 mit Erholung, 502 bei Weiterleitung, fremdes Konto).
Confirmation:
  AC: AC-1
  Code reference: betrieb/testzugang.py:350
  Evidence: Startprüfung über `_voruebergehend` (329-339); Netzfehler (OSError, HTTPException, Serverfehler; Zeile 60) werden zu -32603 mit ID, Benachrichtigung per continue ohne Antwort, Exit 0. Test grün.
  Status: CONFIRMED
Confirmation:
  AC: AC-2
  Code reference: betrieb/testzugang.py:334
  Evidence: Fehler mitten im Lauf gefangen, Schleife läuft weiter; Probe 'recover' leitet nach Wiederkehr wieder weiter.
  Status: CONFIRMED
Confirmation:
  AC: AC-3
  Code reference: betrieb/testzugang.py:324
  Evidence: `weiterleiten` prüft nach, solange `geprueft` False (320 setzt es erst nach bestandener Prüfung). Probe 'wrong': fremdes Konto -> Exit 1, Server sah nur `initialize`, keine Weiterleitung; Probe '502': Server sah nur initialize, nie die Nutzlast.
  Status: CONFIRMED
Confirmation:
  AC: AC-4
  Code reference: betrieb/testzugang.py:271
  Evidence: `ErneuernFehler` -> -32603 (338-339) ohne Token/Pfad; Sperre im finally freigegeben. Probe: kein 'SECRET' in Ausgabe oder stderr in allen Läufen.
  Status: CONFIRMED
Confirmation:
  AC: AC-5
  Code reference: betrieb/testzugang.py:306
  Evidence: 4xx und 200 ohne result bleiben `Abbruch` (Probe 403: Exit 1, 'Connector check failed (initialize, HTTP 403)'); fremdes Konto/Betreiber Abbruch (316/319); fehlende Ablage/Instanzwert vor der Schleife; Erneuern bei Ablauf/401 unverändert. Bestehende Tests grün.
  Status: CONFIRMED
Confirmation:
  AC: AC-6
  Code reference: betrieb/testzugang.py:303
  Evidence: `s >= 500` -> `Serverfehler` (56-57), in NETZFEHLER und zusätzlich vor ihm in `_voruebergehend` gefangen (334-335). Probe 502 beim Start: Exit 0, beide Anfragen -32603 mit ID, Prüfung bei jeder Anfrage wiederholt (4x initialize), nichts weitergeleitet. Probe 'recover': nach 502 -> Prüfung besteht -> Weiterleitung. Reihenfolge der Checks: 5xx wird vor der 4xx/result-Prüfung (305) erkannt, 4xx unberührt.
  Status: CONFIRMED
**Implementierer:** (nicht beteiligt)

### Runde 2
**Adversary:** Gezielte Randfälle zu AC-6.
- 5xx bei normaler Weiterleitung (Prüfung bereits bestanden): `frage` wird nur in der Prüfung benutzt, `senden` reicht den Status durch; Probe 'fwd502': Exit 0, -32603 'Connector answered HTTP 502' mit ID, Benachrichtigung ohne Antwort, Brücke läuft weiter. Unverändert gegenüber vorher.
- Serverfehler mitten in der zweiten Prüfungsstufe (tools/list 5xx): ebenfalls `Serverfehler`, `geprueft` bleibt False, Wiederholung ab initialize. Fail-closed.
- Fehlertext des Serverfehlers enthält nur den Status (304), kein Antwortkörper, keine Tokens.
- Batch (F002) und ungültiges JSON von /token (F003) bleiben laut Koordinator bewusst außerhalb; F003 wird eigenes Issue. Nicht erneut als blockierend gewertet.
Finding:
  ID: F004
  Severity: LOW
  Category: anti_pattern
  Code reference: betrieb/testzugang.py:60
  Description: `Serverfehler` erbt von Exception und steht in `NETZFEHLER`, der Kommentar nennt 'nicht erreichbar'; der except-Zweig für Serverfehler (334) steht vor dem allgemeinen. Funktional korrekt, nur leicht redundant.
  Spec requirement: AC-6
  Conflict: keiner, nur Stil.
  Remediation: optional, Serverfehler aus NETZFEHLER nehmen, da eigener except-Zweig existiert.
**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`).

## Verdict

VERDICT: VERIFIED
AC-1 bis AC-6 bewiesen (23 Tests grün, Proben bestätigen), F001 behoben, keine Regression gefunden; F002/F003 bewusst außerhalb, F004 nur Stil.

## Geprüfte Dateien

- sha256:8b6ace9a7ffad5e82a71482b9262e09cb12f0c20392985f7b728eccdcf7305f3  betrieb/testzugang.py

## Prüfbasis

- base: a68152bbe13e413fabf4418eca6c50ba2a07702b
- blob:31c53e06ff7d9f136decced9b686433b375b66ac  betrieb/testzugang.py
