---
entity_id: loeschfrage-grossansicht-689
type: bugfix
created: 2026-11-25
updated: 2026-11-25
status: draft
workflow: fix-689-loeschdialog-uebergang
---

# Löschfrage in der Großansicht geht beim Öffnen nicht mehr verloren (#689)

Grundlage: `docs/context/fix-689-loeschdialog-uebergang.md` (Kontext, Befunde 1 bis 8, Analyse, Bewertung des Lösungswegs). Messung: `docs/artifacts/fix-689-loeschdialog-uebergang/messung689.py` und `messung689.txt` (Chromium). Aufbau wie `docs/specs/betrieb/wackelige-browsertests-654.md`.

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es ändert sich nur der Umgang eines Klicks innerhalb der vorhandenen Großansicht (`grossAnsicht`) und der Test dazu. Keine neue Grundform, kein neuer Baustein, keine Änderung an Daten, Schnittstellen oder Vendor-Code; der Kern aus ADR-0001 ist nicht berührt.

## Purpose

Wer in der Großansicht „Foto entfernen“ antippt, während sich die Großansicht noch öffnet (rund 0,4 s), bekommt heute keine Frage: Der Klick geht verloren, und die Folgen sind gefährlich. Später kommt die Frage unerwartet, und nach Weiterblättern meint sie ein anderes Bild als das gezeigte; wer dann „Entfernen“ bestätigt, löscht das falsche Foto. Der Klick soll stattdessen gemerkt werden und die Frage kommen, sobald das Öffnen beendet ist, für genau das Bild vom Klick. Blättert man vorher wirklich weiter, wird der Klick verworfen. Auslöser war der einmalige Ausfall von `test_browser_hochladen_hinweis_nennung_und_loeschen[webkit]` in der CI (Lauf 45397237767, Job `tests (instanz)`); der Test soll das Fenster gezielt herstellen, statt auf Rechnertempo zu hoffen.

**Ehrlichkeit über die Reichweite:** Dass der CI-Ausfall genau dieser Fehler war, ist nicht bewiesen (Befund 8): Das Protokoll nennt den Zustand der Großansicht nicht, und WebKit ist lokal nicht installiert. Bewiesen (Chromium) ist der Fehler der Seite, der zum selben Bild passt (erster Klick wirkungslos, zweiter wirkt). Die Ursache ist ein nachgestellter Fehler der Seite, keine zu kurze Wartezeit im Test; der Vorschlag im Issue (15 s warten) allein hülfe nicht (Klick im Öffnen: Frage auch nach 5 s nicht da). Das wird im Pull Request und im Issue so gesagt.

## Ursachen (Befunde, nachgestellt oder gelesen)

1. Klick auf „Foto entfernen“ im Öffnen geht verloren (Chromium, 0 bis 300 ms nach Erscheinen des Knopfs: keine Frage, Großansicht bleibt offen). Grund aus dem Code: `pswp.destroy()` ruft `close()`, und `PhotoSwipe.close()` tut nichts, solange `opener.isOpen` falsch ist, also während des ganzen Übergangs. Der Knopf ist schon sichtbar, weil `pswp--ui-visible` zu Beginn des Übergangs gesetzt wird.
2. Folgen (gemessen, `messung689.txt`, Weg „null“): Klick im Öffnen, später Escape: die Frage kommt unerwartet (Fall 3). Klick im Öffnen, später weiterblättern, Escape: die Frage meint BI-91, gezeigt war zuletzt BI-90; mit „Entfernen“ wird BI-91 gelöscht (Fall 4). Der Dreifachklick im Öffnen ergibt null Dialoge (Fall 2).
3. Ende des Übergangs rund 430 ms nach `init`, unabhängig davon, ob das große Bild lädt (Fall 10).
4. Bei reduzierter Bewegung ist `isOpen` sofort wahr; der Klick wirkt sofort (Fall 9, Bestand).
5. Kreuz, Escape und Wischen während des Öffnens wirken nicht (Fälle 6 und 7): Verhalten der Bibliothek, nicht Teil des Tickets.
6. Blättern im Öffnen: Mit der Pfeiltaste blättert nichts; mit dem Pfeilknopf tritt ein eigener, älterer Fehler auf (leere Ansicht, Seitenfehler „reading 'data'“, Zähler und Knopf bleiben beim vorigen Bild): #706, getrennt.
7. Der CI-Lauf ist nicht bewiesen (siehe Purpose).

