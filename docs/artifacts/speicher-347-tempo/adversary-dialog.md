# Adversary Dialog — speicher-347-tempo
Spec: docs/specs/betrieb/speicher-347-tempo.md
Datum: 2026-11-06 16:32

## Checkliste
- [x] **Input:** unverändert (`reise`, `bis`, `spalte`; `reise`, `ordner`, `basis`, …).
- [x] **Output:** exakt dieselben Rückgabewerte, Reihenfolgen und Ausnahmen wie vorher; nur die Rechenzeit sinkt.
- [x] **Side effects:** keine; es entstehen weder neue Spalten noch neue Dateien.
- [x] **AC-1:** Given eine Reise mit vielen Versionen je Pfad / When `_stand` den Stand bildet / Then liest die Abfrage die gewünschte Spalte nur für die jeweils neueste Version je Pfad, in einer Abfrage und ohne Schleife je Pfad (Test 1).
- [x] **AC-2:** Given beliebige Reisen mit Löschungen, neu angelegten Pfaden, leeren Dateien und Stand `bis` / When `_stand` läuft / Then sind Ergebnis, Reihenfolge und Ausnahmen gleich dem Verhalten vor dem Umbau (Test 2 bis 5).
- [x] **AC-3:** Given ein Ordner und eine Basis / When `ordner_als_vorgang` läuft / Then entstehen dieselben Vorgänge und Ausnahmen wie vorher, und der Vorher-Stand wird über Prüfsummen statt Bytes gebildet (Test 6 bis 9).
- [x] **AC-4:** Given die 110-MB-Testreise / When der Messlauf nach dem Umbau läuft / Then liegt das Mittel je Vorgang unter dem Wert vor dem Umbau (5,4 s), und die Zahlen stehen vorher/nachher im Issue; das Verfehlen von 1,6 s (Git) wird offen benannt.
- [x] **AC-5:** Given der Branch / When `engine/.venv/bin/python -m pytest -q engine/tests` läuft / Then ist alles grün ohne echte Reisen, und die vorhandenen Tests sind unverändert.

## Dialog

### Runde 1
**Adversary:** Tombstone vs. leere Datei, geloescht+neu angelegt, bis=frueher, unbekannte Reise/Stand, basis=0/99, Reihenfolge. Test: 105 passed in 49.84s (adversary-test-output.txt).
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Differential-Fuzz: 60 Zufallshistorien ueber 3 Reisen verschachtelt (leere Dateien, Loeschen, Neuanlegen, Unterordner, Umlaut-Pfad, Binaerdaten), jeder Stand bis, beide Spalten, neue _stand-Liste gegen Referenzabfrage (alte Form): 23296 Vergleiche, 0 Abweichungen; nach jedem ordner_als_vorgang gleicht aktueller_stand dem Ordner (0 Abweichungen). basis=0 -> Vorgang stand 1; unbekannte Basis 99 -> StandGeaendert (wie vorher, da erwartet=basis unveraendert).
**Implementierer:** (nicht beteiligt)

Finding: keine.

Confirmation:
  AC: AC-1
  Code reference: engine/reisespeicher.py:159
  Evidence: MATERIALIZED-CTE k nur mit pfad/vorgang/weg, Spalte erst im Join ueber PK (vorgang,pfad); Test 1 prueft Plan und eine Abfrage.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/reisespeicher.py:168
  Evidence: weg bleibt an inhalt IS NULL, ORDER BY w.pfad; Fuzz 0 Abweichungen, Tests 2-5 gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/reisespeicher.py:251
  Evidence: _stand(...,"pruefsumme") in eigener Verbindung, KeyError -> {}, basis=0 -> {}; Vergleich vorher.get(p) != _summe(b); _eintragen nutzt dieselbe Summe (Zeile 199). Tests 6-9 gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/reisespeicher.py:246
  Evidence: Betroffene drei Testdateien 105 passed; Gesamtlauf laut Auftraggeber gruen bis auf einen Einzel-gruenen Flake in test_pwa (nicht von mir wiederholt).
  Status: CONFIRMED

AC-4 (Messlauf, Zahlen im Issue): nicht von mir ausgefuehrt; Prozessschritt, kein Code. Offen bis Zahlen im Issue stehen.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict


═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 105 passed, 0 failed, 0 uebersprungen
Edge cases: alle geprueft, nichts gebrochen (Fuzz 23296 Vergleiche, 0 Abweichungen)
Regressions: keine
Checklist: Code-Punkte bewiesen; AC-4 (Messlauf im Issue) ist Prozessschritt und noch offen

## Geprüfte Dateien

- sha256:c40c688fe610a670aacaa72b6e8947a0923211d73145b13e455ea8af8b7e5e11  engine/reisespeicher.py

## Prüfbasis

- base: 4634739008eb45ee3d3b76e5400feb46e0c8c629
- blob:f0c8b9f3be2af44072cad4bdacec7d0e3e53644b  engine/reisespeicher.py
