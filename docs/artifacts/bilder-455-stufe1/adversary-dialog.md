# Adversary Dialog — bilder-455-stufe1
Spec: docs/specs/oberflaeche/bilder-455-stufe1.md
Datum: 2026-11-15 17:43

## Checkliste
- [x] **AC-1 (P1):** Given eine Commons-Datei oder eine Wikidata-Kennung mit freier Lizenz / When `image_add` mit `zu` aufgerufen wird / Then entsteht `BI-NN` mit Herkunft, gesäubertem Urheber, Lizenz und beiden WebP-Fassungen, und die Antwort an Claude zeigt eine kleine Vorschau.
- [x] **AC-2 (P1):** Given eine Lizenz außerhalb der Positivliste (Free Art, NC, ND, GFDL-only, unbekannt) / When `image_add` / Then Ablehnung mit dem passenden Schlüssel `bild.abgelehnt.*` und kein Eintrag.
- [x] **AC-3 (P1):** Given Rolle `mitwirkend` / When Bild hinzufügen, ändern, zurückziehen oder Titelbild setzen / Then alles außer dem Titelbild gelingt; Given `organisator` / When Titelbild setzen / Then es gibt genau ein Titelbild.
- [x] **AC-4 (P1):** Given ein zurückgezogenes Bild / When gebaut wird / Then fehlt es überall, bleibt aber in Liste und Ablage; Given 60 aktive Bilder / When ein weiteres / Then Ablehnung, außer `max_anzahl` in `reise.yaml` ist höher.
- [x] **AC-5 (P1):** Given Commons antwortet mit 429 und dann 200 / When `image_add` / Then gelingt der Abruf vor der Schreibsperre mit Zeitlimit 20 s und User-Agent aus `instanz.kennung()`; kein Test benutzt das Netz.
- [x] **AC-6 (P1):** Given ein Text mit `![](https://…)` oder `![](//host/…)` / When gebaut oder über den Schreibweg geschrieben wird / Then Fehler mit Katalogtext; Links bleiben erlaubt; die Meta-CSP enthält `img-src 'self' data:` (`blob:` nur nach V10 mit Grund im PR-Text), und der Seitentest zeigt Karte, Belege und App-Symbol ohne CSP-Fehler in Chromium und WebKit.
- [x] **AC-7 (P1):** Given eine Reise mit `![](medien/x.jpg)` und einem fremden Bild im Text / When `neu.py nachziehen` zweimal läuft / Then Altbestand steht als `BI-NN` mit `quelle: reise` in `bilder.yaml`, das fremde Bild ist ein Link, der zweite Lauf ändert nichts, und der Bau gelingt.
- [x] **AC-8 (P1):** Given `![…](BI-NN)` im Text / When gebaut wird / Then erscheint das Bild mit Namensnennung nach V16 und seine große Fassung steht in der Offline-Liste des Service Workers.
- [x] **AC-9 (P1):** Given `BI-03` und `B-03` / When `neu`, `routen` und `schreiben` Kennungen erkennen / Then werden sie nie verwechselt; `bilder.py` steht in `KN_MODULE` und `SB_MODULE`.


## Nicht Teil dieser Prüfung (Paket P1)

Entscheidung des Product Owners vom 15.11.2026: Paket P1 wird einzeln ausgeliefert (wie in der Spec vorgesehen). Die folgenden Punkte sind weder bewiesen noch Defekte; sie werden in eigenen Durchgängen geprüft: AC-10 mit den Tests der einbindenden Instanz vor dem Vorspulen (Suite des Branches grün, 2877 passed), AC-11 bis AC-15 mit P2, AC-16 und AC-17 mit P3.

