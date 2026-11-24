---
entity_id: testkonto-648
type: feature
created: 2026-11-24
updated: 2026-11-24
status: draft
workflow: feature-648-testkonto
version: "1.0"
tags: [testkonto, abnahme, konnektor, mcp, oauth, sperre, loeschen, betrieb]
---

# Testkonto für Abnahmen über den Konnektor (#648)

Grundlage: `docs/context/feature-648-testkonto.md` (Anfrage, Befunde, Entscheidung des Tech Leads), Issue #648, #381 (Löschen mit Frist), #273 (Testkonzept), ADR-0001, ADR-0005 (Konten und Anmeldung).

## Approval

- [ ] Approved

(Die einzige Produktentscheidung, die Freigabe der Löschliste, wird im Ablauf unter „Implementation Details“, Abschnitt 5 und Schritt (7) der Reihenfolge, vor dem Vormerken beim Product Owner eingeholt. Sie ist keine offene Frage dieser Spec.)

## Purpose

Abnahmen über den Konnektor liefen bisher über das Konto des Product Owners und haben dort Testreisen hinterlassen. Künftig bekommt Claude Code einen eigenen Konnektor-Zugang `frieda-test`, der gegen dieselbe Instanz mit einem eigenen Testkonto arbeitet, ohne dass der Product Owner etwas tun muss. Eine Sperre verhindert den Rückfall: Schreibende Werkzeuge des Konnektors des Product Owners sind in Claude-Code-Sitzungen dieses Repos nicht mehr aufrufbar. Die vorhandenen Testreisen im Konto des Product Owners werden nach Freigabe über den normalen Löschweg entfernt.

## Source

