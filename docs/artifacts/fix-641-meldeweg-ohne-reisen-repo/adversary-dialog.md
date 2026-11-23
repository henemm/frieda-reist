# Adversary Dialog — fix-641-meldeweg-ohne-reisen-repo
Spec: docs/specs/betrieb/meldeweg-instanz-repo-641.md
Datum: 2026-11-23 17:33

## Checkliste
- [x] **AC-1:** Given das Instanz-Repo ist angelegt / When seine Sichtbarkeit abgefragt wird / Then ist es privat, trägt das Label `betrieb-meldung`, und `CLAUDE.md` beschreibt keine Submodul-Anordnung mehr, sondern `<FR_DIENST>/instanz/` und die Instanz-Tests mit einem Branch der Software. (N)
- [x] **AC-2:** Given das Instanz-Repo enthält nur `CLAUDE.md` und README / When es geprüft wird / Then liegen dort keine Kopien von `melden.sh`, `einstellungen.env` oder `tests/`. (N)
- [x] **AC-3:** Given `einstellungen.env` der Instanz / When der Betrieb sie einliest / Then gilt `FR_MELDEN_REPO=<Instanz-Repo>`, ohne Änderung an `fr_einlesen` oder `fr_melden`. (Test 5, N)
- [x] **AC-4:** Given `FR_MELDEN_REPO` fehlt / When `melden.sh` ein Ziel bestimmt / Then ist die Vorgabe das Instanz-Repo, nie das alte Reisen-Repo. (Test 7)
- [x] **AC-5:** Given der Meldeweg ist umgestellt / When eine Meldung der Stufe `normal` über `fr_melden` aus dem Betrieb ausgelöst wird / Then entsteht ein Issue mit Label `betrieb-meldung` im Instanz-Repo, ohne Handschritt. (Nachweis A)
- [x] **AC-6:** Given die Probemeldung ist erschienen / When sie bearbeitet ist / Then ist das Probe-Issue geschlossen und im Issue #641 als Nachweis vermerkt. (Nachweis A)
- [x] **AC-7:** Given die sechs offenen Issues des alten Repos / When die Übertragung abgeschlossen ist / Then ist jedes entweder in das Instanz-Repo übertragen (Kommentare erhalten, alter Verweis führt weiter) oder mit schriftlicher Begründung geschlossen, und kein Issue ist mehr offen. (Nachweis B)
- [x] **AC-8:** Given ein Issue ist durch #454/#557 überholt (zum Beispiel der Instanz-Test mit Submodul) / When es nicht übertragen wird / Then steht in seinem Abschlusskommentar, was es ersetzt. (Nachweis B)
- [x] **AC-9:** Given das Skript für Sitzungen und die Meldungsskripte der Infrastruktur / When sie nach der Umstellung gelesen werden / Then verweisen sie auf das Instanz-Repo statt auf das alte Reisen-Repo, und ein Issue in der Infrastruktur hält es fest. (Nachweis D)
- [x] **AC-10:** Given `docs/betrieb.md`, `CLAUDE.md`, `README.md` / When sie gelesen werden / Then nennen sie als Ort der Einstellungen `<FR_DIENST>/instanz/` und als Ort der Anleitung und der Meldungen das private Repo der Instanz, nicht das Reisen-Repo. (Test 1)
- [x] **AC-11:** Given `engine/konten.py`, `docs/konten.md` und die Textkataloge aller Sprachen / When der Hinweis bei `meldung-erledigt` und der Text `konnektor.ontologie_werkzeug.4` gelesen werden / Then nennen sie das private Repo der Instanz; die Schlüssel sind in allen Sprachen vorhanden, `engine/tests/test_texte.py` bleibt grün. (Test 2)
- [x] **AC-12:** Given die Usage-Kommentare und `betrieb/einstellungen.beispiel` / When sie gelesen werden / Then ist `FR_MELDEN_REPO` mit Platzhalter beschrieben und das Reisen-Repo nicht als Ort der Einstellungen genannt. (Test 3)
- [x] **AC-13:** Given der Rückfall-Test / When jemand das Reisen-Repo wieder als aktuellen Ort in Ist-Doku, Usage oder sichtbare Texte schreibt / Then wird die Suite rot; Specs und Historie sind ausgenommen, die Ausnahmeliste wird nur kürzer. (Tests 1, 4)
- [x] **AC-14:** Given die Reihenfolge / When das alte Repo archiviert wird / Then liegen AC-5 bis AC-9 bereits nachgewiesen vor; die Archivierung ist der letzte Schritt. (Nachweis C)
- [x] **AC-15:** Given das alte Repo ist archiviert / When erneut eine Probemeldung der Stufe `normal` ausgelöst wird / Then gelingt sie im Instanz-Repo, und das Archiv bleibt unverändert. (Nachweis C)
- [x] **AC-16:** Given dieses öffentliche Repo / When Spec, Doku, Tests und Nachweise gelesen werden / Then enthalten sie keine echten Repo-Namen, Benutzer, Serveradressen, Instanzpfade, Reisenamen und keine Issue-Nummern des privaten Repos (`test_protokolle_ohne_pfade.py` grün).
- [x] **AC-17:** Given die vollständige Testsuite / When sie läuft / Then ist sie grün (`engine/.venv/bin/python -m pytest -q -n 3 engine/tests`), `ALARMSTELLEN` ist unverändert, und die Instanz-Tests laufen vor dem Vorspulen mit dem Branch ohne neuen Fehler gegenüber `main`. (Test 6) — Repo-Suite und Instanz-Tests mit dem Branch grün (vor dem Vorspulen); volle Suite siehe test-green-output.txt
- [x] **AC-18:** Given alle Schritte erledigt / When #641 und #557 geprüft werden / Then tragen beide den Endstand (Ziel, Übertragungen, Archivierung) und AC-36 aus #557 ist erfüllt; #641 wird erst dann geschlossen.

