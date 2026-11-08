# Adversary Dialog — feature-383-datenschutz-impressum
Spec: docs/specs/betrieb/rechtliches-383.md
Datum: 2026-11-08 00:29

## Checkliste
- [x] **AC-1:** Given die drei Pfade `/datenschutz`, `/impressum`, `/alpha` / When sie ohne Anmeldung per GET geöffnet werden / Then antworten sie 200 in der Sprache der Anfrage (Deutsch und Englisch), und POST auf sie wird abgelehnt.
- [x] **AC-2:** Given gesetzte Betreiberangaben in den Einstellungen / When das Impressum geöffnet wird / Then zeigt es genau Name, Anschrift und Kontakt aus `FR_BETREIBER_NAME`, `FR_BETREIBER_ANSCHRIFT`, `FR_BETREIBER_KONTAKT` (maskiert), und sie stehen weder im Katalog noch in einer anderen Seite.
- [x] **AC-3:** Given eine fehlende oder leere Betreiberangabe / When das Impressum geöffnet wird / Then antwortet es 200 mit dem Hinweis „nicht eingerichtet“ ohne leere Felder, und die Warteliste bleibt nutzbar.
- [x] **AC-4:** Given Warteliste, Anmeldeseiten, Einladungsseite und Mein Konto / When sie angezeigt werden / Then enthalten sie die Link-Zeile zu Datenschutz, Impressum und Alpha-Hinweis.
- [x] **AC-5:** Given eine gebaute Reiseseite in jeder Sprache / When sie geöffnet wird / Then zeigt die Fußzeile immer die Rechtszeile mit den drei Links, Texte aus dem Katalog.
- [x] **AC-6:** Given die Datenschutzerklärung / When Löschen und Export genannt werden / Then ist nur das Konto-Löschen zugesagt, alles andere steht als „folgt“, und der Inhalt entspricht der Tabelle „Datenschutz je Instanz“.
- [x] **AC-7:** Given alle sichtbaren Texte / When `test_texte.py` läuft / Then sind alle Schlüssel in `de` und `en` vorhanden, und die Ausnahmelisten sind nicht länger.
- [x] **AC-8:** Given die nginx-Vorlage / When der Vorlagentest läuft / Then enthält sie die drei Orte mit der Konto-Zone.
- [x] **AC-9:** Given Anmeldung, Warteliste, Konto, Kalender und Reisedaten / When die Seiten eingebaut sind / Then verhalten sie sich unverändert (bestehende Tests grün).

## Dialog

