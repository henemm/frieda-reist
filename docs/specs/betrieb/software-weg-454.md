---
entity_id: software-weg-454
type: feature
created: 2026-11-12
updated: 2026-11-13
status: draft
workflow: software-weg-454
version: "1.0"
tags: [software-weg, veroeffentlichen, reisespeicher, umzug, betrieb, epic-345]
---

# Software direkt aus dem öffentlichen Repo, Reisen-Repo wird Archiv (#454)

Folge von #350 (Variante B). Grundlage: `docs/context/software-weg-454.md` (Kontext, Inventar, Analyse, Technical Approach), `docs/specs/betrieb/speicher-350-stufe5.md`, `docs/specs/betrieb/software-wechsel-ohne-handarbeit-250.md`, `docs/specs/betrieb/meldeweg-nur-ausfaelle-446.md`, ADR-0009, ADR-0001.

## Approval

- [ ] Approved

(Keine Produktentscheidung offen: Alle Entscheidungen sind technisch und unten begründet.)

## Purpose

Heute erreicht die Software die Instanz nur über das private Reisen-Repo: Der Bauordner `FR_WURZEL` ist dessen Klon, die Software ist das Submodul `frieda/`, ein Workflow im Reisen-Repo („Software nachziehen“) hebt den Zeiger, `veroeffentlichen.sh` stößt ihn per `gh workflow run` an. Nach #350 liegen die Reiseinhalte im Reisespeicher; der Umweg trägt nur noch die Software und drei Dinge, die sonst im Reisen-Repo wohnen (Einstellungen, Meldeweg, Instanz-Tests). Er kostet Zuverlässigkeit (GitHub-Workflow, Zeitplan, Zeiger) und hält ein zweites Repo am Leben.

