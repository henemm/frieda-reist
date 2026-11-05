# Context: speicher-346-stufe1

## Request Summary

Stufe 1 des Epics #345 (Weg C, Entscheidung des Product Owners 5.11.2026): Reisedaten als Versionen in einer SQLite-Datenbank, nur anhängen. Diese Stufe baut nur den Speicher selbst (Schema, Import eines Reiseordners, Byte-gleicher Export, Verlauf, „Stand zurücksetzen“, Sicherung mit Rückspieltest) und schreibt ADR-0008. Der Schreibweg bleibt in dieser Stufe auf Git (das ist #347).

## Related Files

| File | Relevance |
|------|-----------|
| `engine/konten.py` (`db()`, `sichern()`, Z. 154–179 und 946–970) | Vorbild: SQLite mit WAL, Ordner 700/Datei 600, `user_version` für Schema-Stufen, Schnappschuss über `sqlite3.Connection.backup`, `journal_mode = DELETE` in der Kopie, `integrity_check`, atomar per `os.replace` |
| `engine/instanz.py` | Ablageorte einer Instanz (`seiten()`, `ablage()`, `dienst()`, `konten()`); der Ort der neuen Datenbank kommt hierher (neue Funktion, Wert `FR_…` aus `betrieb/einstellungen.env`, Vorgabe unter `<Seiten>/_…`) |
| `engine/stand.py` | Heutige Stand-Nummer = `git rev-list --count HEAD -- <ordner>`; Änderungsliste aus Commits mit Trailer `Frieda-Person`. Wird in Stufe 1 nicht umgebaut, aber die neue Stand-Nummer (Zahl der Versionen) muss dazu passen (Stufe 2) |
| `engine/schreiben.py` (Z. 63, 4224–4225, 4340–4345) | Vorgangs-Kennung heute: Env `FR_VORGANG` → Git-Trailer `Frieda-Vorgang:`; `vorgang_eingetragen` sucht ihn nach Zeitüberschreitung auf `origin/main`. Die Vorgangs-Nummer der Datenbank (eindeutig) ersetzt das in Stufe 2 |
| `engine/neu.py` (Z. 107, 180) | Kennt den Aufbau eines Reiseordners (Textdateien `.md/.yaml/.yml/.json`, `medien/`) |
| `betrieb/waechter.sh` (Z. 8, 24–25) | Ruft täglich `konten.py sichern` auf, meldet Fehlschlag dringend; die Sicherung der Reisen-Datenbank gehört analog hierher |
| `betrieb/deploy.sh` (Z. 21–27) | Modullisten der Dienste; ein neues Modul gehört erst hinein, wenn ein Dienst es importiert (Stufe 2) — Test in `engine/tests/test_betrieb.py` prüft das |
| `docs/betrieb.md` (Z. 34, 184) | Abschnitt „Sicherung“ (Konten-Schnappschuss, Zurückholen) und Wächter-Lauf; dort kommen Ablage und Sicherung der Reisen-Datenbank dazu |
| `docs/adr/README.md`, `docs/adr/0005-konten.md` | Aufbau eines ADR (Status, Kontext, Entscheidung, Begründung, Konsequenzen, Verlauf) und Index-Tabelle, in die ADR-0008 kommt |
| `engine/tests/test_konten.py:467` | Vorbild-Test `test_sichern_schreibt_einen_stimmigen_schnappschuss` |
| `engine/tests/test_betrieb.py:1740–1746` | Tests des Wächters zur Sicherung (Fehlschlag meldet sich, Fehler sichert trotzdem) |
| `engine/tests/test_protokolle_ohne_pfade.py` | Prüft, dass Kontext/Spec/Protokolle keine Pfade relativ zu `~` enthalten |
| `beispiel/reisen/beispielreise`, `beispiel/reisen/stadtwochenende` | Testgrundlage für Import/Export (Akzeptanz: beide Byte-gleich) |

## Existing Patterns

