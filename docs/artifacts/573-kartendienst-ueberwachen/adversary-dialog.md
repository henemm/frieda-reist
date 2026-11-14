# Adversary Dialog — 573-kartendienst-ueberwachen
Spec: docs/specs/betrieb/kartendienst-ueberwachen-573.md
Datum: 2026-11-14 13:01

## Checkliste
- [x] Ein gelungener Zugriff auf den eigenen Dienst hinterlässt `Own map service answered (<n> elements)`; ein Rückfall weiter eine der beiden Zeilen aus #567.
- [x] Ein einzelner Rückfall oder zwei in Folge lösen keine Warnung aus.
- [x] Der ruhende Dienst (Socket lauscht, Proxy und Container `inactive`) gilt als bereit; der Check weckt ihn nie.
- [x] Nach drei Rückfällen in Folge innerhalb von 24 h kommt genau eine Warnung; beim nächsten gelungenen Zugriff genau eine Entwarnung.
- [x] Ohne eingerichteten Kartendienst bleibt der Check still.
- [x] **AC-1 (Erfolgszeile):** Given der eigene Kartendienst antwortet gültig (auch mit leerer Trefferliste) / When `overpass_holen` läuft / Then steht genau die Zeile `Own map service answered (<n> elements)` auf stderr, einzeilig, ohne Adresse; Rückgabe und Rückfall sind wie bisher
- [x] **AC-2 (Vertrag Präfix):** Given Fehler, Antwort ohne `elements` und Erfolg / When je eine Abfrage läuft / Then beginnt jede Zeile über den eigenen Dienst mit `Own map service`, und ein Kommentar an `overpass_eigen` benennt das Präfix als Vertrag mit `monitor.sh`
- [x] **AC-3 (Ohne Einrichtung still):** Given keine `abdeckung.json` / When der Check läuft / Then ist er ok ohne Meldung
- [x] **AC-4 (Ruhe ist ok):** Given Socket `active`, Proxy und Container `inactive` / When der Check läuft / Then ist er ok, und der Check ruft den Dienst nie auf (keine Probe)
- [x] **AC-5 (Einheiten nicht bereit):** Given der Socket ist nicht `active` oder Proxy oder Container ist `failed` / When der Check läuft / Then folgt eine Warnung „eigener Kartendienst nicht bereit (<Einheit>)“, nicht kritisch und ohne Agent
- [x] **AC-6 (Häufung warnt):** Given die letzten 3 Zugriffe im Fenster von 24 h sind alle Rückfälle / When der Check läuft / Then folgt genau eine Warnung mit Grund der jüngsten Zeile und Hinweis `journalctl -u frieda-reisen-schreiben -n 50`
- [x] **AC-7 (Einzelfall warnt nie):** Given weniger als 3 Zugriffe oder die jüngste Zeile ist ein Erfolg / When der Check läuft / Then ist er ok
- [x] **AC-8 (Entwarnung):** Given eine Warnung besteht / When wieder ein Zugriff gelingt (Erfolgszeile) und die Einheiten bereit sind / Then ist der Check ok, und es kommt einmal ✅
- [x] **AC-9 (Einstellbar):** Given `FRIEDA_KARTEN_RUECKFALL_SCHWELLE` und `FRIEDA_KARTEN_RUECKFALL_FENSTER` stehen oben in `monitor.sh` mit den Vorgaben 3 und 24 h / When sie gesetzt sind / Then gelten die gesetzten Werte
- [x] **AC-10 (Kein Alarmweg):** Given der Check meldet / When die Warnung abgesetzt wird / Then ist die Check-ID `frieda-reisen-kartendienst-bereit` nicht kritisch (`MONITOR_ERRORS` bleibt 0), ohne Incident-Agent, kein `high` über den Meldeweg
- [x] **AC-11 (Doku):** Given `docs/betrieb.md` / When die Änderung steht / Then nennt der Abschnitt „Eigener Kartendienst“ das Protokoll des Schreibwegs (nicht des Konnektors), die drei Zeilenformen und die Überwachung samt Ende der Warnung
- [x] **AC-12 (Spec 444):** Given `docs/specs/betrieb/eigener-kartendienst-444.md` / When die Änderung steht / Then nennt AC-6 dort zusätzlich die Erfolgszeile
- [x] **AC-13 (Infra-Issue):** Given der Infra-Anteil / When er umgesetzt wird / Then gibt es ein Issue im Infra-Repo, auf das der dortige Commit verweist

## Dialog

