# Adversary Dialog — papierkorb-146
Spec: docs/specs/oberflaeche/papierkorb-146.md
Datum: 2026-10-30 17:45

## Checkliste
- [x] **Input:** Eine Reise hat an einem Ding mindestens eine stornierte Buchung.
- [x] **Output:** Die Seite zeigt an diesem Ding nur die geltenden Buchungen voll, die stornierten in einem zugeklappten Block „Storniert (n)“ mit Hinweis „Zurückholen: im Gespräch mit Frieda.“
- [x] **Side effects:** Keine. Daten, IDs, Verläufe, Konnektor, Schreibweg und Rückmeldedienst bleiben unberührt.
- [x] **AC-1:** Given U-01 hat B-01 (gebucht) und B-03 (storniert). When die Seite U-01 zeigt (Unterkunftskarte im Abschnitt „Nacht“ der Tagesseite und, bei einer Reise ohne Tagesseiten, im Tageskasten des Plans), Then ist B-01 als volle Karte sichtbar, B-03 steht nicht voll im Tag, an der Unterkunft oder im Tageskasten.
- [x] **AC-2:** Given dieselbe Ansicht. When die Seite geladen ist, Then gibt es genau einen Block `details.weg` mit der Zusammenfassung „Storniert (1)“, er ist zugeklappt, und die Karte von B-03 ist darin enthalten, aber nicht sichtbar.
- [x] **AC-3:** Given ein Ding ohne stornierte Buchung (z. B. E-20 mit B-02). When die Seite es zeigt, Then gibt es dort keinen Block „Storniert“ und keinen Hinweis zum Zurückholen.
- [x] **AC-4:** Given der Block ist aufgeklappt. When man ihn liest, Then steht dort die Hinweiszeile „Zurückholen: im Gespräch mit Frieda.“ und B-03 mit durchgestrichenem Chip „storniert“, Nummer, Grund im Verlauf („Zimmer doppelt gebucht …“) und Verlauf (2 Einträge).
- [x] **AC-5:** Given `location.hash = "B-03"`. When die Route angesteuert wird, Then ist B-03 sichtbar, der Block „Storniert (1)“ ist offen, und B-03 steht bei seinem Ding (U-01). Das gilt mit und ohne Tagesseiten (`darstellung.tiefe`).
- [x] **AC-6:** Given eine Strecke, ein Aufenthalt ohne Nacht oder ein Tageskasten mit einer stornierten Buchung . When die Seite sie zeigt, Then gilt dasselbe wie in AC-1 bis AC-3, denn alle vier Aufrufstellen nutzen denselben Helfer. Prüfweg: ein Quelltext-Test in `test_seite.py` liest `engine/vorlage.html` und prüft, dass `streckeZeile`, `aufenthaltZeile`, `tagKarte` und `unterkunftKarte` je `stornierteBuchungen(stornierteBei(…))` aufrufen und keine von ihnen stornierte Buchungen über `buchungBlock` voll zeichnet.
- [x] **AC-7:** Given V-03 mit einer verworfenen Option (V-03.b). When die Seite die Zeile „Alle Möglichkeiten“ zeigt, Then steht dort die Zahl der gültigen Optionen (nicht verworfen, nicht ersetzt), und die verworfene steht weiter im Block „Verworfen (n)“ der Karte. Bei V-03 (eine gültige, eine verworfene Option) steht auf der Tagesseite „Alle Möglichkeiten (1)“, und `#V-03.b` öffnet „Verworfen (1)“. Hat die Wahlstelle insgesamt nur eine Option, erscheint die Zeile nicht.
- [x] **AC-8:** Given B-03 ist storniert. When die Seite Stände zählt (Chip der Unterkunft, Zeitachse, „Zu buchen“, Zähler), Then wird B-03 nirgends als „gebucht“ gezählt; U-01 zeigt „gebucht“ aus B-01.
- [x] **AC-9:** Given der Konnektor `ueberblick` auf der Beispielreise. When er die Buchungen zählt, Then lautet die Zeile „## Buchungen: 2 gebucht, 1 storniert (zeige B-…)“; `zeige U-01` nennt weiter „Buchung: gebucht (B-01, zeige B-01)“.
- [x] **AC-10:** Given die Bausteinseite `#bausteine`. When sie geladen ist, Then zeigt sie das Molekül „Stornierte Buchungen“ mit einer Buchung, und `test_design.py` ist grün (vier Stellen).
- [x] **AC-11:** Given ein Rundgang durch alle Routen und Kennungen der Beispielreise (`seiten_browser.mjs`). When `#B-03` besucht wird, Then ist die Seite nicht leer, ohne waagerechtes Scrollen bei 390 px und mit erlaubten Schriftgrößen; die Kennung gehört der Grundform Buchung an (kein Eintrag in `ohneArt`).
- [x] **AC-12:** Given der Gesamtlauf. When `engine/.venv/bin/python -m pytest -q engine/tests` ohne echte Reisen läuft, Then ist alles grün; die neuen Prüfungen sind ohne die Änderung rot (TDD RED).
- [x] **AC-13:** Es wird nichts gelöscht: Die YAML-Daten, der Verlauf und die Kennung B-03 sind nach dem Bauen vollständig in `R.buchungen` enthalten (Test liest B-03 mit Status und beiden Verlaufseinträgen aus den gebauten Daten).

