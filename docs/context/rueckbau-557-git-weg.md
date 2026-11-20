# Context: rueckbau-557-git-weg

## Request Summary
Rückbau des alten Git-Wegs nach dem Umzug auf den Software-Klon (#454): Code, Skripte, Workflow „Software nachziehen“, alte Anordnung mit Submodul `frieda/`, Arbeitskopien `-schreiben-*`, Rückweg-Doku; dazu auf dem Server den alten Bauordner entfernen und das alte Reisen-Repo der ersten Instanz archivieren. **Entscheidung PO 20.11.2026: jetzt vollständig, nicht erst nach der Beobachtungszeit bis 27.11.** (Kommentar in #557).

## Lage auf dem Server (20.11.2026)
- Alle Units laufen mit `FR_WURZEL=<FR_SEITEN>/_software`, `FR_DIENST=<FR_SEITEN>/_dienst`; Umzugszustand `umzug-454 = fertig` seit 13.11.
- Alle 10 Reisen sind Speicherreisen (`reisespeicher.py speicherreisen` listet alle zehn); keine Reise liegt mehr in Git.
- Alter Bauordner `<FR_SEITEN>/_bau` (Reisen-Repo mit Submodul) und zehn `_bau-schreiben-<reise>` liegen noch.
- `<FR_DIENST>/instanz/einstellungen.env` existiert (enthält noch `FR_SPEICHERREISEN`, wirkungslos, und Kommentare mit `frieda/`).
- Instanz-Tests liegen unter `<FR_DIENST>/instanz/tests` (nicht im Reisen-Repo).
- Reisen-Repo der Instanz: Workflow `software-nachziehen.yml` scheitert seit 17.11. (Runner „No space left“) – zuerst Zeitplan abschalten (Kommentar PO 19.11.).
- henemm-infra `scripts/monitor.sh`: `FRIEDA_SOFTWARE_HEAD` (~281, `_bau/.git/modules/frieda/HEAD`), `frieda_umgezogen`/`frieda_software_ordner` (~449–477) mit Zweig für die alte Anordnung; Kommentare zu „Software nachziehen“ (~275), Meldetext mit `_bau` (~1929).

## Related Files (Bestandsaufnahme, Explore 20.11.)

### Noch lebendige Abhängigkeiten (vor dem Löschen umbauen)
- (A) `engine/reisespeicher.py:689-711` `_git_baum` (nutzt `stand_git.git`) → `umschaltung_frei` (713) → `speicherreisen` (760-769) → `instanz.speicherreisen`. Läuft auch im Klon (`_software/.git` existiert), Ergebnis „nichts da“.
- (B) `engine/schreiben.py:6262-6268` `/gesund`: ruft `schreiben_git.gesund`, wenn `wurzel/.git` existiert – trifft im Klon zu.
- (C) `FR_SCHREIBKOPIE` trägt auch den Exportordner des Speicherwegs (`schreiben.py:6099`, `schreibkopie()` 222-224, 6340; `Schreiber.arbeit` 5483, `anwenden_im_ordner` 5564-5612; Sperrdatei `…-schreiben-<reise>.lock` 5765 bleibt).

### schreiben_git / stand_git
- Aufrufer in `engine/schreiben.py`: 5497 vorbereiten, 5550 verwerfen (basis None), 5622 schreiben, 5641 buchung_im_repo (do_GET 6292), 5781 vorgang_eingetragen, 5987 anwenden_extern else, 6216 `_export_repo`, 6262 /gesund, 6347 CLI vorbereiten, 6356 Re-Import-Kommentar, 6017 `git_reisen()` (6058).
- `engine/stand.py:41,114` (`nummer`, `aenderungen`; Git-Zweig von `fuer_seite` 151-163, aus `bauen.py:1538`).
- `engine/reisespeicher.py:813-866` `umschalten_automatisch` (CLI `umschalten` 1358), `umschaltung_frei` mit Stempel `<FR_DIENST>/vergleich/<reise>.json` (733-753), CLI `umschaltung` 1371 (aus veroeffentlichen.sh:352).
- `betrieb/deploy.sh:26,33,35` Modullisten; `:36-44` Bau aus `$WURZEL/reisen` für Nicht-Speicherreisen.
- konnektor.py: keine direkte Abhängigkeit.

### Skripte
- `betrieb/vergleichslauf.sh` (kein Aufrufer), `betrieb/software-nachziehen.sh` + `.yml` (Vorlage fürs Reisen-Repo), `betrieb/messlauf-schreibweg.py` (`--weg git`).
- `betrieb/veroeffentlichen.sh`: alter `main()` ab ~1180, `reisen_des_laufs` 224, `ci_nachweis` 516, `anstoss_weitergeben` 553, `software_anstossen` 568, `git_reisen_uebrig` 602, `git_reisen_umschalten` 688, `umzug_*` 1015-1135, Übergabe an Klon 1175; Köpfe 20-83. Behalten/anpassen: `main_klon` (900-1013), `software_klon` 719, `software_kennung` 246, `umzug_fertig_im_klon` 1111, `speicher_reisen_lauf` 318/352, `speicher_rot_melden` 1350, `pruefen_lauf` 533, `anstoss_lauf` 722.
- `betrieb/gemeinsam.sh`: 3-10 Kopf, 37-44 FR_WURZEL-Rückfall über Superprojekt, 46 `fr_alte_anordnung`, 57 Meldung `nur_bauordner` mit `frieda/`, 87-96 einstellungen.env-Rückfall, 112/137 FR_SCHREIBKOPIE, 115-119 FR_PYTHON-Rückfall, 128/139/146 FR_SPEICHERREISEN, 138/184-187 FR_NACHZIEHEN_*.
- `betrieb/einrichten.sh:41-48` Zweig alte Anordnung; `betrieb/vorlagen/schreiben.service:5,11,56` `ReadWritePaths=-__WURZEL__-schreiben`.
- `betrieb/einstellungen.beispiel:54-55,70-72`; `.github/workflows/tests.yml:124,128`.
- `engine/instanz.py:4,15,21-22,47-55,152`; `engine/schreiben.py:27,5465-5473` (`veroeffentlichen_skript` mit `.gitmodules`).
- Usage-Texte: `werkzeuge/karte-holen.sh:7-9,78`, `betrieb/sichern.sh:9`.

### Tests
- Ganz: `engine/tests/test_software_nachziehen.py`.
- `test_betrieb.py`: Fixture `vf` (179) baut eine Reisen-Repo-Anordnung und läuft durch den alten `main()` – rund 86 Tests über `vf`/`an`/`sp`; außerdem 55-75, 97-120, 547-680, 1564-1602 (Modullisten, `instanz`-Fixture mit Submodul), 2121-2156, 2331, 3005, 3106. Abhängige Dateien prüfen: `test_playwright_tmp_628.py`, `test_nginx_baustein_loeschen_527.py`, `test_vorgemerkte_durchlauf_529.py`, `test_texte.py`.
- `test_software_weg_454.py`: Fixture `alt` (630) und Umzug/Rückweg-Tests (690-845, 1082, 1145), Lieferung-1-Tests 169-267, 1103, 1118, 512.
- `test_speicher_stufe5.py` 148-340, 479-621, 671-719; `test_speicher_stufe3.py:243`; `test_export.py` 189, 232, 285, 298; `test_schreiben_speicher.py` 140-218, 355, 371, 614-626, 696; `test_stand.py` 49-133; `test_anstoss_pfad_570.py:43,52`; Dummy-FR_SCHREIBKOPIE in `test_schreiben.py:52,61`, `test_schreiben_speicher.py:78,269`, `test_speicher_stufe5.py:73,495`, `test_software_weg_454.py:82`.

### Doku
- `docs/betrieb.md`: 3-39, 77, 96-121, 156-186, 267-289, 312-356, 370-376, 404-418, 609-641.
- `docs/adr/0009-reisespeicher.md:36,45-50`, `CLAUDE.md:49` (Regel nennt Workflow „Software nachziehen“), `openspec.yaml:3`, `engine/rueckmeldungen.py:65`, Spec `docs/specs/betrieb/software-weg-454.md:79,290-299`.
- Historische Specs/Kontexte/Artefakte bleiben unverändert (Geschichte).

## Existing Patterns
- Formatwechsel bringen ihre Umstellung in `neu.py nachziehen` mit (#250); Betriebswechsel ohne Handschritt: Veröffentlichen erledigt Umstellungen selbst (Muster: `umzug_454`, Entfernen nginx-Baustein #527).
- Vorgaben der Instanz aus `<FR_DIENST>/instanz/einstellungen.env`; nichts Instanzspezifisches in Engine/betrieb.
- Deploy-Modullisten in `betrieb/deploy.sh` mit Test.

## Dependencies
- Upstream: Software-Klon `_software` (fetch, CI-Nachweis per Commit), Reisespeicher.
- Downstream: Units der Instanz (schreiben.service Sandbox), henemm-infra monitor.sh, Instanz-Tests unter `<FR_DIENST>/instanz/tests`, Reisen-Repo-Workflows.

## Risks & Considerations
- Kein Rückweg mehr nach dem Rückbau (PO-Entscheidung bewusst). Vor dem Entfernen von `_bau`: Sicherung (Archiv); Daten sind im Reisespeicher und im Reisen-Repo auf GitHub (archiviert, nicht gelöscht).
- Sehr großer Umfang (Code, 100+ Tests, Doku, Server, Infra-Repo, Reisen-Repo) → in Lieferungen schneiden.
- `schreiben.service`-Sandbox: `ReadWritePaths` ändern verlangt Neuerzeugen der Units (über Veröffentlichen/Einrichten), sonst Handschritt.
- Monitor in henemm-infra muss vor dem Löschen von `_bau` umgestellt sein, sonst Fehlalarm.
- Tests der einbindenden Instanz mit dem Branch laufen lassen (Meldungstexte/Umgebungswerte ändern sich).

## Analysis

### Type
Feature (Rückbau/Aufräumen nach #454; PO-Entscheidung 20.11.2026: jetzt vollständig, kein Rückweg)

### Geprüfte Befunde
- `/gesund` (`engine/schreiben.py:6262-6268`): Bedingung `not liste or (wurzel/.git).exists()` ist im Software-Klon wahr → prüft heute `schreiben_git.gesund` gegen das Software-Repo statt einer Reisen-Ablage. Git-Teil ersatzlos streichen; `speicher_gesund()` und `EinstellungenNichtLesbar`→503 (#361) bleiben.
- `reisespeicher._git_baum` (689) läuft im Klon und liefert „nichts“ → alle Reisen frei. `umschaltung_frei`, Stempel `<FR_DIENST>/vergleich/`, `umschalten_automatisch` (813-866), `git_stand_nachtragen` werden überflüssig. `speicherreisen()` = jede Reise mit Vorgang (heutige Wirkung).
- Sperrdatei liegt unter `FR_SPERREN`/`FR_DIENST` (schreiben.py:5762-5765), nicht neben der Wurzel – vom Rückbau unberührt.
- Reise ohne Speichereintrag: `vorgang_speicher` kennt den Fall schon (503 `reise_nicht_im_speicher`); neue Reisen legen den Speicher an (basis=0). Git-Zweig in `dienst()` (~5987) entfällt; Text `umschaltung_nicht_freigegeben` entfällt in allen Sprachen.
- `FR_SCHREIBKOPIE`: wird von `vorgang_speicher` intern an den Unterprozess gesetzt (6099, temp-Ordner). Name behalten als interne Übergabe, Standardwert `<wurzel>-schreiben` und gemeinsam.sh:112/137 streichen.
- `schreiben.service` `ReadWritePaths=-__WURZEL__-schreiben`: `-` macht fehlenden Pfad harmlos; Zeile entfernen, Units werden über Veröffentlichen/`units.py` neu erzeugt (kein Handschritt).
- `FR_SPEICHERREISEN`-Zeile in `<FR_DIENST>/instanz/einstellungen.env` ist wirkungslos; Software ignoriert sie → liegen lassen, kein Handschritt.
- Konnektor, Rückmeldedienst, Push: keine Abhängigkeit.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/schreiben_git.py, engine/stand_git.py | DELETE | Git-Weg |
| engine/schreiben.py | MODIFY | Schreiber nur Speicherweg (basis immer gesetzt), /gesund ohne Git, `buchung_im_repo`, `git_reisen`, `_export_repo`, CLI `vorbereiten`, `veroeffentlichen_skript` ohne `.gitmodules`-Zweig |
| engine/reisespeicher.py | MODIFY | `_git_baum`, `umschaltung_frei`, Stempel, `umschalten_automatisch`, `git_stand_nachtragen`, CLI `umschalten`/`umschaltung` raus; `speicherreisen` ohne Filter |
| engine/stand.py | MODIFY | Git-Zweig von `fuer_seite`, `nummer`, `aenderungen` raus |
| engine/instanz.py | MODIFY | `FR_SPEICHERREISEN`, Superprojekt-/`frieda/`-Kommentare und Rückfälle |
| engine/texte_*.py, engine/rueckmeldungen.py:65 | MODIFY | entfallene Meldungen/Kommentare |
| betrieb/deploy.sh | MODIFY | Modullisten (26-35), Bau aus `$WURZEL/reisen` (36-44) |
| betrieb/veroeffentlichen.sh | MODIFY | alter `main()`, `umzug_*` (außer `umzug_fertig_im_klon`), `reisen_des_laufs`, `ci_nachweis`, `anstoss_weitergeben`, `software_anstossen`, `git_reisen_uebrig`, `git_reisen_umschalten`, Übergabe an Klon; neu `altbau_entfernen` (L3) |
| betrieb/gemeinsam.sh, betrieb/einrichten.sh | MODIFY | alte Anordnung, `nur_bauordner`, FR_SCHREIBKOPIE/FR_SPEICHERREISEN/FR_NACHZIEHEN_* |
| betrieb/vorlagen/schreiben.service | MODIFY | `ReadWritePaths=-__WURZEL__-schreiben` |
| betrieb/einstellungen.beispiel, .github/workflows/tests.yml | MODIFY | entfallene Werte |
| betrieb/software-nachziehen.sh/.yml, betrieb/vergleichslauf.sh, betrieb/messlauf-schreibweg.py | DELETE | Git-Weg-Werkzeuge |
| werkzeuge/karte-holen.sh, betrieb/sichern.sh | MODIFY | Usage-Texte ohne `frieda/` |
| engine/tests/test_software_nachziehen.py | DELETE | |
| engine/tests/test_betrieb.py | MODIFY | Fixture `vf` (alter main) ersetzen/auf `main_klon` umstellen, Modullisten, Units |
| engine/tests/test_software_weg_454.py, test_speicher_stufe5.py, test_speicher_stufe3.py, test_export.py, test_schreiben_speicher.py, test_stand.py, test_anstoss_pfad_570.py, test_schreiben.py, test_texte.py | MODIFY | Git-Fälle raus, fail-closed-Fälle (#361) behalten |
| docs/betrieb.md, docs/adr/0009-reisespeicher.md, CLAUDE.md:49, openspec.yaml:3, docs/specs/betrieb/software-weg-454.md | MODIFY | Ist-Zustand ohne Git-Weg und ohne Rückweg |
| extern henemm-infra scripts/monitor.sh | MODIFY | `FRIEDA_SOFTWARE_HEAD`, alte Anordnung, Meldetext `_bau` → Klon |
| extern Reisen-Repo der Instanz | MODIFY/ARCHIVE | Zeitplan „Software nachziehen“ abschalten, danach archivieren |

### Scope Assessment
- Files: ~35 (davon ~8 gelöscht), dazu 2 externe Repos
- Estimated LoC: ca. +700 / −6000 (Löwenanteil Tests)
- Risk Level: MEDIUM (zentrale Pfade Schreibweg/Veröffentlichen; unumkehrbares Löschen auf dem Server, aber Daten liegen im Reisespeicher, auf GitHub und im Archiv)

### Technical Approach (Empfehlung Plan-Bewertung, übernommen)
Schnitt in Lieferungen, jede einzeln mit grüner CI auslieferbar:
0. **Vorab extern:** Zeitplan des Workflows „Software nachziehen“ im Reisen-Repo der Instanz abschalten; henemm-infra `monitor.sh` auf den Klon `_software` umstellen und ausrollen (Issue in henemm-infra). Danach ist `_bau` für die Überwachung unkritisch.
1. **L1 Engine ohne Git-Weg:** schreiben.py, reisespeicher.py, stand.py, instanz.py, Löschen `schreiben_git.py`/`stand_git.py`, `/gesund`, deploy.sh-Listen, Engine-Tests. Muss die Aufrufe `reisespeicher.py umschaltung/umschalten` in veroeffentlichen.sh (352, 1371, `git_reisen_umschalten` 688) mitnehmen, sonst bricht der Lauf.
2. **L2 Betriebsskripte:** alter `main()` samt Umzugs-/Git-Funktionen, gemeinsam.sh, einrichten.sh, Vorlagen, Löschen der Git-Weg-Skripte, tests.yml, Umbau test_betrieb (`vf`). Noch kein Löschen auf dem Server.
3. **L3 Server-Aufräumen:** Schritt `altbau_entfernen` in `main_klon` (Muster #527): nur wenn `umzug-454 = fertig`, Units zeigen auf den Klon und jede Reise aus `_bau/reisen` Speicherreise ist; vorher Archiv von `_bau` (ohne `-schreiben-*`) nach `<FR_DIENST>/archiv/` mit Platzprüfung; dann `_bau` und `_bau-schreiben-*` entfernen (Pfadprüfung innerhalb `FR_SEITEN`), Merker `<FR_DIENST>/altbau-557` für Idempotenz; Fehler nur als Warnzeile, kein Alarm. Erst nach Monitor-Umstellung.
4. **L4 Doku:** betrieb.md (Rückweg-Abschnitte raus), ADR-0009, CLAUDE.md:49, Spec 454, openspec.yaml; nach L3 in main.
5. **Danach extern:** Reisen-Repo der Instanz archivieren (nicht löschen).
Vor jedem Vorspulen: Tests der Instanz (`<FR_DIENST>/instanz/tests`) mit dem Branch laufen lassen.

### Dependencies
- Monitor-Umstellung (henemm-infra) vor L3.
- L1 vor L2 (L2 baut auf entfernten Engine-CLIs auf).
- Der laufende Veröffentlichen-Lauf aktualisiert sich selbst aus dem Klon; neuer Code wirkt ab dem Folgelauf. `umzug_neustart`/`software_klon` dürfen nicht beschädigt werden.

### Befunde gegen den Plan
- L1 allein würde veroeffentlichen.sh brechen → Aufrufe gehen in L1 mit (gelöst).
- Kein Rückweg nach L3 – bewusste PO-Entscheidung (Kommentar #557, 20.11.).
- Sonst keine.

### Open Questions
- keine Produktfragen offen (Entscheidung „jetzt vollständig“ liegt vor; alles Weitere technisch).
