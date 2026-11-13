# Mini-Spec: Zweiter Einlieferungsweg für Mails (#561)

Entscheidung des Product Owners vom 13.11.2026 (henemm-infra#444): Lehnt der Mailanbieter ab (Tageskontingent erschöpft, Störung), wird dieselbe Mail über einen zweiten Weg der Instanz verschickt. Dass ein Teil davon beim Empfänger im Spam landet, ist in Kauf genommen.

## Was ändert sich
- `engine/konten.py` (`mail_senden`): Scheitert die Einlieferung bei `FR_SMTP_HOST` (`OSError`, `smtplib.SMTPException`) und ist `FR_SMTP_ERSATZ_HOST` gesetzt, folgt ein zweiter Versuch dort (`FR_SMTP_ERSATZ_PORT`, Vorgabe 587, STARTTLS, Anmeldung mit `FR_SMTP_ERSATZ_USER`/`_PASS`, falls gesetzt). Absender, Empfänger, Inhalt und `Reply-To` bleiben gleich.
- Gelingt der zweite Weg, steht auf stderr genau eine Zeile `mail: first route failed (<Fehlerklasse>), sent via FR_SMTP_ERSATZ_HOST`, ohne Adresse und Inhalt. Kein Alarm (Meldeweg nur für Ausfälle, #446); die Infrastruktur zählt die Nutzung des zweiten Wegs selbst.
- Die Einlieferung selbst steht in der Hilfsfunktion `_einliefern(m, praefix)`.
- `docs/konten.md`: Zeile für `FR_SMTP_ERSATZ_*` in der Tabelle „Betrieb“.

## Was darf sich nicht ändern
- Ohne `FR_SMTP_ERSATZ_HOST` verhält sich `mail_senden` wie bisher, auch im Fehlerfall (`konto.fehler.mail_fehlgeschlagen`).
- Nimmt der erste Weg an, wird der zweite nicht berührt.
- `FR_MAIL_DATEI` hat weiter Vorrang vor beiden Wegen.
- Keine neuen sichtbaren Texte; scheitern beide Wege, gilt `konto.fehler.mail_fehlgeschlagen`.

## Manuelle Test-Schritte
1. Instanz mit falschem `FR_SMTP_PASS` und gültigem `FR_SMTP_ERSATZ_*`: Anmeldecode anfordern, die Mail kommt an, im Protokoll steht die Warnzeile.
2. Ohne `FR_SMTP_ERSATZ_HOST`: gleiche Störung, die Seite meldet wie bisher, dass die Mail nicht verschickt werden konnte.

## Inline-Test
- [x] `test_mail_ersatzweg_wenn_erster_ablehnt`: zweiter Weg mit eigener Anmeldung, gleicher Absender und Reply-To, Warnzeile ohne Adresse und Inhalt.
- [x] `test_mail_ersatzweg_unbenutzt_wenn_erster_annimmt`
- [x] `test_mail_ohne_ersatzweg_fehler_wie_bisher`
- [x] `test_mail_beide_wege_scheitern`
