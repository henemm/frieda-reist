# Die Reise-Ontologie: Grundformen in der Software, Arten in der Reise

Kern: `docs/adr/0001-kern.md`. Dieses Dokument sagt, was die Software über eine Reise weiß (die Grundformen und die Form eines Merkmals) und wie eine Reise ihre eigenen Arten und Merkmale festlegt (`plan/arten.yaml`). Es ersetzt die „Mischform“ mit der Grundliste `engine/merkmale.yaml` (26.10.–28.10.2026), siehe Verlauf unten. Herkunft der Begriffe: Recherche „Grundformen in der Software, Arten in der Reise“ (28.10.2026; schema.org Trip/Accommodation/PropertyValue, Transmodel, GTFS, PROV-O, Eurostat/IRTS, FHIR-Profile), gelesen gegen die zwei laufenden Reisen.

## Grundformen

Die Software kennt genau diese Dinge. Sie gelten für jede Art von Reise (Hüttentour, Städtereise, Familienbesuch, Bahnreise, Kreuzfahrt, Geschäftsreise).

| Grundform | Was es ist | ID heute | Datei |
|---|---|---|---|
| **Reise** | Rahmen: Titel, Zeitraum, Personen mit Rollen, Status, Bausteine, Regeln | – | `reise.yaml` |
| **Ort** | ein Punkt oder Gebiet, an dem man ist oder das man passiert | `O-` | `plan/routen.yaml` |
| **Aufenthalt** | an einem Ort sein: Übernachtung (heute `U-` und `nacht`), künftig auch ohne Nacht (Essen, Besichtigung) | `U-` | `plan/routen.yaml` |
| **Bewegung** | von Ort zu Ort: Wanderung, Bahn, Bus, Fähre, Flug, Mietwagen … | `E-` | `plan/routen.yaml` |
| **Folge** | ein geordneter Abschnitt aus Aufenthalten und Bewegungen: Tag, Reiseteil, benannter Plan | `T-`, `P-` | `plan/routen.yaml` |
| **Wahl** | Wahlstelle mit Optionen (eine von mehreren, mit oder ohne, wie lange), Verlauf mit Person, Datum, Grund | `V-`, `V-01.a` | `plan/routen.yaml` |
| **Aussage** | ein Merkmal eines Dings: Wert, Herkunft (`quelle`), Prüfdatum (`geprueft`), Gültigkeit (`gilt`), Notiz | am Ding | `plan/routen.yaml` |
| **Offenes** | Frage, Aufgabe, Wunsch, Rückmeldung, jeweils an eine ID gehängt | `F-`, `AG-`, `R-` | `offene-fragen.md`, Ablage |
| **Wissen** | Fließtext mit Herkunft: Geschichte, Praxis, Quellen | `W-` | `inhalt/` |

Jedes Ding hat einen **Kern**: feste ID (nie neu vergeben, nie gelöscht), Grundform, **Art** (von der Reise vergeben), Titel, Herkunft, Zeit- oder Ortsbezug, Verweise auf andere Dinge, Merkmale, Verlauf.

## Die Art eines Dings

Welche Arten es gibt (Hotel, Refugi, Ryokan, Nachtfähre, Wanderung, Shinkansen, Reiseteil …), weiß nur die Reise. Sie stehen in **`reisen/<reise>/plan/arten.yaml`**, entwickelt im Gespräch im AI-Client, und werden dort immer wieder geschärft (Art anlegen, Merkmal ergeben, umbenennen, zusammenführen, abschalten; vorschlagen dürfen Mitwirkende, festlegen Organisator:innen, mit Verlauf). Seit 29.10.2026 geht das über die Konnektor-Werkzeuge `art_definieren` und `merkmal_definieren` direkt in die Datei (`docs/konnektor.md`, „Ontologie im Gespräch“; Schreibweg `engine/schreiben.py`); der Verlauf ist die Geschichte des Repos, ein Commit je Änderung mit Person und Grund. Zusammenführen zweier Merkmale (Werte umhängen) folgt mit dem Schreiben von Werten. Die Software liefert keine Liste, weder als Pflicht noch als Vorschlag. Der AI-Client darf Standards wie schema.org oder OpenStreetMap als Wissen nutzen, wenn er Merkmale vorschlägt. Die Beispielreise der Software hat eine Anschauungs-`arten.yaml` (erfundene Reise, kein Katalog). Arten einer früheren Reise derselben Person darf der AI-Client nur auf ausdrückliche Nachfrage als Kopie übernehmen (Product Owner, 28.10.2026).

