# Packliste

Die Packliste hält fest, was auf die Reise mitkommt: in Kategorien, mit Merkmalen wie Gewicht oder Raum, mit der Person, die etwas packt, und mit Haken für das, was schon im Rucksack ist. Sie entsteht im Gespräch und gehört zur Reise wie Plan und Buchungen; abgehakt wird auf der Reiseseite, auch ohne Netz.

**Auf einen Blick:** Wo: Gespräch · Reiseseite · Wer: alle lesen; Mitwirkende legen an und haken ab; Organisator:innen ändern alles · Baustein: `packliste`

## Was du damit tun kannst

- Eine Packliste im Gespräch aufbauen, aus einem Vorschlag von Claude („mach eine Liste für eine Hüttentour“) oder aus einer früheren eigenen Reise.
- Gegenstände in **Kategorien** ordnen, die deine Reise selbst festlegt (Kleidung, Ausrüstung, Apotheke …).
- Je Kategorie **Merkmale** führen, etwa Gewicht, Anzahl, Anschaffungspreis oder wo etwas zu Hause liegt.
- Summen sehen, je Kategorie und für die ganze Liste, zum Beispiel das Gesamtgewicht.
- Festlegen, wer einen Gegenstand packt; Gegenstände ohne Zuständige packt jede Person für sich.
- Einen Gegenstand an eine Strecke, eine Unterkunft, einen Aufenthalt oder einen Ort hängen, etwa „Wanderstöcke für die Etappe zur Bastei“.
- Beim Packen abhaken, nach Kategorie oder nach Raum sortiert, auch ohne Netz.
- Etwas weglassen, ohne es zu löschen, und es später zurückholen.

## So geht's

### Kategorien und Merkmale

Frieda führt kein Inventar und belegt nichts vor. Die Kategorien sind Arten der Reise ([Reisemodell](reisemodell.md)), ihre Merkmale legt die Reise fest wie bei jeder Art. Ein Merkmal, das summiert werden soll, bekommt diese Rolle; eine Kategorie darf mehrere davon haben.

Die beiden Beispielreisen zeigen, wie verschieden das aussehen kann:

- **Malerweg in vier Tagen:** Kleidung, Ausrüstung und Apotheke, mit den Merkmalen Gewicht (in Gramm, summiert), Getragen (am Körper, Tagesrucksack, Rucksack), Raum (Flur, Schlafzimmer, Bad, Küche, Keller) und bei der Ausrüstung Anschaffung (summiert). Die Wanderstöcke hängen an der ersten Etappe, die Stirnlampe an der Wanderherberge Altendorf und wird von Karl gepackt, das Erste-Hilfe-Set trägt Ida für alle. Die Sonnencreme ist weggelassen („Karl hat eigene dabei“). Die Kategorie Fotoausrüstung ist für diese Reise ausgeblendet.
- **Stadtwochenende:** nur Papiere und Kleidung, ohne Gewicht und Raum. Die Fahrkarte hängt an der Hinfahrt, den Personalausweis packt Lea.

### Im Gespräch

> „Mach uns eine Packliste für den Malerweg, wir übernachten in Pensionen.“

Claude schlägt Kategorien und Gegenstände vor; Frieda legt sie nach deiner Bestätigung an.

> „Nimm die Packliste von unserer letzten Wanderreise.“

Frieda kopiert Kategorien und Gegenstände als Vorschlag. Danach streicht und ergänzt ihr im Gespräch.

> „Wie schwer ist alles zusammen, und was muss ich noch einpacken?“

Frieda nennt die Summen und die Gegenstände, die für dich noch nicht abgehakt sind.

| Werkzeug | wofür |
|---|---|
| `packing_list` | die Packliste mit Summen und Packstand lesen |
| `gear_create` | einen Gegenstand auf die Liste setzen |
| `gear_update` | Gegenstand ändern, weglassen oder zurückholen |
| `gear_pack` | für dich abhaken oder den Haken zurücknehmen |
| `packing_list_adopt` | Packliste einer früheren Reise als Vorschlag übernehmen |
| `kind_define`, `attribute_define` | Kategorie und Merkmale anlegen, Kategorie aus- oder einblenden |

