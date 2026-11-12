# Adversary Dialog — betreiber-meldung-530
Spec: docs/specs/betrieb/betreiber-meldung-530.md
Datum: 2026-11-12 11:00

## Checkliste
- [x] **AC-1 (Werkzeug für jedes Konto):** Für ein Konto mit Mitgliedschaft in `beispielreise`, eines mit Mitgliedschaft in `stadtwochenende`, eines mit beiden und eines ohne Reise listet `frieda_werkzeuge(k)` genau ein Werkzeug `an_frieda_melden` (englisch `report_to_frieda`); ohne Reise hat sein Schema keine Eigenschaft `reise`, mit Reisen ist `reise` eine Aufzählung genau der eigenen Reisen.
- [x] **AC-2 (Alias):** In `schnittstelle.NAMEN` steht `report_to_frieda` ↔ `an_frieda_melden`, in `PARAMETER` `zusammenhang` ↔ `context`; ein Aufruf mit den englischen und mit den deutschen Namen und Parametern führt zum selben Ergebnis.
- [x] **AC-3 (Meldung anlegen):** Gegeben ein Konto Ida (Mitglied von `beispielreise`), wenn `an_frieda_melden` mit `art=Fehler`, `text`, `reise=beispielreise`, `zusammenhang` aufgerufen wird, dann entsteht genau eine Zeile in `betreiber_meldungen` (`konto`, `reise`, `art`, `text`, `zusammenhang`, `zeit` gesetzt, `issue` `NULL`) und die Antwort ist `konnektor.an_frieda_melden.angekommen` mit der Nummer der Zeile, kein Fehler. Ohne `reise` und `zusammenhang` entsteht die Zeile mit leeren Feldern.
- [x] **AC-4 (Mail an Betreiber mit Reply-To):** Gegeben zwei Betreiber-Konten (eines englisch, eines deutsch) und ein Nicht-Betreiber, wenn Ida meldet, dann enthält `FR_MAIL_DATEI` genau zwei Mails (nur an die Betreiber), jede in der Sprache ihres Empfängers (Betreff `konto.betreiber_meldung.mail_betreff`, Text mit Nummer, Name, Adresse, Art, Reise, Text und Zusammenhang), jede mit `antwort_an` gleich der Adresse von Ida. Im SMTP-Zweig trägt die Nachricht den Kopf `Reply-To: <Adresse von Ida>` und als Absender die Adresse der Instanz.
- [x] **AC-5 (Fremde Reise abgelehnt):** Gegeben Idas Konto und eine Reise, in der sie nicht Mitglied ist (`stadtwochenende`), wenn sie `reise=stadtwochenende` meldet, dann Fehlerantwort `konnektor.frieda_werkzeug.1`, keine Zeile, keine Mail.
- [x] **AC-6 (Pflicht und Grenzen der Felder):** Leerer oder nur aus Leerraum bestehender `text` → `konto.betreiber_meldung.leer`; `text` oder `zusammenhang` mit 2001 Zeichen → `konto.betreiber_meldung.zu_lang`, genau 2000 Zeichen ist erlaubt; `art` außerhalb der Aufzählung oder fehlend → `konto.betreiber_meldung.art`; in allen drei Fällen keine Zeile, keine Mail, kein Eintrag in `versand`.
- [x] **AC-7 (Tagesgrenze):** Gegeben Idas Konto, wenn sie 10 Meldungen am selben Tag sendet, dann werden alle 10 angenommen, die elfte ergibt `konto.betreiber_meldung.grenze` (mit `n`=10), ohne Zeile und Mail; Tims Konto (anderes Konto) kann am selben Tag trotzdem melden; Zeilen in `versand` unter `betreiber_meldung:<konto>` sind älter als 24 Stunden nicht mehr gezählt (Zeit über das Mittel der Tests gesetzt).
- [x] **AC-8 (Mailfehler verliert nichts):** Gegeben `mail_senden` wirft `KontoFehler` für einen Betreiber (SMTP nicht eingerichtet oder Fehler), dann ist die Zeile gespeichert, der Tester bekommt „angekommen“, der zweite Betreiber bekommt seine Mail trotzdem, auf stderr steht genau eine Zeile `operator report <nr>: mail failed: …` je gescheiterte Mail (ohne Text der Meldung, ohne Adresse); die Meldung erscheint bei `my_trips` des Betreibers und in `konten.py meldungen`. Gibt es gar kein Betreiber-Konto: Zeile gespeichert, keine Mail, „angekommen“.
- [x] **AC-9 (Löschen entfernt alles):** Gegeben Ida hat gemeldet (Zeile und Schlüssel `betreiber_meldung:<konto>` in `versand`), wenn ihr Konto gelöscht wird (`konten.loeschen`), dann gibt es keine Zeile in `betreiber_meldungen` mit ihrem Konto und keinen `versand`-Schlüssel `betreiber_meldung:<konto>`; Meldungen anderer Konten bleiben. `test_loeschen_konto.py` bleibt grün (dessen Prüfung über `sqlite_master` erfasst die neue Tabelle ohne Änderung).
- [x] **AC-10 (Betreiber sieht offene Meldungen):** Gegeben ein Betreiber-Konto und zwei offene Meldungen, dann enthält `meine_reisen_konto` nach den Freischaltungs-Anfragen die Kopfzeile mit der Anzahl und je Meldung eine Zeile mit Nummer, Art, Name, Adresse und verdichtetem, auf 300 Zeichen gekürztem Text (höchstens die letzten 20). Eine als erledigt abgehakte Meldung steht nicht mehr darin. Ohne offene Meldungen fehlt der Block ganz.
- [x] **AC-11 (Nicht-Betreiber sieht keine Liste):** Gegeben Idas Konto (kein Betreiber) mit eigener offener Meldung, dann enthält `meine_reisen_konto` für sie weder Kopfzeile noch Meldungszeile.
- [x] **AC-12 (CLI listet und hakt ab):** `konten.py meldungen` gibt offene Meldungen aus (Nummer, Datum, Art, Adresse, Name, `trip:`, `issue: open`, Text, bei Zusammenhang `context:`); `--alle` auch erledigte mit ihrem Verweis; `konten.py meldung-erledigt <nr> <issue>` setzt den Verweis und gibt `done` aus (danach fehlt die Meldung ohne `--alle`); eine unbekannte Nummer gibt `no such report`; ein leerer Verweis führt zu Fehler `issue_fehlt` und lässt die Meldung offen.
- [x] **AC-13 (Export enthält die eigenen Meldungen):** Gegeben Ida und Karl haben je eine Meldung, davon Idas eine erledigt, dann enthält `person.json` von Ida (`export_person`) unter `betreiber_meldungen` genau ihre Meldung mit `art`, `text`, `zusammenhang`, `reise`, `zeit` und `erledigt`, aber ohne `issue`, ohne `id` und ohne Konto; Karls Meldung und seine Adresse kommen nirgends in Idas ZIP vor. Ohne Meldungen ist die Liste leer. Die bisherigen Felder von `person.json` sind unverändert.
- [x] **AC-14 (Datenschutzseite):** `/datenschutz` (de und en) enthält den Abschnitt „Meldungen an den Betreiber“ / „Reports to the operator“ mit dem Wortlaut aus Punkt 22/23, an der Stelle nach „Belege“ und vor „Sicherungen“; `recht.datenschutz.konto_loeschen` nennt die Meldungen; der Rechte-Block (`…reise_loeschen`, `…namen_freitext`, `…export`, `…folgt`, `…kontakt`) ist unverändert in Wortlaut und Reihenfolge. `test_rechtliches.py` bleibt grün.
- [x] **AC-15 (Alpha-Seite nennt den Weg):** `/alpha` (de und en) enthält den Satz aus `recht.alpha.melden` mit dem Wert von `FR_BETREIBER_KONTAKT`, wenn er gesetzt ist (maskiert: ein Wert mit `<` erscheint als Text, nicht als HTML); ist er nicht gesetzt oder nur Leerraum, steht stattdessen `recht.alpha.melden_impressum` mit einem Link `/impressum`, kein leerer Platzhalter und keine Zeichenfolge `{kontakt}`.
- [x] **AC-16 (Anleitung):** `anleitung_frieda(k)` enthält für ein Konto mit Reisen und für eines ohne Reise den Satz `konnektor.anleitung.frieda.melden` in der Sprache des Kontos (de und en).
- [x] **AC-17 (Export-Text):** `konto.export.punkt_4` nennt die Meldungen an den Betreiber (de und en); die Seite Mein Konto zeigt ihn so.
- [x] **AC-18 (Texte vollständig):** Jeder Schlüssel aus Punkt 22/23 steht in `texte_de.py` und `texte_en.py` (gleiche Platzhalter); `wert.Fehler` existiert; `test_texte.py` (Parität, Platzhalter, Literal-Test, Ausnahmelisten nicht länger, Pseudo-Sprache) bleibt grün; `recht.datenschutz.folgt` ist byteweise wie auf `main`.
- [x] **AC-19 (Nichts Weiteres ändert sich):** `betrieb/deploy.sh` und `neu.py` unverändert; `mail_senden` ohne `antwort_an` schreibt in `FR_MAIL_DATEI` dieselbe JSON-Zeile wie vorher (ohne `antwort_an`); die bestehenden Tests der Konten, des Konnektors und der Warteliste bleiben grün.
- [x] **AC-20 (Abnahme auf der Instanz) [nach Auslieferung, nicht prüfbar in dieser Phase, kein Defekt]:** Nach dem Ausliefern (Prüfpunkte des Issues, nach dem Ausliefern, an einer eigenen Testreise/einem Testkonto der Instanz, nie an echten Reisen): (a) Probe der Mail: Eine Meldung über die Claude-App kommt beim Betreiber an und „Antworten“ adressiert den Tester; (b) Löschen: ein Testkonto mit Meldung wird gelöscht, `konten.py meldungen --alle` zeigt keine Zeile mehr; (c) Datenschutz: `/datenschutz` und `/alpha` auf der Instanz zeigen die neuen Texte; (d) Export des Testkontos enthält die Meldung. Ergebnis als Kommentar in #530.

