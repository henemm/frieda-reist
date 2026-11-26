# Frieda Reist

*English summary: [README.en.md](README.en.md).*

**AI-first-Reiseplanung und Reisehandbuch.** Frieda hält eine Reise als strukturierte Wahrheit (Reise-Ontologie): Tage, Aufenthalte, Bewegungen, Orte, Alternativen mit Entscheidungsverlauf und Wissen, jede Stelle mit fester ID, jede Angabe mit Herkunft und Prüfdatum. Alles Unstrukturierte (Gespräch, Recherche, Abwägen) passiert im AI-Client der Reisenden (Claude Desktop oder Handy), der über einen MCP-Konnektor liest und strukturiert zurückschreibt. Ein Generator baut daraus eine Reiseseite, die offline funktioniert. Der Kern steht in [`docs/adr/0001-kern.md`](docs/adr/0001-kern.md).

**Was Frieda anders macht:** Die Herkunft jeder Angabe wird beim Schreiben erzwungen, nicht nachträglich erbeten. Der Konnektor nimmt keinen Wert ohne Quelle an, Veränderliches nur mit Prüfdatum, Entscheidungen nur von Organisator:innen mit Person, Datum und Grund. Frieda enthält keine eigene KI: Sie prüft Regeln, hält die Wahrheit und zeigt sie; recherchiert, abgewogen und formuliert wird im AI-Client der Reisenden. Welche Arten von Dingen und welche Merkmale eine Reise kennt (Refugi, Ryokan, Zeitfenster-Ticket, Vorbestellung), legt jede Reise selbst im Gespräch fest; die Software liefert keinen Katalog.

*A travel planner and handbook, AI first: a trip lives as a structured ontology (days, stays, movements, places, choices with a decision log, knowledge), every statement with its source and check date. The travellers' own AI client (Claude Desktop or mobile) reads and writes it through an MCP connector; Frieda itself contains no AI, it enforces the rules: no value without a source, no decision without a named organiser. A generator builds an offline-capable web handbook. The page and the connector speak German and English (further languages: one file each, `docs/sprachen.md`); the detailed documentation is in German, a short English summary is in [README.en.md](README.en.md).*

## Was es kann

Alle Funktionen mit Beispielen und Bildern stehen auf der Webseite jeder Frieda-Instanz unter „Alle Funktionen“ (`/info/funktionen/`), eine Seite je Bereich, auf Deutsch und Englisch: vom Reisemodell und dem Planen im Gespräch über Reiseseite, Alternativen, Buchungen, Karte, Zusammenarbeit, Packliste, Bilder und Erinnerungen bis zu Konto, Sprachen und dem Betrieb auf einem eigenen Server. Für Entwickler:innen: [Wegweiser zu den Bereichen](docs/funktionen/README.md) und die ganze Dokumentation unter [docs/](docs/README.md).

## Ausprobieren

```
python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt
engine/.venv/bin/python engine/bauen.py --reisen beispiel/reisen --ziel dist beispielreise
python3 -m http.server -d dist 8000      # dann http://localhost:8000/beispielreise/
```

Die Beispielreise „Malerweg in vier Tagen“ ist erfunden (siehe `beispiel/README.md`).

## Eigene Reisen

Im Betrieb entsteht eine Reise im Gespräch: Wer Reisen anlegen darf, sagt der Claude-App „Leg eine neue Reise an …“, und Frieda legt sie im Reisespeicher der Instanz an ([Neue Reise anlegen](docs/neue-reise.md)). Von da an wächst sie im Gespräch.

Zum Ausprobieren ohne Server baut der Generator Reisen aus Ordnern, standardmäßig aus `./reisen/` des aktuellen Ordners (`--reisen`, `--ziel` zum Ändern). Aufbau einer Reise: `beispiel/reisen/beispielreise/` (Wanderung) und `beispiel/reisen/stadtwochenende/` (Wochenende ohne Wanderung), `reise.yaml`, `reise.json`, `plan/routen.yaml`, `plan/arten.yaml`, `inhalt/`, `medien/`. Das Modell beschreibt die [Reise-Ontologie](docs/ontologie.md).

## Auf dem eigenen Server

Seiten ausliefern, Rückmeldungen annehmen, was der AI-Client über den Konnektor festlegt sofort in den Reisespeicher schreiben und veröffentlichen: `betrieb/` mit Anleitung in [`docs/betrieb.md`](docs/betrieb.md). Auf dem Server läuft keine KI (`docs/adr/0001-kern.md`). Eine Reisegruppe mit eigenem Betreiber ist eine Instanz (eigene Ordner, Dienste und Adresse; die Software kommt direkt aus diesem Repo); ihre Werte stehen unter `<FR_DIENST>/instanz/` in `einstellungen.env`, die Skripte kennen keine Instanz. Grundkarten und Punkte aus OpenStreetMap holen die Werkzeuge in `werkzeuge/` (`docs/werkzeuge.md`).

## Tests

```
engine/.venv/bin/python -m pytest -q engine/tests
```

Die Browser-Prüfung der Offline-Fähigkeit braucht Playwright (`PLAYWRIGHT_MODUL=<pfad>/playwright/index.mjs`), sonst wird sie übersprungen.

## Lizenz

GNU Affero General Public License v3.0 (siehe `LICENSE`). Wer die Software als Online-Dienst anbietet, muss den geänderten Quellcode ebenfalls zugänglich machen. Eingebundene Bibliotheken und Schriften stehen unter ihren eigenen Lizenzen, siehe `THIRD_PARTY.md`.
