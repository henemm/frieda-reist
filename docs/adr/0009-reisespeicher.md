# ADR-0009: Reisespeicher: Reisedaten als unveränderliche Versionen in SQLite, nur anhängen

## Status

Gilt · Entschieden vom Product Owner am 5.11.2026 (Epic #345, Weg C) · Stufe 1 gebaut mit #346

Steht unter [ADR-0001](0001-kern.md), Punkt 8: Die Technik ist Mittel, nicht Kern. Dieses ADR ändert, wo die Reisedaten liegen, nicht, was sie sind: Grundformen, Arten, Merkmale und Dateiformat der Reise bleiben unverändert.

## Kontext

Bisher sind die Reisedaten Dateien in einem Git-Repo, und jeder Schreibvorgang des Konnektors ist ein Commit auf einem gemeinsamen Zweig, der nach `main` gebracht wird. Die Messwerte einer Instanz aus Epic #345 (anonym): 379 Schreibvorgänge in rund einem Monat, mittlere Dauer 2,7 Sekunden je Vorgang, 5 Vorgänge gingen verloren, 92 % der Dateien sind Fotos. Der Weg über Git ist langsam, braucht eine Arbeitskopie je Reise, kann bei gleichzeitigen Vorgängen Arbeit verlieren und verwaltet große Binärdateien schlecht. Die Stand-Nummer einer Reise ist die Zahl der Commits, die ihren Ordner ändern (#226).

## Entscheidung

1. **Weg C:** Die Reisedaten liegen als unveränderliche Versionen in einer SQLite-Datenbank je Instanz (`<FR_SPEICHER>/reisen.db`, Vorgabe `<Seiten>/_speicher`, `engine/reisespeicher.py`, nur Standardbibliothek). Git ist auf Dauer nicht mehr Träger der Reisedaten.
2. **Variante B:** Zwei Tabellen. `vorgaenge` hält je Schreibvorgang einmal die Angaben (Reise, Stand, Zeit in UTC, Person, Rolle, Werkzeug, Titel, Grund, Kennung, Herkunft); `versionen` hält je Vorgang eine Zeile je geänderter Datei (Bytes als BLOB, SHA-256; gelöscht heißt eine Zeile ohne Inhalt, ein Tombstone). Unveränderte Dateien erzeugen keine Zeile, ein Vorgang ohne Änderung ist ein Fehler.
3. **Stand-Nummer zählt Vorgänge:** Jeder Vorgang einer Reise erhöht sie um 1, gleich wie viele Dateien er berührt (wie heute je Commit, #226). „Stand-Nummer = Zahl der Versionen“ aus #346 ist die Kurzform dieses Verhaltens. Die Nummer steigt streng, ist aber nicht lückenlos garantiert. Ein Import kann eine bisherige Zahl übernehmen (`ab`), damit Seiten nicht zurückspringen.
4. **Nur anhängen:** Nichts wird geändert oder gelöscht. Zurücksetzen auf einen alten Stand ist ein neuer Vorgang mit Person und Grund; der Verlauf wird nie gekürzt. Eine Kennung des Aufrufers macht einen Vorgang wiederholbar, ohne ihn doppelt einzutragen.
5. **Schutz in zwei Schichten:** Trigger verweigern UPDATE und DELETE auf beiden Tabellen (mit `recursive_triggers`, sonst löschte `INSERT OR REPLACE` an ihnen vorbei); der Authorizer der Verbindung verweigert dazu UPDATE, DELETE, DROP, ALTER TABLE und `PRAGMA writable_schema`.
6. **Sicherung:** Der Wächter schreibt täglich einen geprüften Schnappschuss über die Backup-API von SQLite nach `<FR_SPEICHER>/sicherung/reisen.db`; das Wegbringen außer Haus übernimmt das Server-Backup der Instanz.

## Begründung

- Ein Vorgang ist eine Transaktion in einer Datei: kein Zweig, keine Arbeitskopie, kein Vorspulen, kein verlorener Vorgang durch einen Konflikt im gemeinsamen Zweig.
- Variante B hält die Angaben eines Vorgangs einmal und zählt den Stand wie bisher. Würde jede Datei-Version zählen, spränge die Seitenzahl beim Import um die Zahl der Dateien.
- SQLite ist Teil der Standardbibliothek, läuft ohne Dienst, kennt WAL, Trigger, Authorizer und Online-Backup; die Konten liegen schon so (ADR-0005, `engine/konten.py`).
- Nur anhängen erfüllt ADR-0001, Punkt 7: Nichts wird ohne Verlauf überschrieben, jede Änderung trägt Person, Werkzeug, Grund und Zeit (Punkt 5).
- **Ehrliche Grenze:** SQLite kennt keine Benutzerrechte. Der Schutz hält Software-Fehler und Fehlbedienung über die Verbindung des Moduls ab, nicht jemanden mit Schreibzugriff auf die Datei, der sie selbst öffnet und die Trigger entfernt. Dasselbe gilt für andere Wege an der Prüfung von SQL vorbei, etwa die Online-Backup-Schnittstelle mit einer Verbindung des Moduls als Ziel: Das ist kein Fehler im Schreibweg, sondern ein bewusster Eingriff in die Datei. Gegenmittel sind `reisespeicher.py pruefen` (rechnet alle Prüfsummen und die Stand-Folge nach) und die Sicherung außer Haus.

## Konsequenzen

- Stufe 1 (#346): Modul mit Import, Byte-gleichem Export (auch eines alten Stands), Verlauf, Zurücksetzen, Prüfen und Sicherung mit Rückspieltest; Ort über `instanz.speicher()` (`FR_SPEICHER`), tägliche Sicherung im Wächter. Der Schreibweg bleibt in Stufe 1 auf Git und schreibt nicht zusätzlich in den Speicher; `betrieb/deploy.sh` nimmt das Modul erst mit Stufe 2 auf.
- Byte-gleich heißt gleiche Pfadmenge und gleiche Bytes. Leere Ordner, Rechte und Zeitstempel der Dateien bleiben nicht erhalten; der Ordner `.git` gehört nicht dazu, ein Symlink bricht den Import ab.
- Das Format der Reisedaten ändert sich nicht; `neu.py nachziehen` braucht keine Umstellung.
- Stufe 2 (#347): Der Schreibweg (`engine/schreiben.py`, `engine/stand.py`) schreibt in den Speicher statt in Git; die Sperre je Reise bleibt im Schreibweg, die Kennung ersetzt die Suche nach dem Vorgang im Git-Verlauf (Nachprüfung lokal). Übergangsregel: Ein Schalter je Reise (`FR_SPEICHERREISEN`, Vorgabe leer) wählt den Weg; der Git-Weg lebt bis Stufe 5 in `engine/schreiben_git.py` und `engine/stand_git.py` und lehnt Reisen der Liste ab. Zusätze der Schnittstelle: `vorgang_schreiben(..., erwartet=)` mit `StandGeaendert`, `db(timeout)`, `datei(reise, pfad, bis)`, `reisen()` und der Baustein `ordner_als_vorgang` (auch für `reise_anlegen`, später `nachziehen`). Konnektor und Rückmeldedienst lesen erst ab Stufe 3. Umgeschaltet wird eine echte Reise erst nach Stufe 3 und nach gesicherter Sicherung außer Haus.
- Stufe 3: Veröffentlichen und Nachziehen lesen aus dem Speicher. Der alte Git-Verlauf wird nicht nachgebaut: Ein Anfangsvorgang je Reise mit dem Vermerk „vorher in Git“ und der übernommenen Stand-Nummer genügt.
- Stufe 4: Auslagerung großer Fotos aus der Datenbank; später eine Hash-Kette über die Vorgänge.
- Eine Datenbank je Instanz sperrt beim Schreiben die ganze Datei. Bei den gemessenen Raten genügt WAL mit 10 Sekunden Wartezeit; der Messlauf in #347 bestätigt das.

## Verlauf

- 5.11.2026: Weg C vom Product Owner entschieden (Epic #345); Stufe 1 mit diesem ADR gebaut (#346).
- 6.11.2026: Stufe 2 gebaut (#347): Schalter `FR_SPEICHERREISEN` je Reise (Option A, Product Owner), Git-Weg in `schreiben_git.py` und `stand_git.py` bis Stufe 5, Zusätze der Schnittstelle (siehe Konsequenzen).