- **SQLite-Modul mit `db()`**: legt Ordner/Datei mit engen Rechten an, WAL beim Anlegen, `executescript(SCHEMA)` mit `CREATE … IF NOT EXISTS`, Schema-Wechsel über `PRAGMA user_version` (konten.py).
- **Sicherung**: `quelle.backup(kopie)` in eine Temp-Datei, `integrity_check`, dann `os.replace` auf `<ordner>/sicherung/<name>.db`; Aufruf über Unterbefehl `sichern`, täglich aus `waechter.sh`, Fehlschlag → `fr_melden high`.
- **Befehle**: Module haben `main(a)` mit Unterbefehlen (`liste`, `sichern` …) und Docstring mit „Aufrufe:“.
- **Orte**: Nie feste Pfade; alles über `instanz.py` und `FR_…`-Werte, Vorgabe unter `<Seiten>/_<name>`.
- **Texte**: Meldungen an Menschen über `texte.t(...)` aus `engine/texte_<sprache>.py` (ADR-0006); Betreiber-Befehle drucken heute englisch (siehe `konten.liste`, `waechter.sh`-Meldungen).
- **Kennungen und Zeiten**: Zeiten UTC als ISO mit `Z` (`stand.zeit_iso`).

## Dependencies

- Upstream: Python-Standardbibliothek `sqlite3` (SQLite 3.45.1 im venv, Python 3.12.3) — keine neue Fremdbibliothek nötig; `hashlib` für die Prüfsumme; `instanz.py` für den Ort.
- Downstream (in dieser Stufe): Befehle für den Betreiber, `waechter.sh` (Sicherung), Tests. Ab Stufe 2: `schreiben.py`, `stand.py`, `konnektor.py`, Rückmeldedienst; ab Stufe 3: `veroeffentlichen.sh`, `software-nachziehen.sh`.

## Existing Specs

- Keine Spec zum Reisespeicher. Verwandt: `docs/context/schreibweg-zeitgrenzen-118-121.md` (Vorgangs-Kennung, Nachprüfung nach Zeitüberschreitung), `docs/context/software-wechsel-ohne-handarbeit-250.md` (keine Handschritte).

## Inhalt eines Reiseordners (gemessen an den Beispielreisen)

- Wanderung (136 KB): `reise.yaml`, `reise.json`, `CLAUDE.md`, `offene-fragen.md`, `plan/` (5), `inhalt/` (6, `.md`/`.yaml`), `medien/` (SVG, PNG, `gpx/` mit 4 GPX).
- Städtewochenende (44 KB): `reise.yaml`, `reise.json`, `ids.yaml`, `offene-fragen.md`, `plan/` (3), `inhalt/` (1); keine Medien.
- Keine Symlinks, keine leeren Ordner, keine ausführbaren Dateien, nichts über 200 KB.

## Fragen für die Analyse (nicht hier entscheiden)

1. **Was ist eine „Version“?** Issue: Zeile je (Reise, Pfad, Versionsnummer). „Stand-Nummer = Zahl der Versionen“ würde dann nach dem Import gleich der Dateizahl sein und bei einem Vorgang, der drei Dateien ändert, um drei springen. Alternative: Vorgang als Einheit (Stand-Nummer = Zahl der Vorgänge, Zeilen je Datei hängen am Vorgang). Heute zählt `stand.nummer` Commits, also Vorgänge.
2. **Gelöschte Dateien** im Verlauf (Tombstone-Zeile mit Inhalt NULL?), damit „Export eines alten Stands“ und „Stand zurücksetzen“ stimmen.
3. **Binärdateien** (PNG, GPX) bis Stufe 4 als BLOB in derselben Tabelle oder schon jetzt ausgeklammert? Akzeptanz verlangt Byte-gleichen Ordner, also gehören sie in Stufe 1 mit hinein (oder die Akzeptanz wird auf Textdateien begrenzt — Product Owner).
4. **Was zählt zum Ordner?** Dateirechte, `.gitkeep`, versteckte Dateien, gebaute Dateien (`reise.json` ist gebaut oder Quelle?); Byte-gleich heißt: gleiche Pfade und gleicher Inhalt, nicht gleiche Zeitstempel.
5. **„Nur Rechte zum Einfügen“**: SQLite kennt keine Benutzerrechte. Möglich sind Trigger `BEFORE UPDATE/DELETE … RAISE(ABORT)` und ggf. eine Autorisierungs-Rückruffunktion (`set_authorizer`) in der Verbindung des Dienstes, die `UPDATE`, `DELETE`, `DROP` verweigert. Wer Schreibrecht auf die Datei hat, kann Trigger dennoch entfernen — das gehört ehrlich ins ADR.
6. **„Stand zurücksetzen“**: legt neue Versionen mit altem Inhalt an — als ein Vorgang, mit Grund und Person.
7. **Eine Datenbank je Instanz oder je Reise?** Epic: „Alle Reisen schreiben auf einen Zweig“ war ein Engpass; SQLite sperrt beim Schreiben die ganze Datei. Bei den gemessenen Raten (379 Vorgänge in rund einem Monat) reicht eine Datei mit WAL; je Reise wäre Isolation, aber mehr Sicherungen.
8. **Sicherung „außer Haus“** (Epic) — Stufe 1 liefert den stimmigen Schnappschuss wie bei den Konten; das Wegbringen ist Sache des Server-Backups der Instanz (Doku), Rückspieltest in den Tests.

