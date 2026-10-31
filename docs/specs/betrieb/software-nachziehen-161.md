---
entity_id: software-nachziehen-161
type: module
created: 2026-10-31
updated: 2026-10-31
status: draft
version: "1.0"
tags: [betrieb, submodul, github-actions, ueberwachung]
---

# Neue Software automatisch ins Reisen-Repo nachziehen (#161)

Workflow: `161-software-nachziehen` · Grundlage: `docs/context/software-nachziehen-161.md` · Der Product Owner hat am 31.10.2026 entschieden, dass alle Teile in dieser Sitzung erledigt werden, auch die in den anderen Repos.

## Approval

- [ ] Approved

## Purpose

Neue Software-Stände kommen ohne Handarbeit in den Betrieb einer Instanz. Das geschieht nur bei grünen Tests. Bei Rot wird es sichtbar (Issue), und ein Rückstand fällt der Überwachung auf. Drei Teile:

1. **Vorlage** `betrieb/software-nachziehen.yml` in diesem Repo, allgemein und ohne Angaben einer Instanz, beschrieben in `docs/betrieb.md`.
2. **Instanz:** Der laufende Workflow im Reisen-Repo bekommt dieselben Korrekturen und ist danach eine Kopie der Vorlage. Das behebt dort #224: Das Issue bei roten Tests wurde nie angelegt.
3. **Überwachung:** ein Teil-Check im Monitor der Instanz (eigenes Infra-Repo). Er meldet, wenn der Software-Stand im Bauordner länger als 6 h hinter `main` dieses Repos liegt.

## Source

- **Files:** `betrieb/software-nachziehen.yml` (neu), `docs/betrieb.md`, `engine/tests/test_betrieb.py`; im Reisen-Repo der Instanz `.github/workflows/software-nachziehen.yml`; im Infra-Repo `scripts/monitor.sh`, `tests/test_monitor_frieda_software.py` (neu), `docs/monitoring.md`
- **Identifier:** Workflow „Software nachziehen“, Teil-Check `check_frieda_software`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`) | Dienst | führt den Workflow im Reisen-Repo aus |
| `gh` im Runner | Werkzeug | legt das Issue bei roten Tests an |
| `git ls-remote` | Werkzeug | liest den Stand von `main` ohne API-Limit |
| `alert_on_change`, `status_ok/fail` (Monitor) | Shell-Funktionen | Meldung nur bei Zustandswechsel |

## Scope

- Vorlage etwa 110 Zeilen YAML, Doku etwa 15 Zeilen, Test etwa 50 Zeilen; Instanz-Workflow: Ersatz durch die Vorlage; Monitor-Check etwa 45 Zeilen plus Test etwa 90 Zeilen und eine Doku-Zeile.
- **Nicht im Scope:** Änderungen an `veroeffentlichen.sh` (bleibt die zweite Prüfung), `submodule update --remote` auf dem Server (verworfen, siehe Issue), Renovate oder Dependabot.

## Implementation Details

**Vorlage `betrieb/software-nachziehen.yml`** (Basis: laufende Fassung der Instanz)
- Auslöser `schedule` (alle 30 Minuten) und `workflow_dispatch`; `permissions: contents: write, issues: write`; `concurrency` ohne Abbruch.
- Schritt „Neuer Stand?“: alt = eingebundener Stand, neu = `origin/main` des Submoduls. Nur vorwärts: Ist alt kein Vorfahre von neu, wird nichts übernommen (Warnung).
- Testschritt `python -m pytest -q -rs engine/tests tests` mit **`continue-on-error: true`**, damit die Schritte danach `steps.tests.outcome` auswerten können (Fix #224).
- Commit als `github-actions[bot]` mit der noreply-Adresse. Betreff: `Software auf Stand <kurz> (automatisch)`. Im Text eine Zeile je Commit seit dem alten Stand (`git log --format='- %h %s' alt..neu`).
- Push: bis zu drei Versuche `git pull --rebase origin main` und `git push origin HEAD:main`. Vor jedem neuen Versuch `git rebase --abort || true`. Nie `--force`. Scheitert alles, endet der Lauf rot. Der nächste Lauf versucht es wieder.
- Rote Tests: Issue mit dem Label `software-nachziehen` anlegen, wenn noch keines offen ist. Danach endet der Lauf rot (`exit 1`), GitHub meldet den Fehlschlag per Mail.
- Kein Instanzname, kein Server, keine Pfade außer `frieda/` und den Testordnern.

**Doku `docs/betrieb.md`**: In „Neue Instanz einrichten“ ein Schritt, der die Datei nach `.github/workflows/` des Reisen-Repos kopieren lässt und die Rechte nennt. Dazu ein kurzer Absatz unter „Überwachung“: Rückstand des Software-Stands gegen `main` prüfen, Schwelle etwa 6 h.

**Instanz:** Der Workflow im Reisen-Repo wird durch die Vorlage ersetzt (über einen PR, die Tests laufen dort mit), danach wird #224 geschlossen.

**Monitor `check_frieda_software`** (Infra-Repo, läuft als root alle 5 Minuten)
- Eingebundener Stand: Inhalt von `<bau>/.git/modules/frieda/HEAD` (40 Hex-Zeichen, sonst Fehler „Stand nicht lesbar“). Im Bauordner wird nichts geschrieben.
- Stand von `main`: `git ls-remote https://github.com/henemm/frieda-reist refs/heads/main`. Bei einem Netz- oder Lesefehler gibt es keinen Zustandswechsel (Statuszeile „nicht prüfbar“).
- Gleich: ok, die Merkdatei wird gelöscht.
- Verschieden: Die Merkdatei in `STATE_DIR` enthält `<eingebundener Stand> <epoch>`. Fehlt sie oder nennt sie einen anderen eingebundenen Stand, wird sie mit der jetzigen Zeit neu geschrieben. Liegt der Rückstand für diesen Stand länger als `FRIEDA_SOFTWARE_MAX_AGE` zurück (6 h), kommt ein fail mit Stunden und Hinweis („Workflow Software nachziehen rot oder Veröffentlichen hängt?“). Sonst ok, Statuszeile „Rückstand seit N min“.
- Schlüssel `frieda-reisen-software`, damit gelten `NON_CRITICAL_PREFIXES` und `NO_AGENT_PREFIXES` automatisch.
- Begründung der Messgröße (weicht vom Wortlaut des Issues ab): Commits kommen nach lokalem Vorspulen oft Stunden nach ihrem Commit-Datum auf `main`. Am Commit-Datum gemessen, käme der Alarm sofort. Gemessen wird deshalb, seit wann der Monitor den Rückstand je eingebundenem Stand sieht. Rückt der Bauordner vor, beginnt die Zählung neu. Ein Stand, der nicht vorwärts geht (diverged), rückt nie vor und meldet sich nach 6 h ebenfalls.

