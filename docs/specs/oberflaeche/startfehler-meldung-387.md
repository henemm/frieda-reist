---
entity_id: startfehler-meldung-387
type: bugfix
created: 2026-11-10
updated: 2026-11-10
status: draft
version: "1.0"
workflow: fix-387-startfehler-meldung
tags: [startfehler, meldung, fänger, startprobe, textkatalog, baustein, service-worker]
test_targets: [engine/vorlage.html, engine/bauen.py, engine/texte_de.py, engine/texte_en.py, engine/tests/texte_xx.py, betrieb/startprobe.mjs, engine/tests/test_startfehler_meldung_387.py, engine/tests/seiten_startfehler_387.mjs, engine/tests/test_startprobe.py, engine/tests/test_texte.py, engine/tests/test_design.py]
---

# Startfehler-Meldung statt leerem Bildschirm (#387, Rest)

Workflow: `fix-387-startfehler-meldung`. Analyse: `docs/context/fix-387-startfehler-meldung.md`.

## GitHub Issue

**Issue:** #387 (dieser Teil ist der Rest von #387; das Issue bleibt offen, bis der Teil-Check der Überwachung läuft und die Abnahme nach dem Ausliefern erfolgt ist)

## Approval

- [ ] Approved

Vorbedingung („Erst zeigen, dann bauen“, CLAUDE.md, #436): Aussehen und Wortlaut der Meldung werden dem Product Owner vor dem Bau als privater Entwurf in einem Claude-Artefakt gezeigt (mit den erfundenen Beispieldaten). Gebaut wird erst nach seiner Zustimmung. Wortlaut-Vorschlag: Titel „Die Seite konnte nicht gestartet werden.“, Knopf „Neu laden“; englisch „The page could not be started.“ und „Reload“.

## Purpose

Bricht das Skript der Reiseseite beim Start ab, zeigt sie heute einen leeren Bildschirm, ohne Hinweis und ohne Ausweg. Die Ursache des ursprünglichen Fehlers ist behoben (f5470f6), dazu gibt es Tests (`test_seite_startet.py`, `test_startreihenfolge.py`) und die Startprobe beim Veröffentlichen (`betrieb/startprobe.mjs`, #395). Es fehlt noch der Teil für die Person vor dem Gerät: Scheitert der Start trotzdem (anderer Browser, unerwarteter Datenstand), soll sie eine verständliche Meldung mit dem Knopf „Neu laden“ sehen.

## Source

- **File:** `engine/vorlage.html` (Körper ab Z. 994, Leaflet Z. 1016, Hauptskript ab Z. 1019 mit `const D`, `const TEXTE`, Skriptende Z. 6101), `engine/bauen.py` (Platzhalter Z. 1339–1347, `texte_fuer_seite()` Z. 1698), `engine/texte_de.py` / `texte_en.py` (`seite.fehler.*`, ca. Z. 376), `betrieb/startprobe.mjs`
- **Identifier:** Platzhalter `/*__DATEN__*/null`, `/*__TEXTE__*/null`; neu `/*__STARTFEHLER__*/null`, `window.__startFertig`, Element `#startfehler`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `docs/adr/0001-kern.md` | ADR | Prüfstelle, unten beantwortet |
| `docs/adr/0002-atomic-design.md` | ADR | Neuer Baustein an vier Stellen eintragen |
| `docs/adr/0006-mehrsprachigkeit.md`, `docs/sprachen.md` | ADR/Anleitung | Texte nur im Katalog, alle Sprachen, Pseudo-Sprache (`engine/tests/texte_xx.py`) |
| `engine/tests/test_seite_startet.py`, `seiten_start.mjs` | Vorbild | Browsertest an beiden Beispielreisen |
| `betrieb/startprobe.mjs`, `engine/tests/test_startprobe.py` | Bestand | Probe beim Veröffentlichen wertet die Meldung als Fehler |
| Service Worker (`engine/sw.vorlage.js`) | Bestand | Neue Seite kommt über den Versionswechsel |

## Scope

### Im Scope

1. Ein kleines eigenes Skript direkt vor dem Hauptskript (nach Leaflet und Grundkarte, vor `const D`) fängt `error` und `unhandledrejection`, solange `window.__startFertig` nicht `true` ist.
2. Das Hauptskript setzt `window.__startFertig = true` als letzte Anweisung. Fehler danach (Netz, Karte, Rückmeldedienst, Service Worker) bleiben unbeachtet.
3. Der Fänger erzeugt das Element `#startfehler` (`role="alert"`, Klassen `.hinweis.glas`) mit Titel und Knopf „Neu laden“ (`location.reload()`).
4. Texte aus dem Katalog: neue Schlüssel `seite.fehler.start_titel` und `seite.fehler.start_neu_laden` in allen `texte_*.py`. `bauen.py` setzt den Platzhalter `/*__STARTFEHLER__*/null` mit einem Ausschnitt dieser beiden Texte für alle Sprachen ein. Die Sprache kommt aus `<html lang>` (Sprache der Reise), unbekannt: erste Sprache des Ausschnitts.
5. Neuer Baustein „Startfehler-Meldung“ (Ebene Molekül): Kopfkommentar der Vorlage, Stile, Bausteinseite, `docs/design.md`.
6. `betrieb/startprobe.mjs` wertet ein sichtbares `#startfehler` als Fehler („Startfehler-Meldung sichtbar“), zusätzlich zur leeren Seite.
7. Tests (siehe unten).

### Nicht im Scope

- Meldungen für Fehler nach dem Start (bleiben still, wie heute).
- Eine eigene Fehlerseite für andere Ursachen (Server nicht erreichbar, Service Worker).
- Änderung des Service Workers oder der Reisedaten.

### Folgearbeiten (eigene Aufgaben, halten #387 offen)

- **Teil-Check der Überwachung:** Eigenes Issue in `henemm/henemm-infra`: Teil-Check „Seite im Browser laden“ in `scripts/monitor.sh` (neben `check_frieda_seiten`, das nur HTTP 200 prüft). Warnung statt Alarm, entprellt, höchstens alle paar Stunden; vorher die Last des Servers messen; `betrieb/startprobe.mjs` wiederverwenden. Kein eigener BetterStack-Monitor.
- **Abnahme nach dem Ausliefern:** Echte Reiseseite im Browser laden und eine Reise ohne Pläne ebenso (beides nur lesend); die Meldung selbst nur an einer Testreise per erzwungenem Fehler zeigen, nie an echten Reisen.

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/vorlage.html | MODIFY | Fänger-Skript, Stile, `__startFertig`, Kopfkommentar |
| engine/bauen.py | MODIFY | Platzhalter `/*__STARTFEHLER__*/null` prüfen und einsetzen |
| engine/texte_de.py, texte_en.py, weitere texte_*.py | MODIFY | Schlüssel `seite.fehler.start_titel`, `seite.fehler.start_neu_laden` |
| engine/tests/texte_xx.py | MODIFY | Pseudo-Sprache bekommt die Schlüssel |
| betrieb/startprobe.mjs | MODIFY | Meldung als Fehler werten |
| docs/design.md, Bausteinseite (Vorlage) | MODIFY | Baustein „Startfehler-Meldung“ |
| engine/tests/test_startfehler_meldung_387.py, seiten_startfehler_387.mjs | CREATE | Neue Tests |
| engine/tests/test_startprobe.py, test_texte.py, test_design.py | MODIFY | Fälle ergänzen, Ausnahmelisten nicht verlängern |

### Estimated Changes

- Files: ca. 12
- LoC: +180/−5
- Risiko: NIEDRIG bis MITTEL (Skript vor dem Hauptskript, jede gebaute Seite betroffen)

## Implementation Details

### Fänger

Ein eigenes `<script>` (ohne `"use strict"`-Abhängigkeit vom Hauptskript) steht vor dem Hauptskript. Es liest `const T0 = /*__STARTFEHLER__*/null` (Ausschnitt `{sprache: {titel, neu_laden}}`) und hängt auf `window` zwei Hörer:

```
function melde() {
  if (window.__startFertig || document.getElementById("startfehler")) return;
  const t = T0[document.documentElement.lang] || T0[Object.keys(T0)[0]];
  /* createElement/textContent: Box mit role=alert, Titel, Knopf → location.reload() */
}
addEventListener("error", melde); addEventListener("unhandledrejection", melde);
```

Der Fänger nutzt nur `createElement` und `textContent` und greift nicht auf `D`, `TEXTE`, `T()` oder `el()` zu, damit er auch dann arbeitet, wenn das Hauptskript früh oder gleich beim Parsen scheitert. Er selbst ist in `try/catch` gefasst. Die Meldung wird im Rahmen `.meldungen` eingefügt, sonst als erstes Kind von `body`; ohne `#startfehler` im festen HTML (Seiten ohne Fehler bleiben unberührt). Fehler fremder Skripte ohne Quelle („Script error.“) zählen, solange der Start läuft: gewollt.

Ein Syntaxfehler im Hauptskript löst `error` aus, bevor `D` existiert; auch dieser Fall ist abgedeckt, weil der Fänger vorher in einem eigenen Skript steht.

### Ende des Starts

Letzte Anweisung des Hauptskripts: `window.__startFertig = true;`. Die Registrierung des Service Workers liegt davor oder dahinter, ein Fehler dort ist harmlos; die Marke steht an der Stelle, ab der die Seite als gestartet gilt (nach `route()` und dem ersten Zeichnen). `test_startreihenfolge.py` bleibt gültig.

### Platzhalter in `bauen.py`

Neben `/*__DATEN__*/null` und `/*__TEXTE__*/null` wird `/*__STARTFEHLER__*/null` genau einmal verlangt (sonst `BauFehler`). Der Ausschnitt wird aus `texte.sprache(k).TEXTE` je Sprache gebildet (nur die zwei Schlüssel, `</` wie beim Katalog als `<\/` geschützt) und in die Seite eingesetzt. Der Code kennt keine Sprache beim Namen (ADR-0006).

### Stile

`.hinweis.glas` (Vorlage Z. 883–885) bleibt die Grundlage, wie bei `#neu` und `#offline`. Zusätzlich nur, was für eine vor dem Hauptskript sichtbare Meldung nötig ist (feste Lage oben, lesbar auch ohne Pico und Designwerte; mit Rückfallwerten statt Tokens, falls das Stilblatt nicht geladen ist). Logische Eigenschaften (`inset-inline`, `padding-inline`) für `rtl`.

### Startprobe

`betrieb/startprobe.mjs` prüft nach dem Laden, ob `#startfehler` im DOM und sichtbar ist, und fügt dann „Startfehler-Meldung sichtbar“ den Fehlern hinzu (Exit 1). Die vorhandenen Prüfungen (Seitenfehler, `console.error`, leere Seite) bleiben.

### Service Worker und Cache

Die geänderte `index.html` kommt über den Wechsel der Version des Service Workers (Hash über die Dateien, `bauen.py` Z. 1409) zu den Geräten; kein Handschritt. Die Reisedaten ändern sich nicht, also keine Umstellung in `neu.py nachziehen`.

### Bausteinregel (ADR-0002)

Baustein „Startfehler-Meldung“, Ebene Molekül: Eintrag im Kopfkommentar „Bausteine nach Ebenen“, Stile der Ebene Moleküle, Bausteinseite (`#bausteine`, mit Muster, weil die Seite die Meldung sonst nie zeigt), `docs/design.md`. Er zeigt keine Grundform der Reise, also kein Eintrag in `ONTOLOGIE`/`GRUNDFORMEN`. `test_design.py` prüft die vier Stellen.

## Acceptance Criteria

- **AC-1:** Bricht das Hauptskript beim Start ab (Laufzeitfehler, Syntaxfehler oder abgelehntes Versprechen), zeigt die Seite `#startfehler` mit `role="alert"`, dem Titel und dem Knopf „Neu laden“, sichtbar im Fenster. Gilt für beide Beispielreisen (Wanderung, Stadtwochenende).
- **AC-2:** Der Knopf lädt die Seite neu (`location.reload()`).
- **AC-3:** Titel und Knopf stehen in der Sprache der Reise (`<html lang>`); ist sie nicht im Ausschnitt, in der ersten Sprache. Die Texte stammen aus dem Katalog, im Code stehen keine sichtbaren Wörter.
- **AC-4:** Eine gesunde Seite beider Beispielreisen enthält kein `#startfehler`. Ein Fehler nach Ende des Starts (z. B. `setTimeout(() => { throw … })`, abgelehntes `fetch`) zeigt keine Meldung.
- **AC-5:** Der Fänger greift nicht auf `D`, `TEXTE`, `T()` oder `el()` zu und arbeitet mit `createElement` und `textContent`; er löst selbst keinen Fehler aus (Test mit Syntaxfehler im Hauptskript).
- **AC-6:** `bauen.py` verlangt `/*__STARTFEHLER__*/null` genau einmal; der eingesetzte Ausschnitt enthält alle Sprachen des Katalogs und nur die zwei Schlüssel.
- **AC-7:** `seite.fehler.start_titel` und `seite.fehler.start_neu_laden` stehen in allen `texte_*.py` und in der Pseudo-Sprache; die Ausnahmelisten in `test_texte.py` werden nicht länger.
- **AC-8:** `betrieb/startprobe.mjs` endet mit Exit 1 und „Startfehler-Meldung sichtbar“, wenn die Seite die Meldung zeigt; auf gesunden Seiten beider Beispielreisen bleibt sie grün.
- **AC-9:** Der Baustein ist im Kopfkommentar, in den Stilen, auf der Bausteinseite und in `docs/design.md` eingetragen (`test_design.py` grün).
- **AC-10:** `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün, auch die Browsertests und `test_seite_startet.py`.
- **AC-11:** (Prozess) Aussehen und Wortlaut sind dem Product Owner vor dem Bau als Artefakt-Entwurf gezeigt und von ihm freigegeben.
- **AC-12:** (Prozess) Das Issue in `henemm/henemm-infra` für den Teil-Check ist angelegt und in #387 verlinkt; #387 wird erst nach laufendem Teil-Check und Abnahme geschlossen.

## Test Plan

Neue Dateien `engine/tests/test_startfehler_meldung_387.py` (Python, Bau und Katalog) und `engine/tests/seiten_startfehler_387.mjs` (Browser, Vorbild `seiten_start.mjs`/`test_seite_startet.py`). Rot zuerst.

- [ ] Test 1 (AC-1 bis AC-3): GIVEN gebaute Seiten beider Beispielreisen mit erzwungenem Startfehler im Hauptskript (Seite vor dem Laden verändert, z. B. Fehler als erste Anweisung und ein zweiter Lauf mit Syntaxfehler) WHEN geladen THEN ist `#startfehler` sichtbar, hat `role="alert"`, den Titel und den Knopf; Text in der Sprache der Reise; Klick auf den Knopf lädt neu.
- [ ] Test 2 (AC-4): GIVEN gesunde Seiten beider Beispielreisen WHEN geladen und danach per `setTimeout` ein Fehler geworfen THEN fehlt `#startfehler`.
- [ ] Test 3 (AC-5): GIVEN Quelltext des Fängers WHEN geprüft THEN kommen `D`, `TEXTE`, `T(` und `el(` nicht darin vor.
- [ ] Test 4 (AC-7): GIVEN Katalog WHEN `test_texte.py` läuft THEN stehen beide Schlüssel in jeder Sprache und in der Pseudo-Sprache, Ausnahmelisten nicht länger.
- [ ] Test 5 (AC-8): GIVEN eine gebaute Seite mit erzwungenem Startfehler WHEN `startprobe.mjs` läuft THEN Exit 1 mit „Startfehler-Meldung sichtbar“; gesunde Seite Exit 0 (in `test_startprobe.py`).
- [ ] Test 6 (AC-6): GIVEN gebaute `index.html` beider Beispielreisen THEN kommt `/*__STARTFEHLER__*/` nicht mehr vor, der Ausschnitt enthält alle Sprachen; GIVEN eine Vorlage mit zwei Platzhaltern THEN `BauFehler`.
- [ ] Test 7 (AC-9): `test_design.py` kennt den neuen Baustein an allen vier Stellen.
- [ ] Test 8 (AC-10): Gesamtlauf `pytest -q engine/tests -n 3`.

## Prüfstelle ADR-0001

| Nr. | Antwort |
|---|---|
| 1 | Nur Oberfläche und Bau, keine Grundform und nichts Reisespezifisches. Mit beiden Beispielreisen (Wanderung, Stadtwochenende ohne Wanderung) durchgespielt. |
| 2 | Kein Katalog von Arten oder Merkmalen; die Software führt nur einen Hüllentext ein. |
| 3 | Keine KI, reine Regel im Browser. |
| 4 | Keine Reiseinhalte betroffen; der Konnektor braucht nichts (nicht anwendbar, Oberfläche der Hülle). |
| 5 | Keine neue Aussage über die Reise, keine Herkunft nötig. |
| 6 | Es fällt keine Entscheidung. |
| 7 | Keine IDs, kein Überschreiben von Daten. |
| 8 | Die Seite startet und läuft offline wie bisher; die Meldung wirkt auch offline (Texte liegen in der Seite). Browser-Rundgang über beide Beispielreisen. |
| 9 | Nein, Claude Code baut nur die Software. |
| 10 | Diese Spec, `docs/design.md` (Baustein), `docs/betrieb.md` Z. 158 (Startprobe, um die Meldung ergänzen), `docs/sprachen.md` falls nötig. |

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** keine (bestehend: ADR-0001, ADR-0002, ADR-0006). Der Fänger folgt dem Bestand: Meldung als `.hinweis.glas` wie `#neu`/`#offline`, Text aus dem Katalog.

## Risiken

- Der Fänger darf nicht selbst fehlschlagen: nur `createElement`/`textContent`, kein Zugriff auf `D`/`TEXTE`, in `try/catch`.
- Harmlose Fehler (Netz, Karte, Rückmeldedienst) dürfen die Seite nicht überdecken: nur Fehler vor `__startFertig` zählen. Würde die Marke zu spät gesetzt, bliebe ein später Fehler beim Start als Meldung sichtbar, zu früh gesetzt, ginge ein Startfehler unbemerkt durch; deshalb steht sie als letzte Anweisung (Test 1 und 2 prüfen beide Seiten).
- Gesunde Seite kurz vor der Marke wirft in einem Fremdskript (z. B. Karte): Meldung erscheint, obwohl die Seite brauchbar wäre. Gewollt: Start gilt als gescheitert; Test an beiden Beispielreisen mit und ohne Grundkarte.
- Cache: ältere Geräte zeigen die alte Seite bis zum Versionswechsel.
- Teil-Check der Überwachung: Last des Servers vorher messen (Folgearbeit).

## Definition of Done

- [ ] Alle Tests 1–8 sind geschrieben, zuerst rot, dann grün (Browsertests an Wanderung und Stadtwochenende)
- [ ] Ein eigener Test belegt, dass der Fänger bei einem Syntaxfehler im Hauptskript selbst nichts wirft (zweiter Teil von AC-5)
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n 3` ist grün, darunter Startprobe-, Text- und Design-Test
- [ ] Baustein „Startfehler-Meldung“ steht an allen vier Stellen (Kopfkommentar, Stile, Bausteinseite, `docs/design.md`)
- [ ] Entwurf von Aussehen und Wortlaut wurde dem Product Owner gezeigt und vor dem Bau angenommen
- [ ] Pull Request, CI grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Vorspulen auf `main`
- [ ] Issue für den Teil-Check „Seite im Browser laden“ in `henemm/henemm-infra` angelegt und in #387 verlinkt
- [ ] Abnahme nach dem Ausliefern dokumentiert; #387 erst danach geschlossen

## Known Limitations

- Fänger und Meldung gelten nur für Fehler im Start; Fehler danach bleiben unsichtbar.
- Die Sprache ist die der Reise, nicht die persönliche Wahl der Person (liegt im Hauptskript und ist beim Startfehler nicht erreichbar).
- Ohne laufendes JavaScript (blockiert) erscheint weiterhin nichts; dafür ist die Überwachung zuständig.
- Die Meldung ersetzt nicht die Ursachenbehebung: Sie zeigt den Ausfall nur an, der Teil-Check der Überwachung findet ihn.

## Changelog

- 2026-11-10: Erstfassung
