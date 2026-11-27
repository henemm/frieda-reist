# Adversary Dialog — fix-692-macos-temp-pfade
Spec: docs/specs/fast/fix-692-macos-temp-pfade.md
Datum: 2026-11-27 19:16

## Checkliste
- AC-1: test_muster_erkennt_macos_temp vorher rot, jetzt grün — PROVEN
- AC-2: test_protokolle_ohne_absolute_pfade grün; altes #694-Protokoll wäre gemeldet worden — PROVEN
- AC-3: übrige Tests grün (Befund siehe Runde 2), alte Muster unverändert, /tmp/… erlaubt — PROVEN
- Invarianten: nur Pfad-Ersetzungen zu $TMPDIR/ in #694 und #656, keine weiteren Protokolle, Kennung nirgends mehr — PROVEN

## Dialog

### Runde 1
**Adversary:** Behauptung: Das Muster greift und die Protokolle sind bereinigt. Beweis? Ich glaube erst, wenn das alte Muster die Beispiele wirklich nicht erkennt und das neue die alte Protokollfassung wirklich meldet.
**Implementierer:** Gemessen (Muster aus dem Stand febd806 per git show geladen, neues Muster aus dem Arbeitsordner): Das alte Muster erkennt keines der drei Beispiele im Test (/private/var/folders/…, /private/tmp/…, /var/folders/…): jeweils False, also schlägt die erste assert von test_muster_erkennt_macos_temp vorher fehl (rot). Jetzt: 4 passed in test_protokolle_ohne_pfade.py. Das neue Muster meldet in der alten Fassung von #694 198 von 5320 Zeilen, in der alten Fassung von #656 0 von 155 (die gekürzte Form mit … ist laut Spec absichtlich erlaubt). Die heutigen Protokolle: 0 Funde.
**Adversary:** Die 30 übrigen geänderten Zeilen in #694 und die Zeile in #656 sind gekürzte Formen. Wurde dort mehr als der Temp-Teil verändert?
**Implementierer:** Mechanischer Vergleich Zeile für Zeile gegen febd806: #694 hat 5320 Zeilen vorher und nachher, 228 geänderte Zeilen (198 volle Form plus 30 mit gn/T/-Kennung, entspricht der Zählung der Spec); #656 155 Zeilen, 1 geänderte. Nach Anwendung der Ersetzung der Temp-Ordner-Teil bis T/ zu $TMPDIR/ stimmen alle geänderten Zeilen überein, bis auf 12 Zeilen mit mittig gekürzter Form, in denen der ganze gekürzte Ordnerteil bis T/ zu $TMPDIR/ wird (z. B. kd = Zeilen mit aufrufe.log); dort bleibt der Rest der Zeile (Testname, Dateiname, Speicheradresse) identisch. Die #656-Diff-Zeile ersetzt nur den Teil von ...olders/…/T/ durch ...$TMPDIR/. git diff --name-only gegen febd806 nennt nur die zwei Protokolle, die Artefakte, Briefing und Spec dieses Workflows und den Test: keine weiteren Protokolle. git grep nach 0000gn, 0000g, w5wl, 9n/w5, q1x7j, b5nw6, vj80000: 0 Treffer; die Treffer für var/folders stehen nur in Spec, Briefing und Test (ohne Kennung).

