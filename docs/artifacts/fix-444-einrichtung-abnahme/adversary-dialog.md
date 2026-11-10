# Adversary Dialog — fix-444-einrichtung-abnahme
Spec: docs/specs/betrieb/einrichtung-abnahme-444.md
Datum: 2026-11-10 09:23

## Checkliste
- [x] **Input:** Instanz mit gesetzter Region, Testreisen.
- [x] **Output:** Eigener Dienst läuft bei Bedarf, antwortet innerhalb von 10 Sekunden, ruht ohne Container, Rückfall auf den öffentlichen Dienst bleibt.
- [x] **Side effects:** Docker-Image und Datenbank (2 GB) auf dem Server; ein Teil-Check in `monitor.sh`.
- [x] **AC-1:** Given Region gesetzt / When `einrichten.sh` und Einspielen laufen / Then existiert `abdeckung.json` mit der Fläche der Balearen und eine echte Abfrage antwortet.
- [x] **AC-2:** Given Wanderung innerhalb der Fläche / When `map_points_fetch` mit Wasserstellen läuft / Then Treffer mit Quelle, Datenstand und Hinweis auf den eigenen Dienst innerhalb von 10 Sekunden auch beim Kaltstart (gemessen 2 s); zweiter Aufruf ersetzt statt zu verdoppeln; zweite Kategorie ebenso.
- [x] **AC-3:** Given Städtewochenende / When die Abfrage läuft / Then Ablehnung wie bisher oder Antwort des öffentlichen Dienstes (beides gilt als bestanden, solange die Abfrage nicht am eigenen Dienst hängt) am eigenen Dienst.
- [x] **AC-4:** Given 15 min ohne Aufruf / When `docker ps` geprüft wird / Then kein Container und kein Proxy-Prozess; der nächste Aufruf startet beides wieder.
- [x] **AC-5:** Given gestoppter eigener Dienst / When eine Abfrage läuft / Then Rückfall auf den öffentlichen Dienst mit dessen Ergebnis oder Fehlermeldung.
- [x] **AC-6:** Given der Teil-Check / When er läuft / Then meldet er Warnung ab 40 Tagen Alter von `abdeckung.json`, sonst grün; ein Lauf ist belegt.
- [x] **AC-7:** Given Abschluss / When aufgeräumt ist / Then `~/overpass-test` und der Testcontainer sind weg; Nachweis steht in #444, #240 und `docs/artifacts/`; `engine/tests/test_protokolle_ohne_pfade.py` ist grün.

## Dialog

### Runde 1
**Adversary:** Prüft den Live-Zustand selbst, ohne dem Nachweis zu glauben: abdeckung.json, echte Abfrage, Einheiten, Ruhezustand im Journal, Teil-Check grün/rot/ohne Datei, Aufräumen, Nachweis ohne Pfade.
**Implementierer:** Nachweis in docs/artifacts/fix-444-einrichtung-abnahme/test-green-output.txt; Abnahme AC-1 bis AC-7 am laufenden Dienst, Teil-Check in henemm-infra#418.
Code reference: engine/schreiben.py:2318 (geprüfter Abrufweg kartenpunkte_holen, unverändert)
**Ergebnis:** AC-1 bis AC-7 AKZEPTIERT. 43 Treffer, Datenstand 2026-11-08; Ruhezustand im Journal belegt (Stopp 09:20:59 UTC, Neustart 09:21:20 UTC); Teil-Check 0 Tage grün, 50 Tage rot, ohne Datei grün; Testaufbau entfernt; test_protokolle_ohne_pfade grün.

### Runde 2
**Adversary:** Nachfrage zu AC-2, AC-3, AC-5: nur über den Nachweis belegt, nicht live wiederholbar ohne Eingriff.
**Implementierer:** AC-2/3/5 stammen aus Läufen an erfundenen Beispielreisen im Wegwerf-Ordner (Ausgaben im Nachweis); AC-5 zusätzlich durch die Software-Tests der Haupt-Spec (62 Tests grün). Kein Defekt gefunden.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

## Geprüfte Dateien

- sha256:da6a01e5c6aac6a515eecd7059d00a25eddd11919c8717cd875bbadad4fe0d68  engine/schreiben.py

## Prüfbasis

- base: 00944e08591409fd6a4adfac29afd61832cbb291
- blob:07fe8a6f39c56ff22b46357003106ebeb1339bc1  engine/schreiben.py

## Geprüfte Dateien

- sha256:da6a01e5c6aac6a515eecd7059d00a25eddd11919c8717cd875bbadad4fe0d68  engine/schreiben.py

## Prüfbasis

- base: 00944e08591409fd6a4adfac29afd61832cbb291
- blob:07fe8a6f39c56ff22b46357003106ebeb1339bc1  engine/schreiben.py
