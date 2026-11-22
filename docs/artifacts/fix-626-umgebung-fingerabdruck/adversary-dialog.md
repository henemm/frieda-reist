# Adversary Dialog — fix-626-umgebung-fingerabdruck
Spec: docs/specs/betrieb/umgebung-fingerabdruck-626.md
Datum: 2026-11-22 21:55

## Checkliste
- [x] **AC-1:** Given ein gescheiterter Deploy der Dienste (Lauf 1) und unveränderte Umgebung / When Lauf 2 ohne `VF_UMGEBUNG` mit npm-Attrappe läuft / Then steht im Protokoll `Known red state … skipped` und es gibt insgesamt genau einen `--dienste`-Aufruf (Test 1).
- [x] **AC-2:** Given eine Rot-Datei der Art `reise` und unveränderte Umgebung / When erneut veröffentlicht wird / Then wird der rote Stand übersprungen (Test 2).
- [x] **AC-3:** Given eine geänderte Playwright-Version unter `<FR_DIENST>/playwright` / When der rote Stand geprüft wird / Then meldet das Skript `environment changed` (Test 3).
- [x] **AC-4:** Given `VF_UMGEBUNG` gesetzt / When der Fingerabdruck berechnet wird / Then gilt nur dieser Wert (Test 4).
- [x] **AC-5:** Given keine Playwright-Kopie und kein `PLAYWRIGHT_MODUL` / When der Fingerabdruck berechnet wird / Then bricht nichts ab (Test 5).
- [x] **AC-6:** Given der Stand der Änderung / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then sind alle Tests grün, auch F002 ohne Verdecken durch `VF_NPM`, und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) sind grün.
- [x] **AC-7:** Given der Kopfkommentar von `umgebung_stand` / When er gelesen wird / Then nennt er die Quelle der Playwright-Version und dass sie nicht von der Reihenfolge im Lauf abhängt.

## Dialog

### Runde 1
**Adversary:** Diff gelesen (pw_modul_einstellung Zeile 61, umgebung_stand Zeilen 375-388). Gezielter Lauf `-k "626 or f002"`: 8 passed; ganze Datei test_software_weg_454.py: 44 passed (Nachweis: adversary-test-output.txt). Gesamtlauf aus test-green-output.txt: 3488 passed. Frage: Wird pw_modul_einstellung nach dem Laden der Einstellungen gesetzt? Antwort: gemeinsam.sh (Zeile 60, per source) lädt die Einstellungen vor Zeile 61; FR_DIENST hat Vorgabe in gemeinsam.sh:91.
**Implementierer:** (Gerüst, keine Antwort nötig)

### Runde 2
**Adversary:** Randfälle per isolierter Ausführung von umgebung_stand unter `set -euo pipefail`: FR_DIENST leer -> rc=0; PLAYWRIGHT_MODUL auf nicht existente Datei -> rc=0 (grep scheitert, `|| true`). Unterschalen: pw_modul_einstellung ist eine normale Shell-Variable, Unterschalen (software_pruefen, Zeile 662) erben sie; abhaengigkeiten_playwright setzt sie nicht, daher in Eltern und Kind gleicher Wert. Beobachtung: Ist PLAYWRIGHT_MODUL eingestellt, wird die Kopie unter FR_DIENST ignoriert (kein Rückfall); beide Seiten des Vergleichs nutzen dieselbe Regel, daher stabil. deploy.sh und konnektor.py unverändert (git status: nur veroeffentlichen.sh modifiziert). F002 ist grün; bei AC-1 durch test_626_rot_bleibt_uebersprungen_mit_npm mit npm-Attrappe abgedeckt (grün).
**Implementierer:** (Gerüst)

### Runde 3
**Adversary:** Nachprüfung nach rotem CI-Lauf: .github/workflows/tests.yml setzt PLAYWRIGHT_MODUL in GITHUB_ENV, die Tests test_626_* erbten es über sw.env (SAUBER filtert nur FR_/VF_). Fix: Fixture mit_npm (engine/tests/test_software_weg_454.py:744) und Test 5 (:832) entfernen die Variable. `PLAYWRIGHT_MODUL=<attrappe 9.9.9> pytest engine/tests/test_software_weg_454.py`: 44 passed; ohne Variable: 44 passed. Das Ausblenden schwächt keinen Test: AC-3/AC-4 prüfen erst dadurch die Kopie unter <FR_DIENST>/playwright, AC-5 stellt die Vorbedingung her statt sie nur anzunehmen. Andere Tests setzen oder blenden die Variable selbst aus (test_seite_ansehen.py, test_betrieb.py:662). CI des PR danach: tests (leer), tests (instanz), gitleaks grün.
**Implementierer:** Übernommen; Hinweis (zentral im Fixture sw ausblenden) als F002 LOW vermerkt, keine Änderung nötig.

