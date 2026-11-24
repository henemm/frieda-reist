# Karte

Frieda zeichnet die Karte der Reise selbst, aus allem, was Koordinaten hat. Niemand muss eine Karte von Hand pflegen: Sobald Orte, Unterkünfte und Aufenthalte ihre Lage haben, stehen sie auf der Karte, und unterwegs funktioniert sie auch ohne Netz.

**Auf einen Blick:** Wo: Gespräch · Reiseseite · Wer: alle lesen; Lage und Tracks ab Mitwirkende:r; Kartenansichten und Punkte aus OpenStreetMap Organisator:innen · Baustein: `karte`

## Was du damit tun kannst

- Die ganze Reise auf einer Karte sehen, mit Legende nach den Arten der Reise (etwa Hotel, Pension, Zugfahrt).
- Je Tag einen Kartenausschnitt mit den Strecken und Punkten dieses Tags sehen.
- Einen Track (GPX-Datei) an eine Strecke hängen, damit die Karte den echten Weg zeigt statt einer gestrichelten Linie.
- Eigene Kartenansichten anlegen, etwa „nur die Wandertage“ oder „alle Einkehrmöglichkeiten“.
- Punkte entlang einer Strecke aus OpenStreetMap holen lassen: Wasserstellen, Einkehr, Haltestellen.
- Unterwegs ohne Netz auf der Offline-Grundkarte nachsehen.
- Von jeder Unterkunft und jedem Aufenthalt mit einem Tipp zu Google Maps (auf Apple-Geräten auch zu Apple Karten) springen.

## So geht's

### Im Gespräch

> „Schalte die Karte für die Reise ein.“

Frieda schaltet den Baustein ein und sagt dir, ob die Karte schon gebaut werden kann und welche Einträge noch keine Koordinaten haben.

> „Trag für die Pension Burgblick in Hohnstein Adresse und Koordinaten ein.“

Claude recherchiert die Lage, nennt die Quelle und trägt sie nach deiner Bestätigung ein. Die Lage ist eine Angabe wie jede andere: mit Herkunft und Prüfdatum.

> „Hier ist der GPX-Track der Etappe von Stadt Wehlen nach Hohnstein, häng ihn an.“

> „Hol mir die Trinkwasserstellen entlang der Etappe Altendorf – Schrammsteine – Bad Schandau, bis 300 Meter vom Weg.“

Frieda legt jeden Treffer als eigenes Ding an, mit Koordinaten, Quelle und Stand der Daten. Fragst du später noch einmal, werden dieselben Dinge aktualisiert, nichts wird gelöscht. Die Abfrage kann bis etwa eine Minute dauern.

| Werkzeug | wofür |
|---|---|
| `setting_set` | Baustein `karte` ein- oder ausschalten |
| `item_create`, `item_update` | Koordinaten und Adresse eintragen; mit `gpx` einen Track an eine Strecke hängen |
| `map_view_set` | Kartenansicht anlegen, ersetzen oder entfernen (Tage, Strecken, Arten, Übersicht unter der Karte) |
| `map_points_fetch` | Punkte aus OpenStreetMap entlang einer Strecke als Dinge anlegen |
| `kind_define` | eine Art für Kartenpunkte anlegen (etwa „Wasserstelle“), bevor Punkte geholt werden |
| `overview` | Kartenstatus: gebaut oder nicht, Grund, Zahl der Punkte, Einträge ohne Koordinaten |

### Auf der Reiseseite

