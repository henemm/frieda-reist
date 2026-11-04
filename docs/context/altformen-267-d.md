# Kontext: altformen-267-d (#267, PR d: Lesepfade `typ` und Einzelwert)

## Auftrag

Letzter Teil von #267 (Spec `docs/specs/betrieb/altformen-entfernen-267.md`, Abschnitt „PR d“, AC-10, AC-11):
Der Bau liest den früheren Schlüssel `typ` an Unterkunft, Aufenthalt und Nacht nicht mehr als Ersatz für `art`.
`neu.py nachziehen` stellt `typ` weiter um. Die Einzelform eines Merkmalswerts in `schreiben.py` bleibt als
Lesetoleranz und bekommt nur einen Kommentar.

## Befund an den Daten (4.11.2026, lesend)

- Reisen-Repo, `main` über die GitHub-API: 7 von 8 Reisen haben `plan/routen.yaml`
  (`testreise-abnahme-223-erfunden-2027` hat keine), 7598 Zeilen, **0 Zeilen `typ:`** mit Einrückung (also auch kein
  Datentyp eines Merkmals in `routen.yaml`; Datentypen stehen in `arten.yaml`).
- Beide Beispielreisen und `engine/reisevorlage/`: 0 Treffer `typ:` in `routen.yaml`.

## Betroffene Stellen

| Datei | Stelle | Befund |
|---|---|---|
| `engine/routen.py` | `art_von` (Z. 1043–1056) | `eintrag.get("art") or art_schluessel(eintrag.get("typ"))`; Aufrufer: Unterkunft (Z. 607), Aufenthalt (Z. 620), Nacht (Z. 1420) |
| `engine/routen.py` | `nacht` (Z. 1420) | ruft `art_von` nur, wenn `typ`, `art` oder `an_bord` steht |
| `engine/texte_de.py` / `texte_en.py` | `pruefung.routen.62` | „{wo}: braucht typ oder art …“ — **das ist der Fehler für fehlende Art an Aufenthalten**, nicht `pruefung.routen.65` (der gilt für Strecken). Die Spec nennt 65 irrtümlich. |
| `engine/schreiben.py` | `art_schluessel_von` **zweimal definiert** (Z. 1679 und Z. 3976; die zweite gilt) | Lesepfad `typ` im Schreibweg; Aufrufer Z. 1626 (`ding_aendern`, Katalog der Merkmale) und Z. 3954 (`attribute_merge`/Arten zusammenführen) |
| `engine/schreiben.py` | Z. 1764 | `alt` für das Feld `art`: `knoten.get("art") or art_schluessel(knoten.get("typ"))` |
| `engine/schreiben.py` | Z. 1775 | entfernt `typ`, sobald `art` gesetzt wird (Aufräumen, kein Lesepfad) |
| `engine/schreiben.py` | Z. 1044 (`wert_eintragen`) | `[alt]`, wenn kein Liste: Einzelform, Lesetoleranz (Spec Entscheidung 2) |
| `engine/neu.py` | `arten_ableiten` (Z. 313 ff.) | liest `art`, sonst `typ`: Einmal-Werkzeug zum Ableiten der Arten aus Bestandsdaten; nicht Teil des Baus |
| `engine/neu.py` | `typ_zu_art` in `nachziehen` (Z. 582–597) | die Umstellung selbst, bleibt |
| `engine/tests/test_routen.py` | Grunddaten `roh()` Z. 30–32 (U-01..U-03 mit `typ`), Z. 389, Z. 494, `test_unterkunft_art_aus_typ_oder_ausdruecklich` (Z. 487) | Tests verlassen sich auf die Brücke; werden auf `art` umgestellt, der Brückentest wird zum Fehlertest |

## Analyse und Entscheidungen

1. **Fehlerschlüssel:** `pruefung.routen.62` statt 65. Text wird geändert (kein neuer Schlüssel): nennt nur noch `art`
   und, falls `typ` steht, den Hinweis „`neu.py nachziehen` stellt typ auf art um“. Sauberer: zwei Varianten des Textes
   wären ein neuer Schlüssel; stattdessen bekommt 62 den Hinweis immer (ein Satz, kurz). Wortlaut in der Spec d.
2. **Nacht mit nur `typ`:** Fiele `typ` aus der Bedingung in `nacht` weg, bekäme eine solche Nacht still keine Art (kein
   Fehler). Das wäre stilles Verlassen. Deshalb bleibt `typ` in der Bedingung (die Nacht wird geprüft), `art_von`
   liest aber nur `art` und meldet 62. So bricht der Bau laut statt still.
