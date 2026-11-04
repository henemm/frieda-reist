---
entity_id: altformen-sprache-bestand-267-c2
type: refactor
created: 2026-11-04
updated: 2026-11-04
status: draft
workflow: altformen-267-c2
issue: 267
---

# `BESTAND_REISE` entfällt (#267, PR c2; Teil 3 von #215)

Teilspec zu [altformen-entfernen-267.md](altformen-entfernen-267.md) (Abschnitt „PR c“, Abnahmebedingung b → c, AC-6, AC-7, AC-9).
Zuschnitt des Product Owners vom 4.11.2026: PR c1 löschte `routen.STUFEN_WORTE` (siehe [altformen-stufen-worte-267-c.md](altformen-stufen-worte-267-c.md),
auf `main`), dieses Paket ist c2.

## Purpose (Anlass)

`texte.BESTAND_REISE = "de"` ist die Bestandssprache: Eine `reise.yaml` ohne Feld `sprache` gilt als deutsch (Reisen von vor
ADR-0006). Seit PR b trägt `neu.py nachziehen` das Feld ein, und der Nachweis b → c liegt vor (alle Reisen des Reisen-Repos haben
`sprache`, Kommentar in #267 vom 4.11.2026). Die Lesetoleranz ist damit toter Code und widerspricht ADR-0006 („die Sprache steht
ausdrücklich in der Datei“). Sie fällt, ohne Ersatz-Konstante.

## Lösung

### Verhalten

- **`engine/texte.py`:** Konstante `BESTAND_REISE` (Z. 18) löschen. In `_einzeln` (Z. 144) meinte die Bedingung
  `kuerzel != BESTAND_REISE` nie den Bestand einer Reise, sondern: Die Namen der Schnittstelle (Parameter und Werte, `_RAND`,
  aus `schnittstelle.py`) sind schon Wörter dieser Sprache, ein Rückfall auf ihre englischen Namen wäre falsch. Nur 17 der 136
  `_RAND`-Werte haben in `texte_de` einen `wert.`-Eintrag (Befund RED, 4.11.2026); fiele die Bedingung ersatzlos, zeigte Deutsch
  `kind` statt `art`. Deshalb trägt die Sprachdatei diese Eigenschaft selbst (ADR-0006: der Code kennt keine Sprache beim Namen):
  optionales Feld `NAMEN_DER_SCHNITTSTELLE = True` in `texte_de.py` (kein Pflichtfeld; andere Sprachen lassen es weg). `_einzeln`
  greift auf `_RAND[wert]` nur zurück, wenn die Sprache das Feld nicht trägt und keinen Text `wert.<wert>` hat. Den
  119 fehlenden Werten `wert.`-Einträge zu geben, scheidet aus: Die Menge der Datenwerte (`_datenwerte`, AC-6) bliebe nicht gleich.
- **`engine/reise.py`:**
  - `Reise.sprache` (Z. 382–388): Fehlt das Feld oder ist es leer, meldet die Prüfung
    `self.fehl(texte.satz("pruefung.reise.sprache_fehlt", bekannt=", ".join(texte.SPRACHEN)))`; der Bau bricht. Ein
    vorhandener, aber unbekannter Wert bleibt `pruefung.reise.sprache_unbekannt`. Die Rückgabe bei Fehler ist `texte.VORGABE_REISE`
    (wie bei „unbekannt“), damit der Bau die weiteren Fehler noch sammelt.
  - `sprache_pruefen(wert)` (Z. 233–240): Parameter `leer` entfällt (einziger Nutzer war `Reise.sprache`); `None`/`""` ergibt
    weiter `(texte.VORGABE_REISE, None)` für den Aufruf aus `neu.py` (neue Reise ohne Angabe, Z. 158). Das Gegenstück für
    „fehlt im Bestand“ steht nur noch in `Reise.sprache` (Fehler). Docstring ohne Bestand.
  - `sprache_von` (Z. 220–230): Ohne Zeile `sprache:` gilt `texte.VORGABE_REISE` (derselbe Rückfall wie für unlesbare Dateien und
    unbekannte Kürzel). Docstring und Kopfkommentar Z. 6 ohne „Bestand“.
