---
entity_id: warteliste-push-631
type: bugfix
created: 2026-11-19
updated: 2026-11-19
status: draft
workflow: fix-631-warteliste-push
version: "1.0"
tags: [push, betreiber, warteliste, zusammenfassung, m7]
---

# Push und Tageszusammenfassung für Meldungen ohne Reise (#631)

## Approval

- [ ] Approved

## Purpose

Wenn jemand auf der Warteliste seine Adresse bestätigt oder in der Claude-App um eine neue Reise bittet, landet die Meldung für die Betreiber in der Ablage ohne Reise (`<Konten>/neu/meldungen.jsonl`). Der Push-Dienst liest bisher nur Reiseordner; diese Meldungen erreichen die Betreiber deshalb nie aufs Handy und nie in der täglichen Zusammenfassung. Mit dieser Spec liest der Dienst auch die Ablage ohne Reise und behandelt die Meldungen wie alle anderen Anfragen: Push in der Gruppe `rueckmeldungen` mit Ruhezeit, je nach Einstellung auch in der täglichen Mail, einmal je Eintrag, nichts Altes.

Auftrag des Product Owners im Issue #631 (Owner des Repos). Kontext und Analyse: `docs/context/fix-631-warteliste-push.md`. Das ist ein Fehler, kein neues Merkmal: Der Kopf von `engine/push.py` sagt schon zu, dass Anfragen zur Gruppe `rueckmeldungen` gehören und aufs Handy kommen.

## Ziel und Abgrenzung

- **Im Scope:**
  - Neue Funktion `sammeln_ohne_reise(jetzt)` in `engine/push.py`, aufgerufen von `sammeln()`; eigener Stand-Schlüssel `meldungen:_neu` in `push_stand`.
  - Empfänger: die Kennungen in `an`, die ein bestehendes, nicht gesperrtes Konto sind. Ein Name als Rückfall (Meldung `neue_reise` ohne Kennung) wird übersprungen.
  - Text in der Sprache des Empfängers (`rm.meldung_text_in(m, sprache_von(kid))`, sonst der gespeicherte Text).
  - `nachricht()` und `zusammenfassungen()` können mit `reise == ""` umgehen: Titel aus dem Textkatalog, Ziel Mein Konto.
  - `sammeln_fuer_mail` ohne Reise: gilt die Vorgabe `meldekanal` (enthält `mail`) statt `zustand("")`.
  - Neue Textschlüssel in `engine/texte_de.py` und `engine/texte_en.py` (jede künftige `texte_<kürzel>.py` folgt `docs/sprachen.md`).
  - Tests in `engine/tests/test_push.py`; Abschnitt Push in `docs/betrieb.md`.
- **Nicht im Scope:**
  - Keine Änderung an `betreiber_melden` und `zustellen.py`, am Format von `neu/meldungen.jsonl`, an `engine/app/sw.js` und am Rückmeldedienst.
  - Kein Nachschicken alter Meldungen; kein Telegram- und kein MQ-Alarm (nur Ausfälle, Regel der Instanz).
  - Keine neue Einstellung auf Mein Konto: es gelten die vorhandenen der Gruppe `rueckmeldungen`.
  - Keine Änderung an `mail_rueckfall` (betrifft nur wichtige Meldungen in Reisen).
- **Bewusst mit drin:** `neue_reise` (Link zur neuen Reise) und `loeschung` (Hinweis zur Löschung) fallen durch dieselbe Lücke und laufen deshalb über denselben Weg; `kategorie("meldung", m)` ordnet sie der Gruppe `rueckmeldungen` zu.
- **Kern (ADR-0001):** Betrieb, keine Ontologie. Der Dienst liest und stellt zu, er deutet nichts, ändert keine Reise und enthält keine KI. Keine Grundform und kein Merkmal einer Reise sind berührt.
- **Instanzen:** Nichts Instanzspezifisches: Empfänger sind Konten der Meldung, Adressen kommen aus `konten.basis()`, der Titel aus dem Katalog. Keine echten Reisen, Namen, Adressen oder Pfade in Spec, Tests und Beispielen.
- **Keine Umstellung in `neu.py nachziehen`:** Weder Reisedaten noch Dateiformate ändern sich; `betrieb/deploy.sh` bleibt unverändert (`push.py` ist schon in der Liste, kein neues Modul).

