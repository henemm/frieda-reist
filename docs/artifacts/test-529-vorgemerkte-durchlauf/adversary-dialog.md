# Adversary Dialog — test-529-vorgemerkte-durchlauf
Spec: docs/specs/betrieb/vorgemerkte-durchlauf-529.md
Datum: 2026-11-20 08:12

## Checkliste
- [x] **Input:** Eine Reise im Speicher steht bei Aufruf von `veroeffentlichen.sh` in der Liste von `konten.py vorgemerkt`.
- [x] **Output:** Ihre Seite ist entfernt, sie wird nicht gebaut (auch nicht mit `--immer`), Exit 0, Protokollzeile „<reise> is marked for deletion: page removed.“; andere Reisen laufen unberührt weiter. Nach dem Zurückholen baut der nächste Lauf sie wieder.
- [x] **Fehlerfall:** Ist die Liste nicht lesbar, Exit 1 mit Fehlerzeile, nichts wird gebaut, keine Seite entfernt.
- [x] **AC-1:** Given `stadtwochenende` ist vorgemerkt (neue Anordnung) / When Veröffentlichen läuft / Then Exit 0, die Seite ist entfernt, kein Deploy der Reise, Meldung „is marked for deletion: page removed.“ steht in der Ausgabe. Test: 1.
- [x] **AC-2:** Given eine zweite, nicht vorgemerkte Reise / When die vorgemerkte entfernt wird / Then bleibt die andere Reise unberührt. Test: 2.
- [x] **AC-3:** Given eine vorgemerkte Reise / When Veröffentlichen mit `--immer` läuft / Then wird sie weiterhin nicht gebaut, die anderen werden gebaut. Test: 3.
- [x] **AC-4:** Given die Vormerkung wird zurückgeholt / When der nächste Lauf folgt / Then wird die Reise wieder gebaut und ihre Seite ist wieder da. Test: 4.
- [x] **AC-5:** Given die Kontendatenbank ist unlesbar (neue Anordnung) / When Veröffentlichen läuft / Then Exit 1 mit Fehlerzeile, kein Deploy, keine Seite entfernt (fail closed). Test: 5.
- [x] **AC-6:** Given die alte Anordnung (`sp` mit Kontendatenbank) / When Veröffentlichen läuft / Then gelten dieselben Aussagen für Vormerkung (Seite weg, kein Bau, Exit 0) und für die unlesbare Datenbank (Exit 1, kein Bau, Seiten bleiben). Test: 6, 7.
- [x] **AC-7:** Given die neue Testdatei und `test_loeschen_reise.py` / When `engine/.venv/bin/python -m pytest -q engine/tests -n 3` läuft / Then ist alles grün, die Quelltextprüfung besteht unverändert, `betrieb/veroeffentlichen.sh` ist nicht geändert und die Tests brauchen keine echten Reisen.

## Dialog

### Runde 1
**Adversary:** Neue Testdatei und Skript gelesen. Skript unveraendert (Diff gegen origin/main im Ordner betrieb/ leer). Tests: 46 passed (neue Datei + test_loeschen_reise.py), Ausgabe in adversary-test-output.txt; volle Suite laut test-green-output.txt 3436 passed.
Mutationsprobe M1: Aufruf `vorgemerkte_entfernen || return 1` in main_klon (Z. 911) auskommentiert -> 4 Tests rot (neu_vorgemerkte_entfernt, neu_immer, neu_zurueckgeholte, neu_unlesbare_liste); alt-Tests und neu_andere bleiben gruen (erwartet).
Mutationsprobe M2: Aufruf im Lauf der alten Anordnung (Z. 1191) auskommentiert -> 2 Tests rot (alt_vorgemerkte, alt_unlesbare_liste).
Mutationsprobe M3: Fehlerzweig auf `return 0` entschaerft (kein Abbruch bei unlesbarer Liste) -> test_neu_unlesbare_liste_fail_closed und test_alt_unlesbare_liste_fail_closed rot.
Nach jeder Mutation Datei per checkout zurueckgesetzt; abschliessend Diff gegen origin/main in betrieb/ leer (SAUBER).
Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_vorgemerkte_durchlauf_529.py:84
  Evidence: Exit 0, Seite weg, kein Deploy, Meldung; rot unter M1.
  Status: CONFIRMED
Confirmation:
  AC: AC-1
  Code reference: betrieb/veroeffentlichen.sh:256
  Evidence: vorgemerkte_entfernen entfernt Webordner, gibt Meldung aus; Aufruf Z. 911 (main_klon).
  Status: CONFIRMED
Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_vorgemerkte_durchlauf_529.py:95
  Evidence: andere Reise behaelt daten.json, kein Deploy, keine Meldung fuer sie.
  Status: CONFIRMED
Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_vorgemerkte_durchlauf_529.py:107
  Evidence: --immer baut ANDERE, nicht VORGEMERKT; rot unter M1.
  Status: CONFIRMED
Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_vorgemerkte_durchlauf_529.py:120
  Evidence: nach Zurueckholen wird neu gebaut, Seite wieder da; rot unter M1.
  Status: CONFIRMED
Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_vorgemerkte_durchlauf_529.py:133
  Evidence: kaputte konten.db -> Exit 1, Fehlerzeile, keine Deploys, Seiten byteidentisch; rot unter M1 und M3.
  Status: CONFIRMED
