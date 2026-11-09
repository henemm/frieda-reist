# Adversary Dialog — kartenpunkte-frist-240
Spec: docs/specs/betrieb/kartenpunkte-frist-240.md
Datum: 2026-11-09 09:59

## Checkliste
- [x] **Input:** Aufruf `kartenpunkte_holen` (Strecke, Kategorie, OSM-Tags, optional Abstand) durch eine Organisator:in.
- [x] **Output:** wie bisher (Titel, Text mit Trefferzahl, Beispielen, ODbL-Hinweis). Bei erreichbarem, aber langsamem Dienst (bis etwa 45 s) kommen jetzt Treffer, die Antwort dauert dann bis etwa eine Minute. Ist der Dienst überlastet oder nicht erreichbar, kommt eine Ablehnung (`schreiben.kartenpunkte.limit` bzw. `.dienst`, "nichts wurde geändert") nach höchstens etwa 55 s.
- [x] **Side effects:** zwei Protokollzeilen wie bisher (`Rejected` bzw. `Done`); die Sperre der Reise wird nur für den kurzen eigentlichen Vorgang gehalten; ein temporärer Ordner, der immer gelöscht wird. Der Vorab-Abruf liest die Reise nur, er schreibt nichts in sie.
- [x] **Beide Reisetypen:** Wanderung (Strecke mit Linie): Vorab-Abruf, dann Eintragen. Städtewochenende (keine Strecke, kein Ding mit Linie): `kartenpunkte_abfrage` lehnt wie bisher ab (`schreiben.ding_finden.3` bzw. `schreiben.kartenpunkte.keine_linie`), ohne Netzabruf.
- [x] **AC-1 (Zeitbudget):** Given die Konstanten und die nginx-Vorlage / When sie verglichen werden / Then `ZEIT_VORAB + ZEIT_GESAMT + ZEIT_PRUEFUNG` ist kleiner als die Wartezeit des Konnektors (`schreib_anfrage`, 120 s) und kleiner als jedes `proxy_read_timeout`; `OSM_FRIST_VORAB` ist größer als `OSM_ZEIT`; die bisherige Grenze `ZEIT_GESAMT + ZEIT_PRUEFUNG < 60` und `ZEIT_SPERRE <= ZEIT_GESAMT` gelten weiter
- [x] **AC-2 (Abruf vor der Sperre, gleiche Abfrage):** Given eine Wanderung mit Strecke und eine Organisator:in, und `FR_OVERPASS` zeigt auf eine unerreichbare Adresse für den Unterprozess / When `kartenpunkte_holen` über `anwenden_extern` läuft und der Vorab-Abruf (ersetzt) eine Antwort liefert / Then trägt der Vorgang die Treffer ein, ohne selbst ins Netz zu gehen (Unterprozess nutzt die Datei aus `FR_OSM_VORAB`), und der Abruf geschah, bevor die Sperre der Reise genommen wurde (die Sperre ist während des Abrufs frei)
- [x] **AC-3 (andere Abfrage):** Given die Linie der Strecke ändert sich zwischen Vorab-Abruf und Vorgang, sodass die Abfrage abweicht / When der Vorgang läuft / Then wird die Vorab-Antwort nicht genutzt und der Vorgang ruft selbst ab (mit der kurzen Frist `OSM_ZEIT`)
- [x] **AC-4 (Rolle zuerst):** Given eine Anfrage mit Rolle Gast oder Mitwirkend / When `kartenpunkte_holen` läuft / Then wird der Netzabruf nicht einmal versucht (Zähler des ersetzten Abrufs bleibt 0), und die Antwort ist die bisherige Ablehnung der Rollenprüfung (422)
- [x] **AC-5 (eine Wiederholung):** Given der ersetzte Netzzugriff antwortet zuerst mit 502, 503, 504 oder 429 und beim zweiten Mal mit Treffern / When `overpass_holen` läuft / Then genau eine Wiederholung nach `OSM_PAUSE` und Treffer; Given er antwortet beide Male mit 502 / Then genau zwei Zugriffe und `Ablehnung("schreiben.kartenpunkte.dienst")`; Given er antwortet mit 429 oder 504 beide Male / Then die Ablehnung `schreiben.kartenpunkte.limit`; Given eine Zeitüberschreitung / Then keine Wiederholung
- [x] **AC-6 (Fehlschlag ohne Sperre):** Given der Vorab-Abruf scheitert endgültig / When `anwenden_extern` läuft / Then Antwort 422 mit der Ablehnung (Text "nichts wurde geändert" bzw. Limit-Text), die Sperrdatei der Reise wurde nicht genommen, der Unterprozess nicht gestartet, und der Stand der Reise ist unverändert
- [x] **AC-7 (nur eigene Datei):** Given eine Anfrage, die selbst ein Feld mit Namen `FR_OSM_VORAB`, `osm_vorab` oder eine eingebettete Antwort enthält / When der Vorgang läuft / Then wird kein solches Feld je als Antwort genommen (der Abruf ersetzt die Antwort, nur sie erscheint im Ergebnis); Given `FR_OSM_VORAB` zeigt auf eine fehlende, leere oder fremde Datei / Then eigener Abruf wie in AC-3, kein Absturz
- [x] **AC-8 (Aufräumen):** Given ein Vorgang endet mit Erfolg, Ablehnung, Fristablauf (504) oder Ausnahme / When er vorbei ist / Then existiert der Ordner `frieda-osm-*` des Vorab-Abrufs nicht mehr
- [x] **AC-9 (Sperre nicht länger):** Given der Vorab-Abruf dauert (ersetzt, verzögert) mehrere Sekunden / When parallel ein anderer Schreibvorgang derselben Reise läuft / Then bekommt dieser die Sperre ohne 429; die Sperre des `kartenpunkte_holen`-Vorgangs wird erst nach dem Abruf genommen und nicht länger gehalten als vor dieser Änderung
- [x] **AC-10 (beide Wege):** Given eine Reise im Speicher (`FR_SPEICHERREISEN`) und eine Git-Reise / When `kartenpunkte_holen` läuft / Then bekommt der Unterprozess in beiden Wegen `FR_OSM_VORAB` (Umgebung des Unterprozesses geprüft), und die Lesekopie des Vorab-Abrufs liest den Stand der Reise ohne ihn zu verändern (Speicher: Stand-Nummer und Dateien vorher = nachher; Git: Arbeitskopie unberührt)
- [x] **AC-11 (alter Code):** Given ein Unterprozess, der `FR_OSM_VORAB` nicht kennt (alter Code der Arbeitskopie) / When er läuft / Then ruft er wie bisher selbst ab und das Ergebnis ist richtig; die Umgebungsvariable verändert sonst kein Verhalten
- [x] **AC-12 (Städtewochenende):** Given die Beispielreise `stadtwochenende` (keine Strecke, keine Linie) / When `kartenpunkte_holen` mit beliebiger Strecke läuft / Then dieselbe Ablehnung wie bisher (422) und kein Netzabruf (Zähler 0)
- [x] **AC-13 (Overpass-Adresse):** Given `FR_OVERPASS` ist gesetzt / When `overpass_holen` ruft ab / Then geht die Anfrage an diese Adresse mit der Kennung `instanz.kennung()` als User-Agent und `[timeout:N]` in der Abfrage, wobei N der ganzen Frist entspricht; ohne den Wert gilt die bisherige Adresse
- [x] **AC-14 (bestehendes Verhalten):** Given die bisherige Erfindung der Antwort per `monkeypatch` auf `overpass_abfragen` / When der Test `test_kartenpunkte_holen_mit_erfundener_antwort` läuft / Then bleibt er grün, unverändert in Treffern, Aktualisieren statt Verdoppeln und Ablehnungen
- [x] **AC-15 (Texte):** Given alle Sprachdateien / When die Textprüfung läuft / Then stehen alle neuen sichtbaren Texte (falls es welche gibt) in `engine/texte_*.py` in allen Sprachen, im Code keiner