```yaml
# reisen/<reise>/plan/arten.yaml – Arten und Merkmale dieser Reise (docs/ontologie.md)
arten:
  hotel:
    grundform: aufenthalt          # aufenthalt | bewegung | folge
    name: Hotel                    # Anzeige
    farbe: blau                    # Darstellung auf Karte, Legende, Vergleich (Palette der Seite, siehe unten)
    merkmale:
      preis:       {name: Preis pro Nacht, typ: geld, veraenderlich: true, stufe: empfohlen,
                    hilfe: "Website des Hauses; für das Reisedatum und zwei Personen", frage: "Hast du einen Preis?"}
      geoeffnet:   {name: Geöffnet am Reisedatum, typ: auswahl, werte: [ja, nein, unklar], veraenderlich: true, stufe: pflicht}
      fruehstueck: {name: Frühstück, typ: auswahl, werte: [inklusive, gegen Aufpreis, keins, unklar], veraenderlich: true}
  refugi:
    grundform: aufenthalt
    name: Refugi
    farbe: gruen
    merkmale:
      abendessen:  {name: Abendessen, typ: auswahl, werte: [im Haus mit Vorbestellung, im Ort, keins, unklar], stufe: empfohlen}
      geoeffnet:   {name: Geöffnet am Reisedatum, typ: auswahl, werte: [ja, nein, unklar], veraenderlich: true, stufe: pflicht}
  wandern:
    grundform: bewegung
    name: Wanderung
    merkmale:
      gehzeit:     {name: Gehzeit, auto: gehzeit}
      laenge:      {name: Länge, auto: laenge}
      hoehenmeter: {name: Höhenmeter, auto: hoehenmeter}
      schwierigkeit: {name: Schwierigkeit, typ: text, hilfe: "Wanderführer; Kettenstellen, Trittsicherheit"}
  bus:
    grundform: bewegung
    name: Bus
    merkmale:
      dauer:       {name: Dauer, typ: text, veraenderlich: true}
      verkehrt:    {name: Fährt, typ: text, veraenderlich: true, hilfe: "Fahrplan; nicht jede Linie fährt täglich"}
  reiseteil:
    grundform: folge
    name: Reiseteil
    merkmale:
      tage:        {name: Tage, auto: tage}
      unterkuenfte: {name: Unterkünfte, auto: unterkuenfte}
      anschluss:   {name: Anschluss, auto: anschluss}
      kosten:      {name: Kosten grob, typ: geld, veraenderlich: true, stufe: angeboten}
```

**Zuordnung eines Dings zu seiner Art:**

- Unterkunft (`U-…`) und Nacht (`nacht: {typ: …}`): Feld `art:`; fehlt es, wird `typ` als Art gelesen (klein geschrieben, Umlaute und Leerzeichen zu `ae`/`_`: `Refugi` → `refugi`, `Shukubō` → `shukubo`). Die Art muss in `arten.yaml` stehen, sonst bricht der Bau mit dem Hinweis ab, sie im Gespräch anzulegen.
- Strecke (`E-…`): Feld `art:` wie bisher (`wandern`, `bahn`, `faehre` …). Eine Liste mehrerer Arten gilt als Art `kombiniert`, die die Reise definiert.
- Wahlstelle (`V-…`): Feld `art:` (bis 28.10.2026 `bereich:`, wird weiter gelesen). Fehlt es, kommt die Art aus den Optionen: Unterkünfte → die Art der ersten Unterkunft, Strecken → die gemeinsame Art der Strecken, Folge → die eine Art der Grundform `folge`, wenn die Reise genau eine hat, sonst keine Merkmale.
- Jede Art gehört zu genau einer Grundform. Berechnete Merkmale (`auto`) gibt es je Grundform: Bewegung `gehzeit`, `laenge`, `hoehenmeter`; Folge `tage`, `gehzeit`, `unterkuenfte`, `anschluss`. Sie sind Kennzahlen der Grundform, kein Katalog; die Reise entscheidet, ob und unter welchem Namen sie erscheinen.