### Auf der Reiseseite

Die Packliste hat einen eigenen Reiter „Packliste“ mit zwei Ansichten:

- **Planen:** je Kategorie eine Tabelle mit den Merkmalen als Spalten, darunter die Summen, oben die Summe der ganzen Liste. Jede Spalte lässt sich sortieren. Die Gesamtsumme kann nach einem Auswahl-Merkmal aufgeteilt werden, etwa nach „Getragen“: wie viel am Körper, im Tagesrucksack und im großen Rucksack steckt.
- **Packen:** die Gegenstände mit Haken, gruppiert nach Kategorie oder einem Merkmal der Reise, zum Beispiel nach Raum, damit du beim Packen einmal durch die Wohnung gehst. „Nur meins“ zeigt deine Gegenstände und die, die jede Person für sich packt; „Alle“ zeigt die ganze Liste. Mit „Für mich zeigen“ blendest du auf deinem Gerät Kategorien aus. Nicht gepackte Gegenstände stehen oben, gepackte rutschen nach unten.

Abhaken geht auch ohne Netz: Die Seite merkt sich den Haken und reicht ihn nach, sobald wieder Netz da ist. An der Strecke, der Unterkunft, dem Aufenthalt oder dem Ort, an dem ein Gegenstand hängt, steht die Zeile „Mitnehmen“ mit einem Link zur Packliste.

## Wer darf was

| Rolle | darf |
|---|---|
| Gast | die Packliste lesen |
| Mitwirkende:r | Gegenstände anlegen, eigene ändern (selbst angelegt oder ihr:ihm zugewiesen), abhaken |
| Organisator:in | alle Gegenstände ändern, Kategorien und Merkmale festlegen, Packlisten früherer Reisen übernehmen |

Einen Gegenstand mit Zuständiger:m hakt nur diese Person ab; einen ohne hakt jede Person für sich ab.

## Regeln und Grenzen

- Ein Gegenstand braucht keine Herkunft; eine Regenjacke ist keine Behauptung über die Welt. Ein veränderliches Merkmal, etwa ein Preis, behält sein Prüfdatum.
- Nichts wird gelöscht. Weglassen heißt „entfällt“, mit Grund im Verlauf; zurückholen geht jederzeit. Weggelassene Gegenstände zählen nicht in den Summen.
- Ein Wert gilt für den ganzen Eintrag: „Wandersocken, 3 Stück, 240 g“ wiegt 240 g, nicht dreimal so viel.
- Ein Gegenstand hängt nie an einem Tag; was ein Tag braucht, ergibt sich aus seinen Strecken, Aufenthalten und Unterkünften. Hängt ein Gegenstand nur an einer verworfenen Möglichkeit, steht er gedämpft mit Hinweis da.
- Eine ausgeblendete Kategorie fehlt in Planen, Packen, Summen und „Mitnehmen“, bleibt aber erhalten und lässt sich wieder einblenden.
- Übernehmen aus einer früheren Reise bringt Kategorien und Gegenstände mit neuen Kennungen, aber ohne Haken, ohne Zuständige und ohne Bezug zu Strecken oder Unterkünften der alten Reise. Werte von Merkmalen, die eine schon vorhandene Kategorie nicht kennt, entfallen; Frieda nennt sie.
- Der Packstand ist live und persönlich: Er erscheint nur angemeldet, zählt nicht im Verlauf der Reise und ändert den Reise-Stand nicht.
- Die Packliste ist in jedem Status schreibbar, auch unterwegs (Nachkaufen vor Ort) und in der Nachlese, nur im Archiv nicht mehr. Ohne den Baustein `packliste` gibt es weder den Reiter noch die Werkzeuge.

## Siehe auch

- [Reisemodell](reisemodell.md) (Arten und Merkmale), [Reiseseite](reiseseite.md), [Zusammenarbeit](zusammenarbeit.md)
- [ADR-0010: Der Gegenstand](../adr/0010-gegenstand.md), [Reise-Ontologie](../ontologie.md) (Abschnitt Packliste)
- [Konnektor](../konnektor.md) (`gear_create`, `packing_list_adopt`), [Design](../design.md) (Packliste)
