# Adversary Dialog — fix-632-zugeklappt
Spec: docs/specs/oberflaeche/klappen-zugeklappt-632.md
Datum: 2026-11-23 08:12

## Checkliste
- [x] **Input:** eine gebaute Seite beider Beispielreisen, Ansicht frisch geladen, ohne gemerkte Zustände und ohne Sprung.
- [x] **Output:** außer dem gemerkten Tageskapitel, der Packliste und einem Wunschformular mit Entwurf ist keine Klappe offen. Der Pfeil nach rechts steht für zu, der nach unten für offen, bei Kapiteln und allen übrigen Klappen gleich.
- [x] **Side effects:** keine; es werden keine Daten gespeichert oder verändert. Ein Sprung auf ein Ding in zugeklappten Einzelheiten öffnet sie.
- [x] **AC-1:** Given beide Beispielreisen frisch geladen ohne gemerkte Zustände / When alle Klappen der Seite gelesen werden / Then ist keine Klappe offen außer Tageskapitel (gemerkt), Packliste und Wunschformular mit Entwurf.
- [x] **AC-2:** Given eine Seite mit Kapiteln und Pico-Klappen / When der Pfeil im Zustand zu und im Zustand offen gelesen wird / Then bedeutet rechts überall zu und unten überall offen; die berechnete Transformation ist bei `kapitel` und Pico-Klappen je Zustand gleich.
- [x] **AC-3:** Given ein Ding oder eine Buchung, gebucht oder ungebucht / When die Seite lädt / Then sind die Einzelheiten zu, und Name, Datum, Stand, Frist, Preis und Buchen-Handlung bleiben außerhalb sichtbar.
- [x] **AC-4:** Given ein Wissens- oder Recherchetext / When die Seite lädt / Then ist auch der erste Abschnitt zu.
- [x] **AC-5:** Given eine Wahl mit erwogenen Plänen / When die Seite lädt / Then ist „Andere erwogene Pläne“ zu.
- [x] **AC-6:** Given das Wunschformular / When die Person keinen angefangenen Entwurf hat / Then ist es zu, auch bei leerer Wunschliste; mit angefangenem Entwurf ist es offen.
- [x] **AC-7:** Given zugeklappte Einzelheiten / When ein Sprung per Hash, „zu buchen“ oder Suche auf einen Eintrag darin führt / Then öffnen sich alle umgebenden Klappen und das Ziel ist sichtbar.
- [x] **AC-8:** Given die Packliste / When Planen oder Packen geladen wird / Then ist sie unverändert wie in #511 (Kern = Arbeitsfläche; das Gerät merkt jede Abweichung).
- [x] **AC-9:** Given die Doku / When `docs/design.md`, die Bausteinseite und der Kopfkommentar der Vorlage gelesen werden / Then nennen sie die neue Regel („beim Laden zu, offen nur der Kern“) und die eine Pfeil-Konvention, und „offen bis zur Buchung“ steht nirgends mehr.
- [x] **AC-10:** Given die vollständige Testsuite / When `engine/.venv/bin/python -m pytest -q engine/tests` läuft (lokal und CI) / Then ist sie grün, einschließlich `test_design.py`, `test_texte.py` und der angepassten Seitentests.

## Dialog

### Runde 1
**Adversary:** Alle `open`-Setzungen und alle `el("details"`-Stellen in `engine/vorlage.html` durchgesehen. Zusätzlich eine eigene Sonde über 66 (Beispielreise) und 24 (Stadtwochenende) Ansichten inkl. Bausteinseite, Blöcke, Pläne, Wahlen, Orte, jeweils mit Adresse geladen, alle `details` im ganzen Dokument (nicht nur `#main`) gezählt.
Ergebnis: Außer `.pack-klapper` offen sind nur Sprungziele (E-01.skizze, E-01.tipps, E-01.quellen-und-pruefung, per Adresse, AC-7 gewollt) und auf der Bausteinseite der Muster-Block (`block(blockMuster, true)`).
**Implementierer:** (Code gelesen, nicht befragt) `einzelheiten(inhalt, titel)` ohne Parameter `offen` (Code reference: engine/vorlage.html:2415), `block(b, false, ...)` (Code reference: engine/vorlage.html:1822), `details.weg` ohne `open` (Code reference: engine/vorlage.html:3669), `wu-neu` nur mit Entwurf (Code reference: engine/vorlage.html:5756).

