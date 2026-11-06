# ADR-0010: Der Gegenstand ist eine Grundform, Kategorien sind Arten, die Rolle „wird summiert“

Status: gilt · Entschieden vom Product Owner am 6.11.2026 · Issue: frieda-reist #370 (Packliste)

Steht unter [ADR-0001](0001-kern.md) und ist die **einzige Erweiterung des Kerns** durch die Packliste: eine neue Grundform. Alles Weitere benutzt Vorhandenes: Arten und Merkmale ([ADR-0001](0001-kern.md), `docs/ontologie.md`), den Elternbezug `an:` ([ADR-0007](0007-elternbezug.md)), die Heimat ([ADR-0003](0003-heimat.md)), den Reisespeicher ([ADR-0009](0009-reisespeicher.md)).

## Kontext

Eine Reise braucht eine Packliste: was mitkommt, in Kategorien, wer es packt, was schon gepackt ist, mit Summen (Gewicht, Volumen, Preis). Der Product Owner hat am 6.11.2026 entschieden:

- Frieda führt **kein Inventar** und keine Anlässe. Ausgangsbasis einer neuen Packliste ist eine frühere Reise („nimm die Reise von damals“) oder ein Vorschlag der KI im Gespräch. Frieda belegt nichts vor.
- **Kategorien** gehören der Reise (Darstellung auf der Seite), kein Katalog in der Software.
- **Erweiterbar wie alles in Frieda:** Merkmale je Kategorie (Gewicht …), mit Summen.
- **Packmodus nach Raum** ist nett, kein Muss. Raum ist ein gewöhnliches Merkmal.
- Werkzeuge englisch (`gear_…`) mit deutschem Alias, Wörter auf der Seite aus dem Textkatalog je Sprache.

Die Frage der Prüfstelle (ADR-0001, Frage 2) lautet: Muss die Software dafür etwas Neues kennen, oder trägt die Reise es? Ein Gegenstand ist weder ein Aufenthalt noch eine Bewegung noch eine Folge: Er ist nicht irgendwo, nicht unterwegs und kein Abschnitt, sondern **etwas, das mitkommt**. Er hat eigene Rechenbedeutung (Summen, Packstand) und eine eigene Heimat, deshalb ist er eine Grundform und kein Merkmal eines anderen Dings.

## Entscheidung

