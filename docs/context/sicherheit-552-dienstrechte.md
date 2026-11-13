# Context: sicherheit-552-dienstrechte

## Request Summary
Rest der Sicherheitsprüfung vom 12.11.2026 (#552, privat frieda-reisen#271 Punkte 2 und 6, K3-Rest): Die aus dem Netz
erreichbaren Dienste (Konnektor, Rückmeldedienst, Push) dürfen weder über sudo noch über Docker an Root-Rechte kommen;
dazu Härtung an nginx (`limit_req` für `/register`, `/token`), am Schreibweg (`ProtectSystem`, `ReadWritePaths`),
Sperrdateien aus `/tmp`, Rollenprüfung über den Schreibweg statt aus dem veröffentlichten Stand. Software-Wechsel laufen
weiter automatisch (Entscheidung PO 13.11.2026). Fertig erst, wenn auch die Instanz umgestellt ist.

## Related Files
| Datei | Bedeutung |
|------|-----------|
| `betrieb/freischalten.sh` | legt Reise-Bausteine per `sudo install/test/cat/rm` in `/etc/nginx/snippets` an, `nginx -t`, reload |
| `betrieb/vorlagen/nginx-orte-installieren.py` | Muster für einen Root-Helfer mit fester Grammatik (stdin, `-I`, feste Pfade, Sicherung, `nginx -t` mit Rückweg) |
| `betrieb/vorlagen/units-installieren.py`, `betrieb/units.py` | Root-Helfer für Units mit Erlaubnisliste `ERLAUBT` (gleich in beiden, Test prüft) |
| `betrieb/nginx.py` | Abgleich; liest Bausteine (640 root) per `sudo cat`; `installieren` ruft Orte-Helfer |
| `betrieb/einrichten.sh` | erzeugt Units/nginx/Helfer, nennt sudoers-Zeilen, `usermod -aG docker` für Dienstbenutzer |
| `betrieb/vorlagen/{konnektor,rueckmeldungen,push,schreiben,veroeffentlichen,waechter}.service` | Units; Netzdienste haben `NoNewPrivileges`, `ProtectSystem=strict`; `schreiben` hat nur `NoNewPrivileges`, `PrivateTmp` |
| `betrieb/vorlagen/kartendienst/*` | Overpass-Container per `docker run` als `User=__BENUTZER__` (braucht Gruppe docker); `aktualisieren` führt `kartendienst.sh` aus dem Repo aus, liest `betrieb.env` |
| `betrieb/kartendienst.sh` | Einspielen mit Docker; Sperre `$FR_SPERREN/<instanz>-kartendienst.lock` (Vorgabe `/tmp`) und `FR_DIENST/veroeffentlichen.lock` |
| `engine/schreiben.py:5377` `sperrdatei()` | Sperre je Reise in `FR_SPERREN` (Vorgabe `/tmp`) |
| `betrieb/gemeinsam.sh:100` | `FR_SPERREN:=/tmp` |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | `/token`, `/register` ohne `limit_req` (Begründung: gemeinsame Adressen der Claude-App) |
| `betrieb/vorlagen/nginx-zone.conf` | Zonen `_mcp` (10 r/s), `_anmelden` (5 r/m), `_konto` (30 r/m), `_api` |
| `engine/konnektor.py` `einladen()` ab Z. 1962, `rueckmeldung_erledigen`, Wunsch einplanen | Rolle `wer["rolle"]` aus veröffentlichtem Stand (K3-Rest) |
| `docs/betrieb.md` Z. 364 ff. (sudo), 378 ff. (Units), 410 ff. (nginx), 480 ff. (Kartendienst) | Doku |
| Tests: `engine/tests/test_betrieb.py`, `test_nginx.py`, `test_nginx_helfer.py`, `test_units.py`, `test_units_helfer.py`, `test_kartendienst*.py` | |

## Existing Patterns
- Root-Helfer: Vorlage in `betrieb/vorlagen/*.py`, `#!/usr/bin/python3 -I`, Platzhalter `__INSTANZ__` usw. von `einrichten.sh`
  eingesetzt, nach `/usr/local/sbin/<instanz>-…` (root, 0755), sudoers-Zeile `NOPASSWD` genau für den Helfer; liest
  Eingabe auf stdin, traut Umgebung und Argumenten nicht, Ausgänge 0/2/3/…; Tests rufen die Vorlage mit umgelenkten Pfaden.
- Units-Abgleich: `units.py pruefen` vergleicht Soll und Ist; nur Zeilen der Erlaubnisliste gehen automatisch, alles andere
  ist eine „gesperrte Abweichung“ → einmalige Meldung, Installation von Hand (`einrichten.sh --installieren`).
- Orte-Datei des Konnektors wird automatisch über den Orte-Helfer installiert (Grammatik erlaubt `limit_req` mit den drei
  Zonen) → `limit_req` für `/token`/`/register` geht ohne Handschritt.
- Sperren: `veroeffentlichen.sh` liegt schon in `FR_DIENST` (#211, wegen `PrivateTmp`).

## Dependencies
- Upstream: systemd (Sandbox-Optionen), nginx, sudo, Docker, git/gh (Schreibweg pusht mit Anmeldung des Dienstbenutzers).
- Downstream: `veroeffentlichen.sh` ruft `freischalten.sh` je Reise; `units.py`/`nginx.py` beim Veröffentlichen;
  `kartendienst.sh` koordiniert sich mit dem Veröffentlichen über die Sperre in `FR_DIENST`.

## Befund auf diesem Server (Instanz frieda-reisen)
- Dienstbenutzer ist `hem` — der Admin-Benutzer des Servers mit `(ALL) NOPASSWD: ALL` und Gruppe `docker`; auch alle
  Claude-Code-Sitzungen laufen als `hem`. Die schmalen sudo-Regeln der Doku wirken hier nicht.
- Netzdienste (`konnektor`, `rueckmeldungen`, `push`) laufen mit `NoNewPrivileges=yes` → sudo ist für sie gesperrt.
  Offener Weg: `/run/docker.sock` ist erreichbar (`ProtectSystem=strict` sperrt kein Verbinden mit einem Socket).
- `schreiben.service`: `ProtectSystem=no`, `ProtectHome=no` → kann Dateien in `/home/hem` (Shell-Profile, Skripte des
  Bauordners, die der Timer ohne `NoNewPrivileges` ausführt) ändern → indirekt Root.
- `veroeffentlichen.service`, `waechter.service`, `kartendienst-aktualisieren.service` ohne Sandbox (brauchen sudo bzw. Docker).

## Existing Specs
- `docs/specs/betrieb/nginx-orte-automatisch-445.md` (Grammatik des Orte-Helfers)
- Specs zu Units-Abgleich (#260) unter `docs/specs/betrieb/`

## Risks & Considerations
- Echte Trennung braucht auf diesem Server einen eigenen Dienstbenutzer statt `hem` (Besitz von `/srv/frieda-reisen`,
  Bauordner, Schreibkopie, venv, Git-Zugang zum Pushen). Großer Umzug mit Ausfallrisiko; vor dem Bauen abwägen, was die
  Netzdienste tatsächlich erreicht (Sandbox) gegenüber Benutzerwechsel.
- Jede Änderung an Units ist für `units-installieren` eine gesperrte Abweichung → Installation je Instanz mit Root
  (hier möglich, `hem` hat sudo) oder Erweiterung der Erlaubnisliste (Sicherheitsentscheidung).
- Root-Helfer, die Code oder Umgebung aus Ordnern des Dienstbenutzers lesen (`betrieb.env`, Skripte im Repo), heben die
  Trennung wieder auf (EnvironmentFile kann `LD_PRELOAD` setzen).
- `ProtectSystem=strict` für den Schreibweg muss alle Schreibziele kennen: Schreibkopie, `.git` des Bauordners (Worktree),
  `FR_DIENST`, Konten, Reisespeicher, Bau-Ordner, Sperren; sonst scheitern Schreibvorgänge (Messlauf `messlauf-schreibweg.py`).
- `limit_req` für `/token`/`/register`: Claude-App ruft von gemeinsamen Adressen → großzügige Zone (`_mcp`) statt streng.
- Freischalten ohne sudo `test`/`cat`: Link einer Reise steht dann nur noch in `seiten.json` bzw. muss der Helfer melden.

## Analysis

### Type
Feature (Härtung des Betriebs nach der Sicherheitsprüfung vom 12.11.2026)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/vorlagen/nginx-reise-installieren.py` | CREATE | Root-Helfer nach Muster `nginx-orte-installieren.py`: stdin genau `<reise>` (Muster `^[a-z0-9][a-z0-9-]{1,39}\Z`), Vorlage und Werte (Seiten, RM-Port, Zone, Instanz) beim Einrichten eingebacken (nie aus dem Repo gelesen), legt Token selbst an (`secrets`), erneuert vorhandene Bausteine mit bestehendem Pfad, Sicherung + `nginx -t` mit Rückweg + reload, gibt nur `<pfad>` aus; Lesemodus nur Pfad (ersetzt `sudo cat`) |
| `betrieb/freischalten.sh` | MODIFY | statt `sudo test/install/cat/rm`, `nginx -t`, reload nur noch Helfer-Aufruf; Rechteprüfung (Z. 48–50) auf den Helfer umstellen |
| `betrieb/nginx.py` | MODIFY | Reise-Bausteine nicht mehr per `sudo cat` lesen (Abgleich nur Orte/Zone bzw. über Helfer) |
| `betrieb/einrichten.sh` | MODIFY | neuen Helfer erzeugen/installieren; sudoers-Hinweise nur Helfer + `systemctl restart`; kein `usermod -aG docker` für den Dienstbenutzer; Kartendienst-Benutzer |
| `betrieb/vorlagen/{konnektor,rueckmeldungen,push}.service` | MODIFY | `InaccessiblePaths=-/run/docker.sock` |
| `betrieb/vorlagen/schreiben.service` | MODIFY | `ProtectSystem=strict`, `ProtectHome=read-only`, `ReadWritePaths=` (Schreibkopie, Bauordner inkl. `.git`, FR_DIENST, FR_KONTEN, Reisespeicher), `InaccessiblePaths=-/run/docker.sock`; Ziele per `messlauf-schreibweg.py` belegen, auch das Hochladen der Commits mit der gh-Anmeldung unter der Sandbox |
| `betrieb/vorlagen/kartendienst/kartendienst.service`, `-aktualisieren.service` | MODIFY | Docker nicht mehr als Dienstbenutzer: eigener Benutzer `<instanz>-karte` (Gruppe docker) bzw. Root-Unit, die kein vom Dienstbenutzer schreibbares Skript/Env ausführt |
| `betrieb/kartendienst.sh`, `betrieb/gemeinsam.sh`, `engine/schreiben.py:5377` | MODIFY | Sperren in `FR_DIENST` statt `/tmp` (Vorgabe von `FR_SPERREN`) |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | MODIFY | `/token`, `/register` mit `limit_req zone=_mcp burst=40 nodelay` (gemeinsame Adressen der Claude-App → großzügige Zone); geht über den Orte-Helfer automatisch |
| `engine/konnektor.py` `einladen_per_mail` (~2106) | MODIFY | erst `person_schreiben` über den Schreibweg (prüft Rolle aus `reise.yaml`, `schreiben.py` ~5122), dann Mail/`einladungen.json` |
| `engine/konnektor.py` `rueckmeldung_erledigen`, Wunsch einplanen | MODIFY | Rolle nicht nur aus veröffentlichtem Stand: Rückmeldedienst bzw. Schreibweg prüft gegen aktuellen Stand (Stelle in der Spec festlegen) |
| `docs/betrieb.md` | MODIFY | neuer Weg (Helfer statt sudo-Regeln, Kartendienst-Benutzer, Sandbox); Warnung: Server-Admin als Dienstbenutzer hebt die schmalen Regeln auf |
| neue `engine/tests/test_nginx_reise_helfer.py`; `test_betrieb.py`, `test_units.py`, `test_kartendienst*.py`, Konnektor-Tests | CREATE/MODIFY | Grammatik/Rückweg des Helfers, Netzdienste ohne Docker-Zugang, keine sudo-Aufrufe außer Helfern in `betrieb/*.sh`, Sperrpfade, Einladungsreihenfolge |

### Scope Assessment
- Files: ~16
- Estimated LoC: +700/-120 (davon ~300 Tests, ~250 Helfer)
- Risk Level: MEDIUM — betrifft Freischalten neuer Reisen, Schreibweg und Kartendienst; Fehler stoppen Veröffentlichen oder Schreiben, zerstören aber keine Daten (Helfer mit Sicherung und Rückweg).

### Technical Approach
Entscheidung (Tech Lead): **kein Umzug der ganzen Instanz auf einen neuen Benutzer** in diesem Issue (großer Umzug mit Ausfallrisiko; auf diesem Server bleibt `hem` ohnehin Admin). Stattdessen „least privilege“ je Dienst:
1. Netzdienste abgeschottet: `NoNewPrivileges` (schon da) + `InaccessiblePaths=-/run/docker.sock` → weder sudo noch Docker. Test an den Vorlagen.
2. Root nur über feste Helfer mit Grammatik (units, nginx-orte, neu nginx-reise); sudo-Regeln für `install/test/cat/rm`, `nginx -t`, reload entfallen.
3. Docker nur für den Kartendienst unter eigenem Benutzer.
4. Schreibweg mit `ProtectSystem=strict`/`ProtectHome=read-only` + gemessenen `ReadWritePaths` → kann Shell-Profile und Skripte in `~` nicht mehr ändern.
5. `limit_req` an `/token` und `/register` mit der Zone `_mcp`.
6. Sperren in `FR_DIENST`.
7. K3-Rest: Einladung erst nach geprüftem Schreiben; Rückmeldung erledigen/Wunsch einplanen gegen aktuellen Stand.

Unit-Änderungen gehen **nicht** in die Erlaubnisliste `ERLAUBT` (Sandbox-Werte wie `ReadWritePaths` könnten Schreibrechte öffnen); einmalige Installation je Instanz mit `einrichten.sh --installieren` (bestehendes Muster). Auf dieser Instanz führt Claude das selbst aus.

Reihenfolge: limit_req + docker.sock → Einladungsreihenfolge → nginx-reise-Helfer + freischalten.sh/nginx.py → Sperren → Schreibweg-Sandbox nach Messlauf → Kartendienst-Benutzer → Doku → Instanz umstellen (frieda-reisen#271).

### Dependencies
- `veroeffentlichen.service` (ohne Sandbox) ruft `freischalten.sh` je Reise; der Schreibweg startet nur das Veröffentlichen (#465).
- `nginx.py installieren` installiert die Orte-Datei über den Orte-Helfer (limit_req ohne Handschritt).
- `kartendienst.sh` und `veroeffentlichen.sh` koordinieren über `FR_DIENST/veroeffentlichen.lock` (bleibt).
- Vorhandene Bausteine (640 root) bleiben gültig; der Helfer übernimmt sie mit unverändertem Token.

### Open Questions
- [x] Eigener Dienstbenutzer für die ganze Instanz? → nein (technische Entscheidung, oben); Doku empfiehlt ihn für neue Instanzen.
- [x] Unit-Härtung über `ERLAUBT`? → nein, einmalige Installation.
- [ ] (Spec) Wunsch einplanen: genaue Stelle der Rollenprüfung im Rückmeldedienst.
- [ ] (Spec/Messlauf) vollständige `ReadWritePaths` des Schreibwegs inkl. Hochladen mit gh-Anmeldung.
