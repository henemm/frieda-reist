# Adversary Dialog — 161-software-nachziehen
Spec: docs/specs/betrieb/software-nachziehen-161.md
Datum: 2026-10-31 12:00

## Checkliste
- [x] **AC-1:** Given die Vorlage `betrieb/software-nachziehen.yml` / When sie als YAML geladen wird / Then sie hat die Auslöser `schedule` und `workflow_dispatch`, die Rechte `contents: write` und `issues: write`, und `concurrency` bricht nichts ab.
- [x] **AC-2:** Given der Testschritt (id `tests`) / When die Tests rot sind / Then hat er `continue-on-error: true`, der Schritt „Nach main übernehmen“ verlangt `steps.tests.outcome == 'success'`, der Issue-Schritt verlangt `== 'failure'` und endet mit `exit 1`.
- [x] **AC-3:** Given der Übernahme-Schritt / Then er setzt `github-actions[bot]` mit einer `users.noreply.github.com`-Adresse, der Commit-Text enthält eine Liste der Commits (`log` über `alt..neu`), es gibt eine Wiederholschleife mit `git rebase --abort`, und `--force` kommt in der ganzen Datei nicht vor.
- [x] **AC-4:** Given die Vorlage / Then sie enthält keine Angaben einer Instanz: kein `/srv/`, kein `/home/`, keine Domain außer `github.com`, keinen Namen eines Reisen-Repos.
- [x] **AC-5:** Given `docs/betrieb.md` / Then „Neue Instanz einrichten“ nennt `betrieb/software-nachziehen.yml`, `.github/workflows/` und die Rechte, und „Überwachung“ nennt den Rückstand gegen `main`.
- [x] **AC-7:** Given eingebundener Stand gleich `main` / When `check_frieda_software` läuft / Then ✓, `MONITOR_ERRORS` bleibt 0, die Merkdatei fehlt danach.
- [x] **AC-8:** Given Rückstand, zum ersten Mal gesehen / When der Check läuft / Then ✓ mit „Rückstand“, die Merkdatei nennt den eingebundenen Stand.
- [x] **AC-9:** Given Rückstand, Merkdatei mit demselben Stand älter als 6 h / When der Check läuft / Then ✗, die Meldung nennt die Stunden, `MONITOR_ERRORS` bleibt 0 (nicht kritisch).
- [x] **AC-10:** Given Merkdatei älter als 6 h, aber für einen anderen eingebundenen Stand (Bauordner ist vorgerückt) / When der Check läuft / Then ✓, die Zählung beginnt neu.
- [x] **AC-11:** Given `git ls-remote` scheitert / When der Check läuft / Then kein ✗ und kein Zustandswechsel (`alert_on_change` wird nicht gerufen), Statuszeile „nicht prüfbar“.
- [x] **AC-12:** Given die HEAD-Datei fehlt oder enthält keinen SHA / When der Check läuft / Then ✗ „Stand nicht lesbar“, nicht kritisch.

## Betriebsabnahme nach dem Merge (in /60-validate, nicht vor dem Merge beweisbar)
- **Input:** neuer Commit auf `main` dieses Repos.
- **Output:** innerhalb von etwa 30 Minuten ein Commit des Bots auf `main` des Reisen-Repos (bei Grün), danach Veröffentlichen. Bei Rot: ein Issue und eine Mail von GitHub. Bleibt der Rückstand länger als 6 h, meldet der Monitor ihn.
- **Side effects:** Label `software-nachziehen` im Reisen-Repo, Merkdatei im Zustandsordner des Monitors.
- **AC-6:** Given das Reisen-Repo der Instanz / When der PR mit der Vorlage zusammengeführt ist / Then die Datei dort ist inhaltlich gleich der Vorlage, `tests.yml` war grün, und #224 ist mit Verweis geschlossen.
- **AC-13:** Given der Check ist auf `main` des Infra-Repos / When `server-monitor.service` das nächste Mal läuft / Then das Journal zeigt die Zeile des Checks mit ✓, und `docs/monitoring.md` beschreibt ihn.

## Dialog

### Runde 1
**Adversary:** Beweise je AC. Tests: frieda-reist 68 passed (test_software_nachziehen.py + test_betrieb.py), henemm-infra 30 passed (tests/test_monitor_frieda*.py), 0 failed, 0 übersprungen.
- AC-1: Auslöser, Rechte, concurrency geladen und per Test geprüft.
- AC-2: `continue-on-error: true` am Schritt `tests`; Übernahme `outcome == 'success'`, Issue `outcome == 'failure'` plus `exit 1`. Semantik: bei continue-on-error bleibt `outcome` = failure, `conclusion` = success; die Wahl von `outcome` ist richtig.
- AC-3/AC-4: Bot-Name, noreply-Adresse, `log alt..neu`, Schleife mit `rebase --abort`, kein `--force`; keine Instanzangaben (nur die Bot-Domain, Ausnahme im Test eng gefasst).
- AC-5: Doku per Diff geprüft. AC-7..AC-12: je ein Test, plus eigene Codeprüfung.
- AC-6, AC-13: Betriebsabnahme nach Merge, offen.
**Implementierer:** keine Rückfragen (Spec und Code allein bewertet).

