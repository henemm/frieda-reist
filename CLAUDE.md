# Frieda Reist – Arbeitsregeln für die Software

Dieses Repo enthält nur die Software (Generator, Vorlage, Service Worker, Rückmeldedienst, Konnektor für die Claude-App, Betrieb auf dem Server) und eine erfundene Beispielreise. Es ist öffentlich (AGPL-3.0). Echte Reisen liegen in eigenen, privaten Repos, die dieses als Submodul `frieda/` einbinden.

## Rollen und Zusammenarbeit (Vorgabe des Product Owners, 8.11.2026, gilt für jede Sitzung, auch Cloud)

- **Der Product Owner ist kein Programmierer**; er schaut nie in Git, PRs oder CI. Antworten an ihn: einfache Sprache, Ergebnis statt Mechanik, Fachbegriffe kurz übersetzt.
- **Form der Antworten an den Product Owner** (jede Antwort, auch nach langer Arbeit): Das Ergebnis steht zuerst, in ein bis zwei Sätzen, danach nur, was er entscheiden oder tun muss. Keine Dateinamen, Commit- oder PR-Nummern, Testzahlen, Werkzeug- oder Funktionsnamen, außer er fragt danach. Was nicht geklappt hat, in einem Satz mit dem nächsten Schritt. Kurze Absätze, keine langen Listen und Tabellen; Fachwörter, die sich nicht vermeiden lassen, in einem Halbsatz erklären. Technische Einzelheiten gehören in das Issue oder den Pull Request, nicht in den Chat.
- **Wer spricht** (Product Owner, 10.11.2026): In Antworten an den Product Owner nennt Claude sich beim Namen statt „ich“, etwa „Claude hat die Buchungen umgestellt“, damit klar ist, wer gehandelt hat: Claude (Claude Code), nicht Frieda (der Assistent in der Claude-App) und nicht der Product Owner selbst.
- **Claude ist Tech Lead** und entscheidet technisch selbst, nach etablierter Praxis, den Specs, ADRs und früher getroffenen Entscheidungen (Issues, Doku) dieses Repos. Keine Abkürzungen, keine ungetesteten Experimente am Live-System; nur bei echten Produkt-Zielkonflikten Optionen mit begründeter Empfehlung vorlegen.
- **Git ist allein Claudes Sache:** Branch, Commit, Push, PR, CI abwarten, Vorspulen auf `main`, Deploy, Issues, ohne Rückfrage und ohne Bericht darüber, nach dem Lieferweg unten (PR, grüne Pflichtprüfungen, dann `git push origin HEAD:main`). Das hebt die Standardvorsicht („Commit/Push nur auf Nachfrage“) für dieses Repo ausdrücklich auf. Andere Sitzungen und Instanzen sind ebenfalls Claude Code; nie Arbeit an den Product Owner abgeben.
- **Den Product Owner fragen nur zu Produktentscheidungen** (Freigabe von Anforderungen, fachliche Zielkonflikte), per `AskUserQuestion`, nie als Freitext. Tooling, Git, Hooks und Server-Mechanik klärt Claude selbst.
- **Erst zeigen, dann bauen** (Product Owner, 9.11.2026, #436): Was der Product Owner sieht oder liest (neue Seiten, Gestaltung, Texte, Beispiele, Bilder), zeigt Claude ihm vor dem Ausliefern als Entwurf in einem Claude-Artefakt (privat, mit den erfundenen Beispieldaten) und baut erst nach seiner Zustimmung fertig. Änderungen daran ebenso: zuerst in den Entwurf, dann ausliefern.
- **Aufgaben nur als GitHub-Issues** in diesem Repo; ein Issue erst schließen, wenn es end-to-end erledigt ist.

## Was nie hierher gehört

Echte Reisen, Namen echter Personen, Serveradressen, geheime Pfade, Zugangsdaten, Konnektor-Links, Buchungen, Texte oder Fotos aus Reiseführern. Das gilt auch für Protokolle, Nachweise und Specs (`docs/artifacts/`, `docs/specs/`, `docs/context/`): kopierte Testausgaben mit Pfaden relativ zum Repo oder zu `~`, echte Reisen nur als Platzhalter (`<Reise A>`); `engine/tests/test_protokolle_ohne_pfade.py` prüft die Pfade. Beispiele und Tests nutzen nur die beiden Beispielreisen (`beispiel/reisen/beispielreise`, eine Wanderung mit Varianten, Personen Ida und Karl; `beispiel/reisen/stadtwochenende`, ein Wochenende bei Verwandten ohne Wanderung, Personen Tom und Lea) oder erfundene Testdaten.

## Aufbau

```
engine/            bauen.py (Generator), routen.py (Routenmodell), reise.py (reise.yaml), gpx.py, karte.py (Karte aus dem Plan), instanz.py (Vorgaben einer Instanz),
                   konten.py, anmeldung.py, oauth.py (Konten und Anmeldung, ADR-0005),
                   reisespeicher.py (Reisedaten als Versionen in SQLite, nur anhängen, ADR-0009), packliste.py (Packliste: Gegenstände G-…, Summen, ADR-0010),
                   vorlage.html, sw.vorlage.js, rueckmeldungen.py (Dienst), belege.py (Belege zu Buchungen), konnektor.py (MCP), schnittstelle.py (englische Namen mit deutschen Aliasen), texte.py und texte_<kürzel>.py (Textkatalog je Sprache), schreiben.py (Schreibweg:
                   der Konnektor schreibt direkt in die Reise), waechter.py (Wächter und Erinnerer, läuft täglich),
                   neu.py (Anlegen, IDs, Abschnitte für den Schreibweg; als Befehl nur Struktur: erste Reise, pruefen, arten-ableiten, nachziehen), reisevorlage/, vendor/ (Fremdbibliotheken, siehe THIRD_PARTY.md), tests/
betrieb/           Betrieb einer Instanz: Schreibweg, Veröffentlichen, Deploy, Freischalten, Zustellen der Links neuer Reisen,
                   Wächter-Lauf, Einrichten, Vorlagen für systemd und nginx, einstellungen.beispiel (keine KI auf dem Server)
werkzeuge/         Werkzeuge für Inhalte aus dem Netz: Grundkarte, Punkte und Adressen aus OpenStreetMap, Wasserstellen
beispiel/reisen/   erfundene Beispielreisen (Wanderung und Städtewochenende), Demo und Testgrundlage; jede Funktion gegen beide denken (ADR-0001, Frage 1)
docs/              Produktbild, Alternativen und Merkmale, Design und Bausteine, Konnektor, Sprachen, Betrieb, Werkzeuge;
                   adr/ Architektur-Entscheidungen, ADR-0001 ist der Kern und die Prüfstelle, ADR-0002 Atomic Design, ADR-0003 eine Heimat je Grundform,
                   ADR-0004 Lage eines Aufenthalts, ADR-0005 Konten und Anmeldung, ADR-0009 Reisespeicher, ADR-0010 Gegenstand und Packliste, ADR-0011 Vorlagen für Arten; abgleich-2026-10-29.md Prüfbericht und Backlog
```

Der Generator sucht Reisen in `./reisen/` des aktuellen Ordners (`--reisen`, `--ziel` zum Ändern).

## Regeln

- **Zuerst der Kern:** Jedes Vorhaben wird vor dem Bauen an `docs/adr/0001-kern.md` gemessen (zehn Fragen der Prüfstelle, im PR-Template). Widerspricht es dem Kern, wird nicht gebaut, sondern der Product Owner gefragt. Die Software kennt nur die Grundformen der Reise-Ontologie und die Form eines Merkmals; Arten und Merkmale gehören der Reise (Vorlagen für häufige Arten nur als Angebot zum Übernehmen, ADR-0011). Frieda enthält keine eigene KI; Reiseinhalte entstehen im AI-Client über den Konnektor, nicht in Claude Code (Product Owner, 28.10.2026).
- Änderungen gelten für alle Reisen: nichts Reisespezifisches in die Engine, Einstellungen gehören in `reise.yaml` der Reise.
- Änderungen gelten für alle Instanzen: nichts Instanzspezifisches in `betrieb/`, `werkzeuge/` oder die Engine (Pfade, Adressen, Benutzer, Meldeweg, Kennung kommen aus `betrieb/einstellungen.env` des Reisen-Repos, `docs/betrieb.md`; Vorgaben der Engine in `engine/instanz.py`).
- Oberfläche nach Atomic Design ([ADR-0002](docs/adr/0002-atomic-design.md)): vorhandene Bausteine nutzen; ein neuer Baustein kommt in den Kopfkommentar der Vorlage, in die Stile seiner Ebene, auf die Bausteinseite und in `docs/design.md` (zeigt er eine Grundform, auch in `GRUNDFORMEN`). Jede Grundform hat genau eine Heimat auf der Seite, überall sonst nur eine Zeile mit einem Link dorthin ([ADR-0003](docs/adr/0003-heimat.md)).
- Sichtbare Texte (Seite, Konnektor, Mails, Fehler) stehen in `engine/texte_<sprache>.py` in allen Sprachen, nie im Code ([ADR-0006](docs/adr/0006-mehrsprachigkeit.md)); Werkzeug- und Parameternamen des Konnektors englisch mit deutschem Alias. Der Code kennt keine Sprache beim Namen; eine neue Sprache ist eine Datei und wird gefunden, ohne dass Code geändert wird (Anleitung, Regeln für Schlüssel und die Pseudo-Sprache der Tests: [docs/sprachen.md](docs/sprachen.md)). Die Ausnahmelisten in `engine/tests/test_texte.py` dürfen nur kürzer werden.
- Bibliotheken statt Eigenbau; neue Fremdbestandteile mit Lizenz in `engine/vendor/` und `THIRD_PARTY.md`.
- Tests: `engine/.venv/bin/python -m pytest -q engine/tests` muss ohne echte Reisen grün sein (rund 20 Minuten; mit `-n 3` oder `-n auto` parallel in etwa 7, so läuft auch CI, #322; auf dem Server der Instanz seit #395 ebenso, wenn pytest-xdist in `FR_PYTHON` liegt). Neue Funktionen bekommen Tests, wenn nötig mit Ergänzungen der Beispielreise (erfunden, als Beispielwert markiert).
- Jede Änderung am Format der Reisedaten bringt ihre Umstellung in `neu.py nachziehen` mit, mit Test; der Workflow „Software nachziehen“ stellt damit jede Reise im selben Commit wie den neuen Software-Stand um. Ein Handschritt in Reisen oder Instanzen nach einem Software-Wechsel ist ein Fehler der Software (#250).
- Braucht der Konnektor oder der Rückmeldedienst ein neues eigenes Modul, gehört es in die Liste in `betrieb/deploy.sh` (ein Test prüft das).
- Sprache der Texte und Kommentare: Deutsch mit korrekten Umlauten.
- Kleine, thematisch saubere Commits; Änderungen über Pull Requests.
- Alles, was Git betrifft (Branches, Commits, Rebase, Vorspulen auf `main`, Push), entscheidet Claude selbst und ohne Rückfrage (Product Owner, 1.11.2026). „Autark umsetzen“ heißt: bis `main` ausliefern, sobald die Tests grün sind.
- Keine privaten E-Mail-Adressen in der Geschichte: lokal `user.email` auf die GitHub-noreply-Adresse setzen und Pull Requests lokal vorspulen statt auf GitHub zusammenführen (nach grünen Tests `git push origin HEAD:main`; GitHub markiert den PR dann selbst als gemergt). Jedes Zusammenführen über GitHub trägt sonst die Konto-Adresse als Committer ein.
- `main` ist geschützt (Ruleset, Product Owner 2.11.2026, #205): Ein Push nach `main` wird nur angenommen, wenn genau dieser Commit seine Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) schon grün hat. Also: Branch pushen, PR, CI abwarten, dann `git push origin HEAD:main`. Hängt die CI, `gh run rerun`; das Ruleset wird nie abgeschaltet, um etwas durchzudrücken.
- Mehrere Sitzungen arbeiten oft gleichzeitig. Wer eine Störung oder ein Issue übernimmt, sagt es vorher an: Kommentar im Issue (ohne Issue erst eines anlegen) und eine direkte Nachricht an die laufenden Sitzungen der Software und ihrer Instanzen. Vorher nachsehen, ob schon jemand dran ist. Kein Auftrag an eine andere Sitzung für etwas, das man selbst erledigen kann; ein Issue hält es nachvollziehbar. Meldewege der Instanz (Telegram u. ä.) sind nur für Ausfälle, nicht für Absprachen.
- **Meldeweg nur für Ausfälle** (#445, #446): Die Stufe `high` von `FR_MELDEN` (`fr_alarm`, `alarm_senden`) gilt nur, wenn etwas ausgefallen ist und der Betreiber jetzt handeln muss und kann (Wächter oder Sicherung gescheitert, Veröffentlichen rot). Alles andere: `normal` (wird bei der Instanz ein Issue), eine Warnzeile im Protokoll oder ein Teil-Check in `monitor.sh` der Infrastruktur; ein Bericht (`erledigt`) wird nicht versendet. Jeder Alarm kommt einmal je Störung und endet, sobald der Teil wieder gelingt. Nie Arbeit über den Meldeweg an andere Instanzen weiterreichen. Jede `high`-Stelle steht mit Begründung in `ALARMSTELLEN` (`engine/tests/test_betrieb.py`); eine neue ohne Begründung macht den Test rot.
- Ändert ein PR Meldungstexte, Schnittstellen, Umgebungswerte oder Dateiformate, die eine Instanz nutzt, laufen vor dem Vorspulen auch die Tests der einbindenden Instanzen mit dem Branch (Anleitung im Reisen-Repo der Instanz). Die öffentliche CI kann private Tests nicht ausführen.
