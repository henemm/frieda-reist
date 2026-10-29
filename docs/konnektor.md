# Konnektor: Reisen in der Claude-App

Mit dem Konnektor lässt sich eine Reise in jedem normalen Claude-Chat nutzen (App am Handy, Desktop, claude.ai). Claude liest dabei die Reise und kann Rückmeldungen abgeben. Technisch ist es ein MCP-Server: `engine/konnektor.py` auf dem eigenen Server, neben dem Rückmeldedienst.

## Grundsätze (24.10.2026)

- Der Plan ändert sich nie in der App selbst, sondern beim Einarbeiten (Claude Code). Ein **Auftrag** aus der App wird dort geprüft und dann übernommen. Eine **Entscheidung** (`entscheiden`) prüft der Dienst dagegen im selben Moment (siehe „Entscheiden“) und hält sie mit Datum fest; eingearbeitet wird sie trotzdem. **Seit 29.10.2026 gilt das nur noch für den Übergang** (ADR-0001, Paket O-3): Frieda enthält keine KI, der Konnektor schreibt direkt in die Reise, geprüft von Regeln im Code (`engine/schreiben.py`, siehe „Ontologie im Gespräch“). Zuerst Arten und Merkmale; Werte, Dinge, Wahlstellen und Entscheidungen folgen Schritt für Schritt, der Einarbeiten-Lauf entfällt am Ende.
- Nutzen dürfen ihn **alle Personen der Reise** (`reise.yaml personen`). Seit 26.10.2026 gehört ein Link zu einer Person; ihre Rolle entscheidet: `gast` liest, `mitwirkend` gibt Rückmeldungen, Wünsche, Vorschläge und Aufgaben, `organisator` dazu Aufträge. Alte Links mit Rolle `mitreisend` gelten als `mitwirkend`.
- **Ein Link pro Reise und Person.**
- Gehört der Link zu einer Person, steht der Name fest. Bei einem Link ohne Person (nur Rolle) fragt Claude einmal nach dem Vornamen.
- **Aufgaben** (AG-01 …) sind die Ausnahme von „nur als Auftrag“: Alle dürfen sie über die App und über die Webseite sofort anlegen, ändern und abhaken. Eine Aufgabe hängt an einer oder mehreren IDs oder an der Reise allgemein. Sie hat Titel, Zuständig, Priorität, „ab wann möglich“, Frist, Notiz, Status (offen, in Arbeit, erledigt, entfällt) und einen Verlauf. Gelöscht wird nie.

## Was Claude damit kann

