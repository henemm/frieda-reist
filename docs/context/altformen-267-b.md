# Context: altformen-267-b (Teil b von #267, Teil 3 von #215)

## Request Summary
`neu.py nachziehen` trägt in jeder `reise.yaml`, in der `sprache` fehlt oder leer ist, `sprache: de` ein, idempotent, mit
Meldung in der Sprache der Reise. Vorbedingung für PR c (`texte.BESTAND_REISE` entfällt). Die Spec liegt fertig vor:
`docs/specs/betrieb/altformen-entfernen-267.md`, Abschnitt „PR b“, AC-3, AC-4, AC-5, AC-12.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/neu.py` Z. 543–632 (`nachziehen`) | Hier kommt der neue Schritt hinein; Meldungen sammelt die Liste `meldungen`. |
| `engine/neu.py` Z. 659–694 (`reste_nachziehen`) | Liest `sprache_von`; arbeitet zeilenweise auf `reise.yaml` (Kopfkommentar). Muss nach dem Eintragen laufen. |
| `engine/neu.py` Z. 697–760 (`eckdaten_nachziehen`) | Vorbild: `sb.reise_yaml_laden` / `reise_yaml_speichern` (ruamel), `insert` an fester Stelle, Meldung per `texte.t(sprache, …)`. |
| `engine/neu.py` Z. 182–196 (`anlegen`) | Reihenfolge der Schlüssel bei neuen Reisen: titel, untertitel, ziel, pfad, **sprache**, zeitraum. |
| `engine/schreiben.py` Z. 2603–2614 | `reise_yaml_laden` / `reise_yaml_speichern` (Rundlauf mit ruamel, Kommentare bleiben). |
| `engine/reise.py` Z. 220–240 | `sprache_von` (Regex auf `^sprache:`; ohne Feld `BESTAND_REISE`) und `sprache_pruefen`. |
| `engine/texte.py` Z. 17–18 | `VORGABE_REISE = "en"`, `BESTAND_REISE = "de"`. |
| `engine/texte_de.py`, `engine/texte_en.py` | Neuer Schlüssel `inhalt.nachziehen.sprache_eingetragen` in beiden Katalogen. |
| `engine/tests/test_umstellung_250.py` | Muster der Tests (Anlegen, `nachziehen`, zweiter Lauf leer, jede Sprache). |
| `engine/tests/test_neu.py` Z. 306 ff. | `test_nachziehen_nur_schluessel`: bestehende Erwartungen an die Meldungsliste. |

## Existing Patterns
- Umstellungen laufen in `nachziehen` mit `schreiben=False` als Probelauf (nur melden) und sind idempotent (zweiter Lauf `== []`).
- Meldungen der älteren Schritte sind teils englische Festtexte, die neueren (`pruefung.neu.nachziehen.*`) kommen aus dem
  Katalog in der Sprache der Reise. Die Spec verlangt den Katalog (`inhalt.nachziehen.sprache_eingetragen`).
- Schlüssel per `roh.insert(index, key, wert)` an der Stelle, die zur Reihenfolge von `anlegen` passt (hinter `pfad`).
- `sb.skalar(...)` baut Werte in der Form der Datei.

## Dependencies
- Upstream: `ruamel` über `schreiben.yaml_rund`, `reise.sprache_von`, `texte.t`.
- Downstream: Workflow „Software nachziehen“ (`betrieb/software-nachziehen.sh`/`.yml`) ruft `neu.py nachziehen` je Reise auf und
  committet das Ergebnis in das Reisen-Repo; `Reise.sprache()` (reise.py Z. 385) liest das Feld; PR c baut darauf auf.

## Existing Specs
- `docs/specs/betrieb/altformen-entfernen-267.md` (PR b, AC-3 bis AC-5, AC-12), `docs/specs/betrieb/software-wechsel-ohne-handarbeit-250.md`.

## Risks & Considerations
- **Reihenfolge:** Eintragen vor `eckdaten_nachziehen` und `reste_nachziehen`. Der Wert `de` entspricht dem bisherigen Bestand, an deren Ergebnis ändert sich nichts.
- **Idempotenz / Byte-Gleichheit:** Steht `sprache` schon, darf die Datei nicht angefasst werden (kein Speichern ohne Änderung, auch kein ruamel-Rundlauf, der Formatierung verschiebt).
- **Fremde Eingaben:** Eine unbekannte Sprache bleibt unberührt, der Bau meldet sie weiter. „Leer“ heißt fehlend, `None` oder `""`.
- **Bestehende Tests:** Tests mit einer `reise.yaml` ohne `sprache`, die `nachziehen` aufrufen und die Meldungsliste prüfen, bekommen eine Zeile mehr; sie sind anzupassen (Erwartung, keine Abschwächung).
- **Ohne `reise.yaml`** gibt es nichts einzutragen (seit PR a bricht schon der Bau ab).
- **Meldungssprache:** Die Meldung wird in der Sprache `de` ausgegeben, weil genau diese eingetragen wird.
- **Auslieferung (AC-5):** Der Bot-Lauf an der Instanz ist manueller Nachweis nach dem Vorspulen (Commit des Bots, lesende Prüfung); er blockiert PR b nicht.

## Analysis

### Type
Feature (Umstellung beim Nachziehen, PR b von #267; keine Fehlerbehebung)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/neu.py | MODIFY | Neue Funktion `sprache_nachziehen(reise_dir, schreiben)`: trägt `sprache: de` ein; in `nachziehen` vor `eckdaten_nachziehen`/`reste_nachziehen` aufgerufen (Meldung in die Liste, Probelauf schreibt nicht). |
| engine/texte_de.py | MODIFY | Schlüssel `inhalt.nachziehen.sprache_eingetragen` |
| engine/texte_en.py | MODIFY | derselbe Schlüssel (Pflicht in allen Sprachen, `test_texte.py`) |
| engine/tests/test_umstellung_267.py (oder test_neu.py) | CREATE/MODIFY | Fehlt/leer/`None` → Eintrag + Meldung (de, en-Reise nicht betroffen); zweiter Lauf `[]` und Datei byte-gleich; Probelauf schreibt nicht; unbekannte Sprache unberührt; Kommentare bleiben; beide Beispielreisen |
| engine/tests/test_neu.py | MODIFY | Erwartungen der Meldungslisten bei `reise.yaml` ohne `sprache` um eine Zeile ergänzen (Erwartung, nicht abschwächen) |

### Scope Assessment
- Files: 4–5
- Estimated LoC: +70/-0 (davon ca. 45 Tests)
- Risk Level: LOW

### Technical Approach
- Neue Funktion nach dem Vorbild von `eckdaten_nachziehen`: `reise.yaml` mit `sb.reise_yaml_laden` lesen, nur bei fehlendem/leerem (`None`, `""`) Feld `roh.insert(<Index hinter "pfad">, "sprache", "de")`, speichern, Meldung `texte.t("de", "inhalt.nachziehen.sprache_eingetragen")`.
- **Keine Änderung der Datei ohne Bedarf:** Prüfung vorab auf dem Rohtext/Rundlauf-Ergebnis; steht das Feld mit gültigem oder unbekanntem Wert, wird nicht gespeichert (AC-4, Byte-Gleichheit). Unbekannte Sprache bleibt unberührt, der Bau meldet sie weiter.
- Position: hinter `pfad` (Reihenfolge wie in `anlegen`: titel, untertitel, ziel, pfad, sprache, zeitraum); fehlt `pfad`, hinter dem letzten der bekannten Vorgänger, sonst ans Ende der Kopfschlüssel.
- Aufruf in `nachziehen` unabhängig von `reise.json` (also vor dem `cfg_pfad`-Block), damit auch Reisen ohne `reise.json` umgestellt werden; vor `eckdaten_nachziehen` und `reste_nachziehen` (beide lesen `sprache_von`). Ohne `reise.yaml`: nichts tun.
- Verhalten ändert sich nicht: `de` ist bisher schon der Bestandswert (`BESTAND_REISE`); PR c entfernt dann den Rückfall.

### Dependencies
- Upstream: `schreiben.reise_yaml_laden/-speichern` (ruamel), `reise.sprache_von`, `texte.t`.
- Downstream: Workflow „Software nachziehen“ (Bot-Lauf an den vier Reisen ohne `sprache`, AC-5, manueller Nachweis nach dem Vorspulen); PR c (`BESTAND_REISE` entfällt) baut darauf auf.
- Beim Vorspulen: Ändert das Meldungstexte/Dateiformat der Instanz → Tests der einbindenden Instanzen mit dem Branch laufen lassen (CLAUDE.md).

### Befunde, die gegen den Plan sprechen
- Keine gegen den Ansatz. Aber eine Kante: `sprache_von` nutzt `re.search(r"^sprache:\s*['\"]?([A-Za-z-]+)", …, re.M)`. Bei `sprache:` ohne Wert (leere Zeile) frisst `\s*` den Zeilenumbruch und liest das erste Wort der Folgezeile als Sprache. Deshalb muss `sprache_nachziehen` das Feld über YAML (ruamel) prüfen, nicht über `sprache_von`. Der leere Wert wird dabei durch `de` ersetzt (nicht zusätzlich eingefügt, sonst doppelter Schlüssel). Optional kleiner Test, dass `reste_nachziehen` danach nicht mehr falsch liest.

### Open Questions
- [ ] Keine, die den PO betreffen. Die Spec (AC-3/4/5/12) ist eindeutig; Meldungstext wird in der Spec-Phase festgelegt.
