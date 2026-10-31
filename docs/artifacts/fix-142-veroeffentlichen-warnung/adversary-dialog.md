# Adversary Dialog — fix-142-veroeffentlichen-warnung
Spec: docs/specs/betrieb/veroeffentlichen-warnung-142.md
Datum: 2026-10-31 08:28
Testlauf: docs/artifacts/fix-142-veroeffentlichen-warnung/adversary-test-output.txt (test_betrieb, test_waechter, test_schreiben, test_konnektor: 213 passed, 0 failed, 0 übersprungen); volle Suite laut test-green-output.txt: 679 passed

## Checkliste
- [x] **Input:** ein Lauf von `veroeffentlichen.sh` (Timer, nach einem Schreibvorgang oder von Hand, auch mit `--immer`); ein Schreibvorgang über den Konnektor; ein Aufruf des Werkzeugs `start_ende_setzen`.
- [x] **Output:** Exit-Codes und Protokollzeilen nach F-5; Antwort des Schreibwegs mit optionalem Feld `hinweise`; Antwort von `start_ende_setzen` wie bei `reise_aendern` (`Titel, Text`).
- [x] **Side effects:** Dateien `<FR_DIENST>/veroeffentlichen-rot` und `<FR_DIENST>/veroeffentlichen-warnung`; Meldungen in `meldungen.jsonl` der Ablage der betroffenen Reise; Nachrichten über `FR_MELDEN`; ein Commit im Reisen-Repo je `start_ende_setzen` mit Verlaufseintrag in `reise.yaml`.
- [x] **AC-1:** tests/ rot sperrt nicht, Exit 0, Warnzeile, fr_melden normal einmal
- [x] **AC-2:** Warnung einmal je Commit (Merker veroeffentlichen-warnung)
- [x] **AC-3:** engine/tests rot: Exit 1, art=software, seit, kein Stand/Stempel/Heartbeat
- [x] **AC-4:** deploy.sh und Tor prüfen nur engine/tests, FR_GEPRUEFT-Zeile unverändert, --basetemp
- [x] **AC-5:** Warnung im Plan sperrt nie (Bau Exit 0)
- [x] **AC-6:** eine rote Reise hält die anderen nicht auf (Exit 2), art=reise, Stand nicht geschrieben
- [x] **AC-7:** deploy.sh Exit 2 bei Baufehler, sonst Exit 1
- [x] **AC-8:** Infrastrukturfehler (Exit 1) beendet die Schleife, Rot-Datei unberührt
- [x] **AC-9:** neue Warnung als `hinweise`, ok true, Eintrag im Repo
- [x] **AC-10:** keine neuen Warnungen: kein Feld `hinweise`
- [x] **AC-11:** Baufehler lehnt ab, nichts geändert, keine Hinweise
- [x] **AC-12:** mehr als 10 Hinweise: 10 Zeilen plus „und N weitere“
- [x] **AC-13:** Konnektor hängt Hinweise an (Eintragen und entscheiden), kein Fehler
- [x] **AC-14:** Zeitgrenzen bleiben (Vorher-Bau innerhalb ZEIT_GESAMT)
- [x] **AC-15:** roter Stand wird nicht erneut geprüft („Bekannter roter Stand“)
- [x] **AC-16:** Überspringen ohne Stempel und Heartbeat
- [x] **AC-17:** --immer oder neuer Commit prüft neu, Grün löscht Rot-Datei
- [x] **AC-18:** Infrastrukturfehler wird wiederholt, nicht gemerkt
- [x] **AC-19:** „nichts Neues“ nach Grün mit Stempel und Heartbeat
- [x] **AC-20:** kein Alarm vor der Schwelle
- [x] **AC-21:** Alarm genau einmal je Rot-Phase
- [x] **AC-22:** rot-melden nur bei art=reise mit --reisen
- [x] **AC-23:** rot_melden idempotent über schluessel, an Organisator:innen, ohne Pfade
- [x] **AC-24:** fr_melden-Ausfall: gemeldet bleibt 0, Wiederholung
- [x] **AC-25:** Schwelle FR_ROT_MELDEN_NACH_MINUTEN einstellbar, Vorgabe 30 im Beispiel
- [x] **AC-26:** seit und gemeldet bleiben über neue rote Commits
- [x] **AC-27:** start_ende_setzen ändert Plan und Verlauf
- [x] **AC-28:** nur Organisator:innen
- [x] **AC-29:** Ablehnungen bei ungültiger Eingabe
- [x] **AC-30:** leerer Text entfernt ende.ort / ende.datum
- [x] **AC-31:** Warnung kommt als Hinweis, Baufehler lehnt ab
- [x] **AC-32:** Werkzeug in WERKZEUGE, AKTIONEN, Konnektor-Liste, docs/konnektor.md; reise_aendern verweist darauf
- [x] **AC-33:** docs/betrieb.md beschreibt Sperrkriterien, Exit-Codes, Rot-Datei, Überspringen, Alarm, Schwelle, Konvention

