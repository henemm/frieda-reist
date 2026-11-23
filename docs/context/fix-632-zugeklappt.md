# Context: fix-632-zugeklappt

## Request Summary
Aufklappbare Bereiche der Reiseseite sollen zugeklappt starten (Progressive Disclosure); offen startet nur, was zum Kern gehört. Pfeil und Zustand müssen zusammenpassen (#632, Präzisierung des Product Owners vom 19.11.2026: Kern ist der offene Ausgangszustand, die Quelle-Zeile nur ein Beispiel).

## Related Files
| File | Relevance |
|------|-----------|
| engine/vorlage.html `einzelheiten()` (~2410), Aufrufer `planungsTeil()` (~2257) und `buchungBlock()` (~2457) | Einzelheiten eines Dings und einer Buchung: `open: !gebucht` (Stand-Leiter, PO 31.10.2026). Aktivitäten sind nie gebucht, daher immer offen; darin die Quelle-Zeile (`quelleZeilen`). |
| engine/vorlage.html `block()` (~1758), Aufruf `block(b, i === 0, …)` (~1818) | Erster Abschnitt eines Wissens-/Recherche-Textes offen. |
| engine/vorlage.html `ansichtVarianten()` (~3664) | „Andere erwogene Pläne“ (`details.weg`) offen, solange der gezeigte Plan nicht der feste ist. |
| engine/vorlage.html Wunschformular (~5751) | `details.wu-neu` offen, solange es keinen Wunsch gibt oder ein Entwurf vorliegt. |
| engine/vorlage.html `packTabelle()` (~6003), `packGruppe()` (~6038), `plKlapper()` (~6046) | Planen: Tabelle je Kategorie offen; Packen: Gruppe offen, solange nicht alles Eigene gepackt ist (#511). Gerät merkt sich Abweichungen von der Vorgabe (`pl-offen`). |
| engine/vorlage.html CSS 704–705 | Eigener Pfeil nur für `details.kapitel`: zu = Pfeil nach unten, offen = nach oben. |
| engine/vendor/pico-2.1.1…css | Pico-Pfeil für alle übrigen `details`: zu = nach rechts (rotate -90°), offen = nach unten. |
| engine/vorlage.html Bausteinseite (~5066, ~5100) | Muster für Einzelheiten und Packklapper mit Erklärtext „offen, solange gehandelt wird“. |
| docs/design.md Zeile 13 (Moleküle `einzelheiten`, `plKlapper`), Abschnitt Stand-Leiter (~246 ff.) | Doku der heutigen Regel „offen bis zur Buchung“ und „beim Planen offen“. |

## Existing Patterns
- Schon zugeklappt: Tageskapitel (`kapitel`, nur das gemerkte offen), Verlauf, Storniertes, Herkunft je Wert, Quellen, Alternativen, Einzelheiten ab der Buchung, weggelassene Gegenstände.
- Ziel-Sprung öffnet umgebende `details` (vorlage ~3540, ~4763 „zu-buchen“ per Hash, ~6566 Suche/Sprung). Das bleibt und ist der Weg, Zugeklapptes gezielt zu zeigen.
- Packliste: Vorgabe plus gemerkte Abweichung je Gerät (`plKlapper`/`plMerkeOffen`); eine geänderte Vorgabe verändert gemerkte Wahl nicht, nur ungemerkte.

## Befund Pfeil
Zwei Konventionen auf derselben Seite: Tageskapitel zeigen zu einen Pfeil nach unten, alle Pico-Klappen zeigen offen einen Pfeil nach unten. Die meldende Person las den Pfeil nach unten an den (offenen) Einzelheiten als „zu“ – Ursache der Meldung „Pfeil und Zustand passen nicht“. Eine Konvention für die ganze Seite nötig.

## Dependencies
- Upstream: Pico 2.1.1 (`details`/`summary`-Stil), Textkatalog (`seite.buchung.einzelheiten`, `seite.einzelheiten.aus_der_planung`, `seite.plan.andere_erwogene_n`, `seite.wunsch.neuer`).
- Downstream (Tests, die Klappzustände prüfen): `seiten_tagesseite.mjs` (54, 142–151: `einzelheiten` open-Werte), `seiten_buchung_zeitraum.mjs` (22: `einzelheiten_zu`), `seiten_packliste.mjs` (166–173: Alle auf/zu, gemerkt), `seiten_ding_lesetext.mjs` (25: Quelle in Einzelheiten), `seiten_variante.mjs` (details.weg), `namen_browser.mjs` (17), dazu die Python-Tests in `test_seite.py`, die diese Skripte auswerten.

## Existing Specs
- docs/design.md Stand-Leiter (PO 31.10.2026): „Einzelheiten offen bis zur Buchung“ – wird durch #632 geändert, braucht Freigabe des PO (frühere Produktentscheidung).
- #511 Packliste: „beim Planen offen, beim Packen zu, wenn alles gepackt“.

## Risks & Considerations
- Widerspricht zwei früheren PO-Entscheidungen (Stand-Leiter, #511) → Entwurf als Artefakt und Freigabe (Erst zeigen, dann bauen, #436).
- Unentschiedene Unterkunft: Einzelheiten enthalten das, „was man zum Buchen braucht“ – zugeklappt muss weiter alles Nötige einen Tipp entfernt sein.
- Wunschformular: Bei leerer Liste ist das Formular die einzige Handlung auf der Ansicht (Kern?).
- Packliste beim Packen: offene Gruppen sind die Arbeitsfläche (Kern?).
- Pfeilwechsel betrifft alle Klappen der Seite visuell; Screenshot-/Design-Tests prüfen.
- Gilt für beide Beispielreisen (Wanderung, Stadtwochenende) und Reisen ohne Pläne.

## Analysis

### Type
Bug (Meldung aus der App) mit Produktanteil: Die Regel „offen bis zur Buchung“ (Stand-Leiter, PO 31.10.2026) und „beim Planen/Packen offen“ (#511) sind frühere PO-Entscheidungen; welche Stellen zum Kern gehören, entscheidet der PO am Entwurf (Phase 3, #436).

### Ursache
1. Fünf Klappen starten offen (Bestandsaufnahme im Issue-Kommentar vom 19.11.): `einzelheiten(!gebucht)` an Ding und Buchung, `block(b, i === 0)`, `details.weg` (`VARIANTE !== fest?.id`), `details.wu-neu` (kein Wunsch oder Entwurf), Packliste (`plKlapper("planen…", true)`, `packGruppe` mit `!alles`).
2. Zwei Pfeil-Konventionen auf einer Seite: `details.kapitel` (CSS 704–705) zeigt zu einen Pfeil nach unten, offen nach oben; Pico zeigt zu nach rechts, offen nach unten. Eine offene Pico-Klappe sieht deshalb aus wie ein zugeklapptes Kapitel. Das ist die eigentliche Ursache von „Pfeil und Zustand passen nicht“.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/vorlage.html | MODIFY | Startzustand an den freigegebenen Stellen auf zu (`einzelheiten`-Aufrufe 2257/2457, `block` 1818, `details.weg` 3664, ggf. `wu-neu` 5751, ggf. Packliste 6003/6038); Kapitel-Pfeil auf die Pico-Konvention (zu → rechts, offen → unten); Bausteinseite 5066/5100 Erklärtexte; Kopfkommentar |
| docs/design.md | MODIFY | Moleküle `einzelheiten`/`plKlapper`, Stand-Leiter: neue Regel „zu, außer Kern“, eine Pfeil-Konvention |
| engine/tests/seiten_tagesseite.mjs, seiten_buchung_zeitraum.mjs, seiten_variante.mjs, seiten_ding_lesetext.mjs, seiten_packliste.mjs, namen_browser.mjs | MODIFY | Erwartete open-Werte anpassen; Inhalt nach Aufklappen prüfen |
| engine/tests/test_seite.py (+ ggf. neuer Test) | MODIFY/CREATE | Regel prüfen: beim Laden ist auf beiden Beispielreisen keine Klappe außerhalb der Kern-Liste offen; Pfeil-Konvention (berechneter Stil von `summary::after` zu vs. offen) einheitlich für `kapitel` und Pico-Klappen |
| engine/texte_*.py | ggf. MODIFY | nur falls Erklärtexte der Bausteinseite im Katalog stehen |

### Scope Assessment
- Files: ~8–10
- Estimated LoC: +60/−30 (überwiegend Tests)
- Risk Level: MEDIUM — reine Darstellung, keine Daten; aber viele Browser-Tests prüfen Klappzustände, und alle Klappen der Seite ändern ihr Pfeilbild.

### Technical Approach
- Eine Konvention für die ganze Seite: Pico (zu → Pfeil nach rechts, offen → nach unten), weil sie für alle übrigen Klappen schon gilt und gängige Disclosure-Praxis ist; nur das Kapitel-CSS ändert sich (rotate −45° zu, 45° offen).
- Standard „zu“; offen startet nur, was der PO als Kern freigibt. Empfehlung für den Entwurf:
  - Einzelheiten (Ding und Buchung, auch ungebucht): zu. Name, Datum, Stand, Frist und die Buchen-Handlung stehen außerhalb; Preis/Zahlung ungebucht bleiben sichtbar (stehen heute schon außerhalb).
  - Erster Abschnitt eines Wissens-/Recherche-Textes: zu.
  - „Andere erwogene Pläne“: zu.
  - Wunschformular: zu; offen nur, wenn ein eigener Entwurf vorliegt (Zustand der Person, kein Ausgangszustand).
  - Packliste: bleibt wie #511 (Arbeitsfläche beim Planen und Packen = Kern der Ansicht; Gerät merkt sich jede Abweichung). Gegenoption für den PO: auch hier zu.
- Sprünge (Hash, Suche, „zu buchen“) öffnen umgebende Klappen weiter; Test sichert das für zugeklappte Einzelheiten.
- Kein Formatwechsel der Reisedaten → kein `nachziehen` nötig.
- Gegen beide Beispielreisen und eine Reise ohne Pläne prüfen.

### Dependencies
Pico 2.1.1 (Pfeil-Stil, unverändert), Textkatalog (keine neuen Schlüssel erwartet), Browser-Tests (siehe oben).

### Open Questions
- [x] PO-Entscheidung 23.11.2026 (Artefakt + AskUserQuestion, Wortlaut im Issue #632): Packliste bleibt offen wie #511 (Variante 1); Einzelheiten (auch ungebucht), erster Wissensabschnitt, „Andere erwogene Pläne“ zu; Wunschformular zu, offen nur mit Entwurf; Pfeil überall rechts = zu, unten = offen.
