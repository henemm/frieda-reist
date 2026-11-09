---
entity_id: kartenpunkte-frist-240
type: bugfix
created: 2026-11-09
updated: 2026-11-09
status: draft
workflow: kartenpunkte-frist-240
version: "1.0"
tags: [schreibweg, kartenpunkte, overpass, timeout, betrieb, k14]
---

# Kartenpunkte-Frist: Abruf bei OpenStreetMap vor der Sperre (#240, K14 `map_points_fetch`)

## Approval

- [ ] Approved

## Purpose

Das Werkzeug `kartenpunkte_holen` (Konnektor: `map_points_fetch`) liefert am echten Overpass-Dienst nie Treffer. Der Dienst braucht vom Server der Instanz aus 33 bis 44 s (Messung 9.11.2026: 200 nach 33 bis 34 s, ein Versuch direkt danach 502 nach 0,1 s; die Ausweichdienste `overpass.private.coffee` und `overpass.kumi.systems` antworten innerhalb von 40 s gar nicht). Das Werkzeug wartet aber nur `OSM_ZEIT` = 12 s, mitten im Schreibvorgang, innerhalb von `ZEIT_GESAMT` = 25 s und unter der Sperre der Reise.

Der Netzabruf wird deshalb aus dem Schreibvorgang gelöst: Der Dienst ruft Overpass **vor** der Sperre mit einer eigenen, längeren Frist (und höchstens einer Wiederholung bei sofortigem Fehler) und reicht die Antwort an den Vorgang weiter. Die Sperre der Reise wird dadurch nicht länger gehalten als heute; andere Schreibvorgänge laufen während des Abrufs weiter.

## Source

- **File:** `engine/schreiben.py`, `engine/schreiben_git.py` (nur Weitergabe des Umgebungswerts)
- **Identifier:** `OVERPASS`, `OSM_ZEIT`, `overpass_abfragen`, `kartenpunkte_holen`, `ZEIT_GESAMT`, `ZEIT_PRUEFUNG`, `anwenden_extern`, `vorgang_speicher`, `schreiben_git.vorgang`, `Schreiber.wer_pruefen`, `route_stand`, `reisespeicher.exportieren`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| Overpass-API (`https://overpass-api.de/api/interpreter`, ODbL) | Extern | Quelle der Punkte; verlangt eine Kennung als User-Agent (ohne: 406) |
| `instanz.kennung()`, `instanz.wert(name, vorgabe)` | Funktion | User-Agent; Overpass-Adresse über `FR_OVERPASS` überschreibbar (Tests) |
| `route_stand`, `bauen.Bauer` | Funktion | Linie der Strecke (Probebau); kann in den Ordner schreiben, deshalb nur in einer Kopie |
| `reisespeicher.exportieren(reise, ziel, bis=stand_nummer)` | Funktion | Lesekopie bei Speicher-Reisen (nur lesend) |
| `Schreiber.wer_pruefen` | Methode | Rollenprüfung vor dem Abruf, damit eine Gast-Rolle keine Last am öffentlichen Dienst auslöst |
| `engine/konnektor.py` `schreib_anfrage` | Funktion | wartet 120 s auf den Schreibdienst; nginx `/mcp` hat `proxy_read_timeout 300s` |
| `werkzeuge/punkte_holen.py` | Muster | Wiederholung bei 429/502/503/504 (dort außerhalb des Dienstes) |
| `docs/specs/betrieb/schreibweg-zeitgrenzen.md`, `docs/specs/betrieb/schreibweg-speicher-347.md` | Spec | Zeitbudget, Sperre, Speicherweg |
| `docs/adr/0001-kern.md` | ADR | Prüfstelle |

## Scope