## Dialog

### Runde 1
**Adversary:** Ich gehe die Rot-Datei-Logik von `betrieb/veroeffentlichen.sh` durch und versuche, sie zu brechen.
- Infrastrukturfehler: Vorspulen und Submodul (Zeilen 143 und 145) enden mit `return 1`, bevor `rot_lesen` oder `rot_schreiben` laufen. Die Rot-Datei bleibt dort also unberührt. Exit≠0,2 aus `deploy.sh` landet im `*)`-Zweig (Zeile 186) mit `return 1` und ebenfalls ohne Schreiben der Rot-Datei. Das deckt AC-8 und AC-18 ab.
- set -e-Fallen: Der Deploy-Rückgabewert wird mit `rc=0; "$deploy" "$reise" || rc=$?` abgefangen (Zeile 181), so bricht `set -e` nicht ab. `rot_lesen` mit fehlender Datei endet mit `return 0` (Zeile 49). In `alarm_pruefen` stehen `[ ... ] || return 0` und `[ "$rot_gemeldet" = 1 ] && return 0`, beides sind keine letzten Befehle einer Liste, die set -e auslösen. Die Zuweisung `seit_s="$(date ...)" || {...}` ist abgesichert.
- Überspringen (Zeilen 149 bis 154): Es gibt kein `erfolg_melden`, kein `pytest`, kein `deploy`, nur `zustellen` und `alarm_pruefen`. Das deckt AC-15 und AC-16 ab.
- seit/gemeldet bleiben über neue Commits: `rot_schreiben` (Zeilen 68 bis 75) liest die Datei und setzt `seit` und `gemeldet=0` nur, wenn `seit` leer ist. AC-26 ist belegt.
- Alarm genau einmal: `alarm_pruefen` (Zeilen 82 bis 106) ruft `fr_melden` über `alarm_senden` nur bei `gemeldet≠1` und setzt dann `gemeldet=1` über `rot_ablegen`. Schlägt der Versand fehl, bleibt `gemeldet=0`. AC-20, AC-21 und AC-24 sind belegt.
- Freischalten nur gelungener Reisen: Die Schleife läuft über `$gut` (Zeile 190). Rote Reisen stehen nur in `$rote`. AC-6 ist belegt.
- Merker je Commit (Zeilen 170 bis 174): `veroeffentlichen-warnung` enthält den Commit der letzten Meldung. Das deckt AC-2 ab.
- Tests-Prüfung des Reisen-Repos: Zeile 168 steht in `if ! ... ` und kann daher nicht sperren.
- `deploy.sh` Zeilen 30 bis 34: Das Bauscheitern führt zu `exit 2`. Die `FR_GEPRUEFT`-Zeile (37) ist wörtlich unverändert. Die pytest-Zeile (39) enthält `engine/tests` und kein `$WURZEL/tests`, aber `--basetemp`.
Ich suche eine Lücke und finde: Ohne `FR_MELDEN` gilt der Alarm als gesendet (Zeile 78: `return 0`, danach `gemeldet=1`). Das ist Befund F001.
**Implementierer:** Zu F001: `fr_melden` in `betrieb/gemeinsam.sh:70-72` ist ohne `FR_MELDEN` ebenfalls ein stilles Nichts. „Sonst nichts“ ist bewusst die Konvention der Instanz ohne Meldeweg. Die Alternative wäre ein Alarm, der ohne Meldeweg bei jedem Lauf neu versucht wird, ohne dass er jemals ankommen kann. Spec F-6 sagt „Fällt fr_melden aus (Exit != 0)“. Ein nicht eingerichteter Weg ist kein Ausfall. Die Meldung an die Organisator:innen über `rot-melden` läuft unabhängig davon weiter.

