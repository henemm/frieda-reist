# Adversary Dialog — alternativen-453-dinge
Spec: docs/specs/routen/dinge-als-moeglichkeit-453.md
Datum: 2026-11-17 12:29

## Checkliste
- [x] **AC-1 (Aufteilen):** Given eine Möglichkeit mit `dinge: [E-02, A-01, O-04]`, when die Reise lädt und baut, then stehen `strecken`, `aufenthalte` und `orte` in der Ausgabe der Option wie bei den alten Feldern, ohne Fehler.
- [x] **AC-2 (Reihenfolge):** Given `dinge: [O-06, O-04]`, when die Reise lädt, then bleibt die Reihenfolge der Eingabe in der Gruppe `orte` erhalten.
- [x] **AC-3 (unbekannter Präfix):** Given `dinge: [X-01]`, when die Reise lädt, then genau ein Prüffehler mit Wahlstelle, Möglichkeit und ID; der Bau meldet ihn wie die übrigen Optionsfehler.
- [x] **AC-4 (Existenz je Präfix):** Given je ein unbekanntes `U-99`, `E-99`, `A-99`, `O-99` in einer Möglichkeit, when die Reise lädt, then gibt es je einen Prüffehler (auch für U und E, die vorher ungeprüft blieben).
- [x] **AC-5 (alte Felder):** Given eine Option mit `unterkuenfte`, `aufenthalte`, `orte` oder `strecken` (allein oder neben `dinge`), when die Reise lädt, then ein Prüffehler mit Hinweis auf `dinge`; `folge` bleibt ohne Fehler.
- [x] **AC-6 (Präfixregel):** Given Möglichkeiten (a) `{U}` allein, (b) `folge` allein, (c) `{E, A, O}` in jeder Teilmenge, then gültig; Given `{U, O}`, `{U, E}`, `{folge, dinge}` oder leeres `dinge`, then ungültig (`option_inhalt_ok` falsch bzw. Prüffehler).
- [x] **AC-7 (Schreiben):** Given eine Testreise, when `choice_create`/`option_create` Optionen mit `dinge` anlegen, then steht `dinge` in `plan/routen.yaml` als Liste der IDs in Eingabereihenfolge, der Verlauf enthält `wechsel("dinge", …)`, nichts wird überschrieben; ein unbekanntes Ding oder eine ungültige Mischung wird mit Begründung abgelehnt (`schreiben.option_bauen.2`).
- [x] **AC-8 (Ändern):** Given eine bestehende Möglichkeit, when `option_update` `dinge` setzt, ersetzt oder leert, then gilt die Präfixregel auf dem zusammengeführten Stand (`schreiben.option_aendern.5`); ein Update mit nur `dinge` ist eine Änderung, nicht `option_aendern.8`; die Entscheider-Sperre `option_aendern.9` bleibt.
- [x] **AC-9 (Schema):** Given `OPTION_FELDER` und das erzeugte Schema, then enthält es `things` (Array von Strings, Beschreibung aus dem Katalog) mit deutschem Alias `dinge` und keines der vier alten Felder.
- [x] **AC-10 (Übergang):** Given ein Aufruf mit den alten Parametern (englisch `accommodations`, `stays`, `places`, `legs` und deutsch `unterkuenfte`, `aufenthalte`, `orte`, `strecken`), when der Konnektor ihn verarbeitet, then wird er angenommen und als `dinge` geschrieben (Eingabereihenfolge: Unterkünfte, Aufenthalte, Orte, Strecken, wie sie übergeben wurden), und das Ergebnis ist dasselbe wie bei `things`.
- [x] **AC-11 (Mischung):** Given ein Aufruf mit `things`/`dinge` und zugleich einem alten Parameter, then Ablehnung mit Begründung aus dem Katalog; nichts wird geschrieben.
- [x] **AC-12 (Umstellen):** Given eine Reise mit alten Feldern an Optionen, when `neu.py nachziehen` läuft, then haben alle Optionen `dinge` an Stelle des ersten alten Felds, die alten Felder sind weg, die Reihenfolge der IDs bleibt, `folge` und andere Felder bleiben unberührt, und die Meldung kommt aus `texte`; die Reise baut danach mit gleicher Ausgabe wie vorher.
- [x] **AC-13 (Idempotenz):** Given dieselbe Reise nach `nachziehen`, when `nachziehen` erneut läuft, then ist das Ergebnis byte-gleich und es gibt keine Meldung.
- [x] **AC-14 (Server-Variante):** Given eine Reise im Reisespeicher mit mehreren Versionen, when `nachziehen_speicher` läuft, then steht die umgestellte Fassung als neue, angehängte Version; ein zweiter Lauf legt keine weitere an.
- [x] **AC-15 (Wanderung):** Given `beispiel/reisen/beispielreise`, when sie baut, then nutzen V-03 und V-06 `dinge:`, es gibt keinen Fehler, und Summe 595 min, 25,4 km, ↑1075, ↓1025 sowie die Pläne P-A 610 min und P-B 595 min sind unverändert.
- [x] **AC-16 (Stadtwochenende):** Given `beispiel/reisen/stadtwochenende` (keine Wahlstellen), when sie baut, then baut sie ohne Fehler und Warnung, `daten.json` ist gleich dem Stand vorher; Given dazu im Test eine erfundene Wahlstelle am Sonntag: Möglichkeit a `dinge: [A-02]` (Stadtmuseum) gegen Möglichkeit b `dinge: [A-90]` (erfundenes zweites Ziel, nur in den Testdaten angelegt), then baut sie ohne Fehler, die Beispielreise selbst bleibt unverändert.
- [x] **AC-17 (Seite unverändert):** Given die gebaute Wanderung vor und nach der Umstellung, then sind die Seitendaten `R.wahlstellen[].optionen[]` inhaltlich gleich (gleiche Gruppen `unterkuenfte`, `aufenthalte`, `orte`, `strecken`, `folge`); `vorlage.html` und `karte.py` sind nicht geändert; die Browser-Tests `seiten_option_aufenthalt.mjs` und `seiten_option_ort.mjs` bestehen unverändert.
- [x] **AC-18 (Ableiten):** Given eine Reise ohne `arten.yaml` mit `dinge` an Optionen, when `arten_ableiten` und `aufraeumen.art_der_option` laufen, then liefern sie dieselben Arten wie vorher mit den alten Feldern.
- [x] **AC-19 (Texte):** Given alle Sprachdateien, then stehen die neuen und geänderten Schlüssel (`konnektor.feld.option_felder.dinge`, `pruefung.routen.option_*`, `schreiben.option_bauen.2`, `schreiben.option_aendern.5`, Nachziehmeldung, Mischungs-Ablehnung) in allen Sprachen, und die Ausnahmelisten in `engine/tests/test_texte.py` sind nicht länger geworden.
- [x] **AC-20 (Gesamtlauf):** `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen (CI: `tests (leer)`, `tests (instanz)`, `gitleaks` auf dem vorgespulten Commit).
- [x] **AC-21 (Instanz-Tests, Nachweis im PR-Text):** Weil Schema und Meldungstexte sich ändern, laufen vor dem Vorspulen die Tests der einbindenden Instanzen mit dem Branch (Anleitung im Reisen-Repo der Instanz); es kommt kein Fehler gegenüber `main` hinzu. (Orchestrator: belegt in docs/artifacts/alternativen-453-dinge/instanz-tests.md, kein neuer Fehler gegenüber main)

## Dialog

### Runde 1
**Adversary:** Tests gelaufen: gezielte Suite (test_option_dinge, test_option_orte, test_option_aufenthalte, test_schreiben, test_neu, test_texte) = 407 passed, 0 failed, 0 übersprungen (adversary-test-output.txt). Gesamtsuite laut Entwickler 3161 passed. Eigene Probeläufe gegen die Spec; alle ACs einzeln geprüft.

Confirmation:
  AC: AC-1
  Code reference: engine/routen.py:488
  Evidence: dinge_aufteilen teilt nach Präfix in unterkuenfte/aufenthalte/orte/strecken; dinge_aufteilen_alle (engine/routen.py:746) arbeitet auf Kopien (dict(o)) vor der Prüfschleife; Test test_dinge_wird_in_gruppen_aufgeteilt_und_baut grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/routen.py:493
  Evidence: Schleife über die Eingabeliste, Append je Gruppe, Reihenfolge bleibt; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/routen.py:769
  Evidence: Probe: [4], [o-04], [""], [None], [O-04a] ergeben je genau einen Prüffehler mit Wahlstelle, Möglichkeit und ID.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/routen.py:776
  Evidence: Existenzprüfung je Gruppe gegen self.unterkuenfte/aufenthalte/orte/strecken; parametrisierter Test für U/E/A/O grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/routen.py:766
  Evidence: jedes alte Feld an einer Option gibt option_altes_feld, auch neben dinge; folge bleibt fehlerfrei.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/schreiben.py:4060
  Evidence: dinge_liste prüft Form und Existenz je Präfix; Eingabereihenfolge, Verlauf, PLAIN_FELDER ohne Anführungszeichen; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/schnittstelle.py:101
  Evidence: dinge -> things in PARAMETER; OPTION_FELDER ohne alte Felder; Schematest grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/konnektor.py:259
  Evidence: Hinweis 1 geprüft: dinge_uebersetzen lässt bei Mischung die alten Felder stehen, der Schreibweg lehnt ab (engine/schreiben.py:4091). Probe: wahlstelle_anlegen mit gültiger Option a und gemischter Option b -> Ablehnung schreiben.option_dinge.gemischt, routen.yaml byte-gleich (kein Teil-Schreiben: alle Optionen werden vor dem Speichern gebaut). Texte in beiden Sprachen (engine/texte_de.py:1822, engine/texte_en.py:1821). Nur der Ort der Ablehnung weicht vom Wortlaut ab, das Ergebnis erfüllt AC-11.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/neu.py:1234
  Evidence: dinge_nachziehen setzt dinge an der Stelle des ersten alten Felds, löscht alte Felder, Meldung über texte.t; Hinweis 4 (dinge plus alte Felder: alte IDs angehängt, ohne Dopplung) ist von der Spec ("nichts doppelt") gedeckt.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/neu.py:1241
  Evidence: ohne alte Felder continue, keine Änderung, keine Meldung; Idempotenztest grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/neu.py:1263
  Evidence: nachziehen_speicher nutzt nachziehen; Test mit mehreren Versionen und zweitem Lauf grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/routen.py:746
  Evidence: Beispielreise baut mit dinge, Summen und Pläne unverändert; Rohdaten bleiben unverändert (Kopie).
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/routen.py:505
  Evidence: erfundene Wahlstelle A gegen A (A-02/A-90) gültig über Präfixregel; Stadtwochenende unberührt; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: engine/routen.py:769
  Evidence: Seitendaten behalten Gruppen (SEITE_VORHER-Vergleich grün); vorlage.html und karte.py nicht im Diff.
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: engine/neu.py:432
  Evidence: art_der_option und arten_ableiten lesen über dinge_aufteilen; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: engine/texte_de.py:1822
  Code reference: engine/texte_en.py:1821
  Evidence: neue Schlüssel in de und en (engine/texte_en.py:1821, 2952, 3157), test_texte grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-20
  Code reference: engine/schreiben.py:4051
  Evidence: gezielte Suite 407 passed; Gesamtsuite laut Entwickler 3161 passed (nicht erneut vollständig gelaufen).
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/konnektor.py:259
  Evidence: alte Parameter englisch und deutsch werden zu dinge (Reihenfolge nach Feldgruppe U, A, O, E); Ergebnis wie things. Siehe aber F001 und F003.
  Status: CONFIRMED

Finding:
  ID: F001 (Runde 1: offen; Runde 2: BEHOBEN)
  Severity: MEDIUM
  Category: regression
  Code reference: engine/schreiben.py:4099
  Description: option_aendern ersetzt dinge als Ganzes. Über den Übergang (engine/konnektor.py:259) wird aus einem alten Einzelparameter ein vollständiges dinge. Probe: Option mit dinge [E-04, O-03]; option_update mit nur places [O-06] -> dinge [O-06] (E-04 verloren); option_update mit legs [] -> dinge komplett leer. Vorher änderte jeder alte Parameter nur sein eigenes Feld.
  Spec requirement: AC-10 — alte Parameter werden angenommen und als dinge geschrieben, Ergebnis wie bei things.
  Conflict: Die Spec lässt die Semantik von Teilupdates mit alten Parametern offen; für laufende Gespräche mit altem Schema (Spec-Risiko "AI-Clients mit altem Schema") ist das stiller Datenverlust.
  Remediation: In option_update alte Einzelparameter gruppenweise in die bestehenden dinge einmischen (nur Gruppen des Präfixes ersetzen) oder alten Einzelparameter an bestehender Option ablehnen mit Hinweis auf dinge.

Finding:
  ID: F002 (Runde 1: offen; Runde 2: BEHOBEN durch Spezifikation)
  Severity: LOW
  Category: spec_violation
  Code reference: engine/routen.py:773
  Description: Hinweis 2: dinge: [] im YAML baut ohne Fehler (Probe), weil der Fehler nur bei nicht-leerer Liste geprüft wird (liste and not unbekannt and ...). option_inhalt_ok(leer) ist falsch (engine/schreiben.py:4051), wird im Schreibweg aber nur bei nicht-leerem Inhalt aufgerufen.
  Spec requirement: AC-6 — leeres dinge ist ungültig (option_inhalt_ok falsch bzw. Prüffehler).
  Conflict: "bzw." erlaubt die Funktionsprüfung allein, daher nur LOW/AMBIGUOUS; Option ohne dinge und folge war schon vorher erlaubt (Planungs-Option), also konsistent mit dem Altzustand, aber handgepflegtes dinge: [] bleibt still gültig.
  Remediation: In der Spec festhalten, dass leere Möglichkeiten erlaubt bleiben, oder dinge: [] als Prüffehler melden.

Finding:
  ID: F003 (Runde 1: offen; Runde 2: BEHOBEN)
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:259
  Description: dinge_uebersetzen behandelt einen alten Parameter mit Wert null als Liste mit None: {"unterkuenfte": null, "orte": ["O-04"]} -> dinge [None, "O-04"] -> Ablehnung wegen ID None (Probe). Clients, die ungesetzte Felder als null senden, werden abgelehnt; fruehere_felder_ablehnen nutzt dagegen is not None (engine/schreiben.py:4091).
  Spec requirement: AC-10 — alte Parameter werden angenommen.
  Conflict: inkonsistente Behandlung von null.
  Remediation: In dinge_uebersetzen None-Werte überspringen.

**Implementierer:** (nicht beteiligt, Adversary arbeitet isoliert)

### Runde 2
**Adversary:** Nachbesserungen geprüft. Gezielte Suite erneut: 410 passed, 0 failed, 0 übersprungen (adversary-test-output.txt). Spec neu gelesen: AC-6 (leere Möglichkeit erlaubt, nur option_inhalt_ok meldet sie leer) und AC-10 (alter Gruppen-Parameter ersetzt bei option_update nur seine Gruppe; null = nicht gesetzt) sind präzisiert; die angepasste Assertion im Übersetzungstest passt dazu.

Probeläufe option_update an Option mit dinge [A-01, O-03, E-04] (Konnektor-Eingabeschritt + Schreibweg):
- places [O-06] -> [A-01, O-06, E-04] (nur Gruppe ersetzt, Position bleibt): OK
- orte [O-06] + strecken [] -> [A-01, O-06] (leere Liste leert nur ihre Gruppe): OK
- places [O-99] -> Ablehnung schreiben.id_liste.3; places [A-01] -> Ablehnung schreiben.id_liste.2 (falsche Gruppe): OK
- accommodations [U-02] auf Option mit A/O/E -> schreiben.option_aendern.5 (Präfixregel auf dem Ergebnis): OK
- places plus things -> schreiben.option_dinge.gemischt, nichts geändert: OK
- stays null plus legs [E-02] -> null wird ignoriert, E-02 ergänzt: OK (F003 behoben)
- option_update mit places an Option mit folge (V-01.a) -> schreiben.option_aendern.5: OK
- things [O-03] ersetzt vollständig: OK

Confirmation:
  AC: AC-10
  Code reference: engine/konnektor.py:259
  Evidence: dinge_uebersetzen(o, aendern=True) benennt nur um, null-Werte werden entfernt; schreibseitig mischt dinge_einmischen (engine/schreiben.py:4072) gruppenweise ein; option_aendern (engine/schreiben.py:4099) lehnt Mischung mit dinge ab. F001 und F003 behoben.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/routen.py:774
  Evidence: Spec präzisiert (leere Möglichkeit erlaubt); Verhalten entspricht dem; Präfixregel engine/routen.py:505, option_inhalt_ok engine/schreiben.py:4051. F002 behoben durch Spezifikation.
  Status: CONFIRMED

Confirmation:
  AC: AC-1
  Code reference: engine/neu.py:1234
  Evidence: Referenzen aktualisiert: Aufteilung engine/routen.py:746, Nachziehen engine/neu.py:1234, Schnittstelle engine/schnittstelle.py:101, Texte engine/texte_de.py:1822 und engine/texte_en.py:1821 unverändert gültig.
  Status: CONFIRMED

Finding:
  ID: F004
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:274
  Description: Im Änderungsmodus (aendern=True) werden deutscher und englischer Name desselben Feldes still zusammengeführt: o[i] = o.pop(e) überschreibt. Probe: option_update mit places [O-04] und orte [O-06] ergibt nur O-04, O-06 verschwindet ohne Meldung. Beim Anlegen werden beide dagegen aneinandergehängt.
  Spec requirement: AC-10 — alte Parameter englisch wie deutsch werden angenommen.
  Conflict: Inkonsistent und ein Parameter geht still verloren; praktisch unwahrscheinlich (ein Client sendet nicht beide Namen).
  Remediation: Bei beiden Namen zusammenhängen oder ablehnen. Nicht blockierend.

Doppelte IDs (places [O-06, O-06]) bleiben doppelt in dinge, wie vorher bei orte; kein Finding. wahlstelle_anlegen ist unverändert (dinge_uebersetzen ohne aendern, Mischung wird abgelehnt, nichts geschrieben, Runde 1 belegt). AC-21: außerhalb dieses Dialogs, Orchestrator.
**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 410 passed, 0 failed, 0 übersprungen (gezielte Suite)
Findings: F001, F002, F003 behoben; F004 (LOW, nicht blockierend) offen.
Checklist: AC-1 bis AC-20 bewiesen, AC-21 außerhalb dieses Dialogs.

## Geprüfte Dateien

- sha256:79192b58a9facfbb810d7b6ad2575fd5cb65510aa3fda5034c690b86fdc94fa4  engine/konnektor.py
- sha256:50c6ae986fadb8b52481ee06ff3247e1f14509f4fd02c27f3a8a1b48bce25a24  engine/neu.py
- sha256:7cd6c018fc32e84fe741a2cb6a9e549167d2deb24a35ab50a210b2c876a140ab  engine/routen.py
- sha256:793185f35710d348b3fbc4b41eeef8bccac95380005668634fcdd897a70a7f74  engine/schnittstelle.py
- sha256:116a31559ffa07d98c7b02ba5eaa532b2739e47735bec0a56995818a8313db44  engine/schreiben.py
- sha256:1ab7b285b7703e54e5d205667d1c256806ae593c5e669bdad2230640a19d19b3  engine/texte_de.py
- sha256:75c30342a7495aa467af4ce1f4747a59b1848d17d8fcc1a79349b77a69a216cb  engine/texte_en.py

## Prüfbasis

- base: a5143e9a84dab58e841fb3a6f7b6edd624a43647
- blob:0d80488f0c36375fb24b62b7e8367e8f318d4f23  engine/konnektor.py
- blob:b7c30275b55439b26a0d217ab41fe226c5f8f124  engine/neu.py
- blob:2fe8a381822a6ade0f00b959f92e9de75828efa3  engine/routen.py
- blob:69694909dceff8287a6e6b402ab03c28609800a2  engine/schnittstelle.py
- blob:5c64b71b9ecb7b6e9c13f31216c3ec255368e042  engine/schreiben.py
- blob:c5b65b605f842150942c861cfcc7a5b15e053909  engine/texte_de.py
- blob:c05a755760c55035658fc56728d2fe131edcb32c  engine/texte_en.py
