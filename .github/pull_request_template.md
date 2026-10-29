## Was ändert sich

<!-- in einfachen Worten, für den Product Owner -->

## Prüfstelle (ADR-0001, `docs/adr/0001-kern.md`)

Jede Zeile mit „ja“ oder „nein“ beantworten; bei 1 bis 7 heißt die falsche Antwort: nicht zusammenführen.

| Nr. | Frage | Antwort |
|---|---|---|
| 1 | Reisespezifisches steht in der Reise, nicht in der Software; mit zwei Reisetypen durchgespielt? | |
| 2 | Die Software führt keine Art und kein Merkmal ein und setzt keines voraus? | |
| 3 | Kein KI-Lauf in Frieda; Prüfungen sind Regeln im Code und getestet? | |
| 4 | Der AI-Client kann es über den Konnektor lesen und (rollengerecht) schreiben? | |
| 5 | Jede neue Aussage trägt Herkunft, Prüfdatum, Gültigkeit; ohne Herkunft wird abgelehnt? | |
| 6 | Keine Entscheidung ohne Organisator:in, Person, Datum, Grund und Verlauf; die KI entscheidet nie? | |
| 7 | Keine ID neu vergeben oder gelöscht, nichts ohne Verlaufseintrag überschrieben? | |
| 8 | Die PWA bleibt offline nutzbar und zeigt das Neue in Planung und unterwegs? | |
| 9 | Reiseinhalte entstehen nicht in Claude Code? | |
| 10 | Dokumentiert in: | |
| 11 | Oberfläche (ADR-0002, ADR-0003): neue Bausteine an vier Stellen (Kopfkommentar, Stile, Bausteinseite, `docs/design.md`), jedes Ding an genau einer Heimat vollständig; `test_design.py` grün? | |

## Tests

<!-- engine/.venv/bin/python -m pytest -q engine/tests -->