### Runde 1
**Adversary:** Statische Prüfung und Diff-Vergleich. Tests: Gesamtlauf engine/tests mit -n 3: 1781 passed in 888.23s, 0 failed, 0 übersprungen (adversary-testsuite-output.txt). Gezielt test_rechtliches, test_texte, test_nginx, test_design: 159 passed. Die drei geänderten Bestandstests per Diff: (a) test_texte.py test_schluessel_form: nur das Präfix recht in die Regex aufgenommen, die Ausnahmelisten sind unverändert (Vergleich mit origin/main zeigt nur diese Zeile), berechtigt, AC-7 ok. (b) test_bauen.py: Regex ohne hidden am Fuß, zwingend wegen AC-5, berechtigt. (c) test_betrieb.py test_betrieb_ohne_ki (Zeile 2054): von FR_BETREIBER not in beispiel auf Regex ^#?FR_BETREIBER= gelockert; nötig, weil FR_BETREIBER_NAME jetzt im Beispiel steht; Schwäche: Schreibweise mit Leerzeichen nach der Raute würde nicht erkannt (F004, LOW). Code reference: engine/anmeldung.py:594 (BETREIBER), :611-622 (impressum_inhalt, esc und Zeilenumbruch), :659-661 (ist_unsere), :680-684 (Methodenprüfung). Datenschutztext de und en gegen die Tabelle in docs/betrieb.md Zeilen 47-55 gelesen: Konto, Warteliste (7 Tage, konten.py WARTELISTE_TAGE = 7), Verlauf, Reise, Belege, Sicherungen stimmen. Zugesagt wird nur das Konto-Löschen (recht.datenschutz.konto_loeschen); Warteliste-Löschen, Warteliste-Export und Reisedaten-Export stehen als folgt da (recht.datenschutz.folgt). Auslassung: Der Knopf Auf Neueres prüfen im Fuß der Reiseseite fragt eine externe Schnittstelle des Quellcode-Dienstes aus dem Browser an (engine/vorlage.html:5770), nur auf Tipp, im Abschnitt Weitergabe nicht genannt (F003, LOW).
**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Echte HTTP-Anfragen gegen den Konnektor-Dienst mit der Fixture welt (adversary_probe_test.py, Ausgabe adversary-probe-output.txt). GET /impressum 200 auch mit Query-String; /impressum/, /impressum/x, /Impressum, /impressum.html, /alpha/, /impressum;a alle 404 (gehören nicht dem Dienst); HEAD 200 ohne Inhalt; POST mit Origin 405 mit Allow GET, DELETE 405, PUT, PATCH, PROPFIND 405; OPTIONS 204 mit Allow GET, HEAD, POST, OPTIONS (verspricht POST, F005 LOW). XSS: script-Tag und img mit onerror erscheinen nur escaped (lt-Entitäten), Zeilenumbruch der Anschrift wird zu br; noindex vorhanden; Englisch über Accept-Language ok. Randfall: FR_BETREIBER_NAME nur aus Leerzeichen zeigt das Feld Name leer und keinen Hinweis nicht eingerichtet (F002 MEDIUM, widerspricht Verhalten 8; engine/anmeldung.py:617 ohne strip, engine/instanz.py:60). Seiten ohne Rechtszeile: Einladung unbekannt oder abgelaufen (404-Seite, engine/anmeldung.py:755), Konto-Lösch-Rückfrage (:555) und Konto-gelöscht-Seite (:835) (F001 LOW). Beispielreise und stadtwochenende gebaut: Fuß ohne hidden, Rechtszeile mit drei Links und data-t, Katalog beider Sprachen enthält seite.rahmen.recht.* (Bauordner danach gelöscht). nginx: drei exakte Orte mit __ZONE_KONTO__ in betrieb/vorlagen/nginx-konnektor-orte.inc:47-60. Betreiberwerte nur im Impressum (Probe, Test test_betreiberangaben_stehen_nur_im_impressum), im Katalog nur ein Kommentar. deploy.sh unverändert.
**Implementierer:** (nicht beteiligt)

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:680
  Evidence: GET 200 ohne Anmeldung in de und en; POST, PUT, DELETE abgelehnt (405 oder 403 bei falscher Herkunft); Pfade mit Anhang 404
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:611
  Evidence: Werte per esc maskiert (Probe mit script und img); Katalog ohne Betreiberangaben
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/anmeldung.py:171
  Evidence: fuss mit recht=True auf Warteliste (alle Hinweise), Anmeldung Adress- und Code-Seite, Einladung (Hauptfälle), Konto; Probe bestätigt Links auf /warteliste und /anmelden
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/texte_en.py:3369
  Evidence: gebaute Beispielreise und Stadtwochenende: Fuß ohne hidden, drei Links mit data-t, Schlüssel seite.rahmen.recht.* in beiden Sprachen im eingebetteten Katalog
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_de.py:3354
  Evidence: nur konto_loeschen zugesagt, folgt für den Rest, Inhalt entspricht der Tabelle (siehe F003 für eine kleine Auslassung)
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/texte_en.py:3327
  Evidence: alle recht.* Schlüssel in de und en; Ausnahmelisten unverändert
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/anmeldung.py:594
  Evidence: nginx-Vorlage mit drei exakten Orten und __ZONE_KONTO__; test_nginx grün
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/anmeldung.py:659
  Evidence: 1781 passed, 0 failed; Abläufe unverändert
  Status: CONFIRMED

