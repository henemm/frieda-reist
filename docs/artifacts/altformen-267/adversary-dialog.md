# Adversary Dialog — altformen-267 (PR a)
Spec: docs/specs/betrieb/altformen-entfernen-267.md
Datum: 2026-11-03 10:10

## Checkliste

- AC-1 (a): fehlender reise.yaml -> BauFehler mit Katalogtext (de/en); `.alt` aus reise.py weg: PROVEN
- AC-2 (a): beide Beispielreisen bauen unverändert (Seiten gleich): PROVEN
- AC-12/13 (soweit PR a): Tests ohne echte Reisen grün (1066 passed, docs/artifacts/altformen-267/test-green-output.txt; gezielt 168 passed); neue Texte in allen Sprachen, Parität: PROVEN
- Entfernungen ohne Leser (Suche statt Vermutung): PROVEN, Reste nur in Doku für PR c (siehe F002)

## Dialog

### Runde 1
**Adversary:** Prüfung der Umsetzung gegen AC-1 und AC-2.
- Quelltext: `grep -E "\.alt\b|self\.alt|pruefung\.reise\.2\b"` in engine/ (ohne .venv/vendor) trifft nichts in reise.py/bauen.py/Texten; Treffer nur in vorlage.html (JS `imPlan.alt`, andere Sache), schreiben.py:1780 (Kommentar "alte Form: art = wann", fremd, nicht Reise.alt) und in den Tests, die das Fehlen prüfen.
- Bau-Vergleich: beide Beispielreisen mit dem Stand HEAD (Kopie der Engine mit den vier alten Dateien aus `git show HEAD:`) und mit dem Arbeitsstand gebaut. Ergebnis: 28 Dateien je Lauf, gleicher Dateisatz; index.html und sw.js unterscheiden sich nur im Attribut `data-release` (Release-Info aus dem Git-Stand des Worktrees, in der Scratchpad-Kopie leer); nach Entfernen dieses Attributs sind beide index.html byte-gleich. sw.js-Abweichung ist der daraus folgende Inhalts-Hash. AC-2 PROVEN.
- Fehlende Datei: Bauer(...) wirft BauFehler, Meldung `<pfad>/reise.yaml is missing: no trip builds without reise.yaml ...` (en, weil die Sprache der Reise vor dem Lesen unbekannt ist; identisch zu `pruefung.bauen.datei_fehlt`). de-Text vorhanden (texte_de.py:2833), en (texte_en.py:2833). Test test_altformen_267 prüft den Katalogtext je Beispielreise. AC-1 PROVEN.
- Tests gezielt: test_altformen_267, test_bauen, test_texte, test_pwa: 168 passed.
**Implementierer:** (nicht anwesend, Kontextisolation; Diff und Tests sprechen für sich.)

### Runde 2
**Adversary:** Nachbohren an Rändern.
- Leere reise.yaml: `or {}` -> Reise bekommt `{}` -> Fehler titel/pfad/status/Organisator (5 Meldungen), kein Absturz. Nur Kommentare: gleich. Kaputtes YAML: BauFehler `yaml_reise`. OK.
- reise.yaml als Liste (`[1,2]`): AttributeError 'list' object has no attribute 'get' (reise.py Reise.__init__, `self.r = roh or {}`). Ist im Stand HEAD identisch (gleiche Zeile unverändert), also keine Regression, aber eine ungeprüfte Eingabe: F001 LOW.
- Vereinfachte Zweige in bauen.py: `"entscheider" in roh` (Fehler 21) und `entscheider=organisator` werden jetzt immer ausgeführt statt nur mit reise_roh not None. Da reise_roh nach dem Konstruktor nie None ist (Bauer wirft vorher), ist das für jede Reise mit reise.yaml verhaltensgleich. `reise_roh` bleibt als Attribut; der Test `b.reise_roh is not None` bleibt sinnvoll. OK.
- `cfg`-Parameter: wird weiter für die "noch in reise.json"-Fehler gebraucht (Felder ALTE_ECKDATEN, DARSTELLUNG, funktionen). Sinnvoll, Docstring angepasst. OK.
- Entfernte Konstanten: NOCH_NICHT_GEBAUT wird weiter benutzt (reise.py:503); keine toten Importe durch die Streichung gefunden. Andere Aufrufer von Reise(...) (test_waechter, test_rollen_alt) übergeben Wörterbücher, nie None. OK.
- Andere Stellen mit Rückfall bei fehlender reise.yaml: neu.py:579 (arten_ableiten, kein Bauweg) bleibt zu Recht; sonst keine.
- Tests: test_pwa.py (nicht im Auftrag) nur um eine reise.yaml erweitert (mini_reise braucht sie jetzt, sonst Baufehler), Titel/Pfad von reise.json nach reise.yaml verlegt; Assertions unverändert, nicht abgeschwächt. test_bauen: CFG/GRUND_YAML ebenso; `test_alte_form_ohne_reise_yaml` jetzt als Abbruchtest; entfallene Aussagen (Kontingent-Vorgaben, Funktionen in der alten Form) betrafen nur die alte Form, Abdeckung der Regeln bleibt in test_reise_yaml etc.
- Reste in Doku: docs/sprachen.md:91 und docs/betrieb.md:116 nennen den Bestandsfall für fehlendes `sprache` (PR c, nicht PR a). Keine Doku nennt noch "reise.yaml fehlt -> alte Form": F002 LOW nur Hinweis.
**Implementierer:** (nicht anwesend.)

