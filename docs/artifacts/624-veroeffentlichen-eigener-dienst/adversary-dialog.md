# Adversary Dialog — 624-veroeffentlichen-eigener-dienst
Spec: docs/specs/betrieb/veroeffentlichen-eigener-dienst-624.md
Datum: 2026-11-18 19:18

## Checkliste
- [x] **Input:** Ein erfolgreiches Speichern im Schreibweg (Speicher- oder Git-Weg).
- [x] **Output:** Merker `veroeffentlichen-anstoss`; die Path-Einheit startet `<instanz>-veroeffentlichen.service`; das Skript entfernt den Merker, veröffentlicht, die Seite ist aktuell.
- [x] **Side effects:** Kein Kindprozess im Schreibdienst; Speicherspitze des Schreibdienstes entfällt; kein `NoNewPrivileges` im Lauf; ein Neustart des Schreibdienstes beendet das Veröffentlichen nicht. Ohne aktive Path-Einheit veröffentlicht der Timer (bis zu fünf Minuten Latenz).
- [x] **AC-1:** (Merker statt Prozess) GIVEN ein leeres Dienstverzeichnis und ein gesetztes `SB_VEROEFFENTLICHEN` WHEN `veroeffentlichen_anstossen` läuft THEN existiert `<FR_DIENST>/veroeffentlichen-anstoss`, und das Skript wurde nicht ausgeführt. Test: `test_anstoss_pfad_570.py::test_anstoss_legt_nur_merker`.
- [x] **AC-2:** (leer = aus) GIVEN `SB_VEROEFFENTLICHEN` ist leer WHEN der Anstoß läuft THEN wird kein Merker angelegt. Test: `test_anstoss_pfad_570.py::test_leeres_skript_legt_keinen_merker`.
- [x] **AC-3:** (wirft nie) GIVEN das Dienstverzeichnis ist nicht beschreibbar WHEN der Anstoß läuft THEN wirft die Funktion nicht, und der Fehler steht nur im Protokoll. Test: `test_anstoss_pfad_570.py::test_anstoss_wirft_nie`.
- [x] **AC-4:** (beide Wege, kein Anstoß-Protokoll) GIVEN ein erfolgreiches Speichern im Speicherweg und im Git-Weg WHEN es abgeschlossen ist THEN liegt der Merker, und `veroeffentlichen-anstoss.log` entsteht nicht. Test: `test_schreiben_speicher.py::test_speichern_legt_anstoss_merker`, `test_schreiben.py::test_git_weg_legt_anstoss_merker`.
- [x] **AC-5:** (Path-Vorlage) GIVEN `betrieb/vorlagen/veroeffentlichen.path` WHEN sie gelesen wird THEN enthält sie genau `PathExists=__DIENST__/veroeffentlichen-anstoss`, `Unit=__INSTANZ__-veroeffentlichen.service` und `WantedBy=paths.target`. Test: `test_betrieb.py::test_veroeffentlichen_path_vorlage`.
- [x] **AC-6:** (Merker vor Sperre) GIVEN `veroeffentlichen.sh` WHEN es startet, mit freier oder mit belegter Sperre THEN ist der Anstoß-Merker vor dem `flock`-Aufruf entfernt; bei belegter Sperre ist zusätzlich `veroeffentlichen-nochmal` gesetzt. Test: `test_betrieb.py::test_merker_vor_sperre_entfernt`, `test_betrieb.py::test_belegte_sperre_setzt_nochmal`.
- [x] **AC-7:** (Grenze 512M) GIVEN `schreiben.service` WHEN sie gelesen wird THEN stehen `MemoryHigh=384M`, `MemoryMax=512M`, `MemorySwapMax=256M` darin, `MemoryHigh` ist kleiner als `MemoryMax`, und der Text „bis #624“ fehlt. Test: `test_betrieb.py::test_dauerdienste_tragen_speichergrenzen` (angepasst).
- [x] **AC-8:** (Einrichten) GIVEN `betrieb/einrichten.sh` WHEN es Einheiten erzeugt und installiert THEN behandelt es `.path`-Vorlagen wie `.service` und `.timer` und aktiviert `<instanz>-veroeffentlichen.path`. Test: `test_betrieb.py::test_einrichten_aktiviert_path_einheit`.
- [x] **AC-9:** (Abgleich meldet fehlende Path-Einheit) GIVEN `EINHEITEN` in `units.py` WHEN sie gelesen wird THEN enthält sie die Path-Einheit; GIVEN sie ist nicht installiert WHEN `units.py pruefen` läuft THEN ist es eine gesperrte Abweichung (Ausgang ungleich 0), und `veroeffentlichen.sh` setzt nur eine normale Meldung ab, keinen Alarm. Test: `test_units.py::test_path_einheit_in_einheiten`, `test_units.py::test_fehlende_path_einheit_ist_gesperrt`.
- [x] **AC-10:** (Helfer unverändert) GIVEN `units-installieren.py` WHEN seine Einheitenliste gelesen wird THEN enthält sie nur die sechs `.service`-Einheiten, und `ERLAUBT` ist unverändert und gleich der in `units.py`. Test: `test_units_helfer.py::test_ac1_alle_sechs_einheiten_sind_erlaubt` (bestehend), `test_units.py::test_helfer_erlaubnisliste_gleich` (bestehend).
- [x] **AC-11:** (Messlauf) GIVEN `betrieb/messlauf-schreibweg.py` WHEN es den Anstoß in der Sandbox prüft THEN prüft es den Merker und startet kein Skript. Test: `test_betrieb.py::test_messlauf_prueft_merker`.
- [x] **AC-12:** (Doku) GIVEN `docs/betrieb.md` und `docs/specs/betrieb/speichergrenzen-538.md` WHEN sie gelesen werden THEN beschreiben sie Merker, Path-Einheit, die Grenze 512M, den Auslieferungsschritt und den Wegfall des Anstoß-Protokolls, und „bis #624“ steht nicht mehr als offener Zustand. Test: `test_betrieb.py::test_doku_beschreibt_veroeffentlichen_dienst`.
- [x] **AC-13:** (kein Kindprozess) GIVEN der Quelltext von `veroeffentlichen_anstossen` WHEN er geprüft wird THEN startet er keinen Prozess (kein `Popen`, kein `subprocess`). Test: `test_anstoss_pfad_570.py::test_anstoss_startet_keinen_prozess`.
- [x] **AC-14 (offen, Server-Nachweis nach Auslieferung, hier nicht prüfbar, als außerhalb CI vermerkt; vom PO am 18.11.2026 so freigegeben):** (Instanz umgestellt, Teil von „fertig“) GIVEN die Software ist ausgeliefert WHEN `einrichten.sh --installieren` einmal auf der Instanz gelaufen ist THEN gilt: `systemctl is-active <instanz>-veroeffentlichen.path` ist `active`; `systemctl show` für `<instanz>-schreiben` zeigt 384M, 512M und 256M; ein Anstoß aus der vorhandenen Testreise führt innerhalb von zwei Minuten zur aktuellen Seite; `units.py pruefen` endet mit 0; der Schreibdienst läuft ohne Speicherabbruch. Ausnahme mit Begründung: braucht systemd und Root auf dem echten Server und läuft nicht in CI; der Nachweis steht im Issue #624 (ohne Serverpfade, Uhrzeiten mit Zeitzone), erst dann wird es geschlossen.

