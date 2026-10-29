# ADR-0002: Oberfläche nach Atomic Design

Status: gilt · Entschieden vom Product Owner am 28.10.2026 in Claude Code; gelebt seit dem Designsystem vom 26.10.2026 (frieda-reist #18) · Umsetzung: frieda-reist #87

Gilt für `engine/vorlage.html` (Skript und Stile), `docs/design.md` und die Bausteinseite `#bausteine`, für alle Reisen und Instanzen. Steht unter [ADR-0001](0001-kern.md): Die Oberfläche zeigt die Grundformen der Reise-Ontologie, sie führt keine eigenen Arten ein.

## Kontext

Die Seite einer Reise ist eine einzige Vorlage (`engine/vorlage.html`), die der Generator für jede Reise füllt. Sie ist schnell gewachsen. Dabei hat jede neue Ansicht dieselben Dinge (Tag, Nacht, Wahl, Aufgabe …) leicht anders selbst gezeichnet. Die Folgen waren doppelte Werte, verschiedene Gesichter für dieselbe Sache und Seiten ohne Rangfolge, die niemand mehr überblickte (Analyse des Reiters „Plan“, 28.10.2026). Auch beim Bau der Seitenordnung (frieda-reist #84) entstanden zunächst eine eigene Zeile und eine eigene Zahlmarke für „Zu tun“, obwohl es Listenzeile und Zustand schon gab. Auf die Frage des Product Owners, ob alles nach Atomic Design umgesetzt sei, lautete die Antwort deshalb „nicht vollständig“.

## Entscheidung

Die Oberfläche folgt Brad Frosts Atomic Design. Dazu kommt die Abbildung der Ontologie auf Bausteine.

1. **Fünf Ebenen.** Tokens → Atome → Moleküle → Organismen → Vorlagen (Ansichten). Ein Baustein nutzt nur Bausteine derselben oder einer tieferen Ebene. Welcher Baustein auf welcher Ebene steht, sagt `docs/design.md` (Abschnitt „Aufbau“). Im Code steht dieselbe Liste im Kopfkommentar „Bausteine nach Ebenen“ von `engine/vorlage.html`.
2. **Wiederverwenden vor Neubau.** Eine neue Ansicht setzt sich aus vorhandenen Bausteinen zusammen. Passt ein Baustein fast, bekommt er einen Parameter (Beispiel: `listenZeile` mit Zustand rechts für „Zu tun“). Eine Kopie mit eigenen Stilen gibt es nicht.
3. **Ontologie → Bausteine.** Jede Grundform der Reise (Folge/Tag, Bewegung, Aufenthalt, Ort, Wahl mit Option, Wissen, Offenes) hat feste Bausteine je Dichte: Zeile, Vorschau, Karte, Seite. Die Tabelle steht als `ONTOLOGIE` im Code und in `docs/design.md`. Wo die Grundform auf der Seite ihre Heimat hat, regelt [ADR-0003](0003-heimat.md).
4. **Werte nur aus Tokens.** Farben, Radien, Schatten, Breiten und Schriftgrößen kommen aus den Tokens (`--acc`, `--warn`, `--r-*`, `--t-*` …). Für die Schrift gibt es genau fünf Stufen, die Schriftleiter (`docs/design.md`, Product Owner 29.10.2026); ein Baustein wählt eine Stufe, keine eigene Zahl. Zwei Tests prüfen das: im Stil keine freie Größe, auf der gebauten Seite kein Text außerhalb der Stufen. Zustände haben feste Namen (`chip`: plan, offen, unterwegs, weg, leise, neben); die Farbe folgt der Bedeutung, nicht dem Ort.
5. **Gleiche Ordnung in Skript und Stilen.** Der Stilblock ist nach Ebenen gegliedert: Tokens, Grundlagen, Atome, Moleküle, Organismen, Vorlagen, Rahmen, Breiten. Jede Regel steht bei ihrem Baustein, das Raster einer Ansicht bei den Vorlagen.
6. **Verhalten über Achsen, nicht über neue Bausteine.** Zustand, Dichte und Kontext (Handy oder Rechner, planen oder unterwegs) ändern Reihenfolge und Betonung, nie die Bausteine.

**Pflicht bei jeder Änderung an der Oberfläche:**
- Ein neuer Baustein kommt an vier Stellen hinzu: in den Kopfkommentar der Vorlage, in die Stile seiner Ebene, auf die Bausteinseite (mit Daten der Reise oder einem als „Muster“ benannten Wert) und in `docs/design.md`. Zeigt er eine Grundform, kommt er außerdem in `ONTOLOGIE`.
- Zeichnet eine Ansicht etwas selbst, was ein Baustein schon kann, ist das ein Fehler und wird vor dem Zusammenführen umgebaut.

## Begründung

- **Ein Ding, ein Gesicht.** Wer eine Nacht einmal als Zeile kennt, erkennt sie überall wieder. Ändert sich das Gesicht, ändert es sich an einer Stelle.
- **Prüfbar.** Die Bausteinseite zeichnet alle Bausteine mit denselben Funktionen und den Daten der Reise. Sie kann nicht vom Design abweichen, und `test_seite.py` öffnet sie bei jeder Prüfung.
- **Generisch.** Bausteine hängen an Grundformen, nicht an Arten einer Reise. Damit passen sie zu ADR-0001: Eine Hüttentour und eine Städtereise nutzen dieselben Bausteine.

## Konsequenzen

- Neue Ansichten brauchen vorab etwas mehr Überlegung, welcher Baustein passt.
- Die Vorlage bleibt eine Datei. Die Ebenen sind Abschnitte darin, keine eigenen Module.
- Umbauten ohne sichtbare Änderung werden mit `seiten_browser.mjs` und `stil_abzug.mjs` belegt (`docs/design.md`, Bausteinseite und Prüfung).
- Mit frieda-reist #87 nachgezogen: „Zu entscheiden“ und „Zu buchen“ nutzen `listenZeile` und `chip`. `nachtAbschnitt`, `zuEntscheiden` und `zuBuchen` stehen im Inventar, in `ONTOLOGIE` und auf der Bausteinseite.

## Verlauf

- 26.10.2026: Designsystem nach Atomic Design (frieda-reist #18), Stilblock nach Ebenen geordnet.
- 28.10.2026: Als ADR festgehalten auf Wunsch des Product Owners. Zuerst als ADR 0001 angelegt; umnummeriert zu 0002, weil am selben Tag ADR-0001 „Der Kern“ entstand.