- **`engine/neu.py`:** Z. 650 (`etappen_ebenen`-Vorgabe „Unterwegs nachschlagen“) liest den Text weiter aus dem deutschen Katalog,
  jetzt ausdrücklich `texte.t("de", "inhalt.nachziehen.unterwegs")` mit Kommentar „die frühere Vorgabe war deutsch, #217“. Das
  ist der Wert der Altform-Umstellung (die alte Software-Vorgabe war deutsch), unabhängig von der Sprache der Reise; `nachziehen`
  liefert für Altreisen dasselbe Ergebnis wie bisher. `SPRACHE_NACHZIEHEN = "de"` bleibt; sein Kommentar (Z. 659) spricht nicht mehr von
  „Bestand“, sondern: der Wert, den `nachziehen` einträgt, weil für Reisen ohne Feld bisher Deutsch galt (keine Lesetoleranz).
- **`engine/schreiben.py`** (`einstellung_setzen`, Z. 2839–2840): Der Vergleich lautet `roh.get("sprache") != sprache` (ohne
  Ersatzwert; fehlendes Feld gilt als Änderung); als „von“ steht bei leerem Feld der Katalogtext
  `S("schreiben.antwort.einstellung.sprache_ungesetzt")`, sonst der alte Wert.
- **Katalog:** zwei neue Schlüssel in `engine/texte_de.py` und `engine/texte_en.py`:
  - `pruefung.reise.sprache_fehlt` (nennt `{bekannt}` und dass `neu.py nachziehen` das Feld einträgt),
  - `schreiben.antwort.einstellung.sprache_ungesetzt` („nicht gesetzt“ / „not set“).
- **Kommentare** „Sprache des Bestands“ → „Rückfall (`texte.VORGABE_REISE`)“, ohne Verhaltensänderung: `texte.py` Z. 115, 271;
  `konnektor.py` Z. 188, 200, 210, 1326, 2041; `konten.py` Z. 73; `kalender.py` Z. 275. `texte.py` Z. 339 (`str(Satz)` ist der
  deutsche Satz) wird nur dort geändert, wo „Bestand“ für `BESTAND_REISE` steht; je Stelle beim Umsetzen prüfen. Nicht betroffen:
  „Bestandsdaten“ in `neu.py arten-ableiten`, `schreiben.quelle_bestand`, `routen.py` Z. 33.
- **Doku:** `docs/sprachen.md`, Abschnitt „Rückfall und Bestand“ (Z. 88–91) wird „Rückfall“: der Punkt zu `BESTAND_REISE` entfällt,
  neuer Punkt „`sprache:` steht in jeder `reise.yaml`; ohne Feld bricht der Bau mit `pruefung.reise.sprache_fehlt`, `neu.py
  nachziehen` trägt `de` ein“. `docs/betrieb.md` Z. 116 („fehlt das Feld, gilt `de`“) wird entsprechend geändert (Bau bricht, `nachziehen` trägt ein);
  Z. 239 (Umstellen) stimmt schon. Beim Umsetzen mit `grep -n "ohne Feld\|fehlt das Feld\|Bestand" docs/*.md docs/adr/*.md` auf weitere Stellen prüfen.
- Kein Format der Reisedaten ändert sich neu: Die Umstellung gibt es seit PR b (`nachziehen` trägt `sprache` ein); c2 braucht keine
  weitere Umstellung in `neu.py nachziehen`.

## Source

- **Datei:** `engine/texte.py` — **Identifier:** `BESTAND_REISE`, `_einzeln`
- **Datei:** `engine/reise.py` — **Identifier:** `sprache_von`, `sprache_pruefen`, `Reise.sprache`
- **Datei:** `engine/neu.py` — **Identifier:** Vorgabe `etappen_ebenen` in `nachziehen`, `SPRACHE_NACHZIEHEN`
- **Datei:** `engine/schreiben.py` — **Identifier:** `einstellung_setzen`

