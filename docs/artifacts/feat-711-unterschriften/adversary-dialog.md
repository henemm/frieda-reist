# Adversary Dialog — feat-711-unterschriften
Spec: docs/specs/oberflaeche/funktionsseiten-711-unterschriften.md
Datum: 2026-11-26 21:24

## Checkliste
- [x] AC-1: `info.bereich.reiseseite.bild.reise` und `info.bild.reise` nennen in DE und EN weder die Zeitachse der Tage noch die erwogenen Pläne, sondern Zähler, Anreise und Karte (`test_unterschriften_nur_das_sichtbare`).
- [x] AC-2: `info.bereich.reiseseite.bild.tag` und `info.bild.tag` nennen in DE und EN weder Nacht noch „jede Angabe“, sondern die Zeitleiste mit S-Bahn, Quelle und Buchung (`test_unterschriften_nur_das_sichtbare`).
- [x] AC-3: `info.bereich.betrieb.gespraech.2` nennt „höchstens zwei Minuten“ (DE) und „two minutes“ (EN) (`test_betrieb_nennt_das_ziel_der_quelle`).
- [x] AC-4: Texte vollständig, Fachwörter einheitlich (`test_texte`); Bilder unverändert.

## Dialog

### Runde 1
**Adversary:** Bilder per PIL nach PNG gewandelt und angesehen (reise-de/en, tag-de/en, je 585x1050). Wort fuer Wort verglichen.
Ueberblick: Titel "Beispielreise - Malerweg in vier Tagen", Zeitraum 13.-16.5.2027, Zaehler "noch 185 Tage"/"185 days to go", "Anreise Do 13.5.", Karte mit Dresden, Stadt Wehlen, Bastei, Hohnstein, Marken 2 und 3, unten Leiste mit sechs Reitern. Unterschrift (`info.bereich.reiseseite.bild.reise`): Titel, Zeitraum, Zaehler, Anreise, Karte mit Dresden und den ersten Wandertagen, Leiste mit Reitern: alles sichtbar, nichts erfunden. Keine Zeitachse, keine erwogenen Plaene. `info.bild.reise` (Zaehler, Anreise, Karte): sichtbar.
Tag: "Tag 2 - Fr 14.5.", Plan A / Plan B, "Uebersicht" mit Kurztext, Zeitleiste mit "Start Dresden", S-Bahn Dresden -> Stadt Wehlen, "Bahn ab 08:12 an 08:40", "Quelle: Beispiel; ...", darunter "Buchung" mit Marke "gebucht" (halb von der Leiste verdeckt). Unterschriften nennen genau das; keine Nacht, kein "jede Angabe". EN-Bilder tragen englische Beschriftungen (dep./arr., Source, Booking), EN-Unterschriften passen.
Tests: 119 passed (test_funktionsseiten_711, test_texte, test_englisch). Bilder: git diff HEAD --stat -- engine/info leer, also unveraendert.
**Implementierer:** (nicht beteiligt)

### Runde 2
**Adversary:** Gezielt gesucht nach Ueberversprechen. (a) "ihrer Buchung" ist nur angeschnitten sichtbar: Marke "gebucht" und Preis lugen unter der Leiste hervor, also noch vertretbar. (b) "Karte mit Dresden und den ersten Wandertagen": Marken 2 und 3 sichtbar, vertretbar. (c) `info.bereich.betrieb.gespraech.2`: Quelle (docs/funktionen/selbst-betreiben.md:29, docs/betrieb.md:264) nennt "Ziel" von 2 Minuten, docs/betrieb.md meldet Ueberschreitungen als Warnung und kennt den 5-Minuten-Takt. Der Chat-Text sagt "Nach höchstens zwei Minuten baut der Server ihre Seite" bzw. "Within two minutes at most": als feste Zusage formuliert, die Quelle nennt ein Ziel (F001, LOW). Das Ziel misst ausserdem Sichern bis Veroeffentlichung, der Text sagt "baut", gleichbedeutend genug. (d) Test `test_unterschriften_nur_das_sichtbare` prueft nur Negativwoerter und je ein Positivwort; er faengt Ueberversprechen mit anderen Woertern nicht (F002, LOW), die Texte selbst sind aber korrekt.
**Implementierer:** (nicht beteiligt)