## Findings
Finding:
  ID: F002
  Severity: LOW
  Category: maintainability
  Code reference: engine/tests/test_software_weg_454.py:744
  Description: PLAYWRIGHT_MODUL wird je Test ausgeblendet statt zentral im Fixture sw.
  Spec requirement: AC-3, AC-5 — Tests ohne eingestelltes PLAYWRIGHT_MODUL
  Conflict: Kein Verstoß; beide betroffenen Stellen blenden aus, alle Tests grün.
  Remediation: keine nötig.

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:381
  Description: Ist PLAYWRIGHT_MODUL in der Einstellung gesetzt, aber die Datei fehlt, bleibt der Playwright-Teil leer; die Kopie unter FR_DIENST wird nicht als Rückfall genutzt.
  Spec requirement: AC-5 — kein Abbruch bei fehlender Datei
  Conflict: Kein Verstoß; Verhalten stabil und gleich wie vor der Änderung. Nur Hinweis.
  Remediation: keine nötig.

## Confirmations
Confirmation:
  AC: AC-1
  Code reference: betrieb/veroeffentlichen.sh:381
  Evidence: Fingerabdruck liest Version aus Einstellung oder Kopie, unabhängig von abhaengigkeiten_playwright; engine/tests/test_software_weg_454.py:770 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_software_weg_454.py:782
  Evidence: Art reise gleicher Fingerabdruck, Test grün (rot_schreiben und rot_erneut_pruefen nutzen dieselbe Funktion).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_software_weg_454.py:808
  Evidence: geänderte package.json-Version führt zu "environment changed"; grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: betrieb/veroeffentlichen.sh:376
  Evidence: VF_UMGEBUNG-Zweig steht vor allem anderen; engine/tests/test_software_weg_454.py:818 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_software_weg_454.py:828
  Evidence: ohne Playwright kein Abbruch, rot übersprungen; manuell set -euo pipefail mit leerem FR_DIENST und falschem Modulpfad rc=0.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/tests/test_software_weg_454.py:770
  Evidence: 3488 passed im Gesamtlauf (test-green-output.txt), 44 passed in der Datei von mir erneut. Offen/außerhalb dieses Dialogs: CI-Pflichtprüfungen (tests (leer), tests (instanz), gitleaks) folgen erst bei Auslieferung.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/tests/test_software_weg_454.py:840
  Evidence: Kopfkommentar betrieb/veroeffentlichen.sh:377-379 nennt #626, Quelle <FR_DIENST>/playwright und Reihenfolge im Lauf; Test grün.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
VERDICT: VERIFIED
Tests: 44 passed (Datei), 3488 passed (Gesamtlauf laut Nachweis), 0 failed. Edge cases: none broken. Regressions: none. Checklist: 7/7 (AC-6 CI-Pflichtprüfungen offen bis Auslieferung).

## Geprüfte Dateien

- sha256:220053c1b1f3d74dda1b85491e31dc02ca396b16e8b9c879c8bcb55fed7e3399  betrieb/veroeffentlichen.sh
- sha256:b8b434bc7dc2f72dd654ee3c4cdb1b293c381719e341789cc04d8a7de32150f8  engine/tests/test_software_weg_454.py

## Prüfbasis

- base: a0af665793aa742a870a5b1399ca360f5dd2acaf
- blob:1a222e6bb2eda1b0b40d3abafa9b79644dd5bf2a  betrieb/veroeffentlichen.sh
- blob:427eaad5c241884cf826546719fbcf591370829c  engine/tests/test_software_weg_454.py

## Geprüfte Dateien

- sha256:220053c1b1f3d74dda1b85491e31dc02ca396b16e8b9c879c8bcb55fed7e3399  betrieb/veroeffentlichen.sh
- sha256:b8b434bc7dc2f72dd654ee3c4cdb1b293c381719e341789cc04d8a7de32150f8  engine/tests/test_software_weg_454.py

## Prüfbasis

- base: a0af665793aa742a870a5b1399ca360f5dd2acaf
- blob:1a222e6bb2eda1b0b40d3abafa9b79644dd5bf2a  betrieb/veroeffentlichen.sh
- blob:427eaad5c241884cf826546719fbcf591370829c  engine/tests/test_software_weg_454.py

## Geprüfte Dateien

- sha256:220053c1b1f3d74dda1b85491e31dc02ca396b16e8b9c879c8bcb55fed7e3399  betrieb/veroeffentlichen.sh
- sha256:95b88c7b0e8359580643f8cfafbf29dd1ef5eb02de9cae21b9e39167aa456bf5  engine/tests/test_software_weg_454.py

## Prüfbasis

- base: f2a935715ab2ff4733a57e890fe72386b447eb7a
- blob:1a222e6bb2eda1b0b40d3abafa9b79644dd5bf2a  betrieb/veroeffentlichen.sh
- blob:1ff18183d7194ab8e268e0c040f525aaf99cfd4f  engine/tests/test_software_weg_454.py
