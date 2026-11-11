# Die Reise-Ontologie: Grundformen in der Software, Arten in der Reise

Kern: `docs/adr/0001-kern.md`. Dieses Dokument sagt, was die Software über eine Reise weiß (die Grundformen und die Form eines Merkmals) und wie eine Reise ihre eigenen Arten und Merkmale festlegt (`plan/arten.yaml`). Es ersetzt die „Mischform“ mit der Grundliste `engine/merkmale.yaml` (26.10.–28.10.2026), siehe Verlauf unten. Herkunft der Begriffe: Recherche „Grundformen in der Software, Arten in der Reise“ (28.10.2026; schema.org Trip/Accommodation/PropertyValue, Transmodel, GTFS, PROV-O, Eurostat/IRTS, FHIR-Profile), gelesen gegen die zwei laufenden Reisen.

## Grundformen

Die Software kennt genau diese Dinge. Sie gelten für jede Art von Reise (Hüttentour, Städtereise, Familienbesuch, Bahnreise, Kreuzfahrt, Geschäftsreise).

| Grundform | Was es ist | ID heute | Datei |
|---|---|---|---|
| **Reise** | Rahmen: Titel, Ziel, Zeitraum, Personen mit Rollen, Status, Bausteine, Regeln; Untertitel und der Abschnitt Eckdaten entstehen beim Bau daraus (#217) | – | `reise.yaml` |
| **Ort** | eine Station der Reise: wo eine Strecke beginnt oder endet, wo man übernachtet, oder eine Gegend, in der man sich ohne eigene Strecke bewegt (ADR-0008); Lokal, Museum, Unterkunft sind Aufenthalte am Ort; darf mit `an:` an genau einem anderen Ort liegen (nur Anzeige) und eine Art der Reise haben (freiwillig); `ausserhalb: true` für einen Ort der An- und Abreise außerhalb der Reisegegend (Flughafen oder Bahnhof daheim; Issue #135), die Seite nennt ihn so, die Karte zeigt ihn nicht; seine Position auf der Karte ist `punkt` (Koordinaten als Aussage, Epic #225), eine Adresse hat er nicht | `O-` | `plan/routen.yaml` |
| **Aufenthalt** | an einem Ort sein: mit Nacht die Unterkunft (`U-`, `unterkuenfte`, am Tag `nacht`), ohne Nacht Besichtigung, Essen, Besuch (`A-`, `aufenthalte`, am Tag `aufenthalte: [A-01]`, mit `zeit` als Text; Paket O-5; Uhrzeit für den Kalender in `beginn` und `ende`, #77); ein Aufenthalt darf an keinem Tag stehen (#235): dann steht er auf der Karte und an seiner Heimat (`an:`, Ortsseite), nicht im Tagesplan; ohne jede Seite zugeklappt als „Noch ohne Platz“ in der Reise (#432) | `U-`, `A-` | `plan/routen.yaml` |
| **Bewegung** | von Ort zu Ort: Wanderung, Bahn, Bus, Fähre, Flug, Mietwagen …; mit `ab` und `an` (Issue #135: Uhrzeit HH:MM am Tag der Strecke oder Zeitpunkt JJJJ-MM-TTTHH:MM+HH:MM mit Zeitzone; die Software kennt keine Zeitzonen der Orte, sie prüft die Form und meldet, wenn die nächste Strecke des Tags abfährt, bevor diese ankommt); `gpx` ist ihr Track (Pfad unter `medien/` oder `{datei, quelle, geprueft}`, #238) | `E-` | `plan/routen.yaml` |
| **Folge** | ein geordneter Abschnitt aus Aufenthalten und Bewegungen: Tag, Reiseteil, benannter Plan | `T-`, `P-` | `plan/routen.yaml` |
| **Wahl** | Wahlstelle mit Optionen (eine von mehreren, mit oder ohne, wie lange), Verlauf mit Person, Datum, Grund | `V-`, `V-01.a` | `plan/routen.yaml` |
| **Aussage** | ein Merkmal eines Dings: Wert, Herkunft (`quelle`), Prüfdatum (`geprueft`), Gültigkeit (`gilt`), Notiz | am Ding | `plan/routen.yaml` |
| **Buchung** | ein Aufenthalt oder eine Bewegung ist angefragt, gebucht oder storniert (seit 29.10.2026, #76): `fuer` (eine oder mehrere IDs), `status`, `nummer`, `bei`, `preis`, `bezahlt`, `frist` mit `frist_was`, `storno` mit `storno_bis`, `gebucht_am`, `wer`, `quelle` (Pflicht), `notiz`, `verlauf`; seit Issue #135 `personen` (die Reisenden dieser Buchung, `{Name: Angabe}` wie Sitzplatz, Gepäck, Vielfliegernummer, oder Liste der Namen; nur Personen der Reise), `preise` (`{ID aus fuer: Betrag}`, wenn eine Buchung mehrere Dinge umfasst, etwa Hin- und Rückflug), `ab` mit `ab_was` (ab wann etwas geht, etwa der Check-in; `frist` sagt bis wann); seit Issue #166 `zahlung` (Zahlstand, feste Werte `offen`, `angezahlt`, `bezahlt`, `vor_ort`, `inklusive`, `erstattet` (nur bei `storniert`); Datenwerte deutsch, englische Aliase `open`, `deposit`, `paid`, `on_site`, `included`, `refunded` bei der Eingabe, ADR-0006; Einzelheiten weiter im Text `bezahlt`) und `merkmale` (`{Merkmal: Wert}`, nur Merkmale der Buchung, die die Arten ihrer Dinge festlegen, siehe „Angebot und Buchung“); seit Issue #463 der Zeitraum `anreise` und `abreise` (JJJJ-MM-TT, bei Strecken das Reisedatum; eine Nacht gehört dazu, wenn anreise ≤ Nacht < abreise, ein Tag einer Strecke oder eines Aufenthalts, wenn anreise ≤ Tag ≤ abreise, nur `anreise`: genau dieser Tag; ohne Zeitraum gilt die Buchung für alle Nächte ihrer Dinge), `anreise_ab` und `abreise_bis` (Check-in ab, Check-out bis, Text wie „15:00“) und `vor_ort_zahlen` (was vor Ort noch zu zahlen ist, etwa die Kurtaxe; dann nicht noch einmal in `preis` oder `bezahlt`). Seit Issue #472 nehmen `frist` und `ab` auch einen Zeitpunkt mit Uhrzeit `JJJJ-MM-TTTHH:MM` (Ortszeit), damit die Uhrzeit nicht im Text `frist_was`/`ab_was` steht; der Wächter zählt den Tag und nennt die Uhrzeit. Seit Issue #476 sind Kurzfelder (`preis`, `bezahlt`, `ab_was`, `frist_was`, `vor_ort_zahlen`) und Text-Merkmale höchstens 60 Zeichen lang; ein Merkmal mit `lang: true` an seiner Definition darf länger sein (z. B. Charakter). Seit Issue #473 hat eine Buchung über mehrere Dinge (Hin- und Rückflug) `je_ding` (`{ID aus fuer: {ab, ab_was, frist, frist_was}}`): Das gilt an diesem Ding statt `ab`/`frist` der Buchung; die Seite zeigt die Buchung an jedem dieser Dinge mit nur seinen Angaben, Wächter und Kalender melden je Ding. Hat eine Unterkunft mehrere getrennte Aufenthalte, hat jede Buchung ihren Zeitraum; die Seite zeigt an jeder Nacht nur ihre Buchung, und zwei Buchungen mit getrennten Zeiträumen sind keine Warnung. Eine Buchung über mehrere Strecken ist eine Buchung mit mehreren IDs in `fuer`. Der Buchungsstand des Dings folgt seiner geltenden Buchung: Stornierte gelten nie; unter mehreren gilt gebucht vor angefragt, dann die jüngste (`gebucht_am`), dann die spätere in der Datei (Product Owner 29.10.2026). Mitwirkende ändern nur Buchungen, die sie selbst eingetragen haben (`wer`), Organisator:innen alle; Stornieren braucht einen Grund. Der **Beleg** (PDF, Bild, Abschrift als Text) ist eine Datei in der Ablage der Instanz, nie im Repo (`engine/belege.py`, `docs/betrieb.md` „Belege“); anhängen geht nur angemeldet, auf der Reiseseite oder im Gespräch, beim Anlegen der Buchung in einem Schritt (`buchung_anlegen` mit `beleg_text`/`beleg_base64`) oder nachträglich (`beleg_anlegen`, Issue #135) | `B-` | `plan/routen.yaml` (`buchungen:`), Beleg in `<ablage>/<reise>/belege/` |
| **Gegenstand** | etwas, das mitkommt (Packliste, [ADR-0010](adr/0010-gegenstand.md), #370): feste ID, `art` (die Kategorie, eine Art mit `grundform: gegenstand`), `titel`, `merkmale` (Gewicht, Raum, Anzahl, Preis … je nach Art, ohne Herkunftspflicht), `an` (Strecke, Aufenthalt, Unterkunft oder Ort, nie ein Tag), `wer` (die Person, die ihn packt; ohne `wer` packt ihn jede Person für sich), `notiz`, `status` (nur `entfaellt`, gelöscht wird nie), `verlauf`. Der Packstand (abgehakt, je Person) liegt live beim Rückmeldedienst | `G-` | `plan/packliste.yaml` (`gegenstaende:`), Packstand in `<ablage>/<reise>/packstand.json` |
| **Offenes** | Frage, Aufgabe, Wunsch, Rückmeldung, jeweils an eine ID gehängt | `F-`, `AG-`, `R-` | `offene-fragen.md`, Ablage |
| **Wissen** | Fließtext mit Herkunft: Geschichte, Praxis, Quellen | `W-` | `inhalt/` |

Jedes Ding hat einen **Kern**: feste ID (nie neu vergeben, nie gelöscht), Grundform, **Art** (von der Reise vergeben), Titel, Herkunft, Zeit- oder Ortsbezug, Verweise auf andere Dinge, Merkmale, Verlauf.

**Uhrzeit und Kalender** (frieda-reist #77, Product Owner 29.10.2026): Bewegungen und Aufenthalte ohne Nacht haben optional `beginn` und `ende` als Uhrzeit `"HH:MM"` (in Anführungszeichen, Ortszeit am Ort des Dings; `ende` nur mit `beginn`, ein Ende vor dem Beginn liegt am Tag danach, etwa bei einer Nachtfähre). Der freie Text `zeit` („nach der Wanderung“) bleibt daneben. Daraus und aus Tagen, Nächten und Fristen entsteht der Kalender der Reise (`engine/kalender.py`): als Datei auf der Seite („In den Kalender“, ganz oder je Ding) und als persönlicher Kalender über alle Reisen (Abo und Download auf „Mein Konto“, Konnektor `kalender`; was darin steht, stellt jede Person selbst ein). Er zeigt nur Entschiedenes: Tage unter einer offenen Planungs-Wahlstelle stehen in `route.tage[].vorlaeufig` und fehlen im Kalender, ebenso Nächte und Strecken aus einer offenen Planungs-Wahlstelle.

**Ort als Station** ([ADR-0008](adr/0008-ort.md), Product Owner 5.11.2026): Der Ort ist die Einheit, an der der Anschluss geprüft wird; seine Größe wählt die Reise. Ein Ort darf mit `an: O-…` in genau einem anderen Ort liegen; das zeigt nur die Seite (Ortsseite des übergeordneten Orts mit seinen Orten, „liegt in“; ein Ort mit Orten darin hat auch ohne eigenen Text eine Seite, ein Ort ohne eigene Seite steht als Zeile auf der Seite des Orts, in dem er liegt), der Anschluss bleibt exakte Gleichheit der Station. Eine Art mit `grundform: ort` ist freiwillig (Farbe, Symbol, Merkmale, Gliederung des Lesetexts). **Eine Lage je Stelle:** Der Ort trägt `koordinaten` (typisiertes Merkmal; `punkt` wird weiter gelesen); ein Aufenthalt an derselben Stelle (Wegpunkt im Dorf) verweist mit der Rolle `bezug` auf den Ort statt eigener Koordinaten. `neu.py nachziehen` führt einen Ort und seine gleichnamigen Wegpunkte (Aufenthalte an einer Strecke) zusammen, wenn sie höchstens 100 m auseinanderliegen: Der Ort übernimmt Koordinaten und Herkunft des ersten Wegpunkts (hat er keine eigenen), die Wegpunkte bekommen `bezug` (fehlt der Art das Merkmal, entsteht `station` „Ort“). Ein Wegpunkt, der schon die Lage einer Unterkunft an diesem Ort ist, bleibt; Weiteres (weiter auseinander, anderer Bezug, nur ähnlicher Name, Ort mit Unterorten) meldet es als offen. Was eine Karte zeigt, ist eine Regel: Übersicht = Orte des Plans und Unterkünfte, Etappe = Dinge an der Strecke, Ort = Dinge am Ort und seine Orte; ein Ort mit Unterorten ist kein Punkt. Was davon umgesetzt ist, steht im Verlauf von ADR-0008.

**Lage eines Aufenthalts** ([ADR-0004](adr/0004-lage.md), Product Owner 29.10.2026): Ein Aufenthalt hat neben seinem Ort (`ort: O-…`, die Gegend) eine eigene Lage, nämlich `adresse` (Postadresse), `punkt` (Koordinaten) oder beides. Beide sind Aussagen mit Herkunft: `adresse: {wert: "Terrassenufer 1, 01067 Dresden", quelle: …, geprueft: 2026-10-29}`, `punkt: {wert: [50.9792, 14.1128], quelle: …}`. Ein Ort selbst hat keine Adresse. Fehlt der Punkt, nimmt der Bau ihn aus `plan/punkte.yaml` (Punkt mit `id: U-…`). Ab Status `fest` mahnt der Bau Unterkünfte im Plan ohne Lage. Die Seite verlinkt die Lage mit Google Maps, auf Apple-Geräten auch mit Apple Karten. Eintragen: `lage_eintragen` in der Claude-App; vorfüllen aus OpenStreetMap: `werkzeuge/adressen_holen.py` (`docs/werkzeuge.md`). Das Merkmal „Lage“ einer Reise („400 m vom Zentrum“) ist etwas anderes: eine Beschreibung, keine Adresse.

## Packliste: Gegenstände und ihre Kategorien (ADR-0010, #370)

Eine Reise mit dem Baustein `packliste` hat eine Packliste (`plan/packliste.yaml`). Die **Kategorien** sind Arten der Reise mit `grundform: gegenstand` (`plan/arten.yaml`), ihre **Merkmale** wie bei jeder Art; Frieda führt kein Inventar, keine Anlässe und belegt nichts vor. Eine neue Liste beginnt mit einer früheren Reise (`packliste_uebernehmen`) oder einem Vorschlag der KI im Gespräch.

```yaml
arten:
  kleidung:
    grundform: gegenstand
    name: Kleidung
    merkmale:
      gewicht: {name: Gewicht, typ: zahl, einheit: g, rolle: summe}      # wird je Kategorie und gesamt summiert
      raum:    {name: Raum, typ: auswahl, werte: [am Körper, Tagesrucksack, Rucksack]}   # Raum ist ein gewöhnliches Merkmal
```

```yaml
gegenstaende:                                  # plan/packliste.yaml
  - id: G-05
    art: ausruestung
    titel: Wanderstöcke
    merkmale: {gewicht: 480, preis: 45 €, raum: Rucksack}
    an: E-01                                  # Elternbezug, ADR-0007: Strecke, Aufenthalt, Unterkunft oder Ort, nie ein Tag
    wer: Ida                                  # nur sie hakt ihn ab; ohne wer packt ihn jede Person für sich
    verlauf: [{datum: 2026-10-02, wer: Ida, was: angelegt}]
```

- **Ohne Herkunft:** Ein Gegenstand braucht keine `quelle` (ausdrückliche Ausnahme der Herkunftspflicht, ADR-0010 Punkt 10); ein Merkmal mit `veraenderlich: true` behält sein Prüfdatum.
- **Summen:** je Kategorie und gesamt für jedes Merkmal mit der Rolle `summe` (oder dem Alias `kosten`), mit Einheit; weggelassene Gegenstände zählen nicht, der Wert gilt für den ganzen Eintrag (nicht mal Anzahl).
- **Heimat:** der Reiter „Packliste“ ([ADR-0003](adr/0003-heimat.md)); an der Strecke, dem Aufenthalt, der Unterkunft oder dem Ort steht die Zeile „Mitnehmen“ mit Link. Hängt ein Gegenstand nur an verworfenen Möglichkeiten, meldet der Bau eine Warnung und die Seite zeigt ihn gedämpft.
- **Packstand:** `<ablage>/<reise>/packstand.json` (`{G-ID: {Person: Zeitpunkt}}`), live beim Rückmeldedienst wie die Aufgaben, nicht im Verlauf der Reise; Abhaken geht auch ohne Netz.
- **Rollen:** Mitwirkende legen an, ändern eigene (selbst angelegt oder zugewiesen) und haken ab; Organisator:innen alles; die Packliste ist in jedem Status schreibbar außer im Archiv.

## Wo ein Ding zu Hause ist: der Elternbezug `an:` (ADR-0007, seit Schritt a, #282)

Jedes Ding in `plan/routen.yaml` (Ort, Strecke, Unterkunft, Aufenthalt, Buchung) darf mit **`an:`** sagen, an welchem anderen Ding es zu Hause ist, genau eines: ein Ort (`O-…`), eine Strecke (`E-…`), ein Aufenthalt (`A-…`), eine Unterkunft (`U-…`), ein Abschnitt des Wissens (`W-…`) oder die Reise selbst (`an: reise`). Die Seite des Elternelements ist die Heimat des Dings (ADR-0003). Ein Tag ist als Elternelement nicht nötig: Ein Ding steht an einem Tag, indem es dort steht (`aufenthalte:`, `strecken:`, `nacht:`).

Vorgabe ohne `an:` (nichts Bestehendes ändert sich): Nacht und Strecke am Tag, Aufenthalt mit Tag an seinem ersten Tag im Plan, Aufenthalt ohne Tag an seinem Ort (hat der Ort keine Seite: zugeklappt als „Noch ohne Platz“ am Ende des Reiseüberblicks, ein Mangel, den der AI-Client mit `an:` behebt; ADR-0003, #432), Buchung an ihrem ersten Ding, Wahlstelle über ihr `an:` (eine Liste, wie bisher). `an:` wird nur geschrieben, wenn es von der Vorgabe abweicht, und vom Bau geprüft: bekanntes Ding der erlaubten Arten, nicht das Ding selbst, kein Kreis. Bei einer **Strecke** war `an:` bis Schritt b die Ankunftszeit: Ein Wert, der eine Kennung ist, gilt als Elternbezug, jeder andere als Zeit. `item_update` (`ding_aendern`) setzt `an` um; ein Aufenthalt mit Tag wird dabei von seinen Tagen gelöst (Sammeltag, #235); ein Tag als Ziel geht über `tag_aendern`.

## Übersicht je Art (ADR-0007, Schritt e, #286; löst #275 ab)

Eine Liste aller Dinge einer oder mehrerer Arten (alle Supermärkte der Reise, alle Pensionen) ist **ein Baustein, keine Daten**: der Organismus `artUebersicht`, gebaut wie der Vergleich der Wahl, aber ohne Entscheidung. Die Spalten sind die Merkmale der Art mit der Stufe „nötig“ und „gut zu wissen“, die mindestens ein Ding belegt; die Werte kommen aus den Merkmalen der Dinge, geändert wird nichts im Text. Am Rechner ist es eine Tabelle mit sortierbaren Spalten, am Telefon sind es gestapelte Karten. Jede Zeile führt zur Heimat des Dings (ADR-0003, Punkt 2: eine Sammelansicht mit der Aufgabe „nachschlagen“), kein Ding steht dort vollständig.

Sie steht nur dort, wo sie **angefordert** wird, es gibt keinen eigenen Reiter und kein Markdown-Kommando:

- **An einem Abschnitt des Wissens:** `reise.json` → `uebersichten: {"W-05": ["supermarkt", "baumarkt"]}`; Konnektor: `wissen_schreiben` und `wissen_aendern` nehmen `uebersicht` (Liste von Arten, leer entfernt); `zeige W-…` nennt sie.
- **An einer Kartenansicht:** `plan/routen.yaml` → `karten_ansichten: [{titel, …, uebersicht: [Art, …]}]`; `kartenansicht_setzen` nimmt `uebersicht`. Die Übersicht steht unter der Karte, wenn die Ansicht gewählt ist.

Der Bau prüft, dass der Abschnitt und jede Art vorhanden sind.

## Die Art eines Dings

Welche Arten es gibt (Hotel, Refugi, Ryokan, Nachtfähre, Wanderung, Shinkansen, Reiseteil …), weiß nur die Reise. Sie stehen in **`reisen/<reise>/plan/arten.yaml`**, entwickelt im Gespräch im AI-Client, und werden dort immer wieder geschärft (Art anlegen, Merkmal ergeben, umbenennen, zusammenführen, abschalten; vorschlagen dürfen Mitwirkende, festlegen Organisator:innen, mit Verlauf). Seit 29.10.2026 geht das über die Konnektor-Werkzeuge `art_definieren` und `merkmal_definieren` direkt in die Datei (`docs/konnektor.md`, „Ontologie im Gespräch“; Schreibweg `engine/schreiben.py`); der Verlauf ist die Geschichte des Repos, ein Commit je Änderung mit Person und Grund. Zusammenführen zweier Merkmale (Werte umhängen, das alte wird ein weiterer Name des bleibenden): `merkmal_zusammenfuehren` (seit 29.10.2026). Die Software liefert keine Liste, weder als Pflicht noch als Vorschlag. Der AI-Client darf Standards wie schema.org oder OpenStreetMap als Wissen nutzen, wenn er Merkmale vorschlägt. Die Beispielreise der Software hat eine Anschauungs-`arten.yaml` (erfundene Reise, kein Katalog). Arten einer früheren Reise derselben Person darf der AI-Client nur auf ausdrückliche Nachfrage als Kopie übernehmen (Product Owner, 28.10.2026; Werkzeug `arten_uebernehmen`, nur Reisen, auf denen die Person dabei ist).

```yaml
# reisen/<reise>/plan/arten.yaml – Arten und Merkmale dieser Reise (docs/ontologie.md)
arten:
  hotel:
    grundform: aufenthalt          # aufenthalt | bewegung | folge | ort (ADR-0008, freiwillig) | gegenstand (Packliste, ADR-0010)
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

- Unterkunft (`U-…`), Aufenthalt (`A-…`) und Nacht (`nacht: {art: …}`): Feld `art:`. Der alte Schlüssel `typ:` (bis 29.10.2026) wird nicht mehr als Art gelesen: steht er statt `art:`, bricht der Bau mit dem Hinweis auf `neu.py nachziehen` ab, das ihn umstellt (`Refugi` → `refugi`, `Shukubō` → `shukubo`; #267 d); die Seite und der Konnektor nennen den Namen der Art aus `arten.yaml`. Die Art muss in `arten.yaml` stehen, sonst bricht der Bau mit dem Hinweis ab, sie im Gespräch anzulegen.
- Strecke (`E-…`): Feld `art:`, Pflicht (seit 29.10.2026 gibt es keine Vorgabe mehr: die Software kennt keine Art, auch nicht „wandern“). Eine Liste mehrerer Arten gilt als Art `kombiniert`, die die Reise definiert; Werte stehen dann an der Option. Welche Bewegung „aus eigener Kraft“ ist (Gehzeit, Länge, Höhenmeter werden summiert, Etappenkarte, Tageskilometer), sagt `summiert: true` an der Art. Eine Strecke einer summierten Art ist eine Etappe (#269): „Etappe“ ist ein Wort der Oberfläche, keine Art und kein Typ der Software. Ihre Kennzahlen stehen an der Strecke (`kennzahlen: {gehzeit: "3:30", aufstieg: 380, abstieg: 220, laenge: 11.5}`, feste Kennungen; eigene Namen der Reise erlaubt; eine Fahrt trägt `fahrzeit` statt `gehzeit`; ein Wert darf `{wert, quelle, geprueft}` sein, ohne eigene Herkunft gilt die der Strecke, #508), ihr Lesetext im Etappen-Dossier unter `## E-… Name`. Zwischenstopps (#509): `abschnitte: [{nach: O-…, kennzahlen, halt: {zweck, dauer: "0:30"}}, …]` in Reihenfolge, der letzte endet am Ziel der Strecke ohne Halt; fehlt der Strecke eine Kennzahl, die alle Abschnitte tragen, gilt deren Summe. **Was aus dem Plan fällt, bricht nichts** (#357, Product Owner 6.11.2026): Eine Etappe wird nie gelöscht; hat ein Abschnitt im Dossier noch die alte Überschrift („## Etappe 10: …“) und der Plan keine Strecke dazu, bleibt er als Archiv-Text in der Datei, der Bau übergeht ihn, die Umstellung meldet ihn als `ARCHIV` (kein Handschritt). Eine Überschrift mit Kennung ohne Strecke („## E-99 …“) bleibt ein Fehler (Tippfehler-Schutz). Widerspricht eine Kennzahl im Dossier dem Wert an der Strecke, gilt der Wert an der Strecke, die Zeile bleibt als Text stehen. Ein Kartenpunkt an einer Strecke, die es nicht gibt, bleibt in `plan/punkte.yaml`.
- Wahlstelle (`V-…`): Feld `art:` ist die Art der Dinge, zwischen denen gewählt wird (bis 29.10.2026 `bereich:`, wird weiter gelesen). Fehlt es, kommt die Art aus den Optionen: Unterkünfte, Aufenthalte ohne Nacht (`aufenthalte: [A-…]`) und Orte (`orte: [O-…]`, nur ein Ort mit Art) → die Art des ersten Dings, Strecken → die gemeinsame Art der Strecken, Folge → die eine Art der Grundform `folge`, wenn die Reise genau eine hat, sonst keine Merkmale. Wann entschieden wird, sagt `wann: planung | unterwegs` (Vorgabe `planung`; bis 29.10.2026 stand das in `art:`, was mit der Art der Dinge kollidierte; `art: planung` wird weiter gelesen). In den gebauten Daten heißen die Felder ebenso `art` und `wann`. **Eine Wahlstelle darf Dinge verschiedener Arten mischen** (Product Owner, 6.11.2026, #353): Ohne `art:` zeigt der Vergleich die Merkmale aller beteiligten Arten, und jede Möglichkeit füllt und mahnt nur die ihrer eigenen Art (Museum neben Wanderung). Eine Möglichkeit enthält `unterkuenfte` oder `folge` allein, sonst `strecken`, `aufenthalte` und `orte` in beliebiger Mischung (Weg und Rast, Gipfelalternative, Ort mit Museum darin). Der Aufenthalt der gewählten Möglichkeit steht am Tag der Wahlstelle (`wahl:` am Tag), im Kalender nur, wenn entschieden ist. **Ein Ort kann Möglichkeit sein** (`orte: [O-…]`, #353, Schritt 2): ein Ziel ohne Rechenbedeutung (Schlechtwetter- oder Gipfelalternative). Er steht im Wahlstellen-Block des Tags, im Vergleich und auf der Karte; Anschluss, Anfang und Ende des Tags und der Ort der Nacht ändern sich nicht, im Kalender steht er nicht. Seine Art ist freiwillig (ADR-0008): ohne Art zeigt der Vergleich nur Text, Plus und Minus.
- Jede Art gehört zu genau einer Grundform. Berechnete Merkmale (`auto`) gibt es je Grundform: Bewegung `gehzeit`, `laenge`, `hoehenmeter`; Folge `tage`, `gehzeit`, `unterkuenfte`, `anschluss`. Sie sind Kennzahlen der Grundform, kein Katalog; die Reise entscheidet, ob und unter welchem Namen sie erscheinen.

## Die Form eines Merkmals

Ein Merkmal ist eine Definition in `arten.yaml` und ein Wert am Ding.

| Feld der Definition | Bedeutung |
|---|---|
| `name` | Anzeige |
| `typ` | `text` (Vorgabe), `geld`, `zahl`, `auswahl` (mit `werte`), `link` (Adresse mit `https://` oder `http://`; die Seite zeigt jeden Wert dieses Typs gleich als Link nach außen, mit dem Namen der Webseite und der Herkunft beim Darüberfahren; seit #165, 31.10.2026), dazu seit ADR-0007 (Schritt b, #283) `adresse`, `koordinaten`, `gpx`, `uhrzeit`, `zeitpunkt`, `zeitraum` (siehe „Typisierte Merkmale der Grundformen“) |
| `veraenderlich` | der Wert braucht ein Prüfdatum; ohne steht „ungeprüft“ daneben, ab Status `fest` eine Mahnung, der Wächter meldet alte Prüfdaten |
| `stufe` | `pflicht`, `empfohlen` (Vorgabe), `angeboten`, `aus`. Für Menschen heißen sie **„nötig“**, **„gut zu wissen“** und **„zusätzlich“** (Product Owner 29.10.2026); `aus` bleibt unsichtbar. In Dateien und Werkzeugen bleiben die Schlüssel, der Schreibweg nimmt auch die Wörter an (`routen.stufe_schluessel`), der Konnektor sagt die Wörter (`routen.stufe_wort`; bei einer Stufe je Unterkunftstyp „sonst“ für `*` und „gilt nicht“ für `aus`), die Seite erklärt den Vergleich in Worten. Nötig und gut zu wissen sind die Spalten im Vergleich der Alternativen (zusätzlich steht dort nur in den Einzelheiten, `docs/design.md`); nur **nötig** zählt als „Fehlt noch“ und im Zähler des Vergleichs (seit Paket O-5); gut zu wissen ohne Wert ist keine Lücke und keine Mahnung (Product Owner 29.10.2026); zusätzlich erscheint nur mit Wert; aus gilt nicht. Eine Wahlstelle kann die Stufe für sich ändern (`merkmale: {abendessen: {stufe: empfohlen}}`) |
| `auto` | berechnet, nie eingetragen (siehe Grundformen) |
| `hilfe`, `frage` | wie der AI-Client den Wert recherchiert und wonach er fragt |
| `einheit` | Anzeige hinter Zahlen |
| `auch` | weitere Namen, unter denen dasselbe gemeint ist (Zuordnung ähnlicher Vorschläge innerhalb der Reise) |
| `nach_buchung` | `true` (Product Owner 31.10.2026): der Wert bleibt auf der Seite sichtbar, wenn das Ding gebucht ist, etwa der Charakter eines Hotels; alle übrigen Merkmale stehen dann zugeklappt „Aus der Planung“, weil nach der Buchung die Buchung gilt. Vorgabe: keines. Nur bei Merkmalen des Dings, nicht bei Merkmalen der Buchung |
| `rolle` | `hero` (Product Owner 5.11.2026, #343): dieses Merkmal (Typ `text`, etwa eine Einschätzung „Was macht es besonders, für wen passt es?“) steht im Vergleich in jeder Möglichkeit ganz oben über alle Spalten (Tabelle: Zeile unter der Möglichkeit, Karte: unter dem Namen), ist dann keine Spalte und kein Eintrag der Merkmalliste mehr; je Art höchstens eines, seine Herkunft steht wie die der anderen Werte in den Einzelheiten. Den Text schreibt der AI-Client im Gespräch (ADR-0001, Regel 5), Frieda erzeugt ihn nicht. Außerdem `summe` (ADR-0010, #370): die Seite und der Konnektor summieren dieses Merkmal (Typ `zahl` oder `geld`) über die Dinge der Art, je Art und gesamt, mit der Einheit des Merkmals (bei Geld mit der Währung des Werts; Dinge mit Status `entfaellt` zählen nicht); eine Art darf mehrere solche Merkmale haben (Gewicht und Preis einer Packliste), die Software kennt die Rolle, nicht den Namen. Und `kosten` (Product Owner 29.10.2026), der Alias für `summe` mit Typ `geld`, je Art einmalig: dieses Merkmal (Typ `geld`) ist der Preis des Dings, den die Seite über die Reise summiert („Übernachtungen“ im Reiseüberblick: Preis je Nacht am Datum der Nacht, bei offener Wahl die Spanne). Die Software kennt die Rolle, nicht den Namen des Merkmals; je Art trägt sie höchstens ein Merkmal, ohne Rolle wird nichts summiert (die Herberge der Beispielreise mit „Preis pro Person“ hat keine) |

### Typisierte Merkmale der Grundformen (ADR-0007, Schritt b, #283)

Lage, Zeit und Track waren feste Felder (`adresse`, `punkt`, `beginn`, `ende`, `ab`, `an`, `buchungslink`, `gpx`). Sie sind Merkmale mit einem **Typ**, den die Software kennt und mit genau einem Baustein zeigt (Atom Wert, `merkmalWert`; `kartenLinks`, `lageZeile`, `zeitText`, Karte, Track):

| Typ | Wert | Baustein / Verwendung |
|---|---|---|
| `adresse` | Text (Postadresse) | `lageZeile` mit `kartenLinks`; die Lage eines Aufenthalts oder einer Unterkunft (ADR-0004) |
| `koordinaten` | `[Breite, Länge]` | Punkt auf der Karte, `kartenLinks`; Lage von Ort, Unterkunft, Aufenthalt |
| `gpx` | Datei unter `medien/….gpx` | Track einer Bewegung auf der Karte (`track_attach`) |
| `uhrzeit` | `HH:MM` (Ortszeit) | `zeitText`; mit Rolle `beginn` oder `ende` |
| `zeitpunkt` | `HH:MM` oder `JJJJ-MM-TTTHH:MM+HH:MM` | `zeitText`; mit Rolle `abfahrt` oder `ankunft` einer Bewegung (Anschlussprüfung, Kalender) |
| `zeitraum` | `{beginn: HH:MM, ende: HH:MM}` (ende freiwillig) | `uhrzeit` des Aufenthalts im Kalender (#77) |

Welche dieser Merkmale eine **Grundform** fest trägt, sagt die Software (wie `rolle: kosten`), kein Katalog: Aufenthalt und Unterkunft `adresse`, `koordinaten`, `buchungslink` (ein `link` mit Rolle `buchung`), der Aufenthalt dazu `zeitraum`; Bewegung `abfahrt`, `ankunft`, `gpx`; Ort `koordinaten`. Welche Merkmale eine **Art** trägt, sagt weiter die Reise (`arten.yaml`); sie darf auch ein gewöhnliches Merkmal mit einem dieser Typen definieren (etwa die Adresse eines Parkplatzes), das als Merkmal erscheint.

```yaml
aufenthalte:
  A-01:
    name: Burg Hohnstein
    ort: O-03
    art: besichtigung
    merkmale:
      eintritt: {wert: "6 €", quelle: "…", geprueft: 2026-10-29}      # Merkmal der Art (arten.yaml)
      adresse: {typ: adresse, wert: "Markt 1, 01848 Hohnstein", quelle: "…", geprueft: 2026-11-01}
      koordinaten: {typ: koordinaten, wert: [50.9792, 14.1128], quelle: "…", geprueft: 2026-11-01}
      zeitraum: {typ: zeitraum, wert: {beginn: "16:00", ende: "18:00"}, quelle: "…"}
```

- **Der Wert trägt seinen Typ** (`typ:`, bei `uhrzeit`, `zeitpunkt` und `link` dazu `rolle:`); sein Name ist ein Schlüssel der Reise. Gelesen wird nur Typ und Rolle, nie der Name (ADR-0001, Frage 2). Eine Grundform trägt je Typ (und Rolle) höchstens ein solches Merkmal; steht dasselbe als altes Feld und als Merkmal da, bricht der Bau ab.
- **Herkunft wie jede Aussage:** `quelle` ist beim Schreiben Pflicht, `geprueft` freiwillig (bei Lage empfohlen).
- **Alte Felder** (`adresse`, `punkt`, `beginn`, `ende`, `ab`, `an` als Zeit, `buchungslink`, `gpx`) werden weiter gelesen und nie mehr geschrieben. `neu.py nachziehen` stellt sie in jeder Reise um (Herkunft der Aussage, sonst die des Dings, sonst „Bestand der Reise“); der Schreibweg stellt eine noch nicht umgestellte Datei beim ersten Schreiben am Ding um. Beim Lesen faltet der Bau die Merkmale zurück in die Felder, die Karte, Kalender, Anschlussprüfung, Mahnung (ab `fest` ohne Lage) und Seite lesen; deshalb sehen alte und neue Form gleich aus. Ist `an` einer Strecke eine Kennung, ist es der Elternbezug (siehe oben), keine Zeit.
- **Konnektor:** `ding_anlegen` nimmt die Merkmale der Grundform unter ihren Namen in `merkmale` (`adresse`, `koordinaten`, `zeitraum`, `abfahrt`, `ankunft`, `buchungslink`) oder wie bisher als Parameter; `ding_aendern`, `lage_eintragen` und `track_anhaengen` schreiben dieselben Merkmale. Eine Art, die ein Merkmal unter demselben Namen selbst definiert, behält ihr Merkmal.

### Angebot und Buchung (Product Owner 31.10.2026, Issue #166)

Zum **Angebot** gehört, was für jeden Kandidaten gilt, auch solange nichts gebucht ist: Preis laut Website, Frühstück, Lage, Bewertung. Das sind die Merkmale der Art (`merkmale`), ihre Werte stehen am Ding. Zur **Buchung** gehört, was erst durch das Buchen entsteht: tatsächlich bezahlter Preis, Zahlstand, Nummer, Stornoregel, Reisende. Das sind die festen Felder der Buchung (oben) und die **Merkmale der Buchung**, die die Reise je Art festlegt:

```yaml
bahn:
  grundform: bewegung
  merkmale:            # Angebot
    preis: {name: Preis, typ: geld, veraenderlich: true}
  buchung_merkmale:    # Buchung
    ticketart: {name: Ticketart, typ: auswahl, werte: [Sparpreis, Flexpreis]}
```

- Fest bleibt, womit die Software rechnet: Status, Frist, Stornofrist, Ab-Termin, Preise, Reisende, Zahlstand (Wächter, Buchungsstand, Kosten). Alles andere legt die Reise fest (Prüfstelle Frage 2: kein Katalog).
- Form eines Merkmals der Buchung: `name`, `typ` (wie oben), `werte`, `einheit`, `hilfe`, `frage`. Keine `stufe`, `rolle`, `auto` oder `veraenderlich`: der Wert ist eine gebuchte Tatsache, er **erbt die Herkunft** (`quelle`) der Buchung und braucht kein Prüfdatum. Jede Änderung steht im Verlauf der Buchung.
- Eine Buchung darf die Merkmale der Buchungen aller Arten ihrer Dinge tragen (Flug und Hotel in einer Buchung: beide), in der Reihenfolge der Definition. Ein unbekanntes Merkmal oder ein Wert außerhalb der Auswahl ist beim Bau eine Warnung, der Schreibweg lehnt es ab.
- Konnektor: `merkmal_definieren` mit `fuer: buchung`; Werte mit `buchung_anlegen` und `buchung_aendern` (`merkmale`, leer entfernt eines). Seite und `zeige B-…` zeigen sie im `buchungBlock` unter den festen Zeilen.

Ein **Wert** am Ding: `{wert, quelle, geprueft, notiz, gilt}`; mehrere Werte je Datum als Liste mit `gilt` (`docs/alternativen.md`). Ein Wert ohne Herkunft wird abgelehnt, seit der Konnektor direkt schreibt (Paket O-3, `wert_eintragen`); Bestandswerte ohne Quelle bleiben lesbar.

Die Software prüft nur die Form: bekannte Felder, erlaubte Typen, Stufen und Rollen, Auswahlwerte, Prüfdatum bei Veränderlichem, dass jede Art genau eine Grundform hat und jedes Ding eine bekannte Art. Ob „Frühstück“ für ein Refugi sinnvoll ist, entscheidet die Reise. Eine Stufe je Art (`stufe: {"*": aus, refugi: empfohlen}`) hängt am Schlüssel der Art.

**Buchungsstand eines Dings:** Er folgt seiner geltenden Buchung (`B-…`). Das freie Feld `buchung:` am Ding (bis 29.10.2026) wird weiter gelesen, aber vom Konnektor nicht mehr geschrieben: Eine Buchung ohne Nummer, Frist, Stornoregel und Herkunft wäre eine Tatsache ohne Herkunft (ADR-0001, Frage 5).

## Lesetext und seine Gliederung

Zu einem Ding gehört oft ein **Lesetext**: der Text am Anfang einer Etappe (Abschnitt „Zusammenfassung“, auf der Seite die Ebene „Der Weg“, `docs/design.md`) oder oben auf der Seite eines Orts (unter `## O-… Name` im Ortsdossier vor den Unterabschnitten, ADR-0008, #334) oder auf der Karte einer Unterkunft oder eines Aufenthalts. Er ist Wissen (Grundform), hängt aber an einer Bewegung, einem Ort oder einem Aufenthalt. Ein bestimmtes Lokal, Museum oder eine Unterkunft ist kein Text, sondern ein Ding am Ort (`an: O-…`); die Rubrik „Essen“ erzählt nur, was kein Ding ist (Küche der Gegend, wann man isst). Wie er aufgebaut ist, legt die Reise **je Art** fest, denn eine Wanderung erzählt man anders als eine Bahnfahrt oder einen Stadttag. Die Software kennt nur die Form einer Gliederung, keine Rubriken (ADR-0001, kein Katalog).

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

- **Am Aufenthalt** (Unterkunft und Aufenthalt ohne Nacht, #334, Product Owner 6.11.2026: die allgemeinste Form, ohne eigenes Dossier je Grundform): ein Feld am Ding in `routen.yaml`, mit Herkunft wie jede Aussage. Der Bau zeigt ihn mit einer Herkunftszeile auf der Karte des Dings an seiner Heimat, nie in einer Zeile oder Kachel. Preis, Frühstück und andere Fakten bleiben Merkmale.

  ```yaml
  unterkuenfte:
    U-02:
      lesetext:
        text: |
          **Das Haus.** …
        quelle: "Website des Hauses"
        geschrieben: 2026-11-06
        wer: Ida
  ```
- **Form im Text:** je Rubrik ein Absatz, der mit ihrem Namen als fettem Stichwort beginnt (`**Charakter.** …`). Rubriken ohne Inhalt fallen weg; die Reihenfolge der Datei ist die Lesereihenfolge. Die Herkunft steht wie bisher darunter.
- **Prüfung:** Die Software prüft die Form der Gliederung (Schlüssel, Name, bekannte Felder `name` und `hilfe`, kein Name doppelt). Beim Bauen ist ein Stichwort im Lesetext, das keine Rubrik der Art des Dings ist, ein Hinweis (kein Fehler); ein Lesetext am Aufenthalt ohne `text` oder `quelle` ist ein Fehler. Ohne Gliederung der Art wird nichts geprüft.
- **Konnektor:** `zeige E-…`, `O-…`, `U-…` und `A-…` nennen die Gliederung der Art mit der Hilfe je Rubrik, damit der AI-Client den Text in diesem Aufbau schreibt; `lesetext_schreiben` schreibt oder ersetzt ihn (ein fremdes Stichwort lehnt der Schreibweg ab), `art_definieren` pflegt die Gliederung (`lesetext`) und erhält sie beim Ändern anderer Felder (seit 29.10.2026).
- **Herkunft des Aufbaus** (Recherche 29.10.2026): Wanderführer und Tourenportale trennen den erzählenden Text von der Wegbeschreibung. Rother stellt jeder Tour Kopfdaten (Ausgangspunkt, Anforderungen, Einkehr, Varianten) und eine kurze Einleitung voran, dann folgt die Beschreibung; Cicerone nennt je Etappe Kennzahlen und Verpflegung vor dem Text. Outdooractive unterscheidet Kurzbeschreibung (Teaser, 50–300 Zeichen), Beschreibung (Erlebnis, Charakter und Sehenswertes, 900–2000 Zeichen) und Wegbeschreibung (so genau, dass man danach gehen kann), dazu Tipp, Sicherheitshinweise und Ausrüstung als eigene Felder. Wikivoyage gibt für Reiserouten ein Grundgerüst vor, von dem man weglässt, was nicht passt. Daraus der Grundaufbau Kurzzeile, Charakter, Verlauf in groben Zügen, Höhepunkte, Anforderungen, Ankommen; was eine Reise darüber hinaus wichtig findet (etwa „Im Vergleich zu gestern“, „Was andere sagen“, „Jahreszeit“), ergänzt sie in ihrer Gliederung. Die Beispielreise zeigt eine Gliederung für Wanderung und eine kürzere für Bahn. Für Orte zeigt sie eine Gliederung für Etappenorte (Ankommen, Versorgung, Umschauen), das Städtewochenende eine für die Stadt (Überblick, Essen, Unterwegs). Für Aufenthalte: die Pension der Wanderung (Das Haus, Ankommen, mit Text an der Pension Burgblick), das Museum des Städtewochenendes (Sammlung, Zeit).

## Sprache der Reise

`reise.yaml` trägt in den Eckdaten das Feld `sprache` (Kürzel einer Sprachdatei, Vorgabe `de`). Es gehört zur Grundform Reise und ändert nichts an den Grundformen, Arten oder Merkmalen: Datenschlüssel, Werte mit fester Bedeutung, IDs und Dateinamen sind in jeder Sprache dieselben; Namen von Arten, Merkmalen und Kategorien schreibt die Reise in ihrer Sprache (siehe [sprachen.md](sprachen.md)).

## Darstellung

Eine Art kann eine `farbe` aus der Palette der Seite tragen: `blau`, `braun`, `lila`, `gruen`, `tuerkis`, `oliv`, `grau`, `rosa`, `schiefer` (`engine/vorlage.html`, `--farbe-*`); ohne Angabe `grau`. Dazu ein `symbol` aus dem Zeichensatz der Seite (`engine/bauen.py` SYMBOLE, Lucide): `unterkunft`, `zelt`, `einkehr`, `ticket`, `museum`, `wandern`, `bus`, `bahn`, `schiff`, `flug`, `auto`, `rad`, `taxi`, `strecke`, `ort`, `karte`, `plan`; ohne Angabe das Zeichen der Grundform (Aufenthalt Bett, Bewegung Weg, Folge Plan). Die Seite zeigt Name, Farbe und Symbol der Art am Etikett jedes Dings, in der Zeitleiste des Tags, in der Legende der Karte und im Vergleich; sie kennt keine Art selbst (bis Paket O-5 trug `engine/vorlage.html` eine Liste von Verkehrsmitteln, `ART_TEXT`). `buchbar: true` gibt den Dingen der Art einen Buchungsstand (aus ihrer Buchung `B-…`, sonst „offen“; das frühere Feld `buchung:` am Ding stellt `neu.py nachziehen` um, #215), der auf der Seite unter „Zu buchen“ und im Stand der Vorbereitung erscheint; Vorgabe: Aufenthalte ja, Bewegungen und Folgen nein. Summen („Nächte: 5× Hotel, 3× Refugi“) zählen je Art.

## Karte (Epic #225, 2.11.2026)

Die Karte ist keine eigene Grundform, sondern eine Ansicht der Lage: Ist der Baustein `karte` an, baut der Bau sie aus allem mit Koordinaten (`engine/karte.py`): Orte (`punkt`), Unterkünfte und Aufenthalte (`punkt`, ADR-0004); ein Ort ohne eigenen Punkt liegt beim ersten Punkt seiner Unterkünfte und Aufenthalte. Auf der Übersicht stehen nur Orte des Plans (Station einer Strecke, Anfang oder Ende eines Tags, Ort einer Unterkunft oder eines Aufenthalts an einem Tag oder in einer Option); ein Ort, an dem andere Orte hängen, ist kein Punkt (`karte.orte[O-…].punkt: false`, seine Lage bleibt für die Linien; ADR-0008). Beide mahnt der Kartenstatus nicht als „ohne Lage“ an. Es braucht mindestens zwei Punkte. Der Rahmen ergibt sich aus den Punkten plus Rand. Name und Farbe eines Punkts kommen aus seiner Art; eine Kartenkategorie mit dem Schlüssel einer Art (Gruppe `punkt`) überschreibt sie. Jeder Punkt hat einen Stand: im Plan (an einem Tag des Plans), Alternative (nur in einer Option oder an einem Tag außerhalb des Plans; Umriss) oder ohne Tag. Strecken ohne Track verbinden ihre Stationen in Tagesreihenfolge (hat ein Tag genau eine Strecke, liegen seine Aufenthalte dazwischen) und gelten als schematisch. **Kartenansichten** stehen als Teil des Plans in `plan/routen.yaml`: `karten_ansichten: [{titel, tage, strecken, arten}]`; die Übersicht gibt es immer. `plan/karte.yaml` (in `reise.json` unter `routen.karte`) bleibt als Überschreibung: eine handgepflegte Karte sieht aus wie vorher. Ein Fehler in den Kartendaten lässt den Bau nicht scheitern; `route.karte_status` (gebaut, Grund, Zahl der Punkte, Einträge ohne Lage) zeigen `ueberblick` und `einstellung_setzen`.

## Kartenpunkte sind Dinge, Kategorien sind Arten (ADR-0007, Schritt d, #285)

Zusätzliche Punkte auf den Karten (Etappen- und Tageskarte, Karte im Wissensabschnitt) sind **Dinge**: ein Aufenthalt (`A-…`) mit Art, ID, Herkunft, Koordinaten (typisiertes Merkmal) und **`an:`** (der Strecke, an der er liegt, oder dem Block des Wissens, `W-05.der-hockstein`). Es gibt keine zweite Taxonomie: Was früher eine Kartenkategorie war, ist eine **Art** der Grundform `aufenthalt` mit den Feldern `gruppe` (`punkt`: Dinge an einer Strecke, Karte der Etappe; `wissen`: Dinge an einem Block des Wissens, Karte dort), `einzahl` (ein einzelner Punkt), `nummeriert` (der Punkt zeigt seine Nummer statt eines Symbols) und `sorten` (Zusatz je Sortenwort: `name`, `symbol`, `hinweis`, `umriss`); `farbe` darf zusätzlich `kontrast` oder `#rrggbb` sein, `symbol` auch `wasser` oder `apotheke`. **Eine Art darf ohne Merkmale sein** („Wasserstelle“). Die Legende der Karten und ihre Ansichten wählen nach Arten; `plan/kategorien.yaml` und `category_define` entfallen (das Werkzeug bleibt als Alias von `kind_define`, `categories` als Alias lesend).

Was ein Punkt über Kategorie und Koordinaten hinaus trug, steht als Merkmale der Art, gelesen nach **Rolle** (nie nach Namen, wie `kosten`): `nummer` (Typ `zahl`; die Nummer eines nummerierten Punkts), `alias` (`text`; weitere Namen getrennt durch `;`, aus ihnen werden im Etappentext Kartenlinks), `sorte` (`text`; das Sortenwort), `osm` (`text`; Objekt in OpenStreetMap, `node/123`), `trinkbar` (`text`; `yes` oder `no` aus OpenStreetMap), `oeffnung` (`text`; Öffnungszeiten laut OpenStreetMap, `opening_hours`), `bezug` (`text`; die Kennung der Unterkunft oder des Orts, die der Punkt ist; zeigt er auf einen Ort `O-…` und hat der Punkt keine eigenen Koordinaten, liegt er beim Ort, ADR-0008; einen unbekannten Ort lehnt der Bau ab). Quelle und Prüfdatum stehen am Ding (Herkunft und `geprueft` an den Koordinaten). Ein Kartenpunkt ist nicht buchbar, steht nicht in der Liste „Ohne Tag“ und liegt nicht auf der automatischen Übersichtskarte, sondern auf den Karten der Etappe und des Wissens. Benannte Wegpunkte eines GPX-Tracks werden weiter nummerierte Punkte ohne Ding. `kartenpunkte_holen` legt aus OpenStreetMap Dinge der gewählten Art an (ein zweiter Aufruf aktualisiert dieselben Dinge nach ihrem OSM-Bezug; nichts wird gelöscht, die IDs bleiben).

**Alte Dateien** (`plan/punkte.yaml`, die Punkte in `inhalt/wissen-punkte.yaml`, `plan/kategorien.yaml`) werden weiter gelesen, wenn es sie gibt; `neu.py nachziehen` stellt sie um: neue IDs aus `ids.yaml` (nie neu vergeben), die Kategorien werden Arten (mit den Rollen der Merkmale, die ihre Punkte brauchen), Punkte ohne passende Kategorie und mit `ohne_karte` werden gemeldet und nicht übernommen. Die Datei `inhalt/wissen-punkte.yaml` bleibt für ihre übrigen Angaben (`grundkarten`, `namensnennung`, `stand`), ohne `bloecke`.

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
- 29.10.2026 (frieda-reist #135): Reisende, Preise je Ding und Ab-Termin an der Buchung; `ab`/`an` an Bewegungen mit Anschlussprüfung; `ausserhalb` am Ort; Beleg auch aus dem Gespräch (`beleg_anlegen`); gerade Angelegtes ist im selben Gespräch nutzbar, weil der Schreibweg mit dem Repo prüft.
- 31.10.2026 (Product Owner): Form eines Merkmals um `nach_buchung` ergänzt: Die Reise legt fest, welche Merkmale eines Dings nach der Buchung sichtbar bleiben (etwa „Charakter“); alle übrigen stehen dann auf der Seite „Aus der Planung“.
- 31.10.2026 (frieda-reist #166, Product Owner): Angebot und Buchung getrennt: Merkmale der Buchung je Art (`buchung_merkmale`, Werte in `merkmale` der Buchung, Herkunft der Buchung); Zahlstand `zahlung` als festes Feld mit festen Werten (`offen`, `angezahlt`, `bezahlt`, `vor_ort`, `inklusive`, `erstattet`); der Wächter meldet offene Zahlungen, wenn die Reise `regeln.waechter_zahlung` einschaltet.
- 29.10.2026 (frieda-reist #76, Product Owner): Buchung als eigenes Ding `B-…` (`buchungen:` in `plan/routen.yaml`) mit Beleg-Datei in der Ablage; Konnektor `buchung_anlegen`, `buchung_aendern`; Wächter meldet Fristen und Stornofristen; die Seite zeigt die Buchung bei ihrem Ding und hängt Belege an.
- 6.11.2026 (frieda-reist #370, Product Owner, [ADR-0010](adr/0010-gegenstand.md)): Grundform **Gegenstand** (`G-`, `plan/packliste.yaml`) mit den Arten der Reise als Kategorien; Rolle `summe` (Typ `zahl` oder `geld`, mehrere je Art) verallgemeinert `kosten`, das als Alias bleibt; Baustein `packliste`; Packstand live beim Rückmeldedienst.
