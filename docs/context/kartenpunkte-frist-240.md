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
