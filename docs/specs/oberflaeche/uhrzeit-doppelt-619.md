---
entity_id: uhrzeit-doppelt-619
type: bugfix
created: 2026-11-22
updated: 2026-11-22
status: draft
workflow: fix-619-uhrzeit-doppelt
tags: [oberflaeche, konnektor, kalender, zeit, anzeige]
---

# Uhrzeit nicht doppelt anzeigen (#619)

## Approval

- [ ] Approved

## Purpose

Hat ein Aufenthalt oder eine Unterkunft einen freien Zeittext (`zeit`) und ein strukturiertes Zeitfenster (`beginn`/`ende`, gefaltet aus dem Merkmal `zeitraum`), steht die Uhrzeit heute doppelt auf der Seite und im Konnektor („nach der Wanderung, 16–18 Uhr · 16:00–18:00 Uhr“). Künftig erscheint das Zeitfenster einmal, der Freitext nur mit dem, was er darüber hinaus sagt.

## Source

- **File:** `engine/routen.py`
- **Identifier:** `def zeit_ohne_uhr` (neu); Nutzer: `engine/bauen.py`, `engine/vorlage.html`, `engine/konnektor.py` (`aufenthalt`), `engine/kalender.py`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `routen.lage_merkmale_falten` | function | liefert die gefalteten Felder `beginn`/`ende` |
| `bauen.py` Nachbearbeitung der Seitendaten | module | trägt das Anzeigefeld `zeit_rest` je Aufenthalt und Unterkunft ein (Muster wie `ohne_tag`) |
| Textschlüssel `seite.zeit.uhr` | text | Einheitswort (Text ohne `{zeit}`), damit der Code keine Sprache kennt (ADR-0006) |
| `konnektor.ausgabe.uhr` | text | bisherige Darstellung des Zeitfensters im Konnektor, bleibt |
| ADR-0007 | adr | typisierte Merkmale (`zeitraum`) |
| ADR-0001 | adr | Kern: nichts Reisespezifisches in der Engine |

## Scope

### Affected Files
| File | Change Type | Description |
|------|-------------|-------------|
| engine/routen.py | MODIFY | reine Hilfsfunktion `zeit_ohne_uhr(zeit, beginn, ende, einheit)` |
| engine/bauen.py | MODIFY | Anzeigefeld `zeit_rest` neben `zeit` in den Seitendaten (Aufenthalt, Unterkunft) |
| engine/vorlage.html | MODIFY | die drei Etiketten (Aufenthaltszeile, Unterkunftskarte, Zeile ohne Tag) lesen `zeit_rest ?? zeit` |
| engine/konnektor.py | MODIFY | `aufenthalt` (show und Tagestext) nutzt die Funktion |
| engine/kalender.py | MODIFY | Termintext ohne die doppelte Uhrzeit, wenn der Termin selbst eine Uhrzeit trägt |
| engine/tests/test_zeit_doppelt.py | CREATE | Hilfsfunktion, Seite, Konnektor, Kalender an beiden Beispielreisen |

### Estimated Changes
- Files: 6 (5 MODIFY, 1 CREATE)
- LoC: +90/-6

## Implementation Details

Eine Funktion an einer Stelle (Python); die Vorlage rechnet nichts, sie liest nur das Feld.

**`zeit_ohne_uhr(zeit, beginn, ende, einheit)`** gibt den Anzeigetext des Freitexts zurück.
- Der Freitext wird an `,`, `;` und `·` in Teilstücke zerlegt.
- Ein Teilstück fällt nur weg, wenn es ausschließlich eine Uhrzeitangabe ist: Zeiten der Form `H`, `HH`, `H:MM`, `HH.MM`, höchstens ein Bereichsstrich (`–` oder `-`) und das Einheitswort; kein weiteres Wort („ab“, „gegen“ und Ähnliches bleiben, sie tragen Bedeutung).
- Die Zeiten müssen genau zu `beginn` bzw. `beginn` und `ende` passen (Minuten `:00` dürfen fehlen). Eine Angabe mit nur einer Zeit passt, wenn diese Zeit gleich `beginn` ist (mit oder ohne `ende`); eine Angabe mit zwei Zeiten passt nur, wenn sie gleich `beginn` und `ende` sind. Widerspricht die Angabe dem Fenster, bleibt der Text stehen („nie verstecken“).
- Das Einheitswort ist der Text aus `seite.zeit.uhr` ohne `{zeit}` (de „Uhr“, en leer). Der Code kennt keine Sprache beim Namen; bei leerem Einheitswort gilt dieselbe Regel ohne Wort.
- Bleibt nach dem Entfernen nichts übrig, ist das Ergebnis leer (der Freitext entfällt). Ohne `beginn` wird nichts verändert. Im Zweifel bleibt der Freitext unverändert: im ungünstigsten Fall doppelt wie bisher, nie falsch.

**Gespeicherte Daten bleiben unverändert.** Nur die Anzeige ändert sich; kein Formatwechsel, daher kein Eintrag in `neu.py nachziehen`.

