# Adversary Dialog — schreibweg-zeitgrenzen-118-121
Spec: docs/specs/betrieb/schreibweg-zeitgrenzen.md
Datum: 2026-10-29

Verlauf: Die erste Prüfung (Prüfer 1) ergab BROKEN (F001 HIGH, F002 und F003 MEDIUM, F004 LOW). Der Entwickler hat alle vier behoben, jeweils mit neuem Test. Die zweite, unabhängige Prüfung (Prüfer 2, unten) ergab VERIFIED.

## Checkliste
- [x] **Input:** ein Schreibvorgang (`werkzeug`, `anfrage`) für eine Reise.
- [x] **Output:** 200/422 wie bisher; bei Fristablauf eine der Antworten aus der Meldungstabelle oben. Die Antwort kommt immer vor Ablauf von `proxy_read_timeout` (höchstens 28 s). Worst Case gemessen: 28,04 s.
- [x] **Side effects:** Protokollzeilen (`journalctl -u <instanz>-schreiben`); je Reise eine Sperrdatei und eine Arbeitskopie; eine Kennungszeile in jeder Commit-Nachricht eines Eintrags; Veröffentlichen läuft mit niedriger Priorität.
- [x] **AC-1:** Konstanten 25 + 3 < 30, `ZEIT_SPERRE` ≤ `ZEIT_GESAMT`. Code reference: engine/schreiben.py:57. Test: engine/tests/test_schreiben.py:920.
- [x] **AC-2:** Prüfung nicht möglich → 504 „bitte prüfen“, Zeile `Zeit … 504: abgebrochen, ungeprüft`. Code reference: engine/schreiben.py:1864. Test: engine/tests/test_schreiben.py:368.
- [x] **AC-3:** Hängendes `vorbereiten()` → 504 „nicht eingetragen“ in der Zeit, ohne Ergebnisprüfung. Code reference: engine/schreiben.py:1688. Test: engine/tests/test_schreiben.py:928.
- [x] **AC-4:** Sperre je Reise, nach `ZEIT_SPERRE` 429, andere Reise unbehindert (Probe: zwei Reisen parallel, vier Runden, alle 200). Code reference: engine/schreiben.py:1830. Test: engine/tests/test_schreiben.py:326.
- [x] **AC-5:** Zeile `Abgelehnt <werkzeug> 422: <Grund>`, einzeilig, ≤ 200 Zeichen. Code reference: engine/schreiben.py:1823. Test: engine/tests/test_schreiben.py:343.
- [x] **AC-6:** `Nice=10`, `IOSchedulingClass=best-effort`, `IOSchedulingPriority=7`; Startbefehl mit `nice` und `ionice`. Code reference: betrieb/vorlagen/veroeffentlichen.service:20. Code reference: engine/schreiben.py:1795. Tests: engine/tests/test_betrieb.py:586, engine/tests/test_schreiben.py:941.
- [x] **AC-7:** Kennung in Commit, Ergebnisprüfung (Tri-State), Prozessgruppe beendet. Code reference: engine/schreiben.py:1772. Code reference: engine/schreiben.py:1847. Code reference: engine/schreiben.py:80. Tests: engine/tests/test_schreiben.py:956, engine/tests/test_schreiben.py:978.
- [x] **AC-8:** Genau eine Zeile `Fertig <werkzeug> <code> in <s> s` für jeden Ausgang, im `finally`. Code reference: engine/schreiben.py:1890. Test: engine/tests/test_schreiben.py:994.

## Dialog

### Runde 1
**Adversary (Prüfer 2):** Alle 8 ACs plus die vier Fixes der ersten Prüfung mit eigenen Proben prüfen.
**Implementierer (Belege):**
- Tests: 81 passed (Schreib- und Betriebstests), voller Lauf 568 passed, 0 failed.
- F001 behoben: Veröffentlichen mit stdin/stdout/stderr auf DEVNULL (engine/schreiben.py:1795). Probe: Stummel mit Ausgabe und 40 s Schlaf → Antwort 200 nach 0,44 s, keine Abbruch-Zeile. Test: engine/tests/test_schreiben.py:1016.
- F002 behoben: `except Exception` → 500 plus Zeile `Fehler … 500: …`, `Fertig` im `finally` (engine/schreiben.py:1877). Test: engine/tests/test_schreiben.py:1046.
- F003 behoben für den Worktree: `git_sperren_raeumen` (engine/schreiben.py:1894), `index.lock` und `HEAD.lock` entfernt, Vorgang liefert 200. Test: engine/tests/test_schreiben.py:1058.
- F004 behoben: Rückfall ohne `nice`/`ionice` per `shutil.which` und `try/except OSError`. Test: engine/tests/test_schreiben.py:1072.

