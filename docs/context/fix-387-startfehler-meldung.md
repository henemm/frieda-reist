# Context: fix-387-startfehler-meldung

## Request Summary
Rest von #387: Bricht das Skript der Reiseseite beim Start ab, zeigt sie heute einen leeren Bildschirm. Sie soll eine sichtbare Meldung mit „Neu laden“ zeigen. Dazu ein Teil-Check der Überwachung, der die Seite im Browser lädt (Issue in henemm-infra), und die Abnahme nach dem Ausliefern.

## Schon erledigt (auf main)
- Code-Fehler behoben (f5470f6), roter Test und Folgetest (63200cc, 1461286).
- `engine/tests/test_seite_startet.py` (jede Seite jeder Beispielreise), `test_startreihenfolge.py` (Startanweisungen gegen später angelegte const/let).
- Startprobe beim Veröffentlichen: `betrieb/startprobe.mjs`, `engine/tests/test_startprobe.py` (#395); `docs/betrieb.md` Zeile 158.

## Related Files
| File | Relevance |
|------|-----------|
| engine/vorlage.html (Z. 994 body, 1016 Leaflet, 1019 Hauptskript, 1022 `const TEXTE`) | Hier fehlt der Fänger für Startfehler; `TEXTE` und `T()` stehen erst im Hauptskript, sind bei einem Startfehler evtl. nicht nutzbar |
| engine/bauen.py (Z. 1331–1347) | Ersetzt Platzhalter `/*__DATEN__*/null`, `/*__TEXTE__*/null`; Ort, um die Meldung je Sprache einzusetzen |
| engine/texte_de.py, texte_en.py (`seite.fehler.*`, ~Z. 376) | Textkatalog je Sprache; neue Schlüssel `seite.fehler.start…` in beiden |
| engine/tests/test_texte.py, docs/sprachen.md | Regeln für Schlüssel, Pseudo-Sprache, Ausnahmelisten (dürfen nur kürzer werden) |
| engine/tests/test_seite_startet.py, seiten_start.mjs | Vorbild für einen Browsertest an beiden Beispielreisen |
| betrieb/startprobe.mjs | Erkennt Seitenfehler und leere Seite; muss die neue Meldung als Fehler werten (Meldung sichtbar = Start gescheitert) |
| ~/henemm-infra/scripts/monitor.sh (`check_frieda_seiten`, Z. 2029) | Prüft nur HTTP 200; Teil-Check „Seite im Browser laden“ gehört als Issue und Umsetzung dorthin |
| docs/design.md, Kopfkommentar der Vorlage | Neuer Baustein „Startfehler-Meldung“ ist dort einzutragen (ADR-0002) |

## Existing Patterns
- Sichtbare Texte nur im Katalog (ADR-0006), nie im Code; Seite holt sie über `T("schlüssel")`.
- Meldungen der Hülle: `.hinweis.glas` Blöcke im Kopf (`#neu`, `#offline`); Vorbild für Gestaltung.
- Baustein-Regel: neuer Baustein in Kopfkommentar, Stile, Bausteinseite, `docs/design.md`.

## Offene Entwurfsfrage (für die Analyse)
Der Fänger muss auch dann greifen, wenn das Hauptskript früh abbricht, und darf nicht vom Hauptskript abhängen. Ein kleines eigenes Skript vor dem Hauptskript (`error` und `unhandledrejection`) mit dem Text je Sprache, den `bauen.py` einsetzt, ist der naheliegende Weg. Der Text muss aus dem Katalog kommen, nicht aus dem Code. Die Meldung muss sich vom normalen Zustand unterscheiden lassen, damit die Startprobe sie als Fehler wertet.

## Dependencies
- Upstream: Katalog, bauen.py, Pseudo-Sprache der Tests.
- Downstream: jede gebaute Reiseseite, Service Worker (Seite wird gecacht), Startprobe, Browsertests.

## Risks & Considerations
- Der Fänger darf nicht bei harmlosen Fehlern (Netz, Karte, Rückmeldedienst) die ganze Seite überdecken: nur Fehler vor Ende des Starts melden.
- Beide Beispielreisen prüfen (Wanderung und Stadtwochenende), auch Reise ohne Pläne.
- Cache: Neue Seite kommt über den Service Worker erst mit dem Wechsel der Version.
- Teil-Check der Überwachung läuft im Infra-Repo; vorher an der Last des Servers messen (Browser auf dem Server, Entprellung wie die anderen Teil-Checks).

## Analyse (Phase 2)

### Entscheidung
Ein kleines eigenes Skript direkt vor dem Hauptskript fängt `error` und `unhandledrejection`, solange der Start nicht beendet ist, und zeigt dann die Meldung mit „Neu laden“.

- **Text aus dem Katalog:** neue Schlüssel `seite.fehler.start_titel` und `seite.fehler.start_neu_laden` in `texte_de.py` und `texte_en.py`. `bauen.py` setzt einen Platzhalter `/*__STARTFEHLER__*/null` mit den beiden Texten je Sprache ein (kleiner Ausschnitt, nicht der ganze Katalog). Die Sprache kommt aus `<html lang>` (Sprache der Reise); die persönliche Wahl liegt im Hauptskript und ist beim Startfehler nicht erreichbar. Zurückfallen auf die erste Sprache, wenn unbekannt.
- **Ende des Starts:** Das Hauptskript setzt als letzte Anweisung `window.__startFertig = true`. Fehler danach (Netz, Karte, Rückmeldedienst) bleiben unbeachtet. Ein Fehler beim Registrieren des Service Workers liegt hinter der Marke und ist harmlos.
- **Meldung:** Element `#startfehler` (`role="alert"`, Stil `.hinweis.glas`, Knopf „Neu laden“ ruft `location.reload()`), wird vom Fänger erzeugt, nicht im festen HTML (kein Eingriff in Seiten ohne Fehler). Eigene Stile stehen im Fänger-`<style>` oder in der Vorlage-CSS (Baustein der Ebene Molekül); Eintrag in Kopfkommentar, Bausteinseite, `docs/design.md`.
- **Startprobe:** wertet ein sichtbares `#startfehler` als Fehler („Startfehler-Meldung sichtbar“), zusätzlich zur leeren Seite.

### Tests (rot zuerst)
1. Browsertest an beiden Beispielreisen: Seite laden, im Hauptskript einen Fehler erzwingen (Skript vor dem Laden ändern) → Meldung sichtbar, Knopf „Neu laden“ vorhanden, Text in der Sprache der Reise; Wanderung und Stadtwochenende.
2. Gesunde Seite: `#startfehler` fehlt; Fehler nach Start (`setTimeout(() => {throw …})`) zeigt keine Meldung.
3. Katalogtests (`test_texte.py`): neue Schlüssel in allen Sprachen und in der Pseudo-Sprache; Ausnahmelisten nicht verlängern.
4. `test_startprobe.py`: Probe wird rot bei Seite mit Startfehler-Meldung.
5. Bau-Test: Platzhalter genau einmal, Ausschnitt enthält alle Sprachen.

### Service Worker / Cache
Die neue Seite kommt über den Wechsel der Version; kein Handschritt. Reisedaten unverändert, also keine Umstellung in `neu.py nachziehen`.

### Teil-Check Überwachung
Eigenes Issue in `henemm/henemm-infra` (Teil-Check „Seite im Browser laden“ in `monitor.sh`, Warnung statt Alarm, entprellt; vorher Last des Servers messen, höchstens alle paar Stunden). Wiederverwendung von `betrieb/startprobe.mjs`. Dieses Issue (#387) bleibt offen, bis der Check läuft und die Abnahme nach dem Ausliefern erfolgt ist.

### Abnahme nach dem Ausliefern
Echte Reiseseite im Browser laden und eine Reise ohne Pläne (Stadtwochenende-artig) ebenso; Meldung selbst per erzwungenem Fehler an einer Testreise zeigen, nicht an echten Reisen.

### Risiken
- Fänger darf nicht selbst fehlschlagen: nur `textContent`/`createElement`, kein Zugriff auf `D` oder `TEXTE`.
- `error`-Ereignisse von Fremdskripten ohne Quelle („Script error.“) zählen ebenfalls, solange der Start läuft: gewollt.
- Entwurf der Meldung (Aussehen, Wortlaut) vor dem Bauen als Artefakt zeigen (Regel „Erst zeigen, dann bauen“).
