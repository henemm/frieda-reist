# Context: kennzahlen-268

## Request Summary
#268 (Teil 2 von #215): Die Regeln für Kennzahlen (Gehzeit/Dauer, Länge, Aufstieg/Abstieg) und das Merkmal `summiert` einer Art werden an genau einer Stelle gerechnet, im Routenmodell (`engine/routen.py`). Seite (`engine/vorlage.html`) und Konnektor (`engine/konnektor.py`) zeigen nur das Ergebnis. Vorbereitung für #269 (Etappe als Art der Reise).

## Related Files
| File | Relevance |
|------|-----------|
| `engine/routen.py` 400–428 | `zahl`, `minuten`, `kennwerte`: erkennt Kennzahl-Schlüssel über den Katalog (`inhalt.kennzahl.*`) und liest Zahlen; die eine Rechenstelle, die es schon gibt |
| `engine/routen.py` 1256–1270 | `auto_werte`: berechnete Merkmale einer Option (gehzeit, laenge, hoehenmeter, tage, unterkuenfte); `hoehenmeter` formatiert `↑ … m, ↓ … m` fest im Code |
| `engine/routen.py` 1706–1746 | `summe`, `option_summe`: Summe über Tage; summiert nur Arten mit `summiert: true`; liefert `min, auf, ab, km, fehlend, laengster, unterkunftstypen, unvollstaendig`, aber keine Werte je Tag und keine Werte je Strecke |
| `engine/routen.py` 1601, 1687, 1767, 1806–1808 | Ausgabe: `summe` der Reise, der Pläne, der Optionen; je Strecke `summiert` und rohe `kennzahlen` (Texte aus routen.yaml) |
| `engine/vorlage.html` 964–977 | `REGEL.gehzeit/aufstieg/abstieg/laenge`: zweite Erkennung der Kennzahl-Schlüssel (gleiche Katalogwörter, eigene Regex) |
| `engine/vorlage.html` 1271–1274 | `summiertArt`, `fahrtVon`: liest `summiert` der Art selbst (für Linienstil, Gehzeit/Dauer, Etappenkarte) |
| `engine/vorlage.html` 1326–1333 | `summeText`: zeigt Gehzeit/km/auf-ab, wenn `s.km` gesetzt ist |
| `engine/vorlage.html` 1337–1348 | `kennzahlPaar`, `kennzahlLeiste`: ordnet rohe Schlüssel den Kennungen zu (zweite Erkennung), Formatierung `↑ v m` |
| `engine/vorlage.html` 2243–2257 | `tagKm`, `tagMin`: **rechnen die Tagessumme ein zweites Mal** aus den rohen Texten; `tagKm` mit fest deutschem Muster `/^(länge|strecke|km)/` und nur Werten mit „km“, `tagMin` nur `h:mm` (routen.py liest auch „2 h“) |
| `engine/vorlage.html` 2264–2274 | `steckbrief`: entscheidet „Wanderdaten?“ mit `s.min || s.km || s.auf` |
| `engine/vorlage.html` 2916–2941 | `tagZeile` (nutzt tagMin/tagKm), `reiseKennzahlen` (wieder `s.min || s.km || s.auf`) |
| `engine/konnektor.py` 664–673 | `Handbuch.summe`: Text der Summe; entscheidet mit `s.get("min")`; Aufrufe 734, 861, 1190 |
| `engine/texte_*.py` | `inhalt.kennzahl.*` (Erkennungswörter), `seite.kennzahl.*`, `seite.auto.*`, `konnektor.summe.*` |
| `engine/tests/test_routen.py` 325–390, 557 | Tests zu `summe` (Bus zählt nicht, Unterkunftstypen) |
| `engine/tests/test_texte.py` 607 | Test zu `Handbuch.summe` |
| `engine/tests/test_bauen.py` 651 | Summe eines Plans |
| `docs/design.md` 13, 75, 85, 178 | Kennzahlenleiste, „ein Wert steht einmal“, Kennzahlen der Reise mit/ohne Wanderdaten |

## Existing Patterns
- Die Seite bekommt fertige Werte aus `routen.py` (z. B. `summe`, `arten.kosten`, `eltern`); „die Seite kennt keine Art selbst“ (Kommentar 1614). Dieses Muster wird auf die Kennzahlen ausgeweitet.
- Erkennung von Inhaltswörtern über den Katalog (`texte.inhaltswoerter`, `D.inhaltswoerter`) für alle Sprachen zugleich.
- Formatierung in der Sprache der Hülle bleibt auf der Seite (`dauer`, `kmText`, `zahlText`), im Konnektor über `tk(...)`.