## Source

- `engine/push.py`: `sammeln` (Z. 310), `sammeln_reise` (Z. 252, Vorbild), `neue` (Z. 175), `_jsonl` (Z. 159), `einreihen` (Z. 232), `kategorie` (Z. 99), `sprache_von` (Z. 247), `seite_von` (Z. 316), `titel_von` (Z. 329), `ziele` (Z. 337), `nachricht` (Z. 348), `zustellen` (Z. 364, gruppiert schon je `reise`), `sammeln_fuer_mail` (Z. 560), `zusammenfassungen` (Z. 574), `_mail_an` (Z. 517).
- `engine/rueckmeldungen.py`: `ordner_neu` (Z. 131), `meldung_text_in` (Z. 328).
- `engine/anmeldung.py`: `betreiber_melden` (schreibt die Meldung mit `art` `anfrage_warteliste` oder `anfrage_reisen` nach `neu/`); Mein Konto mit den Stellen `id="freischalten"` und `id="meldungen"`; Meldung `loeschung` (Z. 755).
- `betrieb/zustellen.py`: Meldung `neue_reise` (an Kennung, Rückfall Name).
- `engine/texte_de.py`, `engine/texte_en.py`: `push.*` (Z. ~3310 bis 3321 in de).
- `engine/tests/test_push.py`: vorhandene Fixtures `reise` und `welt`.

## Verhalten

1. **Sammeln.** `sammeln(jetzt)` ruft zusätzlich `sammeln_ohne_reise(jetzt)` auf und zählt dessen vorgemerkte Nachrichten mit. Es liest `rm.ordner_neu()/meldungen.jsonl` mit `_jsonl` und filtert mit `neue(…, "meldungen:_neu")`. Gibt es die Ablage nicht (`ordner_neu()` ist `None`), geschieht nichts.
2. **Erster Lauf nur merken.** Hat `push_stand` für `meldungen:_neu` noch keinen Eintrag, merkt `neue` den Stand und liefert nichts. Auch bei fehlender Ablage oder leerer Datei bleibt kein Altes übrig: Sobald Meldungen dazukommen, zählen nur die neuen.
3. **Empfänger.** Für jede neue Meldung gilt: jeder Eintrag in `an`, der eine Konto-Kennung ist und mit `konten.konto(kid)` ein bestehendes Konto mit `gesperrt == 0` ergibt. Alles andere (Namen, unbekannte Kennungen, gesperrte Konten) wird übersprungen, ohne Fehler. Doppelte Einträge in `an` zählen einmal.
4. **Einreihen.** Je Empfänger: `einreihen(kid, "", "meldung", text, ziel, jetzt, kategorie("meldung", m))`. Damit gelten die vorhandenen Regeln unverändert: Push nur, wenn die Gruppe `rueckmeldungen` für das Konto an ist und es ein Gerät mit Abo hat; ist die Mail der Gruppe auf `taeglich`, kommt der Eintrag zusätzlich in die Sammlung der Zusammenfassung.
5. **Text.** `rm.meldung_text_in(m, sprache_von(kid))`, wenn vorhanden, sonst `m["text"]`. Die Sprache ist die des Empfängers.
6. **Ziel.** Anfragen an Betreiber (`anfrage_warteliste`, `anfrage_reisen`) führen zu `freischalten` auf Mein Konto, alle anderen Meldungen ohne Reise (`neue_reise`, `loeschung`) zu `meldungen`.
7. **Nachricht ohne Reise.** `nachricht(kid, "", eintraege)` liefert als Titel `texte.t(sprache, "push.titel_ohne_reise")`, als `url` `konten.basis() + "/konto#" + ziel` (ohne Basisadresse: nur `/konto#…`), als `tag` `frieda-konto`. Bei mehreren Einträgen gilt der vorhandene Text `push.mehrere` mit Ziel `meldungen`. `zustellen` bündelt weiter je `reise` (hier `""`), die Ruhezeit des Kontos hält die Nachricht zurück und lässt sie danach als eine Nachricht kommen. `ziele(abos, "")` nimmt je Gerät das zuletzt aufgefrischte Abo.
8. **Zusammenfassung ohne Reise.** In `sammeln_fuer_mail` entscheidet bei `reise == ""` die Vorgabe `rg.VORGABEN["meldekanal"]` (enthält `mail`) statt `rm.zustand("")`. In `zusammenfassungen` bekommt der Eintrag ohne Reise eine eigene Überschrift aus dem Katalog (`push.mail.zusammenfassung.ohne_reise`) und, falls `konten.basis()` gesetzt ist, den Link auf Mein Konto statt einer Reiseseite.
9. **Einmal je Eintrag.** Der Stand in `push_stand` und die vorhandene Warteschlange sorgen dafür: Ein zweiter Lauf ohne neue Meldungen stellt nichts vor; ein Eintrag steht höchstens einmal in der Warteschlange und höchstens einmal in der Zusammenfassung.
10. **Gleicher Weg für alle Arten.** `anfrage_warteliste`, `anfrage_reisen`, `neue_reise` und `loeschung` werden gleich behandelt; es gibt keinen Sonderfall je Art außer dem Ziel (Punkt 6).

