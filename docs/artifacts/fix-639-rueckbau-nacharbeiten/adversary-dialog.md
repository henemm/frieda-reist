# Adversary Dialog — fix-639-rueckbau-nacharbeiten
Spec: docs/specs/betrieb/rueckbau-nacharbeiten-639.md
Datum: 2026-11-23 13:48

## Checkliste
- [x] **AC-1:** Given `FR_ABLAGE` fällt mit dem Bauordner zusammen oder liegt darin / When `altbau_entfernen` läuft / Then bleibt alles erhalten, Warnzeile, Exit 0, kein Alarm. (Test 1, RB)
- [x] **AC-2:** Given `FR_KONTEN` oder `FR_KONNEKTOR` liegt im Bauordner / When `altbau_entfernen` läuft / Then bleibt alles erhalten, Warnzeile. (Test 2, RB; je Variable ein Fall)
- [x] **AC-3:** Given Exit 4 und keine Ausgabezeile nennt `<FR_SEITEN>/_bau` / When `umzug_fertig_im_klon` läuft / Then wird `fertig` gesetzt. (Test 3, RB)
- [x] **AC-4:** Given Exit 4 mit Nennung des alten Bauordners oder Exit außerhalb von 0, 3, 4 / When `umzug_fertig_im_klon` oder `altbau_entfernen` läuft / Then bleibt der Zustand, es wird nichts gelöscht. (Tests 4 und 5, RB)
- [x] **AC-5:** Given `FR_SEITEN` nicht betretbar / When `altbau_entfernen` läuft / Then kein Abbruch unter `set -e`, Exit 0. (Test 6, RB)
- [x] **AC-6:** Given die Zustandsdatei lässt sich nicht schreiben / When `umzug_fertig_im_klon` läuft / Then kein Abbruch unter `set -e`. (Test 7, RB)
- [x] **AC-7:** Given beide Funktionen / When sie die Units prüfen / Then nutzen beide dieselbe Hilfsfunktion `units_ohne_altbau` (Test: der Stub von `VF_UNITS` wird von beiden Läufen mit identischem Ergebnis ausgewertet, RB; zusätzlich Textprüfung, dass `units.py pruefen` nur in `units_ohne_altbau` aufgerufen wird).
- [x] **AC-8:** Given die Datenbank ist nicht lesbar / When `arten_uebernehmen` läuft / Then 503 `schreiben.dienst.speicher_nicht_erreichbar`, keine Wirkung, eine Protokollzeile. (Test 8, SP)
- [x] **AC-9:** Given kaputte fremde Ablage oder `OSError` / When `packliste_uebernehmen` läuft / Then 503 `speicher_nicht_erreichbar`, kein 500, keine Wirkung. (Test 9, SP)
- [x] **AC-10:** Given unbekannte Reise oder unbrauchbarer Inhalt / When `arten_uebernehmen` oder `packliste_uebernehmen` läuft / Then bleibt es bei der Ablehnung `.2` (kein Verhaltenswechsel für fachliche Fälle). (Test 10, SP)
- [x] **AC-11:** Given ein Ablagefehler / When `fremde_datei` aufgerufen wird / Then wirft sie `FremdNichtLesbar`; der Text nennt nicht die eigene Reise als Fehlerort. (Test 11, SP)
- [x] **AC-12:** Given die Änderungen / When `docs/betrieb.md` und der Kommentar der Vorlage gelesen werden / Then kommt „Bauordner mit `.git`“ nicht mehr vor, Schutzbedingungen nennen Ablage, Konten und Konnektor. (Textprüfung in RB)
- [x] **AC-13:** Given die vollständige Testsuite / When sie läuft / Then ist sie grün (`engine/.venv/bin/python -m pytest -q -n 3 engine/tests`), `ALARMSTELLEN` und die Textkataloge sind unverändert, und die Instanz-Tests laufen vor dem Vorspulen mit dem Branch ohne Fehler (Hinweis: 503 statt 422 im Speicherfehlerfall).

## Dialog

