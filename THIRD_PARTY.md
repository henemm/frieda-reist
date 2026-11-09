# Eingebundene Fremdbestandteile

Unter `engine/vendor/` liegen Bibliotheken und Schriften, die unverändert mitgeliefert und in die erzeugten Seiten eingebettet werden. Ihre Lizenztexte liegen jeweils daneben.

| Bestandteil | Version | Lizenz | Datei |
|---|---|---|---|
| Leaflet | 1.9.4 | BSD-2-Clause | `engine/vendor/leaflet-LICENSE` |
| protomaps-leaflet | 5.1.0 | BSD-3-Clause | `engine/vendor/protomaps-leaflet-LICENSE` |
| Pico CSS | 2.1.1 | MIT | `engine/vendor/pico-LICENSE.md` |
| Lucide Icons | 1.55.0 | ISC | `engine/vendor/lucide-1.55.0/LICENSE` |
| Source Sans 3 | – | SIL Open Font License 1.1 | `engine/vendor/fonts/source-sans-3-OFL.txt` |

Python-Pakete (`engine/requirements.txt`, nicht mitgeliefert): Markdown (BSD), PyYAML (MIT), Pillow (MIT-CMU), CairoSVG (LGPL-3.0), pytest (MIT), pyspellchecker (MIT, nur in den Tests: erkennt deutsche Wörter in englischen Texten), icalendar (BSD-2-Clause, nur in den Tests: prüft die Kalenderdateien unabhängig), pywebpush (MPL-2.0, nur im Push-Dienst `engine/push.py`; bringt py-vapid und http-ece (MPL-2.0), cryptography (Apache-2.0 oder BSD), requests (Apache-2.0) und aiohttp (Apache-2.0) mit).

Kartendaten: Grundkarten aus OpenStreetMap (© OpenStreetMap-Mitwirkende, ODbL) über Protomaps; bei automatischen Karten holt sie das Veröffentlichen (`werkzeuge/grundkarte_auto.py`). Punkte aus `kartenpunkte_holen` kommen über den Overpass-Dienst aus OpenStreetMap (ODbL) und tragen Quelle und Stand. Die Seite zeigt die Namensnennung an. Die Beispielreise enthält keine Kartendaten Dritter, ihre Tracks und Punkte sind von Hand geschätzt.

Eigener Kartendienst (optional, #444, `docs/betrieb.md`): Eine Instanz kann einen eigenen Overpass-Dienst betreiben. Overpass API steht unter der GNU Affero General Public License (AGPL); das Docker-Image `wiktorn/overpass-api` wird nicht mitgeliefert, sondern auf dem Server geladen und per Digest gepinnt (`betrieb/gemeinsam.sh`). Die eingespielten Regionsauszüge (Geofabrik) sind Daten aus OpenStreetMap (© OpenStreetMap-Mitwirkende, ODbL, Namensnennung in jedem Treffer).
