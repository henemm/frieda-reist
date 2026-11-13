# Konten: Anmeldung mit E-Mail-Adresse

Paket J (Issue #43). Stand:
- J1: Grundlage, `engine/konten.py`
- J2: Anmeldung im Web, `engine/anmeldung.py`, Rückmeldedienst mit Sitzung, Reiseseite
- J3: Konnektor „Frieda“ mit OAuth für alle Reisen, `engine/oauth.py`, [konnektor.md](konnektor.md)

Es folgen Betrieb (eigene Adresse, Mail) und Umstellung.

## Warum

Bisher erkennt Frieda Menschen nur an geheimen Links. Wer einen Link verliert oder sein Claude-Konto wechselt, steht
draußen, und über Reisen hinweg gibt es keine Identität. Mit Konten wird jeder Mensch an seiner E-Mail-Adresse
erkannt und bekommt darüber jederzeit wieder Zugang.

## Grundsätze (Entscheidungen des Product Owners, 27.10.2026)

- **Konto:** Jedes Konto hat eine feste, unsichtbare Kennung (`K-…`), die sich nie ändert. Darauf verweisen
  Mitgliedschaften und Verlauf.
- **E-Mail-Adresse = Anmeldename:**
  - höchstens ein Konto je Adresse, ohne Unterschied von Groß- und Kleinschreibung
  - änderbar, aber nur mit einem Code an die neue Adresse und nur, wenn sie frei ist
- **Sprache (ADR-0006):** Jedes Konto hat eine Sprache (Spalte `konten.sprache`, leer heißt Vorgabe `en`; bei der ersten Anmeldung aus `Accept-Language` des Browsers). Die Kontoseiten, die Mails an das Konto und der Konnektor sprechen sie. Vor der Anmeldung folgen die Seiten dem Browser. Ändern geht auf der Kontoseite („Sprache“) oder mit dem Werkzeug `sprache_setzen`. Eine Einladung an eine Adresse ohne Konto kommt in der Sprache der Reise (`reise.yaml sprache`). Auf einer vorhandenen Datenbank fügt das Öffnen die Spalte hinzu (`ALTER TABLE`), nichts muss von Hand migriert werden. Einmal je Datenbank (`PRAGMA user_version` 1) bekommen Konten ohne Sprache Deutsch: Sie stammen von vor ADR-0006 (Product Owner, 1.11.2026).
- **Ohne Passwort:** Wer seine Adresse eingibt, bekommt einen sechsstelligen Code per Mail.
  - Der Code gilt 10 Minuten, nur einmal, und höchstens 5 Versuche sind erlaubt.
  - Der Code ist der Hauptweg, der Link in der Mail ist Zusatz. Apps auf dem Home-Bildschirm haben eigene Cookies.
- **Freie Anmeldung:**
  - Das erste Anmelden legt das Konto an. Frieda fragt dabei nach dem Namen, bei einer Einladung ist er vorbelegt.
  - Ohne Einladung hat ein Konto keine Reisen.
- **Reisen anlegen:**
  - Erst mit Freischaltung durch den Betreiber.
  - Ein Konto kann darum bitten. Eine Ablehnung bleibt bestehen, bis der Betreiber sie ändert.
- **Einladung:**
  - Sie gilt für eine Reise und einen Personen-Schlüssel.
  - Hat die Adresse schon ein Konto, gilt sie sofort, sonst beim ersten Anmelden mit dieser Adresse.
  - Der Link aus der Einladungsmail (30 Tage gültig) ist selbst ein Nachweis: Wer ihn öffnet, darf sich auch mit einer
    anderen Adresse anmelden.
- **Rollen** bleiben, wo sie sind (`reise.yaml`, `einladungen.json`). Konten verknüpfen nur Konto und Person. Im
  Repo stehen deshalb keine Adressen.
- **Lesen** der Reiseseite geht weiter über den geheimen Seitenlink ohne Anmeldung. Mitmachen braucht Anmeldung und
  Rolle (ab J2). Das ist eine bewusste Grenze (Product Owner, 27.10. und 8.11.2026, #421): Wer den Link kennt, liest die
  Seite, `stand`, `brett`, `packstand` und Belege wie ein Gast; ein angemeldetes Nicht-Mitglied sieht nicht mehr als ein
  Gast, und entfernte Personen lesen über den Link weiter wie ein Gast. Der Link hat 96 Bit Zufall, ist `noindex` und
  `no-referrer`. Die Testreihe `engine/tests/test_trennung.py` belegt die Trennung zweier Konten (#380).

## Szenarien

| Nr. | Szenario | Was geschieht |
|---|---|---|
| 1 | Neu ohne Einladung | Konto entsteht, „noch keine Reisen“, Bitte „Reisen anlegen“ möglich |
| 2 | Neu, eingeladen | Mail mit Code-Hinweis und Link, nach dem Anmelden ist die Reise da |
| 3 | Eingeladen, ohne Claude | Alles im Web (J2) |
| 4 | Konto vorhanden, zweite Reise | Gilt sofort, Mail als Hinweis |
| 5 | Neues Gerät oder neues Claude-Konto | Mit derselben Adresse anmelden, alles ist wieder da |
| 6 | Adresse ändern | Code an die neue Adresse. Gehört sie schon einem Konto, wird abgelehnt |
| 7 | Nur Leselink | Lesen geht, Schreiben verlangt die Anmeldung (J2) |
| 8 | Bisherige Personen | Einladung per Mail. Alte Links gelten bis zur Umstellung |
| 9 | Freigeschaltet | Legt eine Reise an, ist dort Organisator:in und lädt per Mail ein (J3) |
| 10 | Aus der Reise nehmen, Konto sperren | Die Verknüpfung entfällt. Sperren meldet alle Geräte ab |
| 11 | Konto selbst löschen | Konto und Adresse sind weg, aus allen Tabellen der Kontendatenbank (auch Einladungen, Wartelisteneintrag, Anmeldungen der Claude-App). Im Verlauf und in den bekannten Herkunftsmustern steht „gelöschte Person“ (zugeordnet über den Personen-Schlüssel). Reisen nur mit der Person gehen mit Schonfrist mit. Ist sie die einzige Organisator:in einer Reise mit weiteren Mitgliedern, wird abgelehnt („erst klären“: Rolle übergeben oder Reise löschen). Die Adresse ist danach wieder frei (#381) |
| 12 | Reise löschen | Nur Organisator:innen einer Reise im Reisespeicher: „Reise löschen …“ unter den Personen auf Mein Konto, Haken, dann den Reisenamen eintippen. Die Reise ist sofort überall wie nicht vorhanden; alle anderen Mitglieder bekommen Mail und Meldung. Bis zum Ende der Schonfrist (14 Tage, `FR_LOESCHFRIST_TAGE`) steht sie oben in „Meine Reisen“ mit „Reise zurückholen“; danach entfernt der Wächter sie endgültig (#381, `docs/betrieb.md`, „Wächter“) |
| 13 | Meine Daten herunterladen | Auf Mein Konto unter „Meine Daten“: eine ZIP mit den Kontoangaben (`person.json`, ohne Schlüssel und ohne Adressen anderer) und je Reise, in der die Person dabei ist (auch archivierte, nicht vorgemerkte), die ganze Reise, ihre Beiträge und die Belege, die die Person sehen darf. Scheitert etwas, kommt „Export gerade nicht möglich“, nie eine halbe Datei (#498, `docs/betrieb.md`, „Export der Daten“) |

## Sicherheit

- **Geheimnisse:** Codes, Sitzungen und Einladungen liegen nur als SHA-256 in der Datenbank.
- **Datenbank:** `<FR_KONTEN>/konten.db` (SQLite, WAL), Standard `<FR_SEITEN>/_konten`. Ordner 700, Datei 600. Der Ordner gehört zum Dienst der Instanz und enthält Konten, Anmeldungen und das Dienst-Geheimnis aller Nutzer dieser Instanz, getrennt von den Reisen. Bis 28.10.2026 lag er unter `<FR_ABLAGE>/_konten/`; eine dort liegende Datenbank gilt weiter, solange am neuen Ort keine liegt.
- **Keine Auskunft:** Antworten verraten nie, ob eine Adresse ein Konto hat. Mails an bekannte und unbekannte
  Adressen sind gleich.
- **Begrenzung:**
  - je Adresse 3 Codes in 15 Minuten, je IP 10 in der Stunde
  - je Reise 50 Einladungen am Tag
  - je Konto höchstens `FR_GRENZE_REISEN` angelegte Reisen (Vorgabe 10; gezählt werden angenommene Anfragen, dauerhaft;
    archivierte Reisen geben die Zahl nicht frei) und `FR_GRENZE_SCHREIBEN` schreibende Werkzeugaufrufe im Konnektor je
    Stunde (Vorgabe 300, gleitendes Fenster; schreibend sind die Werkzeuge aus `SCHREIB_WERKZEUGE`, `SCHREIB_AKTION` und
    `ONTOLOGIE_WERKZEUGE`). Zähler in den Tabellen `angelegte_reisen` und `schreibvorgaenge` der Konten-Datenbank;
    Betreiber (Recht `betreiber`) sind ausgenommen. Wer an eine Grenze stößt, bekommt einen freundlichen Satz samt
    Wartezeit; im Dienstprotokoll steht eine Zeile `grenze <konto> schreiben|reisen` ohne Adresse oder Name, ein Alarm
    geht nicht (#380). Aufrufe einer fremden Reise verbrauchen keinen Zähler.
- **Sitzungen:** je Gerät, 365 Tage gültig und rollierend (jede Nutzung verlängert). Abmelden geht je Gerät oder
  überall.

## Anmeldung im Web (J2)

- **Seiten:** Der Konnektor-Dienst liefert sie unter Friedas eigener Adresse aus (`FR_BASIS`).
  - `/anmelden`: Adresse, dann Code, beim ersten Mal auch der Name
  - `/einladung/<token>`: Einladung ansehen, annehmen oder mit einer anderen Adresse anmelden
  - `/`: Startseite der Adresse; angemeldet führt sie zu `/konto` (#41), ohne Anmeldung zeigt sie die Infoseite „Was ist Frieda?“ (#436): Grundprinzipien, erfundene Beispiel-Gespräche mit Claude, Bilder der Reiseseite, erste Schritte mit der Adresse des Konnektors, Anmelden und Warteliste. Sprache nach dem Browser, umschaltbar mit `/?sprache=<kürzel>` (auch für geteilte Links); `/anmelden` verweist darauf
  - `/info/`: dieselbe Infoseite für alle, auch angemeldet als Einstiegshilfe (#440; Kopf und Knopf führen dann zu Mein Konto, der Sprachumschalter bleibt auf `/info/?sprache=`). Sie liegt unter `/info/`, weil nginx diesen Ort für die Bilder schon zum Dienst führt und `/info` selbst dorthin umleitet (der Dienst ebenso). Mein Konto verlinkt sie im Kopf und zeigt bis zur ersten Verbindung mit Claude (gültiges Refresh-Token, `konten.mit_claude_verbunden`) die Karte „Neu bei Frieda?“
  - `/info/<name>-<sprache>.webp`: Bilder der Infoseite aus `engine/info/` (nur diese Form; der Dienst liest den Ordner bei jedem Abruf). Erzeugt aus den beiden Beispielreisen mit `engine/.venv/bin/python engine/info/erzeugen.py`, je Sprache der Software; neu erzeugen, wenn sich die Reiseseite sichtbar ändert. Nie echte Reisen: das Repo ist öffentlich
  - `/konto`: Meldungen an die Person über alle Reisen (#21 Stufe 1, dieselbe Quelle wie `meine_reisen`: `rueckmeldungen.meldungen_des_kontos`; je Zeile ein Link an die Stelle der Reise, Lesestand des Kontos in der Tabelle `meldung_gelesen`, #407), Name, Adresse, Reisen, Kalender (Abo-Link, Download, Einstellungen; #77), Benachrichtigungen (Arten, Ruhezeit, auf allen Geräten ausschalten; #21, `docs/betrieb.md` „Push-Nachrichten“), Bitte „Reisen anlegen“, Geräte, Meine Daten herunterladen (#498), Konto löschen; für Betreiber die offenen Bitten
  - `/abmelden`
- **Sitzung:** Cookie `__Host-frieda` (HttpOnly, Secure, SameSite=Lax, ein Jahr, rollierend).
- **Herkunft:** Jede Änderung muss von Friedas eigener Adresse kommen (`Origin`), sonst 403. SameSite trennt nicht von
  Nachbar-Subdomains. Rückkehradressen sind nur Pfade auf Friedas Adresse.
- **Link aus der Mail:** öffnet nur die Code-Seite mit ausgefülltem Code. Angemeldet wird erst nach einem Klick, weil
  Mailprogramme Links vorab aufrufen.
- **Rückmeldedienst, wer schreibt:**
  - Der Konnektor schickt das Dienst-Geheimnis (`X-Frieda-Dienst`, Datei `dienst-geheimnis` neben der Datenbank).
  - Alles andere gilt als Seite (fail-closed). Name und Rolle kommen aus Sitzung und Mitgliedschaft, ein eingetippter
    Name wird überschrieben.
- **Mitmachen nur angemeldet** (seit #421, Product Owner 8.11.2026): ohne Sitzung 401, ohne Mitgliedschaft 403. Die frühere
  Regel `anmeldung` je Reise (`uebergang`: auch ein eingetippter Name; `noetig`) ist entfallen; steht sie noch in einer
  `reise.yaml`, baut die Reise mit Hinweis, und `neu.py nachziehen` nimmt sie heraus. Lesen geht weiter ohne Anmeldung
  über den geheimen Link zur Seite.
- **Einplanen** auf dem Wunsch-Brett: auch angemeldet auf der Seite, aber nur als Organisator:in.
- **Zurückziehen:** Angemeldet geht es nur bei eigenen Rückmeldungen.
- **Reiseseite:** `GET api/ich` sagt, wer angemeldet ist.
  - Oben rechts steht „Anmelden“ oder der eigene Name (Molekül `kontoKnopf`, nur auf Friedas eigener Adresse).
  - Angemeldet nennt `nameFeld` den Namen, unter dem man schreibt; sonst steht dort der Hinweis zum Anmelden (ein Feld für einen eingetippten Namen gibt es nicht mehr, #421).
  - Antwortet der Dienst mit 401, bleibt der Eintrag im Ausgang und geht nach dem Anmelden los.
- **Mit Claude verbinden (#422):** Mein Konto erklärt in vier Schritten, wie man Frieda als Konnektor in die Claude-App einträgt (Adresse `<FR_BASIS>/mcp` zum Kopieren, Hinweis auf bezahlte Konten); die Einladungsmail verweist mit `<FR_BASIS>/konto#verbinden` darauf.
- **Archivierte Reisen (#416):** Auf Mein Konto stehen Reisen im Status archiv nicht in der Liste, sondern in einem eingeklappten Abschnitt „Archivierte Reisen (n)“ darunter; `meine_reisen` nennt sie nur in einer Schlusszeile. Nichts wird gelöscht, die Reisen bleiben mit ihrem Ordnernamen ansprechbar (Status zurücksetzen mit `reise_status_setzen`).
- **Personen einer Reise (#406):** Auf Mein Konto klappt unter jeder Reise die Liste der Personen auf, in der Claude-App liest das Werkzeug `personen` dasselbe. Alle Mitglieder sehen Name, Rolle, „reist mit“ und von/bis. Den Zugang (angemeldet, eingeladen, noch keiner) sehen nur Organisator:innen (Product Owner, 8.11.2026). E-Mail-Adressen und Notizen zeigt keine der beiden Stellen. Beides nutzt `rueckmeldungen.personen_zeilen`.

## Claude-App (J3)

**Ablauf beim Hinzufügen** von `<FR_BASIS>/mcp` als Konnektor:
1. Ohne Token antwortet der Konnektor mit 401 und zeigt auf die Metadaten.
2. Die Claude-App registriert sich (DCR oder Client ID Metadata Document).
3. Sie öffnet `/authorize`. Wer nicht angemeldet ist, meldet sich an (wie im Web).
4. Die Zustimmungsseite zeigt, wer fragt und wohin der Code geht.
5. „Erlauben“ schickt einen Code an die Claude-App. Sie tauscht ihn mit dem PKCE-Verifier gegen Tokens.

**Fristen der Tokens:**
- Code: 5 Minuten, nur einmal
- Access-Token: 1 Stunde
- Refresh-Token: 90 Tage mit Rotation

**Missbrauch:**
- Ein zweimal eingelöster Code widerruft alles, was aus ihm entstand.
- Ein schon benutzter Refresh-Token widerruft die ganze Familie.
- „Überall abmelden“, Sperren und Löschen beenden auch den Zugriff der Claude-App.

## Warteliste (#382, Alpha)

Grundsatz (Product Owner, 6.11.2026): Die freie Anmeldung bleibt offen. Die Warteliste steuert nur, wer Reisen anlegen
darf; sie lädt zur Nutzung des Dienstes ein, nicht zu einer Reise.

1. Auf `/warteliste` trägt sich jemand mit der Adresse ein. Die Seite nennt die Voraussetzung (bezahltes Claude-Konto für
   den Konnektor) und antwortet immer gleich („Wir haben dir eine Mail geschickt“), egal ob die Adresse neu, schon
   eingetragen, bestätigt, freigegeben oder schon ein Konto ist.
2. Eine Mail bringt den Link `/warteliste/bestaetigen/<wort>` (7 Tage, einmal, nur als SHA-256 gespeichert). Der Link zeigt
   nur einen Knopf; erst der Knopfdruck bestätigt. Danach sehen die Betreiber den Eintrag und bekommen eine Meldung.
3. Der Betreiber gibt frei (`konten.py freigeben <email>` oder Knopf auf Mein Konto). Die Mail „Du bist dabei“ geht in der
   Sprache des Eintrags; das Recht `reise_anlegen` gilt sofort, wenn die Adresse schon ein Konto hat, sonst beim ersten
   Anmelden. Eine zweite Freigabe ändert nichts. Scheitert die Mail, bleibt der Eintrag wartend und der Fehler wird
   gemeldet; die Freigabe lässt sich dann wiederholen.

- Mails gehen nur an neue und an noch unbestätigte Einträge. Auch wer schon ein Konto hat, wird eingetragen, bestätigt
  und freigegeben wie alle (Product Owner, 7.11.2026); daneben bleibt die Bitte „Reisen anlegen“ auf Mein Konto.
- Begrenzung: je Adresse 3 Mails in 15 Minuten, je IP 10 in der Stunde (eigene Zähler, getrennt von den Anmeldecodes),
  höchstens 1000 unbestätigte Einträge zugleich. Unbestätigte Einträge verfallen nach 7 Tagen.
- Tagesgrenze (#534): Je Kalendertag (UTC) gehen höchstens `FR_GRENZE_WARTELISTE_TAG` Bestätigungsmails der Warteliste
  raus (Vorgabe 20), damit das Mail-Kontingent der Instanz für Anmeldecodes und andere Dienste reicht. Gezählt wird jede
  ausgelöste Bestätigungsmail, auch die erneute an eine unbestätigte Adresse; nicht gezählt werden Anfragen bestätigter
  oder freigegebener Adressen, Ablehnungen und Freigaben. Ist die Grenze erreicht, zeigt die Seite für jede Adresse
  gleich „Heute sind alle Plätze vergeben. Bitte morgen wieder vorbeischauen.“ (ohne Zahl), schickt keine Mail und
  speichert nichts; ab Mitternacht UTC ist die Grenze wieder frei. Bei der ersten Ablehnung eines Tages bekommen die
  Betreiber einmal eine Meldung der Art `betrieb` auf Mein Konto (kein Alarm). Die Zählzeilen in `versand` tragen
  weder Adresse noch IP.
- Ein Eintrag verschwindet mit dem Konto derselben Adresse (#381); Löschen ohne Konto und Exportieren folgen später.

## Betrieb

Umgebung:

| Variable | Bedeutung |
|---|---|
| `FR_BASIS` | Öffentliche Adresse von Frieda (für Links in Mails, OAuth); gleich `FR_KN_ADRESSE` der Instanz, ohne Pfad (`docs/betrieb.md`, nginx-Vorlage des Konnektors) |
| `FR_SMTP_HOST`, `FR_SMTP_PORT` (587), `FR_SMTP_USER`, `FR_SMTP_PASS`, `FR_ABSENDER` | Mailversand mit STARTTLS |
| `FR_SMTP_ERSATZ_HOST`, `FR_SMTP_ERSATZ_PORT` (587), `FR_SMTP_ERSATZ_USER`, `FR_SMTP_ERSATZ_PASS` | Zweiter Einlieferungsweg (#561): Lehnt `FR_SMTP_HOST` ab oder ist nicht erreichbar (etwa erschöpftes Tageskontingent), geht dieselbe Mail mit demselben Absender hier hinaus; auf stderr steht dann eine Warnzeile ohne Adresse. Nicht gesetzt: kein zweiter Versuch |
| `FR_MAIL_DATEI` | Mails stattdessen als JSON-Zeilen in diese Datei (Tests, Probebetrieb) |
| `FR_OAUTH_REDIRECTS` | weitere erlaubte Redirect-URIs der Claude-App (durch Komma getrennt) |
| `FR_CIMD_HOSTS` | Hosts, von denen Client ID Metadata Documents geladen werden (Vorgabe `claude.ai`) |
| `FR_GRENZE_REISEN`, `FR_GRENZE_SCHREIBEN` | Grenzen je Konto (Vorgaben 10 Reisen, 300 Schreibvorgänge je Stunde; Abschnitt „Sicherheit“); ungültige oder nicht positive Werte gelten als nicht gesetzt |
| `FR_GRENZE_WARTELISTE_TAG` | Bestätigungsmails der Warteliste je Kalendertag (UTC), Vorgabe 20 (#534, Abschnitt „Warteliste“); ungültige oder nicht positive Werte gelten als nicht gesetzt |
| `FR_GRENZE_CODES_TAG` | Anmeldecodes je Kalendertag (UTC) an Adressen ohne Konto und ohne offene Einladung, Vorgabe 30; ist die Grenze erreicht, geht an solche Adressen keine Mail mehr hinaus, die Antwort bleibt gleich |
| `FR_LOESCHFRIST_TAGE` | Schonfrist zwischen „Reise löschen“ und dem endgültigen Entfernen (Vorgabe 14 Tage, #381) |

Befehle für den Betreiber: `python3 engine/konten.py liste | anfragen | freischalten <email> [--nein] |
warteliste | freigeben <email> | vorgemerkt |
betreiber <email> | sperren <email> | entsperren <email> | loeschen <email> | zusammenfuehren <von> <nach> |
einladen <reise> <schluessel> <email> <rolle> <Name> <von> | meldungen [--alle] | meldung-erledigt <nr> <issue>`.

Meldungen an den Betreiber (#530) aus der Claude-App liegen in der Tabelle `betreiber_meldungen` (Text, Art,
Zusammenhang, Reise, Zeitpunkt, Konto, Verweis auf das Issue, solange offen leer). `meldungen` listet die offenen (mit
`--alle` auch erledigte), `meldung-erledigt` hakt eine mit dem Verweis auf das Issue im privaten Reisen-Repo ab. Konto
löschen nimmt die Meldungen und ihre Zählzeilen mit; der Export der Person enthält sie, ohne den Verweis. Ablauf und
Grenzen: `docs/betrieb.md`, „Meldungen an den Betreiber“.