## Dependencies

| Abhängigkeit | Richtung | Bemerkung |
|---|---|---|
| `texte.SPRACHEN`, `texte.gueltig`, `texte.VORGABE_REISE`, `texte.satz` | upstream | unverändert genutzt |
| Katalog `inhalt.nachziehen.unterwegs` | upstream | bleibt deutsch gelesen (Wert der Umstellung) |
| PR b (`nachziehen` trägt `sprache` ein) | upstream | auf `main`; Voraussetzung, Nachweis b → c im Issue |
| `bauen.py` (über `Reise`), `waechter.py`, `neu.py`, `schreiben.py` (über `sprache_von`) | downstream | Verhalten nur für Reisen ohne Feld geändert |
| Konnektor `setting_set` (über `einstellung_setzen`) | downstream | neue Antwort „nicht gesetzt“ bei fehlendem Feld |

## Scope (Betroffene Dateien)

| Datei | Änderung |
|---|---|
| `engine/texte.py` | `BESTAND_REISE` löschen; `_einzeln` ohne Bestandsbedingung; Docstrings Z. 115, 271 |
| `engine/reise.py` | Kopfkommentar; `sprache_von` → `VORGABE_REISE`; `sprache_pruefen` ohne `leer`; `Reise.sprache` meldet `sprache_fehlt` |
| `engine/neu.py` | Z. 650 `texte.t("de", …)` mit Kommentar; Kommentar Z. 659 |
| `engine/schreiben.py` | `einstellung_setzen`: Vergleich ohne Ersatz, „von“ = `sprache_ungesetzt` |
| `engine/texte_de.py`, `engine/texte_en.py` | zwei neue Schlüssel; `texte_de.py` zusätzlich `NAMEN_DER_SCHNITTSTELLE = True` |
| `engine/konnektor.py`, `engine/konten.py`, `engine/kalender.py` | nur Kommentare |
| `docs/sprachen.md`, `docs/betrieb.md` | Bestandsfall streichen |
| `engine/tests/test_texte.py` | `_datenwerte()` liest aus `texte.VORGABE`; Suchtest; Test auf `_einzeln("de", …)` |
| `engine/tests/test_neu.py` | Z. 360–385 umschreiben (siehe Tests) |
| `engine/tests/test_bauen.py` | Test „ohne Feld bricht der Bau“; Vorlagen `GRUND_YAML` (Z. 107), `REISE_YAML` (Z. 404) mit `sprache: de` |
| `engine/tests/test_schreiben.py` | `einstellung_setzen` ohne Feld |
| `engine/tests/test_pwa.py`, `test_regeln.py`, `test_reiseueberblick.py`, `test_waechter.py` | Testvorlagen, die durch den Bau laufen, mit `sprache: de`; endgültige Liste ergibt der erste Lauf der Suite (RED) |

`engine/tests/test_betrieb.py` Z. 1536 (`titel: x`) prüft nur den Ordner und bleibt, falls der erste Lauf nichts anderes zeigt.

### Estimated Changes

- Code und Texte: ca. +60 / −25 Zeilen in 8 Dateien (davon 3 nur Kommentare), Doku 2 Dateien
- Tests: ca. +40 / −15 Zeilen in 6–8 Dateien
- Risiko: mittel (Verhalten ändert sich nur für Reisen ohne Feld `sprache`, die es laut Nachweis nicht mehr gibt)

## Acceptance Criteria

- **AC-1 (Bau ohne Feld):** Given eine Reise, deren `reise.yaml` kein Feld `sprache` hat, When sie gebaut wird, Then bricht der Bau
  mit der Meldung `pruefung.reise.sprache_fehlt`; der Text nennt alle Kürzel aus `texte.SPRACHEN` und `neu.py nachziehen`.
  (AC-7 der Gesamtspec)
- **AC-2 (leeres Feld):** Given `sprache:` ohne Wert (oder `sprache: ""`), When gebaut wird, Then dieselbe Meldung wie AC-1.
  Ein unbekanntes Kürzel meldet weiter `pruefung.reise.sprache_unbekannt`.
