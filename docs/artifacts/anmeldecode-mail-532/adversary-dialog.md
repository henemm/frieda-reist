# Adversary Dialog — anmeldecode-mail-532
Spec: docs/specs/betrieb/anmeldecode-mail-532.md
Datum: 2026-11-19 19:16

## Checkliste
- [x] **AC-1 (Mehrteiler):** Gegeben `mail_senden(an, betreff, text, html=h)` im SMTP-Zweig (Spion für `smtplib.SMTP`), dann ist die gesendete Nachricht `multipart/alternative` mit genau zwei Teilen: zuerst `text/plain` mit dem Text, dann `text/html` mit `h`. Ohne `html` ist sie eine einteilige `text/plain`-Nachricht wie bisher.
- [x] **AC-2 (Anzeigename):** Gegeben `FR_ABSENDER=frieda@beispiel.invalid`, dann lautet `From` `Frieda <frieda@beispiel.invalid>`. Gegeben `FR_ABSENDER=Andere Person <frieda@beispiel.invalid>`, dann lautet `From` ebenfalls genau `Frieda <frieda@beispiel.invalid>` (kein doppelter Name, nur ein „Frieda“). Gegeben ein `FR_ABSENDER` mit Zeilenumbruch (`a@b.invalid\nBcc: x@y.invalid`) oder ohne gültige Adresse, dann wird nichts gesendet und `KontoFehler("konto.fehler.mail_nicht_eingerichtet")` geworfen; kein Kopf `Bcc` entsteht.
- [x] **AC-3 (Dateizeile ohne HTML unverändert):** Gegeben `FR_MAIL_DATEI` und `mail_senden` ohne `html`, dann ist die geschriebene Zeile byte-gleich mit der bisherigen (`an`, `betreff`, `text`, bei `antwort_an` zusätzlich dieses Feld); die Dateizeilen-Prüfung in `test_mail_senden_antwort_an_smtp` bleibt unverändert (nur dessen `From`-Erwartung ändert sich, siehe AC-2).
- [x] **AC-4 (Dateizeile mit HTML):** Gegeben `mail_senden` mit `html`, dann enthält die Zeile zusätzlich das Feld `html` mit genau diesem Wert, die übrigen Felder wie ohne `html`.
- [x] **AC-5 (Betreff mit Code vorn):** Gegeben eine Code-Anforderung (`zweck=anmelden`, de und en), dann beginnt der Betreff mit den sechs Ziffern des Codes ohne Leerzeichen (zuerst Ziffern, dann das übrige Wort), enthält keinen Zeilenumbruch und denselben Code wie Text- und HTML-Teil. Für `zweck=adresse` gilt dasselbe mit dem Betreff `mail.code.betreff_adresse`.
- [x] **AC-6 (Code nie in einem Link):** Gegeben `FR_BASIS=https://frieda.beispiel.invalid`, dann steht der Code in keiner Adresse (`href` und ausgeschriebene Links in Text und HTML) und in keinem Betreff-Link; der Link der Anmeldung enthält `schritt=code` und `email=`, aber keine Ziffernfolge des Codes.
- [x] **AC-7 (Link nur bei Anmelden mit Basis):** Gegeben `zweck=anmelden` und gesetztes `FR_BASIS`, dann enthalten Text und HTML den Link zur Code-Eingabe. Gegeben `zweck=adresse`, dann enthält die Mail diesen Link nicht (und keinen `href` auf `/anmelden`). Gegeben kein `FR_BASIS`, dann gibt es keinen Link der Code-Eingabe und keinen `href` im HTML, der Text enthält nicht `mail.code.zeile_link`. Gegeben ein `FR_BASIS` mit anderem Schema als `http`/`https`, dann entsteht kein Link.
- [x] **AC-8 (Text-Teil vollständig):** Gegeben die Mail wird nur als Text gelesen, dann enthält sie in de und en: den Code, die Gültigkeit mit „10“ aus `CODE_MINUTEN` (Test setzt zusätzlich einen anderen Wert und sieht ihn in der Mail), den Sicherheitshinweis (`mail.code.sicher_text`), den Grund (`mail.fuss.grund`) und die Wörter für Impressum und Datenschutz; kein `<`-Markup und keinen Platzhalter `{…}`.
- [x] **AC-9 (HTML-Gerüst):** Gegeben der HTML-Teil, dann enthält er `<table`, `color-scheme` (Meta) und `prefers-color-scheme: dark`; sein einziger `<style>`-Block enthält nur diesen Dunkelmodus (keine sonstigen Regeln außerhalb von `@media`); alle übrigen Gestaltung steht in `style="…"`. Er enthält keinen der Marker `<img`, `<link`, `<script`, `<iframe`, `<form`, `url(`, `@import`, `@font-face`; jede in ihm vorkommende Adresse steht in einem `href` auf `basis()`; es gibt keine Adresse mit `http` außerhalb von `href`.
- [x] **AC-10 (Escaping):** Gegeben `FR_BETREIBER_NAME` und `FR_BETREIBER_ANSCHRIFT` mit `<script>alert(1)</script> & "x"` und eine Adresse `a+<b>@beispiel.invalid`, dann steht im HTML nur die escapte Form (`&lt;script&gt;`, `&amp;`, `&quot;`), nie das rohe `<script>`; im Text-Teil erscheinen die Werte unverändert als Text; Zeilen der Anschrift sind mit `<br>` getrennt, jede einzeln escaped.
- [x] **AC-11 (Fuß mit Betreiberwerten):** Gegeben `FR_BETREIBER_NAME` und `FR_BETREIBER_ANSCHRIFT` gesetzt und `FR_BASIS` gesetzt, dann enthalten Text und HTML den Grund, den Betreibernamen, die Anschrift, `basis()/impressum` und `basis()/datenschutz` (im HTML als `href`).
- [x] **AC-12 (Fuß ohne Betreiberwerte, ohne Basis):** Gegeben `FR_BETREIBER_NAME` und `FR_BETREIBER_ANSCHRIFT` nicht gesetzt oder nur Leerraum, dann ist die Mail trotzdem gültig und vollständig: der Fuß enthält den Grund und die Wörter für Impressum und Datenschutz, aber keine leere Zeile mit Platzhalter, kein „None“ und keine Zeichenfolge `{`; es gibt keinen Fehler. Gegeben nur eine der beiden Angaben gesetzt, dann steht genau diese da. Gegeben kein `FR_BASIS`, dann stehen Impressum und Datenschutz als Wörter ohne Link und ohne Adresse.
- [x] **AC-13 (de und en, nur Katalog):** Gegeben `sprache` `de` und `en`, dann stammen alle sichtbaren Wörter der Mail aus dem Katalog der Sprache (Test vergleicht mit `text(...)`); jeder Schlüssel aus Punkt 12 steht in `texte_de.py` und `texte_en.py` mit gleichen Platzhaltern; `engine/tests/test_texte.py` (Parität, Literal-Test, Pseudo-Sprache) ist grün, die Ausnahmelisten sind nicht länger.
- [x] **AC-14 (Keine Zirkelbezüge):** `import engine.mailrahmen` gelingt ohne dass `anmeldung` geladen wird (Test: `sys.modules` vor und nach dem Import in einem frischen Prozess); `mailrahmen.py` enthält weder `import anmeldung` noch `import konten`.
- [x] **AC-15 (Andere Mails unverändert):** Gegeben Betreiber-Meldung, Warteliste, Freigabe, Einladung und Reise löschen, dann sind ihre `FR_MAIL_DATEI`-Zeilen (Betreff, Text, `antwort_an`) byte-gleich wie vor der Änderung und tragen kein Feld `html`.
- [x] **AC-16 (Eine Mail je Anforderung):** Gegeben eine Code-Anforderung, dann enthält `FR_MAIL_DATEI` genau eine Zeile mit `an` gleich der Adresse; die stille Tagesgrenze (`still`) und die Antwort für unbekannte Adressen verhalten sich wie vorher (keine Mail bei `still`, gleiche Rückgabe).
- [x] **AC-17 (Deploy-Listen):** `mailrahmen.py` steht in `RM_MODULE`, `KN_MODULE`, `SB_MODULE` und `PS_MODULE` von `betrieb/deploy.sh` (Test in `engine/tests/test_betrieb.py` für neue eigene Module bleibt grün).
- [x] **AC-18 (Doku):** `docs/design.md` beschreibt den „Mail-Rahmen“ (Mail ist keine Seite und der Rahmen kein Atomic-Design-Baustein der Seite, siehe ADR-Abschnitt; kein Eintrag in `GRUNDFORMEN`, Impressum und Datenschutz bleiben auf ihrer Seite und werden nur verlinkt); `docs/betrieb.md` beschreibt das Format von `FR_MAIL_DATEI` (Felder `an`, `betreff`, `text`, optional `html`, `antwort_an`) und den Mailabschnitt. Der Mail-Rahmen steht in `docs/design.md` in einem eigenen Abschnitt **außerhalb** der Ebenen-Tabelle (`| Ebene | Bausteine` bis `## Ontologie und Bausteine`) und ohne Eintrag im Kopfkommentar von `engine/vorlage.html`: Er ist ein Python-Baustein der Mail, keine Funktion der Seite; `engine/tests/test_design.py` (Abgleich Vorlage ↔ Tabelle, „fremde“ Namen in der Tabelle sind verboten) bleibt dadurch unverändert grün.
- (nach Auslieferung, Phase 7) **AC-19 (Abnahme auf der Instanz):** Nach dem Ausliefern, mit einem eigenen Testkonto der Instanz (nie echte Reisen, nie fremde Adressen): (a) Eine Anmeldung per E-Mail liefert eine Mail mit Absender „Frieda“, Betreff mit Code vorn und gut lesbarem Code; (b) sie wird in mindestens einem Client im Hell- und im Dunkelmodus geprüft (Zeichen lesbar, Fuß vorhanden); (c) Impressum- und Datenschutz-Link führen zu den Seiten der Instanz; (d) die Zustellung landet im Posteingang (nicht im Spam) bei mindestens einem Testpostfach bei Gmail und einem bei Stalwart; (e) die Mail als Text allein gelesen ist vollständig. Ergebnis als Kommentar in #532; das Issue wird erst danach geschlossen.

