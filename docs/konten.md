# Konten: Anmeldung mit E-Mail-Adresse

Paket J (Issue #43). Stand: Schritt J1 (Grundlage, `engine/konten.py`). Anmeldeseiten im Web (J2) und der Konnektor
„Frieda“ mit OAuth für alle Reisen (J3) folgen.

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
| 9 | Freigeschaltet | Legt eine Reise an, ist dort Bestimmer und lädt per Mail ein (J3) |
| 10 | Aus der Reise nehmen, Konto sperren | Die Verknüpfung entfällt. Sperren meldet alle Geräte ab |
| 11 | Konto selbst löschen | Konto und Adresse sind weg. Verlaufseinträge behalten den Namen. Die Adresse ist danach wieder frei |

## Sicherheit

- **Geheimnisse:** Codes, Sitzungen und Einladungen liegen nur als SHA-256 in der Datenbank.
- **Datenbank:** `<RM_ABLAGE>/_konten/konten.db` (SQLite, WAL). Ordner 700, Datei 600.
- **Keine Auskunft:** Antworten verraten nie, ob eine Adresse ein Konto hat. Mails an bekannte und unbekannte
  Adressen sind gleich.
- **Begrenzung:**
  - je Adresse 3 Codes in 15 Minuten, je IP 10 in der Stunde
  - je Reise 50 Einladungen am Tag
- **Sitzungen:** je Gerät, 365 Tage gültig und rollierend (jede Nutzung verlängert). Abmelden geht je Gerät oder
  überall.

## Betrieb

Umgebung:

| Variable | Bedeutung |
|---|---|
| `FR_BASIS` | Öffentliche Adresse von Frieda (für Links in Mails) |
| `FR_SMTP_HOST`, `FR_SMTP_PORT` (587), `FR_SMTP_USER`, `FR_SMTP_PASS`, `FR_ABSENDER` | Mailversand mit STARTTLS |
| `FR_MAIL_DATEI` | Mails stattdessen als JSON-Zeilen in diese Datei (Tests, Probebetrieb) |

Befehle für den Betreiber: `python3 engine/konten.py liste | anfragen | freischalten <email> [--nein] |
betreiber <email> | sperren <email> | entsperren <email> | loeschen <email> | zusammenfuehren <von> <nach> |
einladen <reise> <schluessel> <email> <rolle> <Name> <von>`.