Confirmation:
  AC: AC-5
  Code reference: betrieb/veroeffentlichen.sh:262
  Evidence: Fehlerzweig mit return 1 (fail closed); main_klon bricht mit `|| return 1` ab.
  Status: CONFIRMED
Confirmation:
  AC: AC-6
  Code reference: engine/tests/test_vorgemerkte_durchlauf_529.py:148
  Evidence: alte Anordnung: Vormerkung entfernt Seite, kein Deploy, Meldung; rot unter M2. Fail-closed-Test Z. 160 rot unter M2 und M3.
  Status: CONFIRMED
Confirmation:
  AC: AC-6
  Code reference: betrieb/veroeffentlichen.sh:1191
  Evidence: zweite Aufrufstelle im Lauf der alten Anordnung.
  Status: CONFIRMED
Confirmation:
  AC: AC-7
  Code reference: engine/tests/test_loeschen_reise.py:471
  Evidence: Quelltextpruefung unveraendert und gruen; keine /home-Pfade in Testdatei und Protokoll; nur beispielreise/stadtwochenende, Konto k-ida erfunden (example.invalid).
  Status: CONFIRMED


### Runde 2
**Adversary:** Nachbohren. (a) Schwache Assertion: test_neu_andere_reise_bleibt_unberuehrt besteht auch unter M1; er beweist nur Nichtbeeintraechtigung, die Entfernung deckt Test 1 (rot unter M1). (b) Deploy-Abwesenheit wird ueber Zaehlerstand in deploy.log geprueft, nicht ueber Texttreffer; robust. (c) Fail-closed-Tests laufen mit --immer und vorher gebauten Seiten und vergleichen Seiteninhalt vorher/nachher; ein Entfernen waere sichtbar. (d) Alte Anordnung nur mit --immer getestet; die Vormerkung greift vor dem Bauen unabhaengig davon (Z. 256ff). (e) Echte Reisen/absolute Pfade: keine. (f) Ohne Kontendatenbank liefert die Funktion 0 (Z. 262), laut Spec bewusst.
**Implementierer:** keine Einwaende.
Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/test_vorgemerkte_durchlauf_529.py:95
  Description: test_neu_andere_reise_bleibt_unberuehrt wuerde auch ohne Vormerkung bestehen (gruen unter Mutation M1).
  Spec requirement: AC-2 - andere Reise unberuehrt
  Conflict: Beweist allein nichts ueber die Vormerkung; zusammen mit Test 1 ausreichend. Kein Blocker.
  Remediation: Optional zusaetzlich pruefen, dass VORGEMERKT entfernt ist.


## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 46 passed, 0 failed (volle Suite 3436 passed), 0 uebersprungen
Mutationen M1/M2/M3 machen die zugehoerigen Tests rot; Skript danach unveraendert.
Edge cases: geprueft, nur LOW F001. Regressions: keine. Checklist: 10/10 proven.

## Geprüfte Dateien

- sha256:e72e5e8d0bfa97c0360aa66389f1fb6954dbe21be3b28d40222df6943c3fb0a3  betrieb/veroeffentlichen.sh
- sha256:dc5e6185b7454c6ab6a45d0c417bb787fdba43861707581278904dfee86065e6  engine/tests/test_loeschen_reise.py
- sha256:9165464496205bcccd600b11780f8354869c106a4a3184aefe40d35dfcd055e8  engine/tests/test_vorgemerkte_durchlauf_529.py

## Prüfbasis

- base: aa05ba66e0ed367f8348e8f4d8160c42287650bc
- blob:38059217e3b8340838708f17f6203cb290763dc1  betrieb/veroeffentlichen.sh
- blob:94ddc92bf348f108ef30d1f6268f63bd116e3ec8  engine/tests/test_loeschen_reise.py
- blob:86c0f9b1481164f75cce8fa7c4d5f549a6dbed3c  engine/tests/test_vorgemerkte_durchlauf_529.py

## Geprüfte Dateien

- sha256:e72e5e8d0bfa97c0360aa66389f1fb6954dbe21be3b28d40222df6943c3fb0a3  betrieb/veroeffentlichen.sh
- sha256:dc5e6185b7454c6ab6a45d0c417bb787fdba43861707581278904dfee86065e6  engine/tests/test_loeschen_reise.py
- sha256:9165464496205bcccd600b11780f8354869c106a4a3184aefe40d35dfcd055e8  engine/tests/test_vorgemerkte_durchlauf_529.py

## Prüfbasis

- base: aa05ba66e0ed367f8348e8f4d8160c42287650bc
- blob:38059217e3b8340838708f17f6203cb290763dc1  betrieb/veroeffentlichen.sh
- blob:94ddc92bf348f108ef30d1f6268f63bd116e3ec8  engine/tests/test_loeschen_reise.py
- blob:86c0f9b1481164f75cce8fa7c4d5f549a6dbed3c  engine/tests/test_vorgemerkte_durchlauf_529.py