## Dialog

### Runde 1
**Adversary:** Testlauf der gezielten Dateien (test_mailrahmen, test_konten, test_anmeldung, test_betreiber_meldung, test_texte, test_betrieb, test_design): 477 passed, 0 failed, 0 übersprungen (adversary-test-output.txt). Entwicklerlauf der Gesamtsuite: 3410 passed. Prüfung der Hinweise: (1) `f.value.args[0]` in den zwei Tests war nie der Schlüssel, denn `KontoFehler.__init__` übergibt an `super().__init__` den übersetzten Satz (engine/konten.py:90-92); `.schluessel` ist die strengere und richtige Prüfung (Schlüsselgleichheit statt Textgleichheit), keine Abschwächung. (2) Zusatzparameter `basis` in `code_mail` (engine/mailrahmen.py:75): bewusst, damit mailrahmen konten nicht importiert (AC-14); keine Spec-Verletzung, nur Abweichung der Signatur.
Sondierungen: Header-Injektion über FR_ABSENDER: `parseaddr` liefert für `a@b.invalid, c@d.invalid`, `Name, X <a@b.invalid>` und `a@b.invalid;x` leere Adresse, also KontoFehler (engine/konten.py:285-288); Zeilenumbruch wird vorab abgewiesen. Escaping: Betreibername `<script>x</script>&"y"` erscheint im Text unverändert, im HTML nur über `esc` (engine/mailrahmen.py:56-62). Code in Links: `code_link` enthält nur `schritt` und `email` (engine/mailrahmen.py:72); Code steht nur in Text/HTML-Körper. Basis mit `javascript:` oder Großschreibung `HTTPS://` ergibt keinen Link (engine/mailrahmen.py:31-34). Zirkel: mailrahmen importiert nur html, urllib.parse, instanz, texte. Dateizeile: Feld `html` nur bei gesetztem html (engine/konten.py:~293), sonst Zeile unverändert. Andere Mails: nur `code_anfordern` ruft mailrahmen auf (engine/konten.py:362); übrige Aufrufer von `mail_senden` unverändert. Altes `zeile_loeschen` ist weg und wird durch Test abgesichert. Deploy-Listen: mailrahmen.py in allen vier Listen (betrieb/deploy.sh:26,27,33,35). Katalog: Schlüssel in de und en vorhanden (engine/texte_de.py:1167, engine/texte_en.py:1166), test_texte grün.
**Implementierer:** (nicht beteiligt; Kontextisolation)

