# Adversary Dialog — fix-619-uhrzeit-doppelt
Spec: docs/specs/oberflaeche/uhrzeit-doppelt-619.md
Datum: 2026-11-22 06:55

## Checkliste
- [x] **AC-1:** Given ein Aufenthalt mit Freitext „nach der Wanderung, 16–18 Uhr“ und Zeitfenster 16:00–18:00 / When die Anzeige berechnet wird / Then lautet der Freitext „nach der Wanderung“; bei „13 Uhr“ und 13:00–15:00 entfällt der Freitext ganz.
- [x] **AC-2:** Given „Sonntag Vormittag“, „ab 16 Uhr“ (16:00), „17–19 Uhr“ bei 16:00–18:00 oder ein Freitext ohne Beginn / When die Anzeige berechnet wird / Then bleibt der Freitext unverändert.
- [x] **AC-3:** Given eine Sprache mit anderem oder leerem Einheitswort (en, Pseudo-Sprache der Tests) / When „16–18“ bei 16:00–18:00 angezeigt wird / Then entfällt die Uhrzeit, ohne dass der Code eine Sprache beim Namen kennt; das Einheitswort kommt aus `seite.zeit.uhr`.
- [x] **AC-4:** Given beide Beispielreisen (Beispielreise A-01, Stadtwochenende) / When Seite, Konnektor `show`, Tagestext und Kalender erzeugt werden / Then steht die Uhrzeit je Aufenthalt genau einmal.
- [x] **AC-5:** Given eine gebaute Reise / When die Reisedaten danach gelesen werden / Then sind `zeit`, `beginn` und `ende` unverändert gespeichert; kein `nachziehen` nötig.
- [x] **AC-6:** Given die vollständige Testsuite / When `engine/.venv/bin/python -m pytest -q engine/tests` läuft / Then ist sie grün, einschließlich `test_texte.py` und `test_design.py` (kein neuer Baustein, kein neuer Text).

## Dialog

### Runde 1
**Adversary:** Testlauf `engine/tests/test_zeit_doppelt.py`: 28 passed (Ausgabe in adversary-test-output.txt, dazu 35 Direktaufrufe von `zeit_ohne_uhr`). Volle Suite laut test-green-output.txt: 3482 passed. Randfälle (Ergebnis in Klammern):
- „16 - 18 Uhr“, „16:00–18:00 Uhr“, „16:00-18:00“, „16.30 Uhr“ bei 16:30 (mit/ohne Ende), „08 Uhr“ bei 8:00 (alle leer, korrekt).
- „16 Uhr · ab Bahnhof“ (bleibt „ab Bahnhof“), „ab 16 Uhr“, „Besuch 16 Uhr“, „18–16 Uhr“, „16–18–20 Uhr“, „16–18 Uhr“ ohne Ende (alle unverändert, korrekt).
- „16 Uhrzeit“ und „16Uhr“ (Einheitswort als Wortteil): unverändert, sicher.
- ende fehlt bei „16 Uhr“: entfällt (laut Spec: eine Zeit gleich beginn passt). ende leer/„abc“: kein Absturz, „16 Uhr“ bei ende „abc“ bleibt.
- beginn „abc“ oder leer: unverändert; beginn „16:00:00“: passt (Sekunden werden ignoriert).
- zeit kein String (123) oder None: unverändert zurück, kein Absturz. Nur Trennzeichen („,“, „ · ; “): unverändert.
- Einheit leer/„h“/„o'clock“: „16–18“ entfällt bei jeder Einheit; „16–18 Uhr“ bleibt bei fremder Einheit stehen (sicher, im Zweifel doppelt).
Beobachtung: „a; 16–18 Uhr · b“ ergibt „a · b“ (das Trennzeichen des folgenden Stücks wird benutzt, rein kosmetisch).
Kalender: `a.get("zeit_rest", a.get("zeit")) if b else a.get("zeit")` fällt ohne `zeit_rest` auf `zeit` zurück und nutzt `zeit_rest` nur, wenn `_spanne` wirklich einen Beginn liefert (Beginn „25:00“ liefert kein b, dann bleibt der Freitext). Ein leeres `zeit_rest` ergibt keinen Textzeilen-Eintrag. Korrekt.
Konnektor: Einheit aus der Reisesprache, Rückfall `texte.VORGABE_REISE`; bei Abweichung zur Personensprache bleibt höchstens die Doppelanzeige, nie ein falscher Text.
Vorlage: drei Etiketten lesen `zeit_rest ?? zeit` (leerer String bleibt leer, `??` greift nur bei null/undefined).
**Implementierer:** (keine Stellungnahme, Kontext getrennt)

