# Adversary Dialog — fix-570-anstoss-pfad
Spec: docs/specs/betrieb/anstoss-pfad-570.md
Datum: 2026-11-14 12:24

## Checkliste
- [x] Im Software-Klon stößt jeder Schreibvorgang das Skript `<wurzel>/betrieb/veroeffentlichen.sh` an; die Seite zeigt den neuen Stand nach Sekunden.
- [x] In der alten Anordnung gilt unverändert `<wurzel>/frieda/betrieb/veroeffentlichen.sh`.
- [x] Fehlt das Skript, steht eine Zeile im Journal; der Schreibvorgang selbst gelingt wie bisher.
- [x] **AC-1 (alte Anordnung, `.gitmodules`):** Given eine Wurzel mit `.gitmodules` / When die Vorgabe bestimmt wird / Then ist sie `<wurzel>/frieda/betrieb/veroeffentlichen.sh`
- [x] **AC-2 (alte Anordnung, Ordner):** Given eine Wurzel mit Ordner `frieda/betrieb`, ohne `.gitmodules` / When die Vorgabe bestimmt wird / Then ist sie ebenfalls `<wurzel>/frieda/betrieb/veroeffentlichen.sh`
- [x] **AC-3 (neue Anordnung):** Given eine Wurzel ohne `.gitmodules` und ohne Ordner `frieda/betrieb` / When die Vorgabe bestimmt wird / Then ist sie `<wurzel>/betrieb/veroeffentlichen.sh`
- [x] **AC-4 (Vorrang):** Given ein Argument, `SB_VEROEFFENTLICHEN` und die Vorgabe / When `Schreiber` entsteht / Then gilt das Argument vor `SB_VEROEFFENTLICHEN` vor der Vorgabe
- [x] **AC-5 (Anstoß im Software-Klon):** Given ein Software-Klon mit Skript unter `betrieb/` und ohne `SB_VEROEFFENTLICHEN` / When ein Schreibvorgang das Veröffentlichen anstößt / Then wird das Skript gestartet
- [x] **AC-6 (fehlendes Skript):** Given ein nicht vorhandenes Skript / When `veroeffentlichen_anstossen` läuft / Then steht genau eine Zeile `Publishing not started (<pfad>): script missing` auf stderr, es startet kein Prozess und es wird keine Ausnahme geworfen
- [x] **AC-7 (leerer Pfad):** Given ein leerer Pfad / When `veroeffentlichen_anstossen` läuft / Then bleibt es still und es startet kein Prozess
- [x] **AC-8 (Bestand):** Given die bestehenden Anstoß-Tests / When der Stand läuft / Then sind sie unverändert grün
- [x] **AC-9 (Betrieb):** Given die Instanz mit dem neuen Stand / When ein Schreibvorgang erfolgt / Then steht ein neuer Eintrag im Anstoß-Protokoll von `<FR_DIENST>` und die Seite zeigt den Stand nach Sekunden statt nach Minuten

## Dialog

### Runde 1
**Adversary:** Suite (test_anstoss_pfad_570, test_schreiben, test_software_weg_454, -n 3): 234 passed, 0 failed, 0 übersprungen (adversary-test-output.txt). Regel verglichen mit fr_alte_anordnung (betrieb/gemeinsam.sh:46-48: `-e .gitmodules || -d frieda/betrieb`): Python engine/schreiben.py:5100-5108 nutzt `.exists()` und `.is_dir()`, identisch. Probe: Ordner frieda ohne betrieb ergibt neue Anordnung; frieda/betrieb als Datei ergibt neue Anordnung (wie `-d`); .gitmodules als Ordner ergibt alte (wie `-e`). Aufrufer: schreiben_git.py:201 reicht s.veroeffentlichen weiter (nach __init__ nie None, leerer Wert bleibt leer); messlauf-schreibweg.py:64 setzt absichtlich einen fehlenden Pfad (nur neue stderr-Zeile, spec-konform). Kein Unit, keine Vorlage und keine Doku im Repo setzt SB_VEROEFFENTLICHEN leer oder überhaupt (grep betrieb/, docs/): der Wechsel von `or` auf `is None` trifft im Repo keinen Fall; ein leerer Wert schaltet aus, laut Spec (Implementation Details 2) ausdrücklich gewollt.
**Implementierer:** Code engine/schreiben.py:5100-5108, 5116-5125, 5299-5303 erfüllt die Punkte; Test 1-7 grün.

### Runde 2
**Adversary:** Gezielte Brüche: (a) Leerer SB_VEROEFFENTLICHEN gesetzt (Probe): Schreiber.veroeffentlichen ist leer, anstossen kehrt still zurück, keine Ausnahme. Risiko nur extern (eine Instanz-Einstellung mit leerem Wert schaltet jetzt das Anstoßen ab, vorher Vorgabe): im Repo nirgends vorhanden, durch Spec gedeckt, nur als Hinweis F001. (b) Fehlendes Skript: genau eine Zeile, kein Popen, kein Wurf (Zeile 5301-5303, Test 6). (c) Skript nicht ausführbar: Popen-OSError wird wie bisher in der Schleife gemeldet, kein Wurf. (d) Verzeichnis statt Skript: exists() wahr, OSError gefangen. (e) Pfad mit Leerzeichen: argv-Element, keine Shell. (f) Absolute Pfade in docs/artifacts: keine gefunden.
**Implementierer:** Alle Fälle bleiben im bestehenden try/except; Spec-Vorgaben eingehalten.

### Runde 2
**Adversary:**
**Implementierer:**

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Confirmations

Confirmation:
  AC: AC-1, AC-2, AC-3
  Code reference: engine/schreiben.py:5100
  Evidence: veroeffentlichen_skript prüft .gitmodules bzw. frieda/betrieb als Ordner, identisch zu fr_alte_anordnung; Tests 1-3 grün, Probe bestätigt Randfälle.
  Status: CONFIRMED

Confirmation:
  AC: AC-4, AC-7
  Code reference: engine/schreiben.py:5119
  Evidence: Argument, dann SB_VEROEFFENTLICHEN, dann Vorgabe, je mit `is None`; leerer Wert bleibt leer; Test 4 und 7 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5, AC-6
  Code reference: engine/schreiben.py:5299
  Evidence: leerer Pfad still, fehlendes Skript eine stderr-Zeile ohne Prozess, sonst Popen; Test 5 und 6 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:5116
  Evidence: 234 passed in den drei Testdateien, keine Regression.
  Status: CONFIRMED

AC-9: nach Auslieferung offen, nicht blockierend (Abnahme auf dem Server).

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/schreiben.py:5119
  Description: Ein extern gesetzter, leerer SB_VEROEFFENTLICHEN schaltet jetzt aus statt auf die Vorgabe zurückzufallen.
  Spec requirement: Implementation Details 2 — ein ausdrücklich leerer Pfad bleibt leer und schaltet aus.
  Conflict: keiner; im Repo wird der Wert nirgends leer gesetzt. Nur Hinweis für Instanzen mit eigener Einstellung.
  Remediation: keine nötig; bei der Auslieferung Instanz-Einstellungen prüfen.

## Verdict
VERDICT: VERIFIED

## Geprüfte Dateien

- sha256:9ee80b6962f6e4cfb6bf4e8c6536153cf6f496e1feb2f4156e60ce63da927265  engine/schreiben.py

## Prüfbasis

- base: d39253bc0b9336d4b6b1c81eadbfe80e2502f16d
- blob:bf97db3df452f0406b85203aabf77d033367d872  engine/schreiben.py
