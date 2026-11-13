# Adversary Dialog — software-weg-454
Spec: docs/specs/betrieb/software-weg-454.md
Datum: 2026-11-13 07:47

## Checkliste
- [x] **AC-1.1:** *Given* der Speicher enthält Reisen und `FR_SPEICHERREISEN` ist leer oder nennt andere Namen, *when* `instanz.speicherreisen()` aufgerufen wird, *then* sind es genau die Reisen mit Eintrag im Speicher.
- [x] **AC-1.2:** *Given* `FR_SPEICHERREISEN` ist in der Umgebung oder Einstellungsdatei gesetzt, *when* eine Reise nicht im Speicher steht, *then* gilt sie nicht als Speicherreise (Wert wirkungslos, keine Fehlermeldung).
- [x] **AC-1.3:** *Given* der Speicher ist nicht lesbar, *when* `speicherreisen()` aufgerufen wird, *then* wird ein Fehler ausgelöst (fail closed, #361), nie eine leere Liste.
- [x] **AC-1.4:** *Given* eine Speicher-Instanz, *when* `reise_anlegen` für die Vorlage der Beispielreise (Wanderung) und für das Stadtwochenende aufgerufen wird, *then* liegt jeweils ein Anfangsvorgang im Speicher und kein Ordner `reisen/<name>` im Bauordner.
- [x] **AC-1.5:** *Given* eine neu angelegte Reise, *when* der Lauf des Veröffentlichens läuft, *then* baut der Speicher-Teil sie und die Seite wird veröffentlicht, ohne dass der Git-Teil sie anfasst.
- [x] **AC-1.6:** *Given* eine Reise liegt in Git und ist inhaltsgleich im Speicher darstellbar (beide Beispielreisen), *when* der Lauf läuft, *then* wird sie umgeschaltet: Anfangsvorgang, Stempel `gleich`, Reise steht in `speicherreisen()`, Lauf bleibt grün.
- [x] **AC-1.7:** *Given* der Vergleich einer Git-Reise ergibt „unterschiedlich“ oder Fehler, *when* der Lauf läuft, *then* bleibt die Reise in Git, nichts wird gelöscht oder geändert, es gibt eine Warnzeile mit Grund und keine Meldung der Stufe `high`.
- [x] **AC-1.8:** *Given* eine Reise ist schon umgeschaltet, *when* der Lauf erneut läuft, *then* ändert sich nichts (kein zweiter Anfangsvorgang, gleicher Stand).
- [x] **AC-1.9:** *Given* die Umschaltung läuft, *when* sie nach dem Anfangsvorgang und vor dem Stempel abbricht, *then* gilt die Reise bis dahin weiter als Git-Reise, und der nächste Lauf setzt die Umschaltung fort: erneuter Vergleich gegen den vorhandenen Anfangsvorgang, bei „gleich“ Stempel; kein zweiter Anfangsvorgang, kein Handschritt.
- [x] **AC-1.10:** *Given* eine Instanz, die vor Lieferung 1 Reisen über `FR_SPEICHERREISEN` im Speicher hatte, *when* die neue Software läuft, *then* bleiben diese Reisen im Speicher und ihre Seiten unverändert (kein Handschritt, #250).
- [x] **AC-1.11:** *Given* die Schreib-Werkzeuge des Konnektors, *when* sie auf eine Reise im Speicher angewendet werden, *then* verhalten sie sich wie zuvor (Namen, Parameter, Texte unverändert).
- [x] **AC-2.1 (Abruf):** *Given* ein neuer Commit auf `main` der Software, *when* der Lauf läuft, *then* wird er ohne Reisen-Repo, ohne GitHub-Workflow der Instanz und ohne Anmeldung geholt und (nach Prüfung) eingespielt.
- [x] **AC-2.2 (Prüfung vor Umschalten):** *Given* ein neuer Commit `C` ohne gültigen Nachweis, *when* die Tests auf dem Server rot sind, *then* zeigt `HEAD` des Klons weiter auf den bisherigen Commit, und der Arbeitsbaum des Klons ist unverändert.
- [x] **AC-2.3 (Nachweis):** *Given* alle Pflichtprüfungen von `C` sind auf GitHub grün, *when* der Lauf läuft, *then* wird der Klon auf `C` vorgespult, ohne die Tests auf dem Server zu wiederholen.
- [x] **AC-2.4 (Nachweis nur je Stand):** *Given* derselbe Commit `C` wird in mehreren Läufen gesehen, *when* der Nachweis fehlt, *then* wird er nur einmal je Stand abgefragt.
- [x] **AC-2.5 (Rückfall):** *Given* `C` ist rot oder der Deploy mit `C` scheitert, *when* der Lauf endet, *then* arbeiten die Dienste weiter mit dem Commit aus `<FR_DIENST>/software-gut`, und die Seiten der Reisen bleiben auf ihrem letzten guten Stand.
- [x] **AC-2.6 (Rot-Datei):** *Given* `C` ist rot, *when* der nächste Lauf denselben `C` sieht, *then* wird er nicht erneut geprüft („Bekannter roter Stand“), und erst nach Ablauf der Schwelle gibt es genau einen Alarm der Stufe `high` je Rot-Phase.
- [x] **AC-2.7 (Kennung):** *Given* `veroeffentlicht` und `software_kennung`, *when* ein Lauf grün endet, *then* sind beide der Commit der Software, und `software-gut` trägt denselben Commit.
- [x] **AC-2.8 (Nachziehen der Reisen):** *Given* ein neuer Software-Commit, *when* er veröffentlicht ist, *then* zieht der Speicher-Teil jede Reise (Wanderung und Stadtwochenende) auf die neue Kennung nach (`neu.py nachziehen-speicher`, nur bei grünem Probebau).
- [x] **AC-2.9 (Einstellungen):** *Given* `<FR_DIENST>/instanz/einstellungen.env` liegt vor, *when* ein Skript startet, *then* kommen Einstellungen aus der Umgebung, sonst aus dieser Datei, sonst (Übergang) aus dem alten Ort.
- [x] **AC-2.10 (Meldeweg):** *Given* `<FR_DIENST>/instanz/melden.sh`, *when* eine Meldung ausgelöst wird, *then* ruft `FR_MELDEN` diesen Weg auf; ohne Meldeweg wird nichts gesendet.
- [x] **AC-2.11 (Python-Umgebung):** *Given* die Python-Umgebung liegt unter `<FR_DIENST>/python`, *when* der Klon umgeschaltet oder zurückgesetzt wird, *then* bleibt sie erhalten; ändert sich `requirements` im Commit, wird sie vor dem Umschalten der Dienste neu aufgebaut.
- [x] **AC-2.12 (Umzug ohne Handschritt des Betreibers):** *Given* eine Instanz im alten Zustand (Submodul im Bauordner), *when* der Lauf mit der Software dieses Commits läuft, *then* legt er den Klon an, kopiert Einstellungen und Meldeweg, baut und prüft die Python-Umgebung, ohne dass jemand etwas tut; weichen die Units nur in gesperrten Zeilen ab (`ExecStart`, `FR_WURZEL`), bleibt er mit einer Warnzeile je Commit beim alten Weg, ohne die Units zu ändern. Sind die Units (einmalig bei der Auslieferung, Entscheidung 10, Schritt 4) auf den Klon umgestellt, läuft der nächste Lauf aus dem Klon, setzt den Zustand auf `fertig` und endet grün.
- [x] **AC-2.13 (Units zuletzt):** *Given* ein Schritt des Umzugs (1 bis 3) scheitert oder die Prüfung der Units (`units.py pruefen`) meldet gesperrte Abweichungen (Lauf schreibt nur die Warnzeile, stellt nichts um), *when* der Lauf endet, *then* zeigen alle Units unverändert auf den alten Bauordner, das Veröffentlichen läuft weiter über den alten Weg, und der nächste Lauf versucht den Umzug erneut.
- [x] **AC-2.14 (Wiederholbar):** *Given* der Umzug ist `fertig` oder halb durchgeführt, *when* der Lauf erneut läuft, *then* ändert er nichts Unnötiges (keine doppelten Kopien, kein Überschreiben neuerer Einstellungen, keine Units-Änderung ohne Unterschied).
- [x] **AC-2.15 (Alter Bauordner bleibt):** *Given* der Umzug ist `fertig`, *when* der alte Bauordner betrachtet wird, *then* ist er unverändert (nichts gelöscht, keine Datei verändert); der Rückweg (Units bewusst mit `einrichten.sh --installieren` aus dem alten Bauordner zurückstellen, Zustand `alt`) ist in `docs/betrieb.md` beschrieben, und ein Lauf mit Zustand `alt` startet keinen neuen Umzug.
- [x] **AC-2.16 (Selbstaustausch):** *Given* das Vorspulen des Klons ändert `veroeffentlichen.sh`, *when* der Lauf weiterläuft, *then* startet er mit `exec` das neue Skript neu und endet genau einmal mit einem Ergebnis (kein Mischlauf aus altem und neuem Code).
- [x] **AC-2.17 (Anstoß):** *Given* die Seite legt `_anstoss.json` ab, *when* der Lauf es sieht, *then* startet er einen Lauf und ruft kein `gh workflow run` auf; die Anstoß-Datei wird danach gelöscht, ohne dass der Lauf endlos wiederholt wird.
- [x] **AC-2.18 (Kein Git-Teil):** *Given* eine Instanz im neuen Zustand ohne Reisen-Repo und ohne `gh`, *when* der Lauf läuft, *then* endet er grün und ruft weder `gh` noch `git` auf dem Reisen-Repo auf (Fetch, Vorspulen, `software_anstossen`, `reisen_des_laufs`, Tests des Reisen-Repos).
- [x] **AC-2.19 (Einrichtung):** *Given* eine neue Instanz, *when* `einrichten.sh` läuft, *then* verlangt es weder `gh auth` noch ein Reisen-Repo, legt den Klon und `<FR_DIENST>/instanz/` an und erzeugt Units mit den neuen Pfaden.
- [x] **AC-2.20 (Alarm nur bei Ausfall):** *Given* ein Umzugsfehler, eine nicht umschaltbare Reise oder ein nicht abrufbarer Nachweis, *when* sie auftreten, *then* gibt es keine neue Meldung der Stufe `high`; die Liste `ALARMSTELLEN` in `test_betrieb.py` ändert sich nicht, und jede Meldung kommt höchstens einmal je Störung.
- [x] **AC-2.21 (Auslieferungstor Infrastruktur):** *Given* Lieferung 2 soll auf eine Instanz, *when* der Monitor nur den alten Pfad (`.git/modules/frieda/HEAD`) kennt oder der Backup-Aufruf nur den alten Pfad von `sichern.sh`, *then* wird Lieferung 2 nicht ausgeliefert; das Issue im Infrastruktur-Repo ist abgeschlossen und verlinkt, bevor sie freigegeben wird.
- [x] **AC-2.22 (Instanz-Tests):** *Given* `<FR_DIENST>/instanz/tests/` fehlt, *when* der Lauf läuft, *then* wird ohne Fehler übersprungen; liegt es vor und ist rot, gibt es eine Warnung und keinen Abbruch des Wechsels.
- [x] **AC-2.23 (Software ohne Instanzspezifisches):** *Given* die Software nach Lieferung 2, *when* nach Pfaden, Adressen, Benutzern gesucht wird, *then* kommt nichts Instanzspezifisches vor (Tests mit `einstellungen.beispiel` und den Beispielreisen; vorhandene Prüfungen `test_protokolle_ohne_pfade` und der Test auf Privates bleiben grün).
- [x] **AC-2.24 (Doku):** *Given* `docs/betrieb.md`, *when* sie gelesen wird, *then* beschreiben die Abschnitte Bauordner, Veröffentlichen, Anstoß, Überwachung, Einrichten und Umzug den neuen Weg samt Rückweg; ADR-0009 nennt #454 in Stufe 5.

## Dialog

### Runde 1
**Adversary:**
Testlauf aktuell: 233 passed, 0 failed (docs/artifacts/software-weg-454/adversary-test-output.txt). Diff von veroeffentlichen.sh und betrieb.md gelesen. Angriffe: (1) Funktionsprobe umzug_fertig_im_klon mit Zuständen leer/alt/fertig/halb: nur leer und halb werden fertig, alt und fertig bleiben, Rückgabe stets 0 (mit set -e sicher). (2) installieren im Umzug: nur noch Kommentare (veroeffentlichen.sh:22-25, 1029); einziger Aufruf ist das bestehende Einheiten-Abgleichen (:1298) mit Erlaubnisliste. (3) high: keine neue Stelle. (4) Entprellung: Fingerabdruck aus Commit, Ausgang und Ausgabe (:1034-1042), Test F004 grün. (5) Frische Instanz: Lauf aus dem Klon schreibt einmalig fertig und die Zeile "Move (#454) done", obwohl nie ein Umzug stattfand (F002). (6) Vorzeitiges fertig: Läuft ein Lauf aus dem Klon, bevor die Units umgestellt sind (z. B. manueller Aufruf), setzt umzug_fertig_im_klon fertig ohne Prüfung der Units; das alte Skript macht danach im Klon weiter (:1105), Units, Wächter, Schreibweg bleiben auf dem alten Bauordner, keine Warnzeile mehr (F001). (7) Der Lauf des alten Skripts nach der Umstellung ruft units_abgleichen (:1263) vor umzug_454 mit alten Vorlagen gegen auf den Klon zeigende Units: erwartbar eine normale Meldung (F003, aus dem Code abgeleitet).
**Implementierer:** (keine Rückmeldung in diesem Durchgang, die Befunde gehen an den Aufrufer.)

### Runde 2
**Adversary:**
Runde 2: Alle ACs einzeln gegen den aktuellen Code geprüft, Belege unveränderter ACs aus dem Vorgängerprotokoll durch den heutigen Testlauf bestätigt (233 passed). Gegenprobe zu F001: AC-2.12 verlangt fertig nur bei umgestellten Units; der Lauf aus dem Klon beweist das nur indirekt über den Skriptort. Gegenprobe AC-2.15: Zustand alt im Klon-Lauf bleibt alt (nur Funktionsprobe, kein Test, F004). Der Merker .units wird bei bereits gesetztem fertig nicht gelöscht (harmlos). Keine Befunde der Stufe HIGH oder CRITICAL.
**Implementierer:** (keine Rückmeldung in diesem Durchgang.)


## Findings

Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:1051
  Description: umzug_fertig_im_klon setzt den Zustand fertig, sobald ein Lauf aus dem Klon startet, ohne die Units zu prüfen.
  Spec requirement: AC-2.12 — fertig erst, wenn die Units auf den Klon umgestellt sind (Entscheidung 10, Schritt 4/5); AC-2.13 — Units zuletzt
  Conflict: Ein manueller Lauf aus dem Klon vor der Umstellung markiert fertig; danach setzt das alte Skript im Klon fort (:1105), die Units bleiben auf dem alten Bauordner, es gibt keine Warnzeile mehr. Betrifft nur manuelle Aufrufe, der Timer läuft vor der Umstellung aus dem alten Bauordner.
  Remediation: Vor dem Setzen units.py pruefen mit FR_WURZEL des Klons aufrufen und nur bei Ausgang 0 fertig setzen; oder in der Auslieferungsanleitung vermerken, vor der Umstellung keinen Lauf aus dem Klon zu starten.

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: betrieb/veroeffentlichen.sh:1051
  Description: Eine frische Instanz (nie Submodul, nie Umzug) schreibt beim ersten Lauf umzug-454 = fertig und gibt "Move (#454) done" aus.
  Spec requirement: AC-2.14 — nichts Unnötiges
  Conflict: Irreführende Protokollzeile, unnötige Zustandsdatei; fachlich harmlos, da umzug_454 nur in der alten Anordnung läuft.
  Remediation: Nur schreiben, wenn umzug-454.geprueft oder umzug-454.units existiert.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:1263
  Description: Im Lauf des alten Skripts nach der Umstellung der Units (Zustand noch nicht fertig) vergleicht units_abgleichen die auf den Klon zeigenden Units mit den alten Vorlagen, bevor umzug_454 (:1277) fertig setzt.
  Spec requirement: AC-2.20 — keine unnötigen Meldungen
  Conflict: Vermutlich genau eine Meldung der Stufe normal "Units differ from the templates" im Übergangslauf (aus dem Code abgeleitet; der Test nutzt eine Attrappe für units.py). Keine high-Meldung.
  Remediation: umzug_454 vor units_abgleichen aufrufen oder Abgleich überspringen, wenn die Units auf den Klon zeigen; Test mit echtem units.py ergänzen.

Finding:
  ID: F004
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/test_software_weg_454.py:805
  Description: Keine Tests für umzug_fertig_im_klon mit Zustand alt im Klon-Lauf und für die frische Instanz.
  Spec requirement: AC-2.15 — ein Lauf mit Zustand alt startet keinen neuen Umzug
  Conflict: Verhalten nur durch Funktionsprobe belegt, nicht durch die Suite.
  Remediation: Zwei Tests ergänzen.

Weitere geprüfte Dateien ohne eigenen AC (nur Hash-Abdeckung, Funktion unverändert): werkzeuge/adressen_holen.py:46, werkzeuge/wissen_punkte_holen.py:42, werkzeuge/wasser_pruefen.py:47, engine/schreiben.py:95.

## Confirmations

Confirmation:
  AC: AC-1.1
  Code reference: engine/instanz.py:149
  Evidence: speicherreisen() liest die Reisen mit Eintrag im Speicher; Tests der Gruppe L1 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.2
  Code reference: engine/instanz.py:149
  Evidence: FR_SPEICHERREISEN wird nicht mehr ausgewertet, Wert wirkungslos.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.3
  Code reference: engine/reisespeicher.py:147
  Evidence: Speicher nicht lesbar führt zu Fehler (fail closed), nie leere Liste.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.4
  Code reference: engine/schreiben.py:95
  Evidence: reise_anlegen schreibt Anfangsvorgang in den Speicher, kein Ordner im Bauordner (Test grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-1.5
  Code reference: betrieb/veroeffentlichen.sh:855
  Evidence: Speicher-Teil (speicher_reisen_lauf) baut neue Reisen ohne den Teil für das Reisen-Repo.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.6
  Code reference: engine/stand_git.py:16
  Evidence: Vergleich Reisen-Repo gegen Speicher, bei gleich Stempel; Umschalt-Test der Gruppe L1 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.7
  Code reference: engine/stand.py:41
  Evidence: Bei unterschiedlich oder Fehler bleibt die Reise im Reisen-Repo, Warnzeile, kein high.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.8
  Code reference: engine/stand.py:41
  Evidence: Idempotenz: test_umschaltung_ist_idempotent grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.9
  Code reference: engine/stand.py:41
  Evidence: Fortsetzung nach Abbruch: test_umschaltung_nach_abbruch_wird_fortgesetzt grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.10
  Code reference: engine/instanz.py:149
  Evidence: Bestehende Speicherreisen bleiben, Stand aus dem Speicher.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.11
  Code reference: engine/rueckmeldungen.py:122
  Evidence: Schreibwerkzeuge unverändert in Namen und Texten (Texttests grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.1
  Code reference: betrieb/veroeffentlichen.sh:855
  Evidence: main_klon holt im Klon origin/main ohne Reisen-Repo, gh, Anmeldung.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.2
  Code reference: betrieb/veroeffentlichen.sh:855
  Evidence: Rot: HEAD und Arbeitsbaum bleiben; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.3
  Code reference: betrieb/veroeffentlichen.sh:855
  Evidence: Nachweis grün führt zum Vorspulen ohne Tests auf dem Server.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.4
  Code reference: betrieb/veroeffentlichen.sh:855
  Evidence: Nachweis einmal je Stand abgefragt.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.5
  Code reference: betrieb/veroeffentlichen.sh:855
  Evidence: Rückfall auf software-gut.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.6
  Code reference: betrieb/veroeffentlichen.sh:855
  Evidence: Rot-Datei, ein high je Rot-Phase nach Schwelle.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.7
  Code reference: betrieb/veroeffentlichen.sh:855
  Evidence: Kennung und software-gut gleich bei grünem Lauf.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.8
  Code reference: betrieb/pruefsitzung.py:31
  Evidence: Nachziehen der Reisen bei grünem Probebau.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.9
  Code reference: engine/instanz.py:33
  Evidence: Einstellungen: Umgebung, instanz/einstellungen.env, alter Ort (test_einstellungen_reihenfolge grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.10
  Code reference: werkzeuge/wasser_pruefen.py:47
  Evidence: Meldeweg über <FR_DIENST>/instanz/melden.sh; ohne Weg nichts gesendet.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.11
  Code reference: betrieb/veroeffentlichen.sh:744
  Evidence: Python-Umgebung unter FR_DIENST/python bleibt, Neubau bei geänderter requirements.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.12
  Code reference: betrieb/veroeffentlichen.sh:1027
  Evidence: umzug_units ruft nur pruefen auf, nie installieren; bei Abweichung genau eine Warnzeile je Commit und Befund; fertig aus umzug_units (:1045) oder umzug_fertig_im_klon (:1051); Tests test_umzug_ohne_handschritt, test_umzug_mit_umgestellten_units_im_alten_lauf_wird_fertig, test_lauf_aus_dem_klon_setzt_umzug_fertig grün. Einschränkung F001.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.13
  Code reference: betrieb/veroeffentlichen.sh:1028
  Evidence: Schritt 1-3 scheitert oder pruefen meldet Abweichung: return 0 ohne Umstellung, Units unverändert, nächster Lauf erneut; test_umzug_scheitert_vor_units_alles_beim_alten und test_umzug_units_abweichend_nur_warnung_keine_umstellung grün. Suche nach installieren im Umzugscode: nur Kommentare, kein Aufruf.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.14
  Code reference: betrieb/veroeffentlichen.sh:1051
  Evidence: fertig oder alt: no-op; Funktionsprobe mit Zuständen leer, alt, fertig, halb: nur leer und halb werden fertig, alt und fertig bleiben; test_umzug_ist_wiederholbar grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.15
  Code reference: docs/betrieb.md:524
  Evidence: Rückweg mit einrichten.sh --installieren und Zustand alt beschrieben; alter Bauordner wird nie geschrieben (test_alter_bauordner_bleibt_und_ist_rueckweg), Zustand alt startet keinen Umzug (test_zustand_alt_startet_keinen_umzug) und bleibt alt im Klon-Lauf (Funktionsprobe).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.16
  Code reference: betrieb/veroeffentlichen.sh:1061
  Evidence: exec des neuen Skripts, genau ein Ergebnis (test_skript_startet_sich_nach_umschalten_neu grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.17
  Code reference: betrieb/veroeffentlichen.sh:667
  Evidence: anstoss_lauf ohne gh, Datei wird gelöscht.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.18
  Code reference: betrieb/veroeffentlichen.sh:663
  Evidence: Neue Anordnung ruft weder gh noch das Reisen-Repo auf.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.19
  Code reference: werkzeuge/grundkarte_auto.py:27
  Evidence: einrichten.sh braucht kein gh auth, legt Klon und instanz/ an (Tests grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.20
  Code reference: betrieb/veroeffentlichen.sh:1051
  Evidence: Keine neue high-Stelle: ALARMSTELLEN-Test (test_betrieb.py:1988) grün; Umzugsfehler nur Warnzeile; neue Funktion meldet nichts.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.21
  Code reference: docs/betrieb.md:521
  Evidence: Vorbedingung Infrastruktur als Auslieferungstor beschrieben (Doku).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.22
  Code reference: betrieb/pruefsitzung.py:31
  Evidence: tests/ fehlt: übersprungen; rot: Warnung.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.23
  Code reference: werkzeuge/punkte_holen.py:53
  Evidence: Nichts Instanzspezifisches; test_protokolle_ohne_pfade grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.24
  Code reference: docs/betrieb.md:508
  Evidence: Abschnitt Umzug samt Rückweg; Schritt 4/5 und Rückweg an die Entscheidung angepasst.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hat den Angriffen standgehalten; die vier Befunde der Stufe MEDIUM und LOW (F001 bis F004) sind keine Spec-Verstöße im Normalablauf.
Tests: 233 passed, 0 failed, 0 übersprungen
Edge cases: geprüft; F001 (vorzeitiges fertig bei manuellem Lauf aus dem Klon) empfohlen zu schließen
Regressions: None found
Checklist: alle ACs belegt

## Geprüfte Dateien

- sha256:b85689deb5f759f3aa11762178ea19b602ec1b29118a2f0602a1775156fdc027  betrieb/pruefsitzung.py
- sha256:4665839384a98a2e2227a3f63d911a9963739950075fc75905e53df9b418451f  betrieb/veroeffentlichen.sh
- sha256:b0db9d772a14eafc7025be093acbb6866371dd2e040e3e798d9400cda096bcc1  docs/betrieb.md
- sha256:3de1aa8ed6b87d955ca3c1b828ed09d848d889134f1b98a4c7194f16e1381758  engine/instanz.py
- sha256:3343b6ef764520e4c968366aae121e421bda5f27684faa2946030b3498c0916d  engine/reisespeicher.py
- sha256:7f7b161ab388a81e209e434ff48c9f868d265c115c42e47d44c074423c7890a1  engine/rueckmeldungen.py
- sha256:a2e7bf10b3089d5aaf27f2569a9c0805d4a0429419e7aa6d813b0534ef1271df  engine/schreiben.py
- sha256:c14ab51e5925f65e4d6652e8dae64592d1c505697277dadb3213897ecf72ee0a  engine/stand.py
- sha256:d7e92ac1b2890fdf0966bab647d4f375d753655034d6ee4791a0b41ad3cd193d  engine/stand_git.py
- sha256:0207ef31e1b851399693ccf6962d8965a9ef60dae4c07b3ba55765d1e6b60e83  engine/tests/test_software_weg_454.py
- sha256:cdb57bf08d485eaa945fa1b6254e765b41286eda2d4461d81b76852de0092cf5  werkzeuge/grundkarte_auto.py
- sha256:9b700b53081e0452db01a64ae0a422cc7a42bd55dc860c7a38eed0413697289e  werkzeuge/punkte_holen.py
- sha256:d3593ac158de2987d5d4d0b63513be5693a1c9903b397027306ea5d599cdc1c2  werkzeuge/wasser_pruefen.py

## Prüfbasis

- base: a547f1de6ddb0b0769e05ef34b7146c2d150641d
- blob:678b6d4e6b5c246ece0f243bc25e3de84ff66c26  betrieb/pruefsitzung.py
- blob:0e974d19b5e24aba305236a42dbe3f8ca4d7a0e2  betrieb/veroeffentlichen.sh
- blob:327f4c3b8cb68c0c150af4ea2715cce26b19edd4  docs/betrieb.md
- blob:d47e057ebeb89f9e0e17cedba2cd34b40bdcf8fe  engine/instanz.py
- blob:151ca69f03094ddd161079b77339587e342343ba  engine/reisespeicher.py
- blob:05e909338c2a8d07660ae747a4707e501a188757  engine/rueckmeldungen.py
- blob:144faeb33a50f95665a404ff9f39ab65442343ac  engine/schreiben.py
- blob:e88146a0a60aa07c6ec6cc71bdd58a208eadd0be  engine/stand.py
- blob:6fc580fee227048d5532d110b64815099cbb9442  engine/stand_git.py
- blob:d64bf8981a023e1d2b9242399fb2c1e432cf0a3c  engine/tests/test_software_weg_454.py
- blob:60a02e310da610273db0a4a268d6617248e8868c  werkzeuge/grundkarte_auto.py
- blob:89803fc80b4d20cbfeacd34ea20a6656a2ef9dd5  werkzeuge/punkte_holen.py
- blob:86ae622a4ada48b5bd12c7e2edaa00a71577916b  werkzeuge/wasser_pruefen.py