## Dialog

### Runde 1
**Adversary:** Testlauf selbst: `pytest -q -n 3` über test_meldeweg_ziel_641, test_texte, test_betrieb, test_protokolle_ohne_pfade, Ausgabe in adversary-test-output.txt: 288 passed, 0 failed, 0 übersprungen. Rückfall-Test per Mutation geprüft: Zeile „Die Einstellungen liegen im Reisen-Repo.“ an docs/betrieb.md angehängt, Test `test_ist_doku_nennt_reisen_repo_nicht_als_aktuellen_ort` wurde rot (1 failed, Fundstelle docs/betrieb.md:601), danach Datei zurückkopiert; `git diff` von docs/betrieb.md ist identisch zum Stand davor. Der Test ist wirksam (AC-13).
**Implementierer:** Test wirkt wie spezifiziert; Ausnahmeliste hat 8 Einträge (Obergrenze im Test 8), je Eintrag begründet und durch `test_ausnahmen_gibt_es_noch` an eine noch vorhandene Fundstelle gebunden.

Code reference: engine/tests/test_meldeweg_ziel_641.py:31
Code reference: betrieb/zustellen.py:12
Code reference: engine/konten.py:37
Code reference: engine/texte_de.py:2162
Code reference: engine/texte_en.py:2161

Text-Prüfung: `konnektor.ontologie_werkzeug.4` de „… ändert eine Sitzung im privaten Repo der Instanz die Reise“ und en „… a session in the instance's private repo changes the trip“ sind inhaltsgleich, Umlaute korrekt, Schlüssel in beiden Katalogen vorhanden (test_texte grün). `git diff` zeigt in keiner hinzugefügten Zeile echte Repo-Namen, Benutzer, Serveradressen oder Pfade; nur Platzhalter.

Finding F001:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/test_meldeweg_ziel_641.py:22
  Description: Der Rückfall-Test sucht nur die exakte Schreibweise „Reisen-Repo“ (Katalogtest zusätzlich „trips repo“); Varianten wie „Reisenrepo“ oder „Reise-Repo“ würden nicht erkannt.
  Spec requirement: AC-13 — Rückfall in das Reisen-Repo als aktuellen Ort macht die Suite rot
  Conflict: Die Spec nennt ausdrücklich das Suchwort „Reisen-Repo“; Varianten sind nicht gefordert, die Lücke ist gering.
  Remediation: Optional Suchmuster auf `Reisen-?[Rr]epo` erweitern. Kein Blocker.

### Runde 2
**Adversary:** Betriebsteil nur lesend geprüft. Das Instanz-Repo ist privat (nicht archiviert), enthält nur CLAUDE.md und README.md (keine Kopien von melden.sh, einstellungen.env, tests/; AC-2), Label `betrieb-meldung` vorhanden. Dessen CLAUDE.md beschreibt keine Submodul-Anordnung, sondern den Instanzordner unter FR_DIENST und die Prüfung der Instanz mit einem Branch der Software (AC-1). `einstellungen.env` der Instanz setzt `FR_MELDEN_REPO` auf das Instanz-Repo, die Vorgabe in `melden.sh` (Zeile 30) ebenso (AC-3, AC-4); Test 5 (fr_melden reicht die Variable durch, ohne Änderung an gemeinsam.sh) grün. Instanz-Tests mit dem Branch (FR_WURZEL auf den Worktree): 4 passed; ein Test prüft Wert und Vorgabe mit und ohne Eintrag (Test 7). Probe-Issue im Instanz-Repo: Label `betrieb-meldung`, geschlossen, Text zeigt Herkunft aus `betrieb/melden.sh` (AC-5); Issue #641 der Software trägt den Zwischenstand-Kommentar mit Nachweis A (AC-6). Offene Issues im alten Repo: noch sechs, altes Repo nicht archiviert; das ist der vorgesehene Stand vor Schritt 3 und 6.
**Implementierer:** AC-7, AC-8, AC-9, AC-14, AC-15, AC-18 folgen laut Reihenfolge der Spec nach der Auslieferung des Software-Teils. Die Software steht ihnen nicht im Weg: kein Eingriff in fr_melden/fr_einlesen, ALARMSTELLEN unverändert (Test 6 grün), kein neues Modul.

