---
entity_id: altformen-typ-art-267-d
type: refactor
created: 2026-11-04
updated: 2026-11-04
status: draft
workflow: altformen-267-d
issue: 267
---

# Lesepfade `typ` und Einzelwert (#267, PR d)

Teilspec zu [altformen-entfernen-267.md](altformen-entfernen-267.md) (Abschnitt „PR d“, AC-10, AC-11, AC-13, Entscheidung 2).
PR a, b, c1 und c2 sind auf `main` (siehe [altformen-stufen-worte-267-c.md](altformen-stufen-worte-267-c.md),
[altformen-sprache-bestand-267-c2.md](altformen-sprache-bestand-267-c2.md)); dieses Paket ist der letzte Teil von #267.

## Purpose (Anlass)

Der Bau liest an Unterkunft, Aufenthalt und Nacht den früheren Schlüssel `typ` noch als Ersatz für `art` (`routen.py`,
`Routen.art_von`). Seit #250 stellt `neu.py nachziehen` jede Reise um (`typ_zu_art`), der Befund vom 4.11.2026 ist 0 Zeilen
`typ:` an Unterkünften und Nächten in allen sieben `routen.yaml` des Reisen-Repos und in beiden Beispielreisen. Die Brücke ist damit
toter Code und widerspricht dem Grundsatz „eine Form pro Ding“. Sie fällt; der Bau bricht bei einem früheren `typ` laut und nennt
die Umstellung. Im Schreibweg (`schreiben.py`) entfallen die Lesepfade `typ` mit.

## Berichtigung der Mutter-Spec

Die Mutter-Spec nennt im Abschnitt „PR d“ den Fehler `pruefung.routen.65` („art fehlt“). Das ist falsch: `pruefung.routen.65`
gilt für Strecken. Der Fehler für eine fehlende Art an Unterkunft, Aufenthalt und Nacht ist **`pruefung.routen.62`**
(`art_von`, Befund der Analyse 4.11.2026, am Code bestätigt). Diese Spec gilt vor der Mutter-Spec; die Mutter-Spec wird im
Abschnitt „PR d“ nicht nachträglich geändert, dieser Vermerk genügt.

## Scope

**In:**

- `engine/routen.py`: `art_von` liest nur `art`; die Bedingung in `nacht` behält `typ`, damit eine Nacht mit nur `typ` laut bricht.
- `engine/texte_de.py`, `engine/texte_en.py`: Text von `pruefung.routen.62` (kein neuer Schlüssel).
- `engine/schreiben.py`: beide Definitionen von `art_schluessel_von` entfallen; Aufrufer lesen nur `art`; `alt` für das Feld `art`
  liest nur `art`; Kommentar zum Aufräumen von `typ`; Kommentar zur Einzelform in `wert_eintragen`.
- Tests (siehe unten).

**Out:**

- `neu.py`: `arten_ableiten` und `typ_zu_art` bleiben unverändert. `typ_zu_art` ist die Umstellung selbst; `arten_ableiten` ist das
  Einführungswerkzeug für Bestandsdaten (liest tolerant, der Bau hängt nicht davon ab).
