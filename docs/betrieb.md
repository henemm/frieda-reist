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
| Ablage | `<FR_ABLAGE>/<reise>/` (`eingang.jsonl`, `status.json`, `aufgaben.json`, …) | Eingaben der Mitreisenden; nie im Repo |
| Konten | `<FR_KONTEN>/` (`konten.db`, Dienst-Geheimnis, `sicherung/konten.db`, `neu/` mit Anfragen nach neuen Reisen und Meldungen an Personen) | Konten, Anmeldungen, Einladungen und alles Personenbezogene ohne Reise; nie im Repo, nie in einer Reise |
| Reisespeicher | `<FR_SPEICHER>/` (`reisen.db`, `sicherung/reisen.db`; Vorgabe `<FR_SEITEN>/_speicher`) | Reisedaten als unveränderliche Versionen in SQLite (`engine/reisespeicher.py`, [ADR-0008](adr/0008-reisespeicher.md), #346); in Stufe 1 schreibt nur der Betreiber hinein, der Schreibweg bleibt auf Git |
| Dienstordner | `<FR_DIENST>/` | Code der Dienste, Stände, Stempel, vorgemerkte Links, geheime Einstellungen |
| Konnektor-Zugänge | `<FR_KONNEKTOR>/zugaenge.json`, `seiten.json` (600) | geheime Links; nie im Repo |
| systemd | `<instanz>-rueckmeldungen`, `-konnektor`, `-schreiben`, `-push`, `-veroeffentlichen.timer`, `-waechter.timer` | aus `betrieb/vorlagen/`, erzeugt von `einrichten.sh` |
| nginx | `<FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf` (mit Token), `<instanz>-konnektor-orte.inc` mit `<instanz>-konnektor.inc`, Zone in `conf.d/<instanz>-zone.conf` | aus `betrieb/vorlagen/` |

Die Skripte rufen sich im Reisen-Repo als `frieda/betrieb/<skript>.sh` auf und finden die Instanz selbst (das Repo, das die Software einbindet; sonst `FR_WURZEL`).

## Was wohin gehört

Drei Gruppen, die sich nie mischen sollen:

1. **Die Software** (dieses Repo): Code, Vorlagen, Werkzeuge. Auf dem Server liegt eine Kopie des Dienst-Codes in `<FR_DIENST>/*.py`, die `deploy.sh` anlegt. Sie ist für jede Instanz gleich und enthält nichts Eigenes.
2. **Die Daten einer Reisegruppe** (das Reisen-Repo und seine Ordner): Reisen, Seiten, Ablage mit Rückmeldungen, Aufträgen, Aufgaben und Belegen, Einstellungen und Meldeweg der Instanz.
3. **Daten der Nutzer**: Konten und Anmeldungen (`<FR_KONTEN>/`), Zugänge zum Konnektor (`<FR_KONNEKTOR>/`), Anfragen nach neuen Reisen samt Meldungen an Personen (`<FR_KONTEN>/neu/`, Rechte 700) und der Mailzugang (`konten.env`). Sie gehören nicht in das Reisen-Repo und gehören nicht einer einzelnen Reise. Betriebsdaten des Konnektors bleiben in `<FR_KONNEKTOR>/` (`seiten.json`, `neue-reisen-ausstehend.jsonl`; `zugaenge.json` entfällt mit den alten Links, #43).

**Sicherung:** Das Server-Backup sichert `<FR_KONTEN>/` und `<FR_ABLAGE>/`. Die Reisen selbst liegen im Reisen-Repo, die Seiten entstehen daraus neu. `konten.db` läuft im WAL-Modus; eine Kopie der Datei im laufenden Betrieb kann unbrauchbar sein. Darum schreibt der Wächter-Lauf täglich einen sauberen Schnappschuss über die Backup-API von SQLite nach `<FR_KONTEN>/sicherung/konten.db` (`engine/konten.py sichern`, geprüft mit `integrity_check`, ohne WAL-Dateien). Zurückholen: Dienste anhalten, den Schnappschuss als `<FR_KONTEN>/konten.db` einsetzen (alte `-wal`/`-shm` entfernen), Dienste starten.

**Reisespeicher (#346, [ADR-0008](adr/0008-reisespeicher.md)):** `<FR_SPEICHER>/reisen.db` hält die Reisedaten als Versionen, nur anhängen (Ordner 700, Datei 600, WAL). Der Wächter-Lauf schreibt täglich einen Schnappschuss nach `<FR_SPEICHER>/sicherung/reisen.db` (`engine/reisespeicher.py sichern`, wie bei den Konten über die Backup-API, geprüft mit `integrity_check`, ohne WAL-Dateien); scheitert ein Schnappschuss, bleibt die letzte gute Sicherung stehen. Das Wegbringen außer Haus ist Sache des Server-Backups der Instanz: Es muss `<FR_SPEICHER>/sicherung/` mitsichern, spätestens sobald der Schreibweg in den Speicher schreibt (Stufe 2, #347); bis dahin ist der Speicher nur eine Kopie. Zurückholen: Schreiber anhalten, den Schnappschuss als `<FR_SPEICHER>/reisen.db` einsetzen (alte `-wal`/`-shm` entfernen), dann `engine/reisespeicher.py pruefen` (muss `ok` melden) und zur Kontrolle eine Reise mit `engine/reisespeicher.py exportieren <reise> <leerer Ordner>` ausgeben und mit dem erwarteten Stand vergleichen. Weitere Befehle: `importieren <ordner> <reise> <wer> [--grund TEXT] [--ab N]`, `verlauf <reise> [n]`, `exportieren <reise> <ziel> [--bis N]` (auch ein alter Stand), `zuruecksetzen <reise> <bis> <wer> <grund>` (ein neuer Vorgang, der Verlauf bleibt). Der Schutz gegen Ändern und Löschen hält Software-Fehler und Fehlbedienung ab, nicht jemanden mit Schreibzugriff auf die Datei; `pruefen` rechnet deshalb alle Prüfsummen nach.

**Umzug von `_neu` (#72, 1.11.2026):** Früher lagen Anfragen und Meldungen ohne Reise in `<FR_ABLAGE>/_neu/`. Dieser Ort gilt weiter, solange in `<FR_KONTEN>/neu/` nichts liegt. Umziehen bei angehaltenen Diensten: `mv <FR_ABLAGE>/_neu <FR_KONTEN>/neu && chmod 700 <FR_KONTEN>/neu`.

Der Name der Instanz (`FR_INSTANZ`) steht vor Units, Zonen und nginx-Bausteinen und nennt nur diese Instanz, nicht die Software. Eine zweite Reisegruppe bekommt eine zweite Instanz mit eigenem Namen, eigenem Reisen-Repo und eigenen Ordnern, ihre Daten sind damit von denen der ersten getrennt (#15). Ein gemeinsamer Ort für mehrere Gruppen mit Trennung je Mandant ist #68.

## Datenschutz je Instanz (#15)

Jede Instanz ist für ihre Daten selbst verantwortlich; es wird nichts mit anderen Instanzen geteilt. Die Software legt fest, wer was sieht und wie gelöscht wird. Der Betreiber der Instanz legt die Aufbewahrung der Sicherungen fest.

| Daten | Wer sieht sie | Löschen auf Wunsch einer Person | Aufbewahrung |
|---|---|---|---|
| Konto (Adresse, Name, Sprache, Geräte, Kalender-Abo, Benachrichtigungen) | die Person selbst („Mein Konto“); der Betreiber in der Datenbank | Konto löschen (Mein Konto oder `engine/konten.py loeschen <adresse>`): Mitgliedschaften, Anfragen, Abos und Anmeldungen (auch der Claude-App) entfallen, die Adresse ist wieder frei | bis zum Löschen |
| Namen in Verlauf und Reise-Stand (Git-Verlauf der Reise) | alle Mitglieder der Reise | bleiben bewusst stehen, weil der Verlauf nur wächst (`main` wird nicht umgeschrieben) | dauerhaft mit der Reise |
| Reise (Pläne, Personen, Entscheidungen) | Mitglieder nach Rolle (`reisend`, `einbringer`, `bestimmer`), nie öffentlich ohne Link | die Reise liegt im Reisen-Repo der Gruppe; über sie entscheidet die Gruppe | bis die Gruppe sie entfernt |
| Rückmeldungen, Aufgaben, Antworten (Ablage) | Organisator:innen der Reise, Absender sehen ihre eigenen | nur durch den Betreiber in der Ablage | bis zum Löschen der Reise |
| Belege zu Buchungen | hochladende Person und Organisator:innen, bei Freigabe alle der Reise | werden nie vom Dienst gelöscht, zurückgezogene bleiben als Datei; Löschen nur durch den Betreiber in `<FR_ABLAGE>/<reise>/belege/` | bis zum Löschen der Reise |
| Sicherungen (Konten-Schnappschuss, Archiv der Ablage) | nur der Betreiber | verschwinden mit der Aufbewahrungsfrist der Sicherung | Frist bestimmt der Betreiber der Instanz |

Die KI-Läufe gehören nicht dazu: Frieda enthält keine eigene KI, Reiseinhalte entstehen im AI-Client der Person über den Konnektor (ADR-0001). Es fallen auf dem Server keine Kosten für KI-Läufe an.

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
5. `betrieb/veroeffentlichen.sh` im Hintergrund, mit `FR_WURZEL` des Bauordners. Hält ein anderer Lauf die Sperre, merkt das Skript das (`<FR_DIENST>/veroeffentlichen-nochmal`), und der laufende Lauf veröffentlicht danach gleich noch einmal (#230).
6. Den neuen Reise-Stand (Nummer, Zeit, Commit) schreibt der Schreibweg nach `<FR_DIENST>/reise-stand/<reise>.gesichert.json`; die Antwort an den Konnektor nennt ihn und den veröffentlichten (Abschnitt „Reise-Stand“).

Die Routendatei (`plan/routen.yaml`; neue IDs über `ids.yaml`, Fragen in `offene-fragen.md`) schreibt er mit ruamel.yaml rund (Kommentare und Form bleiben; `engine/requirements.txt`, bei einer bestehenden Instanz einmal `engine/.venv/bin/pip install -r engine/requirements.txt`). Beim ersten Schreiben zieht er von Hand umbrochene Fließ-Mappings in eine Zeile; `python engine/schreiben.py normalisieren <reise>` tut das vorab in einer Sitzung, damit der erste Commit aus dem Gespräch nur seine Stelle ändert. Hat eine Reise noch keine Routendatei (neu aus der App angelegt), legt der erste Eintrag sie an: Start und Ende aus dem Zeitraum in `reise.yaml`, noch ohne Ort (`start_ende_setzen` ergänzt ihn). Sobald die Reise Arten hat, trägt der Schreibweg den Plan auch in `reise.json` ein (`routen.datei`), damit der Generator ihn liest, dazu die Abschnitte für Tagesplan und Unterkünfte (`routen.tagesplan`, `routen.unterkuenfte`, neue `W-…`), damit die Seite die Tage zeigt.

Der Dienst läuft als Dienstbenutzer mit dessen `git`-Anmeldung (`gh` als Credential-Helfer, `PATH` aus `FR_PFAD`), ohne `ProtectHome`, weil die Arbeitskopie neben dem Repo liegt. `GET /gesund` antwortet `{"gesund": true}`, wenn das Repo erreichbar ist. Von Hand: `frieda/betrieb/…`: `FR_WURZEL=<Bauordner> engine/.venv/bin/python engine/schreiben.py vorbereiten` legt die Arbeitskopie an. Protokoll: `journalctl -u <instanz>-schreiben`. Eine Instanz ohne diesen Dienst setzt `KN_SCHREIBDIENST` nicht; der Konnektor bietet die Schreibwerkzeuge dann nicht an, und neue Reisen lassen sich aus der Claude-App nicht anlegen.

**Fehlerfälle:** Lehnt der Schreibweg ab (Rolle, Status, Form, Probebau), bleibt alles unverändert, und der AI-Client bekommt den Grund im Gespräch. Scheitert `git push` (Konflikt nach drei Versuchen, kein Netz), meldet er „bitte noch einmal“; nichts ist halb geschrieben. Bleibt der Dienst stehen (`failed`), sieht das der Monitor der Instanz (siehe „Überwachung“), der Konnektor meldet der Person „Schreibweg nicht erreichbar“.

## Belege

Belege zu Buchungen (Buchungsbestätigung, Ticket; `engine/belege.py`, #76, 29.10.2026) liegen in `<FR_ABLAGE>/<reise>/belege/` mit dem Verzeichnis `belege.json` daneben, nie im Repo und nie in den Web-Ordnern. Der Rückmeldedienst ist ihr einziger Schreiber (`POST /<reise>/belege/<B-id>`, nur angemeldet oder über den Dienst-Header, nie mit bloß eingetipptem Namen; die Buchung muss veröffentlicht sein, oder der Konnektor hat sie beim Schreibweg im Repo geprüft und schickt `X-Frieda-Buchung: im-repo` mit, damit der Beleg sofort nach dem Anlegen geht; Body ist die Datei, höchstens 10 MB, Typ am Inhalt geprüft: PDF, JPEG, PNG, WebP, HEIC, dazu Text als `.txt`/`.md` für die Abschrift einer Bestätigung aus dem Gespräch, Konnektor `beleg_anlegen`, Issue #135; 100 MB und 200 Dateien je Reise) und liefert sie aus (`GET /<reise>/belege/<D-id>`), nur an die hochladende Person und Organisator:innen, oder an alle, wenn eine Organisator:in den Beleg freigegeben hat. Nichts wird gelöscht; zurückgezogene Belege bleiben als Datei. Der nginx-Baustein der Reise hat dafür einen eigenen `location`-Block (`api/belege/`, `client_max_body_size 11m`); `freischalten.sh` erneuert den Baustein jeder Reise, wenn sich die Vorlage ändert (gleicher Pfad, nginx geprüft; der Pfad wird aus dem Baustein gelesen und muss nicht mit dem Ordner der Reise beginnen, etwa bei einem von Hand angelegten Baustein). Die Prüfungen vor dem Veröffentlichen laufen in einem eigenen Testordner (`--basetemp`), damit gleichzeitige pytest-Läufe auf demselben Rechner sie nicht stören. Belege gehören zur Sicherung der Ablage wie Rückmeldungen und Aufgaben.

## Kalender

Kalender (`engine/kalender.py`, #77) gibt es zweimal. **Je Reise als Datei:** Der Rückmeldedienst liefert `GET /<reise>/kalender.ics` (ganze Reise, `?id=<ID>` für ein Ding) aus den veröffentlichten Daten und den Aufgaben der Ablage, wie die Seite ohne Anmeldung, nur unter dem geheimen Link. **Je Person über alle Reisen:** Der Konnektor liefert das Abo unter `<FR_KN_ADRESSE>/kalender/<wort>.ics` (Kalender-Apps melden sich nicht an; das Wort ist je Konto aus dem Dienst-Geheimnis berechnet, nicht gespeichert) und den Download auf „Mein Konto“ (`/konto?kalender=datei`, angemeldet). Was darin steht, stellt jede Person auf „Mein Konto“ ein (Einträge, nur eigene Aufgaben, Erinnerungen, Reisen); die Einstellungen und ein Zähler für „neuer Link“ liegen in `konten.db`, Tabelle `kalender_abo`. Es zählen nur Reisen, in denen das Konto Mitglied ist; ein gesperrtes Konto hat kein Abo. nginx: Baustein `api/` der Reise und `/kalender/` im Baustein des Konnektors; der Konnektor braucht `KN_BASIS` (steht in der Vorlage `konnektor.service`). Nur Standardbibliothek, weil die Dienste mit dem Python des Systems laufen. Wird das Dienst-Geheimnis ersetzt, gelten alle Abo-Links nicht mehr.

Das Abo folgt dem, was Kalender-Programme erwarten (1.11.2026, nach dem Fehler im Apple Kalender): Die Adresse ist HTTPS mit gültigem Zertifikat; Apple-Geräte holen `webcal://` über HTTPS und fragen nur, wenn das scheitert, ob es „ohne SSL“ gehen soll. Vor dem Laden prüfen Apps die Adresse mit `HEAD`, `OPTIONS` oder `PROPFIND` (ist das CalDAV?); der Konnektor antwortet darauf mit 200, 204 (`Allow: GET, HEAD, OPTIONS`) und 405, nie mit 501, das ein Abo scheitern lässt. Jede Antwort trägt ein `ETag` (ohne `DTSTAMP` berechnet) und `Cache-Control: private, no-cache`; fragt die App mit `If-None-Match`, kommt bei gleichem Inhalt 304. Der Kalender trägt `NAME`, `X-WR-CALNAME`, `REFRESH-INTERVAL` und `X-PUBLISHED-TTL` (6 Stunden) und bleibt auch leer gültig (eine Zeitzone UTC statt keines Bestandteils, RFC 5545). Das Abo spricht die Sprache des Kontos. „Mein Konto“ und der Konnektor geben je Programm den passenden Weg: `webcal://` (iPhone, iPad, Mac, Outlook für Windows), Google Kalender („Kalender hinzufügen“ über `calendar.google.com/calendar/render?cid=`), Outlook im Web (`outlook.live.com/calendar/0/addfromweb`) und die https-Adresse zum Kopieren. Google und Outlook im Web holen das Abo von ihren eigenen Servern; die Adresse muss deshalb aus dem Internet erreichbar sein und darf nicht nach Herkunft oder User-Agent sperren. Der server-Block der Instanz (nicht Teil der Bausteine) soll `http://` mit 301 auf `https://` umleiten, damit auch der Weg „ohne SSL“ ankommt. Jede Antwort des Konnektors trägt den Kopf `X-Frieda: konnektor`; `deploy.sh` fragt nach jedem Deploy `/gesund`, `/anmelden`, `/kalender/…`, `/schrift/…` und `/favicon.svg` über `FR_KN_ADRESSE` ab und warnt und meldet (`FR_MELDEN`), wenn ein Weg bei nginx statt beim Konnektor endet (so blieb das Abo der ersten Instanz unbemerkt hinter einer 404-Seite von nginx). Beim Veröffentlichen geschieht das einmal je Lauf nach dem Freischalten aller Reisen (`wege_pruefen` in `gemeinsam.sh`, `FR_WEGE_SPAETER`), nicht je Reise: Die Abrufe kommen vom Server selbst und zählen in nginx in dieselbe Begrenzung wie die Prüfung von `freischalten.sh`, je Reise abgefragt bekamen die letzten Reisen 429. Prüfen von außen: `curl -I <abo-adresse>` (200, `text/calendar`), `curl -X OPTIONS -i <abo-adresse>` (204), `curl -X PROPFIND -i <abo-adresse>` (405).

## Zeitgrenzen und Sperren des Schreibwegs

Ein Schreibvorgang darf samt Wartezeit auf die Sperre nicht länger dauern, als nginx auf den Konnektor wartet (`proxy_read_timeout`: 300 s für `/mcp` in `nginx-konnektor-orte.inc`, sonst die Vorgabe von nginx mit 60 s, Begründung in `nginx-konnektor.inc`; bis 1.11.2026 30 s), sonst erreicht die Meldung die Claude-App nie (#118, #163). Darum gilt (`engine/schreiben.py`; ein Test prüft die Summe gegen jede Lesefrist der nginx-Vorlage): `ZEIT_GESAMT = 25` Sekunden für Sperre, Vorbereiten der Arbeitskopie (jeder `git`-Aufruf mit dem Rest der Frist) und Anwenden zusammen, davon höchstens `ZEIT_SPERRE = 3` Wartezeit auf die Sperre, und danach `ZEIT_PRUEFUNG = 3` Sekunden Reserve für die Ergebnisprüfung. Eine Antwort kommt also nach höchstens 28 Sekunden. Wer die nginx-Grenze ändert, prüft die Werte mit.

Das Anwenden läuft als Unterprozess in eigener Prozessgruppe; bei Fristablauf wird die ganze Gruppe beendet, auch ein laufendes `git push`. Jeder Vorgang bekommt eine kurze Kennung, die als Zeile `Frieda-Vorgang: <Kennung>` in der Commit-Nachricht steht. Nach einem Abbruch im Anwenden holt der Schreibweg `origin/main` und sucht die Kennung (beides zusammen höchstens `ZEIT_PRUEFUNG`). Die Meldungen:

| Fall | Code | Meldung | Protokoll |
|------|------|---------|-----------|
| eingetragen trotz Abbruch | 200 | „Es hat länger gedauert, ist aber eingetragen.“ | `Timeout <werkzeug> 504: aborted, saved` |
| nicht eingetragen (Abbruch im Vorbereiten oder Kennung nicht gefunden) | 504 | „… ist nicht eingetragen; bitte noch einmal versuchen.“ | `Timeout <werkzeug> 504: aborted, not saved` |
| Prüfung nicht möglich (`origin` nicht erreichbar) | 504 | „… bitte prüfen, ob es angekommen ist.“ | `Timeout <werkzeug> 504: aborted, unchecked` |
| Sperre belegt | 429 | „… bitte gleich noch einmal versuchen.“ | `Locked <werkzeug> 429: …` |
| abgelehnt | 422 | Grund der Regel | `Rejected <werkzeug> 422: <Grund>` (#121) |
| unerwarteter Fehler im Dienst | 500 | „Schreiben fehlgeschlagen (Fehler im Dienst) …“ | `Error <werkzeug> 500: <Art>: <Text>` |

Ein Restrisiko bleibt: Wird ein `git push` im Moment der Übertragung beendet, kann der Eintrag noch ankommen, nachdem „nicht eingetragen“ gemeldet wurde; eine Wiederholung kann ihn dann doppelt eintragen.

Ein beendetes `git` kann Sperrdateien (`index.lock` u. ä.) hinterlassen. Vor dem Vorbereiten entfernt der Schreibweg darum veraltete `*.lock` im eigenen git-Ordner der Arbeitskopie (`<Repo>/.git/worktrees/<Name>/`); das ist sicher, weil er dabei die Sperre der Reise hält. Sperren im gemeinsamen git-Ordner des Repos fasst er nicht an, dort arbeiten andere Reisen und das Veröffentlichen.

Sperre und Arbeitskopie (`<wurzel>-schreiben-<reise>`) gibt es je Reise (#119): Was bei einer Reise hängt, hält die anderen nicht auf. Betriebsprotokolle (stderr, Journal) sind englisch, unabhängig von der Sprache der Personen (ADR-0006). Das Protokoll des Schreibwegs (`journalctl -u <instanz>-schreiben`) nennt Ablehnungen mit Werkzeug und Grund (einzeilig, höchstens 200 Zeichen) und für jeden Vorgang mit jedem Code eine Zeile `Done <werkzeug> <code> in <Sekunden> s`. An diesen Dauern lässt sich prüfen, ob `ZEIT_GESAMT` für große Reisen reicht.

## Sprachen

Die Texte der Software stehen in `engine/texte_<kürzel>.py`. `deploy.sh` nimmt jede Sprachdatei im Ordner `engine/` von selbst in die Modullisten von Rückmeldedienst, Konnektor und Schreibweg auf (`SPRACHDATEIEN`); eine neue Sprache braucht dort keinen Eintrag ([sprachen.md](sprachen.md)). Die Sprache einer Person steht in der Spalte `konten.sprache` der Kontendatenbank; auf einer vorhandenen Datenbank fügt der erste Start des neuen Stands die Spalte selbst hinzu (`ALTER TABLE`), von Hand ist nichts zu migrieren. Die Sprache einer Reise steht in ihrer `reise.yaml`; fehlt das Feld, bricht der Bau (`pruefung.reise.sprache_fehlt`), `neu.py nachziehen` trägt `de` ein. Meldungen des Wächters (`meldungen.jsonl`) und der Kalender folgen der Sprache der Reise.

## Veröffentlichen

`betrieb/veroeffentlichen.sh` holt `origin/main`, spult den Bauordner vor und bringt das Submodul auf den festgehaltenen Stand. Hat das Vorspulen die Einstellungsdatei geändert (Prüfsumme davor und danach; Erscheinen oder Verschwinden zählt mit), schreibt es „Settings changed by the update, restarting.“ ins Protokoll und startet sich mit denselben Argumenten neu, höchstens einmal je Lauf, damit Bau und Freischalten schon die neuen Werte nutzen (#242). Die Prüfungen laufen überall in derselben Umgebung (#202): `engine/requirements.txt` hält jede Bibliothek mit Version und Hash fest (erzeugt mit pip-tools aus `engine/requirements.in`, Befehl steht dort), `engine/tests/playwright/package-lock.json` die Playwright-Version. CI installiert genau diese Stände und prüft zusätzlich mit nachgestellten Einstellungen einer Instanz. `veroeffentlichen.sh` installiert sie vor den Prüfungen nach, wenn sich eine der Listen geändert hat: die Bibliotheken in `FR_PYTHON` (Prüfsumme in `<FR_DIENST>/requirements.sha256`; danach starten Schreibweg und Push-Dienst beim ersten Deploy des Laufs neu), Playwright mit `npm ci` in eine eigene Kopie `<FR_DIENST>/playwright` (Browser ohne `--with-deps`, die Systembibliotheken gehören zur Einrichtung), die die Prüfungen über `PLAYWRIGHT_MODUL` bekommen. Scheitert eine Installation, endet der Lauf ohne Prüfung und Bau, und der nächste versucht es wieder. Eine neue Bibliothek oder Version kommt also nur über einen Commit, den CI in derselben Umgebung geprüft hat. Danach laufen die Tests einmal. Dann ruft es `deploy.sh` für jede Reise mit `reise.json` auf und gibt ihm den geprüften Stand mit (`FR_GEPRUEFT`), damit die Tests nicht je Reise erneut laufen. Der Lauf hat niedrige Priorität (`Nice=10`, `IOSchedulingPriority=7` im Dienst `veroeffentlichen.service`; der Schreibweg startet ihn mit `nice` und `ionice`), damit Schreibvorgänge während der Tests nicht warten (#120); fehlen `nice` oder `ionice`, startet er ohne sie. Die Ausgabe dieses angestoßenen Laufs geht nach `/dev/null`: Sonst hielte das Skript die Leitung zum Schreibweg bis zu seinem Ende offen, und jeder Schreibvorgang wartete darauf. Verloren geht dabei nichts Wesentliches: Ein Erfolg zeigt sich an `<FR_DIENST>/veroeffentlichen-erfolg` und am Heartbeat, ein Infrastrukturfehler wird vom Timer wiederholt, ein roter Stand wird übersprungen und meldet sich nach der Schwelle selbst (unten); die Ausgabe des Timers steht im Protokoll (`journalctl -u <instanz>-veroeffentlichen`). Gemerkt wird der Stand in `<FR_DIENST>/veroeffentlicht`. Nur ein ganz gelungener Lauf merkt ihn. Ist der Ordner nicht auf `main` oder nicht sauber, überspringt es den Lauf. `--immer` veröffentlicht auch ohne neuen Stand und prüft auch einen bekannten roten Stand neu.

**Was sperrt (#142):** Eine Inhaltsfrage einer Reise hält das Veröffentlichen nie an. Sperren können nur zwei Dinge:

- **Tests der Software rot** (`pytest engine/tests`): Keine Reise wird angefasst, Exit 1.
- **Bau einer Reise gescheitert** (Baufehler, `deploy.sh` endet mit Exit 2): Nur diese Reise bleibt auf ihrem letzten guten Stand, die anderen werden gebaut und freigeschaltet. Der Lauf endet mit Exit 1, der Stand wird nicht gemerkt.

Warnungen im Plan sperren nie, weder im Bau noch im Schreibweg (dort stehen neue Warnungen als Hinweise in der Antwort). Die Tests in `tests/` des Reisen-Repos laufen danach weiter, sperren aber nicht: Sind sie rot, steht „Warnung: Tests des Reisen-Repos rot (sperren nicht)“ im Protokoll, und der Betrieb bekommt je Commit einmal eine Nachricht (`normal`; Merker `<FR_DIENST>/veroeffentlichen-warnung`).

**Rot-Datei:** Ein roter Stand steht in `<FR_DIENST>/veroeffentlichen-rot`, Zeilen `schluessel=wert`: `commit` (der rote Stand), `art` (`software` oder `reise`), `reisen` (die roten Reisen, durch Komma), `seit` (Beginn der Rot-Phase, UTC), `gemeldet` (`1`, wenn der Alarm an den Betrieb raus ist), `umgebung` (Fingerabdruck der Prüfumgebung: installierte Bibliotheken, Python, Node, Playwright), `geprueft` (Zeit der letzten Prüfung, Sekunden seit 1970) und `tests` (die ersten roten Tests mit der ersten Fehlerzeile; der Alarm nennt sie). Eine Rot-Phase reicht vom ersten roten Lauf bis zum nächsten ganz grünen; ein neuer roter Commit ändert `commit`, `art` und `reisen`, `seit` und `gemeldet` bleiben. Ein ganz grüner Lauf löscht die Datei.

**Kein Wiederholen ohne Änderung:** Kommt der nächste Lauf auf denselben roten Commit, steht „Known red state …, skipped“ (Bekannter roter Stand) im Protokoll: keine Tests, kein Bau, Exit 0, aber **kein Stempel und kein Heartbeat** (Rot ist kein fachlicher Erfolg). Neu geprüft wird bei einem neuen Commit, mit `--immer` und von selbst (#203): sofort, wenn sich die Umgebung geändert hat (ein Fehler, den eine Installation behebt, heilt so ohne Eingriff), und bei roter Software zusätzlich, wenn die letzte Prüfung länger als `FR_ROT_NEU_PRUEFEN_MINUTEN` (Vorgabe 60) zurückliegt; eine rote Reise ist ein Inhaltsfehler und wartet auf einen neuen Commit. `seit` und `gemeldet` bleiben dabei, es gibt also keinen zweiten Alarm. Eine Rot-Datei ohne Fingerabdruck (von vor #203) wird einmal geprüft. Ein Baufehler, der nur durch etwas anderes außerhalb des Repos verschwindet, braucht `--immer`. Infrastrukturfehler werden dagegen nicht gemerkt und vom Timer wiederholt: Vorspulen oder Submodul scheitern, `deploy.sh` endet mit Exit 1 (dann endet auch die Schleife über die Reisen sofort).

**Alarm:** Ist ein Stand seit `FR_ROT_MELDEN_NACH_MINUTEN` Minuten rot (Vorgabe 30, Einstellungen), geht bei jedem Lauf, der das Rot kennt (auch beim Überspringen), die Alarmprüfung los: einmal je Rot-Phase `high` an den Betrieb („Veröffentlichen seit … Minuten rot“, mit Art, Reisen und Commit). Kommt die Nachricht nicht an, bleibt `gemeldet=0` und der nächste Lauf versucht es wieder. Bei roten Reisen legt `engine/waechter.py rot-melden --reisen <a,b> --seit <seit>` dazu je Reise eine Meldung an deren Organisator:innen an (sie sehen sie im Konnektor); der Schlüssel enthält Reise und `seit`, darum kommt sie je Phase nur einmal. Bei roter Software geht nur der Alarm an den Betrieb.

**Konvention für `tests/` des Reisen-Repos:** Inhaltsschnappschüsse (feste Warnungslisten, Tageszahlen, Summen, Bildanzahlen) im `tests/` des Reisen-Repos sperren nicht und gehören dort gekennzeichnet oder entfernt: Jede Änderung über den Schreibweg kann sie rot machen, ohne dass etwas kaputt ist. Das gilt ebenso für den Workflow „Software nachziehen“ (#168): Er sperrt nur bei roten `engine/tests` oder einer Reise, die nicht baut; rote `tests/` sind dort eine Warnung im Lauf. Was wirklich sperren soll, gehört als Regel des Baus in die Software (eigenes Issue, gemessen an `docs/adr/0001-kern.md`), nicht als Schnappschuss.

`FR_WURZEL=<Bauordner> betrieb/deploy.sh <reise>` (sonst von `veroeffentlichen.sh` aufgerufen) baut, führt die Tests der Software aus (`engine/tests`, außer der Stand ist schon geprüft) und kopiert die Seite nach `<FR_SEITEN>/<reise>/`. Exit-Codes: 0 gelungen, Exit 2 Bau dieser Reise gescheitert (vor jeder Wirkung, die Seite bleibt auf dem letzten guten Stand), 1 alles andere (`FR_WURZEL` fehlt, Ordner nicht auf `main`, Reise oder Ordner fehlt, ungesicherte Änderungen, Tests rot, Dienste nicht bereit). Es legt die Ablage der Reise an und kopiert den Code der Dienste nach `<FR_DIENST>/`. Die Liste der Module steht im Skript, ein Test prüft sie gegen die Importe. Bei geändertem Code startet es die Dienste neu (`sudo -n systemctl restart`). Am Ende prüft es Seite, Rückmeldedienst und Konnektor.

## Neue Reise freischalten

Ohne Handarbeit (`docs/neue-reise.md`): Nach dem Veröffentlichen ruft `veroeffentlichen.sh` für jede Reise `freischalten.sh <reise>` auf.

- **Neue Reise:** Sie bekommt einen nginx-Baustein aus `vorlagen/nginx-reise.conf` mit einem neuen Zufalls-Token (root, 640). Dann `nginx -t`; bei einem Fehler wird der Baustein wieder entfernt. Danach lädt nginx neu. Bis die neuen Pfade gelten, vergeht ein Moment; die Prüfung des neuen Links versucht es deshalb bis zu zehnmal im Sekundenabstand.
- **Prüfung:** Seite und `api/gesund` müssen mit 200 antworten. Eine 429 kommt von der Anfragebegrenzung in nginx (je IP, gemeinsam für die API aller Reisen; der Server fragt sich selbst von außen ab), nicht von der Reise: Die Prüfung wartet dann 5 s und fragt erneut, bis zu sechsmal (`FS_429_WARTEN`, `FS_429_VERSUCHE`, #198). Vorher blieben neue Reisen dadurch ohne Verknüpfung mit dem Konto, bis ein späterer Lauf sie freischaltete.
- **Link:** Der Link zur Seite kommt nach `seiten.json` (für `meine_reisen`).
- **Vorgemerkte Links:** Links neuer Reisen aus der App merkt der Konnektor in `<FR_KONNEKTOR>/neue-reisen-ausstehend.jsonl` vor (neben den Zugängen; den Dienstordner darf der Konnektor nicht beschreiben). Das Veröffentlichen stellt sie zu (`betrieb/zustellen.py`), sobald die Seite online ist, als Meldung an die Person oder bei einem Konto als Verknüpfung mit der Reise und Einladung per Mail.

Links von Hand: `freischalten.sh <reise>` für die Seite, `freischalten.sh <reise> --person <schlüssel>` für die Claude-App. Links stehen nie im Protokoll, im Repo, in Issues oder Nachrichten.

## Reise-Stand (Epic #223)

Jede Reise trägt eine fortlaufende Nummer, den **Reise-Stand**: die Zahl der Commits auf `main`, die `reisen/<reise>/` ändern (`engine/stand.py`). Jeder gesicherte Schreibvorgang erhöht sie um 1, ein Software-Update (Submodul) lässt sie stehen; weil `main` nur wächst, enthält Stand 43 alles aus Stand 42. In einem flachen Klon fehlt die Nummer (wie die des Releases). Der Bau legt sie mit den letzten zehn Änderungen (Zeit, Person, was; Person aus der Zeile `Frieda-Person:` des Schreibwegs, sonst der Autor des Commits) in die Seite (`daten.reise_stand`); eine Bauzeit steht nicht darin, gleicher Inhalt gibt weiter dieselbe Seite.

Weg eines Stands: **gesichert** (Schreibweg) → **wird gebaut** → **veröffentlicht** (die Seite liegt auf dem Server) → **auf dem Gerät** (nur die Person sieht das, im Fuß). Scheitert der Bau, ist der Zustand **fehlgeschlagen** mit dem Grund (Meldungen von `bauen.py`), und der bisherige Stand bleibt sichtbar; rote Prüfungen der Software melden sich ebenso, mit den roten Tests. Die Dateien in `<FR_DIENST>/reise-stand/` haben je einen Schreiber: `<reise>.gesichert.json` der Schreibweg, `<reise>.lauf.json` `veroeffentlichen.sh` (Zustand, Nummer, Zeit des Sicherns, seit wann, Dauer, Grund). Veröffentlicht ist, was `<FR_SEITEN>/<reise>/daten.json` nennt.

Abgefragt wird nur auf dem Server: Der Rückmeldedienst antwortet unter `api/stand` (die Seite; der Service Worker lässt `api/` nie über seinen Speicher), der Konnektor mit `veroeffentlichung_pruefen` (`publish_status`, `docs/konnektor.md`). Zeiten stehen dort als UTC mit `Z`; die Seite zeigt sie in der Ortszeit des Geräts, der Konnektor in der Zeitzone der Person mit Angabe der Zone (sonst `FR_ZEITZONE`, Vorgabe UTC; #227).

**Zeitziel 2 Minuten** vom Sichern bis zur Veröffentlichung (Product Owner, E3, 2.11.2026; #230). Gemessen wird je Reise: `veroeffentlichen.sh` schreibt nach dem Bau „Published <reise> state <n>, <s> s after saving.“ ins Protokoll, über dem Ziel als Warnung, und die Dauer nach `<reise>.lauf.json`; `veroeffentlichung_pruefen` zeigt sie gegen das Ziel, auch während ein Stand noch wartet. Ursache der 15 Minuten vom 2.11.2026 (Baustein um 09:32 gesetzt, um 09:47 sichtbar), aus dem Ablauf des Skripts: Jeder neue Commit auf `main`, auch ein reiner Inhaltsstand, ließ die ganze Prüfung der Software laufen (`engine/tests` mit Browsertests, auf der Instanz mehrere Minuten) und danach alle Reisen bauen; fand der Anstoß des Schreibwegs die Sperre eines laufenden Timer-Laufs belegt, wurde er übersprungen, und der Stand wartete bis zum nächsten Timer-Lauf (5 Minuten) samt dessen voller Prüfung. Seitdem:

- Ein **reiner Inhaltsstand** (seit dem zuletzt ganz veröffentlichten Stand nur Änderungen unter `reisen/`) baut nur die geänderten Reisen (und die zuletzt roten, damit ihr Rot bestehen bleibt, bis ihr Bau gelingt) und überspringt die Prüfungen der Software, die für genau diese Software schon grün waren (`FR_GEPRUEFT` auf den Stand gesetzt).
- Ein **Software-Wechsel** (alles außerhalb von `reisen/`, auch das Submodul, oder ohne bekannten Stand, oder `--immer`) prüft weiter vollständig und baut alle Reisen. Nur dann laufen die Tests des Reisen-Repos, nach dem Bauen, damit sie keinen Stand aufhalten.
- Ein Anstoß, der die Sperre belegt findet, legt `<FR_DIENST>/veroeffentlichen-nochmal` an; der laufende Lauf startet am Ende gleich noch einmal, statt auf den Timer zu warten.

## Anstoß „Veröffentlichen“ von der Seite

Die Seite kann nur holen, was auf dem Server liegt. Der Fuß jeder Seite fragt auf „Auf Neueres prüfen“ zuerst den Server (Update des Service Workers): Liegt dort ein neuer Stand, heißt der Knopf „Jetzt aktualisieren“ und übernimmt ihn (mit Rückfall: feuert der Wechsel nicht, lädt die Seite nach 4 Sekunden trotzdem neu). Ist nur `main` der Software neuer, nennt der Fuß die Zahl der Stände und sagt, dass sie noch nicht auf dem Server sind. Organisator:innen (angemeldet) bekommen dazu „Veröffentlichen anstoßen“: Der Rückmeldedienst legt `<FR_ABLAGE>/_anstoss.json` an (Zeit, Reise, Person; ein Anstoß gilt, bis er abgeholt ist). Der nächste Lauf von `veroeffentlichen.sh` (Timer, höchstens 5 Minuten) startet damit `gh workflow run <FR_NACHZIEHEN_WORKFLOW> --ref main` im Bauordner, schreibt das Ergebnis nach `<FR_ABLAGE>/_anstoss-ergebnis.json` und löscht den Anstoß. Der Workflow „Software nachziehen“ prüft und übernimmt den neuen Stand wie zur halben Stunde; ein späterer Lauf veröffentlicht ihn. Mit Push-Nachrichten bekommen alle eine Nachricht, sobald das neue Release online ist; Tippen darauf öffnet die Seite mit `?aktualisieren=1`, und die Seite übernimmt den neuen Stand selbst.

Voraussetzung: `gh` ist für den Dienstbenutzer angemeldet und darf Workflows des Reisen-Repos starten (Recht `actions: write`, beim klassischen Token `repo`). Scheitert der Start, steht `ok: false` im Ergebnis (die Seite sagt „Der letzte Anstoß ist gescheitert“) und der Betrieb bekommt eine Nachricht (`normal`).

## Push-Nachrichten

`engine/push.py dienst` (`<instanz>-push.service`) stellt Push-Nachrichten zu (Issue #21, Kanal `push` in `docs/waechter.md`). Er läuft mit `FR_PYTHON`, weil der Versand `pywebpush` braucht (`engine/requirements.txt`; bei einer bestehenden Instanz einmal `engine/.venv/bin/pip install -r engine/requirements.txt`), und lädt seinen Code aus `<FR_DIENST>` (`PS_MODULE` in `deploy.sh`, Neustart bei geändertem Code, wenn die Unit eingeschaltet ist). Alle 20 Sekunden liest er, was in den Reisen neu ist (`meldungen.jsonl`, `eingang.jsonl`, `aufgaben.json` der Ablage und das Release im Fuß der veröffentlichten Seite), merkt sich den Stand in `konten.db` (`push_stand`; beim ersten Lauf nur merken) und stellt die Nachrichten aus der Warteschlange (`push_warteschlange`) zu, außerhalb der Ruhezeit der Person. Was 36 Stunden nicht zugestellt werden konnte, fällt weg; ein Abo, das der Push-Dienst des Browsers nicht mehr kennt (404, 410), wird gelöscht.

- **Schlüssel:** Das VAPID-Schlüsselpaar legt der erste Start an (`konten.db`, Tabelle `push_schluessel`); `engine/push.py schluessel` zeigt den öffentlichen. Ihn bringt „Mein Konto“ für den Schalter mit (`data-schluessel`); ohne ihn bietet die Seite keine Benachrichtigungen an. Wird der Schlüssel ersetzt, müssen alle Geräte neu einschalten.
- **Geräte:** Abos je Gerät in `konten.db` (`push_abos`: Adresse beim Push-Dienst, Schlüssel, Reise und Adresse der Seite, Zeitzone), höchstens 10 je Konto. Sperren, Löschen und „Auf allen Geräten ausschalten“ (Mein Konto) entfernen sie.
- **Link der Nachricht:** die Adresse der Seite aus einem Abo derselben Reise, sonst aus `seiten.json` neben den Konnektor-Zugängen (`KN_ZUGAENGE`).
- **Kontakt:** `FR_BASIS` aus `konten.env` steht als Absender in der VAPID-Unterschrift.
- **Probe:** `FR_KONTEN=… RM_ABLAGE=… engine/.venv/bin/python <FR_DIENST>/push.py probe <email>` schickt eine Nachricht an alle Geräte eines Kontos. Protokoll: `journalctl -u <instanz>-push`.
- **Frieda-App (Entscheidung A, 2.11.2026):** Ein- und ausgeschaltet wird je Gerät auf „Mein Konto“ (`engine/app/konto.js`, POST `/konto` mit `aktion=push_an` oder `push_ab`, Sitzung und Origin wie jede Änderung; Antwort 204). Das Abo gehört zu keiner Reise (`reise` leer, `seite` = `<FR_BASIS>/konto`) und bekommt die Nachrichten aller Reisen; gezeigt werden sie vom Worker `/sw.js` der Frieda-App (Scope `/`, nur Push, kein Abfangen, kein Speichern). Manifest, Worker und Skript liefert der Konnektor aus `<FR_DIENST>/app/` (`deploy.sh` kopiert `engine/app/`); der server-Block braucht dafür die Orte `/manifest.webmanifest`, `/sw.js` und `/konto.js` (Baustein `<instanz>-konnektor-orte.inc`, `wege_pruefen` prüft sie). Der Fuß der Reiseseite verweist nur auf „Mein Konto“; `api/push` der Reiseseite bleibt für ältere Abos.
- **iPhone und iPad:** Push gibt es nur in der App vom Home-Bildschirm (iOS 16.4 und neuer). Im Browser zeigt „Mein Konto“ die drei Schritte: Teilen, „Zum Home-Bildschirm“, Frieda öffnen und dort einmal anmelden (die App hat eigene Cookies).

## Wächter

`betrieb/waechter.sh` läuft täglich und ruft `engine/waechter.py lauf` auf (`docs/waechter.md`). Es berücksichtigt nur Reisen mit Baustein `waechter` und Status `fest` oder `unterwegs`. Hat es etwas zu melden, geht eine Sammelnachricht an den Betreiber; ein Fehler wird dringend gemeldet. Danach schreibt es die Schnappschüsse der Konten (`engine/konten.py sichern`) und des Reisespeichers (`engine/reisespeicher.py sichern`), siehe „Sicherung“; schlägt einer fehl, kommt je Sicherung eine dringende Meldung, die andere Sicherung läuft trotzdem, und der Stempel bleibt aus.

## Einstellungen

`betrieb/einstellungen.env` im Reisen-Repo (Vorlage `betrieb/einstellungen.beispiel`) enthält Zeilen `NAME=wert`, ohne Shell-Auswertung. Was schon in der Umgebung steht, gilt vor der Datei. Eine Änderung der Datei, die mit einem Stand auf `main` kommt, wirkt beim Veröffentlichen schon im selben Lauf (Neustart, Abschnitt „Veröffentlichen“); Werte aus dem Aufruf (systemd, von Hand) behalten dabei Vorrang, und `betrieb.env` liegt nicht in git, ändert sich also nicht durch das Vorspulen. Geheimes gehört nicht dorthin, sondern nach `<FR_DIENST>/betrieb.env` (600, gleiche Form). Das ist die Datei, die die Units als `EnvironmentFile` laden. Mailweg und Konten stehen in `<FR_DIENST>/konten.env` (`docs/konten.md`).

| Name | Vorgabe | Bedeutung |
|---|---|---|
| `FR_INSTANZ` | `frieda` | Name der Instanz: Units, nginx-Bausteine, Sperren, Drossel-Zone |
| `FR_TITEL` | `Frieda` | Kurzname in Nachrichten |
| `FR_ADRESSE` | – | öffentliche Adresse der Seiten (nötig zum Freischalten) |
| `FR_KN_ADRESSE` | `<FR_ADRESSE>` | Adresse des Konnektors, ohne Pfad: Er steht an ihrer Wurzel (`/mcp` für die Claude-App, Anmeldung, „Mein Konto“, OAuth). Gleich `FR_BASIS` in `konten.env`. Bis 1.11.2026 war die Vorgabe `<FR_ADRESSE>/<FR_INSTANZ>-mcp` (#163) |
| `FR_UMZUG_NACH` | leer | neue Adresse der Seiten bei einem Umzug auf eine andere Domain: Der Generator baut dann einen Service Worker, der gespeicherte Seiten verwirft und sich abmeldet, und eine Seite, die auf denselben Pfad der neuen Adresse weiterleitet. Erst danach darf der Server von der alten Adresse umleiten (ein umgeleitetes `sw.js` lehnt der Browser als Update ab). Kann auch als `bauen.py --umzug-nach` übergeben werden |
| `FR_SEITEN`, `FR_ABLAGE`, `FR_DIENST`, `FR_KONNEKTOR`, `FR_KONTEN`, `FR_SPEICHER` | `/srv/<instanz>`, darunter `_rueckmeldungen`, `_dienst`, `_konnektor`, `_konten`, `_speicher` | Ordner auf dem Server |
| `FR_RM_PORT`, `FR_KN_PORT`, `FR_SB_PORT` | `8771`, `8772`, `8773` | Ports auf 127.0.0.1 (Rückmeldedienst, Konnektor, Schreibweg) |
| `FR_SCHREIBKOPIE` | `<Wurzel>-schreiben` | Arbeitskopie des Schreibwegs (Git-Worktree, legt der Dienst an) |
| `FR_PYTHON` | `<Wurzel>/engine/.venv/bin/python` | Python mit den Paketen der Software |
| `FR_MELDEN` | leer | Meldeweg (unten) |
| `FR_ROT_MELDEN_NACH_MINUTEN` | `30` | Minuten Rot beim Veröffentlichen bis zum Alarm (Veröffentlichen) |
| `FR_NGINX_SNIPPETS`, `FR_SUDO` | `/etc/nginx/snippets`, `sudo -n` | nginx-Bausteine und Rechte |
| `FR_EIGENE_ADRESSEN` | leer | Adressen, die nicht ins Anfragekontingent von nginx zählen, getrennt durch Leerzeichen: die des Servers selbst (die Schleife `127.0.0.1` und `::1` gilt immer). Abschnitt „nginx-Bausteine abgleichen“ |
| `FR_SPERREN` | `/tmp` | Ordner der Sperrdateien je Reise im Schreibweg; die Sperre des Veröffentlichens liegt in `<FR_DIENST>/veroeffentlichen.lock`, weil der Schreibweg mit privatem `/tmp` läuft und Timer und Schreibweg sie teilen müssen (#211) |
| `FR_BENUTZER`, `FR_GRUPPE`, `FR_HOME`, `FR_PFAD` | aufrufender Benutzer | nur für `einrichten.sh`: Benutzer und `PATH` der Dienste |
| `FR_HEARTBEAT_VEROEFFENTLICHEN` | leer | Überwachungsadresse, nur in `betrieb.env` |
| `FR_NACHZIEHEN_WORKFLOW` | `software-nachziehen.yml` | Workflow des Reisen-Repos, den ein Anstoß von der Seite startet (Abschnitt „Anstoß“) |
| `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN` | `6` | Wartezeit in Stunden, bevor das Veröffentlichen denselben neuen Software-Stand noch einmal anstößt (Neue Instanz einrichten, „Anstoß vom Server“) |
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
   **Software nachziehen:** `cp frieda/betrieb/software-nachziehen.yml .github/workflows/` (dazu ein `tests.yml`, das `python -m pytest -q -rs engine/tests tests` ausführt). Der Workflow braucht die Rechte `contents: write` und `issues: write`, die er selbst anfordert. In den Einstellungen des Repos müssen Actions erlaubt sein, mit Schreibrechten für `GITHUB_TOKEN`. Alle 30 Minuten zieht er das Submodul auf den neuen Stand von `main` der Software, als Commit des Bots. Das Tor ist dasselbe wie beim Veröffentlichen: Sperren können nur die Tests der Software (`engine/tests`) und der Bau jeder Reise; rote Tests des Reisen-Repos (`tests/`) sind nur eine Warnung im Lauf. Sperrt das Tor, legt er ein Issue mit dem Label `software-nachziehen` an. Die Vorlage wird nur einmal kopiert: Sie ermittelt den Stand, setzt das Submodul und ruft `frieda/betrieb/software-nachziehen.sh` aus dem neuen Stand auf; der Ablauf kommt mit der Software (Ablauf unten).

   **Ablauf von `betrieb/software-nachziehen.sh`** (#250, auf dem Runner im Klon des Reisen-Repos):
   1. **Umstellen:** `neu.py nachziehen` für jede Reise mit `reise.json`, in jedem Lauf, auch ohne neuen Software-Stand (idempotent). So werden auch Reisen umgestellt, deren Software schon früher nachgezogen wurde. Fehlt in `reise.yaml` das Feld `sprache` (oder ist es leer), trägt es `sprache: de` ein, was für diese Reisen bisher galt; ein vorhandener Wert bleibt, auch ein unbekannter (#267). Ein offener Punkt („OFFEN …“) sperrt nicht, er erscheint als Warnung.
   2. **Nichts geändert** (weder Submodul noch Reisen): Ende, grün, kein Commit.
   3. **Tor:** `engine/tests` nur bei neuem Software-Stand, der Bau jeder Reise in jedem Lauf mit Änderung; `tests/` des Reisen-Repos nur Warnung.
   4. **Übernehmen:** ein Commit des Bots mit Submodul und umgestellten Reisen, erste Zeile „Software auf Stand X (automatisch)“ oder „Reisen auf den Stand der Software umgestellt (automatisch)“, darunter die Liste der Commits und die Meldungen der Umstellung je Reise.
   5. **Wettlauf mit dem Schreibweg:** Scheitert der Push, setzt das Skript auf `origin/main` zurück, setzt das Submodul erneut, stellt neu um, prüft neu und committet neu. Höchstens drei Versuche, nie erzwungen; scheitern alle, endet der Lauf rot ohne Issue, und der nächste Lauf versucht es wieder.
   6. **Tor rot:** Ohne offenes Issue `software-nachziehen` entsteht eins, und der Lauf endet rot (GitHub mailt). Mit offenem Issue endet er mit einer Warnung und grün, ohne Commit; nennt das Issue den aktuellen Software-Stand noch nicht, bekommt es einen Kommentar mit Stand und Lauf. Das offene Issue ist die Meldung, bis es geschlossen ist.

   Fehlt das Skript im gesetzten Stand (Submodul älter als #250), endet der Lauf rot mit einem Hinweis im Protokoll. Konnektor und Schreibweg laufen nach dem Commit noch mit dem alten Code, bis der nächste Lauf von `veroeffentlichen.sh` sie neu startet (wenige Minuten); ein Schreibvorgang in diesem Fenster kann abgelehnt werden und gelingt danach.

   **Anstoß vom Server:** `veroeffentlichen.sh` fragt bei jedem Lauf mit `git ls-remote` nach `main` der Software (URL aus `.gitmodules`). Ist dieser Stand ein anderer als der eingebundene und noch nicht angestoßen, startet es `gh workflow run <FR_NACHZIEHEN_WORKFLOW>` und merkt Stand und Zeit in `<FR_DIENST>/nachziehen-angestossen` (nur nach Erfolg von `gh`). Für denselben Stand startet es erst wieder, wenn seit der gemerkten Zeit `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN` (Vorgabe 6) vergangen sind; so erzeugt ein rotes Tor eine Fehler-Mail je Software-Stand, nicht eine alle 5 Minuten. Scheitert `ls-remote` oder `gh`, ist das eine Warnung im Protokoll, das Veröffentlichen läuft weiter. Der Zeitplan von GitHub bleibt als Rückfallweg.
3. **Bauordner auf dem Server:** Klon des Reisen-Repos als Dienstbenutzer, `git submodule update --init`. Danach `python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt`. `git fetch` muss ohne Rückfrage gehen. Lokale Dateien, die nicht ins Repo gehören (etwa `.claude/settings.json`), kommen in `.git/info/exclude`, sonst gilt der Ordner als belegt und das Veröffentlichen setzt aus.
4. **Einrichten:** `frieda/betrieb/einrichten.sh` prüft die Voraussetzungen. Es erzeugt Units und nginx-Bausteine in einem Ordner und zeigt die Befehle zum Aktivieren. Außerhalb dieses Ordners ändert es nichts. `--installieren` legt nach Rückfrage die Ordner an und kopiert Units und Bausteine nach `/etc`.
5. **nginx:** Im server-Block der Adresse `include <FR_NGINX_SNIPPETS>/<instanz>-*.conf;` eintragen, `nginx -t`, neu laden. Das bindet die Reiseseiten ein. Der Konnektor kommt mit einer eigenen Zeile `include <FR_NGINX_SNIPPETS>/<instanz>-konnektor-orte.inc;` in den Block seiner Adresse (gemeinsame Einstellungen in `<instanz>-konnektor.inc`). Beide enden bewusst auf `.inc`: Der Stern `<instanz>-*.conf` bindet sie nicht ein, sonst käme der Konnektor in jeden Block, der die Reiseseiten einbindet (etwa den einer zweiten Adresse), und die Orte stünden doppelt. Der Konnektor steht an der Wurzel der Adresse (#163):
   - `/` (Startseite, führt zu Mein Konto; #41), `/mcp` (Claude-App), `/anmelden`, `/abmelden`, `/konto`, `/einladung/…`, OAuth (`/authorize`, `/token`, `/register`, `/.well-known/oauth-…`), `/kalender/…` (Abo), `/schrift/…`, Favicon und App-Symbole, `/gesund`.
   - Reiseseiten und Konnektor teilen sich die Adresse: Die Sitzung (`__Host-frieda`) gilt nur dort, und die Reiseseite fragt mit ihr `api/ich`.
   - Kein `add_header Referrer-Policy "no-referrer"` im server-Block für diese Pfade: Der Dienst setzt `same-origin`, sonst schicken Browser `Origin: null` und jede Anmeldung scheitert an der Prüfung der Herkunft. Cache-Control und Content-Security-Policy setzt ebenfalls der Dienst.
   - Präfix-Orte (`^~`) und genaue Orte (`=`) gehen allgemeinen Regeln für Dateiendungen vor; Regeln mit `^~` oder `=` für dieselben Pfade im server-Block dürfen nicht stehen.
   - Die Links aus der Zeit vor den Konten (`/<token>`, früher `/<instanz>-mcp/<token>`) sind abgeschaltet (Frist 1.11.2026); die Vorlage hat keine Orte dafür, nginx antwortet 404.
6. **sudo** für den Dienstbenutzer, ohne Passwort und nur für diese Befehle:
   - `systemctl restart <instanz>-rueckmeldungen <instanz>-konnektor <instanz>-schreiben <instanz>-push`
   - `nginx -t` und `systemctl reload nginx`
   - `install`, `test`, `cat` und `rm` für Dateien in `<FR_NGINX_SNIPPETS>/<instanz>-*.conf`
7. **Erste Reise** leer anlegen: `engine/neu.py reise <reisen-ordner> --titel … --von … --bis … --person … --wer …` (nur Eckdaten und Personen, kein Inhalt; `docs/neue-reise.md`), nach `main` bringen, im Bauordner `FR_WURZEL=<Bauordner> frieda/betrieb/deploy.sh <reise>` (legt den Code der Dienste an). Danach `sudo systemctl enable --now <instanz>-rueckmeldungen <instanz>-konnektor <instanz>-schreiben <instanz>-push` und die beiden Timer, wie `einrichten.sh` sie nennt. Eine bestehende Instanz richtet den Push-Dienst nach: `pip install -r engine/requirements.txt`, `einrichten.sh --installieren` (neue Unit), sudo-Regel um `<instanz>-push` ergänzen, `enable --now <instanz>-push`.
8. **Prüfen:** `FR_WURZEL=<Bauordner> frieda/betrieb/veroeffentlichen.sh --immer` zeigt „Done: … is online“. `curl -s <FR_KN_ADRESSE>/.well-known/oauth-authorization-server` zeigt die Endpunkte unter derselben Adresse; in der Claude-App wird `<FR_KN_ADRESSE>/mcp` als Konnektor eingetragen, die Anmeldung läuft mit E-Mail und Code (`docs/konten.md`). `curl -s 127.0.0.1:<FR_SB_PORT>/gesund` antwortet `{"gesund": true}`.

**Zwei Instanzen auf einem Server** brauchen verschiedene `FR_INSTANZ`, `FR_SEITEN` (und damit Ablage und Dienstordner) und Ports. `einrichten.sh` bricht ab, wenn eine andere installierte Instanz dieselben Ports nutzt. Unit-Namen, nginx-Bausteine, Drossel-Zone und Sperrdateien tragen den Namen der Instanz. Jede Instanz braucht eine eigene Adresse (Host), weil ihr Konnektor an der Wurzel steht.

## Einheiten abgleichen (#260)

Die systemd-Einheiten in `/etc/systemd/system` entstehen aus `betrieb/vorlagen/`. Damit eine geänderte Vorlage nicht still
vom Server abweicht, vergleicht `veroeffentlichen.sh` nach jedem grünen Lauf `units.py pruefen` (erzeugt die Soll-Einheiten
mit `einrichten.sh --erzeugen` und vergleicht Zeile für Zeile; es ändert nichts). Bei einer Abweichung kommt genau eine
normale Meldung (Issue, kein Alarm), danach erst wieder bei einer anderen Abweichung (Merker `<FR_DIENST>/units-gemeldet`).
Ein Fehler im Abgleich stoppt das Veröffentlichen nie.

Ausgang von `units.py pruefen`: 0 alles gleich, 3 nur erlaubte Abweichungen, 4 auch gesperrte, 1 Fehler. Erlaubt sind nur
die Zeilen `Environment=FR_DIENST=…`, `Environment=FR_ZEITZONE=…` und `TimeoutStartSec=…` jeweils mit engem Wertmuster
(feste Namensliste `ERLAUBT`, gleich in `units.py` und im Hilfsprogramm; ein neuer Eintrag ist eine Sicherheitsentscheidung des
Product Owners). Alles andere (User, Startbefehle, Rechte, Reihenfolge, Drop-in-Ordner `<einheit>.d`, Timer, nicht
installierte Einheiten) ist gesperrt und braucht einen bewussten Schritt (`einrichten.sh --installieren`).

**Automatisch installieren (Hilfsprogramm mit Root-Rechten).** Hat der Abgleich nur erlaubte Abweichungen, ruft
`veroeffentlichen.sh` `units.py installieren` auf. Das übergibt jede betroffene Einheit samt neuer Datei (stdin) an
`sudo -n /usr/local/sbin/<instanz>-units-installieren <einheit>`, startet danach die Dauerdienste (`rueckmeldungen`,
`konnektor`, `schreiben`, `push`; nie `veroeffentlichen` oder `waechter`) neu und prüft erneut; was dann noch abweicht, wird
einmal gemeldet. Das Hilfsprogramm (Vorlage `betrieb/vorlagen/units-installieren.py`, von `einrichten.sh` mit Instanz und
Benutzer erzeugt) gehört auf dem Server root und liegt außerhalb des Repos, die Software kann es nicht ändern. Es
nimmt nur die sechs Dienst-Einheiten der Instanz an, liest die installierte Datei selbst, ersetzt nur dann, wenn sich beide
Dateien allein in den erlaubten Zeilen unterscheiden (alles andere in gleicher Reihenfolge), verlangt `User=` mit dem
Betriebsbenutzer in beiden, lehnt Fortsetzungszeilen, Steuerzeichen, Nicht-UTF-8, Eingaben über 64 KiB, Symlinks und Drop-ins ab,
ersetzt atomar und führt `systemctl daemon-reload` aus. Es liest weder Umgebung noch Argumente für Pfade oder Programme.
Ausgang 0 installiert, 2 nichts zu tun, 3 abgelehnt. Bekannte, bewusst offene Grenze (Gegenprüfung F101): Die Position der
erlaubten Zeilen zu den übrigen wird nicht verglichen; steht in der Einheit ein `TimeoutSec=`, kann ein verschobenes
`TimeoutStartSec=` den wirksamen Start-Timeout ändern (begrenzt durch das Wertmuster, keine Rechteausweitung). Die Zeilen
werden wie bei systemd nur an Leerzeichen und Tab getrennt; Nicht-ASCII ist nur in Kommentaren und Werten anderer Zeilen möglich.

Einmalig und bewusst (Freigabe des Product Owners, kein Teil des automatischen Laufs): Hilfsprogramm und sudoers-Zeile
installieren, die Befehle nennt `einrichten.sh` am Ende seiner Ausgabe. Ohne installiertes Hilfsprogramm bleibt es bei der
Meldung. Nach einer Änderung der Vorlage `units-installieren.py` muss die Kopie auf dem Server bewusst erneuert werden.

## nginx-Bausteine abgleichen (#206)

Der Konnektor hat drei Drosseln und die Reise-Seiten eine vierte, je Adresse (`betrieb/vorlagen/nginx-zone.conf`, Zonen mit dem Namen der Instanz in einer eigenen
Datei `conf.d/<instanz>-zone.conf`; eine gemeinsam genutzte Datei wie `limit-req.conf` bleibt unberührt, damit keine Namen streiten):
`<instanz>_mcp` großzügig (10 pro Sekunde, burst 40), weil die Claude-App von gemeinsamen Adressen aus aufruft; `<instanz>_anmelden`
streng (5 pro Minute, burst 10); `<instanz>_konto` für Konto, Einladung, Kalender-Abo (30 pro Minute, burst 20); `<instanz>_api` für den Rückmeldedienst der Reise-Seiten (120 pro Minute, burst 10; Zone der Reise-Bausteine, #316; ein Seitenaufruf macht sieben Abfragen, bei 30 pro Minute wurde am 4.11.2026 ein Besucher über fail2ban ausgesperrt).
`/token`, `/register`, die OAuth-Metadaten, Schrift und Symbole haben keine Drossel: Sie kommen von den gemeinsamen Adressen der
Claude-App, ein Limit träfe alle Nutzer zusammen, der Dienst prüft PKCE, Weiterleitungsadressen und Codes selbst.

**Ausnahme für den Server selbst.** Für die Schleife (`127.0.0.1`, `::1`) und `FR_EIGENE_ADRESSEN` ist der Schlüssel der Zonen leer
(`geo` und `map`); nginx rechnet Anfragen mit leerem Schlüssel nicht an. Die Prüfungen des Servers laufen so weiter den echten Weg
über nginx, ohne Kontingent von Besuchern zu verbrauchen. Bedingung: Die Ausnahme ist sicher, solange die Software keine Funktion hat,
mit der der Server eine fremde Adresse aufruft und deren Antwort nach außen weitergibt (heute gibt es keine). Kommt eine solche
Funktion, wird die Ausnahme vorher neu bewertet.

**Abgleich.** Nach jedem grünen Lauf vergleicht `veroeffentlichen.sh` mit `nginx.py pruefen` die erzeugten Bausteine mit den
installierten (`conf.d/<instanz>-zone.conf`, `<instanz>-konnektor-orte.inc`, `<instanz>-konnektor.inc`). Bei einer Abweichung kommt genau eine
normale Meldung mit dem einen Befehl zum Beheben, danach erst wieder bei einer anderen Abweichung (Merker `<FR_DIENST>/nginx-gemeldet`).
Sind die Bausteine noch nicht eingerichtet, meldet der Abgleich nichts. **Installiert wird nie automatisch:** Jede nginx-Zeile wirkt
als Root (ein einziger Ort kann Dateien ausliefern oder, weil nginx beim Start als Root Logdateien öffnet, schreiben); es gibt keine
harmlose Teilmenge wie bei den Einheiten. Ausgang von `nginx.py pruefen`: 0 gleich oder nicht eingerichtet, 3 weicht ab, 1 Fehler.

Der Befehl aus der Meldung ist `sudo env … nginx.py anwenden` (von Hand, mit Root-Rechten, weil er `/etc/nginx` ändert; der Betriebsbenutzer braucht dafür keine Rechte, `pruefen` liest nur mit `sudo -n cat` unter `/etc/nginx/`, wie bei den Reise-Bausteinen). Er erzeugt das Soll neu, sichert die installierten Dateien in `<FR_DIENST>/nginx-sicherung/<Zeit>/`, installiert, prüft mit `nginx -t` und lädt nur bei bestandener Prüfung neu; besteht sie nicht, stellt er die gesicherten Dateien (und das Fehlen neuer) wieder her und endet mit Fehler; das gilt auch bei einem Abbruch von Hand. Rechte und Besitzer stellt er nicht einzeln wieder her (Zone 644, Bausteine 640, root). Er läuft nie automatisch.

**Hinweis zur Ausnahme:** Die Ausnahme gilt für die Adresse, die nginx sieht (`$remote_addr`). Wird später ein vorgeschalteter Proxy oder CDN verwendet oder `realip` eingeschaltet, erscheint dessen Verkehr als eigene Adresse und wäre unbegrenzt; dann muss die Ausnahme vorher überprüft werden.

**Einmalige Umstellung des Server-Blocks** (bewusst, mit Freigabe des Product Owners): Der Block der Konnektor-Adresse wird auf die Form „fester
Rahmen plus erzeugter Baustein“ gebracht (`include <snippets>/<instanz>-konnektor-orte.inc;` statt der von Hand gebauten Orte), die Zonendatei
kommt nach `conf.d`. Danach gilt der Abgleich. Die Zone `<instanz>_api` der Reise-Bausteine (`nginx-reise.conf`) steht ebenfalls in der eigenen Zonendatei (#316).

**Zone aus einer gemeinsamen Datei umziehen.** Stand die Zone früher in einer gemeinsam genutzten `conf.d/*.conf` (etwa `limit-req.conf`), meldet
`nginx.py pruefen` das als Abweichung (Ausgang 3). `nginx.py anwenden` entfernt dort im selben Lauf genau die Zeile der Instanz samt dem
Kommentarblock direkt darüber, installiert die Zonendatei, sichert beide Dateien (die fremde unter `nginx-sicherung/<Zeit>/fremd/`), prüft
einmal mit `nginx -t` und stellt bei einem Fehler beide wieder her. Das muss ein Lauf sein: nginx verbietet doppelte Zonen, und ohne Definition
laden die Reise-Bausteine nicht. Alle anderen Zeilen und die Rechte der fremden Datei bleiben. Ist die Definition nicht eindeutig (zweimal,
oder weitere Direktiven in derselben Zeile), ändert `anwenden` nichts und endet mit Fehler. Weitere Instanzen brauchen keinen Handschritt.

## Bauordner und Arbeitsordner

Der **Bauordner** spiegelt nur `main`. Timer, Schreibweg und Wächter laufen von dort, ihre Units nennen ihn mit `FR_WURZEL`. Von Hand wird darin nichts geändert, kein Branch ausgecheckt und nichts committet. Sonst setzt das Veröffentlichen aus (es überspringt jeden Lauf, solange der Ordner nicht auf `main` oder nicht sauber ist). `deploy.sh` und `veroeffentlichen.sh` laufen nur mit `FR_WURZEL`. `deploy.sh` baut außerdem nur, wenn der Ordner auf dem Branch `main` steht. Ein Aufruf aus einem anderen Klon bricht damit ab, statt von dort zu veröffentlichen (#137). Was nicht im Repo liegt, hat der Bauordner selbst: die Python-Umgebung (`engine/.venv`), die Werkzeuge (`engine/.bin`) und die Grundkarten. Für automatische Karten holt `veroeffentlichen.sh` die Grundkarte vor dem Bau selbst, wenn sich ihr Rahmen geändert hat (`werkzeuge/grundkarte_auto.py`, `FR_GRUNDKARTE_AUTO`, Epic #225; ohne Netz baut die Reise trotzdem). Eine neue Grundkarte einer handgepflegten Karte kommt mit `FR_WURZEL=<Bauordner> frieda/werkzeuge/karte-holen.sh <reise>` direkt dorthin (ignorierte Dateien, `main` bleibt sauber), danach `FR_WURZEL=<Bauordner> frieda/betrieb/veroeffentlichen.sh --immer`.

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
