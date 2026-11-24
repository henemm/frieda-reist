# Adversary Dialog — fix-665-zeitleiste
Spec: docs/specs/oberflaeche/zeitleiste-bewegung-665.md
Datum: 2026-11-24 19:02

## Checkliste
- [x] **AC-1:** Given ein Ding mit einem Zeitpunkt-Merkmal ohne Rolle / When die Reise gelesen wird / Then ist es gültig und bleibt Merkmal; `uhrzeit` ohne Rolle bleibt ein Fehler, abfahrt und ankunft gelten je einmal.
- [x] **AC-2:** Given eine Reise, die `erinnern` an einem Zeitpunkt-Merkmal setzt (Konnektor `remind` oder `erinnern`) / When sie gespeichert und gelesen wird / Then ist die Eigenschaft sichtbar in `attributes` und `show`; an anderen Typen wird sie mit Text aus dem Katalog abgelehnt.
- [x] **AC-3:** Given ein erinnernder Zeitpunkt mit Datum bei Status fest / When der Wächter läuft / Then kommt genau eine Erinnerung auf dem gleichen Meldeweg wie die Buchungs-`ab` und der Kalender trägt genau einen Termin mit eigener UID; ohne Datum wird nicht erinnert.
- [x] **AC-4:** Given eine Buchungs-`ab` und ein erinnerndes Merkmal mit gleichem Zeitpunkt am selben Ding / When Wächter und Kalender laufen / Then gibt es nur eine Erinnerung und einen Kalendertermin.
- [x] **AC-5:** Given eine Bewegung mit mindestens einem Zeitpunkt außer Abfahrt und Ankunft (Merkmal oder Buchungs-`ab`) / When ihre Heimat gezeigt wird / Then erscheint die Zeitleiste in zeitlicher Reihenfolge (freier Punkt bei gleicher Zeit vor der Abfahrt bzw. hinter der Ankunft).
- [x] **AC-6:** Given dieselbe Zeitleiste / When ihre Schrift gemessen wird / Then haben alle Uhrzeiten und Daten (auch das Datum der Kopfzeile und ein abweichendes Datum) dieselbe Schriftgröße; Abfahrt und Ankunft unterscheiden sich nur durch fetten Namen und gefüllten Punkt.
- [x] **AC-7:** Given eine Bewegung mit Zeitleiste / When ihre Kopfzeile unter dem Titel gezeigt wird / Then steht dort, sofern der Tag der Fahrt bekannt ist, nur das Datum der Fahrt (fett, Größe der Uhrzeiten) ohne Art-Name und ohne Uhrzeiten, sonst entfällt die Zeile; ein abweichendes Datum eines Punkts steht fett direkt unter seiner Uhrzeit in derselben Spalte.
- [x] **AC-8:** Given dieselbe Bewegung / When die Heimat gezeigt wird / Then steht jeder Zeitpunkt nur in der Zeitleiste (nicht auch in der Merkmalliste), andere Merkmale bleiben in der Liste, und der Buchungsblock zeigt keine ab-Zeile; an Unterkünften bleibt die ab-Zeile.
- [x] **AC-9:** Given eine Bewegung ohne weitere Zeitpunkte (Bahnstrecke der Beispielreise) / When ihre Heimat gezeigt wird / Then bleibt die kurze Zeile „ab … → an …“ und die heutige Kopfzeile „Art · Datum · ab … → an …“ unverändert.
- [x] **AC-10:** Given ein Merkmal mit `bei: <Schlüssel>` (Zeitpunkt-Merkmal derselben Art, oder `abfahrt`/`ankunft`) / When die Reise gelesen oder `attribute_define` mit `at` oder `bei` aufgerufen wird / Then ist die Zuordnung gespeichert und in `attributes` und `show` sichtbar; an Zeitpunkt/Uhrzeit-Merkmalen und bei unbekanntem Ziel wird sie mit Text aus dem Katalog (de und en) abgelehnt.
- [x] **AC-11:** Given ein Merkmal mit `bei` und Wert an einer Bewegung mit Zeitleiste / When ihre Heimat gezeigt wird / Then steht sein Wert als Zusatzzeile unter dem zugehörigen Punkt und nicht in der Merkmalliste; fehlt der Punkt oder die Zeitleiste, steht es in der Merkmalliste wie heute; die Sichtbarkeit `nach_buchung` bleibt maßgeblich.
- [x] **AC-12:** Given der Quelltext der Vorlage / When `test_design.py` läuft / Then sind Molekül `zeitLeiste` und die gemeinsamen Atome an den vier Stellen (Kopfkommentar, Stile, Bausteinseite, `docs/design.md`) registriert, `zeitLeiste` und `halteLeiste` nutzen dieselben Atome, und die Halteleiste sieht im Browser-Vergleich unverändert aus.
- [x] **AC-13:** Given beide Beispielreisen / When Seite, Wächter, Kalender und Konnektor geprüft werden / Then zeigen Seite und Konnektor `show` an E-01 dieselben Zeitpunkte, Wächter und Kalender melden je erinnerndem Zeitpunkt mit Datum genau einen Termin (Tests 5–7, 11), und die gespeicherten Reisedaten sind außer den neuen Beispielwerten unverändert; `neu.py nachziehen` ändert nichts (Test 14).
- [x] **AC-14:** Given die vollständige Testsuite / When `engine/.venv/bin/python -m pytest -q engine/tests -n 3` läuft / Then ist sie grün, einschließlich `test_texte.py`, `test_design.py`, des Browser-Tests der Heimat der Strecke, der Gegenprobe der Halteleiste und des Protokolltests ohne Pfade.

