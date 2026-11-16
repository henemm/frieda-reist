# Adversary Dialog — bilder-455-p2
Spec: docs/specs/oberflaeche/bilder-455-p2.md
Datum: 2026-11-16 07:02

## Checkliste
- [~] **AC-1 (AC-11):** Titelbild, Mini, Kopfbild, Bildreihe: PROVEN (Tests chromium und webkit grün; Code unten)
- [ ] **AC-2 (AC-11):** Bild im Text und Bildlink im Satz als figure: DISPROVEN (doppelt verschachtelt, F001); Großansicht, Pfeile, Escape: PROVEN
- [x] **AC-3 (AC-12):** Stadtwochenende: PROVEN
- [x] **AC-4 (AC-13):** keine CSP-Fehler, keine Inline-Handler: PROVEN
- [x] **AC-5 (AC-14):** __DATEIEN__: PROVEN
- [x] **AC-6 (AC-14):** Warnung offline_mb: PROVEN
- [x] **AC-7 (AC-15):** Bausteine in allen Stellen: PROVEN
- [x] **AC-8 (V24):** echte freie Bilder, THIRD_PARTY: PROVEN

## Dialog

### Runde 1
**Adversary:** Testlauf test_bilder, test_seite_bilder (chromium und webkit), test_pwa, test_texte, test_design, test_seite: 271 passed, 0 failed, 0 übersprungen (Ausgabe: docs/artifacts/bilder-455-p2/adversary-test-output.txt). Gegenprobe mit eigenem Bau der Beispielreise und Auslesen von daten.json und der Seite im Browser:
- Der Wissenstext enthält für jedes Bild der Liste `<figure><button …><figure><button …><img></button><figcaption>…</figcaption></figure></button><figcaption>…</figcaption></figure>`. Ursache: figuren_setzen wandelt jedes img erst im Absatz (innere Schleife) und danach noch einmal im Rückfall `bild.sub(...)` über den ganzen Text, dort auch die img, die schon in einem figure stehen. Im Browser (HTML-Parser schließt den äußeren Knopf) entstehen zwei figure, zwei figcaption (Bildunterschrift und Nennung doppelt) und ein leerer, fokussierbarer Knopf mit data-bild und aria-label ohne Bild. Die Tests prüfen nur „mindestens ein figure mit Knopf“ und sehen das nicht.
- Stadtwochenende: daten.json ohne `bilder`, kein medien/, Test grün (AC-3).
- XSS: Urheber `<img src=x onerror=alert(1)>&` und lizenz_url mit Anführungszeichen: im Text als `&lt;img…` und `&quot;` maskiert, in daten.json (bilder[].nennung) nur Daten; Seite setzt per el()-Textknoten (bildNennung). Nicht ausnutzbar.
- offline_mb: 1 setzen -> Hinweis mit Katalogtext, „Done“ (AC-6).
- __DATEIEN__: 9 kleine + große von BI-01 (Text), BI-02 (Titel), BI-03 (Text), BI-04, BI-07, BI-08, BI-09; BI-05 und BI-06 große fehlen mit Absicht (AC-5).
- Pfeile: Großansicht bei 360 und 560 px display:none, bei 561 und 700 px block, Chromium und WebKit (Container-Query wirkt wie die Spec verlangt).
- Änderung der Tests nach RED: nur der Ziel-Ansprung (#wissen -> Abschnitt mit data-bild); keine Erwartung schwächer.
**Implementierer:** (nicht beteiligt)

### Runde 2
**Adversary:** Nachgehakt an den gemeldeten Abweichungen.
- Aktiver Bildeintrag ohne Datei nur als Hinweis (bauen.py bilder_daten): bilder-455-stufe1.md fordert den Baufehler nur für den Text (unbekannte Kennung) und für Bildquellen; für Listeneinträge ohne Datei steht dort nichts -> kein Widerspruch, Text mit Verweis darauf bleibt Baufehler (bild_kennung). Akzeptabel.
- Skizze BI-01 doppelt auf der Tagesseite (Kopfbild E-01 und Bild im Etappentext): Die Beispieldaten legen das so an (Bild im Text und zugleich erstes Bild von E-01); ADR-0003 regelt Grundformen, nicht Bilder, der Autor entscheidet. Hinweis LOW (F002), kein Verstoß.
- Etappen-Kopfbild nur am Heimat-Tag (ETAPPE_TAG) und in ansichtAbschnitt: Code geprüft, passt zu V14.
- Schriftgrößen als Tokens: nur Gestaltung, harmlos.
- Fokusrückgabe, Escape, Wischen: Tests grün in beiden Browsern.

**Findings**

Finding:
  ID: F001
  Severity: HIGH
  Category: spec_violation
  Code reference: engine/bauen.py:551
  Description: figuren_setzen läuft nach der Absatzschleife noch einmal über den ganzen Text (`return bild.sub(lambda i: self.figur(i) or i.group(0), h)`), und der Treffer ist auch das img, das figur() eben erst in ein figure gesetzt hat.
  Spec requirement: AC-2 — Bild im Wissenstext und Bildlink im Satz erscheinen als figure mit Unterschrift und Nennung nach V16
  Conflict: Jedes Textbild wird doppelt verpackt (figure > button > figure > button > img, zwei figcaption). Im Browser: zwei Unterschriften mit Nennung, ein leerer Knopf mit data-bild ohne Bild als zusätzlicher Tab-Halt, ein leeres figure. Reproduktion: Beispielreise bauen (engine/bauen.py beispielreise --reisen beispiel/reisen --ziel <Ordner>), in daten.json den Abschnitt W-05 lesen oder die Seite öffnen und `document.querySelectorAll("#main figcaption")` zählen (2 statt 1).
  Remediation: Im Rückfall nur img treffen, die nicht schon in einem figure stehen (z. B. Absatzschleife weglassen und alle img einmal ersetzen, oder bereits gesetzte Figuren vor dem zweiten Durchlauf schützen); Test, der genau ein figure und genau ein figcaption je Textbild verlangt.

Finding:
  ID: F002
  Severity: LOW
  Category: anti_pattern
  Code reference: engine/vorlage.html:1478
  Description: Die Beispieldaten zeigen BI-01 als Kopfbild von E-01 und noch einmal im Etappentext; bildNennung/kopfBild unterscheiden das nicht.
  Spec requirement: AC-1 — Kopfbild an Ort, Etappe, Tag, Unterkunft
  Conflict: Doppelte Darstellung desselben Bildes auf der Tagesseite; kein Spec-Verstoß, nur Beispielwahl.
  Remediation: Im Beispiel BI-01 nur einmal einsetzen oder in den Text-Hinweisen erwähnen.

**Confirmations**

Confirmation:
  AC: AC-1
  Code reference: engine/vorlage.html:1503
  Evidence: kopfBild(id, art) setzt Titelbild (art titel) und Kopfbild mit Nennung und Bildreihe; tagZeile setzt mit-bild und miniEl nur bei vorhandenem Kopfbild; nachtZeile(…, mitBild) Mini nur außerhalb der Heimat. Browsertests chromium und webkit grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/bauen.py:880
  Evidence: bilder_daten nur mit aktiven Bildern, der Schlüssel `bilder` fehlt sonst ganz; die Großansicht wird erst beim Öffnen erzeugt (vorlage.html grossAnsicht). Probe-Bau Stadtwochenende: kein bilder, kein medien/.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/vorlage.html:1542
  Evidence: Großansicht mit addEventListener und data-bild, keine Inline-Handler, Bilder nur von eigener Seite; Tests ohne CSP-Meldung.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/sw.vorlage.js:24
  Evidence: DATEIEN trägt vorab alle kleinen, die großen von Titel-, Kopf- und Textbildern (bauen.py self.spaeter, im_text); eigener Probe-Bau: BI-05/BI-06 gross fehlen, übrige da.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_de.py:3772
  Evidence: bilder_offline mit Katalogtext in de und en (engine/texte_en.py:3770); Probe mit offline_mb 1: Hinweis, Bau gelingt.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/texte_en.py:3771
  Evidence: Schlüssel seite.bild.* in de und en, Bausteine im Kopfkommentar, Bausteinseite und docs/design.md; test_texte und test_design grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: engine/bauen.py:517
  Evidence: THIRD_PARTY.md hat Zeilen BI-02 bis BI-09 (Commons, CC0 / CC BY-SA), Titelbild BI-02, Gruppe BI-04 bis BI-06 an O-03; nennung_daten gibt Urheber, Lizenz, Commons-Seite wieder.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/vorlage.html:949
  Evidence: Teil Großansicht (Zähler „Ding · i / n“, Pfeil- und Escape-Taste, Fokusrückgabe, Wischen) und Pfeile bis 560 px aus (Container-Query, gemessen 360/560 aus, 561/700 an, Chromium und WebKit). Der Teil „figure im Text“ ist durch F001 NICHT bewiesen.
  Status: CONFIRMED (Großansicht); Textfigur siehe F001

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: BROKEN
═══════════════════════════════════════
Finding F001: Bilder im Text (und Bildlink im Satz) werden doppelt zu figure/button/figcaption verpackt; Nennung und Unterschrift erscheinen doppelt, dazu ein leerer fokussierbarer Knopf.
  Severity: HIGH
  Evidence: engine/bauen.py:551
  Reproduction: Beispielreise bauen, Abschnitt W-05 in daten.json lesen oder Seite öffnen; 2 figcaption statt 1.
Tests: 271 passed, 0 failed, 0 übersprungen (die Tests sehen den Fehler nicht)
Edge cases: übrige alle geprüft, nur F001 gebrochen; F002 LOW
Regressions: keine weiteren gefunden
Checklist: 7/8 proven, AC-2 teilweise (Textfigur) disproven

## Geprüfte Dateien

- sha256:a54ea197783b18f87f53cb4d03784634811f256650e0f96401b55a8f86f182cc  engine/bauen.py
- sha256:dbe43cdbe310aea5bf2a3e4eb1350546ae3ea11a821fc9bd5586c63e01c6b91b  engine/sw.vorlage.js
- sha256:5ac9db1c9621145901b4571440cccd91f80f79e45ff534bd209ca7cc452eaa6e  engine/texte_de.py
- sha256:a8244cd7638634f91380f5853d9682fee92659096aef162d45ab376b1f51fdd9  engine/texte_en.py
- sha256:cae80cdf6c0f2243919b2ac282de3cf8d5b9d7e287b8b7c3e9ac29c4695261d3  engine/vorlage.html

## Prüfbasis

- base: 6206fd722b84876c771d6bce1aeb249b21b2bab6
- blob:3fccc9f72137fade652d9fe8b177b85b764dbed8  engine/bauen.py
- blob:e951662c9249cdf68bf07bfde808ce96d6fe2f15  engine/sw.vorlage.js
- blob:9e5f7160463f56fbcb2106c3aa345efd56f64920  engine/texte_de.py
- blob:d00717ee8aa094f4e74c545817f7642b762f3245  engine/texte_en.py
- blob:98d2e6f93ef215756fcf4ce49d7f72de575a37ed  engine/vorlage.html