## Risks & Considerations

- **Nichts Instanzspezifisches**: Ort der Datenbank über `instanz.py` und einen `FR_…`-Wert, Vorgabe neben den Konten bzw. Seiten.
- **Kein Doppelschreiben** (Epic): Stufe 1 schreibt nur per Import/Befehl, nicht aus dem Schreibweg; kein Schalter in Reisen nötig.
- **Formatwechsel**: Das Dateiformat der Reisen ändert sich nicht, also kein `neu.py nachziehen` nötig — im Spec ausdrücklich festhalten.
- **Byte-Gleichheit**: Inhalte als BLOB speichern (nicht als TEXT), sonst Risiko durch Kodierung und Zeilenenden; Prüfsumme SHA-256 über die Bytes; Test vergleicht Ordner rekursiv Byte für Byte.
- **Nur anhängen**: Test muss UPDATE und DELETE (und am besten DROP TRIGGER über die Dienst-Verbindung) scheitern sehen.
- **Rückspieltest**: Schnappschuss erstellen, in neuen Ort einsetzen, öffnen, Export vergleichen.
- **ADR-0008 ohne Namen echter Reisen und ohne Adressen**; Messwerte nur die anonymen aus #345 (379 Vorgänge, Mittel 2,7 s, 5 verloren, 92 % Fotos).
- **Tests**: kein echtes Git nötig, schnell; Testdauer der Suite nicht spürbar erhöhen.
- **Parallele Sitzung** zu #347 (Stufe 2) läuft in der Cloud; die Schnittstelle des Speichers (Funktionsnamen, Vorgangs-Nummer) muss dort passen — in der Spec klar benennen.
- **Texte**: Ausgaben der Befehle für den Betreiber folgen dem Muster von `konten.py` (englisch, kein Katalog); Fehler, die ein Mensch über den Konnektor sieht, kommen erst in Stufe 2.

## Analysis

