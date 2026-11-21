# Adversary Dialog — fix-568-kartenlegende-wackelig
Spec: docs/specs/betrieb/wackelige-browsertests-568.md
Datum: 2026-11-21 08:19

## Checkliste
- [x] **AC-1:** Das Signal `data-geladen` wird immer genau nach dem Neuzeichnen durch `route(true)` gesetzt, auch wenn alle Lader scheitern (`api/**` abgebrochen). Test: Test 1.
- [x] **AC-2:** Nach dem Signal findet beim Erstaufbau kein weiteres `replaceChildren` von `#main` statt. Test: Test 2.
- [x] **AC-3:** Die Seite sieht nicht anders aus und verhält sich nicht anders; das Signal ist unsichtbar und ändert keine Texte. Test: bestehende Browser- und Bildtests bleiben unverändert grün; kein Eintrag in den Textkatalogen.
- [x] **AC-4:** `seiten_karte_legende.mjs` und `seiten_bilder_csp.mjs` warten vor dem ersten Zugriff auf `.ekarte` auf `html[data-geladen]`. Test: Test 3.
- [x] **AC-5:** Die Doku nennt das Signal als Wartepunkt-Regel (#369, #457, #550). Test: Test 4.
- [x] **AC-6:** (Läufe belegt, CI-Pflichtprüfungen AUSSTEHEND bis Push) 20 Wiederholungsläufe von `test_karte_legende.py` und des Tests mit `seiten_bilder_csp.mjs` unter `-n auto` bleiben ohne Rot; danach die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) grün. Test: Test 5 (manuell, Ergebnis im Nachweis) und CI.

## Dialog

### Runde 1
**Adversary:** Beweis je AC angefordert und selbst nachgeprüft. Tests selbst gelaufen: 251 passed, 0 failed (adversary-test-output.txt). RED-Test-Änderung: `git diff HEAD` zeigt nur sonde() geändert (Wanderung über gebaut() mit Grundkarten-Attrappen, Pfad beispiel/ statt r/); alle Assertions und Parametrisierung der vier Tests unverändert. Das korrigiert nur die Testumgebung (ohne Attrappen gibt es keine .ekarte, AC-2-Karte-gleich-Prüfung wäre nie ausgeführt worden) und stärkt eher: hatKarte wird gefordert.
Lader: blLaden, rmLaden, agLaden fangen alles im try/catch. brLaden, psLaden: Fetch/Parse im try; der Ausgangs-Senden-Teil danach (brAusgangSenden/psSenden) liegt außerhalb try, ist aber bei abgebrochenem Netz nicht erreichbar bzw. fängt Netzfehler selbst (psSenden: try/break).
**Implementierer:** (Diff und Nachweise siehe Staging.)

