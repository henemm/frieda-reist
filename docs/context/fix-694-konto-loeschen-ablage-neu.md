# Kontext: #694 Konto löschen – Name und Adresse bleiben in der Ablage ohne Reise

## Request Summary

Nach `konten.loeschen(kid)` stehen Name und Adresse der Person weiter in `<Konten>/neu/` (Ablage ohne Reise,
`instanz.neu()`, übergangsweise `<Ablage>/_neu`). `_ablage_pseudonymisieren` läuft nur über die Ablagen der Reisen, in
denen die Person bleibt (`_pseudonymisieren(kid, bleiben)`). Erwartet: Beim Löschen verschwinden Name und Adresse auch
in `neu/meldungen.jsonl`, in Meldungen zur Warteliste (`anfrage_warteliste`) und in `neu/auftraege.jsonl`.

Spec #381 (`docs/specs/betrieb/loeschen-381.md`, Ziel Z. 20) sagt zu: „der eigene Name steht danach nirgends mehr“.
Punkt 27 nennt nur `<FR_ABLAGE>/<reise>/`; `neu/` wurde dort vergessen.

## Related Files

| Datei | Stelle | Rolle |
|---|---|---|
| `engine/konten.py` | `ABLAGE_NAMENSFELDER` Z. 583, `_ablage_pseudonymisieren` Z. 586, `_pseudonymisieren` Z. 619, `loeschen` Z. 652 | Ort der Änderung |
| `engine/rueckmeldungen.py` | `ordner_neu` Z. 139, `meldung_anlegen` Z. 309, `ohne_reise_gilt` Z. 432, `meldungen_des_kontos` Z. 449, `auftraege` Z. 513, `meldung_adresse` | Format und Leser der Meldungen ohne Reise |
| `engine/anmeldung.py` | `betreiber_melden` Z. 1927 (Warteliste Z. 1761) | schreibt `anfrage_reisen` (Text und `t` mit Name und Adresse, `extra.konto`) und `anfrage_warteliste` (Adresse in Text und `t`) an alle Betreiber |
| `engine/anmeldung.py` | Z. 775 | Meldung `loeschung` an ein Konto (`an=[kid]`), Text mit dem Namen der auslösenden Person (`wer`) |
| `betrieb/zustellen.py` | Z. 38–90 | liest `auftraege.jsonl` (`konto_id`, `einladen`, Sprache) und schreibt `neue_reise` an `konto_id` (Rückfall: Name) |
| `engine/konnektor.py` | `reise_anlegen` Z. 2432–2480, `vergebene_pfade` Z. 2340 | schreibt `auftraege.jsonl`: `name`, `konto` (Kürzel aus dem Namen), `konto_id`, `text` (Namen aller Personen), `daten.neue_reise.personen` (Namen), `einladen` [{email, name, …}] |
| `engine/tests/test_loeschen_konto.py` | `_spuren` Z. 37, `test_ablage_dateien_pseudonymisiert` Z. 236 | bestehende Tests, hier ergänzen |
| `engine/tests/test_meldungen_veraltet.py` | `test_bitte_konto_geloescht_verschwindet` | #687: Meldung wird nach Löschen nur ausgeblendet, die Zeile bleibt auf der Platte |

## Was in `neu/` personenbezogen steht

