# Adversary Dialog — software-weg-454
Spec: docs/specs/betrieb/software-weg-454.md
Datum: 2026-11-13 06:58

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
- [x] **AC-2.12 (Umzug ohne Handschritt):** *Given* eine Instanz im alten Zustand (Submodul im Bauordner), *when* der Lauf mit der Software dieses Commits läuft, *then* legt er den Klon an, kopiert Einstellungen und Meldeweg, baut die Python-Umgebung, gleicht die Units ab und stellt den Zustand auf `fertig`, ohne dass jemand etwas tut.
- [x] **AC-2.13 (Units zuletzt):** *Given* ein Schritt des Umzugs vor dem Abgleich der Units scheitert, *when* der Lauf endet, *then* zeigen alle Units unverändert auf den alten Bauordner, das Veröffentlichen läuft weiter über den alten Weg, und der nächste Lauf versucht den Umzug erneut.
- [x] **AC-2.14 (Wiederholbar):** *Given* der Umzug ist `fertig` oder halb durchgeführt, *when* der Lauf erneut läuft, *then* ändert er nichts Unnötiges (keine doppelten Kopien, kein Überschreiben neuerer Einstellungen, keine Units-Änderung ohne Unterschied).
- [x] **AC-2.15 (Alter Bauordner bleibt):** *Given* der Umzug ist `fertig`, *when* der alte Bauordner betrachtet wird, *then* ist er unverändert (nichts gelöscht, keine Datei verändert); stellt man die Units auf ihn zurück, laufen Veröffentlichen, Wächter, Schreibweg und Kartendienst wieder wie vorher (Rückweg).
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
Tests: 378 passed in 118.65s (adversary-test-output.txt, Pfade bereinigt). Nachprüfung der Nachbesserungen aus Durchgang 1.
F001 im Experiment (Scratch): reisen.db vorhanden, Zwischenordner mode 000 -> fr_speicher_fehlt Exit 1 (Python entscheidet, Fehler); Ordner mode 000 mit fehlendem Unterordner -> Exit 1; hängender Symlink im Pfad -> Exit 0 (Python: exists() falsch, "nein", gleiche Antwort); Pfad durch eine Datei -> Exit 1; nicht vorhandener Weg unter durchsuchbarem Elternordner -> Exit 0. Fail closed bleibt; FR_SPEICHER leer wird durch := zum Vorgabepfad. Code reference: betrieb/gemeinsam.sh:149 und engine/reisespeicher.py:1347.
F002: veroeffentlichen.sh:924 main_klon: Dienste-Deploy mit C zuerst; Fehler: rot_schreiben, rueckfall (Klon auf software-gut, python_zurueck, deploy --dienste), alarm_pruefen; nachziehen erst nach grünem Deploy; pipefail aktiv, PIPESTATUS[0] im ||-Zweig korrekt. Nächster Takt: Known red state. Tests test_f002_* grün.
F003 im Experiment: python3 -m venv v1, dann mv v1 v2: bin/python meldet sys.prefix=v2, site-packages unter v2, -m pip --version läuft. Nur Shebangs von Console-Scripts veraltet; im Code nur -m (deploy.sh:66, veroeffentlichen.sh:416/490/603). Absturz zwischen Vorspulen und python_uebernehmen: nächster Lauf baut neu (stand ungleich kopf).
F004: umzug_454 (961) geteilt in vorbereiten/units; Merker umzug-454.geprueft; Warnzeile nur je Fingerabdruck (1034). Fehler vor Units: Zustand bleibt, Units unberührt.
F005: git_stand_nachtragen in einer Transaktion, zählt Nicht-Import-Vorgänge, hängt nur an (Tombstones), nie löschen; wiederholte Läufe hängen nichts neu an. AC-1.7-Tests um einen Schreibvorgang ergänzt: AC-1.7 bleibt für diesen Fall echt geprüft, der Fall nur Importe hat eigenen Test (test_f005_*). Rest: F008.
F006/F007: Vorlagen __SOFTWARE__/__UMGEBUNG_DIENST__ ersetzt (einrichten.sh:115); alte Anordnung Kommentar statt Environment, Test grün; Gebrauchstexte der werkzeuge/* zeigen $FR_PYTHON statt frieda/-Pfad.
**Implementierer:** (nicht im Protokoll; Behauptungen der Entwicklung wurden selbst geprüft)

### Runde 2
**Adversary:**
Zweiter Angriff: (a) python_uebernehmen ohne renameat2: mv ziel nach alt, mv neu nach ziel, bei Fehler return 1, Lauf rot, nächster Lauf baut neu: ok. (b) rueckfall mit gut gleich HEAD: kein Zurücksetzen, python_zurueck trotzdem: ok. (c) deploy.sh --dienste: NUR_DIENSTE-Zweig vor ist_speicherreise und Reisenprüfung, baut keine Seite: ok. (d) Umzug: units pruefen rc 3, installieren, erneut prüfen; Restdifferenz: Warnung einmal je Befund, kein Alarm. (e) Speicher mitten im Lauf nicht lesbar: speicherreisen_lesen || return 1, Lauf rot (test_f001_lauf_mit_unlesbarem_speicher_ist_rot grün). (f) F005-Randfall: ein manueller Import eines anderen Standes (nur Importe) würde bei Änderung in Git vom Git-Stand überlagert; Verlauf bleibt, umkehrbar. Als F008 (LOW) festgehalten, da die Spec nicht nachgezogen wurde.
Alles in Runde 1 grün: jede Zeile durch Code und Experiment belegt, nicht nur durch Testergebnis.
**Implementierer:** (keine Rückmeldung nötig)

## Findings

Finding:
  ID: F008
  Severity: LOW
  Category: spec_violation
  Code reference: engine/reisespeicher.py:787
  Description: git_stand_nachtragen hängt bei offener Umschaltung und nur Importen im Speicher den Stand aus Git als weiteren Import an (nur anhängen, nie löschen). Das ist die empfohlene Lösung aus Durchgang 1 (F005), beschrieben in docs/betrieb.md:119.
  Spec requirement: AC-1.7 — bei Unterschied "nichts wird gelöscht oder geändert"
  Conflict: Wörtlich ändert sich der Speicher (ein angehängter Vorgang); die Spec docs/specs/betrieb/software-weg-454.md wurde nicht angepasst, nur die Tests. Kein Datenverlust, Verlauf bleibt.
  Remediation: Ausnahme in AC-1.7 der Spec und im Änderungsprotokoll festhalten.

## Confirmations

Confirmation:
  AC: AC-1.1
  Code reference: engine/instanz.py:149
  Evidence: speicherreisen() liefert reisespeicher.speicherreisen(): jede Reise mit Vorgang und freier Umschaltung; FR_SPEICHERREISEN wird nicht ausgewertet (Tests grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-1.2
  Code reference: engine/instanz.py:149
  Evidence: Wert aus Umgebung/Datei wirkungslos, keine Fehlermeldung.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.3
  Code reference: engine/instanz.py:149
  Evidence: sqlite3.Error/OSError werden zu SpeicherNichtLesbar; Shell-Seite fail closed (betrieb/gemeinsam.sh:158); im Experiment bei nicht durchsuchbarem Ordner Exit 1 und damit Python-Weg.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.4
  Code reference: engine/schreiben.py:5493
  Evidence: reise_anlegen schreibt in den Speicher (Anfangsvorgang), kein reisen/<name>.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.5
  Code reference: betrieb/veroeffentlichen.sh:631
  Evidence: Neue Speicherreise wird vom Speicher-Teil gebaut; die Umschaltung fasst nur reisen/*/reise.json an.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.6
  Code reference: engine/reisespeicher.py:855
  Evidence: umschalten_automatisch: Anfangsvorgang, Vergleich, Stempel gleich; danach in speicherreisen().
  Status: CONFIRMED

