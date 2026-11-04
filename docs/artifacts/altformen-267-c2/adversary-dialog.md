# Adversary Dialog — altformen-267-c2
Spec: docs/specs/betrieb/altformen-sprache-bestand-267-c2.md
Datum: 2026-11-04 13:24

## Checkliste
- [x] **AC-1 (Bau ohne Feld):** Given eine Reise, deren `reise.yaml` kein Feld `sprache` hat, When sie gebaut wird, Then bricht der Bau mit der Meldung `pruefung.reise.sprache_fehlt`; der Text nennt alle Kürzel aus `texte.SPRACHEN` und `neu.py nachziehen`. (AC-7 der Gesamtspec)
- [x] **AC-2 (leeres Feld):** Given `sprache:` ohne Wert (oder `sprache: ""`), When gebaut wird, Then dieselbe Meldung wie AC-1. Ein unbekanntes Kürzel meldet weiter `pruefung.reise.sprache_unbekannt`.
- [x] **AC-3 (nach `nachziehen`):** Given eine Reise ohne Feld, When `neu.py nachziehen` (mit Schreiben) lief, Then steht `sprache: de` in der Datei, die Reise baut ohne Fehler, die Seite ist deutsch (`lang="de"`), und die Meldungen/Dateien, die `nachziehen` dabei schreibt, sind deutsch wie bisher (auch die Vorgabe „Unterwegs nachschlagen“ in `reise.json`).
- [x] **AC-4 (`BESTAND_REISE` weg):** In keiner Nicht-Testdatei unter `engine/` kommt `BESTAND_REISE` vor. Der Suchtest setzt den Namen zusammen und schließt `engine/tests/` aus, sodass er sich nicht selbst findet. (AC-7)
- [x] **AC-5 (`_einzeln`):** Given Sprache `de`, When `texte._einzeln("de", w)` für jeden Schlüssel `w` aus `texte._RAND` aufgerufen wird, Then liefert es den Katalogtext `wert.<w>` oder `None` (das Wort bleibt), nie den englischen Namen `_RAND[w]`. Für `en` und die Pseudo-Sprache der Tests bleibt der Rückfall auf `_RAND` wie bisher. `texte_de.py` trägt `NAMEN_DER_SCHNITTSTELLE = True`, keine andere Sprachdatei; `_einzeln` liest die Eigenschaft aus der Sprachdatei (kein Sprachkürzel im Code).
- [x] **AC-6 (Prüfstelle `_datenwerte`):** `_datenwerte()` in `test_texte.py` liest die Schlüssel `wert.*` aus `texte.VORGABE`; die Menge ist gleich der aus dem deutschen Katalog (Paritätstest de/en über alle `wert.`-Schlüssel). Damit ändert sich die Menge der erlaubten Datenwerte nicht, und die Ausnahmelisten in `engine/tests/test_texte.py` sind gegenüber `main` nicht länger geworden. (AC-9)
- [x] **AC-7 (`sprache_von`):** Given eine `reise.yaml` ohne Zeile `sprache:`, When `sprache_von` läuft (Test mit Marke `echter_rueckfall`), Then ist das Ergebnis `texte.VORGABE_REISE` (Englisch); mit gültigem Feld das Kürzel; mit unbekanntem Kürzel oder ohne lesbare Datei wie bisher `texte.VORGABE_REISE`.
- [x] **AC-8 (`sprache_pruefen`):** Die Funktion hat keinen Parameter `leer`; `None`/`""` ergibt `(texte.VORGABE_REISE, None)`; ein gültiges Kürzel wird normalisiert; ein unbekanntes liefert `pruefung.reise.sprache_unbekannt`.
- [x] **AC-9 (`einstellung_setzen`):** Given `setting_set` mit `sprache: en` für eine Reise mit Feld `de`, Then meldet die Antwort „de → en“ wie bisher. Given dieselbe Eingabe, aber `reise.yaml` ohne Feld (Datei direkt geschrieben), Then meldet die Antwort als „von“ den Katalogtext `schreiben.antwort.einstellung.sprache_ungesetzt`, trägt `en` ein, und die Änderung gilt als Änderung (keine Ablehnung `einstellung_setzen.4`). Gibt man dasselbe Kürzel wie das gesetzte noch einmal an, bleibt die Ablehnung `einstellung_setzen.4`.
- [x] **AC-10 (Katalog):** `pruefung.reise.sprache_fehlt` und `schreiben.antwort.einstellung.sprache_ungesetzt` stehen in `texte_de.py` und `texte_en.py` (und damit in jeder Sprachdatei, die der Katalogtest `test_texte.py` kennt, einschließlich der Pseudo-Sprache der Tests); die Platzhalter beider Sprachen stimmen überein.
- [x] **AC-11 (Testvorlagen):** Jede Testvorlage, die eine `reise.yaml` schreibt und durch den Bau läuft, trägt `sprache: de` (Beispielwert); `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün.
- [x] **AC-12 (keine Verhaltensänderung sonst):** Bau und Seiten beider Beispielreisen (`beispielreise`, `stadtwochenende`) sind vor und nach dem Paket gleich (Bau mit dem Branch und mit `main`, Vergleich der gebauten Seiten), ebenso die Meldungstexte in de, en und der Pseudo-Sprache der Tests. (AC-9 der Gesamtspec)
- [x] **AC-13 (Abnahme b → c, AC-6 der Gesamtspec) [vor dem Vorspulen, Orchestrator; kein Defekt]:** Vor dem Vorspulen sind im PR-Text belegt: (a) lesende Prüfung am Stand von `main` des Reisen-Repos: in jeder `reisen/*/reise.yaml` steht ein gültiges Feld `sprache` (kein Treffer bei `grep -L '^sprache:'`, die Werte aus `grep -h '^sprache:'` sind Kürzel aus `texte.SPRACHEN`), ebenso in jedem weiteren Reisen-Repo, das die Software einbindet; (b) der Probebau jeder Reise mit dem Branch ist grün; (c) die Tests der einbindenden Instanz laufen mit dem Branch grün (dieses Paket ändert Meldungstexte). Reisenamen, Pfade und Adressen stehen nicht in der Spec, sondern nur im PR-Text.

## Dialog

### Runde 1
**Adversary:** Ich gehe von einem kaputten Paket aus und prüfe je Punkt mit eigenem Beweis (Testausgabe: `docs/artifacts/altformen-267-c2/adversary-test-output.txt`, 331 passed in test_texte/test_neu/test_bauen/test_schreiben/test_pwa; Vollsuite laut Auftrag 1316 passed, nicht wiederholt).

Eigener Probelauf (Skript im Scratchpad, Kopie der Beispielreise, Feld `sprache` verändert, `bauen.bauen` und `neu.nachziehen`):
- Feld fehlt / `sprache: null` / `sprache:` / `sprache: ""` -> Bau bricht mit `pruefung.reise.sprache_fehlt` (Text nennt "de, en" und `neu.py nachziehen`). `nachziehen` trägt jeweils `de` ein, danach baut die Reise (`sprache_von` = de). Code: engine/reise.py:382-390, engine/neu.py:676-678.
- `sprache: xx`, `5`, `[de]` -> `pruefung.reise.sprache_unbekannt` (nicht `sprache_fehlt`). `sprache: DE` -> baut (normalisiert).
- AC-12: beide Beispielreisen mit dem Stand dieses Branches und mit dem Stand von main (5ee7b3c, ausgecheckt im Scratchpad) gebaut, `diff -r`: je nur `index.html` Zeile 907 (Release-Stempel Nummer/Kennung/Commit) und `sw.js` (VERSION, RELEASE, STAND-Hash von index.html, folgt nur aus dem Stempel). Kein Unterschied in Inhalt, `lang="de"`, Medien, Manifest, Icons. Der Abzweigpunkt (04e4a35) liegt hinter der Spitze von main; der Vergleich gegen die Spitze zeigt trotzdem keinen inhaltlichen Unterschied.
- Aufrufer: Suche in betrieb/, werkzeuge/, .github/ findet weder `sprache_pruefen`, `sprache_von` (reise.py) noch `BESTAND_REISE`; `betrieb/zustellen.py:51` nutzt nur `VORGABE_REISE`. In engine/ ist `BESTAND_REISE` nur noch in docs/Spec/Kontext genannt. Alle `sprache_pruefen`-Aufrufer (reise.py:301, 389; neu.py:158, 876) rufen mit einem Argument, keiner mit `leer=`.
- waechter.py:50, kalender.py:111, konnektor.py:187/1959 lesen `reise.sprache` mit `or VORGABE_REISE`; diese Wege laufen nur auf gebauten Daten, in denen die Sprache schon geprüft ist; eine Reise ohne Feld kommt dort nicht an (Bau bricht vorher). Wächter-Meldungen für eine nicht baubare Reise fallen auf Englisch zurück; das ist der in der Spec gewollte Rückfall.
- `_einzeln`: `texte._einzeln("de", w)` für alle `_RAND`-Schlüssel getestet (test_einzeln_de_liefert_deutsche_namen grün); `NAMEN_DER_SCHNITTSTELLE` steht nur in texte_de.py:12, `_einzeln` liest per `getattr(modul, ...)` (texte.py:141-148), kein Kürzel im Code. Für `en`/Pseudo-Sprache bleibt der Rückfall (Test grün).
- Geänderte Assertion test_neu.py (`meldet(..., sprache=texte.VORGABE_REISE)`): sachlich richtig, nicht überdeckend. Der Test trägt die Marke `echter_rueckfall` (conftest.py:40-46 setzt sonst `VORGABE_REISE` auf "de"), und `Reise.fehl` schreibt `texte.satz(...)` im Rückfall; im Probelauf ohne Marke erscheint die Meldung tatsächlich englisch. Die Assertion prüft weiter den Katalogschlüssel `pruefung.reise.sprache_fehlt`, nur in der richtigen Sprache.
- AC-9: Tests test_einstellung_sprache_mit_feld / _ohne_feld_meldet_nicht_gesetzt / _gleiche_sprache_ablehnung grün; Code schreiben.py:2839-2842 (Vergleich ohne Ersatzwert, "von" = Katalogtext).
- AC-6: Der Unterschied von test_texte.py gegen den Abzweigpunkt 04e4a35 zeigt nur Ergänzungen, an den Ausnahmelisten keine Zeile; `_datenwerte()` liest `texte.VORGABE` (de/en-Parität per Test).
- Docs: betrieb.md:116, sprachen.md:91, mehrsprachigkeit.md:37 ohne Bestandsfall; kein weiterer Treffer für "ohne Feld/fehlt das Feld".
- Pflichtdateien kalender.py, konnektor.py, konten.py, texte.py (nur Kommentar-/Docstring-Änderungen, geprüft), neu.py, reise.py, schreiben.py, texte_de.py, texte_en.py (Verhalten, geprüft); Code-Referenzen unten.

Gegenfragen an den Implementierer: (1) Gibt es einen Weg, auf dem `Reise.sprache` den Rückgabewert "en" bei Fehler nutzt und trotzdem etwas geschrieben wird? (2) Was passiert, wenn der Schreibweg in eine unmigrierte Reise schreibt?
**Implementierer:** (1) Nein: bei `fehl` bricht der Bau am Ende der Sammlung (BauFehler), es wird nichts ausgeliefert; `VORGABE_REISE` dient nur dem Weitersammeln weiterer Fehler. (2) `schreiben.sprache_von` liefert dann `VORGABE_REISE` (Englisch) statt wie früher Deutsch; das ist in der Spec ausdrücklich so vorgesehen und wird durch AC-13 (Nachweis, dass jede Reise das Feld trägt) abgesichert.

### Runde 2
**Adversary:** Nachbohren an den Rändern.
- `sprache_von` (reise.py:220-230): Die Regex ist unverändert; `\s*` überspringt Zeilenumbrüche, sodass ein leeres `sprache:` gefolgt von `titel: x` das Wort "titel" fängt; das ist kein Kürzel, also `VORGABE_REISE`. Im Probelauf lieferten `sprache:`, `null`, `""` jeweils "en" -> kein falsches Kürzel. Schon vor dem Paket vorhanden, keine Verschlechterung, für den Bau irrelevant (der Bau bricht über `Reise.sprache`).
- Konsistenz nachziehen/Bau: `neu.py:676-678` behandelt `None` und Leerstring gleich wie `reise.py:386`; Probelauf bestätigt für alle vier Leerformen: nachziehen -> Bau grün.
- Unterwegs-Vorgabe (neu.py:651): `texte.t("de", ...)`, unabhängig von VORGABE_REISE, Sicherungstest test_nachziehen_unterwegs_vorgabe_ist_deutsch grün (unter echter_rueckfall).
- `setting_set`: `roh.get("sprache") or S(...)` zeigt bei explizitem `null` ebenfalls "nicht gesetzt"; beim Wert `DE` (Großschreibung in der Datei) zählt `sprache: de` weiter als Änderung (wie vor dem Paket). Kein Unterschied zu vorher.
- Katalog (AC-10): Platzhalter `{bekannt}` in de/en gleich; `sprache_ungesetzt` ohne Platzhalter; Katalogtests in test_texte.py (Parität, Pseudo-Sprache) grün.
- Anmerkung (LOW, F001): Die Meldung `sprache_fehlt` erscheint im Produktivbetrieb englisch (Rückfall), auch für deutsche Betreiber; gleichartig wie `sprache_unbekannt`, gewollt.
- Schreibweg und `waechter.py` für Reisen ohne Feld fallen auf Englisch zurück statt auf Deutsch (Verhaltensänderung nur für Reisen ohne Feld, laut Spec akzeptiert; Absicherung ist AC-13, Orchestrator).
**Implementierer:** Keine Einwände; die LOW-Anmerkung ist Absicht (Prüfsätze stehen im Rückfall der Software, ADR-0006). AC-13 erledigt der Orchestrator vor dem Vorspulen.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/reise.py:386
  Evidence: `Reise.sprache` meldet bei fehlendem Feld `pruefung.reise.sprache_fehlt` mit allen Kürzeln aus `texte.SPRACHEN`; Probelauf: Bau bricht mit dieser Meldung, Text nennt "de, en" und `neu.py nachziehen`.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/reise.py:386
  Evidence: `wert is None or wert == ""` deckt `sprache:`, `null`, `""`; Probelauf je dieselbe Meldung; `xx`, `5`, `[de]` melden weiter `sprache_unbekannt` (reise.py:233-240).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/neu.py:651
  Evidence: `nachziehen` trägt `sprache: de` ein (neu.py:676-678, SPRACHE_NACHZIEHEN neu.py:660), Reise baut danach, `lang="de"`; die Vorgabe "Unterwegs nachschlagen" kommt aus `texte.t("de", ...)`; test_reise_ohne_feld_sprache_baut_erst_nach_nachziehen und test_nachziehen_unterwegs_vorgabe_ist_deutsch grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/texte.py:18
  Evidence: Die Zeile mit `BESTAND_REISE` ist gelöscht; Suche über engine/ ohne tests findet den Namen nicht; test_bestand_reise_kommt_nicht_mehr_vor grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/texte.py:141
  Evidence: `_einzeln` prüft `getattr(modul, "NAMEN_DER_SCHNITTSTELLE", False)`; texte_de.py:12 trägt das Feld als einzige Sprachdatei; drei Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_de.py:12
  Evidence: Keine `wert.`-Einträge hinzugefügt (de/en-Parität per Test), `_datenwerte()` liest `texte.VORGABE`; Ausnahmelisten in test_texte.py unverändert (nur Ergänzungen).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/reise.py:229
  Evidence: `sprache_von` gibt ohne Zeile `sprache:` `texte.VORGABE_REISE`; Probelauf "von: en" für alle Leerformen; Test mit Marke echter_rueckfall grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/reise.py:233
  Evidence: Signatur `sprache_pruefen(wert)` ohne `leer`; `None`/`""` -> `(VORGABE_REISE, None)`; alle Aufrufer ohne zweites Argument (Suche).
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/schreiben.py:2839
  Evidence: Vergleich `roh.get("sprache") != sprache`, "von" = `sprache_ungesetzt`; drei Tests grün, Ablehnung `einstellung_setzen.4` bei gleichem Kürzel bleibt.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/texte_en.py:2739
  Evidence: Beide Schlüssel in texte_de.py:877/2740 und texte_en.py:876/2739; Platzhalter gleich; Katalogtests inkl. Pseudo-Sprache grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/konten.py:73
  Evidence: konten.py nur Kommentar-Änderung; Testvorlagen tragen `sprache: de`; meine Läufe 331 passed, Vollsuite laut Auftrag 1316 passed (test-green-output.txt).
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/kalender.py:275
  Evidence: kalender.py nur Kommentar. Bauvergleich beider Beispielreisen, Branch gegen main: nur Release-Stempel und davon abgeleitete sw.js-Hashes unterscheiden sich (index.html Z. 907, sw.js Z. 20-23), alle anderen Dateien gleich. Meldungstexte: je Sprache nur ein Schlüssel ergänzt, kein Wortlaut geändert, Katalogtests grün.
  Status: CONFIRMED

Confirmation:
  AC: Kommentare konnektor.py
  Code reference: engine/konnektor.py:188
  Evidence: Nur Kommentare/Docstrings geändert (konnektor.py:188, 200, 210, 1326, 2041), Code unverändert.
  Status: CONFIRMED

AC-13: vor dem Vorspulen, Orchestrator (lesende Prüfung der privaten Reisen-Repos, Probebau, Instanz-Tests); kein Defekt dieses Pakets, hier nicht prüfbar.

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/reise.py:387
  Description: Der Bau meldet `sprache_fehlt` im Rückfall (Englisch), auch für deutsche Betreiber (wie `sprache_unbekannt`).
  Spec requirement: AC-1 — Meldung `pruefung.reise.sprache_fehlt`, Text nennt Kürzel und `neu.py nachziehen`
  Conflict: Kein Widerspruch; nur Lesbarkeit. Entspricht ADR-0006 (Prüfsätze im Rückfall).
  Remediation: Keine nötig.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Implementierung hat den Angriffen standgehalten.
Tests: 331 passed, 0 failed, 0 übersprungen (gezielte Dateien, adversary-test-output.txt); Vollsuite laut Auftrag 1316 passed
Edge cases: sprache fehlt/null/leer/""/unbekannt/Zahl/Liste/Großschreibung, nachziehen -> Bau, setting_set mit und ohne Feld: keine Brüche
Regressions: None found (AC-12: nur Release-Stempel und abgeleitete sw.js-Hashes unterscheiden sich)
Checklist: 12/12 Punkte belegt; AC-13 vor dem Vorspulen beim Orchestrator (kein Defekt)
Finding F001: LOW, nur Anmerkung, kein Blocker

## Geprüfte Dateien

- sha256:9cfd276e6f81ba3cb6b3aa818db044e3bb6993bd421c5094038f9c59992cda70  engine/kalender.py
- sha256:a46b47be9c88edfc6253a93cd971cd23df1b1e056396b985498d3009851c05e0  engine/konnektor.py
- sha256:cf8e5e3c686a1232d05173336a75df432040f4dbe814a1d900d55cfe4bf5fe5c  engine/konten.py
- sha256:a45a7cde6af99e003088ad31c2ce8ac8a6ad3e76160f7b5ee6c74070ddb189c8  engine/neu.py
- sha256:62ebc5f982c799a9b3fae9c4ab729eff95e03fbcd129826629c25c32c589fb3d  engine/reise.py
- sha256:3331e15c21013109d45db103217ffc34bfda69985dd17623710eb00db1dcf314  engine/schreiben.py
- sha256:7433237f1fa050b778262993d36bc8100522e144144f7b1099a5647ffd1d87b1  engine/texte.py
- sha256:d6b2791c1816c00a3f3577968edcb52f38970b7473fb041a988c2c16ec620421  engine/texte_de.py
- sha256:66260b10604c7d31d9d0ddf59e7b863bfdca832968bc6b0128b905e496fe9256  engine/texte_en.py

## Prüfbasis

- base: 04e4a358485630e7beb5c08e6e9f5a61449647f8
- blob:7833a1bd536a117a47bbb4919d5fe63ec81aad72  engine/kalender.py
- blob:fd612260f1b1388744613b42034795c36f23f25d  engine/konnektor.py
- blob:46243a5dada9c345f00ca0a58d375f754ca1caa2  engine/konten.py
- blob:442940a2b6059a842a79cba786db53c8d26e2b85  engine/neu.py
- blob:ae972976ea86b03a34977a2e10ee2a387afa7001  engine/reise.py
- blob:227281c1680b5017ca26c6b32c1aac7de8237195  engine/schreiben.py
- blob:a3f7a6b7460c8dcaed810c89847359af5f215132  engine/texte.py
- blob:aa9ae42ffd7edf32a3ad563d6c482e6a9768127b  engine/texte_de.py
- blob:6ff9efbaff20356a13ca4e79e5ef66d2431c6ff5  engine/texte_en.py

## Geprüfte Dateien

- sha256:9cfd276e6f81ba3cb6b3aa818db044e3bb6993bd421c5094038f9c59992cda70  engine/kalender.py
- sha256:a46b47be9c88edfc6253a93cd971cd23df1b1e056396b985498d3009851c05e0  engine/konnektor.py
- sha256:cf8e5e3c686a1232d05173336a75df432040f4dbe814a1d900d55cfe4bf5fe5c  engine/konten.py
- sha256:a45a7cde6af99e003088ad31c2ce8ac8a6ad3e76160f7b5ee6c74070ddb189c8  engine/neu.py
- sha256:62ebc5f982c799a9b3fae9c4ab729eff95e03fbcd129826629c25c32c589fb3d  engine/reise.py
- sha256:3331e15c21013109d45db103217ffc34bfda69985dd17623710eb00db1dcf314  engine/schreiben.py
- sha256:7433237f1fa050b778262993d36bc8100522e144144f7b1099a5647ffd1d87b1  engine/texte.py
- sha256:d6b2791c1816c00a3f3577968edcb52f38970b7473fb041a988c2c16ec620421  engine/texte_de.py
- sha256:66260b10604c7d31d9d0ddf59e7b863bfdca832968bc6b0128b905e496fe9256  engine/texte_en.py

## Prüfbasis

- base: 04e4a358485630e7beb5c08e6e9f5a61449647f8
- blob:7833a1bd536a117a47bbb4919d5fe63ec81aad72  engine/kalender.py
- blob:fd612260f1b1388744613b42034795c36f23f25d  engine/konnektor.py
- blob:46243a5dada9c345f00ca0a58d375f754ca1caa2  engine/konten.py
- blob:442940a2b6059a842a79cba786db53c8d26e2b85  engine/neu.py
- blob:ae972976ea86b03a34977a2e10ee2a387afa7001  engine/reise.py
- blob:227281c1680b5017ca26c6b32c1aac7de8237195  engine/schreiben.py
- blob:a3f7a6b7460c8dcaed810c89847359af5f215132  engine/texte.py
- blob:aa9ae42ffd7edf32a3ad563d6c482e6a9768127b  engine/texte_de.py
- blob:6ff9efbaff20356a13ca4e79e5ef66d2431c6ff5  engine/texte_en.py