## Source

- **File:** `engine/vorlage.html`, `engine/tests/seiten_bilder_eigen.mjs`, `engine/tests/test_bilder_eigen.py`
- **Identifier:** `function grossAnsicht` (Vorlage, Klick-Hörer des Knopfs „Foto entfernen“, `destroy`-Hörer, `openingAnimationEnd`); `grossAuf`, `frage`, `loeschen` (Skript); `test_browser_hochladen_hinweis_nennung_und_loeschen` und neue Tests (Python)

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/vendor/photoswipe-5.4.4.esm.min.js` | Vendor, unverändert | genutzt werden `opener.isOpen`, `isDestroying`, `openingAnimationEnd`, `change`; die Dauer wird nur im Test per `route` verlängert |
| `bildEntfernenFragen`, `darfFotoEntfernen` (Vorlage) | Funktionen | der Dialog „Foto entfernen?“ mit der Zusage; öffnet sofort mit `showModal()`, keine Änderung |
| `docs/specs/oberflaeche/bilder-582-eigene-fotos.md`, AC-14 | Spec | „Foto entfernen“ in der Großansicht öffnet den Dialog; „Behalten“ sendet nichts, erst „Entfernen“ löscht; bleibt unverändert gültig |
| `docs/specs/betrieb/wackelige-browsertests-654.md`, `docs/specs/fast/fix-656-vorab-ordner-faden.md` | Muster | auf Zustände warten statt auf feste Zeiten, Grund des Scheiterns sichtbar machen, Nachweis unter eingespielter Verzögerung |
| `engine/tests/seiten_bilder_p2.mjs`, `test_seite_bilder.py` | Vorbild und Mitnutzer | `offen` wartet auf den Fokus in der Großansicht; müssen grün bleiben |
| `_Server`, `_node`, `eigen_eintragen` (Test) | Mitnutzer | Testserver und Hilfen aus `test_bilder_eigen.py`; das zweite Foto (BI-91) kommt über `eigen_eintragen` |
| Playwright (Chromium, WebKit) | extern | Chromium lokal, WebKit nur in der CI |
| #706 | Issue | Fehler des Pfeilknopfs im Öffnen; getrennt, hier nur sauber umgangen |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/vorlage.html` | MODIFY | `grossAnsicht`: Klick merken; `change` verwirft ihn; ein Hörer auf `openingAnimationEnd` schließt nach der Meldung |
| `engine/tests/seiten_bilder_eigen.mjs` | MODIFY | `grossAuf` wartet auf das Ende des Öffnens statt fest 500 ms; `frage` verschluckt nichts mehr; neuer Ablauf mit verlängertem Öffnen und Klick mitten im Öffnen |
| `engine/tests/test_bilder_eigen.py` | MODIFY | benannte Prüfungen zu den neuen Abläufen; zweites eigenes Foto BI-91 nur dafür |

Unterlagen unter `docs/` (Kontext, Messung, diese Spec, Nachweise) kommen dazu. Unverändert: Vendor, Engine, `engine/tests/seiten_bilder_p2.mjs`, `docs/funktionen/bilder.md` (beschreibt das Soll schon), `docs/design.md`, `betrieb/`, Gate-Konfiguration, `.github/workflows/tests.yml`.

### Estimated Changes