1. **Gegenstand ist eine Grundform** (`gegenstand`) mit eigener ID `G-01`, `G-02` … (wie Buchung `B-` und Aufenthalt `A-`). Er hat den Kern jedes Dings: feste ID, Grundform, Art, Titel, Merkmale, Verlauf. IDs werden nie neu vergeben und nie gelöscht; „weglassen“ ist der Status `entfaellt` mit Verlaufseintrag (und Grund).
2. **Die Kategorie ist die Art.** `plan/arten.yaml` kennt Arten mit `grundform: gegenstand` (Kleidung, Schlafen, Küche, Apotheke …). Die Reise legt sie im Gespräch an (`art_definieren`), die Software kennt keine. Eine Art darf ohne Merkmale sein (Städtewochenende).
3. **Merkmale wie heute.** Gewicht (`typ: zahl`, `einheit: g`), Raum (`typ: auswahl` oder `text`), Anzahl, Preis: gewöhnliche Merkmale der Art. Die Software liest nur Typ und Rolle, nie einen Namen. **Wer packt**, ist kein Merkmal, sondern das Feld `wer` des Gegenstands (eine Person der Reise), weil die Software damit rechnet (Packstand).
4. **Elternbezug `an:`** nach ADR-0007 an eine Strecke, einen Aufenthalt, eine Unterkunft oder einen Ort („Steigeisen für E-04“, „Hüttenschlafsack an U-03“); **nicht an einen Tag** (ein Tag ist kein Elternelement, ADR-0007: was ein Tag braucht, ergibt sich aus seinen Dingen). Geprüft wird: bekanntes Ding, kein Tag. Ein Kreis ist nicht möglich, weil nichts an einem Gegenstand hängt. Seine Heimat bleibt die Packliste (ADR-0003); an der Strecke, dem Aufenthalt, der Unterkunft oder dem Ort steht nur eine Zeile „Mitnehmen“ mit Link. Hängt ein Gegenstand an einem Ding, das nur in verworfenen oder ersetzten Möglichkeiten vorkommt, meldet der Bau eine Warnung und die Seite zeigt ihn gedämpft.
5. **Datei:** `plan/packliste.yaml` der Reise, Liste `gegenstaende:` mit `id`, `art`, `titel`, `merkmale`, `an`, `wer`, `notiz`, `status`, `verlauf`. Eine neue Datei geht wie jede Reisedatei über den Schreibweg und damit in den Reisespeicher (ADR-0009). Es ist keine Umstellung in `neu.py nachziehen` nötig, weil kein bestehendes Format sich ändert.
6. **Die Rolle „wird summiert“.** Die Rolle `kosten` (ein Merkmal je Art, das die Seite über die Reise summiert, Typ `geld`) wird zur allgemeinen Rolle `summe` (Typ `zahl` oder `geld`); `kosten` bleibt als Alias für `summe` mit dem Typ `geld`. Die Seite und der Konnektor zeigen die Summe je Kategorie und gesamt mit der Einheit des Merkmals (bei Geld mit der Währung des Werts, mehrere Währungen werden getrennt summiert). **Mehrere summierte Merkmale je Art sind erlaubt** (Gewicht und Preis); `kosten` bleibt je Art einmalig, weil es zugleich der Preis der Nacht einer Unterkunft ist. Gegenstände mit Status `entfaellt` zählen nicht. Der Wert eines Eintrags gilt für den ganzen Eintrag („Socken, 240 g“) und wird nicht mit einer Anzahl multipliziert.
7. **Der Packstand liegt live beim Rückmeldedienst** (`<ablage>/<reise>/packstand.json`, `{G-ID: {Person: Zeitpunkt}}`), wie die Aufgaben, nicht als Version im Reisespeicher. Abhaken ohne Netz ist so möglich, ohne dass jeder Haken ein Verlaufseintrag wird. Ein Gegenstand mit `wer` wird von dieser Person abgehakt, einer ohne `wer` von jeder Person für sich. Der Dienst ist der einzige Schreiber; er prüft Rolle, Baustein und Status der Reise.
8. **Der Baustein `packliste`** (`reise.yaml`, `bausteine`) schaltet Reiter, Werkzeuge und Schreibrecht ein. Die Packliste ist in jedem Status schreibbar (auch `unterwegs`: Nachkaufen vor Ort) und in der Nachlese (`danach`), nicht im Archiv.
9. **Rollen:** Mitwirkende legen Gegenstände an, ändern eigene (selbst angelegt oder ihnen zugewiesen, `wer`) und haken ab; Organisator:innen ändern alles und übernehmen Packlisten aus früheren Reisen. Gäste lesen.
10. **Ausnahme von der Herkunftspflicht** (ADR-0001, Punkt 5 und Frage 5): Ein Gegenstand braucht **keine `quelle`**; eine Regenjacke hat keine. Die Ausnahme gilt nur für Gegenstände und ihre Merkmale und ist im Schreibweg ausdrücklich getestet. Merkmale mit `veraenderlich: true` behalten das Prüfdatum, die Herkunft bleibt freiwillig (`quelle` ist ein erlaubtes Feld).
11. **Übernahme aus einer früheren Reise** (`packliste_uebernehmen`, Muster `arten_uebernehmen`): nur von Reisen, auf denen die Person dabei ist. Übernommen werden Kategorien (Arten mit `grundform: gegenstand`, samt Merkmalen) und Gegenstände als **Vorschlag**: mit neuen IDs, ohne Packstand, ohne `an:` (die Dinge der alten Reise gibt es hier nicht), ohne `wer`; weggelassene bleiben weg; Werte von Merkmalen, die eine schon vorhandene Kategorie nicht kennt, entfallen und werden in der Antwort genannt. Danach streicht und ergänzt der AI-Client im Gespräch.

## Begründung

