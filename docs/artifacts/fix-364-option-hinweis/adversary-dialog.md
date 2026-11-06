# Adversary Dialog — fix-364-option-hinweis
Spec: docs/specs/fast/fix-364-option-hinweis.md
Datum: 2026-11-06

## Checkliste
- [x] 1. `schreiben.option_bauen.1` nennt in DE und EN alle fünf Sorten — PROVEN
- [x] 2. Verhalten von `option_bauen` unverändert, Schlüssel/Platzhalter gleich — PROVEN
- [x] 3. DE/EN deckungsgleiche Schlüssel, Umlaute korrekt — PROVEN
- [x] 4. Ablehnung mit diesem Text bei Option ohne Inhalt — PROVEN nur für Nicht-Objekt; für Objekt ohne Inhalt AMBIGUOUS (Runde 2)

## Dialog

### Runde 1
**Adversary:** Beweise Punkt 1 und 2. Was wurde wirklich geändert?
**Implementierer:** Commit 4634739 ändert nur engine/texte_de.py und engine/texte_en.py, je 1 Zeile. engine/schreiben.py ist nicht berührt; `raise Ablehnung("schreiben.option_bauen.1")` (engine/schreiben.py:2296) ohne Platzhalter, unverändert.
Code reference: engine/texte_de.py:1607 — "…(unterkuenfte, strecken, aufenthalte, orte oder folge)."
Code reference: engine/texte_en.py:1606 — "…(unterkuenfte, strecken, aufenthalte, orte or sequence)."
**Adversary:** Platzhalter, Schlüsselparität, Test-Beleg?
**Implementierer:** Keine {…}-Platzhalter in beiden Texten; set(DE)==set(EN) (3224 Schlüssel). Umlaute der Nachbarzeilen unverändert. `pytest -q engine/tests/test_texte.py`: 88 passed, 0 failed, 0 übersprungen; der neue Test test_option_bauen_hinweis_nennt_alle_sorten prüft mit Wortgrenzen alle fünf Sorten (EN: sequence).

### Runde 2
**Adversary:** Punkt 4: Eine Option mit titel und ohne Inhalt — kommt wirklich dieser Text?
**Implementierer:** option_bauen direkt aufgerufen (Scratchpad, keine echte Reise): "kein dict" und None -> schreiben.option_bauen.1, DE und EN mit allen fünf Sorten. {"titel":"X"} ohne quelle -> option_bauen.5. {"titel":"X","quelle":"Anruf"} wird ohne Ablehnung angenommen, weil option_inhalt_ok (engine/schreiben.py:3577) 0 Sorten zulässt. Text .1 erscheint also nur bei Nicht-Objekten. Das ist vorbestehendes Verhalten außerhalb der Spec; der manuelle Testschritt 1 der Spec ist wörtlich nicht erreichbar, der Text selbst ist korrekt.
Code reference: engine/schreiben.py:2296
Code reference: engine/schreiben.py:3577

## Herkunft der Vorbedingungen
kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
**VERIFIED**
Änderung korrekt und minimal, 88 passed. Hinweis: Spec-Testschritt 1 trifft nicht zu, weil eine Option mit titel+quelle ohne Inhalt heute angenommen wird; .1 greift nur bei Nicht-Objekten.

## Geprüfte Dateien

- sha256:091e0b6649655c2528d016922d1408fd9b7340eb4abdaa27d97cb8059e9ae2f6  engine/schreiben.py
- sha256:03c266719b1fbe7ad062e6854823ffbcaabb10a9dd8292ae0c8b1137bad3682d  engine/texte_de.py
- sha256:fa9bb180394c47f226a07515001e785b0c7fdefc38a3442a409d76d15714f25a  engine/texte_en.py

## Prüfbasis

- base: 4634739008eb45ee3d3b76e5400feb46e0c8c629
- blob:0a0061631b44b3ebcffdefcef77604a7d6482675  engine/schreiben.py
- blob:ab1dd085f5ddf0dcdaa1860259d749f27e2e4b0c  engine/texte_de.py
- blob:37a525800c7a7ee379416a380e092bc511b9fa01  engine/texte_en.py

## Geprüfte Dateien

- sha256:091e0b6649655c2528d016922d1408fd9b7340eb4abdaa27d97cb8059e9ae2f6  engine/schreiben.py
- sha256:03c266719b1fbe7ad062e6854823ffbcaabb10a9dd8292ae0c8b1137bad3682d  engine/texte_de.py
- sha256:fa9bb180394c47f226a07515001e785b0c7fdefc38a3442a409d76d15714f25a  engine/texte_en.py

## Prüfbasis

- base: 4634739008eb45ee3d3b76e5400feb46e0c8c629
- blob:0a0061631b44b3ebcffdefcef77604a7d6482675  engine/schreiben.py
- blob:ab1dd085f5ddf0dcdaa1860259d749f27e2e4b0c  engine/texte_de.py
- blob:37a525800c7a7ee379416a380e092bc511b9fa01  engine/texte_en.py
