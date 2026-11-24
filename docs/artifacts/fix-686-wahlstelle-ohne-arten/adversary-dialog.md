# Adversary Dialog — fix-686-wahlstelle-ohne-arten
Spec: docs/specs/konnektor/plan-ohne-arten-686.md
Datum: 2026-11-24 14:13

## Checkliste
- [x] **AC-1:** Given eine Reise ohne Arten / When `choice_create` mit zwei Optionen läuft / Then lehnt der Schreibweg mit `schreiben.plan.ohne_arten` ab, es gibt keine neue Fassung und keine offene Frage F-… ohne Wahlstelle. Test: `test_wahlstelle_ohne_arten_wird_abgelehnt`.
- [x] **AC-2:** Given eine Reise ohne Arten / When `item_create`, `start_end_set`, `day_create` oder `fixed_date_set` laufen / Then lehnt jedes mit demselben Text ab und `reise.json` bleibt ohne `routen`. Test: `test_plan_werkzeuge_ohne_arten_werden_abgelehnt`.
- [x] **AC-3:** Given der Ablehnungstext / When er in jeder Sprache aufgelöst wird / Then ist er vorhanden und nennt den Weg über Arten (`kinds_adopt`, `kind_define`); der Text steht nur in den `texte_<sprache>.py`. Test: `test_ablehnung_in_allen_sprachen`.
- [x] **AC-4:** Given eine Reise ohne Arten, aber mit Gerüst `plan/routen.yaml` / When Arten übernommen oder definiert werden / Then steht `routen` sofort in `reise.json` und der Plan ist ohne weiteres Werkzeug sichtbar und beschreibbar. Tests: `test_arten_uebernehmen_traegt_vorhandenen_plan_ein`, `test_art_definieren_traegt_plan_ein`.
- [x] **AC-5:** Given eine Reise mit Arten und noch ohne Plan / When das erste Plan-Werkzeug gelingt / Then ist der Plan eingetragen und im Probebau enthalten. Test: `test_plan_nach_erstem_werkzeug_sofort_sichtbar`.
- [x] **AC-6:** Given eine Reise mit Arten und `plan/routen.yaml`, aber ohne `routen` / When `neu.py nachziehen` (auch über `nachziehen-speicher` beim Veröffentlichen) läuft / Then wird der Eintrag ergänzt, ein zweiter Lauf ändert nichts, die Vorschau schreibt nichts. Tests: `test_nachziehen_heilt_altlast`, `test_nachziehen_speicher_beim_veroeffentlichen_heilt_altlast`.
- [x] **AC-7:** Given die rohe Funktion / When Gerüst, `umbrechen` und `nachziehen` in einer Reise ohne Arten schreiben / Then lehnen sie nicht ab. Test: `test_roh_schreiben_ohne_arten_erlaubt`.
- [x] **AC-8:** Given die beiden Beispielreisen / When Plan-Werkzeuge laufen und der Generator baut / Then verhalten sie sich wie bisher, ohne Änderung an den Beispielreisen. Test: `test_beispielreisen_unveraendert`.
- [x] **AC-9:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen.

## Dialog

### Runde 1
**Adversary:** Behauptung: ohne Arten wird jedes Plan-Werkzeug abgelehnt, mit Arten steht der Plan sofort in reise.json. Beweis gefordert. Gezielter Lauf (Ausgabe in docs/artifacts/fix-686-wahlstelle-ohne-arten/adversary-test-output.txt): 416 passed, 0 failed, 0 übersprungen (test_plan_ohne_arten_686, test_schreiben, test_neu, test_texte, test_hinweis_604, test_konnektor*). Gesamtlauf 3615 passed laut test-green-output.txt (nicht wiederholt).