## Dialog

### Runde 1
**Adversary:** Testlauf 232 passed, 0 failed, 0 uebersprungen (docs/artifacts/betreiber-meldung-530/adversary-test-output.txt). Angriff auf Werkzeug, Ablage, Grenzen.

Confirmation: AC-1
Code reference: engine/konnektor.py:221
Evidence: an_frieda_melden_werkzeug fuer jedes Konto; reise-Enum nur bei vorhandenen Reisen; Pflicht text, art.
Status: CONFIRMED

Confirmation: AC-2
Code reference: engine/schnittstelle.py:79
Evidence: NAMEN-Paar und PARAMETER zusammenhang/context.
Status: CONFIRMED

Confirmation: AC-3, AC-5
Code reference: engine/konnektor.py:2367
Evidence: Zweig vor Reise-Auswahl; fremde Reise liefert konnektor.frieda_werkzeug.1 vor jeder Speicherung; Erfolg liefert angekommen mit nr.
Status: CONFIRMED

Confirmation: AC-6, AC-7, AC-8, AC-9
Code reference: engine/konten.py:759
Evidence: an_betreiber_melden prueft leer, 2000/2001, Art, dann _begrenzt und INSERT in einer Transaktion; Mails erst nach Commit, KontoFehler wird zu stderr-Zeile ohne Text und Adresse; _begrenzt zaehlt nur gespeicherte Eintraege (24-h-Fenster); loeschen entfernt Zeilen und Schluessel.
Status: CONFIRMED

