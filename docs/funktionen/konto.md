# Konto und Anmeldung

Mit einem Konto erkennt dich Frieda an deiner E-Mail-Adresse, über alle Reisen hinweg und auf jedem Gerät. Ein Passwort gibt es nicht: Du bekommst bei jeder Anmeldung einen Code per Mail. Auf „Mein Konto“ findest du deine Reisen, Meldungen und Einstellungen an einem Ort.

**Auf einen Blick:** Wo: Mein Konto · Gespräch · Wer: jede Person mit Konto · Baustein: immer da (Profil für eine Reise: Baustein `profile`)

## Was du damit tun kannst

- Dich mit deiner E-Mail-Adresse und einem Code anmelden, ohne Passwort.
- Frieda als Konnektor in der Claude-App verbinden, einmal für alle deine Reisen.
- Auf Mein Konto alle Meldungen aus allen Reisen lesen und deine Reisen als Kacheln sehen.
- Den Kalender aller Reisen abonnieren und Benachrichtigungen je Gerät einschalten.
- Name, E-Mail-Adresse und Sprache ändern, angemeldete Geräte abmelden.
- Ein persönliches Profil mit deinen Vorlieben pflegen, das nur du siehst.
- Alle deine Daten als ZIP herunterladen.
- Dein Konto löschen.
- Dich auf die Warteliste setzen, um Reisen anlegen zu dürfen.

## So geht's

### Auf Mein Konto

**Anmelden.** Du gibst deine Adresse ein und bekommst einen sechsstelligen Code. Er gilt zehn Minuten und nur einmal. Beim ersten Mal entsteht dabei dein Konto, und Frieda fragt nach deinem Namen; bist du eingeladen, ist er schon eingetragen. Die Anmeldung gilt je Gerät ein Jahr und verlängert sich bei jeder Nutzung.

**Aufbau.** Oben deine Meldungen über alle Reisen: Ungelesene stehen oben mit grünem Punkt, ein Tipp führt an die Stelle in der Reise. Darunter „Deine Reisen“ als Kacheln mit Titelbild und deiner Rolle, dann der Abschnitt „Mit Claude verbinden“. Am Rechner stehen seltener gebrauchte Dinge in einer zweiten Spalte: Kalender, Benachrichtigungen, Einstellungen, „Meine Daten“, Abmelden und Löschen.

**Mit Claude verbinden.** Mein Konto zeigt in vier Schritten, wie du Frieda in der Claude-App einträgst: Einstellungen, Konnektoren, „Eigenen Konnektor hinzufügen“, die Adresse zum Kopieren einfügen, dann mit deiner E-Mail-Adresse anmelden und zustimmen. Danach erscheint jede Reise, zu der du gehörst, von selbst im Gespräch. Solange dein Konto nicht verbunden ist, steht oben die Karte „Neu bei Frieda?“ mit einem Link zur Erklärung.

**Kalender.** „Im Kalender abonnieren“ gibt dir einen persönlichen Link für alle deine Reisen. Unter „Konfigurieren“ stellst du ein, was drinsteht (Tage, Unterkünfte, Fahrten, Fristen) und welche Reisen.

**Benachrichtigungen.** Je Gerät einschalten, dann je Gruppe einstellen, was aufs Handy kommt, und wann Ruhe ist. Auf iPhone und iPad geht das nur in der Frieda-App vom Home-Bildschirm; Mein Konto zeigt dort die drei Schritte.

**Profil.** Hier siehst du deine Profileinträge, kannst ihren Text ändern oder sie löschen. Neue Einträge entstehen nur im Gespräch.

**Meine Daten.** „Meine Daten herunterladen“ liefert eine ZIP: deine Kontoangaben und je Reise, in der du dabei bist, die ganze Reise, die Beiträge und die Belege, die du sehen darfst. „Was ist drin?“ erklärt den Inhalt. Klappt der Export nicht, sagt die Seite das, statt eine halbe Datei zu liefern.