- **Im Reiseüberblick** steht die Karte unter der Anreise. „Karte vergrößern“ bringt sie auf Fenstergröße, Schließen mit dem Knopf oder der Esc-Taste. Tippst du einen Ort an, erscheint darunter ein Kasten mit ihm. Fährst du über einen Tag der Zeitachse, hebt die Karte ihn hervor.
- **Auf der Tagesseite** steht der Ausschnitt des Tags neben oder unter dem Tageskasten. Strecken ohne Track sind gestrichelt.
- **Kartenansichten** wählst du an der Karte des Überblicks. Hat eine Ansicht eine Übersicht je Art, steht darunter eine Tabelle aller Dinge dieser Arten; jede Zeile führt zum Ding.
- **Kartenpunkte** (Punkte aus OpenStreetMap oder der Recherche) stehen auf der Karte der Etappe und an ihrer Strecke als „Punkte am Weg“. Ein Tipp auf eine Zeile zeigt den Punkt auf der Karte.
- **Kartenlinks** stehen bei der Lage jeder Unterkunft und jedes Aufenthalts.

**Was auf der Karte erscheint.** Orte des Plans, Unterkünfte und Aufenthalte mit Koordinaten. Name, Farbe und Symbol eines Punkts kommen aus seiner Art. Unterkünfte und Aufenthalte, die nur in einer noch offenen Möglichkeit stehen, erscheinen als Umriss. Bei der Beispielreise „Malerweg in vier Tagen“ sind das etwa Dresden, Hohnstein, Altendorf und Bad Schandau mit den Unterkünften dazwischen und den Tracks der vier Etappen.

## Wer darf was

| Rolle | darf |
|---|---|
| Gast | Karte und Ansichten ansehen |
| Mitwirkende:r | dazu Koordinaten und Adressen eintragen, Tracks anhängen |
| Organisator:in | dazu Baustein ein- und ausschalten, Kartenansichten setzen, Punkte aus OpenStreetMap holen, Arten anlegen |

## Regeln und Grenzen

- Die Karte braucht den Baustein `karte` und mindestens zwei Punkte mit Koordinaten. Ein Ort (eine Stadt, ein Dorf) hat Koordinaten, aber keine Adresse; eine Unterkunft hat eine Adresse, Koordinaten oder beides.
- Koordinaten recherchiert Claude im Gespräch. Frieda selbst sucht keine Adressen und rät keine Lage; was ohne Quelle ist, wird nicht eingetragen.
- Ein Track ist eine GPX-Datei als Text, höchstens etwa 60 000 Zeichen.
- Punkte aus OpenStreetMap brauchen eine Art der Reise für Kartenpunkte. Fehlt sie, lehnt Frieda ab und sagt, welche Art zuerst anzulegen ist.
- Ab Status „fest“ mahnt Frieda im Gespräch Unterkünfte im Plan ohne Lage an. Der Wächter meldet Koordinaten und Adressen mit altem Prüfdatum wie jede veränderliche Angabe.
- Die Offline-Grundkarte holt der Server beim Veröffentlichen selbst, sobald sich der Rahmen der Karte geändert hat. Sie ist einige 10 MB groß und wird beim Installieren oder beim nächsten Update der Seite ganz geladen, am besten im WLAN.
- Ein Fehler in den Kartendaten lässt die Seite nicht ausfallen: Sie erscheint ohne Karte, und der Kartenstatus im Gespräch nennt den Grund.
- Einen eigenen Reiter „Karte“ gibt es nicht; die Karte gehört zur Reise.

## Siehe auch

- [Reiseseite](reiseseite.md), [Reisemodell](reisemodell.md), [Planen im Gespräch](gespraech.md), [Alternativen](alternativen.md), [Erinnerungen](erinnerungen.md)
- Referenz: [Konnektor: Karte aus dem Plan](../konnektor.md#karte-aus-dem-plan-epic-225-2112026), [Ontologie: Karte](../ontologie.md#karte-epic-225-2112026), [Ontologie: Kartenpunkte](../ontologie.md#kartenpunkte-sind-dinge-kategorien-sind-arten-adr-0007-schritt-d-285), [ADR-0004: Lage eines Aufenthalts](../adr/0004-lage.md), [Werkzeuge: Offline-Grundkarte](../werkzeuge.md#offline-grundkarte-pmtiles)
