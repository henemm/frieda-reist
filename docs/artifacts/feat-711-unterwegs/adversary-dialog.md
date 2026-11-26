# Adversary Dialog — feat-711-unterwegs
Spec: docs/specs/oberflaeche/funktionsseiten-711-unterwegs.md
Datum: 2026-11-26 20:04

## Checkliste
- [x] AC-1: `/info/funktionen/karte/` und `/info/funktionen/packliste/` liefern in DE und EN 200 mit allen Abschnitten aus dem Katalog und ihren Bildern (`test_unterseite[karte]`, `test_unterseite[packliste]`, `test_unterseiten_unterwegs`).
- [x] AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- [x] AC-3: Texte und Bilder vollständig je Sprache in den Maßen von `erzeugen` (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- [x] AC-4: Beispiele stimmen mit den Beispielreisen überein (Packliste 2810 g, 900/980/930 g, 70 € Anschaffung; Wanderstöcke am ersten Wandertag, Stirnlampe an der Wanderherberge Altendorf von Karl, Erste-Hilfe-Set trägt Ida, Sonnencreme weggelassen; Stadtwochenende: Ausweis packt Lea; Hotel am Elbufer mit Adresse und Kartenlinks; Bahn gestrichelt); jede Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.
- [x] AC-5: Ohne `ziel` nimmt `aufnehmen.mjs` jedes Bild wie bisher auf; vorhandene Bilder bleiben unverändert im Commit.

## Dialog

### Runde 1
**Adversary:** Tests selbst gelaufen: `pytest -q -n 4 test_funktionsseiten_711 test_texte test_englisch test_englisch_schnittstelle` = 113 passed, 0 failed, 0 übersprungen. `git diff --stat`: test_texte.py unverändert (Ausnahmelisten nicht länger). Neue Dateien unter engine/info/: nur karte/lage/summen-{de,en}.webp, vorhandene 16 Bilder unverändert (kein M-Status).
**Implementierer:** (nicht gesehen; Beweis nur aus Code und Bildern)

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1360
  Evidence: INFO_UNTERSEITEN enthält karte (bilder karte, lage) und packliste (summen, packliste); test_unterseite[karte|packliste] und test_unterseiten_unterwegs (engine/tests/test_funktionsseiten_711.py:215) grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1360
  Evidence: Die Übersicht leitet sich aus INFO_UNTERSEITEN ab; test_uebersicht_alle_funktionen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:4121
  Evidence: Alle Schlüssel info.bereich.karte.* und packliste.* stehen in DE (texte_de.py) und EN (texte_en.py:4121, :4159) gleich vollständig; test_texte_und_bilder_jeder_unterseite, test_texte, test_englisch grün; Ausnahmelisten unverändert.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/texte_en.py:4159
  Evidence: Zahlen gegengerechnet an beispiel/reisen/beispielreise/plan/packliste.yaml: 900 am Körper; 420+180+350+30=980 Tagesrucksack; 240+480+90+120=930 Rucksack; Summe 2810 g (Kamera G-11 ist per Art foto ausgeblendet, Sonnencreme entfällt); Anschaffung 45+25=70 €. Wanderstöcke an E-01, Stirnlampe an U-04 (Wanderherberge Altendorf, routen.yaml:130) von Karl, Erste-Hilfe-Set Ida, Sonnencreme weggelassen: stimmt. Stadtwochenende: Ausweis packt Lea (G-02). Hotel am Elbufer U-01, Adresse Terrassenufer 1 mit Google-Maps- und Apple-Karten-Link im Bild lage-de.webp. Bildunterschriften gegen die vier Bilder (mit Read angesehen) geprüft: karte (Dresden, Wanderwege mit Tagesnummern 2-4, Legende Hotel/Pension/Herberge/Bahn, Bahn gestrichelt), lage, summen (2810 g, 70 €, am Körper 900/Tagesrucksack 980/Rucksack 930), packliste (Papiere, Lea) beschreiben nur Sichtbares. Kein Widerspruch gefunden.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/info/aufnehmen.mjs:21
  Evidence: Das Rollen läuft nur in `if (bild.ziel)`; ohne ziel bleibt der Pfad goto, warten, Text, Screenshot unverändert. erzeugen.py:49 setzt ziel nur für karte; die anderen BILDER-Einträge haben kein ziel, und die Liste wird per `{"name": n, **b}` durchgereicht (erzeugen.py:80).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/info/erzeugen.py:49
  Evidence: Einträge karte, lage, summen ergänzt; bestehende Einträge unberührt.
  Status: CONFIRMED

### Runde 2
**Adversary:** Nachbohren: (a) karte.gut.1 „mindestens zwei Punkte mit Lage“ gegen engine/karte.py:3 und bauen.py:1254 geprüft: stimmt. (b) Karte „unter der Anreise“, „Karte vergrößern“ (texte_de.py:3395), „Punkte am Weg“ (texte_de.py:404), „Mitnehmen:“ (texte_de.py:3637), „Nur meins“, „Summe aufteilen nach“ stimmen mit den Seitentexten überein. (c) Das zweite Bild der Karte-Seite (lage) und das Bild summen enthalten Elemente, die nicht in der Unterschrift stehen (Foto im Hotelbild, Papier-Tabs), das ist keine falsche Behauptung. (d) EN-Unterschrift karte nennt keine Legendenwörter, hier nicht falsch, weil die Legende im EN-Bild übersetzt ist. (e) Randfall ziel nicht gefunden: p.$eval wirft, aufnehmen bricht dann laut ab, kein stilles Weglassen. 
**Implementierer:** –

Confirmation:
  AC: AC-4
  Code reference: engine/bauen.py:1163
  Evidence: Der erste Verdacht (karte.gut.3 „ab Status fest Hinweis auf Unterkünfte ohne Lage“, engine/texte_de.py:4156) ist ausgeräumt: bauen.py:1163 mahnt ab Status fest Unterkünfte ohne Lage. Keine Befunde.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

Kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Keine verdächtigen Schreibstellen; die Änderung schreibt nur Texte, Registereinträge und Bilder, keine Feldwerte.

## Verdict
VERDICT: VERIFIED
5/5 ACs bewiesen, 113 passed, 0 failed, 0 übersprungen, keine Befunde.

## Geprüfte Dateien

- sha256:196658729e3e67ddf3b40b87875fc6af727bc8d5128dca05abcd52e81c6b480c  engine/anmeldung.py
- sha256:325641b897a1fe003384aa73be9209d1bfafd28483ff01385b828c724fe544c0  engine/bauen.py
- sha256:de97c1d2fadd4b2d44bb5c6abdea5ca87afa86d4d18c620aee209eaecb0fe292  engine/info/aufnehmen.mjs
- sha256:ca464c584d2584566198132ea745d41dc720139e9e1c30425e12d625d568f283  engine/info/erzeugen.py
- sha256:12db21b2b149c60fe779817a77eb69dc0e496edda19ac285713f1537a4c996f8  engine/texte_de.py
- sha256:24244925aae89e8468385f3a709bbd1ef9f20fe64e9e3d12115f8e4541d76856  engine/texte_en.py

## Prüfbasis

- base: f40c3133a955fbbd00c021fa1adf9fe554536d7b
- blob:275e60a8e748c78b4688065f243fe432f33d4aa1  engine/anmeldung.py
- blob:5f85fbc42820e1e51ecd69854920588c6467d093  engine/bauen.py
- blob:29fefdfa104b6963f4a8a6dd862de878a378cbd4  engine/info/aufnehmen.mjs
- blob:590ee9434d8134fff4328329de0b5982c3168861  engine/info/erzeugen.py
- blob:1331a0e8c454e56d529ff39a9b2a70db7a8b3dfd  engine/texte_de.py
- blob:9a44cbe79177b45a7812c91fea48e260fe63a3aa  engine/texte_en.py

## Geprüfte Dateien

- sha256:196658729e3e67ddf3b40b87875fc6af727bc8d5128dca05abcd52e81c6b480c  engine/anmeldung.py
- sha256:325641b897a1fe003384aa73be9209d1bfafd28483ff01385b828c724fe544c0  engine/bauen.py
- sha256:de97c1d2fadd4b2d44bb5c6abdea5ca87afa86d4d18c620aee209eaecb0fe292  engine/info/aufnehmen.mjs
- sha256:ca464c584d2584566198132ea745d41dc720139e9e1c30425e12d625d568f283  engine/info/erzeugen.py
- sha256:12db21b2b149c60fe779817a77eb69dc0e496edda19ac285713f1537a4c996f8  engine/texte_de.py
- sha256:24244925aae89e8468385f3a709bbd1ef9f20fe64e9e3d12115f8e4541d76856  engine/texte_en.py

## Prüfbasis

- base: f40c3133a955fbbd00c021fa1adf9fe554536d7b
- blob:275e60a8e748c78b4688065f243fe432f33d4aa1  engine/anmeldung.py
- blob:5f85fbc42820e1e51ecd69854920588c6467d093  engine/bauen.py
- blob:29fefdfa104b6963f4a8a6dd862de878a378cbd4  engine/info/aufnehmen.mjs
- blob:590ee9434d8134fff4328329de0b5982c3168861  engine/info/erzeugen.py
- blob:1331a0e8c454e56d529ff39a9b2a70db7a8b3dfd  engine/texte_de.py
- blob:9a44cbe79177b45a7812c91fea48e260fe63a3aa  engine/texte_en.py