- Files: 3 (dazu Spec und Nachweise unter `docs/`)
- LoC: etwa +150/-15 (Seite rund +8/-2, der Rest Tests; die frühere Schätzung von +70 zählte die Einzeltests nicht mit). Grenze ±250.

### Out of Scope

- #706: Pfeilknopf im Öffnen (Seitenfehler „reading 'data'“).
- Kreuz, Escape und Wischen während des Öffnens (Bibliothek).
- Der Knopf bis zum Ende des Übergangs sperren (verworfen, siehe Implementation Details).
- Änderungen an der Bibliothek im Vendor.

## Implementation Details

**Lösungsweg „plan“ (entschieden):** Der Klick wird gemerkt, nicht gesperrt. In `grossAnsicht`:

1. Klick auf „Foto entfernen“: `danach` setzen (wie bisher). Ist `pswp.opener.isOpen` wahr (Übergang vorbei, reduzierte Bewegung, Klick später), wie bisher sofort `pswp.destroy()`. Sonst nichts weiter: der Klick bleibt gemerkt.
2. Vor `pswp.init()` und vor den `change`-Hörern der Elemente (Zähler, Unterschrift) angehängt: ein `change`-Hörer setzt `danach = null` (echtes Blättern verwirft den Klick); ein `openingAnimationEnd`-Hörer ruft `setTimeout(() => { if (danach && !pswp.isDestroying) pswp.destroy(); })`. Der Aufschub vermeidet das Schließen mitten in der Meldung der Bibliothek (Befund 6 im Kontext); der Wächter `!pswp.isDestroying` ist nötig, sonst baut `destroy()` während des Schließens sofort ab.
3. Der bestehende `destroy`-Hörer (Fokus an den Auslöser, dann `setTimeout(danach)`) bleibt unverändert.

**Warum „plan“:** Von fünf gemessenen Wegen (heute, sofort schließen, je Klick ein Hörer mit Aufschub, sperren, plan) erfüllt nur „plan“ alle Fälle: Ein Klick im Öffnen führt zu genau einer Frage mit Fokus im Dialog, Dreifachklick zu einem Dialog, Blättern verwirft den Klick (keine Frage zum falschen Bild), Escape ändert nichts an der Frage, reduzierte Bewegung und Klick nach dem Öffnen bleiben wie bisher. „Sperren“ ergäbe nie eine Frage; „sofort“ und „aufschub“ fragten nach dem Pfeilknopf im Öffnen trotzdem und löschten BI-91 (Fall 5).

**`change` ohne Blättern (aus dem Code):** Die Bibliothek meldet `change` in `init()` (vor jedem Klick), bei echtem Indexwechsel und in `refreshSlideContent` (von der Vorlage nicht aufgerufen). Ein Klick wird also nur durch echtes Blättern verworfen. Für WebKit nicht gemessen.

**Test ohne Rechnertempo.** Im Skript wird die Dauer der ausgelieferten Bibliothek nur im Test per `route` verlängert (`showAnimationDuration:333` auf z. B. 3000). Die Zeichenkette muss genau einmal vorkommen; der Test prüft den Treffer, sonst scheitert er mit Grund. Dann wird auf `pswp--ui-visible` gewartet, geklickt und im selben `evaluate` `opener.isOpen === false` festgehalten (sonst scheitert der Test mit Grund: das Fenster war nicht offen). So ist das Fenster rund 3 s groß statt 0,4 s und unabhängig vom Rechner.

**Skript.** `grossAuf` wartet auf `GROSS.opener.isOpen` (genau die Bedingung, unter der der Klick sofort wirkt) statt fest 500 ms und verschluckt das Zeitlimit nicht mehr. `frage` wartet bis 15 s (wie die übrigen Browsertests) und scheitert sonst mit einem Grund, der den Zustand nennt: Zahl der offenen Dialoge, Großansicht da oder nicht, `isOpen`. Das gilt für beide Aufrufe in `loeschen`. Der Ablauf für „Mo“ (kein Knopf, `d.knopf === false`) endet vor `frage` und bleibt unverändert. Die bestehenden Prüfungen (BI-90) bleiben unverändert scharf; die neuen Abläufe nutzen ein zweites eigenes Foto BI-91 am selben Ort (`eigen_eintragen`), das in der Messung zuerst gezeigt wird, damit „Foto vom Klick“ und „anderes Foto“ unterscheidbar sind.

