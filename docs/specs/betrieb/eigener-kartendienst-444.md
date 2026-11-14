---
entity_id: eigener-kartendienst-444
type: feature
created: 2026-11-09
updated: 2026-11-09
status: draft
workflow: feat-444-eigener-kartendienst
version: "1.0"
tags: [schreibweg, kartenpunkte, overpass, kartendienst, docker, systemd, betrieb, k14]
---

# Eigener Kartendienst (Overpass bei Bedarf) für `map_points_fetch` (#444, Ursprung #240)

Grundlage: `docs/context/feat-444-eigener-kartendienst.md` (Messungen, Analyse). Fristen des Abrufs: `docs/specs/betrieb/kartenpunkte-frist-240.md`.

## Approval

- [ ] Approved

## Purpose

Der öffentliche Overpass-Dienst antwortet vom Server der Instanz aus seit Tagen mit 502 oder erst nach 30 bis 45 s; die Abnahme von `kartenpunkte_holen` (Konnektor: `map_points_fetch`, #240) scheitert deshalb wiederholt. Statt auf den öffentlichen Dienst zu warten, betreibt die Instanz bei Bedarf einen eigenen Overpass-Dienst, der nur die Regionen enthält, die die Instanz einstellt. Er läuft in einem Container, startet beim ersten Aufruf und beendet sich nach einer Ruhezeit von selbst. Gemessen (Testaufbau, Balearen-Auszug, 2,0 GB Datenbank): Kaltstart bis zur ersten gültigen Antwort 2,0 s, Abfrage längs einer Strecke 0,09 bis 0,24 s, Speicher im Betrieb 70 MiB (nur beim Einspielen rund 1,6 GiB).

Die Software wählt je Abfrage den Dienst: Liegt der Rahmen der Abfrage ganz in der Abdeckung des eigenen Dienstes, fragt sie zuerst ihn (kurze Teilfrist), bei Fehler oder Zeitüberschreitung danach den öffentlichen Dienst in der Restfrist. Liegt er nicht ganz darin, geht es wie bisher an den öffentlichen Dienst. Ohne Einstellung für den eigenen Dienst ändert sich nichts.

## Source

- **Files:** `engine/kartendienst.py` (neu), `engine/schreiben.py`, `betrieb/kartendienst.sh` (neu), `betrieb/vorlagen/kartendienst/` (neu), `betrieb/einrichten.sh`, `betrieb/deploy.sh`
- **Identifier:** `overpass_holen`, `overpass_abfragen`, `OVERPASS`, `OSM_FRIST_VORAB`, `OSM_ZEIT`, `FR_OVERPASS`, `FR_KARTENDIENST`, `FR_KARTENDIENST_ORDNER`, `FR_KARTENDIENST_REGIONEN`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `instanz.wert(name, vorgabe)`, `instanz.kennung()` | Funktion | Einstellungen der Instanz (nur `FR_`-Namen, Umgebung vor Datei), User-Agent |
| `overpass_holen`, `overpass_abfragen`, `kartenpunkte_holen` (`engine/schreiben.py`) | Funktion | Abrufweg; beide Aufrufer (Vorab-Abruf und Rückfall im Vorgang) laufen über `overpass_holen` |
| `werkzeuge/punkte_holen.py`, `werkzeuge/wasser_pruefen.py` | Werkzeug | haben die Overpass-Adresse fest; lesen künftig dieselbe Einstellung `FR_OVERPASS` |
| `betrieb/einrichten.sh`, `betrieb/vorlagen/`, `betrieb/units.py` (#260) | Skript/Vorlagen | Erzeugen der Einheiten; der Abgleich mit fester Menge von sechs Arten (`ARTEN`) darf keinen Lärm erzeugen (vgl. #445) |
| `betrieb/deploy.sh` | Skript | Modulliste des Schreibwegs; ein Test prüft die Importe |
| Docker (Dienstbenutzer in der Gruppe `docker`), systemd (`systemd-socket-proxyd`), Image `wiktorn/overpass-api` | Extern | Betrieb des Containers; Image per Digest gepinnt |
| Regionsauszüge (Geofabrik, ODbL), `osmium` im Container | Extern | Datenquelle und Vorverarbeitung (pbf nach osm.bz2) |
| `henemm-infra/scripts/monitor.sh` | Extern (anderes Repo) | Teil-Check „Alter der Abdeckungsdatei“ (eigenes Issue dort, siehe Abnahme Schritt 6) |
| `docs/adr/0001-kern.md` | ADR | Prüfstelle |

## Scope

- **Im Scope:**
  - Neues Modul `engine/kartendienst.py`: Abdeckung lesen und prüfen, Dienst wählen, Antwort um Dienst und Stand der Daten ergänzen.
  - `overpass_holen` und `overpass_abfragen` in `engine/schreiben.py` bekommen den Rahmen der Abfrage; Teilfrist und Rückfall auf den öffentlichen Dienst.
  - Einstellungen der Instanz (siehe unten), dokumentiert in `betrieb/einstellungen.beispiel`, `docs/betrieb.md`, `docs/werkzeuge.md`.
  - Betrieb als optionaler Baustein: Vorlagen in `betrieb/vorlagen/kartendienst/`, Einspiel-Skript `betrieb/kartendienst.sh`, Erzeugen der Einheiten und Ausgabe der Einrichtungsbefehle in `betrieb/einrichten.sh`.
  - Werkzeuge `punkte_holen` und `wasser_pruefen` lesen `FR_OVERPASS` statt einer festen Adresse.
  - Texte (Stand der Kartendaten, Dienst) in allen `engine/texte_*.py`.
  - Hinweis auf Lizenzen (Overpass AGPL, Daten ODbL) in `docs/betrieb.md` und `THIRD_PARTY.md` (Image wird nicht mitgeliefert, nur Hinweis).
  - Danach Abnahme von #240 am eigenen Dienst.
- **Affected Files:** `engine/kartendienst.py` (neu), `engine/schreiben.py`, `engine/texte_de.py`, `engine/texte_en.py`, `werkzeuge/punkte_holen.py`, `werkzeuge/wasser_pruefen.py`, `betrieb/kartendienst.sh` (neu), `betrieb/vorlagen/kartendienst/*` (neu), `betrieb/einrichten.sh`, `betrieb/deploy.sh`, `betrieb/einstellungen.beispiel`, `docs/betrieb.md`, `docs/werkzeuge.md`, `THIRD_PARTY.md`, `engine/tests/test_kartendienst.py` (neu), `engine/tests/test_kartendienst_skript.py` (neu), `engine/tests/test_schreiben.py`, `engine/tests/test_betrieb.py`, `engine/tests/test_einrichten*.py`
- **Estimated Changes:** ca. +450/-15 LoC, davon rund 200 Tests. Risiko MEDIUM: Der Abrufweg betrifft nur `map_points_fetch` und hat den öffentlichen Dienst als Rückfall; neu ist Docker als Betriebsbaustein (erstmals im Repo) und der Speicherbedarf beim Einspielen auf einem knappen Server.
- **Nicht im Scope:**
  - Echte Regionen der Instanz: Sie werden im Reisen-Repo der Instanz in den Einstellungen der Instanz eingetragen, nicht hier. Im Repo stehen nur erfundene oder neutrale Beispiele.
  - Minutendiffs (laufende Aktualisierung der Daten), Weltkarte, andere Dienste als Overpass (Geocoding, Routing, Kacheln).
  - Ein Sammelabruf, ein Zwischenspeicher oder Abruf im Hintergrund (Folge-Issues, falls nötig).
  - Änderungen an Abfrage-Inhalt, Filtern, `MAX_TREFFER` oder dem Ablegen der Punkte.
  - Änderung des Einheiten-Abgleichs (#260): Die Menge seiner Arten bleibt.
  - Ein BetterStack-Heartbeat (Regel: Teil-Check in `monitor.sh`).

## Einstellungen der Instanz

Alle in den Einstellungen der Instanz (Datei im Reisen-Repo) oder in der Umgebung (Umgebung vor Datei, wie `instanz.wert`). Ohne `FR_KARTENDIENST` ist der eigene Dienst aus.

| Name | Vorgabe | Bedeutung |
|------|---------|-----------|
| `FR_OVERPASS` | `https://overpass-api.de/api/interpreter` | öffentlicher Dienst (Reserve), wie heute |
| `FR_KARTENDIENST` | leer (aus) | Adresse des eigenen Dienstes, z. B. `http://127.0.0.1:<Port>/api/interpreter` |
| `FR_KARTENDIENST_ORDNER` | leer | Datenordner mit Datenbank und `abdeckung.json`; ohne ihn gilt die Abdeckung als leer |
| `FR_KARTENDIENST_REGIONEN` | leer | Liste der Auszüge (Geofabrik-Pfade, durch Leerzeichen getrennt, z. B. `europe/andorra`); nur Einrichten und Einspielen lesen sie |
| `FR_KARTENDIENST_PORT` | `12345` | lokaler Port des Sockets (nur 127.0.0.1) |
| `FR_KARTENDIENST_SPEICHER` | `2g` | Speichergrenze des Containers |
| `FR_KARTENDIENST_RUHE` | `15min` | Ruhezeit bis zum Stopp (`--exit-idle-time`) |

## Implementation Details

```
engine/kartendienst.py:
  TEILFRIST_EIGEN = 10   Sekunden für den eigenen Dienst (Kaltstart 2 s gemessen + Puffer bei Speicherdruck)
  eigener_dienst()       -> Adresse aus FR_KARTENDIENST oder None
  abdeckung(ordner)      -> Liste von Rahmen (süd, west, nord, ost) aus <ordner>/abdeckung.json
                            fehlende, unlesbare, leere oder formal falsche Datei -> []   (nie eine Ausnahme)
  rahmen_abgedeckt(rahmen, abdeckung) -> bool: der Rahmen der Abfrage liegt GANZ in EINEM Rahmen der Abdeckung
                            (Rand zählt als innen; liegt er über zwei Regionen verteilt, ist er nicht abgedeckt)
  dienst_waehlen(rahmen) -> ("eigen", adresse) oder ("oeffentlich", adresse)
  stempeln(antwort, dienst) -> Antwort + {"dienst": "eigen"|"oeffentlich", "stand": osm3s.timestamp_osm_base oder None}

overpass_holen(abfrage, frist, rahmen=None):
  Ist ein eigener Dienst eingestellt und der Rahmen abgedeckt:
    1. Anfrage an den eigenen Dienst mit Frist min(TEILFRIST_EIGEN, frist), ohne Wiederholung.
    2. Gültige Antwort (JSON mit "elements") gilt, auch mit leerer Liste (innerhalb der Abdeckung ist "keine Treffer" ein Ergebnis).
    3. Fehler, Zeitüberschreitung, kein JSON: weiter mit dem öffentlichen Dienst in der RESTFRIST (frist minus verbrauchte Zeit);
       die Regeln der Wiederholung (eine Wiederholung nur bei 429/502/503/504 und mindestens 15 s Rest) gelten dort unverändert.
  Sonst (kein eigener Dienst, nicht abgedeckt, kein Rahmen übergeben): wie heute nur der öffentliche Dienst, Fristen unverändert.
  Die Gesamtfrist wird nie überschritten: eigener und öffentlicher Dienst teilen sich dieselbe Frist.
  Die Antwort wird mit stempeln() versehen.

Betrieb (betrieb/vorlagen/kartendienst/, nur erzeugt, wenn FR_KARTENDIENST_REGIONEN gesetzt ist;
         Platzhalter __KD_PORT__, __KD_ORDNER__, __KD_SPEICHER__, __KD_RUHE__, __KD_BILD__):
  <instanz>-kartendienst.socket            lauscht auf 127.0.0.1:Port
  <instanz>-kartendienst-proxy.service     systemd-socket-proxyd --exit-idle-time=Ruhezeit zum Container; BindsTo/After den Container
  <instanz>-kartendienst.service           docker run --rm, Image per Digest gepinnt, Speichergrenze,
                                           StopWhenUnneeded=yes, ExecStartPost = Bereitschaft über eine echte Mini-Abfrage
                                           (/api/status liefert in diesem Image 502 und taugt nicht)
  <instanz>-kartendienst-aktualisieren.service/.timer   Prüfung täglich nachts; einspielen, wenn der Stand älter als ein Monat
                                           ist oder die Prüfsumme der Regionenliste von der in abdeckung.json abweicht
  Der Unterordner vorlagen/kartendienst/ liegt nicht im Muster vorlagen/*.service; der Einheiten-Abgleich (#260) behält seine sechs Arten.

betrieb/kartendienst.sh einspielen:
  1. Prüft Speicher und Platz und läuft nie parallel zu Prüfläufen (Sperre; rund 1,6 GiB je kleiner Region).
  2. Lädt die Auszüge der Regionen (Prüfsumme), verbindet sie (osmium) zu osm.bz2 (OVERPASS_PLANET_PREPROCESS).
  3. Container im Modus init in einen Nebenordner; Datenordner Rechte 755 (sonst "Permission denied ... osm3s_osm_base").
  4. abdeckung.json im Nebenordner: Rahmen je Region (osmium fileinfo), Prüfsumme der Regionenliste, Zeitpunkt, Stand der Daten.
  5. Probeabfrage gegen den Nebenordner; erst bei Erfolg wird atomar umgeschaltet (Umbenennen), der alte Ordner bleibt bis dahin.
  6. Schlägt ein Schritt fehl: Nebenordner löschen, bisheriger Stand bleibt unverändert, Ausgang ungleich 0.

abdeckung.json:  {"stand": "<Zeitpunkt>", "regionen_pruefsumme": "<Summe>", "rahmen": [[süd, west, nord, ost], ...]}

Monitor (anderes Repo): Teil-Check in henemm-infra/scripts/monitor.sh prüft das Alter von abdeckung.json
  (Warnung statt Alarm, wenn älter als 40 Tage); kein BetterStack-Heartbeat. Eigenes Issue in henemm/henemm-infra.
```

Zeitbudget: Der eigene Dienst verbraucht höchstens `TEILFRIST_EIGEN` = 10 s der bestehenden Gesamtfrist des Abrufs (`OSM_FRIST_VORAB` = 45 s im Vorab-Abruf, `OSM_ZEIT` = 12 s im Rückfall im Vorgang); der Rest bleibt dem öffentlichen Dienst als Reserve. Im Rückfall im Vorgang bleiben ihm damit 2 s; das reicht nur, wenn er schnell ist, sonst Ablehnung wie heute. Die Zeitbudget-Prüfung aus #240 (`ZEIT_VORAB + ZEIT_GESAMT + ZEIT_PRUEFUNG` kleiner als die Wartezeit des Konnektors) bleibt unverändert gültig, weil keine Konstante der Gesamtfristen wächst.

## Expected Behavior

- **Input:** Aufruf `kartenpunkte_holen` (Strecke, Kategorie, OSM-Tags, optional Abstand) durch eine Organisator:in; Einstellungen der Instanz wie oben.
- **Output:** wie bisher (Titel, Text mit Trefferzahl, Beispielen, ODbL-Hinweis); zusätzlich nennt der Text den Stand der Kartendaten (Zeitpunkt aus `osm3s.timestamp_osm_base`) statt nur „heute“ und, welcher Dienst geantwortet hat (eigener oder öffentlicher). Quelle der Dinge: `schreiben.kartenpunkte.quelle` mit Stand.
- **Side effects:** Beim ersten Aufruf nach der Ruhezeit startet der Container (rund 2 s); nach `FR_KARTENDIENST_RUHE` ohne Verkehr beendet sich der Proxy und mit ihm der Container. Sonst keine Seiteneffekte im Schreibweg.
- **Beide Reisetypen:** Wanderung innerhalb der Fläche: eigener Dienst, Treffer in unter einer Sekunde nach dem Start. Städtewochenende (keine Strecke, keine Linie): lehnt wie bisher vor jedem Abruf ab; eine Strecke mit Linie außerhalb der Fläche geht an den öffentlichen Dienst. Die Wahl des Dienstes richtet sich allein nach dem Rahmen, nie nach dem Reisetyp.

## Known Limitations

- Die Daten sind so alt wie der letzte Einspielvorgang (bis zu etwa einem Monat); für Wasserstellen, Hütten und Haltestellen genügt das, der Stand steht in jedem Treffer.
- Außerhalb der Abdeckung bleibt es beim öffentlichen Dienst und seiner Unzuverlässigkeit.
- Der Rahmen einer Region ist ein Rechteck um den Auszug; liegt eine Abfrage im Rechteck, aber außerhalb der tatsächlichen Daten (Meer, Nachbarland), liefert der eigene Dienst null Treffer. Regionen deshalb kompakt wählen.
- Einspielen braucht rund 1,6 GiB Speicher je kleiner Region und etwa 2 GB Platte; auf einem knappen Server nur außerhalb von Prüfläufen.
- Im Rückfall im Vorgang (kurze Frist `OSM_ZEIT`) bleibt dem öffentlichen Dienst nach einem fehlgeschlagenen eigenen Versuch wenig Zeit; der Vorab-Abruf (45 s) ist der Normalweg.
- Das Image hat keinen brauchbaren Statusaufruf; die Bereitschaft wird über eine echte Abfrage geprüft.

## Definition of Done

- [ ] Jede Acceptance Criterion unten ist durch einen automatischen Test belegt (ohne Docker, ohne echtes Netz); AC-20 durch die Abnahme
- [ ] Texte nur in `engine/texte_*.py`, in allen Sprachen; die Ausnahmelisten in `engine/tests/test_texte.py` werden nicht länger
- [ ] Doku nachgezogen: `betrieb/einstellungen.beispiel`, `docs/betrieb.md`, `docs/werkzeuge.md`, `THIRD_PARTY.md`
- [ ] `kartendienst.py` steht in der Modulliste von `betrieb/deploy.sh` (Test prüft die Importe)
- [ ] Regressionslauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün, auch die Tests der einbindenden Instanzen mit dem Branch (neue Umgebungswerte, Schreibweg berührt)
- [ ] Issue in `henemm/henemm-infra` für den Teil-Check in `monitor.sh` angelegt und erledigt
- [ ] Einrichtung auf der Instanz (Region im Reisen-Repo), Abnahme #240 am eigenen Dienst im Issue festgehalten; die Testdateien außerhalb des Repos aufgeräumt

## Acceptance Criteria

- **AC-1 (aus ohne Einstellung):** Given `FR_KARTENDIENST` ist nicht gesetzt / When `overpass_holen` und `kartenpunkte_holen` laufen / Then geht jede Abfrage nur an `FR_OVERPASS` (bzw. die Vorgabe), unverändert in Fristen, Wiederholung und Ablehnungen; alle bestehenden Tests bleiben grün
  - Test: `engine/tests/test_kartendienst.py::test_ohne_einstellung_wie_bisher`, bestehende Tests in `engine/tests/test_schreiben.py` unverändert
- **AC-2 (innerhalb der Abdeckung):** Given `abdeckung.json` mit einem Rahmen und eine Abfrage, deren Rahmen ganz darin liegt (Rand zählt als innen) / When `overpass_holen` läuft / Then geht die Anfrage zuerst an den eigenen Dienst (Stummel-Server), die Antwort trägt `dienst = eigen` und den Stand aus `timestamp_osm_base`, und der öffentliche Dienst wird nicht gefragt
  - Test: `engine/tests/test_kartendienst.py::test_innerhalb_der_abdeckung_fragt_eigenen_dienst`
- **AC-3 (außerhalb oder teilweise außerhalb):** Given eine Abfrage, deren Rahmen ganz außerhalb liegt, oder die über den Rand oder über zwei Regionen hinausragt / When `overpass_holen` läuft / Then wird der eigene Dienst nicht gefragt, die Antwort kommt vom öffentlichen Dienst (`dienst = oeffentlich`)
  - Test: `engine/tests/test_kartendienst.py::test_ausserhalb_geht_an_oeffentlichen_dienst`
- **AC-4 (kaputte Abdeckung):** Given `abdeckung.json` fehlt, ist leer, kein gültiges JSON, ohne Rahmen oder mit unsinnigen Werten (Texte, vertauschte Ecken), oder `FR_KARTENDIENST_ORDNER` fehlt / When `overpass_holen` läuft / Then öffentlicher Dienst, kein Absturz
  - Test: `engine/tests/test_kartendienst.py::test_kaputte_abdeckung_geht_an_oeffentlichen_dienst`
- **AC-5 (leere Antwort ist ein Ergebnis):** Given der eigene Dienst antwortet innerhalb der Abdeckung mit gültigem JSON und leerer Trefferliste / When `overpass_holen` läuft / Then gilt das als Ergebnis (null Treffer), der öffentliche Dienst wird nicht gefragt
  - Test: `engine/tests/test_kartendienst.py::test_leere_antwort_innerhalb_abdeckung_gilt`
- **AC-6 (Rückfall bei Fehler):** Given der eigene Dienst antwortet mit Fehler (500, 502), ist nicht erreichbar oder liefert Nicht-JSON / When `overpass_holen` läuft / Then antwortet der öffentliche Dienst in der Restfrist (`dienst = oeffentlich`); scheitert auch er, kommt die bisherige Ablehnung (`schreiben.kartenpunkte.dienst` bzw. `.limit`); der Rückfall hinterlässt eine Protokollzeile mit Grund auf stderr, ohne Adresse des Dienstes (#567); ebenso hinterlässt ein gelungener Zugriff eine Zeile `Own map service answered (<n> elements)`, also Erfolg wie Rückfall genau eine Zeile mit dem Präfix `Own map service` (#573)
  - Test: `engine/tests/test_kartendienst.py::test_fehler_des_eigenen_dienstes_faellt_zurueck`
- **AC-7 (Teilfrist und Gesamtfrist):** Given der eigene Dienst antwortet nicht (hängt) / When `overpass_holen` mit Frist 45 s läuft / Then wird der eigene Dienst nach höchstens 10 s aufgegeben, der öffentliche Dienst bekommt höchstens den Rest, und die Summe überschreitet die Gesamtfrist nie; mit der kurzen Frist `OSM_ZEIT` (12 s) bekommt der eigene Dienst höchstens 10 s und der öffentliche den Rest (Uhr ersetzt, kein echtes Warten)
  - Test: `engine/tests/test_kartendienst.py::test_teilfrist_und_gesamtfrist`
- **AC-8 (Zeitbudget unverändert):** Given die Konstanten / When sie verglichen werden / Then gilt die Prüfung aus #240 unverändert (`ZEIT_VORAB + ZEIT_GESAMT + ZEIT_PRUEFUNG` kleiner als die Wartezeit des Konnektors), und `TEILFRIST_EIGEN` ist kleiner als `OSM_FRIST_VORAB`
  - Test: `engine/tests/test_schreiben.py::test_zeitgrenzen_liegen_unter_der_des_konnektors` (erweitert)
- **AC-9 (Stand und Dienst in den Treffern):** Given eine Antwort mit `osm3s.timestamp_osm_base` und gestempeltem Dienst / When `kartenpunkte_holen` Treffer einträgt / Then nennen Antworttext und Quelle der Dinge den Stand der Daten und den Dienst (eigen oder öffentlich); fehlt der Zeitstempel, steht wie bisher das Abrufdatum; der ODbL-Hinweis bleibt
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_nennt_stand_und_dienst`
- **AC-10 (beide Beispielreisen):** Given die Beispielreise `beispielreise` (Strecke innerhalb eines erfundenen abgedeckten Rahmens) und `stadtwochenende` (keine Linie) / When `kartenpunkte_holen` läuft / Then Wanderung: Anfrage geht an den eigenen Stummel-Dienst; Städtewochenende: dieselbe Ablehnung wie bisher (422), kein Abruf an irgendeinen Dienst (Zähler 0); eine Strecke außerhalb des erfundenen Rahmens geht an den öffentlichen Stummel
  - Test: `engine/tests/test_schreiben.py::test_kartenpunkte_dienstwahl_an_beiden_beispielreisen`
- **AC-11 (Texte):** Given alle Sprachdateien / When die Textprüfung läuft / Then stehen alle neuen sichtbaren Texte (Stand der Daten, Dienst) in allen `engine/texte_*.py`, im Code keiner; die Ausnahmelisten werden nicht länger
  - Test: `engine/tests/test_texte.py` (bestehende Prüfungen)
- **AC-12 (Werkzeuge):** Given `FR_OVERPASS` ist gesetzt / When `werkzeuge/punkte_holen.py` und `werkzeuge/wasser_pruefen.py` laufen / Then gehen sie an diese Adresse; ohne den Wert gilt die bisherige
  - Test: `engine/tests/test_werkzeuge.py::test_overpass_adresse_aus_einstellung` (bzw. die vorhandene Testdatei der Werkzeuge)
- **AC-13 (Vorlagen und Einrichten):** Given `einrichten.sh --erzeugen` mit und ohne `FR_KARTENDIENST_REGIONEN` / When es läuft / Then entstehen ohne Regionen keine Kartendienst-Einheiten und keine Befehle dazu; mit Regionen entstehen Socket, Proxy-Dienst, Container-Dienst, Aktualisieren-Dienst und -Timer mit allen Platzhaltern ersetzt (Prüfung „placeholder not replaced“), das Image steht mit Digest (`@sha256:`), `StopWhenUnneeded=yes` und `--exit-idle-time` stehen darin, der Socket lauscht nur auf 127.0.0.1, und die Ausgabe nennt die einmaligen Befehle (Datenordner 755, Socket aktivieren, erstes Einspielen)
  - Test: `engine/tests/test_betrieb.py::test_einrichten_kartendienst_nur_mit_regionen`
- **AC-14 (Einheiten-Abgleich ohne Lärm):** Given die Vorlagen des Kartendienstes / When der Einheiten-Abgleich (#260) läuft / Then meldet er sie nicht als neue oder fehlende Einheiten, und die feste Menge `ARTEN` bleibt bei sechs
  - Test: `engine/tests/test_units_helfer.py`, `engine/tests/test_units.py` (bestehende Prüfungen bleiben grün, ein Fall mit Kartendienst-Vorlagen ergänzt)
- **AC-15 (keine echten Domains, Pfade, Regionen):** Given `betrieb/`, `docs/` und die neuen Vorlagen / When die Prüfungen laufen / Then enthalten sie keine echten Domains, Serveradressen, absoluten Pfade oder Regionen einer Instanz (nur Platzhalter und Beispiele wie `europe/andorra`)
  - Test: `engine/tests/test_betrieb.py` (bestehende Prüfung auf echte Domains, um den Unterordner erweitert), `engine/tests/test_protokolle_ohne_pfade.py`
- **AC-16 (Einspielen mit Rückweg):** Given `betrieb/kartendienst.sh einspielen` mit Attrappen für Download, Container und Probeabfrage / When ein Schritt fehlschlägt (Download, Vorverarbeitung, Einspielen, Probeabfrage) / Then bleibt der bisherige Datenstand samt `abdeckung.json` unverändert, der Nebenordner ist gelöscht und der Ausgang ungleich 0; bei Erfolg wird atomar umgeschaltet und `abdeckung.json` trägt Rahmen je Region, Prüfsumme der Regionenliste und Stand
  - Test: `engine/tests/test_kartendienst_skript.py::test_einspielen_mit_rueckweg`
- **AC-17 (Aktualisierung bei geänderter Liste):** Given `abdeckung.json` mit der Prüfsumme einer Regionenliste / When die Liste geändert wird / Then erkennt der Aktualisieren-Lauf die abweichende Prüfsumme und spielt neu ein; bei gleicher Liste und Alter unter einem Monat tut der tägliche Lauf nichts
  - Test: `engine/tests/test_kartendienst_skript.py::test_neu_einspielen_bei_geaenderter_liste`
- **AC-18 (Modulliste):** Given `engine/kartendienst.py` / When der Test der Modulliste von `betrieb/deploy.sh` läuft / Then ist das Modul dort aufgeführt und importierbar
  - Test: `engine/tests/test_betrieb.py` (bestehender Test der Modulliste)
- **AC-19 (Lizenzhinweis):** Given `docs/betrieb.md` und `THIRD_PARTY.md` / When sie geprüft werden / Then nennen sie Overpass (AGPL), das Image per Digest (nicht mitgeliefert) und die Daten (ODbL, Namensnennung)
  - Test: `engine/tests/test_betrieb.py::test_kartendienst_lizenzhinweis_in_doku`
- **AC-20 (Abnahme am laufenden Dienst, manuell mit Testreise):** Given eingerichtete Instanz mit Region / When die Abnahme unten läuft / Then bestehen alle ihre Schritte, einschließlich Ruhezustand ohne Container
  - Test: kein automatischer Test; Nachweis im Issue #240 und #444

## Test Plan

Alle automatischen Tests laufen ohne Docker und ohne echtes Netz: zwei lokale Stummel-Server auf 127.0.0.1 (eigen und öffentlich, Adressen über `FR_KARTENDIENST` und `FR_OVERPASS`), `abdeckung.json` in einem Testordner mit erfundenen Rahmen (z. B. ein Rechteck um die Beispielreise), die Uhr für die Fristen ersetzt. Das Einspiel-Skript wird mit Attrappen für `docker`, `curl` und `osmium` im Suchpfad getestet. Es kommen nur die Beispielreisen `beispielreise` und `stadtwochenende` und erfundene Antworten zum Einsatz.

- `engine/.venv/bin/python -m pytest -q engine/tests/test_kartendienst.py engine/tests/test_kartendienst_skript.py`
- `engine/.venv/bin/python -m pytest -q engine/tests/test_schreiben.py -k "kartenpunkte or overpass or zeitgrenzen"`
- `engine/.venv/bin/python -m pytest -q engine/tests/test_betrieb.py engine/tests/test_units_helfer.py engine/tests/test_units.py engine/tests/test_texte.py`
- Danach der volle Lauf: `engine/.venv/bin/python -m pytest -q -n 3 engine/tests`; vor dem Vorspulen auf `main` die Tests der einbindenden Instanzen mit dem Branch (Umgebungswerte neu).
- Reihenfolge nach TDD: erst `engine/kartendienst.py` mit seinen Tests (rot, dann grün), danach der Abrufweg in `schreiben.py`, zuletzt Vorlagen und Skript.

## Abnahme (#240 am eigenen Dienst)

Nur mit der eigenen, archivierten Testreise (Wiederverwendung, kein neues Anlegen) und einer Testreise vom Typ Städtewochenende; keine echte Reise. Die Region der Instanz wird zuerst im Reisen-Repo der Instanz eingetragen; die Einrichtungsbefehle aus `einrichten.sh` führt Claude selbst aus.

1. Einrichten und erstes Einspielen; `abdeckung.json` enthält die Fläche der Instanz.
2. Wanderung innerhalb der Fläche: `map_points_fetch` mit `amenity=drinking_water` längs einer Strecke. Erwartet: Treffer mit Quelle, Stand der Daten und Hinweis auf den eigenen Dienst, Antwort in wenigen Sekunden (Kaltstart rund 2 s).
3. Zweiter Aufruf ersetzt die Treffer und verdoppelt nicht; eine zweite Kategorie (z. B. Einkehr) läuft ebenso.
4. Städtewochenende (keine Strecke, oder Linie außerhalb der Fläche): Ablehnung wie bisher bzw. Antwort des öffentlichen Dienstes mit dessen Fehlermeldung, kein Hängen am eigenen Dienst.
5. Ruhezustand: nach Ablauf der Ruhezeit (15 min ohne Aufruf) läuft kein Container mehr (`docker ps` leer) und der Proxy-Dienst ist beendet; der nächste Aufruf startet ihn wieder.
6. Überwachung: Issue in `henemm/henemm-infra` für den Teil-Check in `monitor.sh` (Alter von `abdeckung.json`, Warnung ab 40 Tagen) anlegen, umsetzen und den Check einmal laufen lassen.
7. Ergebnis in #240 und #444 festhalten; danach die Testdateien außerhalb des Repos aufräumen. #240 wird erst geschlossen, wenn die Abnahme end to end gelaufen ist.

## Rückweg

- **Eigenen Dienst abschalten ohne Neuaufbau:** `FR_KARTENDIENST` entfernen oder leeren; ab dem nächsten Aufruf gilt wieder nur der öffentliche Dienst (AC-1). Die Einheiten sind harmlos (nur bei Bedarf gestartet) und lassen sich mit `systemctl disable --now` des Sockets stilllegen.
- **Fehlerhafter Datenstand:** Das Einspielen schaltet erst nach erfolgreicher Probeabfrage um und behält den alten Ordner bis dahin. Eine fehlende oder beschädigte `abdeckung.json` führt von selbst zum öffentlichen Dienst (AC-4).
- **Code:** Revert des Merge-Commits; die Betriebsvorlagen werden nur bei gesetzten Regionen erzeugt und wirken nicht auf bestehende Instanzen.

## Kern-Prüfung (ADR-0001, zehn Fragen)

| Nr. | Antwort |
|---|---|
| 1 Ontologie statt Sonderfall | Keine neue Grundform; geändert wird nur, woher ein vorhandenes Werkzeug seine Daten holt. Geprüft an Wanderung (Fläche abgedeckt) und Städtewochenende (keine Linie, Ablehnung wie bisher). |
| 2 Kein Katalog | Keine Art, kein Merkmal, keine Kategorie; die Regionen sind eine Einstellung der Instanz, kein Reiseinhalt. |
| 3 Keine KI | Keine; feste Abfrage, Regeln, Rahmenvergleich. |
| 4 Die Tür | Der Konnektor bleibt die Tür; Werkzeugname, Parameter und Antwortform bleiben. |
| 5 Herkunft | Treffer nennen Quelle (OpenStreetMap, ODbL), Stand der Daten und den antwortenden Dienst. |
| 6 Rollen entscheiden | Unverändert: Rollenprüfung vor dem Abruf (#240); der eigene Dienst ist von außen nicht erreichbar (nur 127.0.0.1). |
| 7 IDs und Verlauf | Unverändert; ein zweiter Aufruf ersetzt die Treffer derselben Kategorie, nichts wird gelöscht. |
| 8 PWA | Die Seite ändert sich nicht; Abnahme über den Konnektor an Testreisen. |
| 9 Claude Code | Reiseinhalte entstehen weiter im AI-Client über den Konnektor; kein neuer Weg in Claude Code. |
| 10 Dokumentation | Diese Spec, `docs/betrieb.md`, `docs/werkzeuge.md`, `betrieb/einstellungen.beispiel`, `THIRD_PARTY.md`. |

Kein Widerspruch zum Kern, keine Produktfrage an den Product Owner. Instanzneutral: Regionen, Port, Datenordner, Speichergrenze und Ruhezeit kommen aus den Einstellungen der Instanz.

## Risiken

- **Abdeckung:** Der eigene Dienst liefert außerhalb seiner Regionen eine leere, gültige Antwort. Gegenmittel: `abdeckung.json` mit Rahmen je Region; er wird nur gefragt, wenn der Rahmen ganz in einem Rahmen liegt (AC-2 bis AC-4). Rechteckige Rahmen überschätzen die Fläche, siehe Known Limitations.
- **Start bei Bedarf:** `--exit-idle-time` beendet nur den Proxy; der Container endet über `StopWhenUnneeded` und `BindsTo`. Die erste Abfrage nach Kaltstart braucht die Bereitschaftsprüfung im Container-Dienst, sonst scheitert sie in den ersten Sekunden (dann greift der Rückfall, AC-6).
- **Speicher beim Einspielen:** rund 1,6 GiB auf einem Server, der schon stark belegt ist. Gegenmittel: Speichergrenze, nie parallel zu Prüfläufen, Lauf des Timers nachts.
- **Platte:** rund 2 GB je Balearen-Größe; Prüfung des freien Platzes vor dem Einspielen.
- **Rechte:** Der Datenordner braucht 755; das Einrichten setzt es (Stolperstein aus der Messung).
- **Image:** `wiktorn/overpass-api` ist ein Fremdbestandteil; Pinnen per Digest, damit ein Update des Images nichts ungeprüft ändert. Lizenz: Overpass AGPL, Daten ODbL (Hinweis, nicht mitgeliefert).
- **Handarbeit:** Kein Format der Reisedaten ändert sich, also keine Umstellung in `neu.py nachziehen`. Einmalig je Instanz ist die Einrichtung (sudo-Befehle aus `einrichten.sh`), wie bei den übrigen Einheiten.
- **Einheiten-Abgleich:** Der eigene Vorlagen-Unterordner verhindert Lärm (AC-14).

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Betriebsdetail ohne Berührung von Grundformen oder Merkmalen (ADR-0001). Verworfen wurden: weiter auf den öffentlichen Dienst warten (Dauerstörung), ein Ausweichdienst (vom Server aus nicht erreichbar), ein ständig laufender eigener Dienst (der Bedarfsstart kostet nur 2 s und spart Speicher auf dem knappen Server) und eigener Startcode im Konnektor (Socket-Aktivierung mit `systemd-socket-proxyd` ist etablierte Praxis).

## Changelog

- 2026-11-09 (TDD RED): Schnittstellen aus den Tests festgelegt: `overpass_holen(abfrage, frist, rahmen=None)` liest den Rahmen ohne Angabe aus der Abfrage (`kartendienst.rahmen_aus_abfrage`), damit Aufrufer und bestehende Ersatzfunktionen unverändert bleiben; gestempelt (`dienst`, `stand`) wird nur mit gesetztem `FR_KARTENDIENST` (AC-1: ohne Einstellung ist die Antwort unverändert); neue Textschlüssel `schreiben.antwort.kartenpunkte.dienst.eigen`/`.oeffentlich`, der Stand geht als Datum in `schreiben.kartenpunkte.quelle`; die Einheiten des Kartendienstes entstehen in `<EI_ZIEL>/kartendienst/` statt `systemd/` (AC-14); das Einspiel-Skript kennt `einspielen` und `aktualisieren`, Untergrenzen der Prüfung über `KD_SPEICHER_MIN_MB`/`KD_PLATZ_MIN_MB`. Hinweis für GREEN: Die bestehende Prüfung auf Domains in `betrieb/` erlaubt keine `.de`-Adresse; die Downloadadresse der Auszüge muss daher außerhalb von `betrieb/` stehen oder als Einstellung kommen.
- 2026-11-09: Initial spec created (Analyse in `docs/context/feat-444-eigener-kartendienst.md`; Teilfrist 10 s, Ruhezeit 15 min, monatliche Aktualisierung mit Prüfsumme der Regionenliste, Abdeckungsdatei und Vorlagen-Unterordner vom Tech Lead festgelegt)
