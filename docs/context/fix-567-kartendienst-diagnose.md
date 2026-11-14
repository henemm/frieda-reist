# Context: fix-567-kartendienst-diagnose

## Request Summary
Wackeliger Test `test_kartenpunkte_dienstwahl_an_beiden_beispielreisen` (#567): einmal rot, nicht nachstellbar. Ziel: Den Fehlerfall beobachtbar machen (Protokoll beim stillen Wechsel weg vom eigenen Kartendienst, aussagekräftige Zusicherungen) und den nachweislich unsauberen Test-Stummel `Kaputt` sauber beenden. Stand der Ursachensuche: Issue #567, Kommentar „Ursachensuche, Stand 2“.

## Befund aus dem roten Lauf
- `Done kartenpunkte_holen 200 in 1.1 s`, keine Zeile `Prefetch … skipped`: Vorab-Abruf im Prozess, kein Aushungern (Teilfrist eigen 10 s).
- Eigener Stummel ohne Anfrage → entweder `dienst_waehlen` wählte öffentlich, oder `overpass_eigen` scheiterte schnell und wechselte still (keine Protokollzeile).
- Diagnose (Plugin um `overpass_senden`, Protokoll je Worker): 3 Gesamtläufe `-n 3` und 60 Folgeläufe (`test_kartendienst.py` + Kartentests von `test_schreiben.py`, 4 parallel) grün; Dienstwahl ruft je Lauf 2× im Prozess ab (eigen, dann öffentlich), 1–5 ms.

## Related Files
| File | Relevance |
|------|-----------|
| engine/schreiben.py:2237 `overpass_holen` | Dienstwahl, Teilfrist, Wechsel auf öffentlich |
| engine/schreiben.py:2263 `overpass_eigen` | schluckt jeden Fehler ohne Protokoll → hier Protokollzeile mit Fehlerart |
| engine/schreiben.py:5504 `kartenpunkte_vorab` | Vorbild für Protokollzeilen (`sys.stderr.write(... [:LOG_LAENGE])`, englisch, Fehlerart + gekürzter Text) |
| engine/kartendienst.py `dienst_waehlen`, `abdeckung` | Wahl nach Abdeckung; `abdeckung()` liefert bei Lesefehler still [] |
| engine/tests/test_schreiben.py:2660 `OverpassStummel`, :2973 Dienstwahl-Test | Zusicherungen ohne Diagnose (`assert len(eigen.anfragen) == 1 and …`) |
| engine/tests/test_kartendienst.py:292 `Kaputt` | Faden blockiert in `accept()`, `schliessen()` nur `close()`; Leseschleife dreht endlos bei leerem `recv()`; Fadenzahl im Worker steigt 3 → 9 |
| engine/tests/test_kartendienst.py:217, :330 | bestehende Tests zum Rückfall (AC-6/F001) – Ort für Test der neuen Protokollzeile |
| engine/tests/test_protokolle_ohne_pfade.py | Protokolle/Nachweise ohne Pfade |

## Existing Patterns
- Protokollzeilen des Schreibdienstes: englisch, `sys.stderr.write(f"... {' '.join(f'{type(e).__name__}: {e}'.split())[:LOG_LAENGE]}\n")`; keine Textkatalog-Einträge (nicht sichtbar für Personen).
- Stummel in Tests: `ThreadingHTTPServer` mit `shutdown()` + `server_close()` (sauber); `Kaputt` ist der einzige rohe Socket-Server.
- Diagnose in Zusicherungen: `assert …, a` mit Antwort als Meldung (überall in test_schreiben.py).

## Dependencies
- Upstream: `kartendienst` (Wahl, Stempel), `urllib`, `instanz.wert`.
- Downstream: `overpass_abfragen` (Rückfall im Vorgang), `kartenpunkte_vorab`; Tests in test_kartendienst.py prüfen Rückfall per Anfragezahlen (müssen grün bleiben).

## Existing Specs
- `docs/specs/betrieb/eigener-kartendienst-444.md` – AC-6 Rückfall bei Fehler (keine Aussage zum Protokoll).

## Risks & Considerations
- Protokollzeile darf keine Pfade/Adressen mit Geheimnissen enthalten: nur Fehlerart und gekürzter Text (Adresse ist lokal/Instanz; besser weglassen).
- Ursache bleibt unbelegt: Die Änderung macht das nächste Rot erklärbar, sie behauptet keine Behebung. Issue erst schließen, wenn die Protokollzeile im Betrieb steht und Wiederholungsläufe grün sind.
- `Kaputt` sauber beenden ohne neue Wackler: `shutdown(SHUT_RDWR)` vor `close()`, Faden mit Frist `join`, Leseschleife bricht bei `b""` ab.
- Meldungstexte/Protokoll ändern sich → laut CLAUDE.md vor dem Vorspulen auch Tests der einbindenden Instanz prüfen (Protokollzeile ist neu, kein geänderter Text; geringes Risiko).

## Analysis

### Type
Bug (wackeliger Test, Ursache unbelegt) – Ziel: Beobachtbarkeit herstellen und einen nachgewiesenen Mangel im Test-Stummel beheben; keine behauptete Behebung.

Hinweis zum Vorgehen: Die Investigation (bug-intake) ist im Issue bereits zweimal gelaufen (Zwischenstand und Stand 2, über 8 Gesamtläufe und 240 Einzel-/Folgeläufe). Ein erneuter Intake-Agent würde sie nur wiederholen; die Analyse stützt sich auf den Code-Stand und die Befunde oben.

### Code-Befund
- `overpass_holen` (engine/schreiben.py:2237): Bei `dienst == "eigen"` und `overpass_eigen(...) is None` Wechsel auf öffentlich ohne jede Spur. `overpass_eigen` (:2267) liefert `None` in zwei Fällen: Ausnahme (URLError, HTTPException, TimeoutError, OSError, ValueError) oder Antwort ohne Liste `elements`. Beide Fälle sind heute stumm, auch im Betrieb (ausgefallener eigener Kartendienst bliebe unbemerkt).
- `dienst_waehlen` (kartendienst.py:76) liest `abdeckung.json` bei jedem Aufruf frisch (kein Cache, kein mtime) – die Cache-Vermutung aus dem Issue ist damit ausgeschlossen. `abdeckung()` liefert bei Lesefehler still `[]`.
- Test (test_schreiben.py:2973): erste Zusicherung `len(eigen.anfragen) == 1 and oeffentlich.anfragen == []` ohne Meldung; das rote Ergebnis `0 == 1` sagt nicht, ob der öffentliche Stummel gefragt wurde und welcher Dienst in `a["text"]` steht.
- `Kaputt` (test_kartendienst.py:292): `schliessen()` nur `sock.close()`. Ein Faden, der in `accept()` blockiert, wird unter Linux durch `close()` nicht geweckt; er hält den alten Socket und bleibt hängen (Fadenzahl 3 → 9). CPython liest die Dateinummer des Sockets erst nach Freigabe des GIL unmittelbar vor dem Systemaufruf: ein laufender Faden, der zwischen zwei Verbindungen zurück zu `accept()` geht, kann in einem schmalen Fenster eine bereits geschlossene und neu vergebene Dateinummer erwischen und Verbindungen eines anderen Sockets annehmen. Das passt zum Bild (eigener Stummel ohne Anfrage, schneller Fehler, stiller Wechsel), ist aber nicht belegt und vom Zeitpunkt (71 % des Laufs) eher unwahrscheinlich. Leseschleife dreht endlos bei `recv() == b""`.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/schreiben.py | MODIFY | `overpass_eigen`: beim Scheitern eine Protokollzeile auf stderr (englisch, Muster `kartenpunkte_vorab`): Fehlerart und gekürzter Text (`LOG_LAENGE`), ohne Adresse; ebenso für „Antwort ohne elements“. Kein Textkatalog (nicht sichtbar für Personen). |
| engine/tests/test_kartendienst.py | MODIFY | `Kaputt` sauber beenden: `shutdown(SHUT_RDWR)` vor `close()`, Faden mit Frist `join`, Leseschleifen brechen bei `b""` ab. Neue Zusicherungen: Rückfall-Tests (Kaputt, nicht erreichbar, Antwort ohne elements) prüfen die Protokollzeile (capsys/capfd); Test, dass nach `schliessen()` kein Faden des Stummels weiterläuft. |
| engine/tests/test_schreiben.py | MODIFY | Dienstwahl-Test: Zusicherungen mit Diagnose (beide Anfragelisten, `a["text"]`, eingefangenes stderr via capfd). |
| docs/specs/betrieb/eigener-kartendienst-444.md | MODIFY | AC-6 ergänzen: Rückfall hinterlässt eine Protokollzeile mit Grund. |

### Scope Assessment
- Files: 4
- Estimated LoC: +60/-10
- Risk Level: LOW (eine zusätzliche Protokollzeile im Fehlerpfad; Tests/Stummel)

### Technical Approach
1. Protokollzeile in `overpass_eigen` (nicht in `overpass_holen`), damit beide `None`-Fälle ihre eigene Begründung tragen: z. B. `Own map service failed (URLError: ...), falling back to public` bzw. `Own map service answered without elements, falling back to public`. Ohne Adresse (Instanzdetail), Text einzeilig und auf `LOG_LAENGE` gekürzt.
2. Tests der Protokollzeile in den bestehenden Rückfall-Tests (test_kartendienst.py, AC-6/F001), dazu Prüfung, dass im Erfolgsfall keine Zeile entsteht.
3. Diagnose im Dienstwahl-Test; der Test bleibt sonst unverändert (keine Wiederholung, kein Lockern).
4. `Kaputt` deterministisch beenden; Test, der die Fadenzahl vor/nach misst bzw. `thread.is_alive()` nach `schliessen()` falsch erwartet.
5. Danach Wiederholungsläufe (Gesamtlauf `-n 3` mehrfach, Folgeläufe der Kartentests) grün; Issue offen lassen mit Beobachtungsauftrag, bis die Zeile im Betrieb steht (Schluss nach Spec festlegen).

### Dependencies
- `overpass_abfragen` und `kartenpunkte_vorab` nutzen `overpass_holen` – Verhalten unverändert, nur zusätzliche stderr-Zeile.
- `test_protokolle_ohne_pfade.py` betrifft nur Doku-Nachweise; Protokollzeile enthält keine Pfade.
- Instanz-Tests: Neue Zeile, kein geänderter Meldungstext; dennoch vor dem Ausliefern kurz gegen die Tests der Instanz laufen lassen (CLAUDE.md).

### Open Questions
- Keine Produktfrage. Technische Festlegung: Protokollzeile auf stderr wie die übrigen Zeilen des Schreibdienstes (landet im Dienst-Journal); kein Alarm, kein Monitor-Check (Betriebsüberwachung des eigenen Kartendienstes ist eigenes Thema, ggf. Folge-Issue).
