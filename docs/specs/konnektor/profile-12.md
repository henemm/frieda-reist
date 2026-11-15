---
entity_id: profile-12
type: feature
created: 2026-11-15
updated: 2026-11-15
status: draft
workflow: feature-12-profile
version: "1.0"
tags: [konnektor, konten, profil, datenschutz, art-9, paket-f, m6]
---

# Profile je Person (#12, Paket F, Meilenstein M6)

## Approval

- [ ] Approved

## Purpose

Jede Person bekommt ein reiseübergreifendes Profil: kurze Einträge zu ihren Vorlieben (zum Beispiel Tempo, Essen, Unterkunftsarten, Budgetgefühl, Erlebtes). Der AI-Client schlägt Einträge vor; eingetragen wird nur, was die Person im Gespräch bestätigt hat. Die Person sieht, ändert und löscht ihr Profil auf „Mein Konto“ und über ihren eigenen AI-Client. Vorschläge an Wahlstellen nennen das Profil als Grund, wenn der Baustein `profile` der Reise es erlaubt. Organisator:innen und andere Mitreisende sehen nichts davon.

Grundlage sind die Entscheidungen des Product Owners vom 1.11.2026 (Kommentar in #12) und die Analyse in `docs/context/feature-12-profile.md`, die hier nicht neu entschieden werden.

## Ziel und Abgrenzung

- **Im Scope:**
  - Tabelle `profil` in `konten.db`, Funktionen in `engine/konten.py`, Kontolöschung und Kontozusammenführung kennen sie.
  - Drei Konto-Werkzeuge im Konnektor (ohne `reise`): `my_profile`, `profile_entry_set`, `profile_entry_remove` mit deutschen Aliasen für Werkzeug- und Parameternamen.
  - Anleitungssätze: kontoweit in `anleitung_frieda`, je Reise in `anleitung()` abhängig vom Baustein `profile`.
  - Karte „Mein Profil“ auf Mein Konto (ansehen, Text ändern, Eintrag löschen).
  - Export `person.json` enthält das eigene Profil; Datenschutztext bekommt den Art.-9-Absatz.
  - `engine/reise.py`: `NOCH_NICHT_GEBAUT` wird leer.
  - Texte in `engine/texte_de.py` und `engine/texte_en.py`; Doku in `docs/konnektor.md`, `docs/produkt.md`, Verlaufszeile in `docs/adr/0001-kern.md`.
  - Tests in `engine/tests/test_profil.py` (neu) und die benannten Anpassungen bestehender Tests.
- **Nicht im Scope (Out of Scope):**
  - Teilen einzelner Profileinträge mit anderen Personen (später, eigenes Vorhaben).
  - Eine Zwischenstufe „vorgeschlagen“: Es gibt nur bestätigte Einträge (Bestätigung im Gespräch gilt als Einwilligung, PO 1.11.2026).
  - Profilanzeige auf der Reiseseite oder im Service Worker, Profil in Reisedaten, Reiseordnern oder Rückmeldungen.
  - Feste Kategorien oder Vorlieben-Katalog als Wissen der Software.
  - Eine Änderung des Reisedatenformats (`neu.py nachziehen` bleibt unberührt), ein neues Modul (`betrieb/deploy.sh` bleibt unberührt).
- **Kern (ADR-0001), neu gemessen am 15.11.2026:**
  1. Ontologie: Das Profil hängt an der Person (Grundform Person), nicht an einer Reise; es gilt gleich für die Wanderung (Ida, Karl) und das Stadtwochenende (Tom, Lea).
  2. Kein Katalog: `bereich` ist freier Text; die Software kennt keine Kategorien. Tempo, Essen und ähnliche Wörter stehen höchstens als Beispiele im Anleitungstext.
  3. Keine KI: Frieda prüft nur Pflichtfelder, Längen, Anzahl und Eigentum.
  4. Tür: Konto-Werkzeuge im Konnektor, dokumentiert in `docs/konnektor.md`.
  5. Herkunft: `herkunft` ist Pflicht, `datum` setzt Frieda selbst.
  6. Rollen: keine Entscheidung; Eintrag nur mit `confirmed=true`.
  7. IDs und Verlauf: Das Profil ist ein Kontodatum wie Sitzungen, kein Teil der Reise-Ontologie. Das echte Löschen einzelner Einträge ist durch die PO-Entscheidung vom 1.11.2026 („löschbar“) und Art. 17 DSGVO gedeckt; die Verlaufszeile in ADR-0001 stellt das klar, es entsteht keine neue Ausnahme.
  8. PWA: Das Profil erscheint nie auf der Reiseseite und nie im Service Worker; seine Heimat ist „Mein Konto“ (ADR-0003).
  9. Claude Code: nicht betroffen, Reiseinhalte entstehen im AI-Client.
  10. Doku: siehe Scope.
- **Instanzen:** Nichts Instanzspezifisches; Grenzen kommen als Vorgaben aus `engine/instanz.py`. Beispiele und Tests nur mit Ida, Karl, Tom, Lea und erfundenen Daten.

## Source

- `engine/konten.py`: `SCHEMA` (neue Tabelle, Migration per `CREATE TABLE IF NOT EXISTS`), `loeschen(kid)` (Tabellenliste, rund Z. 655), `zusammenfuehren`, `schreibgrenze`/`schreiben_vormerken` (#380).
- `engine/konnektor.py`: `frieda_werkzeuge(k)` (rund Z. 2257), `frieda_werkzeug(k, name, args)` (rund Z. 2358; Muster `an_frieda_melden`, `sprache_setzen`, `kalender`; neue Zweige vor `reisen_des_kontos`), `anleitung_frieda` (rund Z. 2293), `anleitung()` je Reise (rund Z. 3016 und 3052).
- `engine/schnittstelle.py`: englische Außennamen mit deutschen Aliasen; `"profiles": "profile"` für den Baustein steht schon (rund Z. 150).
- `engine/reise.py`: `BAUSTEINE` enthält `profile`; `NOCH_NICHT_GEBAUT` (rund Z. 41, Hinweis rund Z. 516).
- `engine/anmeldung.py`: `konto_seite` (rund Z. 1040), `bearbeiten` (POST-Zweige von `/konto`), `export_person` (rund Z. 939), `EXPORT_PUNKTE`, `datenschutz_inhalt`.
- `engine/instanz.py`: Vorgaben der Engine (neue Grenzen).
- `engine/texte_de.py`, `engine/texte_en.py`: `konnektor.werkzeug.*`, `konto.*`, `recht.datenschutz.*` (rund Z. 3546).
- Verwandte Specs: `docs/specs/betrieb/loeschen-381.md`, `docs/specs/betrieb/export-498.md`, `docs/specs/betrieb/rechtliches-383.md`.

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `konten.db` (sqlite) | Daten | Ort der Tabelle `profil`, außerhalb jeder Reise |
| `engine/konten.py` | module | Funktionen, Löschen, Zusammenführen, Schreibgrenze je Konto (#380) |
| `engine/konnektor.py` | module | Konto-Werkzeuge, Anleitung, OAuth-Konto des Aufrufers |
| `engine/schnittstelle.py` | module | Außennamen und deutsche Aliase |
| `engine/anmeldung.py` | module | Mein Konto, Export, Datenschutzseite |
| `engine/instanz.py` | module | Vorgaben für Längen und Anzahl |
| `engine/texte_de.py`, `engine/texte_en.py` | module | alle sichtbaren Texte (ADR-0006) |
| `engine/reise.py` | module | Baustein `profile`, `NOCH_NICHT_GEBAUT` |
| #380 (Schreibgrenze je Konto) | Vorhaben | Setzen zählt mit |
| #381 (Löschen), #498 (Export), #383 (Datenschutz) | Vorhaben | Löschen, Export und Datenschutztext werden erweitert |
| ADR-0001, ADR-0003, ADR-0005, ADR-0006 | ADR | Kern, eine Heimat, Konten, Mehrsprachigkeit (keine neue ADR) |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/konten.py | MODIFY | Tabelle `profil`; `profil_liste`, `profil_setzen`, `profil_aendern`, `profil_entfernen`; `loeschen()` und `zusammenfuehren()` |
| engine/konnektor.py | MODIFY | Werkzeuge `my_profile`, `profile_entry_set`, `profile_entry_remove`; Anleitungssätze |
| engine/schnittstelle.py | MODIFY | Außennamen und deutsche Aliase (`mein_profil`, Parameternamen) |
| engine/instanz.py | MODIFY | Vorgaben: Länge `bereich`, Länge `text`, Anzahl Einträge je Konto |
| engine/texte_de.py | MODIFY | Texte der Werkzeuge, Karte, Fehler, Anleitung, Datenschutz |
| engine/texte_en.py | MODIFY | dieselben Schlüssel auf Englisch |
| engine/anmeldung.py | MODIFY | Karte „Mein Profil“, POST-Zweige, `export_person`, `EXPORT_PUNKTE` |
| engine/reise.py | MODIFY | `NOCH_NICHT_GEBAUT` leeren (Struktur bleibt) |
| engine/tests/test_profil.py | CREATE | alle neuen Tests |
| engine/tests/test_grenzen.py, test_bauen.py, test_englisch_schnittstelle.py, test_oauth.py | MODIFY | erwartbare Anpassungen (freie Werkzeuge, Baustein-Hinweis, Werkzeuglisten) |
| docs/konnektor.md | MODIFY | Werkzeugliste, Regeln des Profils |
| docs/produkt.md | MODIFY | „profile nicht gebaut“ aktualisieren (rund Z. 27, 49, 67, 156) |
| docs/adr/0001-kern.md | MODIFY | Verlaufszeile: Löschen einzelner Profileinträge gedeckt durch PO-Entscheidung 1.11.2026, Kontodatum wie Sitzungen, keine neue Ausnahme |

### Estimated Changes

- Files: 13 (davon 1 neu)
- LoC: +600/-15 (Code rund 270, Texte rund 40 Schlüssel je Sprache, Tests rund 250, Doku rund 30)

## Implementation Details

### Daten (`engine/konten.py`)

1. Tabelle `profil`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `konto` (Kontokennung), `bereich` (freier Text), `text`, `herkunft` (`NOT NULL`), `datum` (von Frieda gesetzt, UTC, ISO-8601). Migration per `CREATE TABLE IF NOT EXISTS` im `SCHEMA`; keine Reisedatenformat-Änderung, daher nichts in `neu.py nachziehen`.
2. Nach außen heißt ein Eintrag `PR-<n>` (n = `id`). Wegen `AUTOINCREMENT` wird eine Nummer nie wiederverwendet, auch nicht nach dem Löschen oder einer Kontozusammenführung.
3. Funktionen: Liste der Einträge eines Kontos (nach `id` aufsteigend), Setzen (neu oder Ändern eines vorhandenen Eintrags des Kontos), Entfernen. Jede Abfrage nimmt die Kontokennung des angemeldeten Kontos und filtert immer mit `WHERE konto = ?`; es gibt keine Funktion, die Einträge ohne Konto liest.
4. Prüfungen in `konten.py` (Fehler als `KontoFehler` mit Text je Sprache): `bereich`, `text` und `herkunft` nicht leer nach `strip()`; Länge `bereich` und `text` höchstens die Vorgabe aus `instanz.py`; Anzahl der Einträge je Konto höchstens die Vorgabe (nur beim Neuanlegen). Die Software prüft nie den Inhalt, nie einen Bereichsnamen.
5. `loeschen(kid)`: `profil` steht in der Tabellenliste, die in einer Transaktion mit `DELETE FROM <t> WHERE konto = ?` geleert wird. `zusammenfuehren(...)`: Einträge des aufgelösten Kontos werden auf das bleibende Konto umgehängt (`UPDATE profil SET konto = ?`), Kennungen bleiben gleich; die Obergrenze gilt dabei nicht (nichts geht verloren).

### Konnektor-Werkzeuge (ohne `reise`)

6. `my_profile` (Alias `mein_profil`, nur Lesen): liefert die Einträge des Kontos des Aufrufers mit `PR-<n>`, `bereich`, `text`, `herkunft`, `datum`. Das Lesewerkzeug ist immer erreichbar, auch wenn ein Baustein `profile` einer Reise aus ist (technisch nicht je Reise sperrbar, der AI-Client hat das Konto); die Wirkung je Reise steuert die Anleitung.
7. `profile_entry_set` (Alias `profil_eintrag_setzen`): Parameter `bereich`, `text`, `herkunft`, `confirmed` und optional `id` (`PR-<n>`, dann wird dieser Eintrag geändert, sonst entsteht ein neuer). Pflicht: `confirmed=true` und `herkunft`; ohne eines von beiden wird abgelehnt, nichts geschrieben. Setzen zählt zur Schreibgrenze je Konto (#380, `konten.schreibgrenze`/`schreiben_vormerken`, explizit aufgerufen nach dem Muster der anderen schreibenden Konto-Werkzeuge). `datum` setzt Frieda. Eine fremde oder unbekannte `PR-<n>` führt zu „nicht gefunden“, ohne zu verraten, ob sie einem anderen Konto gehört.
8. `profile_entry_remove` (Alias `profil_eintrag_entfernen`): Parameter `id` (`PR-<n>`), echtes Löschen der Zeile. Wird nie von der Schreibgrenze blockiert (Löschen darf nie durch eine Grenze verhindert werden) und zählt nicht zu ihr. Eigentum wie bei Punkt 7.
9. Deutsche Aliase für Werkzeug- und Parameternamen stehen in `engine/schnittstelle.py` (`my_profile`/`mein_profil`, `profile_entry_set`/`profil_eintrag_setzen`, `profile_entry_remove`/`profil_eintrag_entfernen`, Parameter `confirmed`/`bestaetigt`, `herkunft`, `bereich`, `text`, `id`). Der Werkzeugname `my_profile` vermeidet bewusst die Verwechslung mit dem Baustein `profile`.
10. Beschreibungen der Werkzeuge stehen als `konnektor.werkzeug.*` in `texte_de.py` und `texte_en.py`. Fehler laufen über `konten.KontoFehler(...).text(sprache)`.

### Anleitung

11. `anleitung_frieda` (kontoweit) bekommt einen Satz: Ins Profil nur eintragen, was die Person im Gespräch ausdrücklich bestätigt hat; vorher den genauen Wortlaut und den Bereich zeigen lassen; nie raten oder aus Reisedaten ableiten. Bereiche wie Tempo oder Essen stehen höchstens als Beispiele („etwa“), nie als vollständige oder verbindliche Liste.
12. `anleitung()` je Reise bekommt einen Satz abhängig vom Baustein `profile`: Ist er an oder ist `bausteine` `None` (gilt als an), soll der AI-Client das Profil der Person nutzen und bei Vorschlägen an Wahlstellen das Profil als Grund nennen; ist er aus, soll es nicht genutzt werden. Beide Sätze stehen im Katalog beider Sprachen.
13. `engine/reise.py`: `NOCH_NICHT_GEBAUT` wird leer; die Struktur und der Hinweiscode bleiben, die Reiseprüfung warnt bei `profile` nicht mehr.

### Mein Konto

14. `konto_seite` bekommt die Karte „Mein Profil“ (Heimat des Profils, ADR-0003) mit den Einträgen (Bereich, Text, Herkunft, Datum), je Eintrag einem Formular „Text ändern“ und einem Knopf „Löschen“; ohne Einträge ein kurzer Erklärtext, wie Einträge entstehen (über Frieda in der Claude-App, nach Bestätigung). Die Karte erscheint für jedes angemeldete Konto. Das Profil erscheint nirgends sonst (nicht auf der Reiseseite, nicht im Service Worker).
15. Neue POST-Zweige in `bearbeiten()` unter den Herkunfts- und Formularschlüssel-Prüfungen wie die übrigen `/konto`-Zweige: Ändern des Textes (Länge geprüft, `herkunft` bleibt, `datum` wird erneuert) und Löschen. Jede Anweisung wirkt mit `WHERE konto = ?` des angemeldeten Kontos; eine fremde `PR-<n>` ändert nichts. Ein GET löst nichts aus. Es gibt keinen Weg, auf „Mein Konto“ neue Einträge anzulegen (Schreiben nur über den AI-Client, PO 1.11.2026).

### Datenschutz (Art. 9 DSGVO)

16. Ein Absatz `recht.datenschutz.profil` im Datenschutztext (`datenschutz_inhalt`, de und en) sagt: Profileinträge können besondere Angaben enthalten (zum Beispiel zu Gesundheit oder Glauben); ein Eintrag entsteht nur, wenn du ihn im Gespräch ausdrücklich bestätigst, und diese Bestätigung ist deine ausdrückliche Einwilligung; nur du siehst dein Profil, nicht Organisator:innen oder Mitreisende; du kannst jeden Eintrag jederzeit ändern oder löschen; das Profil wird mit dem Konto gelöscht und ist im Export enthalten. Zusätzlich nennt `recht.datenschutz.konto_loeschen` das Profil in der Liste dessen, was mit dem Konto entfällt. Der Wortlaut wird dem PO vorab gezeigt (siehe „Erst zeigen, dann bauen“).
17. Profiltexte (`bereich`, `text`) stehen nie in Logs (stderr zeigt höchstens `PR-<n>` und Konto-Kennung, keinen Inhalt), nie in Meldungen, Push, Mails, der Betreiber-Meldung, Reisedaten, Reiseseite oder Service Worker und nie im Export anderer Personen.

### Export

18. `export_person` (`person.json`) enthält ein Feld `profil` mit den eigenen Einträgen (`id` als `PR-<n>`, `bereich`, `text`, `herkunft`, `datum`); `EXPORT_PUNKTE` und der „Was ist drin?“-Text in Mein Konto nennen das Profil (Schlüssel `konto.export.punkt_4` wird um das Profil ergänzt, de und en). Der Export anderer Personen und die Reise-Ordner der ZIP enthalten nie Profildaten.

### Texte

19. Alle neuen sichtbaren Texte stehen in `texte_de.py` und `texte_en.py` (rund 40 Schlüssel je Sprache: Werkzeugbeschreibungen, Ausgaben, Fehler, Anleitungssätze, Karte, Datenschutzabsatz, Export). Die Ausnahmelisten in `engine/tests/test_texte.py` werden nicht länger. Der deutsche Text hat korrekte Umlaute; die englischen Begriffe folgen dem vorhandenen Katalog.

### Erst zeigen, dann bauen (#436)

20. Die Karte „Mein Profil“ (mit erfundenen Beispieleinträgen von Ida) und der Datenschutzabsatz sind das, was der Product Owner sieht und liest. Sie werden ihm mit der Spec-Freigabe als Entwurf in einem Claude-Artefakt gezeigt; gebaut wird erst nach seiner Zustimmung. Wortlaut und Gestaltung des Entwurfs sind danach verbindlich; Änderungen daran gehen zuerst in den Entwurf.

## Test Plan

### Automated Tests (TDD RED)

Datei `engine/tests/test_profil.py`, eigene Datenbank je Test, Konten Ida und Karl (`beispielreise`) sowie Tom und Lea (`stadtwochenende`), Mails über `FR_MAIL_DATEI`, beide Beispielreisen parametrisiert.

Konten-Funktionen:
- [ ] Test 1: GIVEN ein Konto WHEN ein Eintrag gesetzt wird THEN erscheint er mit `PR-1`, `herkunft` und gesetztem `datum`; GIVEN ein zweiter Eintrag THEN `PR-2`.
- [ ] Test 2: GIVEN der Eintrag `PR-2` ist gelöscht WHEN ein neuer Eintrag entsteht THEN trägt er `PR-3` (Nummer nie wiederverwendet).
- [ ] Test 3: GIVEN leeres `bereich`, `text` oder `herkunft`, zu lange Werte oder die Obergrenze je Konto erreicht WHEN gesetzt wird THEN Fehler mit Text de und en, nichts gespeichert.
- [ ] Test 4: GIVEN Karls Konto WHEN er die `PR-<n>` von Ida ändert oder löscht THEN „nicht gefunden“ und Idas Eintrag unverändert.
- [ ] Test 5: GIVEN ein Konto mit Einträgen WHEN `loeschen(kid)` läuft THEN sind alle seine Profileinträge weg und die anderer Konten unverändert.
- [ ] Test 6: GIVEN zwei Konten mit Einträgen WHEN sie zusammengeführt werden THEN hat das bleibende Konto alle Einträge mit unveränderten Kennungen und es gibt keine Kollision.
- [ ] Test 7: GIVEN eine Datenbank vor der Einführung (ohne Tabelle) WHEN das Schema geöffnet wird THEN entsteht die Tabelle, vorhandene Daten bleiben.

Konnektor-Werkzeuge (de und en, Aliase):
- [ ] Test 8: GIVEN `my_profile` und `mein_profil` WHEN aufgerufen THEN dieselben Einträge des Aufrufers, nie die eines anderen Kontos.
- [ ] Test 9: GIVEN `profile_entry_set` ohne `confirmed=true` oder ohne `herkunft` THEN abgelehnt und nichts geschrieben; mit beiden gespeichert, `datum` von Frieda.
- [ ] Test 10: GIVEN die Schreibgrenze je Konto ist erreicht WHEN `profile_entry_set` THEN abgelehnt; WHEN `profile_entry_remove` THEN trotzdem gelöscht und die Grenze nicht berührt.
- [ ] Test 11: GIVEN die Werkzeugliste (`frieda_werkzeuge`) THEN enthält sie die drei Werkzeuge ohne `reise`-Parameter, mit englischem Namen und deutschem Alias, Beschreibung in beiden Sprachen.
- [ ] Test 12: GIVEN ein Aufruf mit unbekanntem `PR-<n>` THEN Fehlertext ohne Hinweis auf fremde Konten.

Anleitung:
- [ ] Test 13: GIVEN `anleitung_frieda` THEN enthält sie den Satz „nur Bestätigtes eintragen“; Bereichswörter erscheinen nur als Beispiele.
- [ ] Test 14: GIVEN eine Reise mit Baustein `profile` an oder `bausteine` `None` THEN enthält `anleitung()` den Nutzungssatz mit „als Grund nennen“; GIVEN `profile` aus THEN den Satz „nicht nutzen“.
- [ ] Test 15: GIVEN `reise.yaml` mit Baustein `profile` THEN keine Hinweiszeile „noch nicht gebaut“ mehr (`NOCH_NICHT_GEBAUT` leer).

Mein Konto:
- [ ] Test 16: GIVEN Idas Konto mit Einträgen WHEN `/konto` geöffnet wird (de und en) THEN zeigt die Karte „Mein Profil“ nur Idas Einträge; GIVEN Karls Konto THEN sieht er nichts davon.
- [ ] Test 17: GIVEN ein POST „Text ändern“ mit gültiger Herkunft THEN der Text ist geändert, `herkunft` bleibt, `datum` erneuert; GIVEN ein POST „Löschen“ THEN der Eintrag ist weg.
- [ ] Test 18: GIVEN ein POST mit fremder `PR-<n>` THEN ändert er nichts; GIVEN ein POST ohne gültige Herkunft oder Sitzung THEN abgewiesen wie bei den anderen `/konto`-Zweigen; GIVEN GET mit denselben Parametern THEN keine Änderung.
- [ ] Test 19: GIVEN Mein Konto THEN gibt es kein Formular zum Neuanlegen eines Eintrags.

Isolation und Art. 9:
- [ ] Test 20: GIVEN Ida mit Profil und Karl in derselben Reise WHEN Karl alle Werkzeuge der Reise, Reisedaten, Rückmeldungen, Reiseseite, Service Worker und Konnektor-Ausgaben liest THEN kommt kein Profiltext vor; dasselbe für Organisator:in Tom und Mitglied Lea in `stadtwochenende`.
- [ ] Test 21: GIVEN ein Profiltext mit Suchmarke WHEN Setzen, Ändern, Löschen und Export laufen THEN fehlt die Marke in stderr, in Mails, Push, Betreiber-Meldung und in allen Reiseordnern; im Export einer anderen Person kommt sie nicht vor.
- [ ] Test 22: GIVEN `person.json` des Exports von Ida THEN enthält `profil` ihre Einträge mit `PR-<n>`, `bereich`, `text`, `herkunft`, `datum`; der Export von Karl enthält keinen davon; `EXPORT_PUNKTE` nennt das Profil.
- [ ] Test 23: GIVEN die Datenschutzseite (de und en) THEN steht der Absatz `recht.datenschutz.profil` mit den Aussagen aus Punkt 16; die Absätze von #381 und #498 bleiben unverändert.

Texte und Betrieb:
- [ ] Test 24: GIVEN alle neuen Schlüssel THEN in `texte_de.py` und `texte_en.py` vorhanden; `test_texte.py` und `test_rechtliches.py` grün, Ausnahmelisten nicht länger.
- [ ] Test 25: GIVEN `betrieb/deploy.sh` THEN ohne neue Modulzeile; der Modullisten-Test bleibt grün.
- [ ] Test 26: GIVEN `docs/adr/0001-kern.md` THEN enthält der Verlauf die Zeile zum Löschen einzelner Profileinträge (Textprüfung).

Angepasste bestehende Tests: `test_grenzen.py` (freie Werkzeuge), `test_bauen.py` (Baustein-Hinweis), `test_englisch_schnittstelle.py` (Namen und Aliase), `test_oauth.py` (Werkzeuglisten).

Gesamt:
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n 3` grün.

**Instanz-Tests:** Die Werkzeugliste und der Export der Instanz ändern sich. Vor dem Vorspulen auf `main` laufen darum die Tests der einbindenden Instanzen mit dem Branch (Anleitung im Reisen-Repo der Instanz, CLAUDE.md). Abnahme über den Konnektor an einer eigenen Testreise beider Reisetypen (Wanderung und Stadtwochenende), nie an echten Reisen.

## Acceptance Criteria

- **AC-1:** Given ein Konto / When ein gültiger Eintrag mit Herkunft gesetzt wird / Then erscheint er als `PR-<n>` mit Datum von Frieda, Nummern werden nie wiederverwendet, Längen und Anzahl sind begrenzt, und eine ältere Datenbank bekommt die Tabelle ohne Datenverlust (Test 1, 2, 3, 7).
- **AC-2:** Given `profile_entry_set` / When `confirmed=true` oder `herkunft` fehlt / Then wird abgelehnt und nichts gespeichert (Test 9, 12).
- **AC-3:** Given die Schreibgrenze je Konto ist erreicht / When gesetzt oder entfernt wird / Then wird Setzen abgelehnt, Entfernen funktioniert trotzdem und zählt nicht (Test 10).
- **AC-4:** Given der Konnektor eines Kontos / When die Werkzeugliste abgefragt wird / Then gibt es `my_profile` (Alias `mein_profil`), `profile_entry_set` und `profile_entry_remove` als Konto-Werkzeuge ohne `reise`, mit deutschen Aliasen für Werkzeug- und Parameternamen und Beschreibungen in beiden Sprachen (Test 8, 11).
- **AC-5:** Given ein Konto / When `anleitung_frieda` erzeugt wird / Then verlangt sie, nur Bestätigtes einzutragen, und nennt Bereiche höchstens als Beispiele (Test 13).
- **AC-6:** Given eine Reise mit Baustein `profile` an, aus oder ohne `bausteine` / When ihre Anleitung erzeugt wird / Then heißt es bei an oder ohne `bausteine`: Profil nutzen und bei Wahlstellen als Grund nennen, bei aus: nicht nutzen; `NOCH_NICHT_GEBAUT` ist leer (Test 14, 15).
- **AC-7:** Given Ida mit Profileinträgen / When sie Mein Konto öffnet, einen Text ändert oder einen Eintrag löscht / Then zeigt die Karte „Mein Profil“ nur ihre eigenen Einträge, Ändern und Löschen wirken nur mit `WHERE konto=?`, fremde Kennungen ändern nichts, Neuanlegen ist dort nicht möglich (Test 16, 17, 18, 19).
- **AC-8:** Given ein Konto mit Profil / When es gelöscht oder mit einem anderen zusammengeführt wird / Then ist das Profil beim Löschen mit weg und hängt beim Zusammenführen ohne Kollision am bleibenden Konto (Test 5, 6).
- **AC-9:** Given Ida und Karl mit Profilen / When Ida ihre Daten exportiert / Then enthält `person.json` Idas Profil und nie das von Karl (Test 22).
- **AC-10:** Given Ida, Karl, Tom, Lea und Organisator:innen / When jemand Werkzeuge, Seiten oder Reisedaten abruft / Then sieht niemand außer der Person selbst ihr Profil (Test 20).
- **AC-11:** Given ein Profileintrag / When er gesetzt, geändert, gelöscht oder exportiert wird / Then taucht sein Text nie in Logs, Meldungen, Push, Mails oder der Betreiber-Meldung auf (Test 21).
- **AC-12:** Given die Datenschutzseite / When sie auf Deutsch oder Englisch aufgerufen wird / Then enthält sie den Art.-9-Absatz mit ausdrücklicher Einwilligung durch Bestätigung und das Profil in der Liste der Kontolöschung (Test 23).
- **AC-13:** Given die fertige Änderung / When die Tests laufen / Then stehen alle sichtbaren Texte in beiden Sprachkatalogen, Ausnahmelisten sind nicht länger, `deploy.sh` ist unverändert, `docs/konnektor.md`, `docs/produkt.md` und die Verlaufszeile in ADR-0001 sind nachgezogen (Test 24, 25, 26).
- **AC-14:** Given die Spec / When sie freigegeben wird / Then sind Karte „Mein Profil“ und Datenschutzabsatz dem Product Owner vorher als Artefakt-Entwurf gezeigt worden (#436); manuelles Prozess-Kriterium, kein automatisierter Test.

## Definition of Done

- [ ] `engine/.venv/bin/python -m pytest -q engine/tests` grün ohne echte Reisen, `engine/tests/test_profil.py` vorhanden und grün
- [ ] AC-1 bis AC-13 durch die zugeordneten Tests belegt, AC-14 vor dem Bauen erfüllt (Entwurf freigegeben)
- [ ] Texte in `texte_de.py` und `texte_en.py`, Ausnahmelisten in `test_texte.py` nicht länger
- [ ] Doku nachgezogen: `docs/konnektor.md`, `docs/produkt.md`, Verlaufszeile in `docs/adr/0001-kern.md`, Datenschutztext
- [ ] Abnahme über den Konnektor mit einer vorhandenen Testreise beider Reisetypen (Baustein `profile` an und aus), Profil auf Mein Konto ansehen, ändern, löschen
- [ ] Kontolöschung und Export in der Abnahme geprüft: Profil verschwindet mit dem Konto, steht nur im eigenen Export

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue (ADR-0001, ADR-0003, ADR-0005 und ADR-0006 gelten)
- **Rationale:** Das Profil ist ein Kontodatum wie Sitzungen und gehört nicht zur Reise-Ontologie; die Software kennt nur die Form eines Eintrags, keine Kategorien. Die Entscheidung zu Ort, Schreiben, Lesen und Bestätigung hat der Product Owner am 1.11.2026 getroffen; ADR-0001 erhält nur eine klarstellende Verlaufszeile, keine neue Ausnahme.

## Changelog

- 2026-11-15: Initial spec created
