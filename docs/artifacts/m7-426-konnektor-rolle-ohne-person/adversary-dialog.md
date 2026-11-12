# Adversary Dialog — m7-426-konnektor-rolle-ohne-person
Spec: docs/specs/konnektor/rolle-ohne-person-426.md
Datum: 2026-11-12 12:44

## Checkliste
- [x] **AC-1:** Given ein Zugang `{reise, rolle}` ohne `person` / When `wer_spricht` ihn auflöst / Then ist das Ergebnis `None`, und ein Werkzeugaufruf damit endet mit „gehört zu keiner Person“, ohne Schreiben und ohne Gast-Rückfall. Test: `test_zugang_ohne_person_hat_keinen_zugriff`.
- [x] **AC-2:** Given beliebige Person der Reise / When `tools/list` geliefert wird / Then hat kein Werkzeugschema ein Feld `name`, und `vorname` kommt nur bei `einladen` vor. Test: `test_tools_list_ohne_name_und_vorname_ausser_einladen`.
- [x] **AC-3:** Given ein Client sendet weiter `name` oder `vorname` / When er ein Werkzeug aufruft / Then gibt es keinen Fehler, das Argument wirkt nicht, und der Name im Verlauf ist der der Person. Test: `test_ueberzaehliges_namensargument_ohne_fehler`.
- [x] **AC-4:** Given Gast `kim` als Person (Kopie der Beispielreise in der Testvorbereitung) / When sie liest / Then klappt es, / When sie schreibt / Then wird abgelehnt. Test: `test_gast_als_person_kim_liest_schreibt_nicht`. Die Beispielreise im Repo und ihre Demoseite bleiben unverändert (kein Gast dort).
- [x] **AC-5:** Given die Texte entfernt sind / When der Katalog geprüft wird / Then fehlen `konnektor.einladen.6`, `.entscheiden.2`, `.ontologie_werkzeug.7`, `.werkzeug.14`, `.frage_beantworten.4`, `anleitung.du_ohne_name`, `anleitung.mit.vorname`, `feld.name_feld`, `werkzeug.rueckmeldung_geben.name` in allen `engine/texte_*.py` zugleich, kein Code verweist mehr darauf, und `engine/tests/test_texte.py` ist grün mit nicht längeren Ausnahmelisten. Test: `engine/tests/test_texte.py` (bestehend) plus Suche im Code.
- [x] **AC-6:** Given Karl / When die Anleitung erzeugt wird / Then fragt sie nie nach dem Vornamen, und `einladen` nimmt weiter `vorname` der eingeladenen Person. Tests: `test_anleitung_ohne_namensfrage`, `test_einladen_vorname_bleibt`.
- [x] **AC-7:** Given die Tests nutzen nur Personen der Beispielreisen (plus `kim` in der Testvorbereitung) / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün; weder `MITREISEND` noch ein Zugang mit `rolle` ohne `person` kommt in `engine/tests/` vor.
- [x] **AC-8 (Doku-Teil; Instanz-Tests offen für Phase 8):** Given die Änderung berührt die Konnektor-Schnittstelle / When sie ausgeliefert werden soll / Then laufen vorher die Tests der einbindenden Instanzen mit dem Branch grün; Doku in `docs/konnektor.md` und `docs/auftraege/mehrsprachigkeit/M8.md` nennt den Zugang ohne Namen nicht mehr. Test: `test_doku_nennt_keinen_zugang_ohne_namen` (sucht in beiden Dateien nach Hinweisen auf Vornamen-Abfrage bzw. Zugang ohne Person).

## Dialog

