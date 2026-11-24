---
entity_id: veraltete-meldungen-687
type: bugfix
created: 2026-11-24
updated: 2026-11-24
status: draft
workflow: fix-687-veraltete-meldungen
version: "1.0"
tags: [konnektor, mein-konto, meldungen, anfragen, warteliste, reise-loeschen]
---

# Veraltete Meldungen ohne Reise verschwinden (#687 und #693 Punkt 1)

## Approval

- [ ] Approved

## Purpose

Meldungen ohne Reise bleiben heute 14 Tage stehen, auch wenn das Ding, um das es geht, nicht mehr besteht: „Deine neue Reise … ist angelegt“ zu einer vorgemerkten oder entfernten Reise (#687), und Anfragen an die Betreiber (Bitte „Reisen anlegen“, bestätigter Wartelisten-Eintrag), die längst entschieden sind oder deren Konto oder Eintrag es nicht mehr gibt (#693 Punkt 1). Künftig gilt eine solche Meldung nur so lange, wie das Ding besteht; gefiltert wird beim Lesen, in einer Stelle für Konnektor und Mein Konto.

## Ziel und Abgrenzung

- **Entscheidung des Product Owners (Issue #693 Punkt 2, 24.11.2026):** Testanfragen werden nicht unterdrückt. Es gibt keine Ausnahme für Adressen des Testpostfachs; die Meldung zu einer Testanfrage kommt weiter und verschwindet wie jede andere, sobald die Anfrage entschieden oder das Konto entfernt ist (Punkt 1). Das deckt sich mit der bekannten Grenze in der Spec zu #648.
- **Im Scope:**
  - `meldungen_des_kontos` in `engine/rueckmeldungen.py` wendet auf die Meldungen ohne Reise (Ablage `neu`) eine kleine neue Prüfung „gilt die Meldung noch?“ an. Maßstab: Eine Anfrage-Meldung gilt genau so lange, wie die Anfrage unter „Freischaltungen“ oder „Warteliste“ auf Mein Konto steht (`konten.anfragen()`, `konten.warteliste()`).
  - Art `neue_reise`: weg, wenn `ziel` in `konten.vorgemerkte_reisen()` steht (vorgemerkt oder im Löschprotokoll). Wird die Reise zurückgeholt, erscheint die Meldung wieder. Es wird nicht auf Mitgliedschaft geprüft (bestehende Tests mit `winterwoche` bleiben).
  - Art `anfrage_reisen`: gilt, wenn das Konto unter den offenen Anfragen steht. Neues Feld `konto` (Kennung) in der Meldung; `anmeldung.betreiber_melden` schreibt es bei der Bitte über `extra`. Altmeldung ohne Feld `konto`: Zuordnung über die Adresse `email` aus `t` (Teil `konto.meldungen.text.anfrage_reisen`).
  - Art `anfrage_warteliste`: gilt, wenn die Adresse `email` aus `t` in `konten.warteliste()` steht. Kein neues Feld (die Adresse ist der Schlüssel der Tabelle).
  - Nicht zuzuordnen (weder Feld noch lesbares `t`): bleibt stehen, bis die 14 Tage um sind; nichts ohne Beleg verstecken. Unlesbare Daten werfen nie.
  - Alle anderen Arten (`betrieb`, `loeschung`, `warteliste_tagesgrenze`-Text der Art `betrieb`, Konflikte, Status, Erinnerungen) bleiben unverändert.
  - Mengen werden je Aufruf höchstens einmal und nur geladen, wenn eine passende Art vorliegt; keine Abfrage je Meldung. `vorgemerkte_reisen()` liest nur und legt ohne Datenbank nichts an.
  - Doku: je ein Satz in `docs/funktionen/erinnerungen.md`, `docs/konnektor.md`, `docs/konten.md`.
- **Nicht im Scope (bekannte Grenzen):**
  - Push und tägliche Zusammenfassung: Schon eingereihte Nachrichten können eine gerade erledigte Anfrage nennen; `engine/push.py` liest die Ablage selbst, die Spec zu #631 bleibt.
  - Warteliste, dieselbe Adresse erneut bestätigt: keine Zeitprüfung. Eine alte Meldung kann innerhalb der 14 Tage wieder erscheinen; sie stimmt dann inhaltlich, denn es gibt einen offenen Eintrag.
  - Adresse geändert bei einer Altmeldung ohne Feld `konto`: Die Meldung verschwindet, die Bitte steht weiter unter Freischaltungen. Endet nach 14 Tagen. Neue Meldungen sind davon nicht betroffen (Feld `konto`).
  - Recht direkt gesetzt (`recht_setzen`, Freigabe über die Warteliste): Die Bitte bleibt in `konten.anfragen()` offen, also bleibt auch die Meldung; gleiches Verhalten wie der Abschnitt Freischaltungen.
  - Zweimal gebeten: Es entstehen zwei Meldungen, beide verschwinden mit der Entscheidung.
  - Nebenbefunde werden eigene Issues: (a) `konten.loeschen` lässt Name und Adresse der Person in `<Konten>/neu/meldungen.jsonl` stehen; (b) war eine Person freigeschaltet und wurde ihr das Recht später entzogen, endet `trip_create_request` im Konnektor mit `KeyError: 'freigeschaltet'`.
  - `meldungen_aktuell` bleibt unverändert (auch für Reisen und `push.mail_rueckfall`); `neue_reise_gesehen` braucht nichts; `betrieb/zustellen.py` bleibt.
- **Kern (ADR-0001):** Keine neue Grundform, nichts Reise- oder Instanzspezifisches, nur Anzeige; nichts wird gelöscht. Keine neuen Textschlüssel (Texte der Meldungen unverändert). Keine Umstellung in `neu.py nachziehen`: Die Ablage ohne Reise besteht nicht aus Reisedaten, und alte Zeilen bleiben lesbar (Zuordnung über `t`, sonst bleibt die Meldung bis zum Ablauf).
- **Gelesen-Zähler:** Die Zahl der gelesenen Meldungen in `my_trips` sinkt mit verschwundenen Meldungen; gewollt.
- **Mehrere Betreiber:** Entscheidet eine Person, verschwindet die Meldung bei allen (eine Wahrheit: die Anfrage).

## Source

- **File:** `engine/rueckmeldungen.py`
- **Identifier:** `def meldungen_des_kontos` (mit neuer Hilfsfunktion für die Prüfung); `engine/anmeldung.py`: `def betreiber_melden`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `konten.vorgemerkte_reisen` | Code (`engine/konten.py`) | Menge der vorgemerkten und entfernten Reisen, liest nur |
| `konten.anfragen` | Code | Offene Bitten „Reisen anlegen“ (mit `konto`, `email`) |
| `konten.warteliste` | Code | Bestätigte, nicht freigegebene Einträge (`email`) |
| `rueckmeldungen.meldung_anlegen` (`extra`) | Code | Trägt das Feld `konto` |
| `rueckmeldungen.meldungen_aktuell` | Code | Bleibt unverändert; liefert die Meldungen nach Alter |
| `anmeldung.betreiber_melden` | Code | Legt die Anfrage-Meldungen an; aufgerufen aus `engine/anmeldung.py` und `engine/konnektor.py` (`trip_create_request`), die Aufrufer bleiben unverändert |
| `konnektor.meine_reisen_konto`, `anmeldung.meldungen_abschnitt`, `meldung_oeffnen`, Aktion `meldungen_gelesen` | Code | Leser von `meldungen_des_kontos`; wirken ohne eigene Änderung mit |
| #407, #631, #648, #693 | Issues und Specs | `docs/specs/oberflaeche/meldungen-konto-407.md`, `docs/specs/betrieb/warteliste-push-631.md`, `docs/specs/betrieb/warteliste-382.md`, `docs/specs/betrieb/testkonto-648.md` |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/rueckmeldungen.py` | MODIFY | Kleine Prüfung „gilt die Meldung ohne Reise noch?“, in `meldungen_des_kontos` auf die Ablage `neu` angewendet |
| `engine/anmeldung.py` | MODIFY | `betreiber_melden` speichert bei der Bitte die Konto-Kennung als Feld `konto` (`extra`) |
| `engine/tests/test_meldungen_veraltet.py` | CREATE | Tests zu allen Lagen, Konnektor und Mein Konto |
| `engine/tests/test_anmeldung.py` | MODIFY | Zwei Tests (um Zeile 606 und 635) stellen die Bitte wirklich |
| `docs/funktionen/erinnerungen.md`, `docs/konnektor.md`, `docs/konten.md` | MODIFY | je ein Satz |

### Estimated Changes

- Files: 2 Code, 2 Tests (davon 1 neu), 3 Doku (nur Sätze)
- LoC: rund +25/-3 Code, +120 Tests
- Risiko: niedrig (nur Anzeige, nichts wird gelöscht; eine Quelle für Konnektor und Mein Konto)

## Implementation Details

1. `rueckmeldungen.py`: Neue Hilfsfunktion (Arbeitsname `ohne_reise_gilt`) entscheidet je Meldung aus der Ablage ohne Reise anhand von `art`, `ziel`, `konto` und `t`. Die Mengen (`vorgemerkte_reisen()`, offene `anfragen()`, `warteliste()`) werden pro Aufruf von `meldungen_des_kontos` lazy höchstens einmal geladen. Adressvergleich ohne Beachtung der Groß- und Kleinschreibung.
2. `meldungen_des_kontos` filtert die Ergebnisse von `meldungen_aktuell(o, k["id"])` damit; die Meldungen aus den Reisen bleiben unberührt.
3. Adresse aus `t`: erster Teil mit Schlüssel `konto.meldungen.text.anfrage_reisen` beziehungsweise `konto.meldungen.text.anfrage_warteliste`, Wert `email`. Fehlt `t`, hat es eine falsche Form oder fehlt `email`: nicht zuzuordnen, Meldung bleibt (kein Wurf).
4. `betreiber_melden(k, art="anfrage_reisen", …)`: Bei `art == "anfrage_reisen"` und einem Konto `k` mit Kennung wird `extra={"konto": k["id"]}` übergeben. `k` kann `None` sein (Warteliste, Tagesgrenze) oder, in `engine/tests/test_push.py`, ein Wörterbuch ohne `id` (`TOM`); die Kennung wird deshalb mit `k.get("id")` gelesen und das Feld nur bei vorhandener Kennung gesetzt, damit Push-Tests unverändert grün bleiben. Ohne das Feld greift die Zuordnung über `t`.
5. `bezug` und `KENNUNG` werden nicht benutzt (würden zur Sprungmarke). `ziel="reise"` bleibt.

## Test Plan

### Automated Tests (TDD RED)

Datei: `engine/tests/test_meldungen_veraltet.py` (neu), erfundene Daten (Ida, Karl, Tom, Lea; Adressen `@beispiel.invalid`; Beispielreisen), Aufbau wie in `test_anmeldung.py` und `test_warteliste.py`. Rote Tests zuerst gegen den unveränderten Stand.

- [ ] `test_neue_reise_vorgemerkt_verschwindet`: GIVEN eine Meldung `neue_reise` zu einer Reise, in der das Konto Mitglied ist WHEN die Reise vorgemerkt wird THEN fehlt die Meldung in `meldungen_des_kontos`.
- [ ] `test_neue_reise_entfernt_verschwindet`: GIVEN dieselbe Meldung WHEN die Reise endgültig entfernt ist (Löschprotokoll) THEN fehlt sie.
- [ ] `test_neue_reise_zurueckgeholt_erscheint_wieder`: GIVEN die Reise ist vorgemerkt und die Meldung weg WHEN die Reise zurückgeholt wird THEN erscheint die Meldung wieder, die Datei `meldungen.jsonl` ist dazwischen unverändert.
- [ ] `test_neue_reise_ohne_mitgliedschaft_bleibt`: GIVEN eine Meldung `neue_reise` zu einer nicht vorgemerkten Reise, in der das Konto kein Mitglied ist (`winterwoche`) WHEN gelesen THEN bleibt sie sichtbar.
- [ ] `test_bitte_freigeschaltet_verschwindet`: GIVEN Karl bittet um „Reisen anlegen“, ein Betreiber hat die Meldung WHEN die Bitte freigeschaltet wird THEN fehlt die Meldung beim Betreiber.
- [ ] `test_bitte_abgelehnt_verschwindet`: wie zuvor mit `konten.freischalten(…, ja=False)`.
- [ ] `test_bitte_konto_geloescht_verschwindet`: GIVEN offene Bitte WHEN das Konto gelöscht wird (`konten.loeschen`) THEN fehlt die Meldung.
- [ ] `test_bitte_konten_zusammengefuehrt_verschwindet`: GIVEN offene Bitte WHEN das Konto mit einem anderen zusammengeführt wird (`konten.zusammenfuehren`) THEN steht die Bitte nicht mehr in `konten.anfragen()` und die Meldung fehlt.
- [ ] `test_offene_bitte_bleibt_sichtbar`: GIVEN offene Bitte WHEN gelesen THEN ist die Meldung da.
- [ ] `test_wartelisten_eintrag_freigegeben_verschwindet`: GIVEN bestätigter Eintrag mit Meldung WHEN `konten.freigeben` läuft THEN fehlt die Meldung.
- [ ] `test_wartelisten_eintrag_geloescht_verschwindet`: GIVEN bestätigter Eintrag WHEN der Eintrag gelöscht wird THEN fehlt die Meldung.
- [ ] `test_offener_wartelisten_eintrag_bleibt_sichtbar`: GIVEN bestätigter, nicht freigegebener Eintrag WHEN gelesen THEN ist die Meldung da.
- [ ] `test_adresse_geaendert_bitte_mit_feld_konto_bleibt`: GIVEN offene Bitte (neue Meldung mit Feld `konto`) WHEN das Konto seine Adresse ändert (`konten.adresse_aendern`) THEN bleibt die Meldung sichtbar.
- [ ] `test_altmeldung_ohne_feld_konto_ueber_adresse`: GIVEN eine Altmeldung `anfrage_reisen` ohne Feld `konto`, mit `t` samt `email` WHEN die Bitte offen ist THEN sichtbar; WHEN sie entschieden ist THEN weg.
- [ ] `test_nicht_zuzuordnende_altmeldung_bleibt`: GIVEN Altmeldung ohne Feld `konto` und ohne `t` WHEN gelesen THEN bleibt sie sichtbar (bis zum Ablauf der 14 Tage; ältere fallen wie bisher weg).
- [ ] `test_unlesbares_t_wirft_nicht`: GIVEN Meldungen mit `t` in falscher Form (kein Liste, kein `email`, falscher Typ) WHEN gelesen THEN kein Fehler, die Meldungen bleiben.
- [ ] `test_andere_arten_unveraendert`: GIVEN Meldungen der Arten `betrieb`, `loeschung` und die Tagesgrenze (`warteliste_tagesgrenze`) WHEN gelesen THEN bleiben sie wie bisher sichtbar.
- [ ] `test_mehrere_betreiber_entscheidung_gilt_fuer_alle`: GIVEN zwei Betreiber WHEN einer die Bitte freischaltet THEN fehlt die Meldung bei beiden.
- [ ] `test_wirkung_im_konnektor_my_trips`: GIVEN die obigen Lagen WHEN `my_trips` (`konnektor.meine_reisen_konto`) läuft THEN fehlen die veralteten Meldungen dort, die Zahl der gelesenen sinkt mit.
- [ ] `test_wirkung_auf_mein_konto`: GIVEN dieselben Lagen WHEN die Seite `/konto` abgerufen wird THEN steht die veraltete Meldung nicht im Abschnitt Meldungen, die gültigen schon.
- [ ] `test_filter_nur_beim_lesen`: GIVEN beliebige verschwundene Meldungen WHEN gelesen wird THEN ist `meldungen.jsonl` byte-gleich wie vorher.
- [ ] `test_testanfrage_wird_nicht_unterdrueckt`: GIVEN eine Bitte mit Adresse einer Unteradresse des Testpostfachs (erfundene `@beispiel.invalid`-Entsprechung) WHEN sie offen ist THEN kommt die Meldung wie bei jeder Adresse und verschwindet erst mit der Entscheidung (Entscheidung #693 Punkt 2).

### Bestehende Tests, die sich ändern

- `engine/tests/test_anmeldung.py` um Zeile 606: `betreiber_melden(k)` wurde ohne echte Bitte in `anfragen` aufgerufen, und der Test erwartet die Meldung danach sichtbar. Mit dem Filter wäre sie zu Recht weg. Der Test stellt die Bitte künftig wirklich (`konten.reisen_anlegen_anfragen`, dann `betreiber_melden`), sonst bleibt der Inhalt gleich (Teile in `t`, englischer Text auf Mein Konto).
- `engine/tests/test_anmeldung.py` um Zeile 635 bis 637 (`test_meldung_ohne_reise_folgt_nicht_dem_namen`): gleicher Grund; Mos Bitte wird wirklich gestellt, damit die Erwartung „Karl sieht genau eine Meldung `anfrage_reisen`, Mo keine“ weiter die Trennung nach Kennung prüft statt des Filters.
- Bleiben unverändert grün: `test_anmeldung.py` um Zeilen 420 und 624 (`neue_reise` zu `winterwoche`), `test_warteliste.py` um Zeilen 329 und 588 (Tagesgrenze, Art `betrieb`), `test_loeschen_reise.py` um Zeile 327 (Art `loeschung`), `test_push.py` Zeilen 592 bis 757 (Push liest die Ablage selbst; `TOM` hat keine Kennung, siehe Implementierung Punkt 4), `test_trennung.py`, `test_export.py`.

## Acceptance Criteria

- **AC-1:** Given eine Meldung `neue_reise` zu einer Reise / When die Reise vorgemerkt wird / Then verschwindet die Meldung bei Konnektor und Mein Konto. Test: `test_neue_reise_vorgemerkt_verschwindet`.
- **AC-2:** Given dieselbe Lage / When die Reise endgültig entfernt ist / Then bleibt sie weg. Test: `test_neue_reise_entfernt_verschwindet`.
- **AC-3:** Given die Reise ist vorgemerkt / When sie zurückgeholt wird / Then erscheint die Meldung wieder. Test: `test_neue_reise_zurueckgeholt_erscheint_wieder`.
- **AC-4:** Given eine nicht vorgemerkte Reise ohne Mitgliedschaft des Kontos / When gelesen wird / Then bleibt die Meldung sichtbar. Test: `test_neue_reise_ohne_mitgliedschaft_bleibt`.
- **AC-5:** Given eine Bitte „Reisen anlegen“ / When sie freigeschaltet wird / Then verschwindet die Meldung bei den Betreibern. Test: `test_bitte_freigeschaltet_verschwindet`.
- **AC-6:** Given eine Bitte / When sie abgelehnt wird / Then verschwindet die Meldung. Test: `test_bitte_abgelehnt_verschwindet`.
- **AC-7:** Given eine Bitte / When das Konto gelöscht wird / Then verschwindet die Meldung. Test: `test_bitte_konto_geloescht_verschwindet`.
- **AC-8:** Given eine Bitte / When das Konto zusammengeführt wird / Then verschwindet die Meldung. Test: `test_bitte_konten_zusammengefuehrt_verschwindet`.
- **AC-9:** Given eine offene Bitte / When gelesen wird / Then bleibt die Meldung sichtbar. Test: `test_offene_bitte_bleibt_sichtbar`.
- **AC-10:** Given ein bestätigter Wartelisten-Eintrag / When er freigegeben wird / Then verschwindet die Meldung. Test: `test_wartelisten_eintrag_freigegeben_verschwindet`.
- **AC-11:** Given ein bestätigter Wartelisten-Eintrag / When der Eintrag gelöscht wird / Then verschwindet die Meldung. Test: `test_wartelisten_eintrag_geloescht_verschwindet`.
- **AC-12:** Given ein offener Wartelisten-Eintrag / When gelesen wird / Then bleibt die Meldung sichtbar. Test: `test_offener_wartelisten_eintrag_bleibt_sichtbar`.
- **AC-13:** Given eine offene Bitte mit Feld `konto` / When das Konto die Adresse ändert / Then bleibt die Meldung. Test: `test_adresse_geaendert_bitte_mit_feld_konto_bleibt`.
- **AC-14:** Given eine Altmeldung ohne Feld `konto` mit Adresse in `t` / When die Bitte offen beziehungsweise entschieden ist / Then bleibt sie sichtbar beziehungsweise verschwindet. Test: `test_altmeldung_ohne_feld_konto_ueber_adresse`.
- **AC-15:** Given eine Altmeldung ohne Feld und ohne `t` / When gelesen wird / Then bleibt sie sichtbar. Test: `test_nicht_zuzuordnende_altmeldung_bleibt`.
- **AC-16:** Given ein unlesbares `t` / When gelesen wird / Then wirft nichts und die Meldung bleibt. Test: `test_unlesbares_t_wirft_nicht`.
- **AC-17:** Given Meldungen der Arten `betrieb`, `loeschung` und der Tagesgrenze / When gelesen wird / Then bleiben sie unverändert. Test: `test_andere_arten_unveraendert`.
- **AC-18:** Given mehrere Betreiber / When einer entscheidet / Then verschwindet die Meldung bei allen. Test: `test_mehrere_betreiber_entscheidung_gilt_fuer_alle`.
- **AC-19:** Given veraltete Meldungen / When `my_trips` läuft und `/konto` abgerufen wird / Then fehlen sie in beiden. Tests: `test_wirkung_im_konnektor_my_trips`, `test_wirkung_auf_mein_konto`.
- **AC-20:** Given beliebige verschwundene Meldungen / When gelesen wird / Then bleibt `meldungen.jsonl` unverändert (nur Filter beim Lesen). Test: `test_filter_nur_beim_lesen`.
- **AC-21:** Given eine Bitte mit Adresse des Testpostfachs / When sie offen ist / Then kommt die Meldung wie jede andere und verschwindet mit der Entscheidung; keine Ausnahme. Test: `test_testanfrage_wird_nicht_unterdrueckt`.
- **AC-22:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen.

## Definition of Done

- [ ] Rote Tests bestätigt (gegen den unveränderten Stand), danach Korrektur, Tests grün
- [ ] Gesamtlauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün
- [ ] Doku nachgezogen (`docs/funktionen/erinnerungen.md`, `docs/konnektor.md`, `docs/konten.md`)
- [ ] Pflichtprüfungen der CI grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), danach `git push origin HEAD:main`, Konnektor auf dem Server neu gestartet
- [ ] Prüfung am laufenden System nur über den Testzugang `frieda-test`, nie über das Konto des Product Owners; eine Meldung an ein Betreiberkonto lässt sich darüber nicht prüfen (`frieda-test` ist nie Betreiber), dafür gelten die Tests
- [ ] #687 und #693 erst nach dieser Prüfung mit Abschlusskommentar geschlossen; Nebenbefunde als eigene Issues angelegt

## Known Limitations

- Bereits eingereihte Push-Nachrichten und die tägliche Zusammenfassung können eine inzwischen erledigte Anfrage noch nennen.
- Erneut bestätigte Adresse auf der Warteliste: Eine alte Meldung kann innerhalb der 14 Tage wieder erscheinen.
- Adressänderung bei einer Altmeldung ohne Feld `konto`: Meldung verschwindet bis zum Ablauf, obwohl die Bitte offen ist.
- Direkt gesetztes Recht (`recht_setzen`) lässt die Bitte, und damit die Meldung, stehen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Fehlerkorrektur im bestehenden Muster „gefiltert wird beim Lesen“ (`meldungen_aktuell`); keine neue Grundform, kein neues Datenformat außer einem zusätzlichen optionalen Feld `konto` in neuen Meldungen, alte Zeilen bleiben lesbar.

## Changelog

- 2026-11-24: Initial spec created (Entwurf) für #687 und #693 Punkt 1.