- **File:** `betrieb/testzugang.py` (neu), `.claude/hooks/frieda_sperre.py` (neu), `engine/konten.py`, `betrieb/pruefsitzung.py`
- **Identifier:** Befehle `testzugang.py einrichten` und `testzugang.py dienst`; Hook `frieda_sperre`; Betreiberbefehl `konten.py vormerken <reise>` (Funktion `loeschung_vormerken`, `reise_vorgemerkt`)

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/oauth.py` | Modul | Echter OAuth-Weg: dynamische Registrierung (Loopback-Redirect), PKCE S256, Zustimmung per POST, Token |
| `engine/konten.py` | Modul | Konten und Rechte (`reise_anlegen`, `betreiber`), OAuth-Ablage (`oauth_code_anlegen`, `_tokens_ausstellen`; Access-Token 1 Stunde, Refresh-Token 90 Tage mit Rotation), Löschvormerkung (`loeschung_vormerken`, `reise_vorgemerkt`, `faellige_loeschungen`) |
| `engine/konnektor.py` und `engine/schnittstelle.py` | Modul | Werkzeugliste mit `annotations.readOnlyHint` und englischen Namen; Endpunkt `POST /mcp` (JSON-RPC, JSON-Antwort, nur `Authorization: Bearer`) |
| `betrieb/pruefsitzung.py` | Skript | Sitzung ausstellen; wird zur gemeinsamen Hilfsfunktion, die `testzugang.py` mitnutzt |
| `engine/instanz.py` und `<FR_DIENST>/instanz/einstellungen.env` | Modul, Datei | Instanzwerte `FR_KN_ADRESSE`, `FR_KONTEN`, neu `FR_TESTKONTO`, `FR_TESTZUGANG` |
| `engine/waechter.py` (`loeschungen_ausfuehren`) | Modul | Entfernt vorgemerkte Reisen nach `FR_LOESCHFRIST_TAGE` (Vorgabe 14) endgültig mit Löschprotokoll; unverändert |
| `engine/reisespeicher.py` (`reise_entfernen`) | Modul | Endgültiges Entfernen im Reisespeicher; unverändert |
| Claude Code (`.mcp.json`, `.claude/settings.json`, PreToolUse-Hook) | Werkzeug | Einbinden der Brücke und der Sperre; nur Standardbibliothek im Hook |
| Postfach für das Testkonto in der Mailinfrastruktur | extern | Eigenes Postfach mit Unteradressen für Einladungen; Issue im Infrastruktur-Repo, außerhalb dieses Repos |
| Einstellungen der privaten Instanz | extern | Wert `FR_TESTKONTO` und die Freigabeliste der Löschung (nur dort) |

## Scope

### Im Scope

1. **Testzugang einrichten:** `betrieb/testzugang.py einrichten` legt das Testkonto (Adresse `FR_TESTKONTO`) an oder findet es, vergibt das Recht `reise_anlegen`, nie `betreiber`, stellt eine kurze Sitzung aus und durchläuft den echten OAuth-Ablauf gegen die Instanz. Es legt `client_id` und Refresh-Token außerhalb des Repos ab.
2. **Brücke:** `betrieb/testzugang.py dienst` ist ein stdio-MCP-Server, der JSON-RPC an `<FR_KN_ADRESSE>/mcp` weiterleitet. Er erneuert Tokens selbst (Rotation) und prüft beim Start, dass das Token zum Testkonto gehört.
3. **Einbindung in Claude Code:** `.mcp.json` mit Server `frieda-test` (Befehl ohne Adresse und ohne Geheimnis) und `.claude/settings.json` mit Freigabe des Servers und Hook-Eintrag.
4. **Sperre:** `.claude/hooks/frieda_sperre.py` (PreToolUse auf `mcp__claude_ai_Frieda__.*`) lässt am Konnektor des Product Owners nur Werkzeuge mit `readOnlyHint: true` zu. Ein Test hält die Erlaubnisliste gegen die Werkzeugliste des Konnektors synchron.
5. **Betreiberbefehl `konten.py vormerken <reise>`:** Löschen vormerken ohne Sitzung, mit normaler Schonfrist.
6. **Aufräumen:** Nach Freigabe durch den Product Owner werden die fünf Testreisen (zwei aktiv, drei archiviert) in seinem Konto vorgemerkt; der Wächter entfernt sie endgültig.
7. **Doku:** Regel in `CLAUDE.md`, Einrichtung und Testkonzept in `docs/betrieb.md` (Stufe 3 „Testkonto statt Archivieren“), `betrieb/einstellungen.beispiel`.

### Nicht im Scope (Out of Scope)

- Kein zweites Claude-Konto und keine Umstellung der Anmeldung des Konnektors in der Claude-App (ausgeschlossen vom Product Owner).
- Keine Hintertür im Dienst: kein fester Token, kein Sonderpfad im Konnektor, keine Änderung an `oauth.py` oder `konnektor.py`.
- Keine Wegwerf-Instanz für Abnahmen; sie bleibt den automatischen Tests (pytest) vorbehalten.
- Keine Verkürzung der Löschfrist und kein Sofort-Löschen; Altreisen brauchen keinen Sonderweg.
- Keine Änderung der Workflow-Gates oder ihrer Konfiguration; kein Schritt dieser Spec braucht eine menschliche Sperre (override).
- Keine Sperre in der Claude-App des Product Owners; die Sperre wirkt nur in Claude-Code-Sitzungen dieses Repos.
- Kein Postfach und kein Instanzwert im Repo: Das Postfach entsteht über ein Issue im Infrastruktur-Repo, `FR_TESTKONTO` steht in den Einstellungen der privaten Instanz.
- Keine echten Reisen, Namen echter Personen, Serveradressen oder absoluten Server-Pfade im öffentlichen Repo; es gelten die Platzhalter `<Testreise A>` bis `<Testreise E>`, `<FR_DIENST>`, `<Instanzadresse>`.

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/testzugang.py` | CREATE | Befehle `einrichten` (Konto, OAuth, Ablage) und `dienst` (stdio-Brücke, Erneuern, Kontoprüfung); Standardbibliothek, `einrichten` mit Engine-Import wie `pruefsitzung.py` |
| `betrieb/pruefsitzung.py` | MODIFY | Sitzung ausstellen als gemeinsame Hilfsfunktion, ohne Verhaltensänderung des Befehls |
| `engine/konten.py` | MODIFY | Betreiberbefehl `vormerken <reise>` in der CLI (`main`); Prüfungen und Hilfetext |
| `.mcp.json` | CREATE | Server `frieda-test`: `python3 betrieb/testzugang.py dienst` |
| `.claude/settings.json` | CREATE | Freigabe des Servers `frieda-test`, PreToolUse-Hook auf `mcp__claude_ai_Frieda__.*` |
| `.claude/hooks/frieda_sperre.py` | CREATE | Sperre mit Erlaubnisliste der Lesewerkzeuge; nur Standardbibliothek |
| `betrieb/einstellungen.beispiel` | MODIFY | `FR_TESTKONTO` (Adresse des Testpostfachs, auskommentiert mit Beispielwert), `FR_TESTZUGANG` (Ablageort) |
| `engine/tests/test_testzugang.py` | CREATE | Einrichten, Brücke, Erneuern, Rotation, falsches Konto, Rechte 600, Betreiber-Verweigerung |
| `engine/tests/test_frieda_sperre.py` | CREATE | Hook gegen die Werkzeugliste des Konnektors; andere Server unberührt |
| `engine/tests/test_konten_vormerken.py` | CREATE | Betreiberbefehl `vormerken`: Erfolg, unbekannte und bereits vorgemerkte Reise |
| `CLAUDE.md` | MODIFY | Regel „Abnahmen nie über das Konto des Product Owners, immer über `frieda-test`“ |
| `docs/betrieb.md` | MODIFY | Einrichtung des Testzugangs, Testkonzept Stufe 3, Betreiberbefehl `vormerken`, Hinweis zur Sperre |

