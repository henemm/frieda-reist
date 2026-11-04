# Context: Altformen entfernen (#267, Teil 3 von #215)

## Request Summary
Mitgeschleppte Altformen aus Engine und Konnektor entfernen, aber nur dort, wo keine Reise sie mehr nutzt oder die Software die Umstellung selbst mitbringt (Product Owner, 2.11.2026: keine Handarbeit im Betrieb).

## Befund an den Daten (3.11.2026, lesend gegen <Reisen-Repo>/reisen und die Beispielreisen)
| Altform | Genutzt? | Folge |
|---|---|---|
| Alte Form ohne `reise.yaml` (`Reise.alt`) | Nein, alle 6 echten und beide Beispielreisen haben `reise.yaml` | entfernen, fehlende Datei = Baufehler |
| Bestandssprache `de` ohne `sprache` | Ja, 4 von 6 echten Reisen (<Reise G>, <Reise J>, <Reise S>, <Testreise>) | erst automatisch umstellen (`neu.py nachziehen`), dann Fallback entfernen |
| Schlüssel `typ` statt `art` | Nein (kein `typ:` in routen.yaml der echten Reisen); `neu.py nachziehen` schreibt `typ` schon in `art` um (Zeile 433–449) | Lesepfad in `routen.py` (`art_von`, Nacht) und `neu.py` kann fallen; ein Rest bleibt, wenn eine Instanz alte Reisen hat: nachziehen bleibt die Umstellung |
| Merkmalswert als Skalar | Nein (0 Skalare) | Lesepfad in `schreiben.py` 1002–1004 und `routen.py` prüfen |
| Merkmalswert als Liste | Ja (<Reise G>, 14), aber das ist die reguläre Form „Wert je Datum“, keine Altform | bleibt |
| `varianten_titel` | Ja (<Reise J>) | bleibt |

