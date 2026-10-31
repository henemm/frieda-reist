---
entity_id: bauordner-137
type: module
created: 2026-10-31
updated: 2026-10-31
status: draft
version: "1.0"
tags: [betrieb, veroeffentlichen, deploy, ordner]
---

# Bauordner getrennt vom Arbeitsordner, Phase 3 (#137)

Grundlage: Plan in Issue #137 (Product Owner, 29.10.2026). Die Phasen 0 bis 2 sind seit 30.10.2026 auf dem Server umgesetzt. Seit dem 30.10.2026, 10:47 Uhr, laufen Veröffentlichen, Schreibweg und Wächter grün aus dem Bauordner. Diese Spec betrifft den Teil von Phase 3, der in der Software liegt.

## Approval

- [x] Approved (Plan im Issue, Product Owner 29.10.2026)

## Purpose

Eine Instanz baut nur aus ihrem **Bauordner**. Das ist ein Klon des Reisen-Repos, der nur `main` spiegelt und den Menschen nie bearbeiten. Gearbeitet wird in einem normalen **Arbeitsordner** mit Branches. Bisher ließ sich `deploy.sh` oder `veroeffentlichen.sh` aus jedem Klon aufrufen, die Wurzel ergab sich dann aus dem Ordner, in dem das Skript lag. Ein Aufruf aus dem Arbeitsordner hätte die Seiten aus einem Branch oder einem halbfertigen Stand gebaut (Fehlgriff am 29.10.2026). Die Arbeitskopien (`arbeitskopie.sh`, Worktree `<Klon>-arbeit`) sind nach dem Umbau überflüssig.

## Source

- **Files:** `betrieb/gemeinsam.sh`, `betrieb/deploy.sh`, `betrieb/veroeffentlichen.sh`, `betrieb/einrichten.sh`, `betrieb/arbeitskopie.sh` (entfällt), `werkzeuge/karte-holen.sh`, `engine/schreiben.py` (nur Kommentare), `docs/betrieb.md`, `docs/werkzeuge.md`, `engine/tests/test_betrieb.py`
- **Identifier:** `nur_bauordner` (gemeinsam.sh)

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| systemd-Units aus `betrieb/vorlagen/` | Vorlage | setzen `FR_WURZEL` auf den Bauordner |
| `engine/schreiben.py` | Dienst | startet `veroeffentlichen.sh` mit `FR_WURZEL` |

## Scope

- Schutz etwa 15 Zeilen Shell, Tests etwa 60 Zeilen, Doku etwa 30 Zeilen geändert; `arbeitskopie.sh` entfällt.
- **Nicht im Scope:** der Server selbst (Worktrees abbauen, alten Ordner umwidmen), die Doku des Reisen-Repos der Instanz. Beides wird im Issue nachgehalten.

## Implementation Details

- `gemeinsam.sh` merkt sich vor dem Ermitteln der Wurzel, ob `FR_WURZEL` von außen kam. Die Funktion `nur_bauordner [--main]` bricht mit Exit 1 und einer Meldung auf stderr ab, wenn das nicht so ist. Mit `--main` bricht sie auch ab, wenn `HEAD` der Wurzel nicht der Branch `main` ist (auch bei losgelöstem `HEAD`).
- `deploy.sh` ruft `nur_bauordner --main` vor jeder Wirkung auf.
- `veroeffentlichen.sh` ruft `nur_bauordner` auf. Steht der Ordner nicht auf `main`, bleibt es beim Überspringen mit Exit 0 wie bisher: Der Lauf merkt sich nichts, berührt den Erfolgsstempel nicht, und die Überwachung meldet einen anhaltenden Zustand.
- Andere Skripte (`freischalten.sh`, `waechter.sh`, `einrichten.sh`, Werkzeuge) behalten die Ermittlung der Wurzel aus dem Submodul. Sie bauen keine Seiten aus dem Stand des Ordners.
- Zurückrollen einer Seite geschieht künftig per `git revert` auf `main` (über einen PR), danach veröffentlicht der Timer. Ein `git checkout <commit>` im Bauordner entfällt, das widerspräche „spiegelt nur main“.
- Grundkarten liegen nicht im Repo. Neue holt man mit `FR_WURZEL=<Bauordner> frieda/werkzeuge/karte-holen.sh <reise>` direkt in den Bauordner (ignorierte Dateien, `main` bleibt sauber), danach `FR_WURZEL=<Bauordner> frieda/betrieb/veroeffentlichen.sh --immer`.
- Begriffe: „Veröffentlichungsordner“ heißt in Code und Doku jetzt „Bauordner“. Statt „Arbeitskopien“ heißt es „Arbeitsordner“. Die Arbeitskopie des Schreibwegs (`<Bauordner>-schreiben-<reise>`) bleibt, wie sie ist.
- Keine Serverpfade in diesem Repo, nur Platzhalter.

