# Adversary Dialog — feat-711-konto
Spec: docs/specs/oberflaeche/funktionsseiten-711-konto.md
Datum: 2026-11-26 21:14

## Checkliste
- [x] AC-1: `/info/funktionen/konto/` und `/info/funktionen/sprachen/` liefern in DE und EN 200 mit allen Abschnitten aus dem Katalog und ihren Bildern (`test_unterseite[konto]`, `test_unterseite[sprachen]`, `test_unterseiten_konto`).
- [x] AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- [x] AC-3: Texte und Bilder vollständig je Sprache (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- [x] AC-4: Inhalte stimmen mit der Quelle überein (Code sechsstellig, zehn Minuten, einmal; Anmeldung ein Jahr je Gerät; vier Schritte zum Verbinden; Profil nur mit Bestätigung, nur für dich sichtbar; ZIP-Export; Löschen mit Häkchen; Warteliste; neues Konto in der Sprache des Browsers, sonst Englisch; Inhalte nie übersetzt); jede Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.
- [x] AC-5: Vorhandene Bilder bleiben unverändert im Commit.

## Dialog

### Runde 1
**Adversary:** Tests selbst gelaufen: `pytest -q -n 4` über test_funktionsseiten_711, test_texte, test_englisch: 115 passed, 0 failed, 0 übersprungen (Ausgabe wird durch den Gate-Lauf des Aufrufers abgelegt). Diff gelesen: 5 Dateien geändert (+150 Zeilen), zwei neue Bilder fuss-de/en.webp; keine Ausnahmelisten in test_texte.py angefasst. Alle 74 Schlüssel `info.bereich.konto|sprachen.*` stehen in DE und EN (je 74). Bilder fuss-de/en und tag-de/en mit eigenen Augen angesehen.
**Implementierer:** n/a (isoliert).

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1370
  Evidence: INFO_UNTERSEITEN enthält `konto` (Bild fuss, vier Gesprächszeilen) und `sprachen` (Bilder fuss, tag, zwei Zeilen); test_unterseite[konto|sprachen] und test_unterseiten_konto grün (DE und EN 200).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1336
  Evidence: INFO_GRUPPEN führt konto und sprachen; info_bereich_link (anmeldung.py:1572) verlinkt jeden Namen aus INFO_UNTERSEITEN auf die Unterseite, test_uebersicht_alle_funktionen grün. `betrieb` (Teil 2) bleibt bewusst „Seite folgt“; die Verweise „siehe“ auf betrieb zeigen auf die Übersichtszeile, kein toter Link.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:4311
  Evidence: Schlüsselsatz (lead, wo, wer, bild.*, tun.1-8 bzw. 1-4, wie.1-6 bzw. 1-3, gespraech, rolle.1-3, gut.1-5 bzw. 1-4) in DE deckungsgleich mit EN (texte_en.py:4309); test_texte_und_bilder_jeder_unterseite und test_texte grün. EN-Fachwörter einheitlich: trip, notification, organiser, My account, footer.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/texte_en.py:4353
  Evidence: Fuß-Bild (DE): „Frieda Release 940 · 7f16f04 · Auf Neueres prüfen“, „Sprache: Deutsch · English“ mit Deutsch schwarz (gewählt), Links Datenschutz, Impressum, Alpha-Hinweis: beide Unterschriften (konto.bild.fuss, sprachen.bild.fuss) stimmen. EN-Bild: English gewählt, Deutsch als Link, Privacy/Legal notice/Alpha notice: EN-Unterschrift „English is selected“ stimmt. Tag-Bild DE: Tag 2 vollständig deutsch; EN: Day 2, Fri 14/5, Overview, dep./arr., Source:, Booking, aber Beispieltexte der Reise deutsch: Unterschrift „labels and dates in English, texts of the trip stay in German“ stimmt. Inhalt gegen docs/funktionen/konto.md und sprachen.md abgeglichen: sechsstelliger Code, zehn Minuten, einmal; ein Jahr je Gerät; vier Schritte; Profil nur nach ausdrücklichem Ja, nur du; ZIP; Häkchen; Warteliste; Browser-Sprache sonst Englisch; Inhalte nie übersetzt: alle treu (texte_de.py:4311-4376).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/info/erzeugen.py:55
  Evidence: `git status --short engine/info`: nur erzeugen.py geändert (Eintrag fuss, Ziel #fuss) und neu fuss-de/en.webp; tag-/mitreisende-*.webp unverändert (git diff --stat listet keine Binärdatei).
  Status: CONFIRMED

### Runde 2
**Adversary:** Nachgebohrt. (a) Spec Scope 1 und 3 nennen für `konto` die Bilder `fuss` und `mitreisende`, der Code hat nur `fuss`; die ACs verlangen kein zweites Bild, die Seite ist aber ärmer als die Spec. (b) Die Sprache-des-Kontos-Zeile verschweigt die Einschränkung der Quelle, dass die Meldung selbst in der Sprache der Reise steht. (c) Das Fuß-Bild zeigt den Basis-Commit 7f16f04 und Release 940 (Beispielstand, harmlos, kein Geheimnis). (d) Gespräch Sprachen Zeile 2 erfindet das Verhalten „Frieda fragt mit Grund zurück“; es deckt sich mit der Quelle („nur Organisator:innen, mit Grund“). (e) `sprachen.wer` DE „die Sprache der Reise Organisator:innen“ ist wörtlich aus der Quelle, ohne Doppelpunkt etwas holprig; EN setzt ihn.
**Implementierer:** n/a.

Finding:
  ID: F001
  Severity: LOW
  Category: spec_violation
  Code reference: engine/anmeldung.py:1370
  Description: `konto` hat nur das Bild `fuss`; die Spec (Scope 1, Scope 3) nennt `fuss` und `mitreisende`.
  Spec requirement: Scope 1 (kein AC) — konto mit Bildern fuss und mitreisende
  Conflict: Abweichung zwischen Spec und Code; AC-1/3/4 sind trotzdem erfüllt (Tests grün, Bild vorhanden).
  Remediation: Spec angleichen (nur `fuss`) oder `mitreisende` samt Schlüssel `info.bereich.konto.bild.mitreisende` in DE und EN ergänzen.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/texte_de.py:4362
  Description: `info.bereich.sprachen.wie.1.text` sagt, die Sprache des Kontos gelte für „Mails und Push-Nachrichten an dich“; die Quelle (docs/funktionen/sprachen.md, Tabelle) nennt die Einschränkung „die Meldung selbst steht in der Sprache der Reise“. Dazu fehlt der Name des Kalender-Abos.
  Spec requirement: AC-4 — Inhalte stimmen mit der Quelle überein
  Conflict: Könnte erwarten lassen, dass auch der Meldungstext in der Kontosprache kommt, obwohl er in der Reisesprache steht. Gleiches in EN (texte_en.py:4360).
  Remediation: DE „… Mails und Push-Nachrichten an dich (Betreff und Anrede; die Meldung selbst steht in der Sprache der Reise) …“, EN „… emails and push messages to you (subject and greeting; the notification itself is in the language of the trip) …“.

Finding:
  ID: F003
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/texte_de.py:4354
  Description: `info.bereich.sprachen.wer` übernimmt die Quelle wörtlich: „die Sprache der Reise Organisator:innen; die Sprache des Kontos jede Person für sich“, ohne Doppelpunkt nach „Reise“; EN setzt ihn (texte_en.py:4352).
  Spec requirement: AC-3 — Texte je Sprache gleichwertig
  Conflict: Kosmetische Holprigkeit in DE.
  Remediation: DE „die Sprache der Reise: Organisator:innen; die Sprache des Kontos: jede Person für sich“.

Code reference (Abdeckung): engine/texte_en.py:4309, engine/texte_de.py:4311, engine/anmeldung.py:1370, engine/info/erzeugen.py:55

## Herkunft der Vorbedingungen
kein Sprachprofil konfiguriert (`precondition_origins.default_lang`).

## Verdict

VERDICT: VERIFIED

Tests: 115 passed, 0 failed, 0 übersprungen. Edge Cases geprüft, nichts gebrochen. Checkliste 5/5 bewiesen. Drei Befunde, alle LOW (F001 Spec nennt zusätzlich `mitreisende`, F002 Einschränkung zur Meldungssprache fehlt, F003 DE-Satzzeichen).

## Geprüfte Dateien

- sha256:be17c5e8f79d4732416575281295c4e933a7fcd0f4e7554e7fe1417a79ca83b8  engine/anmeldung.py
- sha256:31c9fc004db654c55bc3ccd3818c60eef0470da87f3efcf98ba7c0e66f75db6f  engine/info/erzeugen.py
- sha256:31dac8808377bcad76a0f1d1356f50950913234a296d3ba54192ad2a795b384c  engine/texte_de.py
- sha256:a4a392e40941b0605d1934bf915351c5718d98ecb8525c4f4b8d1a3e9e268b1a  engine/texte_en.py

## Prüfbasis

- base: 7f16f048d54c07e96d938efca174347823019945
- blob:450d273ce3298eff2061ed90c77abfcb1ba76a49  engine/anmeldung.py
- blob:10d44dd1ffeb1354dbe65461605c3334c44c2e49  engine/info/erzeugen.py
- blob:5f0cb2f8b75902824c25a7f7c44e995c36e64848  engine/texte_de.py
- blob:a87f6d7e546c93234e54e4947fd35875c7563814  engine/texte_en.py

## Geprüfte Dateien

- sha256:be17c5e8f79d4732416575281295c4e933a7fcd0f4e7554e7fe1417a79ca83b8  engine/anmeldung.py
- sha256:31c9fc004db654c55bc3ccd3818c60eef0470da87f3efcf98ba7c0e66f75db6f  engine/info/erzeugen.py
- sha256:31dac8808377bcad76a0f1d1356f50950913234a296d3ba54192ad2a795b384c  engine/texte_de.py
- sha256:a4a392e40941b0605d1934bf915351c5718d98ecb8525c4f4b8d1a3e9e268b1a  engine/texte_en.py

## Prüfbasis

- base: 7f16f048d54c07e96d938efca174347823019945
- blob:450d273ce3298eff2061ed90c77abfcb1ba76a49  engine/anmeldung.py
- blob:10d44dd1ffeb1354dbe65461605c3334c44c2e49  engine/info/erzeugen.py
- blob:5f0cb2f8b75902824c25a7f7c44e995c36e64848  engine/texte_de.py
- blob:a87f6d7e546c93234e54e4947fd35875c7563814  engine/texte_en.py
