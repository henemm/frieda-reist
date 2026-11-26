---
entity_id: funktionsseiten-711
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-galerie
tags: [infoseite, galerie, photoswipe, funktionen, unterseite, mehrsprachigkeit, baustein]
test_targets: [engine/anmeldung.py, engine/konnektor.py, engine/app/galerie.js, engine/texte_de.py, engine/texte_en.py, engine/info/erzeugen.py, engine/tests/test_infoseite.py, engine/tests/test_funktionsseiten_711.py, engine/tests/info_galerie_711.mjs]
---

# Funktionsseiten unter /info/ und Galerie der Infoseite (#711, Etappe 1)

Workflow: `feat-711-galerie`. Kontext und Analyse: `docs/context/feat-711-galerie.md`.

## GitHub Issue

**Issue:** #711 (Etappe 1: Grundgerüst; die übrigen Unterseiten und der Verweis von GitHub auf die Webseite folgen in eigenen Etappen)

## Approval

- [x] Approved: Entwurf vom Product Owner am 26.11.2026 freigegeben (Artefakt mit den drei Ansichten Startseite, Alle Funktionen, Muster Reiseseite); der Entwurf ist verbindlich für Aufbau, Texte und Aussehen.

## Purpose

Neue Nutzer:innen und Interessenten sollen sich auf der Frieda-Webseite selbst ein Bild machen: Die Bilder der Infoseite lassen
sich durchblättern, und eine Seite „Alle Funktionen“ mit einer Unterseite je Bereich erklärt Frieda mit Bildern, in jeder Sprache
der Software, statt des Links auf eine deutsche Markdown-Datei bei GitHub.

## Prüfstelle (ADR-0001)

Nur Erklärseiten der Software, keine Reisedaten, keine Grundform, keine KI, keine Einstellung einer Reise oder Instanz. Bilder und
Beispiele nur aus den erfundenen Beispielreisen. Texte im Katalog (ADR-0006), vorhandene Bausteine (ADR-0002), Heimat: die
Erklärung eines Bereichs steht auf seiner Unterseite, die Übersicht trägt nur eine Zeile mit Link (ADR-0003).

## Scope

### PR 1: Galerie der Infoseite

1. Die Bilder „So sieht die Reiseseite aus“ stehen als wischbare Reihe (`.bilder.reihe`): am Handy waagerecht mit Einrasten, ein Bild
   rund 62 % breit, darunter schmal „Weitere Bilder: seitlich wischen ›“; ab 640 px vier nebeneinander, ohne Hinweis. Auf jedem
   Bild ein Vergrößern-Symbol.
2. Ein Tipp öffnet PhotoSwipe 5.4.4 (aus `engine/vendor/`, unter `/info/photoswipe-5.4.4.esm.min.js`, lädt erst beim ersten
   Öffnen; Stile in der Seite, weil die CSP nur Inline-Stile erlaubt). Ohne Skript führt der Tipp wie bisher zur großen Fassung.
3. Unterschrift in einem eigenen undurchsichtigen dunklen Streifen unten; das Bild bekommt dort Platz (`paddingFn` oben 56, unten 112),
   der Text liegt nie auf dem Bild. Darunter klein „<Galerie> · Bild i von n“.
4. #706 im neuen Code abgefangen: kommt `change` ohne `currSlide` (Blättern während des Öffnens), bleibt der Streifen stehen und wird
   nach dem Öffnen nachgezogen; keine Skriptfehler.
5. Das Skript `engine/app/galerie.js` unter `/info/galerie.js`, Texte über `data-texte` aus dem Katalog.

### PR 2 und 3 (eigene Workflows, Grenze von 250 Zeilen je Änderung): Alle Funktionen und Muster-Unterseite

6. Auf der Infoseite ersetzt die Karte „Was Frieda alles kann“ mit dem Knopf „Alle Funktionen ansehen“ den Satz mit dem GitHub-Link.
   „Quellcode (AGPL)“ im Fuß bleibt.
7. Neue Seite `/info/funktionen/`: Zurück-Link zur Infoseite, Karte mit Titel und Satz, „Frieda arbeitet an drei Orten“, drei Gruppen
   mit je einer Zeile pro Bereich (Titel und ein Satz), „Wer darf was“. Bereiche ohne Unterseite zeigen die Marke „Seite folgt“ und
   keinen Link.
8. Muster-Unterseite `/info/funktionen/reiseseite/`: Kopf mit Wo/Wer, Galerie, „Was du damit tun kannst“, „So geht's“ als Klappen,
   Gesprächsbeispiel als Sprechblasen, „Wer darf was“, „Gut zu wissen“, „Siehe auch“ (Links auf vorhandene Unterseiten, sonst auf die
   Zeile des Bereichs in der Übersicht).
9. Bilder der Unterseite je Sprache aus den Beispielreisen per `engine/info/erzeugen.py` (mindestens Überblick und Tagesseite, dazu
   Ortsseite und Zu tun).
10. Form für weitere Unterseiten: ein Eintrag in `INFO_UNTERSEITEN` (Bilder, Sprecher des Gesprächs, Siehe auch) und Texte unter
    `info.bereich.<name>.…` in jeder Sprachdatei; nummerierte Listen werden aus dem Katalog gezählt; Bilder über `erzeugen.BILDER`.
    Dokumentiert in `docs/design.md` und `docs/sprachen.md`.
