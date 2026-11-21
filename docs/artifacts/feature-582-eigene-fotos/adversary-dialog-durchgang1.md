# Adversary Dialog — feature-582-eigene-fotos
Spec: docs/specs/oberflaeche/bilder-582-eigene-fotos.md
Datum: 2026-11-21 14:55

## Checkliste
- [x] **AC-1 (V1, V6):** Given eine angemeldete Person mit Rolle mitwirkend oder organisator / When sie auf der Reiseseite ein Foto wählt / Then wird es angenommen; Given Gast, Nicht-Mitglied, keine Anmeldung oder fremder Origin / Then wird es abgelehnt, und die Rolle wird über `rolle_aktuell` frisch geprüft.
- [x] **AC-2 (V2, V5):** Given JPEG, PNG, WebP oder HEIC bis 12 MB / When hochgeladen / Then wird es angenommen; Given eine größere, falsche, beschädigte oder zu pixelreiche Datei / Then kommt die passende Ablehnung (V17), der Dienst bleibt stabil.
- [x] **AC-3 (V3):** Given ein Foto mit GPS und Kameradaten / When es gespeichert ist / Then enthalten die Fassungen keine Metadaten, die Drehung ist angewendet und das Original ist nirgends gespeichert.
- [x] **AC-4 (V4):** Given eine Reise an `bilder.max_anzahl` oder `bilder.max_mb` / When ein weiteres Foto kommt / Then wird mit „Grenze erreicht“ abgelehnt, und `bilder.max_mb` ist in `reise.yaml` einstellbar (Vorgabe 150).
- [x] **AC-5 (V7):** Given ein gespeichertes eigenes Foto / When die Seite gebaut wird / Then steht der Eintrag mit Quelle `eigen`, Besitzkennung und der Nennung „Foto: <Name>“.
- [x] **AC-6 (V8):** Given jemand will ein Foto hinzufügen / When das Formular erscheint / Then steht der Hinweis zu Personen auf Fotos vorher da, ohne Haken und ohne Frage nach der Urheberschaft.
- [x] **AC-7 (V9):** Given ein gescheitertes Speichern / When der Vorgang endet / Then bleiben keine verwaisten Fassungen zurück; vorhandene Waisen verschwinden beim nächsten Hochladen.
- [x] **AC-8 (V10, V18):** Given die Beispielreise und das Stadtwochenende / When Fotos hochgeladen werden und die Seiten gebaut sind / Then funktionieren beide fehlerfrei, und alte Einträge in `plan/bilder.yaml` bleiben gültig.
- [x] **AC-9 (V19):** Given `pillow-heif` und der Foto-Block in nginx / When das Veröffentlichen läuft / Then sind Bibliothek (Lizenz, Hashes), Glibc-Prüfung, Deploy-Liste und der nginx-Block ohne Handschritt vorhanden.
- [x] **AC-10 (V11):** Given ein eigenes Foto / When die hochladende Person oder eine Organisator:in es entfernt / Then geschieht es; Given eine andere mitwirkende Person oder ein Token / Then wird es abgelehnt.
- [ ] **AC-11 (V12):** Given das Löschen / When `bild_entfernen` läuft / Then sind beide Fassungen in allen Versionen, in der Ablage, im Export und auf der Seite weg, nur die zwei Pfade des Bildes sind betroffen, das Löschprotokoll hat den Eintrag, `pruefen()` ist grün.
- [x] **AC-12 (V12):** Given zwei Uploads mit gleichem Inhalt / When einer gelöscht wird / Then bleibt der andere unversehrt.
- [ ] **AC-13 (V13):** Given ein entferntes Foto / When der Verlauf gelesen wird / Then steht „Foto entfernt“ mit Datum und Person ohne Bild, die ID wird nie neu vergeben.
- [x] **AC-14 (V14):** Given der Dialog zum Löschen / When er erscheint / Then enthält er die Zusage nach der Regel aus #381: sofort entfernt, Sicherungen höchstens 30 Tage, fremde Kopien nicht zurückholbar.
- [x] **AC-15 (V15):** Given ein gelöschtes Bild im Cache eines Geräts / When die Seite wieder geladen wird / Then ist es aus dem Cache entfernt.
- [x] **AC-16 (V16):** Given eine Person ab mitwirkend / When Frieda das Werkzeug ausführt / Then kommt ein Link, der 30 Minuten gilt, höchstens 10 Fotos erlaubt, an Reise und Person gebunden ist und in `konten.db` nur als Hash steht.
- [x] **AC-17 (V16):** Given ein Token mit abgelaufener Zeit, erschöpftem Zähler, falscher Reise oder Person / When hochgeladen wird / Then kommt immer dieselbe Ablehnung „Link abgelaufen“.
- [x] **AC-18 (V16):** Given ein gültiger Token, aber inzwischen herabgestufte Rolle / When hochgeladen wird / Then wird abgelehnt.
- [x] **AC-19 (V16):** Given ein Token / When etwas anderes als Hochladen versucht wird (Löschen, Lesen) / Then wird es abgewiesen.
- [x] **AC-20 (V16):** Given die Link-Seite / When sie geladen wird / Then trägt sie eigene CSP und `Referrer-Policy: no-referrer`, enthält keinen geheimen Seitenlink und lädt keine fremden Ressourcen.
- [x] **AC-21 (V16):** Given ein gelöschtes Konto / When aufgeräumt wird / Then sind seine Tokens entfernt.
- [x] **AC-22 (V17):** Given die Spec-Freigabe / When gebaut wird / Then folgen Wortlaut und Gestaltung dem freigegebenen Entwurf; die Tabelle V17 stimmt mit `texte_de.py` überein, alle Sprachen sind vollständig (`test_texte.py`).
- [x] **AC-23 (V20):** Given die Pakete sind ausgeliefert / When die Doku geprüft wird / Then sind ADR-0009 (dritte Ausnahme), ADR-0001 (Verlauf zu Frage 7), `docs/konnektor.md`, `docs/betrieb.md` und `docs/design.md` nachgeführt.
- [ ] **AC-24:** Given die Pakete / When vor dem Vorspulen die Tests der einbindenden Instanz mit dem Branch laufen / Then sind sie grün; die volle Testsuite ist ohne echte Reisen grün.

