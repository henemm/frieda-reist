# Adversary Dialog — fix-694-konto-loeschen-ablage-neu
Spec: docs/specs/betrieb/konto-loeschen-ablage-neu-694.md
Datum: 2026-11-27 10:37

## Checkliste
- [x] **AC-1:** Given eine Bitte „Reisen anlegen“ der Person (mit `konto`, alt nur mit Adresse) / When ihr Konto gelöscht wird / Then fehlen die Zeilen, die Bitte einer anderen Person bleibt unverändert. Test: `test_neu_anfrage_reisen_der_person_entfaellt`.
- [x] **AC-2:** Given ein bestätigter Wartelisten-Eintrag derselben Adresse / When das Konto gelöscht wird / Then fehlt die Meldung, andere Adressen bleiben. Test: `test_neu_anfrage_warteliste_derselben_adresse_entfaellt`.
- [x] **AC-3:** Given die Person ist Betreiber:in / When das Konto gelöscht wird / Then fehlt ihre Kennung in `an`, die Meldung an weitere Betreiber:innen bleibt, die nur an sie entfällt. Test: `test_neu_betreiberin_nur_kennung_aus_an`.
- [x] **AC-4:** Given eine Meldung `neue_reise` an die Person / When das Konto gelöscht wird / Then entfällt sie; ein Name, den ein anderes Konto trägt, bleibt in `an`. Test: `test_neu_neue_reise_an_person_entfaellt`.
- [x] **AC-5:** Given ein Auftrag der Person / When das Konto gelöscht wird / Then sind Name, Kürzel, Personenname und Name im Text (ganzes Wort) „gelöschte Person“, die Kennung `konto_id` fehlt und `pfad` bleibt. Test: `test_neu_auftrag_der_person_pseudonymisiert`.
- [x] **AC-6:** Given der Auftrag einer anderen Person mit ihrer Adresse in `einladen` / When das Konto gelöscht wird / Then fehlt dieser Eintrag, ihr Name dort ist „gelöschte Person“, alles andere bleibt. Test: `test_neu_einladen_mit_adresse_entfernt_fremder_auftrag`.
- [x] **AC-7:** Given eine ausstehende neue Reise der Person / When das Konto gelöscht wird und `zustellen.py` läuft / Then fehlt die Zeile und die Reise ist zur Löschung vorgemerkt. Test: `test_neu_ausstehende_reise_vorgemerkt`.
- [x] **AC-8:** Given Zeilen nur anderer Personen / When ein anderes Konto gelöscht wird / Then sind die Dateien byteidentisch. Test: `test_neu_fremde_zeilen_byteidentisch`.
- [x] **AC-9:** Given alle Lagen zugleich / When das Konto gelöscht wird / Then steht weder Name noch Adresse noch Kennung unter `ordner_neu()` und, nach dem nächsten Lauf von `zustellen.py`, in der Ausstehend-Datei. Test: `test_neu_volltextsuche_ohne_spur`.
- [x] **AC-10:** Given unlesbare Zeilen / When das Konto gelöscht wird / Then bleiben sie, nichts wirft. Test: `test_neu_unlesbare_zeilen_bleiben`.
- [x] **AC-11:** Given ein Fehler beim Umschreiben / When das Konto gelöscht wird / Then kommt `konto.fehler.loeschen_spaeter`, die Datenbank bleibt unberührt, ein späterer Versuch gelingt. Test: `test_neu_fehler_bricht_vor_datenbank_ab`.
- [x] **AC-12:** Given `meldung_anlegen` und der Konnektor hängen an / When sie laufen / Then nehmen sie `ablage_sperre`. Tests: `test_neu_sperre_in_meldung_anlegen`, `test_neu_sperre_im_konnektor_anhaengen`.
- [x] **AC-13:** Given die bisherigen Ablagen der Reisen / When das Konto gelöscht wird / Then bleibt das Verhalten unverändert. Test: `test_neu_bestehende_ablage_der_reisen_unveraendert`.
- [x] **AC-14:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen; `test_texte.py` bleibt grün (keine neuen Textschlüssel).

## Dialog

