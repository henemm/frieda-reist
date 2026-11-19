# Context: Anmeldecode-Mail professionell gestalten (#532)

## Request Summary
Die Mail mit dem Anmeldecode (und dem Code für eine neue Adresse) bekommt einen HTML-Teil neben dem Text, den Anzeigenamen
„Frieda“ im Absender und einen Fuß mit Impressum und Datenschutz. Maßgeblich: Plan im Kommentar vom 12.11.2026 10:49 UTC und
Freigabe des Product Owners vom 12.11.2026 11:07 UTC (Entwurf „So einbauen“, Deutsch und Englisch). Das Artefakt ist nicht mehr
abrufbar. Weitere Mails (Warteliste, Freigabe, Einladung, Reise löschen, Betreiber-Meldung) bekommen den Rahmen später, nicht in diesem Issue.

## Ausgangslage (Ist)
- `engine/konten.py` `mail_senden(an, betreff, text, antwort_an=None)` (Z. 264): einziger Versandweg. Mit `FR_MAIL_DATEI` eine JSON-Zeile
  `{an, betreff, text[, antwort_an]}` an die Datei anhängen; sonst SMTP (`FR_SMTP_HOST/PORT/USER/PASS`, STARTTLS), `From` = `FR_ABSENDER` roh
  (ohne Anzeigenamen), `set_content(text)` (nur Text), Fehler → `KontoFehler("konto.fehler.mail_fehlgeschlagen")`.
- `basis()` (Z. 260) = `FR_BASIS` ohne Schlusszeichen `/`.
- `code_anfordern` (Z. 311–356): Code `NNN NNN` (Leerzeichen in der Mitte), Zeilen `mail.code.zeile_code`, `zeile_eingabe` (mit `CODE_MINUTEN`=10),
  nur bei `zweck=="anmelden"` und gesetztem `basis()` der Link `…/anmelden?schritt=code&email=…` (ohne Code), `zeile_loeschen`;
  Betreff `mail.code.betreff_anmelden` bzw. `betreff_adresse` mit `{code}` (lesbar, mit Leerzeichen).
- Weitere Aufrufer von `mail_senden` (nur Text, bleiben unverändert): `konten.py` Z. 922 (Betreiber-Meldung, mit `antwort_an`), 1013 (Warteliste),
  1081 (Freigabe), 1535 (Einladung); `anmeldung.py` Z. 764 (Reise löschen). `mail_konfiguriert()` (Z. 973) prüft `FR_MAIL_DATEI` oder SMTP+Absender.
- `FR_BETREIBER_NAME/_ANSCHRIFT/_KONTAKT` (`betrieb/einstellungen.beispiel` Z. 163–165): gelesen in `anmeldung.py` über `BETREIBER` (Z. 1237) und
  `instanz.wert(...)` für Impressum (`/impressum`) und Datenschutz (`/datenschutz`, Pfade in `RECHT`, Z. 1236). Fehlt ein Wert, zeigt das Impressum
  einen Hinweis „nicht angegeben“; das Mailfuß-Verhalten muss damit umgehen (Fuß ohne Anschrift statt Fehler; Links bleiben).
- Texte: `mail.code.*` in `engine/texte_de.py` Z. 1166–1171 und `texte_en.py` (nur diese zwei Sprachen; Pseudo-Sprache der Tests und
  `test_texte.py` verlangen Parität, Ausnahmelisten nur kürzer).
- Tests der Mails: `engine/tests/test_anmeldung.py` (Fixture setzt `FR_MAIL_DATEI`), `test_konten.py`, `test_warteliste.py`, `test_betreiber_meldung.py`
  (`test_mail_senden_antwort_an_smtp`, Z. 273–310: SMTP-Mock und Dateizeile ohne `antwort_an` = „dieselbe Zeile wie bisher“; darf nicht brechen).

## Delta (Soll)
1. `mail_senden(an, betreff, text, antwort_an=None, html=None)`: optionaler HTML-Teil per `add_alternative(html, subtype="html")`; Absender als
   `formataddr(("Frieda", adresse))` (Anzeigename „Frieda“; ist `FR_ABSENDER` schon `Name <adresse>`, nicht doppelt; Adresse aus `parseaddr`).
   `FR_MAIL_DATEI`: Zeile bekommt `html` nur, wenn gesetzt (ohne HTML bleibt die Zeile byte-gleich wie bisher), dazu `von` (Anzeigename+Adresse) nur wenn der Test es braucht.
