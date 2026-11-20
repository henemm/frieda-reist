---
entity_id: rolle-kosten-einmal-584
type: bugfix
created: 2026-11-20
updated: 2026-11-20
status: draft
workflow: fix-584-rolle-kosten-einmal
---

# nachziehen setzt rolle kosten nur noch am Altstand (#584)

## Approval

- [ ] Approved

## Purpose

`neu.py nachziehen` soll die Rolle `kosten` am Merkmal `preis` nur an einer Reise ergänzen, die noch aus der Zeit vor dem Rollen-Konzept stammt. Bisher überschreibt der Schritt bei jedem Veröffentlichen auch eine bewusst rollenlose Art (Beispielreise: Herberge) und macht `nachziehen` damit nicht idempotent.

## Source

- **File:** `engine/neu.py`
- **Identifier:** `def nachziehen` (Block „arten.yaml: rolle kosten am Merkmal preis …“ und Docstring)

## Anlass

Die Rolle `kosten` kam am 29.10.2026 zusammen mit dem Rollen-Konzept; vorher trug keine Art eine Rolle. Der Schritt erkennt aber nicht einen alten Schlüssel (wie die anderen Schritte: typ zu art, bereich zu art, buchung zu B-…), sondern das Fehlen eines Werts, und das kann auch eine bewusste Entscheidung sein: Der Konnektor kann eine Rolle entfernen (`attribute_define` mit `rolle: keine`). `veroeffentlichen.sh` ruft `nachziehen-speicher` für jede Reise bei jedem Lauf auf, die Entscheidung würde also überschrieben. Messung am 20.11.2026: An der Beispielreise meldet `nachziehen` jedes Mal „arten.yaml herberge: attribute preis gets rolle kosten“ und ändert `plan/arten.yaml`; am Stadtwochenende nichts.

## Entscheidung (Option A)

Die Umstellung greift nur, wenn in `arten.yaml` keine Art in `merkmale` oder `buchung_merkmale` irgendeine Rolle trägt (jede Rolle aus `routen.ROLLEN` zählt). Das ist der Altstand vor dem Rollen-Konzept, erkannt am Inhalt wie bei den übrigen Schritten; ein Formatmarker kommt nicht dazu.

