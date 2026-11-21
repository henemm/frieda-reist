# Adversary Dialog — feature-582-eigene-fotos
Spec: docs/specs/oberflaeche/bilder-582-eigene-fotos.md
Datum: 2026-11-21 16:53

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
- [x] **AC-11 (V12):** Given das Löschen / When `bild_entfernen` läuft / Then sind beide Fassungen in allen Versionen, in der Ablage, im Export und auf der Seite weg, nur die zwei Pfade des Bildes sind betroffen, das Löschprotokoll hat den Eintrag, `pruefen()` ist grün.
- [x] **AC-12 (V12):** Given zwei Uploads mit gleichem Inhalt / When einer gelöscht wird / Then bleibt der andere unversehrt.
- [x] **AC-13 (V13):** Given ein entferntes Foto / When der Verlauf gelesen wird / Then steht „Foto entfernt“ mit Datum und Person ohne Bild, die ID wird nie neu vergeben.
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
- [x] **AC-24:** Given die Pakete / When vor dem Vorspulen die Tests der einbindenden Instanz mit dem Branch laufen / Then sind sie grün; die volle Testsuite ist ohne echte Reisen grün.

## Dialog

Zweiter Durchgang. Tests: `adversary-test-output.txt` (382 passed in den acht Zieldateien), volle Suite `test-green-output.txt` (3453 passed). AC-22 (Freigabe des Entwurfs) und AC-24 (Tests der privaten Instanz) sind bewusst nach dem Ausliefern bzw. außerhalb dieser Phase und kein Defekt; sie bleiben offen in der Checkliste.

### Runde 1
**Adversary:** Nachprüfung F001–F005 am Code, nicht am Bericht.

- F001 behoben: `bild_aendern` lehnt entfernte Fotos vor jeder Änderung ab. Test `test_entferntes_foto_laesst_sich_nicht_mehr_aendern` grün.
- F002 behoben: zweiphasiges Protokoll. Vormerken vor dem Vorgang, bestätigen danach, verwerfen im `except BaseException`; `bild_endgueltig_entfernen` wirft nie. Tests `test_liegengebliebene_vormerkung_ohne_vorgang_schadet_nicht`, `test_fehler_nach_dem_vorgang_ist_kein_abbruch_der_waechter_holt_nach` grün. Alle Leser, die "entfernt" meinen, filtern auf `bestaetigt = 1` (`bild_loeschprotokoll`); die einzigen anderen Verbraucher sind der Wächter und die Konto-Löschung.
- F003 behoben: `_dasselbe_foto` verlangt quelle eigen und passende Prüfsummen. Test `test_sicherung_von_vor_dem_hochladen_neues_bild_gleicher_id_bleibt` grün.
- F004 behoben: Kopfkommentar in DE und EN nennt `bild_entfernen` und „Foto entfernt“.
- F005 behoben: Token wird vor dem Body-Lesen geprüft; Drosselung je Adresse und je Link; `zeiten_aufraeumen` räumt auf. Der Zähler wird erst nach dem Lesen in `hochladelink_nehmen` abgezogen, `hochladelink_pruefen` ändert nichts. Test `test_link_prueft_token_vor_dem_lesen_und_drosselt_je_link_und_adresse` grün.
- Schema-Migration: `db()` ergänzt `pruefsummen`/`bestaetigt` per ALTER; alte Zeilen bekommen `bestaetigt = 1` (gelten weiter). Test `test_alte_protokollzeilen_ohne_neue_spalten_gelten_weiter` grün.
- nginx setzt `X-Real-IP` auf `$remote_addr` (nginx-hochladen.inc Zeile 19), der Header ist also nicht fälschbar; 30 Anfragen je Minute und Adresse genügen für 10 Fotos je Link.

**Implementierer:** Lauf der Zieltests (382 passed) und der vollen Suite (3453 passed) belegt die Punkte.

### Runde 2
**Adversary:** Suche nach Defekten der Nacharbeit.

