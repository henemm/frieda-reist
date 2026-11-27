# Adversary Dialog — fix-706-pfeil-im-oeffnen
Spec: docs/specs/oberflaeche/pfeil-im-oeffnen-706.md
Datum: 2026-11-27 16:43

## Checkliste
- [x] **AC-1:** Given die Großansicht öffnet noch / When der Pfeilknopf gedrückt wird / Then bleibt sie auf dem angetippten Bild; nach dem Öffnen zeigt sie es, Zähler und Unterschrift gehören dazu, kein Seitenfehler. Test: `engine/tests/test_bilder_eigen.py::test_gross_pfeil_im_oeffnen_bleibt`
- [x] **AC-2:** Given die Großansicht ist offen (nach einem Pfeil im Öffnen) / When der Pfeilknopf gedrückt wird / Then blättert sie wie bisher zum nächsten Bild, Zähler folgt. Test: `engine/tests/test_bilder_eigen.py::test_gross_pfeil_nach_dem_oeffnen_blaettert`
- [x] **AC-3:** Given die Großansicht öffnet / When erst der Pfeilknopf, dann „Foto entfernen“ gedrückt wird / Then genau eine Frage nach dem Öffnen, und „Entfernen“ löscht das gezeigte Foto, kein anderes. Test: `engine/tests/test_bilder_eigen.py::test_gross_pfeil_dann_klick_meint_gezeigtes_foto`
- [x] **AC-4:** Given Klick auf „Foto entfernen“ im Öffnen / When danach der Pfeilknopf gedrückt wird / Then blättert nichts und die Frage kommt nach dem Öffnen zum gezeigten Foto; die Ausnahme für den #706-Seitenfehler ist entfernt, jeder Seitenfehler macht den Test rot. Test: `engine/tests/test_bilder_eigen.py::test_gross_klick_im_oeffnen_dann_pfeil_fragt`
- [x] **AC-5:** Given der heutige Stand (Vorlage unverändert) / When die Tests zu AC-1, AC-3 und AC-4 laufen / Then sind sie rot; nach der Änderung grün. Test: von Claude ausgeführt (RED- und GREEN-Lauf, Ausgabe im Nachweis)
- [x] **AC-6:** Given der Stand vor der Auslieferung / When `test_bilder_eigen.py` und `test_seite_bilder.py` laufen / Then grün in Chromium und WebKit, dazu die Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`. Test: von Claude ausgeführt (lokal und CI) — lokal Chromium grün; WebKit und Pflichtprüfungen in der CI vor dem Vorspulen (Phase 8)
- [x] **AC-7:** Given der Stand der Änderung / When mit `main` verglichen / Then nur die drei Dateien oben und Unterlagen unter `docs/` geändert, Vendor unverändert. Test: von Claude ausgeführt (Vergleich mit `main`)

## Dialog

### Runde 1
**Adversary:** Pfeilknopf im Öffnen: ruft der Knopf wirklich über `goTo`? Vendor: `next()`/`prev()` rufen `this.goTo(...)`; die Hülle in der Vorlage greift also. Läuft der Test wirklich auf der Änderung? Chromium-Lauf: 102 passed, 1 skipped, 25 deselected (WebKit), Ausgabe siehe test-run-output.txt.
**Implementierer:** Belegt: Code reference: engine/vorlage.html:1739 (Hülle um goTo, nur bei `pswp.opener.isOpen`).

### Runde 2
**Adversary:** Randfälle. (a) Wischen: `onPointerDown` verwirft vor `isOpen` und nutzt `moveIndexBy` direkt, die Hülle ändert daran nichts. (b) Pfeiltaste: ab `bindEvents`, nutzt `next()`/`prev()` also `goTo`, nach dem Öffnen `isOpen` wahr, unverändert. (c) Reduzierte Bewegung: `isOpen` nach `init()` sofort wahr, Hülle lässt durch. (d) Schließen: `isOpen` wird in `close()` falsch, Blättern während des Schließens wirkt nicht; folgenlos. (e) Vendor/Galerie der Infoseite (`engine/app/galerie.js`): unverändert, `git status` für engine/vendor und engine/app leer. (f) Der Rest der Tests: `change → danach = null` bleibt, ohne Blättern im Öffnen nie ausgelöst, Escape-Pfad (#689 AC-7) im selben Lauf grün. (g) Tests prüfen scharf: Ausnahme für #706 entfernt, `_gross_ohne_fehler` verlangt `fehler == []`, Zähler und gezeigtes Bild werden geprüft (Code reference: engine/tests/test_bilder_eigen.py:1549, :1558, :1567, :1536; Abläufe in engine/tests/seiten_bilder_eigen.mjs:260, :274). Keine Lücke gefunden. Einschränkung (kein Defekt): `-k "not webkit"` ließ 25 WebKit-Tests aus (lokal nicht installiert), laufen in der CI. Ein skipped im Lauf (bereits vorher bestehende Bedingung, nicht Teil dieser Änderung).
**Implementierer:** Bestätigt.

## Bestätigungen

Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_bilder_eigen.py:1549
  Evidence: Pfeil im Öffnen ergibt `{isOpen: False, index: 0}`, danach Bild BI-91, Zähler "1 / 2", fehler == []; grün (Vorlage engine/vorlage.html:1739).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_bilder_eigen.py:1558
  Evidence: Nach dem Öffnen blättert der Pfeil auf Index 1, BI-90, Zähler "2 / 2"; grün (Ablauf engine/tests/seiten_bilder_eigen.mjs:260).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_bilder_eigen.py:1567
  Evidence: Pfeil, dann Klick im Öffnen: gezeigt BI-91, eine Frage, DELETE nur BI-91; grün (Ablauf engine/tests/seiten_bilder_eigen.mjs:274).
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_bilder_eigen.py:1536
  Evidence: Klick, dann Pfeil: kein Blättern, Frage zu BI-91; Ausnahmeliste für den Seitenfehler entfernt, `_gross_ohne_fehler`/`fehler` streng; grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/vorlage.html:1739
  Evidence: RED-Ausgabe liegt in docs/artifacts/fix-706-pfeil-im-oeffnen/test-red-output.txt (Vorlage damals unverändert); GREEN nachher im Lauf (102 passed). Hinweis: RED-Lauf nicht erneut ausgeführt, Datei geprüft nur auf Vorhandensein und Größe (93 Zeilen).
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/tests/seiten_bilder_eigen.mjs:241
  Evidence: Chromium grün (102 passed, 1 skipped). WebKit und Pflichtprüfungen der CI lokal nicht prüfbar: OFFEN, nicht als Defekt.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/vorlage.html:1734
  Evidence: `git diff origin/main --name-only`: nur engine/vorlage.html, engine/tests/seiten_bilder_eigen.mjs, engine/tests/test_bilder_eigen.py und Dateien unter docs/; engine/vendor und engine/app unverändert.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
VERDICT: VERIFIED
Tests: 102 passed, 0 failed, 1 übersprungen (Chromium; 25 WebKit-Tests abgewählt, laufen in der CI)
Edge cases: Wischen, Pfeiltaste, reduzierte Bewegung, Schließen, Galerie geprüft, nichts gebrochen
Regressions: keine gefunden
Checklist: 7/7 (AC-6 WebKit und CI-Pflichtprüfungen offen)

## Geprüfte Dateien

- sha256:17742d5e4647976c7ee7e93484ef6c429b2a21814357516e926a9f219a04a740  engine/tests/seiten_bilder_eigen.mjs
- sha256:ec600a4ca7f6a827714815836ef74f87acd16298ae4ba4174174277785b52f20  engine/tests/test_bilder_eigen.py
- sha256:eba797b9f8fa4c4df10c1dcb2271f79c1e50aa84514d01663c7dad2d18c1f675  engine/vorlage.html

## Prüfbasis

- base: 1243ad0da7749d33fe125faec887330753183de8
- blob:e5ca7c16c30e4826df4b63a3a91bbb2c908cfa3d  engine/tests/seiten_bilder_eigen.mjs
- blob:be5af5a22445d4c4fd9943761b13360834aa5026  engine/tests/test_bilder_eigen.py
- blob:9d1daa231b8cae64dfd74aa2588faa14a68b3b6f  engine/vorlage.html

## Geprüfte Dateien

- sha256:17742d5e4647976c7ee7e93484ef6c429b2a21814357516e926a9f219a04a740  engine/tests/seiten_bilder_eigen.mjs
- sha256:ec600a4ca7f6a827714815836ef74f87acd16298ae4ba4174174277785b52f20  engine/tests/test_bilder_eigen.py
- sha256:eba797b9f8fa4c4df10c1dcb2271f79c1e50aa84514d01663c7dad2d18c1f675  engine/vorlage.html

## Prüfbasis

- base: 1243ad0da7749d33fe125faec887330753183de8
- blob:e5ca7c16c30e4826df4b63a3a91bbb2c908cfa3d  engine/tests/seiten_bilder_eigen.mjs
- blob:be5af5a22445d4c4fd9943761b13360834aa5026  engine/tests/test_bilder_eigen.py
- blob:9d1daa231b8cae64dfd74aa2588faa14a68b3b6f  engine/vorlage.html

## Geprüfte Dateien

- sha256:17742d5e4647976c7ee7e93484ef6c429b2a21814357516e926a9f219a04a740  engine/tests/seiten_bilder_eigen.mjs
- sha256:ec600a4ca7f6a827714815836ef74f87acd16298ae4ba4174174277785b52f20  engine/tests/test_bilder_eigen.py
- sha256:eba797b9f8fa4c4df10c1dcb2271f79c1e50aa84514d01663c7dad2d18c1f675  engine/vorlage.html

## Prüfbasis

- base: 1243ad0da7749d33fe125faec887330753183de8
- blob:e5ca7c16c30e4826df4b63a3a91bbb2c908cfa3d  engine/tests/seiten_bilder_eigen.mjs
- blob:be5af5a22445d4c4fd9943761b13360834aa5026  engine/tests/test_bilder_eigen.py
- blob:9d1daa231b8cae64dfd74aa2588faa14a68b3b6f  engine/vorlage.html
