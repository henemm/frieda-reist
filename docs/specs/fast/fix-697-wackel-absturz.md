# Mini-Spec: fix-697-wackel-absturz

Issue #697 (Meilenstein M7: wackelige Tests). Nur Testcode, die Software bleibt unverändert.

## Ursache

`engine/tests/test_wackel_599.py::test_alter_ablauf_ist_unter_verzoegerung_rot` soll zeigen, dass der Rundgang im Stand vor
#599 unter Verzögerung scheitert. Unter Last scheitert der alte Rundgang aber nicht mit einer falschen Leiste, sondern stürzt
ab (`page.evaluate: TypeError … box.parentElement`, das Symptom aus #661). `_rundgang` prüft `aus.returncode == 0`
(Zeile 78) und lässt den Test deshalb scheitern, obwohl der alte Ablauf erwartungsgemäß versagt hat.

## Was ändert sich

- `_rundgang(…, erwarte_ok=True)`: Mit `erwarte_ok=False` wird ein Rückgabecode ≠ 0 nicht als Testfehler gewertet; die
  Funktion gibt dann `None` zurück.
- `_leiste(…, erwarte_ok=True)` reicht den Schalter durch und gibt bei einem Absturz `None` zurück.
- `_leiste_stimmt(None)` ist `False`: Ein abgestürzter Rundgang hat keine stimmende Leiste.
- `test_alter_ablauf_ist_unter_verzoegerung_rot` ruft `_leiste` für den alten Stand mit `erwarte_ok=False` auf.

## Was darf sich nicht ändern

- Alle Nachweise für den neuen Ablauf (`erwarte_ok` bleibt standardmäßig `True`): Ein Absturz des neuen Rundgangs bleibt rot.
- Der Teil des Tests zur Karte (`_karte`, alter Stand von `seiten_karte_popup.mjs`) bleibt wie er ist; #697 betrifft nur die
  Leiste.
- `seiten_browser.mjs` und alle übrigen Testdateien.

## Acceptance Criteria

- AC-1: Ein Rundgang-Skript, das mit Rückgabecode ≠ 0 endet, ergibt mit `erwarte_ok=False` eine nicht stimmende Leiste, ohne
  dass der Test scheitert.
- AC-2: Dasselbe Skript lässt `_leiste` mit dem Standard (`erwarte_ok=True`) weiterhin scheitern (strenger neuer Ablauf).
- AC-3: `test_wackel_599.py` ist vollständig grün.

## Inline-Test

- [ ] `test_absturz_des_alten_ablaufs_zaehlt_als_rot`: ein kleines Ersatzskript, das sofort mit Code 1 endet; prüft AC-1 und
  AC-2 ohne Browser (läuft also immer, auch in CI).
