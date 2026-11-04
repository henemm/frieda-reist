# Context: zone-api-eigene-datei-316

## Request Summary
Die Zone `<instanz>_api` der Reise-Bausteine (Rückmeldedienst, `nginx-reise.conf`, `freischalten.sh`) steht auf dem Server noch in der
geteilten `conf.d/limit-req.conf`. Sie soll in `<instanz>-zone.conf` ziehen und im selben Zug aus der geteilten Datei verschwinden
(nginx verbietet doppelte Zonennamen). Umstellung wie bei #206: Sicherung, `nginx -t`, Rückweg, keine Handarbeit für weitere Instanzen.

## Stand auf dem Server (4.11.2026, nur gelesen)
- `/etc/nginx/conf.d/limit-req.conf` Zeile 21–23: Kommentar plus `limit_req_zone $binary_remote_addr zone=frieda_reisen_api:1m rate=30r/m;`.
  Die Datei gehört auch anderen Diensten (`mail_api`, `mcp_api`, `login` …); nur die Zeilen der Instanz dürfen weg.
- `/etc/nginx/conf.d/frieda-reisen-zone.conf` definiert `_mcp`, `_anmelden`, `_konto` mit dem Schlüssel `$frieda_reisen_schluessel` (eigene Adressen ausgenommen), `_api` fehlt.
- Eingebunden wird `conf.d/*.conf` (nicht `*.bak*`). Die Reise-Bausteine in den Snippets sind nur für root lesbar.

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/vorlagen/nginx-zone.conf | bekommt vierte Zone `__ZONE_API__` |
| betrieb/einrichten.sh | `ZONE=${ZB}_api` (Z. 32), Ersetzung `__ZONE__` (Z. 93), NOTE „zone not defined yet“ (Z. 124) |
| betrieb/nginx.py | `pruefen`/`anwenden`: Sicherung, Installation, `nginx -t`, Rückweg; kennt nur die drei eigenen Dateien |
| betrieb/freischalten.sh | setzt `__ZONE__` in den Reise-Baustein (Z. 47); unverändert |
| betrieb/vorlagen/nginx-reise.conf | `limit_req zone=__ZONE__`; Kommentar nennt schon „Zone aus nginx-zone.conf“ |
| engine/tests/test_nginx.py | Muster: `erzeugen`, Fixture `abgleich`, `_anwenden` mit Attrappen für `nginx -t`/Neuladen, echter nginx-Test |
| docs/betrieb.md | Abschnitt „nginx-Bausteine abgleichen (#206)“, letzter Absatz verspricht genau diesen Schritt |
| docs/specs/fast/nginx-vorlage-206.md | Vorgänger-Spec; „Reise-Bausteine und Zone `_api` bleiben unverändert“ fällt hier |

## Existing Patterns
- Abgleich meldet nur (`pruefen`, Ausgang 3 + ein Befehl); installiert wird ausschließlich von Hand mit `anwenden`.
- `anwenden` sichert nach `<FR_DIENST>/nginx-sicherung/<Zeit>/`, installiert, prüft `nginx -t`, lädt nur bei Erfolg, rollt sonst zurück (auch bei Strg-C).

## Risks & Considerations
- **Reihenfolge ist das Risiko:** Definition in `<instanz>-zone.conf` und Entfernen in der geteilten Datei müssen in *einem* `anwenden`-Lauf mit *einem* `nginx -t` passieren. Jeder Zwischenstand (beide definieren / keiner definiert) lässt nginx nicht starten bzw. neu laden; das Neuladen lehnt nginx dann ab, der laufende Stand bleibt, aber die Prüfung schlägt fehl.
- Die geteilte Datei gehört nicht der Instanz → nur die exakte Zeile `limit_req_zone … zone=<instanz>_api:…;` und der unmittelbar darüberstehende Kommentarblock entfernen, alles andere bleibt byte-gleich. Sicherung der geteilten Datei und Rückweg gehören in den Rollback.
- Die geteilte Datei darf nicht fest `limit-req.conf` heißen (weitere Instanzen): suchen in allen `conf.d/*.conf` außer der eigenen Zonendatei.
- Nach dem Umzug ist `pruefen` die Dauerprüfung: steht die Zone noch in einer fremden Datei, ist das eine Abweichung (Ausgang 3), sonst bleibt der Fehler unsichtbar bis zum nächsten Zonen-Konflikt.
- Schlüssel der neuen Zone: Vorschlag `$<instanz>_schluessel` wie die anderen drei (Server-Adressen zählen nicht). Verhaltensänderung für die Reise-APIs: nur eigene Adressen, Besucher unverändert.
- Beim Wechsel zählt der Zustand der Zone neu (Speicher der Zone wird beim Neuladen ohnehin neu aufgebaut) – für Besucher unsichtbar.
