---
entity_id: wackelige-browsertests-568
type: bugfix
created: 2026-11-21
updated: 2026-11-21
status: draft
version: 1
workflow: fix-568-kartenlegende-wackelig
tags: [browsertests, wartepunkt, vorlage, kartenlegende]
---

# Wackeliger Browsertest Kartenlegende: Signal „Live-Daten geladen“ als Wartepunkt (#568)

Grundlage: `docs/context/fix-568-kartenlegende-wackelig.md` (Kontext, Nachstellung, Analyse). Verwandt: #369, #457, #550 (auf den Zielzustand warten, nicht auf ein Zwischensignal).

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Die Vorlage bekommt nur ein Merkmal am Wurzelelement, das nichts darstellt und keine Reisedaten, Schnittstellen oder Texte berührt. Der Kern aus ADR-0001 ist nicht berührt.

## Purpose

Der Browsertest der Kartenlegende war in der CI einmal rot, ohne dass die Seite einen Fehler hat: Er greift auf die Etappenkarte zu, während die Seite sie gerade durch eine neue ersetzt. Die Seite soll deshalb selbst anzeigen, wann sie nach dem Laden der Live-Daten fertig neu gezeichnet hat, und die Browsertests sollen darauf warten, statt auf das erste Erscheinen eines Elements.

## Verhalten / Ursache

1. Am Ende des Skripts zeichnet `route()` die Etappenansicht; `.ekarte` erscheint (nachgestellt nach etwa 205 ms).
2. Danach laden sechs Lader die Live-Daten (`Promise.all(...)`), anschließend zeichnet `route(true)` die Ansicht erneut (etwa 403 ms). `route()` leert dabei `#main` mit `replaceChildren()` und baut eine neue `.ekarte`.
3. `seiten_karte_legende.mjs` wartet nur auf das erste Erscheinen von `.ekarte` und greift sofort zu; fällt der Zugriff in den zweiten Aufbau, ist das Element nicht mehr im DOM. `seiten_bilder_csp.mjs` hat dieselbe Folge.
4. Alle sechs Lader fangen Netzfehler selbst ab; `Promise.all` erfüllt sich daher auch bei abgebrochenem `api/**` (so läuft der Test), und `route(true)` läuft genau einmal nach dem ersten Aufbau.

Das Neuzeichnen ist gewollt (Live-Daten erscheinen nach dem Laden); der Fehler liegt im Wartepunkt der Tests. Für Nutzer ändert sich nichts.

## Source

- **File:** `engine/vorlage.html`, `engine/tests/seiten_karte_legende.mjs`, `engine/tests/seiten_bilder_csp.mjs`
- **Identifier:** `Promise.all([ichLaden(), ...]).then(...)` am Skriptende der Vorlage; Wartepunkt vor `.ekarte` in beiden Skripten

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| Playwright (feste Version) | extern | Browser für die Messskripte, `waitForSelector` auf das Signal |
| Beispielreise (beide: Wanderung und Städtewochenende) | Testgrundlage | Seite, auf der das Signal geprüft wird |
| `bauen.bauen` | Engine | baut die Seite aus der Vorlage für die Tests |
| `engine/tests/test_karte_legende.py` | Test | Rahmen: baut Beispielreise mit Attrappen, startet Server, ruft das Skript |
| `route()` und die sechs Lader in `engine/vorlage.html` | Vorlage | Neuzeichnen nach dem Laden; die Lader werfen nie |

Keine Änderung an Datenformat, Schnittstelle, Instanz oder sichtbaren Texten (ADR-0006 unberührt); kein `nachziehen`, kein Instanztest nötig.

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/vorlage.html` | MODIFY | `.then(() => route(true))` wird zu `.then(() => { route(true); document.documentElement.dataset.geladen = "1"; })`, mit Kommentar, warum |
| `engine/tests/seiten_karte_legende.mjs` | MODIFY | vor `waitForSelector(".ekarte")` auf `html[data-geladen]` warten (`state: "attached"`) |
| `engine/tests/seiten_bilder_csp.mjs` | MODIFY | dito |
| `engine/tests/test_karte_legende.py` oder neuer Test | MODIFY/CREATE | Nachweis des Signals (siehe Tests) |
| `docs/design.md` und/oder Kopfkommentar der Vorlage | MODIFY | Signal als Wartepunkt-Regel dokumentieren |

### Estimated Changes

- Files: 4 bis 5
- LoC: +25/-2

### Nicht im Scope

- Andere wackelige Tests (#565, #599 und weitere), eigene Issues.
- Ein anderes Verhalten der Seite (etwa das zweite Neuzeichnen zu vermeiden); es ist gewollt.
- `waitForLoadState("networkidle")` (von Playwright abgeraten) und Wiederholen bei „not attached“ (verdeckt das Rennen).

### Gilt für

Das Signal gilt für jede Reise und jede Ansicht, nicht nur für die Etappenkarte: Es hängt am Wurzelelement der Seite und wird gesetzt, sobald der Erstaufbau samt Live-Daten steht. Zu bedenken sind beide Beispielreisen: Wanderung (Etappenkarte, `#E-01`) und Städtewochenende (Ansichten ohne Wanderung); in beiden wird `route(true)` genau einmal ausgeführt und das Signal danach gesetzt.

