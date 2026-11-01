# Frieda Reist – Arbeitsregeln für die Software

Dieses Repo enthält nur die Software (Generator, Vorlage, Service Worker, Rückmeldedienst, Konnektor für die Claude-App, Betrieb auf dem Server) und eine erfundene Beispielreise. Es ist öffentlich (AGPL-3.0). Echte Reisen liegen in eigenen, privaten Repos, die dieses als Submodul `frieda/` einbinden.

## Was nie hierher gehört

Echte Reisen, Namen echter Personen, Serveradressen, geheime Pfade, Zugangsdaten, Konnektor-Links, Buchungen, Texte oder Fotos aus Reiseführern. Beispiele und Tests nutzen nur die Beispielreise (`beispiel/reisen/beispielreise`, Personen Ida und Karl) oder erfundene Testdaten.

## Aufbau

```
engine/            bauen.py (Generator), routen.py (Routenmodell), reise.py (reise.yaml), gpx.py, instanz.py (Vorgaben einer Instanz),
                   konten.py, anmeldung.py, oauth.py (Konten und Anmeldung, ADR-0005),
                   vorlage.html, sw.vorlage.js, rueckmeldungen.py (Dienst), belege.py (Belege zu Buchungen), konnektor.py (MCP), schnittstelle.py (englische Namen mit deutschen Aliasen), texte.py und texte_<kürzel>.py (Textkatalog je Sprache), schreiben.py (Schreibweg:
                   der Konnektor schreibt direkt in die Reise), waechter.py (Wächter und Erinnerer, läuft täglich),
                   neu.py (neue Reise, IDs, arten-ableiten, nachziehen), reisevorlage/, vendor/ (Fremdbibliotheken, siehe THIRD_PARTY.md), tests/
betrieb/           Betrieb einer Instanz: Schreibweg, Veröffentlichen, Deploy, Freischalten, Zustellen der Links neuer Reisen,
                   Wächter-Lauf, Einrichten, Vorlagen für systemd und nginx, einstellungen.beispiel (keine KI auf dem Server)
werkzeuge/         Werkzeuge für Inhalte aus dem Netz: Grundkarte, Punkte und Adressen aus OpenStreetMap, Wasserstellen
beispiel/reisen/   erfundene Beispielreise, Demo und Testgrundlage
docs/              Produktbild, Alternativen und Merkmale, Design und Bausteine, Konnektor, Sprachen, Betrieb, Werkzeuge;
                   adr/ Architektur-Entscheidungen, ADR-0001 ist der Kern und die Prüfstelle, ADR-0002 Atomic Design, ADR-0003 eine Heimat je Grundform,
                   ADR-0004 Lage eines Aufenthalts, ADR-0005 Konten und Anmeldung; abgleich-2026-10-29.md Prüfbericht und Backlog
```

Der Generator sucht Reisen in `./reisen/` des aktuellen Ordners (`--reisen`, `--ziel` zum Ändern).

## Regeln

- **Zuerst der Kern:** Jedes Vorhaben wird vor dem Bauen an `docs/adr/0001-kern.md` gemessen (zehn Fragen der Prüfstelle, im PR-Template). Widerspricht es dem Kern, wird nicht gebaut, sondern der Product Owner gefragt. Die Software kennt nur die Grundformen der Reise-Ontologie und die Form eines Merkmals; Arten und Merkmale gehören der Reise. Frieda enthält keine eigene KI; Reiseinhalte entstehen im AI-Client über den Konnektor, nicht in Claude Code (Product Owner, 28.10.2026).
- Änderungen gelten für alle Reisen: nichts Reisespezifisches in die Engine, Einstellungen gehören in `reise.yaml` der Reise.
- Änderungen gelten für alle Instanzen: nichts Instanzspezifisches in `betrieb/`, `werkzeuge/` oder die Engine (Pfade, Adressen, Benutzer, Meldeweg, Kennung kommen aus `betrieb/einstellungen.env` des Reisen-Repos, `docs/betrieb.md`; Vorgaben der Engine in `engine/instanz.py`).
- Oberfläche nach Atomic Design ([ADR-0002](docs/adr/0002-atomic-design.md)): vorhandene Bausteine nutzen; ein neuer Baustein kommt in den Kopfkommentar der Vorlage, in die Stile seiner Ebene, auf die Bausteinseite und in `docs/design.md` (zeigt er eine Grundform, auch in `ONTOLOGIE`). Jede Grundform hat genau eine Heimat auf der Seite, überall sonst nur eine Zeile mit einem Link dorthin ([ADR-0003](docs/adr/0003-heimat.md)).
- Sichtbare Texte (Seite, Konnektor, Mails, Fehler) stehen in `engine/texte_<sprache>.py` in allen Sprachen, nie im Code ([ADR-0006](docs/adr/0006-mehrsprachigkeit.md)); Werkzeug- und Parameternamen des Konnektors englisch mit deutschem Alias. Der Code kennt keine Sprache beim Namen; eine neue Sprache ist eine Datei und wird gefunden, ohne dass Code geändert wird (Anleitung, Regeln für Schlüssel und die Pseudo-Sprache der Tests: [docs/sprachen.md](docs/sprachen.md)). Die Ausnahmelisten in `engine/tests/test_texte.py` dürfen nur kürzer werden.
- Bibliotheken statt Eigenbau; neue Fremdbestandteile mit Lizenz in `engine/vendor/` und `THIRD_PARTY.md`.
- Tests: `engine/.venv/bin/python -m pytest -q engine/tests` muss ohne echte Reisen grün sein. Neue Funktionen bekommen Tests, wenn nötig mit Ergänzungen der Beispielreise (erfunden, als Beispielwert markiert).
- Braucht der Konnektor oder der Rückmeldedienst ein neues eigenes Modul, gehört es in die Liste in `betrieb/deploy.sh` (ein Test prüft das).
- Sprache der Texte und Kommentare: Deutsch mit korrekten Umlauten.
- Kleine, thematisch saubere Commits; Änderungen über Pull Requests.
- Alles, was Git betrifft (Branches, Commits, Rebase, Vorspulen auf `main`, Push), entscheidet Claude selbst und ohne Rückfrage (Product Owner, 1.11.2026). „Autark umsetzen“ heißt: bis `main` ausliefern, sobald die Tests grün sind.
- Keine privaten E-Mail-Adressen in der Geschichte: lokal `user.email` auf die GitHub-noreply-Adresse setzen und Pull Requests lokal vorspulen statt auf GitHub zusammenführen (nach grünen Tests `git push origin HEAD:main`; GitHub markiert den PR dann selbst als gemergt). Jedes Zusammenführen über GitHub trägt sonst die Konto-Adresse als Committer ein.
