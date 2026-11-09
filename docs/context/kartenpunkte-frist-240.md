# Context: Kartenpunkte-Frist (#240, K14 `map_points_fetch`)

## Request Summary
`kartenpunkte_holen` (`map_points_fetch`) liefert am echten Overpass-Dienst nie Treffer: Der Dienst braucht vom Server der Instanz aus
33–44 s (ein Rechner von overpass-api.de antwortet sofort mit 502, der andere langsam), das Werkzeug wartet nur `OSM_ZEIT` = 12 s,
innerhalb von `ZEIT_GESAMT` = 25 s und unter der Sperre der Reise. Die Abfrage soll aus dem Schreibvorgang gelöst werden: Abruf vor der
Sperre mit eigener, längerer Frist und einer Wiederholung bei sofortigem 502; danach die offene Abnahme aus #240.

## Messungen (9.11.2026, vom Server, UTC)
- Ohne User-Agent: 406 (Overpass verlangt eine Kennung; das Werkzeug sendet `instanz.kennung()`, also kein Problem).
- Mit Kennung, kleine Abfrage: 200 nach 33–34 s; ein weiterer Versuch 502 nach 0,1 s.
- overpass.private.coffee, overpass.kumi.systems: kein Antwort in 40 s.

## Related Files
| File | Relevance |
|------|-----------|
| engine/schreiben.py:2018–2040 | `OVERPASS`, `OSM_ZEIT = 12`, `overpass_abfragen(abfrage)` (Tests ersetzen sie), Ablehnungen `schreiben.kartenpunkte.limit`/`.dienst` |
| engine/schreiben.py:2186–2260 | `kartenpunkte_holen`: liest Route (`route_stand`), Linie aus `karte.wege[sid]` oder Orte von/nach, baut bbox und Abfrage, ruft `overpass_abfragen`, filtert nach Abstand, `kartenpunkte_ablegen(..., aktualisieren=True)` |
| engine/schreiben.py:65–69 | `ZEIT_GESAMT = 25`, `ZEIT_SPERRE = 3`, `ZEIT_PRUEFUNG = 3` (Kommentar zu 30 s nginx ist veraltet, /mcp hat 300 s) |
| engine/schreiben.py:5006–5110 | `anwenden_extern` (Weiche Speicher/Git) und `vorgang_speicher` (Sperre, Export in tmp, Unterprozess `anwenden` mit `FR_SB_FRIST`) |
| engine/schreiben_git.py:~175 | `vorgang` des Git-Wegs, `s.ende = start + sb.ZEIT_GESAMT`, gleiche Sperre |
| engine/schreiben.py:5182–5201 | `Dienst.do_POST` → `anwenden_extern`; Anfrage-JSON vom Konnektor |
| engine/konnektor.py:1263 | `schreib_anfrage`: wartet 120 s auf den Schreibdienst |
| betrieb/vorlagen/nginx-konnektor-orte.inc | `/mcp` mit `proxy_read_timeout 300s` |
| engine/tests/test_schreiben.py:1353 | `test_zeitgrenzen_liegen_unter_der_des_konnektors` (ZEIT_GESAMT + ZEIT_PRUEFUNG < nginx-Grenzen und < 60) |
| engine/tests/test_schreiben.py:2235 | `test_kartenpunkte_holen_mit_erfundener_antwort` (ersetzt `overpass_abfragen` per monkeypatch) |
| werkzeuge/punkte_holen.py:72–93 | Muster: Overpass mit Wiederholung bei 429/502/503/504 (Werkzeug außerhalb des Dienstes, Frist 180 s) |
| docs/konnektor.md:36, docs/werkzeuge.md | Beschreibung des Werkzeugs |

## Existing Patterns
- Netzabrufe im Schreibweg sind selten; Ablehnungen als `Ablehnung(schluessel, …)`, Texte in `engine/texte_*.py`.
- Zeitgrenzen-Spec `docs/specs/betrieb/schreibweg-zeitgrenzen.md`: Sperre nicht blockierend (3 s), dann 429 „besetzt“.
- Tests ersetzen `overpass_abfragen` per monkeypatch; nie echte Netzaufrufe in Tests.

## Dependencies
- Upstream: Overpass-API (ODbL), `instanz.kennung()` als User-Agent, `route_stand`, `reisespeicher.exportieren` (Speicher-Reisen) bzw. Git-Arbeitskopie.
- Downstream: Konnektor `map_points_fetch` → Schreibdienst `POST /<reise>/kartenpunkte_holen`.

## Existing Specs
- `docs/specs/betrieb/schreibweg-zeitgrenzen.md`, `docs/specs/betrieb/schreibweg-speicher-347.md`
- `docs/specs/fast/abnahme-240-punkte-osm.md` (früherer Abnahme-Workflow, steht in phase5)

