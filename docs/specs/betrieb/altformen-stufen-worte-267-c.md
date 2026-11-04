# `STUFEN_WORTE` entfällt (#267, PR c1; Teil 3 von #215)

Teilspec zu [altformen-entfernen-267.md](altformen-entfernen-267.md) (Entscheidung 1, AC-8). Zuschnitt des Product Owners vom
4.11.2026: PR c1 löscht nur `routen.STUFEN_WORTE`, PR c2 danach `texte.BESTAND_REISE` (AC-7, AC-9). Dieses Paket ist c1.

## Anlass

`routen.STUFEN_WORTE = texte.gruppe(texte.BESTAND_REISE, "schreiben.stufe")` hängt an der Bestandssprache. Die Konstante muss
weg, bevor `BESTAND_REISE` fallen kann. Sie hat genau einen Leser: `stufe_satz` prüft mit `s in STUFEN_WORTE`, ob ein Wert
eine bekannte Stufe ist. Die Wörter selbst holt `stufe_satz` mit `texte.satz("schreiben.stufe." + s)` in der Sprache der
Person; `stufe_schluessel` liest sie je Sprache aus dem Katalog. Die Konstante enthält genau die vier Schlüssel (belegt durch den bisherigen Test in `test_texte.py`, Suchbegriff `STUFEN_WORTE`), die
`STUFEN` schon sprachneutral nennt (`pflicht`, `empfohlen`, `angeboten`, `aus`).

## Lösung

- `engine/routen.py`: Zeile mit `STUFEN_WORTE` löschen; in `stufe_satz` die Mengenprüfung `s in STUFEN` statt
  `s in STUFEN_WORTE`. Kommentar bei `STUFEN` anpassen, falls er die Konstante nennt.
- `stufe_schluessel` und `schreiben.stufe_satz` bleiben unverändert. Keine Katalogänderung, kein neues Modul.
- Das Verhalten für Menschen bleibt gleich („nötig (pflicht)“ usw., in Deutsch und Englisch).
- Kein Format der Reisedaten betroffen, daher keine Umstellung in `neu.py nachziehen` und kein Handschritt in Reisen oder
  Instanzen. Kein Instanz-Test nötig: keine Meldungstexte, Schnittstellen, Umgebungswerte oder Dateiformate ändern sich.

## Betroffene Dateien

| Datei | Änderung |
|---|---|
| `engine/routen.py` | `STUFEN_WORTE` löschen; `stufe_satz` prüft `s in STUFEN` |
| `engine/tests/test_texte.py` | Test auf den Inhalt der Konstante (Z. ~135) entfällt; neuer Test auf `stufe_satz` in beiden Sprachen |

## Geplante Tests

- `stufe_satz` liefert in Deutsch und Englisch für `pflicht`, `empfohlen`, `angeboten` und `aus` den Katalogtext der
  jeweiligen Sprache, und für den Typ-Zusatz („gilt nicht“) wie bisher; ein unbekannter Wert bleibt `Satz(str(s))`.
- Ein Test sucht in `engine/` (ohne die Testdateien selbst) nach `STUFEN_WORTE` ohne Treffer; der Name steht im Test nicht ausgeschrieben, sonst fände er sich selbst.
- Bestehende Tests zu `stufe_schluessel` (`test_texte.py`, `test_routen.py`) bleiben grün.
- Vor dem Vorspulen: `engine/.venv/bin/python -m pytest -q engine/tests` grün ohne echte Reisen.

## Acceptance Criteria

- **AC-8 (c1):** `routen.STUFEN_WORTE` ist gelöscht (Suche in `engine/` ohne Treffer); `stufe_satz` und `stufe_schluessel`
  liefern in Deutsch und Englisch dieselben Ergebnisse wie vorher; ein unbekannter Wert wird unverändert als Text
  zurückgegeben.
- **AC-C1-1:** Die Ausnahmelisten in `engine/tests/test_texte.py` sind gegenüber dem Stand von `main` nicht länger geworden.
- **AC-C1-2:** Bau und Seiten beider Beispielreisen (`beispielreise`, `stadtwochenende`) sind vor und nach dem Paket gleich (Bau beider Reisen mit dem Branch und mit `main`, Vergleich der gebauten Seiten).

## Abgrenzung

- `texte.BESTAND_REISE` bleibt in c1 stehen (Paket c2).
- Nichts Reisespezifisches, keine Änderung an Wortlauten.
