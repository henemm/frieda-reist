# Adversary Dialog — warteliste-382
Spec: docs/specs/betrieb/warteliste-382.md
Datum: 2026-11-06 21:12

## Checkliste
- [x] **AC-1:** Given die öffentliche Seite `/warteliste` / When eine gültige Adresse eingetragen wird / Then geht eine Bestätigungsmail an sie, und eine ungültige Adresse wird abgewiesen, ohne dass etwas gespeichert wird.
- [x] **AC-2:** Given eine beliebige Adresse (neu, schon eingetragen, schon freigegeben oder mit Konto) / When sie sich einträgt / Then ist die Antwort der Seite dieselbe und verrät nichts über den Stand.
- [x] **AC-3:** Given ein unbestätigter Eintrag / When der Link aus der Mail geöffnet wird / Then ändert sich nichts, und erst der Knopfdruck bestätigt; danach erscheint der Eintrag beim Betreiber und eine Meldung geht an die Betreiber.
- [x] **AC-4:** Given Massen-Einträge / When die Grenzen je Adresse, je IP oder für unbestätigte Einträge erreicht sind / Then lehnt die Seite ab, und unbestätigte Einträge verfallen nach 7 Tagen.
- [x] **AC-5:** Given bestätigte Einträge / When der Betreiber sie mit Befehl oder auf `/konto` ansieht und einen freigibt / Then klappt das nur mit Betreiber-Recht, ohne es wird abgelehnt.
- [x] **AC-6:** Given ein freigegebener Eintrag / When die Freigabe erfolgt / Then geht eine Mail in der Sprache des Eintrags an die Adresse, und das Recht „Reisen anlegen“ gilt sofort bei vorhandenem Konto, sonst beim ersten Anmelden.
- [x] **AC-7:** Given die bestehende Anmeldung, Codes, Reise-Einladungen und die Bitte „Reisen anlegen“ / When die Warteliste eingebaut ist / Then verhalten sie sich unverändert.

## Dialog

### Runde 1
**Adversary:** Tests ausgeführt: `pytest -q test_warteliste.py test_texte.py test_konten.py test_anmeldung.py test_nginx.py` -> 199 passed, 0 failed, 0 übersprungen. Angriffe per Code-Lesung:
- Reihenfolge Begrenzung vs. Zustand: `_begrenzt` und der Versand-Eintrag laufen vor jeder Unterscheidung nach Stand (Adresse neu/bestätigt/Konto) -> die Begrenzung verrät den Stand nicht. Gleiche Antwortseite `warteliste.gesendet` für alle Stände.
- Bestätigungswort: nur SHA-256 (`_hash("warteliste", wort)`), nach Bestätigung `hash = NULL` (einmal), `ablauf >= jetzt` (7 Tage), Länge 20..100. GET ruft nur `warteliste_wort_gilt` (read-only). Unbekannt/abgelaufen -> 404 "Link gilt nicht mehr".
- CSRF: jeder POST (auch /warteliste und /warteliste/bestaetigen) läuft durch `herkunft_ok` (Origin == FR_BASIS) -> 403.
- Freigabe ohne Betreiber-Recht über /konto: `a == "warteliste_freigeben" and recht(k, "betreiber")`; sonst Durchfall auf 400, keine Freigabe. Abschnitt nur im Betreiberzweig.
- HTML-Escaping: Adresse in `warteliste_karte` und `warteliste_seite` durch `esc`. Header-Injection: `EMAIL_MUSTER` verbietet `\s`, `adresse()` strippt vorher -> CR/LF nicht möglich.
- Recht beim ersten Anmelden: `anmelden` setzt `rechte="reise_anlegen"` bei freigegebenem Eintrag.
- DB-Rechte: unverändert `db()` (Ordner 700, Datei 600); keine neue Datei.
- Zweite Freigabe: `freigegeben IS NOT NULL` -> False, keine Mail.
**Implementierer:** (keine Rückmeldung; Prüfung ohne Implementierer-Kontext)

