# Context: feat-534-warteliste-tagesgrenze

## Request Summary
Die Warteliste nimmt je Kalendertag (UTC) höchstens N Einträge an, die eine Bestätigungsmail auslösen (Vorgabe 20, `FR_GRENZE_WARTELISTE_TAG`). Darüber eine freundliche Seite „Heute sind alle Plätze vergeben, bitte morgen wieder“, keine Mail, nichts gespeichert; der Betreiber bekommt einmal je Tag eine Meldung über Mein Konto. Grund: Resend Free, 100 Mails/Tag für alle Dienste (Entscheidung des PO, 12.11.2026, #384).

## Related Files
| File | Relevance |
|------|-----------|
| engine/konten.py | `warteliste_eintragen` (Z. ~834): Prüfungen vor dem Schreiben, `_begrenzt` und Tabelle `versand` (Schlüssel, Zeit; Zeilen älter als 24 h werden gelöscht), `WARTELISTE_MAX_UNBESTAETIGT` als bestehende Obergrenze mit `KontoFehler("konto.fehler.warteliste_voll")`; `loeschen` räumt `versand`-Schlüssel je Adresse |
| engine/instanz.py | `_grenze(name, vorgabe)`, `grenze_reisen()`, `grenze_schreiben()`: Muster für `grenze_warteliste_tag()` mit `VORGABE_GRENZE_WARTELISTE_TAG = 20` |
| engine/anmeldung.py | Weg `/warteliste` (POST, Z. ~1418): `KontoFehler` → Formular mit Fehlersatz; sonst immer derselbe Satz `warteliste.gesendet`. `betreiber_melden(k, art, text, teile)` legt Meldungen an alle Betreiber an (Mein Konto und `meine_reisen`), Beispiel `anfrage_warteliste`; `MELDUNG_WARM`, `meldung_ziel` |
| engine/rueckmeldungen.py | `meldung_anlegen`, `meldungen_des_kontos`: Quelle für Mein Konto und `meine_reisen` |
| engine/texte_de.py, texte_en.py (+ alle `texte_*.py`) | `konto.fehler.*`, `warteliste.*`, `konto.meldungen.text.<art>`, `konto.meldungen.art.<art>`, `konto.betreiber.*` |
| engine/tests/test_warteliste.py | bestehende Tests der Warteliste (Fixtures, `FR_MAIL_DATEI`) |
| docs/konten.md (Abschnitt Warteliste, Tabelle der Umgebungswerte), docs/betrieb.md (Tabelle FR_GRENZE_*), betrieb/einstellungen.beispiel | Doku des neuen Werts |

## Existing Patterns
- Begrenzung über Zeilen in `versand` (`_begrenzt(v, schluessel, (anzahl, sekunden))`) – gleitendes Fenster; für den Kalendertag reicht eine Zählung ab Mitternacht UTC (Zeilen < 24 h alt bleiben erhalten).
- Grenzen der Instanz: `instanz._grenze` mit Vorgabe, ungültig/kleiner 1 = Vorgabe; Wert aus Umgebung oder `konten.env`.
- Ablehnung auf der Seite: `KontoFehler(schluessel)` → `warteliste_seite(email, satz)`.
- Meldung an Betreiber: `betreiber_melden(None, art, text_vorgabesprache, teile)` wie bei `anfrage_warteliste`.
- Die Warteliste verrät nie den Stand einer Adresse: Begrenzungen werden vor jeder Unterscheidung nach dem Stand geprüft.

## Dependencies
- Upstream: `instanz.wert`, `versand`-Tabelle, `texte`, `rueckmeldungen.meldung_anlegen`.
- Downstream: Seite `/warteliste`, Mein Konto und `meine_reisen` der Betreiber, Monitor (Resend-Teil-Check bleibt unverändert).

## Existing Specs
- docs/specs zur Warteliste (#382) und Konten (ADR-0005).

## Risks & Considerations
- Erneutes Eintragen einer unbestätigten Adresse schickt ebenfalls eine Mail: für das Kontingent zählt jede Bestätigungsmail, nicht nur neue Zeilen.
- Grenzprüfung nicht vor Adressprüfung platzieren, die den Stand verrät; bestätigte Adressen bekommen ohnehin keine Mail – Zählung nur für versendete Mails, Ablehnung aber unabhängig vom Stand, damit nichts verraten wird.
- Betreiber-Meldung nur einmal je UTC-Tag (Merker in `versand`), nicht bei jedem abgelehnten Versuch.
- Freigaben (`freigeben`) zählen nicht.
- Texte in allen Sprachen; Ausnahmelisten in test_texte dürfen nicht wachsen.

## Analysis

### Type
Feature

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/instanz.py | MODIFY | `VORGABE_GRENZE_WARTELISTE_TAG = 20`, `grenze_warteliste_tag()` über `_grenze("FR_GRENZE_WARTELISTE_TAG", …)` |
| engine/konten.py | MODIFY | `_tagesbeginn()` (Mitternacht UTC von `_jetzt()`); in `warteliste_eintragen` nach der Adress-/IP-Begrenzung und VOR den `versand`-Einträgen: Zählung `versand`-Schlüssel `warteliste-tag` seit Tagesbeginn ≥ Grenze → `KontoFehler("konto.fehler.warteliste_tag_voll")`, unabhängig vom Stand der Adresse. Nach Entscheidung „Mail geht raus“ (neue oder erneute unbestätigte Adresse) Zeile `warteliste-tag` einfügen. Neue Funktion `warteliste_tagesgrenze_merken()` → True genau einmal je UTC-Tag (Merker `warteliste-tag-gemeldet` in `versand`, atomar in einer Transaktion) |
| engine/anmeldung.py | MODIFY | Weg `/warteliste` POST: bei `x.schluessel == "konto.fehler.warteliste_tag_voll"` und `konten.warteliste_tagesgrenze_merken()` → `betreiber_melden(None, "betrieb", texte.t(VORGABE, "konto.betreiber.warteliste_tagesgrenze", grenze=…), [("konto.meldungen.text.warteliste_tagesgrenze", {"grenze": …})])`; Seite zeigt den Satz wie andere Ablehnungen (Formular mit Satz) |
| engine/texte_de.py, engine/texte_en.py | MODIFY | `konto.fehler.warteliste_tag_voll` („Heute sind alle Plätze vergeben. Bitte morgen wieder.“), `konto.betreiber.warteliste_tagesgrenze`, `konto.meldungen.text.warteliste_tagesgrenze` |
| engine/tests/test_warteliste.py | MODIFY | Tests: Grenze greift (keine Mail, keine Zeile in `warteliste`, keine `versand`-Zeile der Adresse), neuer Tag gibt frei (Zeit über `_jetzt`-Patch), erneute Mail an unbestätigte Adresse zählt, bestätigte Adresse zählt nicht, Ablehnung auch für bestätigte Adresse bei voller Grenze (verrät nichts), Freigaben zählen nicht, Betreiber-Meldung genau einmal je Tag, `FR_GRENZE_WARTELISTE_TAG` wirkt, ungültiger Wert = 20 |
| docs/konten.md | MODIFY | Abschnitt Warteliste: Tagesgrenze, Grund (Mail-Kontingent), Meldung an Betreiber |
| docs/betrieb.md, betrieb/einstellungen.beispiel | MODIFY | Zeile `FR_GRENZE_WARTELISTE_TAG` (Vorgabe 20; Ort des Werts wie `FR_GRENZE_REISEN`, `konten.env`) |

### Scope Assessment
- Files: 8
- Estimated LoC: +~170/-~3 (davon ~110 Tests)
- Risk Level: LOW — nur der Eintragsweg der Warteliste, bestehende Muster (`versand`, `_grenze`, `betreiber_melden`)

### Technical Approach
- Kalendertag UTC: Zählung `versand` mit `zeit >= Mitternacht UTC`; `_begrenzt` löscht nur Zeilen > 24 h, die Zeilen des laufenden Tages bleiben also erhalten. Eigene kleine Zählung statt `_begrenzt` (das gleitende Fenster passt nicht).
- Reihenfolge in `warteliste_eintragen`: Adresse prüfen → Mail eingerichtet → abgelaufene löschen → Adress-/IP-Begrenzung → **Tagesgrenze** → `versand`-Zeilen der Adresse → Stand. Die Tagesgrenze steht vor jeder Unterscheidung nach dem Stand (verrät nichts) und vor jedem Schreiben (nichts gespeichert).
- Gezählt wird jede ausgelöste Bestätigungsmail (auch die erneute an eine unbestätigte Adresse), nicht bestätigte Adressen ohne Mail und nicht `freigeben`. Ablehnung durch `warteliste_voll` (Höchstzahl unbestätigt) zählt nicht, weil keine Mail rausgeht: Zeile `warteliste-tag` erst direkt vor dem Ende der Transaktion einfügen (nach der `warteliste_voll`-Prüfung).
- Betreiber-Meldung: Merker in `versand` (`warteliste-tag-gemeldet`, Prüfen+Einfügen in einer Transaktion), Meldung in `anmeldung.py` (konten importiert anmeldung nicht). Art `betrieb` (vorhanden, warm, ohne Reise → kein Ziel-Link); Texte mit Grenze als Zahl. Kein Telegram.
- Mail-Versand liegt nach der Transaktion: Scheitert der Versand, ist die Zeile `warteliste-tag` trotzdem gezählt — vertretbar (vorsichtig fürs Kontingent).
- Monitor unverändert (Resend-Teil-Check in henemm-infra bleibt die Gesamtwarnung).
- `neu.py nachziehen`: nicht nötig (kein Reisedatenformat betroffen). Instanz-Tests: neuer Fehlertext und neuer Umgebungswert; Tests der Instanz vor dem Vorspulen mitlaufen lassen.

### Dependencies
- Upstream: `instanz.wert/_grenze`, Tabelle `versand`, `texte`, `rueckmeldungen.meldung_anlegen` (über `betreiber_melden`).
- Downstream: Seite `/warteliste`, Mein Konto und `meine_reisen` der Betreiber (Meldungen), Push (Art `betrieb` löst Push aus — gewollt, einmal je Tag).

### Open Questions
- keine (Umfang im Issue durch PO-Entscheidung festgelegt; Wortlaut der Seite steht im Issue)
