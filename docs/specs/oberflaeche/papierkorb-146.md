---
entity_id: papierkorb-146
type: module
created: 2026-10-30
updated: 2026-10-30
status: draft
version: "1.0"
tags: [vorlage, buchung, stornieren, papierkorb, loeschen]
---

# Stornierte Buchungen eingeklappt am Ding (Papierkorb-Wirkung, #146)

Workflow: `papierkorb-146`. Analyse: `docs/context/papierkorb-146.md`, Abschnitt „Analysis“ (Variante V3).

## Approval

- [ ] Approved

## Purpose

Der Product Owner will, dass Nutzer Dinge „löschen“ können, also aus der normalen Ansicht verschwinden lassen. Ein Papierkorb ist ausdrücklich in Ordnung, die Technik ist ihm egal (Kommentar in #146). Auslöser: stornierte Testbuchungen stehen als durchgestrichene Karten mitten im Tag.

Nach dieser Spec gilt in einfachen Worten:

- Eine stornierte Buchung verschwindet aus der normalen Ansicht. An ihrem Ding (Unterkunft, Aufenthalt, Strecke, Tageskasten) steht statt der Karte nur noch eine schmale, zugeklappte Zeile „Storniert (1)“. Ein Klick darauf zeigt die Buchung wie zuvor, mit Grund und Verlauf.
- Nichts wird gelöscht. Die Kennung (B-…) und der Verlauf bleiben, Links auf die Buchung funktionieren weiter.
- Verworfene Optionen einer Wahlstelle sind schon eingeklappt („Verworfen (n)“). Die Zahl „Alle Möglichkeiten (n)“ soll sie nicht mehr mitzählen.

### Bewusste Abweichung vom Ticket

Der Tech-Lead-Kommentar in #146 nennt (1) eine Sammelstelle „Papierkorb“ und (2) einen Zurückholen-Knopf dort. Beides wird hier nicht gebaut:

1. Eine Sammelstelle sammelt Dinge aus mehreren Heimaten. ADR-0003, Regel 2, erlaubt das nur mit eigener Aufgabe (entscheiden, buchen) und nur als Zeilen. „Aufräumen“ ist keine solche Aufgabe. Die Regel zu ändern, kann nur der Product Owner.
2. Ein Knopf auf der Seite bräuchte einen Schreibweg Seite → Repo mit Rollenprüfung. Den gibt es nicht: Der Rückmeldedienst schreibt nur in die Ablage; ins Repo schreibt allein der Schreibweg, und nur für den Konnektor (Geheimnis `X-Frieda-Dienst`).

Beides steht im Folge-Issue **#149**. Zurückholen geht bis dahin im Gespräch mit Frieda (Wege aus #145: Buchung mit `buchung_aendern` auf Status gebucht). Die zugeklappte Zeile sagt das.

## Source

- **File:** `engine/vorlage.html`
- **Identifier:** `buchungenZu`, `buchungenBei`, `buchungBlock`, `streckeZeile`, `aufenthaltZeile`, `tagKarte`, `unterkunftKarte`, `ansichtTag` (Zeile „Alle Möglichkeiten“), `ansichtBausteine`, neu: `stornierteBei`, `stornierteBuchungen`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `R.buchungen` | Daten | Buchungen mit `status` (angefragt, gebucht, storniert); der Generator reicht sie durch |
| `buchungsStand` / `buchungChip` | Bausteine | zeigen schon nur die geltende Buchung (`routen.py`: `buchung_je_ding` ohne stornierte); bleiben unverändert |
| `gueltigeOptionen`, `weg()` | Funktionen | vorhanden; `gueltigeOptionen` liefert Optionen ohne verworfen/ersetzt |
| `zumZiel()` | Funktion | öffnet vor dem Scrollen alle übergeordneten `details`; trägt den Link `#B-…` in den Block (keine Änderung) |
| `heimat()` | Funktion | Heimat einer Buchung bleibt ihr erstes Ding (ADR-0003); keine Änderung |
| `engine/tests/test_design.py` | Test | Vier-Stellen-Prüfung (ADR-0002) |
| `docs/design.md` | Doku | Bausteintabelle, Seitenordnung |

## Scope

- **Affected Files:** siehe Tabelle „Betroffene Dateien“.
- **Estimated Changes:** ca. +90/-10 LoC (Vorlage ca. +35, Beispielreise +15, Tests +30, Doku +10).
- **Nicht im Umfang:**
  - Aufgaben mit Status `entfaellt` (stehen schon eingeklappt in „Erledigt oder entfallen“) und Fragen mit Status `entfaellt` (stehen unter „Geklärt“; ein Wiedereröffnen gibt es laut #145 nicht).
  - Sammelstelle „Papierkorb“ und Zurückholen-Knopf (Folge-Issue #149).
  - Echtes Löschen (IDs und Verlauf bleiben, ADR-0001 Frage 7; bleibt zurückgestellt).
  - Texte des Konnektors: Sie sind neutral („Buchung storniert …“, `konnektor.py` um :2475 und :2771) und bleiben unverändert.
  - Änderungen am Schreibweg, am Rückmeldedienst, am Service Worker, an Rollen oder Daten.

## Implementation Details

### Verhalten

**V1 Buchungen.** An den vier Stellen, an denen `buchungenBei(id)` Buchungen voll zeichnet (`streckeZeile` :1196, `aufenthaltZeile` :1228, `tagKarte` :1290, `unterkunftKarte` :1333), stehen nur geltende Buchungen (angefragt, gebucht) voll da. Alle stornierten Buchungen dieses Dings stehen zusammen in **einem** zugeklappten Block (`details.weg`, wie „Verworfen (n)“ an der Wahlstelle) am selben Ort, direkt nach den geltenden Buchungen. Die Reihenfolge im Block entspricht der Reihenfolge der Buchungen in der Reise. Im Block ist jede Buchung vollständig und unverändert gezeichnet (`buchungBlock`: durchgestrichener Chip „storniert“, Grund und Verlauf im Verlauf).

**V2 Wortlaut des Blocks.**

- Zusammenfassung (summary): `Storniert (n)` mit n = Zahl der stornierten Buchungen an diesem Ding.
- Im aufgeklappten Block steht oben eine leise Hinweiszeile (kleine Schrift, Klasse wie `z klein`): `Zurückholen: im Gespräch mit Frieda.`
- Keine Kennungen im Hinweistext. Gibt es keine stornierte Buchung, gibt es keinen Block und keinen Hinweis.

**V3 Links.** `#B-…` auf eine stornierte Buchung bleibt gültig: `heimat()` führt zum ersten Ding, `zumZiel()` öffnet den Block (alle übergeordneten `details`), dann steht die Buchung sichtbar da. Der Test prüft das ausdrücklich.

**V4 Optionen.** Verworfene und ersetzte Optionen stehen schon eingeklappt (`details.weg` „Verworfen (n)“ in `wahlKarte`). Einzige Korrektur: Die Zusammenfassung „Alle Möglichkeiten (n)“ in `ansichtTag` (:2970) zählt nur gültige Optionen (`gueltigeOptionen(w).length`), und die Zeile erscheint nur bei mehr als einer gültigen Option. Die Karte darunter (`wahlKarte(w)`) bleibt unverändert und zeigt die verworfenen weiter im Block „Verworfen“.

**V5 Chips und Zähler.** `buchungChip` und `buchungsStand` zeigen schon nur die geltende Buchung. Es wird geprüft (Test), dass nirgends auf der Seite eine stornierte Buchung als „gebucht“ gezählt wird (Chip der Unterkunft, Zeitachse, „Zu buchen“, Zähler). Findet der Test eine Stelle, wird sie in diesem Vorhaben behoben.

**V6 Offline und Rollen.** Der Block entsteht aus den gebauten Daten, also offline wie bisher. Es gibt keine Aktion und keine Rollenprüfung.

### Baustein-Entscheidung (ADR-0002)

Der Block hat eine eigene Funktion und wird deshalb als **Molekül „Stornierte Buchungen“** (`stornierteBuchungen`) eingetragen, nicht als bloße Variante von `details.weg`. Begründung: Er hat einen festen Wortlaut, einen festen Hinweis, wird an vier Stellen gebraucht und soll auf der Bausteinseite mit einer Muster-Buchung zu sehen sein.

Die vier Stellen, wie `engine/tests/test_design.py` sie prüft:

1. **Kopfkommentar der Vorlage** („Bausteine nach Ebenen“): `stornierteBuchungen` in die Zeile „Moleküle:“. `test_jeder_baustein_ist_eine_funktion_der_vorlage` verlangt dafür eine Funktion `function stornierteBuchungen(` oder `const stornierteBuchungen = ` am Zeilenanfang im Skript.
2. **Stile seiner Ebene** im `<style>`: Der Block nutzt `details.weg` (vorhanden); die Hinweiszeile nutzt eine vorhandene Klasse. Neue Stile nur, wenn der Hinweis sonst nicht passt, dann in der Moleküle-Gruppe und mit Tokens (`test_radien_und_schatten_aus_tokens`, Schriftleiter: nur die fünf Stufen).
3. **Bausteinseite** (`ansichtBausteine`): Der Aufruf `stornierteBuchungen(` steht in `ansichtBausteine` (`test_bausteinseite_zeichnet_jeden_baustein`) und zeigt den Block mit der Muster-Buchung. Gibt es keine stornierte Buchung in der Reise, nimmt die Seite eine Muster-Buchung nach dem Vorbild der vorhandenen (`id: "B-00"`, Muster). Knöpfe und Formulare darin werden wie bei `buBlock` abgeschaltet. Die Ansicht-Beschreibung nennt das Molekül.
4. **`docs/design.md`**: Der Name steht in der Zeile „Moleküle“ der Bausteintabelle (`test_jeder_baustein_steht_in_design_md_und_umgekehrt`, auf derselben Ebene), mit kurzer Erklärung („stornierte Buchungen eines Dings, zugeklappt, mit Hinweis zum Zurückholen“). Außerdem in der Beschreibung der Organismen `buchungBlock` ein Halbsatz: „stornierte nur im Block `stornierteBuchungen`“, und in der Seitenordnung ein Satz zur Buchung.

`GRUNDFORMEN` ändert sich nicht: Der Block zeigt die Grundform Buchung, die schon eingetragen ist (`buchung`: Zeile `buchungChip`, Vorschau `listenZeile`, Seite `buchungBlock`). Dort wird `stornierteBuchungen` nicht ergänzt, denn die Heimat der Buchung bleibt `buchungBlock` (ADR-0003); `test_grundformen_nennen_nur_bausteine_der_liste` bleibt grün.

### Ein gemeinsamer Helfer

Statt vier Kopien gibt es genau einen Weg:

- `buchungenBei(id)` liefert nur noch die geltenden Buchungen, deren erstes Ding `id` ist (Heimat, ADR-0003).
- `stornierteBei(id)` liefert die stornierten Buchungen, deren erstes Ding `id` ist.
- `stornierteBuchungen(bs)` zeichnet aus einer Liste stornierter Buchungen den Block und gibt eine Liste zurück: leer bei keiner Buchung, sonst mit einem `details`. So lässt er sich an jeder Stelle mit `k.append(...stornierteBuchungen(stornierteBei(id)))` anhängen, ohne Fallunterscheidung.

Die vier Aufrufstellen ändern sich nur um diesen einen Aufruf. Die Sortierung in `buchungenZu` (stornierte nach hinten) entfällt, weil getrennt wird.

### Beispielreise

Die Beispielreise bekommt eine stornierte Buchung **B-03 am Ding U-01** („Hotel am Elbufer“). Geprüft in `beispiel/reisen/beispielreise/plan/routen.yaml`: B-03 ist frei (vorhanden sind B-01 für U-01 und B-02 für E-20); U-01 hat mit B-01 schon eine geltende Buchung, B-03 zeigt also genau den Fall „geltende Buchung voll, stornierte im Block“. Heimat von B-03 ist U-01 (`fuer: [U-01]`). Die Reise hat keine `ids.yaml`; die nächste vergebene Nummer ergibt sich aus der höchsten vorhandenen (`neu.naechste_id`), also wird sie B-04 (siehe Risiken, `test_schreiben.py`).

```yaml
  B-03:
    fuer: [U-01]
    status: storniert
    nummer: "HE-2027-0388"
    bei: "direkt beim Hotel (Mail)"
    preis: "95 € für eine Nacht (Beispielwert)"
    storno: "kostenlos bis 3 Tage vorher"
    gebucht_am: 2026-10-27
    wer: Ida
    quelle: "erfundene Beispielbuchung (Beispielwert), Mail vom 27.10.2026"
    verlauf:
      - {datum: 2026-10-27, wer: Ida, was: angelegt}
      - {datum: 2026-10-29, wer: Ida, was: Status, grund: "Zimmer doppelt gebucht, die Buchung HE-2027-0415 gilt"}
```

Alle Werte sind erfunden und als Beispielwert markiert; Personen sind nur Ida und Karl. Die Form (Felder, Verlauf mit `datum`, `wer`, `was`, optional `grund`) folgt B-01 und B-02 und `BUCHUNG_FELDER`.

## Expected Behavior

- **Input:** Eine Reise hat an einem Ding mindestens eine stornierte Buchung.
- **Output:** Die Seite zeigt an diesem Ding nur die geltenden Buchungen voll, die stornierten in einem zugeklappten Block „Storniert (n)“ mit Hinweis „Zurückholen: im Gespräch mit Frieda.“
- **Side effects:** Keine. Daten, IDs, Verläufe, Konnektor, Schreibweg und Rückmeldedienst bleiben unberührt.

## Acceptance Criteria

Alle Prüfungen laufen gegen die Beispielreise mit B-03 (storniert, U-01) und B-01 (gebucht, U-01).

- **AC-1:** Given U-01 hat B-01 (gebucht) und B-03 (storniert). When die Seite U-01 zeigt (Unterkunftskarte im Abschnitt „Nacht“ der Tagesseite und, bei einer Reise ohne Tagesseiten, im Tageskasten des Plans), Then ist B-01 als volle Karte sichtbar, B-03 steht nicht voll im Tag, an der Unterkunft oder im Tageskasten.
- **AC-2:** Given dieselbe Ansicht. When die Seite geladen ist, Then gibt es genau einen Block `details.weg` mit der Zusammenfassung „Storniert (1)“, er ist zugeklappt, und die Karte von B-03 ist darin enthalten, aber nicht sichtbar.
- **AC-3:** Given ein Ding ohne stornierte Buchung (z. B. E-20 mit B-02). When die Seite es zeigt, Then gibt es dort keinen Block „Storniert“ und keinen Hinweis zum Zurückholen.
- **AC-4:** Given der Block ist aufgeklappt. When man ihn liest, Then steht dort die Hinweiszeile „Zurückholen: im Gespräch mit Frieda.“ und B-03 mit durchgestrichenem Chip „storniert“, Nummer, Grund im Verlauf („Zimmer doppelt gebucht …“) und Verlauf (2 Einträge).
- **AC-5:** Given `location.hash = "B-03"`. When die Route angesteuert wird, Then ist B-03 sichtbar, der Block „Storniert (1)“ ist offen, und B-03 steht bei seinem Ding (U-01). Das gilt mit und ohne Tagesseiten (`darstellung.tiefe`).
- **AC-6:** Given eine Strecke, ein Aufenthalt ohne Nacht oder ein Tageskasten mit einer stornierten Buchung . When die Seite sie zeigt, Then gilt dasselbe wie in AC-1 bis AC-3, denn alle vier Aufrufstellen nutzen denselben Helfer. Prüfweg: ein Quelltext-Test in `test_seite.py` liest `engine/vorlage.html` und prüft, dass `streckeZeile`, `aufenthaltZeile`, `tagKarte` und `unterkunftKarte` je `stornierteBuchungen(stornierteBei(…))` aufrufen und keine von ihnen stornierte Buchungen über `buchungBlock` voll zeichnet.
- **AC-7:** Given V-03 mit einer verworfenen Option (V-03.b). When die Seite die Zeile „Alle Möglichkeiten“ zeigt, Then steht dort die Zahl der gültigen Optionen (nicht verworfen, nicht ersetzt), und die verworfene steht weiter im Block „Verworfen (n)“ der Karte. Hat die Wahlstelle nur eine gültige Option, erscheint die Zeile nicht.
- **AC-8:** Given B-03 ist storniert. When die Seite Stände zählt (Chip der Unterkunft, Zeitachse, „Zu buchen“, Zähler), Then wird B-03 nirgends als „gebucht“ gezählt; U-01 zeigt „gebucht“ aus B-01.
- **AC-9:** Given der Konnektor `ueberblick` auf der Beispielreise. When er die Buchungen zählt, Then lautet die Zeile „## Buchungen: 2 gebucht, 1 storniert (zeige B-…)“; `zeige U-01` nennt weiter „Buchung: gebucht (B-01, zeige B-01)“.
- **AC-10:** Given die Bausteinseite `#bausteine`. When sie geladen ist, Then zeigt sie das Molekül „Stornierte Buchungen“ mit einer Buchung, und `test_design.py` ist grün (vier Stellen).
- **AC-11:** Given ein Rundgang durch alle Routen und Kennungen der Beispielreise (`seiten_browser.mjs`). When `#B-03` besucht wird, Then ist die Seite nicht leer, ohne waagerechtes Scrollen bei 390 px und mit erlaubten Schriftgrößen; die Kennung gehört der Grundform Buchung an (kein Eintrag in `ohneArt`).
- **AC-12:** Given der Gesamtlauf. When `engine/.venv/bin/python -m pytest -q engine/tests` ohne echte Reisen läuft, Then ist alles grün; die neuen Prüfungen sind ohne die Änderung rot (TDD RED).
- **AC-13:** Es wird nichts gelöscht: Die YAML-Daten, der Verlauf und die Kennung B-03 sind nach dem Bauen vollständig in `R.buchungen` enthalten (Test liest B-03 mit Status und beiden Verlaufseinträgen aus den gebauten Daten).

## Test Plan

Die Zeilenangaben der Analyse wurden am Code geprüft; sie stimmen (Vorlage :1075/:1078 für `buchungenZu`/`buchungenBei`, :1196, :1228, :1290, :1333 für die Aufrufe, :1362 `buchungBlock`, :2970 „Alle Möglichkeiten“, :1540 `gueltigeOptionen`, :3422 Bausteinseite). Abweichung: Die Zählzeile im Konnektor steht in `engine/konnektor.py` um :712, der Test dazu in `engine/tests/test_konnektor.py` um :877.

| Datei | Änderung |
|---|---|
| `engine/tests/test_seite.py` | Neuer Browser-Test (chromium und webkit, wie `test_buchung_hat_eine_heimat_auch_ohne_tagesseiten`) über `seite_der_variante`: AC-1 bis AC-5 und AC-7, AC-13, mit Tagesseiten; dazu der Quelltext-Test für AC-6 und mit `darstellung={"tiefe": True}` |
| `engine/tests/seiten_variante.mjs` | Erweiterung neben dem Block für `#B-01` (:27ff): `#B-03` ansteuern; ausgeben, ob B-03 sichtbar ist, ob der Block offen ist, die Zusammenfassung, ob B-01 voll sichtbar ist und ob außerhalb des Blocks keine Karte von B-03 steht; Text der Zeile „Alle Möglichkeiten“ von V-03 |
| `engine/tests/seiten_browser.mjs` | keine Änderung nötig: Der Rundgang besucht jede Buchung aus `R.buchungen` (:24-31) und prüft die Grundform (:61-68); `#B-03` kommt mit der Beispielreise von selbst hinein (AC-11) |
| `engine/tests/test_konnektor.py` | Zeile um :877: Erwartung „## Buchungen: 2 gebucht, 1 storniert (zeige B-…)“ (AC-9); `zeige U-01` bleibt |
| `engine/tests/test_design.py` | keine Änderung am Test; er prüft die neue Eintragung automatisch (AC-10). Optional: Die Liste der Teile für die Bausteinseite in `test_seite.py` (:79) um „Molekül · Stornierte Buchungen“ ergänzen |
| `engine/tests/test_schreiben.py` | Folgeänderung durch die Beispielreise: Der Test legt eine Buchung an und erwartet bisher „B-03“ (:955-990, `ids["B"] == 3`). Mit B-03 in der Reise wird die neue ID B-04. Alle B-03 in diesem Test werden B-04, die Marke `ids["B"] == 4` |
| `engine/tests/test_konnektor.py` (Mock) | B-03 in den Tests um :845 und :943-967 ist ein Mock des Schreibwegs (kein Zugriff auf die Beispielreise); bleibt unverändert |
| `engine/tests/test_rueckmeldungen.py` | B-05/B-06 sind dort nicht vorhandene Buchungen; bleibt unverändert, ist nach Änderung weiter nicht vorhanden |
| `engine/tests/test_routen.py` | eigene Testdaten (:900-937); unberührt |

Zusätzlich beim Umsetzen: `kalender.py` überspringt stornierte Buchungen (:155-157), bleibt unkritisch; ein Lauf der gesamten Tests zeigt, ob weitere Stellen die Buchungsliste der Beispielreise zählen.

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** ADR-0001 (Kern), ADR-0002 (Atomic Design: neues Molekül an den vier Stellen), ADR-0003 (Heimat: bleibt am Ding, Regel 2 wird nicht verletzt). Keine neue ADR nötig.

### Prüfstelle (ADR-0001)

| Nr. | Antwort |
|---|---|
| 1 | Ontologie: betrifft die Grundform Buchung allgemein, nichts Reisespezifisches. Mit Hüttentour (Beispielreise) und Städtereise (Hotel, Tag 1) gedacht: gleiche Wirkung. |
| 2 | Kein Katalog: keine Art und kein Merkmal wird eingeführt. Der Block hängt nur am Status `storniert`, einem Wert der Grundform Buchung. |
| 3 | Keine KI in Frieda: reine Anzeige aus vorhandenen Daten. |
| 4 | Die Tür: Der Konnektor liest und schreibt Buchungen unverändert (`zeige`, `ueberblick`, `buchung_aendern`). Nichts Neues zu lesen, daher nur die Anpassung des Tests der Zählung. `docs/konnektor.md` bleibt gleich. |
| 5 | Herkunft: keine neue Aussage; die Beispielbuchung trägt `quelle`. |
| 6 | Rollen: Keine Entscheidung wird ohne Person und Datum möglich; die Seite entscheidet nichts. |
| 7 | IDs und Verlauf: nichts wird neu vergeben, gelöscht oder überschrieben. |
| 8 | PWA: Anzeige aus den gebauten Daten, funktioniert offline; Browser-Rundgang grün (AC-11). |
| 9 | Claude Code: Reiseinhalte entstehen weiter nicht dort. |
| 10 | Dokumentation: `docs/design.md` (Bausteine, Seitenordnung), diese Spec. |

## Betroffene Dateien

| Datei | Änderungsart | Beschreibung |
|---|---|---|
| `engine/vorlage.html` | MODIFY | `buchungenBei` nur geltende, neue `stornierteBei`, neues Molekül `stornierteBuchungen`, Aufruf an den 4 Stellen, Zähler „Alle Möglichkeiten“, Kopfkommentar, Stile (falls nötig), Muster auf der Bausteinseite |
| `beispiel/reisen/beispielreise/plan/routen.yaml` | MODIFY | neue stornierte Buchung B-03 an U-01 (Beispielwert) |
| `docs/design.md` | MODIFY | Molekül `stornierteBuchungen` in der Bausteintabelle, Halbsatz bei `buchungBlock`, Seitenordnung |
| `engine/tests/test_seite.py` | MODIFY | neuer Browser-Test; ggf. Teil „Molekül · Stornierte Buchungen“ |
| `engine/tests/seiten_variante.mjs` | MODIFY | Sonde für `#B-03` und „Alle Möglichkeiten“ |
| `engine/tests/test_konnektor.py` | MODIFY | Zählzeile „2 gebucht, 1 storniert“ |
| `engine/tests/test_schreiben.py` | MODIFY | neue ID nach dem Anlegen B-04 statt B-03, Marke 4 |
| `engine/tests/test_design.py` | unverändert | prüft die Eintragung automatisch |
| `engine/tests/seiten_browser.mjs` | unverändert | besucht `#B-03` automatisch |

## Risiken

1. **Beispielreise verändert Zählungen:** Neue Buchung ändert `ueberblick` und die nächste ID im Schreibtest (siehe Tests). Gemildert: beide Stellen sind benannt und werden im selben Schritt angepasst; der Gesamtlauf deckt weitere auf.
2. **Link ins Leere:** Falls `zumZiel()` den Block nicht öffnet, wäre B-03 unsichtbar. AC-5 prüft das im Browser (chromium und webkit).
3. **Zählung stornierter als gebucht:** V5/AC-8 prüfen alle Zähler; Chips sind laut Analyse schon richtig.
4. **ADR-Regeln:** Neuer Baustein ohne alle vier Stellen bricht `test_design.py`; deshalb sind die Stellen einzeln aufgeführt.
5. **Schriftleiter und Radien:** Der Hinweis nutzt vorhandene Klassen und Tokens, sonst bricht `seiten_browser.mjs` (Schriftstufen) oder `test_radien_und_schatten_aus_tokens`.
6. **Offline:** Keine Änderung; der Block kommt aus den gebauten Daten.
7. **Zurückholen nur im Gespräch:** Wer die Seite allein nutzt, kann nichts zurückholen. Der Hinweis nennt den Weg; ein Knopf ist #149.

## Definition of Done

- [ ] Stornierte Buchungen stehen an allen vier Stellen nur im zugeklappten Block „Storniert (n)“ mit Hinweis
- [ ] Ein gemeinsamer Helfer (`stornierteBuchungen`), keine vier Kopien
- [ ] Molekül an den vier Stellen eingetragen (Kopfkommentar, Stile, Bausteinseite, `docs/design.md`)
- [ ] „Alle Möglichkeiten (n)“ zählt nur gültige Optionen
- [ ] Beispielreise mit B-03 (Beispielwert), `ueberblick`-Zählung und Schreibtest angepasst
- [ ] Neue Tests vorher rot, jetzt grün; `engine/.venv/bin/python -m pytest -q engine/tests` insgesamt grün
- [ ] Folge-Issue #149 verweist auf Sammelstelle und Zurückholen-Knopf

## Known Limitations

- Zurückholen geht nur im Gespräch mit Frieda (Konnektor), nicht auf der Seite; ebenso gibt es keine zentrale Stelle, die alle stornierten Buchungen zeigt (#149).
- Aufgaben und Fragen sind nicht Teil dieser Änderung.

## Offene Punkte

- Keine für den Product Owner. Die Form (Block am Ding statt Sammelstelle und Knopf) zeigt die Freigabe der Spec; die Abweichung vom Ticket ist oben begründet.

## Changelog

- 2026-10-30: Entwurf (Workflow papierkorb-146).
- 2026-10-30: RED-Phase. Erkenntnisse für die Umsetzung: Die Beispielreise hat erst mit festem Plan Tagesseiten (`reise_bauen(fest=True)`, Plan A gewählt); ohne festen Plan und mit `tiefe` zeigt die Planseite B-01/B-03 zweimal, im Tageskasten T-01 und in der Unterkunftskarte U-01 (vorhandenes Verhalten). Der Browser-Test prüft deshalb je Ding (nächstes Element mit `id`): dort genau ein Block „Storniert (1)“. AC-7 läuft auf der Tagesseite T-02 der Variante „fest“. Folgeänderungen durch B-03 auch in `test_schreiben.py` (Aufenthalts- und Reisenden-Test) und im Mock des Belegtests in `test_konnektor.py` (B-04/B-05).
