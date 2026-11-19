---
entity_id: anmeldecode-mail-532
type: feature
created: 2026-11-19
updated: 2026-11-19
status: draft
workflow: anmeldecode-mail-532
version: "1.0"
tags: [konten, anmeldung, mail, zustellbarkeit, alpha, m7]
---

# Anmeldecode-Mail professionell gestalten (#532)

## Approval

- [ ] Approved

## Purpose

Die Mail mit dem Anmeldecode ist heute eine nackte Textmail: Der Absender trägt keinen Anzeigenamen, der Code steht mit Leerzeichen mitten im Satz, es gibt keinen Hinweis, was zu tun ist, wenn man die Mail nicht erwartet hat, und keinen Fuß mit Betreiber, Impressum und Datenschutz. Das ist die erste Mail, die jede neue Person von Frieda sieht (öffentliche Alpha), und sie entscheidet über Vertrauen und Zustellbarkeit. Mit dieser Spec bekommt die Mail für den Anmeldecode und den Code für eine neue Adresse einen Betreff mit dem Code vorn, einen großen, kopierbaren Code, die Gültigkeit, einen Sicherheitshinweis, den Anzeigenamen „Frieda“ im Absender, einen Fuß mit Grund, Betreiberangaben und Links auf Impressum und Datenschutz sowie einen HTML-Teil neben dem vollständigen Text-Teil.

Ursprung: Issue #532. Maßgeblich sind der Plan im Kommentar vom 12.11.2026 (10:49 UTC) und die Freigabe des Product Owners vom 12.11.2026 (11:07 UTC) für den Entwurf „So einbauen“ in Deutsch und Englisch. Das Artefakt ist nicht mehr abrufbar; diese Spec ersetzt es als Vorgabe. Kontext und Analyse: `docs/context/anmeldecode-mail-532.md`. Die weiteren Mails (Warteliste, Freigabe, Einladung, Reise löschen, Betreiber-Meldung) bekommen den Rahmen später, nicht in diesem Issue.

## Ziel und Abgrenzung

- **Im Scope:**
  - `mail_senden` in `engine/konten.py` bekommt den optionalen Parameter `html` (Mehrteiler `text/plain` + `text/html`) und schickt den Absender mit Anzeigenamen „Frieda“.
  - Neues Modul `engine/mailrahmen.py`: baut aus Titel, Vorschautext, Code, Gültigkeit, Link, Sicherheitshinweis und Fuß den HTML-Teil und den Text-Teil aus denselben Textschlüsseln.
  - `code_anfordern` (Zweck `anmelden` und `adresse`) nutzt den Rahmen; neuer Betreff mit Code vorn.
  - Neue und überarbeitete Texte `mail.code.*` und `mail.fuss.*` in `engine/texte_de.py` und `engine/texte_en.py`.
  - `betrieb/deploy.sh`: `mailrahmen.py` in die Modullisten, die `konten.py` laden.
  - Anpassung der Betreff-Erwartungen in bestehenden Tests; neue Tests in `engine/tests/test_mailrahmen.py`.
  - Doku: `docs/design.md` (Baustein „Mail-Rahmen“), `docs/betrieb.md` (Mailabschnitt, Format von `FR_MAIL_DATEI`).