Finding:
  ID: F002
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/anmeldung.py:617
  Description: impressum_inhalt prüft mit all(w for _, w in werte) ohne strip; ein Wert nur aus Leerzeichen gilt als gesetzt
  Spec requirement: AC-3 — leere Angabe führt zum Hinweis nicht eingerichtet, keine leeren Felder
  Conflict: Probe zeigt das Feld Name mit leerem Inhalt und keinen Hinweis
  Remediation: Werte vor der Prüfung mit strip() bereinigen

Finding:
  ID: F001
  Severity: LOW
  Category: spec_violation
  Code reference: engine/anmeldung.py:755
  Description: Einladung unbekannt oder abgelaufen (404), Konto-Lösch-Rückfrage und Konto-gelöscht-Seite haben keine Rechtszeile
  Spec requirement: AC-4 — Einladungsseite (alle Fälle) und Mein Konto tragen die Link-Zeile
  Conflict: einzelne Zustände ohne Link-Zeile
  Remediation: fuss(recht=True) anhängen oder in der Spec ausnehmen

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/texte_de.py:3350
  Description: Weitergabe nennt nicht, dass Auf Neueres prüfen im Fuß der Reiseseite eine externe Schnittstelle (Quellcode-Dienst) anfragt
  Spec requirement: AC-6 — Inhalt entspricht der Tabelle, nichts verschweigen
  Conflict: Auslassung, nur auf Tipp der Person
  Remediation: Satz ergänzen oder dem Product Owner bei der rechtlichen Prüfung zeigen

Finding:
  ID: F004
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/tests/test_betrieb.py:2054
  Description: Gelockerte Prüfung in test_betrieb_ohne_ki erkennt FR_BETREIBER= mit Leerzeichen nach der Raute nicht
  Spec requirement: AC-9 — bestehende Tests nicht abschwächen
  Conflict: leichte Abschwächung, fachlich nötig
  Remediation: Regex mit optionalem Leerraum nach der Raute

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/konnektor.py:3448
  Description: OPTIONS auf /impressum liefert Allow mit POST, obwohl der Dienst POST mit 405 ablehnt
  Spec requirement: AC-1 — nur GET
  Conflict: Allow-Kopf inkonsistent, ohne Wirkung
  Remediation: _erlaubt um die drei Pfade (GET, HEAD, OPTIONS) erweitern

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (precondition_origins.default_lang)

### Runde 3 (nach Korrektur F001, F002)
**Adversary:** Eigene HTTP-Probe adversary_probe2_test.py (Ausgabe adversary-probe2-output.txt). F002 behoben: engine/anmeldung.py:614 bereinigt jeden Wert mit strip(). Probe: Leerzeichen, Tab, Zeilenumbruch, Mischung aus Leerraum und NBSP (U+00A0), je in Name, Anschrift und Kontakt einzeln (die anderen gesetzt): immer 200 mit Hinweis nicht eingerichtet, kein Feld (kein strong-Tag). Alle drei fehlen: Hinweis. Werte mit Leerraum am Rand: Anzeige ohne Rand. Rest: Nur das Zeichen U+200B (Nullbreiten-Leerzeichen) gilt weiter als gesetzt und zeigt ein unsichtbares Feld (F006, LOW, praktisch irrelevant, da str.strip es nicht kennt). F001 behoben: Rechtszeile genau einmal auf /einladung/gibt-es-nicht (404), /konto?loeschen=1, nach Konto-Löschen (Seite Konto gelöscht, 200), Lösch-Antwort ohne Häkchen (400, Konto-Seite). Keine Doppelung: auf allen geprüften Seiten steht der Absatz class recht genau einmal (/warteliste, /anmelden, Code-Seite, /datenschutz, /impressum, /alpha, Warteliste-Bestätigen 404, /konto). /impressum verlinkt sich selbst nicht (ausser, Absicht), die Datenschutz-Seite hat 3 Impressum-Links (Einleitung, Kontakt, Rechtszeile), gewollt. Weitere Seiten ohne Rechtszeile: /kalender/xyz 404, allgemeine 404, 403 falsche Herkunft, 405 auf den Rechtspfaden. Das sind technische Fehlerantworten, keine Warteliste-, Anmelde-, Einladungs- oder Kontoseiten und liegen außerhalb von AC-4. Ein unbekannter Warteliste-Bestätigungslink und Einladung-unbekannt tragen die Zeile. Code reference: engine/anmeldung.py:614, engine/anmeldung.py:755, engine/anmeldung.py:836, engine/texte_de.py:3354, engine/texte_en.py:3352 (Zusage nur Konto-Löschen unverändert, folgt-Satz unverändert). Suite laut Entwickler 1784 grün; Datei test_rechtliches enthält test_leerraum_zaehlt_als_nicht_gesetzt.
**Implementierer:** F001 und F002 behoben.