- **Der Kern verlangt es nicht anders.** Ein Gegenstand hat Rechenbedeutung (Summe, Packstand, Heimat). Als Merkmal eines anderen Dings wäre er unauffindbar, als Aufenthalt falsch (er ist nirgends). Eine Grundform mit Arten der Reise ist das kleinste Neue, das ADR-0001 zulässt.
- **Keine Kategorien in der Software.** Die Software kennt die Grundform und die Rolle, nicht „Kleidung“ oder „Gewicht“ (Prüfstelle Frage 2).
- **Eine Rolle statt einer weiteren Sonderregel.** `kosten` summierte schon ein Merkmal; `summe` verallgemeinert es, ohne dass die Software ein Merkmal beim Namen kennt.
- **Live statt Version für den Packstand.** Beim Packen hakt man viele Male ab, oft ohne Netz. Das gehört zu den Dingen wie Aufgaben, die live liegen, nicht in den Verlauf der Reise.
- **Keine Herkunftspflicht, weil sie hier keinen Sinn hätte.** Die Herkunft schützt vor erfundenen Fakten (Fahrpläne, Preise); „Regenjacke“ ist keine Behauptung über die Welt. Was sich ändern kann (ein Preis), behält sein Prüfdatum.

## Konsequenzen

- **Software:** `routen.GRUNDFORMEN` um `gegenstand`, `ROLLEN` um `summe` (`rolle_typen`, `SUMMEN_ROLLEN`, `ROLLEN_MEHRFACH`), neues Modul `engine/packliste.py` (Prüfen, Aufbereiten, Summen), `bauen.py` lädt `plan/packliste.yaml` und legt `packliste` in `daten.json` ab, `neu.py` vergibt `G-`-IDs, `schreiben.py` bekommt `gegenstand_anlegen`, `gegenstand_aendern` und `packliste_uebernehmen`, `rueckmeldungen.py` den Packstand (`GET/PATCH /<reise>/packstand`), `reise.py` den Baustein `packliste` und die Aktionen `gegenstand`, `packen`, `packliste_uebernehmen`. Das neue Modul steht in `betrieb/deploy.sh` (Konnektor und Schreibweg).
- **Konnektor:** `packing_list` (`packliste`), `gear_create` (`gegenstand_anlegen`), `gear_update` (`gegenstand_aendern`), `gear_pack` (`gegenstand_packen`), `packing_list_adopt` (`packliste_uebernehmen`); `show G-…`, `search` und `overview` kennen Gegenstände; bei einer Strecke, einem Aufenthalt, einer Unterkunft und einem Ort steht „Mitnehmen“. Der englische Fachbegriff ist **gear** (nicht „item“, das der Katalog für „thing“ ausschließt).
- **Seite:** Reiter „Packliste“ als Heimat der Grundform Gegenstand, Ansicht Planen (nach Kategorie, Summen) und Packen (Gruppierung nach einem beliebigen Merkmal, Abhaken je Person, offline gesammelt und nachgereicht), Zeile „Mitnehmen“ am Elternelement; neue Bausteine nach ADR-0002 an den vier Stellen.
- **Beispielreisen:** Wanderung mit Gewicht, Raum, Preis, Summen, einem gemeinsamen Gegenstand mit `wer` und Gegenständen mit `an:`; Städtewochenende klein, ohne Gewicht und Raum.
- **Prüfstelle ADR-0001:** 1 ja (Kategorien und Merkmale in der Reise; beide Beispielreisen), 2 ja (nur Grundform und Rolle), 3 ja (keine KI), 4 ja (fünf Werkzeuge, `show G-…`), 5 Ausnahme Punkt 10, 6 ja (Rollenregel wie bei Buchungen, Verlauf mit Person und Datum), 7 ja, 8 ja (Abhaken offline), 9 ja, 10 dieses ADR, `docs/ontologie.md`, `docs/konnektor.md`, `docs/design.md`, `docs/produkt.md`.

## Verlauf

- 6.11.2026: Entschieden vom Product Owner (Issue #370, Packliste); Umsetzung in drei Paketen: (1) Modell, Schreibweg, Konnektor, Rolle `summe`, Beispielreisen; (2) Seite und Packstand; (3) Texte, Dokumentation, Rest.