## Expected Behavior

- **Input:** neuer Commit auf `main` dieses Repos.
- **Output:** innerhalb von etwa 30 Minuten ein Commit des Bots auf `main` des Reisen-Repos (bei Grün), danach Veröffentlichen. Bei Rot: ein Issue und eine Mail von GitHub. Bleibt der Rückstand länger als 6 h, meldet der Monitor ihn.
- **Side effects:** Label `software-nachziehen` im Reisen-Repo, Merkdatei im Zustandsordner des Monitors.

## Prüfstelle ADR-0001

Reiner Betrieb: keine Grundform, keine Art, kein Merkmal, kein KI-Lauf, nichts Reisespezifisches. Die Vorlage enthält nichts Instanzspezifisches, die Werte einer Instanz bleiben in deren Repos.

## Known Limitations

- Ob der Workflow mit roten Tests das Issue wirklich anlegt, zeigt erst ein echter roter Lauf. Der Test hier prüft die Struktur (`continue-on-error`, Bedingungen).
- Der Monitor misst in seinem Takt von 5 Minuten. Fällt er selbst aus, beginnt die Zählung später.

## Acceptance Criteria

- **AC-1:** Given die Vorlage `betrieb/software-nachziehen.yml` / When sie als YAML geladen wird / Then sie hat die Auslöser `schedule` und `workflow_dispatch`, die Rechte `contents: write` und `issues: write`, und `concurrency` bricht nichts ab.
- **AC-2:** Given der Testschritt (id `tests`) / When die Tests rot sind / Then hat er `continue-on-error: true`, der Schritt „Nach main übernehmen“ verlangt `steps.tests.outcome == 'success'`, der Issue-Schritt verlangt `== 'failure'` und endet mit `exit 1`.
- **AC-3:** Given der Übernahme-Schritt / Then er setzt `github-actions[bot]` mit einer `users.noreply.github.com`-Adresse, der Commit-Text enthält eine Liste der Commits (`log` über `alt..neu`), es gibt eine Wiederholschleife mit `git rebase --abort`, und `--force` kommt in der ganzen Datei nicht vor.
- **AC-4:** Given die Vorlage / Then sie enthält keine Angaben einer Instanz: kein `/srv/`, kein `/home/`, keine Domain außer `github.com`, keinen Namen eines Reisen-Repos.
- **AC-5:** Given `docs/betrieb.md` / Then „Neue Instanz einrichten“ nennt `betrieb/software-nachziehen.yml`, `.github/workflows/` und die Rechte, und „Überwachung“ nennt den Rückstand gegen `main`.
- **AC-6:** Given das Reisen-Repo der Instanz / When der PR mit der Vorlage zusammengeführt ist / Then die Datei dort ist inhaltlich gleich der Vorlage, `tests.yml` war grün, und #224 ist mit Verweis geschlossen.
- **AC-7:** Given eingebundener Stand gleich `main` / When `check_frieda_software` läuft / Then ✓, `MONITOR_ERRORS` bleibt 0, die Merkdatei fehlt danach.
- **AC-8:** Given Rückstand, zum ersten Mal gesehen / When der Check läuft / Then ✓ mit „Rückstand“, die Merkdatei nennt den eingebundenen Stand.
- **AC-9:** Given Rückstand, Merkdatei mit demselben Stand älter als 6 h / When der Check läuft / Then ✗, die Meldung nennt die Stunden, `MONITOR_ERRORS` bleibt 0 (nicht kritisch).
- **AC-10:** Given Merkdatei älter als 6 h, aber für einen anderen eingebundenen Stand (Bauordner ist vorgerückt) / When der Check läuft / Then ✓, die Zählung beginnt neu.
- **AC-11:** Given `git ls-remote` scheitert / When der Check läuft / Then kein ✗ und kein Zustandswechsel (`alert_on_change` wird nicht gerufen), Statuszeile „nicht prüfbar“.
- **AC-12:** Given die HEAD-Datei fehlt oder enthält keinen SHA / When der Check läuft / Then ✗ „Stand nicht lesbar“, nicht kritisch.
- **AC-13:** Given der Check ist auf `main` des Infra-Repos / When `server-monitor.service` das nächste Mal läuft / Then das Journal zeigt die Zeile des Checks mit ✓, und `docs/monitoring.md` beschreibt ihn.
