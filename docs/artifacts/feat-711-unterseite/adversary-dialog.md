# Adversary Dialog — feat-711-unterseite
Spec: docs/specs/oberflaeche/funktionsseiten-711-teil3.md
Datum: 2026-11-26

## Checkliste
- [x] AC-1: Unterseite DE/EN vollständig (PROVEN)
- [x] AC-2: Übersicht verlinkt Reiseseite (PROVEN)
- [x] AC-3: Wege (PROVEN)
- [x] AC-4: Galerie im Browser (PROVEN, 4 Browser-Tests grün, keine übersprungen)
- [x] AC-5: Texte und Bilder je Sprache, BILDER genau die Bilder (PROVEN)
- [x] AC-6: Ausnahmelisten nicht länger, alle Tests grün (PROVEN, 225 passed)

## Dialog

### Runde 1
**Adversary:** Fixes aus dem Vorlauf prüfen. F001 (fester Pfad /info/funktionen/karte): Wegetest leitet `ohne` jetzt per next(..., "gibtsnicht") aus einem Bereich ohne Unterseite ab und prüft `/info/funktionen/{ohne}` ohne Schrägstrich auf 404. Route 404 hängt nur an `m[1] not in INFO_UNTERSEITEN` (engine/anmeldung.py:1768). Probe: Kopie im Scratchpad, zweite Unterseite `karte` nur mit INFO_UNTERSEITEN-Eintrag und Texten in de/en: test_unterseite[reiseseite], test_unterseite[karte], test_texte_und_bilder_jeder_unterseite, test_wege_der_funktionsseiten grün, test_texte (98 mit Funktionsseiten) grün. Form gilt.
**Implementierer:** Fix bestätigt durch Test und Probe.

### Runde 2
**Adversary:** F002 (stille Mindestmengen): test_unterseite verlangt nun `bilder` und nummern(tun/wie/rolle/gut) je mindestens 1 (assert in Zeile mit `seite["bilder"] and nummern(...)`); docs/design.md nennt die Regel. `nummern` im Code (engine/anmeldung.py:1571) bricht bei Lücke (tun.1, tun.3) still ab; nicht abgesichert, nur LOW. F003 (Unterschriften): ort/zutun-Unterschriften stimmen mit den Bildern überein (ort-en/de zeigt Hohnstein, Fotos, Lage; zutun zeigt „Zu entscheiden“ / „To decide“). Rest: „reise“ nennt „alle Tage als Zeitachse und die erwogenen Pläne“ und „tag“ nennt „Nacht“; im 390x700-Bild sieht man oben die Karte beziehungsweise Weg und Buchung, Zeitachse der Tage, Pläne und Nacht liegen unterhalb. Das widerspricht der Regel „die Unterschrift beschreibt nur, was das Bild zeigt“ (docs/design.md). Die Texte stammen aber aus dem freigegebenen Entwurf und spiegeln die Unterschriften der Infoseite („Karte, Tage und die erwogenen Pläne“).
**Implementierer:** offen, LOW.

