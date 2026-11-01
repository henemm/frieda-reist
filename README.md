# Frieda Reist

*English summary: [README.en.md](README.en.md).*

**AI-first-Reiseplanung und Reisehandbuch.** Frieda hält eine Reise als strukturierte Wahrheit (Reise-Ontologie): Tage, Aufenthalte, Bewegungen, Orte, Alternativen mit Entscheidungsverlauf und Wissen, jede Stelle mit fester ID, jede Angabe mit Herkunft und Prüfdatum. Alles Unstrukturierte (Gespräch, Recherche, Abwägen) passiert im AI-Client der Reisenden (Claude Desktop oder Handy), der über einen MCP-Konnektor liest und strukturiert zurückschreibt. Ein Generator baut daraus eine Reiseseite, die offline funktioniert. Der Kern steht in [`docs/adr/0001-kern.md`](docs/adr/0001-kern.md).

**Was Frieda anders macht:** Die Herkunft jeder Angabe wird beim Schreiben erzwungen, nicht nachträglich erbeten. Der Konnektor nimmt keinen Wert ohne Quelle an, Veränderliches nur mit Prüfdatum, Entscheidungen nur von Organisator:innen mit Person, Datum und Grund. Frieda enthält keine eigene KI: Sie prüft Regeln, hält die Wahrheit und zeigt sie; recherchiert, abgewogen und formuliert wird im AI-Client der Reisenden. Welche Arten von Dingen und welche Merkmale eine Reise kennt (Refugi, Ryokan, Zeitfenster-Ticket, Vorbestellung), legt jede Reise selbst im Gespräch fest; die Software liefert keinen Katalog.

*A travel planner and handbook, AI first: a trip lives as a structured ontology in Git (days, stays, movements, places, choices with a decision log, knowledge), every statement with its source and check date. The travellers' own AI client (Claude Desktop or mobile) reads and writes it through an MCP connector; Frieda itself contains no AI, it enforces the rules: no value without a source, no decision without a named organiser. A generator builds an offline-capable web handbook. The page and the connector speak German and English (further languages: one file each, `docs/sprachen.md`); the detailed documentation is in German, a short English summary is in [README.en.md](README.en.md).*

## Was es kann

- **Tagesplan, Etappen, Orte, Unterkünfte** mit festen IDs (T-, E-, O-, U-, W- …), damit sich jede Rückmeldung genau zuordnen lässt.
- **Alternativen im Modell:** Wahlstellen mit Optionen auf jeder Ebene, benannte Pläne mit Summen (Gehzeit, Strecke, Höhenmeter, Nächte je Art) und ein Verlauf. Verworfenes wird nie gelöscht, entscheiden dürfen nur Organisator:innen.
- **Arten und Merkmale je Reise:** Hotel, Refugi, Ryokan, Nachtfähre, Museum und was dazu bekannt sein muss, stehen in `plan/arten.yaml` der Reise, entwickelt im Gespräch; die Seite nimmt Name, Farbe und Symbol daraus (`docs/ontologie.md`).
- **Quellen und Prüfdaten:** Fußnoten mit Titel, Link und Datum; Merkmale wie Preise tragen ein Prüfdatum.
- **Offline:** Die Seite ist eine PWA mit Vorab-Speicher, Update-Hinweis und Ausgang für Rückmeldungen ohne Netz. Karten mit nummerierten Orten (Leaflet, optional OpenStreetMap-Vektorkarten als PMTiles).
- **Mitreisende:** Rückmeldungen, Wünsche und Aufgaben zu jeder ID, über die Seite oder über die Claude-App (MCP-Konnektor). Personen haben Rollen: `gast` (lesen), `mitwirkend` (Eingaben) und `organisator` (entscheiden).
- **Der Konnektor schreibt direkt:** Was im Gespräch festgelegt wird (Werte, Dinge, Optionen, Entscheidungen, Fragen, Wissen, Personen, Status), prüft der Schreibweg nach den Regeln der Reise und sichert es sofort mit Person und Herkunft ins Repo; wenige Minuten später ist es auf der Seite. Rückmeldungen von der Seite arbeitet eine Organisator:in im Gespräch ein, der Status geht an den Absender zurück.

## Ausprobieren

```
python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt
engine/.venv/bin/python engine/bauen.py --reisen beispiel/reisen --ziel dist beispielreise
python3 -m http.server -d dist 8000      # dann http://localhost:8000/beispielreise/
```

Die Beispielreise „Malerweg in vier Tagen“ ist erfunden (siehe `beispiel/README.md`).

## Eigene Reisen

Eigene Reisen gehören in ein eigenes, gern privates Repo, das dieses als Submodul einbindet. Der Generator sucht die Reisen standardmäßig in `./reisen/` des aktuellen Ordners:

```
mein-reisen-repo/
  frieda/          dieses Repo als Submodul
  engine -> frieda/engine
  reisen/<reise>/  reise.yaml, reise.json, plan/routen.yaml, inhalt/, medien/
```

Aufbau einer Reise: `beispiel/reisen/beispielreise/`, Modell in `engine/routen.py` und `engine/reise.py`, Reise-Ontologie (Grundformen, Arten und Merkmale je Reise) in `docs/ontologie.md`, Produktbild in `docs/produkt.md`, Alternativen in `docs/alternativen.md`, Design und Bausteine in `docs/design.md`, Claude-App in `docs/konnektor.md`, neue Reise anlegen in `docs/neue-reise.md`, Sprachen und eine neue Sprache hinzufügen in `docs/sprachen.md`.

## Auf dem eigenen Server

Seiten ausliefern, Rückmeldungen annehmen, was der AI-Client über den Konnektor festlegt sofort in die Reise schreiben und veröffentlichen: `betrieb/` mit Anleitung in `docs/betrieb.md`. Auf dem Server läuft keine KI (`docs/adr/0001-kern.md`). Eine Reisegruppe mit eigenem Betreiber ist eine Instanz (ein Reisen-Repo, eigene Ordner und Dienste); ihre Werte stehen in `betrieb/einstellungen.env` des Reisen-Repos, die Skripte kennen keine Instanz. Grundkarten und Punkte aus OpenStreetMap holen die Werkzeuge in `werkzeuge/` (`docs/werkzeuge.md`).

## Tests

```
engine/.venv/bin/python -m pytest -q engine/tests
```

Die Browser-Prüfung der Offline-Fähigkeit braucht Playwright (`PLAYWRIGHT_MODUL=<pfad>/playwright/index.mjs`), sonst wird sie übersprungen.

## Lizenz

GNU Affero General Public License v3.0 (siehe `LICENSE`). Wer die Software als Online-Dienst anbietet, muss den geänderten Quellcode ebenfalls zugänglich machen. Eingebundene Bibliotheken und Schriften stehen unter ihren eigenen Lizenzen, siehe `THIRD_PARTY.md`.