## Dialog

### Runde 1
**Adversary:** Gesamtlauf pytest -q engine/tests: 643 passed, 0 failed, 0 übersprungen (adversary-test-output.txt). Eigene Sonden in chromium und webkit gegen eine abgewandelte Beispielreise (B-01 und B-02 ebenfalls storniert, B-03 mit zwei Dingen U-02 und U-01, mit und ohne festen Plan): Dinge nur mit stornierter Buchung zeigen „nicht gebucht“, Zu buchen zählt „0 von 6“, kein Chip führt zu einer stornierten Buchung, #B-01, #B-02, #B-03 sind sichtbar und öffnen den Block am eigenen (ersten) Ding, B-03 nur an U-02. Kein Skriptfehler. Die vier Aufrufstellen rufen den Helfer auf, buchungenBei filtert den Status, stornierteBei das Gegenteil, Bausteinseite zeichnet das Molekül mit echter oder Muster-Buchung.
Code reference: engine/vorlage.html:1075
Code reference: engine/vorlage.html:1197
Code reference: engine/vorlage.html:1229
Code reference: engine/vorlage.html:1294
Code reference: engine/vorlage.html:1338
Code reference: engine/vorlage.html:1392
Code reference: engine/vorlage.html:3441
Code reference: docs/design.md:13
Code reference: beispiel/reisen/beispielreise/plan/routen.yaml:132
**Implementierer:** Alle Stellen wie in der Spec umgesetzt.

### Runde 2
**Adversary:** Nachprüfung von F001 nach der Entscheidung des Product Owners (Variante A). In engine/vorlage.html:2984 steht die Zeile jetzt bei w.optionen.length größer 1, die Zahl ist gueltigeOptionen(w).length. Sonde in chromium und webkit auf der Tagesseite T-02 (fester Plan): #V-03, #V-03.a und #V-03.b sind wieder Ziele, #V-03.b ist sichtbar und öffnet „Verworfen (1)“. Die Zeile lautet „Alle Möglichkeiten (1)“. Eine Wahlstelle mit genau einer Option insgesamt hat keine Zeile (Bedingung optionen.length größer 1). Die Tests sind angepasst: seiten_variante.mjs:92 misst verworfenSichtbar nach #V-03.b, test_seite.py:209 erwartet „Alle Möglichkeiten (1)“, „Verworfen (1)“ und verworfenSichtbar; die Sichtbarkeitsmessung in seiten_variante.mjs:27 bleibt streng (umschließendes details muss offen sein). F001 ist damit erledigt. Neuer Randfall F002: Sind alle Optionen einer Wahlstelle verworfen oder ersetzt (mehr als eine), steht die Zeile „Alle Möglichkeiten (0)“; das folgt aus Variante A und ist ein Schönheitsfehler, kein Verlust.
Code reference: engine/vorlage.html:2984
Code reference: engine/tests/seiten_variante.mjs:92
Code reference: engine/tests/test_seite.py:209
Code reference: engine/tests/test_konnektor.py:877
Code reference: engine/tests/test_schreiben.py:965
Code reference: engine/tests/test_regeln.py:27
Zu (a): Die Sichtbarkeitsmessung ist nur strenger geworden und weicht nichts auf. Zu (b): doppeltes B-03 im Plan ohne Tagesseiten ist vorhandenes, akzeptiertes Verhalten. Zu (c): keine Flakiness in zwei Gesamtläufen und den Sonden.
**Implementierer:** Zeile und Zahl wie vom Product Owner entschieden; F002 (Null-Zähler) ist ein Randfall der Entscheidung.

### Bestätigungen und Findings

