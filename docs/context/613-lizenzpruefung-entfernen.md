# Context: 613-lizenzpruefung-entfernen

## Request Summary
Entscheidung des Product Owners (17.11.2026, #613, Teil von #455): Frieda prüft Urheberschaft und Lizenz von Bildern nicht
selbst. Die Positivliste der Lizenzen und die Ablehnung `bild.abgelehnt.lizenz` entfallen, jedes Commons-Bild wird angenommen.
Die Namensnennung unter dem Bild bleibt. Ergänzung (Kommentar des Owners): Die Antwort von `image_add` nennt Urheber und
Lizenz, erinnert daran, dass die Person die Nutzungsrechte verantwortet, und sagt bei eingeschränkten Lizenzen (NC, ND, GFDL,
unbekannt, fehlend) konkret, was eingeschränkt ist. Der Hinweis informiert nur, er sperrt nie.

## Related Files
| File | Relevance |
|------|-----------|
| engine/bilder.py | `lizenz_pruefen` (Positivliste `FREI`, `GEMEINFREI`), `abrufen` ruft sie auf; Docstring nennt Positivliste |
| engine/schreiben.py | `bild_hinzufuegen` baut die Antwort `schreiben.antwort.bild.neu` aus Urheber und Lizenz |
| engine/texte_de.py, engine/texte_en.py | `bild.abgelehnt.lizenz` (entfällt), `schreiben.antwort.bild.neu`, `konnektor.werkzeug.bild_hinzufuegen` (nennt Positivliste) |
| engine/bauen.py | `nennung_daten`/`nennung_html`: Namensnennung; gemeinfrei nur Urheber; leere Lizenz ergibt Urheber + Commons-Seite |
| engine/tests/test_bilder.py | Tests der Positivliste und der Ablehnung; Fixtures `wanderung`, `stadt`, `Netz`, `meta`, `commons_antwort` |
| docs/konnektor.md | Zeile zu `bild_hinzufuegen` nennt Positivliste |

## Existing Patterns
- Antworten des Schreibwegs setzen sich aus Katalogsätzen zusammen (`S(...)` + Zusätze wie `schreiben.antwort.packliste.*`).
- Ablehnungen des Moduls `bilder` als `Abgelehnt(schluessel)`; ohne Lizenzprüfung bleiben nur Netz, Format, Größe, Quelle.
- Abruf vor der Sperre (`vorab_schreiben/vorab_lesen`) reicht das Ergebnis-Dict als JSON weiter; eine Einschränkung wird
  deshalb in `schreiben` aus dem Lizenznamen abgeleitet (reine Funktion), nicht als neues Feld durch den Vorab-Weg getragen.

## Dependencies
- Upstream: Commons `extmetadata` (`LicenseShortName`, `LicenseUrl`, `Artist`), `nh3` zum Säubern.
- Downstream: `bauen.nennung_*` (unverändert), Konnektor-Werkzeugbeschreibung, Instanz-Tests (Meldungstexte ändern sich).

## Existing Specs
- `docs/specs/oberflaeche/bilder-455-stufe1.md` (P1: Lizenzregel V8) – historisch, die neue Spec ersetzt die Regel.

## Risks & Considerations
- Leere Lizenz oder leerer Urheber: Antwort darf keine leeren Stellen („: , .“) zeigen → Katalogwörter für „ohne Angabe“.
- `FREI` verlangte bisher eine Versionsnummer; für die Einordnung „ohne Einschränkung“ auch „CC BY-SA“ ohne Version zulassen.
- Mehrere Einschränkungen zugleich (CC BY-NC-ND) → beide nennen.
- Ausnahmelisten in test_texte.py dürfen nur kürzer werden; neue Schlüssel in de und en.
- Meldungstext ändert sich → Tests der einbindenden Instanz vor dem Vorspulen laufen lassen.
- Beispielreisen enthalten nur freie Bilder; Test an beiden Reisen, dass eingeschränkte Bilder angenommen und genannt werden.

## Vorläufiger Ansatz (aus Phase 1, in der Analyse bestätigen)
- `bilder.lizenz_pruefen` wird `lizenz_lesen` (wirft nie, leere Lizenz → `""`), dazu reine Funktion
  `bilder.einschraenkungen(lizenz) -> list` mit Codes `nc`, `nd`, `gfdl`, `fehlt` (leer), `andere` (unbekannter Name, etwa
  Free Art License, „Copyrighted“); frei ohne Hinweis: CC0, gemeinfrei, CC BY, CC BY-SA (Version optional).
- `schreiben.bild_hinzufuegen`: Antwort = `schreiben.antwort.bild.neu` (Ersatzwörter bei leerem Urheber/Lizenz)
  + `schreiben.antwort.bild.rechte` (Verantwortung liegt bei der Person) + je Code `schreiben.antwort.bild.einschraenkung.<code>`.
- `bild.abgelehnt.lizenz` aus de/en entfernen; Werkzeugbeschreibung de/en und docs/konnektor.md ohne Positivliste.
- Tests: Positivlisten-Tests ersetzen; NC/ND/GFDL/FAL/leer werden an Wanderung und Stadtwochenende angenommen, Antwort nennt die
  Einschränkung, gebaute Seite zeigt Namensnennung mit Lizenz.

## Analysis

### Type
Feature (Vorgabe des Product Owners: Sperre durch Hinweis ersetzen)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/bilder.py | MODIFY | `FREI`-Positivliste und `lizenz_pruefen` → `lizenz_lesen` (wirft nie); neue reine Funktion `einschraenkungen(lizenz) -> list[str]` (Codes `nc`, `nd`, `gfdl`, `fehlt`, `andere`); `abrufen` und Kopf-Docstring anpassen |
| engine/schreiben.py | MODIFY | `bild_hinzufuegen` (Z. ~5298): Antwort = `bild.neu` mit Ersatzwörtern bei leerem Urheber/Lizenz + `bild.rechte` + je Einschränkung `bild.einschraenkung.<code>`; Docstring „Lizenz prüfen“ → „Lizenz lesen“ |
| engine/texte_de.py, engine/texte_en.py | MODIFY | `bild.abgelehnt.lizenz` entfernen; neu `schreiben.antwort.bild.rechte`, `…bild.einschraenkung.{nc,nd,gfdl,fehlt,andere}`, Ersatzwörter `…bild.ohne_urheber`, `…bild.ohne_lizenz`; `konnektor.werkzeug.bild_hinzufuegen` ohne Positivliste, mit Hinweis auf Verantwortung |
| engine/tests/test_bilder.py | MODIFY | Positivlisten-/Ablehnungstests (Z. 8, 163–174, 302) ersetzen durch: eingeschränkte Lizenzen werden angenommen (Wanderung und Stadtwochenende), Antwort nennt Einschränkung, gebaute Seite zeigt Namensnennung; reine Tests für `einschraenkungen` |
| docs/konnektor.md | MODIFY | Zeile 70: Positivliste raus, Hinweis statt Ablehnung |

Nicht betroffen: `bauen.nennung_daten/nennung_html` (leere Lizenz ergibt bereits Urheber + Commons-Seite), `neu.py` (keine Lizenzregel, kein Formatwechsel der Reisedaten → kein `nachziehen` nötig), `gemeinfrei()`/`GEMEINFREI` bleiben. Historische Artefakte in `docs/artifacts/bilder-455-stufe1/` bleiben unverändert.

### Scope Assessment
- Files: 6
- Estimated LoC: +90/-40
- Risk Level: LOW (ein isolierter Abruf- und Antwortpfad; Datenformat unverändert; nur Meldungstexte ändern sich → Instanz-Tests vor dem Vorspulen)

### Technical Approach
Vorläufiger Ansatz aus Phase 1 bestätigt. Einordnung in `einschraenkungen` (reine Funktion, ohne Netz):
- leer → `["fehlt"]`; gemeinfrei (bestehendes `GEMEINFREI`) → `[]`
- Muster `CC BY(-SA)?( \d\.\d)?( [a-z]{2})?` → `[]` (Version optional)
- enthält `NC` → `nc`, enthält `ND` → `nd` (beide möglich, Reihenfolge nc, nd); `GFDL` → `gfdl`
- alles andere (Free Art License, „Copyrighted“, Attribution …) → `["andere"]`
Die Einschränkung wird in `schreiben` aus dem gespeicherten Lizenznamen abgeleitet; der Vorab-Weg (JSON) bleibt unverändert.
Der Hinweis informiert nur; keine neue Ablehnung, kein neues Feld in `plan/bilder.yaml`.

### Dependencies
- `bilder.abrufen` ← `schreiben.bild_hinzufuegen` und Vorab-Abruf des Dienstes; `bauen` liest `lizenz` aus `plan/bilder.yaml`.
- `test_texte.py`: neue Schlüssel in de und en; Ausnahmelisten werden nicht länger.
- #582 (eigene Fotos) übernimmt später `bild.rechte`; hier nicht umgesetzt.

### Open Questions
- keine (Vorgabe und Ergänzung des Owners decken Verhalten und Texte ab)
