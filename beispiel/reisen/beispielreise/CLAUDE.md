# Beispielreise – Malerweg in vier Tagen

Erfundene Reise als Beispiel und Testdaten für den Generator. Die Gegend (Dresden, Sächsische Schweiz, Malerweg) ist echt; Reisende, Unterkünfte, Preise und Kennzahlen der Etappen sind erfunden oder geschätzt und als Beispielwerte markiert.

## Eckdaten

- Do 13.5. bis So 16.5.2027, An- und Abreise mit dem Zug über Dresden.
- 2 Personen: Ida (Rolle bestimmer) und Karl (Rolle einbringer), siehe `reise.yaml`.
- Tag 1 Stadttag in Dresden, Tage 2 bis 4 Wandern auf Abschnitten des Malerwegs: Stadt Wehlen → Hohnstein → Altendorf → Bad Schandau oder Lichtenhainer Wasserfall.
- Ohne Auto; S-Bahn und Kirnitzschtalbahn.

## Vorlieben

- Kurze Wandertage (höchstens etwa 4 Stunden), lieber Aussicht als Strecke.
- Karl möchte einmal mit der Kirnitzschtalbahn fahren (Wunsch, keine Entscheidung).

## Entscheidungen

- 20.10.2026 (Ida): Unterkunft in Hohnstein ist die Pension Burgblick (V-03.a); der Gasthof Polenztal ist verworfen, weil der Weg am Morgen erst wieder hinaufführt (F-02).

Offen bleibt der letzte Tag (V-01, F-01). Karl favorisiert Plan B; entschieden ist das erst, wenn Ida wählt.

## Dateien

- `reise.yaml` – Eckdaten, Status, Personen, Bausteine
- `reise.json` – Zuordnung der Überschriften zu IDs
- `plan/routen.yaml` – Tage, Strecken, Unterkünfte, Wahlstellen, Pläne P-A und P-B
- `plan/karte.yaml`, `plan/punkte.yaml` – schematische Karte und Punkte je Etappe
- `inhalt/` – Etappen, Unterkünfte, Wissen, Orte
- `medien/gpx/` – von Hand gesetzte, schematische Tracks; `medien/skizze-felsen.png` und `medien/icon.svg` sind eigene Zeichnungen
