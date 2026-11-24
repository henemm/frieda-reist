# Lebenszyklus einer Reise

Eine Reise begleitet Frieda von der ersten Idee bis ins Archiv. Der Status der Reise sagt, was gerade gilt: was gemahnt wird, was noch geändert werden darf und womit die Seite beginnt. Dazu legt jede Reise selbst fest, welche Bausteine sie braucht.

**Auf einen Blick:** Wo: Gespräch · Reiseseite · Mein Konto · Wer: neue Reise mit freigeschaltetem Konto; Status, Bausteine und Löschen Organisator:innen · Baustein: immer da

## Was du damit tun kannst

- Eine neue Reise im Gespräch anlegen: Titel, Zeitraum, Ziel, Sprache, Personen und was schon bekannt ist.
- Ohne Freischaltung darum bitten, Reisen anlegen zu dürfen.
- Den Status der Reise setzen, von Idee über Planung, fest, unterwegs und danach bis Archiv, auch rückwärts.
- Rechtzeitig erinnert werden, wenn ein Statuswechsel fällig ist.
- Bausteine ein- und ausschalten: Varianten, Karte, Rückmeldungen, Fragen, Aufgaben, Wünsche, Packliste, Wächter, Profile.
- Eckdaten wie Titel, Untertitel, Ziel und Zeitraum ändern.
- Eine Reise löschen und innerhalb der Schonfrist zurückholen.

## So geht's

### Im Gespräch

> „Leg eine neue Reise an: Malerweg in vier Tagen, 13. bis 16. Mai, Sächsische Schweiz. Ida organisiert, Karl wirkt mit und kommt erst am zweiten Tag dazu.“

Claude fragt nur nach Lücken (etwa der E-Mail-Adresse für Karls Einladung) und lässt bestätigen, was genau angelegt wird. Dann legt Frieda die Reise an. Sobald ihre Seite online ist, ist die Reise mit deinem Konto verknüpft, die übrigen Personen bekommen eine Einladung per Mail, und du bekommst die Meldung „neue Reise“.

Die neue Reise steht im Status **Idee** und hat schon Eckdaten, einen Abschnitt Wissen und eine erste offene Frage. Danach füllt sie sich im Gespräch: Arten klären, Orte, Unterkünfte und Strecken anlegen, Start und Ende setzen, Tage anlegen, Wissen aus Quellen schreiben.

> „Wir planen jetzt richtig: Stell die Reise auf Planung und schalte Varianten und Karte dazu.“

| Werkzeug | wofür |
|---|---|
| `trip_create` | neue Reise anlegen |
| `trip_create_request` | um das Recht bitten, Reisen anzulegen |
| `my_trips` | deine Reisen mit Rolle und Status, davor deine Meldungen |
| `trip_status_set` | Status setzen, mit Grund |
| `setting_set` | Bausteine, Spielregeln und Sprache der Reise |
| `trip_update` | Titel, Untertitel, Kurzname, Ziel, Zeitraum |
| `start_end_set` | Start und Ende des Plans (Datum und Ort) |

### Auf der Reiseseite

Unter dem Untertitel steht der Status als Etikett. Organisator:innen tippen darauf, wählen den neuen Status und bestätigen. Ist ein Wechsel fällig, öffnet der Hinweis „Für dich“ dieselbe Auswahl gleich mit dem vorgeschlagenen Status.

### Auf Mein Konto

Unter „Deine Reisen“ steht jede Reise als Kachel. Archivierte Reisen stehen zugeklappt in einem eigenen Abschnitt darunter. Organisator:innen finden unter den aufgeklappten Personen einer Reise den roten Link „Reise löschen …“: erst eine Erklärung mit Häkchen, dann den Namen der Reise eintippen. Eine zum Löschen vorgemerkte Reise steht oben in einem grauen Kasten mit „Reise zurückholen“.

## Die Status