- Einzelform eines Merkmalswerts (`wert_eintragen`): nur ein Kommentar, kein Verhalten (Mutter-Spec, Entscheidung 2).
- Kein neuer Textschlüssel; keine neue Umstellung in `nachziehen` (sie besteht seit #250 und ist durch den Test unten belegt).
- `typ` als Datentyp einer Merkmalsdefinition in `arten.yaml` (`text`, `geld`, `zahl`, `auswahl`, `link`, `zeitpunkt`, `adresse` u. a.):
  keine Altform, unberührt.
- `routen.art_schluessel` bleibt (viele Nutzer).

### Estimated Changes

- Code und Texte: ca. +15 / −15 Zeilen in 4 Dateien (`routen.py`, `schreiben.py`, `texte_de.py`, `texte_en.py`)
- Tests: ca. +80 / −15 Zeilen in 4 Dateien (`test_routen.py`, `test_neu.py`, `test_schreiben.py`, `test_texte.py`)
- Risiko: niedrig (geändert werden Lesepfade, die in keiner Reise etwas treffen, und ein Meldungstext)

## Lösung

### Verhalten

- **`Routen.art_von(eintrag, wo)`:** `a = eintrag.get("art")`. Fehlt `art` und steht kein `an_bord`, meldet der Bau
  `pruefung.routen.62` mit `wo` und liefert `None` (wie bisher, nur ohne Ersatz aus `typ`). Der Docstring nennt nur noch `art:`
  („Art einer Unterkunft, eines Aufenthalts oder einer Nacht: `art:`; an Bord ohne Angabe: unterwegs. Prüft gegen arten.yaml“).
  Die Meldungen 63 und 64 bleiben unverändert. Aufrufer: Unterkunft, Aufenthalt, Nacht.
  Ausnahme von der Vorgabe „an Bord ohne Angabe: unterwegs“: Fehlt `art`, steht aber der frühere Schlüssel `typ`, meldet `art_von`
  immer 62, auch mit `an_bord`. Bisher lieferte `typ` dort die Art; ohne diese Ausnahme würde eine nicht umgestellte Nacht an Bord
  still zu „unterwegs“ statt laut zu brechen. `typ` wird dabei nur auf Vorhandensein geprüft, nie als Art gelesen.
- **`nacht`:** Die Bedingung `n.get("typ") or n.get("art") or n.get("an_bord")` bleibt wörtlich. Eine Nacht mit nur `typ` wird damit
  geprüft, `art_von` findet keine `art` und meldet 62. Fiele `typ` aus der Bedingung, bekäme die Nacht still keine Art; das wäre
  stilles Verlassen und ist ausgeschlossen. Ein Kommentar an der Bedingung nennt den Grund („`typ` bleibt in der Bedingung, damit
  eine nicht umgestellte Nacht laut mit 62 bricht, nicht still ohne Art“).
- **Text `pruefung.routen.62`** (Platzhalter bisher und künftig nur `{wo}`, am Code geprüft):
  - de, bisher: `{wo}: braucht typ oder art (eine Art aus plan/arten.yaml).`
  - de, neu: `{wo}: braucht art (eine Art aus plan/arten.yaml). Steht noch der frühere Schlüssel typ, stellt „neu.py nachziehen“ ihn auf art um.`
  - en, bisher: `{wo}: needs typ or art (a kind from plan/arten.yaml).`
  - en, neu: `{wo}: needs art (a kind from plan/arten.yaml). If the old key typ is still there, "neu.py nachziehen" converts it to art.`

  Der Hinweis steht immer im Text (ein Satz), weil zwei Varianten ein neuer Schlüssel wären. Die Schreibweise der Anführungszeichen
  folgt der Datei, in der der Text steht (de: „…“, en: "…"); der Befehl `neu.py nachziehen` bleibt in beiden Sprachen unübersetzt.
- **Schreibweg (`schreiben.py`):**
  - Beide Definitionen von `art_schluessel_von` (die erste vor `_ding_aendern_felder`, die zweite vor `arten_uebernehmen`; die zweite
    gilt, weil sie später im Modul steht) werden gelöscht.
  - Aufrufer in `_ding_aendern_felder` (Katalog der Merkmale): `art = knoten.get("art")`. Aufrufer beim Zusammenführen und Übernehmen
    der Arten (Stelle `knoten.get("art") or art_schluessel_von(knoten)`): `knoten.get("art") == art`.
  - In `_ding_aendern_felder` ist `alt` für das Feld `art` einfach `knoten.get("art")`; der lokale Import `from routen import art_schluessel`
    in `_ding_aendern_felder` entfällt (Befund: die Zeile für `alt` ist dort seine einzige Nutzung). Die übrigen lokalen Importe von
    `art_schluessel` in anderen Funktionen bleiben.
  - Das Entfernen von `typ`, sobald `art` gesetzt wird (`if feld == "art" and "typ" in knoten: del knoten["typ"]`), bleibt: Aufräumen der
    Datei, kein Lesepfad. Der Kommentar „Brücke typ: entfällt …“ wird zu „räumt einen früheren typ: auf, sobald art: steht“.
  - Begründung: Der Konnektor baut vor jedem Schreiben probehalber; eine Reise mit `typ` baut nicht mehr, der Schreibweg kann sie
    nicht mehr treffen.
- **Einzelform (`wert_eintragen`):** Kommentar an `alt = merkmale.get(k)` / `alte = list(alt) if isinstance(alt, list) else [alt] …`:
  „Einzelform (ein Eintrag ohne Liste) ist gültig und bleibt Lesetoleranz; der Bau liest dieselbe Form (`routen.py`, `v if isinstance(v, list) else [v]`).
  Kein Umstellen: ein nackter Wert hat keine Herkunft, die `nachziehen` erfinden dürfte (ADR-0001).“ Kein Verhalten ändert sich.

### Reihenfolge der Umsetzung

1. Tests in `test_routen.py` auf `art` umstellen und Fehlertests schreiben (RED).
2. `art_von` und Kommentar in `nacht`.
3. Text 62 in beiden Sprachen.
4. `schreiben.py`: Lesepfade und Kommentare.
5. Ende-zu-Ende-Test mit `nachziehen`.

## Source

- **Datei:** `engine/routen.py` — **Identifier:** `Routen.art_von`, `Routen.nacht`
- **Datei:** `engine/schreiben.py` — **Identifier:** `art_schluessel_von` (zwei Definitionen), `_ding_aendern_felder`, Zusammenführen der Arten (Aufrufer von `art_schluessel_von`), `wert_eintragen`
- **Datei:** `engine/texte_de.py`, `engine/texte_en.py` — **Identifier:** `pruefung.routen.62`
- **Datei:** `engine/neu.py` — **Identifier:** `typ_zu_art`, `arten_ableiten` (unverändert, nur Bezug)

## Betroffene Dateien

| Datei | Änderung |
|---|---|
| `engine/routen.py` | MODIFY: `art_von` liest nur `art` (Docstring); Kommentar an der Bedingung in `nacht` |
| `engine/schreiben.py` | MODIFY: beide `art_schluessel_von` löschen; Aufrufer und `alt` für `art` lesen nur `art`; Kommentare zu Aufräumen und Einzelform |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY: Text von `pruefung.routen.62` |
| `engine/tests/test_routen.py` | MODIFY: Grunddaten `roh()` (U-01..U-03) und Nächte mit `typ` auf `art`; `test_unterkunft_art_aus_typ_oder_ausdruecklich` wird Fehlertest |
| `engine/tests/test_neu.py` | MODIFY: Ende-zu-Ende-Test mit `nachziehen` |
| `engine/tests/test_schreiben.py` | MODIFY: Tests zu `ding_aendern` (Katalog nach `art`), Fehlen von `art_schluessel_von`, Einzelform |
| `engine/tests/test_texte.py` | MODIFY: Test, dass Text 62 in jeder Sprache `art` und `nachziehen` nennt |
| `engine/neu.py` | unverändert |

## Dependencies

| Abhängigkeit | Richtung | Bemerkung |
|---|---|---|
| `routen.art_schluessel`, `texte.satz` | upstream | unverändert genutzt |
| `neu.py nachziehen` (`typ_zu_art`) | upstream | liefert die Umstellung, unverändert |
| Konnektor (`ding_aendern`, Arten zusammenführen/übernehmen) | downstream | liest über `schreiben.py` nur noch `art` |
| Bau beider Beispielreisen, Instanz-Tests im Reisen-Repo | downstream | Meldungstext 62 ändert sich |

## Acceptance Criteria

Alle AC prüfbar durch Tests oder den genannten Befehl; ohne echte Reisen.

- **AC-1:** Given eine Reise, in der eine Unterkunft `typ: Hotel` und kein `art` trägt, when der Bau läuft, then bricht er mit
  `pruefung.routen.62` (Text mit „Unterkunft U-…“ als `{wo}`), und `typ` ersetzt `art` nicht.
- **AC-2:** Given ein Aufenthalt (Ding der Grundform Aufenthalt ohne Nacht) mit `typ` und ohne `art`, when der Bau läuft, then
  bricht er mit `pruefung.routen.62` (`{wo}` = „Aufenthalt A-…“).
- **AC-3:** Given eine Nacht `{ort: …, typ: …}` ohne `art` und ohne `an_bord`, when der Bau läuft, then bricht er mit
  `pruefung.routen.62` (`{wo}` = „<Tag> nacht“), nicht still ohne Art.
- **AC-3b:** Given eine Nacht mit `an_bord: true` und `typ`, aber ohne `art`, when der Bau läuft, then bricht er mit
  `pruefung.routen.62` und setzt nicht still `unterwegs`; eine Nacht mit `an_bord: true` ohne `typ` und ohne `art` bekommt weiter
  `unterwegs` ohne Fehler.
- **AC-4:** Given dieselben Daten mit `art:` statt `typ:` an Unterkunft, Aufenthalt und Nacht, when der Bau läuft, then ist er grün
  und die Ausgabe nennt die Arten wie vor PR d (Art und Artname je Unterkunft und Nacht gleich).
- **AC-5:** Given eine Unterkunft mit `typ: Tempel` und `art: huette`, when der Bau läuft, then gilt `huette` und es gibt keinen
  Fehler (`typ` wird ignoriert, nicht ausgewertet).
- **AC-6:** Given beide Beispielreisen (`beispielreise`, `stadtwochenende`) und `engine/reisevorlage/`, when sie bauen, then sind sie
  grün; `grep -rn "^ *typ:" beispiel/reisen/*/plan/routen.yaml engine/reisevorlage` ohne Treffer.
- **AC-7 (Ende zu Ende):** Given eine Kopie der Beispielreise (Testordner), in der eine Unterkunft und eine Nacht `art` durch den
  früheren `typ` ersetzt haben, when der Bau läuft, then meldet er 62; when `neu.py nachziehen` die Kopie umstellt, then steht `art`
  an beiden Stellen (kein `typ` mehr), und der Bau ist grün; ein zweiter Lauf von `nachziehen` ändert keine Datei.
- **AC-8:** Given eine Reise mit `art`-Feldern, when `ding_aendern` ein Feld einer Unterkunft ändert, then richtet sich der
  Merkmalskatalog nach `art` des Knotens; given ein Knoten mit nur `typ` (ohne `art`), then wird kein Katalog aus `typ` abgeleitet.
  Das Setzen von `art` entfernt einen vorhandenen `typ` aus dem Knoten (Aufräumen bleibt).
- **AC-9:** Given der Quelltext von `engine/schreiben.py`, then enthält er keine Definition und keinen Aufruf von `art_schluessel_von`
  und keinen Lesezugriff `knoten.get("typ")`; `routen.py` liest `typ` an Unterkunft, Aufenthalt und Nacht nirgends als Ersatz für `art`
  (`art_von` prüft `typ` nur auf Vorhandensein, um laut mit 62 zu brechen, und gibt nie einen aus `typ` abgeleiteten Wert zurück;
  die Bedingung in `nacht` trägt den Kommentar).
- **AC-10 (Texte):** Given `pruefung.routen.62`, then steht der neue Text in `texte_de.py` und `texte_en.py` (nennt `art`, nicht
  `typ oder art`, und den Hinweis auf `neu.py nachziehen`), `{wo}` ist der einzige Platzhalter; `engine/tests/test_texte.py` ist grün und
  die Ausnahmelisten darin sind nicht länger geworden.
- **AC-11 (Einzelform):** Given ein Merkmal mit einem einzelnen Eintrag ohne Liste in der Datei, when `wert_eintragen` einen Wert
  schreibt, then verhält es sich wie vor PR d (Eintrag wird als Liste weitergeführt); der Kommentar zur Einzelform steht an der Stelle.
- **AC-12 (unverändert):** `neu.py` ist im Diff nicht enthalten; `engine/tests/test_neu.py` (`typ_zu_art`, `arten_ableiten`) bleibt grün
  ohne Änderung der bestehenden Fälle.
- **AC-13 (Gesamtlauf):** `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen (CI auf dem vorgespulten Commit).
- **AC-14 (Instanz-Tests, manueller Nachweis im PR-Text):** Weil sich der Meldungstext von 62 ändert, laufen vor dem Vorspulen die Tests
  der einbindenden Instanzen im Reisen-Repo mit dem Branch (Anleitung dort) und sind grün; der Probelauf des Baus aller echten Reisen
  mit dem Branch ist grün (lesend, Befund 0 × `typ:` bestätigt). Das Ergebnis steht im PR-Text.

## Test Plan (Geplante Tests)

| Datei | Test | Prüft |
|---|---|---|
| `engine/tests/test_routen.py` | `roh()` (Grunddaten) | U-01..U-03 und Nächte mit `art` statt `typ`; alle übrigen bestehenden Tests laufen unverändert weiter |
| `engine/tests/test_routen.py` | `test_unterkunft_art_aus_typ_oder_ausdruecklich` wird `test_unterkunft_typ_ohne_art_bricht_mit_62` | AC-1; Fehlertext enthält den Hinweis auf `nachziehen` |
| `engine/tests/test_routen.py` | `test_unterkunft_art_gilt_typ_daneben_ignoriert` (neu) | AC-5: `typ: Tempel` neben `art: huette` → Art `huette`, kein Fehler |
| `engine/tests/test_routen.py` | `test_aufenthalt_typ_ohne_art_bricht_mit_62` (neu) | AC-2 |
| `engine/tests/test_routen.py` | `test_nacht_nur_typ_bricht_laut_mit_62` (neu) | AC-3: Fehlerliste enthält 62, keine Nacht ohne Art ohne Fehler |
| `engine/tests/test_routen.py` | `test_nacht_an_bord_mit_typ_bricht_mit_62` (neu) | AC-3b: an Bord mit `typ` ohne `art` → 62; an Bord ohne beides → `unterwegs`, kein Fehler |
| `engine/tests/test_routen.py` | `test_unterkunft_nacht_aufenthalt_mit_art_bauen` (neu) | AC-4: Arten und Artnamen in der Ausgabe |
| `engine/tests/test_neu.py` | `test_nachziehen_stellt_typ_an_unterkunft_und_nacht_um_bau_gruen` (neu) | AC-7: Kopie der Beispielreise in `tmp_path`, Bau 62, `nachziehen`, Bau grün, zweiter Lauf ohne Änderung |
| `engine/tests/test_schreiben.py` | `test_ding_aendern_katalog_nach_art` (neu) | AC-8: Katalog nach `art`, nur `typ` ergibt keinen Katalog, `typ` wird beim Setzen von `art` entfernt |
| `engine/tests/test_schreiben.py` | `test_schreiben_ohne_art_schluessel_von` (neu) | AC-9: der Quelltext von `schreiben.py` enthält den Namen nicht (Name im Test aus Teilen zusammengesetzt) und hat keinen Lesezugriff `knoten.get("typ")` |
| `engine/tests/test_schreiben.py` | `test_merkmal_einzelform_bleibt_les_und_schreibbar` (neu) | AC-11: Verhalten; zusätzlich prüft der Test, dass der Quelltext von `wert_eintragen` den Kommentar „Einzelform“ enthält |
| `engine/tests/test_texte.py` | bestehende Prüfungen | AC-10: alle Sprachen, Ausnahmelisten nicht länger; ergänzend ein Test, dass der Text 62 in beiden Sprachen `nachziehen` und `art` nennt |

AC-6 belegen die vorhandenen Bau-Tests beider Beispielreisen; der Grep aus AC-6 läuft als Befehl in Phase 6 und steht im PR-Text.
AC-12 (`neu.py` nicht im Diff) belegt ein leerer Diff von `engine/neu.py` gegen `main` im PR-Text. Der Ende-zu-Ende-Test nutzt die Beispielreise
mit Nacht und Unterkunft (`beispielreise`); `stadtwochenende` bleibt im Bau-Test grün (Abnahme an zwei Reisetypen, #214).

## Risiken

- **Tests außerhalb von `test_routen.py`**, die Unterkünfte mit `typ` als YAML-String bauen, fallen erst im RED-Lauf auf. Die Analyse fand keine
  (übrige Treffer von `typ:` sind Datentypen von Merkmalen); der RED-Lauf der gesamten Suite beweist es. Fundstellen werden auf `art` umgestellt.
- **Meldungstext 62 ändert sich:** Instanz-Tests im Reisen-Repo könnten den Wortlaut prüfen (AC-14).
- **Reise mit `typ` und `an_bord` ohne `art`:** Bisher lieferte `typ` die Art. Damit sie nicht still zu `unterwegs` wird, meldet `art_von`
  hier 62 (AC-3b). Kein Datenfall (Befund 0 × `typ:`).
- **Doppelte Definition `art_schluessel_von`:** Löschen beider Definitionen ist nur sicher, wenn kein weiterer Aufrufer existiert; geprüft:
  die Analyse fand zwei Aufrufer, beide werden angepasst, `grep -rn art_schluessel_von engine --exclude-dir=tests` danach ohne Treffer (AC-9).
- **Reisen ohne Umstellung:** Eine Reise, die nie nachgezogen wurde, baut nicht mehr. Befund: keine. Der Fehlertext nennt den Weg,
  und die Umstellung läuft ohne Handschritt über den Workflow „Software nachziehen“ (#250).

## Prüfstelle ADR-0001

Kurz gegen die Prüfstelle: Die Änderung nimmt eine Altform aus dem Bau und fügt nichts Reisespezifisches in die Engine ein (Frage 1: beide
Beispielreisen bauen grün). Die Grundformen der Reise-Ontologie und die Form eines Merkmals bleiben unberührt; Arten bleiben Sache der Reise
(`arten.yaml`). Es gibt keine erfundenen Aussagen (nachziehen erfindet keine Herkunft, die Einzelform bleibt wegen genau dieser Regel).
Der Fehler ist laut, nicht still (Entscheidung 2). Der Text steht im Katalog in allen Sprachen (ADR-0006), Instanzspezifisches kommt nicht vor.
Ein Handschritt nach dem Software-Wechsel entsteht nicht: `nachziehen` stellt um, belegt durch AC-7.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Begründung:** Keine neue Architekturentscheidung. Das Paket setzt die Gesamtspec #267 fort (Altformen verlassen, laut brechen statt still)
  und folgt der Prüfstelle aus [ADR-0001](../../adr/0001-kern.md) (Abschnitt oben) und [ADR-0006](../../adr/0006-mehrsprachigkeit.md) für den Meldungstext.

## Definition of Done

- [ ] AC-1 bis AC-5, AC-7 bis AC-11 und AC-13 durch automatische Tests belegt; AC-6 und AC-12 zusätzlich per Befehl im PR-Text; `engine/.venv/bin/python -m pytest -q engine/tests` grün ohne echte Reisen
- [ ] AC-14 im PR-Text belegt (Instanz-Tests mit dem Branch, Probebau aller echten Reisen lesend)
- [ ] CI grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), Commit auf `main` vorgespult
- [ ] Kommentar in #267 mit Stand d; #267 schließen, wenn alle Teile (a bis d) auf `main` sind

## Changelog

- 2026-11-04: Entwurf (altformen-267-d), Berichtigung `pruefung.routen.62` statt `.65` gegenüber der Mutter-Spec.
- 2026-11-04: AC-3b (an Bord mit `typ` ohne `art` bricht laut), Estimated Changes, ADR, Definition of Done, Approval; Prüfweg AC-9 ohne Testordner.

## Approval

- [ ] Approved