**Adversary:** Zweiter Blick auf `engine/waechter.py` `rot_melden` (Zeile 318) und auf die Verarbeitung der Meldungsart `betrieb`.
- `engine/rueckmeldungen.py:260/272`: `WAECHTER_ARTEN = ("erinnerung","status","pruefung")`. Eine Meldung der Art `betrieb` wird nicht herausgefiltert, wenn der Baustein `waechter` fehlt. Das ist hier sogar gewollt, denn die Meldung soll auch ohne Wächter ankommen. Die Alterung (`MELDUNG_TAGE`) gilt wie für jede andere Art. `engine/konnektor.py:2107` gibt die Art nur als Text aus (`m['art']`). Eine unbekannte Art bricht nichts.
- `neue_meldungen` (`waechter.py:256-274`): `wiederholen=None` heißt, derselbe `schluessel` erzeugt nie eine zweite Meldung. `if not m["an"]: continue` fängt eine leere Organisatorenliste ab. Der Text enthält weder „/“ noch „http“; `datum_de(seit)` schneidet mit `[:10]` auf das Datum zu, also kein Absturz mit der ISO-Zeit.
- Kante: Für eine Reise, die noch nie veröffentlicht wurde (kein `daten.json`), liefert `veroeffentlicht()` (`waechter.py:54-59`) `None`. `rot_melden` überspringt sie stumm (`continue`, Zeile 326), die Organisator:innen erfahren nichts. Das ist Befund F002.
**Implementierer:** Zu F002: Der Betrieb bekommt den Alarm trotzdem, und die Organisator:innen einer nie veröffentlichten Reise sind aus `daten.json` nicht ermittelbar. Das ist eine Grenze der Quelle, kein Fehler, und es wird im Betrieb sichtbar. Die Spec nennt `organisator_von(d)` ausdrücklich als Quelle. Der Befund wird dokumentiert, nicht behoben.

### Runde 2
**Adversary:** Ich greife `engine/schreiben.py` an.
- Vorher-Bau (`Schreiber.vorher`, im Ablauf Zeile 2883): Er wirft `BauFehler`, dann ist `vorher` leer und es gibt keinen Abbruch. Das deckt Known Limitation 4 und R-7 ab. Läuft ein Fehler anderer Art (nicht `BauFehler`) im Vorher-Bau, würde der Schreibvorgang scheitern. Ohne den Vorher-Bau scheitert aber auch das nachfolgende `probebau` an derselben Klasse, das Verhalten ist also nicht schlechter als vorher.
- `probebau` (Zeile 2840) lehnt nur bei `BauFehler` ab. `neue_hinweise` (Zeile 2780) vergleicht Mengen von `(bezug, text)`, begrenzt auf 10 und fügt „und N weitere“ an. Das Feld `hinweise` wird nur bei einer nichtleeren Liste gesetzt, `reise_anlegen` bleibt ohne. AC-9 bis AC-12 sind belegt, die Tests sind grün.
- `start_ende_neu` (Zeile 2464) und `start_ende_setzen` (Zeile 2484): `datum_wert` liefert `date`, `None` oder `""` (`schreiben.py:1795`). Der Vergleich `v == alt` gegen das von ruamel gelesene `date` ist deshalb typgleich, und „unverändert“ führt zu „Nichts zu ändern“. `start_datum=""` und `start_ort=""` werden abgelehnt. Ort-Existenz wird gegen `roh["orte"]` geprüft (die Beispielreise führt die Orte dort, Test mit O-02 ist grün). Ende vor Start wird vor dem Speichern abgelehnt. Bei leerem `ende` wird der Eintrag gelöscht. Der Verlauf wird geschrieben. Das Werkzeug steht in `AKTIONEN` als `einstellung` (nur Organisator:innen).
- Zeit (AC-14): `ZEIT_GESAMT = 25` bleibt, der Vorher-Bau kostet etwa eine Bauzeit (Beispielreise etwa 0,1 s). `test_zeitgrenzen_liegen_unter_der_des_konnektors` ist grün.
**Implementierer:** Die Quellen stehen so in der Spec (F-8, F-10). Kein neuer Befund.