### Runde 1
**Adversary:** Angriff auf Pfade ohne Person. `wer_spricht` liefert ohne `person` sofort None, auch bei gesetzter `rolle`. Geprüft: `werkzeug` (Code reference: engine/konnektor.py:3043) lehnt bei None mit `konnektor.werkzeug.1` ab, bevor irgendein Schreibaufruf läuft; `anleitung` und `werkzeuge_fuer` fallen auf Gast nur zum Lesen zurück (engine/konnektor.py:2991, 3239), schreibende Werkzeuge sind für Gast ausgeblendet und werden im Aufruf ohnehin erneut abgelehnt. Kopieren aus anderer Reise nutzt None als „keine Person dort“ (engine/konnektor.py:1587). Rückfälle `args.get("name"/"vorname")` sind entfernt; `rest`-Filter (engine/konnektor.py:1559) und `args.pop("name")` (Konto-Weg) schlucken überzählige Argumente, `person_einladen` liest `vorname` weiter separat (engine/konnektor.py:1968). Kein Pfad gefunden, der ohne Person schreibt. Sonderfall: Gast-Rückfall in `anleitung` mit `name=None` erzeugt `du_mit_name` mit leerem Namen, aber nur in der Zweig-Reihenfolge, der Gast-Satz kommt nur bei vorhandenem Namen; sonst Hinweis `werkzeug.1`. Unerreichbar über den Konto-Weg, daher ohne Befund.
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Textschlüssel: grep über engine/*.py findet keine Verwendung der neun entfernten Schlüssel (Treffer nur `ausgabe.frage_beantworten.4`, `schreiben.entscheiden.2`, `ontologie_werkzeug.14`, `ausgabe.entscheiden.2`, andere Schlüssel); dynamische Zusammensetzung nicht gefunden. Katalog: Code reference: engine/texte_de.py:2171 und engine/texte_en.py:2170 (`konnektor.werkzeug.1` bleibt, `werkzeug.14` fehlt). Schemas: kein `NAME_FELD` mehr, `name` in `rueckmeldung_geben` weg (Code reference: engine/rueckmeldungen.py:107, `INHALT` bleibt, wird aber im Konnektor mit der Person überschrieben); das verbleibende `name` in engine/konnektor.py:2571 gehört zu verschachtelten Lesetext-Rubriken, kein Top-Level-Feld. Beispielreise: `git diff 71b4beb --stat -- beispiel` leer, `test_texte.py` unverändert (Ausnahmelisten nicht länger). Tests: entfernte Tests in test_gespraech.py, test_brett.py, test_konnektor.py betrafen ausschließlich Zugang ohne Person oder „Name fehlt“ (beide Fälle gibt es nicht mehr); eine Assertion in test_rueckmeldung_kontext_449.py verlor nur `name` aus der Menge (nach Spec). Ersatz: `test_zugang_ohne_person_hat_keinen_zugriff` deckt das Ablehnen ab. Gezielter Lauf: 335 bestanden, 0 fehlgeschlagen (docs/artifacts/m7-426-konnektor-rolle-ohne-person/adversary-test-output.txt), Gesamtlauf laut test-green-output.txt 2477 bestanden. Doku: docs/konnektor.md und M8.md ergänzt bzw. bereinigt (NAME_FELD aus M8 entfernt). Offen für Phase 8: Tests der einbindenden Instanzen (kein BROKEN-Grund).
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Bestätigungen
  Code reference: engine/konnektor.py:3043
  Code reference: engine/texte_de.py:2171
  Code reference: engine/texte_en.py:2170
  Code reference: engine/rueckmeldungen.py:107

Confirmation:
  AC: AC-1
  Code reference: engine/konnektor.py:240
  Evidence: wer_spricht liefert None ohne person; werkzeug lehnt ab
  Status: CONFIRMED
Confirmation:
  AC: AC-2
  Code reference: engine/konnektor.py:2245
  Evidence: NAME_FELD entfernt, vorname nur bei person_einladen
  Status: CONFIRMED
Confirmation:
  AC: AC-3
  Code reference: engine/konnektor.py:1559
  Evidence: name/vorname werden gefiltert, Name aus wer["name"]
  Status: CONFIRMED
Confirmation:
  AC: AC-4
  Code reference: engine/konnektor.py:3239
  Evidence: Gast liest, Schreiben per recht() abgelehnt; Beispielreise unverändert
  Status: CONFIRMED
Confirmation:
  AC: AC-5
  Code reference: engine/texte_de.py:2171
  Evidence: neun Schlüssel in de und en weg, keine Verwendung im Code
  Status: CONFIRMED
Confirmation:
  AC: AC-6
  Code reference: engine/texte_en.py:2170
  Evidence: Anleitung ohne Namensfrage, einladen behält vorname
  Status: CONFIRMED
Confirmation:
  AC: AC-7
  Code reference: engine/tests/conftest.py:100
  Evidence: mcp_intern reicht nur reise/person/sprache durch; kein MITREISEND
  Status: CONFIRMED
Confirmation:
  AC: AC-8
  Code reference: docs/konnektor.md:1
  Evidence: Doku bereinigt; Instanz-Tests offen für Phase 8
  Status: CONFIRMED (Teil)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 335 passed, 0 failed, 0 übersprungen (gezielt); Gesamtlauf 2477 passed
Edge cases: All checked, none broken
Regressions: None found
Checklist: 8/8 points proven (AC-8: Instanz-Tests offen für Phase 8)

## Geprüfte Dateien

- sha256:8e6f9c0aed1ee1cde0ff5aff0e73765771b36e872059803703f210ff0a072f19  docs/konnektor.md
- sha256:d0ba4b2353bad9c514a1ea9723ac2f71069d1077aadd137e0d1235791f199815  engine/konnektor.py
- sha256:d8c2bfa3e6d9df413d148093b165e53be1d0d7dc6960cc320b71197046fdce55  engine/rueckmeldungen.py
- sha256:fc858ac5b4cd3c1ffeab4ed3afb0660ec7ae8dae5da67fb3e9e1558f74130181  engine/tests/conftest.py
- sha256:5e412d973471b8c3e894aaf11fe38d1e90761a9e84f58bb4d01e48a071994bec  engine/texte_de.py
- sha256:95406966837ae02c68659d30e704f8fb164f57f4c359e7918a084e01d81615bf  engine/texte_en.py

## Prüfbasis

- base: 71b4bebacfd491c9d2654c85ed142db8fd71d18b
- blob:26de90960563faf1ccc12fcc0841b8091cb1b51c  docs/konnektor.md
- blob:2274191008f44efe2422f618f30130a02c0574d3  engine/konnektor.py
- blob:3e14e7112dd18ce3f0e0975828e04678f5afb2ed  engine/rueckmeldungen.py
- blob:c0d2e0544ad154028066535ab1f3e08f500df6b5  engine/tests/conftest.py
- blob:3dbd700f762698b68d24998aaacb1346173f09e4  engine/texte_de.py
- blob:2a489628ec9cf4130248ffce38355c183708a5a4  engine/texte_en.py
