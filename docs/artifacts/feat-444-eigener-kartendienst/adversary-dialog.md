# Adversary Dialog — feat-444-eigener-kartendienst
Spec: docs/specs/betrieb/eigener-kartendienst-444.md
Datum: 2026-11-09 22:07

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
- [x] **AC-6 (Rückfall bei Fehler):** Given der eigene Dienst antwortet mit Fehler (500, 502), ist nicht erreichbar oder liefert Nicht-JSON / When `overpass_holen` läuft / Then antwortet der öffentliche Dienst in der Restfrist (`dienst = oeffentlich`); scheitert auch er, kommt die bisherige Ablehnung (`schreiben.kartenpunkte.dienst` bzw. `.limit`)
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
- [x] **AC-20 (Abnahme am laufenden Dienst, manuell mit Testreise):** Given eingerichtete Instanz mit Region / When die Abnahme unten läuft / Then bestehen alle ihre Schritte, einschließlich Ruhezustand ohne Container — MANUELL AUSSTEHEND (Abnahme nach Deploy, Nachweis in #240 und #444), hier nicht bewiesen

## Dialog

### Runde 1
**Adversary:** Zweite Iteration. Alle fuenf Befunde der ersten Iteration einzeln nachgeprueft. Testlauf siehe adversary-test-output.txt (ein einmaliger Fehlschlag von test_kartenpunkte_abruf_haelt_die_sperre_nicht unter fremder Last, danach 3 von 3 einzeln gruen; sauberer Wiederholungslauf siehe unten).
Breite der neuen Ausnahmen: HTTPException, URLError, OSError, ValueError, TimeoutError sind Netz-/Antwortfehler; Programmierfehler (TypeError, AttributeError, KeyError) werden nicht gefangen. ValueError ist die gleiche Menge wie vorher im oeffentlichen Pfad. Nicht zu breit.
Stummel Kaputt (engine/tests/test_kartendienst.py:292): echter Socket-Server, liest die ganze Anfrage, sendet dann Muell bzw. zu kurzen Koerper; Testbeweis zaehlt Anfragen an beide Dienste (1/1). Mein eigener Stummel erzeugt dieselben Ausnahmen (vorher Ausnahme, jetzt Rueckfall): Beweiskraft gegeben.
Confirmation:
  AC: AC-1
  Code reference: engine/schreiben.py:2032
  Evidence: ohne FR_KARTENDIENST geht overpass_holen direkt an overpass_oeffentlich, Antwort ungestempelt.
  Status: CONFIRMED
Confirmation:
  AC: AC-2, AC-3, AC-4
  Code reference: engine/kartendienst.py:59
  Evidence: rahmen_abgedeckt: Rand innen, nur EIN Rahmen zaehlt; _rahmen_gueltig (Zeile 34) weist bool, Texte, vertauschte Ecken, NaN/Infinity und Werte ausserhalb +-90/+-180 ab.
  Status: CONFIRMED
Confirmation:
  AC: AC-5, AC-6, AC-7
  Code reference: engine/schreiben.py:2062
  Evidence: overpass_eigen faengt jetzt auch http.client.HTTPException. Probe mit Stummel (Muell-Statuszeile, abgeschnittener Koerper) bei Frist 45/12/3: dienst=oeffentlich nach 0.0 s; haengender Stummel: 10.0 s, bei Frist 3 gesamt 3.0 s.
  Status: CONFIRMED
Confirmation:
  AC: AC-8
  Code reference: engine/kartendienst.py:18
  Evidence: TEILFRIST_EIGEN=10 kleiner als OSM_FRIST_VORAB; Units-Tests gruen.
  Status: CONFIRMED
Confirmation:
  AC: AC-9, AC-11
  Code reference: engine/texte_de.py:3177
  Evidence: neue Schluessel (quelle.eigen/.oeffentlich, lizenz.stand, dienst.*) in Deutsch; test_texte.py ungeaendert.
  Status: CONFIRMED
Confirmation:
  AC: AC-11
  Code reference: engine/texte_en.py:3176
  Evidence: dieselben Schluessel in Englisch.
  Status: CONFIRMED
Confirmation:
  AC: AC-12
  Code reference: werkzeuge/punkte_holen.py:44
  Evidence: OVERPASS = instanz.wert(FR_OVERPASS, Vorgabe).
  Status: CONFIRMED
Confirmation:
  AC: AC-12
  Code reference: werkzeuge/wasser_pruefen.py:35
  Evidence: dasselbe.
  Status: CONFIRMED
Confirmation:
  AC: AC-13, AC-14, AC-15
  Code reference: betrieb/einrichten.sh:124
  Evidence: Einheiten nur mit Regionen, eigener Unterordner; keine echten Domains/Pfade (grep).
  Status: CONFIRMED
Confirmation:
  AC: AC-13
  Code reference: betrieb/gemeinsam.sh:112
  Evidence: KD_BILD mit @sha256-Digest.
  Status: CONFIRMED
Confirmation:
  AC: AC-13
  Code reference: betrieb/vorlagen/kartendienst/kartendienst.service:8
  Evidence: StopWhenUnneeded=yes; init_done-Pruefung, Socket nur 127.0.0.1.
  Status: CONFIRMED
Confirmation:
  AC: AC-16, AC-17
  Code reference: betrieb/kartendienst.sh:160
  Evidence: wiederherstellen holt .alt zurueck, wenn ORDNER fehlt (Test test_harter_abbruch... gruen); mv ist atomar.
  Status: CONFIRMED
Confirmation:
  AC: AC-18
  Code reference: betrieb/deploy.sh:28
  Evidence: kartendienst.py in SB_MODULE.
  Status: CONFIRMED
Confirmation:
  AC: AC-10
  Code reference: engine/schreiben.py:2300
  Evidence: kartenpunkte_holen nutzt overpass_abfragen -> overpass_holen; Beispielreisen-Tests gruen.
  Status: CONFIRMED
Confirmation:
  AC: AC-3
  Code reference: engine/kartendienst.py:65
  Evidence: rahmen_aus_abfrage: Teilwort around irgendwo in der Abfrage -> None (Probe: reine around und Mischabfrage -> oeffentlich). Leerzeichen-Schreibweisen (around :, around.x:) werden vom Teilwort miterfasst; Gross-/Kleinschreibung kennt Overpass nicht.
  Status: CONFIRMED
Confirmation:
  AC: AC-19
  Code reference: betrieb/kartendienst.sh:1
  Evidence: Lizenzen in docs/betrieb.md/THIRD_PARTY.md (Test gruen).
  Status: CONFIRMED
**Implementierer:** (keine Antwort)

### Runde 2
**Adversary:** F004: wiederherstellen laeuft in einspielen() NACH sperren (flock), also ohne Wettlauf. Sind ORDNER und ALT beide da, tut es nichts (ORDNER ist dann der neue, vollstaendig umgeschaltete Stand, mv ist atomar); das folgende weg ALT loescht nur den alten Stand. Kein Datenverlust.
Finding F006: im Zweig aktualisieren (betrieb/kartendienst.sh:203) laeuft wiederherstellen VOR der Sperre. Laeuft gleichzeitig ein einspielen genau zwischen seinen beiden mv in umschalten, holt der Timer-Lauf .alt nach ORDNER zurueck; das spaetere mv NEBEN ORDNER legt den neuen Stand dann als ORDNER/.kartendienst.neu in den alten (UMGESCHALTET=1, alter Stand bleibt aktiv, neuer vergraben). Fenster Mikrosekunden, daher LOW; Abhilfe: wiederherstellen in aktualisieren erst nach sperren (einspielen macht es ohnehin selbst) oder neu_noetig/wiederherstellen unter der Sperre.
F003: dokumentiert (docs/betrieb.md Abschnitt Grenze der Abdeckung, Zeile 454), ausreichend. F005: dokumentiert (Zeile 459).
**Implementierer:** (keine Antwort)

### Runde 3
**Adversary:** Dritte Iteration, nur F006 (betrieb/kartendienst.sh).
Wettlauf geschlossen: Hauptablauf ist Befehl pruefen, eingaben_pruefen, Elternordner pruefen, sperren, wiederherstellen, dann einspielen bzw. neu_noetig. Wiederherstellen und die Pruefung von abdeckung.json laufen jetzt unter der Sperre; umschalten (mv, mv) laeuft ebenfalls unter ihr. Ein zweiter Lauf kann also nie zwischen den beiden mv eingreifen.
Regression: Vor der Sperre laeuft nichts Schreibendes (nur Eingabepruefung und -d/-w auf den Elternordner, der Zweig-Check gilt jetzt fuer beide Befehle). Falscher Befehl liefert Ausgang 2 wie zuvor. einspielen() hat keine eigene Sperre mehr, wird nur vom Hauptablauf gerufen.
Verklemmung: Reihenfolge immer erst kartendienst.lock (fd 8), dann veroeffentlichen.lock (fd 9), beide mit flock -w KD_SPERRE_WARTEN. betrieb/veroeffentlichen.sh nimmt nur die zweite Sperre und nicht blockierend (flock -n, setzt veroeffentlichen-nochmal, kehrt zurueck), nie die erste: kein Zyklus, keine Verklemmung. Hinweis: Auch ein aktualisieren ohne Arbeit haelt die Veroeffentlichen-Sperre kurz; ein dann uebersprungenes Veroeffentlichen holt der naechste Lauf nach (Marker), wie schon bei einspielen.
Test test_aktualisieren_wartet_auf_die_sperre (engine/tests/test_kartendienst_skript.py:174): haelt eine fremde Sperre (flock LOCK_EX auf probe-kartendienst.lock), stellt den Zustand "ORDNER fehlt, .alt da" her und prueft Ausgang != 0, Meldung der Sperre, unveraenderten Dateibaum, kein Docker/curl-Aufruf; danach ohne Sperre Wiederherstellung. Mit der alten Reihenfolge (wiederherstellen vor der Sperre) haette der erste Lauf .alt zurueckbenannt und der Baumvergleich schluege fehl: Beweiskraft gegeben. Nicht abgedeckt: die Sperre des Veröffentlichens (kein FR_DIENST im Test), LOW und durch Code-Lesen geprueft.
Confirmation:
  AC: AC-16, AC-17
  Code reference: betrieb/kartendienst.sh:207
  Evidence: sperren steht vor wiederherstellen (Zeile 208) und vor neu_noetig; F006 behoben.
  Status: CONFIRMED
**Implementierer:** (keine Antwort)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Iteration 3: F006 (LOW, Wettlauf von wiederherstellen vor der Sperre) ist behoben, Beleg betrieb/kartendienst.sh:207 und Test test_aktualisieren_wartet_auf_die_sperre. F001 bis F005 bleiben behoben (Iteration 2). Keine neuen Befunde.

Befunde der ersten Iteration: F001 (HIGH) behoben, belegt per Stummel-Probe und Tests; F002 behoben (around -> None, auch Mischabfrage); F003 behoben durch Dokumentation (Abdeckung ist Rechteck); F004 behoben (wiederherstellen, unter der Sperre in einspielen); F005 behoben durch Dokumentation.

AC-20 bleibt manuell nach Deploy offen.

## Geprüfte Dateien

- sha256:72e9682f3ec99dd28e896c0ff87e4e6e20d3779f008a44c5828c6e53a0124973  betrieb/deploy.sh
- sha256:01791cf96936d46fdea5f57bce160f4adae592d36221e5bae81130b7758c8f22  betrieb/einrichten.sh
- sha256:c2c83ff2cf27dfc376be39750ced921c844b3dd9c2c89b25a69ca5fd480338b7  betrieb/gemeinsam.sh
- sha256:42d622d038ca8f5e7b2a239a94f741e63e3515dd13f2ef991dea3ec16c99e0e1  betrieb/kartendienst.sh
- sha256:a889fad6ba0a059cb4be78c24d26499238143c51782a867de67ba12fc55f7d48  betrieb/vorlagen/kartendienst/kartendienst.service
- sha256:041699200b1dc84479bac2cec31c549cbd188a949069db05f0259e1087aa2a1d  engine/kartendienst.py
- sha256:38f4ce29c7db2798bdd4d25291e38cd7933f9f8f9ee09c673ebf3fabcaf95f04  engine/schreiben.py
- sha256:0b25af97ef8bc3c6b5fbc5e141c8d8736ea07ad536074831b463ed864993dc44  engine/texte_de.py
- sha256:c3aab8542bea655c252de7757edec827d1e90f633add87624eed1a9c392636fc  engine/texte_en.py
- sha256:0085540f4b7d9d8b240d8496370c6a081c08152251a9cf4605bff0975b317b3d  werkzeuge/punkte_holen.py
- sha256:e212873541bcd1d4671164e4df4ccbd762a41aad3307cd1c9e12b658a1f45126  werkzeuge/wasser_pruefen.py

## Prüfbasis

- base: 448920afaacaf21f0f052d3ffd03915c83eb7343
- blob:1df88581a39ceb41a45d031ec2cf37f50aed93b4  betrieb/deploy.sh
- blob:35ddf9f3ce69797aab6da16284e5a3a11fcdfab1  betrieb/einrichten.sh
- blob:90a3ab29ec6d09285bffb1260e7b474108f3e6ea  betrieb/gemeinsam.sh
- blob:9c13e303c25b2fe0818df42bb9621e91400a3c9c  betrieb/kartendienst.sh
- blob:b6893b43bf3ead19455f8b957fa45665b62886de  betrieb/vorlagen/kartendienst/kartendienst.service
- blob:ae5e93872e4bdfefa877a967a6a16cce052ceacd  engine/kartendienst.py
- blob:2bc6562e90c21bd25a07d776b1d9886e55920720  engine/schreiben.py
- blob:fb10a7239c60abb0da686a8f32fd439ef7b23194  engine/texte_de.py
- blob:421b3e77883eee7dcb7a4ef4b8c0f89f58898664  engine/texte_en.py
- blob:32af4229bdc2dde0f757255b2ff109b3008e4186  werkzeuge/punkte_holen.py
- blob:7c58ec9c3f058ec964d139306baf9f8b58820341  werkzeuge/wasser_pruefen.py