3. **Schreibweg:** Der Konnektor baut vor jedem Schreiben probehalber; eine Reise mit `typ` baut nicht mehr. Die
   Lesepfade `typ` im Schreibweg (`art_schluessel_von`, Z. 1764) sind dann toter Code. Sie entfallen mit (beide
   Definitionen von `art_schluessel_von`; Aufrufer lesen nur `art`). Z. 1775 (`typ` beim Setzen von `art` entfernen)
   bleibt: Es ist Aufräumen der Datei, kein Ersatz-Lesen. Spur B ist angefragt (kein Konflikt, #225 arbeitet an #316).
4. **`arten_ableiten`:** bleibt unverändert. Es ist das Einführungswerkzeug für Bestandsdaten (O-2) und liest
   Eingaben tolerant; der Bau hängt nicht davon ab.
5. **Einzelform:** nur Kommentar an Z. 1044 (und Verweis auf `routen.py` Lesestelle), kein Verhalten.
6. **Umstellung:** keine neue nötig; `nachziehen` stellt `typ` seit #250 um. Ende-zu-Ende-Test: Kopie der Beispielreise
   mit `typ` an einer Unterkunft und einer Nacht → Bau meldet 62 → `nachziehen` → Bau grün.

## Abhängigkeiten

- Upstream: `art_schluessel` (bleibt, viele Nutzer), `texte.satz`.
- Downstream: Konnektor (`ding_aendern`, `attribute_merge`), Bau beider Beispielreisen, Instanz-Tests im Reisen-Repo
  (Meldungstext 62 ändert sich → Instanz-Tests mit dem Branch laufen lassen, AC-13).

## Risiken

- Tests außerhalb von `test_routen.py`, die Unterkünfte mit `typ` bauen (YAML-Strings), fallen erst im RED-Lauf auf.
- Meldungstext 62 ändert sich: Instanz-Tests prüfen.

## Analysis

### Type
Feature (Abbau einer Altform, Teil d von #267; AC-10, AC-11 der Spec `docs/specs/betrieb/altformen-entfernen-267.md`)

### Prüfung der Fundstellen (4.11.2026)
Alle Zeilenangaben oben gegen den Branch `altformen-267-d` bestätigt. Außer `engine/tests/test_routen.py` stützt sich
kein Test auf `typ` als Art (übrige Treffer `typ:` sind Datentypen von Merkmalen: `zeitpunkt`, `adresse` u. a.;
die bleiben unberührt). `art_von`/`art_schluessel_von` werden außerhalb von `routen.py`/`schreiben.py` nicht genutzt.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/routen.py` | MODIFY | `art_von` liest nur `art` (Docstring anpassen); Bedingung in `nacht` behält `typ`, damit eine Nacht mit nur `typ` laut mit 62 bricht |
| `engine/schreiben.py` | MODIFY | beide Definitionen von `art_schluessel_von` entfallen; Aufrufer Z. 1626 und Z. 3954 lesen nur `art`; Z. 1764 `alt` = `knoten.get("art")`; Z. 1774 f. bleibt (Aufräumen), Kommentar anpassen; Z. 1044 nur Kommentar „Einzelform: Lesetoleranz“ |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | `pruefung.routen.62`: nennt nur `art` plus Hinweis „`neu.py nachziehen` stellt typ auf art um“ |
| `engine/tests/test_routen.py` | MODIFY | `roh()` U-01..U-03 und Nächte Z. 389/494 auf `art`; `test_unterkunft_art_aus_typ_oder_ausdruecklich` wird Fehlertest (62) |
| `engine/tests/test_neu.py` (oder `test_routen.py`) | MODIFY | Ende-zu-Ende: Kopie Beispielreise mit `typ` an Unterkunft und Nacht → Bau 62 → `nachziehen` → Bau grün |
| `engine/tests/test_schreiben.py` | MODIFY | Test: Schreibweg auf Reise ohne `typ` unverändert; Merkmalskatalog von `ding_aendern` richtet sich nach `art` |
| `engine/neu.py` | — | unverändert (`typ_zu_art` und `arten_ableiten` bleiben) |

### Scope Assessment
- Files: 5–7
- Estimated LoC: +40/−25 (davon der größte Teil Tests)
- Risk Level: LOW — die Daten aller Reisen (Reisen-Repo und Beispiele) haben 0 × `typ:` an Unterkünften und Nächten; geändert werden Lesepfade, die nichts mehr treffen, und ein Meldungstext

### Technical Approach
Siehe Entscheidungen 1–6 oben. Reihenfolge: (1) Tests in `test_routen.py` auf `art` umstellen und Fehlertests
schreiben (RED), (2) `routen.py` `art_von`, (3) Text 62 in beiden Sprachen, (4) `schreiben.py` Lesepfade, (5) Kommentar
Einzelform, (6) Ende-zu-Ende-Test mit `nachziehen`. Kein neuer Schlüssel, keine neue Umstellung in `nachziehen`.
Die Strategie-Bewertung durch Subagenten entfällt bewusst: Die Untersuchung liegt vollständig in dieser Datei vor und
wurde inline am Code bestätigt; der Umfang ist klein und abgegrenzt.

### Dependencies
- Upstream: `routen.art_schluessel` (bleibt), `texte.satz`.
- Downstream: Konnektor (`ding_aendern`, `attribute_merge`), Bau beider Beispielreisen, Instanz-Tests im Reisen-Repo
  (Meldungstext 62 ändert sich → Instanz-Tests mit dem Branch vor dem Vorspulen, AC-13).

### Open Questions
- keine (die Spec nennt irrtümlich `pruefung.routen.65`; die Spec d nennt 62 — Berichtigung, keine Frage an den PO)
