---
entity_id: rueckbau-nacharbeiten-639
type: bugfix
created: 2026-11-23
updated: 2026-11-23
status: draft
workflow: fix-639-rueckbau-nacharbeiten
version: "1.0"
tags: [rueckbau, veroeffentlichen, schreibweg, reisespeicher, betrieb, nacharbeit]
---

# Rückbau #557: Nacharbeiten aus der Qualitätsprüfung (#639)

Folge von #557. Grundlage: `docs/context/fix-639-rueckbau-nacharbeiten.md` (Analyse, Technical Approach), `docs/specs/betrieb/rueckbau-git-weg-557.md` (Vorgänger), ADR-0009, ADR-0001.

## Approval

- [ ] Approved

(Keine Produktentscheidung offen. Alle Punkte sind technisch und unten begründet.)

## Purpose

Die unabhängige Prüfung des Rückbaus #557 fand fünf kleine Mängel, alle mit niedrigem Risiko: Das Aufräumen des alten Bauordners schützt Ablage, Konten und Konnektor nicht vor dem Löschen, wenn deren Ordner abweichend eingestellt sind. Ein Lesefehler im Reisespeicher wird beim Übernehmen von Arten oder Packliste als „Reise ohne Arten“ gemeldet statt als Speicherfehler. Die Betriebsdoku nennt bei den Schreibzielen noch den „Bauordner mit `.git`“. Der Umzugsabschluss bleibt bei einer reinen Rechte-Abweichung der Units hängen. Zwei Zuweisungen laufen unter `set -e` ungesichert. Diese Spec beseitigt alle fünf, ohne Formatwechsel und ohne neue Texte.

## Source

- **File:** `betrieb/veroeffentlichen.sh`, `engine/schreiben.py`, `docs/betrieb.md`, `betrieb/vorlagen/schreiben.service` (nur Kommentar)
- **Identifier:** `altbau_entfernen`, `umzug_fertig_im_klon`, neue Hilfsfunktion `units_ohne_altbau` (alle in `betrieb/veroeffentlichen.sh`); `fremde_datei`, `arten_uebernehmen`, `packliste_uebernehmen`, `anwenden`, neue Ausnahme `FremdNichtLesbar` (in `engine/schreiben.py`)

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `betrieb/units.py` (`pruefen`, Exit 0 gleich, 3 nur erlaubte Abweichungen, 4 gesperrte Abweichung) | Skript | Grundlage der gemeinsamen Prüfung „keine Unit zeigt auf den alten Bauordner“ |
| `betrieb/gemeinsam.sh` (Vorgaben `FR_ABLAGE`, `FR_KONTEN`, `FR_KONNEKTOR` unter `FR_SEITEN`) | Skript | Quelle der zusätzlich zu schützenden Pfade |
| `engine/reisespeicher.py` (`datei`) | Modul | Wirft `KeyError` (Reise/Datei fehlt), `sqlite3.Error`, `AblageFehlt`/`AblageFehler`, `OSError` |
| `engine/schreiben.py` (`anwenden`, `speicher_fehler`) | Modul | Bildet Speicherfehler auf 503 `schreiben.dienst.speicher_nicht_erreichbar` ab (vorhandener Textschlüssel) |
| Konnektor-Werkzeuge `kinds_adopt`, `packing_list_adopt` | Downstream | Reichen die Antwort des Schreibwegs durch; im Speicherfehlerfall 503 statt 422 |
| Tests der Instanz unter `<FR_DIENST>/instanz/tests` | Instanz-Tests | Laufen vor dem Vorspulen mit dem Branch (Antwort ändert sich im Fehlerfall) |

## Scope

### Im Scope

