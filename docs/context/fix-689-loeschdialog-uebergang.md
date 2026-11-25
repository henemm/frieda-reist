# Kontext: fix-689-loeschdialog-uebergang

## Wunsch

`test_bilder_eigen.py::test_browser_hochladen_hinweis_nennung_und_loeschen[webkit]` scheiterte einmal in der CI (Lauf 45397237767, Versuch 1, `tests (instanz)`): Der Dialog „Foto entfernen?“ stand nach dem ersten Klick nicht da, nach dem zweiten schon (#689). Auftrag des Product Owners: nach #654 und #656 auch #689. Ursache klären, beheben, Prüfung nicht abschwächen.

## Betroffene Dateien

| Datei | Bedeutung |
|---|---|
| `engine/vorlage.html` (:1721-1780 `grossAnsicht`, :1755 Knopf „Foto entfernen“, :1762-1766 `destroy`, :1773 `openingAnimationEnd`) | Hier geht der Klick verloren; Ort der Korrektur |
| `engine/vorlage.html` (:1677 `bildEntfernenFragen`, :1628 `blatt`) | Dialog mit der Zusage, öffnet sofort mit `showModal()`; keine Änderung nötig |
| `engine/vendor/photoswipe-5.4.4.esm.min.js` | Fremdbibliothek, bleibt unverändert |
| `engine/tests/seiten_bilder_eigen.mjs` (:70-99 `grossAuf`, `frage`, `loeschen`) | `grossAuf` wartet auf `pswp--open` (steht sofort) und fest 500 ms; `frage` verschluckt das Zeitlimit (3 s) |
| `engine/tests/test_bilder_eigen.py` (:1454-1484) | Prüfungen zum Ablauf (AC-14 von #582), hier kommt der neue Fall dazu |
| `engine/tests/seiten_bilder_p2.mjs` (:118-123 `offen`, `geschlossen`), `test_seite_bilder.py` | Vorbild: `offen` wartet, bis der Fokus in der Großansicht liegt, also auf das Ende des Übergangs; muss grün bleiben |
| `docs/funktionen/bilder.md` (:47-50), `docs/design.md` (:88) | Nutzersicht beschreibt das Soll schon; voraussichtlich keine Änderung |

## Befunde

1. **Ursache nachgestellt, anders als im Issue vermutet.** Klick auf „Foto entfernen“, solange die Großansicht noch öffnet, geht verloren (Chromium, Klick 0 bis 300 ms nach Erscheinen des Knopfs: Frage auch nach 5 s nicht da, Großansicht offen; ab 600 ms da). Skript und Ausgabe: `docs/artifacts/fix-689-loeschdialog-uebergang/`. Es ist ein Fehler der Seite. Eine längere Wartezeit (Vorschlag im Issue) hilft nicht.
2. **Weg im Code (Korrektur der Vorprüfung).** `pswp.destroy()` setzt, wenn noch nicht geschlossen wird, `showHideAnimationType = "none"` und ruft `close()`. `PhotoSwipe.close()` tut nichts, solange `opener.isOpen` falsch ist; das ist während des ganzen Übergangs so. Der Wächter in `opener.close()` (`isOpening`) wird gar nicht erst erreicht. `isDestroying` bleibt falsch, ein zweiter Aufruf wirkt also.
3. **Der Knopf ist dabei schon sichtbar:** `pswp--ui-visible` wird beim Beginn des Übergangs gesetzt, nicht am Ende.
4. **Nebenfolgen des verlorenen Klicks (aus dem Code, nicht gemessen):**
   - `danach` bleibt gesetzt: Schließt man die Großansicht später mit Kreuz, Escape oder Wischen, kommt die Frage unerwartet.
   - `danach` hält das Bild vom Zeitpunkt des Klicks. Hat man inzwischen weitergeblättert, fragt der Dialog nach dem früheren Bild, ohne es zu zeigen.
   - `showHideAnimationType` bleibt auf „none“: Das spätere Schließen hat keinen Übergang mehr.
5. **Kreuz, Escape, Wischen nach unten während des Öffnens** laufen ebenfalls über `PhotoSwipe.close()` und dürften dort wirkungslos sein (aus dem Code, nicht gemessen). Das ist Verhalten der Bibliothek, kein Teil des Issues.
6. **Reihenfolge am Ende des Übergangs:** Die Bibliothek setzt `isOpen`, meldet `openingAnimationEnd`, danach `initialZoomInEnd`, und arbeitet dann in derselben Funktion weiter. Schließen mitten in dieser Meldung ist möglich, aber nicht geprüft; ein Aufschub (`setTimeout`) wäre vorsichtiger.
7. **Reduzierte Bewegung:** Der Kommentar in der Vorlage sagt, PhotoSwipe schalte Übergänge dann selbst ab. Für das Fenster des verlorenen Klicks nicht gemessen.
8. **CI-Lauf nicht bewiesen:** Das Protokoll nennt den Zustand der Großansicht nicht; ein nur spät öffnender Dialog ergäbe dieselben Werte. Das Bild (erster Klick wirkungslos, zweiter wirkt) passt zu Befund 1. WebKit ist lokal nicht installiert, dort nicht gemessen; die CI läuft mit beiden Browsern.

## Bestehende Muster

- Auf Zustände warten statt auf feste Zeiten (#154, #599, #654); Grund des Scheiterns sichtbar machen.
- Wackelige Tests mit eingespieltem Fehler oder Verzögerung nachweisen, ein echter Fehler bleibt rot (#654, #656).
- `openingAnimationEnd` wird in `grossAnsicht` schon für den Fokus genutzt.

## Abhängigkeiten

- Nutzt: PhotoSwipe 5.4.4 (Vendor), `bildEntfernenFragen`, `darfFotoEntfernen`.
- Wird genutzt von: jeder Reise mit Bildern; `grossAnsicht` ruft der Klick auf `[data-bild]`. Der Knopf „Foto entfernen“ erscheint nur bei eigenen Fotos. Auf der Bausteinseite wird `bildEntfernenFragen` auch ohne Großansicht aufgerufen.

## Specs

- `docs/specs/oberflaeche/bilder-582-eigene-fotos.md` AC-14: „Foto entfernen“ in der Großansicht öffnet den Dialog; „Behalten“ sendet nichts, erst „Entfernen“ löscht (Chromium und WebKit).
- `docs/specs/betrieb/wackelige-browsertests-654.md` und `docs/specs/fast/fix-656-vorab-ordner-faden.md`: Vorgehen bei den beiden anderen Tests desselben Auftrags.

## Risiken und offene Punkte für die Analyse

- Löschen ist endgültig: Die Frage darf nur kommen, wenn gerade „Foto entfernen“ gedrückt wurde, und muss das Bild von diesem Klick meinen. Blättern oder Schließen vor dem Ende des Übergangs muss geregelt sein.
- Mehrfachklick während des Übergangs darf nur einen Dialog öffnen.
- Fokus nach dem Schließen: Der Auslöser bekommt den Fokus, danach öffnet der Dialog (bestehendes Verhalten, bleibt).
- Alternative zum Merken des Klicks: Knopf bis zum Ende des Übergangs sperren. Dann müsste man noch einmal tippen; das Merken entspricht dem, was man erwartet. In der Analyse entscheiden.
- Der Test soll den Klick mitten im Übergang gezielt herstellen (vorher rot) und nicht von der Geschwindigkeit des Rechners abhängen, etwa durch einen verlängerten oder angehaltenen Übergang.
- `frage()` soll beim ersten Öffnen nicht mehr verschlucken; der Ablauf für „Mo“ (kein Knopf) muss davon unberührt bleiben.
- Offen und zu messen: Befunde 4, 5 und 7; Verhalten in WebKit (nur CI).
- Nicht Teil des Tickets, sofern die Analyse nichts anderes zeigt: Kreuz, Escape und Wischen während des Öffnens.

## Analysis

### Type
Bug (Seite und Test). Messung: `docs/artifacts/fix-689-loeschdialog-uebergang/messung689.py` (Aufruf mit Weg und Fallnummer), Ausgabe `messung689.txt`, Chromium. Die Lösungswege waren nur in der gebauten Seite eingesetzt.

### Gemessen (ergänzt die Befunde 4, 5, 7)
- **Befund 4 bestätigt, und schwerer:** Klick im Öffnen, später weiterblättern, Escape: Die Frage kommt unerwartet und löscht BI-91, gezeigt war BI-90. Ohne Blättern kommt die Frage beim Schließen ebenfalls unerwartet. Das ist ein Risiko für falsches Löschen.
- **Befund 5 bestätigt:** Escape und Kreuz während des Öffnens wirken nicht (Verhalten der Bibliothek, nicht Teil des Issues).
- **Befund 7 geklärt:** Bei reduzierter Bewegung ist `isOpen` sofort wahr, kein Fenster. Die Meldung `openingAnimationEnd` kommt dann synchron in `init()`, vor dem Anhängen des Hörers nach `init()`.
- **Ende des Übergangs** rund 430 ms nach `init` (rund 50 ms Decode des Vorschaubilds, höchstens 250, dann 333 ms); unabhängig davon, ob das große Bild lädt (Fall 10).
- **Blättern mit der Pfeiltaste** wirkt im Öffnen nicht; **mit dem Pfeilknopf** gibt es einen eigenen, älteren Fehler (leere Ansicht, Zähler und „Foto entfernen“ bleiben beim vorigen Bild): #706, nicht Teil dieses Tickets.
- Kein weiterer Aufrufer von `pswp.destroy`; kein Test prüft den Quelltext der Stelle, kein Größenbudget der Vorlage. Aufrufer von `grossAnsicht`: Klick auf `[data-bild]` und die Bausteinseite. Ein Hash-Wechsel schließt die Großansicht nicht.

### Lösungswege im Vergleich (Chromium, dieselben Fälle)
| Fall | heute | sofort (in der Meldung schließen) | aufschub (je Klick ein Hörer, setTimeout) | sperre (Klick ignorieren) | **plan (ein Hörer, Blättern verwirft)** |
|---|---|---|---|---|---|
| 1 Klick im Öffnen: Frage | nein | ja | ja | nein | **ja**, Fokus im Dialog |
| 2 Dreifachklick: Dialoge | 0 | 1 (`destroy` ohne `closingAnimationStart`, hartes Ende) | 1 (ebenso) | 0 | **1, sauberes Schließen** |
| 3/4 später schließen oder blättern | unerwartete Frage, falsches Bild | Frage sofort, richtiges Bild | Frage sofort, richtiges Bild | keine Frage | **Frage sofort, richtiges Bild** |
| 5 Klick, dann Pfeilknopf im Öffnen | – (#706) | Frage, löscht BI-91 | Frage, löscht BI-91 | keine Frage | **keine Frage (verworfen)** |
| 8 Klick, dann Escape | nichts | Frage | Frage | nichts | **Frage** |
| 9 reduzierte Bewegung | Frage | Frage | Frage | Frage | **Frage** |
| 11 Klick nach dem Öffnen | Frage | Frage | Frage | Frage | **Frage** |

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/vorlage.html` (`grossAnsicht`) | MODIFY | Klick merken; `change` verwirft ihn; ein Hörer auf `openingAnimationEnd` schließt nach der Meldung |
| `engine/tests/seiten_bilder_eigen.mjs` | MODIFY | `grossAuf` wartet auf das Ende des Öffnens statt 500 ms; `frage` verschluckt beim ersten Öffnen nichts; Ablauf mit Klick mitten im Öffnen |
| `engine/tests/test_bilder_eigen.py` | MODIFY | Prüfungen dazu, zweites eigenes Foto nur für die neuen Abläufe |

### Scope Assessment
- Files: 3 (dazu Spec, Nachweise)
- Estimated LoC: rund +70/-10
- Risk Level: LOW bis MEDIUM (endgültiges Löschen hängt daran; Fenster nur rund 0,4 s)

### Technical Approach
- `danach` bleibt das Gemerkte. Klick: `danach` setzen, bei `pswp.opener.isOpen` wie bisher `pswp.destroy()`.
- Vor `init()` anhängen, vor dem Hörer der Unterschrift: `change` setzt `danach = null`; `openingAnimationEnd` ruft `setTimeout(() => { if (danach && !pswp.isDestroying) pswp.destroy(); })`.
- **Test ohne Rechnertempo:** Im Test die Dauer in der ausgelieferten Bibliothek per `route` verlängern (`showAnimationDuration:333` → z. B. 3000; die Zeichenkette kommt genau einmal vor, der Test prüft den Treffer), dann auf `pswp--ui-visible` warten und klicken; Zustand `opener.isOpen === false` im selben `evaluate` festhalten, sonst scheitert der Test mit Grund. Heute rot: keine Frage.
- Testfälle: Klick im Öffnen → genau ein Dialog und Großansicht zu; Dreifachklick → ein Dialog; „Behalten“ im selben Ablauf sendet nichts, „Entfernen“ löscht das Bild vom Klick; nach „Klick im Öffnen“ ohne Blättern keine zweite Frage. WebKit läuft nur in der CI.

### Dependencies
PhotoSwipe 5.4.4 (unverändert; genutzt werden `opener.isOpen`, `isDestroying`, `openingAnimationEnd`, `change`).

### Open Questions
- [x] Merken oder sperren: merken (Tipp wirkt, wie man es erwartet; rund 0,4 s später).
- [x] #706 getrennt.
- [ ] WebKit: erst in der CI zu sehen.

### Bewertung des Lösungswegs (unabhängige Prüfung) und Korrekturen
- Empfehlung: Weg „plan“. Die Tabelle stimmt mit `messung689.txt` überein; Präzisierungen: Zeile 3/4 „heute“: unerwartete Frage in beiden Fällen, falsches Bild nur in Fall 4. Zeile 5 meint den Pfeilknopf; mit der Pfeiltaste blättert im Öffnen nichts, „plan“ fragt dann nach dem gezeigten Bild (BI-91). „Sauberes Schließen“ in Zeile 2 heißt nur: ein `destroy()` über `close()`, kein zweites hinterher; sichtbar ist kein Übergang (`showHideAnimationType` „none“).
- **Seitenfehler „reading 'data'“ in der Messung:** gehört zu #706. Läufe ohne Blättern hatten keinen Fehler (erster Lauf von „null“ mit einem Foto: `Fehler: []`); die Zahl passt zu den Pfeilknopf-Fällen (2 bei Fall 5, 3 mit Fall 12). Aus den Zahlen geschlossen, nicht je Fall gemessen.
- **`change` ohne Blättern:** Die Bibliothek meldet es an drei Stellen: in `init()` (vor jedem Klick), bei echtem Indexwechsel, in `refreshSlideContent` (die Vorlage ruft es nicht auf). Ein Klick wird also nur durch echtes Blättern verworfen. Aus dem Code, WebKit nicht gemessen.
- Der Wächter `!pswp.isDestroying` ist nötig: `destroy()` baut sonst während des Schließens sofort ab.
- **Für die Spec:** Nebenbei bekannt, nicht Teil des Tickets: Bei reduzierter Bewegung kommt `openingAnimationEnd` vor dem Fokus-Hörer (nach `init()` angehängt); aus dem Code, Auswirkung auf den Fokus nicht gemessen.
- Reihenfolge: roter Test (verlängerter Übergang), `grossAuf` und `frage` auf Zustände, Seite, Zusatzfälle, CI mit WebKit.
