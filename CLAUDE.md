# Frieda Reist – Arbeitsregeln für die Software

Dieses Repo enthält nur die Software (Generator, Vorlage, Service Worker, Rückmeldedienst, Konnektor für die Claude-App, Betrieb auf dem Server) und eine erfundene Beispielreise. Es ist öffentlich (AGPL-3.0). Echte Reisen liegen in eigenen, privaten Repos, die dieses als Submodul `frieda/` einbinden.

## Was nie hierher gehört

Echte Reisen, Namen echter Personen, Serveradressen, geheime Pfade, Zugangsdaten, Konnektor-Links, Buchungen, Texte oder Fotos aus Reiseführern. Beispiele und Tests nutzen nur die Beispielreise (`beispiel/reisen/beispielreise`, Personen Ida und Karl) oder erfundene Testdaten.

## Aufbau

```
engine/            bauen.py (Generator), routen.py (Routenmodell), reise.py (reise.yaml), gpx.py,
                   vorlage.html, sw.vorlage.js, rueckmeldungen.py (Dienst), konnektor.py (MCP), waechter.py (Wächter und
                   Erinnerer, läuft täglich), merkmale.yaml,
                   vendor/ (Fremdbibliotheken, siehe THIRD_PARTY.md), tests/
betrieb/           Betrieb einer Instanz: Einarbeiten (KI je Reise), Veröffentlichen, Deploy, Freischalten, Wächter-Lauf,
                   Einrichten, Vorlagen für systemd und nginx, KI-Anweisung, einstellungen.beispiel
werkzeuge/         Werkzeuge für Inhalte aus dem Netz: Grundkarte, Punkte aus OpenStreetMap, Wasserstellen
beispiel/reisen/   erfundene Beispielreise, Demo und Testgrundlage
docs/              Produktbild, Alternativen und Merkmale, Design und Bausteine, Architekturentscheidungen (adr/), Konnektor, Betrieb, Werkzeuge
```

Der Generator sucht Reisen in `./reisen/` des aktuellen Ordners (`--reisen`, `--ziel` zum Ändern).

## Regeln

- Änderungen gelten für alle Reisen: nichts Reisespezifisches in die Engine, Einstellungen gehören in `reise.yaml` der Reise.
- Änderungen gelten für alle Instanzen: nichts Instanzspezifisches in `betrieb/`, `werkzeuge/` oder die Engine (Pfade, Adressen, Benutzer, Meldeweg, Kennung kommen aus `betrieb/einstellungen.env` des Reisen-Repos, `docs/betrieb.md`; Vorgaben der Engine in `engine/instanz.py`).
- Oberfläche nach Atomic Design ([ADR 0001](docs/adr/0001-atomic-design.md)): vorhandene Bausteine nutzen; ein neuer Baustein kommt in den Kopfkommentar der Vorlage, in die Stile seiner Ebene, auf die Bausteinseite und in `docs/design.md` (zeigt er eine Art, auch in `ONTOLOGIE`). Grundsatzentscheidungen stehen als ADR in `docs/adr/`.
- Bibliotheken statt Eigenbau; neue Fremdbestandteile mit Lizenz in `engine/vendor/` und `THIRD_PARTY.md`.
- Tests: `engine/.venv/bin/python -m pytest -q engine/tests` muss ohne echte Reisen grün sein. Neue Funktionen bekommen Tests, wenn nötig mit Ergänzungen der Beispielreise (erfunden, als Beispielwert markiert).
- Braucht der Konnektor oder der Rückmeldedienst ein neues eigenes Modul, gehört es in die Liste in `betrieb/deploy.sh` (ein Test prüft das).
- Sprache der Texte und Kommentare: Deutsch mit korrekten Umlauten.
- Kleine, thematisch saubere Commits; Änderungen über Pull Requests.
- Keine privaten E-Mail-Adressen in der Geschichte: lokal `user.email` auf die GitHub-noreply-Adresse setzen und Pull Requests lokal vorspulen statt auf GitHub zusammenführen (nach grünen Tests `git push origin HEAD:main`; GitHub markiert den PR dann selbst als gemergt). Jedes Zusammenführen über GitHub trägt sonst die Konto-Adresse als Committer ein.
