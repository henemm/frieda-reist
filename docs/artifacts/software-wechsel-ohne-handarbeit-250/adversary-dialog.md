# Adversary Dialog — software-wechsel-ohne-handarbeit-250
Spec: docs/specs/betrieb/software-wechsel-ohne-handarbeit-250.md
Datum: 2026-11-02 18:05

## Checkliste

<!-- Von Hand aus „## Akzeptanzkriterien“ übernommen: der Parser des Plugins erkennt nur „## Acceptance Criteria“. -->
- [x] AC-1: Vorlage software-nachziehen.yml ruft frieda/betrieb/software-nachziehen.sh mit ALT, NEU, NEU_DA, Python in jedem Lauf; „Neuer Stand?“, „Submodul setzen“, Auslöser, Rechte, concurrency unverändert gegenüber 74a2d29; Skript fehlt → rot mit Hinweis
- [x] AC-2: Skript stellt in jedem Lauf jede Reise mit reise.json um, ein Commit mit Submodul und Reisen, auch ohne neuen Stand; ohne Änderung kein Commit; zweiter Lauf ändert nichts
- [x] AC-3: Tor: engine/tests (nur bei neuem Stand) und Bau sperren, tests/ warnt; rot ohne Issue → Issue + Exit 1; rot mit Issue → Warnung, Exit 0, kein Commit, Kommentar nur wenn Stand noch nicht genannt
- [x] AC-4: Push scheitert → Zurücksetzen auf origin/main, neu umstellen, max. 3 Versuche, nie erzwungen; nach 3 Fehlschlägen Exit 1 ohne Issue
- [x] AC-5: veroeffentlichen.sh startet Workflow einmal je neuem Stand, Wiederholung erst nach FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN (6); Merkdatei nur nach gh-Erfolg; Fehler hält Veröffentlichen nicht auf  (F001 behoben, Runde 3)
- [x] AC-6: neu.py nachziehen entfernt CLAUDE.md und kontext/herkunft.md nur als ausgefüllte Kopien des Musters (leeres kontext/ mit), andere Dateien unberührt ohne OFFEN, Kopfkommentar mit wörtlichem \n berichtigt; neue Reise meldet nichts, jede Sprache
- [x] AC-7: Eckdaten zeigen Status in Worten für jeden Wert von reise.STATUS außer idee, jede Sprache
- [x] AC-8: docs/betrieb.md beschreibt Ablauf, Anstoß, Wartezeit; CLAUDE.md enthält die Regel; „von Hand übernommen“ nirgends mehr in Doku/Regeln der Software
- [x] AC-9: vom Orchestrator belegt: ac9-instanz-tests.txt (18 von 18 grün, nichts neu rot)

## Dialog

