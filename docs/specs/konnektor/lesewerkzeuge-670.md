---
entity_id: lesewerkzeuge-670
type: bugfix
created: 2026-11-24
updated: 2026-11-24
status: draft
workflow: fix-670-lesewerkzeuge
version: "1.0"
tags: [konnektor, readonly, sperre, testzugang, instanz, konten-env]
---

# Lesewerkzeuge mit readOnlyHint und Adressprüfung im Testzugang (#670)

Grundlage: `docs/context/fix-670-lesewerkzeuge.md` (Anfrage, Befunde, Analyse), Issue #670, `docs/specs/betrieb/testkonto-648.md` (Testzugang und Sperre), ADR-0001.

## Approval

- [ ] Approved

## Purpose

Zwei Befunde aus der Validierung von #648 werden behoben. Erstens tragen die reinen Lesewerkzeuge `my_trips` und `my_profile` keine Annotation `readOnlyHint`; die Sperre für Claude-Code-Sitzungen lässt sie deshalb am Konnektor des Product Owners nicht zu, und die Claude-App bekommt keinen Hinweis, dass sie nichts verändern. Zweitens vergleicht `testzugang.py einrichten` das Testkonto mit `FR_BETREIBER_KONTAKT` über `instanz.wert`, der Wert steht aber in `<FR_DIENST>/konten.env`, die `instanz.wert` nicht liest; die Zusatzprüfung greift dort nicht.

## Ziel und Abgrenzung

- **Im Scope:**
  - `MEINE_REISEN` (`my_trips`) und `MEIN_PROFIL` (`my_profile`) in `engine/konnektor.py` bekommen `"annotations": {"readOnlyHint": True}`.
  - `ERLAUBT` in `.claude/hooks/frieda_sperre.py` wird um `my_trips` und `my_profile` ergänzt.
  - Neue eng begrenzte Funktion `konten_wert(name)` in `engine/instanz.py`; `testzugang.einrichten` prüft zusätzlich gegen diesen Wert.
  - Doku: ein Satz in `docs/specs/betrieb/testkonto-648.md` und in `docs/betrieb.md` (Abschnitt „Abnahmen über den Testzugang“).
- **Tech-Lead-Entscheidung, Abweichung vom Issue-Wortlaut („alle drei Werkzeuge“):** `calendar` bekommt bewusst keine Annotation. `calendar` mit `neu=true` ruft `konten.kalender_token(kid, erneuern=True)`: Der Stand des Abos wird hochgezählt, der alte Link gilt nicht mehr, und das ist nicht umkehrbar. Nach der MCP-Spezifikation heißt `readOnlyHint: true`, dass das Werkzeug seine Umgebung nicht verändert; für `calendar` wäre die Annotation falsch, und die Sperre ließe sonst das Widerrufen des Kalenderlinks aus Claude-Code-Sitzungen zu. Teilen in ein lesendes und ein erneuerndes Werkzeug wäre eine Schnittstellenänderung für alle Nutzer ohne Bedarf; der Kalenderlink wird in Claude-Code-Sitzungen nicht gebraucht. Ein Teilen bekäme bei Bedarf ein eigenes Issue. Die Begründung kommt als Kommentar ins Issue #670.
- **Nicht im Scope:**
  - `instanz.wert` auf `konten.env` erweitern: Die Datei enthält Geheimnisse (Mailzugang), `wert` wird überall benutzt.
  - Änderung der Schranke Recht `betreiber`: bleibt unverändert und unabhängig wirksam; die Adressprüfung ist nur eine Zusatzprüfung.
  - Änderung an Werkzeugverhalten: Die Annotation ändert nur Metadaten in `tools/list`.
- **Kern (ADR-0001):** Keine neue Grundform, nichts Reisespezifisches, nichts Instanzspezifisches im Code; der Pfad kommt aus `instanz.dienst()`, der Name der Datei (`konten.env`) ist bereits Instanzvertrag (`betrieb/einstellungen.beispiel`, systemd `EnvironmentFile`).
- **Instanzen:** `tools/list` ändert sich (zwei Annotationen). Vor dem Vorspulen laufen die Tests der einbindenden Instanzen mit dem Zweig (Anleitung im privaten Repo der Instanz).

## Source

