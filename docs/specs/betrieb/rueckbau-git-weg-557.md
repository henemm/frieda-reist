---
entity_id: rueckbau-git-weg-557
type: refactor
created: 2026-11-20
updated: 2026-11-20
status: draft
workflow: rueckbau-557-git-weg
version: "1.0"
tags: [rueckbau, git-weg, veroeffentlichen, reisespeicher, betrieb, epic-345]
---

# Rückbau des Git-Wegs nach dem Umzug auf den Software-Klon (#557)

Folge von #454. Grundlage: `docs/context/rueckbau-557-git-weg.md` (Bestandsaufnahme, Analyse, Lieferungsschnitt), `docs/specs/betrieb/software-weg-454.md` (Vorgänger, dort als „Folge-Issue Rückbau“ ausgelagert), `docs/specs/betrieb/nginx-baustein-loeschen-527.md` (Muster: Veröffentlichen entfernt Altlast selbst), ADR-0009, ADR-0001.

## Approval

- [ ] Approved

(Keine Produktentscheidung offen. Der Product Owner hat am 20.11.2026 im Issue entschieden: Rückbau jetzt vollständig, kein Rückweg mehr, nicht erst nach der Beobachtungszeit bis 27.11. Alles Weitere ist technisch und unten begründet.)

## Purpose