* **AC-10 (P1, Suite gruen, Instanz-Tests offen bei Auslieferung):** Given der Branch / When die volle Testsuite und die Tests der einbindenden Instanz laufen / Then sind beide grün (Nachweis im PR-Text).
* **AC-11 (P2, nicht Teil von P1, folgt mit P2/P3):** Given die Beispielreise / When die Seite in Chromium und WebKit (auch 360 px) geöffnet wird / Then zeigen Titelbild, Vorschau in der Tagesliste, Kopfbild an der Heimat, Bildreihe, Mini-Vorschau, Bild im Text und Großansicht die Maße und Stellen aus V13 bis V17 mit Nennung nach V16, ohne Überbreite.
* **AC-12 (P2, nicht Teil von P1, folgt mit P2/P3):** Given das Stadtwochenende / When gebaut und geöffnet wird / Then enthält es keine Bild-Elemente und keine Bilddaten.
* **AC-13 (P2, nicht Teil von P1, folgt mit P2/P3):** Given die neuen Bausteine / When die Karte geöffnet wird / Then lädt sie ohne CSP-Fehler (Seitentest aus P1 bleibt grün).
* **AC-14 (P2, nicht Teil von P1, folgt mit P2/P3):** Given aktive Bilder / When gebaut wird / Then enthält die Offline-Liste die kleine Fassung aller und die große von Titel- und Kopfbildern; Given über `offline_mb` / Then Warnung, der Bau gelingt.
* **AC-15 (P2, nicht Teil von P1, folgt mit P2/P3):** Given neue Bausteine und Texte / When die Prüfungen von Bausteinseite und Texten laufen / Then stehen sie in Kopfkommentar, Bausteinseite, `docs/design.md` und allen Sprachdateien.
* **AC-16 (P3, nicht Teil von P1, folgt mit P2/P3):** Given ein Mitglied mit Titelbild / When „Meine Reisen“ geöffnet wird / Then zeigt die Kachel das Bild über `/bild/<reise>/<BI>.webp` (Ordnername, `Cache-Control: private`), ohne Titelbild die Akzentfläche mit App-Symbol; Given Nicht-Mitglied / Then kein Bild; der geheime Link taucht nie auf.
* **AC-17 (P3, nicht Teil von P1, folgt mit P2/P3):** Given P3 ist ausgeliefert / When die Doku geprüft wird / Then sind `docs/konnektor.md`, `docs/design.md`, `docs/ontologie.md` und der ADR-0001-Verlauf nachgeführt.

## Dialog

