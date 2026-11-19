---
entity_id: wackelige-browsertests-599
type: bugfix
created: 2026-11-19
updated: 2026-11-19
status: draft
workflow: fix-599-wackelige-browsertests
---

# Wackelige WebKit-Browsertests unter Last stabilisieren (#599)

Grundlage: `docs/context/fix-599-wackelige-browsertests.md` (Kontext, Analyse, Ursachen).

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es ändern sich nur Testskripte und ein neuer Nachweistest. Seite, Vorlage, Engine und Betrieb bleiben unverändert, der Kern aus ADR-0001 ist nicht berührt.

## Purpose

Zwei WebKit-Browsertests scheitern unter hoher Serverlast zufällig, ohne dass die Seite einen Fehler hat: die Prüfung von Popup und Ausschnitt der Karte (`test_karte_popup_310[webkit]`) und die Höhe der Leiste als App (`test_seite.py::test_alle_ansichten_der_beispielreise[webkit]`). Ein roter Software-Test hält die Übernahme eines neuen Software-Stands an. Die Tests sollen auf den Zustand warten, an dem die Seite tatsächlich reagiert hat, statt auf feste Zeiten oder zu früh einsetzende Ruhe, und echte Fehler weiterhin sichtbar machen.

## Ursachen

1. **Karte.** Nach dem Klick auf eine Ansicht wartet `seiten_karte_popup.mjs` fest 600 ms und misst dann Zoom und Ausschnitt. Die Übersichtskarte wird neu gebaut, solange ihr Kasten noch nicht im Dokument hängt; `fitBounds` auf die 0-Pixel-Karte setzt den Höchstzoom (18). Erst der `ResizeObserver` der Karte vermisst neu und stellt den Ausschnitt richtig. Unter Last hat er nach 600 ms noch nicht gefeuert, gemessen wird `zoom 18, alle: false`. Ein Warten auf `moveend` allein griffe zu kurz, weil das erste `moveend` schon vom 0-Pixel-`fitBounds` kommt.
2. **Leiste als App.** `seiten_browser.mjs` misst mit `unten()` nach drei Bildern Ruhe. Ruhe beweist nicht, dass die Vorlage schon reagiert hat: Nach `blur()` misst die Vorlage per Zeitgeber (50 und 400 ms in der Seite), der Test wartet aber 500 ms in Node-Zeit; und `hoehe()` wartet nur auf die neue `innerHeight`, nicht auf das `resize`-Ereignis, an dem die Vorlage hängt. Steht die Leiste vor der Reaktion still auf dem alten Wert, wird dieser gemessen (788 statt 488 oder umgekehrt). `tippt` (focusin) und `luege` (synchrones Ereignis) haben keine Lücke.

Für Nutzer ist beides kein Fehler: auf langsamen Geräten stellt sich die Seite etwas später richtig ein.

## Source

