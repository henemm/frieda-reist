# ADR-0011: Vorlagen für Arten

Stand: 10.11.2026 · Entscheidung des Product Owners (frieda-reist #471, #477), Entwurf am 10.11.2026 freigegeben

## Kontext

ADR-0001, Punkt 2 („Kein Katalog in der Software“): Welche Arten und Merkmale eine Reise kennt, entsteht je Reise im Gespräch. Übernehmen ging bisher nur aus einer früheren eigenen Reise. Für eine neue Person oder eine neue Instanz gibt es keine solche Reise; jede Reise baut Hotel, Flug oder Bus dann von vorn auf, und bewährte Merkmale (Frühstückszeiten, Rezeption, Flugnummer) fehlen.

## Entscheidung

1. Frieda bringt **Vorlagen** für häufige Arten mit: Hotel, Refugi, Flug, Bahn, Bus. Eine Vorlage enthält nur die Definition (Grundform, Name, Farbe, Symbol, buchbar, Merkmale mit Name, Typ, Werteliste, veränderlich, Rolle, `nach_buchung`, `lang`, Hilfe), **keine Werte**.
2. Eine Vorlage ist ein **Angebot**. In eine Reise kommt sie nur, wenn eine Organisator:in sie mit `arten_uebernehmen` (`vorlage: true`) übernimmt. Danach ist sie eine Kopie der Reise, frei änderbar, ohne Verweis zurück. Keine Reise bekommt eine Vorlage von selbst.
3. Der Code setzt weiterhin **keine Art und kein Merkmal voraus**: Seite, Prüfungen, Wächter und Konnektor richten sich nur nach der Definition der Reise. Feste Felder der Grundformen (Abfahrt, Ankunft, Adresse, Buchungslink) stehen nicht in den Vorlagen.
4. Die Vorlagen liegen je Sprache in `engine/artvorlagen/<sprache>.yaml` (Form wie `plan/arten.yaml`); fehlt eine Sprache, gilt die Vorgabesprache. Eine neue Sprache bringt ihre Datei mit (ADR-0006).
5. Übernehmen bringt nie Werte mit, weder aus einer Vorlage noch aus einer früheren Reise.

## Folgen

- Prüfstelle, Frage 2: „Setzt die Software eine Art oder ein Merkmal voraus? Nein; Vorlagen gelangen nur durch Übernehmen in eine Reise.“
- Neue Vorlagen oder Merkmale darin sind eine Änderung der Software (Pull Request, Tests mit beiden Beispielreisen).
- `deploy.sh` legt `artvorlagen/` neben den Code des Schreibwegs.
