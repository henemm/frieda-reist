# Context: fix-539-gesund-vorgemerkt

## Request Summary
Die Bereitschaftsprüfung `/gesund` des Konnektors fiel am 12.11.2026 auf 503, nachdem eine Reise zur Löschung vorgemerkt
wurde (#381). Ihre Seite ist weg, ihr Eintrag in `seiten.json` bleibt. Ziel: vorgemerkte Reisen zählen für die
Bereitschaft nicht mit (#539). Live entstört durch Entfernen des Eintrags der Prüfreise.

## Related Files
| File | Relevance |
|------|-----------|
| engine/konnektor.py `gesund()` | zählt jede Reise aus `seitenlinks()` und verlangt `daten(r)` |
| engine/konten.py `vorgemerkte_reisen()` | Menge vorgemerkter und entfernter Reisen, nur lesend, ohne Datenbank leer |
| engine/konnektor.py Z. ~2218, ~3041 | übrige Wege behandeln vorgemerkte Reisen schon „wie nicht vorhanden“ |
| betrieb/veroeffentlichen.sh `vorgemerkte_entfernen` | entfernt die Seite, nicht den Eintrag in seiten.json |
| engine/tests/test_konnektor.py `test_gesund_ohne_token` | bestehender Test der Bereitschaft |

## Existing Patterns
- Vorgemerkte Reisen werden im Konnektor über `konten.vorgemerkte_reisen()` / `konten.reise_vorgemerkt()` ausgeblendet.

## Dependencies
- Upstream: `seitenlinks()`, `daten()`, `konten.vorgemerkte_reisen()`
- Downstream: nginx-Ort `/gesund`, BetterStack-Monitor, deploy.sh-Bereitschaftsprüfung, monitor.sh

## Existing Specs
- docs/specs zu #381 (Löschen von Reise und Konto)

## Risks & Considerations
- Sind alle Reisen vorgemerkt, bleibt 503 (keine freigeschaltete Reise) — gewollt, wie bisher ohne Reise.
- Aufräumen des Links selbst (nginx-Baustein, seiten.json) gehört zu #527, nicht hierher.

## Stand
- Roter Test liegt schon (nicht eingecheckt) in engine/tests/test_konnektor.py: `test_gesund_ueberspringt_zur_loeschung_vorgemerkte_reise`. Vorgesehene Korrektur in `gesund()`: `reisen = set(seitenlinks()) - konten.vorgemerkte_reisen()`.

## Analysis

### Type
Bug (Ursache bestätigt, Störung live bereits behoben)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/konnektor.py `gesund()` | MODIFY | `reisen = set(seitenlinks()) - konten.vorgemerkte_reisen()`; Docstring nennt den Ausschluss |
| engine/tests/test_konnektor.py | MODIFY | `test_gesund_ueberspringt_zur_loeschung_vorgemerkte_reise` (liegt rot vor) |

### Scope Assessment
- Files: 2
- Estimated LoC: +2/-1 (Code), +15 (Test)
- Risk Level: LOW

### Technical Approach
`gesund()` zieht die Menge aus `konten.vorgemerkte_reisen()` (vorgemerkt und schon entfernt) von den Reisen aus
`seiten.json` ab, genau wie die übrigen Wege des Konnektors vorgemerkte Reisen „wie nicht vorhanden“ behandeln.
`konten` ist im Konnektor schon importiert; ohne Kontendatenbank liefert die Funktion eine leere Menge, Verhalten
dann unverändert. Bleibt nach dem Abzug keine Reise übrig: 503 wie bisher ohne Reise (gewollt).
Eine fehlende Seite einer nicht vorgemerkten Reise bleibt ein Fehler (503) — der Test prüft das mit.

Geprüft und nicht betroffen:
- Rückmeldedienst `/<reise>/gesund` prüft nur die Ablage einer Reise, deploy.sh ruft ihn für die gerade
  veröffentlichte Reise (die nicht vorgemerkt ist).
- henemm-infra monitor.sh liest seiten.json nicht; die Überwachung läuft über den BetterStack-Monitor auf `/gesund`.
- Aufräumen von seiten.json und nginx-Baustein bleibt bei #527.

### Dependencies
- `konten.vorgemerkte_reisen()` (nur lesend, legt keine Datenbank an), `seitenlinks()`, `daten()`.
- Konsumenten von `/gesund`: nginx, BetterStack, deploy.sh (`bereit`), keine Formatänderung der Antwort.
- Kein Formatwechsel der Reisedaten → kein `neu.py nachziehen`; keine Instanz-Schnittstelle ändert sich.

### Lücke (Ursache statt Symptom)
Kein Test verband Löschen (#381) mit der Bereitschaft. Der neue Test schließt das.

### Open Questions
- keine
