# Adversary Dialog — fix-215-altformen
Spec: docs/specs/oberflaeche/altformen-rest-215.md
Datum: 2026-11-05 15:34

## Checkliste
- [x] **AC-1:** (Test 1, 3): Der Reiter heißt im Code `zu-tun`; die Seite beider Beispielreisen zeigt ihn wie bisher. PROVEN
- [x] **AC-2:** (Test 2, 4): Alte Adressen `#offen` (Lesezeichen, Push) öffnen weiter „Zu tun“; neue Push-Meldungen tragen `#zu-tun`. PROVEN
- [x] **AC-3:** (Test 5–9): `neu.py nachziehen` stellt `buchung:` ohne Handschritt um, verliert keinen Buchungsstand, ist idempotent und lässt Reisen ohne das Feld unberührt. PROVEN
- [x] **AC-4:** (Test 10): Ein verbliebenes `buchung:` wird nie still ignoriert. PROVEN
- [x] **AC-5:** (Test 11): `test_texte.py` bleibt grün, Ausnahmelisten nur kürzer. PROVEN
- [x] **AC-6:** (alle Tests): `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün; die Browser-Tests laufen über beide Beispielreisen. PROVEN (Gesamtlauf 1410 grün laut test-green-output.txt, nicht erneut gelaufen; gezielter Lauf 272 grün)
- (nicht Teil der Checkliste) **AC-7:** (Prozess): außerhalb des Dialogs, offen bis Vorspulen (Orchestrator: Instanz-Tests, Schließen von #215)

## Dialog

### Runde 1
**Adversary:** Gezielter Lauf test_altformen_rest_215, test_routen, test_neu, test_push, test_texte: 272 passed in 39.96s, 0 failed, 0 skipped. Danach Angriff auf nachziehen an Kopien beider Beispielreisen in einem Scratch-Ordner (nicht im Repo). Eingespeist in die Beispielreise: U-01 `buchung: gebucht` (hat schon B-01), U-02 `angefragt`, U-03 Freitext „Zusage per Telefon“, U-04 `offen`, A-01 leer, A-02 `gebucht`, A-03 `Gebucht` (Großschreibung), A-04 `true` (YAML-Wahrheitswert); im Stadtwochenende U-01 `angefragt`, A-01 `gebucht`; zusätzlich in der Beispielreise zwei Strecken in Fließform mit `buchung: gebucht` (E-01) und `buchung: angefragt` (E-02).
Ergebnisse: (1) Trockenlauf (schreiben=False) verändert die Datei nicht (Assertion), liefert dieselben Meldungen und dieselben Nummern wie der echte Lauf (B-04 bis B-08), ids.yaml wird im Trockenlauf nicht angelegt. (2) Echter Lauf: offen/leer löscht nur den Schlüssel, ohne Buchung; U-01 behält B-01 und bekommt keine zweite Buchung, Meldung nennt B-01; angefragt/gebucht werden Buchungen mit fuer, status und quelle (Katalogtext); Freitext wird gebucht mit notiz und OFFEN-Meldung „bitte prüfen“. ids.yaml bekommt B: 8 (Beispielreise ohne ids.yaml: Datei wird angelegt; Stadtwochenende mit W und F: nur B ergänzt, B: 3). (3) Zweiter Lauf: leere Meldungsliste, Datei unverändert (idempotent). (4) Strecken in Fließform: vor nachziehen bricht der Bau mit der Katalogmeldung (je Ding eine Meldung, E-01 und E-02, nennt neu.py nachziehen), nach nachziehen baut er, Strecken-Stand unverändert gebucht/angefragt, Unterkunft U-01 gebucht. (5) Das Diff der Datei zeigt nur die neuen Buchungsblöcke, Kommentare bleiben.
Punkt (f): Die Leerzeile vor `tage:` steht nach dem Lauf vor den neuen Buchungen (B-04 …), `tage:` folgt direkt auf die letzte neue Buchung. Die Datei bleibt gültig und baut; rein optisch, kein Verlust (F002, LOW).
Grenzfälle der Freitext-Regel: `Gebucht` und `true` werden Freitext (gebucht, notiz „Gebucht“/„True“) mit Prüf-Meldung. Das erhält den alten Stand (die Vorlage rechnete alles außer offen/angefragt als gebucht) und entspricht der Spec.
**Implementierer:** (nicht beteiligt, Isolation)

### Runde 2
**Adversary:** Zweiter Angriff auf Route, Prüfung, Textkatalog, Push.
(b) routen.py prüft alle drei Gruppen (Unterkünfte, Aufenthalte, Strecken) in `buchungen_pruefen`; `buchung_von` liest das Eingabefeld nicht mehr. Der Bau bricht (belegt in Runde 1 für Strecken; Unterkunft und Aufenthalt gehen durch dieselbe Schleife, Test 10 deckt beide Reisen).
(c) vorlage.html: `offen` kommt nur noch in `ROUTE_ALIAS` vor; `route()` normalisiert `#offen` und ersetzt die Adresszeile per `history.replaceState` (kein hashchange-Ereignis, kein neuer Verlaufseintrag); `START` normalisiert `reise.json start` über `routeName`; `offenZahl()` sucht `#zu-tun`; die Badge hängt an `k === "zu-tun"`. Alle Zweige `zeigeReiter("zu-tun")`. Keine weitere Fundstelle von `#offen` in Vorlage, Service Worker, bauen.py, konnektor.py, betrieb/ (Rest-Treffer sind Aufgabenstatus und Chipzustand, laut Spec gültig).
Fund: `routeName` schlägt per `ROUTE_ALIAS[h]` auf einem normalen Objekt nach. Ein Hash wie `#constructor`, `#toString` oder `#__proto__` liefert einen Funktions- oder Objektwert (mit node geprüft), `routeName(h) !== h` ist wahr, und `route()` schreibt die Adresszeile auf den Text der Funktion um. Nur bei handgetippten oder fremden Links, keine Datenfolge, aber ein echter Fehler der neuen Alias-Logik (F001, LOW). Behebung: `Object.hasOwn(ROUTE_ALIAS, h) ? ROUTE_ALIAS[h] : h` oder eine Map.
(d) push.py: `ziel = "zu-tun"` nur wenn alle Einträge meldung/rueckmeldung/aufgabe sind, sonst leer; Test in test_push grün; `#offen`-Altadresse über Alias (Browser-Test pwa_browser).
(e) Textkatalog: Schlüssel `pruefung.routen.buchung_feld`, `pruefung.neu.nachziehen.buchung`, `…buchung_entfernt`, `…buchung_vorhanden`, `…buchung_pruefen`, `inhalt.nachziehen.buchung_quelle` in beiden vorhandenen Sprachen (de, en; weitere texte_*.py gibt es nicht); test_texte grün. Die Umstellungsmeldungen laufen in der Sprache der Reise.
Regression: `buchung_von` hat Aufrufer in routen.py für Strecken, Aufenthalte, Unterkünfte, alle übergeben did; Dinge mit geltender Buchung sind unverändert, ohne Buchung gilt „offen“ bei buchbarer Art. Sonstige Schreibwege (schreiben.py, konnektor.py) erzeugen kein `buchung:` an Dingen (grep). Unbelegt, da nicht prüfbar: ob echte Reisen das Feld nutzen (AC-7).
Nebenbefund, kein Defekt: `naechste_id` erhöht ids.yaml sofort, routen.yaml wird erst am Ende gespeichert; bricht ein späterer Schritt ab, bleibt eine Nummer ungenutzt (IDs werden nie neu vergeben, laut ids.yaml-Kopf gewollt).
**Implementierer:** (nicht beteiligt, Isolation)

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/vorlage.html:1150
  Description: `ROUTE_ALIAS` ist ein normales Objekt, `routeName(h)` (Zeile 1151) schlägt `ROUTE_ALIAS[h]` ohne Eigenschaftsprüfung nach; in `route()` (Zeile 5079) führt das bei `#constructor`, `#toString`, `#__proto__` dazu, dass `h` ein Funktions- oder Objektwert wird und die Adresszeile auf den Funktionstext umgeschrieben wird.
  Spec requirement: AC-2 — nur `#offen` wird auf `#zu-tun` umgeleitet, andere Adressen bleiben unverändert.
  Conflict: Fremde Hashes werden verändert; keine Datenfolge, nur handgetippte Links.
  Remediation: `Object.hasOwn(ROUTE_ALIAS, h) ? ROUTE_ALIAS[h] : h` oder `new Map`.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:859
  Description: `buchung_nachziehen` hängt neue Buchungen an `buchungen:` an; die Leerzeile, die zuvor `tage:` abgesetzt hat, steht danach vor den neuen Buchungen, `tage:` folgt direkt.
  Spec requirement: AC-3 — Kommentare und Form der Datei bleiben.
  Conflict: Nur optisch; Datei bleibt gültig, baut, zweiter Lauf ändert nichts, kein Kommentar geht verloren.
  Remediation: Optional; nicht blockierend.

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/vorlage.html:1147
  Evidence: REITER-Eintrag, REIHE (Zeile 1157), START (Zeile 1154), Zweige in route() und zeigeReiter tragen `zu-tun`; Browser-Tests über beide Beispielreisen grün (Gesamtlauf 1410 grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-1
  Code reference: engine/bauen.py:1419
  Evidence: Symbolzuordnung `"zu-tun": "list-checks"`, der Reiter hat sein Symbol (Test test_symbol_und_pushziel_heissen_zu_tun).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/push.py:313
  Evidence: Ziel `zu-tun` für reine Meldungs-/Rückmeldungs-/Aufgaben-Pushes; alte Adresse `#offen` wird in route() (vorlage.html:5079) per replaceState umgeleitet; pwa_browser-Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/neu.py:818
  Evidence: nachziehen ruft buchung_nachziehen vor dem Speichern von routen.yaml; Szenarien offen, leer, angefragt, gebucht, Freitext, vorhandene Buchung, Strecke/Aufenthalt/Unterkunft, mehrere Dinge, Trocken- und echter Lauf, zweiter Lauf und ids.yaml in Scratch-Kopien beider Beispielreisen wie erwartet (Runde 1).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/routen.py:696
  Evidence: Schleife über Unterkünfte, Aufenthalte, Strecken meldet jedes verbliebene `buchung` als Fehler; Bau bricht mit der Katalogmeldung (Runde 1, Strecken in Fließform belegt).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/routen.py:1840
  Evidence: `buchung_von` ohne Zweig für das Eingabefeld; Stand nur aus geltender Buchung oder „offen“ bei buchbarer Art.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/texte_de.py:2591
  Evidence: Prüfschlüssel, Umstellungsmeldungen (Zeilen 2867 bis 2870) und Quelltext (Zeile 2991) vorhanden; test_texte grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/texte_en.py:2590
  Evidence: dieselben Schlüssel in Englisch (Quelle Zeile 2990); weitere Sprachdateien existieren nicht; test_texte grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/routen.py:1834
  Evidence: Gesamtlauf docs/artifacts/fix-215-altformen/test-green-output.txt: 1410 passed; gezielter Lauf 272 passed, 0 failed, 0 übersprungen.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

Kein Sprachprofil konfiguriert (`precondition_origins.default_lang`); keine Tabelle angehängt. Geprüfte Schreibstelle des Felds `buchung:` an Dingen: nur `neu.buchung_nachziehen` löscht es (Bedingung davor: Feld vorhanden, in routen.yaml als Dict); Test dafür: test_altformen_rest_215 Tests 5 bis 9, zusätzlich Szenarien in Runde 1. Produktionscode schreibt es nirgends neu (grep schreiben.py, konnektor.py).

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hat den Angriff überstanden; zwei LOW-Funde (F001 Prototyp-Lookup im Alias, F002 Leerzeilenlage), beide nicht blockierend.
Tests: 272 passed (gezielt), 1410 passed (Gesamtlauf), 0 failed, 0 übersprungen
Edge cases: geprüft, keiner bricht die Spec
Regressions: keine gefunden
Checklist: 6/6 prüfbare Punkte bewiesen (AC-1 bis AC-6); AC-7 ist Prozess und liegt außerhalb des Dialogs, offen bis Vorspulen

## Geprüfte Dateien

- sha256:e0eb820397e2515c2ac00772534cd5d621127eda730af03decdcdae400825c78  engine/bauen.py
- sha256:3cb21cf9cda05b6446a05e94518190da0df8c8c77080b8d31766e9b77265b496  engine/neu.py
- sha256:9b707a6edff857182dddd09cf26917d3973297f92f54116b25e9958a6e4f9c47  engine/push.py
- sha256:2e60aafc0b9c1e0de51cb3c58330ad758a9d6220eeb358f81996d62b7f2e83a3  engine/routen.py
- sha256:447a2ed32bb6c9c258b3cd7b9e5d77ff921f223e33a7485f35f4429d542ace44  engine/texte_de.py
- sha256:5a04e5eea55badb44f4513643ef123941efc55557a820d2f3fb2c24bf0da1ef2  engine/texte_en.py
- sha256:196d7a2083d5016d056007b5473364fabfe9f282bd9333e43c590ac719ca6348  engine/vorlage.html

## Prüfbasis

- base: c7bb82acf25652dd2d1b741aae5bda81ecef4434
- blob:706aa65f3b6a1ed82c0a3dd5d87aefc97ca4f16e  engine/bauen.py
- blob:9bfd0df25af502b5773392e533b7ff59c494fa7f  engine/neu.py
- blob:02dbdb8b898c9937ceb0291c7c8b43743904b2a9  engine/push.py
- blob:908343fcdbb23d0b551e18238eeaa24fa572b6ee  engine/routen.py
- blob:7c40039bfa3de5628bd495436b4799ae90613f55  engine/texte_de.py
- blob:53d4add7170f3f70385a2df1c80f68f63e34dd85  engine/texte_en.py
- blob:5a292e587d244524adf0d51c5348c610d603a0fa  engine/vorlage.html

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)
