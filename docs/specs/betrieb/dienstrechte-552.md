---
entity_id: dienstrechte-552
type: feature
created: 2026-11-13
updated: 2026-11-13
status: draft
version: "1.0"
tags: [betrieb, sicherheit, systemd, nginx, rollen]
workflow: sicherheit-552-dienstrechte
---

# Rechte des Dienstbenutzers enger fassen, Härtung an nginx und Units (#552)

Grundlage: `docs/context/sicherheit-552-dienstrechte.md` (Kontext, Analyse, Befund). Vorbild für den neuen Root-Helfer: `docs/specs/betrieb/nginx-orte-automatisch-445.md`. Meldeweg bleibt wie in `docs/specs/betrieb/meldeweg-nur-ausfaelle-446.md`.

## Approval

- [ ] Approved

## Purpose

Rest der Sicherheitsprüfung vom 12.11.2026 (Punkte 2 und 6 und der Rest von K3 im privaten Issue der Instanz): Die aus dem Netz erreichbaren Dienste (Konnektor, Rückmeldedienst, Push) dürfen weder über `sudo` noch über Docker an Root-Rechte kommen; der Schreibweg darf keine Dateien im Home-Verzeichnis ändern, die später mit höheren Rechten laufen; `/token` und `/register` bekommen eine Drossel; Sperrdateien liegen nicht mehr im gemeinsamen `/tmp`; und die Rolle einer Person wird bei Einladen, Erledigen und Einplanen gegen den aktuellen Stand der Reise geprüft, nicht gegen den veröffentlichten. Software-Wechsel laufen dabei weiter ohne Handarbeit (Entscheidung des Product Owners, 13.11.2026).

## Entscheidungen (Tech Lead, nicht offen)

1. **Kein Umzug der ganzen Instanz** auf einen neuen Benutzer (großer Umzug, Ausfallrisiko). `docs/betrieb.md` empfiehlt für neue Instanzen einen eigenen Dienstbenutzer ohne Admin-Rechte und warnt: Ist der Dienstbenutzer zugleich Server-Admin (weites `sudo`), heben sich die schmalen Regeln dieser Spec auf; sie schützen dann vor Fehlern, nicht vor einem übernommenen Dienst.
2. **Netzdienste** (`konnektor`, `rueckmeldungen`, `push`): `NoNewPrivileges=yes` (vorhanden) plus `InaccessiblePaths=-/run/docker.sock`.
3. **Root nur über feste Helfer mit Grammatik** (Einheiten, nginx-Orte, neu nginx-Reise); keine `sudo`-Regel mehr für `install`, `test`, `cat`, `rm`, `nginx -t`, Reload.
4. **Kartendienst** läuft unter eigenem Benutzer `<instanz>-karte`; der Dienstbenutzer ist nicht mehr in der Gruppe `docker`; Root- und Karte-Einheiten führen kein vom Dienstbenutzer beschreibbares Skript und keine von ihm beschreibbare Umgebungsdatei aus.
5. **Schreibweg** mit `ProtectSystem=strict`, `ProtectHome=read-only` und gemessenen `ReadWritePaths`.
6. **Drossel** für `/token` und `/register` mit der vorhandenen Zone `_mcp`.
7. **Sperren** in `FR_DIENST` statt `/tmp`.
8. **Unit-Änderungen nicht in `ERLAUBT`** (Sandbox-Werte wie `ReadWritePaths` können Rechte öffnen): einmalige Installation je Instanz mit `einrichten.sh --installieren` (Root). Die Umstellung der Instanz gehört zu „fertig“.
9. **Lesen der installierten nginx-Bausteine ohne sudo** (Nachtrag aus der Umsetzung): `nginx.py pruefen` las die Bausteine der Instanz mit `sudo cat`; diese Regel entfällt (Entscheidung 3). Stattdessen installieren alle Wege (Orte-Helfer, Reise-Helfer, `nginx.py anwenden`) die Bausteine der Instanz mit `0640 root:<FR_GRUPPE>`, und `einrichten.sh --installieren` stellt vorhandene einmalig so um. Der Dienstbenutzer kennt ihren Inhalt ohnehin aus den Einstellungen; Schreiben bleibt Root vorbehalten.
10. **Kartendienst-Daten im Zustandsordner des Karte-Benutzers** (Nachtrag): Das Umschalten des Datenordners braucht Schreibrecht im Elternordner; der Elternordner von `FR_KARTENDIENST_ORDNER` ist auf einer Instanz meist der Instanzordner und darf nicht dem Karte-Benutzer gehören. Darum liegen die Daten unter `/var/lib/<instanz>-kartendienst/`, und `FR_KARTENDIENST_ORDNER` wird ein root-eigener Verweis dorthin, angelegt und die vorhandenen Daten umgezogen von `einrichten.sh --installieren`, ohne Handschritt.
11. **Restrisiko Bauordner** (Nachtrag): Der Schreibweg braucht weiter Schreibrecht auf den Bauordner mit `.git` (Schreibkopie ist ein Worktree davon, Veröffentlichen läuft als sein Kindprozess). Seit #454 gilt dasselbe für `<FR_DIENST>/python` und `<FR_DIENST>/instanz`. Die vollständige Trennung (eigener Klon, Anstoß über systemd, danach `ReadOnlyPaths` für diese Ziele) wird nicht gebaut: **Entscheidung des Product Owners (13.11.2026)**, das Restrisiko wird angenommen, weil es nur nach zwei aufeinanderfolgenden Schwachstellen (Konnektor, dann Codeausführung im Schreibweg) greift und der Aufwand groß ist (#555 geschlossen).

## Source