**Konto löschen.** „Konto löschen …“ zeigt auf einer eigenen Seite, was gelöscht wird, was bleibt und welche Reisen mitgehen; erst nach einem Häkchen geht es weiter.

### Im Gespräch

> „Merk dir, dass ich lieber in kleinen Pensionen übernachte als in großen Hotels.“

Claude formuliert den Eintrag, nennt die Herkunft (dieses Gespräch) und schreibt erst nach deinem ausdrücklichen Ja. An Wahlstellen kann Claude dein Profil später als Grund nennen, wenn die Reise den Baustein `profile` eingeschaltet hat.

> „Stell meine Sprache auf Englisch.“

| Werkzeug | wofür |
|---|---|
| `my_trips` | deine Reisen und Meldungen |
| `my_profile` | dein Profil lesen |
| `profile_entry_set` | Profileintrag anlegen oder ändern, nur mit deiner Bestätigung |
| `profile_entry_remove` | Profileintrag endgültig löschen |
| `language_set` | Sprache des Kontos |
| `calendar` | persönlicher Kalender-Link, auf Wunsch neu |
| `report_to_frieda` | Fehler, Wunsch oder Frage zu Frieda selbst an den Betreiber |

### Warteliste

Anmelden kann sich jede:r. Reisen anlegen darf ein Konto erst, wenn der Betreiber es freischaltet. Dafür trägst du dich auf der Warteliste ein, bestätigst den Link aus der Mail, und sobald der Betreiber dich freigibt, kommt die Mail „Du bist dabei“. Mit Konto geht auch die Bitte „Reisen anlegen“ auf Mein Konto oder im Gespräch.

## Wer darf was

| Wer | darf |
|---|---|
| jede Person mit Konto | ihr eigenes Konto, Profil, Kalender, Benachrichtigungen, Export, Löschen |
| Organisator:innen einer Reise | dazu sehen, wer dort schon angemeldet oder eingeladen ist (ohne Adressen) |
| Betreiber der Instanz | dazu Konten freischalten und Bitten beantworten |

## Regeln und Grenzen

- Je Adresse gibt es höchstens ein Konto. Eine neue Adresse bestätigst du mit einem Code an diese Adresse; gehört sie schon einem Konto, wird abgelehnt.
- Frieda verrät nie, ob eine Adresse ein Konto hat: Die Antworten sind immer gleich.
- Für den Konnektor brauchst du ein Claude-Konto, in dem eigene Konnektoren erlaubt sind; bei Team- oder Firmenkonten muss der Admin sie freigeben.
- Dein Profil sieht niemand außer dir: keine Mitreisenden, keine Organisator:innen, nicht die Reiseseite. Ohne deine ausdrückliche Bestätigung wird nichts eingetragen.
- „Auf allen Geräten abmelden“ beendet auch den Zugriff der Claude-App.
- Beim Löschen des Kontos verschwinden Adresse und Konto ganz; im Verlauf der Reisen steht danach „gelöschte Person“. Reisen, in denen nur du warst, gehen mit Schonfrist mit. Bist du die einzige Organisator:in einer Reise mit weiteren Mitgliedern, lehnt Frieda ab: erst die Rolle übergeben oder die Reise löschen.
- Was gespeichert wird, wer es sieht und wie lange Sicherungen bleiben, steht auf der Datenschutzseite der Instanz. Jede Instanz ist für ihre Daten selbst verantwortlich.
- Lesen einer Reiseseite geht auch ohne Konto über ihren Link; mitmachen nur angemeldet.

## Siehe auch

- [Planen im Gespräch](gespraech.md), [Lebenszyklus](lebenszyklus.md), [Zusammenarbeit](zusammenarbeit.md), [Erinnerungen](erinnerungen.md), [Sprachen](sprachen.md), [Selbst betreiben](selbst-betreiben.md)
- Referenz: [Konten](../konten.md), [Konnektor: Profil je Person](../konnektor.md#profil-je-person-12-paket-f-15112026), [Betrieb: Datenschutz je Instanz](../betrieb.md#datenschutz-je-instanz-15), [Design: Anmelde- und Kontoseiten](../design.md)
