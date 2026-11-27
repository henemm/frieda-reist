# Adversary Dialog — fix-669-bruecke-netzfehler
Spec: docs/specs/fast/fix-669-bruecke-netzfehler.md
Datum: 2026-11-27 17:56

## Checkliste
- [x] AC-1: Ist der Konnektor nicht erreichbar, antwortet die Brücke auf jede Anfrage mit `-32603` und der ID der Anfrage; Benachrichtigungen bleiben ohne Antwort; Exit-Code 0, kein Traceback.
- [x] AC-2: Ein Netzfehler mitten im Lauf ergibt eine Fehlerantwort; die Brücke läuft weiter und leitet nach Wiederkehr des Konnektors wieder weiter.
- [x] AC-3: Nach einem Netzfehler beim Start wird die Kontoprüfung vor der nächsten Weiterleitung nachgeholt; erst danach wird weitergeleitet. Gehört der Zugang einem anderen Konto, bricht die Brücke auch dann ohne Weiterleitung ab. test_bruecke_bricht_nach_netzfehler_beim_start_bei_anderem_konto_ab
- [x] AC-4: Scheitert die Token-Erneuerung, antwortet die Brücke mit `-32603` und läuft weiter; kein Token in der Ausgabe.
- [x] AC-5: Abbruch bei falschem Konto oder Betreiber, Abbruch bei fehlender Ablage oder fehlendem Instanzwert sowie das Erneuern bei Ablauf und bei 401 bleiben unverändert.

## Dialog

### Runde 1
**Adversary:** Testlauf `pytest engine/tests/test_testzugang.py`: 22 passed, 0 failed, 0 uebersprungen. Risiko hoch, daher zwei Runden. Ich pruefe jede AC gegen den Code und probiere Randfaelle mit einem lokalen Fake-Konnektor (Skript im Scratchpad).
Confirmation:
  AC: AC-1
  Code reference: betrieb/testzugang.py:342
  Evidence: Die Startpruefung laeuft ueber `_voruebergehend` (Zeile 323-331), Netzfehler (OSError, HTTPException, Zeile 56) werden abgefangen. Zeilen 352-359: Fehlerantwort -32603 mit id der Anfrage, Benachrichtigung (kein "id") per `continue` ohne Antwort. Schleife endet am stdin-Ende mit return 0. Test test_bruecke_beantwortet_unerreichbaren_konnektor_mit_fehler gruen.
  Status: CONFIRMED
Confirmation:
  AC: AC-2
  Code reference: betrieb/testzugang.py:352
  Evidence: Jede Nachricht geht durch `_voruebergehend(weiterleiten)`; nach Fehler laeuft die Schleife weiter, `senden` versucht es bei der naechsten Anfrage neu. Probe mit abbrechendem Server: RemoteDisconnected wird zu -32603 "Connector unreachable (RemoteDisconnected)", Exit 0.
  Status: CONFIRMED
Confirmation:
  AC: AC-3
  Code reference: betrieb/testzugang.py:316
  Evidence: `weiterleiten` ruft `konto_pruefen`, solange `geprueft` False ist (Zeile 318); `geprueft` wird erst nach bestandener Pruefung gesetzt (Zeile 314). Ein Netzfehler in der nachgeholten Pruefung wird in Zeile 352 abgefangen, Pruefung bleibt ausstehend, es wird nichts weitergeleitet. Fremdes Konto/Betreiber: Abbruch (Zeile 310/313) ist keine ErneuernFehler/Netzfehler, geht bis `main` (Exit 1, nichts weitergeleitet). Beide Tests gruen.
  Status: CONFIRMED
Confirmation:
  AC: AC-4
  Code reference: betrieb/testzugang.py:271
  Evidence: `ErneuernFehler` (Zeile 52) wird nur aus HTTP != 200 beim Erneuern geworfen und in Zeile 330 zu -32603 mit Text "Token refresh failed (HTTP n)..." ohne Token/Pfad. Die Dateisperre wird im `finally` (Zeile 274-275) auch bei Netzfehler/Fehler im Erneuern freigegeben (Dateideskriptor geschlossen).
  Status: CONFIRMED
Confirmation:
  AC: AC-5
  Code reference: betrieb/testzugang.py:253
  Evidence: Fehlende Ablage (ablage_lesen Zeile 141) und fehlender Instanzwert (Zeile 111/118) werfen weiter `Abbruch` vor der Schleife (Zeilen 340-341, ausserhalb von `_voruebergehend`). Erneuern bei Ablauf (Zeile 279) und 401 (Zeile 286) unveraendert. Bestehende Tests 3 bis 6 gruen.
  Status: CONFIRMED