- **Files:** `betrieb/vorlagen/nginx-reise-installieren.py` (neu), `betrieb/freischalten.sh`, `betrieb/nginx.py`, `betrieb/einrichten.sh`, `betrieb/gemeinsam.sh`, `betrieb/kartendienst.sh`, `betrieb/vorlagen/*.service`, `betrieb/vorlagen/kartendienst/*`, `betrieb/vorlagen/nginx-konnektor-orte.inc`, `engine/schreiben.py`, `engine/konnektor.py`, `engine/rueckmeldungen.py`, `docs/betrieb.md`
- **Identifier:** `nginx-reise-installieren`, `Schreiber.rolle_lesen`, `rolle_aktuell`, `sperrdatei`, `FR_SPERREN`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/vorlagen/nginx-orte-installieren.py` | Helfer | Muster für Grammatik, Sicherung, `nginx -t` mit Rückweg, Ausgänge |
| `betrieb/vorlagen/units-installieren.py`, `betrieb/units.py` (`ERLAUBT`) | Helfer | bleiben unverändert; neue Unit-Werte sind gesperrte Abweichungen |
| `betrieb/einrichten.sh --erzeugen/--installieren` | Skript | erzeugt und installiert Helfer, Units, sudoers-Zeilen |
| `betrieb/messlauf-schreibweg.py` | Skript | misst alle Schreibziele des Schreibwegs für `ReadWritePaths` |
| `engine/schreiben.py` (`wer_pruefen`, Lesekopie wie in `kartenpunkte_vorab`) | Modul | Rolle aus `reise.yaml` des aktuellen Stands |
| `engine/neu.py nachziehen` | Befehl | Betriebs-Umstellung ohne Handschritt (#250) |
| systemd, nginx, sudo, Docker | Fremd | Sandbox-Optionen, Orte, Rechte |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/vorlagen/nginx-reise-installieren.py` | CREATE | Root-Helfer für den Baustein einer Reise (Ablauf siehe unten) |
| `betrieb/freischalten.sh` | MODIFY | statt `sudo test/install/cat/rm`, `nginx -t`, Reload nur der Helfer-Aufruf; Rechteprüfung auf den Helfer |
| `betrieb/nginx.py` | MODIFY | Reise-Bausteine nicht mehr per `sudo cat` lesen, sondern direkt (Bausteine der Instanz sind für `FR_GRUPPE` lesbar, Entscheidung 9); `anwenden` installiert mit `0640 root:<FR_GRUPPE>` |
| `betrieb/einrichten.sh` | MODIFY | Helfer erzeugen und installieren; sudoers nur noch Helfer und `systemctl restart`; kein `usermod -aG docker`; Benutzer `<instanz>-karte` |
| `betrieb/vorlagen/{konnektor,rueckmeldungen,push}.service` | MODIFY | `InaccessiblePaths=-/run/docker.sock`; `rueckmeldungen` erhält die Adresse des Schreibwegs |
| `betrieb/vorlagen/schreiben.service` | MODIFY | `ProtectSystem=strict`, `ProtectHome=read-only`, `ReadWritePaths=` (gemessen), `InaccessiblePaths=-/run/docker.sock` |
| `betrieb/vorlagen/kartendienst/*` | MODIFY | `User=<instanz>-karte`; Aktualisieren führt ein root-eigenes, beim Einrichten erzeugtes Skript aus, liest keine Umgebungsdatei des Dienstbenutzers |
| `betrieb/kartendienst.sh`, `betrieb/gemeinsam.sh`, `engine/schreiben.py` (`sperrdatei`) | MODIFY | Vorgabe von `FR_SPERREN` ist `FR_DIENST`, nicht `/tmp` |
| `betrieb/kartendienst-umzug.sh` | CREATE | einmaliger Umzug der Kartendaten nach `/var/lib/<instanz>-kartendienst/` mit root-eigenem Verweis (Entscheidung 10), wiederholbar |
| `betrieb/vorlagen/nginx-orte-installieren.py` | MODIFY | Bausteine mit `0640 root:<FR_GRUPPE>` (Entscheidung 9) |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | MODIFY | `limit_req zone=_mcp burst=40 nodelay;` für `/token` und `/register` |
| `engine/schreiben.py` | MODIFY | lesende Rollenabfrage `GET /<reise>/rolle` (`Schreiber.rolle_lesen`) |
| `engine/rueckmeldungen.py` | MODIFY | `rolle_aktuell(reise, person, name)`; Wunsch einplanen prüft damit |
| `engine/konnektor.py` | MODIFY | `einladen_per_mail`: erst Schreibweg, dann Mail und `einladungen.json`; `rueckmeldung_erledigen` prüft mit `rm.rolle_aktuell` |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | neue Meldungen (Rolle nicht prüfbar, Rolle nicht mehr ausreichend) |
| `engine/neu.py` | MODIFY | `nachziehen` bringt den Sperrort der Instanz auf den neuen Stand (falls dort gesetzt) |
| `docs/betrieb.md` | MODIFY | neuer Weg, Einmalschritt, Kartendienst-Benutzer, Warnung zum Admin-Benutzer |
| `engine/tests/test_nginx_reise_helfer.py` | CREATE | Grammatik und Rückweg des Helfers |
| `engine/tests/test_betrieb.py`, `test_units.py`, `test_nginx.py`, `test_nginx_helfer.py`, `test_kartendienst.py`, `test_schreiben.py`, `test_konnektor.py`, `test_rueckmeldungen.py`, `test_neu.py`, `test_texte.py` (vorhanden, nur ausgeführt) | MODIFY | je Kriterium unten |

### Estimated Changes

- Files: ca. 22
- LoC: +750/-130 (davon ca. 320 Tests, ca. 250 Helfer)
- Risiko mittel: betrifft Freischalten neuer Reisen, Schreibweg, Kartendienst; Fehler stoppen Veröffentlichen oder Schreiben, zerstören aber keine Daten (Helfer mit Sicherung und Rückweg).

## Implementation Details

### Netzdienste und Docker

`konnektor`, `rueckmeldungen`, `push` bekommen `InaccessiblePaths=-/run/docker.sock` (das Minus: kein Fehler, wo der Socket fehlt). `NoNewPrivileges=yes` bleibt; damit ist `sudo` aus diesen Prozessen gesperrt. Der Dienstbenutzer verlässt die Gruppe `docker` (`einrichten.sh` führt kein `usermod -aG docker` mehr aus und sagt in der Ausgabe, dass bestehende Mitgliedschaften zu entfernen sind).

### Helfer `nginx-reise-installieren.py`

Nach dem Muster von `nginx-orte-installieren.py`, `#!/usr/bin/python3 -I`, nur Standardbibliothek, `/usr/local/sbin/<instanz>-nginx-reise-installieren`, root:root, 0755:

- **Eingabe:** stdin genau ein Reisename, Muster `^[a-z0-9][a-z0-9-]{1,39}\Z` (die Reise-Namen der Software), keine Argumente außer dem Lesemodus (siehe unten); alles andere Ausgang 3.
- **Eingebacken** (von `einrichten.sh` eingesetzt, nie aus dem Repo, der Umgebung oder der Eingabe gelesen): Vorlage des Bausteins, Seitenordner, Port des Rückmeldedienstes, Zone, Instanz, Snippets-Ordner.
- **Token** erzeugt der Helfer selbst (`secrets`); ein vorhandener Baustein behält seinen Token (der Helfer liest ihn selbst mit `O_NOFOLLOW`, regulär, root-eigen). Der Token verlässt den Helfer nie.
- **Ablauf:** Sperre (`flock`, nicht blockierend), Baustein bauen, byteweise gleich: Ausgang 2; sonst Sicherung in `/var/lib/<instanz>-nginx-sicherung/` (root, 0700, die letzten 20), atomar ersetzen (0640 root), `nginx -t`, bei Fehler Rückweg und zweiter `nginx -t`, sonst `systemctl reload nginx`; Ausgänge wie bei den Orten (0, 2, 3, 4, 5, 6). Ausgabe auf stdout nur der Pfad des Bausteins.
- **Lesemodus** (ersetzt `sudo cat`): Aufruf mit dem einzigen Argument `--pfad` und dem Reisenamen auf stdin gibt nur den Pfad des vorhandenen Bausteins aus (Ausgang 0) oder Ausgang 2, wenn keiner da ist. Der Link der Reise steht sonst in `seiten.json`; die Software braucht den Inhalt des Bausteins nicht mehr zu lesen.
- Entfernen eines Bausteins (bisher `sudo rm`): Argument `--entfernen` mit Reisename auf stdin, gleiche Sicherung, `nginx -t` und Reload.

