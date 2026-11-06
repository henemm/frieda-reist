# Kontext: Orte als Möglichkeiten einer Wahlstelle (#353, Schritt 2)

## Anfrage
Der Grundsatz „Alternativen kann jedes Ding sein, nur der Tag nicht“ (Product Owner, 6.11.2026, #353) gilt ganz: Nach den Aufenthalten ohne Nacht (Schritt 1, PR #355, in main seit 6.11.2026) sollen auch **Orte (`O-…`)** Möglichkeiten einer Wahlstelle sein können, etwa als Schlechtwetter- oder Gipfelalternative. Laut Issue-Kommentar gehört dazu „Orte mit Art und Merkmalen“. Das ist durch ADR-0008 Schritt a schon erledigt: Orte haben eine freiwillige Art mit Merkmalen (`self.o_art`, `self.mk_ort`). Laut ADR-0008 ist keine Umstellung im Datenformat nötig, solange `orte:` an der Option nur dazukommt.

## Betroffene Dateien
| Datei | Bedeutung |
|------|-----------|
| `engine/routen.py` | Optionen lesen und prüfen (≈ Zeile 655, Prüfung `option_aufenthalt`), `art_der_wahl` (≈ 1158), `arten_der_option` (≈ 1177), Kriterien und Werte (≈ 1261 ff., `a_extra` neben `u_extra`/`s_extra`; `mk_ort` bekommt heute nur den Katalog der eigenen Art), `option_werte`/Lücken (≈ 1357), `nacht()` (≈ 1508: Nacht als `O-…`, als `V-…` nur mit Unterkünften), `aufenthalte_des_tages` (≈ 1504), `tag_lauf` (Ort am Abend/Anfang, Anschluss), `anschluss()` (≈ 1363, nur `folge`), `regeln_im_plan` (≈ 932, `im_plan` enthält Orte), Ausgabe der Option für die Seite (≈ 1846, `aufenthalte` bereits ausgegeben), Ausgabe `orte` (≈ 1712) |
| `engine/schreiben.py` | `option_bauen` (≈ 2298), `option_aendern` (≈ 3623), `option_inhalt_ok` (≈ 3571: genau eine Sorte, nur Strecken + Aufenthalte zusammen), `PLAIN_FELDER` |
| `engine/konnektor.py` | `OPTION_FELDER` (≈ 2561) bekommt `orte` |
| `engine/texte_de.py`, `engine/texte_en.py` | Beschreibung des Felds `konnektor.feld.option_felder.orte`, Prüfsätze, Ablehnungen `option_bauen.2`/`option_aendern.5` (nennen heute vier Sorten) |
| `engine/karte.py` | `dinge_bezug` (≈ 137–160): Aufenthalte der Möglichkeiten als „plan“/„alternative“; Orte haben eigene Regeln (Übersicht nur mit Orten des Plans, ADR-0008 Schritt b) |
| `engine/kalender.py` | zeigt nur Entschiedenes (`aufenthalte_offen`); für Orte am Tag gibt es keinen eigenen Eintrag |
| `engine/vorlage.html` | `optionBlock` (≈ 2276) und `optionEinzelheiten` (≈ 2320): Zeile je Ding der Möglichkeit; für Orte gibt es eine Ortsseite (Heimat, ADR-0003) und eine Ortszeile |
| `engine/tests/test_option_aufenthalte.py`, `engine/tests/seiten_option_aufenthalt.mjs` | Vorlage für die Tests von Schritt 2 |
| `docs/ontologie.md` (Zeile 100: „Orte als Möglichkeit folgen in Schritt 2“), `docs/alternativen.md`, `docs/konnektor.md`, `docs/design.md` | Doku |
| `beispiel/reisen/beispielreise` (Wanderung, Orte mit Art `stadt`/`ort_am_weg`, Wahlstellen V-01 bis V-03), `beispiel/reisen/stadtwochenende` (zwei Orte, keine Wahlstelle, keine Ortsart) | Testgrundlage |

## Bestehende Muster
- **Schritt 1 als Vorlage** (Commit efb4920, 12 Dateien, ≈ 300 Zeilen): neues Listenfeld an der Option, Prüfung auf Existenz, Art des ersten Dings als Art der Wahlstelle, Merkmale aller beteiligten Arten bei gemischter Wahlstelle (`arten_der_option`), Werte des ersten Dings im Vergleich, das Ding der aktiven Möglichkeit steht am Tag (`wahl:`), im Kalender nur entschieden, auf der Karte „plan“ oder „alternative“.
- **Nacht als Wahlstelle:** `nacht: V-…` liest heute nur `unterkuenfte` der Optionen; der Ort der Nacht kommt aus der Unterkunft, verschiedene Orte geben eine Warnung (`pruefung.routen.110`). `nacht: O-…` (Nacht an einem Ort ohne Unterkunft) gibt es schon.
- **Ort mit Rechenbedeutung (ADR-0008):** Strecken (`von`, `nach`), Nacht und Position am Tag vergleichen O-IDs auf Gleichheit; daraus kommt der Anschluss. Ein Aufenthalt hängt mit `ort:`/`an:` am Ort.
- **Elternbezug:** Eine Wahlstelle hängt über `an:` (Liste) an Tagen, Strecken, Unterkünften, Aufenthalten, Orten.

## Abhängigkeiten
- Grundlage: Art und Merkmale am Ort (`o_art`, `mk_ort`, ADR-0008 Schritt a), Lage über `bezug` und Übersicht nur mit Orten des Plans (Schritt b).
- Was davon abhängt: Vergleich der Seite, Karte (Übersicht, Etappe, Ort), Kalender, Konnektor `choice_create`/`option_create`/`option_update`/`show`, Wächter (offene Wahlstellen), Prüfung der Regeln (`erfordert`/`schliesst_aus`, `im_plan`).

## Bestehende Specs
- Keine Spec zu Optionen; `docs/specs/routen/kennzahlen-268.md` ist nur am Rand berührt.

## Risiken und offene Punkte für die Analyse
- **Was heißt „ein Ort ist gewählt“?** Drei mögliche Bedeutungen: (1) Ziel ohne Rechenbedeutung (Ausflug in A oder B, nur Anzeige am Tag, auf der Karte, im Vergleich); (2) Ort der Nacht (`nacht: V-…` mit `orte:`, „Übernachten in A oder B“, solange noch keine Unterkunft feststeht), dann bestimmt die Wahl `end_ort` und damit den Anschluss; (3) Station einer Strecke (das geht schon über Strecken als Möglichkeit). Die Bedeutung entscheidet, ob Anschluss und Tag-Lauf betroffen sind.
- Ein Tag kennt heute kein Feld für Orte, die man besucht (nur Strecke, Nacht, Aufenthalte). Ein neues Tagesfeld wäre eine Änderung im Datenformat.
- Die Karte zeigt in der Übersicht nur Orte des Plans; ein Ort, der nur Möglichkeit ist, braucht eine Regel („alternative“ wie bei Aufenthalten).
- `option_inhalt_ok`: Darf ein Ort zusammen mit anderen Sorten stehen (Ort mit Aufenthalten darin)?
- Ein Ort ohne Art hat keine Merkmale; dann bleibt der Vergleich leer bis auf Text, Plus und Minus.
- Abnahme an beiden Beispielreisen und an der Reise ohne Pläne (Stadtwochenende hat keine Wahlstelle), Tests der Instanz (13 bekannte Fehler in main laut Kommentar von 6.11.2026, nicht von #353).

## Analysis

### Type
Feature (Schritt 2 von #353: Orte `O-…` als Möglichkeiten einer Wahlstelle, nach Schritt 1 mit Aufenthalten, Commit efb4920).

### Entscheidungen des Tech Leads (begründet, keine offene Frage an den PO)
1. **Ein gewählter Ort ist ein Ziel ohne Rechenbedeutung** (Variante a). Die Beispiele des Product Owners (Schlechtwetter-, Gipfelalternative) sind Ziele, keine Nachtorte; „Übernachten in A oder B“ ist laut Issue schon die Unterkunft am Ort. Anschluss, `start_ort`/`end_ort`, `tag_lauf` und `nacht()` bleiben unberührt.
   - **Vertagt (nicht entschieden):** Ort der Nacht aus `orte:` bei `nacht: V-…` (Variante b). Vermerk in `docs/alternativen.md`.
   - `nacht: V-…`, deren Optionen nur `orte` (keine Unterkunft) haben, gibt eine **Prüfwarnung** („Ort der Nacht kommt nur aus Unterkünften“, neuer Schlüssel in `texte_*`), statt still `ort=None` zu rechnen. Ein Test hält fest, dass der Nachtort unverändert bleibt.
2. **Sorten an einer Option** (`option_inhalt_ok`): `orte` allein, mit `aufenthalte` (Ort mit Rast/Museum dort), mit `strecken` oder mit beidem. `unterkuenfte` und `folge` stehen weiter allein. Umsetzung als Teilmengenprüfung gegen `{strecken, aufenthalte, orte}`.
3. **Ort ohne Art ist erlaubt** (ADR-0008: Art freiwillig; O-06 der Wanderung, beide Orte des Stadtwochenendes haben keine). Der Vergleich zeigt dann nur Text, Plus, Minus; keine Warnung.
4. **Wahlstelle mischt Arten** wie in Schritt 1: Der Vergleich zeigt die Merkmale aller beteiligten Arten (`arten_der_option` mit `o_art`), die Art der Wahlstelle ohne `art:` kommt aus dem ersten Ding, beim Ort nur wenn er eine Art hat.
5. **Am Tag:** Ein Ort als Möglichkeit kommt über `wahl: [V-…]` am Tag oder `an:` der Wahlstelle an den Tag, wie Aufenthalte. Die Tagesansicht zeigt den Wahlstellen-Block des Tags schon (`vorlage.html` ≈ 3120), darin die Ortszeile. **Kein neues Tagesfeld** und keine eigene Tageszeile für Orte; die Ortszeile in der Option verlinkt auf die Ortsseite (Heimat, ADR-0003).
6. **Karte:** Ein Ort, der Möglichkeit ist, zählt als „im Plan verwendet“ (ADR-0008 Punkt 5) und bekommt auf der Übersicht einen Punkt; `dinge_bezug` führt Orte der Optionen mit Stand `plan`/`alternative`, `orte_im_plan` nimmt sie mit Stand ≠ `frei` auf (Vorbild: Orte alternativer Aufenthalte zählen dort schon). **Bewusste Grenze:** Der Punkt sieht aus wie ein normaler Planort, ohne Kennzeichnung „Alternative“; eine eigene Darstellung ist nicht Teil dieses Schritts.
7. **Kalender:** kein Eintrag für Orte (Kalender kennt keine Orte als Eintrag, ein Ort hat keine Zeit).
8. **`regeln_im_plan`:** nicht erweitert, wie in Schritt 1 (dort sind Aufenthalte der Möglichkeiten auch nicht in `im_plan`). Grenze: `an: O-…` einer anderen Wahlstelle wird durch einen Ort, der nur in einer Möglichkeit steht, nicht erreicht.
9. **Datenformat:** `orte:` an der Option kommt nur dazu, keine Umstellung in `neu.py nachziehen` nötig (nachziehen fasst Optionen nicht an). `neu.py arten_ableiten` bekommt einen Zweig für `orte` (Art aus `o_art`, wenn gesetzt).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/routen.py` | MODIFY | Optionsprüfung (≈ 700) gegen `self.orte` mit neuem Prüfschlüssel `option_ort`; `art_der_wahl` (≈ 1202) mit `o_art`; `arten_der_option` (≈ 1213); `merkmale_pruefen` `o_extra`/`mk_ort` (≈ 1296–1338); `merkmale_aus` (≈ 1399) `orte[:1]` → `mk_ort`; Ausgabe der Option (≈ 1892) `"orte"`; Warnung bei `nacht: V-…` nur mit Orten (≈ 1524–1541) |
| `engine/schreiben.py` | MODIFY | `PLAIN_FELDER` (≈ 1108), `option_bauen` (≈ 2298, `id_liste(…"orte", r"O-\d+")`), `option_inhalt_ok` (≈ 3571, Teilmengenregel), `option_aendern` (≈ 3626) |
| `engine/konnektor.py` | MODIFY | `OPTION_FELDER` (≈ 2561) Feld `orte` (Liste von O-IDs) |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | `konnektor.feld.option_felder.orte`; `schreiben.option_bauen.2`, `option_aendern.5` (Sorten nennen); `option_aendern.8` (fehlt schon `aufenthalte`); `pruefung.routen.option_ort`; Warnung Nachtort nur aus Unterkünften |
| `engine/karte.py` | MODIFY | `dinge_bezug` (≈ 125–173) Orte der Optionen in beiden Schleifen; `orte_im_plan` (≈ 187–195) Orte mit Stand ≠ `frei` |
| `engine/vorlage.html` | MODIFY | `optionBlock` (≈ 2276) und `optionEinzelheiten` (≈ 2320): Zeile je Ort mit Link zur Ortsseite (vorhandene Ortszeile nutzen) |
| `engine/neu.py` | MODIFY | `arten_ableiten` (≈ 314–370) Zweig für `orte` |
| `engine/tests/test_option_orte.py` | CREATE | nach Muster `test_option_aufenthalte.py`: Ort mit Art, Ort ohne Art, unbekannter Ort, Sorten-Regel, Schreibweg (`option_create`/`option_update`), gemischter Vergleich, Karte (Punkt auf Übersicht), Nacht unverändert + Warnung, Kalender ohne Eintrag |
| `engine/tests/seiten_option_ort.mjs` | CREATE | Seitentest: Ortsname mit Link in der Option, Vergleich |
| `beispiel/reisen/beispielreise/plan/routen.yaml` | MODIFY | neue erfundene Wahlstelle an einem Tag über `wahl:` mit zwei Orten (einer mit Art, O-06 ohne Art), als Beispielwert markiert; V-01 eignet sich nicht (hängt an `folge`) |
| `docs/ontologie.md` (Z. 100), `docs/alternativen.md` (Z. 21, 121, Vertagung b), `docs/konnektor.md` (Z. 39), `docs/design.md` | MODIFY | Doku |

### Scope Assessment
- Files: ≈ 13
- Estimated LoC: +300/−20 (davon rund die Hälfte Tests)
- Risk Level: MEDIUM — viele Stellen, aber nur ein neues optionales Feld nach erprobtem Muster; Bestand ohne `orte:` bleibt gleich.

### Risiken
- **Bestehende Tests zur Karte:** Ein neuer Ort im Plan der Beispielreise kann die frischen #335-Tests („Übersicht nur mit Orten des Plans“), Zählungen und Seitenprüfungen ändern (`test_karte_*`, `test_art_uebersicht.py`, `seiten_karte.mjs`, `seiten_art_uebersicht.mjs`, `test_tagesplan.py`, `test_tagesseite.py`). Vor dem Ändern der Beispielreise prüfen; Orte der neuen Wahlstelle so wählen, dass sie keine bisherige Annahme brechen (z. B. Orte, die ohnehin schon im Plan sind, plus O-06).
- **Tests der Instanz sind Pflicht** vor dem Vorspulen: Der PR ändert Meldungstexte (`option_bauen.2`, `option_aendern.5/.8`) und das Konnektor-Schema. Vergleichsbasis: 13 bekannte Fehler in main (ADR-0008, nicht von #353).
- Latente Mehrdeutigkeit in `nacht()` (`next(iter(orte))` bei mehreren Unterkunftsorten) bleibt, wird durch (a) nicht schlimmer.

### Messung an ADR-0001 (zehn Fragen)
1. Ontologie: betrifft die Grundform Wahl und Ding (Ort); durchgespielt an Wanderung (neue Wahlstelle) und Stadtwochenende (ohne Wahlstelle, bleibt unverändert, Orte ohne Art) — besteht.
2. Kein Katalog: keine Art, kein Merkmal in der Software; Merkmale kommen aus der Art des Orts der Reise — besteht.
3. Keine KI: reine Prüfregeln (Existenz, Sorten) — besteht.
4. Tür: Feld `orte` in `choice_create`/`option_create`/`option_update`, Ausgabe in `show`, Doku `docs/konnektor.md` — besteht.
5. Herkunft: Merkmalwerte am Ort/an der Option mit bestehender Herkunftspflicht — besteht.
6. Rollen: Entscheidung über `decide` wie bisher — besteht.
7. IDs/Verlauf: keine neuen ID-Sorten, nichts überschrieben — besteht.
8. PWA: Option zeigt Ortszeile, Vergleich, Karte; offline wie bisher; Browser-Rundgang in der Abnahme — besteht (zu prüfen).
9. Claude Code: keine Reiseinhalte, nur erfundene Beispieldaten — besteht.
10. Doku: `docs/ontologie.md`, `docs/alternativen.md`, `docs/konnektor.md`, `docs/design.md`.

### Technical Approach
Ein PR nach dem Muster von efb4920, Reihenfolge: (1) Tests RED, (2) Konnektor- und Schreibfelder mit Sortenregel und Texten, (3) Lesen/Prüfen und Ausgabe in `routen.py`, (4) Art und Merkmale, (5) Warnung bei Nacht nur mit Orten, (6) Karte, (7) Seite, (8) Beispielreise, (9) Doku. Abnahme über den Konnektor an einer frischen Testreise und an beiden Reisetypen.

### Dependencies
- Grundlage: `o_art`, `mk_ort` (ADR-0008 Schritt a), `bezug` und Übersicht nur mit Orten des Plans (Schritt b), Schritt 1 (`aufenthalte`, gemischte Arten).
- Abhängig: Vergleich und Option auf der Seite, Karte, Konnektor `choice_create`/`option_create`/`option_update`/`show`, Tests der Instanz.

### Open Questions
- keine an den Product Owner (Bedeutung „Ort gewählt“ als Tech-Lead-Entscheidung oben, Nachtort vertagt).
