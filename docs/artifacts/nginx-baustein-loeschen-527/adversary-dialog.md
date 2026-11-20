# Adversary Dialog — nginx-baustein-loeschen-527
Spec: docs/specs/betrieb/nginx-baustein-loeschen-527.md
Datum: 2026-11-19 21:41

## Checkliste
- [x] **Input:** Eine Reise steht im Löschprotokoll, ihr Baustein `<instanz>-<reise>.conf` liegt noch im Snippet-Ordner.
- [x] **Output:** Der nächste Lauf von Veröffentlichen mit Root-Rechten entfernt den Baustein über den Helfer, nginx ist geladen; Protokollzeile „Block removed: <reise>“.
- [x] **Side effects:** Ein Reload von nginx je entfernte Reise (gesichert und mit Rückweg). Ohne Root-Rechte im Lauf: Hinweiszeile, der Timer holt es nach.
- [x] **AC-1:** Given Reisen im Löschprotokoll und in der Schonfrist / When `konten.py entfernt` läuft / Then listet es nur die Reisen des Löschprotokolls, eine je Zeile, ohne Datenbank nichts. Test: 1.
- [x] **AC-2:** Given eine entfernte Reise mit liegendem Baustein und Root-Rechten / When Veröffentlichen läuft / Then wird der Helfer mit `--entfernen` und dem Reisenamen auf stdin aufgerufen und die Zeile „Block removed“ steht im Protokoll; der Baustein einer Reise in der Schonfrist bleibt. Test: 2.
- [x] **AC-3:** Given eine entfernte Reise ohne Baustein-Datei / When Veröffentlichen läuft / Then wird weder der Helfer noch `sudo` aufgerufen. Test: 3.
- [x] **AC-4:** Given ein Lauf ohne Root-Rechte / When der Schritt läuft / Then wird nichts verändert, eine Hinweiszeile steht im Protokoll, der Lauf bleibt grün und der nächste Lauf mit Root holt es nach. Test: 4.
- [x] **AC-5:** Given der Helfer endet mit Ausgang 3 bis 6 / When der Schritt läuft / Then steht eine Warnzeile mit Grund im Protokoll, der Bau läuft weiter, es entsteht kein `high`-Alarm, der nächste Lauf versucht es erneut; bei Ausgang 2 bleibt es still. Test: 5, 6.
- [x] **AC-6:** Given ein ungültiger Reisename im Löschprotokoll / When der Schritt läuft / Then wird er übersprungen und der Helfer nicht aufgerufen. Test: 7.
- [x] **AC-7:** Given die Liste ist nicht lesbar / When der Schritt läuft / Then Warnzeile ohne Abbruch des Laufs. Test: 8.
- [x] **AC-8:** Given der Skripttext / When er geprüft wird / Then steht der Schritt an beiden Aufrufstellen direkt nach `vorgemerkte_entfernen`. Test: 9.
- [x] **AC-9:** Given Doku und Docstring / When sie gelesen werden / Then beschreiben sie den neuen Ablauf, und der alte Satz „Baustein bleibt (Root-Rechte)“ fehlt. Test: 10.
- [x] **AC-10:** Given die bestehenden Tests / When `engine/.venv/bin/python -m pytest -q engine/tests -n 3` läuft / Then ist alles grün, `ALARMSTELLEN` ist unverändert, `test_nginx_reise_helfer.py` und die Tests zu #381 bestehen. Test: 11.
- [x] **AC-11 (Ausnahme laut Spec, vom Product Owner am 20.11.2026 freigegeben: Nachweis auf der Instanz nach Auslieferung im Issue #527, nicht in CI prüfbar):** (Instanz, Teil von „fertig“) Given die Software ist auf der Instanz / When eine eigene Testreise endgültig entfernt wird / Then ist ihr Baustein nach dem nächsten Lauf von Veröffentlichen weg, `nginx -t` ist grün und der Reload hat stattgefunden. Ausnahme mit Begründung: braucht nginx und Root auf dem echten Server und läuft nicht in CI; der Nachweis steht ohne Serverpfade im Issue #527 (Uhrzeiten mit Zeitzone).

## Dialog

### Runde 1
**Adversary:** Testlauf: `test_nginx_baustein_loeschen_527.py`, `test_betrieb.py`, `test_nginx_reise_helfer.py`: 258 bestanden, 0 fehlgeschlagen, 0 übersprungen (adversary-test-output.txt); volle Suite laut test-green-output.txt grün. Angriffe auf den Schritt `entfernte_bausteine`:
1. Namen mit Leerzeichen/Glob-Zeichen: `for r in $liste` ohne Quoting expandiert Globs. Die Liste kommt aus der Spalte `reise` der Kontendatenbank (Namen werden beim Anlegen über das Reisenamen-Muster geprüft); selbst ein `*` würde nur Dateinamen des Arbeitsordners liefern, die erst das Muster `^[a-z0-9][a-z0-9-]{1,39}$` passieren müssten, und der Helfer prüft das Muster ein zweites Mal. Kein Weg zu Pfadausbruch (kein `/`, `..` durch das Muster ausgeschlossen). Kein Defekt, nur Härtungsmöglichkeit.
2. `FR_SUDO` leer: `${FR_SUDO-sudo -n}` ohne Doppelpunkt nimmt gesetzt-aber-leer als „kein sudo“, wie `root_geht` (Code reference: betrieb/veroeffentlichen.sh:105 und :296). Ungesetzt: `sudo -n`. Konsistent.
3. Helfer nicht ausführbar/fehlt: `[ ! -x "$helfer" ]` ergibt Warnzeile, kein Abbruch. Geprüft.
4. `set -euo pipefail` (betrieb/veroeffentlichen.sh:86): Die Abfragen laufen als `|| hrc=$?` bzw. `|| {...}`, daher kein Abbruch. Ausnahme: `fehler_datei="$(mktemp)"` ohne Absicherung; schlägt mktemp fehl (Platte voll, TMPDIR fehlt), bricht der ganze Lauf ab, entgegen „immer Rückgabe 0“. Siehe F001 (LOW, sehr unwahrscheinlich; derselbe Lauf braucht mktemp ohnehin an anderen Stellen).
5. Reise in Schonfrist UND Löschprotokoll: `entfernt` liest nur das Löschprotokoll (Code reference: engine/konten.py:1724); ein Eintrag im Protokoll bedeutet endgültig entfernt, Baustein darf weg. Ein Rückspielen einer alten Sicherung mit wieder auftauchender Reise: Wächter entfernt sie erneut, kein Konflikt, nur ein späteres freischalten würde den Baustein neu anlegen.
6. Ohne Datenbank: Frühausstieg in Skript und `konten.py` (leere Ausgabe). `FR_INSTANZ` fehlt: wäre unter `set -u` schon vorher im Lauf fatal, kein neuer Fehlerpfad.
7. Meldeweg: Der Schritt nutzt nur `echo`, kein `fr_melden`; keine `high`-Stelle, `ALARMSTELLEN` unverändert (test_betrieb.py grün).
8. Pfade: Protokolle und Artefakte enthalten keine absoluten Home-Pfade (grep: 0 Treffer).
**Implementierer:** (nicht beteiligt, Isolation)

### Runde 2
**Adversary:** Zweite Runde gegen Wiederholung und Reihenfolge. Aufruf an beiden Stellen direkt nach `vorgemerkte_entfernen` (Code reference: betrieb/veroeffentlichen.sh:912 und :1192), nach dessen Erfolg (`|| return 1` davor); der neue Schritt ist selbst nie fatal außer F001. Helfer-Ausgang 2 bleibt still (Zeile 305), Ausgang 0 meldet „Block removed“ (Zeile 304), alle anderen Warnung mit Grund; stderr wird in eine Datei umgeleitet und auf eine Zeile gekürzt, `rm -f` immer. Wiederholbarkeit: liegt die Datei noch, wird der nächste Lauf erneut versucht (kein Zustandsmerker nötig). Die Docstrings (Code reference: engine/waechter.py:430 und :453) beschreiben den neuen Ablauf, der alte Satz fehlt (Test 10 grün). Wächter selbst unverändert in der Logik, nur Docstrings. Bei jedem 5-Minuten-Lauf mit Löschprotokoll wächst die Schleife linear, je Reise ein `[ -e ]`, vernachlässigbar. Keine weiteren Brüche gefunden.
**Implementierer:** (nicht beteiligt, Isolation)

## Findings und Confirmations

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:297
  Description: `fehler_datei="$(mktemp)"` ist unter `set -euo pipefail` ungeschützt; scheitert mktemp, endet der gesamte Lauf, obwohl der Kopfkommentar „immer Rückgabe 0“ zusagt.
  Spec requirement: AC-5 — Fehler des Schritts brechen den Bau nicht ab
  Conflict: Nur bei kaputtem Temp-Ordner, dann ohnehin ein Ausfall; kein Reisedaten-Risiko.
  Remediation: `fehler_datei="$(mktemp)" || { echo "Warning: ..."; return 0; }` (optional).

Confirmation:
  AC: AC-1
  Code reference: engine/konten.py:1724
  Evidence: Befehl `entfernt` gibt nur `loeschprotokoll()` aus, liest nur; Test 1 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: betrieb/veroeffentlichen.sh:296
  Evidence: Aufruf des Helfers mit `--entfernen`, Name auf stdin, Zeile „Block removed“ (:304); Schonfrist-Reisen nicht in der Liste; Test 2 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: betrieb/veroeffentlichen.sh:289
  Evidence: `[ -e "$datei" ] || continue` steht vor `root_geht`, also kein sudo/Helfer; Test 3 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: betrieb/veroeffentlichen.sh:290
  Evidence: Ohne Root Hinweiszeile und `continue`, Rückgabe 0; Test 4 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: betrieb/veroeffentlichen.sh:303
  Evidence: `case "$hrc"`: 0 Meldung, 2 still, sonst Warnzeile mit Grund; kein fr_melden; Tests 5, 6 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: betrieb/veroeffentlichen.sh:287
  Evidence: Regex-Prüfung vor jedem Aufruf; Test 7 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/veroeffentlichen.sh:283
  Evidence: Scheitert `konten.py entfernt`, Warnzeile und `return 0`; Test 8 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: betrieb/veroeffentlichen.sh:1192
  Evidence: Aufruf direkt nach `vorgemerkte_entfernen` in `main` (:1192) und `main_klon` (:912); Test 9 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/waechter.py:453
  Evidence: Docstrings (:430, :453) und Dokumente beschreiben den neuen Ablauf; alter Satz fehlt; Test 10 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/waechter.py:430
  Evidence: Nur Docstrings in waechter.py geändert; 258 Tests der drei Dateien grün, volle Suite grün (test-green-output.txt), ALARMSTELLEN unverändert.
  Status: CONFIRMED

AC-11: offen, Instanznachweis in Phase 7/8 (nicht in CI möglich, kein Defekt).

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 258 passed, 0 failed, 0 übersprungen (drei Zieldateien); volle Suite grün
Edge cases: geprüft; nur F001 (LOW, optional)
Regressions: None found
Checklist: AC-1 bis AC-10 bewiesen; AC-11 offen (Instanznachweis)

## Geprüfte Dateien

- sha256:e72e5e8d0bfa97c0360aa66389f1fb6954dbe21be3b28d40222df6943c3fb0a3  betrieb/veroeffentlichen.sh
- sha256:d4eb9cdfeae01c923811f7a0cb7347752490e9c20546573607b4566ea3df4ae0  engine/konten.py
- sha256:2627f002c7955e1c9eb846981c43f53bad3d2333ee732bc38ab3bf440fce3bf1  engine/waechter.py

## Prüfbasis

- base: 8f88356b5c3947d48dacd6a4a75a99a9d7bace51
- blob:38059217e3b8340838708f17f6203cb290763dc1  betrieb/veroeffentlichen.sh
- blob:c774cb10c97919d8f3a64f42d18b1962b984b8e0  engine/konten.py
- blob:a846f3c7126a68ee2e88f03d5bdd5539352acca9  engine/waechter.py

## Geprüfte Dateien

- sha256:e72e5e8d0bfa97c0360aa66389f1fb6954dbe21be3b28d40222df6943c3fb0a3  betrieb/veroeffentlichen.sh
- sha256:d4eb9cdfeae01c923811f7a0cb7347752490e9c20546573607b4566ea3df4ae0  engine/konten.py
- sha256:2627f002c7955e1c9eb846981c43f53bad3d2333ee732bc38ab3bf440fce3bf1  engine/waechter.py

## Prüfbasis

- base: 8f88356b5c3947d48dacd6a4a75a99a9d7bace51
- blob:38059217e3b8340838708f17f6203cb290763dc1  betrieb/veroeffentlichen.sh
- blob:c774cb10c97919d8f3a64f42d18b1962b984b8e0  engine/konten.py
- blob:a846f3c7126a68ee2e88f03d5bdd5539352acca9  engine/waechter.py
