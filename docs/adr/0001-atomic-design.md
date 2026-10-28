# ADR 0001: Oberfläche nach Atomic Design

- **Status:** angenommen
- **Datum:** 28.10.2026 festgehalten; gelebt seit dem Designsystem vom 26.10.2026 (frieda-reist#18)
- **Entschieden von:** Product Owner
- **Gilt für:** `engine/vorlage.html` (Skript und Stile), `docs/design.md`, die Bausteinseite `#bausteine`, alle Reisen und Instanzen

## Kontext

Die Seite einer Reise ist eine einzige Vorlage (`engine/vorlage.html`), die der Generator für jede Reise füllt. Sie ist schnell gewachsen. Dabei hat jede neue Ansicht dieselben Dinge (Tag, Nacht, Wahl, Aufgabe …) leicht anders selbst gezeichnet. Die Folgen waren doppelte Werte, verschiedene Gesichter für dieselbe Sache und Seiten ohne Rangfolge, die niemand mehr überblickte (Analyse des Reiters „Plan“, 28.10.2026). Auch beim Bau der Seitenordnung entstanden zunächst eine eigene Zeile und eine eigene Zahlmarke für „Zu tun“, obwohl es Listenzeile und Zustand schon gab.

## Entscheidung

Die Oberfläche folgt Brad Frosts Atomic Design. Dazu kommt die Ontologie der Reise.

1. **Fünf Ebenen.** Tokens → Atome → Moleküle → Organismen → Vorlagen (Ansichten). Ein Baustein nutzt nur Bausteine derselben oder einer tieferen Ebene. Welcher Baustein auf welcher Ebene steht, sagt `docs/design.md` (Abschnitt „Aufbau“). Die Liste steht auch im Kopfkommentar „Bausteine nach Ebenen“ in `engine/vorlage.html`.
2. **Wiederverwenden vor Neubau.** Eine neue Ansicht setzt sich aus vorhandenen Bausteinen zusammen. Passt ein Baustein fast, bekommt er einen Parameter (Beispiel: `listenZeile` mit Zustand rechts für „Zu tun“). Eine Kopie mit eigenen Stilen gibt es nicht.
3. **Ontologie.** Jede Art der Reise (Tag, Etappe, Ort, Unterkunft, Wahlstelle, Option, Plan, Frage, Wissen, Aufgabe, Rückmeldung) hat feste Bausteine je Dichte: Zeile, Vorschau, Karte, Seite. Die Tabelle steht als `ONTOLOGIE` im Code und in `docs/design.md`. Jede Art hat genau eine Heimat, an der sie vollständig steht. Überall sonst erscheint sie als Zeile oder Vorschau mit genau einem Link dorthin (Seitenordnung, 28.10.2026).
4. **Werte nur aus Tokens.** Farben, Radien, Schatten und Breiten kommen aus den Tokens (`--acc`, `--warn`, `--r-*` …). Zustände haben feste Namen (`chip`: plan, offen, unterwegs, weg, leise, neben); die Farbe folgt der Bedeutung, nicht dem Ort.
5. **Gleiche Ordnung in Skript und Stilen.** Der Stilblock ist nach Ebenen gegliedert (Tokens, Grundlagen, Atome, Moleküle, Organismen, Vorlagen, Rahmen, Breiten). Jede Regel steht bei ihrem Baustein. Das Raster einer Ansicht steht bei den Vorlagen.
6. **Verhalten über Achsen, nicht über neue Bausteine.** Zustand, Dichte und Kontext (Handy oder Rechner, planen oder unterwegs) ändern Reihenfolge und Betonung, nie die Bausteine.

## Pflicht bei jeder Änderung an der Oberfläche

- Ein neuer Baustein kommt an vier Stellen hinzu: in den Kopfkommentar „Bausteine nach Ebenen“, in die Stile seiner Ebene, auf die Bausteinseite `#bausteine` (mit Daten der Reise oder einem als „Muster“ benannten Wert) und in die Tabelle in `docs/design.md`. Zeigt er eine Art, kommt er zusätzlich in `ONTOLOGIE`.
- `engine/tests/test_seite.py` öffnet die Bausteinseite und jede Ansicht bei 390 und 1200 px. Umbauten ohne sichtbare Änderung werden mit `seiten_browser.mjs` und `stil_abzug.mjs` belegt (`docs/design.md`, Bausteinseite und Prüfung).
- Eine Ansicht, die etwas selbst zeichnet, was ein Baustein schon kann, ist ein Fehler und wird vor dem Zusammenführen umgebaut.

## Folgen

- Gleiche Dinge sehen überall gleich aus und ändern sich an einer Stelle.
- Die Bausteinseite zeigt alle Bausteine mit echten Daten. Sie kann nicht vom Design abweichen, weil sie dieselben Funktionen nutzt.
- Neue Ansichten brauchen etwas mehr Überlegung vorab: erst prüfen, welcher Baustein passt.
- Die Vorlage bleibt eine Datei. Die Ebenen sind Abschnitte darin, keine eigenen Module.
