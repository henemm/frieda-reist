# Konnektor: Reisen in der Claude-App

Mit dem Konnektor lässt sich eine Reise in jedem normalen Claude-Chat nutzen (App am Handy, Desktop, claude.ai). Claude liest dabei das Reisehandbuch und kann Rückmeldungen abgeben. Technisch ist es ein MCP-Server: `engine/konnektor.py` auf dem eigenen Server, neben dem Rückmeldedienst.

## Grundsätze (24.10.2026)

- Ändern geht nur als **Auftrag** (Variante B). Ein Auftrag aus der App ändert nichts sofort. Er wird in Claude Code mit „Rückmeldungen einarbeiten“ geprüft und dann übernommen.
- Nutzen dürfen ihn **alle Personen der Reise** (`reise.yaml personen`). Seit 26.10.2026 gehört ein Link zu einer Person; ihre Rolle entscheidet: `reisend` liest, `einbringer` gibt Rückmeldungen, Wünsche, Vorschläge und Aufgaben, `bestimmer` dazu Aufträge. Alte Links mit Rolle `mitreisend` gelten als `einbringer`.
- **Ein Link pro Reise und Person.**
- Gehört der Link zu einer Person, steht der Name fest. Bei einem Link ohne Person (nur Rolle) fragt Claude einmal nach dem Vornamen.
- **Aufgaben** (AG-01 …) sind die Ausnahme von „nur als Auftrag“: Alle dürfen sie über die App und über die Webseite sofort anlegen, ändern und abhaken. Eine Aufgabe hängt an einer oder mehreren IDs oder an der Reise allgemein. Sie hat Titel, Zuständig, Priorität, „ab wann möglich“, Frist, Notiz, Status (offen, in Arbeit, erledigt, entfällt) und einen Verlauf. Gelöscht wird nie.

## Was Claude damit kann

| Werkzeug | Wer | Was |
|---|---|---|
| `ueberblick` | alle | Eckdaten, Tagesplan mit IDs, Wahlstellen, Inhaltsverzeichnis |
| `zeige` | alle | Volltext zu einer ID (T-, E-, O-, U-, V-, P-, F-, W-) |
| `suche` | alle | Volltextsuche |
| `offene_fragen` | alle | F-Liste mit Frist und Status |
| `varianten` | alle | Pläne und Wahlstellen mit Dafür/Dagegen und Summen |
| `rueckmeldungen` | alle | bisherige Rückmeldungen mit Status und Antwort; bei Bestimmern auch die Aufträge |
| `rueckmeldung_geben` | alle | landet im selben Eingang wie die Rückmeldungen von der Webseite; Art `Wunsch` für Ideen ohne feste Stelle (ziel leer), sichtbar im Reiter „Wünsche“ |
| `aufgaben` | alle | Aufgaben, Standard nur offene; Filter nach Bezug, Zuständig, Status |
| `aufgabe_anlegen` | alle | neue Aufgabe, gilt sofort |
| `aufgabe_aendern` | alle | abhaken, Status, Felder, Kommentar in den Verlauf; gilt sofort |
| `merkmale` | alle | welche Merkmale eine Alternative braucht (mit Hinweis zum Recherchieren und Nachfragen), was jede Option hat und was fehlt; siehe `docs/alternativen.md` |
| `alternative_vorschlagen` | alle | neue Option mit Merkmalen; von Bestimmern als Auftrag (mit strukturierten `daten`), von Einbringern als Rückmeldung der Art `Ergänzung` |
| `auftrag_geben` | Bestimmer | Änderungsauftrag, abgelegt in `auftraege.jsonl` |

Schreibende Werkzeuge (`rueckmeldung_geben`, `aufgabe_*`, `alternative_vorschlagen`) sehen nur Einbringer und Bestimmer.

Gelesen wird die veröffentlichte Seite (`<seiten>/<reise>/daten.json`). Der Konnektor zeigt also denselben Stand wie die Webseite nach dem letzten Veröffentlichen.

`zeige` zu einer ID listet auch die Aufgaben, die daran hängen. `zeige AG-…` zeigt eine Aufgabe mit Verlauf, `ueberblick` die Zahl der offenen und die überfälligen Aufgaben.

Aufgaben liegen live in `<ablage>/<reise>/aufgaben.json`, nicht im Repo. Der Rückmeldedienst ist ihr einziger Schreiber (`GET/POST /<reise>/aufgaben`, `PATCH /<reise>/aufgaben/<AG-id>`). Der Konnektor und die Webseite schreiben beide über ihn. In Claude Code zeigt `python3 engine/rueckmeldungen.py aufgaben <reise> [--alle]` sie an.

## Einrichten (einmalig)

