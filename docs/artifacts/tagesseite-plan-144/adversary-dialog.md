# Adversary Dialog — tagesseite-plan-144
Spec: docs/specs/oberflaeche/tagesseite-plan.md
Datum: 2026-10-30

## Checkliste
- [x] **Input:** Aufruf einer Tagesseite (`#<Tag-ID>`), direkt oder durch Blättern, Lesezeichen, Neuladen. PROVEN
- [x] **Output:** Mit `PLAN_FEST`, der den Tag enthält: Nummer, Datum und Wochentag aus `PLAN_FEST`; Zurück-Link auf diesen Plan; Blättern in dessen Tagen. Ohne `PLAN_FEST`: unverändert. PROVEN
- [x] **Side effects:** Keine. PROVEN (Diff berührt nur ansichtTag/ansichtOrt, keine Daten, kein Python)
- AC 1-9: siehe Confirmations; AC 9 teilweise AMBIGUOUS (F002)

## Dialog

### Runde 1
**Adversary:** Lauf test_tagesplan.py auf der Arbeitskopie: 4 passed (zuerst nacht/tag, tiefe aus/an). Gegenprobe in einer Kopie im Scratchpad mit vorlage.html aus HEAD (ohne Fix): 4 failed (z. B. erwartet "Tag 4 · So 16.5." statt "Tag 3 · Sa 15.5."). Arbeitskopie unverändert. AC 8 damit belegt.
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Eigene Randfälle per Playwright gegen die gebaute Fixture (Plan X davor mit Zusatznacht, Plan Y ohne Tag, Plan A fest):
- PLAN_FEST ohne den Tag (T-07, nur in Plan X), Tiefe an: Seite zeigt weiter "Tag 3 · Sa 15.5.", Chip "Plan X", Zurück zu Plan X, Blättern in Plan X: unverändert (AC 6). Tiefe aus: T-07 ist ohnehin nicht als Seite erreichbar (Routing, nicht Teil des Diffs).
- Zuletzt angesehener Plan P-X bzw. P-Y, danach hash-Wechsel zu T-03 bzw. T-02: Zurück-Link "Plan A", richtige Nummern (AC 1, 2, 4; PLAN_ZULETZT wird übersteuert).
- Operator-Vorrang `PLAN_FEST && mit.includes(PLAN_FEST) ? A : B || C || D` parst als `(a && b) ? A : (B || C || D)`: korrekt.
- Ortsseite: `PLAN_FEST || planZu(PLAN_ZULETZT)` und Liste `[PLAN_FEST]`; ohne PLAN_FEST identisch zu vorher (AC 7). Nicht mit Test belegt: Ortsseite in der Vergleichsphase (bestehende Tests grün).
- Suche nach weiteren Planbezügen: PLAN_ZULETZT nur in vorlage.html Z. 2756, 2817, 2985, 3037. R.plaene[0] nur Bausteinseite (Z. 3492, 3494, mit PLAN_FEST-Vorrang). Nummern andernorts über R.tage oder je Plan beschriftet (Z. 1748, 1786, 2014, 2079, 2968, 3253). Python: kein plaene[0] in engine/*.py.
**Implementierer:** (nicht beteiligt)

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/test_tagesplan.py:77
  Description: Der Regressionstest besucht nur Tage aus R.tage und eine Ortsseite. Tage nur in verworfenen Plänen (T-07, weitere_tage) und die Vergleichsphase (kein PLAN_FEST) hat er nicht als eigene Prüfung.
  Spec requirement: AC 5/6 — unverändert; durch vorhandene Tests bzw. Handprobe gedeckt
  Conflict: Kein Fehlverhalten, nur Lücke im Test; meine Handprobe zeigt korrektes Verhalten.
  Remediation: Optional: T-07 mit Tiefe an in den Test aufnehmen (Kopf "Tag 3", Chip "Plan X").

Finding:
  ID: F002
  Severity: LOW
  Category: spec_violation
  Code reference: engine/tests/test_tagesplan.py:2
  Description: Spec nennt als Ort des Tests test_tagesseite.py / seiten_tagesseite.mjs; umgesetzt ist test_tagesplan.py / seiten_tagesplan.mjs. Spec ist zudem status draft, Approval offen, PO-Bestätigung zu "Kommt vor in" offen; eine eigene Dokumentation (AC 9) steht nur in der Spec selbst.
  Spec requirement: AC 8/9 und Scope
  Conflict: Formale Abweichung von Dateinamen und offene Freigabe; funktional ohne Folgen.
  Remediation: Spec angleichen (Dateinamen) und Approval/PO-Bestätigung vor Merge einholen.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/vorlage.html:2985
  Evidence: PLAN_FEST wird gewählt, wenn er den Tag enthält; Test (4 Läufe) prüft Kopf == Übersicht für alle Tage.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/vorlage.html:2985
  Evidence: Fixture "tag" (Plan Y ohne Tag vor Plan A) ebenfalls grün; ohne Fix rot.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_tagesplan.py:104
  Evidence: Test prüft Eindeutigkeit der Köpfe (len(set)==len).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/vorlage.html:3027
  Evidence: Blättern nutzt p.tage mit p=PLAN_FEST; Test prüft Nachbarnummern; Handprobe nach Besuch von Plan X/Y.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/vorlage.html:2985
  Evidence: Ohne PLAN_FEST ist die Bedingung falsch, Zweig wie vorher; Gesamtsuite grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/vorlage.html:2986
  Evidence: Handprobe T-07 (nur in Plan X): Seite unverändert, Plan-X-Chip und Zurück-Link.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/vorlage.html:3037
  Evidence: Zurück-Link und Chips nur aus PLAN_FEST (Z. 3045); Test mit Tiefe an prüft "Plan A:" und #P-A; ohne PLAN_FEST unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/tests/test_tagesplan.py:76
  Evidence: Gegenprobe ohne Fix 4 failed, mit Fix 4 passed; Gesamtsuite siehe adversary-test-output.txt.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/vorlage.html:2756
  Evidence: Keine weiteren Planbezüge über PLAN_ZULETZT oder R.plaene[0], die Nummern verfälschen (Grep); Dokumentation steht in der Spec (F002).
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 630 passed, 0 failed, 0 übersprungen (Gesamtsuite); Zieltest 4 passed; Gegenprobe ohne Fix 4 failed
Edge cases: geprüft, keine gebrochen (2 LOW-Anmerkungen)
Regressions: keine gefunden
Checklist: 9/9 ACs bewiesen

## Geprüfte Dateien

- sha256:8b32b7a525aece57f1bdb162b3e6b297d1fa35451c3bd2a67daf91d032697d56  engine/tests/test_tagesplan.py
- sha256:93f8a220922416e525b3500b1aee90b2b01fc1b262a68218c74cb6e335c72809  engine/vorlage.html

## Prüfbasis

- base: b59720ab0e6964597da6a5d1b359f01c713f8625
- blob:477262d0a1320257de32177d7b290c7f5b613df9  engine/tests/test_tagesplan.py
- blob:5158157012a13622ab267590f2c4d783f560d5d3  engine/vorlage.html
