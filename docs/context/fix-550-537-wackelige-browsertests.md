# Kontext: Wackelige Browsertests (#550, #537)

## Request Summary

Drei Browsertests scheitern gelegentlich, ohne dass die Seite sich geändert hat: zwei webkit-Tests unter voller Parallel-Last auf dem Server (#550) und der Vollseiten-Screenshot der Bausteinseite in der CI (#537). Ziel: Wartebedingung statt Zeit bzw. robuster Screenshot, danach mehrere Gesamtläufe parallel grün (Vorgehen wie #457, #369).

## Related Files

| Datei | Relevanz |
|------|-----------|
| `engine/tests/seiten_packliste.mjs` (Z. 155–169) | Einklappen #511: nach dem Haken an „Wanderschuhe“ wird `knopf0 = texte(".pack-alle")[0]` sofort gelesen. Ergebnis im Fehlerfall: `""` |
| `engine/vorlage.html` (Z. ~5668, `plAlleKnopf`) | Der Knopf wird leer erzeugt; den Text setzt `stand()` erst per `setTimeout(stand)` bzw. im `toggle`-Listener. Wird die Ansicht nach dem Haken neu gezeichnet, ist der neue Knopf bis zum nächsten Takt leer |
| `engine/tests/test_packliste.py:648` | Prüfung `k["knopf0"] == "Alle aufklappen"` |
| `engine/tests/test_pwa.py:206–272` (`test_reise_stand_im_browser`) | Stub-Server: `api/stand` antwortet ab Stand 2 erst nach `time.sleep(1)` (#321); fünf Prüfungen auf Fußzeile, Hinweis, Änderungsliste |
| `engine/tests/stand_browser.mjs` | Ablauf mit `waitForFunction`/`waitForSelector` (15 s / 30 s). Mögliche Stellen ohne Wartepunkt: `ergebnis.listeSichtbar`/`liste` direkt nach dem Klick auf `[data-stand-liste]`; `ergebnis.apiStand` als eigener Abruf (1 s Verzögerung); `#neu` nach `reload` (15 s) |
| `engine/tests/seiten_browser.mjs:115–133` | Bausteinseite hell/dunkel bei 390/1200; nur mit `RH_BILDER` Vollseiten-Screenshot (bis 32000 px Höhe), Zeile 130 — Fundstelle von #537 |
| `.github/workflows/tests.yml:138` | `RH_BILDER` ist nur in der CI gesetzt; lokal/auf dem Server läuft der Screenshot nie |
| `engine/tests/seiten_brett.mjs:76`, `seiten_packliste.mjs:114,184` | weitere Vollseiten-Screenshots unter `RH_BILDER` (gleiches Risiko, bisher nicht gemeldet) |
| `engine/tests/test_seite.py:29–40,126,155` | ruft `seiten_browser.mjs` auf, legt den Bildordner an |

## Existing Patterns

- `#369` (`docs/context/fix-369-legende-flake.md`): Wartebedingung per `waitForFunction` mit Zeitgrenze statt fester Pause; bei Zeitüberschreitung weiter, damit die Prüfung die echte Lage zeigt.
- `#457`: Reihenfolge deterministisch statt knapper Zeitgrenzen.
- `seiten_packliste.mjs:33` hat bereits den Helfer `warte(p, f, ...a)` (`waitForFunction`, 5 s).
- Feste Pausen im Packliste-Skript: Z. 129 (400 ms, #503 gewollt), Z. 153 (300 ms nach Nachreichen).

## Dependencies

- Upstream: Playwright (Chromium, webkit) unter `PLAYWRIGHT`, Node; Vorlage und Rückmeldedienst (`rm.Dienst`).
- Downstream: Pflichtprüfungen `tests (leer)`/`tests (instanz)` in der CI; Bilder der Bausteinseite als CI-Artefakt zur Durchsicht.

## Existing Specs

- Keine eigene Spec für Testhilfen; Verhalten des Knopfs „Alle aufklappen“ aus #511, Fußzeile/Reise-Stand aus #223/#228/#229/#321.

## Risks & Considerations

- Nur Testskripte ändern, Seite und Vorlage bleiben gleich (die Seite verhält sich richtig; der Knopftext erscheint einen Takt später). Prüfen in der Analyse, ob der leere Knopf für Nutzer sichtbar ist — falls ja, wäre `stand()` sofort beim Erzeugen aufzurufen eine kleine Verbesserung der Vorlage (dann Produktänderung, gesondert abwägen).
- Für `test_reise_stand_im_browser` ist die genaue Fehlermeldung nicht festgehalten („Stub-Server wartet 1 s“); in der Analyse unter Last reproduzieren (z. B. CPU-Last parallel, mehrfach webkit) und die tatsächlich scheiternde Prüfung ermitteln, statt zu raten.
- #537: Ursache vermutlich Ressourcen des CI-Runners bei sehr hohen Vollseiten-Bildern; robust machen per Wiederholversuch (z. B. bis 3 Versuche mit kurzer Pause) und ggf. kleinerer Höchsthöhe. Der Screenshot ist nur Beiwerk zur Durchsicht: ein endgültiges Scheitern sollte als Warnung gelten statt den Test rot zu machen — abwägen, da sonst fehlende Bilder unbemerkt bleiben.
- Erfolgsnachweis: mehrere Gesamtläufe mit `-n 3` grün (Server), CI-Lauf mit `RH_BILDER` grün.

## Analysis

### Type
Bug (wackelige Tests; die Seite selbst verhält sich richtig)

### Reproduktion (13.11.2026, Server, 4 CPU)
Beide betroffenen Tests (chromium und webkit) mit `-n 4`, zwei Prozesse Dauerlast daneben, elf Durchläufe: drei rot.
- `test_reise_stand_im_browser[webkit]`, ein Mal: `e["hinweis"] == "Neue Version des Handbuchs bereit. Aktualisieren"` statt „Neu: Reise-Stand 2.“
- `test_packliste_im_browser[webkit]`, zwei Mal (Fehlerzeile durch Filter nicht erfasst; Meldung aus #550: `knopf0 == ""`).

### Ursachen
1. **Reise-Stand (#550, erster Test):** Nach `reload` mit Stand 2 laufen zwei Wege um die Wette. (a) Der Service Worker findet eine neue `sw.js`, installiert sie und zeigt `#neu` mit dem allgemeinen Text „Neue Version des Handbuchs bereit.“ (`zeigen()` in der Vorlage). (b) `api/stand` antwortet nach 1 s (Stub, #321), `neuerStandHinweis()` setzt dann „Neu: Reise-Stand 2.“ (überschreibt, weil `RS_NEU` noch 0 ist). `stand_browser.mjs` wartet nur auf `#neu:not([hidden])` und liest sofort. Ist (a) zuerst da, liest der Test den Zwischenstand. Endzustand der Seite ist richtig.
2. **Packliste (#550, zweiter Test):** `plAlleKnopf()` erzeugt den Knopf leer, den Text setzt `stand()` erst per `setTimeout`. Nach dem Haken an „Wanderschuhe“ wird die Ansicht neu gezeichnet; der Test wartet auf das Zuklappen der Gruppe und liest den Knopf im selben Takt, bevor der Zeitgeber lief. Für Nutzer höchstens ein einzelnes Bild lang leer, nicht bemerkbar; Vorlage bleibt unverändert.
3. **Bausteinseite (#537):** `Page.captureScreenshot` scheitert gelegentlich im CI-Runner bei Vollseitenbildern bis 32000 px Höhe (Ressourcen des Runners). Nur mit `RH_BILDER` (nur CI); die Bilder sind Beiwerk zur Durchsicht, kein Test prüft sie.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/tests/stand_browser.mjs` | MODIFY | Nach `reload` per `waitForFunction` auf den Text „Neu: Reise-Stand“ in `#neu` warten (15 s; bei Zeitüberschreitung weiterlesen, damit die Prüfung die echte Lage zeigt, Muster #369) |
| `engine/tests/seiten_packliste.mjs` | MODIFY | Vor dem Lesen von `knopf0` mit `warte()` auf nicht leeren Text von `.pack-alle` warten; ebenso vor dem Lesen nach `reload` (`knopf`); Vollseitenbilder über den neuen Helfer |
| `engine/tests/bild.mjs` | CREATE | Helfer `bild(page, optionen)`: Screenshot mit bis zu 3 Versuchen und kurzer Pause; scheitert er endgültig, gibt er `false` zurück statt zu werfen |
| `engine/tests/seiten_browser.mjs` | MODIFY | Bausteinseite über den Helfer; fehlende Bilder als Liste `bilderFehlen` in der Ausgabe |
| `engine/tests/seiten_brett.mjs` | MODIFY | Vollseitenbilder über den Helfer |
| `engine/tests/test_seite.py` | MODIFY | Fehlende Bilder als `warnings.warn` (sichtbar in der Warnungsübersicht des CI-Logs), nicht rot |
| `engine/tests/test_bild_helfer.py` o. ä. | CREATE | Test des Helfers: wiederholt bei Fehler, gibt nach dem dritten Fehlversuch `false` zurück (mit gestellter Seite, ohne Browser) |

### Scope Assessment
- Files: 6–7, nur Tests
- Estimated LoC: +60/-10
- Risk Level: LOW (Vorlage, Engine und Betrieb unverändert)

### Technical Approach
Wartebedingung statt Zeitpunkt (wie #369, #457): auf den fachlichen Zielzustand warten, nicht auf ein Zwischensignal. Für die Bilder Wiederholversuch und, als letztes Mittel, Warnung statt roter Pflichtprüfung, weil die Bilder nur zur Durchsicht dienen und ein roter Lauf die Auslieferung für etwas Nebensächliches anhält. Die Höchsthöhe von 32000 px bleibt (kleiner würde Bausteine abschneiden); erst wenn die Warnung trotz Wiederholung wiederkehrt, Höhe senken (im Issue vermerken).

Erfolgsnachweis: der Lastaufbau oben (11 Durchläufe, `-n 4`, Dauerlast) ohne Rot; danach mehrere Gesamtläufe `-n 3`; CI mit `RH_BILDER` grün.

### Dependencies
Playwright (chromium, webkit), Node; CI-Job mit `RH_BILDER` und Artefakt `bausteine`.

### Open Questions
- keine (alle Punkte technisch, vom Tech Lead entschieden)

## Hinweise für die Umsetzung (Phase 5, 13.11.2026)

- Schnittstelle des Helfers laut Tests: `export async function bild(page, optionen, {pause = 500} = {})` in `engine/tests/bild.mjs`; `test_seite.py` bekommt die Funktion `bilder_fehlen_melden(e)`, die der Browser-Rundgang mit seiner JSON-Ausgabe aufruft.
- Der Arbeitsordner dieser Sitzung hat keine eigene Python-Umgebung (`engine/.venv` fehlt); die RED-Läufe nutzten die Umgebung eines anderen Arbeitsordners derselben Software. Für die Umsetzung eine eigene anlegen oder ebenso verfahren.