## Dialog

### Runde 1
**Adversary:** Ich gehe von "kaputt" aus und prüfe zuerst die Eingangsseite (Rolle, Format, Metadaten, Bomben), dann den Löschweg.

Methode: gezielter Testlauf (691 bestanden, 0 fehlgeschlagen, 0 übersprungen; Ausgabe docs/artifacts/feature-582-eigene-fotos/adversary-test-output.txt), eigene Sonden gegen `eigen_umwandeln` (PNG 1x1, 49 MP, 64 MP, 400 MP, 1x4000, 4000x1, RGBA, JPEG mit GPS/Kamera/ICC und Drehung 6, WebP mit EXIF und XMP, animiertes WebP/APNG, GIF, SVG, leer, abgeschnittenes JPEG, JPEG mit Anhang, genau 12 MB und 12 MB + 1, falsches HEIC, 30000x1000 und 65000x900 JPEG, echtes HEIC mit Drehung, 81-MP-HEIC).
Ergebnis der Sonden: 64 MP, 400 MP und das 81-MP-HEIC werden mit `bild.abgelehnt.format` abgelehnt (Dienst stabil, das HEIC nach 5 s); 12 MB + 1 gibt `foto_zu_gross`; weder GPS, Kameraname, EXIF, ICC noch der XMP-Text stehen in den WebP-Fassungen; Drehung 6 liefert 200x300 (JPEG und HEIC); GIF, SVG, leer, abgeschnitten und falsches HEIC werden abgelehnt.

Code reference: engine/bilder.py:393 (`eigen_umwandeln`: Größe vor Verkleinerung, Magic Bytes, Unterprozess mit Zeitgrenze, alle Fehler gleich abgelehnt); engine/bilder.py:367 (`umwandeln_hier`: Pillow-Warnung wird zum Fehler, `exif_transpose`, `im.info` geleert, `exif=b""`, `xmp=b""`).

Finding:
  ID: F001
  Severity: HIGH
  Category: spec_violation
  Code reference: engine/schreiben.py:5388
  Description: `bild_aendern` (Aktion "bild", ab Rolle mitwirkend) prüft nicht, ob der Eintrag `status: entfernt` hat. Sonde mit der Beispielreise (Ida organisator): Foto hochladen, Bildunterschrift setzen, mit `bild_entfernen` entfernen, danach `bild_aendern` mit `wiederherstellen: true` ergibt die Antwort "restored: it appears again"; der Eintrag steht auf `status: aktiv` ohne `dateien`, der Verlaufseintrag "Foto entfernt" ist weg, `entfernt:` bleibt als Rest im Eintrag. Danach schreibt `bildunterschrift: "neuer Text"` wieder Text auf den entfernten Eintrag, danach macht `zurueckziehen: true` daraus `status: zurueckgezogen`. Der Bau warnt nur (bauen.py bilder_daten, "ohne Datei kein Bild"), lehnt nicht ab.
  Spec requirement: AC-13 / V13 — "Foto entfernt" mit Datum und Person bleibt im Verlauf; Dateien, Titel, Bildunterschrift und Alt-Text sind geleert.
  Conflict: Jede mitwirkende Person (nicht nur der Besitzer) kann über das Konnektor-Werkzeug `bild_aendern` den Verlaufseintrag eines entfernten Fotos auflösen, in einen kaputten aktiven oder zurückgezogenen Eintrag verwandeln und Texte neu eintragen. "Entfernt" ist damit kein stabiler Endzustand.
  Remediation: In `bild_aendern` vor jeder Änderung `if bilder.entfernt(b): raise Ablehnung(...)` (neuer Katalogschlüssel in allen Sprachen) und ein Test dafür.

