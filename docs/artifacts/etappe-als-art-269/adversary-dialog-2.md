# Adversary Dialog — etappe-als-art-269
Spec: docs/specs/oberflaeche/etappe-als-art-269.md
Datum: 2026-11-05 08:46

## Checkliste
- [x] **AC-1:** (Test 1, 10): Die Seite der Beispielreise zeigt Etappenseiten, Tagesseiten, Kennzahlen und Karte inhaltlich wie vorher (Werte gleich, Reihenfolge gleich). PROVEN fuer die Beispielreise (Referenzbau Altstand gegen Neustand); Einschraenkung F101 bis F103 fuer Altbestand
- [x] **AC-2:** (Test 5): `grep` auf `REGEL.gehzeit`, `kennzahlPaar`, `typ === "etappe"`, `etappen_muster` in `engine/` (außer `neu.py nachziehen` und Tests der Umstellung) findet nichts. PROVEN
- [x] **AC-3:** (alle Tests): `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün (beide Beispielreisen, auch `stadtwochenende` ohne Etappen). PROVEN (1373 passed, 0 failed, 0 uebersprungen)
- [x] **AC-4:** (Test 2, 3): `neu.py nachziehen` stellt die Beispielreise ohne Handschritt um, ist idempotent und lässt Reisen ohne Dossier unberührt. PROVEN fuer Beispielreise (auch aus echten Altdaten) und stadtwochenende; DISPROVEN fuer Randfaelle F101, F102, F103, F104
- [x] **AC-5:** (Test 4): Eine Reise mit anderer summierter Art (nicht `wandern`) bekommt ihre Etappen im Reiter „Etappen“, ohne dass Code den Artnamen kennt. PROVEN (Datenebene); Reiter-Wortlaut F006 AMBIGUOUS
- [x] **AC-6:** (Test 9): Das Wort „Etappe“ steht nur im Textkatalog (alle Sprachen); `test_texte.py` bleibt grün. PROVEN
- [x] **AC-7:** (Test 8): Tag mit summierter Strecke ohne Angaben zeigt „Angaben fehlen“. PROVEN
- [x] **AC-8:** (Prozess, kein Test): Umsetzung beginnt erst, wenn #268 auf `main` ist (vor dem ersten Edit an `routen.py`/`vorlage.html` geprüft); der Branch setzt auf diesen Stand auf. PROVEN

## Dialog

### Runde 1
**Adversary:** Zweiter Durchgang. Ich pruefe zuerst die behaupteten Behebungen von F001, F002, F003, F004 und F008 unabhaengig und stelle dann den Altbestand nach, nicht nur die Beispielreise (AC-1, AC-2, AC-4). Methoden: (1) Referenzbau aus einem Export des Repo-Stands faf3ac1 in einem Scratch-Ordner (Altstand) gegen den jetzigen Stand, beide Beispielreisen, daten.json Feld fuer Feld; (2) beide Seiten im Browser (Playwright) geladen, sichtbarer Text der vier Etappenseiten und der ganzen Seite verglichen; (3) neu.nachziehen des jetzigen Stands auf eine Kopie der Beispielreise aus dem Altstand (echte Altdaten), Datei fuer Datei gegen die eingecheckte Beispielreise; (4) Suche zu AC-2 und Pruefung auf Namen echter Reisen und Serverpfade in Arbeitsbaum und Verlauf.
**Implementierer:** (aus den Belegen)
- AC-1: daten.json Altstand gegen Neustand, Beispielreise: nur erwartete Abweichungen (Abschnittstyp etappe wird strecke, Titel ohne "Etappe N:", Kennzahlen unter Kennungen statt Namen, Block-HTML der Eckdaten ohne die vier Kennzahl-Zeilen, nr und name entfallen); route.plaene (Summen), Kennzahlen-Werte, Block-IDs, Karte: kein Unterschied. stadtwochenende: einziger Unterschied reise_stand (der exportierte Altstand hat keine Versionsverwaltung, kein inhaltlicher Unterschied). Browser: sichtbarer Text der vier Etappenseiten E-01..E-04 Zeichen fuer Zeichen gleich (1960, 860, 646, 620 Zeichen); ganzer Seitentext gleich bis auf die Fusszeile Reise-Stand/Release (Altstand ohne Versionsverwaltung) und die eingebetteten Daten.
- (a) Test 2 ist nicht ausgehoehlt: er stellt das Altformat aus den eingecheckten Werten her (Kennzahl-Zeilen in die Eckdaten, Namen in routen.yaml entfernt, Ueberschriften "Etappe N:") und prueft jetzt zusaetzlich, dass das Dossier nach nachziehen byteweise der eingecheckten Beispielreise gleicht und die Kennzahlen unveraendert sind. Gegenprobe mit echten Altdaten: nachziehen auf der Kopie der Beispielreise aus faf3ac1 ergibt reise.json, etappen.md, unterkuenfte.md byte-gleich zur eingecheckten Beispielreise; routen.yaml unterscheidet sich nur in drei Kommentarzeilen; arten.yaml unterscheidet sich, weil die eingecheckte Beispielreise die Umstellung "rolle kosten" (nicht aus #269, sie tritt auch im Altstand auf) noch nicht enthaelt. Zweiter Lauf leer. nachziehen auf der bereits umgestellten Beispielreise meldet nur diese arten.yaml-Umstellung (Altstand ebenso).
- AC-2: kein Treffer fuer REGEL.gehzeit, kennzahlPaar, typ === "etappe", etappen_muster in engine/ ausser neu.py (Umstellung), den Katalogmeldungen und Tests der Umstellung bzw. der negativen Pruefung in test_seite_sprachen.py.
- AC-8: Die Vorfahren-Pruefung von ce72978 gegen HEAD ist wahr.
- F008: unquotiertes gehzeit: 4:00 lehnt der Bau jetzt mit Meldung ab (routen.py:586, Katalog de/en). F003: doppelte Nummer wird OFFEN gemeldet, Einstellungen bleiben. Beides bestaetigt.
- Bis hierher: die Beispielreise ist in Ordnung. Die Fixes sind aber nur an der Beispielreise belegt. Ich gehe an die Raender von nachziehen.

### Runde 2
**Adversary:** Gezielte Brueche an etappen_nachziehen, eckdaten_ohne_kennzahlen, kennzahlen_kennungen, kennzahlen_wert: (b) Eckdaten-Zeilen und Strecke mit schon vorhandenen Kennzahlen; (c) Eckdaten-Tabelle mit fett gesetztem Namen, mit leerem Wert, mit nur Kennzahl-Zeilen; (d) zwei Namen in etappen_kennzahlen, die dieselbe Kennung ergeben; (e) Namenskollision Gehzeit/gehzeit in routen.yaml; (f) Schreibweg und kennung_der_kennzahl mit eigenen Namen; (g) Konnektor-Schema; (h) volle Testsuite.
**Implementierer:** (aus den Belegen, alle mit Kopie der Beispielreise im Altformat nachgestellt)
- (b) BROKEN. Strecke E-01 hat in routen.yaml schon kennzahlen mit gehzeit "5:00 h", das Dossier hat die Zeilen Gehzeit, Aufstieg (Hm) 485, Abstieg (Hm) 285, Laenge: nachziehen entfernt alle Kennzahl-Zeilen aus den Eckdaten (neu.py:689, die Zuweisung an raus laeuft unbedingt), schreibt aber wegen der Bedingung "keine kennzahlen an der Strecke" (neu.py:691) nichts an die Strecke. Ergebnis: Strecke nur gehzeit "5:00 h"; Aufstieg 485, Abstieg 285, Laenge sind aus der Reise verschwunden; die Meldung behauptet trotzdem "Titel und Kennzahlen ... an die Strecke". Siehe F101.
- (c) BROKEN. Eine Zeile mit fett gesetztem Namen (Aufstieg (Hm) in Sternchen, Wert 5) wird aus dem Dossier entfernt (die Entfernung entfernt Sternchen und Leerzeichen am Namen, neu.py:634), aber nicht uebertragen (die Uebertragung sucht den Namen exakt in den Schluesseln von tabelle_lesen, neu.py:688): Wert 5 weg. Zwei Parser fuer dieselbe Tabelle. Zeile mit leerem Wert: korrekt entfernt. Zeile "laenge (km)" (klein): bleibt als Eckdaten-Zeile stehen, sauber. Tabelle nur aus Kennzahlen: Kopf und Trennlinie entfallen, es bleibt eine leere Ueberschrift Eckdaten und ein leerer Block E-01.eckdaten, die Seite zeigt eine nackte Ueberschrift ohne Inhalt (Browser). Siehe F102, F107.
- (d) BROKEN. etappen_kennzahlen mit Gehzeit, "Gehzeit mit Pausen" und Schwierigkeit, Zeilen "Gehzeit: ca. 3:40 h" und "Gehzeit mit Pausen: ca. 5:00 h": beide landen unter gehzeit, der zweite ueberschreibt den ersten (neu.py:688), beide Zeilen werden entfernt, kein Hinweis. Der Altstand summierte den ersten Treffer (3:40 h), der Neustand 5:00 h. Eigener Name "Schwierigkeit" wird korrekt uebertragen. Siehe F103.
- (e) Namenskollision in routen.yaml: "Gehzeit" neben "gehzeit" (und "Aufstieg (Hm)" neben dem aus "Aufstieg" entstandenen aufstieg) bleiben als eigene Namen stehen, kein Datenverlust, aber keine OFFEN-Meldung; der Altstand las den ersten Treffer ("Gehzeit"), der Neustand gehzeit: Summen aendern sich still (neu.py:610, Bedingung neu not in km). Siehe F104.
- (f) kennung_der_kennzahl (neu.py:581) ordnet per startswith zu: "Kmh Schnitt" und "Km-Stand" werden laenge, "Dauer der Pause" wird gehzeit, "Aufstiegshilfe" wird aufstieg; kennzahlen_kennungen laeuft auf jeder Reise bei jedem Nachziehen, benennt so in routen.yaml auch eigene Namen um (nur wenn die Kennung frei ist). Der Schreibweg (schreiben.py:1525) speichert dagegen "Gehzeit" und "Aufstieg" als eigene Namen (nur englische Namen werden uebersetzt). Ergebnis: item_update legt "Gehzeit" an, das naechste Nachziehen macht daraus still gehzeit. Das widerspricht dem Satz "eigene Namen bleiben". Der Altstand hatte dieselbe Praefix-Suche (routen.kennwerte), aber nur beim Lesen, nie beim Umschreiben von Daten. Siehe F105 (zusammen mit dem zurueckgestellten F005).
- (g) Konnektor: item_create hat 8 Parameter (an, art, geprueft, hinweis, merkmale, quelle, titel, was); kennzahlen steht als Feld der Grundform in merkmale (de: kennzahlen, en: figures mit walking_time, ascent, descent, length; routen.GRUNDFORM_FELDER und FEST_ALIAS; schnittstelle.KENNZAHL_ALIAS); felder_aus_merkmalen (schreiben.py:1288) wird in ding_anlegen (1397) und ding_aendern (1645) angewandt, also geht item_update auch ueber attributes. Die Abnahme "Strecke mit Kennzahlen ueber item_create anlegen" ist damit ueber das Schema moeglich (englische Aliase getestet in test_kennzahlen_an_strecken_schreiben). DING_AENDERN hat zusaetzlich einen Sonderparameter kennzahlen (jetzt 10 Properties), gegenlaeufig zu ADR-0007 (Sonderparameter entfallen) und redundant zu attributes. Siehe F108 (LOW). Die Konnektor-Ausgabe zeigt Kennungen "gehzeit: ...; laenge: ..." statt Namen, siehe F109 (LOW). F004 ist damit behoben.
- AC-5: F006 und F007 des ersten Durchgangs sind Spec-Mehrdeutigkeiten und bleiben AMBIGUOUS (nicht als BROKEN gewertet); F005 ist durch F105 mitbehandelt.
- Volle Suite, seriell: 1373 passed in 1219.55s, 0 failed, 0 uebersprungen (docs/artifacts/etappe-als-art-269/adversary-test-output-2.txt).
- Nicht geprueft: Browser-Rundgang ueber engine/tests/seiten_browser.mjs und seiten_reise.mjs (nur Playwright-Vergleich der Seiten und Teil der Suite), eine frische Reise aus engine/reisevorlage, Tests der einbindenden Instanzen, Konnektor-Abnahme ueber die App mit einer Testreise.

- (h) Verlauf: Der lokale, nicht veroeffentlichte Stand db5c2d6 (RED-Tests) traegt in docs/context/etappe-als-art-269.md den Namen einer echten Reise (Platzhalter Reise A); in den Dateien ist er ersetzt, im Verlauf bleibt er, sobald die Behebung als eigener Stand obenauf kommt. Dateien in engine/, beispiel/, werkzeuge/ und die Protokolle: kein Treffer fuer Namen echter Reisen oder Serverpfade. Siehe F106.

## Findings

Finding:
  ID: F101
  Severity: HIGH
  Category: edge_case
  Code reference: engine/neu.py:691
  Description: etappen_nachziehen entfernt die Kennzahl-Zeilen aus der Eckdaten-Tabelle unbedingt (Zuweisung an raus aus eckdaten_ohne_kennzahlen), schreibt die Kennzahlen aber nur, wenn die Strecke noch keine hat. Hat die Strecke schon eine Kennzahl (z. B. nur gehzeit), sind die uebrigen Kennzahlen des Dossiers (Aufstieg 485, Abstieg 285, Laenge 8,1 km) nach dem Lauf in keiner Datei mehr. Die Meldung sagt trotzdem, Titel und Kennzahlen seien an die Strecke gekommen.
  Evidence: Kopie der Beispielreise im Altformat, E-01 mit gehzeit "5:00 h" als einziger Kennzahl in routen.yaml, Dossier mit Kennzahl-Zeilen; nach nachziehen: Strecke nur gehzeit, Eckdaten-Tabelle ohne die Zeilen (neu.py:691 und 689).
  Remediation: Nur Zeilen entfernen, deren Wert an der Strecke steht (je Kennung zusammenfuehren: fehlende Kennungen ergaenzen, vorhandene behalten; eine Zeile nur entfernen, wenn Kennung und Wert an der Strecke stehen, sonst OFFEN melden); Test mit vorhandenen Teil-Kennzahlen.

Finding:
  ID: F102
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/neu.py:634
  Description: Zwei Parser lesen dieselbe Tabelle: die Entfernung vergleicht das erste Feld der Zeile (ohne Sternchen und Leerzeichen) mit den Namen, die Uebertragung sucht den Namen exakt in den Schluesseln von tabelle_lesen. Eine Zeile mit fett gesetztem Namen oder in einer zweiten Tabelle des Abschnitts wird entfernt, ohne dass ihr Wert an die Strecke kommt.
  Evidence: Kopie im Altformat mit einer Eckdaten-Tabelle, deren Name Aufstieg (Hm) fett gesetzt ist (Wert 5): Zeile weg, Strecke ohne aufstieg (neu.py:634 gegen neu.py:688).
  Remediation: Nur Zeilen entfernen, deren Wert tatsaechlich uebertragen wurde (eine Quelle der Wahrheit fuer Zeilen und Werte).

Finding:
  ID: F103
  Severity: HIGH
  Category: edge_case
  Code reference: engine/neu.py:688
  Description: kennung_der_kennzahl bildet mehrere Namen aus etappen_kennzahlen auf dieselbe Kennung ab (Gehzeit und "Gehzeit mit Pausen" werden gehzeit). Der zweite Wert ueberschreibt den ersten, beide Zeilen werden aus den Eckdaten entfernt, es gibt keine Meldung. Im Altstand zaehlte der erste Treffer (3:40 h), im Neustand zaehlt 5:00 h; ein Wert geht verloren, die Summen aendern sich.
  Evidence: Kopie im Altformat, etappen_kennzahlen mit Gehzeit, "Gehzeit mit Pausen", Schwierigkeit: Strecke gehzeit "ca. 5:00 h", Zeile Gehzeit 3:40 h nirgends mehr.
  Spec requirement: Spec Risiken: nicht eindeutig Zuzuordnendes wird offen gemeldet statt geraten; Projektregel: nachziehen aendert keinen Wert.
  Remediation: Zweiten Namen derselben Kennung nicht ueberschreiben, die Zeile stehen lassen und OFFEN melden (oder als eigenen Namen uebernehmen).

Finding:
  ID: F104
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/neu.py:610
  Description: kennzahlen_kennungen laesst einen Namen stehen, wenn die Kennung schon vorhanden ist, und meldet das nicht. Der Altstand las den ersten startswith-Treffer in Reihenfolge der Datei (Gehzeit 9:00 h), der Neustand liest die Kennung (gehzeit ca. 4:00 h): Summen aendern sich still; der alte Name bleibt als totes Feld stehen. Realistisch, weil item_update neue Kennungen in bestehende Namen hinein zusammenfuehrt.
  Evidence: Kopie, E-02 mit Gehzeit "9:00 h" neben gehzeit "ca. 4:00 h" und Aufstieg neben "Aufstieg (Hm)": nachziehen meldet nur die Umbenennungen von Aufstieg und "Laenge (km)"; Gehzeit und "Aufstieg (Hm)" bleiben ohne OFFEN-Meldung.
  Remediation: Kollision mit OFFEN melden (Name, Kennung, beide Werte), nicht still stehen lassen.

Finding:
  ID: F105
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/schreiben.py:1525
  Description: Der Schreibweg uebersetzt nur englische Namen in Kennungen; Gehzeit oder Aufstieg wird als eigener Name gespeichert und nie summiert. kennzahlen_kennungen (neu.py:581-588, startswith-Zuordnung) macht daraus beim naechsten Nachziehen die Kennung und trifft dabei auch eigene Namen wie "Kmh Schnitt", "Km-Stand" (laenge), "Dauer der Pause" (gehzeit), "Aufstiegshilfe" (aufstieg). Nachziehen ist so ein dauerhafter, ratender Normalisierer, der dem Satz "eigene Namen bleiben" und dem Schreibweg widerspricht (F005 des ersten Durchgangs gehoert hierher).
  Evidence: kennzahlen_wert mit "Gehzeit" liefert einen eigenen Namen (schreiben.py:1525); kennung_der_kennzahl("Km-Stand") liefert laenge (neu.py:581).
  Remediation: Zuordnung beim Nachziehen auf die Namen einschraenken, die der Katalog nennt (ganzer Name oder Name mit Einheit, nicht Praefix), und im Schreibweg die Katalognamen (Gross-/Kleinschreibung) ebenfalls auf die Kennung abbilden.

Finding:
  ID: F106
  Severity: MEDIUM
  Category: security
  Code reference: docs/context/etappe-als-art-269.md:1
  Description: Der lokale, noch nicht veroeffentlichte Stand db5c2d6 (RED-Tests) enthaelt in docs/context/etappe-als-art-269.md den Namen einer echten Reise (Platzhalter Reise A); in der Datei ist er ersetzt. Das Repo ist oeffentlich, die Projektregeln verbieten echte Reisenamen in Specs und Kontexten. Mit einem eigenen Stand obenauf bleibt der Name im Verlauf.
  Evidence: Ansicht des Stands db5c2d6, Zeile 55 des Kontextdokuments; kein Remote-Zweig enthaelt ihn (Abfrage leer); die Datei selbst ohne Treffer.
  Remediation: Vor dem Veroeffentlichen die Ersetzung in den RED-Stand einarbeiten (Fixup mit anschliessendem Zusammenfuehren), nicht als eigener Stand obenauf.

Finding:
  ID: F107
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:622
  Description: Bestand die Eckdaten-Tabelle nur aus Kennzahlen, entfernt eckdaten_ohne_kennzahlen Kopf und Trennlinie, aber nicht die Ueberschrift: es bleibt eine leere Eckdaten-Ueberschrift, der Bau legt einen Block E-01.eckdaten mit leerem HTML an, die Seite zeigt eine nackte Ueberschrift.
  Evidence: Browser, Kopie mit nur vier Kennzahl-Zeilen: Seitentext Eckdaten direkt gefolgt von Wegpunkte.
  Remediation: Bei leerem Abschnitt auch die Ueberschrift entfernen, oder der Bau laesst Bloecke ohne Inhalt weg.

Finding:
  ID: F108
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/konnektor.py:2537
  Description: DING_AENDERN bekommt einen eigenen Parameter kennzahlen (10 Properties), obwohl kennzahlen als Feld der Grundform in attributes ueber felder_aus_merkmalen schon geht (item_create tut es so). ADR-0007 will die Sonderparameter abbauen, nicht vermehren.
  Evidence: konnektor.py:2528-2540; schreiben.py:1645.
  Remediation: Parameter streichen, nur attributes.figures; die Beschreibung steht schon in ding_anlegen.merkmale.

Finding:
  ID: F109
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:798
  Description: Die Konnektor-Ausgabe der Strecken schreibt die Kennungen als Namen ("gehzeit: ca. 3:40 h; aufstieg: 485; laenge: 8,1 km"), waehrend der Konnektor sonst Namen statt Kennungen verlangt; der Altstand zeigte die Anzeigenamen des Dossiers.
  Evidence: test_konnektor.py: Zeile "gehzeit: ca. 3:40 h; aufstieg: 485".
  Remediation: Namen aus dem Katalog (seite.kennzahl.*) verwenden.

Finding:
  ID: F006
  Severity: LOW
  Category: spec_violation
  Code reference: engine/bauen.py:437
  Description: AMBIGUOUS (aus Durchgang 1, nicht gebaut, Product Owner): Der Reiter Etappen ist seit #214 nie sichtbar (ETAPPEN_REITER ist HAT_ETAPPEN und nicht PLAN_ANSICHT); Spec-Wortlaut und Ist-Zustand weichen ab. Nicht als BROKEN gewertet.
  Evidence: engine/vorlage.html (ETAPPEN_REITER), Test 4 prueft nur Datenflags.
  Remediation: Spec an den Ist-Zustand anpassen oder Seitentest ergaenzen.

Finding:
  ID: F007
  Severity: LOW
  Category: spec_violation
  Code reference: engine/bauen.py:454
  Description: AMBIGUOUS (aus Durchgang 1, nicht gebaut): Lesetext zu nicht summierter Strecke (z. B. Bahn) steht nicht auf der Tagesseite, nur per Direktlink. Spec-Mehrdeutigkeit, nicht als BROKEN gewertet.
  Evidence: engine/bauen.py:437-470 (typ strecke fuer jeden Dossier-Abschnitt).
  Remediation: Entscheidung des Product Owners dokumentieren.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/bauen.py:415
  Evidence: Referenzbau Altstand gegen Neustand: Summen, Kennzahlen-Werte, Block-IDs, Karte gleich; Etappenseiten im Browser Zeichen fuer Zeichen gleich; Beispielreise nach Nachziehen aus echten Altdaten gleich der eingecheckten.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/routen.py:419
  Evidence: kennwerte() liest nur Kennungen (KENNZAHLEN); die Suchbegriffe kommen in engine/ nur noch in neu.py, den Katalogmeldungen und Tests der Umstellung vor.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/schreiben.py:3712
  Evidence: lesetext_schreiben findet den Abschnitt ueber bauen.STRECKE_UEBERSCHRIFT (bauen.py:52); die Seite entscheidet ueber R.strecken[..].summiert, kein Artname im Code.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_de.py:505
  Evidence: seite.tag.angaben_fehlen, konnektor.werkzeug.ding.kennzahlen, schreiben.kennzahlen.form, pruefung.routen.kennzahlen_gehzeit, pruefung.routen.kennzahlen, pruefung.bauen.dossier_ohne_strecke und die sechs pruefung.neu.nachziehen-Schluessel stehen in texte_de.py und texte_en.py (texte_en.py:504); test_texte.py ist unveraendert, die Ausnahmelisten sind nicht laenger.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/schnittstelle.py:129
  Evidence: Kennungen und englische Aliase fuer Kennzahlen (KENNZAHL_ALIAS) sowie PARAMETER kennzahlen und figures; bei fehlenden Angaben zeigt die Tagesseite seite.tag.angaben_fehlen (Test 8 gruen).
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: werkzeuge/punkte_holen.py:141
  Evidence: dossier_namen liest die Kennung der Ueberschrift (E-0N); ce72978 (#268) ist Vorfahre von HEAD.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_en.py:504
  Evidence: Die englischen Texte der neuen Schluessel (seite.tag.angaben_fehlen, schreiben.kennzahlen.form, pruefung.neu.nachziehen-Meldungen) stehen vollstaendig in texte_en.py; es gibt nur texte_de.py und texte_en.py.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: BROKEN

Finding F101: nachziehen entfernt Kennzahl-Zeilen, schreibt sie aber nicht an die Strecke, wenn diese schon eine Kennzahl hat (Datenverlust).
  Severity: HIGH
  Evidence: engine/neu.py:691
  Reproduction: Beispielreise im Altformat, E-01 mit gehzeit "5:00 h" in routen.yaml, Dossier mit Kennzahl-Zeilen, nachziehen: Aufstieg, Abstieg, Laenge weg.

Finding F103: zwei Namen mit derselben Kennung ueberschreiben sich, beide Zeilen entfallen, still.
  Severity: HIGH
  Evidence: engine/neu.py:688
  Reproduction: etappen_kennzahlen mit Gehzeit und "Gehzeit mit Pausen", zwei Zeilen im Dossier, nachziehen.

Weitere: F102, F104, F105, F106 (MEDIUM); F107, F108, F109 (LOW); F006, F007 AMBIGUOUS (nicht als BROKEN gewertet).
Behoben und bestaetigt: F001 (Seite filtert nicht mehr nach Wert), F002 (fuer den Normalfall), F003, F004, F008.
Tests: 1373 passed in 1219.55s, 0 failed, 0 uebersprungen

## Geprüfte Dateien

- sha256:04fff02a15ceca9bea4c7f22dc0ea94067cc8c2bd862569599ef32d0a97f2fe3  docs/context/etappe-als-art-269.md
- sha256:1614821e4efe9d28efef32ad22b40802f0e3d4c2bea7787c03a0e2ffe6a351bf  engine/bauen.py
- sha256:a57000b5013a4d49cd2e2e7c5760670d7bd449fa45775fc4915f8acd144a5a72  engine/konnektor.py
- sha256:b4707d93f54a79b4e535ae305537c19783199797fcc62d4c52dcd27759626cb1  engine/neu.py
- sha256:e4ab5bb66f7723a6e7bac2275901fcfe676f25e5de91e0a4f9b7ed9a8d79c538  engine/routen.py
- sha256:1282d283b0bf30cacd06c6f542c6f4b4b9af3f6d079d6d00fc89a7cfbbc4ca84  engine/schnittstelle.py
- sha256:9a808e9e8cdb8ee03f9fb03e2f9a7a2c221640eb54f31abdfc3b04d28f98b348  engine/schreiben.py
- sha256:29daf1f943156b48c44bcc6f9caf992f1ee47d74843394790c79ed6915d50ce2  engine/texte_de.py
- sha256:417d7851f09fe7425013e1bdc8037a282f642a489a536269ec40194fa0917a6e  engine/texte_en.py
- sha256:931932cee2e6c5e2944832969be5000222093c7de8cba6c9de3088d9d57615c9  werkzeuge/punkte_holen.py

## Prüfbasis

- base: faf3ac103ce0ee76a1d89b222f3e14f75848b86b
- blob:293148795ee0338a342cc14c3e43e9c979ac630c  docs/context/etappe-als-art-269.md
- blob:ac300be1728d1e53eb5f27bc5e5eaced2ea3881e  engine/bauen.py
- blob:f197c8d2d3a25517f066f070d98dd020e360ab09  engine/konnektor.py
- blob:b096b15465a91231ab24730a43ae8e3f1135e8fe  engine/neu.py
- blob:0f4e8875de8a526b7abbfe10692543ff6fed28bc  engine/routen.py
- blob:c8f63ce087e037eabd32815a173019bd05811ac6  engine/schnittstelle.py
- blob:f2630c57bc59f8ede5b90baf7e5e4cd68e95c6b7  engine/schreiben.py
- blob:fe821ee6318eb949c1a83ccf8e0e4ce9c2cd84f2  engine/texte_de.py
- blob:4030d98450d317d12e21254a584a10dffeed68cd  engine/texte_en.py
- blob:bf3b806ef99b856e7a4fddeccee1c8876a8e8658  werkzeuge/punkte_holen.py
