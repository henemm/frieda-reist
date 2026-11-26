---
entity_id: funktionsseiten-711-teil2
type: feature
created: 2026-11-26
updated: 2026-11-26
status: draft
version: "1.0"
workflow: feat-711-funktionen
tags: [infoseite, funktionen, uebersicht, mehrsprachigkeit]
test_targets: [engine/anmeldung.py, engine/texte_de.py, engine/texte_en.py, engine/instanz.py, engine/tests/test_funktionsseiten_711.py, engine/tests/test_infoseite.py]
---

# Seite „Alle Funktionen“ unter /info/funktionen/ (#711, Etappe 1, Teil 2)

Workflow: `feat-711-funktionen`. Kontext: `docs/context/feat-711-funktionen.md`. Gesamtvorhaben und Teil 1 (Galerie, ausgeliefert):
`docs/specs/oberflaeche/funktionsseiten-711.md`.

## GitHub Issue

**Issue:** #711

## Approval

- [x] Approved: Entwurf vom Product Owner am 26.11.2026 freigegeben (Ansichten „Startseite“ und „Alle Funktionen“), verbindlich
  für Aufbau, Texte und Aussehen.

## Purpose

Neue Nutzer:innen und Interessenten finden von der Infoseite aus eine Übersicht aller Funktionen auf der Frieda-Webseite selbst,
in jeder Sprache der Software, statt eines Links auf eine deutsche Markdown-Datei bei GitHub.

## Prüfstelle (ADR-0001)

Nur Erklärseiten der Software, keine Reisedaten, keine Grundform, keine KI. Texte im Katalog (ADR-0006). Heimat (ADR-0003): jeder
Bereich hat auf der Übersicht genau eine Zeile; seine Erklärung gehört auf seine Unterseite (Teil 3 und Folge-Etappen).

## Scope

1. Infoseite: Die Karte „Was Frieda alles kann“ (`.karte.einstieg`, Satz, Knopf „Alle Funktionen ansehen“ nach `/info/funktionen/`)
   ersetzt den Satz mit dem GitHub-Link. „Quellcode (AGPL)“ im Fuß bleibt. Reihenfolge wie im Entwurf: So funktioniert Frieda,
   So sieht die Reiseseite aus, Was Frieda alles kann, Beispiele aus dem Gespräch, Erste Schritte.
2. Neue Seite `/info/funktionen/`: Kopf wie die Infoseite, Zurück-Link „‹ Was ist Frieda?“, Karte mit Titel und Satz,
   „Frieda arbeitet an drei Orten“ als drei kleine Karten, drei Gruppen (Planen und entscheiden; Unterwegs und gemeinsam; Konto und
   Betrieb) mit je einer Zeile je Bereich (Titel und ein Satz). Bereiche ohne Unterseite tragen die Marke „Seite folgt“ und keinen
   Link; jede Zeile hat den Bereich als Anker. „Wer darf was“ mit Gast, Mitwirkende:r, Organisator:in.
3. Datenform: `INFO_ORTE`, `INFO_GRUPPEN`, `INFO_ROLLEN`, `INFO_UNTERSEITEN` (Bereiche mit Unterseite; in Teil 2 leer) in
   `engine/anmeldung.py`, Texte unter `info.ort.…`, `info.gruppe.…`, `info.bereich.<b>.titel/.satz`, `info.rolle.…`.
4. Wege: `/info/funktionen` (ohne Schrägstrich) leitet mit 303 auf `/info/funktionen/` (Sprache bleibt); `/info/funktionen/<x>/`
   ohne Unterseite gibt 404; POST führt ohne Wirkung zurück; HEAD wie GET; angemeldet steht „Mein Konto“ im Kopf. Kein neuer
   nginx-Ort (`^~ /info/` führt schon zum Dienst).
5. Aufräumen: `info.funktionen.satz/.link/.datei` und `instanz.quellcode_datei` entfallen (nur noch für den GitHub-Link genutzt).

### Nicht im Scope
- Unterseite „Reiseseite“ (Teil 3), weitere Unterseiten (Folge-Etappen), Verweis von GitHub auf die Webseite.

## Acceptance Criteria

- AC-1: Infoseite DE und EN, an `/` und `/info/`: Karte `.karte.einstieg` mit Titel, Satz und Knopf nach `/info/funktionen/`; kein Link auf `docs/funktionen` oder `README.en.md`; „Quellcode (AGPL)“ bleibt im Fuß.
- AC-2: `/info/funktionen/` DE und EN: Titel der Seite, Zurück-Link, Satz, drei Orte, drei Gruppen, jeder Bereich mit Titel, Satz und Anker; Bereiche ohne Unterseite mit „Seite folgt“ und ohne Link; „Wer darf was“ mit drei Rollen; Sprachumschalter auf derselben Adresse; alle Texte aus dem Katalog.
- AC-3: Wege: ohne Schrägstrich 303 (mit Sprache); unbekannter oder noch nicht vorhandener Bereich 404; POST 303 zurück; HEAD 200; angemeldet „Mein Konto“ im Kopf.
- AC-4 (Browser, 390 px und 1280 px, DE und EN): kein seitlicher Überlauf, keine Skriptfehler; am Handy die drei Orte untereinander, am Rechner nebeneinander; jede Zeile mindestens 44 px hoch.
- AC-5: Die Ausnahmelisten in `test_texte.py` werden nicht länger; alle Tests grün.

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | Karte auf der Infoseite, Seite „Alle Funktionen“, Datenform, Wege |
| engine/texte_de.py, engine/texte_en.py | MODIFY | neue Schlüssel, drei entfallen |
| engine/instanz.py, engine/tests/texte_xx.py | MODIFY | `quellcode_datei` und Sonderfall entfallen |
| engine/tests/test_funktionsseiten_711.py | CREATE | Tests |
| engine/tests/test_infoseite.py | MODIFY | Test des GitHub-Links entfällt |
| docs/design.md, docs/sprachen.md | MODIFY | Infoseite, Abschnitt Funktionsseiten |

## Test Plan

- pytest: Abruf von Infoseite und Übersicht in jeder Sprache (Texte, Links, Anker, Marken), Wege, angemeldet.
- Browser (Playwright, Chromium): Übersicht an 390 und 1280 px, DE und EN.

## Definition of Done

- [ ] Tests zuerst rot, dann grün
- [ ] Gezielte Tests lokal grün, CI grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Vorspulen auf `main`
- [ ] `docs/design.md` und `docs/sprachen.md` nachgezogen
- [ ] Nach dem Ausliefern auf der Instanz per `curl` geprüft