1. **Schutzliste:** `altbau_entfernen` löscht nichts, wenn der Bauordner mit `FR_ABLAGE`, `FR_KONTEN` oder `FR_KONNEKTOR` zusammenfällt oder sie enthält (Auflösung wie bisher mit `realpath -m`; leere Werte werden übersprungen).
2. **Gemeinsame Units-Prüfung:** Eine Hilfsfunktion `units_ohne_altbau` liefert Erfolg, wenn `units.py pruefen` mit Exit 0, 3 oder 4 endet und die Ausgabe `$FR_SEITEN/_bau` nicht nennt. `altbau_entfernen` und `umzug_fertig_im_klon` nutzen sie beide, damit es keine zwei Auslegungen der Exitcodes gibt. Damit setzt eine reine gesperrte Rechte-Abweichung (Exit 4, die den alten Bauordner nicht nennt) den Umzug auf `fertig`.
3. **Absicherung unter `set -e`:** `seiten_real="$(cd "$FR_SEITEN" && pwd -P)" || return 0` in `altbau_entfernen`; in `umzug_fertig_im_klon` wird `{ echo fertig > …neu && mv …; } || return 0` (Schreibfehler stumm, kein Abbruch des Laufs).
4. **Lesefehler des Speichers:** `fremde_datei` fängt nur noch `KeyError` und `UnicodeDecodeError` (Ergebnis `None`, Ablehnung wie bisher). `sqlite3.Error` geht unverändert durch. `OSError` sowie `AblageFehlt`/`AblageFehler` werden in die neue Ausnahme `FremdNichtLesbar` überführt. `anwenden` beantwortet sie wie `sqlite3.Error` als 503 `schreiben.dienst.speicher_nicht_erreichbar`, mit Protokollzeile.
5. **Doku:** `docs/betrieb.md` berichtigt (Schreibziele, Aufräumen, Umzugsabschluss); Kommentar in `betrieb/vorlagen/schreiben.service`: `__WURZEL__` ist der Software-Klon.

### Nicht im Scope (Out of Scope)

- Kein Formatwechsel der Reisedaten, keine Umstellung in `neu.py nachziehen`.
- Keine neuen Texte (vorhandener Schlüssel `speicher_nicht_erreichbar`), keine neue Alarmstelle (`ALARMSTELLEN` bleibt unverändert; Verstöße beim Aufräumen bleiben Warnzeilen), kein neues Modul für `betrieb/deploy.sh`.
- Keine Änderung der Erlaubnisliste von `units.py` und keine Änderung des Konnektors selbst.
- Keine echten Reisen, Serveradressen, Namen echter Personen oder absolute Pfade (öffentliches Repo); Platzhalter wie `<FR_SEITEN>`, `<FR_DIENST>`.

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `betrieb/veroeffentlichen.sh` | MODIFY | Schutzliste um Ablage, Konten, Konnektor; `units_ohne_altbau`; zwei Absicherungen unter `set -e`; `umzug_fertig_im_klon` nutzt die Hilfsfunktion |
| `engine/schreiben.py` | MODIFY | `fremde_datei` trennt fachlich (None) von technisch (Ausnahme); `anwenden` beantwortet `FremdNichtLesbar` als 503 |
| `docs/betrieb.md` | MODIFY | Schreibziele „Software-Klon mit Git-Daten (Holen von main beim Veröffentlichen)“; Aufräumen nennt Ablage, Konten, Konnektor; Umzugsabschluss auch bei reiner gesperrter Rechte-Abweichung |
| `betrieb/vorlagen/schreiben.service` | MODIFY | Nur Kommentar: `__WURZEL__` = Software-Klon |
| `engine/tests/test_rueckbau_557.py` | MODIFY | Tests zu AC-1 bis AC-7 und AC-12 |
| `engine/tests/test_schreiben_speicher.py` | MODIFY | Tests zu AC-8 bis AC-11; bestehender Test bei Ablagefehler angepasst |

### Estimated Changes

- Files: 6
- LoC: +120/-15 (davon rund 90 Tests)

## Implementation Details

Technischer Ansatz wie in der Analyse (`docs/context/fix-639-rueckbau-nacharbeiten.md`), verbindlich.

**Skript:** In `altbau_entfernen` wird die Schleife über die geschützten Pfade (bisher `FR_WURZEL`, `FR_DIENST`, `FR_SPEICHER`, `FR_SEITEN/_software`, `FR_SEITEN/_dienst`) um `FR_ABLAGE`, `FR_KONTEN`, `FR_KONNEKTOR` erweitert. Jeder Verstoß bleibt `altbau_warnen <schlüssel> <text>; return 0`, nie ein Alarm. `units_ohne_altbau` ruft `units.py pruefen` (über `VF_UNITS` in Tests ersetzbar), wertet den Exitcode (0, 3, 4 gelten als vertretbar, alles andere nicht) und prüft die Ausgabe auf den Pfad `$FR_SEITEN/_bau`. Exit 4 kann eine gesperrte Abweichung sein, die noch auf den alten Ort zeigt; nur die Nennung des alten Bauordners hält Aufräumen und Umzugsabschluss auf.

