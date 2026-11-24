# Zusammenarbeit

Eine Reise planen selten eine Person allein. Frieda gibt jeder Person der Reise eine Rolle und einen Weg, mitzureden: Rückmeldungen an einer Stelle, Fragen, Aufgaben und Wünsche, im Gespräch mit Claude und auf der Reiseseite, mit denselben Regeln. Entschieden wird trotzdem klar: von einer Organisator:in, mit Datum und Grund.

**Auf einen Blick:** Wo: Gespräch · Reiseseite · Mein Konto · Wer: alle Personen der Reise, je nach Rolle · Baustein: Personen immer da; `rueckmeldungen`, `fragen`, `aufgaben`, `wuensche` zuschaltbar

## Was du damit tun kannst

- Personen per E-Mail-Adresse einladen und ihnen eine Rolle geben, auch wenn sie nur einen Teil der Reise mitreisen.
- Sehen, wer bei der Reise dabei ist, mit Rolle und ab wann sie oder er mitreist.
- An jeder Stelle der Reise etwas anmerken: Kommentar, Frage, Korrektur, Ergänzung.
- Offene Fragen stellen, beantworten und als Organisator:in klären.
- Aufgaben anlegen, zuweisen, mit Frist versehen und abhaken.
- Wünsche ohne feste Stelle einbringen, mit Punkten gewichten und unterwegs abhaken.
- Als Organisator:in Rückmeldungen im Gespräch einarbeiten und mit einer Antwort abschließen.

## So geht's

### Im Gespräch

> „Lade Karl ein, er ist mitwirkend und reist ab dem zweiten Tag mit.“

Claude fragt nach Karls E-Mail-Adresse, lässt die Angaben bestätigen und lädt ihn ein. Die Rolle gilt sofort, die Einladung kommt per Mail.

> „Gib als Rückmeldung zur Pension Burgblick: Das Frühstück gibt es erst ab acht.“

Die Rückmeldung landet im selben Eingang wie die Anmerkungen von der Reiseseite.

> „Welche Rückmeldungen sind offen? Arbeite die zur Strecke nach Hohnstein ein.“

Als Organisator:in lässt du Claude prüfen, eintragen und die Rückmeldung mit einem Satz für die Seite abschließen.

> „Leg eine Aufgabe an: Bahnticket in die App laden, zuständig Karl, Frist 13. Mai.“

| Werkzeug | wofür |
|---|---|
| `people` | Personen der Reise mit Rolle, „reist mit“ und von/bis |
| `person_invite`, `person_remove` | per E-Mail-Adresse einladen, Rolle ändern; jemanden herausnehmen |
| `feedback_give`, `feedback_list`, `feedback_resolve` | Rückmeldung geben, Stand ansehen, abschließen (übernommen, verworfen, Rückfrage) |
| `question_create`, `question_answer`, `question_close` | offene Frage anlegen, beantworten, als geklärt oder entfallen schließen |
| `tasks`, `task_create`, `task_update` | Aufgaben ansehen, anlegen, ändern und abhaken |
| `wishes`, `wish_update`, `wish_propose` | Wunsch-Brett lesen; Punkte, abhaken, einplanen; Vorschlag nach dem Prüfen eintragen |

### Auf der Reiseseite

- **Anmerken:** Neben jeder Stelle steht eine Sprechblase. Sie öffnet ein Fenster „Zu …“ mit den Rückmeldungen dieser Stelle (offene oben, erledigte zugeklappt) und dem Formular. Eine grüne Blase hat Rückmeldungen, eine Zahl zeigt die offenen. Ohne Netz bleibt der Eintrag im Ausgang und geht später los.
- **Zu tun:** Hier stehen die Aufgaben (Überfällig, Offen, Später möglich; Erledigtes zugeklappt) mit „+ Neue Aufgabe“ und die offenen Fragen. Stellen erscheinen als Namen, nie als Kennungen.
- **Wünsche:** Der Reiter zeigt das Wunsch-Brett mit „Neuer Wunsch“, den Spalten und der Bilanz je Person.

### Auf Mein Konto

Unter jeder Reise klappt die Liste der Personen auf. Die Einladungsmail führt dorthin und erklärt, wie man Frieda mit Claude verbindet.

## Rollen

| Rolle | darf |
|---|---|
| Gast | lesen |
| Mitwirkende:r | dazu Rückmeldungen, Wünsche und Punkte, Aufgaben, Antworten und Fragen; Eingaben wie Werte, Optionen, Wissen und Buchungen; auch für Personen, die nicht mitreisen |
| Organisator:in | dazu entscheiden, Status und Einstellungen der Reise setzen, Personen einladen und herausnehmen, Rückmeldungen abschließen, Wünsche einplanen |

