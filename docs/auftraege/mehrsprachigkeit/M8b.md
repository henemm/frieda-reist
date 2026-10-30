# Auftrag M8b: Englische Namen der Schnittstelle mit deutschen Aliasen

Modell: Schritt 1 Sonnet, Schritt 2 Haiku (ein PR je Schritt) · Voraussetzung: M8 übernommen · Plan: `docs/mehrsprachigkeit.md`, Abschnitte „Namen der Schnittstelle“ und „M8b“

## Lies zuerst

`docs/auftraege/mehrsprachigkeit/README.md`, `docs/adr/0006-mehrsprachigkeit.md` (Punkt 4), `docs/mehrsprachigkeit.md` (Tabelle der 55 Werkzeugnamen und die Regeln für Parameternamen), `docs/konnektor.md`, `engine/konnektor.py`: alle `inputSchema` (Werkzeuge 1852 bis 2693), `antwort_auf` (2942), `frieda_antwort` (2019), `konto_antwort` (2055), `werkzeug()` (2796), `ontologie_werkzeug()` (1100), `frieda_werkzeug()` (1965), `SCHREIB_WERKZEUGE` (73), `ONTOLOGIE_WERKZEUGE` (77), `wname()` aus M8; `engine/tests/test_konnektor.py` (Mengenvergleiche auf Namen 178 bis 184, 288, 540, 615).

## Ziel

`tools/list` zeigt englische Werkzeug- und Parameternamen; Aufrufe mit englischen, deutschen oder gemischten Namen liefern dasselbe; unter dem Rand des Konnektors bleibt alles deutsch.

## Schritt 1 (Sonnet): Tabellen

1. `NAMEN`: englisch → intern, genau die Tabelle aus dem Plan (55 Einträge plus `language_set` → `sprache_setzen`, `frieda` → `frieda`).
2. `PARAMETER`: alle Property-Namen aller `inputSchema` auflisten (Skript, in der PR-Beschreibung die Liste zeigen); ein Wort immer dieselbe Übersetzung (Regeln im Plan: `reise` → `trip`, `ziel` → `target`, `quelle` → `source`, `geprueft` → `checked`, `gilt` → `valid_for`, `grund` → `reason`, …); Konflikte (gleiches Wort, andere Bedeutung) als Ausnahme je Werkzeug (`PARAMETER_JE_WERKZEUG`). Englische Namen `snake_case`, kein Zusammenstoß mit einem bestehenden internen Namen (sonst Aliasauflösung mehrdeutig; prüfen und im Test festhalten).
3. `ENUM_ALIAS` je Datenwert: `chosen` → `gewaehlt`, `rejected` → `verworfen`, `replaced` → `ersetzt`, `proposed` → `vorgeschlagen`, `favoured` → `favorisiert`, `organizer` → `organisator`, `contributor` → `mitwirkend`, `guest` → `gast`, `required` → `pflicht`, `recommended` → `empfohlen`, `optional` → `angeboten`, `off` → `aus`, `open` → `offen`, `in_progress` → `in_arbeit`, `done` → `erledigt`, `dropped` → `entfaellt`, `booked` → `gebucht`, `requested` → `angefragt`, `cancelled` → `storniert`, `resolved` → `geklaert`, `idea` → `idee`, `planning` → `planung`, `fixed` → `fest`, `travelling` → `unterwegs`, `after` → `danach`, `archive` → `archiv`, `comment`/`question`/`correction`/`addition`/`answer`/`wish` → `Kommentar`/`Frage`/`Korrektur`/`Ergänzung`/`Antwort`/`Wunsch`. Nur Eingabe; Schemata nennen weiter die Datenwerte, die englischen Beschreibungen (M8) nennen beide.
4. `docs/konnektor.md`: Tabelle der Werkzeuge bekommt die Spalte „Englisch (`tools/list`)“ vorn, die deutsche Spalte heißt „Intern und Alias“; neue Tabelle der Parameternamen; Enum-Aliase. Die Anleitungen in der Doku nennen englische Namen.

## Schritt 2 (Haiku): Umsetzung

1. `tools/list`: jedes Werkzeug mit `name` aus der Umkehrung von `NAMEN`, Properties und `required` umbenannt nach `PARAMETER`; Beschreibungen (M8) nennen Werkzeuge über `wname()`, das jetzt den englischen Namen liefert.
2. `tools/call`: Funktion `intern(name, args)`: Werkzeugname über `NAMEN` oder unverändert, wenn schon intern; jedes Argument über `PARAMETER` (englisch gewinnt bei Doppelung); Enum-Werte über `ENUM_ALIAS` für Properties mit `enum` oder bekannten Statusfeldern. Erst danach laufen `werkzeug()`, `ontologie_werkzeug()`, `frieda_werkzeug()` unverändert.
3. Alle Antworttexte, die einen Werkzeugnamen nennen („nur mit `entscheiden`“), über `wname()`.
4. Tests: `tools/list` enthält `trip_create`, nicht `reise_anlegen`; Property `source`, nicht `quelle`; ein Aufruf `value_set` mit `source` und einer mit `wert_eintragen` mit `quelle` und einer gemischt liefern dieselbe Datei und dieselbe Antwort; `decide` mit `status: chosen` schreibt `gewaehlt`; die bestehenden Prüfungen mit deutschen Namen bleiben unverändert grün (sie prüfen Aufrufe, nicht die Liste); die Mengenvergleiche auf `tools/list` (178 bis 184 usw.) werden über `NAMEN` abgebildet, nicht umgeschrieben; kein englischer Name kollidiert mit einem internen.

## Nicht anfassen

`SCHREIB_WERKZEUGE`, `ONTOLOGIE_WERKZEUGE`, `ONTOLOGIE_AKTION`, `SCHREIB_AKTION`, `schreiben.WERKZEUGE`, Pfade des Schreibwegs, `rueckmeldungen.py`, Dateien der Reise, Commit-Nachrichten.

## Fertig, wenn

- Tests grün; die drei Aufrufvarianten liefern dasselbe; Doku vollständig mit beiden Spalten.
- Je ein PR nach README, Statuszeile M8b.
