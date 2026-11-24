# Selbst betreiben

Frieda ist freie Software (AGPL-3.0). Jede Reisegruppe kann sie auf einem eigenen Server betreiben, als eigene Instanz mit eigenen Konten, eigenen Reisen und eigener Adresse. Diese Seite erklärt, was dann auf dem Server läuft und wie es zusammenspielt; die Anleitung mit allen Einzelheiten steht in [Betrieb einer Instanz](../betrieb.md).

**Auf einen Blick:** Wo: eigener Server · Wer: Betreiber einer Instanz · Baustein: –

## Was du damit tun kannst

- Eine eigene Instanz betreiben: Reiseseiten ausliefern, den Konnektor für die Claude-App anbieten, Konten und Anmeldung selbst führen.
- Die Reisen deiner Gruppe sicher speichern, mit vollständigem Verlauf und täglicher Sicherung.
- Neue Software automatisch übernehmen, erst nachdem sie geprüft ist, mit Rückfall auf den letzten guten Stand.
- Neue Reisen ohne Handarbeit freischalten: Seite, geheimer Link, Verknüpfung mit dem Konto, Einladungen.
- Konten freischalten, die Warteliste führen und Meldungen der Nutzer:innen zu Frieda empfangen.
- Den Zustand der Instanz überwachen.

## Was auf dem Server läuft

Frieda enthält keine eigene KI. Auf dem Server läuft kein Sprachmodell und es fallen keine Kosten für KI an; recherchiert und formuliert wird im AI-Client der Reisenden.

| Teil | Aufgabe |
|---|---|
| Konnektor | die Tür für die Claude-App; liefert auch Anmeldung, Mein Konto, Infoseite, Datenschutz und Impressum aus |
| Schreibweg | prüft jede Eintragung aus dem Gespräch (Rolle, Status, Form, Probebau) und schreibt sie in den Reisespeicher |
| Rückmeldedienst | nimmt Eingaben der Seite an: Rückmeldungen, Aufgaben, Wünsche, Packstand, Belege, Fotos |
| Push-Dienst | stellt Benachrichtigungen aufs Handy zu |
| Veröffentlichen | baut geänderte Reisen, holt neue Software, schaltet neue Reisen frei (nach jedem Schreibvorgang und alle 5 Minuten) |
| Wächter | täglich: Fristen, fällige Statuswechsel und alte Prüfdaten melden, Sicherungen schreiben, gelöschte Reisen nach der Schonfrist entfernen |

**Der Kreislauf.** Im Gespräch wird etwas festgelegt, der Schreibweg prüft es und speichert es sofort als neuen Reise-Stand. Das Veröffentlichen baut daraus die Seite neu, Ziel sind höchstens 2 Minuten. Rückmeldungen von der Seite liegen in der Ablage, bis eine Organisator:in sie im Gespräch einarbeitet; Aufgaben, Wünsche und Packstand gelten sofort.

**Was wohin gehört.** Drei Gruppen mischen sich nie:

1. **Die Software:** ein Klon des öffentlichen Repos auf dem Server, für jede Instanz gleich, ohne eigene Daten.
2. **Die Reisen:** der Reisespeicher, eine SQLite-Datenbank je Instanz, in die nur angehängt wird. Jeder Schreibvorgang ist eine neue Version mit Person, Werkzeug, Grund und Zeit; nichts wird überschrieben. Fotos, Tracks und Karten liegen daneben in einer Ablage nach Prüfsumme. Dazu die Ablage der Eingaben (Rückmeldungen, Aufgaben, Belege).
3. **Daten der Nutzer:innen:** Konten, Anmeldungen und Einladungen in einer eigenen Datenbank, getrennt von den Reisen.

Einstellungen und Geheimnisse der Instanz liegen in einem eigenen Ordner neben der Software, nie in ihr.

**Sicherung.** Der Wächter schreibt täglich geprüfte Schnappschüsse von Reisespeicher und Konten. Das Wegbringen außer Haus übernimmt das Backup deines Servers; es muss die Schnappschüsse und die Ablage der Medien mitnehmen. Zurücksetzen auf einen alten Stand einer Reise ist ein neuer Vorgang, der Verlauf bleibt.

**Veröffentlichen und neue Software.** Ein neuer Stand der Software wird geprüft, bevor der Server umschaltet: Sind die Prüfungen auf GitHub grün, gilt das als Nachweis, sonst laufen die Tests auf dem Server. Scheitert danach das Ausrollen, fällt die Instanz auf den letzten guten Stand zurück. Ein Fehler im Inhalt einer Reise hält nur diese Reise auf ihrem letzten guten Stand an, alle anderen laufen weiter. Ist GitHub nicht erreichbar, werden die Reisen trotzdem veröffentlicht; nur die Software wartet.

