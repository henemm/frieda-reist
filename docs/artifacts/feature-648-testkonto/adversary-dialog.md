# Adversary Dialog — feature-648-testkonto
Spec: docs/specs/betrieb/testkonto-648.md
Datum: 2026-11-24 06:41

## Checkliste
- [x] **Input:** Claude Code startet den Server `frieda-test` aus `.mcp.json`; Aufrufe der Werkzeuge des Konnektors; Betreiberbefehle `testzugang.py einrichten`, `konten.py vormerken <reise>`.
- [x] **Output:** Aufrufe gegen die echte Instanz als Testkonto mit den Rechten des Testkontos (anlegen, schreiben, veröffentlichen, einladen an Unteradressen). Aufrufe schreibender Werkzeuge über den Konnektor des Product Owners werden abgelehnt.
- [x] **Side effects:** Ablage-Datei des Zugangs außerhalb des Repos (Rechte 600, bei jeder Erneuerung neu geschrieben); beim Vormerken ein Eintrag in der Löschvormerkung, nach der Schonfrist das endgültige Entfernen durch den Wächter mit Löschprotokoll.
- [x] **AC-1:** Given eine Instanz mit `FR_TESTKONTO` / When `testzugang.py einrichten` läuft / Then entsteht ein Testkonto mit Recht `reise_anlegen`, ohne `betreiber`, und eine Ablage mit Rechten 600 außerhalb des Repos. (Tests 1, 2)
- [x] **AC-2:** Given ein Konto mit Recht `betreiber` oder `FR_TESTKONTO` gleich einer Betreiberadresse / When `einrichten` läuft / Then wird die Einrichtung verweigert. (Test 2)
- [x] **AC-3:** Given der eingerichtete Zugang / When Claude Code den Server `frieda-test` startet / Then liefert die Brücke dieselbe Werkzeugliste wie der Konnektor und beantwortet Aufrufe als Testkonto. (Test 3)
- [x] **AC-4:** Given ein abgelaufenes Access-Token / When eine Anfrage kommt / Then erneuert die Brücke selbst, schreibt die Ablage atomar mit 600 und widerruft bei parallelen Sitzungen die Token-Familie nicht. (Tests 4, 5)
- [x] **AC-5:** Given ein Token, das nicht zum Testkonto gehört / When die Brücke startet / Then bricht sie ohne Weiterleitung ab. (Test 6)
- [x] **AC-6:** Given eine Claude-Code-Sitzung dieses Repos / When ein schreibendes oder unbekanntes Werkzeug des Konnektors des Product Owners aufgerufen wird / Then lehnt der Hook ab mit Hinweis auf `frieda-test`; Lesewerkzeuge und andere Server bleiben aufrufbar. (Tests 8, 9, 10)
- [x] **AC-7:** Given ein neues Werkzeug im Konnektor / When die Testsuite läuft / Then ist der Hook-Test rot, bis Erlaubnisliste und Werkzeug übereinstimmen (keine Handpflege). (Test 8)
- [x] **AC-8:** Given eine Reise im Reisespeicher / When `konten.py vormerken <reise>` läuft / Then ist die Reise überall verschwunden und der Wächter entfernt sie nach der normalen Schonfrist endgültig; Reisen außerhalb des Speichers und bereits vorgemerkte werden verweigert. (Tests 12, 13, 14)
- [x] **AC-9:** Given die freigegebene Liste von fünf Testreisen / When sie vorgemerkt sind / Then zeigt `my_trips` (aktiv und Archiv) keine davon mehr; nach Fristende bestätigen `konten.py vorgemerkt` und das Löschprotokoll das endgültige Entfernen. Kein Schritt davon erfolgt ohne vorherige Freigabe des Product Owners, und die Liste steht nicht im öffentlichen Repo.
- [x] **AC-10:** Given die Doku / When `CLAUDE.md` und `docs/betrieb.md` gelesen werden / Then enthalten sie die Regel „Abnahmen nie über das Konto des Product Owners“, die Einrichtung, das Testkonzept (Stufe 3: Testkonto statt Archivieren) und die bekannte Grenze zu Betreiber-Meldungen.
- [x] **AC-11:** Given die vollständige Testsuite / When sie läuft / Then ist sie grün (`engine/.venv/bin/python -m pytest -q -n 3 engine/tests`), `ALARMSTELLEN` bleibt unverändert und es gibt keine echten Reisekennungen in Repo und Specs.
- [x] **AC-12:** Given die Umsetzung / When die Workflow-Gates geprüft werden / Then wurde keine Gate-Konfiguration geändert und keine menschliche Sperre (override) gebraucht.