**Aufbau der neuen Abläufe.** Eigene Art im Skript (`oeffnen`), ein Browserlauf je Browser für alle Abläufe, jeder Ablauf in eigener Seite; die benannten Tests lesen das gemeinsame Ergebnis (Fixture je Browser). So wächst die Laufzeit um einen Browserlauf, nicht um acht.

**Gegenprobe (AC-8).** Im Ablauf wird auf der geladenen Seite `bildEntfernenFragen` durch eine leere Funktion ersetzt (nur in dieser Seite), die Wartezeit von `frage` für diesen Ablauf verkürzt. Erwartet wird der Fehler mit Grund; ein stilles Weiterlaufen macht den Test rot.

**Blättern im Test (AC-4) und #706.** Geblättert wird im Öffnen mit dem Pfeilknopf (Klick im `evaluate`, wie in der Messung, Fall 5), denn die Pfeiltaste blättert im Öffnen nicht. Dieser Weg löst heute den Seitenfehler „Cannot read properties of undefined (reading 'data')“ aus #706 aus (Zuordnung aus den Zahlen der Messung geschlossen). Der Test lässt in diesem einen Ablauf genau diese Meldung zu, mit Verweis auf #706 im Kommentar; jeder andere Seitenfehler und dieselbe Meldung in einem anderen Ablauf machen ihn rot. Er verlangt sie nicht: Ist #706 behoben, bleibt er grün, und die Ausnahme wird dort entfernt (Vermerk in #706). Geprüft wird nur, was der Weg „plan“ garantiert: keine Frage, kein DELETE, auch nicht nach späterem Schließen. Der `change`-Hörer von „plan“ ist vor den werfenden Hörern angehängt; das Verwerfen läuft deshalb vor dem Fehler (Fall 5 „knopf“, Weg „plan“, gemessen).

## Test Plan

### Automated Tests (TDD RED)

Alle in `engine/tests/test_bilder_eigen.py` (Chromium und WebKit, soweit vorhanden), Abläufe in `engine/tests/seiten_bilder_eigen.mjs`. RED wird am heutigen Stand (Vorlage unverändert) gezeigt für die Fälle, die heute scheitern: Tests 1, 2, 3, 4a, 4b, 7 und 8.

