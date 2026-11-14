# Adversary Dialog — fix-567-kartendienst-diagnose
Spec: docs/specs/betrieb/kartendienst-diagnose-567.md
Datum: 2026-11-14 09:52

## Checkliste
- [x] Scheitert der eigene Kartendienst (Fehler, nicht erreichbar, Nicht-JSON, Antwort ohne `elements`), steht im Dienst-Journal genau eine Zeile mit dem Grund; die Abfrage wird weiter wie bisher vom öffentlichen Dienst beantwortet.
- [x] Antwortet der eigene Dienst gültig (auch mit leerer Trefferliste), entsteht keine Zeile.
- [x] Wird der Dienstwahl-Test noch einmal rot, zeigt die Meldung beide Anfragelisten, den gewählten Dienst und die Protokollzeile; das nächste Rot ist damit erklärbar.
- [x] Nach `schliessen()` läuft kein Faden des Stummels `Kaputt` mehr.
- [x] **AC-1 (Fehler):** Given der eigene Kartendienst antwortet mit Fehler oder ist nicht erreichbar / When `overpass_holen` läuft / Then steht genau eine Protokollzeile `Own map service failed (<Fehlerart>: <Text>), falling back to public` auf stderr, einzeilig, auf `LOG_LAENGE` gekürzt, ohne Adresse; Rückgabe und Rückfall sind wie bisher
- [x] **AC-2 (Antwort ohne elements):** Given der eigene Dienst antwortet gültig ohne Liste `elements` / When `overpass_holen` läuft / Then steht genau die Zeile `Own map service answered without elements, falling back to public`
- [x] **AC-3 (Erfolg ohne Zeile):** Given der eigene Dienst antwortet gültig / When `overpass_holen` läuft / Then entsteht keine Zeile über den eigenen Dienst
- [x] **AC-4 (Stummel endet):** Given der Stummel `Kaputt` / When `schliessen()` aufgerufen wird / Then ist sein Faden danach nicht mehr am Leben und die Leseschleife endet bei `recv() == b""`
- [x] **AC-5 (Diagnose im Dienstwahl-Test):** Given der Dienstwahl-Test wird rot / When die Zusicherung scheitert / Then zeigt die Meldung beide Anfragelisten, `a["text"]` und das eingefangene stderr; die Zusicherungen selbst bleiben unverändert (keine Wiederholung, kein Lockern)
- [x] **AC-6 (Spec 444):** Given `docs/specs/betrieb/eigener-kartendienst-444.md` / When die Änderung steht / Then nennt AC-6 dort zusätzlich, dass der Rückfall eine Protokollzeile mit Grund hinterlässt
- [x] **AC-7 (Verhalten unverändert):** Given die bestehenden Tests zu Rückfall, Teilfrist und Gesamtfrist (AC-5 bis AC-7 der Spec 444) / When der Stand läuft / Then sind sie unverändert grün


## Dialog

### Runde 1
**Adversary:** Alle 11 Punkte gegen Quelltext und Lauf geprüft. Tests: `-n 3` auf test_kartendienst.py und test_schreiben.py: 224 passed; 3 Folgeläufe `-k "kartendienst or kartenpunkte" -n 4`: je 79 passed; test_protokolle_ohne_pfade.py: 2 passed (Output: adversary-test-output.txt). Der Diff von engine/schreiben.py gegen den Hauptstand zeigt nur die zwei neuen Protokollzeilen und das `as e`; beide `return None` und der Erfolgs-Rückgabewert sind unverändert.

Confirmation:
  AC: AC-1
  Code reference: engine/schreiben.py:2274
  Evidence: Ausnahmepfad schreibt genau eine Zeile `Own map service failed (<Art>: <Text>), falling back to public`, Leerraum zusammengezogen, Text auf LOG_LAENGE gekürzt; `return None` unverändert. overpass_eigen wird in overpass_holen (Zeile 2249) höchstens einmal aufgerufen, daher auch bei Teil-/Gesamtfrist genau eine Zeile. Tests test_rueckfall_fehlerantwort_, _nicht_erreichbar_, _http_fehler_und_kein_json grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/schreiben.py:2281
  Evidence: Antwort ohne Liste elements schreibt exakt `Own map service answered without elements, falling back to public`; Test prüft Gleichheit der Zeilenliste.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/schreiben.py:2279
  Evidence: Erfolgszweig gibt ohne Schreiben zurück, auch bei leerer Liste; test_erfolg_schreibt_keine_protokollzeile (200, leer) grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_kartendienst.py:339
  Evidence: schliessen() ruft shutdown(SHUT_RDWR), close() und join(timeout=3); laufen() bricht bei recv()==b"" ab; accept() wirft OSError und der Faden kehrt zurück. test_kaputt_beendet_faden_nach_schliessen (wartet_in_accept, leere_verbindung) grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_schreiben.py:2973
  Evidence: diagnose() liefert eigen.anfragen, oeffentlich.anfragen, a.get("text") und das stderr von capfd; die Zusicherungen (code, ok, Anzahl der Anfragen) sind laut Diff des Test-Commits unverändert, nur Meldungen ergänzt. Die Meldung wird nur bei Rot ausgewertet, kein Nebeneffekt im Grünfall.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: docs/specs/betrieb/eigener-kartendienst-444.md:168
  Evidence: AC-6 ergänzt um "der Rückfall hinterlässt eine Protokollzeile mit Grund auf stderr, ohne Adresse des Dienstes (#567)".
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/tests/test_kartendienst.py:254
  Evidence: test_fehler_des_eigenen_dienstes_faellt_zurueck (220), test_teilfrist_und_gesamtfrist (254) und alle übrigen Bestandstests laufen grün (224/224).
  Status: CONFIRMED