- **Nicht im Scope:**
  - Der Rahmen für die Mails Warteliste, Freigabe, Einladung, Reise löschen und Betreiber-Meldung: sie bleiben Text-Mails, mit eigenem Betreff und unverändertem Inhalt (später, eigene Issues).
  - Keine Bilder, kein Logo, kein Zählpixel, keine externen Ressourcen, keine Webschriften (Datenschutz, Zustellbarkeit).
  - Keine Änderung an Code-Erzeugung, Gültigkeit (`CODE_MINUTEN`), Begrenzungen, Hash, Einlösen, Antwortverhalten für bekannte und unbekannte Adressen.
  - Keine Änderung an Absenderadresse, Versanddienst und Zustellbarkeit der Domain (SPF, DKIM, DMARC; Infrastruktur, henemm-infra#433).
  - Kein zweiter Versand: eine Mail je Code-Anforderung, das Mailkontingent bleibt unverändert.
  - Kein Mailvorlagen-System, keine Sprachen außer den vorhandenen (de, en); jede künftige `texte_<kürzel>.py` folgt `docs/sprachen.md`.
- **Kern (ADR-0001):** Konten und Betrieb, keine Ontologie. Keine Grundform und kein Merkmal einer Reise ist berührt; keine KI; die Mail ist keine Seite, sondern ein Gerüst ohne Eintrag in `GRUNDFORMEN`. Nichts Reisespezifisches; beide Beispielreisen sind unberührt (die Mail kennt keine Reise).
- **Instanzen:** Betreibername und Anschrift kommen nur aus `FR_BETREIBER_NAME` und `FR_BETREIBER_ANSCHRIFT` (`engine/instanz.py`), Basisadresse aus `FR_BASIS`, Absender aus `FR_ABSENDER`; nichts Instanzspezifisches im Code. Keine echten Adressen, Namen oder Pfade in Spec, Tests und Beispielen (erfundene Werte mit der Domain `beispiel.invalid`).
- **Keine Umstellung in `neu.py nachziehen`:** Weder Reisedaten noch Dateiformate der Reisen ändern sich. Die Zeile in `FR_MAIL_DATEI` (nur Tests und Entwicklung) bekommt höchstens das Feld `html`, und nur dort, wo HTML gesetzt ist.

## Source

Zeilennummern nach dem Stand von `main` (Branch `feat-532-anmeldecode-mail`).

- `engine/konten.py`: `basis` (Z. 260), `mail_senden` (Z. 264; `FR_MAIL_DATEI`-Zweig Z. 268–274, SMTP-Zweig Z. 275–291, `From` = `FR_ABSENDER` roh, `set_content(text)`), `CODE_MINUTEN` (Z. 67), `code_anfordern` (Z. 305–356; Code `NNN NNN` mit Leerzeichen Z. 348, Zeilen Z. 349–354, Betreff Z. 355, Versand Z. 356). Weitere Aufrufer von `mail_senden`, die unverändert bleiben: Betreiber-Meldung (mit `antwort_an`), Warteliste, Freigabe, Einladung in `konten.py`, Reise löschen in `engine/anmeldung.py`.
- `engine/anmeldung.py`: `RECHT` (Z. 1236, Pfade `/datenschutz`, `/impressum`, `/alpha`), `BETREIBER` (Z. 1237), `impressum_inhalt` (Z. 1259; „leer zählt als nicht gesetzt“). `konten.py` darf `anmeldung.py` nicht importieren (Zirkel).
- `engine/instanz.py`: `wert(name, vorgabe)`.
- `engine/texte_de.py` Z. 1166–1171 und `engine/texte_en.py` Z. 1165–1170: `mail.code.betreff_adresse`, `betreff_anmelden`, `zeile_code`, `zeile_eingabe`, `zeile_link`, `zeile_loeschen`.
- `betrieb/deploy.sh`: `RM_MODULE` (Z. 26), `KN_MODULE` (Z. 27), `SB_MODULE` (Z. 33), `PS_MODULE` (Z. 35); alle enthalten `konten.py`.
- `engine/tests/test_anmeldung.py` (Z. 329: Betreff `startswith("Frieda: your code")` und Text „Your code for Frieda“), `engine/tests/test_konten.py` (Z. 50, 149: `meldet(m["betreff"], "mail.code.betreff_adresse")`, Link und Text; Z. 333 und 413: alter Betreff „Frieda: dein Code“/„Frieda: your code“), `engine/tests/test_betreiber_meldung.py` (`test_mail_senden_antwort_an_smtp`, Z. 301: SMTP-Spion erwartet `From == "frieda@beispiel.invalid"`; Dateizeile ohne `antwort_an`), Code-Leser mit Muster `(\d{3}) (\d{3})` in `test_anmeldung.py` (Z. 70, 120, 261, 330), `test_konten.py` (Z. 39, 150, 154, 410), `test_kalender.py` (Z. 241), `test_seite.py` (Z. 595, 656), `test_warteliste.py` (Z. 94, 202, 220, 225, 242), `engine/tests/test_texte.py` (Parität, Ausnahmelisten), `engine/tests/test_betrieb.py` (Modullisten in `deploy.sh`).

## Verhalten

### Versandweg (`engine/konten.py`)

1. **Signatur.** `mail_senden(an, betreff, text, antwort_an=None, html=None)`. Alle bisherigen Aufrufe bleiben gültig und verändern sich nicht.
2. **Mehrteiler.** Mit `html` besteht die Nachricht aus `text/plain` (Standardteil, `set_content(text)`) und `text/html` (`add_alternative(html, subtype="html")`), in dieser Reihenfolge (Text zuerst, HTML als bevorzugte Alternative). Ohne `html` bleibt sie eine reine Textmail wie bisher.
3. **Anzeigename.** Im SMTP-Zweig wird `From` mit `email.utils.formataddr(("Frieda", adresse))` gesetzt. `adresse` ist der Adressteil von `FR_ABSENDER` (`email.utils.parseaddr`); steht dort schon `Name <adresse>`, wird der Name durch „Frieda“ ersetzt, nie doppelt gestellt. Enthält `FR_ABSENDER` einen Zeilenumbruch oder liefert `parseaddr` keine Adresse mit „@“, gibt es keinen Anzeigenamen und keine Fehlbildung des Kopfes: Es wird `KontoFehler("konto.fehler.mail_nicht_eingerichtet")` geworfen (kein Versand mit einem Absender, den die Konfiguration nicht hergibt). Reply-To, To und Subject bleiben wie bisher.
4. **`FR_MAIL_DATEI`.** Die JSON-Zeile bleibt ohne `html` byte-gleich wie bisher (`an`, `betreff`, `text`, bei `antwort_an` dieses Feld). Nur wenn `html` gesetzt ist, kommt das Feld `html` dazu, nach `text` und vor `antwort_an`. Ein Feld `von` kommt nicht dazu.
5. **Fehlerverhalten.** Wie bisher: nicht eingerichtet oder SMTP-Fehler → `KontoFehler("konto.fehler.mail_nicht_eingerichtet")` bzw. `konto.fehler.mail_fehlgeschlagen`; der Code bleibt in der Datenbank wie bisher.

### Rahmen (`engine/mailrahmen.py`, neu)

6. **Aufbau.** Reine Funktionen ohne Datenbank und ohne Netz. Das Modul importiert `texte` und `instanz`, **nicht** `anmeldung` und nicht `konten`. Aufruf aus `konten.py`: `mailrahmen.code_mail(sprache, zweck, code, minuten, link)` liefert `(betreff, text, html)`; `link` ist `None` oder die fertige Adresse (siehe Punkt 11). Der Fuß wird von `mailrahmen.fuss(sprache, basis)` aus der übergebenen Basisadresse und den Betreiberwerten gebaut: `konten.py` reicht `basis()` als Argument weiter (kein zweites Lesen von `FR_BASIS`, eine Quelle). Eine Basis gilt nur als gesetzt, wenn sie mit `http://` oder `https://` beginnt; jede andere wird wie eine fehlende behandelt (für Fuß-Links und den Link zur Code-Eingabe gleich).
7. **Betreff.** Code vorn, ohne Leerzeichen im Code (kopierbar), Wortlaut aus `mail.code.betreff_anmelden` bzw. `mail.code.betreff_adresse` mit `{code}` am Anfang; der Betreff enthält keine Zeilenumbrüche. Der Code erscheint in Betreff, Text und HTML ohne Leerzeichen (sechs Ziffern).
8. **Text-Teil (vollständig).** Der Text-Teil ist allein lesbar und enthält: Titel, den Code, die Gültigkeit (`mail.code.zeile_eingabe` mit `CODE_MINUTEN`, heute 10 Minuten), bei `zweck == "anmelden"` und gesetztem `FR_BASIS` den Link, den Sicherheitshinweis (`mail.code.sicher_titel` und `mail.code.sicher_text`: „Hast du keinen Code angefordert, kannst du diese Mail einfach löschen“) und den Fuß (Punkt 10). Kein Markup, keine Bild- oder HTML-Reste.
9. **HTML-Teil.** Ein vollständiges Dokument mit `lang` der Mailsprache und `<meta charset="utf-8">`, `<meta name="color-scheme" content="light dark">` und `<meta name="supported-color-schemes" content="light dark">`. Gestaltung nur über Tabellen-Layout und **Inline-Stile**; zusätzlich ein einziger `<style>`-Block, der ausschließlich `@media (prefers-color-scheme: dark)` für Dunkelmodus enthält (Lesbarkeit auch ohne diesen Block, wenn ein Client ihn verwirft). Der Code steht groß (etwa 32 px), in Festbreitenschrift mit Zeichenabstand, in einer eigenen Zelle und ohne Leerzeichen, sodass ein Doppelklick ihn markiert. Der Vorschautext (`mail.code.vorschau`) steht als verstecktes Vorschaufeld am Anfang des Bodys. **Verboten:** `<img>`, `<link>`, `<script>`, `<iframe>`, `<form>`, `url(`, `@import`, `@font-face`, Webschriften, jede externe Ressource, jedes Zählpixel; Adressen erscheinen nur in `href` der erlaubten Links. Alle eingesetzten Werte (Code, Titel, Betreibername, Anschrift, Adressen, Texte) gehen durch `html.escape(…, quote=True)`; Anschrift mit Zeilenumbrüchen wird je Zeile mit `<br>` gesetzt, nachdem jede Zeile escaped wurde.
10. **Fuß (Text und HTML).** Er besteht aus:
    - dem Grund der Mail (`mail.fuss.grund`: sie kam, weil jemand mit dieser Adresse einen Code für Frieda angefordert hat),
    - den Betreiberangaben: `FR_BETREIBER_NAME` und `FR_BETREIBER_ANSCHRIFT` (jeweils `instanz.wert(...)`, getrimmt; leer oder nicht gesetzt zählt als fehlend). Fehlt ein Wert oder fehlen beide, steht der Fuß ohne diese Angabe da, ohne Platzhalter, ohne halbe Zeile und ohne Fehler,
    - den Hinweisen auf Impressum und Datenschutz (`mail.fuss.impressum`, `mail.fuss.datenschutz`): mit gesetzter, gültiger Basis (`http(s)`, siehe Punkt 6) als Links `basis()/impressum` und `basis()/datenschutz` (im HTML `href`, im Text die ausgeschriebene Adresse), ohne `FR_BASIS` nur das Wort ohne Link. Impressum und Datenschutz haben ihre Heimat auf der Seite (ADR-0003); die Mail wiederholt sie nicht, sie verweist nur.
11. **Link zur Code-Eingabe.** Nur bei `zweck == "anmelden"` und gesetztem `FR_BASIS`: `basis()/anmelden?schritt=code&email=<Adresse>` (URL-kodiert wie bisher, im HTML zusätzlich escaped), ohne Code. **Der Code steht nie in einem Link** (Protokolle, Verläufe, Weiterleitungen). Bei `zweck == "adresse"` oder ohne `FR_BASIS` gibt es keinen Link und kein Schaltflächenelement; der Text `mail.code.zeile_link` entfällt dann ganz. Ein `FR_BASIS`, das nicht mit `http://` oder `https://` beginnt, ergibt keinen Link (keine `javascript:`- oder anderen Schemata).
12. **Texte.** Alle sichtbaren Wörter stehen im Katalog (ADR-0006), nie im Code. Text- und HTML-Teil verwenden dieselben Schlüssel. Überarbeitet: `mail.code.betreff_anmelden`, `mail.code.betreff_adresse` (Code vorn, ohne Leerzeichen), `mail.code.zeile_code`, `mail.code.zeile_eingabe`, `mail.code.zeile_link`. Neu: `mail.code.titel_anmelden`, `mail.code.titel_adresse`, `mail.code.vorschau`, `mail.code.sicher_titel`, `mail.code.sicher_text`, `mail.fuss.grund`, `mail.fuss.impressum`, `mail.fuss.datenschutz`. Der alte Schlüssel `mail.code.zeile_loeschen` geht in `mail.code.sicher_text` über (kein toter Schlüssel bleibt). Der verbindliche Wortlaut wird beim Bauen im Katalog festgelegt, de und en sinngleich; Beispiele: Betreff „{code} ist dein Frieda-Code“ / „{code} is your Frieda code“. Die Texte sind **zur Freigabe** nach „Erst zeigen, dann bauen“ (#436): Sie folgen dem vom Product Owner am 12.11.2026 freigegebenen Entwurf „So einbauen“; weil dieser nicht mehr abrufbar ist, zeigt Claude den Wortlaut (de, en) und das Aussehen vor dem Ausliefern als Entwurf (Artefakt mit erfundenen Daten) und liefert erst nach Bestätigung aus.

### Code-Mail (`code_anfordern`)

13. **Ablauf.** `code_anfordern` erzeugt Code, Hash, Gültigkeit und Begrenzungen unverändert; erst der Teil nach dem Eintragen (bisher Z. 348–356) ruft `mailrahmen.code_mail(...)` auf und dann `mail_senden(e, betreff, text, html=html)`. Die Antwort für bekannte und unbekannte Adressen, die stille Tagesgrenze (`still`) und alle Fehler bleiben unverändert.
14. **Genau eine Mail** je Code-Anforderung, mit `To` nur der angefragten Adresse; kein BCC, kein zweiter Versand.
15. **Andere Mails unverändert.** Betreiber-Meldung, Warteliste, Freigabe, Einladung und Reise löschen rufen `mail_senden` weiter ohne `html` auf: reine Textmails, Inhalt wie bisher. Sie bekommen durch Punkt 3 den Anzeigenamen „Frieda“ im Absender (eine Änderung am Absender-Kopf, nicht am Inhalt); Reply-To der Betreiber-Meldung bleibt.

## Was darf sich nicht ändern

- `FR_MAIL_DATEI`-Zeilen ohne `html`: byte-gleich wie bisher; in `test_mail_senden_antwort_an_smtp` bleibt der Teil zur Dateizeile unverändert, nur die `From`-Erwartung des SMTP-Spions wird auf `Frieda <frieda@beispiel.invalid>` umgestellt (gewollte Folge von Punkt 3).
- Code-Erzeugung, Gültigkeit, Begrenzungen, Einlösen, „stille“ Antworten und der Rückgabewert von `code_anfordern`.
- Wortlaut und Inhalt der Mails Warteliste, Freigabe, Einladung, Reise löschen, Betreiber-Meldung.
- `neu.py`, Reisedaten, Reisespeicher, Schreibweg; beide Beispielreisen.
- Impressum und Datenschutz bleiben ihre Seiten (ADR-0003); die Mail führt kein zweites Impressum.

## Acceptance Criteria

Mail-Tests lesen `FR_MAIL_DATEI` oder einen SMTP-Spion; Texte über `meldet(...)`/`text(...)` aus `conftest.py`, keine kopierten Sätze.

- **AC-1 (Mehrteiler):** Gegeben `mail_senden(an, betreff, text, html=h)` im SMTP-Zweig (Spion für `smtplib.SMTP`), dann ist die gesendete Nachricht `multipart/alternative` mit genau zwei Teilen: zuerst `text/plain` mit dem Text, dann `text/html` mit `h`. Ohne `html` ist sie eine einteilige `text/plain`-Nachricht wie bisher.
- **AC-2 (Anzeigename):** Gegeben `FR_ABSENDER=frieda@beispiel.invalid`, dann lautet `From` `Frieda <frieda@beispiel.invalid>`. Gegeben `FR_ABSENDER=Andere Person <frieda@beispiel.invalid>`, dann lautet `From` ebenfalls genau `Frieda <frieda@beispiel.invalid>` (kein doppelter Name, nur ein „Frieda“). Gegeben ein `FR_ABSENDER` mit Zeilenumbruch (`a@b.invalid\nBcc: x@y.invalid`) oder ohne gültige Adresse, dann wird nichts gesendet und `KontoFehler("konto.fehler.mail_nicht_eingerichtet")` geworfen; kein Kopf `Bcc` entsteht.
- **AC-3 (Dateizeile ohne HTML unverändert):** Gegeben `FR_MAIL_DATEI` und `mail_senden` ohne `html`, dann ist die geschriebene Zeile byte-gleich mit der bisherigen (`an`, `betreff`, `text`, bei `antwort_an` zusätzlich dieses Feld); die Dateizeilen-Prüfung in `test_mail_senden_antwort_an_smtp` bleibt unverändert (nur dessen `From`-Erwartung ändert sich, siehe AC-2).
- **AC-4 (Dateizeile mit HTML):** Gegeben `mail_senden` mit `html`, dann enthält die Zeile zusätzlich das Feld `html` mit genau diesem Wert, die übrigen Felder wie ohne `html`.
- **AC-5 (Betreff mit Code vorn):** Gegeben eine Code-Anforderung (`zweck=anmelden`, de und en), dann beginnt der Betreff mit den sechs Ziffern des Codes ohne Leerzeichen (zuerst Ziffern, dann das übrige Wort), enthält keinen Zeilenumbruch und denselben Code wie Text- und HTML-Teil. Für `zweck=adresse` gilt dasselbe mit dem Betreff `mail.code.betreff_adresse`.
- **AC-6 (Code nie in einem Link):** Gegeben `FR_BASIS=https://frieda.beispiel.invalid`, dann steht der Code in keiner Adresse (`href` und ausgeschriebene Links in Text und HTML) und in keinem Betreff-Link; der Link der Anmeldung enthält `schritt=code` und `email=`, aber keine Ziffernfolge des Codes.
- **AC-7 (Link nur bei Anmelden mit Basis):** Gegeben `zweck=anmelden` und gesetztes `FR_BASIS`, dann enthalten Text und HTML den Link zur Code-Eingabe. Gegeben `zweck=adresse`, dann enthält die Mail diesen Link nicht (und keinen `href` auf `/anmelden`). Gegeben kein `FR_BASIS`, dann gibt es keinen Link der Code-Eingabe und keinen `href` im HTML, der Text enthält nicht `mail.code.zeile_link`. Gegeben ein `FR_BASIS` mit anderem Schema als `http`/`https`, dann entsteht kein Link.
- **AC-8 (Text-Teil vollständig):** Gegeben die Mail wird nur als Text gelesen, dann enthält sie in de und en: den Code, die Gültigkeit mit „10“ aus `CODE_MINUTEN` (Test setzt zusätzlich einen anderen Wert und sieht ihn in der Mail), den Sicherheitshinweis (`mail.code.sicher_text`), den Grund (`mail.fuss.grund`) und die Wörter für Impressum und Datenschutz; kein `<`-Markup und keinen Platzhalter `{…}`.
- **AC-9 (HTML-Gerüst):** Gegeben der HTML-Teil, dann enthält er `<table`, `color-scheme` (Meta) und `prefers-color-scheme: dark`; sein einziger `<style>`-Block enthält nur diesen Dunkelmodus (keine sonstigen Regeln außerhalb von `@media`); alle übrigen Gestaltung steht in `style="…"`. Er enthält keinen der Marker `<img`, `<link`, `<script`, `<iframe`, `<form`, `url(`, `@import`, `@font-face`; jede in ihm vorkommende Adresse steht in einem `href` auf `basis()`; es gibt keine Adresse mit `http` außerhalb von `href`.
- **AC-10 (Escaping):** Gegeben `FR_BETREIBER_NAME` und `FR_BETREIBER_ANSCHRIFT` mit `<script>alert(1)</script> & "x"` und eine Adresse `a+<b>@beispiel.invalid`, dann steht im HTML nur die escapte Form (`&lt;script&gt;`, `&amp;`, `&quot;`), nie das rohe `<script>`; im Text-Teil erscheinen die Werte unverändert als Text; Zeilen der Anschrift sind mit `<br>` getrennt, jede einzeln escaped.
- **AC-11 (Fuß mit Betreiberwerten):** Gegeben `FR_BETREIBER_NAME` und `FR_BETREIBER_ANSCHRIFT` gesetzt und `FR_BASIS` gesetzt, dann enthalten Text und HTML den Grund, den Betreibernamen, die Anschrift, `basis()/impressum` und `basis()/datenschutz` (im HTML als `href`).
- **AC-12 (Fuß ohne Betreiberwerte, ohne Basis):** Gegeben `FR_BETREIBER_NAME` und `FR_BETREIBER_ANSCHRIFT` nicht gesetzt oder nur Leerraum, dann ist die Mail trotzdem gültig und vollständig: der Fuß enthält den Grund und die Wörter für Impressum und Datenschutz, aber keine leere Zeile mit Platzhalter, kein „None“ und keine Zeichenfolge `{`; es gibt keinen Fehler. Gegeben nur eine der beiden Angaben gesetzt, dann steht genau diese da. Gegeben kein `FR_BASIS`, dann stehen Impressum und Datenschutz als Wörter ohne Link und ohne Adresse.
- **AC-13 (de und en, nur Katalog):** Gegeben `sprache` `de` und `en`, dann stammen alle sichtbaren Wörter der Mail aus dem Katalog der Sprache (Test vergleicht mit `text(...)`); jeder Schlüssel aus Punkt 12 steht in `texte_de.py` und `texte_en.py` mit gleichen Platzhaltern; `engine/tests/test_texte.py` (Parität, Literal-Test, Pseudo-Sprache) ist grün, die Ausnahmelisten sind nicht länger.
- **AC-14 (Keine Zirkelbezüge):** `import engine.mailrahmen` gelingt ohne dass `anmeldung` geladen wird (Test: `sys.modules` vor und nach dem Import in einem frischen Prozess); `mailrahmen.py` enthält weder `import anmeldung` noch `import konten`.
- **AC-15 (Andere Mails unverändert):** Gegeben Betreiber-Meldung, Warteliste, Freigabe, Einladung und Reise löschen, dann sind ihre `FR_MAIL_DATEI`-Zeilen (Betreff, Text, `antwort_an`) byte-gleich wie vor der Änderung und tragen kein Feld `html`.
- **AC-16 (Eine Mail je Anforderung):** Gegeben eine Code-Anforderung, dann enthält `FR_MAIL_DATEI` genau eine Zeile mit `an` gleich der Adresse; die stille Tagesgrenze (`still`) und die Antwort für unbekannte Adressen verhalten sich wie vorher (keine Mail bei `still`, gleiche Rückgabe).
- **AC-17 (Deploy-Listen):** `mailrahmen.py` steht in `RM_MODULE`, `KN_MODULE`, `SB_MODULE` und `PS_MODULE` von `betrieb/deploy.sh` (Test in `engine/tests/test_betrieb.py` für neue eigene Module bleibt grün).
- **AC-18 (Doku):** `docs/design.md` beschreibt den „Mail-Rahmen“ (Mail ist keine Seite und der Rahmen kein Atomic-Design-Baustein der Seite, siehe ADR-Abschnitt; kein Eintrag in `GRUNDFORMEN`, Impressum und Datenschutz bleiben auf ihrer Seite und werden nur verlinkt); `docs/betrieb.md` beschreibt das Format von `FR_MAIL_DATEI` (Felder `an`, `betreff`, `text`, optional `html`, `antwort_an`) und den Mailabschnitt. Der Mail-Rahmen steht in `docs/design.md` in einem eigenen Abschnitt **außerhalb** der Ebenen-Tabelle (`| Ebene | Bausteine` bis `## Ontologie und Bausteine`) und ohne Eintrag im Kopfkommentar von `engine/vorlage.html`: Er ist ein Python-Baustein der Mail, keine Funktion der Seite; `engine/tests/test_design.py` (Abgleich Vorlage ↔ Tabelle, „fremde“ Namen in der Tabelle sind verboten) bleibt dadurch unverändert grün.
- **AC-19 (Abnahme auf der Instanz):** Nach dem Ausliefern, mit einem eigenen Testkonto der Instanz (nie echte Reisen, nie fremde Adressen): (a) Eine Anmeldung per E-Mail liefert eine Mail mit Absender „Frieda“, Betreff mit Code vorn und gut lesbarem Code; (b) sie wird in mindestens einem Client im Hell- und im Dunkelmodus geprüft (Zeichen lesbar, Fuß vorhanden); (c) Impressum- und Datenschutz-Link führen zu den Seiten der Instanz; (d) die Zustellung landet im Posteingang (nicht im Spam) bei mindestens einem Testpostfach bei Gmail und einem bei Stalwart; (e) die Mail als Text allein gelesen ist vollständig. Ergebnis als Kommentar in #532; das Issue wird erst danach geschlossen.

## Test Plan

**Reihenfolge:** Vor GREEN zeigt Claude dem Product Owner den Wortlaut (de, en) und das Aussehen als Entwurf (Artefakt mit erfundenen Daten) und trägt erst den bestätigten Wortlaut in den Katalog ein (#436, Punkt 12).

Datei `engine/tests/test_mailrahmen.py` (neu). Nur erfundene Daten: Adressen `ida@beispiel.invalid`, `karl@beispiel.invalid`, Basis `https://frieda.beispiel.invalid`, erfundener Betreiber. Mails über `FR_MAIL_DATEI` oder einen SMTP-Spion (Muster `test_mail_senden_antwort_an_smtp`), eigene Datenbank je Test, Sprachen `de` und `en` parametrisiert. Die RED-Phase schreibt die Tests vor der Umsetzung.

Versandweg:
- [ ] `test_mehrteiler_text_und_html_smtp`: GIVEN `html` gesetzt, WHEN der SMTP-Spion die Nachricht bekommt, THEN `multipart/alternative`, erster Teil `text/plain`, zweiter `text/html`; ohne `html` einteilig. (AC-1)
- [ ] `test_absender_anzeigename_frieda` (parametrisiert: nur Adresse, `Name <adresse>`): GIVEN verschiedene gültige `FR_ABSENDER`, THEN `From` genau `Frieda <adresse>`, nie doppelt. (AC-2)
- [ ] `test_absender_ohne_header_injektion` (parametrisiert: Zeilenumbruch mit `Bcc:`, ohne „@“, leer): GIVEN ein solcher `FR_ABSENDER`, WHEN `mail_senden`, THEN `KontoFehler("konto.fehler.mail_nicht_eingerichtet")`, kein Versand, kein `Bcc` im Spion. (AC-2)
- [ ] `test_dateizeile_ohne_html_unveraendert`: GIVEN `FR_MAIL_DATEI`, WHEN ohne `html` (mit und ohne `antwort_an`), THEN die Zeile ist byte-gleich der bisherigen; der Dateizeilen-Teil von `test_mail_senden_antwort_an_smtp` bleibt unverändert. (AC-3)
- [ ] `test_dateizeile_mit_html`: GIVEN `html` gesetzt, THEN Feld `html` vorhanden, übrige Felder gleich. (AC-4)

Code-Mail:
- [ ] `test_betreff_code_vorn_ohne_leerzeichen` (de/en, Zweck `anmelden` und `adresse`): GIVEN `code_anfordern`, THEN Betreff beginnt mit sechs Ziffern, keine Leerzeichen im Code, Code gleich in Betreff, Text und HTML. (AC-5)
- [ ] `test_code_nie_in_einem_link`: GIVEN `FR_BASIS`, THEN kein `href`, keine ausgeschriebene Adresse enthält den Code. (AC-6)
- [ ] `test_link_nur_bei_anmelden_mit_basis`: Anmelden mit Basis → Link; Adresse → kein Link; ohne Basis → kein Link und kein `href`; Schema ungleich `http(s)` → kein Link. (AC-7)
- [ ] `test_text_teil_vollstaendig`: Code, Gültigkeit (mit geändertem `CODE_MINUTEN`), Sicherheitshinweis, Grund, Fuß, kein Markup, kein `{`. (AC-8)
- [ ] `test_eine_mail_je_anforderung_und_still`: genau eine Zeile; `still` ohne Mail, gleiche Rückgabe. (AC-16)

HTML und Fuß:
- [ ] `test_html_geruest_dunkelmodus_inline_stile`: `<table`, Meta `color-scheme`, `prefers-color-scheme: dark`, `<style>` nur mit diesem Block, Gestaltung inline. (AC-9)
- [ ] `test_html_ohne_bild_pixel_externe_ressourcen`: Liste der verbotenen Marker fehlt; jede Adresse nur in `href` auf die Basis. (AC-9)
- [ ] `test_html_alles_escaped`: Betreibername, Anschrift, Adresse mit `<script>`, `&`, `"`; THEN nur Escape-Form im HTML, unverändert im Text, `<br>` je Anschriftszeile. (AC-10)
- [ ] `test_fuss_mit_betreiberwerten_und_links`: Name, Anschrift, `basis()/impressum`, `basis()/datenschutz`. (AC-11)
- [ ] `test_fuss_ohne_betreiberwerte_und_ohne_basis` (parametrisiert: nichts, nur Name, nur Anschrift, Leerraum, ohne Basis): gültig, ohne Platzhalter und `None`, kein Fehler, ohne Basis keine Links. (AC-12)

Texte, Module, Deploy:
- [ ] `test_mail_texte_vollstaendig_de_en`: alle Schlüssel aus Punkt 12 in `texte.SPRACHEN`, gleiche Platzhalter; sichtbare Wörter der Mail stammen aus dem Katalog; `test_texte.py` und die Ausnahmelisten bleiben grün. (AC-13)
- [ ] `test_mailrahmen_importiert_anmeldung_nicht`: frischer Prozess (`python -I -c …`), `anmeldung` nicht in `sys.modules`; Quelltext ohne `import anmeldung`/`konten`. (AC-14)
- [ ] `test_andere_mails_unveraendert` (Betreiber-Meldung, Warteliste, Freigabe, Einladung, Reise löschen): Betreff und Text wie vorher, kein Feld `html`. (AC-15)
- [ ] `test_doku_mailrahmen_und_mail_datei`: `docs/design.md` enthält einen Abschnitt „Mail-Rahmen“ außerhalb der Ebenen-Tabelle; `docs/betrieb.md` nennt die Felder `an`, `betreff`, `text`, `html`, `antwort_an` von `FR_MAIL_DATEI`; `test_design.py` bleibt grün. (AC-18)
- [ ] `test_deploy_listen_enthalten_mailrahmen`: `mailrahmen.py` in `RM_MODULE`, `KN_MODULE`, `SB_MODULE`, `PS_MODULE`; der bestehende Test in `test_betrieb.py` bleibt grün. (AC-17)

Anpassung bestehender Tests (Betreff-Erwartung ändert sich, Schlüssel und Link bleiben):
- [ ] `engine/tests/test_anmeldung.py` (Z. 329): Erwartung `startswith("Frieda: your code")` und Text „Your code for Frieda“ wird durch die Erwartung „Betreff beginnt mit den sechs Ziffern des Codes“ und `meldet(...)` mit den neuen Schlüsseln ersetzt.
- [ ] `engine/tests/test_konten.py` (Z. 50, 149, 333, 413): Erwartungen an den alten Betreff („Frieda: dein Code“, „Frieda: your code“) und Text auf den neuen Wortlaut und den Code vorn im Betreff umstellen; Z. 333 prüft zusätzlich weiter Verbindung, STARTTLS und Login.
- [ ] `engine/tests/test_betreiber_meldung.py` (Z. 301): nur die `From`-Erwartung auf `Frieda <frieda@beispiel.invalid>`; Reply-To und Dateizeile unverändert.
- [ ] `engine/tests/test_anmeldung.py` Z. 626: Der Filter `"Dein Code" in z` erkennt Code-Mails künftig über den Betreff (`meldet(...)` mit `mail.code.betreff_anmelden`) statt über den alten Wortlaut, damit der Test nicht leer läuft.
- [ ] Falls die Umsetzung weitere Stellen findet (`NNN NNN` mit Leerzeichen, „dein Code“), dort ebenso nur die Erwartung an den neuen Wortlaut und den Code ohne Leerzeichen anpassen; nichts anderes ändern. Kein Test wird abgeschwächt, nur umgestellt.
- [ ] Code-Leser mit Muster `(\d{3}) (\d{3})` (Suche 19.11.2026): `test_anmeldung.py` Z. 70, 120, 261, 330; `test_konten.py` Z. 39, 150, 154, 410; `test_kalender.py` Z. 241; `test_seite.py` Z. 595, 656; `test_warteliste.py` Z. 94, 202, 220, 225, 242. Sie lesen künftig den Code als sechs zusammenhängende Ziffern (ein gemeinsames Muster, möglichst eine Hilfsfunktion in `conftest.py`); sonst ändert sich an diesen Tests nichts.

Gesamt:
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n 3` grün (Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`).

**Instanz-Tests:** Mailtext und Betreff der Code-Mail ändern sich, und `FR_MAIL_DATEI` kann ein neues Feld bekommen; beides nutzen die einbindenden Instanzen (Anleitung im privaten Reisen-Repo der Instanz, CLAUDE.md). Vor dem Vorspulen auf `main` laufen daher die Tests der einbindenden Instanzen mit dem Branch, weil die öffentliche CI private Tests nicht ausführt. Danach Abnahme nach AC-19 auf der Instanz.

## Dokumentation

- `docs/design.md`: eigener Abschnitt „Mail-Rahmen“ außerhalb der Ebenen-Tabelle (kein Baustein der Seite, siehe ADR-Abschnitt): Aufbau (Kopf mit Name, Titel, Code-Zelle, Gültigkeit, Link, Sicherheitshinweis, Fuß), Regeln (Tabellen, Inline-Stile, nur Dunkelmodus im Stilblock, keine Bilder und Pixel, alles escaped). Die Mail ist keine Seite: kein Eintrag in `GRUNDFORMEN`; Impressum und Datenschutz haben ihre Heimat auf der Seite, die Mail verlinkt nur (ADR-0003).
- `docs/betrieb.md`: Mailabschnitt (Absender „Frieda“, Mehrteiler, Betreiberangaben im Fuß aus `FR_BETREIBER_*`, fehlende Werte lassen den Fuß kürzer, nie fehlerhaft) und Format der Zeilen in `FR_MAIL_DATEI` (`an`, `betreff`, `text`, optional `html`, `antwort_an`).
- `docs/konten.md`: nur, wenn dort der Mailtext beschrieben ist; sonst unverändert.
- Kopf von `engine/mailrahmen.py` beschreibt Zweck und Grenzen (keine Datenbank, kein Import von `anmeldung`).

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/konten.py` (`mail_senden`, `basis`, `code_anfordern`, `CODE_MINUTEN`) | Modul, geändert | Mehrteiler, Absender, Code-Mail |
| `engine/mailrahmen.py` | Modul, neu | HTML-Gerüst und Textfuß |
| `mail_senden(..., antwort_an=...)` (Stand #530, Reply-To) | Signatur, übernommen | bleibt unverändert; `html` kommt als weiterer optionaler Parameter dazu |
| `engine/instanz.py` (`wert`) | Modul, nur gelesen | `FR_BETREIBER_NAME`, `FR_BETREIBER_ANSCHRIFT` |
| `engine/texte.py` (nur gelesen), `texte_de.py`, `texte_en.py` (geändert) | Katalog | Schlüssel `mail.code.*`, `mail.fuss.*` |
| `engine/anmeldung.py` (`BETREIBER`, `RECHT`) | Modul, nur Vorbild | Namen der Einstellungen und Pfade; nicht importiert |
| `betrieb/deploy.sh` | Betriebsskript, geändert | `mailrahmen.py` in `RM_MODULE`, `KN_MODULE`, `SB_MODULE`, `PS_MODULE` |
| Python-Standardbibliothek (`email.message`, `email.utils`, `html`) | Bibliothek | Mehrteiler, Absender, Escape; keine neue Abhängigkeit |
| Einstellungen `FR_BASIS`, `FR_ABSENDER`, `FR_SMTP_*`, `FR_BETREIBER_*` | Konfiguration | Links, Absender, Fuß |
| SMTP-Dienst der Instanz (Resend) und Stalwart | Fremd | Zustellung; Domain-Einstellungen (SPF, DKIM, DMARC) in henemm-infra#433 |
| Private Reisen-Repo der Instanz | Betrieb | Instanz-Tests vor dem Vorspulen |

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue; bestehend gelten ADR-0001, ADR-0002, ADR-0003 und ADR-0006.
- **Rationale:** Die Mail gehört zu Konten und Betrieb, nicht zur Reise-Ontologie (ADR-0001: keine Grundform, kein Merkmal, keine KI, nichts Reisespezifisches). Das Gerüst ist **kein Atomic-Design-Baustein** im Sinn von ADR-0002: ADR-0002 und die Pflicht „vier Stellen“ (Kopfkommentar der Vorlage, Stile der Ebene, Bausteinseite, `docs/design.md`) gelten für Funktionen der Seite in `engine/vorlage.html`; der Mail-Rahmen ist Python, wird in keinem Browser der Seite gezeichnet, nutzt keine Stile der Vorlage (Mail-Clients verlangen Inline-Stile) und kann auf der Bausteinseite nicht erscheinen. Er bekommt deshalb einen eigenen Abschnitt in `docs/design.md` außerhalb der Ebenen-Tabelle. Er ist auch keine Grundform (ADR-0003: Impressum und Datenschutz behalten ihre eine Heimat, die Mail verlinkt nur). Alle sichtbaren Texte stehen im Katalog (ADR-0006). Es wird eine Standardbibliothek statt Eigenbau genutzt (kein Vendor-Eintrag nötig). Die ADRs werden nicht geändert.

**Prüfstelle ADR-0001 (zehn Fragen, im PR zu beantworten):** keine Grundform und kein Merkmal berührt (Frage zu Arten und Merkmalen entfällt); nichts Reisespezifisches in der Engine; beide Beispielreisen unberührt (die Mail kennt keine Reise); keine eigene KI; Texte im Katalog; Einstellungen kommen aus der Instanz, nicht aus dem Code; kein neues Datenformat der Reisen, daher keine Umstellung in `nachziehen`; Daten bleiben bei Konto und Betrieb.

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konten.py` | MODIFY | `mail_senden(..., html=None)` mit Mehrteiler, Anzeigename „Frieda“ (`formataddr`, `parseaddr`), `FR_MAIL_DATEI` mit `html` nur wenn gesetzt; `code_anfordern` baut Text und HTML über `mailrahmen` |
| `engine/mailrahmen.py` | CREATE | HTML-Gerüst und Textfuß, reine Funktionen, alles escaped, kein Bild, kein Pixel |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | Schlüssel `mail.code.*` und `mail.fuss.*` (überarbeitet und neu), `zeile_loeschen` geht in `sicher_text` über |
| `betrieb/deploy.sh` | MODIFY | `mailrahmen.py` in `RM_MODULE`, `KN_MODULE`, `SB_MODULE`, `PS_MODULE` |
| `engine/tests/test_mailrahmen.py` | CREATE | Nachweistests nach Test Plan |
| `engine/tests/test_anmeldung.py`, `test_konten.py`, `test_kalender.py`, `test_seite.py`, `test_warteliste.py`, `test_betreiber_meldung.py`, `test_texte.py` (nur falls Ausnahmelisten kürzer werden), ggf. `conftest.py` | MODIFY | Betreff- und Code-Erwartungen auf den neuen Wortlaut umstellen |
| `docs/design.md`, `docs/betrieb.md` | MODIFY | Baustein „Mail-Rahmen“, Format von `FR_MAIL_DATEI`, Mailabschnitt |

### Estimated Changes

- Files: 14 sicher (2 neu: `mailrahmen.py`, `test_mailrahmen.py`), dazu höchstens `conftest.py` und `test_texte.py`; davon 5 Produktivdateien (`konten.py`, `mailrahmen.py`, `texte_de.py`, `texte_en.py`, `deploy.sh`).
- LoC: etwa +250 Produktivcode und Texte, +300 Tests und Doku, −10. Risiko mittel: einziger Anmeldeweg; der Text-Teil muss vollständig bleiben, Instanz-Tests prüfen Mailtexte. Bleibt in einem Issue; braucht das Gerüst mehr als 150 Zeilen, wird in zwei Schritte geteilt (zuerst Gerüst und `mail_senden`, dann Texte und Code-Mail).

## Risiken

- **Einziger Anmeldeweg:** Ein Fehler in der Code-Mail sperrt alle Anmeldungen. Gegenmittel: Text-Teil vollständig und unabhängig vom HTML, Tests auf beide Teile, Abnahme nach AC-19 direkt nach dem Ausliefern.
- **Zustellbarkeit:** HTML-Mails landen eher im Spam, wenn sie Bilder, externe Ressourcen oder nur HTML enthalten. Gegenmittel: Mehrteiler mit Text, keine Bilder und Ressourcen, Prüfung bei Gmail und Stalwart (AC-19 d); Domain-Einstellungen in henemm-infra#433.
- **Instanz-Tests:** Betreff und Mailtext ändern sich; private Tests der Instanz können darauf prüfen. Gegenmittel: Instanz-Tests mit dem Branch vor dem Vorspulen.
- **Wortlaut ohne Vorlage:** Das freigegebene Artefakt „So einbauen“ ist nicht mehr abrufbar. Gegenmittel: Der neue Wortlaut (de, en) wird dem Product Owner vor dem Ausliefern als Entwurf gezeigt (Regel „Erst zeigen, dann bauen“, #436).

## Definition of Done

- [ ] Alle Punkte des Test Plans sind in `engine/tests/test_mailrahmen.py` umgesetzt und grün; `engine/tests` insgesamt grün (Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`).
- [ ] Alle Acceptance Criteria durch Tests oder den Abnahmeschritt auf der Instanz belegt.
- [ ] Texte in allen Sprachen (de, en) vollständig; Ausnahmelisten in `test_texte.py` nicht länger.
- [ ] Der Wortlaut (de, en) und das Aussehen der Mail wurden dem Product Owner vor dem Ausliefern als Entwurf (Artefakt mit erfundenen Daten) gezeigt und von ihm bestätigt, weil der Entwurf „So einbauen“ (12.11.2026) nicht mehr abrufbar ist.
- [ ] Die Tests der einbindenden Instanzen laufen mit dem Branch, vor dem Vorspulen auf `main`.
- [ ] Doku ergänzt (`docs/design.md`, `docs/betrieb.md`); `deploy.sh` enthält `mailrahmen.py`.
- [ ] Nach dem Ausliefern: Abnahme nach AC-19 auf der Instanz; Ergebnis im Issue #532, Issue erst danach schließen.
- [ ] Die Prüfstelle (zehn Fragen, ADR-0001) ist im PR beantwortet.

## Changelog

- 2026-11-19: Prüfrunden: Absender-Fehlerfälle getrennt, Risiken, Doku-Test (AC-18, außerhalb der Ebenen-Tabelle), vollständige Liste der betroffenen Tests (Code-Leser, `From`-Erwartung in `test_betreiber_meldung.py`).
- 2026-11-19: Entwurf der Spec (v1.0) aus Kontext, Plan (Kommentar in #532) und Freigabe des Product Owners vom 12.11.2026; Festlegungen: Code ohne Leerzeichen in Betreff, Text und HTML; Dunkelmodus nur als `prefers-color-scheme` im einzigen Stilblock; Absender immer „Frieda“, ungültiger oder mehrzeiliger `FR_ABSENDER` führt zu „nicht eingerichtet“; andere Mails bleiben Text-Mails und bekommen nur den Absendernamen.
