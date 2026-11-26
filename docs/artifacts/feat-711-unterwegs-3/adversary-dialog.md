# Adversary Dialog — feat-711-unterwegs-3
Spec: docs/specs/oberflaeche/funktionsseiten-711-unterwegs-3.md
Datum: 2026-11-26 20:33

## Checkliste
- [x] AC-1: `/info/funktionen/erinnerungen/` liefert in DE und EN 200 mit allen Abschnitten aus dem Katalog und seinen Bildern (`test_unterseite[erinnerungen]`, `test_unterseiten_unterwegs`).
- [x] AC-2: Die Übersicht verlinkt den Bereich statt „Seite folgt“; die Gruppe „Unterwegs und gemeinsam“ hat keine Zeile „Seite folgt“ mehr (`test_uebersicht_alle_funktionen`).
- [x] AC-3: Texte und Bilder vollständig je Sprache (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- [x] AC-4: Beispiele stimmen mit der Beispielreise und der Quelle überein (S-Bahn-Buchung von Karl mit Frist 13.5. „Ticket in die App laden“; Pension Burgblick und Wanderherberge Altendorf nicht gebucht; Weg zum Zug am letzten Tag offen; Status „planung“ ohne Baustein `waechter`; drei Tage Vorlauf, 60 Tage Prüfalter, Ruhezeit 21:30–7:00, 14 Tage); jede Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.
- [x] AC-5: Vorhandene Bilder bleiben unverändert im Commit.

## Dialog

### Runde 1
**Adversary:** Tests selbst gelaufen: `pytest -q -n 4` über test_funktionsseiten_711, test_texte, test_englisch, test_englisch_schnittstelle: 116 passed, 0 failed, 0 übersprungen (Ausgabe: docs/artifacts/feat-711-unterwegs-3/test-run-output.txt wird durch den Gate-Lauf des Aufrufers erzeugt). Diff gelesen: nur 5 Dateien geändert plus zwei neue Bilder, keine Ausnahmelisten in test_texte.py angefasst.
**Implementierer:** n/a (isoliert).

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1368
  Evidence: INFO_UNTERSEITEN["erinnerungen"] mit Bildern bahnbuchung/kalender, vier Gesprächszeilen, vier "siehe"-Verweise; test_unterseite[erinnerungen] grün (DE/EN 200).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1345
  Evidence: test_unterseiten_unterwegs prüft jetzt `set(INFO_GRUPPEN["unterwegs"]) <= set(INFO_UNTERSEITEN)` (strenger als zuvor, kein Eintrag mehr hartkodiert); grün; "Seite folgt" nicht mehr im Code gefunden.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:4272
  Evidence: Schlüsselsatz info.bereich.erinnerungen.* (lead, wo, wer, bild.*, tun.1-9, wie.1-4, gespraech.1-4, rolle.1-3, gut.1-5) in DE und EN deckungsgleich (EN texte_en.py:4270); test_texte_und_bilder_jeder_unterseite grün. Fachwörter EN einheitlich: "trip", "notification", "organiser", "quiet hours", "My account", Status "Fixed/Travelling/After" wie seite.reise_status.* (texte_en.py:769-771).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/texte_en.py:4273
  Evidence: Bildunterschriften gegen die Bilder geprüft: bahnbuchung-de/en.webp zeigt gebuchte S-Bahn Dresden -> Stadt Wehlen, Frist 13.5. "Ticket in die App laden" (Untertitel passt). kalender-de/en.webp zeigt Tag 4 mit Wanderherberge Altendorf "nicht gebucht", darunter "Ganze Reise in den Kalender" und Hinweis "Nur Entschiedenes ..." (Untertitel passt). Oberflächenbezeichnungen stimmen mit seite.kalender.ganze_reise/hinweis_abo und seite.fuer_dich.titel/gelesen (EN "Mark as read") überein. Zahlen 3/7/60 Tage, 21:30-7:00, 14 Tage, Status-Übergänge 7 Tage vor Beginn/erster Tag/nach letztem Tag, Mail nach einem Tag: alle gleich docs/funktionen/erinnerungen.md:25-31,65-66,82. Beispielreise: reise.yaml Status planung, bausteine ohne waechter (Zeile 23); B-02 gebucht, bezahlt, Frist 2027-05-13 "Ticket in die App laden", wer Karl (routen.yaml:429-446); 13.5. minus 3 Tage = 10.5. stimmt.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/info/erzeugen.py:54
  Evidence: git status: unter engine/info/ nur erzeugen.py geändert (Eintrag "kalender", Ziel ".reise-tage > .chips") und neu kalender-de/en.webp; keine vorhandene .webp verändert.
  Status: CONFIRMED

### Runde 2
**Adversary:** Nachgebohrt: (a) Gespräch Zeile 4 sagt, Erinnerungen greifen bei "fest"; zusätzlich nötig ist Baustein waechter (aktuell aus), die Zeile schließt mit der Rückfrage "Soll ich sie so einschalten?" und deckt das ab. (b) DE schreibt Statuswörter klein in Anführungszeichen („fest“, „unterwegs“) wie die Quelldoku, die Oberfläche zeigt "Fest"/"Unterwegs" (texte_de.py:770-771); EN dagegen "Fixed" groß wie die Oberfläche. Rein kosmetisch. (c) Bild-Unterschrift EN übersetzt die im Bild deutsch gebliebene Beispieldaten-Frist; beschreibt trotzdem nur den Bildinhalt. (d) Kalenderbild-Release-Fußzeile zeigt Basis-Commit 0251567; harmlos.
**Implementierer:** n/a.

Finding:
  ID: F001
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/texte_de.py:4284
  Description: Statuswörter stehen in DE kleingeschrieben in Anführungszeichen („fest“, „unterwegs“), die Oberfläche zeigt "Fest"/"Unterwegs" (texte_de.py:770-771); EN nutzt die Oberflächenschreibweise.
  Spec requirement: AC-4 — Bezeichnungen der Oberfläche stimmen
  Conflict: Kleine Schreibabweichung zur Oberfläche, deckt sich aber mit docs/funktionen/erinnerungen.md.
  Remediation: Optional auf „Fest“/„Unterwegs“ angleichen.

Code reference (Abdeckung): engine/texte_en.py:4267 (Nachbarschlüssel unverändert), engine/info/erzeugen.py:51

## Herkunft der Vorbedingungen
kein Sprachprofil konfiguriert (`precondition_origins.default_lang`).

## Herkunft der Vorbedingungen

<!-- vom Prüfer auszufüllen, siehe `precondition_origins.py` -->

## Verdict

VERDICT: VERIFIED

Tests: 116 passed, 0 failed, 0 übersprungen. Edge Cases geprüft, nichts gebrochen. Checkliste 5/5 bewiesen. Einziger Befund F001 (LOW, kosmetisch).

## Geprüfte Dateien

- sha256:c6b306b90819d6a4c084fd6944df308daf6ba57f7939211a9d91a730a29e92d6  engine/anmeldung.py
- sha256:56550105279cf14834518b5c18c64f9ca18993dfc469fc31d6f3dea0e1c103ae  engine/info/erzeugen.py
- sha256:089b1f1003270775826f6017751b042ba75ade7a7f39db50e5e7d43443d105a4  engine/texte_de.py
- sha256:afb616f1f9074d46f81cd614a5e70aefe276a7ec7105950ceca481089d78259c  engine/texte_en.py

## Prüfbasis

- base: a3e02f7c3a9249a2ba2072251375121bf282d132
- blob:ba27fb20acac3e437e27d963a186e9d714476595  engine/anmeldung.py
- blob:5bb7b3a3205973e2072843077b36fcdf29dcd8fc  engine/info/erzeugen.py
- blob:d0cf6a461eaa1edfc0cb88e4fd27a8f0ef2835bf  engine/texte_de.py
- blob:b2ae41405b8a97e4f65dada308e8acb752520dc3  engine/texte_en.py
