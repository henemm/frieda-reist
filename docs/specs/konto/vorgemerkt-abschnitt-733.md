# Spec: Vorgemerkte Reisen als zugeklappter Abschnitt (#733)

Vorgabe des Product Owners vom 27.11.2026, Entwurf mit Beispieldaten gezeigt und freigegeben. Kontext:
`docs/context/feat-733-vorgemerkt-abschnitt.md`.

## Was ändert sich

Auf „Mein Konto“ stehen Reisen, die zum Löschen vorgemerkt sind, nicht mehr oben in „Deine Reisen“. Sie stehen in
einem zugeklappten Abschnitt „Zum Löschen vorgemerkt (n)“ unter der Reiseliste und unter dem Archiv. Aufgeklappt
zeigt er je Reise eine Kachel mit:

- dem Namen der Reise (fett),
- dem Satz „Wird am <Datum mit Zone> endgültig gelöscht.“ (klein), nach Fristende „Wird gerade endgültig gelöscht.“,
- nur für Organisator:innen und nur vor Fristende: dem leisen Knopf „Reise zurückholen“ (wie bisher, #730).

Kein neuer Baustein: Abschnitt wie das Archiv (`details.archiv`), Kacheln (`.kachel`), `.klein`, Knopf `.leise`.

## Scope

Betroffene Dateien (5):

- `engine/anmeldung.py`: `konto_seite`, `loeschen_block`, Kommentare.
- `engine/texte_de.py`, `engine/texte_en.py`: Titel des Abschnitts und Satz der Kachel ohne Titel; ungenutzte alte
  Schlüssel entfallen; Halbsatz zur Lage in `info.bereich.lebenslauf.wie.5.text`.
- `engine/tests/test_loeschen_reise.py`: Lage und Aufbau.
- `docs/design.md`: Beschreibung von Mein Konto.

## Was sich nicht ändert

Vormerken, Zurückholen, Fristen, Mails und Meldungen; wer den Knopf sieht; Reiseliste und Archiv selbst.

## Acceptance Criteria

- AC-1: Hat ein Konto vorgemerkte Reisen, steht auf „Mein Konto“ ein `<details>` ohne `open` mit dem Titel
  „Zum Löschen vorgemerkt (n)“ (n = Anzahl). Es steht nach der Reiseliste und nach dem Archiv; vor der Reiseliste
  steht nichts zu vorgemerkten Reisen.
- AC-2: Im Abschnitt steht je vorgemerkter Reise eine Kachel mit dem Titel der Reise und dem Löschdatum samt Zone.
- AC-3: Den Knopf „Reise zurückholen“ sehen nur Organisator:innen vor Fristende; Zurückholen wirkt wie bisher.
- AC-4: Ohne vorgemerkte Reisen gibt es den Abschnitt nicht.
- AC-5: Texte in allen Sprachdateien; `test_texte.py` und `test_design.py` grün.

## Test Plan

- Bestehender Test `test_block_oben_knopf_nur_fuer_organisatorin_und_zurueckholen` wird auf die neue Lage umgestellt
  (AC-1 bis AC-3), dazu eine Prüfung mit Archiv und ohne Vorgemerkte (AC-1, AC-4).
- `test_knopf_auch_bei_abgebauter_seite` (#730) bleibt grün.

## Definition of Done

- AC-1 bis AC-5 durch Tests belegt, Gesamtsuite in der CI grün.
- `docs/design.md` und Info-Unterseite nachgezogen.
- Auf `main` ausgeliefert und auf der Instanz an der Kontoseite geprüft.