**Engine:** `fremde_datei` unterscheidet „Reise oder Datei gibt es nicht“ und „Inhalt unbrauchbar“ (fachlich, `None`, Ablehnung `.2` wie bisher) von „Speicher nicht lesbar“ (technisch). Die technische Ausnahme trägt nicht den Ort der eigenen Reise, damit `ablage_fehler` die eigene Reise nicht fälschlich als Fehlerort nennt, und `OSError` endet nicht als 500. Der Speicherfehlerfall ändert die Antwort von `kinds_adopt` und `packing_list_adopt` von 422 auf 503; deshalb laufen vor dem Vorspulen die Instanz-Tests mit dem Branch mit.

**Hinweis zur Ablage:** `arten.yaml` und `packliste.yaml` liegen in der Datenbank, nicht in der Ablage; ein Ablagefehler ist dort praktisch nur theoretisch, wird aber vollständig behandelt.

## Test Plan

### Automated Tests (TDD RED)

- [ ] Test 1: GIVEN ein alter Bauordner und `FR_ABLAGE` zeigt auf diesen Ordner WHEN `altbau_entfernen` läuft THEN wird nichts gelöscht, es gibt eine Warnzeile, Exit 0 und keine Alarmmeldung.
- [ ] Test 2: GIVEN `FR_KONTEN` (bzw. `FR_KONNEKTOR`) liegt im alten Bauordner WHEN `altbau_entfernen` läuft THEN wird nichts gelöscht und es gibt eine Warnzeile.
- [ ] Test 3: GIVEN `units.py pruefen` endet mit Exit 4 ohne Nennung von `<FR_SEITEN>/_bau` WHEN `umzug_fertig_im_klon` läuft THEN steht der Zustand auf `fertig`.
- [ ] Test 4: GIVEN Exit 4 mit einer Zeile, die `<FR_SEITEN>/_bau` nennt WHEN `umzug_fertig_im_klon` läuft THEN bleibt der Zustand unverändert.
- [ ] Test 5: GIVEN `units.py pruefen` endet mit Exit 1 WHEN `umzug_fertig_im_klon` und `altbau_entfernen` laufen THEN bleibt der Zustand unverändert und es wird nichts gelöscht.
- [ ] Test 6: GIVEN `FR_SEITEN` ist nicht betretbar WHEN `altbau_entfernen` läuft THEN bricht der Lauf nicht ab (Exit 0, Warnzeile).
- [ ] Test 7: GIVEN das Schreiben der Zustandsdatei schlägt fehl WHEN `umzug_fertig_im_klon` läuft THEN bricht der Lauf nicht ab.
- [ ] Test 8: GIVEN die Datenbank der fremden Reise ist nicht lesbar (`sqlite3.Error`) WHEN `arten_uebernehmen` läuft THEN lautet die Antwort 503 `schreiben.dienst.speicher_nicht_erreichbar` ohne Wirkung auf die Zielreise.
- [ ] Test 9: GIVEN die fremde Ablage ist kaputt (`AblageFehler`, `OSError`) WHEN `packliste_uebernehmen` läuft THEN lautet die Antwort 503 `speicher_nicht_erreichbar` ohne Wirkung.
- [ ] Test 10: GIVEN die fremde Reise gibt es nicht oder die Datei ist kein lesbarer Text WHEN `arten_uebernehmen` läuft THEN bleibt es bei der Ablehnung `.2`.
- [ ] Test 11: GIVEN ein Ablagefehler WHEN `fremde_datei` direkt aufgerufen wird THEN wirft sie `FremdNichtLesbar` statt `None` zu liefern (bestehender Test `test_ablagefehler_gibt_saubere_antwort_ohne_wirkung` angepasst).

## Acceptance Criteria

Jedes Kriterium nennt den geplanten Test. Dateien: `engine/tests/test_rueckbau_557.py` (RB) und `engine/tests/test_schreiben_speicher.py` (SP).

