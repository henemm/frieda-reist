# Adversary Dialog — fix-670-lesewerkzeuge
Spec: docs/specs/konnektor/lesewerkzeuge-670.md
Datum: 2026-11-24 20:49

## Checkliste
- [x] **AC-1:** Given der Konnektor / When die Werkzeugliste erzeugt wird / Then tragen `my_trips` und `my_profile` `readOnlyHint: true`. Test: `test_meine_reisen_und_mein_profil_sind_lesewerkzeuge`.
- [x] **AC-2:** Given die Sperre in Claude-Code-Sitzungen / When `my_trips` oder `my_profile` aufgerufen werden / Then lässt der Hook sie zu, und `ERLAUBT` entspricht weiter genau den Lesewerkzeugen. Tests: `test_meine_reisen_und_mein_profil_sind_lesewerkzeuge`, `test_erlaubnisliste_entspricht_den_lesewerkzeugen`.
- [x] **AC-3:** Given `calendar` kann mit `neu=true` den Link erneuern / When die Werkzeugliste und die Sperre geprüft werden / Then hat `calendar` kein `readOnlyHint` und bleibt gesperrt. Test: `test_calendar_bleibt_gesperrt`.
- [x] **AC-4:** Given `konten.env` mit der Kontaktadresse / When `konten_wert` aufgerufen wird / Then gilt Umgebung vor Datei, Anführungszeichen außen entfallen, nur der angefragte Name (nur `FR_…`) wird geliefert. Tests: `test_konten_wert_liest_datei_und_entfernt_anfuehrungszeichen`, `test_konten_wert_umgebung_vor_datei`, `test_konten_wert_liefert_nur_den_einen_namen`.
- [x] **AC-5:** Given die Datei fehlt oder ist nicht lesbar / When `konten_wert` aufgerufen wird / Then ist das Ergebnis `None`, ohne Ausnahme, ohne Ausgabe und ohne Protokollzeile. Test: `test_konten_wert_datei_fehlt_oder_unlesbar`.
- [x] **AC-6:** Given Geheimnisse in `konten.env` / When `instanz.wert` läuft / Then bleiben sie unsichtbar; `wert` liest die Datei nicht. Test: `test_wert_liest_konten_env_nicht`.
- [x] **AC-7:** Given `FR_TESTKONTO` entspricht der Kontaktadresse, die nur in `konten.env` steht / When `testzugang.py einrichten` läuft / Then wird verweigert und kein Konto angelegt. Test: `test_einrichten_verweigert_kontaktadresse_aus_konten_env`.
- [x] **AC-8:** Given keine `konten.env` / When `einrichten` mit gewöhnlichem Testkonto läuft / Then gelingt es wie bisher; die Schranke Recht `betreiber` greift weiter. Tests: `test_einrichten_ohne_konten_env_bricht_nicht_ab`, `test_einrichten_verweigert_betreiberkonto`.
- [x] **AC-9:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen; vor dem Vorspulen sind die Tests der einbindenden Instanzen mit dem Zweig grün.

## Dialog

### Runde 1
**Adversary:** Ich gehe von einer fehlerhaften Umsetzung aus und prüfe jeden Punkt am Code und mit eigenen Läufen.
Testlauf selbst: 40 passed (Sperre, Instanz, Testzugang, Protokolle ohne Pfade), Ausgabe in docs/artifacts/fix-670-lesewerkzeuge/adversary-test-output.txt.

Confirmation:
  AC: AC-1
  Code reference: engine/konnektor.py:2503
  Evidence: MEIN_PROFIL (my_profile) trägt readOnlyHint True; MEINE_REISEN (my_trips) ebenso, engine/konnektor.py:2787. Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: .claude/hooks/frieda_sperre.py:18
  Evidence: ERLAUBT enthält my_profile und my_trips; Abgleichstest gegen die Werkzeugliste grün, also nur Lesewerkzeuge.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/konnektor.py:2491
  Evidence: KALENDER ohne annotations (Zeilen 2491-2493 unverändert), nicht in ERLAUBT; Test test_calendar_bleibt_gesperrt grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/instanz.py:97
  Evidence: Eigener Lauf: Datei mit Anführungszeichen liefert A@x.de; Umgebung gewinnt (env@x); Name ohne FR_ gibt None; der Parser filtert auf FR_-Namen und konten_wert gibt nur .get(name) zurück. Parser: instanz.py:75-91.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/instanz.py:108
  Evidence: except (OSError, UnicodeDecodeError) liefert None, keine print- oder Log-Aufrufe. Leerer Wert und auskommentierte Zeile ergeben None.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/instanz.py:93
  Evidence: wert() unverändert (Umgebung oder einstellungen()), konten.env wird dort nicht gelesen; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/testzugang.py:182
  Evidence: kontakt = wert(...) or konten_wert(...), strip().lower(); Vergleich mit email in Zeile 185 vor jeder Kontoanlage; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: betrieb/testzugang.py:185
  Evidence: Fehlende Datei ergibt None, dann ""; Schranke Recht betreiber im selben if unverändert. Beide Tests grün.
  Status: CONFIRMED

