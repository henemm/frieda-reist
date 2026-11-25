# Adversary Dialog — fix-656-vorab-ordner-faden
Spec: docs/specs/fast/fix-656-vorab-ordner-faden.md
Datum: 2026-11-25 15:19

## Checkliste
- [x] **AC-1:** Given im Fall `[frist]` beginnt der Export des Fadens erst nach der Antwort 504, when der Block der Hilfe verlassen ist, then hat dieser Export geendet, und `tmp-osm` ist leer. (Ohne die Hilfe ist dieser Fall bei jedem Lauf rot.)
- [x] **AC-2:** Given ein Faden, der erst nach einer Weile endet, when der Block der Hilfe verlassen wird, then geschieht das erst nach dessen Ende.
- [x] **AC-3:** Given ein Faden, der nicht in der Zeitgrenze endet, when der Block verlassen wird, then scheitert die Hilfe mit einer Meldung, die den Namen des Fadens nennt.
- [x] **AC-4:** Given eine Prüfung im Block scheitert, when der Block verlassen wird, then wird trotzdem auf die Fäden gewartet, und der ursprüngliche Fehler bleibt der gemeldete.
- [x] **AC-5:** Given die vier Fälle und die übrigen Tests der Datei, when sie laufen, then sind sie grün, und `tmp-osm` ist nach jedem der vier Fälle leer.

## Dialog

### Runde 1
**Adversary:** Voller Lauf `engine/tests/test_schreiben.py -n 3`: 163 passed, 0 failed, 0 übersprungen (adversary-test-output.txt). `git diff main` zeigt keine Änderung an engine/schreiben.py und engine/reisespeicher.py; `exist_ok` kommt in der Datei nicht vor. Gegenbeweis durch Veränderungen in einer Kopie im Scratchpad (Mutationen der Hilfe):
- M1 (Hilfe nur `yield`): rot sind `[frist]` (Zeile 2851, Aussage `begonnen == []` bzw. Folgeprüfung), AC-2-, AC-3-, AC-4-Test. Dreimal wiederholt: `[frist]` jedes Mal rot, die drei anderen Fälle grün. Unverändert dreimal grün. => AC-1 (ohne Hilfe bei jedem Lauf rot) bewiesen.
- M4 (nur einmal prüfen statt warten): AC-2, AC-4 und `[frist]` rot.
- M5 (Hilfe wirft bei hängendem Faden nicht): AC-3 rot.
- M3 (kein Warten im Fehlerpfad): AC-4 rot (`geendet == [1]`).
- M2 (kein Zusatz am Fehler): AC-4 rot (Notiz fehlt).
**Implementierer:** Richtigstellung zu M1 (nachgetragen vom Orchestrator, drei eigene Läufe mit der Hilfe als bloßem `yield`): `[frist]` scheitert jedes Mal in Zeile 2858 (`assert [] == [1]`, der Export hat noch nicht begonnen), nicht in 2851 oder an `begonnen == []` (2852). Die Aussage zu AC-1 bleibt.

### Runde 2
**Adversary:** Schwachstellen gesucht. (a) M7 (Pause `time.sleep(0.3)` in `nach_der_antwort` auf 0): Test bleibt grün. Die Pause ist also nicht tragend; tragend ist `beantwortet.wait(20)`, das den Export bis nach der Antwort anhält. Nur der Kommentar „sicher schon vorbei“ übertreibt, keine Lücke. (b) Reihenfolge: das Warten steht im Testrumpf (Zeile 2849), pytest setzt monkeypatch und löscht tmp_path erst danach; `beantwortet.set()` steht im `finally` vor dem Verlassen, daher kein Selbstblockieren, auch wenn `anwenden_extern` wirft. (c) Fäden von vorher werden ausgenommen (AC-3-Test prüft das). (d) Fäden, die während des Blocks starten und enden, werden nie gesehen, was nötig ist. Ein Faden, der kurz vor dem Prüfen neu startet, wird durch die Schleife ohne `join` erfasst. (e) `tmp-osm` leer: Zeile 2859 nach dem Warten in allen vier Fällen, im vollen Lauf grün. (f) Alte Prüfungen (Abruf-Ordner gesehen, Code je Ausgang, `frieda-osm-*` leer) stehen unverändert; der Test `…_auch_nach_zu_langer_vorbereitung_weg` ist unverändert und grün.
Kleinere Befunde (nicht blockierend): F001 LOW, Kommentar in Zeile 2840 übertreibt (siehe M7). F002 LOW, `time` wird in der Hilfe lokal importiert, Stilfrage.
**Implementierer:** F001: Die Pause betrifft nur den Fall ohne Abwarten (dort hält sie den Export sicher hinter dem Ende des Tests); mit der Hilfe ist sie erwartungsgemäß ohne Einfluss, M7 hat nur diesen Fall geprüft. Bleibt. F002: lokaler Import wie in den übrigen Tests der Datei. Bleibt.

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_schreiben.py:2840
  Evidence: Export des Fadens wartet auf `beantwortet` (nach 504); `begonnen == geendet == [1]` (2858) und `tmp.iterdir() == []` (2859) nach dem Block (2849); Mutation M1 macht `[frist]` dreimal rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_schreiben.py:2774
  Evidence: Test wartet auf zwei verschachtelte Fäden (0,3 s je), Reihenfolge `["erster","zweiter"]`; M1 und M4 machen ihn rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_schreiben.py:2536
  Evidence: Hilfe wirft `AssertionError` mit den Fadennamen (nur neue Fäden); Test 2779ff prüft Namen und Ausschluss des Fadens von vorher; M5 und M1 machen ihn rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_schreiben.py:2804
  Evidence: Fehler im Block: Warten, ursprünglicher ValueError bleibt, Hängemeldung als Zusatz (`add_note`, 2536); M1, M2, M3 machen den Test rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_schreiben.py:2859
  Evidence: Voller Lauf 163 passed; `tmp.iterdir() == []` nach jedem der vier Fälle; schreiben.py und reisespeicher.py unverändert.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 163 passed, 0 failed, 0 übersprungen
Edge cases: geprüft, keine gebrochen (zwei LOW-Hinweise: F001, F002)
Regressions: keine
Checklist: 5/5 points proven

## Geprüfte Dateien

- sha256:c1b96781cf91c6bce15e10bcc723bdee40c0ae548fd84d2d28769e43c78a846e  engine/tests/test_schreiben.py

## Prüfbasis

- base: bfc80f8330509a2b6c12beb51b4be47715a6499c
- blob:dcc9600b22272c33e43eff8d52d2ed3d5cd8fec0  engine/tests/test_schreiben.py
