# Erinnerungen, Meldungen und Kalender

Fristen verstreichen, Preise ändern sich, und irgendwann beginnt die Reise. Frieda behält das im Blick: Der Wächter und der Erinnerer rechnen täglich nach, was ansteht, und melden es der richtigen Person, auf der Reiseseite, in der Claude-App, als Push-Nachricht oder per Mail. Dazu kommt die Reise als Kalender.

**Auf einen Blick:** Wo: Gespräch · Reiseseite · Mein Konto · Wer: Meldungen an Zuständige und Organisator:innen; Kalender für alle Personen der Reise · Baustein: `waechter` (Statushinweis und Kalender immer da)

## Was du damit tun kannst

- Erinnert werden, bevor eine Aufgabe fällig wird, und wenn sie überfällig ist.
- Erinnert werden an Fristen und Stornofristen von Buchungen und an Termine wie „Online-Check-in ab …“.
- Auf Wunsch an offene Zahlungen erinnert werden.
- Als Organisator:in erfahren, welche veränderlichen Angaben (Preise, Öffnungszeiten, Fahrpläne) zu lange nicht geprüft wurden.
- Rechtzeitig hören, dass der Status der Reise wechseln sollte, etwa auf „unterwegs“.
- Alle Meldungen über alle Reisen an einem Ort sehen und als gelesen markieren.
- Push-Nachrichten aufs Handy bekommen, mit Ruhezeit, oder Wichtiges per Mail.
- Die Reise im eigenen Kalender abonnieren oder einzelne Tage und Unterkünfte herunterladen.

## So geht's

### Was gemeldet wird

| Meldung | wann | an wen |
|---|---|---|
| Frist | Aufgabe offen, Frist in höchstens 3 Tagen; überfällig alle 7 Tage neu | zuständige Person, sonst Organisator:innen |
| Jetzt möglich | „ab wann möglich“ einer Aufgabe oder Buchung ist erreicht | wie oben bzw. wer gebucht hat |
| Buchungsfrist, Stornofrist | Frist oder „kostenlos stornieren bis“ einer Buchung in höchstens 3 Tagen | wer gebucht hat, sonst Organisator:innen |
| Zahlung offen | nur wenn eingeschaltet: Buchung offen oder angezahlt, Frist oder Reisetag naht | wer gebucht hat, sonst Organisator:innen |
| Prüfung | eine veränderliche Angabe hat kein Prüfdatum oder ein älteres als 60 Tage | Organisator:innen |
| Statuswechsel | 7 Tage vor dem ersten Tag „fest“, am ersten Tag „unterwegs“, nach dem letzten „danach“ | Organisator:innen |
| Konflikt | zwei Organisator:innen haben dieselbe Stelle verschieden entschieden | beide |