Probe: Doppelzaehlung ausgeschlossen (_begrenzt schreibt nicht selbst). Nicht-str-Eingaben werden zu leerem Text, kein Absturz. Gesperrte Betreiber ausgeschlossen.
**Implementierer:** keine Einwaende.

### Runde 2
**Adversary:** Angriff auf Betreiber-Sicht, CLI, Export, Texte, Testlockerungen.

Confirmation: AC-4
Code reference: engine/konten.py:251
Evidence: mail_senden(antwort_an): Reply-To im SMTP-Zweig, JSON-Feld nur wenn gesetzt, Absender bleibt FR_ABSENDER; Betreff nur nr und art.
Status: CONFIRMED

Confirmation: AC-10, AC-11
Code reference: engine/konnektor.py:2334
Evidence: Block nur im Betreiber-Zweig, offen[-20:], Text verdichtet und auf 300 gekuerzt; Nicht-Betreiber ohne Block.
Status: CONFIRMED

Confirmation: AC-12
Code reference: engine/konten.py:1543
Evidence: meldungen [--alle]; meldung-erledigt nur bei 3 Argumenten und numerischer Nr (sonst Aufrufhilfe); leerer Verweis wirft KontoFehler (ERROR), Zeile bleibt offen.
Status: CONFIRMED

Confirmation: AC-13
Code reference: engine/anmeldung.py:949
Evidence: export_person nutzt eigene_betreiber_meldungen(kid): nur eigenes Konto, ohne id, issue, konto; zeit als ISO UTC.
Status: CONFIRMED

Confirmation: AC-14, AC-15, AC-17
Code reference: engine/anmeldung.py:1191
Evidence: Abschnitt nach belege vor sicherungen; alpha_inhalt trimmt FR_BETREIBER_KONTAKT, maskiert mit esc, sonst Impressum-Link; folgt im Diff gegen Basis 51dc745 nur Kontextzeile, unveraendert.
Status: CONFIRMED

Confirmation: AC-16, AC-18
Code reference: engine/texte_de.py:119
Evidence: alle Schluessel aus Punkt 22 im Spec-Wortlaut, wert.Fehler vorhanden.
Status: CONFIRMED

Confirmation: AC-18 (en)
Code reference: engine/texte_en.py:118
Evidence: wert.Fehler = bug und englische Fassungen; test_texte.py gruen.
Status: CONFIRMED