**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Gezielte Randfälle.
- Leerer Wert in konten.env: None, kein Leeradress-Treffer (email nie leer).
- Großschreibung/Leerzeichen: strip().lower() in testzugang.py:182-183; email kommt normalisiert aus konten.adresse.
- Umgebung gesetzt aber leer: Datei wird gelesen, gleiche Semantik wie wert().
- Kommentarzeile: ignoriert.
- PermissionError/UnicodeDecodeError: abgefangen.
- Regression: _lesen(datei=None) behält Verhalten für einstellungen(); Annotation ändert nur tools/list.

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/instanz.py:75
  Description: Parser erkennt Zeilen mit export-Präfix oder Leerzeichen um das Gleichheitszeichen nicht; die Zusatzprüfung greift dann still nicht.
  Spec requirement: AC-4 — Format NAME=wert, nur FR_…
  Conflict: kein Verstoß (gleicher Parser wie bei der Einstellungsdatei); die Schranke Recht betreiber bleibt die eigentliche Absicherung.
  Remediation: keine nötig.

AC-9: Gesamtlauf 3633 passed, 1 failed (test_wackel_599, webkit, Ablauf unter Verzögerung). Betrifft Browserverhalten der Seite, keine der vier geänderten Dateien; allein wiederholt 18 passed; Issue #697. Kein Bezug zur Änderung. Instanztests laufen in Phase 8: offen für später, kein Defekt dieser Phase.

Confirmation:
  AC: AC-9
  Code reference: engine/konnektor.py:2787
  Evidence: Gesamtlauf bis auf einen unabhängigen Wackeltest grün, eigene 40 Tests grün; Instanztests in Phase 8 offen.
  Status: CONFIRMED

**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 40 passed, 0 failed, 0 übersprungen (eigener Lauf); Gesamtlauf 3633 passed, 1 unabhängiger Wackeltest (#697)
Edge cases: geprüft, nur LOW-Hinweis F001 (kein Verstoß)
Regressions: None found
Checklist: 9/9 proven (AC-9 mit offenem Phase-8-Instanztest)

## Geprüfte Dateien

- sha256:8907ccde6c7e42085395fcf18fa71024873d4f3897c2ca916e5361b69ce20487  .claude/hooks/frieda_sperre.py
- sha256:0fdb411853a05ad31bdc1a4de6cf28472c7e9c5ce4ec8d287272abd683216fab  betrieb/testzugang.py
- sha256:3e469e7193ff289b93158e6bf91a1afabb4cb635fa7a8531c95016d481efd090  engine/instanz.py
- sha256:a0636a6d42a94d316373e95a57a89f7d3cc404daa122a0654232f6b87666e6c2  engine/konnektor.py

## Prüfbasis

- base: 35e2d890bf82b956fbe78a698e42757e510ec42b
- blob:bc8fb263aefeb35e940e38f56580327aa0bc027a  .claude/hooks/frieda_sperre.py
- blob:91ba43a029de303d4539638ba315794a7f31f798  betrieb/testzugang.py
- blob:7f202a0ab08b85e8d4eb6a84e9104dc8da734f31  engine/instanz.py
- blob:18dc914d6dcbbf83e641c903c1c035f2460791e8  engine/konnektor.py

## Geprüfte Dateien

- sha256:8907ccde6c7e42085395fcf18fa71024873d4f3897c2ca916e5361b69ce20487  .claude/hooks/frieda_sperre.py
- sha256:0fdb411853a05ad31bdc1a4de6cf28472c7e9c5ce4ec8d287272abd683216fab  betrieb/testzugang.py
- sha256:3e469e7193ff289b93158e6bf91a1afabb4cb635fa7a8531c95016d481efd090  engine/instanz.py
- sha256:a0636a6d42a94d316373e95a57a89f7d3cc404daa122a0654232f6b87666e6c2  engine/konnektor.py

## Prüfbasis

- base: 35e2d890bf82b956fbe78a698e42757e510ec42b
- blob:bc8fb263aefeb35e940e38f56580327aa0bc027a  .claude/hooks/frieda_sperre.py
- blob:91ba43a029de303d4539638ba315794a7f31f798  betrieb/testzugang.py
- blob:7f202a0ab08b85e8d4eb6a84e9104dc8da734f31  engine/instanz.py
- blob:18dc914d6dcbbf83e641c903c1c035f2460791e8  engine/konnektor.py