### Runde 2
**Adversary:** Gezielt nach Lücken gesucht.
- Weitere Leser von `zeit` im Code: `engine/kalender.py:135` (Tageseintrag der Sorte „tage“) schreibt `Name, zeit` mit dem rohen Freitext. Dieser Eintrag trägt aber keine Uhrzeit (ganztägig), daher keine Doppelung innerhalb eines Eintrags; über Einträge hinweg kann „16–18 Uhr“ im Tagestext und im eigenen Termin stehen (Finding F001, LOW, vorbestehend, nicht in der Spec gefordert).
- `engine/vorlage.html:3867` (Zeitleiste) zeigt `a.zeit` ohne `uhrText`, also einmal; kein Fehler.
- Konnektor: `zeit` wird sonst nirgends ausgegeben (grep), kein weiterer Pfad.
- Gespeicherte Daten: `zeit_anzeigen` schreibt `zeit_rest` nur in die Seitendaten-Struktur, `zeit`/`beginn`/`ende` bleiben (Test test_gespeicherte_daten_bleiben); in `neu.py` keine Änderung.
- Nebenänderung `engine/tests/test_trennung.py` (Datum auf heute statt festes Datum) gehört nicht zum Thema, verändert aber nur Testdaten, Suite grün.
- Rückfall bei Seitendaten ohne `zeit_rest` (alte Seite): Vorlage und Kalender fallen auf `zeit` zurück.
**Implementierer:** (keine Stellungnahme)

### Bestätigungen
Confirmation: AC: AC-1, Code reference: engine/routen.py:421, Evidence: `zeit_ohne_uhr` zerlegt an , ; · und entfernt nur Stücke, die reine Uhrzeit zum Fenster sind; Direktaufruf „nach der Wanderung, 16–18 Uhr“ ergibt „nach der Wanderung“, „13 Uhr“ bei 13:00–15:00 ergibt leer. Status: CONFIRMED
Confirmation: AC: AC-2, Code reference: engine/routen.py:404, Evidence: `_nur_fenster` verlangt exakten Treffer auf beginn/ende und kein weiteres Wort; „ab 16 Uhr“, „17–19 Uhr“, „Sonntag Vormittag“, fehlender beginn bleiben unverändert (Direktaufruf, Tests). Status: CONFIRMED
Confirmation: AC: AC-3, Code reference: engine/routen.py:395, Evidence: `uhr_einheit` liest `seite.zeit.uhr` aus dem Katalog (de „Uhr“, en leer); die Funktion hat keinen Sprachnamen; „16–18“ entfällt bei Einheit leer, „h“ und „o'clock“. Status: CONFIRMED
Confirmation: AC: AC-4, Code reference: engine/bauen.py:1433, Evidence: `zeit_anzeigen` setzt `zeit_rest` für Aufenthalte und Unterkünfte; Vorlage engine/vorlage.html:2094 liest `zeit_rest ?? zeit` (ebenso 2272, 3743); Konnektor engine/konnektor.py:928 und Kalender engine/kalender.py:160 nutzen dasselbe; Tests für beide Beispielreisen grün. Status: CONFIRMED
Confirmation: AC: AC-5, Code reference: engine/bauen.py:1440, Evidence: nur das Anzeigefeld wird ergänzt, keine Schreibung in die Reisedaten; Test test_gespeicherte_daten_bleiben grün. Status: CONFIRMED
Confirmation: AC: AC-6, Code reference: engine/konnektor.py:74, Evidence: volle Suite 3482 passed (test-green-output.txt), `test_zeit_doppelt.py` 28 passed im eigenen Lauf; kein neuer Text, kein neuer Baustein. Status: CONFIRMED

