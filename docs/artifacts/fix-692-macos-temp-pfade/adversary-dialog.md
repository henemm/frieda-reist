# Adversary Dialog — fix-692-macos-temp-pfade
Spec: docs/specs/fast/fix-692-macos-temp-pfade.md
Datum: 2026-11-27

## Checkliste
- AC-1: neuer Test rot vorher, grün nachher: PROVEN
- AC-2: Protokollprüfung grün nach Bereinigung: PROVEN
- AC-3: übrige Tests des Moduls grün: PROVEN
- Invarianten: PROVEN, mit einer Randbeobachtung (F001)

## Dialog

### Runde 1
**Adversary:** Beweis je AC verlangt. Modul-Lauf: 4 passed (test_protokolle_ohne_absolute_pfade, test_muster_erkennt_pfade, test_muster_erkennt_pytest_tmp, test_muster_erkennt_macos_temp). RED: das alte ABSOLUT aus febd806 geladen und gegen die drei Positiv-Beispiele des neuen Tests geprüft: Trefferliste [False, False, False], der neue Test wäre also an der ersten assert rot. Neues Muster trifft alle drei und lehnt $TMPDIR, die gekürzte Form mit … und schlichtes /tmp/pytest-of-<benutzer> ab. Regex-Logik geprüft: `private/var(?!/folders\b)` verhindert Doppeltreffer, `/private/var/folders/…` scheitert am Namensteil `[\w.-]+` (… ist kein Wortzeichen), wie in der Spec gewollt.
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Bereinigung nachgerechnet: Diff des #694-Protokolls hat 228 Zeilen weg und 228 dazu (nur Ersetzungen, keine Zeile hinzugekommen oder entfallen). Jede geänderte Zeile unterscheidet sich von der alten nur im Bereich Temp-Pfad (Ersatz durch $TMPDIR, auch bei der Mitte-gekürzten Form); die 40 Zeilen, die ein strenger Regex-Nachbau als abweichend meldete, sind dieselbe gekürzte Form (Abweichung nur im Nachbau, per Opcode-Diff bestätigt). Die Kennung des Temp-Ordners kommt im #694-Protokoll 0-mal vor. Fehlalarme: in docs und CLAUDE.md steht außerhalb von diesem Workflow kein /private/var, /var/folders oder /private/tmp, die Prüfung meldet also nichts Falsches. Gegenprobe der Kennung über docs/artifacts, docs/specs, docs/context: ein Rest in einem fremden Protokoll (F001).
**Implementierer:** (nicht beteiligt)

## Findings und Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:40
  Evidence: test_muster_erkennt_macos_temp; altes Muster liefert [False, False, False] für die Positiv-Beispiele (rot), neues Muster trifft (grün, 4 passed).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:9
  Evidence: Neues ABSOLUT-Muster; test_protokolle_ohne_absolute_pfade grün. Vor der Bereinigung enthielt das #694-Protokoll 198 Zeilen mit dem Temp-Pfad, die das Muster getroffen hätte.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: docs/artifacts/fix-694-konto-loeschen-ablage-neu/test-run-output.txt:61
  Evidence: Zeile trägt jetzt $TMPDIR/pytest-of-<benutzer>/…, diff 228/228 nur Pfad-Ersetzungen, Kennung 0-mal.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:30
  Evidence: test_muster_erkennt_pytest_tmp und test_muster_erkennt_pfade unverändert und grün; alte Muster (home, Users, srv, mnt, root, var/www) im Regex unverändert.
  Status: CONFIRMED

Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: docs/artifacts/fix-656-vorab-ordner-faden/test-red-output.txt:91
  Description: Die Zeile enthält ein von pytest in der Mitte gekürztes Fragment `…olders/<Kennung des Temp-Ordners>/T/pytest-of-<benutzer>/…` mit der rechnerspezifischen Kennung. Vorbestehend, nicht Teil dieser Änderung.
  Spec requirement: Invariante des Auftrags — keine rechnerspezifische Temp-Kennung mehr irgendwo unter docs/artifacts, docs/specs, docs/context
  Conflict: Die Kennung steht dort noch, weil weder das neue Muster noch die Bereinigung dieses Fragment erfassen (es beginnt nicht mit /private/var). Die Spec selbst nennt nur das #694-Protokoll und verbietet Änderungen an anderen Protokollen; Lücke in Spec und Muster, nicht im Code.
  Remediation: Fragment in einem Folgeschritt zu `...$TMPDIR/` ersetzen und ggf. das Muster um die gekürzte Form mit Kennung erweitern.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
VERDICT: AMBIGUOUS
Alle drei ACs bewiesen (4 passed, 0 failed, 0 übersprungen im Modul). Offen nur F001: Rest der Temp-Kennung in einem fremden Protokoll, nach Wortlaut der Spec (keine Änderung anderer Protokolle) nicht behebbar, nach der Invariante des Auftrags aber ein Rest.

## Geprüfte Dateien

- sha256:91ead76e155937d2aa46ba5b96512ab98ec1f4ed934e7be723b4beec087fa85a  docs/artifacts/fix-656-vorab-ordner-faden/test-red-output.txt
- sha256:a8e88dba7777f698241b186c6f12b3e3605e35f0e5cdb5625789eb5e4e983a28  docs/artifacts/fix-694-konto-loeschen-ablage-neu/test-run-output.txt
- sha256:c9aa03bc98664eeae55c95aa2070038ff3d648493767d964b8fec04a0772e1d0  engine/tests/test_protokolle_ohne_pfade.py

## Prüfbasis

- base: febd806074e1ffbb9c5264da21ff0cc39ee2e5d4
- blob:91a09b1845daa537ede5b617b8e194da6e715cd4  docs/artifacts/fix-656-vorab-ordner-faden/test-red-output.txt
- blob:5f0b5f4aacff5802e6ae7fe2a797242f0c9e2049  docs/artifacts/fix-694-konto-loeschen-ablage-neu/test-run-output.txt
- blob:c68825a6188589cae603028ce78f4c3b9e80c87d  engine/tests/test_protokolle_ohne_pfade.py