- **AC-3 (nach `nachziehen`):** Given eine Reise ohne Feld, When `neu.py nachziehen` (mit Schreiben) lief, Then steht `sprache: de`
  in der Datei, die Reise baut ohne Fehler, die Seite ist deutsch (`lang="de"`), und die Meldungen/Dateien, die `nachziehen`
  dabei schreibt, sind deutsch wie bisher (auch die Vorgabe „Unterwegs nachschlagen“ in `reise.json`).
- **AC-4 (`BESTAND_REISE` weg):** In keiner Nicht-Testdatei unter `engine/` kommt `BESTAND_REISE` vor. Der Suchtest setzt den
  Namen zusammen und schließt `engine/tests/` aus, sodass er sich nicht selbst findet. (AC-7)
- **AC-5 (`_einzeln`):** Given Sprache `de`, When `texte._einzeln("de", w)` für jeden Schlüssel `w` aus `texte._RAND` aufgerufen wird,
  Then liefert es den Katalogtext `wert.<w>` oder `None` (das Wort bleibt), nie den englischen Namen `_RAND[w]`. Für `en` und die
  Pseudo-Sprache der Tests bleibt der Rückfall auf `_RAND` wie bisher. `texte_de.py` trägt `NAMEN_DER_SCHNITTSTELLE = True`, keine
  andere Sprachdatei; `_einzeln` liest die Eigenschaft aus der Sprachdatei (kein Sprachkürzel im Code).
- **AC-6 (Prüfstelle `_datenwerte`):** `_datenwerte()` in `test_texte.py` liest die Schlüssel `wert.*` aus `texte.VORGABE`; die Menge
  ist gleich der aus dem deutschen Katalog (Paritätstest de/en über alle `wert.`-Schlüssel). Damit ändert sich die Menge der
  erlaubten Datenwerte nicht, und die Ausnahmelisten in `engine/tests/test_texte.py` sind gegenüber `main` nicht länger geworden.
  (AC-9)
- **AC-7 (`sprache_von`):** Given eine `reise.yaml` ohne Zeile `sprache:`, When `sprache_von` läuft (Test mit Marke
  `echter_rueckfall`), Then ist das Ergebnis `texte.VORGABE_REISE` (Englisch); mit gültigem Feld das Kürzel; mit unbekanntem Kürzel
  oder ohne lesbare Datei wie bisher `texte.VORGABE_REISE`.
- **AC-8 (`sprache_pruefen`):** Die Funktion hat keinen Parameter `leer`; `None`/`""` ergibt `(texte.VORGABE_REISE, None)`; ein
  gültiges Kürzel wird normalisiert; ein unbekanntes liefert `pruefung.reise.sprache_unbekannt`.
- **AC-9 (`einstellung_setzen`):** Given `setting_set` mit `sprache: en` für eine Reise mit Feld `de`, Then meldet die Antwort
  „de → en“ wie bisher. Given dieselbe Eingabe, aber `reise.yaml` ohne Feld (Datei direkt geschrieben), Then meldet die Antwort
  als „von“ den Katalogtext `schreiben.antwort.einstellung.sprache_ungesetzt`, trägt `en` ein, und die Änderung gilt als
  Änderung (keine Ablehnung `einstellung_setzen.4`). Gibt man dasselbe Kürzel wie das gesetzte noch einmal an, bleibt die
  Ablehnung `einstellung_setzen.4`.
- **AC-10 (Katalog):** `pruefung.reise.sprache_fehlt` und `schreiben.antwort.einstellung.sprache_ungesetzt` stehen in `texte_de.py`
  und `texte_en.py` (und damit in jeder Sprachdatei, die der Katalogtest `test_texte.py` kennt, einschließlich der Pseudo-Sprache der Tests); die Platzhalter beider Sprachen stimmen überein.
