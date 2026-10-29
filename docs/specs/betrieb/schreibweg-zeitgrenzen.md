---
entity_id: schreibweg-zeitgrenzen
type: module
created: 2026-10-29
updated: 2026-10-29
status: draft
version: "1.1"
tags: [schreibweg, betrieb, timeout, sperre]
---

# Schreibweg: Zeitgrenzen, Sperre je Reise, Priorität, Ablehnungsgrund (#118–#121)

## Approval

- [ ] Approved

## Purpose

Ein zu langsamer Schreibvorgang soll der Claude-App eine verständliche Meldung geben, statt von nginx mit 504 abgebrochen zu werden, und die Meldung soll sagen, ob eingetragen wurde (#118). Dazu kommen: Sperre und Arbeitskopie je Reise (#119), niedrige Priorität für das Veröffentlichen (#120) und der Ablehnungsgrund im Protokoll (#121).

## Source

- **File:** `engine/schreiben.py`, `betrieb/vorlagen/veroeffentlichen.service`, `betrieb/vorlagen/nginx-konnektor.conf` (nur gelesen)
- **Identifier:** `anwenden_extern`, `sperre_nehmen`, `sperrdatei`, `Schreiber.vorbereiten`, `Schreiber.veroeffentlichen_anstossen`, `anwenden`, `git`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `nginx-konnektor.conf` (`proxy_read_timeout 30s`) | Config | Wartezeit des Konnektors auf die Antwort des Schreibwegs; der Dienst antwortet erst am Ende, daher gilt sie praktisch für die Gesamtdauer eines Vorgangs |
| `instanz.wert("FR_SPERREN")` | Funktion | Ort der Sperrdateien |
| git, flock, nice, ionice | Systemwerkzeuge | Arbeitskopie, Sperre, Priorität |
| `docs/adr/0001-kern.md` | ADR | Prüfstelle; asynchrones Schreiben ist ausdrücklich nicht Teil dieser Spec |

## Scope

- **Affected Files:** `engine/schreiben.py`, `betrieb/vorlagen/veroeffentlichen.service`, `docs/betrieb.md`, `engine/tests/test_schreiben.py`, `engine/tests/test_betrieb.py`
- **Estimated Changes:** ca. +160/-10 LoC (davon etwa +85 schon im Arbeitsbaum; offen: Gesamtfrist, Prozessgruppe, Kennung und Ergebnisprüfung, Dauer-Protokoll, `nice`/`ionice` beim Start)
- **Nicht im Scope:** asynchrone Schreibvorgänge (Vorgangsnummer, Nachfragen). Sie kommen als eigenes Issue und werden vorher an ADR-0001 gemessen.

## Implementation Details

```
Zeitbudget (Sekunden, alles gemessen ab Beginn von anwenden_extern, time.monotonic()):
  ZEIT_SPERRE   = 3    Wartezeit auf die Sperre der Reise (Teil von ZEIT_GESAMT)
  ZEIT_GESAMT   = 25   Sperre + Vorbereiten + Anwenden zusammen
  ZEIT_PRUEFUNG = 3    Reserve NACH ZEIT_GESAMT für die gesamte Ergebnisprüfung (git fetch UND git log zusammen
                       unter dieser einen Frist; ist sie um, gilt "Prüfung nicht möglich")
  Höchstdauer einer Antwort = ZEIT_GESAMT + ZEIT_PRUEFUNG = 28 s (plus Beenden der Prozessgruppe, Millisekunden)
  < proxy_read_timeout 30 s; die restlichen 2 s sind Sicherheitsreserve für Antwort und Übertragung.
  ZEIT_ANWENDEN entfällt (war 150 s, im Arbeitsbaum 20 s); docs/betrieb.md ("Zeitgrenzen und Sperren des
  Schreibwegs") wird auf diese drei Werte umgestellt.

Ablauf:
  1. Sperre der Reise nehmen (nicht blockierend, Frist ZEIT_SPERRE); belegt -> 429.
  2. Vorbereiten: jeder git-Aufruf bekommt als Zeitgrenze den Rest von ZEIT_GESAMT.
     Läuft die Frist hier ab, ist noch nichts angewendet: Meldung "nicht eingetragen" ohne Ergebnisprüfung.
  3. Kennung: pro Vorgang eine kurze Zufallskennung; sie geht als Umgebungsvariable FR_VORGANG an den Anwenden-
     Unterprozess und steht als Zeile "Frieda-Vorgang: <Kennung>" in der Commit-Nachricht des Eintrags.
  4. Anwenden als Unterprozess in eigener Prozessgruppe (start_new_session), Zeitgrenze = Rest von ZEIT_GESAMT.
     Ist der Rest schon aufgebraucht (<= 0), wird der Unterprozess gar nicht gestartet: "nicht eingetragen" wie
     bei Schritt 2. Bei Fristablauf wird die ganze Gruppe beendet (SIGKILL), damit ein darunter laufendes
     git push nicht weiterläuft.
  5. Ergebnisprüfung nach Abbruch im Anwenden: git fetch origin main, dann Suche nach der Kennung in origin/main
     (git log --grep); beides zusammen höchstens ZEIT_PRUEFUNG. Gefunden / nicht gefunden / Prüfung nicht möglich -> Tabelle unten.

Meldungen (ein Wortlaut, alle Abschnitte verweisen hierher):
  | Fall                                  | Code | ok    | Text (fehler bzw. hinweis)                                                                        | Protokoll                              |
  | eingetragen trotz Abbruch             | 200  | true  | "Es hat länger gedauert, ist aber eingetragen."                                                   | Zeit <werkzeug> 504: abgebrochen, eingetragen |
  | nicht eingetragen (Abbruch)           | 504  | false | "Das Schreiben hat zu lange gedauert und ist nicht eingetragen; bitte noch einmal versuchen."      | Zeit <werkzeug> 504: abgebrochen, nicht eingetragen |
  | Prüfung nicht möglich                 | 504  | false | "Das Schreiben hat zu lange gedauert; bitte prüfen, ob es angekommen ist."                         | Zeit <werkzeug> 504: abgebrochen, ungeprüft |
  | Sperre belegt                         | 429  | false | "Bei dieser Reise läuft gerade ein anderer Schreibvorgang; bitte gleich noch einmal versuchen."    | Gesperrt <werkzeug> 429: ...           |
  | abgelehnt                             | 422  | false | Grund der Regel                                                                                   | Abgelehnt <werkzeug> 422: <Grund>      |
  Grund im Protokoll: einzeilig (Whitespace zusammengezogen), höchstens 200 Zeichen.
  Zusätzlich schreibt JEDER Vorgang mit jedem Code (200, 422, 429, 503, 504, 500) genau eine Zeile
  "Fertig <werkzeug> <code> in <Sekunden> s" (Sekunden mit einer Nachkommastelle). <code> ist immer der Code der
  Antwort an den Konnektor; "eingetragen trotz Abbruch" steht also als "Fertig <werkzeug> 200", zusätzlich zur
  Zeile "Zeit <werkzeug> 504: abgebrochen, eingetragen". Grundlage, um die Gesamtfrist
  an echten Dauern zu messen.

Sperre und Arbeitskopie je Reise: <FR_SPERREN>/<instanz>-schreiben-<reise>.lock, Arbeitskopie <arbeit>-<reise>.
Veröffentlichen: veroeffentlichen.service mit Nice=10, IOSchedulingClass=best-effort, IOSchedulingPriority=7;
  der Start aus dem Schreibweg (Popen) ruft das Skript über nice und ionice auf.
```

## Expected Behavior

- **Input:** ein Schreibvorgang (`werkzeug`, `anfrage`) für eine Reise.
- **Output:** 200/422 wie bisher; bei Fristablauf eine der Antworten aus der Meldungstabelle oben. Die Antwort kommt immer vor Ablauf von `proxy_read_timeout` (höchstens 28 s).
- **Side effects:** Protokollzeilen (`journalctl -u <instanz>-schreiben`); je Reise eine Sperrdatei und eine Arbeitskopie; eine Kennungszeile in jeder Commit-Nachricht eines Eintrags; Veröffentlichen läuft mit niedriger Priorität.

## Known Limitations

- Die Ergebnisprüfung braucht ein erreichbares `origin`; ist es das nicht, bleibt es bei „bitte prüfen, ob es angekommen ist“.
- Restrisiko: Wird ein `git push` im Moment der Übertragung beendet, kann der Server den Push noch fertig verarbeiten, nachdem die Prüfung „nicht eingetragen“ gemeldet hat. Wiederholt die App dann, kann ein Eintrag doppelt stehen. Das Fenster ist die Übertragungszeit eines Pushes (Millisekunden bis wenige Sekunden); eine Entdopplung gibt es hier nicht, sie gehört zu den asynchronen Vorgängen.
- Große Reisen mit langem Probebau können die 25 s überschreiten und werden dann abgebrochen; Messwerte fehlen bisher, AC-8 liefert sie ab dem Einsatz.
- Arbeitskopien je Reise brauchen mehr Platz; parallele `git fetch` im selben Repo sind möglich (Push-Konflikte fängt `hochladen` per Rebase ab).
- Asynchrone Vorgänge (Vorgangsnummer, Nachfragen) wären die vollständige Lösung und bleiben ein eigenes Issue.

## Definition of Done

Fertig ist diese Änderung, wenn:

- [ ] Jede Acceptance Criterion unten ist durch einen automatischen Test belegt
- [ ] Ein zu langsamer Schreibvorgang (auch ein hängendes `git fetch`) gibt dem Konnektor innerhalb von 28 s eine Meldung aus der Meldungstabelle, und das Protokoll nennt Werkzeug und Grund
- [ ] Nach einem Abbruch sagt die Meldung, ob der Eintrag angekommen ist (eingetragen / nicht eingetragen), solange `origin` erreichbar ist
- [ ] Das Protokoll zeigt die Dauer jedes Vorgangs, damit die Gesamtfrist an echten Werten geprüft werden kann
- [ ] Zwei Reisen blockieren sich nicht gegenseitig
- [ ] `docs/betrieb.md` beschreibt Zeitgrenzen, Sperren, Meldungen und Priorität
- [ ] Keine bestehende Funktion ist dabei kaputtgegangen (Regressionslauf grün)

## Acceptance Criteria

- **AC-1:** Given die nginx-Vorlage des Konnektors / When die Zeitkonstanten mit `proxy_read_timeout` verglichen werden / Then `ZEIT_GESAMT + ZEIT_PRUEFUNG` ist kleiner als `proxy_read_timeout`, und `ZEIT_SPERRE` ist nicht größer als `ZEIT_GESAMT`
  - Test: `engine/tests/test_schreiben.py::test_zeitgrenzen_liegen_unter_der_des_konnektors`
- **AC-2:** Given ein Anwenden-Unterprozess, der die Frist überschreitet, und `origin` nicht erreichbar für die Prüfung / When `anwenden_extern` läuft / Then Antwort 504 im Fall „Prüfung nicht möglich“ der Meldungstabelle (mit dem dortigen Text) und die Protokollzeile `Zeit <werkzeug> 504: abgebrochen, ungeprüft`
  - Test: `engine/tests/test_schreiben.py::test_zu_langsamer_vorgang_gibt_meldung_in_der_zeit`
- **AC-3:** Given ein hängender git-Aufruf in `vorbereiten()` / When `anwenden_extern` läuft / Then Antwort 504 „nicht eingetragen“ (ohne Ergebnisprüfung, weil noch nichts angewendet wurde) innerhalb von `ZEIT_GESAMT` plus Reserve, nicht erst nach dem Hängen
  - Test: `engine/tests/test_schreiben.py::test_haengendes_vorbereiten_gibt_504_in_der_zeit`
- **AC-4:** Given die Sperre einer Reise ist belegt / When ein Vorgang für dieselbe Reise kommt / Then nach `ZEIT_SPERRE` Antwort 429; ein Vorgang für eine andere Reise wird davon nicht aufgehalten
  - Test: `engine/tests/test_schreiben.py::test_sperre_je_reise_und_begrenzte_wartezeit`
- **AC-5:** Given eine abgelehnte Anfrage (422) / When `anwenden_extern` läuft / Then das Protokoll enthält genau eine Zeile `Abgelehnt <werkzeug> 422: <Grund>` mit höchstens 200 Zeichen Grund, ohne Zeilenumbruch
  - Test: `engine/tests/test_schreiben.py::test_ablehnungsgrund_steht_im_protokoll`
- **AC-6:** Given `veroeffentlichen.service` und der Start durch den Schreibweg / When die Vorlage gerendert und der Startbefehl gebaut wird / Then die Einheit enthält `Nice=10`, `IOSchedulingClass=best-effort` und `IOSchedulingPriority=7`, und der Startbefehl beginnt mit `nice` und `ionice`
  - Test: `engine/tests/test_betrieb.py::test_einrichten_erzeugt_einheiten_ohne_platzhalter` und `engine/tests/test_schreiben.py::test_veroeffentlichen_startet_mit_niedriger_prioritaet`
- **AC-7:** Given ein Vorgang wird im Anwenden von der Frist abgebrochen / When die Ergebnisprüfung die Kennung auf `origin/main` findet bzw. nicht findet / Then die Antwort ist „eingetragen trotz Abbruch“ (200, ok: true) bzw. „nicht eingetragen (Abbruch)“ (504) aus der Meldungstabelle; die Commit-Nachricht eines Eintrags enthält die Zeile `Frieda-Vorgang: <Kennung>`; die Prozessgruppe des Anwenden ist nach dem Abbruch beendet (kein weiterlaufender Kindprozess)
  - Test: `engine/tests/test_schreiben.py::test_nach_abbruch_sagt_die_antwort_ob_eingetragen_wurde`
- **AC-8:** Given ein beliebiger Vorgang mit beliebigem Antwortcode (200, 422, 429, 503, 504, 500) / When er endet / Then das Protokoll enthält genau eine Zeile `Fertig <werkzeug> <code> in <Sekunden> s`
  - Test: `engine/tests/test_schreiben.py::test_dauer_steht_im_protokoll`

> Die Test-Zuordnung steht hier, nicht nachträglich: Nach der Freigabe ist diese Datei eingefroren. Stimmt ein Testname später nicht mehr, gehört die Korrektur in die TDD-RED-Artefakte. Mehrere der genannten Tests gibt es noch nicht (AC-3, AC-6 zweiter Teil, AC-7, AC-8) oder sie prüfen noch den Stand vor dieser Spec (AC-1 und AC-2 mit `ZEIT_ANWENDEN`); beides entsteht bzw. wird in TDD RED angepasst.

## Test Plan

Automatische Tests (jeweils an eine AC oben gebunden):
- `engine/.venv/bin/python -m pytest -q engine/tests/test_schreiben.py engine/tests/test_betrieb.py`
- Danach der volle Lauf: `engine/.venv/bin/python -m pytest -q engine/tests`

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Betriebsdetail ohne Berührung der Grundformen oder Merkmale (ADR-0001). Asynchrones Schreiben wäre eine Architekturänderung und wird gesondert an ADR-0001 gemessen. Die Kennungszeile in der Commit-Nachricht ist Metadaten des Schreibwegs, kein neues Merkmal der Reise.

## Changelog

- 2026-10-29: Initial spec created
- 2026-10-29: AC-7 (Ergebnisprüfung nach Abbruch, Prozessgruppe) und AC-8 (Dauer im Protokoll) ergänzt nach Tech-Lead-Prüfung
- 2026-10-29: Zeitbudget geschlossen (kein Mindestwert fürs Anwenden, Fetch und Suche unter einer Frist), Protokollcode bei „eingetragen trotz Abbruch“ festgelegt (Validator-Befund, 2. Lauf)
- 2026-10-29: Meldungstabelle, geschlossenes Zeitbudget (25 + 3 s Reserve) und Widersprüche zwischen AC-2/AC-3/AC-7 und Known Limitations bereinigt (Validator-Befund)