| Status | Was gilt |
|---|---|
| Idee | Eckdaten, Personen und Wünsche sammeln. Kein Plan nötig, keine Warnungen. |
| Planung | Alles ist offen. Lücken und offene Wahlstellen sind normaler Zwischenstand. |
| fest | Der Plan ist gewählt, das Buchen läuft. Offene Wahlstellen und ungeprüfte Angaben werden im Gespräch gemahnt, Aufgabenfristen zählen, der Wächter prüft Veränderliches. |
| unterwegs | Wie fest. Vorn in der Leiste steht „Heute“, Wahlstellen für unterwegs rücken nach vorn, Wünsche werden abgehakt. |
| danach | Nachlese: Rückmeldungen, Aufgaben, Antworten, Wissen und Abhaken von Wünschen gehen noch. Der Plan ist schreibgeschützt: keine neuen Werte, Dinge, Alternativen oder Entscheidungen. |
| Archiv | Nur noch lesen. |

**Statuswechsel-Hinweis.** Für jede Reise mit Tagen erinnert Frieda die Organisator:innen: sieben Tage vor dem ersten Tag an „fest“, am ersten Tag an „unterwegs“, nach dem letzten Tag an „danach“. Der Hinweis erscheint auf der Reiseseite und als Push-Nachricht; gilt er nach einem Tag noch und hat die Person keine Benachrichtigungen eingeschaltet, kommt er einmal per Mail. Er wiederholt sich alle sieben Tage, bis gewechselt ist. Wechseln tut immer eine Organisator:in, nie Frieda oder Claude.

**Bausteine.** Immer da sind Plan mit Zeitachse und Tagesseiten, Wissen, Suche und Personen. Eine neue Reise startet mit Rückmeldungen, Fragen, Aufgaben, Wünschen und Wächter; Varianten und Karte kommen dazu, wenn die Planung beginnt. Ein ausgeschalteter Baustein verschwindet aus Seite und Gespräch, seine Daten bleiben.

## Wer darf was

| Rolle | darf |
|---|---|
| Konto ohne Freischaltung | um das Recht bitten, Reisen anzulegen |
| freigeschaltetes Konto | Reisen anlegen; wer anlegt, ist Organisator:in |
| Organisator:in | Status, Bausteine, Spielregeln, Eckdaten ändern; die Reise löschen und zurückholen |
| Mitwirkende:r, Gast | Status und Bausteine sehen, nicht ändern |

## Regeln und Grenzen

- Der Status wird ausdrücklich gesetzt, nie aus dem Datum abgeleitet. Jede Änderung bekommt einen Verlaufseintrag mit Person, Datum und Grund.
- Status und Einstellungen lassen sich in jedem Status ändern, damit eine gesperrte Reise wieder geöffnet werden kann, auch aus dem Archiv. Auf der Reiseseite gibt es die Wahl „Archiv“ nicht, nur im Gespräch.
- Wie viele Reisen ein Konto anlegen darf, legt die Instanz fest (Vorgabe 10). Eine archivierte Reise gibt keinen Platz frei.
- Inhalte einer Reise löscht Frieda nie: Eine Buchung wird storniert, eine Option verworfen, eine Aufgabe entfällt. Ganz entfernen lässt sich nur die Reise als Ganzes.
- Eine gelöschte Reise ist sofort für alle unsichtbar; die übrigen Mitglieder bekommen Mail und Meldung. Bis zum Ende der Schonfrist (Vorgabe 14 Tage) lässt sie sich zurückholen, danach entfernt Frieda sie endgültig.
- Den Ordnernamen einer Reise gibt es nur einmal; Frieda lehnt eine neue Reise mit einem schon vergebenen Namen ab.

## Siehe auch

- [Planen im Gespräch](gespraech.md), [Reisemodell](reisemodell.md), [Erinnerungen](erinnerungen.md), [Konto](konto.md), [Zusammenarbeit](zusammenarbeit.md), [Sprachen](sprachen.md)
- Referenz: [Produkt: Status einer Reise](../produkt.md#status-einer-reise), [Neue Reise anlegen](../neue-reise.md), [Konten](../konten.md), [Wächter und Erinnerer](../waechter.md)
