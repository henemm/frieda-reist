---
entity_id: push-absender-709
type: bugfix
created: 2026-11-28
updated: 2026-11-28
status: draft
workflow: fix-709-push-absender
---

# Spec: Push-Nachrichten kommen nur noch über die Frieda-App (#709)

- [ ] Approved

## Purpose

Hat ein Konto Push in der Frieda-App eingeschaltet, kommen alle Push-Nachrichten nur noch über diese App. Kein fremder
Reisename mehr als Absender („from <Reise>“ unter dem Titel „Frieda“) und keine doppelten Nachrichten auf demselben
Gerät.

## Source

- **File:** `engine/push.py`
- **Identifier:** `zustellen`, neu `wirksam`
- Kontext: `docs/context/fix-709-push-absender.md`. Bugfix, Variante 2.

## Problem und Ursache

Auf dem iPhone steht unter der Nachricht „Deine neue Reise … ist angelegt“ (Titel „Frieda“) ein Absender „from
<Reise>“.

- iOS schreibt unter jede Web-Push-Nachricht „from <Name>“: den Namen der Web-App auf dem Home-Bildschirm, deren
  Service Worker das Abo hält. Den Titel setzt Frieda selbst.
- Bis 2.11.2026 schaltete man Push im Fuß der Reiseseite ein; diese Abos liegen in `push_abos` mit `reise = <Ordner>`
  und gehören der als App installierten Reiseseite. Seit Entscheidung A (2.11.2026) schaltet man Push nur noch auf Mein
  Konto in der Frieda-App ein (`anmeldung.push_geraet_schalten`, Abo mit `reise = ""`). Alte Reise-Abos bleiben
  bestehen, bis der Push-Dienst sie mit 404/410 ablehnt; der Altweg `POST /<reise>/push` nimmt weiter Abos an.
