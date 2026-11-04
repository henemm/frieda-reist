# Mini-Spec: zone-api-eigene-datei-316

Issue #316 (Folge von #206/#260). Vorbereitung, noch nicht freigegeben. Der Eingriff am Live-Server (`anwenden` auf dem Server) braucht
wie bei #206 die Freigabe des Product Owners.

## Was ändert sich

- `betrieb/vorlagen/nginx-zone.conf`: vierte Zone `limit_req_zone $__SCHLUESSEL__ zone=__ZONE_API__:1m rate=30r/m;` (Rückmeldedienst der Reise-Seiten).
- `betrieb/einrichten.sh`: `__ZONE_API__` ersetzen (= bisheriges `ZONE`), den Hinweis „zone not defined yet“ streichen.
- `betrieb/nginx.py`:
  - Neuer Befund: Die Zone `<instanz>_api` ist in einer **anderen** `conf.d/*.conf` definiert. `pruefen` meldet das als Abweichung (Ausgang 3, derselbe Befehl).
  - `anwenden` entfernt in demselben Lauf aus dieser Datei genau die Definition (Zeile `limit_req_zone … zone=<instanz>_api:…;` samt dem unmittelbar darüberstehenden Kommentarblock). Alles andere bleibt unverändert.
  - Sicherung der fremden Datei im selben Ordner wie die übrigen; ein `nginx -t` über beide Änderungen; Rückweg stellt auch sie wieder her (auch bei Abbruch von Hand).
  - Eine fremde Datei, die die Zone mehr als einmal oder in einer Form definiert, die nicht eindeutig erkannt wird (Zeile mit weiteren Direktiven, Zone in `include`-Datei), wird nicht angefasst: Fehler mit Datei und Zeile, nichts geändert.
- `docs/betrieb.md`: Absatz „Einmalige Umstellung“ (Zone `_api` bleibt in der gemeinsamen Datei) ersetzen durch die neue Regel; Zonen-Liste um `_api` ergänzen.

## Was darf sich nicht ändern

- `nginx-reise.conf`, `freischalten.sh`, der Name `<instanz>_api` (bestehende Reise-Bausteine auf dem Server laden weiter).
- Alle übrigen Zeilen der geteilten Datei, Rechte und Besitzer der Dateien (Zone 644, Bausteine 640).
- Nichts am Server in diesem Schritt; die Umstellung des Live-Servers ist ein eigener, bewusster Schritt.

## Acceptance Criteria

- AC-1: Die erzeugte Zonendatei enthält `<instanz>_api` (1m, 30r/m, Schlüssel der Instanz); `einrichten.sh` meldet keine fehlende Zone mehr.
- AC-2: Steht die Zone in einer fremden `conf.d`-Datei, meldet `pruefen` Abweichung (Ausgang 3) mit Dateiname; steht sie nirgends sonst, ist die Instanz gleich (0).
- AC-3: `anwenden` bringt Zonendatei und fremde Datei in einem Lauf in den Sollstand; die fremde Datei verliert nur die Zone der Instanz (Vergleich Zeile für Zeile), Rechte bleiben.
- AC-4: Mit echtem nginx: vorher (Zone nur in der geteilten Datei) und nachher (nur in der eigenen) besteht `nginx -t`; ein Zwischenstand mit doppelter Zone wird nie neu geladen.
- AC-5: Besteht `nginx -t` nicht oder bricht der Lauf ab, sind beide Dateien wie vorher (Inhalt und Rechte).
- AC-6: Zweiter Lauf: „nothing to do“. Eine Instanz, bei der die Zone nie in einer geteilten Datei stand, wird unverändert eingerichtet.
- AC-7: Eine fremde Datei mit mehrdeutiger Definition wird nicht verändert, der Lauf endet mit 1.
- AC-8: Gesamte Tests grün (`engine/.venv/bin/python -m pytest -q engine/tests`).

## Manuelle Test-Schritte (Live, erst nach Freigabe)

1. `nginx.py pruefen`: Abweichung 3, nennt `limit-req.conf` und `frieda-reisen-zone.conf`.
2. Befehl aus der Meldung ausführen; Ausgabe „installed, nginx tested and reloaded.“
3. `/gesund`, `/mcp`, eine Reise-Seite mit `api/`-Aufruf; `nginx.py pruefen` endet mit 0; Sicherung unter `_dienst/nginx-sicherung/` liegt vor.

## Inline-Test

- [ ] `test_nginx.py`: AC-1 bis AC-7 mit Attrappen für `nginx -t`/Neuladen; AC-4 mit dem echten nginx wie `test_nginx_laedt_die_zonen_…`.