Confirmation:
  AC: AC-1
  Code reference: engine/vorlage.html:1338
  Evidence: unterkunftKarte zeichnet nur geltende Buchungen voll, stornierte über stornierteBuchungen; B-01 sichtbar, B-03 nur im zugeklappten Block, mit und ohne Tagesseiten.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/vorlage.html:1392
  Evidence: genau ein details.weg mit „Storniert (n)“, zugeklappt.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/vorlage.html:1392
  Evidence: leere Liste ergibt []; E-20 mit B-02 hat keinen Block und keinen Hinweis.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/vorlage.html:1392
  Evidence: Hinweiszeile „Zurückholen: im Gespräch mit Frieda.“ und unveränderte Karte (Chip, Nummer, Verlauf mit Grund).
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/vorlage.html:1197
  Evidence: heimat führt zum ersten Ding, zumZiel öffnet alle details; Sonde bestätigt, mit und ohne Tagesseiten.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/vorlage.html:1229
  Evidence: streckeZeile (1197), aufenthaltZeile (1229), tagKarte (1294) und unterkunftKarte (1338) nutzen den Helfer; Quelltext-Test test_seite.py:218 grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/vorlage.html:2984
  Evidence: Zeile bei mehr als einer Option, Zahl nur gültige; Sonde auf T-02 zeigt „Alle Möglichkeiten (1)“ und #V-03.b sichtbar in „Verworfen (1)“, chromium und webkit.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/vorlage.html:1075
  Evidence: buchungsStand liest nur die geltende Buchung; bei allen Buchungen storniert „nicht gebucht“ und „0 von 6“.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/tests/test_konnektor.py:877
  Evidence: Test erwartet „2 gebucht, 1 storniert“, grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/vorlage.html:3441
  Evidence: ansichtBausteine ruft stornierteBuchungen auf (echte oder Muster-Buchung B-00); Kopfkommentar und docs/design.md:13 nennen das Molekül; test_design grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: beispiel/reisen/beispielreise/plan/routen.yaml:132
  Evidence: B-03 in R.buchungen, Rundgang seiten_browser.mjs grün in chromium und webkit.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/tests/test_regeln.py:27
  Evidence: Gesamtlauf 643 passed, 0 failed, 0 übersprungen.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/tests/test_schreiben.py:965
  Evidence: B-03 mit Status und zwei Verlaufseinträgen in den gebauten Daten, neue ID B-04.
  Status: CONFIRMED

Finding:
  ID: F001
  Severity: MEDIUM
  Category: spec_violation
  Code reference: engine/vorlage.html:2984
  Description: Früherer Befund (verworfene Option und Links #V-03.b auf der Tagesseite verschwanden). Nach Entscheidung des Product Owners behoben und nachgeprüft.
  Spec requirement: AC-7 — verworfene Option bleibt im Block „Verworfen (n)“ erreichbar
  Conflict: erledigt; Sonde zeigt #V-03.b sichtbar auf T-02.
  Remediation: keine mehr nötig.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/vorlage.html:2984
  Description: Sind bei mehr als einer Option alle verworfen oder ersetzt, lautet die Zeile „Alle Möglichkeiten (0)“.
  Spec requirement: AC-7 — Zahl der gültigen Optionen
  Conflict: spec-konform, aber wenig sinnvolle Anzeige; kein Datenverlust.
  Remediation: optional Zeile anders benennen, wenn keine gültige Option bleibt.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Gesamtlauf 643 passed, 0 failed, 0 übersprungen. 16 von 16 Punkten der Checkliste belegt; F001 nach der PO-Entscheidung behoben und im Browser nachgeprüft (chromium und webkit). Offen nur F002 (LOW, Schönheitsfehler bei lauter verworfenen Optionen).

## Geprüfte Dateien

- sha256:0577ab2ec0345fd5c9db4e7ee4fa472b5e3aad8dbde9da243dc6949f639e0803  beispiel/reisen/beispielreise/plan/routen.yaml
- sha256:25346dd8bc152145ff899fcba174d7b7ba033b1bcb37e427047a409fabfb6f7d  docs/design.md
- sha256:33691b1613fe9fca7dcbdb626009c5f44d82a25a1083ce56aff6e4e2e57bcc43  engine/tests/seiten_variante.mjs
- sha256:2413700eb9b7029358682b254aaa7f8ef1ab8da1262a0f22e43dc10081d5ba85  engine/tests/test_konnektor.py
- sha256:b2d956afe38b2360951d3f3145f41e051142854415dcba4ebd22a63928c7aece  engine/tests/test_regeln.py
- sha256:fd9e347615475cbc0fea139c0c9c4a725de517f0cc8a4cd2508ba5a04b4c55a2  engine/tests/test_schreiben.py
- sha256:49fcc4a82a6e2df00c8c74fdc45a0251e523d9b0cc3cab9cf7d98e6fe72d37a3  engine/tests/test_seite.py
- sha256:940a76b011d14df705cbd7cec55b45e661aec7fbdfdee3a4462d72cd39fe4b23  engine/vorlage.html

## Prüfbasis

- base: 13710598fa6fe2bfb91b9eac558fafb5a4b32d9a
- blob:c7f58f722142a4823cf8d779a4528d04b1f78051  beispiel/reisen/beispielreise/plan/routen.yaml
- blob:b12f22a6825d0067eed3bbf06505d443c8859747  docs/design.md
- blob:6e57785d5e6451ad6200fd20eb1d02cab74e6d24  engine/tests/seiten_variante.mjs
- blob:fb0b89729077a88bdb96a4dc0d9e94c8e377240a  engine/tests/test_konnektor.py
- blob:2abca5c637d9374eac9321d5fc8bf7b794ce6cd7  engine/tests/test_regeln.py
- blob:027cd6c058cc1d59fd709eb1cf45e4f603ae234b  engine/tests/test_schreiben.py
- blob:d43588895419fd6271e9f3751b465beb1a54400b  engine/tests/test_seite.py
- blob:4e8642ef96eff1ea37dcde9c8925dba630773d94  engine/vorlage.html