## Findings

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/texte_de.py:4400
  Description: Antwort sagt "Nach höchstens zwei Minuten baut der Server ihre Seite" als feste Zusage; EN engine/texte_en.py:4398 ebenso ("Within two minutes at most").
  Spec requirement: AC-3 — nennt das Ziel "höchstens zwei Minuten" der Quelle
  Conflict: Quelle nennt ein Ziel, keine Garantie (docs/betrieb.md:264 warnt bei Ueberschreitung; Timer-Fallback 5 Minuten). AC-3 ist woertlich erfuellt, der Ton ist eine Spur zu sicher.
  Remediation: Optional "Ziel: höchstens zwei Minuten" / "usually within two minutes"; nicht blockierend.

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/tests/test_funktionsseiten_711.py:226
  Description: Test prueft Verbotswortliste und je ein Positivwort, nicht den ganzen Bildinhalt.
  Spec requirement: AC-1, AC-2
  Conflict: Kuenftige Ueberversprechen mit anderen Woertern wuerden nicht erkannt.
  Remediation: Nicht noetig fuer diese Etappe.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/texte_de.py:3857
  Evidence: DE-Unterschrift Ueberblick (und engine/texte_de.py:3785) nennt nur Titel, Zeitraum, Zaehler, Anreise, Karte, Reiter; alles im Bild reise-de.webp sichtbar.

Confirmation:
  AC: AC-1
  Code reference: engine/texte_en.py:3855
  Evidence: EN-Unterschrift (und engine/texte_en.py:3783) deckt sich mit reise-en.webp ("185 days to go", Arrival, Enlarge map, Tabs).

Confirmation:
  AC: AC-2
  Code reference: engine/texte_de.py:3858
  Evidence: Tag 2, Plan A/B, Uebersicht, S-Bahn ab Dresden, Quelle, Buchung sichtbar in tag-de.webp; engine/texte_de.py:3786 ebenso; keine Nacht.

Confirmation:
  AC: AC-2
  Code reference: engine/texte_en.py:3856
  Evidence: deckt sich mit tag-en.webp (dep./arr., Source, Booking); engine/texte_en.py:3784 ebenso.

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:4400
  Evidence: "höchstens zwei Minuten"; EN engine/texte_en.py:4398 "two minutes"; test_betrieb_nennt_das_ziel_der_quelle gruen (engine/tests/test_funktionsseiten_711.py:240).

Confirmation:
  AC: AC-4
  Code reference: engine/tests/test_funktionsseiten_711.py:226
  Evidence: 119 passed (test_funktionsseiten_711, test_texte, test_englisch); git diff HEAD --stat -- engine/info leer.

## Herkunft der Vorbedingungen

Kein Sprachprofil konfiguriert (`precondition_origins.default_lang`); die Aenderung schreibt keine Feldwerte, nur Katalogtexte.

## Verdict

VERDICT: VERIFIED
Tests: 119 passed, 0 failed, 0 uebersprungen
Edge cases: Bilder Wort fuer Wort geprueft, nur F001/F002 (LOW)
Regressions: None found
Checklist: 4/4 points proven

## Geprüfte Dateien

- sha256:880982a06ac6c7e3870c86ff3c593b9b9202c9c06fb9728578690324743531f1  engine/tests/test_funktionsseiten_711.py
- sha256:efe385cc119c2e7c4a402d5b20b72cac6555decf96d397b56451bc970c79507c  engine/texte_de.py
- sha256:3b6e4b2973b0feb5b0ca63ae1dacc75755409a3746fe0806cec332c80ab80281  engine/texte_en.py

## Prüfbasis

- base: 7f16f048d54c07e96d938efca174347823019945
- blob:e71ae5922ac457952af116547ee13bc8b370c06f  engine/tests/test_funktionsseiten_711.py
- blob:c21036206162be7b2e3eb4b44b7381d6138d7434  engine/texte_de.py
- blob:f23cd53035e79e485f06477262aafc77ddc403c2  engine/texte_en.py
