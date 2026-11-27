---
entity_id: bitte-nach-entzug-695
type: bugfix
created: 2026-11-27
updated: 2026-11-27
status: draft
---

# Spec: Bitte um „Reisen anlegen“ nach Entzug des Rechts (#695)

- [ ] Approved

## Purpose

Wer das Recht „Reisen anlegen“ wieder verloren hat, kann erneut darum bitten, statt dass Frieda mit einem Fehler
abbricht oder der Knopf auf Mein Konto wirkungslos bleibt.

## Source

- **File:** `engine/konten.py`
- **Identifier:** `reisen_anlegen_anfragen`
- Kontext: `docs/context/fix-695-anfrage-nach-entzug.md`. Bugfix, Variante A.

## Problem und Ursache

Wurde ein Konto freigeschaltet und ihm das Recht `reise_anlegen` danach wieder entzogen, bricht
`reisen_anlegen_anfragen` (Konnektor: `trip_create_request`) mit `KeyError: 'freigeschaltet'` ab.

- `engine/konten.py:985-987`: Hat das Konto das Recht nicht, aber eine Zeile in `anfragen`, wird deren Status
  unverändert zurückgegeben. Nach `freischalten(ja=True)` (`:1003-1005`) steht dort `freigeschaltet`;
  `recht_setzen(..., False)` (`:965`) ändert die Zeile nicht.
- `engine/konnektor.py:2653-2658`: Das Wörterbuch kennt nur `offen`, `schon_erlaubt`, `abgelehnt`.
- `engine/anmeldung.py:1138-1144` zeigt auf Mein Konto bei Status `freigeschaltet` ohne Recht den Knopf; der Klick
  (`:1864-1866`) bekommt `freigeschaltet`, meldet nichts und lädt neu. Der Knopf wirkt nicht.

## Entscheidung (Variante A)

Ist die Bitte eines Kontos als `freigeschaltet` gespeichert, hat das Konto das Recht `reise_anlegen` aber nicht
(mehr), öffnet `reisen_anlegen_anfragen` die Bitte wieder (`status` offen, `erstellt` heute, `entschieden` leer)
und liefert `offen`. Ein Entzug ist keine Ablehnung.
Wiederholt bitten geht damit nicht: Solange die Bitte offen liegt, bleibt sie offen (keine weitere Meldung);
wiedergeöffnet wird nur nach einer erneuten Freischaltung mit anschließendem Entzug.

Folgen ohne weitere Änderung: Der Konnektor antwortet „liegt beim Betreiber“, der Betreiber bekommt die bestehende
Meldung (#687, nur bei `offen`), der Knopf auf Mein Konto wirkt. Eine ausdrückliche Ablehnung bleibt endgültig;
`offen` und `schon_erlaubt` verhalten sich unverändert. Die Funktion liefert damit nur noch die drei bekannten Werte.

Verworfen: Variante B (Konnektor fängt `freigeschaltet` mit eigenem Text ab) lässt den wirkungslosen Knopf stehen
und bräuchte neuen Text in allen Sprachen.

## Scope

- `engine/konten.py`: `reisen_anlegen_anfragen` (~5 LoC), `UPDATE anfragen … WHERE konto = ?` in derselben
  Transaktion wie das Lesen.
- `engine/tests/test_konten.py`, `engine/tests/test_oauth.py`, `engine/tests/test_anmeldung.py`: neue Tests.
- `docs/konten.md`: Zeile 32 um „nach Entzug des Rechts ist eine neue Bitte möglich“ ergänzen.

Kein neuer Text, keine Änderung am Datenformat, keine Umstellung in `neu.py nachziehen`, keine Schnittstelle zu
Instanzen. Geschätzt: 4 Dateien, +5/-0 LoC Code, ~40 LoC Tests.

## Dependencies

| Abhängigkeit | Art | Zweck |
|---|---|---|
| `engine/konnektor.py` (`trip_create_request`) | Aufrufer | Antworttext je Status, unverändert |
| `engine/anmeldung.py` (Mein Konto, `betreiber_melden`) | Aufrufer | Knopf und Meldung an den Betreiber, unverändert |

## Acceptance Criteria

- **AC-1:** Given ein Konto wurde freigeschaltet und danach ist das Recht `reise_anlegen` entzogen / When
  `reisen_anlegen_anfragen(kid)` läuft / Then liefert sie `offen`, und die Bitte steht in `anfragen()` (status offen,
  `erstellt` heute, `entschieden` leer).
- **AC-2:** Given derselbe Zustand / When das Konnektor-Werkzeug `trip_create_request` aufgerufen wird / Then antwortet es
  ohne Abbruch mit dem Text „liegt beim Betreiber“ und ohne Fehlerflag.
- **AC-3:** Given derselbe Zustand / When auf Mein Konto die Aktion `anfragen` ausgelöst wird / Then liegt die Bitte
  offen vor, und die Seite zeigt danach „liegt beim Betreiber“ statt des Knopfs.
- **AC-4:** Given eine abgelehnte Bitte / When das Konto erneut bittet / Then bleibt sie `abgelehnt` (Regression);
  ebenso unverändert: offene Bitte bleibt `offen`, Konto mit Recht liefert `schon_erlaubt`.
- **AC-5:** Given das Wiederöffnen / When die Aktion `anfragen` auf Mein Konto läuft / Then bekommt der Betreiber die
  Meldung `anfrage_reisen` (einmal, wie bei einer ersten Bitte).

## Test Plan (TDD RED zuerst)

- `test_konten.py`: Freischalten, Recht entziehen, bitten -> `offen`, in `anfragen()`; Ablehnung bleibt (bestehender
  Test).
- `test_oauth.py`: gleiche Lage über das Werkzeug, Antwort enthält „liegt beim Betreiber“, kein Fehlerflag.
- `test_anmeldung.py`: Aktion `anfragen` nach Entzug legt Bitte an, Seite ohne Knopf, Meldung `anfrage_reisen`
  (Muster: Test zu #687).
- Gesamtlauf `engine/.venv/bin/python -m pytest -q engine/tests -n 3` grün.

## Definition of Done

- [ ] AC1–AC5 durch Tests belegt, vorher rot (AC1–AC3, AC5), danach grün
- [ ] Gesamtlauf der Tests grün
- [ ] `docs/konten.md` nachgezogen

## Prüfstelle ADR-0001

Berührt keine Grundform der Reise-Ontologie und kein Merkmal, nur die Kontenverwaltung (Kontendatenbank, Inhalt
einer Zeile). Nichts Reise- oder Instanzspezifisches in der Engine.

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** keine (Korrektur innerhalb ADR-0005)

Keine neue ADR: kleine Korrektur innerhalb von ADR-0005 (Konten und Anmeldung); Entzug ≠ Ablehnung ist die
naheliegende Lesart und ändert keine Architektur.

## Changelog

- 2026-11-27: Spec erstellt.