- **Im Scope:**
  - Abruf nur für `kartenpunkte_holen`, vor der Sperre, in `anwenden_extern`, für Speicher- und Git-Reisen.
  - `overpass_holen(abfrage, frist)` mit eigener Frist und höchstens einer Wiederholung.
  - Übergabe der Antwort als Datei (Umgebungswert `FR_OSM_VORAB`) an den Unterprozess `anwenden`.
  - `FR_OVERPASS` als überschreibbare Adresse, Zeitbudget-Test, Berichtigung des veralteten Kommentars „30 s von proxy_read_timeout“.
  - Doku: `docs/specs/betrieb/schreibweg-zeitgrenzen.md`, `docs/konnektor.md`, `docs/werkzeuge.md`.
  - Danach Abnahme am echten Dienst (siehe Abschnitt Abnahme).
- **Affected Files:** `engine/schreiben.py`, `engine/schreiben_git.py`, `engine/tests/test_schreiben.py`, `docs/specs/betrieb/schreibweg-zeitgrenzen.md`, `docs/konnektor.md`, `docs/werkzeuge.md`; `engine/texte_*.py` nur, falls eine neue Ablehnung nötig wird (voraussichtlich nicht)
- **Estimated Changes:** ca. +150/-20 LoC, etwa die Hälfte Tests. Risiko MEDIUM: Der Eingriff liegt in `anwenden_extern`, dem gemeinsamen Einstieg aller Schreibvorgänge, bleibt aber auf `kartenpunkte_holen` begrenzt.
- **Nicht im Scope:**
  - Ausweichdienst (kein anderer Overpass-Dienst ist vom Server aus erreichbar) und eigener Overpass-Server (eigenes Vorhaben).
  - Abruf im Hintergrund mit späterer Meldung (asynchrone Vorgänge; nur als Folge-Issue, falls die Abnahme es nötig zeigt).
  - Größere `ZEIT_GESAMT`, auch nicht nur für dieses Werkzeug (hielte die Sperre der Reise eine Minute, andere Vorgänge bekämen 429).
  - Änderungen an Abfrage-Inhalt, Filtern, Trefferlimit (`MAX_TREFFER`) oder Ablegen der Punkte.

## Implementation Details