Die vier Expected-Behavior-Punkte sind durch AC-1/2 (Punkt 1), AC-3 (Punkt 2), AC-5 (Punkt 3) und AC-4 (Punkt 4) belegt.

**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Gezielte Angriffe.

1. Adresse in der Zeile: Der Test prüft nur die Stummel-Adressen. Probe mit fehlerhaft konfigurierter Adresse (overpass_eigen mit "kaputt-adresse/x") ergibt `Own map service failed (ValueError: unknown url type: 'kaputt-adresse/x'), ...`; mit Leerzeichen ebenso `InvalidURL: ... 'exa mple.invalid'`. Verbindungsfehler (Refused, Name not known) enthalten keine Adresse. Siehe F001.
2. Zeilenlänge: nur der Fehlertext wird auf LOG_LAENGE gekürzt (Muster wie "Prefetch kartenpunkte_holen", Zeile 5550), die Gesamtzeile ist bis zu 200 plus 49 Zeichen lang. Der Test akzeptiert genau diese Toleranz; die Spec-Formulierung "höchstens LOG_LAENGE" in Test 1 ist wörtlich enger. Siehe F002.
3. Mehrzeilige Fehlertexte, Tabs, doppelte Leerzeichen: durch split() abgefangen; Test prüft das.
4. Genau eine Zeile bei Teil-/Gesamtfrist: overpass_holen ruft overpass_eigen einmal, Fehlerzweige und Erfolgszweig schließen sich aus.
5. Kaputt-Faden in accept(): shutdown auf einem lauschenden Socket weckt accept() unter Linux mit OSError; Test belegt es. Andere Systeme nicht geprüft (OSError wird gefangen, join hat Frist, Daemon-Faden).
6. Wackeln: 3 Folgeläufe plus Gesamtlauf ohne Rot.
7. Regression: einziger Aufrufer von overpass_eigen ist overpass_holen; kein Aufrufer wertet stderr aus.
**Implementierer:** (nicht beteiligt)

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/schreiben.py:2276
  Description: Der Fehlertext der Ausnahme wird unverändert übernommen; bei fehlerhaft konfigurierter Adresse (ValueError "unknown url type", InvalidURL) steht die Adresse in der Zeile.
  Spec requirement: AC-1 — ohne Adresse des Dienstes
  Conflict: Nur bei Fehlkonfiguration, nicht in den spezifizierten Fällen (Fehler, nicht erreichbar, Nicht-JSON); das Journal sieht nur der Betreiber.
  Remediation: Optional die Adresse aus dem Text entfernen oder in der Spec als bekannte Grenze vermerken.

Finding:
  ID: F002
  Severity: LOW
  Category: spec_violation
  Code reference: engine/schreiben.py:2276
  Description: LOG_LAENGE kürzt nur den Fehlertext, die ganze Zeile ist bis zu 49 Zeichen länger.
  Spec requirement: AC-1 — auf LOG_LAENGE gekürzt
  Conflict: Wörtlich enger als umgesetzt, aber identisch zum Vorbild kartenpunkte_vorab und vom Test ausdrücklich so toleriert.
  Remediation: Keine nötig; Spec-Satz bei Gelegenheit auf "Fehlertext auf LOG_LAENGE gekürzt" präzisieren.

Datei-Abdeckung:
  Code reference: engine/schreiben.py:2267
  Code reference: engine/tests/test_kartendienst.py:399
  Code reference: engine/tests/test_schreiben.py:2989

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Tests: 224 passed, 0 failed, 0 übersprungen (gezielt); 3 Folgeläufe je 79 passed; Pfadtest 2 passed
Edge cases: zwei LOW-Beobachtungen (F001, F002), keine Spec-Verletzung in den spezifizierten Fällen
Regressions: None found, Rückgabewerte gleich dem Hauptstand
Checklist: 11/11 points proven

## Geprüfte Dateien

- sha256:69cd56f1c5855ae101e80834381921adbfd74dc88c7c61c72d5c84d1c65b1bc1  docs/specs/betrieb/eigener-kartendienst-444.md
- sha256:e92c84aeb9111d23e509f7d60988dd59c9db84bfb60d9bca8128d0c36e967486  engine/schreiben.py
- sha256:25e698dda9dcaf997f262693c9f625db4f3533bc8b0e10c61d3902708a1f7e7e  engine/tests/test_kartendienst.py
- sha256:92453f4a6686f31d02ecc63cf4e67a66971d522bba346a6142015aeb75528f30  engine/tests/test_schreiben.py

## Prüfbasis

- base: f8f9ba7948887921c44edf2b87e9fc283381a87c
- blob:3298f3b65fc01f9754561924f3d6ca3ee2385ba7  docs/specs/betrieb/eigener-kartendienst-444.md
- blob:b79965cf105136c6f513e23f28825e093dd3583c  engine/schreiben.py
- blob:3e10b140a9689564c2d4ebf5195bd27f0974507e  engine/tests/test_kartendienst.py
- blob:a8fd13342fc76894e656fd5bcf3d74f39945fca3  engine/tests/test_schreiben.py
