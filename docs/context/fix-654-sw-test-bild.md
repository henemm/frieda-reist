# Kontext: fix-654-sw-test-bild

## Wunsch

`test_bilder_eigen.py::test_browser_service_worker_vergisst_geloeschtes_bild[chromium]` scheiterte einmal in der CI (Lauf 44999677401, Versuch 1, Job `tests (instanz)`) mit `{'fehler': [], 'vorher': 2, 'nachher': 2}`. Ursache klären, Test stabil machen, Prüfung nicht abschwächen (#654). Auftrag des Product Owners: #654, danach #656 und #689.

## Betroffene Dateien

| Datei | Bedeutung |
|---|---|
| `engine/tests/test_bilder_eigen.py` (:1374-1390 `_Server`, :1444-1456 Test) | Testserver ohne eigene Warteschlange, ohne Cache-Vorgabe, antwortet auf `If-Modified-Since`; `_Server` nutzt auch der Test der Seite (:1417, #689) |
| `engine/tests/seiten_bilder_eigen.mjs` (:162-188, Art `sw`) | Neuer Stand wird hingelegt, Seite neu geladen, `update()` mit verschlucktem Fehler (:185), dann bis zu 10 s zählen (:187) |
| `engine/sw.vorlage.js` (:37-84) | `install` ruft `bilderVergessen` vor dem Laden; wird nicht geändert |
| `engine/tests/test_pwa.py` (:105-140) | Vorbild Testserver: verwirft `If-Modified-Since` wegen 304 in derselben Sekunde (#154), Protokoll der Anfragen |
| `engine/tests/pwa_browser.mjs` (:50-91) | Vorbild: auf Zustände warten; Zeile 91 ruft `update()` ohne Verschlucken |
| `engine/tests/test_wackel_599.py` | Vorbild: Nachweis unter künstlicher Verzögerung, ein echter Fehler bleibt rot |
| `betrieb/vorlagen/nginx-reise.conf` (:13) | Der echte Server sendet `Cache-Control: no-cache`, der Testserver nicht |

## Befunde (macOS, Chromium 147, Playwright 1.59.1, Messung in einer Kopie des Skripts)

1. Im Normalfall ist das Bild schon kurz nach `update()` weg (1-2 ms Wartezeit, unter Last bis 271 ms). Der Test wartet bereits bis zu 10 s. „Zu früh gemessen“ erklärt `nachher: 2` nicht.
2. **Abruf von `sw.js` scheitert dauerhaft** (eingespielt): exakt `vorher: 2, nachher: 2` ohne Fehler, auch 20 s später, weil `.catch(() => {})` den Fehler verschluckt. Nach einem einmaligen Abbruch holt Chromium das Update von selbst nach (rund 1,7 s), der Test bleibt grün.
3. **`304 unverändert` auf `sw.js`** (eingespielt: neue Datei mit der Änderungszeit der alten): exakt dasselbe Bild, 2 von 2 Läufen, `update()` meldet dabei „ok“. Chromium fragt nach 1,6 s noch einmal und bekommt wieder 304. Im unveränderten Ablauf liegt die Kopierzeit später als die alte Datei; dass es in der CI dieselbe Sekunde war, ist unbelegt und wenig wahrscheinlich.
4. **Testserver unter Last:** Mit der Standard-Warteschlange (5) scheiterte die Anmeldung des Workers in 9/150, 13/120, 4/100, 3/100, 0/100 Läufen (in den näher protokollierten Läufen mit `ERR_CONNECTION_RESET`/`ERR_SOCKET_NOT_CONNECTED`), mit 128 in 0/200. Das ist ein anderes Bild als in der CI (dort lief die Anmeldung, `vorher: 2`); Linux behandelt volle Warteschlangen anders.
5. **Nicht bestätigt:** Der alte Worker holt das Bild aus dem HTTP-Cache des Browsers zurück (künstlich gealterte Dateien 0/18, mit `no-cache` 0/6).
6. Ohne eingespielten Fehler trat `nachher: 2` in keinem Lauf auf. **Der Auslöser in der CI ist nicht bewiesen**, das Protokoll enthält weder den Fehler von `update()` noch die Anfragen. Webkit wurde nicht gemessen (lokal nicht installiert).

## Bestehende Muster

- Auf Zustände warten statt auf feste Zeiten (#154, #599), Grund des Scheiterns sichtbar machen.
- Wackelige Tests werden unter eingespieltem Fehler oder Verzögerung nachgewiesen, ein echter Fehler muss rot bleiben.

## Abhängigkeiten

- Nutzt: `bauen.py`, `sw.vorlage.js`, Playwright, Node.
- Wird genutzt von: nur `test_bilder_eigen.py` (zwei Tests über `_Server` und `_node`).

## Spec

- `docs/specs/oberflaeche/bilder-582-eigene-fotos.md` AC-15 (V15): gelöschtes Bild ist nach dem nächsten Laden aus dem Cache entfernt.

## Risiken und Überlegungen

- Ein Wiederholen von `update()` darf keinen Produktfehler verdecken: Wiederholt werden darf nur der Anstoß, geprüft wird weiter `nachher == 0`, zusätzlich dass der neue Worker wirklich installiert wurde.
- Vor jedem Umbau: Der Test muss mit ausgebautem `bilderVergessen` weiterhin rot sein (Gegenprobe).
- Weil der Auslöser nicht bewiesen ist, gehört Diagnose in die Fehlermeldung (Fehler von `update()`, Zustände des Workers, Anfragen mit Status), damit ein erneuter Ausfall die Ursache nennt.
- #689 betrifft dasselbe Skript (`frage()`), bleibt eigenes Issue.

## Analysis

### Type

Bug (unzuverlässiger Test; am Produkt wird nichts geändert). Die Vorprüfung aus dem Intake (Befunde 1-6) galt als Bestandsaufnahme; die Analyse hat nur die offenen Punkte nachgeholt.

### Neue Befunde

7. **CI-Protokoll:** Der rote Lauf prüfte a0af665; `engine/sw.vorlage.js` und die Warteschleife sind seither unverändert. `nachher: 2` heißt laut Code, dass die Schleife (100 × 100 ms) voll durchlief. Job parallel (`-n auto`, Worker gw2), 1 rot, 3480 grün, 1128 s. Die Testdauer selbst steht nicht im Protokoll.
8. **Kein Weg im Produkt gefunden**, der nach einer Installation des neuen Workers dauerhaft `nachher: 2` ergibt: VERSION ändert sich mit jedem entfernten Bild (`bauen.py:1636-1651`), vor `bilderVergessen` gibt es in `install` keinen naheliegenden Wurf. Folgerung, nicht Beweis: Im roten Lauf wurde kein neuer Worker installiert.
9. **Schmales Zeitfenster im Produkt (nur gelesen, nicht nachgestellt):** Ein Abruf des alten Workers, der vor dem Entfernen begann und nach `bilderVergessen` mit 200 endet, legt das Bild wieder in den alten Speicher (`sw.vorlage.js`, `ausSpeicher`: `cache.put` ohne Abgleich); dort liegt es bis zur Übernahme des neuen Stands. Erklärt die CI nicht gut (beide Einträge lagen schon im Speicher, kein Abruf nötig). Nicht Teil dieses Tickets.
10. **Aktivierung:** `activate` löscht den ganzen alten Speicher. Übernimmt der neue Worker, ist `nachher == 0` auch ohne `bilderVergessen`. Im Test passiert das nicht absichtlich: `uebernehmen` kommt nur durch Tippen oder `?aktualisieren=` (`vorlage.html:7077`, `:7093`). Der heutige Test prüft das aber nicht.

### Affected Files (with changes)

| File | Change Type | Description |
|---|---|---|
| `engine/tests/test_bilder_eigen.py` | MODIFY | `_Server`: `If-Modified-Since` verwerfen, `Cache-Control: no-cache` wie nginx, Warteschlange 128, Protokoll (Pfad, Status), Fehler für Nachweise einspielbar; Test prüft zusätzlich den neuen Worker und nennt die Diagnose |
| `engine/tests/seiten_bilder_eigen.mjs` | MODIFY | Art `sw`: Anstoß begrenzt wiederholen, Fehler sammeln, auf neuen installierten Worker warten, dann zählen, Zustände ausgeben |
| `engine/tests/test_wackel_654.py` | CREATE | Nachweise mit eingespielten Fehlern und Gegenproben |

### Scope Assessment

- Files: 3 (nur Tests)
- Estimated LoC: +220/-15
- Risk Level: LOW (kein Produktcode); Hauptgefahr ist eine unbemerkt schwächere Prüfung

### Technical Approach

| Variante | deckt ab | Schwäche |
|---|---|---|
| nur Server | 304 (2/2 rot eingespielt), Verbindungsabbrüche (bis 13/120 → 0/200 mit 128) | verschluckter Fehler bleibt, erneuter Ausfall ohne Grund |
| nur Skript | vorübergehender Abbruch | 304 wiederholt sich, Abbrüche bei der Anmeldung bleiben |
| nur Diagnose | Grund beim nächsten Ausfall | bleibt unzuverlässig |
| **beides mit Diagnose** | alle nachgestellten Auslöser | etwas mehr Testcode |

Empfehlung: beides mit Diagnose.

1. Vor dem Umbau festhalten: ohne den Aufruf von `bilderVergessen` ist der heutige Test rot.
2. Wiederholt wird nur der Anstoß (`update()`), hart begrenzt nach Zeit. Kommt kein neuer Worker, scheitert der Test mit genanntem Grund (Fehler, Zustände, Anfragen mit Status); nie überspringen.
3. Erst nach „installiert“ zählen. Verlangt werden `vorher > 0`, der neue Worker wartet (`waiting`, der alte ist noch aktiv), `nachher == 0`. Damit kann `activate` die Prüfung nicht erfüllen, sie wird strenger als heute.
4. Zustände nur über `installing/waiting/active` lesen (gilt auch für Webkit).
5. Nachweise: `sw.js` einmal und mehrfach abgebrochen → grün; neue Datei mit alter Änderungszeit → grün; dauerhaft abgebrochen → rot mit Grund; ohne `bilderVergessen` → rot.

### Dependencies

- `_Server` und `_node` nutzt auch der Test der Seite (#689): beide Tests laufen lassen. #689 bleibt eigenes Issue, dieselbe Datei, deshalb danach.
- Muster: `test_pwa.py` (#154), `pwa_browser.mjs`, `test_wackel_599.py`. `pwa_browser.mjs:74` verschluckt den Fehler absichtlich (kaputtes Update) und wartet auf das Protokoll, dort ist nichts zu tun.

### Befunde, die gegen den Plan sprechen

- Der Auslöser in der CI bleibt unbewiesen (Befund 6); der Umbau deckt die nachgestellten Wege ab und macht einen erneuten Ausfall erklärbar, er beweist keine Behebung. Das gehört so in Spec, PR und Issue.
- Webkit ist lokal nicht installiert; gemessen wird es erst in der CI. Vor dem Ausliefern beide Browser in der CI mehrfach laufen lassen.
- Ob `waiting` nach dem Neuladen in beiden Browsern immer erreicht wird, ist noch zu messen; wird der Worker dort doch aktiv, braucht die Prüfung eine andere Form, kein Weglassen.

### Open Questions

- Keine an den Product Owner. Das Zeitfenster aus Befund 9 wird als eigenes Issue notiert.

## Nachtrag aus der RED-Phase (25.11.2026)

11. **`304` entsteht auch ohne eingespielten Fehler.** Der heutige Ablauf (altes Messskript, Server nur um ein Protokoll ergänzt) ergab lokal in 2 von 15 Messläufen und zusätzlich im ersten RED-Lauf `vorher: 2, nachher: 2, fehler: []` mit den Anfragen `[200, 304, 304]`. In den 15 Läufen genau dann, wenn die alte `sw.js` und die hingelegte Kopie in dieselbe Sekunde fielen (2 von 2; sonst 0 von 13, dort `[200, 200]`). Zwischen Bau und Kopie lagen 0,5 bis 1 s. Damit sind die Aussagen „ohne eingespielten Fehler trat `nachher: 2` in keinem Lauf auf“ (Befund 6) und „dieselbe Sekunde wenig wahrscheinlich“ (Befund 3) überholt: Es ist ein natürlicher Weg zum Bild der CI und der wahrscheinlichste. Bewiesen ist er für den CI-Lauf nicht (dort kein Protokoll der Anfragen; ob der Abstand dort unter 1 s lag, ist unbekannt).
12. **Vorher-Messung** (heutiger Ablauf, `docs/artifacts/fix-654-sw-test-bild/test-red-output.txt`): Dreifacher Abbruch von `sw.js` und gleiche Änderungszeit ergeben das Bild der CI; ohne `bilderVergessen` ist `nachher: 2`, der alte Test also rot; bei sofortiger Übernahme stürzt das alte Messskript ab („Execution context was destroyed“). Laufzeit des alten Tests ohne Fehler: 1,85 s. Im ersten RED-Lauf (nicht aufbewahrt) scheiterte einmal die Anmeldung des Workers (Befund 4), auch ohne künstliche Last.
13. **Probe-Umbau (nicht im Repo, Chromium):** `waiting` wird nach dem Neuladen immer erreicht, der alte Worker bleibt aktiv; alle Nachweise grün, unter Last (8 Prozesse zugleich, 3 Durchgänge) 168 von 168. Für GREEN daraus: Version der Worker über die Nachricht `version` lesen (großzügige Frist, sonst sieht eine späte Antwort wie ein Wechsel aus); Auswertungen bei „context was destroyed“ wiederholen; nach einer Übernahme vor dem Zählen warten, bis der Controller `activated` ist (`activate` räumt erst dann fertig auf).
14. **Nachweis a, einmal:** Die Erwartung ist „jeder gescheiterte Anstoß ist gesammelt“ statt „genau ein Fehler“, weil der eigene Abruf des Browsers nach dem Laden den Abbruch unter Last verbrauchen kann.
