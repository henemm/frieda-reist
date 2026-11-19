# Adversary Dialog — fix-631-warteliste-push
Spec: docs/specs/betrieb/warteliste-push-631.md
Datum: 2026-11-19 15:58

## Checkliste
- [x] **AC-1 (Warteliste, Push):** Gegeben ein Betreiber-Konto Ida mit Gerät und Gruppe `rueckmeldungen` an, ein erster Lauf hat den Stand gemerkt, wenn danach eine Meldung `anfrage_warteliste` mit `an = [Idas Kennung]` in `neu/meldungen.jsonl` steht und `lauf` läuft, dann steht genau eine Nachricht in der Warteschlange (`reise = ""`, `art = "meldung"`), und `zustellen` schickt sie an Idas Gerät.
- [x] **AC-2 (Reisen anlegen, Push):** Gegeben dieselbe Lage, wenn eine Meldung `anfrage_reisen` ankommt, dann geht ebenso genau eine Nachricht an Idas Gerät; ein zweiter Betreiber Karl mit Gerät bekommt seine eigene.
- [x] **AC-3 (Titel und Ziel):** Gegeben eine zugestellte Nachricht ohne Reise, dann ist der Titel `push.titel_ohne_reise` in der Sprache des Kontos (de und en), die URL ist `<basis>/konto#freischalten` bei `anfrage_*` und `<basis>/konto#meldungen` bei `neue_reise` und `loeschung`, und der `tag` ist `frieda-konto`; die Nachricht ist nicht leer betitelt und zeigt nicht auf `#reise`.
- [x] **AC-4 (Ruhezeit):** Gegeben Idas Uhr liegt in ihrer Ruhezeit, dann bleibt die Nachricht in der Warteschlange (`warten` zählt sie), und nach dem Ende der Ruhezeit kommt sie als eine Nachricht.
- [x] **AC-5 (Gruppe aus):** Gegeben Ida hat die Gruppe `rueckmeldungen` für Push ausgeschaltet, dann entsteht keine Nachricht in der Warteschlange; ohne Gerät ebenso keine.
- [x] **AC-6 (Mail täglich):** Gegeben Ida hat die Mail der Gruppe `rueckmeldungen` auf `taeglich`, wenn eine Meldung ohne Reise ankommt und `zusammenfassungen` nach `ZUSAMMENFASSUNG_UM` läuft, dann enthält die Mail den Text unter der Überschrift `push.mail.zusammenfassung.ohne_reise` (nicht unter dem Titel einer Reise) und, mit gesetzter Basisadresse, den Link auf Mein Konto; mit Mail `nie` fehlt der Eintrag. Auch ohne Gerät erreicht der Eintrag die Zusammenfassung.
- [x] **AC-7 (Erster Lauf nur merken):** Gegeben es liegen schon Meldungen in `neu/` und der Dienst hat noch keinen Stand, wenn der erste Lauf geschieht, dann entsteht keine Nachricht und kein Eintrag für die Zusammenfassung; nur Meldungen danach kommen an.
- [x] **AC-8 (Kein Doppelversand):** Gegeben eine Meldung wurde gesammelt, wenn `lauf` ein zweites und drittes Mal ohne neue Meldung läuft, dann entsteht keine weitere Nachricht und kein weiterer Eintrag in der Zusammenfassung; zwei Meldungen in derselben Sekunde gehen beide durch (Verhalten von `neue`).
- [x] **AC-9 (Empfänger):** Gegeben eine Meldung mit `an` = [Kennung eines gesperrten Kontos, Kennung eines unbekannten Kontos, ein Name als Rückfall, Idas Kennung], dann entsteht genau eine Nachricht, nämlich an Ida; die anderen werden ohne Fehler übersprungen.
- [x] **AC-10 (Gleicher Weg):** Gegeben Meldungen der Arten `neue_reise` (mit Kennung) und `loeschung` in `neu/`, dann werden sie wie `anfrage_*` in der Gruppe `rueckmeldungen` vorgemerkt (gleiche Einstellungen, gleiche Ruhezeit, gleicher Titel), mit Ziel `meldungen`; eine `neue_reise` mit Namen statt Kennung erzeugt nichts.
- [x] **AC-11 (Sprache des Empfängers):** Gegeben eine Meldung mit Textteilen (`t`) und zwei Betreiber, einer deutsch, einer englisch, dann ist der Text jeder Nachricht in der Sprache ihres Empfängers; ohne Teile gilt der gespeicherte Text.
- [x] **AC-12 (Nichts Weiteres ändert sich):** Die bestehenden Tests in `engine/tests/test_push.py` bleiben unverändert grün; Reisemeldungen, Rückmeldungen, Aufgaben, Versionen und `mail_rueckfall` verhalten sich wie vorher; `betrieb/deploy.sh` und `neu.py` bleiben unverändert.
- [x] **AC-13 (Texte vollständig):** Beide neuen Schlüssel stehen in `texte_de.py` und `texte_en.py`; `test_texte.py` (Parität, Platzhalter, Literal-Test, Ausnahmelisten, Pseudo-Sprache) bleibt grün; im Code stehen keine deutschen Literale.
- [x] **AC-14 (nach Auslieferung, hier nicht prüfbar) (Abnahme auf der Instanz):** Nach dem Ausliefern, nur mit einem Testkonto der Instanz und nie an echten Reisen: Eine Probe-Bestätigung auf der Warteliste und eine Bitte „Reisen anlegen“ lösen je einen Push beim Betreiber-Gerät aus (Klick öffnet Mein Konto); Ergebnis als Kommentar in #631.