### Runde 1
**Adversary:** Suite gezielt ausgefuehrt: test_bilder.py + test_sicherheit.py = 110 passed, 0 skipped (inkl. Chromium und WebKit); test_betrieb/test_texte/test_englisch_schnittstelle = 283 passed (docs/artifacts/bilder-455-stufe1/adversary-test-output.txt). Volle Suite laut docs/artifacts/bilder-455-stufe1/test-green-output.txt: 2855 passed. Danach Randfaelle von Hand gegen eine Kopie der Beispielreise: 19 Bildquellen-Varianten im Text (https, HTTPS, //host, /\host, /abs, data:, DaTa:, HTML-img, srcset, picture, Tab im Schema, Referenz-Syntax, mit Titel, Link, BI-99, bi-01, BI-01 mit Titel) und 1 Konfigurationsfall (reise.yaml bilder), 1 Altbestandsfall mit kaputter Bilddatei, Titelbild-Wechsel.

Befunde der Runde 1:

Finding:
  ID: F001
  Severity: HIGH
  Category: spec_violation
  Code reference: engine/reise.py:584
  Description: Die Schluesselliste von Reise.daten() kennt "bilder" nicht. Steht in reise.yaml der in AC-4 und im Katalogtext (bild.abgelehnt.grenze) genannte Block `bilder: {max_anzahl: 100}`, bricht der Bau mit "reise.yaml: unknown key bilder" ab (Probe: Beispielreise plus Block, bauen.bauen -> BauFehler). bilder_grenzen() (engine/reise.py:60) und bild_grenze() (engine/schreiben.py:5109) lesen den Block zwar, aber test_grenze_je_reise (engine/tests/test_bilder.py:355) baut danach nie.
  Spec requirement: AC-4 - 60 aktive Bilder, Ablehnung ausser max_anzahl in reise.yaml ist hoeher.
  Conflict: Die Grenze laesst sich nicht erhoehen, ohne die Reise unbaubar zu machen (Probebau des Schreibwegs lehnt dann auch jede weitere Aenderung ab).
  Remediation: "bilder" in die erlaubten Schluessel (engine/reise.py:584) aufnehmen und Werte pruefen; Test, der mit gesetztem Block baut.

Finding:
  ID: F002
  Severity: HIGH
  Category: edge_case
  Code reference: engine/neu.py:1451
  Description: bilder_nachziehen stellt Dateien einzeln um (neu.py:1474 und write_text in der Schleife), speichert plan/bilder.yaml aber erst am Ende. Eine kaputte Altbild-Datei (Probe: medien/kaputt.png mit Inhalt "kein bild", Verweis in inhalt/wissen.md, ein gueltiges Bild vorher in inhalt/etappen.md) wirft bilder.Abgelehnt("bild.abgelehnt.kein_rasterbild") aus fassungen_schreiben (engine/bilder.py:274) ungefangen: Traceback, nachziehen bricht ab. Zustand danach: etappen.md steht schon auf ![n](BI-04), die WebP-Dateien BI-04 liegen in medien/bilder/, plan/bilder.yaml enthaelt BI-04 nicht; der Bau meldet "image BI-04 is not in the list of images". Jeder weitere Lauf stuerzt erneut ab.
  Spec requirement: AC-7 - nachziehen laeuft, der Bau gelingt; CLAUDE.md: Handschritt nach Software-Wechsel ist ein Fehler der Software.
  Conflict: Teilweise umgestellte, nicht baubare Reise; der Workflow "Software nachziehen" waere fuer diese Reise dauerhaft kaputt.
  Remediation: Abgelehnt je Bild abfangen (Bild als unveraendert lassen, Meldung), Liste und Texte erst gemeinsam am Ende schreiben (oder Liste nach jedem Bild speichern); Test mit kaputter Datei.

Finding:
  ID: F003
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/schreiben.py:5204
  Description: bild_aendern setzt bei titelbild=false (explizit, nur Organisator) die Marke bei ALLEN Bildern zurueck, auch wenn das angesprochene Bild gar nicht das Titelbild ist. Probe: Beispielreise (Titelbild BI-02), bild_aendern(ziel=BI-03, titelbild=false) -> Antwort "changed", danach hat kein Bild mehr ein Titelbild.
  Spec requirement: AC-3 - genau ein Titelbild / hoechstens eines.
  Conflict: Ein Aufruf fuer ein anderes Bild nimmt der Reise ihr Titelbild; die Antwort meldet harmlose Aenderung.
  Remediation: Marke nur loeschen, wenn titelbild=true gesetzt wird oder das Bild selbst das Titelbild ist.

Finding:
  ID: F004
  Severity: LOW
  Category: edge_case
  Code reference: engine/schreiben.py:5186
  Description: Ein Bild laesst sich zugleich zurueckziehen und als Titelbild setzen, und ein zurueckgezogenes Bild behaelt die Titelbild-Marke (Probe: bild_aendern BI-01 titelbild=true zurueckziehen=true -> titelbild bleibt bei BI-01 in der Liste). In P1 hat die Marke noch keinen Verbraucher; mit P2 (Titelbild-Anzeige, AC-11/AC-16) muss ein zurueckgezogenes Titelbild als "nicht vorhanden" gelten (AC-4 "fehlt ueberall").
  Spec requirement: AC-4 / AC-3 (genau ein sichtbares Titelbild).
  Conflict: Latenter Fehler fuer P2.
  Remediation: Marke beim Zurueckziehen entfernen oder in P2 beim Lesen nur aktive Bilder zaehlen; Test dazu.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/bauen.py:505
  Description: `![x](BI-01 "Titel")` und `![x](bi-01)` werden von BILD_LINK/KENNUNG nicht als Kennung erkannt; der Bau gelingt ohne Fehler und gibt ein totes relatives <img src="BI-01"> ohne Nennung aus (Probe: "bititel BAU OK", "kleinbi BAU OK"). Kein Sicherheitsproblem (gleiche Adresse), aber stilles totes Bild.
  Spec requirement: AC-8 - ![...](BI-NN) erscheint mit Nennung.
  Conflict: Randvariante der Schreibweise erzeugt kein Bild und keinen Fehler.
  Remediation: Titel-Variante zulassen oder BI-artige Ziele ohne Eintrag als Baufehler melden.
**Implementierer:** (nicht beteiligt; Kontextisolierung, keine Rueckmeldung eingeholt)

### Runde 2
**Adversary:** Zweite Runde, gezielt auf die Punkte, die in Runde 1 ohne Befund blieben, mit eigenem Beweis:

Confirmation:
  AC: AC-1
  Code reference: engine/bilder.py:217
  Evidence: abrufen() holt Metadaten (Commons/Wikidata P18), prueft Lizenz, nur Hosts upload/thumb.wikimedia.org, Raster per Pillow; fassungen_schreiben (engine/bilder.py:270) legt 480/1600-WebP ohne EXIF an; engine/schreiben.py:5147 legt BI-NN mit quelle, urheber (nh3 gesaeubert, bilder.py:81), lizenz, seite an; engine/konnektor.py:1628 gibt die kleine Fassung als MitBild an Claude; engine/schnittstelle.py:85 englischer Name image_add. Tests gruen. Randfall Wikidata ohne P18 -> nicht_gefunden (bilder.py:180).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/bilder.py:93
  Evidence: Positivliste CC0/gemeinfrei/CC BY/CC BY-SA per fullmatch; Free Art, NC, ND, GFDL, unbekannt, fehlend -> Abgelehnt("bild.abgelehnt.lizenz"), das schreiben.py:5147 vor jedem Eintrag und vor dem Ablegen der Dateien in Ablehnung umsetzt; Katalogtexte engine/texte_de.py:3736 und engine/texte_en.py:3734. 5 parametrisierte Lizenzfaelle gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/reise.py:115
  Evidence: AKTIONEN "bild" ab mitwirkend, "titelbild" nur organisator; bild_anfrage prueft das Titelbild-Recht vor dem Netz (engine/schreiben.py:5129ff). Mitwirkend: hinzufuegen, aendern, zurueckziehen gelingen; Titelbild abgelehnt; hoechstens ein Titelbild beim Setzen. EINSCHRAENKUNG siehe F003 und F004.
  Status: CONFIRMED (mit F003, F004 als Randfaelle)

Confirmation:
  AC: AC-4 (Teil 1, Zurueckziehen)
  Code reference: engine/bauen.py:466
  Evidence: Zurueckgezogenes Bild: bild_kennung gibt "" zurueck (Bild fehlt im Text), bleibt in plan/bilder.yaml und medien/bilder/. Test test_zurueckgezogenes_bild_entfaellt gruen. Teil 2 (Grenze erhoehen) ist durch F001 gebrochen (Grenze 60 selbst: engine/reise.py:57, test_vorgabe_der_grenze_ist_60 gruen).
  Status: CONFIRMED fuer Teil 1, DISPROVEN fuer max_anzahl (F001)

Confirmation:
  AC: AC-5
  Code reference: engine/bilder.py:127
  Evidence: _holen: User-Agent instanz.kennung() (bilder.py:133), Zeitlimit min(20 s, Rest der 60-s-Frist), genau eine Wiederholung nach 429/5xx mit PAUSE; Abruf vor der Sperre in engine/schreiben.py:5745 (bild_vorab) und engine/schreiben_git.py:189 (vorgang reicht bild_vorab als FR_BILD_VORAB weiter); Tests ersetzen urlopen, kein Netz. Randfall: scheitert die Vorbereitung (Zeitlimit), ruft der Vorgang selbst ab (dokumentierter Rueckfall wie bei kartenpunkte); nicht als Defekt gewertet.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/bauen.py:76
  Evidence: FREMDE_BILDQUELLE (Schema, Schraegstrich, Backslash nach Entfernen von Steuerzeichen) wird auf das erzeugte HTML angewendet (bauen.py:197), deckt damit Markdown, HTML-img, Referenzsyntax und Titel ab. Probe 19 Varianten (adversary-test-output.txt): https, HTTPS, //, /\, /abs, data:, DaTa:, img-HTML, srcset, picture, Tab im Schema, Referenz, mit Titel, ftp, blob ergeben BauFehler; ein Link auf https baut. Meta-CSP engine/bauen.py:150 mit img-src self und data: ohne blob: (test_sicherheit.py:59); Seitentest test_seite_unter_der_csp_ohne_meldung chromium und webkit gruen (nicht uebersprungen). Schreibweg lehnt ab (test_schreibweg_lehnt_fremdes_bild_im_text_ab, 2 gruen). Kein Verbraucher von blob: oder createObjectURL in vorlage.html oder sw.vorlage.js (grep leer).
  Status: CONFIRMED

Finding:
  ID: F007
  Severity: LOW
  Category: edge_case
  Code reference: engine/neu.py:1484
  Description: AC-7, Randformen: Bilder mit Quelle /\host oder /a.png in Markdown werden von bilder_nachziehen nicht zum Link (nur Schema oder //, neu.py:1466); ein data:-Bild wird zu einem Link mit data:-Schema, den der Bau weiter als Fehler meldet. Im Trockenlauf (schreiben=False) vergibt _bild_aus_der_reise (neu.py:1443) fuer mehrere Bilder dieselbe Kennung in den Meldungen.
  Spec requirement: AC-7 - fremdes Bild ist ein Link, der Bau gelingt.
  Conflict: Nur Randformen; Hauptfall (https, http, //) und Idempotenz gruen.
  Remediation: Muster in nachziehen an FREMDE_BILDQUELLE angleichen; data: entfernen statt verlinken.

Bewertung des Hinweises zu AC-7 (#584): selbst erhoben: nachziehen auf einer Kopie der Beispielreise aendert nur plan/arten.yaml (herberge: attribute preis gets rolle kosten), keine Bilddatei, keinen Text, keine Bilderliste. Der Test test_nachziehen_stellt_altbestand_um_und_ist_idempotent vergleicht ALLE Dateien nach erstem und zweitem Lauf (volle Idempotenz) und ist gruen; der abgeschwaechte Vergleich betrifft nur test_nachziehen_aendert_die_beispielreise_nicht_mehr. Das traegt sachlich. Der Fall der kaputten Datei ist aber F002.

Confirmation:
  AC: AC-8
  Code reference: engine/bauen.py:485
  Evidence: bild_kennung (bauen.py:466) schreibt die grosse Fassung in self.bilder und self.fassungen und die Nennung (nennung_html: Urheber, Lizenz-Link, Commons-Seite; gemeinfrei nur Urheber; Werte maskiert, nur https-Links) hinter das img; die grosse Fassung steht in __DATEIEN__ (bauen.py:1528). Tests zu Nennung und Offline-Liste gruen. Abweichungen der Schreibweise siehe F005.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/routen.py:38
  Evidence: MUSTER bild BI-NN neben buchung B-NN; neu.ARTEN enthaelt BI (engine/neu.py:53), _nummern verlangt B- ohne vorangehenden Buchstaben, sodass BI-03 B-03 nicht zaehlt; ID_MUSTER (engine/schreiben.py:1212) trennt BI und B; engine/konnektor.py:3350 registriert die Werkzeuge; betrieb/deploy.sh:27 und :33 enthalten bilder.py in KN_MODULE und SB_MODULE (test_betrieb gruen).
  Status: CONFIRMED

AC-10: Volle Suite 2855 passed (test-green-output.txt); die Tests der einbindenden Instanz laufen erst vor der Auslieferung mit dem gepushten Branch: offen bei Auslieferung, kein Defekt. Die gruene Suite hat F001 bis F003 nicht erkannt (Testluecken: kein Bau mit reise.yaml-Block, keine kaputte Altdatei, kein titelbild=false auf Nicht-Titelbild).

AC-11 bis AC-17: nicht Teil von P1 (folgt mit P2/P3); weder bewiesen noch als Defekt gewertet.

Weitere Belege je Datei (Abdeckung der geaenderten Dateien):

Confirmation:
  AC: AC-1
  Code reference: engine/konnektor.py:1628
  Evidence: ontologie_werkzeug gibt bei antwort[vorschau] MitBild mit der kleinen WebP-Fassung an Claude zurueck.
  Status: CONFIRMED

Confirmation:
  AC: AC-1
  Code reference: engine/schnittstelle.py:85
  Evidence: image_add und image_update auf bild_hinzufuegen und bild_aendern; Parameter belongs_to, caption, alt_text, title_image, withdraw, restore (test_englisch_schnittstelle gruen).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/schreiben_git.py:189
  Evidence: vorgang nimmt bild_vorab und gibt es ueber vorab_umgebung als FR_BILD_VORAB an den Unterprozess.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/texte_de.py:3736
  Evidence: Katalogtexte bild.abgelehnt.* und pruefung.bauen.bild_fremd vorhanden (test_texte gruen).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/texte_en.py:3734
  Evidence: dieselben Schluessel in Englisch vorhanden.
  Status: CONFIRMED

**Implementierer:** (nicht beteiligt)

### Runde 3 (Nachpruefung nach den Behebungen)
**Adversary:** Alle Befunde der Runden 1 und 2 selbst nachgestellt (Proben in adversary-test-output.txt). Gezielte Suiten: test_bilder, test_sicherheit, test_betrieb, test_texte, test_englisch_schnittstelle = 413 passed, 0 skipped. Die Befunde F001 bis F007 aus Runde 1 und 2 sind Historie; massgeblich ist der Stand dieser Runde.

Nachpruefung F001 (BEHOBEN): Bau mit bilder max_anzahl 100 gelingt; bilder leer gelingt; True, 1.5, offline_mb 0, unbekannter Schluessel, Zahl 5 und Liste ergeben jeweils einen klaren BauFehler (pruefung.reise.bilder) statt "unknown key".
Confirmation:
  AC: AC-4
  Code reference: engine/reise.py:581
  Evidence: bilder_pruefen akzeptiert nur ganze Zahlen ab 1 (bool ausgeschlossen) fuer max_anzahl und offline_mb; "bilder" steht in der Schluesselliste (reise.py:597). Schluessel pruefung.reise.bilder in engine/texte_de.py:3736 und engine/texte_en.py:3734.
  Status: CONFIRMED

Nachpruefung F002 (BEHOBEN): Reise mit gueltigem Altbild in etappen.md und kaputter Datei in wissen.md: nachziehen laeuft durch, Meldung "OPEN ... left unchanged", BI-04 steht in plan/bilder.yaml UND im Text, zweiter Lauf aendert nichts ausser der OPEN-Meldung (Dateivergleich leer). Hinweis, vorbestehend und nicht von P1 verursacht: der Bau stuerzt bei einer kaputten Bilddatei weiter mit UnidentifiedImageError (Image.open in bauen.py, gleicher Absturz auf dem Stand vor nachziehen); kein P1-Defekt.
Confirmation:
  AC: AC-7
  Code reference: engine/neu.py:1473
  Evidence: _bild_ersetzen faengt bilder.Abgelehnt/OSError je Bild, laesst das Bild unveraendert; bilder_nachziehen (neu.py:1514) schreibt Liste und Texte erst am Ende. Dry-Run vergibt eindeutige Kennungen. Randformen (/\, /abs, data:) werden Alt-Text oder Link, Bau gelingt (Probe datax/https im Text).
  Status: CONFIRMED

Nachpruefung F003/F004 (BEHOBEN), Titelbild-Wechsel hin und her an der Beispielreise (Titel BI-02): BI-03 false -> Titel bleibt BI-02; BI-01 true -> BI-01; BI-02 true -> BI-02; BI-01 true -> BI-01; BI-01 zurueckziehen+titelbild -> Ablehnung bild.abgelehnt.zurueckgezogen; BI-01 zurueckziehen (Mitwirkend) -> Marke weg, kein Titelbild; Titelbild auf zurueckgezogenem -> abgelehnt; wiederherstellen+titelbild in einem Aufruf -> gelingt; Mitwirkend titelbild true und false -> abgelehnt (bild.abgelehnt.rolle), Mitwirkend Bildunterschrift gelingt; eigenes false entfernt nur die eigene Marke; Bau danach gelingt. Immer hoechstens ein Titelbild.
Confirmation:
  AC: AC-3
  Code reference: engine/schreiben.py:5187
  Evidence: bild_titelbild_setzen (Recht, false nur eigene Marke, true loest bisheriges ab, nie zurueckgezogen); bild_status_setzen entfernt beim Zurueckziehen die Marke (schreiben.py:5177ff). Rechte engine/reise.py:118.
  Status: CONFIRMED

Nachpruefung F005: "![x](BI-01 "Titel")", "![x](bi-01)", "![x]( BI-01 )" ergeben jetzt das Bild mit Nennung (BILD_KENNUNG_IM_TEXT, engine/bauen.py:77 und :525), kleingeschriebenes unbekanntes bi-99 ist Baufehler. Rest, LOW: Referenzsyntax "![x][r]" mit "[r]: BI-01" baut ohne Fehler und gibt weiter ein totes img src="BI-01" ohne Nennung aus (Probe ref/refklein). Kein Sicherheitsproblem (gleiche Adresse), exotische Schreibweise.
Finding:
  ID: F008
  Severity: LOW
  Category: edge_case
  Code reference: engine/bauen.py:525
  Description: BILD_KENNUNG_IM_TEXT erfasst nur Inline-Bilder, nicht Referenzdefinitionen; ![x][r] mit [r]: BI-01 erzeugt ein stilles totes Bild (im Bau-HTML src="BI-01" nachgewiesen).
  Spec requirement: AC-8 - ![...](BI-NN) erscheint mit Nennung (Inline-Form; Referenzform nicht ausdruecklich genannt).
  Conflict: Randvariante ohne Fehlermeldung.
  Remediation: Ziel BI- nach dem Markdown-Lauf im HTML als Baufehler melden oder Referenzdefinitionen mit BI- umschreiben. Nicht blockierend.

Restbestaetigung der uebrigen P1-Punkte (Code- und Testlauf in dieser Runde unveraendert gruen, Probe der 19 Quellenvarianten erneut: https, data:, DaTa: bleiben Baufehler, Links bauen):
Confirmation:
  AC: AC-1
  Code reference: engine/bilder.py:217
  Evidence: abrufen mit Hostliste, Raster-Pruefung, Fassungen (bilder.py:270); Eintrag engine/schreiben.py:5147; MitBild engine/konnektor.py:1628; englischer Name engine/schnittstelle.py:85.
  Status: CONFIRMED
Confirmation:
  AC: AC-2
  Code reference: engine/bilder.py:93
  Evidence: Positivliste per fullmatch, Ablehnung bild.abgelehnt.lizenz vor jedem Eintrag; Texte engine/texte_de.py:3738 und engine/texte_en.py:3736.
  Status: CONFIRMED
Confirmation:
  AC: AC-5
  Code reference: engine/schreiben.py:5758
  Evidence: bild_vorab ruft vor der Sperre ab; engine/schreiben_git.py:189 reicht bild_vorab als FR_BILD_VORAB weiter; _holen (engine/bilder.py:127) mit User-Agent, 20 s, einer Wiederholung nach 429; Tests ohne Netz.
  Status: CONFIRMED
Confirmation:
  AC: AC-6
  Code reference: engine/bauen.py:199
  Evidence: fremde Bildquelle im HTML geprueft (bauen.py:78 FREMDE_BILDQUELLE); CSP img-src self data: ohne blob (bauen.py:150); Seitentest Chromium und WebKit gruen, nicht uebersprungen.
  Status: CONFIRMED
Confirmation:
  AC: AC-8
  Code reference: engine/bauen.py:468
  Evidence: bild_kennung mit Nennung und grosser Fassung in der Offline-Liste; zurueckgezogen entfaellt.
  Status: CONFIRMED
Confirmation:
  AC: AC-9
  Code reference: engine/routen.py:38
  Evidence: MUSTER bild neben buchung; neu.ARTEN enthaelt BI (engine/neu.py:53); deploy.sh Zeilen 27 und 33 mit bilder.py (test_betrieb gruen).
  Status: CONFIRMED

AC-10: Suite laut Entwickler 2877 passed; Tests der einbindenden Instanz erst vor der Auslieferung mit dem gepushten Branch: offen bei Auslieferung, kein Defekt. AC-11 bis AC-17: nicht Teil von P1 (folgt mit P2/P3).

**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
F001 bis F007 behoben und nachgestellt. Offen nur F008 (LOW, Referenzsyntax von BI-Bildern), nicht blockierend. AC-1 bis AC-9 bewiesen; AC-10: Suite gruen, Tests der einbindenden Instanz offen bei Auslieferung; AC-11 bis AC-17 nicht Teil von P1.

## Geprüfte Dateien

- sha256:9110627c01f211a9c441dfa36dbbd09500e05a0b505d2949bc95b6d96dee7843  engine/bauen.py
- sha256:cdff09024df297030d82807a7f62b3f28ebd6caccf61c6fb71661be162778745  engine/bilder.py
- sha256:3b5145014308a290ca33a156bb81055507ede7af431a50e6ae9c379b68d28052  engine/konnektor.py
- sha256:2d5e5ce92525eaff3a92063836329861d231a6406035c09b9a3e1995c0a00128  engine/neu.py
- sha256:558f4ec346177d077323561a7e5e2f5268a031bf87e887b97c13d75b197fe439  engine/reise.py
- sha256:46dc2d884bb6ca0b4846ae60815cd11127f6f0014c761472aeb216ec39859b5f  engine/routen.py
- sha256:9909733117af1a07d6c6a3eac3bf6ea8f823f1ec1414641fc387cc9eb1abca01  engine/schnittstelle.py
- sha256:93df5b54535a4866c114ee616ec5e084af40ad6cfbac522e07b0abb241b6fdc4  engine/schreiben.py
- sha256:bc56604bc781f865241ed3b9745990ca081ad531edf6758457b03967129ad8f8  engine/schreiben_git.py
- sha256:fc30b28b86748c8fe0bd781a6ff9410e57136c37c9a25a4cc5c4965f8db97c0c  engine/texte_de.py
- sha256:e17223ab33a0cfc14fbdf7587da2b3ce7619099f37d2204d89a96cba0948e41e  engine/texte_en.py

## Prüfbasis

- base: bb187975d1c2847f5e8022d9a41fc7745eae409d
- blob:6f1ae3fe249414b7bba554324aacc8cb5c6fc867  engine/bauen.py
- blob:91a0cb95ab0cd81bcd8dc909c481854a123acfa4  engine/bilder.py
- blob:bbf55d81407194b192f38f9c041af4849982d574  engine/konnektor.py
- blob:20699b7f97aa415856dd2a9f37585c411f25d893  engine/neu.py
- blob:a758b6a7c273c884ae1e3cbdf6ffec77f935fb23  engine/reise.py
- blob:1718f8490c7dd3500cfc3b18fad7595507afb947  engine/routen.py
- blob:6b990f20d75960808c230a5c1db42db6b3fe3973  engine/schnittstelle.py
- blob:f7ff15e7d0b44d83b21ccc256bc57f03b74457d3  engine/schreiben.py
- blob:7bd5fbdf94a6d47567fc60432a1e8c1b7e491f00  engine/schreiben_git.py
- blob:02f0e10db10a3e022a8e7f16833265c92f8e27b7  engine/texte_de.py
- blob:d726f7cb6e5007811f511c6feafcb6baa9733bd4  engine/texte_en.py

## Geprüfte Dateien

- sha256:9110627c01f211a9c441dfa36dbbd09500e05a0b505d2949bc95b6d96dee7843  engine/bauen.py
- sha256:cdff09024df297030d82807a7f62b3f28ebd6caccf61c6fb71661be162778745  engine/bilder.py
- sha256:3b5145014308a290ca33a156bb81055507ede7af431a50e6ae9c379b68d28052  engine/konnektor.py
- sha256:2d5e5ce92525eaff3a92063836329861d231a6406035c09b9a3e1995c0a00128  engine/neu.py
- sha256:558f4ec346177d077323561a7e5e2f5268a031bf87e887b97c13d75b197fe439  engine/reise.py
- sha256:46dc2d884bb6ca0b4846ae60815cd11127f6f0014c761472aeb216ec39859b5f  engine/routen.py
- sha256:9909733117af1a07d6c6a3eac3bf6ea8f823f1ec1414641fc387cc9eb1abca01  engine/schnittstelle.py
- sha256:93df5b54535a4866c114ee616ec5e084af40ad6cfbac522e07b0abb241b6fdc4  engine/schreiben.py
- sha256:bc56604bc781f865241ed3b9745990ca081ad531edf6758457b03967129ad8f8  engine/schreiben_git.py
- sha256:fc30b28b86748c8fe0bd781a6ff9410e57136c37c9a25a4cc5c4965f8db97c0c  engine/texte_de.py
- sha256:e17223ab33a0cfc14fbdf7587da2b3ce7619099f37d2204d89a96cba0948e41e  engine/texte_en.py

## Prüfbasis

- base: bb187975d1c2847f5e8022d9a41fc7745eae409d
- blob:6f1ae3fe249414b7bba554324aacc8cb5c6fc867  engine/bauen.py
- blob:91a0cb95ab0cd81bcd8dc909c481854a123acfa4  engine/bilder.py
- blob:bbf55d81407194b192f38f9c041af4849982d574  engine/konnektor.py
- blob:20699b7f97aa415856dd2a9f37585c411f25d893  engine/neu.py
- blob:a758b6a7c273c884ae1e3cbdf6ffec77f935fb23  engine/reise.py
- blob:1718f8490c7dd3500cfc3b18fad7595507afb947  engine/routen.py
- blob:6b990f20d75960808c230a5c1db42db6b3fe3973  engine/schnittstelle.py
- blob:f7ff15e7d0b44d83b21ccc256bc57f03b74457d3  engine/schreiben.py
- blob:7bd5fbdf94a6d47567fc60432a1e8c1b7e491f00  engine/schreiben_git.py
- blob:02f0e10db10a3e022a8e7f16833265c92f8e27b7  engine/texte_de.py
- blob:d726f7cb6e5007811f511c6feafcb6baa9733bd4  engine/texte_en.py
