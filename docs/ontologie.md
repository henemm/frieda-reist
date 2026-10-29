# Die Reise-Ontologie: Grundformen in der Software, Arten in der Reise

Kern: `docs/adr/0001-kern.md`. Dieses Dokument sagt, was die Software über eine Reise weiß (die Grundformen und die Form eines Merkmals) und wie eine Reise ihre eigenen Arten und Merkmale festlegt (`plan/arten.yaml`). Es ersetzt die „Mischform“ mit der Grundliste `engine/merkmale.yaml` (26.10.–28.10.2026), siehe Verlauf unten. Herkunft der Begriffe: Recherche „Grundformen in der Software, Arten in der Reise“ (28.10.2026; schema.org Trip/Accommodation/PropertyValue, Transmodel, GTFS, PROV-O, Eurostat/IRTS, FHIR-Profile), gelesen gegen die zwei laufenden Reisen.

## Grundformen

Die Software kennt genau diese Dinge. Sie gelten für jede Art von Reise (Hüttentour, Städtereise, Familienbesuch, Bahnreise, Kreuzfahrt, Geschäftsreise).

| Grundform | Was es ist | ID heute | Datei |
|---|---|---|---|
| **Reise** | Rahmen: Titel, Zeitraum, Personen mit Rollen, Status, Bausteine, Regeln | – | `reise.yaml` |
| **Ort** | ein Punkt oder Gebiet, an dem man ist oder das man passiert | `O-` | `plan/routen.yaml` |
| **Aufenthalt** | an einem Ort sein: mit Nacht die Unterkunft (`U-`, `unterkuenfte`, am Tag `nacht`), ohne Nacht Besichtigung, Essen, Besuch (`A-`, `aufenthalte`, am Tag `aufenthalte: [A-01]`, mit `zeit` als Text; Paket O-5) | `U-`, `A-` | `plan/routen.yaml` |
| **Bewegung** | von Ort zu Ort: Wanderung, Bahn, Bus, Fähre, Flug, Mietwagen … | `E-` | `plan/routen.yaml` |
| **Folge** | ein geordneter Abschnitt aus Aufenthalten und Bewegungen: Tag, Reiseteil, benannter Plan | `T-`, `P-` | `plan/routen.yaml` |
| **Wahl** | Wahlstelle mit Optionen (eine von mehreren, mit oder ohne, wie lange), Verlauf mit Person, Datum, Grund | `V-`, `V-01.a` | `plan/routen.yaml` |
| **Aussage** | ein Merkmal eines Dings: Wert, Herkunft (`quelle`), Prüfdatum (`geprueft`), Gültigkeit (`gilt`), Notiz | am Ding | `plan/routen.yaml` |
| **Buchung** | ein Aufenthalt oder eine Bewegung ist angefragt, gebucht oder storniert (seit 29.10.2026, #76): `fuer` (eine oder mehrere IDs), `status`, `nummer`, `bei`, `preis`, `bezahlt`, `frist` mit `frist_was`, `storno` mit `storno_bis`, `gebucht_am`, `wer`, `quelle` (Pflicht), `notiz`, `verlauf`. Der Buchungsstand des Dings folgt seiner geltenden Buchung: Stornierte gelten nie; unter mehreren gilt gebucht vor angefragt, dann die jüngste (`gebucht_am`), dann die spätere in der Datei (Product Owner 29.10.2026). Mitwirkende ändern nur Buchungen, die sie selbst eingetragen haben (`wer`), Organisator:innen alle; Stornieren braucht einen Grund. Der **Beleg** (PDF, Bild) ist eine Datei in der Ablage der Instanz, nie im Repo (`engine/belege.py`, `docs/betrieb.md` „Belege“); anhängen geht nur angemeldet | `B-` | `plan/routen.yaml` (`buchungen:`), Beleg in `<ablage>/<reise>/belege/` |
| **Offenes** | Frage, Aufgabe, Wunsch, Rückmeldung, jeweils an eine ID gehängt | `F-`, `AG-`, `R-` | `offene-fragen.md`, Ablage |
| **Wissen** | Fließtext mit Herkunft: Geschichte, Praxis, Quellen | `W-` | `inhalt/` |

Jedes Ding hat einen **Kern**: feste ID (nie neu vergeben, nie gelöscht), Grundform, **Art** (von der Reise vergeben), Titel, Herkunft, Zeit- oder Ortsbezug, Verweise auf andere Dinge, Merkmale, Verlauf.

**Lage eines Aufenthalts** ([ADR-0004](adr/0004-lage.md), Product Owner 29.10.2026): Ein Aufenthalt hat neben seinem Ort (`ort: O-…`, die Gegend) eine eigene Lage, nämlich `adresse` (Postadresse), `punkt` (Koordinaten) oder beides. Beide sind Aussagen mit Herkunft: `adresse: {wert: "Terrassenufer 1, 01067 Dresden", quelle: …, geprueft: 2026-10-29}`, `punkt: {wert: [50.9792, 14.1128], quelle: …}`. Ein Ort selbst hat keine Adresse. Fehlt der Punkt, nimmt der Bau ihn aus `plan/punkte.yaml` (Punkt mit `id: U-…`). Ab Status `fest` mahnt der Bau Unterkünfte im Plan ohne Lage. Die Seite verlinkt die Lage mit Google Maps, auf Apple-Geräten auch mit Apple Karten. Eintragen: `lage_eintragen` in der Claude-App; vorfüllen aus OpenStreetMap: `werkzeuge/adressen_holen.py` (`docs/werkzeuge.md`). Das Merkmal „Lage“ einer Reise („400 m vom Zentrum“) ist etwas anderes: eine Beschreibung, keine Adresse.

## Die Art eines Dings

Welche Arten es gibt (Hotel, Refugi, Ryokan, Nachtfähre, Wanderung, Shinkansen, Reiseteil …), weiß nur die Reise. Sie stehen in **`reisen/<reise>/plan/arten.yaml`**, entwickelt im Gespräch im AI-Client, und werden dort immer wieder geschärft (Art anlegen, Merkmal ergeben, umbenennen, zusammenführen, abschalten; vorschlagen dürfen Mitwirkende, festlegen Organisator:innen, mit Verlauf). Seit 29.10.2026 geht das über die Konnektor-Werkzeuge `art_definieren` und `merkmal_definieren` direkt in die Datei (`docs/konnektor.md`, „Ontologie im Gespräch“; Schreibweg `engine/schreiben.py`); der Verlauf ist die Geschichte des Repos, ein Commit je Änderung mit Person und Grund. Zusammenführen zweier Merkmale (Werte umhängen, das alte wird ein weiterer Name des bleibenden): `merkmal_zusammenfuehren` (seit 29.10.2026). Die Software liefert keine Liste, weder als Pflicht noch als Vorschlag. Der AI-Client darf Standards wie schema.org oder OpenStreetMap als Wissen nutzen, wenn er Merkmale vorschlägt. Die Beispielreise der Software hat eine Anschauungs-`arten.yaml` (erfundene Reise, kein Katalog). Arten einer früheren Reise derselben Person darf der AI-Client nur auf ausdrückliche Nachfrage als Kopie übernehmen (Product Owner, 28.10.2026; Werkzeug `arten_uebernehmen`, nur Reisen, auf denen die Person dabei ist).

```yaml
# reisen/<reise>/plan/arten.yaml – Arten und Merkmale dieser Reise (docs/ontologie.md)
arten:
  hotel:
    grundform: aufenthalt          # aufenthalt | bewegung | folge
    name: Hotel                    # Anzeige
    farbe: blau                    # Darstellung auf Karte, Legende, Vergleich (Palette der Seite, siehe unten)
    symbol: unterkunft             # Zeichen der Seite (siehe Darstellung); ohne Angabe das der Grundform
    buchbar: true                  # hat einen Buchungsstand (Zu buchen, Stand der Vorbereitung); Vorgabe: Aufenthalte ja
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

- Unterkunft (`U-…`), Aufenthalt (`A-…`) und Nacht (`nacht: {art: …}`): Feld `art:`. Der alte Schlüssel `typ:` (bis 29.10.2026) wird als Art gelesen (klein geschrieben, Umlaute und Leerzeichen zu `ae`/`_`: `Refugi` → `refugi`, `Shukubō` → `shukubo`), aber nie mehr geschrieben; die Seite und der Konnektor nennen den Namen der Art aus `arten.yaml`. Die Art muss in `arten.yaml` stehen, sonst bricht der Bau mit dem Hinweis ab, sie im Gespräch anzulegen.
- Strecke (`E-…`): Feld `art:`, Pflicht (seit 29.10.2026 gibt es keine Vorgabe mehr: die Software kennt keine Art, auch nicht „wandern“). Eine Liste mehrerer Arten gilt als Art `kombiniert`, die die Reise definiert; Werte stehen dann an der Option. Welche Bewegung „aus eigener Kraft“ ist (Gehzeit, Länge, Höhenmeter werden summiert, Etappenkarte, Tageskilometer), sagt `summiert: true` an der Art.
- Wahlstelle (`V-…`): Feld `art:` ist die Art der Dinge, zwischen denen gewählt wird (bis 29.10.2026 `bereich:`, wird weiter gelesen). Fehlt es, kommt die Art aus den Optionen: Unterkünfte → die Art der ersten Unterkunft, Strecken → die gemeinsame Art der Strecken, Folge → die eine Art der Grundform `folge`, wenn die Reise genau eine hat, sonst keine Merkmale. Wann entschieden wird, sagt `wann: planung | unterwegs` (Vorgabe `planung`; bis 29.10.2026 stand das in `art:`, was mit der Art der Dinge kollidierte; `art: planung` wird weiter gelesen). In den gebauten Daten heißen die Felder ebenso `art` und `wann`.
- Jede Art gehört zu genau einer Grundform. Berechnete Merkmale (`auto`) gibt es je Grundform: Bewegung `gehzeit`, `laenge`, `hoehenmeter`; Folge `tage`, `gehzeit`, `unterkuenfte`, `anschluss`. Sie sind Kennzahlen der Grundform, kein Katalog; die Reise entscheidet, ob und unter welchem Namen sie erscheinen.

## Die Form eines Merkmals

Ein Merkmal ist eine Definition in `arten.yaml` und ein Wert am Ding.

| Feld der Definition | Bedeutung |
|---|---|
| `name` | Anzeige |
| `typ` | `text` (Vorgabe), `geld`, `zahl`, `auswahl` (mit `werte`) |
| `veraenderlich` | der Wert braucht ein Prüfdatum; ohne steht „ungeprüft“ daneben, ab Status `fest` eine Mahnung, der Wächter meldet alte Prüfdaten |
| `stufe` | `pflicht`, `empfohlen` (Vorgabe), `angeboten`, `aus`. Für Menschen heißen sie **„nötig“**, **„gut zu wissen“** und **„zusätzlich“** (Product Owner 29.10.2026); `aus` bleibt unsichtbar. In Dateien und Werkzeugen bleiben die Schlüssel, der Schreibweg nimmt auch die Wörter an (`routen.stufe_schluessel`), der Konnektor sagt die Wörter (`routen.stufe_wort`; bei einer Stufe je Unterkunftstyp „sonst“ für `*` und „gilt nicht“ für `aus`), die Seite erklärt den Vergleich in Worten. Nötig und gut zu wissen sind die Spalten im Vergleich der Alternativen (zusätzlich steht dort nur in den Einzelheiten, `docs/design.md`); nur **nötig** zählt als „Fehlt noch“ und im Zähler des Vergleichs (seit Paket O-5); gut zu wissen ohne Wert ist keine Lücke und keine Mahnung (Product Owner 29.10.2026); zusätzlich erscheint nur mit Wert; aus gilt nicht. Eine Wahlstelle kann die Stufe für sich ändern (`merkmale: {abendessen: {stufe: empfohlen}}`) |
| `auto` | berechnet, nie eingetragen (siehe Grundformen) |
| `hilfe`, `frage` | wie der AI-Client den Wert recherchiert und wonach er fragt |
| `einheit` | Anzeige hinter Zahlen |
| `auch` | weitere Namen, unter denen dasselbe gemeint ist (Zuordnung ähnlicher Vorschläge innerhalb der Reise) |
| `rolle` | `kosten` (Product Owner 29.10.2026): dieses Merkmal (Typ `geld`) ist der Preis des Dings, den die Seite über die Reise summiert („Übernachtungen“ im Reiseüberblick: Preis je Nacht am Datum der Nacht, bei offener Wahl die Spanne). Die Software kennt die Rolle, nicht den Namen des Merkmals; je Art trägt sie höchstens ein Merkmal, ohne Rolle wird nichts summiert (die Herberge der Beispielreise mit „Preis pro Person“ hat keine) |

Ein **Wert** am Ding: `{wert, quelle, geprueft, notiz, gilt}`; mehrere Werte je Datum als Liste mit `gilt` (`docs/alternativen.md`). Ein Wert ohne Herkunft wird abgelehnt, seit der Konnektor direkt schreibt (Paket O-3, `wert_eintragen`); Bestandswerte ohne Quelle bleiben lesbar.

Die Software prüft nur die Form: bekannte Felder, erlaubte Typen, Stufen und Rollen, Auswahlwerte, Prüfdatum bei Veränderlichem, dass jede Art genau eine Grundform hat und jedes Ding eine bekannte Art. Ob „Frühstück“ für ein Refugi sinnvoll ist, entscheidet die Reise. Eine Stufe je Art (`stufe: {"*": aus, refugi: empfohlen}`) hängt am Schlüssel der Art.

**Buchungsstand eines Dings:** Er folgt seiner geltenden Buchung (`B-…`). Das freie Feld `buchung:` am Ding (bis 29.10.2026) wird weiter gelesen, aber vom Konnektor nicht mehr geschrieben: Eine Buchung ohne Nummer, Frist, Stornoregel und Herkunft wäre eine Tatsache ohne Herkunft (ADR-0001, Frage 5).

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
- **Konnektor:** `zeige E-…` nennt die Gliederung der Art mit der Hilfe je Rubrik, damit der AI-Client den Text in diesem Aufbau schreibt; `lesetext_schreiben` schreibt oder ersetzt ihn (ein fremdes Stichwort lehnt der Schreibweg ab), `art_definieren` pflegt die Gliederung (`lesetext`) und erhält sie beim Ändern anderer Felder (seit 29.10.2026).
- **Herkunft des Aufbaus** (Recherche 29.10.2026): Wanderführer und Tourenportale trennen den erzählenden Text von der Wegbeschreibung. Rother stellt jeder Tour Kopfdaten (Ausgangspunkt, Anforderungen, Einkehr, Varianten) und eine kurze Einleitung voran, dann folgt die Beschreibung; Cicerone nennt je Etappe Kennzahlen und Verpflegung vor dem Text. Outdooractive unterscheidet Kurzbeschreibung (Teaser, 50–300 Zeichen), Beschreibung (Erlebnis, Charakter und Sehenswertes, 900–2000 Zeichen) und Wegbeschreibung (so genau, dass man danach gehen kann), dazu Tipp, Sicherheitshinweise und Ausrüstung als eigene Felder. Wikivoyage gibt für Reiserouten ein Grundgerüst vor, von dem man weglässt, was nicht passt. Daraus der Grundaufbau Kurzzeile, Charakter, Verlauf in groben Zügen, Höhepunkte, Anforderungen, Ankommen; was eine Reise darüber hinaus wichtig findet (etwa „Im Vergleich zu gestern“, „Was andere sagen“, „Jahreszeit“), ergänzt sie in ihrer Gliederung. Die Beispielreise zeigt eine Gliederung für Wanderung und eine kürzere für Bahn.

## Darstellung

Eine Art kann eine `farbe` aus der Palette der Seite tragen: `blau`, `braun`, `lila`, `gruen`, `tuerkis`, `oliv`, `grau`, `rosa`, `schiefer` (`engine/vorlage.html`, `--farbe-*`); ohne Angabe `grau`. Dazu ein `symbol` aus dem Zeichensatz der Seite (`engine/bauen.py` SYMBOLE, Lucide): `unterkunft`, `zelt`, `einkehr`, `ticket`, `museum`, `wandern`, `bus`, `bahn`, `schiff`, `flug`, `auto`, `rad`, `taxi`, `strecke`, `ort`, `karte`, `plan`; ohne Angabe das Zeichen der Grundform (Aufenthalt Bett, Bewegung Weg, Folge Plan). Die Seite zeigt Name, Farbe und Symbol der Art am Etikett jedes Dings, in der Zeitleiste des Tags, in der Legende der Karte und im Vergleich; sie kennt keine Art selbst (bis Paket O-5 trug `engine/vorlage.html` eine Liste von Verkehrsmitteln, `ART_TEXT`). `buchbar: true` gibt den Dingen der Art einen Buchungsstand (`buchung:` am Ding, sonst „offen“), der auf der Seite unter „Zu buchen“ und im Stand der Vorbereitung erscheint; Vorgabe: Aufenthalte ja, Bewegungen und Folgen nein. Summen („Nächte: 5× Hotel, 3× Refugi“) zählen je Art.

## Kartenpunkte und ihre Kategorien

Punkte auf den Karten (Etappen-Karte aus `plan/punkte.yaml`, Karte im Wissensabschnitt) tragen eine `kat`. Welche Kategorien es gibt (Einkehr, Wasser, Schauplatz, Bahnhof …), weiß nur die Reise: **`reisen/<reise>/plan/kategorien.yaml`**, im Gespräch gepflegt mit `kategorie_definieren` (Frage 2 der Prüfstelle: kein Katalog in der Software; Beispiel: `beispiel/reisen/beispielreise/plan/kategorien.yaml`). Je Kategorie: `gruppe` (`punkt` oder `wissen`), `name` (Legende, Ebenenwahl), `einzahl` (für einen einzelnen Punkt), `farbe` (Palette der Seite, `kontrast` oder `#rrggbb`), `symbol` (Zeichen der Seite), `nummeriert` (der Punkt zeigt seine Nummer) und `arten` (Zusatz je `art`-Wort eines Punkts: `name`, `symbol`, `hinweis`, `umriss`). Der Schlüssel gilt in einer Reise nur einmal, auch über die Gruppen hinweg. Der Bau prüft nur die Form und dass jede `kat` der Punkte dort steht; wer Punkte hat, braucht die Datei. Die `art`-Wörter selbst (OpenStreetMap-Standardwörter wie `hotel`, `bus`) bleiben Angaben der Werkzeuge in `punkte.yaml`; wie sie auf der Karte heißen, sagt die Reise. Das Punktfeld `trinkbar` (aus OpenStreetMap) zeigt die Seite für jeden Punkt, der es trägt.

## Übergang

- Paket O-7 (29.10.2026, frieda-reist #128): Kategorien der Kartenpunkte (bisher `PUNKT_KATEGORIEN`, `WISSEN_KATEGORIEN` im Bau und `PUNKT_KAT`, `PUNKT_ART`, `PUNKT_SYM`, `WISSEN_KAT` samt Farben in der Vorlage) stehen je Reise in `plan/kategorien.yaml`; `kategorie_definieren` im Konnektor. Die beiden laufenden Reisen haben ihren bisherigen Stand unverändert als Definition übernommen.

- Bis 28.10.2026 abends: Grundliste `engine/merkmale.yaml` je Bereich oder Art für alle Reisen; eine Reise durfte nur ergänzen; Übernachtungskategorien fest in `routen.py` (`KATEGORIEN`, `TYP_KATEGORIE`) mit reisespezifischen Wörtern.
- Paket O-0 (28.10.2026, frieda-reist #88): Stufen je Reise als Brücke.
- Paket O-1 (frieda-reist #89): `arten.yaml` je Reise, Grundliste und Kategorien entfallen; Paket O-2 (#90): Ableitung der `arten.yaml` beider laufenden Reisen aus ihren Bestandsdaten ohne ID-Änderung (`neu.py arten-ableiten <reise>`), danach Prüfung im Gespräch.
- Paket O-3, Schritt 1 (29.10.2026, frieda-reist #91): Schreibweg `engine/schreiben.py` und die Werkzeuge `art_definieren`, `merkmal_definieren`; Arten und Merkmale entstehen im Gespräch und landen sofort in `plan/arten.yaml` der Reise.
- Paket O-3, Schritt 2 (29.10.2026): `wert_eintragen` schreibt Werte an Unterkünften, Strecken und Optionen sofort nach `plan/routen.yaml`; ein Wert ohne Herkunft wird abgelehnt, ein veränderlicher ohne Prüfdatum auch.
- Paket O-3, Schritt 3 (29.10.2026): `ding_anlegen`, `ding_aendern`, `option_anlegen`, `wahlstelle_anlegen`, `frage_anlegen`; Dinge, Wahlstellen und Fragen entstehen im Gespräch mit fester ID aus `ids.yaml`, Herkunft und Verlauf. `alternative_vorschlagen` entfällt.
- Paket O-3, Schritt 4 (29.10.2026): `entscheiden` schreibt den Verlauf der Wahl direkt (Person, Datum, Grund; Frage geklärt oder wieder offen), `tag_aendern` den Plan eines Tags.
- Paket O-3, Schritt 5 (29.10.2026): `wissen_schreiben` (W-Abschnitte mit Herkunft am Absatz), `frage_schliessen`, `rueckmeldung_erledigen`, Personen über `person_schreiben` direkt in `reise.yaml`.
- Paket O-3, Schritt 6 (29.10.2026): `reise_status_setzen`, `einstellung_setzen`, `reise_anlegen` über den Schreibweg; `auftrag_geben` entfällt.
- Paket O-3, Abschalten (29.10.2026): Der Einarbeiten-Lauf mit Claude Code auf dem Server ist entfernt; es gibt keinen zweiten KI-Lauf in Frieda mehr (ADR-0001, Punkt 5). Alles Schreiben geht über den Schreibweg.
- Paket O-5 (29.10.2026, frieda-reist #93): Aufenthalte ohne Nacht (`A-…`, `aufenthalte`, am Tag `aufenthalte:`), `symbol` und `buchbar` je Art, Buchungsstand an Unterkunft, Aufenthalt und Bewegung; „Fehlt noch“ und Zähler nur für `pflicht`; die Seite kennt keine Art mehr (`ART_TEXT`, `kategorien` entfallen), ihre Bausteintabelle nennt Grundformen.
- 29.10.2026 (Product Owner): Die Stufen heißen für Menschen „nötig“, „gut zu wissen“, „zusätzlich“; nur „nötig“ ohne Wert ist eine Lücke; der Kasten „Mahnung“ auf der Seite ist weg.
- 29.10.2026 (Abgleich Ontologie · Software · Design, `docs/abgleich-2026-10-29.md`, Product Owner): Form eines Merkmals um `rolle: kosten` ergänzt (die Übernachtungssumme las vorher fest das Merkmal `preis`); an Wahlstellen `art:` = Art der Dinge und `wann:` = planung/unterwegs (vorher `bereich:` und `art:`); Strecke ohne `art:` ist ein Baufehler (vorher Vorgabe `wandern`); `typ:` an Unterkünften und `buchung:` am Ding werden nur noch gelesen; Herkunft ist auch bei Optionen Pflicht; die Vorgabe der Ebenen einer Tagesseite kennt kein Wandervokabular mehr (`reise.json etappen_ebenen`).
- 29.10.2026 (frieda-reist #76, Product Owner): Buchung als eigenes Ding `B-…` (`buchungen:` in `plan/routen.yaml`) mit Beleg-Datei in der Ablage; Konnektor `buchung_anlegen`, `buchung_aendern`; Wächter meldet Fristen und Stornofristen; die Seite zeigt die Buchung bei ihrem Ding und hängt Belege an.