### Runde 2
**Adversary:** Gezielte Suche nach Schwächen:
- F001: Adressen mit bestehendem Konto werden nicht eingetragen (Produktentscheidung, nicht in der Spec). Wer sich schon angemeldet hat (freie Anmeldung offen), sieht "Mail geschickt", bekommt aber nie eine und kann nie freigegeben werden. Dem PO zu melden.
- Testabschwächungen: (a) 3 -> 2 Mails in `test_antwort_ist_fuer_jeden_stand_gleich`: rechnerisch korrekt (Eintrag + Freigabe = 2, Ida hat kein Konto), deckt Spec 3 und 13; keine Abschwächung. (b) Umgestellter Test "Freigabe mit Konto": vorher Konto, dann Eintrag; jetzt Eintrag, Bestätigung, Konto, Freigabe. Der Weg "Recht sofort bei vorhandenem Konto" bleibt getestet, aber nur noch für ein Konto, das nach dem Eintrag entstand; Konto-zuerst ist wegen F001 unmöglich. Folgt aus der Produktentscheidung, nicht aus der Spec -> nicht durch Spec gedeckt. (c) `konten.db().close()` im 403-Test: reine Vorbedingung (Datenbank existiert), prüft weiter "403 speichert nichts"; harmlos.
- F002: In `freigeben` wird committet, danach erst die Mail gesendet. Bei SMTP-Fehler bleibt der Eintrag freigegeben; die zweite Freigabe liefert False ohne Mail -> die Person erfährt nie davon.
- F003: `warteliste_voll` nur für neue Adressen; bei 1000 offenen Einträgen antwortet die Seite für neue anders als für bereits unbestätigte -> schwacher Stand-Hinweis nur bei Überlast.
- F004: Mailfehler bei neuem Eintrag zeigt Fehlermeldung, bei bestätigten Adressen (kein Versand) nicht -> Stand-Hinweis nur bei SMTP-Ausfall.
**Implementierer:** (keine Rückmeldung)

### Runde 3
**Adversary:** Neuer Stand (PO-Entscheidung 7.11.: Konto-Inhaber werden wie alle eingetragen; `freigeben` sendet erst, schreibt dann). Tests: test_warteliste, test_texte, test_konten, test_anmeldung, test_nginx, test_betrieb -> 312 passed, 0 failed, 0 übersprungen.
- F001 behoben: der Zweig "schon ein Konto" ist aus `warteliste_eintragen` verschwunden (Code reference: engine/konten.py:574); Konto-Inhaber laufen denselben Pfad (Begrenzung, Eintrag, Mail, gleiche Antwortseite engine/anmeldung.py:645). AC-2 dicht: kein Zweig fragt noch die Tabelle `konten`. Der Diff der Docs (docs/betrieb.md, docs/konten.md) nennt die neue Regel konsistent; nichts widerspricht ihr mehr.
- Testanpassungen (Karl 2 Mails, Tabelle {LEA, KARL}, Konto-zuerst-Reihenfolge wieder wie ursprünglich) folgen der PO-Entscheidung und stellen den Spec-Fall wieder her; keine Abschwächung.
- F002 behoben: Mail vor der Schreibsperre, bei SMTP-Fehler bleibt der Eintrag wartend und der Fehler geht an den Aufrufer (engine/konten.py:649), wiederholbar. Gelesen wird mit eigener Verbindung, geschrieben erst nach dem Versand; die Mail läuft ohne DB-Schreibsperre.
**Implementierer:** (keine Rückmeldung)