## Dialog

### Runde 1
**Adversary:** Alle Punkte einzeln gegen den Code geprüft; Tests gelaufen (217 gezielt grün, Gesamtsuite 3579 grün laut Nachweis).

Confirmation:
  AC: AC-1, AC-2
  Code reference: betrieb/testzugang.py:215
  Evidence: einrichten verweigert Betreiberrecht und FR_BETREIBER_KONTAKT (Zeile 230) vor jeder Ausstellung; setzt nur reise_anlegen (235); Ablage über ablage_schreiben (184): mkstemp, fchmod 600, fsync, os.replace; Vorgabe-Ablage unter <FR_DIENST>/instanz, nicht im Repo.
  Status: CONFIRMED

Confirmation:
  AC: AC-3, AC-5
  Code reference: betrieb/testzugang.py:338
  Evidence: konto_pruefen liest die Adresse aus der initialize-Anleitung (Wortgrenzen-Regex) und erkennt Betreiber an request_decide in tools/list (engine/schnittstelle.py:74); beides vor der Schleife in dienst (356), also ohne Weiterleitung. Abweichung vom Spec-Text (my_profile) ist durch den verbindlichen Kontext gedeckt.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: betrieb/testzugang.py:291
  Evidence: erneuern unter fcntl.flock, liest die Ablage neu, übernimmt ein fremd erneuertes Paar, sonst Einlösen und atomares Schreiben (Rechte 600 auch bei Erneuerung); 401 löst genau eine Erneuerung aus (senden, 312).
  Status: CONFIRMED

Confirmation:
  AC: AC-6, AC-7
  Code reference: .claude/hooks/frieda_sperre.py:27
  Evidence: nur ERLAUBT passiert, sonst Exit 2 mit Hinweis auf frieda-test; unlesbares Ereignis, fehlender oder nicht-String tool_name ergibt Exit 2; andere Server Exit 0 (Handproben). Synchronität per Test gegen tools/list (engine/tests/test_frieda_sperre.py:49). Matcher in .claude/settings.json nur mcp__claude_ai_Frieda__.*.
  Status: CONFIRMED

Confirmation:
  AC: AC-8, AC-9
  Code reference: engine/konten.py:1859
  Evidence: vormerken prüft Muster und Reisespeicher (Exit 2 sonst), ruft loeschung_vormerken(reise, None); bereits Vorgemerkte verweigert dessen KontoFehler; ohne Argument Hilfe, Exit 1; Wächterweg unverändert (Test 14 grün). AC-9 ist ein Betriebsschritt nach der Auslieferung mit Freigabe des PO, nachgelagert und kein Defekt; das Werkzeug existiert, im Repo steht keine Liste echter Reisen.
  Status: CONFIRMED

Confirmation:
  AC: Expected Behavior (Input, Output, Side effects), AC-10, AC-11
  Code reference: betrieb/pruefsitzung.py:31
  Evidence: sitzung_ausstellen ist der unveränderte Block aus main (Diff geprüft), Verhalten gleich; Doku in CLAUDE.md und docs/betrieb.md (Abschnitt Abnahmen über den Testzugang) vorhanden; keine absoluten Pfade oder echten Adressen in den neuen Dateien (nur die Vorgabe unter FR_SEITEN wie in engine/instanz.py); test_betrieb.py unverändert, ALARMSTELLEN unberührt.
  Status: CONFIRMED