## Dependencies
- Upstream: `plan/arten.yaml` der Reise (`summiert`, `auto`-Merkmale), `routen.yaml` der Strecken (rohe `kennzahlen` als Texte), Textkatalog.
- Downstream: Seite (Tageszeile, Steckbrief, Reiseüberblick, Optionen, Kennzahlenleiste, Wegtabelle, Karte), Konnektor (Überblick, Optionen, Pläne), Browser-Tests, `test_routen`, `test_texte`.

## Existing Specs
- Keine eigene Spec zu Kennzahlen in `docs/specs/`; Regeln stehen in `docs/design.md` und im Code. #215 Punkt 2 beschreibt das Ziel.

## Befund: wo die Regel heute doppelt oder abweichend steht
1. **Tagessumme**: `routen.summe` (pro Reise/Plan/Option) und `tagKm`/`tagMin` in der Vorlage (pro Tag) mit eigenen, engeren Mustern. Abweichung: englische Schlüssel („Length“) und Zeiten wie „2 h“ zählen auf der Seite nicht.
2. **Erkennung der Schlüssel**: `kennwerte` (Python) und `REGEL.*`/`kennzahlPaar` (JS).
3. **„Hat Wanderdaten?“**: drei Bedingungen (`s.km` in `summeText`, `s.min` im Konnektor, `s.min||s.km||s.auf` in Steckbrief und Reiseüberblick).
4. **`summiert`**: `routen.summe` filtert; die Vorlage liest es in `summiertArt` erneut (für Summen in tagKm/tagMin doppelt; für Linienstil und Gehzeit/Dauer reine Darstellung).
5. **Fester Text im Code**: `auto_werte` `"↑ … m, ↓ … m"`; Seite `↑ ${v} m`.

## Risks & Considerations
- Ausgabeformat von `routen.py` ändert sich (neue Felder je Tag/Strecke) → Instanz-Tests der einbindenden Reisen mit dem Branch laufen lassen (CLAUDE.md).
- Kein Format der Reisedaten ändert sich (nur abgeleitete Werte) → kein `neu.py nachziehen` nötig; in der Analyse bestätigen.
- Sichtbare Werte dürfen sich für die Beispielwanderung nicht ändern (außer bewusst behobene Abweichungen); Stadtwochenende ohne Wanderdaten darf keine Gehzeit/km zeigen.
- #269 baut darauf auf: die neue Stelle soll schon „Gehzeit vs. Dauer“ aus `summiert` liefern, ohne Etappen-Sonderfall.
- `vorlage.html` ist groß und viel getestet (Browser-Tests, WebKit); Änderungen klein halten.

## Analysis

### Type
Feature (Umbau ohne neue Funktion; behebt nebenbei Abweichungen zwischen Seite und Routenmodell)

