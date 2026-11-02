# Adversary Dialog — fix-214-eine-seitenordnung
Spec: docs/specs/oberflaeche/eine-seitenordnung-214.md
Datum: 2026-11-02 13:47

## Checkliste

- [x] K1: Startseite ohne Pläne = Zeitachse, eine Spalte, je Tag eine Zeile mit genau einem Link. Beleg: test_eine_seitenordnung.py::test_ohne_plaene_zeitachse_eine_spalte_ein_link grün (adversary-test-output.txt, 193 passed); ansichtStart ruft immer ansichtReise(m, PLAN_ANSICHT).
- [x] K2: Buchung/Unterkunft/Aufenthalt/Wahlvergleich genau einmal vollständig, vier Fälle. Beleg: test_genau_einmal_vollstaendig[4 Fälle] grün; eigener Gegenlauf mit einer Nacht (U-01 nur T-01) in (a) und (b): voll B-01/U-01/A-01 je 1. test_seite.py::test_buchung_genau_einmal_vollstaendig und test_stornierte_buchung_eingeklappt_am_ding grün.
- [x] K3: Keine doppelte ID in allen vier Fällen. Beleg: test_keine_doppelte_id[4] und test_nachtzeile_und_wahlzeile_teilen_keine_id grün; Gegenlauf mit an: U-01, E-01, T-02 an V-02: doppelt = {}.
- [x] K4: "Zu tun" mit Zu entscheiden/Zu buchen ohne Pläne. Beleg: test_zu_tun_auch_ohne_plaene grün; ZU_TUN = !!R (vorlage.html:1093).
- [x] K5: Wahlen mit an: am Element. Beleg: test_wahl_mit_an_steht_am_element[3], test_ohne_plaene_keine_marke_und_kein_vergleich grün.
- [x] K6: Frische Reise sieht aus wie die Beispielreise. Beleg: test_seite.py::test_neue_reise_aus_der_vorlage_im_browser und test_neue_reise_aus_der_vorlage (chromium, webkit) grün; Ausnahme "ohne Tage beginnt mit Wissen" ist in design.md dokumentiert.
- [x] K7: Gesamtlauf grün. Beleg: docs/artifacts/fix-214-eine-seitenordnung/test-green-output.txt (941 passed, vom Auftraggeber geliefert, nicht wiederholt); eigener gezielter Lauf 193 passed + 11 passed, 0 übersprungen; test_texte.py unverändert, Ausnahmelisten nicht länger.
- [x] K8: ADR-0003 (Nachtrag, Verlaufseintrag) und design.md nachgetragen. Beleg: docs/adr/0003-heimat.md Z. 43-49, 72; docs/design.md Z. 109, 128. Prüfstelle: in der Spec beantwortet (PR-Text liegt außerhalb meiner Sicht).
- [x] K9: Fünf Entscheidungen eingetragen. Beleg: ADR-0003 Nachtrag (tagesseiten, tiefe, plan_reiter, Etappen), design.md Z. 128.
- [x] K10: Tagesnummer ohne Pläne aus R.tage. Beleg: test_tagesseite.py::test_tagesnummer_ohne_plaene_aus_tage grün; Nachtrag in tagesseite-plan.md.
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

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Tests: 193 passed + 11 passed (gezielt, adversary-test-output.txt), 0 failed, 0 übersprungen; voller Lauf des Auftraggebers 941 passed (nicht wiederholt).

Befunde (alle nicht blockierend):

- id: F001
  severity: LOW
  category: anti_pattern
  description: Die Zählprüfung der Sprungziele wurde gelockert (nur noch VOLL statt alle Sprungziele). Sachlich richtig, weil O-03 und Extras keine volle Textangabe haben und die alte Behauptung dort nie erfüllbar war. Die Lockerung ist in der Spec nicht festgehalten.
  evidence: Code reference: engine/tests/test_eine_seitenordnung.py:197
  remediation: Eine Zeile im Changelog der Spec; kein Codefix nötig.

