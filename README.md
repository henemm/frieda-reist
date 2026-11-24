# Frieda Reist

*English summary: [README.en.md](README.en.md).*

**AI-first-Reiseplanung und Reisehandbuch.** Frieda hält eine Reise als strukturierte Wahrheit (Reise-Ontologie): Tage, Aufenthalte, Bewegungen, Orte, Alternativen mit Entscheidungsverlauf und Wissen, jede Stelle mit fester ID, jede Angabe mit Herkunft und Prüfdatum. Alles Unstrukturierte (Gespräch, Recherche, Abwägen) passiert im AI-Client der Reisenden (Claude Desktop oder Handy), der über einen MCP-Konnektor liest und strukturiert zurückschreibt. Ein Generator baut daraus eine Reiseseite, die offline funktioniert. Der Kern steht in [`docs/adr/0001-kern.md`](docs/adr/0001-kern.md).

**Was Frieda anders macht:** Die Herkunft jeder Angabe wird beim Schreiben erzwungen, nicht nachträglich erbeten. Der Konnektor nimmt keinen Wert ohne Quelle an, Veränderliches nur mit Prüfdatum, Entscheidungen nur von Organisator:innen mit Person, Datum und Grund. Frieda enthält keine eigene KI: Sie prüft Regeln, hält die Wahrheit und zeigt sie; recherchiert, abgewogen und formuliert wird im AI-Client der Reisenden. Welche Arten von Dingen und welche Merkmale eine Reise kennt (Refugi, Ryokan, Zeitfenster-Ticket, Vorbestellung), legt jede Reise selbst im Gespräch fest; die Software liefert keinen Katalog.

*A travel planner and handbook, AI first: a trip lives as a structured ontology (days, stays, movements, places, choices with a decision log, knowledge), every statement with its source and check date. The travellers' own AI client (Claude Desktop or mobile) reads and writes it through an MCP connector; Frieda itself contains no AI, it enforces the rules: no value without a source, no decision without a named organiser. A generator builds an offline-capable web handbook. The page and the connector speak German and English (further languages: one file each, `docs/sprachen.md`); the detailed documentation is in German, a short English summary is in [README.en.md](README.en.md).*

## Was es kann

| | Funktion | Mehr |
|---|---|---|
| **Reisemodell** | Tage, Orte, Unterkünfte, Aufenthalte, Strecken mit festen Kennungen (T-, O-, U-, A-, E- …); Arten und Merkmale legt jede Reise selbst fest; jede Angabe mit Herkunft, Veränderliches mit Prüfdatum; nichts wird gelöscht | [Reisemodell](docs/funktionen/reisemodell.md) |
| **Planen im Gespräch** | Die Claude-App liest die Reise über den Konnektor und trägt ein; Frieda prüft jede Eintragung nach den Regeln der Reise und sichert sie sofort, wenige Minuten später steht sie auf der Seite | [Planen im Gespräch](docs/funktionen/gespraech.md) |
| **Reiseseite** | Reiseüberblick mit Zeitachse, Tagesseiten, Ortsseiten, Wissen, „Zu tun“, Suche; als App auf dem Home-Bildschirm, offline mit Update-Hinweis und Ausgang für Eingaben ohne Netz | [Reiseseite](docs/funktionen/reiseseite.md) |
| **Alternativen** | Wahlstellen mit Optionen an jeder Stelle, benannte Pläne mit Summen (Gehzeit, Strecke, Höhenmeter, Nächte), Vergleich nach Merkmalen; entscheiden nur Organisator:innen, mit Person, Datum und Grund | [Alternativen](docs/funktionen/alternativen.md) |
| **Buchungen** | Buchung als eigenes Ding mit Nummer, Frist, Stornoregel, Zahlstand und Belegen; Check-in-Ansicht; Kosten der Übernachtungen | [Buchungen](docs/funktionen/buchungen.md) |
| **Karte** | Karte aus allen Orten mit Koordinaten, GPX-Tracks, Kartenansichten, Punkte aus OpenStreetMap, Grundkarte offline (PMTiles) | [Karte](docs/funktionen/karte.md) |
| **Zusammenarbeit** | Personen mit Rollen (Gast, Mitwirkende:r, Organisator:in) per E-Mail einladen; Rückmeldungen zu jeder Stelle, offene Fragen, Aufgaben, Wunsch-Brett mit Punkten | [Zusammenarbeit](docs/funktionen/zusammenarbeit.md) |
| **Packliste** | Gegenstände in Kategorien mit Summen wie Gewicht, Abhaken je Person auch ohne Netz, Übernahme aus einer früheren Reise; kein Inventar | [Packliste](docs/funktionen/packliste.md) |
| **Bilder** | Bilder aus Wikimedia Commons mit Namensnennung, eigene Fotos ohne Standortdaten, Titelbild, App-Symbol je Reise | [Bilder](docs/funktionen/bilder.md) |
| **Erinnerungen** | Fristen, Stornofristen, offene Zahlungen, fällige Statuswechsel, zu alte Prüfdaten; als Meldung, Push-Nachricht oder Mail; Kalender-Abo über alle Reisen | [Erinnerungen](docs/funktionen/erinnerungen.md) |
| **Lebenszyklus** | Neue Reise im Gespräch; Status von Idee bis Archiv mit eigenem Verhalten; Bausteine an- und abschalten; Reise löschen mit Schonfrist | [Lebenszyklus](docs/funktionen/lebenszyklus.md) |
| **Konto** | Anmeldung mit Code per Mail statt Passwort, ein Konnektor für alle Reisen, persönliches Profil, Meine Daten herunterladen, Konto löschen | [Konto](docs/funktionen/konto.md) |
| **Sprachen** | Deutsch und Englisch, jede weitere Sprache ist eine Datei | [Sprachen](docs/funktionen/sprachen.md) |
| **Selbst betreiben** | eigene Instanz: Reisespeicher (SQLite, nur anhängen), Veröffentlichen, tägliche Sicherung, Überwachung; keine KI auf dem Server | [Selbst betreiben](docs/funktionen/selbst-betreiben.md) |

