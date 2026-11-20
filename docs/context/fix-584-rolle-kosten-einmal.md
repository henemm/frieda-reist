# Context: fix-584-rolle-kosten-einmal

## Request Summary
`neu.nachziehen` setzt bei jedem Lauf `rolle: kosten` am Merkmal `preis` (Typ geld) jeder Aufenthalts-Art ohne Rolle. Eine bewusst rollenlose Art (Beispielreise: Herberge, Preis pro Person) wird so bei jedem Software-Wechsel überschrieben, und `nachziehen` ist an der Beispielreise nicht idempotent. Ziel (#584): Die Umstellung wirkt nur auf den alten Stand ohne Rollen-Konzept; ein zweiter Lauf an der Beispielreise ändert keine Datei.

## Related Files
| File | Relevance |
|------|-----------|
| engine/neu.py (`nachziehen`, Block „arten.yaml: rolle kosten …“, ca. Z. 1125–1139; Docstring Z. 1048–1060) | Die zu ändernde Umstellung |
| engine/schreiben.py Z. 826–833 (`merkmal_definieren`) | Konnektor kann eine Rolle entfernen (`rolle: keine` → Schlüssel `rolle` fällt weg). Genau diese bewusste Entscheidung überschreibt `nachziehen` beim nächsten Veröffentlichen |
| engine/konnektor.py Z. 2966 | Enum der Rolle im Werkzeug attribute_define: kosten, summe, hero, keine |
| engine/routen.py Z. 464 (`ROLLEN`) | Alle Rollen: kosten, summe, hero, nummer, alias, sorte, osm, trinkbar, oeffnung, bezug |
| betrieb/veroeffentlichen.sh Z. 283–301 | Veröffentlichen ruft `neu.py nachziehen-speicher` für jede Reise auf (also nach jedem Software-Wechsel) |
| beispiel/reisen/beispielreise/plan/arten.yaml | Herberge bewusst ohne Rolle (Kopfkommentar); andere Arten tragen kosten, hero, nummer, alias, bezug, sorte |
| engine/artvorlagen/de.yaml, en.yaml | Vorlagen (ADR-0011) bringen `rolle: kosten` am Preis schon mit |
| engine/reisevorlage/*/plan/arten.yaml | Neue Reise startet mit `arten: {}` |
| engine/tests/test_neu.py `test_nachziehen_nur_schluessel` (Z. 306 ff.) | Altstand-Test: entfernt nur `, rolle: kosten` und erwartet die Meldung „arten.yaml hotel: attribute preis gets rolle kosten“ |
| engine/tests/test_bilder.py `test_nachziehen_aendert_die_beispielreise_nicht_mehr` | Prüft bis jetzt nur Bilddateien; Kommentar verweist auf #584 für volle Idempotenz |
| engine/tests/test_umstellung_267.py `test_beispielreisen_melden_nichts_zur_sprache` | Docstring nennt die offene Umstellung „herberge: rolle kosten“ als eigenen Befund (= #584) |

## Existing Patterns
- Andere Schritte von `nachziehen` sind von Natur aus idempotent, weil sie einen alten Schlüssel erkennen (typ → art, bereich → art, buchung: → B-…). Der Rollen-Schritt erkennt den alten Stand nicht, sondern das Fehlen eines Werts, das auch eine bewusste Entscheidung sein kann.
- Kein Formatmarker („Schema-Version“) in den Reisedaten; Umstellungen erkennen den Altstand am Inhalt.

## Dependencies
- Upstream: `schreiben.arten_laden`, `arten_speichern` (ruamel, erhält Kommentare nur teilweise: Kopfkommentar wird ersetzt, Fluss-Maps werden Block-Maps).
- Downstream: `nachziehen_speicher` (Veröffentlichen jeder Reise), `neu.py nachziehen` als Befehl, Tests oben.

## Analyse (Summe 2, Kontext und Analyse in einem Durchgang)
Die Rolle `kosten` kam mit 7cce6d3 (29.10.2026) zusammen mit dem Rollen-Konzept überhaupt. Vorher hatte keine Art eine Rolle. Seitdem läuft `nachziehen` bei jedem Veröffentlichen über jede Reise; alle Reisen der Instanz sind also längst umgestellt.

Optionen:
- **A: Altstand am Fehlen jeder Rolle erkennen.** Umstellung nur, wenn in `arten.yaml` kein Merkmal irgendeiner Art (merkmale und buchung_merkmale) eine Rolle trägt. Klein, im Muster der anderen Schritte. Restfall: Eine Reise ganz ohne Rollen, die das einzige `kosten` bewusst entfernt hat, bekäme es wieder.
- **B: Schritt ganz entfernen.** Alle Reisen sind umgestellt; ein Reisestand von vor dem 29.10. kommt nicht mehr herein (Exporte und Sicherungen sind jünger). Kein Restfall, aber eine sehr alte Kopie würde ohne Kostensumme gebaut (harmlos, mit attribute_define nachholbar). Weicht von der Regel ab, Umstellungen dauerhaft mitzuführen.
- **C: Marker in den Reisedaten** (z. B. erledigte Umstellungen in reise.json). Neues Formatelement für einen Schritt; überdimensioniert.

Empfehlung für die Spec: A. Der Restfall von A lässt sich schließen, wenn die Umstellung zusätzlich nur greift, solange die Reise auch noch keine anderen Spuren des neuen Stands trägt — das wird in der Spec entschieden.

## Risks & Considerations
- Der Altstand-Test `test_nachziehen_nur_schluessel` entfernt nur `, rolle: kosten`; mit Option A muss er alle Rollen entfernen, sonst greift die Umstellung nicht mehr.
- Neue Reisen, deren Aufenthalts-Art einen Preis ohne Rolle definiert, bekommen heute still `kosten` beim nächsten Veröffentlichen. Nach dem Fix (A) nur noch, wenn die Reise gar keine Rolle hat; mit B nie. Das entspricht ADR-0001/0011 (Arten gehören der Reise, Vorlagen bringen die Rolle mit).
- Datenformat-Schritt, läuft beim Veröffentlichen über alle Reisen: Tests der Instanz vor dem Ausliefern mitlaufen lassen (Meldungstext unverändert).

## Analysis

### Type
Bug (Umstellung in `nachziehen` nicht idempotent, überschreibt eine bewusste Entscheidung der Reise)

### Messung (20.11.2026)
`neu.nachziehen` auf Kopien beider Beispielreisen (betrieb=False):
- Beispielreise: einzige Meldung `arten.yaml herberge: attribute preis gets rolle kosten`, einzige geänderte Datei `plan/arten.yaml`.
- Stadtwochenende: keine Meldung, keine Datei geändert.
Der Rollen-Schritt ist also der einzige Grund, warum die Beispielreise nicht idempotent ist. Nach dem Fix kann `test_nachziehen_aendert_die_beispielreise_nicht_mehr` (test_bilder.py) auf alle Dateien erweitert werden.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/neu.py (`nachziehen`, Block „arten.yaml: rolle kosten …“; Docstring) | MODIFY | Umstellung nur, wenn keine Art der Reise (merkmale und buchung_merkmale) irgendeine Rolle trägt (Altstand vor dem Rollen-Konzept); Docstring entsprechend |
| engine/tests/test_neu.py `test_nachziehen_nur_schluessel` | MODIFY | Altstand ohne jede Rolle herstellen (alle `rolle: …`, Fluss- und Blockform), nicht nur `, rolle: kosten`; Erwartungen (hotel und herberge bekommen kosten, zweiter Lauf leer) bleiben |
| engine/tests/test_neu.py (neu) | CREATE test | Reise mit Rollen und einer Aufenthalts-Art mit Preis ohne Rolle: nachziehen meldet nichts, arten.yaml unverändert (Herberge der Beispielreise) |
| engine/tests/test_bilder.py `test_nachziehen_aendert_die_beispielreise_nicht_mehr` | MODIFY | volle Idempotenz: alle Dateien der Beispielreise bleiben byte-gleich; Kommentar „#584“ entfällt |
| engine/tests/test_umstellung_267.py (Docstring) | MODIFY | Hinweis auf die offene Umstellung „herberge: rolle kosten“ entfernen, falls sie dort als Ausnahme behandelt wird |

### Scope Assessment
- Files: 3–4 (1 Code, 2–3 Tests)
- Estimated LoC: +25/-10
- Risk Level: LOW — ein Schritt einer Umstellung wird enger; Meldungstext unverändert; alle Reisen der Instanz tragen seit 29.10. Rollen und sind vom Schritt künftig nicht mehr betroffen.

### Technical Approach
Option A (Empfehlung): Altstand am Fehlen jeder Rolle in `arten.yaml` erkennen, im Muster der übrigen Schritte (Altstand am Inhalt erkennen, kein Formatmarker). Prüfung über alle Arten, `merkmale` und `buchung_merkmale`, jede Rolle aus `routen.ROLLEN` zählt. Restfall (Reise ganz ohne Rollen, die das einzige `kosten` bewusst entfernt hat) wird bewusst hingenommen: Eine solche Reise hätte nach dem 29.10. keine Rolle mehr, auch keine aus Vorlagen (ADR-0011 bringen `kosten` mit) — praktisch ausgeschlossen; kein zusätzliches Kriterium, um die Regel einfach zu halten.
B (Schritt entfernen) verworfen: widerspricht der Regel, Umstellungen dauerhaft mitzuführen (#250). C (Marker) überdimensioniert.

### Dependencies
`schreiben.arten_laden`/`arten_speichern`; `nachziehen_speicher` (Veröffentlichen) ruft `nachziehen(ordner, betrieb=False)`; Meldungstext bleibt, daher keine Änderung für Instanz-Tests nötig — sie laufen trotzdem vor dem Ausliefern mit (Datenformat-Schritt).

### Open Questions
- keine (Restfall von A in der Spec als bewusst hingenommen festhalten)