### Runde 2
**Adversary:** Zu früh einig. Randfälle des Musters: bricht es etwas Altes? Und die Volltests?
**Implementierer:** Muster Zeile 9: die alten Alternativen home|Users|srv|mnt|root|var/www sind unverändert, neu (?:private/)?var/folders, private/var(?!/folders\b) und private/tmp. Ohne Namen (/private/var/folders/… mit Auslassungspunkten) trifft nichts, weil nach dem Schrägstrich ein Wortzeichen folgen muss; /tmp/ mit Platzhalter und $TMPDIR bleiben erlaubt (assert not in Zeile 44, grün). PYTEST_TMP unverändert (Zeile 10). Volle Suite (engine/tests, -n 3): 92 failed, 3221 passed, 455 skipped, 41 errors. Die 133 Fehler liegen in test_nginx, test_nginx_reise_helfer, test_betrieb, test_kartendienst(_skript), test_units(_helfer), test_nginx_helfer, test_rueckbau_557 (Liste in adversary-suite-fehler.txt). Gegenprobe im sauberen Basisstand febd806 (eigener Worktree, danach entfernt) mit genau diesen Dateien: ebenfalls 92 failed, 41 errors. Also vorbestehend und rechnerbedingt (macOS ohne nginx/systemd), nicht durch diese Änderung verursacht; keine Datei der Änderung wird dort berührt. Alle übrigen Tests grün, test_protokolle_ohne_pfade 4/4.
**Adversary:** Die Suite ist damit nicht grün. Das darf kein VERIFIED ohne Hinweis sein.
**Implementierer:** Dem stimmt der Prüfer zu: Die Rotbefunde sind identisch im Basisstand und liegen außerhalb des Änderungsbereichs (kein Test der Gruppe liest das Muster; test_betrieb liest docs/artifacts nur beiläufig, gleiche Fehlerzahl vor und nach der Änderung). Es gibt keinen Fehler, der durch die Änderung neu hinzukam: gleiche Anzahl vorher und nachher. Als Hinweis im Verdict vermerkt.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`).

## Findings und Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:40
  Evidence: test_muster_erkennt_macos_temp (Zeilen 40 bis 45) prüft drei Beispiele als erkannt und drei Platzhalter als nicht erkannt; Muster aus febd806 erkennt die drei Beispiele nicht (vorher rot), jetzt 4 passed.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:13
  Evidence: test_protokolle_ohne_absolute_pfade grün; das neue Muster (Zeile 9) meldet die alte Fassung von #694 in 198 Zeilen, die heutige Fassung in 0.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/tests/test_protokolle_ohne_pfade.py:9
  Evidence: Alte Alternativen und PYTEST_TMP (Zeile 10) unverändert; /tmp/ mit Platzhalter bleibt erlaubt (Zeile 44); Suite: gleiche 92 Fehler und 41 Errors wie im Basisstand, keine neuen.
  Status: CONFIRMED

Confirmation:
  AC: Invariante #694
  Code reference: docs/artifacts/fix-694-konto-loeschen-ablage-neu/test-run-output.txt:61
  Evidence: Zeile mit $TMPDIR/ statt Temp-Ordner; 228 geänderte Zeilen von 5320, sonst identisch; Kennung kommt im Repo nicht mehr vor.
  Status: CONFIRMED

Confirmation:
  AC: Invariante #656
  Code reference: docs/artifacts/fix-656-vorab-ordner-faden/test-red-output.txt:91
  Evidence: Genau eine Zeile geändert, nur der mittig gekürzte Temp-Teil wurde zu ...$TMPDIR/.
  Status: CONFIRMED

## Verdict
Basis: base_commit febd806074e1ffbb9c5264da21ff0cc39ee2e5d4

VERDICT: VERIFIED

Hinweis: Gesamtsuite nicht grün (92 failed, 41 errors), identisch im Basisstand febd806 (macOS ohne nginx/systemd), also keine Folge dieser Änderung.

## Geprüfte Dateien

- sha256:a56412bad5870099ccefd5435df988139bebb1bbdf07b1b3cb68944ae8b93fd9  docs/artifacts/fix-656-vorab-ordner-faden/test-red-output.txt
- sha256:a8e88dba7777f698241b186c6f12b3e3605e35f0e5cdb5625789eb5e4e983a28  docs/artifacts/fix-694-konto-loeschen-ablage-neu/test-run-output.txt
- sha256:c9aa03bc98664eeae55c95aa2070038ff3d648493767d964b8fec04a0772e1d0  engine/tests/test_protokolle_ohne_pfade.py

## Prüfbasis

- base: febd806074e1ffbb9c5264da21ff0cc39ee2e5d4
- blob:750586836076bc026bdc27d2d9f19c2d5e95b087  docs/artifacts/fix-656-vorab-ordner-faden/test-red-output.txt
- blob:5f0b5f4aacff5802e6ae7fe2a797242f0c9e2049  docs/artifacts/fix-694-konto-loeschen-ablage-neu/test-run-output.txt
- blob:c68825a6188589cae603028ce78f4c3b9e80c87d  engine/tests/test_protokolle_ohne_pfade.py

## Geprüfte Dateien

- sha256:a56412bad5870099ccefd5435df988139bebb1bbdf07b1b3cb68944ae8b93fd9  docs/artifacts/fix-656-vorab-ordner-faden/test-red-output.txt
- sha256:a8e88dba7777f698241b186c6f12b3e3605e35f0e5cdb5625789eb5e4e983a28  docs/artifacts/fix-694-konto-loeschen-ablage-neu/test-run-output.txt
- sha256:c9aa03bc98664eeae55c95aa2070038ff3d648493767d964b8fec04a0772e1d0  engine/tests/test_protokolle_ohne_pfade.py

## Prüfbasis

- base: febd806074e1ffbb9c5264da21ff0cc39ee2e5d4
- blob:750586836076bc026bdc27d2d9f19c2d5e95b087  docs/artifacts/fix-656-vorab-ordner-faden/test-red-output.txt
- blob:5f0b5f4aacff5802e6ae7fe2a797242f0c9e2049  docs/artifacts/fix-694-konto-loeschen-ablage-neu/test-run-output.txt
- blob:c68825a6188589cae603028ce78f4c3b9e80c87d  engine/tests/test_protokolle_ohne_pfade.py