Seit dem Umzug (#454, Zustand `umzug-454 = fertig`) laufen alle Units aus dem Software-Klon, und alle Reisen der Instanz sind Speicherreisen. Der alte Git-Weg (Reisen-Repo mit Submodul, Arbeitskopien `-schreiben-*`, Workflow „Software nachziehen“, Umschaltung Git nach Speicher, Rückweg) wird nicht mehr gebraucht, hält aber Code, über hundert Tests, Skripte und Doku am Leben und führt zu Fehlverhalten (die Gesundheitsprüfung prüft heute den Software-Klon als wäre er eine Reisen-Ablage).

Ziel: Der Git-Weg verschwindet vollständig aus Software, Betrieb, Tests und Doku. Auf dem Server räumt der Lauf des Veröffentlichens den alten Bauordner selbst auf (nach einem Archiv, ohne Handschritt, #250). Das alte Reisen-Repo der Instanz wird archiviert, nicht gelöscht. Es gibt bewusst keinen Rückweg mehr; die Daten bleiben im Reisespeicher, im Archiv und im archivierten Reisen-Repo auf GitHub erhalten.

## Source

- **File:** `engine/schreiben.py`, `engine/reisespeicher.py`, `engine/stand.py`, `engine/instanz.py`, `engine/texte_<sprache>.py`, `engine/rueckmeldungen.py`, `betrieb/veroeffentlichen.sh`, `betrieb/gemeinsam.sh`, `betrieb/einrichten.sh`, `betrieb/deploy.sh`, `betrieb/vorlagen/schreiben.service`, `betrieb/einstellungen.beispiel`, `.github/workflows/tests.yml`, Usage-Texte in `werkzeuge/` und `betrieb/sichern.sh`, `docs/betrieb.md`, `docs/adr/0009-reisespeicher.md`, `CLAUDE.md`, `openspec.yaml`
- **Identifier (neu):** Schritt `altbau_entfernen` in `main_klon` von `betrieb/veroeffentlichen.sh`, Merker `<FR_DIENST>/altbau-557`, Archiv unter `<FR_DIENST>/archiv/`; neue Testdatei `engine/tests/test_rueckbau_557.py`
- **Identifier (entfallen):** `schreiben_git`, `stand_git`, `reisespeicher._git_baum`, `umschaltung_frei`, `umschalten_automatisch`, `git_stand_nachtragen`, `vergleichslauf.sh`, `software-nachziehen.sh/.yml`, `messlauf-schreibweg.py`, alter `main()` und `umzug_*` in `veroeffentlichen.sh`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/reisespeicher.py` (`speicherreisen`) | Modul | Bleibt einziger Weg für Reiseinhalte; verliert `_git_baum`, `umschaltung_frei`, `git_stand_nachtragen`, `umschalten_automatisch` |
| `engine/instanz.py` (`speicherreisen`, `EinstellungenNichtLesbar`) | Modul | Liste der Speicherreisen ohne Filter; fail closed (#361) bleibt |
| `engine/schreiben.py` (`Schreiber`, `/gesund`, `speicher_gesund`, `vorgang_speicher`, `FR_SCHREIBKOPIE` als interne Übergabe) | Modul | Schreibweg nur noch über den Speicher |
| `engine/stand.py`, `engine/bauen.py` (Aufruf `fuer_seite`) | Module | Stand der Seite ohne Git-Zweig |
| `betrieb/veroeffentlichen.sh` (`main_klon`, `software_klon`, `software_kennung`, `umzug_fertig_im_klon`, `speicher_reisen_lauf`, `speicher_rot_melden`, `pruefen_lauf`, `anstoss_lauf`) | Skript | Behalten; alter `main()` und Git-Funktionen entfallen |
| `betrieb/gemeinsam.sh`, `betrieb/einrichten.sh`, `betrieb/deploy.sh`, `betrieb/units.py`, `betrieb/vorlagen/schreiben.service` | Skripte, Vorlage | Alte Anordnung und Rückfälle entfallen; Units werden über Veröffentlichen/Einrichten neu erzeugt |
| `engine/tests/test_betrieb.py` (Fixture `vf`), `test_software_weg_454.py`, `test_speicher_stufe5.py`, `test_speicher_stufe3.py`, `test_export.py`, `test_schreiben_speicher.py`, `test_stand.py`, `test_anstoss_pfad_570.py`, `test_schreiben.py`, `test_texte.py` | Tests | Git-Fälle entfallen, fail-closed-Fälle bleiben |
| **Infrastruktur-Repo der Instanz (anderes Repo):** `scripts/monitor.sh` | Fremd-Repo | Vorbedingung von L3: Überwachung auf den Klon umgestellt, sonst Fehlalarm |
| **Reisen-Repo der Instanz (anderes Repo):** Zeitplan „Software nachziehen“ | Fremd-Repo | Vorbedingung von L1: Zeitplan abgeschaltet; danach Archivierung |
| Tests der Instanz unter `<FR_DIENST>/instanz/tests` | Instanz-Tests | Laufen vor jedem Vorspulen mit dem Branch |

## Scope

### Im Scope

Fünf Lieferungen plus eine externe Vorstufe, jede einzeln mit grüner CI auslieferbar, in dieser Reihenfolge:

- **L0 (extern, vor allem anderen):** Zeitplan des Workflows „Software nachziehen“ im Reisen-Repo der Instanz abschalten (er scheitert seit 17.11. an „No space left“); Überwachung in der Infrastruktur auf den Klon umstellen und ausrollen (Issue im Infrastruktur-Repo, vom Tech Lead selbst umgesetzt und in #557 verlinkt).
- **L1 (Engine ohne Git-Weg):** `schreiben_git.py` und `stand_git.py` gelöscht; Schreiber nur Speicherweg; `/gesund` ohne Git-Teil; `speicherreisen()` ohne Filter; `umschaltung`/`umschalten`-Aufrufe in `veroeffentlichen.sh` mitgenommen (sonst bricht der Lauf); `deploy.sh`-Modullisten; Texte und Tests.
- **L2 (Betriebsskripte):** alter `main()` und alle Umzugs-/Git-Funktionen aus `veroeffentlichen.sh`, alte Anordnung aus `gemeinsam.sh` und `einrichten.sh`, `ReadWritePaths` der Vorlage, Löschen der Git-Weg-Werkzeuge, `tests.yml`, Umbau des Fixtures `vf`. Noch nichts auf dem Server löschen.
- **L3 (Server-Aufräumen):** Schritt `altbau_entfernen` im Lauf (Muster #527), erst nach L0.
- **L4 (Doku):** `docs/betrieb.md`, ADR-0009, `CLAUDE.md`, `openspec.yaml`, Spec 454; nach L3 in `main`.
- **Danach (extern):** Reisen-Repo der Instanz archivieren (nicht löschen).

### Nicht im Scope (Out of Scope)

- Historische Specs, Kontexte und Artefakte (`docs/specs/` außer Spec 454 und dieser, `docs/context/`, `docs/artifacts/`) bleiben unverändert; sie sind Geschichte. Spec 454 bekommt nur einen Hinweis im Kopf und im Changelog, dass der Rückweg entfallen ist.
- Keine echten Reisen, keine Serveradressen, keine Instanznamen in Specs, Tests oder Doku: Platzhalter wie `<FR_SEITEN>`, `<FR_DIENST>`, `<Reise A>`; Tests nutzen nur die beiden Beispielreisen und erfundene Daten.
- Kein neuer Mechanismus für Units: bestehendes Root-Hilfsprogramm mit unveränderter Erlaubnisliste.
- Keine Änderung am Konnektor, an Rückmeldedienst, Push, Seite oder Service Worker (keine Abhängigkeit vom Git-Weg, Befund der Analyse).
- Löschen des Reisen-Repos auf GitHub (nur archivieren).
- Der Wert `FR_SPEICHERREISEN` in `<FR_DIENST>/instanz/einstellungen.env` wird nicht von Hand entfernt: wirkungslos, bleibt liegen (siehe AC-11).

### Affected Files

| File | Change Type | Lieferung | Description |
|------|-------------|-----------|-------------|
| `engine/schreiben_git.py`, `engine/stand_git.py` | DELETE | L1 | Git-Weg |
| `engine/schreiben.py` | MODIFY | L1 | Schreiber nur Speicherweg, `/gesund` ohne Git, `buchung_im_repo`, `git_reisen`, `_export_repo`, CLI `vorbereiten`, `veroeffentlichen_skript` ohne `.gitmodules`-Zweig |
| `engine/reisespeicher.py` | MODIFY | L1 | `_git_baum`, `umschaltung_frei`, Stempel, `umschalten_automatisch`, `git_stand_nachtragen`, CLI `umschalten`/`umschaltung` raus; `speicherreisen` ohne Filter |
| `engine/stand.py` | MODIFY | L1 | Git-Zweig von `fuer_seite`, `nummer`, `aenderungen` raus |
| `engine/instanz.py` | MODIFY | L1 | `FR_SPEICHERREISEN` und Superprojekt-/`frieda/`-Rückfälle raus |
| `engine/texte_*.py`, `engine/rueckmeldungen.py` | MODIFY | L1 | entfallene Meldungen (`umschaltung_nicht_freigegeben` u. a.) und Kommentare |
| `betrieb/deploy.sh` | MODIFY | L1 | Modullisten ohne gelöschte Module; kein Bau aus `$WURZEL/reisen` |
| `betrieb/veroeffentlichen.sh` | MODIFY | L1, L2, L3 | alter `main()`, `umzug_*`, `reisen_des_laufs`, `ci_nachweis`, `anstoss_weitergeben`, `software_anstossen`, `git_reisen_uebrig`, `git_reisen_umschalten`, Übergabe an Klon raus; neu `altbau_entfernen` |
| `betrieb/gemeinsam.sh`, `betrieb/einrichten.sh` | MODIFY | L2 | alte Anordnung, `nur_bauordner`, `FR_SCHREIBKOPIE`, `FR_SPEICHERREISEN`, `FR_NACHZIEHEN_*` |
| `betrieb/vorlagen/schreiben.service` | MODIFY | L2 | `ReadWritePaths=-__WURZEL__-schreiben` entfällt |
| `betrieb/einstellungen.beispiel`, `.github/workflows/tests.yml` | MODIFY | L2 | entfallene Werte |
| `betrieb/software-nachziehen.sh`, `.yml`, `betrieb/vergleichslauf.sh`, `betrieb/messlauf-schreibweg.py` | DELETE | L2 | Git-Weg-Werkzeuge |
| `werkzeuge/karte-holen.sh`, `betrieb/sichern.sh` | MODIFY | L2 | Usage-Texte ohne `frieda/` |
| `engine/tests/test_software_nachziehen.py` | DELETE | L1/L2 | ganze Datei |
| `engine/tests/test_rueckbau_557.py` | CREATE | L1–L3 | Nachweistests dieser Spec |
| übrige Tests (siehe Test Plan) | MODIFY | L1, L2 | Git-Fälle raus |
| `docs/betrieb.md`, `docs/adr/0009-reisespeicher.md`, `CLAUDE.md`, `openspec.yaml`, `docs/specs/betrieb/software-weg-454.md` | MODIFY | L4 | Ist-Zustand ohne Git-Weg und Rückweg |
| extern: Infrastruktur-Repo `scripts/monitor.sh` | MODIFY | L0 | Überwachung auf den Klon |
| extern: Reisen-Repo der Instanz | MODIFY/ARCHIVE | L0, danach | Zeitplan aus; dann archivieren |

### Estimated Changes

- Files: rund 35 in diesem Repo (davon etwa 8 gelöscht), dazu zwei externe Repos
- LoC: +700/-6000 (Löwenanteil Tests)
- Risiko: MITTEL. Zentrale Pfade (Schreibweg, Veröffentlichen); das Löschen auf dem Server ist unumkehrbar, aber abgesichert durch Archiv, Reisespeicher und GitHub-Archiv.

## Implementation Details

### Entscheidungen mit Begründung

1. **Schnitt in Lieferungen.** Der Umfang ist zu groß für einen Schritt. L1 muss die Aufrufe von `reisespeicher.py umschaltung`/`umschalten` in `veroeffentlichen.sh` mitnehmen, sonst bricht der laufende Lauf zwischen L1 und L2. Der Lauf aktualisiert sich selbst aus dem Klon; neuer Code wirkt ab dem Folgelauf, `umzug_neustart` und `software_klon` dürfen dabei nicht beschädigt werden.
2. **`/gesund` ohne Git-Teil, fail closed bleibt.** Die Bedingung `not liste or (wurzel/.git).exists()` trifft im Klon zu und prüft heute `schreiben_git.gesund` gegen das Software-Repo. Der Git-Teil entfällt ersatzlos; `speicher_gesund()` und `EinstellungenNichtLesbar` mit 503 (#361) bleiben. Ein unlesbarer Speicher ist nie „gesund“.
3. **`speicherreisen()` ohne Filter.** Jede Reise mit Vorgang im Speicher ist Speicherreise (heutige Wirkung auf der Instanz). Ist der Speicher nicht lesbar, Fehler statt leerer Liste.
4. **Schreibweg nur Speicherweg.** Der Schreiber hat immer eine Basis (neue Reisen legen den Speicher an, Basis 0). Eine Reise ohne Speichereintrag liefert den vorhandenen Fehler `reise_nicht_im_speicher` (503). Der Git-Zweig in `dienst()` entfällt.
5. **`FR_SCHREIBKOPIE` bleibt nur als interne Übergabe** an den Unterprozess in `vorgang_speicher` (temporärer Exportordner). Standardwert `<wurzel>-schreiben` und die Zeilen in `gemeinsam.sh` entfallen. Die Sperrdatei liegt unter `FR_SPERREN`/`FR_DIENST` und ist nicht betroffen.
6. **Kein Handschritt (#250).** Units-Vorlage (`ReadWritePaths`) ändert sich; die Units werden über Veröffentlichen/`units.py` neu erzeugt. Der Pfad mit führendem `-` macht einen fehlenden Ordner harmlos, bis das geschehen ist. Die wirkungslose Zeile `FR_SPEICHERREISEN` in `<FR_DIENST>/instanz/einstellungen.env` wird von der Software ignoriert (kein Fehler) und bleibt liegen.
7. **`altbau_entfernen` (L3), Sicherheitsbedingungen.** Der Schritt läuft in `main_klon` und räumt den alten Bauordner `<FR_SEITEN>/_bau` und `<FR_SEITEN>/_bau-schreiben-*` ab. Er läuft nur, wenn alles zutrifft:
   - `umzug-454 = fertig`;
   - alle Units zeigen auf den Klon (`units.py pruefen` ohne Abweichung beim Ort);
   - jede Reise aus `_bau/reisen` ist Speicherreise;
   - der Merker `<FR_DIENST>/altbau-557` fehlt noch.

   Ablauf: Archiv von `_bau` (ohne `-schreiben-*`) nach `<FR_DIENST>/archiv/` mit Platzprüfung vor dem Löschen (freier Platz mindestens Größe des Archivs plus Reserve; sonst nichts löschen); Archiv gelesen und geprüft; Pfadprüfung, dass jeder zu löschende Pfad aufgelöst innerhalb von `FR_SEITEN` liegt und weder `FR_SEITEN` selbst noch `_software`, `_dienst` oder ein Link darauf ist; Löschen; erst danach Merker schreiben (Idempotenz: bei vorhandenem Merker tut der Schritt nichts, auch wenn der Ordner fehlt). Fehler (kein Platz, Archiv schlägt fehl, Pfadprüfung scheitert) sind nur eine Warnzeile, einmal je Störung entprellt, kein `high`-Alarm (#446) und kein Abbruch des Laufs; der nächste Lauf versucht es erneut.
8. **Reihenfolge L0 vor L3.** Ohne umgestellte Überwachung meldet der Monitor das Fehlen von `_bau` als Ausfall. Ob L0 erledigt ist, prüft der Tech Lead vor dem Vorspulen von L3 (Issue im Infrastruktur-Repo verlinkt und geschlossen).
9. **Kein Rückweg, bewusst.** Entfällt in `docs/betrieb.md` samt Zustand `alt`. Rückfall bei Datenproblemen: Reisespeicher (nur anhängende Versionen), Archiv unter `<FR_DIENST>/archiv/`, archiviertes Reisen-Repo auf GitHub.
10. **Ausnahmelisten in `test_texte.py` dürfen nur kürzer werden;** entfallene Textschlüssel verschwinden aus allen Sprachdateien gleichzeitig.
11. **Vor jedem Vorspulen** laufen die Tests der Instanz (`<FR_DIENST>/instanz/tests`) mit dem Branch, weil Meldungstexte, Umgebungswerte und Dateiformate sich ändern; die öffentliche CI kann sie nicht ausführen.

### Prüfstelle (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Der Rückbau entfernt nur Betriebs- und Weglogik; keine Grundform, keine Art. Durchgespielt an beiden Beispielreisen (Wanderung mit Varianten, Stadtwochenende ohne Pläne) als Speicherreisen. |
| 2 Kein Katalog | Keine Art, kein Merkmal. |
| 3 Keine KI | Feste Regeln. |
| 4 Die Tür | Namen, Parameter und Texte der Konnektor-Werkzeuge unverändert; keine neue Funktion, kein Eintrag in `docs/konnektor.md`. |
| 5 Herkunft | Verlauf bleibt nur anhängend; Archiv und Reisespeicher erhalten die Herkunft. |
| 6 Rollen entscheiden | Unverändert. |
| 7 IDs und Verlauf | Nichts wird verändert oder gelöscht im Speicher; gelöscht wird nur der alte Bauordner nach Archiv. |
| 8 PWA | Seite und Service Worker unverändert. |
| 9 Claude Code | Keine Reiseinhalte in Claude Code. |
| 10 Dokumentation | `docs/betrieb.md`, ADR-0009, `CLAUDE.md`, Spec 454, Kopfkommentare der Skripte. |

## Test Plan

TDD: erst RED (Nachweistests laufen rot gegen den Stand vor dem Rückbau), dann Umsetzung je Lieferung. Neue Datei `engine/tests/test_rueckbau_557.py` (Fixtures: Software-Klon aus lokalem Bare-Repo, nachgebauter alter Bauordner `_bau` mit `-schreiben-*` in einem temporären `FR_SEITEN`, Attrappen für `gh`, `git ls-remote` und das Root-Hilfsprogramm; Reisen nur die beiden Beispielreisen). Der Lauf mit seinen Attrappen ist das Muster aus `test_software_weg_454.py` und `test_nginx_baustein_loeschen_527.py`.

### Automated Tests (TDD RED)

| AC | Test (Datei :: Testname) | Geprüft |
|---|---|---|
| AC-1 | `test_rueckbau_557.py::test_kein_workflow_zeitplan_in_der_software` | GIVEN die Software, WHEN nach `software-nachziehen` gesucht wird (Dateien, `tests.yml`, Doku), THEN kein Fund; Abnahme des Zeitplans im Reisen-Repo über das Issue |
| AC-2 | Abnahme im Infrastruktur-Issue; `test_rueckbau_557.py::test_betrieb_md_nennt_vorbedingung_monitor` | Doku nennt Vorbedingung; Issue geschlossen und verlinkt vor Vorspulen von L3 |
| AC-3 | `test_rueckbau_557.py::test_git_module_sind_geloescht` | GIVEN `engine/`, WHEN Dateien gelistet werden, THEN fehlen `schreiben_git.py`, `stand_git.py`; kein `import` darauf im Repo |
| AC-4 | `test_rueckbau_557.py::test_gesund_ohne_git_teil_im_klon` | GIVEN Wurzel mit `.git` (Klon), WHEN `/gesund` gefragt wird, THEN wird kein Git-Aufruf gemacht und die Antwort hängt nur am Speicher |
| AC-5 | `test_schreiben_speicher.py::test_gesund_und_buchung_unlesbare_einstellungen`, `::test_gesund_ohne_datenbank_ist_ungesund_und_legt_nichts_an` (bestehend, behalten) | GIVEN unlesbarer Speicher oder `EinstellungenNichtLesbar`, WHEN `/gesund`, THEN 503, nie 200 (#361) |
| AC-6 | `test_rueckbau_557.py::test_speicherreisen_ohne_filter[beispielreise]`, `[stadtwochenende]` | GIVEN Reisen mit Vorgang, WHEN `speicherreisen()`, THEN genau diese, ohne Stempel und ohne `.git`-Prüfung |
| AC-7 | `test_instanz.py::test_speicherreisen_unlesbare_datei_loest_aus` (bestehend, behalten) | GIVEN unlesbarer Speicher, THEN Fehler statt leerer Liste |
| AC-8 | `test_rueckbau_557.py::test_schreiber_hat_nur_speicherweg[beispielreise]`, `[stadtwochenende]`; `::test_reise_ohne_speichereintrag_ist_503` | Schreiben, Verwerfen, Buchung gehen über den Speicher; fehlender Eintrag gibt `reise_nicht_im_speicher` |
| AC-9 | `test_rueckbau_557.py::test_reisespeicher_hat_keine_umschaltung` | GIVEN `reisespeicher.py`, THEN keine Namen `umschaltung_frei`, `umschalten_automatisch`, `git_stand_nachtragen`, `_git_baum`; CLI kennt `umschalten`/`umschaltung` nicht |
| AC-10 | `test_rueckbau_557.py::test_veroeffentlichen_ruft_keine_umschaltung`; `test_stand.py` (Git-Zweige raus, Rest bleibt) | Kein Aufruf `reisespeicher.py umschalt*` im Skript; `fuer_seite` ohne Git-Zweig, Stand aus dem Speicher |
| AC-11 | `test_rueckbau_557.py::test_fr_speicherreisen_in_einstellungen_wird_ignoriert` | GIVEN `einstellungen.env` mit der Zeile `FR_SPEICHERREISEN`, WHEN ein Skript startet, THEN kein Fehler, keine Wirkung, Zeile unverändert |
| AC-12 | `test_betrieb.py::test_deploy_kopiert_alle_module_der_dienste`, `::test_deploy_kopiert_module_des_schreibwegs` (bestehend, angepasst); neu `test_rueckbau_557.py::test_deploy_ohne_geloeschte_module_und_ohne_reisen_bau` | GIVEN `deploy.sh`, THEN keine gelöschten Module in den Listen, jedes vorhandene eigene Modul in der Liste; kein Bau aus `$WURZEL/reisen` |
| AC-13 | `test_texte.py` (bestehend), `::test_entfallene_texte_in_allen_sprachen_weg` in `test_rueckbau_557.py` | Schlüssel wie `umschaltung_nicht_freigegeben` fehlen in jeder `texte_<kürzel>.py`; Ausnahmelisten nur kürzer (Test vergleicht Länge mit Stand vor dem Rückbau) |
| AC-14 | Instanz-Tests unter `<FR_DIENST>/instanz/tests` mit dem Branch | Lauf vor dem Vorspulen, Ergebnis im PR vermerkt |
| AC-15 | `test_rueckbau_557.py::test_veroeffentlichen_hat_nur_den_klon_weg` | GIVEN `veroeffentlichen.sh`, THEN keine Funktionen `reisen_des_laufs`, `ci_nachweis`, `anstoss_weitergeben`, `software_anstossen`, `git_reisen_uebrig`, `git_reisen_umschalten`, `umzug_*` außer `umzug_fertig_im_klon`; `main_klon` ist der Einstieg |
| AC-16 | `test_software_weg_454.py` (bestehend: `test_nachweis_gruen_spult_klon_vor_ohne_server_tests`, `test_rueckfall_auf_letzten_guten_stand`, `test_rot_datei_am_software_commit_ein_alarm_je_rot_phase`, `test_skript_startet_sich_nach_umschalten_neu`) und `test_betrieb.py` (Fixture `vf` auf `main_klon` umgestellt; Heartbeat- und Entprellungsfälle laufen über `main_klon`), dazu `test_rueckbau_557.py::test_lauf_im_klon_gruen[beispielreise]`, `[stadtwochenende]` | Lauf grün im Klon, Rot-Datei, Rückfall `software-gut`, Heartbeat nur bei Erfolg, Alarmentprellung (#446) bleiben getestet |
| AC-17 | `test_rueckbau_557.py::test_gemeinsam_und_einrichten_ohne_alte_anordnung` | Keine Namen `fr_alte_anordnung`, `nur_bauordner`, `FR_SCHREIBKOPIE`-Standard, `FR_SPEICHERREISEN`, `FR_NACHZIEHEN_*`, keinen Rückfall über Superprojekt; Vorlage `schreiben.service` ohne `-__WURZEL__-schreiben` |
| AC-18 | `test_rueckbau_557.py::test_git_weg_werkzeuge_sind_geloescht` | `vergleichslauf.sh`, `software-nachziehen.sh/.yml`, `messlauf-schreibweg.py` fehlen; `deploy.sh` und `tests.yml` nennen sie nicht |
| AC-19 | `test_betrieb.py::test_alarmstellen_sind_begruendet` (bestehend) | Liste `ALARMSTELLEN` ändert sich nicht |
| AC-20 | `test_rueckbau_557.py::test_usage_texte_ohne_frieda_pfad` | `karte-holen.sh`, `sichern.sh` ohne `frieda/` |
| AC-21 | `test_rueckbau_557.py::test_units_ohne_handschritt` | GIVEN Units mit alter Vorlage, WHEN Veröffentlichen/`units.py` läuft, THEN werden sie ohne Handschritt auf die neue Vorlage abgeglichen |
| AC-23 | `test_rueckbau_557.py::test_altbau_wird_nach_archiv_entfernt` | GIVEN alle Bedingungen erfüllt, WHEN `main_klon` läuft, THEN Archiv vorhanden und lesbar, `_bau` und `_bau-schreiben-*` weg, Merker gesetzt, Lauf grün |
| AC-24 | `test_rueckbau_557.py::test_altbau_nur_bei_umzug_fertig` | `umzug-454` fehlt oder `alt`: nichts gelöscht |
| AC-25 | `test_rueckbau_557.py::test_altbau_nur_wenn_units_auf_klon_zeigen` | Eine Unit zeigt noch auf `_bau`: nichts gelöscht, Warnzeile |
| AC-26 | `test_rueckbau_557.py::test_altbau_nur_wenn_jede_reise_speicherreise[beispielreise]`, `[stadtwochenende]` | Eine Reise aus `_bau/reisen` nicht im Speicher: nichts gelöscht, Warnzeile mit Reisenamen |
| AC-27 | `test_rueckbau_557.py::test_altbau_archiv_platzpruefung` | Zu wenig Platz (Attrappe): nichts gelöscht, Warnzeile, keine Datei im Archiv halb zurückgelassen |
| AC-28 | `test_rueckbau_557.py::test_altbau_archivfehler_loescht_nichts` | Archivbau scheitert: `_bau` unverändert, Merker nicht gesetzt |
| AC-29 | `test_rueckbau_557.py::test_altbau_pfadpruefung_innerhalb_fr_seiten` | Pfad außerhalb `FR_SEITEN`, Link, `_software`, `_dienst` oder `FR_SEITEN` selbst: nichts gelöscht, Warnzeile |
| AC-30 | `test_rueckbau_557.py::test_altbau_ist_idempotent` | Zweiter Lauf: keine Änderung, kein zweites Archiv, keine Warnzeile |
| AC-31 | `test_rueckbau_557.py::test_altbau_fehler_sind_keine_high_meldung` | In jedem Fehlerfall kein Aufruf `fr_alarm … high`, Lauf endet grün, Warnzeile einmal je Störung (entprellt) |
| AC-32 | `test_rueckbau_557.py::test_altbau_haelt_den_lauf_nicht_auf` | Fehler im Schritt verändern Speicher-Teil, Bau und Heartbeat des Laufs nicht |
| AC-34 | `test_rueckbau_557.py::test_betrieb_md_ohne_git_weg_und_rueckweg` | `docs/betrieb.md` nennt weder Zustand `alt` noch Rückweg noch `frieda/`-Anordnung noch „Software nachziehen“; beschreibt Klon, Aufräumen (`altbau_entfernen`, Archiv) und den fehlenden Rückweg samt Rückfall (Speicher, Archiv, GitHub-Archiv) |
| AC-35 | `test_rueckbau_557.py::test_adr_und_regeln_ohne_workflow_software_nachziehen` | ADR-0009, `CLAUDE.md`, `openspec.yaml` nennen den Workflow nicht mehr; Spec 454 trägt den Hinweis im Kopf |
| AC-22 | Instanz-Tests unter `<FR_DIENST>/instanz/tests` mit dem Branch | Nachweis: Ergebnis im PR von L2 vermerkt |
| AC-33 | Auslieferungstor, kein automatischer Test | Nachweis: Infrastruktur-Issue geschlossen und in #557 verlinkt, Instanz-Tests im PR von L3 vermerkt, bevor vorgespult wird |
| AC-39 | `test_rueckbau_557.py::test_kein_gh_workflow_run_in_der_software`; `::test_spec_454_known_limitations_abgeschlossen` | GIVEN die Software, THEN kein `gh workflow run` in `betrieb/`, `engine/`, `werkzeuge/`; GIVEN Spec 454, THEN die Known Limitations zu AC-2.4/2.6/2.17 und Usage-Texten tragen den Vermerk „abgeschlossen (#557)“; bestehend `test_software_weg_454.py::test_anstoss_startet_nur_einen_lauf`, `::test_nachweis_wird_je_stand_nur_einmal_abgefragt` bleiben grün |
| AC-36 | Abnahme im Issue (Reisen-Repo archiviert, nicht gelöscht) | nachweisbar durch Status des Repos (externer Schritt, kein automatischer Test) |
| AC-37 | Gesamtkriterium: ganze Suite und Pflichtprüfungen der CI | grüne CI auf dem Commit, der vorgespult wird |
| AC-38 | Zusammengesetzt aus `test_fr_speicherreisen_in_einstellungen_wird_ignoriert` (AC-11), `test_units_ohne_handschritt` (AC-21), `test_altbau_wird_nach_archiv_entfernt` (AC-23) | Einstellungen, Units und Aufräumen laufen ohne Eingriff; Live-Abnahme nach L3 ohne Handschritt |

Entfallende Testdateien und Fälle:

- Ganz: `engine/tests/test_software_nachziehen.py`.
- `test_betrieb.py`: rund 86 Fälle über die Fixtures `vf`, `an`, `sp` für den alten `main()` (Fixture `vf` baut eine Reisen-Repo-Anordnung); Fälle zu Modullisten, `instanz`-Fixture mit Submodul und den alten Units ersetzt oder umgestellt; fail-closed- und Alarm-Fälle bleiben.
- `test_software_weg_454.py`: Fixture `alt`, Umzugs- und Rückweg-Tests (`test_umzug_*`, `test_zustand_alt_*`, `test_rueckweg_*`, `test_alter_bauordner_bleibt_*`), Lieferung-1-Fälle zur Umschaltung Git nach Speicher; behalten: Software-Klon-Fälle (Prüfung vor Umschalten, `software-gut`, Rot-Datei, Kennung, Selbstaustausch, Anstoß, Einrichtung, Einstellungen, Meldeweg, Python-Umgebung).
- `test_speicher_stufe5.py` (Umschaltung, Stempel, Vergleich, Sperre `umschaltung_frei`), `test_speicher_stufe3.py` (Git-Fall), `test_export.py` (Git-Export), `test_schreiben_speicher.py` (Git-Zweige), `test_stand.py` (Git-Stand), `test_anstoss_pfad_570.py` (Git-Teile): jeweils nur die Git-Fälle; Speicherfälle bleiben.
- Dummy-`FR_SCHREIBKOPIE` in Test-Fixtures nur dort, wo er die interne Übergabe an den Speicherweg simuliert, sonst entfernt.

Weitere Prüfungen:

- `engine/tests/test_playwright_tmp_628.py`, `test_nginx_baustein_loeschen_527.py`, `test_vorgemerkte_durchlauf_529.py`, `test_texte.py` bleiben grün (Abhängigkeiten geprüft).
- `engine/tests/test_protokolle_ohne_pfade.py` bleibt grün; diese Spec und `test_rueckbau_557.py` enthalten keine echten Pfade, Adressen oder Instanznamen.
- Beide Reisetypen: Jede Funktion gegen Wanderung und Stadtwochenende.
- Live (nach L3): ein Lauf grün, Archiv liegt unter `<FR_DIENST>/archiv/`, `_bau` und `_bau-schreiben-*` fehlen, Merker gesetzt, Wächter, Schreibweg und Kartendienst grün, Seiten unverändert.

## Acceptance Criteria

### L0 (extern, Vorstufe)

- **AC-1:** Der Zeitplan des Workflows „Software nachziehen“ im Reisen-Repo der Instanz ist abgeschaltet; in der Software gibt es keinen Workflow und kein Skript dazu mehr (siehe L2).
- **AC-2:** Die Überwachung in der Infrastruktur liest den Stand des Klons statt `_bau/.git/modules/frieda/HEAD` und kennt keine alte Anordnung (`frieda_umgezogen`/`frieda_software_ordner` ohne Zweig für `_bau`); das Issue im Infrastruktur-Repo ist geschlossen und in #557 verlinkt, bevor L3 vorgespult wird.

### L1 (Engine ohne Git-Weg)

- **AC-3:** `engine/schreiben_git.py` und `engine/stand_git.py` sind gelöscht, nichts importiert sie.
- **AC-4:** `/gesund` hat keinen Git-Teil: Es wird nie ein Git-Aufruf gegen die Software-Wurzel gemacht.
- **AC-5:** `/gesund` bleibt fail closed (#361): unlesbarer Speicher oder `EinstellungenNichtLesbar` ergibt 503, nie „gesund“.
- **AC-6:** `speicherreisen()` gibt jede Reise mit Vorgang im Speicher zurück, ohne Filter durch Stempel oder Git-Stand; beide Beispielreisen gehen durch.
- **AC-7:** Ist der Speicher nicht lesbar, löst `speicherreisen()` einen Fehler aus (nie leere Liste).
- **AC-8:** Der Schreibweg ist nur der Speicherweg (Schreiben, Verwerfen, Buchung, Export); eine Reise ohne Speichereintrag liefert `reise_nicht_im_speicher`.
- **AC-9:** `reisespeicher.py` enthält keine Umschaltung (`_git_baum`, `umschaltung_frei`, Stempel, `umschalten_automatisch`, `git_stand_nachtragen`, CLI `umschalten`/`umschaltung`).
- **AC-10:** `veroeffentlichen.sh` ruft keine entfernten Befehle von `reisespeicher.py` mehr auf; `stand.py`/`fuer_seite` haben keinen Git-Zweig.
- **AC-11:** Eine vorhandene Zeile `FR_SPEICHERREISEN` in den Einstellungen der Instanz bleibt liegen und wird ohne Fehler ignoriert (kein Handschritt, #250).
- **AC-12:** Die Modulliste in `betrieb/deploy.sh` enthält kein gelöschtes Modul; `deploy.sh` baut nichts aus `$WURZEL/reisen`.
- **AC-13:** Entfallene Texte sind in allen Sprachdateien entfernt; die Ausnahmelisten in `engine/tests/test_texte.py` sind nur kürzer geworden.
- **AC-14:** Die Tests der Instanz unter `<FR_DIENST>/instanz/tests` laufen vor dem Vorspulen mit dem Branch grün.

### L2 (Betriebsskripte)

- **AC-15:** `betrieb/veroeffentlichen.sh` hat nur den Weg über den Klon (`main_klon`); alter `main()`, `umzug_*` (außer `umzug_fertig_im_klon`), `reisen_des_laufs`, `ci_nachweis`, `anstoss_weitergeben`, `software_anstossen`, `git_reisen_uebrig`, `git_reisen_umschalten` und die Übergabe an den Klon sind entfernt; `software_klon`, `software_kennung`, `speicher_reisen_lauf`, `speicher_rot_melden`, `pruefen_lauf`, `anstoss_lauf` bleiben.
- **AC-16:** Verhalten des Laufs im Klon bleibt unverändert: grüner Lauf, Prüfung vor Umschalten, Rot-Datei, Rückfall auf `software-gut`, Heartbeat nur bei Erfolg (Readiness), Alarmentprellung (#446).
- **AC-17:** `gemeinsam.sh` und `einrichten.sh` kennen keine alte Anordnung (Superprojekt, `nur_bauordner`, `frieda/`), keinen Standardwert für `FR_SCHREIBKOPIE`, kein `FR_SPEICHERREISEN` und kein `FR_NACHZIEHEN_*`; `schreiben.service` hat keine Zeile `ReadWritePaths=-__WURZEL__-schreiben`.
- **AC-18:** `vergleichslauf.sh`, `software-nachziehen.sh`, `software-nachziehen.yml`, `messlauf-schreibweg.py` und `test_software_nachziehen.py` sind gelöscht; `einstellungen.beispiel` und `.github/workflows/tests.yml` nennen sie und ihre Werte nicht.
- **AC-19:** Die Liste `ALARMSTELLEN` in `test_betrieb.py` gewinnt keine neue Stelle.
- **AC-20:** Usage-Texte (`werkzeuge/karte-holen.sh`, `betrieb/sichern.sh`) nennen keinen Pfad mit `frieda/`.
- **AC-21:** Die geänderte Units-Vorlage wird auf der Instanz ohne Handschritt wirksam (Abgleich über Veröffentlichen/`units.py`).
- **AC-22:** Die Tests der Instanz laufen vor dem Vorspulen grün mit dem Branch.

### L3 (Server-Aufräumen `altbau_entfernen`)

- **AC-23:** Sind alle Bedingungen erfüllt, archiviert der Lauf `_bau` (ohne `-schreiben-*`) nach `<FR_DIENST>/archiv/`, entfernt `_bau` und alle `_bau-schreiben-*` und setzt danach den Merker `<FR_DIENST>/altbau-557`.
- **AC-24:** Nur wenn `umzug-454 = fertig`; sonst nichts.
- **AC-25:** Nur wenn alle Units auf den Klon zeigen; sonst nichts, Warnzeile.
- **AC-26:** Nur wenn jede Reise aus `_bau/reisen` Speicherreise ist; sonst nichts, Warnzeile mit Reisenamen.
- **AC-27:** Vor dem Löschen prüft der Schritt den freien Platz für das Archiv; reicht er nicht, wird nichts gelöscht (Warnzeile).
- **AC-28:** Scheitert das Archiv oder ist es nicht lesbar, bleibt `_bau` unverändert und der Merker ungesetzt.
- **AC-29:** Jeder zu löschende Pfad liegt aufgelöst innerhalb von `FR_SEITEN`; `FR_SEITEN` selbst, `_software`, `_dienst`, Links auf sie und Pfade außerhalb werden nie gelöscht.
- **AC-30:** Idempotent: Mit Merker oder ohne Altbau tut der Schritt nichts (kein zweites Archiv, keine Warnzeile).
- **AC-31:** Fehler sind nur eine Warnzeile, einmal je Störung entprellt; kein `high`-Alarm und kein Abbruch des Laufs (#446).
- **AC-32:** Der Schritt ändert Speicher-Teil, Bau und Heartbeat des Laufs nicht; der nächste Lauf versucht es bei Fehlern erneut.
- **AC-33:** L3 wird erst vorgespult, wenn AC-2 erfüllt ist und die Tests der Instanz grün sind.

### L4 (Doku)

- **AC-34:** `docs/betrieb.md` beschreibt den Ist-Zustand ohne Git-Weg, ohne Zustand `alt`, ohne Rückweg, ohne Workflow „Software nachziehen“ und ohne Anordnung mit `frieda/`; sie beschreibt das Aufräumen (`altbau_entfernen`, Archiv) und den bewusst fehlenden Rückweg samt Rückfall (Reisespeicher, Archiv, GitHub-Archiv).
- **AC-35:** ADR-0009, `CLAUDE.md` (Regel zum Workflow) und `openspec.yaml` sind angepasst; Spec 454 trägt im Kopf einen Hinweis auf diesen Rückbau, der Rest bleibt unverändert, außer AC-39.
- **AC-39:** Given die Known Limitations der Spec 454 zu AC-2.4/AC-2.6, AC-2.17 und den Usage-Texten mit `frieda/` / When der Rückbau ausgeliefert ist / Then sind sie abschließend erledigt: Kein Skript der Software ruft mehr `gh workflow run` auf (AC-2.17 gilt damit ohne Einschränkung), die Usage-Texte nennen kein `frieda/` mehr (AC-20), und die erneute Prüfung eines roten Stands nach #203 bleibt als bewusstes Verhalten bestehen (AC-2.4/AC-2.6, höchstens eine Abfrage je Stunde und Stand); Spec 454 vermerkt das in ihren Known Limitations als abgeschlossen mit Verweis auf #557.

### Archivierung (nach L3)

- **AC-36:** Das Reisen-Repo der Instanz ist archiviert, nicht gelöscht; der Stand ist im Issue vermerkt.

### Übergreifend

- **AC-37:** Die gesamte Testsuite ist grün (lokal und Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`); `engine/tests/test_protokolle_ohne_pfade.py` bleibt grün.
- **AC-38:** Es bleibt kein Handschritt in der Instanz nach dem Software-Wechsel (#250).

## Definition of Done

- [ ] Alle Acceptance Criteria AC-1 bis AC-39 erfüllt.
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests` grün; Pflichtprüfungen der CI grün für jede Lieferung.
- [ ] Tests der Instanz vor jedem Vorspulen mit dem Branch grün.
- [ ] Live nach L3: Lauf grün, Archiv unter `<FR_DIENST>/archiv/` lesbar, `_bau` und `_bau-schreiben-*` entfernt, Merker gesetzt, Überwachung ohne Fehlalarm.
- [ ] Doku (L4) im Ist-Zustand; Reisen-Repo der Instanz archiviert; #557 mit Nachweisen geschlossen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** ADR-0009 (Reisespeicher), Stufe 5 wird um #557 ergänzt; kein neues ADR.
- **Rationale:** Die Entscheidung „Reisen im Speicher, Software getrennt, kein Git-Weg“ ist dort getroffen und mit #454 vollzogen; #557 räumt die Folgen auf. Die Entscheidung „kein Rückweg“ trifft der Product Owner (Issue-Kommentar vom 20.11.2026) und ist in Spec und `docs/betrieb.md` festgehalten.

## Risiken und Rückfall

| Risiko | Maßnahme |
|---|---|
| Unumkehrbares Löschen von `_bau` auf dem Server | Archiv mit Platzprüfung und Lesbarkeitsprüfung vor dem Löschen; Pfadprüfung innerhalb `FR_SEITEN`; Bedingungen (Umzug fertig, Units auf Klon, jede Reise Speicherreise); Merker gegen Wiederholung (AC-23 bis AC-30) |
| Fehlalarm der Überwachung, weil `_bau` fehlt | L0 vor L3; Auslieferungstor AC-33 |
| L1 bricht den laufenden Lauf (Aufrufe entfernter Befehle) | Aufrufe in `veroeffentlichen.sh` gehen in L1 mit (AC-10) |
| Neuer Code wirkt auf das laufende Skript | Selbstaustausch über `exec` aus #454 bleibt unangetastet; Wirkung ab dem Folgelauf |
| `ReadWritePaths`-Änderung verlangt neue Units | Pfad mit `-` ist harmlos; Abgleich über Veröffentlichen, kein Handschritt (AC-21) |
| Wirkungslose Einstellung `FR_SPEICHERREISEN` bleibt in der Instanz | wird ignoriert, kein Fehler (AC-11) |
| Fehler in den Instanz-Tests wegen geänderter Texte, Werte, Formate | Instanz-Tests vor jedem Vorspulen mit dem Branch (AC-14, AC-22) |
| Zu großer Umfang | Fünf Lieferungen, jede einzeln mit grüner CI |
| Kein Rückweg mehr | bewusste Entscheidung des Product Owners; Rückfall bei Datenproblemen: Reisespeicher (nur anhängend), Archiv unter `<FR_DIENST>/archiv/`, archiviertes Reisen-Repo auf GitHub |

## Changelog

- 2026-11-20: Initial spec created (Rückbau des Git-Wegs, #557; Entscheidung PO vom 20.11.2026: jetzt vollständig, kein Rückweg).
