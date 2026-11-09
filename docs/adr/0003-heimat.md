# ADR-0003: Seitenordnung – jede Grundform hat genau eine Heimat

Status: gilt · Entschieden vom Product Owner am 28.10.2026 in Claude Code (Analyse, Konzept und grafische Ausarbeitung einzeln freigegeben) · Umsetzung: frieda-reist #84, #87 · Nachträge: #214 (2.11.2026), #332 (5.11.2026)

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

1. **Eine Heimat je Grundform.** Seit [ADR-0007](0007-elternbezug.md) ist die Tabelle unten die Tabelle der **Vorgaben**: Die Heimat eines Dings ist die Seite seines Elternelements (`an:`); wo `an:` fehlt, gilt die Vorgabe der Grundform. Jedes Ding steht an genau einer Stelle vollständig. Überall sonst erscheint es nur als Zeile oder Vorschau mit genau einem Link dorthin.

   | Grundform | Heimat | erscheint als Zeile in |
   |---|---|---|
   | Reise | Reiter „Reise“ (Überblick: Zähler, An- und Abreise, Kennzahlen, Stand) | – |
   | Folge: Tag | Tagesseite | Zeitachse der Reise |
   | Bewegung | Teil der Tagesseite (Tageskasten, Der Weg) | Tageszeile |
   | Aufenthalt: Nacht, Unterkunft | Abschnitt „Nacht“ der Tagesseite | Tageszeile, „Zu tun · Zu buchen“ |
   | Aufenthalt ohne Tag (vor Ort gesammelt, seit 2.11.2026, #235; seit ADR-0007 an seinem Ort) | Ortsseite seines Orts (oder der Abschnitt, an den `an:` ihn hängt); hat der Ort keine Seite: zugeklappt am Ende des Reiseüberblicks („Noch ohne Platz“, seit #432; davor „Ohne Tag“ und der Reiter „Karte“) | Punkt auf der Karte (keine Zeile im Überblick, #432) |
   | Buchung (B-…, seit 29.10.2026, #76) | bei ihrem ersten gebuchten Ding (Unterkunftskarte, Aufenthalt oder Strecke der Tagesseite) | Chip am Ding, „Zu tun · Zu buchen“ |
   | Wahl mit Optionen | das Element, an dem sie hängt (`an:`), mit Vergleich | Marke in der Zeile des Elements, „Zu tun · Zu entscheiden“ |
   | Ort | Ortsseite | Tagesseite, Wissen |
   | Wissen, Plantext | Reiter „Wissen“ (Plantext unter „Über diesen Plan“) | Tagesseite (Kapitel) |
   | Offenes: Frage, Aufgabe, Rückmeldung, Wunsch | „Zu tun“ bzw. „Wünsche“ | Stand im Überblick, Sprechblase am Element |

2. **Sammelansichten nur mit eigener Aufgabe.** Eine Liste, die Dinge aus mehreren Heimaten sammelt, gibt es nur, wenn sie eine eigene Aufgabe hat: entscheiden oder buchen. Sie zeigt Zeilen, die zur Heimat führen, nie die Dinge in voller Länge.
3. **Reiter:** Reise · Zu tun · Wissen (+ Wünsche, Suche). Einen Reiter „Plan“ gibt es nicht (Nachtrag #214, unten).
4. **Ein Link je Zeile, Zurück an dieselbe Stelle.** Die ganze Zeile ist der eine Link, ohne Kennung. Wer von einem Tag zurückkommt (Link, Zurück-Taste, Blättern), steht wieder an dessen Zeile, mit Fokus.
5. **Jedes Element kann Alternativen tragen.** Eine Wahl hängt an Tag, Bewegung, Aufenthalt, Ort, Wahl oder Abschnitt des Wissens und erscheint dort immer gleich.
6. **Text folgt den Daten.** Was als Daten vorliegt (Anreise, Personen, Kennzahlen), steht nicht noch einmal im Lesetext. Hinweise zu einem Tag hängen am Tag. Der Lesetext eines Plans enthält nur die Begründungen.

## Nachtrag (2.11.2026, #214): eine Seitenordnung für alle Reisen

Bis #214 galt diese Ordnung nur für eine Reise mit gewähltem Plan, dem Baustein `tagesseiten` und ohne `darstellung.tiefe`; jede andere Reise, auch jede neue, bekam die alte Plan-Seite (Tageskästen in zwei Spalten, Unterkünfte als Liste, dieselbe Buchung an mehreren Stellen). Der Product Owner hat am 2.11.2026 entschieden: Es gibt eine Seitenordnung, der alte Zweig entfällt. Ob Pläne existieren, ob sie entschieden sind und welche Einstellungen die Reise hat, ändert nur, was am Tag steht (Marke „offen“, Vergleich an der Heimat), nie den Aufbau der Seite.

- **Zu Punkt 3:** Die Reiter hängen nicht an „Plan gewählt“. Jede Reise mit Tagen beginnt mit der Reise (Zeitachse in einer Spalte, je Tag eine Tagesseite); „Zu tun“ mit „Zu entscheiden“ und „Zu buchen“ gibt es immer. Den Reiter „Plan“ gibt es nicht mehr; ein alter Link `#plan` führt zur Reise.
- **Pläne vor der Entscheidung (Entscheidung 1):** Die Zeitachse zeigt den aktuellen Plan, mit der Marke „offen“ an Tagen mit offener Wahl. Der Vergleich ganzer Pläne bleibt erhalten und ist von der Reise aus erreichbar (`#plaene`, Baustein `varianten`). Ohne Pläne zeigt die Zeitachse die Tage der Reise selbst.
- **Baustein `tagesseiten` (Entscheidung 2):** entfällt als Schalter. Tagesseiten gehören zur Grundform Tag und gibt es immer. Eine ältere `reise.yaml`, die ihn nennt, bleibt gültig; der Eintrag ist ohne Wirkung.
- **`darstellung.tiefe` (Entscheidung 3):** steuert nur noch den Plan-Baum (Plan → Tag → Ort) unter dem Vergleich der Pläne, nicht die Startseite, die Tagesseiten oder den Zurück-Link.
- **`darstellung.plan_reiter` (Entscheidung 4):** ohne Wirkung. Die Rahmenabschnitte stehen im Reiter „Wissen“ unter „Über diesen Plan“.
- **Etappen (Entscheidung 5):** richten sich nach dem Plan der Zeitachse, auch bei offenen Plänen: Eine Etappe hat ihren Tag als Heimat, der Reiter „Etappen“ entfällt dann wie bei einem gewählten Plan.
- **Zu Punkt 1:** Die Heimat jedes Dings bestimmt eine Stelle (`heimat` in `engine/vorlage.html`); Tageskasten, Tagesseite und Listen fragen sie. Ein Aufenthalt an mehreren Tagen steht an seinem ersten Tag vollständig, an den übrigen als Zeile; eine Wahl an ihrem ersten Tag mit Vergleich, ein Reiseteil zur Wahl (Wahlstelle in der Route) am ersten Tag seiner Möglichkeiten; an einem Ort oder Abschnitt des Wissens steht eine Wahl als Zeile mit Link, wenn ihre Heimat anderswo ist. Nur die Heimat trägt die Kennung als Sprungziel; keine ID steht doppelt im DOM.

## Nachtrag (5.11.2026, #332): Tiefe der Kaskaden

Entschieden vom Product Owner am 5.11.2026 in Claude Code (drei Fragen, alle nach Empfehlung). Anlass: Eine Wahl zeigte ihre Optionen voll, eine Option zeigte ganze Tageskarten (`tagKarte` im Aufklapper), ein Tag zeigt seine Wahlen: Tag → Wahl → Option → Tag war möglich, und der einzige Schutz war ein stilles `null` ab Tiefe 3.

- **Zu Punkt 1: höchstens zwei Ebenen voll.** Ein Ding steht auf der Seite seiner Heimat (Ebene 1) und als Karte darauf (Ebene 2) vollständig. Was in einer Karte steckt, erscheint nur als Zeile mit einem Link zur Heimat.
- **Eine Option zeigt Tage nie als Karte**, sondern als Zeilen (`tagZeile`) mit Link zur Tagesseite. Der Aufklapper „Tage dieser Variante“ mit ganzen Tageskarten entfällt; Strecken und Unterkünfte einer Option bleiben Zeilen.
- **Ein Kreis wird sichtbar abgefangen.** Einen Kreis in den Elternbezügen meldet der Generator als Fehler (`pruefung.routen.eltern_kreis`, ADR-0007). Ist eine Kette trotzdem länger als `HEIMAT_TIEFE`, liefert `heimat()` `{kreis: true}` statt `null`; der Router zeigt dazu den Hinweis „verweist im Kreis oder zu tief auf andere Dinge“ mit dem Titel des Dings (Text `seite.kreis.hinweis`) und schreibt eine Warnung in die Konsole.
- Geprüft von `test_tiefenregel_option_zeigt_tage_nie_als_karte_und_ein_kreis_endet_sichtbar` in `engine/tests/test_design.py`.

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

- 5.11.2026 (#332, Schritt C): Nachtrag Tiefe: höchstens zwei Ebenen voll, eine Option zeigt Tage nur als Zeilen, ein Kreis endet sichtbar. `optionBlock` umgebaut, `heimat()` mit `HEIMAT_TIEFE` und `{kreis: true}`.
- 2.11.2026: Nachtrag #214: eine Seitenordnung für alle Reisen; der alte Zweig der Plan-Seite (`PLAN_DA`) ist entfernt, Baustein `tagesseiten` und `darstellung.plan_reiter` sind ohne Wirkung, `darstellung.tiefe` steuert nur noch den Plan-Baum (fünf Entscheidungen des Product Owners, `docs/specs/oberflaeche/eine-seitenordnung-214.md`). Tests: `engine/tests/test_eine_seitenordnung.py` (vier Fälle: ohne Pläne, Pläne offen, Plan fest, `tiefe`).
- 5.11.2026 (#332, Schritt B): Die Vorgaben der Tabelle stehen als Regel im Code: `heimat()` fragt `vorgabeEltern` je Grundform und nimmt die Seite des Elternelements; die Dichte wählt `dichteHier` nach dem Abstand, `zeigeDing` zeichnet das Ding in dieser Dichte (Bewegung, Ort, Buchung, Frage und Aufgabe haben dafür die Karte `dingKurzKarte`). Die Entscheidungen bleiben dieselben.
- 3.11.2026 (ADR-0007, #282): Die Tabelle der Heimaten ist die Tabelle der Vorgaben; die Heimat ist die Seite des Elternelements (`an:`), ein Aufenthalt ohne Tag hat sie auf der Ortsseite seines Orts (ohne Ortsseite wie bisher unter der Karte).
- 2.11.2026 (Epic #225, Entscheidung des Product Owners 3.11.2026): Die Karte hat einen eigenen Reiter „Karte“, sobald der Baustein Karte an ist, auch ohne den Baustein Varianten (#231). Der Start bleibt immer der Reiseüberblick (#214); der Reiter „Varianten“ bleibt nur für den Planvergleich. Aufenthalte ohne Tag haben ihre Heimat unter der Karte (#235); die Tageskarte auf der Tagesseite ist ein Ausschnitt, keine zweite Heimat.

- 29.10.2026: Abgleich (`docs/abgleich-2026-10-29.md`): Buchung und Unterkunft standen an mehreren Stellen vollständig (bei jedem Ding der Buchung, an jeder Nacht der Unterkunft, als Liste unter dem Plan), ein Link auf eine Buchung an einem Aufenthalt oder einer Fahrt hatte kein Ziel, die Liste der Entscheidungen im Plan zeigte Wahlen vollständig, die schon am Tag standen. Jetzt: Buchung nur an ihrem ersten Ding, Unterkunft nur an ihrer ersten Nacht, Aufenthalt und Fahrt haben ihren Tag als Heimat (`heimat`), Sammellisten zeigen Zeilen.
- 28.10.2026: Analyse, Konzept (Navigation A, Plantext auflösen, Alternativen an jedem Element) und grafische Ausarbeitung einzeln vom Product Owner freigegeben, gebaut in frieda-reist #84. Am selben Abend als ADR festgehalten.

## Nachtrag (6.11.2026, #370, ADR-0010): Heimat des Gegenstands

Der Gegenstand der Packliste (`G-…`) ist eine eigene Grundform. **Heimat** ist der Reiter „Packliste“ (Baustein `packliste`). An der Strecke, dem Aufenthalt, der Unterkunft oder dem Ort, an dem er hängt (`an:`, ADR-0007), steht er nur als Zeile „Mitnehmen“ mit einem Link zur Packliste; an einem Tag steht er nie (ein Tag ist kein Elternelement). Der Reiter steht nach „Wünsche“ und vor der Suche. Die Tabelle oben ist die der Vorgaben; die Zeile für den Gegenstand steht in `docs/design.md`.
- 8.11.2026 (#425, Entscheidung des Product Owners): Der Reiter „Karte“ entfällt. Die Karte steht nur unter „Reise“ und lässt sich dort auf Fenstergröße vergrößern (Schalter „Karte vergrößern“, Schließen mit Knopf und Esc); die alte Adresse `#karte` führt zur Reise. Aufenthalte ohne Tag sind eine Krücke: Ihre Heimat ist das Wissen (ADR-0007); nur wer dort keine Seite hat, steht am Ende der Reise. Der Nachtrag vom 2.11.2026 (#231) gilt damit nicht mehr; der Baustein Karte braucht weiter keinen Baustein Varianten.
- 9.11.2026 (#432, Vorgabe des Product Owners): Keine Sammelliste „Ohne Tag“ mehr in der Reise. Ein Aufenthalt ohne Tag, der eine Heimat anderswo hat (Abschnitt des Wissens über `an:`, Ortsseite), steht dort und als Punkt auf der Karte, in der Reise gar nicht (die Zeilen waren eine Sammelansicht ohne eigene Aufgabe, Punkt 2). Nur wer nirgends eine Seite hat, steht als Ersatz am Ende der Reise, zugeklappt unter „Noch ohne Platz (n)“ mit dem Hinweis, ihn einem Tag oder dem Wissen zuzuordnen: Ein Aufenthalt ohne Platz ist ein Mangel der Reise, kein Ort zum Sammeln. Der Konnektor sagt beim Anlegen eines Aufenthalts ohne `an:` dasselbe.
