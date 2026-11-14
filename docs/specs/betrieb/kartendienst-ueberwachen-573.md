---
entity_id: kartendienst-ueberwachen-573
type: feature
created: 2026-11-14
updated: 2026-11-14
status: draft
workflow: 573-kartendienst-ueberwachen
---

# Ausfall des eigenen Kartendienstes überwachen (#573)

Grundlage: `docs/context/573-kartendienst-ueberwachen.md` (Kontext, Befunde, Analyse), Issue #573 und die Spezifikationen `eigener-kartendienst-444.md` und `kartendienst-diagnose-567.md` im selben Ordner.

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es kommen eine Protokollzeile im Erfolgsfall, ein Teil-Check in der Überwachung der Infrastruktur und Doku dazu. Datenformat, Rückfallverhalten und Oberfläche bleiben unverändert; der Kern aus ADR-0001 ist nicht berührt. Schwelle und Zeitfenster sind Betriebsdetails.

## Purpose

Fällt der eigene Kartendienst (Overpass bei Bedarf, #444) dauerhaft aus, springt der Schreibweg still auf den öffentlichen Dienst zurück. Seit #567 steht dafür eine Zeile im Protokoll, aber niemand wird gewarnt. Diese Änderung lässt einen dauerhaften Ausfall als Warnung (🟡, einmal je Störung, kein `high`-Alarm, kein Incident-Agent) in `monitor.sh` der Infrastruktur auffallen, ohne den ruhenden Dienst je durch eine Probe zu wecken.

## Befund

1. **Kein Signal bei Dauerausfall.** `overpass_eigen` schreibt bei Rückfall eine Zeile; ausgewertet wird sie nirgends. Der vorhandene Check `check_frieda_kartendienst` prüft nur das Alter von `abdeckung.json`.
2. **Gesundung nicht erkennbar.** Ein gelungener Zugriff hinterlässt heute keine Zeile. Aus Rückfall-Zeilen allein ließe sich nicht sagen, ob der Dienst nach einer Häufung wieder geht; eine Warnung könnte erst nach Ablauf des Zeitfensters enden. Deshalb kommt eine Erfolgszeile dazu.
3. **Keine aktive Probe möglich.** Ein Aufruf des Sockets startet Proxy und Container (rund 1,6 GiB beim Einspielen, im Betrieb deutlich weniger, aber spürbar); alle 5 Minuten gerufen, ruhte der Dienst nie. Bereitschaft wird nur passiv geprüft.
4. **Einzelne Rückfälle sind normal** (Kaltstart, Zeitüberschreitung bei großer Abfrage). Gewarnt wird erst bei einer Häufung.
5. **Der Zugriff läuft im Prozess des Schreibwegs** (`frieda-reisen-schreiben`, `overpass_holen`), nicht im Konnektor. `docs/betrieb.md` nennt fälschlich das „Protokoll des Konnektors“.
6. **Entprellung je Check-ID:** `alert_on_change` meldet nur beim Wechsel ok zu fail und zurück; zwei Bedingungen unter derselben ID überschrieben sich, daher eine eigene ID.

## Source

- **File:** `engine/schreiben.py`, `engine/tests/test_kartendienst.py`, `docs/betrieb.md`; im Infra-Repo `scripts/monitor.sh` und `tests/test_monitor_frieda_kartendienst_bereit.py`
- **Identifier:** `overpass_eigen` (Erfolgszeile), neue Funktion `check_frieda_kartendienst_bereit`, Check-ID `frieda-reisen-kartendienst-bereit`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `overpass_eigen`, `overpass_holen` | function | Quelle der Protokollzeilen; Rückgabewerte und Rückfallverhalten unverändert |
| `LOG_LAENGE` | Konstante | Kürzung der Protokollzeilen |
| `eigener-kartendienst-444.md` | Spec | Start bei Bedarf, Rückfall (AC-6), Units |
| `kartendienst-diagnose-567.md` | Spec | Rückfallzeilen, die der Check auswertet |
| `frieda-reisen-kartendienst.socket`, `-proxy.service`, `.service` | systemd-Units | Bereitschaft; Ruhe (`inactive`) ist kein Fehler |
| `frieda-reisen-schreiben` | systemd-Unit | Journal mit den Zeilen `Own map service …` |
| `abdeckung.json` (`FRIEDA_KARTEN_ABDECKUNG`) | Datei | fehlt sie, ist der Dienst nicht eingerichtet und der Check still ok |
| `alert_on_change`, `NON_CRITICAL_PREFIXES`, `NO_AGENT_PREFIXES` | monitor.sh | Entprellung; Präfix `frieda-reisen-` ist schon nicht kritisch und ohne Agent |
| `test_monitor_frieda_schreiben.py` | Test | Muster für den neuen Infra-Test |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/schreiben.py` | MODIFY | `overpass_eigen`: Erfolgszeile `Own map service answered (<n> elements)`; Kommentar nennt das Präfix `Own map service` als Vertrag mit `monitor.sh` |
| `engine/tests/test_kartendienst.py` | MODIFY | Erfolgszeile festhalten; Test AC-3 aus #567 (keine Zeile bei Erfolg) auf die neue Zeile umstellen; Vertragstest zum Präfix |
| `docs/betrieb.md` | MODIFY | Abschnitt „Eigener Kartendienst“: Protokoll des Schreibwegs statt Konnektor, Erfolgszeile, Überwachung beschreiben |
| `docs/specs/betrieb/eigener-kartendienst-444.md` | MODIFY | AC-6: Erfolg wie Rückfall hinterlässt eine Zeile (Folge aus der Erfolgszeile) |
| `docs/specs/betrieb/kartendienst-ueberwachen-573.md` | CREATE | diese Spec |
| Infra-Repo `scripts/monitor.sh` | MODIFY | Variablen `FRIEDA_KARTEN_RUECKFALL_SCHWELLE` und `FRIEDA_KARTEN_RUECKFALL_FENSTER`, Funktion `check_frieda_kartendienst_bereit`, Aufruf in der Check-Liste |
| Infra-Repo `tests/test_monitor_frieda_kartendienst_bereit.py` | CREATE | Tests mit ersetzten `systemctl` und `journalctl` |
| Issue im Infra-Repo | CREATE | Nachvollziehbarkeit des Infra-Anteils; Commit dort verweist darauf |

### Estimated Changes

- Files: 6 in diesem Repo (davon 1 neu), 2 im Infra-Repo
- LoC: dieses Repo ca. +45/-5, Infra-Repo ca. +60 Check und +120 Tests
- Risiko: niedrig (eine zusätzliche Protokollzeile, Check ist Warnung ohne Agent, entprellt)

### Out of Scope

- Aktive Probe gegen den Socket (siehe Befund 3).
- Alarm über den Meldeweg (`high`, Telegram) und Incident-Agent: ein Ausfall des eigenen Dienstes ist keiner der Nutzer, der öffentliche Dienst trägt.
- Überwachung des öffentlichen Overpass-Dienstes.
- Änderung von Rückgabewerten oder Rückfallverhalten von `overpass_eigen` und `overpass_holen`.
- Änderung des vorhandenen Checks `check_frieda_kartendienst` (Alter der Abdeckung).

## Implementation Details

### Engine (dieses Repo)

1. In `overpass_eigen` kommt eine dritte Zeile hinzu: bei gültiger Antwort mit Liste `elements` (auch leer) schreibt die Funktion `Own map service answered (<n> elements)` auf stderr, englisch, einzeilig, ohne Adresse, wie die beiden Rückfallzeilen. Rückgabewerte bleiben unverändert.
2. Alle drei Formen beginnen mit `Own map service` (`failed (…)`, `answered without elements`, `answered (<n> elements)`). Das Präfix ist der Vertrag mit `monitor.sh`; ein Test hält es fest, ein Kommentar an der Stelle benennt ihn.
3. Volumen gering: je Kartenabfrage eine Zeile, Abfragen sind selten.

### Check `check_frieda_kartendienst_bereit` (Infra-Repo)

Passiv, je Lauf (alle 5 Minuten), unter der eigenen Check-ID `frieda-reisen-kartendienst-bereit`:

1. Fehlt `abdeckung.json`: still ok (wie der vorhandene Check).
2. Bereitschaft der Einheiten: ist `frieda-reisen-kartendienst.socket` nicht `active`, oder ist die Proxy- oder Container-Einheit `failed`, folgt die Warnung „eigener Kartendienst nicht bereit (<Einheit>)“. `inactive` bei Proxy und Container ist der Ruhezustand und kein Fehler.
3. Verlauf der Zugriffe: aus dem Journal von `frieda-reisen-schreiben` der letzten `FRIEDA_KARTEN_RUECKFALL_FENSTER` (Vorgabe 24 h) werden die Zeilen mit `Own map service` gelesen. Sind die letzten `FRIEDA_KARTEN_RUECKFALL_SCHWELLE` (Vorgabe 3) Zugriffe alle Rückfälle, folgt die Warnung „eigener Kartendienst fiel bei den letzten 3 Abfragen aus, öffentlicher Dienst trägt“ mit Grund der jüngsten Zeile (gekürzt) und dem Hinweis `journalctl -u frieda-reisen-schreiben -n 50`. Ist die jüngste Zeile ein Erfolg oder gibt es weniger als 3 Zugriffe, ist der Check ok.
4. Ende der Warnung: gelingt wieder ein Zugriff (Erfolgszeile) oder liegen keine Rückfälle mehr im Fenster und die Einheiten sind bereit, ist der Check ok; `alert_on_change` sendet dann einmal ✅.
5. Meldung 🟡, Präfix `frieda-reisen-` heißt nicht kritisch (`MONITOR_ERRORS` bleibt 0) und ohne Incident-Agent; einmal je Störung durch `alert_on_change`.
6. Journal nicht lesbar oder leer: kein Zustandswechsel durch den Verlauf (nur Punkt 2 entscheidet). Der Check ist auch ohne Erfolgszeile sicher; er warnt dann nur länger, bis das Fenster abläuft, deshalb zuerst die Engine ausliefern.

### Doku

`docs/betrieb.md`: im Abschnitt „Eigener Kartendienst“ „Protokoll des Konnektors“ durch „Protokoll des Schreibwegs“ ersetzen, die drei Zeilenformen nennen und beschreiben, wann `monitor.sh` warnt (Einheiten nicht bereit, 3 Rückfälle in Folge innerhalb von 24 h) und wann die Warnung endet.

## Expected Behavior

- Ein gelungener Zugriff auf den eigenen Dienst hinterlässt `Own map service answered (<n> elements)`; ein Rückfall weiter eine der beiden Zeilen aus #567.
- Ein einzelner Rückfall oder zwei in Folge lösen keine Warnung aus.
- Der ruhende Dienst (Socket lauscht, Proxy und Container `inactive`) gilt als bereit; der Check weckt ihn nie.
- Nach drei Rückfällen in Folge innerhalb von 24 h kommt genau eine Warnung; beim nächsten gelungenen Zugriff genau eine Entwarnung.
- Ohne eingerichteten Kartendienst bleibt der Check still.

## Test Plan

### Automated Tests (TDD RED)

In `engine/tests/test_kartendienst.py`:

- [ ] Test 1 (`test_erfolg_schreibt_erfolgszeile`): GIVEN der eigene Dienst antwortet gültig mit n Elementen (auch 0) / WHEN `overpass_holen` läuft / THEN steht auf stderr genau die Zeile `Own map service answered (<n> elements)`, einzeilig, ohne Adresse.
- [ ] Test 2 (`test_protokollzeilen_beginnen_mit_vertragspraefix`): GIVEN die drei Wege (Fehler, ohne `elements`, Erfolg) / WHEN je eine Abfrage läuft / THEN beginnt jede Zeile über den eigenen Dienst mit `Own map service` und Rückgabe und Rückfall sind wie bisher.

Im Infra-Repo `tests/test_monitor_frieda_kartendienst_bereit.py` (Muster `test_monitor_frieda_schreiben.py`, `systemctl` und `journalctl` als Funktionen ersetzt, ohne echten Dienst):

- [ ] Test 3: GIVEN keine `abdeckung.json` / WHEN der Check läuft / THEN ok und keine Meldung.
- [ ] Test 4: GIVEN Socket `active`, Proxy und Container `inactive`, keine Zeilen im Journal / WHEN der Check läuft / THEN ok (Ruhe).
- [ ] Test 5: GIVEN Socket nicht `active` / WHEN der Check läuft / THEN fail (Warnung) mit Einheit im Text, `MONITOR_ERRORS=0`, kein Agent.
- [ ] Test 6: GIVEN Proxy oder Container `failed` / WHEN der Check läuft / THEN fail mit dieser Einheit im Text.
- [ ] Test 7: GIVEN drei Rückfallzeilen als jüngste Zugriffe im Fenster / WHEN der Check läuft / THEN fail mit Grund der jüngsten Zeile und Hinweis auf `journalctl -u frieda-reisen-schreiben`, kein Agent.
- [ ] Test 8: GIVEN zwei Rückfälle oder ein Rückfall, sonst nichts / WHEN der Check läuft / THEN ok.
- [ ] Test 9: GIVEN drei Rückfälle, danach eine Erfolgszeile / WHEN der Check läuft / THEN ok (Entwarnung); `alert_on_change` meldet den Wechsel fail zu ok einmal.
- [ ] Test 10: GIVEN Erfolg, Rückfall, Rückfall, Rückfall (jüngste drei sind Rückfälle) / WHEN der Check läuft / THEN fail.
- [ ] Test 11: GIVEN gesetzte Variablen für Schwelle und Fenster / WHEN der Check läuft / THEN gelten die gesetzten Werte (Fenster geht als `--since` ans Journal).
- [ ] Test 12: GIVEN derselbe Fehlerzustand in zwei Läufen / WHEN der Check läuft / THEN nur eine Meldung (Entprellung); Check-ID liegt unter `frieda-reisen-` (nicht kritisch, ohne Agent).
- [ ] Test 13: GIVEN `monitor.sh` / WHEN der Quelltext gelesen wird / THEN steht der Aufruf `check_frieda_kartendienst_bereit` in der Check-Liste und die Funktion startet weder Socket noch Dienst (kein `curl` und kein `systemctl start`/`restart` darin).

Vor der Umsetzung rot: Test 1 und 2 (Erfolgszeile fehlt), Test 3 bis 13 (Check fehlt).

### Manuelle Prüfung (Erfolgsnachweis)

- Gesamtlauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün; Tests des Infra-Repos grün.
- Auf der Instanz: nach Einspielen der Engine steht nach einer Kartenabfrage mit eigenem Dienst die Erfolgszeile im Journal des Schreibwegs.
- `monitor.sh --status` zeigt den Check `frieda-reisen-kartendienst-bereit` als ok; der Kartendienst bleibt dabei im Ruhezustand (Proxy und Container `inactive`).
- Vor dem Vorspulen laufen die Tests der einbindenden Instanz gegen den Stand (CLAUDE.md); neu ist nur eine Protokollzeile, kein geänderter Text für Personen.

## Acceptance Criteria

- **AC-1 (Erfolgszeile):** Given der eigene Kartendienst antwortet gültig (auch mit leerer Trefferliste) / When `overpass_holen` läuft / Then steht genau die Zeile `Own map service answered (<n> elements)` auf stderr, einzeilig, ohne Adresse; Rückgabe und Rückfall sind wie bisher
  - Test: `engine/tests/test_kartendienst.py::test_erfolg_schreibt_erfolgszeile`
- **AC-2 (Vertrag Präfix):** Given Fehler, Antwort ohne `elements` und Erfolg / When je eine Abfrage läuft / Then beginnt jede Zeile über den eigenen Dienst mit `Own map service`, und ein Kommentar an `overpass_eigen` benennt das Präfix als Vertrag mit `monitor.sh`
  - Test: `engine/tests/test_kartendienst.py::test_protokollzeilen_beginnen_mit_vertragspraefix`
- **AC-3 (Ohne Einrichtung still):** Given keine `abdeckung.json` / When der Check läuft / Then ist er ok ohne Meldung
  - Test: Infra-Repo, Test 3
- **AC-4 (Ruhe ist ok):** Given Socket `active`, Proxy und Container `inactive` / When der Check läuft / Then ist er ok, und der Check ruft den Dienst nie auf (keine Probe)
  - Test: Infra-Repo, Test 4 und Test 13
- **AC-5 (Einheiten nicht bereit):** Given der Socket ist nicht `active` oder Proxy oder Container ist `failed` / When der Check läuft / Then folgt eine Warnung „eigener Kartendienst nicht bereit (<Einheit>)“, nicht kritisch und ohne Agent
  - Test: Infra-Repo, Test 5 und Test 6
- **AC-6 (Häufung warnt):** Given die letzten 3 Zugriffe im Fenster von 24 h sind alle Rückfälle / When der Check läuft / Then folgt genau eine Warnung mit Grund der jüngsten Zeile und Hinweis `journalctl -u frieda-reisen-schreiben -n 50`
  - Test: Infra-Repo, Test 7, Test 10 und Test 12
- **AC-7 (Einzelfall warnt nie):** Given weniger als 3 Zugriffe oder die jüngste Zeile ist ein Erfolg / When der Check läuft / Then ist er ok
  - Test: Infra-Repo, Test 8
- **AC-8 (Entwarnung):** Given eine Warnung besteht / When wieder ein Zugriff gelingt (Erfolgszeile) und die Einheiten bereit sind / Then ist der Check ok, und es kommt einmal ✅
  - Test: Infra-Repo, Test 9
- **AC-9 (Einstellbar):** Given `FRIEDA_KARTEN_RUECKFALL_SCHWELLE` und `FRIEDA_KARTEN_RUECKFALL_FENSTER` stehen oben in `monitor.sh` mit den Vorgaben 3 und 24 h / When sie gesetzt sind / Then gelten die gesetzten Werte
  - Test: Infra-Repo, Test 11
- **AC-10 (Kein Alarmweg):** Given der Check meldet / When die Warnung abgesetzt wird / Then ist die Check-ID `frieda-reisen-kartendienst-bereit` nicht kritisch (`MONITOR_ERRORS` bleibt 0), ohne Incident-Agent, kein `high` über den Meldeweg
  - Test: Infra-Repo, Test 5, 7 und 12
- **AC-11 (Doku):** Given `docs/betrieb.md` / When die Änderung steht / Then nennt der Abschnitt „Eigener Kartendienst“ das Protokoll des Schreibwegs (nicht des Konnektors), die drei Zeilenformen und die Überwachung samt Ende der Warnung
  - Prüfung: Sichtprüfung im Review
- **AC-12 (Spec 444):** Given `docs/specs/betrieb/eigener-kartendienst-444.md` / When die Änderung steht / Then nennt AC-6 dort zusätzlich die Erfolgszeile
  - Prüfung: Sichtprüfung im Review
- **AC-13 (Infra-Issue):** Given der Infra-Anteil / When er umgesetzt wird / Then gibt es ein Issue im Infra-Repo, auf das der dortige Commit verweist
  - Prüfung: Sichtprüfung im Review

## Known Limitations

- **Kopplung an den Wortlaut.** Ändert jemand die Zeilen in `overpass_eigen`, verstummt der Verlaufs-Teil des Checks still. Gegenmittel: der Vertragstest zum Präfix (AC-2) und der Kommentar an der Stelle; die Einheiten-Prüfung wirkt unabhängig davon weiter.
- **Zwei Repos, feste Reihenfolge.** Erst die Engine (Erfolgszeile) ausliefern, dann den Check. Läuft der Check ohne Erfolgszeile, warnt er nach einer Häufung nur länger, bis das Fenster abläuft.
- **Kein Zugriff, keine Aussage.** Ohne Kartenabfragen gibt es weder Rückfall- noch Erfolgszeilen; ein stiller Ausfall wird dann nur über die Einheiten (Socket nicht `active`, Container oder Proxy `failed`) sichtbar. Ein Dienst, der gesund wirkt, aber bei jedem Zugriff scheitert, fällt erst bei der dritten Abfrage auf.
- **Passive Prüfung.** Der Check belegt nicht, dass der Container beim nächsten Zugriff startet; das zeigt erst der Zugriff selbst.

## Definition of Done

- [ ] AC-1 bis AC-13 durch Test 1 bis 13 und Sichtprüfung belegt
- [ ] Engine ausgeliefert (Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks` grün), danach Check im Infra-Repo mit Issue dort
- [ ] Auf der Instanz: Erfolgszeile im Journal nachgewiesen, Check zeigt ok bei ruhendem Dienst
- [ ] Issue #573 erst schließen, wenn Engine, Check und Doku live sind

## Changelog

- 2026-11-14: Initiale Spec (#573)
