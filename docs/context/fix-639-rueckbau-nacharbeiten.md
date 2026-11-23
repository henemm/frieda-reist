# Context: fix-639-rueckbau-nacharbeiten

## Request Summary
Nacharbeiten aus der unabhängigen Prüfung des Rückbaus #557 (alle niedrig): Schutzliste beim Aufräumen des alten
Bauordners vervollständigen, Lesefehler des Reisespeichers beim Übernehmen von Arten/Packliste nicht als „Reise ohne
Arten“ melden, Doku der Schreibziele berichtigen, Abschluss des Umzugs auch bei reiner Rechte-Abweichung der Units,
zwei ungesicherte Zuweisungen unter `set -e` absichern (Kommentar des Owners, F005).

## Related Files
| File | Relevance |
|------|-----------|
| betrieb/veroeffentlichen.sh (`altbau_entfernen`, ~Z. 839) | Schutzliste `for fremd in "$FR_WURZEL" "$FR_DIENST" "$FR_SPEICHER" "$FR_SEITEN/_software" "$FR_SEITEN/_dienst"` ohne FR_ABLAGE, FR_KONTEN, FR_KONNEKTOR; `seiten_real="$(cd "$FR_SEITEN" && pwd -P)"` ungesichert unter `set -e` |
| betrieb/veroeffentlichen.sh (`umzug_fertig_im_klon`, ~Z. 817) | `units.py pruefen > /dev/null 2>&1 \|\| return 0` → Exit 3/4 setzt nie `fertig`; `echo fertig > …neu && mv …` als letzter Befehl einer &&-Kette, danach weitere Zeilen (set -e greift nicht in &&-Liste außer letztem Glied) |
| betrieb/units.py (`ausgang`) | Exit 0 = gleich, 3 = nur erlaubte Abweichungen, 4 = gesperrte Abweichung (z. B. ReadWritePaths/Sandbox), sonst Fehler |
| betrieb/gemeinsam.sh Z. 93–95 | Vorgaben FR_ABLAGE=`$FR_SEITEN/_rueckmeldungen`, FR_KONNEKTOR=`$FR_SEITEN/_konnektor`, FR_KONTEN=`$FR_SEITEN/_konten` |
| engine/schreiben.py `fremde_datei` (~Z. 5151) | fängt KeyError, OSError, sqlite3.Error, UnicodeDecodeError, AblageFehlt/AblageFehler → None |
| engine/schreiben.py `arten_uebernehmen` (~Z. 4738), `packliste_uebernehmen` (~Z. 5166) | None → Ablehnung `.2` („ohne Arten“/„nicht lesbar“) |
| engine/schreiben.py `anwenden` (~Z. 5794) | wandelt sqlite3.Error → 503 `schreiben.dienst.speicher_nicht_erreichbar`, Ablagefehler → 503 pruefung.bauen.79/.80, StandGeaendert → 503 |
| betrieb/vorlagen/schreiben.service | `ReadWritePaths=__WURZEL__ __DIENST__ __KONTEN__ __SEITEN__ __ABLAGE__`; Kommentar: `__WURZEL__` = Bauordner mit .git (Software-Klon, #454): Holen von main beim Veröffentlichen |
| docs/betrieb.md Z. 384 | Schreibziele „(Bauordner mit `.git`, …)“ – mehrdeutig, seit #557 gibt es nur noch den Software-Klon; Z. 574 Aufräumen-Absatz (Schutzbedingungen) |
| engine/tests/test_rueckbau_557.py | Fixture `ab` (L3 altbau_entfernen), Pfadprüfungs-Tests AC-29, `test_altbau_reine_readwritepaths_abweichung_haelt_nicht_auf` (Muster für units-Stub mit Exit 4) |
| engine/tests/test_schreiben_speicher.py Z. 262 | `test_ablagefehler_gibt_saubere_antwort_ohne_wirkung` erwartet `fremde_datei(...) is None` bei Ablagefehler (muss angepasst werden) |

## Existing Patterns
- Speicherfehler im Schreibweg → `speicher_fehler(werkzeug, e)` → 503 mit Katalogschlüssel; Ablehnungen nur für fachliche Gründe.
- altbau_entfernen: jeder Verstoß → `altbau_warnen <schlüssel> <text>; return 0`, nie Alarm.
- units-Stubs in Tests über `VF_UNITS`.

## Dependencies
- Upstream: reisespeicher.datei (KeyError für unbekannte Reise/Datei), units.py pruefen.
- Downstream: Konnektor-Werkzeuge kinds_adopt / packing_list_adopt (Antwort 503 statt 422 bei Speicherfehler).

## Existing Specs
- `docs/specs/*/rueckbau-git-weg-557.md`, `rueckbau-557-git-weg.md`

## Risks & Considerations
- `umzug_fertig_im_klon` bei Exit 4: Exit 4 kann auch eine gesperrte Abweichung sein, die noch auf den alten Ort zeigt. Nur `fertig` setzen, wenn keine Abweichungszeile den alten Bauordner `<FR_SEITEN>/_bau` nennt (wie altbau_entfernen prüft).
- arten.yaml/packliste.yaml liegen in der DB, nicht in der Ablage; Ablagefehler dort praktisch nur theoretisch.
- Schutzliste: FR_ABLAGE/FR_KONTEN/FR_KONNEKTOR liegen per Vorgabe unter FR_SEITEN, aber nie unter _bau; Schutz greift nur bei abweichender Einstellung.
- Kein Formatwechsel der Reisedaten, keine Texte neu (vorhandener Schlüssel speicher_nicht_erreichbar).

## Analysis

### Type
Bug (Nacharbeiten, alle niedrig; nur nicht umgezogene bzw. fehlerhafte Instanzen betroffen)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| betrieb/veroeffentlichen.sh | MODIFY | `altbau_entfernen`: Schutzliste um `$FR_ABLAGE` `$FR_KONTEN` `$FR_KONNEKTOR` ergänzen (leere Werte überspringen); `seiten_real="$(cd … && pwd -P)" \|\| return 0`. Neue Hilfsfunktion `units_ohne_altbau` (rc ∈ {0,3,4} und Ausgabe nennt `$FR_SEITEN/_bau` nicht), von `altbau_entfernen` und `umzug_fertig_im_klon` gemeinsam genutzt. `umzug_fertig_im_klon`: statt `pruefen … \|\| return 0` die Hilfsfunktion; `{ echo fertig > neu && mv …; } \|\| return 0` (Schreibfehler stumm, kein Abbruch unter `set -e`) |
| engine/schreiben.py | MODIFY | `fremde_datei`: nur `KeyError` (Reise/Datei fehlt) und `UnicodeDecodeError` (Inhalt unbrauchbar) → None. `sqlite3.Error` geht unverändert weiter (anwenden → 503 speicher_nicht_erreichbar). `OSError` und `AblageFehlt/AblageFehler` werden zu einer eigenen Ausnahme (z. B. `FremdNichtLesbar`), die `anwenden` ebenfalls als 503 `schreiben.dienst.speicher_nicht_erreichbar` beantwortet — so nennt `ablage_fehler` nicht fälschlich die eigene Reise als Ort des Fehlers, und OSError endet nicht als 500 |
| docs/betrieb.md | MODIFY | Z. 384: Schreibziele „Software-Klon mit Git-Daten (Holen von main beim Veröffentlichen)“ statt „Bauordner mit `.git`“; Z. 574: Schutzbedingung nennt Ablage, Konten, Konnektor; Umzug: fertig auch bei reiner gesperrter Rechte-Abweichung, solange keine Unit den alten Bauordner nennt |
| betrieb/vorlagen/schreiben.service | MODIFY (Kommentar, falls nötig) | `__WURZEL__` = Software-Klon |
| engine/tests/test_rueckbau_557.py | MODIFY | Tests: Ziel enthält FR_ABLAGE/FR_KONTEN/FR_KONNEKTOR → nichts gelöscht, Warnzeile; `umzug_fertig_im_klon` mit units-Stub Exit 4 ohne `_bau` → fertig; Exit 4 mit `_bau` in der Zeile → bleibt; Exit 1 → bleibt; nicht betretbares FR_SEITEN → Lauf bricht nicht ab |
| engine/tests/test_schreiben_speicher.py | MODIFY | Z. 285: `fremde_datei` bei Ablagefehler wirft statt None; neu: arten_uebernehmen / packliste_uebernehmen mit kaputter fremder Ablage bzw. DB → 503 speicher_nicht_erreichbar, keine Wirkung; unbekannte Reise bleibt Ablehnung `.2` |

### Scope Assessment
- Files: 5–6
- Estimated LoC: +~120 / -~15 (davon ~90 Tests)
- Risk Level: LOW — Aufräumen wird nur strenger geschützt; Umzugsabschluss betrifft nur Instanzen, die noch nicht `fertig` sind; Schreibweg ändert nur die Antwort im Fehlerfall (503 statt 422)

### Technical Approach
1. Schutzliste vervollständigen (realpath -m wie bisher).
2. Eine gemeinsame Prüfung „keine Unit zeigt auf den alten Bauordner“ für Aufräumen und Umzugsabschluss — dieselbe Regel an beiden Stellen statt zweier Auslegungen der units.py-Exitcodes.
3. Zwei Zuweisungen unter `set -e` absichern (`|| return 0`).
4. `fremde_datei` trennt fachlich (Reise/Datei fehlt → Ablehnung wie bisher) von technisch (Speicher nicht lesbar → 503 mit Protokollzeile). Kein neuer Text.
5. Doku berichtigen.

Kein Formatwechsel der Reisedaten, keine `nachziehen`-Umstellung, keine neuen Texte, kein neues Modul für deploy.sh, keine neue Alarmstelle. Antwort der Werkzeuge kinds_adopt / packing_list_adopt bei Speicherfehler ändert sich (503 statt 422) → Instanz-Tests vor dem Ausliefern mitlaufen lassen.

### Dependencies
- `units.py pruefen` (Zeilen „<unit>: allowed/BLOCKED, …“; Exit 0/3/4).
- `reisespeicher.datei` (KeyError, sqlite3.Error, AblageFehlt/AblageFehler, OSError).
- Konnektor reicht 503 der Schreibweg-Antwort als Speicherfehler weiter.

### Open Questions
- keine (nur technische Entscheidungen)