```
Konstanten (engine/schreiben.py):
  OVERPASS         = instanz.wert("FR_OVERPASS", "https://overpass-api.de/api/interpreter")   # zur Laufzeit gelesen
  OSM_ZEIT         = 12    bleibt: kurze Frist für den eigenen Abruf im Unterprozess (Rückfall)
  OSM_FRIST_VORAB  = 45    Frist des Abrufs vor der Sperre inklusive Wiederholung und Pause (Sekunden)
  OSM_PAUSE        = 2     Pause vor der einen Wiederholung
  ZEIT_VORAB_VORB  = 10    höchstens für Lesekopie, Rollenprüfung und Abfrage vor dem Abruf
  ZEIT_VORAB       = ZEIT_VORAB_VORB + OSM_FRIST_VORAB = 55   Vorab-Fenster insgesamt

Zeitbudget (Sekunden, ab Beginn von anwenden_extern):
  Vorab-Fenster 55 + ZEIT_GESAMT 25 + ZEIT_PRUEFUNG 3 = 83 < 120 (Wartezeit des Konnektors, schreib_anfrage)
  Das Vorab-Fenster liegt VOR der Sperre; die Frist des Vorgangs (ZEIT_GESAMT) beginnt erst danach neu.
  Der Kommentar bei ZEIT_GESAMT ("30 s von proxy_read_timeout") wird berichtigt: /mcp hat 300 s, der Konnektor wartet 120 s.

Aufteilung von kartenpunkte_holen:
  kartenpunkte_abfrage(reise_dir, args) -> (abfrage, linie, abstand, tags, sid, kat, route)
      Prüfungen (strecke, kategorie, osm-Tags, abstand_m, Strecke vorhanden, Linie aus karte.wege[sid] oder Orte von/nach),
      bbox, Abfragetext OHNE Zeitangabe: "[out:json];(nwr[...](bbox);...);out center tags;"
      Wirft dieselben Ablehnungen wie bisher (keine_linie, kategorie, tag, abstand ...).
  overpass_holen(abfrage, frist) -> dict
      Setzt "[timeout:<ganze Sekunden der Frist>]" in die Abfrage, sendet mit User-Agent instanz.kennung(),
      Client-Frist = Rest der Frist. Wiederholung nur, wenn der Fehler eine schnelle HTTP-Antwort 429/502/503/504 war
      UND mindestens 15 s der Frist übrig sind; genau eine Wiederholung nach OSM_PAUSE. Zeitüberschreitung (keine
      Antwort bis zur Frist) wird nie wiederholt. Fehler werden zu Ablehnung("schreiben.kartenpunkte.limit", w1=code)
      bei 429/504 sonst ("schreiben.kartenpunkte.dienst", w1=Fehlerart) wie heute.
  overpass_abfragen(abfrage) -> dict    (Name bleibt, Tests ersetzen sie)
      1. Ist FR_OSM_VORAB gesetzt und lesbar und steht in der Datei {"abfrage": ..., "antwort": {...}} mit abfrage == abfrage
         (exakter Vergleich des Abfragetexts ohne Zeitangabe): Antwort daraus, kein Netzabruf.
      2. Sonst (Variable fehlt, Datei fehlt oder unlesbar, andere Abfrage): overpass_holen(abfrage, OSM_ZEIT), wie bisher.

Vorab-Abruf (kartenpunkte_vorab(s, reise, anfrage), aufgerufen in anwenden_extern NUR für werkzeug == "kartenpunkte_holen",
vor vorgang_speicher bzw. schreiben_git.vorgang):
  1. Ordner vorab = tempfile.mkdtemp(prefix="frieda-osm-") (eigener Ordner, nicht der des Vorgangs); wird in jedem Fall gelöscht.
  2. Lesekopie des aktuellen Stands in vorab/kopie:
       Speicher-Reise (reise in instanz.speicherreisen()): reisespeicher.exportieren(reise, vorab/kopie/reisen/<reise>, bis=stand_nummer(reise))
       Git-Reise: Kopie von <wurzel>/reisen/<reise> (shutil.copytree; nur lesen, die Arbeitskopie des Vorgangs bleibt unberührt)
     Nichts davon nimmt die Sperre der Reise.
  3. Rolle prüfen: Schreiber.wer_pruefen(kopie, anfrage, "kartenpunkte_holen") (Aktion "karte", nur Organisator:innen).
     Lehnt sie ab, oder lehnt kartenpunkte_abfrage ab (keine Strecke / keine Linie, falsche Art, falsches Tag ...):
     KEIN Abruf, KEINE Antwortdatei; der Vorgang läuft normal weiter und lehnt mit demselben Grund ab (maßgeblich bleibt der Vorgang).
  4. Abruf: overpass_holen(abfrage, OSM_FRIST_VORAB). Scheitert er (Ablehnung): sofort Antwort 422 mit dieser Ablehnung
     (abgelehnt(werkzeug, e)), ohne die Sperre zu nehmen; Protokollzeile wie jede Ablehnung.
  5. Erfolg: Datei vorab/osm.json mit {"abfrage": <Text>, "antwort": <Overpass-JSON>}; Pfad als Umgebungswert FR_OSM_VORAB in
     die Umgebung des Unterprozesses `anwenden` (vorgang_speicher UND schreiben_git.vorgang reichen den Wert weiter).
  6. Der Vorgang beginnt danach mit seinem eigenen start/ZEIT_GESAMT (neuer Fristbeginn, die Sperre wird erst jetzt genommen).

Sicherheit und Verträglichkeit:
  - Die Antwort kommt NIE aus einem Feld der Anfrage (JSON vom Konnektor), nur aus der Datei im eigenen Ordner, den allein
    der Dienst anlegt. Ein Feld "FR_OSM_VORAB" oder "osm_vorab" in der Anfrage wird ignoriert.
  - Der Umgebungswert statt eines neuen Anfragefelds: Im Git-Weg läuft der Unterprozess mit dem Code der Arbeitskopie (kann älter
    sein). Alter Code kennt FR_OSM_VORAB nicht und ruft wie bisher selbst ab (mit OSM_ZEIT) - gefahrlos.
  - Die Linie kann sich zwischen Vorab-Abruf und Vorgang ändern: Weicht die Abfrage des Vorgangs ab, wird die Datei nicht genutzt
    und eigenständig (kurze Frist) abgerufen.
  - Last am öffentlichen Dienst: höchstens zwei Anfragen je Werkzeugaufruf, nur nach bestandener Rollenprüfung, mit Kennung.
```

