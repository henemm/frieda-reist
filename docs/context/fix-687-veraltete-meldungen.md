# Context: fix-687-veraltete-meldungen

## Request Summary
Meldungen zu Dingen, die es nicht mehr gibt, sollen verschwinden: „Deine neue Reise … ist angelegt“ zu einer vorgemerkten oder entfernten Reise (#687) und Anfragen an die Betreiber (Warteliste, Bitte „Reisen anlegen“), die entschieden sind oder deren Konto bzw. Eintrag nicht mehr besteht (#693, Punkt 1).

## Entscheidungen
- #693 Punkt 2, Product Owner, 24.11.2026: **Meldung kommt weiter.** Keine Ausnahme für Adressen des Testpostfachs; die Meldung verschwindet über Punkt 1. Deckt sich mit der bekannten Grenze in der Spec zu #648.
- Beide Issues in einem Workflow und einem PR (Wortlaut des Auftrags: „los“ auf die Empfehlung, #687 und #693 zusammen).

## Ursache (aus dem Code hergeleitet, noch nicht per Test nachgestellt)
- `rueckmeldungen.meldungen_des_kontos` übernimmt aus der Ablage ohne Reise alles aus `meldungen_aktuell(o, k["id"])`. Dort fallen nur Meldungen älter als 14 Tage weg (Aufgaben und Status gibt es ohne Reise nicht).
- #687: `neue_reise` wird nie gegen `konten.reise_vorgemerkt(ziel)` geprüft. `konten.mitgliedschaften` behält vorgemerkte Reisen bis zum endgültigen Entfernen, deshalb ist die Meldung sogar noch mit der Reise verknüpft. Meldungen aus der Reise selbst fallen schon weg, weil `ordner(reise)` bei vorgemerkten Reisen None liefert.
- #693: `anmeldung.betreiber_melden` speichert `ziel="reise"` ohne Bezug zur Anfrage; niemand vergleicht mit `konten.anfragen()` oder `konten.warteliste()`.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/rueckmeldungen.py` (`meldungen_des_kontos`, `meldungen_aktuell`, `meldung_anlegen`) | Ort der gemeinsamen Prüfung; `meldung_anlegen` hat `extra` für weitere Felder |
| `engine/anmeldung.py` (`betreiber_melden`, Aufrufe in `/warteliste/bestaetigen/` und Aktion `anfragen`) | legt die Anfrage-Meldungen an; Bezug ergänzen |
| `engine/konten.py` (`anfragen`, `warteliste`, `reise_vorgemerkt`, `freischalten`, `freigeben`, `loeschen`, `adresse_aendern`, `zusammenfuehren`) | Wahrheit über offene Anfragen und Reisen |
| `betrieb/zustellen.py` | legt `neue_reise` an, `ziel` ist die Kennung der Reise; keine Änderung nötig |
| `engine/push.py` (`sammeln_ohne_reise`, `mail_rueckfall`) | liest die Ablage selbst, sammelt neue Meldungen gleich ein; `mail_rueckfall` betrifft nur Reisen |
| `docs/konten.md`, `docs/konnektor.md`, `docs/funktionen/erinnerungen.md` | Nutzersicht „Meldungen verschwinden …“ nachziehen |

## Existing Patterns
- Gefiltert wird beim Lesen, `meldungen.jsonl` wird nur angehängt (`meldungen_aktuell`: erledigte Aufgabe, vollzogener Statuswechsel).
- `konten.reise_vorgemerkt` ist die eine Abfrage für „Reise gilt als nicht vorhanden“ (vorgemerkt oder im Löschprotokoll).
- `extra` in `meldung_anlegen` für zusätzliche Felder (`status_bei`).

## Dependencies
- Upstream: `konten` (Datenbank), `instanz.neu()`.
- Downstream: `konnektor.meine_reisen_konto` (my_trips), `anmeldung.meldungen_abschnitt`, `meldung_oeffnen`, Aktion `meldungen_gelesen`. Alle lesen `meldungen_des_kontos`; eine Änderung dort wirkt überall.

## Existing Specs
- `docs/specs/oberflaeche/meldungen-konto-407.md`, `docs/specs/betrieb/warteliste-push-631.md`, `docs/specs/betrieb/warteliste-382.md`, `docs/specs/betrieb/testkonto-648.md` (bekannte Grenze Betreiber-Meldungen)

## Vorhandene Tests mit Bezug
- `engine/tests/test_anmeldung.py` um Z. 606 und 635–637: `betreiber_melden` **ohne** echte Bitte in `anfragen`; Z. 637 erwartet die Meldung danach sichtbar. Der Test muss die Bitte künftig wirklich stellen (`reisen_anlegen_anfragen`).
- `engine/tests/test_anmeldung.py` Z. 420, 624: `neue_reise` zu Reisen ohne Mitgliedschaft (`winterwoche`), muss sichtbar bleiben (nicht vorgemerkt).
- `engine/tests/test_warteliste.py` Z. 329, 588 (Tagesgrenze, Art `betrieb`), `test_loeschen_reise.py` Z. 327 (Meldung `loeschung`): unverändert sichtbar.
- `engine/tests/test_push.py` Z. 592–757: Push ohne Reise, soll unverändert grün bleiben.

## Risks & Considerations
- **Schlüssel der Bitte:** Konto-Kennung als eigenes Feld, weil `adresse_aendern` die Adresse ändert. Warteliste: Adresse ist der Schlüssel der Tabelle. `KENNUNG`/`bezug` nicht dafür nutzen (wird zur Sprungmarke).
- **Altmeldungen ohne das neue Feld:** Adresse steht in `t` (`email`, seit #407 Stufe C). Altmeldungen ohne `t`: in der Analyse entscheiden (laufen nach 14 Tagen ohnehin ab). Keine Umstellung in `neu.py nachziehen` nötig, wenn Altes lesbar bleibt (Ablage ohne Reise, keine Reisedaten); bestätigen.
- **Zurückholen einer Reise:** Meldung muss wieder erscheinen; Filter beim Lesen erfüllt das.
- **Warteliste erneut eingetragen:** Nach Löschen und neuem Bestätigen derselben Adresse würde die alte Meldung wieder gelten; gegebenenfalls Zeit vergleichen.
- **Mehrere Betreiber:** Entscheidet eine Person, verschwindet die Meldung bei allen.
- **Push und Tageszusammenfassung:** eingereihte Nachrichten können eine inzwischen erledigte Anfrage nennen. In der Analyse entscheiden, ob das in den Umfang gehört (Vorschlag: nein, Spec #631 bleibt).
- **Nur lesen:** `reise_vorgemerkt` und Anfragen dürfen ohne Datenbank nichts anlegen; nicht je Meldung eine Abfrage, sondern Mengen einmal laden (`vorgemerkte_reisen()`).
- **Nebenbefund (nicht Teil dieser Aufgabe, noch zu prüfen):** `konten.loeschen` will jede Spur des Kontos entfernen, die Zeilen der Anfrage-Meldungen mit Name und Adresse in `<Konten>/neu/meldungen.jsonl` scheinen aber zu bleiben (`_ablage_pseudonymisieren` läuft nur über Reiseordner). Bestätigt sich das, eigenes Issue.

## Analysis

### Type
Bug (#687 und #693 Punkt 1, eine Ursache). Analyse direkt im Code und mit einem Wegwerf-Test, ohne Teilagenten: Ursache und Dateien standen schon im Kontext.

### Nachgestellt (24.11.2026, Wegwerf-Test gegen den unveränderten Stand)
| Lage | Meldung heute | erwartet |
|------|---------------|----------|
| Reise vorgemerkt | `neue_reise` sichtbar | weg |
| Reise endgültig entfernt (Löschprotokoll) | `neue_reise` sichtbar | weg |
| Bitte „Reisen anlegen“ freigeschaltet | `anfrage_reisen` sichtbar | weg |
| Konto der Bitte gelöscht | `anfrage_reisen` sichtbar | weg |
| Warteliste freigegeben | `anfrage_warteliste` sichtbar | weg |
| Wartelisten-Eintrag gelöscht | `anfrage_warteliste` sichtbar | weg |

Nicht nachgestellt: Ablehnen, Zusammenführen und Zurückholen. Die ersten beiden laufen über denselben Weg (`konten.anfragen()` enthält die Bitte dann nicht mehr); alle drei gehören in die Tests.

### Root Cause
`rueckmeldungen.meldungen_des_kontos` fragt für Meldungen ohne Reise nur nach dem Alter (`meldungen_aktuell`), nie nach dem Ding, um das es geht. Anfrage-Meldungen tragen außerdem keinen Bezug zu ihrer Anfrage, nur Text und Adresse in `t`.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/rueckmeldungen.py` | MODIFY | kleine Funktion „gilt die Meldung ohne Reise noch?“, in `meldungen_des_kontos` auf die Ablage ohne Reise angewendet |
| `engine/anmeldung.py` | MODIFY | `betreiber_melden` speichert bei der Bitte die Konto-Kennung (`extra={"konto": k["id"]}`) |
| `engine/tests/test_meldungen_veraltet.py` | CREATE | Tests zu allen Lagen, Konnektor und Mein Konto |
| `engine/tests/test_anmeldung.py` | MODIFY | zwei Tests (um Z. 606 und 635) stellen die Bitte wirklich (`reisen_anlegen_anfragen`) |
| `docs/funktionen/erinnerungen.md`, `docs/konnektor.md` (Absatz zu `meldungen_des_kontos`, Z. 195), `docs/konten.md` | MODIFY | je ein Satz |

### Scope Assessment
- Files: 2 Code, 2 Tests, 3 Doku (Doku nur Sätze)
- Estimated LoC: rund +25/-3 Code, +120 Tests
- Risk Level: LOW (nur Anzeige, nichts wird gelöscht; eine Quelle für Konnektor und Mein Konto)

### Technical Approach
Filter beim Lesen, Maßstab: **Eine Anfrage-Meldung gilt genau so lange, wie die Anfrage unter „Freischaltungen“/„Warteliste“ auf Mein Konto steht** (`konten.anfragen()`, `konten.warteliste()`).
1. `neue_reise`: weg, wenn `ziel` in `konten.vorgemerkte_reisen()`. Zurückgeholt: erscheint wieder. Nicht auf Mitgliedschaft prüfen (bestehende Tests mit `winterwoche`).
2. `anfrage_reisen`: gilt, wenn `konto` unter den offenen Anfragen; ohne Feld `konto` (Altmeldung) über `email` aus `t` (Teil `konto.meldungen.text.anfrage_reisen`).
3. `anfrage_warteliste`: gilt, wenn `email` aus `t` in `konten.warteliste()` steht. Kein neues Feld nötig (Adresse ist Schlüssel der Tabelle).
4. Ohne Feld und ohne `t` nicht zuzuordnen: bleibt stehen, bis die 14 Tage um sind (nichts ohne Beleg verstecken). Echte solche Meldungen sollte es nicht mehr geben: `t` ist seit 8.11.2026 im Code (Stand der Instanz nicht geprüft).
5. Alle anderen Arten (`betrieb`, `loeschung`, …) unverändert. `art` mit `ziel="reise"` bleibt; `bezug` nicht benutzen.
6. Mengen je Aufruf höchstens einmal laden und nur, wenn eine passende Art vorliegt. Fehler in den Daten (`t` unlesbar) werfen nie, sondern zählen als „nicht zuzuordnen“.

`meldungen_aktuell` bleibt unverändert (auch für Reisen und `push.mail_rueckfall`); die Prüfung sitzt in `meldungen_des_kontos`. `neue_reise_gesehen` braucht nichts.

### Entscheidungen der Analyse
- **Keine Umstellung in `neu.py nachziehen`:** Ablage ohne Reise sind keine Reisedaten, alte Zeilen bleiben lesbar (Punkte 2 und 4).
- **Push und tägliche Zusammenfassung:** nicht im Umfang. Schon eingereihte Nachrichten können eine gerade erledigte Anfrage nennen; Spec #631 bleibt.
- **Warteliste, selbe Adresse erneut bestätigt:** keine Zeitprüfung. Die alte Meldung kann innerhalb der 14 Tage wieder erscheinen; sie stimmt dann inhaltlich (es gibt einen offenen Eintrag). Bekannte Grenze.
- **Adresse geändert bei Altmeldung ohne `konto`:** Meldung verschwindet, die Bitte steht weiter unter Freischaltungen. Bekannte Grenze, endet nach 14 Tagen.
- **Zweimal gebeten:** heute entstehen zwei Meldungen; beide verschwinden mit der Entscheidung. Keine Änderung.
- **Recht direkt gesetzt** (`recht_setzen`, Freigabe über die Warteliste): die Bitte bleibt in `konten.anfragen()` offen, also bleibt auch die Meldung. Gleiches Verhalten wie der Abschnitt Freischaltungen, keine Änderung.
- **Gelesen:** Zahl der gelesenen Meldungen in `my_trips` sinkt mit; gewollt.

### Dependencies
`konten.vorgemerkte_reisen`, `konten.anfragen`, `konten.warteliste` gibt es alle schon; keine neuen Module, `betrieb/deploy.sh` unverändert. Texte unverändert (kein neuer Schlüssel im Katalog). Nichts Sichtbares wird neu gestaltet, also kein Entwurf im Artefakt nötig.

### Befunde, die gegen den Plan sprechen
Keine. Geprüft (gelesen): bestehende Tests mit Meldungen ohne Reise (siehe oben) und die Leser `konnektor.meine_reisen_konto`, `anmeldung.meldungen_abschnitt`, `meldung_oeffnen` (404 bei nicht mehr gültiger Meldung, passt), `meldungen_gelesen`.

### Nebenbefunde (eigene Issues, nicht Teil dieser Aufgabe)
- Bestätigt: Nach `konten.loeschen` stehen Name und Adresse der Person weiter in `<Konten>/neu/meldungen.jsonl`.
- Bestätigt: War eine Person freigeschaltet und wurde ihr das Recht später entzogen, endet `trip_create_request` (`reisen_anlegen_anfragen`) im Konnektor mit `KeyError: 'freigeschaltet'` (`konnektor.frieda_werkzeug`).

### Open Questions
Keine.
