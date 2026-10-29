# Design: Grundregeln und Bausteine

Die Seite folgt einem Designsystem (Issue #18): wenige Bausteine, die jede Ansicht zusammensetzt, statt dass jede Ansicht dieselbe Sache selbst zeichnet. So bekommt eine neue Art von Alternative (Fähre, Restaurant, Flug) kein neues Design, sondern bringt nur ihre Merkmale mit. Seit dem 27.10.2026 gilt das Gesicht **„Freundlich“ (B2)**, erarbeitet an echten Seiten (frieda-reist#52).

## Aufbau: Atomic Design und drei Achsen

Die Ebenen folgen Brad Frosts Atomic Design; festgelegt in [ADR-0002](adr/0002-atomic-design.md) (mit der Pflicht, neue Bausteine an vier Stellen einzutragen). Skript und Stile in `engine/vorlage.html` sind gleich geordnet: Der Stilblock beginnt mit den Tokens, dann Grundlagen (Seite, Text, Pico CSS, Reisetexte), Atome, Moleküle, Organismen, Vorlagen, der Rahmen der Seite (Kopf, Meldungen, Glas, Leiste) und zuletzt die Breiten. Jede Regel steht bei dem Baustein, zu dem sie gehört; was ein Baustein in einem anderen anders macht, steht beim umfassenden.

| Ebene | Bausteine in `engine/vorlage.html` |
|---|---|
| Tokens | Farben (`--bg`, `--card`, `--fg`, `--mut`, `--line`, `--acc`, `--acc2`, `--warn`, `--warnbg`, `--ocker`, `--kat-*`, `--plan-*`), Schrift (`--font-text`), Formen (`--r-klein`, `--r`, `--r-kachel`, `--r-gross`, `--r-pille`, `--schatten`, `--schatten-klein`), Breiten (`--breite`, `--lese`) |
| Atome | `symbol` (Lucide), `chip` (Zustand), Etikett (`.etikett`, sagt, was etwas ist), `merkmalWert` (Wert mit Herkunft), `zid` (Kennung als Sprechblase), `planMarke` (Farbe eines Plans als Punkt oder Linie), `webLink` (Webseite nach außen, „Webseite ↗“, aus Buchungslink oder Kontakt), `kartenLinks` (Lage zu Google Maps, auf Apple-Geräten auch Apple Karten; ADR-0004) |
| Moleküle | Fläche (`.karte`, `.karte.flaeche`, `details.block`), `kennzahlLeiste` (Kacheln), `merkmalListe`, `reiseText` (Reisetext, Merkmallisten ohne doppelte Kennzahlen), `reiterGruppe` (Reiter als Pillen), `ebeneKopf`, `kapitel` (zuklappbarer Abschnitt mit Vorschau), `dingEtikett`, `listenZeile` (Wissen, Praxis, Quellen, Orte, Listen in „Zu tun“; rechts Kennung oder Zustand), `zeilenKarte` (offene Frage), `rmEintrag` (Rückmeldung, Wunsch), `agEintrag` (Aufgabe), `eintragGruppen` („Titel (n)“ mit Einträgen), `kartenLegende`, `umschalter` (ein Knopf gedrückt, z. B. `planUmschalter`), `kontoKnopf`, `nameFeld`, `fehltZeile`, `optionChips`, `standLeiste` (Stand der Vorbereitung), `lageZeile` (Adresse oder Koordinaten mit Herkunft und Kartenlinks), `reiseEnde` (An- oder Abreise), `mitreisende`, `buchungChip` (Stand einer Buchung mit Link zu ihr), `belegeListe` (Belege einer Buchung mit Formular zum Anhängen) |
| Organismen | Ding: `nachtZeile` (Aufenthalt mit Nacht als Zeile), `unterkunftKarte` (als Karte), `aufenthaltZeile` (Aufenthalt ohne Nacht), `streckeZeile` (Bewegung); `buchungBlock` (Buchung am Ding, ihre Heimat); Wahl-Modul: `wahlEinstieg`, `wahlVergleich`, `wahlKarte`; Tageskasten: `tagKarte` mit `wegVerlauf`; Tagesseite: `tagEbenen`, `tagOrteZeilen`; Tag als Zeile der Zeitachse: `tagZeile`; Nacht der Tagesseite: `nachtAbschnitt`; Sammellisten „Zu tun“: `zuEntscheiden`, `zuBuchen` (aus `listenZeile`); `uebersichtKarte` (Karte der Reise oder der Pläne mit Legende) |
| Vorlagen | `tagKachel`, die Ansichten (`ansichtTag` = Tagesseite, `ansichtReise` = Reiseüberblick, `ansichtOffen` = Zu tun, `ansichtWissen`, `ansichtPlan` …) mit ihren Rastern |

## Ontologie und Bausteine (28.10.2026)

Die Bausteine sind auf die Grundformen der Reise-Ontologie abgebildet (ADR-0001, `docs/ontologie.md`): Jede Grundform (an ihrer Kennung erkennbar) hat ihre festen Bausteine je Dichte. Welche Arten eine Reise hat (Hotel, Refugi, Bahn, Museum …), weiß nur sie (`plan/arten.yaml`); eine Art bekommt keinen Baustein, sondern bringt Name, Farbe und Symbol mit (seit Paket O-5; vorher kannte die Vorlage Verkehrsmittel als `ART_TEXT`). Im Code steht die Zuordnung als `GRUNDFORMEN` in `engine/vorlage.html`; die Bausteinseite zeigt sie als Tabelle, und `test_seite.py` prüft, dass jede Kennung der Beispielreise einer Grundform angehört (`grundformVon`).

| Grundform | Kennung | Zeile | Vorschau | Karte | Seite und Teile |
|---|---|---|---|---|---|
| Folge: Tag | T-01 | `tagZeile` | `tagKachel` | `tagKarte` (im Plan; auf der Tagesseite der Tageskasten) | `ansichtTag`, `ansichtReise` |
| Bewegung: Etappe, Strecke | E-01 | `streckeZeile` | `abschnittKarte` | – | `ansichtAbschnitt`, `tagEbenen` |
| Ort | O-01 | im `wegVerlauf` | `tagOrteZeilen`, `listenZeile` | – | `ansichtOrt` |
| Aufenthalt mit Nacht: Unterkunft | U-01 | `nachtZeile` | `listenZeile` (Zu buchen) | `unterkunftKarte` | `nachtAbschnitt` |
| Aufenthalt ohne Nacht | A-01 | `aufenthaltZeile` (in der Zeitleiste des Tags an seinem Ort) | `listenZeile` (Zu buchen) | – | Tagesseite (`tagKarte` voll) |
| Buchung | B-01 | `buchungChip` (am Ding) | `listenZeile` (Zu buchen, mit Frist) | – | `buchungBlock` bei seinem Ding: `unterkunftKarte`, `aufenthaltZeile` und `streckeZeile` voll; ohne Tagesseiten im Tageskasten des Plans |
| Wahl: Wahlstelle | V-01 | `wahlZeile` | `listenZeile` (Zu entscheiden) | `wahlKarte` | `wahlEinstieg`, `wahlVergleich`, `nachtAbschnitt` |
| Option einer Wahl | V-01.a | `optionBlock` | Zeile der Tabelle im `wahlVergleich` (Rechner) | Karte im `wahlVergleich` (Handy) | – |
| Plan | P-A | `planMarke` | `steckbrief` | – | `ansichtPlanDetail` |
| Offene Frage | F-01 | – | – | `zeilenKarte` | `ansichtFragen` |
| Wissen, Praxis, Quelle, Plantext | W-01 | – | `listenZeile` | – | `ansichtAbschnitt`, `ansichtWissen` |
| Abschnitt eines Textes | E-01.eckdaten | – | – | `block` (aufklappbar) | `reiseText`, `reiterGruppe`, `leseAbschnitt` |
| Aufgabe | AG-01 | `agEintrag` | – | – | `ansichtAufgaben`, `agFormular` |
| Rückmeldung, Wunsch | R-… | `rmEintrag` | – | `wuKarte` | `rmFormular`, `ansichtWuensche` |

Dichten: **Zeile** steht in einem größeren Ganzen (im Tag, in einer Liste), **Vorschau** führt zur ganzen Seite, **Karte** steht für sich, **Seite** zeigt alles. Jede Art trägt die Kennung (Atom `zid`).

Atomic Design allein sagt nicht, wie sich ein Baustein verhält. Dafür gibt es drei Achsen:

- **Zustand.** Feste Namen in `CHIP`: `plan` (entschieden, im Plan), `offen` (braucht eine Entscheidung), `unterwegs` (erst unterwegs zu entscheiden), `weg` (verworfen, ersetzt), `leise` (Nebenangabe), `neben` (Nebenroute). Ein Wert ist bekannt, ungeprüft, unklar, offen oder gilt je Datum.
- **Dichte.** Zeile, Vorschau, Karte, Seite (siehe Tabelle oben); ein Ding hat in jeder Dichte dasselbe Etikett.
- **Kontext.** Planung oder unterwegs (`verhalten.ausloeser_vor` je Status), Handy oder Rechner, offline. Der Kontext ändert Reihenfolge und Betonung, nie die Bausteine. Grundsatz: **Rechner = planen, Handy und Tablet = unterwegs.**

## Regeln

1. **Ein Ding, ein Baustein.** Aufenthalt, Bewegung und Folge sehen überall gleich aus.
2. **Eine Wahl, ein Modul.** Jede Stelle mit Alternativen hat denselben Einstieg „Alternativen vergleichen“ und denselben Vergleich (Regeln in `docs/alternativen.md`).
3. **Ein Wert steht einmal.** Notiz, Prüfdatum und Quelle stehen hinter dem „i“ des Werts, nicht im Fließtext. Was die Kennzahlenleiste zeigt, wiederholt keine Merkmalliste; derselbe Text steht an einer Stelle einmal.
4. **Farbe trägt Bedeutung.** Akzentgrün heißt entschieden, Warnfarbe heißt offen, ein dünner Rand heißt unterwegs. Sonst nichts. Ausnahme sind Erkennungsfarben aus den Daten (Plan, Art der Unterkunft, Art eines Orts); sie kommen als CSS-Variable (`--farbe`, `--kat`), nie als `style="color:…"`.
5. **Aus Daten, nicht aus Einstellungen.** Was eine Ansicht zeigt, ergibt sich aus dem Planungsstand, für alle Reisen gleich.
6. **Ein Kasten nur, wo man handelt.** Flächen mit Rand oder Schatten tragen Bedienelemente (Tageskasten); Lesetext steht ohne Rahmen.
7. **Symbol oder Wort, nie beides.** Was man nur vielleicht braucht, ist ein Symbol mit Tooltip (Anmerken); was man oft braucht, ist ein Wort ohne Symbol („Alternativen vergleichen“, Reiter, „← Plan“). Etiketten dürfen ein Symbol tragen, wenn es die Art sofort zeigt (Nacht, Wahl, Ort, Kennzahlen); sie sind keine Bedienelemente.
8. **Das Gerät bestimmt die Reihenfolge.** Dieselben Bausteine, am Rechner zum Planen nebeneinander, am Handy zum Nachschlagen untereinander (Tagesseite).
9. **Anmerken erst nach dem Lesen.** Unterwegs (Handy und Tablet) trägt eine Vorschau (`.vorschau`) und der Kopf eines zugeklappten Blocks keine Sprechblase; sie erscheint, sobald der Inhalt offen oder die Seite geöffnet ist. Niemand merkt etwas an, bevor er den Inhalt gesehen hat. Am Rechner (Planen) bleibt sie überall (Entscheidung 28.10.2026).

## Reisetexte

Was in den Markdown-Dateien einer Reise steht (Wissen, Praxis, Etappen, Unterkünfte), ist Fließtext. Das Designsystem gibt dort nur die Typografie vor: Überschriften, Absätze, Listen, Tabellen, Zitate, Links und Bilder sehen überall gleich aus, weil sie über die Gestaltung der Seite laufen. Bausteine entstehen nie aus Text, sondern aus Daten (Routenmodell, Merkmale).

Der Generator prüft das: Ein Text darf nur enthalten, was Markdown selbst erzeugt (`TextPruefung` in `engine/bauen.py`). Eigenes HTML, Stile, Klassen oder Skripte im Text sind ein Fehler beim Bauen. Erlaubt ist allein die Spaltenausrichtung von Tabellen. Was der Generator danach selbst ergänzt (Tabellenrahmen, Fußnoten, Bildlisten, Links in neuem Fenster), gehört zur Seite und nicht zum Text.

**Tabellen (B2, 27.10.2026).** Etappentexte bestehen oft aus Tabellen; roh sind sie am Handy breiter als der Bildschirm. Der Generator ordnet sie deshalb für alle Reisen gleich (`tabellen_ordnen` in `engine/bauen.py`), der Text bleibt reines Markdown:

- **Zweispaltig** (Merkmal | Wert) wird eine Merkmalliste `dl.textmerkmale` ohne Kopfzeile: bei genug Platz Merkmal und Wert nebeneinander, in schmalem Behälter (unter 700 px, Container-Query auf die Hülle `.tabelle`) das Merkmal als Etikett über dem Wert. Ein „/“ im Merkmal darf umbrechen.
- **Breiter** bleibt eine Tabelle (`.tabelle.stapel`). In schmalem Behälter wird jede Zeile ein Eintrag: erste Spalte fett, die übrigen als „Spalte: Wert“, leere Zellen („–“) entfallen. Nichts steht seitlich über.
- **Ein Wert steht einmal.** Zeigt die Seite die Kennzahlenleiste (Tag, Etappe), entfallen in der Merkmalliste die Zeilen, die sie schon zeigt (gleicher Name wie in `kennzahlen`). Derselbe Text zweimal an einer Stelle (etwa dieselbe Tabelle aus Etappen- und Unterkünfte-Dossier) steht einmal. Das Höhenprofil behält Bild und Tabelle.
- Der Konnektor liest Merkmallisten als „- Merkmal: Wert“.

## Gestaltung „Freundlich“ (B2, 27.10.2026)

Vorher „Wanderführer“ (Papiergrund, Waldgrün, Serifen, Etiketten in Großbuchstaben). Gewählt nach vier Runden an echten Seiten (#52, #55):

- **Farben** (hell / dunkel): Grund `#f8f8f5` / `#151816`, Fläche `#ffffff` / `#1d211e`, Text `#1d2420` / `#eceee9`, gedämpft `#5b645e` / `#a5aca6`, Linie `#e4e5df` / `#2c312d`, Akzent `#1f7a57` / `#6fd0a5`, helle Akzentfläche `#e3f1ea` / `#1f3329`, offen `#9a5b00` auf `#fbeed6` / `#f0c46a` auf `#3a3017`. Text auf Grund und Fläche hat hell und dunkel mindestens 4,5:1 (WCAG AA), der Akzent auf der hellen Akzentfläche 4,5:1.
- **Schrift:** Source Sans 3 für Titel und Text (keine Serifen mehr), Tagesnummer 800, Titel mit leicht engerem Abstand.
- **Etiketten** (Atom Etikett: Ding-Etikett, Tagesdatum, Kennzahl, Start und Ziel, Merkmal einer Merkmalliste) in normaler Schreibweise, 0,85 rem, halbfett, gedämpft. Titel einer Ebene oder Gruppe 1,2 rem fett.
- **Kennzahlen** als hellgrüne Kacheln (Radius 14 px) mit Symbol im Etikett: Gehzeit (Uhr), Aufstieg, Abstieg, Strecke; am Handy 2 × 2.
- **Symbole an Etiketten:** Nacht und Unterkunft (Bett), Wahl (Abzweig), Orte (Nadel).
- **Flächen:** die Fläche, an der man handelt, weiß, ohne Rahmen, weicher Schatten, Radius 18 px; übrige Karten (Plan, Listen) vorerst mit feiner Linie.
- **Pillen:** Reiter als Segmentleiste (gewählter Reiter weiß mit kleinem Schatten), „Alternativen vergleichen“ hellgrün mit Zahl, „offen“ als Marke, „unterwegs entscheiden“ mit dünnem Rand.
- **Leiste unten** (Plan, Karte, Wissen, Offen, Suche) als **Glas** über dem Inhalt (Fassung 2, Entscheidung 28.10.2026, #55): Fläche zu 58 % deckend mit 14 px Unschärfe, der Inhalt läuft sichtbar darunter durch; Radius 22 px, feiner Rand als Schatten; Reiter gedämpft, der gewählte als hellgrüne Pille mit grüner Schrift. Ohne `backdrop-filter` bleibt sie deckend. Die Anmeldeseiten haben statt der dunklen Kopfleiste eine helle mit feiner Linie.
- Tippflächen mindestens 44 px (Reiter 40 px in einer 48 px hohen Leiste). Pico CSS 2.1.1 ist die Grundlage.

**Noch offen:** das Übertragen auf Plan, Orte, Wissen und Vergleich (#58).

## Schrift und Breite (27.10.2026)

- **Schrift.** Alle Schriftgrößen stehen in `rem`, nichts in `px` (Ausnahme: Beschriftung und Zeichen auf der Karte). Die Wurzelgröße wächst mit dem Bildschirm: Handy 16 px, ab 760 px 17 px, ab 1100 px 19 px, ab 1700 px 20 px. So wird der Text am Rechner größer, ohne dass das Handy sich ändert, und jede Größe ändert man an einer Stelle.
- **Breite.** Kopf und alle Ansichten teilen die Breite `--breite` (Handy voll, ab 760 px 920 px, ab 1100 px 1280 px, ab 1700 px 1400 px). Eine Ansicht ist nie schmaler oder breiter als die andere. Fließtext bleibt auf Lesebreite `--lese` (44 rem), damit Zeilen nicht zu lang werden; Karten, Tabellen und die Karte nutzen die ganze Breite.
- **Spalten.** Ab 1100 px stehen die Tage des Plans in zwei Spalten, ein Tag mit geöffnetem Vergleich nimmt die ganze Breite. Der Vergleich zeigt am Handy 2, bis 1099 px 4 und ab 1100 px 5 Möglichkeiten nebeneinander (`vglMax`).

## Seitenordnung (28.10.2026)

Analyse, Konzept und grafische Ausarbeitung hat der Product Owner am 28.10.2026 Schritt für Schritt freigegeben (frieda-reist#58). Festgelegt in [ADR-0003](adr/0003-heimat.md). Grundsatz aus der Ontologie: **Jede Art hat genau eine Heimat**, an der sie vollständig steht; überall sonst erscheint sie nur als Zeile mit **einem** Link dorthin. Sammelansichten gibt es nur mit eigener Aufgabe (entscheiden, buchen).

| Art | Heimat | als Zeile in |
|---|---|---|
| Reise | Reiter „Reise“ (Überblick) | – |
| Tag | Tagesseite | Zeitachse der Reise |
| Nacht, Unterkunft | Abschnitt „Nacht“ der Tagesseite | Tageszeile, „Zu tun · Zu buchen“ |
| Buchung | das Ding, zu dem sie gehört (Nacht, Aufenthalt, Strecke); ohne Tagesseiten der Tageskasten des Plans | Chip am Ding, „Zu tun · Zu buchen“ |
| Wahlstelle, Option | das Element, an dem sie hängt (Nacht, Strecke, Tag, Ort, Abschnitt des Wissens) | Marke in der Tageszeile, „Zu tun · Zu entscheiden“ |
| Plantext | Wissen „Über diesen Plan“ | – |
| Frage, Aufgabe, Rückmeldung | „Zu tun“ | Stand im Überblick, Sprechblase an der Stelle |

- **Reiter.** Ist ein Plan gewählt und hat die Reise Tagesseiten, heißen die Reiter **Reise · Zu tun · Wissen** (+ Wünsche, Suche); der Reiter „Plan“ entfällt, `#plan` führt zur Reise. „Zu tun“ hieß bis dahin „Offen“. Solange kein Plan gewählt ist (oder ohne Tagesseiten), bleibt „Plan“ mit Tagesplan und Entscheidungen.
- **Zeitachse.** Die Tage der Reise stehen in **einer Spalte** mit Punkt und Linie (`tagZeile` in `.achse`): Nummer und Datum, Titel, Marken (feste Termine zwischen An- und Abreise, „Wahl unterwegs: …“, offene Wahl am Tag), Gehzeit und Strecke, Nacht mit Stand. Die ganze Zeile ist der einzige Link, ohne Kennung. Am Rechner (ab 1100 px) steht der Überblick links, die Zeitachse rechts mit Spalten für Zeit und Nacht; am Handy untereinander.
- **Zurück an dieselbe Stelle.** Kommt man von einem Tag (oder einem Element an ihm) zu einer Liste mit seiner Zeile zurück, über „← Reise“, die Zurück-Taste oder nach dem Blättern, steht die Zeile in der Mitte und hat den Fokus (`zurueckZurZeile`, `history.scrollRestoration = "manual"`).
- **Heimat statt Seitenende.** Ein Link auf eine Unterkunft oder Wahlstelle (`#U-…`, `#V-…`, `#V-….a`) öffnet das Element, an dem sie hängt (`heimat`): die Nacht des ersten Tags im Plan, die Strecke, den Ort oder Abschnitt; was an keinem Element hängt, steht in „Zu tun“.
- **Nacht auf der Tagesseite** (`nachtAbschnitt`): Ist die Wahl offen, die Möglichkeiten im Vergleich (Karten oder Tabelle) mit dem Hinweis, dass in der Claude-App entschieden wird; sonst die Unterkunft vollständig (Kontakt, Buchung, Nächte, Merkmale), die übrigen Möglichkeiten zugeklappt. Im Tageskasten steht die Nacht als Zeile mit „Alternativen vergleichen“, das zum Abschnitt führt. Reihenfolge am Handy wie im Wanderführer: Der Weg, Unterwegs nachschlagen, Nacht, Orte, Hintergrund, Quellen; am Rechner links lesen (Der Weg, Nacht, Hintergrund), rechts nachschlagen.
- **Alternativen am Rechner** (Variante D1, Product Owner 29.10.2026; gewählt wird am Rechner): Der Vergleich (`wahlVergleich`) zeigt ab 700 px eine Tabelle mit **je Möglichkeit einer Zeile**, alle gültigen Möglichkeiten. **Spalten sind die Merkmale der Stufe „nötig“ (`pflicht`) und „gut zu wissen“ (`empfohlen`)**; die Reise legt die Stufe fest (in der Claude-App, `docs/ontologie.md`). Merkmale der Stufe „zusätzlich“ (`angeboten`) stehen nur in den aufgeklappten Einzelheiten, `aus` nirgends; hat kein Merkmal der Stufen nötig oder gut zu wissen einen Wert, sind alle belegten Spalten (Product Owner 29.10.2026). Erste Spalte: Name, „vorläufig im Plan“, „Webseite ↗“. Ein Klick auf einen Spaltenkopf sortiert (Geldbeträge nach Zahl), ein Klick auf die Zeile klappt die Einzelheiten auf (Vor- und Nachteile, Verlauf, Kontakt). Keine zweite Liste darunter; Verworfene zugeklappt am Ende. Ist die Wahl einer Nacht offen, steht der Abschnitt „Nacht“ am Rechner über die volle Breite, direkt unter Tageskasten und Karte. Am Handy bleiben Karten (höchstens 2 nebeneinander) mit „Alle Möglichkeiten im Einzelnen“ zum Aufklappen.
- **Kein Link auf sich selbst, Webseite nach außen** (29.10.2026): Name und Unterkunft einer Möglichkeit verweisen nicht mehr auf die Seite, auf der sie stehen. Die Webseite kommt aus dem Kontakt der Unterkunft (`https://…`, `www.…` oder `name.com`) und öffnet in einem neuen Fenster; fehlt sie, steht „Webseite fehlt“ in den Einzelheiten.
- **Alternativen an jedem Element.** Eine Wahlstelle kann mit `an:` an Tag, Strecke, Unterkunft, Ort, Wahlstelle oder einem Abschnitt des Wissens hängen (`W-…`, etwa Essen oder Ausflug; `docs/alternativen.md`). Sie erscheint dort immer gleich: am Tag im Tageskasten, an Ort oder Abschnitt unter „Zur Wahl“, mit Vergleich.
- **Zu tun.** Oben (am Rechner nebeneinander) **Zu entscheiden** (offene Planungs-Wahlstellen mit „n zur Wahl“, darunter „Unterwegs entscheiden“; je Zeile wo sie hängt und was vorläufig gilt) und **Zu buchen** (je Nacht die Unterkunft mit Datum, Ort und Stand; dazu seit Paket O-5 jede Bewegung und jeder Aufenthalt ohne Nacht mit Buchungsstand, Symbol der Art, Zeile führt zum Tag); darunter Aufgaben, offene Fragen und Rückmeldungen wie bisher. Einen Kasten „Mahnung“ gibt es seit dem 29.10.2026 nicht mehr (Product Owner): Was er nannte, steht als „Zu entscheiden“ hier und als „ungeprüft“ am Wert; die Mahnungen selbst stehen in der Claude-App. Der Stand der Vorbereitung im Überblick führt zu „Zu buchen“ und „Zu entscheiden“.
- **Wissen.** Neu oben „Über diesen Plan“: der Plantext der Reise (Abschnitte vom Typ `plan`, ohne Tagesplan und Unterkunftsliste, die an ihrer Heimat stehen). Was im Plantext Fakten (Überblick) oder Tageshinweise (Tag) sind, ordnet der AI-Client beim Schreiben (`wissen_schreiben`, `tag_aendern`) dort ein; die Software hat dafür keine Sonderregel.

Entwurf und Konzept: Artefakte „Seitenordnung“ im Reisen-Repo der Instanz.

## Tagesseite (B2 „Freundlich“, 27.10.2026)

Am 27.10.2026 wurde das Grunddesign an einer echten Tagesseite überarbeitet (frieda-reist#52): Die Seite war eine Tabellenwüste aus Kästen ohne Rangfolge, mit doppelten Werten. Grundsatz: **Rechner = planen, Handy und Tablet = unterwegs.** Es sind dieselben Bausteine, Reihenfolge und Betonung folgen dem Gerät (Achse Kontext).

- **Oben** der Tageskasten (die Zeitleiste des Tags: Start, Bewegungen mit Kennzahlen, Aufenthalte ohne Nacht an ihrem Ort mit Zeit, Buchung, Lage und Merkmalen, Unterwegs-Wahl, Nacht) und die Karte der Etappe. Jede Bewegung und jeder Aufenthalt trägt Symbol und Namen seiner Art aus `plan/arten.yaml` (Paket O-5). Der Tageskasten ist die **einzige Fläche** der Seite (`.karte.flaeche`: weiß, ohne Rahmen, weicher Schatten, Radius 18 px), denn nur dort handelt man. Lesetext steht ohne Rahmen.
- **Vier Ebenen** je Etappe:
  - *Der Weg:* die Zusammenfassung als Lesetext (gegliedert in Absätze mit fettem Stichwort nach der Gliederung der Art, `docs/ontologie.md` „Lesetext“), nach gut vier Zeilen sanft abgeschnitten mit „Weiterlesen“ (nur wenn mehr Text da ist; ein Tiefenlink zeigt ihn ganz), darunter die Unterzeile der Quelle; die Kennung der Etappe steht hier (im Tageskasten nicht noch einmal).
  - *Unterwegs nachschlagen:* Eckdaten, Höhenprofil, Wegpunkte, Unterkünfte … als **Reiter** (Molekül `reiterGruppe`), immer einer offen, kein Aufklappen. Der Bereich, den die Reiter umschalten, liegt auf einer getönten Fläche (`--tint`): am Handy als Streifen über die ganze Breite, am Rechner als Fläche in der rechten Spalte (Vorschlag „Streifen“, Entscheidung 28.10.2026). Die Wahl merkt sich die Seite je Tag; die Sprechblase des offenen Reiters steht rechts im Kopf der Ebene. Pfeiltasten wechseln den Reiter.
  - *Hintergrund:* Tipps, Geschichte und alles Übrige als **Kapitel** (Molekül `kapitel`): zugeklappt mit Titel, einer Zeile Vorschau und der Zahl der Einträge, immer nur eines offen; die Seite merkt sich das offene je Tag. Tiefenlinks öffnen das Kapitel (28.10.2026, vorher alles offen).
  - *Quellen und Prüfung:* das einzige Aufklappen, ganz unten.
- **Orte des Tages** als Zeilen: Name als Link, Kurztext, Kennung; keine Marken.
- **Reihenfolge.** Handy und Tablet (`max-width:1099px` oder `pointer:coarse`): untereinander Tageskasten, Karte, Der Weg, Unterwegs nachschlagen, Orte, Hintergrund, Quellen. Rechner (`min-width:1100px` und `pointer:fine`): Tageskasten neben der Karte, darunter zwei Spalten, links lesen (Der Weg, Hintergrund, Quellen), rechts nachschlagen (Unterwegs, Orte).
- **Weniger Lärm.** „im Plan“ und die Orte-Marken unter der Etappe entfallen; ist ein Plan gewählt, nennt der Tag keine Pläne.
- **Tiefenlinks** (`#E-01.eckdaten`) wählen den Reiter, öffnen die Quellen oder springen zum Abschnitt.

**Welche Ebene?** Der Generator ordnet jeden Abschnitt einer Etappe nach dem Anfang seines Titels (`EBENEN_VORGABE` in `engine/bauen.py`, Groß- und Kleinschreibung egal), für alle Reisen gleich:

| Ebene | Titel beginnt mit |
|---|---|
| Der Weg | Zusammenfassung |
| Unterwegs nachschlagen | Eckdaten, Höhenprofil, Wegpunkte, Unterkünfte, Unterkunft, Kontakte, Wasser, Einkehr, Verpflegung, Anfahrt, Abfahrt, Praktisch |
| Quellen und Prüfung | Quellen, Prüfung, Karten |
| Hintergrund | alles andere |

Eine Reise kann eigene Titelanfänge ergänzen, die vor der Vorgabe gelten: in `reise.json` `"etappen_ebenen": {"unterwegs": ["Fahrplan"], "hintergrund": ["Höhenprofil"]}`. Eine unbekannte Ebene ist ein Fehler beim Bauen.

Ergebnis an einem echten Etappentag (Handy, 390 px): Weg zu den Unterkünften 2,2 statt 7,5 Bildschirme, 17 statt 35 Knöpfe, 1 statt 14 Kästen, keine Tabelle mehr breiter als der Bildschirm.

## Reiseüberblick (28.10.2026)

Ist ein Plan gewählt, heißt der erste Reiter **„Reise“** und zeigt die Reise statt des Plans (Vorlage `ansichtReise`, Entscheidung 28.10.2026). Der Planname („Plan B“), sein Steckbrief und die anderen erwogenen Pläne kommen auf der Seite nicht mehr vor, auch nicht in der Suche; ihre Daten bleiben in `routen.yaml`, ein Link auf einen Plan (`#P-…`) führt zum Überblick. Ist noch kein Plan gewählt, bleibt der Vergleich der Pläne. Für alle Reisen gleich, alles aus den Daten, von oben nach unten:

1. **Kopf:** „Reise“ mit Zähler: vor der Reise „noch n Tage“, unterwegs „Tag x von n“, danach nichts. Unterwegs steht der heutige Tag darüber.
2. **Anreise:** der erste Tag mit seinen festen Terminen (`fixpunkte`) und Fahrten (Strecken, die keine Wanderung sind), z. B. „Ankunft mit dem Zug in Dresden“ (Beispielreise); führt zum Tag.
3. **Karte** der Reise mit Legende (`uebersichtKarte`). Der Kasten unter der Karte erscheint erst, wenn man einen Ort antippt.
4. **Kennzahlen** als Kacheln (`kennzahlLeiste`): mit Wanderdaten Tage, Gehzeit, Strecke, Höhenmeter; ohne Tage, Nächte, Orte. Fehlt eine Angabe, entfällt die Kachel. Dazu **Übernachtungen**: Summe der Preise pro Nacht (Merkmal `preis` der Unterkunft, am Datum der Nacht), bei offener Wahl als Spanne der Kandidaten; je Währung getrennt. Fehlen Preise, sagt ein Satz darunter, für wie viele Nächte der Preis bekannt ist. Gelesen wird der erste Betrag oder die erste Spanne vor einer Klammer; „pro Person“ zählt nicht.
5. **Mitreisende:** wer reist (`reist`), wer nur einen Teil mitreist mit „ab“ und „bis“ (`von`, `bis` an der Person in `reise.yaml`).
6. **Stand der Vorbereitung** (`standLeiste`), sichtbar für alle bis zur Abreise (Status idee, planung, fest): Unterkünfte gebucht (x von y, führt zu „Zu tun · Zu buchen“, mit Reiter „Plan“ zum ersten Tag mit ungebuchter Nacht), noch zu entscheiden (offene Planungs-Wahlstellen), offene Fragen, offene Aufgaben (Warnfarbe bei überfälligen). Zeilen ohne Offenes entfallen, die Unterkünfte bleiben.
7. **Nächste Fristen:** die drei offenen Aufgaben mit der frühesten Frist (`agEintrag`), mit Link auf alle.
8. **Feste Termine** zwischen An- und Abreise (die am ersten und letzten Tag stehen schon dort), je Termin Tag und Titel.
9. **Die Tage** als Zeitachse (`tagZeile`, siehe Seitenordnung): Nummer und Datum, Titel, Gehzeit, die Nacht mit Stand: „gebucht“ (oder was in `buchung` steht), „nicht gebucht“, „noch wählen · n“ bei offener Wahl, „Unterkunft offen“. Zeigen auf eine Zeile hebt den Tag auf der Karte hervor, Tippen öffnet ihn. Teile einer Reise (`teil`) stehen als Etikett dazwischen.
10. **Abreise:** der letzte Tag wie die Anreise, Fahrten vor den Terminen (Beispielreise: „S-Bahn Bad Schandau → Dresden“).

**Buchung als eigenes Ding (29.10.2026, #76):** Eine Buchung `B-…` (`route.buchungen`) hat ihre Heimat bei ihrem ersten gebuchten Ding (ADR-0003): auf der Unterkunftskarte, am Aufenthalt und an der Strecke auf der Tagesseite (ohne Tagesseiten im Tageskasten des Plans) steht das Molekül `buchungBlock`: Etikett „Buchung“ mit Zustand (gebucht im Plan-Ton, angefragt in Warnfarbe, storniert durchgestrichen), Nummer, Anbieter, Preis, bezahlt, Frist (Warnfarbe, wenn überfällig und Fristen zählen), Storno mit Datum, leise gebucht am/von und Herkunft, die **Belege** (`belegeListe`: Name öffnet die Datei in neuem Fenster, Größe, wer, wann, Sichtbarkeit; Organisator:innen geben frei, die hochladende Person zieht zurück; Formular „Beleg anhängen“ für Mitwirkende mit Netz) und der Verlauf zugeklappt. Überall sonst nur der Chip `buchungChip` mit Link `#B-…` (die Adresse führt zum Ding, der Block ist das Ziel) und in „Zu tun · Zu buchen“ die Zeile mit Stand und Frist („gebucht · Frist 13.5.“), die zur Buchung führt. Belege kommen live vom Rückmeldedienst (`api/belege`, nur was die Person sehen darf), die letzte Liste bleibt im Browser; die Datei selbst braucht Netz.

**Buchungsstand (Paket O-5):** Einen Buchungsstand hat jedes Ding einer buchbaren Art (`buchbar` in `plan/arten.yaml`; Vorgabe: Aufenthalte ja) und jedes Ding mit `buchung:` in `routen.yaml`. Gebucht ist, was eine andere Buchung als `offen` trägt (`buchung: gebucht`, `buchung: Zeitfenster 10 Uhr`); ohne Angabe gilt bei buchbarer Art `offen`. Der Stand steht als Marke am Ding (Unterkunftskarte, Streckenzeile, Aufenthalt) und zählt in „Stand der Vorbereitung“ („Gebucht x von y“) und „Zu buchen“.

## Aufgaben und Wünsche (28.10.2026)

Beide Ansichten sprechen die Sprache der Mitreisenden, nicht die des Systems:

- **Keine Kennungen im Text.** Eine Aufgabe nennt ihre Stellen mit Namen („Tag 2 · Stadt Wehlen → Bastei → Hohnstein“, „Pension Burgblick“) als hellgrüne Pillen; die Kennung steht nur im Tooltip und im Formular. Ebenso der Vorschlag an einem Wunsch. Erklärtexte nennen „Frieda“ statt „Claude Code“.
- **Aufgabe** (`agEintrag`): Haken, Titel, rechts das Wort „Bearbeiten“; darunter Frist (fett, überfällig in Warnfarbe), Zuständig und Wichtigkeit als eine Zeile mit Punkten; die Notiz leise. Gruppen („Überfällig“, „Offen“, „Später möglich“) mit Zahl als Marke; Erledigtes als zugeklapptes Kapitel. Filter als Segmentleiste wie die Reiter, daneben „+ Neue Aufgabe“ als Pille.
- **Kennungen im Lesetext** (`kennungenImText`, 28.10.2026): Nach dem Zeichnen jeder Ansicht (außer der Bausteinseite) werden Kennungen in Texten zu Namen mit Link („(F-03)“ → die ersten Worte der Frage, „U-12“ → Name der Unterkunft); Auftrags- und Rückmeldungsnummern (A-…, R-…) entfallen. Die Dateien behalten die Kennungen (Herkunft, Nachvollziehbarkeit). Frieda in der Claude-App spricht ebenso in Namen (`SPRACHE` in `engine/konnektor.py`) und schreibt neue Lesetexte mit Namen.
- **Offene Fragen** (`frageZeile`): die Frage in Worten, gruppiert nach Stand („Zu klären“, „Als Aufgabe unterwegs“, „Geklärt“ zugeklappt), darunter „bis …“, die Stellen als Pillen und die Notiz zum Stand leise. Die Spalten kommen aus `offene-fragen.md` (Was, Bis, Status). Kennungen im Text löst `kennungenAufloesen` auf, für jede Reise gleich: Eine Klammer nur mit Kennungen („(V-01.a)“) entfällt und wird zur Pille, eine Kennung im Satz wird zum Namen mit Link, eine andere Frage zu ihren ersten Worten, eine Aufgabe zu ihrem Titel; Code-Markierungen (`…`) entfallen.
- **Wünsche:** „Neuer Wunsch“ ist eine Fläche (man handelt dort) auf Lesebreite: Wunsch über die ganze Breite, darunter Link und Name nebeneinander (am Handy untereinander), „Wunsch senden“ rechts. Ohne Wünsche ein gestrichelter Hinweis mit Symbol. Spalten des Bretts mit Zahl als Marke, Karten mit fettem Wunsch, Punkte als leise Marke.

## Kennung und Rückmeldung (B2, 27.10.2026)

Die Kennung (Atom `zid`: T-01, V-05 …) ist die Anschrift jeder Rückmeldung. Im Alltag braucht niemand sie, deshalb steht sie nie in der Seite. Es gilt **„Symbol oder Wort, nie beides“**: Bedienelemente, die man nur vielleicht braucht, sind ein Symbol mit Tooltip; was man oft braucht, ist ein Wort ohne Symbol („Alternativen vergleichen“, Reiter, „← Plan“, „Tag 3 →“).

- **Anmerken** ist deshalb überall nur die Sprechblase: Tippfläche 44 × 44 px, Symbol 1,25 rem, leer blass (Deckkraft 0,7; bei Hover und Fokus voll), mit Rückmeldungen grün gefüllt mit der Zahl oben rechts, eine offene Aufgabe als Warnpunkt unten rechts.
- Der Tooltip (`title`) sagt es in Klartext: „Anmerken“ oder „2 Rückmeldungen · 1 Aufgabe offen“. `aria-label` nennt dazu die Kennung („Anmerken zu T-01, 2 Rückmeldungen“).
- Die Kennung selbst steht im Fenster, das sich öffnet („Zu T-01“), mit einem Knopf „Kopieren“, um im Gespräch auf eine Stelle zu zeigen. Ein Info-Zeichen „i“ gibt es nicht.
- In Titelzeilen sitzt die Sprechblase mit Abstand am rechten Rand, damit Tippen auf den Titel sie nicht trifft.
- Unterwegs fehlt sie in Vorschauen und an Zugeklapptem (Regel 9).
- Das „i“ an einem Wert (Notiz, Prüfdatum, Quelle; Atom `merkmalWert`) ist etwas anderes und bleibt.

Die Deckkraft ist 0,7 statt der im Versuch gezeigten 0,55: Erst so erreicht das Symbol den Kontrast 3:1, den Bedienelemente brauchen (WCAG 1.4.11), hell und dunkel. Ohne die Bausteine Rückmeldungen und Aufgaben bleibt die Kennung als schlichter Text.

Das ersetzt die Festlegung vom selben Tag (Wortmarke „Anmerken“ mit „i“ bei genug Platz und in Karten, Sprechblase nur bei wenig Platz).

## Friedas Symbol (28.10.2026)

Ein Wegweiser mit zwei Richtungsschildern, weiß und gelb auf dem Akzentgrün (`engine/marke/frieda.svg`). Er steht für Reisen und für Entscheiden zwischen Wegen und bleibt auch in 16 Pixeln erkennbar. Buchstaben sind bewusst nicht im Symbol: Ein einzelnes F liegt zu nah an bekannten Markenzeichen. Der Konnektor-Dienst liefert es unter Friedas Adresse als Favicon und App-Symbol aus und gibt es der Claude-App in `serverInfo.icons` mit. claude.ai beachtet diese Angabe bei eigenen Konnektoren bisher nicht. Es zeigt das Google-Favicon der Hauptdomain (anthropics/claude-ai-mcp#152, offen, Stand 28.10.2026). Sobald Claude die Angabe liest, erscheint das Symbol ohne weitere Änderung. Nach einer Änderung am SVG: `engine/.venv/bin/python engine/marke/erzeugen.py`. Die Reiseseiten behalten ihr eigenes Symbol je Reise.

## Bausteinseite und Prüfung

`#bausteine` zeigt alle Bausteine mit den Daten der jeweiligen Reise, gezeichnet mit denselben Funktionen wie die Seiten. Sie steht nicht in der Leiste. Wo die Reise einen Fall nicht hat, steht ein als „Muster“ benannter Wert.

`engine/tests/test_seite.py` öffnet jede Ansicht der Beispielreise bei 390 und 1200 px. Er meldet Skriptfehler, leere Ansichten und Ansichten, die auf dem Handy seitlich überstehen, bedient das Wahl-Modul und prüft die Bausteinseite. Mit `RH_BILDER=<ordner>` entstehen Bilder der Bausteinseite (Handy und Rechner, hell und dunkel, Chromium und WebKit, also auch Safari auf iPhone und iPad); GitHub Actions legt sie bei jedem Lauf als Artefakt „bausteine“ ab. Pixelvergleiche mit Referenzbildern gibt es bewusst nicht, weil die Schriftglättung je Rechner abweicht und solche Tests ohne echten Fehler rot werden.

Für Umbauten ohne sichtbare Änderung:

- **Inhalt:** `node engine/tests/seiten_browser.mjs <playwright> <url> vorher.json` vor und nach dem Umbau, dann die beiden Dateien vergleichen; jede Abweichung ist eine sichtbare Änderung.
- **Stile:** `node engine/tests/stil_abzug.mjs <playwright> <url> vorher.json` vor und nach dem Umbau, dann `node engine/tests/stil_abzug.mjs vergleich vorher.json nachher.json`. Der Abzug hält für jedes Element jeder Route (390 und 1200 px, hell und dunkel) Lage, Größe und rund 50 berechnete Eigenschaften fest; so wurde das Ordnen des Stilblocks nach Atomic Design als Umbau ohne sichtbare Änderung belegt.

`engine/tests/test_tagesseite.py` prüft die Tagesseite bei 390 und 1300 px: kein Überstand, genau ein Kasten, Reihenfolge der Ebenen je Gerät, Reiter mit Klick und Pfeiltasten, Tiefenlinks in einen Reiter und in die Quellen, Kennung und Fenster, Merkmallisten ohne doppelte Kennzahlen, gestapelte Tabellen.
