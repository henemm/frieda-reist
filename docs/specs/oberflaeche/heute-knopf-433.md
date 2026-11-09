---
entity_id: heute-knopf-433
type: module
created: 2026-11-09
updated: 2026-11-09
status: approved
version: "0.1"
tags: [oberflaeche, leiste, unterwegs, tagesseite, heimat]
---

# Leiste: Knopf „Heute“, solange die Reise unterwegs ist (#433)

## Approval

- [x] Approved (Product Owner, 9.11.2026, zwei Entscheidungen per AskUserQuestion im Issue: Knopf nur unterwegs;
  Kasten „Heute · Tag N“ weg, Start auf Heute). Die offene Frage „kein heutiger Tag im Plan“ entscheidet der Tech Lead
  nach dem Vorschlag im Issue: Start auf „Reise“, Knopf ausgeblendet.

## Purpose

Unterwegs will man mit einem Tipp den heutigen Tag sehen. Bisher stand er als Kasten oben im Reiter „Reise“, über der
Karte; das war eine zweite Darstellung des Tags (gegen ADR-0003) und machte „Reise“ unterwegs unruhig.

## Verhalten

- **Heutiger Tag:** Status mit `verhalten.start: heute` (nur `unterwegs`), die Reise hat Tage, und ein Tag hat das
  heutige Datum (Ortszeit des Geräts). Sonst gibt es keinen heutigen Tag.
- **Knopf:** Gibt es einen heutigen Tag, steht in der Leiste ganz vorn „Heute“ (Symbol Kalender, Link `#heute`).
  Er führt auf die Tagesseite dieses Tags, ihre eine Heimat. Auf dieser Tagesseite ist „Heute“ der gewählte Reiter,
  egal ob über `#heute` oder über die Kennung des Tags erreicht. Ohne heutigen Tag fehlt der Knopf.
- **Start:** Ohne Sprungziel öffnet die Seite mit heutigem Tag dessen Tagesseite, sonst wie bisher (unterwegs: „Reise“).
- **`#heute` ohne heutigen Tag** (alter Link, Reise vorbei): wie ohne Sprungziel.
- **Kasten weg:** Der Reiter „Reise“ und der Vergleich der Pläne zeigen unterwegs keinen Kasten „Heute“ mehr; „Reise“
  sieht in jedem Status gleich aus (bis auf Zähler und Stand der Vorbereitung, wie bisher).
- Der Tageswechsel um Mitternacht gilt beim nächsten Seitenwechsel (die Leiste wird bei jedem Wechsel neu gezeichnet).

## Gilt für

- Wanderung (Beispielreise) und Städtewochenende: gleich, beide haben Tage mit Datum.
- Reise ohne Pläne oder ohne Tage: kein Knopf, Start wie bisher.
- Der Konnektor (`ueberblick` nennt unterwegs den heutigen Tag) bleibt unverändert.

## Texte (ADR-0006)

- neu `seite.reiter.heute` („Heute“ / „Today“).
- entfallen `seite.plan.heute`, `seite.plan.heute_tag`, `seite.plan.heute_kein_tag` (nur der Kasten nutzte sie).

## Bausteine (ADR-0002)

Kein neuer Baustein: Der Knopf ist ein Reiter der Leiste (`zeigeReiter`). `heuteBlock` entfällt (auch aus der
Ausnahmeliste in `test_design.py`). Symbol `heute` (Lucide `calendar-days`, schon im Satz).

## Tests

`engine/tests/test_seite.py::test_seite_je_status_und_baustein` (Chromium und WebKit) mit `seiten_variante.mjs`:
- planung: kein „heute“ in der Leiste, Start auf „Reise“.
- unterwegs am 1. Reisetag: „heute“ steht vorn, ist gewählt, die Seite zeigt die Tagesseite von Tag 1; kein Kasten.
  Über die Kennung desselben Tags ist „Heute“ gewählt, „Reise“ zeigt keinen Kasten.
- unterwegs ohne heutigen Tag: kein Knopf, Start auf „Reise“, `#heute` landet auf „Reise“.