- Rennen Wächter gegen laufenden Vorgang: Der Wächter verwirft eine unbestätigte Vormerkung, solange der Eintrag noch nicht entfernt ist, auch wenn der Vorgang gerade läuft. Ist der Vorgang danach festgeschrieben, legt `bild_loeschung_bestaetigen` die Zeile per Upsert neu an (Fehlen der Zeile ist ausdrücklich vorgesehen). Kein Datenverlust im Normalfall. Nur wenn zusätzlich auch das Bestätigen scheitert, fehlt die Zeile und der Wächter kann nicht nachholen (F006, LOW, sehr enges Zeitfenster, der Wächter läuft täglich).
- Upsert: `ON CONFLICT ... DO UPDATE` setzt `pruefsummen = excluded.pruefsummen`, und `excluded` enthält schon die Vereinigung aus alter und neuer Menge; keine Summe geht verloren.
- Bestätigen im Wächter ohne Prüfsummen: bewahrt die gespeicherten, da die Menge aus der Zeile gelesen wird.
- Vormerken nach `anwenden_im_ordner`: Ablehnungen (unbekannt, nicht eigen, Recht, schon entfernt) kommen vor der Vormerkung; es entstehen keine Vormerkungen für abgelehnte Aufrufe.
- Drosselspeicher: Schlüssel je Link entstehen nur für POST; Aufräumen höchstens einmal je Minute, Speicher wächst höchstens um die Anfragen einer Minute.
- Token-Prüfung verbraucht den Zähler nicht; gescheiterte Uploads geben ihn zurück (`hochladelink_zurueckgeben`, auf das Maximum gedeckelt).

**Implementierer:** Keine Änderungen nötig außer optional F006.

### Runde 3
**Adversary:** Neue Belege zu AC-22 und AC-24 selbst geprüft.

- AC-22: Der letzte Kommentar mit Freigabe des Oberflächen-Entwurfs in Issue 582 stammt vom Besitzer (authorAssociation OWNER), 21.11.2026. Der Wortlaut-Abgleich V17 gegen texte_de.py lag schon vor. Bewertung: erfüllt.
- AC-24: instanz-test-output.txt zeigt 17 passed, 1 failed. Der Fehler ist test_einstellungen_wie_auf_dem_server mit FR_WURZEL is missing aus gemeinsam.sh; der Diff von betrieb/gemeinsam.sh ist leer, die Datei ist also nicht von 582 verändert; die Gegenprobe ohne 582 zeigt denselben Fehler (laut Koordinator, im Issue 582 dokumentiert, eigenes Issue in der Instanz). Bewertung: für 582 erfüllt, der Fehler ist vorbestehend und nicht verursacht. Er bleibt als eigenes Issue offen.

