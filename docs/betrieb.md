# Betrieb einer Instanz

Wie Frieda auf einem eigenen Server läuft: Seiten ausliefern, Rückmeldungen annehmen, sie von der KI einarbeiten lassen, veröffentlichen, neue Reisen freischalten und an Fristen erinnern. Alles dafür liegt in dieser Software unter `betrieb/`. Eine Instanz liefert nur ihre Werte.

## Instanz

Eine **Instanz** ist eine Reisegruppe mit eigenem Betreiber: ein Reisen-Repo, dazu Ordner, Dienste und Adresse auf einem Server. Mehrere Gruppen bedeuten mehrere Instanzen, gern auf demselben Server. Die Reisen einer Instanz teilen sich Ablage, Dienste, KI-Anmeldung und Meldeweg; getrennt sind die Gruppen nur über eigene Instanzen. Mandanten innerhalb einer Instanz sind ein späterer Schritt (Issue #68).

| Teil | Ort | Inhalt |
|---|---|---|
| Software | dieses Repo, im Reisen-Repo als Submodul `frieda/` (`engine -> frieda/engine`) | Generator, Dienste, `betrieb/` mit Skripten, Vorlagen und KI-Anweisung |
| Reisen-Repo | eigenes, privates Repo | `reisen/<reise>/`, `betrieb/einstellungen.env`, optional `betrieb/einarbeiten-ergaenzung.md`, ein Meldeskript, eigene Tests unter `tests/` |
| Veröffentlichungsordner | Klon des Reisen-Repos auf dem Server, immer auf `main` | von hier wird gebaut; nicht darin arbeiten |
| Arbeitskopien | `<Klon>-auto` (Einarbeiten), `<Klon>-arbeit` (Sitzungen) | Git-Worktrees, `betrieb/arbeitskopie.sh` |
| Seiten | `<FR_SEITEN>/<reise>/` | gebaute Seiten, nginx liefert sie aus |
| Ablage | `<FR_ABLAGE>/<reise>/` (`eingang.jsonl`, `auftraege.jsonl`, `status.json`, …), `<FR_ABLAGE>/_neu/`, `<FR_ABLAGE>/_konten/` | Eingaben und Konten; nie im Repo |
| Dienstordner | `<FR_DIENST>/` | Code der Dienste, Stände, Protokolle, Stempel, geheime Einstellungen |
| Konnektor-Zugänge | `<FR_KONNEKTOR>/zugaenge.json`, `seiten.json` (600) | geheime Links; nie im Repo |
| systemd | `<instanz>-rueckmeldungen`, `-konnektor`, `-veroeffentlichen.timer`, `-einarbeiten.path`/`.timer`, `-waechter.timer` | aus `betrieb/vorlagen/`, erzeugt von `einrichten.sh` |
| nginx | `<FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf` (mit Token), `<instanz>-konnektor.conf`, Zone in `conf.d/<instanz>-zone.conf` | aus `betrieb/vorlagen/` |

Die Skripte rufen sich im Reisen-Repo als `frieda/betrieb/<skript>.sh` auf und finden die Instanz selbst (das Repo, das die Software einbindet; sonst `FR_WURZEL`).

## Der Kreislauf

1. **Eingabe:** Rückmeldedienst (Webseite), Konnektor (Claude-App) und Wächter schreiben in die Ablage der Reise und berühren `<FR_ABLAGE>/.neu`.
2. **Einarbeiten:** Der Pfad-Wächter `<instanz>-einarbeiten.path` sieht `.neu` und startet `einarbeiten.sh`. Nach der Sammelzeit arbeitet die KI je Reise ein. Das Skript prüft, baut, testet und führt in `main` zusammen.
3. **Veröffentlichen:** `veroeffentlichen.sh` holt `main` in den Veröffentlichungsordner und ruft `deploy.sh` für jede Reise auf. Das geschieht gleich nach dem Einarbeiten und sonst alle 5 Minuten. Danach schaltet `freischalten.sh` neue Reisen frei.
4. **Rückmeldung:** Erst wenn alles online ist, setzt das Einarbeiten die Status. Die Absender sehen „aufgenommen“, „passt nicht“ oder eine Rückfrage.
5. **Erinnern:** `waechter.sh` läuft täglich, meldet Fristen und legt Prüfaufträge an, die wieder bei 1 eingehen.

Eine Änderung aus einer Sitzung (Claude Code im Reisen-Repo) geht über einen PR nach `main` und von dort denselben Weg ab Schritt 3.

## Einarbeiten

`betrieb/einarbeiten.sh` bearbeitet Rückmeldungen und Aufträge mit Status „neu“, die noch kein Lauf gesehen hat. Ohne Neues startet keine KI, ein leerer Lauf kostet nichts.

**Ablauf eines Durchgangs:**

1. **Sammelzeit:** Nach der letzten neuen Eingabe wartet der Lauf `regeln.sammelzeit_minuten` der Reise (`reise.yaml`), höchstens `FR_MAX_WARTEN_MIN` nach der ersten. So gehen mehrere Eingaben in einen Lauf.
2. **Ein Lauf zur Zeit (Sperre):** Was währenddessen eingeht, bearbeitet derselbe Dienst in einem weiteren Durchgang, höchstens `FR_DURCHGAENGE`.
3. **Arbeitskopie:** Eine eigene Arbeitskopie `<Klon>-auto` auf dem Branch `auto/einarbeiten-<zeit>`.
4. **Neue Reisen** aus der Claude-App (`<FR_ABLAGE>/_neu`) legt das Skript ohne KI an, denn der Dienst hat sie schon geprüft (`einarbeiten_hilfe.py neue_reisen`).
5. **Ein KI-Lauf je Reise** (`claude -p`, Modus `dontAsk`) mit der Anweisung `betrieb/einarbeiten-auftrag.md` und den IDs dieser Reise:
   - Schreiben nur unter `reisen/<reise>/` und in die eigene Ergebnisdatei.
   - Lesen verboten für die anderen Reisen (Arbeitskopie und Veröffentlichungsordner) und für die ganze Ablage.
   - Befehle nur `rueckmeldungen.py liste <reise>` und `bauen.py <reise>`, dazu Websuche und Webabruf.
   - Kein git, keine Status: Die KI schreibt `status.tsv` und `bericht.md`.
   - Was sie trotzdem außerhalb ihrer Reise ändert, verwirft das Skript und nennt es im Bericht.
6. **Regelprüfung** (`einarbeiten_hilfe.py regeln`): Ein Konflikt muss eine neue offene Frage mit der Auftrags-ID ergeben. Ein Prüfauftrag des Wächters darf keinen Wert ändern.
7. **Bauen, Tests** (Software und `tests/` des Reisen-Repos), dann ein Commit und ein PR für alle Reisen des Durchgangs, zusammenführen (`gh`).
8. **Sofort veröffentlichen:** Hält gerade der Timer die Sperre, holt er es nach. Die Nachricht sagt dann „Online in wenigen Minuten“.
9. **Status setzen:** nur für Einträge dieses Laufs und nur aus der Datei der eigenen Reise.

**Ergänzung der Instanz:** Was eine Instanz der KI zusätzlich sagen will (eigene Gepflogenheiten, Namen von Rollen), steht in `betrieb/einarbeiten-ergaenzung.md` des Reisen-Repos und wird angehängt. Die Anweisung der Software nennt keine Person und kein Repo.

**Fehlerfälle:**

| Fall | Folge |
|---|---|
| KI-Lauf einer Reise bricht ab | Ihre halben Änderungen werden verworfen. Ihre Einträge bleiben „neu“, der Versuch zählt nur für sie. Die anderen Reisen gehen online. Meldung „Einarbeiten fehlgeschlagen“. |
| Derselbe Eintrag scheitert `FR_MAX_VERSUCHE`-mal | Er wird aufgegeben: Rückfrage auf der Seite („<FR_BETREIBER> schaut es sich in der nächsten Sitzung an“), Meldung, kein automatischer Versuch mehr. Spätere Eingaben hält er nicht auf. |
| Regel verletzt oder Tests rot | Nichts geht online, die Status bleiben „neu“. Der Branch `auto/einarbeiten-…` wartet zum Nachsehen in einer Sitzung, die Einträge gelten als gesehen. |
| PR nicht zusammengeführt | Meldung, nichts online, Einträge gesehen. |

**Messen:** Jeder Durchgang mit Neuem schreibt eine Zeile nach `<FR_DIENST>/einarbeiten-laeufe.jsonl`: Ergebnis (`ok`, `teilweise`, `fehler`), Reisen, Anzahl, Dauer, KI-Dauer, Kosten in USD, Zeit von der ältesten Eingabe bis zum Ende, online ja/nein. Ansehen mit `python3 engine/rueckmeldungen.py laeufe [<reise>] [--alle]`. Die Claude-App zeigt den Abschnitt „Einarbeiten“ im Überblick, Kosten zeigt sie nicht.

**Von Hand:** `frieda/betrieb/einarbeiten.sh` im Veröffentlichungsordner. Ohne Kosten prüfen: `date > <FR_ABLAGE>/.neu`, dann zeigt `journalctl -u <instanz>-einarbeiten -n 20` „Nichts Neues.“

## Veröffentlichen

`betrieb/veroeffentlichen.sh` holt `origin/main`, spult den Veröffentlichungsordner vor und bringt das Submodul auf den festgehaltenen Stand. Danach ruft es `deploy.sh` für jede Reise mit `reise.json` auf. Gemerkt wird der Stand in `<FR_DIENST>/veroeffentlicht`. Nur ein gelungener Lauf merkt ihn, ein fehlgeschlagener wird also beim nächsten Mal wiederholt. Ist der Ordner nicht auf `main` oder nicht sauber, überspringt es den Lauf. `--immer` veröffentlicht auch ohne neuen Stand.

`betrieb/deploy.sh <reise>` baut, führt die Tests aus und kopiert die Seite nach `<FR_SEITEN>/<reise>/`. Es legt die Ablage der Reise an und kopiert den Code der Dienste nach `<FR_DIENST>/`. Die Liste der Module steht im Skript, ein Test prüft sie gegen die Importe. Bei geändertem Code startet es die Dienste neu (`sudo -n systemctl restart`). Am Ende prüft es Seite, Rückmeldedienst und Konnektor.

## Neue Reise freischalten

Ohne Handarbeit (`docs/neue-reise.md`): Nach dem Veröffentlichen ruft `veroeffentlichen.sh` für jede Reise `freischalten.sh <reise>` auf.

- **Neue Reise:** Sie bekommt einen nginx-Baustein aus `vorlagen/nginx-reise.conf` mit einem neuen Zufalls-Token (root, 640). Dann `nginx -t`; bei einem Fehler wird der Baustein wieder entfernt. Danach lädt nginx neu.
- **Prüfung:** Seite und `api/gesund` müssen mit 200 antworten.
- **Link:** Der Link zur Seite kommt nach `seiten.json` (für `meine_reisen`).
- **Vorgemerkte Links:** Links neuer Reisen aus der App merkt das Einarbeiten in `<FR_DIENST>/neue-reisen-ausstehend.jsonl` vor. Das Veröffentlichen stellt sie zu, sobald die Seite online ist, als Meldung an die Person oder bei einem Konto als Einladung per Mail.

Links von Hand: `freischalten.sh <reise>` für die Seite, `freischalten.sh <reise> --person <schlüssel>` für die Claude-App. Links stehen nie im Protokoll, im Repo, in Issues oder Nachrichten.

## Wächter

`betrieb/waechter.sh` läuft täglich und ruft `engine/waechter.py lauf` auf (`docs/waechter.md`). Es berücksichtigt nur Reisen mit Baustein `waechter` und Status `fest` oder `unterwegs`. Hat es etwas zu melden, geht eine Sammelnachricht an den Betreiber; ein Fehler wird dringend gemeldet.

## Einstellungen

`betrieb/einstellungen.env` im Reisen-Repo (Vorlage `betrieb/einstellungen.beispiel`) enthält Zeilen `NAME=wert`, ohne Shell-Auswertung. Was schon in der Umgebung steht, gilt vor der Datei. Geheimes gehört nicht dorthin, sondern nach `<FR_DIENST>/betrieb.env` (600, gleiche Form). Das ist die Datei, die die Units als `EnvironmentFile` laden. Mailweg und Konten stehen in `<FR_DIENST>/konten.env` (`docs/konten.md`).

| Name | Vorgabe | Bedeutung |
|---|---|---|
| `FR_INSTANZ` | `frieda` | Name der Instanz: Units, nginx-Bausteine, Sperren, Drossel-Zone |
| `FR_TITEL` | `Frieda` | Kurzname in Nachrichten |
| `FR_BETREIBER` | leer | wer Rückfragen ansieht; steht im Kommentar aufgegebener Einträge |
| `FR_ADRESSE` | – | öffentliche Adresse der Seiten (nötig zum Freischalten) |
| `FR_KN_ADRESSE` | `<FR_ADRESSE>/<FR_INSTANZ>-mcp` | Adresse des Konnektors |
| `FR_SEITEN`, `FR_ABLAGE`, `FR_DIENST`, `FR_KONNEKTOR` | `/srv/<instanz>`, darunter `_rueckmeldungen`, `_dienst`, `_konnektor` | Ordner auf dem Server |
| `FR_RM_PORT`, `FR_KN_PORT` | `8771`, `8772` | Ports auf 127.0.0.1 |
| `FR_PYTHON` | `<Wurzel>/engine/.venv/bin/python` | Python mit den Paketen der Software |
| `FR_MELDEN` | leer | Meldeweg (unten) |
| `FR_CLAUDE`, `FR_CLAUDE_MIN` | `claude`, `45` | Befehl und Höchstdauer eines KI-Laufs je Reise |
| `FR_DURCHGAENGE`, `FR_MAX_VERSUCHE`, `FR_MAX_WARTEN_MIN` | `3`, `3`, `20` | Durchgänge je Start, Fehlversuche bis zum Aufgeben, längste Sammelzeit |
| `FR_NGINX_SNIPPETS`, `FR_SUDO` | `/etc/nginx/snippets`, `sudo -n` | nginx-Bausteine und Rechte |
| `FR_SPERREN` | `/tmp` | Ordner der Sperrdateien |
| `FR_BENUTZER`, `FR_GRUPPE`, `FR_HOME`, `FR_PFAD` | aufrufender Benutzer | nur für `einrichten.sh`: Benutzer und `PATH` der Dienste |
| `FR_HEARTBEAT_VEROEFFENTLICHEN` | leer | Überwachungsadresse, nur in `betrieb.env` |

Die Skripte setzen daraus die Umgebung der Software (`RM_ABLAGE`, `KN_SEITEN`, `KN_ZUGAENGE`, `KN_BASIS`, `RM_LAEUFE`). Ausdrücklich gesetzte Werte bleiben.

**Meldeweg:** `FR_MELDEN` ist eine ausführbare Datei der Instanz, aufgerufen als `<befehl> <normal|high> <betreff> <text> [erledigt]`. `erledigt` heißt: Das ist ein reiner Bericht, es ist nichts zu tun. Fehler kommen ohne `erledigt` und sollen offen bleiben, bis jemand sie ansieht. Wie die Nachricht ankommt (Mail, Telegram, eine Warteschlange), entscheidet die Instanz in ihrem Skript.

## Überwachung

Nach fachlichem Erfolg berühren die Läufe Stempel in `<FR_DIENST>/`: `einarbeiten-erfolg` (nichts Neues oder alles online) und `waechter-erfolg`. Ein Monitor der Instanz meldet, wenn ein Stempel zu alt ist (etwa 3 h beim Einarbeiten, 36 h beim Wächter) oder ein Dienst `failed` ist. Das Veröffentlichen ruft nach Erfolg `FR_HEARTBEAT_VEROEFFENTLICHEN` ab, übersprungene oder gescheiterte Läufe rufen sie nicht ab. Seiten, `api/gesund` und der Konnektor unter `/gesund` lassen sich von außen prüfen.

## Neue Instanz einrichten

1. **Server:** Benutzer für die Dienste, nginx mit HTTPS für die Adresse, Python 3, `git`, `rsync`, `flock`, Node 22 (Browser-Prüfung in den Tests), [Claude Code](https://claude.com/claude-code) und `gh`, beide als dieser Benutzer angemeldet.
2. **Reisen-Repo:** neues privates Repo mit der Software als Submodul:
   ```
   git submodule add https://github.com/henemm/frieda-reist frieda
   ln -s frieda/engine engine
   mkdir -p reisen betrieb && cp frieda/betrieb/einstellungen.beispiel betrieb/einstellungen.env
   ```
   Werte eintragen; ein Meldeskript ist optional. In `.gitignore`: `.einarbeiten/`, `dist/`, `reisen/*/medien/karte`.
3. **Klon auf dem Server:** als Dienstbenutzer, `git submodule update --init`. Danach `python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt`. `git fetch` muss ohne Rückfrage gehen.
4. **Einrichten:** `frieda/betrieb/einrichten.sh` prüft die Voraussetzungen. Es erzeugt Units und nginx-Bausteine in einem Ordner und zeigt die Befehle zum Aktivieren. Außerhalb dieses Ordners ändert es nichts. `--installieren` legt nach Rückfrage die Ordner an und kopiert Units und Bausteine nach `/etc`.
5. **nginx:** Im server-Block der Adresse `include <FR_NGINX_SNIPPETS>/<instanz>-*.conf;` eintragen, `nginx -t`, neu laden.
6. **sudo** für den Dienstbenutzer, ohne Passwort und nur für diese Befehle:
   - `systemctl restart <instanz>-rueckmeldungen <instanz>-konnektor`
   - `nginx -t` und `systemctl reload nginx`
   - `install`, `test`, `cat` und `rm` für Dateien in `<FR_NGINX_SNIPPETS>/<instanz>-*.conf`
7. **Erste Reise** anlegen (`docs/neue-reise.md`), committen, `frieda/betrieb/deploy.sh <reise>` (legt den Code der Dienste an). Danach `sudo systemctl enable --now <instanz>-rueckmeldungen <instanz>-konnektor` und die Timer und den Pfad-Wächter, wie `einrichten.sh` sie nennt.
8. **Prüfen:** `veroeffentlichen.sh --immer` zeigt „ist online“. Mit `freischalten.sh <reise> --person <schlüssel>` bekommt jede Person ihren Link, den sie in der Claude-App einträgt (`docs/konnektor.md`). `date > <FR_ABLAGE>/.neu` zeigt im Journal „Nichts Neues.“.

**Zwei Instanzen auf einem Server** brauchen verschiedene `FR_INSTANZ`, `FR_SEITEN` (und damit Ablage und Dienstordner) und Ports. `einrichten.sh` bricht ab, wenn eine andere installierte Instanz dieselben Ports nutzt. Unit-Namen, nginx-Bausteine, Drossel-Zone und Sperrdateien tragen den Namen der Instanz. Jede Instanz braucht einen eigenen Konnektor-Pfad (`<instanz>-mcp`).

## Arbeitskopien

Im Veröffentlichungsordner wird nicht gearbeitet, sonst setzt der Timer aus. `frieda/betrieb/arbeitskopie.sh <branch>` legt daneben einen Git-Worktree an oder wechselt dort den Branch. Was nicht im Repo liegt, wird aus dem Veröffentlichungsordner verlinkt: Python-Umgebung, Werkzeuge, Grundkarten und `.claude/settings.json`.

## Zurückrollen und sperren

- **Seite:** auf den letzten guten Stand gehen (`git checkout <commit>`), `deploy.sh <reise>`, zurück auf `main`. Der Service Worker bietet den alten Inhalt als neue Version an.
- **Dienste:** der Code liegt in `<FR_DIENST>/`; ein Deploy eines älteren Stands bringt ihn zurück.
- **Link sperren:** Eintrag aus `zugaenge.json` löschen (Konnektor, wirkt sofort) bzw. den Token im nginx-Baustein ändern (Seite).

## Wenn etwas klemmt

| Anzeichen | Erster Blick |
|---|---|
| Seite antwortet nicht | `ls <FR_SEITEN>/<reise>/index.html`, `sudo nginx -t`, Fehlerlog von nginx |
| `api/gesund` antwortet nicht | `systemctl status <instanz>-rueckmeldungen`, `journalctl -u <instanz>-rueckmeldungen -n 50` |
| Konnektor `gesund` 503 | `zugaenge.json` unlesbar oder eine verlinkte Reise nicht veröffentlicht |
| Nichts geht online | `journalctl -u <instanz>-veroeffentlichen -n 50`; ist der Veröffentlichungsordner auf `main` und sauber? |
| Eingaben bleiben „neu“ | `journalctl -u <instanz>-einarbeiten -n 100`, `rueckmeldungen.py laeufe`, offene Branches `auto/einarbeiten-…` |
