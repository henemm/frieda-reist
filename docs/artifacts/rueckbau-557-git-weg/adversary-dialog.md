# Adversary Dialog — rueckbau-557-git-weg
Spec: docs/specs/betrieb/rueckbau-git-weg-557.md
Datum: 2026-11-20 13:14

## Checkliste
- [~] **AC-1:** Der Zeitplan des Workflows „Software nachziehen“ im Reisen-Repo der Instanz ist abgeschaltet; in der Software gibt es keinen Workflow und kein Skript dazu mehr (siehe L2).
- [~] **AC-2:** Die Überwachung in der Infrastruktur liest den Stand des Klons statt `_bau/.git/modules/frieda/HEAD` und kennt keine alte Anordnung (`frieda_umgezogen`/`frieda_software_ordner` ohne Zweig für `_bau`); das Issue im Infrastruktur-Repo ist geschlossen und in #557 verlinkt, bevor L3 vorgespult wird.
- [x] **AC-3:** `engine/schreiben_git.py` und `engine/stand_git.py` sind gelöscht, nichts importiert sie.
- [x] **AC-4:** `/gesund` hat keinen Git-Teil: Es wird nie ein Git-Aufruf gegen die Software-Wurzel gemacht.
- [x] **AC-5:** `/gesund` bleibt fail closed (#361): unlesbarer Speicher oder `EinstellungenNichtLesbar` ergibt 503, nie „gesund“.
- [x] **AC-6:** `speicherreisen()` gibt jede Reise mit Vorgang im Speicher zurück, ohne Filter durch Stempel oder Git-Stand; beide Beispielreisen gehen durch.
- [x] **AC-7:** Ist der Speicher nicht lesbar, löst `speicherreisen()` einen Fehler aus (nie leere Liste).
- [x] **AC-8:** Der Schreibweg ist nur der Speicherweg (Schreiben, Verwerfen, Buchung, Export); eine Reise ohne Speichereintrag liefert `reise_nicht_im_speicher`.
- [x] **AC-9:** `reisespeicher.py` enthält keine Umschaltung (`_git_baum`, `umschaltung_frei`, Stempel, `umschalten_automatisch`, `git_stand_nachtragen`, CLI `umschalten`/`umschaltung`).
- [x] **AC-10:** `veroeffentlichen.sh` ruft keine entfernten Befehle von `reisespeicher.py` mehr auf; `stand.py`/`fuer_seite` haben keinen Git-Zweig.
- [x] **AC-11:** Eine vorhandene Zeile `FR_SPEICHERREISEN` in den Einstellungen der Instanz bleibt liegen und wird ohne Fehler ignoriert (kein Handschritt, #250).
- [x] **AC-12:** Die Modulliste in `betrieb/deploy.sh` enthält kein gelöschtes Modul; `deploy.sh` baut nichts aus `$WURZEL/reisen`.
- [x] **AC-13:** Entfallene Texte sind in allen Sprachdateien entfernt; die Ausnahmelisten in `engine/tests/test_texte.py` sind nur kürzer geworden.
- [~] **AC-14:** Die Tests der Instanz unter `<FR_DIENST>/instanz/tests` laufen vor dem Vorspulen mit dem Branch grün.
- [x] **AC-15:** `betrieb/veroeffentlichen.sh` hat nur den Weg über den Klon (`main_klon`); alter `main()`, `umzug_*` (außer `umzug_fertig_im_klon`), `reisen_des_laufs`, `ci_nachweis`, `anstoss_weitergeben`, `software_anstossen`, `git_reisen_uebrig`, `git_reisen_umschalten` und die Übergabe an den Klon sind entfernt; `software_klon`, `software_kennung`, `speicher_reisen_lauf`, `speicher_rot_melden`, `pruefen_lauf`, `anstoss_lauf` bleiben.
- [x] **AC-16:** Verhalten des Laufs im Klon bleibt unverändert: grüner Lauf, Prüfung vor Umschalten, Rot-Datei, Rückfall auf `software-gut`, Heartbeat nur bei Erfolg (Readiness), Alarmentprellung (#446).
- [x] **AC-17:** `gemeinsam.sh` und `einrichten.sh` kennen keine alte Anordnung (Superprojekt, `nur_bauordner`, `frieda/`), keinen Standardwert für `FR_SCHREIBKOPIE`, kein `FR_SPEICHERREISEN` und kein `FR_NACHZIEHEN_*`; `schreiben.service` hat keine Zeile `ReadWritePaths=-__WURZEL__-schreiben`.
- [x] **AC-18:** `vergleichslauf.sh`, `software-nachziehen.sh`, `software-nachziehen.yml`, `messlauf-schreibweg.py` und `test_software_nachziehen.py` sind gelöscht; `einstellungen.beispiel` und `.github/workflows/tests.yml` nennen sie und ihre Werte nicht.
- [x] **AC-19:** Die Liste `ALARMSTELLEN` in `test_betrieb.py` gewinnt keine neue Stelle.
- [x] **AC-20:** Usage-Texte (`werkzeuge/karte-holen.sh`, `betrieb/sichern.sh`) nennen keinen Pfad mit `frieda/`.
- [x] **AC-21:** Die geänderte Units-Vorlage wird auf der Instanz ohne Handschritt wirksam (Abgleich über Veröffentlichen/`units.py`).
- [~] **AC-22:** Die Tests der Instanz laufen vor dem Vorspulen grün mit dem Branch.
- [x] **AC-23:** Sind alle Bedingungen erfüllt, archiviert der Lauf `_bau` (ohne `-schreiben-*`) nach `<FR_DIENST>/archiv/`, entfernt `_bau` und alle `_bau-schreiben-*` und setzt danach den Merker `<FR_DIENST>/altbau-557`.
- [x] **AC-24:** Nur wenn `umzug-454 = fertig`; sonst nichts.
- [x] **AC-25:** Nur wenn alle Units auf den Klon zeigen; sonst nichts, Warnzeile.
- [x] **AC-26:** Nur wenn jede Reise aus `_bau/reisen` Speicherreise ist; sonst nichts, Warnzeile mit Reisenamen.
- [x] **AC-27:** Vor dem Löschen prüft der Schritt den freien Platz für das Archiv; reicht er nicht, wird nichts gelöscht (Warnzeile).
- [x] **AC-28:** Scheitert das Archiv oder ist es nicht lesbar, bleibt `_bau` unverändert und der Merker ungesetzt.
- [x] **AC-29:** Jeder zu löschende Pfad liegt aufgelöst innerhalb von `FR_SEITEN`; `FR_SEITEN` selbst, `_software`, `_dienst`, Links auf sie und Pfade außerhalb werden nie gelöscht.
- [x] **AC-30:** Idempotent: Mit Merker oder ohne Altbau tut der Schritt nichts (kein zweites Archiv, keine Warnzeile).
- [x] **AC-31:** Fehler sind nur eine Warnzeile, einmal je Störung entprellt; kein `high`-Alarm und kein Abbruch des Laufs (#446).
- [x] **AC-32:** Der Schritt ändert Speicher-Teil, Bau und Heartbeat des Laufs nicht; der nächste Lauf versucht es bei Fehlern erneut.
- [~] **AC-33:** L3 wird erst vorgespult, wenn AC-2 erfüllt ist und die Tests der Instanz grün sind.
- [x] **AC-34:** `docs/betrieb.md` beschreibt den Ist-Zustand ohne Git-Weg, ohne Zustand `alt`, ohne Rückweg, ohne Workflow „Software nachziehen“ und ohne Anordnung mit `frieda/`; sie beschreibt das Aufräumen (`altbau_entfernen`, Archiv) und den bewusst fehlenden Rückweg samt Rückfall (Reisespeicher, Archiv, GitHub-Archiv).
- [x] **AC-35:** ADR-0009, `CLAUDE.md` (Regel zum Workflow) und `openspec.yaml` sind angepasst; Spec 454 trägt im Kopf einen Hinweis auf diesen Rückbau, der Rest bleibt unverändert, außer AC-39.
- [x] **AC-39:** Given die Known Limitations der Spec 454 zu AC-2.4/AC-2.6, AC-2.17 und den Usage-Texten mit `frieda/` / When der Rückbau ausgeliefert ist / Then sind sie abschließend erledigt: Kein Skript der Software ruft mehr `gh workflow run` auf (AC-2.17 gilt damit ohne Einschränkung), die Usage-Texte nennen kein `frieda/` mehr (AC-20), und die erneute Prüfung eines roten Stands nach #203 bleibt als bewusstes Verhalten bestehen (AC-2.4/AC-2.6, höchstens eine Abfrage je Stunde und Stand); Spec 454 vermerkt das in ihren Known Limitations als abgeschlossen mit Verweis auf #557.
- [~] **AC-36:** Das Reisen-Repo der Instanz ist archiviert, nicht gelöscht; der Stand ist im Issue vermerkt.
- [x] **AC-37:** Die gesamte Testsuite ist grün (lokal und Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`); `engine/tests/test_protokolle_ohne_pfade.py` bleibt grün.
- [x] **AC-38:** Es bleibt kein Handschritt in der Instanz nach dem Software-Wechsel (#250).

## Dialog

Testlauf (Adversary): 581 passed, 0 failed, 0 übersprungen (docs/artifacts/rueckbau-557-git-weg/adversary-test-output.txt). Die volle Suite (3354 passed) liegt in test-green-output.txt. Legende der Checkliste: [x] bewiesen, [~] extern/Auslieferungstor, nachgelagert (Software-Seite stimmt).

### Runde 1
**Adversary:** Jeder AC einzeln, mit Beweis.

Confirmation:
  AC: AC-3, AC-9, AC-10
  Code reference: engine/reisespeicher.py:676
  Evidence: Grep nach den entfernten Modulen, Umschalt-Namen, FR_SPEICHERREISEN und FR_NACHZIEHEN über engine/, betrieb/, werkzeuge/, .github, openspec.yaml, CLAUDE.md findet nur Tests, die das Fehlen prüfen (test_git_module_sind_geloescht, test_reisespeicher_hat_keine_umschaltung, test_veroeffentlichen_ruft_keine_umschaltung).
  Status: CONFIRMED

Confirmation:
  AC: AC-4, AC-5
  Code reference: engine/schreiben.py:6176
  Evidence: /gesund ruft nur instanz.speicherreisen() und speicher_gesund() (SELECT 1); EinstellungenNichtLesbar/SpeicherNichtLesbar ergibt 503, fehlende Datenbank ergibt False (503). Kein subprocess. Test test_gesund_ohne_git_teil_im_klon.
  Status: CONFIRMED

Confirmation:
  AC: AC-6, AC-7
  Code reference: engine/instanz.py:149
  Evidence: speicherreisen() ist ein SELECT DISTINCT ohne Filter (engine/reisespeicher.py:676); sqlite3.Error und OSError werden zu SpeicherNichtLesbar (fail closed); ein kaputter Link zählt nicht als „keine Datenbank“. Test test_speicherreisen_ohne_filter für beide Beispielreisen.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:5595
  Evidence: reise_nicht_im_speicher als Ablehnung (5595), 503 bei Verwerfen/Buchung (5698) und Schreiben (6032); Texte in engine/texte_de.py:942 und engine/texte_en.py:941. arten_uebernehmen liest die andere Reise über fremde_datei() aus dem Speicher (schreiben.py:4750), die eigene Reise wird abgelehnt; packliste_uebernehmen ebenso (5174). Test test_reise_ohne_speichereintrag_ist_503.
  Status: CONFIRMED

Confirmation:
  AC: AC-10 (stand.py)
  Code reference: engine/stand.py:136
  Evidence: fuer_seite ohne Zweig für den alten Weg. engine/neu.py:1225 nutzt den Versionsbefehl nur für die Software-Kennung (legitim); engine/neu.py:1263 nachziehen_speicher bleibt.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: betrieb/gemeinsam.sh:95
  Evidence: kein Code liest FR_SPEICHERREISEN mehr; test_fr_speicherreisen_in_einstellungen_wird_ignoriert.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: betrieb/deploy.sh:28
  Evidence: RM/KN/SB/PS-Modullisten nennen nur vorhandene Module (Abgleich mit der Liste engine/*.py); Modullisten-Test in test_betrieb.py grün; Sprachdateien per Glob (Zeile 27).
  Status: CONFIRMED

Confirmation:
  AC: AC-13, AC-19
  Code reference: engine/texte_de.py:942
  Evidence: test_entfallene_texte_in_allen_sprachen_weg und test_texte.py grün (Ausnahmelisten unverändert, nicht länger); der Diff zeigt keine Änderung an ALARMSTELLEN.
  Status: CONFIRMED

Confirmation:
  AC: AC-15, AC-16
  Code reference: betrieb/veroeffentlichen.sh:698
  Evidence: nur der Klon-Weg; test_veroeffentlichen_hat_nur_den_klon_weg, test_lauf_im_klon_gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-17, AC-18, AC-20
  Code reference: betrieb/einrichten.sh:123
  Evidence: kein FR_SCHREIBKOPIE-Standardwert in gemeinsam.sh, einrichten.sh, einstellungen.beispiel (Grep leer); schreiben.service hat nur ReadWritePaths=__WURZEL__ __DIENST__ __KONTEN__ __SEITEN__ __ABLAGE__ (Zeile 50); gelöschte Dateien laut Arbeitsstand; test_gemeinsam_und_einrichten_ohne_alte_anordnung, test_usage_texte_ohne_frieda_pfad.
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: betrieb/veroeffentlichen.sh:956
  Evidence: units_abgleichen meldet Exit 4 nur als Warnung (kein Alarm, kein Abbruch); die Abweichung steht in docs/betrieb.md Zeile 380 (Einmalschritt einrichten.sh --installieren, altbau_entfernen wartet nicht darauf). test_units_ohne_handschritt belegt Exit 4 mit BLOCKED nur auf ReadWritePaths.
  Status: CONFIRMED

Confirmation:
  AC: AC-23 bis AC-32
  Code reference: betrieb/veroeffentlichen.sh:822
  Evidence: altbau_entfernen: Merker-Prüfung (824), umzug-454=fertig (835), Pfadprüfung mit -L, realpath -e und Gleichheit mit FR_SEITEN/Name (839), Schutz von FR_WURZEL/FR_DIENST/FR_SPEICHER/_software/_dienst (844), Reisen im Speicher (856), Units (862), Platzprüfung (871), Archiv mit Lesetest über tar -tzf und Reise-Datei-Prüfung (889), erneute Linkprüfung direkt vor dem Löschen (896), Merker erst nach dem Löschen (899), Warnung nur über altbau_warnen mit Schlüssel (816, entprellt), Rückgabe immer 0, Aufruf (698) zwischen Lesen der Reisen und Speicher-Teil, Heartbeat unberührt. Tests test_altbau_* (Archiv, Zustand, Units, Speicherreise, Platz, Archivfehler, Pfade: _bau als Link nach außen, auf _dienst, auf _software; Idempotenz; kein high; Lauf läuft weiter) alle grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-34, AC-35, AC-39
  Code reference: engine/rueckmeldungen.py:1194
  Evidence: docs/betrieb.md Zeile 569 „Kein Rückweg“ samt Rückfall; test_betrieb_md_ohne_git_weg_und_rueckweg, test_spec_454_known_limitations_abgeschlossen, test_adr_und_regeln_ohne_workflow_software_nachziehen grün; rueckmeldungen.py ohne Aufruf des alten Wegs (Gesundheit je Reise nur über os.access).
  Status: CONFIRMED

Confirmation:
  AC: AC-37, AC-38
  Code reference: engine/tests/test_rueckbau_557.py:581
  Evidence: test_protokolle_ohne_pfade.py und die gezielte Auswahl grün (581 passed); volle Suite 3354 passed. Kein Handschritt außer dem dokumentierten Einmalschritt beim Ausliefern (Tech Lead).
  Status: CONFIRMED

Extern/Auslieferungstor, nachgelagert: AC-1 (Workflow im Reisen-Repo deaktiviert, prüfbar per Workflow-Liste des Reisen-Repos mit --all), AC-2 (Infrastruktur-Issue henemm-infra#479 offen, nach VERIFIED), AC-14/AC-22/AC-33 (Instanz-Tests, Vorspul-Tor), AC-36 (Archivierung). Software-Seite: kein Workflow und kein Workflow-Aufruf in der Software (test_kein_workflow_zeitplan_in_der_software, test_kein_gh_workflow_run_in_der_software).
**Implementierer:** (nicht beteiligt, Kontext isoliert)

Confirmation:
  AC: AC-13
  Code reference: engine/texte_en.py:941
  Evidence: Diff gegen die Basis: texte_en.py und texte_de.py verlieren exakt dieselben vier Schlüssel (schreiben.dienst.repo_nicht_erreichbar_spaeter, repo_nicht_erreichbar, umschaltung_nicht_freigegeben, reise_im_speicher); kein neuer Schlüssel; kein Code verwendet sie noch (Grep leer); der bleibende Schlüssel reise_nicht_im_speicher steht in beiden Dateien (texte_en.py:941, texte_de.py:942).
  Status: CONFIRMED

### Runde 2
**Adversary:** Angriffe auf altbau_entfernen und Randfälle.

- Symlinks: `_bau` als Link auf _software oder _dienst, `_bau-schreiben-*` als Link auf _dienst: der -L-Zweig (betrieb/veroeffentlichen.sh:839) warnt und löscht nichts; Tests grün. Das Löschen folgt keinen Links, die Linkprüfung läuft direkt davor erneut (896).
- Leerzeichen/Glob: alle Pfade in Anführungszeichen, Glob nur als `"$FR_SEITEN"/_bau-schreiben-*` mit -e/-L-Wächter gegen das unaufgelöste Muster; der Warnschlüssel enthält den Pfad.
- Platz: df -PB1 plus 512 MiB Reserve; nicht ermittelbar ergibt Warnung statt Löschen (871).
- Archiv: .neu-Datei, tar -tzf lesbar, jede Reise aus _bau/reisen im Archiv; erst dann mv und Löschen; Fehler entfernt die .neu-Datei (889).
- Units-Bedingung gegen die akzeptierte Abweichung: Exit 4 mit einer ReadWritePaths-Zeile ohne Pfad von _bau blockiert nicht (test_altbau_reine_readwritepaths_abweichung_haelt_nicht_auf). Echte Ortsabweichung: units.py gibt bei geänderten ExecStart/Environment die installierte Zeile samt Pfad aus (betrieb/units.py:146-150), dann greift der Vergleich auf den _bau-Pfad (862); Exit 1 oder unbekannte Codes warnen ebenfalls (test_altbau_nur_wenn_units_auf_klon_zeigen).
- Entprellung und kein high: altbau_warnen schreibt den Merker nur bei neuem Schlüssel (816), kein Alarmaufruf; test_altbau_fehler_sind_keine_high_meldung, ALARMSTELLEN unverändert.
- Heartbeat und Lauf: Rückgabe immer 0, erfolg_melden bleibt am Ende; test_altbau_haelt_den_lauf_nicht_auf.
- Teilausfall: schlägt das Löschen bei einem späteren Ziel fehl, versucht der nächste Lauf es erneut (Archiv nur, solange _bau existiert); Merker nur nach Erfolg.
- Grenze: nicht live auf dem echten Server geprüft (nur Tests und Lesen des Codes, nichts unter /srv geändert).

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:844
  Description: Die Schutzliste „darf nicht innerhalb des zu löschenden Ordners liegen“ nennt FR_WURZEL, FR_DIENST, FR_SPEICHER, _software, _dienst, nicht aber FR_ABLAGE, FR_KONTEN und FR_KONNEKTOR.
  Spec requirement: AC-29 — nie löschen, was Klon, Dienst oder Speicher berührt.
  Conflict: Die Vorgaben aus gemeinsam.sh liegen außerhalb von _bau (gemeinsam.sh:95, FR_KONTEN=FR_SEITEN/_konten); nur eine abweichende Einstellung einer Instanz in _bau wäre betroffen. Kein Verstoß gegen die Spec, nur Härtung.
  Remediation: FR_ABLAGE, FR_KONTEN, FR_KONNEKTOR in die for-Liste (Zeile 844) aufnehmen.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:809
  Description: umzug_fertig_im_klon verlangt units.py pruefen mit Exit 0. Weicht eine Unit nur in der gesperrten ReadWritePaths-Zeile ab (Exit 4), würde umzug-454 auf einer noch nicht fertigen Instanz nicht auf fertig gesetzt.
  Spec requirement: AC-21/AC-25 — die akzeptierte Abweichung darf das Aufräumen nicht blockieren.
  Conflict: Betrifft nur Instanzen ohne Zustand fertig; die Zielinstanz hat umzug-454 = fertig (Zeile 807 kehrt vorher zurück), kein praktischer Fehler.
  Remediation: Optional Exit 3/4 ohne Nennung des alten Bauordners wie in altbau_entfernen behandeln.

Finding:
  ID: F003
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/schreiben.py:5158
  Description: fremde_datei schluckt alle Lesefehler und liefert None; arten_uebernehmen meldet dann arten_uebernehmen.2 (Reise ohne Arten) statt eines Speicherfehlers.
  Spec requirement: AC-8 — Speicherweg; Fehler dürfen nicht still als leer gelten (#361).
  Conflict: Bei unlesbarem Speicher wird abgelehnt (nichts geschrieben), also sicher; nur die Meldung ist ungenau.
  Remediation: sqlite3.Error und OSError als eigene Ablehnung weiterreichen.

Finding:
  ID: F004
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/instanz.py:149
  Description: docs/betrieb.md:377 spricht noch von „Bauordner mit .git“ als Schreibziel der Unit, die Vorlage (betrieb/vorlagen/schreiben.service:50) nennt ihn nicht mehr einzeln. Veralteter Halbsatz, kein Verhalten.
  Spec requirement: AC-34 — Doku beschreibt den Ist-Zustand.
  Conflict: Geringe Unschärfe in der Beschreibung; keine Blockade.
  Remediation: Halbsatz auf „Klon der Software“ ändern.

Confirmation:
  AC: Pflichtdateien vollständig
  Code reference: engine/neu.py:1263
  Evidence: engine/stand.py:136; engine/rueckmeldungen.py:1194; engine/reisespeicher.py:676; engine/schreiben.py:6176; engine/instanz.py:149; engine/texte_de.py:942; engine/texte_en.py:941; betrieb/veroeffentlichen.sh:822; betrieb/gemeinsam.sh:95; betrieb/einrichten.sh:123; betrieb/deploy.sh:28
  Status: CONFIRMED
**Implementierer:** (nicht beteiligt)

### Runde 3
**Adversary:** Nachprüfung der Nachbesserung zu AC-32 (set -e in altbau_entfernen), mit Blick auf AC-28, AC-30, AC-31.

Zeile für Zeile geprüft, was unter `set -euo pipefail` den Lauf abbrechen könnte:
- `mkdir -p` (betrieb/veroeffentlichen.sh:873), `mv "$tmp" "$archiv"` (891) und die Merker-Kette (899-900) enden bei Fehler jetzt in altbau_warnen und `return 0`; bei mv und Merker wird die `.neu`-Datei entfernt.
- Schon gesichert: `aus="$(units pruefen)" || rc=$?`, `liste="$(tar -tzf)" || rc=2`, `du ... || echo 0` (Leerwert ergibt gültige Arithmetik), `df ... || true`, `realpath ... || true`, grep in `||`-Kette, `rm -rf` mit `||`.
- altbau_warnen (815-820): Lesen mit `|| true`, Schreiben mit `|| true`, letzter Befehl liefert 0; kann den Lauf nicht abbrechen.
- Der Aufruf (698) ist nackt, daher zählt jede ungesicherte Stelle; einzige verbleibende: `seiten_real="$(cd "$FR_SEITEN" && pwd -P)"` (840), siehe F005.
- Merker nicht schreibbar nach dem Löschen: Warnung "merker" einmal; der nächste Lauf findet keine Ziele mehr (`ziele` leer) und kehrt stumm mit 0 zurück: keine Endlos-Warnung, nichts Falsches getan.
- AC-28: bei Archivordner-Fehler vor tar kein Löschen, kein Merker (Test unten). AC-30/AC-31: Warnschlüssel "archiv" entprellt, kein Alarmaufruf in den neuen Zweigen.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:840
  Description: `seiten_real="$(cd "$FR_SEITEN" && pwd -P)"` ist eine ungesicherte Zuweisung; scheitert cd (Ordner existiert, ist aber nicht betretbar), bricht set -e den Lauf ab.
  Spec requirement: AC-32 — der Schritt ändert Bau und Heartbeat nicht
  Conflict: nur theoretisch; FR_SEITEN wird im selben Lauf beschrieben (der Bau scheiterte vorher), praktisch nicht erreichbar.
  Remediation: `|| return 0` ergänzen.

Confirmation:
  AC: AC-32
  Code reference: betrieb/veroeffentlichen.sh:873
  Evidence: Archivordner nicht anlegbar, Ablage (891) und Merker (899) scheitern ohne Abbruch; test_altbau_archivordner_nicht_anlegbar_haelt_den_lauf_nicht_auf (engine/tests/test_rueckbau_557.py:567) prüft Bau, Ping, Warnzeile, _bau erhalten, kein Merker; grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-28
  Code reference: engine/tests/test_rueckbau_557.py:490
  Evidence: test_altbau_archivfehler_loescht_nichts grün; die neuen Zweige (873, 891) kehren vor dem Löschen zurück.
  Status: CONFIRMED

Confirmation:
  AC: AC-30
  Code reference: engine/tests/test_rueckbau_557.py:529
  Evidence: Idempotenz-Test grün; Merker (899) wird atomar über .neu geschrieben, Fehler entfernt .neu.
  Status: CONFIRMED

Confirmation:
  AC: AC-31
  Code reference: engine/tests/test_rueckbau_557.py:542
  Evidence: Kein Alarmaufruf in den neuen Zweigen, nur altbau_warnen (entprellt, 815); Test grün.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Runde 3: Nachbesserung zu AC-32 hält; nur LOW-Hinweis F005 (cd-Zuweisung, praktisch nicht erreichbar). Frühere Hinweise F001 bis F004 unverändert, keine blockierend.
Tests: 42 passed, 0 failed, 0 übersprungen (test_rueckbau_557.py, Runde 3); frühere volle Suite 3354 passed.

## Geprüfte Dateien

- sha256:60cafd6b9387cff52434f0b2fdc0b39a9db91420949a0eeb7711727f09b38411  betrieb/deploy.sh
- sha256:d81656e0bbc9e4e4592ee33108f4a8b039274ef81dea7d2082d8d20e88e5689b  betrieb/einrichten.sh
- sha256:b7841e7db828f05dc0348ca5f352014dfba2d79e94b7a62e239d262629d84575  betrieb/gemeinsam.sh
- sha256:4e1f89b5b67b061d7ad9a40f8ab6624e1049d3d85f33a29b9d587cd91590adf2  betrieb/veroeffentlichen.sh
- sha256:9f34696004c60711be0410cb5b1ef2ee8ff96f23f17dab44c7d4acc50f613d70  engine/instanz.py
- sha256:876c079b5605daba9a3f8a80c58cff211b75474c319bfca9c13d0e7e2a307370  engine/neu.py
- sha256:3a3f84e7034658c4039c702766bd34382d18b92e5ae9b62fb455b90004e20768  engine/reisespeicher.py
- sha256:da4fa1c239274e0ed3eaeaa84e359aa496a4a65966a5bbb3aee9766e521fe9b3  engine/rueckmeldungen.py
- sha256:0cf1a84dd3ccd8f5175755cc09825b0b150bc959576676aacde532cdca8ee43e  engine/schreiben.py
- sha256:5533970ec038bb07aecd202f13586d45e2023206227873e03dfd3d96daa19c34  engine/stand.py
- sha256:b005e9f16666330fa2a61039a551ec75488e0f1cad714dc50932b02331467334  engine/tests/test_rueckbau_557.py
- sha256:15a45506dcd3f9bd195ca6167cd842347c2ee5d5d7870a8b6a94bc176a105b93  engine/texte_de.py
- sha256:3830c03ef2f8c68bc404c6ae6435af4b37d9153ef0843172630382a41a2c69b0  engine/texte_en.py

## Prüfbasis

- base: 2f45a52e29e98c1ac0aff8b1fd90565910f89a40
- blob:ace32154fca297906df36163e1e400b7605f0789  betrieb/deploy.sh
- blob:7015dd8822df2afbfebb152b9238a41c75a3804f  betrieb/einrichten.sh
- blob:4385e382e8bdcdb423dddf21ca4a0a44652e1d23  betrieb/gemeinsam.sh
- blob:0351c383bbfdd27c6d5eb37b490a5b59cc2d5b9b  betrieb/veroeffentlichen.sh
- blob:38d1dff54af8abad0c227c560c41ae89dd09d484  engine/instanz.py
- blob:1e15d408a090c5e0cfa43ac2f2b9f67a68b28201  engine/neu.py
- blob:aceeb80dbb4219cf049df688688d14347ab65f74  engine/reisespeicher.py
- blob:45f30bf27edad443e01b6e9d0d9731f552e1ea18  engine/rueckmeldungen.py
- blob:e10c5b02f79af9b5b2972a6cfb25b5f020f6a96d  engine/schreiben.py
- blob:751ffa18219d54c1a0e212afed943947b711b790  engine/stand.py
- blob:4a76d6916d9f0f81261ada93a4129bce85ee657f  engine/tests/test_rueckbau_557.py
- blob:5927ee7c9bb5ddae32a163c4f08addd22c66e70e  engine/texte_de.py
- blob:da1160222f2db897f318c944e0872dcb88bede73  engine/texte_en.py

## Geprüfte Dateien

- sha256:60cafd6b9387cff52434f0b2fdc0b39a9db91420949a0eeb7711727f09b38411  betrieb/deploy.sh
- sha256:d81656e0bbc9e4e4592ee33108f4a8b039274ef81dea7d2082d8d20e88e5689b  betrieb/einrichten.sh
- sha256:b7841e7db828f05dc0348ca5f352014dfba2d79e94b7a62e239d262629d84575  betrieb/gemeinsam.sh
- sha256:0a915cda7ce12ed384ffc14d54322a1c32670f7c1e3257cf8ad8ba943ffbf7dc  betrieb/veroeffentlichen.sh
- sha256:9f34696004c60711be0410cb5b1ef2ee8ff96f23f17dab44c7d4acc50f613d70  engine/instanz.py
- sha256:876c079b5605daba9a3f8a80c58cff211b75474c319bfca9c13d0e7e2a307370  engine/neu.py
- sha256:3a3f84e7034658c4039c702766bd34382d18b92e5ae9b62fb455b90004e20768  engine/reisespeicher.py
- sha256:da4fa1c239274e0ed3eaeaa84e359aa496a4a65966a5bbb3aee9766e521fe9b3  engine/rueckmeldungen.py
- sha256:0cf1a84dd3ccd8f5175755cc09825b0b150bc959576676aacde532cdca8ee43e  engine/schreiben.py
- sha256:5533970ec038bb07aecd202f13586d45e2023206227873e03dfd3d96daa19c34  engine/stand.py
- sha256:3e8646755a52d94d3d11035ccd2e4a5b97f712380bb283683a7b42b9c070f635  engine/tests/test_rueckbau_557.py
- sha256:15a45506dcd3f9bd195ca6167cd842347c2ee5d5d7870a8b6a94bc176a105b93  engine/texte_de.py
- sha256:3830c03ef2f8c68bc404c6ae6435af4b37d9153ef0843172630382a41a2c69b0  engine/texte_en.py

## Prüfbasis

- base: 2f45a52e29e98c1ac0aff8b1fd90565910f89a40
- blob:ace32154fca297906df36163e1e400b7605f0789  betrieb/deploy.sh
- blob:7015dd8822df2afbfebb152b9238a41c75a3804f  betrieb/einrichten.sh
- blob:4385e382e8bdcdb423dddf21ca4a0a44652e1d23  betrieb/gemeinsam.sh
- blob:f16b64d6a57c92baebcf2d45de930632dd3935af  betrieb/veroeffentlichen.sh
- blob:38d1dff54af8abad0c227c560c41ae89dd09d484  engine/instanz.py
- blob:1e15d408a090c5e0cfa43ac2f2b9f67a68b28201  engine/neu.py
- blob:aceeb80dbb4219cf049df688688d14347ab65f74  engine/reisespeicher.py
- blob:45f30bf27edad443e01b6e9d0d9731f552e1ea18  engine/rueckmeldungen.py
- blob:e10c5b02f79af9b5b2972a6cfb25b5f020f6a96d  engine/schreiben.py
- blob:751ffa18219d54c1a0e212afed943947b711b790  engine/stand.py
- blob:0c79335b6f1da1d32cb591f6e2f74ed795d4f6e0  engine/tests/test_rueckbau_557.py
- blob:5927ee7c9bb5ddae32a163c4f08addd22c66e70e  engine/texte_de.py
- blob:da1160222f2db897f318c944e0872dcb88bede73  engine/texte_en.py