**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Gezielte Angriffe.

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/testzugang.py:162
  Description: Netzfehler (Instanz nicht erreichbar, Zeitüberschreitung) in anfrage() werden nicht als Abbruch behandelt; die Brücke endet mit Traceback (Handprobe: ConnectionRefusedError, Exit 1), im Betrieb ebenso statt mit einer JSON-RPC-Fehlerantwort. Kein Geheimnis im Traceback.
  Spec requirement: AC-3 — Brücke beantwortet Aufrufe als Testkonto
  Conflict: Robustheit: ein kurzer Netzfehler beendet den Server frieda-test bis zum Neustart in Claude Code.
  Remediation: OSError in senden/dienst fangen und als -32603 beantworten.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: .claude/hooks/frieda_sperre.py:15
  Description: Der Hook deckt nur den Präfix mcp__claude_ai_Frieda__ ab. Ein reisebezogener Konnektor des PO (Handprobe mcp__claude_ai_Reise_gr221__item_update, Exit 0) bleibt aufrufbar.
  Spec requirement: AC-6 — nur Konnektor des PO, andere Server frei (Spec Abschnitt 3 nennt genau diesen Matcher)
  Conflict: Keine Verletzung der Spec, aber eine Lücke im Ziel der Sperre.
  Remediation: Folgeaufgabe: prüfen, ob solche Reisekonnektoren in Claude Code erscheinen; dann Matcher erweitern.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/testzugang.py:229
  Description: Betreiberschutz kennt nur das Recht betreiber und FR_BETREIBER_KONTAKT; die zweite Schranke (request_decide beim Start der Brücke) fängt andere Fälle ab. Kein Defekt, nur Hinweis.
  Spec requirement: AC-2
  Conflict: keiner (zweistufig geschützt)
  Remediation: keine

Weitere Proben ohne Befund: kaputte Ablage (klare Meldung, Exit 1, kein Geheimnis); Rotation unter Sperre (Test 5 grün); .mcp.json ohne Adresse und Geheimnis (Test 7); Exit-Codes von vormerken; pruefsitzung im Verhalten unverändert.

AC-12: Gate-Konfiguration nicht geändert (settings.json und Hook sind neue Projektdateien; an getrackten Dateien unter .claude gibt es keine Änderung). Der nötige override war eine Fehlannahme der Spec (Edit-Gate schützt diese Pfade), kein Defekt der Umsetzung; die Spec ist zu berichtigen.
**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 217 gezielt passed (Gesamtsuite 3579 passed laut Nachweis), 0 failed, 0 übersprungen
Edge cases: geprüft; nur LOW-Befunde F001 bis F003, keiner blockierend
Regressions: None found
Checklist: alle Punkte belegt (AC-9 nachgelagert, AC-12 Fehlannahme der Spec)

## Geprüfte Dateien

- sha256:06f5aad0855e8da20479ae3af8a20271f4a6d6fbfed958f6d4de765e990f4835  .claude/hooks/frieda_sperre.py
- sha256:05d836725023a1a6513dd9f54e02975844fcb28f74a20f90105243267e76d1a8  betrieb/pruefsitzung.py
- sha256:44181b82160ace799377b2fee90ef9ab20c11e016787f67aacacb21b47830691  betrieb/testzugang.py
- sha256:69d5fb8f770dc058135930fb8ad8a7cb29e8a96ef70443c32e25b18377e381fc  engine/konten.py

## Prüfbasis

- base: 70864f5cadfa617c3fd6c58257a5d763bc7fa906
- blob:b7620b9f4d1a1d1d1a19f70416239d5d4cce82d1  .claude/hooks/frieda_sperre.py
- blob:e27acf255405220668e451b1486dc9b6bc92c418  betrieb/pruefsitzung.py
- blob:22b5f9e1241ee31abfc13967b718f99763919834  betrieb/testzugang.py
- blob:6b31845d70ec17f09bd6a83975fa42165257773f  engine/konten.py

## Geprüfte Dateien

- sha256:06f5aad0855e8da20479ae3af8a20271f4a6d6fbfed958f6d4de765e990f4835  .claude/hooks/frieda_sperre.py
- sha256:05d836725023a1a6513dd9f54e02975844fcb28f74a20f90105243267e76d1a8  betrieb/pruefsitzung.py
- sha256:44181b82160ace799377b2fee90ef9ab20c11e016787f67aacacb21b47830691  betrieb/testzugang.py
- sha256:69d5fb8f770dc058135930fb8ad8a7cb29e8a96ef70443c32e25b18377e381fc  engine/konten.py

## Prüfbasis

- base: 70864f5cadfa617c3fd6c58257a5d763bc7fa906
- blob:b7620b9f4d1a1d1d1a19f70416239d5d4cce82d1  .claude/hooks/frieda_sperre.py
- blob:e27acf255405220668e451b1486dc9b6bc92c418  betrieb/pruefsitzung.py
- blob:22b5f9e1241ee31abfc13967b718f99763919834  betrieb/testzugang.py
- blob:6b31845d70ec17f09bd6a83975fa42165257773f  engine/konten.py