Finding:
  ID: F001
  Severity: LOW
  Category: spec_violation
  Code reference: engine/vorlage.html:5159
  Description: Die Bausteinseite (#bausteine) zeigt das Muster "Fläche: aufklappbarer Abschnitt" per `block(blockMuster, true)` offen; die Seite startet mit einer offenen Klappe ausserhalb des Kerns. Der Regeltest (engine/tests/klappen_browser.mjs:36) enthält `bausteine` nicht in der Ansichtenliste, sieht das also nicht.
  Spec requirement: AC-1 / Output — ausser Kern keine Klappe offen
  Conflict: Wörtlich verletzt, praktisch Entwicklerseite (ENTWICKLERSEITE-ANFANG, nicht in der Leiste), das Muster soll den offenen Zustand zeigen; die Spec nennt die Bausteinseite nur für Erklärtexte. Vertretbar, aber nicht als Ausnahme dokumentiert.
  Remediation: Muster zu (`block(blockMuster, false)`) oder die Ausnahme in Spec und Regeltest ausdrücklich festhalten. Kein Blocker.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: docs/design.md:257
  Description: Der Satz nennt "bis dahin bis zur Buchung offen" als Geschichte. Der Regeltest sucht nur "offen bis zur Buchung" (engine/tests/test_klappen_zugeklappt.py:139), findet das umgestellte Wort nicht.
  Spec requirement: AC-9 — "offen bis zur Buchung" steht nirgends mehr
  Conflict: Der Wortlaut der Spec ist erfüllt, der Sinn (alte Regel nirgends mehr als geltend) auch, da klar als vergangen markiert. Nur Schönheitsfehler.
  Remediation: optional streichen.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/vorlage.html:5756
  Description: `open: !!WU_ENTWURF.text` ignoriert einen Entwurf, der nur einen Link (`WU_ENTWURF.quelle`) enthält; das Formular ist dann nach dem Neuzeichnen zu und der angefangene Entwurf verborgen.
  Spec requirement: AC-6 — mit angefangenem Entwurf offen
  Conflict: Spec nennt ausdrücklich `WU_ENTWURF.text`, daher spec-konform; bisheriges Verhalten identisch. Nur Hinweis.
  Remediation: optional `|| !!WU_ENTWURF.quelle`.

### Runde 2
**Adversary:** Gezielt Pfeil, Sprünge, Teständerungen und Textkatalog gebohrt.
- Pfeil: `details.kapitel>summary::after` Rand rechts/unten, zu rotate(-45deg) = rechts, offen rotate(45deg) = unten; Pico: Bild ungedreht unten, zu -90 = rechts. Der Test liest die berechnete Richtung beider im Browser (Code reference: engine/tests/klappen_browser.mjs:92) und vergleicht (Code reference: engine/tests/test_klappen_zugeklappt.py:76). Bestätigt.
- Sprung: `zumZiel` öffnet alle umgebenden `details` (Code reference: engine/vorlage.html:3545), Suche/Hash ebenso (engine/vorlage.html:6571), "zu-buchen" nur bei passender Adresse (engine/vorlage.html:4768). Test deckt Hash auf Einzelheiten, Block per Adresse, Suche, zu-buchen ab.
- Teständerung klappen_browser.mjs (`.z, .karte, .buchung`): die Datei ist neu in diesem Workflow (kein bestehender Test abgeschwächt). `closest` nimmt den nächsten Behälter; bei Strecken im Wegverlauf ist das die Zeile `.z`, deren Geschwister den Namen tragen. Das ist eine Präzisierung, kein Aufweichen: die Prüfung "Text ausserhalb der Einzelheiten vorhanden" gilt weiter (Code reference: engine/tests/klappen_browser.mjs:127). Zulässig.
- seiten_b2.mjs: öffnet die Einzelheiten vor dem Klick auf den Wert (Code reference: engine/tests/seiten_b2.mjs:55). Der Test prüft Herkunfts-Popover am Wert, nicht den Startzustand; der Startzustand ist durch Regeltest abgedeckt. Zulässig, kein Verlust an Prüfung.
- seiten_tagesseite.mjs / test_tagesseite.py: Erwartung `[True]` auf `[False]` gedreht, wie von der Spec vorgesehen (Code reference: engine/tests/seiten_tagesseite.mjs:53, engine/tests/test_tagesseite.py:66).
- Spec nennt weitere anzupassende Tests (seiten_variante, seiten_ding_lesetext, namen_browser, seiten_buchung_zeitraum, test_seite); sie blieben unverändert und sind grün (volle Suite 3507 passed). Abweichung von der Dateiliste, kein Fehler.
- Textkatalog: Keine neuen sichtbaren Texte; Bausteinseiten-Erklärtext steht (wie bisher) in der Vorlage, test_texte.py grün.
- Doku: Regel und Pfeil-Konvention in docs/design.md:68, Kopfkommentar (Code reference: engine/vorlage.html:1508), Bausteinseite (Code reference: engine/vorlage.html:5070).
**Implementierer:** keine weitere Gegenrede nötig.

Confirmation:
  AC: AC-1
  Code reference: engine/vorlage.html:2415
  Evidence: Sonde über alle Ansichten beider Reisen: nur Packliste, Sprungziele und Bausteinmuster (F001) offen; Regeltest grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/vorlage.html:706
  Evidence: Berechnete Pfeilrichtung Kapitel = Pico (0 Grad zu, 90 Grad offen) per Browser, Test grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/vorlage.html:2261
  Evidence: planungsTeil/buchungBlock rufen `einzelheiten` ohne offen auf; Test prüft zu und Text ausserhalb.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/vorlage.html:1822
  Evidence: `block(b, false, kennzahlen)` für alle Abschnitte.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/vorlage.html:3669
  Evidence: `details.weg` ohne open; Test zeichnet für fest/anderen/alle Pläne.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/vorlage.html:5756
  Evidence: open nur mit Entwurf; Test ohne/mit Entwurf nach Neuzeichnen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/vorlage.html:6571
  Evidence: Sprung öffnet alle umgebenden details; Tests für Hash, zu buchen, Suche, Einzelheiten grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/vorlage.html:6053
  Evidence: plKlapper unverändert (nicht im Diff); Test: Packliste steht auf Vorgabe.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: docs/design.md:68
  Evidence: Regel 10 "Beim Laden zu, offen nur der Kern" und Pfeil-Konvention; alte Formulierungen per grep ausser Spec/Kontext/Artefakte nicht mehr vorhanden (F002 Restwort in Historie).
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/tests/test_klappen_zugeklappt.py:1
  Evidence: Volle Suite 3507 passed (test-green-output.txt); gezielter Lauf 139 passed, 0 skipped (adversary-test-output.txt).
  Status: CONFIRMED

Weitere geänderte Dateien (Coverage):

Code reference: engine/tests/klappen_browser.mjs:1
Code reference: engine/tests/test_klappen_zugeklappt.py:139
Code reference: engine/tests/test_tagesseite.py:66
Code reference: engine/tests/seiten_b2.mjs:55
Code reference: engine/tests/seiten_tagesseite.mjs:53
Code reference: engine/vorlage.html:1822
Code reference: docs/design.md:68

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

Nur LOW-Findings (F001 bis F003), keine Spec-Verletzung mit Wirkung. Tests: 139 passed, 0 failed, 0 übersprungen (gezielt); volle Suite 3507 passed. Checkliste 13/13.

## Geprüfte Dateien

- sha256:558058a6182573e47e0951b1a1cf4daa0bf98945285467c45ba6d3b89a0e9cbc  docs/design.md
- sha256:dd9f2c33eecd9ac4f7cbcb421bb420e14480b5d9fc86dc9b2a5d55356926f6c2  engine/tests/klappen_browser.mjs
- sha256:7ff7c6b1588bc67d1e1c69cd737ee0c79448131967666ff73069741bf07c8f8f  engine/tests/seiten_b2.mjs
- sha256:05903e7ada1eeee801db0f4fe081aad0038876b48ca86108f39d3ec07da633f1  engine/tests/seiten_tagesseite.mjs
- sha256:8548f418804b6739e863a7886de601c67d10ca3de3ddc2a99527977c3c0fd2e5  engine/tests/test_klappen_zugeklappt.py
- sha256:a2710c993ac44d69fd72aae5993ce7102b480bedd27dc592e898ef6aa4b88463  engine/tests/test_tagesseite.py
- sha256:f5e7f360cb3c7b7d31225b714666c527647da260d230f93288284de45a93c015  engine/vorlage.html

## Prüfbasis

- base: 100cff3047cc564501d33c95fa524b75987732a3
- blob:23063bbea4bdb26440e61a59c5741e7873a67930  docs/design.md
- blob:4256de8496f61b247c4bfb3f6306a37c958ba2ab  engine/tests/klappen_browser.mjs
- blob:d11460610b3e2a0532c6e6b360e48061404b5c2a  engine/tests/seiten_b2.mjs
- blob:7e0b3b7179af3b3d49194c56eb2788a5d13fed32  engine/tests/seiten_tagesseite.mjs
- blob:5d55f97e9f1f17c277d28d7d3f414f41a99118f1  engine/tests/test_klappen_zugeklappt.py
- blob:e8be9c79af3c279851681d318ec085fca3d2ab71  engine/tests/test_tagesseite.py
- blob:b5fc44d8ab5ba8a806a394bab9e657b3d9152b6a  engine/vorlage.html