2. Neues Modul `engine/mailrahmen.py`: baut aus Titel, Vorschautext, Code, Gültigkeit, Link, Sicherheitshinweis und Fuß ein HTML-Gerüst
   (Tabellen-Layout, nur Inline-Stile, `<meta name="color-scheme" content="light dark">` und `prefers-color-scheme`-Dunkelmodus, kein Bild, kein Zählpixel,
   alle Werte mit `html.escape`, Links nur `http(s)` aus `basis()`). Text- und HTML-Teil kommen aus denselben Textschlüsseln.
3. `code_anfordern`: Betreff mit Code vorn, ohne Leerzeichen im Code (kopierbar), HTML und Text neu; Link nur bei `zweck=="anmelden"` und `basis()`.
4. Fuß (Text und HTML): Grund der Mail (`mail.fuss.grund`), Impressum (Name, Anschrift aus `FR_BETREIBER_*`, soweit gesetzt) und Links
   `basis()/impressum`, `basis()/datenschutz` (`mail.fuss.impressum`, `mail.fuss.datenschutz`); ohne `basis()` kein Link, nur Text.
5. Neue/überarbeitete Texte in `texte_de.py` und `texte_en.py`: `mail.code.betreff_*` (Code vorn), `mail.code.zeile_*`, neu `mail.code.titel_anmelden`,
   `titel_adresse`, `vorschau`, `sicher_titel`, `sicher_text`, `mail.fuss.grund`, `mail.fuss.impressum`, `mail.fuss.datenschutz`. Sichtbare Texte nie im Code.
6. Neues Modul in `betrieb/deploy.sh`: `mailrahmen.py` in alle Modullisten, die `konten.py` laden (`RM_MODULE`, `KN_MODULE`, `SB_MODULE`, `PS_MODULE`);
   ein Test prüft das bereits für neue eigene Module.
7. Dokumentation: Baustein „Mail-Rahmen“ in `docs/design.md` (Mail ist keine Seite: nur Gerüst, Ebene „Organismus“ ohne Eintrag in `GRUNDFORMEN`; Heimat von
   Impressum/Datenschutz bleibt die Seite, die Mail hat nur Links, ADR-0003), `docs/betrieb.md` (Mailabschnitt, `FR_MAIL_DATEI`-Format), `docs/konten.md` falls Mailtext beschrieben.

## Related Files
| File | Relevanz |
|------|----------|
| engine/konten.py | `mail_senden`, `basis`, `code_anfordern`; Aufrufer-Liste oben |
| engine/mailrahmen.py (neu) | HTML-Gerüst und Textfuß, reine Funktionen ohne Datenbank |
| engine/anmeldung.py | `BETREIBER`, `RECHT`, Betreiberwerte (ggf. kleine Hilfsfunktion in `instanz.py`/`mailrahmen.py`, damit konten.py nicht anmeldung.py importiert: Zirkel vermeiden) |
| engine/instanz.py | `wert("FR_BETREIBER_…")` |
| engine/texte_de.py, texte_en.py | alle Mailtexte |
| betrieb/deploy.sh | Modullisten |
| docs/design.md, docs/betrieb.md | Baustein und Betrieb |
| engine/tests/test_mailrahmen.py (neu) | Mehrteiler, Absendername, Escape, Dunkelmodus, kein Bild/Pixel, Fuß mit/ohne Betreiberwerte, de/en |
| engine/tests/test_anmeldung.py, test_betreiber_meldung.py, test_texte.py | bestehende Erwartungen (Betreff, Dateizeile) anpassen bzw. unverändert halten |

## Existing Patterns
- Mailtests über `FR_MAIL_DATEI` (JSON-Zeilen) und SMTP-Mock (`test_betreiber_meldung.py` Z. 273 ff.).
- Betreiberwerte aus `FR_BETREIBER_*` über `instanz.wert`, nie im Code; Texte nur im Katalog (ADR-0006).
- Rechtsseiten haben genau eine Heimat (ADR-0003): die Mail verweist nur.

