# Kontext: papierkorb-146

## Wunsch

Der Product Owner will, dass Nutzer Dinge „löschen“ können, also aus der normalen Ansicht verschwinden lassen; ein Papierkorb ist ausdrücklich in Ordnung, die Technik dahinter ist ihm egal (Entscheidung 30.10.2026, Kommentar in #146). Auslöser: stornierte Testbuchungen (TEST-1) stehen als durchgestrichene Karten mitten im Tag. Nichts wird wirklich entfernt: IDs und Verlauf bleiben (ADR-0001, Frage 7).

## Betroffene Dateien

| Datei | Bedeutung |
|---|---|
| `engine/vorlage.html` | Zeichnet alles im Browser. Buchungen: `buchungenZu` sortiert stornierte nur nach hinten (:1074-1078), `buchungBlock` zeigt sie voll mit durchgestrichenem Chip (:1362-1383); Aufrufe in `streckeZeile` (:1196), `aufenthaltZeile` (:1228), `tagKarte` (:1290), `unterkunftKarte` (:1333). Optionen: `weg()` (:1087), `gueltigeOptionen` (:1540), `wahlKarte` hat schon `details.weg` „Verworfen (n)“ (:1812-1817), Chip in `chips()` (:1023), „Alle Möglichkeiten (n)“ zählt verworfene mit (:2970). Aufgaben: `ansichtAufgaben` legt erledigt+entfällt in `details.ag-erledigt` (:4177-4179); `rmFormular` zeigt alle Aufgaben einer Stelle (:3664). Fragen: `frageStand` zählt „entfällt“ zu „zu“ (:2689-2698), `ansichtFragen` zeigt sie unter „Geklärt“ (:2747). Bausteinliste im Kopfkommentar (:946-960), Bausteinseite `ansichtBausteine` (:3336ff), `GRUNDFORMEN` (:3290-3306), Sammelstelle-Vorbild „Zu tun“ `ansichtOffen` (:3187-3218), Router `route()` (:4277ff), `heimat()` (:4199-4233). |
| `engine/bauen.py` | Reicht Daten durch; Fragen aus Markdown-Tabelle mit freiem Status (:1028-1042). |
| `engine/rueckmeldungen.py` | Dienst der Seite: `api/ich` mit Rolle (:843-851), Belege `PATCH api/belege` mit Rollenprüfung (:873-893), Aufgaben `PATCH api/aufgaben` (:930-936, `aufgabe_aendern` :452-486), Wunsch-Brett „Einplanen“ für Organisator:innen (:921-924, nur `brett.json`). |
| `engine/schreiben.py` | Schreibweg ins Repo, nur mit Geheimnis `X-Frieda-Dienst` (:3030,3040), also nur über den Konnektor. `buchung_aendern` (:1923-2012), `entscheiden` (:1408-1491), `frage_schliessen` (:1601-1618, ausdrücklich kein Wiedereröffnen), `option_aendern` (:2221). |
| `engine/konnektor.py` | Ruft den Schreibweg (:1037-1052); Löschwunsch-Texte aus #145. |
| `engine/reise.py` | Rollen und AKTIONEN (z. B. „aufgabe“ ab mitwirkend), `ENTSCHEIDUNGEN` (:114). |
| `engine/sw.vorlage.js` | `api/` nie aus dem Speicher (:7,88): Zurückholen braucht Netz. Sonst unberührt. |
| `docs/adr/0003-heimat.md`, `docs/design.md` (Seitenordnung :107-110) | Heimat-Regel; Sammelansichten nur mit eigener Aufgabe (entscheiden, buchen), nur Zeilen. |
| `engine/tests/test_design.py` (:27-75) | Prüft die vier Stellen eines Bausteins. |
| `engine/tests/seiten_browser.mjs` (:24-31,61-68), `seiten_variante.mjs` (:27-36) | Besuchen jede Route/ID; `#B-01` muss bei seinem Ding sichtbar sein. |
| `engine/tests/test_reiseueberblick.py` (:94) | Erwartet Fragegruppen genau `["Zu klären","Geklärt"]`. |
| `engine/tests/test_konnektor.py` (:989-1035) | Löschwunsch-Texte (#145), u. a. „neue Frage“ statt Wiedereröffnen. |
| `beispiel/reisen/beispielreise/plan/routen.yaml` (:229) | V-03.b verworfen: Testgrundlage. |

## Bestehende Muster

- Einklappen nach Status gibt es schon an drei Stellen: `details.weg` „Verworfen (n)“ an der Wahlstelle, `details.ag-erledigt` „Erledigt oder entfallen“ bei Aufgaben, Fragegruppe „Geklärt“. Ein Papierkorb kann diese Muster vereinheitlichen.
- Sammelansichten bestehen aus Zeilen (`listenZeile`, `gruppenTitel`, `zahlMarke`, `eintragGruppen`), nie aus Dingen in voller Länge (ADR-0003).
- Aktionen auf der Seite: Knopf → `PATCH api/...` an den Rückmeldedienst, der die Rolle selbst prüft (Belege, Aufgaben). Für Repo-Daten (Buchung, Option, Frage) gibt es keinen Weg von der Seite.

## Abhängigkeiten

- Aufwärts: Daten aus `routen.yaml`, `offene-fragen.md`, Aufgaben im Dienst; Rolle aus `api/ich`.
- Abwärts: Router und `heimat()` (Links `#B-…`, `#V-….x`), Bausteinseite, Browser-Tests, Konnektor-Texte aus #145 (verweisen auf Rückholwege).

## Risiken

1. **Kein Schreibweg Seite → Repo** für Buchung, Option und Frage. Ein Zurückholen-Knopf auf der Seite bräuchte einen neuen Weg (Dienst → Schreibweg) mit Rollenprüfung; sonst bleibt Zurückholen im Gespräch über den Konnektor (Wege aus #145) und der Papierkorb zeigt nur, wie es geht.
2. **Fragen ohne Wiedereröffnen:** Regel in `frage_schliessen` und Test aus #145. Zurückholen von Fragen widerspräche dem.
3. **ADR-0003:** Ein ausgeblendetes Ding verliert seine Heimat; der Papierkorb würde Heimat oder zumindest Sammelansicht mit neuer Aufgabe „zurückholen“. ADR-0003 Punkt 2 und `docs/design.md` Seitenordnung müssen angepasst werden (Rückfrage Kern? Der PO hat das Ziel entschieden, nicht die Form).
4. **Links ins Leere:** `#B-…`/`#V-….x` aus Texten, Verlauf und Konnektor müssen auch auf ausgeblendete Dinge führen (in den Papierkorb).
5. **Trennung:** „entfällt“ steckt heute bei Fragen in „Geklärt“ und bei Aufgaben in „Erledigt oder entfallen“; erledigte Aufgaben und geklärte Fragen gehören nicht in den Papierkorb.
6. **Zählungen:** „Alle Möglichkeiten (n)“ und ähnliche Zähler müssen konsistent bleiben.
7. Offline: Zurückholen nur mit Netz; die Anzeige des Papierkorbs selbst funktioniert offline aus den gebauten Daten.

## Bestehende Specs

- `docs/specs/konnektor/loeschwunsch.md` (#145): Löschwunsch im Gespräch, Rückholwege je Grundform.

## Analysis

### Type
Feature (Oberfläche der Reiseseite)

### Entscheidung Tech Lead: Variante V3 „eingeklappt am Ding“
Verglichen wurden drei Varianten:

| | V1 Ausblenden + Sammelstelle | V2 V1 + Zurückholen-Knopf | V3 eingeklappt am Ding |
|---|---|---|---|
| Aufwand | 7–9 Dateien, ca. 170 LoC | 11–13 Dateien, ca. 320 LoC | 4–5 Dateien, ca. 50–70 LoC |
| Risiko | mittel (ADR, Links, Tests) | hoch (neuer Schreibweg Seite → Repo, Sicherheit) | niedrig |
| Kern | ADR-0003 Regel 2 verletzt (Sammelansicht ohne Aufgabe), Änderung nur durch PO | wie V1, dazu ADR-0001 Frage 6 (Grund, Person, Verlauf) und Rollenprüfung | konform, Heimat bleibt am Ding |
| Nutzen | Karten weg, eine Stelle zum Nachsehen | wie V1, Zurückholen per Knopf | Karte weg aus dem Tag, nur eine schmale Zeile „Storniert (1)“ |

**Gewählt: V3.** Der PO hat das Ziel entschieden („aus der normalen Ansicht verschwinden“, Technik egal, Papierkorb nur „in Ordnung“), nicht die Form. V3 erfüllt das Ziel innerhalb des Kerns und folgt dem vorhandenen Muster „Verworfen (n)“ an der Wahlstelle. Damit wird bewusst von den Tech-Lead-Folgerungen (1) Sammelstelle und (2) Zurückholen von dort im Issue-Kommentar abgewichen:
- (1) braucht eine Änderung von ADR-0003 Regel 2 (nur PO),
- (2) braucht einen Schreibweg Seite → Repo, den es nicht gibt (Rückmeldedienst schreibt nur in die Ablage; Repo nur über Konnektor/Schreibweg mit `X-Frieda-Dienst`).
Beides ist als Folge-Issue **#149** festgehalten. Zurückholen geht bis dahin im Gespräch (Wege aus #145; die eingeklappte Zeile nennt das).
(3) IDs/Verlauf bleiben: V3 ändert keine Daten. (4) Echtes Entfernen: weiter zurückgestellt. (5) #145: Konnektor-Texte sind neutral („Buchung storniert, … erst …“, konnektor.py:2771, :2475) und bleiben unverändert.

### Verhalten (für die Spec)
1. **Buchungen:** Überall, wo `buchungenBei(id)` Buchungen voll zeichnet (`streckeZeile` :1196, `aufenthaltZeile` :1228, `tagKarte` :1290, `unterkunftKarte` :1333), stehen nur geltende Buchungen (angefragt, gebucht) voll da. Stornierte stehen zusammen in **einem** zugeklappten Block `details.weg` „Storniert (n)“ am selben Ort. Ein neuer gemeinsamer Helfer zeichnet diesen Block, damit die vier Stellen nicht vier Kopien haben. Im Block steht ein leiser Hinweis zum Zurückholen: „Zurückholen: im Gespräch mit Frieda.“ (Wortlaut in der Spec festlegen; keine Kennungen im Text.)
2. **Links:** `#B-…` auf eine stornierte Buchung funktioniert schon. `zumZiel()` (:4262–4267) öffnet alle übergeordneten `details`, bevor gescrollt wird. Ein Test prüft das trotzdem.
3. **Optionen:** sind bereits eingeklappt („Verworfen (n)“, :1812). Einzige Korrektur: „Alle Möglichkeiten (n)“ (:2970) zählt nur gültige Optionen (`gueltigeOptionen`), nicht verworfene/ersetzte.
4. **Chips/Zähler:** `buchungChip`/`buchungsStand` zeigen schon nur die geltende Buchung (routen.py `buchung_je_ding` ohne stornierte). Prüfen, dass kein Zähler der Seite stornierte als „gebucht“ zählt.
5. **Nicht im Umfang:** entfallene Aufgaben (schon in „Erledigt oder entfallen“) und Fragen (unter „Geklärt“, kein Wiedereröffnen laut #145); Sammelstelle, Zurückholen-Knopf (#149); echtes Löschen.
6. **Baustein:** Der Block „Storniert (n)“ ist eine Variante des vorhandenen Musters `details.weg`, kein neuer Baustein. Falls er als eigene Funktion erscheint, kommt er an die vier Stellen nach ADR-0002 (Kopfkommentar, Stile, Bausteinseite, docs/design.md). In der Spec entscheiden. Empfehlung: als Molekül „Stornierte Buchungen“ eintragen, die Bausteinseite zeigt ihn mit der Muster-Buchung (:3422ff).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/vorlage.html | MODIFY | Helfer für geltende/stornierte Buchungen, Block „Storniert (n)“ an den 4 Aufrufstellen, Zähler :2970, ggf. Kopfkommentar und Bausteinseite |
| beispiel/reisen/beispielreise/plan/routen.yaml | MODIFY | Eine stornierte Buchung (B-03, als Beispielwert markiert) an einem Ding, das schon eine geltende Buchung hat (z. B. U-01), mit Verlauf und Grund |
| engine/tests/test_seite.py | MODIFY | Neuer Test: stornierte Buchung nicht voll im Tag, aber im zugeklappten Block; `#B-03` öffnet ihn und ist sichtbar; „Alle Möglichkeiten (n)“ zählt nur gültige |
| engine/tests/test_konnektor.py | MODIFY | `ueberblick` erwartet dann „2 gebucht, 1 storniert“ (:877); `zeige U-01` bleibt „gebucht (B-01…)“ |
| docs/design.md | MODIFY | Buchung: stornierte eingeklappt am Ding (Seitenordnung/Bausteine) |
| engine/tests/test_design.py | ggf. | nur wenn ein neuer Baustein eingetragen wird |

### Scope Assessment
- Files: 5–6
- Estimated LoC: +70 / -10
- Risk Level: LOW (nur Anzeige; keine Daten, kein Schreibweg)

### Dependencies
- Daten: `R.buchungen` (Generator reicht `status` durch), `gueltigeOptionen`/`weg()` vorhanden.
- Router/`heimat()`: unverändert; Buchungsheimat bleibt erstes Ding (ADR-0003).
- Mögliche Brüche durch neue Testbuchung: `test_konnektor.py:877` (Zählung), `kalender.py:155–157` (überspringt stornierte, unkritisch), `seiten_browser.mjs` (besucht jede ID, `#B-03` muss sichtbar werden), `test_routen.py:900–937` (eigene Testdaten, unberührt).

### Open Questions
- Keine für den PO. Die Form zeigt die Spec-Freigabe (Phase 3→4); Sammelstelle und Knopf liegen in #149.
