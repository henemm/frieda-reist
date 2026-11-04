# Adversary Dialog — altformen-267-c
Spec: docs/specs/betrieb/altformen-stufen-worte-267-c.md
Datum: 2026-11-04 11:05

## Checkliste
- [x] **AC-8 (c1):** `routen.STUFEN_WORTE` ist gelöscht (Suche in `engine/` ohne Treffer); `stufe_satz` und `stufe_schluessel` liefern in Deutsch und Englisch dieselben Ergebnisse wie vorher; ein unbekannter Wert wird unverändert als Text zurückgegeben. — PROVEN
- [x] **AC-C1-1:** Die Ausnahmelisten in `engine/tests/test_texte.py` sind gegenüber dem Stand von `main` nicht länger geworden. — PROVEN
- [x] **AC-C1-2:** Bau und Seiten beider Beispielreisen (`beispielreise`, `stadtwochenende`) sind vor und nach dem Paket gleich (Bau beider Reisen mit dem Branch und mit `main`, Vergleich der gebauten Seiten). — PROVEN

## Dialog

### Runde 1
**Adversary:** Ich gehe davon aus, dass die Änderung kaputt ist, und greife an drei Stellen an.
1. Hat die Konstante noch andere Leser als `stufe_satz`? Die Suche nach `STUFEN_WORTE` in `engine/`, `betrieb/` und `werkzeuge/` findet keinen Treffer. In `docs/` stehen nur Spec-, Kontext- und Artefakt-Dateien. Im Hauptcheckout `/home/hem/frieda-reist/engine/routen.py` steht sie noch, weil dort die Änderung nicht eingespielt ist. Das gehört nicht zum Paket.
2. Ist `STUFEN` gleich dem Schlüsselsatz der alten Konstante? Ich habe `texte.gruppe(texte.BESTAND_REISE, "schreiben.stufe")` ausgewertet. Es kommt `{pflicht, empfohlen, angeboten, aus}` heraus, und `routen.STUFEN` ist `("pflicht","empfohlen","angeboten","aus")`. Die Schlüsselmengen sind gleich.
3. Verhaltensvergleich gegen den Stand von `main`: Ich habe `routen.py` von `main` in den Scratchpad gelegt und beide Module mit denselben 18 Eingaben aufgerufen, je in `de` und `en` (36 Fälle): `None`, `""`, `[]`, `1`, `0`, `True`, `"PFLICHT"`, `"nötig"`, `"pflicht "`, `"pflicht"`, `"aus"`, `"empfohlen"`, `"angeboten"`, `"x"`, `{}`, `("a",)`, `{"*":"aus","a":"pflicht"}`, `{"a":None}`. Ergebnis: 0 Abweichungen, auch bei den Ausnahmen. Das ist erwartbar: Die Prüfung `isinstance(s, str)` steht vor dem Mengentest, daher kommt eine Liste nie in einen Hash-Lookup. Gross-/Kleinschreibung und Wörter wie „nötig“ gelten wie vorher als unbekannt und bleiben Text. Die Eingabe über Wörter läuft weiter über `stufe_schluessel`, das unverändert ist (`engine/routen.py:318-328`).
4. Tests: `pytest -q engine/tests/test_texte.py engine/tests/test_routen.py` ergibt 168 passed. Die Voll-Suite (1299 passed) laut `test-green-output.txt` habe ich nicht neu laufen lassen.
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Zweiter Angriff auf die Nachweise.
1. AC-C1-1: Der Diff von `engine/tests/test_texte.py` gegen `main` ändert nur den Block um Zeile 135 (alte Prüfung auf die Konstante entfernt, zwei neue Tests). Keine Zeile einer Ausnahmeliste kommt hinzu oder fällt weg. Die Listen sind unverändert, also nicht länger.
2. Ist der Namens-Test echt oder leer? `test_stufen_konstante_der_bestandssprache_ist_weg` (`engine/tests/test_texte.py`) baut den Namen aus `"STUFEN" + "_WORTE"` zusammen, damit er sich nicht selbst findet. Er liest alle `*.py` unter `ENGINE` (ohne `.venv`, `vendor`, `tests`) als Text. Er findet also auch Kommentare und Docstrings und ist unabhängig von Hash und `.pyc`. `.pyc`-Dateien werden nicht gescannt, sie sind aber nicht eingecheckt und entstehen aus der Quelle. Das RED-Protokoll `test-red-output.txt` zeigt, dass er vorher fehlschlug. Schwäche (nur Hinweis, kein Befund): `betrieb/` und `werkzeuge/` liegen außerhalb des Scans. Dort gibt es aber keinen Treffer (siehe Runde 1).
3. AC-C1-2: Ich habe beide Beispielreisen selbst gebaut, einmal mit dem Branch-Stand und einmal mit einer Kopie von `engine/` und `beispiel/`, in der `routen.py` durch den Stand von `main` ersetzt ist (Reisedaten aus dem Worktree, damit der von der Versionsverwaltung abhängige `reise_stand` gleich ist). Beide Bauten enden mit Exit 0. Der Ordnervergleich zeigt Unterschiede nur in `index.html` (Zeile `data-release`) und `sw.js` (`VERSION`, `RELEASE`, `STAND`-Hash von `index.html`). Nach dem Ersetzen von `data-release` sind beide `index.html` identisch. Die Release-Zeilen kommen aus der Versionsverwaltung (Nummer 460, Kennung 66331b7 gegen `{}` in der Kopie ohne Repo), der Hash folgt daraus. Das deckt sich mit `seitenvergleich.txt`. `daten.json`, Manifest und alle übrigen Dateien sind byte-gleich. Ein erster Versuch mit Reisedaten außerhalb des Repos wich in `reise_stand` ab; das war ein Fehler meines Aufbaus, nicht der Änderung.
4. Frühe Einigkeit: In beiden Runden kam kein Befund. Deshalb habe ich je Punkt eigene Messungen gemacht und die Aussagen des Implementierers nicht übernommen.
**Implementierer:** (nicht beteiligt)