## Dialog

### Runde 1
**Adversary:** Alle Behauptungen am Code gegengelesen und Tests gelaufen (adversary-test-output.txt: 133 passed, 0 failed, 0 übersprungen; kompletter Lauf laut test-green-output.txt 3343 passed).

Confirmation:
  AC: AC-1, AC-2, AC-10
  Code reference: engine/push.py:310
  Evidence: sammeln_ohne_reise liest rm.ordner_neu()/meldungen.jsonl, neue(..., "meldungen:_neu"), reiht je Empfänger mit reise "" und kategorie("meldung", m) ein; sammeln() zählt es mit. Alle Arten gehen denselben Weg, nur das Ziel unterscheidet (anfrage_* -> freischalten, sonst meldungen).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/push.py:366
  Evidence: nachricht() mit leerer Reise liefert Titel push.titel_ohne_reise, URL basis+/konto#ziel (ohne Basis nur /konto#..), tag frieda-konto; mehrere Einträge -> push.mehrere mit Ziel meldungen.
  Status: CONFIRMED

Confirmation:
  AC: AC-4, AC-5
  Code reference: engine/push.py:409
  Evidence: zustellen gruppiert je reise (""), Ruhezeit zählt in warten; einreihen (Z. 232) prüft Gruppe und Abos, sonst keine Zeile.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/push.py:587
  Evidence: sammeln_fuer_mail nimmt ohne Reise die Vorgabe meldekanal (enthält mail laut engine/reise.py:53); einreihen ruft es vor der Geräteprüfung auf, daher auch ohne Gerät; Überschrift in zusammenfassungen (Z. 625 bis 627) aus Katalog, Link nur mit Basisadresse.
  Status: CONFIRMED

Confirmation:
  AC: AC-7, AC-8
  Code reference: engine/push.py:175
  Evidence: neue() merkt beim ersten Lauf nur; bei fehlender Ablage wird [] übergeben, Stand mit bis="" gesetzt, spätere Meldungen zählen. Stand mit ids derselben Sekunde verhindert Doppelversand und Verlust. Schlüssel meldungen:_neu kollidiert nicht mit Reisen (REISE_MUSTER lässt keinen führenden Unterstrich zu, engine/rueckmeldungen.py:102).
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/push.py:321
  Evidence: dict.fromkeys dedupliziert an; konten.konto(kid) None (Name, Unbekannt) oder gesperrt wird übersprungen, keine Ausnahme. an als Text statt Liste iteriert Zeichen, findet keine Konten, kein Fehler.
  Status: CONFIRMED

Confirmation:
  AC: AC-11
  Code reference: engine/push.py:324
  Evidence: rm.meldung_text_in(m, sprache_von(kid)) or m["text"], je Empfänger.
  Status: CONFIRMED

Confirmation:
  AC: AC-12
  Code reference: engine/push.py:587
  Evidence: Der Reisenzweig in nachricht, zusammenfassungen und sammeln_fuer_mail ist für nicht leere Reise unverändert (Diff gelesen); deploy.sh und neu.py ohne Änderung; bestehende Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/texte_de.py:3321
  Evidence: Beide Schlüssel in de (Z. 3321 und 3322), im Code keine deutschen Literale; test_texte.py im Lauf grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-13
  Code reference: engine/texte_en.py:3320
  Evidence: push.titel_ohne_reise und push.mail.zusammenfassung.ohne_reise vorhanden, gleiche Platzhalter (keine).
  Status: CONFIRMED

