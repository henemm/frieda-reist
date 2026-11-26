# Adversary Dialog — feat-711-unterwegs-2
Spec: docs/specs/oberflaeche/funktionsseiten-711-unterwegs-2.md
Datum: 2026-11-26 20:28

## Checkliste
- [x] AC-1: `/info/funktionen/zusammenarbeit/` und `/info/funktionen/bilder/` liefern in DE und EN 200 mit allen Abschnitten aus dem Katalog und ihren Bildern (`test_unterseite[zusammenarbeit]`, `test_unterseite[bilder]`, `test_unterseiten_unterwegs`).
- [x] AC-2: Die Übersicht verlinkt beide Bereiche statt „Seite folgt“ (`test_uebersicht_alle_funktionen`).
- [x] AC-3: Texte und Bilder vollständig je Sprache (`test_texte_und_bilder_jeder_unterseite`); Ausnahmelisten in `test_texte.py` nicht länger; englische Fachwörter einheitlich (`test_texte`).
- [x] AC-4: Beispiele stimmen mit der Beispielreise überein (Ida organisiert, Karl wirkt mit und reist ab 14.5.; Frage zum letzten Tag; Karls Wunsch Kirnitzschtalbahn passt zum letzten Tag; 10 Punkte je Person; Frist 13.5.2027 für das Bahnticket; Titelbild Schrammsteine, Blick von der Brandaussicht von Romzig unter CC0; Hohnstein mit drei Bildern); jede Bildunterschrift beschreibt nur, was das Bild in DE und EN zeigt.
- [x] AC-5: Vorhandene Bilder bleiben unverändert im Commit.

## Dialog

### Runde 1
**Adversary:** Tests selbst ausgeführt: `pytest -q -n 4 test_funktionsseiten_711.py test_texte.py test_englisch.py test_englisch_schnittstelle.py` ergibt 115 passed, 0 failed, 0 übersprungen. Bilder (DE und EN) mit dem Read-Werkzeug angesehen; Texte gegen reise.yaml, offene-fragen.md, wuensche.yaml, bilder.yaml, routen.yaml (B-02) und die Quellen docs/funktionen/{zusammenarbeit,bilder}.md abgeglichen.
**Implementierer:** (nicht einsehbar, Kontextisolation)

Confirmation:
  AC: AC-1
  Code reference: engine/anmeldung.py:1364
  Evidence: INFO_UNTERSEITEN enthält "zusammenarbeit" und "bilder" mit Bildern, Gespräch und Verweisen; test_unterseiten_unterwegs und die parametrisierten test_unterseite laufen grün (115 passed).
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:1366
  Evidence: Die Übersicht verlinkt jeden Bereich mit Eintrag in INFO_UNTERSEITEN; test_uebersicht_alle_funktionen grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:4195
  Evidence: Alle Schlüssel info.bereich.zusammenarbeit.* und info.bereich.bilder.* (lead, wo, wer, bild.*, tun, wie, gespraech, rolle, gut) stehen in DE und gleichlautend in EN (engine/texte_en.py:4193); erzeugen.BILDER deckt mitreisende und etappe ab, die webp-Dateien haben die Maße 585x1050 (test_texte_und_bilder_jeder_unterseite grün). test_texte.py ist unverändert (git status), die Ausnahmelisten wurden nicht verlängert. Englisch einheitlich: trip, organiser, contributor, guest, spot, wish board.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/info/erzeugen.py:52
  Evidence: BILDER nennt mitreisende (Ziel .mitreisende) und etappe (E-02) aus beispielreise; Mengengleichheit mit INFO_UNTERSEITEN wird getestet.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/texte_en.py:4196
  Evidence: Beispiele stimmen: Karl mitwirkend ab 14.5. (reise.yaml), 2 offene Fragen (Bild mitreisende zeigt "Offene Fragen 2"), Frage zum letzten Tag (F-01), Wunsch Kirnitzschtalbahn passt zu T-05/V-01, 10 Punkte je Person, Frist 13.5.2027 (B-02), Titelbild Schrammsteine (BI-02), Brandaussicht von Romzig CC0 (BI-08), Hohnstein mit drei Bildern (BI-04 bis BI-06). Bildunterschriften: mitreisende (Ida, Karl ab 14.5., Stand der Vorbereitung, zwei offene Fragen) stimmt; tag (Tag 2 mit Sprechblasen) stimmt; ort (Hauptbild mit Urheber/Lizenz, zwei Vorschaubilder, "3 Bilder") stimmt; etappe (Blick, Urheber Romzig) stimmt; lage (Hotel am Elbufer, Terrassenufer, Urheber, Lizenz, Commons-Seite) stimmt, in DE und EN. Fakten (30 Minuten, 10 Fotos, 12 MB, 60 Bilder, Titelbild löst ab, Archiv) stimmen mit docs/funktionen/bilder.md überein; Rollen, Gast/Mitwirkende:r/Organisator:in und Mitmachen nur angemeldet mit docs/funktionen/zusammenarbeit.md.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/tests/test_funktionsseiten_711.py:217
  Evidence: git status: unter engine/info/ nur erzeugen.py geändert und neu etappe- und mitreisende-{de,en}.webp; keine vorhandene Bilddatei verändert (git ls-files -m engine/info nennt nur erzeugen.py).
  Status: CONFIRMED

