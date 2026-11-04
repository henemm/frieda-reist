# Adversary Dialog — kennzahlen-268
Spec: docs/specs/routen/kennzahlen-268.md
Datum: 2026-11-04 20:30

## Checkliste
- [x] **AC-1 (Beispielwanderung unverändert):** Given `beispiel/reisen/beispielreise`, when sie baut, then zeigt die Reise die Summe 595 min, 25,4 km, ↑1075, ↓1025 (`fehlend` leer, `mit_kennzahlen` wahr), die Pläne P-A 610 min und P-B 595 min; je Plan ist die Summe der `kennzahlen.min` aller Tage in `p.tage` gleich `p.summe.min`, und für die Reise gilt dasselbe für `R.tage` und `R.summe`.
- [x] **AC-2 (Stadtwochenende):** Given `beispiel/reisen/stadtwochenende` (keine summierte Strecke), when sie baut, then ist `summe.mit_kennzahlen` falsch, jeder Tag hat `kennzahlen` mit Nullwerten ohne `fehlend`, und die gebaute Seite zeigt weder Gehzeit noch km noch Höhenmeter noch „Angaben fehlen“ (Browser- oder Seitentest).
- [x] **AC-3 (Zeiten und Schlüssel):** Given eine Wanderstrecke mit Kennzahlen „2 h“ (statt `h:mm`) und der englische Schlüssel „Length“ (statt „Länge“), when der Bau läuft, then zählen beide in `tag.kennzahlen` (2 h = 120 min; „Length“ = km) und die Seite zeigt sie in der Tageszeile.
- [x] **AC-4 (kombinierte Art):** Given eine Strecke mit `art: [wandern, bahn]` (nur eine Art summiert), when der Bau läuft, then gilt dieselbe Regel in `summe`, in `tag.kennzahlen` und in `strecke.summiert`; Seite (Linienstil, Gehzeit/Dauer, Etappenkarte, `streckeZeile`, Wegverlauf) liest nur `strecke.summiert`; ein Test mit beiden Seiten (Summe und Anzeige) widerspricht sich nicht.
- [x] **AC-5 (Angaben fehlen statt Null):** Given eine summierte Strecke ohne Kennzahlen, when der Bau läuft, then ist `mit_kennzahlen` wahr, `fehlend` nennt die Felder, und Seite (Steckbrief/Reiseüberblick) und Konnektor (`Handbuch.summe`) zeigen „Angaben fehlen“ (Katalogtext) statt nichts oder `0:00`.
- [x] **AC-6 (nur eine Stelle):** Given der Quelltext von `engine/vorlage.html`, then enthält er weder `tagKm` noch `tagMin` und keine Bedingung `s.min || s.km || s.auf`; `steckbrief`, `summeText`, `reiseKennzahlen` und `Handbuch.summe` lesen `mit_kennzahlen`; `summiertArt`, `streckeZeile` und Wegverlauf enthalten kein `artDef(…).summiert`. Die Kartenlegende bleibt auf Art-Ebene.
- [x] **AC-7 (keine festen Texte):** Given `routen.py` und `vorlage.html`, then enthalten sie kein festes `↑ … m, ↓ … m` und kein `↑ ${v} m`; die Texte kommen aus dem Katalog; die neuen Schlüssel stehen in allen Sprachen, `engine/tests/test_texte.py` ist grün und die Ausnahmelisten sind nicht länger geworden.
- [x] **AC-8 (Sprache der Hülle):** Given Beispielreise in Pseudo-Sprache/Englisch, when die Seite die Tageszeile und Höhenmeter zeigt, then stehen die Texte in der Sprache der Hülle, Zahlen über `dauer`/`kmText` formatiert (bestehende Tests `test_seite_sprachen.py` bleiben grün).
- [x] **AC-9 (Plan-Tage):** Given eine Reise mit zwei Plänen, deren Tage verschiedene Wahlen tragen, when der Bau läuft, then trägt jeder `p.tage[i].kennzahlen` die Werte seiner eigenen Wahl; ein Wechsel der Wahl in der Seite ändert keine Tagessumme außerhalb des Plans.
- [x] **AC-10 (Konnektor):** Given eine Summe mit `mit_kennzahlen` falsch, when `Handbuch.summe` formatiert, then steht keine Gehzeit-Zeile; given `mit_kennzahlen` wahr und vollständig, then steht dieselbe Zeile wie heute (gleiche Werte wie `konnektor.summe.gehzeit`).
- [x] **AC-11 (Gesamtlauf):** `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen (CI auf dem vorgespulten Commit).
- [x] **AC-12 (nachgelagert, nicht Teil von Phase 6; Orchestrator vor dem Vorspulen) (Instanz-Tests, Nachweis im PR-Text):** Weil `daten.json` neue Felder bekommt, laufen vor dem Vorspulen die Tests der einbindenden Instanzen mit dem Branch und sind grün; der Probebau aller echten Reisen mit dem Branch ist grün (lesend).

## Dialog

### Runde 1
**Adversary:** Ich unterstelle, dass die Umsetzung bricht. Angriffe: (a) Rechenstellen: bleibt irgendwo ein zweiter Weg (tagKm/tagMin, `s.min || s.km || s.auf`, `artDef(..).summiert` ausser der Kartenlegende)? (b) feste Texte `↑ ${` und `m, ↓` in routen.py/vorlage.html; (c) Ausnahmelisten in test_texte.py; (d) Reisespezifik oder Art-Namen in der Engine; (e) Aufrufer von `summiertArt` mit Ersatzobjekten, die jetzt anders entscheiden; (f) kombinierte Art in Summe, Tageswert, Strecke, Seite; (g) Plan-Tage mit eigener Wahl; (h) Stadtwochenende; (i) „2 h“, „Length“; (j) fehlende Einzelfelder; (k) englische Hülle.
**Implementierer (Belege, vom Adversary selbst erhoben):**
- (a) Suche nach tagKm/tagMin in vorlage.html: keine Treffer. Verbleibende `summiert`-Stellen: `summiertArt` (vorlage.html:1274), streckeZeile (:1414), wegVerlauf (:1480); nur die Kartenlegende (:2823) filtert auf Art-Ebene, wie die Spec es erlaubt. Alle Aufrufer von `summiertArt` (1275, 1417, 2415, 2440, 3030, 3511, 4036) übergeben Objekte aus `R.strecken` (gebaut von `strecke_aus`, routen.py:1608, trägt `summiert`) oder Ersatzobjekte ohne Feld, das ergibt „nicht summiert“ wie heute.
- (b) Suche nach dem festen Muster für Höhenmeter in routen.py und vorlage.html: keine Treffer. Texte stehen in texte_de.py:377-379 und texte_en.py:376-378 sowie im Konnektor-Katalog (`konnektor.summe.angaben_fehlen`, `konnektor.summe.fehlt`).
- (c) Diff von test_texte.py gegen die Basis: nur Tests ergänzt, keine Ausnahmeliste verändert, also nicht länger.
- (d) Diff gelesen: weder Art-Namen noch Reisespezifik; `ist_summiert` liest nur das Merkmal `summiert` der Art (routen.py:1732).
- (f) `summe`, `strecken_summe` und `strecke_aus` rufen alle `ist_summiert`: eine Regel, kein zweiter Code. Die Seite liest nur `st.summiert`.
- (g) Tag-Dict trägt `kennzahlen` aus `strecken_summe` der eigenen Wahl (routen.py:1535); Pläne bauen in eigenem Lauf. Test `test_plan_tage_tragen_eigene_kennzahlen` grün.
- (i) `kennwerte` mit Length 8 km und Dauer 2 h ergibt min 120, km 8.0 (eigener Aufruf).
- Gezielte Tests (eigener Lauf, adversary-test-output.txt): 306 passed in 18,69 s.

Code reference: engine/routen.py:1737
Code reference: engine/vorlage.html:1274

**Adversary-Zwischenstand:** Keine Rechenstelle gefunden, die noch abweicht. Frühe Einigkeit ist verdächtig; Runde 2 greift die Ränder an.

### Runde 2
**Adversary:** Ränder: (1) Konnektor mit nur einem fehlenden Feld; (2) alle Felder fehlend; (3) `mit_kennzahlen` falsch; (4) Seite bei teilweise fehlenden Angaben; (5) Schlüsselname weicht von der Spec ab; (6) Tageszeile ohne Hinweis auf fehlende Angaben; (7) englische Hülle; (8) Regression durch die Regel für kombinierte Art.
**Implementierer (Belege):**
- (1) konnektor.py:671-679: bekannte Werte bleiben, ein Feld ohne jeden Wert wird „–“ (nie „0:00“), Zusatz `seite.summe.unvollstaendig`; Test `test_handbuch_summe_teilweise_angaben` grün. Fehlt nur `ab`, während `auf` Werte hat, bleiben die Teilwerte stehen, durch den Zusatz „unvollständig“ gekennzeichnet; kein Defekt.
- (2) alle vier fehlend und alle Summen 0: `konnektor.summe.angaben_fehlen` (texte_de.py:1988, texte_en.py:1987), Test `test_handbuch_summe_angaben_fehlen`.
- (3) `mit_kennzahlen` falsch: keine Gehzeit-Zeile (konnektor.py:673 nicht betreten), AC-10-Test grün. Stadtwochenende: Seitentests grün (Gesamtlauf 1358 passed).
- (4) vorlage.html:1330-1336 (`summeText`), :2255 (`steckbrief`), :2926 (`reiseKennzahlen`) entscheiden über `mit_kennzahlen`; fehlende Felder zeigen `seite.steckbrief.angaben_fehlen`; im `summeText` entfallen fehlende Felder, es bleibt der Zusatz „unvollständig“.
- (5) `seite.auto.hoehenmeter` statt `routen.auto.hoehenmeter`: Bereich `routen.` ist nach `test_schluessel_form` nicht erlaubt; die Spec lässt den Namen offen. Stimmig, liegt neben `seite.auto.laenge` und `seite.auto.dezimaltrenner`, die `auto_werte` schon nutzt.
- (6) Tageszeile (vorlage.html:2908, 2917) zeigt nur vorhandene Werte; `kennzahlen.fehlend` je Tag wird dort nicht angezeigt. AC-5 fordert „Angaben fehlen“ nur für Steckbrief, Reiseüberblick, Konnektor.
- (7) Neue Tests in test_seite_sprachen.py und `kennzahlPaar` über `T("seite.kennzahl.hoehe_auf")` (vorlage.html:1342): Texte in Sprache der Hülle; grün.
- (8) Verhaltensänderung bei kombinierter Art: die Seite zählte sie vorher als summiert, jetzt folgt sie der Art `kombiniert` wie die Summe. Von der Spec gewollt (AC-4); auf echten Reisen sichtbar, deshalb AC-12 (nachgelagert).

Code reference: engine/konnektor.py:671
Code reference: engine/texte_de.py:1988
Code reference: engine/texte_en.py:1987
Code reference: engine/vorlage.html:2926
Code reference: engine/routen.py:1535

**Adversary-Schluss:** Zwei kleine Beobachtungen (F001, F002), kein Verstoss gegen die Spec. Jeder Punkt ist mit Test oder Code belegt.

## Structured Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/vorlage.html:2917
  Description: Die Tageszeile zeigt nur vorhandene Werte; `tag.kennzahlen.fehlend` wird nicht ausgewertet, ein Tag mit summierter Strecke ohne Angaben bleibt dort stumm.
  Spec requirement: AC-5 nennt nur Steckbrief, Reiseüberblick und Konnektor
  Conflict: kein Widerspruch; nur eine Lücke gegenüber dem Gedanken „keine stille Null“.
  Remediation: optional später (#269) ein Hinweis in der Tageszeile.

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/vorlage.html:1330
  Description: `summeText` lässt fehlende Felder weg und hängt nur „unvollständig“ an; „Angaben fehlen“ steht dort nicht.
  Spec requirement: AC-5 (Steckbrief/Reiseüberblick)
  Conflict: kein Widerspruch, `summeText` ist nicht genannt und verhielt sich vorher gleich.
  Remediation: optional.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/routen.py:1707
  Evidence: `summe` addiert `strecken_summe` je Tag; Tests in test_routen/test_bauen (595 min, 25,4 km, 610/595 je Plan) grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/routen.py:1737
  Evidence: ohne summierte Strecke bleibt `gezaehlt` falsch, also `mit_kennzahlen` falsch, Nullwerte ohne fehlend; Seitentest grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/vorlage.html:2908
  Evidence: `kennwerte` (2 h = 120, Length = km) speist `strecken_summe`; die Tageszeile liest `t.kennzahlen`.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/routen.py:1732
  Evidence: `ist_summiert` ist die einzige Regel für Summe, Tageswert und `strecke.summiert`; Seite liest `st.summiert` (vorlage.html:1274).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/konnektor.py:671
  Evidence: „Angaben fehlen“ aus dem Katalog; Seite vorlage.html:2926; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/vorlage.html:2256
  Evidence: kein tagKm/tagMin, keine Bedingung `s.min || s.km || s.auf`; `mit_kennzahlen` in steckbrief, summeText, reiseKennzahlen, Handbuch.summe; test_design grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/texte_de.py:379
  Evidence: Schlüssel in de und en (texte_en.py:378); keine festen Texte; Ausnahmelisten unverändert; test_texte grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/vorlage.html:1342
  Evidence: `T()` mit Hüllensprache; test_seite_sprachen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/routen.py:1535
  Evidence: Tag-Dict mit `kennzahlen` der eigenen Wahl; test_plan_tage_tragen_eigene_kennzahlen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/konnektor.py:673
  Evidence: Gehzeit-Zeile nur bei `mit_kennzahlen`; vollständig dieselbe Zeile wie `konnektor.summe.gehzeit`.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/texte_en.py:376
  Evidence: Gesamtlauf test-green-output.txt 1358 passed; eigener gezielter Lauf adversary-test-output.txt 306 passed, 0 failed, 0 übersprungen.
  Status: CONFIRMED

AC-12: nachgelagert, nicht Teil von Phase 6 (Instanz-Tests und Probebau erledigt der Orchestrator vor dem Vorspulen); hier weder belegt noch BROKEN.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 306 passed (gezielt), 1358 passed (Gesamtlauf des Implementierers), 0 failed, 0 übersprungen
Edge cases: alle geprüft, keine gebrochen (F001, F002 nur LOW, kein Spec-Verstoss)
Regressions: keine gefunden; Verhaltensänderung bei kombinierter Art ist gewollt (AC-4)
Checklist: 11/11 prüfbare Punkte bewiesen; AC-12 nachgelagert

## Geprüfte Dateien

- sha256:3cf5c25368ea0b690404885d9245744005ded4e9c7dc1ede776c764552493ee9  engine/konnektor.py
- sha256:9a875cd986bde9461a82841cfd3a007444a29c4d90b827fa550ed0bdb25a0dcc  engine/routen.py
- sha256:a2fa0b77a621b03bedcbc6a2fbb4569f4181cc2d7f270e00cbd4b76fc79463fa  engine/texte_de.py
- sha256:a61ac5a0d97a100e8d82cfdc93486804b87b25ea83e6d8647096480abd9ac20a  engine/texte_en.py
- sha256:a8d345fe086c3ef0a11f6a4b2dfa680f51cf50ae2dad96e85a3224f2c338f703  engine/vorlage.html

## Prüfbasis

- base: 6492c76882d1bff9bb9223cfb463e4de2df21ecb
- blob:0a096c5b3e3b118db853ab4d5179da90f5815c1d  engine/konnektor.py
- blob:3c3ab1468a4cfc132d3de47b7e1f31043faf47af  engine/routen.py
- blob:f4e77510a24f8f2f9fda916fef891243f6df034c  engine/texte_de.py
- blob:18f825a807544bef4ad19b5207bb5fa16db26086  engine/texte_en.py
- blob:77026139e8e08cbb6db51b3689d1ce12e92b1856  engine/vorlage.html

## Geprüfte Dateien

- sha256:3cf5c25368ea0b690404885d9245744005ded4e9c7dc1ede776c764552493ee9  engine/konnektor.py
- sha256:9a875cd986bde9461a82841cfd3a007444a29c4d90b827fa550ed0bdb25a0dcc  engine/routen.py
- sha256:a2fa0b77a621b03bedcbc6a2fbb4569f4181cc2d7f270e00cbd4b76fc79463fa  engine/texte_de.py
- sha256:a61ac5a0d97a100e8d82cfdc93486804b87b25ea83e6d8647096480abd9ac20a  engine/texte_en.py
- sha256:a8d345fe086c3ef0a11f6a4b2dfa680f51cf50ae2dad96e85a3224f2c338f703  engine/vorlage.html

## Prüfbasis

- base: 6492c76882d1bff9bb9223cfb463e4de2df21ecb
- blob:0a096c5b3e3b118db853ab4d5179da90f5815c1d  engine/konnektor.py
- blob:3c3ab1468a4cfc132d3de47b7e1f31043faf47af  engine/routen.py
- blob:f4e77510a24f8f2f9fda916fef891243f6df034c  engine/texte_de.py
- blob:18f825a807544bef4ad19b5207bb5fa16db26086  engine/texte_en.py
- blob:77026139e8e08cbb6db51b3689d1ce12e92b1856  engine/vorlage.html