### Runde 2
**Adversary:** Nachbohren.
- `set -e`: monitor.sh setzt nur `set -uo pipefail` (Zeile 8), kein `-e`. `[ -f ] && read` bei leerer Merkdatei: read liefert 1, Variablen leer, Regex schlägt fehl, Zählung beginnt neu (in bash nachgestellt: leer, dann reset). Kein Absturz, kein unset-Fehler.
- HEAD-Datei mit `ref:`: Regex `^[0-9a-f]{40}$` scheitert, "nicht lesbar", nicht kritisch. Die echte HEAD-Datei im Bauordner enthält einen SHA und ist gleich main (ls-remote): AC-7 real stimmig.
- Leere ls-remote-Ausgabe oder Fehler: Regex scheitert, status_warn, kein alert_on_change (AC-11).
- Merkdatei: root, STATE_DIR 700 root; Format `<sha> <epoch>`; ungültige Epoche setzt neu.
- Präfix `frieda-reisen-` ist in NO_AGENT_PREFIXES; nicht kritisch laut Tests (MONITOR_ERRORS 0).
- Workflow: `fetch --unshallow ... || fetch` ist unter `bash -e` sicher. `merge-base --is-ancestor` im elif ist von errexit ausgenommen. `rebase --abort ... || true` und Schleife: `exit 0` im `if`, `exit 1` am Ende korrekt. Flacher Klon des Elternrepos beim pull --rebase: üblicher Fall, nicht live bewiesen (siehe AC-13).
- Issue-Schritt: fehlendes Label bei `issue list` liefert leer, `|| echo 0` fängt Fehler. Folge: Bei dauerhaft roten Tests endet jeder 30-Minuten-Lauf rot (viele Mails), Issue nur einmal. Spec-gemäß, nur Hinweis.
**Implementierer:** keine Rückfragen.

### Runde 3
**Adversary:** F001 nachgeprüft. Zeile 1768 `[ "$STATUS_MODE" = true ] || rm -f "$merk"` und Zeile 1776 `[ "$STATUS_MODE" = true ] || echo ... > "$merk"`: Merkdatei wird nur im normalen Lauf angefasst. Angriffe: (1) Normaler Modus, gleicher Stand: Merkdatei wird gelöscht (gewollt, AC-7). (2) Status-Modus, gleicher Stand: Datei bleibt unverändert (Test test_status_gleicher_stand). (3) Status-Modus, Rückstand erstmals: keine Datei geschrieben, age = 0, Statuszeile ok; bei alter Datei 7 h Statuszeile fail ohne Schreiben (test_status_rueckstand). (4) Status-Modus mit Netzfehler oder unlesbarer HEAD: kein State (test_status_netzfehler_und_nicht_lesbar). `||`-Form ist ohne `-e` unkritisch. Tests: 33 passed in tests/test_monitor_frieda*.py. F001 ist behoben.
Zusätzlich zitiert: die Ausnahme für die Bot-Domain in test_vorlagen_ohne_werte_einer_instanz.
Code reference: /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/engine/tests/test_betrieb.py:1059
Code reference: /home/hem/henemm-infra-wt-frieda-software/scripts/monitor.sh:1768
**Implementierer:** F001 behoben, siehe Runde 3.

Finding (behoben in Runde 3):
  ID: F001
  Severity: LOW
  Category: anti_pattern
  Code reference: /home/hem/henemm-infra-wt-frieda-software/scripts/monitor.sh:1776
  Description: Im Status-Modus schreibt und löscht der Check die Merkdatei (Zeilen 1768, 1776), obwohl alert_on_change dort bewusst keinen Zustand schreibt (Zeile 323). Ein manueller Status-Aufruf als Nicht-root gibt eine Permission-Fehlermeldung aus.
  Spec requirement: AC-8 — Merkdatei nennt den Stand (kein Verbot im Status-Modus)
  Conflict: Inkonsistent zur Konvention des Monitors; kein Spezifikationsbruch. Folge harmlos.
  Remediation: Schreiben und Löschen mit `[ "$STATUS_MODE" = false ]` absichern.

