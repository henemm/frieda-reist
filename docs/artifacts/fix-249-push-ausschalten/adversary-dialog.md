# Adversary Dialog — fix-249-push-ausschalten
Spec: docs/specs/fast/fix-249-push-ausschalten.md
Datum: 2026-11-02 16:58

## Checkliste

1. Platz `<div id="push-geraet-aus" hidden></div>` vor `push_aus`, genau einmal, auch ohne Gerät: PROVEN
2. konto.js an: Zustand + Hinweis in #push-geraet, Knopf in #push-geraet-aus: PROVEN
3. Alle anderen Zweige: #push-geraet-aus leer und hidden (auch an -> aus Fehlerpfad): PROVEN
4. Text aus_wo in de/en, PUSH_GERAET_TEXTE, Ausnahmelisten unverändert: PROVEN
5. Unverändertes Verhalten (push_an, push_ab, fertig, CSP): PROVEN
6. Doku (design.md, Kopfkommentar konto.js, Docstring push_karte): PROVEN

## Dialog

### Runde 1
**Adversary:** Zielt auf Punkt 1, 2, 4. Test `engine/tests/test_push.py` + `test_texte.py` gezielt gelaufen: 96 passed (adversary-test-output.txt). Prüfe, ob der Platz wirklich in `<details>` vor push_aus liegt und nur einmal vorkommt, und ob aus_wo bei data-texte ankommt.

Confirmation:
  AC: Punkt 1
  Code reference: engine/anmeldung.py:350
  Evidence: `+ '<div id="push-geraet-aus" hidden></div>' + aus` steht zwischen Formular und `aus` (push_aus) innerhalb der Einstellungen; unbedingt erzeugt, also auch ohne Gerät; Test prüft Reihenfolge, Einmaligkeit und Fall ohne Abo.
  Status: CONFIRMED

Confirmation:
  AC: Punkt 4
  Code reference: engine/anmeldung.py:311
  Evidence: "aus_wo" in PUSH_GERAET_TEXTE; push_geraet() liefert alle PUSH_GERAET_TEXTE per data-texte (Test liest aus_wo aus dem Attribut). test_texte.py im Diff unverändert, Lauf grün.
  Status: CONFIRMED

Confirmation:
  AC: Punkt 4 (de)
  Code reference: engine/texte_de.py:2839
  Evidence: `konto.push.geraet.aus_wo` = „Ausschalten unter ‚Konfigurieren‘.“
  Status: CONFIRMED

Confirmation:
  AC: Punkt 4 (en)
  Code reference: engine/texte_en.py:2839
  Evidence: `konto.push.geraet.aus_wo` = „Switch off under “Configure”.“ ; Texttest (Vollständigkeit je Sprache) grün.
  Status: CONFIRMED

**Implementierer:** (nicht beteiligt; Kontext isoliert)

### Runde 2
**Adversary:** Zielt auf Punkt 2, 3, 5 per Code-Lektüre (Push im Testbrowser nicht abonnierbar). Angriffe: (a) Zustandsleck: darstellen() wird nach Fehler erneut gerufen; bleibt ein alter Knopf stehen? (b) Zweige ohne Push/gesperrt/ohne Schlüssel/iOS; (c) doppelter push_an; (d) Umbenennung a -> dieses in ausschalten().

Confirmation:
  AC: Punkt 3
  Code reference: engine/app/konto.js:115
  Evidence: `ausZeigen()` ist die erste Anweisung von darstellen() vor allen Zweigen; replaceChildren() leert, hidden = true. Damit sind kein-Push, iOS-Schritte, kein Schlüssel, denied, nicht aus-geschaltet-Zweig sowie der Fehlerpfad (ausschalten -> catch -> darstellen(t("fehler")), Z.110) sauber: der Knopf wird geleert und im an-Zweig neu erzeugt, wenn das Abo noch besteht. Kein veralteter Handler.
  Status: CONFIRMED

Confirmation:
  AC: Punkt 2
  Code reference: engine/app/konto.js:131
  Evidence: `ausZeigen(aus)` füllt #push-geraet-aus mit dem neutralen Knopf (Handler ausschalten, Z.130); `zeigen(...status, p.aktiv(an), satz(aus_wo,"klein"))` enthält keinen Knopf. ausOrt-Null-Schutz (Z.57) verhindert Absturz, falls der Platz fehlt.
  Status: CONFIRMED

Confirmation:
  AC: Punkt 5
  Code reference: engine/app/konto.js:102
  Evidence: ausschalten(): push_ab -> unsubscribe -> fertig("aus") (Z.82 location.replace ?push=…#push) unverändert, nur Variable umbenannt (a -> dieses, keine Kollision mit dem a im darstellen-Zweig). einschalten/push_an-Auffrischen (Z.128) unverändert; Datei bleibt externes Skript, kein Inline-Skript.
  Status: CONFIRMED

Confirmation:
  AC: Punkt 6
  Code reference: engine/anmeldung.py:326
  Evidence: Docstring push_karte beschreibt Platz push-geraet-aus, Position, Skriptfüllung und leer ohne Skript; Kopfkommentar konto.js Z.5-6 und design.md Baustein pushSchalter (Diff) beschreiben dasselbe.
  Status: CONFIRMED

Beobachtung (kein Befund): Bei einem Fehler im Ausschalten erscheint die Fehlermeldung in der Karte oben, während der Knopf im eingeklappten „Konfigurieren“ liegt; funktional korrekt, Wiederholung möglich. Ebenso zeigt der Hinweis „unter Konfigurieren“ auf eine Stelle, die beim ersten Mal zugeklappt ist; so von der Spec gewählt.

Frühe-Einigkeits-Skepsis: Jeder Punkt wurde am Code und mit eigenem Testlauf belegt, nicht nur an der Aussage des Implementierers. Keine Findings.

**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
**VERIFIED**

## Geprüfte Dateien

- sha256:dd9547dfd651dfebba04e7da2d336057885cf48e62d745d59524850fa6fa8d37  engine/anmeldung.py
- sha256:a9572d179677a769049ccc6b712589502bf102d5967c7da9bb0c325ab3621af9  engine/app/konto.js
- sha256:f40090970ec5de25da8a5d9ddb63c048ba182a30763f86b23203931067e84a2c  engine/texte_de.py
- sha256:a996c5bb1dc3db39ee4caaa8fe151d5e5df6fd361af4fd6bbbe58cbfc4f10202  engine/texte_en.py

## Prüfbasis

- base: 74a2d29f35c2834d8dc6ba7a7dd6e6597c6e9d2e
- blob:baf31a59798462fd9aa16b357ad5ad89df402c50  engine/anmeldung.py
- blob:2b76779c09dc0861b36e27d9b1f3cd03d45ba816  engine/app/konto.js
- blob:613be3664bf9e53e441fc35d66e1f4d785d27e4d  engine/texte_de.py
- blob:a125d07080059f30921709f7d44424c55b4887b7  engine/texte_en.py