1. Seite bauen und veröffentlichen, sodass `<seiten>/<reise>/daten.json` existiert. Der Konnektor braucht `konnektor.py`, `reise.py` und `rueckmeldungen.py` im selben Ordner.
2. Den Dienst starten (`python3 engine/konnektor.py dienst`, z. B. als systemd-Dienst). Umgebung: `KN_SEITEN`, `KN_ZUGAENGE`, `KN_RUECKMELDEDIENST`, `KN_HOST`, `KN_PORT`, `KN_BASIS` (siehe Kopf von `engine/konnektor.py`).
3. Einen Reverse-Proxy mit HTTPS davorsetzen, mit geheimem Pfad und Drossel.
4. Links anlegen:
   ```
   KN_BASIS=https://<domain>/<pfad> python3 engine/konnektor.py zugang <reise> <person>
   … zugang beispielreise karl
   … zugang beispielreise einbringer      # Link ohne feste Person, fragt nach dem Vornamen
   ```
   `zugang <reise> <person>` nimmt den Schlüssel aus `reise.yaml personen` der veröffentlichten Seite, alternativ eine Rolle. Jeder Aufruf gibt einen Link aus. `zugaenge` zeigt alle. Neue Links gelten sofort, ein Neustart ist nicht nötig. Ein Link wird gesperrt, indem man seinen Eintrag aus `zugaenge.json` löscht. Die Links kommen nie ins Repo.

## In der Claude-App eintragen

Einstellungen → Konnektoren → „Eigenen Konnektor hinzufügen“. Als Name z. B. den Titel der Reise, als URL den Link, ohne Anmeldung. Danach kann man im Chat z. B. fragen: „Was steht an T-02 an?“, „Welche Fragen sind offen?“, „Gib als Rückmeldung zu U-02: …“.

Jede Person braucht ein eigenes Claude-Konto, in dem eigene Konnektoren erlaubt sind. Bei Team- oder Firmenkonten muss der Admin sie freigeben.

## Stand (26.10.2026)

Der `ueberblick` endet mit dem Abschnitt „Stand“: wann die Reise zuletzt veröffentlicht wurde, wann der Konnektor gestartet ist und mit welchem Code (Kurz-Hash von `konnektor.py`, `reise.py`, `rueckmeldungen.py`). Liegt auf dem Server neuerer Code als der, mit dem der Dienst gestartet ist, steht dort, dass er einen Neustart braucht. So lässt sich in der App prüfen, ob das Veröffentlichen gelaufen ist, ohne auf den Server zu schauen. Der Rückmeldedienst wird dabei nicht geprüft.

## Symbol

Der Konnektor meldet beim Verbinden das Symbol der Reise (`serverInfo.icons`, dasselbe Bild wie das App-Symbol der Seite, `icon-32.png` und `icon-192.png` aus der veröffentlichten Seite, als Data-URI). So zeigt die Claude-App beim Konnektor das Symbol der Reise statt des allgemeinen der Domain. Ohne veröffentlichte Symbole entfällt das Feld. Ob und wie die App das Symbol anzeigt, entscheidet die App (Stand 26.10.2026 nicht überall gleich).

## Sicherheit

- Wer einen Link kennt, kann die Reise lesen und Rückmeldungen schicken. Das ist dasselbe Prinzip wie bei der Webseite. Ein Mitreisenden-Link kann keine Aufträge geben.
- Über den Konnektor ändert sich nichts direkt. Rückmeldungen und Aufträge sind Eingaben. Was übernommen wird, entscheidet die Prüfung in Claude Code. Status `gewaehlt`/`verworfen` setzen nur Bestimmer.
- Drossel im Reverse-Proxy. Der Dienst protokolliert weder Tokens noch Inhalte.
- Überwachung: `GET /gesund` (ohne Token) meldet `{"gesund": true}`, wenn die Zugänge lesbar und alle verlinkten Reisen veröffentlicht sind.

Darunter steht der Abschnitt „Einarbeiten“ (Paket D): wann zuletzt automatisch eingearbeitet wurde. Bestimmer sehen zusätzlich, wie lange es von der Eingabe bis zum fertigen Stand dauert (Schnitt, Maximum) und was die Läufe kosten (Summe, Schnitt, letzter Lauf) über alle Reisen zusammen, dazu fehlgeschlagene Läufe; alle anderen sehen keine Beträge. Quelle ist das Protokoll `einarbeiten-laeufe.jsonl`, das das Betriebsskript je Lauf schreibt (Ort: Ordner `_dienst` neben der Rückmelde-Ablage, `RM_LAEUFE` überschreibt ihn). Auf der Kommandozeile: `python3 engine/rueckmeldungen.py laeufe [<reise>] [--alle]`.