### Findings
Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/kalender.py:135
  Description: Der ganztägige Tageseintrag listet `Name, zeit` mit dem rohen Freitext, auch wenn der Aufenthalt als eigener Termin mit Uhrzeit im Kalender steht.
  Spec requirement: AC-4 — Uhrzeit je Aufenthalt genau einmal im Kalender
  Conflict: Nur bei sehr strenger Lesart doppelt (zwei verschiedene Einträge); die Spec fordert nur den Termintext (Test 8). Vorbestehendes Verhalten.
  Remediation: Optional dort ebenfalls `zeit_rest` verwenden, wenn beginn gesetzt ist.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/routen.py:421
  Description: Beim Entfernen eines mittleren Stücks übernimmt der Rest das Trennzeichen des Folgestücks („a; 16–18 Uhr · b“ ergibt „a · b“).
  Spec requirement: AC-1 — Freitext ohne die Uhrzeit
  Conflict: Rein kosmetisch, kein Inhaltsverlust.
  Remediation: Keine nötig.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hielt dem Angriff stand.
Tests: 28 passed (test_zeit_doppelt.py), volle Suite 3482 passed, 0 failed, 0 übersprungen
Edge cases: alle geprüft, nichts gebrochen (2 LOW-Anmerkungen F001, F002, keine Blocker)
Regressions: keine gefunden
Checklist: 6/6 Punkte bewiesen

Code reference: engine/bauen.py:1433
Code reference: engine/kalender.py:160
Code reference: engine/konnektor.py:928
Code reference: engine/routen.py:421
Code reference: engine/vorlage.html:2094

## Geprüfte Dateien

- sha256:595aae962b8522ccaa58fbb3c84ad078d66516d77689d76007fe595d1ef539dc  engine/bauen.py
- sha256:ef0a1477e3db6cc4508d459b6ec518ebe118e78e607588ae07999d7ba9627c6a  engine/kalender.py
- sha256:8893bc5dfdb1127be02ad3890293ba552b205d6e614c8016fc315af5d97441ee  engine/konnektor.py
- sha256:9d4eb23bc4618a6023cecd8b649c14eb053bd689df370e2bbb7777147c031835  engine/routen.py
- sha256:cdd1f61e90c3b57d3cf7a8aa918095f90c2ee7d42aae8f6998fe2a2d11322eed  engine/vorlage.html

## Prüfbasis

- base: 388dba0e50ec1e111bfa346b946d1babed7a3cbb
- blob:d0812b228fba0f5f2fe91ae33e902cd8287fbe4c  engine/bauen.py
- blob:7495ee17710a169b79c315956612c74ce9acb4f2  engine/kalender.py
- blob:9a8508e5ff3e621f77444689ef513a797789b613  engine/konnektor.py
- blob:d9593f3398c845aa101a32e2df4e988c78f38861  engine/routen.py
- blob:5994e68189c6f852b7647ba38ce56a1d0bd95c8f  engine/vorlage.html

## Geprüfte Dateien

- sha256:595aae962b8522ccaa58fbb3c84ad078d66516d77689d76007fe595d1ef539dc  engine/bauen.py
- sha256:ef0a1477e3db6cc4508d459b6ec518ebe118e78e607588ae07999d7ba9627c6a  engine/kalender.py
- sha256:8893bc5dfdb1127be02ad3890293ba552b205d6e614c8016fc315af5d97441ee  engine/konnektor.py
- sha256:9d4eb23bc4618a6023cecd8b649c14eb053bd689df370e2bbb7777147c031835  engine/routen.py
- sha256:cdd1f61e90c3b57d3cf7a8aa918095f90c2ee7d42aae8f6998fe2a2d11322eed  engine/vorlage.html

## Prüfbasis

- base: 388dba0e50ec1e111bfa346b946d1babed7a3cbb
- blob:d0812b228fba0f5f2fe91ae33e902cd8287fbe4c  engine/bauen.py
- blob:7495ee17710a169b79c315956612c74ce9acb4f2  engine/kalender.py
- blob:9a8508e5ff3e621f77444689ef513a797789b613  engine/konnektor.py
- blob:d9593f3398c845aa101a32e2df4e988c78f38861  engine/routen.py
- blob:5994e68189c6f852b7647ba38ce56a1d0bd95c8f  engine/vorlage.html