### Runde 1
**Adversary:** Alle 14 Punkte einzeln geprüft. Tests: `engine/tests/test_loeschen_konto.py` 36 passed. Gesamtlauf `pytest -q -n 4 engine/tests`: 3209 passed, 92 failed, 41 errors, 449 skipped (test-run-output.txt). Die 92+41 liegen alle in test_betrieb.py, test_nginx*.py, test_units*.py, test_kartendienst*.py, test_rueckbau_557.py (einrichten.sh: `shopt globasciiranges`, getent, `find -perm`: macOS). Gegenprobe: dieselben 9 Dateien am unveränderten HEAD (eigener Wegwerf-Worktree): ebenfalls 92 failed, 41 errors. Also vorbestehend, kein Treffer der Änderung; AC-14 bleibt für Linux-CI offen.

Confirmation:
  AC: AC-1
  Code reference: engine/konten.py:700
  Evidence: `_meldung_ohne` entfernt `anfrage_reisen` mit `konto == kid` oder gleicher Adresse (casefold); Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/konten.py:702
  Evidence: `anfrage_warteliste` entfällt bei gleicher Adresse, nur dann.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/konten.py:705
  Evidence: `an` wird um die Kennung gekürzt, leer entfällt die Meldung.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/konten.py:750
  Evidence: Name wird nur ersetzt, wenn kein anderes Konto ihn trägt (`frei`); Test `test_neu_name_in_an_bleibt_wenn_anderes_konto_ihn_traegt` grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/konten.py:712
  Evidence: `_auftrag_ohne` setzt name/konto/Personenname/Text (Wortgrenze, `re.escape`) auf „gelöschte Person“, entfernt `konto_id`, `pfad` bleibt. Sonderzeichen-Probe mit Name `C++ (Karl)`: korrekt ersetzt, `Karl-Heinz`/`Karls` unberührt.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/konten.py:728
  Evidence: `einladen`-Einträge mit gleicher Adresse (casefold) entfallen, Name nur beim Personenschlüssel und im Text ersetzt.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/zustellen.py:23
  Evidence: `_konto_geloescht` lässt die Zeile fallen und merkt die Reise mit `loeschung_vormerken(…, None)` vor; schon vorgemerkt wird geprüft, KontoFehler abgefangen; Aufruf in der Schleife vor dem Zugriff auf daten.json (Zeile 61).
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/konten.py:652
  Evidence: `_jsonl_umschreiben` schreibt nur bei `geaendert` und lässt unveränderte Zeilen als Originalbytes; Test byteidentisch grün. Einschränkung siehe F001.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/konten.py:742
  Evidence: Beide Dateien in `ordner_neu()` (inkl. Übergang `_neu`, da `instanz.neu()`), Ausstehend-Datei über zustellen; Volltextsuchtest grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/konten.py:665
  Evidence: nicht lesbare oder nicht-dict-Zeilen werden unverändert übernommen (auch ungültiges UTF-8).
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/konten.py:767
  Evidence: `_ablage_neu_bereinigen` steht im selben try wie `_pseudonymisieren`, vor der Transaktion; jede Ausnahme wird `konto.fehler.loeschen_spaeter`.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/rueckmeldungen.py:344
  Evidence: `meldung_anlegen` hängt unter `ablage_sperre` an (Zeile 312); Konnektor ebenso (`engine/konnektor.py:2471`). Stresstest: ein Thread legt 300 Meldungen an, während 120 Umschreibläufe laufen: 300 von 300 vorhanden, keine verlorene Zeile.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/konten.py:767
  Evidence: `_pseudonymisieren` unverändert, Test `test_neu_bestehende_ablage_der_reisen_unveraendert` und `test_ablage_dateien_pseudonymisiert` grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/konnektor.py:2471
  Evidence: `reise_anlegen` hängt an `auftraege.jsonl` unter `rm.ablage_sperre(o)` an; Test `test_neu_sperre_im_konnektor_anhaengen` grün.
  Status: CONFIRMED

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/konten.py:705
  Description: `_meldung_ohne` setzt `m["an"]` auf die gefilterte Liste und löscht die Zeile, wenn sie leer ist. Eine fremde Meldung, deren `an` schon vorher leer war, würde beim Löschen eines beliebigen Kontos entfallen (Probe: `{"art":"konflikt","an":[]}` -> None). Das Umschreiben der Datei geschieht dann zwar nur bei einer Änderung, aber die Zeile geht verloren.
  Spec requirement: AC-8 — Zeilen anderer Personen bleiben byteidentisch.
  Conflict: Im Code erzeugt kein Aufrufer eine Meldung mit leerem `an` in `ordner_neu()` (anmeldung.py:1935 prüft `if namen`, :775 hat immer eine Kennung); nur theoretisch erreichbar.
  Remediation: Nur löschen, wenn `an` vor dem Filtern nicht leer war.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/konten.py:728
  Description: Die Adresse in `einladen` wird nur mit `casefold()`, ohne `strip()`, verglichen; die der gelöschten Person ist gestrippt (Zeile 744). Ein Eintrag mit Leerzeichen um die Adresse bleibt stehen (Probe belegt). Der Konnektor normalisiert Adressen vor dem Anhängen, daher nur theoretisch.
  Spec requirement: AC-6 / AC-9
  Conflict: Adresse bliebe bei nicht normalisierten Altdaten stehen.
  Remediation: `str(e.get("email") or "").strip().casefold()`.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/konten.py:738
  Description: Wird der Name aus einer Einladung im `text` ersetzt, trifft es jedes Wort mit gleichem Namen, auch eine andere Person des fremden Auftrags mit gleichem Vornamen (Probe: zwei „Tom“, im Text beide ersetzt, in `personen` nur der Schlüssel `k`). Das ist in der Spec so beschrieben (ganzes Wort im Text), verfälscht aber den Text bei Namensgleichheit.
  Spec requirement: AC-6
  Conflict: Spec-konform, nur Hinweis; wie in „Known Limitations“ (lieber nicht ersetzen als den Falschen treffen) nicht abgefangen.
  Remediation: Hinnehmen oder bei Namensgleichheit im selben Auftrag den Text nicht anfassen.

