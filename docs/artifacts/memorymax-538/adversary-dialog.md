# Adversary Dialog — memorymax-538
Spec: docs/specs/betrieb/speichergrenzen-538.md
Datum: 2026-11-17 18:34

## Checkliste
- [x] **Input:** Vorlagen der vier Dauerdienste, installierte Units der Instanz.
- [x] **Output:** Units mit den drei Zeilen je Dienst; `units.py pruefen` endet mit 0, wenn installiert und Vorlage übereinstimmen.
- [x] **Side effects:** Überschreitet ein Dienst `MemoryHigh`, wird er gedrosselt; überschreitet er `MemoryMax` oder `MemorySwapMax`, beendet systemd Prozesse seiner cgroup (Neustart durch den Dienst-Manager nach den vorhandenen `Restart=`-Vorgaben). Beim Schreibweg bedeutet das für ein laufendes angestoßenes Veröffentlichen: kein Fehler an den Aufrufer, die Sperre ist frei, der Timer (alle 5 Minuten) holt nach.
- [x] **AC-1:** (Grenzen vorhanden) GIVEN die Vorlagen `rueckmeldungen`, `push`, `konnektor`, `schreiben` WHEN sie gelesen werden THEN enthält jede genau eine Zeile `MemoryHigh=`, `MemoryMax=` und `MemorySwapMax=` mit den Werten aus Entscheidung 2. Test: `test_betrieb.py::test_dauerdienste_tragen_speichergrenzen`.
- [x] **AC-2:** (weich vor hart) GIVEN die Werte einer Vorlage WHEN sie in Megabyte umgerechnet werden (G = 1024 M) THEN ist `MemoryHigh` kleiner als `MemoryMax`. Test: `test_betrieb.py::test_speicher_high_kleiner_max`.
- [x] **AC-3:** (Veröffentlichen ohne Grenze) GIVEN `veroeffentlichen.service` WHEN die Vorlage gelesen wird THEN steht keine Zeile `MemoryHigh`, `MemoryMax` oder `MemorySwapMax` darin. Test: `test_betrieb.py::test_veroeffentlichen_ohne_speichergrenze`.
- [x] **AC-4:** (Erlaubnisliste erweitert) GIVEN `ERLAUBT` in `units.py` WHEN die Schlüssel gelesen werden THEN enthält sie genau die früheren Einträge plus `("Service","MemoryHigh")`, `("Service","MemoryMax")`, `("Service","MemorySwapMax")`, und keine Sandbox- oder Benutzerzeile. Test: `test_units.py::test_erlaubnisliste_schluessel` (bestehender Test, feste Namensliste erweitert).
- [x] **AC-5:** (Listen gleich) GIVEN `ERLAUBT` in `units.py` und im Hilfsprogramm WHEN sie verglichen werden THEN sind sie in Schlüsseln und Mustern identisch. Test: `test_units.py::test_helfer_erlaubnisliste_gleich` (bestehender Test).
- [x] **AC-6:** (gültige Werte) GIVEN die Werte `256M`, `1G`, `4G`, `99999M` WHEN sie gegen das Muster geprüft werden THEN werden sie angenommen, in `units.py` und im Hilfsprogramm. Test: `test_units.py::test_speicherwert_gueltig`, `test_units_helfer.py::test_speicherwert_gueltig`.
- [x] **AC-7:** (Negativfälle des Musters) GIVEN `infinity`, `0`, `0M`, `50%`, `512K`, `1T`, `0256M`, `100000M` (zu lang), `256m`, `256` (ohne Einheit) und `256M` mit Zeilenumbruch am Ende WHEN sie geprüft werden THEN wird jeder abgelehnt, in `units.py` wie im Hilfsprogramm. Test: `test_units.py::test_speicherwert_ungueltig`, `test_units_helfer.py::test_speicherwert_ungueltig`.
- [x] **AC-8:** (Installation einer Grenz-Abweichung) GIVEN eine installierte Unit, die sich von der Vorlage nur in einer Grenzzeile mit gültigem Wert unterscheidet WHEN der Abgleich läuft THEN gilt sie als erlaubte Abweichung und das Hilfsprogramm installiert sie; GIVEN sie enthält zusätzlich eine nicht erlaubte Zeile THEN installiert das Hilfsprogramm nichts. Test: `test_units_helfer.py::test_grenzabweichung_wird_installiert`, `test_units_helfer.py::test_gemischte_abweichung_wird_nicht_installiert`.
- [x] **AC-9:** (ungültiger Wert gesperrt) GIVEN eine Grenzzeile mit ungültigem Wert WHEN `units.py pruefen` läuft THEN ist sie eine gesperrte Abweichung (Ausgang ungleich 0), das Hilfsprogramm installiert nichts, und `veroeffentlichen.sh` setzt nur eine normale Meldung ab, keinen Alarm. Test: `test_units.py::test_ungueltige_grenze_ist_gesperrt`, `test_betrieb.py::test_units_abweichung_nur_normale_meldung` (bestehende Prüfung der Meldestufe um diesen Fall ergänzt).
- [x] **AC-10:** (alter Helfer) GIVEN ein Hilfsprogramm mit der alten Erlaubnisliste ohne die drei Schlüssel WHEN eine Grenzzeile abweicht THEN ist sie eine gesperrte Abweichung, die genau eine normale Meldung auslöst (Merker `units-gemeldet`, kein Alarm, keine Wiederholung bei jedem Lauf). Test: `test_units.py::test_alter_helfer_nur_normale_meldung`.
- [x] **AC-11:** (Doku) GIVEN `docs/betrieb.md` und `docs/specs/betrieb/dienstrechte-552.md` WHEN sie gelesen werden THEN nennt `betrieb.md` die drei Schlüssel, das Muster, die Werte und den Einmalschritt (Absatz „Speichergrenzen (#538)“), und Entscheidung 8 der Spec 552 nennt die Abgrenzung Ressourcengrenzen gegen Sandbox-Werte. Test: `test_betrieb.py::test_doku_beschreibt_speichergrenzen`.
- [x] **AC-12 (offen, Server-Nachweis nach Auslieferung, hier nicht prüfbar, als außerhalb CI vermerkt):** (Instanz umgestellt, Teil von „fertig“) GIVEN die Software ist ausgeliefert WHEN `einrichten.sh --installieren` einmal mit Root-Rechten auf der Instanz gelaufen ist THEN liefert `systemctl show -p MemoryHigh -p MemoryMax -p MemorySwapMax <dienst>` für jeden der vier Dienste die Werte aus Entscheidung 2, `veroeffentlichen.service` zeigt `infinity`, `units.py pruefen` endet mit 0, und Schreiben, Veröffentlichen und ein Seitenbild über den Konnektor laufen danach ohne Fehler durch. Ausnahme mit Begründung: Der Nachweis braucht systemd und Root auf dem echten Server und läuft nicht in CI; er wird im Issue #538 festgehalten (ohne Serverpfade), erst dann wird es geschlossen.

## Dialog

### Runde 1
**Adversary:** Testlauf selbst ausgeführt (`adversary-test-output.txt`): `test_betrieb.py`, `test_units.py`, `test_units_helfer.py`: 418 passed, 0 failed, 0 übersprungen. Muster-Randfälle selbst gegen BEIDE ERLAUBT-Listen geprüft (Skript im Scratchpad): akzeptiert werden `256M`, `1G`, `4G`, `99999M`; abgelehnt werden `infinity`, `0`, `0M`, `50%`, `512K`, `1T`, `0256M`, `100000M`, `256m`, `256`, `256M\n`, `１56M`-artige Unicode-Ziffern (`２56M`, `1٣M`), führendes/folgendes Leerzeichen, `+256M`, `256 M`, `256MB`, NUL-Byte. Die Pattern-Strings beider Listen sind identisch (Vergleich: True).
Regressionsprobe `.match` -> `.fullmatch`: Für TimeoutStartSec, FR_ZEITZONE, FR_DIENST ändert sich das Ergebnis nur bei Werten mit angehängtem Zeilenumbruch (`90\n`, `Europe/Berlin\n`, `/srv/x\n`: früher angenommen, jetzt abgelehnt); alle echten Werte (`90`, `5min`, `1h`, `10s`, `Europe/Berlin`, `UTC`, `/srv/x`) bleiben gleich angenommen, Negativfälle (`0`, `1 h`, `100000`, `/srv/../x`, `relativ`) bleiben abgelehnt. Zeilen werden zudem vorher mit strip/split getrennt (units.py:46-47), ein Zeilenumbruch im Wert kommt real nicht vor. Keine Verhaltensänderung für echte Einträge.
Vorlagen: per awk geprüft, alle neun Werte stehen im Abschnitt `[Service]` und stimmen exakt mit der Tabelle in Entscheidung 2 überein (rueckmeldungen/push 192M/256M/128M, konnektor 768M/1G/256M, schreiben 4G/5G/1G); `veroeffentlichen.service` enthält kein `Memory*`. `einrichten.sh` übernimmt die Vorlagen nur per `sed` mit `__PLATZHALTER__`-Ersetzung (Zeile 125-134); die Memory-Zeilen enthalten keinen Platzhalter, werden also unverändert übernommen. `veroeffentlichen.sh` `units_abgleichen` (Zeile 1315-1342): Rückgabecodes 3/4 führen nur zu `fr_melden normal`, nie `high`; Test `test_units_abweichung_nur_normale_meldung` (stub exit 4, `MemoryMax=infinity`) prüft `not hoch(vf)` und keine Wiederholung.
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Gezielt gesucht nach Lücken. (a) Spec-Wortlaut AC-11: Entscheidung 8 von Spec 552 (Zeile 33) lautet unverändert „Unit-Änderungen nicht in `ERLAUBT`“ ohne Verweis; die Abgrenzung steht nur im Changelog (Zeile 245). Der Zweck (dokumentierte, auffindbare Abgrenzung, Test erzwingt sie) ist erfüllt, der Wortlaut von AC-11 („Entscheidung 8 ... nennt die Abgrenzung“) und AC-11 in Spec 538 selbst wurden aber nicht angepasst; ein Leser nur von Entscheidung 8 sieht einen scheinbaren Widerspruch. Begründung für die Abweichung (gesperrter Text, Hook) ist in Known Limitations dokumentiert -> LOW. (b) Testnamen: Spec nennt `test_erlaubnisliste_schluessel` und `test_helfer_erlaubnisliste_gleich`, real heißen sie `test_erlaubnisliste_ist_eine_feste_namensliste` (test_units.py:115) und `test_ac5_erlaubnisliste_ist_in_helfer_und_units_py_gleich` (test_units_helfer.py:206); beide laufen grün, nur der Name in der Spec ist veraltet -> LOW. (c) Semantik: Das Muster kann nicht erzwingen, dass MemoryHigh < MemoryMax in einer abweichenden installierten Unit gilt (z. B. `MemoryMax=1M` oder High > Max); AC-2 prüft nur die Vorlagen. Folge ist höchstens Neustart des Dienstes (Verfügbarkeit), laut Spec Entscheidung 6 bewusst akzeptiert -> LOW, kein Defekt. (d) Alter Helfer: `test_alter_helfer_meldet_einmal_normal` (test_betrieb.py:2514) belegt Ausgang 5 -> genau eine normale Meldung, Merker `units-gemeldet`, keine Wiederholung. (e) AC-12 ist ein Server-Nachweis nach dem Ausliefern, hier nicht prüfbar: offen, außerhalb CI, kein BROKEN. (f) Bekannte Ausnahme test_software_weg_454::test_f002 (#622) lag nicht im geprüften Umfang und wurde nicht bewertet.
**Implementierer:** (nicht beteiligt)

### Findings
Finding:
  ID: F001
  Severity: LOW
  Category: spec_violation
  Code reference: docs/specs/betrieb/dienstrechte-552.md:33
  Description: Entscheidung 8 trägt weiter den Satz „Unit-Änderungen nicht in ERLAUBT“; die Abgrenzung steht nur im Changelog (Zeile 245).
  Spec requirement: AC-11 — Entscheidung 8 der Spec 552 nennt die Abgrenzung
  Conflict: Wortlaut nicht erfüllt; Zweck erfüllt (datierter Nachtrag, Test liest ihn, in Known Limitations begründet).
  Remediation: Beim nächsten freigegebenen Eingriff in Spec 552 einen Verweis in Entscheidung 8 ergänzen; AC-11 der Spec 538 an die Ablage im Changelog anpassen.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/units.py:34
  Description: Das Muster prüft jeden Wert einzeln; High < Max und plausible Mindestgröße für eine abweichende installierte Unit werden nicht erzwungen.
  Spec requirement: AC-2 — High kleiner als Max (nur für Vorlagen)
  Conflict: Eine abweichende Unit kann z. B. MemoryMax=1M tragen und wird als erlaubt installiert; Folge nur Neustart des Dienstes, von Entscheidung 6 akzeptiert.
  Remediation: Keine nötig; optional Hinweis in docs/betrieb.md.

Finding:
  ID: F003
  Severity: LOW
  Category: anti_pattern
  Code reference: betrieb/vorlagen/units-installieren.py:35
  Description: Spec nennt zwei Testnamen, die so nicht existieren (siehe Runde 2 b).
  Spec requirement: AC-4, AC-5 — Verweis auf bestehende Tests
  Conflict: Nur Namensabweichung, Tests laufen grün.
  Remediation: Namen in der Spec berichtigen.

## Bestätigungen
Confirmation:
  AC: AC-1
  Code reference: betrieb/vorlagen/schreiben.service:46
  Evidence: Je Vorlage genau drei Memory-Zeilen in [Service] mit den Werten der Tabelle (awk-Prüfung, Test grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: betrieb/vorlagen/konnektor.service:30
  Evidence: High < Max in allen vier Vorlagen; Test test_speicher_high_kleiner_max grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: betrieb/vorlagen/veroeffentlichen.service:1
  Evidence: grep Memory liefert keinen Treffer; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: betrieb/units.py:34
  Evidence: ERLAUBT enthält die drei neuen Schlüssel, keine Sandbox- oder User-Einträge; Namenslistentest grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: betrieb/vorlagen/units-installieren.py:40
  Evidence: Pattern-Strings beider Listen identisch (eigener Vergleich), Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: betrieb/units.py:71
  Evidence: gültige Werte werden in beiden Listen per fullmatch angenommen (eigene Probe).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/vorlagen/units-installieren.py:107
  Evidence: alle Negativfälle plus Unicode-Ziffern, Leerzeichen, +, NUL abgelehnt (eigene Probe); fullmatch lehnt Zeilenumbruch ab.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: betrieb/vorlagen/units-installieren.py:104
  Evidence: test_grenzabweichung_wird_installiert und test_gemischte_abweichung_wird_nicht_installiert grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: betrieb/units.py:92
  Evidence: ungültiger Wert -> gesperrt (wanted); veroeffentlichen.sh:1334 sendet nur normal; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: betrieb/units.py:68
  Evidence: alter Helfer: Ausgang 5, eine normale Meldung, Merker, keine Wiederholung (Test grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: docs/betrieb.md:446
  Evidence: betrieb.md nennt Schlüssel, Muster, Werte, Einmalschritt; Abgrenzung als Nachtrag im Changelog der Spec 552 (siehe F001, Zweck erfüllt).
  Status: CONFIRMED

AC-12: offen, Server-Nachweis nach dem Ausliefern, nicht in CI prüfbar (kein BROKEN).

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Es werden keine Felder von Produktionscode neu geschrieben; die Änderung betrifft nur Vorlagen und Muster.

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hielt dem Angriff stand.
Tests: 418 passed, 0 failed, 0 übersprungen
Edge cases: alle geprüft, keine gebrochen (3 LOW-Hinweise F001-F003)
Regressions: keine (.fullmatch ändert nur Werte mit Zeilenumbruch am Ende)
Checklist: AC-1 bis AC-11 bewiesen; AC-12 offen (Server-Nachweis, außerhalb CI)

## Geprüfte Dateien

- sha256:6b80489b80ff34e1ce05e0f49af48b001503aa2e54730e396d387ae29367553f  betrieb/units.py
- sha256:605ca991108affad37a17181a5647f5e6eff029a0bab6a23fd349f54ab87240a  betrieb/vorlagen/konnektor.service
- sha256:afef50a2eceef899668ba106f9c57bf35133241975bd2b3048101b6b27ff1220  betrieb/vorlagen/schreiben.service
- sha256:d15e62d3ca20632e915d1db1147cdff459594a5dff463752d18a4c8367f19f5b  betrieb/vorlagen/units-installieren.py
- sha256:581c40355a6f3f51ca557a5c78f6254a6928d0fc4078ad6693fbedf2112a01e2  betrieb/vorlagen/veroeffentlichen.service
- sha256:e1ee8427dd30095351e0097f7ba824e4d5c27a1a79edd9afab5201ab1584de05  docs/betrieb.md
- sha256:753cf4874cc450e05079fe36f3110a25236d75e7168f8c74a26052bad02decee  docs/specs/betrieb/dienstrechte-552.md

## Prüfbasis

- base: 275835c8db55d49678231d8e01726419ac6ba647
- blob:64670a4b0cc222c0de8cc3600db06f0720e983b2  betrieb/units.py
- blob:1e644615ad0d4a21a4ef7072ff2802752bb5bd89  betrieb/vorlagen/konnektor.service
- blob:6f70d5b26bceba368eec4dbb7dab95fa66c340ee  betrieb/vorlagen/schreiben.service
- blob:ed38b7c1452b4b739c9901599e086ec40bfdaac0  betrieb/vorlagen/units-installieren.py
- blob:f31fad10751eee6d0e7a254622f141fda94d8179  betrieb/vorlagen/veroeffentlichen.service
- blob:c0b86de2716b42a77627f1383e041c5b314d8912  docs/betrieb.md
- blob:d303487d5e692958ebddf98e1d0f30a51ecac17f  docs/specs/betrieb/dienstrechte-552.md
