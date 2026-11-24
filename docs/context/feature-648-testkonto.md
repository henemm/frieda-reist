# Context: feature-648-testkonto

## Request Summary
Abnahmen über den Konnektor sollen mit einem eigenen Testkonto laufen, nie über das Konto des Product Owners (dessen Konnektor in Claude Code eingebunden ist). Dazu eine Sperre gegen den Rückfall, das endgültige Löschen der vorhandenen Testreisen im Konto des Product Owners (Liste vorher zur Freigabe) und nachgeführte Doku. Hürde (Kommentar OWNER): ein zweites Claude-Konto oder das Umstellen der Anmeldung des claude.ai-Konnektors sind ausgeschlossen.

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/pruefsitzung.py | Prüfkonto `pruefung@<host>` per SQL, Sitzungs-Cookie für Playwright; kein OAuth-Token, keine Rechte/Mitgliedschaft (:40-56) |
| engine/konten.py | Konten entstehen bei `anmelden` (:441); Rechte `reise_anlegen`, `betreiber` (:67); CLI `liste`, `freischalten`, `loeschen` u. a. (:24-39, main :1857); OAuth-Ablage: `oauth_code_anlegen` :1736, `_tokens_ausstellen` :1745 (Access 1 h, Refresh 90 Tage mit Rotation); Löschen vormerken `loeschung_vormerken` :1190, `faellige_loeschungen` :1247, `loeschung_abschliessen` :1256 |
| engine/oauth.py | Dynamische Registrierung, PKCE S256 Pflicht, Loopback-Redirects (Claude Code) erlaubt; `/authorize` braucht Sitzungs-Cookie, sonst Mail-Code-Anmeldung (:285-288) |
| engine/anmeldung.py | Reise löschen vormerken nur über „Mein Konto“, nur Organisator:in, nur Reisen im Reisespeicher (:769-817); Archivliste (:1105) |
| engine/waechter.py | `loeschen` entfernt endgültig, aber erst nach Frist `FR_LOESCHFRIST_TAGE` (Vorgabe 14) (:448-491, :677-684) |
| engine/reisespeicher.py | `reise_entfernen` :880 |
| engine/konnektor.py | `reisen_des_kontos` :2517, `meine_reisen_konto` :2588; Dienst `konnektor.py dienst` (KN_HOST/KN_PORT 8772) |
| engine/tests/test_oauth.py | `verbinden()` :69 spielt den ganzen OAuth-Ablauf wie die App nach, `aufruf()` :81 |
| engine/tests/test_anmeldung.py | Fixture `welt` :24, `anmelden()` liest Code aus `FR_MAIL_DATEI` :73 |
| engine/tests/conftest.py | `mcp_intern` :129 (ohne OAuth) |
| docs/betrieb.md | :341-343 „Seiten prüfen“ (Prüfkonto); Testkonzept fehlt |
| CLAUDE.md | Regel „nie Testreisen ins Konto des Product Owners“ fehlt |

