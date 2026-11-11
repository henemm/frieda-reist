# Context: alpha-380-trennung (#380)

## Request Summary
Für die öffentliche Alpha (M5a, eine Instanz für alle Tester) nachweisen und, wo nötig, beheben: Eine angemeldete Person sieht, liest, sucht und schreibt nur Reisen, in denen sie Mitglied ist. Das gilt für den Konnektor, die Reiseseiten, den Rückmeldedienst, den Reisespeicher und die Mails. Dazu kommen Mengenbegrenzungen je Person, deren Grenzwerte aus der Instanz kommen. Prüfpunkte: eine grüne Testreihe mit zwei Konten und ein Prüfbericht als Kommentar.

## Related Files
| File | Relevance |
|------|-----------|
| engine/konnektor.py:3366 | `do_POST /mcp`: prüft das Bearer-Token (`oauth.bearer`, `konten.oauth_konto`), sonst 401. Danach ist der Zugang nur `{"konto_id"}`. |
| engine/konnektor.py:2174 | `reisen_des_kontos`: Mitgliedschaften des Kontos, nur veröffentlichte Reisen. |
| engine/konnektor.py:2185 | `frieda_werkzeuge`: Das Schema beschränkt `reise` per enum. Das ist nur kosmetisch. |
| engine/konnektor.py:2237 | `meine_reisen_konto`: reiseübergreifend, aber nur über Mitgliedschaften. |
| engine/konnektor.py:2314-2322 | `frieda_werkzeug`: die **zentrale Mitgliedschaftsprüfung**. Ist `reise` keine Reise des Kontos, gibt es den Fehler `konnektor.frieda_werkzeug.1`. Ohne `reise` wird die einzige Reise des Kontos genommen. |
| engine/konnektor.py:222, 243 | `wer_spricht` und `recht()`: Rolle je Reise (gast < mitwirkend < organisator), `reise.erlaubt(...)`. |
| engine/konnektor.py:1007 | `suche` ist eine Methode der Reise und damit auf eine Reise begrenzt. |
| engine/konnektor.py:1932-1987 | `person_invite`: Rollen nur bis zur eigenen Rolle; Ändern und Entfernen nur als Organisator:in. |
| engine/konnektor.py:2100-2160 | `trip_create`: Wer anlegt, wird als Organisator:in mit dem eigenen Konto verknüpft (`e["konto_id"]`); dazu kommen Einladungsmails. |
| engine/konten.py:524, 684, 690, 718 | `recht` (Kontorechte `reise_anlegen` und `betreiber`), `mitgliedschaften`, `mitglied`, `verknuepfen`. |
| engine/konten.py:67-68, 966 | Feste Grenzen: Anmeldecodes je Adresse und je IP, Einladungen je Reise (50 in 24 h). |
| engine/rueckmeldungen.py:919, 940, 163 | `wer_ist` (dienst, seite, fremd, konto), `name_fuer` (403 ohne Mitgliedschaft, 401 anonym, #421), `seher` (Nicht-Mitglied sieht wie ein Gast). |
| engine/rueckmeldungen.py:1143-1148 | GET `stand`, `brett`, `packstand`: **keine Mitgliedschaftsprüfung**, nur über den Geheimpfad geschützt. |
| engine/rueckmeldungen.py:105, 954, 193 | `MAX_JE_MINUTE = 30` je Reise, `gedrosselt`, `MAX_EINLADUNGEN = 50`. |
| engine/rueckmeldungen.py:389-412 | Meldungen über alle Reisen des Kontos. |
| engine/kalender.py:258ff | Kalender-Abo per HMAC-Token je Konto, über alle Mitgliedschaften. |
| engine/belege.py | Belege nur für Angemeldete (`rueckmeldungen.py:1206`, `:1300`); `bl.liste(o, name, rolle)` filtert. |
| engine/waechter.py:24 | Ohne Angabe läuft er über alle Reisen der Ablage. Zu prüfen: an wen gehen seine Mails? |
| betrieb/freischalten.sh, betrieb/vorlagen/nginx-reise.conf | Reiseseiten liegen unter einem geheimen Zufallspfad je Reise, ohne `auth_request`. |
| betrieb/vorlagen/nginx-konnektor-orte.inc:10, 20-25 | Cookie `__Host-frieda` für api/ich; `limit_req` je IP für /mcp (burst 40). |
| engine/instanz.py | Vorgaben einer Instanz. Hierher gehören Grenzwerte je Person (Vorgabe in #380 und ADR-0001). |

## Existing Patterns
- **Zugriff in zwei Stufen:** zuerst die Mitgliedschaft (Konto → Reise, `konten.mitgliedschaften`), dann die Rolle in der Reise (`reise.erlaubt`).
- **Konto-Werkzeuge** (`meine_reisen`, `kalender`, `sprache_setzen`, `anfrage_entscheiden`, `trip_create`) laufen vor der Reiseprüfung und arbeiten nur über die Mitgliedschaften.
- **Rückmeldedienst:** Identität über eine Sitzung mit Origin-Prüfung gegen CSRF; die Reise kommt aus dem URL-Pfad.
- **Drosselung** bisher je Reise oder IP mit festen Konstanten, nicht je Konto und nicht aus der Instanz.

## Dependencies
- Upstream: oauth.py (Token), konten.py (Mitgliedschaften und Rechte), reise.py (`erlaubt`), reisespeicher.py, nginx-Vorlagen.
- Downstream: alle MCP-Werkzeuge, Reiseseite (vorlage.html und Service Worker rufen `stand`, `brett`, `packstand` und Rückmeldungen auf), Mails (Einladungen, Wächter, Zustellen).

## Existing Specs / Docs
- docs/adr/0005-konten.md (Punkte 4 und 5: Rolle gehört zur Reise, Identität zum Konto; Anlegen nur nach Freischaltung; Belege nur für Angemeldete)
- docs/adr/0001-kern.md (Grenzen kommen aus der Instanz)
- docs/konten.md, docs/konnektor.md, docs/betrieb.md:7 und :43 (#68: Trennung bisher nur über eigene Instanzen)
- docs/specs/betrieb/warteliste-382.md, docs/specs/oberflaeche/meldungen-konto-407.md

## Vorhandene Tests
- test_konten.py:94, :122, :290; test_anmeldung.py:137; test_kalender.py:246, :277, :334; test_konnektor.py:934, :994 (Belege); test_rueckmeldungen.py, test_oauth.py.
- **Es fehlt** eine Testreihe mit zwei Konten und zwei Reisen: Konto B ruft Werkzeuge mit `reise=<Reise A>` auf, sucht, liest Belege oder Rückmeldungen per Cookie, schreibt in Reise A, und Namen oder Adressen aus Reise A dürfen in keiner Antwort an B auftauchen.

## Risks & Considerations
- **Mögliche Lücke 1 (wichtigste):** Reiseseiten und GET-Endpunkte des Rückmeldedienstes (`stand`, `brett`, `packstand`) sind nur durch den Geheimpfad geschützt. Wer den Link kennt, liest, auch ohne Konto. Das war bisher gewollt (Links wurden geteilt), inzwischen werden Personen aber per E-Mail eingeladen. Für die Analyse offen: Reicht der Geheimpfad für die Alpha, oder soll Lesen eine Anmeldung brauchen? Das wäre womöglich eine Produktentscheidung (Gäste ohne Konto, Offline-Seite und Service Worker).
- **Lücke 2:** Es gibt keine Mengenbegrenzung je Person für angelegte Reisen und Schreibvorgänge im Konnektor. Die vorhandenen Grenzen sind feste Konstanten statt Instanzvorgaben.
- **Zu prüfen:** Empfänger der Wächter- und Erinnerungsmails (nur Mitglieder der jeweiligen Reise?); Fehlertexte, die fremde Reisenamen preisgeben (z. B. bei `konnektor.frieda_werkzeug.1`); `meine_reisen` und Kalender mit einer Mitgliedschaft auf einer unveröffentlichten Reise; entfernte Personen lesen als Gast weiter (gewollt, aber festhalten).
- Mehrere Mandanten in einer Instanz (#68) bleiben außerhalb des Umfangs; Funde dazu dort benennen.
- Was eine Instanz nutzt (Umgebungswerte für Grenzen), braucht Tests der einbindenden Instanz und eine Umstellung in `neu.py nachziehen`, falls sich Datenformate ändern.

## Analysis

### Type
Feature (Nachweis plus Ergänzung: Mengenbegrenzung je Person); Lücken, die der Test findet, werden als Fehler im selben Workflow behoben.

### Befund der Prüfstellen (Stand 11.11.2026)
- **Konnektor:** Die zentrale Prüfung in `frieda_werkzeug` (engine/konnektor.py:2314-2322) lässt nur Reisen aus `reisen_des_kontos` zu; der Fehler `konnektor.frieda_werkzeug.1` nennt keinen Reisenamen. `suche` ist an die Reise gebunden. Konto-Werkzeuge laufen nur über Mitgliedschaften. Erwartung: dicht, der Test soll es belegen.
- **Rückmeldedienst, Schreiben:** `name_fuer` gibt 403 ohne Mitgliedschaft, 401 anonym (#421). Dicht.
- **Rückmeldedienst, Lesen (`stand`, `brett`, `packstand`, Belege für alle):** nur über den geheimen Seitenlink (96 Bit Zufall, noindex, no-referrer). **So gewollt:** Entscheidung des Product Owners 27.10.2026 und erneut 8.11.2026 in #421 („Lesen über den geheimen Seitenlink bleibt, ohne Anmeldung“). Keine Produktfrage offen; im Prüfbericht als bewusste Grenze festhalten. Angemeldete Nicht-Mitglieder sehen Belege wie ein Gast (`seher`).
- **Wächter/Erinnerer:** Empfänger nur Personen derselben Reise (`empfaenger`, `organisator_von` aus `reise.personen`). Test ergänzen, dass keine Meldung einer Reise bei einem Konto ohne Mitgliedschaft landet (Meldungen über alle Reisen des Kontos, rueckmeldungen.py:389-412).
- **Kalender-Abo:** nur Mitgliedschaften des Kontos (bestehende Tests, im Bericht verweisen).
- **Mengenbegrenzung:** fehlt je Konto. Vorhanden nur je Reise (`MAX_JE_MINUTE`, `MAX_EINLADUNGEN`), je IP (nginx `limit_req`) und je Adresse (Anmeldecodes), alles feste Konstanten.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/instanz.py | MODIFY | Grenzwerte je Person aus den Einstellungen der Instanz mit Vorgaben: `FR_GRENZE_REISEN` (angelegte Reisen je Konto), `FR_GRENZE_SCHREIBEN` (Schreibvorgänge je Konto und Stunde) |
| engine/konten.py | MODIFY | Zähler je Konto (Schreibvorgänge im gleitenden Fenster, in der Konten-Datenbank), Anzahl selbst angelegter Reisen |
| engine/konnektor.py | MODIFY | Vor `trip_create`/`reise_anlegen` Reisegrenze prüfen; in `frieda_werkzeug` vor schreibenden Werkzeugen Schreibgrenze prüfen; Ablehnung mit Text, Eintrag im Protokoll |
| engine/texte_*.py | MODIFY | Ablehnungstexte (Grenze erreicht) in allen Sprachen |
| engine/tests/test_trennung.py | CREATE | Testreihe mit zwei Konten und zwei Reisen (Beispielreise, Stadtwochenende): Werkzeuge, Suche, my_trips, Kalender, Meldungen, Belege, Rückmeldungen per Cookie, Schreiben; keine Namen oder Adressen aus Reise A in Antworten an B |
| engine/tests/test_grenzen.py (oder in test_trennung.py) | CREATE | Grenzen greifen, kommen aus der Instanz, Vorgaben wirken ohne Einstellung |
| docs/konten.md, docs/betrieb.md | MODIFY | Grenzen und Umgebungswerte beschreiben; Lesen über Seitenlink als bewusste Grenze |
| betrieb/einstellungen.beispiel | MODIFY | neue Werte mit Vorgabe dokumentieren |

### Scope Assessment
- Files: ~8
- Estimated LoC: +350/-10 (davon rund 250 Tests)
- Risk Level: MEDIUM — die Prüfung betrifft jeden Schreibvorgang im Konnektor; zu niedrige Vorgaben würden echte Arbeit bremsen. Deshalb großzügige Vorgaben (z. B. 10 Reisen, 300 Schreibvorgänge je Stunde) und Betreiber ausgenommen.

### Technical Approach
1. Zuerst die Testreihe mit zwei Konten schreiben (RED nur dort, wo eine Lücke auftaucht; der Rest belegt den Ist-Stand).
2. Grenzen als Instanzwerte über `instanz.wert(...)` mit Vorgabe; Zähler in der Konten-Datenbank (SQLite, ohne neue Datei in der Reise, daher kein Formatwechsel der Reisedaten und kein `nachziehen`). Die Konten-Datenbank bekommt eine Tabelle über die vorhandene Schema-Anlage in konten.py.
3. Welche Werkzeuge „schreibend“ sind, kommt aus der vorhandenen Einteilung der Werkzeuge (Rolle/Aktion), keine zweite Liste.
4. Verhalten bei Missbrauch: freundliche Ablehnung mit Wartezeit, Zeile im Dienstprotokoll; kein Alarm (keine Meldung per Telegram, Beobachtung höchstens über den Monitor-Check der Instanz).
5. Prüfbericht als Kommentar im Issue, ohne echte Reisen; Funde zu mehreren Mandanten nach #68.
6. Da Umgebungswerte und Texte neu sind: vor dem Vorspulen die Tests des Reisen-Repos mit dem Branch laufen lassen.

### Dependencies
konten.py (Datenbank, Rechte `betreiber`), instanz.py, konnektor.py (`frieda_werkzeug`, `reise_anlegen`), rueckmeldungen.py (Meldungen, Belege), waechter.py, Textkatalog.

### Open Questions
- keine Produktfrage: Lesen über den Seitenlink ist entschieden (#421); Grenzwerte sind Betriebsdetails (Vorgaben vom Tech Lead, Instanz kann sie ändern).