### Runde 2
**Adversary:** Gezielt gebrochen:
- Sandbox: Der Rückmeldedienst darf `ReadWritePaths=__ABLAGE__ __KONTEN__` (rueckmeldungen.service:36), `ordner_neu()` liegt unter Konten; `loeschen` fasst die Ausstehend-Datei nicht an (Test `test_neu_loeschen_ohne_schreibrecht_im_konnektorordner`). push.service hat ABLAGE und KONNEKTOR nur lesend: Alle Lesepfade (push.py:263, 317, 560) lesen `meldungen.jsonl` ohne `ablage_sperre`; die Sperre steht nur in `meldung_anlegen`, im Konnektor-Anhängen und im Löschen. Keine Sperre in einem Lesepfad.
- Wächter und Konnektor rufen `meldung_anlegen` auf Reise-Ablagen (waechter.py:368, konnektor.py:2183): dort entsteht jetzt `.sperre`. Alle Durchläufer über Reise-Ablagen (`_ablage_pseudonymisieren` konten.py:601) filtern auf `.json/.jsonl`; `.sperre` wird ignoriert. Export (anmeldung.py `_export_reise`) und Reise-Löschen lesen keine Verzeichnisse der Ablage per Glob. Keine Folge gefunden. Dieselben Prozesse beschreiben `meldungen.jsonl` schon heute im selben Ordner, die neue Datei braucht keine neuen Rechte.
- Übergang `_neu`: `instanz._belegt` prüft `any(iterdir())`; `.sperre` könnte einen sonst leeren Ordner „belegt“ machen. Nur wirksam, wenn neu und alt beide leer waren (dann gewinnt neu ohnehin), oder wenn die Sperre im alten Ort liegt (dort liegen ohnehin Daten). Kein Flip möglich.
- Gleichzeitiges Anhängen: Stresstest mit Thread (300 Anhänger gegen 120 Umschreibläufe): nichts verloren. Verschachtelte Sperre (Deadlock): `aendern`-Callbacks rufen `meldung_anlegen` nicht auf; `zustellen.meldung_anlegen` läuft außerhalb des Umschreibens. Kein Deadlock.
- Regex-Sonderzeichen (`C++ (Karl)`), Umlaute (`Jürgen`, `Jürgens`, `ÄJürgen`: nur ganzes Wort ersetzt), leere Adresse (`adresse` leer: kein Abgleich, kein Treffer auf leere E-Mail `email: None`), `daten: None`, Name leer: alle ohne Ausnahme.
- Betreiber:in mit gleichem Namen wie anderes Konto: `frei=None`, nur die Kennung wird entfernt (Test grün).
- Zustellen: Zeile eines gelöschten Kontos wird verworfen und vorgemerkt; schon vorgemerkte Reise löst keinen Fehler aus; Zeilen ohne `konto_id` (alt) werden nicht angefasst (bewusst, Altfall).
- Restrisiko: Die Ablage wird vor der DB-Transaktion bereinigt; scheitert die Transaktion, ist die Ablage schon bereinigt (Konto bleibt, Bitten weg). Das entspricht dem Muster von `_pseudonymisieren` und ist in der Spec so gewollt (Wiederholung möglich).
**Implementierer:** keine Antwort nötig; keine Finding ist spec-brechend.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`); keine Tabelle angehängt. Schreibstellen der neuen Felder: `a["konto_id"]` wird nur von `engine/konnektor.py` (reise_anlegen) geschrieben, Bedingung davor: Konto gibt die Anfrage in der Claude-App auf; Test für diesen Weg: `test_neu_auftrag_der_person_pseudonymisiert` und `test_neu_sperre_im_konnektor_anhaengen`. `.sperre`: einzige Schreibstelle `ablage_sperre`, Test `test_neu_sperre_in_meldung_anlegen`.

## Verdict

VERDICT: VERIFIED

Tests: Gesamtlauf 3209 passed, 92 failed + 41 errors (identisch am unveränderten HEAD, macOS-Skripte einrichten.sh/nginx/units/kartendienst), 449 übersprungen; test_loeschen_konto.py 36 passed.
Edge cases: geprüft; drei LOW-Hinweise (F001-F003), keiner bricht die Spec.
Regressions: keine gefunden.
Checklist: 13/14 bewiesen, AC-14 (grüner Gesamtlauf) erst auf Linux-CI belegbar.

## Geprüfte Dateien

- sha256:15fb6e025987f1550010ae1a2bef057edc012ab34834529fe934afb6a9a52d2e  betrieb/zustellen.py
- sha256:26f491e5823566b060c3cdac99729d6f729efe4dde6c4b3165a6eda89bee9a10  engine/konnektor.py
- sha256:a52ef3158f4e773005519685f1a22eb08880c1e40f4cb7219ef962cf4fba406b  engine/konten.py
- sha256:8bebcb51e76ace3d9acf1e523173d395619919337e60c70ae1258269b8a56333  engine/rueckmeldungen.py

## Prüfbasis

- base: 1915f39c283d5a6c4576257dd0d3231d51a59c1f
- blob:997d835ca1cdc40619dc48725c56b07f257a1a4a  betrieb/zustellen.py
- blob:c12b45915464f5fdd9fe9b95c38ad139d0d93515  engine/konnektor.py
- blob:62c2b6443681325819b38bdd3921d65c57235ebe  engine/konten.py
- blob:c7ab771cea6fef9181664d72e13a188bf90022f9  engine/rueckmeldungen.py

## Geprüfte Dateien

- sha256:15fb6e025987f1550010ae1a2bef057edc012ab34834529fe934afb6a9a52d2e  betrieb/zustellen.py
- sha256:26f491e5823566b060c3cdac99729d6f729efe4dde6c4b3165a6eda89bee9a10  engine/konnektor.py
- sha256:a52ef3158f4e773005519685f1a22eb08880c1e40f4cb7219ef962cf4fba406b  engine/konten.py
- sha256:8bebcb51e76ace3d9acf1e523173d395619919337e60c70ae1258269b8a56333  engine/rueckmeldungen.py

## Prüfbasis

- base: 1915f39c283d5a6c4576257dd0d3231d51a59c1f
- blob:997d835ca1cdc40619dc48725c56b07f257a1a4a  betrieb/zustellen.py
- blob:c12b45915464f5fdd9fe9b95c38ad139d0d93515  engine/konnektor.py
- blob:62c2b6443681325819b38bdd3921d65c57235ebe  engine/konten.py
- blob:c7ab771cea6fef9181664d72e13a188bf90022f9  engine/rueckmeldungen.py