### Zusätzliche Befunde der Analyse
- **Kombinierte Arten** (Strecke mit `art: [a, b]`): `routen.summe` und `strecke_aus.summiert` nehmen `summiert` der Art `kombiniert`; die Seite (`summiertArt`) nimmt „irgendeine der Arten ist summiert“. Bei `[wandern, bahn]` zeigt die Seite heute Gehzeit, Linienstil Fuß und zählt die Strecke in `tagKm`/`tagMin`, die Summe des Plans nicht. Nach dem Umbau gilt überall die Regel aus `routen.py`.
- Je Tag gehen heute keine Kennzahlen an die Seite (Tag-Dict in `routen.py`, nur `strecken: [{id, wahl}]`); `tag_min` wird nur intern für `laengster` gerechnet.
- Die rohen Kennzahlen einer Wanderstrecke kommen bei Dossier-Etappen über `Routen.strecke` (`setdefault("kennzahlen", …)`) aus `inhalt/etappen.md`; `strecke_aus` gibt sie weiter.
- Beispielreisen (gebaut und ausgelesen): Wanderung E-01 bis E-04 summiert, alle vier Kennzahlen vorhanden (`ca. 3:40 h`, `8,1 km` …), Summe 595 min / 25,4 km / ↑1075 / ↓1025, `fehlend` leer. Stadtwochenende: keine summierte Strecke, Summe 0, `fehlend` leer. Beide Semantiken für „hat Kennzahlen“ ergeben dort dasselbe → keine sichtbare Änderung an den Beispielen.
- Weitere Verbraucher: Tabellen der Pläne/Zeitachse (`vorlage.html` ~2291, ~2304) nutzen `tagMin`; `reiseKennzahlen` (~3109) speist die Kennzahlenleiste der Reise; `konnektor.py` 753, 792 geben rohe `kennzahlen` nur als Text aus (keine Rechnung, bleibt).
- **Tageswerte je Plan:** Die Tage eines Plans (`plaene()[].tage`) entstehen in einem eigenen `Routen(..., zwang).bauen()`-Lauf. Werden die Tageskennzahlen in `bauen()` beim Bilden des Tag-Dicts gerechnet, tragen `R.tage` und jeder `p.tage` automatisch die Werte ihrer eigenen Wahl (Beispielwanderung: P-A 610 min, P-B 595 min). Keine Rechnung über globale Tag-IDs.
- **Weitere Lesestellen von `summiert` in der Vorlage** (über `artDef(a).summiert` statt `summiertArt`): `streckeZeile` (~1410, Name des Verkehrsmittels ausblenden), Wegverlauf (~1476, Klasse `fahrt`), Legende der Karte (~2835, filtert Arten). 1410 und 1476 arbeiten auf `R.strecken`-Objekten → auf `st.summiert` umstellen. 2835 filtert Art-Schlüssel für die Legende (Ebene Art, nicht Strecke) → bleibt beim Merkmal der Art aus `R.arten`, ist reine Darstellung.
- **Alle Aufrufer von `summiertArt`** übergeben `R.strecken[id]`-Objekte oder einen Ersatz ohne `art` (`|| {}`, `|| {titel: id}`); die Musterseite (~4047) nimmt `Object.entries(R.strecken)`. Umstellung auf `st.summiert` ist damit sicher; ein Ersatzobjekt ergibt wie heute „nicht summiert“.
- Randbedingungen aus Tests: `test_design.py` (keine Art-Namen in der Vorlage; kein `.get("gehzeit")` in `engine/*.py`), `test_seite_sprachen.py` 247–251 (`REGEL.gehzeit/laenge` in beiden Sprachen; bleibt, weil `kennzahlPaar` bleibt).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/routen.py` | MODIFY | Innere Schleife von `summe` als `strecken_summe(strecken) -> {min, auf, ab, km, fehlend}` ausgliedern; `summe` nutzt sie je Tag; Tag-Dict in `bauen()` bekommt `kennzahlen: {min, km, auf, ab, fehlend}` (Zahlen; gilt damit für `R.tage` und je Plan `p.tage`); `summe` bekommt `mit_kennzahlen` (bool); `auto_werte` Höhenmeter-Text aus dem Katalog |
| `engine/vorlage.html` | MODIFY | `tagKm`/`tagMin` entfallen, Aufrufer (tagZeile, Tabellen) lesen `t.kennzahlen`; `summeText`, `steckbrief`, `reiseKennzahlen` entscheiden nur über `s.mit_kennzahlen`; `summiertArt`, `streckeZeile` und Wegverlauf lesen nur `st.summiert` (Legende der Karte bleibt auf Art-Ebene); `↑ ${v} m`/`↓ ${v} m` in `kennzahlPaar` über `T()` |
| `engine/konnektor.py` | MODIFY | `Handbuch.summe` entscheidet über `mit_kennzahlen`; fehlende Angaben wie auf der Seite kennzeichnen statt `0:00` zu zeigen (neues Verhalten, eigenes Akzeptanzkriterium, neuer Katalogschlüssel in allen Sprachen) |
| `engine/texte_*.py` | MODIFY | Schlüssel für Höhenmeter-Text in `auto_werte` und für `↑/↓ … m` der Kennzahlenleiste (falls vorhandene Schlüssel `seite.kennzahl.auf_ab` nicht passen), in allen Sprachen |
| `engine/tests/test_routen.py` | MODIFY | Tageswerte (auch „2 h“, englischer Schlüssel), `mit_kennzahlen` beider Beispielreisen, kombinierte Art |
| `engine/tests/test_texte.py` | MODIFY | `Handbuch.summe` mit `mit_kennzahlen` und mit fehlenden Angaben |
| `engine/tests/` (Browser) | MODIFY/CREATE | Tageszeile zeigt Werte aus `routen.py` (Wanderung unverändert, Stadtwochenende ohne Gehzeit/km) |
| `docs/design.md` | MODIFY | Regel „Kennzahlen rechnet das Routenmodell, die Seite zeigt sie“ ergänzen |

### Scope Assessment
- Files: ca. 8 (davon 3 Code, Rest Texte, Tests, Doku)
- Estimated LoC: +120/−50 (Code ca. +55/−45, Tests ca. +60)
- Risk Level: MEDIUM — Vorlage und Routenmodell sind zentral; sichtbare Werte der Beispiele bleiben gleich, Abweichungen ändern sich nur bei Sonderfällen (kombinierte Art, „2 h“, englische Schlüssel)

### Technical Approach
Empfehlung (Plan-Bewertung, Analyse bestätigt):
1. **Tageswerte schlank**: eine Rechenstelle `strecken_summe`; `summe` addiert die Tage; jeder Tag bekommt `kennzahlen` als Zahlen. Die Seite formatiert in der Sprache der Hülle (`dauer`, `kmText`).
2. **„Hat Kennzahlen“ = mindestens eine summierte Strecke** in den Tagen (`summe.mit_kennzahlen`). Folgt direkt aus `summiert`, braucht keinen Sonderfall `min||km||auf`; fehlen Angaben, zeigt die Seite „Angaben fehlen“ (die Texte gibt es schon, sie sind heute bei ganz fehlenden Angaben unerreichbar). An den Beispielen keine Änderung.
3. **`summiert` nur aus dem Strecken-Dict** (`st.summiert`, Regel aus `routen.py` inkl. kombinierter Art).
4. **Feste Texte in den Katalog** (`auto_werte`, `↑/↓ … m`).
5. **Nicht in #268**: Zuordnung roher Kennzahl-Namen zu Kennungen (`REGEL.gehzeit` …, `kennzahlPaar`) und Dossier-Etappen (`bauen.py` 441, 1141–1150). Gehört zu #269 (Etappe als Art, Etappen werden Strecken); hier umgebaut, würde es dort noch einmal umgebaut. Vermerkt in #268 und #269 (Kommentar 4.11.2026).
6. Kein Format der Reisedaten ändert sich → kein `neu.py nachziehen`. Ausgabeformat (`daten.json`) bekommt neue Felder → Instanz-Tests der einbindenden Reisen vor dem Vorspulen mit dem Branch laufen lassen.

Varianten (aus der Plan-Bewertung):
| Variante | Vorteil | Nachteil |
|---|---|---|
| Tag: volle `summe` | eine Funktion | sinnlose Felder je Tag (Nächte, Unterkunftstypen) |
| **Tag: schlank über `strecken_summe`** | klein, eine Rechenstelle | ein Feld mehr |
| „hat Kennzahlen“: alt `min\|\|km\|\|auf` | Verhalten bleibt exakt | Sonderregel; Wanderung ohne Angaben verschwindet still |
| **„hat Kennzahlen“: summierte Strecke vorhanden** | folgt aus `summiert`, zeigt Lücken ehrlich | Plan mit summierter Strecke ohne Angaben zeigt „Angaben fehlen“ statt nichts |
| Namenszuordnung jetzt | doppelte Erkennung ganz weg | zieht Dossier-Etappen hinein, doppelte Arbeit mit #269 |
| **Namenszuordnung in #269** | #268 bleibt klein | `REGEL.gehzeit` bleibt vorerst in `kennzahlPaar` |

Reihenfolge: RED-Tests (Tageswerte, `mit_kennzahlen`, kombinierte Art, Konnektor) → `routen.py` → Vorlage → Konnektor → Katalog → Browser- und Instanz-Tests.

### Dependencies
- `routen.summe` ← `bauen()` (Reise), `plaene()`, `option_summe`/`wahl_aus`, `auto_werte`; Ergebnis als `D.route` über `bauen.py`.
- Konsumenten: Vorlage (`summeText`, `steckbrief`, `reiseKennzahlen`, `tagZeile`, Tabellen, Kennzahlenleiste, Linienstil, Etappenkarte), Konnektor (`Handbuch.summe`, Aufrufe 735, 862, 1190).
- `schreiben.py`, `waechter.py`, `karte.py`, `neu.py` nicht betroffen.

### Open Questions
- Keine, die den Product Owner brauchen: Die Semantik „mindestens eine summierte Strecke“ ändert an keiner Beispielreise etwas Sichtbares und folgt ADR-0001 (die Reise sagt mit `summiert`, was zählt). Bei echten Reisen prüfen die Instanz-Tests vor dem Vorspulen, ob sich etwas Sichtbares ändert.