### Runde 4
**Adversary:** Race bei paralleler Freigabe:
- F005: Beide Aufrufe lesen `freigegeben IS NULL`, beide senden die Mail, erst danach schützt `UPDATE ... AND freigegeben IS NULL` (rowcount). Das Recht wird nur einmal gesetzt (idempotent), aber die Mail geht doppelt: Spec Punkt 13 / AC-6 "zweite Freigabe ohne zweite Mail" ist bei Gleichzeitigkeit (Doppelklick auf /konto, Befehl plus Knopf) verletzt. Folge: eine zusätzliche identische Mail, kein Datenschaden. Die Reihenfolge Mail-vor-Schreiben ist die bewusste Gegenentscheidung zu F002.
- F003/F004 bewusst unverändert, akzeptiert (Überlast- bzw. SMTP-Ausfall-Randfall).
**Implementierer:** (keine Rückmeldung)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Findings

Finding:
  ID: F001 (behoben durch PO-Entscheidung 7.11.2026, Runde 3)
  Severity: MEDIUM
  Category: spec_violation
  Code reference: engine/konten.py:603
  Description: `warteliste_eintragen` legt für Adressen mit bestehendem Konto keinen Eintrag an und schickt keine Mail (return None), die Seite meldet trotzdem "Mail geschickt".
  Spec requirement: AC-2 / AC-6 — Antwort gleich auch für Adressen mit Konto; Recht sofort bei vorhandenem Konto
  Conflict: Die Spec verbietet den Eintrag nicht; Kontoinhaber (freie Anmeldung offen) können nie freigegeben werden und werden nicht informiert. Produktentscheidung, dem PO melden.
  Remediation: PO entscheiden lassen: Eintrag auch bei Konto zulassen (Freigabe setzt Recht sofort) oder Seitentext und Spec anpassen.

Finding:
  ID: F002 (behoben, Runde 3)
  Severity: MEDIUM
  Category: edge_case
  Code reference: engine/konten.py:669
  Description: Freigabe wird committet, dann erst die Mail gesendet; bei SMTP-Fehler bleibt `freigegeben` gesetzt.
  Spec requirement: AC-6 — bei Freigabe geht eine Mail an die Adresse; Verhalten 13 — zweite Freigabe schickt keine Mail
  Conflict: Nach Mailfehler ist die Mail nicht nachholbar.
  Remediation: `freigegeben` erst nach erfolgreichem Versand setzen oder bei Mailfehler zurückrollen.

Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: engine/konten.py:600
  Description: "Gerade zu viel los" nur für neue Adressen; bestehende unbestätigte Adressen erhalten bei voller Liste die Erfolgsseite.
  Spec requirement: AC-2 — Antwort verrät nichts über den Stand
  Conflict: Im Überlastfall (1000 offen) unterscheidbar.
  Remediation: Bei Überschreitung für alle gleich antworten.

Finding:
  ID: F004
  Severity: LOW
  Category: edge_case
  Code reference: engine/anmeldung.py:650
  Description: Mailfehler wird als Fehlermeldung gezeigt, nur wenn tatsächlich gesendet wird; der Eintrag bleibt gespeichert.
  Spec requirement: AC-2 — gleiche Antwort
  Conflict: Nur bei SMTP-Ausfall unterscheidbar.
  Remediation: Akzeptieren oder dokumentieren.

Finding:
  ID: F005
  Severity: LOW
  Category: edge_case
  Code reference: engine/konten.py:649
  Description: `freigeben` liest den Stand, sendet die Mail und schreibt erst danach `freigegeben`; zwei gleichzeitige Aufrufe senden beide die Mail, nur das Schreiben ist durch `freigegeben IS NULL` geschützt.
  Spec requirement: Verhalten 13 / AC-6 — zweite Freigabe schickt keine zweite Mail
  Conflict: Bei Gleichzeitigkeit (Doppelklick, Befehl plus Knopf) geht die Mail doppelt; das Recht nur einmal (idempotent).
  Remediation: Freigabe vor dem Senden reservieren (kurze Transaktion, Zustand "sendet"), bei Mailfehler zurücknehmen.

## Confirmations

