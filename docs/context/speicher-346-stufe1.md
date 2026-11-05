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