## Lösungsrichtungen (für die Analyse)
1. **Abruf vor der Sperre (bevorzugt):** Der Dienst liest für `kartenpunkte_holen` die Linie aus einem Lesestand ohne Sperre, ruft
   Overpass mit eigener Frist (z. B. 40 s, eine Wiederholung bei sofortigem 502/503), gibt Abfrage und Antwort intern an den Vorgang
   weiter. Der Vorgang nutzt die Antwort, wenn seine Abfrage gleich ist, sonst fragt er selbst (kurze Frist). Ein vom Client
   mitgeschicktes internes Feld muss verworfen werden.
2. Eigene größere `ZEIT_GESAMT` nur für dieses Werkzeug: einfacher, hält aber die Sperre der Reise eine Minute (andere Schreibvorgänge 429).
3. Ausweichdienst/eigener Overpass-Server: aktuell keine Ausweichinstanz erreichbar; eigener Server ist ein eigenes Vorhaben.

## Risks & Considerations
- Zeitbudget: Konnektor wartet 120 s; Abruf ≤ ~45 s + ZEIT_GESAMT + ZEIT_PRUEFUNG (28 s) bleibt darunter. Unbekannt: wie lange die
  Claude-App selbst auf ein Werkzeug wartet; die Abnahme am echten Dienst zeigt es.
