---
entity_id: schreibweg-speicher-347
type: feature
created: 2026-11-06
updated: 2026-11-06
status: draft
workflow: speicher-347-stufe2
version: "1.0"
tags: [schreibweg, reisespeicher, sqlite, betrieb, epic-345]
---

# Speicher Stufe 2: Schreibweg über den Reisespeicher statt Git (#347, Epic #345)

## Approval

- [ ] Approved

## Purpose

Der Schreibweg soll jeden Schreibvorgang einer Reise als einen Vorgang im Reisespeicher (ADR-0009, Stufe 1, `engine/reisespeicher.py`) ablegen, statt per fetch, Commit, Rebase und Push auf `main`. Das beseitigt die Zeitüberschreitungen, die der Git-Weg unter Last hat (Betriebswerte: 379 Vorgänge, Mittel 2,7 s, p99 etwa 25 s, 5 Zeitüberschreitungen). Damit der Merge keine laufende Instanz verändert, wählt ein Schalter je Reise den Weg; ohne Einstellung bleibt alles beim Git-Weg, der bis Stufe 5 in eigene Module zieht.

## Ziel und Abgrenzung

- **Im Scope:**
  - Schalter je Reise als Instanz-Einstellung `FR_SPEICHERREISEN` (Vorgabe leer = Git).
  - Speicherweg in `engine/schreiben.py`: Arbeitskopie aus dem Speicher, Rolle prüfen, Werkzeug anwenden, Probebau, ein Vorgang in einer Transaktion, Nachprüfung nach Abbruch, `buchung`, `/gesund`, `reise_anlegen`.
  - Git-Weg zieht unverändert nach `engine/schreiben_git.py` und `engine/stand_git.py`.
  - `engine/stand.py` liest Stand-Nummer und Änderungsliste aus dem Speicher.
  - Zusätze an der Speicher-Schnittstelle: `erwartet=`, `db(timeout)`, `datei(reise, pfad)`, `reisen()`.
  - Gemeinsamer Baustein „Ordner vorher/nachher → ein Vorgang“ (genutzt von `reise_anlegen`).
  - Neue Texte in allen Sprachdateien, `SB_MODULE` in `betrieb/deploy.sh`, Messlauf-Skript `betrieb/messlauf-schreibweg.py`, Doku.