11. Wege: `/info/funktionen` ohne Schrägstrich leitet weiter; ein unbekannter Bereich gibt 404; POST führt ohne Wirkung zurück.

### Nicht im Scope

- Die übrigen Unterseiten (Folge-Etappen), Verweis von `docs/funktionen/` und README auf die Webseite.
- Behebung von #706 in der Großansicht der Reiseseite.
- Neuer nginx-Ort oder Erweiterung der Wegeprüfung (der Ort `^~ /info/` deckt alles ab).

## Acceptance Criteria

- AC-1: Infoseite DE und EN: Bildreihe `.bilder.reihe` mit `data-galerie`, je Bild Link mit `data-breite`/`data-hoehe`, Hinweis zum Wischen; `galerie.js` eingebunden, kein Inline-Skript.
- AC-2: `/info/galerie.js` und `/info/photoswipe-5.4.4.esm.min.js` werden als JavaScript ausgeliefert; andere Namen unter /info/ bleiben 404.
- AC-3 (Browser, Handy 390 px und Rechner 1280 px, DE und EN): am Handy ist die Reihe waagerecht scrollbar, ein Bild 55–70 % der Reihe breit, der Hinweis sichtbar; am Rechner vier Bilder in einer Zeile, ohne Hinweis; nirgends seitlicher Überlauf der Seite.
- AC-4 (Browser): Tipp auf Bild 2 öffnet die Großansicht mit Bild 2; der Streifen zeigt die Unterschrift und „… · Bild 2 von 4“ in der Sprache der Seite, sein Grund ist undurchsichtig, das Bild endet oberhalb des Streifens; Pfeil weiter zeigt Bild 3 und „Bild 3 von 4“; Escape schließt.
- AC-5 (Browser, #706): Pfeil weiter sofort beim Öffnen ergibt keinen Skriptfehler, danach passt der Streifen zum gezeigten Bild.
- AC-11: Die Ausnahmelisten in `test_texte.py` werden nicht länger; alle Tests grün.

## Folgearbeiten (eigene Workflows mit eigener Spec)

- F-6: Infoseite enthält die Karte „Was Frieda alles kann“ mit Knopf nach `/info/funktionen/`, nicht mehr den GitHub-Link der Funktionsübersicht; Quellcode-Link bleibt.
- F-7: `/info/funktionen/` DE und EN: drei Orte, drei Gruppen, jeder Bereich mit Titel und Satz; die Reiseseite als Link, alle anderen mit „Seite folgt“ ohne Link; „Wer darf was“ mit drei Rollen; Sprachumschalter auf derselben Adresse.
- F-8: `/info/funktionen/reiseseite/` DE und EN mit allen Abschnitten; jeder Text kommt aus dem Katalog; die Bilder in der Sprache der Seite; „Siehe auch“ ohne kaputte Links.
- F-9: Wege: `/info/funktionen` → 303 auf `/info/funktionen/`; `/info/funktionen/gibtsnicht/` → 404; POST → 303 auf die Seite; angemeldet Kopf „Mein Konto“.
- F-10: Jede Unterseite und jedes Bild aus `INFO_UNTERSEITEN` hat in jeder Sprache der Software seine Texte; Bilder gibt es für Deutsch und Englisch in den Maßen von `erzeugen`.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/app/galerie.js | CREATE | Galerie mit PhotoSwipe, Unterschrift-Streifen |
| engine/anmeldung.py | MODIFY | Bildreihe, Stile, Dateien unter /info/, Seiten und Routen |
| engine/konnektor.py | MODIFY | /info/-Dateien und -Seiten |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Schlüssel `info.galerie.…`, `info.funktionen.…`, `info.bereich.…`, `info.rolle.…` |
| engine/info/erzeugen.py, engine/info/*.webp | MODIFY/CREATE | Bilder der Unterseite |
| engine/tests/test_infoseite.py, test_funktionsseiten_711.py, info_galerie_711.mjs | MODIFY/CREATE | Tests |
| docs/design.md, docs/sprachen.md | MODIFY | Bausteine und Form der Unterseiten |

## Test Plan

- pytest: Abruf der Seiten in jeder Sprache (Texte, Wege, 404, Weiterleitung, Dateien), Vollständigkeit der Texte und Bilder.
- Browser (Playwright): Infoseite und Unterseite an 390 px und 1280 px, DE und EN: Maße der Reihe, Großansicht, Streifen, Zähler, #706-Fall, keine Seitenfehler.

## Definition of Done

- [ ] Tests zuerst rot, dann grün (pytest und Browser an 390 px und 1280 px, Deutsch und Englisch)
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n auto` grün, darunter Text-, Design- und Betriebstests
- [ ] Neue Bausteine (bildReihe, unterschriftStreifen) in `docs/design.md`; Form der Unterseiten in `docs/design.md` und `docs/sprachen.md`
- [ ] Pull Requests mit grünen Pflichtprüfungen, Vorspulen auf `main`
- [ ] Nach dem Ausliefern auf der Instanz per `curl` geprüft (Infoseite, `/info/galerie.js`, `/info/funktionen/`, Unterseite), Stand im Issue