## Expected Behavior

- **Input:** Aufruf von `deploy.sh` oder `veroeffentlichen.sh`.
- **Output:** Kommt der Aufruf aus einer Unit, aus dem Schreibweg oder von Hand mit `FR_WURZEL`, läuft er wie bisher. Ohne `FR_WURZEL` folgt Exit 1 mit dem Hinweis `FR_WURZEL=<Bauordner>`. `deploy.sh` auf einem anderen Branch als `main` endet mit Exit 1, ohne zu bauen.
- **Side effects:** keine.

## Prüfstelle ADR-0001

Reiner Betrieb: keine Grundform, keine Art, kein Merkmal, kein KI-Lauf, nichts Reisespezifisches. Nichts Instanzspezifisches: Der Bauordner kommt aus den Units der Instanz.

## Known Limitations

- Wer `FR_WURZEL` von Hand auf einen Arbeitsordner setzt, der auf `main` steht, kann immer noch von dort veröffentlichen. Der Schutz fängt den Fehlgriff ab, nicht die Absicht.

## Acceptance Criteria

- **AC-1:** Given ein Aufruf von `deploy.sh <reise>` ohne `FR_WURZEL` (Software als Submodul eines Reisen-Repos auf `main`) / When er läuft / Then Exit 1, stderr nennt `FR_WURZEL`, keine Seite liegt im Zielordner.
- **AC-2:** Given ein Aufruf von `veroeffentlichen.sh` ohne `FR_WURZEL` / When er läuft / Then Exit 1, stderr nennt `FR_WURZEL`, kein `deploy.sh`, kein Stand, kein Stempel.
- **AC-3:** Given `FR_WURZEL` gesetzt, der Ordner auf einem anderen Branch als `main` oder mit losgelöstem `HEAD` / When `deploy.sh <reise>` läuft / Then Exit 1, die Meldung nennt `main`, keine Seite liegt im Zielordner.
- **AC-4:** Given `FR_WURZEL` gesetzt und der Ordner auf `main` / When `deploy.sh` oder `veroeffentlichen.sh` läuft / Then alles wie bisher (bestehende Tests grün).
- **AC-5:** Given die Software / Then `betrieb/arbeitskopie.sh` gibt es nicht mehr, und kein Text in `docs/`, `betrieb/`, `werkzeuge/` und `engine/` außerhalb von `docs/artifacts`, `docs/specs`, `docs/context` nennt sie noch.
- **AC-6:** Given jede dokumentierte Handzeile, die `deploy.sh` oder `veroeffentlichen.sh` aufruft (`docs/*.md`, die Hinweise in `einrichten.sh` und `karte-holen.sh`) / Then sie setzt `FR_WURZEL=`.
- **AC-7:** Given `docs/betrieb.md` / Then die Tabelle der Instanz nennt Bauordner und Arbeitsordner, „Zurückrollen“ beschreibt `git revert` auf `main` statt `git checkout`, und „Veröffentlichungsordner“ kommt nicht mehr vor.