**Implementierer:** (nicht beteiligt, Kontextisolation)

### Runde 2
**Adversary:** Randfaelle.
Finding:
  ID: F001
  Severity: MEDIUM
  Category: edge_case
  Code reference: betrieb/testzugang.py:300
  Description: Antwortet der Konnektor (z. B. ein Proxy vor ihm) bei der Startpruefung oder der nachgeholten Pruefung mit HTTP 5xx, wirft `frage` `Abbruch("Connector check failed")`. Das ist weder Netzfehler noch ErneuernFehler und wird von `_voruebergehend` nicht gefangen. Reproduziert: Fake-Server antwortet 502 auf /mcp, Brücke endet mit Exit 1 und "ERROR: Connector check failed (initialize, HTTP 502)", ohne Antworten.
  Spec requirement: AC-1/AC-3 — Konnektor beim Start nicht erreichbar: Brücke endet nicht, beantwortet Anfragen mit -32603 und holt die Pruefung nach.
  Conflict: Woertlich nennt die Spec nur OSError/HTTPException. Ein 502/503/504 beim Neustart des Dienstes ist aber der typische Ausfall hinter nginx und beendet die Bruecke genau wie vor #669; die Absicht der Spec (Bruecke ueberlebt Ausfaelle des Konnektors) ist hier nicht erfuellt. Fail-closed bleibt gewahrt (nichts wird weitergeleitet).
  Remediation: Fehlerantwort 5xx in `frage` als voruebergehenden Fehler (eigene Ausnahme wie ErneuernFehler) behandeln; 4xx und fehlendes result bei 200 weiter als Abbruch.
Finding:
  ID: F002
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/testzugang.py:335
  Description: Eine Batch-Zeile (JSON-Liste) im Fehlerfall ergibt eine einzelne Fehlerantwort mit id null statt je Element eine Antwort. Reproduziert. MCP 2025-06-18 kennt keine Batches, daher nur theoretisch.
  Spec requirement: AC-1 — jede Anfrage mit ihrer ID.
  Conflict: id null fuer Liste.
  Remediation: Bei Liste je Element mit id eine Fehlerantwort als Liste zurueckgeben.
Finding:
  ID: F003
  Severity: LOW
  Category: edge_case
  Code reference: betrieb/testzugang.py:272
  Description: Antwortet /token beim Erneuern mit 200 und ungueltigem JSON (oder ohne access_token), wirft `json.loads`/`_tokens_uebernehmen` ValueError/KeyError: Traceback, Brücke endet (Exit 1). Reproduziert. Die Stelle bestand schon vor #669.
  Spec requirement: AC-4 — scheitert die Token-Erneuerung, -32603 und weiterlaufen.
  Conflict: Nicht abgedeckter Weg des Scheiterns (Spec nennt nur Abbruch aus `erneuern`). Kein Token-Leck im Traceback beobachtet.
  Remediation: ValueError/KeyError in erneuern als ErneuernFehler melden.
Sonstiges geprueft: Fehlertexte enthalten nur Ausnahmeklasse bzw. HTTP-Status (Zeile 329/271), keine Tokens/Pfade; Netzfehler im Erneuern gibt die Sperre frei; RemoteDisconnected wird gefangen (Probe).
**Implementierer:** (nicht beteiligt)

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`).

## Verdict

VERDICT: AMBIGUOUS
Alle fuenf ACs sind nach Wortlaut bewiesen (22 Tests gruen). F001 (HTTP 5xx bei der Pruefung beendet die Bruecke) ist ein Grenzfall zwischen Spec-Wortlaut und Spec-Absicht; F002/F003 sind LOW. Entscheidung des Product Owners/Tech Leads noetig, ob F001 vor dem Merge behoben wird (Empfehlung: ja, kleine Aenderung).

## Geprüfte Dateien

- sha256:76d5e9e0da8143e59c330c2b916acee1b05d4e04cb7c5529e3cf77b9f56927f3  betrieb/testzugang.py

## Prüfbasis

- base: a68152bbe13e413fabf4418eca6c50ba2a07702b
- blob:e1c275adc42d19639c4b03a9bd4731f2177680ab  betrieb/testzugang.py