### Runde 2
**Adversary:** Nachbohren an Randfällen. (a) Nicht-ASCII-Adresse in FR_ABSENDER (z. B. `ä@b.invalid`): `email.utils.formataddr` wirft `UnicodeEncodeError` statt KontoFehler (engine/konten.py:292); nur bei Fehlkonfiguration durch den Betreiber, Mail wird dann nicht versendet; kein Sicherheitsproblem. (b) Basis in Großschreibung (`HTTPS://`) wird still als „keine Basis“ behandelt: sichere Ausfallrichtung, Mail ohne Link (engine/mailrahmen.py:34). (c) Ein NUL-Zeichen in FR_ABSENDER wird nicht abgewiesen (engine/konten.py:286); nur Betreiberkonfiguration. (d) Der Code im Betreff ist durch `" ".join(split())` auf eine Zeile normiert (engine/mailrahmen.py:77); er besteht ohnehin nur aus Ziffern. (e) E-Mail-Adresse mit `<`, `"`, `&` im Link: urlencode, danach `esc` im href; keine Attributausbrüche. (f) Basis mit Anführungszeichen: im href escaped, Text enthält sie roh (Betreiber-eigener Wert, kein Angriffsweg). (g) AC-9 „Adresse nur in href“: im Footer erscheinen Adressen nur als href; im Textteil ausgeschrieben, wie gefordert. Keine Regression gefunden, kein Finding über LOW.