### Runde 1
**Adversary:** Beweise je Punkt. Test-Läufe: Frieda `test_kartendienst.py` + `test_protokolle_ohne_pfade.py` 61 bestanden; Infra `test_monitor_frieda_kartendienst_bereit.py` 14 bestanden (Ausgabe: adversary-test-output.txt). Eigene Angriffe auf `check_frieda_kartendienst_bereit` (scripts/monitor.sh:2248-2290) mit ersetztem systemctl/journalctl:
- zwei Rückfälle -> ok, keine Meldung; drei -> genau eine Meldung, STATE=fail, ERRORS=0, kein Agent.
- drei Zeilen `answered without elements` -> fail (zählt als Rückfall, nicht Erfolg; grep auf `answered (` mit Klammer trifft sie nicht).
- Erfolg, dann drei Rückfälle -> fail; drei Rückfälle, dann Erfolg -> ok.
- Fremdzeilen dazwischen -> ignoriert, fail bei drei Rückfällen.
- Sonderzeichen im Grund (`"`, `'`, `$(id)`, Backticks, `%s %d`, `\n`) -> wird wörtlich gemeldet, keine Ausführung.
- 500 Zeichen langer Grund -> auf 120 gekürzt.
- journalctl rc=1 mit Zeilen / leeres Journal -> ok (Spec Punkt 6).
- Schwelle leer -> Vorgabe 3 (`:-`).
- Funktion enthält weder curl noch start/restart (grep leer); aufgerufene systemctl: nur is-active/is-failed.
- monitor.sh läuft mit `set -uo pipefail` (Zeile 8), ohne -e; unter `set -u` läuft die Funktion ohne unbound variable.
- Frieda: engine/schreiben.py:2267 `overpass_eigen`, Erfolgszeile Zeile 2282, Kommentar zum Präfix-Vertrag Zeile 2279-2280; Rückgabe unverändert.
Gefunden (gering): (a) Schwelle 0 -> Dauerwarnung mit leerem Grund; (b) Schwelle Nicht-Zahl -> Check bleibt still ok, stderr-Rauschen von tail/[; (c) ein Fehlertext, der selbst `Own map service answered (` enthält, würde als Erfolg zählen (konstruiert, Fehlertexte kommen aus urllib/Socket).
**Implementierer:** (nicht anwesend; Isolation)

### Runde 2
**Adversary:** Nachbohren. (1) Entprellung: Test 12 grün, alert_on_change sendet nur bei ok->fail bzw. fail->ok; zweiter Lauf ohne Meldung. (2) Prefix `frieda-reisen-` steht in NON_CRITICAL_PREFIXES und NO_AGENT_PREFIXES (monitor.sh:162ff/206ff), Lauf zeigt ERRORS=0, kein `agent:`. (3) Ruhe: Socket active, Proxy/Container inactive -> ok; `is-failed` für inactive liefert 1, kein Fehler. (4) Fehlt abdeckung.json -> ok, systemctl wird nicht aufgerufen (Test 3). (5) Fenster geht als `--since` an journalctl (Test 11). (6) Keine echten Serverpfade: grep nach /home/, /srv/ in den neuen Frieda-Protokollen und im Doku-Diff leer; test_protokolle_ohne_pfade grün. (7) Doku docs/betrieb.md: Protokoll des Schreibwegs, drei Zeilenformen, Überwachung samt Ende der Warnung vorhanden. (8) Spec-444 AC-6 nennt die Erfolgszeile. (9) AC-13: Infra-Issue #455 OPEN, Commit 17f91e5 verweist darauf (Titel nennt frieda-reist#573, Commit-Text "(#455)"). (10) Schreibweg-Einheit: betrieb/einrichten.sh Zeile 113/191/236 kennt `<instanz>-schreiben.service`; FRIEDA_SCHREIBEN_UNIT=frieda-reisen-schreiben. Hinweis: Die Infra-Arbeitskopie ist ungesichert (nur Test-Commit, monitor.sh unversioniert geändert, 49 Zeilen), Lieferung steht noch aus; kein Defekt der Implementierung.
**Implementierer:** (nicht anwesend; Isolation)

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/schreiben.py:2282
  Evidence: Erfolgszeile `Own map service answered (<n> elements)` bei Liste elements (auch leer); test_erfolg_schreibt_erfolgszeile grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/schreiben.py:2279
  Evidence: Kommentar nennt Präfix als Vertrag mit monitor.sh; alle drei Zeilen beginnen mit `Own map service`; Vertragstest grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: ~/henemm-infra-wt-573/scripts/monitor.sh:2254
  Evidence: Ohne abdeckung.json alert_on_change ok, return vor jedem systemctl; Test 3 und eigener Lauf.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: ~/henemm-infra-wt-573/scripts/monitor.sh:2259
  Evidence: Nur is-active/is-failed, kein curl/start/restart; Ruhe ergibt ok.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: ~/henemm-infra-wt-573/scripts/monitor.sh:2266
  Evidence: Warnung "nicht bereit (<Einheit>)", ERRORS=0, kein Agent.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: ~/henemm-infra-wt-573/scripts/monitor.sh:2273
  Evidence: tail -n Schwelle der Zeilen mit Präfix, Warnung wenn keine `answered (`; Grund gekürzt, Hinweis journalctl vorhanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: ~/henemm-infra-wt-573/scripts/monitor.sh:2275
  Evidence: Zwei Rückfälle und Erfolg als jüngste Zeile -> ok (eigene Läufe).
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: ~/henemm-infra-wt-573/scripts/monitor.sh:2284
  Evidence: Nach Erfolgszeile ok, alert_on_change sendet einmal Entwarnung (Test 9).
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: ~/henemm-infra-wt-573/scripts/monitor.sh:272
  Evidence: Variablen mit Vorgaben 3 und "24 hours ago" oben; Test 11.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: ~/henemm-infra-wt-573/scripts/monitor.sh:2248
  Evidence: Check-ID unter frieda-reisen-; ERRORS=0, kein Agent; Meldung nur über NOTIFY 🟡.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: docs/betrieb.md:500
  Evidence: Protokoll des Schreibwegs, drei Zeilenformen, Überwachung inkl. Ende der Warnung (Zeilen 500 und 515-517).
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: docs/specs/betrieb/eigener-kartendienst-444.md:168
  Evidence: AC-6 nennt zusätzlich die Erfolgszeile.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: docs/specs/betrieb/kartendienst-ueberwachen-573.md:173
  Evidence: Issue henemm/henemm-infra#455 OPEN; Infra-Commit 17f91e5 verweist darauf.
  Status: CONFIRMED

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/schreiben.py:2282
  Description: Prüfung auf Erfolg im Check ist ein Teilstring `Own map service answered (` über die letzten Zeilen; Rückfallzeile enthält Fehlertext frei von außen (Zeile 2276-2277).
  Spec requirement: AC-6 — drei Rückfälle in Folge warnen
  Conflict: Ein Fehlertext, der selbst `Own map service answered (` enthält, würde als Erfolg gelesen (konstruiert, praktisch unwahrscheinlich).
  Remediation: Erfolg nur am Zeilenanfang prüfen (`grep -q '^Own map service answered ('`).

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: ~/henemm-infra-wt-573/scripts/monitor.sh:2272
  Description: Schwelle wird nicht auf positive Ganzzahl geprüft. Schwelle 0 -> Dauerwarnung mit leerem Grund; Schwelle "abc" -> Check ok mit stderr-Rauschen.
  Spec requirement: AC-9 — gesetzte Werte gelten
  Conflict: Fehlkonfiguration führt zu Dauerwarnung oder stillem Aus; Spec verlangt nichts Anderes, aber nicht robust.
  Remediation: `[[ "$schwelle" =~ ^[1-9][0-9]*$ ]] || schwelle=3`.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Begründung: Alle 5 Erwartungen und AC-1 bis AC-13 belegt. Tests: Frieda 61 bestanden, Infra 14 bestanden, 0 fehlgeschlagen, 0 übersprungen. Zwei LOW-Findings (kein Blocker). Hinweis: Infra-Anteil liegt noch ungesichert in der Arbeitskopie und muss mit dem Issue-Verweis committet werden.

## Geprüfte Dateien

- sha256:0b6efa924e9b95c75781c8079c10cce66f7227882dc0aa6fa05778db341a842c  docs/betrieb.md
- sha256:25471383f43903813b2102609440c289617a390ab3ae3740f80246e8741134ce  docs/specs/betrieb/eigener-kartendienst-444.md
- sha256:e2b3efc46ffb687f9df52fcbfe1ddd7fcc212672f772f0cf7b3b9da999c66ff7  docs/specs/betrieb/kartendienst-ueberwachen-573.md
- sha256:7965538cb2d09eada79f4da47d7cd8ac0e07c384cca32fbd02a6bc6663539e54  engine/schreiben.py

## Prüfbasis

- base: d39253bc0b9336d4b6b1c81eadbfe80e2502f16d
- blob:1ce7620f12cf61b63c547129a9514f548a4b034e  docs/betrieb.md
- blob:7f6dfa9c9f7e53c6aaafbd674285070e389ce6f9  docs/specs/betrieb/eigener-kartendienst-444.md
- blob:86dfb08cbc199fdcf6377680aa05cc2bc3d38ed5  docs/specs/betrieb/kartendienst-ueberwachen-573.md
- blob:99757d7987aeabd0a3a61946c6f9ab33f0b1594f  engine/schreiben.py

## Geprüfte Dateien

- sha256:0b6efa924e9b95c75781c8079c10cce66f7227882dc0aa6fa05778db341a842c  docs/betrieb.md
- sha256:25471383f43903813b2102609440c289617a390ab3ae3740f80246e8741134ce  docs/specs/betrieb/eigener-kartendienst-444.md
- sha256:e2b3efc46ffb687f9df52fcbfe1ddd7fcc212672f772f0cf7b3b9da999c66ff7  docs/specs/betrieb/kartendienst-ueberwachen-573.md
- sha256:7965538cb2d09eada79f4da47d7cd8ac0e07c384cca32fbd02a6bc6663539e54  engine/schreiben.py

## Prüfbasis

- base: d39253bc0b9336d4b6b1c81eadbfe80e2502f16d
- blob:1ce7620f12cf61b63c547129a9514f548a4b034e  docs/betrieb.md
- blob:7f6dfa9c9f7e53c6aaafbd674285070e389ce6f9  docs/specs/betrieb/eigener-kartendienst-444.md
- blob:86dfb08cbc199fdcf6377680aa05cc2bc3d38ed5  docs/specs/betrieb/kartendienst-ueberwachen-573.md
- blob:99757d7987aeabd0a3a61946c6f9ab33f0b1594f  engine/schreiben.py