Dazu kommen Push-Nachrichten zu neuen Rückmeldungen (an Organisator:innen), neu zugewiesenen Aufgaben und neuen Versionen der Software. Die Fristen und Abstände sind Spielregeln der Reise und lassen sich ändern ([Wächter](../waechter.md#was-gemeldet-wird)).

### Im Gespräch

> „Was steht für mich an?“

Claude beginnt mit den Meldungen an dich: im Überblick der Reise und in der Liste deiner Reisen, über alle Reisen hinweg.

> „Prüf die Angaben, die Frieda als ungeprüft meldet.“

Claude schlägt jede Angabe nach. Stimmt sie, bekommt sie ein neues Prüfdatum und die Quelle. Weicht sie ab, entscheidet eine Organisator:in; bis dahin bleibt der alte Wert stehen.

> „Gib mir den Link, um alle meine Reisen im Kalender zu abonnieren.“

| Werkzeug | wofür |
|---|---|
| `overview`, `my_trips`, `feedback_list` | Meldungen an dich, je Reise und über alle Reisen |
| `item_update` | geprüfte Angabe mit Prüfdatum und Quelle eintragen |
| `trip_status_set` | Status der Reise umstellen (Organisator:innen) |
| `setting_set` | Baustein `waechter` und seine Spielregeln einstellen (Organisator:innen) |
| `calendar` | persönlicher Abo-Link für alle Reisen; `new` stellt einen neuen aus |

### Auf der Reiseseite

- Angemeldet steht oben der Hinweis „Für dich“ mit den neuesten drei Meldungen dieser Reise und „Gelesen“. Eine Zeile führt an die Stelle, um die es geht. Der Hinweis steht auch ohne Netz.
- Ist ein Statuswechsel fällig, stellen Organisator:innen ihn direkt um: Tipp auf das Status-Etikett unter dem Untertitel oder auf den Knopf am Hinweis.
- **Kalender:** An der Heimat eines Dings (Tag, Unterkunft, Aufenthalt) steht „In den Kalender“, sobald es entschieden ist und ein Datum hat. Im Reiseüberblick unter der Zeitachse steht „Ganze Reise in den Kalender“. Das ist ein Download, er braucht Netz.

### Auf Mein Konto

- **Meldungen:** ganz oben, über alle Reisen, ungelesene mit grünem Punkt, Konflikte zuerst. Ein Tipp führt an die Stelle und merkt die Meldung als gelesen, auf allen Geräten.
- **Benachrichtigungen:** Push je Gerät einschalten. Je Gruppe wählst du, was aufs Handy kommt (Wichtiges, Rückmeldungen und Aufgaben, Fristen; Leises wie Prüfungen nur, wenn eingeschaltet), und die Ruhezeit (Vorgabe 21:30 bis 7:00 Uhr auf der Uhr des Geräts). Was in die Ruhezeit fällt, kommt an ihrem Ende. Auf iPhone und iPad gibt es Push nur in der Frieda-App vom Home-Bildschirm; Mein Konto zeigt die drei Schritte dorthin.
- **Mail:** Wichtiges (Status fällig, Konflikt, Frist überfällig) kommt per Mail, wenn es nach einem Tag noch gilt, ungelesen ist und du kein Gerät mit Benachrichtigungen hast; einstellbar auf „sofort“ oder „nie“. Auf Wunsch gibt es eine tägliche Zusammenfassung.
- **Kalender:** „Im Kalender abonnieren“ mit dem passenden Weg für Apple, Google und Outlook, „ICS-Datei herunterladen“ und unter „Konfigurieren“ die Auswahl: welche Einträge (Tage, Unterkünfte, Aufenthalte, Fahrten, Fristen von Buchungen und Aufgaben), bei Aufgaben nur die eigenen, Erinnerungen vor Fristen und Terminen, welche Reisen.

## Stufen der Meldungen

| Stufe | was | Wege |
|---|---|---|
| Wichtig | Status fällig, Konflikt, Frist überfällig | Seite und Push sofort; Mail nach einem Tag ohne Wirkung |
| Normal | Frist naht, Stornofrist, jetzt möglich, Zahlung offen; Rückmeldungen, Fragen, Wünsche, Aufgaben an dich | Seite und Push; auf Wunsch tägliche Zusammenfassung per Mail |
| Leise | Prüfungen veränderlicher Angaben, neue Versionen | Seite, Mein Konto, Claude-App; Push nur, wenn eingeschaltet |

## Regeln und Grenzen

- **Frieda meldet nur.** Wächter und Erinnerer rechnen, sie schlagen nichts nach und ändern nichts. Nachgeschlagen wird im Gespräch mit Claude ([ADR-0001](../adr/0001-kern.md)).
- **Niemand wechselt den Status automatisch.** Frieda erinnert, eine Organisator:in stellt um.
- **Nur mit Baustein und im richtigen Status:** Fristen, Zahlungen und Prüfungen meldet der Wächter nur bei eingeschaltetem Baustein `waechter` und im Status „fest“ oder „unterwegs“. Der Statushinweis gilt für jede Reise mit Tagen.
- **Keine Flut:** Jede Meldung kommt einmal; Überfälliges höchstens alle 7 Tage. Höchstens 15 Prüfungen je Lauf, die ältesten zuerst. Meldungen verschwinden nach 14 Tagen oder wenn erledigt ist, worum es ging; Konflikte bleiben.
- **Kalender nur mit Entschiedenem:** Im Kalender steht, was gewählt ist und ein Datum hat, mit Uhrzeiten, wo es welche gibt. Ein neuer Abo-Link macht den alten ungültig. Das Abo zählt nur Reisen, in denen du Mitglied bist.
- **Vorlesen zählt nicht als gelesen:** Nennt Claude eine Meldung, bleibt sie auf der Seite ungelesen, bis du sie dort oder auf Mein Konto als gelesen markierst.

## Siehe auch

- [Zusammenarbeit](zusammenarbeit.md), [Buchungen](buchungen.md), [Lebenszyklus einer Reise](lebenszyklus.md), [Konto](konto.md), [Reiseseite](reiseseite.md)
- Referenz: [Wächter und Erinnerer](../waechter.md), [Push-Nachrichten](../betrieb.md#push-nachrichten), [Kalender im Betrieb](../betrieb.md#kalender), [Konten](../konten.md)