**Adversary:** Letzter Angriff auf `engine/konnektor.py`, besonders auf die Ersetzungen, die per Skript gemacht wurden.
- `ONTOLOGIE_WERKZEUGE` (Zeilen 80 bis 83) enthält `"start_ende_setzen"`, `ONTOLOGIE_AKTION` (Zeilen 91 bis 93) bildet es auf `"einstellung"` ab. Die Liste in `werkzeuge_fuer` (Zeile 3001) enthält `START_ENDE_SETZEN` neben `REISE_AENDERN` und ist an `schreibdienst()` gebunden. Die Definition steht in Zeile 2549 mit Pflichtfeld `grund`. `REISE_AENDERN` verweist jetzt auf `start_ende_setzen`. Syntax und Klammern sind intakt, 213 Tests grün.
- `hinweise_text` (Zeile 1102) wird an beiden Stellen angehängt (Zeile 1180 allgemeines Eintragen, Zeile 1465 `entscheiden`). Ohne `hinweise` ist der Text byte-gleich zum alten (leerer Anhang). Die Fehlerkennzeichen bleiben `False`. Der Schreibdienst gibt das ganze Antwort-Dict durch (`schreiben.py:2967`), das Feld geht also nicht verloren.
- Instanz- und Reisespezifisches: Die Suche in den hinzugefügten Zeilen von `betrieb/`, `engine/*.py`, `docs/betrieb.md` und `docs/konnektor.md` nach echten Namen, Adressen und E-Mail-Adressen blieb ohne Treffer. Der Alarmtext enthält nur `journalctl -u $FR_INSTANZ-veroeffentlichen`, die Instanz kommt aus der Konfiguration. Das Skript nennt keine Pfade der Instanz.
- Dokumentation (AC-33): `docs/betrieb.md` Zeilen 102 bis 108 und 143, 160 enthalten Rot-Datei, Überspringen, Alarm, Schwelle und Konvention. `betrieb/einstellungen.beispiel` enthält `FR_ROT_MELDEN_NACH_MINUTEN`.
- Restkante: Der Merker der Reisetests-Warnung (`veroeffentlichen.sh` Zeilen 170 bis 174) wird auch geschrieben, wenn `fr_melden` fehlschlägt, weil `fr_melden` Fehler zu einer Warnzeile macht (`gemeinsam.sh:72`). Die Warnung geht dann verloren. Das ist Befund F003.
**Implementierer:** Zu F003: R-4 hält `fr_melden` bewusst rückgabefrei, damit andere Aufrufer unter `set -e` nicht abbrechen. Die Warnung bleibt im Protokoll und im Test (`normal`-Stufe), ein Verlust der Nachricht betrifft nur Prioritätsstufe normal. Akzeptiert als LOW.

