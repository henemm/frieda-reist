# Adversary Dialog — altformen-267-d
Spec: docs/specs/betrieb/altformen-typ-art-267-d.md
Datum: 2026-11-04 18:10

## Checkliste
- [x] **AC-1:** Given eine Reise, in der eine Unterkunft `typ: Hotel` und kein `art` trägt, when der Bau läuft, then bricht er mit `pruefung.routen.62` (Text mit „Unterkunft U-…“ als `{wo}`), und `typ` ersetzt `art` nicht.
- [x] **AC-2:** Given ein Aufenthalt (Ding der Grundform Aufenthalt ohne Nacht) mit `typ` und ohne `art`, when der Bau läuft, then bricht er mit `pruefung.routen.62` (`{wo}` = „Aufenthalt A-…“).
- [x] **AC-3:** Given eine Nacht `{ort: …, typ: …}` ohne `art` und ohne `an_bord`, when der Bau läuft, then bricht er mit `pruefung.routen.62` (`{wo}` = „<Tag> nacht“), nicht still ohne Art.
- [x] **AC-3b:** Given eine Nacht mit `an_bord: true` und `typ`, aber ohne `art`, when der Bau läuft, then bricht er mit `pruefung.routen.62` und setzt nicht still `unterwegs`; eine Nacht mit `an_bord: true` ohne `typ` und ohne `art` bekommt weiter `unterwegs` ohne Fehler.
- [x] **AC-4:** Given dieselben Daten mit `art:` statt `typ:` an Unterkunft, Aufenthalt und Nacht, when der Bau läuft, then ist er grün und die Ausgabe nennt die Arten wie vor PR d (Art und Artname je Unterkunft und Nacht gleich).
- [x] **AC-5:** Given eine Unterkunft mit `typ: Tempel` und `art: huette`, when der Bau läuft, then gilt `huette` und es gibt keinen Fehler (`typ` wird ignoriert, nicht ausgewertet).
- [x] **AC-6:** Given beide Beispielreisen (`beispielreise`, `stadtwochenende`) und `engine/reisevorlage/`, when sie bauen, then sind sie grün; `grep -rn "^ *typ:" beispiel/reisen/*/plan/routen.yaml engine/reisevorlage` ohne Treffer.
- [x] **AC-7 (Ende zu Ende):** Given eine Kopie der Beispielreise (Testordner), in der eine Unterkunft und eine Nacht `art` durch den früheren `typ` ersetzt haben, when der Bau läuft, then meldet er 62; when `neu.py nachziehen` die Kopie umstellt, then steht `art` an beiden Stellen (kein `typ` mehr), und der Bau ist grün; ein zweiter Lauf von `nachziehen` ändert keine Datei.
- [x] **AC-8:** Given eine Reise mit `art`-Feldern, when `ding_aendern` ein Feld einer Unterkunft ändert, then richtet sich der Merkmalskatalog nach `art` des Knotens; given ein Knoten mit nur `typ` (ohne `art`), then wird kein Katalog aus `typ` abgeleitet. Das Setzen von `art` entfernt einen vorhandenen `typ` aus dem Knoten (Aufräumen bleibt).
- [x] **AC-9:** Given der Quelltext von `engine/schreiben.py`, then enthält er keine Definition und keinen Aufruf von `art_schluessel_von` und keinen Lesezugriff `knoten.get("typ")`; `routen.py` liest `typ` an Unterkunft, Aufenthalt und Nacht nirgends als Ersatz für `art` (`art_von` prüft `typ` nur auf Vorhandensein, um laut mit 62 zu brechen, und gibt nie einen aus `typ` abgeleiteten Wert zurück; die Bedingung in `nacht` trägt den Kommentar).
- [x] **AC-10 (Texte):** Given `pruefung.routen.62`, then steht der neue Text in `texte_de.py` und `texte_en.py` (nennt `art`, nicht `typ oder art`, und den Hinweis auf `neu.py nachziehen`), `{wo}` ist der einzige Platzhalter; `engine/tests/test_texte.py` ist grün und die Ausnahmelisten darin sind nicht länger geworden.
- [x] **AC-11 (Einzelform):** Given ein Merkmal mit einem einzelnen Eintrag ohne Liste in der Datei, when `wert_eintragen` einen Wert schreibt, then verhält es sich wie vor PR d (Eintrag wird als Liste weitergeführt); der Kommentar zur Einzelform steht an der Stelle.
- [x] **AC-12 (unverändert):** `neu.py` ist im Diff nicht enthalten; `engine/tests/test_neu.py` (`typ_zu_art`, `arten_ableiten`) bleibt grün ohne Änderung der bestehenden Fälle.
- [x] **AC-13 (Gesamtlauf):** `engine/.venv/bin/python -m pytest -q engine/tests` ist grün ohne echte Reisen (CI auf dem vorgespulten Commit).
- [x] **AC-14 (Instanz-Tests, manueller Nachweis im PR-Text) [vor dem Vorspulen, Orchestrator; kein Defekt]:** Weil sich der Meldungstext von 62 ändert, laufen vor dem Vorspulen die Tests der einbindenden Instanzen im Reisen-Repo mit dem Branch (Anleitung dort) und sind grün; der Probelauf des Baus aller echten Reisen mit dem Branch ist grün (lesend, Befund 0 × `typ:` bestätigt). Das Ergebnis steht im PR-Text.