## Expected Behavior

- **Input:** Aufruf `kartenpunkte_holen` (Strecke, Kategorie, OSM-Tags, optional Abstand) durch eine Organisator:in.
- **Output:** wie bisher (Titel, Text mit Trefferzahl, Beispielen, ODbL-Hinweis). Bei erreichbarem, aber langsamem Dienst (bis etwa 45 s) kommen jetzt Treffer, die Antwort dauert dann bis etwa eine Minute. Ist der Dienst überlastet oder nicht erreichbar, kommt eine Ablehnung (`schreiben.kartenpunkte.limit` bzw. `.dienst`, "nichts wurde geändert") nach höchstens etwa 55 s.
- **Side effects:** zwei Protokollzeilen wie bisher (`Rejected` bzw. `Done`); die Sperre der Reise wird nur für den kurzen eigentlichen Vorgang gehalten; ein temporärer Ordner, der immer gelöscht wird. Der Vorab-Abruf liest die Reise nur, er schreibt nichts in sie.
- **Beide Reisetypen:** Wanderung (Strecke mit Linie): Vorab-Abruf, dann Eintragen. Städtewochenende (keine Strecke, kein Ding mit Linie): `kartenpunkte_abfrage` lehnt wie bisher ab (`schreiben.ding_finden.3` bzw. `schreiben.kartenpunkte.keine_linie`), ohne Netzabruf.

## Known Limitations

- Die Wartezeit der Claude-App auf ein Werkzeug ist nicht dokumentiert. Dauert der Abruf bis zu 45 s, liegt die Gesamtdauer bei etwa 50 bis 75 s. Ob die App so lange wartet, zeigt die Abnahme. Wartet sie nicht, kommt ein Folge-Issue (z. B. Abruf im Hintergrund mit späterer Meldung); bis dahin gilt: Die Treffer kommen nicht, wenn die App vorher aufgibt, der Eintrag wird dann aber auch nicht halb geschrieben (der Vorgang beginnt erst nach dem Abruf).
- Overpass antwortet unregelmäßig (ein Rechner von overpass-api.de schnell mit 502, der andere langsam); auch mit einer Wiederholung kann es scheitern. Die Ablehnung nennt das ehrlich und bittet um einen späteren Versuch.
- Zwei gleichzeitige Aufrufe für dieselbe Reise rufen Overpass je einmal ab (es gibt keinen Zwischenspeicher).

## Definition of Done

- [ ] Jede Acceptance Criterion unten ist durch einen automatischen Test belegt
- [ ] Kein Test greift auf das echte Netz zu (Ersatz per `monkeypatch` oder unerreichbare `FR_OVERPASS`-Adresse)
- [ ] Texte nur in `engine/texte_*.py`, in allen Sprachen; die Ausnahmelisten in `engine/tests/test_texte.py` werden nicht länger
- [ ] Doku in `docs/specs/betrieb/schreibweg-zeitgrenzen.md`, `docs/konnektor.md`, `docs/werkzeuge.md` nachgezogen
- [ ] Regressionslauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün, auch die Tests der einbindenden Instanzen mit dem Branch (Schnittstelle des Schreibwegs berührt)
- [ ] Nach dem Deploy: Abnahme am echten Dienst nur mit der eigenen Testreise `testreise-karten-225-erfunden-2027` (Wanderung) und an einem Städtewochenende; Ergebnis im Issue #240 festgehalten

## Acceptance Criteria

- **AC-1 (Zeitbudget):** Given die Konstanten und die nginx-Vorlage / When sie verglichen werden / Then `ZEIT_VORAB + ZEIT_GESAMT + ZEIT_PRUEFUNG` ist kleiner als die Wartezeit des Konnektors (`schreib_anfrage`, 120 s) und kleiner als jedes `proxy_read_timeout`; `OSM_FRIST_VORAB` ist größer als `OSM_ZEIT`; die bisherige Grenze `ZEIT_GESAMT + ZEIT_PRUEFUNG < 60` und `ZEIT_SPERRE <= ZEIT_GESAMT` gelten weiter
  - Test: `engine/tests/test_schreiben.py::test_zeitgrenzen_liegen_unter_der_des_konnektors` (erweitert)