## Befunde und Bestätigungen

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:78
  Description: `alarm_senden` gibt ohne `FR_MELDEN` sofort 0 zurück, danach wird `gemeldet=1` gesetzt. Der Alarm gilt als gesendet, obwohl nichts ging.
  Spec requirement: AC-24 / F-6 — gemeldet bleibt 0, wenn fr_melden ausfällt
  Conflict: Nur formal, ein fehlender Meldeweg ist kein Ausfall; wird `FR_MELDEN` später in derselben Rot-Phase eingerichtet, kommt der Alarm nicht mehr.
  Remediation: Optional `gemeldet` nur bei gesetztem `FR_MELDEN` auf 1 setzen. Vertretbar wie `fr_melden` (`betrieb/gemeinsam.sh:71`).

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/waechter.py:318
  Description: `rot_melden` überspringt Reisen ohne veröffentlichte `daten.json` stumm und gibt dafür keine Meldung an Personen aus.
  Spec requirement: AC-23 / F-7 — Meldung an Organisator:innen der roten Reise
  Conflict: Eine nie veröffentlichte Reise (erster Bau scheitert) löst keine Meldung an ihre Organisator:innen aus. Der Alarm an den Betrieb kommt trotzdem.
  Remediation: Zeile in der Ausgabe ergänzen oder die Quelle um `reise.yaml` erweitern (eigenes Issue).

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:171
  Description: Der Merker `veroeffentlichen-warnung` wird geschrieben, auch wenn `fr_melden` die Nachricht nicht senden konnte.
  Spec requirement: AC-2 — Nachricht je Commit einmal
  Conflict: Bei Ausfall des Meldewegs geht die normale Warnung verloren (nur Stufe normal).
  Remediation: `fr_melden` mit Rückgabewert (wie `alarm_senden`) verwenden; optional.

Confirmation:
  AC: AC-1, AC-2, AC-3, AC-6, AC-8, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-22, AC-24, AC-25, AC-26
  Code reference: betrieb/veroeffentlichen.sh:149
  Evidence: Überspringen (Zeile 149 bis 154) ohne Stempel, Heartbeat, pytest, deploy. Rot-Datei mit seit/gemeldet (Zeilen 68 bis 75), Alarm einmal (Zeilen 82 bis 106), Schleife mit Exit 0/2/sonst (Zeilen 181 bis 187), Freischalten nur `$gut` (Zeile 190), Exit 1 ohne Stand bei roten Reisen (Zeilen 194 bis 201). 213 Tests in den vier Dateien grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4, AC-5, AC-7
  Code reference: betrieb/deploy.sh:34
  Evidence: `bauen.py ... || { ...; exit 2; }` (Zeilen 30 bis 34); pytest-Zeile 39 prüft nur `$WURZEL/engine/tests` mit `--basetemp`; die Zeile `FR_GEPRUEFT` (37) ist unverändert; andere Fehler enden mit Exit 1.
  Status: CONFIRMED

Confirmation:
  AC: AC-23
  Code reference: engine/waechter.py:318
  Evidence: `rot_melden` legt je Reise eine Meldung mit schluessel `veroeffentlichen-rot:<reise>:<seit>`, `an=organisator_von(d)`, `bezug` „reise“, Art `betrieb` an. `neue_meldungen` (Zeile 256) erzeugt dank `wiederholen=None` nie ein Duplikat; der Text enthält weder Pfade noch Adressen. Art `betrieb` steht nicht in `WAECHTER_ARTEN` (`rueckmeldungen.py:260`) und wird nicht herausgefiltert.
  Status: CONFIRMED

Confirmation:
  AC: AC-9, AC-10, AC-11, AC-12, AC-14, AC-27, AC-28, AC-29, AC-30, AC-31
  Code reference: engine/schreiben.py:2883
  Evidence: Vorher-Bau (`vorher`), Werkzeug, dann `probebau`; `neue_hinweise` (Zeile 2780) vergleicht und begrenzt auf 10; `start_ende_neu` (Zeile 2464) und `start_ende_setzen` (Zeile 2484) validieren, schreiben Verlauf und gehören zur Aktion `einstellung`. Baufehler setzt die Arbeitskopie zurück, `ZEIT_GESAMT` unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-13, AC-32
  Code reference: engine/konnektor.py:1102
  Evidence: `hinweise_text` hängt „Neue Hinweise der Prüfung“ an beiden Stellen an (Zeilen 1180 und 1465), `START_ENDE_SETZEN` (Zeile 2549) steht in der Werkzeugliste (Zeile 3001), `ONTOLOGIE_WERKZEUGE` und `ONTOLOGIE_AKTION`; `REISE_AENDERN` verweist auf `start_ende_setzen`; `docs/konnektor.md` hat die Tabellenzeile.
  Status: CONFIRMED

