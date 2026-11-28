# Adversary Dialog — fix-709-push-absender
Spec: docs/specs/konto/push-absender-709.md
Datum: 2026-11-28 09:11

## Checkliste
- [x] **AC-1:** Given ein Konto hat nur Abos der Frieda-App (`reise == ""`) / When `wirksam(abos)` läuft / Then liefert sie alle diese Abos in derselben Reihenfolge.
- [x] **AC-2:** Given ein Konto hat nur alte Reise-Abos / When `wirksam(abos)` läuft / Then liefert sie alle Abos unverändert, und `ziele(wirksam(abos), reise)` ergibt dasselbe wie bisher `ziele(abos, reise)`.
- [x] **AC-3:** Given ein Konto hat ein App-Abo und ein altes Reise-Abo (`beispielreise`) / When `wirksam(abos)` läuft / Then enthält das Ergebnis nur das App-Abo.
- [x] **AC-4:** Given derselbe Zustand / When eine Meldung ohne Reise und eine Meldung zu `beispielreise` zugestellt werden (`zustellen` mit Test-`senden`) / Then geht je Nachricht genau ein Versand an das App-Abo, keiner an das alte Reise-Abo.
- [x] **AC-5:** Given ein App-Abo ohne Gerätekennung (`geraet` leer) neben einem alten Reise-Abo / When zugestellt wird / Then geht die Nachricht nur an das App-Abo (Gerät zählt über `endpoint`).
- [x] **AC-6:** Given ein Konto mit einem App-Abo und einem alten Reise-Abo / When Mein Konto die Benachrichtigungen zeigt / Then steht dort ein Gerät („Push ist auf 1 Gerät eingeschaltet“, `konto.push.geraete`, n = 1), nicht zwei.
- [x] **AC-7:** Given ein Konto nur mit alten Reise-Abos / When zugestellt wird / Then ändert sich das Verhalten nicht (bestehende Tests, u. a. `test_je_geraet_ein_abo_das_der_reise_zuerst`, bleiben grün). Mail-Rückfälle, Ruhezeit und `seite_von` verhalten sich unverändert.

## Dialog

### Runde 1
**Adversary:** Diff und Spec gelesen, Tests ausgeführt (84 bestanden, 0 fehlgeschlagen, 0 übersprungen; test_push.py und test_konten.py, Ausgabe in test-run-output.txt). Jede AC einzeln gegen den Code geprüft.

Confirmation:
  AC: AC-1
  Code reference: engine/push.py:366
  Evidence: wirksam() filtert `a["reise"] == ""` per Listenfilter, Reihenfolge der Eingabe bleibt; nur App-Abos ergeben die gleiche Liste.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/push.py:370
  Evidence: Ohne App-Abo `return app if app else abos` gibt die unveränderte Eingabe zurück; ziele() ist unverändert, also identisch zu vorher.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/push.py:369
  Evidence: Mit App-Abo enthält das Ergebnis ausschließlich Abos mit reise == "".
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/push.py:426
  Evidence: zustellen ruft ziele(wirksam(abos), reise) für jede Reise-Gruppe, auch für reise "" ; alte Abos sind nicht mehr in der Kandidatenliste, je Gerät höchstens ein Versand.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/push.py:355
  Evidence: ziele() schlüsselt über `geraet or endpoint`; die gefilterte Liste enthält nur das App-Abo, ein leeres geraet kann also kein altes Abo verdrängen oder ergänzen.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/anmeldung.py:462
  Evidence: push_karte zählt die Mengen der Gerätekennungen über push.wirksam(konten.push_abos(...)); App-Abo plus altes Abo ergibt 1.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/push.py:239
  Evidence: einreihen, Statushinweise (push.py:576), _zone_von (push.py:606) und seite_von (push.py:336) nutzen weiter ungefiltertes konten.push_abos; git diff zeigt keine Änderung dort. Bestehende Tests grün.
  Status: CONFIRMED

**Implementierer:** keine Antwort (Adversary-Lauf ohne Rückfrage). Alle Punkte in Runde 1 bewiesen; wegen Frühkonvergenz folgt Runde 2 mit Randfällen.

