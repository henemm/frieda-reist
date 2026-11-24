# Alternativen und Entscheidungen

Fast jede Reise hat Stellen, an denen mehrere Möglichkeiten offen sind: zwei Unterkünfte im selben Ort, zwei Wege zum Zug, ein Ausweichziel bei Regen. Frieda hält diese Möglichkeiten nebeneinander, vergleicht sie nach den Merkmalen der Reise und hält fest, wer wann was entschieden hat und warum.

**Auf einen Blick:** Wo: Gespräch · Reiseseite · Wer: alle lesen; Mitwirkende schlagen vor; Organisator:innen entscheiden · Baustein: `varianten`

## Was du damit tun kannst

- Eine **Wahlstelle** anlegen: eine Stelle im Plan mit mehreren Möglichkeiten, etwa „Unterkunft in Hohnstein“.
- Möglichkeiten als **Optionen** an die Wahlstelle hängen: Unterkünfte, Strecken, Aufenthalte, Orte oder ganze Reiseteile aus mehreren Tagen.
- Die Optionen nebeneinander vergleichen, am Rechner als Tabelle, am Handy als Karten.
- Festlegen, ob vor der Reise entschieden wird oder erst unterwegs, und für unterwegs einen Auslöser nennen („nur bei trockenem Fels“).
- Eine Option favorisieren, mit Begründung, ohne schon zu entscheiden.
- Entscheiden: eine Option wählen, verwerfen oder durch eine andere ersetzen, immer mit Grund.
- Benannte **Pläne** bilden: feste Kombinationen von Optionen über die ganze Reise, die man als Ganzes vergleicht.
- Regeln zwischen Optionen festhalten: „geht nur zusammen mit …“ und „nie zusammen mit …“.

## So geht's

### Begriffe

- **Wahlstelle:** eine Stelle mit mehreren Möglichkeiten. Sie hängt an dem Element, um das es geht: einem Tag, einer Strecke, einer Unterkunft, einem Ort oder einem Abschnitt des Wissens (etwa „Essen“). Jedes Ding kann Alternativen haben, nur der Tag selbst nicht; einen anderen Tagesablauf wählt man als Reiseteil.
- **Option:** eine Möglichkeit an einer Wahlstelle. Sie hat einen Zustand mit Verlauf: vorgeschlagen, favorisiert, gewählt, verworfen oder ersetzt. Eine Wahlstelle darf Verschiedenes mischen, etwa ein Museum neben einer Wanderung.
- **Plan:** eine feste Auswahl von Optionen über die ganze Reise. Die Beispielreise hat zwei: „Direkt hinunter nach Bad Schandau“ und „Über die Affensteine zur Kirnitzschtalbahn“, jeweils mit Dafür und Dagegen.
- **Wann entschieden wird:** in der Planung (die Regel) oder unterwegs. Der Zugang zum Hockstein in der Beispielreise wird erst unterwegs gewählt; die Wolfsschlucht nur „bei trockenem Fels“.

### Im Gespräch

> „Welche Unterkünfte stehen für die Nacht in Hohnstein zur Wahl?“

Frieda nennt die Optionen mit ihren Merkmalen, was noch fehlt und wer was dafür oder dagegen gesagt hat.

> „Es gibt noch eine Pension in Hohnstein.“

Frieda sieht nach, welche Merkmale die Art braucht, recherchiert zuerst selbst (Website, Buchungsportal), trägt die Werte mit Herkunft ein und fragt nur nach dem, was sie nicht findet. Dann legt sie die Unterkunft an und hängt sie als Option an die Wahlstelle, mit dem Zustand „vorgeschlagen“.

> „Wir nehmen die Pension Burgblick, weil sie direkt am Weg liegt.“

Frieda lässt kurz bestätigen und trägt die Entscheidung mit Datum, Person und Grund ein. Die übrigen offenen Optionen gelten danach als „ersetzt“ (nicht gewählt); die Frage der Wahlstelle ist geklärt, sobald alles entschieden ist.

| Werkzeug | wofür |
|---|---|
| `variants` | Pläne und Wahlstellen mit Dafür, Dagegen und Summen |
| `attributes` | welche Merkmale eine Option braucht und was noch fehlt |
| `choice_create`, `choice_update` | Wahlstelle anlegen oder ändern |
| `option_create`, `option_update` | Option anlegen, ändern oder favorisieren |
| `decide` | Option wählen, verwerfen oder ersetzen |
| `plan_create`, `plan_update` | benannte Pläne anlegen und ändern |

### Auf der Reiseseite

Jede Wahlstelle mit mindestens zwei gültigen Optionen sieht überall gleich aus: an der Nacht, am Weg eines Tags, an einem Ort oder Abschnitt unter „Zur Wahl“. Der Knopf „Alternativen vergleichen“ mit der Zahl der Möglichkeiten öffnet den **Vergleich** an Ort und Stelle.

