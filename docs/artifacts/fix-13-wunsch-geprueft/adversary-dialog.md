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

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/vorlage.html:5320
  Description: Karte eines Wunsches mit Rückmeldestatus „neu“ und Vorschlag zeigt weiter das Chip „wird geprüft“, steht aber jetzt in der Spalte „Geprüft“.
  Spec requirement: Spec „Was ändert sich“ — Wunsch mit Vorschlag steht unter „geprüft“ (Spalte); Chip nicht erwähnt.
  Conflict: Kosmetisch widersprüchlich, kein Datenfehler, nicht von der Spec gefordert.
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
  Code reference: engine/tests/test_seite.py:486
  Evidence: Beispielwunsch mit Status „neu“ plus Vorschlag aus plan/wuensche.yaml; Test grün.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 45 passed, 0 failed, 0 übersprungen
Edge cases: geprüft, nur kosmetisches LOW-Finding F001 (Chip „wird geprüft“)
Regressions: None found
Checklist: 5/5 points proven

## Geprüfte Dateien

- sha256:8ce1412191615541aedb2f43cd3d0cc9eba7b8076021efee62cf4e003cec1ff1  engine/rueckmeldungen.py
- sha256:a8aa6b9ff3aa3043a6f59f7c5083b99adf5f6c1459394ca7140bfd8f93e56a59  engine/tests/test_brett.py
- sha256:bafaba1070cfd25784833cc81a7a5f88b55ed8231714552911aec013e392dbe9  engine/tests/test_seite.py
- sha256:6f5cbfa1fae96113c0272cf0a0d75ce79a8f4c0542f20e96df92cb9ad0157414  engine/vorlage.html

## Prüfbasis

- base: 42b6017f3ff3820c624608387a2890348c574406
- blob:480e87645c83266349fd0b6486109d683c3c9158  engine/rueckmeldungen.py
- blob:316014efcbaefd6198321186c4e2421e735156e8  engine/tests/test_brett.py
- blob:973c57f803f9c2ac8df459a013eb9d5725423102  engine/tests/test_seite.py
- blob:6ea4f2efef18eeae5c0dc031c0c9dc32e3c724cf  engine/vorlage.html