- `push.ziele(abos, reise)` wählt je Gerät (`geraet`, sonst `endpoint`) das Abo der betroffenen Reise, sonst das zuletzt
  aufgefrischte. Bei Meldungen ohne Reise (#631) und bei Meldungen einer anderen Reise kann so das Abo einer
  fremden Reiseseite gewählt werden: Absender „from <Reise>“.
- Die Gerätekennung (`rh-geraet`) ist je Web-App eigen. Frieda-App und installierte Reiseseite desselben iPhones haben
  verschiedene Kennungen, zählen als zwei Geräte und bekommen jede Nachricht doppelt.

## Entscheidung (Variante 2)

Neue reine Hilfsfunktion `wirksam(abos)` in `engine/push.py`: Hat das Konto mindestens ein Abo der Frieda-App
(`reise == ""`), liefert sie nur diese Abos (Reihenfolge unverändert, neueste zuerst), sonst alle Abos. `zustellen`
wählt die Ziele mit `ziele(wirksam(abos), reise)`. `push_karte` (`engine/anmeldung.py`) zählt die Geräte über
`push.wirksam(...)`, damit ein iPhone mit Alt- und Neu-Abo auf Mein Konto nicht als zwei Geräte erscheint.

Unverändert: `ziele`, `nachricht`, `seite_von` (Links), Mail-Rückfall in `einreihen` und bei den Statushinweisen
(`konten.push_abos` ungefiltert), Ruhezeit und Zeitzone (neuestes Abo), `push_abo_speichern`, Altweg `POST /<reise>/push`.

Verworfen: Variante 1 (Vorrang je Gerät) löst Doppelte und „from X“ bei Alt-Abo nicht, weil die Gerätekennung auf iOS je
Web-App verschieden ist. Variante 3 (Alt-Abos löschen, Altweg sperren) ändert Daten und löst ohne Variante 2 nichts.

## Bewusste Folge

Ein Gerät, das nur ein altes Reise-Abo hat, während dasselbe Konto auf einem anderen Gerät die Frieda-App mit Push
nutzt, bekommt keine Push-Nachrichten mehr; dort muss Push in der Frieda-App eingeschaltet werden. Das folgt
Entscheidung A (2.11.2026: Push nur noch in der Frieda-App) und betrifft nur Abos von vor diesem Datum. Konten ohne
Abo der Frieda-App behalten den bisherigen Weg, niemand verliert dadurch Nachrichten, der noch kein App-Abo hat.

## Nicht Teil dieser Änderung

- Alte Reise-Abos löschen oder aufräumen (Daten bleiben unangetastet).
- Den Altweg `POST /<reise>/push` sperren oder ändern.
- Änderungen an `ziele`, `seite_von`, Ruhezeit, Mail-Rückfällen.

## Scope

### Affected Files

| Datei | Änderung | Beschreibung |
|---|---|---|
| `engine/push.py` | MODIFY | `wirksam(abos)` neu; `zustellen` nutzt `ziele(wirksam(abos), reise)` |
| `engine/anmeldung.py` | MODIFY | `push_karte` zählt Geräte über `push.wirksam(...)` |
| `engine/tests/test_push.py` | MODIFY | neue Tests (siehe Test Plan) |

### Estimated Changes

- Dateien: 3
- LoC: +~10/-~2 Code, ~+40 Tests

Kein neuer Text (keine Änderung an `engine/texte_*.py`), keine Änderung am Datenformat der Reisedaten oder der
Kontendatenbank, keine Umstellung in `neu.py nachziehen`, keine Schnittstelle zu Instanzen.

## Dependencies

| Abhängigkeit | Art | Zweck |
|---|---|---|
| `engine/konten.py` (`push_abos`, `push_abo_speichern`) | Aufrufer/Daten | liefert die Abos, unverändert |
| `engine/anmeldung.py` (`push_geraet_schalten`) | Quelle der App-Abos | schreibt `reise = ""`, unverändert |
| `engine/rueckmeldungen.py` (`POST /<reise>/push`) | Quelle alter Abos | unverändert |

## Acceptance Criteria

- **AC-1:** Given ein Konto hat nur Abos der Frieda-App (`reise == ""`) / When `wirksam(abos)` läuft / Then liefert sie
  alle diese Abos in derselben Reihenfolge.
- **AC-2:** Given ein Konto hat nur alte Reise-Abos / When `wirksam(abos)` läuft / Then liefert sie alle Abos
  unverändert, und `ziele(wirksam(abos), reise)` ergibt dasselbe wie bisher `ziele(abos, reise)`.
- **AC-3:** Given ein Konto hat ein App-Abo und ein altes Reise-Abo (`beispielreise`) / When `wirksam(abos)` läuft /
  Then enthält das Ergebnis nur das App-Abo.
- **AC-4:** Given derselbe Zustand / When eine Meldung ohne Reise und eine Meldung zu `beispielreise` zugestellt
  werden (`zustellen` mit Test-`senden`) / Then geht je Nachricht genau ein Versand an das App-Abo, keiner an das alte
  Reise-Abo.
- **AC-5:** Given ein App-Abo ohne Gerätekennung (`geraet` leer) neben einem alten Reise-Abo / When zugestellt wird /
  Then geht die Nachricht nur an das App-Abo (Gerät zählt über `endpoint`).
- **AC-6:** Given ein Konto mit einem App-Abo und einem alten Reise-Abo / When Mein Konto die Benachrichtigungen
  zeigt / Then steht dort ein Gerät („Push ist auf 1 Gerät eingeschaltet“, `konto.push.geraete`, n = 1), nicht zwei.
- **AC-7:** Given ein Konto nur mit alten Reise-Abos / When zugestellt wird / Then ändert sich das Verhalten nicht
  (bestehende Tests, u. a. `test_je_geraet_ein_abo_das_der_reise_zuerst`, bleiben grün). Mail-Rückfälle,
  Ruhezeit und `seite_von` verhalten sich unverändert.

## Test Plan (TDD RED zuerst)

Alle in `engine/tests/test_push.py`, nur erfundene Daten (`beispielreise`, `stadtwochenende`, Ida, Karl, Beispiel-Endpunkte).

- [ ] `test_wirksam_nur_app_abos`: GIVEN zwei Abos mit `reise == ""` WHEN `push.wirksam` THEN beide, gleiche Reihenfolge (Fall a).
- [ ] `test_wirksam_nur_alte_reise_abos`: GIVEN Abos mit `reise` `beispielreise` und `stadtwochenende` WHEN `push.wirksam` THEN
  unverändert alle (Fall b, RED nicht nötig, sichert das Verhalten).
- [ ] `test_wirksam_app_abo_verdraengt_alte`: GIVEN ein App-Abo und zwei alte Reise-Abos WHEN `push.wirksam` THEN nur das
  App-Abo; `ziele(wirksam(abos), "")` und `ziele(wirksam(abos), "beispielreise")` liefern je nur dieses (Fall c).
- [ ] `test_wirksam_app_abo_ohne_geraetekennung`: GIVEN App-Abo mit `geraet == ""` und altes Abo mit Kennung WHEN `push.wirksam`
  und `push.ziele` THEN genau das App-Abo (Fall d).
- [ ] `test_zustellen_nur_ueber_die_frieda_app` (Fixture `reise`, Test-`senden` aus der Fixture): GIVEN Ida hat ihr altes Abo
  `geraet-ida-1` (`reise = beispielreise`) und zusätzlich ein App-Abo (`reise = ""`, Kennung `geraet-ida-app`) WHEN eine
  Rückmeldung zu `beispielreise` und eine Meldung ohne Reise zugestellt werden THEN `u.gesendet` enthält je Nachricht genau
  einen Eintrag, und zwar an den Endpunkt des App-Abos, keinen an das alte.
- [ ] `test_konto_nur_mit_alten_abos_bekommt_weiter_nachrichten`: GIVEN nur das alte Reise-Abo WHEN zugestellt wird THEN
  Versand wie bisher (deckt AC-7; die bestehenden Zustell-Tests der Fixture `reise` leisten das bereits mit).
- [ ] `test_kontoseite_zaehlt_geraete_ueber_wirksame_abos`: GIVEN App-Abo und altes Reise-Abo (verschiedene Kennungen) WHEN
  `/konto` abgerufen wird THEN `konto.push.geraete.one` (ein Gerät), nicht die Mehrzahl.
- [ ] Gesamtlauf `engine/.venv/bin/python -m pytest -q engine/tests -n 3` grün (insbesondere `test_texte.py`,
  `test_betrieb.py`, `test_protokolle_ohne_pfade.py`).

## Definition of Done

- [ ] AC-1 bis AC-7 durch Tests belegt, die neuen vorher rot (AC-1, AC-3 bis AC-6), danach grün
- [ ] Gesamtlauf der Tests grün
- [ ] Issue #709 mit Ursache und Entscheidung kommentiert; Schließen erst nach Auslieferung

## Prüfstelle ADR-0001

Berührt keine Grundform der Reise-Ontologie und kein Merkmal, nur die Auswahl der Push-Abos eines Kontos. Nichts
Reise- oder Instanzspezifisches in der Engine (die Unterscheidung läuft nur über das Feld `reise` des Abos, nie
über einen Reisenamen). Keine sichtbare Textänderung, also keine Änderung an `engine/texte_<sprache>.py`. Kein Format
der Reisedaten betroffen, daher keine Umstellung in `neu.py nachziehen`. Funktioniert gleich für Wanderung und
Städtewochenende.

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** keine (Korrektur innerhalb ADR-0005)

Keine neue ADR: setzt Entscheidung A vom 2.11.2026 (Push nur noch in der Frieda-App, Konten und Anmeldung, ADR-0005)
auch beim Versand um und ändert keine Architektur.

## Changelog

- 2026-11-28: Spec erstellt.