## Existing Patterns
- Prüfsitzung: Betriebsbefehl, läuft als Dienstbenutzer mit Instanzwerten, legt das Prüfkonto direkt an und gibt nur eine Datei (Rechte 600) aus.
- OAuth-Ablauf (`verbinden`) existiert im Testcode, Vorlage für einen Betriebsbefehl.
- Mail ohne SMTP: `FR_MAIL_DATEI` schreibt Codes in eine Datei (Wegwerf-Instanz).
- Löschen: vormerken → Frist → Wächter entfernt endgültig mit Löschprotokoll.
- Früheres Werkzeug `betrieb/messlauf-schreibweg.py` (Wegwerf-Instanz, #347) nur noch in der Historie (entfernt um #557).

## Dependencies
- Upstream: konten.py (SQLite Konten), oauth.py, reisespeicher.py, Instanz-Einstellungen (`<FR_DIENST>/instanz/einstellungen.env`).
- Downstream: Claude-Code-Sitzungen (MCP-Eintrag), Wächter, Datenschutzerklärung (Löschen).

## Existing Specs
- docs/specs/betrieb/anmeldecode-mail-532.md, betreiber-meldung-530.md, warteliste-push-631.md (Muster „Abnahme nur mit Testkonto/Testreise“).
- Issue #273 (geschlossen): Testkonzept drei Stufen; Stufe 3 sagte „danach archiviert“, überholt durch #648.
- Issue #381 (geschlossen): Löschen mit Frist.

## Lösungsrichtungen (für /20-analyse)
1. Eigener MCP-Eintrag nur in Claude Code (Projekt-Scope), z. B. `frieda-test`, gegen dieselbe Instanz, angemeldet als Testkonto. Anmeldung ohne Handgriff: Betriebsbefehl, der für das Testkonto ein Token ausstellt (wie pruefsitzung), oder OAuth-Ablauf mit Prüfsitzungs-Cookie automatisiert. Offen: Access-Token gilt 1 h; ein fester Header-Token müsste erneuert werden.
2. Abnahmen in einer Wegwerf-Instanz (127.0.0.1, eigener Ordner, `FR_MAIL_DATEI`); Produktion nur lesend prüfen.
- Testkonto braucht ein eigenes Postfach (Stalwart) für Einladungsmails; Recht `reise_anlegen`, Reisegrenze beachten.
- Sperre: PreToolUse-Hook im Repo, der Schreibwerkzeuge `mcp__claude_ai_Frieda__*` sperrt (Lesen erlaubt?); das Repo hat bisher keine projekteigenen Hooks.
- Aufräumen: Liste der Testreisen im Konto des Product Owners (nur in der Instanz, nie im öffentlichen Repo); Löschen über Vormerken + Wächter; Frist 14 Tage prüfen (verschwindet eine vorgemerkte Reise sofort aus der Liste?).

## Risks & Considerations
- Echte Reisen dürfen nie gelöscht werden: Freigabeliste, nur Reisen mit erkennbarem Testcharakter.
- Kein Token des Testkontos im öffentlichen Repo; Ablage außerhalb, Rechte 600.
- Testkonto auf der Produktion: keine Betreiberrechte.
- Die Sperre darf die Nutzung des Product Owners in der Claude-App nicht betreffen (nur Claude-Code-Sitzungen).
- Instanzspezifisches (Adresse des Testpostfachs) gehört in die Einstellungen der Instanz, nicht ins Repo.

## Analysis

### Type
Feature (Betrieb und Werkzeug für Abnahmen; keine Änderung am Produktverhalten für Reisende)

### Befunde (24.11.2026)
- Der Konnektor spricht reines JSON-RPC über `POST /mcp` mit JSON-Antwort (kein SSE, keine Sitzungskennung) und prüft nur `Authorization: Bearer` (`konnektor.py` do_POST, `konten.oauth_konto`). Eine Brücke stdio → HTTP kommt mit der Standardbibliothek aus.
- OAuth: dynamische Registrierung mit Loopback-Redirect erlaubt, PKCE S256, `/authorize` braucht eine Sitzung (Cookie), Zustimmung per POST `aktion=erlauben` mit Herkunftsprüfung; Access-Token 1 h, Refresh-Token 90 Tage mit Rotation (zweites Einlösen widerruft die Familie).
- Die Dienste der Instanz laufen als derselbe Benutzer wie Claude Code; Claude kann den Einrichtungsbefehl (wie `pruefsitzung.py`) selbst ausführen, ohne Handgriff des Product Owners.
- Ein `/mcp`-Login von Claude Code über den Browser scheidet aus (Server ohne Browser, Handgriff nötig); ein fester Header-Token scheitert an der Stunde Gültigkeit.
- Löschen (#381): `loeschung_vormerken(reise, kid)` lässt die Reise sofort überall wie nicht vorhanden erscheinen (`reise_vorgemerkt`, auch Archivliste); der Wächter entfernt sie nach `loeschfrist_tage` (14) endgültig. Weg dahin nur über „Mein Konto“ (Sitzung der Organisator:in), kein Betreiberbefehl; `konten.py vorgemerkt` listet nur.
- Kandidaten im Konto des Product Owners (my_trips, 24.11.): aktiv `<Testreise A>`, `<Testreise B>`; archiviert `<Testreise C>`, `<Testreise D>`, `<Testreise E>`. Alle liegen im Reisespeicher (Spec, Abschnitt 5). Echte Reisen sind nie Kandidaten. Die Liste mit echten Kennungen steht nur in der privaten Instanz.
- Nebenbefund: Betreiber-Meldungen aus Abnahmen (Probe 631, Warteliste) landen beim Product Owner als Betreiber. Bei Abnahmen der Warteliste unvermeidlich (Betreiberrolle); in der Spec als bekannte Grenze festhalten. Das Testkonto bekommt kein Betreiberrecht.
- Das Repo hat keine projekteigenen Hooks und keine `.mcp.json`; getrackt ist unter `.claude/` nur `commands/naechstes.md`.

### Entscheidung (Tech Lead): Lösungsrichtung 1, Brücke statt Wegwerf-Instanz
Eigener Konnektor-Zugang nur in Claude Code (`frieda-test`), unabhängig von claude.ai, gegen die echte Instanz, angemeldet als Testkonto über den echten OAuth-Weg. Begründung: prüft genau den Weg der Claude-App (Anmeldung, Token, Schreibweg, Veröffentlichen, Seite, Mails), keine Hintertür im Dienst, keine zweite Instanz zu pflegen. Die Wegwerf-Instanz bleibt den automatischen Tests (pytest) vorbehalten.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| betrieb/testzugang.py | CREATE | `einrichten`: Testkonto anlegen/finden (Adresse aus Instanzwert, Recht `reise_anlegen`, nie Betreiber), kurze Sitzung, OAuth-Ablauf gegen die Instanz (Registrierung Loopback, authorize mit Cookie, Zustimmung, Token), Ablage `client_id` + Refresh-Token außerhalb des Repos (600, atomar). `dienst`: stdio-MCP-Brücke zu `<adresse>/mcp`, erneuert Tokens selbst (Rotation, Datei atomar, Sperre gegen parallele Sitzungen), prüft beim Start, dass das Token zum Testkonto gehört, sonst Abbruch |
| betrieb/pruefsitzung.py | MODIFY | Sitzung ausstellen als gemeinsame Hilfsfunktion, die testzugang.py mitnutzt |
| engine/konten.py | MODIFY | Betreiberbefehl `vormerken <reise>` (Löschen vormerken ohne Sitzung); Wächter erledigt den Rest |
| .mcp.json | CREATE | Server `frieda-test`: `python3 betrieb/testzugang.py dienst` (ohne Adresse, ohne Geheimnis) |
| .claude/settings.json | CREATE | `enabledMcpjsonServers: ["frieda-test"]`; PreToolUse-Hook auf `mcp__claude_ai_Frieda__.*` |
| .claude/hooks/frieda_sperre.py | CREATE | Sperre: am Konnektor des Product Owners nur Lesewerkzeuge (Erlaubnisliste, neue Werkzeuge standardmäßig gesperrt); alles andere abgelehnt mit Hinweis auf `frieda-test` |
| betrieb/einstellungen.beispiel | MODIFY | `FR_TESTKONTO` (Adresse des Testpostfachs), Ablageort des Zugangs |
| engine/tests/test_testzugang.py | CREATE | Einrichten und Brücke gegen den Test-Konnektor (Muster `verbinden()` aus test_oauth.py), Erneuern/Rotation, falsches Konto → Abbruch, Datei 600 |
| engine/tests/test_frieda_sperre.py | CREATE | Hook: Lesewerkzeug erlaubt, Schreib- und unbekanntes Werkzeug gesperrt, andere Server unberührt |
| CLAUDE.md, docs/betrieb.md, Testkonzept | MODIFY | Regel „nie über das Konto des Product Owners testen“, Einrichtung, Testkonzept (Stufe 3: Testkonto statt Archivieren) |
| Infrastruktur-Repo (Issue) | – | Postfach für das Testkonto in Stalwart mit Unteradressen für eingeladene Testpersonen |
| frieda-instanz (privat) | – | `FR_TESTKONTO` in den Einstellungen der Instanz; Aufräumliste nur dort |

### Scope Assessment
- Files: ~12 (4 neu im Code, 2 Tests)
- Estimated LoC: +450/-20
- Risk Level: MEDIUM — Anmeldung und Löschen auf der echten Instanz; Absicherung: Kontoprüfung in der Brücke, Freigabeliste, Löschen nur mit Schonfrist.

### Technical Approach
Siehe Entscheidung oben. Reihenfolge: (1) Postfach (Infra) und `FR_TESTKONTO`, (2) testzugang.py + Tests, (3) Sperre + Tests, (4) `.mcp.json`/Einstellungen, (5) Abnahme einmal vollständig über `frieda-test` (Reise anlegen, Dinge, Entscheidung, Einladung an Unteradresse, Veröffentlichen, Seite mit Prüfsitzung), (6) Freigabe der Löschliste beim Product Owner, `vormerken`, Doku.

### Dependencies
- Upstream: konten.py (Sitzung, OAuth-Tabellen, Löschvormerkung), oauth.py, konnektor.py (/mcp), Instanzwerte (FR_KN_ADRESSE, FR_KONTEN, FR_TESTKONTO).
- Downstream: Claude-Code-Sitzungen dieses Repos (MCP-Eintrag, Hook), Wächter (endgültiges Löschen), Stalwart-Postfach.
- `betrieb/deploy.sh`-Modulliste nicht betroffen (testzugang läuft im Klon, nicht im Dienst).

### Open Questions
- [ ] Freigabe der Löschliste (5 Testreisen) durch den Product Owner – Produktentscheidung, per AskUserQuestion vor dem Löschen.
- [ ] Lesen über den Konnektor des Product Owners bleibt erlaubt (technische Entscheidung: ja, Schreiben gesperrt).
- [x] Liegen die beiden älteren archivierten Testreisen im Reisespeicher? Ja (Spec, Abschnitt 5); kein Sonderweg für Altreisen.

## Hinweise aus der RED-Phase (2026-11-24)

- **Kontoprüfung der Brücke:** `my_profile` liefert nur Profileinträge, nicht die Kontoadresse. Die Brücke liest die Adresse aus der Antwort auf `initialize` (die Anleitung nennt das angemeldete Konto); ein Betreiberkonto erkennt sie an `request_decide` in `tools/list`. Beides ohne Änderung an `konnektor.py`.
- **Lesewerkzeuge ohne `readOnlyHint`:** `my_trips`, `my_profile` und `calendar` tragen keinen `readOnlyHint` und bleiben daher am Konnektor des Product Owners gesperrt (Regel „genau `readOnlyHint: true`“). Die Liste der Kandidaten für Schritt 5.1 entsteht deshalb aus `konten.py liste` auf dem Server (Mitgliedschaften des Kontos, aktiv und Archiv), nicht aus `my_trips`.
- **Ablage:** enthält neben `client_id` und `refresh_token` auch das aktuelle Access-Token mit Ablauf, damit eine zweite Brücke nach der Erneuerung durch die erste das neue Paar unter der Sperre übernimmt, statt selbst einzulösen (Test 5).
- **Tests:** `engine/tests/test_testzugang.py`, `engine/tests/test_frieda_sperre.py`, `engine/tests/test_konten_vormerken.py`; zusätzlich zu den Tests 1 bis 14: Einrichten ohne `FR_TESTKONTO`, zweites Einrichten widerruft den alten Zugang, Erneuern bei 401 mitten im Lauf, Testkonto nachträglich Betreiber, Instanzwerte in `einstellungen.beispiel`, Frist aus `FR_LOESCHFRIST_TAGE`.