Verworfen: B (Schritt entfernen) widerspricht der Regel, Umstellungen dauerhaft mitzuführen (#250). C (Marker in den Reisedaten) wäre ein neues Formatelement für einen einzigen Schritt.

Bewusst hingenommener Restfall: Eine Reise, die gar keine Rolle mehr trägt, weil sie das einzige `kosten` bewusst entfernt hat, bekäme es beim nächsten Lauf wieder. Praktisch ausgeschlossen: Vorlagen (ADR-0011) bringen `kosten` am Preis mit, und alle Reisen der Instanz laufen seit dem 29.10.2026 durch den Schritt. Ein zusätzliches Kriterium würde die Regel nur verkomplizieren. Der Meldungstext bleibt unverändert.

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `schreiben.arten_laden`, `schreiben.arten_speichern` | module | Lesen und Schreiben von `plan/arten.yaml` |
| `routen.ROLLEN` | module | Schlüssel dieses dict (Rolle → Typ) zählen als „Rolle vorhanden“ |
| `neu.nachziehen_speicher` | function | Aufruf beim Veröffentlichen je Reise (ruft `nachziehen(ordner, betrieb=False)`; Signatur `nachziehen(reise_dir, strecken_arten=None, schreiben=True, betrieb=True)`) |
| `betrieb/veroeffentlichen.sh` | script | Ruft `nachziehen-speicher`; unverändert |

## Scope

### Affected Files
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/neu.py` | MODIFY | Schritt greift nur ohne jede Rolle in `arten.yaml`; Docstring angepasst |
| `engine/tests/test_neu.py` | MODIFY | `test_nachziehen_nur_schluessel` baut Altstand ohne jede Rolle; neuer Test für Reise mit Rollen |
| `engine/tests/test_bilder.py` | MODIFY | `test_nachziehen_aendert_die_beispielreise_nicht_mehr` vergleicht alle Dateien byte-gleich; Verweis auf #584 entfällt |
| `engine/tests/test_umstellung_267.py` | MODIFY | Docstring: Hinweis auf die offene Umstellung „herberge: rolle kosten“ entfernen |

### Estimated Changes
- Files: 4 (1 Code, 3 Tests)
- LoC: +25/-10

## Implementation Details

Vor der Schleife über die Arten wird einmal geprüft, ob irgendein Merkmal irgendeiner Art (`merkmale` und `buchung_merkmale`) eine Rolle trägt. Ist das so, entfällt der ganze Schritt. Sonst gilt die bisherige Regel unverändert (Aufenthalts-Art, Merkmal `preis`, Typ `geld`, Rolle `kosten`, gleiche Meldung). Der Schritt bleibt idempotent: Nach dem ersten Lauf trägt die Reise eine Rolle, der zweite Lauf überspringt ihn.

Ein Probelauf (`schreiben=False`) meldet wie bisher, schreibt aber nichts.

## Test Plan

### Automated Tests (TDD RED)
- [ ] Test 1: GIVEN ein Altstand der Beispielreise ohne jede Rolle in `arten.yaml` WHEN `nachziehen` läuft THEN meldet es „arten.yaml hotel: attribute preis gets rolle kosten“ (und für Herberge), schreibt `kosten`, und ein zweiter Lauf meldet nichts (`test_nachziehen_nur_schluessel`, angepasst).
- [ ] Test 2: GIVEN eine Reise mit Rollen und einer Aufenthalts-Art mit Preis (Typ geld) ohne Rolle WHEN `nachziehen` läuft THEN keine Meldung zu `arten.yaml`, und `plan/arten.yaml` ist byte-gleich (neu, in `test_neu.py`).
- [ ] Test 3: GIVEN eine Kopie der Beispielreise WHEN `nachziehen` läuft THEN bleiben alle Dateien byte-gleich (`test_nachziehen_aendert_die_beispielreise_nicht_mehr`, erweitert).
- [ ] Test 4: GIVEN eine Kopie des Stadtwochenendes WHEN `nachziehen` läuft THEN keine Meldung und alle Dateien byte-gleich.
- [ ] Test 5: GIVEN Altstand ohne Rollen und `schreiben=False` WHEN `nachziehen` läuft THEN Meldung ja, Datei unverändert.

## Acceptance Criteria

- **AC-1:** Given in `plan/arten.yaml` trägt mindestens ein Merkmal einer Art (in `merkmale` oder `buchung_merkmale`) eine Rolle aus `routen.ROLLEN` / When `nachziehen` läuft / Then setzt es an keiner Art `rolle: kosten` und meldet nichts dazu.
- **AC-2:** Given keine Art trägt eine Rolle (Altstand vor dem Rollen-Konzept) / When `nachziehen` läuft / Then setzt es `rolle: kosten` an `preis` (Typ geld) jeder Aufenthalts-Art, mit der unveränderten Meldung „arten.yaml <art>: attribute preis gets rolle kosten“, und ein zweiter Lauf meldet nichts mehr.
- **AC-3:** Given eine Kopie der Beispielreise oder des Stadtwochenendes / When `nachziehen` läuft / Then bleiben alle Dateien byte-gleich (nicht nur Bilder).
- **AC-4:** Given die bewusst rollenlose Herberge der Beispielreise / When `nachziehen` läuft / Then behält ihr Merkmal `preis` keine Rolle.
- **AC-5:** Given die Änderung ist umgesetzt / When man Docstring und Testkommentare liest / Then beschreibt der Docstring von `nachziehen` die neue Bedingung, und der Hinweis auf die offene Umstellung „herberge: rolle kosten“ in `test_umstellung_267.py` sowie der Verweis auf #584 in `test_bilder.py` sind entfernt.
- **AC-6:** Given der Stand ist fertig und lokal grün / When er auf `main` vorgespult werden soll / Then laufen vorher die Tests des Reisen-Repos der Instanz mit diesem Stand; rot darf nur sein, was schon vorher rot war.

## Definition of Done

- [ ] AC-1 bis AC-6 erfüllt
- [ ] Tests 1 bis 5 grün, volle Testsuite ohne echte Reisen grün
- [ ] Tests der Instanz mit diesem Stand gelaufen
- [ ] Ausgeliefert auf `main`, Issue #584 mit Nachweis geschlossen

## Prüfung gegen ADR-0001 (`docs/adr/0001-kern.md`)

- Frage 1: Die Umstellung gilt für jede Reise gleich und enthält nichts Reisespezifisches; durchgespielt an Beispielreise (Wanderung) und Stadtwochenende.
- Frage 2: Kein neuer Katalog. Die Software setzt weiterhin keine Art voraus; sie überschreibt künftig nur keine Entscheidung der Reise mehr.
- Fragen 3, 4, 6, 9: Keine KI, kein neues Werkzeug (die Tür `attribute_define` mit `rolle: keine` wirkt jetzt dauerhaft), keine Entscheidung betroffen, kein Inhalt in Claude Code.
- Frage 5: Berührt keine Aussagen, also keine Herkunft.
- Frage 7: Keine ID wird vergeben oder gelöscht; die Änderung wird enger, nicht weiter. Das Schreiben läuft wie bisher über `arten_speichern` mit Verlauf.
- Frage 8: Die Seite ist nicht berührt.
- Frage 10: Spec und Docstring; kein ADR nötig.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Enge Fehlerbehebung an einem Umstellungsschritt im Rahmen von ADR-0001 und ADR-0011; Arten und Rollen gehören der Reise, die Software überschreibt sie nicht mehr.

## Changelog

- 2026-11-20: Initial spec created
- 2026-11-20: Definition of Done ergänzt, Signatur von `nachziehen` präzisiert, Acceptance Criteria im Given/When/Then-Format (Validator, Spec-Gate)