Finding:
  ID: F002
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/schreiben.py:5710
  Description: `bild_endgueltig_entfernen` läuft erst NACH dem festgeschriebenen Vorgang (schreiben.py:5668-5672). `konten.bild_loeschung_protokollieren` steht außerhalb des `try`. Wirft es (SQLite gesperrt, Datenbank nicht lesbar) oder stirbt der Prozess zwischen Vorgang und Protokoll, ist das Foto im neuesten Stand weg, die Blobs der älteren Versionen und der Ablage bleiben, und es gibt keinen Protokolleintrag, den `waechter.bildloeschungen_nachholen` nachholen könnte. Der Aufrufer bekommt zusätzlich einen 500 für einen schon festgeschriebenen Vorgang.
  Spec requirement: AC-11 / V12 — Fassungen in allen Versionen und in der Ablage weg; Zusage "sofort entfernt".
  Conflict: Kein Wiederanlauf für dieses Fenster; die Datenschutzzusage kann ohne sichtbaren Fehler unerfüllt bleiben.
  Remediation: Protokolleintrag vor dem Vorgang schreiben oder den Wächter `status: entfernt` ohne Protokolleintrag erkennen und leeren lassen; Fehler des Protokolls nicht nach dem Vorgang als Abbruch durchreichen.

Finding:
  ID: F003
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/waechter.py:493
  Description: `_bild_eintrag_entfernen` und `bildloeschungen_nachholen` (waechter.py:526) wählen den Eintrag nur über die ID und prüfen weder `quelle == eigen` noch, dass es dasselbe Foto ist. Wird eine Sicherung zurückgespielt, die älter ist als der Upload (die ID `BI-07` ist dort frei), und danach ein neues Bild mit derselben ID angelegt (Commons oder eigenes), macht der nächste Lauf aus dem neuen, unbeteiligten Bild einen Eintrag "entfernt" und leert dessen Fassungen in allen Versionen (`reisespeicher.bild_entfernen`).
  Spec requirement: AC-11 — nur die zwei Pfade des gelöschten Bildes sind betroffen; AC-13 — die ID wird nie neu vergeben.
  Conflict: Das Löschprotokoll kennt nur (Reise, ID); nach einem Rückspielen vor dem Upload gilt "nie neu vergeben" nicht mehr.
  Remediation: Im Protokoll die Prüfsumme der Fassungen oder das Hinzufüge-Datum mitführen und nur bei Übereinstimmung entfernen; mindestens `quelle == "eigen"` prüfen.

Finding:
  ID: F004
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/texte_de.py:3891
  Description: Der Kopfkommentar jeder `plan/bilder.yaml` (Schlüssel `inhalt.schreiben.bilder_kopf`, de und en, texte_en.py:3889) sagt weiter "gelöscht wird nie, zurückgezogene Bilder bleiben erhalten"; ebenso der Docstring von `bild_aendern` (schreiben.py:5388, "Gelöscht wird nie."). Seit #582 stimmt das für eigene Fotos nicht mehr.
  Spec requirement: AC-23 — Doku nachgeführt.
  Conflict: Widersprüchliche Aussage in jeder gespeicherten Bilderliste.
  Remediation: Text in beiden Sprachen ergänzen: eigene Fotos lassen sich endgültig entfernen.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/rueckmeldungen.py:1637
  Description: Der Link-Weg liest den Body (bis 12 MB, bis 24 MB verworfen) und drosselt erst danach (`_foto_lesen` vor `gedrosselt_je`), nur je Adresse; die Spec nennt Drosselung "je Token und je Adresse". Ungültige Tokens kosten damit Einlesezeit ohne frühe Ablehnung. Der Drosselspeicher `_zeiten` (rueckmeldungen.py:1114) wächst je Schlüssel ohne Aufräumen.
  Spec requirement: Implementation Details P2 — Drosselung je Token und je Adresse.
  Conflict: Teilweise erfüllt (der Zähler von 10 Fotos begrenzt gültige Tokens, nicht die Anfragen mit ungültigen).
  Remediation: Token zuerst mit `hochladelink_pruefen` prüfen, dann den Body lesen; Drosselschlüssel um den Token ergänzen.

