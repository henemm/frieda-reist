# Adversary Dialog — software-weg-454
Spec: docs/specs/betrieb/software-weg-454.md
Datum: 2026-11-13 06:03

## Checkliste
- [ ] **AC-1.1:** *Given* der Speicher enthält Reisen und `FR_SPEICHERREISEN` ist leer oder nennt andere Namen, *when* `instanz.speicherreisen()` aufgerufen wird, *then* sind es genau die Reisen mit Eintrag im Speicher.
- [ ] **AC-1.2:** *Given* `FR_SPEICHERREISEN` ist in der Umgebung oder Einstellungsdatei gesetzt, *when* eine Reise nicht im Speicher steht, *then* gilt sie nicht als Speicherreise (Wert wirkungslos, keine Fehlermeldung).
- [ ] **AC-1.3:** *Given* der Speicher ist nicht lesbar, *when* `speicherreisen()` aufgerufen wird, *then* wird ein Fehler ausgelöst (fail closed, #361), nie eine leere Liste.
- [ ] **AC-1.4:** *Given* eine Speicher-Instanz, *when* `reise_anlegen` für die Vorlage der Beispielreise (Wanderung) und für das Stadtwochenende aufgerufen wird, *then* liegt jeweils ein Anfangsvorgang im Speicher und kein Ordner `reisen/<name>` im Bauordner.
- [ ] **AC-1.5:** *Given* eine neu angelegte Reise, *when* der Lauf des Veröffentlichens läuft, *then* baut der Speicher-Teil sie und die Seite wird veröffentlicht, ohne dass der Git-Teil sie anfasst.
- [ ] **AC-1.6:** *Given* eine Reise liegt in Git und ist inhaltsgleich im Speicher darstellbar (beide Beispielreisen), *when* der Lauf läuft, *then* wird sie umgeschaltet: Anfangsvorgang, Stempel `gleich`, Reise steht in `speicherreisen()`, Lauf bleibt grün.
- [ ] **AC-1.7:** *Given* der Vergleich einer Git-Reise ergibt „unterschiedlich“ oder Fehler, *when* der Lauf läuft, *then* bleibt die Reise in Git, nichts wird gelöscht oder geändert, es gibt eine Warnzeile mit Grund und keine Meldung der Stufe `high`.
- [ ] **AC-1.8:** *Given* eine Reise ist schon umgeschaltet, *when* der Lauf erneut läuft, *then* ändert sich nichts (kein zweiter Anfangsvorgang, gleicher Stand).
- [ ] **AC-1.9:** *Given* die Umschaltung läuft, *when* sie nach dem Anfangsvorgang und vor dem Stempel abbricht, *then* gilt die Reise bis dahin weiter als Git-Reise, und der nächste Lauf setzt die Umschaltung fort: erneuter Vergleich gegen den vorhandenen Anfangsvorgang, bei „gleich“ Stempel; kein zweiter Anfangsvorgang, kein Handschritt.
- [ ] **AC-1.10:** *Given* eine Instanz, die vor Lieferung 1 Reisen über `FR_SPEICHERREISEN` im Speicher hatte, *when* die neue Software läuft, *then* bleiben diese Reisen im Speicher und ihre Seiten unverändert (kein Handschritt, #250).
- [ ] **AC-1.11:** *Given* die Schreib-Werkzeuge des Konnektors, *when* sie auf eine Reise im Speicher angewendet werden, *then* verhalten sie sich wie zuvor (Namen, Parameter, Texte unverändert).
- [ ] **AC-2.1 (Abruf):** *Given* ein neuer Commit auf `main` der Software, *when* der Lauf läuft, *then* wird er ohne Reisen-Repo, ohne GitHub-Workflow der Instanz und ohne Anmeldung geholt und (nach Prüfung) eingespielt.
- [ ] **AC-2.2 (Prüfung vor Umschalten):** *Given* ein neuer Commit `C` ohne gültigen Nachweis, *when* die Tests auf dem Server rot sind, *then* zeigt `HEAD` des Klons weiter auf den bisherigen Commit, und der Arbeitsbaum des Klons ist unverändert.
- [ ] **AC-2.3 (Nachweis):** *Given* alle Pflichtprüfungen von `C` sind auf GitHub grün, *when* der Lauf läuft, *then* wird der Klon auf `C` vorgespult, ohne die Tests auf dem Server zu wiederholen.
- [ ] **AC-2.4 (Nachweis nur je Stand):** *Given* derselbe Commit `C` wird in mehreren Läufen gesehen, *when* der Nachweis fehlt, *then* wird er nur einmal je Stand abgefragt.
- [ ] **AC-2.5 (Rückfall):** *Given* `C` ist rot oder der Deploy mit `C` scheitert, *when* der Lauf endet, *then* arbeiten die Dienste weiter mit dem Commit aus `<FR_DIENST>/software-gut`, und die Seiten der Reisen bleiben auf ihrem letzten guten Stand.
- [ ] **AC-2.6 (Rot-Datei):** *Given* `C` ist rot, *when* der nächste Lauf denselben `C` sieht, *then* wird er nicht erneut geprüft („Bekannter roter Stand“), und erst nach Ablauf der Schwelle gibt es genau einen Alarm der Stufe `high` je Rot-Phase.
- [ ] **AC-2.7 (Kennung):** *Given* `veroeffentlicht` und `software_kennung`, *when* ein Lauf grün endet, *then* sind beide der Commit der Software, und `software-gut` trägt denselben Commit.
- [ ] **AC-2.8 (Nachziehen der Reisen):** *Given* ein neuer Software-Commit, *when* er veröffentlicht ist, *then* zieht der Speicher-Teil jede Reise (Wanderung und Stadtwochenende) auf die neue Kennung nach (`neu.py nachziehen-speicher`, nur bei grünem Probebau).
- [ ] **AC-2.9 (Einstellungen):** *Given* `<FR_DIENST>/instanz/einstellungen.env` liegt vor, *when* ein Skript startet, *then* kommen Einstellungen aus der Umgebung, sonst aus dieser Datei, sonst (Übergang) aus dem alten Ort.
- [ ] **AC-2.10 (Meldeweg):** *Given* `<FR_DIENST>/instanz/melden.sh`, *when* eine Meldung ausgelöst wird, *then* ruft `FR_MELDEN` diesen Weg auf; ohne Meldeweg wird nichts gesendet.
- [ ] **AC-2.11 (Python-Umgebung):** *Given* die Python-Umgebung liegt unter `<FR_DIENST>/python`, *when* der Klon umgeschaltet oder zurückgesetzt wird, *then* bleibt sie erhalten; ändert sich `requirements` im Commit, wird sie vor dem Umschalten der Dienste neu aufgebaut.
- [ ] **AC-2.12 (Umzug ohne Handschritt):** *Given* eine Instanz im alten Zustand (Submodul im Bauordner), *when* der Lauf mit der Software dieses Commits läuft, *then* legt er den Klon an, kopiert Einstellungen und Meldeweg, baut die Python-Umgebung, gleicht die Units ab und stellt den Zustand auf `fertig`, ohne dass jemand etwas tut.
- [ ] **AC-2.13 (Units zuletzt):** *Given* ein Schritt des Umzugs vor dem Abgleich der Units scheitert, *when* der Lauf endet, *then* zeigen alle Units unverändert auf den alten Bauordner, das Veröffentlichen läuft weiter über den alten Weg, und der nächste Lauf versucht den Umzug erneut.
- [ ] **AC-2.14 (Wiederholbar):** *Given* der Umzug ist `fertig` oder halb durchgeführt, *when* der Lauf erneut läuft, *then* ändert er nichts Unnötiges (keine doppelten Kopien, kein Überschreiben neuerer Einstellungen, keine Units-Änderung ohne Unterschied).
- [ ] **AC-2.15 (Alter Bauordner bleibt):** *Given* der Umzug ist `fertig`, *when* der alte Bauordner betrachtet wird, *then* ist er unverändert (nichts gelöscht, keine Datei verändert); stellt man die Units auf ihn zurück, laufen Veröffentlichen, Wächter, Schreibweg und Kartendienst wieder wie vorher (Rückweg).
- [ ] **AC-2.16 (Selbstaustausch):** *Given* das Vorspulen des Klons ändert `veroeffentlichen.sh`, *when* der Lauf weiterläuft, *then* startet er mit `exec` das neue Skript neu und endet genau einmal mit einem Ergebnis (kein Mischlauf aus altem und neuem Code).
- [ ] **AC-2.17 (Anstoß):** *Given* die Seite legt `_anstoss.json` ab, *when* der Lauf es sieht, *then* startet er einen Lauf und ruft kein `gh workflow run` auf; die Anstoß-Datei wird danach gelöscht, ohne dass der Lauf endlos wiederholt wird.
- [ ] **AC-2.18 (Kein Git-Teil):** *Given* eine Instanz im neuen Zustand ohne Reisen-Repo und ohne `gh`, *when* der Lauf läuft, *then* endet er grün und ruft weder `gh` noch `git` auf dem Reisen-Repo auf (Fetch, Vorspulen, `software_anstossen`, `reisen_des_laufs`, Tests des Reisen-Repos).
- [ ] **AC-2.19 (Einrichtung):** *Given* eine neue Instanz, *when* `einrichten.sh` läuft, *then* verlangt es weder `gh auth` noch ein Reisen-Repo, legt den Klon und `<FR_DIENST>/instanz/` an und erzeugt Units mit den neuen Pfaden.
- [ ] **AC-2.20 (Alarm nur bei Ausfall):** *Given* ein Umzugsfehler, eine nicht umschaltbare Reise oder ein nicht abrufbarer Nachweis, *when* sie auftreten, *then* gibt es keine neue Meldung der Stufe `high`; die Liste `ALARMSTELLEN` in `test_betrieb.py` ändert sich nicht, und jede Meldung kommt höchstens einmal je Störung.
- [ ] **AC-2.21 (Auslieferungstor Infrastruktur):** *Given* Lieferung 2 soll auf eine Instanz, *when* der Monitor nur den alten Pfad (`.git/modules/frieda/HEAD`) kennt oder der Backup-Aufruf nur den alten Pfad von `sichern.sh`, *then* wird Lieferung 2 nicht ausgeliefert; das Issue im Infrastruktur-Repo ist abgeschlossen und verlinkt, bevor sie freigegeben wird.
- [ ] **AC-2.22 (Instanz-Tests):** *Given* `<FR_DIENST>/instanz/tests/` fehlt, *when* der Lauf läuft, *then* wird ohne Fehler übersprungen; liegt es vor und ist rot, gibt es eine Warnung und keinen Abbruch des Wechsels.
- [ ] **AC-2.23 (Software ohne Instanzspezifisches):** *Given* die Software nach Lieferung 2, *when* nach Pfaden, Adressen, Benutzern gesucht wird, *then* kommt nichts Instanzspezifisches vor (Tests mit `einstellungen.beispiel` und den Beispielreisen; vorhandene Prüfungen `test_protokolle_ohne_pfade` und der Test auf Privates bleiben grün).
- [ ] **AC-2.24 (Doku):** *Given* `docs/betrieb.md`, *when* sie gelesen wird, *then* beschreiben die Abschnitte Bauordner, Veröffentlichen, Anstoß, Überwachung, Einrichten und Umzug den neuen Weg samt Rückweg; ADR-0009 nennt #454 in Stufe 5.

## Dialog

### Runde 1
**Adversary:** Diff aller 42 Dateien gelesen, betroffene Tests ausgeführt (367 passed, siehe adversary-test-output.txt). Angriffe und Ergebnis:

Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/gemeinsam.sh:149
  Description: speicherreisen_lesen setzt eine leere Liste mit Exit 0, wenn `-e $FR_SPEICHER/reisen.db` falsch ist. Ist das Speicherverzeichnis nicht durchsuchbar (Reproduktion: Speicher mit reisen.db anlegen, chmod 000 auf das Verzeichnis, `. betrieb/gemeinsam.sh; speicherreisen_lesen` gibt rc=0, Liste leer), sieht die Shell keine Datenbank. Python `instanz.speicherreisen()` wirft dagegen korrekt SpeicherNichtLesbar.
  Spec requirement: AC-1.3 (und #361 fail closed): nie eine leere Liste bei nicht lesbarem Speicher.
  Conflict: Die Shell-Entsprechung (von veroeffentlichen.sh und deploy.sh benutzt) behandelt einen unlesbaren Speicher als "keine Reisen"; git_reisen_umschalten (veroeffentlichen.sh:631) prüft ebenfalls nur `-e reisen.db`. Folge: Speicherreisen werden stillschweigend nicht gebaut, der Lauf kann grün enden.
  Remediation: Python-Aufruf immer machen und dort exists() entscheiden lassen, oder zusätzlich `[ -x "$FR_SPEICHER" ]` prüfen.

Finding:
  ID: F002
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:843
  Description: main_klon ruft rueckfall bei jedem Fehlschlag von speicher_reisen_lauf (Zeilen 842-845). Der Rückgabewert 1 steht auch für Störungen ohne Bezug zur Software: Speicher kurz nicht lesbar, Umschaltprüfung gescheitert, Deploy-Exit 1 einer Reise. Dann wird der Klon auf software-gut zurückgesetzt und alle Dienste werden mit altem Code neu gestartet (deploy.sh --dienste), obwohl C geprüft grün war. Im nächsten Takt (5 Minuten) wird C erneut vorgespult und ausgerollt. Es gibt keine Rot-Datei und keinen Alarm; bei dauerhaft scheiterndem Deploy mit C entstehen alle 5 Minuten zwei Neustarts der Dienste, lautlos. Hat nachziehen-speicher schon Reisen auf die Kennung von C umgestellt, läuft nach dem Rückfall alter Code gegen bereits umgestellte Speicherdaten (Rück-Nachziehen mit altem Code, ungetestet).
  Spec requirement: AC-2.5 (Rückfall bei rotem C oder gescheitertem Deploy mit C) und AC-2.6 (Rot-Datei je Stand).
  Conflict: Rückfall ist nicht auf Deploy-Fehler der Software eingegrenzt und es gibt keine Bremse gegen die Schleife.
  Remediation: Rückfall nur bei Deploy-Fehlern mit C, nicht bei Speicher-Lesefehlern; beim Rückfall Rot-Datei schreiben, damit die Schwelle einen Alarm einmal je Phase auslöst und der Stand nicht endlos neu versucht wird.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:812
  Description: python_umgebung "$neu" (pip install nach <FR_DIENST>/python, Prüfsumme gesetzt, FR_BIBLIOTHEKEN_NEU exportiert) läuft vor software_pruefen. Ist C rot, bleibt die Umgebung mit den Bibliotheken von C verändert; der Rückfall setzt nur den Klon zurück ("nie gelöscht", Zeile 693 ff.).
  Spec requirement: AC-2.2 und AC-2.11 (Prüfung vor dem Umschalten).
  Conflict: Rotes Ergebnis lässt die Live-Umgebung nicht auf dem Stand des letzten guten Commits; spätere Neustarts laufen mit neuen Bibliotheken zum alten Code. Kein Test dafür.
  Remediation: akzeptieren und dokumentieren, oder in Wegwerf-Umgebung prüfen.

Finding:
  ID: F004
  Severity: MEDIUM
  Category: anti_pattern
  Code reference: betrieb/veroeffentlichen.sh:894
  Description: umzug_454 läuft nach jedem grünen Lauf komplett durch, solange Schritt 4 (Units) an der gesperrten ExecStart-Änderung scheitert (erwarteter Dauerzustand bis zum Handschritt mit Root). Schritt 3 ruft dabei in jedem Takt software_pruefen "$sub" auf: curl auf die GitHub-API, und ohne Nachweis (FR_CI_NACHWEIS=0 oder API nicht erreichbar) die vollen Server-Tests in frischem Arbeitsbaum, Minuten bis etwa 20 min, bei jedem Takt.
  Spec requirement: AC-2.4 (Nachweis nur einmal je Stand) und AC-2.14 (nichts Unnötiges wiederholen).
  Conflict: kein Merker "Prüfung für $sub schon grün".
  Remediation: Ergebnis je $sub in <FR_DIENST> ablegen und überspringen.

Finding:
  ID: F005
  Severity: MEDIUM
  Category: spec_violation
  Code reference: engine/reisespeicher.py:712
  Description: umschaltung_frei wird jetzt für jede Reise mit Speichereintrag ausgewertet (früher nur Reisen aus FR_SPEICHERREISEN). Eine alte Speicherreise ohne .gebaut und ohne gültigen Stempel, die im Git-Bauordner liegt, gilt ab jetzt als Git-Reise; Schreibwerkzeuge laufen über den Git-Weg (engine/schreiben.py:5509) statt mit 503 abgelehnt zu werden (test_schreibweg_lehnt_gesperrte_reise_ab wurde so umgeschrieben). Schreibt der Git-Weg, ändert sich der Git-Baum, der Stempel wird veraltet, und die automatische Umschaltung vergleicht danach den alten Anfangsvorgang gegen den neuen Git-Stand: dauerhaft "unterschied", die Reise bleibt in Git. Kein Datenverlust, aber die Spec sagt nichts zu "Speichereintrag, offene Umschaltung, weitere Git-Schreibvorgänge".
  Spec requirement: AC-1.7, AC-1.9, AC-1.10.
  Conflict: Mehrdeutig, ob gewollt; Hinweis nur im Protokoll, keine Lösung ohne Handschritt.
  Remediation: Entscheidung des Auftraggebers: Anfangsvorgang bei veraltetem Stempel neu importieren oder eine normale Meldung je betroffener Reise.

Finding:
  ID: F006
  Severity: LOW
  Category: regression
  Code reference: betrieb/veroeffentlichen.sh:1156
  Description: Die Vorlagen nennen jetzt `ExecStart=__WURZEL__/betrieb/...`. In der alten Anordnung rendert einrichten.sh --erzeugen mit FR_WURZEL = altem Bauordner; installiert ist `<alt>/frieda/betrieb/...`. units.abgleich (selbst reproduziert) liefert setzen=[Environment FR_DIENST] und gesperrt=[ExecStart wanted/installed], also Exit 4: units_abgleichen schreibt in jedem Lauf der alten Anordnung nach dem Softwarewechsel eine Warnzeile und genau eine normale Meldung "Units differ from the templates", bis zum manuellen Unit-Wechsel.
  Spec requirement: AC-2.20 (keine neue Meldung high, hält ein), AC-2.13.
  Conflict: Rauschen und ein vermeidbares Issue im Übergang; keine Wirkung auf Dienste.
  Remediation: In alter Anordnung (fr_alte_anordnung) units_abgleichen überspringen oder mit frieda/betrieb rendern.

Finding:
  ID: F007
  Severity: LOW
  Category: anti_pattern
  Code reference: werkzeuge/wasser_pruefen.py:149
  Description: Die in Reisedaten geschriebene Quellenangabe wurde von frieda/werkzeuge/wasser_pruefen.py auf werkzeuge/wasser_pruefen.py geändert. Die Gebrauchstexte werkzeuge/punkte_holen.py:19, adressen_holen.py:15, wissen_punkte_holen.py:13 nennen weiter "in der Wurzel des Reisen-Repos: engine/.venv/bin/python", obwohl die Python-Umgebung im Klon unter <FR_DIENST>/python liegt.
  Spec requirement: AC-2.23, AC-2.24.
  Conflict: teilweise veraltete Aufrufhilfen, nur Lesbarkeit.
  Remediation: Aufrufzeilen vereinheitlichen.

Bestätigt ohne Fund: Fail-closed der Einstellungsdatei (engine/instanz.py:138, Test um FR_SPEICHER-in-Umgebung ergänzt, Absicherung nicht verloren); umschalten_automatisch (engine/reisespeicher.py:786) schreibt nur Vorgang und Stempel, nie löschen, Exportordner ist ein TemporaryDirectory; Abbruch zwischen Anfangsvorgang und Stempel über den bekannt-Zweig; engine/rueckmeldungen.py:972 nur Kommentar; engine/stand.py:155 und engine/stand_git.py:64 (git archive aus HEAD, tar-Filter gegen Pfade nach außen); engine/schreiben.py: SpeicherNichtLesbar wird an allen vier Stellen mit 503 beantwortet, kein Ausweichen auf Git; neue Texte in texte_de.py:937 und texte_en.py:936; deploy.sh-Modulliste enthält stand_git.py; keine neue high-Alarmstelle.
**Implementierer:** (nicht beteiligt; Kontext-Isolation)

### Runde 2
**Adversary:** Nachfassen zu den Bohrpunkten:
- Roter Commit lässt Klon unverändert: software_pruefen läuft in einem eigenen Arbeitsbaum (worktree add --detach) und räumt ihn ab; HEAD und Arbeitsbaum des Klons bleiben (test_roter_commit_laesst_klon_unveraendert grün). Bei rc 2 kein Rot-Eintrag, Wiederholung je Takt.
- Rot-Datei einmal je Rot-Phase: Known-red-Zweig ruft nur alarm_pruefen, Entprellung über rot_gemeldet; Neuprüfung nur bei Umgebungswechsel oder nach 60 Minuten.
- Keine neuen high-Alarmstellen: Umzugswarnungen sind echo, Instanz-Tests melden normal; ALARMSTELLEN unverändert.
- Nichts Instanzspezifisches: nur Platzhalter.
- Umzug Schritt 4 (bekannter Punkt): units pruefen mit FR_WURZEL=<Klon> liefert bei Pfadabweichung rc 4, installieren läuft nur bei rc 3; damit keine Teil-Installation, Zustandsdatei umzug-454 bleibt ungesetzt, Wiederholung idempotent (Kosten siehe F004). Nach manuellem Unit-Wechsel ist pruefen rc 0, Schritt 5 schreibt fertig und umzug_neustart setzt im Klon fort.
- Race Schreibweg gegen Umschaltung: Lauf hält flock; schreibt der Git-Weg dazwischen, wird der Stempel ungültig und die Reise bleibt in Git (F005).
- Abgeschwächte Tests: Fail-closed bleibt (test_instanz erweitert), neue Fixture git_weg belegt, dass offene Reisen nie in den Speicher schreiben. Verloren: der 503 umschaltung_nicht_freigegeben für offene Reisen (F005).
**Implementierer:** (nicht beteiligt)

## Bestätigungen

Confirmation:
  AC: AC-1.1
  Code reference: engine/instanz.py:149
  Evidence: speicherreisen() fragt reisespeicher.speicherreisen (engine/reisespeicher.py:759), FR_SPEICHERREISEN wird nicht gelesen; Test grün
  Status: CONFIRMED

Confirmation:
  AC: AC-1.2
  Code reference: engine/instanz.py:149
  Evidence: Umgebung und Datei werden für die Liste ignoriert, keine Fehlermeldung
  Status: CONFIRMED

Confirmation:
  AC: AC-1.3
  Code reference: engine/instanz.py:149
  Evidence: SpeicherNichtLesbar/EinstellungenNichtLesbar statt leerer Liste (selbst mit chmod 000 geprüft); Shell-Lücke siehe F001
  Status: CONFIRMED

Confirmation:
  AC: AC-1.4
  Code reference: engine/schreiben.py:5509
  Evidence: reise_anlegen geht immer in vorgang_speicher, Namenskollisionen mit Git-Reisen werden erkannt
  Status: CONFIRMED

Confirmation:
  AC: AC-1.5
  Code reference: betrieb/veroeffentlichen.sh:271
  Evidence: speicher_reisen_lauf baut jede Reise aus der Speicherliste, neue Reise hat keinen Git-Baum und ist frei
  Status: CONFIRMED

Confirmation:
  AC: AC-1.6
  Code reference: engine/reisespeicher.py:786
  Evidence: Anfangsvorgang aus HEAD, Vergleich, Stempel gleich; beide Beispielreisen im Test
  Status: CONFIRMED

Confirmation:
  AC: AC-1.7
  Code reference: engine/reisespeicher.py:786
  Evidence: unterschied/fehler: nur Stempel, Reise bleibt in Git; veroeffentlichen.sh:631 gibt Warnzeile ohne Meldung
  Status: CONFIRMED

Confirmation:
  AC: AC-1.8
  Code reference: engine/reisespeicher.py:786
  Evidence: schon_im_speicher ohne neuen Vorgang, Stempel byte-gleich (Test)
  Status: CONFIRMED

Confirmation:
  AC: AC-1.9
  Code reference: engine/reisespeicher.py:786
  Evidence: bekannt-Zweig vergleicht erneut gegen vorhandenen Anfangsvorgang (Test); Einschränkung F005
  Status: CONFIRMED

Confirmation:
  AC: AC-1.10
  Code reference: engine/reisespeicher.py:712
  Evidence: Reisen mit .gebaut bleiben frei; Altreisen ohne .gebaut und Stempel: F005 (AMBIGUOUS)
  Status: CONFIRMED

Confirmation:
  AC: AC-1.11
  Code reference: engine/schreiben.py:5509
  Evidence: Werkzeugnamen, Parameter und Texte unangetastet, Test grün
  Status: CONFIRMED

Confirmation:
  AC: AC-2.1
  Code reference: betrieb/veroeffentlichen.sh:773
  Evidence: fetch im Klon ohne gh und Workflow, Test grün
  Status: CONFIRMED

Confirmation:
  AC: AC-2.2
  Code reference: betrieb/veroeffentlichen.sh:719
  Evidence: Prüfung im eigenen Arbeitsbaum, Klon unberührt; Einschränkung F003
  Status: CONFIRMED

Confirmation:
  AC: AC-2.3
  Code reference: betrieb/veroeffentlichen.sh:665
  Evidence: Nachweis per curl der drei Pflichtprüfungen, dann keine Server-Tests
  Status: CONFIRMED

Confirmation:
  AC: AC-2.4
  Code reference: betrieb/veroeffentlichen.sh:773
  Evidence: je Stand über Rot-Datei und neu!=kopf; Ausnahme im Umzug F004
  Status: CONFIRMED

Confirmation:
  AC: AC-2.5
  Code reference: betrieb/veroeffentlichen.sh:759
  Evidence: rueckfall auf software-gut mit deploy --dienste; Grenzen F002
  Status: CONFIRMED

Confirmation:
  AC: AC-2.6
  Code reference: betrieb/veroeffentlichen.sh:812
  Evidence: Rot-Datei am Software-Commit, Alarm nach Schwelle einmal je Phase (Test)
  Status: CONFIRMED

Confirmation:
  AC: AC-2.7
  Code reference: betrieb/veroeffentlichen.sh:773
  Evidence: veroeffentlicht, Kennung und software-gut tragen kopf (Test)
  Status: CONFIRMED

Confirmation:
  AC: AC-2.8
  Code reference: betrieb/veroeffentlichen.sh:271
  Evidence: nachziehen-speicher je Reise nach geprüftem Commit, beide Beispielreisen im Test
  Status: CONFIRMED

Confirmation:
  AC: AC-2.9
  Code reference: engine/instanz.py:48
  Evidence: Reihenfolge Umgebung, Instanzdatei, alter Ort in Python und Shell
  Status: CONFIRMED

Confirmation:
  AC: AC-2.10
  Code reference: betrieb/gemeinsam.sh:128
  Evidence: FR_MELDEN findet instanz/melden.sh, leer sendet nichts
  Status: CONFIRMED

Confirmation:
  AC: AC-2.11
  Code reference: betrieb/veroeffentlichen.sh:693
  Evidence: Umgebung unter FR_DIENST/python, Neubau bei geänderter requirements; Einschränkung F003
  Status: CONFIRMED

Confirmation:
  AC: AC-2.12
  Code reference: betrieb/veroeffentlichen.sh:869
  Evidence: Schritte 1 bis 5, Test mit Units-Attrappe grün
  Status: CONFIRMED

Confirmation:
  AC: AC-2.13
  Code reference: betrieb/veroeffentlichen.sh:894
  Evidence: Units zuletzt; rc 4 bei gesperrten Zeilen, installieren nur bei rc 3, keine Teil-Installation
  Status: CONFIRMED

Confirmation:
  AC: AC-2.14
  Code reference: betrieb/veroeffentlichen.sh:860
  Evidence: kopieren nur wenn Ziel fehlt oder Quelle neuer; Test grün; Prüfkosten F004
  Status: CONFIRMED

Confirmation:
  AC: AC-2.15
  Code reference: betrieb/veroeffentlichen.sh:869
  Evidence: alter Bauordner wird nur gelesen, Rückweg-Test grün
  Status: CONFIRMED

Confirmation:
  AC: AC-2.16
  Code reference: betrieb/veroeffentlichen.sh:828
  Evidence: exec bei geänderter veroeffentlichen.sh oder gemeinsam.sh, höchstens einmal
  Status: CONFIRMED

Confirmation:
  AC: AC-2.17
  Code reference: betrieb/veroeffentlichen.sh:657
  Evidence: Anstoß schreibt Ergebnis, löscht Datei, kein gh; engine/rueckmeldungen.py:972 nur Kommentar
  Status: CONFIRMED

Confirmation:
  AC: AC-2.18
  Code reference: betrieb/veroeffentlichen.sh:773
  Evidence: main_klon ohne gh und Reisen-Repo, Test grün
  Status: CONFIRMED

Confirmation:
  AC: AC-2.19
  Code reference: betrieb/gemeinsam.sh:43
  Evidence: einrichten.sh ohne gh auth, Klon statt Reisen-Repo, neue Unit-Pfade (Test)
  Status: CONFIRMED

Confirmation:
  AC: AC-2.20
  Code reference: betrieb/veroeffentlichen.sh:869
  Evidence: Umzugsfehler sind echo; ALARMSTELLEN unverändert; Rauschen F006
  Status: CONFIRMED

Confirmation:
  AC: AC-2.21
  Code reference: docs/betrieb.md:519
  Evidence: Auslieferungstor dokumentiert und getestet; das Infrastruktur-Issue selbst ist ausserhalb dieses Repos und nicht geprüft
  Status: CONFIRMED

Confirmation:
  AC: AC-2.22
  Code reference: betrieb/veroeffentlichen.sh:743
  Evidence: fehlt tests: übersprungen; rot: Warnung und normale Meldung, kein Abbruch
  Status: CONFIRMED

Confirmation:
  AC: AC-2.23
  Code reference: betrieb/gemeinsam.sh:43
  Evidence: nur Platzhalter, Tests auf Privates grün
  Status: CONFIRMED

Confirmation:
  AC: AC-2.24
  Code reference: docs/betrieb.md:507
  Evidence: Abschnitte Bauordner, Veröffentlichen, Anstoß, Überwachung, Einrichten, Umzug vorhanden; ADR-0009 ergänzt
  Status: CONFIRMED

Abdeckung weiterer geänderter Dateien:
  Code reference: betrieb/pruefsitzung.py:12 — nur Gebrauchstext
  Code reference: engine/instanz.py:138 — einstellungen_pruefen fail closed
  Code reference: engine/reisespeicher.py:786 — umschalten_automatisch
  Code reference: engine/rueckmeldungen.py:972 — nur Kommentar
  Code reference: engine/schreiben.py:5509 — Wegwahl, 503 bei SpeicherNichtLesbar
  Code reference: engine/stand.py:155 — fuer_seite nutzt speicherreisen
  Code reference: engine/stand_git.py:64 — reise_aus_head
  Code reference: werkzeuge/adressen_holen.py:15 — nur Gebrauchstext
  Code reference: werkzeuge/grundkarte_auto.py:12 — nur Gebrauchstext
  Code reference: werkzeuge/punkte_holen.py:19 — nur Gebrauchstext
  Code reference: werkzeuge/wasser_pruefen.py:149 — Quellentext, F007
  Code reference: werkzeuge/wissen_punkte_holen.py:13 — nur Gebrauchstext
  Code reference: betrieb/gemeinsam.sh:149 — speicherreisen_lesen, F001
  Code reference: betrieb/einrichten.sh:70 — kein gh, Klon-Prüfung
  Code reference: betrieb/deploy.sh:26 — Modulliste, --dienste

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: BROKEN
═══════════════════════════════════════
Keine CRITICAL/HIGH-Funde, die Kernlogik hält (35/35 Punkte nachgewiesen, mit den Einschränkungen unten). Vier MEDIUM-Funde sollten vor dem Ausliefern behoben oder bewusst akzeptiert werden.

Finding F001: Shell-Entsprechung von speicherreisen() ist bei nicht durchsuchbarem Speicher fail-open
  Severity: MEDIUM
  Evidence: betrieb/gemeinsam.sh:149
  Reproduction: Speicher mit reisen.db anlegen, chmod 000 auf das Verzeichnis, `. betrieb/gemeinsam.sh; speicherreisen_lesen` ergibt rc=0 und leere Liste (Python wirft SpeicherNichtLesbar).

Finding F002: rueckfall wird bei jeder Störung von speicher_reisen_lauf ausgelöst, ohne Rot-Datei und Alarm, mit möglicher 5-Minuten-Schleife
  Severity: MEDIUM
  Evidence: betrieb/veroeffentlichen.sh:843
  Reproduction: Speicher kurz unlesbar oder Deploy-Exit 1 mit C: Klon zurück auf software-gut, Dienste neu gestartet, nächster Takt rollt C erneut aus.

Finding F004: Umzug wiederholt Prüfung (Nachweis oder volle Server-Tests) in jedem Takt, solange Units nicht umgestellt werden können
  Severity: MEDIUM
  Evidence: betrieb/veroeffentlichen.sh:894

Finding F005: Speicherreisen ohne .gebaut und ohne Stempel, die in Git liegen, gelten still als Git-Reise; nach Git-Schreibvorgang dauerhaft "unterschied" (mehrdeutig, Spec schweigt)
  Severity: MEDIUM
  Evidence: engine/reisespeicher.py:712

Niedrig: F003 (Python-Umgebung wird vor der Prüfung verändert, betrieb/veroeffentlichen.sh:812), F006 (Units-Meldung in alter Anordnung, betrieb/veroeffentlichen.sh:1156), F007 (veraltete Aufrufhilfen, werkzeuge/wasser_pruefen.py:149).

Tests: gezielt 367 passed; Gesamtlauf engine/tests 2551 passed, 1 failed (test_packliste_im_browser[webkit], bekannt wackelig #550, einzeln wiederholt 2 passed), 0 übersprungen
Edge cases: siehe Findings
Regressions: keine funktionalen; abgeschwächte Tests ohne Verlust der Absicherung gegen Datenverlust (F005 beschreibt die Verhaltensänderung)
Checklist: 35/35 Punkte belegt; AC-2.21 (Infrastruktur-Issue) nur dokumentarisch prüfbar

## Geprüfte Dateien

- sha256:eb402143b7de3198188ec176ef37db9a891193c22c3f664d9d50f382fc7905a0  betrieb/deploy.sh
- sha256:18c424165a99af0f42757748cfbebb4ec384812db5cad874894f8167ea0f9de8  betrieb/einrichten.sh
- sha256:f6229be937b35a10632e08fb1b62058c844a938241bcfafd5c2ac7b105200039  betrieb/gemeinsam.sh
- sha256:b85689deb5f759f3aa11762178ea19b602ec1b29118a2f0602a1775156fdc027  betrieb/pruefsitzung.py
- sha256:f3e51803f70936ceb03094f783e33f74ceddec95fd4d59bbe04e8157624e677b  betrieb/veroeffentlichen.sh
- sha256:85c8ba91b167a504fa98f3f0f0038876d83c7bf02920616caf42d40312954f8d  docs/betrieb.md
- sha256:0221c06992fe864876124cdfb06d8d3c0fac35a46e40618381053ee26eb1f306  engine/instanz.py
- sha256:1e49099eb3cf8502212d5441bc701f76d6f6f6bf23ac62df251f74dc999719ad  engine/reisespeicher.py
- sha256:5a67869ef04a32d8c9a8250a4677fcc64359614b22b575a21cd480957567e206  engine/rueckmeldungen.py
- sha256:e2b7e9942bfa1603c2f0642927d74014038d30a8c1d80c2ab6cf2f0576fb6299  engine/schreiben.py
- sha256:c14ab51e5925f65e4d6652e8dae64592d1c505697277dadb3213897ecf72ee0a  engine/stand.py
- sha256:d7e92ac1b2890fdf0966bab647d4f375d753655034d6ee4791a0b41ad3cd193d  engine/stand_git.py
- sha256:d8187a45431568f33364b7518dcc2a4bf2d4e72862392d648720b05d30acfd7d  werkzeuge/adressen_holen.py
- sha256:cdb57bf08d485eaa945fa1b6254e765b41286eda2d4461d81b76852de0092cf5  werkzeuge/grundkarte_auto.py
- sha256:125ea4980cf538662a6de493c919949f6d59b686374839d13d062b105f811f12  werkzeuge/punkte_holen.py
- sha256:328c0b6e3245b4f58e82109166c1c8413ccc15e2a95c1084c11559068e58e6f2  werkzeuge/wasser_pruefen.py
- sha256:fdcdd708f6d8cf08b42bf58c83e5b70b5efc0d7de25adfbbd5aa96f456c732a5  werkzeuge/wissen_punkte_holen.py

## Prüfbasis

- base: 7af1f0669c5fd61576962bab24a4bcb8bb2a0a3e
- blob:4746614bb4d74477609a77db9e70a9a92b23be13  betrieb/deploy.sh
- blob:982072a570c941a5e8f6348e838ee66d08495fd9  betrieb/einrichten.sh
- blob:f1f8740f174769fa7228ffddce03232129a0a653  betrieb/gemeinsam.sh
- blob:678b6d4e6b5c246ece0f243bc25e3de84ff66c26  betrieb/pruefsitzung.py
- blob:2cb1d64371779dde7106a025ac36718c318e2a58  betrieb/veroeffentlichen.sh
- blob:40395a5ee1e5c144a8ab070d8ffcad8005546b1d  docs/betrieb.md
- blob:e000306fffe4a2065fa31c5eb3a392b74465802a  engine/instanz.py
- blob:a36bde3191ccc7df43d7930cf68cd1d5d1a989c3  engine/reisespeicher.py
- blob:5abb64136fcbcaf7e25cead95c8b7379e99897e0  engine/rueckmeldungen.py
- blob:4bd14f4df154f01143655ba071d89be07d5caaca  engine/schreiben.py
- blob:e88146a0a60aa07c6ec6cc71bdd58a208eadd0be  engine/stand.py
- blob:6fc580fee227048d5532d110b64815099cbb9442  engine/stand_git.py
- blob:0662b29a58e72f9db21e70b7c9dd0496982b8695  werkzeuge/adressen_holen.py
- blob:60a02e310da610273db0a4a268d6617248e8868c  werkzeuge/grundkarte_auto.py
- blob:22e10cff448c3c31f8547138569ba23810102bf1  werkzeuge/punkte_holen.py
- blob:3c56eab18a2dee26d026f36d679774a50a35eb91  werkzeuge/wasser_pruefen.py
- blob:62e1639fdff4fb2d822867340aa301b4623ea6c2  werkzeuge/wissen_punkte_holen.py
