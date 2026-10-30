# ADR-0003: Seitenordnung – jede Grundform hat genau eine Heimat

Status: gilt · Entschieden vom Product Owner am 28.10.2026 in Claude Code (Analyse, Konzept und grafische Ausarbeitung einzeln freigegeben) · Umsetzung: frieda-reist #84, #87

Gilt für die Seite (PWA) jeder Reise. Steht unter [ADR-0001](0001-kern.md) (die Seite zeigt die Ontologie) und neben [ADR-0002](0002-atomic-design.md) (mit welchen Bausteinen sie das tut).

## Kontext

Am 28.10.2026 war der Reiter „Plan“ einer laufenden Reise nach Worten des Product Owners „vollkommen wirr“. Die Analyse fand:
- Tage standen dreimal: im Überblick, als Kästen in zwei Spalten im Plan und auf der Tagesseite.
- Alle Unterkünfte standen als Anhang unter dem Plan statt an der Nacht.
- Entscheidungen standen in einem Block ohne Bezug zum Tag.
- Fakten der Reise steckten im Lesetext.
- Jede Tageskachel hatte drei Links, zwei davon zum selben Ziel.
- „Zurück“ sprang an den Seitenanfang.

Ursache war keine einzelne Änderung. Für jede Art von Ding gab es keine Regel, wo sie hingehört, und so hat jede Ansicht sie selbst noch einmal gezeigt.

## Entscheidung

1. **Eine Heimat je Grundform.** Jedes Ding steht an genau einer Stelle vollständig. Überall sonst erscheint es nur als Zeile oder Vorschau mit genau einem Link dorthin.

   | Grundform | Heimat | erscheint als Zeile in |
   |---|---|---|
   | Reise | Reiter „Reise“ (Überblick: Zähler, An- und Abreise, Kennzahlen, Stand) | – |
   | Folge: Tag | Tagesseite | Zeitachse der Reise |
   | Bewegung | Teil der Tagesseite (Tageskasten, Der Weg) | Tageszeile |
   | Aufenthalt: Nacht, Unterkunft | Abschnitt „Nacht“ der Tagesseite | Tageszeile, „Zu tun · Zu buchen“ |
   | Buchung (B-…, seit 29.10.2026, #76) | bei ihrem ersten gebuchten Ding (Unterkunftskarte, Aufenthalt oder Strecke der Tagesseite; ohne Tagesseiten im Tageskasten des Plans) | Chip am Ding, „Zu tun · Zu buchen“ |
   | Wahl mit Optionen | das Element, an dem sie hängt (`an:`), mit Vergleich | Marke in der Zeile des Elements, „Zu tun · Zu entscheiden“ |
   | Ort | Ortsseite | Tagesseite, Wissen |
   | Wissen, Plantext | Reiter „Wissen“ (Plantext unter „Über diesen Plan“) | Tagesseite (Kapitel) |
   | Offenes: Frage, Aufgabe, Rückmeldung, Wunsch | „Zu tun“ bzw. „Wünsche“ | Stand im Überblick, Sprechblase am Element |

2. **Sammelansichten nur mit eigener Aufgabe.** Eine Liste, die Dinge aus mehreren Heimaten sammelt, gibt es nur, wenn sie eine eigene Aufgabe hat: entscheiden oder buchen. Sie zeigt Zeilen, die zur Heimat führen, nie die Dinge in voller Länge.
3. **Reiter:** Reise · Zu tun · Wissen (+ Wünsche, Suche). Den Reiter „Plan“ gibt es nur, solange kein Plan gewählt ist oder die Reise keine Tagesseiten hat.
4. **Ein Link je Zeile, Zurück an dieselbe Stelle.** Die ganze Zeile ist der eine Link, ohne Kennung. Wer von einem Tag zurückkommt (Link, Zurück-Taste, Blättern), steht wieder an dessen Zeile, mit Fokus.
5. **Jedes Element kann Alternativen tragen.** Eine Wahl hängt an Tag, Bewegung, Aufenthalt, Ort, Wahl oder Abschnitt des Wissens und erscheint dort immer gleich.
6. **Text folgt den Daten.** Was als Daten vorliegt (Anreise, Personen, Kennzahlen), steht nicht noch einmal im Lesetext. Hinweise zu einem Tag hängen am Tag. Der Lesetext eines Plans enthält nur die Begründungen.

## Begründung

- Recherche vom 28.10.2026 (Reise-Apps, Wanderführer, Karten-Apps, NN/g, Baymard, Material, Inclusive Components):
  - Der Tagesplan ist das Rückgrat, in einer Spalte.
  - Die Unterkunft gehört an die Nacht.
  - Eine Karte hat genau ein Ziel.
  - Wer nach „Zurück“ oben landet, bricht ab.
- Wahlstellen mit Vergleich und Entscheidung hat keine der untersuchten Apps; sie brauchen deshalb einen festen, wiedererkennbaren Platz am Element.
- Eine Heimat je Grundform folgt aus der Ontologie in ADR-0001 und macht jede Ansicht prüfbar: Erscheint ein Ding in voller Länge an zwei Stellen, ist das ein Fehler.

## Konsequenzen

- Ein Link auf eine Unterkunft oder Wahl (`#U-…`, `#V-…`) öffnet das Element, an dem sie hängt (`heimat` in `engine/vorlage.html`), nicht mehr eine Sammelseite.
- Neue Inhalte einer Reise werden beim Eintragen ihrer Heimat zugeordnet: Fakten in Daten, Tageshinweise an den Tag, Begründungen in den Plantext.
- Die Tests prüfen Reiter, einen Link je Zeile, Zurück an dieselbe Zeile, die Heimat der Unterkunft, „Zu buchen“ und „Über diesen Plan“ (`engine/tests/test_reiseueberblick.py`).
- Details der Gestaltung: `docs/design.md`, Abschnitt „Seitenordnung“.

## Verlauf

- 29.10.2026: Abgleich (`docs/abgleich-2026-10-29.md`): Buchung und Unterkunft standen an mehreren Stellen vollständig (bei jedem Ding der Buchung, an jeder Nacht der Unterkunft, als Liste unter dem Plan), ein Link auf eine Buchung an einem Aufenthalt oder einer Fahrt hatte kein Ziel, die Liste der Entscheidungen im Plan zeigte Wahlen vollständig, die schon am Tag standen. Jetzt: Buchung nur an ihrem ersten Ding, Unterkunft nur an ihrer ersten Nacht, Aufenthalt und Fahrt haben ihren Tag als Heimat (`heimat`), Sammellisten zeigen Zeilen.
- 28.10.2026: Analyse, Konzept (Navigation A, Plantext auflösen, Alternativen an jedem Element) und grafische Ausarbeitung einzeln vom Product Owner freigegeben, gebaut in frieda-reist #84. Am selben Abend als ADR festgehalten.