- **Nicht im Scope:**
  - `betrieb/veroeffentlichen.sh` liest noch nicht aus dem Speicher (Stufe 3, #348). Für eine Speicher-Reise zeigt `publish_status` deshalb bis Stufe 3 „wartet“; die Seite einer Speicher-Reise wird bis dahin nicht neu gebaut.
  - Der Aufruf des Bausteins durch `neu.py nachziehen` (Stufe 3, #348; Entscheidung des Product Owners vom 6.11.2026).
  - Umschalten echter Reisen: kein Eintrag in `FR_SPEICHERREISEN` einer echten Instanz in dieser Stufe. Das geschieht erst nach Stufe 3 (Vergleichslauf, Sicherung außer Haus, Rückspielversuch) in Stufe 5.
  - Entfernen des Git-Wegs (Stufe 5), Auslagerung der Fotos (Stufe 4), asynchrone Vorgänge.
- **Kein `neu.py nachziehen` in dieser Stufe:** Das Format der Reisedaten ändert sich nicht. Der Speicherweg schreibt dieselben Dateien wie der Git-Weg; nur der Träger wechselt, und nur dort, wo der Schalter es verlangt.
- **Auslegung „kein git“ (Product Owner, 6.11.2026):** Das Akzeptanzkriterium aus #347 gilt für die Module `engine/schreiben.py` und `engine/stand.py`. Der Git-Weg lebt bis Stufe 5 in `schreiben_git.py` und `stand_git.py` weiter.

## Source

- **File:** `engine/schreiben.py`, `engine/stand.py`, `engine/reisespeicher.py`; neu `engine/schreiben_git.py`, `engine/stand_git.py`, `betrieb/messlauf-schreibweg.py`
- **Identifier:** `Schreiber`, `vorgang`, `nach_abbruch`, `vorgang_eingetragen`, `Dienst.do_GET`, `stand.fuer_seite`, `reisespeicher.vorgang_schreiben`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/reisespeicher.py` (Stufe 1, ADR-0009) | Modul | Vorgänge, Stand, Export, Nachprüfung per Kennung |
| `engine/instanz.py` | Modul | Einstellung `FR_SPEICHERREISEN`, Ort des Speichers (`speicher()`) |
| `engine/bauen.py` | Modul | Probebau (`Bauer`), `stand.fuer_seite` im Bau (Z. 1229) |
| `engine/reise.py` | Modul | Rollen und Rechte (`erlaubt`, `rolle_neu`) |
| `engine/texte.py`, `engine/texte_de.py`, `engine/texte_en.py` | Module | neue Meldungen (ADR-0006) |
| `engine/neu.py` | Modul | `reise_anlegen` (REPO_WERKZEUGE), IDs; ruft den Baustein erst mit #348 |
| `betrieb/deploy.sh` | Skript | Modulliste `SB_MODULE` des Schreibwegs |
| `docs/specs/betrieb/schreibweg-zeitgrenzen.md` | Spec | Fristen 3/25/3 s und Meldungstabelle 200/504/429/422 bleiben; die Nachprüfung wird lokal |
| `docs/specs/betrieb/reisespeicher-346.md`, `docs/adr/0009-reisespeicher.md` | Spec, ADR | verbindliche Schnittstelle des Speichers |
| Server-Backup von `<FR_SPEICHER>/sicherung/` (henemm-infra) | Betrieb | Pflicht vor dem ersten Umschalten einer echten Reise |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/schreiben.py` | MODIFY | Schalter, Speicherweg, Nachprüfung lokal, `buchung`, `/gesund`, `reise_anlegen`; keine git-Aufrufe |
| `engine/schreiben_git.py` | CREATE | bisheriger Git-Weg, verschoben ohne Verhaltensänderung (bis Stufe 5) |
| `engine/stand.py` | MODIFY | Stand-Nummer und Änderungsliste aus dem Speicher; kein git |
| `engine/stand_git.py` | CREATE | bisherige Git-Zählung (`git`, `nummer`, `aenderungen`), nur bei Bedarf geladen (bis Stufe 5) |
| `engine/reisespeicher.py` | MODIFY | `erwartet=`, `db(timeout)`, `datei`, `reisen`, Baustein Ordner → Vorgang |
| `engine/bauen.py` | MODIFY | Stand je Weg, Probebau ohne Stand |
| `engine/instanz.py` | MODIFY | Einstellung `FR_SPEICHERREISEN` samt Kopfkommentar |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | neue Meldungen |
| `betrieb/deploy.sh` | MODIFY | `SB_MODULE` um die Module des Speicherwegs und des Probebaus |
| `betrieb/einstellungen.beispiel` | MODIFY | Zeile `FR_SPEICHERREISEN` (Test verlangt jeden `FR_`-Namen) |
| `betrieb/messlauf-schreibweg.py` | CREATE | Messlauf (kein Test, Werte ins Issue) |
| `docs/betrieb.md`, `docs/adr/0009-reisespeicher.md`, `docs/specs/betrieb/schreibweg-zeitgrenzen.md` | MODIFY | Schalter, Speicherweg, Nachprüfung lokal |
| `engine/tests/test_schreiben_speicher.py` | CREATE | Tests zu den Acceptance Criteria des Speicherwegs |
| `engine/tests/test_reisespeicher.py` | MODIFY | Tests der Zusätze; Stufe-1-Test „Schreibweg bindet den Speicher nicht ein“ (um Z. 570) wird ersetzt |
| `engine/tests/test_schreiben.py` und Nutzer der Fixture `repo` | MODIFY | Git-Weg über `schreiben_git`, wo nötig beide Wege |
| `engine/tests/test_stand.py`, `test_texte.py`, `test_betrieb.py` | MODIFY | Stand je Weg, Modullisten, Einstellungsbeispiel |

### Estimated Changes

- Files: 4 neu (`schreiben_git.py`, `stand_git.py`, `messlauf-schreibweg.py`, `test_schreiben_speicher.py`), etwa 18 geändert
- LoC: etwa +1300/-350 (ohne Doku); die rund 3000 Zeilen Werkzeuge in `schreiben.py` bleiben unverändert

## Implementation Details

### Schalter je Reise

- `FR_SPEICHERREISEN` in `betrieb/einstellungen.env` des Reisen-Repos: kommagetrennte Reisenamen (Ordnernamen). Vorgabe leer. `instanz` liefert die Liste; der Code kennt keine Reise beim Namen.
- Eine Reise in der Liste schreibt über den Speicher, jede andere über Git. Ohne Einstellung ändert sich nichts.
- **Reise in der Liste ohne Eintrag im Speicher:** Antwort 503 (eigener Text), ohne jede Wirkung. Es wird nie aus einer leeren Arbeitskopie geschrieben. Ausgenommen ist `reise_anlegen` (siehe unten).
- **Der Git-Weg lehnt eine Reise der Liste ab** (kein Doppelschreiben), mit demselben 503-Text.
- Warum nicht „Eintrag im Speicher = umgeschaltet“: Import und Vergleichslauf (Stufe 3) brauchen den Eintrag vorab und würden sonst unbemerkt umschalten. Warum nicht in der Reise selbst: Der Schalter läge sonst in dem Speicher, den er auswählt.

### Schnittstellenänderungen am Reisespeicher

| Funktion | Änderung und Verhalten |
|----------|------------------------|
| `vorgang_schreiben(..., erwartet=None)` | Neuer Parameter. Ist `erwartet` eine Stand-Nummer und weicht `stand_nummer(reise)` innerhalb der Schreib-Transaktion davon ab, wird nichts geschrieben und eine eigene Ausnahme (`StandGeaendert`, Felder `erwartet`, `aktuell`) ausgelöst. `None` heißt: keine Prüfung (Verhalten wie Stufe 1). Bei einer noch unbekannten Reise ist `erwartet=0` gleichbedeutend mit „es gibt noch keinen Stand“. Die Kennungsprüfung (`VorgangVorhanden`) hat Vorrang. |
| `db(timeout=10)` | Neuer Parameter für die Wartezeit auf die Datenbanksperre in Sekunden. Der Schreibweg übergibt die Restzeit der 25-s-Frist (mindestens 0,1), damit eine Sperre die Frist nicht überdauert. Ein Sperrfehler bleibt `sqlite3.OperationalError`. |
| `datei(reise, pfad, bis=None) -> bytes` | Inhalt einer einzelnen Datei im Stand `bis` (ohne: neuester), ohne die übrigen Dateien (Fotos) zu laden. Unbekannte Reise, Stand oder Datei, auch gelöscht: `KeyError`. Pfadregeln wie `vorgang_schreiben`. |
| `reisen() -> list[str]` | Alle Reisen mit mindestens einem Vorgang, sortiert. Kein Schreibzugriff. |
| Baustein `ordner_als_vorgang(reise, ordner, basis, wer, werkzeug, titel, grund, kennung, rolle)` | Vergleicht den Ordner (nachher) mit `aktueller_stand(reise, basis)` (vorher), bildet daraus die Dateienliste mit Löschungen als `None` und ruft `vorgang_schreiben(..., erwartet=basis)`. Ohne Unterschied: `ValueError`. Der Name steht hier fest; die Lage im Modul legt die Umsetzung fest. Derselbe Baustein dient `reise_anlegen` (mit `basis=0`) und später `nachziehen` (#348). |

Hinweis: `stand.py` importiert `reisespeicher` nur innerhalb von Funktionen, weil `reisespeicher` selbst `stand.zeit_iso` importiert (sonst Zirkel).

### Ablauf eines Speicher-Vorgangs (Reise in `FR_SPEICHERREISEN`)

1. **Anfrage prüfen:** Reisename (`REISE_MUSTER`), Werkzeug bekannt (sonst 404 bzw. 422 wie heute).
2. **Weg wählen:** Reise in der Liste → Speicherweg; sonst Git-Weg (aus `schreiben_git`).
3. **Sperre der Reise** (`flock` auf `<FR_SPERREN>/<instanz>-schreiben-<reise>.lock`, Wartezeit `ZEIT_SPERRE` = 3 s). Belegt → 429 wie heute, Stand unverändert.
4. **Speicher prüfen:** `reisen()` enthält die Reise (außer `reise_anlegen`), sonst 503 ohne Wirkung; Datenbank nicht erreichbar (`sqlite3.Error`) → 503 mit anderem Text.
5. **Kennung** wie heute vor dem Unterprozess erzeugen (`secrets.token_hex(6)`); sie geht als `FR_VORGANG` in den Unterprozess.
6. **Arbeitskopie:** temporärer Ordner, `exportieren(reise, <tmp>/reisen/<reise>)`; `basis = stand_nummer(reise)` merken. Der Export zählt zur Frist.
7. **Anwenden im Unterprozess** mit dem installierten Code aus `<FR_DIENST>` (nicht mehr mit dem Code einer Git-Arbeitskopie), Frist = Rest von `ZEIT_GESAMT` (25 s), eigene Prozessgruppe, bei Fristablauf `SIGKILL` der Gruppe wie heute. Darin unverändert: `wer_pruefen` (Rolle, Status), Werkzeug, Probebau (nur ein Baufehler lehnt ab), neue Hinweise. Eine Ablehnung (Rolle, Probebau, nichts geändert) endet hier mit 422, ohne dass der Speicher berührt wurde.
8. **Eintragen:** Unterprozess ruft den Baustein auf (`erwartet=basis`, `db(timeout=Rest)`): ein Vorgang, eine Transaktion. Aus der bisherigen Commit-Nachricht werden `titel` (erste Zeile ohne Reisetitel), `grund` (Text und Fuß aus `inhalt.schreiben.commit_fuss`, in der Sprache der Reise), `wer` (Name der Person), `rolle`, `werkzeug` und `kennung`.
9. **Antwort:** 200 mit `ok`, `text`, `stand` (`gesichert` = neue Stand-Nummer, `veroeffentlicht` wie heute aus `stand.veroeffentlicht`), `commit` = Vorgangs-Nummer (`Vorgang.nummer`, als Text), gegebenenfalls `id`, `hinweise`, `text_teile`. `stand.gesichert_schreiben(reise, stand, commit)` schreibt `<reise>.gesichert.json` wie heute. `veroeffentlichen_anstossen()` bleibt (für Speicher-Reisen wirkungslos bis Stufe 3).
10. **Aufräumen:** temporärer Ordner wird in jedem Fall gelöscht (auch nach Fehler und Abbruch), Sperre freigeben, genau eine Protokollzeile „Fertig <werkzeug> <code> in <Sekunden> s“.

Eine Ablehnung braucht kein Rücksetzen mehr (kein `git checkout/clean`): Die Arbeitskopie ist je Vorgang frisch und wird verworfen.

### Nachprüfung nach Abbruch (lokal)

- `vorgang_vorhanden(kennung)` in `schreiben.py` ruft `reisespeicher.vorgang_eingetragen(kennung)` (nur Lesen, `db(timeout)` mit der Prüffrist `ZEIT_PRUEFUNG` = 3 s) statt fetch und `git log --grep`.
- Ein im Moment des Abbruchs getöteter Unterprozess rollt die SQLite-Transaktion zurück; „nicht eingetragen“ ist deshalb sicher, „eingetragen“ ist es nur bei vorhandener Kennung.
- Ergebnis wie in der Meldungstabelle von `schreibweg-zeitgrenzen.md`: gefunden → 200 „Es hat länger gedauert, ist aber eingetragen.“ mit `stand` aus der gefundenen Stand-Nummer; nicht gefunden → 504 „nicht eingetragen“; Datenbank nicht lesbar oder Prüffrist um → 504 „ungeprüft“. Höchstdauer einer Antwort bleibt 25 + 3 = 28 s, unter `proxy_read_timeout` 30 s.
- Läuft die Frist schon beim Export (Schritt 6) ab, ist noch nichts angewendet: 504 „nicht eingetragen“ ohne Nachprüfung (wie `vorbereiten` heute).

### Weitere Stellen

- **`buchung`** (`GET /<reise>/buchung/<B-…>`): `reisespeicher.datei(reise, "plan/routen.yaml")` statt `git show origin/main`; fehlende Reise oder Datei → `{"gibt_es": False}`; Datenbank nicht erreichbar → 503 (Text „Speicher nicht erreichbar“). Für Git-Reisen unverändert aus `schreiben_git`.
- **`/gesund`:** Beim Speicherweg gesund, wenn die Datenbank antwortet (`SELECT 1` über `db(timeout=...)`); sonst 503. Der Git-Teil (`.git` und `rev-parse`) zieht nach `schreiben_git`, der Dienst ruft ihn nur, wenn die Instanz keine Speicher-Reise hat und Git-Reisen schreibt. Gibt es beide Wege, müssen beide gesund sein.
- **`reise_anlegen`** (REPO_WERKZEUGE): Arbeitskopie mit den bekannten Reisen (`reisen()`) als leere Ordner, damit IDs und Namenskollision wie heute geprüft werden; Sperre auf einer Sperrdatei „reisen“; Werkzeug und Probebau wie heute; die neue Reise wird als erster Vorgang (`basis=0`) über den Baustein geschrieben. Gibt es die Reise schon (im Speicher oder als Git-Reise), lehnt das Werkzeug wie heute ab. Ob eine neue Reise im Speicher oder in Git entsteht, richtet sich nach dem Schalter: Steht ihr Name nicht in `FR_SPEICHERREISEN`, bleibt `reise_anlegen` auf dem Git-Weg.
- **`stand.fuer_seite(ordner, daten)`:** Der Bau kennt nur den Ordner; die Reise ergibt sich aus dem Ordnernamen. Steht sie in `FR_SPEICHERREISEN` und hat einen Speichereintrag, kommen Nummer (`stand_nummer`) und Änderungsliste (`verlauf`, letzte `AENDERUNGEN`, `was` mit Namen statt Kennungen, `wer`, `zeit`) aus dem Speicher; Git-Reisen rufen `stand_git`. Ohne Eintrag (Beispielreisen im Repo, CI, Reise außerhalb der Liste ohne Git) bleibt das Ergebnis `None` wie heute ohne Git.
- **Probebau ohne Stand:** Der Probebau des Schreibwegs und `wer_pruefen` rufen `fuer_seite` nicht auf (der Stand ist dort nicht gebraucht und der Ordner der Arbeitskopie hat keinen Speicherbezug). Ein Schalter am Bau (Name in der Umsetzung) lässt `reise_stand` im Probebau aus.
- **`stand.py`:** `nummer`, `aenderungen`, `git` ziehen nach `stand_git`; `stand.py` enthält weder `subprocess` noch das Wort `git` als Aufruf und importiert `stand_git` nur innerhalb einer Funktion.

### Neue Texte (ADR-0006)

Alle in `texte_de.py` und `texte_en.py` (und jeder weiteren `texte_<sprache>.py`, die zum Zeitpunkt der Umsetzung existiert), Schlüssel unter `schreiben.dienst.`:

| Schlüssel | Anlass | Code |
|-----------|--------|------|
| `speicher_nicht_erreichbar` | Datenbank nicht erreichbar oder gesperrt über die Frist hinaus | 503 |
| `reise_nicht_im_speicher` | Reise steht in `FR_SPEICHERREISEN`, hat aber keinen Eintrag | 503 |
| `reise_im_speicher` | Der Git-Weg lehnt eine Reise der Liste ab | 503 |
| `stand_geaendert` | `erwartet` stimmt nicht mehr (jemand hat zwischenzeitlich geschrieben); bitte noch einmal versuchen | 503 |

Die Ausnahmelisten in `engine/tests/test_texte.py` dürfen nicht länger werden. Die Commit-Nachricht-Texte (`inhalt.schreiben.*`) bleiben.

### Betrieb: Modulliste

`SB_MODULE` in `betrieb/deploy.sh` enthält zusätzlich `reisespeicher.py` und alle Module, die der Unterprozess `anwenden` für Probebau und Werkzeuge lädt (`bauen.py`, `routen.py`, `gpx.py`, `karte.py`, `neu.py` und weitere, die ein Test aus den Importen ermittelt), samt Vorlage und `vendor/`. Neu ist, dass der Dienstordner den Code für `anwenden` liefert; vorher kam er aus der Git-Arbeitskopie. `schreiben_git.py` und `stand_git.py` gehören ebenfalls hinein, solange der Dienst sie lädt. `engine/tests/test_texte.py` (Modullisten-Test um Z. 313) und `engine/tests/test_betrieb.py` werden entsprechend ergänzt. Eine Liste, die den Importen nicht folgt, lässt den Dienst im Betrieb scheitern; der Test prüft sie gegen die Importe.

### Messlauf

`betrieb/messlauf-schreibweg.py` (kein Teil der Testläufe):

- Temporäre Instanz mit beiden Beispielreisen und Kopien unter anderem Namen; Werkzeugmix aus den Werkzeugen des Schreibwegs.
- Zwei Läufe: nacheinander und parallel (mehrere Reisen gleichzeitig, mehrere Vorgänge auf derselben Reise; 429 werden getrennt gezählt).
- Kennzahlen: Anzahl, Mittel, p50, p90, p99, Maximum, Zahl der 504, 429 und 5xx; Export- und Probebauzeit einzeln.
- Parameter `--weg git|speicher`; der Git-Weg läuft gegen einen lokalen Origin und ist nur Richtwert.
- Belastbarer Wert: Lauf auf dem Server der Instanz mit einer erfundenen Testreise, die mit Fotos auf die Größe der größten echten Reise aufgefüllt ist (Fotos sind bis Stufe 4 Blobs in der Datenbank und treiben den Export). Die Werte kommen als Kommentar ins Issue #347, neben die Betriebswerte.

### Doku-Änderungen

- `docs/betrieb.md`: Schalter `FR_SPEICHERREISEN`, Speicherweg und Ablauf, Nachprüfung lokal, Hinweis „Speicher-Reisen zeigen bis Stufe 3 ‚wartet‘“, Server-Backup als Vorbedingung.
- `docs/adr/0009-reisespeicher.md`: Verlauf und Folgen für Stufe 2 (Schalter, Git-Weg in eigenen Modulen bis Stufe 5, Zusätze der Schnittstelle).
- `docs/specs/betrieb/schreibweg-zeitgrenzen.md`: Hinweis, dass Fristen und Meldungstabelle auch für den Speicherweg gelten und die Nachprüfung dort lokal ist; Eintrag im Changelog.
- `betrieb/einstellungen.beispiel`: Zeile `FR_SPEICHERREISEN`.

## Risiken und Betriebs-Vorbedingungen

- **Server-Backup:** Vor dem ersten Umschalten einer echten Reise sichert das Server-Backup der Instanz `<FR_SPEICHER>/sicherung/` (henemm-infra) außer Haus; Rückspielversuch nachgewiesen. Ohne das schaltet keine Instanz um.
- **Dateirechte:** Die Datenbank hat Modus 600 und gehört dem ersten Öffner; der Dienstbenutzer des Schreibwegs und der Benutzer des Wächters müssen dieselbe Datei öffnen können (gleicher Benutzer oder angepasste Rechte). Falsche Rechte zeigen sich als 503 „Speicher nicht erreichbar“.
- **Veralteter Bau:** Bis Stufe 3 baut `veroeffentlichen.sh` nur aus Git; eine Speicher-Reise bliebe stehen. Deshalb kein Umschalten echter Reisen in dieser Stufe.
- **Datenbank-Sperre:** SQLite sperrt die ganze Datei; lange Wartezeit kostet die Frist. Gegenmittel `db(timeout)` mit der Restzeit; der Messlauf zeigt die Grenze.
- **Software-Stand des Unterprozesses:** Der installierte Code in `<FR_DIENST>` muss zum Stand des Speichers passen; eine unvollständige `SB_MODULE` fällt erst im Betrieb auf. Abfangen durch den Importtest.
- **Instanz-Tests:** Ändert sich eine Schnittstelle, die eine Instanz nutzt (Antwortfeld `commit` wird zur Vorgangs-Nummer, neue 503-Texte, Einstellung), laufen vor dem Vorspulen auf `main` die Tests der einbindenden Instanzen mit dem Branch (Anleitung im Reisen-Repo der Instanz). Die öffentliche CI kann private Tests nicht ausführen.
- **Konnektor und 503:** Der Konnektor gibt bei jedem Fehlercode des Schreibwegs den mitgeschickten Text (`fehler`, `fehler_code`, Werte) in der Sprache der Person weiter (`engine/konnektor.py`, Behandlung von `HTTPError` in der Schreibanfrage); die neuen 503-Texte erreichen die Person also ohne Änderung am Konnektor.
- **Eintragen im Unterprozess:** Der Unterprozess `anwenden` trägt den Vorgang selbst ein (Schritt 8). So gilt die Frist auch für das Eintragen, und ein getöteter Unterprozess hinterlässt höchstens eine zurückgerollte Transaktion; die Nachprüfung per Kennung ist deshalb eindeutig.

## Prüfstelle (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Der Speicherweg kennt nur Pfade und Bytes; getestet an beiden Beispielreisen (Wanderung und Städtewochenende). |
| 2 Kein Katalog | Keine Art, kein Merkmal. |
| 3 Keine KI | Keine; reine Regeln. |
| 4 Die Tür | Der Konnektor bleibt die Tür; Werkzeuge und Antwortfelder bleiben, `commit` trägt die Vorgangs-Nummer. |
| 5 Herkunft | Jeder Vorgang trägt Person, Rolle, Werkzeug, Grund, Zeit und Kennung. |
| 6 Rollen entscheiden | Die Rollenprüfung vor dem Eintragen bleibt unverändert; eine Ablehnung ändert den Stand nicht. |
| 7 IDs und Verlauf | Nichts wird überschrieben; Vorgänge werden nur angehängt. |
| 8 PWA | Die Seite einer Git-Reise bleibt unverändert; Speicher-Reisen werden erst ab Stufe 3 gebaut. Kein Browser-Rundgang in dieser Stufe nötig. |
| 9 Claude Code | Reiseinhalte entstehen weiterhin im AI-Client über den Konnektor. |
| 10 Dokumentation | Diese Spec, ADR-0009, `docs/betrieb.md`. |

## Test Plan

### Automated Tests (TDD RED)

Neue Testdatei `engine/tests/test_schreiben_speicher.py` mit einer Fixture, die einen Speicher in `tmp_path` anlegt und die Beispielreisen importiert (parametrisiert über `beispielreise` und `stadtwochenende`); Zusätze der Schnittstelle in `engine/tests/test_reisespeicher.py`. Die Tests sind in dieser Spec den Acceptance Criteria zugeordnet.

- [ ] Test 1: GIVEN eine Reise im Speicher WHEN `vorgang_schreiben` mit `erwartet` unter, gleich und über dem aktuellen Stand läuft THEN nur bei Gleichheit entsteht ein Vorgang, sonst `StandGeaendert` ohne Zeile.
- [ ] Test 2: GIVEN ein Vorgang über den Speicherweg WHEN eine Beispielreise über den Dienst geschrieben wird THEN 200, Stand +1, `commit` = Vorgangs-Nummer und Verlauf mit Titel, Person, Rolle und Kennung.
- [ ] Test 3: GIVEN abgelehnte Vorgänge (Rolle, Probebau, nichts geändert, Sperre belegt) WHEN sie laufen THEN bleibt `stand_nummer` und `aktueller_stand` unverändert.
- [ ] Test 4: GIVEN der Quelltext von `schreiben.py` und `stand.py` WHEN geprüft wird THEN kein git-Aufruf, kein `subprocess` mit git, kein Modulebenen-Import von `*_git`; GIVEN ein `git`-Stub im PATH, der eine Marke schreibt, WHEN ein Speicher-Vorgang samt Probebau läuft THEN fehlt die Marke.
- [ ] Test 5: GIVEN `FR_SPEICHERREISEN` mit einer Reise ohne Speichereintrag WHEN sie schreibt THEN 503 ohne Wirkung; GIVEN eine Reise der Liste WHEN der Git-Weg sie bekommt THEN lehnt er sie ab.
- [ ] Test 6: GIVEN ein abgebrochener Unterprozess WHEN die Nachprüfung läuft THEN gefunden → 200 verzögert, nicht gefunden → 504 „nicht eingetragen“, Datenbank gesperrt → 504 „ungeprüft“.

## Acceptance Criteria

Alle Tests in `engine/tests/test_schreiben_speicher.py`, wenn nicht anders genannt; Beispielreisen: `beispielreise` (Ida, Karl) und `stadtwochenende` (Tom, Lea).

- **AC-1 Schutz vor verlorenen Änderungen:** Given eine Reise im Speicher / When `vorgang_schreiben(..., erwartet=N)` läuft und der aktuelle Stand N, kleiner oder größer ist / Then nur bei Gleichheit entsteht ein Vorgang; sonst `StandGeaendert(erwartet, aktuell)` und keine neue Zeile; ohne `erwartet` bleibt das Verhalten der Stufe 1.
  - Test: `engine/tests/test_reisespeicher.py::test_erwartet_schuetzt_vor_verlorenen_aenderungen`
- **AC-2 Wartezeit der Datenbank:** Given eine von einer anderen Verbindung gehaltene Schreibsperre / When `db(timeout=0.2)` bzw. ein Schreibzugriff damit läuft / Then kommt nach etwa 0,2 s `sqlite3.OperationalError`, nicht erst nach 10 s; ohne Parameter bleibt es bei 10 s.
  - Test: `engine/tests/test_reisespeicher.py::test_db_timeout_richtet_sich_nach_dem_parameter`
- **AC-3 Einzeldatei und Reisenliste:** Given zwei Reisen im Speicher / When `datei(reise, "plan/routen.yaml")` und `reisen()` laufen / Then liefert `datei` die Bytes genau dieser Datei (auch mit `bis=`), `KeyError` bei unbekannter Reise, Stand oder gelöschter Datei, und `reisen()` die sortierte Liste beider Reisen.
  - Test: `engine/tests/test_reisespeicher.py::test_datei_und_reisen`
- **AC-4 Baustein Ordner → Vorgang:** Given ein Ordner mit geänderten, neuen und fehlenden Dateien gegenüber `aktueller_stand(reise, basis)` / When der Baustein läuft / Then entsteht genau ein Vorgang mit den Änderungen und Löschungen (Tombstones); ohne Unterschied `ValueError`; mit `basis=0` für eine neue Reise.
  - Test: `engine/tests/test_reisespeicher.py::test_ordner_als_vorgang`
- **AC-5 Schalter:** Given `FR_SPEICHERREISEN` leer bzw. gesetzt / When `instanz` gefragt wird / Then leere Liste bzw. die genannten Reisen (Leerzeichen und Leerstellen ignoriert); `betrieb/einstellungen.beispiel` enthält `FR_SPEICHERREISEN`; ohne Einstellung schreibt jede Reise über Git wie vor dieser Stufe.
  - Test: `engine/tests/test_schreiben_speicher.py::test_schalter_vorgabe_ist_git` und `engine/tests/test_betrieb.py::test_beispiel_einstellungen_sind_vollstaendig`
- **AC-6 Speicherweg schreibt einen Vorgang:** Given eine Reise der Liste mit Speichereintrag (je eine Beispielreise) / When ein Werkzeug (z. B. eine Frage anlegen) den Dienst durchläuft / Then 200, `stand_nummer` +1, genau ein neuer Vorgang mit Titel, Person, Rolle, Werkzeug und Kennung, `commit` ist die Vorgangs-Nummer, und `aktueller_stand` enthält die geänderte Datei.
  - Test: `test_speicherweg_schreibt_einen_vorgang` (parametrisiert über beide Beispielreisen)
- **AC-7 Ablehnungen lassen den Stand unverändert:** Given eine Reise im Speicher / When ein Vorgang an der Rolle, am Probebau, an „nichts geändert“ oder an der belegten Sperre (429) scheitert / Then die Antwort ist 422 bzw. 429, `stand_nummer` und `aktueller_stand` sind unverändert, und der temporäre Ordner ist gelöscht.
  - Test: `test_abgelehnte_vorgaenge_lassen_den_stand_unveraendert`
- **AC-8 Reise ohne Speichereintrag:** Given eine Reise in `FR_SPEICHERREISEN` ohne Eintrag im Speicher / When ein Schreibvorgang kommt / Then 503 mit dem Text `reise_nicht_im_speicher`, ohne Vorgang und ohne Datei.
  - Test: `test_reise_der_liste_ohne_eintrag_gibt_503_ohne_wirkung`
- **AC-9 Git-Weg lehnt Listenreise ab:** Given eine Reise in `FR_SPEICHERREISEN` / When sie den Git-Weg (`schreiben_git`) erreicht / Then wird sie mit 503 und dem Text `reise_im_speicher` abgelehnt, ohne Commit und ohne fetch.
  - Test: `test_git_weg_lehnt_reise_der_liste_ab`
- **AC-10 Konflikt:** Given zwischen Export und Eintragen schreibt ein anderer Vorgang auf dieselbe Reise / When der erste Vorgang einträgt / Then 503 mit dem Text `stand_geaendert`, kein zweiter Eintrag, Stand des anderen bleibt.
  - Test: `test_zwischenzeitliche_aenderung_gibt_stand_geaendert`
- **AC-11 Nachprüfung nach Abbruch:** Given der Unterprozess überschreitet die Frist / When `nach_abbruch` läuft / Then bei vorhandener Kennung 200 „eingetragen trotz Abbruch“ mit dem Stand, bei fehlender Kennung 504 „nicht eingetragen“, bei nicht lesbarer Datenbank oder abgelaufener Prüffrist 504 „ungeprüft“; die Protokollzeilen der Meldungstabelle bleiben; Stand unverändert, wenn der Unterprozess vor dem Eintrag getötet wurde.
  - Test: `test_nach_abbruch_prueft_lokal_im_speicher`
- **AC-12 Fristen:** Given ein hängender Export oder Eintrag / When der Vorgang läuft / Then endet die Antwort nach höchstens `ZEIT_GESAMT + ZEIT_PRUEFUNG` Sekunden, die Datenbankwartezeit richtet sich nach der Restzeit, und die Zeile „Fertig <werkzeug> <code> in <Sekunden> s“ steht genau einmal im Protokoll; `ZEIT_GESAMT`, `ZEIT_SPERRE`, `ZEIT_PRUEFUNG` behalten die Werte 25, 3, 3.
  - Test: `test_speicherweg_haelt_die_fristen` und der bestehende `test_zeitgrenzen_liegen_unter_der_des_konnektors`
- **AC-13 Buchung:** Given eine Speicher-Reise mit Buchung B-01 in `plan/routen.yaml` / When `GET /<reise>/buchung/B-01` fragt / Then `{"gibt_es": true, "fuer": [...], "wer": ...}`; unbekannte Buchung oder Reise `{"gibt_es": false}`; Datenbank nicht erreichbar 503; Git-Reisen verhalten sich wie vorher.
  - Test: `test_buchung_wird_aus_dem_speicher_gelesen`
- **AC-14 Gesundheit:** Given der Dienst mit Speicher-Reisen / When `GET /gesund` fragt / Then 200 `{"gesund": true}`, wenn die Datenbank antwortet; 503 `{"gesund": false}`, wenn nicht. Ohne Speicher-Reisen prüft `/gesund` wie vorher den Git-Teil.
  - Test: `test_gesund_prueft_die_datenbank`
- **AC-15 Neue Reise:** Given der Speicher kennt die Reisen A und B / When `reise_anlegen` mit einem neuen Namen in `FR_SPEICHERREISEN` läuft / Then entsteht die Reise als erster Vorgang (Stand 1) mit den erzeugten Dateien und neuen IDs ohne Kollision; ein vorhandener Name oder eine Ablehnung des Probebaus legt nichts an.
  - Test: `test_reise_anlegen_schreibt_den_ersten_vorgang`
- **AC-16 Stand-Nachweis:** Given ein Speicher-Vorgang / When `<reise>.gesichert.json` gelesen wird / Then enthält sie `nummer` = Stand-Nummer und `commit` = Vorgangs-Nummer; `stand.lesen` und `stand.enthalten` arbeiten unverändert über die Stand-Nummer.
  - Test: `test_gesichert_json_traegt_stand_und_vorgangsnummer` und der bestehende `engine/tests/test_stand.py`
- **AC-17 Stand für die Seite:** Given eine Reise der Liste mit Speichereintrag / When `stand.fuer_seite` gerufen wird / Then Nummer, Zeit und Änderungsliste (neueste zuerst, Namen statt Kennungen, Person) kommen aus dem Speicher; eine Git-Reise liefert dasselbe wie vor der Verschiebung (`stand_git`); ohne Eintrag und ohne Git ist das Ergebnis `None`; der Probebau enthält keinen Stand.
  - Test: `engine/tests/test_stand.py::test_fuer_seite_je_weg` und `test_probebau_ohne_stand`
- **AC-18 Kein git (statisch):** Given der Quelltext von `engine/schreiben.py` und `engine/stand.py` / When er geprüft wird / Then enthält er keinen git-Aufruf (`"git"` in `subprocess`-Argumenten, `git(`) und keinen Modulebenen-Import von `schreiben_git` oder `stand_git`; die Importe geschehen nur in Funktionen des Git-Wegs.
  - Test: `test_schreiben_und_stand_enthalten_kein_git`
- **AC-19 Kein git (Laufzeit):** Given ein ausführbarer `git`-Stub im ersten Ordner des `PATH`, der bei jedem Aufruf eine Marke schreibt / When ein vollständiger Speicher-Vorgang einschließlich Probebau, ein abgelehnter Vorgang, `buchung`, `/gesund` und `fuer_seite` laufen / Then fehlt die Marke.
  - Test: `test_speicherweg_ruft_nie_git_auf`
- **AC-20 Git-Weg unverändert:** Given keine Einstellung `FR_SPEICHERREISEN` / When die bestehenden Tests des Git-Wegs laufen (`test_schreiben.py`, `test_stand.py`, `test_betrieb.py`, `test_software_nachziehen.py`, `test_bauen.py`, `test_pwa.py`, `test_art_uebersicht.py`) / Then sind sie grün, ohne dass sich ihre Erwartungen an Meldungen, Antwortfelder oder Protokollzeilen ändern; verschoben sind nur Importe der Fixtures.
  - Test: bestehende Tests, Lauf `engine/.venv/bin/python -m pytest -q engine/tests`
- **AC-21 Texte in allen Sprachen:** Given die vier neuen Schlüssel / When `test_texte.py` läuft / Then stehen sie in jeder `texte_<sprache>.py` (mindestens `de`, `en`) und in der Pseudo-Sprache der Tests; die Ausnahmelisten sind nicht länger geworden.
  - Test: `engine/tests/test_texte.py` (bestehende Prüfungen) und `test_neue_schluessel_in_allen_sprachen`
- **AC-22 Modulliste des Betriebs:** Given `betrieb/deploy.sh` / When `SB_MODULE` gelesen und gegen die Importe von `schreiben.py` und seinen Folgemodulen verglichen wird / Then enthält sie `reisespeicher.py` und jedes Modul, das der Speicherweg und der Probebau laden; der Modullisten-Test (`test_jede_sprache_steht_in_den_modullisten_des_deploys`) bleibt grün.
  - Test: `engine/tests/test_betrieb.py::test_sb_module_deckt_die_importe_des_schreibwegs`
- **AC-23 Stufe-1-Test ersetzt:** Given der Stufe-1-Test „Schreibweg bindet den Speicher nicht ein“ / When er ersetzt wird / Then dürfen `schreiben.py`, `stand.py` und `deploy.sh` `reisespeicher` nennen, `konnektor.py` und `rueckmeldungen.py` weiterhin nicht (Stufe 3).
  - Test: `engine/tests/test_reisespeicher.py::test_nur_schreibweg_und_stand_binden_den_speicher_ein`
- **AC-24 Messlauf:** Given `betrieb/messlauf-schreibweg.py` / When es mit `--weg speicher` und `--weg git`, nacheinander und parallel, mit beiden Beispielreisen läuft / Then gibt es Anzahl, Mittel, p50, p90, p99, Maximum und die Zahl der 504, 429 und 5xx aus; der Speicherweg zeigt im Lauf auf dem Server der Instanz keine Zeitüberschreitung, und p99 liegt deutlich unter 25 s. Die Werte stehen im Issue #347.
  - Test: `engine/tests/test_schreiben_speicher.py::test_messlauf_skript_gibt_kennzahlen_aus` (Kurzlauf mit wenigen Vorgängen); die Messwerte selbst sind Nachweis, kein Test
- **AC-25 Doku:** Given die Änderung / When `docs/betrieb.md`, ADR-0009, `schreibweg-zeitgrenzen.md` und `betrieb/einstellungen.beispiel` gelesen werden / Then nennen sie `FR_SPEICHERREISEN`, den Speicherweg, die lokale Nachprüfung, das Fehlen des Bauens aus dem Speicher bis Stufe 3 und das Server-Backup als Vorbedingung; `engine/tests/test_protokolle_ohne_pfade.py` bleibt grün.
  - Test: `engine/tests/test_schreiben_speicher.py::test_doku_nennt_schalter_und_vorbedingungen` und der bestehende `test_protokolle_ohne_pfade.py`

## Definition of Done

- [ ] Jede Acceptance Criterion ist durch einen automatischen Test belegt (AC-24: Kurzlauf; die Messwerte stehen im Issue)
- [ ] Alle Tests ohne echte Reisen grün (`engine/.venv/bin/python -m pytest -q engine/tests -n auto`), mit beiden Beispielreisen
- [ ] Messwerte stehen im Issue #347 neben den Betriebswerten
- [ ] Vor dem Vorspulen: Tests der einbindenden Instanzen mit dem Branch
- [ ] Keine echte Reise ist umgeschaltet; kein Handschritt in Reisen oder Instanzen nötig

## Known Limitations

- Speicher-Reisen werden bis Stufe 3 nicht neu gebaut; `publish_status` zeigt „wartet“.
- Der Git-Weg bleibt bis Stufe 5; danach entfallen `schreiben_git.py`, `stand_git.py` und der Schalter.
- Der Messlauf gegen den Git-Weg nutzt einen lokalen Origin und ist nur ein Richtwert.
- Große Fotos liegen bis Stufe 4 als BLOB in der Datenbank und verlängern den Export.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** ADR-0009 (`docs/adr/0009-reisespeicher.md`, wird um den Verlauf der Stufe 2 ergänzt)
- **Rationale:** Die Entscheidung für den Speicher steht in ADR-0009. Stufe 2 setzt sie um und fügt als Übergangsregel den Schalter je Reise und die Trennung des Git-Wegs hinzu (Option A der Analyse, Entscheidung des Product Owners vom 6.11.2026). Das berührt Grundformen und Merkmale nicht (ADR-0001, Punkt 8: Technik ist Mittel); ein neues ADR ist nicht nötig.

## Changelog

- 2026-11-06: Initial spec created
- 2026-11-06: Mit Stufe 3 (#348, `speicher-348-stufe3.md`) entfällt „bis Stufe 3 wartet“: Das Veröffentlichen baut Reisen aus `FR_SPEICHERREISEN` aus dem Speicher.
