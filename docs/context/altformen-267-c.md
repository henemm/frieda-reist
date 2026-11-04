# Context: altformen-267-c (Teil c1 von #267, Teil 3 von #215)

## Request Summary
`routen.STUFEN_WORTE` entfällt (AC-8). Die Konstante hängt an `texte.BESTAND_REISE` und muss weg, bevor `BESTAND_REISE` (Paket c2,
AC-7, AC-9) fallen kann. Zuschnitt (Product Owner, 4.11.2026): c1 = nur `STUFEN_WORTE`, c2 = `BESTAND_REISE`. Dieses Paket ist c1.
Die Spec liegt vor: `docs/specs/betrieb/altformen-entfernen-267.md`, Entscheidung 1 und AC-8.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/routen.py` Z. 290 | Definition `STUFEN_WORTE = texte.gruppe(texte.BESTAND_REISE, "schreiben.stufe")` |
| `engine/routen.py` Z. 293–305 (`stufe_satz`) | Einziger Leser: `s in STUFEN_WORTE and s != "aus"`; die Wörter holt `texte.satz("schreiben.stufe." + s)` in der Sprache der Person |
| `engine/routen.py` Z. 289 (`STUFEN`) | Sprachneutrale Schlüssel `pflicht, empfohlen, angeboten, aus`: ersetzt die Mengenprüfung |
| `engine/routen.py` Z. 319–329 (`stufe_schluessel`) | Liest die Wörter je Sprache aus dem Katalog, hängt nicht an `STUFEN_WORTE`; bleibt unverändert |
| `engine/tests/test_texte.py` Z. 135 | Prüft den Inhalt der Konstante auf Deutsch; entfällt, ersetzt durch Test auf `stufe_satz` in beiden Sprachen |
| `engine/tests/test_texte.py` Z. 490–491, `test_routen.py` Z. 929 | Tests zu `stufe_schluessel`; bleiben grün |
| `engine/schreiben.py` Z. 129–131 | `stufe_satz` reicht an `routen.stufe_satz` durch; unverändert |

Keine andere Stelle in `engine/`, `betrieb/`, `werkzeuge/` oder `docs/` nennt `STUFEN_WORTE` außer dem Test, der Spec und den Unterlagen zu #267.

## Existing Patterns
- Sprachneutrale Schlüssel im Code, Wörter nur im Katalog (ADR-0006: der Code kennt keine Sprache beim Namen).
- Sätze über `texte.satz(...)` in der Sprache der Person; Tests prüfen je Sprache über die Umschaltung der Sprache der Person.

## Dependencies
- Upstream: `STUFEN`, `texte.satz`, Katalogschlüssel `schreiben.stufe.*`, `schreiben.stufe_mit_wert`.
- Downstream: `schreiben.stufe_satz` (Antworten des Konnektors zu Merkmalen). Verhalten für Menschen bleibt gleich: „nötig (pflicht)“ usw.

## Existing Specs
- `docs/specs/betrieb/altformen-entfernen-267.md` (Entscheidung 1, AC-8, Abschnitt „PR c“).

## Risks & Considerations
- **Verhalten gleich halten:** `STUFEN_WORTE` enthielt genau die vier Schlüssel (Test Z. 135). `s in STUFEN` ist damit gleichbedeutend; der Test auf `stufe_satz` sichert das in Deutsch und Englisch.
- **Reihenfolge:** c1 braucht den Nachweis b → c nicht (keine Reise betroffen). c2 danach, der Nachweis liegt in #267 vor.
- **Umfang:** 1 Code-Datei (3 Zeilen), 1 Testdatei. Weit unter den Grenzen.

## Analysis

### Type
Feature (Aufräumen von Altformen, Teil c1 von #267)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/routen.py | MODIFY | Zeile 290 `STUFEN_WORTE` löschen; in `stufe_satz` (Z. 300) `s in STUFEN` statt `s in STUFEN_WORTE`; Kommentar zu Z. 289 ggf. kürzen |
| engine/tests/test_texte.py | MODIFY | Z. 135 (Inhalt der Konstante auf Deutsch) entfällt; neuer Test: `stufe_satz` liefert „nötig (pflicht)“, „gut zu wissen (empfohlen)“, „zusätzlich (angeboten)“, „aus“ und „gilt nicht“ je Typ in Deutsch und Englisch, unbekannter Wert bleibt `Satz(str(s))` |

Gegenprobe (am 4.11.2026 per grep): `STUFEN_WORTE` kommt im Code nur in routen.py Z. 290 und Z. 300 vor, in den Tests nur in test_texte.py Z. 135; sonst nur in Spec, Context und Artefakten.

### Scope Assessment
- Files: 2
- Estimated LoC: +12/-2
- Risk Level: LOW (ein Leser, Menge der vier Schlüssel ist identisch mit `STUFEN`)

### Technical Approach
Konstante löschen, Mengenprüfung auf `STUFEN` umstellen (Spec, Entscheidung 1). Kein neues Modul, keine Katalogänderung; `stufe_schluessel` und `schreiben.stufe_satz` bleiben unberührt. Nachweis des gleichen Verhaltens durch den neuen Test in beiden Sprachen (RED: Test auf `STUFEN_WORTE` nicht mehr vorhanden / Konstante noch da; GREEN nach dem Löschen). Kein Format der Reisedaten betroffen, deshalb keine Umstellung in `neu.py nachziehen`.

### Dependencies
- Upstream: `STUFEN`, `texte.satz`, Schlüssel `schreiben.stufe.*`, `schreiben.stufe_mit_wert`.
- Downstream: `schreiben.stufe_satz` (Antworten des Konnektors); c2 (`BESTAND_REISE`) setzt dieses Paket voraus.
- Kein Instanz-Test nötig: keine Meldungstexte, Schnittstellen, Umgebungswerte oder Dateiformate ändern sich.

### Open Questions
- [x] Keine. Zuschnitt c1/c2 hat der Product Owner am 4.11.2026 festgelegt, Wortlaut der Stufen bleibt gleich.
