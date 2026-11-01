# Frieda Reist

*Deutsch: see [README.md](README.md). The detailed documentation in `docs/` is in German; this page is a short summary in English.*

**An AI-first travel planner and trip handbook.** Frieda keeps a trip as structured truth (a travel ontology): days, stays, movements, places, alternatives with a decision log, and knowledge. Every item has a fixed ID, and every statement carries its source and check date. Everything unstructured (conversation, research, weighing options) happens in the travellers' own AI client (Claude Desktop or mobile), which reads and writes the trip through an MCP connector. A generator turns the trip into a web handbook that works offline.

## The core in three sentences

- Frieda contains no AI of its own. It enforces rules, holds the truth and shows it; research and wording happen in the AI client.
- The origin of every statement is enforced when it is written: no value without a source, anything that changes over time only with a check date, decisions only by organisers, with name, date and reason.
- Which kinds of things and which features a trip knows (a mountain hut, a ryokan, a timed-entry ticket) is decided by each trip in conversation; the software ships no catalogue. See [`docs/adr/0001-kern.md`](docs/adr/0001-kern.md) (German).

## What it does

- **Day plan, stages, places, stays** with fixed IDs, so that every comment can be matched to exactly one item.
- **Alternatives in the model:** choices with options on every level, named plans with totals, and a history. Nothing rejected is ever deleted.
- **Offline:** the page is a PWA with an offline cache, an update notice and an outbox for feedback without a network; maps with numbered places.
- **Fellow travellers:** feedback, wishes and tasks on every ID, through the page or through the Claude app. Roles: `gast` (read), `mitwirkend` (contribute), `organisator` (decide).
- **The connector writes directly:** what is settled in conversation is checked against the trip's rules and saved to the repository at once, with person and source; a few minutes later it is on the page.
- **Languages:** German and English. The page follows the trip's language and has a switcher for the labels; the connector speaks the language of the person's account. A further language is one file, `engine/texte_<code>.py` (see [`docs/sprachen.md`](docs/sprachen.md), German).

## Try it

```
python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt
engine/.venv/bin/python engine/bauen.py --reisen beispiel/reisen --ziel dist beispielreise
python3 -m http.server -d dist 8000      # then open http://localhost:8000/beispielreise/
```

The example trip "Malerweg in four days" is invented (see `beispiel/README.md`). Real trips live in their own, preferably private repositories that include this one as a submodule `frieda/`.

## Tests

```
engine/.venv/bin/python -m pytest -q engine/tests
```

## Licence

GNU Affero General Public License v3.0 (see `LICENSE`). Anyone offering the software as an online service must make the modified source code available as well. Bundled libraries and fonts are under their own licences, see `THIRD_PARTY.md`.
