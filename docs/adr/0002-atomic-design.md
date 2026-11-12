# ADR-0002: Oberfläche nach Atomic Design

Status: gilt · Entschieden vom Product Owner am 28.10.2026 in Claude Code; gelebt seit dem Designsystem vom 26.10.2026 (frieda-reist #18) · Umsetzung: frieda-reist #87

Gilt für `engine/vorlage.html` (Skript und Stile), `docs/design.md` und die Bausteinseite `#bausteine`, für alle Reisen und Instanzen. Steht unter [ADR-0001](0001-kern.md): Die Oberfläche zeigt die Grundformen der Reise-Ontologie, sie führt keine eigenen Arten ein.

## Kontext

Die Seite einer Reise ist eine einzige Vorlage (`engine/vorlage.html`), die der Generator für jede Reise füllt. Sie ist schnell gewachsen. Dabei hat jede neue Ansicht dieselben Dinge (Tag, Nacht, Wahl, Aufgabe …) leicht anders selbst gezeichnet. Die Folgen waren doppelte Werte, verschiedene Gesichter für dieselbe Sache und Seiten ohne Rangfolge, die niemand mehr überblickte (Analyse des Reiters „Plan“, 28.10.2026). Auch beim Bau der Seitenordnung (frieda-reist #84) entstanden zunächst eine eigene Zeile und eine eigene Zahlmarke für „Zu tun“, obwohl es Listenzeile und Zustand schon gab. Auf die Frage des Product Owners, ob alles nach Atomic Design umgesetzt sei, lautete die Antwort deshalb „nicht vollständig“.

## Entscheidung

Die Oberfläche folgt Brad Frosts Atomic Design. Dazu kommt die Abbildung der Ontologie auf Bausteine.

1. **Fünf Ebenen.** Tokens → Atome → Moleküle → Organismen → Vorlagen (Ansichten). Ein Baustein nutzt nur Bausteine derselben oder einer tieferen Ebene. Welcher Baustein auf welcher Ebene steht, sagt `docs/design.md` (Abschnitt „Aufbau“). Im Code steht dieselbe Liste im Kopfkommentar „Bausteine nach Ebenen“ von `engine/vorlage.html`.
2. **Wiederverwenden vor Neubau.** Eine neue Ansicht setzt sich aus vorhandenen Bausteinen zusammen. Passt ein Baustein fast, bekommt er einen Parameter (Beispiel: `listenZeile` mit Zustand rechts für „Zu tun“). Eine Kopie mit eigenen Stilen gibt es nicht.
3. **Ontologie → Bausteine.** Jede Grundform der Reise (`docs/ontologie.md`: Reise, Ort, Aufenthalt, Bewegung, Folge, Wahl, Aussage, Buchung, Gegenstand, Offenes, Wissen) hat feste Bausteine je Dichte: Zeile, Vorschau, Karte, Seite. Die Tabelle steht als `GRUNDFORMEN` im Code (bis Paket O-5 `ONTOLOGIE`) und in `docs/design.md`; jede Zeile nennt die Grundform, die sie zeigt, und ein Test hält Ontologie, Code und Doku beieinander (seit 12.11.2026, #543). Wo die Grundform auf der Seite ihre Heimat hat, regelt [ADR-0003](0003-heimat.md).
4. **Werte nur aus Tokens.** Farben, Radien, Schatten, Breiten und Schriftgrößen kommen aus den Tokens (`--acc`, `--warn`, `--r-*`, `--t-*` …). Für die Schrift gibt es genau fünf Stufen, die Schriftleiter (`docs/design.md`, Product Owner 29.10.2026); ein Baustein wählt eine Stufe, keine eigene Zahl. Zwei Tests prüfen das: im Stil keine freie Größe, auf der gebauten Seite kein Text außerhalb der Stufen. Zustände haben feste Namen (`chip`: plan, offen, unterwegs, weg, leise, neben); die Farbe folgt der Bedeutung, nicht dem Ort.
5. **Gleiche Ordnung in Skript und Stilen.** Der Stilblock ist nach Ebenen gegliedert: Tokens, Grundlagen, Atome, Moleküle, Organismen, Vorlagen, Rahmen, Breiten. Jede Regel steht bei ihrem Baustein, das Raster einer Ansicht bei den Vorlagen.
6. **Verhalten über Achsen, nicht über neue Bausteine.** Zustand, Dichte und Kontext (Handy oder Rechner, planen oder unterwegs) ändern Reihenfolge und Betonung, nie die Bausteine.

**Pflicht bei jeder Änderung an der Oberfläche:**
- Ein neuer Baustein kommt an vier Stellen hinzu: in den Kopfkommentar der Vorlage, in die Stile seiner Ebene, auf die Bausteinseite (mit Daten der Reise oder einem als „Muster“ benannten Wert) und in `docs/design.md`. Zeigt er eine Grundform, kommt er außerdem in `GRUNDFORMEN`. Die vier Stellen prüft `engine/tests/test_design.py` (seit 29.10.2026): Kopfkommentar und `docs/design.md` sind dieselbe Liste, die Bausteinseite zeichnet jeden Baustein, `GRUNDFORMEN` nennt nur Bausteine der Liste.
- Zeichnet eine Ansicht etwas selbst, was ein Baustein schon kann, ist das ein Fehler und wird vor dem Zusammenführen umgebaut.

## Begründung

- **Ein Ding, ein Gesicht.** Wer eine Nacht einmal als Zeile kennt, erkennt sie überall wieder. Ändert sich das Gesicht, ändert es sich an einer Stelle.
- **Prüfbar.** Die Bausteinseite zeichnet alle Bausteine mit denselben Funktionen und den Daten der Reise. Sie kann nicht vom Design abweichen, und `test_seite.py` öffnet sie bei jeder Prüfung.
- **Generisch.** Bausteine hängen an Grundformen, nicht an Arten einer Reise. Damit passen sie zu ADR-0001: Eine Hüttentour und eine Städtereise nutzen dieselben Bausteine.

## Konsequenzen

- Neue Ansichten brauchen vorab etwas mehr Überlegung, welcher Baustein passt.
- Die Vorlage bleibt eine Datei. Die Ebenen sind Abschnitte darin, keine eigenen Module.
- Umbauten ohne sichtbare Änderung werden mit `seiten_browser.mjs` und `stil_abzug.mjs` belegt (`docs/design.md`, Bausteinseite und Prüfung).
- Mit frieda-reist #87 nachgezogen: „Zu entscheiden“ und „Zu buchen“ nutzen `listenZeile` und `chip`. `nachtAbschnitt`, `zuEntscheiden` und `zuBuchen` stehen im Inventar und auf der Bausteinseite.

## Nachtrag: Organismen richten sich nach der Breite ihres Behälters (5.11.2026, #332, Schritt D)

Ein Organismus kann überall stehen: auf einer eigenen Seite, in einer Karte, in der schmalen rechten Spalte der Tagesseite am Rechner. Sein Layout folgt deshalb der Breite des Behälters, in dem er steht, nicht der des Fensters.

1. **Behälter statt Fenster.** Jeder Organismus mit breitenabhängigem Layout ist ein benannter Behälter (`container: name / inline-size`) und fragt mit `@container name (…)`. Benannt, weil eine unbenannte Anfrage den nächsten Behälter träfe, wer er auch sei. Ein Behälter gestaltet nur seine Nachfahren: Wer sich selbst gestalten muss (Rand, Überlauf), bekommt eine Hülle (`kz-huelle`, `wege-huelle`, `brett-huelle`), die den Behälter trägt.
2. **Drei Stufen.** schmal unter 630 px (Handy, schmale Spalte), mittel ab 630 px, breit ab 960 px; die Kennzahlleiste kippt schon bei 420 px auf zwei mal zwei. Die Schwellen sind aus den Breiten gemessen, die ein Behälter bei den Fensterbreiten 700 und 1100 px hat (Seitenrand 16 oder 28 px, `--breite` 920 px bis 1099 px): in voller Breite sieht daher jede Seite aus wie vorher (Beleg: `stil_abzug.mjs` bei 320, 390, 700, 900, 1100 und 1300 px, hell und dunkel, an beiden Beispielreisen und einer Reise ohne Pläne, vom Stand des Pull Requests: von 1884 Ansichten sind 1680 in Lage und Größe gleich bis auf ±1 px; 110 weichen durch den Zeitpunkt der Messung ab („Weiterlesen“) und 94 durch gewollte Änderungen und Sprünge zu einem Abschnitt: der Umschalter „Tabelle“ bei 700 und 900 px mit Maus (+50 px je Vergleich), am Rechner unter dem offenen Vergleich einer Entscheidung 6 px mehr und auf der Bausteinseite unter einem Vergleich 7 px weniger; ist ein Vergleich am Rechner geschlossen, bleibt die leere Gruppe mit 17 px Rand stehen, die Handy-Darstellung ist gleich). Ein Behälter fängt die Ränder seiner Kinder ein; die Hüllen tragen sie deshalb selbst. Die gewollte sichtbare Folge (Entscheidung des Product Owners 5.11.2026, Option B): Steht ein Vergleich am Rechner in einer Spalte unter 960 px (die Nacht auf der Tagesseite, 695 px bei 1300 px Fenster; die rechte Spalte, 581 px), zeigt er Karten und mit Maus dazu den Umschalter „Tabelle“ statt einer Tabelle, deren letzte Spalte dort abgeschnitten war; Sortieren und Aufklappen bleiben erreichbar. Mit Finger bleibt es bei Karten (#58). Neu ist der Umschalter auch in einem mittelbreiten Browserfenster mit Maus (700 bis 1099 px).
3. **Seitenraster bleibt Media-Query.** Abschnitt „8 Breiten“, `.reise-seite`, `.tagseite`, `.achse .tagzeile`, `.ebene-unterwegs` (gleicht den Rand von `main` aus), Navigation und `dialog#rm` teilen die Seite auf und sind kein Baustein. Die Liste steht in `RASTER_BREITEN` (`test_design.py`) und darf nur kürzer werden.
4. **Das Zeigergerät ist keine Breite.** `pointer` und `hover` bleiben Media-Queries, auch geschachtelt in eine `@container`-Regel: Die Tabelle des Vergleichs steht von Anfang an nur in breitem Behälter und mit Maus; in mittlerem Behälter ist sie mit Maus zum Umschalten da, mit Finger gibt es nur Karten (#58).
5. **Auch das Skript misst den Behälter.** `vglMax` fragt nach der Breite des Ortes, an dem der Vergleich steht (`matchMedia` mit Breite ist verboten); ein `ResizeObserver` korrigiert die Zahl der gezeigten Möglichkeiten, sobald der Vergleich im Dokument steht oder der Behälter sich ändert.

## Verlauf

- 5.11.2026: Organismen richten sich nach der Breite ihres Behälters (Nachtrag, #332, Schritt D): `wm`, Kennzahlen, Wegetabelle, Tageskasten, Wunschfelder und Brett mit `@container`; `test_design.py` hält die Media-Queries mit Breite auf der Liste `RASTER_BREITEN`.
- 5.11.2026: Die Ebenenregel (Punkt 1) prüft `engine/tests/test_design.py` (#332, Schritt A): kein Baustein ruft einen höherer Ebene auf; Zeichner mit eigenen Klassen außerhalb des Inventars stehen auf der Liste `EIGENE_FLAECHEN`, die nur kürzer werden darf. Dabei umgestellt: `buchungChip` ist ein Molekül (nutzt `buchungsStand`), `stornierteBuchungen` und `leseAbschnitt` sind Organismen; die drei Kartenzeichner teilen `karteBedienbar` und `beiSicht`.
- 29.10.2026: Abgleich (`docs/abgleich-2026-10-29.md`): Die Seite kannte die Art „wandern“ noch an sieben Stellen und die Arten „flug“ und „faehre“ in Legende und Linienstil; jetzt entscheidet allein `summiert` der Art. Buchungsstand, Datum, Zustand einer Wahl, Zählmarke, Terminzeile und Kontakt sind je ein Baustein statt mehrfach gezeichnet; Radien und Schatten kommen aus Tokens; die drei Bausteinlisten sind eine Liste, die Bausteinseite zeichnet jeden Baustein, ein Test prüft die vier Stellen.
- 26.10.2026: Designsystem nach Atomic Design (frieda-reist #18), Stilblock nach Ebenen geordnet.
- 28.10.2026: Als ADR festgehalten auf Wunsch des Product Owners. Zuerst als ADR 0001 angelegt; umnummeriert zu 0002, weil am selben Tag ADR-0001 „Der Kern“ entstand.