## Sichtbare Texte (de/en)

Alle Texte stehen im Katalog (`engine/texte_de.py` und `engine/texte_en.py`, nie im Code, ADR-0006). Neue Schlüssel stehen in allen vorhandenen `texte_<sprache>.py` mit gleichen Platzhaltern; die Ausnahmelisten in `engine/tests/test_texte.py` werden nicht länger.

| Schlüssel | Deutsch | English |
|---|---|---|
| `push.titel_ohne_reise` | Frieda | Frieda |
| `push.mail.zusammenfassung.ohne_reise` | Konto und Anfragen | Account and requests |

Die Titel sind Entwurf; weil beide Texte der Betreiber lesen, nicht die Reisenden, genügt die Vorlage durch Claude im PR (kein neuer Text für Reisende).

## Fehlerverhalten

- **Keine Ablage, leere oder kaputte Zeilen:** `_jsonl` überspringt kaputte Zeilen; nichts wird vorgemerkt, kein Fehler.
- **Namen statt Kennung, unbekanntes oder gesperrtes Konto:** übersprungen (Punkt 3).
- **Kein Gerät oder Gruppe aus:** kein Push (Regel von `einreihen`); die Meldung bleibt auf Mein Konto und in der Claude-App wie bisher.
- **Push-Dienst nicht erreichbar:** vorhandene Wiederholung (`MAX_VERSUCHE`, `MAX_ALTER`) gilt unverändert.
- **Datenschutz:** Der Text der Meldung kann die Mailadresse der anfragenden Person enthalten (`konto.meldungen.text.anfrage_reisen`). Er geht nur an Betreiber-Konten: als Web Push ende-zu-ende verschlüsselt an deren Geräte und, auf Wunsch, in deren eigene Zusammenfassung. Betreiber haben diese Angaben schon auf Mein Konto; die Spec ändert nicht, wer sie sieht.
- **Sicherheit:** Der Text ist Nutzdaten: Er wird nur gekürzt (`_kurz`) und angezeigt, nie ausgewertet.

## Was darf sich nicht ändern