Status der Befunde: F001 und F002 geschlossen. F003 und F005 bleiben LOW offen (an den Product Owner). F004 akzeptiert. F006 LOW neu, ohne Handlungsbedarf.

Finding:
  ID: F006
  Severity: LOW
  Category: edge_case
  Code reference: engine/anmeldung.py:614
  Description: Ein Wert nur aus U+200B zählt nach strip() als gesetzt und erzeugt ein unsichtbares Feld
  Spec requirement: AC-3 — leere Angabe, keine leeren Felder
  Conflict: praktisch nicht auftretend
  Remediation: optional zusätzlich Nullbreiten-Zeichen entfernen

## Verdict

VERDICT: AMBIGUOUS
Offen, zur Kenntnis des Product Owners: F003 (LOW, Datenschutztext lässt die Prüfanfrage Auf Neueres prüfen aus), F005 (LOW, Allow-Kopf bei OPTIONS), F006 (LOW). Alle neun ACs belegt, F001 und F002 behoben, keine CRITICAL- oder HIGH-Befunde.
Tests: 1781 passed in der ersten Runde (Gesamtlauf), Stand nach Korrektur laut Entwickler 1784 passed, 0 failed, 0 übersprungen; Probe 2 und Probe 1 grün.
Checklist: 9/9 Punkte belegt

## Geprüfte Dateien

- sha256:47811c1720f1a97b2bad106250f422d4200b2afb6d30ed8607ed0096c7a70892  engine/anmeldung.py
- sha256:ef7a8052b78b35f75885831c39993cbf2e96cf31165d73316b63c41b5954c723  engine/konnektor.py
- sha256:60da3e12fbb91b5240c4c84e43b167048b316687d4d9aeec5a4ed0c506003043  engine/tests/test_betrieb.py
- sha256:86234a9e588f7e332fbd0438d7953465fc42c727e253f892f3c6881eb4a6855d  engine/texte_de.py
- sha256:d1c4b22f2a0e394c2c0b4d7e9608524548e835cf478b8b60c7fd75eb8e312289  engine/texte_en.py

## Prüfbasis

- base: 8513f6ab3628bcfcde1250ebc766928eef794434
- blob:ed621ce665703a4390486db53a7178f14942434f  engine/anmeldung.py
- blob:21a11ab4dfd9bb35fb0b0011d934fc4d5965d478  engine/konnektor.py
- blob:d0770b9f39807ee6acd98d2aad43e95850dc8535  engine/tests/test_betrieb.py
- blob:cef5a31c51d05df94ba97d6814615aee292b72b2  engine/texte_de.py
- blob:16265cb453491105dff8a61dc04afc1e40f87ab7  engine/texte_en.py