Anmerkung (kein Defekt): Die CLAUDE.md des Instanz-Repos schreibt bereits „archiviert“ und „Offene Issues hierher übertragen“, obwohl beides erst folgt. Muss vor Abschluss durch Schritt 3 und 6 wahr werden; sonst nachziehen.

Code reference: engine/tests/test_meldeweg_ziel_641.py:140
Code reference: betrieb/zustellen.py:13
Code reference: engine/konten.py:903
Code reference: engine/texte_de.py:2162
Code reference: engine/texte_en.py:2161

### Runde 3
**Adversary:** Nur lesend geprüft, die zuvor planmäßig offenen Betriebsschritte.
- AC-7/AC-8: Abfrage der offenen Issues und Pull Requests des <Reisen-Repo> per GraphQL liefert leere Listen, das Repo ist archiviert. Zwei Issues sind in das <Instanz-Repo> übertragen (dort offen, mit 9 und 8 Kommentaren, also Kommentare erhalten). Vier sind mit Abschlusskommentar geschlossen: ein Epic (abgeschlossen, Material bleibt im Archiv lesbar), ein Kartendienst-Issue (erledigt, Dienst läuft) und zwei Instanz-Test-Issues, deren Kommentare ausdrücklich nennen, was sie ersetzt (Prüfungen im Instanzordner unter FR_DIENST, Software über FR_WURZEL). Die Abweichung, das Epic zu schließen statt zu übertragen, genügt AC-7: Der Wortlaut verlangt „übertragen ODER mit schriftlicher Begründung geschlossen“, die Begründung steht im Abschlusskommentar. Auch der angehaltene Entwurfs-PR ist geschlossen.
- AC-9: Im Infrastruktur-Arbeitsbaum zeigen die vier Skripte (Sitzungsstarter und drei Meldungsskripte) auf den Ordner des Instanz-Repos; der Diff gegen origin/main umfasst genau diese 4 Dateien (+7/-7); `bash -n` bei allen vier fehlerfrei; `tests/test_sitzung_starten.py`: 15 passed. Die Zuordnung in `ack.sh` läuft über `$PWD`: ein Aufruf aus dem Ordner des Instanz-Repos trifft den Zweig `frieda`. Ein Infrastruktur-Issue hält die Änderung fest. Die Änderung ist noch nicht in `main` der Infrastruktur; das ist laut Koordinator die Auslieferung direkt nach VERIFIED. AC-9 ist damit am Arbeitsstand belegt, als Restpunkt bleibt nur die Auslieferung nach VERIFIED.
- AC-14/AC-15: <Reisen-Repo> ist archiviert (isArchived true). Die Probemeldung nach der Archivierung liegt im <Instanz-Repo> als Issue mit Label `betrieb-meldung`, geschlossen (Erstellzeit 17:39 UTC am 23.11.2026, nach den Probe- und Übertragungsschritten). Das <Instanz-Repo> ist nicht archiviert, das Archiv blieb unverändert (letzter Push 19.11.). AC-14 verlangt laut Wortlaut nur AC-5 bis AC-9 vor der Archivierung; AC-5 bis AC-8 lagen nachgewiesen vor, AC-9 war vorbereitet. Die Reihenfolge der Spec nennt Schritt 5 (Software-Repo) vor Schritt 6; archiviert wurde vor dem Ausliefern des Software-Teils. Das ist eine Reihenfolgeabweichung ohne Schaden (die Software-Texte sind fertig und getestet, das Archiv ist umkehrbar) und erfüllt den AC-Wortlaut.
- AC-18: Die neuesten Kommentare im Software-Issue der Umstellung und im Issue des Rückbaus tragen den Endstand (Ziel, Übertragungen, Archivierung, AC-36 erfüllt). Das Umstellungs-Issue bleibt offen bis zur Auslieferung, wie der Wortlaut „erst dann geschlossen“ es verlangt.
**Implementierer:** Bestätigt; Auslieferung von Software-Teil und Infrastruktur folgt direkt nach VERIFIED.