Findings:
Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/konten.py:292
  Description: formataddr mit Nicht-ASCII-Adresse aus FR_ABSENDER wirft UnicodeEncodeError (kein KontoFehler); NUL im FR_ABSENDER wird nicht abgewiesen.
  Spec requirement: AC-2 — ungültige Absender liefern KontoFehler mail_nicht_eingerichtet
  Conflict: Nur für Nicht-ASCII/Steuerzeichen; die Spec nennt Zeilenumbruch und fehlende Adresse. Betreiberkonfiguration, kein Angriffsweg.
  Remediation: Vor formataddr auf ascii und Steuerzeichen prüfen und KontoFehler werfen (optional).

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/mailrahmen.py:34
  Description: gueltige_basis ist schemagroß-/kleinschreibungsempfindlich; `HTTPS://x` ergibt keinen Link und keinen Fuß-Link.
  Spec requirement: AC-7 — andere Schemata als http/https erzeugen keinen Link
  Conflict: Sichere Richtung, aber Großschreibung ist ein gültiges Schema; harmlos, da FR_BASIS im Betrieb klein geschrieben wird.
  Remediation: optional `.lower().startswith`.

Confirmation:
  AC: AC-1
  Code reference: engine/konten.py:266
  Evidence: set_content(text) plus add_alternative(html, subtype="html"); test_mehrteiler_text_und_html_smtp grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/konten.py:285
  Evidence: parseaddr, Zeilenumbruch-/Adressprüfung, formataddr(("Frieda", adresse)); Sondierung bestätigt leere Adresse für Komma/Semikolon-Fälle.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/konten.py:276
  Evidence: Dateizeile ohne html unverändert (zeile nur an, betreff, text, antwort_an).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/konten.py:277
  Evidence: `if html: zeile["html"] = html`.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/texte_de.py:1167
  Evidence: Betreff beginnt mit {code} (de, en, anmelden und adresse); Code ohne Leerzeichen in code_anfordern (engine/konten.py:362) und Ziffern in Betreff/Text/HTML.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/mailrahmen.py:72
  Evidence: Link enthält nur schritt und email; Sondierung zeigt Link ohne Code.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/mailrahmen.py:34
  Evidence: nur http(s)-Basis; code_link nur bei zweck anmelden (engine/konten.py:361); javascript: ergibt None.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/mailrahmen.py:83
  Evidence: Textteil mit Titel, Code, Gültigkeit (minuten Parameter), Sicherheitshinweis, Fuß; Sondierungsausgabe ohne Markup und Platzhalter.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/mailrahmen.py:95
  Evidence: Tabellen, Meta color-scheme, einziger Style-Block nur DUNKEL (engine/mailrahmen.py:15); keine verbotenen Marker im Quelltext des Gerüsts.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/mailrahmen.py:58
  Evidence: jede Anschriftzeile einzeln escaped, mit <br> verbunden; Name via esc.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/mailrahmen.py:44
  Evidence: fuss() setzt Grund, Name, Anschrift, Impressum- und Datenschutz-Links aus basis.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/mailrahmen.py:52
  Evidence: Name/Anschrift nur bei Vorhandensein; ohne Basis Wörter ohne Link.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/texte_en.py:3625
  Evidence: Schlüssel mail.code.* und mail.fuss.* in de und en gleich; test_texte grün (477 passed).
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/mailrahmen.py:9
  Evidence: Importe nur html, urllib.parse, instanz, texte.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/konten.py:362
  Evidence: nur der Code-Pfad nutzt mailrahmen/html; alle anderen mail_senden-Aufrufe unverändert; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/konten.py:358
  Evidence: `still`-Rückkehr vor dem Versand unverändert, genau ein mail_senden-Aufruf.
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: betrieb/deploy.sh:26
  Evidence: mailrahmen.py in RM, KN, SB, PS; test_betrieb grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: docs/design.md:1
  Evidence: Abschnitt Mail-Rahmen und FR_MAIL_DATEI-Format durch test_doku_mailrahmen_und_mail_datei und test_design belegt (grün).
  Status: CONFIRMED

