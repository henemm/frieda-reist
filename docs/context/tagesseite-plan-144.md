# Context: tagesseite-plan-144

## Request Summary
Die Tagesseite einer Reise zeigt Nummer und Datum eines Tags aus dem falschen Plan, wenn ein Plan gewählt ist und
daneben ein verworfener Plan mit einer zusätzlichen Nacht besteht. Die Übersicht ist richtig (Issue #144).

## Related Files
| File | Relevance |
|------|-----------|
| engine/vorlage.html, `ansichtTag` (ab Z. 2924) | Sucht den Tag über `R.plaene`: `p = mit.find(PLAN_ZULETZT) \|\| mit[0] \|\| planZu(PLAN_ZULETZT)`, `t` kommt aus `p.tage`. Bei direktem Aufruf ist `mit[0]` der erste Plan der Liste, nicht der gewählte. Ursache. |
| engine/vorlage.html, Z. 889 `PLAN_FEST` | Der vollständig gewählte Plan; Karte und Reiseüberblick richten sich schon danach (Z. 889, 2600, 3111, 3388). Die Tagesseite tut das nicht. |
| engine/vorlage.html, Z. 1266ff., 2373 | Übersicht und Tagesliste nehmen `R.tage` (aktueller Plan), daher richtig. |
| engine/vorlage.html, `ansichtOrt` (Z. 2976) | `p = planZu(PLAN_ZULETZT)` steuert nur den Zurück-Link. Die „Kommt vor in“-Chips tragen den Plannamen („P-A: Tag 8“), sind also je Plan richtig. Voraussichtlich kein Fehler. |
| engine/routen.py, `bauen()` (Z. 1065ff.) | Zählt `nr = i + 1` und das Datum aus dem aktuellen Plan; die Quelle der Wahrheit. `plaene()` (Z. 1168) baut dieselben Felder je Plan. |
| engine/tests/test_tagesseite.py, seiten_tagesseite.mjs | Vorhandener Browser-Test (Playwright) der Tagesseite; Ort für den Regressionstest. |
| beispiel/reisen/beispielreise/plan/routen.yaml (`plaene:` ab Z. 141) | Erfundene Beispielreise mit Plänen; Testgrundlage, wenn nötig ergänzt (als Beispielwert markiert). |

## Existing Patterns
- Ist ein Plan gewählt, ersetzt `PLAN_FEST` die Planauswahl (Karte als Startseite, Reiseüberblick ohne Plannamen).
- Die Vorlage bekommt die Daten als `R` (Reisemodell aus dem Generator); Python rechnet, JavaScript zeigt.

## Dependencies
- Upstream: `R.tage`, `R.plaene`, `R.weitere_tage`, `PLAN_FEST`, `PLAN_ZULETZT`, `planZu`, `alternativen`.
- Downstream: Tagesseiten aller Reisen; Verweise auf Tage (Wahlstellen-Titel, Erinnerungen) nehmen `R.tage`, nicht `ansichtTag`.

## Existing Specs
- Keine Spec zur Tagesseite gefunden, die Plan und Nummer regelt (vor dem Schreiben noch gegen `docs/` prüfen).

## Risks & Considerations
- Solange Pläne noch verglichen werden (kein `PLAN_FEST`), ist die planabhängige Nummer gewollt und darf sich nicht ändern.
- Tage, die nur in einer verworfenen Variante vorkommen (`R.weitere_tage`), brauchen weiter ihren Weg.
- Vorlage gilt für alle Reisen: Änderung braucht Test mit der Beispielreise, keine echten Reisedaten ins öffentliche Repo.
- Die Python-Seite (Fristen, Erinnerungen, Kalenderexport) rechnet aus dem aktuellen Plan; Prüfung der Aufrufer bleibt Teil der Analyse.
- Die Arbeitskopie steht noch auf dem Zweig `worktree-hashed-noodling-crown`; vor dem Festschreiben auf aktuellen `origin/main` aufsetzen (Rebase-Gate).

## Analysis

### Type
Bug (Anzeige, Vorlage). Daten und Konnektor sind richtig; nur die Auswahl des Plans in der Tagesseite ist falsch.

### Ursache (bestätigt im Code)
`ansichtTag` (engine/vorlage.html:2925f.) wählt `p = mit.find(x => x.id === PLAN_ZULETZT) || mit[0] || planZu(PLAN_ZULETZT)`.
`mit` sind alle Pläne, die den Tag enthalten, in Listenreihenfolge. Bei direktem Aufruf (Link, Lesezeichen, Neuladen) ist
`PLAN_ZULETZT` leer, also gewinnt `mit[0]`. Steht ein verworfener Plan vor dem gewählten (oder ist `PLAN_ZULETZT` ein verworfener Plan,
den man vorher angesehen hat), kommen `nr` und `datum` aus dem verworfenen Plan. Das Blättern (← / →) hängt ebenfalls an `p.tage` und ist
damit mitbetroffen. `PLAN_FEST` (Z. 889) wird hier nicht beachtet, obwohl der Kommentar in Z. 2938 („Ist ein Plan gewählt, nennt der Tag keine Pläne“) davon ausgeht.
Hinweis zum Test: Mit der Beispielreise steht P-A (später fest) vor P-B; der Fehler zeigt sich nur, wenn der verworfene Plan in der Liste VOR dem gewählten steht oder `PLAN_ZULETZT` auf ihn zeigt.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/vorlage.html (`ansichtTag`) | MODIFY | Ist `PLAN_FEST` gesetzt und enthält er den Tag: `p = PLAN_FEST`. Sonst bisherige Suche (Vergleichsphase, Tage nur in verworfenen Varianten) |
| engine/vorlage.html (`ansichtOrt`, „Kommt vor in“, Z. 2985) | MODIFY (klein) | Ist ein Plan gewählt, nur dessen Tage aufführen (wie die Tagesseite keine Pläne nennt); Zurück-Link nimmt `PLAN_FEST` statt `PLAN_ZULETZT` |
| engine/tests/test_tagesseite.py, seiten_tagesseite.mjs | MODIFY | Regressionstest im Browser (Direktaufruf der Tagesseiten) |
| beispiel/reisen/beispielreise/plan/routen.yaml | MODIFY (nur wenn nötig) | Zwei erfundene Zusatzpläne als Testgrundlage; besser im Test per Kopie ergänzen (wie `plan_fest`), damit die Demo unverändert bleibt |

### Prüfung der weiteren Stellen (Akzeptanzkriterium des Issues)
| Stelle | Ergebnis |
|--------|----------|
| Übersicht, Tagesliste (Z. 1266ff., 2373) | `R.tage` = aktueller Plan, richtig |
| Wahlstellen-Titel, Verweistexte (`rueckmeldungen.py` ~1065) | `R.tage`, richtig |
| Konnektor (`konnektor.py` 635, 949) | Pläne einzeln mit eigener Tagesliste, je Plan beschriftet, richtig |
| Erinnerungen, Fristen, Wächter (`waechter.py`) | rechnen aus Reisedaten, nicht aus `ansichtTag`; kein Planbezug, richtig |
| Kalenderexport | Aufrufer von `R.tage`/aktuellem Plan; in der Spec-Phase noch einmal gezielt grep-prüfen (`kalender`) |
| Orte („Kommt vor in“) | Chips tragen den Plannamen, also je Plan richtig; bei gewähltem Plan aber irreführend (nennt verworfene Pläne) → kleine Angleichung |

### Scope Assessment
- Files: 2–3 (Vorlage, Test, ggf. Beispielreise)
- Estimated LoC: +10/-3 Vorlage, +50 Test
- Risk Level: LOW — Änderung gilt nur, wenn ein Plan fest gewählt ist; in der Vergleichsphase (kein `PLAN_FEST`) bleibt alles gleich.

### Technical Approach
In `ansichtTag` die Planwahl umstellen: `const p = (PLAN_FEST && PLAN_FEST.tage.some(t => t.id === tid)) ? PLAN_FEST : (mit.find(PLAN_ZULETZT) || mit[0] || planZu(PLAN_ZULETZT))`. Alles Weitere (Kopf, Blättern, Zurück-Link) folgt aus `p`. Kein Eigenbau, keine Python-Änderung. Test: Beispielreise kopieren, Plan A fest, davor einen verworfenen Plan mit zusätzlicher Nacht und einen, der einen Tag weglässt; jede Tagesseite direkt aufrufen und Nummer/Datum gegen die Übersicht prüfen. Der Test muss ohne Fix rot sein.
Gegenbefunde: keine gegen den Plan. Ein Randfall: Sind mehrere Pläne vollständig gewählt, nimmt `PLAN_FEST` den ersten (`find`); das ist bestehendes Verhalten und nicht Teil dieses Fehlers.

### Dependencies
`R.plaene`, `R.tage`, `PLAN_FEST`, `PLAN_ZULETZT`, `planZu`, `alternativen`; Tagesseiten nur mit Baustein „tagesseiten“ (`PLAN_TAGE`).

### Open Questions
- [ ] Soll „Kommt vor in“ auf der Ortsseite bei gewähltem Plan nur den gewählten Plan zeigen? (Empfehlung: ja, gleiche Regel wie Tagesseite; Entscheidung des Product Owners, falls er die Vergleichsansicht dort behalten will.)
- [ ] Kalenderexport vor der Spec noch gezielt auf Planbezug prüfen.
- [ ] Prüfung in einer echten Reise nach dem Veröffentlichen liegt außerhalb dieses Repos (Product Owner/Reise-Repo).