### Runde 1
**Adversary:** Zielgerichtete Tests ausgeführt: `pytest engine/tests/test_rueckbau_557.py engine/tests/test_schreiben_speicher.py -k 639` ergibt 26 passed. Erweiterte Läufe (Rückbau, Speicher, Betrieb, Texte) 367 passed, gespeichert in `docs/artifacts/fix-639-rueckbau-nacharbeiten/adversary-test-output.txt`. Volle Suite des Implementierers: 3538 passed (test-green-output.txt). Keine Übersprungenen.

Confirmation:
  AC: AC-1
  Code reference: betrieb/veroeffentlichen.sh:872
  Evidence: Die Schleife über die geschützten Pfade nimmt `${FR_ABLAGE:-}` auf; `case "$fremd/" in "$real"/*` fängt Gleichheit und Enthaltensein; nur Warnzeile, `return 0`. Test test_639_altbau_schuetzt_ablage_konten_konnektor[FR_ABLAGE-gleich/darin] grün (kein Alarm geprüft über `_hoch`).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: betrieb/veroeffentlichen.sh:873
  Evidence: `${FR_KONTEN:-}` und `${FR_KONNEKTOR:-}` in derselben Schleife; je Variable ein parametrisierter Fall grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: betrieb/veroeffentlichen.sh:825
  Evidence: `case 0|3|4` lässt Exit 4 durch, danach nur Prüfung der Ausgabe auf `$FR_SEITEN/_bau`; umzug_fertig_im_klon (Zeile 839) setzt fertig. Test test_639_umzug_fertig_bei_reiner_gesperrter_abweichung grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: betrieb/veroeffentlichen.sh:826
  Evidence: Exit außerhalb 0/3/4 gibt `return 1`; Ausgabe mit `_bau` gibt Rückgabe 1 (Zeile 826). Beide Aufrufer brechen mit `return 0` ab (Zeile 839 und Warnzeile 892 bis 894), nichts wird gelöscht oder geschrieben. Tests exit4_nennt_bau, exit1 (Umzug) und test_639_altbau_bleibt_bei_units_exit_1 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: betrieb/veroeffentlichen.sh:866
  Evidence: `seiten_real=... || { altbau_warnen ...; return 0; }`; Test überschreibt `cd` unter `set -euo pipefail` und prüft Exit 0, "WEITER 0", `_bau` bleibt.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: betrieb/veroeffentlichen.sh:840
  Evidence: `{ echo fertig > .neu && mv ...; } 2>/dev/null || return 0`; Test mit Ordner an Stelle der Zustandsdatei: Lauf grün, genau ein Ping.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/veroeffentlichen.sh:819
  Evidence: `units.py pruefen` wird nur in units_ohne_altbau (Zeile 824) aufgerufen; grep nach `pruefen` außerhalb von Kommentaren zeigt keine weitere Stelle für units; Textprüfung-Test grün; beide Funktionen rufen die Hilfsfunktion (Zeilen 839, 892).
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:5825
  Evidence: sqlite3.Error geht durch fremde_datei (Zeilen 5164 bis 5169 fangen es nicht) bis anwenden und wird von speicher_fehler als 503 speicher_nicht_erreichbar mit stderr-Zeile "Store ... 503" beantwortet; Zielreise unverändert (Stand vorher gleich nachher). Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/schreiben.py:5168
  Evidence: OSError, AblageFehlt, AblageFehler werden zu FremdNichtLesbar, anwenden antwortet 503; kein 500 (kein re-raise), Fall ablage_fehlt/ablage_fehler/oserror je für beide Werkzeuge grün. Die Abfrage `isinstance(..FremdNichtLesbar)` steht vor `ist_ablage_fehler`, die eigene Reise wird nicht als Fehlerort genannt.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/schreiben.py:5166
  Evidence: `except (KeyError, UnicodeDecodeError): return None`; die Aufrufer (Zeile 4751, 5184) lehnen mit .2 ab; Tests unbekannt/kein_text liefern 422 `.2` ohne Wirkung.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/schreiben.py:5151
  Evidence: FremdNichtLesbar-Text ist `{von}/{rel}: ...`, nennt die fremde Reise; Test mit echter beschädigter/fehlender Ablagedatei grün und prüft, dass "stadtwochenende" nicht im Text steht.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: docs/betrieb.md:572
  Evidence: grep nach "Bauordner mit" in docs/betrieb.md und der Vorlage: keine Treffer. Der Absatz Aufräumen (Zeile 574) nennt Ablage, Konten und Konnektor. Dokumentänderung Schreibziele in Zeile 384.
  Status: CONFIRMED

