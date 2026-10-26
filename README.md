# Frieda Reist

**Ein Reisehandbuch mit Lektorat, AI first.** Eine Reise liegt als Text und YAML in einem Git-Repo: Tage, Etappen, Orte, Unterkünfte, Alternativen und Wissen, jede Stelle mit fester ID. Ein KI-Assistent (heute Claude Code) recherchiert und pflegt die Inhalte, mit Quelle und Prüfdatum zu jeder veränderlichen Angabe. Ein Generator baut daraus ein Reisehandbuch als Webseite, das offline funktioniert.

*A travel handbook with an editor, AI first: trips live as text in Git, an AI assistant researches and maintains them with sources and check dates, and a generator builds an offline-capable web handbook. Fellow travellers comment on any item; the AI works their input in. Documentation is in German for now.*

## Was es kann

- **Tagesplan, Etappen, Orte, Unterkünfte** mit festen IDs (T-, E-, O-, U-, W- …), damit sich jede Rückmeldung genau zuordnen lässt.
- **Alternativen im Modell:** Wahlstellen mit Optionen auf jeder Ebene, benannte Pläne mit Summen (Gehzeit, Strecke, Höhenmeter, Nächte nach Kategorie) und ein Verlauf. Verworfenes wird nie gelöscht, entscheiden dürfen nur Bestimmer.
- **Quellen und Prüfdaten:** Fußnoten mit Titel, Link und Datum; Merkmale wie Preise tragen ein Prüfdatum.
- **Offline:** Die Seite ist eine PWA mit Vorab-Speicher, Update-Hinweis und Ausgang für Rückmeldungen ohne Netz. Karten mit nummerierten Orten (Leaflet, optional OpenStreetMap-Vektorkarten als PMTiles).
- **Mitreisende:** Rückmeldungen, Wünsche und Aufgaben zu jeder ID, über die Seite oder über die Claude-App (MCP-Konnektor). Personen haben Rollen: `reisend` (lesen), `einbringer` (Eingaben) und `bestimmer` (entscheiden).
- **Die KI arbeitet ein:** Eingaben werden geprüft, mit Quelle eingearbeitet, gebaut, getestet und veröffentlicht. Der Status geht an den Absender zurück.

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

Aufbau einer Reise: `beispiel/reisen/beispielreise/`, Modell in `engine/routen.py` und `engine/reise.py`, Produktbild in `docs/produkt.md`, Alternativen und Merkmale in `docs/alternativen.md`, Claude-App in `docs/konnektor.md`.

## Tests

```
engine/.venv/bin/python -m pytest -q engine/tests
```

Die Browser-Prüfung der Offline-Fähigkeit braucht Playwright (`PLAYWRIGHT_MODUL=<pfad>/playwright/index.mjs`), sonst wird sie übersprungen.

## Lizenz

GNU Affero General Public License v3.0 (siehe `LICENSE`). Wer die Software als Online-Dienst anbietet, muss den geänderten Quellcode ebenfalls zugänglich machen. Eingebundene Bibliotheken und Schriften stehen unter ihren eigenen Lizenzen, siehe `THIRD_PARTY.md`.