- **Am Rechner** eine Tabelle, je Möglichkeit eine Zeile. Die Spalten sind die Merkmale der Stufen „nötig“ und „gut zu wissen“; ein Klick auf den Spaltenkopf sortiert, ein Klick auf die Zeile klappt die Einzelheiten auf (Vor- und Nachteile, Verlauf, Kontakt, Quellen).
- **Am Handy** Karten, höchstens zwei nebeneinander, mit Umschalter auf die Tabelle; am Tablet bis zu vier Karten.
- **„nur Unterschiede“** blendet Zeilen aus, in denen alle Möglichkeiten gleich sind.
- Die Möglichkeit, die im Plan steht, kommt zuerst; Verworfene stehen zugeklappt am Ende. Eine Einschätzung in Worten („Was macht es besonders, für wen passt es?“) kann ganz oben stehen, wenn die Reise ein solches Merkmal festlegt.
- An offenen Wahlstellen der Planung steht bei jeder Option „Fehlt noch: …“ für nötige Merkmale ohne Wert; fehlende Werte heißen „offen“, Widersprüchliches „unklar“, ungeprüfte veränderliche Werte „ungeprüft“.

Unter **„Zu tun“** steht „Zu entscheiden“ mit allen offenen Wahlstellen der Planung, darunter „Unterwegs entscheiden“, je Zeile mit der Stelle und dem, was vorläufig gilt. Gibt es mehrere Pläne und ist keiner gewählt, heißt der erste Reiter „Varianten“ und führt zum Vergleich ganzer Pläne; ist ein Plan gewählt, zeigt die Seite nur noch die Reise.

Der Vergleich ist zum Lesen. Entschieden wird im Gespräch; wer nur mitwirkt, schreibt dazu eine Rückmeldung an der Stelle ([Zusammenarbeit](zusammenarbeit.md)).

### Berechnet: Anschluss und Regeln

- **Anschluss:** Bei einem Reiseteil zur Wahl rechnet Frieda aus, ob er an seine Stelle im Plan passt: „nahtlos“ oder „Lücke am Anfang: Altendorf → Bad Schandau“. So sieht man vor der Entscheidung, welche Variante einen fehlenden Weg mitbringt.
- **Regeln zwischen Optionen:** Eine Option kann eine andere voraussetzen („der Bus fährt nur, wenn das Gepäck in der Pension Burgblick bleibt“) oder ausschließen. Verletzt der Plan eine Regel, steht das unter „Geht noch nicht auf“. Verhindert wird nichts; Frieda weist beim Entscheiden darauf hin.

## Wer darf was

| Rolle | darf |
|---|---|
| Gast | Wahlstellen, Optionen und den Vergleich lesen |
| Mitwirkende:r | Wahlstellen und Optionen anlegen, Werte eintragen, Optionen favorisieren (mit Grund), Rückmeldungen geben |
| Organisator:in | dazu entscheiden (wählen, verwerfen, ersetzen), Wahlstellen ändern, Pläne anlegen und ändern, den Plan eines Tags ändern |

Frieda selbst schlägt vor, prüft und kann eine Option mit Begründung favorisieren, entscheidet aber nie.

## Regeln und Grenzen

- Jede Entscheidung hat genau eine Person, ein Datum und einen Grund. Ohne Grund lehnt Frieda ab, ebenso eine Option, die es nicht gibt, oder eine Entscheidung, die schon so vorliegt.
- **Konflikt:** Entscheidet eine zweite Organisator:in an derselben Stelle anders, überschreibt sie nicht die erste. Frieda schreibt dann nichts in den Plan, legt eine offene Frage mit beiden Positionen an und meldet das allen Beteiligten.
- Wird die gewählte Option später verworfen, sind die übrigen wieder „vorgeschlagen“, und die Frage der Wahlstelle ist wieder offen.
- Nichts wird gelöscht: Eine Option, die niemand mehr will, wird verworfen und lässt sich mit einer neuen Wahl zurückholen.
- Der Kalender zeigt nur Entschiedenes; Tage und Nächte unter einer offenen Wahlstelle der Planung fehlen dort.
- Ab Status „fest“ ist jede offene Wahlstelle der Planung eine Mahnung im Überblick des Gesprächs. In der Nachlese und im Archiv gibt es keine neuen Optionen und keine Entscheidungen mehr.
- Die Werkzeuge für Alternativen und Entscheidungen gibt es nur, wenn der Baustein `varianten` eingeschaltet ist.

## Siehe auch

- [Reisemodell](reisemodell.md) (Arten, Merkmale, Stufen), [Buchungen](buchungen.md), [Reiseseite](reiseseite.md), [Zusammenarbeit](zusammenarbeit.md)
- [Alternativen: Standard für Wahlstellen, Optionen und Merkmale](../alternativen.md)
- [Konnektor](../konnektor.md) (`decide` und alle Werkzeuge), [Design](../design.md) (Seitenordnung, Vergleich)