## Related Files
| File | Relevance |
|------|-----------|
| engine/reise.py | `Reise.alt`-Zweige (Zeilen 353–570), `sprache()`/`BESTAND_REISE`, Docstring |
| engine/bauen.py 286–296 | lädt reise.yaml nur, wenn sie existiert; muss sonst abbrechen |
| engine/texte.py 17–18, texte_de.py/texte_en.py | `BESTAND_REISE`, `pruefung.reise.2` |
| engine/neu.py 425–512 | `nachziehen`: hier gehört die Umstellung `sprache` hinein (idempotent) |
| engine/schreiben.py 1002, 1998 | Merkmalswert skalar/Liste, `BESTAND_REISE` bei Einstellungen |
| engine/routen.py 828, 1198 | `typ` gelesen |
| betrieb/ (Nachziehen-Workflow, #168) | ruft `neu.py nachziehen` automatisch auf |
| engine/tests/test_neu.py, test_bauen.py, test_routen.py | Tests der Pfade |

## Existing Patterns
- Umstellung beim Nachziehen: `neu.py nachziehen` ist idempotent und läuft automatisch im Workflow „Software nachziehen“ (#168); `typ → art` ist das Vorbild.
- Fehlertexte laufen über den Katalog (ADR-0006), Tests prüfen Schlüssel statt Wortlaut (`meldet`).

## Risks & Considerations
- Fällt der Fallback `de`, bevor die Reisen umgestellt sind, wird die Veröffentlichung für vier Reisen rot. Reihenfolge: Umstellung zuerst (eigener PR), Fallback danach.
- Die Datei-Änderung in den echten Reisen entsteht durch das Nachziehen im Reisen-Repo, nicht von Hand.
- `schreiben.py`, `neu.py`, `konnektor.py` sind Dateien von Spur B: Sitzung B vor dem Anfassen informieren.
- Die Suite braucht ~20 Minuten (CI auf dem vorgespulten Commit): kleine PRs bündeln.

## Aufteilung
1. PR a: alte Form ohne reise.yaml entfernen (reise.py, bauen.py, Texte).
2. PR b: `nachziehen` trägt `sprache: de` ein (idempotent, Test); Veröffentlichen zieht die Reisen nach.
3. PR c: Fallback `BESTAND_REISE` entfernen, wenn alle Reisen umgestellt sind (fehlendes `sprache` = Fehler).
4. PR d: Lesepfade `typ` und Skalar entfernen, soweit der Befund es erlaubt.

## Analysis

### Type
Feature (Aufräumen mit automatischer Umstellung)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/reise.py | MODIFY | `Reise.alt`-Zweige (353, 365–366, 379, 419, 480, 491, 549–570) entfernen; `sprache()` ohne `BESTAND_REISE` (221–228, 389) |
| engine/bauen.py | MODIFY | fehlende `reise.yaml` = Baufehler (Katalogtext) |
| engine/texte.py, texte_de.py, texte_en.py | MODIFY | `BESTAND_REISE` (Z. 18, 144) entfällt in PR c; neuer Fehlertext für fehlende Datei/`sprache` |
| engine/neu.py | MODIFY | `nachziehen` (425–512) trägt `sprache: de` ein, idempotent; Z. 500 `BESTAND_REISE` ersetzen; `typ`-Lesepfade (313–365) prüfen |
| engine/schreiben.py | MODIFY | Z. 1998–1999 `BESTAND_REISE`; Z. 1002–1004 Skalar-Lesepfad prüfen (Spur B) |
| engine/routen.py | MODIFY | Z. 135 `STUFEN_WORTE` nutzt `BESTAND_REISE`; `typ`-Lesepfad (16, 828, 1198) |
| engine/tests/test_neu.py, test_bauen.py, test_routen.py, test_reise.py | MODIFY | Tests je Pfad; Umstellungstest für `sprache` |
| docs/betrieb.md, docs/sprachen.md | MODIFY | Hinweis auf Fallback streichen |

### Scope Assessment
- Files: ca. 10–12 (4 PRs)
- Estimated LoC: +120/-250
- Risk Level: MEDIUM (Fallback `de` zu früh entfernt → Veröffentlichung rot für 4 echte Reisen)

### Technical Approach
Vier PRs, strikt in dieser Reihenfolge:
1. PR a: Alte Form ohne `reise.yaml` entfernen (nicht genutzt, kein Umstellungsbedarf).
2. PR b: `nachziehen` schreibt `sprache: de` bei fehlendem Feld (idempotent, Test, Meldung wie bei `typ→art`). Software-nachziehen-Workflow (#168) stellt die 4 Reisen im Reisen-Repo selbst um.
3. PR c: erst NACH nachgewiesener Umstellung aller Reisen (lesend prüfen): `BESTAND_REISE`-Fallback entfernen, fehlendes `sprache` = Fehler mit Katalogtext. `STUFEN_WORTE` (routen.py:135) braucht dann eine feste Wortquelle (z. B. Vorgabesprache) – in der Spec klären.
4. PR d: Lesepfade `typ` und Skalar nur entfernen, wo `nachziehen` sie schon umstellt und Befund 0 Treffer zeigt; Skalar-Pfad in `schreiben.py` 1002 bleibt, wenn er nur Eingabe-Komfort ist (prüfen).

### Dependencies
- `neu.py nachziehen` ← Workflow „Software nachziehen“ (#168) ← Reisen-Repo `<Reisen-Repo>`
- `BESTAND_REISE`: texte.py, reise.py, routen.py, schreiben.py, neu.py
- Spur B berührt `schreiben.py`, `neu.py`, `konnektor.py`: Sitzung B vorher informieren (ListAgents/SendMessage).
- Tests der einbindenden Instanzen laufen vor dem Vorspulen (Meldungstexte/Dateiformat ändern sich).

### Open Questions
- [ ] PR c: Woher bezieht `STUFEN_WORTE` die Wörter, wenn `BESTAND_REISE` fällt (Vorgabesprache oder je Reise)?
- [ ] Soll der Skalar-Lesepfad in `schreiben.py:1002` fallen oder bleibt er als tolerante Eingabe?
- [ ] PR c erst nach Nachweis, dass der Workflow die 4 Reisen umgestellt hat (Reihenfolge b → c als Abnahmebedingung).