- `meldungen.jsonl`
  - `anfrage_reisen`: `text` und `t` mit Name und Adresse der bittenden Person, `konto` = Kennung (seit #687), `an` = Betreiber-Kennungen.
  - `anfrage_warteliste`: Adresse in `text` und `t`; zum Konto gehört sie über die gleiche Adresse.
  - `loeschung`, `neue_reise`: `an` = Kennung des Kontos (bei `neue_reise` alter Rückfall: Name); `loeschung` nennt im Text den Namen einer anderen Person (`wer`).
  - ist die gelöschte Person Betreiber:in, steht ihre Kennung in `an` vieler Meldungen.
- `auftraege.jsonl`: Name, Kürzel und Kennung der anlegenden Person, Namen aller Personen in `text` und `daten`, Adressen eingeladener Personen in `einladen`.
- `status.json` der Ablage (`status_setzen`): Status und Kommentar je Auftrag.

## Existing Patterns

- `_ablage_pseudonymisieren`: ersetzt Werte bekannter Felder (`ABLAGE_NAMENSFELDER`) in JSON/JSONL-Dateien, atomar über Temp-Datei, lässt Unlesbares unverändert.
- `_pseudonymisieren` ermittelt die Namen über den Personen-Schlüssel und lässt Namen stehen, die ein anderes Mitglied trägt („lieber nicht ersetzen als den Falschen treffen“).
- `loeschen` bricht mit `KontoFehler("konto.fehler.loeschen_spaeter")` ab, wenn das Umbenennen scheitert; die Datenbank wird erst danach abgeräumt.
- #687 blendet Anfrage-Meldungen aus, deren Bitte nicht mehr offen ist; gelöscht wird dort nichts.

## Dependencies / Dependents

- Leser von `neu/meldungen.jsonl`: `meldungen_des_kontos` (Mein Konto, Konnektor `meine_reisen`), `push.py` Z. 315 (Benachrichtigungen), Konnektor-Überblick der Betreiber.
- Leser von `neu/auftraege.jsonl`: `vergebene_pfade` (nur `pfad`), `zustellen.py` (`konto_id`, `einladen`, Sprache), Konnektor-Status der Anfragen.
- Datenschutztext `recht.datenschutz.*` (alle Sprachen) sagt „bleiben, bis du dein Konto löschst“.

## Existing Specs

- `docs/specs/betrieb/loeschen-381.md` (Konto und Reise löschen)
- `docs/specs/konnektor/veraltete-meldungen-687.md` (Ausblenden veralteter Meldungen)
- `docs/specs/betrieb/betreiber-meldung-530.md` Punkt 12 (Tabellen beim Löschen)

## Risks

- Zu viel löschen: Meldungen an andere Betreiber:innen oder Aufträge anderer Personen gehen verloren (z. B. eine Wartelisten-Adresse, die zufällig gleich ist; ein Auftrag, der noch zugestellt werden muss).
- Zu wenig: Name steht frei formuliert im `text` (Auftrag, Meldung `loeschung`); ein reines Feld-Ersetzen trifft ihn nicht.
- Gleichzeitiges Schreiben: `meldung_anlegen` hängt ohne Sperre an; ein Umschreiben der Datei während eines Anhängens kann eine Zeile verlieren.
- Übergangsort `<Ablage>/_neu` muss mit abgedeckt sein (über `ordner_neu()`).
- Vorgemerkte Reisen nur dieser Person: ihr Auftrag bleibt für `vergebene_pfade` nötig (Pfad), nicht der Name.

## Analysis

**Type:** Bugfix (Datenschutzlücke beim Löschen eines Kontos, #381 unvollständig)

**Root Cause:** `konten.loeschen` (engine/konten.py Z. 652) ruft nur `_pseudonymisieren(kid, bleiben)` auf, und das läuft
ausschließlich über `instanz.ablage() / reise` der Reisen in `bleiben` (Z. 586–649). `rueckmeldungen.ordner_neu()` und
die Datei `neue-reisen-ausstehend.jsonl` im Ordner des Konnektors kommen nirgends vor. #687 blendet die Anfragen nur aus.

**Zusätzlicher Befund (strategische Bewertung):** Eine Reise, die die Person angelegt hat und die noch nicht
veröffentlicht ist, hat noch keine Mitgliedschaft (die verknüpft erst `betrieb/zustellen.py` über `konten.verknuepfen`).
Sie fällt deshalb weder unter `allein` noch unter `bleiben`. Nach dem Löschen bleibt sie ohne Besitzer stehen, und
`zustellen` scheitert bei jedem Lauf an `konto_nicht_gefunden`.

### Affected Files

| Datei | Change | Was |
|---|---|---|
| `engine/konten.py` | MODIFY | neue Funktion `_ablage_neu_bereinigen(kid, email, name)`, Aufruf in `loeschen` nach `_pseudonymisieren` und vor der Transaktion, Fehler → `KontoFehler("konto.fehler.loeschen_spaeter")` |
| `engine/rueckmeldungen.py` | MODIFY | kleine Dateisperre `ablage_sperre(ordner)` (fcntl.flock auf `<ordner>/.sperre`), benutzt in `meldung_anlegen` |
| `engine/konnektor.py` | MODIFY | Anhängen an `auftraege.jsonl` und `neue-reisen-ausstehend.jsonl` unter derselben Sperre |
| `engine/tests/test_loeschen_konto.py` | MODIFY | Tests (siehe unten) |
| `docs/specs/betrieb/loeschen-381.md` | MODIFY | Punkt 27 um die Ablage ohne Reise ergänzt, Verweis #694 |

### Technical Approach (Variante B der Bewertung, plus offene Reise)

1. `meldungen.jsonl` in `ordner_neu()`:
   - Zeile weg: `anfrage_reisen` mit `konto == kid` oder `meldung_adresse(m) == email`; `anfrage_warteliste` mit `meldung_adresse(m) == email`.
   - `an`: `kid` entfernen; den Namen nur, wenn kein anderes Konto ihn trägt (Muster von `_pseudonymisieren`). Ist `an` danach leer, Zeile weg.
2. `auftraege.jsonl` in `ordner_neu()` (bleibt als Beleg, `pfad` wird für `vergebene_pfade` gebraucht):
   - Einträge mit `konto_id == kid`: `name`, `konto` und `daten.neue_reise.personen[*].name` (ganzer Wert gleich dem Namen) → „gelöschte Person“ (Katalog, Sprache der neuen Reise). Im `text` den Namen als ganzes Wort ersetzen (Regex mit Wortgrenzen, kein Treffer in längeren Namen).
   - Alle Einträge: `einladen`-Einträge mit derselben Adresse (casefold) entfernen.
3. `neue-reisen-ausstehend.jsonl` (`konnektor.ausstehend_datei()`, Pfad über `KN_AUSSTEHEND`/instanz): Zeilen mit `konto_id == kid` entfernen, die Reise mit `loeschung_vormerken(r, None)` zur Löschung vormerken (sie hat nur diese Person, wie `allein`).
4. Umschreiben atomar über Temp-Datei wie `_ablage_pseudonymisieren`, unter `ablage_sperre`; Appender nehmen dieselbe Sperre, damit keine gleichzeitig angehängte Zeile verloren geht.

### Scope / Risk

- 5 Dateien, etwa 70 LoC Code, 100 LoC Tests, 10 Zeilen Spec. Liegt innerhalb der Grenzen.
- Risiko mittel: Löschweg und Anhängen von Meldungen. Abgefedert durch Tests mit zwei Betreibern, fremden Meldungen und fremden Aufträgen, die byteidentisch bleiben müssen.
- Nicht im Scope: `zustellen.py` schreibt die Ausstehend-Datei ohne Sperre um (bestehendes Risiko, eigenes Issue, falls nötig). Bereits versandte Mails liegen im Postfach des Betreibers (wie in #530 Punkt 12).

### Tests (RED)

- Bitte „Reisen anlegen“ der Person (mit `konto` und eine alte ohne `konto`, nur Adresse) → Zeilen weg; Bitte einer anderen Person bleibt unverändert.
- Bestätigter Wartelisten-Eintrag derselben Adresse → Meldung weg.
- Person ist Betreiberin, Meldung an zwei Betreiber → Meldung bleibt, nur ihre Kennung fehlt in `an`; Meldung nur an sie → weg.
- Meldung `neue_reise` an sie → weg.
- Auftrag der Person → Name, Kürzel, Personenname und Text ohne Namen, `pfad` bleibt; Auftrag einer anderen Person mit ihrer Adresse in `einladen` → nur dieser Eintrag fehlt.
- Ausstehende neue Reise der Person → Zeile weg, Reise zur Löschung vorgemerkt.
- Nach allem steht weder Name noch Adresse irgendwo unter `ordner_neu()` und in der Ausstehend-Datei (Volltextsuche).
- Sperre: `meldung_anlegen` nimmt `ablage_sperre` (Test über Monkeypatch).
- Beide Beispielreisen parametrisiert, wo eine Reise vorkommt.

### Open Questions

Keine Produktfrage: Die Zusage aus #381 („der Name steht nirgends mehr“) und die Datenschutzseite („bleiben, bis du dein Konto löschst“) legen das Verhalten schon fest.