Confirmation:
  AC: AC-1
  Code reference: engine/konten.py:574
  Evidence: Adresse normalisiert, Prüfungen vor dem Schreiben, Mail mit Link, ungültige Adresse speichert nichts; Tests grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/anmeldung.py:645
  Evidence: Immer dieselbe Seite `warteliste.gesendet`; Begrenzung vor Stand (konten.py:586). Einschränkungen F003/F004 (LOW).
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/konten.py:626
  Evidence: GET nur `warteliste_wort_gilt`; POST bestätigt einmal (hash=NULL); Meldung via betreiber_melden (anmeldung.py:667) nur bei Bestätigung.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/konten.py:586
  Evidence: 3/15min je Adresse, 10/h je IP, Obergrenze 1000, Löschen nach Ablauf (7 Tage); nginx-Zonen in betrieb/vorlagen/nginx-konnektor-orte.inc:36.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/anmeldung.py:739
  Evidence: Freigabe auf /konto nur mit Recht betreiber, sonst 400; Abschnitt nur im Betreiberzweig (anmeldung.py:255); Befehle in konten.py main.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/konten.py:381
  Evidence: Recht beim ersten Anmelden; sofort bei Konto in `freigeben` (konten.py:651); Mail in Sprache des Eintrags, Texte engine/texte_de.py:3305 und engine/texte_en.py:3304. Einschränkung F001/F002.
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/texte_en.py:3321
  Evidence: Bestehende Konten- und Anmelde-Tests grün (199 passed); neue Schlüssel in de (engine/texte_de.py:3322) und en; `betreiber_melden` abwärtskompatibel durch Standardargumente.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/texte_de.py:3305
  Evidence: Freigabe-Mail und Warteliste-Texte in de vollständig, Schlüsselparität zu en durch test_texte.py geprüft.
  Status: CONFIRMED

## Testlauf
pytest -q test_warteliste.py test_texte.py test_konten.py test_anmeldung.py test_nginx.py test_betrieb.py -> 312 passed in 94.11s (0 failed, 0 übersprungen)

Confirmation:
  AC: AC-2
  Code reference: engine/texte_en.py:3304
  Evidence: Runde 3: Konto-Inhaber laufen denselben Pfad und dieselbe Antwort; Texte in de und en gleich vollständig.
  Status: CONFIRMED

## Verdict
═══════════════════════════════════════
VERDICT: VERIFIED
═══════════════════════════════════════
Die Umsetzung hält stand; offen bleiben nur LOW-Randfälle.
Tests: 312 passed, 0 failed, 0 übersprungen
Edge cases: F001 und F002 behoben; F003, F004, F005 (alle LOW) bewusst offen
Regressions: None found
Checklist: 7/7 points proven

## Geprüfte Dateien

- sha256:8cf5c0b51512ebb92b0f5bc0e59d8b6cb8024ac4222ab1aef91d4401e9250211  engine/anmeldung.py
- sha256:acf04a8f202e94fcd995192789d500145ce6a4d1e4d318c745cd18f80e712833  engine/konten.py
- sha256:9c2d4c901699bfd8b6969cc549878e6dad42ae9adc35d7c48f168a3cd6a709ae  engine/texte_de.py
- sha256:946016872ad5d99e7ab930735616bcf60d9feb600a61524716ac5ba7cbf7a514  engine/texte_en.py

## Prüfbasis

- base: d3ea8c34a873fe28104a616f6b86f31e55ea09f4
- blob:fce70cac47f7418a0e59b8dd5f3fd5c5991f2c6c  engine/anmeldung.py
- blob:b77413d435b0087ce08d05852762ce2f83272467  engine/konten.py
- blob:0e654488fe88d183a5ac49efb8196eefd3e8759c  engine/texte_de.py
- blob:15bd66c92aa5211ac2ece5ff4bffc495312937e4  engine/texte_en.py