## Dialog

Testlauf (adversary-test-output.txt, relative Pfade): 633 passed, 0 failed, 0 übersprungen (test_anstoss_pfad_570, test_betrieb, test_units, test_units_helfer, test_schreiben, test_schreiben_speicher). test_software_weg_454::test_f002 (vorbestehend rot, #622) nicht Teil dieses Laufs.

### Runde 1
**Adversary:** Beweise je Punkt, Code gelesen.

Confirmation:
  AC: AC-1
  Code reference: engine/schreiben.py:5674
  Evidence: merker.touch legt <instanz.dienst()>/veroeffentlichen-anstoss an; kein Popen/subprocess mehr in der Funktion (Diff gelesen). Test test_anstoss_legt_nur_merker grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/schreiben.py:5666
  Evidence: `if not self.veroeffentlichen: return` vor dem Anlegen; fehlendes Skript (#570) gibt weiter nur eine Zeile nach stderr/Journal ohne Merker, mit der Spec vereinbar (Zeilen 5668-5669).
  Status: CONFIRMED

Confirmation:
  AC: AC-3, AC-4
  Code reference: engine/schreiben.py:5675
  Evidence: `except Exception` um mkdir/touch, Fehler nur auf stderr; ein Anstoß-Protokoll (.log) wird nirgends mehr geschrieben, Tests prüfen das Fehlen für Speicherweg und Weg über die Arbeitskopie.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: betrieb/vorlagen/veroeffentlichen.path:9
  Evidence: PathExists=__DIENST__/veroeffentlichen-anstoss, Unit=__INSTANZ__-veroeffentlichen.service, WantedBy=paths.target. __DIENST__ ist in einrichten.sh dasselbe FR_DIENST wie in schreiben.service (__UMGEBUNG_DIENST__, Klon-Anordnung Environment=FR_DIENST=...; alte Anordnung aus den Einstellungen) und gleich instanz.dienst(). ReadWritePaths des Schreibdienstes enthält __DIENST__ (betrieb/vorlagen/schreiben.service:56), Schreiben trotz ProtectSystem=strict möglich.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: betrieb/veroeffentlichen.sh:1123
  Evidence: `rm -f "$FR_DIENST/veroeffentlichen-anstoss"` steht in main() vor `exec 9>` und `flock -n` (Zeile 1126); bei belegter Sperre wird veroeffentlichen-nochmal gesetzt. veroeffentlichen.service startet ExecStart=__SOFTWARE__/betrieb/veroeffentlichen.sh, das main() aufruft (Struktur unverändert).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: betrieb/vorlagen/schreiben.service:48
  Evidence: MemoryHigh=384M, MemoryMax=512M, MemorySwapMax=256M; "bis #624" entfernt.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: betrieb/einrichten.sh:138
  Evidence: Schleife nimmt *.path mit; Zeilen 231 und 241 aktivieren <instanz>-veroeffentlichen.path.
  Status: CONFIRMED

Confirmation:
  AC: AC-9, AC-10
  Code reference: betrieb/units.py:39
  Evidence: EINHEITEN-Muster enthält path; fehlt die Einheit, ist sie gesperrt (Ausgang 4, Test grün). units_abgleichen in betrieb/veroeffentlichen.sh (ab Zeile ~1321) meldet über fr_melden normal und gibt 0 zurück: kein Alarm, kein Abbruch. Root-Helfer units-installieren.py unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: betrieb/messlauf-schreibweg.py:70
  Evidence: anstoss_pruefen prüft den Merker im Sandbox-Dienstordner; das Stummelskript wird nie gestartet; Rückgabe 1, wenn der Merker fehlt.
  Status: CONFIRMED

Confirmation:
  AC: AC-12, AC-13
  Code reference: betrieb/vorlagen/veroeffentlichen.path:1
  Evidence: Doku-Test und Kein-Popen-Test grün; docs/betrieb.md:483 beschreibt den Wegfall des Anstoß-Protokolls. Reste von veroeffentlichen-anstoss.log nur in Tests (Prüfung auf Nicht-Existenz) und Doku; kein Code in engine/ oder betrieb/ erwartet die Datei (grep).
  Status: CONFIRMED

Confirmation:
  AC: Input, Output, Side effects
  Code reference: betrieb/veroeffentlichen.sh:1123
  Evidence: Kette Merker, Path-Einheit (PathExists), eigener Dienst ohne NoNewPrivileges (Vorlage veroeffentlichen.service unverändert), Neustart des Schreibdienstes beendet das Veröffentlichen nicht (eigene cgroup). Timer bleibt Rückfall.
  Status: CONFIRMED

AC-14: offen, nach Auslieferung (Nachweis auf der Instanz, kein Defekt).

**Implementierer:** (nicht beteiligt, Kontextisolation.)

### Runde 2
**Adversary:** Gezielte Angriffe auf die Endlosschleife.

Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:1123
  Description: Der Merker wird erst in main() entfernt. Davor enden Läufe per set -e/exit, ohne ihn zu löschen: gemeinsam.sh bricht ab, wenn die Einstellungsdatei vorhanden, aber unlesbar ist (betrieb/gemeinsam.sh:73), nur_bauordner (gemeinsam.sh:58) und ein fehlschlagendes `mkdir -p "$FR_DIENST"`. Der Merker bleibt, PathExists bleibt wahr, systemd startet den Dienst erneut.
  Spec requirement: Risiko Endlosschleife — Gegenmaßnahme AC-6 (Merker vor flock löschen)
  Conflict: Keine unbegrenzte Schleife: Die Start-Rate-Begrenzung von systemd greift (Standard StartLimitBurst=5 in 10 s am Dienst, danach geht die Path-Einheit auf failed). Folge: kurzer Sturm von Fehlstarts im Journal, danach ist der schnelle Anstoßweg stumm tot (Path-Einheit failed, weder Alarm noch Warnzeile); der Timer bleibt Rückfall, scheitert aber an derselben Ursache. Keine Verletzung von AC-1 bis AC-13.
  Remediation: ExecStartPre=-/bin/rm -f __DIENST__/veroeffentlichen-anstoss in der Dienst-Vorlage, oder im AC-14-Nachweis den Neustart einer failed Path-Einheit (reset-failed) festhalten; optional Teil-Check für failed Path-Einheit in monitor.sh.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/vorlagen/veroeffentlichen.path:9
  Description: Wird die Path-Einheit nach der Auslieferung nicht aktiviert (nur ausgegebener Befehl, betrieb/einrichten.sh:231), veröffentlicht nur der Timer, bis zu 5 Minuten später; units.py meldet die fehlende Einheit nur normal (AC-9, betrieb/units.py:39).
  Spec requirement: AC-9, AC-14
  Conflict: Keine Verletzung; AC-14 ist zwingend vor dem Schließen von #624.
  Remediation: AC-14 ausführen (is-active der Path-Einheit).

Ohne Befund: Rennen Merker anlegen nach rm (Anstoß während des Laufs): PathExists prüft nach Ende des oneshot-Dienstes neu, dazu veroeffentlichen-nochmal, kein Verlust. Merker schon vor Aktivierung der Path-Einheit da: löst einen Lauf aus, harmlos. Schreibrechte: Dienstbenutzer gleich, ReadWritePaths enthalten FR_DIENST. Fehlendes Skript (#570): kein Merker, Journalzeile, spec-konform (engine/schreiben.py:5668). Alte Anordnung: FR_DIENST in beiden Einheiten aus denselben Einstellungen (betrieb/einrichten.sh:43-47). Messlauf endet mit 1, wenn der Merker fehlt (betrieb/messlauf-schreibweg.py), nur dieses Werkzeug betroffen.

**Implementierer:** (nicht beteiligt.)

### Runde 3
**Adversary:** Nachbesserung zu F001 geprüft.

Confirmation:
  AC: F001 (Endlosschleife der Path-Einheit)
  Code reference: betrieb/vorlagen/veroeffentlichen.service:21
  Evidence: `ExecStartPre=-/bin/rm -f __DIENST__/veroeffentlichen-anstoss` steht vor ExecStart (Zeile 22). einrichten.sh ersetzt __DIENST__ für alle Vorlagen gleich (betrieb/einrichten.sh:127), also derselbe Pfad wie in der Path-Vorlage und instanz.dienst(). Der Merker fällt nun vor jedem Skriptstart, auch bei frühem Abbruch (gemeinsam.sh, mkdir); das Präfix `-` lässt einen rm-Fehler den Start nicht verhindern (rm -f meldet ohnehin 0 bei fehlender Datei). Timer-Läufe: der Merker wird dort ebenfalls entfernt, der Lauf veröffentlicht ohnehin den neuesten Stand; ein Anstoß während eines laufenden Dienstes wird von systemd als wartender Start nachgeholt und löscht den Merker erst vor diesem Start. Die Entfernung in betrieb/veroeffentlichen.sh:1123 bleibt als zweite Absicherung. Tests: test_betrieb.py und test_units.py 294 passed, 0 failed.
  Status: CONFIRMED

Status F001: GESCHLOSSEN (Behebung bestätigt). Restrisiko: ein Abbruch nach dem Löschen setzt keinen neuen Merker, keine Schleife.

**Implementierer:** (nicht beteiligt.)

### Runde 4
**Adversary:** Nachgebesserte Spec (Entscheidung 3, Risiken) und neue Tests gegen den Code geprüft; Code seit Runde 3 unverändert. Testlauf: `adversary-test-output.txt`.

Confirmation:
  AC: Entscheidung 3 (zweite Sicherung ExecStartPre)
  Code reference: betrieb/vorlagen/veroeffentlichen.service:21
  Evidence: `ExecStartPre=-/bin/rm -f __DIENST__/veroeffentlichen-anstoss` steht genau einmal und vor `ExecStart=` (Zeile 22). Der Pfad ist derselbe Platzhalter `__DIENST__` wie in `PathExists=` der Path-Vorlage; `ersetze()` in einrichten.sh setzt ihn für alle Vorlagen gleich. Das Präfix `-` verhindert, dass ein rm-Fehler den Start blockiert. Wirkung bei Timer-Läufen: der Merker wird ebenfalls entfernt, der Lauf veröffentlicht ohnehin den neuesten Stand; ein Anstoß während des Laufs legt den Merker neu, PathExists startet danach erneut.
  Status: CONFIRMED

Confirmation:
  AC: Neue Tests prüfen mehr als trivial
  Code reference: engine/tests/test_betrieb.py:2624
  Evidence: `test_veroeffentlichen_service_entfernt_merker_vor_start` filtert Kommentare, verlangt genau ein Vorkommen der Zeile (count == 1) und Index vor dem einzigen `ExecStart=`. Ein entfernter, doppelter, nachgestellter oder auskommentierter rm würde rot. Schwäche (LOW, F003): prüft Reihenfolge und Text, nicht, dass der Pfad dem der Path-Vorlage entspricht; das deckt die Zusicherung in `test_einrichten_erzeugt_einheiten_ohne_platzhalter` (Platzhalter ersetzt) nur indirekt.
  Status: CONFIRMED

Confirmation:
  AC: Schreibweg legt nur den Merker an
  Code reference: engine/schreiben.py:5672
  Evidence: `merker = instanz.dienst() / "veroeffentlichen-anstoss"`, `mkdir`, `touch`, Fehler nur nach stderr; kein Prozessstart. Gleicher Dateiname wie im Dienst und im Skript.
  Status: CONFIRMED

Confirmation:
  AC: Skript-rm bleibt zweite Absicherung
  Code reference: betrieb/veroeffentlichen.sh:1123
  Evidence: `rm -f "$FR_DIENST/veroeffentlichen-anstoss"` vor `exec 9>` und flock; `test_merker_vor_sperre_entfernt` (test_betrieb.py:2635) prüft Reihenfolge und Lauf.
  Status: CONFIRMED

Confirmation:
  AC: Gesperrte Einheiten / Messlauf
  Code reference: betrieb/units.py:17
  Evidence: Path-Einheiten und neue Zeilen wie ExecStartPre stehen nicht in ERLAUBT und werden nur gemeldet, nie automatisch installiert (Sicherheitsgrenze unverändert). Messlauf: `betrieb/messlauf-schreibweg.py:72` prüft den Merker statt eines Prozessstarts.
  Status: CONFIRMED

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/units.py:60
  Description: Bestehende Instanzen haben die installierte veroeffentlichen.service ohne ExecStartPre; `schluessel()` kennt ExecStartPre nicht, die Abweichung wird als gesperrt gemeldet und nicht automatisch eingespielt.
  Spec requirement: Entscheidung 3 (zweite Sicherung)
  Conflict: Auf bereits eingerichteten Instanzen fehlt die zweite Sicherung, bis `einrichten.sh` mit sudo neu läuft; die erste Sicherung (Skript-rm) wirkt weiter. Bewusste Sicherheitsgrenze, kein Defekt.
  Remediation: Beim Ausliefern einmal einrichten.sh laufen lassen (wie für die Path-Einheit); keine Codeänderung.

Status: Keine Spec-Verletzung gefunden, F003 nur Hinweis.

**Implementierer:** (nicht beteiligt.)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 634 passed, 0 failed, 0 übersprungen.
Edge cases: F001 (MEDIUM, in Runde 3 geschlossen durch ExecStartPre), F002 und F003 (beide LOW) dokumentiert, keine Spec-Verletzung.
Regressions: keine gefunden.
Checklist: 16/17 bewiesen; AC-14 offen, nach Auslieferung (kein Defekt).

## Geprüfte Dateien

- sha256:17925d65786135ed0756dacff5a8e875129204cda4488f4f1179a2c29c64c23e  betrieb/einrichten.sh
- sha256:057289a8699cbcc5373c980e0972161ee950935da36e4a7c13c34e494f89529f  betrieb/messlauf-schreibweg.py
- sha256:b7403e8fbd4261728334feba6dc2dce3d807983757c517cfc49317d868bedf93  betrieb/units.py
- sha256:3c0587e571b1a103da61316b76b467cca60a3a1366d2da986f02ee7c59ef0e32  betrieb/veroeffentlichen.sh
- sha256:bdcee2f95cc636b3ff050d2ed75d0926e8d2269adf366707b9972f230968fda8  betrieb/vorlagen/schreiben.service
- sha256:63c1a7e8c87ff3ecf18af0c57c5d4812006e0be995a7824f1ee72311bf65c93d  betrieb/vorlagen/veroeffentlichen.path
- sha256:f264d684b44f34f52b214f7915cd21d0bed49ae646b36067275479dc0836ae1e  betrieb/vorlagen/veroeffentlichen.service
- sha256:caf9e78605059b1ce0b912699489563c03ea03fcd727f7768560d1a10d1564bc  engine/schreiben.py
- sha256:9e241d8554145597fe96e523da4dd0072cfe4b1c527bcc6214eff5c5f4078b2f  engine/tests/test_betrieb.py

## Prüfbasis

- base: b809523b37ef8d17fc67893b234912851fdfa25c
- blob:eefc314c24d579b148118c22ac425b2782185881  betrieb/einrichten.sh
- blob:80ce70bc941da859bf8cfbb4ce97688f34015cb8  betrieb/messlauf-schreibweg.py
- blob:6d0357dc7e6a3214497682149f564f934dd6d217  betrieb/units.py
- blob:7ff14e53992b5b8aa94f1cb6528b46ddbaf32a4b  betrieb/veroeffentlichen.sh
- blob:744d8255ada19bfdc8bda083c1273fcc2f73c097  betrieb/vorlagen/schreiben.service
- blob:effd74d637cd928a70d6e41f090d072d0a8ba675  betrieb/vorlagen/veroeffentlichen.path
- blob:b00fb737b2635658b630683fb4b2f8381c5b7d02  betrieb/vorlagen/veroeffentlichen.service
- blob:b9f6707a36986abf189dc869095c46ed1b8b0aab  engine/schreiben.py
- blob:996895d809d875b8797b707b20fdf12cb21992a5  engine/tests/test_betrieb.py