Alle Funktionen mit Beispielen: [docs/funktionen/](docs/funktionen/README.md). Die ganze Dokumentation: [docs/](docs/README.md).

## Ausprobieren

```
python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt
engine/.venv/bin/python engine/bauen.py --reisen beispiel/reisen --ziel dist beispielreise
python3 -m http.server -d dist 8000      # dann http://localhost:8000/beispielreise/
```

Die Beispielreise „Malerweg in vier Tagen“ ist erfunden (siehe `beispiel/README.md`).

## Eigene Reisen

Im Betrieb entsteht eine Reise im Gespräch: Wer Reisen anlegen darf, sagt der Claude-App „Leg eine neue Reise an …“, und Frieda legt sie im Reisespeicher der Instanz an ([Lebenszyklus](docs/funktionen/lebenszyklus.md), [Neue Reise anlegen](docs/neue-reise.md)). Von da an wächst sie im Gespräch.

Zum Ausprobieren ohne Server baut der Generator Reisen aus Ordnern, standardmäßig aus `./reisen/` des aktuellen Ordners (`--reisen`, `--ziel` zum Ändern). Aufbau einer Reise: `beispiel/reisen/beispielreise/` (Wanderung) und `beispiel/reisen/stadtwochenende/` (Wochenende ohne Wanderung), `reise.yaml`, `reise.json`, `plan/routen.yaml`, `plan/arten.yaml`, `inhalt/`, `medien/`. Das Modell beschreibt die [Reise-Ontologie](docs/ontologie.md).

## Auf dem eigenen Server

Seiten ausliefern, Rückmeldungen annehmen, was der AI-Client über den Konnektor festlegt sofort in den Reisespeicher schreiben und veröffentlichen: `betrieb/` mit Überblick in [Selbst betreiben](docs/funktionen/selbst-betreiben.md) und Anleitung in [`docs/betrieb.md`](docs/betrieb.md). Auf dem Server läuft keine KI (`docs/adr/0001-kern.md`). Eine Reisegruppe mit eigenem Betreiber ist eine Instanz (eigene Ordner, Dienste und Adresse; die Software kommt direkt aus diesem Repo); ihre Werte stehen unter `<FR_DIENST>/instanz/` in `einstellungen.env`, die Skripte kennen keine Instanz. Grundkarten und Punkte aus OpenStreetMap holen die Werkzeuge in `werkzeuge/` (`docs/werkzeuge.md`).

## Tests

```
engine/.venv/bin/python -m pytest -q engine/tests
```

Die Browser-Prüfung der Offline-Fähigkeit braucht Playwright (`PLAYWRIGHT_MODUL=<pfad>/playwright/index.mjs`), sonst wird sie übersprungen.

## Lizenz

GNU Affero General Public License v3.0 (siehe `LICENSE`). Wer die Software als Online-Dienst anbietet, muss den geänderten Quellcode ebenfalls zugänglich machen. Eingebundene Bibliotheken und Schriften stehen unter ihren eigenen Lizenzen, siehe `THIRD_PARTY.md`.
