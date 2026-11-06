# Adversary Dialog — fix-374-wahlstelle-hinweis
Spec: docs/specs/fast/fix-374-wahlstelle-hinweis.md
Datum: 2026-11-06

## Checkliste
- [x] AC-1: DE-Text nennt unterkuenfte, strecken, aufenthalte, orte, folge — PROVEN
- [x] AC-2: EN-Text nennt dieselben Sorten (sequence statt folge) — PROVEN
- [x] AC-3: Schlüssel, Platzhalter, Verhalten unverändert; DE/EN gleiche Schlüssel — PROVEN

## Dialog

### Runde 1
**Adversary:** Beweise AC-1 und AC-2 am Katalog, nicht am Test. Was steht im Katalog, was vor der Änderung?
**Implementierer:** Der Diff ändert nur drei Dateien (texte_de, texte_en, tests/test_texte.py), je eine Zeile bzw. ein Test. Neuer DE-Text: „…(titel und unterkuenfte, strecken, aufenthalte, orte oder folge).“ EN: „…(titel and unterkuenfte, strecken, aufenthalte, orte or sequence).“ Alter Text laut HEAD-Stand von engine/texte_de.py (Zeile 1672): „…strecken oder folge“, also ohne aufenthalte und orte; der Test (Wortgrenzen-Regex für alle fünf Sorten, DE und EN) hätte damit für aufenthalte und orte versagt und zeigt den Fehler. Die Namen entsprechen schreiben.option_bauen.2 (texte_de.py:1608).
Code reference: engine/texte_de.py:1672
Code reference: engine/texte_en.py:1671
Code reference: engine/tests/test_texte.py:686
**Adversary:** Platzhalter, Parität, Umlaute?
**Implementierer:** Keine Platzhalter in .4 (DE und EN, per Regex geprüft); set(texte_de.TEXTE)==set(texte_en.TEXTE) (3224 Schlüssel); Anführungszeichen und Umlaute unverändert. pytest -q engine/tests/test_texte.py: 89 passed, 0 failed, 0 übersprungen.

### Runde 2
**Adversary:** Wird der Text bei wahlstelle_anlegen ohne optionen wirklich ausgegeben? Auch bei leerer Liste oder Nicht-Liste?
**Implementierer:** Scratchpad-Kopie der Beispielreise (keine echte Reise): schreiben.wahlstelle_anlegen(Kopie, Ida, titel X) lehnt ab mit Schlüssel schreiben.wahlstelle_anlegen.4; e.text(de) und e.text(en) liefern die neuen Texte mit allen fünf Sorten. Dasselbe für optionen=[] und optionen=x (Bedingung not isinstance list or not optionen). schreiben.py ist nicht geändert. Anders als bei #364 ist der Text hier über den manuellen Testschritt 1 der Spec tatsächlich erreichbar.
Code reference: engine/schreiben.py:2420
**Adversary:** Restrisiko? Weitere Sprachen?
**Implementierer:** Es gibt nur de und en; der Test deckt beide. Der Text nennt die Regel „nur eines von…“ aus option_bauen.2 nicht, das ist kein Spec-Punkt.

## Herkunft der Vorbedingungen
kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
**VERIFIED**
Änderung korrekt und minimal, 89 passed. Alle drei ACs belegt, Text im Scratchpad-Aufruf tatsächlich ausgegeben.

## Geprüfte Dateien

- sha256:091e0b6649655c2528d016922d1408fd9b7340eb4abdaa27d97cb8059e9ae2f6  engine/schreiben.py
- sha256:4421f46e408048a825068c43a01191d8bd6230180d7197dd248be87f894da518  engine/tests/test_texte.py
- sha256:e4f13e9f559e0f46b400b1bdaa613f538c304421b1450de90f609c359b806ffc  engine/texte_de.py
- sha256:4d421c3dd710d63f16972c27745dd5da942d7f283bd4b655295b7232b937b126  engine/texte_en.py

## Prüfbasis

- base: 0ff37b3a997c750cf965211332ee5c8c1861fe3a
- blob:0a0061631b44b3ebcffdefcef77604a7d6482675  engine/schreiben.py
- blob:500cd67a26ddf2fc7137f4dc9f56631652b0f470  engine/tests/test_texte.py
- blob:c0411ddfe94804ea75253784ba10b95a86b2c929  engine/texte_de.py
- blob:464dab6c644ff0422e1a180dab567bf66c8bac76  engine/texte_en.py
