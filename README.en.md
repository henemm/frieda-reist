# Frieda Reist

*Deutsch: see [README.md](README.md). The detailed documentation in `docs/` is in German; this page is a short summary in English.*

**An AI-first travel planner and trip handbook.** Frieda keeps a trip as structured truth (a travel ontology): days, stays, movements, places, alternatives with a decision log, and knowledge. Every item has a fixed ID, and every statement carries its source and check date. Everything unstructured (conversation, research, weighing options) happens in the travellers' own AI client (Claude Desktop or mobile), which reads and writes the trip through an MCP connector. A generator turns the trip into a web handbook that works offline.

## The core in three sentences

- Frieda contains no AI of its own. It enforces rules, holds the truth and shows it; research and wording happen in the AI client.
- The origin of every statement is enforced when it is written: no value without a source, anything that changes over time only with a check date, decisions only by organisers, with name, date and reason.
- Which kinds of things and which features a trip knows (a mountain hut, a ryokan, a timed-entry ticket) is decided by each trip in conversation; the software ships no catalogue. See [`docs/adr/0001-kern.md`](docs/adr/0001-kern.md) (German).

## What it does

All features, with examples and pictures, are on the website of every Frieda instance under "What Frieda can do" (`/info/funktionen/`), one page per area, in English and German: from the trip model and planning in conversation to the trip page, alternatives, bookings, map, collaboration, packing list, images and reminders, to accounts, languages and running Frieda on your own server. For developers: [guide to the areas](docs/funktionen/README.md) (German) and the documentation under [docs/README.md](docs/README.md).

## Try it

```
python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt
engine/.venv/bin/python engine/bauen.py --reisen beispiel/reisen --ziel dist beispielreise
python3 -m http.server -d dist 8000      # then open http://localhost:8000/beispielreise/
```

The example trip "Malerweg in four days" is invented (see `beispiel/README.md`). In operation, trips are created in conversation and kept in the trip store of an instance (SQLite, append-only); running your own instance is described in [`docs/betrieb.md`](docs/betrieb.md) (German).

## Tests

```
engine/.venv/bin/python -m pytest -q engine/tests
```

## Licence

GNU Affero General Public License v3.0 (see `LICENSE`). Anyone offering the software as an online service must make the modified source code available as well. Bundled libraries and fonts are under their own licences, see `THIRD_PARTY.md`.
