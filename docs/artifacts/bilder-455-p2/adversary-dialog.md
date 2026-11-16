# Adversary Dialog — bilder-455-p2
Spec: docs/specs/oberflaeche/bilder-455-p2.md
Datum: 2026-11-16 07:45

## Checkliste
- [x] **AC-1 (AC-11):** Given die Beispielreise / When die Seite in Chromium und WebKit geöffnet wird / Then steht das Titelbild (16:10, Radius `--r-gross`) mit Nennung vor dem Reisekopf, die Tagesliste zeigt ein Mini (44 px) nur bei Tagen mit Kopfbild, und Ort, Etappe, Tag und Unterkunft an der ersten Nacht zeigen das Kopfbild (16:9) mit Bildreihe (72 × 54, „n Bilder“); an anderen Nächten steht nur ein Mini mit Verweis.
- [x] **AC-2 (AC-11):** Given ein Bild im Wissenstext, ein Bildlink im Satz und die Breite 360 px / When die Seite geöffnet und ein Bild angeklickt wird / Then erscheinen beide als Bild mit Unterschrift und Nennung nach V16 ohne Überbreite, und die Großansicht öffnet mit „Ding · i / n“, Pfeil- und Escape-Taste, Fokusrückgabe, Wischen (waagerecht wechselt, nach unten schließt); bis 560 px sind die Pfeile ausgeblendet.
- [x] **AC-3 (AC-12):** Given das Stadtwochenende / When gebaut und geöffnet wird / Then fehlt `bilder` in `daten.json`, es gibt keine Bild-Elemente, keine Bilddateien und kein `#gross`, und die Seite entspricht dem Stand vor P2.
- [x] **AC-4 (AC-13):** Given die neuen Bausteine / When die Karte in Chromium und WebKit geöffnet wird / Then lädt sie ohne CSP-Fehler, und die Großansicht lädt nur von der eigenen Seite (keine Inline-Handler).
- [x] **AC-5 (AC-14):** Given aktive Bilder / When gebaut wird / Then enthält `__DATEIEN__` alle kleinen Fassungen und die großen von Titel- und Kopfbildern, übrige große nicht, und die JPEG-Pipeline unter `medien/` verhält sich wie vorher.
- [x] **AC-6 (AC-14):** Given die Summe der Vorab-Bilddateien liegt über `bilder.offline_mb` / When gebaut wird / Then gibt es eine Warnung mit Katalogtext, und der Bau gelingt.
- [x] **AC-7 (AC-15):** Given die neuen Bausteine und Texte / When die Prüfungen laufen / Then stehen sie in Kopfkommentar, Bausteinseite, `docs/design.md` und allen Sprachdateien, und die Ausnahmelisten in `test_texte.py` sind nicht länger.
- [x] **AC-8 (V24):** Given die Beispielreise / When ihre Bilder geprüft werden / Then sind es echte freie Bilder (CC0, CC BY oder CC BY-SA) mit je einer Zeile in `THIRD_PARTY.md`, mit Titelbild und einer Gruppe von 3 Bildern an einem Ort.

## Dialog

### Runde 1
**Adversary:** Testlauf test_bilder, test_seite_bilder (chromium und webkit), test_pwa, test_texte, test_design, test_seite: 274 passed, 0 failed, 0 übersprungen (docs/artifacts/bilder-455-p2/adversary-test-output.txt). Nachprüfung F001 aus dem ersten Protokoll (docs/artifacts/bilder-455-p2/adversary-dialog-runde1.md): Eigener Bau der Beispielreise mit zusätzlichem Probetext (zwei Bilder im selben Absatz, Bildlink und Bild desselben BI im selben Text, Bild in Listenpunkt, Bild in Tabellenzelle, Alt-Text mit `</figure><figcaption>`). Ergebnis im Abschnitt W-05: 8 figure, 8 schließende figure, 8 figcaption, 8 Knöpfe mit je einem img, maximale Verschachtelungstiefe 1, Ende 0. E-01: 1 figure, 1 Knopf mit img, kein Knopf ohne Bild. Der Alt-Text kommt aus der Bilderliste, nicht aus dem Text, ein Einschleusen ist nicht möglich. Die Neufassung von figuren_setzen (engine/bauen.py, Teilung an fertigen figure vor dem Rückfall) lässt fertige figure unberührt, Bilder in Liste und Tabelle werden im Rückfall gesetzt. Neuer Test test_p2_jedes_bild_im_text_genau_einmal_verpackt (engine/tests/test_bilder.py) wäre ohne Fix rot: er verlangt je BI-01, BI-03 genau einen Knopf mit data-bild, im alten Code gab es zwei verschachtelte. Übernommene Belege der Runde 1: Pfeile bei 360 und 560 px aus, bei 561 und 700 px an (Container-Query, Chromium und WebKit); Stadtwochenende ohne bilder und medien; offline_mb 1 führt zu Hinweis mit Katalogtext und Bau gelingt; __DATEIEN__ ohne große Fassungen von BI-05 und BI-06; XSS in Urheber und lizenz_url maskiert.
**Implementierer:** F001 behoben, Tests ergänzt.