Confirmation:
  AC: AC-12 (Vorlage)
  Code reference: betrieb/vorlagen/schreiben.service:9
  Evidence: Kommentar nennt jetzt "Software-Klon (#454) mit seinen Git-Daten"; nur Kommentarzeile geändert, keine Unit-Direktive (Diff geprüft), also kein Abgleich-Effekt für units.py.
  Status: CONFIRMED

Confirmation:
  AC: AC-13 (Repo-Teil)
  Code reference: engine/tests/test_schreiben_speicher.py:632
  Evidence: Volle Suite 3538 passed. `git status` zeigt engine/tests/test_betrieb.py und engine/texte_*.py unverändert (ALARMSTELLEN und Textkataloge unberührt); neue Texte nicht nötig, vorhandener Schlüssel speicher_nicht_erreichbar. Testkorrektur in test_schreiben_speicher.py: AblageFehlt/AblageFehler erhalten das zweite Konstruktorargument `summe` (reisespeicher.py:98/106 verlangt `(pfad, summe)`); die Prüfung ist nicht abgeschwächt, der alte `is None`-Assert wurde durch das strengere `pytest.raises(FremdNichtLesbar)` ersetzt, die Aussagen zu 503, Werten und Stand blieben. Instanz-Tests vor dem Vorspulen: noch offen (Schritt des Orchestrators).
  Status: CONFIRMED

Randfälle geprüft (Skriptprobe mit set -euo pipefail): FR_ABLAGE/FR_KONTEN/FR_KONNEKTOR ungesetzt und leer: kein Abbruch, `[ -n "$fremd" ] || continue` überspringt; Lauf erreicht die Units-Prüfung. Ausgabe der Prüfung mit `<FR_SEITEN>/_bau-schreiben-1`: gilt als Nennung und hält auf (konservativ, siehe F001).

**Implementierer:** keine Antwort (isolierte Prüfung).

### Runde 2
**Adversary:** Zweiter Durchgang gegen Regressionen und Rückfälle. (a) Aufrufer von fremde_datei: Zeile 4751 (arten_uebernehmen) und 5184/5185 (packliste_uebernehmen) liegen unter Schreiber.schreiben und damit in `anwenden`; kein weiterer Aufrufer ausserhalb (grep). (b) `anwenden` fängt FremdNichtLesbar vor `ist_ablage_fehler`; keine Doppelbehandlung, die eigene Reise wird nicht als Ablageort gemeldet. (c) sqlite3.Error geht unverändert durch (kein Wrapping), Protokollzeile über speicher_fehler. (d) set -e: `|| units_ohne_altbau_rc=$?` bewahrt den Exitcode; `local aus` getrennt von der globalen Rückgabe-Variable, kein Konflikt mit `local rc` (Variable `rc` entfiel sinnvoll aus altbau_entfernen; `rc` bleibt als local deklariert und wird weiter unten benutzt, Tests laufen grün). (e) Exit 3 setzte früher den Umzug nicht auf fertig, jetzt schon: von der Spec gewollt (0, 3, 4), Test deckt Exit 4 und 1, Exit 3 durch die gemeinsame case-Zeile. (f) Symlink-Pfade in der Units-Ausgabe: Prüfung ist Teilstring auf `$FR_SEITEN/_bau` wie zuvor, keine neue Schwäche. (g) Der Fehlerpfad der Zustandsdatei lässt eine Rest-Datei `.neu` zurück, harmlos.

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:826
  Description: Die Prüfung `[[ "$aus" != *"$FR_SEITEN/_bau"* ]]` ist ein Teilstring und trifft auch `_bau-schreiben-*` und beliebige Pfade mit diesem Präfix; ebenso nennt die Warnzeile bei Exit 0 "units still point to" (irreführend, wenn nur die Ausgabe etwas nennt).
  Spec requirement: AC-4 — nur die Nennung des alten Bauordners hält auf
  Conflict: Falsch-Positive halten Umzugsabschluss/Aufräumen nur auf (fail-safe, nie fälschlich löschen); entspricht dem Verhalten vor #639 (`*"$bau"*`). Kein Verstoß, nur Hinweis.
  Remediation: Optional später auf Pfadgrenze prüfen; nicht für dieses Issue nötig.

