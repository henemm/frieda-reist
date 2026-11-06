# Kontext und Analyse: instabiler Test der Etappenlegende (#369)

## Request Summary

`engine/tests/test_karte_legende.py::test_legende_nach_arten[390-chromium]` schlug einmal in der CI an Zeile 79 fehl (`all(x["hoch"] >= 44 ...)` bzw. Breite): Die Zeilen der Ebenenwahl hatten `breit: 0`. Derselbe Stand war im Parallellauf grün, lokal dreimal grün, nach `gh run rerun --failed` grün.

## Analysis

- **Fundstelle:** `engine/tests/seiten_karte_legende.mjs`, Zeilen 24 und 25: Der Klick auf den Schalter der Ebenenwahl und gleich danach `imFenster(".ekarte .leaflet-control-layers-list label")`, ohne Wartepunkt dazwischen.
- **Ursache (Vermutung, eine Messung schlug nur einmal an):** Leaflet klappt die Liste über die Klasse `leaflet-control-layers-expanded` auf; erst dann haben die Zeilen eine Größe. Auf einem langsamen Läufer wird `getBoundingClientRect()` vor dem Layout gelesen, die Zeilen sind da, aber Breite und Höhe sind 0.
- **Warum nur der schmale Lauf (390, Touch) aufgefallen ist:** Dort gilt zusätzlich die Tippfläche von 44 px (`pointer: coarse`), und die Zeilen messen sich erst nach dem Aufklappen; bei 1300 wird nur `innen` geprüft, was bei Breite 0 nicht scheitert.
- **Software ist nicht betroffen:** Die Seite zeichnet die Legende richtig; nur der Zeitpunkt der Messung im Test ist offen.

## Lösung

Nach dem Klick wartet das Skript, bis die Liste aufgeklappt ist und mindestens eine Zeile eine Breite über 0 hat (`waitForFunction`, Zeitgrenze 5 s, bei Zeitüberschreitung weiter wie bisher, damit die Fehlermeldung des Tests die Lage zeigt statt eines Skriptabbruchs). Keine feste Wartezeit, keine Änderung an Seite oder Vorlage.

## Risiken

- Zeigt die Seite wirklich keine Ebenen, wartet das Skript 5 s und der Test meldet wie bisher „ebenen leer“ (kein falsches Grün).
- Die Ursache ist eine Vermutung; hält der Test danach trotzdem einmal an, steht in der Meldung dank der Messung nach dem Warten die echte Lage.