### Estimated Changes

- Files: 12
- LoC: +450/-20 (davon rund 220 Tests)

## Implementation Details

Technischer Ansatz wie in der Analyse (`docs/context/feature-648-testkonto.md`), verbindlich. Code gehört in die genannten Dateien; hier stehen nur die Verträge.

### 1. Einrichten (`testzugang.py einrichten`)

- Liest die Instanzwerte wie `pruefsitzung.py` (Engine-Import, `FR_KN_ADRESSE`, `FR_KONTEN`, `FR_TESTKONTO`, `FR_TESTZUGANG`). Fehlt `FR_TESTKONTO`, bricht der Befehl mit klarer Meldung ab.
- **Schutz vor Betreiberrechten:** Der Befehl verweigert die Einrichtung, wenn das Konto das Recht `betreiber` hat oder `FR_TESTKONTO` gleich einer Betreiberadresse ist. Das Testkonto bekommt ausschließlich `reise_anlegen`.
- Stellt über die gemeinsame Hilfsfunktion aus `pruefsitzung.py` eine kurze Sitzung für das Testkonto aus und führt damit den OAuth-Ablauf wie die Claude-App aus: dynamische Registrierung mit Loopback-Redirect, `/authorize` mit Sitzungs-Cookie, Zustimmung per POST `aktion=erlauben` mit Herkunftsprüfung, Code gegen Token (PKCE S256). Vorlage ist `verbinden()` in `engine/tests/test_oauth.py`.
- **Ablage:** `client_id` und Refresh-Token liegen in einer Datei außerhalb des Repos (Pfad aus `FR_TESTZUGANG`, Vorgabe unter `<FR_DIENST>`), Rechte 600, geschrieben atomar (temporäre Datei, `fsync`, Umbenennen). Nichts davon wird ausgegeben oder protokolliert.
- Mehrfaches Ausführen ist unschädlich: ein vorhandener, noch gültiger Zugang wird ersetzt, der alte Refresh-Token widerrufen.

### 2. Brücke (`testzugang.py dienst`)

