# Alternativen: Standard für Wahlstellen, Optionen und Merkmale

Festgelegt am 26.10.2026.

## Begriffe

- **Wahlstelle** (`V-01`): eine Stelle im Plan mit mehreren Möglichkeiten. Wahlstellen gibt es auf jeder Ebene: ganze Route oder ein Reiseteil, eine Strecke, eine Unterkunft.
- **Option** (`V-01.a`): eine Möglichkeit an einer Wahlstelle. Sie hat einen Status mit Verlauf (`vorgeschlagen`, `favorisiert`, `gewaehlt`, `verworfen`, `ersetzt`).
- **Plan** (`P-A`): eine feste Kombination von Optionen über die ganze Reise (Reiter „Varianten“).
- **Art** der Dinge, zwischen denen eine Wahlstelle wählt (Feld `bereich:`): Sie bestimmt, welche Merkmale verglichen werden. Arten definiert allein die Reise in `plan/arten.yaml` (`docs/ontologie.md`). Fehlt `bereich:`, leitet der Generator die Art aus den Optionen ab: die Art der ersten Unterkunft, die gemeinsame Art der Strecken, die eine Folge-Art der Reise; sonst `allgemein` ohne Merkmale.
- **Merkmal**: ein Vergleichskriterium mit Wert, zum Beispiel Preis pro Nacht oder Frühstück.

## Merkmale: je Reise, je Art

Seit dem 28.10.2026 (ADR-0001, Paket O-1) gibt es keine Grundliste in der Software mehr. Jede Reise legt ihre Arten und deren Merkmale in `plan/arten.yaml` fest, entwickelt im Gespräch im AI-Client (Aufbau, Felder, Stufen, Zuordnung: `docs/ontologie.md`). Eine **Wahlstelle** ergänzt für sich allein mit `merkmale:` oder ändert die Stufe eines Merkmals ihrer Art (`merkmale: {abendessen: {stufe: empfohlen}}`). Nur `pflicht` und `empfohlen` erscheinen als „Fehlt noch“, zählen im Vergleich („3/7“), werden gemahnt und vom Wächter geprüft; `angeboten` wird nur gezeigt, wenn ein Wert da ist; `aus` gilt nicht.

Die Merkmale einer Art gelten für alle Mitreisenden gemeinsam. Vorlieben Einzelner stehen als Notiz oder unter Dafür/Dagegen, nicht als eigene Gewichtung.

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
    an: [O-05]          # beliebige IDs: Tag, Strecke, Unterkunft, Ort, Wahlstelle oder Abschnitt (W-…)
    optionen:
      - {id: V-07.a, titel: Gasthaus, merkmale: {kueche: regional}}
```

`an:` nennt die IDs, an denen die Wahlstelle hängt (Tag, Strecke, Unterkunft, Ort, Wahlstelle oder ein Abschnitt des Wissens `W-…`, etwa Essen oder Ausflug; seit 28.10.2026 kann so jedes Element Alternativen tragen). Die Seite zeigt die Wahlstelle an diesem Element (`docs/design.md`, Seitenordnung). Tage, an denen die Wahlstelle als Übernachtung, Strecke oder `wahl:` eingetragen ist, werden weiter automatisch erkannt (`an`). Die ausdrücklichen IDs stehen im Ergebnis als `an_ids`.

## Werte eintragen

Bei Unterkünften stehen die Werte an der Unterkunft (`U-…`), damit sie auch ohne Wahlstelle sichtbar sind. In allen anderen Bereichen stehen sie an der Option.

```yaml
U-01:
  name: Hotel am Elbufer
  ort: O-02
  merkmale:
    preis: {wert: "120 €", geprueft: 2026-10-23, quelle: Ida}
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

Seit 29.10.2026 (ADR-0001, O-3) trägt der AI-Client Werte mit `wert_eintragen` direkt ein (`docs/konnektor.md`): mit Herkunft, bei veränderlichen Merkmalen mit Prüfdatum; der Schreibweg ersetzt den Wert für dieselben Tage und hält den alten im Verlauf (Repo-Geschichte). Die Kurzform ohne Quelle gibt es für neue Werte nicht mehr.

Erlaubte Felder je Wert: `wert`, `quelle`, `geprueft` (Datum), `notiz`, `gilt` (Datum oder Liste von Daten). Ein fehlender Wert wird weggelassen, nicht leer eingetragen. Bei Widerspruch zwischen Quellen gilt `unklar` mit Notiz, sofern das Merkmal eine Auswahl ist. Unbekannte Merkmale, falsche Auswahlwerte und eingetragene `auto`-Merkmale sind Fehler. Die Seite wird dann nicht gebaut.

## Regeln zwischen Optionen

Manche Optionen gehen nur zusammen mit einer anderen (der Bus fährt nur, wenn das Gepäck in der Pension bleibt) oder nie zusammen mit ihr. Das steht an der Option:

```yaml
- id: V-01.c
  titel: "Mit dem Bus zurück"
  erfordert: [V-03.a]       # geht nur, wenn V-03.a im Plan steht
  schliesst_aus: [V-02.b]   # nie zusammen mit V-02.b; gilt in beide Richtungen
```