- **File:** `engine/tests/seiten_karte_popup.mjs`, `engine/tests/seiten_browser.mjs`, `engine/tests/test_wackel_599.py`
- **Identifier:** Messskript Popup/Ansicht der Karte, Funktionen `hoehe()` und `unten()` und der Schritt `zu` der Leiste als App, neuer Test `test_wackel_599`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| Playwright (WebKit, Chromium), Node | extern | Browser für die Messskripte |
| Leaflet (vendored, Version fest), Interna `_animatingZoom`, `_panAnim` | extern | Erkennen einer laufenden Zoom- oder Schwenk-Animation der Karte |
| globale `KARTE` in `engine/vorlage.html` | Vorlage | Kartenobjekt, wird nur gelesen |
| `engine/tests/test_karte_popup_310.py` | Test | ruft `seiten_karte_popup.mjs` auf und prüft: Ansicht hat 2 Punkte, alle im Ausschnitt, Spanne < 0.05; bleibt unverändert |
| `engine/tests/test_seite.py` | Test | ruft `seiten_browser.mjs` auf, Erwartung App: start/klein/zu/voll/luege 788, tippt 488; Browser: klein/tippt/zu 488; bleibt unverändert |
| Muster `waitForFunction` mit Frist und `.catch` | Vorgehen | wie in `seiten_karte_legende.mjs`, `seiten_brett.mjs`: warten, bei Fristablauf weiter messen, im Python-Test prüfen |
| Software-Tests in CI und auf dem Server (`deploy.sh`, Nachziehen) | Downstream | ein roter Test hält die Übernahme eines Software-Stands an |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/tests/seiten_karte_popup.mjs` | MODIFY | Statt `waitForTimeout(600)` nach dem Klick auf die Ansicht: `waitForFunction` bis Karte vermessen (Größe > 0), alle Ansichtspunkte im Ausschnitt und keine Zoom-/Schwenk-Animation; Frist etwa 10 s mit `.catch`, danach wie bisher messen |
| `engine/tests/seiten_browser.mjs` | MODIFY | Leiste als App: `hoehe()` wartet zusätzlich auf ein `resize`-Ereignis (Hörer vor `setViewportSize` einhängen); nach `blur()` wartet ein eigener Zeitgeber in der Seite (länger als 400 ms) statt 500 ms Node-Zeit |
| `engine/tests/test_wackel_599.py` | CREATE | Nachweis unter künstlicher Verzögerung |
| `engine/tests/verzoegerung.mjs` | CREATE | Hülle um das Playwright-Modul: hängt jeder Browser-Umgebung ein Init-Skript mit der Verzögerung an (`RH_VERZOEGERN`, `RH_PLAYWRIGHT_ECHT`); die Messskripte bleiben dafür unverändert |

Unverändert: `engine/tests/test_karte_popup_310.py`, `engine/tests/test_seite.py`, `engine/vorlage.html`, Engine, `betrieb/`, `.github/workflows/tests.yml`.

### Estimated Changes

- Files: 3
- LoC: +60/-5

### Out of Scope

- Teil 2 des Issues (soll ein wackeliger Test das Veröffentlichen sperren?): erledigt durch #600 (Software-Tests einmal je Software-Stand) und #168 (gleiches Tor für Nachziehen, Inhaltstests nur Warnung).
- Die wackeligen Tests #568 (Kartenlegende) und #565 (PWA), eigene Issues.
- Änderung der Vorlage (etwa die Karte sofort richtig zu vermessen); sie ist für Nutzer nicht fehlerhaft.
- Ein Lasttest auf dem Live-Server; die Dienste dort dürfen nicht beeinträchtigt werden.

## Implementation Details

Grundsatz: auf das Ereignis oder den Zustand warten, an dem die Seite hängt, nicht auf eine Zeit; und nie so warten, dass ein echter Fehler verschwindet.

1. **Karte (`seiten_karte_popup.mjs`).** Nach dem Klick auf die Ansicht wartet `waitForFunction` auf: Kartengröße größer als 0, alle Punkte der Ansicht im Ausschnitt, `KARTE._animatingZoom` nicht gesetzt und kein laufender `_panAnim`. Frist etwa 10 s; läuft sie ab, wird mit `.catch(() => {})` abgefangen und trotzdem gemessen. Die Prüfung bleibt im Python-Test (`test_karte_popup_310.py`): Ein echter Fehler (falscher Endwert) bleibt nach Ablauf der Frist rot, mit Messwert.
2. **Leiste, Größenwechsel (`hoehe()`).** Vor `setViewportSize` wird ein einmaliger `resize`-Hörer in der Seite eingehängt; danach wartet `hoehe()` auf `innerHeight === h` und auf das eingetretene Ereignis, anschließend wie bisher auf Ruhe über `unten()`. Die Vorlage misst an `resize`; der Test misst erst danach.
3. **Leiste, Schritt `zu`.** Nach `blur()` setzt der Test in der Seite einen eigenen Zeitgeber, länger als der 400-ms-Zeitgeber der Vorlage, und wartet auf ihn; er läuft nach dem der Vorlage. Danach folgt die Ruhe-Erkennung wie bisher. Rechnet die Vorlage falsch, steht danach der falsche Wert still und der Test bleibt rot.
4. **Nachweis (`test_wackel_599.py`).** Ist die Umgebungsvariable der Hilfsdateien gesetzt, hängen sie vor dem Laden ein Init-Skript ein: Rückrufe des `ResizeObserver` laufen 1,5 s später, `setTimeout` der Seite 700 ms später, `resize`-Ereignisse verzögert. Der Test führt beide Messskripte unter dieser Verzögerung aus. Der alte Ablauf (feste 600 ms, Warten nur auf `innerHeight` und 500 ms Node-Zeit) wird als rot erwiesen, der neue als grün. Ohne die Variable ändert sich im Verhalten der Hilfsdateien nichts. Der Nachweis läuft in WebKit und Chromium, soweit der Browser vorhanden ist.

## Test Plan

### Automated Tests (TDD RED)

Alle in `engine/tests/test_wackel_599.py`.

- [ ] Test 1 (Karte, Verzögerung): GIVEN das Init-Skript verzögert den `ResizeObserver`-Rückruf der Karte um 1,5 s / WHEN `seiten_karte_popup.mjs` die Ansicht wählt und misst / THEN liegen alle Punkte im Ausschnitt, die Spanne ist kleiner als 0.05 und der Zoom ist nicht der Höchstzoom; vor der Änderung ist dieser Test rot.
- [ ] Test 2 (Leiste, verzögerter Zeitgeber): GIVEN `setTimeout` der Seite läuft 700 ms später / WHEN `seiten_browser.mjs` die Schritte der Leiste als App durchläuft (insbesondere `zu` nach `blur()`) / THEN stimmen alle Höhen mit den Erwartungen aus `test_seite.py` (788, tippt 488); vor der Änderung rot.
- [ ] Test 3 (Leiste, verzögertes resize): GIVEN `resize`-Ereignisse kommen verzögert an / WHEN `klein` und `voll` gemessen werden / THEN wird erst nach dem Ereignis gemessen und die Höhen stimmen; vor der Änderung rot.
- [ ] Test 4 (echter Fehler bleibt rot): GIVEN die Karte erreicht den Sollzustand nie (Verzögerung weit über der Frist oder Punkte außerhalb des Ausschnitts) / WHEN das Skript nach Ablauf der Frist misst / THEN meldet es den echten Messwert (`alle: false`) und `test_karte_popup_310.py` bewertet ihn als Fehler.
- [ ] Test 5 (statische Prüfung): GIVEN die Quelltexte von `seiten_karte_popup.mjs` und `seiten_browser.mjs` / WHEN sie gelesen werden / THEN steht in der Karte kein `waitForTimeout(600)` mehr, sondern ein `waitForFunction` mit Frist und `.catch`, und `hoehe()` hängt einen `resize`-Hörer vor `setViewportSize` ein.

### Manuelle Prüfung (Erfolgsnachweis)

- Prüfung 6 (Vorlage unverändert): Der Vergleich des Stands mit `main` zeigt keine Änderung an `engine/vorlage.html`, Engine, `betrieb/`, `test_karte_popup_310.py` und `test_seite.py`.
- Laufzeit: Die beiden betroffenen Tests ohne Verzögerung vor und nach der Änderung messen; kein merklicher Unterschied.
- Danach mehrere Gesamtläufe `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` ohne Rot. Kurze, niedrig priorisierte Last auf dem Entwicklungsrechner ist erlaubt, nicht auf dem Live-Server.

## Acceptance Criteria

- **AC-1:** Given die Verzögerung des `ResizeObserver`-Rückrufs um 1,5 s / When `test_karte_popup_310[webkit]` läuft / Then ist er grün, weil `seiten_karte_popup.mjs` bis zu einer vermessenen Karte (Größe > 0) mit allen Ansichtspunkten im Ausschnitt und ohne laufende Animation wartet (Test 1).
  Test: `engine/tests/test_wackel_599.py::test_karte_unter_verzoegertem_resizeobserver`
- **AC-2:** Given `setTimeout` der Seite 700 ms später / When `test_alle_ansichten_der_beispielreise[webkit]` die Schritte der Leiste als App durchläuft / Then ist er grün, weil nach `blur()` ein Zeitgeber in der Seite abgewartet wird, der nach dem der Vorlage läuft (Test 2).
  Test: `engine/tests/test_wackel_599.py::test_leiste_unter_verzoegertem_zeitgeber`
- **AC-3:** Given `resize` verzögert / When `hoehe()` nach `setViewportSize` misst / Then wartet es auf das `resize`-Ereignis und liest erst danach; die Erwartungen aus `test_seite.py` gelten unverändert (Test 3).
  Test: `engine/tests/test_wackel_599.py::test_leiste_unter_verzoegertem_resize`
- **AC-4:** Given der alte Ablauf (feste 600 ms, Warten nur auf `innerHeight`, 500 ms Node-Zeit) / When er unter derselben Verzögerung läuft / Then ist er rot; damit ist belegt, dass der Nachweistest die Wackelstelle trifft (Test 1 bis 3).
  Test: `engine/tests/test_wackel_599.py::test_alter_ablauf_ist_unter_verzoegerung_rot`
- **AC-5:** Given ein echter Fehler, bei dem der Sollzustand der Karte nie erreicht wird / When die Frist von etwa 10 s abgelaufen ist / Then misst das Skript weiter, meldet den echten Wert und `test_karte_popup_310.py` ist rot; der Fehler wird nicht verdeckt (Test 4).
  Test: `engine/tests/test_wackel_599.py::test_echter_fehler_bleibt_rot`
- **AC-6:** Given die Laufzeit im Normalfall ohne Verzögerung / When die beiden betroffenen Tests vor und nach der Änderung gemessen werden / Then steigt die Laufzeit der Suite nicht merklich (Zuwachs deutlich unter 1 s je Test, weil auf den Zustand statt auf feste Zeit gewartet wird).
  Test: manuell (Laufzeitmessung vor und nach der Änderung, Ergebnis im Nachweis)
- **AC-7:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then sind `engine/vorlage.html`, `test_karte_popup_310.py`, `test_seite.py`, Engine und `betrieb/` unverändert (Prüfung 6).
  Test: `engine/tests/test_wackel_599.py::test_quelltext_wartet_auf_zustand` (statisch, Test 5) und manuell Vergleich mit `main`
- **AC-8:** Given mehrere Gesamtläufe mit `-n 3` / When sie nach der Umsetzung laufen / Then sind alle grün, und die Pflichtprüfungen (`tests (leer)`, `tests (instanz)`, `gitleaks`) sind grün.
  Test: manuell (Gesamtläufe `-n 3`) und CI

## Risks

- **Warten verdeckt echten Fehler:** Begrenzt durch Frist und `.catch` mit anschließender Messung; die Prüfung bleibt im Python-Test (AC-5). Bei der Leiste wird auf Ereignis und Zeitgeber gewartet, nie auf den Sollwert, ein falscher Wert bleibt also sichtbar.
- **Leaflet-Interna:** `_animatingZoom` und `_panAnim` sind keine öffentliche Schnittstelle; die Version ist vendored und fest. Fehlen die Felder, gilt „keine Animation“ und die Frist greift.
- **Nachweis nicht identisch mit echter Last:** Die künstliche Verzögerung stellt die Wackelstelle nach, nicht jede denkbare Lastlage. Tritt danach noch ein Rot auf, wird die Stelle nach demselben Muster ergänzt und im Issue vermerkt.

## Definition of Done

- [ ] AC-1 bis AC-7 durch Test 1 bis 5 und Prüfung 6 belegt
- [ ] AC-8 durch mehrere Gesamtläufe und grüne Pflichtprüfungen belegt
- [ ] Auslieferung nur über den normalen Weg (Pull Request, grüne Pflichtprüfungen, Vorspulen)
- [ ] Issue #599 erst nach grünem Lauf auf `main` schließen

## Changelog

- 2026-11-19: Initiale Spec (#599)
- 2026-11-19: Testzuordnung je AC ergänzt (Validierung)
- 2026-11-19 (TDD RED): Die Verzögerung steckt nicht in den Hilfsdateien, sondern in einer eigenen Hülle `verzoegerung.mjs`, die statt des Playwright-Moduls übergeben wird. So ändern sich die Messskripte nur am Warten, und der Nachweis läuft auch gegen den alten Stand. AC-4 läuft den alten Stand aus der Geschichte (`git show`), im flachen Checkout der CI übersprungen; AC-4 und AC-5 sind Wächter und schon vor der Änderung grün, rot sind vorher AC-1 bis AC-3 und der statische Test.
