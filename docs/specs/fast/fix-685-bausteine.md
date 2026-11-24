# Mini-Spec: fix-685-bausteine

Issue: #685. Zwei Kartentests ersetzen in der kopierten `reise.yaml` der Beispielreise eine feste Zeile
`bausteine: [varianten, karte, tagesseiten, …, wuensche]`. Die Zeile lautet inzwischen anders
(`packliste` dazu, `tagesseiten` weg), `str.replace` greift nicht, die Tests laufen still mit allen Bausteinen.

## Was ändert sich
- Neue Testhilfe `bausteine_setzen(reise_ordner, liste)` in `engine/tests/test_karte_auto.py`: ersetzt die
  Zeile `bausteine: [...]` per regulärem Ausdruck unabhängig von ihrem Inhalt und bricht mit `assert` ab,
  wenn es nicht genau eine solche Zeile gibt (kein stilles Nichtstun mehr).
- `engine/tests/test_karte_seite.py` (`seite()`) und `engine/tests/test_karte_popup_310.py` (`_seite()`)
  nutzen die Hilfe; der Parameter `bausteine` von `seite()` wirkt damit wieder.
- `test_karte_auto.py` (Karte aus, Zeile 80) nutzt dieselbe Hilfe statt eines Präfix-Ersatzes.
- Der veraltete Baustein `tagesseiten` (seit #214 ohne Wirkung, wird still herausgenommen) verschwindet aus
  den Bausteinlisten der Tests.
- Danach prüfen, ob die Tests mit dem gewünschten Satz grün sind und noch prüfen, was sie sollen
  (Reiter „Karte“ ohne Varianten, mit Varianten bei Festlegung/Plänen, Popup).

## Was darf sich nicht ändern
- Kein Produktcode, keine Beispielreise, keine sichtbaren Texte.
- Die Aussagen der Tests (was sie im Browser prüfen) bleiben gleich, außer ein Test zeigt, dass er bisher
  nur dank aller Bausteine grün war; dann wird die Erwartung an den gewünschten Satz angepasst und im PR erklärt.

## Manuelle Test-Schritte
1. `engine/.venv/bin/python -m pytest -q engine/tests/test_karte_seite.py engine/tests/test_karte_popup_310.py engine/tests/test_karte_auto.py`
2. Hilfe gegen eine Zeile ohne `bausteine:` aufrufen: muss mit AssertionError scheitern.

## Inline-Test (wird während Implementierung geschrieben)
- [ ] Test für `bausteine_setzen`: setzt die Liste (per YAML nachgelesen) und scheitert laut ohne passende Zeile