- Ziele sind Optionen anderer Wahlstellen. Unbekannte Optionen, Ziele in derselben Wahlstelle, zwei Optionen derselben Wahlstelle unter `erfordert` und dasselbe Ziel unter beiden Feldern sind Fehler.
- Verletzt der aktuelle Plan oder ein benannter Plan (`P-…`) eine Regel, steht das bei „Geht noch nicht auf“ (Bezug `plan`). Gezählt werden nur Optionen, die der Plan wirklich erreicht: Eine Wahlstelle in einer Variante, die nicht im Plan ist, zählt nicht mit, auch wenn sie eine Auswahl hat.
- Setzt eine gültige Option eine verworfene voraus, gibt es einen Hinweis an der Option.
- Die Seite zeigt „Setzt voraus“ und „Schließt aus“ an der Option und als Zeilen im Vergleich, jeweils mit „im Plan“, „nicht im Plan“ oder „verworfen“. Die Claude-App nennt beides in der Option und gibt beim Entscheiden Hinweise (wählen, obwohl die Voraussetzung fehlt; verwerfen, was eine Option im Plan voraussetzt). Verhindert wird nichts: Entscheiden bleibt Sache der Organisator:innen.

## Anschluss (berechnet)

Bei Reiseteilen (Bereich `route`) berechnet der Generator das Merkmal **Anschluss**: Passt die Option an ihre Stelle im aktuellen Plan? Verglichen wird, wo der Plan davor endet, mit dem Anfang ihres ersten Tages (Start der ersten Strecke, sonst Ort der Nacht), und wo sie endet, mit dem, was danach kommt (nächster Tag oder Reiseende). Werte: „nahtlos“, „Lücke am Anfang: A → B“, „Lücke am Ende: A → B“, bei einer Option ohne Tage „Lücke: A → B“. Hinter dem „i“ steht, wovon die Rechnung ausgeht. Die Lücken sind dieselben, die der Plan als Warnung meldet, sobald die Option gilt; so sieht man vor der Entscheidung, welche Variante einen fehlenden Weg mitbringt. Optionen ohne `folge` (noch nicht ausgearbeitet) und Wahlstellen außerhalb des aktuellen Plans bekommen keinen Wert.

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
- Eine berechnete Lücke (Anschluss) ist hervorgehoben wie „unklar“.
- An offenen Planungs-Wahlstellen steht bei jeder Option „Fehlt noch: …“.

## Ablauf, wenn eine neue Alternative dazukommt

Ida sagt zum Beispiel: „Es gibt noch eine Pension in Hohnstein.“

1. Claude ruft die Merkmalliste der Art ab, in der Claude-App mit `merkmale` (zu `V-…`, `U-…`, zu einer Strecke `E-…` oder mit `bereich`, einer Art der Reise), sonst aus `plan/arten.yaml` der Reise.
2. Claude **recherchiert zuerst selbst** (Website, Buchungsportal, Wanderführer) und trägt veränderliche Werte mit Prüfdatum ein.
3. Claude **fragt nur nach den Lücken**, gezielt nach dem Hinweis `frage`, zum Beispiel: „Hast du einen Preis? Ist Frühstück drin?“ In Claude Code geschieht das mit dem Fragewerkzeug (AskUserQuestion).
4. In der Claude-App legt Claude die Alternative direkt an (seit 29.10.2026, ADR-0001 O-3): die Unterkunft oder Strecke mit `ding_anlegen` (Herkunft Pflicht, Merkmale gleich mit), dann `option_anlegen` an der Wahlstelle; es entsteht eine Option mit Status `vorgeschlagen` und Verlauf (Datum, Person, Grund). Fehlt die Wahlstelle, legt `wahlstelle_anlegen` sie an (planung bekommt ihre F-Frage mit). Ein Merkmal, das die Art noch nicht hat, legt ein:e Organisator:in erst mit `merkmal_definieren` an (Mitwirkende schlagen es damit vor); der Konnektor nennt ähnliche vorhandene Merkmale (`geoeffnet` statt `oeffnung`).
5. Die Art der neuen Option ergibt sich aus der Stelle: an einer Wahlstelle aus ihrem `bereich`, an `U-…` Unterkunft, an `E-…` die Art der Strecke. Werte, die vom Datum abhängen, gehen als Liste mit `gilt` (ISO-Datum oder Liste von Daten), höchstens ein Eintrag ohne `gilt`, kein Datum doppelt; Fehler lehnt der Dienst sofort ab.
6. Ähnelt ein genanntes Merkmal einem vorhandenen („oeffnung“ neben „geoeffnet“, „preise“ neben „preis“), nennt der Konnektor das vorhandene und trägt nichts ein; der Wert kommt dann unter das vorhandene Merkmal. Ein wirklich neues Merkmal entsteht nur über `merkmal_definieren` an der Art (kein stilles Wachsen der Merkmale).

## Empfehlung

Hat jede gültige Option die wichtigen Merkmale, darf Claude eine Option als `favorisiert` vorschlagen, immer mit `grund` im Verlauf. Ohne Begründung bricht der Bau ab. Entscheiden (`gewaehlt`, `verworfen`, `ersetzt`) können nur Organisator:innen.
