# Adversary Dialog — software-weg-454
Spec: docs/specs/betrieb/software-weg-454.md
Datum: 2026-11-13 08:08

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
Testlauf aktuell: 236 passed, 0 failed, 0 übersprungen (docs/artifacts/software-weg-454/adversary-test-output.txt). Nachbesserung umzug_fertig_im_klon (betrieb/veroeffentlichen.sh:1052-1064) gelesen. Angriffe: (1) Matrix-Funktionsprobe der Funktion mit Spur (keine / umzug-454 / .geprueft / .units) x Zustand (leer / halb / alt / fertig) x Ausgang von units.py pruefen (0 / 3 / 4 / 127), unter bash -e: fertig wird nur bei Ausgang 0 und vorhandener Spur geschrieben (auch bei halb); bei Ausgang 3, 4, 127 bleibt alles unverändert und stumm (keine Ausgabe, Rückgabe 0, kein Abbruch durch set -e); alt und fertig bleiben in allen Fällen; ohne jede Spur entsteht nie eine Datei (frische Instanz, F002 behoben). (2) Abweichung in jedem Takt im Klon-Lauf: Die Funktion schreibt nichts und meldet nichts; die einzige Ausgabe kommt vom bestehenden units_abgleichen (:945), das eine normale Meldung je Fingerabdruck entprellt und keine high-Stufe nutzt. Der Preis ist ein zusätzlicher units.py-Aufruf je Takt (harmlos). (3) Wechselwirkung mit units_abgleichen im selben Klon-Lauf: Die Funktion läuft vor ihm (:856 gegen :945) und ändert nichts an den Units; bei Ausgang 3 würde units_abgleichen (bestehender Mechanismus, Erlaubnisliste) installieren, die Funktion hat das nie getan. (4) Zustand halb: wird bei pruefen 0 zu fertig, sonst bleibt er. (5) Kein installieren: im Umzugscode weiterhin nur Kommentare. (6) F003 (units_abgleichen vor umzug_454 im alten Skript, :1268) unverändert offen, bewusst. (7) units.py fehlt oder ist nicht ausführbar: pruefen scheitert (Ausgang 127), der Umzug bleibt stumm unfertig (F005, LOW).
**Implementierer:** F001, F002, F004 behoben; F003 bewusst offen (Auslieferungsnotiz).

### Runde 2
**Adversary:**
Runde 2: Alle ACs einzeln gegen den aktuellen Stand geprüft, Zeilennummern neu gezogen (Funktionen um eine Zeile verschoben), Belege unveränderter ACs durch den heutigen Lauf (236 passed) bestätigt. Gegenproben: neue Tests test_klon_lauf_laesst_zustand_alt (:817), test_frische_instanz_im_klon_schreibt_keinen_umzug (:827), test_klon_lauf_vor_der_umstellung_wird_nicht_fertig (:835) prüfen genau die Matrix-Zeilen meiner Probe. F001 (vorzeitiges fertig bei manuellem Lauf) ist damit geschlossen, weil pruefen mit FR_WURZEL des Klons vor dem Setzen entscheidet; F002 und F004 geschlossen. Keine neuen Befunde der Stufe MEDIUM oder höher.
**Implementierer:** (keine weitere Rückmeldung.)


### Runde 3

Runde 3 (Validierung, 13.11.2026): Prüfling ist die Änderung an docs/betrieb.md, „Neue Instanz einrichten“ beschreibt den Software-Klon (AC-2.19, AC-2.24), die alte Anordnung bleibt wörtlich als Unterabschnitt. Ein unabhängiger Prüfer hat zwölf Aussagen gegen den Code gehalten: elf bestätigt (einrichten.sh:150-163 befehle() mit Klon und <FR_DIENST>/instanz, gemeinsam.sh:120 FR_PYTHON, veroeffentlichen.sh:599-605 und :713-768 Neubau der Umgebung, deploy.sh --dienste, schreiben.py:17 neue Reise im Speicher, docs/konten.md:30 Anlegen nur mit Freischaltung). Befund F1 (MEDIUM, „Anstoß über gh im Code“) ist widerlegt: main() springt im Klon in main_klon (veroeffentlichen.sh:1110 `if software_klon; then main_klon "$@"; return; fi`), main_klon ruft nur anstoss_lauf (:848, :668, kein gh); anstoss_weitergeben (:1116) und software_anstossen (:1151) laufen nur in der alten Anordnung, die der Text als solche benennt. F2 (LOW, curl fehlt in den Voraussetzungen) behoben. F3 (LOW, Abschnitt Software-Wechsel nennt das Submodul) betrifft die alte Anordnung und ist dort richtig. Doku-Tests grün (test_software_nachziehen doku, test_software_weg_454 doku/betrieb_md/einrichten/rueckweg/infra: 7 passed). Keine offenen Befunde MEDIUM oder höher.