Ziel: Die Instanz holt die Software direkt aus diesem öffentlichen Repo, prüft sie, bevor sie umschaltet, und fällt bei Rot auf den letzten guten Stand zurück. Das Reisen-Repo wird Archiv. Kein Handschritt des Betreibers beim Wechsel (#250); einzige Ausnahme ist die einmalige Umstellung der Units durch den Tech Lead bei der Auslieferung (Entscheidung 10, Schritt 4). Der Wechsel ist umkehrbar.

Zwei Lieferungen unter einer Spec, in dieser Reihenfolge:

1. **Lieferung 1, alle Reisen im Speicher** (keine Pfadänderung): „Im Speicher ist, was im Speicher steht“; neue Reisen entstehen im Speicher; übrige Git-Reisen schaltet der Lauf selbst um. Voraussetzung für Lieferung 2 (sonst bliebe eine Reise ohne Heimat, sobald das Reisen-Repo nicht mehr gebaut wird).
2. **Lieferung 2, Software direkt:** Software-Klon, Prüfung vor dem Umschalten, letzter guter Stand, Einstellungen unter `<FR_DIENST>/instanz/`, automatischer wiederholbarer Umzug, Anstoß nur noch als Lauf.

## Source

- **File:** `engine/instanz.py`, `engine/schreiben.py`, `engine/neu.py`, `engine/reisespeicher.py`, `engine/rueckmeldungen.py`, `engine/texte_<sprache>.py`, `betrieb/veroeffentlichen.sh`, `betrieb/gemeinsam.sh`, `betrieb/einrichten.sh`, `betrieb/deploy.sh`, `betrieb/waechter.sh`, `betrieb/sichern.sh`, `betrieb/freischalten.sh`, `betrieb/units.py`, `betrieb/vorlagen/*`, `betrieb/einstellungen.beispiel`, Usage-Texte in `werkzeuge/`, `.github/workflows/tests.yml`, `docs/betrieb.md`, `docs/adr/0009-reisespeicher.md`; neu `engine/tests/test_software_weg_454.py`
- **Identifier (neu):** `instanz.speicherreisen()` (liest aus dem Speicher), `reisespeicher.umschalten_automatisch`, Software-Klon `<FR_SEITEN>/_software`, Merker `<FR_DIENST>/software-gut` (letzter guter Commit), `<FR_DIENST>/instanz/` (`einstellungen.env`, `melden.sh`, optional `tests/`), `<FR_DIENST>/umzug-454` (Zustand des Umzugs), Python-Umgebung `<FR_DIENST>/python`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/veroeffentlichen.sh` (`main`, `software_kennung`, `ci_nachweis`, `software_anstossen`, `anstoss_weitergeben`, Rot-Datei, `reisen_des_laufs`, `git_reisen_uebrig`, `units_abgleichen`) | Skript | Software-Weg und Lauf |
| `betrieb/gemeinsam.sh` (`FR_WURZEL`, `nur_bauordner --main`, `fr_einlesen`, `FR_PYTHON`, `FR_SCHREIBKOPIE`, `fr_alarm`, `fr_alarm_ende`) | Skript | Wurzel, Einstellungen, Vorgaben, entprellte Alarme (#446) |
| `betrieb/deploy.sh`, `betrieb/einrichten.sh`, `betrieb/units.py`, Vorlagen für systemd und nginx | Skripte | Kopieren der Module nach `<FR_DIENST>`, Einrichtung, Abgleich der Units über das Root-Hilfsprogramm |
| `engine/instanz.py`, `engine/schreiben.py`, `engine/neu.py`, `engine/reisespeicher.py`, `betrieb/vergleichslauf.sh` | Module, Skript | Wahl Git-/Speicherweg, Anlegen, Vergleich und Umschaltung (Sperre aus #350, `umschaltung_frei`) |
| `engine/rueckmeldungen.py` | Modul | Anstoß von der Seite (`api/aktualisieren`, `_anstoss.json`) |
| `engine/tests/test_betrieb.py`, `test_software_nachziehen.py`, `test_speicher_stufe5.py`, `test_schreiben.py`, `test_stand.py` | Tests | Fixtures bauen die Anordnung mit Submodul nach und werden auf den Klon umgestellt |
| **Infrastruktur-Repo der Instanz (anderes Repo):** `scripts/monitor.sh` (Rückstands-Check über `.git/modules/frieda/HEAD`), Aufruf von `sichern.sh` im Server-Backup | Fremd-Repo | **Vorbedingung von Lieferung 2** (siehe unten) |
| `docs/specs/betrieb/software-wechsel-ohne-handarbeit-250.md`, `meldeweg-nur-ausfaelle-446.md`, `speicher-350-stufe5.md` | Specs | Regeln, die gelten bleiben (kein Handschritt, Alarm nur bei Ausfall, Umschaltprüfung) |

### Vorbedingung von Lieferung 2 (Infrastruktur)

Zwei Stellen außerhalb dieses Repos hängen am Pfad des heutigen Bauordners und müssen **beide Anordnungen** (alt: Submodul im Bauordner; neu: Software-Klon) akzeptieren, bevor Lieferung 2 auf einer Instanz ausgeliefert wird:

1. **Monitor:** Der Rückstands-Check liest heute `.git/modules/frieda/HEAD`. Künftig vergleicht er `HEAD` des Software-Klons mit `main` der Software (Warnung ab > 6 h wie bisher); fehlt der Klon, gilt der alte Ort.
2. **Backup:** Der Aufruf von `sichern.sh` im Server-Backup muss den neuen Pfad finden (Klon statt `<Bauordner>/frieda/betrieb/`). Sonst entsteht eine Sicherung ohne frischen Schnappschuss. Die Einstellungen unter `<FR_DIENST>/instanz/` liegen im gesicherten Bereich.

Dafür entsteht ein Issue im Infrastruktur-Repo; der Tech Lead setzt es selbst um und verlinkt es in #454. Ohne dessen Abschluss wird Lieferung 2 nicht ausgeliefert (Auslieferungstor, AC-2.21).

## Scope

### Im Scope

**Lieferung 1:**
- `speicherreisen()` in `engine/instanz.py` und die Entsprechung in `betrieb/gemeinsam.sh` (`speicherreisen`, `ist_speicherreise`) fragen den Reisespeicher: im Speicher ist, was dort einen Eintrag hat. `FR_SPEICHERREISEN` ist nur Übergang (gelesen, wirkungslos, keine Fehlermeldung, kein Handschritt).
- `trip_create` und `reise_anlegen` legen die Reise im Speicher an (Anfangsvorgang wie bei der Umschaltung); sie entsteht nie mehr in Git. Der Speicher-Teil des Laufs baut sie.
- Der Lauf schaltet übrige Git-Reisen selbst um: Vergleich wie `vergleichslauf.sh`, nur bei „gleich“ umschalten, sonst Hinweis, die Reise bleibt in Git (kein Datenverlust, kein Löschen).

**Lieferung 2:**
- Software-Klon als Bauordner, `main` nur vorspulen; Prüfung vor dem Umschalten; letzter guter Stand und Rückfall; Kennung, Rot-Datei und Stempel am Software-Commit.
- Einstellungen, Meldeweg und optional Prüfungen der Instanz unter `<FR_DIENST>/instanz/`; Python-Umgebung außerhalb des Klons.
- Automatischer, wiederholbarer Umzug einer bestehenden Instanz; alter Bauordner bleibt als Rückweg; Units als letzter Schritt.
- Anstoß von der Seite stößt nur noch einen Lauf an.
- Wegfall des Git-Teils des Laufs (Fetch des Reisen-Repos, `reisen_des_laufs`, `git_reisen_uebrig`, Tests des Reisen-Repos, `software_anstossen`), Anpassung von `einrichten.sh` (ohne `gh auth` und Reisen-Repo), Pfade der Units, Vorlagen, Skripte und Usage-Texte.
- Tests, `.github/workflows/tests.yml` (Instanz-Lauf ohne Superprojekt), Doku in `docs/betrieb.md` und ADR-0009.

### Nicht im Scope (Out of Scope)

- **Rückbau des Git-Wegs als Folge-Issue** (wird bei Abschluss von Lieferung 2 angelegt und in #454 verlinkt): `engine/schreiben_git.py`, `engine/stand_git.py`, `betrieb/vergleichslauf.sh`, `FR_SCHREIBKOPIE` und `_bau-schreiben-*`, `betrieb/software-nachziehen.sh` und `.yml`, Archivierung des Reisen-Repos, Entfernen des alten Bauordners. Dieser Schritt ist erst nach einer Beobachtungszeit sicher, weil der alte Bauordner der Rückweg ist. #454 sorgt nur dafür, dass der neue Software-Weg den Git-Weg nicht mehr **braucht**; vorhandener Code bleibt unangetastet, soweit er nicht im Weg ist.
- Umstellen der Units über einen neuen Mechanismus: Es bleibt das vorhandene Root-Hilfsprogramm (`units.py`, `<instanz>-units-installieren`) mit unveränderter Erlaubnisliste. Die einmalige Umstellung bei der Auslieferung (Entscheidung 10, Schritt 4) nutzt `einrichten.sh --installieren`, das dieselben Vorlagen installiert und als Root auch die gesperrten Zeilen setzen darf.
- Alles in den Fremd-Repos (Infrastruktur, privates Reisen-Repo) außer den genannten Issues; Archivieren des Reisen-Repos ist Teil des Folge-Issues.
- Änderungen an Konnektor-Werkzeugen, ihren Namen und an der Seite; keine neue Reise-Funktion.

### Affected Files

| Datei | Änderung | Lieferung |
|---|---|---|
| `engine/instanz.py` | `speicherreisen()` aus dem Speicher; `FR_SPEICHERREISEN` wirkungslos | 1 |
| `engine/schreiben.py`, `engine/neu.py` | neue Reise im Speicher anlegen | 1 |
| `engine/reisespeicher.py` | `umschalten_automatisch`, offene Umschaltung erkennen | 1 |
| `betrieb/gemeinsam.sh` | `speicherreisen`/`ist_speicherreise` aus dem Speicher (1); `FR_WURZEL` = Klon, Einstellungen aus `<FR_DIENST>/instanz/`, `FR_PYTHON` = `<FR_DIENST>/python` (2) | 1, 2 |
| `betrieb/veroeffentlichen.sh` | automatische Umschaltung (1); Software-Weg, Prüfung vor Umschalten, `software-gut`, Rückfall, Kennung, Rot-Datei, Umzug, Anstoß, Wegfall Git-Teil (2) | 1, 2 |
| `betrieb/einrichten.sh` | ohne `gh auth` und Reisen-Repo, legt Klon und `<FR_DIENST>/instanz/` an | 2 |
| `betrieb/deploy.sh`, `betrieb/waechter.sh`, `betrieb/sichern.sh`, `betrieb/freischalten.sh`, `betrieb/units.py`, `betrieb/vorlagen/*`, `betrieb/einstellungen.beispiel` | Pfade `__WURZEL__/betrieb/…`, keine Reisen aus `<FR_WURZEL>/reisen` | 2 |
| Usage-Texte in `werkzeuge/` | Pfade ohne `frieda/` | 2 |
| `engine/rueckmeldungen.py`, `engine/texte_<sprache>.py` | Anstoß nur Lauf, Texte `seite.rahmen.release.*` | 2 |
| `engine/tests/test_software_weg_454.py` (neu), `test_betrieb.py`, `test_software_nachziehen.py`, `test_speicher_stufe5.py`, `test_schreiben.py`, `test_stand.py` | neue Tests, Fixtures ohne Superprojekt | 1, 2 |
| `.github/workflows/tests.yml` | Instanz-Lauf ohne Superprojekt | 2 |
| `docs/betrieb.md`, `docs/adr/0009-reisespeicher.md` | neuer Weg, Umzug, Rückweg, Infra-Vorbedingung | 1, 2 |

### Estimated Changes

- Dateien: ca. 20 in diesem Repo, dazu ein Issue in der Infrastruktur
- Umfang: rund +900 / -500 Zeilen (etwa die Hälfte Tests)
- Risiko: HOCH. Lieferweg aller Reisen und Pfade sämtlicher Units. Abgefedert durch zwei getrennte Lieferungen, „erst prüfen, dann umschalten“, Units als letzten Schritt, unangetasteten alten Bauordner und Wiederholbarkeit des Umzugs.

## Entscheidungen mit Begründung

1. **Zwei Lieferungen, eine Spec.** Lieferung 1 ändert keinen Pfad und ist allein nützlich (neue Reisen entstehen in Git, solange es das gibt: eine wachsende Lücke). Lieferung 2 darf erst folgen, wenn auf der Instanz keine Reise mehr in Git liegt. Zwei kleine Schritte am Live-System statt einem großen.
2. **Im Speicher ist, was im Speicher steht.** Die Liste in einer versionierten Einstellungsdatei ist eine zweite Wahrheit, die auseinanderlaufen kann (Befund der Instanz: die Liste kam aus der geheimen Umgebung, nicht aus der Einstellungsdatei). Der Speicher kennt seine Reisen; `speicherreisen()` liest sie von dort. Eine Reise gilt als im Speicher, wenn sie dort mindestens einen Vorgang hat und keine Umschaltung offen ist (Anfangsvorgang aus Git ohne Stempel `gleich`, Entscheidung 4). Ist der Speicher nicht lesbar, wird `EinstellungenNichtLesbar` beziehungsweise der bekannte Speicherfehler ausgelöst (fail closed, #361), nie „keine Reisen“.
3. **Neue Reisen im Speicher.** `reise_anlegen` schreibt den Anfangsvorgang in den Speicher (Struktur aus `neu.py`: IDs, Abschnitte, Anlegen). Ein Rückfall nach Git gibt es nicht. Die Reise erscheint im Speicher-Teil des Laufs; die Seite entsteht beim nächsten Bau.
4. **Automatische Umschaltung nur bei „gleich“.** Der Lauf vergleicht eine Git-Reise mit dem Speicher (Anfangsvorgang aus dem Git-Stand, Vergleich byte-gleich, dieselbe Logik wie `vergleichslauf.sh`). Bei „gleich“ legt er den Anfangsvorgang an und stempelt `gleich` (Stempel mit `baum`, `stand`); danach gilt die Reise durch Mitgliedschaft im Speicher. Bei „unterschiedlich“ oder Fehler bleibt die Reise in Git, es gibt eine Warnzeile und kein `high` (kein Ausfall, #446). Es wird nie gelöscht und nie überschrieben. Idempotent: Eine schon umgeschaltete Reise wird übersprungen. Bricht die Umschaltung zwischen Anfangsvorgang und Stempel ab, ist sie offen: Die Reise bleibt in Git, der nächste Lauf vergleicht erneut gegen den vorhandenen Anfangsvorgang und stempelt bei „gleich“ (kein zweiter Anfangsvorgang).
5. **Prüfung vor dem Umschalten statt nach dem Umschalten.** Der Klon wird erst auf einen neuen Commit gesetzt, wenn der Commit geprüft ist. Ablauf: `git fetch origin main` → Commit `C` von `origin/main` → Nachweis der Pflichtprüfungen genau dieses Commits (`tests (leer)`, `tests (instanz)`, `gitleaks`; `main` ist geschützt, also liegt dort nur grün Geprüftes; Abfrage ohne Anmeldung, einmal je neuem Stand, Begrenzung 60 je Stunde unkritisch) → erst dann Umschalten des Arbeitsbaums. Ohne Nachweis (Abfrage scheitert, Prüfung noch nicht fertig): Tests auf dem Server in einem eigenen Arbeitsbaum von `C` (`git worktree`), der Klon bleibt unberührt. Rot: Klon bleibt auf dem letzten guten Stand, Rot-Datei am Software-Commit, Alarm wie heute (einmal je Rot-Phase, `alarm_senden`).
6. **Letzter guter Stand in `<FR_DIENST>/software-gut`.** Erst nach grünem Lauf (Deploy und Bau grün) schreibt der Lauf `C` dort hinein. Rückfall = Klon auf diesen Commit zurücksetzen und die Dienste neu starten. Fehlt die Datei (Erstlauf nach Umzug), gilt der Commit, mit dem der Umzug lief.
7. **Stempel und Kennung am Software-Commit.** `veroeffentlicht` und `software_kennung` sind künftig der Commit der Software (statt `HEAD:frieda` im Reisen-Repo). Der Speicher-Teil zieht Reisen nach, sobald dieser Commit veröffentlicht ist; die Logik bleibt, nur die Quelle der Kennung ändert sich. Die Rot-Datei hängt am Software-Commit („Bekannter roter Stand“ derselbe Commit).
8. **Fester Ort für Einstellungen: `<FR_DIENST>/instanz/`.** Dort liegen `einstellungen.env`, `melden.sh`, optional `tests/`. Der Ort ist vom Server-Backup erfasst und unabhängig vom Klon. Reihenfolge der Einstellungen: Umgebung vor `<FR_DIENST>/instanz/einstellungen.env`; Übergang: Fehlt die Datei dort, gilt der alte Ort `<alter Bauordner>/betrieb/einstellungen.env`. Geheimes bleibt in `<FR_DIENST>/betrieb.env` und `konten.env` (unverändert). Nichts Instanzspezifisches in der Software: der Ort ist aus `FR_DIENST` abgeleitet.
9. **Python-Umgebung an festem Ort `<FR_DIENST>/python` außerhalb des Klons**, damit ein Umschalten oder Zurücksetzen des Klons sie nicht berührt und der Rückweg (alter Bauordner mit eigener `engine/.venv`) unabhängig bleibt. Sie wird neu aufgebaut, wenn sich die Abhängigkeitsliste (`requirements`) im Commit ändert, vor dem Umschalten der Units.
10. **Umzug ohne Handschritt des Betreibers (#250), wiederholbar und umkehrbar; die Units stellt der Tech Lead einmalig bei der Auslieferung um (Schritt 4).** Der **letzte Stand, der noch über das Submodul kommt** (also dieser Commit, wenn er über den alten Weg ankommt), führt im grünen Lauf den Umzug aus. Reihenfolge, jeder Schritt idempotent und einzeln prüfbar:
    1. Software-Klon anlegen oder aktualisieren (öffentlich, ohne Anmeldung, nur `main`).
    2. Einstellungen und Meldeweg nach `<FR_DIENST>/instanz/` kopieren (nur wenn Ziel fehlt oder älter ist; nie überschreiben, wenn dort Neueres liegt); optionale Instanz-Tests kopieren.
    3. Python-Umgebung unter `<FR_DIENST>/python` aufbauen und mit dem Klon-Commit prüfen (Probebau einer Beispielreise, Tests des Klons nach Entscheidung 5).
    4. **Erst wenn 1 bis 3 grün sind:** Units auf die neuen Pfade abgleichen. Das ist der **letzte** Schritt. Weil sich dabei `ExecStart` und `FR_WURZEL` ändern, die nicht in der Erlaubnisliste des Root-Hilfsprogramms stehen, stellt der Tech Lead die Units **einmalig bei der Auslieferung bewusst** um (`einrichten.sh --installieren` aus dem Klon, Root). Die Erlaubnisliste bleibt unverändert (Entscheidung des Product Owners, 13.11.2026). Bis dahin meldet der Lauf den Stand einmal je Commit als Warnzeile und veröffentlicht weiter über den alten Weg.
    5. Zustand `<FR_DIENST>/umzug-454` auf `fertig` setzen; Neustart des Skripts mit `exec "$0"` (Muster #242), damit es aus dem Klon läuft. Startet der Lauf schon aus dem Klon (Units umgestellt), setzt er den Zustand selbst auf `fertig`, falls er es noch nicht ist.

    Scheitert ein Schritt vor 4, bleibt alles beim alten Weg: kein Alarm der Stufe `high`, eine Warnzeile, der nächste Lauf (alle 5 Minuten) versucht denselben Umzug erneut. Der alte Bauordner und alle seine Units-Vorlagen bleiben unangetastet; **Rückweg:** Units auf den alten Bauordner abgleichen (derselbe Mechanismus), Zustand auf `alt`. Der Rückweg gehört in `docs/betrieb.md` und ist kein neuer Befehl.
11. **Alarm nur bei Ausfall (#446).** Neue Meldungen: nur Rot-Phase des Veröffentlichens bleibt `high` (bestehende Stelle, einmal je Rot-Phase). Alles Neue (Umzug scheitert, Umschaltung einer Reise bleibt aus, Nachweis nicht abrufbar) ist Warnzeile im Protokoll oder `normal`, entprellt über `fr_alarm`-Merker; die `high`-Liste `ALARMSTELLEN` in `engine/tests/test_betrieb.py` bekommt keine neue Stelle. Dauerhafte Zustände gehören als Teil-Check in `monitor.sh`.
12. **Anstoß von der Seite stößt nur einen Lauf an.** `_anstoss.json` löst statt `gh workflow run` den Lauf des Veröffentlichens aus (Start der Unit beziehungsweise Merker, den der Lauf liest). Die Seite zeigt weiter „Stand noch nicht auf dem Server“ bis zum nächsten grünen Lauf. Texte `seite.rahmen.release.*` werden auf die neue Bedeutung geprüft, in allen Sprachen.
13. **Instanz-Tests entfallen als Pflicht.** Der Betrieb wird durch Software-Tests mit `einstellungen.beispiel` und den Umzugstest abgedeckt; Inhaltstests echter Reisen entfallen (jede Reise wird bei jedem Bau geprüft). Liegt `<FR_DIENST>/instanz/tests/` vor, laufen sie als **nicht sperrende** Prüfung (Warnung), damit die Prüfung „nichts Privates in der Software“ erhalten bleibt, ohne einen Wechsel aufzuhalten.
14. **Kein Zustand im Skript, der den Wechsel überlebt.** Der Lauf liest Klon-Commit, `software-gut`, Zustand des Umzugs und Rot-Datei bei jedem Start neu; ein halber Wechsel (Abbruch zwischen Schritten) wird beim nächsten Lauf fortgesetzt oder zurückgenommen, nie stillgelegt.

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** ADR-0009 (Reisespeicher), Stufe 5 wird um #454 ergänzt; kein neues ADR, weil die Entscheidung „Reisen im Speicher, Software getrennt“ dort schon getroffen ist und #454 sie für den Lieferweg der Software vollzieht.

## Prüfstelle (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Betrieb und Anlegen kennen nur Reisenamen, den Speicher und Commits der Software; keine Grundform, keine Art. Durchgespielt an beiden Beispielreisen: `beispielreise` (Wanderung mit Varianten) und `stadtwochenende` (ohne Pläne), jeweils als Git-Reise, die der Lauf umschaltet, und als neu im Speicher angelegte Reise. |
| 2 Kein Katalog | Keine Art und kein Merkmal. |
| 3 Keine KI | Feste Regeln. |
| 4 Die Tür | `trip_create` und `reise_anlegen` behalten Namen, Parameter und Texte; sie schreiben nur an anderer Stelle (Speicher). Keine neue Funktion, daher kein Eintrag in `docs/konnektor.md`. |
| 5 Herkunft | Anlegen und Umschalten erzeugen einen Anfangsvorgang mit Person und Zeit (Verlauf bleibt nur anhängend). |
| 6 Rollen entscheiden | Rollenprüfung beim Anlegen unverändert (wer eine Reise anlegen darf, entscheidet die Rolle wie bisher). |
| 7 IDs und Verlauf | Nur anhängend; Umschaltung verändert keine IDs, nichts wird gelöscht. |
| 8 PWA | Seite und Service Worker unverändert; Seiten kommen aus demselben Generator. Der Fuß „Stand noch nicht auf dem Server“ bleibt. |
| 9 Claude Code | Keine Reiseinhalte in Claude Code. |
| 10 Dokumentation | Diese Spec, `docs/betrieb.md` (Bauordner, Veröffentlichen, Anstoß, Überwachung, Einrichten, Umzug, Rückweg), ADR-0009 (Zeile #454), Kopfkommentare der Skripte. |

## Verhalten

### Lieferung 1: Alle Reisen im Speicher

- `instanz.speicherreisen()` gibt die Reisen mit Eintrag im Reisespeicher zurück (sortiert, ohne Duplikate). `FR_SPEICHERREISEN` wird gelesen und ignoriert (kein Fehler, keine Wirkung).
- `reise_anlegen` (und damit `trip_create`) legt Anfangsvorgang im Speicher an; `schreiben.py` wählt für diese Reise den Speicherweg.
- Pro Lauf von `veroeffentlichen.sh`, vor dem Speicher-Teil: für jede Reise im Bauordner `reisen/<name>/reise.json`, die nicht im Speicher steht, wird `reisespeicher.umschalten_automatisch(reise)` aufgerufen: Anfangsvorgang aus Git anlegen, Vergleich, Stempel. Ergebnis „gleich“: Reise ist im Speicher, ab jetzt gilt der Speicherweg. Ergebnis „unterschiedlich“ oder Fehler: Reise bleibt in Git, Warnzeile mit Grund, Lauf bleibt grün.
- Beim Bau läuft für jede Speicherreise unverändert der Speicher-Teil (Sperre `umschaltung_frei` aus #350 bleibt als Absicherung).

### Lieferung 2: Software direkt

Ablauf eines Laufs von `veroeffentlichen.sh` (nach dem Umzug):

1. Umzug prüfen (Entscheidung 10); ist er `fertig`, weiter.
2. `git fetch origin main` im Software-Klon. Scheitert er, ist das wie heute kein Fehler des Laufs (Speicher-Teil läuft, Warnung entprellt über `software-wartet`, #350).
3. Neuer Commit `C`: Nachweis (oder Tests im Arbeitsbaum) vor dem Umschalten (Entscheidung 5). Rot: Rot-Datei, Klon unverändert, Speicher-Teil läuft weiter mit der bisherigen Software.
4. Grün: Klon vorspulen (`git merge --ff-only`), `deploy.sh`, Speicher-Teil und Bau, Stempel `veroeffentlicht` = `C`, `software-gut` = `C`, Heartbeat nur bei vollem Erfolg (Readiness).
5. Ändert sich das Skript selbst durch das Vorspulen, Neustart mit `exec "$0"` (alles in `main()`).

Der Git-Teil des Reisen-Repos (Fetch, `reisen_des_laufs`, `git_reisen_uebrig`, `tests/` des Reisen-Repos, `software_anstossen`) entfällt im neuen Weg. `anstoss_weitergeben` stößt nur noch einen Lauf an.

## Acceptance Criteria

### Lieferung 1 (alle Reisen im Speicher)

- **AC-1.1:** *Given* der Speicher enthält Reisen und `FR_SPEICHERREISEN` ist leer oder nennt andere Namen, *when* `instanz.speicherreisen()` aufgerufen wird, *then* sind es genau die Reisen mit Eintrag im Speicher.
- **AC-1.2:** *Given* `FR_SPEICHERREISEN` ist in der Umgebung oder Einstellungsdatei gesetzt, *when* eine Reise nicht im Speicher steht, *then* gilt sie nicht als Speicherreise (Wert wirkungslos, keine Fehlermeldung).
- **AC-1.3:** *Given* der Speicher ist nicht lesbar, *when* `speicherreisen()` aufgerufen wird, *then* wird ein Fehler ausgelöst (fail closed, #361), nie eine leere Liste.
- **AC-1.4:** *Given* eine Speicher-Instanz, *when* `reise_anlegen` für die Vorlage der Beispielreise (Wanderung) und für das Stadtwochenende aufgerufen wird, *then* liegt jeweils ein Anfangsvorgang im Speicher und kein Ordner `reisen/<name>` im Bauordner.
- **AC-1.5:** *Given* eine neu angelegte Reise, *when* der Lauf des Veröffentlichens läuft, *then* baut der Speicher-Teil sie und die Seite wird veröffentlicht, ohne dass der Git-Teil sie anfasst.
- **AC-1.6:** *Given* eine Reise liegt in Git und ist inhaltsgleich im Speicher darstellbar (beide Beispielreisen), *when* der Lauf läuft, *then* wird sie umgeschaltet: Anfangsvorgang, Stempel `gleich`, Reise steht in `speicherreisen()`, Lauf bleibt grün.
- **AC-1.7:** *Given* der Vergleich einer Git-Reise ergibt „unterschiedlich“ oder Fehler, *when* der Lauf läuft, *then* bleibt die Reise in Git, nichts wird gelöscht oder geändert, es gibt eine Warnzeile mit Grund und keine Meldung der Stufe `high`.
- **AC-1.8:** *Given* eine Reise ist schon umgeschaltet, *when* der Lauf erneut läuft, *then* ändert sich nichts (kein zweiter Anfangsvorgang, gleicher Stand).
- **AC-1.9:** *Given* die Umschaltung läuft, *when* sie nach dem Anfangsvorgang und vor dem Stempel abbricht, *then* gilt die Reise bis dahin weiter als Git-Reise, und der nächste Lauf setzt die Umschaltung fort: erneuter Vergleich gegen den vorhandenen Anfangsvorgang, bei „gleich“ Stempel; kein zweiter Anfangsvorgang, kein Handschritt.
- **AC-1.10:** *Given* eine Instanz, die vor Lieferung 1 Reisen über `FR_SPEICHERREISEN` im Speicher hatte, *when* die neue Software läuft, *then* bleiben diese Reisen im Speicher und ihre Seiten unverändert (kein Handschritt, #250).
- **AC-1.11:** *Given* die Schreib-Werkzeuge des Konnektors, *when* sie auf eine Reise im Speicher angewendet werden, *then* verhalten sie sich wie zuvor (Namen, Parameter, Texte unverändert).

### Lieferung 2 (Software direkt)

- **AC-2.1 (Abruf):** *Given* ein neuer Commit auf `main` der Software, *when* der Lauf läuft, *then* wird er ohne Reisen-Repo, ohne GitHub-Workflow der Instanz und ohne Anmeldung geholt und (nach Prüfung) eingespielt.
- **AC-2.2 (Prüfung vor Umschalten):** *Given* ein neuer Commit `C` ohne gültigen Nachweis, *when* die Tests auf dem Server rot sind, *then* zeigt `HEAD` des Klons weiter auf den bisherigen Commit, und der Arbeitsbaum des Klons ist unverändert.
- **AC-2.3 (Nachweis):** *Given* alle Pflichtprüfungen von `C` sind auf GitHub grün, *when* der Lauf läuft, *then* wird der Klon auf `C` vorgespult, ohne die Tests auf dem Server zu wiederholen.
- **AC-2.4 (Nachweis nur je Stand):** *Given* derselbe Commit `C` wird in mehreren Läufen gesehen, *when* der Nachweis fehlt, *then* wird er nur einmal je Stand abgefragt.
- **AC-2.5 (Rückfall):** *Given* `C` ist rot oder der Deploy mit `C` scheitert, *when* der Lauf endet, *then* arbeiten die Dienste weiter mit dem Commit aus `<FR_DIENST>/software-gut`, und die Seiten der Reisen bleiben auf ihrem letzten guten Stand.
- **AC-2.6 (Rot-Datei):** *Given* `C` ist rot, *when* der nächste Lauf denselben `C` sieht, *then* wird er nicht erneut geprüft („Bekannter roter Stand“), und erst nach Ablauf der Schwelle gibt es genau einen Alarm der Stufe `high` je Rot-Phase.
- **AC-2.7 (Kennung):** *Given* `veroeffentlicht` und `software_kennung`, *when* ein Lauf grün endet, *then* sind beide der Commit der Software, und `software-gut` trägt denselben Commit.
- **AC-2.8 (Nachziehen der Reisen):** *Given* ein neuer Software-Commit, *when* er veröffentlicht ist, *then* zieht der Speicher-Teil jede Reise (Wanderung und Stadtwochenende) auf die neue Kennung nach (`neu.py nachziehen-speicher`, nur bei grünem Probebau).
- **AC-2.9 (Einstellungen):** *Given* `<FR_DIENST>/instanz/einstellungen.env` liegt vor, *when* ein Skript startet, *then* kommen Einstellungen aus der Umgebung, sonst aus dieser Datei, sonst (Übergang) aus dem alten Ort.
- **AC-2.10 (Meldeweg):** *Given* `<FR_DIENST>/instanz/melden.sh`, *when* eine Meldung ausgelöst wird, *then* ruft `FR_MELDEN` diesen Weg auf; ohne Meldeweg wird nichts gesendet.
- **AC-2.11 (Python-Umgebung):** *Given* die Python-Umgebung liegt unter `<FR_DIENST>/python`, *when* der Klon umgeschaltet oder zurückgesetzt wird, *then* bleibt sie erhalten; ändert sich `requirements` im Commit, wird sie vor dem Umschalten der Dienste neu aufgebaut.
- **AC-2.12 (Umzug ohne Handschritt des Betreibers):** *Given* eine Instanz im alten Zustand (Submodul im Bauordner), *when* der Lauf mit der Software dieses Commits läuft, *then* legt er den Klon an, kopiert Einstellungen und Meldeweg, baut und prüft die Python-Umgebung, ohne dass jemand etwas tut; weichen die Units nur in gesperrten Zeilen ab (`ExecStart`, `FR_WURZEL`), bleibt er mit einer Warnzeile je Commit beim alten Weg, ohne die Units zu ändern. Sind die Units (einmalig bei der Auslieferung, Entscheidung 10, Schritt 4) auf den Klon umgestellt, läuft der nächste Lauf aus dem Klon, setzt den Zustand auf `fertig` und endet grün.
- **AC-2.13 (Units zuletzt):** *Given* ein Schritt des Umzugs (1 bis 3) scheitert oder die Prüfung der Units (`units.py pruefen`) meldet gesperrte Abweichungen (Lauf schreibt nur die Warnzeile, stellt nichts um), *when* der Lauf endet, *then* zeigen alle Units unverändert auf den alten Bauordner, das Veröffentlichen läuft weiter über den alten Weg, und der nächste Lauf versucht den Umzug erneut.
- **AC-2.14 (Wiederholbar):** *Given* der Umzug ist `fertig` oder halb durchgeführt, *when* der Lauf erneut läuft, *then* ändert er nichts Unnötiges (keine doppelten Kopien, kein Überschreiben neuerer Einstellungen, keine Units-Änderung ohne Unterschied).
- **AC-2.15 (Alter Bauordner bleibt):** *Given* der Umzug ist `fertig`, *when* der alte Bauordner betrachtet wird, *then* ist er unverändert (nichts gelöscht, keine Datei verändert); der Rückweg (Units bewusst mit `einrichten.sh --installieren` aus dem alten Bauordner zurückstellen, Zustand `alt`) ist in `docs/betrieb.md` beschrieben, und ein Lauf mit Zustand `alt` startet keinen neuen Umzug.
- **AC-2.16 (Selbstaustausch):** *Given* das Vorspulen des Klons ändert `veroeffentlichen.sh`, *when* der Lauf weiterläuft, *then* startet er mit `exec` das neue Skript neu und endet genau einmal mit einem Ergebnis (kein Mischlauf aus altem und neuem Code).
- **AC-2.17 (Anstoß):** *Given* die Seite legt `_anstoss.json` ab, *when* der Lauf es sieht, *then* startet er einen Lauf und ruft kein `gh workflow run` auf; die Anstoß-Datei wird danach gelöscht, ohne dass der Lauf endlos wiederholt wird.
- **AC-2.18 (Kein Git-Teil):** *Given* eine Instanz im neuen Zustand ohne Reisen-Repo und ohne `gh`, *when* der Lauf läuft, *then* endet er grün und ruft weder `gh` noch `git` auf dem Reisen-Repo auf (Fetch, Vorspulen, `software_anstossen`, `reisen_des_laufs`, Tests des Reisen-Repos).
- **AC-2.19 (Einrichtung):** *Given* eine neue Instanz, *when* `einrichten.sh` läuft, *then* verlangt es weder `gh auth` noch ein Reisen-Repo, legt den Klon und `<FR_DIENST>/instanz/` an und erzeugt Units mit den neuen Pfaden.
- **AC-2.20 (Alarm nur bei Ausfall):** *Given* ein Umzugsfehler, eine nicht umschaltbare Reise oder ein nicht abrufbarer Nachweis, *when* sie auftreten, *then* gibt es keine neue Meldung der Stufe `high`; die Liste `ALARMSTELLEN` in `test_betrieb.py` ändert sich nicht, und jede Meldung kommt höchstens einmal je Störung.
- **AC-2.21 (Auslieferungstor Infrastruktur):** *Given* Lieferung 2 soll auf eine Instanz, *when* der Monitor nur den alten Pfad (`.git/modules/frieda/HEAD`) kennt oder der Backup-Aufruf nur den alten Pfad von `sichern.sh`, *then* wird Lieferung 2 nicht ausgeliefert; das Issue im Infrastruktur-Repo ist abgeschlossen und verlinkt, bevor sie freigegeben wird.
- **AC-2.22 (Instanz-Tests):** *Given* `<FR_DIENST>/instanz/tests/` fehlt, *when* der Lauf läuft, *then* wird ohne Fehler übersprungen; liegt es vor und ist rot, gibt es eine Warnung und keinen Abbruch des Wechsels.
- **AC-2.23 (Software ohne Instanzspezifisches):** *Given* die Software nach Lieferung 2, *when* nach Pfaden, Adressen, Benutzern gesucht wird, *then* kommt nichts Instanzspezifisches vor (Tests mit `einstellungen.beispiel` und den Beispielreisen; vorhandene Prüfungen `test_protokolle_ohne_pfade` und der Test auf Privates bleiben grün).
- **AC-2.24 (Doku):** *Given* `docs/betrieb.md`, *when* sie gelesen wird, *then* beschreiben die Abschnitte Bauordner, Veröffentlichen, Anstoß, Überwachung, Einrichten und Umzug den neuen Weg samt Rückweg; ADR-0009 nennt #454 in Stufe 5.

## Test Plan

TDD: erst RED (Tests unten laufen rot gegen den heutigen Stand), dann Umsetzung je Lieferung. Neue Datei `engine/tests/test_software_weg_454.py` (Fixtures bauen einen Software-Klon aus einem lokalen Bare-Repo ohne Submodul, Attrappen für `gh`, `git ls-remote` und das Root-Hilfsprogramm der Units; Reisen nur die Beispielreisen). Bestehende Fixtures `vf`, `an`, `sp`, `s5`, `repo`, `reisen_repo` werden auf die neue Anordnung umgestellt, ohne die Fälle der alten Anordnung zu verlieren, solange sie existiert (Übergang).

| AC | Test (Datei :: Testname) |
|---|---|
| AC-1.1 | `engine/tests/test_software_weg_454.py::test_speicherreisen_liest_aus_dem_speicher` |
| AC-1.2 | `engine/tests/test_software_weg_454.py::test_fr_speicherreisen_ist_wirkungslos` |
| AC-1.3 | `engine/tests/test_software_weg_454.py::test_speicherreisen_unlesbarer_speicher_ist_fehler` |
| AC-1.4 | `engine/tests/test_software_weg_454.py::test_reise_anlegen_entsteht_im_speicher[beispielreise]`, `[stadtwochenende]` |
| AC-1.5 | `engine/tests/test_software_weg_454.py::test_neue_reise_wird_vom_speicher_teil_gebaut` |
| AC-1.6 | `engine/tests/test_software_weg_454.py::test_git_reise_wird_bei_gleich_umgeschaltet[beispielreise]`, `[stadtwochenende]` |
| AC-1.6/1.7 im Lauf | `engine/tests/test_software_weg_454.py::test_lauf_schaltet_git_reise_bei_gleich_um`, `::test_lauf_laesst_ungleiche_git_reise_mit_warnung_in_git` |
| AC-1.7 | `engine/tests/test_software_weg_454.py::test_git_reise_bleibt_bei_unterschied_in_git` |
| AC-1.8 | `engine/tests/test_software_weg_454.py::test_umschaltung_ist_idempotent` |
| AC-1.9 | `engine/tests/test_software_weg_454.py::test_umschaltung_nach_abbruch_wird_fortgesetzt` |
| AC-1.10 | `engine/tests/test_software_weg_454.py::test_bisherige_speicherreisen_bleiben_ohne_handschritt` |
| AC-1.11 | `engine/tests/test_software_weg_454.py::test_schreibwerkzeuge_speicherreise_unveraendert` (bestehende Tests in `test_schreiben.py` grün, dazu dieser) |
| AC-2.1 | `engine/tests/test_software_weg_454.py::test_neuer_commit_wird_ohne_reisen_repo_geholt` |
| AC-2.2 | `engine/tests/test_software_weg_454.py::test_roter_commit_laesst_klon_unveraendert` |
| AC-2.3 | `engine/tests/test_software_weg_454.py::test_nachweis_gruen_spult_klon_vor_ohne_server_tests` |
| AC-2.4 | `engine/tests/test_software_weg_454.py::test_nachweis_wird_je_stand_nur_einmal_abgefragt` |
| AC-2.5 | `engine/tests/test_software_weg_454.py::test_rueckfall_auf_letzten_guten_stand` |
| AC-2.6 | `engine/tests/test_software_weg_454.py::test_rot_datei_am_software_commit_ein_alarm_je_rot_phase` |
| AC-2.7 | `engine/tests/test_software_weg_454.py::test_stempel_und_kennung_sind_software_commit` |
| AC-2.8 | `engine/tests/test_software_weg_454.py::test_reisen_werden_nach_neuer_kennung_nachgezogen[beispielreise]`, `[stadtwochenende]` |
| AC-2.9 | `engine/tests/test_software_weg_454.py::test_einstellungen_reihenfolge_umgebung_instanz_alter_ort` |
| AC-2.10 | `engine/tests/test_software_weg_454.py::test_meldeweg_aus_instanz_ordner` |
| AC-2.11 | `engine/tests/test_software_weg_454.py::test_python_umgebung_ausserhalb_des_klons` |
| AC-2.12 | `engine/tests/test_software_weg_454.py::test_umzug_ohne_handschritt`, `::test_umzug_mit_umgestellten_units_im_alten_lauf_wird_fertig`, `::test_lauf_aus_dem_klon_setzt_umzug_fertig` |
| AC-2.13 | `engine/tests/test_software_weg_454.py::test_umzug_scheitert_vor_units_alles_beim_alten`, `::test_umzug_units_abweichend_nur_warnung_keine_umstellung`, `::test_f004_umzug_prueft_je_commit_einmal_und_warnt_einmal` |
| AC-2.14 | `engine/tests/test_software_weg_454.py::test_umzug_ist_wiederholbar` |
| AC-2.15 | `engine/tests/test_software_weg_454.py::test_alter_bauordner_bleibt_und_ist_rueckweg`, `::test_zustand_alt_startet_keinen_umzug`, `::test_rueckweg_und_einmalige_umstellung_in_betrieb_md` |
| AC-2.16 | `engine/tests/test_software_weg_454.py::test_skript_startet_sich_nach_umschalten_neu` |
| AC-2.17 | `engine/tests/test_software_weg_454.py::test_anstoss_startet_nur_einen_lauf` |
| AC-2.18 | `engine/tests/test_software_weg_454.py::test_lauf_ohne_reisen_repo_und_ohne_gh` |
| AC-2.19 | `engine/tests/test_software_weg_454.py::test_einrichten_ohne_gh_und_reisen_repo` |
| AC-2.20 | `engine/tests/test_betrieb.py::test_alarmstellen_sind_begruendet` (bestehend), Liste geprüft in `engine/tests/test_software_weg_454.py::test_umzugsfehler_und_nachweis_sind_keine_high_meldung` |
| AC-2.21 | `engine/tests/test_software_weg_454.py::test_dokumentierte_infra_vorbedingung` (prüft, dass `docs/betrieb.md` die Vorbedingung und die zwei Stellen nennt); Abnahme des Auslieferungstors im Infrastruktur-Issue |
| AC-2.22 | `engine/tests/test_software_weg_454.py::test_instanz_tests_fehlen_oder_rot_sperren_nicht` |
| AC-2.23 | `engine/tests/test_protokolle_ohne_pfade.py` (bestehend) und `engine/tests/test_software_weg_454.py::test_keine_instanzspezifischen_werte_in_betrieb` |
| AC-2.24 | `engine/tests/test_software_weg_454.py::test_betrieb_md_beschreibt_neuen_weg` |

Weitere Prüfungen:

- Die bestehenden Tests von `test_betrieb.py`, `test_software_nachziehen.py`, `test_speicher_stufe5.py`, `test_schreiben.py`, `test_stand.py` bleiben grün (mit angepassten Fixtures); die Modulliste in `betrieb/deploy.sh` stimmt mit den Modulen überein (kein neues eigenes Modul vorgesehen; entsteht eines, kommt es in die Liste, ein vorhandener Test prüft das).
- Texte nur im Katalog (`engine/tests/test_texte.py`, Ausnahmelisten nur kürzer).
- Instanz-Lauf in `.github/workflows/tests.yml` ohne Superprojekt (`FR_WURZEL` = Software-Klon).
- Beide Reisetypen (ADR-0001): Jede Funktion gegen Wanderung und Stadtwochenende.
- Tests der einbindenden Instanz laufen vor dem Vorspulen mit dem Branch (Umgebungswerte und Dateiformate ändern sich; Anleitung im Reisen-Repo der Instanz).
- Live (Lieferung 1): Ein Lauf ohne Fehler, neue Testreise (die vorhandene wiederverwenden) entsteht im Speicher und erscheint auf der Seite; übrige Git-Reisen sind umgeschaltet oder mit Grund gewarnt.
- Live (Lieferung 2, nach Auslieferungstor): Umzug in einem Lauf, danach Veröffentlichen, Wächter und Schreibweg über die neuen Pfade; Rückfall und Rückweg einmal an einer Testinstanz oder mit Attrappen durchgespielt, nie an echten Reisen.

## Definition of Done

- [ ] Alle Tests aus dem Test Plan geschrieben, zuerst rot, dann grün; gesamte Testsuite grün (lokal und CI, Pflichtprüfungen)
- [ ] Tests der einbindenden Instanz mit dem Branch grün
- [ ] Lieferung 1 auf der Instanz: keine Reise mehr in Git oder jede verbleibende mit Grund gewarnt; neue Reise entsteht im Speicher und erscheint auf der Seite
- [ ] Infrastruktur-Issue (Monitor, Backup-Pfad) umgesetzt und in #454 verlinkt (Auslieferungstor AC-2.21)
- [ ] Lieferung 2 auf der Instanz: Umzug (Schritte 1–3) ohne Handschritt des Betreibers gelaufen, Units einmalig bei der Auslieferung umgestellt, Veröffentlichen, Wächter, Schreibweg und Kartendienst über die neuen Pfade grün
- [ ] `docs/betrieb.md` und ADR-0009 aktualisiert
- [ ] Folge-Issue für den Rückbau des Git-Wegs angelegt und in #454 verlinkt

## Risiken

| Risiko | Maßnahme |
|---|---|
| Pfadwechsel aller Units (Hauptrisiko) | Units als letzter Schritt; Schritte 1 bis 3 vorher geprüft; alter Bauordner unangetastet; Rückweg über denselben Mechanismus; Umzug wiederholbar (AC-2.12 bis AC-2.15) |
| Skript ändert sich unter sich selbst | alles in `main()`, `exec "$0"` nach dem Vorspulen (Muster #242, AC-2.16) |
| Abfrage der Prüfergebnisse ohne Anmeldung auf 60 je Stunde begrenzt | nur einmal je neuem Stand; Rückfall: Tests auf dem Server im eigenen Arbeitsbaum (AC-2.3, AC-2.4) |
| Infra kennt den neuen Pfad nicht: falscher Alarm des Monitors oder Backup ohne frischen Schnappschuss | Vorbedingung und Auslieferungstor (AC-2.21); beide Anordnungen zulassen |
| Reise liegt noch in Git, wenn das Reisen-Repo nicht mehr gebaut wird | Lieferung 1 zuerst; automatische Umschaltung; Lieferung 2 erst nach Lieferung 1 auf der Instanz (Entscheidung 1) |
| Instanz-Einstellungen verlieren ihr versioniertes Zuhause | `<FR_DIENST>/instanz/`, vom Backup erfasst; Kopie beim Umzug nie überschreibend (AC-2.9, AC-2.14) |
| Meldungen werden zu laut | nur `high` bei Rot-Phase; alles andere Warnzeile oder `normal`, entprellt (#446, AC-2.20) |
| Halber Wechsel legt Veröffentlichen still | Zustand wird bei jedem Lauf neu gelesen; Fortsetzen oder Zurücknehmen (Entscheidung 14) |

## Known Limitations

- Zu AC-1.7 und AC-1.9 (Adversary F005/F008): Ist die Umschaltung offen und liegen im Speicher nur Import-Vorgänge, hängt der Lauf den aktuellen Git-Stand als weiteren Import-Vorgang an (nur anhängen, ADR-0009; nichts wird gelöscht) und vergleicht erneut; bei „gleich“ wird gestempelt. Sonst bliebe die Reise nach einer Änderung in Git dauerhaft offen (Handschritt, #250). Gibt es andere Vorgänge, gilt AC-1.7 unverändert.

## Changelog

- 2026-11-13 (RED zur Entscheidung PO): Tests zu AC-2.12, AC-2.13, AC-2.15 an die einmalige Umstellung der Units angepasst und ergänzt (Testplan).
- 2026-11-13 (Entscheidung PO nach Validierung): Units-Schritt des Umzugs nach Entscheidung des Product Owners einmalig bei der Auslieferung durch den Tech Lead, Erlaubnisliste unverändert (Entscheidung 10, AC-2.12, AC-2.13, AC-2.15). Infrastruktur-Issue für AC-2.21: henemm-infra#436.
- 2026-11-13: AC-1.7 um die Ausnahme der offenen Umschaltung mit nur Importen ergänzt (Adversary F005/F008); Prüfung vor dem Umschalten mit eigener Python-Umgebung, Rückfall nur bei rotem Dienst-Deploy (F002, F003).
- 2026-11-12: Affected Files, ADR, Definition of Done ergänzt; offene Umschaltung (AC-1.9) eindeutig festgelegt.
- 2026-11-12: Erstfassung (Spec zu #454, zwei Lieferungen, Folge-Issue für den Rückbau des Git-Wegs).