- Liest JSON-RPC-Zeilen von stdin, schickt jede als `POST <FR_KN_ADRESSE>/mcp` mit `Authorization: Bearer <Access-Token>` und schreibt die JSON-Antwort nach stdout. Benachrichtigungen ohne Antwort bleiben ohne Ausgabe.
- **Erneuern:** Ist das Access-Token abgelaufen oder antwortet der Dienst mit 401, löst die Brücke den Refresh-Token ein (Rotation: zweites Einlösen derselben Token-Familie widerruft sie, daher darf kein zweiter Prozess gleichzeitig erneuern). Dazu hält sie eine Dateisperre (`fcntl`) auf der Ablage, liest die Datei unter der Sperre neu (ein anderer Prozess kann bereits erneuert haben) und schreibt das neue Paar atomar mit Rechten 600.
- **Kontoprüfung beim Start:** Die Brücke ruft `my_profile` (Kontoadresse) ab. Weicht die Adresse von `FR_TESTKONTO` ab, bricht sie ohne Weiterleitung ab, mit einer Meldung auf stderr. Dasselbe gilt, wenn das Konto Betreiber ist.
- Läuft mit der Standardbibliothek (`urllib`, `json`, `fcntl`); die Adresse und der Ablageort kommen aus dem Instanzwert, nicht aus `.mcp.json`.

### 3. Sperre (`.claude/hooks/frieda_sperre.py`)

- Der Hook liest das Hook-Ereignis (JSON auf stdin) und prüft den Werkzeugnamen `mcp__claude_ai_Frieda__<name>`.
- Die Erlaubnisliste wird nicht von Hand gepflegt: Ein Test vergleicht sie mit der Werkzeugliste des Konnektors. Erlaubt sind genau die Werkzeuge mit `readOnlyHint: true` (englische Namen laut `schnittstelle.py`). Unbekannte oder neue Werkzeuge sind gesperrt, bis der Test und die Liste sie kennen.
- Abgelehnt wird mit Exit-Code 2 und einem Hinweis auf `frieda-test`. Lesen über den Konnektor des Product Owners bleibt erlaubt. Andere MCP-Server, insbesondere `frieda-test`, sind unberührt (der Hook hängt nur an `mcp__claude_ai_Frieda__.*`).
- Nur Standardbibliothek.
- **Nachtrag #670:** Die Erlaubnisliste umfasst auch `my_trips` und `my_profile`; `calendar` bleibt gesperrt, weil es mit `neu=true` den Kalenderlink erneuert, und die Kontaktadresse des Betreibers (`FR_BETREIBER_KONTAKT`) liest `einrichten` auch aus `<FR_DIENST>/konten.env`.

### 4. Betreiberbefehl `konten.py vormerken <reise>`

- Ruft `loeschung_vormerken` ohne Sitzung auf, Vormerkender ist die Kennung `betreiber` (Konto leer). Die normale Schonfrist (`FR_LOESCHFRIST_TAGE`, Vorgabe 14 Tage) gilt unverändert; keine Abkürzung.
- Die Reise verschwindet sofort überall (`reise_vorgemerkt`, auch aus dem Archiv und aus `my_trips`); der Wächter entfernt sie nach Fristende endgültig samt Seitenordner und schreibt das Löschprotokoll.
- Der Befehl verweigert Reisen, die nicht im Reisespeicher liegen, und bereits vorgemerkte Reisen; beides mit klarer Meldung und Exit-Code ungleich 0.

### 5. Ablauf Aufräumen (Schritt 7 der Reihenfolge)

Alle fünf Testreisen im Konto des Product Owners (zwei aktiv, drei archiviert, hier `<Testreise A>` bis `<Testreise E>`) liegen im Reisespeicher. Der Löschweg aus #381 gilt daher für alle; ein Sonderweg für Altreisen ist nicht nötig.

1. Claude erstellt die Liste der Kandidaten aus `my_trips` (aktiv und Archiv) und legt sie dem Product Owner zur Freigabe vor, per Frage mit Optionen und Empfehlung, vor dem Vormerken. Die Liste steht nur im privaten Instanz-Repo und im Chat, nie im öffentlichen Repo. Echte Reisen sind nie Kandidaten.
2. Nach Freigabe führt Claude `konten.py vormerken` für jede freigegebene Reise aus.
3. Erfüllt ist das Fertig-Kriterium „keine Testreise mehr im Konto“ mit dem Vormerken: `my_trips` (aktiv und Archiv) zeigt keine davon mehr.
4. Nach Fristende prüft Claude die endgültige Entfernung mit `konten.py vorgemerkt` und dem Löschprotokoll des Wächters.

