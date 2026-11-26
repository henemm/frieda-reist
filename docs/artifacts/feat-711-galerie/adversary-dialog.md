# Adversary Dialog — feat-711-galerie
Spec: docs/specs/oberflaeche/funktionsseiten-711.md
Datum: 2026-11-26 16:29

## Checkliste
- [x] AC-1: Infoseite DE und EN: Bildreihe `.bilder.reihe` mit `data-galerie`, je Bild Link mit `data-breite`/`data-hoehe`, Hinweis zum Wischen; `galerie.js` eingebunden, kein Inline-Skript.
- [x] AC-2: `/info/galerie.js` und `/info/photoswipe-5.4.4.esm.min.js` werden als JavaScript ausgeliefert; andere Namen unter /info/ bleiben 404.
- [x] AC-3 (Browser, Handy 390 px und Rechner 1280 px, DE und EN): am Handy ist die Reihe waagerecht scrollbar, ein Bild 55–70 % der Reihe breit, der Hinweis sichtbar; am Rechner vier Bilder in einer Zeile, ohne Hinweis; nirgends seitlicher Überlauf der Seite.
- [x] AC-4 (Browser): Tipp auf Bild 2 öffnet die Großansicht mit Bild 2; der Streifen zeigt die Unterschrift und „… · Bild 2 von 4“ in der Sprache der Seite, sein Grund ist undurchsichtig, das Bild endet oberhalb des Streifens; Pfeil weiter zeigt Bild 3 und „Bild 3 von 4“; Escape schließt.
- [x] AC-5 (Browser, #706): Pfeil weiter sofort beim Öffnen ergibt keinen Skriptfehler, danach passt der Streifen zum gezeigten Bild.
- [x] AC-11: Die Ausnahmelisten in `test_texte.py` werden nicht länger; alle Tests grün.

## Dialog

### Runde 1
**Adversary:** Tests: 197 passed, 0 failed, 0 übersprungen (test_infoseite_galerie_711, test_infoseite, test_texte, test_anmeldung, test_konnektor). Quelltext galerie.js gelesen: passen() (Z. 44-47) misst den Streifen, setzt rand.unten = max(112, ceil(Höhe)) und ruft updateSize(true) nur bei Abweichung; Aufrufer: zeigen() (Z. 42) und pswp-Ereignis resize (Z. 48). F003/F004 mit eigener Playwright-Probe (Chromium, DE und EN, Skripte im Scratchpad) nachgestellt: 1280 nach 320 px bei Bild 3 und 4 sowie 390 nach 320 px: Bild endet jetzt genau am Streifenanfang (578/578), kein Überdecken mehr. Schleifenverdacht updateSize -> resize -> passen -> updateSize: passen() bricht bei gleicher Höhe ab (Z. 46), die Messung war nach 1,5 s Ruhe identisch (stabil=true in allen 5 Läufen je Sprache), keine pageerror. 6 schnelle Wechsel 320/1280 px in 150-ms-Takt: endet konsistent (Bild 4 bei 320 px: 578/578).
**Implementierer:** passen() bei jedem resize und nach jedem Füllen (galerie.js:44-48).

### Runde 2
**Adversary:** Wiederholung mit Schwerpunkt Breiter werden und Drehen. 320 nach 1280 px (Bild 4): Streifen 96 px, Bild unten 588 <= 604, rand.unten schrumpft also wieder (F004 behoben, Z. 45 max statt nur wachsen). 320 nach 360 px ok. Drehen 320x640 -> 640x320 -> 320x640 bei jedem der Bilder: Bild stets oberhalb des Streifens (208<=224 und 518<=518), Zähler bleibt richtig. Zusätzlich Zeile 51 (openingAnimationEnd mit updateSize bei rand>112) geprüft: kein Fehler, kein Doppelaufruf-Effekt. Früher bestätigte Punkte erneut: AC-1/AC-2 über Tests, AC-3 über Browsertest 390/1280 DE+EN, AC-5 Taste sofort beim Öffnen ohne pageerror (Sperre Z. 69-74, Guard Z. 37). Nicht abgedeckt: Größenänderung exakt während der Öffnungsanimation (updateSize wirkt dort laut Kommentar Z. 50 nicht, Z. 51 zieht danach nach), kein Fehlverhalten beobachtet.
**Implementierer:** (nicht befragt, Code durfte nicht geändert werden)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1442
  Evidence: Reihe mit data-galerie und data-texte, galerie.js per defer eingebunden, kein Inline-Skript; Test test_infoseite_hat_die_bildreihe_und_das_skript grün in DE und EN.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/konnektor.py:1
  Evidence: Nur die zwei festen Namen unter /info/ werden als text/javascript ausgeliefert, übrige 404; test_skripte_unter_info_ausgeliefert grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:3793
  Evidence: Hinweis im Katalog DE und EN (engine/texte_en.py:3791); Browsertest 390 und 1280 px DE und EN grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/app/galerie.js:45
  Evidence: Streifen wird gemessen, rand.unten = max(112, Höhe); Bild endet in allen Proben (Öffnen, Blättern, Verkleinern, Vergrößern, Drehen) oberhalb des Streifens.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/app/galerie.js:37
  Evidence: Guard bei fehlendem currSlide und Sperre bis openingAnimationEnd; Taste sofort beim Öffnen ohne pageerror.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/texte_en.py:3790
  Evidence: test_texte.py unverändert, 197 Tests grün, neue Schlüssel info.galerie.* in beiden Sprachen (engine/texte_de.py:3792).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/app/galerie.js:48
  Evidence: F003 behoben: resize-Hörer ruft passen(); 1280 auf 320 px bei Bild 3 und 4 DE, Bild 4 EN: Bild unten 578 gleich Streifenanfang 578. F004 behoben: max(112, Höhe) schrumpft bei kürzerer Unterschrift (96 px Streifen nach 320 auf 1280).
  Status: CONFIRMED

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:218
  Evidence: Skriptzeile /info/galerie.js defer in der Seite, keine Änderung gegenüber Vorrunde.
  Status: CONFIRMED

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
F003 und F004 behoben, keine neuen Findings (keine Schleife, stabile Messung, Drehen und Breiterwerden ok).
Tests: 197 passed, 0 failed, 0 übersprungen
Edge cases: All checked, none broken
Regressions: None found
Checklist: 6/6 points proven

## Geprüfte Dateien

- sha256:bf454d12eda6eba3cc3c6acf2f4d69dc51e0c3521acfd7f1c91eebc7c6a0bd49  engine/anmeldung.py
- sha256:d5876279295faa38c648ef5fbd7d88e60a253391292727b608934ad96f13b6e6  engine/app/galerie.js
- sha256:46022573caba81ca225305f08984c0694f00cb7d3d575b11b903d847cad83e5a  engine/konnektor.py
- sha256:9eda405bc31ed62842acb27d896c0091e92a58e547e9d927e447e840de721053  engine/texte_de.py
- sha256:2b6f764cf399aa36cb6e7249dc381a4571d572a154997efe795270949cb865c2  engine/texte_en.py

## Prüfbasis

- base: 2a40a98ac99719c7aa31114f37e41c021dec4478
- blob:16005de0f8c35a7d40f21119672b5131e7f56a2d  engine/anmeldung.py
- blob:c6717bab9ad17a83da34f83e5ba8e3bb04c4d9a3  engine/app/galerie.js
- blob:a6eb272a3ffc741adae15bf7adab0eadb775f0bf  engine/konnektor.py
- blob:c50439aaeb78ed32310e2eb8b85b4f087d652f94  engine/texte_de.py
- blob:f7593ca98312249dd84b8adb96e87520155827f7  engine/texte_en.py
