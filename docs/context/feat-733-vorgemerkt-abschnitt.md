# Kontext: feat-733-vorgemerkt-abschnitt

## Anfrage

Product Owner, 27.11.2026 (#733): Vorgemerkte Reisen nicht mehr oben in „Deine Reisen“, sondern in einem geschlossenen
Abschnitt unterhalb der Reisen. Entwurf mit Beispieldaten gezeigt (Claude-Artefakt, privat) und freigegeben:
`<details>` wie das Archiv, Titel „Zum Löschen vorgemerkt (n)“, unter der Reiseliste und unter dem Archiv; darin je Reise
eine Kachel mit Name (fett), Satz „Wird am <Datum> endgültig gelöscht.“ (klein) und, nur für Organisator:innen vor
Fristende, dem leisen Knopf „Reise zurückholen“ (#730).

## Betroffene Stellen

- `engine/anmeldung.py`
  - `konto_seite` (~1110–1135): sammelt `meine_vorgemerkten`, setzt heute `loeschen_block(...)` vor die Liste;
    danach `details.archiv` mit `konto.archiv.titel`. Neu: Abschnitt nach dem Archiv.
  - `loeschen_block` (~841–857): rendert je Reise `div.vorgemerkt.kasten` mit Satz `konto.reise_loeschen.block`
    (bzw. `block_vorbei`) und Knopf. Neu: Kacheln innerhalb von `details.archiv.vorgemerkt`.
  - Kommentare bei ~706 und ~1121 nennen „oben“.
  - Leere Liste: `konto.reisen.keine` erscheint nur, wenn weder Reisen noch Archiv noch Vorgemerkte da sind (bleibt so).
  - CSS: `.archiv>summary`, `.archiv` (~137), `.kasten` (~112), `.kachel`, `.klein`, `.leise` vorhanden; kein neuer Baustein.
- Texte `engine/texte_de.py`, `engine/texte_en.py`: neu `konto.reise_loeschen.abschnitt` („Zum Löschen vorgemerkt ({n})“);
  Satz in der Kachel ohne Titel: neu `konto.reise_loeschen.kachel` („Wird am {frist} endgültig gelöscht.“) — der
  bisherige Schlüssel `block` enthält den Titel. `block_vorbei` analog als `kachel_vorbei`. Alte Schlüssel entfernen,
  wenn ungenutzt (test_texte prüft ungenutzte Schlüssel vermutlich).
- Info-Unterseite Lebenslauf: `info.bereich.lebenslauf.wie.5.text` sagt nicht, wo die vorgemerkte Reise steht; ein
  Halbsatz („unter deinen Reisen unter „Zum Löschen vorgemerkt““) in de und en.
- `docs/design.md` Zeile ~238: „Vorgemerkte Reisen stehen oben in „Meine Reisen“ als grauer Kasten …“ → neue Lage.
- Tests: `engine/tests/test_loeschen_reise.py:282` prüft „Block steht oben“ (`block < liste`) → umdrehen (nach Liste
  und Archiv, in `<details>` ohne `open`). `:295`, `:315`, `test_bilder_konto.py:276` prüfen nur `class="vorgemerkt`
  → Klasse an der Kachel behalten.

## Risiken

- Nichts an Daten, Konten oder Schnittstellen; nur Darstellung der Kontoseite.
- Pseudo-Sprache der Tests (docs/sprachen.md): neue Schlüssel in allen Sprachdateien.
