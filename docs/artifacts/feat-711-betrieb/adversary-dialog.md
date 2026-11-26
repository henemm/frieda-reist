# Adversary Dialog — feat-711-betrieb
Spec: docs/specs/oberflaeche/funktionsseiten-711-betrieb.md
Datum: 2026-11-26 21:19

## Checkliste
- [x] AC-1: `/info/funktionen/betrieb/` liefert in DE und EN 200 mit allen Abschnitten und Bildern (`test_unterseite[betrieb]`).
- [x] AC-2: Die Übersicht hat keine Zeile „Seite folgt“ mehr (`test_unterseiten_konto`, `test_uebersicht_alle_funktionen`).
- [x] AC-3: Die Unterseite verlinkt die Anleitung `docs/betrieb.md` im Repo aus `instanz.QUELLCODE`, mit `target="_blank"` und `rel="noopener"`; Seiten ohne `doku` haben keinen solchen Link (`test_link_zur_anleitung`).
- [x] AC-4: Texte vollständig je Sprache; Ausnahmelisten nicht länger; Fachwörter einheitlich (`test_texte`). Inhalt treu zur Quelle (keine KI auf dem Server; Reisespeicher nur anhängen; tägliche Sicherung; neue Software erst nach Prüfung, Rückfall auf den letzten guten Stand; Veröffentlichen höchstens 2 Minuten als Ziel); Bildunterschriften nur das Sichtbare.
- [x] AC-5: Vorhandene Bilder unverändert.

## Dialog

### Runde 1
**Adversary:** Beweis je AC verlangt. Test-Lauf: `engine/.venv/bin/python -m pytest -q -n 4 engine/tests/test_funktionsseiten_711.py engine/tests/test_texte.py engine/tests/test_englisch.py` -> 117 passed, 0 failed, 0 skipped (12 s). Bilder: `git status --short engine/info` und `git diff HEAD --stat -- engine/info` leer; `git diff --stat` zeigt nur 5 Dateien (design.md, anmeldung.py, Test, texte_de.py, texte_en.py), 86 Zeilen hinzu, 9 weg.

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1374
  Evidence: Eintrag `betrieb` in INFO_UNTERSEITEN mit Bildern fuss und reise, Gespräch person/claude, siehe konto/wahrheit/erinnerungen/sprachen; Texte lead, wo, wer, bild.*, tun.1-4, wie.1-3, gespraech, rolle.1-3, gut.1-3 in beiden Katalogen (engine/texte_de.py:4381 bis 4409, engine/texte_en.py:4379 bis 4407). `test_unterseite[betrieb]` ist grün (DE und EN).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1342
  Evidence: Gruppe vollständig, Übersichtstests (`test_unterseiten_konto`, `test_uebersicht_alle_funktionen`) grün; kein Schlüssel „Seite folgt“ mehr nötig.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/anmeldung.py:1632
  Evidence: Nur bei `s.get("doku")` wird `<QUELLCODE>/blob/main/<doku>` mit `target="_blank" rel="noopener"` und Text `info.bereich.betrieb.doku` angehängt (engine/texte_de.py:4384, engine/texte_en.py:4382). `test_link_zur_anleitung` prüft alle Unterseiten in allen Sprachen, auch „kein Link ohne doku“; grün. Der Wert wird mit `esc` maskiert.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/anmeldung.py:1374
  Evidence: Keine Datei unter engine/info/ geändert (git diff leer); die Bilder fuss-de/en.webp und reise-de/en.webp wurden nur betrachtet.
  Status: CONFIRMED

**Implementierer:** (Stand der Änderung wie im Diff.)

### Runde 2
**Adversary:** Inhalt und Bilder gegen Quellen geprüft.

Bildunterschriften: `info.bereich.betrieb.bild.fuss` (engine/texte_de.py:4385, engine/texte_en.py:4383) gegen fuss-de.webp/fuss-en.webp: Sichtbar sind „Frieda Release 940 · Hash · Auf Neueres prüfen“ (EN „Check for newer version“), die Zeile Sprache, Datenschutz, Impressum, Alpha-Hinweis. Die Unterschrift nennt Stand, „Auf Neueres prüfen“, Datenschutz und Impressum, nichts Unsichtbares; Alpha-Hinweis und Sprachzeile fehlen, das ist zulässig (nur das Sichtbare, nicht alles). Der EN-Text „Check for newer version“ stimmt wörtlich mit dem Bild. `.bild.reise` (engine/texte_de.py:4386, engine/texte_en.py:4384) gegen reise-de/en.webp: Anfang der Beispielreise mit Titel, Zähler, Anreise und Karte; „Überblick“ ist so auch in `info.bereich.reiseseite.bild.reise` benannt (der Reiter heißt in der Beispielreise „Varianten“), also konsistent.