Finding:
  ID: F001
  Severity: LOW
  Category: spec_violation
  Code reference: engine/texte_de.py:4234
  Description: Das Beispiel "häng es an Hohnstein" (EN: "attach it to Hohnstein", engine/texte_en.py:4232) weicht von der Quelle docs/funktionen/bilder.md:21 ab ("an den Aufenthalt am zweiten Tag"). Hohnstein ist in der Beispielreise ein Ort (O-03), daher fachlich stimmig.
  Spec requirement: AC-4 — Beispiele stimmen mit Beispielreise und Quelle überein
  Conflict: Nur Wortabweichung von der Quelle, kein Widerspruch zur Beispielreise (BI-04 bis BI-06 hängen an O-03).
  Remediation: Optional angleichen; nicht blockierend.


### Runde 2
**Adversary:** Nachgebohrt: (a) Ausnahmelisten: test_texte.py nicht im git diff. (b) Das Bild "tag" zeigt Tag 2 mit Sprechblasen neben jeder Stelle, passend zur Unterschrift. (c) Gespräch Karl "Frist 13. Mai" vs. B-02: B-02 ist eine Buchung mit Frist 13.5.2027, "Ticket in die App laden"; als Aufgabe im Beispiel stimmig mit Datum und Text. (d) "Pension Burgblick" existiert (routen.yaml:97), das Frühstück ab acht ist ein erfundenes Beispiel im Gespräch, keine Behauptung über die Beispielreise. (e) Kein Randfall in Code gefunden: die Änderungen in anmeldung.py und erzeugen.py sind reine Tabelleneinträge ohne neue Logik; die Weg-Regel INFO_WEG (`[a-z]+`) trifft beide Namen.
**Implementierer:** (nicht einsehbar)


## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`). Keine Verdachtszeilen: die Änderungen sind Tabelleneinträge und Texte, keine neuen Schreibstellen für Felder.

## Verdict

VERDICT: VERIFIED

Tests: 115 passed, 0 failed, 0 übersprungen. Regressions: keine. Checklist: 5/5 bewiesen.
Befund F001 (LOW, nicht blockierend): Beispielsatz "an Hohnstein" statt "an den Aufenthalt am zweiten Tag" wie in der Quelle.
Coverage der Dateien: engine/anmeldung.py:1364, engine/info/erzeugen.py:52, engine/texte_de.py:4195, engine/texte_en.py:4193.

## Geprüfte Dateien

- sha256:1e3f9ff436c223055c07ac55e91383503fcd3c3c8d96646317ead6154e2311d4  engine/anmeldung.py
- sha256:ffdaf26c9d4e13e3a8c41262b5e1b2654bf5256127d203341e38f3e3034a4ede  engine/info/erzeugen.py
- sha256:56215b98096b51c940410a30c159b9f5cdae90ae8b0dc8b932f67f718b56511a  engine/tests/test_funktionsseiten_711.py
- sha256:97010c2df4f66f5a50d73de53bf2c48c7023879bdcccbf38ab3346f8fd6c56b6  engine/texte_de.py
- sha256:880000748772b0fbcded9394a0cd992ec511a33c261d91e014c0346b0eac0fc6  engine/texte_en.py

## Prüfbasis

- base: f40c3133a955fbbd00c021fa1adf9fe554536d7b
- blob:9b52dc698251501e1a4451a08824230bdac8abf9  engine/anmeldung.py
- blob:6b0199c0915ae10ab1f8ccf97ead5dbc67465323  engine/info/erzeugen.py
- blob:51846135271afb44c8eac970aef57aaf8eb133df  engine/tests/test_funktionsseiten_711.py
- blob:521d9ebae362ae4281119bc699d992cdcc0576ff  engine/texte_de.py
- blob:ff8fd2092e1b0bf9f00be6c5950638967861787d  engine/texte_en.py