AC-19: nach Auslieferung offen, nicht durch Tests belegbar.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Tests: 477 passed, 0 failed, 0 übersprungen (Entwickler: 3410 passed gesamt)
Edge cases: F001, F002 nur LOW, Betreiberkonfiguration beziehungsweise sichere Ausfallrichtung
Regressions: None found
Checklist: 18/19 belegt; AC-19 nach Auslieferung offen

## Geprüfte Dateien

- sha256:9da7d021c9dc2bd68c1694e8eb09cd51a781b3c92f0098481673c3380845c48c  betrieb/deploy.sh
- sha256:d9f979c7fce700e33230a0c2858551753cd6a85519d1fbc69f004e7d888c5a2c  docs/design.md
- sha256:1b2ae577fbe1be78a888434ae7f9576a7a98392526e56b78fef109d9f1890cbb  engine/konten.py
- sha256:30a6d53a5d96b3b8edc957e6ba1767d2b3e9c94e1843f664ae12d868ebce2bdc  engine/mailrahmen.py
- sha256:eb95d1fd9110e9c0891a549b0d97c8d0083a2eb3e22d9f4ebccf8902d35f116e  engine/texte_de.py
- sha256:f893e334685a012a5e8c095d73d34c70aef38abcb5144ed775c956c86f7e52dc  engine/texte_en.py

## Prüfbasis