### Runde 2
**Adversary:** Gegenprobe der Abweichungen. Änderung der Tests nach RED: nur das Ziel des Ansprungs, keine Erwartung schwächer; neue Zählungen verschärfen. Aktiver Bildeintrag ohne Datei nur als Hinweis: die Stufe-1-Spec verlangt den Baufehler nur für den Text, dieser bleibt Fehler. Doppelte Skizze BI-01 auf der Tagesseite ist Beispieldatenwahl (LOW, kein Verstoß gegen ADR-0003). Pfeile per Container-Query wirken wie in der Spec. Die Änderung berührt nur bauen.py (figuren_setzen); sw.vorlage.js, vorlage.html, texte_de.py, texte_en.py unverändert zur Runde 1, deren Belege gelten fort.

**Findings**

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/vorlage.html:1478
  Description: Die Beispieldaten zeigen BI-01 als Kopfbild von E-01 und noch einmal im Etappentext.
  Spec requirement: AC-1 — Kopfbild an Ort, Etappe, Tag, Unterkunft
  Conflict: Doppelte Darstellung desselben Bildes auf der Tagesseite; kein Spec-Verstoß, nur Beispielwahl.
  Remediation: Im Beispiel BI-01 nur einmal einsetzen.

**Confirmations**

Confirmation:
  AC: AC-1
  Code reference: engine/vorlage.html:1503
  Evidence: kopfBild setzt Titel- und Kopfbild mit Nennung und Bildreihe; Mini nur mit Kopfbild; Browsertests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/bauen.py:536
  Evidence: figuren_setzen verpackt jedes Textbild genau einmal (8 von 8 im Probe-Bau, keine Verschachtelung); Großansicht und Pfeile bis 560 px aus in vorlage.html:949.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/bauen.py:880
  Evidence: bilder_daten liefert nur mit aktiven Bildern, der Schlüssel fehlt sonst; Stadtwochenende ohne bilder und medien.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/vorlage.html:1542
  Evidence: addEventListener und data-bild, keine Inline-Handler, keine CSP-Meldungen im Test.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/sw.vorlage.js:24
  Evidence: DATEIEN mit allen kleinen und den großen von Titel-, Kopf- und Textbildern; BI-05 und BI-06 gross fehlen.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_de.py:3772
  Evidence: Katalogtext bilder_offline in de, en in engine/texte_en.py:3770; Probe-Bau mit offline_mb 1: Hinweis und Bau gelingt.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/texte_en.py:3771
  Evidence: seite.bild.* in allen Sprachdateien, Bausteine in Kopfkommentar, Bausteinseite und docs/design.md; test_texte und test_design grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/bauen.py:517
  Evidence: THIRD_PARTY.md Zeilen BI-02 bis BI-09 (CC0, CC BY-SA), Titelbild und Gruppe BI-04 bis BI-06; Nennung als Daten aus nennung_daten.
  Status: CONFIRMED

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hat die Gegenprobe bestanden; F001 ist behoben.
Tests: 274 passed, 0 failed, 0 übersprungen
Edge cases: alle geprüft, keine gebrochen (F002 nur LOW, Beispielwahl)
Regressions: keine gefunden
Checklist: 8/8 points proven

## Geprüfte Dateien

- sha256:3e2c9c6e7bf5ed61bd7105c7b82e9d950d28c9be3623068f4bb4937945032146  engine/bauen.py
- sha256:dbe43cdbe310aea5bf2a3e4eb1350546ae3ea11a821fc9bd5586c63e01c6b91b  engine/sw.vorlage.js
- sha256:5ac9db1c9621145901b4571440cccd91f80f79e45ff534bd209ca7cc452eaa6e  engine/texte_de.py
- sha256:a8244cd7638634f91380f5853d9682fee92659096aef162d45ab376b1f51fdd9  engine/texte_en.py
- sha256:cae80cdf6c0f2243919b2ac282de3cf8d5b9d7e287b8b7c3e9ac29c4695261d3  engine/vorlage.html

## Prüfbasis

- base: 6206fd722b84876c771d6bce1aeb249b21b2bab6
- blob:97c627bf4d10a8ff414081332935ce445dcc7eba  engine/bauen.py
- blob:e951662c9249cdf68bf07bfde808ce96d6fe2f15  engine/sw.vorlage.js
- blob:9e5f7160463f56fbcb2106c3aa345efd56f64920  engine/texte_de.py
- blob:d00717ee8aa094f4e74c545817f7642b762f3245  engine/texte_en.py
- blob:98d2e6f93ef215756fcf4ce49d7f72de575a37ed  engine/vorlage.html
