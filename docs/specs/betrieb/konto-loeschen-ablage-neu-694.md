---
entity_id: konto-loeschen-ablage-neu-694
type: bugfix
created: 2026-11-27
updated: 2026-11-27
status: draft
workflow: fix-694-konto-loeschen-ablage-neu
version: "1.0"
tags: [datenschutz, loeschen, konten, meldungen, ablage, neue-reise]
---

# Konto löschen räumt auch die Ablage ohne Reise auf (#694)

## Approval

- [ ] Approved

## Purpose

Beim Löschen eines Kontos (`konten.loeschen`) werden Name und Adresse heute nur in den Ablagen der Reisen ersetzt, in denen die Person bleibt. Die Ablage ohne Reise (`rueckmeldungen.ordner_neu()`: `meldungen.jsonl`, `auftraege.jsonl`) und die Datei `neue-reisen-ausstehend.jsonl` des Konnektors behalten Name und Adresse, obwohl #381 zusagt, der eigene Name stehe danach nirgends mehr. Künftig bereinigt `loeschen` diese Dateien vollständig und atomar; eine vorgemerkte, noch nicht veröffentlichte Reise der Person bleibt nicht mehr ohne Besitzer zurück.

## Ziel und Abgrenzung

- **Ausgangslage:** Die Spec `docs/specs/betrieb/loeschen-381.md` nennt in Punkt 27 nur `<FR_ABLAGE>/<reise>/`. Die Ablage ohne Reise wurde dort nicht bedacht. #687 blendet Anfrage-Meldungen nach dem Löschen nur aus; die Zeilen bleiben auf der Platte.
- **Im Scope:**
  - Neue Funktion `_ablage_neu_bereinigen(kid, email, name)` in `engine/konten.py`, aufgerufen in `loeschen` nach `_pseudonymisieren` und vor der Datenbank-Transaktion.
  - `meldungen.jsonl` in `ordner_neu()`:
    - Zeile entfällt: `anfrage_reisen` mit `konto == kid` oder `meldung_adresse(m) == email`; `anfrage_warteliste` mit `meldung_adresse(m) == email`.
    - In `an` wird `kid` entfernt, den Namen (Rückfall alter Meldungen) nur, wenn kein anderes Konto ihn trägt (Muster von `_pseudonymisieren`: lieber nicht ersetzen als den Falschen treffen). Ist `an` danach leer, entfällt die Zeile. Das deckt `neue_reise` und `loeschung` an die Person und die Betreiber:innen-Kennung ab.
  - `auftraege.jsonl` in `ordner_neu()` (bleibt als Beleg, `pfad` wird für `vergebene_pfade` gebraucht):
    - Einträge mit `konto_id == kid`: `name`, `konto` und `daten.neue_reise.personen[*].name` (ganzer Wert gleich dem Namen) werden zu „gelöschte Person“ (Textschlüssel `konto.geloeschte_person`, Sprache der neuen Reise); im `text` wird der Name als ganzes Wort ersetzt (Wortgrenzen, kein Treffer in längeren Wörtern). `pfad` bleibt.
    - Alle Einträge: `einladen`-Einträge mit derselben Adresse (ohne Beachtung der Groß- und Kleinschreibung) werden entfernt. Den Namen aus einem solchen Eintrag (so, wie die einladende Person sie genannt hat) ersetzt Frieda in demselben Auftrag wie oben durch „gelöschte Person“: als ganzen Wert bei der Person mit demselben Schlüssel in `daten.neue_reise.personen` und als ganzes Wort im `text`. Alles Übrige des fremden Auftrags bleibt.
  - `neue-reisen-ausstehend.jsonl` (`konnektor.ausstehend_datei()`): Zeilen mit `konto_id == kid` entfallen; die zugehörige Reise wird mit `loeschung_vormerken(r, None)` zur Löschung vorgemerkt (sie hat nur diese Person, wie bei `allein` in #381 Punkt 22).
  - Umschreiben atomar über Temp-Datei wie `_ablage_pseudonymisieren`, unter einer kleinen Dateisperre `ablage_sperre(ordner)` (`fcntl.flock` auf `<ordner>/.sperre`) in `engine/rueckmeldungen.py`. Die Anhänger nehmen dieselbe Sperre: `meldung_anlegen` und der Konnektor beim Anhängen an `auftraege.jsonl` und `neue-reisen-ausstehend.jsonl`.
  - Fehler (Lesen, Schreiben, Umbenennen) führen zu `KontoFehler("konto.fehler.loeschen_spaeter")`; die Datenbank bleibt unberührt, das Löschen lässt sich später wiederholen.
  - Unlesbare Zeilen bleiben unverändert (wie in `_ablage_pseudonymisieren`); nichts wirft.
  - Der Übergangsort `<Ablage>/_neu` ist über `ordner_neu()` abgedeckt.
- **Nicht im Scope:**
  - `betrieb/zustellen.py` schreibt die Ausstehend-Datei ohne Sperre um (bestehendes Risiko; eigenes Issue, falls nötig).
  - Bereits versandte Mails an Betreiber:innen liegen in deren Postfach (wie in #530 Punkt 12).
  - `status.json` der Ablage (Status und Kommentar je Auftrag) und frei geschriebene Namen jenseits des Auftragstexts.
  - Neue Textschlüssel: keine; `konto.geloeschte_person` besteht in allen Sprachen.
- **Kern (ADR-0001):** Keine neue Grundform, kein Typ, keine Art, kein Merkmal, keine KI. Es geht um Konten und Betrieb, nicht um die Reise-Ontologie. Nichts Reise- oder Instanzspezifisches: Pfade kommen aus `instanz` und `rueckmeldungen.ordner_neu()`. Alle zehn Fragen der Prüfstelle im PR beantworten; keine Frage berührt den Kern, weil die Ontologie unverändert bleibt.
- **Keine Umstellung in `neu.py nachziehen`:** Das Format der Reisedaten ändert sich nicht. Die Ablage ohne Reise und die Ausstehend-Datei sind Betriebsdaten, keine Reisedaten; Felder und Zeilenform bleiben, die Sperrdatei `.sperre` entsteht bei Bedarf und ist kein Datenformat.
- **Beide Beispielreisen:** Wo eine Reise vorkommt, laufen die Tests für `beispielreise` (Ida, Karl) und `stadtwochenende` (Tom, Lea).

## Source

- **File:** `engine/konten.py`
- **Identifier:** `def _ablage_neu_bereinigen` (neu), `def loeschen`; `engine/rueckmeldungen.py`: `def ablage_sperre` (neu), `def meldung_anlegen`; `engine/konnektor.py`: Anhängen an `auftraege.jsonl` und `neue-reisen-ausstehend.jsonl` (`reise_anlegen`)

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `rueckmeldungen.ordner_neu` | Code | Ort der Ablage ohne Reise (auch Übergangsort `<Ablage>/_neu`) |
| `rueckmeldungen.meldung_adresse` | Code | Adresse einer Anfrage-Meldung für den Abgleich |
| `rueckmeldungen.meldung_anlegen` | Code | Anhänger von `meldungen.jsonl`, nimmt künftig die Sperre |
| `konnektor.ausstehend_datei` | Code | Pfad der Datei `neue-reisen-ausstehend.jsonl` |
| `konten.loeschung_vormerken` | Code | Reise ohne Besitzer zur Löschung vormerken (`None` als auslösendes Konto) |
| `konten._pseudonymisieren`, `_ablage_pseudonymisieren` | Code | Muster für Namenszuordnung und atomares Umschreiben |
| `konto.geloeschte_person`, `konto.fehler.loeschen_spaeter` | Textschlüssel | bestehen in allen Sprachen, keine neuen Texte |
| `betrieb/zustellen.py` | Betrieb | liest `auftraege.jsonl` (`konto_id`, `einladen`, Sprache); bleibt unverändert |
| `engine/rueckmeldungen.py` (`meldungen_des_kontos`), `engine/push.py` (`meldungen_aktuell`) | Code | Leser von `meldungen.jsonl`; wirken ohne Änderung mit |
| #381, #687, #530 | Specs | `docs/specs/betrieb/loeschen-381.md`, `docs/specs/konnektor/veraltete-meldungen-687.md`, `docs/specs/betrieb/betreiber-meldung-530.md` |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konten.py` | MODIFY | `_ablage_neu_bereinigen`, Aufruf in `loeschen`, Fehler zu `konto.fehler.loeschen_spaeter` |
| `engine/rueckmeldungen.py` | MODIFY | `ablage_sperre(ordner)`, benutzt in `meldung_anlegen` |
| `engine/konnektor.py` | MODIFY | Anhängen an `auftraege.jsonl` und `neue-reisen-ausstehend.jsonl` unter derselben Sperre |
| `engine/tests/test_loeschen_konto.py` | MODIFY | Tests zu allen Lagen (siehe Test Plan) |
| `docs/specs/betrieb/loeschen-381.md` | MODIFY | Punkt 27 um einen Satz zur Ablage ohne Reise ergänzt, Verweis auf #694 |

### Estimated Changes

- Files: 5 (3 Code, 1 Test, 1 Spec; diese neue Spec zählt nicht mit)
- LoC: rund +70/-5 Code, +100 Tests, +2 Zeilen Spec
- Risiko: mittel (Löschweg und Anhängen von Meldungen); abgefedert durch Tests mit zwei Betreiber:innen, fremden Meldungen und fremden Aufträgen, die byteidentisch bleiben müssen

## Implementation Details

1. `rueckmeldungen.ablage_sperre(ordner)`: Kontextmanager, der `<ordner>/.sperre` anlegt und mit `fcntl.flock(LOCK_EX)` hält. `meldung_anlegen` hängt unter dieser Sperre an, ebenso der Konnektor an die beiden Dateien. Das Umschreiben in `_ablage_neu_bereinigen` nimmt dieselbe Sperre für `ordner_neu()`.
2. `konten._ablage_neu_bereinigen(kid, email, name)`: Liest die drei Dateien zeilenweise (JSON je Zeile), baut die neuen Inhalte im Speicher und schreibt jede Datei über eine Temp-Datei im selben Ordner mit `os.replace`. Unverändert bleibende Dateien werden nicht angefasst (Bytes gleich). Fehlt ein Ordner oder eine Datei, ist das kein Fehler.
3. Ob ein anderes Konto denselben Namen trägt, wird wie in `_pseudonymisieren` geprüft; dann bleibt der Name in `an` stehen.
4. Der Name im `text` der Aufträge wird mit einem Ausdruck mit Wortgrenzen ersetzt (der Name wird maskiert).
5. Die Reisen der gestrichenen Ausstehend-Zeilen werden nach erfolgreichem Schreiben der Dateien mit `loeschung_vormerken(r, None)` vorgemerkt; schlägt ein Schritt davor fehl, wird nichts vorgemerkt und `KontoFehler("konto.fehler.loeschen_spaeter")` geworfen.
6. Die Reihenfolge in `loeschen`: Prüfungen und Sperren wie bisher, `_pseudonymisieren`, `_ablage_neu_bereinigen`, dann die Transaktion der Datenbank. Jeder Fehler der Ablage bricht vor der Transaktion ab.
7. Ausstehende Reise: Die Zeile verschwindet, weil `zustellen.py` sonst bei jedem Lauf an `konto_nicht_gefunden` scheitert; die Reise (nur diese Person) geht mit Schonfrist mit.

## Test Plan

### Automated Tests (TDD RED)

Datei: `engine/tests/test_loeschen_konto.py`, nur erfundene Namen und Adressen (`@beispiel.invalid`), eigene Datenbank und Ablage je Test, Reisen parametrisiert über `beispielreise` und `stadtwochenende`. Rote Tests zuerst gegen den unveränderten Stand.

- [ ] `test_neu_anfrage_reisen_der_person_entfaellt`: GIVEN eine Bitte „Reisen anlegen“ der Person (mit `konto`, dazu eine alte Zeile ohne `konto`, nur mit Adresse) und die Bitte einer anderen Person WHEN das Konto gelöscht wird THEN fehlen die Zeilen der Person und die der anderen bleibt unverändert.
- [ ] `test_neu_anfrage_warteliste_derselben_adresse_entfaellt`: GIVEN ein bestätigter Wartelisten-Eintrag mit Meldung, dazu eine Meldung zu einer anderen Adresse WHEN das Konto mit der Adresse gelöscht wird THEN fehlt die Meldung zur Adresse und die andere bleibt.
- [ ] `test_neu_betreiberin_nur_kennung_aus_an`: GIVEN die Person ist Betreiberin und eine Meldung geht an zwei Betreiber:innen WHEN das Konto gelöscht wird THEN bleibt die Meldung und nur ihre Kennung fehlt in `an`; eine Meldung nur an sie entfällt.
- [ ] `test_neu_neue_reise_an_person_entfaellt`: GIVEN eine Meldung `neue_reise` an die Person (auch im alten Rückfall mit dem Namen in `an`) WHEN das Konto gelöscht wird THEN entfällt sie; trägt ein anderes Konto denselben Namen, bleibt der Name in `an` stehen.
- [ ] `test_neu_auftrag_der_person_pseudonymisiert`: GIVEN ein Auftrag mit `konto_id` der Person, Name, Kürzel, Personennamen und Namen im Text WHEN das Konto gelöscht wird THEN stehen dort „gelöschte Person“ (Name im Text nur als ganzes Wort ersetzt, ein längeres Wort mit dem Namen bleibt) und `pfad` ist unverändert.
- [ ] `test_neu_einladen_mit_adresse_entfernt_fremder_auftrag`: GIVEN der Auftrag einer anderen Person mit der Adresse der gelöschten Person in `einladen` WHEN das Konto gelöscht wird THEN fehlt dieser Eintrag, ihr Name aus dem Eintrag ist bei ihrer Person und im Text „gelöschte Person“, alles andere im Auftrag (auch weitere Einladungen) bleibt.
- [ ] `test_neu_ausstehende_reise_vorgemerkt`: GIVEN eine ausstehende neue Reise der Person (Zeile in `neue-reisen-ausstehend.jsonl`) WHEN das Konto gelöscht wird THEN fehlt die Zeile und die Reise ist zur Löschung vorgemerkt, ohne auslösendes Konto.
- [ ] `test_neu_fremde_zeilen_byteidentisch`: GIVEN Meldungen, Aufträge und Ausstehend-Zeilen nur anderer Personen WHEN ein anderes Konto gelöscht wird THEN sind die Dateien byteidentisch.
- [ ] `test_neu_volltextsuche_ohne_spur`: GIVEN alle Lagen zugleich WHEN das Konto gelöscht wird THEN findet eine Volltextsuche weder Name noch Adresse unter `ordner_neu()` (auch `_neu`) noch in der Ausstehend-Datei.
- [ ] `test_neu_unlesbare_zeilen_bleiben`: GIVEN eine Datei mit kaputten Zeilen WHEN das Konto gelöscht wird THEN bleiben diese Zeilen unverändert und nichts wirft.
- [ ] `test_neu_fehler_bricht_vor_datenbank_ab`: GIVEN ein künstlicher Fehler beim Schreiben (Monkeypatch) WHEN das Konto gelöscht wird THEN kommt `KontoFehler("konto.fehler.loeschen_spaeter")` und das Konto samt Tabellen ist unberührt; ein zweiter Versuch ohne Fehler gelingt.
- [ ] `test_neu_sperre_in_meldung_anlegen`: GIVEN `ablage_sperre` per Monkeypatch protokolliert WHEN `meldung_anlegen` läuft THEN wird die Sperre für `ordner_neu()` genommen.
- [ ] `test_neu_sperre_im_konnektor_anhaengen`: GIVEN dieselbe Protokollierung WHEN `reise_anlegen` an `auftraege.jsonl` und die Ausstehend-Datei anhängt THEN wird die Sperre genommen.
- [ ] `test_neu_bestehende_ablage_der_reisen_unveraendert`: GIVEN die bisherigen Fälle aus `test_ablage_dateien_pseudonymisiert` WHEN das Konto gelöscht wird THEN verhalten sie sich wie bisher.

## Acceptance Criteria

- **AC-1:** Given eine Bitte „Reisen anlegen“ der Person (mit `konto`, alt nur mit Adresse) / When ihr Konto gelöscht wird / Then fehlen die Zeilen, die Bitte einer anderen Person bleibt unverändert. Test: `test_neu_anfrage_reisen_der_person_entfaellt`.
- **AC-2:** Given ein bestätigter Wartelisten-Eintrag derselben Adresse / When das Konto gelöscht wird / Then fehlt die Meldung, andere Adressen bleiben. Test: `test_neu_anfrage_warteliste_derselben_adresse_entfaellt`.
- **AC-3:** Given die Person ist Betreiber:in / When das Konto gelöscht wird / Then fehlt ihre Kennung in `an`, die Meldung an weitere Betreiber:innen bleibt, die nur an sie entfällt. Test: `test_neu_betreiberin_nur_kennung_aus_an`.
- **AC-4:** Given eine Meldung `neue_reise` an die Person / When das Konto gelöscht wird / Then entfällt sie; ein Name, den ein anderes Konto trägt, bleibt in `an`. Test: `test_neu_neue_reise_an_person_entfaellt`.
- **AC-5:** Given ein Auftrag der Person / When das Konto gelöscht wird / Then sind Name, Kürzel, Personenname und Name im Text (ganzes Wort) „gelöschte Person“ und `pfad` bleibt. Test: `test_neu_auftrag_der_person_pseudonymisiert`.
- **AC-6:** Given der Auftrag einer anderen Person mit ihrer Adresse in `einladen` / When das Konto gelöscht wird / Then fehlt dieser Eintrag, ihr Name dort ist „gelöschte Person“, alles andere bleibt. Test: `test_neu_einladen_mit_adresse_entfernt_fremder_auftrag`.
- **AC-7:** Given eine ausstehende neue Reise der Person / When das Konto gelöscht wird / Then fehlt die Zeile und die Reise ist zur Löschung vorgemerkt. Test: `test_neu_ausstehende_reise_vorgemerkt`.
- **AC-8:** Given Zeilen nur anderer Personen / When ein anderes Konto gelöscht wird / Then sind die Dateien byteidentisch. Test: `test_neu_fremde_zeilen_byteidentisch`.
- **AC-9:** Given alle Lagen zugleich / When das Konto gelöscht wird / Then steht weder Name noch Adresse unter `ordner_neu()` noch in der Ausstehend-Datei. Test: `test_neu_volltextsuche_ohne_spur`.
- **AC-10:** Given unlesbare Zeilen / When das Konto gelöscht wird / Then bleiben sie, nichts wirft. Test: `test_neu_unlesbare_zeilen_bleiben`.
- **AC-11:** Given ein Fehler beim Umschreiben / When das Konto gelöscht wird / Then kommt `konto.fehler.loeschen_spaeter`, die Datenbank bleibt unberührt, ein späterer Versuch gelingt. Test: `test_neu_fehler_bricht_vor_datenbank_ab`.
- **AC-12:** Given `meldung_anlegen` und der Konnektor hängen an / When sie laufen / Then nehmen sie `ablage_sperre`. Tests: `test_neu_sperre_in_meldung_anlegen`, `test_neu_sperre_im_konnektor_anhaengen`.
- **AC-13:** Given die bisherigen Ablagen der Reisen / When das Konto gelöscht wird / Then bleibt das Verhalten unverändert. Test: `test_neu_bestehende_ablage_der_reisen_unveraendert`.
- **AC-14:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen; `test_texte.py` bleibt grün (keine neuen Textschlüssel).

## Definition of Done

- [ ] Rote Tests bestätigt (gegen den unveränderten Stand), danach Korrektur, Tests grün
- [ ] Gesamtlauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün
- [ ] `docs/specs/betrieb/loeschen-381.md` Punkt 27 um die Ablage ohne Reise ergänzt (ein Satz, Verweis #694)
- [ ] Prüfstelle (zehn Fragen, ADR-0001) im PR beantwortet
- [ ] Pflichtprüfungen der CI grün (`tests (leer)`, `tests (instanz)`, `gitleaks`), danach `git push origin HEAD:main`
- [ ] Tests der einbindenden Instanzen laufen mit dem Branch (Dateiformat der Ablage ohne Reise berührt)
- [ ] Prüfung am laufenden System nur über den Testzugang `frieda-test`, nie über das Konto des Product Owners; Testreisen danach mit `konten.py vormerken <reise>` entfernt
- [ ] #694 erst nach Auslieferung und Prüfung mit Abschlusskommentar geschlossen

## Known Limitations

- `zustellen.py` schreibt die Ausstehend-Datei ohne Sperre um; ein gleichzeitiges Anhängen kann dort eine Zeile verlieren (bestehendes Risiko).
- Bereits versandte Mails an Betreiber:innen bleiben in deren Postfach.
- Namen, die in `status.json` oder in frei geschriebenen Texten außerhalb des Auftragstexts stehen, werden nicht gesucht.
- Trägt ein anderes Konto denselben Namen, bleibt der Name in `an` stehen (lieber nicht ersetzen als den Falschen treffen).

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Fehlerkorrektur im bestehenden Muster von #381 (Pseudonymisieren der Ablage beim Löschen), ergänzt um eine kleine Dateisperre; keine neue Grundform, keine Änderung der Reisedaten oder der Ontologie, ADR-0001 bleibt unberührt.

## Changelog

- 2026-11-27: Initial spec created (Entwurf) für #694.
- 2026-11-27 (TDD RED): AC-6 ergänzt: In einem fremden Auftrag wird auch der Name ersetzt, unter dem die gelöschte Person eingeladen war (sonst bliebe er trotz AC-9 stehen).