`freischalten.sh` und `nginx.py` rufen nur noch `$FR_SUDO <helfer>` (Vorgabe `/usr/local/sbin/<instanz>-nginx-reise-installieren`); in `betrieb/*.sh` und `betrieb/nginx.py` steht danach kein `sudo install`, `sudo test`, `sudo cat`, `sudo rm`, `sudo nginx` oder `sudo systemctl reload` mehr. `einrichten.sh` installiert den Helfer, die genannten sudoers-Zeilen nennen nur die Helfer (Einheiten, Orte, Reise) und `systemctl restart` der eigenen Dienste.

### Kartendienst

Eigener Benutzer `<instanz>-karte` (ohne Login, in der Gruppe `docker`) besitzt Datenordner und Docker-Aufrufe. `kartendienst.service` läuft unter ihm. `kartendienst-aktualisieren.service` führt `/usr/local/sbin/<instanz>-kartendienst` aus: eine root-eigene Kopie von `betrieb/kartendienst.sh` mit eingebackenen Werten, erzeugt von `einrichten.sh`; sie liest keine `betrieb.env` und kein Skript aus Ordnern des Dienstbenutzers. Die Sperre gegen das Veröffentlichen öffnet der Karte-Benutzer nur lesend (`flock` genügt ein lesend geöffneter Dateideskriptor); die eigene Sperre `<instanz>-kartendienst.lock` liegt in seinem Zustandsordner (`FR_SPERREN` dieser Einheit).

### Schreibweg-Sandbox

`ProtectSystem=strict`, `ProtectHome=read-only`, `InaccessiblePaths=-/run/docker.sock`; `ReadWritePaths=` nennt genau die gemessenen Schreibziele: Schreibkopie, Bauordner einschließlich `.git`, `FR_DIENST`, `FR_KONTEN`, Reisespeicher, Sperren, und die Ablage der `gh`-Anmeldung, falls das Hochladen der Commits sie schreibend braucht. Die Liste entsteht aus einem Messlauf mit `betrieb/messlauf-schreibweg.py` unter diesen Optionen; jedes gemessene Ziel steht mit Begründung als Kommentar in der Vorlage. Der Schreibweg kann danach keine Shell-Profile und keine Skripte im Home ändern, die der Timer ohne `NoNewPrivileges` ausführt.

### Drossel und Sperren

`nginx-konnektor-orte.inc`: `limit_req zone=_mcp burst=40 nodelay;` bei `/token` und `/register` (großzügig, weil die Claude-App von gemeinsamen Adressen ruft); die Grammatik des Orte-Helfers erlaubt das schon, die Datei geht ohne Handschritt über ihn.
`gemeinsam.sh` (`FR_SPERREN:=…`), `kartendienst.sh` und `sperrdatei()` verwenden `FR_DIENST` als Vorgabe. Sperren sind flüchtig; es gibt nichts zu übertragen. Steht in der Instanz ausdrücklich `FR_SPERREN=/tmp`, entfernt `neu.py nachziehen` bzw. das Einrichten diese Zeile (je nachdem, wo sie steht; Test), damit die Vorgabe gilt.

### K3-Rest: Rolle gegen den aktuellen Stand

Befund im Code: Der Schreibweg prüft die Rolle schon richtig, `wer_pruefen` (`engine/schreiben.py`) liest `reise.yaml` der Arbeitskopie („reise.yaml gilt vor dem, was der Konnektor sagt“). Falsch gegen den veröffentlichten Stand (`daten.json`, kann hinterherhinken, wenn jemand gerade herabgestuft wurde) prüfen dagegen `einladen_per_mail` (nach `wer["rolle"]`, Mail und `einladungen.json` vor dem Schreibweg), `rueckmeldung_erledigen` (PATCH an den Rückmeldedienst, `rolle_von(z, …)` aus `daten.json`) und `wunsch_aendern` im Rückmeldedienst (Aktion `wunsch_einplanen`).

**Festgelegte Stelle:** eine lesende Rollenabfrage des Schreibwegs, keine neue Rechte-Logik im Konnektor.

- `Schreiber.rolle_lesen(reise, person, name)`: Lesekopie des aktuellen Stands (Speicher-Reise: `reisespeicher.exportieren` bis zur neuesten Nummer, Git-Reise: Kopie der Schreibkopie, sonst der Wurzel, dieselbe Quelle wie `wer_pruefen`; der Code wird aus `kartenpunkte_vorab` in eine gemeinsame Funktion `lesekopie` herausgelöst), dann dieselbe Auswertung wie `wer_pruefen` (Funktion `rolle_im_stand`, gemeinsam genutzt, damit es nur eine Quelle gibt). Antwort `{"rolle", "name", "status"}`; steht die Person nicht in `reise.yaml`, `{"rolle": null}`.
- Aufruf: `GET /<reise>/rolle?person=<schluessel>&name=<name>` am Schreibweg, mit Kopf `X-Frieda-Dienst` (wie `/buchung/…`), nur lesend, ohne Sperre, ohne Änderung.
- `rueckmeldungen.rolle_aktuell(reise, person, name)` ruft das auf (Adresse aus `KN_SCHREIBDIENST`, Unit `rueckmeldungen` bekommt denselben Wert); Konnektor und Rückmeldedienst nutzen diese eine Funktion.
- **Verhalten:** Die Rechteprüfung (`erlaubt`) läuft mit der Rolle aus dieser Antwort. Ist der Schreibweg bei der Instanz nicht eingerichtet, gilt wie bisher der veröffentlichte Stand. Ist er eingerichtet, aber nicht erreichbar oder liefert `rolle: null`, wird abgelehnt („Rolle nicht prüfbar, bitte später noch einmal“); nie still auf den veröffentlichten Stand zurückfallen.
- **`einladen_per_mail`:** Neue Person: erst `person_schreiben` über den Schreibweg (prüft die Rolle der Einladenden aus `reise.yaml`); scheitert er, Abbruch ohne Mail, ohne Konto-Verknüpfung und ohne `einladungen.json`; danach `einladungen.json`, dann Mail. Vorhandene Person (Verknüpfung mit einem Konto): vor `konten.einladen` Prüfung mit `rolle_aktuell` (nur Organisator:innen). `person_sichern` gibt den Fehler dafür zurück statt ihn nur zu protokollieren.
- **`rueckmeldung_erledigen`:** vor dem PATCH `rm.rolle_aktuell`; nur dort entscheidet die Maschine, der Rückmeldedienst bekommt den Namen wie bisher.
- **Wunsch einplanen:** in `wunsch_aendern` bei `eingeplant` in der Anfrage die Rolle aus `rolle_aktuell` statt `rolle_von(z, name)` (alle anderen Aktionen des Wunsches bleiben beim veröffentlichten Stand: sie sind ohne Folge für Dritte).
- **Begründung:** Der Schreibweg hat `reise.yaml` des aktuellen Stands ohnehin; eine zweite Rechtefunktion im Konnektor würde auseinanderlaufen. Die Abfrage ist lesend und billig im Vergleich zum Schreiben, und sie läuft nur bei diesen drei seltenen, folgenreichen Aktionen.