### Runde 2
**Adversary:** Randfälle:
- reise None statt "": Spalte `reise TEXT NOT NULL DEFAULT ''` (engine/konten.py:166), push_abo_speichern normalisiert auf "" (engine/konten.py:1584). None kann nicht in der DB stehen; ein Abo mit ungültigem Reisenamen wird zum App-Abo (bestehendes Verhalten, nicht neu).
- Ruhezeit/Zeitzone: push.py:416 und :606 nehmen abos[0] ungefiltert; abos[0] kann ein altes Abo sein, dessen Zeitzone dann gilt. Laut Spec ausdrücklich unverändert (Nicht Teil dieser Änderung); praktisch folgenlos, weil dasselbe Konto/Gerät gleiche Zone hat.
- Mail-Rückfall: push.py:239 und :576 prüfen nur "hat Abos". Ein Konto mit altem und App-Abo gilt weiter als "hat Push"; Spec-konform.
- Alle Abos "weg": weg == len(geraete) bezieht sich auf die gefilterte Liste (push.py:439); sind App-Abos weg, werden sie gelöscht und beim nächsten Lauf kommen alte Abos wieder zum Zug. Nachricht der aktuellen Runde ist erledigt, nicht verloren-doppelt. Kein Fehler, nur Nebenwirkung der Variante 2.
- Fehler (Ausnahme) des App-Abos: kein Rückfall auf altes Abo, Wiederholung bis MAX_VERSUCHE; bewusste Folge laut Spec.
- Mehrere App-Abos (zwei Geräte): alle bleiben, je Gerät eins; kein Abo verloren.
- push_aus (anmeldung.py:1885) löscht alle Abos, unabhängig von wirksam; keine Regression.
- Stichprobe Gesamtlauf: Betriebs-/Shell-Fehler (getent, bash 3.2) berühren push.py/anmeldung.py nicht; geänderte Module nur von test_push/test_konten getestet, beide grün.

Finding-Kandidaten geprüft, keiner erfüllt Schwelle:
- Keine Findings (Beobachtungen oben sind spec-konform).

**Implementierer:** n/a.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Das neue Feld-Lesen betrifft nur `a["reise"] == ""`; Schreibstelle ist push_abo_speichern (engine/konten.py:1584) und anmeldung.push_geraet_schalten, Bedingung: gültiger Reisename sonst "". Test für diesen Weg: test_wirksam_app_abo_verdraengt_alte und test_zustellen_nur_ueber_die_frieda_app in engine/tests/test_push.py.

## Verdict

VERDICT: VERIFIED

Tests: 84 passed, 0 failed, 0 übersprungen. Edge cases: alle geprüft, keine gebrochen. Regressions: keine. Checklist: 7/7 proven.

## Geprüfte Dateien

- sha256:9222b99e4be911f828a63cf68e100eebd9c85b872d19ad9dbdbf7969f08e1d11  engine/anmeldung.py
- sha256:43c47c7e4cdf369e68f11c32db207279991b08ce95e088dbabc7c2ea2a146c29  engine/push.py

## Prüfbasis

- base: b0ae30bb75c45577d9cd81108e54a6e3eb9ea535
- blob:6a4465f995141b262e730a9f0ecb40e3cbc2d235  engine/anmeldung.py
- blob:11e3a0e5e39627a6177b393e371045272edc1c1b  engine/push.py

## Geprüfte Dateien

- sha256:9222b99e4be911f828a63cf68e100eebd9c85b872d19ad9dbdbf7969f08e1d11  engine/anmeldung.py
- sha256:43c47c7e4cdf369e68f11c32db207279991b08ce95e088dbabc7c2ea2a146c29  engine/push.py

## Prüfbasis

- base: b0ae30bb75c45577d9cd81108e54a6e3eb9ea535
- blob:6a4465f995141b262e730a9f0ecb40e3cbc2d235  engine/anmeldung.py
- blob:11e3a0e5e39627a6177b393e371045272edc1c1b  engine/push.py
