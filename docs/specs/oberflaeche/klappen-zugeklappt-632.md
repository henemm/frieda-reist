---
entity_id: klappen-zugeklappt-632
type: bugfix
created: 2026-11-23
updated: 2026-11-23
status: draft
workflow: fix-632-zugeklappt
tags: [oberflaeche, klappen, details, pfeil, progressive-disclosure]
---

# Klappen starten zu, ein Pfeil für die ganze Seite (#632)

## Approval

- [ ] Approved

## Purpose

Mehrere aufklappbare Bereiche der Reiseseite starten heute offen (Einzelheiten eines Dings, erster Abschnitt eines Wissenstextes, „Andere erwogene Pläne“, Wunschformular), und der Pfeil der Tageskapitel bedeutet das Gegenteil des Pfeils aller anderen Klappen: Eine offene Klappe sieht aus wie ein zugeklapptes Kapitel. Künftig gilt eine Regel für die ganze Seite: Beim Laden ist zu, nur der Kern der Ansicht ist offen, und Pfeil nach rechts heißt zu, Pfeil nach unten heißt offen.

## Source

- **File:** `engine/vorlage.html`
- **Identifier:** CSS `details.kapitel` (Zeilen 704–705); `function einzelheiten` (2410) mit den Aufrufern in `planungsTeil` (2257) und `buchungBlock` (2457); `function block` (1758) mit dem Aufruf in Zeile 1818; `details.weg` in `ansichtVarianten` (3664); `details.wu-neu` (5751)

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| Pico 2.1.1 (`engine/vendor`) | vendor | liefert den Pfeil aller übrigen Klappen (zu: nach rechts, offen: nach unten); bleibt unverändert und ist die Vorgabe der Seite |
| `plKlapper`, `packTabelle`, `packGruppe` | molecule | Packliste bleibt unverändert (#511); Kern: Arbeitsfläche |
| Sprung-Öffnen (Zeilen ~3540, ~4763, ~6566) | function | öffnet beim Sprung (Hash, „zu buchen“, Suche) alle umgebenden `details`; bleibt und sichert den Zugang zu Zugeklapptem |
| `docs/design.md` (Stand-Leiter vom 31.10.2026) | doc | die Regel „Einzelheiten offen bis zur Buchung“ wird durch diese Entscheidung ersetzt |
| `seiten_tagesseite.mjs`, `seiten_buchung_zeitraum.mjs`, `seiten_variante.mjs`, `seiten_ding_lesetext.mjs`, `seiten_packliste.mjs`, `namen_browser.mjs`, `test_seite.py` | tests | prüfen heute Klappzustände und werden angepasst |
| ADR-0001, ADR-0002, ADR-0003 | adr | Kern, Atomic Design (kein neuer Baustein), eine Heimat je Grundform |

## Scope

### Affected Files
| File | Change Type | Description |
|------|-------------|-------------|
| engine/vorlage.html | MODIFY | `details.kapitel`: Pfeil wie Pico (zu rechts, offen unten); Einzelheiten (Ding und Buchung) starten zu, auch ungebucht; erster Wissensabschnitt zu; `details.weg` der erwogenen Pläne zu; `wu-neu` offen nur mit angefangenem Entwurf; Erklärtexte der Bausteinseite (~5065, ~5154); Kopfkommentar der Vorlage |
| docs/design.md | MODIFY | Moleküle `einzelheiten` und `plKlapper`, Abschnitt Stand-Leiter: neue Regel „beim Laden zu, offen nur der Kern“ und eine Pfeil-Konvention |
| engine/tests/seiten_tagesseite.mjs | MODIFY | erwartete `open`-Werte der Einzelheiten (Zeilen 54, 142–151) |
| engine/tests/seiten_buchung_zeitraum.mjs | MODIFY | `einzelheiten_zu` bleibt, gilt jetzt auch ungebucht |
| engine/tests/seiten_variante.mjs | MODIFY | `details.weg` der erwogenen Pläne beim Laden zu; Inhalt erst nach dem Aufklappen |
| engine/tests/seiten_ding_lesetext.mjs | MODIFY | Quelle-Zeile in den Einzelheiten erst nach dem Aufklappen prüfen |
| engine/tests/namen_browser.mjs | MODIFY | Einzelheiten der Buchung ohne Annahme „offen“ |
| engine/tests/seiten_packliste.mjs | MODIFY | nur falls eine Erwartung am Pfeil oder an Nachbarklappen hängt; Verhalten der Packliste bleibt |
| engine/tests/test_seite.py | MODIFY | Auswertung der angepassten Skripte |
| engine/tests/klappen_browser.mjs, engine/tests/test_klappen_zugeklappt.py | CREATE | Regeltest (nichts außerhalb des Kerns offen) und Pfeiltest, an beiden Beispielreisen |
| engine/texte_*.py | NONE | nach heutigem Stand stehen die Erklärtexte der Bausteinseite in der Vorlage, nicht im Katalog; stünde einer im Katalog, wird er in allen Sprachen angepasst |

### Estimated Changes
- Files: 11 (9 MODIFY, 2 CREATE)
- LoC: +140/-35 (überwiegend Tests)

## Implementation Details

Reine Darstellung; kein Formatwechsel der Reisedaten, daher kein Eintrag in `neu.py nachziehen`. Es entsteht kein neuer Baustein und kein neuer Text.

**Pfeil.** Nur `details.kapitel` ändert sein CSS (Zeilen 704–705): zu zeigt den Pfeil nach rechts, offen nach unten, also dieselbe Bedeutung wie der Pico-Pfeil aller übrigen Klappen. Pico selbst bleibt unverändert. Die Vorschau (`.kap-vorschau`, Zeile 709) und die Bedienung der Kapitel bleiben.

**Beim Laden zu:**
- `einzelheiten(…)`: startet immer zu, auch ungebucht. Das ersetzt „offen bis zur Buchung“ der Stand-Leiter vom 31.10.2026. Der Parameter `offen` entfällt (neue Signatur `einzelheiten(inhalt, titel)`); alle Aufrufer (Ding in `planungsTeil`, Buchung in `buchungBlock`, Bausteinseite) werden angepasst. So steht der Startzustand an genau einer Stelle, und kein Aufrufer kann ihn versehentlich wieder auf offen setzen.
- `block(b, i === 0, …)`: der erste Abschnitt eines Wissens- oder Recherchetextes startet zu wie die übrigen.
- `details.weg` „Andere erwogene Pläne“ (3664): kein `open` mehr.
- Wunschformular `wu-neu` (5751): `open` nur, wenn ein angefangener Entwurf der Person vorliegt (`WU_ENTWURF.text`); nicht mehr, weil die Wunschliste leer ist.

**Offen bleibt der Kern:** das gemerkte Tageskapitel, die Packliste (Planen: Tabelle je Kategorie offen; Packen: Gruppe offen, solange nicht alles Eigene gepackt ist; das Gerät merkt jede Abweichung, #511) und das Wunschformular mit Entwurf.

**Was sichtbar bleibt, auch bei zugeklappten Einzelheiten:** Name, Datum, Stand, Frist, Preis und die Buchen-Handlung stehen schon heute außerhalb der Einzelheiten und bleiben dort. In den Einzelheiten stehen Merkmale, Herkunft („Quelle“-Zeile), Belege, Verlauf.

**Sprünge.** Hash-Sprung, „zu buchen“ und Suche öffnen weiter alle umgebenden `details` (Zeilen ~3540, ~4763, ~6566). Dieser Weg ist unverändert und wird für zugeklappte Einzelheiten durch einen Test gesichert.

**Doku.** `docs/design.md` (Moleküle `einzelheiten` und `plKlapper`, Stand-Leiter), die Erklärtexte der Bausteinseite („offen, solange gehandelt wird, zu ab der Buchung“ im Muster der Einzelheiten) und der Kopfkommentar der Vorlage (Zeilen 2408–2409 und die Beschreibung der Kapitel) nennen die neue Regel und die eine Pfeil-Konvention.

## Expected Behavior

- **Input:** eine gebaute Seite beider Beispielreisen, Ansicht frisch geladen, ohne gemerkte Zustände und ohne Sprung.
- **Output:** außer dem gemerkten Tageskapitel, der Packliste und einem Wunschformular mit Entwurf ist keine Klappe offen. Der Pfeil nach rechts steht für zu, der nach unten für offen, bei Kapiteln und allen übrigen Klappen gleich.
- **Side effects:** keine; es werden keine Daten gespeichert oder verändert. Ein Sprung auf ein Ding in zugeklappten Einzelheiten öffnet sie.

## Test Plan

### Automated Tests (TDD RED)

In `engine/tests/test_klappen_zugeklappt.py` mit `engine/tests/klappen_browser.mjs` (Muster wie `test_seite.py`), jeweils an `beispiel/reisen/beispielreise` und `beispiel/reisen/stadtwochenende`:

- [ ] Test 1: GIVEN eine gebaute Beispielreise, frisch geladen WHEN alle `details` der Seite gezählt werden THEN ist keine Klappe offen außer Tageskapitel (gemerkt), Packliste (`details.pack-klapper`) und Wunschformular mit Entwurf.
- [ ] Test 2: GIVEN `details.kapitel` und eine Pico-Klappe (etwa `details.einzelheiten`) WHEN die berechnete Transformation von `summary::after` bzw. dem Marker zu und offen gelesen wird THEN ist die Darstellung bei beiden Arten für zu gleich und für offen gleich, und zu und offen unterscheiden sich (rechts gegen unten).
- [ ] Test 3: GIVEN ein ungebuchtes Ding mit Einzelheiten und eine gebuchte Buchung WHEN die Seite lädt THEN sind beide Einzelheiten zu, Name, Datum, Stand, Frist, Preis und Buchen-Handlung sind sichtbar.
- [ ] Test 4: GIVEN ein Wissens- oder Recherchetext mit mehreren Abschnitten WHEN die Seite lädt THEN ist auch der erste Abschnitt zu.
- [ ] Test 5: GIVEN eine Wahl mit erwogenen Plänen WHEN die Seite lädt THEN ist `details.weg` „Andere erwogene Pläne“ zu, auch wenn der gezeigte Plan nicht der feste ist.
- [ ] Test 6: GIVEN die Ansicht mit Wunschformular WHEN ohne Wunsch und ohne Entwurf geladen wird THEN ist `wu-neu` zu; GIVEN ein angefangener Entwurf der Person THEN ist es offen.
- [ ] Test 7: GIVEN zugeklappte Einzelheiten und ein Sprung per Hash auf einen Eintrag darin, per „zu buchen“ und per Suche WHEN der Sprung ausgeführt wird THEN sind alle umgebenden Klappen offen und das Ziel ist sichtbar.
- [ ] Test 8: GIVEN die Packliste WHEN Planen und Packen geladen werden THEN gilt unverändert die Vorgabe aus #511 (Planen Tabellen offen, Packen Gruppe offen, solange nicht alles Eigene gepackt ist; gemerkte Abweichung bleibt).
- [ ] Test 9 (AC-9, reiner Python-Test ohne Browser in `test_klappen_zugeklappt.py`): GIVEN `docs/design.md` und `engine/vorlage.html` (Kopfkommentar, Stilkommentar der Einzelheiten, Kommentar an `einzelheiten`, Bausteinseite) WHEN ihr Text gelesen wird THEN kommen „offen bis zur Buchung“, „Offen, solange noch gehandelt wird“ und „offen, solange noch gehandelt wird“ nicht mehr vor, und `docs/design.md` nennt die Regel „beim Laden zu, offen nur der Kern“ sowie die Pfeil-Konvention (zu = nach rechts, offen = nach unten).

Angepasste bestehende Erwartungen: `seiten_tagesseite.mjs` (Einzelheiten offen → zu), `seiten_buchung_zeitraum.mjs`, `seiten_variante.mjs` (`details.weg`), `seiten_ding_lesetext.mjs` und `namen_browser.mjs` (Inhalt erst nach dem Aufklappen), `test_seite.py` (Auswertung).

## Acceptance Criteria

- **AC-1:** Given beide Beispielreisen frisch geladen ohne gemerkte Zustände / When alle Klappen der Seite gelesen werden / Then ist keine Klappe offen außer Tageskapitel (gemerkt), Packliste und Wunschformular mit Entwurf.
- **AC-2:** Given eine Seite mit Kapiteln und Pico-Klappen / When der Pfeil im Zustand zu und im Zustand offen gelesen wird / Then bedeutet rechts überall zu und unten überall offen; die berechnete Transformation ist bei `kapitel` und Pico-Klappen je Zustand gleich.
- **AC-3:** Given ein Ding oder eine Buchung, gebucht oder ungebucht / When die Seite lädt / Then sind die Einzelheiten zu, und Name, Datum, Stand, Frist, Preis und Buchen-Handlung bleiben außerhalb sichtbar.
- **AC-4:** Given ein Wissens- oder Recherchetext / When die Seite lädt / Then ist auch der erste Abschnitt zu.
- **AC-5:** Given eine Wahl mit erwogenen Plänen / When die Seite lädt / Then ist „Andere erwogene Pläne“ zu.
- **AC-6:** Given das Wunschformular / When die Person keinen angefangenen Entwurf hat / Then ist es zu, auch bei leerer Wunschliste; mit angefangenem Entwurf ist es offen.
- **AC-7:** Given zugeklappte Einzelheiten / When ein Sprung per Hash, „zu buchen“ oder Suche auf einen Eintrag darin führt / Then öffnen sich alle umgebenden Klappen und das Ziel ist sichtbar.
- **AC-8:** Given die Packliste / When Planen oder Packen geladen wird / Then ist sie unverändert wie in #511 (Kern = Arbeitsfläche; das Gerät merkt jede Abweichung).
- **AC-9:** Given die Doku / When `docs/design.md`, die Bausteinseite und der Kopfkommentar der Vorlage gelesen werden / Then nennen sie die neue Regel („beim Laden zu, offen nur der Kern“) und die eine Pfeil-Konvention, und „offen bis zur Buchung“ steht nirgends mehr.
- **AC-10:** Given die vollständige Testsuite / When `engine/.venv/bin/python -m pytest -q engine/tests` läuft (lokal und CI) / Then ist sie grün, einschließlich `test_design.py`, `test_texte.py` und der angepassten Seitentests.

## Known Limitations

- Die Ansicht zeigt weniger auf einen Blick; wer Einzelheiten braucht, tippt einmal. Das ist die bewusste Entscheidung des Product Owners (23.11.2026) für Progressive Disclosure.
- Alle Klappen der Seite ändern ihr Pfeilbild nicht, nur die Kapitel; Kapitel wirken nach der Änderung anders, ohne dass sich ihr Verhalten ändert.
- Die Packliste bleibt bewusst offen (Kern); eine spätere Entscheidung, auch dort zu starten, wäre eine eigene Änderung.
- Der Regeltest kennt die Kern-Liste fest; ein neuer offener Kern braucht eine Entscheidung und einen Eintrag dort.
- Die Bausteinseite (Entwicklerseite, nicht in der Leiste) zeigt das Muster „Fläche: aufklappbarer Abschnitt“ offen, damit man den offenen Zustand sieht; sie gehört nicht zu den Ansichten des Regeltests.
- Bei einer gebuchten Buchung steht der Preis seit #463 in den „Einzelheiten zur Buchung“ (oben Nummer, Check-in, Check-out, Zahlstand); „Preis außerhalb“ in AC-3 gilt für ungebuchte Dinge und Buchungen. #632 ändert daran nichts.

## Definition of Done

- [ ] Alle neuen und angepassten Tests grün, volle Testsuite grün (lokal und CI).
- [ ] Abnahme an beiden Beispielreisen und an einer Reise ohne Pläne (Seite frisch geladen, Sprung öffnet Klappen, Pfeil eindeutig).
- [ ] Ausgeliefert und auf der Instanz veröffentlicht; Issue #632 erst danach geschlossen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Darstellungsregel innerhalb bestehender Entscheidungen (ADR-0002 Atomic Design, ADR-0003 eine Heimat); keine neue Grundform, kein neuer Baustein, kein Formatwechsel. Die Produktentscheidung (Product Owner, 23.11.2026) ersetzt die Stand-Leiter-Regel „Einzelheiten offen bis zur Buchung“ und steht in `docs/design.md` und im Issue #632.

## Changelog

- 2026-11-23: Initial spec created
