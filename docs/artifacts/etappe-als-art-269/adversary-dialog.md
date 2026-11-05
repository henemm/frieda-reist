# Adversary Dialog — etappe-als-art-269
Spec: docs/specs/oberflaeche/etappe-als-art-269.md
Datum: 2026-11-05 07:06

## Checkliste
- [x] **AC-1:** (Test 1, 10): Die Seite der Beispielreise zeigt Etappenseiten, Tagesseiten, Kennzahlen und Karte inhaltlich wie vorher (Werte gleich, Reihenfolge gleich). PROVEN fuer die ausgelieferte Beispielreise (Einschraenkung F001: gilt nicht fuer Altbestand mit Eckdaten-Zeilen, deren Wert anders formatiert ist oder zufaellig einem Kennzahlwert gleicht)
- [x] **AC-2:** (Test 5): `grep` auf `REGEL.gehzeit`, `kennzahlPaar`, `typ === "etappe"`, `etappen_muster` in `engine/` (außer `neu.py nachziehen` und Tests der Umstellung) findet nichts. PROVEN
- [x] **AC-3:** (alle Tests): `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün (beide Beispielreisen, auch `stadtwochenende` ohne Etappen). PROVEN (1369 passed, 0 failed, 0 uebersprungen)
- [x] **AC-4:** (Test 2, 3): `neu.py nachziehen` stellt die Beispielreise ohne Handschritt um, ist idempotent und lässt Reisen ohne Dossier unberührt. PROVEN fuer die Beispielreise und stadtwochenende; DISPROVEN fuer Randfaelle (F002 Altnamen in routen.yaml, F003 doppelte Ueberschrift)
- [x] **AC-5:** (Test 4): Eine Reise mit anderer summierter Art (nicht `wandern`) bekommt ihre Etappen im Reiter „Etappen“, ohne dass Code den Artnamen kennt. PROVEN auf Datenebene und auf der Seite (Prädikat istEtappe); der Reiter selbst ist seit #214 nie sichtbar (F006, AMBIGUOUS)
- [x] **AC-6:** (Test 9): Das Wort „Etappe“ steht nur im Textkatalog (alle Sprachen); `test_texte.py` bleibt grün. PROVEN (nur texte_de.py und texte_en.py existieren, beide haben alle neuen Schluessel; test_texte.py ungeaendert)
- [x] **AC-7:** (Test 8): Tag mit summierter Strecke ohne Angaben zeigt „Angaben fehlen“. PROVEN
- [x] **AC-8:** (Prozess, kein Test): Umsetzung beginnt erst, wenn #268 auf `main` ist (vor dem ersten Edit an `routen.py`/`vorlage.html` geprüft); der Branch setzt auf diesen Stand auf. PROVEN (Commit ce72978 ist Vorfahre von HEAD)

## Dialog

### Runde 1
**Adversary:** Ich gehe davon aus, dass der Umbau Werte veraendert. Vergleich Bau Altstand (Kopie des Repos vor der Umstellung, Stand faf3ac1) gegen jetzigen Stand mit dem Schnappschuss-Skript: Plan-Summen (P-A, P-B), Kennzahlenwerte je Strecke, `summiert`, Abschnitts-IDs, Block-IDs, Ebenen, `im_plan`, `optionen`, `nebenroute`. Dazu die gebaute Seite im Browser: Kennzahlenleiste, Eckdaten-Zeilen und Tageszeilen von E-01..E-04, Karten-Teil von daten.json. Erwartete Abweichung: Titel ohne „Etappe N:“, Kennungen statt Namen, Abschnittstyp strecke statt etappe.
**Implementierer:**
- Summen gleich (True), `summiert` je Strecke gleich, Abschnitts-IDs gleich, Block-IDs und Ebenen gleich; einzige Abweichungen: `typ` etappe -> strecke und Titel ohne „Etappe N:“ (4 Abschnitte E-01..E-04). stadtwochenende: Schnappschuss vor/nach byte-gleich (`cmp` ohne Ausgabe).
- Browser (ausdruecke() aus test_seite_sprachen.py): Kennzahlenbeschriftungen und -werte aller vier Etappen GLEICH (z. B. Gehzeit ca. 3:40 h, Aufstieg 485 m, Abstieg 285 m, Strecke 8,1 km), Anzahl und Namen der Merkmalzeilen GLEICH (3/2/2/2), Tageszeilen GLEICH (3:40 h · 8,1 km, 4:00 h · 10,7 km, 2:15 h · 6,6 km). Abweichung nur in den Kartentiteln der Etappenkarten (ohne „Etappe N:“) – erwartet. Karte: im Vergleich der daten.json (vorher/nachher) kein Unterschied unter `route.karte`.
- AC-2: Suche in engine/ nach `REGEL.gehzeit|aufstieg|abstieg|laenge`, `kennzahlPaar`, `typ === "etappe"`, `etappen_muster` ohne Treffer ausser neu.py, den Katalog-Meldungen und den Tests der Umstellung. engine/tests/test_seite_sprachen.py:251 nennt `REGEL.gehzeit` nur als negative Pruefung (`typeof REGEL.gehzeit === "undefined"`) – zulaessig. Kein Artname `wandern` als Artlogik im Code, nur Symbolname (routen.py SYMBOLE_ARTEN, bauen.py Symbolzuordnung) und eine lokale Variable (vorlage.html:2274).
- AC-8: Vorfahren-Pruefung von ce72978 gegen HEAD: wahr.
- Bis hierher kein Fund. Die Spec sagt, die Zuordnung Kennzahl -> Kennung geschehe „genau einmal“; ich pruefe deshalb in Runde 2 die Randfaelle der Zuordnung und den neuen Seitenfilter.

### Runde 2
**Adversary:** Gezielte Brueche: (a) Eckdaten-Zeilen der Dossier-Tabelle, die jetzt per WERT statt Name von der Kennzahlenleiste abgezogen werden (`reiseText`); (b) Altformat-Reisen mit Kennzahlen unter Anzeigenamen schon in routen.yaml; (c) nachziehen mit Sonderfaellen (Gehzeit „3,5 h“, Etappe „3a“ ohne Strecke, doppelte Ueberschrift); (d) andere summierte Art ohne Dossier und nicht summierte Art mit Dossier; (e) Konnektor: Kennzahlen an Strecken; (f) Katalog und Ausnahmelisten; (g) volle Testsuite.
**Implementierer:**
- (a) Kopie der migrierten Beispielreise, Zeile `| Rastplätze | 400 |` in die Eckdaten von E-02 eingefuegt (Aufstieg ist ebenfalls 400): auf der Seite fehlt die Zeile, die Merkmalliste zeigt nur Höchster Punkt und Herkunft statt drei Zeilen. Gegenprobe: Altstand-Kopie mit `| Länge (km) | 10,7 |` (ohne „km“), nach nachziehen: Strecke hat `laenge: 10.7` (Zahl), die Seite zeigt die Dossier-Zeile „Länge (km)“ ZUSAETZLICH zur Kennzahlenleiste (Zeilen: Länge (km), Höchster Punkt, Herkunft). Der Wertevergleich ist also zugleich zu weit (echte Zeile verschwindet) und zu eng (Dublette bleibt). -> F001.
- (b) Altstand-Kopie, an E-02 in routen.yaml `kennzahlen: {Gehzeit: "9:00 h", "Länge (km)": "30 km"}` (der Altstand las das und gab ihm Vorrang vor dem Dossier). Altstand-Bau: Plan P-A min 910, km 45.5, fehlend [ab, auf]. Nach nachziehen und neuem Stand: P-A min 370, km 15.5, fehlend [ab, auf, km, min]; die Namen bleiben unveraendert unter „Gehzeit“ stehen, nachziehen meldet nichts. -> F002.
- (c) Altstand-Kopie mit Ueberschrift „Etappe 3a: Ohne Strecke“: nachziehen meldet `OFFEN E-03a ...` (gut), laesst die Einstellungen in reise.json stehen, zweiter Lauf wiederholt die Meldung (gut, idempotent). Gehzeit „3,5 h“ landet als Text an E-02, `minuten()` rechnet 210 (gut). Doppelte Ueberschrift „Etappe 1: Doppelt“ (ohne 3a): nachziehen schreibt sie stillschweigend in „E-01 Doppelt“ um, loescht `etappen_kennzahlen`/`etappen_muster`, zweiter Lauf leer; erst der Bau bricht mit „Duplicate ID E-01“. Spec-Risiko verlangt „meldet offen statt zu raten“. -> F003. Idempotenz der Beispielreise: zweiter Lauf `[]`; Ergebnis gleicht der eingecheckten Beispielreise bis auf Kommentarzeilen in routen.yaml (von Hand ergaenzt, kein Wert). stadtwochenende: Verzeichnisvergleich vor/nach leer.
- (d) AC-5: Kopie mit Art `spaziergang` (Schluessel in arten.yaml und art in routen.yaml umbenannt): `R.strecken[..].summiert` fuer E-01..E-04 wahr, `abschnitte.filter(istEtappe)` liefert E-01..E-04, Tageszeilen unveraendert. Eine Strecke der Art bahn mit `gehzeit` ist nicht summiert. Ohne Dossier-Abschnitt: zwei summierte Strecken ohne Lesetext sind in `R.strecken` summiert, aber nicht `istEtappe` (Prädikat prueft `proId`); im Altstand war das genauso (Typ etappe nur mit Dossier), die Spec-Formulierung „alle Strecken“ trifft aber nicht zu. Der Reiter „Etappen“ ist seit #214 nie sichtbar, weil `PLAN_ANSICHT` bei jeder Reise mit Routen gesetzt ist (`ETAPPEN_REITER = HAT_ETAPPEN && !PLAN_ANSICHT`); Test 4 prueft nur Datenflags. -> F006 (AMBIGUOUS). Dossier-Abschnitt zu nicht summierter Strecke (E-20, bahn): per Direktlink sichtbar, auf der Tagesseite T-02 nicht (Altstand: als Etappe auf der Tagesseite). -> F007 (AMBIGUOUS).
- (e) `kennzahlen_wert`: Anzeigename „Gehzeit“ wird als eigener Name gespeichert (nicht summiert); „gehzeit“: „abc“ wird akzeptiert (-> „Angaben fehlen“, vertretbar). `item_create` (DING_ANLEGEN) hat im inputSchema keine Eigenschaft `kennzahlen`, `item_update` schon; `ding_anlegen()` verarbeitet sie, der Test umgeht das Schema. -> F004, F005. Unquotiertes `gehzeit: 3:30` von Hand wird von PyYAML als Zahl 210 gelesen und ergibt 12600 Minuten (der Schreibweg quotiert korrekt) -> F008.
- (f) Katalog: es gibt nur texte_de.py und texte_en.py; beide tragen die neuen Schluessel (seite.tag.angaben_fehlen, konnektor.werkzeug.ding.kennzahlen, schreiben.kennzahlen.form, pruefung.routen.kennzahlen, pruefung.bauen.dossier_ohne_strecke, vier pruefung.neu.nachziehen.etappe*). `engine/tests/test_texte.py` ist im Diff unveraendert, die Ausnahmelisten sind nicht laenger. „Angaben fehlen“ erscheint nur bei Tagen mit summierter Strecke ohne Gehzeit (Browser: „Angaben fehlen · 10,7 km“ nach Entfernen der Gehzeit von E-02), nicht bei Tagen ohne summierte Strecke (T-01 leer) und nicht bei Tagen mit Gehzeit. Englischer Text „figures missing“ beginnt klein (kosmetisch).
- (g) Volle Suite, seriell: siehe docs/artifacts/etappe-als-art-269/adversary-test-output.txt, `1369 passed in 1239.34s`.
- Nicht geprueft: Browser-Rundgang ueber engine/tests/seiten_browser.mjs und seiten_reise.mjs ausserhalb der Suite und eine frische Reise aus engine/reisevorlage; Tests der einbindenden Instanzen; Konnektor-Abnahme an einer Testreise ueber die App.

## Findings

Finding:
  ID: F001
  Severity: HIGH
  Category: regression
  Code reference: engine/vorlage.html:1196
  Description: reiseText() entfernt Merkmalzeilen aus dem Lesetext jetzt auch, wenn ihr WERT einem Wert der Kennzahlenleiste entspricht (`werte.has(normKz(dd.textContent))`), weil die Seite Namen nicht mehr sucht. Eine echte Zeile mit gleichem Wert (z. B. „Rastplätze | 400“ bei Aufstieg 400) verschwindet. Umgekehrt bleibt eine Dossier-Zeile, die nach nachziehen anders formatiert ist („Länge (km) | 10,7“ wird Zahl 10.7, String „10.7“ ungleich „10,7“), als Dublette neben der Leiste stehen. Beides im Browser nachgestellt.
  Spec requirement: AC-1 — Kennzahlen und Etappenseite inhaltlich wie vorher; Test-Plan: Wertevergleich vor/nach.
  Conflict: Der Altstand filterte nach Namen (nur die Kennzahlzeilen); der Wertevergleich versteckt fremde Inhalte und laesst Dubletten zu. Die Beispielreise zeigt es nicht, weil ihre Dossierwerte zufaellig exakt gleich formatiert sind.
  Remediation: Beim nachziehen die Kennzahlzeilen aus der Eckdaten-Tabelle des Dossiers entfernen (sie stehen jetzt an der Strecke) und in reiseText() nichts mehr filtern; alternativ nur Name UND Wert gemeinsam vergleichen.

Finding:
  ID: F002
  Severity: HIGH
  Category: regression
  Code reference: engine/routen.py:422
  Description: kennwerte() liest nur noch die Kennungen gehzeit/aufstieg/abstieg/laenge. Kennzahlen, die eine Strecke schon im Altformat in routen.yaml unter Anzeigenamen trug („Gehzeit“, „Länge (km)“; der Altstand las sie und gab ihnen Vorrang vor dem Dossier), werden von etappen_nachziehen (engine/neu.py:603, „nur, wo sie fehlen“) nicht umbenannt und bei Summen stillschweigend ignoriert. Nachweis: Plan P-A 910 -> 370 Minuten, km 45.5 -> 15.5, `fehlend` waechst um km und min; nachziehen meldet nichts.
  Spec requirement: Prüfstelle/Implementation Details — Namen der Reise „wandern beim Umstellen in Kennungen“; CLAUDE.md — Formatwechsel bringen ihre Umstellung in nachziehen mit, ein Handschritt ist ein Fehler (#250).
  Conflict: Verlust von Kennzahlen in der Summe fuer jede Reise mit namensbasierten Kennzahlen in routen.yaml; nachziehen deckt nur das Dossier ab.
  Remediation: nachziehen soll vorhandene `kennzahlen` in routen.yaml ueber kennung_der_kennzahl() (engine/neu.py:581) auf Kennungen umschreiben (mit Test); alternativ meldet der Bau unbekannte Namen, die wie eine Kennung aussehen.

Finding:
  ID: F003
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/neu.py:625
  Description: Zwei Dossier-Ueberschriften „Etappe 1: ...“ werden beide stillschweigend zu „E-01 ...“ umgeschrieben, die Einstellungen etappen_kennzahlen/etappen_muster entfallen, nachziehen laeuft sauber durch; erst der Bau bricht („Duplicate ID E-01“). Die zweite Etappe verliert ihre Kennzahlen unbemerkt.
  Spec requirement: Risiken — „Sind Überschrift und ID nicht eindeutig zuzuordnen, meldet nachziehen offen statt zu raten.“
  Conflict: nachziehen verdoppelt die Kennung statt OFFEN zu melden und behaelt die Einstellungen nicht.
  Remediation: Doppelte alte_etappen_id in einem Dossier als OFFEN melden, nicht umschreiben, Einstellungen behalten.

Finding:
  ID: F004
  Severity: MEDIUM
  Category: spec_violation
  Code reference: engine/konnektor.py:2515
  Description: Das Werkzeug item_create (DING_ANLEGEN) hat in seinem inputSchema keine Eigenschaft `kennzahlen` (nur DING_AENDERN, engine/konnektor.py:2537), obwohl ding_anlegen() sie verarbeitet (engine/schreiben.py:1436). Der Test ruft den Schreibweg direkt auf und umgeht das Schema.
  Spec requirement: Abnahme — Konnektor: Strecke mit Kennzahlen anlegen.
  Conflict: Ein AI-Client sieht beim Anlegen kein Feld fuer Kennzahlen; eine neue Etappe hat bis zum Folgeaufruf von item_update keine.
  Remediation: `kennzahlen` in DING_ANLEGEN aufnehmen (Beschreibung ist in de/en vorhanden) oder die Abnahme auf item_update beschraenken und dokumentieren.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/schreiben.py:1514
  Description: kennzahlen_wert() uebersetzt nur englische Namen (KENNZAHL_ALIAS, engine/schnittstelle.py:129); der Anzeigename „Gehzeit“ oder „Aufstieg (Hm)“ wird als eigene Kennzahl gespeichert und nie summiert; Werte werden nicht auf die Form h:mm geprueft („gehzeit“: „abc“ ergibt nur „Angaben fehlen“).
  Spec requirement: Datenformat — feste Kennungen, Gehzeit „h:mm“.
  Conflict: Falsch benannte Kennzahl wird still akzeptiert.
  Remediation: Eigene Namen, die nach einer bekannten Kennung aussehen (Katalogwort, Gross-/Kleinschreibung), ablehnen oder mit Hinweis in die Kennung umsetzen.

Finding:
  ID: F006
  Severity: LOW
  Category: spec_violation
  Code reference: engine/vorlage.html:1100
  Description: `istEtappe(a)` (vorlage.html:1049) prueft `R.strecken[a.id].summiert` fuer Dossier-Abschnitte; eine summierte Strecke ohne Dossier-Abschnitt gilt nicht als Etappe. ETAPPEN_REITER = HAT_ETAPPEN && !PLAN_ANSICHT ist immer falsch, weil PLAN_ANSICHT bei jeder Reise mit Routen gesetzt ist (vorlage.html:1081); der Reiter „Etappen“ der Spec-Entscheidung 2 existiert damit nirgends. Test 4 prueft nur Datenflags, keine Seite.
  Spec requirement: Scope 6 / Entscheidung 2 — Reiter „Etappen“ zeigt alle Strecken mit summierter Art; AC-5.
  Conflict: Wortlaut der Spec nicht erfuellbar; Verhalten entspricht dem Altstand (#214), nicht der Spec-Formulierung.
  Remediation: Spec-Formulierung an den Ist-Zustand anpassen (Etappen stehen am Tag und unter „Weitere Wege“) und Test 4 um einen Seitentest erweitern.

Finding:
  ID: F007
  Severity: LOW
  Category: edge_case
  Code reference: engine/bauen.py:437
  Description: Jeder Dossier-Abschnitt „## E-... Name“ bekommt `typ: "strecke"`; gehoert er zu einer nicht summierten Art (z. B. bahn), ist er keine Etappe und fehlt auf der Tagesseite (ansichtTag nutzt etappeZu), ist nur per Direktlink #E-20 zu lesen. Im Altstand waren alle Dossier-Abschnitte Etappen.
  Spec requirement: Scope 2 — Dossier liefert Lesetext zu einer Strecke.
  Conflict: Lesetext zu nicht summierten Strecken ist ohne Direktlink nicht erreichbar.
  Remediation: Entscheidung dokumentieren oder Lesetext nicht summierter Strecken am Tag zeigen.

Finding:
  ID: F008
  Severity: LOW
  Category: edge_case
  Code reference: engine/routen.py:583
  Description: Die Pruefung der kennzahlen akzeptiert jede Zahl; `gehzeit: 3:30` ohne Anfuehrungszeichen in routen.yaml wird von yaml.safe_load (engine/bauen.py:599) als sexagesimale Zahl 210 gelesen, minuten(210) ergibt 12600 Minuten, ohne Meldung. Der Schreibweg (ruamel) quotiert korrekt.
  Spec requirement: Datenformat — Gehzeit Text im Format h:mm.
  Conflict: Handgeschriebene Reise kann stille Fehlsummen bekommen.
  Remediation: gehzeit als Zahl ablehnen oder Meldung bei nicht-Text-Gehzeit.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/bauen.py:415
  Evidence: dossier_lesen()/strecken_lesetext() liefern Abschnitte mit gleichen IDs, Bloecken und Ebenen; Vorher/Nachher-Schnappschuss und Browserwerte der Beispielreise gleich.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/routen.py:419
  Evidence: kennwerte() liest nur Kennungen (KENNZAHLEN); REGEL.*, kennzahlPaar, typ === "etappe", etappen_muster sind aus engine/ ausser neu.py, Katalogmeldung und Tests entfernt.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/schnittstelle.py:129
  Evidence: KENNZAHL_ALIAS und PARAMETER „kennzahlen“ sind eingetragen; volle Suite 1369 passed, 0 failed, 0 uebersprungen (docs/artifacts/etappe-als-art-269/adversary-test-output.txt).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/neu.py:603
  Evidence: etappen_nachziehen stellt die Beispielreise um (Ergebnis gleicht der eingecheckten Beispielreise bis auf Kommentare), zweiter Lauf `[]`, stadtwochenende unveraendert.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/schreiben.py:3710
  Evidence: lesetext_schreiben findet den Abschnitt ueber bauen.STRECKE_UEBERSCHRIFT; die Seite entscheidet ueber R.strecken[..].summiert, kein Artname (Test mit Art spaziergang: E-01..E-04 sind Etappen).
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_de.py:505
  Evidence: seite.tag.angaben_fehlen und alle neuen Schluessel stehen in texte_de.py und texte_en.py (engine/texte_en.py:504); es gibt keine weitere Sprachdatei; test_texte.py gruen und unveraendert.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/vorlage.html:2934
  Evidence: ohneZeit = !m && gezaehlt && fehlend.includes("min"); Browser: „Angaben fehlen · 10,7 km“ bei fehlender Gehzeit, leer bei Tag ohne summierte Strecke.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: werkzeuge/punkte_holen.py:143
  Evidence: dossier_namen liest die Ueberschrift „## E-nn“ (Folge der Formatumstellung, gehoert zu #269); #268 (ce72978) ist Vorfahre von HEAD.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: BROKEN

Tests: 1369 passed, 0 failed, 0 uebersprungen (volle Suite seriell, 20:39 Minuten).
Begruendung: F001 (Seitenfilter nach Wert versteckt echte Zeilen und laesst Dubletten zu) und F002 (Kennzahlen unter Altnamen in routen.yaml gehen bei Summen verloren, nachziehen stellt sie nicht um) sind reproduzierbare Regressionen. F003 und F004 mittel, F005 bis F008 niedrig.
Nicht geprueft: Browser-Rundgang ueber seiten_browser.mjs und seiten_reise.mjs ausserhalb der Suite; frische Reise aus engine/reisevorlage; Tests der einbindenden Instanzen; Konnektor-Abnahme ueber die App an einer Testreise.

## Geprüfte Dateien

- sha256:1614821e4efe9d28efef32ad22b40802f0e3d4c2bea7787c03a0e2ffe6a351bf  engine/bauen.py
- sha256:a57000b5013a4d49cd2e2e7c5760670d7bd449fa45775fc4915f8acd144a5a72  engine/konnektor.py
- sha256:dc2446cc4fab37634234a9bc0a22434b22498e061f3ea59e831fd95084c04eb2  engine/neu.py
- sha256:6547391527f11ba127e7af8707af8601efca684d7887d5054cd244a663e802fa  engine/routen.py
- sha256:1282d283b0bf30cacd06c6f542c6f4b4b9af3f6d079d6d00fc89a7cfbbc4ca84  engine/schnittstelle.py
- sha256:538cef9294dfc6f55ba157db1864d963a208620e781cad42ebf9a2a87f1e9bda  engine/schreiben.py
- sha256:0093fd478f64c3efa167f5523d4182f3da7aebf1f3ececac5216cad1ded9221c  engine/texte_de.py
- sha256:739708bb38497d4097f112754ce27f36d0fb908a2feb79ee611e7df7e054f620  engine/vorlage.html
- sha256:931932cee2e6c5e2944832969be5000222093c7de8cba6c9de3088d9d57615c9  werkzeuge/punkte_holen.py

## Prüfbasis

- base: faf3ac103ce0ee76a1d89b222f3e14f75848b86b
- blob:ac300be1728d1e53eb5f27bc5e5eaced2ea3881e  engine/bauen.py
- blob:f197c8d2d3a25517f066f070d98dd020e360ab09  engine/konnektor.py
- blob:a03a711e2578e3300fd6e61befffb7b831e0db2d  engine/neu.py
- blob:d75b56d0a71d0c984d48223ae10c2f7f71edc16e  engine/routen.py
- blob:c8f63ce087e037eabd32815a173019bd05811ac6  engine/schnittstelle.py
- blob:6261ffad855c95a0f3d08e068098ac289ca9167b  engine/schreiben.py
- blob:20bf96d7c4bb99777442c0ea5cb232573b213908  engine/texte_de.py
- blob:60c1b2389b531d0ec0b5328e0e43e7730de89710  engine/vorlage.html
- blob:bf3b806ef99b856e7a4fddeccee1c8876a8e8658  werkzeuge/punkte_holen.py