Confirmation:
  AC: AC-1
  Code reference: engine/schreiben.py:973
  Evidence: routen_speichern wirft Ablehnung("schreiben.plan.ohne_arten") vor jedem Schreiben; Schreiber.schreiben verwirft die Arbeitskopie, also keine Fassung und keine verwaiste Frage. Geprüft durch test_wahlstelle_ohne_arten_laesst_den_speicher_unveraendert (vergleicht den ganzen Speicherzustand).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/schreiben.py:976
  Evidence: Alle 30 Aufrufer in schreiben.py laufen über routen_speichern (grep); parametrisierter Test für item_create, start_end_set, day_create, fixed_date_set grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:3248
  Evidence: Schlüssel schreiben.plan.ohne_arten nennt kinds_adopt und kind_define; Entsprechung in engine/texte_en.py:3247. test_texte und test_ablehnung_in_allen_sprachen grün; Text nur im Katalog.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/schreiben.py:356
  Evidence: arten_speichern ruft plan_sicherstellen, wenn plan/routen.yaml liegt; beide Tests (kinds_adopt, kind_define) grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/schreiben.py:979
  Evidence: routen_speichern ruft nach dem Schreiben plan_sicherstellen; Test Probebau enthält Wahlstelle grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/neu.py:1062
  Evidence: plan_eintragen_nachziehen: Vorschau (schreiben=False) meldet nur, zweiter Lauf liefert [] weil routen vorhanden; beide Tests grün (inkl. nachziehen-speicher).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/neu.py:355
  Evidence: umbrechen (neu.py:355), nachziehen (neu.py:1153) und Gerüst (schreiben.py:931) nutzen routen_datei_schreiben ohne Prüfung; routen_normalisieren schreiben.py:986 ebenso. Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:964
  Evidence: Mit Arten ändert sich nur der idempotente Eintrag; Beispielreisen haben ihn schon (plan_sicherstellen ändert nichts, wenn neu_ == routen). test_beispielreisen_unveraendert und test_hinweis_604 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/tests/test_plan_ohne_arten_686.py:1
  Evidence: 3615 passed im Gesamtlauf (docs/artifacts/fix-686-wahlstelle-ohne-arten/test-green-output.txt) plus eigener gezielter Lauf 416 passed.
  Status: CONFIRMED

**Implementierer:** (Rückmeldung der Entwicklung als Prüfhinweise übergeben, siehe Runde 2.)

### Runde 2
**Adversary:** Gezielte Angriffe auf die Hinweise.

1. Geänderte Prüfung im RED-Test (engine/tests/test_plan_ohne_arten_686.py:103): LEGITIM. Die Zeile davor (zustand == vorher) vergleicht den gesamten Speicher unverändert, das schließt jede neue Frage schon aus; die neue Prüfung (Titel der Wahlstelle nicht in offene-fragen.md) ist die präzisere Form, weil die Vorlage F-01 mitbringt. Keine Aufweichung.
2. test_schreiben.py:1197: Reihenfolge art_definieren vor ding_anlegen ist die vom Spec verlangte Folge (erst Arten); die Aussage des Tests (Plan entsteht beim ersten Eintrag) bleibt. Legitim.
3. Randfall nachziehen: kartenpunkte_umstellen (neu.py:1132) und orte_lage_zusammenfuehren (neu.py:1133) rufen arten_speichern (neu.py:715, 946), das jetzt über plan_sicherstellen (schreiben.py:356) still den Eintrag setzt, bevor plan_eintragen_nachziehen (neu.py:1155) läuft. Folge: Heilung geschieht, aber ohne Meldungszeile in genau dieser Kombination. Reine Kosmetik; Reihenfolge der Prüfung in der Vorschau bleibt korrekt (dort schreibt arten_speichern nicht). Als LOW notiert.
4. Fremde Aufrufer von routen_speichern: werkzeuge/adressen_holen.py:181 und werkzeuge/wissen_punkte_holen.py:171 arbeiten auf bestehenden Reisen mit Plan (routen_laden/Unterkünfte), also mit Arten; bei Reisen ohne Arten würde nun eine Ablehnung (Ablehnung-Ausnahme) statt stillem Schreiben kommen, was dem Zweck entspricht. Kein legitimer Schreiber ohne Arten gefunden: trip_create/Anlegen aus der Vorlage geht über Gerüst/plan_sicherstellen (roh, schreiben.py:931); Löschpfade und Wächter rufen routen_speichern nicht (grep: nur schreiben.py, werkzeuge, ein Test).
5. Doppelte plan_sicherstellen-Aufrufe (schreiben.py:357, 957, 979, 1525, neu.py:1073): idempotent, weil nur bei neu_ != routen geschrieben wird; neue W-IDs nur, wenn tagesplan fehlt.
6. reise.json ohne Datei: plan_sicherstellen prüft rj.exists() (schreiben.py:934); keine Ausnahme. Unlesbare reise.json: Ablehnung schreiben.reise_json.unlesbar, im Schreibweg zurückgerollt.
7. Reise ohne Arten, aber mit Plan und ohne Eintrag: nachziehen heilt nicht (korrekt, Bau-Regel), schreibt aber die Datei weiter roh (neu.py:1153) ohne Ablehnung.

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:1155
  Description: Wenn kartenpunkte_umstellen/orte_lage_zusammenfuehren im selben nachziehen-Lauf arten_speichern aufrufen, trägt dieses den Plan still ein; plan_eintragen_nachziehen findet routen schon vor und meldet nichts.
  Spec requirement: AC-6 — Eintrag wird ergänzt (erfüllt), Meldung nicht gefordert
  Conflict: Nur fehlende Meldungszeile, Zustand korrekt und idempotent.
  Remediation: Optional plan_eintragen_nachziehen vor Zeile 1132 aufrufen.