## Test Plan

### Automated Tests (TDD RED)

- [ ] Test 1 (AC-1): GIVEN die Vorlagen der drei Netzdienste WHEN sie gelesen werden THEN enthalten sie `NoNewPrivileges=yes` und `InaccessiblePaths=-/run/docker.sock`
- [ ] Test 2 (AC-2): GIVEN die Vorlage von `schreiben.service` WHEN sie gelesen wird THEN stehen `ProtectSystem=strict`, `ProtectHome=read-only`, `ReadWritePaths=` und `InaccessiblePaths=-/run/docker.sock` darin, und jeder Pfad der Liste stammt aus dem Messlauf
- [ ] Test 3 (AC-4 bis AC-7): GIVEN der neue Helfer mit umgelenkten Ordnern WHEN gültige und ungültige Reisenamen, fremder Token, Symlink, Sperre, Fehler bei `nginx -t` und Reload eingegeben werden THEN gelten die Ausgänge 0 bis 6 wie bei den Orten
- [ ] Test 4 (AC-8): GIVEN `betrieb/*.sh` und `betrieb/nginx.py` WHEN nach `sudo` gesucht wird THEN kommen nur die Helfer (Einheiten, Orte, Reise) und `systemctl restart` vor
- [ ] Test 5 (AC-9): GIVEN `einrichten.sh --erzeugen` WHEN es für die Beispielinstanz läuft THEN gibt es den Helfer ohne offene Platzhalter, die sudoers-Ausgabe nennt nur Helfer, und es steht kein `usermod -aG docker` für den Dienstbenutzer darin
- [ ] Test 6 (AC-10): GIVEN die Einheiten des Kartendienstes WHEN sie gelesen werden THEN laufen sie unter `<instanz>-karte` bzw. als Root-Einheit mit `ExecStart` in `/usr/local/sbin`, und kein `ExecStart` und kein `EnvironmentFile` liegt in einem Ordner des Dienstbenutzers
- [ ] Test 7 (AC-11): GIVEN die echte Orte-Vorlage WHEN sie durch die Grammatik des Orte-Helfers läuft THEN besteht sie, und `/token` und `/register` tragen `limit_req zone=_mcp burst=40 nodelay`
- [ ] Test 8 (AC-12): GIVEN keine gesetzte Einstellung WHEN Sperrdateien benannt werden THEN liegen sie in `FR_DIENST` (Schreibweg, `gemeinsam.sh`, `kartendienst.sh`), nie in `/tmp`
- [ ] Test 9 (AC-13): GIVEN `ERLAUBT` in `units.py` und im Einheiten-Helfer WHEN verglichen THEN enthält keine Liste eine Sandbox-Zeile (`ReadWritePaths`, `ProtectSystem`, `InaccessiblePaths`, `User`)
- [ ] Test 10 (AC-14): GIVEN eine Reise, deren `reise.yaml` eine Person auf Gast herabgestuft hat und deren veröffentlichter Stand sie noch als Organisator:in führt WHEN `GET /<reise>/rolle` aufgerufen wird THEN antwortet es mit `gast`
- [ ] Test 11 (AC-15): GIVEN die Herabgestufte WHEN sie `einladen_per_mail` aufruft THEN geht keine Mail hinaus, `einladungen.json` bleibt unverändert und es gibt keine Konto-Verknüpfung
- [ ] Test 12 (AC-16): GIVEN die Herabgestufte WHEN sie `rueckmeldung_erledigen` aufruft THEN wird sie abgelehnt und kein PATCH gesendet; GIVEN der Schreibweg ist nicht erreichbar THEN lehnt es mit „Rolle nicht prüfbar“ ab
- [ ] Test 13 (AC-17): GIVEN die Herabgestufte WHEN sie einen Wunsch einplant THEN antwortet der Rückmeldedienst mit 403 und das Brett bleibt unverändert
- [ ] Test 14 (AC-3): GIVEN `messlauf-schreibweg.py` und die Vorlage `schreiben.service` WHEN ihre Schreibziele verglichen werden THEN sind es dieselben (`test_betrieb.py::test_messlauf_deckt_readwritepaths`)
- [ ] Test 15 (AC-19): GIVEN `docs/betrieb.md` WHEN gelesen THEN nennt sie `nginx-reise-installieren` und `<instanz>-karte` und empfiehlt keine sudoers-Zeile für `install`, `cat`, `rm`, `nginx` (`test_betrieb.py::test_doku_beschreibt_dienstrechte`)
- [ ] Test 17 (AC-18): GIVEN die neuen Meldungen WHEN `test_texte.py` läuft THEN stehen sie in allen Sprachen, die Ausnahmelisten wachsen nicht (`test_texte.py::test_paritaet_schluessel_und_platzhalter`, vorhanden)
- [ ] Test 18 (AC-21): GIVEN Helfer und `nginx.py anwenden` mit Root-Rechten WHEN sie Bausteine der Instanz installieren THEN `0640 root:<FR_GRUPPE>`; `nginx.py pruefen` liest ohne sudo; `einrichten.sh --installieren` stellt vorhandene Bausteine einmalig um (Testnamen in AC-21)
- [ ] Test 19 (AC-22): GIVEN Kartendaten im alten Ordner WHEN der Umzug läuft THEN liegen sie im Zustandsordner hinter einem root-eigenen Verweis; ohne Daten, nach Abbruch und bei fremdem Verweis verhält er sich wie in AC-22 (Testnamen dort)
- [ ] Test 16 (AC-20): GIVEN umgelenkte Ziele WHEN `einrichten.sh --installieren` gegen eine Attrappe läuft THEN liegen Helfer, Units und sudoers-Datei dort mit den neuen Werten (`test_betrieb.py::test_einrichten_installieren_attrappe`)

