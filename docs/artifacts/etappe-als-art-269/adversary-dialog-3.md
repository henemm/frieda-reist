# Adversary Dialog — etappe-als-art-269
Spec: docs/specs/oberflaeche/etappe-als-art-269.md
Datum: 2026-11-05 (3. und letzter Durchgang, Circuit Breaker)
Testausgabe: docs/artifacts/etappe-als-art-269/adversary-test-output-3.txt (1383 passed in 1222.12s, seriell)

## Checkliste
- [x] **AC-1:** (Test 1, 10): Die Seite der Beispielreise zeigt Etappenseiten, Tagesseiten, Kennzahlen und Karte inhaltlich wie vorher (Werte gleich, Reihenfolge gleich). PROVEN
- [x] **AC-2:** (Test 5): `grep` auf `REGEL.gehzeit`, `kennzahlPaar`, `typ === "etappe"`, `etappen_muster` in `engine/` (außer `neu.py nachziehen` und Tests der Umstellung) findet nichts. PROVEN
- [x] **AC-3:** (alle Tests): `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün (beide Beispielreisen, auch `stadtwochenende` ohne Etappen). PROVEN (1383 passed)
- [x] **AC-4:** (Test 2, 3): `neu.py nachziehen` stellt die Beispielreise ohne Handschritt um, ist idempotent und lässt Reisen ohne Dossier unberührt. PROVEN
- [x] **AC-5:** (Test 4): Eine Reise mit anderer summierter Art (nicht `wandern`) bekommt ihre Etappen im Reiter „Etappen“, ohne dass Code den Artnamen kennt. PROVEN (Test der Suite grün; kein Artname im Code)
- [x] **AC-6:** (Test 9): Das Wort „Etappe“ steht nur im Textkatalog (alle Sprachen); `test_texte.py` bleibt grün. PROVEN (DE und EN je 3013 Schlüssel, Differenz leer; test_texte.py unverändert, Ausnahmelisten nicht länger)
- [x] **AC-7:** (Test 8): Tag mit summierter Strecke ohne Angaben zeigt „Angaben fehlen“. PROVEN (Test grün; eine Strecke ohne Eckdaten wird beim Umstellen nur mit Titel angelegt und fällt in diesen Fall)
- [x] **AC-8:** (Prozess, kein Test): Umsetzung beginnt erst, wenn #268 auf `main` ist (vor dem ersten Edit an `routen.py`/`vorlage.html` geprüft); der Branch setzt auf diesen Stand auf. PROVEN (Commit ce72978 ist Vorfahre von origin/main und von HEAD)

## Dialog

### Runde 1
**Adversary:** Referenzbau des Stands faf3ac1 (Archiv in eigenem Ordner) gegen den Neustand, beide Beispielreisen, daten.json Feld für Feld verglichen. Beispielreise: Abweichungen nur typ etappe -> strecke, Titel ohne „Etappe N:“, Felder nr/name/kennzahlen am Abschnitt entfallen (liegen an der Strecke), Kennzahl-Namen -> Kennungen (gehzeit, aufstieg, abstieg, laenge; aufstieg/abstieg als Zahl statt Text), Eckdaten-Block ohne die vier Kennzahlzeilen. Summen, Block-IDs, Karte, Reihenfolge: keine Abweichung. Stadtwochenende: nur reise_stand (kommt aus der Versionsgeschichte, im Archiv nicht vorhanden), sonst gleich. Danach neu.py nachziehen auf einer Kopie der alten Beispielreise: Ergebnis stimmt mit der neuen Beispielreise überein (routen.yaml bis auf Kommentare, Dossiers, reise.json); zweiter Lauf „Nothing to bring up to date“. Stadtwochenende: unverändert. Abbruch mitten drin simuliert (routen.yaml schon umgestellt, Dossiers und reise.json noch alt): der Wiederholungslauf stellt sie um, Ergebnis identisch zum Einmal-Lauf, nichts doppelt.
**Implementierer:** Die Rückgabefunktion schreibt Dossiers und reise.json erst nach routen_speichern (neu.py:821); eine Zeile entfällt nur, wenn der Wert an der Strecke nachgelesen (PyYAML) gleich steht (neu.py:717-723). Beides bestätigt.

### Runde 2
**Adversary:** Randfälle. (a) Zweite Tabelle im Eckdaten-Abschnitt: eckdaten_zeilen (neu.py:630) zählt deren Kopf und Trennlinie als Datenzeilen; Gehzeit/Aufstieg dort lösen „zwei Namen, eine Kennung“ aus, die erste Zeile gilt, Dossier und Überschrift bleiben unverändert, OFFEN. Kein Datenverlust, aber der Bau bricht dann ab (b). (b) OFFEN-Etappe: Bau meldet „heading ... has no ID in reise.json“; der Satz verweist nicht auf die OFFEN-Meldung von nachziehen (F201, LOW). (c) Etappe „3a“ ohne Strecke E-03a: OFFEN etappe_ohne_strecke, Abschnitt bleibt; ID-Regel gleich der alten (zfill 3 bei Buchstabe). (d) Dossier ohne Eckdaten-Tabelle: nur titel wird übertragen. (e) Zahlenformate: „10,7“ und „10.7“ -> 10.7; „3,5 h“, „ca. 3:40 h“ bleiben Text; gehzeit bleibt immer Text und wird in Anführungszeichen geschrieben; Bau mit solchen Werten fehlerfrei, Summe berechnet. „1.234“ wird 1.234 wie vorher (dasselbe zahl() der Summe). (f) kennung_der_kennzahl: Gehzeit/GEHZEIT/Walking time/Duration/Dauer, Aufstieg (Hm), Ascent (m), Descent (m), Länge/Laenge/Length (km), km -> Kennung; Km-Stand, Aufstiegshilfe, Dauer der Pause, Distance, „Aufstieg (Hm) (netto)“ bleiben eigene Namen. (g) Konnektor: item_create (what=strecke, attributes.figures mit walking_time/ascent/descent/length) und item_update (attributes.figures) über den echten Dispatcher mit englischen Namen ausgeführt: der Schreibweg bekommt was/art/titel/von/nach/merkmale.figures unverändert, die inneren Schlüssel werden nicht übersetzt; der Schreibweg wandelt figures und Katalognamen in Kennungen (test_schreiben.py::test_kennzahlen_an_strecken_schreiben). (h) Suche in engine/, beispiel/, docs/, werkzeuge/, betrieb/ nach gr221 und Serverpfaden: kein Treffer (abgleich-2026-10-29.md ausgenommen). (i) Mehrsprachigkeit: nur texte_de.py und texte_en.py, Schlüsselmengen gleich.
**Implementierer:** Bei jeder Unsicherheit bleibt der Abschnitt unverändert und die Einstellungen bleiben für einen späteren Lauf (neu.py:729-731, 740); dokumentiert im Docstring neu.py:652-657 und in docs/betrieb.md (OFFEN sperrt nicht, erscheint als Warnung).

## Findings

Finding:
  id: F201
  severity: LOW
  category: edge_case
  description: Bleibt eine Etappe OFFEN (keine Strecke, doppelte Nummer, zwei Namen einer Kennung, anderer Wert an der Strecke), bleibt die alte Überschrift „## Etappe N: Name“ im Dossier; der Bau lehnt sie danach ab mit „heading ... has no ID in reise.json“. Der Satz nennt weder die OFFEN-Meldung von nachziehen noch die Ursache. Keine Daten gehen verloren, nichts wird still falsch angezeigt.
  evidence: engine/neu.py:684-691, 729-731 (Abschnitt bleibt); Bau einer OFFEN-Reise im Scratchpad: „The page was NOT built ... has no ID in reise.json“
  remediation: Bauzeile um den Hinweis auf OFFEN von nachziehen ergänzen (Textkatalog, beide Sprachen). Kein Blocker.

Finding:
  id: F202
  severity: LOW
  category: edge_case
  description: eckdaten_zeilen zählt alle Tabellenzeilen im Unterabschnitt „Eckdaten“ ab der dritten als Datenzeilen, auch Kopf und Trennlinie einer zweiten Tabelle. Gleichnamige Kennzahlen in der zweiten Tabelle werden als Doppel gemeldet (OFFEN) statt übertragen; sicher, aber streng. Kein Datenverlust (Dossier bleibt unverändert, die Strecke bekommt nur den ersten Wert).
  evidence: engine/neu.py:637-638
  remediation: Nur die erste zusammenhängende Tabelle auswerten. Kein Blocker.

Finding:
  id: F203
  severity: LOW
  category: edge_case
  description: AMBIGUOUS, nicht als BROKEN gewertet: Die bewusst nicht gebauten Punkte F005, F006, F007, F109 bleiben beim Product Owner.
  evidence: docs/artifacts/etappe-als-art-269/adversary-dialog.md, docs/artifacts/etappe-als-art-269/adversary-dialog-2.md
  remediation: Entscheidung des Product Owners.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/bauen.py:415
  Evidence: dossier_lesen erzeugt typ strecke aus „## E-0N Name“; Referenzvergleich der daten.json beider Beispielreisen ohne Abweichung außer den erwarteten.
  Status: CONFIRMED

Confirmation:
  AC: AC-1
  Code reference: engine/routen.py:422
  Evidence: kennwerte liest nur Kennungen; Summen der Beispielreise gleich dem Stand faf3ac1.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/bauen.py:52
  Evidence: STRECKE_UEBERSCHRIFT ersetzt etappen_muster; die vier Muster stehen nur noch in neu.py (Umstellung) und im Meldungstext der Umstellung.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/schreiben.py:1514
  Evidence: Volle Suite seriell: 1383 passed, 0 failed, 0 übersprungen; kennzahlen_wert lehnt falsche Formen ab, gehzeit muss Text sein.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/neu.py:818
  Evidence: etappen_nachziehen vor routen_speichern aufgerufen, Rückgabefunktion danach (neu.py:821); zweiter Lauf leer, Abbruch zwischen beiden Schritten heilt beim Wiederholen; Reise ohne Dossier unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/schnittstelle.py:129
  Evidence: Kennzahlen sind Kennungen (walking_time/ascent/descent/length) ohne Artnamen; Suite-Test zur anderen summierten Art grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_de.py:2861
  Evidence: Neue Meldungen mit gleichem Schlüssel in texte_en.py; Schlüsselmengen beider Kataloge gleich, test_texte.py unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_en.py:2860
  Evidence: englische Entsprechung vorhanden, 3013 Schlüssel je Katalog.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/konnektor.py:798
  Evidence: Konnektor zeigt Kennzahlen von der Strecke; Strecke ohne Angaben fällt in „Angaben fehlen“ (Suite-Test).
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: werkzeuge/punkte_holen.py:141
  Evidence: dossier_namen liest die neue Überschrift „## E-0N“; #268 (ce72978) liegt auf origin/main vor diesem Branch.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Tests: 1383 passed, 0 failed, 0 übersprungen
Edge cases: geprüft (Etappe 3a, fehlende Tabelle, zweite Tabelle, Zahlenformate, Abbruch mitten in nachziehen, zweiter Lauf, OFFEN-Etappe); nur LOW-Befunde F201, F202, kein Datenverlust
Regressions: keine; Referenzbau beider Beispielreisen inhaltlich gleich
Checklist: 8/8 points proven

## Geprüfte Dateien

- sha256:1614821e4efe9d28efef32ad22b40802f0e3d4c2bea7787c03a0e2ffe6a351bf  engine/bauen.py
- sha256:bb11ff413ea69ae193a7c18adcffc66c757981112dfc11720a669ed79efd06be  engine/konnektor.py
- sha256:8e81d359216bf4e4bd296a3a23bbd2b4168b508446194b7e1a73d4d4030945bb  engine/neu.py
- sha256:e4ab5bb66f7723a6e7bac2275901fcfe676f25e5de91e0a4f9b7ed9a8d79c538  engine/routen.py
- sha256:1282d283b0bf30cacd06c6f542c6f4b4b9af3f6d079d6d00fc89a7cfbbc4ca84  engine/schnittstelle.py
- sha256:f043193a07ca12744da78aae21b6024dfd1f490ae073bd1f52ba9d145aa1443c  engine/schreiben.py
- sha256:5c05c7a1c97569047b6083c2fdc01fb4b54856863a4b7e02bdd557e8407a50d5  engine/texte_de.py
- sha256:fab94118ee8585ffa58c66860a655190032cdce424f8394aab53ec8742322b3e  engine/texte_en.py
- sha256:931932cee2e6c5e2944832969be5000222093c7de8cba6c9de3088d9d57615c9  werkzeuge/punkte_holen.py

## Prüfbasis

- base: faf3ac103ce0ee76a1d89b222f3e14f75848b86b
- blob:ac300be1728d1e53eb5f27bc5e5eaced2ea3881e  engine/bauen.py
- blob:84fe0e49a01de056e6629ab22d8e9ab2cee98f37  engine/konnektor.py
- blob:f319352ca6dd2aef83801911b3fa8e9c1b1297b2  engine/neu.py
- blob:0f4e8875de8a526b7abbfe10692543ff6fed28bc  engine/routen.py
- blob:c8f63ce087e037eabd32815a173019bd05811ac6  engine/schnittstelle.py
- blob:52d023a4575fcb971c2c6d25c6e6f5cdef4df25e  engine/schreiben.py
- blob:95cca5cce0e93c066f1d5aa3b53b47e81a5f1a6f  engine/texte_de.py
- blob:ce9e86413eb827c59dadd9d2127cf1ae5b188ebd  engine/texte_en.py
- blob:bf3b806ef99b856e7a4fddeccee1c8876a8e8658  werkzeuge/punkte_holen.py
