# Mini-Spec: fix-656-vorab-ordner-faden

Issue #656: `test_kartenpunkte_vorab_ordner_wird_immer_geloescht[ausnahme]` scheiterte einmal in der CI mit `FileExistsError` auf `tmp-osm`.

## Ursache

Der Fall `[frist]` setzt `ZEIT_GESAMT = 0.01`. `vorgang_speicher` antwortet mit 504, sein Faden `vorbereiten` (`engine/schreiben.py:6204`) exportiert weiter. `exportieren` legt mit `mkdir(parents=True)` (`engine/reisespeicher.py:541`, 544) fehlende Elternordner wieder an. Der Faden löscht danach nur seinen Ordner `frieda-schreiben-*`, nicht das wieder entstandene `tmp-osm`. pytest hat den Testordner des bestandenen Falls gelöscht und gibt dem nächsten Fall wegen der Kürzung der Namen auf 30 Zeichen denselben (`test_kartenpunkte_vorab_ordner0`).

Nachgestellt: Faden vor diesem `mkdir` angehalten, 3 von 3 Läufen rot mit genau diesem Fehler in `[ausnahme]`. Für den CI-Lauf selbst ist es nicht bewiesen (das Protokoll nennt die Fäden nicht); Testfall und Pfad stimmen überein.

## Was ändert sich
- Nur `engine/tests/test_schreiben.py` (rund 30 Zeilen).
- Eine Hilfe für Tests (Kontextmanager `faeden_abwarten`) wartet beim Verlassen auf alle Fäden, die seit ihrem Beginn gestartet wurden (Zeitgrenze 30 s), auch nach einem Fehler im Block. Läuft danach noch einer, scheitert der Test mit einer Meldung, die den Faden nennt.
- `test_kartenpunkte_vorab_ordner_wird_immer_geloescht` wartet in allen vier Fällen so auf seine Fäden, auch wenn eine Prüfung im Test scheitert, und zwar vor dem Zurücksetzen der Umgebung und vor dem Löschen von `tmp_path`.
- Der Fall `[frist]` hält den Faden ab jetzt selbst an: Sein Export beginnt erst nach der Antwort 504. So entsteht die Lage aus der CI bei jedem Lauf statt nur zufällig, und der Test prüft nach dem Warten, dass dieser Export geendet hat.
- Nach dem Warten prüft der Test zusätzlich, dass `tmp-osm` ganz leer ist (bisher nur `frieda-osm-*`).

## Was darf sich nicht ändern
- `engine/schreiben.py` und `engine/reisespeicher.py` bleiben unverändert. Im Betrieb ist der Elternordner das Temp-Verzeichnis, das bestehen bleibt, und der Faden löscht seinen eigenen Ordner.
- Alle bisherigen Prüfungen des Tests bleiben, ebenso `…_auch_nach_zu_langer_vorbereitung_weg` (wartet schon selbst auf seinen Faden).
- `mkdir()` bleibt streng: kein `exist_ok=True`, keine Wiederholung, keine längere Frist als Ersatz für das Warten.

## Acceptance Criteria
- **AC-1:** Given im Fall `[frist]` beginnt der Export des Fadens erst nach der Antwort 504, when der Block der Hilfe verlassen ist, then hat dieser Export geendet, und `tmp-osm` ist leer. (Ohne die Hilfe ist dieser Fall bei jedem Lauf rot.)
- **AC-2:** Given ein Faden, der erst nach einer Weile endet, when der Block der Hilfe verlassen wird, then geschieht das erst nach dessen Ende.
- **AC-3:** Given ein Faden, der nicht in der Zeitgrenze endet, when der Block verlassen wird, then scheitert die Hilfe mit einer Meldung, die den Namen des Fadens nennt.
- **AC-4:** Given eine Prüfung im Block scheitert, when der Block verlassen wird, then wird trotzdem auf die Fäden gewartet, und der ursprüngliche Fehler bleibt der gemeldete.
- **AC-5:** Given die vier Fälle und die übrigen Tests der Datei, when sie laufen, then sind sie grün, und `tmp-osm` ist nach jedem der vier Fälle leer.

## Bleibende Tests
| AC | Test in `engine/tests/test_schreiben.py` |
|---|---|
| AC-1, AC-5 | `test_kartenpunkte_vorab_ordner_wird_immer_geloescht` (alle vier Fälle, `[frist]` mit angehaltenem Faden) |
| AC-2 | `test_faeden_abwarten_bis_zum_ende` |
| AC-3 | `test_faeden_abwarten_nennt_haengenden_faden` |
| AC-4 | `test_faeden_abwarten_auch_nach_fehler` |

## Reichweite
Dass der eine rote CI-Lauf genau so entstand, lässt sich nicht mehr beweisen; das Protokoll nennt die Fäden nicht. Testfall und Pfad stimmen überein, und der nachgestellte Weg erzeugt genau diese Meldung. Dieser Weg ist danach ausgeschlossen; käme der Fehler trotzdem wieder, wäre es ein anderer Weg.

## Manuelle Test-Schritte
Keine, alles automatisch. Zusätzlich einmalig als Nachweis: der Versuchsaufbau mit dem unmittelbar vor `mkdir` angehaltenen Faden (vorher rot, nachher grün) und die vier Fälle 30-mal hintereinander; danach der volle Testlauf in der CI.

## Inline-Test (wird während Implementierung geschrieben)
- [ ] Die vier Tests der Tabelle; `[frist]` ohne die Hilfe rot