- Meldungen in Reiseordnern, Rückmeldungen, Aufgaben, Versionen und die Mails für wichtige Meldungen (`mail_rueckfall`) verhalten sich wie bisher.
- Die Zusammenfassung für Reisen (Überschrift mit Titel und Seite) bleibt gleich; die Reihenfolge der Reisen in der Mail ändert sich nicht.
- Format von `neu/meldungen.jsonl`, `push_stand`, `push_warteschlange` und `konten.db`-Schema.
- Beide Beispielreisen (`beispiel/reisen/beispielreise`, `beispiel/reisen/stadtwochenende`): Die Meldungen ohne Reise hängen an keiner Reise; die Tests prüfen, dass der Lauf mit beiden Reisen im Bestand unverändert bleibt.

## Acceptance Criteria

- **AC-1 (Warteliste, Push):** Gegeben ein Betreiber-Konto Ida mit Gerät und Gruppe `rueckmeldungen` an, ein erster Lauf hat den Stand gemerkt, wenn danach eine Meldung `anfrage_warteliste` mit `an = [Idas Kennung]` in `neu/meldungen.jsonl` steht und `lauf` läuft, dann steht genau eine Nachricht in der Warteschlange (`reise = ""`, `art = "meldung"`), und `zustellen` schickt sie an Idas Gerät.
- **AC-2 (Reisen anlegen, Push):** Gegeben dieselbe Lage, wenn eine Meldung `anfrage_reisen` ankommt, dann geht ebenso genau eine Nachricht an Idas Gerät; ein zweiter Betreiber Karl mit Gerät bekommt seine eigene.
- **AC-3 (Titel und Ziel):** Gegeben eine zugestellte Nachricht ohne Reise, dann ist der Titel `push.titel_ohne_reise` in der Sprache des Kontos (de und en), die URL ist `<basis>/konto#freischalten` bei `anfrage_*` und `<basis>/konto#meldungen` bei `neue_reise` und `loeschung`, und der `tag` ist `frieda-konto`; die Nachricht ist nicht leer betitelt und zeigt nicht auf `#reise`.
- **AC-4 (Ruhezeit):** Gegeben Idas Uhr liegt in ihrer Ruhezeit, dann bleibt die Nachricht in der Warteschlange (`warten` zählt sie), und nach dem Ende der Ruhezeit kommt sie als eine Nachricht.
- **AC-5 (Gruppe aus):** Gegeben Ida hat die Gruppe `rueckmeldungen` für Push ausgeschaltet, dann entsteht keine Nachricht in der Warteschlange; ohne Gerät ebenso keine.
- **AC-6 (Mail täglich):** Gegeben Ida hat die Mail der Gruppe `rueckmeldungen` auf `taeglich`, wenn eine Meldung ohne Reise ankommt und `zusammenfassungen` nach `ZUSAMMENFASSUNG_UM` läuft, dann enthält die Mail den Text unter der Überschrift `push.mail.zusammenfassung.ohne_reise` (nicht unter dem Titel einer Reise) und, mit gesetzter Basisadresse, den Link auf Mein Konto; mit Mail `nie` fehlt der Eintrag. Auch ohne Gerät erreicht der Eintrag die Zusammenfassung.
- **AC-7 (Erster Lauf nur merken):** Gegeben es liegen schon Meldungen in `neu/` und der Dienst hat noch keinen Stand, wenn der erste Lauf geschieht, dann entsteht keine Nachricht und kein Eintrag für die Zusammenfassung; nur Meldungen danach kommen an.
- **AC-8 (Kein Doppelversand):** Gegeben eine Meldung wurde gesammelt, wenn `lauf` ein zweites und drittes Mal ohne neue Meldung läuft, dann entsteht keine weitere Nachricht und kein weiterer Eintrag in der Zusammenfassung; zwei Meldungen in derselben Sekunde gehen beide durch (Verhalten von `neue`).
- **AC-9 (Empfänger):** Gegeben eine Meldung mit `an` = [Kennung eines gesperrten Kontos, Kennung eines unbekannten Kontos, ein Name als Rückfall, Idas Kennung], dann entsteht genau eine Nachricht, nämlich an Ida; die anderen werden ohne Fehler übersprungen.
- **AC-10 (Gleicher Weg):** Gegeben Meldungen der Arten `neue_reise` (mit Kennung) und `loeschung` in `neu/`, dann werden sie wie `anfrage_*` in der Gruppe `rueckmeldungen` vorgemerkt (gleiche Einstellungen, gleiche Ruhezeit, gleicher Titel), mit Ziel `meldungen`; eine `neue_reise` mit Namen statt Kennung erzeugt nichts.
- **AC-11 (Sprache des Empfängers):** Gegeben eine Meldung mit Textteilen (`t`) und zwei Betreiber, einer deutsch, einer englisch, dann ist der Text jeder Nachricht in der Sprache ihres Empfängers; ohne Teile gilt der gespeicherte Text.
- **AC-12 (Nichts Weiteres ändert sich):** Die bestehenden Tests in `engine/tests/test_push.py` bleiben unverändert grün; Reisemeldungen, Rückmeldungen, Aufgaben, Versionen und `mail_rueckfall` verhalten sich wie vorher; `betrieb/deploy.sh` und `neu.py` bleiben unverändert.
- **AC-13 (Texte vollständig):** Beide neuen Schlüssel stehen in `texte_de.py` und `texte_en.py`; `test_texte.py` (Parität, Platzhalter, Literal-Test, Ausnahmelisten, Pseudo-Sprache) bleibt grün; im Code stehen keine deutschen Literale.
- **AC-14 (Abnahme auf der Instanz):** Nach dem Ausliefern, nur mit einem Testkonto der Instanz und nie an echten Reisen: Eine Probe-Bestätigung auf der Warteliste und eine Bitte „Reisen anlegen“ lösen je einen Push beim Betreiber-Gerät aus (Klick öffnet Mein Konto); Ergebnis als Kommentar in #631.

