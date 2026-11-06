---
entity_id: reisespeicher-346
type: feature
created: 2026-11-05
updated: 2026-11-05
status: draft
workflow: speicher-346-stufe1
version: "1.0"
tags: [reisespeicher, sqlite, betrieb, epic-345]
---

# Reisespeicher Stufe 1: Reisedaten als Versionen in SQLite, nur anhängen (#346, Epic #345, Weg C)

## Approval

- [ ] Approved

## Purpose

Die Reisedaten sollen als unveränderliche Versionen in einer SQLite-Datenbank liegen, statt als Git-Commits auf einem gemeinsamen Zweig. Stufe 1 baut nur den Speicher selbst: Schema, Import eines Reiseordners, Byte-gleicher Export (auch eines alten Stands), Verlauf, „Stand zurücksetzen“, Prüfung und Sicherung mit Rückspieltest. Dazu kommt ADR-0008. Die Funktionen sind zugleich die Schnittstelle, auf der Stufe 2 (#347, Schreibweg) aufbaut.

## Ziel und Abgrenzung

- **Im Scope:** neues Modul `engine/reisespeicher.py` (ohne Fremdbibliothek), Ort über `instanz.speicher()`, tägliche Sicherung durch den Wächter, ADR-0008, Betriebsdoku, Tests.
- **Der Schreibweg bleibt in Stufe 1 auf Git.** Der Umbau von `schreiben.py` ist #347. Stufe 1 ändert weder `schreiben.py`, `stand.py`, `konnektor.py` noch den Rückmeldedienst.
- **Kein Doppelschreiben:** Der Schreibweg schreibt in Stufe 1 nicht zusätzlich in den Speicher. Die Datenbank wird nur durch Import, Zurücksetzen und die Betreiber-Befehle beschrieben. Ein Schalter in den Reisen ist deshalb nicht nötig.
- **Kein Eintrag in `betrieb/deploy.sh`:** Die Liste dort enthält die Module, die ein Dienst importiert (Test in `engine/tests/test_betrieb.py`). In Stufe 1 importiert kein Dienst `reisespeicher.py`; der Eintrag kommt mit Stufe 2, sobald `schreiben.py` es nutzt. Der Wächter ruft das Modul als Befehl auf dem Server auf, das ist der Software-Stand auf dem Server, nicht die Dienstliste.
- **Kein `neu.py nachziehen`:** Das Format der Reisedaten (Dateien, Felder, IDs in `reise.yaml`, `plan/`, `inhalt/`, `medien/`) ändert sich nicht. Der Speicher legt eine Kopie der Dateien ab und ändert keine Datei einer Reise. Die Regel „jede Formatänderung bringt ihre Umstellung mit“ greift deshalb nicht; kein Handschritt in Reisen oder Instanzen ist nötig (#250).
- **Nicht im Scope:** Umbau von `schreiben.py`, `stand.py`, Konnektor (#347); Veröffentlichen und Nachziehen aus dem Speicher, Umstellung des alten Git-Verlaufs (Stufe 3); Auslagerung großer Fotos, Hash-Kette über Vorgänge (Stufe 4 bzw. später).

## Source

- **File:** `engine/reisespeicher.py` (neu); Vorbild für `db()` und `sichern()`: `engine/konten.py`
- **Identifier:** `db`, `vorgang_schreiben`, `stand_nummer`, `aktueller_stand`, `vorgang_eingetragen`, `verlauf`, `exportieren`, `importieren`, `zuruecksetzen`, `pruefen`, `sichern`, `main`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `sqlite3`, `hashlib` (Standardbibliothek) | Bibliothek | Datenbank (SQLite 3.45, WAL, Trigger, Authorizer, Online-Backup), SHA-256 der Bytes |
| `engine/instanz.py` | Modul | Ort des Speichers (`speicher()`, neu) |
| `engine/stand.py` (`zeit_iso`) | Funktion | Zeitstempel UTC mit `Z` |
| `engine/konten.py` | Modul (nur Vorbild) | Muster für `db()`, `user_version`, `sichern()` |
| `betrieb/waechter.sh` | Skript | tägliche Sicherung, Fehlschlag meldet `fr_melden high` |
| `betrieb/einstellungen.beispiel` | Vorlage | Zeile `FR_SPEICHER` (Test verlangt jeden `FR_`-Namen) |
| `docs/adr/0001-kern.md` | ADR | Prüfstelle |
| #347 (Stufe 2) | Issue | Verbraucher der Schnittstelle; eine parallele Sitzung arbeitet daran |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/reisespeicher.py` | CREATE | Modul wie unten |
| `engine/tests/test_reisespeicher.py` | CREATE | Tests zu allen Acceptance Criteria |
| `engine/instanz.py` | MODIFY | `speicher()`, `FR_SPEICHER`, Vorgabe `seiten() / "_speicher"`, Kopfkommentar |
| `betrieb/einstellungen.beispiel` | MODIFY | Zeile `FR_SPEICHER` |
| `betrieb/waechter.sh` | MODIFY | zweite Sicherung `reisespeicher.py sichern`, Fehlschlag → `fr_melden high`, Kopfkommentar |
| `engine/tests/test_betrieb.py` | MODIFY | Wächter-Attrappe und Erwartung der Sicherungen auf beide erweitern |
| `engine/tests/conftest.py`, `engine/tests/test_konten.py` | MODIFY | `FR_SPEICHER` in die Env-Listen, damit Tests sie nicht erben |
| `engine/tests/test_texte.py` | MODIFY (nur falls nötig) | Modul in `PY_DATEIEN`, falls es sichtbare Texte enthält; Befehlsausgaben für Betreiber sind englisch wie in `konten.py` |
| `docs/adr/0008-reisespeicher.md` | CREATE | Entscheidung Weg C, Variante B, Grenzen, Folgen für Stufen 2 bis 4 |
| `docs/adr/README.md` | MODIFY | Index-Zeile 0008 |
| `docs/betrieb.md` | MODIFY | Tabelle „Was wohin gehört“, Abschnitt Sicherung und Zurückholen, Wächter-Lauf |
| `betrieb/deploy.sh` | unverändert | erst Stufe 2 (siehe Abgrenzung) |

### Estimated Changes

- Files: 3 neu (Modul, Test, ADR), 9 geändert
- LoC: +700/-5 (davon etwa 300 Modul, 250 Tests, 120 Doku)

## Implementation Details

### Was ist eine Version? (Variante B)

Zwei Tabellen: `vorgaenge` (ein Vorgang = ein Schreibvorgang, Angaben einmal) und `versionen` (je Vorgang eine Zeile je geänderte Datei). Die Stand-Nummer zählt Vorgänge, wie heute `stand.nummer` Commits zählt; „Stand-Nummer = Zahl der Versionen“ aus #346 ist die Kurzform dieses Verhaltens (je Schreibvorgang +1, #226) und wird so in ADR-0008 und als Kommentar in #346 festgehalten. Würde jede Datei-Version zählen, spränge die Seitenzahl beim Import um die Dateizahl und bei einem Vorgang mit drei Dateien um drei.

### Schema (`PRAGMA user_version = 1`, `CREATE ... IF NOT EXISTS` wie in `konten.py`)

```
vorgaenge(
  nummer   INTEGER PRIMARY KEY AUTOINCREMENT,  -- global, nie neu vergeben
  reise    TEXT NOT NULL,
  stand    INTEGER NOT NULL,                   -- Stand-Nummer der Reise
  wann     TEXT NOT NULL,                      -- UTC "...Z" (stand.zeit_iso)
  wer      TEXT NOT NULL, rolle TEXT NOT NULL DEFAULT '',
  werkzeug TEXT NOT NULL, titel TEXT NOT NULL, grund TEXT NOT NULL DEFAULT '',
  kennung  TEXT UNIQUE,                        -- Wert des Aufrufers (heute FR_VORGANG), NULL erlaubt
  herkunft TEXT NOT NULL DEFAULT '',           -- "import:<ordnername>", "zuruecksetzen:<stand>"
  UNIQUE(reise, stand), UNIQUE(nummer, reise))
versionen(
  vorgang INTEGER NOT NULL, reise TEXT NOT NULL, pfad TEXT NOT NULL,
  inhalt BLOB,                                 -- NULL = gelöscht (Tombstone)
  pruefsumme TEXT,                             -- SHA-256 hex der Bytes, NULL bei Tombstone
  PRIMARY KEY(vorgang, pfad),
  FOREIGN KEY(vorgang, reise) REFERENCES vorgaenge(nummer, reise))
INDEX versionen_pfad ON versionen(reise, pfad, vorgang)
```

`titel` und `rolle` ergänzen das Schema aus #346: Der Commit trägt heute Titel und Text, `stand.aenderungen()` zeigt den Titel; ohne Spalte verlöre Stufe 2 die Anzeige.

### Semantik

- **Stand-Nummer:** Jeder Vorgang einer Reise bekommt `stand = max(stand der Reise) + 1`, berechnet innerhalb von `BEGIN IMMEDIATE`. Der Anfangsvorgang des Imports bekommt `stand = ab + 1` (Vorgabe `ab = 0`; Stufe 3 übergibt die bisherige Git-Zahl, damit Seiten nicht zurückspringen). Die Nummern sind nicht lückenlos garantiert, aber streng steigend. `stand_nummer(reise)` liefert `max(stand)`, nie `COUNT`, und `None` für eine unbekannte Reise (wie `stand.nummer`).
- **`nummer` und `stand` sind verschiedene Dinge:** `nummer` ist global und eindeutig (Vorgangs-Nummer), `stand` gilt je Reise und ist das, was die Seite zeigt.
- **Stand `s` einer Reise:** je Pfad die Zeile mit dem höchsten `vorgang` unter den Vorgängen der Reise mit `stand <= s`; ist deren `inhalt` NULL, fehlt die Datei in diesem Stand.
- **Tombstones:** Löschen schreibt eine Zeile mit `inhalt` und `pruefsumme` NULL. Export und Zurücksetzen lassen solche Pfade weg; Wiederkehr der Datei ist eine neue Version.
- **Unveränderte Dateien** (Prüfsumme gleich der des aktuellen Stands) erzeugen keine Zeile; ein Löschen einer ohnehin fehlenden Datei auch nicht.
- **Leerer Vorgang = Fehler:** Bleibt nach dem Überspringen keine Änderung, wird kein Vorgang angelegt (`ValueError`, wie „nichts geändert“ im Schreibweg).
- **Kennung idempotent:** Existiert die `kennung` schon, wird nichts geschrieben und `VorgangVorhanden(nummer, stand)` ausgelöst. Der Aufrufer erzeugt die Kennung vor dem Schreiben; nur so geht die Nachprüfung nach einer Zeitüberschreitung (`vorgang_eingetragen`).
- **Eine Datenbank je Instanz:** `reise` steht in jeder Zeile, eine Aufteilung bleibt später möglich. Je Verbindung `PRAGMA foreign_keys = ON`, `recursive_triggers = ON`, `timeout = 10`; WAL beim Anlegen; Schreiben mit `BEGIN IMMEDIATE`. Sperrfehler gehen als `sqlite3.OperationalError` an den Aufrufer. Die Sperre je Reise bleibt in `schreiben.py`. `executescript` committet implizit; der Schema-Aufbau liegt deshalb getrennt von Transaktionen.

### Öffentliche Schnittstelle (Grundlage für #347)

| Funktion | Verhalten |
|----------|-----------|
| `pfad() -> Path` | `instanz.speicher() / "reisen.db"` |
| `db() -> sqlite3.Connection` | legt Ordner (0700) und Datei (0600) an, WAL, `foreign_keys`, `recursive_triggers`, Schema und Trigger (`IF NOT EXISTS`), setzt `user_version`, installiert danach den Authorizer; Zeilen als `sqlite3.Row` |
| `vorgang_schreiben(reise, dateien: dict[str, bytes \| None], wer, werkzeug, titel, grund="", kennung=None, rolle="", wann=None, herkunft="") -> Vorgang` | eine Transaktion; `None` als Wert = löschen; Pfade werden geprüft (siehe Import); unveränderte Dateien übersprungen; ohne Änderung `ValueError`; bekannte Kennung `VorgangVorhanden`; `wann=None` heißt jetzt (UTC); Rückgabe `Vorgang(nummer, stand)` (benanntes Tupel) |
| `VorgangVorhanden(nummer, stand)` | Ausnahme mit denselben Feldern; „Wiederholung ungefährlich“ |
| `stand_nummer(reise) -> int \| None` | `max(stand)` oder `None` |
| `aktueller_stand(reise, bis=None) -> dict[str, bytes]` | Pfad → Bytes der Reise im Stand `bis` (Stand-Nummer), ohne `bis` der neueste; unbekannter Stand oder unbekannte Reise: `KeyError` |
| `vorgang_eingetragen(kennung) -> Vorgang \| None` | ersetzt `git log --grep Frieda-Vorgang`; kein Schreibzugriff |
| `verlauf(reise, n=None) -> list[dict]` | neueste zuerst; je Eintrag `nummer` (= Stand, wie `stand.aenderungen`), `zeit`, `was` (= Titel), `wer`, dazu `vorgang`, `werkzeug`, `grund`, `dateien` (Pfade, die der Vorgang berührt hat) |
| `exportieren(reise, ziel, bis=None)` | schreibt den Stand in `ziel`; `ziel` fehlt oder ist ein leerer Ordner, sonst `FileExistsError`; kein Überschreiben |
| `importieren(ordner, reise, wer, grund="", ab=0) -> Vorgang` | liest einen Reiseordner als Anfangsvorgang (`werkzeug = "importieren"`, `herkunft = "import:<ordnername>"`); ist die Reise schon vorhanden, wirkt der Import wie jeder andere Vorgang (nur Unterschiede, Tombstones für fehlende Dateien) |
| `zuruecksetzen(reise, bis, wer, grund) -> Vorgang` | neuer Vorgang (`werkzeug = "zuruecksetzen"`, `herkunft = "zuruecksetzen:<bis>"`) mit neuen Versionen für alle Pfade, die vom Stand `bis` abweichen (alter Inhalt oder Tombstone); `wer` und `grund` Pflicht (leer: `ValueError`); keine Abweichung: Fehler, kein Vorgang; der Verlauf wird nie gekürzt |
| `pruefen(reise=None) -> list` | rechnet je Version die SHA-256 neu, prüft `integrity_check`, die Stand-Folge je Reise und dass Tombstones keinen Inhalt haben; Liste der Abweichungen (leer = in Ordnung); eigene Verbindung |
| `sichern() -> Path \| None` | Schnappschuss, siehe Sicherung; `None`, wenn es noch keine Datenbank gibt |
| `main(a)` | Befehle `importieren`, `exportieren [--bis N]`, `verlauf`, `zuruecksetzen`, `pruefen`, `sichern`; Docstring „Aufrufe:“; Ausgaben englisch wie `konten.py`; Exitcode ungleich 0 bei Fehler oder Abweichung |

### Nur anhängen: zwei Schichten und die ehrliche Grenze

SQLite kennt keine Benutzerrechte. Der Schutz hat zwei Schichten:

1. **Trigger** `BEFORE UPDATE` und `BEFORE DELETE` auf beiden Tabellen mit `RAISE(ABORT)`, dazu `PRAGMA recursive_triggers = ON`, sonst löscht `INSERT OR REPLACE`, ohne dass ein DELETE-Trigger feuert.
2. **`set_authorizer`** in der Verbindung von `db()`, erst nach dem Schema-Aufbau: verweigert UPDATE und DELETE auf beide Tabellen, `DROP TABLE`, `DROP TRIGGER`, `DROP INDEX`, `ALTER TABLE` und `PRAGMA writable_schema`. Im Test wird zusätzlich `SQLITE_DBCONFIG_DEFENSIVE` ausprobiert; es ist keine Voraussetzung.

`sichern()` und `pruefen()` benutzen eigene Verbindungen, die nichts davon umgehen müssen (Lesen und Backup).

**Ehrliche Grenze (steht so in ADR-0008):** Das schützt vor Software-Fehlern und Fehlbedienung über `db()`, nicht vor jemandem, der die Datei selbst öffnet und die Trigger entfernt. Gegenmittel sind `pruefen` (Prüfsummen neu rechnen) und die Sicherung außer Haus.

### Import und Export

- **Was zum Ordner zählt:** alle regulären Dateien rekursiv, auch versteckte (`.gitkeep`). Nicht: der Ordner `.git`. Ein Symlink bricht den Import mit Fehler ab (kein stilles Auslassen). Leere Ordner bleiben nicht erhalten (ADR-0008). Rechte und Zeitstempel werden nicht gespeichert. `reise.json` ist Quelle und kommt mit.
- **Byte-gleich** heißt: gleiche Pfadmenge und gleiche Bytes, nicht gleiche Zeitstempel. Dateien werden nur binär gelesen und geschrieben (kein `read_text`, keine Zeilenend-Umwandlung); Inhalt als BLOB, nicht als TEXT.
- **Pfadregeln** (Import, `vorgang_schreiben`, Export): POSIX-Schreibweise, relativ, kein `..`, kein NUL, kein führender Schrägstrich, nicht leer, keine leeren Teile. Der Export prüft zusätzlich, dass jeder aufgelöste Zielpfad im Ziel bleibt; sonst `ValueError` und nichts wird geschrieben.
- **Export:** nur in ein fehlendes oder leeres Ziel; Dateien 0644, Ordner 0755 (die Rechte der Reise-Ordner sind in Git ohnehin nicht Teil des Inhalts).

### Ort und Sicherung

- **Ort:** `instanz.speicher()` liefert den Ordner. Wert `FR_SPEICHER` aus `betrieb/einstellungen.env` des Reisen-Repos; Vorgabe `instanz.seiten() / "_speicher"`. Im Kopfkommentar von `instanz.py` dokumentiert (Muster `konten()`); `betrieb/einstellungen.beispiel` bekommt die Zeile. Nichts Instanzspezifisches im Code.
- **Sicherung** wie `konten.sichern()`: Online-Backup (`sqlite3.Connection.backup`) in eine Temp-Datei im Ordner `<Speicher>/sicherung/`, in der Kopie `journal_mode = DELETE`, `integrity_check` muss `ok` liefern, dann atomar `os.replace` auf `<Speicher>/sicherung/reisen.db`. Schlägt etwas fehl, bleibt die letzte gute Sicherung unberührt.
- **Wächter:** `betrieb/waechter.sh` ruft täglich zusätzlich `reisespeicher.py sichern` auf; Fehlschlag meldet `fr_melden high`, und ein Fehler bei der einen Sicherung verhindert die andere nicht.
- **Außer Haus:** Das Wegbringen der Datei ist Sache des Server-Backups der Instanz (steht in `docs/betrieb.md`); Stufe 1 liefert den stimmigen Schnappschuss und den Rückspieltest.

### Dokumentation

- `docs/adr/0008-reisespeicher.md` nach dem Aufbau von ADR-0005 (Status, Kontext, Entscheidung, Begründung, Konsequenzen, Verlauf): Weg C und Variante B, anonyme Messwerte aus #345 (379 Vorgänge in rund einem Monat, mittlere Dauer 2,7 s, 5 verloren, 92 % der Dateien Fotos), Grenzen (nur anhängen, leere Ordner, Rechte, Zeitstempel), Folgen für die Stufen 2 bis 4 (Stufe 3: Anfangsvorgang mit Vermerk „vorher in Git“ und übernommener Stand-Nummer genügt; Stufe 4: Auslagerung der Fotos, Hash-Kette). Keine Namen echter Reisen, keine Adressen.
- `docs/adr/README.md`: Index-Zeile 0008.
- `docs/betrieb.md`: Ablage (`FR_SPEICHER`) in „Was wohin gehört“, Sicherung und Zurückholen (Schnappschuss einsetzen, `pruefen`, Export vergleichen), Wächter-Lauf mit zweiter Sicherung.

## Prüfstelle (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Der Speicher kennt nur Pfade und Bytes, nichts Reisespezifisches; getestet an beiden Beispielreisen (Wanderung und Städtewochenende). |
| 2 Kein Katalog | Keine Art, kein Merkmal. |
| 3 Keine KI | Keine; reine Regeln und Prüfsummen. |
| 4 Die Tür | Stufe 1 hat keine neue Funktion für den AI-Client; die Anbindung an den Konnektor kommt mit Stufe 2 (#347). Nicht anwendbar, kein Widerspruch. |
| 5 Herkunft | Es entstehen keine neuen Aussagen der Reise; jeder Vorgang trägt Person, Werkzeug, Grund und Zeit. |
| 6 Rollen entscheiden | Keine Entscheidung wird berührt; Zurücksetzen verlangt Person und Grund. |
| 7 IDs und Verlauf | Nichts wird vergeben, gelöscht oder ohne Verlauf überschrieben; der Verlauf ist unveränderlich (Trigger, Authorizer). Zurücksetzen ist ein neuer Vorgang. |
| 8 PWA | Nicht berührt; Seite und Offline-Verhalten bleiben unverändert (kein Browser-Rundgang nötig). |
| 9 Claude Code | Reiseinhalte entstehen weiterhin nicht in Claude Code. |
| 10 Dokumentation | ADR-0008, `docs/betrieb.md`, diese Spec; ADR-0008 verweist auf ADR-0001 (Punkt 8: Technik ist Mittel). |

## Test Plan

### Automated Tests (TDD RED)

Datei `engine/tests/test_reisespeicher.py` (ohne Git, mit `tmp_path` und `FR_SPEICHER`, zusammen unter 5 Sekunden):

- [ ] Test 1: GIVEN eine der beiden Beispielreisen WHEN importiert und in ein leeres Ziel exportiert THEN sind Pfadmenge und alle Bytes gleich (rekursiver Vergleich, parametrisiert über `beispielreise` und `stadtwochenende`).
- [ ] Test 2: GIVEN eine Reise mit drei Vorgängen (Änderung, Löschung, Wiederkehr) WHEN mit `bis=` ein alter Stand exportiert wird THEN entspricht der Export diesem Stand, gelöschte Dateien fehlen.
- [ ] Test 3: GIVEN eine Verbindung aus `db()` WHEN UPDATE, DELETE, `INSERT OR REPLACE`, `DROP TRIGGER` oder `DROP TABLE` auf `vorgaenge` oder `versionen` läuft THEN scheitert jede Anweisung, und die Daten sind unverändert.
- [ ] Test 4: GIVEN ein Vorgang mit Kennung WHEN `vorgang_schreiben` mit derselben Kennung wiederholt wird THEN `VorgangVorhanden` mit gleicher Nummer und Stand, keine neue Zeile; `vorgang_eingetragen` findet ihn, unbekannte Kennung gibt `None`.
- [ ] Test 5: GIVEN `ab=40` beim Import WHEN danach zwei Vorgänge folgen THEN ist `stand_nummer` 41, 42, 43 und ein Vorgang mit drei Dateien zählt +1; unbekannte Reise gibt `None`.
- [ ] Test 6: GIVEN unveränderte Dateien WHEN ein Vorgang nur sie enthält THEN `ValueError` und kein Vorgang; bei gemischtem Inhalt entstehen Zeilen nur für Geändertes.
- [ ] Test 7: GIVEN ein Stand mit Änderungen WHEN `zuruecksetzen` auf einen alten Stand läuft THEN gibt es einen neuen Vorgang mit neuem `stand`, `herkunft = "zuruecksetzen:<bis>"`, der Verlauf bleibt vollständig, `aktueller_stand` gleicht dem alten Stand; ohne Abweichung oder ohne Grund Fehler.
- [ ] Test 8: GIVEN ein Ordner mit Symlink, ein Pfad mit `..` oder mit NUL-Byte (in `vorgang_schreiben` und beim Export) oder ein nicht leeres Ziel WHEN importiert bzw. exportiert wird THEN Fehler, und nichts wird außerhalb des Ziels geschrieben.
- [ ] Test 9: GIVEN eine Datenbank WHEN `sichern()` läuft THEN liegt `sicherung/reisen.db` vor, besteht `integrity_check`; als neue Datenbank an einem anderen Ort eingesetzt und geöffnet, gleicht der Export dem Original (Rückspieltest).
- [ ] Test 10: GIVEN eine absichtlich in der Datei verfälschte Prüfsumme (Test öffnet die Datei ohne Authorizer und ohne Trigger) WHEN `pruefen()` läuft THEN meldet es die Abweichung mit Reise und Pfad; bei gesunden Daten ist die Liste leer.
- [ ] Test 11: GIVEN die Befehle WHEN `main` mit `importieren`, `verlauf`, `exportieren --bis`, `zuruecksetzen`, `pruefen`, `sichern` läuft THEN stimmen Ausgabe und Exitcode.
- [ ] Test 12: GIVEN `FR_SPEICHER` gesetzt bzw. nicht gesetzt WHEN `instanz.speicher()` fragt THEN der gesetzte Ort bzw. `seiten()/"_speicher"`.
- [ ] Test 13 (`engine/tests/test_betrieb.py`): GIVEN die Wächter-Attrappe WHEN `waechter.sh` läuft THEN werden beide Sicherungen aufgerufen, ein Fehlschlag der Reisen-Sicherung meldet `high`, und die Konten-Sicherung läuft trotzdem; `test_beispiel_einstellungen_sind_vollstaendig` kennt `FR_SPEICHER`; der Test zur Modulliste in `deploy.sh` bleibt unverändert grün.

- [ ] Test 14: GIVEN der Quelltext von `engine/schreiben.py`, `engine/konnektor.py`, `engine/rueckmeldungen.py` und `engine/stand.py` WHEN nach `reisespeicher` gesucht wird THEN kein Treffer (der Schreibweg schreibt in Stufe 1 nicht in den Speicher); die Modulliste in `betrieb/deploy.sh` enthält `reisespeicher.py` nicht (bestehender Modullisten-Test bleibt grün).
- [ ] Test 15: GIVEN die Doku WHEN gelesen THEN existiert `docs/adr/0008-reisespeicher.md` mit den Abschnitten Status, Kontext, Entscheidung, Begründung, Konsequenzen, Verlauf und einem Satz zur Grenze des Nur-anhängen-Schutzes (Stichwort „Schreibzugriff auf die Datei“), `docs/adr/README.md` hat eine Zeile mit `0008`, `docs/betrieb.md` nennt `FR_SPEICHER` und `reisespeicher.py sichern`.
- [ ] Test 16: GIVEN `PATH` zeigt nur auf einen leeren Ordner (kein `git` auffindbar) WHEN Import, Vorgang, Export und Sicherung laufen THEN gelingen sie; der Quelltext von `engine/reisespeicher.py` enthält weder `subprocess` noch Präfixe von Systempfaden (Liste im Test), keinen eigenen Zugriff auf `os.environ` (Werte nur über `instanz`) und keine Domain- oder Mail-Adressen (Muster im Test).

Anpassungen ohne eigenen Test: `FR_SPEICHER` in die Env-Listen von `engine/tests/conftest.py` und `engine/tests/test_konten.py`; `engine/tests/test_texte.py` nur, falls das Modul sichtbare Texte enthält.

Lauf: `engine/.venv/bin/python -m pytest -q engine/tests/test_reisespeicher.py engine/tests/test_betrieb.py`, danach der volle Lauf `engine/.venv/bin/python -m pytest -q engine/tests` (mit `-n auto`).

## Definition of Done

Fertig ist diese Änderung, wenn:

- [ ] Jede Acceptance Criterion unten ist durch einen automatischen Test belegt
- [ ] Beide Beispielreisen gehen Byte-gleich durch Import und Export, auch für alte Stände
- [ ] Der Verlauf lässt sich über `db()` weder ändern noch löschen
- [ ] Die tägliche Sicherung läuft im Wächter, ein Rückspieltest ist grün
- [ ] ADR-0008, Index und `docs/betrieb.md` beschreiben Speicher, Sicherung, Zurückholen und die Grenze des Schutzes
- [ ] Schreibweg, Konnektor und `deploy.sh` sind unverändert (Stufe 2 bleibt #347)
- [ ] `engine/tests/test_reisespeicher.py` läuft in unter 5 Sekunden (gemessen mit `--durations`, im Protokoll der Validierung festgehalten)
- [ ] Keine bestehende Funktion ist dabei kaputtgegangen (voller Lauf `engine/tests` grün)

## Acceptance Criteria

- **AC-1:** Import und Export beider Beispielreisen (`beispiel/reisen/beispielreise`, `beispiel/reisen/stadtwochenende`) liefern einen Ordner mit gleicher Pfadmenge und Byte für Byte gleichen Dateien (Test 1).
- **AC-2:** `exportieren(reise, ziel, bis=N)` liefert den Stand N einschließlich fehlender (gelöschter) Dateien und Dateien in alter Fassung (Test 2).
- **AC-3:** Über `db()` scheitern UPDATE, DELETE, `INSERT OR REPLACE`, `DROP TRIGGER` und `DROP TABLE` auf beiden Tabellen; die Daten bleiben unverändert (Test 3).
- **AC-4:** Eine bekannte Kennung schreibt nichts und löst `VorgangVorhanden(nummer, stand)` aus; `vorgang_eingetragen(kennung)` findet den Vorgang (Test 4).
- **AC-5:** `stand_nummer` ist `max(stand)`: Import mit `ab=N` ergibt `N+1`, jeder weitere Vorgang `+1` unabhängig von der Zahl der Dateien; unbekannte Reise gibt `None` (Test 5).
- **AC-6:** Unveränderte Dateien erzeugen keine Versionszeile; ein Vorgang ohne jede Änderung ist ein Fehler und legt nichts an (Test 6).
- **AC-7:** `zuruecksetzen` erzeugt einen neuen Vorgang mit Person und Grund, der Verlauf bleibt vollständig, und der neue Stand gleicht dem Ziel-Stand (Test 7).
- **AC-8:** Symlinks, Pfade mit `..` oder NUL, ein nicht leeres Export-Ziel werden abgelehnt, und außerhalb des Ziels wird nichts geschrieben (Test 8).
- **AC-9:** `sichern()` erzeugt `<Speicher>/sicherung/reisen.db` mit bestandenem `integrity_check`; der Rückspieltest (Schnappschuss als neue Datenbank, Export vergleichen) ist grün (Test 9).
- **AC-10:** `pruefen()` findet eine manipulierte Prüfsumme und meldet Reise und Pfad; bei gesunden Daten ist die Liste leer (Test 10).
- **AC-11:** `instanz.speicher()` folgt `FR_SPEICHER` mit Vorgabe `seiten() / "_speicher"`; `betrieb/einstellungen.beispiel` enthält `FR_SPEICHER`; `engine/reisespeicher.py` enthält keine Instanzwerte (Ort nur über `instanz.speicher()`) (Test 12, Test 16 und `test_beispiel_einstellungen_sind_vollstaendig`).
- **AC-12:** `betrieb/waechter.sh` sichert täglich beide Datenbanken; ein Fehlschlag der Reisen-Sicherung meldet `fr_melden high`, ohne die Konten-Sicherung zu verhindern (Test 13).
- **AC-13:** Weder `betrieb/deploy.sh` noch Schreibweg, Konnektor, Rückmeldedienst oder `stand.py` binden `reisespeicher` ein; der Test zur Modulliste ist grün, und der Schreibweg schreibt nicht in den Speicher (Test 14).
- **AC-14:** ADR-0008 (`docs/adr/0008-reisespeicher.md`) mit Index-Zeile in `docs/adr/README.md` und die Ergänzungen in `docs/betrieb.md` liegen vor; ADR-0008 nennt die ehrliche Grenze des Nur-anhängen-Schutzes (Test 15); `engine/tests/test_protokolle_ohne_pfade.py` bleibt grün.
- **AC-15:** Import, Vorgang, Export und Sicherung gelingen ohne auffindbares `git` (Test 16).
- **AC-16:** Die Befehle `importieren`, `exportieren [--bis N]`, `verlauf`, `zuruecksetzen`, `pruefen`, `sichern` über `main` liefern die erwartete Ausgabe und Exitcode 0, bei Fehlern einen Exitcode ungleich 0 (Test 11).

## Known Limitations

- Der Nur-anhängen-Schutz hält Software-Fehler und Fehlbedienung ab, nicht jemanden mit Schreibzugriff auf die Datei (siehe oben).
- Leere Ordner sowie Rechte und Zeitstempel von Dateien bleiben nicht erhalten.
- Eine Datenbank je Instanz: SQLite sperrt beim Schreiben die ganze Datei. Bei den gemessenen Raten (379 Vorgänge in rund einem Monat) genügt WAL mit `timeout = 10`; der Messlauf in #347 bestätigt das.
- Große Fotos liegen als BLOB in der Datenbank (Beispielreisen unter 200 KB je Datei); Auslagerung ist Stufe 4.
- Der alte Git-Verlauf wird in Stufe 1 nicht übernommen (Stufe 3).

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** ADR-0008 (`docs/adr/0008-reisespeicher.md`, Teil dieser Änderung)
- **Rationale:** Der Speicher ersetzt auf Dauer Git als Träger der Reisedaten (Epic #345, Weg C, Entscheidung des Product Owners vom 5.11.2026). Das ist eine Architekturänderung am Ort der Wahrheit, berührt aber die Grundformen und Merkmale nicht (ADR-0001, Punkt 8: Technik ist Mittel, nicht Kern). Variante B, Stand-Nummer je Vorgang, die Grenze des Nur-anhängen-Schutzes und die Folgen für die Stufen 2 bis 4 gehören deshalb in ein ADR.

## Changelog

- 2026-11-05: Initial spec created
- 2026-11-05: Definition of Done ergänzt; Tests 14–16 für AC-13, AC-14, AC-15 und „keine Instanzwerte“ (Befund des Spec-Validators)
- 2026-11-05: Laufzeit und Gesamtlauf aus AC-15 in die Definition of Done; AC-11 und AC-14 präzisiert (zweiter Validator-Lauf)
- 2026-11-05: NUL-Pfad in Test 8, Instanzwerte in Test 16, AC-13 als prüfbare Aussage, AC-16 für die Befehle (dritter Validator-Lauf)
- 2026-11-06: ADR-Nummer 0008 war auf main inzwischen an „Der Ort ist eine Station der Reise“ (#335) vergeben; das ADR dieser Spec heißt deshalb ADR-0009 (`docs/adr/0009-reisespeicher.md`). Wo oben ADR-0008 steht, ist ADR-0009 gemeint.
