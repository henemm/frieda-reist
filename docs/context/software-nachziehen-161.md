# Context: Neue Software automatisch ins Reisen-Repo nachziehen (#161)

## Request Summary
Nach jedem Merge auf `main` dieses Repos musste jemand im Reisen-Repo einer Instanz das Submodul `frieda/` von Hand nachziehen. Ein Workflow im Reisen-Repo erledigt das inzwischen zeitgesteuert, nur bei grünen Tests. Offen sind drei Teile: eine allgemeine Vorlage hier im Repo, ein Fehler im Workflow der Instanz (das Issue bei roten Tests entsteht nie) und die Überwachung durch den Monitor der Instanz. Der Product Owner hat am 31.10.2026 entschieden, dass alle drei Teile in dieser Sitzung erledigt werden, auch die in den anderen Repos.

## Stand (belegt)
- Der Workflow der Instanz läuft alle 30 Minuten und lässt sich von Hand starten. Er zieht nur vorwärts nach, es läuft immer nur ein Lauf gleichzeitig, und er schreibt mit der Bot-Adresse. Der erste Lauf war grün.
- Fehler: Der Testschritt hat kein `continue-on-error`. Sind die Tests rot, endet der Job dort. Der Schritt „Issue bei Testfehler“ (Bedingung `steps.tests.outcome == 'failure'`) läuft deshalb nie.
- Der Commit-Text nennt nur den Betreff des neuesten Commits. Das Issue verlangt dagegen den neuen Stand und alle Commits seit dem alten.
- Die Wiederholschleife (`git pull --rebase && git push`, drei Versuche) bricht ein gescheitertes Rebase nicht ab. Versuch 2 und 3 laufen dann in einem halb fertigen Rebase.
- Der Monitor der Instanz läuft als root, der Bauordner gehört dem Dienstbenutzer. Der Monitor darf dort nichts schreiben, also auch kein `git fetch`. Den eingebundenen Stand liest er aus der HEAD-Datei unter `.git/modules/frieda`.
- PRs werden lokal vorgespult und danach gepusht. Ein Commit ist beim Ankommen auf `main` darum oft schon Stunden alt. Am Alter des ältesten fehlenden Commits gemessen, käme der Alarm sofort. Deshalb merkt sich der Check selbst, seit wann ein Rückstand besteht, und zwar je eingebundenem Stand.

## Related Files
| File | Relevance |
|------|-----------|
| `betrieb/` | Ort der neuen Vorlage `software-nachziehen.yml` |
| `docs/betrieb.md` | Abschnitte „Überwachung“ und „Neue Instanz einrichten“ |
| `engine/tests/test_betrieb.py` | Tests des Betriebs; neuer Test für die Vorlage |
| Reisen-Repo der Instanz: `.github/workflows/software-nachziehen.yml` | laufende Fassung, bekommt dieselben Korrekturen |
| Monitor der Instanz (eigenes Repo) | neuer Teil-Check: Software-Stand im Bauordner höchstens 6 h hinter `main` |

## Existing Patterns
- Vorlagen für den Betrieb liegen allgemein in `betrieb/` (etwa `einstellungen.beispiel`, `vorlagen/`), die Werte einer Instanz stehen nur in deren Reisen-Repo.
- Teil-Checks statt Heartbeats, Meldung nur bei einer Zustandsänderung, nicht kritisch.

## Risks & Considerations
- Wettlauf mit dem Schreibweg, der laufend auf `main` des Reisen-Repos schreibt: Vor jedem Push wird neu geholt. Ein Push wird nie erzwungen.
- Das Repo ist öffentlich: Die Vorlage nennt keine Instanz, keinen Server und keine Pfade.