- **AC-2 (Abruf vor der Sperre, gleiche Abfrage):** Given eine Wanderung mit Strecke und eine Organisator:in, und `FR_OVERPASS` zeigt auf eine unerreichbare Adresse für den Unterprozess / When `kartenpunkte_holen` über `anwenden_extern` läuft und der Vorab-Abruf (ersetzt) eine Antwort liefert / Then trägt der Vorgang die Treffer ein, ohne selbst ins Netz zu gehen (Unterprozess nutzt die Datei aus `FR_OSM_VORAB`), und der Abruf geschah, bevor die Sperre der Reise genommen wurde (die Sperre ist während des Abrufs frei)
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_vorab_abruf_vor_der_sperre`
- **AC-3 (andere Abfrage):** Given die Linie der Strecke ändert sich zwischen Vorab-Abruf und Vorgang, sodass die Abfrage abweicht / When der Vorgang läuft / Then wird die Vorab-Antwort nicht genutzt und der Vorgang ruft selbst ab (mit der kurzen Frist `OSM_ZEIT`)
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_andere_abfrage_ruft_selbst_ab`
- **AC-4 (Rolle zuerst):** Given eine Anfrage mit Rolle Gast oder Mitwirkend / When `kartenpunkte_holen` läuft / Then wird der Netzabruf nicht einmal versucht (Zähler des ersetzten Abrufs bleibt 0), und die Antwort ist die bisherige Ablehnung der Rollenprüfung (422)
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_gast_loest_keinen_netzabruf_aus`
- **AC-5 (eine Wiederholung):** Given der ersetzte Netzzugriff antwortet zuerst mit 502, 503, 504 oder 429 und beim zweiten Mal mit Treffern / When `overpass_holen` läuft / Then genau eine Wiederholung nach `OSM_PAUSE` und Treffer; Given er antwortet beide Male mit 502 / Then genau zwei Zugriffe und `Ablehnung("schreiben.kartenpunkte.dienst")`; Given er antwortet mit 429 oder 504 beide Male / Then die Ablehnung `schreiben.kartenpunkte.limit`; Given eine Zeitüberschreitung / Then keine Wiederholung
  - Test: `engine/tests/test_schreiben.py::test_overpass_holen_eine_wiederholung_bei_schnellem_fehler`
- **AC-6 (Fehlschlag ohne Sperre):** Given der Vorab-Abruf scheitert endgültig / When `anwenden_extern` läuft / Then Antwort 422 mit der Ablehnung (Text "nichts wurde geändert" bzw. Limit-Text), die Sperrdatei der Reise wurde nicht genommen, der Unterprozess nicht gestartet, und der Stand der Reise ist unverändert
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_fehlschlag_vorab_ohne_sperre`
- **AC-7 (nur eigene Datei):** Given eine Anfrage, die selbst ein Feld mit Namen `FR_OSM_VORAB`, `osm_vorab` oder eine eingebettete Antwort enthält / When der Vorgang läuft / Then wird kein solches Feld je als Antwort genommen (der Abruf ersetzt die Antwort, nur sie erscheint im Ergebnis); Given `FR_OSM_VORAB` zeigt auf eine fehlende, leere oder fremde Datei / Then eigener Abruf wie in AC-3, kein Absturz
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_vorab_nur_aus_eigener_datei`
- **AC-8 (Aufräumen):** Given ein Vorgang endet mit Erfolg, Ablehnung, Fristablauf (504) oder Ausnahme / When er vorbei ist / Then existiert der Ordner `frieda-osm-*` des Vorab-Abrufs nicht mehr
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_vorab_ordner_wird_immer_geloescht`
- **AC-9 (Sperre nicht länger):** Given der Vorab-Abruf dauert (ersetzt, verzögert) mehrere Sekunden / When parallel ein anderer Schreibvorgang derselben Reise läuft / Then bekommt dieser die Sperre ohne 429; die Sperre des `kartenpunkte_holen`-Vorgangs wird erst nach dem Abruf genommen und nicht länger gehalten als vor dieser Änderung
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_abruf_haelt_die_sperre_nicht`
- **AC-10 (beide Wege):** Given eine Reise im Speicher (`FR_SPEICHERREISEN`) und eine Git-Reise / When `kartenpunkte_holen` läuft / Then bekommt der Unterprozess in beiden Wegen `FR_OSM_VORAB` (Umgebung des Unterprozesses geprüft), und die Lesekopie des Vorab-Abrufs liest den Stand der Reise ohne ihn zu verändern (Speicher: Stand-Nummer und Dateien vorher = nachher; Git: Arbeitskopie unberührt)
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_vorab_in_beiden_schreibwegen`
- **AC-11 (alter Code):** Given ein Unterprozess, der `FR_OSM_VORAB` nicht kennt (alter Code der Arbeitskopie) / When er läuft / Then ruft er wie bisher selbst ab und das Ergebnis ist richtig; die Umgebungsvariable verändert sonst kein Verhalten
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_alter_code_ignoriert_vorab_wert` (Unterprozess mit gesetzter, aber unbenutzter Variable und ersetztem Abruf)
- **AC-12 (Städtewochenende):** Given die Beispielreise `stadtwochenende` (keine Strecke, keine Linie) / When `kartenpunkte_holen` mit beliebiger Strecke läuft / Then dieselbe Ablehnung wie bisher (422) und kein Netzabruf (Zähler 0)
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_stadtwochenende_ohne_netzabruf`
- **AC-13 (Overpass-Adresse):** Given `FR_OVERPASS` ist gesetzt / When `overpass_holen` ruft ab / Then geht die Anfrage an diese Adresse mit der Kennung `instanz.kennung()` als User-Agent und `[timeout:N]` in der Abfrage, wobei N der ganzen Frist entspricht; ohne den Wert gilt die bisherige Adresse
  - Test: `engine/tests/test_schreiben.py::test_overpass_adresse_und_kennung` (lokaler Test-Server auf 127.0.0.1)
