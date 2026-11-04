# Adversary Dialog — altformen-267-b
Spec: docs/specs/betrieb/altformen-entfernen-267.md
Datum: 2026-11-03 16:36

## Checkliste
- [x] **AC-1 (a):** Fehlt `reise.yaml`, bricht der Bau mit einem `BauFehler` ab, dessen Text aus dem Katalog kommt (de und en vorhanden); `Reise.alt` und alle Zweige darauf sind aus dem Quelltext verschwunden (Suche nach `.alt` in `engine/reise.py` ohne Treffer). — NICHT TEIL DIESES PR (PR a, bereits vorgespult), hier nicht bewiesen
- [x] **AC-2 (a):** Beide Beispielreisen (`beispielreise`, `stadtwochenende`) und alle echten Reisen bauen unverändert; ihre gebauten Seiten sind vor und nach PR a gleich. — NICHT TEIL DIESES PR (PR a), hier nicht bewiesen
- [x] **AC-3 (b):** `neu.py nachziehen` trägt in jeder `reise.yaml`, in der `sprache` fehlt oder leer ist, das Feld `sprache: de` ein und meldet es mit einer Zeile in der Sprache der Reise; in `reise.yaml` mit gültigem Feld ändert sich nichts, auch nicht in Kommentaren oder Reihenfolge.
- [x] **AC-4 (b):** Ein zweiter Lauf von `nachziehen` direkt danach liefert keine Meldung und ändert keine Datei der Reise (Vergleich aller Dateien vor und nach dem Lauf).
- [x] **AC-5 (b, manueller Nachweis am Reisen-Repo):** Der Lauf „Software nachziehen“ stellt die vier Reisen ohne `sprache` ohne Handschritt um; die Meldungen stehen im Commit des Bots (Verlauf, ADR-0001 Frage 7). — MANUELL AUSSTEHEND (Nachweis nach dem Vorspulen im PR-Text), hier nicht bewiesen
- [x] **AC-6 (c, manueller Nachweis im PR-Text):** Die Abnahmebedingung b → c ist erfüllt und im PR-Text belegt (Commit des Bots, Ausgabe der lesenden Prüfung, grüner Bau aller Reisen mit dem Branch), bevor PR c vorgespult wird. — MANUELL AUSSTEHEND (Nachweis nach dem Vorspulen im PR-Text), hier nicht bewiesen
- [x] **AC-7 (c):** `texte.BESTAND_REISE` kommt im Quelltext von `engine/` nicht mehr vor; eine `reise.yaml` ohne `sprache` bricht den Bau mit dem Katalogtext `pruefung.reise.sprache_fehlt`. — NICHT TEIL DIESES PR (PR c), hier nicht bewiesen
- [x] **AC-8 (c):** `routen.STUFEN_WORTE` ist gelöscht; `stufe_satz` und `stufe_schluessel` liefern in Deutsch und Englisch dieselben Ergebnisse wie vorher. — NICHT TEIL DIESES PR (PR c), hier nicht bewiesen
- [x] **AC-9 (c):** Meldungstexte, Seiten und Dateien beider Beispielreisen sind vor und nach PR c in beiden Sprachen (de, en und der Pseudo-Sprache der Tests) gleich; die Ausnahmelisten in `test_texte.py` sind nicht länger geworden. — NICHT TEIL DIESES PR (PR c), hier nicht bewiesen
- [x] **AC-10 (d):** Der Bau liest `typ` nicht mehr als Ersatz für `art`; `nachziehen` stellt `typ` weiterhin um; die Datentypen der Merkmale (`typ: text|geld|…`) sind unberührt. — NICHT TEIL DIESES PR (PR d), hier nicht bewiesen
- [x] **AC-11 (d):** Der Einzelwert-Pfad in `schreiben.py` Z. 1003–1004 bleibt als Lesetoleranz erhalten; kein Merkmalswert einer Reise wird dadurch verändert. — NICHT TEIL DIESES PR (PR d), hier nicht bewiesen
- [x] **AC-12 (alle):** Jede Änderung am Format bringt ihre Umstellung in `neu.py nachziehen` mit, mit Test (CLAUDE.md, #250); der Nachweis, dass in keiner Reise und keiner Instanz ein Handschritt nötig war, ist manuell: der Commit des Bots und die lesende Prüfung aus der Abnahmebedingung stehen im PR-Text.
- [x] **AC-13 (alle):** Vor dem Vorspulen jedes PR laufen die Tests der einbindenden Instanzen mit dem Branch; rot darf dort nur sein, was auf `main` ohne den Branch schon rot ist (Vergleichslauf der Instanz auf `main` zuerst, Ergebnis im PR-Text). — MANUELL AUSSTEHEND (Nachweis nach dem Vorspulen im PR-Text), hier nicht bewiesen

## Dialog

### Runde 1
**Adversary:** F001-Fix unabhängig angegriffen (Skript im Scratchpad, nur Bytes-Vergleiche, Kopien/Temp-Ordner, keine echten Reisen). Eingaben: CRLF mit fehlendem Feld, leerem Feld, leerem Feld mit Kommentar, ohne Zeilenende am Ende (CRLF und LF), gemischte Zeilenenden in beiden Mischungen, BOM+CRLF, Umlaute und Emoji in Titel und Kommentar, mehrzeiliger Vorgängerwert, einsames CR, sprache: null und '', U+2028 und NEL im Titel, gültiges Feld, Leerzeilen am Dateiende. Jeweils: Probelauf ändert nichts, Schreiblauf, zweiter Lauf, Parsen mit sprache=de.
**Implementierer:** (Prüfer-Ergebnis) Alle Fälle: Probelauf byte-gleich, Ergebnis gültiges YAML mit sprache=de, zweiter Lauf byte-gleich und ohne Meldung. Genau eine Zeile kommt hinzu bzw. wird ersetzt, mit dem Zeilenende der Nachbarzeile oder der Datei: CRLF-Datei ohne Zeilenende am Ende bekommt CRLF, Kommentar hinter leerem Feld bleibt, Umlaute/Emoji/BOM byte-erhalten. Gemischte Zeilenenden: die neue Zeile bekommt CRLF, sobald die Datei irgendwo CRLF hat (mixed2: neue Zeile CRLF zwischen LF-Zeilen); die übrigen Zeilen bleiben unberührt. U+2028/NEL: ruamel und splitlines zählen gleich, kein Versatz. Gültiges Feld (sprache: en, CRLF): unberührt, keine Meldung. Einziger Schönheitsfehler: Datei mit nur einsamem CR bekommt am Ende CRLF/LF-Mix; kein Format, das vorkommt.

### Runde 2
**Adversary:** Ganze Umstellung an Kopien beider Beispielreisen, LF und CRLF (ohne Feld sprache): Probelauf `nachziehen(schreiben=False)` schreibt nichts; echter Lauf ändert in reise.yaml nur die Zeile `sprache: de` (in der CRLF-Variante mit CRLF, kein nacktes LF in der Datei), meldet eine Zeile mit Katalogtext; zweiter Lauf: keine Meldung, SHA-256 aller Dateien der Reise vor und nach gleich (AC-4); Bau (bauen.bauen) beider Kopien danach erfolgreich. Echte reise.yaml lesend geprüft: keine Zeile beginnt mit `{` (grep, Treffer 0), keine enthält CR, vier ohne sprache (werden von der Umstellung erfasst). Tests: 105 passed (test_umstellung_267.py, test_texte.py).
**Implementierer:** (Prüfer-Ergebnis) Keine Abweichung gefunden. Bekannte Grenzen, bewusst nicht behoben: F002 Flow-Style-Wurzel (`{titel: x}`): Einfügen einer Block-Zeile erzeugt ungültiges YAML; kommt in keiner echten reise.yaml vor (grep), `neu.py anlegen` schreibt Block-Stil; das Eintragen hinter einer Flow-Wurzel würde zudem vom Bau schon vorher als ungültig bemerkt werden. F003 leere/Kommentar-Datei oder Liste als Wurzel: `isinstance(roh, dict)` schlägt fehl, Datei bleibt unberührt, keine Meldung; der Bau lehnt solche Dateien ab (AC-7 in PR c, bis dahin Verhalten wie vor PR b), kein Datenverlust.

## Findings

Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/neu.py:650
  Description: Aus Durchgang 1 (CRLF ging verloren). Jetzt: Bytes lesen, Zeilenende erkennen (`nl`), neue Zeile mit passendem Ende. Status: BEHOBEN und in Durchgang 2 unabhängig bestätigt (15 Sonderfälle plus Beispielreisen, siehe Runde 1 und 2).
  Spec requirement: AC-3 — nichts außer dem Feld ändert sich
  Conflict: keiner mehr
  Remediation: keine

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:670
  Description: Flow-Style-Wurzel (`{...}`) würde eine Block-Zeile einfügen und ungültiges YAML erzeugen. Bekannte Grenze, bewusst nicht behoben; keine echte reise.yaml hat eine Zeile mit `{` am Anfang (grep, 6 Dateien), `anlegen` schreibt Block-Stil.
  Spec requirement: AC-3
  Conflict: nur bei handgeschriebenem Flow-Stil
  Remediation: optional Meldung statt Eintrag

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:650
  Description: Leere Datei, nur Kommentar oder Liste als Wurzel: `not isinstance(roh, dict)` gibt [] zurück, Datei bleibt unberührt, keine Meldung. Bekannte Grenze; der Bau lehnt solche Dateien ab.
  Spec requirement: AC-3
  Conflict: keine Meldung, aber auch kein Schaden
  Remediation: keine

## Confirmations

Confirmation:
  AC: AC-3
  Code reference: engine/neu.py:640
  Evidence: sprache_nachziehen trägt bei fehlendem/leerem/null Feld genau eine Zeile `sprache: de` ein, meldet sie, lässt gültige Felder byte-gleich (Probe valid, quoted, en, xx).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:2957
  Evidence: Katalogtext inhalt.nachziehen.sprache_eingetragen (de) vorhanden und von der Meldung genutzt.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_en.py:2957
  Evidence: Katalogtext in en vorhanden; test_texte.py grün (Ausnahmelisten nicht länger).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_umstellung_267.py:101
  Evidence: Test zweiter Lauf; zusätzlich eigener Lauf: SHA-256 aller Dateien beider Beispielreise-Kopien (LF und CRLF) nach Lauf 1 und 2 gleich, 2. Meldungsliste leer.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/tests/test_umstellung_267.py:222
  Evidence: Umstellung in nachziehen (neu.py:556) mit Tests (105 passed). Handschritt-Nachweis in Reisen/Instanzen ist manuell nach dem Vorspulen (AC-5/6/13 ebenso), kein Defekt.
  Status: CONFIRMED

Nicht in diesem PR zu prüfen: AC-1, AC-2, AC-7 bis AC-11 (andere PRs); AC-5, AC-6, AC-13 manuell nach dem Vorspulen.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

Zusatz (manuell): Feld `sprache` in reise.yaml. Produktions-Schreibstelle: nur `sprache_nachziehen`. Bedingung davor: Wurzel ist ein Mapping und `sprache` fehlt, ist null oder ist ein leerer String. Test für diesen Weg: `test_fehlende_oder_leere_sprache_wird_eingetragen`, `test_crlf_bleibt_erhalten`, `test_kopie_ohne_sprache_wird_umgestellt_und_baut_danach` (engine/tests/test_umstellung_267.py).

## Verdict

VERDICT: VERIFIED
Tests: 105 passed, 0 failed, 0 übersprungen (test_umstellung_267.py, test_texte.py; volle Suite lief separat)
Edge cases: F001 behoben und bestätigt; F002/F003 LOW, bekannte Grenzen mit Begründung
Regressions: keine
Checklist: AC-3, AC-4, AC-12 bewiesen (soweit PR b); übrige ACs gehören anderen PRs oder sind manuell

## Geprüfte Dateien

- sha256:50e5db2e66d76873026aa0a17b409267b9c35cdb6dd3ff7bc3ad63e5bc504d18  engine/neu.py
- sha256:d498a4acf581fa9153363905dcbad7aadb5bcd30be6874714c3c9b894a0809df  engine/tests/test_umstellung_267.py
- sha256:13079ae96a0ad9d4861912f2a1bcce852614e1f788466f2eea803d6d11a00c2e  engine/texte_de.py
- sha256:0a5f4e51780d6033d14660a0f407b43a7ded9a8c23104f964513f83be972d8b4  engine/texte_en.py

## Prüfbasis

- base: 61bb7c039bee2339f7db4b400d5eaa642baceb11
- blob:949e0f132b5f9fb5b65a7eeb5ff7e6d4149a487e  engine/neu.py
- blob:7476755308813ae0de873a6f91f0a09aae9c0eff  engine/tests/test_umstellung_267.py
- blob:5e63c236aef5097946accc34a1bace2c79006049  engine/texte_de.py
- blob:823b8f6da527ea194fa4e66c98ca51532fecbeaf  engine/texte_en.py
