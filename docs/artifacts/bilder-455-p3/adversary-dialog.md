# Adversary Dialog — bilder-455-p3
Spec: docs/specs/oberflaeche/bilder-455-p3.md
Datum: 2026-11-17 09:51

## Checkliste
- [x] **Mitglied, Reise mit Titelbild:** „Meine Reisen“ zeigt die Kachel mit dem Titelbild (16:7), darunter Titel und Rolle; ein Klick führt
- [x] **Mitglied, Reise ohne Titelbild** (etwa das Stadtwochenende): Akzentfläche mit App-Symbol, sonst gleich.
- [x] **Reise ohne gebaute Seite:** Kachel ohne Link, Fläche ohne Symbol.
- [x] **Archiv:** aufklappbar, gleiche Kacheln.
- [x] **Bildroute:** liefert nur kleine Fassungen aktiver Bilder und das Symbol an angemeldete Mitglieder; alles andere ergibt dieselbe 404-Antwort.
- [x] **AC-1 (AC-16, Route):** Given ein Mitglied / When `/bild/<reise>/BI-NN.webp` (kleine Fassung eines aktiven Bildes) oder `/bild/<reise>/symbol.png` aufgerufen wird / Then kommt 200 mit passendem `Content-Type`, `Cache-Control: private, max-age=86400` und `nosniff`; Given nicht angemeldet, kein Mitglied, unbekannte Reise, `..`, große Fassung, zurückgezogenes Bild oder fehlende Datei / Then kommt jeweils dieselbe 404-Antwort, und der Pfad wird nie aus der Anfrage zusammengesetzt.
- [x] **AC-2 (AC-16, Kachel):** Given ein Mitglied mit Titelbild / When „Meine Reisen“ geöffnet wird / Then zeigt die Kachel das Titelbild 16:7 über `/bild/<reise>/<BI>.webp` (dekorativ), darunter Titel und Rolle, Link auf die Reiseseite, darunter Personen und „Reise löschen“; ohne Titelbild die Akzentfläche mit App-Symbol, ohne gebaute Seite die Kachel ohne Link und ohne Symbol; das Archiv zeigt dieselben Kacheln in `<details>`; das Stadtwochenende bleibt fehlerfrei.
- [x] **AC-3 (AC-16, Adresse und Breite):** Given die gebaute Kontoseite / When geprüft wird / Then enthält keine Bildadresse die Adresse der Reiseseite, und bei 360 px gibt es keine Überbreite (ab 760 px zwei Spalten).
- [x] **AC-4 (AC-17):** Given P3 ist ausgeliefert / When die Doku geprüft wird / Then sind `docs/konnektor.md` (Route), `docs/design.md` (Kachel, `reiseKachel`), `docs/ontologie.md` (Bild) und der Verlauf in `docs/adr/0001-kern.md` (Bild, Hinweis statt Lizenzprüfung, #613) nachgeführt.

## Dialog

### Runde 1
**Adversary:** Testlauf (294 bestanden, 0 fehlgeschlagen, 0 übersprungen, siehe adversary-test-output.txt) und Direktaufruf von bild_antwort mit Angriffsformen. Ergebnis 404 für: kleingeschriebenes bi-01.webp, BI-01.WEBP, doppelter Schrägstrich, abschließender Schrägstrich, %2e%2e als Reisename, Zeilenumbruch am Ende, klein-Feld mit ../geheim.webp, absolutes klein /etc/passwd, leeres klein, klein ".", klein null, Symlink im seiten-Ordner auf Datei außerhalb (resolve + is_relative_to fängt ihn). Gültige Formen liefern 200. Nicht angemeldet, Nicht-Mitglied und unbekannte Reise liefern byteidentische 404-Antworten (Vergleich r1==r2==r3 wahr). Über bearbeiten(): Query-String wird abgeschnitten (200), %42I-01.webp wird nicht dekodiert (404), POST liefert 404 ohne Inhalt.
**Implementierer:** Code: engine/anmeldung.py:1329 (BILD_WEG fullmatch, Datei nur aus daten.json oder festem Namen), engine/anmeldung.py:1345 (resolve(strict) plus is_relative_to), engine/anmeldung.py:1366 (eine 404 für alles), engine/anmeldung.py:1470 (nur GET, sonst k=None). HEAD wird in engine/konnektor.py:3540 auf GET abgebildet, also Kopf ohne Inhalt; engine/konnektor.py:3605 meldet GET, HEAD, OPTIONS.

### Runde 2
**Adversary:** Kachel und Doku. engine/anmeldung.py:1071 reise_kachel: Titelbild nur bei gebauter Seite und gültiger BI-Kennung, Bildadresse /bild/<reise>/<BI>.webp ohne Reiseseiten-Adresse; ohne Titelbild Akzentfläche mit symbol.png nur wenn icon-192.png existiert; ohne Seite div statt a und keine Symbol. engine/anmeldung.py:1090 konto_seite nutzt .kacheln für Liste und Archiv (details), CSS ab 760 px zwei Spalten, minmax(0,1fr) gegen Überbreite bei 360 px (Browser-Test test_kacheln_im_browser bestanden). nginx-Ort betrieb/vorlagen/nginx-konnektor-orte.inc:99 vorhanden. Doku: docs/konnektor.md:195, docs/design.md:241 (reiseKachel), docs/ontologie.md:62, docs/adr/0001-kern.md:85 (#613). Schwachstelle: Titelbild mit fehlender Datei zeigt nur die leere Akzentfläche (alt leer), kein Symbol-Ersatz.
**Implementierer:** Fehlende Titelbild-Datei ist ein reiner Schönheitsfall; Hintergrund --acc2 bleibt sichtbar, kein Fehler, keine Informationslücke.

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/anmeldung.py:1071
  Description: reise_kachel prüft nicht, ob die Datei des Titelbilds existiert; bei fehlender Datei lädt das img nicht (404) und die Kachel zeigt nur die Hintergrundfarbe ohne Symbol.
  Spec requirement: AC-2 — Titelbild oder Akzentfläche mit Symbol
  Conflict: Nur kosmetisch, tritt nur bei beschädigter gebauter Seite auf; Spec verlangt keine Dateiprüfung beim Rendern.
  Remediation: Optional: Existenz der kleinen Fassung beim Rendern prüfen und auf Symbol zurückfallen.

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1366
  Evidence: 200 mit Content-Type, Cache-Control private max-age=86400 und nosniff; alle Unzulässigen identische 404; Pfad nur über daten.json oder festen Namen, resolve und is_relative_to.
  Status: CONFIRMED

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1345
  Evidence: Symlink und ../ im klein-Feld ergeben 404 (Probe).
  Status: CONFIRMED

Confirmation:
  AC: AC-1
  Code reference: engine/konnektor.py:3605
  Evidence: /bild/ ist als nur lesend (GET, HEAD, OPTIONS) gekennzeichnet; HEAD wird in engine/konnektor.py:3540 wie GET ohne Inhalt behandelt.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1071
  Evidence: Kachel mit Titelbild, Symbolfläche, Fläche ohne Link; Archiv in details mit denselben Kacheln.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/anmeldung.py:1090
  Evidence: Bildadresse nennt nur den Reiseordner; Kacheln ab 760 px zwei Spalten, minmax(0,1fr) ohne Überbreite.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: docs/konnektor.md:195
  Evidence: Route, design.md reiseKachel, ontologie.md Bild, adr 0001 Eintrag mit #613 vorhanden.
  Status: CONFIRMED

Confirmation:
  AC: Bildroute nginx
  Code reference: betrieb/vorlagen/nginx-konnektor-orte.inc:99
  Evidence: location ^~ /bild/ leitet an den Dienst.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 294 passed, 0 failed, 0 übersprungen. Edge cases: alle geprüft, keine gebrochen. Regressions: keine. Checklist: 9/9 proven. Ein LOW-Finding (F001, kosmetisch).

## Geprüfte Dateien

- sha256:72d17042543528dd202380d779008250d8f8c4986ad0acef8fb36a791ba20194  betrieb/vorlagen/nginx-konnektor-orte.inc
- sha256:ec128383ad3726c76406f1d2cd20334635ef1a513db5d63090d1f804f40453d4  docs/konnektor.md
- sha256:abfa01eadef76a69dc98fe4675fd059a67eb5e250a1cfa837bed1db50646f9d4  engine/anmeldung.py
- sha256:f87779376cc57396a15c991a4e4593b621fe5925c309b1fcd4d92925ebb8cb07  engine/konnektor.py

## Prüfbasis

- base: 07f39321a870c8f595c57101ad7420ed46518425
- blob:754d9a8cfd04d75d5508b45698d1bd95a30ac9d8  betrieb/vorlagen/nginx-konnektor-orte.inc
- blob:b3ea3fef18dc484f066540d936ec69c336be77b1  docs/konnektor.md
- blob:ae72a54534d2c128747decd23c4df639626b28be  engine/anmeldung.py
- blob:1d9e4e583c2f8d68775bacf58cb6220c4831f384  engine/konnektor.py
