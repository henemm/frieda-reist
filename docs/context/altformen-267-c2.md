# Context: altformen-267-c2

## Request Summary
Paket c2 von #267 (Teil 3 von #215): Die Bestandssprache `texte.BESTAND_REISE` („Reise ohne Feld `sprache` bleibt deutsch“)
entfällt. Eine `reise.yaml` ohne `sprache` ist danach ein Fehler der Prüfung (`pruefung.reise.sprache_fehlt`), die Reise
baut nicht, bis `neu.py nachziehen` das Feld einträgt (PR b, schon auf main). Grundlage: Spec
`docs/specs/betrieb/altformen-entfernen-267.md`, Abschnitt „PR c“, AC-6, AC-7, AC-9. c1 (`STUFEN_WORTE`, AC-8) ist auf main
(PR #318, 04e4a35). Der Nachweis b → c (AC-6) steht im Issue (Kommentar vom 4.11.2026, 08:59): alle 8 Reisen haben `sprache: de`.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/texte.py:18` | Konstante `BESTAND_REISE` (entfällt) |
| `engine/texte.py:141-146` | `_einzeln`: Bedingung `kuerzel != BESTAND_REISE` entfällt (für `de` ohne Wirkung, solange `texte_de` alle `_RAND`-Werte hat) |
| `engine/reise.py:6` | Kopfkommentar „ohne Feld de (Bestand …)“ |
| `engine/reise.py:220-230` | `sprache_von`: ohne Feld bisher `BESTAND_REISE`, künftig `VORGABE_REISE` |
| `engine/reise.py:233-241` | `sprache_pruefen(wert, leer)`: Docstring nennt den Bestand; Parameter `leer` wird nur von `Reise.sprache` genutzt |
| `engine/reise.py:382-388` | `Reise.sprache`: fehlendes/leeres Feld → `self.fehl(pruefung.reise.sprache_fehlt)` |
| `engine/neu.py:650` | `etappen_ebenen`-Vorgabe: `texte.t("de", …)` mit Kommentar „frühere Vorgabe war deutsch, #217“ |
| `engine/schreiben.py:2839-2840` | `einstellung_setzen`: Vergleich mit `roh.get("sprache")` ohne Ersatz; „von“ = `schreiben.antwort.einstellung.sprache_ungesetzt` |
| `engine/texte_de.py`, `engine/texte_en.py` | neue Schlüssel `pruefung.reise.sprache_fehlt` (nennt `texte.SPRACHEN` und „`neu.py nachziehen` trägt es ein“), `schreiben.antwort.einstellung.sprache_ungesetzt` |
| `docs/sprachen.md:88-91` | Abschnitt „Rückfall und Bestand“: Bestandsfall streichen, Regel „`sprache` steht in jeder `reise.yaml`“ |
| `docs/betrieb.md` | laut Spec Hinweise auf den Bestandsfall; aktuell kein Treffer für „BESTAND“ – beim Umsetzen nach „ohne Feld sprache“ suchen |
| `engine/tests/test_neu.py:360-385` | `test_rueckfall_ist_englisch…` (Aussage zu `BESTAND_REISE` entfällt), `test_reise_ohne_feld_sprache_bleibt_deutsch` (wird zu „bricht den Bau, nach `nachziehen` baut sie“) |
| `engine/tests/test_texte.py:401` | `_datenwerte()` liest aus `BESTAND_REISE` → künftig aus `"de"`-Katalog bzw. laut Spec `texte.VORGABE` (Achtung: muss dieselbe Menge sein; prüfen) |

## Testvorlagen ohne `sprache` (müssen das Feld bekommen)
Diese Fixtures schreiben eine `reise.yaml` ohne `sprache` und bauen sie; nach c2 brechen sie mit `sprache_fehlt`:
- `engine/tests/test_bauen.py:107` `GRUND_YAML`, `:404` `mit_reise_yaml` (`REISE_YAML`)
- `engine/tests/test_pwa.py:34`
- `engine/tests/test_regeln.py:47, 269`, `engine/tests/test_reiseueberblick.py:30`, `engine/tests/test_waechter.py:42` (je prüfen, ob die Vorlage das Feld schon trägt)
- `engine/tests/test_betrieb.py:1536` (`titel: x`, vermutlich gewollt kaputt – prüfen)
Beide Beispielreisen tragen `sprache: de`; die Reisevorlage `engine/reisevorlage/` hat je Sprache eigene Dateien, neue Reisen
bekommen das Feld über `neu.py` (Z. 158 `sprache_pruefen(sprache)` ohne `leer`).

## Existing Patterns
- Fehlende Pflichtangabe mit Katalogtext und Hinweis auf den Umstellweg: `pruefung.bauen.reise_yaml_fehlt` (PR a).
- Testsprache: `conftest.rueckfall_deutsch` setzt `texte.VORGABE_REISE = "de"` für alle Tests ohne Marke `echter_rueckfall`.
  Folge: Mit `sprache_von` → `VORGABE_REISE` ändert sich in den meisten Tests nichts; nur Tests mit `echter_rueckfall` sehen Englisch.
- Tests prüfen Meldungen über den Katalogschlüssel (`meldet()`, #204), nicht über den Wortlaut.

## Dependencies
- Upstream: `texte.SPRACHEN`, `texte.gueltig`, `texte.VORGABE_REISE`, Katalog `inhalt.nachziehen.unterwegs`.
- Downstream: `bauen.py` (Seite, Manifest, `lang`), `neu.py` (`sprache_von` in ids.yaml-Kopf, Herkunft, Meldungen),
  `schreiben.py` (Commit-/Verlaufstexte über `sprache_von`), Konnektor `setting_set` (`einstellung_setzen`).

## Existing Specs
- `docs/specs/betrieb/altformen-entfernen-267.md` – Gesamtspec #267, Abschnitt „PR c“ und AC-6/7/9 (freigegeben).
- `docs/specs/betrieb/altformen-stufen-worte-267-c.md` – c1 (erledigt).

## Risks & Considerations
- Kritischer Pfad: Jede Reise ohne `sprache` baut danach nicht. Nachweis b → c liegt vor (8/8 Reisen mit `sprache: de`);
  vor dem Vorspulen noch einmal lesend prüfen (Spec, Abnahmebedingung Punkt 2/3) und im PR-Text belegen.
- `sprache_von` ohne Feld → Englisch: betrifft nur Dateien, die der Bau ablehnt oder `nachziehen` gleich umstellt. `nachziehen`
  trägt `sprache` vor den Schritten ein, die `sprache_von` nutzen (PR b) – im Test absichern (Reise ohne Feld → nach `nachziehen`
  deutsch und baut).
- `_datenwerte()` in test_texte.py: Spec sagt „aus `texte.VORGABE`“ (en). Die Menge der `wert.`-Schlüssel muss in de und en
  gleich sein (Paritätstest) – sonst ändert sich die Ausnahmeliste (AC-9: Listen nicht länger).
- Ein Suchtest „kein `BESTAND_REISE` in `engine/`“ darf sich selbst (Testdatei) nicht finden: Suche auf Nicht-Testdateien beschränken
  oder den Namen im Test zusammensetzen.
- Volle Testsuite ~20 Minuten.

## Analysis

### Type
Feature (Abbau einer Altform, Teil 3 von #215; Spec `docs/specs/betrieb/altformen-entfernen-267.md`, Abschnitt „PR c“, ohne `STUFEN_WORTE` = c1)

### Abgleich Code ↔ Spec (Stand 04e4a35)
Die Zeilenangaben der Spec sind veraltet, die Stellen selbst stimmen. Echte Nutzer von `texte.BESTAND_REISE` (grep, ohne Tests):
`texte.py:18` (Definition), `texte.py:144` (`_einzeln`), `reise.py:229` (`sprache_von`), `reise.py:385` (`Reise.sprache`),
`neu.py:650` (Vorgabe „Unterwegs nachschlagen“), `schreiben.py:2839-2840` (`einstellung_setzen`). Test: `test_texte.py:401`, `test_neu.py:360-385`.

Nur Wortgebrauch „Sprache des Bestands“ ohne die Konstante (Kommentare/Docstrings, nutzen schon `VORGABE_REISE`):
`texte.py:115, 271, 339`, `konnektor.py:188, 200, 210, 1326, 2041`, `konten.py:73`, `kalender.py:275`. Diese Kommentare sind
irreführend (sie sagen „Bestand“, meinen den Rückfall Englisch) und werden im selben PR auf „Rückfall“ umformuliert, wo sie
`VORGABE_REISE` meinen; `texte.py:339` („als Text ist er der deutsche Satz“) und `schreiben.py:146` beschreiben `str(Satz)` und
bleiben inhaltlich, nur ohne das Wort „Bestand“, falls es dort für `BESTAND_REISE` steht – beim Umsetzen je Stelle prüfen.
Nicht betroffen: „Bestandsdaten“ in `neu.py arten-ableiten`, `schreiben.quelle_bestand`, `routen.py:33` (anderer Begriff).

`neu.SPRACHE_NACHZIEHEN = "de"` bleibt: Das ist der Wert, den `nachziehen` einträgt, und keine Lesetoleranz. Kommentar ohne
Verweis auf eine Konstante, die es nicht mehr gibt.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/texte.py` | MODIFY | `BESTAND_REISE` löschen; `_einzeln` ohne `kuerzel != BESTAND_REISE`; Docstrings 115/271 auf „Rückfall“ |
| `engine/reise.py` | MODIFY | Kopfkommentar Z. 6; `sprache_von` ohne Feld → `VORGABE_REISE`; `sprache_pruefen` ohne Parameter `leer` (einziger Nutzer war `Reise.sprache`); `Reise.sprache`: fehlt/leer → `self.fehl(texte.satz("pruefung.reise.sprache_fehlt", bekannt=…))` |
| `engine/neu.py` | MODIFY | Z. 650 `texte.t("de", …)` mit Kommentar „die frühere Vorgabe war deutsch, #217“; Kommentar Z. 659 |
| `engine/schreiben.py` | MODIFY | `einstellung_setzen`: Vergleich `roh.get("sprache") != sprache`, „von“ = `S("schreiben.antwort.einstellung.sprache_ungesetzt")` wenn leer |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | neue Schlüssel `pruefung.reise.sprache_fehlt`, `schreiben.antwort.einstellung.sprache_ungesetzt` |
| `engine/konnektor.py`, `engine/konten.py`, `engine/kalender.py` | MODIFY | nur Kommentare/Docstrings „Sprache des Bestands“ → „Rückfall“ (kein Verhalten) |
| `docs/sprachen.md` | MODIFY | Abschnitt „Rückfall und Bestand“: Bestandsfall streichen, „`sprache` steht in jeder `reise.yaml`“ |
| `engine/tests/test_neu.py` | MODIFY | Z. 360-385: Aussage zu `BESTAND_REISE` weg; „ohne Feld bleibt deutsch“ → „ohne Feld bricht der Bau mit `sprache_fehlt`, nach `nachziehen` deutsch und baut“ |
| `engine/tests/test_bauen.py` | MODIFY | Test: Reise ohne `sprache` → `meldet(…, "pruefung.reise.sprache_fehlt")`; Vorlagen `GRUND_YAML`/`REISE_YAML` bekommen `sprache: de` |
| `engine/tests/test_texte.py` | MODIFY | `_datenwerte()` aus `texte.VORGABE` (Parität de/en vorher prüfen); Suchtest „kein `BESTAND_REISE` in Nicht-Testdateien von `engine/`“ (Name zusammengesetzt); Test `_einzeln("de", …)` unverändert |
| `engine/tests/test_schreiben.py` | MODIFY | `einstellung_setzen` mit `sprache` für Reise mit Feld: Meldung unverändert; ohne Feld: „nicht gesetzt → en“ |
| weitere Testvorlagen ohne `sprache` | MODIFY | `test_pwa.py:34`, `test_waechter.py:30-39` (Vorgabe `sprache=None` schreibt kein Feld – prüfen, ob der Wächter den Bau/`Reise` durchläuft), `test_regeln.py`, `test_reiseueberblick.py`; `test_betrieb.py:1536` (`titel: x`) prüft nur den Ordner, bleibt. Genaue Liste ergibt der erste Lauf der Suite (RED-Phase) |

### Scope Assessment
- Files: ~8 Code/Doku, ~6-8 Tests
- Estimated LoC: +60/-25 (Code + Texte), Tests +40/-15
- Risk Level: MEDIUM – Verhalten ändert sich nur für Reisen ohne Feld, die es laut Nachweis (8/8) nicht mehr gibt; aber jede
  übersehene Reise baut dann nicht. Abgesichert durch die Abnahmebedingung b → c (lesende Prüfung + Probebau im PR-Text).

### Technical Approach
Ein PR, so wie die Spec ihn beschreibt; keine neue Entscheidung nötig.
1. RED: Tests zuerst (Bau bricht ohne Feld mit `sprache_fehlt`; nach `nachziehen` baut sie deutsch; Suchtest auf `BESTAND_REISE`;
   `einstellung_setzen` ohne Feld meldet „nicht gesetzt“; `sprache_von` ohne Feld → `VORGABE_REISE` unter `echter_rueckfall`).
2. GREEN: Konstante löschen, Stellen umstellen, zwei Katalogschlüssel in de/en, Kommentare bereinigen, `docs/sprachen.md`.
3. Testvorlagen, die durch den Bau laufen, bekommen `sprache: de` (Beispielwert, erfunden).
4. Vor dem Vorspulen: AC-6 (lesende Prüfung im Reisen-Repo, Probebau aller Reisen mit dem Branch, Tests der Instanz mit dem Branch) im PR-Text.

`_einzeln`: Die Bedingung `kuerzel != BESTAND_REISE` fällt ohne Ersatz. Für `de` greift der zweite Teil nur, wenn `texte_de` zu
einem `_RAND`-Wert keinen `wert.`-Eintrag hat – ein Test sichert ab, dass das für keinen `_RAND`-Wert gilt (sonst sähe Deutsch
plötzlich englische Namen; AC-9).

### Dependencies
- Upstream: `texte.SPRACHEN`, `texte.gueltig`, `texte.VORGABE_REISE`, `texte.satz`, Katalog `inhalt.nachziehen.unterwegs`.
- Downstream: `bauen.py` (über `Reise`), `neu.py` (`sprache_von`, `nachziehen`), `schreiben.py` (`sprache_von`, `einstellung_setzen`),
  Konnektor `setting_set`, `waechter.py` (`sprache_von`).
- Reihenfolge: `nachziehen` trägt `sprache` ein, bevor es `sprache_von` nutzt (PR b) – durch Test belegt.

### Open Questions
- keine (Spec freigegeben; Nachweis b → c liegt im Issue vom 4.11.2026, wird vor dem Vorspulen nur erneut lesend bestätigt)

## Befunde aus RED (4.11.2026)
- `_einzeln`: Nur 17 von 136 `_RAND`-Werten haben in `texte_de` einen `wert.`-Eintrag. Fiele `kuerzel != BESTAND_REISE` ersatzlos weg,
  zeigte Deutsch englische Namen (`art` → `kind`). Lösung laut Spec (Changelog RED): optionales Feld `NAMEN_DER_SCHNITTSTELLE = True`
  in `texte_de.py`, `_einzeln` fällt nur auf `_RAND` zurück, wenn die Sprachdatei das Feld nicht trägt. Tests in `test_texte.py`.
- Parität `wert.*` de/en: 104/104, keine Differenz; `_datenwerte()` liest jetzt aus `texte.VORGABE` (umgestellt, grün).
- Testvorlagen (AC-11): `test_bauen.py` `GRUND_YAML`/`REISE_YAML` und `test_pwa.py` tragen jetzt `sprache: de`. `test_regeln.py`,
  `test_waechter.py`, `test_reiseueberblick.py` kopieren die Beispielreise (hat `sprache: de`) und brauchen nichts. Die endgültige Liste
  ergibt der erste volle Lauf nach der Umsetzung; `test_betrieb.py:1536` (`titel: x`) und `:1115` (kaputtes YAML) sind gewollt unvollständig.
- Testumgebung im Worktree: `engine/.venv` angelegt (`pip install -r engine/requirements.txt`).