- **AC-1:** Given `FR_ABLAGE` fällt mit dem Bauordner zusammen oder liegt darin / When `altbau_entfernen` läuft / Then bleibt alles erhalten, Warnzeile, Exit 0, kein Alarm. (Test 1, RB)
- **AC-2:** Given `FR_KONTEN` oder `FR_KONNEKTOR` liegt im Bauordner / When `altbau_entfernen` läuft / Then bleibt alles erhalten, Warnzeile. (Test 2, RB; je Variable ein Fall)
- **AC-3:** Given Exit 4 und keine Ausgabezeile nennt `<FR_SEITEN>/_bau` / When `umzug_fertig_im_klon` läuft / Then wird `fertig` gesetzt. (Test 3, RB)
- **AC-4:** Given Exit 4 mit Nennung des alten Bauordners oder Exit außerhalb von 0, 3, 4 / When `umzug_fertig_im_klon` oder `altbau_entfernen` läuft / Then bleibt der Zustand, es wird nichts gelöscht. (Tests 4 und 5, RB)
- **AC-5:** Given `FR_SEITEN` nicht betretbar / When `altbau_entfernen` läuft / Then kein Abbruch unter `set -e`, Exit 0. (Test 6, RB)
- **AC-6:** Given die Zustandsdatei lässt sich nicht schreiben / When `umzug_fertig_im_klon` läuft / Then kein Abbruch unter `set -e`. (Test 7, RB)
- **AC-7:** Given beide Funktionen / When sie die Units prüfen / Then nutzen beide dieselbe Hilfsfunktion `units_ohne_altbau` (Test: der Stub von `VF_UNITS` wird von beiden Läufen mit identischem Ergebnis ausgewertet, RB; zusätzlich Textprüfung, dass `units.py pruefen` nur in `units_ohne_altbau` aufgerufen wird).
- **AC-8:** Given die Datenbank ist nicht lesbar / When `arten_uebernehmen` läuft / Then 503 `schreiben.dienst.speicher_nicht_erreichbar`, keine Wirkung, eine Protokollzeile. (Test 8, SP)
- **AC-9:** Given kaputte fremde Ablage oder `OSError` / When `packliste_uebernehmen` läuft / Then 503 `speicher_nicht_erreichbar`, kein 500, keine Wirkung. (Test 9, SP)
- **AC-10:** Given unbekannte Reise oder unbrauchbarer Inhalt / When `arten_uebernehmen` oder `packliste_uebernehmen` läuft / Then bleibt es bei der Ablehnung `.2` (kein Verhaltenswechsel für fachliche Fälle). (Test 10, SP)
- **AC-11:** Given ein Ablagefehler / When `fremde_datei` aufgerufen wird / Then wirft sie `FremdNichtLesbar`; der Text nennt nicht die eigene Reise als Fehlerort. (Test 11, SP)
- **AC-12:** Given die Änderungen / When `docs/betrieb.md` und der Kommentar der Vorlage gelesen werden / Then kommt „Bauordner mit `.git`“ nicht mehr vor, Schutzbedingungen nennen Ablage, Konten und Konnektor. (Textprüfung in RB)
- **AC-13:** Given die vollständige Testsuite / When sie läuft / Then ist sie grün (`engine/.venv/bin/python -m pytest -q -n 3 engine/tests`), `ALARMSTELLEN` und die Textkataloge sind unverändert, und die Instanz-Tests laufen vor dem Vorspulen mit dem Branch ohne Fehler (Hinweis: 503 statt 422 im Speicherfehlerfall).

## Definition of Done

- [ ] Alle Acceptance Criteria AC-1 bis AC-13 erfüllt.
- [ ] `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün; Pflichtprüfungen der CI grün.
- [ ] Tests der Instanz vor dem Vorspulen mit dem Branch grün.
- [ ] Doku (`docs/betrieb.md`, Kommentar in `betrieb/vorlagen/schreiben.service`) im Ist-Zustand.
- [ ] #639 mit Nachweisen geschlossen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Nacharbeit innerhalb bestehender Entscheidungen (ADR-0009 Reisespeicher, Spec #557); kein neues Muster, kein Formatwechsel, keine neue Schnittstelle.

## Changelog

- 2026-11-23: Initial spec created