## Dependencies
- Upstream: Textkatalog, `FR_BASIS`, `FR_ABSENDER`, `FR_SMTP_*`, `FR_BETREIBER_*`.
- Downstream: alle Anmeldungen (Web, Konnektor-Anmeldung per OAuth, Adresswechsel), Zustellbarkeit bei Resend/Stalwart (henemm-infra#433), Instanz-Tests im privaten
  Reisen-Repo (Mailtexte und Betreff ändern sich: vor dem Vorspulen mit dem Branch laufen lassen).

## Risks & Considerations
- Betreff und Text prüfen Tests/Instanz-Tests womöglich auf „dein Code“ oder `NNN NNN`; Code vorn im Betreff ohne Leerzeichen ändert das.
- Der Code gehört weiter nie in Links (Protokolle); Link bleibt ohne Code.
- HTML-Injektion: Betreiberwerte und Adresse sind Konfiguration/Benutzereingabe, immer escapen; Header-Injektion über Anzeigename/Adresse (kein Zeilenumbruch).
- Mail-Clients: Dunkelmodus nur als Zusatz, Lesbarkeit auch ohne CSS; Text-Teil bleibt vollständig lesbar (Code, Gültigkeit, Hinweis, Fuß).
- Zählpixel/Bilder ausdrücklich ausgeschlossen (Datenschutz, Zustellbarkeit).
- Antwort-Kopf `Reply-To` und Betreiber-Meldungen unverändert halten.
- Instanzspezifisches (Betreibername, Anschrift) nur aus Einstellungen; ohne Werte bleibt der Fuß gültig.
- Mailkontingent unverändert (eine Mail je Code, kein zweiter Versand).

## Scoping
- Produktivdateien: konten.py, mailrahmen.py (neu), texte_de.py, texte_en.py, deploy.sh (5, grenzwertig; HTML-Gerüst zwingend eigene Datei, konten.py ist ohnehin groß), plus Tests und Doku.
- Geschätzt +230 bis +280 Zeilen Produktivcode und Texte, Tests zusätzlich. Bleibt in einem Issue: Aufteilung nur, wenn das Gerüst mehr als 150 Zeilen braucht
  (dann erst Gerüst + `mail_senden`, danach Texte und Code-Mail).
- Keine neuen Abhängigkeiten (`email.utils`, `html` aus der Standardbibliothek). Keine Format-Änderung der Reisedaten → kein `nachziehen`.
- Vorgehen nach Repo-Konvention: Spec `docs/specs/betrieb/anmeldecode-mail-532.md`, Briefing, RED-Nachweistests, GREEN, Adversary, Instanz-Tests, dann ausliefern.

## Analysis

### Type
Feature (Änderung an bestehendem Versand), freigegeben vom Product Owner am 12.11.2026 (#532). Das freigegebene Artefakt ist nicht mehr abrufbar; maßgeblich ist der Plan im Issue-Kommentar vom 12.11.2026 10:49 UTC.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/konten.py | MODIFY | `mail_senden(..., html=None)`: Mehrteiler per `add_alternative`, Absender mit Anzeigename „Frieda“ (`formataddr`), `FR_MAIL_DATEI` schreibt `html` nur wenn gesetzt; `code_anfordern` baut Text- und HTML-Teil |
| engine/mailrahmen.py | CREATE | HTML-Gerüst (Tabellen, Inline-Stile, `color-scheme`, kein Bild, kein Zählpixel), Fuß mit Betreiberwerten und Links auf Impressum/Datenschutz, alles escaped |
| engine/texte_de.py, engine/texte_en.py | MODIFY | neue und überarbeitete Schlüssel `mail.code.*`, `mail.fuss.*` |
| betrieb/deploy.sh | MODIFY | `mailrahmen.py` in die Modullisten neben `konten.py` |
| engine/tests/test_mailrahmen.py | CREATE | Nachweistests |
| docs/design.md, docs/betrieb.md | MODIFY | Baustein „Mail-Rahmen“, Format von `FR_MAIL_DATEI` |

### Scope Assessment
- Files: 5 produktiv (+ Tests, Doku)
- Estimated LoC: +250/-10
- Risk Level: MEDIUM (einziger Anmeldeweg; Text-Teil muss vollständig bleiben; Instanz-Tests prüfen Mailtexte und müssen vor dem Ausliefern mit dem Branch laufen)

### Technical Approach
Bibliothek statt Eigenbau: `EmailMessage.set_content(text)` + `add_alternative(html, subtype="html")`, `email.utils.formataddr`, `html.escape`. Text- und HTML-Teil aus denselben Textschlüsseln. Code ohne Leerzeichen vorn im Betreff und groß im HTML, nie in einem Link. Andere Mails (Warteliste, Freigabe, Einladung, Betreiber, Löschen) bleiben unverändert (Freigabe: Rahmen später).

### Dependencies
`konten.py` wird von Rückmeldedienst, Konnektor, Seitenbau und Push geladen (deploy.sh-Listen RM/KN/SB/PS); `mailrahmen.py` importiert nur `texte` und `instanz`, nicht `anmeldung` (Zirkel).

### Open Questions
- keine