**Implementierer:** (keine Antwort im Lauf; der Adversary-Lauf ist einseitig, die Antworten gehören zur Nacharbeit.)

### Runde 2
**Adversary:** Zweiter Durchgang gegen die Zugriffsseite und die Zusagen, einzeln je AC.

AC-1: `_angemeldete_person` verlangt Sitzung und Origin (`wer_ist`: ohne Cookie 401, fremder Origin 403, Nicht-Mitglied 403, das Dienst-Geheimnis zählt nicht), `bild_rolle` fragt `rolle_aktuell` frisch (Rückfall auf den veröffentlichten Stand nur, wenn kein Schreibweg eingerichtet ist; ist er eingerichtet und die Person unbekannt, 503, kein stiller Rückfall); der Schreibweg prüft die Rolle aus `reise.yaml` des aktuellen Stands noch einmal (`wer_pruefen`, Besitz über den Schlüssel `person`, nicht über den Namen).
AC-17/18/19: Token nur als sha256, Ablauf, Zähler (BEGIN IMMEDIATE, Rückgabe bei Fehlern), Bindung an Reise und Person über `konten.mitglied`; DELETE und anderes auf `/hochladen/` landen in `_link` und liefern 404; dort wird weder Cookie noch Dienst-Geheimnis ausgewertet. XSS auf der Link-Seite: alle Werte durch `html.escape`, Skript mit Nonce, `daten_json` mit maskiertem `<`, Ausgabe über `textContent`.
AC-20: CSP `default-src 'none'`, `script-src` und `style-src` mit Nonce, `form-action 'none'`, `frame-ancestors 'none'`, `Referrer-Policy: no-referrer`, keine Adresse der Reiseseite.
AC-15: der Service Worker leert beim Installieren eines neuen Stands alle Bilder unter `medien/bilder/`, die `BILDER_JETZT` nicht mehr nennt, aus allen alten Speichern (`bilderVergessen`); Browsertest bestanden.
AC-11/12: `reisespeicher.bild_entfernen` nur zwei feste Pfade je Reise, parametrisiert, `BEGIN IMMEDIATE`, Blobs nur gelöscht, wenn keine Version irgendeiner Reise verweist; der Quelltext-Test lässt genau drei Nutzer von `_db_ausnahme` zu.

Zusätzlich ohne Befund geprüft: Besitzer leer, dann darf nur eine Organisator:in entfernen; zweites Entfernen wird abgelehnt; die HEIC-Bombe wird im Unterprozess nach 5 s abgelehnt; die Entzugsfolge (Entfernen, Protokoll, Leeren, Verdichten, Neubau) läuft in dieser Reihenfolge; kein sichtbarer Text im Code außerhalb der Kataloge (die Bausteinseite in vorlage.html trägt deutsche Muster-Beschriftungen wie die bisherigen Bausteine).
Offen, nicht belegt (AMBIGUOUS, kein Defekt): Der Schlüssel `besitzer` einer gelöschten Person bliebe wirksam, falls derselbe Personenschlüssel in `reise.yaml` später einer neuen Person vergeben wird; ob Schlüssel je wiederverwendet werden, habe ich nicht abschließend geprüft.

Bekannte, bewusst entschiedene Punkte, als dokumentiert bestätigt: nginx-Blöcke je Instanz als Einmalschritt (docs/betrieb.md "Einmalschritt je Instanz beim Ausliefern von #582", Vorlage betrieb/vorlagen/nginx-hochladen.inc, einrichten.sh); venv-Neubau und Glibc-Prüfung ohne Handschritt (veroeffentlichen.sh `glibc_pruefen` vor dem Bau, Test bestanden); AC-22: die Freigabe des Entwurfs steht aus, der Wortlaut der V17-Tabelle stimmt mit `texte_de.py` überein (alle Zeilen verglichen: Hinweis, Zusage mit "30 Tage", Link-Seite, Ablehnungen), alle Sprachen vollständig (`test_texte.py` grün); AC-24: die Tests der privaten Instanz laufen vor dem Ausliefern, die öffentliche Suite ist im Verdict belegt; der Nachtrag im Wächter (`bildloeschungen_nachholen` setzt den Eintrag zurück) ist geprüft, der Test `test_alte_sicherung_eintrag_wird_wieder_entfernt_und_reise_baut` ist grün, die Lücke steht in F003.