### Schnittstellen aus der RED-Phase (festgelegt durch die Tests)

- **Reise-Helfer** (`engine/tests/test_nginx_reise_helfer.py`, Kopfkommentar dort): erzeugt von `einrichten.sh --erzeugen` als `sbin/<instanz>-nginx-reise-installieren` (Vorlage des Bausteins eingebacken, keine `__X__`-Platzhalter, kein `os.environ`/`getenv`). Funktionen `installieren(reise, snippets, sicherung, sperre, nginx, testen, neu_laden) -> (ausgang, pfad)`, `pfad_lesen(reise, snippets) -> str|None`, `entfernen(...) -> ausgang`, `main(argv, daten, **kw)`; argv `["helfer"]`, `["helfer","--pfad"]`, `["helfer","--entfernen"]`, sonst 3. Ausgabe auf stdout nur der Pfad `<reise>-<token>` (bei 0 und 2 des Installierens und im Lesemodus). Ein Baustein entspricht byteweise der bisherigen Ersetzung von `nginx-reise.conf`; ein von Hand angelegter Pfad bleibt.
- **freischalten.sh** (`test_nginx.py::test_reise_baustein_ueber_helfer`): ruft `$FR_SUDO $FR_NGINX_REISE_HELFER` (Vorgabe `/usr/local/sbin/<instanz>-nginx-reise-installieren`) mit dem Reisenamen auf stdin, ohne Argument; Ausgang 0 und 2 = Pfad auf stdout; anderer Ausgang: ERROR-Zeile, kein Link. Kein `FS_NGINX_TEST`/`FS_NGINX_LADEN` mehr.
- **messlauf-schreibweg.py**: Konstante `SCHREIBZIELE` = genau die Wörter der `ReadWritePaths=`-Zeilen in `vorlagen/schreiben.service` (mit Platzhaltern, u. a. `__DIENST__`, `__KONTEN__`); jedes Ziel steht zusätzlich in einem Kommentar der Vorlage.
- **einrichten.sh**: `--erzeugen` legt auch `sbin/<instanz>-kartendienst` (root-eigene Kopie von `kartendienst.sh`, ohne `betrieb.env`, ohne Pfade des Dienstbenutzers) an; Ausgabe nennt `useradd … <instanz>-karte`, `install -m 755 -o root -g root …/sbin/<instanz>-nginx-reise-installieren /usr/local/sbin/`, NOPASSWD-Zeilen nur `/usr/local/sbin/<instanz>-…` oder `/usr/bin/systemctl restart …`. `--installieren` installiert zusätzlich eine sudoers-Datei per `install … <datei> /etc/sudoers.d/<name>` (vorletztes Wort = erzeugte Datei).
- **Kartendienst-Units**: `kartendienst.service` mit `User=<instanz>-karte`; `kartendienst-aktualisieren.service` mit `ExecStart=/usr/local/sbin/<instanz>-kartendienst aktualisieren`, ohne `EnvironmentFile`. `kartendienst.sh` öffnet `veroeffentlichen.lock` mit `exec 9<"$FR_DIENST/veroeffentlichen.lock"`.
- **Rollenabfrage**: `Schreiber.rolle_lesen(reise, person, name) -> {"rolle", "name", "status"}` (Suche nach Schlüssel, ohne Schlüssel nach Namen ohne Groß-/Kleinschreibung; unbekannt: `{"rolle": None}`; keine Sperre, kein neuer Stand). `GET /<reise>/rolle?person=&name=`: ohne Kopf 403, ungültige Reise 404, sonst 200. Konnektor/Rückmeldedienst: Adresse aus `KN_SCHREIBDIENST`/`RM_SCHREIBDIENST`; nicht gesetzt = veröffentlichter Stand; gesetzt und nicht erreichbar = Ablehnung mit „nicht prüfbar“ (Vorschlag Schlüssel `dienst.rolle_nicht_pruefbar`). Die nachgestellten Schreibwege in `test_konnektor.py` (Klasse `Schreibweg`) und `test_regeln.py` (Klasse `Umgebung`) beantworten `/<reise>/rolle` schon.
- **Sperren**: `sperrdatei()` ohne `FR_SPERREN` in `FR_DIENST` (sonst `instanz.dienst()`); `neu.nachziehen` entfernt aus `<wurzel>/betrieb/einstellungen.env` genau die Zeile `FR_SPERREN=/tmp` bzw. `FR_SPERREN="/tmp"`.
- **Hinweis Umzug #454 (13.11.2026)**: Auf der Instanz liegen Software, Python und Einstellungen jetzt unter `<srv>/_software`, `<srv>/_dienst/python`, `<srv>/_dienst/instanz/`; `ReadWritePaths` und Messlauf bei der Umstellung (AC-3, AC-20) gegen diese Orte messen.

## Expected Behavior

- **Input:** Reisename (Helfer auf stdin), Anfragen an Konnektor und Rückmeldedienst wie bisher, `GET /<reise>/rolle?person=…` am Schreibweg (nur mit Dienstkopf).
- **Output:** Helfer: Pfad des Bausteins oder Ausgang 2 bis 6; Rollenabfrage: Rolle aus dem aktuellen Stand oder `null`; abgelehnte Aktionen mit einer Meldung aus dem Textkatalog.
- **Side effects:** Netzdienste und Schreibweg laufen in engerer Sandbox; Reise-Bausteine entstehen nur noch über den Helfer; Sperren liegen in `FR_DIENST`; `/token` und `/register` sind gedrosselt; Einladungen entstehen erst nach geprüftem Schreiben.

## Known Limitations