## Dialog

### Runde 1
**Adversary:** Erste Prüfung (gezielt 29 passed, voll 1886 passed). Befunde: F001 MEDIUM (AC-8): Der Vorbereitungs-Faden lief nach ZEIT_VORAB_VORB weiter, der Dienst löschte den Ordner, der Faden legte ihn neu an; Probe ließ `frieda-osm-*` liegen. F002 LOW: Überschreitung der Vorbereitung ohne Protokollzeile. F003 LOW: `urlopen`-Frist bindet nicht die Gesamtdauer. Der Test-Helfer `deutsch(a)` (text_teile nach Deutsch) schwächt die Tests nicht.
**Implementierer:** F001 und F002 behoben: Der Faden setzt "fertig" unter `threading.Lock` im `finally`; nach `join` setzt der Dienst unter demselben Lock den Abbruchmerker, wenn nicht fertig; der Faden löscht dann `vorab` selbst. Protokollzeile "preparation exceeded N s, skipped". F003 bleibt bewusst offen (akzeptiertes LOW: Budget 83 von 120 s, 37 s Reserve; eine Gesamtfrist bräuchte stückweises Lesen oder einen eigenen Faden).
Code reference: engine/schreiben.py:5066
Code reference: engine/schreiben_git.py:204

### Runde 2
**Adversary:** Nachprüfung der Behebung. (a) Race fertig/Abbruch: Kann der Ordner liegen bleiben? Kann er zu früh gelöscht werden, während der Faden schreibt oder der Dienst ihn nutzt? (b) Fängt der neue Test die Lücke? (c) Gelten AC-1 bis AC-15 weiter?
**Implementierer:** (a) Beide Zustandswechsel laufen unter demselben Lock. Fall 1: Faden zuerst fertig, "fertig" gesetzt, er schreibt danach nichts mehr; der Dienst sieht "fertig", nutzt den Ordner und `anwenden_extern` löscht ihn im `finally`. Fall 2: Dienst zuerst, "abgebrochen" gesetzt; der Dienst gibt None zurück und nutzt den Ordner nie; sein `finally` löscht ihn, der Faden löscht ihn am Ende nochmals (`ignore_errors`), so bleibt auch Nachgeschriebenes nicht liegen. Kein Fenster, in dem der Faden nach "fertig" noch schreibt und kein Aufräumen folgt, und keines, in dem der Dienst einen Ordner nutzt, den der Faden löscht. Der `finally`-Block läuft auch bei Ausnahmen im Faden. Ein ewig hängender Faden hielte seinen Rest, bis er endet: nicht behebbar ohne Abbruch von Fäden, akzeptiert. Probe der Erstprüfung (Kopie 2,5 s, Grenze 1 s) jetzt: Protokollzeile da, `leftover: set()`. (b) `test_kartenpunkte_vorab_ordner_auch_nach_zu_langer_vorbereitung_weg` hält den Faden an, bis der Vorgang vorbei ist (Ordner gelöscht), lässt ihn dann kopieren und prüft das Verschwinden von `frieda-osm-*` sowie die Protokollzeile; das ist exakt die Lücke aus F001/F002, grün. (c) Gezielt 30 passed, test_schreiben, test_texte und Pfadprüfung 248 passed; voller Lauf des Entwicklers 1887 passed; Rollenprüfung, Reihenfolge Abruf vor Sperre, Umgebungsübergabe in beiden Wegen und die übrigen ACs unverändert belegt. Neue Code-Stellen:
Code reference: engine/schreiben.py:5073
Code reference: engine/schreiben_git.py:204

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Begründung: Alle ACs und Erwartungspunkte belegt; F001 und F002 behoben und nachgeprüft (Race unter einem Lock, Probe und neuer Test grün).

Findings:
- F001 MEDIUM, behoben (engine/schreiben.py:5066).
- F002 LOW, behoben (engine/schreiben.py:5077).
- F003 LOW, akzeptiert (engine/schreiben.py:2045): `urlopen`-Frist bindet nicht die Gesamtdauer; Budget hat 37 s Reserve, eine Gesamtfrist bräuchte stückweises Lesen oder einen eigenen Faden.

## Geprüfte Dateien

- sha256:4e912491f1d68d831537e06dde8c52051451f2da514e09dd307ba5b0e82f7ba4  engine/schreiben.py
- sha256:bb2fd2ae1b3a5ffae9d2b64435a2400b92d3ea9054872cd3d507e59720ab332e  engine/schreiben_git.py

## Prüfbasis

- base: dcb31ad91994da7aa43ec47aef94d3d71a482334
- blob:4380a99e349334b1295ba9c7d9bea5c0ddd39506  engine/schreiben.py
- blob:3d66139c00dbedad594c036621882f71f7b05626  engine/schreiben_git.py
