# Werkzeuge für Inhalte

Die Werkzeuge unter `werkzeuge/` holen Daten aus dem Netz und legen sie als Dateien in die Reise. Der Generator liest später nur diese Dateien und holt selbst nie etwas aus dem Netz. Alle brauchen Internet, laufen also auf dem Server oder einem eigenen Rechner, nicht in einer Cloud-Sitzung ohne Netz. Aufgerufen werden sie in der Wurzel des Reisen-Repos (oder mit `FR_WURZEL`).

Gegenüber OpenStreetMap melden sich die Werkzeuge mit `FR_KENNUNG` aus den Einstellungen der Instanz (`betrieb/einstellungen.env`, `docs/betrieb.md`). Die Nutzungsregeln von Nominatim und Overpass verlangen dabei eine Kontaktangabe, etwa `Meine-Reisen/1 (betrieb@example.org)`. Ohne Angabe nennen die Werkzeuge nur die Software.

## Offline-Grundkarte (PMTiles)

1. `frieda/werkzeuge/karte-holen.sh <reise>`: Holt das Werkzeug `pmtiles` einmalig nach `engine/.bin/`. Dann schneidet es aus dem neuesten Protomaps-Tagesbuild den Kartenrahmen aus `plan/karte.yaml` bis Zoom 15 aus. Ergebnis: `reisen/<reise>/medien/karte/grundkarte.pmtiles`, dazu `….quelle.txt` mit der Herkunft. Die Datei kommt nicht ins Repo (`.gitignore`).
2. Veröffentlichen (`frieda/betrieb/deploy.sh <reise>` oder der nächste Lauf des Timers). Fehlt die Grundkarte, meldet das Bauen „Grundkarte … fehlt“, und die Karte bleibt schematisch.
3. Telefon: Die Karte wird bei der Installation bzw. beim nächsten Update ganz geladen, das sind einige 10 MB; am besten im WLAN. Kleiner wird sie mit `MAXZOOM=14 frieda/werkzeuge/karte-holen.sh <reise>`.
4. Nur bei Bedarf auffrischen, etwa kurz vor der Reise: Jede neue Datei heißt für das Telefon einen neuen Download.

Regionale Karten der Recherche: `frieda/werkzeuge/karte-holen.sh <reise> <name>` nimmt Rahmen und Zoom aus `grundkarten.<name>` der Punkte-Datei (`reise.json` → `wissen_punkte`) und schreibt `medien/karte/<name>.pmtiles`.

## Punkte der Etappen-Karten

1. `engine/.venv/bin/python frieda/werkzeuge/punkte_holen.py <reise>` liest zuerst die GPX-Wegpunkte der Tracks. Ihre Nummern verbinden sie mit der Kurzliste im Etappentext. Danach fragt es OpenStreetMap einmal über den Kartenrahmen ab: Einkehr, Wasser, Bus und Notfall, Unterkünfte. Ergebnis: `reisen/<reise>/plan/punkte.yaml`, ein Punkt je Zeile mit Quelle und Stand.
2. Die Datei durchsehen (Zuordnung zu U-IDs, Namen), dann einchecken. Namen aus dem Text, die das Werkzeug nicht gefunden hat, nennt es am Ende; die bekommen keine geschätzte Lage. Von Hand ergänzte Punkte (`von_hand: true`) bleiben beim Auffrischen erhalten.
3. Der Bau liest nur diese Datei und verknüpft die erste Nennung je Block im Etappentext mit der Karte.

## Punkte der Recherche

`engine/.venv/bin/python frieda/werkzeuge/wissen_punkte_holen.py <reise> [--neu] [--rahmen]` sucht für die Punkte der Recherche (`reise.json` → `wissen_punkte`) Koordinaten bei Nominatim. Die Suche bleibt auf das Gebiet des Punkts begrenzt. Was nicht gefunden wird, bleibt ohne Lage. Die Sprachen der Namen bestimmt `FR_SPRACHEN` (Vorgabe `de,en`).

## Adressen der Unterkünfte

`engine/.venv/bin/python frieda/werkzeuge/adressen_holen.py <reise> [--suchen] [--trocken]` füllt die Lage der Unterkünfte vor (ADR-0004). Für Unterkünfte ohne Adresse, die in `plan/punkte.yaml` einen OSM-Punkt mit ihrer ID haben, holt es die Adress-Tags über Overpass. Mit `--suchen` fragt es für die übrigen Nominatim nach „Name, Ort“, begrenzt auf 3 km um den Ort aus `plan/karte.yaml`, und übernimmt nur Treffer, die eine Unterkunft mit Straße sind (dann auch die Koordinaten). Jede Adresse bekommt Quelle und Prüfdatum; was nichts liefert, nennt das Skript am Ende, ohne zu schätzen. `--trocken` zeigt nur an. Danach `plan/routen.yaml` durchsehen und einchecken; den Rest trägt Frieda im Gespräch ein (`lage_eintragen`).

## Wasserstellen prüfen

`engine/.venv/bin/python frieda/werkzeuge/wasser_pruefen.py <reise>` holt die OSM-Wasserpunkte aus `plan/punkte.yaml` noch einmal mit allen Tags: Trinkwasser, saisonal, zeitweise, Zugang, Prüfdatum, Hinweise. Danach stuft es sie ein: gut belegt, mit Vorbehalt, unsicher. Das Ergebnis steht zur Durchsicht in `inhalt/recherche/wasserstellen-osm.md`; `punkte.yaml` bleibt unverändert. Die Einstufung beschreibt die Datenlage, nicht den Zustand vor Ort.

## Seiten vor und nach einer Änderung vergleichen

Wer die Vorlage oder den Generator umbaut, will wissen, ob sich der Inhalt der Seite dabei ändert. `node frieda/werkzeuge/seitenvergleich/dump.mjs <Adresse der Seite> vorher.json` rendert jede Route der Seite bei 390 und 1200 px Breite und speichert das DOM (Playwright als Paket `playwright`, sonst `PLAYWRIGHT=<Pfad zu index.mjs>`). Nach der Änderung mit `nachher.json` wiederholen und `python3 frieda/werkzeuge/seitenvergleich/vergleich.py vorher.json nachher.json` aufrufen: Es nennt die abweichenden Routen mit der ersten Stelle des Unterschieds.