## Implementation Details

Grundsatz: auf den Zielzustand der Seite warten, nicht auf einen Zeitpunkt oder ein Zwischensignal (#369, #457, #550).

1. **Vorlage.** Nach `route(true)` setzt der `then`-Zweig `document.documentElement.dataset.geladen = "1"`. Die Lader werfen nie, das Signal kommt also immer, auch bei abgebrochenem `api/**`. Der Kommentar nennt: Live-Daten geladen, Ansicht steht, Wartepunkt für Browsertests.
2. **Skripte.** Zwischen `goto` und `waitForSelector(".ekarte")`: `await p.waitForSelector("html[data-geladen]", {state: "attached"});`. Erst danach wird auf die Karte zugegriffen und gescrollt. Die Karte wird nach `route(true)` bei Sicht (`beiSicht`) gezeichnet; deshalb scrollt der Test erst nach dem Signal.
3. **Wissenskarte.** Der zweite Teil von `seiten_karte_legende.mjs` wechselt nur den Anker (selbes Dokument, `hashchange`); das Signal steht dann schon und es gibt kein zweites Neuzeichnen.
4. **Doku.** Das Signal steht als Wartepunkt-Regel in `docs/design.md` und/oder im Kopfkommentar der Vorlage: Browsertests, die nach dem Laden auf Inhalte zugreifen, warten auf `html[data-geladen]`.

## Test Plan

- [ ] Test 1 (Signal ohne Dienst): GIVEN die gebaute Beispielreise und abgebrochenes `api/**` / WHEN die Seite lädt / THEN ist `html[data-geladen]` gesetzt; gilt für Wanderung und Städtewochenende.
- [ ] Test 2 (Signal nach dem Neuzeichnen): GIVEN eine Sonde zählt `replaceChildren` von `#main` / WHEN `data-geladen` erscheint / THEN erfolgt nach dem Signal beim Erstaufbau kein weiteres `replaceChildren` (Anzahl 0) und `.ekarte` bleibt dasselbe Element.
- [ ] Test 3 (statische Prüfung): GIVEN die Quelltexte beider Skripte / WHEN sie gelesen werden / THEN steht in beiden `html[data-geladen]` vor `waitForSelector(".ekarte")`.
- [ ] Test 4 (Doku): GIVEN `docs/design.md` bzw. die Vorlage / WHEN sie gelesen werden / THEN nennt die Doku `data-geladen` als Wartepunkt.
- [ ] Test 5 (Wiederholung): GIVEN beide Browsertests / WHEN sie 20-mal unter `-n auto` laufen / THEN bleibt jeder Lauf grün.

Test 1 und 2 sind vor der Änderung rot (Signal fehlt).

## Acceptance Criteria

- **AC-1:** Das Signal `data-geladen` wird immer genau nach dem Neuzeichnen durch `route(true)` gesetzt, auch wenn alle Lader scheitern (`api/**` abgebrochen). Test: Test 1.
- **AC-2:** Nach dem Signal findet beim Erstaufbau kein weiteres `replaceChildren` von `#main` statt. Test: Test 2.
- **AC-3:** Die Seite sieht nicht anders aus und verhält sich nicht anders; das Signal ist unsichtbar und ändert keine Texte. Test: bestehende Browser- und Bildtests bleiben unverändert grün; kein Eintrag in den Textkatalogen.
- **AC-4:** `seiten_karte_legende.mjs` und `seiten_bilder_csp.mjs` warten vor dem ersten Zugriff auf `.ekarte` auf `html[data-geladen]`. Test: Test 3.
- **AC-5:** Die Doku nennt das Signal als Wartepunkt-Regel (#369, #457, #550). Test: Test 4.
- **AC-6:** 20 Wiederholungsläufe von `test_karte_legende.py` und des Tests mit `seiten_bilder_csp.mjs` unter `-n auto` bleiben ohne Rot; danach die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) grün. Test: Test 5 (manuell, Ergebnis im Nachweis) und CI.

## Risks

- **Signal bleibt aus:** Würde ein Lader doch werfen, käme `route(true)` nie und die Tests liefen in die Frist. Begrenzt durch Test 1 (alle Lader scheitern) und die Prüfung, dass die Lader Fehler selbst abfangen.
- **Karte noch nicht gezeichnet:** Nach `route(true)` wird die Karte erst bei Sicht gezeichnet; die Tests scrollen deshalb erst nach dem Signal und warten danach weiter auf `.ekarte`.
- **Signal verdeckt echten Fehler:** Es wartet nur auf das Ende des Erstaufbaus, nie auf einen Sollwert; Prüfungen bleiben in den Python-Tests.
- **Weitere Wackelstellen:** Tritt nach der Änderung noch ein Rot auf, wird die Stelle nach demselben Muster ergänzt und im Issue vermerkt.

## Definition of Done

- [ ] AC-1 bis AC-5 durch Test 1 bis 4 belegt
- [ ] AC-6 durch Wiederholungsläufe und grüne Pflichtprüfungen belegt
- [ ] Auslieferung nur über den normalen Weg (Pull Request, grüne Pflichtprüfungen, Vorspulen)
- [ ] Issue #568 erst nach grünem Lauf auf `main` schließen

## Changelog

- 2026-11-21: Initiale Spec (#568)
