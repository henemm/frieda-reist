# Adversary Dialog — fix-584-rolle-kosten-einmal
Spec: docs/specs/betrieb/rolle-kosten-einmal-584.md
Datum: 2026-11-20 19:53

## Checkliste
- [x] **AC-1:** Given in `plan/arten.yaml` trägt mindestens ein Merkmal einer Art (in `merkmale` oder `buchung_merkmale`) eine Rolle aus `routen.ROLLEN` / When `nachziehen` läuft / Then setzt es an keiner Art `rolle: kosten` und meldet nichts dazu.
- [x] **AC-2:** Given keine Art trägt eine Rolle (Altstand vor dem Rollen-Konzept) / When `nachziehen` läuft / Then setzt es `rolle: kosten` an `preis` (Typ geld) jeder Aufenthalts-Art, mit der unveränderten Meldung „arten.yaml <art>: attribute preis gets rolle kosten“, und ein zweiter Lauf meldet nichts mehr.
- [x] **AC-3:** Given eine Kopie der Beispielreise oder des Stadtwochenendes / When `nachziehen` läuft / Then bleiben alle Dateien byte-gleich (nicht nur Bilder).
- [x] **AC-4:** Given die bewusst rollenlose Herberge der Beispielreise / When `nachziehen` läuft / Then behält ihr Merkmal `preis` keine Rolle.
- [x] **AC-5:** Given die Änderung ist umgesetzt / When man Docstring und Testkommentare liest / Then beschreibt der Docstring von `nachziehen` die neue Bedingung, und der Hinweis auf die offene Umstellung „herberge: rolle kosten“ in `test_umstellung_267.py` sowie der Verweis auf #584 in `test_bilder.py` sind entfernt.
- [x] **AC-6:** Given der Stand ist fertig und lokal grün / When er auf `main` vorgespult werden soll / Then laufen vorher die Tests des Reisen-Repos der Instanz mit diesem Stand; rot darf nur sein, was schon vorher rot war.

## Dialog

### Runde 1
**Adversary:** Beweis je AC verlangt. Gezielte Tests: 240 passed (docs/artifacts/fix-584-rolle-kosten-einmal/adversary-test-output.txt). Sonde hat_rollen mit leerem/None arten, unbekannter Rolle, Rolle als Liste/bool, merkmale None, Art None, Merkmal None, Rolle "" / "keine": überall False, kein Absturz (engine/neu.py:1049-1059; Prüfung isinstance str und in ROLLEN). Rolle nur in buchung_merkmale: True. Kopie von Beispielreise und Stadtwochenende: nachziehen meldet [] und alle Dateien byte-gleich.
**Implementierer:** (nicht beteiligt, Kontextisolierung)

### Runde 2
**Adversary:** Nachbohren: Probelauf schreiben=False und nachziehen_speicher. Der Block ändert nur bei geaendert and schreiben (engine/neu.py:1141-1157); nachziehen_speicher ruft nachziehen(ordner, betrieb=False) (engine/neu.py:1291), gleiche Logik. Tests test_rolle_kosten_am_altstand_probelauf_schreibt_nicht und test_rolle_in_buchung_merkmalen_zaehlt sind grün. Fehlende arten.yaml: Block durch exists()-Abfrage übersprungen. Altstand-Zweig unverändert (Meldungstext gleich, zweiter Lauf still, da dann Rolle vorhanden). Docstrings neu.py angepasst; Hinweise in test_umstellung_267/test_bilder laut Diff entfernt. Instanz-Tests selbst nachgeprüft: 3 passed. Unbekannte Rolle (z. B. "quatsch") zählt nicht als Rolle, damit bleibt ein Altstand mit Müllwert umstellbar; konsistent mit der Spec (ROLLEN). Spec-konformer Restfall (einzige kosten bewusst entfernt) ist dokumentiert.
**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Findings

Keine Findings (kein Fehler gefunden).

### Confirmations
Confirmation:
  AC: AC-1
  Code reference: engine/neu.py:1049
  Evidence: hat_rollen prüft merkmale und buchung_merkmale; bei True ist die Schleife leer (engine/neu.py:1145); Test test_rolle_kosten_nicht_bei_reise_mit_rollen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/neu.py:1145
  Evidence: Altstand ohne Rollen: Regel und Meldung unverändert, zweiter Lauf still; test_nachziehen_nur_schluessel grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/neu.py:1141
  Evidence: Eigene Sonde: beide Beispielreisen, Meldungen [], Dateien byte-gleich.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/neu.py:1145
  Evidence: Beispielreise trägt Rollen, daher bleibt Herberge preis ohne Rolle (Sonde: Dateien byte-gleich).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/neu.py:1063
  Evidence: Docstring beschreibt neue Bedingung (#584); Testkommentare laut Diff angepasst.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/neu.py:1291
  Evidence: Instanz-Tests selbst nachgeprüft: 3 passed; Beleg instanz-tests.md.
  Status: CONFIRMED

## Verdict
VERDICT: VERIFIED
Tests: 240 passed, 0 failed, 0 übersprungen (zielgerichtet); Instanz 3 passed
Edge cases: All checked, none broken
Regressions: None found
Checklist: 6/6 points proven

## Geprüfte Dateien

- sha256:3f2bd480930c8ea7172e6870352d32b4fc339ce300c261ea0f0df986dd1ec7cb  engine/neu.py

## Prüfbasis

- base: 7cfe5dacd6cf98b2d5f8ef82127b1df5711435ee
- blob:e3cc5c41fd28fe55b23cdbb98fbf58dc67580ca7  engine/neu.py
