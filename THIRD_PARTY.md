# Eingebundene Fremdbestandteile

Unter `engine/vendor/` liegen Bibliotheken und Schriften, die unverändert mitgeliefert und in die erzeugten Seiten eingebettet werden. Ihre Lizenztexte liegen jeweils daneben.

| Bestandteil | Version | Lizenz | Datei |
|---|---|---|---|
| Leaflet | 1.9.4 | BSD-2-Clause | `engine/vendor/leaflet-LICENSE` |
| protomaps-leaflet | 5.1.0 | BSD-3-Clause | `engine/vendor/protomaps-leaflet-LICENSE` |
| Pico CSS | 2.1.1 | MIT | `engine/vendor/pico-LICENSE.md` |
| Lucide Icons | 1.55.0 | ISC | `engine/vendor/lucide-1.55.0/LICENSE` |
| markdown-it | 14.1.0 | MIT | `engine/vendor/markdown-it-LICENSE` (zeigt Langtexte auf der Seite, #594) |
| Source Sans 3 | – | SIL Open Font License 1.1 | `engine/vendor/fonts/source-sans-3-OFL.txt` |

Python-Pakete (`engine/requirements.txt`, nicht mitgeliefert): Markdown (BSD), nh3 (MIT, säubert das HTML der Reisetexte; bringt die Rust-Bibliothek ammonia mit, MIT oder Apache-2.0), PyYAML (MIT), Pillow (MIT-CMU), CairoSVG (LGPL-3.0), pytest (MIT), pyspellchecker (MIT, nur in den Tests: erkennt deutsche Wörter in englischen Texten), icalendar (BSD-2-Clause, nur in den Tests: prüft die Kalenderdateien unabhängig), pywebpush (MPL-2.0, nur im Push-Dienst `engine/push.py`; bringt py-vapid und http-ece (MPL-2.0), cryptography (Apache-2.0 oder BSD), requests (Apache-2.0) und aiohttp (Apache-2.0) mit).

Kartendaten: Grundkarten aus OpenStreetMap (© OpenStreetMap-Mitwirkende, ODbL) über Protomaps; bei automatischen Karten holt sie das Veröffentlichen (`werkzeuge/grundkarte_auto.py`). Punkte aus `kartenpunkte_holen` kommen über den Overpass-Dienst aus OpenStreetMap (ODbL) und tragen Quelle und Stand. Die Seite zeigt die Namensnennung an. Die Beispielreise enthält keine Kartendaten Dritter, ihre Tracks und Punkte sind von Hand geschätzt.

Bilder der Beispielreise (`beispiel/reisen/beispielreise/medien/bilder/`, #455): acht freie Bilder aus Wikimedia Commons als Beispielwerte (die Reise ist erfunden, die Bilder zeigen die echte Gegend), von Frieda selbst geholt und als WebP-Fassungen (480 und 1600 px) abgelegt; Urheber und Lizenz stehen auch in `plan/bilder.yaml` der Reise und erscheinen auf der Seite unter dem Bild. Die Skizze `skizze-felsen.png` (BI-01) ist eine eigene Zeichnung.

| Bild | Datei auf Commons | Urheber | Lizenz | Seite |
|---|---|---|---|---|
| BI-02 (Titelbild) | Nationalpark Sächsische Schweiz 20260906 Schrammsteine 01.jpg | NutzerAusBerlin | CC0 | https://commons.wikimedia.org/wiki/File:Nationalpark_S%C3%A4chsische_Schweiz_20260906_Schrammsteine_01.jpg |
| BI-03 | Basteibrücke 01.jpg | John Samuel | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0) | https://commons.wikimedia.org/wiki/File:Basteibr%C3%BCcke_01.jpg |
| BI-04 (Ort Hohnstein, Beispielwert) | 20081018800DR Hohnstein (Sächsische Schweiz).jpg | Jörg Blobelt | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0) | https://commons.wikimedia.org/wiki/File:20081018800DR_Hohnstein_(S%C3%A4chsische_Schweiz).jpg |
| BI-05 (Ort Hohnstein, Beispielwert) | Burg Hohnstein (Juni 2026) 3.jpg | Romzig | CC0 | https://commons.wikimedia.org/wiki/File:Burg_Hohnstein_(Juni_2026)_3.jpg |
| BI-06 (Ort Hohnstein, Beispielwert) | Burg Hohnstein (Juni 2026) 6.jpg | Romzig | CC0 | https://commons.wikimedia.org/wiki/File:Burg_Hohnstein_(Juni_2026)_6.jpg |
| BI-07 (Tag 2, Beispielwert) | Amselgrund Hohnstein.jpg | Lukas Beck | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0) | https://commons.wikimedia.org/wiki/File:Amselgrund_Hohnstein.jpg |
| BI-08 (Etappe 2, Beispielwert) | Brandaussicht (Juni 2026) 1.jpg | Romzig | CC0 | https://commons.wikimedia.org/wiki/File:Brandaussicht_(Juni_2026)_1.jpg |
| BI-09 (Unterkunft der ersten Nacht, Beispielwert) | 20040711620DR Dresden Terrassenufer Brühlsche Terrasse.jpg | Jörg Blobelt | CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0) | https://commons.wikimedia.org/wiki/File:20040711620DR_Dresden_Terrassenufer_Br%C3%BChlsche_Terrasse.jpg |

Eigener Kartendienst (optional, #444, `docs/betrieb.md`): Eine Instanz kann einen eigenen Overpass-Dienst betreiben. Overpass API steht unter der GNU Affero General Public License (AGPL); das Docker-Image `wiktorn/overpass-api` wird nicht mitgeliefert, sondern auf dem Server geladen und per Digest gepinnt (`betrieb/gemeinsam.sh`). Die eingespielten Regionsauszüge (Geofabrik) sind Daten aus OpenStreetMap (© OpenStreetMap-Mitwirkende, ODbL, Namensnennung in jedem Treffer).