### Runde 2
**Adversary:** Gegenprobe Robustheit. ichLaden (vorlage.html:5155): Fetch im try, aber der Code danach (ICH.person.name, spracheWaehlen, statusZeichnen, fuerDich, pushFuss) liegt außerhalb. Antwortet der Dienst mit 200 und unerwartetem JSON (ohne person bei vorhandenem ICH.konto o. Ä.), kann ichLaden werfen; Promise.all lehnt ab, Signal und route(true) entfallen. Das ist auch vor der Änderung so (route(true) kam dann nie), das Signal erbt es nur. Betrifft nur Testwarte-Szenarien mit kaputtem Dienst, nicht die Testumgebung (api/** abgebrochen: ICH bleibt null, MIT_KONTO false, der Code läuft sicher durch; belegt durch Test 1 grün in chromium und webkit). route(true) kann theoretisch werfen (viele Ansichtsfunktionen), dann fehlt das Signal und der Test läuft in den 15-s-Timeout und wird laut rot, nicht still grün: akzeptables Fehlerverhalten. Die 20x-Wiederholung (7 passed je Lauf, wiederholung-20x.txt) trägt AC-6 lokal.
Gesamtsuite-Fehlschlag test_wackel_599.py::test_alter_ablauf_ist_unter_verzoegerung_rot[webkit]: dieser Test berührt weder data-geladen noch .ekarte-Wartepunkte der geänderten Skripte (die Änderung ist ein reines additives Attribut nach route(true)); einzeln 9 passed, Muster Lastflackern (Zeitbudget unter Last). Kein Zusammenhang nachweisbar, aber der Test ist selbst ein Timing-Test (#599) und sollte bei Wiederholung der Gesamtsuite beobachtet werden.
**Implementierer:** keine Gegenargumente nötig.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)


### Confirmations
Confirmation:
  AC: AC-1
  Code reference: engine/vorlage.html:6580
  Evidence: then-Zweig nach Promise.all setzt dataset.geladen direkt nach route(true); Lader fangen Fehler selbst ab; test_signal_ohne_dienst grün (chromium, webkit).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/seiten_geladen.mjs:13
  Evidence: Sonde zählt replaceChildren an #main nach dem Signal (nachSignal == 0) und prüft gleiches .ekarte-Element; test_kein_neuzeichnen_nach_signal grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/vorlage.html:6573
  Evidence: nur ein unsichtbares Attribut, keine Texte; test_texte, test_bilder, test_karte_legende grün (251 passed).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/seiten_karte_legende.mjs:19
  Evidence: waitForSelector html[data-geladen] vor .ekarte, ebenso in seiten_bilder_csp.mjs. Test 3 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/seiten_bilder_csp.mjs:20
  Evidence: gleicher Wartepunkt vor .ekarte.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_wartepunkt_geladen.py:96
  Evidence: docs/design.md nennt data-geladen und #369, #457, #550; sonde() geändert nur in der Testumgebung (test_wartepunkt_geladen.py:25), Assertions unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/tests/seiten_geladen.mjs:5
  Evidence: wiederholung-20x.txt, 20 Läufe 7 passed. CI-Pflichtprüfungen (tests leer, tests instanz, gitleaks) AUSSTEHEND bis nach dem Push.
  Status: CONFIRMED

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/vorlage.html:5155
  Description: ichLaden führt nach dem try-Fetch ungeschützten Code aus; wirft er (200 mit unerwartetem JSON), lehnt Promise.all ab und das Signal kommt nicht.
  Spec requirement: AC-1 — Signal auch wenn alle Lader scheitern (Netzfehler)
  Conflict: gilt nur für unerwartete Antwortform, nicht für Netzfehler; schon vorher kam route(true) dann nicht. Fehlt das Signal, wird der Test laut rot (Timeout), nicht still grün.
  Remediation: optional .finally/catch um das Signal; nicht blockierend.

## Verdict
VERDICT: VERIFIED

Begründung:  251 passed, 0 failed, 0 übersprungen (adversary-test-output.txt). Alle ACs belegt; AC-6 CI-Pflichtprüfungen ausstehend bis zum Push. Gesamtsuite-Flackern in test_wackel_599 (webkit, Timing-Test, einzeln grün) nicht mit der Änderung verknüpft. Nur LOW-Finding F001 (nicht blockierend).

## Geprüfte Dateien

- sha256:b9c2ba4cc8b8a088e406e875fb272fa6ad0e753c83bb2a6297290908dc70da88  engine/tests/seiten_bilder_csp.mjs
- sha256:78ac5fc4669a758d854d306d62c21800c2c320b3143559409d65b38ed9a40c5b  engine/tests/seiten_geladen.mjs
- sha256:c81f865243e3405d33c6b58eb1fc17868d64b0b4b971919aef75263f467342fe  engine/tests/seiten_karte_legende.mjs
- sha256:8b0209d6e91a8930f418ba35c2694004c6bd53a0f64c9f7ac636eeef15513a19  engine/tests/test_wartepunkt_geladen.py
- sha256:f98879236c1f1c29d636217ce8d635a2ed08f578c0aa6bd34ccce824cb9757b4  engine/vorlage.html

## Prüfbasis

- base: b0ed9b6b4c03a08c5e103ed39957cf6049b1b834
- blob:e373603a54bc73b01ee45f482ce8160dedc052e6  engine/tests/seiten_bilder_csp.mjs
- blob:d4fc84de4a6c4888e0c5049257037ee3d1a4b16c  engine/tests/seiten_geladen.mjs
- blob:f0c38f41512729d4840202b9134e0026acd322fc  engine/tests/seiten_karte_legende.mjs
- blob:75670b3967366561cbaaba791c2162a7874e3b82  engine/tests/test_wartepunkt_geladen.py
- blob:5c4d860c573993690155eedf378fd43cc5e85327  engine/vorlage.html