**Überwachung.** Nach fachlichem Erfolg setzen Veröffentlichen und Wächter je einen Stempel; ein Monitor meldet, wenn ein Stempel zu alt ist, ein Dienst ausgefallen ist oder der Schreibweg nicht gesund antwortet. Ein roter Stand meldet sich selbst, einmal je Störung, bei roten Reisen auch an deren Organisator:innen. Wer einen Heartbeat-Dienst nutzt, trägt dessen Adresse ein; sie wird nur nach Erfolg aufgerufen. Seiten und Konnektor haben je eine Gesundheitsadresse für Prüfungen von außen.

## Einrichten

Kurz der Weg; jeder Schritt steht ausführlich in [Neue Instanz einrichten](../betrieb.md#neue-instanz-einrichten).

1. **Server vorbereiten:** ein Benutzer für die Dienste, nginx mit HTTPS für die Adresse, Python 3, git, Node. Ein Konto bei GitHub braucht der Server nicht.
2. **Einstellungen anlegen:** aus der Vorlage `betrieb/einstellungen.beispiel` die Werte der Instanz eintragen (Name, Ordner, Adresse, Ports, Betreiberangaben fürs Impressum). Geheimes wie der Mailzugang kommt in eigene Dateien mit engen Rechten.
3. **Software klonen:** das öffentliche Repo als Software-Klon auf den Server holen und die Python-Umgebung daneben anlegen.
4. **Einrichten lassen:** `betrieb/einrichten.sh` prüft die Voraussetzungen und erzeugt Dienste, Zeitgeber, nginx-Bausteine und schmale sudo-Regeln; mit `--installieren` legt es sie nach Rückfrage an.
5. **nginx einbinden:** Reiseseiten und Konnektor teilen sich eine Adresse; der Konnektor steht an ihrer Wurzel.
6. **Dienste starten und prüfen:** Dienste und Zeitgeber einschalten, einmal veröffentlichen lassen, Gesundheitsadressen abfragen.
7. **Erste Reise:** Ein Konto mit dem Recht, Reisen anzulegen, legt sie in der Claude-App an; der nächste Lauf baut ihre Seite.

Mails verschickt die Instanz über einen SMTP-Zugang deiner Wahl. Mehrere Gruppen auf einem Server bekommen je eine eigene Instanz mit eigenem Namen, eigenen Ordnern, Ports und eigener Adresse.

**Werkzeuge für Inhalte.** Für Karten und Punkte aus OpenStreetMap gibt es Werkzeuge unter `werkzeuge/` ([Werkzeuge](../werkzeuge.md)). Gegenüber OpenStreetMap melden sie sich mit einer Kennung samt Kontaktangabe aus den Einstellungen. Optional kann eine Instanz einen eigenen Overpass-Dienst für ihre Regionen betreiben.

## Wer darf was

| Wer | darf |
|---|---|
| Betreiber | Konten freischalten, Warteliste freigeben, Konten sperren, Meldungen zu Frieda lesen |
| Organisator:in einer Reise | auf der Seite das Veröffentlichen anstoßen, wenn neue Software bereitliegt |
| alle | nichts am Server; Reiseinhalte entstehen nur im Gespräch |

## Regeln und Grenzen

- Jede Instanz ist für ihre Daten selbst verantwortlich und teilt nichts mit anderen Instanzen. Die Tabelle „Datenschutz je Instanz“ ist die Grundlage der Datenschutzerklärung, die der Konnektor zeigt; die rechtliche Prüfung ist Sache des Betreibers.
- Nichts Instanzspezifisches gehört in die Software: Pfade, Adressen, Benutzer und Meldeweg kommen aus den Einstellungen der Instanz.
- Im Ordner der Software wird nie gearbeitet; Änderungen an der Software kommen nur über das öffentliche Repo.
- Der Schutz des Reisespeichers hält Software-Fehler und Fehlbedienung ab, nicht jemanden mit Schreibzugriff auf die Datei. Eine Prüffunktion rechnet deshalb alle Prüfsummen nach.
- Ist der Dienstbenutzer zugleich Administrator des Servers, schützen die schmalen sudo-Regeln nur noch vor Fehlern. Empfohlen ist ein eigener Benutzer ohne Admin-Rechte.
- Reiseseiten sind über geheime Links lesbar. Diese Links stehen nie in Protokollen, Issues oder Nachrichten.

## Siehe auch

- [Konto](konto.md), [Lebenszyklus](lebenszyklus.md), [Erinnerungen](erinnerungen.md), [Karte](karte.md)
- Referenz: [Betrieb einer Instanz](../betrieb.md), [Der Kreislauf](../betrieb.md#der-kreislauf), [Veröffentlichen](../betrieb.md#veröffentlichen), [Überwachung](../betrieb.md#überwachung), [ADR-0009: Reisespeicher](../adr/0009-reisespeicher.md), [Werkzeuge](../werkzeuge.md), [Konten](../konten.md)
