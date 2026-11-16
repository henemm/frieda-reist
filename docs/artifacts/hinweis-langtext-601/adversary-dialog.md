# Adversary Dialog — hinweis-langtext-601
Spec: docs/specs/fast/fix-601-hinweis-langtext.md
Datum: 2026-11-16 19:30

## Checkliste
- [x] **AC-1:** `ding.hinweis` ist im Register als Langtext mit mindestens der bisherigen Länge (`MAX_TEXT`).
- [x] **AC-2:** `ding_aendern` mit mehrzeiligem Hinweis (Fettes, nummerierte Liste) speichert den Text mit Zeilen, ohne Leerraum am Ende, in beiden Beispielreisen; die Reise baut.
- [x] **AC-3:** `ding_anlegen` (Ort) speichert einen mehrzeiligen Hinweis unverändert.
- [x] **AC-4:** Ein Hinweis mit Überschrift oder HTML wird mit Begründung abgelehnt.
- [x] **AC-5:** Ein alter Hinweis mit `<b>` und `##` in den Reisedaten bleibt baubar.
- [x] **AC-6:** Der Kalender zeigt den Hinweis ohne `**`, mit erhaltenen Zeilen der Liste.
- [x] **AC-7:** Die Seite zeigt den Hinweis an der Heimat des Dings mit Fettem und nummerierter Liste; im Hauptbereich stehen nirgends Sternchen.

## Dialog

### Runde 1
**Adversary:** Testlauf test_textform, test_texte, test_konnektor*: 193 passed, 0 failed, 0 übersprungen (adversary-test-output.txt). Die Browser-Tests der Seite (AC-7) liefen mit (19 passed bei -k seite/langtext, keine Skips).
Eigene Proben auf einer Kopie der Beispielreise (ding_aendern): Strecke E-01 mit Fett und nummerierter Liste wird mit Zeilen gespeichert; Ort O-01 mit Liste und Leerraum am Ende wird ohne Leerraum gespeichert; Tabelle, Bild, Skript-HTML, `#`-Überschrift, Codeblock, Kennung (V-01.a) werden mit Begründung abgelehnt; 1000 Zeichen gehen, 1001 werden abgelehnt; Link und CRLF gehen; leerer oder nur aus Leerraum bestehender Hinweis löscht das Feld (None); danach baut die Reise.
Konnektor-Schema: beide Werkzeuge (DING_ANLEGEN, DING_AENDERN) beschreiben hinweis über textform.schema; die Beschreibung steht in texte_de und texte_en; es gibt nur diese zwei Sprachdateien, test_texte (Schlüssel in allen Sprachen) ist grün. Der alte Schlüssel konnektor.feld.allgemein.hinweis ist nirgends mehr verwendet.
Code reference: engine/textform.py:38 (Register LANG, 1000; Test fordert >= MAX_TEXT)
Code reference: engine/schreiben.py:1559 (ding_anlegen liest als Langtext) und engine/schreiben.py:2066 (ding_aendern)
Code reference: engine/konnektor.py:2784 (und 2795)
Code reference: engine/texte_de.py:1225
Code reference: engine/texte_en.py:1224
Code reference: engine/kalender.py:158 (Aufenthalt) und engine/kalender.py:182 (Unterkunft), beide über textform.klartext (None-sicher, Zeilen der Liste bleiben)
Code reference: engine/vorlage.html:1949 (Strecke), :1991 (Aufenthalt), :2154/:2175 (Unterkunft), :2207 (Ort): Heimat über langtext, Kurzformen über mdKlar
**Implementierer:** keine Antwort (Pflichtprüfung durch Adversary); Tests der Spec sind vorhanden und grün.

