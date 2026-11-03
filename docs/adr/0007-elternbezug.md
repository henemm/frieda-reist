# ADR-0007: Ein Elternbezug je Ding, typisierte Merkmale statt Sonderfelder, Kartenpunkte sind Dinge

Status: **Entwurf** · zur Entscheidung des Product Owners · Anlass: frieda-reist #235, #236, #275 und die Frage des Product Owners vom 3.11.2026, ob die wachsende Zahl der Parameter des Konnektors der richtige Weg ist · Issue: frieda-reist #280

Steht unter [ADR-0001](0001-kern.md) (Grundformen in der Software, Arten in der Reise) und ändert [ADR-0003](0003-heimat.md) (die Heimat wird berechnet statt tabelliert) und [ADR-0004](0004-lage.md) (die Lage wird ein Merkmal-Typ). ADR-0002 bleibt unverändert; die Dichte-Achse wird nur konsequent angewandt.

## Kontext

Der Product Owner hat am 3.11.2026 gefragt, ob #235 (Aufenthalte ohne Tag) und #275 (Übersicht der Aufenthalte einer Art im Wissen) der richtige Weg sind. Sein Bild: Es müsste an jeder Stelle möglich sein, ein Kind-Objekt zu erzeugen, das beliebige Eigenschaften trägt, dazu feste Eigenschaften wie Adresse oder GPX-Koordinaten, die die Seite auf eine bestimmte Weise zeigt; und aus der Hierarchie dieser Objekte sollte sich die Darstellung nach Atomic Design ergeben.

Befund (Cloud-Sitzung 3.11.2026, gelesen gegen `engine/konnektor.py`, `engine/schreiben.py`, `engine/routen.py`, `engine/vorlage.html`, `docs/ontologie.md`, `docs/design.md`):

| Größe | Wert |
|---|---|
| Werkzeuge des Konnektors | 61 |
| verschiedene Parameternamen | 105 |
| Parameter von `item_create` | 18 |

1. **Eigenschaften sind schon generisch.** Arten und Merkmale kommen aus der Reise (`plan/arten.yaml`), ein Wert hat Typ, Herkunft, Prüfdatum und Gültigkeit, der Typ bestimmt die Darstellung (`link` wird Link nach außen, `geld` mit `rolle: kosten` wird summiert). Das ist der Teil des Bilds, der steht.
2. **Die Struktur ist es nicht.** `plan/routen.yaml` hat vier Behälter mit je eigenen festen Feldern: Ort (`ausserhalb`), Unterkunft (`ort`, `buchungslink`), Aufenthalt (`ort`, `zeit`, `beginn`, `ende`), Strecke (`von`, `nach`, `ab`, `an`); dazu Lage als `adresse` und `punkt`. Jedes dieser Felder ist ein Parameter von `item_create` und `item_update`, Lage noch einmal in `location_set`. Die Felder sind typisierte Eigenschaften der Grundform, gebaut als Sonderfälle: In der Beispielreise ist „Webseite“ ein Merkmal vom Typ `link`, der Buchungslink daneben ein festes Feld.
3. **Wo ein Ding hängt, ist je Grundform fest.** Aufenthalt am Tag, Unterkunft an der Nacht, Wissen am Reiter. Nur die Wahlstelle hat den generischen Mechanismus: `an:` hängt sie an Tag, Strecke, Unterkunft, Ort, Wahlstelle oder Wissensabschnitt, und die Heimat folgt daraus (ADR-0003, Punkt 5). Jede andere Grundform bekommt bei neuem Platzbedarf eine neue Regel: #235 hat eine dritte Heimat für Aufenthalte eingeführt (unter der Karte, ohne Karte-Baustein im Reiseüberblick), obwohl die Ortsseite als Heimat da wäre. #275 verlangt, dass Wissen Aufenthalte kennt. #236 wählt Punkte und Strecken je Ansicht nach Tagen und Arten aus.
4. **Zwei Taxonomien für dieselbe Frage.** „Was für ein Ding ist das?“ beantwortet die Reise einmal in `arten.yaml` (Art mit Farbe, Symbol, Merkmalen, Buchbarkeit) und einmal in `kategorien.yaml` (Kategorie mit Farbe, Symbol, Gruppe, nummeriert, Umriss). Ein Kartenpunkt (`plan/punkte.yaml`, `inhalt/wissen-punkte.yaml`) hat keine ID, keine Merkmale, keine Herkunftsform je Wert und ist nicht verweisbar. Ein Supermarkt ist entweder ein Punkt oder ein Aufenthalt; als Aufenthalt brauchte er bis #235 einen Tag und kann bis #275 nicht ins Wissen. #275 beschreibt wörtlich diese Folge: 26 Orte stehen als Aufenthalte und ein zweites Mal als Text.
5. **Die Darstellung nach Hierarchie gibt es schon, als Tabelle.** `GRUNDFORMEN` in `engine/vorlage.html` ordnet jeder Grundform Bausteine je Dichte zu (Zeile, Vorschau, Karte, Seite). Die Dichte wird heute je Ansicht von Hand gewählt; `heimat()` ist eine Fallunterscheidung über die Grundformen.