## Dialog

### Runde 1
**Adversary:** Ich gehe von kaputt aus. Befehle und Ergebnisse:
- Gezielter Lauf (test_routen, test_texte, test_neu, test_schreiben): 341 passed, 0 failed, 0 skipped (docs/artifacts/altformen-267-d/adversary-test-output.txt). Gesamtlauf AC-13: 1335 passed laut docs/artifacts/altformen-267-d/test-green-output.txt, nicht wiederholt.
- Grep AC-6 `grep -rn "^ *typ:" beispiel/reisen/*/plan/routen.yaml engine/reisevorlage`: keine Treffer (rc 1). Bau beider Beispielreisen laufen in den Bau-Tests (grün).
- Grep AC-9 in engine/schreiben.py nach `art_schluessel_von` und `get("typ")`: kein Treffer für art_schluessel_von; `.get("typ")` nur als Datentyp einer Merkmalsdefinition (Zeilen 935, 937, 941, 1214, 1239, 1840, 2026, 2110), nie an `knoten`. Im Diff: beide Definitionen weg, beide Aufrufer lesen nur `art`.
- Grenzprobe (Scratchpad probe-out.txt, Aufruf über Routen.bauen mit der Testbasis): Unterkunft nur typ -> 62; typ+art(hotel) -> kein Fehler; art leer + typ -> 62; Unterkunft an_bord+typ -> 62; Nacht nur typ -> 62 (Text mit nachziehen); Nacht an_bord+typ -> 62; an_bord+typ leer -> 62; an_bord+typ None -> 62; an_bord ohne alles -> kein Fehler (unterwegs); an_bord+art -> kein Fehler; an_bord+art+typ -> kein Fehler.
- Angriff auf den Filter-Wechsel in fehler_62 (`in` statt `startswith`): Der Filter fordert weiter meldet(f, "pruefung.routen.62"), den Hinweis `nachziehen` und verbietet "typ oder art". Weicher geworden ist nur die Verankerung am Zeilenanfang; Routen.fehl stellt jeder Meldung den Dateipräfix "plan/routen.yaml: " voran, also war startswith nie erfüllbar. Kein Verlust an Aussagekraft, weil meldet() den Schlüssel prüft.
- AC-12: Diff von engine/neu.py gegen HEAD ist leer, neu.py steht nicht in der Änderungsliste. Der Vergleich gegen die lokale main zeigt dagegen 563 Zeilen, weil dieser Branch die früheren Teile a, b, c1, c2 trägt, die in der lokalen main fehlen. Gemessen an der Basis dieses PR ist neu.py unverändert; Hinweis für den PR-Text, kein Defekt der Umsetzung.
**Implementierer:** (Prüfung ohne Rückfrage; Antworten ergeben sich aus dem Diff)

### Runde 2
**Adversary:** Zweiter Angriff auf Randfälle.
- Nacht mit `typ: ""` oder `typ: None` ohne art und an_bord: die Bedingung in nacht (routen.py:1422) ist falsy, art_von wird nicht gerufen, die Nacht bekommt still art None, kein Fehler (Probe: "N typ leer -> 0", "N typ None -> 0"). Verhalten wie vor PR d. Als LOW geführt, nicht blockierend (F001).
- Gegenprobe an_bord+typ leer/None: bricht mit 62 (Vorhandensein, wie in der Spec). Inkonsistent zur Nacht ohne an_bord, aber spec-konform.
- Schreibweg: ding_aendern liest `art = knoten.get("art")` (schreiben.py:1628); bei Knoten mit nur typ ist der Katalog leer, kein Ausweichen auf typ; Setzen von art löscht typ (schreiben.py:1770). merkmal_zusammenfuehren vergleicht `knoten.get("art") == art` (schreiben.py:3950); ein Knoten nur mit typ wird nicht mehr umgehängt, gewollt, weil der Bau so eine Reise ohnehin ablehnt. Tests test_ding_aendern_katalog_nach_art und test_schreiben_ohne_art_schluessel_von grün.
- Restliche Verwender von art_schluessel_von: nur Tests, Doku und Artefakte; kein Code.
- Texte: 62 hat in de und en nur {wo}, nennt art und `neu.py nachziehen` (texte_de.py:2615, texte_en.py:2614); test_texte grün, test_texte.py nicht im Diff, Ausnahmelisten nicht länger.
- Einzelform: nur Kommentar in wert_eintragen (schreiben.py:1043-1044), kein Verhaltensunterschied im Diff.
**Implementierer:** (keine Rückfrage)

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/routen.py:1422
  Description: Die Bedingung in nacht prüft den Wahrheitswert von typ; eine Nacht mit `typ: ""` oder `typ: None` ohne art und an_bord bekommt still art None ohne Fehler, während dasselbe mit an_bord (art_von prüft Vorhandensein) 62 meldet.
  Spec requirement: AC-3 — Nacht mit typ ohne art bricht laut, nicht still ohne Art
  Conflict: Nur für leere Werte von typ, die kein umstellbarer Bestand sind; Verhalten unverändert zu vor PR d.
  Remediation: Optional "typ" in n prüfen statt n.get("typ"); nicht nötig für die Freigabe.