Nebenbefund: `engine/packliste.py` Zeile 139 (Ersatzname der gelöschten Person in `wer` gültig, #647) gehört fachlich nicht zu #582; mit Test (`test_gelöschte_person_in_wer_bleibt_gültig`), unkritisch.

Confirmation:
  AC: AC-1
  Code reference: engine/rueckmeldungen.py:1128
  Evidence: `bild_rolle` nutzt `rolle_aktuell`; `_angemeldete_person` weist ohne Sitzung (401), fremden Origin und Nicht-Mitglieder (403) ab; Tests `test_rueckmeldedienst_nimmt_fotos_nur_von_mitwirkenden_an` und `test_rolle_aus_dem_aktuellen_stand` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/bilder.py:393
  Evidence: Sonden: 12 MB angenommen; 12 MB + 1, GIF, SVG, leer, abgeschnitten, 64-MP- und 400-MP-PNG, 81-MP-HEIC abgelehnt; Dienst stabil; der Rückmeldedienst prüft Größe und Magic Bytes vorher (rueckmeldungen.py:1544).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/bilder.py:367
  Evidence: Keine Metadaten in den Fassungen (EXIF, XMP, GPS, ICC), Drehung angewendet (200x300), das Original läuft nur über die Pipe, `eigen_vorab_schreiben` schreibt nur die Fassungen.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/schreiben.py:5281
  Evidence: `bild_grenze` prüft die Zahl aktiver Bilder und die Bytes mit neuer Fassung gegen `max_mb` (reise.py:58, Vorgabe 150); Test `test_grenze_je_reise_lehnt_ab_und_speichert_nichts` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/bauen.py:503
  Evidence: Nennung "Foto: <Name>" für Quelle `eigen` (bauen.py:515), `besitzer` in `daten.json` (bauen.py:918); `bild_hochladen` setzt quelle, urheber, besitzer (schreiben.py:5413).
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/vorlage.html:1601
  Evidence: `hochladenBlatt` zeigt zuerst `seite.bild.hinweis_personen` und `hinweis_metadaten`, ohne Haken und ohne Frage zur Urheberschaft; Browsertest bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/bilder.py:475
  Evidence: `waisen_aufraeumen` im selben Zug und Rückbau der Fassungen bei einem Fehler in `bild_hochladen` (schreiben.py:5413); Tests `test_waisen_*` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:5413
  Evidence: Die Beispielreise nimmt ein Foto an (Sonde über den Schreibweg), `test_stadtwochenende_nimmt_fotos_an` bestanden; neue Felder sind optional, kein Formatwechsel.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/anmeldung.py:1240
  Evidence: `pillow-heif` in requirements.in und requirements.txt (Hashes) und THIRD_PARTY.md, Glibc-Prüfung in veroeffentlichen.sh vor dem Venv-Bau, bilder.py in RM_MODULE; die nginx-Blöcke je Instanz als dokumentierter Einmalschritt (bewusste Abweichung). Die Datenschutzseite führt den Abschnitt "fotos".
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/schreiben.py:5444
  Evidence: `bild_entfernen` erlaubt nur `besitzer == wer.person` (Schlüssel) oder Organisator:in; `_bild_entfernen` nur angemeldet, der Token-Weg `_link` kennt kein DELETE; Test `test_andere_mitwirkende_person_darf_nicht_entfernen` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/reisespeicher.py:909
  Evidence: `_ablage_aufraeumen` löscht nur Blobs ohne Verweis irgendeiner Version; Test `test_zwei_uploads_mit_gleichem_inhalt_teilen_den_blob` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/texte_de.py:3932
  Evidence: `seite.bild.entfernen_zusage` (de und en) nennt sofortiges Entfernen, 30 Tage Sicherung, fremde Kopien; Dialog `bildEntfernenFragen` (vorlage.html:1638), "Behalten" sendet nichts.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/sw.vorlage.js:72
  Evidence: `bilderVergessen` löscht Bilder, die `BILDER_JETZT` (bauen.py:1642) nicht nennt; Browsertest `test_browser_service_worker_vergisst_geloeschtes_bild` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/konten.py:1298
  Evidence: `hochladelink_anlegen` speichert nur `_hash(token)`, 30 Minuten, 10 Fotos, Reise und Person; das Werkzeug `bild_hochladelink` (konnektor.py:3628) prüft die Rolle frisch; Alias `image_upload_link` (schnittstelle.py:88).
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: engine/rueckmeldungen.py:1637
  Evidence: `_link` liefert für abgelaufen, aufgebraucht, unbekannt und anderes Mitglied immer 410 `hochladen.abgelaufen`; der Zähler läuft über BEGIN IMMEDIATE (konten.py:1332).
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: engine/rueckmeldungen.py:1128
  Evidence: Der Link-POST ruft `bild_rolle` je Foto und gibt den Zähler bei Ablehnung zurück; Test `test_herabgestufte_rolle_mit_gueltigem_token` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: engine/rueckmeldungen.py:1637
  Evidence: Auf `/hochladen/` sind nur GET und POST erlaubt, anderes ergibt 404; `test_token_erlaubt_nur_hochladen` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-20
  Code reference: engine/rueckmeldungen.py:1622
  Evidence: `_seite_senden` setzt CSP mit Nonce und `Referrer-Policy: no-referrer`; keine fremde Ressource, kein Seitenlink.
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: engine/konten.py:643
  Evidence: `loeschen` nimmt `hochladelinks` in die Tabellenliste; `entfernen` (Person) und `loeschung_abschliessen` räumen ebenfalls ab; `test_konto_loeschen_raeumt_tokens_ab` bestanden.
  Status: CONFIRMED

Confirmation:
  AC: AC-22
  Code reference: engine/texte_en.py:3930
  Evidence: Wortlaut der V17-Tabelle stimmt mit `texte_de.py` überein, alle Schlüssel in allen Sprachen (`test_neue_texte_in_allen_sprachen`, `test_wortlaut_folgt_dem_entwurf` bestanden); die Freigabe des Entwurfs steht noch aus (offener Lieferpunkt, kein Defekt).
  Status: CONFIRMED

Confirmation:
  AC: AC-23
  Code reference: engine/schnittstelle.py:88
  Evidence: ADR-0009 (dritte Ausnahme), ADR-0001 (Verlauf), docs/konnektor.md, docs/betrieb.md, docs/design.md nachgeführt; Rest siehe F004.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/reise.py:58
  Evidence: `bild_entfernen` setzt status entfernt, leert Dateien und Texte, die ID bleibt vergeben; aber `bild_aendern` hebt den Zustand wieder auf (F001), das Rückspielen kann die ID neu vergeben (F003).
  Status: DISPROVEN (F001)

Confirmation:
  AC: AC-11
  Code reference: engine/konnektor.py:3628
  Evidence: Kern erfüllt (zwei Pfade, Transaktion, Protokoll, pruefen grün), aber das Protokoll wird erst nach dem Vorgang geschrieben (F002) und ist nicht an das Foto gebunden (F003); der Konnektor gibt nur den Link aus und kennt kein Entfernen.
  Status: AMBIGUOUS (F002, F003)

Confirmation:
  AC: AC-24
  Code reference: engine/packliste.py:139
  Evidence: Die öffentliche Suite ist im Verdict belegt; die Tests der privaten Instanz laufen laut Auftrag erst vor dem Ausliefern und sind nicht geprüft.
  Status: AMBIGUOUS

**Implementierer:** (keine Antwort im Lauf)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: BROKEN
═══════════════════════════════════════
Finding F001: `bild_aendern` lässt Änderungen an einem entfernten eigenen Foto zu (wiederherstellen, Texte, zurückziehen); der Verlaufseintrag "Foto entfernt" geht verloren, der Eintrag wird ein aktiver Eintrag ohne Dateien (AC-13)
  Severity: HIGH
  Evidence: engine/schreiben.py:5388
  Reproduction: Beispielreise, Ida organisator: `bild_hochladen`, `bild_entfernen`, dann `bild_aendern` mit `wiederherstellen: true` (jede mitwirkende Person darf das Werkzeug aufrufen).

Finding F002 (MEDIUM): Löschprotokoll wird erst nach dem festgeschriebenen Vorgang geschrieben, ohne Wiederanlauf (engine/schreiben.py:5710)
Finding F003 (MEDIUM): Wächter-Nachholen prüft weder Quelle noch Identität des Fotos; nach Rückspielen einer älteren Sicherung kann ein neues Bild mit derselben ID geleert werden (engine/waechter.py:493)
Finding F004 (LOW): Kopfkommentar und Docstring sagen noch "gelöscht wird nie" (engine/texte_de.py:3891)
Finding F005 (LOW): Link-Upload liest den Body vor Token-Prüfung, Drosselung nur je Adresse (engine/rueckmeldungen.py:1637)

Tests: gezielt 691 passed, 0 failed, 0 übersprungen (docs/artifacts/feature-582-eigene-fotos/adversary-test-output.txt); volle Suite `pytest -q engine/tests -n auto`: 3438 passed, 0 failed, 0 übersprungen in 1424 s (docs/artifacts/feature-582-eigene-fotos/test-green-output.txt)
Edge cases: Dekompressionsbomben (PNG 64 MP und 400 MP, HEIC 81 MP), Metadaten (JPEG, WebP, HEIC), Drehung, Größengrenze genau 12 MB und +1, Magic Bytes, Token-Wege, Rollen: bis auf F001 bis F005 nichts gebrochen
Regressions: keine in der Suite; Nebenbefund packliste.py (Ersatzname "gelöschte Person", #647) nicht Teil von #582
Checklist: 21/24 CONFIRMED, AC-13 DISPROVEN (F001), AC-11 und AC-24 AMBIGUOUS (F002, F003; private Instanz-Tests laufen erst vor dem Ausliefern)

## Geprüfte Dateien

- sha256:99c9a5b192778626fedd52fbb8df372f3fc3e39b7fe6ae2f4522ffb5da16e852  engine/anmeldung.py
- sha256:8abef87818d00f82c66e34c68b31b9a35859b26280eb35642c5246c6c38956f9  engine/bauen.py
- sha256:0c637f940137414a728a74e894f025af5ae66a7a6a0ad95b74622c67999e8b08  engine/bilder.py
- sha256:8613d744ecd8fed0f830565d875a513b1264c9398a883165ba0a97fd590b9eb0  engine/konnektor.py
- sha256:87f45510b6fe9da3aa40643fe649f13c0f7214673fe96fc2e5b629cb639cbdfb  engine/konten.py
- sha256:876fdc6c735ccb8a8e0d5612e2455d0d1e317b26b8a87efb9b5874046a7dfa9d  engine/packliste.py
- sha256:8953730baaed5fdff089d78e2e13eb560197a3f321b934f82c88e5abadbbbb22  engine/reise.py
- sha256:6bdd206a24354114da1ed1a3213d0b3340d5c6abec337b74e43beba4e87c7cea  engine/reisespeicher.py
- sha256:56152a6e2213d7c553b7d7d0a49acee4b24f9c308f03780c1658aca3b0d6c9db  engine/rueckmeldungen.py
- sha256:8cbd50f28bfa0cde90ec6f2cd62bd107c3a6ac01d26b81c0a2a411aeb3407529  engine/schnittstelle.py
- sha256:3ae33467c1c801fd28341e23e5cb236b81fa19f15da64708097ed807411a243a  engine/schreiben.py
- sha256:4fa7e73af97247e10f589526d9cd46a5865083e550e768b571928a0b416869a7  engine/sw.vorlage.js
- sha256:b93b77e5b1bfe10e6644e0b5223986fce7abc1934cda6c88c8d17ca519c01913  engine/texte_de.py
- sha256:e8da8b744e445a574e5d46d8b4f989f8617d4399fd52be81584eb254146ee4f6  engine/texte_en.py
- sha256:f063f88db8390480710241e4ed716d5f6a83607838a72af4a04bd78ae06fa6a9  engine/vorlage.html
- sha256:795916df7f9e2004bf5e390d078ee0635894d6e1a3d6d43cb820a8f4cc246382  engine/waechter.py

## Prüfbasis

- base: 4515cb678b6bc7d5920a7e1dc3bbf58836f3c133
- blob:8481ce30fd9818d9571e3949449cb1882323a7e9  engine/anmeldung.py
- blob:cc7d2aecb6ac81ea60f6724698d17125dcdfbdbe  engine/bauen.py
- blob:5bfcf47e4a9fd72a0cf5564e39175eebd5e72130  engine/bilder.py
- blob:b98684b3bd58f6c52dcf05542137c0d67bdf863b  engine/konnektor.py
- blob:8d87d2fe818c6bbd508ab2ac79f7b7c64a58f118  engine/konten.py
- blob:60a14e4dae10fa1c4730d2ab7fe9dd72127beef0  engine/packliste.py
- blob:f0e782943c6265265a81ce3970fcabb1c99ef6de  engine/reise.py
- blob:fc7485067ec463473531a3816896ab5b8897a744  engine/reisespeicher.py
- blob:be3d2c64ec3be057ac82709e56b2b9b615b2f6ca  engine/rueckmeldungen.py
- blob:c7abc98ba049fa714aced1ea5de90c9e34ffbcc9  engine/schnittstelle.py
- blob:d65b9cbee8c244e0459c1748fd935111c84d9075  engine/schreiben.py
- blob:3938530d407c411223101c76249017d85acc8f08  engine/sw.vorlage.js
- blob:08d8e73295e3748022c67be24f6b1e62712975f5  engine/texte_de.py
- blob:246bbc95bd607908d71d94a131a4e53932dedb0c  engine/texte_en.py
- blob:4661d3ea20ae49daf911ecdf0e82264403cc102a  engine/vorlage.html
- blob:049ec05f3193db4605a81eb4e4025db570f7d921  engine/waechter.py

## Geprüfte Dateien

- sha256:99c9a5b192778626fedd52fbb8df372f3fc3e39b7fe6ae2f4522ffb5da16e852  engine/anmeldung.py
- sha256:8abef87818d00f82c66e34c68b31b9a35859b26280eb35642c5246c6c38956f9  engine/bauen.py
- sha256:0c637f940137414a728a74e894f025af5ae66a7a6a0ad95b74622c67999e8b08  engine/bilder.py
- sha256:8613d744ecd8fed0f830565d875a513b1264c9398a883165ba0a97fd590b9eb0  engine/konnektor.py
- sha256:87f45510b6fe9da3aa40643fe649f13c0f7214673fe96fc2e5b629cb639cbdfb  engine/konten.py
- sha256:876fdc6c735ccb8a8e0d5612e2455d0d1e317b26b8a87efb9b5874046a7dfa9d  engine/packliste.py
- sha256:8953730baaed5fdff089d78e2e13eb560197a3f321b934f82c88e5abadbbbb22  engine/reise.py
- sha256:6bdd206a24354114da1ed1a3213d0b3340d5c6abec337b74e43beba4e87c7cea  engine/reisespeicher.py
- sha256:56152a6e2213d7c553b7d7d0a49acee4b24f9c308f03780c1658aca3b0d6c9db  engine/rueckmeldungen.py
- sha256:8cbd50f28bfa0cde90ec6f2cd62bd107c3a6ac01d26b81c0a2a411aeb3407529  engine/schnittstelle.py
- sha256:3ae33467c1c801fd28341e23e5cb236b81fa19f15da64708097ed807411a243a  engine/schreiben.py
- sha256:4fa7e73af97247e10f589526d9cd46a5865083e550e768b571928a0b416869a7  engine/sw.vorlage.js
- sha256:b93b77e5b1bfe10e6644e0b5223986fce7abc1934cda6c88c8d17ca519c01913  engine/texte_de.py
- sha256:e8da8b744e445a574e5d46d8b4f989f8617d4399fd52be81584eb254146ee4f6  engine/texte_en.py
- sha256:f063f88db8390480710241e4ed716d5f6a83607838a72af4a04bd78ae06fa6a9  engine/vorlage.html
- sha256:795916df7f9e2004bf5e390d078ee0635894d6e1a3d6d43cb820a8f4cc246382  engine/waechter.py

## Prüfbasis

- base: 4515cb678b6bc7d5920a7e1dc3bbf58836f3c133
- blob:8481ce30fd9818d9571e3949449cb1882323a7e9  engine/anmeldung.py
- blob:cc7d2aecb6ac81ea60f6724698d17125dcdfbdbe  engine/bauen.py
- blob:5bfcf47e4a9fd72a0cf5564e39175eebd5e72130  engine/bilder.py
- blob:b98684b3bd58f6c52dcf05542137c0d67bdf863b  engine/konnektor.py
- blob:8d87d2fe818c6bbd508ab2ac79f7b7c64a58f118  engine/konten.py
- blob:60a14e4dae10fa1c4730d2ab7fe9dd72127beef0  engine/packliste.py
- blob:f0e782943c6265265a81ce3970fcabb1c99ef6de  engine/reise.py
- blob:fc7485067ec463473531a3816896ab5b8897a744  engine/reisespeicher.py
- blob:be3d2c64ec3be057ac82709e56b2b9b615b2f6ca  engine/rueckmeldungen.py
- blob:c7abc98ba049fa714aced1ea5de90c9e34ffbcc9  engine/schnittstelle.py
- blob:d65b9cbee8c244e0459c1748fd935111c84d9075  engine/schreiben.py
- blob:3938530d407c411223101c76249017d85acc8f08  engine/sw.vorlage.js
- blob:08d8e73295e3748022c67be24f6b1e62712975f5  engine/texte_de.py
- blob:246bbc95bd607908d71d94a131a4e53932dedb0c  engine/texte_en.py
- blob:4661d3ea20ae49daf911ecdf0e82264403cc102a  engine/vorlage.html
- blob:049ec05f3193db4605a81eb4e4025db570f7d921  engine/waechter.py
