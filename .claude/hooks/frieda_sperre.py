#!/usr/bin/env python3
"""Sperre gegen Schreiben über den Konnektor des Product Owners in Claude-Code-Sitzungen dieses Repos (#648).

PreToolUse-Hook für `mcp__claude_ai_Frieda__.*` (.claude/settings.json). Abnahmen laufen über den eigenen Zugang
`frieda-test` mit dem Testkonto; über das Konto des Product Owners darf Claude Code nur lesen.

Erlaubt sind genau die Werkzeuge, die der Konnektor mit `readOnlyHint: true` ausweist (Namen wie in tools/list).
Alles andere, auch ein unbekanntes oder neues Werkzeug, wird mit Exit-Code 2 abgelehnt; der Hinweis auf stderr geht an
Claude Code. Die Liste pflegt niemand von Hand: engine/tests/test_frieda_sperre.py hält sie gegen den Konnektor synchron.
Werkzeuge anderer Server bleiben unberührt. Nur Standardbibliothek.
"""
import json
import sys

PRAEFIX = "mcp__claude_ai_Frieda__"

ERLAUBT = frozenset({
    "attributes", "feedback_list", "my_profile", "my_trips", "open_questions", "overview", "packing_list",
    "page_view", "people", "publish_status", "search", "show", "tasks", "variants", "wishes",
})

HINWEIS = ("Gesperrt (#648): Über den Konnektor des Product Owners darf Claude Code nur lesen. "
           "Für Abnahmen und alles Schreibende den eigenen Zugang frieda-test (Testkonto) nutzen: "
           "mcp__frieda-test__{name}.")


def main():
    try:
        ereignis = json.loads(sys.stdin.read())
        werkzeug = ereignis["tool_name"]
        if not isinstance(werkzeug, str):
            raise TypeError(werkzeug)
    except (ValueError, KeyError, TypeError):
        print("Gesperrt (#648): Hook-Ereignis unlesbar; Werkzeuge des Konnektors des Product Owners nur lesend, "
              "Abnahmen über frieda-test.", file=sys.stderr)
        return 2
    if not werkzeug.startswith(PRAEFIX):
        return 0
    name = werkzeug[len(PRAEFIX):]
    if name in ERLAUBT:
        return 0
    print(HINWEIS.format(name=name), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