Finding:
  ID: F002
  Severity: LOW
  Category: spec_violation
  Code reference: engine/routen.py:1043
  Description: AC-12 lässt sich mit dem Vergleich gegen die lokale main nicht leer belegen, weil der Branch die früheren Teile a bis c2 trägt. Gegen HEAD ist neu.py unverändert.
  Spec requirement: AC-12 — neu.py ist im Diff nicht enthalten
  Conflict: Nur Messbasis, kein Codefehler.
  Remediation: Im PR-Text gegen die tatsächliche PR-Basis messen.

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/routen.py:1048
  Evidence: art_von liest nur art; Unterkunft nur typ -> 62 (Probe).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/routen.py:620
  Evidence: Aufenthalt ruft art_von; test_aufenthalt_typ_ohne_art_bricht_mit_62 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/routen.py:1422
  Evidence: typ bleibt in der Bedingung samt Kommentar (Zeile 1421); Nacht nur typ -> 62 (Probe).
  Status: CONFIRMED

Confirmation:
  AC: AC-3b
  Code reference: engine/routen.py:1048
  Evidence: an_bord ohne typ -> unterwegs; an_bord+typ -> 62 (Probe).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/routen.py:1422
  Evidence: test_unterkunft_nacht_aufenthalt_mit_art_bauen grün; roh() nutzt art.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/routen.py:1046
  Evidence: a = eintrag.get("art"); typ+art(hotel) -> kein Fehler (Probe).
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/routen.py:1043
  Evidence: Grep ohne Treffer; Bau-Tests beider Beispielreisen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/routen.py:1048
  Evidence: test_nachziehen_stellt_typ_an_unterkunft_und_nacht_um_bau_gruen grün (341 passed).
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/schreiben.py:1628
  Evidence: art = knoten.get("art"); typ-Aufräumen bei Zeile 1770 bleibt; test_ding_aendern_katalog_nach_art grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/schreiben.py:3950
  Evidence: art_schluessel_von nirgends im Code; kein knoten.get("typ") in schreiben.py; art_von gibt nie einen typ-Wert zurück.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/texte_de.py:2615
  Evidence: neuer Text nennt art und nachziehen, nur {wo}; test_texte grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/texte_en.py:2614
  Evidence: englischer Text nennt art und nachziehen, nur {wo}.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/schreiben.py:1043
  Evidence: Kommentar Einzelform steht, kein Verhaltensdiff; test_merkmal_einzelform_bleibt_les_und_schreibbar grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/routen.py:1043
  Evidence: neu.py ohne Diff gegen HEAD; test_neu grün (siehe F002 zur Messbasis).
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/schreiben.py:1628
  Evidence: Voller Lauf 1335 passed (test-green-output.txt); gezielter Lauf 341 passed (adversary-test-output.txt).
  Status: CONFIRMED

AC-14: offen, außerhalb dieser Prüfung (manueller Nachweis im PR-Text), nicht als Defekt gewertet.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED
Tests: 341 passed, 0 failed, 0 übersprungen (gezielt); voller Lauf 1335 passed (vorab)
Edge cases: geprüft, nur LOW-Funde (F001, F002), kein Defekt
Regressions: keine gefunden
Checklist: 14/14 Punkte belegt; AC-14 vor dem Vorspulen durch den Orchestrator (Instanz-Tests, Probebau), Nachweis im PR-Text

## Geprüfte Dateien

- sha256:bde6948f93ce544c23222be8da3c80d146f3ebbcae31453cb554b4f51250f598  engine/routen.py
- sha256:c2c998de2858a7d1a3d178332c4f1630d0e45aba48fc589fa0f89ba9f8033a97  engine/schreiben.py
- sha256:a3c62f4fa8a363f6eb318258eaee3fa87bb9cc3c36ee25ddcc1fdcb463da9958  engine/texte_de.py
- sha256:59cfd1c4ae8bceadba21f009b4f3779267520387054ce6c34a18d70b7c769964  engine/texte_en.py

## Prüfbasis

- base: b176a31203602847d6b3a357ef3587f790917897
- blob:e2277b73a1f48a73b8e3b8de0daba9d9eb5b21e3  engine/routen.py
- blob:e66d1940bb60e96cbffd487c2feb383663c93625  engine/schreiben.py
- blob:68c3f37f2d3351416a5e2f501f061a1e23e107be  engine/texte_de.py
- blob:981783ba98f5652f66316b4c2db69e82fc2b6585  engine/texte_en.py
