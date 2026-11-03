# Adversary Dialog — altformen-267-b
Spec: docs/specs/betrieb/altformen-entfernen-267.md
Datum: 2026-11-03 16:30

## Checkliste
- [ ] **AC-1 (a):** Fehlt `reise.yaml`, bricht der Bau mit einem `BauFehler` ab, dessen Text aus dem Katalog kommt (de und en vorhanden); `Reise.alt` und alle Zweige darauf sind aus dem Quelltext verschwunden (Suche nach `.alt` in `engine/reise.py` ohne Treffer).
- [ ] **AC-2 (a):** Beide Beispielreisen (`beispielreise`, `stadtwochenende`) und alle echten Reisen bauen unverändert; ihre gebauten Seiten sind vor und nach PR a gleich.
- [x] **AC-3 (b):** `neu.py nachziehen` trägt in jeder `reise.yaml`, in der `sprache` fehlt oder leer ist, das Feld `sprache: de` ein und meldet es mit einer Zeile in der Sprache der Reise; in `reise.yaml` mit gültigem Feld ändert sich nichts, auch nicht in Kommentaren oder Reihenfolge.
- [x] **AC-4 (b):** Ein zweiter Lauf von `nachziehen` direkt danach liefert keine Meldung und ändert keine Datei der Reise (Vergleich aller Dateien vor und nach dem Lauf).
- [ ] **AC-5 (b, manueller Nachweis am Reisen-Repo):** Der Lauf „Software nachziehen“ stellt die vier Reisen ohne `sprache` ohne Handschritt um; die Meldungen stehen im Commit des Bots (Verlauf, ADR-0001 Frage 7).
- [ ] **AC-6 (c, manueller Nachweis im PR-Text):** Die Abnahmebedingung b → c ist erfüllt und im PR-Text belegt (Commit des Bots, Ausgabe der lesenden Prüfung, grüner Bau aller Reisen mit dem Branch), bevor PR c vorgespult wird.
- [ ] **AC-7 (c):** `texte.BESTAND_REISE` kommt im Quelltext von `engine/` nicht mehr vor; eine `reise.yaml` ohne `sprache` bricht den Bau mit dem Katalogtext `pruefung.reise.sprache_fehlt`.
- [ ] **AC-8 (c):** `routen.STUFEN_WORTE` ist gelöscht; `stufe_satz` und `stufe_schluessel` liefern in Deutsch und Englisch dieselben Ergebnisse wie vorher.
- [ ] **AC-9 (c):** Meldungstexte, Seiten und Dateien beider Beispielreisen sind vor und nach PR c in beiden Sprachen (de, en und der Pseudo-Sprache der Tests) gleich; die Ausnahmelisten in `test_texte.py` sind nicht länger geworden.
- [ ] **AC-10 (d):** Der Bau liest `typ` nicht mehr als Ersatz für `art`; `nachziehen` stellt `typ` weiterhin um; die Datentypen der Merkmale (`typ: text|geld|…`) sind unberührt.
- [ ] **AC-11 (d):** Der Einzelwert-Pfad in `schreiben.py` Z. 1003–1004 bleibt als Lesetoleranz erhalten; kein Merkmalswert einer Reise wird dadurch verändert.
- [ ] **AC-12 (alle):** Jede Änderung am Format bringt ihre Umstellung in `neu.py nachziehen` mit, mit Test (CLAUDE.md, #250); der Nachweis, dass in keiner Reise und keiner Instanz ein Handschritt nötig war, ist manuell: der Commit des Bots und die lesende Prüfung aus der Abnahmebedingung stehen im PR-Text.
- [ ] **AC-13 (alle):** Vor dem Vorspulen jedes PR laufen die Tests der einbindenden Instanzen mit dem Branch; rot darf dort nur sein, was auf `main` ohne den Branch schon rot ist (Vergleichslauf der Instanz auf `main` zuerst, Ergebnis im PR-Text).

## Dialog

Umfang: nur PR b (AC-3, AC-4, AC-12 soweit Test/Umstellung). Nicht Teil dieses PR: AC-1, AC-2, AC-7 bis AC-11 (PR a, c, d). Manuell, ausstehend (nach dem Vorspulen): AC-5, AC-6, AC-13 und der Bot-Nachweis aus AC-12. Das sind keine Defekte.

### Runde 1
**Adversary:** Probeläufe auf Kopien beider Beispielreisen im Scratchpad (Skripte p2.py, p3.py dort; nie echte Reisen). Je Fall: Probelauf (schreiben=False), Lauf 1, Lauf 2, SHA-256 aller Dateien, Gültigkeit des Ergebnisses als YAML, Bau danach.

Ergebnis (beispielreise, 27 Fälle plus stadtwochenende):
- sprache fehlt / leer (`sprache:`) / `null` / `~` / `"  "`: Lauf 1 trägt `sprache: de` ein, Ergebnis ist gültiges YAML mit sprache=de. Probelauf meldet, schreibt aber nichts (Hashes gleich). Lauf 2 liefert 0 Meldungen und ändert keine Datei.
- `sprache: en  # x`, `xx`, `"de"`: reise.yaml bleibt byte-gleich, keine Meldung zur Sprache (unbekannter Wert bleibt dem Bau überlassen, wie im Docstring).
- Leer mit Kommentar dahinter: Kommentar bleibt (`sprache: de   # hallo`, `sprache: ""  # c` wird `sprache: de # c`).
- `sprache:` nur verschachtelt (unter status oder einstellungen): zählt nicht als Top-Level, `sprache: de` kommt zusätzlich nach oben, die verschachtelte Zeile bleibt.
- Datei ohne pfad, nur titel, ohne abschließenden Zeilenumbruch, mehrzeiliger Wert des Vorgängers (`pfad: >`, `ziel: >-` am Dateiende), ohne Vorgänger (erster Schlüssel nach dem Kopfkommentar), `---`-Marker, BOM: alle gültiges YAML mit sprache=de, Zeile an der erwarteten Stelle. Ein Kommentar vor dem nächsten Schlüssel bleibt bei diesem.
- Leere Datei, nur Kommentar, Liste als Wurzel: unberührt, keine Meldung (F003).
- beispielreise und stadtwochenende ohne sprache: Lauf 1 stellt um, Lauf 2 stabil, `bauen.py` baut beide danach fehlerfrei. stadtwochenende mit gültigem Feld: 0 Meldungen, 0 geänderte Dateien.
- Hinweis: In beispielreise ändert sich in jedem Fall (auch mit gültigem sprache) zusätzlich `plan/arten.yaml` mit einer weiteren Meldung. Das ist ein anderer Schritt von nachziehen (Altform der Beispielreise), nicht PR b; Lauf 2 ist stabil.
- Katalog: `inhalt.nachziehen.sprache_eingetragen` in de und en vorhanden; `BESTAND_REISE` in `engine/texte.py:18` unverändert (Datei nicht im Diff). Tests test_umstellung_267.py und test_texte.py: 103 passed.

Gefunden: F001 (CRLF wird zu LF), F002 (Flow-Style-Wurzel liefert kaputtes YAML).
**Implementierer:** nicht anwesend. Die Textschnitt-Methode beschädigt in den realistischen Fällen keine Datei.

### Runde 2
**Adversary:** Gezielt auf Schwachstellen der Textschnitt-Methode.
- Zeilenenden: `read_text` übersetzt CRLF in LF, `write_text` schreibt LF. Beleg: Kopie mit CRLF und fehlendem Feld, nach Lauf 1 CRLF-Zahl 0, LF-Zahl 29. Die Aussage „nur diese eine Zeile ändert sich“ stimmt dann nicht, der Versionsvergleich zeigt die ganze Datei geändert. Das Ergebnis bleibt gültiges YAML, der Bau läuft. Kein Test deckt CRLF ab (F001, MEDIUM).
- Flow-Style-Wurzel (`{titel: X, pfad: x}`): Meldung kommt, die Datei wird zu `{...}` plus Zeile `sprache: de`, beim nächsten Laden ParserError. Reale reise.yaml sind Block-Style (anlegen schreibt so), daher LOW (F002).
- Tab nach dem Doppelpunkt (`sprache:` Tab Kommentar): ScannerError aus ruamel beim Laden, die Datei war schon vorher ungültig und bleibt unberührt.
- Zweiter Lauf nach jedem Eintrag: 0 Meldungen, alle Hashes gleich (AC-4 belegt, Test `test_zweiter_lauf_aendert_nichts`).
- Zahl (`sprache: 5`) und Liste: unberührt, der Bau prüft den Wert.
- Reihenfolge: `sprache_nachziehen` läuft als erster Schritt (engine/neu.py:556) vor den Schritten, die die Sprache der Reise lesen; die beiden Reihenfolge-Tests bestehen. Die Meldung kommt über `texte.t("de", ...)`, korrekt, weil die Reise ohne Feld bisher deutsch galt.
- AC-12: Umstellung und Tests liegen im PR; der Bot-Nachweis ist manuell ausstehend.

Bewertung: AC-3 und AC-4 für alle realistischen Eingaben bewiesen. Offen: zwei Randfälle (CRLF, Flow-Wurzel) und ein Wortlaut-Rand (leere Datei).
**Implementierer:** nicht anwesend.

### Findings

Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/neu.py:648
  Description: `text = y.read_text(encoding="utf-8")` liest mit Universal-Newlines, `y.write_text(...)` (Zeile 678) schreibt LF. Eine reise.yaml mit CRLF verliert alle Zeilenenden (Probe: vorher alle CRLF, nachher 0 CRLF, 29 LF).
  Spec requirement: AC-3 — nur die eine Zeile ändert sich, Form der Datei bleibt
  Conflict: Bei CRLF-Dateien ändert sich die ganze Datei. Der Code behandelt CRLF an anderer Stelle (`rstrip("\r\n")`), erreicht den Fall aber nie, weil der Text schon übersetzt ist.
  Remediation: Mit read_bytes/decode und write_bytes oder `newline=""` arbeiten, die neue Zeile mit dem erkannten Zeilenende einfügen, Test mit CRLF-Datei.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:676
  Description: Bei Flow-Style-Wurzel wird `sprache: de` als neue Zeile hinter die Zeile gesetzt, die Datei ist danach ungültiges YAML.
  Spec requirement: AC-3 — Ergebnis muss gültiges YAML mit sprache=de sein
  Conflict: Der Code prüft nicht, ob die Wurzel Block-Style ist. Praxisrelevanz gering.
  Remediation: Vor dem Schnitt auf Flow-Style der Wurzel prüfen und dann nichts schreiben oder über ruamel dumpen.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:650
  Description: Leere Datei oder reine Kommentardatei (roh ist kein dict) wird ohne Meldung übergangen.
  Spec requirement: AC-3 — „in jeder reise.yaml, in der sprache fehlt oder leer ist“
  Conflict: Wortlaut weiter als das Verhalten; der Bau lehnt eine solche Datei ohnehin ab.
  Remediation: Im Spec auf „Datei mit Zuordnung“ eingrenzen oder `sprache: de` anhängen.

### Confirmations

Confirmation:
  AC: AC-3
  Code reference: engine/neu.py:640
  Evidence: sprache_nachziehen trägt bei fehlendem oder leerem Feld `sprache: de` ein und meldet mit Katalogtext; gültige Werte bleiben byte-gleich. Randfälle F001 bis F003.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/neu.py:556
  Evidence: Zweiter Lauf in allen Probefällen: 0 Meldungen, SHA-256 aller Dateien gleich; Probelauf schreibt nichts.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/texte_de.py:2957
  Evidence: Katalogeintrag de vorhanden, Umstellung in nachziehen, Tests in engine/tests/test_umstellung_267.py (103 passed mit test_texte.py). Bot-Nachweis manuell, ausstehend.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/texte_en.py:2957
  Evidence: Katalogeintrag en parallel zu de; Ausnahmelisten von test_texte.py grün.
  Status: CONFIRMED

Nicht Teil dieses PR: AC-1, AC-2, AC-7, AC-8, AC-9, AC-10, AC-11. Manuell, ausstehend: AC-5, AC-6, AC-13.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: AMBIGUOUS

AC-3 und AC-4 sind für alle realistischen Eingaben bewiesen, keine Datei wird beschädigt, Bau danach grün. F001 (CRLF-Dateien verlieren ihre Zeilenenden) bricht die Zusage „nur eine Zeile ändert sich“ und sollte vor dem Vorspulen behoben oder bewusst akzeptiert werden (Reisen sind in der Praxis LF). F002 und F003 sind LOW. Entscheidung: F001 beheben oder akzeptieren.
Tests: 103 passed (Teilmenge), volle Suite 1164 grün laut Beleg, 0 failed, 0 übersprungen

## Geprüfte Dateien

- sha256:36d202a7b3327bc7fc252aa7cfc362590db8109ea41734511f2c04d07e9cd66f  engine/neu.py
- sha256:13079ae96a0ad9d4861912f2a1bcce852614e1f788466f2eea803d6d11a00c2e  engine/texte_de.py
- sha256:0a5f4e51780d6033d14660a0f407b43a7ded9a8c23104f964513f83be972d8b4  engine/texte_en.py

## Prüfbasis

- base: 61bb7c039bee2339f7db4b400d5eaa642baceb11
- blob:07ca2807894b59f1c62285d34fab52f1771dbc40  engine/neu.py
- blob:5e63c236aef5097946accc34a1bace2c79006049  engine/texte_de.py
- blob:823b8f6da527ea194fa4e66c98ca51532fecbeaf  engine/texte_en.py