**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Gegenprobe zu Randfällen und Regression.
- Erster Lauf ohne Ablage, später Ablage mit Meldung: neue() setzt Stand mit bis="", danach zählt die Meldung (erstellt > ""). Kein Altes nachgeschickt, keine Lücke.
- Mehrere Meldungen in einem Lauf: je Eintrag eine Zeile, zustellen bündelt zu einer Nachricht mit Ziel meldungen.
- Keine Basisadresse: URL /konto#ziel (nicht leer), Mail ohne Link.
- Nach Auslieferung: AC-14 (Abnahme auf der Instanz) ist erwartungsgemäß offen, kein Defekt.

Finding:
  ID: F001
  Severity: LOW
  Category: edge_case
  Code reference: engine/push.py:626
  Description: Der Link in der Zusammenfassung zeigt immer auf #meldungen, auch bei Anfragen (Push zeigt auf #freischalten).
  Spec requirement: AC-6 — Link auf Mein Konto (Ziel nicht festgelegt)
  Conflict: Kein Verstoß, nur Inkonsistenz zum Push-Ziel.
  Remediation: Optional ignorieren.

Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: engine/texte_de.py:3318
  Description: Der Betreff der Zusammenfassung lautet weiter "Neuigkeiten aus deinen Reisen", auch wenn nur Meldungen ohne Reise drin stehen.
  Spec requirement: AC-6 — nur Überschrift im Text gefordert
  Conflict: Kein Verstoß, kosmetisch (Leser sind Betreiber).
  Remediation: Optional ignorieren.

**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Tests: 133 passed (test_push und test_texte), 0 failed, 0 übersprungen; Gesamtlauf 3343 passed
Edge cases: geprüft, keine Defekte; zwei LOW-Hinweise (F001, F002)
Regressions: None found
Checklist: 13/13 proven, AC-14 nach Auslieferung

## Geprüfte Dateien

- sha256:ae6cf122d7c760857f53a285def0ee730c4ba2113edae07a571853727fecc808  engine/push.py
- sha256:c8037bdbe6e3960c9d566b6e79f01aba9f27e207f21ef153b6eef01d5695b739  engine/texte_de.py
- sha256:7cf58d498cc4e566eb1926648cafeacb03ba1845df9971d6f6a2ca38b2715693  engine/texte_en.py

## Prüfbasis

- base: f44ecf3ed17bbd6dc0becc8a5d57db2c5d96c7a5
- blob:6e9807d7b0c68206ec1251d7f16c223fa015c89f  engine/push.py
- blob:2d2fa06c4f50f5ea8ee564919d0de90e702e337f  engine/texte_de.py
- blob:c50c958823239f19252ce5afbbc1cb818340c89c  engine/texte_en.py

## Geprüfte Dateien

- sha256:ae6cf122d7c760857f53a285def0ee730c4ba2113edae07a571853727fecc808  engine/push.py
- sha256:c8037bdbe6e3960c9d566b6e79f01aba9f27e207f21ef153b6eef01d5695b739  engine/texte_de.py
- sha256:7cf58d498cc4e566eb1926648cafeacb03ba1845df9971d6f6a2ca38b2715693  engine/texte_en.py

## Prüfbasis

- base: f44ecf3ed17bbd6dc0becc8a5d57db2c5d96c7a5
- blob:6e9807d7b0c68206ec1251d7f16c223fa015c89f  engine/push.py
- blob:2d2fa06c4f50f5ea8ee564919d0de90e702e337f  engine/texte_de.py
- blob:c50c958823239f19252ce5afbbc1cb818340c89c  engine/texte_en.py

## Geprüfte Dateien

- sha256:ae6cf122d7c760857f53a285def0ee730c4ba2113edae07a571853727fecc808  engine/push.py
- sha256:c8037bdbe6e3960c9d566b6e79f01aba9f27e207f21ef153b6eef01d5695b739  engine/texte_de.py
- sha256:7cf58d498cc4e566eb1926648cafeacb03ba1845df9971d6f6a2ca38b2715693  engine/texte_en.py

## Prüfbasis

- base: f44ecf3ed17bbd6dc0becc8a5d57db2c5d96c7a5
- blob:6e9807d7b0c68206ec1251d7f16c223fa015c89f  engine/push.py
- blob:2d2fa06c4f50f5ea8ee564919d0de90e702e337f  engine/texte_de.py
- blob:c50c958823239f19252ce5afbbc1cb818340c89c  engine/texte_en.py