**Implementierer:** keine Antwort (isolierte Prüfung).

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Geprüfte Änderungsdateien (Abdeckung)

Confirmation:
  AC: AC-12
  Code reference: engine/schreiben.py:5825
  Evidence: required-files nennt engine/schreiben.py; Änderung geprüft (FremdNichtLesbar, fremde_datei, anwenden).
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/tests/test_schreiben_speicher.py:632
  Evidence: Testkorrektur geprüft, nichts abgeschwächt.
  Status: CONFIRMED

## Verdict

VERDICT: VERIFIED
Tests: 26 gezielt + 367 erweitert + 3538 volle Suite bestanden, 0 fehlgeschlagen, 0 übersprungen
Edge cases: geprüft, nichts gebrochen (F001 nur LOW-Hinweis)
Regressions: keine gefunden
Checklist: 13/13 Punkte bewiesen (AC-13 für den Repo-Teil; Instanz-Tests vor dem Vorspulen offen)

## Geprüfte Dateien

- sha256:0500f261a3a80973881bb5788b236596418c8a7f467a1807132d8363d0d4aeec  betrieb/veroeffentlichen.sh
- sha256:3a47d76866ec15828fb922adef7c4a5c3e477e180c27a9d89901b9923276f249  betrieb/vorlagen/schreiben.service
- sha256:902f54f91f8430922fb14c7c898fc5300c466d49441d8ae9a58a8e8a0c584d0f  docs/betrieb.md
- sha256:ed8444b01fae95b5d4938560b54eab5e3ce4c75f29d6fd76386a91c3e6ec6ae4  engine/schreiben.py
- sha256:2bb6fb134993ad8450c8c906d442115c2048149c75f5d8da4b399294a070b40b  engine/tests/test_schreiben_speicher.py

## Prüfbasis

- base: 148e0d64bed7fbba296e06c4bc30e73d09ff2a0b
- blob:6705227182d1b05ed9c6847cb11a560738ed2f3a  betrieb/veroeffentlichen.sh
- blob:dd47c294996fa358946a5c991a5c665f7746e658  betrieb/vorlagen/schreiben.service
- blob:f14bd2de0e083f6c46d0c420683537e67d48f962  docs/betrieb.md
- blob:5f4de251c04db4480de0bce5d863f258c92850c2  engine/schreiben.py
- blob:6d2da4222f988233cc0d4ed21791f7352a817fd5  engine/tests/test_schreiben_speicher.py

## Geprüfte Dateien

- sha256:0500f261a3a80973881bb5788b236596418c8a7f467a1807132d8363d0d4aeec  betrieb/veroeffentlichen.sh
- sha256:3a47d76866ec15828fb922adef7c4a5c3e477e180c27a9d89901b9923276f249  betrieb/vorlagen/schreiben.service
- sha256:902f54f91f8430922fb14c7c898fc5300c466d49441d8ae9a58a8e8a0c584d0f  docs/betrieb.md
- sha256:ed8444b01fae95b5d4938560b54eab5e3ce4c75f29d6fd76386a91c3e6ec6ae4  engine/schreiben.py
- sha256:2bb6fb134993ad8450c8c906d442115c2048149c75f5d8da4b399294a070b40b  engine/tests/test_schreiben_speicher.py

## Prüfbasis

- base: 148e0d64bed7fbba296e06c4bc30e73d09ff2a0b
- blob:6705227182d1b05ed9c6847cb11a560738ed2f3a  betrieb/veroeffentlichen.sh
- blob:dd47c294996fa358946a5c991a5c665f7746e658  betrieb/vorlagen/schreiben.service
- blob:f14bd2de0e083f6c46d0c420683537e67d48f962  docs/betrieb.md
- blob:5f4de251c04db4480de0bce5d863f258c92850c2  engine/schreiben.py
- blob:6d2da4222f988233cc0d4ed21791f7352a817fd5  engine/tests/test_schreiben_speicher.py
