# Adversary Dialog — fix-214-eine-seitenordnung
Spec: docs/specs/oberflaeche/eine-seitenordnung-214.md
Datum: 2026-11-02 13:47

## Checkliste

- [x] K1: Startseite ohne Pläne = Zeitachse, eine Spalte, je Tag eine Zeile mit genau einem Link. Beleg: test_eine_seitenordnung.py::test_ohne_plaene_zeitachse_eine_spalte_ein_link grün (adversary-test-output.txt, 193 passed); ansichtStart ruft immer ansichtReise(m, PLAN_ANSICHT).
- [x] K2: Buchung/Unterkunft/Aufenthalt/Wahlvergleich genau einmal vollständig, vier Fälle. Beleg: test_genau_einmal_vollstaendig[4 Fälle] grün; eigener Gegenlauf mit einer Nacht (U-01 nur T-01) in (a) und (b): voll B-01/U-01/A-01 je 1. test_seite.py::test_buchung_genau_einmal_vollstaendig und test_stornierte_buchung_eingeklappt_am_ding grün.
- [x] K3: Keine doppelte ID in allen vier Fällen. Beleg: test_keine_doppelte_id[4] und test_nachtzeile_und_wahlzeile_teilen_keine_id grün; Gegenlauf mit an: U-01, E-01, T-02 an V-02: doppelt = {}.
- [x] K4: "Zu tun" mit Zu entscheiden/Zu buchen ohne Pläne. Beleg: test_zu_tun_auch_ohne_plaene grün; ZU_TUN = !!R (vorlage.html:1093).
- [x] K5: Wahlen mit an: am Element. Beleg (Runde 3/4): test_wahl_mit_an_steht_am_element[fall x an] mit an in O-03, E-02, U-01, W-05 (12 Läufe) grün; Gegenprobe: wahlAn() abgeschaltet lässt alle 4 Läufe plaene_offen scheitern. Einschränkung: der Zweig an_ids in heimat() wird nicht einzeln erzwungen (F006, LOW).
- [x] K6: Frische Reise sieht aus wie die Beispielreise. Beleg: test_seite.py::test_neue_reise_aus_der_vorlage_im_browser und test_neue_reise_aus_der_vorlage (chromium, webkit) grün; Ausnahme "ohne Tage beginnt mit Wissen" ist in design.md dokumentiert.
- [x] K7: Gesamtlauf grün. Beleg: test-green-output.txt (952 passed, Auftraggeber, nicht wiederholt); eigener Lauf Runde 3/4: 18 passed gezielt, 223 passed in test_tagesplan, test_eine_seitenordnung, test_seite, test_tagesseite, test_schreiben, test_texte, 0 failed, 0 übersprungen (adversary-test-output.txt).
- [x] K8: ADR-0003 (Nachtrag, Verlaufseintrag) und design.md nachgetragen. Beleg: docs/adr/0003-heimat.md Z. 43-49, 72; docs/design.md Z. 109, 128. Prüfstelle: in der Spec beantwortet (PR-Text liegt außerhalb meiner Sicht).
- [x] K9: Fünf Entscheidungen eingetragen. Beleg: ADR-0003 Nachtrag (tagesseiten, tiefe, plan_reiter, Etappen), design.md Z. 128.
- [x] K10: Tagesnummer ohne Pläne aus R.tage: test_tagesseite.py::test_tagesnummer_ohne_plaene_aus_tage grün. Entscheidung 3 (tiefe steuert die Tagesseiten nicht): ansichtTag ohne PLAN_ZULETZT-Vorrang (vorlage.html:3274), test_tagesseite_zaehlt_wie_die_zeitachse_bei_offenen_plaenen[False/True] grün, Gegenprobe mit alter Zeile rot (tiefe=True).
- [x] K11: tiefe/plan_reiter verlieren keine Information. Beleg: test_tagesplan.py::test_tiefe_nur_noch_plan_baum, test_reiseueberblick.py::test_plan_reiter_abschnitte_unter_wissen grün; vorlage.html:4682 (Plan-Baum nur mit TIEFE).
- [x] DoD Suche: PLAN_DA und PLAN_TAGE in engine/ ohne Treffer. TIEFE bleibt absichtlich (Entscheidung 3).
- [x] Unberührt: requirements.txt, CI-Workflow-Ordner, betrieb/, routen.py, konnektor.py, waechter.py, rueckmeldungen.py, neu.py, test_texte.py.