- [ ] Test 1: GIVEN die Großansicht öffnet verlängert (3 s) und „Foto entfernen“ ist sichtbar / WHEN der Klick im Öffnen kommt (`isOpen === false` im selben `evaluate`) / THEN steht nach dem Ende des Öffnens genau ein Dialog „Foto entfernen?“, die Großansicht ist zu, der Fokus liegt im Dialog.
- [ ] Test 2: GIVEN wie Test 1 / WHEN dreimal im Öffnen geklickt wird / THEN genau ein Dialog, kein Seitenfehler.
- [ ] Test 3: GIVEN der Dialog aus Test 1 / WHEN „Behalten“ gedrückt wird, die Großansicht erneut geöffnet und geschlossen wird / THEN wurde nichts gesendet und es kommt keine zweite Frage; in einem zweiten Durchlauf löscht „Entfernen“ genau das Bild vom Klick (BI-91 bei Klick auf BI-91).
- [ ] Test 4a (Blättern verwirft): GIVEN Klick im Öffnen / WHEN vor dem Ende des Öffnens mit dem Pfeilknopf geblättert wird / THEN keine Frage, kein DELETE, auch nicht nach späterem Schließen (Escape nach dem Öffnen); Seitenfehler nur wie unter „Blättern im Test (AC-4) und #706“ beschrieben zugelassen.
- [ ] Test 4b (keine Frage zum falschen Bild): GIVEN Klick im Öffnen bei BI-91, zwei eigene Fotos / WHEN das Öffnen endet / THEN steht die Frage sofort da, die Großansicht ist zu, und „Entfernen“ löscht BI-91. Bleibt die Großansicht offen (heutiger Stand), blättert der Ablauf weiter, schließt mit Escape, bestätigt „Entfernen“ und hält zuletzt gezeigtes und gelöschtes Bild fest; der Test ist dann rot und nennt beide (heute: gezeigt BI-90, gelöscht BI-91).
- [ ] Test 5 (Wächter, heute grün; bestehender Test): GIVEN die Großansicht ist offen (Öffnen beendet) / WHEN „Foto entfernen“ geklickt wird / THEN öffnet sich der Dialog wie bisher (AC-14 aus #582): „Behalten“ sendet nichts, „Entfernen“ löscht.
- [ ] Test 6 (Wächter, heute grün): GIVEN reduzierte Bewegung / WHEN „Foto entfernen“ im Öffnen geklickt wird / THEN wirkt der Klick weiter sofort (Dialog da, Großansicht zu).
- [ ] Test 7: GIVEN Klick im Öffnen / WHEN sofort Escape gedrückt wird / THEN kommt die Frage (Escape wirkt im Öffnen nicht).
- [ ] Test 8 (Gegenprobe): GIVEN der Dialog erscheint beim ersten Öffnen nicht (`bildEntfernenFragen` in dieser Seite durch eine leere Funktion ersetzt) / WHEN `frage` wartet / THEN scheitert der Test mit klarem Grund statt zu verschlucken; der Ablauf für „Mo“ (kein Knopf) bleibt unverändert grün.
- [ ] Test 9 (Wächter der Verlängerung, heute grün; AC-12): GIVEN die Bibliothek wird für den Test ausgeliefert / WHEN die Zeichenkette `showAnimationDuration:333` nicht genau einmal vorkommt / THEN scheitert der Test mit Grund.

Bestehende Tests `test_bilder_eigen.py` und `test_seite_bilder.py` bleiben grün.

### Messungen

- RED-Läufe der Tests 1, 2, 3, 4a, 4b, 7 und 8 am heutigen Stand, Ausgabe im Nachweis unter `docs/artifacts/fix-689-loeschdialog-uebergang/`.
- Chromium lokal; WebKit in der CI.
- CI: der betroffene Test in mindestens 3 CI-Läufen grün, beide Browser (AC-10).

## Acceptance Criteria

- **AC-1:** Given die Großansicht öffnet noch (verlängert, `isOpen` falsch) / When „Foto entfernen“ geklickt wird / Then steht nach dem Öffnen genau ein Dialog, die Großansicht ist zu und der Fokus liegt im Dialog. Greift die Verlängerung nicht (Zeichenkette nicht genau einmal in der Bibliothek, Test 9) oder war das Fenster beim Klick schon zu, scheitert der Test mit Grund.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_klick_im_oeffnen_fragt_einmal`
- **AC-2:** Given wie AC-1 / When dreimal im Öffnen geklickt wird / Then genau ein Dialog und kein Seitenfehler.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_dreifachklick_im_oeffnen_ein_dialog`
- **AC-3:** Given der Dialog aus AC-1 / When „Behalten“ gedrückt und die Großansicht erneut geöffnet und geschlossen wird / Then wurde nichts gesendet und keine zweite Frage kommt; „Entfernen“ löscht genau das Bild vom Klick.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_behalten_und_entfernen_nach_klick_im_oeffnen`
- **AC-4:** Given Klick im Öffnen / When vor dem Ende mit dem Pfeilknopf geblättert wird / Then wird der Klick verworfen: keine Frage, kein DELETE, auch nicht nach späterem Schließen. Ein Seitenfehler „reading 'data'“ (#706) ist dort möglich und nur dort, nur mit genau diesem Text, zugelassen; jeder andere Seitenfehler macht den Test rot.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_klick_im_oeffnen_dann_blaettern_verwirft`
- **AC-4b:** Given Klick im Öffnen und zwei eigene Fotos / When das Öffnen endet / Then steht die Frage sofort da und meint das Foto vom Klick; nie kommt sie erst nach späterem Blättern und Schließen, wenn ein anderes Foto gezeigt wird.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_frage_meint_das_gezeigte_foto`
- **AC-5:** Given die Großansicht ist offen (Öffnen beendet) / When „Foto entfernen“ geklickt wird / Then wie bisher (AC-14 aus #582).
  Test: `engine/tests/test_bilder_eigen.py::test_browser_hochladen_hinweis_nennung_und_loeschen`
- **AC-6:** Given reduzierte Bewegung / When „Foto entfernen“ geklickt wird / Then wirkt der Klick weiter sofort.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_reduzierte_bewegung_klick_sofort`
- **AC-7:** Given Klick im Öffnen / When sofort Escape gedrückt wird / Then kommt die Frage.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_klick_im_oeffnen_dann_escape_fragt`
- **AC-8:** Given der Dialog fehlt beim ersten Öffnen / When `grossAuf` und `frage` laufen / Then ist das ein klarer Fehler mit Grund (Gegenprobe); der Ablauf für „Mo“ (kein Knopf) bleibt unverändert.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_fehlender_dialog_ist_klarer_fehler`
- **AC-9:** Given der heutige Stand (Vorlage unverändert) / When die Tests der AC-1 bis AC-4b, AC-7 und AC-8 laufen / Then sind sie rot (RED), einschließlich des Falls „später blättern und schließen: gezeigt BI-90, gelöscht BI-91“; nach der Änderung grün. AC-5, AC-6 und AC-12 sind Wächter und heute schon grün.
  Test: von Claude ausgeführt (RED-Lauf und GREEN-Lauf, Ausgabe im Nachweis)
- **AC-10:** Given der Stand vor der Auslieferung / When `test_bilder_eigen.py` und `test_seite_bilder.py` laufen / Then sind sie grün (Chromium lokal, WebKit in der CI), der betroffene Test in mindestens 3 CI-Läufen, dazu die Pflichtprüfungen `tests (leer)`, `tests (instanz)` und `gitleaks`.
  Test: von Claude ausgeführt (CI-Läufe, `gh run rerun` genügt)
- **AC-11:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then sind nur `engine/vorlage.html`, `engine/tests/seiten_bilder_eigen.mjs`, `engine/tests/test_bilder_eigen.py` und Unterlagen unter `docs/` geändert; `docs/funktionen/bilder.md` und der Vendor sind unverändert.
  Test: von Claude ausgeführt (Vergleich mit `main`)
- **AC-12:** Given die ausgelieferte Bibliothek / When die Verlängerung des Öffnens eingespielt wird / Then kommt `showAnimationDuration:333` genau einmal vor; sonst scheitert der Test mit Grund, statt das Fenster still zu verlieren.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_verlaengerung_greift`

## Risks

- **CI-Auslöser nicht bewiesen:** Der Umbau behebt einen nachgestellten Fehler der Seite; dass der CI-Ausfall dieser war, ist offen. Tritt er erneut auf, nennt die Meldung nun den Grund (`frage` verschluckt nichts mehr, `grossAuf` wartet auf Zustände).
- **Endgültiges Löschen:** Die Frage darf nur kommen, wenn gerade „Foto entfernen“ gedrückt wurde, und muss das Bild vom Klick meinen. Absicherung: `change` verwirft den Klick; AC-3, AC-4 und AC-4b prüfen das Bild.
- **WebKit lokal nicht gemessen:** Ob dort `change` und `openingAnimationEnd` gleich laufen, zeigt erst die CI (AC-10).
- **Pfeilknopf im Öffnen (AC-4):** Seitenfehler aus #706; eng eingegrenzte Ausnahme, kein pauschales Schlucken. Tritt ein anderer Fehler auf, geht die Spec zur Abstimmung zurück. Ob WebKit denselben Wortlaut meldet, zeigt erst die CI; weicht er ab, wird die Ausnahme um genau diesen Wortlaut ergänzt.
- **Test hängt an Bibliotheksstring:** Ändert sich `showAnimationDuration:333` bei einem Update des Vendors, scheitert der Test mit Grund (Test 9) statt still zu verlieren.
- **Mitnutzer:** Änderungen an `grossAuf` und `frage` berühren den Ablauf für „Mo“ und BI-90; AC-5 und AC-8 sichern das.

## Known Limitations

- Kreuz, Escape und Wischen während des Öffnens wirken nicht (Bibliothek); nicht Teil des Tickets.
- Pfeilknopf im Öffnen: eigener Fehler, #706.
- Nach dem Klick im Öffnen kommt die Frage rund 0,4 s später (am Ende des Öffnens), dann ohne Schließ-Übergang (`showHideAnimationType` ist „none“, wie bisher bei „Foto entfernen“).
- Bei reduzierter Bewegung kommt `openingAnimationEnd` synchron in `init()`, vor dem nachher angehängten Fokus-Hörer. Ob der Fokus dann erst später in die Großansicht kommt, ist aus dem Code geschlossen und nicht gemessen; nicht Teil des Tickets.
- WebKit wurde nach dem RED-Lauf auch lokal gemessen (`webkit-messung.txt`): Der Pfeilknopf-Fehler aus #706 heißt dort „undefined is not an object (evaluating 'pswp.currSlide.data')“; der Test lässt im Ablauf „blaettern“ je Browser genau diesen einen Wortlaut zu (wie unter Risks vorgesehen).
- Das schmale Fenster in der Meldung `openingAnimationEnd` selbst (Schließen mitten in der Meldung) wird durch `setTimeout` umgangen, nicht gesondert geprüft.

## Definition of Done

- [ ] AC-1 bis AC-8, AC-4b und AC-12 durch Tests belegt
- [ ] AC-9: RED am heutigen Stand für die genannten Fälle gezeigt, danach grün
- [ ] AC-10: betroffener Test in mindestens 3 CI-Läufen grün, beide Browser, Pflichtprüfungen grün, `test_bilder_eigen.py` und `test_seite_bilder.py` grün
- [ ] AC-11: Vergleich mit `main` belegt
- [ ] Pull Request und Issue #689 sagen ausdrücklich, dass der CI-Auslöser nicht bewiesen ist, die Ursache ein Fehler der Seite ist und die längere Wartezeit allein nicht geholfen hätte
- [ ] #706 bleibt offen und getrennt; im Pull Request verlinkt
- [ ] Auslieferung nur über den normalen Weg (Pull Request, grüne Pflichtprüfungen, Vorspulen)
- [ ] Issue #689 erst nach grünem Lauf auf `main` schließen

## Changelog

- 2026-11-25: Initiale Spec (#689)
- 2026-11-26: Known Limitations: WebKit lokal gemessen, Wortlaut des #706-Fehlers in WebKit (Validierung)
- 2026-11-27: #706: Der Pfeilknopf wirkt im Öffnen nicht mehr. AC-4 („Klick, dann Pfeil verwirft“) gilt seitdem so: es blättert nichts, die Frage kommt zum gezeigten Foto; Test umbenannt in `test_gross_klick_im_oeffnen_dann_pfeil_fragt`, Ausnahme für den Seitenfehler entfernt (`docs/specs/oberflaeche/pfeil-im-oeffnen-706.md`).
