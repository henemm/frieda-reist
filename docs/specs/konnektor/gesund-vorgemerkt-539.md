---
entity_id: gesund-vorgemerkt-539
type: bugfix
created: 2026-11-12
updated: 2026-11-12
status: draft
workflow: fix-539-gesund-vorgemerkt
version: "1.0"
tags: [konnektor, bereitschaft, loeschen, konten, m7]
---

# Bereitschaft `/gesund` überspringt zur Löschung vorgemerkte Reisen (#539)

## Approval

- [ ] Approved

## Purpose

Die Bereitschaftsprüfung `/gesund` des Konnektors verlangt Daten für jede Reise aus `seiten.json`. Wird eine Reise zur Löschung vorgemerkt (#381), verschwindet ihre Seite, ihr Eintrag in `seiten.json` bleibt, und die Prüfung fällt auf 503, obwohl der Dienst gesund ist. Vorgemerkte Reisen zählen für die Bereitschaft künftig nicht mehr mit, wie sie in den übrigen Wegen des Konnektors schon als nicht vorhanden gelten.

## Ziel und Abgrenzung

- **Im Scope:**
  - In `gesund()` wird die Menge der zu prüfenden Reisen um `konten.vorgemerkte_reisen()` (vorgemerkt und schon entfernt) verringert; der Docstring nennt den Ausschluss.
  - Bleibt nach dem Abzug keine Reise übrig, antwortet `/gesund` wie bisher ohne Reise mit 503 (keine freigeschaltete Reise, gewollt).
  - Eine nicht vorgemerkte Reise mit fehlender Seite bleibt ein Fehler (503).
  - Antwortformat von `/gesund` bleibt unverändert (`{"gesund": true|false}`).
- **Nicht im Scope:** Aufräumen von `seiten.json` und des Nginx-Bausteins nach dem Entfernen einer Reise (gehört zu #527); der Rückmeldedienst-Pfad `/<reise>/gesund` (prüft nur die Ablage der veröffentlichten, nicht vorgemerkten Reise); Überwachung in `monitor.sh` (liest `seiten.json` nicht).
- **Kern (ADR-0001):** Berührt weder Arten, Merkmale noch Grundformen und nichts Reisespezifisches; reine Betriebskorrektur der Bereitschaft, wirkt für alle Reisen und Instanzen gleich. Beide Beispielreisen verhalten sich gleich, solange sie nicht vorgemerkt sind.
- **Instanzen und Datenformat:** Keine Formatänderung der Reisedaten, daher kein Eintrag in `neu.py nachziehen`. Keine Schnittstelle zu Instanzen ändert sich (Antwort gleich), zusätzliche Instanztests sind nicht nötig.
- **Ursache der Lücke:** Kein Test verband Löschen (#381) mit der Bereitschaft. Der neue Test schließt sie. Die Störung vom 12.11.2026 ist live bereits entstört (Eintrag der Prüfreise entfernt).

## Source

- **File:** `engine/konnektor.py`
- **Identifier:** `def gesund`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `konten.vorgemerkte_reisen()` | Code (`engine/konten.py`) | Menge vorgemerkter und entfernter Reisen; nur lesend, legt keine Datenbank an, ohne Datenbank leere Menge |
| `seitenlinks()` | Code (`engine/konnektor.py`) | Reisen aus `seiten.json` |
| `daten()` | Code (`engine/konnektor.py`) | Reisedaten je Reise; Fehler bei fehlender Seite führt zu 503 |
| nginx-Ort `/gesund`, BetterStack-Monitor, `betrieb/deploy.sh` (Bereitschaftsprüfung) | Konsumenten | Antwortformat und Statuscodes bleiben gleich |
| #381, #527 | Issues | Löschen von Reise und Konto; Aufräumen von Link und Baustein |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konnektor.py` | MODIFY | `gesund()`: `reisen = set(seitenlinks()) - konten.vorgemerkte_reisen()`; Docstring ergänzt |
| `engine/tests/test_konnektor.py` | MODIFY | Test `test_gesund_ueberspringt_zur_loeschung_vorgemerkte_reise` (liegt bereits rot vor) |

### Estimated Changes

- Files: 2
- LoC: +2/-1 (Code), +15 (Test)
- Risiko: niedrig

## Implementation Details

1. `konten` ist im Konnektor bereits importiert. In `gesund()` wird die Reiseliste aus `seitenlinks()` um `konten.vorgemerkte_reisen()` verringert, bevor `daten(r)` je Reise verlangt wird.
2. Ohne Kontendatenbank liefert `vorgemerkte_reisen()` eine leere Menge; das Verhalten ist dann unverändert.
3. Ist die verbleibende Menge leer, gilt wie bisher „keine Reise“ und damit 503.
4. Der Docstring von `gesund()` nennt, dass zur Löschung vorgemerkte Reisen nicht mitzählen, weil ihre Seite entfernt wird.

## Test Plan

### Automated Tests (TDD RED)

- [ ] `test_gesund_ueberspringt_zur_loeschung_vorgemerkte_reise` (vorhanden, rot): GIVEN `seiten.json` mit `beispielreise` und einer Reise ohne Seite und ohne Vormerk WHEN `/gesund` abgefragt wird THEN 503 `{"gesund": false}`.
- [ ] Im selben Test: GIVEN dieselbe Lage und die zweite Reise ist per `loeschung_vormerken` vorgemerkt WHEN `/gesund` abgefragt wird THEN 200 `{"gesund": true}`.
- [ ] Im selben Test: GIVEN `seiten.json` enthält nur die vorgemerkte Reise WHEN `/gesund` abgefragt wird THEN 503 `{"gesund": false}`.
- [ ] Bestehend, bleibt grün: `test_gesund_ohne_token` (Bereitschaft ohne Anmeldung, Antwortformat unverändert).

## Acceptance Criteria

- **AC-1:** Given eine zur Löschung vorgemerkte Reise ohne Seite, die noch in `seiten.json` steht, und mindestens eine gesunde freigeschaltete Reise / When `/gesund` abgefragt wird / Then 200 mit `{"gesund": true}`. Test: `test_gesund_ueberspringt_zur_loeschung_vorgemerkte_reise`.
- **AC-2:** Given eine nicht vorgemerkte Reise in `seiten.json` ohne Seite / When `/gesund` abgefragt wird / Then 503 mit `{"gesund": false}` (fehlende Seite bleibt ein Fehler). Test: derselbe, erster Schritt.
- **AC-3:** Given `seiten.json` enthält nur vorgemerkte Reisen / When `/gesund` abgefragt wird / Then 503 mit `{"gesund": false}`. Test: derselbe, letzter Schritt.
- **AC-4:** Given keine Kontendatenbank vorhanden / When `/gesund` abgefragt wird / Then Verhalten und Antwortformat wie zuvor; `test_gesund_ohne_token` bleibt grün.
- **AC-5:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen.

## Definition of Done

- [ ] Roter Test bestätigt, danach Korrektur, Test grün
- [ ] Gesamtlauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün
- [ ] Pflichtprüfungen der CI grün, ausgeliefert, Konnektor auf dem Server neu gestartet und `/gesund` geprüft
- [ ] Issue #539 mit Abschlusskommentar geschlossen

## Known Limitations

- Der verwaiste Eintrag in `seiten.json` und der Nginx-Baustein bleiben bestehen, bis #527 sie aufräumt; die Bereitschaft ignoriert sie bis dahin.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Fehlerkorrektur im Sinne der bestehenden Behandlung vorgemerkter Reisen (#381); keine neue Grundform, kein neues Datenformat, keine Schnittstellenänderung.

## Changelog

- 2026-11-12: Initial spec created (Entwurf) für #539.