## Dialog

### Runde 1
**Adversary:** Ich gehe davon aus, die Umsetzung sei falsch. Angriffe: (1) Wurde die RED-Zählprüfung aufgeweicht? Die Änderung an test_eine_seitenordnung.py betrifft genau eine Schleife (sprung nur über VOLL). (2) Sind alte Bausteine/Einstellungen still verworfen, ohne Daten zu schreiben? (3) Gibt es mehr als eine Heimatbestimmung? (4) Zurück-Link und Etappen bei offenen Plänen? (5) Hartkodierte Texte, verwaiste Schlüssel, echte Reisen, verbotene Dateien? (6) Wird der Wahlvergleich weiter auf "genau einmal" gezählt?
**Implementierer:** (1) Die Schleife lief über e["sprung"], das auch O-03 und `extra` enthält; deren `voll` ist null (kein Text zum Prüfen, Mess-Skript: `voll: text ? ... : null`), die Behauptung `z["voll"]` war für O-03 also nie erfüllbar. Der Wahlvergleich-Block (V-… über a["vergleiche"], je Wahlstelle len(wo) == 1) steht unverändert davor, test_eine_seitenordnung.py:184-200. Der Selektor `h2.tagkopf .tagdatum` ist enger und gilt nur auf der Tagesseite, kein Verlust. (2) reise.py:40/504 und schreiben.py:1955-1963 filtern tagesseiten; test_schreiben.py prüft, dass es nicht in reise.yaml landet; plan_reiter ist in ALTE_DARSTELLUNG, gelesen und ignoriert. (3) vorlage.html:4553 heimat() ist die einzige Funktion; heimTag, wahlAmElement, route() und zurueckZurZeile fragen sie. (4) ansichtTag-Zurück-Link immer "#varianten" (Z. 3282); ETAPPE_TAG und ETAPPEN_REITER richten sich nach PLAN_ANSICHT (Z. 1084-1087); test_etappen_bei_offenen_plaenen_wie_bei_festem_plan grün. (5) Zeilen mit sichtbarem Text im Änderungsstand sind nur die Bausteinseite (21 gleichartige teil("Organismus", ...)-Zeilen schon im Ausgangsstand); Textschlüssel in de/en gleichzeitig entfernt, test_texte.py grün; nur Ida/Karl/Dresden. (6) Siehe (1).
**Adversary (Bewertung der bekannten Abweichungen):** 1 vertretbare Auslegung (O-03 hat keine volle Form; die Prüfung auf alle drei Dinge und alle Wahlen bleibt), aber nicht in der Spec vermerkt (F001, LOW). 2 vertretbare Auslegung, der Spec-Wortlaut "Reiter Pläne" in Entscheidung 1 weicht ab, die Information bleibt erreichbar (Karte, #plaene, HAT_VARIANTEN) (F002, LOW). 3 kein Bruch: Entscheidung 3 verlangt TIEFE für den Plan-Baum; die Suche-Aussage im Risiko-Abschnitt widerspricht Entscheidung 3, die Definition of Done verlangt sie nur für PLAN_DA/PLAN_TAGE (erfüllt). 4 vertretbar: alle Anpassungen folgen der Spec (#146-Test, "wenig" hat jetzt Zu tun, drei Helferstellen, weil tagKarte keine Heimat einer Buchung mehr ist). 5 vertretbar und von Entscheidung 2 gedeckt.

### Runde 2
**Adversary:** Grenzfälle gegen die Funde. (a) Reise ohne Tage; (b) Unterkunft mit nur einer Nacht, in (a) und (b); (c) stornierte Buchung; (d) Wahl mit an: auf Aufenthalt, Unterkunft, Etappe, Tag; (e) Heimat einer Wahl, wenn ihr Tag nicht im PLAN_ANSICHT liegt.
**Implementierer:** (a) test_neue_reise_aus_der_vorlage (chromium+webkit) grün: ohne Tage startet die Seite mit Wissen, keine Fehler, kein Leerraum. (b) Eigener Lauf mit `_gestreckt(r, 0)`: U-01 hat nur ['T-01']; ohne_plaene und plaene_offen: doppelte IDs {}, voll B-01=1, U-01=1, A-01=1. (c) test_stornierte_buchung_eingeklappt_am_ding und test_stornierte_buchungen_ein_helfer_an_jeder_heimat grün (11 passed). (d) an: A-01 wird vom Modell abgelehnt ("an A-01 is neither a day, leg, accommodation, place, choice nor section"), ist also im Datenmodell unmöglich; der Zweig für Aufenthalte in heimat() (vorlage.html:4583) ist toter, aber harmloser Code (F003, LOW). an: U-01 (plan_fest), an: E-01 (tiefe), an: T-02 (plaene_offen): V-02-Vergleich genau einmal (#T-02), keine doppelte ID. (e) heimat() fällt auf die erste Möglichkeit mit Tag im Plan, sonst {offen:true} nach "Zu tun"; Sprung funktioniert (test_wahl_mit_an_steht_am_element). Keine neuen Brüche gefunden.
**Adversary:** Rest-Befund: design.md Z. 128 enthält einen verkürzten Satz ("Der erste Reiter heißt „Reise“, solange mehrere Pläne offen sind „Varianten“"); der Code (vorlage.html:1074) ist eindeutig: "Varianten" nur bei offenen Plänen, sonst "Reise" (F004, LOW, Doku).

### Runde 3
**Adversary:** Die Nacharbeit entfernt in `ansichtTag` den Vorrang des zuletzt geöffneten Plans. Angriffe: (1) Ist der Fix vollständig? Wo steuern TIEFE oder PLAN_ZULETZT sonst Tagesseiten, Blätterlinks, Zurück-Link oder Ortsseiten? (2) Tag außerhalb der Zeitachse: welche Nummer, Absturz? (3) Würde der neue Test ohne den Fix scheitern, in beiden Zweigen (tiefe aus/an)? (4) Ist der Zurück-Link der Tagesseite noch plan-unabhängig?
**Implementierer:** (1) Alle Treffer von TIEFE und PLAN_ZULETZT in engine/vorlage.html durchgesehen: Z. 3274 (ansichtTag, jetzt nur noch Rückfall), Z. 3331 (ansichtOrt: Zurück-Link und „Kommt vor in“ nutzen PLAN_FEST bzw. PLAN_ZULETZT; Ortsseiten gibt es nur mit TIEFE, Z. 4683, dort ist „zuletzt geöffneter Plan“ gewollt und keine Tagesnummer), Z. 3095 (setzt PLAN_ZULETZT nur in ansichtPlanDetail), Z. 2147/2191/2192/2208/2615 (Anzeige im Plan-Baum und Hinweistext, keine Zählung), Z. 3413 (Ortsliste in Wissen, Spec ausdrücklich „nicht geändert“). Die Blätterlinks der Tagesseite (Z. 3322ff) leiten sich aus `p`, also aus der in Z. 3274 gewählten Zeile ab und ändern sich mit dem Fix mit; der Zurück-Link ist fest „#varianten“ (Z. 3282). Die Zeitachse selbst (PLAN_ANSICHT, Z. 1069) kennt weder TIEFE noch PLAN_ZULETZT. Kein weiterer Zählpfad gefunden. (2) Eigener Lauf in einer Kopie: seiten_tagesplan.mjs um R.weitere_tage erweitert, P-X zuletzt geöffnet. T-04, T-07, T-06 (nur in anderen Plänen oder ohne Plan) liefern fehler == [] in beiden Zweigen, kein Absturz. Nummern: T-04 „Tag 5“, T-07 „Tag 3“ aus P-X, T-06 ohne Kopfzeile und ohne Blätterlinks. (3) Gegenprobe in der Kopie mit wiederhergestellter alter Zeile: der Lauf mit tiefe scheitert (T-03: „Tag 4 · So 16.5.“ statt „Tag 3 · Sa 15.5.“ der Zeitachse), der Lauf ohne tiefe besteht, wie zu erwarten (ohne tiefe galt der Vorrang nie). Mit dem Fix im Worktree: 2 passed. Der Test misst die Zeitachse selbst (`achse`, erst #varianten lesen, dann Plan öffnen, dann Tag) statt eines festen Werts und verlangt mindestens vier Tage (`len(auf_achse) >= 4`). (4) Zurück-Link Z. 3282 unverändert.
**Adversary (Bewertung):** Der Fix ist für alle Tage der Zeitachse vollständig und der Test diskriminiert. Rest: Der Test deckt nur Tage der Zeitachse ab (`auf_achse`), Tage außerhalb prüft er nur auf Absturz. Dort zählt die Seite im zuletzt geöffneten Plan (Spec-gedeckt), aber die Blätternummern passen nicht zur Zeitachse: T-07 (P-X „Tag 3“) verlinkt „Tag 4 →“ auf T-03, das auf der Zeitachse „Tag 3“ trägt (F005, MEDIUM, edge_case; die Spec ist hier still, deshalb Auslegungsfrage, kein Bruch).

### Runde 4
**Adversary:** Zweiter Angriff auf die übrigen Nacharbeiten. (a) Ist `test_wahl_mit_an_steht_am_element` mit den vier Zielen wirklich diskriminierend, auch ohne `an:`? (b) Erzwingt es den Zweig an_ids in heimat()? (c) Prüft test_seite.py die Frage F-01 tatsächlich? (d) Konnektor und Texte: hat die Nacharbeit schreiben.py, texte_de/en oder reise.py berührt?
**Implementierer:** (a) Ohne `an:` scheitert schon die erste Behauptung (`an_ids == [an]`). Gegenprobe wahlAn() liefert nichts: alle vier Läufe plaene_offen rot (O-03, E-02, U-01, W-05). Die zusätzliche Messung `wahlLinksSeite` (seiten_eine_seitenordnung.mjs:102) prüft für E-02 und U-01 die ganze Tagesseite, nicht nur section.am-element, weil dort der Tageskasten die Wahl trägt (vorlage.html:1494). (b) Nein: In einer Kopie mit `for (const x of [])` statt `w.an_ids` in heimat() (vorlage.html:4577) bestehen alle vier Läufe weiter, weil V-02 über die Möglichkeiten (`ot`, Z. 4583ff) denselben Tag T-02 findet. Der Zweig an_ids ist durch kein Testbeispiel gesondert erzwungen (F006, LOW). (c) test_seite.py:122 liest den Fragetext aus offene-fragen.md und verlangt ihn im DOM von „Zu tun“ (390#offen); Lauf test_neue_reise_aus_der_vorlage[chromium, webkit] grün. (d) Der Vergleich mit dem Ausgangsstand zeigt: reise.py, schreiben.py, texte_de.py, texte_en.py, test_schreiben.py, test_tagesseite.py sind seit Runde 2 unverändert (reise.py:40 ALTE_BAUSTEINE, schreiben.py:1962, texte_de.py:1167, test_schreiben.py:1006, test_tagesseite.py:161 weiterhin wie bestätigt); alle sechs Testdateien laufen in Lauf 2 (223 passed).
**Adversary (Bewertung):** Die Nacharbeit ist vollständig und die neuen Tests sind bis auf F006 diskriminierend. F005 und F006 sind keine Brüche der Kriterien K1 bis K11, sondern eine offene Auslegung beziehungsweise eine Testlücke. Keine HIGH- oder CRITICAL-Funde, daher VERIFIED mit LOW/MEDIUM-Anmerkungen.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Tests: 18 passed (gezielt) und 223 passed (test_tagesplan, test_eine_seitenordnung, test_seite, test_tagesseite, test_schreiben, test_texte), 0 failed, 0 übersprungen (adversary-test-output.txt); voller Lauf des Auftraggebers 952 passed (nicht wiederholt). Gegenprobe in Kopie: die alte Zeile in ansichtTag lässt den Test mit tiefe scheitern.

Befunde (nicht blockierend):

- id: F001
  severity: LOW
  category: anti_pattern
  description: Die Zählprüfung der Sprungziele wurde gelockert (nur noch VOLL statt alle Sprungziele). Sachlich richtig; in der Spec seit der Umsetzung vermerkt.
  evidence: Code reference: engine/tests/test_eine_seitenordnung.py:197
  remediation: Keine.

- id: F002
  severity: LOW
  category: spec_violation
  description: Entscheidung 1 nennt einen Reiter "Pläne"; umgesetzt ist die Route #plaene mit einer Karte, in der Spec ebenfalls vermerkt.
  evidence: Code reference: engine/vorlage.html:1081 (HAT_VARIANTEN) und engine/vorlage.html:4664 (Route #plaene)
  remediation: Keine.

- id: F003
  severity: LOW
  category: edge_case
  description: heimat() behandelt "an:" auf einen Aufenthalt, das Modell lehnt das aber schon beim Bau ab. Toter, harmloser Zweig.
  evidence: Code reference: engine/vorlage.html:4583
  remediation: Optional entfernen.

- id: F004
  severity: LOW
  category: anti_pattern
  description: Satz in design.md zum Namen des ersten Reiters ist verstümmelt (Code eindeutig).
  evidence: Code reference: engine/vorlage.html:1074; Doku docs/design.md:128
  remediation: Satz umformulieren.

- id: F005
  severity: MEDIUM
  category: edge_case
  description: Ein Tag, der nur in einem anderen als dem Plan der Zeitachse liegt, zählt im zuletzt geöffneten Plan (Spec-gedeckt). Seine Blätterlinks tragen dann Nummern dieses Plans, führen aber auf Tage der Zeitachse, die dort anders heißen (T-07 "Tag 4 →" auf T-03, das auf der Zeitachse "Tag 3" ist). Der neue Test prüft solche Tage nur auf Absturz (fehler == []), nicht auf die Nummer.
  evidence: Code reference: engine/vorlage.html:3274 und engine/tests/test_tagesplan.py:153
  remediation: In der Spec festhalten, dass Tage außerhalb der Zeitachse im zuletzt geöffneten Plan zählen und Blätterlinks dort planlokal sind, oder die Blätterlinks solcher Tage ohne Nummer beschriften.

- id: F006
  severity: LOW
  category: edge_case
  description: Der Zweig an_ids in heimat() wird von keinem Test erzwungen. Ersetzt man die Schleife durch eine leere Liste, bestehen alle Läufe von test_wahl_mit_an_steht_am_element, weil V-02 über seine Möglichkeiten denselben Tag findet.
  evidence: Code reference: engine/vorlage.html:4577 und engine/tests/test_eine_seitenordnung.py:240
  remediation: Testbeispiel, in dem die Wahlstelle keine Möglichkeit mit Tag im Plan hat (nur an: bindet sie), oder Zweig streichen, falls redundant.

Bestätigungen:

- Confirmation: Entscheidung 3 / K10, Code reference: engine/vorlage.html:3274, Evidence: Tagesseite zählt in PLAN_ANSICHT, wenn dieser den Tag enthält, unabhängig von TIEFE; Rückfall nur für Tage außerhalb, Status CONFIRMED.
- Confirmation: K1/K2/K3/K5, Code reference: engine/vorlage.html:1069 (PLAN_ANSICHT) und engine/vorlage.html:4553 (heimat), Evidence: eine Heimatbestimmung, Status CONFIRMED.
- Confirmation: Zurück-Link, Code reference: engine/vorlage.html:3282, Evidence: immer "#varianten", Status CONFIRMED.
- Confirmation: Entscheidung 3 (Test), Code reference: engine/tests/test_tagesplan.py:120, Evidence: Zeitachse wird zuerst gelesen, dann Plan geöffnet; tiefe False und True; mit alter Zeile rot, Status CONFIRMED.
- Confirmation: Entscheidung 3 (Messskript), Code reference: engine/tests/seiten_tagesplan.mjs:23, Evidence: drittes Argument öffnet erst den Plan und liest achse vor dem Wechsel, Status CONFIRMED.
- Confirmation: K5, Code reference: engine/tests/test_eine_seitenordnung.py:240, Evidence: Parametrisierung O-03, E-02, U-01, W-05; ohne wahlAn rot, Status CONFIRMED.
- Confirmation: K5 (Messung), Code reference: engine/tests/seiten_eine_seitenordnung.mjs:102, Evidence: wahlLinksSeite misst die ganze Zielseite, Status CONFIRMED.
- Confirmation: K6, Code reference: engine/tests/test_seite.py:122, Evidence: Fragetext von F-01 in Zu tun, Status CONFIRMED.
- Confirmation: K11/Entscheidung 2, Code reference: engine/reise.py:40, Evidence: ALTE_BAUSTEINE (tagesseiten) gelesen und ignoriert, Status CONFIRMED.
- Confirmation: Konnektor, Code reference: engine/schreiben.py:1962, Evidence: tagesseiten wird in einstellung_setzen still herausgenommen, Status CONFIRMED.
- Confirmation: Konnektor-Beschreibung, Code reference: engine/texte_de.py:1167, Evidence: nennt tagesseiten nicht mehr, Status CONFIRMED.
- Confirmation: Konnektor-Beschreibung (Sprachen), Code reference: engine/texte_en.py:1167, Evidence: gleiche Änderung in Englisch, Status CONFIRMED.
- Confirmation: Konnektor (Test), Code reference: engine/tests/test_schreiben.py:1006, Evidence: alter Baustein nicht abgelehnt und nicht geschrieben, Status CONFIRMED.
- Confirmation: K10, Code reference: engine/tests/test_tagesseite.py:161, Evidence: Tagesnummer ohne Pläne aus R.tage, Status CONFIRMED.

Code-Referenzen (je eine Zeile, für den Stempel):

Code reference: engine/vorlage.html:3274
Code reference: engine/vorlage.html:1069
Code reference: engine/vorlage.html:4553
Code reference: engine/vorlage.html:3282
Code reference: engine/reise.py:40
Code reference: engine/schreiben.py:1962
Code reference: engine/texte_de.py:1167
Code reference: engine/texte_en.py:1167
Code reference: engine/tests/test_tagesplan.py:120
Code reference: engine/tests/seiten_tagesplan.mjs:23
Code reference: engine/tests/test_eine_seitenordnung.py:240
Code reference: engine/tests/seiten_eine_seitenordnung.mjs:102
Code reference: engine/tests/test_seite.py:122
Code reference: engine/tests/test_schreiben.py:1006
Code reference: engine/tests/test_tagesseite.py:161

## Geprüfte Dateien

- sha256:a6a3499ab21053048511844047e2ac5973479c0575bf07fdaf5b6a59dd86440c  engine/reise.py
- sha256:450a3229effb4cd38e1d0731424d4cec5c755e48058ad61a36ccd5dd9b5e0305  engine/schreiben.py
- sha256:5dcd944712c64da188b5eea65f5294403a2cc2f426780ce5d6a69129a8f869f3  engine/tests/seiten_eine_seitenordnung.mjs
- sha256:5c40f8063a3b6e26f63aa501455e73ff43bbac35d08d3f2811f61500573fb0b3  engine/tests/seiten_tagesplan.mjs
- sha256:cee19974f269e4bf91240808658676f7e0b22cc05b326fc503cc5c72715ddf7c  engine/tests/test_eine_seitenordnung.py
- sha256:bbca654a02fd3c27b4463ec8f639b7b4014bd86e425d7726839ba1746ef75d36  engine/tests/test_schreiben.py
- sha256:e78d691824dd8b1626725a4da9078f0776fb73edd299bd153fa480f991b1203a  engine/tests/test_seite.py
- sha256:1d3ecc8446ee354527d69626e9838e54808956d19085b6a706c9f2a47fe678a6  engine/tests/test_tagesplan.py
- sha256:2b962c7ac9f6cd2f4c949a99212e1efc5ba317d61b0b17c6752b4f88c135cb9f  engine/tests/test_tagesseite.py
- sha256:ded29c8eed8ac313b656f50c61b1ecee6bbd63de396fc015879341f5b7e59e0f  engine/texte_de.py
- sha256:dc2a3fdc22af3d1b7a6e9d5a2491ceee5f9cd2707928e10c4389b8af145b9ac2  engine/texte_en.py
- sha256:d8e21ce677f270ff8342fc116f1184ea198b5c7eacdc90d1e3d203c95f9746e2  engine/vorlage.html

## Prüfbasis

- base: c1e039ec64e0a94f1640070a9d5a632b5d908744
- blob:4eb09bc4ec2a0893353f1d87f9c4fefbea54c46b  engine/reise.py
- blob:c80bc596ece1e1757c9710296f66e30268ebec38  engine/schreiben.py
- blob:3f2cbb511f00b94a6d9a3f84cfd16d13ef691775  engine/tests/seiten_eine_seitenordnung.mjs
- blob:f7a5d20c7c31e38beecbc1751eb9e0bc85694978  engine/tests/seiten_tagesplan.mjs
- blob:f5ad801a40a7950b05a13a9638f123f560fd29cd  engine/tests/test_eine_seitenordnung.py
- blob:211f57b741e4df1f5fcd4250812cc3d6f7810350  engine/tests/test_schreiben.py
- blob:946df262a09ce262969a3a81faf255d2a9946934  engine/tests/test_seite.py
- blob:1d16132fff9b251fa7306ea026310c68c2d5d183  engine/tests/test_tagesplan.py
- blob:ce778951c8b263cd9b27177d6c62f308ab94476b  engine/tests/test_tagesseite.py
- blob:5cc3d298f16f950212463b88d4373a909298d716  engine/texte_de.py
- blob:3075bf83393f6afbbff2fb6b6600b956a8c32d0a  engine/texte_en.py
- blob:5f726de3cdab18703e63604eda7bd5bf3a3f1133  engine/vorlage.html
