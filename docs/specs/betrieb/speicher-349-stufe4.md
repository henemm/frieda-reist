---
entity_id: speicher-349-stufe4
type: feature
created: 2026-11-08
updated: 2026-11-08
status: draft
workflow: speicher-349-stufe4
version: "1.0"
tags: [reisespeicher, ablage, medien, nachziehen, sicherung, betrieb, epic-345]
---

# Speicher Stufe 4: Fotos und GPX in eine Dateiablage (#349, Epic #345)

Grundlage: `docs/context/speicher-349-stufe4.md` (Kontext und Analyse mit den Entscheidungen des Tech Leads), ADR-0009, `speicher-348-stufe3.md` (Stufe 3).

## Approval

- [ ] Approved
- [ ] Die zwei Annahmen A-1 und A-2 (unten) vom Product Owner bestätigt

## Purpose

Seit Stufe 1 liegt jede Datei einer Speicher-Reise, auch jedes Foto, als BLOB in der Datenbank `reisen.db`. Die größte echte Reise hat rund 105 MB Fotos; die Datenbank wird damit groß, jeder Schnappschuss der Sicherung kopiert sie ganz, und Materialisieren und Vergleichen lesen die Bytes durch SQLite (Befund aus Stufe 3, Entscheidung 11 der Spec 348). Diese Stufe legt **Medien** (Bilder, GPX, Grundkarten) als Dateien in eine Ablage auf dem Server, benannt nach ihrer Prüfsumme. In der Datenbank bleibt die Zeile mit Pfad und Prüfsumme (der Verweis), die Bytes liegen in der Ablage.

Ziele:

1. Medien liegen nicht mehr in der Datenbank, sondern einmal je Inhalt als Datei in `<FR_SPEICHER>/ablage/`. Gleiche Bytes (auch in mehreren Reisen und Versionen) belegen den Platz nur einmal.
2. Generator, PWA-Bau und Browser-Rundgang bleiben unverändert: `materialisieren` legt weiter echte Dateien in den Bauordner (Hardlink aus der Ablage, Kopie als Rückfall). Die Seite bleibt offline nutzbar, weil der Bau die Bilder wie bisher ins Ziel kopiert.
3. Verlauf, Versionierung und Zurücksetzen bleiben: Eine Datei ändert sich nur durch einen neuen Vorgang mit neuer Prüfsumme; die Ablage wird nur ergänzt.
4. Ein Formatwechsel, der keine Handarbeit braucht (#250): Bestehende Speicher werden von der Software selbst auf das neue Schema gehoben, bestehende Medien von `neu.py nachziehen-speicher` in die Ablage gebracht.
5. Die Ablage ist Teil der Wahrheit einer Reise und wird deshalb zusammen mit der Datenbank gesichert und geprüft.

## Source

- **File:** `engine/reisespeicher.py`, `engine/instanz.py`, `engine/neu.py`, `engine/bauen.py`, `engine/texte_de.py`, `engine/texte_en.py`, `betrieb/deploy.sh`, `betrieb/messlauf-schreibweg.py`; neu `engine/tests/test_reisespeicher_ablage.py`
- **Identifier:** `reisespeicher.AUSLAGERN`, `reisespeicher.ablage_pfad`, `reisespeicher.AblageFehlt`, `instanz.speicher_ablage`, `neu.nachziehen_speicher`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/reisespeicher.py` (Stufen 1 bis 3) | Modul | `db`, `SCHEMA`, `_stand`, `_eintragen`, `datei`, `aktueller_stand`, `exportieren`, `materialisieren`, `vergleichen`, `pruefen`, `sichern`, `zustand`, `importieren`, `ordner_als_vorgang` |
| `engine/instanz.py` | Modul | `speicher()` (Ort), neu `speicher_ablage()` |
| `engine/neu.py` | Modul | `nachziehen-speicher` (Stufe 3), erhält die Auslagerung bestehender Medien |
| `engine/bauen.py` | Modul | liest `medien/` aus dem Reiseordner; bleibt ohne Änderung der Lesewege |
| `engine/schreiben.py` | Modul | `track_anhaengen`, `icon_set` laufen über `ordner_als_vorgang`; greifen ohne Änderung |
| `engine/texte.py`, `texte_<sprache>.py`, `engine/tests/test_texte.py` | Textkatalog | neue Meldungen in allen Sprachen |
| `betrieb/waechter.sh`, `reisespeicher.py sichern` | Betrieb | tägliche Sicherung der Datenbank |
| Server-Backup der Instanz (Infra-Repo) | Betrieb | nimmt `<FR_SPEICHER>/` mit (Datenbank, `sicherung/`, `ablage/`) |
| `docs/specs/betrieb/speicher-348-stufe3.md`, `docs/adr/0009-reisespeicher.md`, `docs/adr/0001-kern.md` | Specs, ADR | Rahmen und Prüfstelle |

## Scope

### Im Scope

- Schema: Spalte `ausgelagert` in `versionen`, `PRAGMA user_version` 2, Anhebung beim Öffnen.
- Ablage: Ort, Schreiben (Datei vor Datenbank), Lesen, Hardlink/Kopie, Pfadsicherheit.
- Lesewege (`_stand`, `datei`, `aktueller_stand`, `exportieren`, `materialisieren`, `vergleichen`, `zuruecksetzen`, `ordner_als_vorgang`) und `pruefen` kennen ausgelagerte Zeilen.
- Fehlerklasse „Datei fehlt in der Ablage“ mit Katalogtext in allen Sprachen; der Bau bricht damit ab.
- `neu.py nachziehen-speicher`: bestehende Medien in die Ablage übernehmen (idempotent).
- Sicherung: `sichern` und `pruefen` nehmen die Ablage in den Blick; `zustand` meldet fehlende Ablagedateien; Server-Backup.
- `betrieb/messlauf-schreibweg.py --auffuellen` legt Zufallsfotos über die Ablage an; Neumessung der Zeitziele.
- Dokumentation: ADR-0009, `docs/betrieb.md`, `betrieb/deploy.sh` (Modulliste unverändert, wenn kein neues Modul entsteht).

### Nicht im Scope

- **Git-Reisen.** Sie behalten `medien/` im Repo bis Stufe 5 (#350). Stufe 4 gilt nur für Reisen in `FR_SPEICHERREISEN`.
- Aufräumen verwaister Ablagedateien (nur der Betreiber, von Hand und bewusst; die Ablage wird nie automatisch verkleinert).
- Verschlüsselung der Ablage, Hash-Kette, Auslieferung der Medien direkt aus der Ablage ohne Bau.
- Medien anderer Ordner als `medien/` (Belege liegen in `<FR_ABLAGE>/<reise>/belege/`, `engine/belege.py`, unverändert).
- Umschalten einer echten Reise (Stufe 5).

### Affected Files

Siehe Abschnitt „Dateien“ weiter unten (vollständige Liste mit Art der Änderung). Die Zeilen „ausgelagert = 1 mit Inhalt“ und „ohne Summe“ in AC-16 stellt der Test über eine rohe Verbindung ohne Trigger und Authorizer her (eigene Hilfsfunktion im Test).

### Estimated Changes

- Dateien: 8 zu ändern, 1 neue Testdatei, 4 nur zu prüfen (Liste: Abschnitt „Dateien“ unten), 1 Fremdrepo-Anteil (Backup im Infra-Repo der Instanz, selbst erledigen, eigenes Issue dort)
- Umfang: ca. +450 / -40 Zeilen
- Risiko: mittel. Das Format aller Speicher-Reisen ändert sich; Datenverlust droht nur, wenn die Ablage nicht gesichert wird (Gegenmittel: AC-19 bis AC-23).

## Annahmen, vom Product Owner zu bestätigen

| Nr. | Frage | Annahme (Tech Lead) | Folge, wenn der Product Owner anders entscheidet |
|---|---|---|---|
| A-1 | Alte BLOBs in der Datenbank: Die Datenbank ist nur anhängend (Trigger `versionen_kein_update`/`_kein_delete`, Authorizer). Bereits eingetragene Medien-BLOBs lassen sich daher nicht in der Datenbank löschen. | Bestehende Medien werden **auch in die Ablage** gelegt, und ab dem Umstellungsvorgang lesen alle Wege aus der Ablage; die alten BLOBs bleiben bis zu einem **Neuaufbau der Datenbank** liegen (`reisespeicher.py ablage-umstellen`, ein Betreiberbefehl: schreibt eine neue `reisen.db` mit denselben Vorgängen und Versionen, ohne die ausgelagerten BLOBs, prüft sie mit `pruefen` und Vergleich, tauscht sie atomar gegen die alte und behält die alte als `reisen.db.vor-ablage`). Er ist **nicht** nötig, damit alles funktioniert (AC-20 gilt auch mit alten BLOBs), nur um die Datenbank zu verkleinern. | Soll der Neuaufbau automatisch im Nachziehen laufen, braucht er eine Sperre gegen den Schreibweg (Dienst anhalten); soll er entfallen, bleibt die Datenbank der Altreisen groß, und nur neue Medien sparen Platz. |
| A-2 | Hardlink statt Kopie beim Materialisieren | Hardlink, wenn Ablage und Bauordner im selben Dateisystem liegen, sonst Kopie. Gefahr: Wer eine Datei im Bauordner beschreibt, würde die Ablage ändern. | Reine Kopie (immer sicher, aber 110 MB pro Bau); der Bau schreibt in den Bauordner nur neue Dateien, nie in vorhandene (`bilder_schreiben` schreibt nach `dist/`, nicht in `medien/`), und die Ablagedateien sind schreibgeschützt (Modus 400). |

## Entscheidungen mit Begründung

1. **Spalte statt zweiter Tabelle.** `versionen` bekommt `ausgelagert INTEGER NOT NULL DEFAULT 0`. Bei `ausgelagert = 1` ist `inhalt` NULL und `pruefsumme` gesetzt. Ein Tombstone bleibt `inhalt NULL und pruefsumme NULL` (und `ausgelagert = 0`), ist also von einem Verweis unterscheidbar. Folge: `_stand(spalte="pruefsumme")`, `vergleichen`, die Stand-Folge und der byte-gleiche Export bleiben im Sinn unverändert. Nur Lesen der Bytes ändert sich. Die Fensterabfrage in `_stand` unterscheidet bisher „weg“ über `inhalt IS NULL`; sie muss auf `inhalt IS NULL AND pruefsumme IS NULL` umgestellt werden (sonst gälte ein Verweis als gelöscht).
2. **Ablageort:** `<FR_SPEICHER>/ablage/<aa>/<summe>`. `<summe>` ist die SHA-256 in Kleinbuchstaben (64 Hexzeichen), `<aa>` deren erste zwei Zeichen. Der Name kommt nur aus dem Hash, nie aus einem Pfad oder einer Eingabe. Ordner 700, Dateien 400 (nur lesbar für den Dienstbenutzer; der Speicher selbst ist 700/600). Eine Funktion `instanz.speicher_ablage()` liefert `speicher() / "ablage"`.
3. **Was ausgelagert wird:** eine Datei unter `medien/` mit der Endung (Kleinbuchstaben verglichen) `png`, `jpg`, `jpeg`, `webp`, `gif`, `gpx` oder `pmtiles`. Eine Konstante `AUSLAGERN` in `reisespeicher.py` hält die Liste; sie ist die einzige Stelle. **Nicht** ausgelagert: `medien/icon.svg` und `medien/icon.png` (klein, der Bau braucht sie, das App-Symbol ist Teil jeder Seite), sowie alles außerhalb von `medien/` (Markdown, YAML, JSON). Die Regel kennt keine Grundform und keinen Reiseinhalt, nur Pfad und Endung.
4. **Keine Größenschwelle.** Die Regel richtet sich nach der Art der Datei, nicht nach einem Schwellenwert, der zufällig entscheidet, wo eine Datei liegt. So wird jedes Duplikat gleich behandelt und nur einmal abgelegt.
5. **Nur Speicher-Reisen.** Der Speicher kennt nur Speicher-Reisen; ein Git-Repo ist nicht betroffen.
6. **Schreibreihenfolge: Datei vor Datenbank.** `_eintragen` legt die Ablagedatei fest (temporär im Ordner der Ablage schreiben, `fsync`, `os.link` auf den Endnamen, dann die Temporärdatei entfernen, `fsync` des Ordners; nie `os.replace`, weil es eine vorhandene Datei überschriebe), dann erst die Zeile in der Datenbank-Transaktion. Bricht etwas dazwischen ab, bleibt eine verwaiste Ablagedatei, die harmlos ist (kein Verweis zeigt darauf). Ein Verweis auf eine fehlende Datei kann so nie entstehen. Existiert die Zieldatei schon (gleiche Summe), wird nichts geschrieben; ist sie vorhanden, aber ihre Größe oder Summe stimmt nicht, wird sie nie überschrieben, sondern der Schreibvorgang bricht mit `AblageFehler` ab (AC-12).
7. **Nur anhängend.** Die Software löscht und ändert nie eine Ablagedatei. Aufräumen ist Sache des Betreibers.
8. **Hardlink mit Kopie-Rückfall** (siehe A-2): `materialisieren` und `exportieren` legen eine ausgelagerte Datei per `os.link(ablage, ziel)` an; scheitert das mit `OSError` (anderes Dateisystem, nicht unterstützt), kopiert es (`shutil.copyfile`, Modus 644 wie bisher; ein Hardlink behält den Modus 400 der Ablagedatei, der Unterschied betrifft nur den Bauordner, `dist/` bekommt seine Dateien weiter per `shutil.copyfile`). Der Export in einen Ordner bleibt byte-gleich.
9. **Prüfsumme beim Lesen.** `datei()` und `aktueller_stand()` rechnen die Summe der gelesenen Bytes nach und melden ein Abweichen. Auch `exportieren` und `materialisieren` (und damit der Bau) rechnen vor dem Verknüpfen oder Kopieren die SHA-256 der Ablagedatei streamend nach (rund 0,3 s je 100 MB; das Zeitziel unten gilt mit dieser Prüfung). Eine beschädigte Datei kommt so nie in einen Bau. `zustand` prüft nur Vorhandensein (schnell), `pruefen` alles.
10. **Migration des Schemas ist Aufgabe der Software.** `db()` hebt `user_version` von 1 auf 2 und ergänzt die Spalte (`ALTER TABLE versionen ADD COLUMN ausgelagert …`) **vor** dem Setzen des Authorizers (dort ist `SQLITE_ALTER_TABLE` verboten; `db()` führt `SCHEMA` und `user_version` schon vor dem Authorizer aus). Bestehende Zeilen bekommen `ausgelagert = 0` und bleiben lesbar.
11. **Die Reise gehört den Daten, nicht dem Ort.** Die Software kennt keine Instanz: der Ort kommt aus `instanz.speicher()`; nichts Instanzspezifisches in der Engine.

## Prüfstelle (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Die Ablage kennt nur Pfade, Endungen und Bytes. Durchgespielt an beiden Beispielreisen: `beispielreise` (Medien: Symbol, Skizze als PNG, vier GPX-Dateien) und `stadtwochenende` (ohne `medien/`: die Reise läuft ohne Ablage, eine Medien-Datei wird nachträglich in einem Test ergänzt). |
| 2 Kein Katalog | Keine Art und kein Merkmal. |
| 3 Keine KI | Feste Regeln. |
| 4 Die Tür | Der Konnektor ändert sich nicht (`track_anhaengen` und `icon_set` laufen über denselben Schreibweg); keine neue Funktion, kein Eintrag in `docs/konnektor.md`. |
| 5 Herkunft | Der Umstellungsvorgang des Nachziehens trägt Person („Software-Nachziehen“), Werkzeug `nachziehen`, Grund und Kennung (wie Stufe 3). |
| 6 Rollen entscheiden | Ändert Speicherort, keine Inhalte und keine Entscheidungen. |
| 7 IDs und Verlauf | Keine IDs betroffen. Nur anhängend: Datenbank und Ablage; Verlauf und Zurücksetzen unverändert. |
| 8 PWA | Die Seite wird mit demselben Generator gebaut; der Browser-Rundgang ist Teil der Abnahme (AC-24, beide Reisetypen). |
| 9 Claude Code | Keine Reiseinhalte in Claude Code. |
| 10 Dokumentation | Diese Spec, ADR-0009 (Satz „das Format ändert sich nicht“ wird ersetzt, siehe unten), `docs/betrieb.md`. |

## Verhalten

### Schreiben

`_eintragen(v, reise, dateien, …)` erkennt je Datei mit Inhalt `ausgelagert`, wenn `pfad.lower()` mit `medien/` beginnt, die Endung in `AUSLAGERN` steht und `pfad` nicht `medien/icon.svg` oder `medien/icon.png` ist. Für solche Dateien:

1. Summe rechnen (`_summe`); ist sie schon der Stand der Datei (`bisher.get(p) == summe`), ändert sich nichts (wie bisher).
2. **Vor** dem `INSERT` der Zeile: `ablage_ablegen(summe, inhalt)` (Entscheidung 6). `_eintragen` läuft in der Transaktion des Aufrufers: die Datei wird dort geschrieben, bevor die Zeile eingefügt wird, unter derselben Schreibsperre; die Transaktion umfasst die Datei aber nicht und kann sie nicht zurückrollen. Scheitert die Transaktion später (z. B. `StandGeaendert`), bleibt die Datei verwaist liegen.
3. Zeile: `(vorgang, reise, pfad, NULL, summe, 1)`.

Dateien, die nicht ausgelagert werden, schreiben wie bisher `(…, inhalt, summe, 0)`.

`importieren` und `ordner_als_vorgang` rufen `_eintragen`; sie brauchen keine eigene Logik, nur dass `_ordner_lesen` die Bytes liefert (bestehend).

### Lesen

- `_stand(v, reise, bis, spalte)`: ändert die Gewinner-Abfrage so, dass `weg` heißt `inhalt IS NULL AND pruefsumme IS NULL`; bei `spalte="inhalt"` wird für ausgelagerte Zeilen zusätzlich `ausgelagert` gelesen und der Wert nicht als Bytes, sondern als Marke geliefert, die der Aufrufer aus der Ablage auflöst. Die Prüfsummen-Sicht (`vergleichen`, `stand_nummer`, der Vergleich „gleiche Summe, nichts zu tun“ in `_eintragen`) bleibt eine reine Datenbankabfrage ohne Dateizugriff. Nur `_eintragen` beim Ablegen neuer Bytes und `exportieren`/`datei`/`aktueller_stand` greifen auf die Ablage zu.
- `datei(reise, pfad, bis)`: liest bei `ausgelagert = 1` die Ablagedatei, rechnet die Summe nach und vergleicht mit `pruefsumme`. Fehlt sie: `AblageFehlt`; stimmt die Summe nicht: `AblageFehler`.
- `aktueller_stand(reise, bis)`: wie `datei` für jede ausgelagerte Zeile.
- `exportieren(reise, ziel, bis)`: ausgelagerte Dateien per Hardlink (Rückfall Kopie, Entscheidung 8), alle Pfade vorher geprüft wie bisher; fehlt eine Ablagedatei, bricht der Export **vor dem ersten Schreiben** ab (in einer Vorab-Runde werden alle Ablagedateien auf Vorhandensein, Größe und Summe geprüft, erst dann wird verknüpft; bei `AblageFehler` gilt dasselbe), damit kein halber Ordner entsteht.
- `materialisieren`: wie bisher (erst `<ordner>.neu`, dann umbenennen); der Export darunter nutzt Hardlinks.
- `zuruecksetzen`: stellt Nicht-Medien wie bisher über `_eintragen` mit den Bytes der alten Fassung wieder her. Bei ausgelagerten Medien holt es keine Bytes, sondern trägt nur den Verweis (alte Summe, `ausgelagert = 1`) neu ein, nachdem es geprüft hat, dass die Ablagedatei vorhanden ist und ihre Größe stimmt; fehlt sie, bricht es mit `AblageFehlt` ab, ohne einen Vorgang zu schreiben.

### Prüfen und Zustand

`pruefen(reise=None)` prüft zusätzlich für jede Zeile mit `ausgelagert = 1`: Ablagedatei vorhanden, Größe und SHA-256 stimmen mit `pruefsumme`. Funde: `<reise> <pfad> (operation N): file missing in store` und `…: store checksum mismatch`. Außerdem: ausgelagert mit `inhalt` nicht NULL, ausgelagert ohne Prüfsumme. Die Ablagedateien selbst werden nur gelesen, nie geändert.

`zustand()` meldet zusätzlich `ablage_fehlt <n>`: Zahl der in der Datenbank verwiesenen Summen, die in der Ablage nicht als Datei existieren (nur Vorhandensein, schnell, ohne Summen; die volle Prüfung ist `pruefen`). Exit 1 bei `n > 0`.

### Sicherung

1. `sichern()` (täglich, Wächter) schreibt den Schnappschuss der Datenbank wie bisher und prüft danach mit der Datenbank-Verbindung, dass jede in der Datenbank verwiesene Summe in der Ablage existiert; fehlt eine, gilt die Sicherung als gescheitert (Exit ungleich 0, kein Ersetzen des vorigen Schnappschusses). Die Ablage selbst wird nicht kopiert: sie ist nur anhängend, jede Datei ändert sich nie, und das Server-Backup der Instanz nimmt `<FR_SPEICHER>/` (Datenbank, `sicherung/`, `ablage/`) mit.
2. Das Server-Backup der Instanz nimmt `ablage/` in dieselbe Sicherung wie `reisen.db`. Reihenfolge: der **Datenbank-Schnappschuss zuerst, die Ablage danach**, nie der Schnappschuss allein; weil die Ablage nur wächst, enthält eine spätere Ablage-Sicherung alles, worauf der frühere Schnappschuss verweist, und mehr (nie ein Verweis ohne Datei). Der Wächter-Schnappschuss (`sichern`) entsteht vor dem Lauf des Server-Backups. Das ist im Infra-Repo der Instanz umzusetzen (eigenes Issue dort, in #349 verlinkt) und in `docs/betrieb.md` zu beschreiben.
3. **Wiederherstellung** (Prüfpunkt, kein Code): aus dem Archiv `sicherung/reisen.db` und `ablage/` in einen Wegwerf-Ordner zurückholen, als `reisen.db` einsetzen, `reisespeicher.py pruefen` muss `ok` melden (Exit 0, keine Fundzeilen; also auch jede Ablagedatei vorhanden und richtig), und `vergleichen` einer Beispielreise gegen ihren Ordner Exit 0.

### Migration: `neu.py nachziehen-speicher`

Die Schema-Anhebung geschieht beim Öffnen (Entscheidung 10), ohne Handschritt. Dazu kommt die Umstellung der Medien:

1. `nachziehen_speicher` erkennt Medien im Stand der Reise, die noch `ausgelagert = 0` tragen (Zeilen mit Inhalt, `medien/…` mit Endung aus `AUSLAGERN`).
2. Es legt ihre Bytes in die Ablage (`ablage_ablegen`, idempotent) und trägt **einen** Vorgang ein (Person „Software-Nachziehen“, Werkzeug `nachziehen`, Titel „ablage-umstellung“, Kennung `ablage:<reise>:<basis>`): für jede solche Datei eine neue Zeile mit gleichem Pfad, gleicher Summe, `ausgelagert = 1`. Weil `_eintragen` bei gleicher Summe „nichts geändert“ sieht, bekommt die Umstellung einen eigenen Weg `reisespeicher.auslagern(reise, …)`, der genau diese Verweiszeilen schreibt (nur diese Funktion darf eine Datei mit gleicher Summe erneut eintragen). Der Inhalt der Reise ändert sich nicht: Summen gleich, `vergleichen` gegen den Stand davor gleich.
3. Idempotent: Ein zweiter Lauf findet keine Medien mit `ausgelagert = 0` mehr und gibt `nichts umzustellen`, Exit 0, kein Vorgang. Dieselbe Kennung zweimal ergibt `VorgangVorhanden` (wie Stufe 3).
4. Die Umstellung läuft im Speicher-Teil von `veroeffentlichen.sh` mit dem Nachziehen (Stufe 3, Software-Wechsel) und hat denselben Wettlauf-Schutz (`StandGeaendert`, höchstens dreimal). Reihenfolge bei einem Software-Wechsel mit beiden Änderungen: erst der Formatvorgang der Stufe 3 (mit Probebau), danach als zweiter, getrennter Vorgang die Auslagerung; jeder trägt seine eigene Kennung, und beide sind einzeln idempotent. Die Auslagerung braucht keinen Probebau (der Inhalt ändert sich nicht), wohl aber den Vergleich vor und nach dem Eintragen (Fehler: nichts geschrieben).
5. Die alten BLOBs bleiben in der Datenbank (A-1). Der Neuaufbau ist der Betreiberbefehl `ablage-umstellen`; Beschreibung in `docs/betrieb.md`. Er ist hier **kein** Muss.

### Meldungstexte

Zwei neue Katalogschlüssel in **allen Sprachen** (zurzeit `de`, `en`; jede später hinzukommende Sprache bekommt sie, die Ausnahmelisten in `engine/tests/test_texte.py` dürfen nicht länger werden):

| Schlüssel | de | en |
|---|---|---|
| `pruefung.bauen.79` | `{w1}: Datei „{ziel}“ fehlt in der Ablage des Speichers (Prüfsumme {summe}).` | `{w1}: file “{ziel}” is missing from the store (checksum {summe}).` |
| `pruefung.bauen.80` | `{w1}: Datei „{ziel}“ in der Ablage des Speichers ist beschädigt (Prüfsumme stimmt nicht).` | `{w1}: file “{ziel}” in the store is damaged (checksum does not match).` |

`w1` ist wie bei den übrigen Meldungen der Reise-Ordner oder -Name. Der Bau (`bauen.py`) bricht mit Exit 2 ab, wenn `materialisieren`/`exportieren` `AblageFehlt` oder `AblageFehler` melden; die Meldung kommt über `texte.satz(...)` (wie alle `pruefung.bauen.N`) mit der Sprache der Instanz. Die Betriebsausgaben von `reisespeicher.py` (`pruefen`, `zustand`) bleiben englische Betreiberzeilen wie bisher.

## Fehlerfälle

| Fall | Verhalten |
|---|---|
| Ablagedatei fehlt beim Lesen, Export oder Bau | `AblageFehlt` mit Pfad und Summe; `exportieren` bricht vor dem ersten Schreiben ab; der Bau endet mit Exit 2 und Katalogtext `pruefung.bauen.79`; die Reise bleibt auf dem letzten guten Stand (rot wie in Stufe 3, kein Stempel, kein Heartbeat). |
| Summe stimmt nicht (Bit-Fäule, Eingriff von Hand) | `AblageFehler`; Bau Exit 2, `pruefung.bauen.80`; `pruefen` meldet den Fund. Die Datei wird nie repariert oder überschrieben (nur anhängend). |
| Ablagedatei beim Schreiben schon vorhanden, aber mit falscher Größe oder Summe | `AblageFehler`, nichts geschrieben, kein Vorgang. |
| Pfadsicherheit | Der Name in der Ablage kommt nur aus der Prüfsumme; `ablage_pfad(summe)` verlangt `^[0-9a-f]{64}$` und weist alles andere mit `ValueError` ab. Die Pfade der Dateien in der Reise werden wie bisher von `_pfad_pruefen` und beim Export gegen das Ziel geprüft (kein `..`, kein Symlink); Hardlinks werden nur auf Ziele im geprüften Zielordner gelegt, und eine Ablagedatei, die ein Symlink ist, wird abgewiesen (`os.lstat`, nur reguläre Dateien). |
| Zwei Schreiber gleichzeitig mit derselben Datei | Temporärdatei trägt Prozessnummer und Zufallsanteil; `os.link` auf den Endnamen schlägt für den zweiten mit `FileExistsError` fehl und gilt als „schon da“ (Größe und Summe werden geprüft, siehe oben). |
| Platte voll beim Ablegen | `OSError`; die Temporärdatei wird gelöscht, kein Vorgang. Der Schreibweg antwortet wie bei anderen Speicherfehlern (Stufe 2). |
| Ablage und Bauordner auf verschiedenen Dateisystemen | `os.link` scheitert, Kopie als Rückfall (Entscheidung 8); Ergebnis gleich, nur langsamer. |
| Datenbank der Stufe 3 (`user_version` 1) | wird beim Öffnen auf 2 gehoben; alle alten Zeilen bleiben lesbar; ohne Medien-Umstellung ändert sich kein Verhalten. |
| Reise ohne Medien (`stadtwochenende`) | `ablage/` entsteht nicht; alle Wege laufen ohne Ablage. |
| Reise ohne Pläne (Status Idee) | unberührt, Medien sind unabhängig von Plänen. |
| Medien-Datei wird gelöscht | Tombstone wie bisher (`inhalt NULL`, `pruefsumme NULL`); die Ablagedatei bleibt liegen (nur anhängend). |
| Gleiche Bytes unter zwei Pfaden oder in zwei Reisen | zwei Verweise, eine Ablagedatei (AC-4). |
| Verwaiste Ablagedatei (Vorgang scheiterte nach dem Ablegen) | harmlos; `zustand` und `pruefen` melden sie nicht als Fehler (optional Zahl `ablage_verwaist` nur als Auskunft). |

## Acceptance Criteria

Neue Testdatei `engine/tests/test_reisespeicher_ablage.py` (`tmp_path`, eigener `FR_SPEICHER` je Test). Wo „beide Beispielreisen“ steht, sind die Tests über `beispielreise` und `stadtwochenende` parametrisiert; für `stadtwochenende` (ohne Medien) legt der Test eine erfundene Datei `medien/foto.png` (und `medien/strecke.gpx`) nachträglich an.

- **AC-1 Schema und Anhebung:** Given ein Speicher im Format der Stufe 3 (`user_version` 1, Spalte fehlt, mit Zeilen) / When `db()` ihn öffnet / Then ist `user_version` 2, die Spalte `ausgelagert` da (Vorgabe 0), alle alten Zeilen unverändert lesbar; ein zweites Öffnen ändert nichts; Trigger und Authorizer gelten weiter (ein `UPDATE` scheitert).
  - Test: `test_schema_wird_auf_version_2_gehoben`
- **AC-2 Auslagerungsregel:** Given Dateien `medien/a.png`, `medien/b.JPG`, `medien/c.gpx`, `medien/d.pmtiles`, `medien/icon.svg`, `medien/icon.png`, `reise.yaml`, `plan/x.md`, `bilder/e.png` / When sie in einem Vorgang geschrieben werden / Then haben genau a, b, c, d `ausgelagert = 1` mit `inhalt` NULL und Prüfsumme, die übrigen `ausgelagert = 0` mit Inhalt.
  - Test: `test_nur_medien_mit_endung_werden_ausgelagert`
- **AC-3 Ablage: Ort und Name:** Given ein ausgelagertes Foto / Then liegt es unter `<FR_SPEICHER>/ablage/<aa>/<summe>` mit `<aa>` = erste zwei Zeichen von `<summe>` = SHA-256 der Bytes, Datei Modus 400, Ordner 700; in der Datenbank steht kein Inhalt.
  - Test: `test_ablage_ort_name_und_rechte`
- **AC-4 Doppelte nur einmal (Akzeptanz #349):** Given dieselben Bytes unter zwei Pfaden einer Reise, in einer zweiten Reise und in einer späteren Version (Datei geändert, dann zurück) / When geschrieben / Then gibt es genau **eine** Datei in der Ablage (Zahl der Dateien unter `ablage/`), und jede Zeile verweist auf dieselbe Summe.
  - Test: `test_doppelte_liegen_nur_einmal_in_der_ablage`
- **AC-5 Export byte-gleich (beide Beispielreisen):** Given eine importierte Beispielreise (bei `stadtwochenende` mit nachträglich ergänzten Medien) / When `exportieren` und `materialisieren` laufen / Then entspricht der Ordner Byte für Byte `beispiel/reisen/<reise>` (gleiche Pfadmenge, gleiche Bytes, ohne `.git`); bei `beispielreise` mit `skizze-felsen.png` und den vier GPX-Dateien aus der Ablage.
  - Test: `test_export_und_materialisieren_byte_gleich_beide_reisen`
- **AC-6 Hardlink mit Kopie-Rückfall:** Given Ablage und Zielordner im selben Dateisystem / Then ist die Datei im Bauordner ein Hardlink (gleiche Inode wie die Ablagedatei); Given `os.link` scheitert (Attrappe wirft `OSError`) / Then ist sie eine Kopie mit gleichen Bytes und der Export gelingt.
  - Test: `test_materialisieren_hardlink_und_kopie_rueckfall`
- **AC-7 Schreibreihenfolge:** Given `_eintragen` scheitert nach dem Ablegen (z. B. `StandGeaendert`, Attrappe in der Transaktion) / Then liegt die Ablagedatei vor, die Datenbank hat keine Zeile; Given die Ablage ist nicht beschreibbar / Then wird weder Zeile noch Vorgang geschrieben. Eine Zeile, die auf eine nicht vorhandene Ablagedatei zeigt, kann durch Schreiben nie entstehen.
  - Test: `test_datei_wird_vor_der_datenbank_abgelegt`
- **AC-8 Nur anhängend:** Given eine geänderte oder gelöschte Medien-Datei / When ein neuer Vorgang sie ersetzt oder per Tombstone löscht / Then bleibt die alte Ablagedatei unverändert liegen (gleicher Inhalt, gleiche Änderungszeit), `zuruecksetzen` auf den alten Stand stellt die alte Fassung wieder her, und die Software enthält keinen Aufruf zum Löschen von Ablagedateien (ausgenommen die eigene Temporärdatei eines Schreibvorgangs).
  - Test: `test_ablage_wird_nie_geaendert_oder_geloescht`
- **AC-9 Fehlende Datei, Export:** Given eine gelöschte Ablagedatei / When `exportieren` oder `materialisieren` läuft / Then `AblageFehlt` mit Pfad und Summe, der Zielordner wurde nicht angelegt, ein vorhandener Ordner bleibt unberührt (kein halber Ordner).
  - Test: `test_fehlende_ablagedatei_bricht_export_ohne_halben_ordner`
- **AC-10 Fehlende Datei, Bau (Akzeptanz #349):** Given eine Speicher-Reise mit fehlender Ablagedatei / When `bauen.py` (Bau über den Speicher-Weg) läuft / Then Exit 2 mit der Meldung `pruefung.bauen.79` in der Sprache der Instanz; der Test prüft die Meldung in **jeder** Sprache aus `texte.SPRACHEN` (Parametrisierung über `SPRACHEN`, damit eine neue Sprache ohne Codeänderung mitgeprüft wird) und dass `{w1}`, `{ziel}`, `{summe}` ersetzt sind.
  - Test: `test_fehlende_datei_bricht_den_bau_mit_katalogtext_in_allen_sprachen_ab`
- **AC-11 Beschädigte Datei:** Given eine Ablagedatei mit geänderten Bytes / When `datei`, `aktueller_stand`, Export oder Bau lesen / Then `AblageFehler` bzw. Bau Exit 2 mit `pruefung.bauen.80`; `pruefen` meldet `store checksum mismatch`; die Datei wird nicht verändert.
  - Test: `test_beschaedigte_ablagedatei_wird_erkannt_und_nicht_repariert`
- **AC-12 Zielname belegt mit falschem Inhalt:** Given am Zielnamen liegt eine Datei mit falscher Größe / When dieselbe Summe geschrieben werden soll / Then `AblageFehler`, kein Vorgang, die Datei bleibt unverändert.
  - Test: `test_vorhandene_ablagedatei_mit_falschem_inhalt_wird_nicht_ueberschrieben`
- **AC-13 Pfadsicherheit:** Given `ablage_pfad` mit `../x`, `abc`, einer Summe mit Großbuchstaben, einer zu langen Summe, leer / Then `ValueError`; Given eine Ablagedatei, die ein Symlink ist / Then wird sie beim Lesen und Verknüpfen abgewiesen; Given ein Reisepfad `medien/../../x.png` / Then lehnt `_pfad_pruefen` ihn ab, bevor etwas abgelegt wird.
  - Test: `test_ablage_pfad_nur_aus_summe_und_symlink_abgewiesen`
- **AC-14 Prüfsumme, Vergleich und Stand ohne Ablagezugriff:** Given eine Reise mit ausgelagerten Medien / When `vergleichen` und `stand_nummer` laufen / Then lesen sie keine Ablagedatei (der Test ersetzt `ablage_lesen`/`os.link` durch Fallen, die scheitern) und `vergleichen` ergibt `gleich` (Exit 0) gegen den Ordner der Beispielreise.
  - Test: `test_vergleichen_braucht_keine_ablagedatei`
- **AC-15 Verweis ist nicht gelöscht:** Given eine ausgelagerte Datei und danach ein Tombstone für eine andere / Then zählt `_stand` die ausgelagerte Datei als vorhanden (`inhalt` NULL, aber Prüfsumme gesetzt), den Tombstone als gelöscht.
  - Test: `test_verweis_zaehlt_nicht_als_tombstone`
- **AC-16 Prüfen:** Given eine Reise mit ausgelagerten Dateien / Then meldet `pruefen` `ok` (Exit 0, keine Fundzeilen); Given eine fehlende, eine beschädigte Ablagedatei, ein `ausgelagert = 1` mit Inhalt, ein `ausgelagert = 1` ohne Summe / Then je ein Fund mit Reise, Pfad und Vorgang.
  - Test: `test_pruefen_prueft_die_ablage`
- **AC-17 Zustand:** Given eine fehlende Ablagedatei / When `zustand` läuft / Then Zeile `ablage_fehlt 1`, Exit 1 und nichts wird geschrieben; ohne fehlende Datei `ablage_fehlt 0` und Exit wie bisher.
  - Test: `test_zustand_meldet_fehlende_ablagedateien`
- **AC-18 Sicherung schlägt bei fehlender Ablagedatei fehl:** Given eine fehlende Ablagedatei / When `sichern` läuft / Then Fehler, der vorige Schnappschuss bleibt; Given alles vorhanden / Then Schnappschuss wie bisher, geprüft mit `integrity_check`.
  - Test: `test_sichern_verlangt_vollstaendige_ablage`
- **AC-19 Wiederherstellung (Prüfpunkt):** Given ein Schnappschuss `sicherung/reisen.db` und eine Kopie von `ablage/` in einem Wegwerf-Ordner (Test: `tmp_path`) / When als `reisen.db` eingesetzt / Then `pruefen` `ok`, `vergleichen` der Beispielreise Exit 0 und `materialisieren` baut den Ordner; ohne die Kopie von `ablage/` meldet `pruefen` die fehlenden Dateien (belegt, dass eine Sicherung ohne Ablage wertlos ist).
  - Test: `test_wiederherstellung_aus_schnappschuss_und_ablage`
- **AC-20 Migration der Medien (#250):** Given ein Speicher der Stufe 3 mit Medien als BLOB (beide Beispielreisen, bei `stadtwochenende` mit ergänzten Medien) / When `neu.py nachziehen-speicher <reise> <ordner>` läuft / Then entsteht genau ein Vorgang (Person „Software-Nachziehen“, Werkzeug `nachziehen`, Titel `ablage-umstellung`), die Medien tragen `ausgelagert = 1`, die Ablage enthält sie, der Export des neuen Stands entspricht Byte für Byte dem davor, und alle Wege lesen aus der Ablage (die alten BLOBs werden nicht mehr gelesen: der Test löscht die Ablagedatei und erwartet `AblageFehlt`).
  - Test: `test_nachziehen_speicher_lagert_bestehende_medien_aus`
- **AC-21 Migration idempotent:** Given eine umgestellte Reise / When der Befehl wieder läuft / Then `nichts umzustellen`, Exit 0, kein Vorgang, Stand gleich; dieselbe Kennung zweimal trägt nie doppelt ein; eine Reise ohne Medien erzeugt gar keinen Vorgang.
  - Test: `test_nachziehen_speicher_ablage_ist_idempotent`
- **AC-22 Migration bei Wettlauf:** Given zwischen Lesen und Eintragen schreibt jemand / Then `StandGeaendert`, neu gelesen, höchstens dreimal, dann Exit 1 und kein Vorgang; die bereits abgelegten Dateien bleiben (harmlos).
  - Test: `test_nachziehen_speicher_ablage_wiederholt_bei_wettlauf`
- **AC-23 Ohne Handschritt:** Given ein Bauordner mit Speicher-Reise im Format der Stufe 3 und ein neuer Software-Stand / When die Läufe von `veroeffentlichen.sh` (Stufe 3, Software-Wechsel) laufen / Then ist die Reise umgestellt, ohne dass jemand `neu.py` oder `reisespeicher.py` aufruft; `docs/betrieb.md` nennt für die Umstellung keinen Handschritt (der Neuaufbau `ablage-umstellen` ist als freiwillig ausgewiesen).
  - Test: `test_software_wechsel_lagert_medien_ohne_handschritt_aus` (Shell-Lauf in `engine/tests/test_betrieb.py` mit der Fixture `vf`) und `test_doku_nennt_keinen_handschritt_fuer_die_ablage`
- **AC-24 Beispielreise baut wie bisher (Akzeptanz #349):** Given `beispielreise` (Symbol, Skizze, GPX) und `stadtwochenende` im Speicher mit Auslagerung / When veröffentlicht wird (Lauf `veroeffentlichen.sh` mit der Fixture `vf`, Stufe-3-Weg) / Then ist `dist/` der Reise **gleich** dem Bau derselben Reise aus dem Ordner (gleiche Dateien, gleiche Bytes ausser Zeitangaben und Stand-Nummer: Vergleich über `daten.json` ohne die Felder `reise_stand`), die Karte zeigt die Strecken, `sw.js` und `manifest.json` stehen da; der **Browser-Rundgang** (`betrieb/pruefsitzung.py` bzw. die Rundgang-Tests der Engine, siehe Prüfstelle Frage 8) läuft für **beide** Reisetypen grün (Nachweis im Issue, mit einer Testreise, nie mit einer echten).
  - Test: `test_speicher_reise_mit_ablage_baut_wie_aus_dem_ordner` (beide Reisen), Browser-Rundgang als Nachweis im Issue
- **AC-25 Schreibweg:** Given ein GPX-Track aus dem Gespräch (`track_anhaengen`) und ein App-Symbol (`icon_set`) auf einer Speicher-Reise / Then liegt die GPX-Datei in der Ablage (`ausgelagert = 1`), das Symbol in der Datenbank (`ausgelagert = 0`), und der Bau findet beides.
  - Test: `test_schreibweg_track_in_ablage_symbol_in_datenbank`
- **AC-26 Leere Instanz und Git-Reisen:** Given `FR_SPEICHERREISEN` leer / Then entsteht kein `ablage/`, kein Aufruf in den Betriebsskripten ändert sich, alle bestehenden Tests bleiben ohne geänderte Erwartung grün (insbesondere `test_reisespeicher.py`, `test_speicher_stufe3.py`, `test_betrieb.py`).
  - Test: bestehende Tests und `test_ohne_speicherreisen_entsteht_keine_ablage`
- **AC-27 Zeitziel:** Siehe „Zeitziele“; der Messlauf belegt es, kein automatischer Test (außer dem Kurzlauf des Messskripts `test_messlauf_skript_gibt_kennzahlen_aus`, der grün bleibt).
  - Test: Messwerte im Issue; `engine/tests/test_schreiben_speicher.py::test_messlauf_skript_gibt_kennzahlen_aus`
- **AC-28 Katalog und Module:** Given die neuen Schlüssel `pruefung.bauen.79` und `.80` / Then stehen sie in jeder Sprachdatei (`test_texte.py` bleibt grün, die Ausnahmelisten wurden nicht länger); `betrieb/deploy.sh` listet kein neues Modul (die Ablage steckt in `reisespeicher.py`), der Modullisten-Test bleibt grün.
  - Test: `engine/tests/test_texte.py` (bestehend) und `engine/tests/test_betrieb.py` (Modullisten)

## Zeitziele

Bezugsgröße ist die erfundene Testreise `gross-erfunden` mit 110 MB Zufallsfotos (`betrieb/messlauf-schreibweg.py --auffuellen 110`, legt die Fotos jetzt in die Ablage). Ziele (Produkt aus Stufe 3, nach Auslagerung neu zu messen):

| Vorgang | Ziel |
|---|---|
| `materialisieren` einer 110-MB-Reise (Hardlink) | unter 5 s (Stufe 3: Ziel unverändert; die Bytes werden zur Summenprüfung einmal streamend gelesen, rund 0,3 s je 100 MB; Messlauf `--auffuellen` neu messen) |
| `materialisieren` mit Kopie-Rückfall | unter 5 s (Annahme, wird gemessen) |
| `vergleichen` einer 110-MB-Reise | unter 10 s; ohne Ablagezugriff (AC-14) |
| Schreibvorgang auf der 110-MB-Reise (ein Foto dazu) | höchstens wie vorher (Maximum 4,2 s aus Stufe 2) |
| `pruefen` der 110-MB-Reise | Auskunft, kein hartes Ziel (liest alle Bytes einmal) |
| Gesamtzeit Schreiben bis Veröffentlichen | unter 120 s (`ZIEL_SEKUNDEN`) |

Reißt eine Messung das Ziel, ist das ein Befund im Issue, kein stilles Anpassen des Ziels.

## Dateien

| Datei | Änderung | Beschreibung |
|---|---|---|
| `engine/reisespeicher.py` | MODIFY | Schema und `user_version` 2, `AUSLAGERN`, `ablage_pfad`, `ablage_ablegen`, `ablage_lesen`, `auslagern`, `AblageFehlt`, `AblageFehler`; `_stand` (Tombstone-Erkennung), `_eintragen`, `datei`, `aktueller_stand`, `exportieren`, `pruefen`, `zustand`, `sichern`, optional `ablage-umstellen` in `main` |
| `engine/instanz.py` | MODIFY | `speicher_ablage()` |
| `engine/neu.py` | MODIFY | `nachziehen-speicher`: Medien in die Ablage übernehmen (idempotent) |
| `engine/bauen.py` | MODIFY (klein) | `AblageFehlt`/`AblageFehler` beim Materialisieren zu Exit 2 und Katalogtext |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | `pruefung.bauen.79`, `pruefung.bauen.80` |
| `engine/schreiben.py` | PRÜFEN | `track_anhaengen`, `icon_set`: keine Änderung erwartet |
| `betrieb/messlauf-schreibweg.py` | MODIFY | `--auffuellen` legt Fotos in die Ablage |
| `betrieb/deploy.sh` | PRÜFEN | Modulliste unverändert (kein neues Modul) |
| `docs/betrieb.md` | MODIFY | Ablage, Sicherung und Wiederherstellung, `ablage-umstellen`, Zeitziele |
| `docs/adr/0009-reisespeicher.md` | MODIFY | „Format ändert sich nicht“ durch Stufe 4 ersetzen: Spalte `ausgelagert`, Ablage nach Prüfsumme, nur anhängend; Verlauf Stufe 4 |
| `engine/tests/test_reisespeicher_ablage.py` | CREATE | Tests der Python-Ebene (AC-1 bis AC-22, AC-25, AC-26 `test_ohne_speicherreisen_entsteht_keine_ablage`) |
| `engine/tests/test_betrieb.py` | MODIFY | AC-23, AC-24 (Shell-Läufe mit `vf`) |
| `engine/tests/test_schreiben_speicher.py` | PRÜFEN | AC-27 (Messlauf-Skript gibt Kennzahlen aus) |
| `engine/tests/test_texte.py` | PRÜFEN | Ausnahmelisten nicht länger |
| Infra-Repo der Instanz, `backup.sh` | MODIFY (selbst erledigen, eigenes Issue dort) | `ablage/` mit sichern, Rückspielversuch mit Fotos |

## Risiken und offene Annahmen

- **Authorizer und Trigger (A-1).** Anhängen-Schutz und Authorizer verbieten `UPDATE`/`DELETE`/`ALTER`. `ALTER TABLE ADD COLUMN` geschieht deshalb in `db()` vor dem Authorizer; die alten BLOBs lassen sich nur durch Neuaufbau entfernen. Nicht belegt: ob `ALTER TABLE … ADD COLUMN` mit den vorhandenen Triggern `versionen_kein_update` verträglich ist (die Trigger betreffen `UPDATE`, nicht `ALTER`); der Test AC-1 klärt es vor dem Bauen.
- **Hardlink-Gefahr (A-2).** Wer eine verknüpfte Datei im Bauordner in-place beschreibt, ändert die Ablage. Gegenmittel: Dateien in der Ablage Modus 400, Bau schreibt nach `dist/`; AC-6.
- **Sicherung ist jetzt zweiteilig.** Ein Schnappschuss der Datenbank allein ist wertlos ohne Ablage (AC-19). Zuständig für die Ablage ist das Server-Backup im Infra-Repo der Instanz; ohne das Issue dort ist die Stufe nicht abgeschlossen (Definition of Done).
- **Dateisystem der Ablage.** Liegen `<FR_SPEICHER>/ablage` und `<FR_DIENST>/bau` auf verschiedenen Dateisystemen, wird kopiert (langsamer). Nicht geprüft, wie die Instanz es einrichtet; die Messung auf dem Server zeigt es.
- **Byte-Gleichheit nach ADR-0009.** Der Export bleibt byte-gleich; die Aussage im ADR, das Format ändere sich nicht, gilt für Stufe 4 nicht mehr und wird ersetzt.
- **Alte Leser der Datenbank.** Ein Prozess mit Software vor Stufe 4 liest `inhalt` NULL und hielte einen Verweis für gelöscht. Gegenmittel: Dienste und Bauordner werden gemeinsam mit der Software umgestellt (Deploy); die Schema-Anhebung erfolgt nur beim ersten Öffnen mit der neuen Software.
- **Personenbezogene Daten.** Fotos zeigen Personen; Rechte 700/400 wie der Speicher; keine Pfade aus Eingaben; keine echten Reisen in Tests oder Nachweisen.
- **Keine Instanzspezifika:** Pfade und Benutzer kommen aus den Einstellungen; Beispiele und Tests nutzen nur die beiden Beispielreisen und erfundene Testdaten.

## Test Plan

### Automated Tests (TDD RED)

- [ ] Test 1: GIVEN ein Speicher der Stufe 3 WHEN geöffnet THEN Schema 2, alte Zeilen lesbar, Anhängen-Schutz bleibt (AC-1).
- [ ] Test 2: GIVEN Medien und Nicht-Medien WHEN geschrieben THEN nur Medien mit Endung ausgelagert, Name nach Summe, Rechte, Doppelte einmal (AC-2 bis AC-4).
- [ ] Test 3: GIVEN beide Beispielreisen WHEN exportiert und materialisiert THEN Byte-gleich, Hardlink und Rückfall (AC-5, AC-6).
- [ ] Test 4: GIVEN Fehlerfälle WHEN gelesen oder gebaut THEN Reihenfolge, Nur-anhängend, fehlende und beschädigte Datei, Katalogtext in allen Sprachen, Pfadsicherheit (AC-7 bis AC-13).
- [ ] Test 5: GIVEN `vergleichen`, `pruefen`, `zustand`, `sichern` WHEN Ablage vollständig, lückenhaft, beschädigt THEN Exit-Codes und Funde (AC-14 bis AC-19).
- [ ] Test 6: GIVEN ein Speicher der Stufe 3 WHEN `nachziehen-speicher` und der Software-Wechsel laufen THEN ein Vorgang, idempotent, Wettlauf, ohne Handschritt (AC-20 bis AC-23).
- [ ] Test 7: GIVEN beide Beispielreisen WHEN veröffentlicht THEN Seite wie bisher (AC-24), Schreibweg (AC-25), leere Instanz (AC-26).

Die Tests sind den Acceptance Criteria zugeordnet; RED vor dem Bauen (`40-tdd-red`).

## Definition of Done

- [ ] Jede Acceptance Criterion durch einen automatischen Test belegt (Ausnahmen mit Nachweis im Issue: AC-24 Browser-Rundgang, AC-27 Messung)
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n auto` grün, ohne echte Reisen, mit beiden Beispielreisen
- [ ] Tests der einbindenden Instanzen mit dem Branch laufen vor dem Vorspulen (Format des Speichers, Meldungstexte)
- [ ] ADR-0009, `docs/betrieb.md` aktuell; Katalogtexte in allen Sprachen
- [ ] Issue im Infra-Repo der Instanz für die Sicherung von `ablage/` angelegt, umgesetzt und in #349 verlinkt; Rückspielversuch mit Fotos dokumentiert (ohne Pfade der Instanz)
- [ ] Messwerte der 110-MB-Testreise im Issue #349
- [ ] Browser-Rundgang grün für beide Beispielreisen (Testreise, nie eine echte)
- [ ] Kein Handschritt nach dem Software-Wechsel (#250)
- [ ] Annahmen A-1 und A-2 bestätigt (oder geändert und die Spec nachgezogen)

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** ADR-0009 (`docs/adr/0009-reisespeicher.md`), wird um Stufe 4 ergänzt (Ablage nach Prüfsumme, Spalte `ausgelagert`, Aussage „Format ändert sich nicht“ ersetzt).
- **Rationale:** ADR-0009 sieht die Auslagerung großer Fotos als Stufe 4 vor. Die Entscheidung berührt Grundformen und Merkmale nicht (ADR-0001, Punkt 8); ein neues ADR ist nicht nötig.

## Known Limitations

- Bestehende Datenbanken behalten die alten BLOBs, bis der freiwillige Neuaufbau `ablage-umstellen` läuft (A-1).
- Die Ablage wird nie verkleinert; verwaiste Dateien räumt nur der Betreiber auf.
- Hardlinks setzen dasselbe Dateisystem voraus, sonst wird kopiert (A-2).
- Das Issue-Wort „nichts davon in der Datenbank“ gilt für die Bytes; die Zeile (Pfad, Prüfsumme) bleibt in der Datenbank, damit Versionierung und Zurücksetzen erhalten bleiben.
- Git-Reisen behalten `medien/` im Repo bis Stufe 5.

## Changelog

- 2026-11-08: Initial spec created
- 2026-11-08: Überarbeitet nach Validierung: Summenprüfung beim Export/Bau, `os.link` statt `os.replace`, Sicherungsreihenfolge (Schnappschuss, dann Ablage), Zeitziel, Reihenfolge der zwei Nachzieh-Vorgänge, Katalogaufruf `texte.satz`