- id: F002
  severity: LOW
  category: spec_violation
  description: Entscheidung 1 nennt einen Reiter "Pläne"; umgesetzt ist die Route #plaene mit einer Karte im Reiseüberblick, der erste Reiter heißt bei offenen Plänen "Varianten". Die Information bleibt erreichbar.
  evidence: Code reference: engine/vorlage.html:1081 (HAT_VARIANTEN) und engine/vorlage.html:4664 (Route #plaene)
  remediation: Spec-Wortlaut an die Umsetzung angleichen (Changelog); keine Codeänderung.

- id: F003
  severity: LOW
  category: edge_case
  description: heimat() behandelt "an:" auf einen Aufenthalt, das Modell lehnt das aber schon beim Bau ab. Toter Zweig.
  evidence: Code reference: engine/vorlage.html:4583 (Modellprüfung: Choice V-02: an "A-01" is neither a day, leg, ...)
  remediation: Optional entfernen oder als Schutz belassen, falls das Modell später Aufenthalte erlaubt.

- id: F004
  severity: LOW
  category: anti_pattern
  description: Satz in design.md zum Namen des ersten Reiters ist verstümmelt.
  evidence: Code reference: engine/vorlage.html:1074 (Code eindeutig); Doku: docs/design.md:128
  remediation: Satz umformulieren: Der erste Reiter heißt "Reise"; solange mehrere Pläne offen sind, "Varianten".

Bestätigungen (Code reference je geänderte Datei):

- Confirmation: AC K1/K2/K3/K5, Code reference: engine/vorlage.html:1069 (PLAN_ANSICHT), Evidence: immer gesetzt (fest, aktuell, sonst R.tage), heimat() (Z. 4553) ist die einzige Heimatbestimmung, Status CONFIRMED.
- Confirmation: Entscheidung 2, Code reference: engine/reise.py:504, Evidence: ALTE_BAUSTEINE (Z. 40) wird gelesen und ignoriert, Status CONFIRMED.
- Confirmation: Entscheidung 2 / Konnektor, Code reference: engine/schreiben.py:1963, Evidence: tagesseiten wird in einstellung_setzen still herausgenommen, Test in test_schreiben.py, Status CONFIRMED.
- Confirmation: Konnektor-Beschreibung, Code reference: engine/texte_de.py:1167, Evidence: einstellung_setzen nennt tagesseiten nicht mehr, Status CONFIRMED.
- Confirmation: Konnektor-Beschreibung (Sprachen), Code reference: engine/texte_en.py:1167, Evidence: gleiche Änderung in Englisch, entfernte Schlüssel in beiden Dateien identisch, test_texte.py grün, Status CONFIRMED.
- Confirmation: K2/K3, Code reference: engine/tests/test_eine_seitenordnung.py:184, Evidence: Zählprüfung in vier Fällen, Wahlvergleich weiter auf "genau einmal" gezählt, Status CONFIRMED.
- Confirmation: K3, Code reference: engine/tests/seiten_eine_seitenordnung.mjs:42, Evidence: Selektor h2.tagkopf .tagdatum nur auf der Tagesseite, Status CONFIRMED.
- Confirmation: K6, Code reference: engine/tests/test_seite.py:140, Evidence: Rundgang über frische Reise grün, Status CONFIRMED.
- Confirmation: K10, Code reference: engine/tests/test_tagesseite.py:161, Evidence: Tagesnummer aus R.tage, Status CONFIRMED.
- Confirmation: Zurück-Link, Code reference: engine/vorlage.html:3282, Evidence: Zurück führt immer zu "#varianten" (Reise), Status CONFIRMED.

Code-Referenzen (je eine Zeile, für den Stempel):

Code reference: engine/vorlage.html:1069
Code reference: engine/vorlage.html:4553
Code reference: engine/vorlage.html:3282
Code reference: engine/reise.py:504
Code reference: engine/schreiben.py:1963
Code reference: engine/texte_de.py:1167
Code reference: engine/texte_en.py:1167
Code reference: engine/tests/test_eine_seitenordnung.py:184
Code reference: engine/tests/seiten_eine_seitenordnung.mjs:42
Code reference: engine/tests/test_seite.py:140
Code reference: engine/tests/test_schreiben.py:1006
Code reference: engine/tests/test_tagesseite.py:161

## Geprüfte Dateien

- sha256:a6a3499ab21053048511844047e2ac5973479c0575bf07fdaf5b6a59dd86440c  engine/reise.py
- sha256:450a3229effb4cd38e1d0731424d4cec5c755e48058ad61a36ccd5dd9b5e0305  engine/schreiben.py
- sha256:0e7be8f400ef22a13dfd2076f021f59d61b91d6a986a38e03bfd842cb90e301d  engine/tests/seiten_eine_seitenordnung.mjs
- sha256:d91c7b4d97ad328c08a457a44326187bd11be211ebcf7b72425e1b82d5826f4f  engine/tests/test_eine_seitenordnung.py
- sha256:bbca654a02fd3c27b4463ec8f639b7b4014bd86e425d7726839ba1746ef75d36  engine/tests/test_schreiben.py
- sha256:cfeb18adeb9760c57da2480a964f3ba67930cf34ec473a7015146fef32585551  engine/tests/test_seite.py
- sha256:2b962c7ac9f6cd2f4c949a99212e1efc5ba317d61b0b17c6752b4f88c135cb9f  engine/tests/test_tagesseite.py
- sha256:ded29c8eed8ac313b656f50c61b1ecee6bbd63de396fc015879341f5b7e59e0f  engine/texte_de.py
- sha256:dc2a3fdc22af3d1b7a6e9d5a2491ceee5f9cd2707928e10c4389b8af145b9ac2  engine/texte_en.py
- sha256:2e5a060bb2d758e63cd0d6bfd0078dc6f22c202bd67b55ff0ef1388df9a69399  engine/vorlage.html

## Prüfbasis

- base: c1e039ec64e0a94f1640070a9d5a632b5d908744
- blob:4eb09bc4ec2a0893353f1d87f9c4fefbea54c46b  engine/reise.py
- blob:c80bc596ece1e1757c9710296f66e30268ebec38  engine/schreiben.py
- blob:2760862db72ef0d614812144f21c74ebc91cf57f  engine/tests/seiten_eine_seitenordnung.mjs
- blob:b7f6baf3f5a200bff0f2bc14dd3e07b479bb6b16  engine/tests/test_eine_seitenordnung.py
- blob:211f57b741e4df1f5fcd4250812cc3d6f7810350  engine/tests/test_schreiben.py
- blob:65ce10f536ea2bfa841fd281f412f42b57d90bd9  engine/tests/test_seite.py
- blob:ce778951c8b263cd9b27177d6c62f308ab94476b  engine/tests/test_tagesseite.py
- blob:5cc3d298f16f950212463b88d4373a909298d716  engine/texte_de.py
- blob:3075bf83393f6afbbff2fb6b6600b956a8c32d0a  engine/texte_en.py
- blob:9176f5a4f7a15c6eac68c3899a755795e117e1bb  engine/vorlage.html