## Dialog

### Runde 1
**Adversary:** Alle Punkte der Checkliste einzeln gegen Code und Tests geprüft, nicht dem Vermerk "3668 passed" vertraut. Gezielte Läufe: 13 Testdateien (Zeitleiste, Buchung-Zeitraum, Design, Texte, Betrieb, englische Schnittstelle, Kalender, Konnektor, neu, schreiben, typisierte Merkmale, Wächter, Option-Aufenthalte): 711 passed, 0 übersprungen (adversary-test-output.txt; Browsertests chromium und webkit liefen mit). Vorabfrage: Wird eine Kernbehauptung nur durch Fixtures gestützt, die der Implementierer selbst gebaut hat? Der Wächtertest stadt_fest schreibt die Merkmaldefinition per Hand in daten.json; ich habe deshalb die Seitendaten-Erzeugung selbst mit abgewandelten Beispielreisen gebaut.
Eigene Angriffe (Ergebnis):
- Zeitpunkt an anderem Tag als die Fahrt (13.3. bei Fahrt 12.3.): hinter der Ankunft, Datum abweichend; korrekt.
- Merkmal-Zeit nach der Ankunft (12:00): hinter der Ankunft; korrekt.
- Merkmal gleich Abfahrt (09:10) und gleich Ankunft (11:25): freier Punkt vor der Abfahrt bzw. hinter der Ankunft (routen.py:490, Rang -1/0/1); korrekt.
- Ungültiger Wert 25:99: Bauabbruch mit Katalogtext (lage_wert); korrekt.
- bei auf Merkmal derselben Art (freischalten): gültig; bei auf nicht vorhandenes Ziel, auf sich selbst, leer, bei an einem Zeitpunkt-Merkmal: je Bauabbruch mit Katalogtext (en geprüft, Valid targets: departure, arrival, freischalten); korrekt.
- erinnern an Typ geld oder als String: abgelehnt (routen.py:1621-1624, Tests grün).
- Unterkunft mit Buchungs-ab: ab-Zeile bleibt (Browser-Gegenprobe test_seite_gegenprobe_ohne_zeitleiste_und_unterkunft grün); Wanderung unbeeinflusst (Halteleiste-Vergleich mit halteleiste_vorher.json, aus RED in HEAD, grün).
- Wächter-Entprellung: Schlüssel zeit:Ding:Merkmal:Wert (waechter.py:279), wie ab: der Buchung; zweiter Lauf am Folgetag meldet nicht erneut (Test 5). Status ungleich fest sperrt über die Verhaltenstabelle (waechter.py:272). Kalender-UID Ding-zeit-Merkmal stabil (kalender.py:206), eindeutig gegen B-01-E-01-ab.
- Keine Reisespezifika in der Engine: Beispielmerkmale (freischalten, gleis) stehen nur in beispiel/reisen/stadtwochenende/plan/*.yaml; die Engine arbeitet über die Definition erinnern und bei.
Befunde: F001 (Nachtfahrt mit Ankunft ohne Datum), F002 (Strecke ohne Plantag), F003, F004 (klein).
**Implementierer:** (nicht beteiligt; Kontextisolation)

### Runde 2
**Adversary:** Nachgefasst auf die Früh-Einigkeit der ersten Runde: Chronologie (AC-5) mit Daten gebrochen, die das Datenmodell zulässt.
- Reproduktion F002: Beispielreise stadtwochenende, tage.T-01.strecken leer setzen (E-01 hängt an keinem Plantag). Zeitleiste: abfahrt (Datum leer, 09:10), ankunft (leer, 11:25), dann Merkmal freischalten (2027-03-11 08:00), dann Buchungs-ab (2027-03-11 09:10). Der Sortierschlüssel mit "datum or leer" (routen.py:491) stellt undatierte Punkte vor alle datierten; die Fahrt steht vor dem Online-Check-in des Vortags. Verletzt AC-5, Randfall, den die Spec nicht ausdrücklich nennt.
- Reproduktion F001: E-01 ankunft "06:00" (Nachtfahrt, ohne Datum). Ergebnis: ankunft (2027-03-12, 06:00) steht vor abfahrt (2027-03-12, 09:10). Der Kalender behandelt dasselbe Paar richtig (Ende <= Beginn ohne Zeitzone liegt am Tag danach, kalender.py:99-100), die Zeitleiste nicht. Mit explizitem Datum (2027-03-13T06:00) stimmt die Reihenfolge. Die Spec sagt "Eine Uhrzeit ohne Datum gilt am Tag der Strecke", also spec-konform, aber inkonsistent zum Kalender.
- Zwei erinnernde Merkmale am selben Ding: je eigener Schlüssel und eigene UID, keine Verschmelzung; Dedupe mit der Buchung nur bei gleichem (Datum, Uhrzeit)-Paar (routen.py:446-449). Akzeptabel.
- Englisch: remind und at im Schema (schnittstelle.py:109,139), departure und arrival als Ziele (schreiben.py:802-805); test_schema_und_englische_namen grün. Die englische Fehlermeldung nennt das Wort bei (texte_en.py:3262): F003.
- Lesen strenger als Schreibweg: bei Abfahrt (Großschreibung) wird beim Lesen abgelehnt, im Schreibweg per lower() angenommen (schreiben.py:799): F004.
- Texte nur im Katalog: neue Schlüssel in beiden Dateien (test_texte, test_neue_texte_in_jeder_sprache grün); "(Muster)" auf der Bausteinseite in vorlage.html ist Demo-Inhalt wie bei vorhandenen Mustern.
- Deploy: kalender.py importiert jetzt routen.py; routen.py importiert nur texte; betrieb/deploy.sh:29 trägt routen.py in RM_MODULE nach (PS_MODULE und SB_MODULE hatten es schon); test_betrieb grün.
**Implementierer:** (nicht beteiligt)

### Runde 3 (nach Behebung F001 bis F004)
**Adversary:** Jede Behebung mit eigener Reproduktion nachgeprüft (Seitendaten-Erzeugung mit abgewandelten Beispielreisen):
- F001 behoben: E-01 abfahrt 22:00, ankunft 06:00 (beide ohne Datum): Ankunft 2027-03-13 06:00, nach der Abfahrt (routen.py:490-493, nacht-Flag). Ankunft mit eigenem Datum (2027-03-12T23:00) bleibt unverändert, kein Folgetag. Abfahrt = Ankunft (09:10 und 09:10): Ankunft am Folgetag; das deckt sich mit kalender._spanne (Ende <= Beginn ohne Zone liegt am Tag danach, kalender.py:99), also konsistent zwischen Seite und Kalender.
- F002 behoben: ohne Plantag und Abfahrt mit Datum (2027-03-12T09:10): Tag der Fahrt aus der Abfahrt (routen.py:477), Reihenfolge Merkmal, Buchung, Abfahrt, Ankunft richtig. Ohne Plantag und ohne Datum an der Abfahrt: datierte Punkte zuerst, undatierte danach (routen.py:499); Nachtankunft ohne Datum zuletzt (an 06:00 nach ab 09:10). Mit datierter Nachtabfahrt und undatierter Ankunft: Ankunft 2027-03-13 06:00 richtig.
- F003 behoben: texte_en.py:3262 nennt "at (bei in arten.yaml)". F004 behoben: routen.py:1641 normalisiert bei per strip().lower().
- Neuer Angriff (F005): Nachtfahrt mit Zwischenpunkt nach Mitternacht. E-01 abfahrt 22:00, ankunft 06:00, Merkmal freischalten "00:30" ohne Datum. Ergebnis: Merkmal 2027-03-12 00:30 steht VOR der Abfahrt 2027-03-12 22:00, obwohl es fachlich in der Nacht dazwischen liegt. Spec-konform (Uhrzeit ohne Datum gilt am Tag der Strecke); mit Datum (2027-03-13T00:30) ist es richtig. Nur Hinweis, kein Blocker.
- Regression: Kalender (kalender.py:204), Wächter (waechter.py:267), Konnektor (konnektor.py:977), Schreibweg (schreiben.py:742), Schnittstelle (schnittstelle.py:139), Texte (texte_de.py:3272) und Vorlage (vorlage.html:2059, 2538) sind seit Runde 2 unverändert; die Beispielreise stadtwochenende bleibt in den Normalfällen wie zuvor.
- Tests: 14 Dateien (13 aus Runde 1 plus Protokolltest ohne Pfade), 718 passed, 0 übersprungen.
**Implementierer:** (nicht beteiligt)

### Runde 4 (Validierung: Test zu AC-13 ergänzt)
**Adversary:** Die Validierung fand AC-13 („Seite und Konnektor show an E-01 zeigen dieselben Zeitpunkte“) ohne Test; ergänzt wurde nur `test_zeige_nennt_die_zeitpunkte_der_zeitleiste`, kein Produktcode. Geprüft:
- Grün: test_zeitleiste_bewegung.py 48 passed.
- Bruchversuch: show an E-01 lautet „ab 09:10, an 11:25“, „Buchung: gebucht (B-01, zeige B-01)“, „Fahrkarte freischalten ab: 2027-03-11T08:00 (erinnert …)“. Der Test liest die Erwartung aus den Seitendaten (zeitleiste mit vier Punktarten) und verlangt den Merkmalwert, „ab <zeit>“ und „an <zeit>“; fehlte einer davon in show, würde er rot. Nicht tautologisch.
- Schwachstelle: die Buchungsprüfung verlangte nur „B-01“, das ohnehin in der Buchungszeile steht. Behoben: der Test verlangt jetzt den Verweis „zeige B-01“.
- ADR-0003: Heimat der Buchung ist die Buchung; show nennt die Buchungs-ab nicht doppelt, sondern verweist (docs/adr/0003-heimat.md:21, :30, :61). Vereinbar.
- Nach der Behebung: test_zeitleiste_bewegung.py und test_protokolle_ohne_pfade.py 51 passed; volle Suite davor 3698 passed, 0 übersprungen.
**Implementierer:** (nicht beteiligt)

## Findings

Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/routen.py:490
  Description: zeitleiste sortiert nach (Datum, Uhrzeit, Rang). Eine Ankunft ohne eigenes Datum, die zeitlich vor der Abfahrt liegt (Nachtfahrt: an 06:00, ab 09:10), bekommt dasselbe Datum wie die Abfahrt und steht dadurch vor der Abfahrt.
  Spec requirement: AC-5 — Zeitleiste in zeitlicher Reihenfolge
  Conflict: Der Kalender (engine/kalender.py:99) legt ein Ende ohne Zeitzone vor dem Beginn auf den Tag danach; die Zeitleiste nicht, Ankunft steht vor Abfahrt. Die Spec (Uhrzeit ohne Datum gilt am Tag der Strecke) deckt das Verhalten, das Ergebnis ist fachlich trotzdem falsch.
  Remediation: Ankunft ohne Datum mit Uhrzeit <= Abfahrt (ohne Zeitzone) auf den Folgetag setzen, wie kalender._spanne; Test mit Nachtfahrt ergänzen.

Finding:
  ID: F002
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/routen.py:491
  Description: Der Sortierschlüssel stellt Punkte ohne Datum vor alle datierten. Hängt die Strecke an keinem Plantag (strecken_tag liefert keinen Tag, routen.py:456-463), haben Abfahrt und Ankunft kein Datum und stehen vor einem Online-Check-in oder einer Buchungs-ab des Vortags.
  Spec requirement: AC-5 — chronologische Reihenfolge
  Conflict: Reproduktion: Beispielreise stadtwochenende, tage.T-01.strecken leer setzen, bauen; Zeitleiste E-01 = abfahrt, ankunft, merkmal freischalten (11.3. 08:00), buchung (11.3. 09:10). Die Fahrt steht vor ihrem Vortags-Check-in.
  Remediation: Undatierte Punkte hinter die datierten einsortieren oder ohne Tag der Strecke keine Zeitleiste bilden (alte Zeile zeigen); Test ergänzen.

Finding:
  ID: F003
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/texte_en.py:3262
  Description: Die englische Fehlermeldung nennt bei statt at als Eigenschaft, obwohl die englische Schnittstelle at heißt.
  Spec requirement: AC-10 — Ablehnung mit Katalogtext (de und en)
  Conflict: Text vorhanden, aber mit dem deutschen Eigenschaftsnamen.
  Remediation: bei im englischen Text durch bei (at) ersetzen.

Finding:
  ID: F004
  Severity: LOW
  Category: edge_case
  Code reference: engine/routen.py:1625
  Description: Beim Lesen der Reise wird bei Abfahrt (Großschreibung) abgelehnt, im Schreibweg (engine/schreiben.py:799) wird lower() angewandt. Nur bei Handbearbeitung der YAML relevant.
  Spec requirement: AC-10
  Conflict: Leichte Inkonsistenz Lesen/Schreiben; die Ablehnung nennt gültige Ziele, kein Datenverlust.
  Remediation: Beim Lesen ebenfalls kleinschreiben oder so lassen.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/routen.py:477
  Description: Ein Zeitpunkt-Merkmal ohne Datum bekommt den Tag der Fahrt. Bei einer Nachtfahrt steht ein Wert wie 00:30 (nach Mitternacht, zwischen Abfahrt und Ankunft) deshalb vor der Abfahrt am Abend.
  Spec requirement: AC-5 — zeitliche Reihenfolge (Spec: Uhrzeit ohne Datum gilt am Tag der Strecke)
  Conflict: Spec-konform; fachlich nur mit Datum am Wert korrekt. Kein Blocker.
  Remediation: Hinweis in der Doku (Zeitpunkte nach Mitternacht mit Datum eintragen) oder Zeit vor der Abfahrt bei Nachtfahrt auf den Folgetag legen.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/routen.py:361
  Evidence: Zeitpunkt ohne Rolle bleibt Merkmal (rest[k] = v), ungültiger Wert meldet lage_wert; uhrzeit ohne Rolle weiter Fehler (lage_rolle, engine/texte_de.py:3355); Tests 1-3 grün, eigener Lauf mit 25:99 bricht ab.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/schreiben.py:742
  Evidence: erinnern und remind im Schreibweg gespeichert (schreiben.py:795,825-830), nur an Typ zeitpunkt (Katalogtext); sichtbar in attributes und show über engine/konnektor.py:977 und engine/konnektor.py:991; Lesen routen.py:1621, DEF_FELDER routen.py:601; en-Alias engine/schnittstelle.py:109; Katalog en engine/texte_en.py:3276.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/waechter.py:267
  Evidence: genau eine Erinnerung je erinnerndem Zeitpunkt mit Datum, nur Status fest, Schlüssel zeit:..., Meldeweg empfaenger(d, None) wie buchungsfristen; Kalender engine/kalender.py:204 ein Termin, UID Ding-zeit-Merkmal; ohne Datum übersprungen (routen.py:448). Tests 5, 6, 8 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/routen.py:446
  Evidence: Menge der (Datum, Uhrzeit)-Paare der Buchungs-ab des Dings; gleicher Zeitpunkt, nur die Buchung (Wächter und Kalender nutzen dieselbe Funktion). Test 7 grün; verschiedene Zeiten melden beide.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/routen.py:466
  Evidence: Reihenfolge im Normalfall richtig (beide Beispielstrecken, anderer Tag, nach Ankunft, gleiche Zeit); F001 und F002 in Runde 3 als behoben nachgeprüft (engine/routen.py:466-501, Sortierschlüssel routen.py:499).
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/vorlage.html:2025
  Evidence: gemeinsame Atome; ol.zeit mit Schriftgröße t-text, Kopfzeile gleiche Größe; Abfahrt und Ankunft nur fetter Name und voller Punkt. Browser-Test misst eine Größe (chromium und webkit, beide Strecken, zwei Breiten), grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/vorlage.html:2059
  Evidence: zeitleiste-kopf nur mit Datum der Fahrt (fahrtTag), sonst entfällt; abweichendes Datum als tag unter der Uhrzeit (leistenZeit). Browser-Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/vorlage.html:2538
  Evidence: buchungBlock mit ohneAb unterdrückt die ab-Zeile nur mit Zeitleiste; Merkmalliste filtert inLeiste; Unterkunft behält die ab-Zeile (Browser-Gegenprobe grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/routen.py:468
  Evidence: zeitleiste liefert leer ohne Punkt außer Abfahrt und Ankunft; die Vorlage fällt auf die alte Kopfzeile zurück; test_ohne_weitere_zeitpunkte_keine_zeitleiste und Browser-Gegenprobe grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/routen.py:400
  Evidence: bei_ziele, Prüfung in definitionen (routen.py:1621-1643) und zeit_eigenschaften_pruefen (engine/schreiben.py:742) mit Katalogtexten de und en (engine/texte_de.py:3263, engine/texte_en.py:3262); at über engine/schnittstelle.py:139; Anzeige engine/konnektor.py:977. Eigene Läufe: unbekanntes Ziel, Selbstbezug, leer, Typ zeitpunkt: alle abgelehnt.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/vorlage.html:2043
  Evidence: zeitleisteMerkmale zählt bei-Merkmale mit Wert und Sichtbarkeit (nach_buchung gebucht); fehlt Punkt oder Zeitleiste, bleibt das Merkmal in der Liste (test_bei_ohne_punkt_bleibt_in_der_merkmalliste); Browsertest nach Buchung grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/vorlage.html:2025
  Evidence: leistenPunkt, leistenZeit, leistenMarke, leistenZusatz und zeitLeiste im Kopfkommentar, Stilen, Bausteinseite und docs/design.md; halteLeiste nutzt dieselben Atome; test_design und Halteleiste-Vorher/Nachher grün in chromium und webkit.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: betrieb/deploy.sh:29
  Evidence: routen.py in RM_MODULE nachgetragen, weil kalender.py es lädt (test_betrieb grün). Stadtwochenende trägt die Beispielwerte, Wanderung unverändert; test_kein_formatwechsel (nachziehen ändert nichts) und test_beispielreise_stadtwochenende_traegt_die_neuen_merkmale grün; Seite und show an E-01 gleiche Zeitpunkte (Test 11).
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/tests/test_zeitleiste_bewegung.py:596
  Evidence: Eigener Lauf der 13 relevanten Dateien: 711 passed, 0 übersprungen, einschließlich test_texte, test_design, Halteleiste-Gegenprobe, Browsertests und Protokolltest ohne Pfade (im ersten Lauf, 348 passed). Die volle Suite (3668 passed laut test-green-output.txt) nicht wiederholt.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/kalender.py:204
  Evidence: Schleife über routen.erinnernde_zeitpunkte erzeugt je erinnerndem Zeitpunkt mit Datum genau einen Termin mit UID Ding-zeit-Merkmal; in Runde 1 und 3 mit dem Kalender-Test und dem Nachtfahrt-Vergleich (kalender.py:99) geprüft.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/konnektor.py:977
  Evidence: zeit_eigenschaften hängt erinnert und steht bei an die Zeilen von attributes und show; test_merkmale_zeigt_erinnern_und_bei grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/schnittstelle.py:139
  Evidence: Für merkmal_definieren heißt bei auf englisch at (an bleibt an), erinnern heißt remind (schnittstelle.py:109); test_schema_und_englische_namen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/texte_de.py:3263
  Evidence: Katalogtext der Ablehnung eines unbekannten bei-Ziels in Deutsch (Gegenstück texte_en.py:3262); weitere neue Texte bei texte_de.py:3272; test_texte grün.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Behebungen F001 bis F004 halten stand (Runde 3, eigene Reproduktionen); der Test zu AC-13 trägt (Runde 4).
Tests: volle Suite 3698 passed, 0 failed, 0 übersprungen (-n 3); nach dem Schärfen des Tests 51 passed (gezielt)
Edge cases: alle geprüft; offen nur F005 (LOW, spec-konform, Hinweis)
Regressions: None found
Checklist: 14/14 points proven

## Geprüfte Dateien

- sha256:0b03c6b4d6495bc32ed43add28dabc5b8e30a7523af21187656d4d2bfb6120f9  betrieb/deploy.sh
- sha256:d8cc01967e8258d32b29aacb9869465c0746b7642a3ac9f685fbe31f6a78027a  engine/kalender.py
- sha256:f53117849e17e657a31e9abcd9631b522f1bba78b8aca28f3b5fdfcd9e72bdd6  engine/konnektor.py
- sha256:7b1ef936fc97c0e68d195ad5256d2d1d7306c7bfd138ac181d548ef2a029b730  engine/routen.py
- sha256:31970afc3aac632859ff451cc7151b32702f57066b8c0d69eb89626cd6c48fdc  engine/schnittstelle.py
- sha256:130fa843bc6c7b033162a7695bdab66ca05583b455899ec74810fca5b0cb3828  engine/schreiben.py
- sha256:4bc411b02d5a4344d7e26bc5349f2476c36c53c48532245384ed82fa116ee78a  engine/tests/test_zeitleiste_bewegung.py
- sha256:cde36c417590430bae55ac57a492e8b372368362eae65927785eed85c93599e7  engine/texte_de.py
- sha256:88bc95234e43e43120aec48166d25274f26b017f42eedc6aec91a3fc399452b9  engine/texte_en.py
- sha256:415ee70f8e270d34d20bef6089fae80ddf7bd8fbd67c210f544aa1e8332d8ae5  engine/vorlage.html
- sha256:4337801c3e808eb445b788c8cea5bb2eea65fa367f00e667e656783af52755f2  engine/waechter.py

## Prüfbasis

- base: fe7b1eaf3b5ffe8d8fab6d23f6ae5c894f9ab754
- blob:94b55d431c9e4aa3d8cf91ad23926c3668347d1c  betrieb/deploy.sh
- blob:1a9e965eecd651e84b2af6b3c9d36e9f67cd1a0d  engine/kalender.py
- blob:80af9ad85c4d8a9c71d131ca26b381971b38a50f  engine/konnektor.py
- blob:2c0f2a51b338ec2384e6ff66f800140718c4d277  engine/routen.py
- blob:489112ca09c13d075cb9fb9ec31fbcae115ea8ac  engine/schnittstelle.py
- blob:cace521c8f0e38593518e380c1854c7597cae1d2  engine/schreiben.py
- blob:1c37faf78f9a90e9b69f04f0e2d6ee3f9ff77ca1  engine/tests/test_zeitleiste_bewegung.py
- blob:3f4615e46b7e1c6bff7517c2a451a46d026c7285  engine/texte_de.py
- blob:fa6a830f94558a3db3a85e27d2067b62c0cfd74b  engine/texte_en.py
- blob:9be6ced153f03f5805ecba228d95c1978c40b4fb  engine/vorlage.html
- blob:9c16af42fe76ef9ecaa9089ed0399976aeefdc15  engine/waechter.py

## Geprüfte Dateien

- sha256:0b03c6b4d6495bc32ed43add28dabc5b8e30a7523af21187656d4d2bfb6120f9  betrieb/deploy.sh
- sha256:d8cc01967e8258d32b29aacb9869465c0746b7642a3ac9f685fbe31f6a78027a  engine/kalender.py
- sha256:f53117849e17e657a31e9abcd9631b522f1bba78b8aca28f3b5fdfcd9e72bdd6  engine/konnektor.py
- sha256:7b1ef936fc97c0e68d195ad5256d2d1d7306c7bfd138ac181d548ef2a029b730  engine/routen.py
- sha256:31970afc3aac632859ff451cc7151b32702f57066b8c0d69eb89626cd6c48fdc  engine/schnittstelle.py
- sha256:130fa843bc6c7b033162a7695bdab66ca05583b455899ec74810fca5b0cb3828  engine/schreiben.py
- sha256:2a63327a40d255dda64710b14229dbaad5e7fe137db1469e81541dc0458faae5  engine/tests/test_zeitleiste_bewegung.py
- sha256:cde36c417590430bae55ac57a492e8b372368362eae65927785eed85c93599e7  engine/texte_de.py
- sha256:88bc95234e43e43120aec48166d25274f26b017f42eedc6aec91a3fc399452b9  engine/texte_en.py
- sha256:415ee70f8e270d34d20bef6089fae80ddf7bd8fbd67c210f544aa1e8332d8ae5  engine/vorlage.html
- sha256:4337801c3e808eb445b788c8cea5bb2eea65fa367f00e667e656783af52755f2  engine/waechter.py

## Prüfbasis

- base: fe7b1eaf3b5ffe8d8fab6d23f6ae5c894f9ab754
- blob:94b55d431c9e4aa3d8cf91ad23926c3668347d1c  betrieb/deploy.sh
- blob:1a9e965eecd651e84b2af6b3c9d36e9f67cd1a0d  engine/kalender.py
- blob:80af9ad85c4d8a9c71d131ca26b381971b38a50f  engine/konnektor.py
- blob:2c0f2a51b338ec2384e6ff66f800140718c4d277  engine/routen.py
- blob:489112ca09c13d075cb9fb9ec31fbcae115ea8ac  engine/schnittstelle.py
- blob:cace521c8f0e38593518e380c1854c7597cae1d2  engine/schreiben.py
- blob:c85d23c95ed35b851cf481118f010a711f252e33  engine/tests/test_zeitleiste_bewegung.py
- blob:3f4615e46b7e1c6bff7517c2a451a46d026c7285  engine/texte_de.py
- blob:fa6a830f94558a3db3a85e27d2067b62c0cfd74b  engine/texte_en.py
- blob:9be6ced153f03f5805ecba228d95c1978c40b4fb  engine/vorlage.html
- blob:9c16af42fe76ef9ecaa9089ed0399976aeefdc15  engine/waechter.py