- Beide Schreibwege (Speicher und Git) laufen noch (#350 offen); der Lesestand für die Linie muss für beide funktionieren.
- Die Linie kann sich zwischen Abruf und Vorgang ändern → Abfrage vergleichen.
- Last am öffentlichen Dienst: höchstens eine Wiederholung, Kennung mitsenden, Lizenzhinweis bleibt.
- Abnahme nur an eigener Testreise (`testreise-karten-225-erfunden-2027`, archiviert, Art `wasserstelle`), auch Städtewochenende.

## Analysis

### Type
Bug (Werkzeug `map_points_fetch` liefert am echten Overpass-Dienst nie Treffer: Frist 12 s gegen gemessene 33–44 s).

### Befund aus dem Code (9.11.2026)
- `kartenpunkte_holen` läuft im Unterprozess `schreiben.py anwenden` unter der Sperre der Reise, Frist `FR_SB_FRIST` = Rest von
  `ZEIT_GESAMT` (25 s). Der Netzabruf `overpass_abfragen` sitzt mitten darin, mit `OSM_ZEIT` = 12 s client- und serverseitig (`[timeout:12]`).
- Die Abfrage hängt nur an der Linie (`karte.wege[sid]` bzw. Orte von/nach aus `route_stand`, d. h. Probebau), an `osm` und `abstand_m`.
- Speicherweg: Unterprozess nutzt den Code des Dienstes. Git-Weg: Unterprozess nutzt den Code der Arbeitskopie (kann älter sein);
  ein neuer Kanal muss deshalb von altem Code gefahrlos ignoriert werden (Umgebungswert statt Feld in der Anfrage).
- Rollenprüfung (`wer_pruefen`) geschieht erst im Vorgang. Ein Abruf vorab darf erst nach derselben Prüfung ins Netz gehen
  (sonst kann eine Gast-Rolle Last am öffentlichen Dienst auslösen).
- `route_stand` ruft `plan_sicherstellen`, das in den Ordner schreiben kann: der Vorab-Abruf arbeitet in einer eigenen Kopie
  (Speicher: `reisespeicher.exportieren(reise, tmp, bis=stand_nummer)`, nur lesend; Git: Kopie von `<FR_WURZEL>/reisen/<reise>`).
- Konnektor wartet 120 s (`schreib_anfrage`), nginx `/mcp` 300 s. Der Kommentar „30 s von proxy_read_timeout“ bei `ZEIT_GESAMT` ist veraltet.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/schreiben.py | MODIFY | `kartenpunkte_abfrage(reise_dir, args)` aus `kartenpunkte_holen` herauslösen (Prüfung, Linie, bbox, Abfrage); `overpass_holen(abfrage, frist)` mit einer Wiederholung bei schnellem 429/502/503/504; `kartenpunkte_vorab(s, reise, anfrage)` vor der Sperre in `anwenden_extern` (Lesekopie, `wer_pruefen`, Abruf mit `OSM_FRIST_VORAB` ≈ 45 s, Ergebnis als Datei, Pfad im Umgebungswert `FR_OSM_VORAB`); `overpass_abfragen` nimmt die Vorab-Antwort, wenn die Abfrage gleich ist, sonst Abruf wie bisher; Overpass-Adresse über `instanz.wert("FR_OVERPASS", …)` (Tests); Kommentar der Zeitgrenzen berichtigen |
| engine/schreiben_git.py | MODIFY | `vorgang` reicht den zusätzlichen Umgebungswert an den Unterprozess weiter |
| engine/texte_*.py | MODIFY (evtl.) | nur falls eine neue Ablehnung nötig ist (z. B. „Dienst nach Wiederholung nicht erreichbar“); bestehende `schreiben.kartenpunkte.limit/.dienst` reichen voraussichtlich |
| engine/tests/test_schreiben.py | MODIFY | Vorab-Abruf: gleiche Abfrage → Unterprozess ohne Netz (FR_OVERPASS auf unerreichbare Adresse), andere Abfrage → eigener Abruf, Gast-Rolle → kein Netzabruf, schneller 502 → genau eine Wiederholung, Fehlschlag → Ablehnung ohne Sperre, Feld aus der Anfrage wird nie als Vorab-Antwort genommen, Städtewochenende (ohne Strecke) → Ablehnung wie bisher; Zeitbudget-Test: Vorab + ZEIT_GESAMT + ZEIT_PRUEFUNG < 120 s Konnektor |
| docs/specs/betrieb/schreibweg-zeitgrenzen.md | MODIFY | Vorab-Fenster für Netzabrufe beschreiben |
| docs/konnektor.md, docs/werkzeuge.md | MODIFY | Dauer (bis etwa eine Minute) und Verhalten bei Überlast |

### Scope Assessment
- Files: 5–7
- Estimated LoC: +150/-20 (davon etwa die Hälfte Tests)
- Risk Level: MEDIUM (greift in `anwenden_extern`, den gemeinsamen Einstieg aller Schreibvorgänge; Änderung bleibt auf `kartenpunkte_holen` begrenzt)

### Technical Approach
Empfehlung: Lösungsrichtung 1 „Abruf vor der Sperre“.
1. In `anwenden_extern`, nur für `kartenpunkte_holen`: Lesekopie des aktuellen Stands in einen temporären Ordner, `wer_pruefen`,
   `kartenpunkte_abfrage` → Abfrage. Scheitert die Prüfung mit einer Ablehnung, kein Vorab-Abruf (der Vorgang lehnt mit demselben
   Grund ab, maßgeblich bleibt er).
2. Abruf mit eigener Frist (≈ 45 s, serverseitig `[timeout:…]` passend), eine Wiederholung nach kurzer Pause nur bei schneller
   Antwort 429/502/503/504; Kennung als User-Agent wie bisher. Scheitert er, Ablehnung sofort, ohne die Sperre zu nehmen.
3. Ergebnis `{abfrage, antwort}` als Datei im eigenen temporären Ordner, Pfad als `FR_OSM_VORAB` an den Unterprozess (beide Wege).
   Der Unterprozess nutzt sie nur bei exakt gleicher Abfrage (Linie zwischendurch geändert → eigener Abruf mit der alten kurzen Frist).
   Ordner wird in jedem Fall gelöscht. Kein Feld der Anfrage wird je als Antwort genommen.
4. Die Sperre der Reise wird dadurch nicht länger gehalten als heute; andere Schreibvorgänge laufen während des Abrufs weiter.
Verworfen: Richtung 2 (Sperre eine Minute, andere Vorgänge bekämen 429), Richtung 3 (kein Ausweichdienst erreichbar; eigener
Overpass-Server ist ein eigenes Vorhaben).

### Dependencies
- Upstream: Overpass-API, `instanz.kennung()`, `route_stand`/`bauen.Bauer` (Probebau), `reisespeicher.exportieren`/`stand_nummer`, `wer_pruefen`.
- Downstream: Konnektor `map_points_fetch` (wartet 120 s), Claude-App (eigene Wartezeit unbekannt, Abnahme zeigt sie).
- Git-Weg (#350 offen) muss weiter funktionieren; alter Code in der Arbeitskopie ignoriert `FR_OSM_VORAB`.

### Kern (ADR-0001)
Keine KI, kein neues Merkmal, nichts Reisespezifisches; nur Zeitverhalten eines vorhandenen Werkzeugs. Beide Reisetypen: Wanderung
(Strecke mit Linie) und Städtewochenende (keine Strecke → gleiche Ablehnung wie bisher, ohne Netzabruf).

### Open Questions
- keine Produktfrage. Technisch offen, durch Abnahme zu klären: Wartet die Claude-App bis etwa 75 s auf ein Werkzeug? Wenn nicht,
  Folge-Issue (z. B. Abruf im Hintergrund mit späterer Meldung).
