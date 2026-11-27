---
entity_id: pfeil-im-oeffnen-706
type: bugfix
created: 2026-11-27
updated: 2026-11-27
status: draft
workflow: fix-706-pfeil-im-oeffnen
---

# Pfeilknopf während des Öffnens der Großansicht wirkt nicht mehr (#706)

Grundlage: `docs/context/fix-706-pfeil-im-oeffnen.md` (Ursache, Varianten, Analyse). Vorgänger: `docs/specs/oberflaeche/loeschfrage-grossansicht-689.md`.

## Approval

- [ ] Approved

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Es ändert sich nur, wann die vorhandene Großansicht (`grossAnsicht`) Blättern annimmt. Keine neue Grundform, kein Baustein, keine Daten, keine Schnittstelle, kein Vendor-Code; der Kern aus ADR-0001 ist nicht berührt.

## Purpose

Wer in der Großansicht den Pfeilknopf „weiter“ oder „zurück“ drückt, während sie sich noch öffnet (rund 0,4 s), bekommt heute eine leere Ansicht; Zähler, Unterschrift und „Foto entfernen“ bleiben beim vorigen Bild stehen, und die Seite meldet einen Fehler. Drückt man danach „Foto entfernen“, wird das Foto des stehengebliebenen Knopfs gelöscht, nicht das, auf dem die Ansicht steht (Nachtrag aus #689, F001). Künftig wirkt der Pfeilknopf während des Öffnens nicht, genau wie Pfeiltaste, Wischen und Escape schon heute; nach dem Öffnen blättert er wie bisher. Zähler, Unterschrift und „Foto entfernen“ gehören damit immer zum gezeigten Bild.

## Ursache (im Code belegt)

PhotoSwipe 5.4.4 füllt beim Öffnen nur den mittleren Platz; die Nachbarplätze bekommen ihr Bild erst im eigenen Hörer auf `openingAnimationEnd`. Der Pfeilknopf ruft `next()`/`prev()` → `goTo()` → `mainScroll.moveIndexBy()` ohne Rücksicht auf `opener.isOpen`; `updateCurrItem` schiebt den leeren Nachbarplatz in die Mitte, `currSlide` ist `undefined`, die `change`-Hörer der Vorlage brechen ab („reading 'data'“), bevor sie Zähler und Knopf erneuern. Pfeiltaste (erst ab `bindEvents`) und Wischen (`onPointerDown` verwirft vor `isOpen`) sind nicht betroffen.

## Source

- **File:** `engine/vorlage.html`, `engine/tests/seiten_bilder_eigen.mjs`, `engine/tests/test_bilder_eigen.py`
- **Identifier:** `function grossAnsicht` (Vorlage); Art `oeffnen`, Ablauf `blaettern` und neue Abläufe (Skript); Fixture `oeffnen`, `test_gross_*` (Python)

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/vendor/photoswipe-5.4.4.esm.min.js` | Vendor, unverändert | genutzt: `goTo` (über `next`/`prev` auch von den Pfeilknöpfen), `opener.isOpen` |
| `docs/specs/oberflaeche/loeschfrage-grossansicht-689.md` | Spec | AC-4 „Klick, dann Pfeil verwirft“ setzte das Blättern im Öffnen voraus; wird hier angepasst (siehe Implementation Details) |
| `bildEntfernenFragen`, `darfFotoEntfernen` (Vorlage) | Funktionen | unverändert |
| Playwright (Chromium, WebKit) | extern | Chromium und WebKit lokal und in der CI |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/vorlage.html` | MODIFY | `grossAnsicht`: `pswp.goTo` umhüllen, Weitergabe nur bei `pswp.opener.isOpen`; Kommentar zu #706 |
| `engine/tests/seiten_bilder_eigen.mjs` | MODIFY | Ablauf `blaettern` hält Stand nach dem Öffnen fest; neue Abläufe `pfeil` (Pfeil im Öffnen, dann blättern nach dem Öffnen) und `pfeilKlick` (Pfeil, dann Klick im Öffnen) |
| `engine/tests/test_bilder_eigen.py` | MODIFY | Ausnahme für #706 entfernen, AC-4 aus #689 auf das neue Verhalten, neue Tests |

Dazu Unterlagen unter `docs/` (Kontext, diese Spec, Nachweise, Changelog der #689-Spec). Unverändert: Vendor, übrige Engine, `docs/funktionen/`, `docs/design.md`, `betrieb/`.

### Estimated Changes

- Files: 3 (dazu Unterlagen unter `docs/`)
- LoC: etwa +70/-15 (Vorlage rund +4, Rest Tests). Grenze ±250.

### Out of Scope

- Blättern im Öffnen aufschieben statt ignorieren (Variante B, verworfen: mehr Zustand, Wechselwirkung mit dem gemerkten Klick aus #689).
- Kreuz, Escape, Wischen im Öffnen (Bibliothek, unverändert).
- Änderungen an der Bibliothek im Vendor.
- Galerie der Erklärseiten (`engine/app/galerie.js`, #711): fängt denselben Fehler schon selbst ab (sperrt im Öffnen alle Klicks und Gesten). Auf der Reiseseite ginge das nicht, weil der Klick auf „Foto entfernen“ im Öffnen gemerkt werden muss (#689); deshalb hier die engere Hülle um `goTo`. Die Erklärseiten bleiben unverändert.

## Implementation Details

In `grossAnsicht`, direkt nach `new PhotoSwipe(...)` und vor `pswp.init()`:

```js
const blaettern = pswp.goTo.bind(pswp);
pswp.goTo = i => { if (pswp.opener.isOpen) blaettern(i); };   // im Öffnen nicht (#706), wie Pfeiltaste und Wischen
```

`next()` und `prev()` rufen intern `this.goTo(...)`, also greift die Hülle für die Pfeilknöpfe, die Tasten und jedes andere Blättern über die API. `init()` ruft `goTo` nicht (setzt `currIndex` direkt). Bei reduzierter Bewegung ist `isOpen` nach `init()` sofort wahr: unverändert. Beim Schließen ist `isOpen` falsch: Blättern während des Schließens wirkt ebenfalls nicht (heute ohne Nutzen, da die Ansicht verschwindet).

**Folge für #689 AC-4:** „Klick auf ‚Foto entfernen‘ im Öffnen, dann Pfeilknopf“ blättert nicht mehr; der Klick bleibt gemerkt, und die Frage kommt am Ende des Öffnens zum gezeigten Foto (wie Escape, #689 AC-7). Das Ziel von AC-4 („nie eine Frage zu einem anderen Foto als dem gezeigten“) bleibt erfüllt. Der Hörer `change → danach = null` bleibt (er greift bei jedem echten Blättern; im Öffnen gibt es keines mehr). Die #689-Spec bekommt einen Changelog-Eintrag mit Verweis hierher.

## Test Plan

### Automated Tests (TDD RED)

Alle in `engine/tests/test_bilder_eigen.py`, Fixture `oeffnen` (Chromium und WebKit, Öffnen per `route` auf 3 s verlängert), Abläufe in `engine/tests/seiten_bilder_eigen.mjs`. Zwei eigene Fotos am selben Ort, BI-91 zuerst.

- [ ] Test 1 (Pfeil im Öffnen): GIVEN die Großansicht öffnet (`isOpen` falsch) / WHEN der Pfeilknopf „weiter“ gedrückt wird / THEN bleibt `currIndex` 0; nach dem Öffnen ist ein Bild im Blick (`currSlide` gesetzt, BI-91), der Zähler nennt „1“, kein Seitenfehler. Heute rot.
- [ ] Test 2 (Blättern danach): GIVEN Test 1 nach dem Öffnen / WHEN der Pfeilknopf „weiter“ gedrückt wird / THEN steht die Ansicht auf Index 1 (BI-90), der Zähler nennt „2“, kein Seitenfehler. Wächter, heute grün (nach dem Öffnen funktioniert der Pfeil schon).
- [ ] Test 3 (Pfeil, dann Klick): GIVEN die Großansicht öffnet / WHEN erst der Pfeilknopf, dann „Foto entfernen“ gedrückt wird / THEN kommt nach dem Öffnen genau eine Frage, „Entfernen“ löscht BI-91 (das gezeigte), kein DELETE eines anderen Fotos, kein Seitenfehler. Heute rot (Seitenfehler).
- [ ] Test 4 (Klick, dann Pfeil, #689 AC-4 neu): GIVEN Klick auf „Foto entfernen“ im Öffnen / WHEN danach der Pfeilknopf gedrückt wird / THEN `currIndex` bleibt 0, nach dem Öffnen genau eine Frage zum gezeigten Foto (Großansicht zu, Fokus im Dialog), keine Seitenfehler (Ausnahme entfernt). Heute rot.
- [ ] Bestehende `test_gross_*`, `test_browser_hochladen_hinweis_nennung_und_loeschen`, `test_seite_bilder.py` bleiben grün.

## Acceptance Criteria

- **AC-1:** Given die Großansicht öffnet noch / When der Pfeilknopf gedrückt wird / Then bleibt sie auf dem angetippten Bild; nach dem Öffnen zeigt sie es, Zähler und Unterschrift gehören dazu, kein Seitenfehler.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_pfeil_im_oeffnen_bleibt`
- **AC-2:** Given die Großansicht ist offen (nach einem Pfeil im Öffnen) / When der Pfeilknopf gedrückt wird / Then blättert sie wie bisher zum nächsten Bild, Zähler folgt.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_pfeil_nach_dem_oeffnen_blaettert`
- **AC-3:** Given die Großansicht öffnet / When erst der Pfeilknopf, dann „Foto entfernen“ gedrückt wird / Then genau eine Frage nach dem Öffnen, und „Entfernen“ löscht das gezeigte Foto, kein anderes.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_pfeil_dann_klick_meint_gezeigtes_foto`
- **AC-4:** Given Klick auf „Foto entfernen“ im Öffnen / When danach der Pfeilknopf gedrückt wird / Then blättert nichts und die Frage kommt nach dem Öffnen zum gezeigten Foto; die Ausnahme für den #706-Seitenfehler ist entfernt, jeder Seitenfehler macht den Test rot.
  Test: `engine/tests/test_bilder_eigen.py::test_gross_klick_im_oeffnen_dann_pfeil_fragt`
- **AC-5:** Given der heutige Stand (Vorlage unverändert) / When die Tests zu AC-1, AC-3 und AC-4 laufen / Then sind sie rot; nach der Änderung grün.
  Test: von Claude ausgeführt (RED- und GREEN-Lauf, Ausgabe im Nachweis)
- **AC-6:** Given der Stand vor der Auslieferung / When `test_bilder_eigen.py` und `test_seite_bilder.py` laufen / Then grün in Chromium und WebKit, dazu die Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`.
  Test: von Claude ausgeführt (lokal und CI)
- **AC-7:** Given der Stand der Änderung / When mit `main` verglichen / Then nur die drei Dateien oben und Unterlagen unter `docs/` geändert, Vendor unverändert.
  Test: von Claude ausgeführt (Vergleich mit `main`)

## Risks

- **Ein Druck geht verloren:** Wer im Öffnen den Pfeil drückt, muss nach 0,4 s noch einmal drücken. Gleich wie Pfeiltaste und Wischen heute; bewusst gewählt.
- **Hülle über eine Methode der Bibliothek:** Ändert ein Update von PhotoSwipe den Weg `next`→`goTo`, greift die Hülle nicht mehr; Test 1 und Test 3 werden dann rot.
- **WebKit:** lokal installiert, wird lokal und in der CI geprüft.

## Known Limitations

- Pfeilknopf ist im Öffnen sichtbar, wirkt aber nicht (keine Sperr-Optik), wie die übrigen Bedienelemente der Bibliothek im Öffnen.

## Definition of Done

- [ ] AC-1 bis AC-4 durch Tests belegt, AC-5 RED/GREEN gezeigt
- [ ] AC-6 grün lokal (Chromium, WebKit) und in der CI
- [ ] AC-7 belegt
- [ ] Changelog der #689-Spec ergänzt
- [ ] Auslieferung über Pull Request, grüne Pflichtprüfungen, Vorspulen; #706 erst danach schließen

## Changelog

- 2026-11-27: Initiale Spec (#706)