Für den AI-Client ist das die schwierigere Schnittstelle: 61 Werkzeuge mit 105 Namen kosten bei jedem Gespräch Kontext, und jeder Sonderfall ist eine Stelle, an der ein Aufruf scheitert.

## Entscheidung (Vorschlag)

1. **Jedes Ding hat einen Elternbezug `an:`.** Wie heute die Wahlstelle: Ein Ding hängt an genau einem anderen Ding (Tag, Ort, Strecke, Aufenthalt, Unterkunft, Wissensabschnitt, Reise). Vorgabe nach Grundform, damit nichts Bestehendes bricht: Nacht und Strecke am Tag, Aufenthalt mit Tag am Tag, Aufenthalt ohne Tag an seinem Ort, Buchung an ihrem ersten Ding, Wahlstelle wie bisher. Die Felder `ort`, `tage`, `naechte`, `fuer` bleiben als Daten (sie tragen Bedeutung: Gegend, Zeit, Nacht, gebuchte Dinge); `an:` sagt nur, wo das Ding zu Hause ist.
2. **Die Heimat wird berechnet, nicht tabelliert.** Heimat = die Seite des Elternelements; bei mehreren Tagen der erste im Plan. Die Dichte folgt dem Abstand: auf der eigenen Seite vollständig (Seite), auf der Seite des Elternelements als Karte, überall sonst als Zeile mit einem Link (ADR-0003, Punkt 1 bleibt). `heimat()` in der Vorlage wird eine Regel statt einer Fallunterscheidung. Die Tabelle in ADR-0003 beschreibt dann die Vorgaben, nicht mehr die einzige Möglichkeit.
3. **Typisierte Merkmale der Grundform statt Sonderfelder.** Die Form eines Merkmals (`docs/ontologie.md`) bekommt weitere Typen, die die Software kennt und mit einem festen Baustein zeigt: `adresse` (Postadresse, `lageZeile`, `kartenLinks`), `koordinaten` (Punkt auf der Karte), `gpx` (Track, Datei unter `medien/`), `uhrzeit` (Ortszeit `HH:MM`), `zeitpunkt` (mit Datum und Zeitzone), `zeitraum` (Beginn und Ende), `link`, `geld`, `zahl`, `text`, `auswahl`. Welche Merkmale eine **Grundform** fest trägt, sagt die Software (Aufenthalt: Lage als `adresse` oder `koordinaten`, Zeitraum; Bewegung: Abfahrt und Ankunft als `zeitpunkt`, Track als `gpx`; Ort: `koordinaten`, `ausserhalb`); das ist kein Katalog (ADR-0001, Frage 2), sondern die Form der Grundform, wie heute `rolle: kosten`. Welche Merkmale eine **Art** trägt, sagt weiter die Reise. Die festen Felder `adresse`, `punkt`, `beginn`, `ende`, `ab`, `an` (Zeit), `buchungslink`, `gpx` werden beim Lesen auf die Merkmale abgebildet und beim Nachziehen (`neu.py nachziehen`) in `merkmale:` überführt; die Regeln der Software (Mahnung ab `fest` ohne Lage, Anschlussprüfung, Kalender, Karte) lesen den Typ und die Rolle, nie den Namen.
4. **Kartenpunkte sind Dinge, Kategorien gehen in den Arten auf.** Ein Punkt aus `plan/punkte.yaml` oder `inhalt/wissen-punkte.yaml` wird ein Aufenthalt (`A-…`) oder Ort (`O-…`) mit Art, ID, Herkunft und `an:` (an der Strecke, an der er liegt, oder am Wissensabschnitt). Die Felder einer Kategorie, die eine Art nicht hat (`gruppe`, `einzahl`, `nummeriert`, `umriss`, Zusatz je `art`-Wort), ziehen in die Art. `kategorien.yaml` und `category_define` entfallen; die Legende der Karte und die Kartenansichten (#236) wählen nach Arten. Bestehende Punkte überführt `neu.py nachziehen` mit neuen IDs (nie neu vergeben, ADR-0001 Punkt 7); OSM-Bezug, Quelle und Prüfdatum bleiben am Ding.
5. **Der Konnektor schrumpft auf die Form.** `item_create` nimmt: `was` (Grundform), `art`, `an`, `titel`, `quelle`, `merkmale` (mit den typisierten Merkmalen der Grundform darin), `hinweis`. `item_update` ändert Felder und Merkmale und setzt `an` um (Aufenthalt vom Sammeltag lösen, #235). `location_set`, `value_set`, `track_attach` und `category_define` gehen darin auf; die deutschen und englischen Namen bleiben als Aliase, damit laufende Gespräche nicht brechen (ADR-0006, Punkt 4). `map_points_fetch` legt Dinge an statt Punkte.
6. **Übersichten je Art sind ein Baustein, keine Daten.** Eine Liste aller Dinge einer Art mit ihren Merkmalen (#275) ist der vorhandene Vergleich (`wahlVergleich`) ohne Entscheidung, als Organismus `artUebersicht` an jeder Stelle, an der etwas hängt. Sie steht da, wo ein Wissensabschnitt oder eine Kartenansicht sie über `an:` oder die Auswahl nach Arten anfordert. Es gibt kein neues Markdown-Kommando und keine Kopie der Werte im Text.

**Nicht entschieden wird:** ein rein generischer Baum, in dem alles ein beliebiger Knoten ist. Tag, Bewegung, Nacht, Wahl und Buchung haben Rechenbedeutung: Der Generator zählt Nächte, summiert Gehzeiten und Kosten, prüft Anschlüsse, baut Kalender und Karte, prüft Entscheidungen und Fristen. Die neun Grundformen bleiben. Generisch wird, **wo** ein Ding hängt und **welche Eigenschaften** es trägt, nicht **was** es ist. Die Grundform wählt den Baustein, die Hierarchie wählt die Dichte.

## Begründung

- **Der Kern verlangt es.** ADR-0001 sagt: Die Software kennt nur Grundformen und die Form eines Merkmals. Feste Felder je Behälter und eine zweite Taxonomie für Kartenpunkte sind Form außerhalb dieser Regel. Mit typisierten Merkmalen und einem Elternbezug gilt die Regel auch für die Struktur.
- **AI first.** Ein Sprachmodell füllt eine Merkmal-Karte sicherer als 18 Parameter mit Sonderbedeutung je Grundform; weniger Werkzeuge mit gleicher Form kosten weniger Kontext und erzeugen weniger Ablehnungen.
- **Eine Heimat als Regel statt Tabelle.** Jeder neue Platzbedarf (#235, #275, #236) ist heute eine neue Heimat mit eigener Fallunterscheidung. Mit `an:` ist er ein Datum in der Reise.
- **Ein Ding, ein Gesicht.** Ein Supermarkt sieht auf der Karte, im Wissen und am Tag gleich aus, weil er dasselbe Ding ist (ADR-0002, Regel 1). Heute ist er zweimal da: als Punkt und als Aufenthalt.
- **Was nicht generisch wird, hat einen Grund.** Alles mit Rechenbedeutung bleibt Grundform; so geht nichts verloren, was Kalender, Karte, Wächter und Vergleich heute können.

## Konsequenzen

- **Datenformat:** `an:` an jedem Ding (Vorgabe beim Lesen, geschrieben nur, wenn es von der Vorgabe abweicht); typisierte Merkmale in `merkmale:` statt fester Felder; `plan/punkte.yaml`, `inhalt/wissen-punkte.yaml`, `plan/kategorien.yaml` werden überführt. `neu.py nachziehen` stellt jede Reise im selben Commit um (CLAUDE.md, #250); die alten Schlüssel werden weiter gelesen, nie mehr geschrieben.
- **Generator und Vorlage:** `heimat()` als Regel; `GRUNDFORMEN` bleibt, die Dichte folgt dem Abstand; neuer Organismus `artUebersicht` (vier Stellen, ADR-0002); Legende und Kartenansichten nach Arten; Bausteine für die Typen `koordinaten`, `gpx`, `zeitraum`, soweit sie fehlen.
- **Konnektor und Schreibweg:** `item_create` und `item_update` mit `an` und typisierten Merkmalen; `location_set`, `value_set`, `track_attach`, `category_define` als Aliase; Regeln lesen Typ und Rolle. Schätzung: sechs Werkzeuge werden drei, die Sonderparameter entfallen.
- **Issues:** #235 bleibt als Zwischenstand, die Heimat wandert zum Ort; #275 wird `artUebersicht` an einem Wissensabschnitt; #236 wählt nach Arten und braucht keine Kategorien.
- **Prüfstelle ADR-0001:** 1 ja (Elternbezug und Typen sind Form, mit Wanderung und Städtewochenende durchzuspielen), 2 ja (kein Merkmalname in der Software, nur Typ und Rolle), 3 ja, 4 ja (`item_create`, `item_update`), 5 ja (jedes typisierte Merkmal ist eine Aussage mit Herkunft), 6 nicht berührt, 7 ja (Punkte bekommen neue IDs, alte Schlüssel bleiben lesbar), 8 Rundgang nötig, 9 ja, 10 dieses ADR, `docs/ontologie.md`, `docs/design.md`, `docs/konnektor.md`, ADR-0003 und ADR-0004 mit Verweis hierher.
- **Reihenfolge, wenn entschieden:** (a) `an:` lesen und Heimat berechnen, Aufenthalt ohne Tag zum Ort; (b) typisierte Merkmale lesen, alte Felder abbilden; (c) Konnektor auf die neue Form, Aliase; (d) Punkte und Kategorien überführen; (e) `artUebersicht`; je Schritt ein PR mit Nachziehen und Instanz-Tests.

## Offene Fragen an den Product Owner

1. Darf ein Ding an **mehreren** Eltern hängen (ein Aufenthalt an zwei Tagen, ein Punkt an zwei Strecken)? Vorschlag: nein, ein Elternbezug; weitere Bezüge sind Daten (`tage`), und dort steht das Ding als Zeile.
2. Sollen die Kartenkategorien wirklich entfallen, oder bleibt eine Kategorie als Art ohne Merkmale erlaubt? Vorschlag: entfallen, eine Art darf leer sein.
3. Ist eine **Übersicht je Art** auch ohne Wissensabschnitt gewünscht (etwa als eigener Reiter), oder nur dort, wo sie angefordert wird? Vorschlag: nur angefordert (ADR-0003, Punkt 2: Sammelansichten nur mit eigener Aufgabe).

## Verlauf

- 3.11.2026: Entwurf nach der Frage des Product Owners (Cloud-Sitzung). Die Analyse hat er gelesen und den Entwurf angefordert; entschieden ist noch nichts.