### 6. Reihenfolge der Umsetzung

(1) Postfach als Issue im Infrastruktur-Repo und `FR_TESTKONTO` in der privaten Instanz, (2) `testzugang.py` mit Tests, (3) Sperre mit Tests, (4) `vormerken` mit Tests, (5) `.mcp.json` und `.claude/settings.json`, (6) einmal vollständige Abnahme über `frieda-test` (Reise anlegen, Dinge, Entscheidung, Einladung an eine Unteradresse des Testpostfachs, Veröffentlichen, Seite mit Prüfsitzung), (7) Freigabe der Löschliste, Vormerken, Doku.

### Testkonto-Regeln

- Recht `reise_anlegen`, nie Betreiber.
- Einladungen in Abnahmen gehen nur an Unteradressen des Testpostfachs (Plus-Adressierung), nie an echte Personen.
- Testreisen im Testkonto werden nach der Abnahme über denselben Weg (Vormerken mit Schonfrist) entfernt; das Konto des Product Owners bleibt unberührt.

## Test Plan

### Automated Tests (TDD RED)

Testdateien: `engine/tests/test_testzugang.py` (TZ), `engine/tests/test_frieda_sperre.py` (SP), `engine/tests/test_konten_vormerken.py` (VM). Alle laufen gegen die Wegwerf-Instanz der Testwelt (Muster `verbinden()` aus `test_oauth.py`, Fixture `welt`, `FR_MAIL_DATEI`), ohne echte Reisen.

