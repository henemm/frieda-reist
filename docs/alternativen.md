# Alternativen: Standard für Wahlstellen, Optionen und Merkmale

Festgelegt am 26.10.2026.

## Begriffe

- **Wahlstelle** (`V-01`): eine Stelle im Plan mit mehreren Möglichkeiten. Wahlstellen gibt es auf jeder Ebene: ganze Route oder ein Reiseteil, eine Strecke, eine Unterkunft.
- **Option** (`V-01.a`): eine Möglichkeit an einer Wahlstelle. Sie hat einen Status mit Verlauf (`vorgeschlagen`, `favorisiert`, `gewaehlt`, `verworfen`, `ersetzt`).
- **Plan** (`P-A`): eine feste Kombination von Optionen über die ganze Reise (Reiter „Varianten“).
- **Bereich oder Art** einer Wahlstelle: Er bestimmt, welche Merkmale verglichen werden. Grundbereiche sind `unterkunft`, `strecke`, `route` und `allgemein`, dazu kommen Arten: `faehre`, `flug`, `bahn`, `bus`, `mietwagen`, `essen`, `erlebnis` und jede Art, die eine Reise selbst anlegt. Der Generator leitet ihn aus den Optionen ab (`unterkuenfte` ergibt `unterkunft`, `folge` ergibt `route`, `strecken` ergibt die gemeinsame `art` der Strecken, wenn die Grundliste sie kennt, sonst `strecke`). Mit `bereich:` an der Wahlstelle lässt er sich festlegen (nötig für `essen`, `erlebnis` und eigene Arten, weil sie keinen eigenen Baustein haben).
- **Merkmal**: ein Vergleichskriterium mit Wert, zum Beispiel Preis pro Nacht oder Frühstück.

## Merkmale: Mischform

1. **Grundliste** in `engine/merkmale.yaml`, je Bereich. Sie gilt für alle Reisen. Jedes Merkmal hat einen Namen und einen Typ (`text`, `geld`, `zahl`, `auswahl` mit `werte`). Es kann `veraenderlich` sein (dann braucht der Wert ein Prüfdatum). Dazu kommen Hinweise, wie Claude den Wert findet (`hilfe`) und wie Claude den Bestimmer fragt (`frage`). Merkmale mit `auto` berechnet der Generator (Gehzeit, Länge, Höhenmeter, Tage, Unterkünfte). Sie werden nie eingetragen.
2. **Reise** ergänzt die Liste in `plan/routen.yaml`:
   ```yaml
   merkmale:
     unterkunft:
       onsen: {name: Onsen im Haus, typ: auswahl, werte: [ja, nein, unklar]}
   ```
3. **Wahlstelle** ergänzt für sich allein, ebenfalls mit `merkmale:`.

Die Liste gilt für alle Mitreisenden gemeinsam. Vorlieben Einzelner stehen als Notiz oder unter Dafür/Dagegen, nicht als eigene Gewichtung.

## Arten statt eines festen Satzes von Bereichen

Reisen enthalten drei Grundformen von Dingen: **Aufenthalt** (Unterkunft, Essen, Erlebnis), **Bewegung** (Wanderweg, Fähre, Flug, Bahn, Bus, Mietwagen) und **Folge** (ein Abschnitt aus beidem, vom Tag bis zum Reiseteil). Gewählt wird auf drei Arten: eine von mehreren, mit oder ohne, wie lange. Die Art eines Dings bestimmt seine Merkmale. Eine Reise legt eine neue Art unter `merkmale:` an, ohne dass jemand programmiert:

```yaml
merkmale:
  restaurant:
    kueche: {name: Küche}
    preis: {name: Preis, typ: geld, veraenderlich: true}
wahlstellen:
  V-07:
    titel: Abendessen in Hohnstein
    art: planung
    frage: F-03
    bereich: restaurant
    an: [O-05]          # beliebige IDs: Tag, Strecke, Unterkunft, Ort oder Wahlstelle
    optionen:
      - {id: V-07.a, titel: Gasthaus, merkmale: {kueche: regional}}
```

`an:` nennt die IDs, an denen die Wahlstelle hängt (Tag, Strecke, Unterkunft, Ort, Wahlstelle). Tage, an denen die Wahlstelle als Übernachtung, Strecke oder `wahl:` eingetragen ist, werden weiter automatisch erkannt (`an`). Die ausdrücklichen IDs stehen im Ergebnis als `an_ids`.

## Werte eintragen

Bei Unterkünften stehen die Werte an der Unterkunft (`U-…`), damit sie auch ohne Wahlstelle sichtbar sind. In allen anderen Bereichen stehen sie an der Option.

```yaml
U-01:
  name: Hotel Born
  ort: O-02
  merkmale:
    preis: {wert: "179 €", geprueft: 2026-10-23, quelle: Ida}
    fruehstueck: inklusive          # Kurzform ohne Quelle und Datum
```

Bei Bewegungen stehen die Werte an der Strecke (`E-…`), bei allen anderen Arten an der Option. Steht ein Wert an der Option und an der Strecke, gilt der an der Option.

Preise und Öffnung gelten für ein Datum. Ein Wert kann deshalb eine Liste sein, jeder Eintrag mit `gilt` (ein Datum oder eine Liste von Daten). Ein Eintrag ohne `gilt` ist der Wert für alle übrigen Tage:

```yaml
U-01:
  merkmale:
    preis:
      - {wert: "179 €", gilt: 2027-02-25, geprueft: 2026-10-23, quelle: Ida}
      - {wert: "195 €", gilt: [2027-03-05, 2027-03-06], geprueft: 2026-10-26, quelle: Booking.com}
```