## Bestätigungen

Confirmation:
  AC: AC-8
  Code reference: engine/routen.py:289
  Evidence: `STUFEN_WORTE` ist weg (Zeile 289 ist nur noch `STUFEN`, kein Treffer in `engine/`); `stufe_satz` prüft in Zeile 299 mit `s in STUFEN`. Identisches Verhalten zu `main` in 36 de/en-Fällen, unbekannte Werte bleiben Text; `stufe_schluessel` (Zeile 318) unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-C1-1
  Code reference: engine/tests/test_texte.py:135
  Evidence: Der Diff berührt keine Ausnahmeliste, nur die alte Konstantenprüfung (ersetzt durch zwei Tests ab Zeile 137).
  Status: CONFIRMED

Confirmation:
  AC: AC-C1-2
  Code reference: engine/routen.py:299
  Evidence: Eigener Nachbau beider Beispielreisen, Branch gegen `main`-`routen.py`: nur Release- und Hash-Zeilen unterscheiden sich, `index.html` ist nach Ersetzen von `data-release` identisch.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Die Änderung schreibt kein Feld; sie ersetzt nur eine Mengenprüfung (`engine/routen.py:299`).

## Verdict

VERDICT: VERIFIED

Tests: 168 passed (gezielt test_texte.py, test_routen.py), 0 failed, 0 übersprungen; Voll-Suite 1299 passed laut test-green-output.txt (nicht neu gelaufen)
Edge cases: Nicht-String, Liste, leer, None, Groß-/Kleinschreibung, Wörter statt Schlüssel: gleiches Verhalten wie main
Regressions: keine; keine weiteren Leser von STUFEN_WORTE in engine/, betrieb/, werkzeuge/
Checklist: 3/3 points proven

## Geprüfte Dateien

- sha256:e8c19839d1d156ac3c8e3652e2f090ccb9c3d160a6560ef6f91a067358fb45e3  engine/routen.py
- sha256:9b6669aa781225b56c248abfb742837901d336b7b390dc4e8c8eaa4ab5312ca0  engine/tests/test_texte.py

## Prüfbasis

- base: d28e7eb70c7ecee666e0844359db4a404ed60bad
- blob:30fa76196f7c4004ee73a5506205c558306f787a  engine/routen.py
- blob:d26db8830ddc66434d4c13bcb8029079547115e8  engine/tests/test_texte.py
