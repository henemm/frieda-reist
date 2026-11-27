# Kontext: fix-706-pfeil-im-oeffnen

## Anfrage

Issue #706 (Besitzer): Drückt man in der Großansicht den Pfeilknopf „weiter“, solange sie noch öffnet (rund 0,4 s), bleibt die
Ansicht leer, der Zähler steht auf „1 / 2“, in der Konsole `TypeError … reading 'data'` aus den `change`-Hörern von
`grossAnsicht`. „Foto entfernen“ gehört weiter zum vorigen Bild. Nachtrag aus #689 (F001): „Pfeil, dann Klick“ löscht das Bild
des stehengebliebenen Knopfs, obwohl `currIndex` schon weiter ist. Gewünscht: Test „Pfeil, dann Klick“ ergänzen und die
Ausnahme in `test_gross_klick_im_oeffnen_dann_blaettern_verwirft` entfernen.

## Ursache (im Code belegt)

PhotoSwipe 5.4.4 (`engine/vendor/photoswipe-5.4.4.esm.min.js`) füllt beim Öffnen nur den mittleren Platz
(`itemHolders[1]`). Die Nachbarplätze bleiben `display:none` ohne Slide und werden erst im eigenen Hörer auf
`openingAnimationEnd` gefüllt (`setContent(t[0], currIndex-1)`, `setContent(t[2], currIndex+1)`).

Der Pfeilknopf ruft `next()` → `goTo()` → `mainScroll.moveIndexBy()` → `updateCurrItem()`, ohne auf `opener.isOpen` zu
achten. `updateCurrItem` schiebt den leeren rechten Platz in die Mitte: `currSlide` ist `undefined`, die `change`-Hörer der
Vorlage (`engine/vorlage.html`, Zähler und Unterschrift in `grossAnsicht`) brechen ab, bevor sie Zähler und Knopf
erneuern. Am Ende des Öffnens füllt PhotoSwipe nur die Nachbarn des neuen Index, die Mitte bleibt leer.

Pfeiltaste und Wischen sind nicht betroffen: PhotoSwipe bindet die Tasten erst bei `bindEvents` (Ende des Öffnens), und
`onPointerDown` verwirft Zeiger, solange `opener.isOpen` falsch ist. Nur der Pfeilknopf (`onClick: "next"/"prev"`) wirkt
schon im Öffnen.

## Betroffene Dateien

- `engine/vorlage.html`, Organismus `grossAnsicht` (Zeile ~1721–1790): Ort der Behebung.
- `engine/tests/seiten_bilder_eigen.mjs`, Art `oeffnen` (Zeile ~169–275): Abläufe im Browser, Ablauf `blaettern`.
- `engine/tests/test_bilder_eigen.py`, Fixture `oeffnen` und `test_gross_*` (Zeile ~1487–1575): Auswertung, Ausnahme für #706.

## Bestehende Muster

- #689: Klick auf „Foto entfernen“ im Öffnen wird in `danach` gemerkt; `change` verwirft ihn; Escape wirkt im Öffnen nicht
  (AC-7), die Frage kommt am Ende des Öffnens.
- Tests: Öffnen per Antwort auf die Bibliothek auf 3 s verlängert (`DAUER`/`LANG`), je Ablauf eigene Seite, Chromium und WebKit.

## Abhängigkeiten / Auswirkungen

- Behebung nur in der Vorlage (kein Eingriff in die Fremdbibliothek, `engine/vendor/` bleibt unverändert).
- #689 AC-4 („Klick, dann Pfeil verwirft den Klick“) setzt voraus, dass der Pfeil im Öffnen blättert. Wirkt der Pfeil im
  Öffnen nicht mehr, verhält er sich wie Escape (AC-7): Der Klick bleibt, die Frage kommt am Ende des Öffnens zum gezeigten
  Foto. Der Test zu AC-4 wird entsprechend umgestellt; der Zweck (die Frage meint nie ein anderes Foto als das gezeigte)
  bleibt.

## Risiken

- Nach dem Öffnen muss Blättern unverändert gehen (Knopf, Taste, Wischen) — Test.
- Ohne Übergang (reduzierte Bewegung) ist `isOpen` sofort wahr — nichts ändert sich.
- Wackelige Zeitfenster in WebKit (#705, #708): Abläufe warten auf Zustände, nicht auf feste Zeiten, wo möglich.

## Analysis

**Type:** Bug. Ursache im Code der Bibliothek belegt (siehe oben), Analyse ohne eigene Bug-Intake-Agenten, weil Ursache,
Auslöser und betroffene Stelle eindeutig und in einer Funktion liegen.

### Affected Files

| Datei | Änderung | Grund |
|---|---|---|
| `engine/vorlage.html` | MODIFY (~5 LoC) | `grossAnsicht`: Blättern per `goTo` (Pfeilknöpfe, `next`/`prev`) im Öffnen ignorieren |
| `engine/tests/seiten_bilder_eigen.mjs` | MODIFY (~25 LoC) | Ablauf `blaettern` auf neues Verhalten, neue Abläufe „Pfeil im Öffnen“ und „Pfeil, dann Klick“ |
| `engine/tests/test_bilder_eigen.py` | MODIFY (~30 LoC) | Ausnahme für #706 entfernen, AC-4 umstellen, neue Tests |

### Varianten

| Variante | Änderung | Verhalten | Risiko |
|---|---|---|---|
| A: `goTo` im Öffnen ignorieren | 3–5 Zeilen Vorlage | Pfeilknopf wirkt im Öffnen nicht, wie Pfeiltaste, Wischen und Escape | gering; ein Druck in 0,4 s geht verloren |
| B: Blättern bis zum Ende des Öffnens aufschieben | ~10 Zeilen, Zustand | Pfeil wirkt nach dem Öffnen | Wechselwirkung mit gemerktem Klick (#689), mehr Zustand |
| C: `change`-Hörer gegen leeres `currSlide` absichern | 2 Zeilen | Ansicht bleibt trotzdem leer | behebt nur den Folgefehler |

**Empfehlung: A.** Einheitlich mit Taste und Wischen (beide wirken im Öffnen nicht), kleinster Eingriff, keine Änderung an der
Fremdbibliothek. Umsetzung: nach `new PhotoSwipe(...)` `goTo` umhüllen, das nur bei `pswp.opener.isOpen` weiterreicht.
`next`/`prev` laufen über `goTo`, also auch die Pfeilknöpfe.

### Folge für #689

AC-4 („Klick, dann Pfeil verwirft den Klick“) hatte den Pfeil im Öffnen als Blättern angenommen. Mit A bleibt der Klick
stehen, die Frage kommt am Ende des Öffnens und meint das gezeigte Foto (wie Escape, AC-7). Ziel von AC-4 („nie ein anderes
Foto als das gezeigte“) bleibt erfüllt; der Hörer `change → danach = null` bleibt für Blättern nach dem Öffnen nötig.

### Scope / Risk

3 Dateien, ~70 LoC (davon ~65 Tests). Risiko niedrig: eine Funktion der Oberfläche, Löschweg unverändert, Tests in
Chromium und WebKit.

### Open Questions

Keine. (Ob der Pfeil im Öffnen ignoriert oder aufgeschoben wird, lässt das Issue offen; A ist einheitlich mit der Taste.)