- Kein Umzug der ganzen Instanz auf einen eigenen Dienstbenutzer: Ist der Dienstbenutzer zugleich Admin des Servers, bleibt er es; die Härtung wirkt über die Sandbox der Dienste, nicht über die sudo-Regeln. Die Doku empfiehlt für neue Instanzen einen eigenen Benutzer.
- Die Unit-Änderungen brauchen je Instanz einmal Root (`einrichten.sh --installieren`), weil Sandbox-Zeilen bewusst nicht automatisch installiert werden.
- Ist der Schreibweg nicht eingerichtet, gilt für die Rollenprüfung weiter der veröffentlichte Stand.
- **Restrisiko Bauordner (Entscheidung 11, vom Product Owner am 13.11.2026 angenommen, #555 geschlossen):** Der Schreibweg behält Schreibrecht auf den Bauordner mit `.git`, auf `<FR_DIENST>/python` und `<FR_DIENST>/instanz`. Wer zuerst den Konnektor und danach den Schreibweg übernimmt, könnte dort Dateien ändern, die später mit mehr Rechten laufen. Eine vollständige Trennung wird nicht gebaut.

## Acceptance Criteria

Erfolgskriterien aus dem Issue (Kontext „Fertig, wenn“): ein übernommener Netzdienst kommt weder über `sudo` noch über Docker an Root-Rechte; der Schreibweg kann keine Dateien ändern, die später mit höheren Rechten laufen; `/token` und `/register` sind gedrosselt; Sperren liegen nicht in `/tmp`; die Rolle wird bei Einladen, Erledigen und Einplanen gegen den aktuellen Stand geprüft; Software-Wechsel brauchen weiter keine Handarbeit; die Instanz ist umgestellt.

- **AC-1:** (Netzdienste ohne Docker) GIVEN die Vorlagen von `konnektor`, `rueckmeldungen`, `push` WHEN sie erzeugt werden THEN enthält jede `NoNewPrivileges=yes` und `InaccessiblePaths=-/run/docker.sock`. Test: `test_betrieb.py::test_netzdienste_ohne_docker_und_sudo`.
- **AC-2:** (Schreibweg-Sandbox) GIVEN die Vorlage `schreiben.service` WHEN sie erzeugt wird THEN stehen `ProtectSystem=strict`, `ProtectHome=read-only`, `InaccessiblePaths=-/run/docker.sock` und eine `ReadWritePaths=`-Liste darin, die genau die Ziele des Messlaufs (Schreibkopie, Bauordner mit `.git`, `FR_DIENST`, `FR_KONTEN`, Reisespeicher, Sperren, ggf. `gh`-Anmeldung) enthält. Test: `test_betrieb.py::test_schreiben_unit_sandbox`.
- **AC-3:** (Messlauf) GIVEN die Instanz mit der neuen Unit WHEN `betrieb/messlauf-schreibweg.py` einen vollständigen Schreibvorgang samt Hochladen und Veröffentlichen ausführt THEN meldet er keinen verweigerten Schreibzugriff; das Protokoll des Laufs liegt unter `docs/artifacts/` (ohne Pfade der Instanz), das Issue verweist darauf. Test: `test_betrieb.py::test_messlauf_deckt_readwritepaths` (die Ziele, die `messlauf-schreibweg.py` prüft, und die `ReadWritePaths` der Vorlage sind dieselbe Liste). Ausnahme mit Begründung: Der Lauf selbst braucht systemd und die echte Instanz und läuft deshalb nicht in CI; er wird bei der Umstellung und nach jeder Änderung der Liste wiederholt, das Protokoll liegt unter `docs/artifacts/`.
- **AC-4:** (Reise-Helfer, Grammatik) GIVEN der Helfer WHEN die Eingabe kein Reisename nach Muster ist (Großbuchstaben, `..`, `/`, Leerzeichen, zu lang, leer, Zeilenumbruch, Argument) THEN Ausgang 3, nichts verändert, `nginx` nicht aufgerufen. Test: `test_nginx_reise_helfer.py::test_eingabe_grammatik`.
- **AC-5:** (Reise-Helfer, Token und Ersetzen) GIVEN eine Reise ohne Baustein WHEN der Helfer läuft THEN entsteht der Baustein (0640, root) mit einem neuen Token und die Ausgabe ist nur der Pfad; GIVEN ein vorhandener Baustein WHEN der Helfer erneut läuft THEN bleibt der Token gleich (Ausgang 2, wenn alles gleich, sonst Erneuerung mit gleichem Token). Test: `test_nginx_reise_helfer.py::test_token_bleibt`.
- **AC-6:** (Reise-Helfer, Rückweg) GIVEN `nginx -t` scheitert WHEN der Helfer ersetzt hat THEN steht der alte Baustein wieder, kein Reload, Ausgang 4; scheitert auch der zweite `nginx -t` oder das Zurückschreiben, Ausgang 6, Sicherung bleibt; scheitert der Reload, Ausgang 5. Test: `test_nginx_reise_helfer.py::test_rueckweg_und_ausgaenge`.
- **AC-7:** (Reise-Helfer, feste Umgebung) GIVEN gesetzte `PATH`, `PYTHON*` und ein vom Aufrufer geschriebener Eingabepfad WHEN der Helfer läuft THEN ändern sie nichts; Vorlage und Werte stammen nur aus der Datei. Der Lesemodus liefert nur den Pfad oder Ausgang 2, nie den Inhalt. Test: `test_nginx_reise_helfer.py::test_umgebung_fest`, `test_nginx_reise_helfer.py::test_lesemodus`.
- **AC-8:** (kein sudo außer Helfern) GIVEN `betrieb/*.sh` und `betrieb/nginx.py` WHEN nach `sudo` gesucht wird THEN stehen nur `$FR_SUDO <Helfer>` und `systemctl restart` der eigenen Dienste darin; `freischalten.sh` und `nginx.py` laufen gegen eine Attrappe des Helfers und legen Baustein, Link und `seiten.json` wie bisher an. Test: `test_betrieb.py::test_nur_helfer_mit_sudo`, `test_nginx.py::test_reise_baustein_ueber_helfer`.
- **AC-9:** (Einrichten) GIVEN `einrichten.sh --erzeugen` für die Beispielinstanz WHEN es läuft THEN gibt es Helfer und Karte-Skript ohne offene Platzhalter, die Ausgabe nennt Installationsbefehl und sudoers-Zeilen nur für Helfer, keinen `usermod -aG docker` für den Dienstbenutzer, aber Anlage und Gruppe von `<instanz>-karte`. Test: `test_betrieb.py::test_einrichten_helfer_und_karte`.
- **AC-10:** (Kartendienst) GIVEN die Kartendienst-Einheiten WHEN sie erzeugt werden THEN läuft Docker nur unter `<instanz>-karte`, und `ExecStart` und `EnvironmentFile` liegen weder im Repo noch in einem Ordner des Dienstbenutzers; die Sperre gegen das Veröffentlichen wird nur lesend geöffnet. Test: `test_kartendienst.py::test_kartendienst_ohne_dienstbenutzer`.
- **AC-11:** (Drossel) GIVEN die echte Orte-Vorlage WHEN sie die Grammatik des Orte-Helfers durchläuft THEN wird sie angenommen (Ausgang 0) und `/token` und `/register` tragen `limit_req zone=_mcp burst=40 nodelay`; `nginx.py pruefen` liest den installierten Baustein ohne sudo (für `FR_GRUPPE` lesbar, AC-21) und meldet bei der Instanz die Abweichung, `nginx.py installieren` behebt sie ohne Handschritt. Test: `test_nginx_helfer.py::test_echte_vorlage_mit_drossel`.
- **AC-12:** (Sperren) GIVEN keine ausdrückliche Einstellung WHEN `gemeinsam.sh`, `kartendienst.sh` und `sperrdatei()` Sperren benennen THEN liegen sie in `FR_DIENST`; GIVEN `FR_SPERREN=/tmp` in einer Instanz WHEN `neu.py nachziehen` bzw. das Einrichten läuft THEN ist die Zeile weg (zweiter Lauf: keine Änderung). Test: `test_schreiben.py::test_sperrdatei_in_dienstordner`, `test_betrieb.py::test_sperren_nicht_in_tmp`, `test_neu.py::test_nachziehen_sperren`.
- **AC-13:** (Einheiten nicht automatisch) GIVEN `ERLAUBT` in `units.py` und `units-installieren.py` WHEN die Listen verglichen werden THEN sind sie gleich und enthalten keine Sandbox- oder Benutzerzeile; GIVEN eine installierte Unit ohne die neuen Werte THEN meldet `units.py pruefen` eine gesperrte Abweichung (einmalige Meldung, kein Alarm). Test: `test_units.py::test_sandbox_nicht_in_erlaubnisliste`.
- **AC-14:** (Rollenabfrage) GIVEN eine Person, die in `reise.yaml` Gast ist, im veröffentlichten Stand aber Organisator:in WHEN `GET /<reise>/rolle?person=…` am Schreibweg läuft THEN `gast`; ohne Kopf `X-Frieda-Dienst` 403; unbekannte Person `rolle: null`; die Abfrage ändert keinen Stand. Beide Arten (Speicher-Reise und Git-Reise) und beide Beispielreisen. Test: `test_schreiben.py::test_rolle_lesen`.
- **AC-15:** (Einladen) GIVEN eine neue Person und der Schreibweg lehnt `person_schreiben` ab (Rolle der Einladenden in `reise.yaml` zu klein) WHEN `einladen` läuft THEN keine Mail, keine Zeile in `einladungen.json`, keine Konto-Verknüpfung; GIVEN er gelingt THEN erst `einladungen.json`, dann Mail; GIVEN eine vorhandene Person mit Konto-Verknüpfung und herabgestufter Einladender THEN abgelehnt. Test: `test_konnektor.py::test_einladen_erst_schreibweg`.
- **AC-16:** (Rückmeldung erledigen) GIVEN eine herabgestufte Person WHEN `rueckmeldung_erledigen` läuft THEN abgelehnt, kein PATCH; GIVEN der Schreibweg ist eingerichtet, aber nicht erreichbar THEN „Rolle nicht prüfbar“, kein PATCH; GIVEN der Schreibweg ist nicht eingerichtet THEN gilt wie bisher der veröffentlichte Stand. Test: `test_konnektor.py::test_erledigen_rolle_aktuell`.
- **AC-17:** (Wunsch einplanen) GIVEN eine herabgestufte Person WHEN die Seite `eingeplant` setzt THEN 403, Brett unverändert; GIVEN eine Organisator:in THEN geht es durch; Punkte und `erlebt` bleiben unverändert. Test: `test_rueckmeldungen.py::test_wunsch_einplanen_rolle_aktuell`.
- **AC-18:** (Texte) GIVEN die neuen Meldungen WHEN `test_texte.py` läuft THEN stehen sie in `texte_de.py` und `texte_en.py`, die Ausnahmelisten wachsen nicht. Test: `test_texte.py::test_paritaet_schluessel_und_platzhalter` (vorhandener Test, deckt die neuen Schlüssel ab).
- **AC-19:** (Doku) GIVEN `docs/betrieb.md` WHEN gelesen THEN beschreibt sie den neuen Helfer, den Kartendienst-Benutzer, die Sandbox, den Einmalschritt und die Warnung zum Admin-Benutzer; ein Test prüft die Nennung von `nginx-reise-installieren` und `<instanz>-karte` und dass keine sudoers-Zeile für `install`, `cat`, `rm`, `nginx` empfohlen wird. Test: `test_betrieb.py::test_doku_beschreibt_dienstrechte`.
- **AC-20:** (Instanz umgestellt, Teil von „fertig“) GIVEN die Software ist ausgeliefert WHEN die Instanz mit `einrichten.sh --erzeugen` und `--installieren` umgestellt ist THEN gilt: die Units tragen die neuen Werte, die Helfer liegen in `/usr/local/sbin`, die sudoers-Datei nennt nur Helfer, der Kartendienst läuft unter `<instanz>-karte`, `units.py pruefen` und `nginx.py pruefen` enden mit 0, Veröffentlichen, Schreiben, Freischalten einer frischen Testreise und Kartenaktualisierung laufen durch, die Netzdienste erreichen den Docker-Socket nicht. Dazu gilt: die installierten nginx-Bausteine der Instanz tragen `0640 root:<FR_GRUPPE>` (AC-21), die Kartendaten liegen unter `/var/lib/<instanz>-kartendienst/` hinter dem Verweis (AC-22). Test: `test_betrieb.py::test_einrichten_installieren_attrappe` (der Installationsweg gegen umgelenkte Ziele). Ausnahme mit Begründung: Die Umstellung der echten Instanz braucht Root auf ihrem Server und lässt sich nicht in CI prüfen; der Nachweis sind die Ausgänge von `units.py pruefen` und `nginx.py pruefen` (0) und die Läufe oben, festgehalten im privaten Issue der Instanz. Erst dann wird #552 geschlossen.
- **AC-21:** (nginx-Bausteine für die Gruppe lesbar, Entscheidung 9) GIVEN der Orte-Helfer, der Reise-Helfer oder `nginx.py anwenden` mit Root-Rechten WHEN sie einen Baustein der Instanz installieren THEN trägt er `0640 root:<FR_GRUPPE>`, eine fremde Datei in `conf.d` behält Modus und Besitz, und der Befehl in der Meldung von `nginx.py` nennt `FR_GRUPPE`; GIVEN installierte Bausteine WHEN `nginx.py pruefen` läuft THEN liest es sie ohne sudo und überspringt unlesbare fremde Dateien ohne Fehler; GIVEN vorhandene Bausteine mit altem Besitz WHEN `einrichten.sh --installieren` läuft THEN stellt es sie einmalig um (zweiter Lauf: keine Änderung). Test: `test_nginx.py::test_anwenden_installiert_mit_gruppe_der_instanz`, `test_nginx.py::test_befehl_nennt_die_gruppe`, `test_nginx.py::test_pruefen_liest_ohne_sudo_und_ueberspringt_unlesbare_fremde_dateien`, `test_nginx_helfer.py::test_orte_helfer_installiert_mit_gruppe_der_instanz`, `test_nginx_helfer.py::test_ac7_als_root_mit_root_eigentum_setzt_root_und_gruppe`, `test_nginx_reise_helfer.py::test_baustein_mit_gruppe_der_instanz`, `test_betrieb.py::test_einrichten_bausteine_lesbar_fuer_die_gruppe`.
- **AC-22:** (Kartendaten im Zustandsordner, Entscheidung 10) GIVEN eine Instanz mit Kartendaten in `FR_KARTENDIENST_ORDNER` WHEN `einrichten.sh --installieren` den Umzug ausführt THEN liegen die Daten unter `/var/lib/<instanz>-kartendienst/` (Besitz `<instanz>-karte`) und `FR_KARTENDIENST_ORDNER` ist ein root-eigener Verweis dorthin; ohne Daten entsteht nur der Verweis; nach einem Abbruch zwischen Kopie und Löschen setzt ein zweiter Lauf sauber fort; ein fremder Verweis bleibt unverändert (Fehlermeldung, nichts verschoben); das Einspielen neuer Kartendaten schaltet hinter dem Verweis um, ohne Schreibrecht im Elternordner. Test: `test_kartendienst.py::test_kartendienst_daten_im_zustandsordner`, `test_kartendienst_skript.py::test_umzug_verschiebt_daten_und_legt_verweis_an`, `test_kartendienst_skript.py::test_umzug_ohne_daten_und_nach_abbruch`, `test_kartendienst_skript.py::test_umzug_fremder_verweis_aendert_nichts`, `test_kartendienst_skript.py::test_einspielen_schaltet_hinter_dem_verweis_um`.

## Definition of Done

- [ ] Jedes Acceptance Criterion (AC-1 bis AC-20) ist durch den genannten automatischen Test belegt; bei AC-3 und AC-20 zusätzlich durch den begründeten Nachweis auf der Instanz.
- [ ] `engine/.venv/bin/python -m pytest -q -n auto engine/tests` ist ohne echte Reisen grün; die Tests der Instanz laufen mit dem Stand vor dem Ausliefern (Umgebungswerte und Unit-Vorlagen ändern sich).
- [ ] Die `ReadWritePaths` des Schreibwegs sind mit `messlauf-schreibweg.py` belegt; das Ergebnis steht im Protokoll unter `docs/artifacts/` (ohne Serverpfade).
- [ ] In der Umsetzung geklärt und getestet: woher eine Instanz ihre bisherige Vorgabe `FR_SPERREN=/tmp` hat (Umstellung ohne Handschritt), dass die Unit `rueckmeldungen` die Adresse des Schreibwegs (`KN_SCHREIBDIENST`) bekommt, und dass die Sperre des Kartendienstes auf ein nur lesend geöffnetes `veroeffentlichen.lock` greift (`flock` auf einem lesenden Dateideskriptor).
- [ ] `docs/betrieb.md` beschreibt den neuen Weg (AC-19).
- [ ] Die Instanz ist umgestellt und im privaten Issue der Instanz abgehakt (AC-20); erst danach wird #552 geschlossen.

## Prüfstelle ADR-0001 (kurz)

Betrieb, nicht Kern: Das Vorhaben berührt weder Grundformen der Reise-Ontologie noch Arten oder Merkmale; nichts Reisespezifisches, nichts Instanzspezifisches in Engine oder `betrieb/` (Benutzer, Pfade, Zonen kommen aus `einstellungen.env` und werden von `einrichten.sh` eingesetzt). Beide Reisetypen: Rollenprüfung und Betrieb sind reiseunabhängig; Tests laufen gegen beide Beispielreisen. Keine eigene KI, keine neue Fremdbibliothek, keine Sprache im Code (Meldungen in `texte_<sprache>.py`). Kein Widerspruch zum Kern.

## Risiken

- **Schreibweg bricht unter Sandbox:** fehlt ein Schreibziel, scheitern Schreibvorgänge. Gegenmaßnahme: Messlauf als Teil der Umsetzung (AC-3), Unit erst nach grünem Lauf in der Instanz installieren, alter Stand der Unit bleibt als Rückweg.
- **Freischalten über Helfer:** schlägt der Helfer fehl, bleibt die neue Reise ohne Seite; Meldung wie bisher einmal je Störung, Sicherung und Rückweg verhindern einen kaputten Webserver.
- **Admin als Dienstbenutzer:** auf einer Instanz, deren Dienstbenutzer weites `sudo` hat, bleiben die Helfer ein Schutz vor Fehlern, nicht vor Übernahme (steht in der Doku, Entscheidung 1).
- **Rolle nicht prüfbar:** Fällt der Schreibweg aus, sind Einladen, Erledigen und Einplanen kurz gesperrt (gewollt, schließt die Lücke); alle anderen Funktionen bleiben unberührt.
- **Kartendienst-Umzug:** Datenordner gehört danach `<instanz>-karte` und liegt unter `/var/lib/<instanz>-kartendienst/`; der Umzug ist wiederholbar und übersteht einen Abbruch (AC-22), ein Überspielen der Karte bleibt wiederholbar, es gehen keine Reisedaten verloren.
- **Bauordner beschreibbar (angenommen):** siehe Known Limitations, Entscheidung 11.

## Instanz-Tests und Reihenfolge

Ändert ein Pull Request Umgebungswerte, Units und Dateiformate, laufen vor dem Vorspulen auch die Tests der einbindenden Instanzen mit dem Branch. Reihenfolge: Drossel und Docker-Socket, Einladungsreihenfolge und Rollenabfrage, Reise-Helfer mit `freischalten.sh` und `nginx.py`, Sperren, Schreibweg-Sandbox nach Messlauf, Kartendienst-Benutzer, Doku, Umstellung der Instanz.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue
- **Rationale:** Die Entscheidungen oben sind Betriebshärtung nach etablierten Mustern (Root-Helfer mit Grammatik wie in #260 und #445, systemd-Sandbox) und berühren keine Architekturgrenze aus den ADRs 0001 bis 0011; sie stehen in dieser Spec, in `docs/betrieb.md` und im Issue.

## Changelog

- 2026-11-13: Initial spec created (Sicherheitsprüfung 12.11., Issue #552)
- 2026-11-13: Nachträge aus der Umsetzung: Entscheidungen 9 bis 11 (Lesen der nginx-Bausteine, Kartendienst-Daten, Restrisiko Bauordner, vom Product Owner angenommen, #555 geschlossen); dazu AC-21, AC-22, Tests 17 bis 19, Known Limitation und Risiko zum Bauordner
- 2026-11-13: Gegenprüfung: Rollenabfrage einer Git-Reise liest die Schreibkopie (sonst die Wurzel), dieselbe Quelle wie `wer_pruefen`; eine Herabstufung über den Schreibweg gilt damit sofort (Entscheidung Tech Lead, Test `test_schreiben.py::test_rolle_lesen_git_aus_der_schreibkopie`)