- [ ] Test 1 (TZ): GIVEN eine Testinstanz und `FR_TESTKONTO` gesetzt WHEN `einrichten` läuft THEN existiert das Konto mit Recht `reise_anlegen` ohne `betreiber`, die Ablage-Datei hat Rechte 600 und enthält ein gültiges Token.
- [ ] Test 2 (TZ): GIVEN das Konto zu `FR_TESTKONTO` hat das Recht `betreiber` oder die Adresse ist eine Betreiberadresse WHEN `einrichten` läuft THEN bricht der Befehl ab und legt keine Ablage an.
- [ ] Test 3 (TZ): GIVEN ein eingerichteter Zugang WHEN die Brücke eine Anfrage `tools/list` per stdio erhält THEN antwortet sie mit der Werkzeugliste des Konnektors.
- [ ] Test 4 (TZ): GIVEN ein abgelaufenes Access-Token WHEN die Brücke eine Anfrage weiterleitet THEN erneuert sie das Token, die Ablage enthält das neue Refresh-Token (Rechte 600, atomar) und die Anfrage gelingt.
- [ ] Test 5 (TZ): GIVEN zwei Brücken-Prozesse mit demselben abgelaufenen Token WHEN beide gleichzeitig erneuern THEN löst nur einer den Refresh-Token ein, der andere liest das neue Paar; die Token-Familie wird nicht widerrufen.
- [ ] Test 6 (TZ): GIVEN die Ablage enthält ein Token eines anderen Kontos WHEN die Brücke startet THEN bricht sie ohne Weiterleitung ab.
- [ ] Test 7 (TZ): GIVEN die Brücke läuft WHEN ihr Quelltext untersucht wird THEN importiert sie nur Standardbibliothek und der Befehl in `.mcp.json` enthält weder Adresse noch Geheimnis.
- [ ] Test 8 (SP): GIVEN die Werkzeugliste des Konnektors WHEN der Hook für jedes Werkzeug befragt wird THEN ist genau jedes Werkzeug mit `readOnlyHint: true` erlaubt und jedes andere abgelehnt.
- [ ] Test 9 (SP): GIVEN ein unbekanntes Werkzeug `mcp__claude_ai_Frieda__neu_erfunden` WHEN der Hook befragt wird THEN wird es abgelehnt mit Hinweis auf `frieda-test`.
- [ ] Test 10 (SP): GIVEN ein Werkzeug eines anderen Servers (etwa `mcp__frieda-test__…`) WHEN der Hook befragt wird THEN greift er nicht ein.
- [ ] Test 11 (SP): GIVEN der Quelltext des Hooks WHEN er untersucht wird THEN nutzt er nur Standardbibliothek.
- [ ] Test 12 (VM): GIVEN eine Reise im Reisespeicher WHEN `konten.py vormerken <reise>` läuft THEN ist sie vorgemerkt (`reise_vorgemerkt`), fehlt in aktiver Liste und Archiv, und die Frist entspricht `FR_LOESCHFRIST_TAGE`.
- [ ] Test 13 (VM): GIVEN eine Reise, die nicht im Reisespeicher liegt, oder eine bereits vorgemerkte WHEN `vormerken` läuft THEN verweigert der Befehl mit Exit-Code ungleich 0 und ohne Wirkung.
- [ ] Test 14 (VM): GIVEN eine vorgemerkte Reise nach Fristende WHEN der Wächter `loeschungen_ausfuehren` ausführt THEN ist die Reise endgültig entfernt (bestehender Weg aus #381, mit Reise aus dem Befehl `vormerken`).
- [ ] Test 15 (PF, bestehende Prüfungen): GIVEN die Texte der Repo-Dokumente und Specs WHEN `engine/tests/test_protokolle_ohne_pfade.py` und die Prüfung auf Platzhalter laufen THEN sind beide grün und keine echte Reisekennung steht in der Spec.

## Acceptance Criteria

- **AC-1:** Given eine Instanz mit `FR_TESTKONTO` / When `testzugang.py einrichten` läuft / Then entsteht ein Testkonto mit Recht `reise_anlegen`, ohne `betreiber`, und eine Ablage mit Rechten 600 außerhalb des Repos. (Tests 1, 2)
- **AC-2:** Given ein Konto mit Recht `betreiber` oder `FR_TESTKONTO` gleich einer Betreiberadresse / When `einrichten` läuft / Then wird die Einrichtung verweigert. (Test 2)
- **AC-3:** Given der eingerichtete Zugang / When Claude Code den Server `frieda-test` startet / Then liefert die Brücke dieselbe Werkzeugliste wie der Konnektor und beantwortet Aufrufe als Testkonto. (Test 3)
- **AC-4:** Given ein abgelaufenes Access-Token / When eine Anfrage kommt / Then erneuert die Brücke selbst, schreibt die Ablage atomar mit 600 und widerruft bei parallelen Sitzungen die Token-Familie nicht. (Tests 4, 5)
- **AC-5:** Given ein Token, das nicht zum Testkonto gehört / When die Brücke startet / Then bricht sie ohne Weiterleitung ab. (Test 6)
- **AC-6:** Given eine Claude-Code-Sitzung dieses Repos / When ein schreibendes oder unbekanntes Werkzeug des Konnektors des Product Owners aufgerufen wird / Then lehnt der Hook ab mit Hinweis auf `frieda-test`; Lesewerkzeuge und andere Server bleiben aufrufbar. (Tests 8, 9, 10)
- **AC-7:** Given ein neues Werkzeug im Konnektor / When die Testsuite läuft / Then ist der Hook-Test rot, bis Erlaubnisliste und Werkzeug übereinstimmen (keine Handpflege). (Test 8)
- **AC-8:** Given eine Reise im Reisespeicher / When `konten.py vormerken <reise>` läuft / Then ist die Reise überall verschwunden und der Wächter entfernt sie nach der normalen Schonfrist endgültig; Reisen außerhalb des Speichers und bereits vorgemerkte werden verweigert. (Tests 12, 13, 14)
- **AC-9:** Given die freigegebene Liste von fünf Testreisen / When sie vorgemerkt sind / Then zeigt `my_trips` (aktiv und Archiv) keine davon mehr; nach Fristende bestätigen `konten.py vorgemerkt` und das Löschprotokoll das endgültige Entfernen. Kein Schritt davon erfolgt ohne vorherige Freigabe des Product Owners, und die Liste steht nicht im öffentlichen Repo.
- **AC-10:** Given die Doku / When `CLAUDE.md` und `docs/betrieb.md` gelesen werden / Then enthalten sie die Regel „Abnahmen nie über das Konto des Product Owners“, die Einrichtung, das Testkonzept (Stufe 3: Testkonto statt Archivieren) und die bekannte Grenze zu Betreiber-Meldungen.
- **AC-11:** Given die vollständige Testsuite / When sie läuft / Then ist sie grün (`engine/.venv/bin/python -m pytest -q -n 3 engine/tests`), `ALARMSTELLEN` bleibt unverändert und es gibt keine echten Reisekennungen in Repo und Specs.
- **AC-12:** Given die Umsetzung / When die Workflow-Gates geprüft werden / Then wurde keine Gate-Konfiguration geändert und keine menschliche Sperre (override) gebraucht.

## Expected Behavior

- **Input:** Claude Code startet den Server `frieda-test` aus `.mcp.json`; Aufrufe der Werkzeuge des Konnektors; Betreiberbefehle `testzugang.py einrichten`, `konten.py vormerken <reise>`.
- **Output:** Aufrufe gegen die echte Instanz als Testkonto mit den Rechten des Testkontos (anlegen, schreiben, veröffentlichen, einladen an Unteradressen). Aufrufe schreibender Werkzeuge über den Konnektor des Product Owners werden abgelehnt.
- **Side effects:** Ablage-Datei des Zugangs außerhalb des Repos (Rechte 600, bei jeder Erneuerung neu geschrieben); beim Vormerken ein Eintrag in der Löschvormerkung, nach der Schonfrist das endgültige Entfernen durch den Wächter mit Löschprotokoll.

## Known Limitations

- **Betreiber-Meldungen:** Bei Abnahmen der Warteliste gehen Betreiber-Meldungen weiter an den Betreiber (Product Owner), denn die Betreiberrolle gehört nicht dem Testkonto. Das ist unvermeidlich und bekannt.
- **Schonfrist:** Vorgemerkte Reisen sind sofort unsichtbar, aber erst nach der Frist (Vorgabe 14 Tage) endgültig entfernt. Die Abschlussprüfung folgt daher erst nach Fristende.
- **Hook nur in Claude Code:** Die Sperre schützt Sitzungen dieses Repos, nicht andere Programme und nicht die Claude-App; dort bleibt es bei der Regel in `CLAUDE.md`.
- **Lesen erlaubt:** Der Konnektor des Product Owners bleibt für Lesewerkzeuge nutzbar; die Sperre verhindert Schreiben, nicht Einsehen.
- **Postfach:** Das Testpostfach entsteht außerhalb dieses Repos; bis dahin sind Abnahmen mit Einladungen nicht vollständig möglich.
- **Neustart:** Ein Widerruf der Token-Familie (etwa nach manuellem Eingriff) verlangt ein erneutes `einrichten`.

## Definition of Done

- [ ] Alle Acceptance Criteria AC-1 bis AC-12 erfüllt.
- [ ] `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün; Pflichtprüfungen der CI grün.
- [ ] Tests der Instanz vor dem Vorspulen mit dem Branch grün (Änderung an `konten.py`-CLI und Einstellungen).
- [ ] Einmalige Abnahme über `frieda-test` an beiden Beispielreisen (Wanderung und Städtewochenende) dokumentiert, ohne echte Reisekennungen.
- [ ] Freigabe der Löschliste eingeholt, Reisen vorgemerkt, Entfernung nach Fristende geprüft.
- [ ] #648 mit Nachweisen geschlossen, Artefakte inhaltlich im Issue.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Betriebswerkzeug innerhalb bestehender Entscheidungen (ADR-0005 Konten und Anmeldung, #381 Löschen mit Frist); keine Änderung am Produktverhalten, kein neues Datenformat, keine neue Schnittstelle des Dienstes. Die Begründung für die Brücke statt einer Wegwerf-Instanz steht in der Analyse (`docs/context/feature-648-testkonto.md`).

## Changelog

- 2026-11-24: Initial spec created