- **AC-11 (Testvorlagen):** Jede Testvorlage, die eine `reise.yaml` schreibt und durch den Bau läuft, trägt `sprache: de`
  (Beispielwert); `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün.
- **AC-12 (keine Verhaltensänderung sonst):** Bau und Seiten beider Beispielreisen (`beispielreise`, `stadtwochenende`) sind vor und
  nach dem Paket gleich (Bau mit dem Branch und mit `main`, Vergleich der gebauten Seiten), ebenso die Meldungstexte in de, en und
  der Pseudo-Sprache der Tests. (AC-9 der Gesamtspec)
- **AC-13 (Abnahme b → c, AC-6 der Gesamtspec):** Vor dem Vorspulen sind im PR-Text belegt: (a) lesende Prüfung am Stand von `main` des
  Reisen-Repos: in jeder `reisen/*/reise.yaml` steht ein gültiges Feld `sprache` (kein Treffer bei `grep -L '^sprache:'`, die Werte
  aus `grep -h '^sprache:'` sind Kürzel aus `texte.SPRACHEN`), ebenso in jedem weiteren Reisen-Repo, das die Software einbindet;
  (b) der Probebau jeder Reise mit dem Branch ist grün; (c) die Tests der einbindenden Instanz laufen mit dem Branch grün (dieses
  Paket ändert Meldungstexte). Reisenamen, Pfade und Adressen stehen nicht in der Spec, sondern nur im PR-Text.

## Test Plan (Geplante Tests)

| AC | Datei | Test |
|---|---|---|
| AC-1, AC-2 | `engine/tests/test_bauen.py` | `test_reise_ohne_sprache_bricht_den_bau` (parametrisiert: Feld fehlt, `sprache:` leer; `meldet(…, "pruefung.reise.sprache_fehlt")`), `test_sprache_fehlt_nennt_kuerzel_und_nachziehen`, `test_sprache_unbekannt_bleibt` |
| AC-3 | `engine/tests/test_neu.py` | `test_reise_ohne_feld_sprache_baut_erst_nach_nachziehen` (ersetzt `test_reise_ohne_feld_sprache_bleibt_deutsch`); `test_nachziehen_unterwegs_vorgabe_ist_deutsch` |
| AC-4 | `engine/tests/test_texte.py` | `test_bestand_reise_kommt_nicht_mehr_vor` (Name aus zwei Teilen, ohne `engine/tests/`) |
| AC-5 | `engine/tests/test_texte.py` | `test_einzeln_de_liefert_deutsche_namen` (über alle `_RAND`-Werte, Sicherungstest: grün vor und nach), `test_einzeln_en_und_pseudo_fallen_auf_rand_zurueck`, `test_namen_der_schnittstelle_steht_in_der_sprachdatei` |
| AC-6 | `engine/tests/test_texte.py` | `_datenwerte()` aus `texte.VORGABE`; `test_datenwerte_paritaet_de_en`; vorhandener Test der Ausnahmelisten bleibt |
| AC-7 | `engine/tests/test_neu.py` | `test_rueckfall_ist_englisch…` (Z. 360–385, Aussage zu `BESTAND_REISE` entfällt) mit Marke `echter_rueckfall`: `sprache_von` ohne Feld → `VORGABE_REISE` |
| AC-8 | `engine/tests/test_neu.py` | `test_sprache_pruefen_ohne_leer` |
| AC-9 | `engine/tests/test_schreiben.py` | `test_einstellung_sprache_mit_feld`, `test_einstellung_sprache_ohne_feld_meldet_nicht_gesetzt`, `test_einstellung_gleiche_sprache_ablehnung` |
| AC-10 | `engine/tests/test_texte.py` | vorhandener Katalog-Paritätstest (Schlüssel, Platzhalter) |
| AC-11 | `engine/tests/test_pwa.py`, `test_regeln.py`, `test_reiseueberblick.py`, `test_waechter.py`, `test_bauen.py` | Vorlagen angepasst; gesamte Suite |
| AC-12 | Handnachweis im PR-Text | Bau beider Beispielreisen mit Branch und `main`, Vergleich |
| AC-13 | Handnachweis im PR-Text | lesende Prüfung, Probebau, Instanz-Tests |

Die Tests prüfen Meldungen über den Katalogschlüssel (`meldet()`), nicht über den Wortlaut. Die RED-Phase beginnt mit den Tests zu
AC-1 bis AC-9; die Vorlagen (AC-11) folgen dem ersten Lauf.

## Risiken

- **Kritischer Pfad:** Jede Reise ohne `sprache` baut danach nicht. Abgesichert durch AC-13 (lesende Prüfung und Probebau vor dem
  Vorspulen) und den Nachweis aus PR b.
- **`_datenwerte()` aus `texte.VORGABE`:** Weichen die `wert.`-Mengen von de und en ab, ändert sich, was als Datenwert (kein Text)
  gilt, und die Ausnahmelisten würden länger. Der Paritätstest (AC-6) fängt das vor der Umstellung ab; ist die Menge ungleich, wird
  der Katalog angeglichen, nicht die Ausnahmeliste verlängert.
- **`sprache_von` ohne Feld → Englisch:** betrifft nur Dateien, die der Bau ablehnt oder die `nachziehen` gleich umstellt.
  `nachziehen` trägt `sprache` vor den Schritten ein, die `sprache_von` nutzen (PR b); AC-3 sichert das ab.
- **Der Suchtest** darf sich nicht selbst finden (AC-4: Name zusammengesetzt, `engine/tests/` ausgeschlossen).
- **Testvorlagen:** Fixtures ohne Feld brechen nach der Änderung; der erste Lauf der Suite nennt sie alle. Ein Test, der eine
  Reise absichtlich ohne Feld braucht, sagt das ausdrücklich.
- **Laufzeit:** Die volle Testsuite braucht rund 20 Minuten; sie läuft vor dem Vorspulen einmal vollständig.
- Parallel arbeitende Sitzungen: Spur B (`schreiben.py`, `neu.py`, `konnektor.py`) beachten; vor dem Vorspulen auf `main` rebasen.

## Abgrenzung

- `STUFEN_WORTE` ist c1 und erledigt; `typ`/`art` und weitere Altformen sind PR d.
- `neu.SPRACHE_NACHZIEHEN` bleibt `"de"` (Wert der Umstellung, keine Lesetoleranz).
- Keine Änderung an Wortlauten bestehender Meldungen, keine Reisespezifika, keine Änderung echter Reisen von Hand: Die Umstellung
  der Reisen geschieht ausschließlich durch den Workflow „Software nachziehen“.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Begründung:** Keine neue Architekturentscheidung. Das Paket setzt [ADR-0006](../../adr/0006-mehrsprachigkeit.md) um (die Sprache steht ausdrücklich in der
`reise.yaml`) und folgt der Prüfstelle aus [ADR-0001](../../adr/0001-kern.md) wie die Gesamtspec (Abschnitt „Prüfstelle ADR-0001“).

## Definition of Done

- [ ] AC-1 bis AC-11 durch automatische Tests belegt, `engine/.venv/bin/python -m pytest -q engine/tests` grün ohne echte Reisen
- [ ] AC-12 und AC-13 im PR-Text belegt (Vergleich der Beispielreisen, lesende Prüfung, Probebau, Instanz-Tests mit dem Branch)
- [ ] `docs/sprachen.md` und `docs/betrieb.md` ohne Bestandsfall
- [ ] CI grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Commit auf `main` vorgespult
- [ ] Kommentar in #267 mit Stand c2; #267 erst nach PR d schließen

## Changelog

- 2026-11-04: Erstfassung (Workflow `altformen-267-c2`, aus Gesamtspec Abschnitt „PR c“ ohne c1)
- 2026-11-04 (RED): `_einzeln` und AC-5 berichtigt. Die Annahme „`texte_de` hat zu jedem `_RAND`-Wert einen `wert.`-Eintrag“ trifft nicht zu (17 von 136); die Eigenschaft „Namen der Schnittstelle sind Wörter dieser Sprache“ steht künftig als `NAMEN_DER_SCHNITTSTELLE` in der Sprachdatei.

## Approval

- [ ] Approved