Confirmation:
  AC: AC-1
  Code reference: /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/betrieb/software-nachziehen.yml:12
  Evidence: schedule, workflow_dispatch, permissions contents/issues write, concurrency cancel-in-progress false.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/betrieb/software-nachziehen.yml:74
  Evidence: continue-on-error true, Bedingungen Zeilen 78 und 108, exit 1 Zeile 125.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/betrieb/software-nachziehen.yml:97
  Evidence: Bot-Identität 92-93, Liste 90, Schleife mit rebase --abort 101, kein --force.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/engine/tests/test_software_nachziehen.py:58
  Evidence: Test auf /srv/, /home/, Domains; Ausnahme der Bot-Domain in /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/engine/tests/test_betrieb.py:1059 eng gefasst.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/docs/betrieb.md:162
  Evidence: Überwachungsabsatz (Rückstand gegen main) und Einrichtschritt Zeile 174 mit Datei, .github/workflows/ und Rechten.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: /home/hem/henemm-infra-wt-frieda-software/scripts/monitor.sh:1766
  Evidence: Gleich: rm -f Merkdatei, alert ok, status_ok.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: /home/hem/henemm-infra-wt-frieda-software/tests/test_monitor_frieda_software.py:59
  Evidence: Erstsicht schreibt Merkdatei mit Stand, ok mit Rückstand.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: /home/hem/henemm-infra-wt-frieda-software/scripts/monitor.sh:1781
  Evidence: Rückstand über 6 h: fail mit Stunden, Präfix frieda-reisen- nicht kritisch.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: /home/hem/henemm-infra-wt-frieda-software/scripts/monitor.sh:1774
  Evidence: Anderer eingebundener Stand setzt die Merkdatei neu.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: /home/hem/henemm-infra-wt-frieda-software/scripts/monitor.sh:1763
  Evidence: ls-remote-Fehler: status_warn und return ohne alert_on_change.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: /home/hem/henemm-infra-wt-frieda-software/scripts/monitor.sh:1755
  Evidence: HEAD fehlt oder kein SHA: fail nicht lesbar.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: /home/hem/henemm-infra-wt-frieda-software/docs/monitoring.md:99
  Evidence: Doku vorhanden, Check in der Aufrufliste (monitor.sh:2017). Journal-Zeile nach Merge: offen, nach Merge (Betriebsabnahme). AC-6 ebenso offen, nach Merge.
  Status: CONFIRMED


## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 68 passed (frieda-reist) + 33 passed (henemm-infra), 0 failed, 0 übersprungen. AC-1..5 und 7..12 bewiesen; AC-6 und AC-13 (Live) offen nach Merge, kein Defekt. F001 LOW behoben und in Runde 3 bestätigt.

## Geprüfte Dateien

- sha256:240a075437f55cf0d7d34c37a24458a1d7f5d97bd61c91b3adb05d22567a8c22  /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/betrieb/software-nachziehen.yml
- sha256:6d699a6e3ff8d47fb12954a9d4993848e731507fb5bc0515fee52cf85f2ef121  /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/docs/betrieb.md
- sha256:d3e856404f766d745738e1c52e80df9ae2bd636921cc42ff5c2c10b5ed474c77  /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/engine/tests/test_betrieb.py
- sha256:dcf8130f92632ec56dce764be0a13d470fbf93a80269a84882c7e9bc81cd91f3  /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/engine/tests/test_software_nachziehen.py
- sha256:d538b92806d341fda1e73136ab2ad1d6606dfcafe7418503d11eec0a4e0055b9  /home/hem/henemm-infra-wt-frieda-software/docs/monitoring.md
- sha256:079879b1e3b12bcfacfbc913d01e1cc819c8191651f692db2670ef2a8fb2487d  /home/hem/henemm-infra-wt-frieda-software/scripts/monitor.sh
- sha256:e38b68136e3ff41e1742457c72ba3be32a1167cabe3c0e53c76c4783112b8674  /home/hem/henemm-infra-wt-frieda-software/tests/test_monitor_frieda_software.py

## Prüfbasis

- base: 1e983e1a8994836959a57ac44f64341a0e975898
- blob:c7072c7ac5c75c2eb98a45e8a943f4d5cfb89b32  /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/betrieb/software-nachziehen.yml
- blob:dce8d63d3886b9690e1bf7100b71d0ff01e96729  /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/docs/betrieb.md
- blob:27d016ba3aa706dee9bcb8b4ef367e93debe84b4  /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/engine/tests/test_betrieb.py
- blob:d69ebea8937af310b934ccc0bdef9736bb4f3242  /home/hem/frieda-reist/.claude/worktrees/imperative-scribbling-goose/engine/tests/test_software_nachziehen.py