**Implementierer:** Kein Widerspruch zu erwarten; LOW ist kein Blocker.

### Runde 3
**Adversary:** Nachtrag zu AC-3: englischer Text nach Glättung geprüft (nennt kinds_adopt und kind_define, sinngleich zum deutschen, nur im Katalog).

Confirmation:
  AC: AC-3
  Code reference: engine/texte_en.py:3247
  Evidence: schreiben.plan.ohne_arten (en) lautet "...anything added now would not show up anywhere. Please add kinds first, either adopt templates (kinds_adopt) or define your own kind (kind_define)..."; test_plan_ohne_arten_686 und test_texte: 111 passed laut Koordinator.
  Status: CONFIRMED

**Implementierer:** Keine Einwände.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)


## Verdict
VERDICT: VERIFIED

Tests: 416 passed (gezielt), 3615 passed (Gesamtlauf, belegt), 0 failed, 0 übersprungen. Edge cases: nur F001 (LOW, kosmetisch). Regressions: keine. Checklist: 9/9 proven.

## Geprüfte Dateien

- sha256:acb1043e5cec97e255c7871588261e235f448fc7506a874f23fa2040e437c8c4  engine/neu.py
- sha256:7ed32244542a92c37cf0f9a6dc3ad65c0b08f26a39d62dfa6caf1c5037a0abda  engine/schreiben.py
- sha256:0ba1fb49801882ddcd1251953c703352abbe90931a887b74c68059068c9ff521  engine/tests/test_plan_ohne_arten_686.py
- sha256:5e4e143e204910840fbeb7a5c31e1785f11ca9d62a0e46a2ea3375d72ec00f7c  engine/texte_de.py
- sha256:3a4ef895a00785ef26cda3d735a37097f386bf5bfd82835e090aa7c0d505ee78  engine/texte_en.py

## Prüfbasis

- base: 627fed38ed56a5e29a4b72dc8b6b0d2561f0e24a
- blob:d09a0970743f4cb64e9424ca5fb8d119e34b436a  engine/neu.py
- blob:2175106f773ed4983fea059bfb5a1a06c41a8215  engine/schreiben.py
- blob:94f8d533d086b4f242ed60e26b6d3f2d0d03c36e  engine/tests/test_plan_ohne_arten_686.py
- blob:79e60b6107a7a9ee507e3e874ddb3020c720b991  engine/texte_de.py
- blob:4ab81bbbbd19c72f9eacef7beb0b060911c5e887  engine/texte_en.py
