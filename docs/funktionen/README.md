# Funktionen von Frieda

Was Frieda kann, steht für Nutzer:innen und Interessierte auf der Webseite jeder Frieda-Instanz: „Alle Funktionen“ unter `/info/funktionen/`, mit einer Unterseite je Bereich, auf Deutsch und Englisch, mit Bildern aus den Beispielreisen. Die Inhalte stehen nur dort (#711). Dieser Ordner bleibt als Wegweiser für Entwickler:innen: welcher Bereich wo auf der Webseite steht und welche Entwicklerdoku dazugehört.

## Bereiche

| Bereich | Webseite | Wegweiser |
|---|---|---|
| Die Reise als geprüfte Wahrheit | `/info/funktionen/wahrheit/` | [reisemodell.md](reisemodell.md) |
| Planen im Gespräch | `/info/funktionen/gespraech/` | [gespraech.md](gespraech.md) |
| Gute Gespräche mit Frieda | `/info/funktionen/gespraeche/` | [gute-gespraeche.md](gute-gespraeche.md) |
| Alternativen und Entscheidungen | `/info/funktionen/alternativen/` | [alternativen.md](alternativen.md) |
| Buchungen und Belege | `/info/funktionen/buchungen/` | [buchungen.md](buchungen.md) |
| Von der Idee bis zum Archiv | `/info/funktionen/lebenslauf/` | [lebenszyklus.md](lebenszyklus.md) |
| Reiseseite | `/info/funktionen/reiseseite/` | [reiseseite.md](reiseseite.md) |
| Karte | `/info/funktionen/karte/` | [karte.md](karte.md) |
| Zusammenarbeit | `/info/funktionen/zusammenarbeit/` | [zusammenarbeit.md](zusammenarbeit.md) |
| Packliste | `/info/funktionen/packliste/` | [packliste.md](packliste.md) |
| Bilder | `/info/funktionen/bilder/` | [bilder.md](bilder.md) |
| Erinnerungen und Meldungen | `/info/funktionen/erinnerungen/` | [erinnerungen.md](erinnerungen.md) |
| Konto und Datenschutz | `/info/funktionen/konto/` | [konto.md](konto.md) |
| Sprachen | `/info/funktionen/sprachen/` | [sprachen.md](sprachen.md) |
| Selbst betreiben | `/info/funktionen/betrieb/` | [selbst-betreiben.md](selbst-betreiben.md) |

## Eine Unterseite ändern

Ändert sich, was Nutzer:innen sehen oder tun können, wird im selben PR die Unterseite auf der Webseite nachgezogen: Texte in `engine/texte_<sprache>.py` unter `info.bereich.<name>.…` in allen Sprachen, Aufbau (Bilder, Gespräch, Siehe auch) in `INFO_UNTERSEITEN` in `engine/anmeldung.py`, neue Bilder in `engine/info/erzeugen.py`. Die Form beschreibt [Design](../design.md) („Form einer neuen Unterseite“); die Tests stehen in `engine/tests/test_funktionsseiten_711.py`.

## Siehe auch

- [Startseite der Dokumentation](../README.md)
- [Der Kern (ADR-0001)](../adr/0001-kern.md) und [Produktbild](../produkt.md) (Rollen, Status einer Reise)
- [Konnektor: alle Werkzeuge im Einzelnen](../konnektor.md)
