# Context: feat-444-eigener-kartendienst

## Request Summary
Das Werkzeug `map_points_fetch` (#240) soll Punkte aus OpenStreetMap von einem eigenen Overpass-Dienst der Instanz holen, der nur bei Bedarf läuft (Container, Start beim Aufruf, Stopp nach Ruhe), nur die benötigten Regionen enthält und dessen Adresse aus den Einstellungen der Instanz kommt. Der öffentliche Dienst bleibt Reserve. Danach Abnahme #240 am eigenen Dienst.

## Messungen (9.11.2026, Testaufbau außerhalb des Repos)
- Image `wiktorn/overpass-api`, Balearen-Auszug (50 MB pbf von openstreetmap.fr), Einspielen im Modus `init`: Datenbank 2,0 GB, Speicher rund 1,6 GiB (Limit 2 GiB). Vorverarbeitung pbf → osm.bz2 mit osmium nötig (`OVERPASS_PLANET_PREPROCESS`).
- Modus normal: Kaltstart bis zur ersten gültigen Antwort 2,0 s; Abfrage Punkt-Umkreis 0,09 s, längs Wegen 0,24 s; Speicher 70 MiB.
- Stolpersteine: Datenordner braucht Rechte 755 (sonst `Permission denied …osm3s_osm_base`); `/api/status` liefert 502 (Absturz im Image), Bereitschaft nur über echte Abfrage prüfbar.
- Öffentlicher Dienst vom Server aus: 502 oder 30–45 s (#240, Kommentare 8./9.11.).

## Related Files
| File | Relevance |
|------|-----------|
| engine/schreiben.py:2020-2069 | `OVERPASS`-Vorgabe, `overpass_holen` (liest `FR_OVERPASS` über `instanz.wert`, Fristen, eine Wiederholung bei 429/502/503/504), `overpass_abfragen` (Vorab-Datei `FR_OSM_VORAB`) |
| engine/schreiben.py:2267, 5083, 5130 | Aufruf in `kartenpunkte_holen`, Abruf vor der Sperre mit `OSM_FRIST_VORAB` |
| engine/instanz.py:36-90 | Einstellungen der Instanz: nur `FR_`-Namen, `wert(name, vorgabe)`, Umgebung vor Datei |
| betrieb/einstellungen.beispiel | Doku der Einstellungen; `FR_OVERPASS` fehlt dort noch |
| docs/betrieb.md (~201, 233, 331) | Doku Einstellungen und Einheiten; `FR_OVERPASS` fehlt |
| docs/werkzeuge.md:27 | einzige Doku von `FR_OVERPASS` |
| betrieb/einrichten.sh:90-135 | erzeugt Einheiten aus `betrieb/vorlagen/*.service|*.timer` mit Platzhaltern, gibt Aktivierungsbefehle aus |
| betrieb/units.py:26-35, betrieb/vorlagen/units-installieren.py:25-38 | Einheiten-Abgleich (#260): feste `ARTEN` (6 Dienste), `ERLAUBT`-Liste; neue Einheiten werden nur gemeldet, nie automatisch installiert |
| engine/tests/test_units_helfer.py:57-66, test_units.py:52,115 | prüfen feste Menge der Einheiten |
| engine/tests/test_betrieb.py:2091 | keine echten Domains in `betrieb/` |
| werkzeuge/punkte_holen.py:44, werkzeuge/wasser_pruefen.py:35 | Overpass-Adresse fest, ohne `FR_OVERPASS` |
| engine/tests/test_schreiben.py:2235, 2421-2645, 2822-2839 | Overpass-Stummel (lokaler HTTP-Server), Fixture setzt `FR_OVERPASS`; Test der Vorgabe overpass-api.de |
| docs/specs/betrieb/kartenpunkte-frist-240.md | Spec der Fristen (#240) |

## Existing Patterns
- Einstellungen: `instanz.wert("FR_…", vorgabe)`, dokumentiert in `einstellungen.beispiel` (auskommentiert mit Vorgabe) und `docs/betrieb.md`.
- Dienste der Instanz: Vorlagen in `betrieb/vorlagen/`, Platzhalter `__…__`, `einrichten.sh` erzeugt und gibt die einmaligen `sudo`-Befehle aus.
- Externe Dienste in Tests: lokaler Stummel-Server, Adresse über Umgebung.
- Kein Docker im Repo bisher.

## Dependencies
- Upstream: Docker auf dem Server (Version 29.9.1, Benutzer in Gruppe `docker`), Image `wiktorn/overpass-api` (AGPL/MIT-Bestandteile, Lizenz prüfen → THIRD_PARTY.md, falls es als Fremdbestandteil gilt), Regionsauszüge (Geofabrik oder openstreetmap.fr, ODbL), systemd (`systemd-socket-proxyd`).
- Downstream: `map_points_fetch` (Schreibweg), Werkzeuge `punkte_holen`, `wasser_pruefen`.

## Existing Specs
- `docs/specs/betrieb/kartenpunkte-frist-240.md`

## Risks & Considerations
- **Abdeckung:** Eine Abfrage außerhalb der eingespielten Regionen liefert beim eigenen Dienst eine leere, gültige Antwort, nicht einen Fehler. Die Software muss wissen, welche Fläche der eigene Dienst abdeckt (z. B. Umriss je Region beim Einspielen ablegen), sonst gilt „keine Treffer“ fälschlich als Ergebnis. Außerhalb: öffentlicher Dienst.
- **Reserve:** Fehler oder Zeitüberschreitung des eigenen Dienstes → öffentlicher Dienst, innerhalb derselben Gesamtfrist.
- **Instanzneutral:** Regionen, Port, Datenordner, Speichergrenze kommen aus `einstellungen.env`; nichts Mallorca-spezifisches in `betrieb/` oder Engine. Keine echten Domains in `betrieb/` (Test).
- **Einheiten-Abgleich:** Neue Einheiten (Socket, Proxy, Container) kennt der Abgleich (#260) nicht; sie gehören wie die übrigen in die einmalige Einrichtung. Prüfen, ob `units.py`/Hilfsprogramm sie melden würden (Lärm, vgl. #445) → bewusst in die Liste aufnehmen oder als optionaler Baustein ausnehmen.
- **Start bei Bedarf:** `systemd-socket-proxyd --exit-idle-time` beendet nur den Proxy; der Container muss über `StopWhenUnneeded=` / `BindsTo=` mit dem Proxy enden. Erste Abfrage nach Kaltstart: 2 s plus Wartezeit, bis der Container lauscht (Proxy verbindet sofort → `ExecStartPost` mit Bereitschaftsprüfung über echte Abfrage).
- **Aktualität:** Daten veralten; Neu-Einspielen je Region (Minuten) periodisch oder bei Bedarf; Stand (`timestamp_osm_base`) als „Stand“ der Treffer nennen statt Abrufdatum allein.
- **Speicher:** Einspielen braucht ~1,6 GiB je kleiner Region; Server hat 8 GB, stark belegt (Swap). Einspielen nicht parallel zu Software-Prüfungen.
- **Platte:** 2 GB je Balearen-Größe; 50 GB frei.
- **Rechte:** Datenordner 755, Container ohne Netz nach außen nötig? (nur Einspielen braucht Download, Abfragen nicht).
- **Lizenz:** ODbL-Hinweis bleibt in den Treffern (Quelle).