Finding:
  ID: F004
  Severity: LOW
  Category: spec_violation
  Code reference: engine/texte_de.py:3857
  Description: Unterschriften reise und tag nennen Zeitachse aller Tage, erwogene Pläne und Nacht; das Handybild zeigt nur den obersten Bildschirm (Karte, Anfang des Tags), diese Teile liegen darunter.
  Spec requirement: AC-1 — Texte aus dem Katalog; Regel aus design.md „Unterschrift beschreibt nur, was das Bild zeigt“
  Conflict: Unterschrift verspricht mehr als der Bildausschnitt; Wortlaut ist aber freigegeben und deckt sich mit der Seite insgesamt.
  Remediation: Unterschrift kürzen („Der Überblick: Karte und Kopf der Reise.“) oder Bildhöhe/Ansicht anpassen; oder PO bestätigt Wortlaut.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/anmeldung.py:1571
  Description: nummern zählt bis zur ersten Lücke; fehlt in einer Sprache zufällig Nummer 2 einer Liste, entfallen alle folgenden Einträge ohne Fehler.
  Spec requirement: AC-5 — jede Unterseite hat ihre Texte in jeder Sprache
  Conflict: Nur der Paritätstest (test_texte, Schlüsselgleichheit der Sprachen) fängt das ab, nicht der Seitentest; kein Spec-Bruch.
  Remediation: keine nötig; optional Lückenprüfung im Test.

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1592
  Evidence: unterseite() baut alle Abschnitte aus INFO_UNTERSEITEN und Katalog; test_unterseite prüft je Sprache Titel, Zurück-Link, dl.kurz, Galerie, tun, wie (Absätze), Blasen, Rollen, gut, siehe-Links, Abschnittstitel; 225 Tests grün.

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1345
  Evidence: Eintrag reiseseite in INFO_UNTERSEITEN macht die Zeile der Übersicht zum Link (info_zeile); in der Kopie wird auch karte verlinkt; Seite folgt nur ohne Eintrag.

Confirmation:
  AC: AC-3
  Code reference: engine/anmeldung.py:1767
  Evidence: fullmatch, 404 für Bereiche ohne Unterseite, 303 ohne Schrägstrich, POST weiter, 200 bei GET/HEAD; test_wege_der_funktionsseiten prüft Übersicht und reiseseite samt Mein Konto und Unterpfade 404.

Confirmation:
  AC: AC-4
  Code reference: engine/anmeldung.py:1460
  Evidence: info_galerie wird von Infoseite und Unterseite geteilt; test_galerie_im_browser mit /info/ und /info/funktionen/reiseseite/ in de und en: 4 passed, 0 skipped.

Confirmation:
  AC: AC-5
  Code reference: engine/info/erzeugen.py:86
  Evidence: alle_bilder() = INFO_BILDER plus Bilder der Unterseiten, assert set(BILDER)==alle_bilder(); ort-/zutun-de/en.webp 585x1050 WEBP; test_texte_und_bilder_jeder_unterseite grün.

Confirmation:
  AC: AC-6
  Code reference: engine/texte_en.py:3855
  Evidence: neue Texte de/en mit gleichen Schlüsseln; test_texte inkl. Ausnahmelisten und Parität grün, 225 passed 0 failed 0 skipped.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
VERDICT: VERIFIED
Alle sechs AC bewiesen, 225 passed, 0 failed, 0 übersprungen; Fixes F001 bis F003 wirksam; Form einer neuen Unterseite in einer Kopie bestätigt (zweite Unterseite nur mit Eintrag und Texten, alle Tests grün). Offen nur F004 und F005 (LOW, kein Blocker; Wortlaut der Unterschriften ist vom Product Owner freigegeben).

## Geprüfte Dateien

- sha256:10f268646bdea05dd17fd2c6cc88dc918606c46d076db2076a40414c93a67281  engine/anmeldung.py
- sha256:7f8dc2e7ab4dcdeb6d1af8a08be0fba1a0ab5148e814b2697c60243feff9de10  engine/info/erzeugen.py
- sha256:98661681357a5ef1da7556111c43a412e35de39bb909b7c37c784bdc1f296481  engine/texte_de.py
- sha256:f0fabf93e984b2867ac85df6c1071226e3fb3e107bb132efcdc68f10c831a65d  engine/texte_en.py

## Prüfbasis

- base: aad85d07dc66ae7e868ba7190089cd70b9ff3adc
- blob:8c338972cd791fa4a9236a3b5e517e8570093b45  engine/anmeldung.py
- blob:8bafbdf73b4982bb89919954d4abbc26a2c3f34d  engine/info/erzeugen.py
- blob:b1976aba42b664b48877802639303e0a7090b0d7  engine/texte_de.py
- blob:4bb89730525dab0ab95ee59b828595b0c55479dc  engine/texte_en.py