### Type
Feature (Stufe 1 des Epics #345, Weg C)

### Entscheidung zur Kernfrage: Was ist eine Version? (Variante B)

| Variante | Stand-Nummer | Vorteil | Nachteil |
|---|---|---|---|
| A: eine Tabelle, Zeile je Datei-Version (Wortlaut Issue) | Zahl der Datei-Versionen | wörtlich wie im Issue | Import = +N, ein Vorgang mit 3 Dateien = +3; „Reise-Stand“ auf der Seite (#226: je Schreibvorgang +1) springt; Person/Grund N-fach |
| **B: `vorgaenge` + `versionen` (gewählt)** | höchster `stand` der Reise, je Vorgang +1 | wie heute (`stand.nummer` zählt Commits = Vorgänge); atomar; Angaben einmal je Vorgang | zwei Tabellen, ein Join |
| C: A plus Spalte `vorgang`, Stand = COUNT(DISTINCT vorgang) | wie B | nah am Wortlaut | Angaben doppelt, Stimmigkeit nur per Konvention |

Auslegung, keine Abweichung: Das Issue nennt die Vorgangs-Nummer selbst als Spalte der Versionen. „Stand-Nummer = Zahl ihrer Versionen“ ist die Kurzform des heutigen Verhaltens (ein Schreibvorgang = +1). Das steht im ADR-0008 und als Kommentar in #346.

**Stand-Nummer eindeutig festgelegt:** Jeder Vorgang einer Reise bekommt `stand = max(stand der Reise) + 1` innerhalb von `BEGIN IMMEDIATE`; der Anfangsvorgang beim Import bekommt `stand = ab + 1` (Vorgabe `ab = 0`; Stufe 3 übergibt die bisherige Git-Zahl, damit Seiten nicht zurückspringen). `stand_nummer(reise)` liefert `max(stand)`, nie `COUNT`; `None` für eine unbekannte Reise (wie `stand.nummer`).

### Schema (`PRAGMA user_version = 1`, `CREATE … IF NOT EXISTS` wie konten.py)

```
vorgaenge(
  nummer   INTEGER PRIMARY KEY AUTOINCREMENT,  -- global, nie neu vergeben
  reise    TEXT NOT NULL,
  stand    INTEGER NOT NULL,                   -- Stand-Nummer der Reise
  wann     TEXT NOT NULL,                      -- UTC „…Z“ (stand.zeit_iso)
  wer      TEXT NOT NULL, rolle TEXT NOT NULL DEFAULT '',
  werkzeug TEXT NOT NULL, titel TEXT NOT NULL, grund TEXT NOT NULL DEFAULT '',
  kennung  TEXT UNIQUE,                        -- Wert des Aufrufers (heute FR_VORGANG), NULL erlaubt
  herkunft TEXT NOT NULL DEFAULT '',           -- „import:<ordnername>“, „zuruecksetzen:<stand>“
  UNIQUE(reise, stand), UNIQUE(nummer, reise))
versionen(
  vorgang INTEGER NOT NULL, reise TEXT NOT NULL, pfad TEXT NOT NULL,
  inhalt BLOB,                                 -- NULL = gelöscht (Tombstone)
  pruefsumme TEXT,                             -- SHA-256 hex der Bytes, NULL bei Tombstone
  PRIMARY KEY(vorgang, pfad),
  FOREIGN KEY(vorgang, reise) REFERENCES vorgaenge(nummer, reise))
INDEX versionen_pfad ON versionen(reise, pfad, vorgang)
```

- `titel` und `rolle` ergänzen das Issue-Schema: Der Commit trägt heute Titel und Text, `stand.aenderungen()` zeigt den Titel; ohne Spalte verlöre Stufe 2 die Anzeige.
- Stand `s` einer Reise = je Pfad die Zeile mit dem höchsten `vorgang` unter den Vorgängen mit `stand <= s`; `inhalt IS NULL` → Datei fehlt.
- Unveränderte Dateien (gleiche Prüfsumme) erzeugen keine Zeile; ein Vorgang ganz ohne Änderung wird abgelehnt (wie „nichts geändert“ im Schreibweg).

### Die acht Fragen aus dem Kontext

1. **Version:** Variante B (oben).
2. **Gelöschte Dateien:** Tombstone-Zeile (`inhalt` und `pruefsumme` NULL). Export und Zurücksetzen lassen sie weg; Wiederkehr = neue Version.
3. **Binärdateien:** schon jetzt als BLOB in derselben Tabelle (Akzeptanz Byte-gleich; Beispiele < 200 KB). Auslagerung/inhaltsadressierte Ablage erst Stufe 4.
4. **Was zum Ordner zählt:** alle regulären Dateien rekursiv, auch versteckte (`.gitkeep`). Nicht: `.git`; Symlinks → Import bricht mit Fehler ab (kein stilles Auslassen); leere Ordner nicht erhaltbar (ADR). Rechte und Zeitstempel werden nicht gespeichert; Export schreibt Dateien 0644, Ordner 0755. Byte-gleich = gleiche Pfadmenge und gleiche Bytes. `reise.json` ist Quelle und kommt mit. Pfade: POSIX, relativ, kein `..`, kein NUL; der Export prüft, dass jeder aufgelöste Pfad im Ziel bleibt.
5. **Nur anhängen:** zwei Schichten. (a) Trigger `BEFORE UPDATE/DELETE … RAISE(ABORT)` auf beiden Tabellen plus `PRAGMA recursive_triggers = ON` (sonst löscht `INSERT OR REPLACE`, ohne dass ein DELETE-Trigger feuert). (b) `set_authorizer` in der Verbindung von `db()`, erst nach dem Schema-Aufbau: verweigert UPDATE/DELETE auf beide Tabellen, DROP TABLE/TRIGGER/INDEX, ALTER, `PRAGMA writable_schema`. Ehrliche Grenze im ADR: Schutz gegen Software-Fehler und Fehlbedienung, nicht gegen jemanden mit Schreibzugriff auf die Datei; Gegenmittel sind `pruefen` (Prüfsummen nachrechnen) und die Sicherung außer Haus. `SQLITE_DBCONFIG_DEFENSIVE` im Test ausprobieren, keine Voraussetzung.
6. **Zurücksetzen:** neuer Vorgang, `werkzeug = 'zuruecksetzen'`, `herkunft = 'zuruecksetzen:<stand>'`, Person und Grund Pflicht; neue Versionen für alle Pfade, die vom Ziel-Stand abweichen (alter Inhalt oder Tombstone). Ohne Abweichung: Fehler, kein Vorgang.
7. **Eine Datenbank je Instanz** (`reise` in jeder Zeile, Aufteilung später möglich). WAL, `BEGIN IMMEDIATE`, `timeout = 10`; Sperrfehler als `sqlite3.OperationalError` weiterreichen. Der Messlauf in #347 bestätigt das.
8. **Sicherung:** wie `konten.sichern()` nach `<Speicher>/sicherung/reisen.db` (Online-Backup, `journal_mode = DELETE` in der Kopie, `integrity_check`, `os.replace`). Rückspieltest als Test: Schnappschuss → als neue Datenbank öffnen → Export vergleichen. Wegbringen außer Haus = Server-Backup der Instanz (Doku).

### Öffentliche Schnittstelle `engine/reisespeicher.py` (Grundlage für #347, Feinheiten in der Spec)

```
pfad() -> Path                     # instanz.speicher() / "reisen.db"
db() -> sqlite3.Connection         # Ordner 700, Datei 600, WAL, foreign_keys, recursive_triggers, Schema, Authorizer
vorgang_schreiben(reise, dateien: dict[str, bytes | None], wer, werkzeug, titel,
                  grund="", kennung=None, rolle="", wann=None, herkunft="") -> Vorgang(nummer, stand)
    # eine Transaktion; None = löschen; unverändert übersprungen; leer → Fehler;
    # schon vorhandene Kennung → VorgangVorhanden(nummer, stand) (Wiederholung ungefährlich)
stand_nummer(reise) -> int | None
aktueller_stand(reise, bis=None) -> dict[str, bytes]     # bis = Stand-Nummer
vorgang_eingetragen(kennung) -> Vorgang | None          # ersetzt git log --grep Frieda-Vorgang
verlauf(reise, n=None) -> list[dict]   # nummer=stand, zeit, was=titel, wer (wie stand.aenderungen) + vorgang, werkzeug, grund, dateien; neueste zuerst
exportieren(reise, ziel, bis=None)     # ziel fehlt oder ist leer
importieren(ordner, reise, wer, grund="", ab=0) -> Vorgang
zuruecksetzen(reise, bis, wer, grund) -> Vorgang
pruefen(reise=None) -> list            # Abweichungen der Prüfsummen
sichern() -> Path | None
main(a): importieren | exportieren [--bis N] | verlauf | zuruecksetzen | pruefen | sichern
```

`stand` (je Reise, zeigt die Seite) und `nummer` (global) sind verschiedene Dinge. Die Kennung erzeugt der Aufrufer vor dem Schreiben; nur so geht die Nachprüfung nach einer Zeitüberschreitung. Die Sperre je Reise bleibt in `schreiben.py`.

### Affected Files (with changes)

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/reisespeicher.py` | CREATE | Modul wie oben (~300 Zeilen) |
| `engine/tests/test_reisespeicher.py` | CREATE | Import/Export Byte-gleich (beide Beispielreisen, auch `bis=`), Tombstone, nur anhängen auf der Dienst-Verbindung (UPDATE, DELETE, `INSERT OR REPLACE`, DROP TRIGGER, DROP TABLE), Kennung idempotent, Stand-Nummer (`max`, `ab`), Zurücksetzen, Symlink abgelehnt, Pfad-Ausbruch abgelehnt, Sicherung mit Rückspieltest, `pruefen`, Befehle (~250 Zeilen, < 1 s) |
| `engine/instanz.py` | MODIFY | `speicher()`: `FR_SPEICHER`, Vorgabe `seiten() / "_speicher"`, im Kopfkommentar dokumentiert (Muster `konten()`) |
| `betrieb/einstellungen.beispiel` | MODIFY | Zeile `FR_SPEICHER` (`test_beispiel_einstellungen_sind_vollstaendig` verlangt jeden FR_-Namen) |
| `betrieb/waechter.sh` | MODIFY | zweite Sicherung `reisespeicher.py sichern`, Fehlschlag → `fr_melden high`, Kopfkommentar |
| `engine/tests/test_betrieb.py` | MODIFY | Wächter-Attrappe und Erwartung `gesichert == "konten.py\n"` auf beide Sicherungen erweitern |
| `engine/tests/conftest.py` / `engine/tests/test_konten.py` | MODIFY | `FR_SPEICHER` in die Env-Listen, damit Tests sie nicht erben |
| `engine/tests/test_texte.py` | MODIFY (optional) | Modul in `PY_DATEIEN`, falls es sichtbare Texte hat (Befehlsausgaben für Betreiber englisch wie `konten.py`) |
| `docs/adr/0008-reisespeicher.md` | CREATE | Entscheidung Weg C, Begründung, Messwerte aus #345 (anonym), Variante B, Grenzen (nur anhängen, leere Ordner, Rechte), Folgen für Stufen 2–4 |
| `docs/adr/README.md` | MODIFY | Index-Zeile 0008 |
| `docs/betrieb.md` | MODIFY | Tabelle „Was wohin gehört“, Sicherung/Zurückholen, Wächter |
| `betrieb/deploy.sh` | — | erst Stufe 2 (kein Dienst importiert das Modul) |

### Scope Assessment
- Files: 2–3 neu, 8–9 geändert
- Estimated LoC: +≈700 / −≈5 (davon ~300 Modul, ~250 Tests, ~120 Doku)
- Risk Level: LOW–MEDIUM — neues, isoliertes Modul, das in Stufe 1 kein Dienst nutzt; Berührung mit Bestehendem nur in Wächter, Einstellungen und Doku. Mittel nur wegen der Schnittstelle, auf die Stufe 2 baut.

### Technical Approach
Variante B mit Schema und Schnittstelle wie oben; Vorbild `konten.py` für `db()`/`sichern()`. Reihenfolge: ADR-0008 und Spec (Schnittstelle früh für #347) → Tests rot → Modul → `instanz.speicher()`, Einstellungen, Wächter mit Attrappe → Doku → Gesamtlauf.

Für die Spec festhalten:
- `PRAGMA foreign_keys = ON` und `recursive_triggers = ON` je Verbindung; `executescript` committet implizit, Schema getrennt von Transaktionen.
- Authorizer erst nach dem Schema; `sichern()` und `pruefen` mit eigenen Verbindungen.
- Dateien nur binär lesen/schreiben (kein `read_text`, keine Zeilenend-Umwandlung).
- Kein `neu.py nachziehen` nötig: Das Format der Reisedaten ändert sich nicht.
- Keine Instanzwerte: Ort nur über `instanz.speicher()`; Tests über `tmp_path` und `FR_SPEICHER`.

### Dependencies
- Upstream: Standardbibliothek (`sqlite3`, `hashlib`), `instanz.py`, `stand.zeit_iso`.
- Downstream ab Stufe 2 (#347): `schreiben.py` (Vorgang, Nachprüfung), `stand.py` (`nummer`, `aenderungen`), `konnektor.py`, Rückmeldedienst, `deploy.sh`; ab Stufe 3 Veröffentlichen und Nachziehen (Import mit `ab`).

### Spätere Stufen / Hinweise fürs ADR (blockieren Stufe 1 nicht)
- Alter Git-Verlauf bei der Umstellung (Stufe 3): Anfangsvorgang mit Vermerk „vorher in Git“ und übernommener Stand-Nummer (`ab`) genügt aus Sicht des Tech Leads; jeden Commit nachzuspielen ist optional. Entscheidung erst in Stufe 3.
- Grenze der Unveränderlichkeit wird im ADR ehrlich benannt (s. Frage 5).
- Hash-Kette über Vorgänge, inhaltsadressierte Ablage für Fotos: später, nicht jetzt.
- Schnittstelle als Kommentar in #347 veröffentlicht, Sitzung „347“ benachrichtigt.

### Open Questions
Keine, die Stufe 1 blockieren.