### Runde 2
**Adversary:** Zweiter Angriff auf Lücken. (a) Bauen prüft den Hinweis nicht: ein alter Hinweis mit `<b>Burg</b> ## ...` baut (Test test_alter_hinweis_mit_html_und_raute_bleibt_baubar, grün). (b) Verbleibende rohe Verwendungen von hinweis in der Vorlage (Zeilen 3006, 3693, 4314) gehören zu n.hinweis der Nacht, nicht zum Ding; unverändert laut Spec. (c) Konnektor-Ausgabe konnektor.py:958 und :894 gibt den Hinweis roh (mit Zeilen) an die KI zurück, das ist Lesen, kein Fehler. (d) Kartenpunkte aus OpenStreetMap (neu.py:581) unverändert. (e) Nebenbefund: ein Langtext lässt Setext-Überschriften ("Titel" über "=====") und Zitate ("> x") durch. Das stammt aus dem gemeinsamen Register textform.langtext_fund (aus #594), nicht aus dieser Änderung; die Seite zeigt es als einfachen Text. Kein Bruch dieser Spec, nur Hinweis.
Kein Gegenbeispiel zu einer der sieben Zusagen gefunden. Alle sieben Punkte mit Test und eigener Probe belegt.
**Implementierer:** keine Änderung nötig.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
VERDICT: VERIFIED

Confirmation:
  AC: AC-1
  Code reference: engine/textform.py:38
  Evidence: FELDER["ding.hinweis"] = (LANG, 1000); Test test_hinweis_im_register_nicht_kuerzer_als_bisher grün
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/schreiben.py:2066
  Evidence: Proben Strecke E-01 und Ort O-01 sowie Tests für beide Beispielreisen: Zeilen bleiben, Leerraum am Ende fällt weg, Reise baut
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/schreiben.py:1559
  Evidence: test_hinweis_anlegen_behaelt_zeilen_und_liste (Ort) grün
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/konnektor.py:2795
  Evidence: Überschrift, HTML, Tabelle, Bild, Codeblock werden mit Begründung abgelehnt (Probe und Test), Schema nennt Form und Länge
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/texte_de.py:1225
  Evidence: Bauen prüft den Hinweis nicht; Test mit altem Wert mit <b> und ## baut; Beschreibungstexte in DE und EN (engine/texte_en.py:1224) vorhanden
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/kalender.py:182
  Evidence: test_kalender_zeigt_hinweis_ohne_auszeichnung: kein ** im Text, Zeilen "1. ..." und "2. ..." erhalten
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/vorlage.html:1991
  Evidence: Browser-Test test_seite_zeigt_hinweis_als_langtext für beide Reisen: ol >= 3, fett >= 2, keine Sternchen im Hauptbereich
  Status: CONFIRMED

Tests: 193 passed, 0 failed, 0 übersprungen
Edge cases: All checked, none broken
Regressions: None found
Checklist: 7/7 points proven

## Geprüfte Dateien

- sha256:aabfabd4bec226f5c017d18cf80fd349435f4337f2302c1ee6b53b0fc9e1139b  engine/kalender.py
- sha256:57978e3f097790f1880d667da415c518b299d88d51cb2183cf257a9741d319c9  engine/konnektor.py
- sha256:bf662cb961b447fda313ad688714ef2b8baa31c31c439eea71215287eece692a  engine/schreiben.py
- sha256:11954fdf826ebcf85f99259b1239087b3dee945ed823f4e5c58d064cc07ae969  engine/texte_de.py
- sha256:b5822b9bc4b0934d2ea4a65d6a6e03e715ee047900a7378b23adeb69c44b20a7  engine/texte_en.py
- sha256:76a2a7ec464a4bf3184f373bcb79a01f51f31a8a8d3d4c7a727a72edcc90ca2e  engine/textform.py
- sha256:310f13ac2291c8b2170be20571dae8fabb3c31e9e4d78c2474d60b36f689f6f6  engine/vorlage.html

## Prüfbasis

- base: 05763f5baf58415090012de2c6fde19af89433f4
- blob:f2c2aea6c11705cbf456807c9dfb545c5f74fc2c  engine/kalender.py
- blob:2c122417b413ad5ee538fbac583e3f80e22c48e1  engine/konnektor.py
- blob:a5a815a58a7ec1c17e7dbd0962086b329cba9583  engine/schreiben.py
- blob:87cc81e66051a51f7638af46f17916213cff8607  engine/texte_de.py
- blob:22efe75a74a894a9f3a1f26a88b5b23b509796fe  engine/texte_en.py
- blob:98b74ae141d6efea67e227f1acf670f4c86be928  engine/textform.py
- blob:d281a9820796dc07020147ca8356d2d719e7fc22  engine/vorlage.html

## Geprüfte Dateien

- sha256:aabfabd4bec226f5c017d18cf80fd349435f4337f2302c1ee6b53b0fc9e1139b  engine/kalender.py
- sha256:57978e3f097790f1880d667da415c518b299d88d51cb2183cf257a9741d319c9  engine/konnektor.py
- sha256:bf662cb961b447fda313ad688714ef2b8baa31c31c439eea71215287eece692a  engine/schreiben.py
- sha256:11954fdf826ebcf85f99259b1239087b3dee945ed823f4e5c58d064cc07ae969  engine/texte_de.py
- sha256:b5822b9bc4b0934d2ea4a65d6a6e03e715ee047900a7378b23adeb69c44b20a7  engine/texte_en.py
- sha256:76a2a7ec464a4bf3184f373bcb79a01f51f31a8a8d3d4c7a727a72edcc90ca2e  engine/textform.py
- sha256:310f13ac2291c8b2170be20571dae8fabb3c31e9e4d78c2474d60b36f689f6f6  engine/vorlage.html

## Prüfbasis

- base: 05763f5baf58415090012de2c6fde19af89433f4
- blob:f2c2aea6c11705cbf456807c9dfb545c5f74fc2c  engine/kalender.py
- blob:2c122417b413ad5ee538fbac583e3f80e22c48e1  engine/konnektor.py
- blob:a5a815a58a7ec1c17e7dbd0962086b329cba9583  engine/schreiben.py
- blob:87cc81e66051a51f7638af46f17916213cff8607  engine/texte_de.py
- blob:22efe75a74a894a9f3a1f26a88b5b23b509796fe  engine/texte_en.py
- blob:98b74ae141d6efea67e227f1acf670f4c86be928  engine/textform.py
- blob:d281a9820796dc07020147ca8356d2d719e7fc22  engine/vorlage.html