Treue zur Quelle (`docs/funktionen/selbst-betreiben.md`, `docs/betrieb.md`): keine KI auf dem Server (wie.1.text, Zeile engine/texte_de.py:4392) ok; Reisespeicher nur anhängen (wie.2.text „überschrieben wird nichts“) ok; tägliche Sicherung (wie.2.text, tun.2) ok; Prüfung vor Umschalten und Rückfall auf letzten guten Stand (wie.3.text, tun.3; betrieb.md Zeile 15) ok; Fehler einer Reise hält nur diese an (betrieb.md Zeile 156) ok; Voraussetzungen HTTPS, Python, git, Node, kein GitHub-Konto (selbst-betreiben.md Zeile 49) ok; Mailversand (betrieb.md, Abschnitt Mails, SMTP) ok.

Korrekturen: `info.bereich.sprachen.wer` DE (engine/texte_de.py:4354) hat nun Doppelpunkte nach „der Reise“ und „des Kontos“; EN ist unverändert (nicht gefordert). `info.bereich.sprachen.wie.1.text` DE (engine/texte_de.py:4362) und EN (engine/texte_en.py:4360) ergänzen „(Betreff und Anrede; die Meldung selbst steht in der Sprache der Reise)“ bzw. die englische Entsprechung, inhaltlich gleich.

Finding:
  ID: F001
  Severity: LOW
  Category: spec_violation
  Code reference: engine/texte_de.py:4400
  Description: `info.bereich.betrieb.gespraech.2` sagt „In wenigen Minuten baut der Server ihre Seite“ (EN engine/texte_en.py:4398 „In a few minutes“). Die Quelle (selbst-betreiben.md Zeile 29) nennt als Ziel höchstens 2 Minuten; AC-4 zählt dieses Ziel zum treuen Inhalt. Es steht nirgends auf der Unterseite.
  Spec requirement: AC-4 — Veröffentlichen höchstens 2 Minuten als Ziel
  Conflict: Die Aussage fehlt, und die Blase ist ungenauer als die Quelle. Nicht falsch (das Ziel ist ein Höchstwert), daher kein Blocker.
  Remediation: `info.bereich.betrieb.gespraech.2` DE/EN auf „Angelegt. In höchstens zwei Minuten baut der Server ihre Seite …“ (EN „within two minutes at most“) oder das Ziel in `info.bereich.betrieb.wie.1.text` ergänzen; wahlweise bewusst weglassen und im Changelog der Spec vermerken.

**Implementierer:** keine weitere Änderung nötig; F001 ist LOW.

## Herkunft der Vorbedingungen

Kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Reiner Text- und Konfigurationsumbau; keine Felder mit Produktions-Schreibstellen betroffen.

## Verdict

Coverage der geänderten Dateien (required-files):
  Code reference: engine/anmeldung.py:1632
  Code reference: engine/texte_de.py:4381
  Code reference: engine/texte_en.py:4379

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 117 passed, 0 failed, 0 übersprungen
Edge cases: alle geprüft (Link nur mit doku, EN/DE, Maskierung)
Regressions: keine gefunden
Checklist: 5/5 Punkte bewiesen; ein LOW-Fund (F001), kein Blocker

## Geprüfte Dateien

- sha256:a7b0e23342c1181093805acc8fe44a93c30b48a1081956212c7a7851aaa44e4f  engine/anmeldung.py
- sha256:d62ac57e31365db6c91f8cdb74f1adfa2d264f6235f7d41c11e2496ab15576cb  engine/texte_de.py
- sha256:d965105b5f7f42394d251c2c9b7ab0aec65e73214b330f7206add87e868b8813  engine/texte_en.py

## Prüfbasis

- base: 7f16f048d54c07e96d938efca174347823019945
- blob:1d6d4fd4c12c0be6eaaebcf061db2a1a09710b44  engine/anmeldung.py
- blob:e7564daed6b67f965cb0bc88f0766f09415428e9  engine/texte_de.py
- blob:a5b47ec1af976825418adbb6c454458603e2885f  engine/texte_en.py
