# Context: fix-670-lesewerkzeuge

## Request Summary
Zwei Befunde aus der Validierung von #648: (1) Die reinen Lesewerkzeuge `my_trips`, `my_profile` und `calendar` tragen
keine Annotation `readOnlyHint: true`; die Sperre für Claude-Code-Sitzungen lässt sie deshalb am Konnektor des Product
Owners nicht zu, und die Claude-App erhält keinen Hinweis, dass sie nichts verändern. (2) `testzugang.py einrichten`
vergleicht `FR_TESTKONTO` mit `FR_BETREIBER_KONTAKT` über `instanz.wert`, der Wert steht aber in `<FR_DIENST>/konten.env`,
die `instanz.wert` nicht liest; die Zusatzprüfung greift dort nicht.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/konnektor.py` (`KALENDER` ~2491, `MEIN_PROFIL` ~2502, `MEINE_REISEN` ~2786) | Werkzeugdefinitionen ohne `annotations`; hier `{"readOnlyHint": True}` ergänzen |
| `.claude/hooks/frieda_sperre.py` (`ERLAUBT`) | Erlaubnisliste der Sperre (#648); muss danach `my_trips`, `my_profile`, `calendar` enthalten |
| `engine/tests/test_frieda_sperre.py` | hält `ERLAUBT` gegen die Lesewerkzeuge des Konnektors synchron (wird rot, bis die Liste nachgezogen ist) |
| `betrieb/testzugang.py` (`einrichten`, Zeile ~182) | Zusatzprüfung gegen `FR_BETREIBER_KONTAKT` |
| `engine/instanz.py` (`_lesen`, `wert`, `dienst`) | liest nur Umgebung und `<FR_DIENST>/instanz/einstellungen.env`; Parser `NAME=wert` ohne Shell |
| `engine/tests/test_testzugang.py` | Fixture `zugang`, Test 2 `test_einrichten_verweigert_betreiberkonto`; neuer Test für die Kontaktadresse aus `konten.env` |
| `betrieb/einstellungen.beispiel` (Z. 147–153) | dokumentiert: Betreiberwerte gehören in `<FR_DIENST>/konten.env` |
| `betrieb/vorlagen/*.service` | laden `konten.env` als `EnvironmentFile` (Dienste sehen den Wert in der Umgebung, Handaufrufe nicht) |
| `docs/betrieb.md` (Abschnitt „Abnahmen über den Testzugang“, Z. ~351) | beschreibt das Verweigern der Betreiberkontakt-Adresse |

## Existing Patterns
- Lesewerkzeuge tragen `"annotations": {"readOnlyHint": True}` direkt im Werkzeug-Dict (viele Beispiele ab Z. 2833).
- Einstellungsdateien: Zeilen `NAME=wert`, nur `FR_…`, ohne Shell-Auswertung, Anführungszeichen außen werden entfernt (`instanz._lesen`).
- Umgebung vor Datei (`instanz.wert`).

## Dependencies
- Upstream: `instanz`, `konten` (Kontenspeicher, Recht `betreiber`), `pruefsitzung`.
- Downstream: Claude-App (tools/list, Bestätigungsdialoge), Sperre-Hook in Claude-Code-Sitzungen, Abnahmen über `frieda-test`.

## Existing Specs
- `docs/specs/betrieb/testkonto-648.md` — Testzugang und Sperre (AC-6, AC-7: Erlaubnisliste gleich Lesewerkzeugen).

## Risks & Considerations
- `konten.env` enthält Geheimnisse (Mailzugang); beim Mitlesen nur den einen Namen übernehmen, nichts ausgeben, Lesefehler (fehlt, keine Rechte) still als „nicht gesetzt“ behandeln.
- Die eigentliche Schranke (Recht `betreiber`) bleibt unverändert und unabhängig davon wirksam.
- Annotation ändert nur Metadaten in tools/list, kein Verhalten der Werkzeuge; `calendar` hat Parameter `neu`, der schreibt (siehe Befund unten).
- Ändert tools/list einer Instanz → Instanztests mit dem Branch laufen lassen (CLAUDE.md).

## Befund beim Sammeln: `calendar` ist nicht rein lesend
`kalender` mit `neu=true` ruft `konten.kalender_token(kid, erneuern=True)` (`engine/konten.py` ~1587): Der Stand des
Abos wird hochgezählt, der alte Link gilt nicht mehr. Das ist eine verändernde, nicht umkehrbare Aktion. Nach der
MCP-Spezifikation heißt `readOnlyHint: true` „verändert seine Umgebung nicht“; die Annotation wäre für `calendar` falsch,
und die Sperre ließe sonst das Widerrufen des Kalenderlinks des Product Owners aus Claude-Code-Sitzungen zu.
`meine_reisen` (`meine_reisen_konto`) und `mein_profil` (`konten.profil_liste`) schreiben nichts.
Folgerung für die Analyse: `calendar` bleibt ohne `readOnlyHint` (oder wird geteilt); nur `my_trips` und `my_profile` erhalten sie.

## Analysis

### Type
Bug (zwei kleine Befunde aus der Validierung von #648). Subagenten-Fan-out bewusst ausgelassen: Kontext vollständig,
Umfang zwei Stellen, alle Fakten oben direkt im Code nachgeprüft.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konnektor.py` | MODIFY | `MEINE_REISEN` und `MEIN_PROFIL` bekommen `"annotations": {"readOnlyHint": True}`; `KALENDER` bleibt ohne (siehe Entscheidung) |
| `.claude/hooks/frieda_sperre.py` | MODIFY | `ERLAUBT` um `my_trips`, `my_profile` ergänzen |
| `engine/tests/test_frieda_sperre.py` | MODIFY | Test: `my_trips`, `my_profile` sind Lesewerkzeuge und erlaubt; `calendar` bleibt gesperrt (ändert per `neu` den Link) |
| `engine/instanz.py` | MODIFY | Parser `_lesen` auf eine Datei verallgemeinern, neue Funktion `konten_wert(name)`: Umgebung, sonst `<dienst()>/konten.env`; Lesefehler still als „nicht gesetzt“; liefert nur den einen angefragten Namen |
| `betrieb/testzugang.py` | MODIFY | Zusatzprüfung nutzt `instanz.wert(...) or instanz.konten_wert("FR_BETREIBER_KONTAKT")` |
| `engine/tests/test_testzugang.py` | MODIFY | neuer Test: Kontaktadresse nur in `<FR_DIENST>/konten.env` → `einrichten` verweigert; fehlende `konten.env` → kein Abbruch |
| vorhandene Tests zu `instanz` | MODIFY | Tests für `konten_wert` (Umgebung vor Datei, Datei fehlt, Anführungszeichen) |
| `docs/specs/betrieb/testkonto-648.md`, `docs/betrieb.md` | MODIFY | ein Satz: Kontaktadresse auch aus `konten.env`; Erlaubnisliste umfasst die Konto-Lesewerkzeuge |

### Scope Assessment
- Files: ~8 (davon 3 Tests, 2 Doku)
- Estimated LoC: +60/-5
- Risk Level: LOW — Annotation ändert nur Metadaten in tools/list; die eigentliche Schranke (Recht `betreiber`) bleibt unberührt; `instanz.wert` bleibt unverändert, Geheimnisse aus `konten.env` gelangen nicht in den allgemeinen Leseweg.

### Technical Approach
1. **Annotationen nur, wo sie stimmen** (MCP: `readOnlyHint` = verändert nichts). `meine_reisen`, `mein_profil` schreiben
   nichts → `readOnlyHint: true`. `kalender` mit `neu=true` widerruft den Abo-Link (nicht umkehrbar) → keine Annotation.
   Entscheidung (Tech Lead): `calendar` nicht teilen. Ein eigenes Werkzeug „Link erneuern“ wäre eine Schnittstellenänderung
   für alle Nutzer ohne Bedarf; der Kalenderlink wird in Claude-Code-Sitzungen nicht gebraucht. Teilen später nur mit eigenem
   Issue. Die Abweichung vom Issue-Wortlaut („alle drei“) wird im Issue begründet.
2. **Sperre:** `ERLAUBT` um die zwei Namen ergänzen; der vorhandene Abgleichtest hält Liste und Annotationen synchron.
3. **Kontaktadresse:** `instanz.wert` bewusst NICHT auf `konten.env` erweitern (Datei enthält Zugangsdaten, `wert` wird
   überall benutzt). Stattdessen eng begrenzte `instanz.konten_wert(name)` mit demselben Parser.
   `testzugang.einrichten` vergleicht gegen Umgebung → Einstellungsdatei → `konten.env`.
4. **Instanz:** tools/list ändert sich (zwei Annotationen) → vor dem Ausliefern Instanztests mit dem Branch.

### Dependencies
- `instanz.dienst()` liefert `<FR_DIENST>`; `konten.env` liegt dort (`betrieb/einstellungen.beispiel` Z. 147–153, systemd `EnvironmentFile`).
- `schnittstelle.aussen`: `meine_reisen`→`my_trips`, `mein_profil`→`my_profile`, `kalender`→`calendar`.
- `test_erlaubnisliste_entspricht_den_lesewerkzeugen` sammelt alle Werkzeug-Dicts aus `konnektor` (Konto-Werkzeuge eingeschlossen).

### Open Questions
- keine (Kalender-Frage als Tech-Lead-Entscheidung oben begründet)