| Werkzeug | Wer | Was |
|---|---|---|
| `ueberblick` | alle | Eckdaten, Tagesplan mit IDs, Wahlstellen, Inhaltsverzeichnis, Meldungen an die Person (Wächter und Erinnerer, wenn der Baustein `waechter` an ist) |
| `zeige` | alle | Volltext zu einer ID (T-, E-, O-, U-, V-, P-, F-, W-) |
| `suche` | alle | Volltextsuche |
| `offene_fragen` | alle | F-Liste mit Frist und Status |
| `varianten` | alle | Pläne und Wahlstellen mit Dafür/Dagegen und Summen |
| `rueckmeldungen` | alle | bisherige Rückmeldungen mit Status und Antwort; bei Organisator:innen auch die Aufträge; vorn die Meldungen an die Person (Konflikte, Fristen, Statuswechsel; siehe `docs/waechter.md`) |
| `rueckmeldung_geben` | alle | landet im selben Eingang wie die Rückmeldungen von der Webseite; Art `Wunsch` für Ideen ohne feste Stelle (ziel leer), sichtbar im Reiter „Wünsche“ |
| `aufgaben` | alle | Aufgaben, Standard nur offene; Filter nach Bezug, Zuständig, Status |
| `aufgabe_anlegen` | alle | neue Aufgabe, gilt sofort |
| `aufgabe_aendern` | alle | abhaken, Status, Felder, Kommentar in den Verlauf; gilt sofort |
| `wuensche` | alle | Wunsch-Brett: Wünsche nach Spalten mit Punkten, Vorschlag, eingeplant, erlebt; Bilanz je Person (Baustein `wuensche`) |
| `wunsch_aendern` | Mitwirkende, Organisator:innen | Punkte auf eigene Wünsche, abhaken (unterwegs und danach), einplanen (nur Organisator:innen mit persönlichem Link; auf der Webseite gibt es das nicht); gilt sofort, Regeln prüft der Rückmeldedienst (siehe `docs/produkt.md`, Wunsch-Brett) |
| `merkmale` | alle | welche Merkmale eine Alternative braucht (mit Hinweis zum Recherchieren und Nachfragen), was jede Option hat und was fehlt; zu einer Wahlstelle `V-…`, einer Strecke `E-…` oder einer Art (`bereich`); siehe `docs/alternativen.md` |
| `alternative_vorschlagen` | alle | neue Option mit Merkmalen; Art aus der Stelle (`V-…`, `U-…`, `E-…`), Werte je Datum mit `gilt`, Hinweis auf ähnliche vorhandene Merkmale (`daten.doppelt`); von Organisator:innen als Auftrag (mit strukturierten `daten`), von Mitwirkenden als Rückmeldung der Art `Ergänzung` |
| `art_definieren` | Organisator:innen schreiben, Mitwirkende schlagen vor | eine Art der Reise anlegen oder ändern (Bezeichnung, Grundform, Farbe, Beschreibung, summiert); schreibt über den Schreibweg direkt in `plan/arten.yaml` (siehe „Ontologie im Gespräch“); nur bei Instanzen mit Schreibweg |
| `merkmal_definieren` | Organisator:innen schreiben, Mitwirkende schlagen vor | ein Merkmal einer Art anlegen oder ändern: umbenennen, Typ und Werte, veränderlich, Stufe (`aus` schaltet ab), Hilfe, Frage, weitere Namen; warnt vor einem ähnlichen vorhandenen Merkmal (`trotzdem` übergeht das) |
| `auftrag_geben` | Organisator:innen | Änderungsauftrag, abgelegt in `auftraege.jsonl` |
| `entscheiden` | Organisator:innen | Option wählen, verwerfen oder ersetzen: wird sofort geprüft und mit Datum, Person und Grund festgehalten (Paket C) |
| `frage_beantworten` | Mitwirkende | Antwort auf eine offene Frage (F-…); hängt an der Frage, die Entscheidung bleibt bei der Organisator:in (Paket C) |
| `person_einladen` | je nach `regeln.einladen` (Vorgabe Organisator:innen) | legt eine Person mit Rolle an und stellt ihren persönlichen Link aus (Paket C) |

Schreibende Werkzeuge (`rueckmeldung_geben`, `frage_beantworten`, `aufgabe_*`, `alternative_vorschlagen`, `wunsch_aendern`) sehen nur Mitwirkende und Organisator:innen; `entscheiden` und `auftrag_geben` nur Organisator:innen, `person_einladen` wer `regeln.einladen` erreicht. Welche Werkzeuge es gibt und was sie dürfen, hängt zusätzlich vom Status der Reise und den eingeschalteten Bausteinen ab (Paket B, `docs/produkt.md`): `danach` sperrt neue Wünsche, Punkte, Alternativen und Aufträge (Abhaken geht noch), `archiv` alles Schreiben; ein ausgeschalteter Baustein nimmt seine Werkzeuge mit (`aufgaben`, `varianten`, `offene_fragen`, `rueckmeldungen`, `wuensche`). Geprüft wird bei jedem Aufruf, nicht nur in der Liste; der Dienst nennt den Grund.

`auftrag_geben` nimmt optional `entscheidung` (gewaehlt, verworfen, ersetzt) mit `ziel`. Widerspricht sie einer Entscheidung einer anderen Organisator:in, wird der Auftrag nicht eingearbeitet, es entsteht eine offene Frage, und alle beteiligten Organisator:innen sehen eine Meldung unter `rueckmeldungen`.

Gelesen wird die veröffentlichte Seite (`<seiten>/<reise>/daten.json`). Der Konnektor zeigt also denselben Stand wie die Webseite nach dem letzten Veröffentlichen.

`zeige E-…` nennt auch die Gliederung des Lesetexts der Art (`plan/arten.yaml` `lesetext`, `docs/ontologie.md`), damit der AI-Client den Text am Anfang der Etappe in diesem Aufbau schreibt. `zeige` zu einer ID listet auch die Aufgaben, die daran hängen. `zeige AG-…` zeigt eine Aufgabe mit Verlauf, `ueberblick` die Zahl der offenen und die überfälligen Aufgaben.

Aufgaben liegen live in `<ablage>/<reise>/aufgaben.json`, nicht im Repo. Der Rückmeldedienst ist ihr einziger Schreiber (`GET/POST /<reise>/aufgaben`, `PATCH /<reise>/aufgaben/<AG-id>`). Der Konnektor und die Webseite schreiben beide über ihn. In Claude Code zeigt `python3 engine/rueckmeldungen.py aufgaben <reise> [--alle]` sie an.