Confirmation:
  AC: AC-33
  Code reference: betrieb/deploy.sh:3
  Evidence: Kopfkommentar nennt die Exit-Codes; `docs/betrieb.md` Zeilen 102 bis 108 beschreiben Rot-Datei, Überspringen, Alarm, Schwelle und Konvention; `betrieb/einstellungen.beispiel` führt `FR_ROT_MELDEN_NACH_MINUTEN=30`.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
**VERIFIED**

Tests: 213 passed (vier Testdateien), 0 failed, 0 übersprungen; volle Suite 679 passed
Edge cases: geprüft, nur LOW-Befunde F001 bis F003
Regressions: keine gefunden
Checklist: 36/36 Punkte belegt

## Geprüfte Dateien

- sha256:2a69a05b0faf072d31c8552fdd58be7999d5af1a5c5268b3a1b05e96be7a3cb6  betrieb/deploy.sh
- sha256:c41b846623cc30c4cc727e890cfa2f32a76f7e760db658619ef1c589fba2a539  betrieb/veroeffentlichen.sh
- sha256:65f8b2aac03223d09b4b26662174ad53297f27b15936841661cbc52334553895  engine/konnektor.py
- sha256:6edb62776cb95894b0a80777c8c61a628403de4874525e7840515b2fb4d1a43e  engine/schreiben.py
- sha256:16796db302cca4908ab54abd79deae436618d01c3b0dd50754a0e79689f70c2d  engine/waechter.py

## Prüfbasis

- base: 3f96069250f82ce2ab6178683ff4a7c2dc2ad8b2
- blob:94e4085b93f8b63fff567395f312620330b8ddfb  betrieb/deploy.sh
- blob:432e6fc6d214f95476e00afd38dcf12dcd333d47  betrieb/veroeffentlichen.sh
- blob:6840557cd7b83da5cb7ad2e32689dd9b0334dd2b  engine/konnektor.py
- blob:7899438b75756ae2d511e8f718bdaaf1761aa318  engine/schreiben.py
- blob:68771f31b14878544b8fe872adbd947ee81dfb2b  engine/waechter.py

## Geprüfte Dateien

- sha256:2a69a05b0faf072d31c8552fdd58be7999d5af1a5c5268b3a1b05e96be7a3cb6  betrieb/deploy.sh
- sha256:c41b846623cc30c4cc727e890cfa2f32a76f7e760db658619ef1c589fba2a539  betrieb/veroeffentlichen.sh
- sha256:65f8b2aac03223d09b4b26662174ad53297f27b15936841661cbc52334553895  engine/konnektor.py
- sha256:6edb62776cb95894b0a80777c8c61a628403de4874525e7840515b2fb4d1a43e  engine/schreiben.py
- sha256:16796db302cca4908ab54abd79deae436618d01c3b0dd50754a0e79689f70c2d  engine/waechter.py

## Prüfbasis

- base: 3f96069250f82ce2ab6178683ff4a7c2dc2ad8b2
- blob:94e4085b93f8b63fff567395f312620330b8ddfb  betrieb/deploy.sh
- blob:432e6fc6d214f95476e00afd38dcf12dcd333d47  betrieb/veroeffentlichen.sh
- blob:6840557cd7b83da5cb7ad2e32689dd9b0334dd2b  engine/konnektor.py
- blob:7899438b75756ae2d511e8f718bdaaf1761aa318  engine/schreiben.py
- blob:68771f31b14878544b8fe872adbd947ee81dfb2b  engine/waechter.py
