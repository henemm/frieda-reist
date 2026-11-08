# Context: speicher-349-stufe4

## Request Summary
Issue #349 (Stufe 4 von Epic #345): Fotos und GPX liegen als Dateien in einer Ablage auf dem Server, benannt nach Prüfsumme. In den Reisedaten steht nur der Verweis mit Prüfsumme; nichts davon in der Datenbank und nicht im Repo. Generator liest von dort, PWA bleibt offline nutzbar, Import legt vorhandene Fotos in die Ablage, Sicherung zusammen mit der Datenbank, Umstellung des Formats in `neu.py nachziehen` mit Test (#250). Akzeptanz: Beispielreise mit Fotos und GPX baut wie bisher; Duplikate nur einmal in der Ablage; fehlende Datei bricht den Bau mit Katalogtext (alle Sprachen) ab; Browser-Rundgang grün, beide Beispielreisen.

## Related Files
| File | Relevance |
|------|-----------|
| `docs/adr/0009-reisespeicher.md` | Entscheidung 1–6; „Stufe 4: Auslagerung großer Fotos aus der Datenbank“; Aussage „Format ändert sich nicht“ gilt für Stufe 4 nicht mehr (muss ergänzt werden) |
| `engine/reisespeicher.py` | Alle Dateien einer Reise sind BLOBs in `versionen` (`vorgang_schreiben`, `_eintragen`, `_stand`, `aktueller_stand`, `exportieren`, `materialisieren`, `importieren`, `ordner_als_vorgang`, `pruefen`, `sichern`). Exportiert Byte für Byte; Stufe 4 muss Medien im Export aus der Ablage zurückholen oder als Verweis lassen |
| `engine/bauen.py` | Liest `medien/` aus dem Reiseordner: Bilder in Markdown (`bilder_umschreiben`, `BILD_LINK`, `BILD_ENDUNGEN`, `bilder_schreiben` mit `bilder_max_breite`), GPX (`strecken_gpx`, `gpx.lesen`), PMTiles (`medien/karte/*.pmtiles`, `grundkarten`), App-Symbol (`medien/icon.svg|png`); räumt in `ziel/medien` Unerwünschtes weg; Meldungen `pruefung.bauen.7/8/48` |
| `engine/gpx.py` | GPX lesen, vereinfachen, Wegpunkte |
| `engine/routen.py` | `gpx:` einer Strecke = Pfad `medien/…​.gpx` (Prüfung Zeile ~265, ~669) |
| `engine/schreiben.py` | `track_anhaengen` (GPX aus Gespräch nach `medien/gpx/<name>.gpx`, ~1979–2004), App-Symbol (`icon_set`, ~2931); Schreibweg Speicher: `ordner_als_vorgang` |
| `engine/neu.py` | `reise_anlegen` (legt `medien/` an, Zeile ~184), `nachziehen` und `nachziehen-speicher` (Format-Umstellung, #250); Zeile ~111 überspringt `medien` |
| `engine/belege.py` | Vorbild für Dateien in der Ablage der Instanz (`<FR_ABLAGE>/<reise>/belege/`, Verzeichnis `belege.json`, Größenlimits) |
| `engine/instanz.py` | Ortsfunktionen (`speicher()`, `ablage()`, `dienst()`); eine Ablage-Funktion für Medien käme hierher |
| `betrieb/veroeffentlichen.sh`, `betrieb/deploy.sh` | Speicher-Teil materialisiert nach `<FR_DIENST>/bau/reisen/<reise>`; Liste der Module; Backup-Hinweise |
| `betrieb/messlauf-schreibweg.py` | Messlauf mit `--auffuellen` (Fotos als Zufallsdaten in der Datenbank) |
| `werkzeuge/grundkarte_auto.py`, `werkzeuge/karte-holen.sh` | schreiben PMTiles nach `medien/karte/` (große Dateien) |
| `engine/wachter.py` / `waechter.py` | tägliche Sicherung des Speichers (`sichern`) |
| `docs/betrieb.md` | Ablagen der Instanz, Sicherung („Das Server-Backup sichert `<FR_KONTEN>/` und `<FR_ABLAGE>/`“, Reisespeicher-Abschnitt) |
| `beispiel/reisen/beispielreise/medien/` | `icon.svg`, `skizze-felsen.png`, `gpx/etappe-1..4*.gpx` – Beispiel für Foto/GPX; `stadtwochenende` hat keine Medien (zweiter Reisetyp prüfen) |
| `engine/texte_de.py`, `texte_en.py` (+ weitere Sprachen), `engine/tests/test_texte.py` | Katalogtexte für die neue Meldung „Datei fehlt in der Ablage“ in allen Sprachen |

## Existing Patterns
- Alles in `medien/` ist heute Teil der Reise (Datei im Ordner, im Speicher als BLOB, im Git-Repo als Datei). Der Generator kennt keinen Verweis, er liest Pfade im Reiseordner.
- Der Speicher exportiert Byte-gleich (ADR-0009); `materialisieren` baut den Ordner für den Generator. Genau dort kann Stufe 4 ansetzen: Verweise wieder zu echten Dateien machen (Hardlink/Kopie aus der Ablage), damit Generator, PWA-Bau und Tests unverändert bleiben.
- Inhaltsadressierte Ablage mit Prüfsumme wie `versionen.pruefsumme` (SHA-256) schon vorhanden.
- Ablagen der Instanz liegen außerhalb des Repos und werden vom Server-Backup mitgenommen (`<FR_ABLAGE>`, `<FR_SPEICHER>/sicherung`). Die Datenbank-Sicherung ist ein Schnappschuss; die Ablage ist nur anhängend (Dateien nie ändern, nur ergänzen) und braucht dafür eine eigene Sicherungsaussage.
- Formatwechsel bringen ihre Umstellung in `neu.py nachziehen` mit Test (CLAUDE.md, #250); `nachziehen-speicher` stellt eine Speicher-Reise in einem Vorgang um.
- Neue Katalogtexte gehören in alle Sprachdateien; die Ausnahmelisten in `test_texte.py` dürfen nur kürzer werden.
- Neue Module der Dienste: Liste in `betrieb/deploy.sh` (Test prüft das).

## Dependencies
- Upstream: `reisespeicher.py` (Stufen 1–3), `instanz.py` (Orte), `bauen.py` (liest `medien/`), `gpx.py`, SHA-256 aus `hashlib`.
- Downstream: Schreibweg (`track_anhaengen`, `icon_set`, `ordner_als_vorgang`), Veröffentlichen/`materialisieren`, `nachziehen-speicher`, Vergleichslauf (`vergleichen`), Wächter-Sicherung, Messlauf (`--auffuellen`), Server-Backup (henemm-infra `backup.sh`), `monitor.sh` Teil-Check (`check_frieda_speicher`).
- Das Git-Repo einer Git-Reise ist nicht betroffen (Stufe 4 gilt nur für Speicher-Reisen; Git-Reisen behalten `medien/` im Repo bis Stufe 5).

## Existing Specs
- `docs/specs/betrieb/speicher-348-stufe3.md` (Materialisieren, Vergleichslauf, Zeitziele)
- `docs/specs/…/speicher-347-*` (Schreibweg), `speicher-346-stufe1` (Speicher)
- `docs/context/speicher-346-stufe1.md`, `speicher-347-stufe2.md`, `speicher-347-tempo.md`, `speicher-348-stufe3.md`

## Risks & Considerations
- **Format-Änderung betrifft alle Reisen und Instanzen:** Umstellung in `nachziehen`/`nachziehen-speicher` mit Test; Git-Reisen dürfen nicht kippen (nur Speicher-Reisen bekommen Verweise).
- **Bytegleicher Export:** ADR-0009 verspricht Byte-Gleichheit; mit Verweisen ändert sich, was „Stand“ als Dateimenge ist. Der Vergleichslauf (`vergleichen`) und `pruefen` müssen den Verweis auflösen können.
- **Verlust von Dateien:** Die Ablage ist künftig Teil der Wahrheit der Reise. Sicherung, Rückspieltest und Prüfung (`pruefen`: jede Prüfsumme in der Ablage vorhanden und stimmt) sind Pflicht, sonst ist ein Backup ohne Fotos wertlos.
- **PMTiles und andere große Dateien** in `medien/karte/` sind ebenfalls Medien; Entscheidung nötig, ob sie auch in die Ablage gehören (Issue nennt nur Fotos und GPX; `grundkarte_auto.py` schreibt sie nach `medien/karte/`).
- **Kleine Dateien (icon.svg, GPX):** Sind GPX/Icons „Medien“ im Sinn der Ablage? Das Issue nennt GPX ausdrücklich; Symbol bleibt vermutlich in der Datenbank (klein, wird beim Bau gebraucht).
- **Nebenläufigkeit:** Ablage-Schreiben vor dem Datenbank-Vorgang (Datei zuerst, dann Verweis), sonst zeigt ein Vorgang auf eine fehlende Datei; Aufräumen verwaister Dateien nur durch den Betreiber (nur anhängen).
- **PWA offline:** Der Bau kopiert Bilder ins Ziel; solange `materialisieren` echte Dateien legt, bleibt das unverändert (Browser-Rundgang prüft es).
- **Zeitziele aus Stufe 3** (Materialisieren < 5 s) müssen mit Hardlinks/Kopien gelten; Messlauf `--auffuellen` neu messen.
- **Sicherheit/Datenschutz:** Fotos sind personenbezogen; Ablage 700/600 wie der Speicher; kein Pfad aus Nutzereingaben (nur Prüfsumme als Name), Pfadprüfung wie `_pfad_pruefen`.
- **Server-Backup in henemm-infra:** `backup.sh` muss die Ablage mitnehmen (selbst erledigen, Issue in henemm-infra).
- **Offene Entscheidung für den Product Owner (ADR-0001/0009):** Geltungsbereich (nur Fotos/GPX oder alle Medien), Verweisformat, Kopie vs. Hardlink; nach der Analyse mit AskUserQuestion klären.

## Analysis

### Type
Feature (Stufe 4 von Epic #345; ändert das Speicherformat, daher Umstellung in `neu.py nachziehen-speicher` nötig, #250).

### Kernidee (Tech-Lead-Entscheidung)
Die Tabelle `versionen` bekommt eine Spalte `ausgelagert` (0/1). Bei einer ausgelagerten Datei bleibt `pruefsumme` (SHA-256) wie bisher, `inhalt` ist NULL, die Bytes liegen in der Ablage `<FR_SPEICHER>/ablage/<aa>/<summe>` (Name = Prüfsumme, nur anhängend, Rechte 700/600). Tombstone bleibt „inhalt NULL und pruefsumme NULL“, also unverwechselbar.
Folgen: `vergleichen`, `pruefen`, Stand-Logik (`_stand` mit Spalte pruefsumme) und der Byte-gleiche Export bleiben unverändert im Sinn; nur Lesen der Bytes (`_stand` mit `inhalt`, `datei`, `exportieren`) holt ausgelagerte Dateien aus der Ablage. Generator, PWA-Bau, Browser-Rundgang bleiben unberührt, weil `materialisieren` weiter echte Dateien legt (Hardlink aus der Ablage, Rückfall Kopie bei anderem Dateisystem).

### Geltungsbereich (Entscheidung)
Ausgelagert wird per Endung unter `medien/`: Bilder (png, jpg, jpeg, webp, gif), `.gpx`, `.pmtiles`. Nicht: `icon.svg|png` (klein, im Bau gebraucht), Markdown/YAML/JSON. Keine Größenschwelle (Regel statt Zufall; Doppelte werden dadurch nur einmal abgelegt). Nur Speicher-Reisen; Git-Reisen behalten `medien/` im Repo bis Stufe 5.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/reisespeicher.py | MODIFY | Schema-Migration (`ausgelagert`), `_eintragen` legt Datei zuerst in Ablage (atomar: tmp, fsync, rename), dann Zeile; Lesepfade holen aus Ablage; `materialisieren` Hardlink/Kopie; `pruefen` prüft Ablage (vorhanden, Summe stimmt); `sichern` nimmt Ablage mit bzw. meldet; Fehlerklasse „Datei fehlt in der Ablage“ |
| engine/instanz.py | MODIFY | `speicher_ablage()` (Ort aus `speicher()`) |
| engine/neu.py | MODIFY | `nachziehen-speicher`: vorhandene BLOBs von Medien in die Ablage umstellen (idempotent) |
| engine/bauen.py | MODIFY (klein) | Bau bricht bei fehlender/unlesbarer Ablagedatei mit Katalogtext ab (Prüfung beim Materialisieren und im Bau) |
| engine/texte_*.py, tests/test_texte.py | MODIFY | neue Meldung in allen Sprachen |
| engine/schreiben.py | MODIFY (prüfen) | `track_anhaengen` und Fotos laufen über `ordner_als_vorgang`, sollten ohne Änderung greifen |
| betrieb/deploy.sh, docs/betrieb.md, docs/adr/0009-reisespeicher.md | MODIFY | ADR: Satz „Format ändert sich nicht“ ersetzen; Sicherung der Ablage; Backup-Hinweis |
| betrieb/messlauf-schreibweg.py | MODIFY | `--auffuellen` legt Fotos in die Ablage |
| engine/tests/test_reisespeicher_ablage.py | CREATE | Doppelte nur einmal, Export Byte-gleich, fehlende Datei, Migration, Hardlink-Rückfall, Pfad-Sicherheit, Wettlauf |
| henemm-infra backup.sh | MODIFY (selbst erledigen, Issue dort) | Ablage außer Haus mitsichern, Rückspielversuch mit Fotos |

### Scope Assessment
- Files: ca. 9 Code/Doku plus 1–2 Testdateien, 1 Fremdrepo-Anteil
- Estimated LoC: +450/-40
- Risk Level: MEDIUM (Format aller Speicher-Reisen; Datenverlust nur, wenn Ablage nicht gesichert wird)

### Technical Approach
1. Reihenfolge beim Schreiben: Datei in Ablage (fsync, rename), danach Datenbank-Transaktion; verwaiste Ablagedateien sind harmlos (nur der Betreiber räumt auf).
2. Migration der DB per `PRAGMA user_version`; `nachziehen-speicher` lagert bestehende BLOBs aus (Vorgang „ablage-umstellung“, Inhalt der Reise bleibt gleich, Prüfsummen identisch, Vergleichslauf beweist es).
3. Sicherung: Datenbank-Schnappschuss bleibt; Ablage ist nur anhängend und wird vom Server-Backup (`<FR_SPEICHER>`) mitgenommen; `zustand`/Monitor prüft zusätzlich, dass alle referenzierten Summen in der Ablage liegen.
4. Tests und Abnahme: beide Beispielreisen (Stadtwochenende hat keine Medien: Test muss dort ohne Ablage laufen und eine Reise mit Fotos nachträglich anlegen), Browser-Rundgang, Zeitziel Materialisieren < 5 s neu messen.

### Befunde gegen den Plan
Keine zwingenden. Bewusst anders als das Issue-Wort „nichts davon in der Datenbank“: die Zeile (Pfad, Prüfsumme) bleibt in der Datenbank, nur die Bytes nicht; das ist der „Verweis mit Prüfsumme“ und erhält Versionierung und Zurücksetzen.

### Dependencies
Upstream: `reisespeicher.py`, `instanz.py`, `hashlib`. Downstream: Schreibweg, Veröffentlichen/`materialisieren`, `nachziehen-speicher`, `vergleichen`, Wächter-Sicherung, Messlauf, Server-Backup.

### Open Questions
- [ ] Keine für den PO: Kopie/Hardlink, Endungsliste und Verweisformat sind oben als Tech-Lead-Entscheidung gesetzt; Einspruch in `/30-write-spec` möglich.