## Findings

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:1268
  Description: Im Lauf des alten Skripts nach der Umstellung der Units (Zustand noch nicht fertig) vergleicht units_abgleichen die auf den Klon zeigenden Units mit den alten Vorlagen, bevor umzug_454 fertig setzt. Bewusst offen, Vermerk in der Auslieferungsnotiz.
  Spec requirement: AC-2.20 — keine unnötigen Meldungen
  Conflict: Vermutlich genau eine Meldung der Stufe normal "Units differ from the templates" im Überlappungslauf (aus dem Code abgeleitet; keine high-Meldung).
  Remediation: umzug_454 vor units_abgleichen aufrufen oder den Abgleich überspringen, wenn die Units auf den Klon zeigen.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:1057
  Description: Fehlt units.py oder ist es nicht ausführbar, scheitert pruefen (Ausgang 127) und umzug_fertig_im_klon bleibt stumm; der Umzug wird nie fertig, ohne Warnzeile aus dieser Funktion.
  Spec requirement: AC-2.12 — der nächste Lauf setzt fertig, wenn die Units umgestellt sind
  Conflict: Nur bei kaputter Installation; units_abgleichen meldet dann "unit comparison failed" (bestehender Mechanismus).
  Remediation: Keine Änderung nötig; optional Warnzeile bei Ausgang größer 4.

Behobene Befunde der Vorrunde (geprüft): F001 (MEDIUM, fertig ohne Units-Prüfung) behoben in betrieb/veroeffentlichen.sh:1057; F002 (LOW, Zustandsdatei bei frischer Instanz) behoben in :1056; F004 (LOW, Testlücke) behoben durch engine/tests/test_software_weg_454.py:817, :827, :835.

Weitere geprüfte Dateien ohne eigenen AC (nur Hash-Abdeckung, Funktion unverändert): werkzeuge/adressen_holen.py:46, werkzeuge/wissen_punkte_holen.py:42, werkzeuge/wasser_pruefen.py:47, engine/schreiben.py:95.

## Confirmations

