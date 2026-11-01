# Betrieb einer Instanz

Wie Frieda auf einem eigenen Server läuft: Seiten ausliefern, Rückmeldungen annehmen, was der AI-Client über den Konnektor festlegt sofort ins Reisen-Repo schreiben, veröffentlichen, neue Reisen freischalten und an Fristen erinnern. Alles dafür liegt in dieser Software unter `betrieb/`. Eine Instanz liefert nur ihre Werte. Frieda enthält keine eigene KI (ADR-0001): Auf dem Server läuft kein Claude Code; bis zum 29.10.2026 gab es einen Einarbeiten-Lauf, der Eingaben mit `claude -p` einarbeitete (Paket D), er ist mit Paket O-3 entfallen.

## Instanz

Eine **Instanz** ist eine Reisegruppe mit eigenem Betreiber: ein Reisen-Repo, dazu Ordner, Dienste und Adresse auf einem Server. Mehrere Gruppen bedeuten mehrere Instanzen, gern auf demselben Server. Die Reisen einer Instanz teilen sich Ablage, Dienste und Meldeweg; getrennt sind die Gruppen nur über eigene Instanzen. Mandanten innerhalb einer Instanz sind ein späterer Schritt (Issue #68).

| Teil | Ort | Inhalt |
|---|---|---|
| Software | dieses Repo, im Reisen-Repo als Submodul `frieda/` (`engine -> frieda/engine`) | Generator, Dienste, `betrieb/` mit Skripten und Vorlagen |
| Reisen-Repo | eigenes, privates Repo | `reisen/<reise>/`, `betrieb/einstellungen.env`, ein Meldeskript, eigene Tests unter `tests/` |
| Bauordner | Klon des Reisen-Repos auf dem Server, spiegelt nur `main` (`FR_WURZEL` der Units) | von hier wird gebaut, hier laufen Timer und Dienste; nie darin arbeiten (Abschnitt „Bauordner und Arbeitsordner“) |
| Arbeitsordner | eigener Klon des Reisen-Repos, Branches erlaubt | hier wird gearbeitet, über Pull Requests nach `main` |
| Arbeitskopie des Schreibwegs | `<Bauordner>-schreiben-<reise>` | Git-Worktree je Reise, legt der Dienst selbst an |
| Seiten | `<FR_SEITEN>/<reise>/` | gebaute Seiten, nginx liefert sie aus |
| Ablage | `<FR_ABLAGE>/<reise>/` (`eingang.jsonl`, `status.json`, `aufgaben.json`, …), `<FR_ABLAGE>/_neu/` (Anfragen nach neuen Reisen) | Eingaben der Mitreisenden; nie im Repo |
| Konten | `<FR_KONTEN>/` (`konten.db`, Dienst-Geheimnis) | Konten, Anmeldungen und Einladungen aller Nutzer der Instanz; nie im Repo, nie in einer Reise |
| Dienstordner | `<FR_DIENST>/` | Code der Dienste, Stände, Stempel, vorgemerkte Links, geheime Einstellungen |
| Konnektor-Zugänge | `<FR_KONNEKTOR>/zugaenge.json`, `seiten.json` (600) | geheime Links; nie im Repo |
| systemd | `<instanz>-rueckmeldungen`, `-konnektor`, `-schreiben`, `-veroeffentlichen.timer`, `-waechter.timer` | aus `betrieb/vorlagen/`, erzeugt von `einrichten.sh` |
| nginx | `<FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf` (mit Token), `<instanz>-konnektor.conf`, Zone in `conf.d/<instanz>-zone.conf` | aus `betrieb/vorlagen/` |

Die Skripte rufen sich im Reisen-Repo als `frieda/betrieb/<skript>.sh` auf und finden die Instanz selbst (das Repo, das die Software einbindet; sonst `FR_WURZEL`).

## Was wohin gehört

Drei Gruppen, die sich nie mischen sollen:

1. **Die Software** (dieses Repo): Code, Vorlagen, Werkzeuge. Auf dem Server liegt eine Kopie des Dienst-Codes in `<FR_DIENST>/*.py`, die `deploy.sh` anlegt. Sie ist für jede Instanz gleich und enthält nichts Eigenes.
2. **Die Daten einer Reisegruppe** (das Reisen-Repo und seine Ordner): Reisen, Seiten, Ablage mit Rückmeldungen, Aufträgen, Aufgaben und Belegen, Einstellungen und Meldeweg der Instanz.
3. **Daten der Nutzer**: Konten und Anmeldungen (`<FR_KONTEN>/`), Zugänge zum Konnektor (`<FR_KONNEKTOR>/`), Anfragen nach neuen Reisen (`<FR_ABLAGE>/_neu/`) und der Mailzugang (`konten.env`). Sie gehören nicht in das Reisen-Repo und gehören nicht einer einzelnen Reise.

Der Name der Instanz (`FR_INSTANZ`) steht vor Units, Zonen und nginx-Bausteinen und nennt nur diese Instanz, nicht die Software. Eine zweite Reisegruppe bekommt eine zweite Instanz mit eigenem Namen, eigenem Reisen-Repo und eigenen Ordnern, ihre Daten sind damit von denen der ersten getrennt (#15). Ein gemeinsamer Ort für mehrere Gruppen mit Trennung je Mandant ist #68.

## Der Kreislauf

1. **Schreiben:** Was im AI-Client über den Konnektor festgelegt wird (Arten, Merkmale, Werte, Dinge, Optionen, Entscheidungen, Fragen, Wissen, Personen, Status, Einstellungen, neue Reisen), prüft der **Schreibweg** nach den Regeln der Reise und schreibt es sofort nach `main` (siehe „Schreibweg“).
2. **Eingaben:** Rückmeldungen und Antworten von der Webseite und aus der Claude-App, Aufgaben und das Wunsch-Brett liegen live in der Ablage der Reise. Eine Organisator:in arbeitet Rückmeldungen im AI-Client ein (prüfen, mit den Schreibwerkzeugen eintragen, `rueckmeldung_erledigen` mit Kommentar); die Absender sehen „aufgenommen“, „passt nicht“ oder eine Rückfrage.
3. **Veröffentlichen:** `veroeffentlichen.sh` holt `main` in den Bauordner und ruft `deploy.sh` für jede Reise auf. Das geschieht gleich nach jedem Schreibvorgang und sonst alle 5 Minuten. Danach schaltet `freischalten.sh` neue Reisen frei und `zustellen.py` meldet neuen Reisen ihre Links.
4. **Erinnern:** `waechter.sh` läuft täglich, meldet Fristen, fällige Statuswechsel und zu alte Prüfdaten als Meldungen an die Personen; nachschlagen und eintragen tut der AI-Client im Gespräch.

Eine Änderung aus einer Sitzung (Claude Code im Reisen-Repo, nur Software und Betrieb) geht über einen PR nach `main` und von dort denselben Weg ab Schritt 3.

Bis zum 29.10.2026 stand zwischen Eingabe und Veröffentlichen der **Einarbeiten-Lauf** (`einarbeiten.sh`, Pfad-Wächter `<instanz>-einarbeiten.path`, Sammelzeit, ein Lauf von Claude Code je Reise, Aufträge `A-…`). Er ist mit ADR-0001 (Paket O-3) entfallen: Es gibt keinen zweiten KI-Lauf in Frieda, der Eingaben nachträglich deutet.

## Schreibweg

`engine/schreiben.py dienst` (`<instanz>-schreiben.service`, 127.0.0.1:`FR_SB_PORT`) nimmt vom Konnektor Anfragen `POST /<reise>/<werkzeug>` mit dem Dienst-Geheimnis an (`X-Frieda-Dienst`, dasselbe wie beim Rückmeldedienst). Er hält eine eigene Arbeitskopie `<Bauordner>-schreiben` (`FR_SCHREIBKOPIE`), einen Git-Worktree ohne eigenen Branch, den er selbst anlegt und vor jedem Schreibvorgang auf `origin/main` bringt. Ein Vorgang zur Zeit (Sperre `<FR_SPERREN>/<instanz>-schreiben.lock`):

1. Arbeitskopie holen (`origin/main`), eigene Reste verwerfen.
2. Mit dem Code **dieser Arbeitskopie** einen Unterprozess `schreiben.py anwenden` starten, damit Code und Daten denselben Stand haben; der Dienst selbst lädt nur `schreiben.py`, `konten.py`, `reise.py`, `instanz.py` aus `<FR_DIENST>` (`SB_MODULE` in `deploy.sh`).
3. Dort: Person und Rolle gegen `reise.yaml` der Reise prüfen (die Datei gilt vor dem, was der Konnektor sagt), Status (`reise.erlaubt`, Aktion `ontologie`), Form der Angaben; Datei ändern; Probebau (`bauen.Bauer(...).daten()`). Lehnt eine Prüfung ab, wird die Arbeitskopie zurückgesetzt, der AI-Client bekommt den Grund (HTTP 422).
4. Commit mit Reise, Titel, Text, Person, Werkzeug und Datum; `git push origin HEAD:main`. Kam inzwischen etwas anderes an, setzt er darauf auf (Rebase, höchstens dreimal); bei einem Konflikt bricht er ab und meldet „bitte noch einmal“.
5. `betrieb/veroeffentlichen.sh` im Hintergrund, mit `FR_WURZEL` des Bauordners. Hält der Timer die Sperre, holt er es in wenigen Minuten nach.

Die Routendatei (`plan/routen.yaml`; neue IDs über `ids.yaml`, Fragen in `offene-fragen.md`) schreibt er mit ruamel.yaml rund (Kommentare und Form bleiben; `engine/requirements.txt`, bei einer bestehenden Instanz einmal `engine/.venv/bin/pip install -r engine/requirements.txt`). Beim ersten Schreiben zieht er von Hand umbrochene Fließ-Mappings in eine Zeile; `python engine/schreiben.py normalisieren <reise>` tut das vorab in einer Sitzung, damit der erste Commit aus dem Gespräch nur seine Stelle ändert. Hat eine Reise noch keine Routendatei (neu aus der App angelegt), legt der erste Eintrag sie an: Start und Ende aus dem Zeitraum in `reise.yaml`, noch ohne Ort (`start_ende_setzen` ergänzt ihn). Sobald die Reise Arten hat, trägt der Schreibweg den Plan auch in `reise.json` ein (`routen.datei`), damit der Generator ihn liest.

Der Dienst läuft als Dienstbenutzer mit dessen `git`-Anmeldung (`gh` als Credential-Helfer, `PATH` aus `FR_PFAD`), ohne `ProtectHome`, weil die Arbeitskopie neben dem Repo liegt. `GET /gesund` antwortet `{"gesund": true}`, wenn das Repo erreichbar ist. Von Hand: `frieda/betrieb/…`: `FR_WURZEL=<Bauordner> engine/.venv/bin/python engine/schreiben.py vorbereiten` legt die Arbeitskopie an. Protokoll: `journalctl -u <instanz>-schreiben`. Eine Instanz ohne diesen Dienst setzt `KN_SCHREIBDIENST` nicht; der Konnektor bietet die Schreibwerkzeuge dann nicht an, und neue Reisen lassen sich aus der Claude-App nicht anlegen.

**Fehlerfälle:** Lehnt der Schreibweg ab (Rolle, Status, Form, Probebau), bleibt alles unverändert, und der AI-Client bekommt den Grund im Gespräch. Scheitert `git push` (Konflikt nach drei Versuchen, kein Netz), meldet er „bitte noch einmal“; nichts ist halb geschrieben. Bleibt der Dienst stehen (`failed`), sieht das der Monitor der Instanz (siehe „Überwachung“), der Konnektor meldet der Person „Schreibweg nicht erreichbar“.

## Belege

Belege zu Buchungen (Buchungsbestätigung, Ticket; `engine/belege.py`, #76, 29.10.2026) liegen in `<FR_ABLAGE>/<reise>/belege/` mit dem Verzeichnis `belege.json` daneben, nie im Repo und nie in den Web-Ordnern. Der Rückmeldedienst ist ihr einziger Schreiber (`POST /<reise>/belege/<B-id>`, nur angemeldet oder über den Dienst-Header, nie mit bloß eingetipptem Namen; die Buchung muss veröffentlicht sein, oder der Konnektor hat sie beim Schreibweg im Repo geprüft und schickt `X-Frieda-Buchung: im-repo` mit, damit der Beleg sofort nach dem Anlegen geht; Body ist die Datei, höchstens 10 MB, Typ am Inhalt geprüft: PDF, JPEG, PNG, WebP, HEIC, dazu Text als `.txt`/`.md` für die Abschrift einer Bestätigung aus dem Gespräch, Konnektor `beleg_anlegen`, Issue #135; 100 MB und 200 Dateien je Reise) und liefert sie aus (`GET /<reise>/belege/<D-id>`), nur an die hochladende Person und Organisator:innen, oder an alle, wenn eine Organisator:in den Beleg freigegeben hat. Nichts wird gelöscht; zurückgezogene Belege bleiben als Datei. Der nginx-Baustein der Reise hat dafür einen eigenen `location`-Block (`api/belege/`, `client_max_body_size 11m`); `freischalten.sh` erneuert den Baustein jeder Reise, wenn sich die Vorlage ändert (gleicher Pfad, nginx geprüft; der Pfad wird aus dem Baustein gelesen und muss nicht mit dem Ordner der Reise beginnen, etwa bei einem von Hand angelegten Baustein). Die Prüfungen vor dem Veröffentlichen laufen in einem eigenen Testordner (`--basetemp`), damit gleichzeitige pytest-Läufe auf demselben Rechner sie nicht stören. Belege gehören zur Sicherung der Ablage wie Rückmeldungen und Aufgaben.

## Kalender

Kalender (`engine/kalender.py`, #77) gibt es zweimal. **Je Reise als Datei:** Der Rückmeldedienst liefert `GET /<reise>/kalender.ics` (ganze Reise, `?id=<ID>` für ein Ding) aus den veröffentlichten Daten und den Aufgaben der Ablage, wie die Seite ohne Anmeldung, nur unter dem geheimen Link. **Je Person über alle Reisen:** Der Konnektor liefert das Abo unter `<FR_KN_ADRESSE>/kalender/<wort>.ics` (Kalender-Apps melden sich nicht an; das Wort ist je Konto aus dem Dienst-Geheimnis berechnet, nicht gespeichert) und den Download auf „Mein Konto“ (`/konto?kalender=datei`, angemeldet). Was darin steht, stellt jede Person auf „Mein Konto“ ein (Einträge, nur eigene Aufgaben, Erinnerungen, Reisen); die Einstellungen und ein Zähler für „neuer Link“ liegen in `konten.db`, Tabelle `kalender_abo`. Es zählen nur Reisen, in denen das Konto Mitglied ist; ein gesperrtes Konto hat kein Abo. nginx bleibt unverändert (Bausteine `api/` der Reise und `-mcp/` des Konnektors); der Konnektor braucht `KN_BASIS` (steht in der Vorlage `konnektor.service`). Nur Standardbibliothek, weil die Dienste mit dem Python des Systems laufen. Wird das Dienst-Geheimnis ersetzt, gelten alle Abo-Links nicht mehr.

## Zeitgrenzen und Sperren des Schreibwegs

Ein Schreibvorgang darf samt Wartezeit auf die Sperre nicht länger dauern als der Konnektor wartet (`proxy_read_timeout 30s` in `nginx-konnektor.conf`), sonst erreicht die Meldung die Claude-App nie (#118). Darum gilt (`engine/schreiben.py`; ein Test prüft die Summe gegen die nginx-Vorlage): `ZEIT_GESAMT = 25` Sekunden für Sperre, Vorbereiten der Arbeitskopie (jeder `git`-Aufruf mit dem Rest der Frist) und Anwenden zusammen, davon höchstens `ZEIT_SPERRE = 3` Wartezeit auf die Sperre, und danach `ZEIT_PRUEFUNG = 3` Sekunden Reserve für die Ergebnisprüfung. Eine Antwort kommt also nach höchstens 28 Sekunden. Wer die nginx-Grenze ändert, prüft die Werte mit.

Das Anwenden läuft als Unterprozess in eigener Prozessgruppe; bei Fristablauf wird die ganze Gruppe beendet, auch ein laufendes `git push`. Jeder Vorgang bekommt eine kurze Kennung, die als Zeile `Frieda-Vorgang: <Kennung>` in der Commit-Nachricht steht. Nach einem Abbruch im Anwenden holt der Schreibweg `origin/main` und sucht die Kennung (beides zusammen höchstens `ZEIT_PRUEFUNG`). Die Meldungen:

| Fall | Code | Meldung | Protokoll |
|------|------|---------|-----------|
| eingetragen trotz Abbruch | 200 | „Es hat länger gedauert, ist aber eingetragen.“ | `Zeit <werkzeug> 504: abgebrochen, eingetragen` |
| nicht eingetragen (Abbruch im Vorbereiten oder Kennung nicht gefunden) | 504 | „… ist nicht eingetragen; bitte noch einmal versuchen.“ | `Zeit <werkzeug> 504: abgebrochen, nicht eingetragen` |
| Prüfung nicht möglich (`origin` nicht erreichbar) | 504 | „… bitte prüfen, ob es angekommen ist.“ | `Zeit <werkzeug> 504: abgebrochen, ungeprüft` |
| Sperre belegt | 429 | „… bitte gleich noch einmal versuchen.“ | `Gesperrt <werkzeug> 429: …` |
| abgelehnt | 422 | Grund der Regel | `Abgelehnt <werkzeug> 422: <Grund>` (#121) |
| unerwarteter Fehler im Dienst | 500 | „Schreiben fehlgeschlagen (Fehler im Dienst) …“ | `Fehler <werkzeug> 500: <Art>: <Text>` |

Ein Restrisiko bleibt: Wird ein `git push` im Moment der Übertragung beendet, kann der Eintrag noch ankommen, nachdem „nicht eingetragen“ gemeldet wurde; eine Wiederholung kann ihn dann doppelt eintragen.

Ein beendetes `git` kann Sperrdateien (`index.lock` u. ä.) hinterlassen. Vor dem Vorbereiten entfernt der Schreibweg darum veraltete `*.lock` im eigenen git-Ordner der Arbeitskopie (`<Repo>/.git/worktrees/<Name>/`); das ist sicher, weil er dabei die Sperre der Reise hält. Sperren im gemeinsamen git-Ordner des Repos fasst er nicht an, dort arbeiten andere Reisen und das Veröffentlichen.

Sperre und Arbeitskopie (`<wurzel>-schreiben-<reise>`) gibt es je Reise (#119): Was bei einer Reise hängt, hält die anderen nicht auf. Das Protokoll des Schreibwegs (`journalctl -u <instanz>-schreiben`) nennt Ablehnungen mit Werkzeug und Grund (einzeilig, höchstens 200 Zeichen) und für jeden Vorgang mit jedem Code eine Zeile `Fertig <werkzeug> <code> in <Sekunden> s`. An diesen Dauern lässt sich prüfen, ob `ZEIT_GESAMT` für große Reisen reicht.

## Sprachen

Die Texte der Software stehen in `engine/texte_<kürzel>.py`. `deploy.sh` nimmt jede Sprachdatei im Ordner `engine/` von selbst in die Modullisten von Rückmeldedienst, Konnektor und Schreibweg auf (`SPRACHDATEIEN`); eine neue Sprache braucht dort keinen Eintrag ([sprachen.md](sprachen.md)). Die Sprache einer Person steht in der Spalte `konten.sprache` der Kontendatenbank; auf einer vorhandenen Datenbank fügt der erste Start des neuen Stands die Spalte selbst hinzu (`ALTER TABLE`), von Hand ist nichts zu migrieren. Die Sprache einer Reise steht in ihrer `reise.yaml`; fehlt das Feld, gilt `de`. Meldungen des Wächters (`meldungen.jsonl`) und der Kalender folgen der Sprache der Reise.

## Veröffentlichen

`betrieb/veroeffentlichen.sh` holt `origin/main`, spult den Bauordner vor und bringt das Submodul auf den festgehaltenen Stand. Danach laufen die Tests einmal. Dann ruft es `deploy.sh` für jede Reise mit `reise.json` auf und gibt ihm den geprüften Stand mit (`FR_GEPRUEFT`), damit die Tests nicht je Reise erneut laufen. Der Lauf hat niedrige Priorität (`Nice=10`, `IOSchedulingPriority=7` im Dienst `veroeffentlichen.service`; der Schreibweg startet ihn mit `nice` und `ionice`), damit Schreibvorgänge während der Tests nicht warten (#120); fehlen `nice` oder `ionice`, startet er ohne sie. Die Ausgabe dieses angestoßenen Laufs geht nach `/dev/null`: Sonst hielte das Skript die Leitung zum Schreibweg bis zu seinem Ende offen, und jeder Schreibvorgang wartete darauf. Verloren geht dabei nichts Wesentliches: Ein Erfolg zeigt sich an `<FR_DIENST>/veroeffentlichen-erfolg` und am Heartbeat, ein Infrastrukturfehler wird vom Timer wiederholt, ein roter Stand wird übersprungen und meldet sich nach der Schwelle selbst (unten); die Ausgabe des Timers steht im Protokoll (`journalctl -u <instanz>-veroeffentlichen`). Gemerkt wird der Stand in `<FR_DIENST>/veroeffentlicht`. Nur ein ganz gelungener Lauf merkt ihn. Ist der Ordner nicht auf `main` oder nicht sauber, überspringt es den Lauf. `--immer` veröffentlicht auch ohne neuen Stand und prüft auch einen bekannten roten Stand neu.

**Was sperrt (#142):** Eine Inhaltsfrage einer Reise hält das Veröffentlichen nie an. Sperren können nur zwei Dinge:

- **Tests der Software rot** (`pytest engine/tests`): Keine Reise wird angefasst, Exit 1.
- **Bau einer Reise gescheitert** (Baufehler, `deploy.sh` endet mit Exit 2): Nur diese Reise bleibt auf ihrem letzten guten Stand, die anderen werden gebaut und freigeschaltet. Der Lauf endet mit Exit 1, der Stand wird nicht gemerkt.

Warnungen im Plan sperren nie, weder im Bau noch im Schreibweg (dort stehen neue Warnungen als Hinweise in der Antwort). Die Tests in `tests/` des Reisen-Repos laufen danach weiter, sperren aber nicht: Sind sie rot, steht „Warnung: Tests des Reisen-Repos rot (sperren nicht)“ im Protokoll, und der Betrieb bekommt je Commit einmal eine Nachricht (`normal`; Merker `<FR_DIENST>/veroeffentlichen-warnung`).

**Rot-Datei:** Ein roter Stand steht in `<FR_DIENST>/veroeffentlichen-rot`, Zeilen `schluessel=wert`: `commit` (der rote Stand), `art` (`software` oder `reise`), `reisen` (die roten Reisen, durch Komma), `seit` (Beginn der Rot-Phase, UTC) und `gemeldet` (`1`, wenn der Alarm an den Betrieb raus ist). Eine Rot-Phase reicht vom ersten roten Lauf bis zum nächsten ganz grünen; ein neuer roter Commit ändert `commit`, `art` und `reisen`, `seit` und `gemeldet` bleiben. Ein ganz grüner Lauf löscht die Datei.

**Kein Wiederholen ohne Änderung:** Kommt der nächste Lauf auf denselben roten Commit, steht „Bekannter roter Stand …, übersprungen“ im Protokoll: keine Tests, kein Bau, Exit 0, aber **kein Stempel und kein Heartbeat** (Rot ist kein fachlicher Erfolg). Neu geprüft wird bei einem neuen Commit oder mit `--immer`. Ein Baufehler, der nur durch etwas außerhalb des Repos verschwindet, braucht `--immer`. Infrastrukturfehler werden dagegen nicht gemerkt und vom Timer wiederholt: Vorspulen oder Submodul scheitern, `deploy.sh` endet mit Exit 1 (dann endet auch die Schleife über die Reisen sofort).

**Alarm:** Ist ein Stand seit `FR_ROT_MELDEN_NACH_MINUTEN` Minuten rot (Vorgabe 30, Einstellungen), geht bei jedem Lauf, der das Rot kennt (auch beim Überspringen), die Alarmprüfung los: einmal je Rot-Phase `high` an den Betrieb („Veröffentlichen seit … Minuten rot“, mit Art, Reisen und Commit). Kommt die Nachricht nicht an, bleibt `gemeldet=0` und der nächste Lauf versucht es wieder. Bei roten Reisen legt `engine/waechter.py rot-melden --reisen <a,b> --seit <seit>` dazu je Reise eine Meldung an deren Organisator:innen an (sie sehen sie im Konnektor); der Schlüssel enthält Reise und `seit`, darum kommt sie je Phase nur einmal. Bei roter Software geht nur der Alarm an den Betrieb.

**Konvention für `tests/` des Reisen-Repos:** Inhaltsschnappschüsse (feste Warnungslisten, Tageszahlen, Summen, Bildanzahlen) im `tests/` des Reisen-Repos sperren nicht und gehören dort gekennzeichnet oder entfernt: Jede Änderung über den Schreibweg kann sie rot machen, ohne dass etwas kaputt ist. Das gilt ebenso für den Workflow „Software nachziehen“ (#168): Er sperrt nur bei roten `engine/tests` oder einer Reise, die nicht baut; rote `tests/` sind dort eine Warnung im Lauf. Was wirklich sperren soll, gehört als Regel des Baus in die Software (eigenes Issue, gemessen an `docs/adr/0001-kern.md`), nicht als Schnappschuss.

`FR_WURZEL=<Bauordner> betrieb/deploy.sh <reise>` (sonst von `veroeffentlichen.sh` aufgerufen) baut, führt die Tests der Software aus (`engine/tests`, außer der Stand ist schon geprüft) und kopiert die Seite nach `<FR_SEITEN>/<reise>/`. Exit-Codes: 0 gelungen, Exit 2 Bau dieser Reise gescheitert (vor jeder Wirkung, die Seite bleibt auf dem letzten guten Stand), 1 alles andere (`FR_WURZEL` fehlt, Ordner nicht auf `main`, Reise oder Ordner fehlt, ungesicherte Änderungen, Tests rot, Dienste nicht bereit). Es legt die Ablage der Reise an und kopiert den Code der Dienste nach `<FR_DIENST>/`. Die Liste der Module steht im Skript, ein Test prüft sie gegen die Importe. Bei geändertem Code startet es die Dienste neu (`sudo -n systemctl restart`). Am Ende prüft es Seite, Rückmeldedienst und Konnektor.

## Neue Reise freischalten

Ohne Handarbeit (`docs/neue-reise.md`): Nach dem Veröffentlichen ruft `veroeffentlichen.sh` für jede Reise `freischalten.sh <reise>` auf.

- **Neue Reise:** Sie bekommt einen nginx-Baustein aus `vorlagen/nginx-reise.conf` mit einem neuen Zufalls-Token (root, 640). Dann `nginx -t`; bei einem Fehler wird der Baustein wieder entfernt. Danach lädt nginx neu. Bis die neuen Pfade gelten, vergeht ein Moment; die Prüfung des neuen Links versucht es deshalb bis zu zehnmal im Sekundenabstand.
- **Prüfung:** Seite und `api/gesund` müssen mit 200 antworten.
- **Link:** Der Link zur Seite kommt nach `seiten.json` (für `meine_reisen`).
- **Vorgemerkte Links:** Links neuer Reisen aus der App merkt der Konnektor in `<FR_KONNEKTOR>/neue-reisen-ausstehend.jsonl` vor (neben den Zugängen; den Dienstordner darf der Konnektor nicht beschreiben). Das Veröffentlichen stellt sie zu (`betrieb/zustellen.py`), sobald die Seite online ist, als Meldung an die Person oder bei einem Konto als Verknüpfung mit der Reise und Einladung per Mail.

Links von Hand: `freischalten.sh <reise>` für die Seite, `freischalten.sh <reise> --person <schlüssel>` für die Claude-App. Links stehen nie im Protokoll, im Repo, in Issues oder Nachrichten.

## Wächter

`betrieb/waechter.sh` läuft täglich und ruft `engine/waechter.py lauf` auf (`docs/waechter.md`). Es berücksichtigt nur Reisen mit Baustein `waechter` und Status `fest` oder `unterwegs`. Hat es etwas zu melden, geht eine Sammelnachricht an den Betreiber; ein Fehler wird dringend gemeldet.

## Einstellungen

`betrieb/einstellungen.env` im Reisen-Repo (Vorlage `betrieb/einstellungen.beispiel`) enthält Zeilen `NAME=wert`, ohne Shell-Auswertung. Was schon in der Umgebung steht, gilt vor der Datei. Geheimes gehört nicht dorthin, sondern nach `<FR_DIENST>/betrieb.env` (600, gleiche Form). Das ist die Datei, die die Units als `EnvironmentFile` laden. Mailweg und Konten stehen in `<FR_DIENST>/konten.env` (`docs/konten.md`).

| Name | Vorgabe | Bedeutung |
|---|---|---|
| `FR_INSTANZ` | `frieda` | Name der Instanz: Units, nginx-Bausteine, Sperren, Drossel-Zone |
| `FR_TITEL` | `Frieda` | Kurzname in Nachrichten |
| `FR_ADRESSE` | – | öffentliche Adresse der Seiten (nötig zum Freischalten) |
| `FR_KN_ADRESSE` | `<FR_ADRESSE>/<FR_INSTANZ>-mcp` | Adresse des Konnektors |
| `FR_UMZUG_NACH` | leer | neue Adresse der Seiten bei einem Umzug auf eine andere Domain: Der Generator baut dann einen Service Worker, der gespeicherte Seiten verwirft und sich abmeldet, und eine Seite, die auf denselben Pfad der neuen Adresse weiterleitet. Erst danach darf der Server von der alten Adresse umleiten (ein umgeleitetes `sw.js` lehnt der Browser als Update ab). Kann auch als `bauen.py --umzug-nach` übergeben werden |
| `FR_SEITEN`, `FR_ABLAGE`, `FR_DIENST`, `FR_KONNEKTOR`, `FR_KONTEN` | `/srv/<instanz>`, darunter `_rueckmeldungen`, `_dienst`, `_konnektor`, `_konten` | Ordner auf dem Server |
| `FR_RM_PORT`, `FR_KN_PORT`, `FR_SB_PORT` | `8771`, `8772`, `8773` | Ports auf 127.0.0.1 (Rückmeldedienst, Konnektor, Schreibweg) |
| `FR_SCHREIBKOPIE` | `<Wurzel>-schreiben` | Arbeitskopie des Schreibwegs (Git-Worktree, legt der Dienst an) |
| `FR_PYTHON` | `<Wurzel>/engine/.venv/bin/python` | Python mit den Paketen der Software |
| `FR_MELDEN` | leer | Meldeweg (unten) |
| `FR_ROT_MELDEN_NACH_MINUTEN` | `30` | Minuten Rot beim Veröffentlichen bis zum Alarm (Veröffentlichen) |
| `FR_NGINX_SNIPPETS`, `FR_SUDO` | `/etc/nginx/snippets`, `sudo -n` | nginx-Bausteine und Rechte |
| `FR_SPERREN` | `/tmp` | Ordner der Sperrdateien |
| `FR_BENUTZER`, `FR_GRUPPE`, `FR_HOME`, `FR_PFAD` | aufrufender Benutzer | nur für `einrichten.sh`: Benutzer und `PATH` der Dienste |
| `FR_HEARTBEAT_VEROEFFENTLICHEN` | leer | Überwachungsadresse, nur in `betrieb.env` |
| `FR_KENNUNG`, `FR_SPRACHEN` | Name der Software, `de,en` | Kennung mit Kontakt gegenüber OpenStreetMap und Sprachen der Namen (`docs/werkzeuge.md`) |

Die Skripte setzen daraus die Umgebung der Software (`RM_ABLAGE`, `KN_SEITEN`, `KN_ZUGAENGE`, `KN_BASIS`; die Unit des Konnektors zusätzlich `KN_SCHREIBDIENST`). Ausdrücklich gesetzte Werte bleiben. Fehlt etwas, etwa bei einem Aufruf von Hand wie `python3 engine/rueckmeldungen.py liste <reise>` in der Wurzel des Reisen-Repos, leitet `engine/instanz.py` die Ordner nach derselben Ordnung ab, notfalls aus der Einstellungsdatei. Die Software selbst kennt keine Instanz, ihre letzte Vorgabe ist `/srv/frieda`.

**Meldeweg:** `FR_MELDEN` ist eine ausführbare Datei der Instanz (ein relativer Pfad gilt ab der Wurzel des Reisen-Repos), aufgerufen als `<befehl> <normal|high> <betreff> <text> [erledigt]`. `erledigt` heißt: Das ist ein reiner Bericht, es ist nichts zu tun. Fehler kommen ohne `erledigt` und sollen offen bleiben, bis jemand sie ansieht. Wie die Nachricht ankommt (Mail, Telegram, eine Warteschlange), entscheidet die Instanz in ihrem Skript.

## Seiten prüfen (angemeldet, im echten Browser)

Die Reiseseiten verlangen eine Anmeldung (E-Mail und Code). Für Prüfungen der veröffentlichten Seiten gilt der übliche Weg von Playwright: ein eigenes Konto mit den geringsten Rechten, die Sitzung außerhalb des Browsers erzeugen und als Cookie einsetzen (`storageState`). Die Anmeldung selbst wird nicht nachgespielt und bekommt keine Hintertür. `betrieb/pruefsitzung.py <datei.json> [--stunden 2]` legt beim ersten Mal das Konto `pruefung@<Adresse der Seiten>` an (kein Mitglied einer Reise, sieht nur, was eine fremde Person mit dem Link sieht), stellt eine kurze Sitzung aus und schreibt sie als storageState (Rechte 600, nie ins Repo). Der Aufruf geschieht als Dienstbenutzer mit den Werten der Instanz (`RM_SEITEN` oder `FR_KONTEN`, `FR_KN_ADRESSE`). Im Browser: `browser.newContext({storageState: "<datei>"})`, dann die Adresse der Reise mit dem geheimen Pfad öffnen. Das Prüfkonto liest damit alle Reiseseiten; schreiben darf es nirgends.

## Überwachung

Nach fachlichem Erfolg berühren die Läufe Stempel in `<FR_DIENST>/`: `veroeffentlichen-erfolg` (nichts Neues oder alles veröffentlicht; nicht bei einem roten oder übersprungenen roten Stand) und `waechter-erfolg`. Ein roter Stand meldet sich selbst: nach `FR_ROT_MELDEN_NACH_MINUTEN` Minuten (Vorgabe 30) einmal je Rot-Phase an den Betrieb, bei roten Reisen auch an deren Organisator:innen (Veröffentlichen, Rot-Datei `<FR_DIENST>/veroeffentlichen-rot`). Ein Monitor der Instanz meldet, wenn ein Stempel zu alt ist (etwa 2 h beim Veröffentlichen, 36 h beim Wächter), ein Dienst `failed` ist oder der Schreibweg auf `127.0.0.1:<FR_SB_PORT>/gesund` nicht mit `{"gesund": true}` antwortet. Wer einen Heartbeat-Dienst hat, setzt `FR_HEARTBEAT_VEROEFFENTLICHEN`: Die Adresse wird nur nach Erfolg zusätzlich abgerufen. Seiten, `api/gesund` und der Konnektor unter `/gesund` lassen sich von außen prüfen.

Der Workflow „Software nachziehen“ (siehe „Neue Instanz einrichten“) läuft auf GitHub und hinterlässt auf dem Server keinen Stempel. Einen Fehlschlag meldet GitHub per Mail. Für die Überwachung prüft der Monitor der Instanz das Ergebnis: Der eingebundene Stand im Bauordner (`.git/modules/frieda/HEAD`, nur lesen) darf nicht länger als etwa 6 h im Rückstand gegen `main` der Software sein (`git ls-remote`). Gezählt wird ab dem Zeitpunkt, an dem der Monitor den Rückstand für diesen Stand zum ersten Mal sieht, nicht ab dem Datum der Commits, die nach dem Vorspulen oft Stunden später auf `main` kommen. Das deckt Workflow, Tests und Veröffentlichen zusammen ab.

## Neue Instanz einrichten

1. **Server:** Benutzer für die Dienste, nginx mit HTTPS für die Adresse, Python 3, `git`, `rsync`, `flock`, Node 22 (Browser-Prüfung in den Tests) und `gh`, als dieser Benutzer angemeldet (Credential-Helfer für `git push` des Schreibwegs). Claude Code ist auf dem Server nicht nötig.
2. **Reisen-Repo:** neues privates Repo mit der Software als Submodul:
   ```
   git submodule add https://github.com/henemm/frieda-reist frieda
   ln -s frieda/engine engine
   mkdir -p reisen betrieb && cp frieda/betrieb/einstellungen.beispiel betrieb/einstellungen.env
   ```
   Werte eintragen; ein Meldeskript ist optional. In `.gitignore`: `dist/`, `reisen/*/medien/karte`.
   **Software nachziehen:** `cp frieda/betrieb/software-nachziehen.yml .github/workflows/` (dazu ein `tests.yml`, das `python -m pytest -q -rs engine/tests tests` ausführt). Der Workflow braucht die Rechte `contents: write` und `issues: write`, die er selbst anfordert. In den Einstellungen des Repos müssen Actions erlaubt sein, mit Schreibrechten für `GITHUB_TOKEN`. Alle 30 Minuten zieht er das Submodul auf den neuen Stand von `main` der Software, als Commit des Bots. Das Tor ist dasselbe wie beim Veröffentlichen: Sperren können nur die Tests der Software (`engine/tests`) und der Bau jeder Reise; rote Tests des Reisen-Repos (`tests/`) sind nur eine Warnung im Lauf. Sperrt das Tor, legt er ein Issue mit dem Label `software-nachziehen` an. Änderungen an der Vorlage werden von Hand übernommen (Datei neu kopieren).
3. **Bauordner auf dem Server:** Klon des Reisen-Repos als Dienstbenutzer, `git submodule update --init`. Danach `python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt`. `git fetch` muss ohne Rückfrage gehen. Lokale Dateien, die nicht ins Repo gehören (etwa `.claude/settings.json`), kommen in `.git/info/exclude`, sonst gilt der Ordner als belegt und das Veröffentlichen setzt aus.
4. **Einrichten:** `frieda/betrieb/einrichten.sh` prüft die Voraussetzungen. Es erzeugt Units und nginx-Bausteine in einem Ordner und zeigt die Befehle zum Aktivieren. Außerhalb dieses Ordners ändert es nichts. `--installieren` legt nach Rückfrage die Ordner an und kopiert Units und Bausteine nach `/etc`.
5. **nginx:** Im server-Block der Adresse `include <FR_NGINX_SNIPPETS>/<instanz>-*.conf;` eintragen, `nginx -t`, neu laden.
6. **sudo** für den Dienstbenutzer, ohne Passwort und nur für diese Befehle:
   - `systemctl restart <instanz>-rueckmeldungen <instanz>-konnektor <instanz>-schreiben`
   - `nginx -t` und `systemctl reload nginx`
   - `install`, `test`, `cat` und `rm` für Dateien in `<FR_NGINX_SNIPPETS>/<instanz>-*.conf`
7. **Erste Reise** anlegen (`docs/neue-reise.md`), nach `main` bringen, im Bauordner `FR_WURZEL=<Bauordner> frieda/betrieb/deploy.sh <reise>` (legt den Code der Dienste an). Danach `sudo systemctl enable --now <instanz>-rueckmeldungen <instanz>-konnektor <instanz>-schreiben` und die beiden Timer, wie `einrichten.sh` sie nennt.
8. **Prüfen:** `FR_WURZEL=<Bauordner> frieda/betrieb/veroeffentlichen.sh --immer` zeigt „ist online“. Mit `freischalten.sh <reise> --person <schlüssel>` bekommt jede Person ihren Link, den sie in der Claude-App einträgt (`docs/konnektor.md`). `curl -s 127.0.0.1:<FR_SB_PORT>/gesund` antwortet `{"gesund": true}`.

**Zwei Instanzen auf einem Server** brauchen verschiedene `FR_INSTANZ`, `FR_SEITEN` (und damit Ablage und Dienstordner) und Ports. `einrichten.sh` bricht ab, wenn eine andere installierte Instanz dieselben Ports nutzt. Unit-Namen, nginx-Bausteine, Drossel-Zone und Sperrdateien tragen den Namen der Instanz. Jede Instanz braucht einen eigenen Konnektor-Pfad (`<instanz>-mcp`).

## Bauordner und Arbeitsordner

Der **Bauordner** spiegelt nur `main`. Timer, Schreibweg und Wächter laufen von dort, ihre Units nennen ihn mit `FR_WURZEL`. Von Hand wird darin nichts geändert, kein Branch ausgecheckt und nichts committet. Sonst setzt das Veröffentlichen aus (es überspringt jeden Lauf, solange der Ordner nicht auf `main` oder nicht sauber ist). `deploy.sh` und `veroeffentlichen.sh` laufen nur mit `FR_WURZEL`. `deploy.sh` baut außerdem nur, wenn der Ordner auf dem Branch `main` steht. Ein Aufruf aus einem anderen Klon bricht damit ab, statt von dort zu veröffentlichen (#137). Was nicht im Repo liegt, hat der Bauordner selbst: die Python-Umgebung (`engine/.venv`), die Werkzeuge (`engine/.bin`) und die Grundkarten. Eine neue Grundkarte kommt mit `FR_WURZEL=<Bauordner> frieda/werkzeuge/karte-holen.sh <reise>` direkt dorthin (ignorierte Dateien, `main` bleibt sauber), danach `FR_WURZEL=<Bauordner> frieda/betrieb/veroeffentlichen.sh --immer`.

Gearbeitet wird in einem eigenen **Arbeitsordner**, einem normalen Klon mit eigener Python-Umgebung und Branches. Er wird über Pull Requests nach `main` gebracht, danach holt der Timer den Stand in den Bauordner. Die Software selbst wird nur in ihrem eigenen Repo geändert. Im Reisen-Repo ändert sich das Submodul `frieda/` nur durch einen Versionswechsel (Workflow „Software nachziehen“).

## Zurückrollen und sperren

- **Seite:** den schlechten Stand auf `main` mit `git revert <commit>` zurücknehmen (in einem Arbeitsordner, über einen PR). Der Timer veröffentlicht den neuen Stand, der Service Worker bietet den alten Inhalt als neue Version an. Im Bauordner wird nichts ausgecheckt.
- **Dienste:** der Code liegt in `<FR_DIENST>/`. Ein Revert der Software (neuer Stand des Submoduls auf `main`) bringt den alten Code beim nächsten Veröffentlichen zurück.
- **Link sperren:** Eintrag aus `zugaenge.json` löschen (Konnektor, wirkt sofort) bzw. den Token im nginx-Baustein ändern (Seite).

## Wenn etwas klemmt

| Anzeichen | Erster Blick |
|---|---|
| Seite antwortet nicht | `ls <FR_SEITEN>/<reise>/index.html`, `sudo nginx -t`, Fehlerlog von nginx |
| `api/gesund` antwortet nicht | `systemctl status <instanz>-rueckmeldungen`, `journalctl -u <instanz>-rueckmeldungen -n 50` |
| Konnektor `gesund` 503 | `zugaenge.json` unlesbar, keine Reise freigeschaltet (`seiten.json`) und kein alter Link, oder eine freigeschaltete oder verlinkte Reise nicht veröffentlicht |
| Konnektor meldet „Schreibweg nicht erreichbar“ oder „nicht eingerichtet“ | `systemctl status <instanz>-schreiben`, `journalctl -u <instanz>-schreiben -n 50`; steht `KN_SCHREIBDIENST` in der Unit des Konnektors? Geht `git push` als Dienstbenutzer ohne Rückfrage? |
| Nichts geht online | `journalctl -u <instanz>-veroeffentlichen -n 50`; ist der Bauordner auf `main` und sauber? |
| Eingetragenes erscheint nicht auf der Seite | `journalctl -u <instanz>-schreiben -n 50` (Commit und Push da?), dann `journalctl -u <instanz>-veroeffentlichen -n 50` |
| Rückmeldungen bleiben „neu“ | Das ist kein Fehler: Eine Organisator:in arbeitet sie im AI-Client ein (`rueckmeldungen`, dann `rueckmeldung_erledigen`); `python3 engine/rueckmeldungen.py liste <reise>` zeigt sie auf dem Server |