- **File:** `engine/konnektor.py`, `.claude/hooks/frieda_sperre.py`, `engine/instanz.py`, `betrieb/testzugang.py`
- **Identifier:** `MEINE_REISEN`, `MEIN_PROFIL`, `ERLAUBT`, `def konten_wert`, `def einrichten`

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/konnektor.py` (`KALENDER`, `MEIN_PROFIL`, `MEINE_REISEN`) | Code | Werkzeugdefinitionen; `KALENDER` bleibt unverändert |
| `engine/schnittstelle.py` (`aussen`) | Code | Zuordnung `meine_reisen`→`my_trips`, `mein_profil`→`my_profile`, `kalender`→`calendar` |
| `.claude/hooks/frieda_sperre.py` | Hook | Erlaubnisliste der Sperre (#648) |
| `engine/instanz.py` (`_lesen`, `wert`, `dienst`) | Code | Parser `NAME=wert`, nur `FR_…`, ohne Shell; Umgebung vor Datei |
| `betrieb/testzugang.py` | Skript | `einrichten` mit Zusatzprüfung der Kontaktadresse |
| `engine/konten.py` (`kalender_token`, `profil_liste`, Recht `betreiber`) | Code | Befund zu `calendar`; Schranke bleibt |
| `betrieb/einstellungen.beispiel`, `betrieb/vorlagen/*.service` | Doku, Vorlage | `konten.env` liegt in `<FR_DIENST>`, Dienste laden sie als `EnvironmentFile` |
| `engine/tests/test_frieda_sperre.py`, `test_testzugang.py`, `test_instanz.py` | Tests | Abgleich Liste und Annotationen; Prüfung der Kontaktadresse; `konten_wert` |
| #648, #670 | Issues | Testkonto und Sperre; dieses Issue |

## Scope

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konnektor.py` | MODIFY | `MEINE_REISEN` und `MEIN_PROFIL` mit `"annotations": {"readOnlyHint": True}`; `KALENDER` unverändert |
| `.claude/hooks/frieda_sperre.py` | MODIFY | `ERLAUBT` um `my_trips`, `my_profile` ergänzen |
| `engine/instanz.py` | MODIFY | Parser auf eine beliebige Datei verallgemeinern, neue Funktion `konten_wert(name)`; `wert` unverändert |
| `betrieb/testzugang.py` | MODIFY | Zusatzprüfung gegen `instanz.wert("FR_BETREIBER_KONTAKT") or instanz.konten_wert("FR_BETREIBER_KONTAKT")` |
| `engine/tests/test_frieda_sperre.py` | MODIFY | `my_trips`, `my_profile` Lesewerkzeuge und erlaubt; `calendar` gesperrt |
| `engine/tests/test_testzugang.py` | MODIFY | Kontaktadresse nur in `konten.env` → verweigert; `konten.env` fehlt → kein Abbruch |
| `engine/tests/test_instanz.py` | MODIFY | Tests für `konten_wert` |
| `docs/specs/betrieb/testkonto-648.md`, `docs/betrieb.md` | MODIFY | je ein Satz: Kontaktadresse auch aus `konten.env`; Erlaubnisliste umfasst die Konto-Lesewerkzeuge |
| `docs/funktionen/` | KEINE ÄNDERUNG | geprüft: dort sind keine Werkzeuganmerkungen (readOnlyHint) beschrieben; für Nutzer:innen ändert sich nichts Sichtbares |

### Estimated Changes

- Files: 8 (davon 3 Tests, 2 Doku)
- LoC: +60/-5
- Risiko: niedrig. Annotation ändert nur Metadaten; die Schranke (Recht `betreiber`) bleibt; Geheimnisse aus `konten.env` gelangen nicht in den allgemeinen Leseweg.

## Implementation Details

1. **Annotationen:** `MEINE_REISEN` und `MEIN_PROFIL` erhalten das Feld wie die übrigen Lesewerkzeuge (Muster: `"annotations": {"readOnlyHint": True}` direkt im Werkzeug-Dict). Beide schreiben nichts (`meine_reisen_konto`, `konten.profil_liste`). `KALENDER` bleibt ohne Annotation.
2. **Sperre:** `ERLAUBT` ergänzt um zwei Namen. `test_erlaubnisliste_entspricht_den_lesewerkzeugen` hält Liste und Annotationen synchron (er wird bis zur Nachziehung rot); `calendar` bleibt gesperrt, weil nicht annotiert.
3. **`konten_wert(name)`:** Umgebung zuerst; sonst `<dienst()>/konten.env` mit demselben Parser wie `_lesen` (`NAME=wert`, nur `FR_…`, keine Shell, Anführungszeichen außen weg). Es wird nur der eine angefragte Name zurückgegeben. Fehlt die Datei oder ist sie nicht lesbar (keine Rechte), ist das Ergebnis `None`, ohne Ausnahme, ohne Ausgabe und ohne Protokollzeile. Es wird nichts gecacht, nichts ausgegeben, nichts geloggt. `instanz.wert` bleibt unverändert und liest `konten.env` nicht.
4. **`testzugang.einrichten`:** Die Zusatzprüfung vergleicht `FR_TESTKONTO` gegen `instanz.wert("FR_BETREIBER_KONTAKT") or instanz.konten_wert("FR_BETREIBER_KONTAKT")` (Umgebung, Einstellungsdatei, `konten.env`). Stimmt die Adresse überein, verweigert `einrichten` wie bisher mit demselben Text. Die Prüfung des Rechts `betreiber` bleibt unverändert.
5. **Doku:** Je ein Satz in `testkonto-648.md` (Abschnitt zu Sperre bzw. Testzugang) und `docs/betrieb.md`: Die Kontaktadresse wird auch aus `konten.env` gelesen; die Erlaubnisliste umfasst `my_trips` und `my_profile`, `calendar` bleibt gesperrt, weil `neu=true` den Link erneuert. Der Satz in `docs/betrieb.md` zu „Lesen über den Konnektor … `readOnlyHint`“ bleibt stimmig.
6. **Ausliefern:** Instanztests mit dem Zweig (Änderung von `tools/list`), dann Pflichtprüfungen der CI, Vorspulen, Konnektor auf dem Server neu starten.

## Test Plan

### Automated Tests (TDD RED)

- [ ] `test_meine_reisen_und_mein_profil_sind_lesewerkzeuge` (`test_frieda_sperre.py`): GIVEN die Werkzeugliste des Konnektors WHEN `my_trips` und `my_profile` gelesen werden THEN tragen beide `readOnlyHint: true` und stehen in `ERLAUBT`; der Hook lässt sie durch (Rückgabecode 0).
- [ ] `test_calendar_bleibt_gesperrt` (`test_frieda_sperre.py`): GIVEN die Werkzeugliste WHEN `calendar` geprüft wird THEN hat es kein `readOnlyHint`, steht nicht in `ERLAUBT`, und der Hook lehnt es mit Rückgabecode 2 und Verweis auf `frieda-test` ab.
- [ ] Bestehend, bleibt grün: `test_erlaubnisliste_entspricht_den_lesewerkzeugen` und `test_hook_entscheidet_fuer_jedes_werkzeug_des_konnektors`.
- [ ] `test_konten_wert_liest_datei_und_entfernt_anfuehrungszeichen` (`test_instanz.py`): GIVEN `<FR_DIENST>/konten.env` mit `FR_BETREIBER_KONTAKT="ida@example.org"` WHEN `konten_wert` aufgerufen wird THEN kommt `ida@example.org` ohne Anführungszeichen zurück.
- [ ] `test_konten_wert_umgebung_vor_datei` (`test_instanz.py`): GIVEN Umgebung und Datei mit verschiedenen Werten WHEN `konten_wert` läuft THEN gewinnt die Umgebung.
- [ ] `test_konten_wert_datei_fehlt_oder_unlesbar` (`test_instanz.py`): GIVEN keine `konten.env` bzw. eine Datei ohne Leserechte WHEN `konten_wert` läuft THEN `None`, keine Ausnahme, keine Ausgabe (`capsys` leer).
- [ ] `test_konten_wert_liefert_nur_den_einen_namen` (`test_instanz.py`): GIVEN `konten.env` mit Mailzugang und Kontaktadresse WHEN `konten_wert("FR_BETREIBER_KONTAKT")` läuft THEN kommt nur dieser Wert zurück; ein Name ohne `FR_`-Präfix, ein fehlender Name und eine Zeile ohne `=` ergeben `None`.
- [ ] `test_wert_liest_konten_env_nicht` (`test_instanz.py`): GIVEN ein Name, der nur in `konten.env` steht WHEN `instanz.wert` läuft THEN `None` bzw. Vorgabe.
- [ ] `test_einrichten_verweigert_kontaktadresse_aus_konten_env` (`test_testzugang.py`): GIVEN `FR_TESTKONTO` ist gleich der Kontaktadresse, die nur in `<FR_DIENST>/konten.env` steht WHEN `einrichten` läuft THEN Verweigerung wie bei der Betreiberadresse, kein Konto angelegt.
- [ ] `test_einrichten_ohne_konten_env_bricht_nicht_ab` (`test_testzugang.py`): GIVEN keine `konten.env` und ein gewöhnliches Testkonto WHEN `einrichten` läuft THEN gelingt es wie bisher.
- [ ] Bestehend, bleibt grün: `test_einrichten_verweigert_betreiberkonto` (Schranke Recht `betreiber`).

## Acceptance Criteria

- **AC-1:** Given der Konnektor / When die Werkzeugliste erzeugt wird / Then tragen `my_trips` und `my_profile` `readOnlyHint: true`. Test: `test_meine_reisen_und_mein_profil_sind_lesewerkzeuge`.
- **AC-2:** Given die Sperre in Claude-Code-Sitzungen / When `my_trips` oder `my_profile` aufgerufen werden / Then lässt der Hook sie zu, und `ERLAUBT` entspricht weiter genau den Lesewerkzeugen. Tests: `test_meine_reisen_und_mein_profil_sind_lesewerkzeuge`, `test_erlaubnisliste_entspricht_den_lesewerkzeugen`.
- **AC-3:** Given `calendar` kann mit `neu=true` den Link erneuern / When die Werkzeugliste und die Sperre geprüft werden / Then hat `calendar` kein `readOnlyHint` und bleibt gesperrt. Test: `test_calendar_bleibt_gesperrt`.
- **AC-4:** Given `konten.env` mit der Kontaktadresse / When `konten_wert` aufgerufen wird / Then gilt Umgebung vor Datei, Anführungszeichen außen entfallen, nur der angefragte Name (nur `FR_…`) wird geliefert. Tests: `test_konten_wert_liest_datei_und_entfernt_anfuehrungszeichen`, `test_konten_wert_umgebung_vor_datei`, `test_konten_wert_liefert_nur_den_einen_namen`.
- **AC-5:** Given die Datei fehlt oder ist nicht lesbar / When `konten_wert` aufgerufen wird / Then ist das Ergebnis `None`, ohne Ausnahme, ohne Ausgabe und ohne Protokollzeile. Test: `test_konten_wert_datei_fehlt_oder_unlesbar`.
- **AC-6:** Given Geheimnisse in `konten.env` / When `instanz.wert` läuft / Then bleiben sie unsichtbar; `wert` liest die Datei nicht. Test: `test_wert_liest_konten_env_nicht`.
- **AC-7:** Given `FR_TESTKONTO` entspricht der Kontaktadresse, die nur in `konten.env` steht / When `testzugang.py einrichten` läuft / Then wird verweigert und kein Konto angelegt. Test: `test_einrichten_verweigert_kontaktadresse_aus_konten_env`.
- **AC-8:** Given keine `konten.env` / When `einrichten` mit gewöhnlichem Testkonto läuft / Then gelingt es wie bisher; die Schranke Recht `betreiber` greift weiter. Tests: `test_einrichten_ohne_konten_env_bricht_nicht_ab`, `test_einrichten_verweigert_betreiberkonto`.
- **AC-9:** Given die Änderung ist fertig / When `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` läuft / Then ist alles grün, ohne echte Reisen; vor dem Vorspulen sind die Tests der einbindenden Instanzen mit dem Zweig grün.

## Definition of Done

- [ ] Rote Tests bestätigt, danach Korrektur, Tests grün
- [ ] Gesamtlauf `engine/.venv/bin/python -m pytest -q -n 3 engine/tests` grün
- [ ] Doku in `testkonto-648.md` und `docs/betrieb.md` nachgezogen; `docs/funktionen/` geprüft (keine Änderung nötig)
- [ ] Tests der einbindenden Instanzen mit dem Zweig gelaufen (`tools/list` ändert sich)
- [ ] Pflichtprüfungen der CI grün, ausgeliefert, Konnektor auf dem Server neu gestartet
- [ ] Issue #670 mit Abschlusskommentar (inklusive Begründung zu `calendar`) geschlossen

## Known Limitations

- `calendar` bleibt in Claude-Code-Sitzungen am Konnektor des Product Owners gesperrt, obwohl der Normalfall (ohne `neu`) nur liest; ein Teilen in zwei Werkzeuge wäre eine eigene Entscheidung (eigenes Issue).
- Die Adressprüfung in `einrichten` ist eine Zusatzprüfung: Fehlt `FR_BETREIBER_KONTAKT` überall (Handaufruf ohne Umgebung und ohne `konten.env`), entscheidet allein das Recht `betreiber`.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Fehlerkorrektur an Metadaten und einer Zusatzprüfung; keine neue Grundform, kein neues Datenformat, keine Änderung der Konten-Architektur (ADR-0005). Die Wahl, `calendar` nicht zu annotieren, folgt aus der MCP-Definition von `readOnlyHint` und ist im Issue begründet.

## Changelog

- 2026-11-24: Initial spec created (Entwurf) für #670.
