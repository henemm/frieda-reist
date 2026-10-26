# Alternativen: Standard für Wahlstellen, Optionen und Merkmale

Festgelegt am 26.10.2026.

## Begriffe

- **Wahlstelle** (`V-01`): eine Stelle im Plan mit mehreren Möglichkeiten. Wahlstellen gibt es auf jeder Ebene: ganze Route oder ein Reiseteil, eine Strecke, eine Unterkunft.
- **Option** (`V-01.a`): eine Möglichkeit an einer Wahlstelle. Sie hat einen Status mit Verlauf (`vorgeschlagen`, `favorisiert`, `gewaehlt`, `verworfen`, `ersetzt`).
- **Plan** (`P-A`): eine feste Kombination von Optionen über die ganze Reise (Reiter „Varianten“).
- **Bereich** einer Wahlstelle: `unterkunft`, `strecke`, `route` oder `allgemein`. Der Generator leitet ihn aus den Optionen ab (`unterkuenfte`, `strecken` oder `folge`). Mit `bereich:` an der Wahlstelle lässt er sich festlegen.
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

Erlaubte Felder je Wert: `wert`, `quelle`, `geprueft` (Datum), `notiz`. Ein fehlender Wert wird weggelassen, nicht leer eingetragen. Bei Widerspruch zwischen Quellen gilt `unklar` mit Notiz, sofern das Merkmal eine Auswahl ist. Unbekannte Merkmale, falsche Auswahlwerte und eingetragene `auto`-Merkmale sind Fehler. Die Seite wird dann nicht gebaut.

## Darstellung auf der Seite

- Ab 700 px Breite (Tablet, Desktop) zeigt eine Wahlstelle mit mindestens zwei gültigen Optionen eine **Vergleichstabelle**: Optionen als Spalten, Merkmale als Zeilen. Es erscheinen nur Merkmale, die bei mindestens einer Option einen Wert haben.
- Auf dem Handy stehen die Merkmale als **Karte** in jeder Option.
- Veränderliche Werte ohne Prüfdatum tragen „ungeprüft“.
- An offenen Planungs-Wahlstellen steht bei jeder Option „Fehlt noch: …“.

## Ablauf, wenn eine neue Alternative dazukommt

Ida sagt zum Beispiel: „Es gibt noch eine Pension in Hohnstein.“

1. Claude ruft die Merkmalliste ab, in der Claude-App mit `merkmale` (zu `V-…` oder mit `bereich`), in Claude Code aus `engine/merkmale.yaml` und `routen.yaml`.
2. Claude **recherchiert zuerst selbst** (Website, Buchungsportal, Wanderführer) und trägt veränderliche Werte mit Prüfdatum ein.
3. Claude **fragt nur nach den Lücken**, gezielt nach dem Hinweis `frage`, zum Beispiel: „Hast du einen Preis? Ist Frühstück drin?“ In Claude Code geschieht das mit dem Fragewerkzeug (AskUserQuestion).
4. In der Claude-App geht der Vorschlag mit `alternative_vorschlagen` weiter: von Bestimmern als Auftrag, von Einbringern als Rückmeldung der Art `Ergänzung`. Beim Einarbeiten entsteht daraus eine neue Option mit Status `vorgeschlagen`. Fehlt die Wahlstelle, legt Claude sie an der genannten ID neu an (planung braucht eine F-Frage). Neue Merkmale aus dem Vorschlag kommen unter `merkmale:` der Wahlstelle oder der Reise.

## Empfehlung

Hat jede gültige Option die wichtigen Merkmale, darf Claude eine Option als `favorisiert` vorschlagen, immer mit `grund` im Verlauf. Ohne Begründung bricht der Bau ab. Entscheiden (`gewaehlt`, `verworfen`, `ersetzt`) können nur Bestimmer.
