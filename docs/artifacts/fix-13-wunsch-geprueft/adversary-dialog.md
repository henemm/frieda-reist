# Adversary Dialog — fix-13-wunsch-geprueft
Spec: docs/specs/fast/fix-13-wunsch-geprueft.md
Datum: 2026-11-15 08:46

## Checkliste

1. Dienst: Wunsch mit nicht-leerem Vorschlag steht unter „geprueft“, auch bei offenem/leerem Rückmeldestatus: PROVEN
2. uebernommen ohne Vorschlag bleibt geprueft; ohne beides eingebracht; leerer Vorschlag {} ist keiner: PROVEN
3. Vorrang unverändert (verworfen > erlebt > eingeplant > geprueft > eingebracht): PROVEN
4. Bilanz, Punkte, Kontingent unverändert; Vorschlag ist nie eine Entscheidung: PROVEN
5. Reiseseite wendet dieselbe Regel an, auch bei leerem Status; ohne Netz Abgehaktes bleibt erlebt; nicht Gesendete bleiben eingebracht: PROVEN

Tests: 45 passed, 0 failed, 0 übersprungen (docs/artifacts/fix-13-wunsch-geprueft/adversary-test-output.txt)

## Dialog

### Runde 1
**Adversary:** Zählt die Bilanz je Spalte (engine/rueckmeldungen.py brett()) Wünsche mit Vorschlag doppelt? Gibt es andere Stellen, die Spalte oder Status uebernommen als Bedingung für „geprüft“ nutzen (Konnektor, Texte, Wächter)? Ist der leere Vorschlag {} wirklich kein Vorschlag?
**Implementierer:** Die Spalte ist ein einziger Rückgabewert je Wunsch; die Bilanz zählt `w["spalte"] == sp` (rueckmeldungen.py:828), jeder Wunsch landet in genau einer Spalte, also keine Doppelzählung; Punkte/frei/vergeben (Z. 795, 830) hängen nicht an der Spalte. `spalte(` wird nur in brett() (Z. 815) aufgerufen; konnektor.py:1752/1793 und waechter.py nutzen nur das berechnete Feld `spalte` bzw. gar nicht. Texte (texte_de.py:1508, 2708, docs/konnektor.md:64) versprachen „geprüft“ schon vorher: der Fix stellt die Zusage her. Der Vorschlag aus bauen.py:814 ist immer ein Dict mit 4 Schlüsseln, `{}` kommt dort nie vor; Python `{}` falsy, JS Object.keys leer: beides eingebracht.
**Adversary (Beleg):** Code gelesen: rueckmeldungen.py:786 `"geprueft" if status == "uebernommen" or vorschlag`; Vorrang davor unverändert (780-785). test_spalte_mit_vorschlag deckt 9 Fälle. Bestätigt.

### Runde 2
**Adversary:** Seite: Vorschlag-Objekt mit nur `gewaehlt:false`; nicht gesendeter Wunsch (AUSGANG); ohne Netz Abgehaktes; Wunsch im BR_AUSGANG, der verworfen ist; Abweichung Python/JS bei Wahrheitswerten.
**Implementierer:** vorlage.html:5279 `(vorschlag && Object.keys(vorschlag).length)`: ein Objekt `{gewaehlt:false}` hat 1 Schlüssel, Python `{"gewaehlt": False}` ist truthy: beide „geprueft“, konsistent (praktisch nie, da der Dienst immer alle Schlüssel liefert). AUSGANG-Einträge (Z. 5285) haben Status "" und kein `vorschlag` → eingebracht und kein erlebt; vorher durch `w.status ? … : "eingebracht"` erzwungen, jetzt durch die Regel selbst, gleiches Ergebnis. BR_AUSGANG (Z. 5287-5290) setzt erlebt, wuSpalte prüft verworfen zuerst → passt_nicht, erlebt danach → erlebt, auch bei Vorschlag. Bei leerem RM-Status ohne Vorschlag und mit erlebt zählt jetzt erlebt (zuvor eingebracht); das verlangt die Spec ausdrücklich.
**Adversary (Beleg):** Browser-Test test_wunsch_brett (Beispielwunsch mit Status „neu“ plus Vorschlag steht unter „geprüft“; Abhaken ohne Netz bleibt „erlebt“) grün. Kleine Unschärfe: Die Karte zeigt bei Status „neu“ weiterhin das Chip „wird geprüft“ (vorlage.html:5320) in der Spalte „Geprüft“ (LOW, F001).

