# Adversary Dialog — 613-lizenzpruefung-entfernen
Spec: docs/specs/oberflaeche/bilder-lizenzhinweis-613.md
Datum: 2026-11-17 08:18

## Checkliste
- [x] **AC-1:** Given ein Commons-Bild mit beliebiger oder fehlender Lizenz / When `image_add` es hinzufügt / Then wird es angenommen; `bild.abgelehnt.lizenz` wird nirgends mehr geworfen.
- [x] **AC-2:** Given die Beispielreise (`beispiel/reisen/beispielreise`) und das Stadtwochenende (`beispiel/reisen/stadtwochenende`) / When ein Bild mit NC, ND, GFDL, Free Art License, „Copyrighted“ oder ohne Lizenz hinzugefügt wird / Then wird es an beiden Reisen angenommen.
- [x] **AC-3:** Given ein angenommenes eingeschränktes Bild / When die Reise gebaut wird / Then zeigt die Seite die Namensnennung mit Urheber und Lizenz unter dem Bild (gemeinfreie Bilder nur den Urheber, wie bisher).
- [x] **AC-4:** Given die Antwort von `image_add` / When die Lizenz frei ist (CC0, gemeinfrei, CC BY, CC BY-SA mit oder ohne Version) / Then nennt sie Urheber, Lizenz und die Verantwortung der Person, ohne Einschränkungssatz.
- [x] **AC-5:** Given die Antwort von `image_add` / When die Lizenz NC, ND, GFDL, unbekannt oder fehlend ist / Then steht zusätzlich je Einschränkung ein Satz, der sagt, was eingeschränkt ist; bei mehreren Einschränkungen alle.
- [x] **AC-6:** Given leerer Urheber oder leere Lizenz / When die Antwort gebildet wird / Then stehen Ersatzwörter aus dem Katalog und keine leeren Stellen.
- [x] **AC-7:** Given die Kataloge / When sie geprüft werden / Then existiert `bild.abgelehnt.lizenz` in keiner Sprache, die neuen Schlüssel stehen in jeder Sprache, und die Ausnahmelisten in `test_texte.py` sind nicht länger.
- [x] **AC-8:** Given `plan/bilder.yaml` / When Bilder hinzugefügt werden / Then gibt es kein neues Feld, und `neu.py nachziehen` ändert nichts (kein Formatwechsel).
- [x] **AC-9:** Given Abrufe mit Netzfehler, nicht unterstütztem Format, Größe über 15 MB oder falscher Quellenangabe / When `image_add` aufgerufen wird / Then bleiben die Ablehnungen `bild.abgelehnt.netz`, `kein_rasterbild`, `zu_gross` und `quelle` wie bisher.
- [x] **AC-10:** Given Werkzeugbeschreibung und `docs/konnektor.md` / When gelesen / Then nennen sie keine Positivliste, sondern Verantwortung der Person und den Hinweis in der Antwort.

## Dialog

### Runde 1
**Adversary:** Tests gezielt: 299 passed (adversary-test-output.txt). Beweise je AC:

Confirmation:
  AC: AC-1
  Code reference: engine/bilder.py:97
  Evidence: lizenz_lesen wirft nie; lizenz_pruefen und FREI entfernt; bild.abgelehnt.lizenz nirgends im Code.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/schreiben.py:5280
  Evidence: bild_hinzufuegen ohne Lizenzabweisung; Tests parametrisiert fuer Wanderung und Stadt gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/bauen.py:498
  Evidence: nennung_daten unveraendert; https() macht aus leerer lizenz_url None; nennung_html filtert leere Teile. Bautest gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/schreiben.py:5301
  Evidence: bild_antwort liefert neu plus rechte; einschraenkungen bei CC0, PD, CC BY und CC BY-SA mit oder ohne Version ist leer. Probe: 'CC BY-SA 2.5 it', 'cc by 4.0', 'PD-old', 'PD-old-70' ergeben [].
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/bilder.py:106
  Evidence: Probe: CC BY-NC-ND 4.0 ergibt nc und nd; 'cc-by-nc-sa-3.0' nc; GFDL gfdl; 'Attribution' andere; None und Leerraum fehlt; 'Bonnc' andere (NC nicht als Wortteil).
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/schreiben.py:5303
  Evidence: Probe mit Urheber None oder leer und Lizenz None: Ersatzwoerter, kein doppeltes Leerzeichen, kein ': ,', kein ' .'. HTML im Urheber bleibt Klartext in der Antwort (Saeuberung in lizenz_lesen; die Antwort ist kein HTML).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/texte_de.py:3825
  Code reference: engine/texte_en.py:3823
  Evidence: neue Schluessel rechte, einschraenkung.nc/nd/gfdl/fehlt/andere, ohne_urheber, ohne_lizenz in de und en (engine/texte_en.py:3823); bild.abgelehnt.lizenz in beiden entfernt; test_texte.py gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:5274
  Evidence: Kein neues Feld; lizenz_url wird jetzt als leerer Text statt weggelassen gespeichert. Folgen: bauen.https() (bauen.py:503) behandelt leer wie fehlend; nachziehen kennt lizenz_url nicht (kein Treffer in neu.py); AC-8-Test gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/bilder.py:236
  Evidence: abrufen behaelt netz, kein_rasterbild, zu_gross, quelle; bestehende Tests gruen.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/texte_de.py:3849
  Evidence: Werkzeugbeschreibung de und en (engine/texte_en.py:3847) und docs/konnektor.md nennen keine Positivliste, sondern Verantwortung und Hinweis.
  Status: CONFIRMED

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/bilder.py:63
  Description: OHNE_EINSCHRAENKUNG erlaubt ein optionales zweibuchstabiges Sprachkuerzel; 'CC BY NC', 'CC BY ND', 'CC BY-SA ND' ergeben [] (frei) statt nc/nd. Probe bestaetigt.
  Spec requirement: AC-5 — NC und ND brauchen einen Satz
  Conflict: Nur bei nicht Commons-ueblichen Namen (Commons schreibt 'CC BY-NC 4.0'); entspricht woertlich Spec-Regel 3. Praktisch irrelevant.
  Remediation: Sprachkuerzel nur nach der Version zulassen.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/bilder.py:63
  Description: 'CC-BY-SA-4.0', 'CC BY 4.0 International', 'CC BY-SA 3.0 Unported' gelten als 'andere' (Warnsatz statt frei). Fehlalarm, nie Sperre.
  Spec requirement: AC-4 — freie Lizenzen ohne Einschraenkungssatz
  Conflict: Freie Lizenzen koennten einen unnoetigen Satz bekommen; die Spec nennt nur die Schreibweise mit Leerzeichen.
  Remediation: Optional Bindestriche und Zusaetze tolerieren.