Confirmation: AC-19
Code reference: engine/konten.py:253
Evidence: Diff gegen Basis fuer betrieb/ und engine/neu.py leer; ohne antwort_an unveraenderte JSON-Zeile.
Status: CONFIRMED

Test-Anpassungen: test_export.py aendert nur punkt_4 (Wortlaut AC-17); test_rechtliches.py lockert nur fuer /alpha den Kontakt, Name und Anschrift bleiben verboten: minimal und spec-gedeckt.
AC-20: nach Auslieferung, in dieser Phase nicht pruefbar (kein Defekt).
Hinweis (LOW, kein Spec-Verstoss): mail_senden faengt ValueError aus EmailMessage nicht; Konten-Adressen sind validiert, daher nur theoretisch.
**Implementierer:** keine Einwaende.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`); keine verdaechtigen Zeilen. Tabelle betreiber_meldungen wird nur in an_betreiber_melden beschrieben (Bedingung: Text, Art, Grenze gueltig; Test: test_betreiber_meldung.py).

## Verdict

VERDICT: VERIFIED
Tests: 232 passed, 0 failed, 0 uebersprungen
Edge cases: alle geprueft, keine gebrochen (LOW-Hinweis oben)
Regressions: keine gefunden
Checklist: 19/19 pruefbare Punkte bewiesen; AC-20 erst nach Auslieferung

## Geprüfte Dateien

- sha256:948d6e8611f9fa7b86067702a8b4e83f9718a3fe840e9a16a99d73f37611c636  engine/anmeldung.py
- sha256:babc5e1e9d9dad1c0979442318cb6a2b7ed5760b88a7dea7501930865488a625  engine/konnektor.py
- sha256:fbd7959d9dc6db1b92ef0c61b189d86a4469ce04719eeecb99865f91ce513f0d  engine/konten.py
- sha256:d6cb698055cffbbee20427a14a31b9f3ccb9099b8ea3beff81dbeb864dfc4c7b  engine/schnittstelle.py
- sha256:516d391b7bd16e175a4740efe8582c919e462daad12fccf283a771e4d445fc35  engine/texte_de.py
- sha256:d1c072c2bac0aeba24043a0a554409cf2397107a9ae3ea6f25b8d02a5368c54c  engine/texte_en.py

## Prüfbasis

- base: 51dc74539205b220e51dd300ded2ad5e51a095c9
- blob:d38cd4508bd40310f6daf96fdc0dd37d666f7a6f  engine/anmeldung.py
- blob:869ee38f710cdcfd0de5f2ed3bc522e140010757  engine/konnektor.py
- blob:4e35b76f26c94d6329e4e0677e0d269370353280  engine/konten.py
- blob:d2cedc91a01eb35f74d5d3639a6a52c5eb1dc836  engine/schnittstelle.py
- blob:38e06247e982db7907957e2017f0a536dc145a6b  engine/texte_de.py
- blob:3f4c5bd057961c3bc2d83cb36a66b55787fc81f4  engine/texte_en.py

## Geprüfte Dateien

- sha256:948d6e8611f9fa7b86067702a8b4e83f9718a3fe840e9a16a99d73f37611c636  engine/anmeldung.py
- sha256:babc5e1e9d9dad1c0979442318cb6a2b7ed5760b88a7dea7501930865488a625  engine/konnektor.py
- sha256:fbd7959d9dc6db1b92ef0c61b189d86a4469ce04719eeecb99865f91ce513f0d  engine/konten.py
- sha256:d6cb698055cffbbee20427a14a31b9f3ccb9099b8ea3beff81dbeb864dfc4c7b  engine/schnittstelle.py
- sha256:516d391b7bd16e175a4740efe8582c919e462daad12fccf283a771e4d445fc35  engine/texte_de.py
- sha256:d1c072c2bac0aeba24043a0a554409cf2397107a9ae3ea6f25b8d02a5368c54c  engine/texte_en.py

## Prüfbasis

- base: 51dc74539205b220e51dd300ded2ad5e51a095c9
- blob:d38cd4508bd40310f6daf96fdc0dd37d666f7a6f  engine/anmeldung.py
- blob:869ee38f710cdcfd0de5f2ed3bc522e140010757  engine/konnektor.py
- blob:4e35b76f26c94d6329e4e0677e0d269370353280  engine/konten.py
- blob:d2cedc91a01eb35f74d5d3639a6a52c5eb1dc836  engine/schnittstelle.py
- blob:38e06247e982db7907957e2017f0a536dc145a6b  engine/texte_de.py
- blob:3f4c5bd057961c3bc2d83cb36a66b55787fc81f4  engine/texte_en.py
