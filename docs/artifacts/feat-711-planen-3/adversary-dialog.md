# Adversary Dialog — feat-711-planen-3
Spec: docs/specs/oberflaeche/funktionsseiten-711-planen-3.md
Datum: 2026-11-26 19:19

## Checkliste
- [x] AC-1: `/info/funktionen/gespraeche/` und `/info/funktionen/lebenslauf/` liefern in DE und EN 200 mit allen Abschnitten aus dem Katalog und ihren Bildern (`test_unterseite[gespraeche]`, `test_unterseite[lebenslauf]`, `test_unterseiten_planen`).
- [x] AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- [x] AC-3: Texte und Bilder vollständig je Sprache in den Maßen von `erzeugen` (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`, `test_englisch_schnittstelle`).
- [x] AC-4: Beispiele stimmen mit den Beispielreisen überein (Tag 3 Hohnstein–Brand–Altendorf 10,7 km, ca. 4 h, 400 m Aufstieg, Gasthaus an der Brandaussicht; Stadtwochenende im Status „Idee“ ohne Varianten und Karte; Malerweg im Status „Planung“); jede Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.

## Dialog

### Runde 1
**Adversary:** Testlauf (Testdatei `test-run-output.txt`, Pfade bereinigt): 10 Testdateien (Funktionsseiten, Infoseite, Texte, Englisch, Sprachen, Protokolle ohne Pfade), 183 bestanden, 3 fehlgeschlagen. Die 3 Fehler (`test_seite_sprachen.py`, nur Variante `webkit`) sind ein fehlender Playwright-Browser (`browserType.launch: Executable doesn't exist ... webkit`), kein Befund am Code; die Chromium-Läufe derselben Tests bestehen. `qa_gate.py --run` verweigert (kein `qa_gate.test_command` konfiguriert), darum direkt gelaufen. Ausnahmelisten: `engine/tests/test_texte.py` ist im Diff unverändert, also nicht länger.
Prüfung AC-4 gegen Beispielreisen: Tag 3 = E-02 „Hohnstein – Brand – Altendorf“, 10,7 km, ca. 4:00 h, 400 m Aufstieg; A-13 „Gasthaus an der Brandaussicht“ mit „Öffnungszeiten nicht geprüft“; Malerweg `status.wert: planung`; Stadtwochenende `status.wert: idee`, Bausteine ohne Varianten und Karte; Pension Burgblick und Wanderherberge Altendorf haben keine Buchung (nur B-01, B-02 gebucht, B-03 storniert). Alles stimmt. Bilder angesehen: `stadt-de/-en` zeigen „Idee“/„Idea“ und „noch 123 Tage“/„123 days to go“; `zutun-de/-en` zeigen „Planung“/„Planning“, Reiter „Zu tun“/„To do“, Überschrift „Zu entscheiden“/„To decide“. Alle vier Bildunterschriften passen zu beiden Sprachen. Englische Statusnamen (Idea, Planning, Fixed, Travelling, After, Archived) entsprechen `seite.reise_status.*`.
Inhaltstreue gegen `docs/funktionen/lebenszyklus.md`: Baustein-Aufzählung im Text nennt „Erinnerungen“ als schaltbaren Baustein; die Quelle nennt Wächter und Profile, und `BAUSTEINE` in `engine/reise.py` kennt keinen Baustein „erinnerungen“. Das ist eine falsche Behauptung über die Software (F001).
Beispielsatz der Entscheidung: Begründung „weil sie direkt am Weg liegt“ steht in keiner Quelle; die Beispielreise (`CLAUDE.md`, `offene-fragen.md`) begründet anders (Burgblick am Markt, Gasthof Polenztal wegen des morgendlichen Wiederanstiegs) (F002).
**Implementierer:** keine Antwort (Kontext isoliert).

### Runde 2
**Adversary:** Zweiter Durchgang gezielt gegen die Behauptungen: Statuswechsel-Erinnerung (7 Tage vor erstem Tag, erster Tag, nach letztem Tag) deckt sich mit der Quelle; „Wechseln tut immer eine Organisator:in“ deckt sich; Schonfrist „in der Regel 14 Tage“ deckt sich (Vorgabe); „Auch eine archivierte Reise lässt sich im Gespräch wieder öffnen“ deckt sich mit der Quelle; „zwei Minuten höchstens“ bei Veröffentlichung deckt sich. Rollen-Tabellen decken sich. Englischer Satz zu den Erinnerungen am Statuswechsel ist grammatisch holprig („reminds them seven days before the first day of “Fixed”“) (F003). Die Bildunterschrift „Etikett unter dem Titel“ ist für das Bild ausreichend genau (Etikett steht unter Titel und Untertitel), nur die Quelle sagt „unter dem Untertitel“; kein Befund. `INFO_UNTERSEITEN`-Einträge: Bilder `stadt`, `zutun` existieren als Dateien und in `BILDER`; `siehe`-Verweise zeigen auf vorhandene Bereiche; `test_unterseite[gespraeche|lebenslauf]` und `test_unterseiten_planen` bestehen. Frühe Einigkeit wird nicht angenommen: die beiden inhaltlichen Befunde sind echte Abweichungen von der Quelle.
**Implementierer:** keine Antwort (Kontext isoliert).

### Runde 3
**Implementierer:** F001 und F003 behoben; F002 bestritten (V-03.a hat `plus: ["direkt am Weg"]` und Verlaufsgrund „liegt am Weg, kein Anstieg am Morgen“).
**Adversary:** F001 geprüft: `engine/texte_de.py:4101` nennt jetzt „Wächter (Erinnerungen an Fristen) und Profile“, EN `engine/texte_en.py:4099` „watcher (deadline reminders) and profiles“; Begriffe stimmen mit `wert.waechter`/`wert.profile` und `BAUSTEINE`. F003 geprüft: `engine/texte_en.py:4097` lautet jetzt „reminds them to switch to “Fixed” …“. F002 widerlegt: `beispiel/reisen/beispielreise/plan/routen.yaml:572` und :574 belegen die Begründung „direkt am Weg“ (auch Zeile 110); meine Quelle war `CLAUDE.md`/`offene-fragen.md` der Beispielreise, nicht die Planungsdaten. Die Begründung ist datentreu, F002 geschlossen. Die 3 Webkit-Fehler bleiben Umgebung (Browser nicht installiert).

## Findings und Bestätigungen

Finding:
  ID: F001 (in Runde 3 behoben)
  Severity: MEDIUM
  Category: spec_violation
  Code reference: engine/texte_de.py:4101
  Description: `info.bereich.lebenslauf.wie.4.text` zählt „Erinnerungen“ unter den Bausteinen auf, die eine Reise ein- und ausschaltet (EN gleich in engine/texte_en.py:4099).
  Spec requirement: AC-4 — keine falschen Behauptungen über die Software; Quelle `docs/funktionen/lebenszyklus.md` nennt Wächter und Profile.
  Conflict: `BAUSTEINE` in `engine/reise.py` enthält „waechter“ und „profile“, aber keinen Baustein „erinnerungen“; auch `tun.5` ist unkritisch, doch hier wird ein nicht vorhandener Schalter versprochen.
  Remediation: DE: „... Varianten, Karte, Rückmeldungen, Fragen, Aufgaben, Wünsche, Packliste, Wächter und Profile.“ EN: „... variants, map, feedback, questions, tasks, wishes, packing list, watcher and profiles.“ (Begriffe wie in den vorhandenen Texten zu Wächter und Profilen prüfen und übernehmen.)

Finding:
  ID: F002 (in Runde 3 widerlegt, geschlossen)
  Severity: LOW
  Category: spec_violation
  Code reference: engine/texte_de.py:4062
  Description: Beispielsatz „Wir nehmen die Pension Burgblick, weil sie direkt am Weg liegt.“ (EN: engine/texte_en.py:4060).
  Spec requirement: AC-4 — Beispiele stimmen mit der Beispielreise überein.
  Conflict: Die Beispielreise gibt als Grund etwas anderes an (Gasthof Polenztal verworfen, weil der Weg am Morgen erst wieder hinaufführt; Burgblick liegt am Markt); „direkt am Weg“ ist erfunden.
  Remediation: DE: „Wir nehmen die Pension Burgblick, weil wir lieber in einer kleinen Pension schlafen. Den Gasthof Polenztal verwerfen.“ (Wortlaut der Quelle) EN: „We’ll take Pension Burgblick because we’d rather sleep in a small guesthouse. Reject Gasthof Polenztal.“

Finding:
  ID: F003 (in Runde 3 behoben)
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/texte_en.py:4097
  Description: „Frieda reminds them seven days before the first day of “Fixed”, on the first day of “Travelling” and after the last day of “After”.“ ist als Satz missverständlich.
  Spec requirement: AC-3 — Texte vollständig und einheitlich in beiden Sprachen.
  Conflict: Lesbarkeit; die deutsche Fassung (engine/texte_de.py:4099) ist verständlich.
  Remediation: EN: „Frieda reminds them to switch to “Fixed” seven days before the first day, to “Travelling” on the first day and to “After” after the last day.“

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1358
  Evidence: `INFO_UNTERSEITEN` hat `gespraeche` (Zeile 1356) und `lebenslauf` mit Bildern, Gespräch und `siehe`; `test_unterseite[gespraeche]`, `test_unterseite[lebenslauf]`, `test_unterseiten_planen` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1336
  Evidence: `INFO_GRUPPEN` führt beide Bereiche in der Gruppe „planen“; `test_uebersicht_alle_funktionen` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/info/erzeugen.py:48
  Evidence: Bild `stadt` in `BILDER` (Stadtwochenende, ohne Anker), Dateien `stadt-de.webp` und `stadt-en.webp` in 585 x 1050 vorhanden; `test_texte_und_bilder_jeder_unterseite`, `test_texte`, `test_englisch_schnittstelle` bestanden; `test_texte.py` unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:4044
  Evidence: alle Schlüssel `info.bereich.gespraeche.*` und `lebenslauf.*` (lead, wo, wer, bild, tun 1-7/1-6, wie, gespraech, rolle, gut) in DE vorhanden und gleich in EN (engine/texte_en.py:4042).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/texte_en.py:4045
  Evidence: Beispieldaten (10,7 km, 4 Stunden, 400 m, Gasthaus an der Brandaussicht, Idee/Planung, Stadtwochenende ohne Varianten und Karte) und die vier Bildunterschriften stimmen mit Beispielreisen und Bildern in DE und EN überein; F001 und F003 behoben, F002 widerlegt.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Es gibt keine Produktionsschreibstelle; die Änderung besteht aus Katalogtexten, zwei Tabelleneinträgen und einem Bild-Eintrag. Keine verdächtige Zeile, daher keine Spalten „Bedingung davor“ / „Test für diesen Weg“ zu füllen.

## Verdict
═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
F001 und F003 behoben und nachgeprüft, F002 widerlegt (Beispieldaten belegen die Begründung).
Tests: 183 bestanden (Runde 1), nach dem Fix 129 bestanden laut Implementierer; 3 Webkit-Fehler nur Umgebung (Browser nicht installiert), 0 übersprungen
Regressions: keine gefunden
Checklist: 4/4 Punkte bewiesen

## Geprüfte Dateien

- sha256:c0bb2ade1e1a5356effe7d8183932077e0e8463b3e8bdfc0192fb65dedbf2f06  engine/anmeldung.py
- sha256:30c2f4cb2fd238c5f219e3e810545c5ae1579c945842622424b3779e07bc6f6c  engine/info/erzeugen.py
- sha256:5ba6bb9ed6c8fc400f97f6c2077fa18da0c61125ddb48729b50c2ad2638df8f5  engine/texte_de.py
- sha256:5cb5484f05909c097c1da262911008c54fd3d9bac718d76a70ade8e66b4d20e1  engine/texte_en.py

## Prüfbasis

- base: 3e187650f944183e7f7c2dbf496f8e2b029dbb17
- blob:e3f316bda60022ddd313e2c0cfdf7d7fbe4831b5  engine/anmeldung.py
- blob:a20afea48f8fd79f23fc99035ad4bcde18b54fa6  engine/info/erzeugen.py
- blob:cdb86cfa0c351b10c7c951eb96bc135b5722c4a1  engine/texte_de.py
- blob:eddf8b6df951281fd27143e9e155e4625f1c4dc6  engine/texte_en.py