## Die Form eines Merkmals

Ein Merkmal ist eine Definition in `arten.yaml` und ein Wert am Ding.

| Feld der Definition | Bedeutung |
|---|---|
| `name` | Anzeige |
| `typ` | `text` (Vorgabe), `geld`, `zahl`, `auswahl` (mit `werte`) |
| `veraenderlich` | der Wert braucht ein Prüfdatum; ohne steht „ungeprüft“ daneben, ab Status `fest` eine Mahnung, der Wächter meldet alte Prüfdaten |
| `stufe` | `pflicht`, `empfohlen` (Vorgabe), `angeboten`, `aus`. Pflicht und empfohlen zählen als „Fehlt noch“ und im Vergleichszähler; Pflicht fehlt ab Status `planung` als Mahnung, empfohlen ab `fest`; angeboten erscheint nur mit Wert; aus gilt nicht. Eine Wahlstelle kann die Stufe für sich ändern (`merkmale: {abendessen: {stufe: empfohlen}}`) |
| `auto` | berechnet, nie eingetragen (siehe Grundformen) |
| `hilfe`, `frage` | wie der AI-Client den Wert recherchiert und wonach er fragt |
| `einheit` | Anzeige hinter Zahlen |
| `auch` | weitere Namen, unter denen dasselbe gemeint ist (Zuordnung ähnlicher Vorschläge innerhalb der Reise) |

Ein **Wert** am Ding: `{wert, quelle, geprueft, notiz, gilt}`; mehrere Werte je Datum als Liste mit `gilt` (`docs/alternativen.md`). Ein Wert ohne Herkunft wird abgelehnt, seit der Konnektor direkt schreibt (Paket O-3, `wert_eintragen`); Bestandswerte ohne Quelle bleiben lesbar.

Die Software prüft nur die Form: bekannte Felder, erlaubte Typen und Stufen, Auswahlwerte, Prüfdatum bei Veränderlichem, dass jede Art genau eine Grundform hat und jedes Ding eine bekannte Art. Ob „Frühstück“ für ein Refugi sinnvoll ist, entscheidet die Reise.

## Lesetext und seine Gliederung

Zu einem Ding gehört oft ein **Lesetext**: der Text am Anfang einer Etappe (Abschnitt „Zusammenfassung“, auf der Seite die Ebene „Der Weg“, `docs/design.md`). Er ist Wissen (Grundform), hängt aber an einer Bewegung. Wie er aufgebaut ist, legt die Reise **je Art** fest, denn eine Wanderung erzählt man anders als eine Bahnfahrt oder einen Stadttag. Die Software kennt nur die Form einer Gliederung, keine Rubriken (ADR-0001, kein Katalog).

```yaml
# plan/arten.yaml
arten:
  wandern:
    grundform: bewegung
    name: Wanderung
    lesetext:                      # Rubriken in ihrer Reihenfolge
      charakter: {name: Charakter, hilfe: "Wie sich der Tag anfühlt: Landschaft, Art des Wegs, Stimmung"}
      verlauf:   {name: Verlauf, hilfe: "Der Weg in groben Zügen, keine Wegbeschreibung Punkt für Punkt"}
      ankommen:  {name: Ankommen, hilfe: "Wann man ankommt und was am Ziel bleibt"}
```