Findings:

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/reise.py:354
  Description: Reise.__init__ nimmt `roh or {}`; eine reise.yaml, die eine Liste oder einen Skalar enthält, führt zu AttributeError statt BauFehler. Unverändert gegenüber HEAD.
  Spec requirement: AC-1 — nur fehlende Datei; kein Verstoß
  Conflict: keiner; vorbestehende Lücke, jetzt etwas sichtbarer, weil kein Rückfall mehr existiert
  Remediation: in bauen.py nach dem Laden `isinstance(dict)` prüfen, Katalogtext; kann Folge-PR sein

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/bauen.py:292
  Description: Die Meldung bei fehlender reise.yaml kommt in der Rückfallsprache (en), weil die Sprache der Reise vor dem Lesen der Datei unbekannt ist; ebenso `datei_fehlt`.
  Spec requirement: AC-1 — Text über den Katalog, de und en vorhanden
  Conflict: keiner; Spec fordert nur Katalog
  Remediation: keine nötig

Confirmation:
  AC: AC-1
  Code reference: engine/bauen.py:292
  Evidence: raise BauFehler([texte.satz("pruefung.bauen.reise_yaml_fehlt", pfad=pfad)]) vor dem Lesen; keine .alt in reise.py (engine/reise.py:16 Kopf neu).
  Status: CONFIRMED

Confirmation:
  AC: AC-1
  Code reference: engine/texte_de.py:2833
  Evidence: Schlüssel vorhanden, pruefung.reise.2 entfernt; Platzhalter {pfad} und docs/produkt.md, test_texte Parität grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-1
  Code reference: engine/texte_en.py:2833
  Evidence: englischer Text mit gleichem Platzhalter; ausgegeben und geprüft.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/reise.py:365
  Evidence: eckdaten/status/personen/bausteine/darstellung/daten lesen nur noch self.r; Beispielreisen bauen byte-gleich (bis auf data-release) zum HEAD-Stand.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Begründung: AC-1, AC-2 und die für PR a anwendbaren Teile von AC-12/13 bewiesen; Tests 168 gezielt und 1066 gesamt grün, 0 übersprungen; zwei Runden; nur zwei LOW-Hinweise ohne Spec-Verstoß (F001 vorbestehend).

## Geprüfte Dateien

- sha256:e3adb4ec521b3b0012199404c72328b1d6ed13e1453968aca8bc9ca692a2744a  engine/bauen.py
- sha256:184eee7ced53039c9ee48e96791e78e7782a10bb4de1aefc0f3763ee35c28b2f  engine/reise.py
- sha256:546a872407a90296e1bfa50dacef2b4d2b8f8792a20736eeb5b1df7ec20ba9eb  engine/texte_de.py
- sha256:d4c771efbc8b2e471a264cd7a8d36f656ff3686b26e6b8cd2c44860d3185aece  engine/texte_en.py

## Prüfbasis

- base: c62b19cf253464297c2ae79ad1d26ae5a36884f3
- blob:807fac7178f23e0f4d0c8573078716d5c8a7d507  engine/bauen.py
- blob:37381eddb155fdc8c609e06e229810214b2df42d  engine/reise.py
- blob:23366ba582de45705ab878c4f72f6196f98b8654  engine/texte_de.py
- blob:8f4d8e2e13e64fced6fd593e153c31635d776c7e  engine/texte_en.py
