# Context: fix-568-kartenlegende-wackelig

## Request Summary
Der Browsertest der Kartenlegende (`test_karte_legende.py`) war in der CI einmal rot: `scrollIntoViewIfNeeded` auf `.ekarte`
traf ein Element, das die Seite gerade ersetzt hatte. Ursache bestätigen, Wartepunkt ergänzen, Wiederholungsläufe ohne Rot.

## Ursache (nachgestellt, 21.11.2026)
Sonde (`replaceChildren` von `#main` mit Stack protokolliert) auf der gebauten Beispielreise mit Kartenattrappe, `#E-01`, 390 px,
Chromium, `api/**` abgebrochen wie im Test:

1. t≈205 ms: `route()` am Ende des Skripts (`engine/vorlage.html:6573`) zeichnet die Etappenansicht, `.ekarte` erscheint.
2. t≈403 ms: `Promise.all([ichLaden(), rmLaden(), agLaden(), brLaden(), blLaden(), psLaden()]).then(() => route(true))`
   (`engine/vorlage.html:6576`) zeichnet die Ansicht erneut; `route()` leert `#main` (`m.replaceChildren()`, Zeile 6462)
   und baut eine neue `.ekarte`.

Der Test wartet in `engine/tests/seiten_karte_legende.mjs:19` nur auf das erste Erscheinen von `.ekarte` und greift in Zeile 20
zu. Fällt der Zugriff in den zweiten Aufbau, ist das Element nicht mehr im DOM. Das Neuzeichnen ist gewollt (Live-Daten des
Dienstes erscheinen nach dem Laden), der Fehler liegt im Wartepunkt des Tests. Gleiches Muster wie #550 (Test wartet auf ein
Zwischensignal statt auf den Zielzustand).

## Related Files
| File | Relevance |
|------|-----------|
| engine/tests/seiten_karte_legende.mjs | Zeilen 18–21: Wartepunkt vor dem ersten Zugriff auf die Etappenkarte |
| engine/tests/test_karte_legende.py | Rahmen: baut Beispielreise mit Attrappen, startet Server, ruft das Skript |
| engine/vorlage.html:6573–6576 | erstes `route()` und Neuzeichnen nach dem Laden der Live-Daten |
| engine/vorlage.html:3308 (`beiSicht`) | Karte wird erst bei Sicht gezeichnet; nach `route(true)` bleibt die Scrollposition |

## Existing Patterns
- #369, #457, #550: auf den fachlichen Zielzustand warten (`waitForFunction` liefert Prüfung und Messung aus einem Augenblick).
- Es gibt bisher kein Signal der Seite „Live-Daten geladen, Ansicht steht“; Tests warten auf Selektoren.

## Dependencies
- Upstream: Playwright (feste Version), Beispielreise, `bauen.bauen`.
- Downstream: nur dieser Test; ein Signal in der Vorlage wäre für weitere Browsertests nutzbar.

## Existing Specs
- keine zu diesem Test; Vorbild `docs/specs` der #550-Arbeit (Wartepunkte).

## Risks & Considerations
- Ein Signal in der Vorlage muss auch gesetzt werden, wenn Lader scheitern (in Tests werden alle `api/**` abgebrochen).
- Nach `route(true)` muss die Karte erneut in Sicht kommen, damit sie gezeichnet wird; der Test scrollt erst nach dem Signal.

## Analysis

### Type
Bug (wackeliger Browsertest; die Seite verhält sich richtig, der Wartepunkt des Tests ist falsch)

### Bestätigte Ursache
Siehe „Ursache“ oben. Ergänzend geprüft (21.11.2026): alle sechs Lader (`ichLaden`, `rmLaden`, `agLaden`, `brLaden`, `blLaden`,
`psLaden`) fangen Netzfehler selbst ab; `Promise.all(...)` erfüllt sich daher auch bei abgebrochenem `api/**`, und `route(true)`
läuft in jedem Testlauf genau einmal nach dem ersten Aufbau. Der zweite Teil des Tests (Wissenskarte) wechselt nur den Anker
(`goto` mit anderem `#…` = Navigation im selben Dokument, `hashchange` → `route()`), dort gibt es kein zweites Neuzeichnen.

Gleiches Muster an zweiter Stelle: `engine/tests/seiten_bilder_csp.mjs:19–21` (identische Folge `goto #E-01` →
`waitForSelector(".ekarte")` → `scrollIntoViewIfNeeded`). Wird mitbehoben.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/vorlage.html | MODIFY | nach `route(true)` im `Promise.all(...).then` ein Signal setzen: `document.documentElement.dataset.geladen = "1"` (Live-Daten geladen, Ansicht steht); Kommentar warum |
| engine/tests/seiten_karte_legende.mjs | MODIFY | vor dem ersten Zugriff auf `.ekarte` auf `html[data-geladen]` warten |
| engine/tests/seiten_bilder_csp.mjs | MODIFY | dito |
| engine/tests/test_karte_legende.py (o. neuer Test) | MODIFY/CREATE | Prüfung des Signals: Seite setzt `data-geladen` auch bei abgebrochenem `api/**`; erst danach ist `.ekarte` stabil (kein zweites `replaceChildren` nach dem Signal) |
| docs/design.md o. Kopfkommentar Vorlage | MODIFY | Signal für Browsertests kurz dokumentieren (Wartepunkt-Regel #369/#457/#550) |

### Scope Assessment
- Files: 4–5
- Estimated LoC: +25/−2
- Risk Level: LOW (ein Attribut am Wurzelelement, keine sichtbare Änderung; Tests sonst unverändert)

### Technical Approach
Abgewogen:
- A) **Signal der Seite** (`data-geladen` nach dem Neuzeichnen), Tests warten darauf. Zielzustand statt Zeitpunkt, wie #369/#457/#550;
  wiederverwendbar für alle Browsertests, die nach dem Laden zugreifen. **Empfehlung.**
- B) Nur im Test `waitForLoadState("networkidle")`: von Playwright ausdrücklich abgeraten, hängt an Netzverhalten, nicht am Zustand.
- C) Zugriff bei „not attached“ wiederholen: kaschiert das Rennen, misst womöglich an einer Karte, die gleich ersetzt wird.

Umsetzung A: In `engine/vorlage.html` die Zeile 6576 zu
`.then(() => { route(true); document.documentElement.dataset.geladen = "1"; })`. Die Lader werfen nie (siehe oben), das Signal
kommt also immer. In beiden Skripten zwischen `goto` und `waitForSelector(".ekarte")`:
`await p.waitForSelector("html[data-geladen]", {state: "attached"});`. Nachweis: RED-Test, der in einer Sonde die
`replaceChildren`-Aufrufe von `#main` nach Setzen des Signals zählt (muss 0 sein) und dass das Signal ohne Dienst gesetzt wird;
danach Wiederholungsläufe beider Browsertests (z. B. 20× unter `-n auto`) ohne Rot.

### Dependencies
Nur Testskripte und eine Zeile Vorlage; kein Datenformat, keine Schnittstelle, keine Instanz betroffen (kein `nachziehen`, kein
Instanztest nötig). Kein sichtbarer Text (ADR-0006 unberührt).

### Open Questions
- keine (rein technisch; keine Produktentscheidung)