- **AC-14 (bestehendes Verhalten):** Given die bisherige Erfindung der Antwort per `monkeypatch` auf `overpass_abfragen` / When der Test `test_kartenpunkte_holen_mit_erfundener_antwort` läuft / Then bleibt er grün, unverändert in Treffern, Aktualisieren statt Verdoppeln und Ablehnungen
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_holen_mit_erfundener_antwort`
- **AC-15 (Texte):** Given alle Sprachdateien / When die Textprüfung läuft / Then stehen alle neuen sichtbaren Texte (falls es welche gibt) in `engine/texte_*.py` in allen Sprachen, im Code keiner
  - Test: `engine/tests/test_texte.py` (bestehende Prüfungen)

## Test Plan

Alle Tests laufen ohne echtes Netz: `monkeypatch` auf `sb.overpass_holen` bzw. `sb.overpass_abfragen`, für Unterprozesse `FR_OVERPASS` auf eine unerreichbare Adresse (`http://127.0.0.1:9/`), AC-13 gegen einen lokalen Test-Server. Es werden nur die Beispielreisen (`beispielreise`, `stadtwochenende`) und erfundene Antworten benutzt.

- `engine/.venv/bin/python -m pytest -q engine/tests/test_schreiben.py -k "kartenpunkte or overpass or zeitgrenzen"`
- Danach der volle Lauf: `engine/.venv/bin/python -m pytest -q -n 3 engine/tests`
- Vor dem Vorspulen auf `main`: Tests der einbindenden Instanzen mit dem Branch (Anleitung im Reisen-Repo der Instanz), weil der Schreibweg berührt wird.

## Abnahme am echten Dienst (nach dem Deploy)

Nur mit der eigenen, archivierten Testreise `testreise-karten-225-erfunden-2027` (Art `wasserstelle`, Wiederverwendung statt Neuanlage) und an einer Reise vom Typ Städtewochenende (eigene Testreise); keine echte Reise.

