# Adversary Dialog — feat-711-unterseite (Nachtrag: CI-Fix „Apps“)
Spec: docs/specs/oberflaeche/funktionsseiten-711-teil3.md

## Checkliste
- [x] AC-1: `/info/funktionen/reiseseite/` DE und EN, Texte aus dem Katalog, Titel
- [x] AC-2: Die Übersicht verlinkt die Reiseseite
- [x] AC-3: Wege 303, POST, HEAD, 404
- [x] AC-4: Galerie der Unterseite (test_infoseite_galerie_711.py)
- [x] AC-5: Texte in jeder Sprache, Bilder DE/EN, BILDER
- [x] AC-6: Ausnahmelisten nicht länger, Tests grün

## Dialog

### Runde 1
**Adversary:** Der Fix ersetzt „neben deinen Apps“ durch „auf deinem Home-Bildschirm“ (einzige Änderung, 1 Zeile in texte_de.py). Behebt das den CI-Fehler? Gibt es weitere Funde?
**Implementierer:** Lauf der sieben Testdateien (test_funktionsseiten_711, test_infoseite_galerie_711, test_infoseite, test_texte, test_englisch_schnittstelle, test_englisch, test_englisch_werte): 119 passed, 0 failed, 0 übersprungen, darunter der CI-Test test_englisch_schnittstelle. „Apps“ steht nicht mehr im Satz; „Home-Bildschirm“ war schon als Beschriftung im Satz.

### Runde 2
**Adversary:** Sinn und Sprache: DE „liegt die Reise mit eigenem Symbol auf deinem Home-Bildschirm“, EN „sits next to your apps with its own icon“. Folgeschäden? texte_en.py, Schlüssel und Ausnahmelisten unverändert.
**Implementierer:** Sinn gleich, Grammatik korrekt. Stilnotiz LOW, nicht blockierend: „Home-Bildschirm“ steht im Satz zweimal. anmeldung.py und erzeugen.py unverändert; AC-1 bis AC-6 durch die Tests weiter belegt.

Confirmation:
  AC: AC-1
  Code reference: engine/texte_de.py:3880
  Evidence: Katalogtext korrekt, Tests grün
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/info/erzeugen.py:1337
  Evidence: Übersicht führt reiseseite unter unterwegs, Tests grün
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/anmeldung.py:1
  Evidence: unverändert, Wege-Tests in test_funktionsseiten_711.py grün
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/info/erzeugen.py:1510
  Evidence: Galerie der Unterseite, test_infoseite_galerie_711.py grün
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/texte_en.py:3878
  Evidence: englischer Text vorhanden, erzeugen.BILDER (erzeugen.py:37) unverändert, Tests grün
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_de.py:3880
  Evidence: test_texte.py und test_englisch*.py grün, Ausnahmelisten unverändert
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
VERDICT: VERIFIED
Tests: 119 passed, 0 failed, 0 übersprungen

## Geprüfte Dateien

- sha256:10f268646bdea05dd17fd2c6cc88dc918606c46d076db2076a40414c93a67281  engine/anmeldung.py
- sha256:7f8dc2e7ab4dcdeb6d1af8a08be0fba1a0ab5148e814b2697c60243feff9de10  engine/info/erzeugen.py
- sha256:0426b4b5657da9c8945ab775878d38b2b9c3f1ab1d7816f0ad92836b74153adc  engine/texte_de.py
- sha256:f0fabf93e984b2867ac85df6c1071226e3fb3e107bb132efcdc68f10c831a65d  engine/texte_en.py

## Prüfbasis

- base: aad85d07dc66ae7e868ba7190089cd70b9ff3adc
- blob:8c338972cd791fa4a9236a3b5e517e8570093b45  engine/anmeldung.py
- blob:8bafbdf73b4982bb89919954d4abbc26a2c3f34d  engine/info/erzeugen.py
- blob:ca7768a50fa785691f6796531c750fb0a8c4e877  engine/texte_de.py
- blob:4bb89730525dab0ab95ee59b828595b0c55479dc  engine/texte_en.py