**Implementierer:** keine Rueckmeldung (isolierte Pruefung).

### Runde 2
**Adversary:** Nachbohren: (a) bauen.icon_aus_svg liest die Datei per Path.read_bytes und gibt CairoSVG nur bytestring; unsafe bleibt aus. Probe mit image-Verweis auf eine lokale Datei rendert ohne den Verweis zu laden (16x16, kein Fehler): Sicherheitsverhalten gleich. Ein Netzpfad wurde frueher von CairoSVG selbst geoeffnet, jetzt nicht mehr (Verbesserung). Aufrufer bauen.py:1867 (Path) und schreiben.py:3324 (bytes); 34 Icon- und SVG-Tests gruen.
Code reference: engine/bauen.py:1840
(b) lizenz_url als leerer Text statt fehlend: Verbraucher bauen.https() und nennung_daten robust; kein Pruefer liest das Feld. Kein Regress.
(c) lizenz_lesen(None) und ({}) liefern lizenz leer, url None, gemeinfrei False und werfen nie; unverschluesselte Links werden auf https gehoben.
(d) 'GFDL, CC BY-SA 3.0' ergibt nur gfdl, korrekt.
(e) Englischer Katalog vollstaendig; ohne_urheber und ohne_lizenz klein geschrieben, passen mitten in den Satz.
Keine weiteren Brueche gefunden.
**Implementierer:** keine Rueckmeldung.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 299 passed, 0 failed, 0 übersprungen
Edge cases: geprüft; nur F001 und F002 (LOW, seltene Namen und Fehlalarme, keine Sperre)
Regressions: None found
Checklist: 10/10 points proven

## Geprüfte Dateien

- sha256:7fcb3d8c0dfde58a3b51bc44b40aa5b8a6710242f01db0e3c86530f1d98fe1ae  engine/bauen.py
- sha256:3fb621bf276c5e23f3c2ece9dd794ac214bc9c5d7aafa382ef04ecfdff753e6a  engine/bilder.py
- sha256:aff212c9f05f844bd1571835544a9959cfc0bc37c6349e93ec73dbca442f90e6  engine/schreiben.py
- sha256:126aabcb8b1eb9adead487a793313c757c532fab28a8be12a854a18cc905cf80  engine/texte_de.py

## Prüfbasis

- base: 14b835bd60ead0216581dd57a52d084d6ef25cd1
- blob:92b73964877cdd1807d859c5636355d134927eb2  engine/bauen.py
- blob:513e7a736c8fd8b75612d0f1fdfc59121b11c01d  engine/bilder.py
- blob:6d446c43f535e37cff41e66363afcf84bee4cfcc  engine/schreiben.py
- blob:c3cf2e0a0798f32718ce74c8b69ce5d0eae92afc  engine/texte_de.py

## Geprüfte Dateien

- sha256:7fcb3d8c0dfde58a3b51bc44b40aa5b8a6710242f01db0e3c86530f1d98fe1ae  engine/bauen.py
- sha256:3fb621bf276c5e23f3c2ece9dd794ac214bc9c5d7aafa382ef04ecfdff753e6a  engine/bilder.py
- sha256:aff212c9f05f844bd1571835544a9959cfc0bc37c6349e93ec73dbca442f90e6  engine/schreiben.py
- sha256:126aabcb8b1eb9adead487a793313c757c532fab28a8be12a854a18cc905cf80  engine/texte_de.py
- sha256:02445cf5641e450f0afc552e111a7bda117e846c079a61d718355e61e2f07c4e  engine/texte_en.py

## Prüfbasis

- base: 14b835bd60ead0216581dd57a52d084d6ef25cd1
- blob:92b73964877cdd1807d859c5636355d134927eb2  engine/bauen.py
- blob:513e7a736c8fd8b75612d0f1fdfc59121b11c01d  engine/bilder.py
- blob:6d446c43f535e37cff41e66363afcf84bee4cfcc  engine/schreiben.py
- blob:c3cf2e0a0798f32718ce74c8b69ce5d0eae92afc  engine/texte_de.py
- blob:f5e6863701f66b392c891fa540c60dedc8e40e59  engine/texte_en.py