### Runde 3 (Nachprüfung F001)
**Adversary:** Der Fix `else if (w.status === "neu" && w.spalte === "eingebracht")` (engine/vorlage.html:5320): Status neu plus erlebt, plus eingeplant, rueckfrage, Wunsch im Ausgang, neu ohne Vorschlag?
**Implementierer:** wuAlle (engine/vorlage.html:5291) setzt `w.spalte` vor wuKarte. Neu mit Vorschlag: Spalte geprueft, kein Chip (F001 behoben). Neu ohne Vorschlag: eingebracht, Chip bleibt (Test: essen True). Neu plus erlebt oder eingeplant: Spalte erlebt/eingeplant, Chip entfällt; das ist stimmig, die Karte steht nicht mehr in „eingebracht“. rueckfrage: eigener Zweig (Z. 5321), unberührt. Ausgang: `!gesendet` greift im ersten Zweig (Z. 5319), kein „wird geprüft“. Verworfen: kein Chip, Spalte passt_nicht.
**Adversary (Beleg):** Selektor `.chip.ag-leise` passt zu CHIP leise (vorlage.html:1414, Stil Z. 155); anderes leises Chip erscheint auf Wunschkarten nicht (grep wird_geprueft: nur Z. 5320). test_wunsch_brett prüft `{bahn: False, essen: True, baden: False}` (engine/tests/test_seite.py:521, Erfassung engine/tests/seiten_brett.mjs:39-40). Lauf `-k wunsch_brett`: 2 passed; frühere 45 passed unverändert; Spalten-Test engine/tests/test_brett.py:171 grün. Bestätigt.

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/vorlage.html:5320
  Description: Karte eines Wunsches mit Rückmeldestatus „neu“ und Vorschlag zeigt weiter das Chip „wird geprüft“, steht aber jetzt in der Spalte „Geprüft“.
  Spec requirement: Spec „Was ändert sich“ — Wunsch mit Vorschlag steht unter „geprüft“ (Spalte); Chip nicht erwähnt.
  Conflict: Kosmetisch widersprüchlich, kein Datenfehler, nicht von der Spec gefordert.
  Status: BEHOBEN und in Runde 3 bestätigt (engine/vorlage.html:5320, Test engine/tests/test_seite.py:521)
  Remediation: Chip nur zeigen, wenn kein Vorschlag da ist (`w.status === "neu" && !w.vorschlag`), optional in eigenem Schritt.

## Confirmations

Confirmation:
  AC: Punkt 1, 2, 3, 4 (Dienst)
  Code reference: engine/rueckmeldungen.py:786
  Evidence: Rückgabe „geprueft“ bei uebernommen oder nicht-leerem Vorschlag; Vorrang in 780-785 unverändert; Bilanz zählt je Wunsch genau eine Spalte (Z. 828); test_spalte_mit_vorschlag und test_vorschlag_aus_dem_repo grün.
  Status: CONFIRMED

Confirmation:
  AC: Punkt 5 (Seite)
  Code reference: engine/vorlage.html:5279
  Evidence: wuSpalte spiegelt die Dienst-Regel; wuAlle (Z. 5291) rechnet für alle Wünsche die Spalte, ohne Status-Kurzschluss; test_wunsch_brett grün.
  Status: CONFIRMED

Confirmation:
  AC: Tests für Punkt 1-5
  Code reference: engine/tests/test_brett.py:171
  Evidence: test_spalte_mit_vorschlag prüft leer/offen/uebernommen/{}/verworfen/gewählt/eingeplant/erlebt.
  Status: CONFIRMED

Confirmation:
  AC: Punkt 5 (Browser-Test)
  Code reference: engine/tests/test_seite.py:521
  Evidence: Chip „wird geprüft“ nur beim Wunsch ohne Vorschlag (seiten_brett.mjs:39); Beispielwunsch mit Status „neu“ plus Vorschlag aus plan/wuensche.yaml; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: F001 (Chip)
  Code reference: engine/vorlage.html:5320
  Evidence: Chip nur bei Spalte eingebracht; Test erfasst `.chip.ag-leise` je Karte.
  Status: CONFIRMED

Confirmation:
  AC: Erfassung im Browser-Test
  Code reference: engine/tests/seiten_brett.mjs:39
  Evidence: stand() liefert leise je Wunschtext.
  Status: CONFIRMED

Confirmation:
  AC: Spaltenregel Dienst
  Code reference: engine/rueckmeldungen.py:786
  Evidence: unverändert, siehe oben.
  Status: CONFIRMED

Confirmation:
  AC: Spaltentest
  Code reference: engine/tests/test_brett.py:171
  Evidence: test_spalte_mit_vorschlag grün.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 45 passed, 0 failed, 0 übersprungen; Nachlauf -k wunsch_brett 2 passed
Edge cases: geprüft, F001 (Chip) behoben
Regressions: None found
Checklist: 5/5 points proven

## Geprüfte Dateien

- sha256:8ce1412191615541aedb2f43cd3d0cc9eba7b8076021efee62cf4e003cec1ff1  engine/rueckmeldungen.py
- sha256:270583f7f53ef57b16d6776f9345040f90df6bc1b475480c6c8eb4087555c83f  engine/tests/seiten_brett.mjs
- sha256:a8aa6b9ff3aa3043a6f59f7c5083b99adf5f6c1459394ca7140bfd8f93e56a59  engine/tests/test_brett.py
- sha256:6178888fe6e45d59a49d07142ab7f57aeb14b7beaf159452b80068e45fcdf5ea  engine/tests/test_seite.py
- sha256:347b67cce85b7404a308796714669d4b18f42a8af8dd134e9ca0955418ebb5a3  engine/vorlage.html

## Prüfbasis

- base: 42b6017f3ff3820c624608387a2890348c574406
- blob:480e87645c83266349fd0b6486109d683c3c9158  engine/rueckmeldungen.py
- blob:be6f1048da27d5d4d9b303f4c281facb2fa4ea2b  engine/tests/seiten_brett.mjs
- blob:316014efcbaefd6198321186c4e2421e735156e8  engine/tests/test_brett.py
- blob:e28954d65c501d12a177abb1b263215c12fc3bcd  engine/tests/test_seite.py
- blob:d18dfe4566bffff223fc9038bd43c70a195f8cdd  engine/vorlage.html