## Test Plan

Datei `engine/tests/test_push.py` (erweitert, Fixtures `welt` und `reise` wiederverwenden). Nur erfundene Konten (Ida und Karl als Betreiber, ein gesperrtes Konto, ein Konto ohne Betreiberrecht), Meldungen werden mit `rm.meldung_anlegen(rm.ordner_neu(anlegen=True), …)` angelegt, Texte über die Hilfen aus `conftest.py` statt kopierter Sätze, mindestens ein Test mit beiden Beispielreisen im Bestand. Die RED-Phase schreibt die Tests vor der Umsetzung.

### Automated Tests (TDD RED)

- [ ] `test_warteliste_meldung_geht_als_push_an_betreiber`: GIVEN Betreiber Ida mit Gerät, Stand gemerkt WHEN `anfrage_warteliste` in `neu/` und `lauf` THEN eine Nachricht, zugestellt an Idas Gerät. (AC 1)
- [ ] `test_bitte_reisen_anlegen_geht_als_push`: GIVEN Ida und Karl mit Gerät WHEN `anfrage_reisen` THEN je eine Nachricht. (AC 2)
- [ ] `test_nachricht_ohne_reise_hat_titel_und_ziel_mein_konto` (de und en): GIVEN eine wartende Nachricht mit `reise = ""` WHEN `nachricht(kid, "", …)` THEN Titel aus `push.titel_ohne_reise`, URL `…/konto#freischalten` bei `anfrage_*`, `…/konto#meldungen` sonst, `tag` `frieda-konto`. (AC 3)
- [ ] `test_ruhezeit_haelt_meldung_ohne_reise_zurueck`: GIVEN Uhr in der Ruhezeit WHEN `zustellen` THEN `warten` zählt, nichts gesendet; danach nach Ruhezeitende eine Nachricht. (AC 4)
- [ ] `test_gruppe_rueckmeldungen_aus_kein_push`: GIVEN Gruppe aus WHEN Meldung THEN keine Zeile in `push_warteschlange`; ebenso ohne Gerät. (AC 5)
- [ ] `test_mail_taeglich_nimmt_meldung_ohne_reise_mit_eigener_ueberschrift`: GIVEN Mail `taeglich` WHEN `zusammenfassungen` nach 07:30 THEN Mail mit Überschrift `push.mail.zusammenfassung.ohne_reise`, Text, Link; Mail `nie` ohne Eintrag; auch ohne Gerät. (AC 6)
- [ ] `test_erster_lauf_merkt_nur`: GIVEN Altbestand in `neu/` WHEN erster Lauf THEN nichts in Warteschlange und Sammlung; eine Meldung danach kommt an. (AC 7)
- [ ] `test_kein_doppelversand`: GIVEN eine gesammelte Meldung WHEN zwei weitere Läufe THEN keine neue Zeile; zwei Meldungen derselben Sekunde gehen beide durch. (AC 8)
- [ ] `test_nur_bestehende_nicht_gesperrte_konten`: GIVEN `an` mit gesperrtem, unbekanntem, Namen und Ida WHEN Lauf THEN genau eine Nachricht an Ida. (AC 9)
- [ ] `test_neue_reise_und_loeschung_laufen_denselben_weg`: GIVEN `neue_reise` (Kennung und Name) und `loeschung` WHEN Lauf THEN Kennung und Löschung als Nachricht (Ziel `meldungen`), Name nichts. (AC 10)
- [ ] `test_text_in_sprache_des_empfaengers`: GIVEN Meldung mit Teilen, ein deutscher und ein englischer Betreiber WHEN Lauf THEN je Sprache der Text des Katalogs; ohne Teile der gespeicherte Text. (AC 11)
- [ ] `test_bestand_mit_beiden_beispielreisen_unveraendert`: GIVEN beide Beispielreisen in der Ablage WHEN Lauf mit und ohne Meldungen in `neu/` THEN Reiseergebnisse gleich, nichts Doppeltes. (AC 12)
- [ ] `test_neue_texte_in_allen_sprachen`: beide Schlüssel in allen Sprachen aus `texte.SPRACHEN`, gleiche Platzhalter. (AC 13)