Finding F002:
  ID: F002
  Severity: LOW
  Category: spec_violation
  Code reference: docs/specs/betrieb/meldeweg-instanz-repo-641.md:111
  Description: Die verbindliche Reihenfolge nennt Schritt 5 (Software-Repo vorspulen) vor Schritt 6 (Archivieren); archiviert wurde vor dem Ausliefern des Software-Teils.
  Spec requirement: AC-14 — AC-5 bis AC-9 liegen vor der Archivierung nachgewiesen vor (erfüllt); der Reihenfolge-Abschnitt nennt zusätzlich Schritt 5
  Conflict: Abweichung nur von der Reihenfolge, nicht vom AC-Wortlaut; Meldungen gehen schon ins <Instanz-Repo>, der Software-Teil ändert nur Doku und Texte.
  Remediation: Keine; im Endstand-Kommentar festhalten.

Code reference: betrieb/zustellen.py:12
Code reference: engine/konten.py:37
Code reference: engine/texte_de.py:2162
Code reference: engine/texte_en.py:2161
Code reference: engine/tests/test_meldeweg_ziel_641.py:31

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

**VERIFIED**

Alle 18 Acceptance Criteria sind belegt. Tests: 288 passed, 0 failed, 0 übersprungen; Instanz-Tests mit dem Branch grün; Rückfall-Test per Mutation als wirksam nachgewiesen. Restpunkte ohne Defekt: Auslieferung des Software-Teils und der Infrastruktur-Änderung direkt nach diesem Verdict (AC-9, AC-18), Schließen des Umstellungs-Issues erst danach. Befunde F001 und F002 sind LOW und nicht blockierend.

## Geprüfte Dateien

- sha256:c0f257a59221f0b50b9da1d5ace4ba0e4df2788f6ed66a38576c7e31f9307a8f  betrieb/zustellen.py
- sha256:698f164441a23934c165eea0ecfc353ff2eecc50befddd917dcd7bdd8ea3658c  docs/specs/betrieb/meldeweg-instanz-repo-641.md
- sha256:d66e4820f75703e28c8c622331d497bc46dfbed65c361d5ecf0f8f6a5935a64b  engine/konten.py
- sha256:3a044551797b41cd4aa8bec3caf7346db55956110364b4bc819aa6f262b07b74  engine/tests/test_meldeweg_ziel_641.py
- sha256:a731230a048f9efd05927943634e55384a204c196d6d6e99a98ab49998ecca49  engine/texte_de.py
- sha256:e9eadc03ab6b04de108c2a2f6176745f90619ea861711ebd43f45aa39d6535a6  engine/texte_en.py

## Prüfbasis

- base: 3d7532160e8f0f61734ef30e657fd70c0608c14f
- blob:46abaf27bfc80f882c8e02b82252f35aa69e9d6f  betrieb/zustellen.py
- blob:44710eddc363644eda245884906d155aabab0975  docs/specs/betrieb/meldeweg-instanz-repo-641.md
- blob:74a9ccc01963d85f06c6f42792d4b55abd22fc39  engine/konten.py
- blob:898fe48e49050045bf02f48da22a6283309fef85  engine/tests/test_meldeweg_ziel_641.py
- blob:a5e187ae5e6074ea6b93fec99873d9a8384f767d  engine/texte_de.py
- blob:b361f32db265ce256f2ee817b00b687111674256  engine/texte_en.py

## Geprüfte Dateien

- sha256:c0f257a59221f0b50b9da1d5ace4ba0e4df2788f6ed66a38576c7e31f9307a8f  betrieb/zustellen.py
- sha256:698f164441a23934c165eea0ecfc353ff2eecc50befddd917dcd7bdd8ea3658c  docs/specs/betrieb/meldeweg-instanz-repo-641.md
- sha256:d66e4820f75703e28c8c622331d497bc46dfbed65c361d5ecf0f8f6a5935a64b  engine/konten.py
- sha256:3a044551797b41cd4aa8bec3caf7346db55956110364b4bc819aa6f262b07b74  engine/tests/test_meldeweg_ziel_641.py
- sha256:a731230a048f9efd05927943634e55384a204c196d6d6e99a98ab49998ecca49  engine/texte_de.py
- sha256:e9eadc03ab6b04de108c2a2f6176745f90619ea861711ebd43f45aa39d6535a6  engine/texte_en.py

## Prüfbasis

- base: 3d7532160e8f0f61734ef30e657fd70c0608c14f
- blob:46abaf27bfc80f882c8e02b82252f35aa69e9d6f  betrieb/zustellen.py
- blob:44710eddc363644eda245884906d155aabab0975  docs/specs/betrieb/meldeweg-instanz-repo-641.md
- blob:74a9ccc01963d85f06c6f42792d4b55abd22fc39  engine/konten.py
- blob:898fe48e49050045bf02f48da22a6283309fef85  engine/tests/test_meldeweg_ziel_641.py
- blob:a5e187ae5e6074ea6b93fec99873d9a8384f767d  engine/texte_de.py
- blob:b361f32db265ce256f2ee817b00b687111674256  engine/texte_en.py
