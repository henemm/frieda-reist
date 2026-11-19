# Context: fix-599-wackelige-browsertests

## Request Summary
Zwei WebKit-Browsertests scheitern unter hoher Serverlast zufällig (#599): `test_karte_popup_310[webkit]` und
`test_seite.py::test_alle_ansichten_der_beispielreise[webkit]` (Leiste als App). Sie sollen auf den tatsächlichen
Endzustand warten statt auf feste Zeiten bzw. zu früh einsetzende Ruhe, ohne echte Fehler zu verdecken.

Der zweite Teil des Issues („soll ein wackeliger Test das Veröffentlichen sperren?“) ist inzwischen erledigt: #600
(Software-Tests einmal je Software-Stand statt je Reise) und #168 (gleiches Tor für Nachziehen, Inhaltstests nur Warnung).
Ein roter Software-Test hält aber weiterhin die Übernahme eines neuen Software-Stands an; darum bleibt die Ursache zu beheben.

## Related Files
| File | Relevance |
|------|-----------|
| engine/tests/seiten_karte_popup.mjs | Ablauf Popup/Ansicht; nach Klick auf die Ansicht feste `waitForTimeout(600)`, dann Messung von Zoom/Ausschnitt. Unter Last steht die Karte noch auf Zwischenstand (zoom 18, `alle: false`) |
| engine/tests/test_karte_popup_310.py | Prüfungen: Ansicht hat 2 Punkte, alle im Ausschnitt, Spanne < 0.05 |
| engine/tests/seiten_browser.mjs:138-186 | Leiste als App: `unten()` wartet, bis der untere Rand der Leiste 3 Bilder still steht (Rückfall 3 s). Steht die Leiste vor dem Eintreffen des resize-Ereignisses schon still auf 488, wird zu früh gemessen |
| engine/tests/test_seite.py:81-85 | Erwartung App: start/klein/zu/voll/luege = 788, tippt = 488; Browser: klein/tippt/zu = 488 |
| engine/vorlage.html:6578-6613 | Höhe als App: `messen()` an resize/visualViewport/focusin/focusout(50, 400 ms); setzt `--hoehe-fehlt` aus größter Unterkante je Breite |
| engine/vorlage.html:3271, 3400, 3455, 4508 | `fitBounds` der Karte (teils animiert) – Ursache der Kamerafahrt nach Wahl einer Ansicht |

## Existing Patterns
- Warten auf Bedingung statt Zeit: `p.waitForFunction(f, arg, {timeout})` in pwa_browser.mjs, seiten_bilder_csp.mjs,
  seiten_brett.mjs (`warte`), seiten_karte_legende.mjs (mit `.catch(() => {})`, danach wird gemessen und im Python-Test geprüft).
- Damit bleibt die Prüfung im Python-Test; die Hilfsdatei wartet nur bis zum erwarteten Zustand oder bis zur Frist und
  meldet dann den gemessenen Wert (echter Fehler → nach Frist roter Test mit Messwert).
- Ruhe-Erkennung über `requestAnimationFrame` (seiten_browser.mjs `unten()`, #159).

## Dependencies
- Upstream: Playwright (WebKit, Chromium), Leaflet-Karte `KARTE` (global in der Vorlage), Vorlage `vorlage.html`.
- Downstream: Software-Tests in CI und auf dem Server (deploy.sh / Nachziehen): ein roter Test sperrt die Übernahme eines
  neuen Software-Stands.

## Existing Specs
- Keine Spec für die Testhilfen; Verhalten der Leiste: Kommentar in vorlage.html (#159, Foto 7.11.2026). Karte/Popup: #310.

## Risks & Considerations
- Warten auf das erwartete Ergebnis darf einen echten Fehler nicht verdecken: Frist begrenzt, danach wird der echte Wert
  gemeldet und geprüft.
- Unter Last nachstellen ist auf dem Live-Server heikel (Dienste laufen dort). Nachweis über künstliche Verzögerung in der
  Seite (Test-Hook) oder kurze, niedrig priorisierte Last; nicht die Dienste beeinträchtigen.
- Verwandte wackelige Tests #568 (Kartenlegende) und #565 (PWA) stehen in M7 direkt danach; nicht in diesem Workflow.
- Es wird nur Testcode geändert; die Vorlage bleibt unverändert, außer die Analyse findet einen echten Fehler.

## Analysis

### Type
Bug (wackelige Tests; kein Fehler der Seite selbst)

### Ursachen (aus dem Code, nicht nur aus dem Symptom)

**1. Karte: `test_punkt_mit_popup_kurztext_und_ausschnitt_310[webkit]`** — `{"zoom": 18, "spanne": [0.00193, 0.00193], "alle": False}`
- Der Klick auf eine Ansicht ruft `route(true)`; die Übersichtskarte wird neu gebaut (`karteZeichnen`, vorlage.html ~3117).
  Der Kasten hängt beim Bau noch nicht im Dokument, `anfangen()` ruft `fitBounds` auf eine 0-Pixel-Karte → Leaflet setzt
  `maxZoom` (18 ohne Grundkarte). Erst der `ResizeObserver` (vorlage.html ~3280) ruft `invalidateSize()` und noch einmal
  `anfangen()` mit echtem Maß (Zoom ~15, danach evtl. animierter Zoom).
- Zoom 18 im Fehlerbild heißt: zum Messzeitpunkt (feste 600 ms nach dem Klick, `seiten_karte_popup.mjs`) hatte der
  ResizeObserver unter Last noch nicht gefeuert. Es ist also keine halbe Kamerafahrt, sondern der Zustand vor der ersten
  echten Vermessung. Das Issue vermutete moveend; ein Warten auf `moveend` allein griffe zu kurz (das erste `moveend`
  kommt schon vom 0-Pixel-`fitBounds`).
- Für Nutzer kein Fehler: Auf langsamen Geräten stellt der ResizeObserver den Ausschnitt etwas später richtig.

**2. Leiste als App: `test_seite.py::test_alle_ansichten_der_beispielreise[webkit]`** — 788 statt 488 (bzw. umgekehrt)
- `seiten_browser.mjs` misst mit `unten()` (3 Bilder Ruhe). Ruhe beweist aber nicht, dass die Vorlage schon reagiert hat:
  - Schritt `zu`: nach `blur()` misst die Vorlage per `setTimeout(messen, 50/400)`; der Test wartet 500 ms in **Node-Zeit**
    (`waitForTimeout`). Unter Last laufen die Zeitgeber der Seite später; die Leiste steht dann noch still auf 488 → Messung
    488, erwartet 788. Wahrscheinlichster Fall.
  - Schritte `klein`/`voll`: `hoehe()` wartet nur auf `innerHeight === h`, nicht auf das `resize`-Ereignis, an dem `messen()`
    hängt. Steht die Leiste vor dem Ereignis still, wird zu früh gemessen.
  - `tippt` (focusin) und `luege` (synchrones `dispatchEvent`) sind ohne Lücke.
- Welche Zeile im Lauf vom 16.11. rot war, steht nicht im Issue; der Ansatz deckt alle drei Lücken ab.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/tests/seiten_karte_popup.mjs | MODIFY | Nach Klick auf die Ansicht statt `waitForTimeout(600)`: `waitForFunction` bis Karte vermessen (Größe > 0), alle Ansichtspunkte im Ausschnitt und keine Zoom-/Schwenk-Animation, Frist ~10 s, `.catch(() => {})`; danach wie bisher messen |
| engine/tests/seiten_browser.mjs | MODIFY | Leiste: `hoehe()` wartet zusätzlich auf ein `resize`-Ereignis nach der Größenänderung (Hörer vor `setViewportSize` einhängen); nach `blur()` in der Seite einen eigenen Zeitgeber > 400 ms abwarten (läuft nach dem 400-ms-Zeitgeber der Vorlage), statt 500 ms Node-Zeit |
| engine/tests/test_wackel_599.py (Name offen) | CREATE | Nachweis unter künstlicher Verzögerung: Init-Skript verzögert ResizeObserver-Rückrufe bzw. Zeitgeber/resize der Seite; alter Ablauf rot, neuer grün. Umgesetzt über eine Umgebungsvariable der Hilfsdateien (nur Testcode) |
| engine/tests/test_karte_popup_310.py, test_seite.py | unverändert | Prüfungen bleiben, wie sie sind |

### Scope Assessment
- Files: 2 geändert, 1 neu (nur Tests)
- Estimated LoC: +60/-5
- Risk Level: LOW — nur Testcode, Vorlage unverändert

### Technical Approach
- Warten auf Bedingung statt Zeit (Muster `waitForFunction` wie in seiten_karte_legende.mjs, seiten_brett.mjs).
- Leiste: auf das **Ereignis bzw. den Zeitgeber, an dem die Vorlage hängt**, warten, nicht auf den erwarteten Wert. So
  bleibt jeder echte Fehler sichtbar: Rechnet `messen()` falsch, steht danach der falsche Wert still und der Test bleibt rot.
- Karte: Bedingung enthält den Sollzustand („alle Punkte im Ausschnitt“), aber mit Frist und `.catch`; danach wird der
  echte Zustand gemessen und im Python-Test geprüft. Ein echter Fehler wird damit nach ~10 s rot mit Messwert, nicht verdeckt.
  Dazu „keine Animation“ (`!KARTE._animatingZoom`, kein laufender `_panAnim`) und Größe > 0, damit nicht mitten in der
  Fahrt gemessen wird.
- Nachweis: Verzögerung per Init-Skript (ResizeObserver-Rückruf +1,5 s; `setTimeout` der Seite +700 ms; `resize` verzögert)
  nur wenn eine Umgebungsvariable gesetzt ist. Kein Lasttest auf dem Live-Server.

### Dependencies
- Playwright (WebKit, Chromium), Leaflet-Interna `_animatingZoom`/`_panAnim` (vendored, Version fest).
- Downstream: Software-Tests in CI und auf dem Server; keine Schnittstelle, kein Format, keine Texte → keine Instanz-Tests nötig.

### Open Questions
- keine (reine Testcode-Änderung, keine Produktentscheidung)
