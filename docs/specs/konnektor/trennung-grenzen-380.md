---
entity_id: trennung-grenzen-380
type: feature
created: 2026-11-11
updated: 2026-11-11
status: draft
workflow: alpha-380-trennung
version: "1.0"
tags: [konnektor, konten, alpha, m5a, trennung, grenzen]
---

# Alpha: Trennung der Tester nachweisen und Mengenbegrenzung je Person (#380, Meilenstein M5a)

## Approval

- [ ] Approved

## Purpose

In der öffentlichen Alpha (M5a) nutzen viele Tester eine gemeinsame Instanz. Jede Person darf nur Reisen sehen, durchsuchen, lesen und beschreiben, in denen sie Mitglied ist, und niemand darf den Dienst durch unbegrenztes Anlegen und Schreiben überlasten. Bisher ist die Trennung nur durch einzelne Tests belegt, und Mengengrenzen je Person fehlen. Diese Änderung weist die Trennung mit einer Testreihe über zwei Konten und zwei Reisen nach, behebt, was der Test findet, und führt Grenzen je Konto ein, deren Werte aus der Instanz kommen.

Entscheidung des Product Owners (27.10. und 8.11.2026, #421): Das Lesen über den geheimen Seitenlink einer Reise bleibt ohne Anmeldung. Das ist eine bewusste Grenze und wird so festgehalten, nicht geändert.

## Ziel und Abgrenzung

- **Im Scope:**
  - Testreihe `engine/tests/test_trennung.py` mit zwei Konten (A: Mitglied der Beispielreise, B: Mitglied nur des Stadtwochenendes). B versucht Werkzeuge mit `reise=<Beispielreise>`, `suche`, `my_trips`/`meine_reisen`, `kalender`, Meldungen, Belege, Rückmeldungen per Cookie (POST) und Schreiben. In keiner Antwort an B stehen Namen oder Adressen aus Reise A. Wo der Test eine Lücke findet, wird sie im selben Workflow als Fehler behoben.
  - Test, dass Wächter- und Erinnerungsmails nur an Personen der eigenen Reise gehen und Meldungen eines Kontos nur Reisen mit Mitgliedschaft enthalten.
  - Test der bewussten Grenze: Wer den Seitenlink kennt, liest `stand`, `brett`, `packstand` ohne Anmeldung; ein angemeldetes Nicht-Mitglied sieht per Cookie nicht mehr als ein Gast.
  - Neue Mengenbegrenzung je Konto: angelegte Reisen (`FR_GRENZE_REISEN`, Vorgabe 10) und Schreibvorgänge im Konnektor je Stunde (`FR_GRENZE_SCHREIBEN`, Vorgabe 300). Werte aus der Instanz (`engine/instanz.py`, `instanz.wert(...)`), Vorgabe greift ohne Einstellung. Zähler in der Konten-Datenbank. Betreiber (Kontorecht `betreiber`) sind ausgenommen.
  - Ablehnung mit freundlichem Text samt Wartezeit (Textkatalog in allen Sprachen) und einer Zeile im Dienstprotokoll; kein Alarm.
  - Doku: `docs/konten.md` (Grenzen, bewusste Grenze beim Lesen), `docs/betrieb.md` und `betrieb/einstellungen.beispiel` (neue Werte).
  - Prüfbericht als Kommentar im Issue #380, ohne echte Reisen.
- **Nicht im Scope:**
  - Mehrere Mandanten in einer Instanz (#68). Funde dazu werden im Prüfbericht benannt und in #68 vermerkt, nicht gebaut.
  - Anmeldepflicht für das Lesen über den Seitenlink (entschieden, siehe oben).
  - Änderung der vorhandenen festen Grenzen (Anmeldecodes je Adresse und IP, Einladungen je Reise, Rückmeldungen je Reise und Minute, `limit_req` je IP in nginx).
  - Formatwechsel der Reisedaten: keiner, daher auch kein Eintrag in `neu.py nachziehen`.
- **Kern (ADR-0001):** Die Änderung betrifft Konten, Konnektor und Betrieb, nicht die Reise-Ontologie. Sie führt weder Art noch Merkmal noch Grundform ein. Grenzwerte stammen aus der Instanz, nichts Instanzspezifisches steht in der Engine.
- **Instanzen:** Die Werte `FR_GRENZE_REISEN` und `FR_GRENZE_SCHREIBEN` stehen in `betrieb/einstellungen.env` des Reisen-Repos; ohne Eintrag gelten die Vorgaben. Vor dem Vorspulen laufen die Tests der einbindenden Instanzen mit dem Branch.

## Source

- `engine/instanz.py`: neue Funktionen `grenze_reisen`, `grenze_schreiben` für die beiden Grenzwerte (Lesen über `wert(...)`, ungültige oder nicht positive Werte fallen auf die Vorgabe zurück).
- `engine/konten.py`: Tabellen in `SCHEMA` (vorhandene `CREATE TABLE IF NOT EXISTS`-Anlage, keine Umstellung bestehender Datenbanken nötig), Funktionen `reisegrenze_erreicht`, `reise_vormerken`, `schreibgrenze`, `schreiben_vormerken` (angelehnt an `_begrenzt` und die Tabelle `versand`).
- `engine/konnektor.py`: Prüfung in `reise_anlegen` und in `frieda_werkzeug` nach der Mitgliedschaftsprüfung, vor `werkzeug(...)`; Quelle der Einteilung „schreibend“: `SCHREIB_WERKZEUGE`, `SCHREIB_AKTION`, `ONTOLOGIE_WERKZEUGE`. Die zentrale Mitgliedschaftsprüfung (`frieda_werkzeug`, Fehler `konnektor.frieda_werkzeug.1`) bleibt unverändert, solange der Test keine Lücke findet.
- `engine/texte_de.py`, `engine/texte_en.py` und jede weitere `engine/texte_<sprache>.py`: Ablehnungstexte.
- `engine/tests/test_trennung.py`, `engine/tests/test_grenzen.py` (neu).
- `docs/konten.md`, `docs/betrieb.md`, `betrieb/einstellungen.beispiel`.

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/konten.py` (`mitgliedschaften`, `recht`, `SCHEMA`, `db`) | Code | Mitgliedschaft, Kontorecht `betreiber`, Zähler |
| `engine/konnektor.py` (`frieda_werkzeug`, `reisen_des_kontos`, `reise_anlegen`, `werkzeug`) | Code | zentrale Prüfung, Ort der Grenzen |
| `engine/instanz.py` (`wert`) | Code | Grenzwerte der Instanz |
| `engine/rueckmeldungen.py` (`name_fuer`, `seher`, `wer_ist`, Meldungen, Belege) | Code | Gegenstand der Trennungstests |
| `engine/waechter.py`, `engine/kalender.py`, `engine/belege.py` | Code | Gegenstand der Trennungstests |
| ADR-0001, ADR-0005 (Punkte 4 und 5) | Entscheidung | Kern; Rolle gehört zur Reise, Identität zum Konto |
| #421 | Entscheidung | Lesen über den Seitenlink bleibt |
| #68 | Folgearbeit | mehrere Mandanten, außerhalb des Umfangs |
| #382 (Warteliste) | Nachbararbeit | Recht `reise_anlegen` steuert, wer anlegen darf; die Reisegrenze gilt zusätzlich |

## Scope

- **Affected Files:** `engine/instanz.py`, `engine/konten.py`, `engine/konnektor.py`, `engine/texte_de.py`, `engine/texte_en.py` (und weitere vorhandene Sprachdateien), `engine/tests/test_trennung.py`, `engine/tests/test_grenzen.py`, `docs/konten.md`, `docs/betrieb.md`, `betrieb/einstellungen.beispiel`.
- **Estimated Changes:** etwa +350 / -10 Zeilen, davon rund 250 Tests. Risiko mittel: die Prüfung betrifft jeden Schreibvorgang im Konnektor; darum großzügige Vorgaben und Betreiber ausgenommen.

## Implementation Details

### Grenzwerte
```
instanz.grenze_reisen()      -> int   FR_GRENZE_REISEN,    Vorgabe 10
instanz.grenze_schreiben()   -> int   FR_GRENZE_SCHREIBEN, Vorgabe 300 je Konto und Stunde
```
Gelesen über `wert(name)`; leer, keine ganze Zahl oder kleiner als 1 gilt als nicht gesetzt (Vorgabe). Jeder Aufruf liest neu, damit Tests mit `monkeypatch.setenv` arbeiten können.

### Zähler (Konten-Datenbank, `konten.py`)
- Tabelle `angelegte_reisen (konto TEXT, pfad TEXT, zeit REAL)`: eine Zeile je angenommener Reiseanfrage des Kontos. Sie zählt auch Anfragen, deren Seite noch nicht online ist; dauerhaft, kein Fenster.
- Tabelle `schreibvorgaenge (konto TEXT, zeit REAL)`: eine Zeile je angenommenem schreibendem Werkzeugaufruf; Zeilen älter als eine Stunde werden bei jeder Prüfung gelöscht (gleitendes Fenster, wie `_begrenzt`).
- Funktionen: `reisegrenze_erreicht(k)`, `reise_vormerken(k, pfad)`, `schreibgrenze(k)` (liefert `None` oder die Wartezeit in Sekunden bis zum Freiwerden des ältesten Eintrags), `schreiben_vormerken(k)`. Für Konten mit `recht(k, "betreiber")` liefern die Prüfungen immer „frei“.

### Prüfung im Konnektor
1. `reise_anlegen`: Nach der Eingabeprüfung, vor dem Ablegen der Anfrage: ist die Reisegrenze erreicht, Ablehnung mit Text; sonst nach erfolgreichem Ablegen `reise_vormerken`. Eine abgelehnte oder fehlerhafte Anfrage zählt nicht.
2. `frieda_werkzeug`: Nach der Mitgliedschaftsprüfung, vor `werkzeug(...)`: gehört `name` zur Menge „schreibend“, wird `schreibgrenze(k)` geprüft und bei Erfolg `schreiben_vormerken(k)`. „Schreibend“ ist abgeleitet aus der vorhandenen Einteilung: `name in SCHREIB_WERKZEUGE or name in SCHREIB_AKTION or name in ONTOLOGIE_WERKZEUGE`; es gibt keine zweite Liste. Lesende Werkzeuge und die Konto-Werkzeuge `meine_reisen`, `kalender`, `sprache_setzen`, `anfrage_entscheiden` zählen nicht. Die Prüfung läuft nach der Mitgliedschaftsprüfung, damit ein Konto durch Aufrufe fremder Reisen keinen Zähler verbraucht.
3. Ablehnung: `(tk("konnektor.grenze.schreiben", ...), True)` bzw. `tk("konnektor.grenze.reisen", ...)` mit Wartezeit in Minuten (aufgerundet) beziehungsweise Grenzwert; eine Zeile auf stderr im Stil der vorhandenen Dienstprotokolle (`grenze <konto> schreiben|reisen`, ohne Adresse oder Name). Kein `betreiber_melden`, kein Telegram.

### Texte
Neue Schlüssel (Namen verbindlich erst bei der Umsetzung, nach dem Schema der Katalogdatei) in allen vorhandenen `engine/texte_<sprache>.py`; Ton freundlich, mit Wartezeit, ohne Vorwurf. `engine/tests/test_texte.py` bleibt grün, die Ausnahmelisten werden nicht länger.

## Expected Behavior

- **Input:** schreibender Werkzeugaufruf oder `reise_anlegen` eines Kontos.
- **Output:** innerhalb der Grenzen unverändertes Verhalten; darüber eine verständliche Ablehnung (Fehlerflag gesetzt), die Wartezeit nennt (Schreibgrenze) beziehungsweise sagt, dass die Höchstzahl angelegter Reisen erreicht ist.
- **Side effects:** je angenommenem Schreibvorgang eine Zeile in `schreibvorgaenge`, je angenommener Reiseanfrage eine in `angelegte_reisen`; bei Ablehnung eine Protokollzeile.

## Known Limitations

- Bewusste Grenze: Das Lesen über den geheimen Seitenlink (Reiseseite, `stand`, `brett`, `packstand`, Belege für Gäste) braucht keine Anmeldung. Wer den Link kennt, liest. Der Link hat 96 Bit Zufall, ist `noindex` und `no-referrer`. Entschieden vom Product Owner (#421); im Prüfbericht und in `docs/konten.md` festgehalten.
- Entfernte Personen lesen über den Seitenlink weiter wie ein Gast (gewollt, wird festgehalten, nicht geändert).
- Die Grenzen gelten je Konto. Wer mehrere Konten anlegt, umgeht sie; das begrenzen Anmeldecodes je Adresse und IP und die Warteliste (#382).
- `angelegte_reisen` zählt Anfragen, nicht dauerhaft vorhandene Reisen; archivierte oder gelöschte Reisen geben die Zahl nicht frei. Der Betreiber kann Zeilen in der Datenbank entfernen oder die Grenze erhöhen.
- Mehrere Mandanten in einer Instanz bleiben offen (#68).

## Definition of Done

Fertig ist diese Änderung, wenn:

- [ ] Jede Acceptance Criterion unten ist durch einen automatischen Test belegt.
- [ ] Die Testreihe mit zwei Konten ist grün, und der Prüfbericht steht als Kommentar in #380: was geprüft wurde, was gefunden und behoben wurde, die bewusste Grenze beim Lesen über den Seitenlink, Funde zu mehreren Mandanten mit Verweis auf #68 (ohne echte Reisen, Namen oder Adressen).
- [ ] Ein Tester mit zu vielen Reisen oder Schreibvorgängen bekommt in der Claude-App einen verständlichen Satz mit Wartezeit statt eines Fehlers; Betreiber merken keine Grenze.
- [ ] Texte in allen Sprachen vollständig, `test_texte.py` grün, Ausnahmelisten nicht länger.
- [ ] `docs/konten.md`, `docs/betrieb.md` und `betrieb/einstellungen.beispiel` nennen die Werte, Vorgaben und die bewusste Grenze.
- [ ] Die Tests der einbindenden Instanz laufen mit dem Branch (neue Umgebungswerte, neue Texte).
- [ ] Kein Formatwechsel der Reisedaten, kein Handschritt nach dem Software-Wechsel.
- [ ] Keine bestehende Funktion ist dabei kaputtgegangen (`engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün).
- [ ] Issue #380 mit Nachweis kommentiert und erst nach der Auslieferung auf `main` geschlossen.

## Acceptance Criteria

Alle Tests nutzen nur erfundene Daten (Beispielreise mit Ida und Karl, Stadtwochenende mit Tom und Lea, erfundene Adressen) und eine eigene Konten-Datenbank je Test. „Nichts aus der Beispielreise“ heißt im Test: Keiner der Prüfwerte steht in der Antwort an B, nämlich die Namen der Personen der Beispielreise (Ida, Karl), ihre E-Mail-Adressen in den Testkonten, der Titel der Beispielreise und ihr Ordnername. Die Prüfwerte liest der Test aus der Beispielreise und den Testkonten, nicht aus einer festen Liste.

- **AC-1:** Given Konto B ist nur Mitglied des Stadtwochenendes, Konto A der Beispielreise / When B jedes Reise-Werkzeug aus der Werkzeugliste des Konnektors (`frieda_werkzeuge`, im Test darüber parametrisiert, also lesend wie schreibend, auch `suche`, `show`, `overview`) mit `reise=beispielreise` aufruft / Then lehnt der Konnektor mit dem Fehler `konnektor.frieda_werkzeug.1` ab, nichts wird geschrieben, und die Antwort enthält keinen Namen und keine Adresse aus der Beispielreise.
  - Test: `engine/tests/test_trennung.py::test_fremde_reise_ueber_werkzeuge_abgelehnt`
- **AC-2:** Given dieselben Konten / When B `meine_reisen`, `kalender` und Werkzeuge ohne Angabe `reise` aufruft / Then erscheinen nur Reisen mit Mitgliedschaft von B; Antworttexte und Kalender-Abo (nur über Mitgliedschaften) enthalten nichts aus der Beispielreise, auch nicht bei einer Mitgliedschaft auf einer unveröffentlichten Reise.
  - Test: `engine/tests/test_trennung.py::test_uebersichten_nur_eigene_reisen`
- **AC-3:** Given dieselben Konten / When B über den Konnektor bei der Beispielreise schreibt (Rückmeldung, Aufgabe, Buchung, Person einladen oder entfernen, Wert eintragen) / Then wird abgelehnt, und die Reisedaten der Beispielreise bleiben unverändert (Vergleich der Datei oder Version vor und nach dem Versuch).
  - Test: `engine/tests/test_trennung.py::test_fremde_reise_nicht_beschreibbar`
- **AC-4:** Given (a) eine gültige Sitzung (Cookie) von B, (b) eine Anfrage ganz ohne Sitzung / When jeweils per POST an den Rückmeldedienst für die Beispielreise geschrieben wird (Rückmeldung, Beleg, Entscheidung) / Then antwortet der Dienst bei (a) mit 403 und bei (b) mit 401, und in beiden Fällen wird nichts gespeichert.
  - Test: `engine/tests/test_trennung.py::test_rueckmeldedienst_schreiben_ohne_mitgliedschaft`
- **AC-5:** Given Meldungen und Belege in der Beispielreise / When B Meldungen, die Belegliste und einzelne Belege der Beispielreise über seinen Cookie abruft / Then enthalten Meldungen nur Reisen mit Mitgliedschaft von B, und Belege sehen angemeldete Nicht-Mitglieder wie ein Gast (`seher`); Namen und Adressen aus der Beispielreise tauchen in keiner Antwort an B auf.
  - Test: `engine/tests/test_trennung.py::test_meldungen_und_belege_nur_eigene_reisen`
- **AC-6:** Given der Wächter und der Erinnerer laufen über beide Reisen / When sie Mails erzeugen / Then geht jede Mail nur an Personen derselben Reise; kein Konto ohne Mitgliedschaft bekommt eine Mail oder Meldung einer fremden Reise.
  - Test: `engine/tests/test_trennung.py::test_waechter_und_erinnerer_nur_an_eigene_reise`
- **AC-7:** Given der geheime Seitenlink der Beispielreise (bewusste Grenze, #421) / When ein Gast ohne Anmeldung und ein angemeldetes Nicht-Mitglied `stand`, `brett` und `packstand` lesen / Then bekommen beide dieselbe Antwort (Gast-Sicht), und das Nicht-Mitglied sieht nicht mehr als der Gast.
  - Test: `engine/tests/test_trennung.py::test_lesen_per_seitenlink_nicht_mehr_als_gast`
- **AC-8:** Given eine Instanz ohne Einstellung der Grenzen / When ein Konto Werkzeuge schreibend aufruft und Reisen anlegt / Then gelten die Vorgaben 10 Reisen und 300 Schreibvorgänge je Stunde; Werte aus der Instanz (`FR_GRENZE_REISEN`, `FR_GRENZE_SCHREIBEN`, auch über `einstellungen.env`) ersetzen sie; ungültige oder nicht positive Werte fallen auf die Vorgabe zurück.
  - Test: `engine/tests/test_grenzen.py::test_grenzwerte_vorgabe_und_instanz`
- **AC-9:** Given `FR_GRENZE_SCHREIBEN=3` / When ein Konto drei schreibende Aufrufe innerhalb einer Stunde ausführt und einen vierten versucht / Then wird der vierte mit freundlichem Text samt Wartezeit abgelehnt und schreibt nichts; lesende Werkzeuge und Konto-Werkzeuge bleiben frei; nach Ablauf des Fensters (Zeit im Test verschoben) geht es wieder; ein Aufruf einer fremden Reise (Fehler der Mitgliedschaft) verbraucht keinen Zähler.
  - Test: `engine/tests/test_grenzen.py::test_schreibgrenze_je_konto_und_stunde`
- **AC-10:** Given `FR_GRENZE_REISEN=2` und ein Konto mit Recht `reise_anlegen` / When es die dritte Reise anlegen will / Then wird abgelehnt mit Text, der die Höchstzahl nennt; die ersten beiden gehen durch, eine fehlerhafte Anfrage zählt nicht, und eine zweite Person (anderes Konto) ist nicht betroffen.
  - Test: `engine/tests/test_grenzen.py::test_reisegrenze_je_konto`
- **AC-11:** Given ein Konto mit Recht `betreiber` / When es über beiden Grenzen liegt / Then wird es nicht abgelehnt.
  - Test: `engine/tests/test_grenzen.py::test_betreiber_ausgenommen`
- **AC-12:** Given eine Ablehnung durch eine Grenze / When sie auftritt / Then steht eine Zeile im Dienstprotokoll (ohne Adresse und Namen), der Text kommt aus dem Katalog in jeder vorhandenen Sprache (de, en und weitere), und es wird weder eine Meldung an Betreiber noch ein Alarm ausgelöst.
  - Test: `engine/tests/test_grenzen.py::test_ablehnung_protokoll_texte_ohne_alarm`
- **AC-13:** Given die Schreibgrenze / When die Menge der „schreibenden“ Werkzeuge bestimmt wird / Then stammt sie aus `SCHREIB_WERKZEUGE`, `SCHREIB_AKTION` und `ONTOLOGIE_WERKZEUGE` (keine zweite Liste), und jedes dort genannte Werkzeug zählt, kein anderes.
  - Test: `engine/tests/test_grenzen.py::test_schreibend_aus_vorhandener_einteilung`
- **AC-14:** Given die Doku der Instanz / When die Grenzen eingebaut sind / Then nennen `betrieb/einstellungen.beispiel` und `docs/betrieb.md` beide Umgebungswerte `FR_GRENZE_REISEN` und `FR_GRENZE_SCHREIBEN` mit ihren Vorgaben, und `docs/konten.md` nennt beide Werte sowie die bewusste Grenze beim Lesen über den Seitenlink mit Verweis auf #421.
  - Test: `engine/tests/test_grenzen.py::test_einstellungen_beispiel_nennt_grenzen` (einstellungen.beispiel, betrieb.md) und `engine/tests/test_grenzen.py::test_konten_doku_nennt_grenzen_und_seitenlink` (konten.md: beide Namen, „#421“)

Regression (kein eigenes AC, Teil der Definition of Done): Die bestehenden Tests bleiben unverändert grün, belegt durch den Gesamtlauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests`.

> Die Test-Zuordnung ist bei der Spec-Erstellung eingetragen. Stimmt ein Testname später nicht mehr, gehört die Korrektur in die TDD-RED-Artefakte, nicht in diese Datei.

## Test Plan

Automatische Tests (jeweils an eine AC oben gebunden):

- `engine/.venv/bin/python -m pytest -q engine/tests/test_trennung.py engine/tests/test_grenzen.py`
- Regression: `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` (zusätzlich in der CI: `tests (leer)`, `tests (instanz)`, `gitleaks`).
- Vor dem Vorspulen: Tests des Reisen-Repos der Instanz mit diesem Branch (Anleitung dort), weil Umgebungswerte und Texte neu sind.
- Vorgehen: Die Testreihe zuerst schreiben; RED nur dort, wo sie eine Lücke findet, sonst belegt sie den Ist-Stand. Funde werden im selben Workflow behoben und im Prüfbericht genannt.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue; ADR-0005 (bestehend) und ADR-0001
- **Rationale:** Die Trennung folgt ADR-0005 (Rolle gehört zur Reise, Identität zum Konto; Lesen über den Seitenlink entschieden in #421). Grenzwerte aus der Instanz folgen ADR-0001. Die Zähler liegen in der Konten-Datenbank, nicht in einer Reise; daher keine neue Entscheidung zum Datenformat.

## Changelog

- 2026-11-11: Erstfassung (Entwurf) für #380; Kernentscheidungen aus der Analyse (`docs/context/alpha-380-trennung.md`): Testreihe mit zwei Konten, Lesen über den Seitenlink als bewusste Grenze, Grenzen je Konto aus der Instanz.
