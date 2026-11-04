# Context: nginx-uebergang-206

## Request Summary
Die nginx-Vorlage des Konnektors soll die abgeschalteten Übergangs-Links nicht wieder öffnen (Server liefert 404, Vorlage würde sie durchlassen).

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/vorlagen/nginx-konnektor-orte.inc | enthält die beiden Übergangs-Orte |
| engine/tests/test_betrieb.py | Tests der erzeugten Orte (um Zeile 1789 und 1908) |
| docs/betrieb.md | beschreibt den Übergang (Zeilen 256, 304) |

## Existing Patterns
- Tests erzeugen die Bausteine mit einrichten.sh und starten ein echtes nginx.

## Dependencies
- Upstream: einrichten.sh ersetzt die Platzhalter. Downstream: nginx.py pruefen/anwenden vergleichen die erzeugten Dateien.

## Existing Specs
- docs/specs/fast/nginx-vorlage-206.md

## Risks & Considerations
- Der Dienst kennt die Token-Pfade weiter; nginx reicht sie nach der Änderung nicht mehr durch (wie heute auf dem Server).