Gesamt:
- [ ] `engine/.venv/bin/python -m pytest -q engine/tests -n 3` grün; die bestehenden Tests unverändert grün.

**Instanz-Tests:** Die Änderung betrifft den Push-Lauf, den auch die einbindenden Instanzen nutzen. Vor dem Vorspulen auf `main` laufen darum die Tests der einbindenden Instanzen mit dem Branch (Anleitung im privaten Reisen-Repo der Instanz, CLAUDE.md); die öffentliche CI führt private Tests nicht aus.

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `konten.db`: `push_abos`, `push_einstellungen`, `push_warteschlange`, `push_stand` | Datenbank, gelesen und geschrieben | Geräte, Einstellungen, Warteschlange, Stand je Quelle |
| `rueckmeldungen.ordner_neu`, `rueckmeldungen.meldung_text_in` | Code, nur gelesen | Ablage ohne Reise, Text je Sprache |
| `konten.konto`, `konten.basis` | Code, nur gelesen | Prüfung des Empfängers (vorhanden, nicht gesperrt), Basisadresse für den Link |
| `texte` | Code, geändert (zwei Schlüssel) | Titel und Überschrift im Katalog |
| `reise.VORGABEN["meldekanal"]` | Konstante, nur gelesen | Mail-Kanal ohne Reise |
| `anmeldung.betreiber_melden`, `betrieb/zustellen.py` | Code, nur gelesen | Quellen der Meldungen (`anfrage_*`, `neue_reise`, `loeschung`) |
| `engine/app/sw.js` | Code, nicht geändert | Klick auf eine Adresse derselben Herkunft öffnet Mein Konto |
| Push-Dienste der Browser | Fremd | Zustellung über Web Push |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/push.py` | MODIFY | `sammeln_ohne_reise`, `sammeln` ruft es auf, `nachricht`/`titel_von`/URL für `reise == ""`, `sammeln_fuer_mail` und `zusammenfassungen` ohne Reise |
| `engine/texte_de.py` | MODIFY | `push.titel_ohne_reise`, `push.mail.zusammenfassung.ohne_reise` |
| `engine/texte_en.py` | MODIFY | dieselben zwei Schlüssel, englisch |
| `engine/tests/test_push.py` | MODIFY | Tests nach Test Plan |
| `docs/betrieb.md` | MODIFY | Abschnitt Push: auch Meldungen ohne Reise (Anfragen an Betreiber, neue Reise, Löschung) |

### Estimated Changes

- Files: 5
- LoC: etwa +60/-3 Code, +90 Tests, +6 Texte und Doku. Risiko niedrig bis mittel: zentraler Push-Lauf, aber nur additiv, eigener Stand-Schlüssel, erster Lauf merkt nur.

## Implementation Details

Generisch statt Sonderfall: Alle Meldungen in `neu/` an Konto-Kennungen laufen durch denselben Mechanismus wie die in Reiseordnern (`neue`, `kategorie`, `einreihen`, Einstellungen, Ruhezeit). Die Warteschlange trägt `reise = ""`; `zustellen` gruppiert schon je `reise`, daher kommen solche Nachrichten gebündelt als eine eigene Nachricht. `ziele(abos, "")` nimmt je Gerät das zuletzt aufgefrischte Abo. Der Service Worker öffnet ein Ziel derselben Herkunft im vorhandenen Fenster, in `sw.js` ändert sich nichts. Ältere Abos auf Reiseseiten öffnen Mein Konto in einem neuen Fenster, das ist hinnehmbar. Nur ein Datenformat bleibt, wie es ist; es gibt nichts nachzuziehen.

Fehlt die Ablage ohne Reise noch (`ordner_neu()` ist `None`), zählt sie als leer: `neue([], "meldungen:_neu")` merkt beim ersten Lauf den leeren Stand. So geht die erste Meldung nach dem Anlegen der Ablage nicht als „Altbestand“ verloren (Verhalten 1 und 2; geprüft über die Fixture `betrieb` in `engine/tests/test_push.py`, RED-Phase).

## Prüfstelle (ADR-0001, zehn Fragen, im PR zu beantworten)

Keine Grundform und kein Merkmal berührt (Fragen zu Arten und Merkmalen entfallen); nichts Reisespezifisches in der Engine, Einstellungen bleiben beim Konto; beide Beispielreisen laufen unverändert (Punkt „Was darf sich nicht ändern“); keine KI, der Dienst deutet nichts; Texte im Katalog aller Sprachen; kein Format der Reisedaten betroffen, also keine Umstellung in `neu.py nachziehen`; nichts Instanzspezifisches. Kein Widerspruch zum Kern.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue (bestehend: ADR-0001 und ADR-0006)
- **Rationale:** Fehlerbehebung innerhalb des vorhandenen Push-Entwurfs; weder Grundform noch Datenformat ändern sich (ADR-0001), sichtbare Texte stehen im Katalog (ADR-0006). Die ADRs werden nicht geändert.

## Definition of Done

- [ ] Alle Punkte des Test Plans umgesetzt und grün; `engine/tests` insgesamt grün (Pflichtprüfungen `tests (leer)`, `tests (instanz)`, `gitleaks`).
- [ ] Alle Acceptance Criteria durch Tests oder den Abnahmeschritt auf der Instanz belegt.
- [ ] Texte in allen Sprachen; Ausnahmelisten in `test_texte.py` nicht länger.
- [ ] Die Tests der einbindenden Instanzen laufen mit dem Branch, vor dem Vorspulen auf `main`.
- [ ] `docs/betrieb.md` ergänzt; `deploy.sh` unverändert.
- [ ] Nach dem Ausliefern: Abnahme nach AC 14, Ergebnis im Issue #631, Issue erst danach schließen.
- [ ] Die Prüfstelle (zehn Fragen, ADR-0001) ist im PR beantwortet.

## Changelog

- 2026-11-19: Initial spec created (v1.0) aus Kontext `docs/context/fix-631-warteliste-push.md` und Issue #631.