### Runde 2
**Adversary (Prüfer 2):** Nachbohren an Aufräumfunktion, DEVNULL, Frist-Arithmetik, Regressionen, Ausnahme nach dem Eintragen.
**Implementierer (Belege):**
- (a) Aufräumen löscht nur `*.lock` direkt im eigenen Worktree-git-Ordner, nur unter der gehaltenen Reisesperre; Reisename per `REISE_MUSTER` geprüft; das Veröffentlichen arbeitet im Hauptordner.
- (b) DEVNULL: Die Spec verlangt keine Ausgabe des Veröffentlichens im Protokoll; Begründung in docs/betrieb.md:89. Code reference: docs/betrieb.md:66.
- (c) Worst Case (push hängt, fetch hängt): 28,04 s, 504 „ungeprüft“, `Fertig … 504 in 28.0 s`, keine Zombies.
- (d) Meldungstexte stimmen mit der Tabelle überein; keine Regressionen.
- (e) Ausnahme nach dem Eintragen: 500 mit Protokollzeilen, Antwort wird ausgeliefert.
- (f) Doppelter `import shutil` (engine/schreiben.py:1478) ist harmlos.

### Runde 3 (Nachprüfung nach Rebase auf origin/main)
**Adversary (Prüfer 3):** Enthält der zusammengeführte Stand noch genau die geprüfte Umsetzung und nichts Fremdes?
**Implementierer (Belege):**
- Diff gegen HEAD: 5 Dateien (+279/−26), nur Zeitgrenzen-Umsetzung. Von main stammt nur die Aktion `kategorie_definieren` in `AKTIONEN`, sie steht unverändert neben den Konstanten.
- Alle Funktionen, Meldungstexte und Protokollzeilen sind vollständig vorhanden; keine Konfliktmarker in den Projektdateien.
- Tests: 120 passed (Schreib-, Betriebs-, Konnektor-Tests); voller Lauf nach dem Rebase 572 passed.
- Frist: 25 + 3 = 28 s < `proxy_read_timeout 30s`; `ZEIT_ANWENDEN` nur noch in Spec und Kontextdokument (historisch).

## Findings (offen, nicht blockierend)
- **F005 (MEDIUM, edge_case):** Stirbt ein `git fetch` im gemeinsamen Repo durch SIGKILL während der Ref-Aktualisierung, kann `refs/remotes/origin/main.lock` liegen bleiben; dann 503 für alle Reisen bis zum manuellen Löschen. Zeitfenster klein. Remediation: Folge-Issue. Evidence: Probe `test_gemeinsame_sperre_bei_neuem_stand`. Code reference: engine/schreiben.py:1894
- **F006 (LOW, anti_pattern):** Ausgabe des vom Schreibweg angestoßenen Veröffentlichens geht nach /dev/null; Fehlläufe sind nur über Timer und Journal sichtbar. Dokumentiert. Code reference: engine/schreiben.py:1795
- **F007 (LOW, edge_case):** `vorgang_eingetragen` fängt `OSError` nicht; daraus wird die allgemeine 500-Meldung statt „bitte prüfen“. Remediation: `OSError` zu `None` zusammenfassen. Code reference: engine/schreiben.py:1847

## Bestätigungen

Code reference: engine/schreiben.py:1795
Code reference: engine/schreiben.py:1890
Code reference: engine/tests/test_schreiben.py:956
Code reference: engine/tests/test_betrieb.py:586
Code reference: betrieb/vorlagen/veroeffentlichen.service:20
Code reference: docs/betrieb.md:66

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
**VERIFIED**

Begründung: Alle 8 ACs sind mit Code, Tests und eigenen Proben belegt. Die vier Befunde der ersten Prüfung halten der erneuten Prüfung stand. Voller Lauf 568 passed. Schlechtester Pfad 28,04 s unter den 30 s von nginx. Offen sind nur F005 bis F007 außerhalb der Spec.

## Geprüfte Dateien