Confirmation:
  AC: AC-2.23
  Code reference: werkzeuge/adressen_holen.py:46
  Evidence: Werkzeug in dieser Lieferung unverändert, nichts Instanzspezifisches, Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.23
  Code reference: werkzeuge/wissen_punkte_holen.py:42
  Evidence: Werkzeug in dieser Lieferung unverändert, nichts Instanzspezifisches, Tests grün.
  Status: CONFIRMED

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
  Code reference: betrieb/veroeffentlichen.sh:856
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
  Code reference: betrieb/veroeffentlichen.sh:856
  Evidence: main_klon holt im Klon origin/main ohne Reisen-Repo, gh, Anmeldung.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.2
  Code reference: betrieb/veroeffentlichen.sh:856
  Evidence: Rot: HEAD und Arbeitsbaum bleiben; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.3
  Code reference: betrieb/veroeffentlichen.sh:856
  Evidence: Nachweis grün führt zum Vorspulen ohne Tests auf dem Server.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.4
  Code reference: betrieb/veroeffentlichen.sh:856
  Evidence: Nachweis einmal je Stand abgefragt.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.5
  Code reference: betrieb/veroeffentlichen.sh:856
  Evidence: Rückfall auf software-gut.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.6
  Code reference: betrieb/veroeffentlichen.sh:856
  Evidence: Rot-Datei, ein high je Rot-Phase nach Schwelle.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.7
  Code reference: betrieb/veroeffentlichen.sh:856
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
  Code reference: betrieb/veroeffentlichen.sh:745
  Evidence: Python-Umgebung unter FR_DIENST/python bleibt, Neubau bei geänderter requirements.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.12
  Code reference: betrieb/veroeffentlichen.sh:1028
  Evidence: umzug_units ruft nur pruefen auf, nie installieren; bei Abweichung genau eine Warnzeile je Commit und Befund; fertig aus umzug_units (:1047) oder umzug_fertig_im_klon (:1051); Tests test_umzug_ohne_handschritt, test_umzug_mit_umgestellten_units_im_alten_lauf_wird_fertig, test_lauf_aus_dem_klon_setzt_umzug_fertig grün. Neu: fertig im Klon-Lauf nur bei pruefen = 0 (Test test_klon_lauf_vor_der_umstellung_wird_nicht_fertig).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.13
  Code reference: betrieb/veroeffentlichen.sh:1029
  Evidence: Schritt 1-3 scheitert oder pruefen meldet Abweichung: return 0 ohne Umstellung, Units unverändert, nächster Lauf erneut; test_umzug_scheitert_vor_units_alles_beim_alten und test_umzug_units_abweichend_nur_warnung_keine_umstellung grün. Suche nach installieren im Umzugscode: nur Kommentare, kein Aufruf.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.14
  Code reference: betrieb/veroeffentlichen.sh:1051
  Evidence: fertig oder alt: no-op; Matrix-Funktionsprobe (Spur none/Zustand/geprueft/units x Zustand leer/halb/alt/fertig x pruefen-Ausgang 0/3/4/127): fertig nur bei Ausgang 0 und vorhandener Spur, alt und fertig bleiben, nie Abbruch; Tests test_klon_lauf_laesst_zustand_alt, test_frische_instanz_im_klon_schreibt_keinen_umzug; test_umzug_ist_wiederholbar grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.15
  Code reference: docs/betrieb.md:527
  Evidence: Rückweg mit einrichten.sh --installieren und Zustand alt beschrieben; alter Bauordner wird nie geschrieben (test_alter_bauordner_bleibt_und_ist_rueckweg), Zustand alt startet keinen Umzug (test_zustand_alt_startet_keinen_umzug) und bleibt alt im Klon-Lauf (Funktionsprobe).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.16
  Code reference: betrieb/veroeffentlichen.sh:1066
  Evidence: exec des neuen Skripts, genau ein Ergebnis (test_skript_startet_sich_nach_umschalten_neu grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.17
  Code reference: betrieb/veroeffentlichen.sh:668
  Evidence: anstoss_lauf ohne gh, Datei wird gelöscht.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.18
  Code reference: betrieb/veroeffentlichen.sh:664
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
  Code reference: docs/betrieb.md:522
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
Die Nachbesserung hält: fertig im Klon-Lauf nur bei Units ohne Abweichung und vorhandener Umzugsspur, stumm sonst, alt und fertig bleiben. Offen nur F003 und F005 (beide LOW, keine Spec-Verstöße im Normalablauf).
Tests: 236 passed, 0 failed, 0 übersprungen
Edge cases: Matrix aus Spur, Zustand und pruefen-Ausgang geprüft, none broken
Regressions: None found
Checklist: alle ACs belegt

## Geprüfte Dateien

- sha256:b85689deb5f759f3aa11762178ea19b602ec1b29118a2f0602a1775156fdc027  betrieb/pruefsitzung.py
- sha256:29925fb7efa05777b76ef53d4779792d4f3ae2e9856aa1097bb4af4d1a68ad27  betrieb/veroeffentlichen.sh
- sha256:abf6651f95fba5773df5890904127070d4250769c7eca929d747cc7221b149e9  docs/betrieb.md
- sha256:3de1aa8ed6b87d955ca3c1b828ed09d848d889134f1b98a4c7194f16e1381758  engine/instanz.py
- sha256:3343b6ef764520e4c968366aae121e421bda5f27684faa2946030b3498c0916d  engine/reisespeicher.py
- sha256:7f7b161ab388a81e209e434ff48c9f868d265c115c42e47d44c074423c7890a1  engine/rueckmeldungen.py
- sha256:a2e7bf10b3089d5aaf27f2569a9c0805d4a0429419e7aa6d813b0534ef1271df  engine/schreiben.py
- sha256:c14ab51e5925f65e4d6652e8dae64592d1c505697277dadb3213897ecf72ee0a  engine/stand.py
- sha256:d7e92ac1b2890fdf0966bab647d4f375d753655034d6ee4791a0b41ad3cd193d  engine/stand_git.py
- sha256:575278e8f1c2d52ff9685b62e9c54924a054112fea0747f67011abed5fa9cb91  werkzeuge/adressen_holen.py
- sha256:cdb57bf08d485eaa945fa1b6254e765b41286eda2d4461d81b76852de0092cf5  werkzeuge/grundkarte_auto.py
- sha256:9b700b53081e0452db01a64ae0a422cc7a42bd55dc860c7a38eed0413697289e  werkzeuge/punkte_holen.py
- sha256:d3593ac158de2987d5d4d0b63513be5693a1c9903b397027306ea5d599cdc1c2  werkzeuge/wasser_pruefen.py
- sha256:855a7ff6543bc716a01eda692e8caf5127a57bfddd4a54c7246122fd21b84637  werkzeuge/wissen_punkte_holen.py

## Prüfbasis

- base: a547f1de6ddb0b0769e05ef34b7146c2d150641d
- blob:678b6d4e6b5c246ece0f243bc25e3de84ff66c26  betrieb/pruefsitzung.py
- blob:c78dc32652d54e83be32ac60daebcc90a868b590  betrieb/veroeffentlichen.sh
- blob:de17e4bc3e19a24e23980f4992cd5cbc0ee10f75  docs/betrieb.md
- blob:d47e057ebeb89f9e0e17cedba2cd34b40bdcf8fe  engine/instanz.py
- blob:151ca69f03094ddd161079b77339587e342343ba  engine/reisespeicher.py
- blob:05e909338c2a8d07660ae747a4707e501a188757  engine/rueckmeldungen.py
- blob:144faeb33a50f95665a404ff9f39ab65442343ac  engine/schreiben.py
- blob:e88146a0a60aa07c6ec6cc71bdd58a208eadd0be  engine/stand.py
- blob:6fc580fee227048d5532d110b64815099cbb9442  engine/stand_git.py
- blob:af5b756c705b69e2f472fd87f1af167f09dff31b  werkzeuge/adressen_holen.py
- blob:60a02e310da610273db0a4a268d6617248e8868c  werkzeuge/grundkarte_auto.py
- blob:89803fc80b4d20cbfeacd34ea20a6656a2ef9dd5  werkzeuge/punkte_holen.py
- blob:86ae622a4ada48b5bd12c7e2edaa00a71577916b  werkzeuge/wasser_pruefen.py
- blob:757498314856f7276125f9681ce622f8dedf9104  werkzeuge/wissen_punkte_holen.py

## Geprüfte Dateien

- sha256:b85689deb5f759f3aa11762178ea19b602ec1b29118a2f0602a1775156fdc027  betrieb/pruefsitzung.py
- sha256:29925fb7efa05777b76ef53d4779792d4f3ae2e9856aa1097bb4af4d1a68ad27  betrieb/veroeffentlichen.sh
- sha256:d4c55a0d611523f5deaeb3b8c563570a9868b433b324bb68d8b674fdf847cffb  docs/betrieb.md
- sha256:3de1aa8ed6b87d955ca3c1b828ed09d848d889134f1b98a4c7194f16e1381758  engine/instanz.py
- sha256:3343b6ef764520e4c968366aae121e421bda5f27684faa2946030b3498c0916d  engine/reisespeicher.py
- sha256:7f7b161ab388a81e209e434ff48c9f868d265c115c42e47d44c074423c7890a1  engine/rueckmeldungen.py
- sha256:a2e7bf10b3089d5aaf27f2569a9c0805d4a0429419e7aa6d813b0534ef1271df  engine/schreiben.py
- sha256:c14ab51e5925f65e4d6652e8dae64592d1c505697277dadb3213897ecf72ee0a  engine/stand.py
- sha256:d7e92ac1b2890fdf0966bab647d4f375d753655034d6ee4791a0b41ad3cd193d  engine/stand_git.py
- sha256:575278e8f1c2d52ff9685b62e9c54924a054112fea0747f67011abed5fa9cb91  werkzeuge/adressen_holen.py
- sha256:cdb57bf08d485eaa945fa1b6254e765b41286eda2d4461d81b76852de0092cf5  werkzeuge/grundkarte_auto.py
- sha256:9b700b53081e0452db01a64ae0a422cc7a42bd55dc860c7a38eed0413697289e  werkzeuge/punkte_holen.py
- sha256:d3593ac158de2987d5d4d0b63513be5693a1c9903b397027306ea5d599cdc1c2  werkzeuge/wasser_pruefen.py
- sha256:855a7ff6543bc716a01eda692e8caf5127a57bfddd4a54c7246122fd21b84637  werkzeuge/wissen_punkte_holen.py

## Prüfbasis

- base: 3b9f9085648b0936e5e73004da98fe49c30509da
- blob:678b6d4e6b5c246ece0f243bc25e3de84ff66c26  betrieb/pruefsitzung.py
- blob:c78dc32652d54e83be32ac60daebcc90a868b590  betrieb/veroeffentlichen.sh
- blob:4e4f7897c1746b2e1ab9a59e6967d60a4c8bd660  docs/betrieb.md
- blob:d47e057ebeb89f9e0e17cedba2cd34b40bdcf8fe  engine/instanz.py
- blob:151ca69f03094ddd161079b77339587e342343ba  engine/reisespeicher.py
- blob:05e909338c2a8d07660ae747a4707e501a188757  engine/rueckmeldungen.py
- blob:144faeb33a50f95665a404ff9f39ab65442343ac  engine/schreiben.py
- blob:e88146a0a60aa07c6ec6cc71bdd58a208eadd0be  engine/stand.py
- blob:6fc580fee227048d5532d110b64815099cbb9442  engine/stand_git.py
- blob:af5b756c705b69e2f472fd87f1af167f09dff31b  werkzeuge/adressen_holen.py
- blob:60a02e310da610273db0a4a268d6617248e8868c  werkzeuge/grundkarte_auto.py
- blob:89803fc80b4d20cbfeacd34ea20a6656a2ef9dd5  werkzeuge/punkte_holen.py
- blob:86ae622a4ada48b5bd12c7e2edaa00a71577916b  werkzeuge/wasser_pruefen.py
- blob:757498314856f7276125f9681ce622f8dedf9104  werkzeuge/wissen_punkte_holen.py
