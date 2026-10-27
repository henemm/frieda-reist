# Design: Grundregeln und Bausteine

Die Seite folgt einem Designsystem (Issue #18): wenige Bausteine, die jede Ansicht zusammensetzt, statt dass jede Ansicht dieselbe Sache selbst zeichnet. So bekommt eine neue Art von Alternative (Fähre, Restaurant, Flug) kein neues Design, sondern bringt nur ihre Merkmale mit.

## Aufbau: Atomic Design und drei Achsen

Die Ebenen folgen Brad Frosts Atomic Design:

| Ebene | Bausteine in `engine/vorlage.html` |
|---|---|
| Atome | `chip` (Zustand), `merkmalWert` (Wert mit Herkunft), `zid` (Kennung mit Rückmeldeknopf), `planMarke` (Farbe eines Plans als Punkt oder Linie) |
| Moleküle | `kennzahlLeiste`, `merkmalListe`, `fehltZeile`, `optionChips`, `dingEtikett`, `listenZeile` (Wissen, Praxis, Quellen, Orte), `zeilenKarte` (offene Frage), `rmEintrag` (Rückmeldung, Wunsch), `agEintrag` (Aufgabe), `eintragGruppen` („Titel (n)“ mit Einträgen), `kartenLegende` (Zeichen und Wort unter einer Karte), `umschalter` (ein Knopf gedrückt, z. B. `planUmschalter`) |
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

## Gestaltung „Wanderführer“

Farben als CSS-Variablen in `:root` (hell, dunkel per `prefers-color-scheme`): `--bg` Papier, `--card` Fläche, `--fg` Tinte, `--mut` gedämpft, `--line` Linie, `--acc`/`--acc2` Akzent, `--warn`/`--warnbg` offen, `--ocker` Etiketten und unterwegs, `--kat-*` Art der Unterkunft. Schrift: Source Serif 4 für Titel, Source Sans 3 für Text. Tippflächen mindestens 44 px. Pico CSS 2.1.1 ist die Grundlage.

## Schrift und Breite (27.10.2026)

- **Schrift.** Alle Schriftgrößen stehen in `rem`, nichts in `px` (Ausnahme: Beschriftung und Zeichen auf der Karte). Die Wurzelgröße wächst mit dem Bildschirm: Handy 16 px, ab 760 px 17 px, ab 1100 px 19 px, ab 1700 px 20 px. So wird der Text am Rechner größer, ohne dass das Handy sich ändert, und jede Größe ändert man an einer Stelle.
- **Breite.** Kopf und alle Ansichten teilen die Breite `--breite` (Handy voll, ab 760 px 920 px, ab 1100 px 1280 px, ab 1700 px 1400 px). Eine Ansicht ist nie schmaler oder breiter als die andere. Fließtext bleibt auf Lesebreite `--lese` (44 rem), damit Zeilen nicht zu lang werden; Karten, Tabellen und die Karte nutzen die ganze Breite.
- **Spalten.** Ab 1100 px stehen die Tage des Plans in zwei Spalten, ein Tag mit geöffnetem Vergleich nimmt die ganze Breite. Der Vergleich zeigt am Handy 2, bis 1099 px 4 und ab 1100 px 5 Möglichkeiten nebeneinander (`vglMax`).

## Kennung und Rückmeldung (27.10.2026)

Die Kennung (Atom `zid`: T-01, V-05 …) ist die Anschrift jeder Rückmeldung. Im Alltag braucht niemand sie, deshalb steht sie nie laut im Text (Entscheidung vom 27.10.2026 nach drei Vorschlägen). Der Baustein hat zwei Gestalten:

- **B, Wortmarke:** ein Info-Zeichen „i“ (nicht kursiv) und ein Wortknopf „Anmerken“, bei Einträgen „2 Rückmeldungen“ mit Zahl, dazu „1 Aufgabe offen“. Tippen auf das „i“ zeigt die Kennung mit „Kopieren“. Gilt bei genug Platz (ab 700 px) und **in Karten immer**.
- **A, Sprechblase:** nur das Symbol, mit Zahl und einem Warnpunkt bei offener Aufgabe. Gilt bei wenig Platz (unter 700 px) außerhalb von Karten, etwa an Überschriften am Handy. Die Kennung steht dort oben im Fenster, das sich öffnet.

Als Karte zählen `.karte`, `details.block`, `.option`, `.wm-karte` und `.ding`; die Regel steht in der Vorlage im Abschnitt „Kennung (Atom zid)“. Ohne die Bausteine Rückmeldungen und Aufgaben bleibt die Kennung als schlichter Text.

## Bausteinseite und Prüfung

`#bausteine` zeigt alle Bausteine mit den Daten der jeweiligen Reise, gezeichnet mit denselben Funktionen wie die Seiten. Sie steht nicht in der Leiste. Wo die Reise einen Fall nicht hat, steht ein als „Muster“ benannter Wert.

`engine/tests/test_seite.py` öffnet jede Ansicht der Beispielreise bei 390 und 1200 px. Er meldet Skriptfehler, leere Ansichten und Ansichten, die auf dem Handy seitlich überstehen, bedient das Wahl-Modul und prüft die Bausteinseite. Mit `RH_BILDER=<ordner>` entstehen Bilder der Bausteinseite (Handy und Rechner, hell und dunkel, Chromium und WebKit, also auch Safari auf iPhone und iPad); GitHub Actions legt sie bei jedem Lauf als Artefakt „bausteine“ ab. Pixelvergleiche mit Referenzbildern gibt es bewusst nicht, weil die Schriftglättung je Rechner abweicht und solche Tests ohne echten Fehler rot werden.

Für Umbauten ohne sichtbare Änderung: `node engine/tests/seiten_browser.mjs <playwright> <url> vorher.json` vor und nach dem Umbau, dann die beiden Dateien vergleichen; jede Abweichung ist eine sichtbare Änderung.