**Implementierer:** Belege nachgereicht.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`); keine Tabelle angehängt, keine verdächtigen Zeilen. Zur Vollständigkeit: Schreibstelle der Vormerkung ist `konten.bild_loeschung_vormerken`; Bedingung davor: `bild_entfernen` hat Besitz oder Rolle, Quelle eigen und „nicht schon entfernt“ geprüft. Test für diesen Weg: `test_liegengebliebene_vormerkung_ohne_vorgang_schadet_nicht` und `test_werkzeug_entfernt_foto_verlauf_bleibt`.

## Findings und Bestätigungen

Finding:
  ID: F006
  Severity: LOW
  Category: edge_case
  Code reference: engine/waechter.py:557
  Description: Der Wächter verwirft eine unbestätigte Vormerkung, auch wenn der zugehörige Vorgang noch läuft.
  Spec requirement: AC-11 — das Löschprotokoll hat den Eintrag
  Conflict: Scheitert danach zusätzlich das Bestätigen (engine/schreiben.py:5740), fehlt die Zeile und das Nachholen entfällt. Der Normalfall ist durch den Upsert (engine/konten.py:1323) abgedeckt.
  Remediation: Vormerkungen nur verwerfen, wenn sie älter als eine Frist sind (Zeitstempel in der Zeile).

Confirmation:
  AC: AC-1
  Code reference: engine/rueckmeldungen.py:1667
  Evidence: Link-Upload prüft Mitgliedschaft frisch und Rolle über `bild_rolle`; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/bilder.py:74
  Evidence: Größen- und Pixelgrenzen vor der Umwandlung; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/bilder.py:24
  Evidence: Fassungen als WebP ohne Metadaten, Original nie gespeichert (Tests grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/reise.py:57
  Evidence: `VORGABEN_BILDER` hat `max_mb` 150, einstellbar über reise.yaml.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/bauen.py:503
  Evidence: Quelle eigen zeigt nur den Namen, „Foto: <Name>“.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/anmeldung.py:1240
  Evidence: Datenschutzabschnitt „fotos“ ergänzt; Hinweis vor dem Formular in der Vorlage, test_texte.py grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/schreiben.py:5417
  Evidence: `bild_hochladen` räumt Waisen früherer Vorgänge im selben Zug auf; Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/bauen.py:515
  Evidence: Bau nennt „Foto: <Name>“ und Verlauf; Tests für Beispielreise und Stadtwochenende grün, alte Einträge in plan/bilder.yaml gelten weiter.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/konnektor.py:3249
  Evidence: nginx-Block (Vorlage nginx-hochladen.inc), Einrichten, Deploy-Liste und Glibc-Prüfung vorhanden, Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/schreiben.py:5448
  Evidence: Entfernen nur durch Besitzer:in oder Organisator:in; Token und andere Mitwirkende abgelehnt.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/reisespeicher.py:944
  Evidence: Fassungen in allen Versionen, Prüfsummen, Löschprotokoll mit Vormerkung und Bestätigung (engine/konten.py:1298); Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/konten.py:1298
  Evidence: Löschen betrifft nur die zwei Pfade des Bildes, Prüfsummenbindung schützt andere Bilder.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/schreiben.py:5399
  Evidence: `bild_aendern` lehnt bei status entfernt ab (F001 behoben); ID bleibt vergeben.
  Status: CONFIRMED

Confirmation:
  AC: AC-14
  Code reference: engine/texte_de.py:3891
  Evidence: Kopfkommentar nennt Entfernen und Verlauf; Zusage mit 30 Tagen steht im Dialog, test_texte.py grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-15
  Code reference: engine/sw.vorlage.js:72
  Evidence: `bilderVergessen` nimmt nicht mehr bekannte Bilder bei der Installation aus allen Speichern.
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/konnektor.py:3629
  Evidence: Werkzeug gibt Link, Token nur als Hash in konten.db, 30 Minuten, 10 Fotos; engine/schnittstelle.py:88 führt image_upload_link mit deutschem Alias.
  Status: CONFIRMED

Confirmation:
  AC: AC-17
  Code reference: engine/rueckmeldungen.py:1678
  Evidence: Alle Fehlerfälle liefern dieselbe Antwort abgelaufen (410).
  Status: CONFIRMED

Confirmation:
  AC: AC-18
  Code reference: engine/rueckmeldungen.py:1679
  Evidence: Mitgliedschaft wird mit der Person verglichen, Rolle neu geprüft; Test herabgestufte Rolle grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-19
  Code reference: engine/rueckmeldungen.py:1657
  Evidence: Der Link-Pfad kennt nur GET und POST auf den Hochlade-Pfad; Test test_token_erlaubt_nur_hochladen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-20
  Code reference: engine/rueckmeldungen.py:1641
  Evidence: eigene CSP, Referrer-Policy no-referrer, default-src none.
  Status: CONFIRMED

Confirmation:
  AC: AC-21
  Code reference: engine/konten.py:1262
  Evidence: Konto löschen räumt hochladelinks und bild_loeschungen auf; Test test_konto_loeschen_raeumt_tokens_ab.
  Status: CONFIRMED

Confirmation:
  AC: AC-23
  Code reference: engine/packliste.py:138
  Evidence: Doku in ADR-0009, ADR-0001, konnektor.md, betrieb.md, design.md nachgeführt; Kopfkommentar englisch (engine/texte_en.py:3889) angepasst. Packliste akzeptiert den Ersatznamen gelöschter Konten.
  Status: CONFIRMED

Confirmation:
  AC: AC-22
  Code reference: engine/texte_en.py:3929
  Evidence: Wortlaut der V17-Tabelle stimmt mit texte_de.py überein, alle Sprachen vollständig; der Product Owner hat den Entwurf am 21.11.2026 freigegeben (Kommentar in Issue 582, authorAssociation OWNER).
  Status: CONFIRMED

Confirmation:
  AC: AC-24
  Code reference: engine/waechter.py:593
  Evidence: Öffentliche Suite grün (3453 passed); Instanz-Tests mit diesem Stand 17 passed, 1 failed (instanz-test-output.txt); der eine Fehler test_einstellungen_wie_auf_dem_server tritt identisch auf dem Stand 4515cb6 ohne 582 auf, betrieb/gemeinsam.sh ist unverändert, vorbestehend.
  Status: CONFIRMED

Confirmation:
  AC: AC-16
  Code reference: engine/schnittstelle.py:88
  Evidence: Werkzeugname image_upload_link mit deutschem Alias bild_hochladelink und Parametern (Zeile 141).
  Status: CONFIRMED

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
F001–F005 sind behoben und durch Tests belegt. Neu: F006 (LOW, enges Zeitfenster, nicht blockierend).
Tests: 382 passed (Zieldateien), 3453 passed (volle Suite), 0 failed, 0 übersprungen
Edge cases: Rennen Wächter gegen Vorgang, Upsert, Migration alter Datenbank, Drosselung, Token-Zähler geprüft; nur F006 (LOW)
Regressions: None found
Checklist: 24/24 proven (AC-24 mit vorbestehendem, nicht verursachtem Instanz-Testfehler)

## Geprüfte Dateien

- sha256:99c9a5b192778626fedd52fbb8df372f3fc3e39b7fe6ae2f4522ffb5da16e852  engine/anmeldung.py
- sha256:8abef87818d00f82c66e34c68b31b9a35859b26280eb35642c5246c6c38956f9  engine/bauen.py
- sha256:0c637f940137414a728a74e894f025af5ae66a7a6a0ad95b74622c67999e8b08  engine/bilder.py
- sha256:8613d744ecd8fed0f830565d875a513b1264c9398a883165ba0a97fd590b9eb0  engine/konnektor.py
- sha256:a006b4672a0652391c5013e8b4740da2acc9e32682169589689346df40612622  engine/konten.py
- sha256:876fdc6c735ccb8a8e0d5612e2455d0d1e317b26b8a87efb9b5874046a7dfa9d  engine/packliste.py
- sha256:8953730baaed5fdff089d78e2e13eb560197a3f321b934f82c88e5abadbbbb22  engine/reise.py
- sha256:898f82d263163a298a92982f7f4f622449c73541aee82f39cbf00a0ba249d886  engine/reisespeicher.py
- sha256:12f439af1e4f8e64bdf7ec314c9d1d9ce374097e49e5e95ab80801b3a5f7c0a6  engine/rueckmeldungen.py
- sha256:8cbd50f28bfa0cde90ec6f2cd62bd107c3a6ac01d26b81c0a2a411aeb3407529  engine/schnittstelle.py
- sha256:a6e1c5ef63ffb70606cfe02177eb0724aff63b0d8a117dd78d189e513df01d0f  engine/schreiben.py
- sha256:4fa7e73af97247e10f589526d9cd46a5865083e550e768b571928a0b416869a7  engine/sw.vorlage.js
- sha256:42ad11ba89f59421f97dcfae50d8f8cd167c5be46745de19614d2b56f5bd2713  engine/texte_de.py
- sha256:75b51707d32aea3f1eee774d0f2003990f2d65d27ac217bbeeefb2d837bb8841  engine/texte_en.py
- sha256:1b52af1aabf9a36d0069fbd3406364510c3a9560fa49a7113856e78455f0cec3  engine/waechter.py

## Prüfbasis

- base: 4515cb678b6bc7d5920a7e1dc3bbf58836f3c133
- blob:8481ce30fd9818d9571e3949449cb1882323a7e9  engine/anmeldung.py
- blob:cc7d2aecb6ac81ea60f6724698d17125dcdfbdbe  engine/bauen.py
- blob:5bfcf47e4a9fd72a0cf5564e39175eebd5e72130  engine/bilder.py
- blob:b98684b3bd58f6c52dcf05542137c0d67bdf863b  engine/konnektor.py
- blob:90b377ffd77be8f33dd77fa891f860815be71367  engine/konten.py
- blob:60a14e4dae10fa1c4730d2ab7fe9dd72127beef0  engine/packliste.py
- blob:f0e782943c6265265a81ce3970fcabb1c99ef6de  engine/reise.py
- blob:26674390e706f89102420a7e4a7bd64529462b1b  engine/reisespeicher.py
- blob:1293c2043105388931556b6e1b5d2d3dd36f3e9a  engine/rueckmeldungen.py
- blob:c7abc98ba049fa714aced1ea5de90c9e34ffbcc9  engine/schnittstelle.py
- blob:802a78f066075f607f04d0e73d531c3e235d33ed  engine/schreiben.py
- blob:3938530d407c411223101c76249017d85acc8f08  engine/sw.vorlage.js
- blob:4d16ac3629365d27efd8c0e827ba4475a60311a7  engine/texte_de.py
- blob:8989989a81d2cdc5321120c079e248adf44a58f4  engine/texte_en.py
- blob:1f9accf09780f1fa0da63fd3061ff1d0a7303406  engine/waechter.py
