# Adversary Dialog — feat-444-eigener-kartendienst
Spec: docs/specs/betrieb/eigener-kartendienst-444.md
Datum: 2026-11-09 21:26

## Checkliste
- [x] **Input:** Aufruf `kartenpunkte_holen` (Strecke, Kategorie, OSM-Tags, optional Abstand) durch eine Organisator:in; Einstellungen der Instanz wie oben.
- [x] **Output:** wie bisher (Titel, Text mit Trefferzahl, Beispielen, ODbL-Hinweis); zusätzlich nennt der Text den Stand der Kartendaten (Zeitpunkt aus `osm3s.timestamp_osm_base`) statt nur „heute“ und, welcher Dienst geantwortet hat (eigener oder öffentlicher). Quelle der Dinge: `schreiben.kartenpunkte.quelle` mit Stand.
- [x] **Side effects:** Beim ersten Aufruf nach der Ruhezeit startet der Container (rund 2 s); nach `FR_KARTENDIENST_RUHE` ohne Verkehr beendet sich der Proxy und mit ihm der Container. Sonst keine Seiteneffekte im Schreibweg.
- [x] **Beide Reisetypen:** Wanderung innerhalb der Fläche: eigener Dienst, Treffer in unter einer Sekunde nach dem Start. Städtewochenende (keine Strecke, keine Linie): lehnt wie bisher vor jedem Abruf ab; eine Strecke mit Linie außerhalb der Fläche geht an den öffentlichen Dienst. Die Wahl des Dienstes richtet sich allein nach dem Rahmen, nie nach dem Reisetyp.
- [x] **AC-1 (aus ohne Einstellung):** Given `FR_KARTENDIENST` ist nicht gesetzt / When `overpass_holen` und `kartenpunkte_holen` laufen / Then geht jede Abfrage nur an `FR_OVERPASS` (bzw. die Vorgabe), unverändert in Fristen, Wiederholung und Ablehnungen; alle bestehenden Tests bleiben grün
- [x] **AC-2 (innerhalb der Abdeckung):** Given `abdeckung.json` mit einem Rahmen und eine Abfrage, deren Rahmen ganz darin liegt (Rand zählt als innen) / When `overpass_holen` läuft / Then geht die Anfrage zuerst an den eigenen Dienst (Stummel-Server), die Antwort trägt `dienst = eigen` und den Stand aus `timestamp_osm_base`, und der öffentliche Dienst wird nicht gefragt
- [x] **AC-3 (außerhalb oder teilweise außerhalb):** Given eine Abfrage, deren Rahmen ganz außerhalb liegt, oder die über den Rand oder über zwei Regionen hinausragt / When `overpass_holen` läuft / Then wird der eigene Dienst nicht gefragt, die Antwort kommt vom öffentlichen Dienst (`dienst = oeffentlich`)
- [x] **AC-4 (kaputte Abdeckung):** Given `abdeckung.json` fehlt, ist leer, kein gültiges JSON, ohne Rahmen oder mit unsinnigen Werten (Texte, vertauschte Ecken), oder `FR_KARTENDIENST_ORDNER` fehlt / When `overpass_holen` läuft / Then öffentlicher Dienst, kein Absturz
- [x] **AC-5 (leere Antwort ist ein Ergebnis):** Given der eigene Dienst antwortet innerhalb der Abdeckung mit gültigem JSON und leerer Trefferliste / When `overpass_holen` läuft / Then gilt das als Ergebnis (null Treffer), der öffentliche Dienst wird nicht gefragt
- [ ] **AC-6 (Rückfall bei Fehler):** Given der eigene Dienst antwortet mit Fehler (500, 502), ist nicht erreichbar oder liefert Nicht-JSON / When `overpass_holen` läuft / Then antwortet der öffentliche Dienst in der Restfrist (`dienst = oeffentlich`); scheitert auch er, kommt die bisherige Ablehnung (`schreiben.kartenpunkte.dienst` bzw. `.limit`)
- [x] **AC-7 (Teilfrist und Gesamtfrist):** Given der eigene Dienst antwortet nicht (hängt) / When `overpass_holen` mit Frist 45 s läuft / Then wird der eigene Dienst nach höchstens 10 s aufgegeben, der öffentliche Dienst bekommt höchstens den Rest, und die Summe überschreitet die Gesamtfrist nie; mit der kurzen Frist `OSM_ZEIT` (12 s) bekommt der eigene Dienst höchstens 10 s und der öffentliche den Rest (Uhr ersetzt, kein echtes Warten)
- [x] **AC-8 (Zeitbudget unverändert):** Given die Konstanten / When sie verglichen werden / Then gilt die Prüfung aus #240 unverändert (`ZEIT_VORAB + ZEIT_GESAMT + ZEIT_PRUEFUNG` kleiner als die Wartezeit des Konnektors), und `TEILFRIST_EIGEN` ist kleiner als `OSM_FRIST_VORAB`
- [x] **AC-9 (Stand und Dienst in den Treffern):** Given eine Antwort mit `osm3s.timestamp_osm_base` und gestempeltem Dienst / When `kartenpunkte_holen` Treffer einträgt / Then nennen Antworttext und Quelle der Dinge den Stand der Daten und den Dienst (eigen oder öffentlich); fehlt der Zeitstempel, steht wie bisher das Abrufdatum; der ODbL-Hinweis bleibt
- [x] **AC-10 (beide Beispielreisen):** Given die Beispielreise `beispielreise` (Strecke innerhalb eines erfundenen abgedeckten Rahmens) und `stadtwochenende` (keine Linie) / When `kartenpunkte_holen` läuft / Then Wanderung: Anfrage geht an den eigenen Stummel-Dienst; Städtewochenende: dieselbe Ablehnung wie bisher (422), kein Abruf an irgendeinen Dienst (Zähler 0); eine Strecke außerhalb des erfundenen Rahmens geht an den öffentlichen Stummel
- [x] **AC-11 (Texte):** Given alle Sprachdateien / When die Textprüfung läuft / Then stehen alle neuen sichtbaren Texte (Stand der Daten, Dienst) in allen `engine/texte_*.py`, im Code keiner; die Ausnahmelisten werden nicht länger
- [x] **AC-12 (Werkzeuge):** Given `FR_OVERPASS` ist gesetzt / When `werkzeuge/punkte_holen.py` und `werkzeuge/wasser_pruefen.py` laufen / Then gehen sie an diese Adresse; ohne den Wert gilt die bisherige
- [x] **AC-13 (Vorlagen und Einrichten):** Given `einrichten.sh --erzeugen` mit und ohne `FR_KARTENDIENST_REGIONEN` / When es läuft / Then entstehen ohne Regionen keine Kartendienst-Einheiten und keine Befehle dazu; mit Regionen entstehen Socket, Proxy-Dienst, Container-Dienst, Aktualisieren-Dienst und -Timer mit allen Platzhaltern ersetzt (Prüfung „placeholder not replaced“), das Image steht mit Digest (`@sha256:`), `StopWhenUnneeded=yes` und `--exit-idle-time` stehen darin, der Socket lauscht nur auf 127.0.0.1, und die Ausgabe nennt die einmaligen Befehle (Datenordner 755, Socket aktivieren, erstes Einspielen)
- [x] **AC-14 (Einheiten-Abgleich ohne Lärm):** Given die Vorlagen des Kartendienstes / When der Einheiten-Abgleich (#260) läuft / Then meldet er sie nicht als neue oder fehlende Einheiten, und die feste Menge `ARTEN` bleibt bei sechs
- [x] **AC-15 (keine echten Domains, Pfade, Regionen):** Given `betrieb/`, `docs/` und die neuen Vorlagen / When die Prüfungen laufen / Then enthalten sie keine echten Domains, Serveradressen, absoluten Pfade oder Regionen einer Instanz (nur Platzhalter und Beispiele wie `europe/andorra`)
- [x] **AC-16 (Einspielen mit Rückweg):** Given `betrieb/kartendienst.sh einspielen` mit Attrappen für Download, Container und Probeabfrage / When ein Schritt fehlschlägt (Download, Vorverarbeitung, Einspielen, Probeabfrage) / Then bleibt der bisherige Datenstand samt `abdeckung.json` unverändert, der Nebenordner ist gelöscht und der Ausgang ungleich 0; bei Erfolg wird atomar umgeschaltet und `abdeckung.json` trägt Rahmen je Region, Prüfsumme der Regionenliste und Stand
- [x] **AC-17 (Aktualisierung bei geänderter Liste):** Given `abdeckung.json` mit der Prüfsumme einer Regionenliste / When die Liste geändert wird / Then erkennt der Aktualisieren-Lauf die abweichende Prüfsumme und spielt neu ein; bei gleicher Liste und Alter unter einem Monat tut der tägliche Lauf nichts
- [x] **AC-18 (Modulliste):** Given `engine/kartendienst.py` / When der Test der Modulliste von `betrieb/deploy.sh` läuft / Then ist das Modul dort aufgeführt und importierbar
- [x] **AC-19 (Lizenzhinweis):** Given `docs/betrieb.md` und `THIRD_PARTY.md` / When sie geprüft werden / Then nennen sie Overpass (AGPL), das Image per Digest (nicht mitgeliefert) und die Daten (ODbL, Namensnennung)
- [ ] **AC-20 (Abnahme am laufenden Dienst, manuell mit Testreise):** Given eingerichtete Instanz mit Region / When die Abnahme unten läuft / Then bestehen alle ihre Schritte, einschließlich Ruhezustand ohne Container — manuell, nach Deploy (nicht Teil dieser Phase)

## Dialog

### Runde 1
**Adversary:** Alle Zielpunkte gegen den Code gelesen und gezielt getestet. Tests: 406 + 32 bestanden, 0 fehlgeschlagen (adversary-test-output.txt).
Confirmation:
  AC: AC-1
  Code reference: engine/schreiben.py:2032
  Evidence: ohne FR_KARTENDIENST ruft overpass_holen sofort overpass_oeffentlich mit der Gesamtfrist, Antwort ungestempelt. Status: CONFIRMED
Confirmation:
  AC: AC-2, AC-3
  Code reference: engine/kartendienst.py:59
  Evidence: rahmen_abgedeckt prueft <= innerhalb EINES Rahmens (Rand innen: Probe (1,1,2,2) in [(1,1,2,2)] True, 2.0001 False); Rahmen ueber zwei Regionen nie abgedeckt. Status: CONFIRMED
Confirmation:
  AC: AC-4
  Code reference: engine/kartendienst.py:34
  Evidence: _rahmen_gueltig weist bool, Texte, vertauschte Ecken, Werte ausserhalb +-90/+-180 ab; NaN/Infinity scheitern an den Vergleichen; abdeckung() faengt OSError/ValueError, nie Ausnahme. Status: CONFIRMED
Confirmation:
  AC: AC-5, AC-7
  Code reference: engine/schreiben.py:2062
  Evidence: leeres elements gilt als Ergebnis; Probe mit haengendem Stummel: eigen nach 10.0 s aufgegeben, Frist 45 -> gesamt 10.0 s dann oeffentlich; Frist 3 -> gesamt 3.0 s (nie ueber Gesamtfrist, nur >=0.1 s Mindest-Timeout). Status: CONFIRMED
Confirmation:
  AC: AC-8
  Code reference: engine/kartendienst.py:18
  Evidence: TEILFRIST_EIGEN = 10 < OSM_FRIST_VORAB; Tests test_units* gruen. Status: CONFIRMED
Confirmation:
  AC: AC-9, AC-11
  Code reference: engine/texte_de.py:3177
  Evidence: neue Schluessel quelle.eigen/.oeffentlich, lizenz.stand, dienst.eigen/.oeffentlich stehen in texte_de und texte_en (engine/texte_en.py:3176); test_texte gruen, test_texte.py ungeaendert (Status). Status: CONFIRMED
Confirmation:
  AC: AC-12
  Code reference: werkzeuge/punkte_holen.py:44
  Evidence: OVERPASS = instanz.wert("FR_OVERPASS", schreiben.OVERPASS); identisch in werkzeuge/wasser_pruefen.py:35. Status: CONFIRMED
Confirmation:
  AC: AC-13, AC-14, AC-19
  Code reference: betrieb/einrichten.sh:124
  Evidence: Einheiten nur mit KD_REGIONEN, eigener Unterordner kartendienst/; Digest betrieb/gemeinsam.sh:112 (@sha256:); StopWhenUnneeded betrieb/vorlagen/kartendienst/kartendienst.service:8, ExecStartPre test -f init_done :15, Socket nur 127.0.0.1 (betrieb/vorlagen/kartendienst/kartendienst.socket:7); Tests gruen; keine echten Domains/Pfade im Neuen (grep). Status: CONFIRMED
Confirmation:
  AC: AC-16, AC-17
  Code reference: betrieb/kartendienst.sh:89
  Evidence: aufraeumen (EXIT-Trap) loescht Probe, Arbeit, Nebenordner, nimmt halbes Umschalten zurueck (mv ALT ORDNER); Sperren per flock 8/9; umschalten atomar per mv; neu_noetig vergleicht Pruefsumme und Alter. Skript-Tests gruen. Status: CONFIRMED
Confirmation:
  AC: AC-18
  Code reference: betrieb/deploy.sh:28
  Evidence: kartendienst.py in SB_MODULE; Test der Modulliste gruen. Status: CONFIRMED
Confirmation:
  AC: AC-10
  Code reference: engine/schreiben.py:2300
  Evidence: kartenpunkte_holen nutzt overpass_abfragen -> overpass_holen; Beispielreise-Tests (-k kartenpunkte) gruen. Status: CONFIRMED
Test-Korrektur test_betrieb.py:2831: maskiert nur str(tmp_path) und prueft weiter, dass das Wort "kartendienst" sonst nirgends in der Ausgabe steht, zusaetzlich bleibt die Dateiprobe (rglob) davor. Nicht ausgehoehlt.
Quelle-Schluessel statt Changelog-Wortlaut: eigene Schluessel tragen Dienst und Stand, der alte bleibt Rueckfall ohne Stempel; sinnvoll, keine Verletzung.
**Implementierer:** (keine Antwort; Pruefung ohne Implementierer-Kontext)

Confirmation:
  AC: AC-11
  Code reference: engine/texte_en.py:3176
  Evidence: alle fuenf neuen Schluessel auch in Englisch.
  Status: CONFIRMED
Confirmation:
  AC: AC-12
  Code reference: werkzeuge/wasser_pruefen.py:35
  Evidence: FR_OVERPASS mit Vorgabe schreiben.OVERPASS.
  Status: CONFIRMED
Confirmation:
  AC: AC-13
  Code reference: betrieb/gemeinsam.sh:112
  Evidence: KD_BILD mit @sha256-Digest.
  Status: CONFIRMED

### Runde 2
**Adversary:** Gezielte Angriffe mit Stummel-Servern (Skriptdatei im Scratchpad, nichts im Repo).
Finding F001: eigener Dienst antwortet mit kaputtem HTTP (Muell-Statuszeile) oder abgeschnittenem Koerper (IncompleteRead): overpass_eigen faengt nur URLError/TimeoutError/OSError/ValueError; BadStatusLine und IncompleteRead sind HTTPException (kein OSError). Probe: Frist 45/12/3 -> Ausnahme statt Rueckfall. Realistisch, wenn der Container mitten in der Antwort stirbt.
Finding F002: Mischabfrage bbox plus around ergibt Rahmen nur aus der bbox; heute baut kartenpunkte_abfrage nur bbox, daher latent. Reine around-Abfrage: None -> oeffentlich (geprueft).
Finding F003: abdeckung.json traegt die Bounding-Box je Auszug, Daten liegen nur im Polygon; leere Treffer im Nachbargebiet der Box gelten als Ergebnis (AC-5).
Finding F004: kartendienst.sh loescht beim Start .alt ohne zu pruefen, ob ORDNER fehlt.
Finding F005: OVERPASS_USE_AREAS=false ist nicht begruendet dokumentiert; unschaedlich.
Rueckfall-Zeit: bei Gesamtfrist kleiner als Teilfrist bekommt der oeffentliche Dienst Restfrist 0 -> Mindest-Timeout 0.1 s; harmlos.
**Implementierer:** (keine Antwort)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: BROKEN

Finding:
  ID: F001
  Severity: HIGH
  Category: edge_case
  Code reference: engine/schreiben.py:2062
  Description: overpass_eigen faengt (URLError, TimeoutError, OSError, ValueError); http.client.HTTPException (BadStatusLine, IncompleteRead) wird nicht gefangen.
  Spec requirement: AC-6 — eigener Dienst mit Fehler/Nicht-JSON/nicht erreichbar -> Rueckfall auf den oeffentlichen Dienst
  Conflict: Stummel mit kaputter Statuszeile bzw. zu kurzem Koerper: Ausnahme geht bis zum Aufrufer, kein Rueckfall (reproduziert fuer Frist 45, 12, 3).
  Remediation: http.client.HTTPException ebenfalls fangen (None) und Test dazu in test_kartendienst.py.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/kartendienst.py:65
  Description: rahmen_aus_abfrage liest nur Rahmen (s,w,n,o); eine zusaetzliche around-Bedingung bleibt unberuecksichtigt.
  Spec requirement: AC-3 — nie faelschlich den eigenen Dienst waehlen
  Conflict: Nur latent (Abfragen enthalten heute nur bbox).
  Remediation: Abfragen mit around an den oeffentlichen Dienst geben.

Finding:
  ID: F003
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/kartendienst.sh:150
  Description: Rahmen aus der Bounding-Box des Auszugs (osmium boxes[0]), Daten nur im Polygon.
  Spec requirement: AC-5 — leere Antwort im Rahmen ist ein Ergebnis
  Conflict: Strecke in der Box, aber ausserhalb des Polygons (Nachbarland) -> still null Treffer ohne Rueckfall.
  Remediation: Grenze in docs/betrieb.md benennen oder Rahmen verkleinern; Produktentscheidung.

Finding:
  ID: F004
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/kartendienst.sh:175
  Description: weg NEBEN; weg ALT loescht Reste ohne Pruefung, ob ORDNER fehlt.
  Spec requirement: AC-16 — bisheriger Datenstand bleibt erhalten
  Conflict: nach hartem Abbruch zwischen den zwei mv ist .alt der einzige Stand und wird geloescht.
  Remediation: vorher: wenn ORDNER fehlt und ALT existiert, ALT zurueckbenennen.

Finding:
  ID: F005
  Severity: LOW
  Category: anti_pattern
  Code reference: betrieb/vorlagen/kartendienst/kartendienst.service:17
  Description: OVERPASS_USE_AREAS=false weicht von der Messung ab, ohne Begruendung in Doku/Spec.
  Spec requirement: AC-13
  Conflict: keine Funktionsverletzung; Abweichung undokumentiert.
  Remediation: Begruendung in docs/betrieb.md ergaenzen.

Tests: 438 passed (406 + 32), 0 failed, 0 übersprungen

## Geprüfte Dateien

- sha256:72e9682f3ec99dd28e896c0ff87e4e6e20d3779f008a44c5828c6e53a0124973  betrieb/deploy.sh
- sha256:01791cf96936d46fdea5f57bce160f4adae592d36221e5bae81130b7758c8f22  betrieb/einrichten.sh
- sha256:c2c83ff2cf27dfc376be39750ced921c844b3dd9c2c89b25a69ca5fd480338b7  betrieb/gemeinsam.sh
- sha256:27c2ec9c5a328eb8b091696356ed9ecde1cff518bdeaa99419ddea8f27e91d40  betrieb/kartendienst.sh
- sha256:a889fad6ba0a059cb4be78c24d26499238143c51782a867de67ba12fc55f7d48  betrieb/vorlagen/kartendienst/kartendienst.service
- sha256:3e68370428dba6af138f87e1f231f859700b637442c79e8aa5c15dba99b0688f  engine/kartendienst.py
- sha256:b03b29c9a656cf406215c3ad9c3b076db21099116cb836cfc635c3d5b8de2208  engine/schreiben.py
- sha256:0b25af97ef8bc3c6b5fbc5e141c8d8736ea07ad536074831b463ed864993dc44  engine/texte_de.py
- sha256:c3aab8542bea655c252de7757edec827d1e90f633add87624eed1a9c392636fc  engine/texte_en.py
- sha256:0085540f4b7d9d8b240d8496370c6a081c08152251a9cf4605bff0975b317b3d  werkzeuge/punkte_holen.py
- sha256:e212873541bcd1d4671164e4df4ccbd762a41aad3307cd1c9e12b658a1f45126  werkzeuge/wasser_pruefen.py

## Prüfbasis

- base: 448920afaacaf21f0f052d3ffd03915c83eb7343
- blob:1df88581a39ceb41a45d031ec2cf37f50aed93b4  betrieb/deploy.sh
- blob:35ddf9f3ce69797aab6da16284e5a3a11fcdfab1  betrieb/einrichten.sh
- blob:90a3ab29ec6d09285bffb1260e7b474108f3e6ea  betrieb/gemeinsam.sh
- blob:e05a19453775a53b33104bce8de3a306773a936b  betrieb/kartendienst.sh
- blob:b6893b43bf3ead19455f8b957fa45665b62886de  betrieb/vorlagen/kartendienst/kartendienst.service
- blob:f356553deebfc8039812b3073181db4db7674b87  engine/kartendienst.py
- blob:f028265b08893b29ab66a18b3ada5d11a729c30f  engine/schreiben.py
- blob:fb10a7239c60abb0da686a8f32fd439ef7b23194  engine/texte_de.py
- blob:421b3e77883eee7dcb7a4ef4b8c0f89f58898664  engine/texte_en.py
- blob:32af4229bdc2dde0f757255b2ff109b3008e4186  werkzeuge/punkte_holen.py
- blob:7c58ec9c3f058ec964d139306baf9f8b58820341  werkzeuge/wasser_pruefen.py