- sha256:bbb0f42df0f8a150b6d098055ed7fd73c679c27c4330683dcdbb81cdebc444ec  betrieb/vorlagen/veroeffentlichen.service
- sha256:4a79aa35d01a77957cdec963996a68b5340cc3b65c146165bc490a4835c7d12c  docs/betrieb.md
- sha256:cc01a8598bb79f42fc858a8b47f6403635f8ab04c41631599ef064f70b9f7205  engine/schreiben.py
- sha256:79228023ebb4945a01264febfe2219e8d5c396bf45fdfc54e2ed24895157afe2  engine/tests/test_betrieb.py
- sha256:f05e734a21601d6153a7cf55d8e21c88050ebbf4e504e35ee1ef2690ee8332ae  engine/tests/test_schreiben.py

## Prüfbasis

- base: 01397794652ccb9de830af5e60159f55537f25c0
- blob:fa2a3833fa6ddcbdacfb4de1158d1732830e9599  betrieb/vorlagen/veroeffentlichen.service
- blob:a9f3573853b26ffca71d247523631ac6b0ae46c5  docs/betrieb.md
- blob:839bc927713cd3cc32b288bf92ad0034338b0b40  engine/schreiben.py
- blob:28ad561c23815b41fc764506919872131b094ceb  engine/tests/test_betrieb.py
- blob:08966e59aa8605ae4f12a6a14325960dd77a6f6f  engine/tests/test_schreiben.py

## Geprüfte Dateien

- sha256:bbb0f42df0f8a150b6d098055ed7fd73c679c27c4330683dcdbb81cdebc444ec  betrieb/vorlagen/veroeffentlichen.service
- sha256:4a79aa35d01a77957cdec963996a68b5340cc3b65c146165bc490a4835c7d12c  docs/betrieb.md
- sha256:cc01a8598bb79f42fc858a8b47f6403635f8ab04c41631599ef064f70b9f7205  engine/schreiben.py
- sha256:79228023ebb4945a01264febfe2219e8d5c396bf45fdfc54e2ed24895157afe2  engine/tests/test_betrieb.py
- sha256:f05e734a21601d6153a7cf55d8e21c88050ebbf4e504e35ee1ef2690ee8332ae  engine/tests/test_schreiben.py

## Prüfbasis

- base: 01397794652ccb9de830af5e60159f55537f25c0
- blob:fa2a3833fa6ddcbdacfb4de1158d1732830e9599  betrieb/vorlagen/veroeffentlichen.service
- blob:a9f3573853b26ffca71d247523631ac6b0ae46c5  docs/betrieb.md
- blob:839bc927713cd3cc32b288bf92ad0034338b0b40  engine/schreiben.py
- blob:28ad561c23815b41fc764506919872131b094ceb  engine/tests/test_betrieb.py
- blob:08966e59aa8605ae4f12a6a14325960dd77a6f6f  engine/tests/test_schreiben.py

## Geprüfte Dateien

- sha256:bbb0f42df0f8a150b6d098055ed7fd73c679c27c4330683dcdbb81cdebc444ec  betrieb/vorlagen/veroeffentlichen.service
- sha256:be7851a8ab8810303ece96473fc4185daac37e51de6dd7c8ec5841f6b5537a89  docs/betrieb.md
- sha256:ffd0afa76240088f3fb1373709ad5a3aae9b9a70c153a53e37147a09e71aaa18  engine/schreiben.py
- sha256:79228023ebb4945a01264febfe2219e8d5c396bf45fdfc54e2ed24895157afe2  engine/tests/test_betrieb.py
- sha256:0d8a2bc664dc721ae8990fa6eeefdc244f7e8a742093be9b403f4bf2cc3c5f0a  engine/tests/test_schreiben.py

## Prüfbasis

- base: 270747e84961fd8efe9bf1e8f4b9424961cbe12b
- blob:fa2a3833fa6ddcbdacfb4de1158d1732830e9599  betrieb/vorlagen/veroeffentlichen.service
- blob:8172f1b4a9c50fee130d05d8f49dd43bdbca1d03  docs/betrieb.md
- blob:4dace7296bcf87c11e6dcb008e3a957685327326  engine/schreiben.py
- blob:28ad561c23815b41fc764506919872131b094ceb  engine/tests/test_betrieb.py
- blob:5c5bab74cca6279f8fef8ec585bf3274e8a94229  engine/tests/test_schreiben.py