1. Wanderung: `map_points_fetch` mit `amenity=drinking_water` längs einer Strecke. Erwartet: Treffer mit Quelle und Stand, Dauer etwa 35 bis 60 s, Antwort in der Claude-App kommt an.
2. Zweiter Aufruf: aktualisiert, verdoppelt nicht.
3. Städtewochenende: sofortige Ablehnung, kein Netzabruf, kein Warten.
4. Offene technische Frage: Wartet die Claude-App etwa 75 s auf ein Werkzeug? Wenn nein: Folge-Issue (z. B. Abruf im Hintergrund mit späterer Meldung); #240 bleibt dann offen, bis der Weg end to end funktioniert.

## Kern-Prüfung (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Kein neues Konzept, nur das Zeitverhalten eines vorhandenen Werkzeugs; geprüft an Wanderung (Strecke mit Linie) und Städtewochenende (keine Strecke, gleiche Ablehnung wie bisher). |
| 2 Kein Katalog | Keine Art, kein Merkmal, keine Kategorie. |
| 3 Keine KI | Keine; feste Abfrage, Regeln. |
| 4 Die Tür | Der Konnektor bleibt die Tür; Werkzeugname, Parameter und Antwortform bleiben. |
| 5 Herkunft | Treffer tragen weiter Quelle (OpenStreetMap, ODbL) und Stand. |
| 6 Rollen entscheiden | Die Rollenprüfung geschieht vor dem Abruf und im Vorgang; ein Gast löst weder Last noch Eintrag aus. |
| 7 IDs und Verlauf | Unverändert; zweiter Aufruf aktualisiert dieselben Dinge, nichts wird gelöscht. |
| 8 PWA | Die Seite ändert sich nicht; kein Browser-Rundgang nötig (Abnahme über den Konnektor an der Testreise). |
| 9 Claude Code | Reiseinhalte entstehen weiter im AI-Client über den Konnektor. |
| 10 Dokumentation | Diese Spec, `docs/specs/betrieb/schreibweg-zeitgrenzen.md`, `docs/konnektor.md`, `docs/werkzeuge.md`. |

## Risiken

- **Gemeinsamer Einstieg:** `anwenden_extern` betrifft alle Schreibvorgänge. Gegenmittel: Der neue Zweig läuft nur bei `kartenpunkte_holen`; jede Ausnahme im Vorab-Zweig wird abgefangen und führt zum bisherigen Ablauf (eigener Abruf im Vorgang) oder zu einer Ablehnung, nie zu einem Absturz; AC-9 und AC-14 sichern das Verhalten der übrigen Vorgänge.
- **Wartezeit der Claude-App:** unbekannt, siehe Known Limitations und Abnahme.
- **Dienst bleibt unzuverlässig:** Die Frist hilft nur, wenn Overpass überhaupt antwortet. Ein Ausweichdienst oder eigener Server wäre ein eigenes Vorhaben.
- **Software-Stand im Git-Weg:** Unterprozess mit altem Code (Arbeitskopie) ignoriert `FR_OSM_VORAB` und fällt auf die kurze Frist zurück; der Vorab-Abruf allein ändert dann nichts (AC-11). Mit dem nächsten Nachziehen der Arbeitskopie gilt der neue Code.
- **Handarbeit:** Kein Format der Reisedaten ändert sich, daher keine Umstellung in `neu.py nachziehen` und kein Handschritt in Reisen oder Instanzen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Betriebsdetail ohne Berührung der Grundformen oder Merkmale (ADR-0001). Verworfen wurden eine größere `ZEIT_GESAMT` nur für dieses Werkzeug (Sperre eine Minute, andere Vorgänge bekämen 429) und ein Ausweichdienst bzw. eigener Overpass-Server (nicht erreichbar bzw. eigenes Vorhaben).

## Changelog

- 2026-11-09: Initial spec created (Lösungsrichtung 1 „Abruf vor der Sperre“ aus der Analyse in `docs/context/kartenpunkte-frist-240.md`)