**Kalender:** Der Termin trägt die Uhrzeit selbst; im Termintext steht `zeit` nur noch mit dem, was die Funktion übrig lässt.

**Buchungsliste** (`[datum, art, zeit]`, zeigt `uhrText` nicht) bleibt unverändert.

## Test Plan

### Automated Tests (TDD RED)

In `engine/tests/test_zeit_doppelt.py`:

- [ ] Test 1: GIVEN Freitext „nach der Wanderung, 16–18 Uhr“, beginn 16:00, ende 18:00, Einheit „Uhr“ WHEN `zeit_ohne_uhr` THEN „nach der Wanderung“.
- [ ] Test 2: GIVEN Freitext „13 Uhr“, beginn 13:00, ende 15:00 WHEN `zeit_ohne_uhr` THEN leerer Text.
- [ ] Test 3: GIVEN „Sonntag Vormittag“ oder „ab 16 Uhr“ (beginn 16:00) WHEN `zeit_ohne_uhr` THEN jeweils unverändert.
- [ ] Test 4: GIVEN „17–19 Uhr“ bei 16:00–18:00 sowie ein Freitext ohne `beginn` WHEN `zeit_ohne_uhr` THEN jeweils unverändert.
- [ ] Test 5: GIVEN die Pseudo-Sprache der Tests und en mit leerem Einheitswort WHEN `zeit_ohne_uhr` mit „16–18“ bei 16:00–18:00 THEN die Uhrzeit entfällt, ohne dass der Code eine Sprache kennt.
- [ ] Test 6: GIVEN die gebaute Seite der Beispielreise (A-01) und des Stadtwochenendes WHEN die Seitendaten gelesen werden THEN `zeit_rest` ist „nach der Wanderung“ bzw. leer, `zeit` bleibt unverändert, und die Etiketten zeigen das Zeitfenster genau einmal.
- [ ] Test 7: GIVEN beide Beispielreisen WHEN Konnektor `show` für A-01 und den Aufenthalt des Stadtwochenendes sowie der Tagestext laufen THEN die Uhrzeit kommt je einmal vor.
- [ ] Test 8: GIVEN beide Beispielreisen WHEN der Kalender gebaut wird THEN der Termintext enthält die Uhrzeit nicht zusätzlich zum Termin.
- [ ] Test 9: GIVEN die Reisedaten (`routen.yaml`) WHEN gebaut THEN bleiben `zeit`, `beginn` und `ende` unverändert gespeichert.

## Acceptance Criteria

- **AC-1:** Given ein Aufenthalt mit Freitext „nach der Wanderung, 16–18 Uhr“ und Zeitfenster 16:00–18:00 / When die Anzeige berechnet wird / Then lautet der Freitext „nach der Wanderung“; bei „13 Uhr“ und 13:00–15:00 entfällt der Freitext ganz.
- **AC-2:** Given „Sonntag Vormittag“, „ab 16 Uhr“ (16:00), „17–19 Uhr“ bei 16:00–18:00 oder ein Freitext ohne Beginn / When die Anzeige berechnet wird / Then bleibt der Freitext unverändert.
- **AC-3:** Given eine Sprache mit anderem oder leerem Einheitswort (en, Pseudo-Sprache der Tests) / When „16–18“ bei 16:00–18:00 angezeigt wird / Then entfällt die Uhrzeit, ohne dass der Code eine Sprache beim Namen kennt; das Einheitswort kommt aus `seite.zeit.uhr`.
- **AC-4:** Given beide Beispielreisen (Beispielreise A-01, Stadtwochenende) / When Seite, Konnektor `show`, Tagestext und Kalender erzeugt werden / Then steht die Uhrzeit je Aufenthalt genau einmal.
- **AC-5:** Given eine gebaute Reise / When die Reisedaten danach gelesen werden / Then sind `zeit`, `beginn` und `ende` unverändert gespeichert; kein `nachziehen` nötig.
- **AC-6:** Given die vollständige Testsuite / When `engine/.venv/bin/python -m pytest -q engine/tests` läuft / Then ist sie grün, einschließlich `test_texte.py` und `test_design.py` (kein neuer Baustein, kein neuer Text).

## Definition of Done

- [ ] Alle Tests in `engine/tests/test_zeit_doppelt.py` grün, volle Testsuite grün (lokal und CI).
- [ ] Abnahme an beiden Beispielreisen: Seite, Konnektor `show`, Tagestext und Kalender zeigen die Uhrzeit je einmal.
- [ ] Ausgeliefert und auf der Instanz veröffentlicht; Issue #619 erst danach geschlossen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** reine Anzeigekorrektur innerhalb bestehender Regeln (ADR-0003 eine Heimat, ADR-0006 Texte im Katalog, ADR-0007 Merkmale); keine neue Grundform, kein Formatwechsel, daher keine eigene Entscheidung nötig.

## Changelog

- 2026-11-22: Initial spec created
