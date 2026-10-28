# Beispielreise

Dieser Ordner enthält eine erfundene, aber in einer echten Gegend spielende Reise: ein Stadttag in Dresden und drei Wandertage auf dem Malerweg in der Sächsischen Schweiz. Sie dient zwei Zwecken:

- **Vorführung:** So sieht eine fertig geplante Reise aus, mit Tagesplan, Etappen, Karte, Varianten, offenen Fragen und Wissen.
- **Testdaten:** Die Beispielreise nutzt die wichtigsten Teile des Generators (Status und Personen, Wahlstellen für Planung und Unterwegs, benannte Pläne, GPX-Tracks, Kartenpunkte, Fußnoten, Bilder, Ortsseiten).

Reisende, Unterkünfte, Preise und die Kennzahlen der Etappen sind erfunden oder aus schematischen Tracks geschätzt und als Beispielwerte gekennzeichnet. Feste Tatsachen (etwa zur Basteibrücke oder zur Kirnitzschtalbahn) nennen ihre Quelle in einer Fußnote. Die GPX-Tracks sind von Hand gesetzt, mit wenigen Punkten: Sie zeigen den ungefähren Verlauf und taugen nicht zum Navigieren.

## Bauen

Aus dem Hauptordner des Projekts:

```
engine/.venv/bin/python engine/bauen.py --reisen beispiel/reisen --ziel /tmp/bsp-dist beispielreise
```

Danach `/tmp/bsp-dist/beispielreise/index.html` im Browser öffnen, am besten über einen kleinen Webserver (z. B. `python3 -m http.server` im Ordner `/tmp/bsp-dist/beispielreise`), damit der Service Worker läuft.

Die Beispielreise liegt bewusst nicht unter `reisen/`, damit sie nicht zusammen mit echten Reisen veröffentlicht wird.

## Aufbau

```
reisen/beispielreise/
  reise.yaml          Eckdaten, Status mit Verlauf, Personen mit Rollen, Bausteine
  reise.json          welche Überschrift welche ID bekommt
  CLAUDE.md           Eckdaten und Entscheidungen der Reise
  offene-fragen.md    offene Fragen (F-01 …)
  plan/               Plan-Text, Routenmodell, Karte, Kartenpunkte
  inhalt/             Etappen, Unterkünfte, Wissen, Ortsseiten
  medien/             Tracks, Skizze, App-Symbol
```

## Was ohne Grundkarte fehlt

Das Beispiel enthält keine Offline-Grundkarte (PMTiles), damit es klein bleibt. Die Übersichtskarte ist deshalb schematisch. Die Karten je Etappe und die Karten in den Wissens-Abschnitten erscheinen nur mit Grundkarte; die Punkte dafür sind trotzdem eingetragen und werden beim Bauen geprüft.