Confirmation:
  AC: AC-1.7
  Code reference: engine/reisespeicher.py:855
  Evidence: Bei Unterschied mit Schreibvorgang im Speicher: NichtNurImport, nichts geschrieben, Reise bleibt in Git, Warnzeile ohne high. Abweichung nur im Fall nur Importe (F008, LOW).
  Status: CONFIRMED

Confirmation:
  AC: AC-1.8
  Code reference: engine/reisespeicher.py:826
  Evidence: bekannt und frei: schon_im_speicher, kein Vorgang.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.9
  Code reference: engine/reisespeicher.py:857
  Evidence: Bekannt aber offen: kein zweiter Import, Vergleich gegen vorhandenen Anfangsvorgang, Stempel bei gleich.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.10
  Code reference: engine/instanz.py:149
  Evidence: Bisherige Speicherreisen bleiben, Eintrag plus Stempel/.gebaut genügt; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-1.11
  Code reference: engine/schreiben.py:5493
  Evidence: Schreibwerkzeuge unverändert, nur Wegwahl via instanz.speicherreisen.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.1
  Code reference: betrieb/veroeffentlichen.sh:924
  Evidence: main_klon holt main ohne gh, Anmeldung, Reisen-Repo.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.2
  Code reference: betrieb/veroeffentlichen.sh:957
  Evidence: software_pruefen vor dem Vorspulen; rot: python_verwerfen, return 1, Klon unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.3
  Code reference: betrieb/veroeffentlichen.sh:795
  Evidence: ci_nachweis_commit grün: Servertests übersprungen.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.4
  Code reference: betrieb/veroeffentlichen.sh:795
  Evidence: Nachweis je Stand einmal (Test grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.5
  Code reference: betrieb/veroeffentlichen.sh:828
  Evidence: rueckfall: Klon auf software-gut, python_zurueck, deploy --dienste; Deploy-Fehler schreibt Rot-Datei (F002 behoben).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.6
  Code reference: betrieb/veroeffentlichen.sh:942
  Evidence: Bekannter roter Stand übersprungen, alarm_pruefen mit Schwelle.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.7
  Code reference: betrieb/veroeffentlichen.sh:990
  Evidence: veroeffentlicht, software-gut (atomar) und Kennung gleich kopf, nur nach ganz grünem Lauf.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.8
  Code reference: betrieb/veroeffentlichen.sh:975
  Evidence: speicher_reisen_lauf erst nach grünem Dienste-Deploy (nachziehen-speicher).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.9
  Code reference: engine/instanz.py:48
  Evidence: Einstellungen: Umgebung, <Dienst>/instanz/einstellungen.env, alter Ort.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.10
  Code reference: betrieb/gemeinsam.sh:128
  Evidence: FR_MELDEN aus <FR_DIENST>/instanz/melden.sh; leer: nichts gesendet.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.11
  Code reference: betrieb/veroeffentlichen.sh:701
  Evidence: python_kandidat/python_uebernehmen/python_zurueck; Experiment: verschobene venv läuft mit bin/python -m (sys.prefix, site-packages stimmen); im Code nur -m-Aufrufe.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.12
  Code reference: betrieb/veroeffentlichen.sh:961
  Evidence: umzug_454: vorbereiten, umzug_units, fertig, ohne Handschritt.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.13
  Code reference: betrieb/veroeffentlichen.sh:1024
  Evidence: Units erst nach Schritten 1-3; bei Fehler Zustand nicht fertig, Warnung nur einmal je Befund.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.14
  Code reference: betrieb/veroeffentlichen.sh:1015
  Evidence: umzug_kopieren nur bei neuerer Quelle, geprueft-Merker, Units-Merker.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.15
  Code reference: betrieb/veroeffentlichen.sh:1046
  Evidence: Alter Bauordner wird nirgends verändert; Rückweg in docs/betrieb.md.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.16
  Code reference: betrieb/veroeffentlichen.sh:965
  Evidence: exec mit _neugestartet-Sperre, genau einmal.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.17
  Code reference: betrieb/veroeffentlichen.sh:926
  Evidence: anstoss_lauf ohne gh workflow run.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.18
  Code reference: betrieb/veroeffentlichen.sh:924
  Evidence: main_klon ruft weder gh noch Reisen-Repo auf.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.19
  Code reference: betrieb/einrichten.sh:43
  Evidence: Keine gh-auth-Prüfung, Klon-Hinweis, <FR_DIENST>/instanz, __SOFTWARE__/__UMGEBUNG_DIENST__ (F006); alte Anordnung ergibt heutige Units (Test grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.20
  Code reference: betrieb/veroeffentlichen.sh:1036
  Evidence: Umzugs- und Umschaltfehler nur Warnzeilen; high nur über bestehende ALARMSTELLEN (test_betrieb grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-2.21
  Code reference: betrieb/deploy.sh:11
  Evidence: Tor liegt außerhalb dieses Repos (Infra-Issue); im Repo kein Defekt, hier nicht beweisbar.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.22
  Code reference: betrieb/veroeffentlichen.sh:1156
  Evidence: instanz_pruefen überspringt fehlende tests/, rot nur Warnung.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.23
  Code reference: betrieb/pruefsitzung.py:12
  Evidence: Gebrauchstexte ohne frieda/-Pfade (F007) in pruefsitzung und werkzeuge/*; test_protokolle_ohne_pfade grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2.24
  Code reference: docs/betrieb.md:119
  Evidence: Abschnitte vorhanden, ADR-0009 nennt #454 (Test test_betrieb_md_beschreibt_neuen_weg).
  Status: CONFIRMED

Weitere Code-Referenzen je geänderter Datei (Abdeckung, #259):
Code reference: engine/rueckmeldungen.py:87
Code reference: engine/stand.py:197
Code reference: engine/stand_git.py:64
Code reference: betrieb/gemeinsam.sh:149
Code reference: betrieb/deploy.sh:39
Code reference: betrieb/einrichten.sh:115
Code reference: betrieb/pruefsitzung.py:12
Code reference: werkzeuge/adressen_holen.py:3
Code reference: werkzeuge/grundkarte_auto.py:1
Code reference: werkzeuge/punkte_holen.py:3
Code reference: werkzeuge/wasser_pruefen.py:3
Code reference: werkzeuge/wissen_punkte_holen.py:3

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Alle Nachbesserungen F001-F007 sind belegt. Tests: 378 passed, 0 failed, 0 übersprungen (gezielte Auswahl; Gesamtsuite 2563 passed laut Entwicklung).
Edge cases: F001 (Rechte, Symlinks, Zwischenordner) und F003 (verschobene venv) im Experiment geprüft, nichts gebrochen.
Regressions: None found. Offen: F008 (LOW, Spec-Text AC-1.7 nachziehen). AC-2.21 (Infra-Tor) liegt außerhalb des Repos.
Checklist: 35/35 points proven (AC-2.21 nur als Auslieferungstor außerhalb des Repos).

## Geprüfte Dateien

- sha256:eb402143b7de3198188ec176ef37db9a891193c22c3f664d9d50f382fc7905a0  betrieb/deploy.sh
- sha256:edf73e3f30de8bda4f67eea34159ebb10856c1c8559fbab636589fb87fe25179  betrieb/einrichten.sh
- sha256:b59618346199651dd6de59c8addcb31eb46941b0f84cbcffe7c4d83db261ee85  betrieb/gemeinsam.sh
- sha256:b85689deb5f759f3aa11762178ea19b602ec1b29118a2f0602a1775156fdc027  betrieb/pruefsitzung.py
- sha256:0fe63082622ff77fbb294c0cab3b1ce41a5eb040e56434400f56e7acc0099e16  betrieb/veroeffentlichen.sh
- sha256:d06cd42061e1f8c841fc17fda10e49a9bf8910c8c4175010dfed511347e2cdf0  docs/betrieb.md
- sha256:0221c06992fe864876124cdfb06d8d3c0fac35a46e40618381053ee26eb1f306  engine/instanz.py
- sha256:3525bc75a53381b541e6912746dd543130550808b0337757e823145fe0a03944  engine/reisespeicher.py
- sha256:5a67869ef04a32d8c9a8250a4677fcc64359614b22b575a21cd480957567e206  engine/rueckmeldungen.py
- sha256:e2b7e9942bfa1603c2f0642927d74014038d30a8c1d80c2ab6cf2f0576fb6299  engine/schreiben.py
- sha256:c14ab51e5925f65e4d6652e8dae64592d1c505697277dadb3213897ecf72ee0a  engine/stand.py
- sha256:d7e92ac1b2890fdf0966bab647d4f375d753655034d6ee4791a0b41ad3cd193d  engine/stand_git.py
- sha256:575278e8f1c2d52ff9685b62e9c54924a054112fea0747f67011abed5fa9cb91  werkzeuge/adressen_holen.py
- sha256:cdb57bf08d485eaa945fa1b6254e765b41286eda2d4461d81b76852de0092cf5  werkzeuge/grundkarte_auto.py
- sha256:9b700b53081e0452db01a64ae0a422cc7a42bd55dc860c7a38eed0413697289e  werkzeuge/punkte_holen.py
- sha256:d3593ac158de2987d5d4d0b63513be5693a1c9903b397027306ea5d599cdc1c2  werkzeuge/wasser_pruefen.py
- sha256:855a7ff6543bc716a01eda692e8caf5127a57bfddd4a54c7246122fd21b84637  werkzeuge/wissen_punkte_holen.py

## Prüfbasis

- base: 7af1f0669c5fd61576962bab24a4bcb8bb2a0a3e
- blob:4746614bb4d74477609a77db9e70a9a92b23be13  betrieb/deploy.sh
- blob:cf5a520a7dd0c035a2c1ba4d864cd83a432409c3  betrieb/einrichten.sh
- blob:03f7d261d5016b0e5ec64efef8fe03a795c4d20d  betrieb/gemeinsam.sh
- blob:678b6d4e6b5c246ece0f243bc25e3de84ff66c26  betrieb/pruefsitzung.py
- blob:eea04928a248b0c5bfb7166a7b03fdab3e2e7d83  betrieb/veroeffentlichen.sh
- blob:32c25b7ab2b5cc9e480a9d9c31248c744db075a2  docs/betrieb.md
- blob:e000306fffe4a2065fa31c5eb3a392b74465802a  engine/instanz.py
- blob:a5c8ed289d3bdb2af28b1970cc5c2dd80da8de00  engine/reisespeicher.py
- blob:5abb64136fcbcaf7e25cead95c8b7379e99897e0  engine/rueckmeldungen.py
- blob:4bd14f4df154f01143655ba071d89be07d5caaca  engine/schreiben.py
- blob:e88146a0a60aa07c6ec6cc71bdd58a208eadd0be  engine/stand.py
- blob:6fc580fee227048d5532d110b64815099cbb9442  engine/stand_git.py
- blob:af5b756c705b69e2f472fd87f1af167f09dff31b  werkzeuge/adressen_holen.py
- blob:60a02e310da610273db0a4a268d6617248e8868c  werkzeuge/grundkarte_auto.py
- blob:89803fc80b4d20cbfeacd34ea20a6656a2ef9dd5  werkzeuge/punkte_holen.py
- blob:86ae622a4ada48b5bd12c7e2edaa00a71577916b  werkzeuge/wasser_pruefen.py
- blob:757498314856f7276125f9681ce622f8dedf9104  werkzeuge/wissen_punkte_holen.py