### Runde 1
**Adversary:** Behauptung: Alle neun Punkte sind umgesetzt. Ich glaube das nicht und suche Brüche. Gezielte Läufe: test_umstellung_250.py, test_software_nachziehen.py, test_neu.py (72 bestanden) und test_betrieb.py mit Filter anstoss/nachziehen/beispiel (6 bestanden); Ausgabe in docs/artifacts/software-wechsel-ohne-handarbeit-250/adversary-test-output.txt. Der volle Lauf (16 min) ist in test-green-output.txt grün und wurde nicht wiederholt. Grüne Tests beweisen nichts über Werte, die kein Test setzt. Angriffe: (1) Wartezeit mit führender Null, (2) Muster-Abgleich mit CRLF, Leerzeilen, leer, Zusatzzeile, Platzhalter, Regex-Zeichen im Text, (3) Kopfkommentar außerhalb des führenden #-Blocks, (4) set -e-Fallen im Skript, (5) Skriptmodus der neuen Datei.
**Implementierer:** Belege aus dem Code.
- AC-1: Code reference: betrieb/software-nachziehen.yml:73 — der Schritt „Umstellen, prüfen, übernehmen“ setzt ALT/NEU/NEU_DA und bricht mit Fehlermeldung und exit 1 ab, wenn das Skript nicht ausführbar ist oder fehlt. Die Schritte „Neuer Stand?“ und „Submodul setzen“, schedule `7,37 * * * *`, workflow_dispatch, permissions und concurrency (cancel-in-progress false) stehen laut Vergleich mit 74a2d29 unverändert; geändert sind nur Kopfkommentar, das `if:` an setup-python und Pakete (jetzt in jedem Lauf) und der Rest. Das Skript hat Modus 755 auf der Platte (ls -l). Voraussetzung: beim Commit muss 100755 in den Index (Modus nach dem Add prüfen), sonst meldet der Workflow dauerhaft „fehlt“; die Prüfung auf Ausführbarkeit ist hier die Falle.
- AC-2: Code reference: betrieb/software-nachziehen.sh:51 (umstellen läuft in jedem Versuch), :52-57 (Add von reisen und frieda, leerer Index → „Nichts zu übernehmen“, return 0, kein Commit), :66 ein Commit mit Submodul und Reisen. Idempotenz des zweiten Laufs: Probe in Runde 2 (Kopfkommentar, zweiter Lauf leer) und Test „zweiter Lauf ändert nichts“ (grün). set -e: umstellen/tor laufen als Bedingung bzw. mit Abfangen; die Funktion main wird ganz eingelesen, bevor das Submodul wechselt.
- AC-3: Code reference: betrieb/software-nachziehen.sh:98-120 (tor: engine/tests nur bei NEU_DA=ja, Bau jeder Reise, tests/ nur Warnung), :138-159 (issue_regel: ohne offenes Issue gh issue create und return 1; mit offenem Issue Warnung, return 0, Kommentar nur wenn grep -qF auf den kurzen SHA über Titel und Kommentare nichts findet). Testläufe grün. Schwäche, niedrig: schlägt die Liste der Issues selbst fehl (:140), gilt „kein Issue“ und es entsteht ggf. ein zweites Issue (F002).
- AC-4: Code reference: betrieb/software-nachziehen.sh:38-49 (Schleife 1..3, ab Versuch 2 fetch, harter Reset auf origin/main, Submodul erneut setzen, neu umstellen und prüfen), :67 Push nach main ohne Erzwingen (die Option für Erzwingen kommt im Skript nicht vor), :72-73 nach drei Fehlschlägen Exit 1 ohne Issue. Die Tests für Wettlauf und drei gescheiterte Pushes sind grün.
- AC-5: Code reference: betrieb/veroeffentlichen.sh:238-270 (software_anstossen), :344 Aufruf mit Abfangen nach dem fetch. Merkdatei erst nach gh-Erfolg (:265-268), ls-remote/gh-Fehler sind Warnungen mit return 0. Aber: siehe Runde 2, F001.
- AC-6: Code reference: engine/neu.py:521 (ist_vorlagen_kopie: CRLF→LF, Leerzeilen am Ende weg, gleiche Zeilenzahl, re.escape je Musterteil, Platzhalter → beliebiger Text, leer passt nie), :534 (reste_nachziehen: löscht nur bei Treffer, kontext/ nur wenn leer), :506 (Aufruf auch ohne reise.json), :562 (Kopfkommentar nur im führenden #-Block). Texte: engine/texte_de.py:2764-2765 und engine/texte_en.py:2764-2765 (rest ohne OFFEN, kopfkommentar). Der Aufruf nachziehen() hat keine frühe Rückkehr vor :506.
- AC-7: Code reference: engine/reise.py:217 (Text je Statuswert), Schlüssel für planung, fest, unterwegs, danach, archiv in engine/texte_de.py:782-786 und engine/texte_en.py:782-786 = alle Werte von reise.STATUS (reise.py:26) außer idee. Test test_umstellung_250.py:106 prüft das je Sprache.
Code reference: engine/texte_de.py:782 (Status-Wörter :782-786; Meldungen der Umstellung :2764-2765)
Code reference: engine/texte_en.py:782 (Status-Wörter :782-786; Meldungen der Umstellung :2764-2765)
  <!-- Nachgetragen vom Orchestrator nach Rebase auf origin/main (#249): eigene Zitatzeilen, damit `stamp` die schon oben geprüften Textdateien erfasst. Inhalt unverändert. -->
- AC-8: Code reference: docs/betrieb.md:232 (Anstoß, Wartezeit, Merkdatei), :193 (Vorgabe), Ablauf-Abschnitt davor; CLAUDE.md:37 (Regel). Die Suche nach „von Hand übernommen“ trifft nur Spec und Kontextdatei (laut Spec-Abschnitt Implementation Details erlaubt); Test test_software_nachziehen.py:167 prüft die Doku.
- AC-9: vom Orchestrator nachzuweisen.

### Runde 2
**Adversary:** Runde 1 hat nur bestätigt, was die Tests prüfen. Tiefere Angriffe mit eigenen Proben (Scratchpad, keine Repo-Änderung):
1. Muster-Abgleich (Probe p1.py, ist_vorlagen_kopie gegen das deutsche Muster): ausgefüllte Kopie True; mit CRLF True; mit drei Leerzeilen am Ende True; leere Datei und nur Zeilenumbrüche False; zusätzliche Zeile False; Zeile „## Eckdaten “ mit Leerzeichen False; geänderter Satz „Noch nichts festgehalten.“ → „Ida mag keine Berge.“ False; „Noch keine.“ → „Fähre.“ False; Status-Zeile mit Zusatz False; Titel mit Regex-Zeichen (Backslash-d, eckige und runde Klammern) True, also Platzhalter und re.escape korrekt. Kein Muster hat eine reine Platzhalterzeile, die beliebigen Inhalt schluckt.
2. Dateisystem (Probe p2.py, reste_nachziehen): Kopfkommentar mit wörtlichem Backslash-n zwischen drei Kommentarzeilen → echte Umbrüche, zweiter Lauf leer (idempotent). Eine Zeile `titel: y # n` mit wörtlichem Backslash-n und folgendem Kommentar (kein führender #-Block) bleibt unberührt. Ein wörtliches Backslash-n am Zeilenende vor einer Leerzeile bleibt, weil der Regex ein folgendes `#` verlangt (LOW, F003). Eine CRLF-Datei wird beim Berichtigen komplett in LF geschrieben (read_text im Textmodus, LOW, F004). Der Versuch, die Fälle „kontext/ mit weiterer Datei“, „versteckte Datei“ und Probelauf als Skript zu fahren, wurde vom Werkzeug-Sandkasten abgelehnt; dafür gelten die grünen Tests in test_umstellung_250.py (Probelauf schreibt nichts, eigene Dateien bleiben) und die Lektüre von neu.py:553-557 (ordner != reise_dir und Ordner leer: versteckte Dateien halten den Ordner, richtig).
3. Wartezeit (Probe mit bash): Die Prüfung auf Ziffern lässt „08“ und „09“ durch. Die anschließende Multiplikation mit 3600 in der Arithmetik ist dann eine Oktalzahl-Auswertung und bricht mit „value too great for base (error token is 08)“ ab. Nachgewiesen mit einem Einzeiler: Funktion f setzt x=08 und wertet einen Vergleich mit x mal 3600 aus, Funktion g ruft f mit Abfangen auf; keine der drei Folgeausgaben (in f, in g, oben) erscheint, Exit 1. Ein Arithmetikfehler in bash verwirft den ganzen laufenden Befehl bis zur obersten Ebene; das Abfangen mit `|| true` hilft nicht. In veroeffentlichen.sh ist das der ganze Aufruf main. Die Stelle wird nur erreicht, wenn die Merkdatei denselben Stand mit gültiger Zeit nennt (Kurzschluss davor), also ab dem zweiten Lauf nach einem erfolgreichen Anstoß. Folge: ein Eintrag FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN=08 in der Einstellungsdatei der Instanz stoppt das gesamte Veröffentlichen, solange main der Software vor dem Submodul liegt. Das verletzt AC-5 („ein Fehler dabei hält das Veröffentlichen nicht auf“) und den Prüfauftrag „ungültige Werte“.
4. Weitere Prüfungen ohne Befund: Rückgabe 1 aus issue_regel als letztes Statement unter set -e beendet den Lauf wie gewünscht rot; der Reset nach rotem Tor lässt die Änderungen im Baum (Runner ist flüchtig); Stunden „0“ startet bei jedem Lauf (gültig); „-1“ oder leer → 6; ls-remote-Fehler → Warnung ohne Merkdatei; m_zeit ungültig → Neustart erlaubt; wechselnder Stand startet sofort. LOW: das Lesen der Merkdatei schreibt bei fehlender Datei eine Fehlermeldung ins Protokoll, weil die Eingabeumleitung vor der Umleitung von stderr ausgewertet wird (F005).
**Implementierer:** Gegenbeleg / Stellung:
- F001 ist real und liegt in Code reference: betrieb/veroeffentlichen.sh:256-257. Behebung: Wert dezimal erzwingen (Präfix 10# vor der Zahl in der Arithmetik) oder die Prüfung verschärfen. Dazu ein Test mit FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN=08 und gemerktem gleichem Stand.
- Code reference: betrieb/gemeinsam.sh:87 setzt den Vorgabewert 6; ein leerer Wert fällt auf 6 zurück, ein „08“ nicht. Der Fehler steckt nur in der Prüfung der Zahl, nicht in der Vorgabe.
- Submodul-Fall (Hinweis, F005): Liegt das Submodul vor main der Software (Branchstand), unterscheiden sich fern und eingebunden dauerhaft; das Veröffentlichen startet den Workflow dann alle 6 Stunden, der Workflow endet laut „Neuer Stand?“ (Vorwärts-Prüfung) mit neu_da=nein. Harmlos, spec-konform („ein anderer Stand“).

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Findings

Finding:
  ID: F001
  Severity: HIGH
  Category: edge_case
  Code reference: betrieb/veroeffentlichen.sh:257
  Description: Die Wartezeit wird auf reine Ziffern geprüft und dann mal 3600 in der Shell-Arithmetik gerechnet. Werte mit führender Null und einer Ziffer 8 oder 9 (08, 09) liest bash als ungültige Oktalzahl; der Arithmetikfehler bricht den ganzen Aufruf von main ab, der Aufruf mit Abfangen fängt das nicht.
  Spec requirement: AC-5 — ein Fehler dabei hält das Veröffentlichen nicht auf
  Conflict: Mit FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN=08 und gemerktem gleichem Stand stoppt jeder Lauf von veroeffentlichen.sh vor dem Bauen und Deployen.
  Remediation: Nach der Prüfung den Wert mit Präfix 10# dezimal erzwingen (auch für m_zeit); Test dazu.

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: betrieb/software-nachziehen.sh:140
  Description: Schlägt gh issue list fehl (API-Fehler), wird liste leer und das Skript behandelt es als „kein offenes Issue“ und legt ein weiteres Issue an.
  Spec requirement: AC-3 — Rot mit offenem Issue: Warnung, Exit 0
  Conflict: Bei vorübergehendem API-Fehler können doppelte Issues entstehen; der Lauf endet ohnehin rot.
  Remediation: Fehler der Issue-Liste getrennt behandeln (Warnung, Exit 1 ohne Issue).

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:562
  Description: Der Regex berichtigt nur ein wörtliches Backslash-n, dem direkt ein Rautezeichen folgt; ein wörtliches Backslash-n am Zeilenende oder vor einem Leerzeichen bleibt.
  Spec requirement: AC-6 — Kopfkommentar mit wörtlichem \n bekommt echte Zeilenumbrüche
  Conflict: Nur relevant, wenn der Rest von #218 anders aussieht als die Form Kommentar, Backslash-n, Kommentar; die Form ist nicht belegt.
  Remediation: Form von #218 in der Spec belegen oder Backslash-n im führenden #-Block insgesamt ersetzen.

Finding:
  ID: F004
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:556
  Description: read_text im Textmodus wandelt CRLF in LF; beim Berichtigen des Kopfkommentars wird die ganze reise.yaml mit LF geschrieben.
  Spec requirement: AC-6 — berichtigt den Kopfkommentar
  Conflict: Nebenwirkung auf die übrigen Zeilen, nur bei CRLF-Dateien.
  Remediation: newline="" beim Lesen und Schreiben.

Finding:
  ID: F005
  Severity: LOW
  Category: anti_pattern
  Code reference: betrieb/veroeffentlichen.sh:253
  Description: Beim Lesen der Merkdatei erscheint bei fehlender Datei die Fehlermeldung trotz Umleitung im Protokoll (Reihenfolge der Umleitungen). Außerdem startet der Server alle 6 Stunden den Workflow, wenn das Submodul vor main der Software liegt.
  Spec requirement: AC-5
  Conflict: Rauschen im Protokoll, kein Funktionsfehler.
  Remediation: Vorher die Lesbarkeit der Datei prüfen.

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: betrieb/software-nachziehen.yml:73
  Evidence: Aufruf des Skripts mit ALT/NEU/NEU_DA, Hinweis und exit 1 wenn es fehlt oder nicht ausführbar ist; unveränderte Schritte laut Vergleich mit 74a2d29; Python und Pakete ohne if.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: betrieb/software-nachziehen.sh:76
  Evidence: umstellen läuft in jedem Versuch für jede reise.json; leerer Index → kein Commit; ein Commit mit Submodul und Reisen.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: betrieb/software-nachziehen.sh:138
  Evidence: issue_regel: ohne Issue anlegen und Exit 1; mit Issue Warnung und Exit 0; Kommentar nur ohne kurzen SHA in Titel und Kommentaren.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: betrieb/software-nachziehen.sh:38
  Evidence: drei Versuche, Reset auf origin/main, neu umstellen, ohne Erzwingen, Exit 1 ohne Issue.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/neu.py:521
  Evidence: Proben p1/p2 (siehe Runde 2); Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/reise.py:217
  Evidence: Status-Wörter in beiden Sprachen für alle Werte von STATUS außer idee.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: betrieb/gemeinsam.sh:87
  Evidence: Vorgabe 6 in gemeinsam.sh, beschrieben in docs/betrieb.md:193 und :232, Regel in CLAUDE.md:37.
  Status: CONFIRMED


Confirmation:
  AC: AC-5
  Code reference: betrieb/veroeffentlichen.sh:257
  Evidence: Die Arithmetik rechnet jetzt mit Präfix 10# für t, m_zeit und stunden; 08 und 09 sind dezimal. Merkdatei wird nur gelesen, wenn sie existiert (:253), leere Datei ergibt leere Felder und damit Neustart. Nicht-numerische Wartezeit fällt auf 6, nicht-numerische gemerkte Zeit erlaubt Neustart. gh-Fehler bleibt Warnung ohne Merkdatei.
  Status: CONFIRMED

### Runde 3
**Adversary:** Fixes für F001, F002, F005 angegriffen. Tests: test_betrieb.py und test_software_nachziehen.py komplett 114 bestanden; voller Lauf laut test-green-output.txt 992 bestanden. Randfälle gelesen: leere Merkdatei (read liefert 1, mit Abfangen, `[ -f ] && {...}` ist unter set -e nicht tödlich, weil nicht letztes Glied der Liste), kaputte Merkdatei (Zeit nicht numerisch → Neustart erlaubt), Wartezeit „abc“ oder „-1“ → 6, „08“ → 8. Kein neuer Bruch. Nur theoretisch: 20-stellige Zahlen laufen in der Shell-Arithmetik über, praktisch irrelevant.
**Implementierer:** Code reference: betrieb/software-nachziehen.sh:140-145: scheitert gh issue list oder jq, endet der Lauf mit Fehlermeldung und Exit 1, ohne Issue und ohne Commit; die Funktion gibt dort mit return 1 zurück, set -e greift nicht vorzeitig, weil die Abfragen Teil einer if-Bedingung sind. Der Zweig „kein Issue“ und „Issue offen“ ist unverändert. F003 und F004: akzeptiert, kein Defekt (echte Reisen haben die Form Backslash-n gefolgt von #, keine CRLF-Dateien; der Orchestrator hat das geprüft). Ich stimme zu: beides bleibt LOW und ist dokumentiert. AC-9: Beleg ac9-instanz-tests.txt vom Orchestrator, 18 von 18 grün mit eingebundenem Stand, mit Basis 74a2d29 und mit Branch plus #250, nichts neu rot.

## Verdict

VERDICT: VERIFIED

F001 (HIGH), F002 und F005 (LOW) behoben und geprüft; F003 und F004 (LOW) als akzeptiert vermerkt. Tests: 992 bestanden, 0 fehlgeschlagen, 0 übersprungen (voller Lauf), gezielt 114 bestanden. Regressionen: keine gefunden. Checkliste: AC-1 bis AC-8 geprüft, AC-9 durch den Orchestrator belegt.

## Geprüfte Dateien

- sha256:610a581a7d262784f54cb33e960e0db8fe55a9ef9b8c3ba9ef7f5c2cd17c7be2  betrieb/gemeinsam.sh
- sha256:f4241e755febbdb453d01ebe88d4b365e98f91cdfbddb9d9517bfe770c22bee3  betrieb/software-nachziehen.sh
- sha256:b64228687c325b382b1d93ed65cd96ed33420a0f88f70b4d88fb20f3939401c5  betrieb/software-nachziehen.yml
- sha256:91fc9d8adc2b080c1193675f8e6c685860ce17024b7c08332f33523e5943cec2  betrieb/veroeffentlichen.sh
- sha256:eca778428323a422e74abd1c715ae2fe6d6f08dbc3e677f6a23cae10e048043e  engine/neu.py
- sha256:89bcbbfaa14874583d62f8d1de2e8921d7d9baaa016ad3bf71422fb5d820b407  engine/reise.py

## Prüfbasis

- base: 74a2d29f35c2834d8dc6ba7a7dd6e6597c6e9d2e
- blob:35b37ba76348786d0db1835bb06db09dbc7189b0  betrieb/gemeinsam.sh
- blob:addfed6517b3f5cf76359fae9721668e87e76fb1  betrieb/software-nachziehen.sh
- blob:246b7b159d7c73cd2bfb4ae8401bec89b35df84e  betrieb/software-nachziehen.yml
- blob:b8982d07b3fd7e2ecbe46cdef62ad5464c6d98d1  betrieb/veroeffentlichen.sh
- blob:865f7aa8e9079695abf6dad6db98d9a76caa11ac  engine/neu.py
- blob:452d4064659833a2864334df0de11494fdc80017  engine/reise.py

## Geprüfte Dateien

- sha256:610a581a7d262784f54cb33e960e0db8fe55a9ef9b8c3ba9ef7f5c2cd17c7be2  betrieb/gemeinsam.sh
- sha256:f4241e755febbdb453d01ebe88d4b365e98f91cdfbddb9d9517bfe770c22bee3  betrieb/software-nachziehen.sh
- sha256:b64228687c325b382b1d93ed65cd96ed33420a0f88f70b4d88fb20f3939401c5  betrieb/software-nachziehen.yml
- sha256:91fc9d8adc2b080c1193675f8e6c685860ce17024b7c08332f33523e5943cec2  betrieb/veroeffentlichen.sh
- sha256:eca778428323a422e74abd1c715ae2fe6d6f08dbc3e677f6a23cae10e048043e  engine/neu.py
- sha256:89bcbbfaa14874583d62f8d1de2e8921d7d9baaa016ad3bf71422fb5d820b407  engine/reise.py

## Prüfbasis

- base: 71bb27794a9d4c621637de872131940203399a60
- blob:35b37ba76348786d0db1835bb06db09dbc7189b0  betrieb/gemeinsam.sh
- blob:addfed6517b3f5cf76359fae9721668e87e76fb1  betrieb/software-nachziehen.sh
- blob:246b7b159d7c73cd2bfb4ae8401bec89b35df84e  betrieb/software-nachziehen.yml
- blob:b8982d07b3fd7e2ecbe46cdef62ad5464c6d98d1  betrieb/veroeffentlichen.sh
- blob:865f7aa8e9079695abf6dad6db98d9a76caa11ac  engine/neu.py
- blob:452d4064659833a2864334df0de11494fdc80017  engine/reise.py

## Geprüfte Dateien

- sha256:610a581a7d262784f54cb33e960e0db8fe55a9ef9b8c3ba9ef7f5c2cd17c7be2  betrieb/gemeinsam.sh
- sha256:f4241e755febbdb453d01ebe88d4b365e98f91cdfbddb9d9517bfe770c22bee3  betrieb/software-nachziehen.sh
- sha256:b64228687c325b382b1d93ed65cd96ed33420a0f88f70b4d88fb20f3939401c5  betrieb/software-nachziehen.yml
- sha256:91fc9d8adc2b080c1193675f8e6c685860ce17024b7c08332f33523e5943cec2  betrieb/veroeffentlichen.sh
- sha256:eca778428323a422e74abd1c715ae2fe6d6f08dbc3e677f6a23cae10e048043e  engine/neu.py
- sha256:89bcbbfaa14874583d62f8d1de2e8921d7d9baaa016ad3bf71422fb5d820b407  engine/reise.py
- sha256:50a8d31a80f033667f576eed018a58de38ec43f46adc35a720d3f6a6ad1b6068  engine/texte_de.py
- sha256:2d14edebcf5eaa0de48d34ba75f8fd378e0bcbeaf69ae8367e489743775ea842  engine/texte_en.py

## Prüfbasis

- base: 71bb27794a9d4c621637de872131940203399a60
- blob:35b37ba76348786d0db1835bb06db09dbc7189b0  betrieb/gemeinsam.sh
- blob:addfed6517b3f5cf76359fae9721668e87e76fb1  betrieb/software-nachziehen.sh
- blob:246b7b159d7c73cd2bfb4ae8401bec89b35df84e  betrieb/software-nachziehen.yml
- blob:b8982d07b3fd7e2ecbe46cdef62ad5464c6d98d1  betrieb/veroeffentlichen.sh
- blob:865f7aa8e9079695abf6dad6db98d9a76caa11ac  engine/neu.py
- blob:452d4064659833a2864334df0de11494fdc80017  engine/reise.py
- blob:83e58f243a04be5cb05608d3d8c617961761d496  engine/texte_de.py
- blob:71a39557db9a9080a198c09241ebee60f9049376  engine/texte_en.py