- base: 3787dfef042552567e98f5e2dcdd7629400f92da
- blob:10f7f44ab31ba2bee9cb80f7236c79bae7cf1e38  betrieb/deploy.sh
- blob:a74561e3aee583bac4ce048ea5afedf0d96801ff  docs/design.md
- blob:31cb32da3f5cc8e805587ac61be4c8e14f6f6f64  engine/konten.py
- blob:8b8c2e3b56a093a467c9cdcd2b1dd812909d9983  engine/mailrahmen.py
- blob:11c7188ea68da6ad8031227abc8ccdf16165dd26  engine/texte_de.py
- blob:9b17320f29e4b70c7b1a635ee1b670b1f1c887fc  engine/texte_en.py

## Geprüfte Dateien

- sha256:9da7d021c9dc2bd68c1694e8eb09cd51a781b3c92f0098481673c3380845c48c  betrieb/deploy.sh
- sha256:d9f979c7fce700e33230a0c2858551753cd6a85519d1fbc69f004e7d888c5a2c  docs/design.md
- sha256:1b2ae577fbe1be78a888434ae7f9576a7a98392526e56b78fef109d9f1890cbb  engine/konten.py
- sha256:30a6d53a5d96b3b8edc957e6ba1767d2b3e9c94e1843f664ae12d868ebce2bdc  engine/mailrahmen.py
- sha256:eb95d1fd9110e9c0891a549b0d97c8d0083a2eb3e22d9f4ebccf8902d35f116e  engine/texte_de.py
- sha256:f893e334685a012a5e8c095d73d34c70aef38abcb5144ed775c956c86f7e52dc  engine/texte_en.py

## Prüfbasis

- base: 3787dfef042552567e98f5e2dcdd7629400f92da
- blob:10f7f44ab31ba2bee9cb80f7236c79bae7cf1e38  betrieb/deploy.sh
- blob:a74561e3aee583bac4ce048ea5afedf0d96801ff  docs/design.md
- blob:31cb32da3f5cc8e805587ac61be4c8e14f6f6f64  engine/konten.py
- blob:8b8c2e3b56a093a467c9cdcd2b1dd812909d9983  engine/mailrahmen.py
- blob:11c7188ea68da6ad8031227abc8ccdf16165dd26  engine/texte_de.py
- blob:9b17320f29e4b70c7b1a635ee1b670b1f1c887fc  engine/texte_en.py

## Geprüfte Dateien

- sha256:9da7d021c9dc2bd68c1694e8eb09cd51a781b3c92f0098481673c3380845c48c  betrieb/deploy.sh
- sha256:d9f979c7fce700e33230a0c2858551753cd6a85519d1fbc69f004e7d888c5a2c  docs/design.md
- sha256:1b2ae577fbe1be78a888434ae7f9576a7a98392526e56b78fef109d9f1890cbb  engine/konten.py
- sha256:30a6d53a5d96b3b8edc957e6ba1767d2b3e9c94e1843f664ae12d868ebce2bdc  engine/mailrahmen.py
- sha256:eb95d1fd9110e9c0891a549b0d97c8d0083a2eb3e22d9f4ebccf8902d35f116e  engine/texte_de.py
- sha256:f893e334685a012a5e8c095d73d34c70aef38abcb5144ed775c956c86f7e52dc  engine/texte_en.py

## Prüfbasis

- base: 3787dfef042552567e98f5e2dcdd7629400f92da
- blob:10f7f44ab31ba2bee9cb80f7236c79bae7cf1e38  betrieb/deploy.sh
- blob:a74561e3aee583bac4ce048ea5afedf0d96801ff  docs/design.md
- blob:31cb32da3f5cc8e805587ac61be4c8e14f6f6f64  engine/konten.py
- blob:8b8c2e3b56a093a467c9cdcd2b1dd812909d9983  engine/mailrahmen.py
- blob:11c7188ea68da6ad8031227abc8ccdf16165dd26  engine/texte_de.py
- blob:9b17320f29e4b70c7b1a635ee1b670b1f1c887fc  engine/texte_en.py
