# Design: Grundregeln und Bausteine

Die Seite folgt einem Designsystem (Issue #18): wenige Bausteine, die jede Ansicht zusammensetzt, statt dass jede Ansicht dieselbe Sache selbst zeichnet. So bekommt eine neue Art von Alternative (Fähre, Restaurant, Flug) kein neues Design, sondern bringt nur ihre Merkmale mit.

## Aufbau: Atomic Design und drei Achsen

Die Ebenen folgen Brad Frosts Atomic Design:

| Ebene | Bausteine in `engine/vorlage.html` |
|---|---|
| Atome | `chip` (Zustand), `merkmalWert` (Wert mit Herkunft), `zid` (Kennung mit Rückmeldeknopf), `planMarke` (Farbe eines Plans als Punkt oder Linie) |
| Moleküle | `kennzahlLeiste`, `merkmalListe`, `fehltZeile`, `optionChips`, `dingEtikett`, `listenZeile` (Wissen, Praxis, Quellen, Orte), `zeilenKarte` (offene Frage), `rmEintrag` (Rückmeldung, Wunsch), `agEintrag` (Aufgabe), `eintragGruppen` („Titel (n)“ mit Einträgen), `kartenLegende` (Zeichen und Wort unter einer Karte), `umschalter` (ein Knopf gedrückt, z. B. `planUmschalter`), `kontoKnopf` („Anmelden“ oder eigener Name oben rechts, nur auf Friedas eigener Adresse), `nameFeld` (ohne Konto „Dein Name“, angemeldet nur „Du schreibst als …“) |
| Organismen | Ding: `nachtZeile` (Aufenthalt als Zeile), `unterkunftKarte` (als Karte), `streckeZeile` (Bewegung); Wahl-Modul: `wahlEinstieg`, `wahlVergleich`, `wahlKarte` |
| Vorlagen | `tagKarte`, `tagKachel`, die Ansichten (`ansichtTag`, `ansichtPlan` …) |

Atomic Design allein sagt nicht, wie sich ein Baustein verhält. Dafür gibt es drei Achsen:

- **Zustand.** Feste Namen in `CHIP`: `plan` (entschieden, im Plan), `offen` (braucht eine Entscheidung), `unterwegs` (erst unterwegs zu entscheiden), `weg` (verworfen, ersetzt), `leise` (Nebenangabe), `neben` (Nebenroute). Ein Wert ist bekannt, ungeprüft, unklar, offen oder gilt je Datum.
- **Dichte.** Ein Ding gibt es als Zeile (im Tag, in Listen) und als Karte (Übersicht), mit demselben Etikett.
- **Kontext.** Planung oder unterwegs (`verhalten.ausloeser_vor` je Status), Handy oder Rechner, offline. Der Kontext ändert Reihenfolge und Betonung, nie die Bausteine.

## Fünf Regeln

1. **Ein Ding, ein Baustein.** Aufenthalt, Bewegung und Folge sehen überall gleich aus.
2. **Eine Wahl, ein Modul.** Jede Stelle mit Alternativen hat denselben Einstieg „Alternativen vergleichen“ und denselben Vergleich (Regeln in `docs/alternativen.md`).
3. **Ein Wert, ein Atom.** Notiz, Prüfdatum und Quelle stehen hinter dem „i“, nicht im Fließtext.
4. **Farbe trägt Bedeutung.** Akzentgrün heißt entschieden, Warnfarbe heißt offen, Ocker als Rahmen heißt unterwegs. Sonst nichts. Ausnahme sind Erkennungsfarben aus den Daten (Plan, Art der Unterkunft, Art eines Orts); sie kommen als CSS-Variable (`--farbe`, `--kat`), nie als `style="color:…"`.
5. **Aus Daten, nicht aus Einstellungen.** Was eine Ansicht zeigt, ergibt sich aus dem Planungsstand, für alle Reisen gleich.

## Reisetexte

Was in den Markdown-Dateien einer Reise steht (Wissen, Praxis, Etappen, Unterkünfte), ist Fließtext. Das Designsystem gibt dort nur die Typografie vor: Überschriften, Absätze, Listen, Tabellen, Zitate, Links und Bilder sehen überall gleich aus, weil sie über die Gestaltung der Seite laufen. Bausteine entstehen nie aus Text, sondern aus Daten (Routenmodell, Merkmale).

Der Generator prüft das: Ein Text darf nur enthalten, was Markdown selbst erzeugt (`TextPruefung` in `engine/bauen.py`). Eigenes HTML, Stile, Klassen oder Skripte im Text sind ein Fehler beim Bauen. Erlaubt ist allein die Spaltenausrichtung von Tabellen. Was der Generator danach selbst ergänzt (Tabellenrahmen, Fußnoten, Bildlisten, Links in neuem Fenster), gehört zur Seite und nicht zum Text.

**Tabellen (B2, 27.10.2026).** Etappentexte bestehen oft aus Tabellen; roh sind sie am Handy breiter als der Bildschirm. Der Generator ordnet sie deshalb für alle Reisen gleich (`tabellen_ordnen` in `engine/bauen.py`), der Text bleibt reines Markdown:

- **Zweispaltig** (Merkmal | Wert) wird eine Merkmalliste `dl.textmerkmale` ohne Kopfzeile: bei genug Platz Merkmal und Wert nebeneinander, in schmalem Behälter (unter 700 px, Container-Query auf die Hülle `.tabelle`) das Merkmal als Etikett über dem Wert. Ein „/“ im Merkmal darf umbrechen.
- **Breiter** bleibt eine Tabelle (`.tabelle.stapel`). In schmalem Behälter wird jede Zeile ein Eintrag: erste Spalte fett, die übrigen als „Spalte: Wert“, leere Zellen („–“) entfallen. Nichts steht seitlich über.
- **Ein Wert steht einmal.** Zeigt die Seite die Kennzahlenleiste (Tag, Etappe), entfallen in der Merkmalliste die Zeilen, die sie schon zeigt (gleicher Name wie in `kennzahlen`). Derselbe Text zweimal an einer Stelle (etwa dieselbe Tabelle aus Etappen- und Unterkünfte-Dossier) steht einmal. Das Höhenprofil behält Bild und Tabelle.
- Der Konnektor liest Merkmallisten als „- Merkmal: Wert“.

## Gestaltung „Wanderführer“

Farben als CSS-Variablen in `:root` (hell, dunkel per `prefers-color-scheme`): `--bg` Papier, `--card` Fläche, `--fg` Tinte, `--mut` gedämpft, `--line` Linie, `--acc`/`--acc2` Akzent, `--warn`/`--warnbg` offen, `--ocker` Etiketten und unterwegs, `--kat-*` Art der Unterkunft. Schrift: Source Serif 4 für Titel, Source Sans 3 für Text. Tippflächen mindestens 44 px. Pico CSS 2.1.1 ist die Grundlage.

## Schrift und Breite (27.10.2026)

- **Schrift.** Alle Schriftgrößen stehen in `rem`, nichts in `px` (Ausnahme: Beschriftung und Zeichen auf der Karte). Die Wurzelgröße wächst mit dem Bildschirm: Handy 16 px, ab 760 px 17 px, ab 1100 px 19 px, ab 1700 px 20 px. So wird der Text am Rechner größer, ohne dass das Handy sich ändert, und jede Größe ändert man an einer Stelle.
- **Breite.** Kopf und alle Ansichten teilen die Breite `--breite` (Handy voll, ab 760 px 920 px, ab 1100 px 1280 px, ab 1700 px 1400 px). Eine Ansicht ist nie schmaler oder breiter als die andere. Fließtext bleibt auf Lesebreite `--lese` (44 rem), damit Zeilen nicht zu lang werden; Karten, Tabellen und die Karte nutzen die ganze Breite.
- **Spalten.** Ab 1100 px stehen die Tage des Plans in zwei Spalten, ein Tag mit geöffnetem Vergleich nimmt die ganze Breite. Der Vergleich zeigt am Handy 2, bis 1099 px 4 und ab 1100 px 5 Möglichkeiten nebeneinander (`vglMax`).

## Tagesseite (B2 „Freundlich“, 27.10.2026)

Am 27.10.2026 wurde das Grunddesign an einer echten Tagesseite überarbeitet (frieda-reist#52): Die Seite war eine Tabellenwüste aus Kästen ohne Rangfolge, mit doppelten Werten. Grundsatz: **Rechner = planen, Handy und Tablet = unterwegs.** Es sind dieselben Bausteine, Reihenfolge und Betonung folgen dem Gerät (Achse Kontext).

- **Oben** der Tageskasten (Strecke mit Kennzahlen, Unterwegs-Wahl, Nacht) und die Karte der Etappe. Der Tageskasten ist die **einzige Fläche** der Seite (`.karte.flaeche`: weiß, ohne Rahmen, weicher Schatten, Radius 18 px), denn nur dort handelt man. Lesetext steht ohne Rahmen.
- **Vier Ebenen** je Etappe:
  - *Der Weg:* die Zusammenfassung als Lesetext, darunter die Unterzeile der Quelle; die Kennung der Etappe steht hier (im Tageskasten nicht noch einmal).
  - *Unterwegs nachschlagen:* Eckdaten, Höhenprofil, Wegpunkte, Unterkünfte … als **Reiter** (Molekül `reiterGruppe`), immer einer offen, kein Aufklappen. Die Wahl merkt sich die Seite je Tag; die Sprechblase des offenen Reiters steht rechts im Kopf der Ebene. Pfeiltasten wechseln den Reiter.
  - *Hintergrund:* Tipps, Geschichte und alles Übrige, offen, Überschrift und Text.
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

## Kennung und Rückmeldung (B2, 27.10.2026)

Die Kennung (Atom `zid`: T-01, V-05 …) ist die Anschrift jeder Rückmeldung. Im Alltag braucht niemand sie, deshalb steht sie nie in der Seite. Es gilt **„Symbol oder Wort, nie beides“**: Bedienelemente, die man nur vielleicht braucht, sind ein Symbol mit Tooltip; was man oft braucht, ist ein Wort ohne Symbol („Alternativen vergleichen“, Reiter, „← Plan“, „Tag 3 →“).

- **Anmerken** ist deshalb überall nur die Sprechblase: Tippfläche 44 × 44 px, Symbol 1,25 rem, leer blass (Deckkraft 0,7; bei Hover und Fokus voll), mit Rückmeldungen grün gefüllt mit der Zahl oben rechts, eine offene Aufgabe als Warnpunkt unten rechts.
- Der Tooltip (`title`) sagt es in Klartext: „Anmerken“ oder „2 Rückmeldungen · 1 Aufgabe offen“. `aria-label` nennt dazu die Kennung („Anmerken zu T-01, 2 Rückmeldungen“).
- Die Kennung selbst steht im Fenster, das sich öffnet („Zu T-01“), mit einem Knopf „Kopieren“, um im Gespräch auf eine Stelle zu zeigen. Ein Info-Zeichen „i“ gibt es nicht.
- In Titelzeilen sitzt die Sprechblase mit Abstand am rechten Rand, damit Tippen auf den Titel sie nicht trifft.

Die Deckkraft ist 0,7 statt der im Versuch gezeigten 0,55: Erst so erreicht das Symbol den Kontrast 3:1, den Bedienelemente brauchen (WCAG 1.4.11), hell und dunkel. Ohne die Bausteine Rückmeldungen und Aufgaben bleibt die Kennung als schlichter Text.

Das ersetzt die Festlegung vom selben Tag (Wortmarke „Anmerken“ mit „i“ bei genug Platz und in Karten, Sprechblase nur bei wenig Platz).

## Bausteinseite und Prüfung

`#bausteine` zeigt alle Bausteine mit den Daten der jeweiligen Reise, gezeichnet mit denselben Funktionen wie die Seiten. Sie steht nicht in der Leiste. Wo die Reise einen Fall nicht hat, steht ein als „Muster“ benannter Wert.

`engine/tests/test_seite.py` öffnet jede Ansicht der Beispielreise bei 390 und 1200 px. Er meldet Skriptfehler, leere Ansichten und Ansichten, die auf dem Handy seitlich überstehen, bedient das Wahl-Modul und prüft die Bausteinseite. Mit `RH_BILDER=<ordner>` entstehen Bilder der Bausteinseite (Handy und Rechner, hell und dunkel, Chromium und WebKit, also auch Safari auf iPhone und iPad); GitHub Actions legt sie bei jedem Lauf als Artefakt „bausteine“ ab. Pixelvergleiche mit Referenzbildern gibt es bewusst nicht, weil die Schriftglättung je Rechner abweicht und solche Tests ohne echten Fehler rot werden.

Für Umbauten ohne sichtbare Änderung: `node engine/tests/seiten_browser.mjs <playwright> <url> vorher.json` vor und nach dem Umbau, dann die beiden Dateien vergleichen; jede Abweichung ist eine sichtbare Änderung.