- **Form im Text:** je Rubrik ein Absatz, der mit ihrem Namen als fettem Stichwort beginnt (`**Charakter.** …`). Rubriken ohne Inhalt fallen weg; die Reihenfolge der Datei ist die Lesereihenfolge. Die Herkunft steht wie bisher darunter.
- **Prüfung:** Die Software prüft die Form der Gliederung (Schlüssel, Name, bekannte Felder `name` und `hilfe`, kein Name doppelt). Beim Bauen ist ein Stichwort im Lesetext, das keine Rubrik der Art der Strecke ist, ein Hinweis (kein Fehler). Ohne Gliederung der Art wird nichts geprüft.
- **Konnektor:** `zeige E-…` nennt die Gliederung der Art mit der Hilfe je Rubrik, damit der AI-Client den Text in diesem Aufbau schreibt. Ändert der Schreibweg eine Art (`art_definieren`), bleibt ihre Gliederung erhalten; die Gliederung selbst pflegt der Konnektor noch nicht (Schritt nach #91).
- **Herkunft des Aufbaus** (Recherche 29.10.2026): Wanderführer und Tourenportale trennen den erzählenden Text von der Wegbeschreibung. Rother stellt jeder Tour Kopfdaten (Ausgangspunkt, Anforderungen, Einkehr, Varianten) und eine kurze Einleitung voran, dann folgt die Beschreibung; Cicerone nennt je Etappe Kennzahlen und Verpflegung vor dem Text. Outdooractive unterscheidet Kurzbeschreibung (Teaser, 50–300 Zeichen), Beschreibung (Erlebnis, Charakter und Sehenswertes, 900–2000 Zeichen) und Wegbeschreibung (so genau, dass man danach gehen kann), dazu Tipp, Sicherheitshinweise und Ausrüstung als eigene Felder. Wikivoyage gibt für Reiserouten ein Grundgerüst vor, von dem man weglässt, was nicht passt. Daraus der Grundaufbau Kurzzeile, Charakter, Verlauf in groben Zügen, Höhepunkte, Anforderungen, Ankommen; was eine Reise darüber hinaus wichtig findet (etwa „Im Vergleich zu gestern“, „Was andere sagen“, „Jahreszeit“), ergänzt sie in ihrer Gliederung. Die Beispielreise zeigt eine Gliederung für Wanderung und eine kürzere für Bahn.

## Darstellung

Eine Art kann eine `farbe` aus der Palette der Seite tragen: `blau`, `braun`, `lila`, `gruen`, `tuerkis`, `oliv`, `grau`, `rosa`, `schiefer` (`engine/vorlage.html`, `--farbe-*`); ohne Angabe `grau`. Die Legende der Karte und der Vergleich zeigen die Arten der Reise mit ihrem Namen. Summen („Nächte: 5× Hotel, 3× Refugi“) zählen je Art.

## Übergang

- Bis 28.10.2026 abends: Grundliste `engine/merkmale.yaml` je Bereich oder Art für alle Reisen; eine Reise durfte nur ergänzen; Übernachtungskategorien fest in `routen.py` (`KATEGORIEN`, `TYP_KATEGORIE`) mit reisespezifischen Wörtern.
- Paket O-0 (28.10.2026, frieda-reist #88): Stufen je Reise als Brücke.
- Paket O-1 (frieda-reist #89): `arten.yaml` je Reise, Grundliste und Kategorien entfallen; Paket O-2 (#90): Ableitung der `arten.yaml` beider laufenden Reisen aus ihren Bestandsdaten ohne ID-Änderung (`neu.py arten-ableiten <reise>`), danach Prüfung im Gespräch.
- Paket O-3, Schritt 1 (29.10.2026, frieda-reist #91): Schreibweg `engine/schreiben.py` und die Werkzeuge `art_definieren`, `merkmal_definieren`; Arten und Merkmale entstehen im Gespräch und landen sofort in `plan/arten.yaml` der Reise.
- Paket O-3, Schritt 2 (29.10.2026): `wert_eintragen` schreibt Werte an Unterkünften, Strecken und Optionen sofort nach `plan/routen.yaml`; ein Wert ohne Herkunft wird abgelehnt, ein veränderlicher ohne Prüfdatum auch.
- Paket O-3, Schritt 3 (29.10.2026): `ding_anlegen`, `ding_aendern`, `option_anlegen`, `wahlstelle_anlegen`, `frage_anlegen`; Dinge, Wahlstellen und Fragen entstehen im Gespräch mit fester ID aus `ids.yaml`, Herkunft und Verlauf. `alternative_vorschlagen` entfällt.
- Paket O-3, Schritt 4 (29.10.2026): `entscheiden` schreibt den Verlauf der Wahl direkt (Person, Datum, Grund; Frage geklärt oder wieder offen), `tag_aendern` den Plan eines Tags.
- Paket O-3, Schritt 5 (29.10.2026): `wissen_schreiben` (W-Abschnitte mit Herkunft am Absatz), `frage_schliessen`, `rueckmeldung_erledigen`, Personen über `person_schreiben` direkt in `reise.yaml`.
- Später: Aufenthalt ohne Nacht und Buchung als eigene Dinge (Paket O-5, O-7).
