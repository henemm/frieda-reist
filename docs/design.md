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

## Bausteinseite und Prüfung

`#bausteine` zeigt alle Bausteine mit den Daten der jeweiligen Reise, gezeichnet mit denselben Funktionen wie die Seiten. Sie steht nicht in der Leiste. Wo die Reise einen Fall nicht hat, steht ein als „Muster“ benannter Wert.

`engine/tests/test_seite.py` öffnet jede Ansicht der Beispielreise bei 390 und 1200 px. Er meldet Skriptfehler, leere Ansichten und Ansichten, die auf dem Handy seitlich überstehen, bedient das Wahl-Modul und prüft die Bausteinseite. Mit `RH_BILDER=<ordner>` entstehen Bilder der Bausteinseite (Handy und Rechner, hell und dunkel, Chromium und WebKit, also auch Safari auf iPhone und iPad); GitHub Actions legt sie bei jedem Lauf als Artefakt „bausteine“ ab. Pixelvergleiche mit Referenzbildern gibt es bewusst nicht, weil die Schriftglättung je Rechner abweicht und solche Tests ohne echten Fehler rot werden.

Für Umbauten ohne sichtbare Änderung: `node engine/tests/seiten_browser.mjs <playwright> <url> vorher.json` vor und nach dem Umbau, dann die beiden Dateien vergleichen; jede Abweichung ist eine sichtbare Änderung.
