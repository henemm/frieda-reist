# Context: Schreibweg – Zeitgrenzen, Sperre je Reise, Priorität, Ablehnungsgrund (#118–#121)

## Request Summary
Die Issues #118 (Zeitgrenzen abstimmen), #119 (Sperre je Reise, Wartezeit begrenzen), #120 (Veröffentlichen mit niedriger Priorität) und #121 (Ablehnungsgrund ins Protokoll) umsetzen.

## Related Files
| File | Relevance |
|------|-----------|
| engine/schreiben.py | `ZEIT_ANWENDEN`, `anwenden_extern` (Sperre, Timeout), `anwenden` (Ablehnung), `Schreiber.vorbereiten` (gemeinsame Arbeitskopie), `veroeffentlichen_anstossen` (Popen) |
| betrieb/vorlagen/nginx-konnektor.conf | `proxy_read_timeout 30s` – Obergrenze für Sperre + Vorgang |
| betrieb/vorlagen/veroeffentlichen.service | Nice/IOScheduling ergänzt |
| docs/betrieb.md | Abschnitt „Zeitgrenzen und Sperren“ ergänzt, Veröffentlichen um Priorität |
| engine/tests/test_schreiben.py | neue Tests (Sperre je Reise, Protokoll, 504, Zeitgrenzen gegen nginx) |
| engine/tests/test_betrieb.py | Prüfung der Dienst-Vorlage auf Nice/IOScheduling |

## Existing Patterns
- Schreibweg: HTTP-Dienst, ruft pro Vorgang `schreiben.py anwenden` als Unterprozess in der Arbeitskopie.
- Ablehnungen sind `Ablehnung`-Exceptions, Antwort 422.
- Tests mit Fixture `repo` (erfundenes Origin, Beispielreise).

## Dependencies
- Upstream: git, flock, subprocess, `instanz.wert("FR_SPERREN")`.
- Downstream: Konnektor (`konnektor.py`) über `KN_SCHREIBDIENST`, nginx, systemd-Vorlagen über `einrichten.sh`.

## Existing Specs
- `docs/adr/0001-kern.md` (Prüfstelle; asynchrones Schreiben wäre erst daran zu messen – nicht Teil dieser Umsetzung).

## Stand (bereits umgesetzt, uncommitted)
- #118: ZEIT_ANWENDEN=20, ZEIT_SPERRE=3; Test gegen nginx-Grenze.
- #119: Sperre (flock, nicht blockierend mit Frist) und Arbeitskopie je Reise, 429 bei belegter Sperre.
- #121: Protokollzeile `Abgelehnt <werkzeug> 422: <Grund>` (200 Zeichen).
- #120: Service-Vorlage, Doku, Test fertig. **Offen:** `nice`/`ionice` vor dem Popen in `veroeffentlichen_anstossen` (Edit wurde vom Workflow-Hook blockiert).

## Risks & Considerations
- Grund-Texte können Eingabewerte enthalten (gekürzt auf 200 Zeichen, keine Prüfung auf Inhalte).
- Arbeitskopie je Reise: parallele `git fetch`/`worktree add` im selben Repo; Push-Konflikte fängt `hochladen` per Rebase ab.
- ZEIT_ANWENDEN=20 s könnte bei sehr großen Reisen (Probebau) knapp sein.
- Asynchrone Schreibvorgänge (Rest von #118) separat als Issue, vorher an ADR-0001 messen.

## Analysis

### Type
Feature (Betriebsverbesserung; #118 Zwischenlösung, #119, #120, #121)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/schreiben.py | MODIFY | Zeitgrenzen 20/3 s, Sperre und Arbeitskopie je Reise, 429, Protokollzeilen; **offen:** `nice`/`ionice` in `veroeffentlichen_anstossen`, Zeitgrenze für `vorbereiten()` |
| betrieb/vorlagen/veroeffentlichen.service | MODIFY | Nice/IOScheduling (fertig) |
| docs/betrieb.md | MODIFY | Abschnitt „Zeitgrenzen und Sperren“, Priorität (fertig) |
| engine/tests/test_schreiben.py | MODIFY | Tests Sperre, Protokoll, 504, Grenze gegen nginx (fertig) |
| engine/tests/test_betrieb.py | MODIFY | Test Dienst-Vorlage (fertig) |

### Scope Assessment
- Files: 5 (bereits geändert, uncommitted)
- Estimated LoC: +85/-8 bisher, offen etwa +10
- Risk Level: MEDIUM (zentraler Schreibweg, aber klar abgegrenzt, gut getestet)

### Technical Approach
Die Zwischenlösung aus #118 ist umgesetzt. Beim Prüfen der Gesamtlaufzeit zeigt sich eine Lücke:
- `vorbereiten()` (git fetch, worktree add, submodule update) läuft **innerhalb der Sperre ohne Zeitgrenze**. Die Gleichung „3 s Sperre + 20 s Vorgang < 30 s“ gilt deshalb nur für Sperre und Unterprozess, nicht für den ganzen Schreibvorgang. Ein hängender Fetch erzeugt weiter einen 504 von nginx ohne Meldung.
- `hochladen` (push, rebase) läuft im Unterprozess und fällt unter die 20 s; Push-Konflikte sind abgefangen.
Empfehlung: `git()` in `vorbereiten` mit einer Zeitgrenze versehen (Rest der Gesamtzeit) und bei Überschreitung dieselbe 504-Meldung geben; Test dazu. Danach `nice`/`ionice` beim Popen (#120), vorher den Workflow-Hook beachten (Edit erst in Phase Implement). Asynchrone Schreibvorgänge bleiben ein eigenes Issue und werden vorher an ADR-0001 gemessen.

### Dependencies
git, flock, subprocess, `instanz.wert("FR_SPERREN")`; nginx-Vorlage des Konnektors (30 s); systemd-Vorlage `veroeffentlichen.service`.

### Open Questions
- [ ] Soll die Gesamtzeit (Sperre + Vorbereiten + Vorgang) als eine Frist von etwa 27 s gelten, oder bekommt `vorbereiten` eine eigene Grenze (z. B. 5 s)?
- [ ] Sind 20 s für große Reisen (Probebau) ausreichend? Messwerte aus dem Betrieb fehlen.
- [ ] Issue für asynchrones Schreiben anlegen (Messung an ADR-0001)?