Jede Stufe enthält die darunter. Rollen gelten je Reise. Es kann mehrere Organisator:innen geben; jede Entscheidung gehört genau einer Person. Claude ist keine Rolle mit Rechten: Es schlägt vor und trägt ein, entscheidet aber nie.

## Einladen und herausnehmen

- Eingeladen wird mit Vorname, E-Mail-Adresse, Rolle (Vorgabe mitwirkend), ob die Person mitreist, und einer Notiz. Wer einlädt, kann höchstens die eigene Rolle vergeben. Wer einladen darf, legt die Reise fest (Vorgabe: nur Organisator:innen).
- Hat die Adresse schon ein Konto, gilt die Einladung sofort, sonst beim ersten Anmelden. Der Link in der Einladungsmail gilt 30 Tage; wer ihn öffnet, darf sich auch mit einer anderen Adresse anmelden.
- Wer eingeladen ist, braucht für die Reiseseite kein Claude: Mitmachen geht dort angemeldet. Für das Gespräch braucht jede Person ein eigenes Claude-Konto mit Konnektoren ([Planen im Gespräch](gespraech.md)).
- `person_remove` macht eine Person zum Gast, der nicht mitreist. Niemand wird gestrichen; im Verlauf bleibt ihr Name.
- E-Mail-Adressen und Notizen zeigt Frieda nie in der Personenliste. Ob jemand schon angemeldet oder nur eingeladen ist, sehen nur Organisator:innen.

## Rückmeldungen, Fragen, Aufgaben, Wünsche

- **Rückmeldungen** sind Eingaben, keine Änderungen. Sie bleiben im Eingang, bis eine Organisator:in sie im Gespräch prüft, einträgt und abschließt. Die Antwort steht danach an der Stelle auf der Seite. Eine eigene Rückmeldung lässt sich zurückziehen, solange sie noch neu ist.
- **Fragen** hängen an einer Stelle oder an der Reise und haben eine Frist. Eine Antwort hängt an der Frage; ob sie geklärt ist, entscheidet eine Organisator:in.
- **Aufgaben** gelten sofort. Sie haben Titel, Zuständig, Wichtigkeit, „ab wann möglich“, Frist, Notiz und Status (offen, in Arbeit, erledigt, entfällt) und einen Verlauf. Gelöscht wird nie.
- **Wünsche** sind Ideen ohne feste Stelle: ein Ort, ein Erlebnis, ein Essen. Das Brett ordnet sie in Spalten: eingebracht, geprüft (Claude hat einen Vorschlag eingetragen, etwa „passt zum letzten Tag“), eingeplant, erlebt, passt nicht. Jede Person verteilt ihre Punkte (Vorgabe 10) nur auf eigene Wünsche. Abhaken dürfen alle Mitwirkenden, auch fremde Wünsche, unterwegs und danach, auch ohne Netz. Einplanen ist eine Entscheidung und bleibt Organisator:innen vorbehalten.

## Regeln und Grenzen

- **Mitmachen nur angemeldet.** Die Reiseseite lässt sich über ihren geheimen Link ohne Anmeldung lesen. Wer etwas einträgt, ist angemeldet und Mitglied der Reise; ein eingetippter Name zählt nicht.
- **Konflikte überschreiben sich nicht.** Entscheiden zwei Organisator:innen dieselbe Stelle verschieden, wird nichts übernommen. Es entsteht eine offene Frage mit beiden Positionen, und beide bekommen eine Meldung.
- **Status der Reise:** Im Status „danach“ gehen Rückmeldungen, Aufgaben, Antworten, Einladen und Abhaken von Wünschen weiter, neue Wünsche und Punkte nicht mehr. Im Archiv wird nur noch gelesen.
- **Bausteine:** Ist ein Baustein aus (etwa `wuensche`), verschwindet er aus Seite und Gespräch; seine Daten bleiben.
- **Grenzen:** Je Reise gehen höchstens 50 Einladungen am Tag hinaus.

## Siehe auch

- [Planen im Gespräch](gespraech.md), [Reiseseite](reiseseite.md), [Erinnerungen und Meldungen](erinnerungen.md), [Alternativen und Entscheidungen](alternativen.md), [Konto](konto.md)
- Referenz: [Rollen](../produkt.md#rollen), [Wunsch-Brett](../produkt.md#wunsch-brett-paket-g-27102026), [Konnektor](../konnektor.md), [Konten](../konten.md), [Design: Aufgaben und Wünsche](../design.md#aufgaben-und-wünsche-28102026)