Im Ergebnis trägt der Wert dann `je_datum`; `routen.gilt_am(wert, "2027-03-05")` liefert den Eintrag für ein Datum. Ansichten ohne Datum zeigen den Wert ohne `gilt`, sonst den ersten.

Erlaubte Felder je Wert: `wert`, `quelle`, `geprueft` (Datum), `notiz`, `gilt` (Datum oder Liste von Daten). Ein fehlender Wert wird weggelassen, nicht leer eingetragen. Bei Widerspruch zwischen Quellen gilt `unklar` mit Notiz, sofern das Merkmal eine Auswahl ist. Unbekannte Merkmale, falsche Auswahlwerte und eingetragene `auto`-Merkmale sind Fehler. Die Seite wird dann nicht gebaut.

## Darstellung auf der Seite

Jede Wahlstelle mit mindestens zwei gültigen Optionen hat dasselbe **Wahl-Modul** (Designsystem, Issue #18), überall wo sie vorkommt: an der Nacht und am Weg eines Tages, beim Reiseteil im Plan und in der Liste der Entscheidungen.

- Der Knopf **„Alternativen vergleichen“** mit der Zahl der Möglichkeiten öffnet den Vergleich an Ort und Stelle. In der Liste der Entscheidungen ist er gleich offen.
- Verglichen werden höchstens 4 Möglichkeiten nebeneinander, auf dem Handy 2 (Richtwerte der Nielsen Norman Group für Vergleichstabellen). Vorgewählt sind die Option im Plan und die mit den meisten Werten; weitere wählt man über die Knöpfe darüber, die zeigen, wie viele Merkmale schon belegt sind (z. B. 3/7). Die Option im Plan bleibt im Vergleich, wenn eine weitere dazukommt.
- **„nur Unterschiede“** blendet Zeilen aus, in denen alle gezeigten Optionen denselben Wert haben. Zeilen ohne jeden Wert erscheinen nie.
- Ab 700 px Breite eine **Tabelle** (Optionen als Spalten, Merkmale als Zeilen, erste Spalte bleibt beim Wischen stehen), auf dem Handy **Karten** je Option mit Umschalter auf die Tabelle.
- Der Vergleich ist nur zum Lesen. Entschieden wird über Rückmeldung oder die Claude-App.
- Jeder Wert zeigt vorn nur den Wert; Notiz, Prüfdatum und Quelle stehen hinter dem „i“. „unklar“ ist hervorgehoben, ein fehlender Wert heißt „offen“.
- Werte je Datum: Im Tag und im Vergleich an einer Nacht gilt der Wert für dieses Datum (mit „am …“), in der Unterkunft und in Listen stehen alle Einträge untereinander („15.5.: 140 €“, „sonst: 120 €“).
- Veränderliche Werte ohne Prüfdatum tragen „ungeprüft“.
- An offenen Planungs-Wahlstellen steht bei jeder Option „Fehlt noch: …“.

## Ablauf, wenn eine neue Alternative dazukommt

Ida sagt zum Beispiel: „Es gibt noch eine Pension in Hohnstein.“

1. Claude ruft die Merkmalliste ab, in der Claude-App mit `merkmale` (zu `V-…`, zu einer Strecke `E-…` oder mit `bereich`), in Claude Code aus `engine/merkmale.yaml` und `routen.yaml`.
2. Claude **recherchiert zuerst selbst** (Website, Buchungsportal, Wanderführer) und trägt veränderliche Werte mit Prüfdatum ein.
3. Claude **fragt nur nach den Lücken**, gezielt nach dem Hinweis `frage`, zum Beispiel: „Hast du einen Preis? Ist Frühstück drin?“ In Claude Code geschieht das mit dem Fragewerkzeug (AskUserQuestion).
4. In der Claude-App geht der Vorschlag mit `alternative_vorschlagen` weiter: von Bestimmern als Auftrag, von Einbringern als Rückmeldung der Art `Ergänzung`. Beim Einarbeiten entsteht daraus eine neue Option mit Status `vorgeschlagen`. Fehlt die Wahlstelle, legt Claude sie an der genannten ID neu an (planung braucht eine F-Frage). Neue Merkmale aus dem Vorschlag kommen unter `merkmale:` der Wahlstelle oder der Reise.
5. Die Art der neuen Option ergibt sich aus der Stelle: an einer Wahlstelle aus ihrem `bereich`, an `U-…` Unterkunft, an `E-…` die Art der Strecke. Werte, die vom Datum abhängen, gehen als Liste mit `gilt` (ISO-Datum oder Liste von Daten), höchstens ein Eintrag ohne `gilt`, kein Datum doppelt; Fehler lehnt der Dienst sofort ab.
6. Ähnelt ein neues Merkmal einem vorhandenen („oeffnung“ neben „geoeffnet“, „kosten“ neben „preis“), meldet der Dienst einen Hinweis und legt die Paare unter `daten.doppelt` ab. Beim Einarbeiten gilt: Meint es dasselbe, kommt der Wert unter das vorhandene Merkmal, kein neues entsteht. Abgelehnt wird nichts, eigene Merkmale bleiben erlaubt.

## Empfehlung

Hat jede gültige Option die wichtigen Merkmale, darf Claude eine Option als `favorisiert` vorschlagen, immer mit `grund` im Verlauf. Ohne Begründung bricht der Bau ab. Entscheiden (`gewaehlt`, `verworfen`, `ersetzt`) können nur Bestimmer.
