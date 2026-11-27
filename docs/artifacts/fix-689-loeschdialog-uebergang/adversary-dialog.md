# Adversary Dialog — fix-689-loeschdialog-uebergang
Spec: docs/specs/oberflaeche/loeschfrage-grossansicht-689.md
Datum: 2026-11-25 18:23

## Checkliste
- [x] **AC-1:** Given die Großansicht öffnet noch (verlängert, `isOpen` falsch) / When „Foto entfernen“ geklickt wird / Then steht nach dem Öffnen genau ein Dialog, die Großansicht ist zu und der Fokus liegt im Dialog. Greift die Verlängerung nicht (Zeichenkette nicht genau einmal in der Bibliothek, Test 9) oder war das Fenster beim Klick schon zu, scheitert der Test mit Grund. Test: `engine/tests/test_bilder_eigen.py::test_gross_klick_im_oeffnen_fragt_einmal`
- [x] **AC-2:** Given wie AC-1 / When dreimal im Öffnen geklickt wird / Then genau ein Dialog und kein Seitenfehler. Test: `engine/tests/test_bilder_eigen.py::test_gross_dreifachklick_im_oeffnen_ein_dialog`
- [x] **AC-3:** Given der Dialog aus AC-1 / When „Behalten“ gedrückt und die Großansicht erneut geöffnet und geschlossen wird / Then wurde nichts gesendet und keine zweite Frage kommt; „Entfernen“ löscht genau das Bild vom Klick. Test: `engine/tests/test_bilder_eigen.py::test_gross_behalten_und_entfernen_nach_klick_im_oeffnen`
- [x] **AC-4:** Given Klick im Öffnen / When vor dem Ende mit dem Pfeilknopf geblättert wird / Then wird der Klick verworfen: keine Frage, kein DELETE, auch nicht nach späterem Schließen. Ein Seitenfehler „reading 'data'“ (#706) ist dort möglich und nur dort, nur mit genau diesem Text, zugelassen; jeder andere Seitenfehler macht den Test rot. Test: `engine/tests/test_bilder_eigen.py::test_gross_klick_im_oeffnen_dann_blaettern_verwirft`
- [x] **AC-4b:** Given Klick im Öffnen und zwei eigene Fotos / When das Öffnen endet / Then steht die Frage sofort da und meint das Foto vom Klick; nie kommt sie erst nach späterem Blättern und Schließen, wenn ein anderes Foto gezeigt wird. Test: `engine/tests/test_bilder_eigen.py::test_gross_frage_meint_das_gezeigte_foto`
- [x] **AC-5:** Given die Großansicht ist offen (Öffnen beendet) / When „Foto entfernen“ geklickt wird / Then wie bisher (AC-14 aus #582). Test: `engine/tests/test_bilder_eigen.py::test_browser_hochladen_hinweis_nennung_und_loeschen`
- [x] **AC-6:** Given reduzierte Bewegung / When „Foto entfernen“ geklickt wird / Then wirkt der Klick weiter sofort. Test: `engine/tests/test_bilder_eigen.py::test_gross_reduzierte_bewegung_klick_sofort`
- [x] **AC-7:** Given Klick im Öffnen / When sofort Escape gedrückt wird / Then kommt die Frage. Test: `engine/tests/test_bilder_eigen.py::test_gross_klick_im_oeffnen_dann_escape_fragt`
- [x] **AC-8:** Given der Dialog fehlt beim ersten Öffnen / When `grossAuf` und `frage` laufen / Then ist das ein klarer Fehler mit Grund (Gegenprobe); der Ablauf für „Mo“ (kein Knopf) bleibt unverändert. Test: `engine/tests/test_bilder_eigen.py::test_gross_fehlender_dialog_ist_klarer_fehler`
- [x] **AC-9:** Given der heutige Stand (Vorlage unverändert) / When die Tests der AC-1 bis AC-4b, AC-7 und AC-8 laufen / Then sind sie rot (RED), einschließlich des Falls „später blättern und schließen: gezeigt BI-90, gelöscht BI-91“; nach der Änderung grün. AC-5, AC-6 und AC-12 sind Wächter und heute schon grün. Test: von Claude ausgeführt (RED-Lauf und GREEN-Lauf, Ausgabe im Nachweis)
- [x] **AC-10:** Given der Stand vor der Auslieferung / When `test_bilder_eigen.py` und `test_seite_bilder.py` laufen / Then sind sie grün (Chromium lokal, WebKit in der CI), der betroffene Test in mindestens 3 CI-Läufen, dazu die Pflichtprüfungen `tests (leer)`, `tests (instanz)` und `gitleaks`. Test: von Claude ausgeführt (CI-Läufe, `gh run rerun` genügt)
- [x] **AC-11:** Given der Stand der Änderung / When er mit `main` verglichen wird / Then sind nur `engine/vorlage.html`, `engine/tests/seiten_bilder_eigen.mjs`, `engine/tests/test_bilder_eigen.py` und Unterlagen unter `docs/` geändert; `docs/funktionen/bilder.md` und der Vendor sind unverändert. Test: von Claude ausgeführt (Vergleich mit `main`)
- [x] **AC-12:** Given die ausgelieferte Bibliothek / When die Verlängerung des Öffnens eingespielt wird / Then kommt `showAnimationDuration:333` genau einmal vor; sonst scheitert der Test mit Grund, statt das Fenster still zu verlieren. Test: `engine/tests/test_bilder_eigen.py::test_gross_verlaengerung_greift`

## Dialog

Testlauf: `docs/artifacts/fix-689-loeschdialog-uebergang/adversary-test-output.txt` (voller Lauf von `test_bilder_eigen.py` und `test_seite_bilder.py`: 121 passed, 1 übersprungen, der Skip ist `flock fehlt` in `test_bilder_eigen.py:1329`, unabhängig von #689; Chromium und WebKit, beide lokal vorhanden). Mutationen und Probe-Abläufe liefen in Kopien unter dem Scratchpad; nichts unter `engine/` im Worktree wurde geändert (Dateien vor und nach den Läufen byteweise verglichen). AC-10 (3 CI-Läufe) ist in Runde 3 geprüft und erfüllt (siehe dort; der Teil „betroffene Tests je Lauf grün“ ist aus den Summenzeilen abgeleitet, nicht aus Testnamen).

### Runde 1
**Adversary:** Spec lesen, nicht den Kommentar im Code. Pro AC ein eigener Lauf oder eine eigene Messung.
- Grundlauf (eigen, Worktree): 121 passed, 1 skipped (fremd). Alle neun neuen Tests und `test_browser_hochladen_hinweis_nennung_und_loeschen` grün in beiden Browsern.
- AC-9 selbst nachgestellt: (a) Tests und Vorlage von Commit ecd51b3 (Vorlage = main): 14 rot von 29 (je Browser 1, 2, 3, 4a, 4b, 7, 8). (b) heutige Tests mit unveränderter Vorlage von main: 12 rot (1, 2, 3, 4a, 4b, 7 in beiden Browsern); der Fall „gezeigt BI-90, gelöscht BI-91“ steht wörtlich in der Meldung von AC-4b. AC-8 ist in (b) grün: er hängt an den Test-Hilfen (`frage`, `grossAuf`), nicht an der Vorlage (Befund F002). Mit heutiger Vorlage und heutigen Tests: 29 grün.
- Mutationen (Kopie; Tabelle im Bericht): `change`-Hörer weg und `change`-Hörer hinter die werfenden Hörer (nach `init()`): AC-4 rot in beiden Browsern, sonst nichts, genau das Soll. `openingAnimationEnd`-Hörer weg: AC-1, 2, 3, 4b, 7 rot. Verlängerung `334` und doppelter Treffer in der Bibliothek: AC-12 rot mit Grund („Verlängerung greift nicht: ... je Abruf [0]-mal / [2]-mal statt einmal“), dazu alle Tests mit Klick im Öffnen. `frage` verschluckt wieder: AC-8 rot in beiden Browsern. Klick nie sofort (kein `destroy` bei `isOpen`): AC-5, AC-6 (Chromium), AC-8 rot.
- Überlebende Mutationen, ohne roten Test: `isDestroying`-Wächter weg (F003), `setTimeout` weg (F003, Known Limitation der Spec), Bedingung `isOpen` weg bzw. immer sofort `destroy` (F003, gleichwertig), Klick meint `gruppe[currIndex]` statt `b` (gleichwertig, solange `change` jeden Indexwechsel verwirft; allein nicht beobachtbar).
- Randfälle ohne Verlängerung (normale 333 ms), beide Browser: Klickzeitpunkt 0, 100, 250, 300, 330, 345, 360, 380, 400, 430, 460, 520 ms nach Erscheinen des Knopfs: überall genau 1 Dialog zu BI-91, Großansicht zu, kein DELETE. Mit Verlängerung (3000 ms) Klick bei 2850 bis 3200 ms, dicht um das Kippen von `isOpen` (3090/3100 ms in Chromium, 3080/3090 ms in WebKit, 10-ms-Schritte): überall genau 1 Dialog. Klick im selben Takt wie `openingAnimationEnd` und im Takt danach: 1 Dialog, kein Seitenfehler.
- Klick im Öffnen, dann Pfeiltaste, Mausziehen, Kreuz, Mausrad, Fenstergröße, Hash-Wechsel im Öffnen (Zurück): überall 1 Frage zu BI-91, kein DELETE ohne Bestätigung. Ohne Klick (offen lassen, Pfeiltasten): nie eine Frage. Behalten, erneut im Öffnen klicken, Behalten, öffnen, nach dem Öffnen klicken: je 1 Frage, nichts gesendet. Einzelbild-Galerie (1 Eintrag, über `grossAnsicht([BI-91], 0, null)`): Klick im Öffnen, 1 Frage. Reduzierte Bewegung: Klick wirkt sofort. Mo: kein Knopf, kein Ablauf.
- Kann ein anderes Foto gelöscht werden als das geklickte? Klick, dann Pfeilknopf (normal und verlängert, beide Browser): Klick verworfen, keine Frage, kein DELETE, nur der erwartete Seitenfehler aus #706. Umgekehrt (Pfeilknopf zuerst, dann Klick auf den danach stehengebliebenen Knopf von BI-91): die Frage kommt am Ende des Öffnens, `currIndex` ist 1 (BI-90), Bestätigen löscht BI-91 (Befund F001).
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Nachbohren bei den überlebenden Mutationen und beim Test selbst.
- `isDestroying`-Wächter: Die Spec nennt ihn „nötig“. Ich erzwang das Fenster: ein eigener Hörer ruft nach dem der Vorlage `GROSS.close()` im Takt von `openingAnimationEnd` auf, einmal mit, einmal ohne Wächter, beide Browser. Beide Male 1 Dialog, Großansicht zu, kein Seitenfehler: kein sichtbarer Unterschied (F003). `setTimeout` weg: ebenfalls kein Seitenfehler und kein roter Test, obwohl die Vorlage ihren `openingAnimationEnd`-Hörer vor dem der Bibliothek anhängt; die Spec führt das als Known Limitation.
- Test selbst: `test_gross_klick_im_oeffnen_dann_blaettern_verwirft` lässt je Browser genau einen Seitenfehlertext zu; den WebKit-Wortlaut (`undefined is not an object (evaluating 'pswp.currSlide.data')`) hat die Umsetzung nach dem RED-Lauf ergänzt; AC-4 in der Spec nennt nur den Chromium-Wortlaut (F004, LOW). Die Ausnahme gilt nur in diesem einen Ablauf; ein anderer Seitenfehler macht ihn rot (an `_gross_frage_da` und `a["fehler"]` der übrigen Abläufe gelesen).
- AC-8 mit `"gross":false` in der Prüfung hängt auch am Verhalten der Vorlage (Klick nie sofort macht ihn rot), nicht nur an `frage`. Kein Mangel, nur Hinweis.
- Streuung: Mutation „Klick nie sofort“ ließ im ersten Lauf unter Last `test_gross_reduzierte_bewegung_klick_sofort[webkit]` nicht rot werden; in drei Wiederholungen (je beide Browser) war er jedes Mal rot. Nicht reproduziert, nur vermerkt (F005, LOW).
- Wirkt das Fenster des Tests wie behauptet? `klickImOeffnen` verlangt in derselben Auswertung `isOpen === false` und die Verlängerung genau einmal (`engine/tests/seiten_bilder_eigen.mjs:194`); beides ließ ich mutieren (AC-12) und es scheitert mit Grund. Die Dauer 3000 ms ist in beiden Browsern gemessen (`dauer: 3000`).
- Dialog nennt das Foto nicht: `bildEntfernenFragen` zeigt nur Titel und Zusage; wer „Entfernen“ bestätigt, kann am Dialog nicht prüfen, welches Foto es trifft. Deshalb zählt F001 mehr, als sein Auslöser vermuten lässt.
- AC-11: Dateiliste des Vergleichs mit dem Stand von main außerhalb `docs/`: genau `engine/vorlage.html`, `engine/tests/seiten_bilder_eigen.mjs`, `engine/tests/test_bilder_eigen.py`; `docs/funktionen/bilder.md` und `engine/vendor/` nicht dabei.
- WebKit: lokal vorhanden und gemessen; die Spec sagt „nur in der CI messbar“, das stimmt für diese Maschine nicht mehr. Ergebnisse stimmen in beiden Browsern überein.
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 3
**Adversary:** Nur AC-10, an den CI-Läufen selbst mit `gh` gelesen, keiner Zusammenfassung geglaubt.
- Geprüfter Stand: Commit 9f5ff05 (Kopf von PR #707). `headSha` aller drei Versuche des Laufs 45704557945 und des Geheimnis-Scans 45704557919 ist dieser Commit. Die drei Blob-Kennungen im Block „Prüfbasis“ stimmen mit dem Baum des Commits überein, die sha256 im Block „Geprüfte Dateien“ mit den Dateien im Arbeitsbaum (neu berechnet); `git status` unter `engine/` ist sauber. Das Protokoll gilt also für genau diesen Commit. Der Vergleich der PR-Dateiliste (`gh pr view 707 --json files`) zeigt unter `engine/` genau die drei Dateien aus AC-11; der lokale Zweig `main` im Worktree ist veraltet (ihm fehlen die #656-Commits), daher zeigt `git diff main...HEAD` dort fälschlich eine vierte Datei.
- Versuche (belegt, Ausgabe von `gh run view ... --attempt N --json jobs`): Versuch 1 `tests (instanz)` und `tests (leer)` success; Versuch 2 `tests (instanz)` success, `tests (leer)` failure; Versuch 3 beide success. `gh pr checks 707` jetzt: `gitleaks` pass, `tests (instanz)` pass, `tests (leer)` pass (Versuch 3). Geheimnis-Scan 45704557919 success.
- Summenzeilen je Job (belegt, wörtlich im Nachweis): 5 Jobs `3741 passed, 1 skipped`, Versuch 2 `tests (leer)` `1 failed, 3740 passed, 1 skipped in 1225.75s`. Der eine Skip ist in allen sechs Jobs `engine/tests/test_wackel_599.py:118: Stand 5f36075 nicht im Checkout` (Aufruf mit `-q -rs -n auto engine/tests`, `.github/workflows/tests.yml:136`); kein Skip in `test_bilder_eigen.py` oder `test_seite_bilder.py` (der Skip „Playwright fehlt“, `engine/tests/test_bilder_eigen.py:1359`, steht in keinem Job). Die Schritte „Browser-Prüfung darf nicht übersprungen worden sein“ sind in allen Jobs grün. Chromium und WebKit werden in der CI installiert (`npx playwright install ... chromium webkit`, Schritt „Playwright und Browser“).
- Ausgefallener Test in Versuch 2 (belegt, `--log-failed`): `engine/tests/test_warteliste.py::test_eintrag_ueber_die_seite_antwort_ist_immer_gleich`; schon die Vorbereitung `seite_anmelden`, `POST /anmelden`, läuft in `TimeoutError: timed out` (10-s-Grenze). Kein Bezug zu #689: weder Vorlage, noch Bildtests, noch Großansicht werden dort berührt; derselbe Test war in Versuch 1 und 3 sowie in `tests (instanz)` von Versuch 2 grün. Ursache offen, in Issue #708 geführt. Nicht ausschließbar (nur vermutet): Last auf dem Runner, zu der die 3-Sekunden-Abläufe der neuen Tests beitragen könnten; Versuch 2 war mit 1225 s der längste, aber Versuch 1 und 3 mit gleichen Tests liefen in 1152 bis 1166 s ohne Ausfall.
- Liefen die betroffenen Tests, grün, nicht übersprungen? Abgeleitet, nicht belegt: `-q` nennt keine Testnamen, also steht in der CI nirgends „`test_gross_klick_im_oeffnen_fragt_einmal[webkit]` passed“. Die Ableitung: (a) der Zweig `-rs` listet jeden Skip, und es gibt nur den einen fremden; (b) in Versuch 2 ist der einzige Fehlschlag der Wartelisten-Test mit Namen, also alle übrigen 3740 Tests, darunter die Bildtests beider Browser, bestanden; (c) 3741 + 1 = 3742 Tests in jedem Job (Versuch 2: 3740 + 1 + 1), also dieselbe Menge; (d) die Bildtests sind Teil von `engine/tests`. Der Beweis für Dateien, Parametrisierung (`engine/tests/test_bilder_eigen.py:1487`, chromium und webkit) und die Zahl der Tests (121 lokal) stammt aus dem Quelltext und dem lokalen Lauf, nicht aus der CI. Das genügt für AC-10; nicht belegt bleibt, dass in der CI wirklich ein WebKit-Prozess startete (der Skip-Zweig dafür steht in `test_bilder_eigen.py:1359` und hätte sich gezeigt).
- F005 (Empfindlichkeit von `test_gross_reduzierte_bewegung_klick_sofort[webkit]`): in der CI nicht aufgefallen. Streng genommen kann die CI das auch nicht zeigen, F005 betraf die Mutation (rot werden), nicht die Stabilität; die CI zeigt nur, dass der Test in sechs Jobs (3 Versuche je zwei Jobs) nicht ausfiel. Befund bleibt LOW und unverändert.
- Ergebnis AC-10 nach Wortlaut: „Chromium lokal, WebKit in der CI“ grün (lokal 121 passed, CI 3741 passed je Job); „betroffener Test in mindestens 3 CI-Läufen“ drei Versuche desselben Commits (die Spec lässt `gh run rerun` ausdrücklich genügen), in allen dreien liefen die Bildtests und bestanden (abgeleitet); „Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`“ im jetzigen Stand alle grün (Versuch 3). Der rote Versuch 2 widerspricht dem nicht: der Fehlschlag ist ein fremder, einmaliger Zeitablauf (#708), die betroffenen Tests waren in ihm grün. Erfüllt.
**Implementierer:** (nicht beteiligt, Kontextisolation)

## Findings

Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/vorlage.html:1762
  Description: Die Frage meint das Foto, dessen Knopf geklickt wurde. Blättert man im Öffnen zuerst mit dem Pfeilknopf (löst den Fehler aus #706 aus, Zähler und Knopf bleiben bei BI-91, `currIndex` wird 1) und klickt danach auf den stehengebliebenen Knopf, wird `danach` für BI-91 gemerkt; `change` kommt nicht mehr, nichts verwirft. Am Ende des Öffnens kommt die Frage, Bestätigen löscht BI-91, während `currIndex` 1 (BI-90, leere Ansicht) ist. Gemessen in Chromium und WebKit (Probe `pfeilDannKlick`): Frage da, DELETE BI-91. Der Dialog nennt das Foto nicht (`engine/vorlage.html:1681`).
  Spec requirement: AC-4b — die Frage meint das Foto vom Klick; Purpose — keine Frage zu einem anderen Bild als dem gezeigten
  Conflict: Kein AC verletzt (das Foto des geklickten Knopfs wird gemeint), aber derselbe Gefahrentyp wie im Ticket; getestet ist nur die Reihenfolge Klick, dann Pfeil. Der Weg ist älter als #689 (derselbe Klick nach dem Öffnen führte schon vorher zur Frage zu BI-91), Ursache ist der stehengebliebene Knopf aus #706.
  Remediation: In #706 aufnehmen (Pfeilknopf im Öffnen), Test „Pfeil, dann Klick“ dort ergänzen; oder im Klick-Hörer `danach` nur setzen, wenn `pswp.currIndex` dem Index des Knopfs entspricht.

Finding:
  ID: F002
  Severity: LOW
  Category: spec_violation
  Code reference: engine/tests/seiten_bilder_eigen.mjs:81
  Description: AC-9 verlangt AC-8 rot „bei unveränderter Vorlage“. Mit den heutigen Tests und der Vorlage von main ist `test_gross_fehlender_dialog_ist_klarer_fehler` grün (12 rot statt 14). Rot war er nur im RED-Commit ecd51b3, weil dort `frage` und `grossAuf` noch alt waren.
  Spec requirement: AC-9 — Tests der AC-1 bis AC-4b, AC-7 und AC-8 sind am heutigen Stand rot
  Conflict: Der Wortlaut stimmt für AC-8 nur gegenüber den alten Test-Hilfen, nicht gegenüber der Vorlage.
  Remediation: AC-9 in der Spec präzisieren (AC-8 ist RED gegenüber den alten Hilfen von ecd51b3); keine Codeänderung.

Finding:
  ID: F003
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/vorlage.html:1742
  Description: Überlebende Mutationen ohne roten Test: `!pswp.isDestroying` weg, `setTimeout` weg, Bedingung `isOpen` in Zeile 1762 weg (immer `destroy`; im Öffnen ist `destroy()` bis auf das Setzen von `showHideAnimationType` wirkungslos, also gleichwertig). Auch ein erzwungenes Schließen im Takt von `openingAnimationEnd` zeigt ohne Wächter keinen Unterschied in beiden Browsern.
  Spec requirement: Implementation Details 2 — Wächter `!pswp.isDestroying` „nötig“; Known Limitations (nur `setTimeout` genannt)
  Conflict: Die behauptete Notwendigkeit von Wächter und Bedingung ist nicht belegt; kein Test hält sie fest.
  Remediation: Entweder als vorsorglich kennzeichnen (Kommentar und Spec) oder einen Test finden, der den Unterschied zeigt; kein Handlungsbedarf für die Auslieferung.

Finding:
  ID: F004
  Severity: LOW
  Category: spec_violation
  Code reference: engine/tests/test_bilder_eigen.py:1536
  Description: Der Test lässt je Browser einen Wortlaut zu, auch den von WebKit; AC-4 und der Abschnitt „Blättern im Test“ der Spec nennen nur den Chromium-Wortlaut („nur mit genau diesem Text“). Die Spec sieht in Risks die Ergänzung vor, hat sie aber nicht nachgetragen.
  Spec requirement: AC-4 — nur mit genau diesem Text zugelassen
  Conflict: Spec und Test weichen im Wortlaut ab; der Test ist enger als jede Pauschalausnahme (je Browser genau ein Text).
  Remediation: AC-4 und Risks um den WebKit-Wortlaut ergänzen.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/tests/test_bilder_eigen.py:1562
  Description: Bei der Mutation „Klick nie sofort“ blieb `test_gross_reduzierte_bewegung_klick_sofort[webkit]` in einem von vier Läufen nicht rot (drei Wiederholungen rot). Ursache nicht geklärt; möglicherweise Takt von `openingAnimationEnd` in WebKit bei reduzierter Bewegung unter Last.
  Spec requirement: AC-6 — bei reduzierter Bewegung wirkt der Klick weiter sofort
  Conflict: Bei der echten Vorlage grün und stabil (121 grün); nur die Empfindlichkeit gegenüber der Mutation schwankte einmal.
  Remediation: Beobachten; in den CI-Läufen von AC-10 prüfen, ob der Test je Lauf stabil grün ist.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/vorlage.html:1742
  Evidence: `openingAnimationEnd` schließt aufgeschoben, wenn `danach` gemerkt ist; Test `test_gross_klick_im_oeffnen_fragt_einmal` (`engine/tests/test_bilder_eigen.py:1515`) grün in beiden Browsern, rot bei Vorlage von main und bei fehlendem Hörer; eigene Probe: 1 Dialog, Großansicht zu, Fokus im Dialog; 20 Klickzeitpunkte normal und verlängert, auch um das Ende.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/seiten_bilder_eigen.mjs:221
  Evidence: dreimal im Öffnen geklickt: 1 Dialog, kein Seitenfehler, beide Browser; `test_gross_dreifachklick_im_oeffnen_ein_dialog` (`engine/tests/test_bilder_eigen.py:1520`) rot bei Vorlage von main und ohne `openingAnimationEnd`-Hörer.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_bilder_eigen.py:1525
  Evidence: „Behalten“ sendet nichts, erneutes Öffnen und Schließen ohne zweite Frage, „Entfernen“ löscht genau BI-91 (`geloescht == ["BI-91"]`); eigene Probe `nachBehalten` bestätigt; Abläufe `behalten` und `entfernen` in `engine/tests/seiten_bilder_eigen.mjs:222`.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/vorlage.html:1741
  Evidence: `change`-Hörer vor `init()` verwirft den Klick; die Mutationen „Hörer weg“ und „Hörer hinter die werfenden Hörer“ machen genau `test_gross_klick_im_oeffnen_dann_blaettern_verwirft` rot (beide Browser); normale Dauer: Klick und Pfeilknopf im selben Takt, Großansicht bleibt offen, keine Frage; nur der Seitenfehler aus #706 tritt auf (Test `engine/tests/test_bilder_eigen.py:1536`). Gegenrichtung siehe F001.
  Status: CONFIRMED

Confirmation:
  AC: AC-4b
  Code reference: engine/tests/test_bilder_eigen.py:1549
  Evidence: bei Vorlage von main rot mit „Klick verloren; gezeigt BI-90, gelöscht ['BI-91']“; heute `geloescht == ["BI-91"]` und keine Frage ohne Klick; in allen eigenen Abläufen nie eine Frage zu BI-90 außer in F001.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_bilder_eigen.py:1454
  Evidence: `test_browser_hochladen_hinweis_nennung_und_loeschen` unverändert grün in beiden Browsern; rot bei der Mutation „Klick nie sofort“, also scharf; Zweig `if (pswp.opener.isOpen) pswp.destroy()` in `engine/vorlage.html:1762`.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/tests/test_bilder_eigen.py:1562
  Evidence: reduzierte Bewegung: `klick.isOpen` wahr, Frage sofort; rot bei „Klick nie sofort“ (im ersten Lauf nur in Chromium, F005); Ablauf `reduziert` in `engine/tests/seiten_bilder_eigen.mjs:261`.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/tests/seiten_bilder_eigen.mjs:256
  Evidence: Escape direkt nach dem Klick im Öffnen: Frage kommt, auch bei normaler Dauer (Probe `normalKlickEscape`); `test_gross_klick_im_oeffnen_dann_escape_fragt` rot bei Vorlage von main.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/tests/seiten_bilder_eigen.mjs:81
  Evidence: `frage` wirft mit Zustand (`dialoge`, `gross`, `isOpen`); die Mutation „frage verschluckt“ macht `test_gross_fehlender_dialog_ist_klarer_fehler` in beiden Browsern rot; Mo ohne Knopf unverändert (`geloescht` leer, `loeschen == {"knopf": false}`). Zum RED-Wortlaut siehe F002.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/tests/test_bilder_eigen.py:1568
  Evidence: RED selbst nachgestellt (ecd51b3: 14 rot; heutige Tests mit Vorlage von main: 12 rot, Fall gezeigt BI-90, gelöscht BI-91 in der Meldung); GREEN: 121 passed, 1 fremder Skip. Abweichung nur bei AC-8, F002.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/vorlage.html:1741
  Evidence: Dateiliste des Vergleichs mit main außerhalb `docs/`: nur `engine/vorlage.html`, `engine/tests/seiten_bilder_eigen.mjs`, `engine/tests/test_bilder_eigen.py`; Vendor und `docs/funktionen/bilder.md` unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/tests/seiten_bilder_eigen.mjs:194
  Evidence: `showAnimationDuration:333` kommt genau einmal in der Bibliothek vor; die Mutationen auf `334` und auf einen doppelten Treffer machen `test_gross_verlaengerung_greift` und alle Tests mit Klick im Öffnen rot mit dem Grund „Verlängerung greift nicht ... [0]-mal / [2]-mal statt einmal“ (Test `engine/tests/test_bilder_eigen.py:1508`).
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/tests/test_bilder_eigen.py:1487
  Evidence: Commit 9f5ff05, Lauf 45704557945 Versuch 1 bis 3: `tests (instanz)` und `tests (leer)` je success außer Versuch 2 `tests (leer)` (`1 failed, 3740 passed, 1 skipped`, ausgefallen `test_warteliste.py::test_eintrag_ueber_die_seite_antwort_ist_immer_gleich`, `TimeoutError` bei `POST /anmelden`, Issue #708, ohne Bezug zu #689); Versuch 3 und `gitleaks` (Lauf 45704557919) grün, `gh pr checks 707` alle drei Pflichtprüfungen pass. Der einzige Skip ist `test_wackel_599.py:118`. Die Bildtests beider Browser (Parametrisierung hier) sind aus den Summenzeilen als bestanden abgeleitet, nicht mit Namen belegt.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

AC-1 bis AC-12 sind belegt; AC-10 in Runde 3 an den CI-Läufen (drei Versuche desselben Commits, Pflichtprüfungen im jetzigen Stand grün; der Ausfall in Versuch 2 ist ein fremder Zeitablauf, Issue #708). Ein MEDIUM-Befund (F001) außerhalb der Akzeptanzkriterien, vier LOW-Befunde; Runde 3 bringt keinen neuen Befund.

VERDICT: VERIFIED
(Tests lokal: 121 passed, 0 failed, 1 übersprungen (fremd, `flock fehlt`); CI Commit 9f5ff05: 3741 passed, 1 skipped (fremd, `test_wackel_599.py`) je Job im grünen Zustand)

## Geprüfte Dateien

- sha256:a2721ad1dbc42a01904dd100c05388ea422aa55e93a84787a110cd7cbf4e03c6  engine/tests/seiten_bilder_eigen.mjs
- sha256:e8b135bc4cc6611be6c1121b01bff9a893dabd93a4a36ded31c1c375a20c4df9  engine/tests/test_bilder_eigen.py
- sha256:536c44a14f40dafc1d01bc119f9f8696a6faf4b3c9d86042484297da6b3c879e  engine/vorlage.html

## Prüfbasis

- base: 2a40a98ac99719c7aa31114f37e41c021dec4478
- blob:17a5b8dffa2a4b20bfcb27fba8d0a83c5e9eb01c  engine/tests/seiten_bilder_eigen.mjs
- blob:63be84ba3bdf89894a0e6c7287ab2d872fa22fd9  engine/tests/test_bilder_eigen.py
- blob:698d3bddd889c8dc9d7f79ac8d07a734d458ef60  engine/vorlage.html

## Geprüfte Dateien

- sha256:a2721ad1dbc42a01904dd100c05388ea422aa55e93a84787a110cd7cbf4e03c6  engine/tests/seiten_bilder_eigen.mjs
- sha256:e8b135bc4cc6611be6c1121b01bff9a893dabd93a4a36ded31c1c375a20c4df9  engine/tests/test_bilder_eigen.py
- sha256:536c44a14f40dafc1d01bc119f9f8696a6faf4b3c9d86042484297da6b3c879e  engine/vorlage.html

## Prüfbasis

- base: 2a40a98ac99719c7aa31114f37e41c021dec4478
- blob:17a5b8dffa2a4b20bfcb27fba8d0a83c5e9eb01c  engine/tests/seiten_bilder_eigen.mjs
- blob:63be84ba3bdf89894a0e6c7287ab2d872fa22fd9  engine/tests/test_bilder_eigen.py
- blob:698d3bddd889c8dc9d7f79ac8d07a734d458ef60  engine/vorlage.html
