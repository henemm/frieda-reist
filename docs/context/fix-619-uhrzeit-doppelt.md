# Context: fix-619-uhrzeit-doppelt

## Request Summary
Issue #619: Ein Aufenthalt (oder eine Unterkunft) mit freiem Zeittext `zeit` und strukturiertem Zeitfenster (Merkmal Typ
`zeitraum`, gefaltet zu `beginn`/`ende`) zeigt die Uhrzeit doppelt: Seite „Besichtigung · nach der Wanderung, 16–18 Uhr ·
16:00–18:00 Uhr“, Konnektor `show A-01` „…, nach der Wanderung, 16–18 Uhr, 16:00–18:00 Uhr“. Ziel: Zeitfenster einmal,
Freitext nur mit dem, was er darüber hinaus sagt.

## Related Files
| File | Relevance |
|------|-----------|
| engine/routen.py:349 `lage_merkmale_falten` | faltet Merkmal `zeitraum` in `beginn`/`ende`; Ort für eine reine Hilfsfunktion |
| engine/vorlage.html:2025 `uhrText` | formatiert `beginn–ende` als „16:00–18:00 Uhr“ |
| engine/vorlage.html:2094 `aufenthaltZeile`, 2272 Unterkunftskarte, 3743 `ohneTagZeile` | Etikett `[art, zeit, uhrText]` → doppelt |
| engine/vorlage.html:3867 Buchungsliste | `[datum, art, zeit]` ohne uhrText |
| engine/konnektor.py:921 `aufenthalt` | `[name, art, zeit, uhr]` → doppelt (show, Tagestext) |
| engine/bauen.py:1191 / 1432 | Nachbearbeitung der Seitendaten je Aufenthalt/Unterkunft (Muster für eine weitere) |
| engine/kalender.py:135, 158 | nutzt `zeit` als Text im Kalender (Termin hat dort selbst Uhrzeit) |
| beispiel/reisen/beispielreise/plan/routen.yaml:143 | A-01 mit `zeit` „nach der Wanderung, 16–18 Uhr“ und `zeitraum` 16:00–18:00 |

## Existing Patterns
- Seitendaten werden in bauen.py nachbearbeitet (z. B. `ohne_tag`, `lesetext_herkunft`) — die Vorlage liest nur Felder.
- Gefaltete Lage-Felder (`beginn`, `ende`) stehen im Routenmodell, das Konnektor und Seite gemeinsam lesen.

## Dependencies
- Upstream: Routenmodell (gefaltete Felder), Texte `seite.zeit.uhr`, `konnektor.ausgabe.uhr`.
- Downstream: Seite (Etiketten), Konnektor (show, Tagestext), Kalender.

## Existing Specs
- keine eigene Spec zur Zeitanzeige; docs/design.md (Etikett), ADR-0007 (typisierte Merkmale).

## Risks & Considerations
- Gespeicherte Daten dürfen nicht verändert werden (nur die Anzeige).
- Erkennung der Uhrzeit im Freitext ist heuristisch: nur entfernen, was zu beginn/ende passt; im Zweifel Freitext stehen lassen.
- Freitext kann in anderer Sprache sein (Reise-Sprache); nicht erkannte Formen bleiben unverändert (doppelt, aber nie falsch).

## Analysis

### Type
Bug (Anzeige; gespeicherte Daten bleiben unverändert)

### Ursache
Freitext `zeit` und das gefaltete Zeitfenster (`beginn`/`ende` aus Merkmal `zeitraum`) werden an vier Stellen
ungeprüft nebeneinander ausgegeben: Vorlage `aufenthaltZeile` (2094), Unterkunftskarte (2272), `ohneTagZeile` (3743)
und Konnektor `aufenthalt` (921). Kalender (kalender.py:158) schreibt `zeit` in den Termintext, obwohl der Termin
selbst die Uhrzeit trägt. Beide Beispielreisen zeigen es: Beispielreise A-01 „nach der Wanderung, 16–18 Uhr“ +
16:00–18:00; Stadtwochenende „13 Uhr“ + 13:00–15:00.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/routen.py | MODIFY | reine Hilfsfunktion `zeit_ohne_uhr(zeit, beginn, ende, einheit)`: entfernt aus dem Freitext nur Teilstücke (getrennt an `,` `;` `·`), die ausschließlich eine Uhrzeitangabe sind, deren Stunden/Minuten zu beginn (und ende) passen; Einheit kommt aus dem Textkatalog |
| engine/bauen.py | MODIFY | Seitendaten je Aufenthalt/Unterkunft: Feld `zeit_rest` (Anzeigetext) neben `zeit`, analog `ohne_tag` |
| engine/vorlage.html | MODIFY | drei Etiketten lesen `zeit_rest ?? zeit` statt `zeit` |
| engine/konnektor.py | MODIFY | `aufenthalt` nutzt die Hilfsfunktion |
| engine/kalender.py | MODIFY | Termintext ohne die doppelte Uhrzeit, wenn der Termin eine Uhrzeit hat |
| engine/tests/test_zeit_doppelt.py | CREATE | Hilfsfunktion (Fälle unten), Seite und Konnektor an beiden Beispielreisen |

### Scope Assessment
- Files: 6 (5 MODIFY, 1 CREATE)
- Estimated LoC: +90/-6
- Risk Level: LOW — nur Anzeige, konservative Erkennung; nicht erkannte Formen bleiben wie heute

### Technical Approach
Eine Funktion an einer Stelle (Python), Ergebnis als Anzeigefeld in die Seitendaten; die Vorlage rechnet nichts.
Erkennungsregel (konservativ): Teilstück ohne Einheitswort und ohne Leerraum-Rand besteht nur aus Uhrzeiten
(`H`, `HH`, `H:MM`, `HH.MM`) und höchstens einem Trenner (`–`, `-`, `bis`-frei: nur Zeichen), und die Zeiten sind
genau beginn bzw. beginn+ende (Minuten :00 dürfen fehlen). Einheitswort = Text aus `seite.zeit.uhr` ohne `{zeit}`
(de „Uhr“, en leer) — so kennt der Code keine Sprache. Bleibt nach dem Entfernen nichts übrig, entfällt der Freitext.
Fälle: „nach der Wanderung, 16–18 Uhr“ → „nach der Wanderung“; „13 Uhr“ (13:00–15:00) → „“; „Sonntag Vormittag“ → unverändert;
„ab 16 Uhr“ → unverändert (Wort „ab“ trägt Bedeutung); „17–19 Uhr“ bei 16:00–18:00 → unverändert (widerspricht, nie verstecken);
ohne beginn → unverändert.
Bewusst nicht: `nachziehen` oder Änderung gespeicherter Daten (kein Formatwechsel).

### Dependencies
Routenmodell (gefaltete Felder) → bauen.py (Seitendaten) → vorlage.html; konnektor.py und kalender.py lesen dasselbe Modell.
Texte `seite.zeit.uhr` (de/en, Pseudo-Sprache der Tests beachten).

### Open Questions
- keine (Produktverhalten im Issue vorgegeben: Zeitfenster einmal, Freitext nur mit dem, was er mehr sagt)
