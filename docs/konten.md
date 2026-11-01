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
  Rolle (ab J2).

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
| 11 | Konto selbst löschen | Konto und Adresse sind weg. Verlaufseinträge behalten den Namen. Die Adresse ist danach wieder frei |

## Sicherheit

- **Geheimnisse:** Codes, Sitzungen und Einladungen liegen nur als SHA-256 in der Datenbank.
- **Datenbank:** `<FR_KONTEN>/konten.db` (SQLite, WAL), Standard `<FR_SEITEN>/_konten`. Ordner 700, Datei 600. Der Ordner gehört zum Dienst der Instanz und enthält Konten, Anmeldungen und das Dienst-Geheimnis aller Nutzer dieser Instanz, getrennt von den Reisen. Bis 28.10.2026 lag er unter `<FR_ABLAGE>/_konten/`; eine dort liegende Datenbank gilt weiter, solange am neuen Ort keine liegt.
- **Keine Auskunft:** Antworten verraten nie, ob eine Adresse ein Konto hat. Mails an bekannte und unbekannte
  Adressen sind gleich.
- **Begrenzung:**
  - je Adresse 3 Codes in 15 Minuten, je IP 10 in der Stunde
  - je Reise 50 Einladungen am Tag
- **Sitzungen:** je Gerät, 365 Tage gültig und rollierend (jede Nutzung verlängert). Abmelden geht je Gerät oder
  überall.

## Anmeldung im Web (J2)

- **Seiten:** Der Konnektor-Dienst liefert sie unter Friedas eigener Adresse aus (`FR_BASIS`).
  - `/anmelden`: Adresse, dann Code, beim ersten Mal auch der Name
  - `/einladung/<token>`: Einladung ansehen, annehmen oder mit einer anderen Adresse anmelden
  - `/konto`: Name, Adresse, Reisen, Kalender (Abo-Link, Download, Einstellungen; #77), Bitte „Reisen anlegen“, Geräte, Konto löschen; für Betreiber die offenen Bitten
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
- **Regel `anmeldung` je Reise:**
  - `uebergang` (Vorgabe, solange umgestellt wird): ohne Anmeldung geht weiter ein eingetippter Name.
  - `noetig`: ohne Sitzung 401, ohne Mitgliedschaft 403.
- **Einplanen** auf dem Wunsch-Brett: auch angemeldet auf der Seite, aber nur als Organisator:in.
- **Zurückziehen:** Angemeldet geht es nur bei eigenen Rückmeldungen.
- **Reiseseite:** `GET api/ich` sagt, wer angemeldet ist.
  - Oben rechts steht „Anmelden“ oder der eigene Name (Molekül `kontoKnopf`, nur auf Friedas eigener Adresse).
  - Angemeldet entfällt das Namensfeld (`nameFeld`).
  - Antwortet der Dienst mit 401, bleibt der Eintrag im Ausgang und geht nach dem Anmelden los.

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

## Betrieb

Umgebung:

| Variable | Bedeutung |
|---|---|
| `FR_BASIS` | Öffentliche Adresse von Frieda (für Links in Mails, OAuth); gleich `FR_KN_ADRESSE` der Instanz, ohne Pfad (`docs/betrieb.md`, nginx-Vorlage des Konnektors) |
| `FR_SMTP_HOST`, `FR_SMTP_PORT` (587), `FR_SMTP_USER`, `FR_SMTP_PASS`, `FR_ABSENDER` | Mailversand mit STARTTLS |
| `FR_MAIL_DATEI` | Mails stattdessen als JSON-Zeilen in diese Datei (Tests, Probebetrieb) |
| `FR_OAUTH_REDIRECTS` | weitere erlaubte Redirect-URIs der Claude-App (durch Komma getrennt) |
| `FR_CIMD_HOSTS` | Hosts, von denen Client ID Metadata Documents geladen werden (Vorgabe `claude.ai`) |

Befehle für den Betreiber: `python3 engine/konten.py liste | anfragen | freischalten <email> [--nein] |
betreiber <email> | sperren <email> | entsperren <email> | loeschen <email> | zusammenfuehren <von> <nach> |
einladen <reise> <schluessel> <email> <rolle> <Name> <von>`.