## Entscheiden, Fragen beantworten, Einladen (Paket C, 26.10.2026)

**`entscheiden`** (nur Organisator:innen, Baustein `varianten`, nicht in `danach` und `archiv`): Eingaben sind `option` (V-01.b), `status` (`gewaehlt`, `verworfen`, `ersetzt`; bei `ersetzt` auch `ersetzt_durch`), `grund` und optional `quelle`. Nur mit persönlichem Link, denn jede Entscheidung gehört genau einer Person. Der Dienst prüft sofort und lehnt mit Begründung ab, wenn die Option oder Wahlstelle fehlt, der Status unbekannt ist, der Grund fehlt, die Option schon so entschieden ist, `ersetzt_durch` nicht zur selben Wahlstelle gehört oder dieselbe Entscheidung schon vorliegt. Hinweise, die nichts verhindern: bisher gewählte Option wird ersetzt, Wahlstelle ist danach offen, fehlende Merkmale, ungeprüfte veränderliche Angaben, Wahlstelle für unterwegs, Regeln zwischen Optionen (die gewählte setzt etwas voraus, das nicht im Plan steht, oder schließt etwas im Plan aus; die verworfene wird von einer Option im Plan vorausgesetzt; `docs/alternativen.md`). Widerspricht die Entscheidung einer anderen Organisator:in, gilt `regeln.konflikt` (Meldung an beide, offene Frage, nichts wird übernommen).

Der Weg steht in `regeln.entscheidungsweg`:

| Weg | Was passiert |
|---|---|
| `direkt` | Die Prüfung im Gespräch genügt. Die Entscheidung gilt ab jetzt, ist als geprüfter Auftrag mit Datum, Person und Grund festgehalten (`daten.weg: direkt`, `geprueft: true`) und wird in der Konnektor-Ansicht der Option sofort als „eingetragen, noch nicht auf der Seite“ gezeigt. Claude Code trägt sie beim Einarbeiten nur noch in `routen.yaml` und `CLAUDE.md` ein, ohne neu zu entscheiden. |
| `auftrag` | Dieselbe Prüfung, aber die Entscheidung ist ein Auftrag (`daten.weg: auftrag`) und gilt erst, wenn Claude Code sie geprüft und eingearbeitet hat. Die KI sagt das so, bis dahin ist nichts entschieden. |

**`frage_beantworten`** (Mitwirkende und Organisator:innen, Bausteine `fragen` und `rueckmeldungen`): Die Antwort wird eine Rückmeldung der Art `Antwort` an die Frage und steht danach unter `zeige F-…`. Die Frage muss es geben und noch offen sein. Geklärt ist sie damit nicht: Das entscheidet ein:e Organisator:in.

**`person_einladen`** (`regeln.einladen`: `organisator` oder `mitwirkend`): Eingaben `vorname`, `rolle` (Standard `mitwirkend`), `reist`, `notiz`. Man kann höchstens die eigene Rolle vergeben. Der Dienst
1. stellt den persönlichen Link aus (`zugaenge.json`, Rechte 600) und gibt ihn dem Einladenden im Gespräch,
2. legt die Person live in `<ablage>/<reise>/einladungen.json` an, damit Rolle und Zugang sofort gelten (Konnektor und Rückmeldedienst kennen sie),
3. legt einen Auftrag an, damit Claude Code sie beim Einarbeiten in `reise.yaml` (`personen`) übernimmt. Steht sie dort, gilt `reise.yaml`.

Gibt es die Person schon, bekommt sie nur einen weiteren Link; ihre Rolle zu ändern ist eine Einstellung der Reise (Auftrag an `reise`). Einen Link zu sperren geht noch von Hand (Eintrag aus `zugaenge.json` löschen).

**Anleitung:** Beim Verbinden bekommt die KI Rolle, Reisestatus, Entscheidungsweg und die Grenzen der sprechenden Person (Mitwirkende:r: kann nicht entscheiden; Link ohne Person: kein Entscheiden und Einladen).

## Ontologie im Gespräch (ADR-0001, Paket O-3, Schritt 1, 29.10.2026)

Welche Arten eine Reise hat (Hotel, Refugi, Ryokan, Zugfahrt, Reiseteil …) und was zu jeder Sache einer Art bekannt sein muss, legt die Reise im Gespräch fest (`docs/ontologie.md`). Dafür gibt es `art_definieren` und `merkmal_definieren`:

- **Organisator:innen** schreiben damit direkt: Der Konnektor schickt die Anfrage mit Person und Rolle an den **Schreibweg** (`engine/schreiben.py dienst`, nur auf 127.0.0.1, mit dem Dienst-Geheimnis). Der prüft mit `reise.yaml` der Reise noch einmal Rolle und Status (Aktion `ontologie`: Organisator:in, Status mit vollem Schreibrecht), die Form der Angaben (Grundform, Typ, Stufe, Werte bei `auswahl`, kein zweiter Name eines vorhandenen Merkmals), ändert `plan/arten.yaml`, baut die Reise zur Probe (der Generator prüft alles Übrige, etwa ob eingetragene Werte zu neuen Auswahlwerten passen), sichert die Änderung als Commit mit Person und Werkzeug nach `main` und stößt das Veröffentlichen an. Lehnt er ab, bleibt alles unverändert, und die Person bekommt den Grund. Die Antwort heißt dann „Eingetragen und gesichert“; die Seite und die Werkzeuge `merkmale`/`zeige` zeigen den neuen Stand nach dem Veröffentlichen (wenige Minuten). Nur mit persönlichem Link: Jede Änderung gehört einer Person.
- **Mitwirkende** schlagen damit vor: Es entsteht eine Rückmeldung der Art `Ergänzung` an die Art („Art festlegen – bezeichnung: Refugi; grundform: aufenthalt“), die Organisator:innen unter `rueckmeldungen` sehen und im Gespräch übernehmen können.
- Die Grundform einer Art lässt sich nicht ändern (neue Art anlegen); Schlüssel bleiben, nur die Bezeichnung ändert sich (IDs und Werte der Reise hängen am Schlüssel). Eine Bewegung „aus eigener Kraft“ (`summiert`) und eine Folge bekommen ihre berechneten Merkmale (Gehzeit, Länge, Höhenmeter; Tage, Gehzeit, Unterkünfte, Anschluss) beim Anlegen. Ein neues Merkmal, das einem vorhandenen ähnelt (gleicher Wortstamm, zweiter Name), wird erst mit `trotzdem` angelegt.
- Der Verlauf steht in der Geschichte des Repos (ein Commit je Änderung: Reise, Titel, Text, Person, Werkzeug, Datum). Arten einer früheren Reise derselben Person übernimmt der AI-Client nur auf ausdrückliche Nachfrage, als Kopie (Product Owner, 28.10.2026); ein eigenes Werkzeug dafür folgt in O-3.
- Noch über den alten Weg (Auftrag, Einarbeiten): Werte an Dingen, neue Dinge, Wahlstellen und Optionen, Entscheidungen in `routen.yaml`, Fragen, Wissen. Sie folgen in den nächsten Schritten von O-3 (frieda-reist #91). Bis dahin laufen beide Wege.

Betrieb: `docs/betrieb.md`, Abschnitt „Schreibweg“. Ohne eingerichteten Schreibweg (`KN_SCHREIBDIENST` leer) gibt es die beiden Werkzeuge nicht, und die Anleitung nennt sie nicht.

## Konnektor „Frieda“ mit Anmeldung (Paket J3, 27.10.2026)

Ein Konnektor für alle Reisen einer Person. Er ersetzt nach der Umstellung die Konnektoren je Reise und den Konto-Link.
Die Adresse ist für alle gleich, `<FR_BASIS>/mcp`, und enthält kein Geheimnis.

**Anmelden:** Beim Hinzufügen in der Claude-App öffnet sich Friedas Anmeldeseite. Man gibt die E-Mail-Adresse und
den Code aus der Mail ein und stimmt dem Zugriff zu. Technisch ist das OAuth 2.1 mit PKCE (S256) und Refresh-Token mit
Rotation. Einzelheiten stehen in `engine/oauth.py` und [konten.md](konten.md).

**Werkzeuge:**
- `meine_reisen`
- `reise_anlegen`, wenn das Konto freigeschaltet ist; sonst `reisen_anlegen_anfragen`
- für den Betreiber `anfrage_entscheiden`
- alle Reise-Werkzeuge mit der Angabe `reise`. Bei nur einer Reise darf sie fehlen.

Die Rechte prüft der Konnektor je Reise wie bisher (Rolle aus `reise.yaml` und `einladungen.json`). Den Namen kennt
er aus dem Konto.

**Einladen:** `person_einladen` verlangt hier eine E-Mail-Adresse und verschickt die Einladung per Mail. Einen Link gibt
es nicht. Auch eine Person, die schon in der Reise steht, lässt sich so mit ihrem Konto verknüpfen.

**Entfernen:** `person_entfernen` (Organisator:in) nimmt eine Person heraus. Konto-Verknüpfung und alte Links enden sofort,
aus `reise.yaml` streicht sie das Einarbeiten.

**Neue Reise:** Das Konto wird nach dem Anlegen mit der Reise verknüpft. Personen mit Adresse bekommen eine Einladung
per Mail. Die Adressen stehen im Auftrag (`einladen`), nie in den Reisedaten.

**Wer darf fragen:**
- Redirect-URIs: nur `https://claude.ai/api/mcp/auth_callback` (dazu `FR_OAUTH_REDIRECTS`) und Loopback mit
  beliebigem Port (Claude Code, MCP Inspector, mit Warnung auf der Zustimmungsseite)
- Clients per DCR oder per Client ID Metadata Document von einem freigegebenen Host (`FR_CIMD_HOSTS`, Vorgabe
  `claude.ai`)

## Konto-Link: meine Reisen und neue Reise (Paket H, 27.10.2026)

Eine neue Reise legt eine Person an, keine Reise. Deshalb gibt es neben den Links je Reise einen persönlichen **Konto-Link** („Frieda – meine Reisen“), angelegt vom Betreiber: `python3 engine/konnektor.py konto <schluessel> <Name>`. Wer einen hat, darf Reisen anlegen. In der Claude-App wird er wie jeder Konnektor eingetragen. Er hat zwei Werkzeuge:

| Werkzeug | Was |
|---|---|
| `meine_reisen` | die veröffentlichten Reisen, auf denen die Person dabei ist (Schlüssel oder Name in `reise.yaml`), mit Rolle, Status, Link zur Seite und ihrem Link für die Claude-App; davor die Meldungen an sie, danach ihre angefragten neuen Reisen |
| `reise_anlegen` | Eingaben `titel`, `von`, `bis` (JJJJ-MM-TT), optional `ziel`, `personen` (je `vorname`, `rolle`, `reist`, `notiz`), `notiz` (Bekanntes in eigenen Worten mit Herkunft) und `pfad`; wer anlegt, ist Organisator:innen der neuen Reise |

`reise_anlegen` lehnt sofort ab, wenn Angaben fehlen oder nicht passen oder wenn es den Ordnernamen schon gibt, als veröffentlichte Reise, als Ablage oder als offene Anfrage (`reise.neue_reise_pruefen`). Sonst entsteht ein Auftrag mit `daten.neue_reise` in `<ablage>/_neu/auftraege.jsonl`, der zu keiner Reise gehört. Der Betrieb legt daraus die Reise an (`neu.aus_auftrag`, die Notiz wird der Überblick), veröffentlicht und schaltet sie frei. Danach schreibt er der Person eine Meldung mit den Links nach `<ablage>/_neu/meldungen.jsonl`. Die Links zu den Seiten liest der Konnektor aus `KN_SEITENLINKS` (Standard `seiten.json` neben den Zugängen), die der Betrieb beim Freischalten schreibt. Den Stand der Anfragen zeigt `rueckmeldungen.py liste _neu`. Eine persönliche Startseite im Web mit derselben Übersicht ist geplant (Issue #41).

## Einrichten (einmalig)

In einer Instanz erledigen das `betrieb/einrichten.sh`, `deploy.sh` und `freischalten.sh` (`docs/betrieb.md`). Von Hand:

1. Seite bauen und veröffentlichen, sodass `<seiten>/<reise>/daten.json` existiert. Der Konnektor braucht seine Module im selben Ordner (Liste `KN_MODULE` in `betrieb/deploy.sh`, dazu `rueckmeldungen.py`).
2. Den Dienst starten (`python3 engine/konnektor.py dienst`, z. B. als systemd-Dienst). Umgebung: `KN_SEITEN`, `KN_ZUGAENGE`, `KN_RUECKMELDEDIENST`, `KN_HOST`, `KN_PORT`, `KN_BASIS` (siehe Kopf von `engine/konnektor.py`).
3. Einen Reverse-Proxy mit HTTPS davorsetzen, mit geheimem Pfad und Drossel.
   Soll `person_einladen` Links ausstellen, braucht der Dienst `KN_BASIS` und Schreibrecht auf den Ordner von `KN_ZUGAENGE` (bei systemd `ReadWritePaths`, siehe `betrieb/vorlagen/konnektor.service`; Einrichtung in `docs/betrieb.md`). Ohne beides lehnt das Werkzeug mit einem Hinweis ab.
4. Links anlegen:
   ```
   KN_BASIS=https://<domain>/<pfad> python3 engine/konnektor.py zugang <reise> <person>
   … zugang beispielreise karl
   … zugang beispielreise mitwirkend      # Link ohne feste Person, fragt nach dem Vornamen
   ```
   `zugang <reise> <person>` nimmt den Schlüssel aus `reise.yaml personen` der veröffentlichten Seite, alternativ eine Rolle. Jeder Aufruf gibt einen Link aus. `zugaenge` zeigt alle. Neue Links gelten sofort, ein Neustart ist nicht nötig. Ein Link wird gesperrt, indem man seinen Eintrag aus `zugaenge.json` löscht. Die Links kommen nie ins Repo.

## In der Claude-App eintragen

Einstellungen → Konnektoren → „Eigenen Konnektor hinzufügen“. Als Name z. B. den Titel der Reise, als URL den Link, ohne Anmeldung. Danach kann man im Chat z. B. fragen: „Was steht an T-02 an?“, „Welche Fragen sind offen?“, „Gib als Rückmeldung zu U-02: …“.

Jede Person braucht ein eigenes Claude-Konto, in dem eigene Konnektoren erlaubt sind. Bei Team- oder Firmenkonten muss der Admin sie freigeben.

## Stand (26.10.2026)

Der `ueberblick` endet mit dem Abschnitt „Stand“: wann die Reise zuletzt veröffentlicht wurde, wann der Konnektor gestartet ist und mit welchem Code (Kurz-Hash von `konnektor.py`, `reise.py`, `rueckmeldungen.py`, `routen.py`). Liegt auf dem Server neuerer Code als der, mit dem der Dienst gestartet ist, steht dort, dass er einen Neustart braucht. So lässt sich in der App prüfen, ob das Veröffentlichen gelaufen ist, ohne auf den Server zu schauen. Der Rückmeldedienst wird dabei nicht geprüft.

## Symbol

Der Konnektor meldet beim Verbinden das Symbol der Reise (`serverInfo.icons`, dasselbe Bild wie das App-Symbol der Seite, `icon-32.png` und `icon-192.png` aus der veröffentlichten Seite, als Data-URI). So zeigt die Claude-App beim Konnektor das Symbol der Reise statt des allgemeinen der Domain. Ohne veröffentlichte Symbole entfällt das Feld. Ob und wie die App das Symbol anzeigt, entscheidet die App (Stand 26.10.2026 nicht überall gleich).

## Sicherheit

- Wer einen Link kennt, kann die Reise lesen und Rückmeldungen schicken. Das ist dasselbe Prinzip wie bei der Webseite. Ein Mitreisenden-Link kann keine Aufträge geben und nicht entscheiden. Der Link gehört zu einer Person: Wer ihn weitergibt, gibt ihre Rolle weiter.
- Über den Konnektor ändern sich nur Aufgaben sowie Arten und Merkmale direkt (Letzteres über den Schreibweg mit Rollen-, Status- und Formprüfung und einem Probebau, siehe „Ontologie im Gespräch“). Rückmeldungen und Aufträge sind Eingaben. Status `gewaehlt`/`verworfen` setzen nur Organisator:innen.
- Drossel im Reverse-Proxy. Der Dienst protokolliert weder Tokens noch Inhalte.
- Überwachung: `GET /gesund` (ohne Token) meldet `{"gesund": true}`, wenn die Zugänge lesbar und alle verlinkten Reisen veröffentlicht sind.

Darunter steht der Abschnitt „Einarbeiten“ (Paket D): wann zuletzt automatisch eingearbeitet wurde. Organisator:innen sehen zusätzlich, wie lange es von der Eingabe bis zum fertigen Stand dauert (Schnitt, Maximum), über alle Reisen zusammen, dazu fehlgeschlagene Läufe. Kosten zeigt der Überblick nicht; sie stehen nur im Protokoll. Quelle ist das Protokoll `einarbeiten-laeufe.jsonl`, das das Betriebsskript je Lauf schreibt (Ort: Ordner `_dienst` neben der Rückmelde-Ablage, `RM_LAEUFE` überschreibt ihn). Auf der Kommandozeile: `python3 engine/rueckmeldungen.py laeufe [<reise>] [--alle]`.
