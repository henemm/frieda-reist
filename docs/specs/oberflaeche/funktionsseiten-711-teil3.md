---
entity_id: funktionsseiten-711-teil3
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-unterseite
tags: [infoseite, funktionen, unterseite, galerie, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/info/erzeugen.py, engine/tests/test_funktionsseiten_711.py, engine/tests/test_infoseite_galerie_711.py, engine/tests/test_infoseite.py]
---

# Muster-Unterseite „Reiseseite“ und Form der Unterseiten (#711, Etappe 1, Teil 3)

Workflow: `feat-711-unterseite`. Kontext: `docs/context/feat-711-unterseite.md`. Gesamtvorhaben: `docs/specs/oberflaeche/funktionsseiten-711.md`,
Teil 2: `docs/specs/oberflaeche/funktionsseiten-711-teil2.md`.

## GitHub Issue

**Issue:** #711

## Approval

- [x] Approved: Entwurf vom Product Owner am 26.11.2026 freigegeben (Ansicht „Muster: Reiseseite“), verbindlich für Aufbau, Texte
  und Aussehen. Der Entwurf nennt weitere Bilder (Ortsseite, Zu tun) ausdrücklich als Ausbau.

## Purpose

Interessenten sehen auf einer eigenen Seite, was die Reiseseite kann, wie sie aussieht und wie man sie benutzt, mit Bildern aus
den Beispielreisen, in jeder Sprache der Software. Die Seite ist das Muster, nach dem die übrigen Bereiche in Folge-Etappen mit
wenig Code ihre Unterseite bekommen.

## Prüfstelle (ADR-0001)

Nur Erklärseiten, keine Reisedaten, keine Grundform, keine KI; Bilder und Beispiele nur aus den erfundenen Beispielreisen; Texte im
Katalog (ADR-0006); vorhandene Bausteine (ADR-0002); die Erklärung des Bereichs hat hier ihre Heimat, die Übersicht trägt nur die
Zeile mit Link (ADR-0003).

## Scope

1. `/info/funktionen/reiseseite/`: Kopf und Fuß wie die Übersicht, Zurück-Link „‹ Alle Funktionen“, Karte mit Titel, Satz und
   Wo/Wer (`dl.kurz`), „So sieht es aus“ als Galerie (Baustein `bildReihe` aus Teil 1, vier Bilder: Überblick, Tagesseite,
   Ortsseite, Zu tun), „Was du damit tun kannst“ (`ul.darf`), „So geht's“ als Klappen in einer `.liste` (Absätze durch Leerzeile),
   „Im Gespräch“ mit Satz und Sprechblasen, „Wer darf was“ als Liste, „Gut zu wissen“ (`ul.punkte`), „Siehe auch“ als Pillen-Links
   (`.siehe`; ein Bereich mit Unterseite verlinkt diese, sonst seine Zeile in der Übersicht `/info/funktionen/#<bereich>`).
2. In der Übersicht wird „Reiseseite“ zum Link auf die Unterseite (die Marke „Seite folgt“ entfällt dort).
3. Form neuer Unterseiten: ein Eintrag in `INFO_UNTERSEITEN` (`bilder`, `gespraech`, `siehe`), Texte unter
   `info.bereich.<name>.…` in jeder Sprachdatei (nummerierte Listen zählt die Seite im Katalog, kein Zählwert im Code), neue Bilder
   in `engine/info/erzeugen.py` (`BILDER`) und erzeugt mit `engine/info/erzeugen.py`. Beschrieben in `docs/design.md` und `docs/sprachen.md`.
4. Bilder `ort` (Ortsseite Hohnstein der Wanderung) und `zutun` (Zu tun der Wanderung) je Sprache aus den Beispielreisen; das
   Skript prüft, dass es genau die Bilder aller Erklärseiten kennt.

### Nicht im Scope
- Die übrigen Unterseiten (Folge-Etappen), Verweis von GitHub auf die Webseite.

## Acceptance Criteria

- AC-1: `/info/funktionen/reiseseite/` DE und EN: alle Abschnitte aus Scope 1, jeder Text aus dem Katalog (Listen vollständig nach Katalog), Bilder in der Sprache der Seite, „Siehe auch“ ohne kaputte Links, Titel der Seite „Reiseseite – Frieda“ bzw. „Trip page – Frieda“.
- AC-2: Die Übersicht verlinkt die Reiseseite; nur Bereiche ohne Unterseite tragen „Seite folgt“.
- AC-3: Wege: `/info/funktionen/reiseseite` → 303 mit Schrägstrich; POST → 303 zurück; HEAD 200; angemeldet „Mein Konto“ im Kopf; Unterpfade 404.
- AC-4 (Browser, 390 / 1280 / 320 px, DE und EN): die Galerie der Unterseite verhält sich wie die der Infoseite (Reihe, Großansicht, Streifen, Zähler, keine Skriptfehler, kein Überlauf).
- AC-5: Jede Unterseite hat ihre Texte in jeder Sprache der Software; jedes Bild aller Erklärseiten gibt es für Deutsch und Englisch in den Maßen von `erzeugen`; `erzeugen.BILDER` nennt genau diese Bilder.
- AC-6: Die Ausnahmelisten in `test_texte.py` werden nicht länger; alle Tests grün.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | Unterseite, Datenform, Route, Stile `.kurz`, `.siehe` |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der Unterseite |
| engine/info/erzeugen.py, engine/info/ort-*.webp, zutun-*.webp | MODIFY/CREATE | Bilder |
| engine/tests/test_funktionsseiten_711.py, test_infoseite_galerie_711.py, test_infoseite.py | MODIFY | Tests |
| docs/design.md, docs/sprachen.md | MODIFY | Unterseite und Form |

## Test Plan

- pytest: Unterseite DE/EN mit allen Abschnitten, Wege, Vollständigkeit von Texten und Bildern.
- Browser: Galerie-Test auch auf der Unterseite.

## Definition of Done

- [ ] Tests zuerst rot, dann grün
- [ ] Gezielte Tests lokal grün, CI grün, Vorspulen auf `main`
- [ ] Doku nachgezogen
- [ ] Nach dem Ausliefern auf der Instanz per `curl` geprüft, Stand im Issue
